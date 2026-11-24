"""Track one face through action for Face Swap, then smooth the whole track.

Per-frame five-point detection drifts and drops out exactly when a face moves:
motion blur lowers the detector score, a whip pan looks like a scene cut, and
each frame's landmarks jitter independently. That makes the swap crop shake
(the generated face wobbles and blurs) or jump to the wrong place. This module
replaces the per-frame guess with a two-stage track:

1. Analysis, in frame order. Each frame gets a prediction from pyramidal
   optical flow (a similarity transform fitted to forward-backward checked
   feature tracks on the face). A detection close to the prediction keeps the
   identity without needing a confident recognition score, so blurred frames
   stay attached. The estimate is then refined with the dense face mesh on an
   upright aligned crop; the five alignment points come from eye contours,
   the nose tip and the mouth corners, which hold steadier than the
   detector's points under blur and turn. Frames with no detection are carried
   by the flow prediction for a short time.
2. Smoothing, over the finished track. Within each shot, short gaps are bridged
   and every coordinate is filtered with a forward and a backward One Euro
   filter whose outputs are averaged: strong smoothing when the face is slow,
   almost none when it moves fast, and no lag in either direction.
"""
import math

import cv2
import numpy as np

if __package__:
    from .face_models import ARCFACE_112, ARCFACE_128, aligned_crop, encode, occlusion
else:
    from face_models import ARCFACE_112, ARCFACE_128, aligned_crop, encode, occlusion

# Eye contours of the 468-point face mesh, image-left eye first.
MESH_EYES = (
    (33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246),
    (362,382,381,380,374,373,390,249,263,466,388,387,386,385,384,398),
)
# Points that follow the swap model's alignment convention (pupil centers,
# nose tip, mouth corners). Iris centers 468/473 exist in the 478-point mesh.
MESH_IRIS, MESH_NOSE, MESH_MOUTH = (468, 473), 1, (61, 291)
# Mesh points for flow tracking that move with the skull: forehead, temples,
# nose bridge, cheekbones and upper cheeks. The jaw, chin and lips are left
# out because talking, smiling or a stuck-out tongue moves them on their own
# and would pull the predicted head transform.
FLOW_POINTS = (10, 151, 9, 67, 297, 109, 338, 103, 332, 70, 300, 105, 334, 8, 168, 6, 197, 195, 5, 4,
               48, 278, 127, 356, 234, 454, 93, 323, 116, 345, 117, 346, 123, 352, 50, 280, 205, 425, 187, 411,
               36, 266, 101, 330, 118, 347, 119, 348, 207, 427)
# A wider version of the swap template keeps the whole face and some margin in
# the mesh crop, which the landmarker needs to lock on.
MESH_TEMPLATE = (ARCFACE_128-.5)*.72+.5
MESH_SIZE = 256
MAX_FLOW_GAP = 15
BRIDGE_GAP = 8
LK = {"winSize": (21, 21), "maxLevel": 4,
      "criteria": (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 20, .02)}


def face_from_points(points, score=1.):
    """Build a detector-style row (box, five points, score) from five points."""
    points = np.asarray(points, np.float32).reshape(5, 2)
    ocular = max(1., float(np.linalg.norm(points[1]-points[0])))
    center = points.mean(axis=0)
    side = 2.6*ocular
    return np.array([center[0]-side/2, center[1]-side*.45, side, side, *points.reshape(-1), score], np.float32)


def ocular(points):
    points = np.asarray(points, np.float32).reshape(5, 2)
    return max(1., float(np.linalg.norm(points[1]-points[0])))


def mesh_five(image, points, detector):
    """Refine five points with the dense mesh on an upright crop.

    Returns (five points, mesh points in frame coordinates) or (None, None).
    """
    import mediapipe as mp

    face = face_from_points(points)
    try:
        crop, matrix = aligned_crop(image, face, MESH_TEMPLATE, MESH_SIZE)
    except ValueError:
        return None, None
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
    if not result.face_landmarks:
        return None, None
    mesh = np.array([(p.x*MESH_SIZE, p.y*MESH_SIZE) for p in result.face_landmarks[0]], np.float32)
    inverse = cv2.invertAffineTransform(matrix)
    frame = mesh @ inverse[:, :2].T + inverse[:, 2]
    eyes = [frame[index] for index in MESH_IRIS] if len(frame) > max(MESH_IRIS) else \
        [frame[list(contour)].mean(axis=0) for contour in MESH_EYES]
    five = np.array([*eyes, frame[MESH_NOSE], frame[MESH_MOUTH[0]], frame[MESH_MOUTH[1]]], np.float32)
    # Reject a mesh that landed on something other than the estimated face.
    scale = ocular(five)/ocular(points)
    shift = float(np.linalg.norm(five.mean(axis=0)-np.asarray(points).reshape(5, 2).mean(axis=0)))/ocular(points)
    if not .6 < scale < 1.6 or shift > .45:
        return None, None
    return five, frame


def flow_prediction(previous_gray, gray, anchors, five):
    """Carry the last five points to this frame with a similarity transform."""
    if previous_gray is None or anchors is None or len(anchors) < 6:
        return None, 0.
    start = anchors.reshape(-1, 1, 2).astype(np.float32)
    forward, good, _ = cv2.calcOpticalFlowPyrLK(previous_gray, gray, start, None, **LK)
    if forward is None:
        return None, 0.
    backward, back, _ = cv2.calcOpticalFlowPyrLK(gray, previous_gray, forward, None, **LK)
    if backward is None:
        return None, 0.
    error = np.linalg.norm(backward[:, 0]-start[:, 0], axis=1)
    keep = (good[:, 0] > 0) & (back[:, 0] > 0) & (error < max(1., .04*ocular(five)))
    if np.count_nonzero(keep) < 6:
        return None, 0.
    transform, inliers = cv2.estimateAffinePartial2D(start[keep, 0], forward[keep, 0], method=cv2.RANSAC,
                                                     ransacReprojThreshold=max(1.5, .05*ocular(five)))
    if transform is None:
        return None, 0.
    support = float(np.count_nonzero(inliers))/len(anchors)
    points = np.asarray(five, np.float32).reshape(5, 2)
    return points @ transform[:, :2].T + transform[:, 2], support


def shot_change(previous_hist, hist):
    # Color histograms survive whip pans and blur that defeat pixel differences.
    return previous_hist is not None and cv2.compareHist(previous_hist, hist, cv2.HISTCMP_CORREL) < .55


def histogram(image):
    small = cv2.resize(image, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    return cv2.normalize(hist, hist).flatten()


class ActionTracker:
    """Frame-ordered analysis. ``step`` returns a record for each frame."""

    def __init__(self, recognizer, mesh=None, identity=None, rivals=(), index=0, occluder=None):
        self.recognizer, self.mesh, self.occluder = recognizer, mesh, occluder
        self.identity, self.rivals = identity, rivals
        self.require_identity = identity is not None
        self.index = index
        self.gray = self.hist = self.five = self.anchors = None
        self.carried = 0
        self.since_check = 0
        self.stats = {"detected": 0, "flow_carried": 0, "mesh_refined": 0, "lost": 0, "cuts": 0, "mouth_covered": 0}

    def embedding(self, image, face):
        crop, _ = aligned_crop(image, face, ARCFACE_112, 112)
        return encode(self.recognizer, crop)

    def score(self, image, face):
        return float(np.sum(self.embedding(image, face)*self.identity))

    def choose(self, image, faces, prediction, cut):
        """Pick the detection that continues the track, or None."""
        if not len(faces):
            return None
        if prediction is not None and not cut:
            # Continuity: the nearest detection to the flow prediction, if it
            # is plausibly the same face. Identity is re-checked every few
            # frames, and only rejects on a clear mismatch, so blur is tolerated.
            centers = np.array([face[4:14].reshape(5, 2).mean(axis=0) for face in faces])
            distance = np.linalg.norm(centers-prediction.mean(axis=0), axis=1)/ocular(prediction)
            best = int(np.argmin(distance))
            if distance[best] < .8:
                if self.identity is not None and (self.since_check >= 8 or len(faces) > 1):
                    self.since_check = 0
                    if self.score(image, faces[best]) < .12:
                        return None
                return faces[best]
        if self.identity is None:
            if self.index >= len(faces):
                return None
            face = faces[self.index]
            self.identity = self.embedding(image, face)
            return face
        scores = [self.score(image, face) for face in faces]
        order = np.argsort(scores)
        best = int(order[-1])
        threshold = .48 if self.require_identity else .42
        margin = .05 if self.require_identity else 0
        if scores[best] < threshold or (len(order) > 1 and scores[best]-scores[order[-2]] < margin):
            return None
        if self.rivals:
            candidate = self.embedding(image, faces[best])
            if any(scores[best]-float(np.sum(candidate*rival)) < margin for rival in self.rivals):
                return None
        return faces[best]

    def step(self, image, faces):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hist = histogram(image)
        cut = shot_change(self.hist, hist)
        self.stats["cuts"] += int(cut)
        prediction, support = (None, 0.) if cut or self.five is None else \
            flow_prediction(self.gray, gray, self.anchors, self.five)
        if prediction is not None and support < .3:
            prediction = None
        self.since_check += 1
        detection = self.choose(image, faces, prediction, cut)
        if detection is not None:
            estimate, source = detection[4:14].reshape(5, 2), "detect"
            self.carried = 0
        elif prediction is not None and self.carried < MAX_FLOW_GAP:
            estimate, source = prediction, "flow"
            self.carried += 1
        else:
            estimate = source = None
        # "cut" marks a shot change only. A restart after a lost face is a new
        # smoothing segment anyway, and may still be bridged within the shot.
        record = {"points": None, "source": None, "cut": bool(cut)}
        if estimate is not None:
            five, mesh = (None, None)
            if self.mesh is not None:
                five, mesh = mesh_five(image, estimate, self.mesh)
                if five is not None and source == "flow":
                    # A second pass realigns the crop on the refined points.
                    five, mesh = mesh_five(image, five, self.mesh) if five is not None else (None, None)
            if five is not None:
                self.stats["mesh_refined"] += 1
                self.anchors = mesh[list(FLOW_POINTS)]
            else:
                five = np.asarray(estimate, np.float32)
                self.anchors = self.corner_anchors(gray, five)
            if self.occluder is not None:
                five = self.uncover(image, five, cut)
            self.stats["detected" if source == "detect" else "flow_carried"] += 1
            record.update(points=five.astype(np.float64), source=source)
            self.five = five
        else:
            self.stats["lost"] += 1
            self.five = self.anchors = None
        self.gray, self.hist = gray, hist
        return record

    def uncover(self, image, five, cut):
        """Keep alignment and flow off whatever is in front of the face.

        A hand or food at the mouth hides the mouth corners, and the mesh then
        guesses them, so the crop jumps and the swap smears. While the eyes and
        nose stay visible, the corners follow the head rigidly from the last
        frame instead. Flow points on the covering object are dropped too.
        """
        try:
            crop, matrix = aligned_crop(image, face_from_points(five), ARCFACE_128, 256)
        except ValueError:
            return five
        visible = occlusion(self.occluder, crop)
        seen = lambda points: visible[np.clip(np.rint(points @ matrix[:, :2].T + matrix[:, 2]).astype(int)[:, 1], 0, 255),
                                      np.clip(np.rint(points @ matrix[:, :2].T + matrix[:, 2]).astype(int)[:, 0], 0, 255)]
        if self.anchors is not None and len(self.anchors):
            clear = seen(np.asarray(self.anchors, np.float32)) >= .5
            if np.count_nonzero(clear) >= 8:
                self.anchors = self.anchors[clear]
        shown = seen(five)
        if cut or self.five is None or shown[3:].min() >= .5 or shown[:3].min() < .5:
            return five
        transform, _ = cv2.estimateAffinePartial2D(self.five[:3], five[:3], method=cv2.LMEDS)
        if transform is None:
            return five
        five = five.copy()
        five[3:] = self.five[3:] @ transform[:, :2].T + transform[:, 2]
        self.stats["mouth_covered"] += 1
        return five

    @staticmethod
    def corner_anchors(gray, five):
        """Strong corners inside the face when no mesh is available."""
        size = ocular(five)
        center = five.mean(axis=0)
        mask = np.zeros_like(gray)
        cv2.ellipse(mask, (int(center[0]), int(center[1])), (int(1.1*size), int(1.4*size)), 0, 0, 360, 255, -1)
        corners = cv2.goodFeaturesToTrack(gray, 60, .01, max(3, size/10), mask=mask)
        return None if corners is None else corners[:, 0]


class OneEuro:
    """One Euro filter (Casiez et al., CHI 2012) on a uniformly sampled signal.

    The cutoff rises with speed, in face widths (inter-ocular distances) per
    second. Offline, the speed comes from a centered difference over the raw
    track, so the filter opens as soon as a movement starts instead of after
    a causal derivative has caught up.
    """

    def __init__(self, rate, minimum=1., beta=20.):
        self.rate, self.minimum, self.beta = rate, minimum, beta

    def alpha(self, cutoff):
        tau = 1/(2*math.pi*cutoff)
        return 1/(1+tau*self.rate)

    def run(self, values, speeds):
        out = np.empty_like(values)
        previous = values[0]
        out[0] = previous
        for index in range(1, len(values)):
            cutoff = self.minimum+self.beta*speeds[index]
            previous = previous+self.alpha(cutoff)*(values[index]-previous)
            out[index] = previous
        return out


def track_speed(segment, rate, scale, reach=3):
    """Centered speed in face widths per second.

    The second-fastest point is used: one noisy landmark cannot open the
    filter, while a mouth movement (both corners) or head motion still does.
    """
    count = len(segment)
    speeds = np.empty(count)
    for index in range(count):
        low, high = max(0, index-reach), min(count-1, index+reach)
        if high == low:
            speeds[index] = 0
            continue
        step = np.sort(np.linalg.norm(segment[high]-segment[low], axis=1))[-2]
        speeds[index] = step*rate/(high-low)/scale
    return speeds


def smooth_track(records, fps, minimum=1., beta=20.):
    """Bridge short gaps and apply zero-lag adaptive smoothing within shots.

    Returns a list of (five points or None, bridged flag).
    """
    count = len(records)
    points = [None if record["points"] is None else np.asarray(record["points"], np.float64) for record in records]
    bridged = [False]*count
    # Bridge short gaps inside a shot by interpolating between the ends.
    index = 0
    while index < count:
        if points[index] is not None:
            index += 1
            continue
        start = index
        while index < count and points[index] is None:
            index += 1
        before, after = start-1, index
        # Straight-line bridging is only trusted while the face moves slowly;
        # a fast whip through the gap is left untouched rather than guessed.
        def step(a, b):
            if a < 0 or b >= count or points[a] is None or points[b] is None:
                return 0.
            return float(np.linalg.norm(points[b]-points[a], axis=1).max())/(b-a)
        slow = before >= 0 and after < count and max(
            step(before, after), step(before-1, before), step(after, after+1)) < .12*ocular(points[before])
        if slow and index-start <= BRIDGE_GAP and not any(records[k]["cut"] for k in range(start, after+1)):
            for k in range(start, after):
                t = (k-before)/(after-before)
                points[k] = points[before]*(1-t)+points[after]*t
                bridged[k] = True
    result = [None]*count
    filter_ = OneEuro(fps, minimum, beta)
    index = 0
    while index < count:
        if points[index] is None:
            index += 1
            continue
        start = index
        index += 1
        while index < count and points[index] is not None and not records[index]["cut"]:
            index += 1
        segment = np.stack(points[start:index])
        if len(segment) > 2:
            scale = float(np.median([ocular(p) for p in segment]))
            speeds = track_speed(segment, fps, scale)
            forward = filter_.run(segment, speeds)
            backward = filter_.run(segment[::-1], speeds[::-1])[::-1]
            segment = (forward+backward)/2
        for offset, value in enumerate(segment):
            result[start+offset] = value
    return [(value, flag) for value, flag in zip(result, bridged)]


def motion_measures(track):
    """Per-frame relative landmark motion and mean velocity in pixels/frame."""
    measures = []
    for index, (points, _) in enumerate(track):
        if points is None:
            measures.append((0., np.zeros(2)))
            continue
        neighbours = [track[k][0] for k in (index-1, index+1) if 0 <= k < len(track) and track[k][0] is not None]
        if not neighbours:
            measures.append((0., np.zeros(2)))
            continue
        delta = np.mean([np.abs(points-other) for other in neighbours], axis=0)
        motion = float(np.percentile(np.linalg.norm(delta, axis=1), 75))/(2.6*ocular(points))
        if index+1 < len(track) and index-1 >= 0 and track[index+1][0] is not None and track[index-1][0] is not None:
            velocity = (track[index+1][0]-track[index-1][0]).mean(axis=0)/2
        else:
            velocity = np.mean([points-other for other in neighbours], axis=0).mean(axis=0)
        measures.append((motion, velocity))
    return measures

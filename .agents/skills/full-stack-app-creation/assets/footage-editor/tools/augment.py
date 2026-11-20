"""Prepare localized body, face, and hands on the original media clock."""
import argparse
from contextlib import ExitStack
from itertools import permutations
import json
import math
from pathlib import Path
from types import SimpleNamespace

import av
import mediapipe as mp
import numpy as np
from PIL import Image

from anatomy import catalog as detail_catalog, facial_details, hand_details, pose_details

BODY = {
    "left-arm": ("Left arm", [(11, 13, .29), (13, 15, .31)]),
    "right-arm": ("Right arm", [(12, 14, .29), (14, 16, .31)]),
    "left-leg": ("Left leg", [(23, 25, .35), (25, 27, .27)]),
    "right-leg": ("Right leg", [(24, 26, .35), (26, 28, .27)]),
    "shoulders": ("Shoulders", []),
    "torso": ("Torso", []),
    "head": ("Head", []),
}
FACE = {
    "left-eye": ("Left eye", (362, 263, 385, 380)),
    "right-eye": ("Right eye", (33, 133, 159, 145)),
    "left-brow": ("Left eyebrow", (336, 300, 334, 296)),
    "right-brow": ("Right eyebrow", (70, 107, 105, 66)),
    "nose": ("Nose", (98, 327, 6, 2)),
    "mouth": ("Mouth", (61, 291, 0, 17)),
    "chin": ("Chin", (148, 377, 17, 152)),
}
TORSO_DETAILS = {
    "chest": "Chest",
    "left-breast": "Left breast",
    "right-breast": "Right breast",
    "hips": "Rear hips",
    "left-hip": "Left hip",
    "right-hip": "Right hip",
    "buttocks": "Buttocks",
    "left-buttock": "Left buttock",
    "right-buttock": "Right buttock",
    "left-calf": "Left calf",
    "right-calf": "Right calf",
}
FINGERS = {
    "thumb": ("thumb", (1, 2, 3, 4)),
    "index-finger": ("index finger", (5, 6, 7, 8)),
    "middle-finger": ("middle finger", (9, 10, 11, 12)),
    "ring-finger": ("ring finger", (13, 14, 15, 16)),
    "pinky": ("little finger", (17, 18, 19, 20)),
}
SIDES = {"left": (11, 13, 15, 23, 25, 27), "right": (12, 14, 16, 24, 26, 28)}


def midpoint(a, b):
    return ((a[0]+b[0])/2, (a[1]+b[1])/2)


def axis(a, b):
    x, y = b[0]-a[0], b[1]-a[1]
    length = math.hypot(x, y)
    return (x/length, y/length, length) if length > 1 else (1, 0, 1)


def mix(a, b, fraction):
    return tuple(left+(right-left)*fraction for left, right in zip(a[:2], b[:2]))


def ellipse(center, direction, width, length):
    # Center, unit width axis, and support radii in source pixels. The
    # perpendicular axis is length. A finite support leaves distant pixels fixed.
    return [round(value, 3) for value in (*center, *direction[:2], max(7, width), max(9, length))]


def on_screen(region, width, height):
    x, y, _, _, rx, ry = region
    margin = .6*max(rx, ry)
    return -margin < x < width+margin and -margin < y < height+margin


class SubjectMatte:
    """Sample each displayed frame's original foreground matte in source pixels."""

    def __init__(self, manifest, timeline):
        self.manifest = manifest
        self.parent = timeline.parent
        self.tile_width, self.tile_height = manifest["tile"]
        self.grid = manifest["grid"]
        self.scale = manifest["pixelScale"]
        self.page = None

    def seek(self, index):
        page, self.slot = divmod(index, self.grid**2)
        if page != self.page:
            path = self.parent / self.manifest["pages"][page][0]
            with Image.open(path) as image:
                self.matte = np.asarray(image.convert("RGB"))[..., 0]
            self.page = page

    def __call__(self, point, width, height):
        x, y = point[:2]
        if not (0 <= x < width and 0 <= y < height):
            return False
        column = (self.slot % self.grid)*self.tile_width + int(x/self.scale)
        row = (self.slot // self.grid)*self.tile_height + int(y/self.scale)
        return self.matte[row, column] >= 77


def keep_region(result, name, region, foreground):
    if foreground(region[:2]):
        result[name] = [region]


def local_torso_regions(points, foreground):
    result = {}
    left_shoulder, right_shoulder = points[11], points[12]
    left_hip, right_hip = points[23], points[24]
    if min(point[2] for point in (left_shoulder,right_shoulder,left_hip,right_hip)) < 40:
        return result
    shoulder, hip = midpoint(left_shoulder,right_shoulder), midpoint(left_hip,right_hip)
    tx,ty,trunk = axis(shoulder,hip)
    wx,wy,span = axis(right_shoulder,left_shoulder)
    hx,hy,hip_span = axis(right_hip,left_hip)
    if trunk < 45 or ty < .55:
        return result
    # Shoulder/hip order reverses between front and rear. Both pairs must
    # show a meaningful projected width, so side-on frames stay unlabelled.
    shoulder_order = left_shoulder[0]-right_shoulder[0]
    hip_order = left_hip[0]-right_hip[0]
    front = shoulder_order > .30*trunk and hip_order > .21*trunk
    rear = shoulder_order < -.30*trunk and hip_order < -.21*trunk
    if front:
        left = mix(left_shoulder,left_hip,.31)
        right = mix(right_shoulder,right_hip,.31)
        keep_region(result,"chest",ellipse(midpoint(left,right),(wx,wy),span*.56,trunk*.24),foreground)
        for side, a, b in (("left",left,right),("right",right,left)):
            region = ellipse(mix(a,b,.24),(wx,wy),span*.24,trunk*.18)
            keep_region(result,f"{side}-breast",region,foreground)
    if rear:
        through = lambda p, distance: (p[0]+tx*trunk*distance,p[1]+ty*trunk*distance)
        keep_region(result,"hips",ellipse(hip,(hx,hy),hip_span*.69,trunk*.19),foreground)
        keep_region(result,"buttocks",ellipse(through(hip,.14),(hx,hy),hip_span*.68,trunk*.23),foreground)
        for side, a, b in (("left",left_hip,right_hip),("right",right_hip,left_hip)):
            keep_region(result,f"{side}-hip",ellipse(mix(a,b,.10),(hx,hy),hip_span*.28,trunk*.16),foreground)
            region = ellipse(through(mix(a,b,.22),.14),(hx,hy),hip_span*.28,trunk*.18)
            keep_region(result,f"{side}-buttock",region,foreground)
    return result


def calf_regions(points, foreground):
    result = {}
    for side, (_,_,_,_,knee_id,ankle_id) in SIDES.items():
        knee,ankle = points[knee_id],points[ankle_id]
        if min(knee[2],ankle[2]) < 28:
            continue
        ux,uy,length = axis(knee,ankle)
        if length < 22:
            continue
        start, center, end = (mix(knee,ankle,t) for t in (.20,.43,.65))
        # A projected shin beyond the edge or behind the performer is not
        # useful as an independent control. Require the visible calf core.
        if sum(foreground(p) for p in (start,center,end)) >= 2 and foreground(center):
            result[f"{side}-calf"] = [ellipse(center,(-uy,ux),length*.20,length*.37)]
    return result


def hand_sides(results, points, width, height):
    detections = [
        ([(p.x*width,p.y*height) for p in landmarks], handedness[0].category_name.lower())
        for landmarks,handedness in zip(results.hand_landmarks,results.handedness)
        if handedness and len(landmarks) == 21
    ]
    # Assign both hands jointly so a crossed hand cannot take the other
    # wrist's label just because it was detected first.
    def evaluate(sides):
        matches, cost = [], 0
        for side, (hand, inferred_side) in zip(sides,detections):
            _,elbow_id,wrist_id,*_ = SIDES[side]
            wrist,elbow = points[wrist_id],points[elbow_id]
            separation = math.dist(wrist[:2],hand[0])
            tolerance = min(125,max(47,math.dist(wrist[:2],elbow[:2])*.55))
            if wrist[2] < 18 or separation > tolerance:
                continue
            cost += separation/tolerance + (.18 if side != inferred_side else 0)
            matches.append((side,hand))
        return (-len(matches),cost),matches

    if not detections:
        return []
    return min((evaluate(sides) for sides in permutations(SIDES,len(detections))),
               key=lambda candidate:candidate[0])[1]


def hand_regions(detections, points, width, height, foreground):
    result = {}
    for side, hand in hand_sides(detections,points,width,height):
        across = math.dist(hand[5],hand[17])
        ux,uy,palm_length = axis(hand[0],hand[9])
        if palm_length < 10 or across < 5:
            continue
        palm = mix(hand[0],hand[9],.57)
        tip_extent = max(math.dist(palm,hand[i]) for i in (4,8,12,16,20))
        keep_region(result,f"{side}-hand",ellipse(palm,(-uy,ux),across*.80,max(palm_length*.92,tip_extent*.74)),foreground)
        if f"{side}-hand" in result:
            result.update(hand_details(side,hand,FINGERS,across,foreground))
        for name,(_,indices) in FINGERS.items():
            joints = [hand[i] for i in indices]
            axis_x,axis_y,span = axis(joints[0],joints[-1])
            center = midpoint(joints[1],joints[2])
            if span < 7 or sum(foreground(point) for point in joints[1:]) < 2:
                continue
            region = ellipse(center,(-axis_y,axis_x),min(18,across*.26),span*.59)
            keep_region(result,f"{side}-{name}",region,foreground)
    return result


def body_regions(points, width, height):
    result = {}
    for name, (_, segments) in BODY.items():
        regions = []
        for a, b, proportion in segments:
            start, end = points[a], points[b]
            if min(start[2], end[2]) < 16:
                regions.append(None)
                continue
            ux, uy, length = axis(start, end)
            region = ellipse(midpoint(start, end), (-uy, ux), max(27,length*proportion), length*.73)
            regions.append(region if on_screen(region,width,height) else None)
        if any(regions):
            result[name] = regions
    shoulder = midpoint(points[11], points[12])
    hip = midpoint(points[23], points[24])
    ux, uy, span = axis(points[12], points[11])
    tx, ty, trunk = axis(shoulder, hip)
    result["shoulders"] = [ellipse(shoulder, (ux, uy), max(70, span*.78), max(35, trunk*.23))]
    result["torso"] = [ellipse(midpoint(shoulder, hip), (-ty, tx), max(65, span*.69), trunk*.65)]
    ears = axis(points[7], points[8])
    result["head"] = [ellipse(midpoint(points[0], midpoint(points[7], points[8])),
                              ears, max(49, ears[2]*1.07), max(65, ears[2]*1.25))]
    return result


def face_regions(landmarks, width, height, pose_nose, foreground):
    pixels = [(lm.x*width, lm.y*height) for lm in landmarks]
    baseline = axis(pixels[33], pixels[263])
    if baseline[2] < 15 or math.dist(pixels[1], pose_nose[:2]) > max(42, baseline[2]):
        return {}
    result = {}
    for name, (_, ids) in FACE.items():
        a, b, c, d = (pixels[i] for i in ids)
        ux, uy, span = axis(a, b)
        minimum = baseline[2]*(.19 if "eye" in name else .23)
        region = ellipse(midpoint(midpoint(a,b),midpoint(c,d)), (ux,uy),
                         max(minimum,span*.95), max(minimum*.65,math.dist(c,d)*1.05))
        if on_screen(region,width,height):
            result[name] = [region]
    for key,shapes in facial_details(pixels,baseline,foreground).items():
        if any(shape for shape in shapes) and key not in result:
            result[key] = shapes
    return result


def build(source, model, timeline, output, hand_model=None, base_regions=None):
    manifest = json.loads(timeline.read_text())
    base = json.loads(base_regions.read_text()) if base_regions else None
    if base and len(base["frames"]) != len(manifest["frames"]):
        raise ValueError("Base augmentation and motion timelines have different frame counts")
    tasks = mp.tasks.vision
    options = tasks.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=tasks.RunningMode.VIDEO,
        min_face_detection_confidence=.38, min_face_presence_confidence=.44,
        min_tracking_confidence=.47,
    )
    crop_options = tasks.FaceLandmarkerOptions(
        base_options=options.base_options, running_mode=tasks.RunningMode.IMAGE,
        min_face_detection_confidence=.35, min_face_presence_confidence=.42)
    matte = SubjectMatte(manifest,timeline)
    rows = []
    with ExitStack() as stack:
        container = stack.enter_context(av.open(str(source)))
        finder = stack.enter_context(tasks.FaceLandmarker.create_from_options(options))
        cropped_finder = stack.enter_context(tasks.FaceLandmarker.create_from_options(crop_options))
        hand_finder = None
        if hand_model is not None:
            hand_options = tasks.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(hand_model)),
                running_mode=tasks.RunningMode.VIDEO, num_hands=2,
                min_hand_detection_confidence=.36, min_hand_presence_confidence=.43,
                min_tracking_confidence=.46,
            )
            hand_finder = stack.enter_context(tasks.HandLandmarker.create_from_options(hand_options))
        stream = container.streams.video[0]
        stream.thread_count = 2
        width,height = stream.width,stream.height
        for index,frame in enumerate(container.decode(stream)):
            expected_width, layers = manifest["frames"][index]
            timestamp = float(frame.pts*frame.time_base)
            if expected_width != width or abs(timestamp-index/manifest["fps"]) > .0006:
                raise ValueError(f"Timeline mismatch at frame {index}")
            points = {key:(x/4,y/4,confidence) for key,(x,y,confidence) in zip(manifest["landmarks"],layers[0])}
            regions = body_regions(points,width,height)
            matte.seek(index)
            foreground = lambda point: matte(point,width,height)
            regions.update(local_torso_regions(points,foreground))
            regions.update(calf_regions(points,foreground))
            regions.update(pose_details(points,foreground))
            rgb = frame.to_ndarray(format="rgb24")
            image = mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
            face = finder.detect_for_video(image,int(timestamp*1000))
            facial = face_regions(face.face_landmarks[0],width,height,points[0],foreground) if face.face_landmarks else {}
            if not facial and points[0][2] > 35:
                # A head crop gives the same detector more pixels on profile
                # views. The pose-nose check still rejects unrelated detections.
                x,y = points[0][:2]
                r = max(78,1.25*math.dist(points[7][:2],points[8][:2]))
                l,t = max(0,int(x-r)),max(0,int(y-r*1.12))
                right,bottom = min(width,int(x+r)),min(height,int(y+r*1.12))
                if right-l>24 and bottom-t>24:
                    crop = mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb[t:bottom,l:right]))
                    candidate = cropped_finder.detect(crop)
                    if candidate.face_landmarks:
                        projected = [SimpleNamespace(x=(l+lm.x*(right-l))/width,y=(t+lm.y*(bottom-t))/height)
                                     for lm in candidate.face_landmarks[0]]
                        facial = face_regions(projected,width,height,points[0],foreground)
            regions.update(facial)
            if hand_finder is not None:
                detected = hand_finder.detect_for_video(image,int(timestamp*1000))
                regions.update(hand_regions(detected,points,width,height,foreground))
            # Extend the reviewed catalog and keep its original per-frame
            # tracks, including frames where an existing feature was absent.
            if base:
                regions = {key:shapes for key,shapes in regions.items() if key not in base["parts"]}
                regions = base["frames"][index] | regions
            rows.append(regions)
    if len(rows) != len(manifest["frames"]):
        raise ValueError("The augmentation and motion timelines have different frame counts")
    catalog = {name:label for name,(label,_) in {**BODY,**FACE}.items()}
    catalog.update(TORSO_DETAILS)
    if hand_model is not None:
        for side in SIDES:
            catalog[f"{side}-hand"] = f"{side.title()} hand"
            catalog.update({f"{side}-{name}":f"{side.title()} {label}" for name,(label,_) in FINGERS.items()})
    details = detail_catalog(SIDES,FINGERS,hand_model is not None)
    catalog.update({key:label for key,(label,_) in details.items()})
    if base:
        catalog = base["parts"] | {key:label for key,label in catalog.items() if key not in base["parts"]}
    data = {"parts":catalog, "parents":{key:parent for key,(_,parent) in details.items()},
            "frames":rows}
    output.parent.mkdir(parents=True,exist_ok=True)
    staging = output.with_suffix(".partial")
    staging.write_text(json.dumps(data,separators=(",",":")))
    staging.replace(output)
    print(json.dumps({name:sum(name in row for row in rows) for name in catalog}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("face_model", type=Path)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--hand-model", type=Path, help="MediaPipe Hand Landmarker task bundle")
    parser.add_argument("--base-regions", type=Path, help="Preserve reviewed regions while adding detailed tracks")
    args = parser.parse_args()
    build(args.source,args.face_model,args.timeline,args.output,args.hand_model,args.base_regions)

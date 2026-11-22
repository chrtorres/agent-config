"""Score Face Swap tracking on a synthetic action clip with known motion.

Compares the earlier per-frame tracker with the action tracker. Each method is
scored against its own still-image points carried by the clip's exact motion,
so the score measures how faithfully the alignment follows the face.

Usage: face_tracking_benchmark.py <portrait> <clip.mp4> <face-models-dir> <face.task>
The clip and its .truth.json come from make_action_face_clip.py.
"""
import json
from pathlib import Path
import sys

import av
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"tools"))
from face_curvature import create_mesh_detector  # noqa: E402
from face_models import detect_faces, session  # noqa: E402
from face_swap_video import FaceTrack  # noqa: E402
from face_tracking import ActionTracker, mesh_five, ocular, smooth_track  # noqa: E402


def score(estimates, reference, matrices):
    errors, residuals, found = [], [], 0
    for points, matrix in zip(estimates, matrices):
        matrix = np.asarray(matrix)
        truth = reference @ matrix[:, :2].T + matrix[:, 2]
        if points is None:
            errors.append(None)
            residuals.append(None)
            continue
        found += 1
        residual = np.asarray(points).reshape(5, 2)-truth
        residuals.append(residual)
        errors.append(float(np.linalg.norm(residual, axis=1).mean())/ocular(truth))
    valid = [e for e in errors if e is not None]
    jitter = [float(np.linalg.norm(a-2*b+c, axis=1).mean())/ocular(reference)
              for a, b, c in zip(residuals, residuals[1:], residuals[2:]) if a is not None and b is not None and c is not None]
    return {"coverage": f"{found}/{len(estimates)}", "mean_error": round(float(np.mean(valid)), 4),
            "p95_error": round(float(np.percentile(valid, 95)), 4), "worst_error": round(float(np.max(valid)), 4),
            "jitter": round(float(np.mean(jitter)), 4)}


def main(portrait, clip, models, mesh_model):
    matrices = json.loads(Path(clip).with_suffix(".truth.json").read_text())["matrices"]
    recognizer = session(Path(models)/"arcface_w600k_r50.onnx", 4)
    detector = cv2.FaceDetectorYN.create(str(Path(models)/"face_detection_yunet_2023mar.onnx"), "", (320, 320), .78)
    still = cv2.imread(str(portrait))
    seed = detect_faces(still, detector, thorough=True)[0]
    frames = [frame.to_ndarray(format="bgr24") for frame in av.open(str(clip)).decode(video=0)]
    detections = [detect_faces(image, detector) for image in frames]

    old = FaceTrack(0, recognizer)
    previous = [old.update(image, faces) for image, faces in zip(frames, detections)]
    previous = [None if face is None else face[4:14].reshape(5, 2) for face in previous]
    results = {"per_frame_tracker": score(previous, seed[4:14].reshape(5, 2), matrices)}

    with create_mesh_detector(mesh_model) as mesh:
        reference, _ = mesh_five(still, seed[4:14].reshape(5, 2), mesh)
        tracker = ActionTracker(recognizer, mesh)
        records = [tracker.step(image, faces) for image, faces in zip(frames, detections)]
    raw = [record["points"] for record in records]
    smoothed = [points for points, _ in smooth_track(records, 30)]
    results["action_tracker_unsmoothed"] = score(raw, reference, matrices)
    results["action_tracker"] = score(smoothed, reference, matrices)
    results["action_tracker_stats"] = tracker.stats
    results["detector_frames"] = sum(bool(len(faces)) for faces in detections)

    # Detector dropouts during the shake and the blurred whip: the earlier
    # tracker leaves those frames unswapped, the action tracker carries them.
    dropped = [[] if 30 <= index < 40 or 80 <= index < 88 else faces for index, faces in enumerate(detections)]
    old = FaceTrack(0, recognizer)
    previous = [old.update(image, faces) for image, faces in zip(frames, dropped)]
    previous = [None if face is None else face[4:14].reshape(5, 2) for face in previous]
    results["dropout_per_frame_tracker"] = score(previous, seed[4:14].reshape(5, 2), matrices)
    with create_mesh_detector(mesh_model) as mesh:
        tracker = ActionTracker(recognizer, mesh)
        records = [tracker.step(image, faces) for image, faces in zip(frames, dropped)]
    results["dropout_action_tracker"] = score([points for points, _ in smooth_track(records, 30)], reference, matrices)
    results["dropout_action_tracker_stats"] = tracker.stats
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])

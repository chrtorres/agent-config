"""Generate a green preview from the same semantic mask used for compositing."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from face_models import read_photo, session
from face_swap_video import face_at_point, mapped_face_mask
from fetch_face_models import MODELS, file_hash


def preview(source, output, models, x, y, mesh_model=None):
    detector_file, parser_file = (models / name for name in (
        "face_detection_yunet_2023mar.onnx", "bisenet_resnet_18.onnx"))
    for path in (detector_file, parser_file):
        if not path.is_file() or file_hash(path) != MODELS[path.name][1]:
            raise ValueError("Face Swap models are unavailable. See the setup instructions.")
    cv2.setNumThreads(2)
    image, _ = read_photo(source)
    detector = cv2.FaceDetectorYN.create(str(detector_file), "", (320, 320), .78)
    face = face_at_point(image, (x, y), detector)
    crop, matrix, alpha = mapped_face_mask(image, face, session(parser_file), fallback=True)
    if not alpha.any():
        raise ValueError("The selected face could not be masked. Choose a clearer frame.")
    if mesh_model is not None:
        from face_curvature import depth_bands, landmarks
        points = landmarks(crop, mesh_model)
        layers = depth_bands(points, crop.shape[1::-1], cv2.invertAffineTransform(matrix), alpha)
        output.write_text(json.dumps(layers, separators=(",", ":")))
        return
    overlay = np.empty((*alpha.shape, 4), np.uint8)
    overlay[..., :3] = [44, 240, 113]
    overlay[..., 3] = np.rint(alpha * .51).astype(np.uint8)
    Image.fromarray(overlay).save(output, "PNG")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output", "models"):
        cli.add_argument(name, type=Path)
    cli.add_argument("x", type=float)
    cli.add_argument("y", type=float)
    cli.add_argument("--curvature-model", type=Path)
    args = cli.parse_args()
    try:
        preview(args.source, args.output, args.models, args.x, args.y, args.curvature_model)
    except (ValueError, OSError) as error:
        cli.exit(1, f"{error}\n")

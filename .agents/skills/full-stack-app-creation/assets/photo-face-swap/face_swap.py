"""Generate a local face composite and lossless verification artifacts."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw, ImageOps


# FaceFusion's ArcFace templates, normalized to the model crop width.
ARCFACE_112 = np.array([
    [0.34191607, 0.46157411], [0.65653393, 0.45983393],
    [0.50022500, 0.64050536], [0.37097589, 0.82469196],
    [0.63151696, 0.82325089],
], dtype=np.float32)
ARCFACE_128 = np.array([
    [0.36167656, 0.40387734], [0.63696719, 0.40235469],
    [0.50019687, 0.56044219], [0.38710391, 0.72160547],
    [0.61507734, 0.72034453],
], dtype=np.float32)
MODELS = Path(__file__).resolve().parent / "models"
FACE_LABELS = (1, 2, 3, 4, 5, 10, 11, 12, 13)


def read_photo(path):
    with Image.open(path) as image:
        rgb = np.array(ImageOps.exif_transpose(image).convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), image.info.get("icc_profile")


def select_face(image, model, index, role):
    height, width = image.shape[:2]
    scale = min(1.0, 1800 / max(height, width))
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    detector = cv2.FaceDetectorYN.create(str(model), "", small.shape[1::-1], 0.8)
    _, faces = detector.detect(small)
    if faces is None:
        raise ValueError(f"No face detected in the {role} image.")
    faces = faces[np.argsort(faces[:, 0] + faces[:, 2] / 2)]
    if index is None and len(faces) != 1:
        raise ValueError(f"{len(faces)} faces detected in the {role} image. "
                         f"Set --{role}-index from left to right, starting at zero.")
    index = 0 if index is None else index
    if index < 0 or index >= len(faces):
        raise ValueError(f"Invalid {role} face index {index} for {len(faces)} detected faces.")
    face = faces[index].copy()
    factors = np.array([width / small.shape[1], height / small.shape[0]])
    face[:14] *= np.tile(factors, 7)
    return face, len(faces)


def aligned_crop(image, face, template, size):
    points = face[4:14].reshape(5, 2)
    matrix, _ = cv2.estimateAffinePartial2D(
        points, template * size, method=cv2.RANSAC, ransacReprojThreshold=100
    )
    if matrix is None:
        raise ValueError("The facial landmarks could not be aligned.")
    crop = cv2.warpAffine(image, matrix, (size, size), borderMode=cv2.BORDER_REPLICATE)
    return crop, matrix


def session(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing model {path.name}. Run fetch_models.py first.")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])


def rgb_tensor(crop):
    return crop[:, :, ::-1].astype(np.float32).transpose(2, 0, 1)[None] / 255


def encode(recognizer, crop):
    tensor = rgb_tensor(crop) * 2 - 1
    vector = recognizer.run(None, {recognizer.get_inputs()[0].name: tensor})[0]
    return vector / np.linalg.norm(vector)


def render(swapper, crop, identity):
    feed = {"target": rgb_tensor(crop) * 2 - 1, "source": identity}
    for item in swapper.get_inputs():
        if item.type == "tensor(float16)":
            feed[item.name] = feed[item.name].astype(np.float16)
    pred = swapper.run(None, feed)[0][0].astype(np.float32)
    return np.clip(pred.transpose(1, 2, 0)[:, :, ::-1] * 127.5 + 127.5, 0, 255)


def face_mask(parser, crop, feather):
    tensor = rgb_tensor(cv2.resize(crop, (512, 512)))
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)[None, :, None, None]
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)[None, :, None, None]
    logits = parser.run(None, {parser.get_inputs()[0].name: (tensor - mean) / std})[0][0]
    labels = logits.argmax(0).astype(np.uint8)
    labels = cv2.resize(labels, crop.shape[1::-1], interpolation=cv2.INTER_NEAREST)
    region = np.isin(labels, FACE_LABELS).astype(np.uint8)
    region = cv2.morphologyEx(region, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    # Remove stray islands and feather inward so the transition stays in the face.
    count, components, stats, _ = cv2.connectedComponentsWithStats(region)
    if count < 2:
        raise ValueError("The target face mask is empty.")
    main = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    region = (components == main).astype(np.uint8)
    region[[0, -1], :] = 0
    region[:, [0, -1]] = 0
    distance = cv2.distanceTransform(region, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    alpha = np.clip(distance / feather, 0, 1)
    return alpha * alpha * (3 - 2 * alpha)


def transfer_source(parser, actor, actor_face, target, target_face, generated, matrix):
    size = 512
    actor_crop, _ = aligned_crop(actor, actor_face, ARCFACE_128, size)
    target_crop, target_matrix = aligned_crop(target, target_face, ARCFACE_128, size)
    source_alpha = face_mask(parser, actor_crop, 45)
    target_alpha = face_mask(parser, target_crop, 45)
    overlap = np.minimum(source_alpha, target_alpha)
    support = (overlap > 0.6).astype(np.float32)
    if not np.any(support):
        raise ValueError("The aligned source and target face masks do not overlap.")

    source_lab = cv2.cvtColor(actor_crop.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    target_lab = cv2.cvtColor(target_crop.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    # A mask-normalized low-pass filter estimates broad lighting differences
    # without drawing color from the hair, background, or crop boundaries.
    numerator = cv2.GaussianBlur((target_lab - source_lab) * support[..., None], (0, 0), 31)
    denominator = cv2.GaussianBlur(support, (0, 0), 31)
    light_delta = numerator / np.maximum(denominator[..., None], 0.04)
    corrected_lab = source_lab + light_delta * np.array([0.72, 0.8, 0.8], dtype=np.float32)
    corrected = cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR) * 255
    # Map the generated crop into the higher-resolution landmark frame before
    # fading the photographed features into its pose-adapted boundary.
    crop_transform = target_matrix @ np.vstack((cv2.invertAffineTransform(matrix), [0, 0, 1]))
    base = cv2.warpAffine(generated, crop_transform, (size, size),
                          borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_CUBIC)
    blend = base + (corrected - base) * overlap[..., None]
    return blend.clip(0, 255), target_matrix


def to_pil(bgr):
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def save_review(path, actor, target, result, actor_face, bbox, icc):
    # Give both target panels the same native-pixel crop for visual comparison.
    left, top, width, height = bbox
    pad = round(max(width, height) * 0.2)
    x0, y0 = max(0, left - pad), max(0, top - pad)
    x1, y1 = left + width + pad, top + height + pad
    before = to_pil(target[y0:y1, x0:x1])
    after = to_pil(result[y0:y1, x0:x1])
    actor_context, _ = aligned_crop(actor, actor_face, ARCFACE_128, 320)
    panels = [("Source reference (aligned)", to_pil(actor_context)),
              ("Original", before), ("Face swap", after)]
    gap, header = 14, 34
    canvas = Image.new("RGB", (sum(panel.width for _, panel in panels) + gap * 4,
                               max(panel.height for _, panel in panels) + header + gap),
                       (27, 29, 32))
    draw = ImageDraw.Draw(canvas)
    x = gap
    for label, panel in panels:
        draw.text((x, 10), label, fill="white")
        canvas.paste(panel, (x, header))
        x += panel.width + gap
    canvas.save(path, icc_profile=icc)


def digest(path):
    with path.open("rb") as stream:
        result = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
        return result.hexdigest()


def run(args):
    if args.output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {args.output_dir}")
    actor, _ = read_photo(args.source)
    target, icc = read_photo(args.target)
    detector = args.models / "face_detection_yunet_2023mar.onnx"
    actor_face, actor_count = select_face(actor, detector, args.source_index, "source")
    target_face, target_count = select_face(target, detector, args.target_index, "target")

    recognizer = session(args.models / "arcface_w600k_r50.onnx")
    source_crop, _ = aligned_crop(actor, actor_face, ARCFACE_112, 112)
    identity = encode(recognizer, source_crop)
    target_crop, matrix = aligned_crop(target, target_face, ARCFACE_128, 256)
    generated = render(session(args.models / "hyperswap_1a_256.onnx"), target_crop, identity)
    parser = session(args.models / "bisenet_resnet_18.onnx")
    alpha_crop = face_mask(parser, target_crop, args.feather)
    texture_matrix = matrix
    if not args.model_only:
        generated, texture_matrix = transfer_source(
            parser, actor, actor_face, target, target_face, generated, matrix
        )
    size = target.shape[1::-1]
    inverse = cv2.invertAffineTransform(matrix)
    alpha = cv2.warpAffine(alpha_crop, inverse, size)
    alpha_u8 = np.rint(alpha * 255).astype(np.uint8)
    bbox = cv2.boundingRect(alpha_u8)
    left, top, width, height = bbox
    if width == 0 or height == 0:
        raise ValueError("The final face mask does not overlap the target image.")
    area = np.s_[top:top + height, left:left + width]
    texture_inverse = cv2.invertAffineTransform(texture_matrix)
    texture_inverse[:, 2] -= [left, top]
    overlay = cv2.warpAffine(generated, texture_inverse, (width, height),
                             borderMode=cv2.BORDER_REPLICATE)
    weight = alpha_u8[area][..., None].astype(np.float32) / 255
    result = target.copy()
    result[area] = np.rint(target[area] + (overlay - target[area]) * weight).astype(np.uint8)
    args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    output = args.output_dir / "face-swap.png"
    to_pil(result).save(output, icc_profile=icc)
    Image.fromarray(alpha_u8).save(args.output_dir / "face-mask.png")
    save_review(args.output_dir / "comparison.png", actor, target, result,
                actor_face, bbox, icc)

    decoded, _ = read_photo(output)
    if decoded.shape != target.shape:
        raise ValueError("The saved output has different dimensions from the target.")
    changed = np.any(decoded != target, axis=2)
    outside = int(np.count_nonzero(changed & (alpha_u8 == 0)))
    if outside or not np.any(changed):
        raise ValueError("The saved output failed the dimension or localized edit check.")
    notes = {
        "dimensions_px": list(size),
        "source_faces": actor_count,
        "target_faces": target_count,
        "source_detector_score": float(actor_face[14]),
        "target_detector_score": float(target_face[14]),
        "target_landmarks_px": target_face[4:14].reshape(5, 2).tolist(),
        "mask_bbox_xywh_px": bbox,
        "mask_pixels": int(np.count_nonzero(alpha_u8)),
        "pixels_changed": int(np.count_nonzero(changed)),
        "pixels_changed_outside_mask": outside,
        "feather_model_px": args.feather,
        "source_texture_transfer": not args.model_only,
        "output_sha256": digest(output),
    }
    (args.output_dir / "verification.json").write_text(json.dumps(notes, indent=2) + "\n")
    print(json.dumps(notes, indent=2))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", required=True, type=Path, help="Source reference photo")
    cli.add_argument("--target", required=True, type=Path, help="Photo to edit")
    cli.add_argument("--output-dir", required=True, type=Path, help="New directory for outputs")
    cli.add_argument("--models", type=Path, default=MODELS)
    cli.add_argument("--source-index", type=int)
    cli.add_argument("--target-index", type=int)
    cli.add_argument("--feather", type=float, default=12)
    cli.add_argument("--model-only", action="store_true",
                     help="Render a baseline without blending photographed source texture")
    args = cli.parse_args()
    if not np.isfinite(args.feather) or args.feather <= 0:
        cli.error("--feather must be a finite positive number")
    try:
        run(args)
    except (OSError, ValueError, cv2.error, ort.capi.onnxruntime_pybind11_state.RuntimeException) as exc:
        cli.exit(1, f"Face swap failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())

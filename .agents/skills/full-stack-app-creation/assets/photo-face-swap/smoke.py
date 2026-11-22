"""Exercise real CPU inference twice on fictional portraits in a fresh directory."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

from fetch_models import file_hash


HERE = Path(__file__).resolve().parent
ARTIFACTS = ("face-swap.png", "face-mask.png", "comparison.png", "verification.json")


def invoke(script, arguments, expected=0, message=None):
    command = [sys.executable, "-B", str(HERE / script), *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != expected or (message and message not in result.stderr):
        raise RuntimeError(f"{command!r} returned {result.returncode}\n{result.stdout}{result.stderr}")
    return {"command": command, "exit_code": result.returncode, "stderr": result.stderr}


def pixels(path, mode):
    with Image.open(path) as image:
        return np.array(image.convert(mode))


def verify(target, directory):
    output = pixels(directory / "face-swap.png", "RGB")
    mask = pixels(directory / "face-mask.png", "L")
    assert output.shape == target.shape and mask.shape == target.shape[:2]
    changed = np.any(output != target, axis=2)
    count = int(np.count_nonzero(changed))
    assert count > 0 and not np.any(changed & (mask == 0))
    meta = json.loads((directory / "verification.json").read_text())
    assert meta["pixels_changed"] == count
    assert meta["pixels_changed_outside_mask"] == 0
    assert meta["source_faces"] == meta["target_faces"] == 1
    assert meta["output_sha256"] == file_hash(directory / "face-swap.png")
    with Image.open(directory / "comparison.png") as image:
        image.verify()
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=HERE / "models")
    parser.add_argument("--work-dir", type=Path, required=True)
    options = parser.parse_args()
    work = options.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    fixture = work / "fixture"
    run = work / "first"
    repeat = work / "repeat"
    baseline = work / "baseline"
    checks = {"fixture": invoke("make_fixture.py", [fixture])}
    source = fixture / "source.png"
    target = fixture / "target.png"
    original_target = file_hash(target)
    args = ["--models", options.models.resolve(), "--source", source, "--target", target]
    for label, dest in (("first", run), ("repeat", repeat)):
        checks[label] = invoke("face_swap.py", [*args, "--output-dir", dest])
    checks["baseline"] = invoke(
        "face_swap.py", [*args, "--output-dir", baseline, "--model-only"]
    )
    target_pixels = pixels(target, "RGB")
    assert verify(target_pixels, run)["source_texture_transfer"]
    assert not verify(target_pixels, baseline)["source_texture_transfer"]
    assert file_hash(run / "face-mask.png") == file_hash(baseline / "face-mask.png")
    assert file_hash(run / "face-swap.png") != file_hash(baseline / "face-swap.png")
    hashes = {name: file_hash(run / name) for name in ARTIFACTS}
    assert hashes == {name: file_hash(repeat / name) for name in ARTIFACTS}
    bad_index = work / "invalid"
    checks["invalid_index"] = invoke(
        "face_swap.py", [*args, "--output-dir", bad_index, "--target-index", 1],
        expected=1, message="Invalid target face index",
    )
    missing = work / "missing"
    checks["missing_input"] = invoke(
        "face_swap.py", [*args, "--output-dir", missing, "--source", work / "absent.png"],
        expected=1, message="No such file",
    )
    checks["existing_output"] = invoke(
        "face_swap.py", [*args, "--output-dir", run], expected=1,
        message="Output directory already exists",
    )
    checks["missing_comparison"] = invoke(
        "open_review.py", [work], expected=2, message="Comparison PNG is missing",
    )
    assert not bad_index.exists() and not missing.exists()
    assert hashes == {name: file_hash(run / name) for name in ARTIFACTS}
    assert original_target == file_hash(target)
    (work / "checks.json").write_text(json.dumps({
        "checks": checks, "reproduced_sha256": hashes, "python": sys.version,
    }, indent=2) + "\n")
    print("CPU compositing, pixel preservation, repeatability, baseline, and error checks passed.")


if __name__ == "__main__":
    main()

"""Exercise GPU allocation recovery at the worker entry point with fictional media."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixtures", "face_models", "mesh_model"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    worker = Path(__file__).resolve().parents[1] / "tools/face_swap_video.py"
    with TemporaryDirectory() as directory:
        work = Path(directory)
        # The subprocess imports this module at startup and again after execve.
        # Only the CUDA allocation is simulated. CPU inference and verification run normally.
        (work/"sitecustomize.py").write_text("""
from pathlib import Path
import onnxruntime as ort
from onnxruntime.capi.onnxruntime_pybind11_state import RuntimeException

original = ort.InferenceSession
ort.get_available_providers = lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
ort.preload_dlls = lambda **kwargs: None
def session(*args, providers=None, **kwargs):
    if "CUDAExecutionProvider" in providers:
        (Path(__file__).parent/"attempted-gpu").touch()
        raise RuntimeException("Failed to allocate memory for requested buffer")
    return original(*args, providers=providers, **kwargs)
ort.InferenceSession = session
""")
        env = {**os.environ, "PYTHONPATH": directory, "FOOTAGE_FACE_CPU": "0"}
        subprocess.run([sys.executable, "-B", worker, args.fixtures/"source.png",
                        args.fixtures/"target.mp4", work, args.face_models, "--mesh-model",
                        args.mesh_model, "--target-point", "0", ".5", ".5", "--preview"],
                       env=env, timeout=240, check=True)
        report = json.loads((work/"verification.json").read_text())
        assert (work/"attempted-gpu").is_file() and (work/"preview.mp4").stat().st_size
        assert report["frames"] == 12 and report["swapped"] > 0
        assert report["video"] == report["audio"] == "verified"
        assert report["outside_mask"] == "byte exact"


if __name__ == "__main__":
    main()

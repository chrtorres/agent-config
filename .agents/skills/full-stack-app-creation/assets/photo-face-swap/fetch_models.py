"""Fetch and verify the exact ONNX files used by face_swap.py."""

import argparse
from hashlib import sha256
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

ASSETS = "https://github.com/facefusion/facefusion-assets/releases/download/"
ZOO = ("https://media.githubusercontent.com/media/opencv/opencv_zoo/"
       "48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_detection_yunet/")
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        ZOO, "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
    ),
    "arcface_w600k_r50.onnx": (
        ASSETS + "models-3.0.0/", "f1f79dc3b0b79a69f94799af1fffebff09fbd78fd96a275fd8f0cbbea23270d1"
    ),
    "hyperswap_1a_256.onnx": (
        ASSETS + "models-3.3.0/", "c0e98a8a03a238f461ed3d2570e426b49f46745ee400854a60dceeb70c246add"
    ),
    "bisenet_resnet_18.onnx": (
        ASSETS + "models-3.1.0/", "2218b6183c26ca5c83303232d682a536c670c13ea9695f716c777d1f244eefe9"
    ),
}
CHUNK_SIZE = 1024 * 1024


def file_hash(path):
    with path.open("rb") as source:
        digest = sha256()
        for block in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(block)
        return digest.hexdigest()


def fetch(destination, url, expected):
    if destination.exists():
        if file_hash(destination) != expected:
            raise ValueError(f"Checksum mismatch for {destination}. Move the file aside and retry.")
        return
    with NamedTemporaryFile(dir=destination.parent, delete=False) as saved:
        partial = Path(saved.name)
        try:
            digest = sha256()
            with urlopen(url, timeout=60) as source:
                for block in iter(lambda: source.read(CHUNK_SIZE), b""):
                    saved.write(block)
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise ValueError(f"Checksum mismatch for download {destination.name}.")
            saved.close()
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--models", default=Path(__file__).resolve().parent / "models", type=Path)
    args = cli.parse_args()
    try:
        args.models.mkdir(mode=0o700, parents=True, exist_ok=True)
        for name, (url, expected) in MODELS.items():
            fetch(args.models / name, url + name, expected)
            print(f"Verified {name}", flush=True)
    except (OSError, ValueError) as exc:
        cli.exit(1, f"Model setup failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())

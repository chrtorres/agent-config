"""Prepare a self-contained material-variant study and generate its Blender assets."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1] / "assets" / "material-variant-example"
VARIANTS = {
    "kohaku": "Kōhaku",
    "sanke": "Taishō Sanke",
    "showa": "Shōwa Sanshoku",
    "asagi": "Asagi",
    "ogon": "Yamabuki Ōgon",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=["kohaku", "asagi"])
    parser.add_argument("--texture-width", type=int, choices=(512, 1024, 2048, 4096), default=4096)
    parser.add_argument("--preview-percent", type=int, default=100)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--threads", type=int, default=3)
    args = parser.parse_args()
    if len(set(args.variants)) != len(args.variants) or len(args.variants) < 2:
        parser.error("--variants needs at least two distinct variants")
    if not 25 <= args.preview_percent <= 100 or min(args.samples, args.threads) < 1:
        parser.error("preview percent must be 25–100 and samples and threads must be positive")
    blender = shutil.which(args.blender)
    if not blender:
        parser.error("Blender executable unavailable")
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=False)
    for name in ("source", "review"):
        shutil.copytree(BUNDLE / name, target / name, ignore=shutil.ignore_patterns("__pycache__"))
    (target / "evidence").mkdir()
    (target / "review" / "catalog.json").write_text(json.dumps({
        "title": "Nishikigoi",
        "variants": [{"slug": slug, "label": VARIANTS[slug]} for slug in args.variants],
        "detail": {"label": "Head detail", "min": [0, .23, .25], "max": [.24, .84, .84],
                   "direction": [-.72, .50, 1]},
    }, ensure_ascii=False, indent=2) + "\n")
    for slug in args.variants:
        destination = target / "variants" / slug
        prefix = [blender, "-b", "--factory-startup", "-t", str(args.threads), "--python-exit-code", "1", "--python"]
        commands = [
            [*prefix, str(target / "source/nishikigoi.py"), "--", "--version", args.version,
             "--variety", slug, "--output", str(destination), "--texture-width", str(args.texture_width),
             "--preview-percent", str(args.preview_percent), "--samples", str(args.samples)],
            [*prefix, str(target / "source/verify_asset.py"), "--", str(destination)],
        ]
        with (target / "evidence" / (slug + ".log")).open("w") as log:
            for command in commands:
                print(json.dumps(command), file=log, flush=True)
                subprocess.run(command, check=True, cwd=target, stdout=log, stderr=subprocess.STDOUT)
        print(f"Built and verified {slug}", flush=True)


if __name__ == "__main__":
    main()

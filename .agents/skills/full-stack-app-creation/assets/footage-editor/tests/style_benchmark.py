"""Score style learning, matching and rendering on synthetic camera clips.

Learns every clip from make_style_clips.py, prints the match between each
pair, then renders each clip in every other camera's style and reports how
closely the result measures like that style. Same-shoot pairs should match at
or above the threshold and different cameras well below it.

Usage: style_benchmark.py <work-directory> [<squeezenet1.1-7.onnx>]
"""
from itertools import combinations
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
import make_style_clips  # noqa: E402
import recording_style as rs  # noqa: E402


def main(directory, model=None):
    directory = Path(directory)
    clips = directory/"clips"
    make_style_clips.main(clips)
    profiles = {path.stem: rs.analyse(path, style_model=model) for path in sorted(clips.glob("*.mp4"))}
    pairs = {f"{a} vs {b}": rs.similarity(profiles[a], profiles[b])[0] for a, b in combinations(profiles, 2)}
    renders = {}
    for source in profiles:
        for style in profiles:
            if source.split("-")[0] == style.split("-")[0] or style.endswith("b"):
                continue
            output = directory/f"{source}-as-{style}.mp4"
            report = rs.apply(clips/f"{source}.mp4", profiles[style], output, style_model=model)
            renders[f"{source} in the style of {style}"] = {"match": report["match"], "groups": report["groups"]}
    results = {"threshold": rs.MATCH_THRESHOLD, "pairs": pairs, "renders": renders}
    (directory/"results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])

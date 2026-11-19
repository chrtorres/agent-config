"""Compare the exact material-variant GLB geometry and pigment payloads."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def inspect(path):
    with path.open("rb") as asset:
        magic, schema, total, count, kind = struct.unpack("<4sIII4s", asset.read(20))
        if (magic, schema, total, kind) != (b"glTF", 2, path.stat().st_size, b"JSON"):
            raise ValueError(f"Invalid GLB at {path}")
        document = json.loads(asset.read(count))
        count, kind = struct.unpack("<I4s", asset.read(8))
        if kind != b"BIN\0":
            raise ValueError(f"Missing binary payload at {path}")
        data = memoryview(asset.read(count))

    def view(index):
        desc = document["bufferViews"][index]
        start = desc.get("byteOffset", 0)
        return data[start:start+desc["byteLength"]]

    # This check targets exports from the bundled Blender generator. Layout changes
    # such as interleaving or compression require decoding accessors before comparison.
    geometry = hashlib.sha256()
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            for index in (primitive["attributes"]["POSITION"], primitive["indices"]):
                accessor = document["accessors"][index]
                descriptor = document["bufferViews"][accessor["bufferView"]]
                if descriptor.get("byteStride") or accessor.get("byteOffset") or "sparse" in accessor:
                    raise ValueError("Expected tightly packed accessors")
                geometry.update(view(accessor["bufferView"]))
    material = next(m for m in document["materials"] if m["name"].startswith("Skin • "))
    pbr = material["pbrMetallicRoughness"]
    textures = {}
    for key, texture in (("pigment", pbr["baseColorTexture"]), ("surface", pbr["metallicRoughnessTexture"]),
                         ("normal", material["normalTexture"])):
        image = document["images"][document["textures"][texture["index"]]["source"]]
        textures[key] = hashlib.sha256(view(image["bufferView"])).hexdigest()
    return {"geometry": geometry.hexdigest(), **textures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", type=Path)
    args = parser.parse_args()
    entries = json.loads((args.version / "review/catalog.json").read_text())["variants"]
    if len({entry["slug"] for entry in entries}) < 2:
        parser.error("At least two distinct variants are required")
    results = {entry["slug"]: inspect(args.version / "variants" / entry["slug"] / "review/model.glb")
               for entry in entries}
    if len({value["geometry"] for value in results.values()}) != 1:
        raise SystemExit("Variant geometry buffers differ")
    if len({value["pigment"] for value in results.values()}) != len(results):
        raise SystemExit("Expected a distinct material map in every variant")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

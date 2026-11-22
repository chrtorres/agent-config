"""Behavioural tests for the robot-description helpers (no Blender or ROS needed).

    python3 -m unittest tests/test_robot_description_tools.py -v
"""
import importlib.util
import json
import shutil
import struct
import tempfile
import unittest

try:
    import numpy  # noqa: F401  compare_glb_exports needs it
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/robot-description"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failures(results):
    return [label for ok, label in results if not ok]


def write_glb(path, animations, positions=(0, 0, 0, 1, 0, 0, 0, 1, 0)):
    """Smallest GLB with one triangle mesh, two nodes and the given animations."""
    binary = struct.pack(f"<{len(positions)}f", *positions) + struct.pack("<3H", 0, 1, 2) + b"\0\0"
    gltf = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(binary)}],
            "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
                            {"buffer": 0, "byteOffset": 36, "byteLength": 6}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                          {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"}],
            "meshes": [{"name": "tri", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "nodes": [{"name": "a", "mesh": 0}, {"name": "b", "translation": [0, 1, 0]}],
            "animations": animations}
    chunk = json.dumps(gltf).encode()
    chunk += b" " * (-len(chunk) % 4)
    body = struct.pack("<I4s", len(chunk), b"JSON") + chunk + struct.pack("<I4s", len(binary), b"BIN\0") + binary
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


class CheckUrdfTests(unittest.TestCase):
    def setUp(self):
        self.check = load("check_urdf")
        self.expect = json.loads((FIXTURE / "expect.json").read_text())
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def mutate(self, old, new):
        text = (FIXTURE / "two_wheel.urdf").read_text()
        self.assertIn(old, text)  # an unapplied mutation would be a false "detected"
        path = self.tmp / "robot.urdf"
        path.write_text(text.replace(old, new, 1))
        return self.check.run(path, expect=self.expect)

    def test_fixture_passes(self):
        self.assertEqual(failures(self.check.run(FIXTURE / "two_wheel.urdf", expect=self.expect)), [])

    def test_raised_wheel_detected(self):
        self.assertTrue(any("left_wheel: touches" in f for f in failures(self.mutate('xyz="0 0.12 0"', 'xyz="0 0.12 0.001"'))))

    def test_flipped_sensor_detected(self):
        self.assertIn("side_sensor_frame: orientation", failures(self.mutate('rpy="0 0 -1.5707963267949"', 'rpy="0 0 1.5707963267949"')))

    def test_mass_change_detected(self):
        self.assertTrue(any("total mass" in f for f in failures(self.mutate('<mass value="0.1"/>', '<mass value="0.2"/>'))))

    def test_bad_inertia_detected(self):
        bad = failures(self.mutate('ixx="0.02" iyy="0.02" izz="0.03"', 'ixx="0.02" iyy="0.02" izz="0.05"'))
        self.assertIn("base_link: inertia triangle inequality", bad)

    def test_com_behind_axle_detected(self):
        bad = failures(self.mutate('<origin xyz="0.01 0 0.02"/>', '<origin xyz="-0.03 0 0.02"/>'))
        self.assertTrue(any("support polygon" in f for f in bad))

    def test_missing_mesh_detected(self):
        bad = failures(self.mutate('<link name="lid"/>',
                                   '<link name="lid"><visual><geometry><mesh filename="package://pkg/meshes/lid.dae"/></geometry></visual></link>'))
        self.assertTrue(any("mesh resolves" in f for f in bad))


class GlbToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.anims = [{"name": f"obj{i}", "samplers": [{"input": 0, "output": 0}],
                       "channels": [{"sampler": 0, "target": {"node": i, "path": "rotation"}}]} for i in range(2)]

    def test_merge_renumbers_samplers(self):
        path = self.tmp / "m.glb"
        write_glb(path, self.anims)
        before = path.read_bytes()[-44:]
        self.assertEqual(load("merge_glb_animations").merge(path, "Joint exercise"), 2)
        data = path.read_bytes()
        n = struct.unpack_from("<I", data, 12)[0]
        gltf = json.loads(data[20:20 + n])
        self.assertEqual([a["name"] for a in gltf["animations"]], ["Joint exercise"])
        self.assertEqual([c["sampler"] for c in gltf["animations"][0]["channels"]], [0, 1])
        self.assertEqual(struct.unpack_from("<I", data, 8)[0], len(data))
        self.assertEqual(data[-44:], before)  # binary chunk untouched

    def test_merge_rejects_unanimated(self):
        path = self.tmp / "e.glb"
        write_glb(path, [])
        with self.assertRaises(ValueError):
            load("merge_glb_animations").merge(path, "x")

    @unittest.skipUnless(HAVE_NUMPY, "numpy not installed")
    def test_compare_ignores_triangle_order_but_not_geometry(self):
        compare = load("compare_glb_exports").compare
        a, b, c = self.tmp / "a.glb", self.tmp / "b.glb", self.tmp / "c.glb"
        write_glb(a, self.anims)
        write_glb(b, self.anims, positions=(1, 0, 0, 0, 1, 0, 0, 0, 0))  # same triangle, rotated order
        write_glb(c, self.anims, positions=(0, 0, 0, 2, 0, 0, 0, 1, 0))
        self.assertTrue(all(ok for ok, _ in compare(a, b)))
        self.assertFalse(compare(a, c)[0][0])


if __name__ == "__main__":
    unittest.main()

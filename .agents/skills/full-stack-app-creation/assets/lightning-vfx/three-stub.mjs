// A minimal Three.js stand-in: just enough of the buffer-geometry, material and scene-graph
// surface that lightning.js and crown.js touch, so their buffer math and pooling can be tested
// without installing three. It is not a renderer; shader strings are stored, never compiled.
export const AdditiveBlending = 2;
export const DoubleSide = 2;

class BufferAttribute {
  constructor(array, itemSize) { this.array = array; this.itemSize = itemSize; this.count = array.length / itemSize; this.needsUpdate = false; this.usage = 0; }
  setUsage(u) { this.usage = u; return this; }
  set(values, offset = 0) { this.array.set(values, offset); }
  getX(i) { return this.array[i * this.itemSize]; }
  getY(i) { return this.array[i * this.itemSize + 1]; }
  getZ(i) { return this.array[i * this.itemSize + 2]; }
}
export { BufferAttribute };
export class Float32BufferAttribute extends BufferAttribute {
  constructor(array, itemSize) { super(array instanceof Float32Array ? array : new Float32Array(array), itemSize); }
}
export const DynamicDrawUsage = 35048;

export class BufferGeometry {
  constructor() { this.attributes = {}; this.index = null; this.drawRange = { start: 0, count: Infinity }; this.disposed = false; }
  setAttribute(name, attr) { this.attributes[name] = attr; return this; }
  getAttribute(name) { return this.attributes[name]; }
  setIndex(attr) { this.index = attr instanceof BufferAttribute ? attr : new BufferAttribute(Uint32Array.from(attr), 1); return this; }
  setDrawRange(start, count) { this.drawRange = { start, count }; }
  computeBoundingSphere() {}
  computeVertexNormals() {}
  dispose() { this.disposed = true; }
}
export class RingGeometry extends BufferGeometry {}
export class SphereGeometry extends BufferGeometry {}

export class Color { constructor(hex = 0) { this.set(hex); } set(hex) { this.hex = typeof hex === "string" ? hex : hex; return this; } }
class Material { constructor(o = {}) { Object.assign(this, o); this.disposed = false; } dispose() { this.disposed = true; } }
export class ShaderMaterial extends Material {}
export class MeshBasicMaterial extends Material {}

export class Vector2 { constructor(x = 0, y = 0) { this.x = x; this.y = y; } }
export class Vector3 {
  constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  copy(v) { return this.set(v.x, v.y, v.z); }
}

class Object3D {
  constructor() { this.children = []; this.parent = null; this.visible = true; this.name = ""; this.position = new Vector3(); this.rotation = { x: 0, y: 0, z: 0 }; this.userData = {}; this.scale = new Vector3(1, 1, 1); this.frustumCulled = true; this.castShadow = this.receiveShadow = false; }
  add(child) { child.parent = this; this.children.push(child); return this; }
  removeFromParent() { if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this); this.parent = null; return this; }
  getWorldPosition(target) {
    let x = 0, y = 0, z = 0, node = this;
    while (node) { x += node.position.x; y += node.position.y; z += node.position.z; node = node.parent; }
    return target.set(x, y, z);
  }
}
export class Group extends Object3D {}
export class Scene extends Object3D {}
export class Mesh extends Object3D {
  constructor(geometry, material) { super(); this.geometry = geometry; this.material = material; }
}
// scale.setScalar is used on scorch rings.
Vector3.prototype.setScalar = function (s) { return this.set(s, s, s); };

export default {
  AdditiveBlending, DoubleSide, DynamicDrawUsage,
  BufferAttribute, Float32BufferAttribute, BufferGeometry, RingGeometry, SphereGeometry,
  Color, ShaderMaterial, MeshBasicMaterial, Vector2, Vector3, Group, Scene, Mesh,
};

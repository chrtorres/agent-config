import * as THREE from "three";
import { OrbitControls } from "./vendor/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "./vendor/examples/jsm/loaders/GLTFLoader.js";

const host = document.querySelector("#viewer");
const loading = document.querySelector("#loading");
const selector = document.querySelector("#variety");
const wireframe = document.querySelector("#wireframe");
const spin = document.querySelector("#autoRotate");
const detailButton = document.querySelector("#detail");
let catalog;
try {
  const result = await fetch("catalog.json");
  if (!result.ok) throw new Error(`Catalog: HTTP ${result.status}`);
  catalog = await result.json();
  if (!catalog.variants.length || catalog.variants.length !== new Set(catalog.variants.map(({slug}) => slug)).size ||
      catalog.variants.some(({slug,label}) => !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || typeof label !== "string")) {
    throw new Error("Catalog requires distinct URL-safe slugs and text labels.");
  }
} catch (error) {
  loading.textContent = "Could not load the variant catalog.";
  throw error;
}
const options = new Map(catalog.variants.map(({slug,label}) => [slug,label]));
for (const [slug,label] of options) selector.add(new Option(label,slug));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 2000);
const defaultDirection = new THREE.Vector3(-0.45, 0.86, 1.45).normalize();
camera.position.copy(defaultDirection);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 0.91;
host.appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xf3faff, 0x68625c, 1.8));
const key = new THREE.DirectionalLight(0xffefdc, 2.55); key.position.set(-220, 320, 420); scene.add(key);
const rim = new THREE.DirectionalLight(0xcde6ed, 1.6); rim.position.set(130, 230, -320); scene.add(rim);
const fill = new THREE.DirectionalLight(0xfff5ed, 0.55);
fill.position.set(-350, -90, -260);
scene.add(fill);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.06; controls.enablePan = true;
controls.update();
let model = null;
let currentVariety = null;
let pending = null;
let needsFrame = true;
controls.addEventListener("change", () => { needsFrame = true; });
const materials = new Set();

function fitRenderer() {
  needsFrame = true;
  const rect = host.getBoundingClientRect();
  renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
  camera.aspect = rect.width / Math.max(1, rect.height); camera.updateProjectionMatrix();
}
function frameView(direction = defaultDirection, focus = null) {
  if (!model) return;
  needsFrame = true;
  const bounds = new THREE.Box3().setFromObject(model);
  if (focus) {
    // Each bound uses a fraction of the full GLB envelope along the corresponding axis.
    const origin = bounds.min.clone();
    const size = bounds.getSize(new THREE.Vector3());
    bounds.min.copy(origin).add(size.clone().multiply(new THREE.Vector3(...focus.min)));
    bounds.max.copy(origin).add(size.multiply(new THREE.Vector3(...focus.max)));
  }
  if (bounds.isEmpty()) return;

  const center = bounds.getCenter(new THREE.Vector3());
  const span = Math.max(1e-6, bounds.getSize(new THREE.Vector3()).length());
  // Stop residual drag or auto-rotation from overriding an explicit inspection angle.
  const damping = controls.enableDamping;
  const autoRotate = controls.autoRotate;
  controls.enableDamping = false;
  controls.autoRotate = false;
  controls.update();
  camera.position.copy(center).add(direction);
  camera.lookAt(center);
  const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
  const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);
  const vertical = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.85;
  const horizontal = vertical * camera.aspect;
  let distance = span * 0.6;
  for (const x of [bounds.min.x, bounds.max.x]) {
    for (const y of [bounds.min.y, bounds.max.y]) {
      for (const z of [bounds.min.z, bounds.max.z]) {
        const corner = new THREE.Vector3(x, y, z).sub(center);
        const padding = Math.max(Math.abs(corner.dot(right)) / horizontal, Math.abs(corner.dot(up)) / vertical);
        distance = Math.max(distance, corner.dot(direction) + padding);
      }
    }
  }

  controls.target.copy(center);
  controls.minDistance = span * 0.12;
  controls.maxDistance = distance * 4;
  camera.near = span / 1500;
  camera.far = controls.maxDistance + span;
  camera.position.copy(center).addScaledVector(direction, distance);
  camera.updateProjectionMatrix();
  controls.update();
  controls.enableDamping = damping;
  controls.autoRotate = autoRotate;
}

function renderMetadata(metadata) {
  document.querySelector("#title").textContent = metadata.title;
  document.querySelector("#status").textContent = metadata.status;
  document.querySelector("#note").textContent = metadata.note;
  const facts = document.querySelector("#facts");
  facts.replaceChildren();
  for (const [key, value] of Object.entries(metadata.facts || {})) {
    const row = document.createElement("div");
    const label = document.createElement("dt"); label.textContent = key;
    const detail = document.createElement("dd"); detail.textContent = value;
    row.append(label, detail); facts.appendChild(row);
  }
}

function dispose(asset) {
  const textures = new Set();
  const materialSet = new Set();
  asset.traverse((node) => {
    if (!node.isMesh) return;
    node.geometry.dispose();
    for (const material of [node.material].flat()) materialSet.add(material);
  });
  for (const material of materialSet) {
    for (const value of Object.values(material)) {
      if (value?.isTexture) textures.add(value);
    }
    material.dispose();
  }
  for (const texture of textures) {
    texture.source.data?.close?.();
    texture.dispose();
  }
}

function commitVariant(asset, metadata, slug, base) {
  const first = model === null;
  if (model) {
    scene.remove(model);
    dispose(model);
  }
  model = asset;
  materials.clear();
  model.traverse((node) => {
    if (node.isMesh) {
      for (const material of [node.material].flat()) materials.add(material);
    }
  });
  for (const material of materials) material.wireframe = wireframe.getAttribute("aria-pressed") === "true";
  scene.add(model);
  if (first) frameView();
  currentVariety = slug;
  renderMetadata(metadata);
  document.querySelector("#glb").href = new URL("model.glb", base);
  document.querySelector("#blend").href = new URL(`../${slug}.blend`, base);
  document.querySelector("#render").href = new URL("../preview/three-quarter.png", base);
  document.querySelector("#downloads").hidden = false;
  const url = new URL(location.href);
  url.searchParams.set("variety", slug);
  history.replaceState({}, "", url);
  host.dataset.variety = slug;
  loading.classList.add("hidden");
  needsFrame = true;
}

async function selectVariety(slug) {
  pending?.abort();
  if (slug === currentVariety) {
    loading.classList.add("hidden");
    return;
  }
  const request = new AbortController();
  pending = request;
  const base = new URL(`../variants/${slug}/review/`, location.href);
  loading.textContent = `Loading ${options.get(slug)}…`;
  loading.classList.remove("hidden");
  try {
    const get = async (name) => {
      const response = await fetch(new URL(name, base), { signal: request.signal });
      if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
      return response;
    };
    const [bytes, metadata] = await Promise.all([
      get("model.glb").then((response) => response.arrayBuffer()),
      get("metadata.json").then((response) => response.json()),
    ]);
    const { scene: asset } = await new GLTFLoader().parseAsync(bytes, base.href);
    // Decoding can complete after a later selection because glTF parsing itself is not abortable.
    if (request.signal.aborted) {
      dispose(asset);
      return;
    }
    commitVariant(asset, metadata, slug, base);
  } catch (error) {
    if (request.signal.aborted) return;
    loading.textContent = `Could not load ${options.get(slug)}. Select a variety to try again.`;
    if (currentVariety) selector.value = currentVariety;
    console.error(error);
  }
}

selector.addEventListener("change", () => selectVariety(selector.value));
document.querySelector("#reset").addEventListener("click", () => frameView());
// GLB uses Y up. A small offset keeps the overhead view off the orbit pole.
document.querySelector("#overhead").addEventListener("click", () => frameView(new THREE.Vector3(0,1,0.001).normalize()));
document.querySelector("#profile").addEventListener("click", () => frameView(new THREE.Vector3(0,0,1)));
if (catalog.detail) {
  detailButton.hidden = false;
  detailButton.textContent = catalog.detail.label;
  detailButton.addEventListener("click", () =>
    frameView(new THREE.Vector3(...catalog.detail.direction).normalize(), catalog.detail));
}
spin.addEventListener("click", (event) => {
  controls.autoRotate = !controls.autoRotate;
  event.currentTarget.setAttribute("aria-pressed", String(controls.autoRotate));
});
wireframe.addEventListener("click", (event) => {
  const enabled = event.currentTarget.getAttribute("aria-pressed") !== "true";
  event.currentTarget.setAttribute("aria-pressed", String(enabled));
  for (const material of materials) material.wireframe = enabled;
  needsFrame = true;
});
window.addEventListener("resize", () => {
  fitRenderer();
  frameView();
});
fitRenderer();

const requested = new URLSearchParams(location.search).get("variety");
selector.value = options.has(requested) ? requested : options.keys().next().value;
selectVariety(selector.value);

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  // Orbit damping can still advance each tick. Rasterize only when the view changes.
  if (needsFrame) {
    renderer.render(scene, camera);
    needsFrame = false;
  }
}
requestAnimationFrame(animate);

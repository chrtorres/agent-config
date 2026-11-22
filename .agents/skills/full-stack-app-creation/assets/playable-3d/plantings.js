import * as T from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

// Synthetic coordinates. Sample the same raised surface that the traversal fixture defines.
const deck = { x: 4, z: -4, halfWidth: 1, halfDepth: 1.7 };
const floor = (x, z) => Math.abs(x - deck.x) <= deck.halfWidth && Math.abs(z - deck.z) <= deck.halfDepth ? .75 : 0;
const layouts = [
  [[-2, 0, "rounded", 1, "marker"], [-4, -3, "spreading", .8, "grove"], [-2, -4, "pendant", 1.1, "grove"]],
  [[2, 0, "pendant", .83, "marker"], [3, -1, "rounded", .81, "grove"], [5.6, -1.1, "spreading", .92, "grove"]],
];

export function validateRoots(layout) {
  for (const [x, z] of layout) {
    for (const [dx, dz] of [[0, 0], [.3, 0], [-.3, 0], [0, .3], [0, -.3]]) {
      if (floor(x + dx, z + dz)) throw Error("Planting overlaps the raised deck");
    }
  }
}

export function createPlantings(scene) {
  const assetRoot = new URL("plant-fixture/", document.baseURI);
  const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setWorkerLimit(2));
  let manifest;
  const requests = new Map();
  const fallbackGeometry = new T.IcosahedronGeometry(.7, 1);
  const fallbackTrunk = new T.CylinderGeometry(.08, .16, 1.8, 8);
  const fallbackBark = new T.MeshBasicMaterial({ color: "#50352f" });
  const fallbackMaterial = new T.MeshBasicMaterial({ color: "#95798a" });
  const root = new T.Group();
  root.name = "Planting fixture";
  scene.add(root);
  const sky = new T.HemisphereLight("#e6efff", "#5e4b50", 2);
  const sun = new T.DirectionalLight("#ffe1c7", 2.2);
  sun.position.set(3, 6, 4);
  root.add(sky, sun);
  const modes = layouts.map((layout, mode) => {
    validateRoots(layout);
    const group = new T.Group();
    group.visible = mode === 0;
    root.add(group);
    return { group, entries: layout.map(([x, z, variety, scale, planting], index) => {
      const specimen = new T.Group();
      specimen.position.set(x, floor(x, z), z);
      specimen.rotation.y = index * 1.9;
      specimen.scale.setScalar(scale);
      const fallback = new T.Group();
      const canopy = new T.Mesh(fallbackGeometry, fallbackMaterial);
      const trunk = new T.Mesh(fallbackTrunk, fallbackBark);
      canopy.position.y = 1.8;
      trunk.position.y = .9;
      fallback.add(canopy, trunk);
      specimen.add(fallback);
      group.add(specimen);
      return { specimen, fallback, variety, planting, state: "fallback", detail: "fallback", scatter: [] };
    }) };
  });
  const marker = new T.Mesh(new T.BoxGeometry(2, .75, 3.4), new T.MeshBasicMaterial({ color: "#5b5765" }));
  marker.position.set(deck.x, .375, deck.z);
  scene.add(marker);
  let active = 0;
  function mount(entry) {
    entry.state = "loading";
    manifest ??= fetch(new URL("specimens.json", assetRoot)).then(response => {
      if (!response.ok) throw Error("Specimen manifest unavailable");
      return response.json();
    });
    if (!requests.has(entry.variety)) requests.set(entry.variety, manifest.then(specs =>
      loader.loadAsync(new URL(specs[entry.variety].file, assetRoot).href)));
    requests.get(entry.variety).then(({ scene }) => {
      const model = scene.clone(true);
      model.visible = false;
      model.traverse(node => {
        if (node.isInstancedMesh) entry.scatter.push([node, node.count]);
      });
      entry.specimen.add(model);
      entry.model = model;
      entry.state = "ready";
    }).catch(() => { entry.state = "fallback-error"; });
  }

  return {
    toggle() {
      modes[active].group.visible = false;
      active = 1 - active;
      sun.color.set(active ? "#b2bfff" : "#ffe1c7");
      modes[active].group.visible = true;
    },
    update(position) {
      const candidates = modes[active].entries.map(entry => ({ entry, distance: entry.specimen.position.distanceTo(position) }))
        .sort((a, b) => a.distance - b.distance);
      for (const [index, { entry, distance }] of candidates.entries()) {
        if (distance < 9 && entry.state === "fallback") mount(entry);
        if (!entry.model) continue;
        const detail = distance > 6 ? "fallback" : index === 0 && distance < 3 ? "full" : "canopy";
        if (entry.detail === detail) continue;
        entry.detail = detail;
        entry.model.visible = detail !== "fallback";
        entry.fallback.visible = detail === "fallback";
        for (const [node, count] of entry.scatter) {
          node.count = detail === "full" ? count : Math.ceil(count / 2);
        }
      }
    },
    observe() {
      return modes.map(({ group, entries }) => ({
        visible: group.visible,
        entries: entries.map(entry => ({
          variety: entry.variety, planting: entry.planting, state: entry.state, detail: entry.detail,
          root: entry.specimen.position.toArray(),
          sourceVisible: !!entry.model?.visible,
          fallbackVisible: entry.fallback.visible,
          drawn: entry.scatter.reduce((sum, [node]) => sum + node.count, 0),
        })),
      }));
    },
  };
}

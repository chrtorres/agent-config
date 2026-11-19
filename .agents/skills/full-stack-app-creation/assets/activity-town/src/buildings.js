import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const boxes = new Map();
const metal = (color, properties = {}) => new THREE.MeshStandardMaterial({
  color,
  roughness: 0.63,
  ...properties,
});
const paint = {
  cream: metal(0xfff4de),
  shell: metal(0xfffcf3),
  ink: metal(0x302c53),
  purple: metal(0x6257c9),
  violet: metal(0x8c7ee5),
  navy: metal(0x42448d),
  lilac: metal(0xc3b8f4),
  periwinkle: metal(0xa9c8f0),
  teal: metal(0x2b9e92),
  aqua: metal(0x7cd9c4),
  mint: metal(0xd0f2df),
  sage: metal(0x8dac64),
  blush: metal(0xf07786),
  peach: metal(0xffaa99),
  salmon: metal(0xbe5264),
  gold: metal(0xf3b847),
  orange: metal(0xf98b4e),
  honey: metal(0xffdf95),
  sky: metal(0x92daef, { roughness: 0.21, metalness: 0.15 }),
  visor: metal(0x251f4c, { roughness: 0.3 }),
  screen: metal(0x394574, { emissive: 0x17213e, emissiveIntensity: 0.6 }),
  glow: metal(0xa5fbee, { emissive: 0x4ec6a9, emissiveIntensity: 0.55 }),
};
const roundGeometry = new THREE.SphereGeometry(1, 20, 12);
const tubeGeometry = new THREE.CylinderGeometry(1, 1, 1, 20);

function part(parent, name, geometry, material, x, y, z, shadow = true) {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = shadow;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function block(parent, name, material, x, y, z, w, h, d, radius = 0.13, shadow = true) {
  const key = `${w}/${h}/${d}/${radius}`;
  if (!boxes.has(key)) {
    boxes.set(key, radius
      ? new RoundedBoxGeometry(w, h, d, 2, Math.min(radius, Math.min(w, h, d) * 0.47))
      : new THREE.BoxGeometry(w, h, d));
  }
  return part(parent, name, boxes.get(key), material, x, y, z, shadow);
}

function round(parent, name, material, x, y, z, w, h, d, shadow = true) {
  const mesh = part(parent, name, roundGeometry, material, x, y, z, shadow);
  mesh.scale.set(w, h, d);
  return mesh;
}

function tube(parent, name, material, x, y, z, radius, height, shadow = true) {
  const mesh = part(parent, name, tubeGeometry, material, x, y, z, shadow);
  mesh.scale.set(radius, height, radius);
  return mesh;
}

function beam(parent, name, material, from, to, thickness, depth) {
  const start = new THREE.Vector3(...from);
  const end = new THREE.Vector3(...to);
  const direction = end.clone().sub(start);
  const middle = start.addScaledVector(direction, 0.5);
  const mesh = block(parent, name, material, middle.x, middle.y, middle.z, thickness, direction.length(), depth);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  return mesh;
}

function group(parent, name, x = 0, y = 0, z = 0) {
  const item = new THREE.Group();
  item.name = name;
  item.position.set(x, y, z);
  parent?.add(item);
  return item;
}

function decal(parent, name, x, y, z, width, height, draw) {
  const canvas = typeof document !== 'undefined' ? document.createElement('canvas') : null;
  if (!canvas) return;
  canvas.width = 512;
  canvas.height = Math.round(canvas.width * height / width);
  const ctx = canvas.getContext('2d');
  draw(ctx, canvas.width, canvas.height);
  const map = new THREE.CanvasTexture(canvas);
  map.colorSpace = THREE.SRGBColorSpace;
  map.anisotropy = 8;
  const face = new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false });
  return part(parent, name, new THREE.PlaneGeometry(width, height), face, x, y, z, false);
}

function sign(parent, title, x, y, z, width, height, plaque, ink) {
  block(parent, `${title} sign plaque`, plaque, x, y, z, width, height, 0.22, 0.13);
  decal(parent, `${title} lettering`, x, y, z + 0.117, width, height, (ctx, w, h) => {
    ctx.fillStyle = ink;
    ctx.font = `900 ${h * 0.54}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.letterSpacing = '5px';
    ctx.fillText(title.toUpperCase(), w / 2, h * 0.505, w * 0.86);
  });
}

function desk(parent, x, z, color, facing = 1) {
  const cubicle = group(parent, 'Furnished cubicle', x, 0, z);
  cubicle.rotation.y = facing < 0 ? Math.PI : 0;
  block(cubicle, 'Felt cubicle screen', color, 0, 0.86, -0.96, 3.94, 1.72, 0.18, 0.12);
  block(cubicle, 'Privacy wing', color, -1.89, 0.67, -0.54, 0.16, 1.29, 0.84);
  block(cubicle, 'Desktop', paint.cream, 0, 0.86, -0.16, 3.35, 0.17, 1.18, 0.09);
  for (const side of [-1, 1]) {
    block(cubicle, 'Desk pedestal', paint.lilac, side * 1.48, 0.39, -0.16, 0.21, 0.76, 0.87);
  }
  block(cubicle, 'Monitor stand', paint.ink, 0, 1.03, -0.45, 0.45, 0.16, 0.3);
  block(cubicle, 'Monitor', paint.ink, 0, 1.4, -0.43, 1.03, 0.65, 0.14);
  block(cubicle, 'Monitor display', paint.screen, 0, 1.41, -0.354, 0.85, 0.48, 0.02, 0.02, false);
  block(cubicle, 'Display highlight', paint.glow, -0.14, 1.47, -0.342, 0.38, 0.06, 0.01, 0.02, false);
  block(cubicle, 'Keyboard', paint.periwinkle, 0.1, 0.959, 0.02, 0.74, 0.035, 0.29, 0.02, false);
  tube(cubicle, 'Desk mug', paint.orange, 1.04, 1.08, -0.07, 0.11, 0.24);
  const chair = group(cubicle, 'Swivel chair', 0.34, 0, 0.89);
  chair.rotation.y = -0.18;
  tube(chair, 'Swivel base', paint.ink, 0, 0.1, 0, 0.36, 0.14);
  tube(chair, 'Swivel post', paint.navy, 0, 0.27, 0, 0.1, 0.34);
  block(chair, 'Chair seat', paint.navy, 0, 0.47, 0, 0.75, 0.22, 0.65, 0.15);
  block(chair, 'Chair back', paint.navy, 0, 0.78, 0.32, 0.73, 0.64, 0.17, 0.1);
}

function plant(parent, x, y, z, scale = 1) {
  const planter = group(parent, 'Leafy planter', x, y, z);
  planter.scale.setScalar(scale);
  tube(planter, 'Terrazzo planter', paint.honey, 0, 0.29, 0, 0.37, 0.58);
  tube(planter, 'Pot rim', paint.cream, 0, 0.59, 0, 0.4, 0.13);
  for (const direction of [-1, 1]) {
    const leaf = round(planter, 'Leaf', paint.sage, direction * 0.22, 0.91, 0, 0.19, 0.42, 0.11);
    leaf.rotation.z = direction * -0.55;
  }
  round(planter, 'New leaf', paint.teal, 0, 1.09, -0.05, 0.15, 0.35, 0.1);
}

function officeModel(ground) {
  const office = group(ground, 'Town Hall · Cutaway office', 0, 0, -2);
  const lower = group(office, 'Ground floor · Cubicles', 0, 0.48, 0);
  const upperLevel = group(office, 'Upper floor and structural supports');
  const upper = group(upperLevel, 'Upper floor · Cubicles', 0, 4.05, -0.88);
  const roof = group(upperLevel, 'Office roof and terrace');

  block(office, 'Office foundation', paint.navy, 0, 0.15, 0, 15.6, 0.29, 10.8, 0.15);
  block(office, 'Ground-floor slab', paint.cream, 0, 0.33, 0, 15.75, 0.3, 10.95, 0.15);
  block(upperLevel, 'Upper-floor fascia', paint.purple, 0, 3.65, -1.33, 15.6, 0.32, 8.16, 0.16);
  block(upperLevel, 'Upper-floor slab', paint.cream, 0, 3.9, -1.33, 15.7, 0.3, 8.27, 0.15);
  block(office, 'Lower rear structure', paint.purple, 0, 2.23, -5.08, 15.3, 3.56, 0.62, 0.24);
  block(upperLevel, 'Upper rear structure', paint.purple, 0, 5.84, -5.08, 15.3, 3.77, 0.62, 0.24);
  block(office, 'Back wall acoustic panel', paint.lilac, 0, 1.89, -4.71, 13.1, 2.62, 0.13);

  // The upper slabs step back so the aerial camera can see both floors.
  block(roof, 'Roof fascia', paint.purple, 0, 7.3, -2.59, 15.73, 0.48, 5.94, 0.23);
  block(roof, 'Roof cap', paint.shell, 0, 7.65, -2.59, 15.91, 0.36, 6.08, 0.2);
  block(roof, 'Office roof terrace', paint.violet, 0, 7.91, -2.86, 12.12, 0.2, 4.08, 0.16);
  sign(roof, 'Town Hall', 0, 8.22, 0.06, 6.0, 1.04, paint.navy, '#fff6e7');
  for (const side of [-1, 1]) {
    tube(roof, 'Roof sign pin', paint.lilac, side * 3.35, 8.0, 0.02, 0.15, 0.46);
    for (const offset of [0, 0.74, 1.48]) {
      tube(roof, 'Roof terrace stud', paint.lilac, side * 5.42, 8.06, -1.23 - offset, 0.17, 0.17, false);
    }
    for (const { level, center, height, window } of [
      { level: office, center: 2.23, height: 3.56, window: 2.26 },
      { level: upperLevel, center: 5.84, height: 3.77, window: 5.93 },
    ]) {
      block(level, 'Side wall return', paint.violet, side * 7.43, center, -3.79, 0.66, height, 3.11, 0.23);
      block(level, 'Corner trim', paint.periwinkle, side * 7.79, center, -3.72, 0.15, height - 0.04, 0.24);
      block(level, 'Side window gasket', paint.navy, side * 7.765, window, -3.75, 0.17, 1.57, 2.31);
      block(level, 'Side window', paint.sky, side * 7.87, window, -3.75, 0.11, 1.34, 2.07, 0.1);
      block(level, 'Side window mullion', paint.shell, side * 7.938, window, -3.75, 0.08, 1.39, 0.09);
    }
  }
  for (const x of [-4.75, 0, 4.75]) {
    block(upperLevel, 'Upper window frame', paint.navy, x, 6.1, -4.74, 3.34, 1.91, 0.21);
    block(upperLevel, 'Upper window glass', paint.sky, x, 6.1, -4.61, 3.09, 1.63, 0.11);
    block(upperLevel, 'Upper window mullion', paint.shell, x, 6.1, -4.538, 0.11, 1.67, 0.07);
  }

  for (const [index, x] of [-4.65, 0, 4.65].entries()) {
    const divider = [paint.periwinkle, paint.lilac, paint.aqua][index];
    desk(lower, x, 2.35, divider);
    desk(upper, x, 0.88, divider);
  }
  block(lower, 'Ground floor carpet', paint.periwinkle, 0, 0.012, 2.55, 13.53, 0.025, 3.72, 0.012, false);
  block(upper, 'Upper floor carpet', paint.lilac, 0, 0.012, 0.63, 13.54, 0.025, 4.2, 0.012, false);

  for (const x of [-6.7, 6.7]) {
    plant(lower, x, 0, 4.48, 0.83);
    plant(upper, x, 0, 2.83, 0.8);
  }
  block(office, 'Low landing', paint.cream, 0, 0.11, 5.64, 5.7, 0.22, 0.66);
  block(office, 'Landing riser', paint.lilac, 0, 0.27, 5.42, 5.7, 0.23, 0.58);
  block(office, 'Landing inlay', paint.purple, 0, 0.127, 5.94, 2.94, 0.025, 0.06, 0.01, false);
  const stairs = group(lower, 'Rear return stair', -5.44, 0, -2.18);
  for (let tread = 0; tread < 12; tread++) {
    block(stairs, 'Stair tread', paint.lilac, tread * 0.36, 0.15 + tread * 0.3, 0, 0.47, 0.29, 1.12, 0.06);
  }
  const handrail = block(stairs, 'Ascending handrail', paint.navy, 1.97, 2.36, 0.55, 5.55, 0.1, 0.12, 0.035);
  handrail.rotation.z = Math.atan2(0.3, 0.36);
  const skylight = block(roof, 'Roof skylight', paint.sky, 0, 8.25, -3.13, 2.95, 0.55, 1.68, 0.24);
  skylight.rotation.x = -0.13;
  tube(roof, 'Relay station base', paint.navy, 3.75, 8.15, -3.84, 0.63, 0.35);
  tube(roof, 'Relay mast', paint.shell, 3.75, 8.65, -3.84, 0.095, 0.81);
  const dish = round(roof, 'Relay dish', paint.periwinkle, 3.75, 9.08, -3.83, 0.65, 0.15, 0.52);
  dish.rotation.x = 0.52;
  tube(roof, 'Relay dish receiver', paint.navy, 3.75, 9.3, -3.75, 0.055, 0.37);
  round(roof, 'Relay dish light', paint.glow, 3.75, 9.5, -3.75, 0.12, 0.12, 0.12, false);
  office.userData.setFloor = (mode) => {
    lower.visible = mode !== 'upper';
    upperLevel.visible = mode !== 'ground';
    roof.visible = mode === 'both';
  };
  return office;
}

function plinth(parent, color, width) {
  block(parent, 'Foundation', color, 0, 0.16, 0, width, 0.31, 6.6, 0.15);
  block(parent, 'Paving cap', paint.cream, 0, 0.33, 0, width + 0.14, 0.24, 6.74, 0.11);
  block(parent, 'Entrance landing', paint.cream, 0, 0.13, 3.52, 3.23, 0.24, 0.8, 0.12);
}

function portal(parent, color, highlight, x, z, width = 2.08) {
  block(parent, 'Entry surround', highlight, x, 1.94, z, width + 0.48, 2.99, 0.29, 0.23);
  block(parent, 'Glazed entry', color, x, 1.88, z + 0.17, width, 2.63, 0.12, 0.19);
  block(parent, 'Door seam', highlight, x, 1.88, z + 0.235, 0.06, 2.58, 0.035, 0.012);
  for (const side of [-1, 1]) {
    block(parent, 'Door grip', highlight, x + side * 0.16, 1.73, z + 0.265, 0.075, 0.34, 0.07, 0.026, false);
  }
}

function documentsModel(ground) {
  const documents = group(ground, 'Documents · Archive', -17, 0, 0);
  plinth(documents, paint.teal, 8.78);
  block(documents, 'Archive body', paint.teal, 0, 2.62, -0.12, 8.5, 4.35, 6.04, 0.46);
  block(documents, 'Archive front inset', paint.aqua, 0, 2.62, 2.961, 7.96, 3.93, 0.23, 0.26);
  block(documents, 'Archive cream roof', paint.shell, 0, 4.82, -0.17, 8.74, 0.42, 6.45, 0.19);
  block(documents, 'Archive rooftop folder', paint.aqua, 0, 5.14, -0.4, 7.47, 0.31, 4.97, 0.16);
  block(documents, 'Folder tab', paint.teal, -1.91, 5.4, -1.27, 3.69, 0.28, 3.24, 0.13);
  for (const z of [-2.29, -1.28, -0.27, 0.74, 1.75]) {
    block(documents, 'Archive side rib', paint.aqua, 4.235, 2.87, z, 0.2, 3.67, 0.24, 0.1);
  }
  portal(documents, paint.teal, paint.mint, 0, 3.045);
  for (const x of [-2.61, 2.61]) {
    block(documents, 'Document shelf alcove', paint.teal, x, 2.18, 3.067, 1.76, 2.31, 0.16, 0.14);
    for (const y of [1.74, 2.68]) {
      block(documents, 'Shelf ledge', paint.mint, x, y - 0.31, 3.168, 1.5, 0.1, 0.19, 0.045, false);
      for (const [i, cover] of [paint.peach, paint.cream, paint.sky, paint.honey].entries()) {
        const binder = block(documents, 'Archive binder', cover, x - 0.49 + i * 0.33,
          y + (i % 2) * 0.08, 3.21, 0.23, 0.52 + (i % 2) * 0.16, 0.16, 0.023, false);
        binder.rotation.z = i === 3 ? -0.16 : 0;
      }
    }
  }
  sign(documents, 'Documents', 0, 4.22, 3.139, 4.58, 0.88, paint.mint, '#174d49');
  return documents;
}

function picturesModel(ground) {
  const pictures = group(ground, 'My Pictures · Gallery', 16, 0, -4);
  plinth(pictures, paint.salmon, 8.65);
  block(pictures, 'Gallery shell', paint.peach, 0, 2.24, 0, 8.39, 3.68, 6.31, 0.54);
  block(pictures, 'Gallery terracotta belt', paint.blush, 0, 3.85, 0, 8.63, 0.45, 6.45, 0.21);
  block(pictures, 'Gallery cream roof', paint.shell, 0, 4.17, 0, 8.73, 0.34, 6.57, 0.16);
  portal(pictures, paint.salmon, paint.cream, -2.38, 3.14, 1.91);
  block(pictures, 'Gallery picture frame', paint.cream, 1.38, 2.13, 3.17, 4.1, 2.64, 0.28, 0.19);
  block(pictures, 'Gallery mat', paint.blush, 1.38, 2.13, 3.33, 3.7, 2.25, 0.12, 0.14);
  block(pictures, 'Gallery print', paint.sky, 1.38, 2.13, 3.401, 3.43, 1.98, 0.045, 0.03);
  decal(pictures, 'Original gallery landscape', 1.38, 2.13, 3.429, 3.29, 1.86, (ctx, w, h) => {
    ctx.fillStyle = '#fac2a0';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = '#ffedac';
    ctx.beginPath();
    ctx.arc(w * 0.69, h * 0.39, h * 0.19, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#8574cc';
    ctx.beginPath();
    ctx.moveTo(0, h * 0.79);
    ctx.quadraticCurveTo(w * 0.23, h * 0.16, w * 0.55, h * 0.77);
    ctx.quadraticCurveTo(w * 0.83, h * 0.34, w, h * 0.74);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.fill();
    ctx.fillStyle = '#4e8b85';
    ctx.beginPath();
    ctx.moveTo(0, h * 0.92);
    ctx.quadraticCurveTo(w * 0.29, h * 0.7, w * 0.57, h * 0.89);
    ctx.quadraticCurveTo(w * 0.75, h, w, h * 0.79);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.fill();
  });
  sign(pictures, 'My Pictures', 0, 3.78, 3.335, 4.89, 0.77, paint.salmon, '#fff2df');

  const camera = group(pictures, 'Rooftop toy camera', 0.36, 4.35, -0.47);
  camera.rotation.y = 0.08;
  block(camera, 'Camera base', paint.blush, 0, 0.09, 0, 4.86, 0.18, 2.8, 0.09);
  block(camera, 'Camera shell', paint.peach, 0, 1.0, 0, 3.85, 1.62, 1.52, 0.32);
  block(camera, 'Camera faceplate', paint.shell, 0, 1.0, 0.75, 3.69, 1.31, 0.18, 0.09);
  const objective = tube(camera, 'Lens barrel', paint.salmon, 0.28, 0.99, 0.98, 0.69, 0.51);
  objective.rotation.x = Math.PI / 2;
  const lens = tube(camera, 'Lens glass', paint.sky, 0.28, 0.99, 1.25, 0.47, 0.09);
  lens.rotation.x = Math.PI / 2;
  block(camera, 'Flash window', paint.honey, -1.31, 1.35, 0.872, 0.46, 0.28, 0.07);
  tube(camera, 'Shutter button', paint.salmon, 1.23, 1.85, -0.16, 0.25, 0.18);
  return pictures;
}

function workshopModel(ground) {
  const workshop = group(ground, 'Workshop · Fabrication bay', 12, 0, 10);
  plinth(workshop, paint.orange, 8.18);
  block(workshop, 'Workshop rear wall', paint.orange, 0, 1.93, -2.89, 7.89, 3.0, 0.54, 0.25);
  for (const side of [-1, 1]) {
    block(workshop, 'Workshop side wall', paint.gold, side * 3.63, 1.94, 0, 0.78, 3.0, 6.25, 0.25);
    block(workshop, 'Garage door track', paint.cream, side * 3.11, 1.91, 3.01, 0.33, 2.9, 0.32, 0.15);
    block(workshop, 'Garage pillar inset', paint.orange, side * 3.65, 1.56, 3.16, 0.41, 1.3, 0.22, 0.08);
  }
  block(workshop, 'Workshop roof beam', paint.gold, 0, 3.58, -0.13, 8.18, 0.51, 6.43, 0.26);
  block(workshop, 'Workshop cream roof', paint.shell, 0, 3.92, -0.13, 8.27, 0.24, 6.58, 0.12);
  block(workshop, 'Sunroof housing', paint.honey, -0.64, 4.16, -0.86, 4.64, 0.39, 3.47, 0.18);
  for (const x of [-2, -0.64, 0.72]) {
    block(workshop, 'Workshop skylight', paint.sky, x, 4.39, -0.86, 1.15, 0.17, 2.64, 0.075);
  }
  tube(workshop, 'Vent housing', paint.orange, 2.79, 4.18, -1.56, 0.57, 0.5);
  tube(workshop, 'Vent chimney', paint.gold, 2.79, 4.63, -1.56, 0.33, 0.58);
  tube(workshop, 'Vent cap', paint.cream, 2.79, 4.95, -1.56, 0.44, 0.17);
  sign(workshop, 'Workshop', 0, 3.56, 3.225, 4.22, 0.77, paint.ink, '#ffedbf');

  block(workshop, 'Workshop floor mat', paint.honey, 0, 0.462, 0.02, 5.69, 0.025, 5.67, 0.01, false);
  block(workshop, 'Workbench', paint.ink, -1.17, 1.07, -1.97, 3.46, 1.23, 0.78, 0.13);
  block(workshop, 'Workbench countertop', paint.cream, -1.17, 1.72, -1.97, 3.65, 0.18, 0.98, 0.075);
  block(workshop, 'Rear storage drawers', paint.peach, 2.28, 1.24, -1.94, 1.83, 1.48, 1.12, 0.12);
  for (const y of [0.91, 1.24, 1.57]) {
    block(workshop, 'Drawer handle', paint.ink, 2.28, y, -1.355, 0.45, 0.08, 0.08, 0.03, false);
  }
  block(workshop, 'Bench tool box', paint.aqua, -2.0, 1.94, -1.79, 0.81, 0.36, 0.43, 0.08);
  const arm = group(workshop, 'Fabrication robot arm', -1.88, 0.48, 1.86);
  tube(arm, 'Fabricator rotary foot', paint.ink, 0, 0.17, 0, 0.59, 0.34);
  tube(arm, 'Fabricator hub', paint.orange, 0, 0.44, 0, 0.38, 0.28);
  const pivot = [0, 0.58, 0];
  const elbow = [0.4, 1.56, 0.03];
  const wrist = [1.1, 1.35, 0.19];
  beam(arm, 'Fabricator shoulder link', paint.gold, pivot, elbow, 0.36, 0.34);
  beam(arm, 'Fabricator forearm link', paint.orange, elbow, wrist, 0.26, 0.26);
  round(arm, 'Fabricator elbow bearing', paint.ink, ...elbow, 0.21, 0.21, 0.2);
  block(arm, 'Fabricator gripper', paint.ink, 1.11, 1.26, 0.19, 0.27, 0.21, 0.27, 0.05);
  for (const x of [1.02, 1.19]) {
    block(arm, 'Gripper finger', paint.cream, x, 1.11, 0.19, 0.067, 0.18, 0.09, 0.025);
  }
  block(arm, 'Fabricator workpiece', paint.aqua, 1.1, 0.18, 0.19, 0.55, 0.34, 0.58, 0.095);
  for (const side of [-1, 1]) {
    block(workshop, 'Floor safety marker', paint.ink, side * 2.77, 0.48, 2.47, 0.18, 0.025, 1.11, 0.012, false);
  }
  return workshop;
}

export function createBuildings(ground) {
  return {
    office: officeModel(ground),
    documents: documentsModel(ground),
    pictures: picturesModel(ground),
    workshop: workshopModel(ground),
  };
}

export function createAgent() {
  const agent = group(null, 'Codex · Town agent');
  const body = group(agent, 'Robot torso and head');
  block(body, 'Robot torso', paint.purple, 0, 0.97, 0, 0.88, 0.84, 0.64, 0.26);
  block(body, 'Robot chest plate', paint.cream, 0, 0.99, 0.29, 0.65, 0.58, 0.17, 0.19);
  block(body, 'Robot chest status light', paint.glow, 0, 1.02, 0.383, 0.27, 0.14, 0.047, 0.06);
  block(body, 'Robot battery pack', paint.orange, 0, 0.99, -0.37, 0.62, 0.55, 0.21, 0.12);
  tube(body, 'Robot neck', paint.ink, 0, 1.41, 0, 0.22, 0.21);

  const head = group(body, 'Robot helmet', 0, 1.79, 0.03);
  block(head, 'Helmet shell', paint.violet, 0, 0, 0, 1.25, 0.81, 0.85, 0.31);
  block(head, 'Helmet front trim', paint.cream, 0, 0, 0.347, 1.08, 0.65, 0.3, 0.235);
  block(head, 'Helmet visor', paint.visor, 0, 0, 0.471, 0.95, 0.51, 0.15, 0.172);
  const eyes = [-0.22, 0.22].map((x) =>
    block(head, 'Robot eye light', paint.glow, x, 0.052, 0.552, 0.135, 0.18, 0.037, 0.026, false),
  );
  block(head, 'Robot smile light', paint.glow, 0, -0.126, 0.552, 0.15, 0.042, 0.03, 0.018, false);
  tube(head, 'Antenna stem', paint.ink, 0.33, 0.48, -0.03, 0.055, 0.23);
  round(head, 'Antenna light', paint.orange, 0.33, 0.609, -0.03, 0.103, 0.103, 0.103);

  const limbs = [-1, 1].map((side) => {
    const earpiece = tube(head, 'Helmet earpiece', paint.orange, side * 0.62, 0, 0, 0.22, 0.13);
    earpiece.rotation.z = Math.PI / 2;
    const arm = group(body, 'Robot arm', side * 0.53, 1.19, 0);
    arm.rotation.z = side * 0.12;
    round(arm, 'Robot shoulder joint', paint.ink, 0, 0, 0, 0.14, 0.14, 0.15);
    block(arm, 'Robot arm shell', paint.cream, 0, -0.2, 0, 0.25, 0.39, 0.27, 0.1);
    round(arm, 'Robot glove', paint.orange, 0, -0.395, 0.026, 0.133, 0.124, 0.13);
    const leg = group(agent, 'Robot leg', side * 0.24, 0.58, 0);
    block(leg, 'Robot shin', paint.ink, 0, -0.2, 0, 0.24, 0.41, 0.23, 0.09);
    block(leg, 'Robot boot', paint.violet, 0, -0.455, 0.075, 0.32, 0.24, 0.46, 0.09);
    return { side, arm, leg };
  });

  return {
    group: agent,
    update(time, moving, working) {
      const stride = moving ? Math.sin(time * 12) : 0;
      body.position.y = moving ? Math.abs(stride) * 0.081 : Math.sin(time * 3.6) * 0.019;
      head.rotation.x = working && !moving ? 0.13 + Math.sin(time * 5) * 0.039 : -0.04;
      head.rotation.z = moving ? stride * 0.045 : Math.sin(time * 1.9) * 0.05;
      const blink = time % 4.6;
      for (const eye of eyes) eye.scale.y = blink > 4.45 ? 0.15 : 1;
      for (const { side, arm, leg } of limbs) {
        leg.rotation.x = stride * side * 0.52;
        arm.rotation.x = working && !moving ? -0.42 + Math.sin(time * 9 + side) * 0.17 : -stride * side * 0.43;
      }
    },
  };
}

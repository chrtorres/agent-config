import * as THREE from 'three';

const materials = new Map();
const cube = new THREE.BoxGeometry();
const ball = new THREE.SphereGeometry(1, 16, 12);
const cylinder = new THREE.CylinderGeometry(1, 1, 1, 16);

function paint(color, roughness = .76) {
  if (!materials.has(color)) materials.set(color, new THREE.MeshStandardMaterial({ color, roughness }));
  return materials.get(color);
}

function part(parent, geometry, color, x, y, z, sx, sy, sz, cast = true) {
  const mesh = new THREE.Mesh(geometry, paint(color));
  mesh.position.set(x, y, z);
  mesh.scale.set(sx, sy, sz);
  mesh.castShadow = cast;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function roundedPlate(width, depth, radius, height) {
  const x = width / 2;
  const z = depth / 2;
  const shape = new THREE.Shape();
  shape.moveTo(-x + radius, -z);
  shape.lineTo(x - radius, -z);
  shape.quadraticCurveTo(x, -z, x, -z + radius);
  shape.lineTo(x, z - radius);
  shape.quadraticCurveTo(x, z, x - radius, z);
  shape.lineTo(-x + radius, z);
  shape.quadraticCurveTo(-x, z, -x, z - radius);
  shape.lineTo(-x, -z + radius);
  shape.quadraticCurveTo(-x, -z, -x + radius, -z);
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: height, bevelEnabled: true, bevelSegments: 3, bevelSize: .15, bevelThickness: .12, curveSegments: 12
  });
  geometry.rotateX(-Math.PI / 2);
  return geometry;
}

function path(ground, width, depth, x, z, color = '#e1e5d3') {
  return part(ground, cube, color, x, .014, z, width, .042, depth, false);
}

function tree(ground, x, z, size, color) {
  part(ground, cylinder, '#988473', x, .52 * size, z, .15 * size, 1.1 * size, .15 * size);
  part(ground, ball, color, x, 1.5 * size, z, .79 * size, .95 * size, .76 * size);
  part(ground, ball, color, x - .42 * size, 1.30 * size, z + .18 * size, .50 * size, .61 * size, .50 * size);
  part(ground, ball, color, x + .41 * size, 1.42 * size, z - .17 * size, .52 * size, .65 * size, .49 * size);
}

function streetlight(ground, x, z) {
  part(ground, cylinder, '#829487', x, .08, z, .26, .16, .26);
  part(ground, cylinder, '#657c72', x, .94, z, .09, 1.64, .09);
  part(ground, ball, '#fff1cf', x, 1.84, z, .22, .22, .22);
}

function bench(ground, x, z, angle) {
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  group.rotation.y = angle;
  ground.add(group);
  for (const side of [-.73, .73]) {
    part(group, cube, '#71877b', side, .21, 0, .14, .42, .53);
    part(group, cube, '#71877b', side, .46, -.21, .14, .56, .1);
  }
  part(group, cube, '#e6ac70', 0, .45, 0, 1.94, .13, .62);
  part(group, cube, '#e6ac70', 0, .7, -.21, 1.94, .21, .11);
}

function planting(ground, x, z, color) {
  part(ground, cylinder, '#c3bba7', x, .12, z, .5, .24, .5);
  part(ground, ball, '#678e72', x, .3, z, .30, .18, .31);
  part(ground, ball, color, x - .18, .45, z, .15, .17, .15);
  part(ground, ball, color, x + .12, .51, z - .09, .15, .20, .15);
  part(ground, ball, color, x + .14, .41, z + .15, .11, .14, .11);
}

export function createLandscape(scene) {
  const ground = new THREE.Group();
  ground.name = 'Diorama and grounds';
  ground.position.y = .85;
  scene.add(ground);

  part(ground, roundedPlate(53, 36, 4, .44), '#7c9b83', 0, -.77, 2.2, 1, 1, 1);
  part(ground, roundedPlate(53, 36, 4, .28), '#acc6a5', 0, -.39, 2.2, 1, 1, 1);
  part(ground, roundedPlate(51.2, 34.2, 3.5, .045), '#becfb1', 0, -.16, 2.2, 1, 1, 1, false);

  path(ground, 46.5, 2.3, -.3, 7.5);
  path(ground, 1.75, 6, -17, 5.35);
  path(ground, 3.8, 5.4, 0, 5.30);
  path(ground, 1.8, 12.5, 6.2, 9.75);
  path(ground, 10.1, 1.65, 11.1, 3.5);
  path(ground, 1.8, 4.3, 13.62, 1.43);
  path(ground, 11.2, 1.65, 10.9, 16);
  path(ground, 1.8, 3.4, 12, 15.15);
  path(ground, 1.6, 8.7, -8.5, 12.1);
  path(ground, 11.6, 1.6, -13.5, 16);
  path(ground, 1.6, 8.9, -19, 12.1);
  path(ground, 1.65, 18, -23.2, -1.15).position.y -= .003;
  path(ground, 47.4, 1.35, -.35, -10.15);
  path(ground, 1.85, 17.65, 22.5, -1.5);
  path(ground, 8, 1.32, -20, -3);
  path(ground, 7, 1.32, 20, -.5);
  for (const x of [-21, -14, -11, -5, 3.1, 10, 19.1]) {
    path(ground, 1.0, .09, x, 7.5, '#b9c5b1').position.y = .038;
  }

  const trees = [
    [-24.2, -11.8, 1.2], [-19.6, -11.9, 1.04], [-12.4, -12.5, 1.43],
    [-5.9, -12.55, 1.16], [3.8, -12.6, 1.4], [9.7, -12.8, 1.12],
    [20.3, -11.9, 1.32], [24, -8, 1.06], [24.4, 1.8, 1.28],
    [24, 12, 1.39], [21.8, 17.1, 1.12], [16.9, 17.65, 1.16],
    [3.4, 17.2, 1.2], [-3.4, 16, 1.07], [-11.1, 17.45, 1.15],
    [-20.8, 17.35, 1.17], [-23.1, 11.8, 1.52], [-24.7, 3.5, 1.08],
    [-11.4, 3.5, 1.15], [-9.1, -5.1, 1.24], [9.7, -6.5, 1.17]
  ];
  const foliage = ['#80a877', '#73996f', '#9cba82', '#87b096'];
  trees.forEach(([x, z, scale], i) => tree(ground, x, z, scale, foliage[i % foliage.length]));

  path(ground, 8.8, 5.9, -13.65, 12, '#d2dabb');
  part(ground, cylinder, '#d2c9cc', -13.8, .16, 12.15, 1.98, .32, 1.98);
  part(ground, cylinder, '#f5e7d3', -13.8, .37, 12.15, 1.61, .19, 1.61);
  part(ground, cylinder, '#87b9c3', -13.8, .478, 12.15, 1.42, .05, 1.42, false);
  part(ground, cylinder, '#dbcfee', -13.8, .78, 12.15, .29, .72, .29);
  part(ground, ball, '#aecfde', -13.8, 1.22, 12.15, .41, .40, .41);
  bench(ground, -16.6, 12.25, Math.PI / 2);
  bench(ground, -11, 12.2, -Math.PI / 2);
  bench(ground, 2, 11.5, 0);
  for (const [x, z] of [[-20, 6.1], [-9.2, 8.95], [-3, 6.2], [4, 8.9], [10.8, 2.55], [19.8, 8.9], [14.9, 16.9]]) {
    streetlight(ground, x, z);
  }
  const flowers = ['#eedba0', '#e8a9bb', '#a6a1d4'];
  [[-20.4, 4.15], [-13.7, 4.17], [-6.5, 5.0], [5, 4.6], [19.5, 1.35], [9.1, 14.35], [15.2, 13.93], [-9.6, 15.3], [-17.7, 14.25]].forEach(
    ([x, z], i) => planting(ground, x, z, flowers[i % flowers.length])
  );
  return ground;
}

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createBuildings, createAgent } from './buildings.js';
import { createLandscape } from './landscape.js';
import { places, routeTo } from './places.js';

const radians = THREE.MathUtils.degToRad;
const degrees = THREE.MathUtils.radToDeg;
const overview = new THREE.Vector3(0, 2.3, 2.8);

function lights(scene) {
  scene.add(new THREE.HemisphereLight('#f8fbff', '#a5ad8d', 2.15));
  const key = new THREE.DirectionalLight('#fff1dc', 2.35);
  key.position.set(-25, 39, 19);
  key.castShadow = true;
  Object.assign(key.shadow.camera, { left: -34, right: 34, top: 31, bottom: -30, near: 1, far: 99 });
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -.0007;
  key.shadow.normalBias = .065;
  key.shadow.radius = 3;
  scene.add(key);
  const fill = new THREE.DirectionalLight('#cad9ff', .65);
  fill.position.set(16, 13, -25);
  scene.add(fill);
}

function tracker(ground) {
  const group = new THREE.Group();
  group.position.y = .092;
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(.82, 32), new THREE.MeshBasicMaterial({
    color: '#574a64', transparent: true, opacity: .22, depthWrite: false
  }));
  shadow.rotation.x = -Math.PI / 2;
  shadow.scale.y = .76;
  group.add(shadow);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.02, .047, 8, 56), new THREE.MeshBasicMaterial({ color: '#8f6ac5' }));
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = .025;
  group.add(ring);
  ground.add(group);
  return group;
}

export function createTown(canvas, heightInput, markerElements, agentMarker, onArrival) {
  const scene = new THREE.Scene();
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;
  renderer.shadowMap.needsUpdate = true;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1.05;
  lights(scene);

  const ground = createLandscape(scene);
  const buildings = createBuildings(ground);
  const robot = createAgent();
  robot.group.traverse((object) => { object.castShadow = false; });
  ground.add(robot.group);
  robot.group.position.set(places.office.door[0], .045, places.office.door[1]);
  const ring = tracker(ground);

  const camera = new THREE.PerspectiveCamera(38, 1, .2, 250);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = .11;
  controls.minPolarAngle = radians(11);
  controls.maxPolarAngle = radians(71);
  controls.minDistance = 15;
  controls.maxDistance = 152;
  controls.panSpeed = .6;
  controls.rotateSpeed = .68;
  controls.zoomSpeed = .75;
  controls.listenToKeyEvents(canvas);

  let destination = 'office';
  let route = [];
  let working = false;
  let cameraMode = 'follow';
  let focusedPlace = null;
  let viewingFloor = 'both';
  let width = 1;
  let height = 1;
  const focus = overview.clone();
  const priorFocus = overview.clone();
  const delta = new THREE.Vector3();
  const projected = new THREE.Vector3();
  const markerPositions = Object.fromEntries(Object.entries(places).map(([key, place]) => (
    [key, new THREE.Vector3(...place.marker)]
  )));

  function initialDistance() {
    return Math.max(57, Math.min(132, 72 / (width / height)));
  }

  function clearCameraInertia() {
    controls.enableDamping = false;
    controls.update();
    controls.enableDamping = true;
  }

  function resetCamera() {
    focusedPlace = null;
    clearCameraInertia();
    controls.target.copy(overview);
    priorFocus.copy(overview);
    camera.position.copy(overview).add(new THREE.Vector3().setFromSphericalCoords(
      initialDistance(), radians(48), radians(24)
    ));
    controls.update();
  }

  function onResize() {
    const { clientWidth, clientHeight } = canvas;
    const oldDistance = initialDistance();
    width = Math.max(clientWidth, 1);
    height = Math.max(clientHeight, 1);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    if (!canvas.dataset.rendered) resetCamera();
    else camera.position.sub(controls.target).multiplyScalar(initialDistance() / oldDistance).add(controls.target);
  }

  const observer = new ResizeObserver(onResize);
  observer.observe(canvas);
  onResize();

  function project(point, element) {
    projected.copy(point).project(camera);
    const x = (projected.x + 1) * width / 2;
    const y = (1 - projected.y) * height / 2;
    const margin = element === agentMarker ? 8 : 20;
    element.hidden = projected.z >= 1 || x < margin || x > width - margin || y < 42 || y > height - 30;
    if (!element.hidden) element.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -100%)`;
  }

  function stepRobot(dt, time) {
    const position = robot.group.position;
    const moving = route.length > 0;
    let remaining = dt * 8.5;
    while (remaining > 0 && route.length) {
      const [x, z] = route[0];
      const dx = x - position.x;
      const dz = z - position.z;
      const distance = Math.hypot(dx, dz);
      if (distance > .01) {
        const direction = Math.atan2(dx, dz);
        const turn = Math.atan2(Math.sin(direction - robot.group.rotation.y), Math.cos(direction - robot.group.rotation.y));
        robot.group.rotation.y += turn * Math.min(1, dt * 13);
      }
      if (distance <= remaining) {
        position.x = x;
        position.z = z;
        route.shift();
        remaining -= distance;
      } else {
        position.x += dx * remaining / distance;
        position.z += dz * remaining / distance;
        remaining = 0;
      }
    }
    if (moving && !route.length) onArrival(destination);
    robot.update(time, route.length > 0, working && !route.length);
    ring.position.x = position.x;
    ring.position.z = position.z;
  }

  function updateCamera(dt) {
    focus.copy(overview);
    if (cameraMode === 'follow') {
      const distance = camera.position.distanceTo(controls.target);
      const close = 1 - THREE.MathUtils.smoothstep(distance, 21, initialDistance());
      focus.x = robot.group.position.x * THREE.MathUtils.lerp(.58, 1, close);
      focus.z += (robot.group.position.z - overview.z) * THREE.MathUtils.lerp(.55, 1, close);
      focus.y = THREE.MathUtils.lerp(overview.y, ground.position.y + 1.25, close);
    } else if (focusedPlace) {
      const [x, , z] = places[focusedPlace].marker;
      focus.x = x * .76;
      focus.z += (z - overview.z) * .76;
    }
    delta.copy(focus).sub(priorFocus).multiplyScalar(1 - Math.exp(-4 * dt));
    priorFocus.add(delta);
    controls.target.add(delta);
    camera.position.add(delta);
    controls.update(dt);
    const elevation = String(Math.round(90 - degrees(controls.getPolarAngle())));
    if (heightInput.value !== elevation) heightInput.value = elevation;
  }

  let priorTime = performance.now();
  let lastObservation = -100;
  function frame(now) {
    const dt = THREE.MathUtils.clamp((now - priorTime) / 1000, 0, .14);
    priorTime = now;
    stepRobot(dt, now / 1000);
    updateCamera(dt);
    renderer.render(scene, camera);
    for (const [key, element] of Object.entries(markerElements)) project(markerPositions[key], element);
    const { x, y, z } = robot.group.position;
    project(projected.set(x, y + ground.position.y + 2.45, z), agentMarker);
    // Publish inspection state after rendering, so browser checks can wait for a drawn frame.
    if (now - lastObservation >= 84) {
      const { x: cx, y: cy, z: cz } = camera.position;
      Object.assign(canvas.dataset, {
        rendered: 'true', floors: viewingFloor,
        agentX: x.toFixed(2), agentY: y.toFixed(2), agentZ: z.toFixed(2),
        cameraX: cx.toFixed(2), cameraY: cy.toFixed(2), cameraZ: cz.toFixed(2)
      });
      lastObservation = now;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  return {
    sendTo(place) {
      if (place === destination) return route.length > 0;
      destination = place;
      route = routeTo([robot.group.position.x, robot.group.position.z], place);
      return route.length > 0;
    },
    setWorking(value) { working = value; },
    setCamera(mode) {
      if (mode === 'follow') {
        clearCameraInertia();
        camera.position.add(delta.copy(priorFocus).sub(controls.target));
        controls.target.copy(priorFocus);
        controls.update();
      }
      cameraMode = mode;
      focusedPlace = null;
    },
    showPlace(place) {
      cameraMode = 'overview';
      focusedPlace = place;
    },
    setHeight(elevation) {
      const offset = camera.position.clone().sub(controls.target);
      const spherical = new THREE.Spherical().setFromVector3(offset);
      spherical.phi = radians(90 - elevation);
      camera.position.copy(controls.target).add(offset.setFromSpherical(spherical));
      controls.update();
    },
    zoom(inward) {
      if (inward) controls.dollyIn(.83);
      else controls.dollyOut(.83);
    },
    resetCamera,
    setFloor(mode) {
      viewingFloor = mode;
      buildings.office.userData.setFloor(mode);
      renderer.shadowMap.needsUpdate = true;
    }
  };
}

import * as T from "three";
import { BEACON, createGame, frameDelta } from "./core.js";
import { createPresentation, GRAPHICS_TIERS } from "./presentation.js";
import { createGait } from "./gait.js";

const game = createGame({ getItem: key => localStorage.getItem(key), setItem: (key, value) => localStorage.setItem(key, value) });
const canvas = new T.WebGLRenderer({ antialias: true });
document.querySelector("main").append(canvas.domElement);
const scene = new T.Scene();
scene.background = new T.Color("#121d2b");
canvas.toneMapping = T.ACESFilmicToneMapping;
const requested = new URLSearchParams(location.search).get("quality");
let quality = GRAPHICS_TIERS.includes(requested) ? requested : "balanced";
const camera = new T.PerspectiveCamera(58, 1, .1, 100);
const presentation = createPresentation(canvas, scene, camera);
function resize() {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  presentation.resize(innerWidth, innerHeight, devicePixelRatio, quality);
}
resize();
addEventListener("resize", resize);
document.querySelector("#quality").addEventListener("click", () => {
  quality = GRAPHICS_TIERS[(GRAPHICS_TIERS.indexOf(quality) + 1) % GRAPHICS_TIERS.length];
  resize();
});
const material = color => new T.MeshBasicMaterial({ color });
const player = new T.Group();
const torso = new T.Mesh(new T.BoxGeometry(.45, .75, .45), material("#ffc777"));
torso.position.y = .57;
player.add(torso);
const boots = [-.14, .14].map(x => {
  const foot = new T.Mesh(new T.BoxGeometry(.15, .12, .26), material("#ed9e63"));
  foot.position.x = x;
  player.add(foot);
  return foot;
});
const gait = createGait();
const beacon = new T.Mesh(new T.CylinderGeometry(.3, .45, 1, 8), material("#58e4f6"));
beacon.position.set(BEACON.x, .5, BEACON.z);
scene.add(player, beacon, new T.GridHelper(18, 18, "#aaaabb", "#495c71"));
const keys = new Set();
let pending = false, previous = null, previousPad, pressed = false, frames = 0;
addEventListener("keydown", e => { keys.add(e.code); if (e.code === "KeyE" && !e.repeat) pending = true; });
addEventListener("keyup", e => keys.delete(e.code));
addEventListener("blur", () => { keys.clear(); pending = false; });

function frame(now) {
  requestAnimationFrame(frame);
  const dt = frameDelta(now, previous);
  previous = now;
  if (document.hidden) { keys.clear(); pending = false; return; }
  let pad;
  try { pad = Array.from(navigator.getGamepads?.() ?? []).find(p => p?.connected && p.mapping === "standard"); }
  catch { /* Some embedded contexts deny the API. Keyboard remains available. */ }
  const axis = n => Number.isFinite(n) && Math.abs(n) > .2 ? n : 0;
  const padPressed = Boolean(pad?.buttons[0]?.pressed);
  if (pad?.index !== previousPad) pressed = false;
  const state = game.update(dt, {
    x: Number(keys.has("KeyD")) - Number(keys.has("KeyA")) + axis(pad?.axes[0]),
    z: Number(keys.has("KeyS")) - Number(keys.has("KeyW")) + axis(pad?.axes[1]),
    interact: pending || (padPressed && !pressed),
  });
  previousPad = pad?.index;
  pressed = padPressed;
  pending = false;
  const distance = Math.hypot(state.x - player.position.x, state.z - player.position.z);
  gait(frames ? distance : 0).forEach(({ rise, stride }, i) => {
    boots[i].position.y = .06 + rise;
    boots[i].position.z = -stride;
  });
  player.position.set(state.x, 0, state.z);
  camera.position.set(state.x + 2, 3, state.z + 5);
  camera.lookAt(state.x, .5, state.z - 1);
  beacon.material.color.set(state.reached ? "#76f5ab" : "#58e4f6");
  const status = document.querySelector("#status");
  const message = state.saveError ? "Save unavailable" : state.reached ? "Checkpoint saved" : "Find the cyan beacon";
  if (status.textContent !== message) status.textContent = message;
  presentation.render(dt);
  window.renderedCheckpoint = {
    ...state, frames: ++frames, cameraDistance: camera.position.distanceTo(player.position),
    quality, resolution: presentation.resolution,
    boots: boots.map(foot => foot.getWorldPosition(new T.Vector3()).toArray()),
  };
}
requestAnimationFrame(frame);

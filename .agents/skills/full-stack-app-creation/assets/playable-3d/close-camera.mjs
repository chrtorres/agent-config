// Close inspection of a character in the running game without touching the game camera.
// The game's own render call is wrapped: renders through the main camera are redirected
// to an inspection camera placed relative to the player each frame, so motion, cloth and
// post-processing set-up stay exactly as the game drives them. Renders through any other
// camera (shadow maps, post-processing quads) pass through unchanged.
//
// Inject this into the page (for example with Playwright's page.evaluate) after the app
// exposes its renderer, main camera and player, then call restore() when finished.

/**
 * @param renderer  object with render(scene, camera)
 * @param mainCamera the game's camera; only its renders are redirected
 * @param inspect   a camera to render from instead (a clone of mainCamera works)
 * @param place     (inspect, mainCamera) => void; positions and aims `inspect` each frame
 * @returns restore() puts the original render function back
 */
export function redirectRender(renderer, mainCamera, inspect, place) {
  const original = renderer.render;
  renderer.render = function (scene, camera) {
    if (camera !== mainCamera) return original.call(this, scene, camera);
    place(inspect, mainCamera);
    return original.call(this, scene, inspect);
  };
  return () => { renderer.render = original; };
}

/**
 * Place a camera on an orbit around a player: `yaw` is measured from the player's facing
 * (0 = in front, PI = behind), `distance` horizontal metres, `height` above the feet, and
 * the camera looks at `focus` metres above the feet. Works with three.js-like objects.
 */
export function orbitAround(player, { yaw = Math.PI * .85, distance = 3.4, height = 1.25, focus = .95 } = {}) {
  return (camera) => {
    const p = player.position, facing = player.rotation.y + yaw;
    camera.position.set(p.x + Math.sin(facing) * distance, p.y + height, p.z + Math.cos(facing) * distance);
    camera.lookAt(p.x, p.y + focus, p.z);
  };
}

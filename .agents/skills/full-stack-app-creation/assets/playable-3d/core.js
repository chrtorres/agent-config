export const STEP = 1 / 120;
export const SAVE_KEY = "checkpoint-fixture.v1";
export const BEACON = { x: 0, z: -3 };

export function frameDelta(now, previous) {
  return Number.isFinite(now) && Number.isFinite(previous)
    ? Math.max(0, Math.min((now - previous) / 1000, .05)) : 0;
}

export function restore(storage) {
  try {
    const data = JSON.parse(storage.getItem(SAVE_KEY));
    if (data?.version === 1 && [data.x, data.z].every(n => Number.isFinite(n) && Math.abs(n) <= 8)
        && typeof data.reached === "boolean")
      return { x: data.x, z: data.z, reached: data.reached };
  } catch {}
  return { x: 0, z: 0, reached: false };
}

export function createGame(storage) {
  const state = restore(storage);
  let accumulator = 0, pendingInteract = false, saveError = false;
  return {
    update(dt, { x = 0, z = 0, interact = false } = {}) {
      pendingInteract ||= interact;
      accumulator += dt;
      const scale = Math.max(1, Math.hypot(x, z));
      while (accumulator + 1e-9 >= STEP) {
        accumulator -= STEP;
        const clamp = n => Math.max(-8, Math.min(8, n));
        state.x = clamp(state.x + 4 * STEP * x / scale);
        state.z = clamp(state.z + 4 * STEP * z / scale);
        if (pendingInteract && Math.hypot(state.x - BEACON.x, state.z - BEACON.z) < .9) {
          state.reached = true;
          try {
            storage.setItem(SAVE_KEY, JSON.stringify({ version: 1, ...state }));
            saveError = false;
          } catch { saveError = true; }
        }
        // Consume the edge once, even when one animation frame runs several simulation ticks.
        pendingInteract = false;
      }
      return { ...state, saveError };
    },
  };
}

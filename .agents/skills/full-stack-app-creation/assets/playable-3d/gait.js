// A deliberately small pose model for testing contact timing. Distance advances
// the cycle so a one-frame input gap cannot restart an in-progress step.
export function createGait() {
  let phase = 0;
  return distance => {
    phase = (phase + distance / 1.4) % 1;
    return [0, .5].map(offset => {
      const p = (phase + offset) % 1;
      return {
        rise: p < .5 ? 0 : .18 * Math.sin((p - .5) * 2 * Math.PI) ** 2,
        stride: p < .5 ? .35 - 1.4 * p : -.35 * Math.cos((p - .5) * 2 * Math.PI),
      };
    });
  };
}

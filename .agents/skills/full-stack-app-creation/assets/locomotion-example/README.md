# Real-world locomotion example

Run `node --test test-locomotion.mjs` from this directory (Node.js 20 or later, no dependencies).

`locomotion.mjs` is a pure, renderer-free movement model on a measured human baseline in SI units. Game feel is tuned up from these values later, not guessed first.

| Behaviour | Model | Baseline |
| --- | --- | --- |
| Sprint acceleration | Force-velocity: a = a0(1 − v/v0) | a0 8 m/s², v0 8.5 m/s; 30 m in 4.3–5.3 s |
| Braking and cornering | Friction-limited | μ 0.6, so μg ≈ 5.9 m/s² |
| Force development | Low-pass filter on acceleration | τ 80 ms; no single-frame force switch |
| Total horizontal force | Friction circle | ≤ μg, shared by drive, braking and turning |
| Cutting | Speed target scales with cos(turn) | Floor 0.3 of top speed |
| Facing | Rate-limited pivot | 10 rad/s, so 180° takes about 0.3 s |
| Flight | Ballistic, quadratic drag | No air control; terminal speed about 47 m/s |
| Jumps | Takeoff velocity, h = v²/2g | 2.7 m/s standing (0.37 m), 3.3 m/s leap (0.55 m) |

Each test bound comes from a formula, for example a stopping distance of v²/2a + v·τ. When smoothing changes an old expectation, derive the new bound instead of loosening it. The sensitivity test reruns the smoothness check with `forceRise: 0` and `pivotRate: Infinity`, and both must fail.

`jumpReach(speed, takeoff, rise)` gives the ballistic distance to a landing `rise` metres above takeoff. Use it to space level obstacles. A gap that is only a jump at the tuned speed becomes impassable once physics is real.

Measuring takeoff from footage: step through a clip at its native frame rate and count frames from the last ground contact to the first landing contact. Takeoff speed is g·t/2. First confirm the clip is real time, because slow-motion clips are common and give takeoff speeds that are far too low.

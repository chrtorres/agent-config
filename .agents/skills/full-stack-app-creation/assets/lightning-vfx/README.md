# Lightning and mode-start VFX (portable example)

Dependency-free building blocks for an electric weather game: a wide lightning crown around
the player, forked sky and ground strikes, and a main-game/tutorial start resolver. Pass your
own Three.js instance as `T`; the modules allocate geometry once and animate through uniforms.

## Files

- `lightning.js` — pure forked-bolt geometry (`forkPath`, `seededRandom`, `strikePoint`,
  `boltEnvelope`) plus `createBoltMesh` (a fixed, rewritable camera-facing ribbon) and
  `createLightningField` (a pool of sky/cloud bolts that strike on an annulus around a focus
  point and report a proximity-weighted flash level).
- `crown.js` — `createEffectCrown`: counter-rotating helices parented to the character, pooled
  forked ground strikes on a configurable ring, scorch rings, and a one-frame burst shockwave.
  Radii default to ~2.4–3.8 m so the crown reads as wide, not cramped at body scale.
- `start-mode.js` — `resolveStartMode`: `?<param>=` wins; automation (`navigator.webdriver`)
  keeps the tutorial so suites written for the old default still pass; a player with no
  main-mode save opens the main mode; otherwise the save's `active` flag decides.
- `three-stub.mjs` — a minimal Three.js stand-in so the buffer/pool logic is testable with no
  install. It is not a renderer.
- `test-lightning.mjs` — behavioral tests, including a fault case where a ~1 m helix fails the
  wide-crown check and a reduced-motion still-pose check.

## Run

```sh
node --test            # uses three-stub.mjs; no npm install required
```

## Integrating into a real game

- Add `createBoltMesh`/`createLightningField` meshes to the scene and advance `field.update(dt)`
  inside the frame loop while the weather is active. Feed `field.strike(px, pz)` on your own
  cadence; cluster a few strikes and send some `cloud: true` for cloud-to-cloud bolts.
- Parent `createEffectCrown` to the player node, pass the walkable-height sampler as `ground`,
  and drive it with `{ active, intense, burst, reduced }` each frame.
- Bloom: the shaders set `toneMapped: false` and push colors above 1, so an existing
  UnrealBloomPass makes the bolts glow. Without a bloom pass they still draw, just flatter.
- Reduced motion: pass `reduced: true` to hold a dim, still crown and suppress strikes.
- Photosensitivity: when you turn a near strike into a full-screen flash, rate-limit it (one
  flash per ~0.34 s) so clustered strikes cannot exceed ~3 flashes/second.

Colors, radii, strike radius, pool sizes and cadence are constructor options. Generalize any
project-specific names, save keys and world dimensions for your own game.

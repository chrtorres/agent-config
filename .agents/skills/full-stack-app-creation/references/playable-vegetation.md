# Integrate authored vegetation into a playable scene

Use the existing [playable 3D regression](playable-3d.md) and [runtime vegetation asset contract](../../3d-modeling/references/runtime-vegetation.md). Decide which plantings mark a single feature and which create a pair or small grove.

1. Declare planting records with a specimen identity, position, height or scale, rotation, and group and scene membership. Sample the canonical terrain height at each root. Check nearby points for trunk clearance on decks, ramps, paths and shorelines. Use crown bounds and the actual gameplay camera for views near starts, turns and fights. A dry root and a clear path still need a visual canopy check.
2. Cache the import per specimen and share its geometry and materials where the engine permits. Keep placement visibility, pose and instance counts local to each clone. Mount a lightweight silhouette first, substitute the loaded asset when appropriate, and keep the fallback usable if decoding fails. Hide the inactive scene's plantings on a mode change and verify the reverse transition.
3. Choose full-, medium- and far-detail thresholds from visual and frame measurements in the game. Bound how many nearby specimens use full detail. Thin minor geometry and instance counts at medium distance. Let the distant silhouette suggest the same variety. Recompute per-instance bounds when changing instance matrices. For movement near thresholds, watch for popping or thrash and add hysteresis if it is visible.
4. Use local scene materials, lighting and litter to tie trees into the setting. Preserve camera, movement, save origin and environmental interactions. Capture views of a solitary tree and a mixed planting and inspect the character, route edges and intended waypoints. Move a tree if branches block a camera even when its trunk clears collision.
5. Test exact served GLB bytes, decoder resources, all detail tiers, scene visibility, reduced motion where implemented, and a failed asset request. Exercise existing traversal, interaction and save checks. In an isolated negative case, place a root on a protected raised surface and verify that the placement check fails. Record frame cost on the intended backend when making a performance claim.

## Isolated reproduction

Use the existing [playable fixture setup](playable-3d.md#reproduce-the-synthetic-checkpoint-fixture). After creating an isolated app directory, run the optional specimen generator before the production build.

```sh
blender -b --factory-startup --python-exit-code 1 \
  --python <modeling-skill-directory>/scripts/create_planting_fixture.py -- \
  --output <isolated-app-directory>
```

Use a Blender installation with a working Draco encoder. The generator creates a new `public/plant-fixture/` under the copied app and saves editable scenes in the copied app directory. Then install the locked app dependencies and Playwright Chromium as described in the fixture setup. From the copied app:

```sh
npm test
npm run build
CHECK_PLANTINGS=1 npm run smoke -- <fresh-evidence-directory>
```

The additional browser case uses `?plantings` and the **Switch planting layout** button. It checks hashes, instanced crowns and detail limits, movement to a far silhouette, a mode round trip, and fallback after a deliberately missing asset. Use the retained screenshots to inspect the solitary tree and the mixed group. The ordinary playable fixture runs without generating specimens. The synthetic models are intended to exercise delivery and placement. Wind tuning, crown quality, the target game's scenery, GPU performance and physical controller feel require application-specific review.

See [capture decisions and resource disposition](vegetation-capture-provenance.md).

# Material variants capture provenance

## Comparison

Factors are listed in the order outcome, scope, procedure, resources, and validation. Scores use weights 25, 15, 35, 15, and 10.

| Candidate | Factors | Score | Evidence and routing |
| --- | --- | ---: | --- |
| 3d-modeling | 1, .75, .75, .75, .75 | 81.25% | The versioned Blender procedure, photo references, asset-only GLB contract, preview template, and geometry/browser checks already cover most of the workflow. Add shared-geometry variant verification, comparable renders, and a selector that preserves the camera. |
| full-stack-app-creation | .5, .5, .5, .5, .5 | 50% | Its vertical-slice, asynchronous state and real browser validation guidance is relevant to the selector. It has no parametric modeling or Blender/glTF material pipeline. |
| smoke-test | .25, .25, .25, .5, .75 | 33.75% | The synthetic shape and lighting fixture tools and browser checks cover review validation. Its inputs and scope do not cover authoring material variants, comparing pigment layouts or verifying shared geometry. |

Extend the user-named 3d-modeling skill. The addition is optional and uses its existing version, review, and print-approval contracts. The standalone single-asset and multipart templates remain available through their existing entrypoints.

## Feedback and observed outcomes

- The user asked for a detailed researched Japanese koi, then requested more realism, multiple color variants, and an explicit smoke test. The revision refined the anatomy, put close-up scale detail into normal maps, and produced five researched original coats with a shared camera and geometry. The originating revision reimported five GLBs, rebuilt one variant byte for byte, and passed 82 browser checks across the model collection and synthetic smoke fixtures. These are historical results from that run.
- An interrupted preview rendered only part of the collection. The final images were regenerated from the saved scene and verified alongside the other varieties. Keep Blender scene saves independent of render completion and confirm every declared output exists.
- The comparison-sheet script originally relied on a newer Pillow enum. It was adjusted to support both the older constant and the newer enum. The comparison sheet is generated from the final renders.
- The user requested capturing this workflow in 3d-modeling. The retained example reproduces the material pipeline and selection behavior independently of the original creation directory. Screen shading is a visual approximation. The browser checks do not establish print readiness or biological fidelity.

## Resources and boundaries

| Resource | Disposition |
| --- | --- |
| Anatomy generator, pigment layouts and map generation | Bundled as a portable worked example under `assets/material-variant-example/source/`. Expose revision, output, resolution and render controls. Cultivar names and body dimensions are fixture content. |
| Editable scenes, GLBs, texture binaries, preview sheets, and original artwork | Regenerated with the launcher and comparison tool. No large generated deliverables need to be copied into the skill. |
| Selection viewer and rendering modules | Bundled locally as a data-driven template. Three.js 0.180.0 and its required loader/control modules carry the upstream MIT license. See [viewer setup](../assets/material-variant-example/README.md). |
| Blender reimport, shared geometry check and browser assertions | Bundled with the examples and tests. Retain current reports and original high-resolution renders externally with their respective runs. |
| Shell, Blender, browser automation and contact-sheet dependencies | Python, Blender 4.5 LTS, optional Pillow and fonts for the sheet, Node.js with Playwright Chromium for browser validation. These are external runtime prerequisites. |
| Active server configuration, original project paths, results and caches | Excluded from the shared bundle. Generalized revision strings, output paths, service addresses, port, browser-module path, and variant catalog. Raw historical logs and screenshots remain in task storage. |

The geometry fixture is an original visual study. Reference pages guided the palette layouts and the distinction between coarse geometry and visual microstructure. No web images or textures are copied into the example. [Variety standards](https://jnpa.info/en/nishikigoi/varieties/) · [Koi scale microscopy](https://e-journal.unair.ac.id/JMV/article/view/65946)

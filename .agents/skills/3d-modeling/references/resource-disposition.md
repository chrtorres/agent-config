# Resource disposition and provenance

This skill was captured from a completed open-cube-frame modeling run.

| Resource | Disposition | Reason |
| --- | --- | --- |
| Parametric Blender source | Generalized and bundled in `scripts/create_box_frame.py` | Portable authored logic; run paths and names were parameterized. |
| Blender preview source | Generalized and bundled in `scripts/render_preview.py` | Preserves the review step without the original task directory. |
| Generated `.blend` | Regenerated from bundled source | The Blend is version-specific and the examples create a new review file. |
| Historical `.stl` | Kept with the original run | The refinement fixture ends at CAD review. Print exports depend on approval and the requested scale and format. |
| Rendered preview PNG | Not bundled as a required input | The preview is regenerated from the current version and must be reviewed for each run. |
| Blender executable | External prerequisite | Discover `blender` at use time; do not embed an installed application tree. |
| MeshLab and slicers | Optional external prerequisites | Use only when the user requests mesh repair or slicing and record the actual tool/version. |
| User feedback | Sanitized in `comparison-and-feedback.md` | Captures the approval-gate requirement without personal or environment-specific data. |

No credentials, account identifiers, hostnames, usernames, private runtime state, Git metadata, dependency caches, or original absolute paths are required by the skill.

## Interlocking revision

| Resource | Disposition |
| --- | --- |
| Authored rail generator and renderer | Adapted into [the example source](../assets/rail-joint-example/) with caller-supplied paths. The scale-neutral dimensions are fixture geometry. |
| Assembly verifier | Bundled with the example. It checks the generated Blend with Blender's mesh and Boolean APIs. The recipe in [assembly-refinement.md](assembly-refinement.md) runs all three scripts in isolation. |
| Reviewed Blend and two PNGs | Historical artifacts remain with the run. The Blender source regenerates a fixture Blend, assembled preview, and exploded corner. |
| Earlier joined-beam and socket drafts | Historical alternatives remain with the run. The initial simple preview example stays available and the refinement example reproduces the selected approach. |
| Design sources and user feedback | Link the primary standards and manufacturing guides in [assembly-refinement.md](assembly-refinement.md). Preserve sanitized feedback and the historical approval in [comparison-and-feedback.md](comparison-and-feedback.md). |

The fixture uses authored Blender Python plus Blender's bundled modules. Acquire Blender from its official distribution and discover it on PATH. Fresh validation artifacts and project-specific approvals belong with their task evidence. Original run names, dates, workstation and launch paths, and physical print settings are outside the shared package.

## Exploded review and print-part sheets

| Resource | Disposition |
| --- | --- |
| HTML, CSS, JavaScript, and part metadata | Extended the existing [viewer template](../assets/interactive-review-viewer/) with reversible explode and isolation. The empty part list preserves single-model callers. Use caller-supplied names and offsets. |
| Print preview rendering and composition | Bundled [Blender renderer](../scripts/render_print_meshes.py) and [sheet builder](../scripts/build_print_previews.py). They take checksummed, individual STL inputs, use display-only translations, and record original extents. |
| Browser interaction and source objects | The [multipart test](../tests/check_multipart_viewer.py) uses the caller's review or the bundled [synthetic generator](../tests/fixtures/create_multipart_review.py). The generator produces the STL inputs, manifests, Blend, render, and GLB. The existing single-shape browser matrix remains available. |
| Run-specific assets and evidence | Original source and print binaries, model-specific labels and offsets, screenshots, browser profiles, ports, and result logs stay with the originating or fresh run outside this skill. Rebuild synthetic evidence with [the reproduction recipe](multipart-preview.md). |
| External dependencies | Use Blender, Chromium/WebGL, pinned Three.js from its CDN, Python Pillow, DejaVu Sans, and Python websocket-client. No installed dependency tree is bundled. |

## Versioned concept and handoff extension

See [versioned-concept-handoff.md](versioned-concept-handoff.md) for the comparison, feedback trace and resource inventory. New reusable resources are the exact Blend subassembly comparator, its regression test and the cross-linked application lifecycle procedure. Project models, hardware data, renders and current evidence remain with their originating run.

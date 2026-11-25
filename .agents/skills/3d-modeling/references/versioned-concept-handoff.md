# Versioned concept refinement and handoff

Use this workflow when a reference-led concept evolves through several Blender versions, keeps an approved subassembly, and is reviewed through one browser application.

## Geometry and review procedure

1. Freeze the current reviewed version before changing geometry. Record the visual target, the remaining mismatch and the properties that carry forward. Keep each revision in a sibling version directory and make a comparison sheet from the actual renders when the silhouette or composition changes across several revisions.
2. Treat approved subassemblies as immutable inputs. Append or link them into the revision and tag their source. Before handoff, compare the selected mesh topology, vertex coordinates and local transforms with [check_preserved_subassembly.py](../scripts/check_preserved_subassembly.py). The check deliberately allows materials to change for scene presentation. Record any other allowed differences explicitly.
3. Separate appearance geometry from fabrication geometry. Surface perforations, lights and hardware envelopes can communicate a concept when they are labeled as such. Do not count them as functional openings, measured hardware clearances or a cooling validation.
4. For a joined organic shell, verify connected-component count and nonmanifold edges on the evaluated mesh. Check intended seats or contacts separately from hardware interference. A positive contact check confirms the modeled pose. It does not establish attachment strength, insertion access or print fit.
5. Carry materials into the reviewed GLB using a runtime-supported representation. Vertex colors are a portable choice for procedural bands or laminations when the browser must show the same pattern. Inspect the GLB in the browser because a Cycles node graph may simplify during export.
6. Publish only complete revisions in the review application. A complete revision has checks, metadata and the exact GLB together. Preserve a valid saved selection. For a fresh session or a removed saved revision, open the latest complete revision.
7. Keep quantitative labels honest. Use terms such as `estimated`, `assumed` and `pending design` in both metadata and the UI. An empty calculation array must render as a pending state instead of producing a fabricated minimum or a runtime error.
8. At handoff, keep a root `HANDOFF.md` with the current review version, launch command, approval state, verified facts and ordered fabrication prerequisites. Stop temporary preview services. Retain a compact evidence package in the project, then remove only the named smoke sandbox after explicit cleanup approval.

## Acceptance layers

Keep these outcomes separate in checks and handoff language:

| Layer | What it can establish |
| --- | --- |
| Visual comparison | The concept is moving toward the supplied reference from the reviewed views |
| Mesh checks | Component count, manifold state, dimensions, modeled contacts and triangle overlap at checked poses |
| Browser review | The delivered GLB loads, renders, moves, isolates and restores through the actual controls |
| Structural estimates | Behavior under declared simplified loads and assumed material properties |
| Fabrication readiness | Printer-sized parts, joints, tolerances, access, functional openings and checked export meshes |
| Physical validation | Printed fit, cooling, strength and stability on the real support |

Do not promote a lower layer into a higher one. A zero-overlap scan and a working review remain concept evidence while joints, measured hardware and printable segmentation are pending.

## Capture record

The completed workflow was compared against the pre-update skills using the skill-capture rubric.

| Candidate | Factors in outcome, inputs, procedure, resources, validation order | Score | Decision |
| --- | --- | ---: | --- |
| `3d-modeling` | 1, 1, .75, .75, .75 | 85% | Extend. Versioned modeling, multipart review, GLB validation and approval gates already covered most of the method. Add approved-subassembly identity, concept-versus-fabrication labels and cleanup-aware handoff. |
| `full-stack-app-creation` | 1, .75, .75, .5, 1 | 80% | Extend its application-facing portion with version discovery, fallback selection and lifecycle handoff. |
| `product-refinement` | .5, .75, .5, .25, .5 | 50% | Keep as the decision-record dependency. It does not provide Blender identity checks or the review application. |

Historical feedback, paraphrased. The user asked for continuous iteration toward the reference, a running root handoff, and cleanup before another person takes over. The response preserved each visual revision, joined the concept shell, verified contacts and the approved subassembly, exposed every complete draft in one app, wrote a root handoff and packaged current evidence before cleanup. The remaining limits were measured hardware, branch attachments, functional openings, shell joints and the real rolling support.

## Resource disposition

| Resource | Disposition |
| --- | --- |
| Exact subassembly comparison | Generalized as the Blender script and regression test linked above |
| Interactive GLB, multipart controls and smoke runners | Reuse the existing viewer template, multipart test and multi-shape smoke runner in this skill |
| Review-application procedure | Captured in [versioned 3D review applications](../../full-stack-app-creation/references/versioned-3d-review-app.md) |
| Project Blender files, GLBs, renders, inventory, hardware names and dimensions | Stay with the originating project. They are task inputs and evidence |
| Browser profiles, ports, service names, PIDs, caches and dependency trees | Excluded. Discover runtimes and choose task-local identities at execution time |
| Fresh logs and screenshots | Keep in the project evidence package. Shared-skill results remain synthetic and current runs must generate their own evidence |

Generalized categories include usernames, absolute paths, project and version names, port and service identities, hardware identities, measurements, evidence-run names and timestamps. Blender, a Chromium-compatible browser, WebGL and the existing viewer dependencies remain external prerequisites.

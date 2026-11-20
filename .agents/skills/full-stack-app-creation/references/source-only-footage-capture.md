# Source-only editor capture

This optional workflow was routed to the two requested existing skills. Factors follow outcome, invocation, procedure, resources, and validation.

| Existing skill | Coverage factors | Weighted overlap | Evidence and destination |
| --- | --- | --- | --- |
| 3d-modeling | 1, .75, .75, .50, .75 | 77.5% | Existing interactive footage procedure covers projected tracking, local source transport, fidelity checks, and temporary data. Extend with the source-only inference and precise edit procedure. |
| full-stack-app-creation | 1, .75, .75, .50, 1 | 80% | Existing footage review covers the delivery, motion/clock invariants, no-retained-data comparison, and browser acceptance. Extend with the standalone engine, volatile lifecycle, and interaction tests. |

| Resource | Disposition |
| --- | --- |
| Engine, browser, launcher, Python exporter and tests | Bundled as source in the [standalone editor](../assets/footage-editor/). Tests use portable geometry values or take a caller-supplied local session URL. |
| Dependencies and generic models | Exact Python package versions declared. Public MediaPipe model bundles are external and verified by checksum. Node, Playwright and an H.264/WebGL-capable browser are external test prerequisites. |
| Input recordings, previous comparison builds, generated media, stills, landmarks, custom anchors, result hashes, session paths, logs and browser profiles | Excluded. Regenerate in an isolated session from the caller's input. Compare only transiently if an approved reference is available. |
| Acceptance evidence | Rebuild, aggregate browser parity, media timing and audio comparison, source-only audit and session cleanup were exercised. Repeat them for each deployment and keep fresh evidence outside the skill. |

Feedback paraphrases and implementation responses:

- Preserve editing responsiveness and avoid scene-wide waves → keep viewing transforms separate from the rig, retain neutral encoded frames, and confine texture transport to the original and moved silhouettes. Compare distant pixel samples and require a complete neutral reset. Previously occluded texture remains estimated.
- Make fine visible features easy to select and allow edits at unlabeled points → inverse-map stage clicks and magnifier clicks, prefer supported nearby detail, and anchor a custom radius to a tracked feature. Test responsive zoom and range, matched raster coordinates and local changes. A missing anchor temporarily hides a custom area.
- Rebuild the editor from only a supplied recording without retaining personal material → use independent detector passes and a temporary memory-backed session, and keep only sanitized source and tests. Host swap policies and explicit browser downloads remain host-level concerns.

Generalized or excluded names, paths, media identities, session addresses, asset measurements, and user-specific configuration. No previous subject-specific outputs are required to run.

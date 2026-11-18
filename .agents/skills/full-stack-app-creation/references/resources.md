# Resource selection and provenance inventory

This bundle captures the complete relevant reproduction set from the completed local monitoring application and its testing workflow. Locations below are skill-relative. Original task paths, live host state, and runtime identities are deliberately external.

| Candidate / provenance | Disposition and destination | Reproduction / validation |
| --- | --- | --- |
| Completed Linux collector, fixed checks, interpretations, jobs, and fixtures | Bundled in `assets/monitoring-app/monitor.py` | Mocked process/command tests and HTTP job tests |
| Completed HTTP server | Bundled in `assets/monitoring-app/server.py` | Actual loopback requests; explicit route, JSON, Host/Origin boundaries |
| HTML, stylesheet, UI orchestration, pure browser core | Complete `assets/monitoring-app/web/` | Core assertions, syntax, real browser controls, inspected screenshots |
| Python behavior/HTTP tests | `assets/monitoring-app/tests/test_monitor.py` | Uses temporary synthetic process files, tiny subprocess fixtures, and real loopback HTTP |
| Source-manifest regression | `assets/monitoring-app/tests/test_validation_manifest.py` | Authored source includes contracts; dependency/evidence README files are excluded |
| JavaScript core tests | `assets/monitoring-app/tests/test-core.mjs` | Missing data, findings, coverage, chart gaps/time spacing, export source |
| Original browser harness | Generalized `assets/monitoring-app/tests/browser-check.mjs` | Fixture-only default; explicit `--live-host` preserves original real-host coverage |
| Original validation launcher | Generalized `assets/monitoring-app/scripts/run_checks.py` | Fresh output, owned-server cleanup, exact command logs and source hashes |
| Application instructions and scope map | Adapted `assets/monitoring-app/README.md` and `WORKFLOW.md` | Relative links; no original directory/cache/preview identity |
| Serialized contracts and synthetic fixtures | `assets/monitoring-app/objects/formats.json`; inline Python/JS fixtures | Export required fields and source asserted by browser; field contract is documentation, not a validator |
| Developer dependency declaration | `assets/monitoring-app/package.json` and `package-lock.json` | Locked Playwright Core; browser and module remain documented external prerequisites |
| New portable scaffold helper | `scripts/create_app.py` and `tests/test_creation.py` | Isolated import, complete-copy checks, existing-work and symlink-boundary tests |
| General creation, interpretation, and QA decisions | `SKILL.md`, `references/diagnostic-contract.md`, `architecture-and-qa.md`, `dependencies.md` | Self-contained procedure; no sibling skill needed at execution |
| Original raw manifests, requests, logs, exports, screenshots | Preserve raw originals outside the skill; curate/regenerate safe examples under `references/example-evidence/` | Examples explicitly historical/synthetic; no live log or original runtime path copied |
| Reusable graphical references | Synthetic PNGs in `references/example-evidence/` | Generated through the real UI with normalized fixture timestamps; visually inspected |
| Curated command/job/report and HTTP examples | JSON/text in `references/example-evidence/` | Relative routes, synthetic identities, redacted runtime metadata; current raw evidence remains external |
| Visual-example regeneration | `scripts/capture_examples.mjs` | Uses fixture APIs and controlled timestamp normalization; refuses non-synthetic data |
| Bundle identity index | `references/bundle-index.json` | Generated after edits; path/type/size/SHA-256 checks, not semantic validation |
| Original cached Playwright module, Chrome/Firefox installations, Python/Node binaries | Excluded; external dependencies described in `dependencies.md` | Runtime/module discovery or isolated developer install; no original cache path required |
| Git metadata, dependency trees, bytecode, virtual environments, active previews/PIDs, ports, logs and unsanitized host data | Excluded | Not required source; fresh task evidence records actual execution identity |
| Fonts, photos, model weights, compiled objects, archives, credentials, hosting/account IDs | None required; none bundled | Interface uses system fonts, text/SVG/CSS; no account or model integration |

App source is authored/generated task material; no new third-party license grant is asserted. Dependency licenses remain with their packages. Existing baseline diagnostic code inspired this collector; original shared skills are neither duplicated as skill installs nor mutated by this capture.

Generalized categories: usernames, home/workspace paths, original project directory, browser/module installation paths, host/kernel identities in examples, local ports and preview URLs, process/run/job identifiers, device names where environment-derived, screenshot timezone, and evidence timestamps. Runtime versions are compatibility evidence, not machine identity. Fictional demo names/devices and deliberately hostile test strings remain executable fixtures. The universal loopback address, procfs paths, command names, and standard HTTP routes are protocol/platform constants rather than copied host addresses.

The starter differs from the original tested app only in portable packaging/documentation and the explicitly selectable browser-test scopes. Current verification must test this adapted copy. Historical examples do not establish a new host's health or the current source's correctness.

## Storage workflow extension

The storage dashboard and secure native authentication workflow are a related second full-stack example. See [storage-and-jit.md](storage-and-jit.md) for its resource inventory, user feedback, implementation responses, generalized values, prerequisites and limits. The monitoring example and its callers remain intact. New resources are `assets/storage-app/`, `scripts/create_storage_app.py`, `scripts/capture_storage_examples.mjs`, `tests/test_storage_creation.py`, and `references/storage-example-evidence/`.

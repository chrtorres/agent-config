# Capture provenance and resource inventory

User feedback (paraphrase): keep the skill bundles uniform and retain meaningful runnable resources, tests, assets, references and reproduction evidence. Response: extend the explicitly selected skill; preserve existing resources, add synthetic objects and behavioral checks, document limits, and index the complete tree. Current machine-specific commands and outcomes are retained externally, not represented here as historical passes.

## Comparison before extension

Dimension order: outcome (25), inputs (15), procedure (35), resources (15), validation (10). Incoming work is resource completion of the named existing workflow, not creation of another workflow. Explicit user target direction governs this extension.

| Candidate | Factors | Score | Evidence and decision |
|---|---|---|---|
| token-usage | 1, 1, 1, 0.5, 0.5 | 87.5% | Existing SKILL.md covers the same outcome, inputs and decisions; existing resources cover only part of reproduction and acceptance. Extend compatible target. |
| verify-repository | 0, 0, 0.25, 0, 0 | 8.75% | Entrypoint describes a different outcome and input contract; only evidence interpretation overlaps. Preserve separately. |

## Resource disposition

| Resource | Disposition and provenance |
|---|---|
| scripts/ | Bundled authored Python helpers; Python 3.9+ standard library only; no installed dependency tree required. |
| tests/ | Bundled behavioral tests, using temporary directories and synthetic input. Run with unittest discovery. |
| assets/ | Bundled authored report template and explicitly synthetic serialized JSON object; no private user data. |
| references/ | Bundled domain/contract guidance and this resource/provenance inventory; generated SHA-256 bundle index checks identity. |
| Generated sample artifacts | Regenerate with the reproduction command below; fresh outputs belong outside the shared skill. |
| Private session logs, host identifiers, actual review logs | Excluded from portable bundle; user supplies session/repository inputs. Paths, IDs, timestamps, versions and repository identities generalized. |
| Vendor binaries, models, downloaded archives | Not required for bundled synthetic reproduction; real repository validation requires separately acquired, identified, licensed target artifacts. No binary functionality is claimed by fixture checks. |
| Compiled objects and dependency caches | Not needed by these standard-library helpers; JSON fixtures are the reusable data objects. No arbitrary binary or empty directory added for appearance. |

Existing resources were authored in the prior workflow and retained; additions are authored for this capture. Third-party code and assets are not redistributed. No new license grant is implied. Semantic review and privacy checks complement indexing. See reproduction.md for commands and limits.

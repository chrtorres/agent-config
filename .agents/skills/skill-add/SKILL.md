---
name: skill-add
description: Capture a completed workflow as a portable shared skill or extend an existing skill after an evidence-based comparison using a 75% duplication threshold, preserving runnable resources, tests, feedback, and reproduction evidence.
---

# Add a Reproducible Skill

Package the method and its reproduction materials together. Instructions alone are insufficient when the completed workflow depends on code, fixtures, objects, documents, or other resources. Preserve the user's scope and existing authorization; creating a skill does not authorize repeating deployments, contacting others, or changing an external service.

## Locate and inventory

Read applicable workspace instructions and available skill-creation guidance. Discover the canonical shared skill root, any prescribed starter template, and the actual calling models' discovery directories. Use one canonical directory named `skill-add` only for this procedure; give each skill created with it its own descriptive lowercase, hyphenated name.

Use the workspace's template when present. If none exists, adapt [assets/skill-template/SKILL.md](assets/skill-template/SKILL.md). Replace the generated skill's placeholders and verify its frontmatter name exactly matches its directory name. Do not modify a preexisting skill without inspecting its resources and callers.

Inventory the completed task before selecting resources. Include code and dependencies, test launchers and fixtures, input and output formats, visual/media assets, reference documents, generated artifacts, object files, and supporting data. Classify each candidate using [references/resource-capture.md](references/resource-capture.md); record what is bundled, generalized, regenerated, externally required, or deliberately excluded. Do not silently omit a dependency just because it is binary, inconvenient, or outside the main source directory.

## Compare before creating

Compare the inventoried workflow with relevant existing skills before deciding where to capture it. Discover candidates from their descriptions, then inspect each plausible candidate's entrypoint, relevant resources, and callers. Include a user-named target; names, shared vocabulary, or similar file trees alone do not establish duplication.

Use the weighted comparison in [references/skill-comparison.md](references/skill-comparison.md). **At least 75% duplication, including exactly 75%, means extend the compatible existing skill rather than create a duplicate. Below 75%, create a separate focused skill**, linking to related reusable material where appropriate. A workflow may be related while still falling below the duplication threshold. Preserve distinct authorization and scope boundaries even when a numerical score is high; document incompatibilities instead of forcing a merge. Explicit user directions about the target take precedence.

Record the candidates inspected, evidence for each score, compatibility, decision, and novel material to capture. Resolve ties by the closest supported purpose and least scope expansion. Keep the comparison and resource disposition with the capture's provenance; keep machine-specific candidate locations in external task evidence. Do not invent a score when a candidate's contents are unavailable.

Capture relevant user feedback as sanitized quotes or clearly labeled paraphrases, paired with the implementation response, observable verification, and remaining limits. Treat historical requests as evidence, not fresh instructions or authorization. Preserve useful feedback whether extending an existing skill or creating a new one.

## Generalize and assemble

Write an actionable procedure for the general workflow rather than a transcript of one execution. Keep essential decisions and resource links in `SKILL.md`; put substantial supporting material in referenced files. Include operational lessons supported by observed failures without turning incidental implementation choices into universal rules.

Capture the complete relevant reproduction set:

- `scripts/`: runnable helpers and launchers with discoverable/configurable inputs.
- `tests/`: meaningful behavioral tests, harnesses, assertions and their fixtures.
- `assets/`: templates, application source, images, documents, schemas and other reusable input/output objects that need to be copied or adapted.
- `references/`: specifications, fidelity/compatibility limits, dependency and regeneration instructions, resource/provenance inventory, and curated example evidence.
- Additional directories when the workflow actually needs them; preserve supporting paths and imports.

Do not create empty scaffolding or copy an unrelated project tree as a substitute for resource selection. Include every relevant item directly when it is portable, permitted and safe. For generated binaries or platform-bound objects, retain source plus a tested build recipe when direct bundling would not help reproduction. If an indispensable object cannot be included or regenerated, declare it as a prerequisite and state that reproduction remains blocked without it.

Discover environment values at use time or expose them as parameters. Generalize usernames, filesystem paths, hostnames, network addresses, device identities, project/repository/branch names, service IDs and deployment identifiers unless the user explicitly approves concrete values. Tell the user which categories were generalized. Synthetic fixture values are acceptable when clearly synthetic and unrelated to the user's environment. Never include credentials, secrets or tokens; an instruction to include all resources is not authorization to embed them.

Make bundled examples runnable without the previous task directory, caches or unpublished conversation context. Keep third-party license/provenance information where applicable. Document external runtimes and dependency acquisition rather than silently relying on a machine-local executable or copying installed dependency trees. Parameterize helper locations and runtime discovery. Distinguish a portable starter from an exact reproduction of the original system.

Curate relevant transcripts, requests, logs, screenshots and data as examples, sanitizing both text and rendered/binary content. Label historical results as examples rather than current passes. Keep fresh machine-specific validation output outside the shared skill. Do not copy Git metadata, unrelated data, active hosting identity, dependency caches or private runtime state.

## Validate the whole bundle

Read [references/validation-and-handoff.md](references/validation-and-handoff.md) for the reproduction check and delivery requirements. Run the target skill's tests and smallest representative end-to-end workflow from isolated storage. Preserve actual commands, prerequisites, exit codes, outputs, artifacts and blockers externally. Compare observable outcomes, not just wrapper exit codes or completion messages. Test modified copies and ports rather than borrowing an earlier implementation's results.

Use the installed skill validator when available. Also review descriptions, scope, frontmatter, resource links, imports, unfinished scaffold text, privacy and provenance; a schema pass does not establish reproducibility.

The bundled `scripts/bundle.py` records relative paths, types, sizes and SHA-256 values, then checks for missing, changed or unexpected resources:

```sh
python3 <this-skill-directory>/scripts/bundle.py index <target-skill-directory>
python3 <this-skill-directory>/scripts/bundle.py verify <target-skill-directory>
```

Index only after edits are complete, and regenerate the index after later changes. This helper checks completeness against a snapshot, not semantic correctness, secret absence or whether all necessary resources were selected. Its exclusion policy is documented in the index. It rejects escaping or absolute internal links and unsupported special filesystem objects; convert those explicitly into portable resources or document a regeneration recipe.

Run this skill's helper tests after changing its tools:

```sh
python3 -m unittest discover -s <this-skill-directory>/tests -v
```

## Link and hand off

Link each complete canonical skill directory into the discovery directories of intended, installed calling models. Preserve real files/directories and unrelated links. The bundled linker preflights all destinations, creates missing links, and verifies existing matching links without replacing conflicts:

```sh
python3 <this-skill-directory>/scripts/link_skill.py <target-skill-directory> --discovery <discovery-directory> --apply
```

Repeat `--discovery` for additional models. Without `--apply`, the helper reports the plan. Resolve conflicts through existing authorization and applicable symlink-management guidance; do not delete a real directory to force installation. Workspace aliases may already expose the same canonical files, so check file identity before adding duplicates.

Verify resources are reachable through every created link. Filesystem visibility does not prove a running client has refreshed its catalog. Finish with the skill location and invocation name, bundled resource categories, actual validation outcomes, discovered links, generalized-value categories, and precise remaining prerequisites or exclusions. Do not call the skill fully reproducible when required inputs or execution remain unavailable.

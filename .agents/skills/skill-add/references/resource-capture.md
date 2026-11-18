# Resource capture and provenance

Inspect actual task files, imports, relative references, commands, outputs and service dependencies. Do not infer a complete resource set from open editor tabs or a successful final message.

For each relevant resource, record a portable source description, purpose, chosen disposition, destination or regeneration recipe, dependency/version needs, provenance/license, sanitization performed and validation performed. Keep machine-specific paths and IDs in external task evidence. These fields can be a concise table or structured data; do not force a fixed directory shape on unrelated workflows.

| Resource | Capture approach |
|---|---|
| Working code and launchers | Include reusable code and its real execution path; remove task-local imports and discover runtimes. |
| Tests and fixtures | Include test logic, synthetic input, expected outcomes and the runner; test from isolated storage. |
| Templates and app source | Keep the full internally consistent asset tree; remove active service bindings and runtime state. |
| Images, fonts, audio, video and documents | Include relevant permitted assets or document acquisition/generation; inspect for embedded personal data and metadata. |
| Schemas, structured objects and serialized data | Preserve format and version information, safe sample values and reconstruction steps; avoid executable deserialization of untrusted objects. |
| Object files, binaries, model weights or large archives | Assess necessity, portability, licensing and size; bundle safe necessary objects when appropriate, otherwise retain a tested reproducible build/download recipe and identity checks. Never claim an unavailable object is bundled. |
| Logs, transcripts, requests, screenshots and results | Retain useful sanitized examples with scope/provenance labels. Store fresh run-specific evidence outside the skill. |
| Runtime dependencies and external services | Document exact compatibility/pinning needs and discovery/setup instructions; keep credentials external and prerequisites explicit. |
| Shared modules and linked files | Include the required dependency closure or a supported external prerequisite; prevent dangling or escaping internal links. |
| Provider metadata, credentials, caches and unrelated files | Exclude secrets, active project/account identity and irrelevant state; document material omissions without exposing sensitive values. |

“All relevant resources” means another agent has the procedure and material inputs needed to reconstruct the result. It does not mean archiving an entire machine, dependency cache, original Git database, unrelated native repository, or every failed scratch file.

Preserve distinctions between source, executable builds and evidence. A source hash establishes identity, not correctness. A fixture replay does not establish a real external integration. A screenshot of a device frame does not establish device execution. A sanitized transcript is sample data, not a live endpoint configuration.

When copying an established workflow, inspect hardcoded network endpoints, absolute imports, hidden dependencies, output paths and deployment manifests before running the copies. Replace environment-derived values with parameters or discovery, and keep synthetic test values identifiable as synthetic. Do not replace meaningful test inputs with vague placeholders that make the tests non-executable.

The bundle index excludes Git metadata, installed dependency trees, common bytecode caches and local virtual environments by entry name. The exclusions are explicit, not evidence of semantic completeness. If such a directory contains indispensable authored inputs, relocate those inputs into an appropriate portable resource directory before indexing.

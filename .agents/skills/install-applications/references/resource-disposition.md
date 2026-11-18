# Resource disposition and provenance

| Resource or dependency | Disposition | Generalized reproduction guidance |
|---|---|---|
| Application binaries and archives | Excluded | Download from the selected official or distribution source at use time; record release, architecture, URL, and checksum when available. |
| Package-manager metadata and caches | Excluded | Discover package managers and package candidates on the target host; do not copy cache state into the skill. |
| User-local launcher wrappers | Generalized in procedure, not bundled | Create wrappers only when the selected artifact needs extracted AppImage execution or isolated runtime libraries. Resolve the user-local root at runtime. |
| Runtime libraries for extracted packages | Excluded | Acquire only the declared runtime dependencies in an isolated application directory; never embed the original host's dependency tree. |
| Confirmation-gate JSON/list | Generalized in procedure | Generate it from the current allowlist, payment status, source policy, optional exclusions, and installation scope. |
| Version and failure logs | Historical evidence only | Keep fresh output outside the shared skill. Report failures such as missing FUSE, missing shared libraries, incompatible glibc, or unavailable privileges without embedding host paths. |
| User identity, home directory, package sources, release IDs, and paths | Generalized | Use placeholders such as `<user-local-root>`, `<architecture>`, `<host-release>`, `<publisher>`, `<package-name>`, and `<artifact-url>`. |
| Credentials and account state | Deliberately excluded | Never store passwords, tokens, cookies, private account identifiers, or authentication caches. |

The completed example used official Blender, MeshLab, PrusaSlicer, and OrcaSlicer artifacts, but those product names and versions are historical examples rather than defaults. The reusable skill must remain product-neutral and require the user-approved allowlist before acquisition.

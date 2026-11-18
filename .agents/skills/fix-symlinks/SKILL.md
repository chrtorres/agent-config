---
name: fix-symlinks
description: Connect shared agent skills to model discovery directories using symlinks, or repair those links after a shared skill directory moves.
---

# Fix Skill Symlinks

Keep one canonical copy of each skill and link its whole directory into each intended model's skill-discovery directory. Preserve supporting resources alongside `SKILL.md`.

## Procedure

1. Read the applicable `AGENTS.md` and model configuration. Identify the canonical shared skill root and intended discovery directories from the user's request, existing configuration, and installed clients. Use `<shared-skill-root>` and `<discovery-directory>` as configurable inputs; do not embed a previous user's paths or assume every client is installed.
2. Inventory immediate child directories containing `SKILL.md`. Exclude templates and internal directories. Verify that each skill's frontmatter `name` matches its directory name before linking it.
3. Inspect existing discovery entries without following directory symlinks. Use `os.path.lexists()` or equivalent so dangling symlinks count as existing entries. Read link targets with `os.readlink()`; interpret relative targets against the link's parent directory.
4. Preflight all intended links before changing anything:
   - Leave a link unchanged when it already resolves to the canonical skill directory.
   - Create a missing link, creating its discovery parent directory when needed.
   - Repair an existing link only when its old target is demonstrably the relocated shared skill or the user explicitly selected its replacement. A broken link alone does not establish which target was intended.
   - Preserve real files, real directories, and links to unrelated skills. Report conflicting paths and continue with independent, unambiguous entries.
5. Create directory symlinks to the canonical skill directories. Use absolute targets or correctly calculated relative targets. For an authorized replacement, create a temporary sibling symlink and atomically replace the old link; never recursively delete an existing entry. Do not copy skill contents into model directories.
6. If the shared root moved, search relevant workspace files and model configuration for references to the old location. Update only references that identify that shared root. Inspect links inside the moved tree too: changing directory depth can break relative targets. Avoid dependency trees, caches, conversation logs, and unrelated repositories unless evidence points there. Do not move the source tree unless the current request authorizes it.
7. Verify every created or repaired link resolves to the intended directory and exposes a readable `SKILL.md`. Check supporting relative paths where relocation affected them. Recheck the inventory: another run should require no changes.
8. Report the linked skills, discovery directories, verification result, and any unresolved conflicts. Distinguish filesystem verification from confirmation that a running client has refreshed its skill catalog.

## Scope and Portability

- Reuse authorization already given for the same relocation or connection task; do not introduce a confirmation step for ordinary reversible linking.
- Inspect only relevant discovery locations. Do not edit unrelated client settings or create discovery trees for unrequested, absent clients.
- Keep environment-specific values out of this skill unless the user explicitly approves including them. Generalize source roots, destination roots, usernames, repository names, and skill inventories into inputs discovered at execution time. Never include secrets.

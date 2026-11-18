---
name: install-applications
description: Install an explicitly approved set of applications with a confirmation gate, privilege-aware user-local fallbacks, compatibility checks, launcher verification, and honest reporting of failures or substitutions.
---

# Install applications safely

Use this skill when a user asks to install one or more applications and the workflow needs an explicit allowlist, a pre-download confirmation, platform-aware source selection, or verification after installation. It covers Linux-first installations but the decision boundaries generalize to other platforms.

This skill does not authorize installing unrequested applications, bypassing licensing or authentication, changing unrelated system configuration, or silently substituting a different product. Paid applications, administrator changes, external accounts, and optional components must remain explicit.

## Procedure

1. Resolve the requested allowlist and scope. Record application names, required roles, free/paid status when known, optional categories, target architecture, and whether system-wide or user-local installation is acceptable. Remove duplicates and preserve user exclusions.

2. Present a confirmation gate before downloading or installing. List every application, selected source or version policy, payment/licensing status, installation scope, expected downloads, optional items excluded, and any administrator or account requirement. Wait for an explicit confirmation that covers the listed items. A broad request to install software is not confirmation for later additions.

3. Inspect the host without changing it: operating system and release, architecture, available package managers, existing commands, writable user-local locations, and whether non-interactive administrator access is available. Do not request or print passwords, tokens, or private account data.

4. Select an official or distribution-maintained source. Prefer a supported system package when the user has authorized system installation and the required privilege is available. If privilege is unavailable, use an official portable archive, AppImage, user-local package extraction, or another documented user-local method. Use the target architecture and a release compatible with the host; do not assume the newest build is compatible.

5. Stage downloads in a unique temporary directory and install only into the approved scope. Avoid broad or destructive cleanup. For AppImages, test FUSE availability; when FUSE is unavailable, use the vendor-supported extraction-and-run path or extract the image and create a wrapper. For packages extracted without root, collect only the required runtime dependencies into an isolated application directory and expose them through a wrapper such as `LD_LIBRARY_PATH` rather than changing system libraries.

6. Handle compatibility failures explicitly. Capture the actual missing-library, architecture, or runtime error. Check the publisher's release assets and compatibility notes, then retry with a supported build for the host. A compatibility build or older release is acceptable only when it is disclosed and the user has authorized the product installation; do not present it as the latest release.

7. Create discoverable launchers in the approved user-local bin directory when needed. Keep wrappers parameterized, avoid hardcoded usernames or machine paths in reusable material, and make the launcher point to the exact tested artifact.

8. Verify each requested application independently. Prefer a version or help check that reaches the real executable; for GUI applications, distinguish a successful command check from a full visible GUI launch. Report the exact observed version, launcher path, compatibility fallback, failed candidates, and remaining prerequisites.

9. Hand off with the final installed allowlist, commands or desktop entry locations, installation scope, license/payment caveats, and any unused downloads or inactive fallback artifacts. Never claim a failed latest build is installed merely because a compatible older build works.

## Reproduction resources

- [Workflow comparison and routing decision](references/comparison-and-disposition.md) records why this is a new focused skill and how the completed installation was generalized.
- [Resource disposition and provenance](references/resource-disposition.md) records what was intentionally not bundled, how external artifacts are regenerated, and which values were generalized.
- Application binaries, package caches, downloaded archives, user home paths, wrapper outputs, credentials, and machine-specific logs are deliberately excluded. Reacquire artifacts from the selected publisher or distribution source at use time, then verify their compatibility and, when available, their checksums.

## Validation and delivery

Validate the skill structure and links from its canonical directory:

```sh
python3 -m unittest discover -s <skill-add-directory>/tests -v
python3 <skill-add-directory>/scripts/bundle.py index <this-skill-directory>
python3 <skill-add-directory>/scripts/bundle.py verify <this-skill-directory>
python3 <skill-add-directory>/scripts/link_skill.py <this-skill-directory> --discovery <model-discovery-directory>
```

For a real installation, preserve fresh host-specific command output outside the shared skill. A valid verification must show each approved launcher reaching its executable or a documented, reproducible blocker. State when root privileges, a display session, GPU support, vendor account, proprietary runtime, or a compatible release is required. Link this canonical directory into each intended model discovery directory without copying it or replacing unrelated entries.

# Comparison and routing decision

## Incoming workflow

The completed workflow installed an approved set of Linux desktop applications through a confirmation gate, discovered that administrator access was unavailable, used user-local portable or extracted package installs, adapted AppImage and runtime-dependency handling, retried incompatible releases with a host-compatible vendor build, and verified each launcher.

## Candidate comparison

The workspace catalog was searched by descriptions and relevant procedures. The following candidates were inspected as the closest matches:

| Candidate | Outcome / scope | Inputs and procedure | Resources / dependencies | Validation | Score | Decision |
|---|---|---|---|---|---:|---|
| `system-health-diagnostic` | 0: it diagnoses Linux and explicitly forbids package installation or repairs | 0: its procedure prohibits package-manager changes and installation | 0.25: it has Linux/package observations, but no installer or launcher workflow | 0.5: it reports evidence and limits, but does not verify installed applications | 8.75% | Do not extend; incompatible authorization and outcome |
| `full-stack-app-creation` | 0: it builds an application rather than installs arbitrary desktop tools | 0.25: it has runtime/dependency discovery, but different inputs and decisions | 0.25: it contains app dependency setup, not portable desktop-install resources | 0.5: it validates an authored application, not vendor launchers | 12.5% | Do not extend; related dependency concerns are insufficient |
| `verify-repository` | 0: it verifies repository claims rather than changing the host | 0.25: it inspects release assets and compatibility, but does not install an allowlist | 0.25: it has source/release evidence guidance, not installer wrappers | 0.5: it supports executable verification, but not confirmation-gated installation | 12.5% | Do not extend; preserve verification ideas as adapted guidance |
| `skill-add` (user-named) | 0: it packages workflows rather than installs applications | 0.25: it supplies general authorization and resource-capture rules, not application inputs | 0.25: its validators are reusable only for this skill's bundle | 0.5: it validates skill resources, not installed applications | 12.5% | Use as the packaging procedure; create this separate skill |

The largest score is below the inclusive 75% extension threshold. `install-applications` is therefore a new focused skill. The user explicitly requested this generalization, which is compatible with the routing decision.

## Feedback captured

| Sanitized feedback | Response | Observable result | Remaining limit |
|---|---|---|---|
| User wanted a confirmation gate listing the exact applications before installation. | Added a pre-download gate with names, status, scope, and exclusions. | Installation began only after explicit confirmation. | Confirmation is per operation; it does not authorize future additions. |
| User replaced a paid mesh tool with a free alternative. | Preserved the allowlist change and re-gated the final set. | The free alternative was installed instead of the paid product. | Licensing status must still be checked for future products. |
| User wanted the maximum recommended slicer count while keeping scanning optional. | Installed two slicers and excluded the optional scanning category. | The final set contained only the approved four applications. | “Maximum recommended” must be resolved per category before the gate. |
| Newest OrcaSlicer failed on the host because its WebKitGTK/glibc requirements were incompatible. | Used a documented vendor build compatible with the host release and updated the launcher. | The compatible OrcaSlicer build passed the launcher check. | The compatible build was not the newest release; GUI behavior still needs a display-session test. |

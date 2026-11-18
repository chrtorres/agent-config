---
name: device-customization-research
description: Investigate customization feasibility for an owned locked consumer device using existing firmware, REA/Ghidra, primary-source research and authorized read-only interrogation. Produce evidence-based research, a conditional implementation plan and a separate clean-room behavioral specification without beginning customization.
---

# Device customization research

Use for reverse engineering and feasibility investigations where the user needs to know whether an existing device can run a custom interface or local assistant. This skill is a research procedure, not an unlock tool or permission to modify hardware.

## Preserve scope

Start from the user's current authorization and existing evidence. Record the objective, exact model/codename, installed-image identity if known, required functions and execution limits. Resume previous work; repeat a test only for a stated evidentiary reason. A later explicit instruction can change earlier preferences; creating this reusable package does not authorize device testing or customization.

Default device work to authorized read-only identification. Flash, erase, lock/unlock, EFI/security changes, exploit execution, software installation, reboot/continue/mode transitions and payload transfers require appropriate explicit authorization. A proposed temporary boot requires a reviewed exact image/digest, command, full expected effects, failure/recovery behavior and separate approval. Do not probe using empty, malformed or oversized payloads without specific approval. RAM loading and booting are different actions; neither guarantees a non-writing execution path.

Review effects using actual code and trustworthy device-specific documentation. Do not assume safety from a command or function name. Test one device operation at a time, capture a baseline, retain exact commands/outputs/exit codes and stop on unexpected responses, state changes or timeouts. Do not automatically retry or attempt recovery commands.

Read [device-testing.md](references/device-testing.md) before using a live device. The optional [record_queries.py](scripts/record_queries.py) only supports a small fixed getvar list on already-characterized Fastboot targets. It does not establish that those queries are safe on a new platform. Run it only with current authorization, previously observed expected responses, a selected serial and a reviewed plan conforming to [query-plan.schema.json](objects/query-plan.schema.json).

## Investigation loop

1. Inventory tools, repository instructions, original artifacts and existing evidence. Inspect installed CLI help and actual prerequisites before changing setup. Keep downloads/source revisions/hashes and distinguish an available repository from a runnable installation. Use [offline-analysis.md](references/offline-analysis.md) for REA/Ghidra and firmware guidance.
2. Establish exact live identity and separate BIOS/UEFI, bootloader, kernel and userspace versions. Preserve contradictory raw outputs. A version label, USB identifier, fitting image size or certificate subject does not prove installed-byte equality.
3. Select the highest-impact unresolved dependency. Research primary documentation and maintainers' actual compatibility lists; analyze relevant artifacts; cross-check with the live model. Record the finding as answered, disproven within a defined scope, or unresolved for a precise reason. Continue independent branches instead of stopping at the first blocker.
4. Evaluate all relevant paths using the [approach matrix](references/approaches.md): stock apps and installation, debugging, privileges/unlock, modified userspace, alternative OS, drivers, startup persistence and backend integration. Browser/vendor-cloud/physical-acquisition paths can be partial alternatives but must not be passed off as a full replacement.
5. Resolve contradictions by checking original evidence and actual function behavior. Correct earlier conclusions explicitly; retain historical provenance rather than silently converting speculation into fact.
6. Finish when each major branch has a disposition, prerequisites, procedure status, recovery limits and evidence. If no route is established, state exactly what remains unproven and what evidence would change that conclusion. Completion does not require inventing a viable route or creating an exploit. Do not keep circling an uncertainty without new evidence.

## Deliverables and separation

Use [deliverables.md](references/deliverables.md) and copy/adapt the templates in [assets](assets/). Produce RESEARCH.md, IMPLEMENTATION_PLAN.md, ANALYSIS.md and SPEC.md when requested. Scale them to the task; templates are scaffolds, not evidence.

Use **live observation**, **artifact-derived**, **primary-source documentation**, **inference**, **proposed requirement** and **unknown** labels consistently. A static declaration is a fact about a file; it is not a runtime acceptance test. Maintain a structured branch/evidence ledger following [research-record.schema.json](objects/research-record.schema.json). Hash local evidence using [hash_evidence.py](scripts/hash_evidence.py), keeping original paths and source provenance separately.

ANALYSIS, RESEARCH, implementation-derived plans, binaries, databases, disassembly, decompiler output and transcripts remain in the non-clean investigation environment. SPEC contains only reviewed external behavior, requirements, interfaces, state transitions, unknowns and acceptance tests. Exclude proprietary code, pseudocode, internal algorithms and unnecessary implementation details. Do not copy the investigation workspace into reconstruction. This skill package is a method, not a behavioral spec or a substitute for isolated access controls.

Do not begin reconstruction, create a final assistant, deploy a service or modify the device during research-only execution. Document inaccessible output destinations and prepare the complete package in an available workspace; do not bypass host permissions or claim the requested destination was populated.

## Package verification

Run `python3 -m unittest discover -s tests -v` from this skill folder after changing helpers. These tests simulate subprocess outcomes and use temporary files; they must not contact a real device. Review [tests/test_helpers.py](tests/test_helpers.py) for covered safety invariants. Run the installed skill-creator validator if available; its metadata checks do not replace behavioral tests.

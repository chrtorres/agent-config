---
name: comment-code
description: Review an existing codebase and add concise human-readable comments where implementation intent, invariants, security boundaries, or non-obvious behavior could be misunderstood, while preserving behavior and verifying the result.
---

# Comment confusing code

Make an existing codebase easier to understand without turning comments into a duplicate of the implementation. Use this skill when the user asks to comment, explain, document, or clarify confusing code in a project.

## Procedure

1. Read the workspace instructions, the requested project instructions, and any explicitly named skill. Resolve the target directory and preserve unrelated user changes. Do not infer permission to refactor, reformat, rename, or change behavior.

2. Inventory authored source, launchers, tests, configuration, and relevant documentation with the repository's normal file-discovery tools. Exclude dependency trees, caches, generated evidence, build output, and vendored code unless the user explicitly includes them or they contain authored logic that must be documented. Inspect imports, entrypoints, tests, and documentation so comments describe the actual contract.

3. Identify code that a competent maintainer could reasonably misread. Prioritize:

   - non-obvious algorithms, transformations, field indexes, bitmasks, units, thresholds, or accounting rules;
   - intentional omissions, fallback states, deduplication, ordering, cache expiry, persistence, or lifecycle decisions;
   - security and authorization boundaries, input validation, fixed command arguments, trust boundaries, and safe rendering;
   - concurrency, cancellation, retries, request identity, stale-data handling, and race prevention;
   - compatibility workarounds and behavior that is constrained by an external format or API.

4. Add comments at the smallest useful scope, near the decision they explain. Prefer one or two plain-language lines describing why the code exists, what invariant it preserves, or what a value means. Use the host language's normal comment style. Explain behavior that is not obvious from names and structure; do not narrate assignments, restate the next line, speculate, or encode temporary task history as permanent documentation.

5. Keep comments accurate and portable. Use discovered paths, identifiers, versions, and environment values only as task-local evidence; do not copy secrets, tokens, private data, hostnames, device identities, or user-specific paths into the reusable workflow. Preserve existing documentation and comments unless they are inaccurate or materially misleading. Do not add comments that imply stronger guarantees than the implementation or tests establish.

6. Review the resulting changes as a maintainer would: check placement, wording, spelling, stale claims, and whether each comment answers a likely misunderstanding. Confirm that only intended source files changed. Run syntax checks and the smallest relevant tests, then run a broader project check when it is available and proportionate. Comments should not change behavior; a failure is still a regression to investigate, not a reason to skip verification.

7. Report the commented files and the categories clarified, excluded/generated areas, verification commands and outcomes, and any remaining uncertainty. If a confusing behavior is actually a bug, describe it separately and do not silently fix it unless the user requested implementation changes.

## Reproduction resources

- [Commenting checklist and decision rules](references/comment-checklist.md) defines the review boundary and examples of useful versus noisy comments.
- [Workflow provenance and comparison](references/provenance.md) records the originating task, candidate-skill comparison, resource disposition, feedback response, and validation evidence. Its machine-specific paths are generalized.

This skill intentionally bundles no project source, dependency tree, screenshots, generated evidence, or executable helper. Reproduction requires the user's target codebase and its own documented runtime/test dependencies. Discover those at use time rather than copying the source tree that produced this skill.

## Validation and delivery

At minimum, run the target language's syntax/type check and the focused tests covering the edited modules. Prefer the project's existing validation command when it is available. For a browser or service project, exercise the affected HTTP/UI path when the comments were added around integration behavior. Record fresh logs or screenshots outside this canonical skill directory.

Deliver the canonical skill from `agent-config/.agents/skills/comment-code/SKILL.md`, linked into each intended model discovery directory. The invocation name is `comment-code`. State which environment-specific categories were generalized and identify unavailable runtimes, excluded generated/dependency material, and any unverified integration limits.

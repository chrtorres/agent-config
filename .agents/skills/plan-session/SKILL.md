---
name: plan-session
description: Turn a product idea or feature request into a focused, implementation-ready user-story markdown document without changing application code.
---

# Plan a feature session

Convert a user's product intent into a concise user-story document that separates the current experience from future work. Use this skill when the user wants to start planning a feature, define a user story, or capture scope before implementation.

## Procedure

1. Read the applicable workspace instructions and inspect nearby documentation conventions. Identify the relevant repository or project location without assuming the workspace root is a Git repository.
2. Extract the request into four parts: target user, desired action, user benefit, and named constraints. Preserve product terminology such as route names, modes, permissions, and device contexts.
3. Write a markdown document with these sections:
   - A descriptive title.
   - A first-person or standard user-story statement using “As a user… I want… so that…”.
   - Current scope: the behavior requested now.
   - Acceptance criteria: observable outcomes that can be checked later.
   - Non-goals: explicitly excluded behavior for this iteration.
   - Future direction: deferred capabilities that should not be mistaken for current scope.
   - Product or implementation notes only when they clarify boundaries or future extensibility.
4. Make view-only, read-only, permission, persistence, or mutation boundaries explicit when the request includes them. Distinguish navigating or inspecting something from modifying it.
5. Generalize future ideas into product capabilities without turning them into implementation commitments. Retain examples of possible interaction methods when the user supplied them.
6. Create or update only the requested documentation. Do not implement the feature, modify application behavior, add dependencies, or make unrelated cleanup changes.
7. Validate the document by checking that the story, acceptance criteria, non-goals, and future direction agree; confirm that every criterion is observable and that deferred work is clearly labeled.
8. If the user separately requests repository hygiene, use the applicable Git workflow to inspect the exact repository and make the smallest requested `.gitignore` change. Do not infer ignore rules or stage, commit, or push without authorization.

## Reproduction resources

This skill has no required code, fixtures, external services, or binary assets. The output is portable Markdown. The source request is the only required input; project-specific paths, route names, device names, account identifiers, and repository names must be discovered at use time or represented as placeholders in reusable examples.

Recommended output shape:

```markdown
# User Story: <descriptive title>

## Story

As a <user>, I want <action>, so that <benefit>.

## Current Scope

- <requested behavior>

## Acceptance Criteria

- <observable outcome>

## Non-Goals for This Iteration

- <explicit exclusion>

## Future Direction

- <deferred capability>
```

Do not copy task-local transcripts, absolute paths, private identifiers, credentials, generated runtime state, or implementation artifacts into the skill.

## Validation and delivery

Perform a focused documentation review:

- The user story names the user, action, and benefit.
- Current scope contains only requested first-pass behavior.
- Acceptance criteria describe observable behavior rather than implementation details.
- Non-goals prevent scope creep.
- Future direction is clearly deferred and does not imply current functionality.
- View-only or mutation boundaries are unambiguous when relevant.
- No application source files were changed.

Report the created or updated Markdown path, summarize the scope captured, and state that implementation was intentionally not performed. If a repository hygiene change was explicitly requested, report its exact file and validation separately.

---
name: full-stack-app-creation
description: Take a full-stack application from requirements through architecture, implementation, meaningful code comments, backend integration, browser testing, and runnable delivery. Includes monitoring, native authorization, interactive live-state examples, and code-generated video delivery.
---

# Full-stack app creation

Turn a user's idea into a working, inspectable application. Own the path from intent and product definition to implementation, verification, and delivery. Choose the architecture that fits the task. The bundled applications illustrate different choices.

## Shape the idea

Read workspace instructions, existing source, and prior decisions. Identify the user, problem, primary workflow, expected outcome, constraints, and delivery environment. Distinguish essential behavior from optional polish. Resolve routine choices autonomously; ask focused questions only where missing information changes the product materially, while continuing independent work.

Write a compact task-local product brief: target users, main journey, acceptance criteria, data sources, persistence, integrations, permissions, and explicit first-pass exclusions. Translate vague aspirations into observable actions and outcomes. Do not impose the worked example's domain or read-only restrictions on unrelated applications.

## Design the product and architecture

Choose the smallest architecture that supports the requested behavior. Decide frontend, backend, data model, API contracts, state ownership, authentication where needed, persistence, integrations, and runtime/deployment requirements. Reuse the user's stack and existing application when appropriate. A buildless interface and standard-library backend are options, not defaults that override the task.

Define screens, navigation, loading/empty/error/success states, responsive behavior, accessibility, and the primary interaction path. Distinguish real services from fixtures. Identify trust boundaries and protect secrets. Discover runtime paths, ports, project identities, and available tools rather than copying a previous environment.

When Sites or another specialized development/hosting workflow applies, read and follow its current skill. Hosting, account changes, and external actions remain within the user's authorization; creating this skill grants no additional permissions.

For apps needing local privileged reads, use [storage-and-jit.md](references/storage-and-jit.md): keep the server unprivileged, put explicit authorization behind a native system prompt, and distinguish retained measurements from retained authority. A password textarea is not the default authentication design. This reference captures the user's feedback and the tested implementation response.

## Implement a complete vertical slice

Build the core user journey through the actual frontend, backend, and storage or integration layers it needs. Keep business behavior separate from rendering and expose explicit contracts. Connect visible controls and completion states to real returned data and stored outcomes.

Extend the slice to the agreed scope: input validation, meaningful errors, cancellation/concurrency where relevant, persistence/reload behavior, exports, and permissions appropriate to the product. Use deterministic fixtures for reproducible tests and label simulated behavior. Render untrusted text safely. Avoid decorative controls that imply unimplemented functionality.

Develop a coherent visual direction suited to the product. Inspect usable screens early and refine observed issues. Respect reduced motion, keyboard access, responsive navigation, and legible supporting copy.

Apply [comment-code](../comment-code/SKILL.md) during implementation and before handoff. Explain the intent of non-obvious algorithms, state transitions, trust boundaries, concurrency, units, and compatibility decisions beside the code that implements them. Read the surrounding code and tests before describing a contract. Check comments for accuracy and portability, and run the affected syntax or type checks and behavioral tests after comment edits.

## Verify the actual application

Derive checks from the acceptance criteria and risks rather than copying the example's test matrix wholesale. Test meaningful business outcomes, failure states, boundaries, and persistence. Exercise real HTTP or service traffic when claiming integration; fixture results do not establish a live integration.

If the user supplies an acceptance threshold, declare its scoring rubric and critical gates before running it. Label engineering acceptance separately from human usability measurements; a passing permission-denied test does not establish a successful privileged integration. Recheck access after dependency installation, then arrange an authorized human test when native authentication is necessary.

Drive the actual browser through the primary journey and important error paths. Wait for observable completion. Compare rendered state, backend results, stored bytes, and downloaded artifacts where relevant. Test relevant viewport sizes and keyboard interactions. Inspect settled screenshots alongside assertions.

For animated interfaces wired to live state, verify that controls cause real motion or geometry changes. Wait for a rendered state before measuring it. When modifying a regression check, reproduce the defect or inject a narrowly scoped fault in an isolated copy to show the check still rejects it. See [the live-state example](references/live-state-and-browser-qa.md) for fixture isolation, low-resource browser rendering, and local review practice.

When extending a playable browser 3D app, use [playable 3D regression and delivery](references/playable-3d.md) for a fixed-step simulation, frame-aware input checks, same-origin saves, controller acceptance, frame-by-frame pose continuity, and an isolated production-build smoke test.

Use isolated task storage and explicitly declared dependencies. Preserve actual commands, working directories, runtime versions, exit codes, assertions, screenshots, relevant requests/artifacts, and a manifest tying evidence to authored source hashes. Exclude dependency trees, credentials, runtime identities, and private data from reusable resources. Record failures and rerun checks affected by fixes; do not borrow another application's passing results.

## Evidence-linked review

When an interface explains real structures or factual relationships, use [evidence-linked review](references/evidence-linked-review.md). Carry research and uncertainty into the data contract and inspection UI. Test that selections change the rendered artifact and restore its state, then validate factual claims against independent evidence.

## Animated 3D review

Use [animated playback review](references/animated-playback-review.md) when a browser app needs clip selection, scrubbing, transport controls, camera tracking, or animated poses alongside static inspection. Validate rendered geometry and state transitions against the same GLB delivered to the user.

## Code-generated video delivery

Use the shared [Python and Blender video workflow](../3d-modeling/references/code-video.md) when an application generates or serves video. Exercise the actual encoder output through the download and playback path. Verify MIME type, byte ranges, rendered motion, seeking and playback in the target browser. Keep generation and encoding outside the request path when they need a background job, and publish the file after a successful encode. The shared synthetic example supplies an MP4 generator, a reference-preserving remux, a comparison command and a browser smoke harness.

## Composing live and inspection views

Use [multiview review architecture](references/multiview-review.md) to combine existing interactive scenes under a compact tab shell. Test lazy startup, playback suspension, camera preservation, keyboard navigation and independent load failures.

## Secondary motion studies

Use the [suspension example](assets/suspension-example/README.md) for a fixed-step companion view that drives named model pivots with documented support input, joints, readouts and reset behavior. Verify the shared GLB download by bytes and the live study by both node transforms and settled frames. See the [capture decision](../3d-modeling/references/registered-assembly-provenance.md).

## Deliver and iterate

Provide the verified running view or build artifact, a specific starting action, retained runnable source, setup instructions, evidence, and material limitations. For hosted delivery, publish the exact prepared source through the active provider workflow and verify the deployment result. For a requested local running application, retain its preview when supported and document its lifecycle in task evidence.

Assess the delivered result against the original acceptance criteria. Report incomplete integrations or verification honestly. Incorporate feedback into the same objective rather than treating an initial prototype as automatic completion.

## Reproduction resources

Read [worked-example.md](references/worked-example.md) when using the captured application. The complete example includes frontend/backend source, API/format contracts, fixtures, test harnesses, a dependency lockfile, creation and validation helpers, and curated visual evidence. These resources demonstrate one reproducible vertical slice; adapt or replace them for other domains/stacks.

```sh
python3 -B <skill-directory>/scripts/create_app.py --destination <new-app-directory>
```

This helper copies the monitoring worked example into a new task directory without overwriting work. It is not a general-purpose framework generator. From the copied example, its validation runner supports fixture-only browser QA and an explicit authorized live-host mode. Read [dependencies.md](references/dependencies.md) before running those checks.

For other applications, retain an equally complete implementation and validation set suited to their actual architecture. Generalize environment values and keep fresh evidence outside the shared skill.

The optional [storage and JIT example](references/storage-and-jit.md) includes a second complete source tree, portable creation helper, original generic shell input, fixtures, locked QA dependencies, and scan security tests. Use `scripts/create_storage_app.py --destination <new-app-directory>` for that domain; read its copied README before choosing fixture-only or explicitly authorized live validation. Its historical acceptance score is not a guaranteed outcome for another app.

Use `scripts/create_app.py --example activity-town --destination <new-app-directory>` for the [Activity Town example](references/live-state-and-browser-qa.md). It includes a Vite and Three.js frontend, a local Node activity relay, synthetic sessions, and Playwright checks for rendered geometry, navigation, and privacy.

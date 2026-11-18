---
name: live-app-recreation
description: Build, browser-test, and present an interactive live view of an app or an explicitly accepted behavioral recreation, with captured source, observable outcomes, and clear fidelity limits.
---

# Live App Recreation

Turn an app workflow into a live, inspectable experience the user can operate. Retain the code and evidence behind the demonstration. Distinguish testing the original application, testing a recreation, and presenting an animated mockup.

## Bundled implementation and validation kit

Read [references/bundled-resources.md](references/bundled-resources.md) when reusing the captured code, launching the example, or running its checks. The kit contains a Python HTTP/SSE agent and scripted server, a complete browser-local phone interface, behavioral and browser tests, preview/validation scripts, portable example evidence, and visual references. Copy and adapt assets into a task workspace; do not treat the example agent's features as requirements for every app or edit the shared starter to hold a task's state.

## Establish what the live view represents

- Read applicable workspace instructions, existing source, prior review results, and user decisions. Reuse the existing recreation when one exists.
- Identify the behaviors the user wants to see, the intended screen/device reference, available runtimes, and whether the requested result is local, hosted, or embedded in conversation.
- If the original runtime is unavailable, continue with an already authorized recreation. Otherwise explain the limitation and obtain agreement before substituting one. Agreement to a recreation does not establish device compatibility.
- Define a compact fidelity map: original behavior, recreated behavior, meaningful differences, and evidence needed. A phone frame or viewport is a layout reference, not execution on that phone or emulation of its processor and operating system.
- Discover paths, browser executables, ports, tools, dependency versions, and hosting identifiers at execution time. Keep concrete values in task evidence rather than this skill.

## Build real interactions beneath the animation

Choose the smallest architecture that satisfies the requested behavior. A static HTML/CSS/JavaScript application often suffices for browser-local demonstrations. Use a server when behavior genuinely depends on server execution or an existing backend. When website tooling such as Sites is available, follow its current skill and supported preview/publication workflow rather than reproducing provider-specific commands here.

Keep the behavioral core separate from rendering so its operations can be tested directly. Connect tool activity, approval dialogs, file views, and completion messages to actual state changes. Do not infer success from the assistant's final text or a decorative success badge.

For an agent-style recreation, useful interactions include:

- A composer, streamed response animation, expandable tool output, and progress activity.
- An actual isolated or virtual workspace with read/create/edit/search operations.
- Approval and denial before mutation; file previews reflecting the stored result.
- Conversation history, stop, settings, reset, persistence, and export when relevant to the requested scope.

Use deterministic fixtures to make demonstrations repeatable. Label scripted responses and simulated storage where users can understand them. A scripted model tests tool execution and UI orchestration; it does not test model reasoning or local inference. If a setting only previews appearance, label that limitation or omit the control.

When porting an existing recreation into a browser runtime, preserve relevant behavior and test the port. State whether the live view calls the existing backend or implements a separate browser-local core; previous backend test results do not establish browser correctness.

Match the requested visual reference with responsive layouts, transitions, and legible controls. Provide a guided walkthrough and a manual path. Pause for real approval decisions rather than silently approving changes. Honor reduced-motion preferences and make controls keyboard accessible. Render user messages, file contents, and tool output as text rather than interpolating untrusted HTML.

## Test the live experience

Follow the active environment's preview and browser-automation rules. Use an available supported browser or an isolated compatible automation dependency where permitted. Do not invent a browser pass when only source checks ran.

Run focused behavioral checks on the core, then drive the actual interface in a browser. Navigate to the relevant screen before interacting with a control. Wait for observable state or completion signals rather than relying on arbitrary delays. Verify meaningful user outcomes:

| Interaction | Evidence to inspect |
|---|---|
| Initial load and response | Served page, usable composer, resulting message, runtime errors |
| Tool execution | Actual returned data and corresponding tool card |
| Approved create/edit | Stored file content and file viewer agree |
| Denied create/overwrite | New file absent or original content unchanged |
| Workspace boundary | Out-of-scope operation rejected without leaking or mutating external data |
| Stop during work or approval | Composer released; pending approval resolved; stale run does not execute later mutations |
| History and reload | Correct conversation, files, and relevant settings retained |
| Reset | Documented initial state restored without unrelated changes |
| Walkthrough | Full interaction sequence completes through actual controls and approvals |
| Responsive view | Relevant viewport remains usable, without horizontal overflow or clipped essential controls |

Adapt this matrix to the app rather than adding unrelated features solely to fill it. Capture genuine backend HTTP traffic when the claim includes networking; a browser-local function call is not an HTTP integration test. Distinguish real service tests from deterministic fixtures.

Inspect representative screenshots as well as assertions. Capture settled frames after the intended state is visible; text assertions alone do not reveal blank screens, unreadable controls, or misleading visual status. Retain failed-run details that explain material fixes, then rerun checks affected by those fixes. Do not repeatedly rerun passing suites without a reason.

## Deliver the running view and retained evidence

Keep new task outputs outside the reusable skill. Curated portable examples already bundled with this skill are reference fixtures, not evidence of a new run. Retain:

- Runnable source and concise instructions identifying required runtimes and dependencies.
- Fidelity map and scope limits, including excluded features and simulated services.
- Test commands, working directories, runtime versions, exit codes, actual assertions and outcomes.
- Representative screenshots and relevant transcripts, requests, file artifacts, or state exports.
- A machine-readable result or manifest connecting source revision or hashes to the tested build.

Serve and verify the local preview before opening it with an available handoff tool. For hosted delivery, follow the active hosting skill, reuse persisted project identity, preserve the audience, publish the exact prepared source/build, and wait for a successful deployment result. Keep credentials out of files and tool output. Do not treat an expected URL or a pending deployment as a live result.

Open the successful hosted view when supported. Stop an owned temporary preview server only after the replacement is available and handed off; retain a local server when it is the requested live deliverable and the environment supports that lifetime.

Finish with the live link, a specific starting action, a brief statement of what passed, a source/evidence link, and the material simulation limits. The user should be able to operate the result without reading the work log.

# Activity Town

Activity Town is a Three.js diorama that follows a local Codex session. Its original toy robot walks between a two-floor Town Hall, Documents, My Pictures, and Workshop as it picks up tasks.

## Run locally

Requires Node.js 20.19 or later and a browser with WebGL 2.

```sh
npm ci
npm run dev
```

Open the loopback URL printed by Vite. To run the production bundle, use `npm run build` followed by `npm start`. The server listens on `127.0.0.1:4173` by default. Set `PORT` to use another port.

- Drag to orbit, right-drag or use the focused canvas's arrow keys to pan, and scroll or pinch to zoom.
- Use **Follow agent** for tracking or **Overview** for a stationary aerial camera. The camera height slider changes elevation. The reset button restores the opening framing.
- Cycle **Both floors** to reveal each Town Hall interior. Select a building to inspect it in a live session or send the robot there in the demo.

## Connect to Codex activity

The local server follows the current IDE session when it inherits `CODEX_SESSION_ID`. Otherwise it looks for the most recent eligible primary session in the workspace. Start the server from the same Codex environment or configure the source explicitly.

| Environment variable | Purpose |
| --- | --- |
| `ACTIVITY_TOWN_WORKSPACE` | Absolute path to the workspace being monitored. Defaults to the repo folder, or the workspace containing a versioned creation checkout. |
| `ACTIVITY_TOWN_SESSION_ID` | Select a specific session. Set it to an empty value to discover a recent workspace session. |
| `ACTIVITY_TOWN_CODEX_HOME` | Set the local Codex data directory. Defaults to the configured Codex home or the standard user directory. |

The browser receives a masked session ID, a state, a destination, a generic activity label, and an update timestamp from the same loopback origin. The relay reads local session records to classify events. It sends document and image actions to their respective buildings, shell and development actions to Workshop, and idle sessions to Town Hall. Generic tool activity can only be classified as broadly as the available events allow. The interface shows **Demo activity** when it cannot find an eligible session.

Configuration is resolved by the local server. The frontend build receives no environment variables and includes only the bundled scene, styles, and fonts. Use server-side environment settings for session selection. Keep local session files and review evidence outside release archives.

## Geometry and review

The geometry lives in `src/buildings.js` and `src/landscape.js`. One scene unit is one meter at the nominal miniature scale. The landscaped base covers roughly 53 × 36 units. Town Hall covers 16 × 12 units and has two levels with three cubicles each. The browser preview displays the same Three.js scene used while tracking activity.

## Smoke testing

```sh
npm run smoke -- --evidence <new-directory-outside-this-repository>
```

The suite builds an isolated checkout, starts two loopback servers with synthetic Codex records, and tests desktop and mobile rendering, camera controls, the office cutaway, robot routes, and redaction. It saves results and screenshots in the supplied directory. It uses `BROWSER_PATH` if set, otherwise it tries a system Chrome or the Playwright bundled browser. To install that browser, run `npx playwright install chromium`.

Use the same smoke command against the reviewed candidate and the integrated revision when publishing through an authorized Git workflow.

## Local pull request review

Review changes in the local checkout. Have engineers who did not author the change compare the feature revision with its base. Ask them to exercise the main user path and an edge case that could pass a superficial check. For example, the floor selector smoke check compares rendered pixels so a label change alone cannot pass it.

Keep review findings and decisions in the local evidence directory. Record the exact revision, affected file and line, reproduction steps, severity, and whether the reviewer approves or requests changes. Fix correctness, privacy, and regression blockers, then ask the local reviewers to recheck the updated revision. The GitHub pull request tracks the change and CI status.

Run smoke tests on the reviewed feature revision before merge and on the resulting `main` revision after merge.

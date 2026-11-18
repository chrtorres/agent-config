# User acceptance test: `<feature name>`

Candidate: `<isolated directory or build identifier>`  
Launch: `<command>`  
URL: `<loopback URL>`  
Tester: `<name or initials>`  
Date: `<YYYY-MM-DD>`

## Prerequisites

- [ ] The candidate process, not another implementation, owns the test port.
- [ ] Required runtime/dependencies are available.
- [ ] Test data or device is connected and safe to inspect.
- [ ] The tester understands which actions may open an authorization prompt.

## Primary journey

| Step | Tester action | Expected result | Actual result / evidence | Pass? |
| ---: | --- | --- | --- | :---: |
| 1 | Open `<URL>` and navigate to `<screen>` | `<initial state>` |  |  |
| 2 | Select `<control>` | `<visible control response>` |  |  |
| 3 | Approve or decline `<prompt>` | `<progress or cancellation state>` |  |  |
| 4 | Wait for completion | `<success output and timestamp/state>` |  |  |
| 5 | Refresh or repeat as applicable | `<session/persistence behavior>` |  |  |

## Boundary cases

| Case | Action | Expected result | Actual result / evidence | Pass? |
| --- | --- | --- | --- | :---: |
| Cancel | `<action>` | `<no later action / clear cancellation>` |  |  |
| Duplicate | `<action while busy>` | `<blocked or safely coalesced>` |  |  |
| Permission/error | `<deny or induce safe fixture error>` | `<actionable error; no unsafe mutation>` |  |  |
| Unsupported input | `<input>` | `<validation response>` |  |  |

## Verdict

- Primary journey: `<pass / fail / blocked>`
- Boundary cases: `<pass / fail / blocked>`
- First failing step: `<step or none>`
- Evidence: `<paths or links>`
- Notes and follow-up: `<details>`

# Controlled device interrogation

## Before a command

Identify the exact unit and current mode without changing it. User authorization for a previous session or model is not evidence of current device state. Read retained commands and outputs before planning a repeat. Document known firmware mismatch and unsupported/empty variables. Empty successful getvar output does not enumerate implemented features.

For uncertain commands, trace dispatcher permissions, handlers, callbacks and success/failure paths in the applicable implementation. Inspect host-client behavior too. A helper named get, read, stage or log can invoke setters, execution, logging or mode changes. A stub in one acquired image does not attest the installed fork. Upstream source describes upstream, not an OEM's shipped behavior.

Define a baseline and expected result from previously obtained evidence. Where a known read-only state-report query is available, compare identity/security fields and the full stable map around each operation. A report-level equality check cannot prove that no hidden logging or storage change occurred. A device-node permission fix enables transport access, not arbitrary command authority.

## Optional helper

`record_queries.py` accepts only explicit plans; it never discovers a serial, uses sudo, downloads data, runs an OEM command, retries or boots an image. Supply an absolute Fastboot executable, output path and plan. Plan example structure is in objects/query-plan.schema.json. `baseline` must include product, version-bootloader, device-state and secureboot with exact previously observed strings; additional stable fields may be included. Each requested query must also have an exact expected response. It captures full getvar-all maps around each query and stops if any map differs from the initial map.

Do not fill a plan with guessed values. Do not run it if getvar-all is not already reviewed for the current target. It writes a fresh JSONL journal exclusively and records each response before assessing it; a failing baseline stops the test before any planned query.

## Stop and recovery

A failure/timeout/unexpected result ends device commands. Preserve the last known state and partial journal. Killing the host client does not prove target recovery. Reboot, disconnect/power-cycle, retry, clearing a staged buffer or entering recovery can change mode or persistent state and are not automatic fallback actions.

Before a separately approved boot trial, identify exact file bytes/format/hash, signatures/trust, startup write paths, expected UI/serial/network behavior, bounded observation, return/re-entry and independent rollback. Booting a factory OS is not a no-write diagnostic. A rejected image can itself trigger a reboot. No boot command or payload-test script ships with this skill.

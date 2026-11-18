---
name: token-usage
description: Report measured token usage for a live or completed session from available usage telemetry, track live changes on request, and distinguish cumulative usage from context size and labeled text estimates.
---

# Token Usage

Use at any point in a conversation to report usage so far or start requested live tracking. For a completed session, return its final recorded total. Model parameter counts describe learned weights, not input capacity; input capacity is measured in tokens.

## Select the source

Prefer platform usage telemetry or session logs over text estimates. For local Codex JSONL sessions, use `scripts/token_usage.py`. With no file argument it identifies the current session from `CODEX_THREAD_ID` or `CODEX_SESSION_ID`, under `CODEX_HOME` (falling back to the user's Codex directory). It requires an unambiguous matching file. Never assume the newest file is the current conversation.

For a past session, supply its JSONL path. If the user has not identified the past session, use available session metadata to resolve it, or ask which session. Do not read unrelated message bodies or expose authentication/configuration files. Other clients require their own documented usage adapter; do not treat their log formats as Codex telemetry.

## Invocation

Run from the skill directory, using the discovered Python interpreter:

```sh
python3 scripts/token_usage.py
python3 scripts/token_usage.py '<session-jsonl>'
python3 scripts/token_usage.py --watch --interval 10
```

The default prints one snapshot. For requested ongoing tracking, launch watch mode asynchronously and retain its process/session handle so it can be polled and stopped. Poll and communicate during active work. Stop on user request or when the requested observation period ends. Do not promise background monitoring after the tool process or conversation ends. Merely loading a skill does not install a persistent tracker.

Read the latest valid cumulative `total_token_usage` snapshot; never sum cumulative snapshots. Report last-call usage separately. Repeated events, compaction, resumed sessions, and log refreshes do not justify adding totals together. If counters regress, logs are incomplete, or session coverage is uncertain, disclose that limitation rather than inventing a whole-session total.

## Interpretation and output

Report source, telemetry timestamp, recorded input/output/total tokens, and cached input when present. Cached input is generally a subset of input and reasoning output a subset of output; preserve source counters without adding either again. Do not infer price from token totals without the relevant model, pricing, and billing semantics.

For a live report, say “as of the latest recorded event”; the current response and in-flight requests may not yet be counted. For a post-session report, say “final recorded total” and only claim complete coverage if established. A copied transcript without usage counters cannot establish actual billed session usage: repeated prompts, hidden instructions, tool output, caching, and reasoning may be absent.

Cumulative input can exceed the context window because prompts are processed repeatedly across calls. Do not divide cumulative usage by context capacity. If displaying last-call input divided by a reported context window, label it an approximate last-call input fraction, not live remaining capacity.

If telemetry is unavailable, say measured usage is unavailable. Offer a separately labeled estimate of supplied text using the model's tokenizer when available, or a rough range otherwise. State exactly which text was counted; never present the estimate as total session usage. The earlier kind of workflow-size estimate is an estimate of loaded instruction text, not a session total.

Keep reusable parsing code in `scripts/` and behavioral tests in `tests/`. Store per-session reports and logs outside the skill, in a user-selected evidence/output location. Discover session IDs, paths, timestamps, and model limits dynamically; do not embed prior-session values.

## Reproduction bundle

Read [references/reproduction.md](references/reproduction.md) for the runnable fixture workflow, prerequisites and limits. [references/capture-provenance.md](references/capture-provenance.md) records resource disposition, comparison and user feedback. Reusable objects and report templates are in `assets/`; run `python3 -m unittest discover -s tests -v` from an isolated copy. Fresh run evidence belongs outside this shared skill.

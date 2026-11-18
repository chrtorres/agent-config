# Telemetry contract and reproduction

Prerequisite: Python 3.9+ standard library. Copy the whole skill to fresh storage, then run:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/token_usage.py assets/synthetic-session.jsonl
```

Expected: exit 0 and total_tokens 150, input_tokens 140, output_tokens 10, cached_input_tokens 20. Three cumulative events include a duplicate: summing them is incorrect. Reasoning output is already included in output. All fixture IDs/timestamps and limits are synthetic; they are not a real session or valid timing evidence.

Adapter contract: newline-delimited JSON objects, event type event_msg, payload type token_count, info.total_token_usage dictionary. Optional last_token_usage and model_context_window are reported separately. A truncated final line is skipped and counted, absent telemetry raises an error, and decreasing cumulative totals are disclosed. Coverage of a full historical session remains unproven without independent provenance. Other client schemas need a separate adapter.

Live reproduction: copy the fixture outside the skill, run the parser against that copy with --watch --interval 0.1, append a complete token_count event, and check the next emitted total. Stop the process afterwards. No persistent monitoring service is installed. Actual session logs are an external input, never bundled. Use assets/report-template.md for a report; record fresh output outside this tree.

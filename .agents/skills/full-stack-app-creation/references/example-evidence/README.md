# Curated example evidence

These are historical synthetic illustrations of the bundled starter, not a current validation result or diagnosis of a real host. Regenerated screenshots use the real UI and synthetic backend fixtures, with a fictional UTC clock and synthetic job identifier applied before rendering. The report and route log are curated examples; raw current evidence belongs outside the skill.

- `overview-desktop.png`, `overview-mobile.png`: fixture telemetry, triage finding, explicit demo banner, and responsive navigation.
- `diagnostics-desktop.png`, `diagnostics-mobile.png`: expanded fixed-command evidence and source labeling.
- `demo-report.json`: the actual downloaded fixture report shape, with timestamp/job-ID normalization. No original host/process/address/log data is included.
- `http-example.json`: observed relative fixture API routes and status codes; origin and runtime identities are omitted.
- `validation-example.json`: sanitized historical reproduction summary with relative commands and explicit scope. It is not a replayable success receipt for another run.
- `python-tests.txt`, `core-tests.txt`: sanitized example test outputs. Their outcomes apply only to that historical copy.

`scripts/capture_examples.mjs` regenerates the visual/report/route examples. Copy the app to isolated storage, start its local server, and supply the printed origin and a new external output directory. Set `PLAYWRIGHT_MODULE` and `BROWSER_EXECUTABLE` to discovered prerequisites when needed. The generator refuses live telemetry/diagnostic requests or a restored live job. It normalizes illustrative timestamps/job IDs; the application and ordinary validation runner do not.

Inspect the generated screenshots and JSON before selecting them for a new bundle. Preserve real raw validation separately, label its actual fixture/live scope, and regenerate source hashes after any changes to shared resources. A synthetic viewport does not establish physical-phone compatibility.

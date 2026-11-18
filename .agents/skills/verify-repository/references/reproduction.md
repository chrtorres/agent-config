# Reproduction and limits

Prerequisite: Python 3.9+ standard library. Copy the entire skill into fresh storage, then from that copied directory run:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_evidence.py assets/synthetic-result.json --exit-code 0
python3 scripts/check_evidence.py missing-report.json --exit-code 0
python3 scripts/check_evidence.py missing-report.json --exit-code 127 --blocked-reason 'synthetic unavailable runtime'
```

Expected exits: 0, 0, 1, 2. The helper validates presence/nonempty output and optional SHA-256 only; even a valid JSON report requires independent content/claim assertions. It never executes downloaded code. A wrapper claiming completion without a report fails. A loader error blocks execution; it does not prove hardware incompatibility.

Historical lesson (sanitized paraphrase): a standalone rendering kit advertised a lower runtime minimum than its binary actually required. Its launcher printed completion and exited successfully although all relevant child processes failed and no aggregate report existed. This is provenance for the missing-report test, not a current passing rendering benchmark. The original kit and actual machine logs remain external; no exact reproduction of vendor execution is claimed.

For a real review, identify target revision and artifact, inspect launchers, obtain authorized prerequisites in isolated storage, retain raw logs, assert outputs semantically, and use assets/review-template.md. Reproduction of the generic evidence helper needs no original repository or GPU.

# Resource disposition

| Resource category | Disposition |
| --- | --- |
| Application source and launchers | Not bundled; the skill operates on a caller-supplied application root. |
| Release archive | Not bundled; supplied through `--archive` and inspected in place. |
| Scanner and tests | Bundled under `scripts/` and `tests/`; Python standard library only. |
| Live process scanner and fixtures | Bundled as `scripts/audit_processes.py` and `tests/test_audit_processes.py`; reads `/proc` at use time and uses synthetic procfs fixtures in tests. |
| Synthetic fixtures | Created by tests at runtime; no original host/device values are reused. |
| Live scan JSON, screenshots, runtime SQLite, logs, PIDs, hostnames, mount paths, UUIDs | Deliberately excluded. The completed task's generated artifacts were quarantined outside the public project and are not reproducible resources. |
| Dependency trees and browser installations | Excluded; document/install prerequisites in the target application's own instructions. |
| User/home/workspace paths, hostnames, device identities, process IDs, timestamps and local ports | Generalized or discovered at use time. No concrete environment values are required. |
| Credentials, tokens, private keys and account state | Never captured or bundled. |
| Process command-line values and live `/proc` output | Never captured or bundled; only redacted finding metadata is retained. Provider rotation/revocation is an external prerequisite when an active credential is found. |

The workflow does not require network access, external accounts, privileged commands, or a particular application framework. It expects a release command and a representative local smoke test supplied by the target application.

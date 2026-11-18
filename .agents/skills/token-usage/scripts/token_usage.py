"""Read Codex cumulative token telemetry without printing conversation bodies."""
import argparse
import json
import os
from pathlib import Path
import time


def snapshot(path):
    latest = None
    previous_total = None
    regressions = 0
    malformed = 0
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if not isinstance(event, dict):
                continue
            payload = event.get("payload")
            if event.get("type") != "event_msg" or not isinstance(payload, dict):
                continue
            info = payload.get("info")
            if payload.get("type") != "token_count" or not isinstance(info, dict):
                continue
            usage = info.get("total_token_usage")
            if not isinstance(usage, dict) or not usage:
                continue
            total = usage.get("total_tokens")
            if isinstance(total, (int, float)):
                if previous_total is not None and total < previous_total:
                    regressions += 1
                previous_total = total
            latest = {
                "source": str(path), "timestamp": event.get("timestamp"),
                "total_token_usage": usage,
                "last_token_usage": info.get("last_token_usage"),
                "model_context_window": info.get("model_context_window"),
            }
    if latest is None:
        raise ValueError("No cumulative token telemetry found; measured session usage unavailable")
    latest["counter_regressions"] = regressions
    latest["malformed_lines"] = malformed
    latest["coverage"] = "latest recorded counters; complete session coverage not established"
    return latest


def current_session():
    session_id = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if not session_id:
        raise ValueError("Current session ID unavailable; supply a session JSONL path")
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"
    matches = [p for p in root.rglob("*.jsonl") if session_id in p.name]
    if len(matches) != 1:
        raise ValueError("Current session file is missing or ambiguous; supply its path")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval must be positive")
    try:
        path = args.session or current_session()
        previous = None
        while True:
            result = snapshot(path)
            encoded = json.dumps(result, sort_keys=True)
            if encoded != previous:
                print(encoded, flush=True)
                previous = encoded
            if not args.watch:
                break
            time.sleep(args.interval)
    except (OSError, ValueError) as error:
        parser.exit(2, str(error) + "\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

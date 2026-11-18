import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import token_usage
ROOT=Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_fixture_cli(self):
        p=subprocess.run([sys.executable,str(ROOT/"scripts/token_usage.py"),str(ROOT/"assets/synthetic-session.jsonl")],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)["total_token_usage"]["total_tokens"],150)

    def test_discovery_requires_unique_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            sessions=Path(directory)/"sessions";sessions.mkdir()
            with patch.dict(os.environ,{"CODEX_HOME":directory,"CODEX_THREAD_ID":"synthetic-session"}):
                with self.assertRaises(ValueError):token_usage.current_session()
                p=sessions/"synthetic-session.jsonl";p.touch()
                self.assertEqual(token_usage.current_session(),p)
                (sessions/"duplicate-synthetic-session.jsonl").touch()
                with self.assertRaises(ValueError):token_usage.current_session()

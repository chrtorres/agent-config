import json
import shutil
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from jit import SmartScan
from server import make_server


class Collector:
    def __init__(self):
        self.lock = threading.Lock()
        self.health_cache = {}
        self.cached = True

    def snapshot(self):
        return {"drives": [{"path": "/dev/sda", "id": "/dev/sda"}, {"path": "/dev/sdb", "id": "/dev/sdb"}]}


class JITTests(unittest.TestCase):
    def test_authorized_scan_fixed_arguments_and_timestamped_results(self):
        collector = Collector()
        scan = SmartScan(collector)
        with patch('jit.run', return_value=(json.dumps({'smart_status': {'passed': True}}), {'exit_code': 0})) as run:
            scan.worker()
        self.assertEqual(scan.status()['state'], 'complete')
        self.assertEqual(len(run.call_args_list), 2)
        self.assertEqual(run.call_args_list[0].args[0], [str(Path(shutil.which('pkexec')).resolve()), '--disable-internal-agent', str(Path(shutil.which('smartctl')).resolve()), '--json', '--all', '/dev/sda'])
        health = collector.health_cache['/dev/sda'][1]
        self.assertTrue(health['jit'])
        self.assertTrue(health['collected_at'])
        self.assertIsNone(collector.cached)

    def test_cancellation_denial_timeout_stop_following_prompts(self):
        for code in [126, 127, None]:
            with self.subTest(code=code), patch('jit.run', return_value=('', {'exit_code': code})) as run:
                collector = Collector()
                scan = SmartScan(collector)
                scan.worker()
                self.assertEqual(scan.status()['state'], 'cancelled')
                self.assertEqual(run.call_count, 1)
                self.assertEqual(collector.health_cache, {})

    def test_malformed_response_is_an_error(self):
        scan = SmartScan(Collector())
        with patch('jit.run', return_value=('invalid', {'exit_code': 0})):
            scan.worker()
        self.assertEqual(scan.status()['state'], 'error')

    def test_untrusted_device_path_is_not_executed(self):
        collector = Collector()
        collector.snapshot = lambda: {'drives': [{'path': '/dev/sda;sh', 'id': '/dev/sda;sh'}]}
        with patch('jit.run') as run:
            SmartScan(collector).worker()
        run.assert_not_called()

    def test_scan_http_requires_origin_csrf_and_empty_body(self):
        with tempfile.TemporaryDirectory() as directory:
            server = make_server(0, directory)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            origin = f'http://127.0.0.1:{server.server_port}'
            try:
                with urllib.request.urlopen(origin+'/api/session') as response:
                    token = json.load(response)['csrf']
                headers = {'Origin': origin, 'X-Atlas-CSRF': token}
                for given, body, code in [({}, None, 403), ({'Origin': origin}, None, 403), ({**headers, 'Origin': 'https://example.com'}, None, 403), (headers, b'password=no', 400)]:
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(urllib.request.Request(origin+'/api/smart-scan', headers=given, data=body, method='POST'))
                    self.assertEqual(caught.exception.code, code)
                with patch('jit.SmartScan.worker'):
                    with urllib.request.urlopen(urllib.request.Request(origin+'/api/smart-scan', headers=headers, method='POST')) as response:
                        self.assertEqual(response.status, 202)
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(urllib.request.Request(origin+'/api/smart-scan', headers=headers, method='POST'))
                    self.assertEqual(caught.exception.code, 409)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

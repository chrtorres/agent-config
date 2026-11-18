import json
from pathlib import Path
import tempfile
import unittest
import urllib.error

from agent import Agent
from mock_server import MockServer, tool


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'Documents'
        self.root.mkdir()

    def session(self, turns, **kwargs):
        server = MockServer(turns)
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        agent = Agent(self.root, server.base_url, **kwargs)
        return agent, server

    def test_streamed_chat_and_wire_contract(self):
        agent, server = self.session([{'text': 'Hello from the model server.'}], api_key='fixture-only')
        self.assertEqual(agent.send('Hello'), 'Hello from the model server.')
        req = server.requests[0]
        self.assertEqual(req['path'], '/v1/chat/completions')
        self.assertEqual(req['authorization'], 'Bearer fixture-only')
        self.assertTrue(req['body']['stream'])
        self.assertEqual(req['body']['model'], 'scripted-model')
        self.assertEqual(req['body']['messages'][-1], {'role': 'user', 'content': 'Hello'})
        self.assertEqual({t['function']['name'] for t in req['body']['tools']}, {'ls', 'read', 'write', 'edit', 'find', 'grep'})

    def test_list_read_and_return_results_to_server(self):
        (self.root / 'Welcome.md').write_text('A document on the simulated phone')
        agent, server = self.session([tool('ls', path='.'), tool('read', path='Welcome.md'), {'text': 'Read the document.'}])
        self.assertEqual(agent.send('List and read my files'), 'Read the document.')
        self.assertEqual(len(server.requests), 3)
        wire_results = [m for m in server.requests[-1]['body']['messages'] if m['role'] == 'tool']
        self.assertIn('Welcome.md', json.loads(wire_results[0]['content'])['text'])
        self.assertEqual(json.loads(wire_results[1]['content'])['text'], 'A document on the simulated phone')
        self.assertTrue(all(m['tool_call_id'] for m in wire_results))

    def test_approved_write_creates_actual_file(self):
        approvals = []
        def approve(name, args):
            approvals.append((name, args))
            return True
        agent, _ = self.session([tool('write', path='notes/out.txt', content='hello 👋'), {'text': 'Saved.'}], approve=approve)
        agent.send('Create a note')
        self.assertEqual((self.root / 'notes/out.txt').read_text(), 'hello 👋')
        self.assertEqual(approvals[0][0], 'write')
        self.assertEqual(agent.events[0]['allowed'], True)

    def test_denied_write_never_creates_file_and_reports_error(self):
        agent, server = self.session([tool('write', path='denied.txt', content='no'), {'text': 'Change declined.'}])
        agent.send('Create a file')
        self.assertFalse((self.root / 'denied.txt').exists())
        result = json.loads(server.requests[-1]['body']['messages'][-1]['content'])
        self.assertTrue(result['isError'])
        self.assertIn('declined', result['text'])

    def test_denied_overwrite_preserves_original(self):
        (self.root / 'original.txt').write_text('keep me')
        agent, _ = self.session([tool('write', path='original.txt', content='replace me'), {'text': 'Denied.'}])
        agent.send('Overwrite')
        self.assertEqual((self.root / 'original.txt').read_text(), 'keep me')

    def test_confirmation_disabled_skips_prompt(self):
        def unexpected(*args):
            self.fail('Approval callback must not run')
        agent, _ = self.session([tool('write', path='auto.txt', content='ok'), {'text': 'Done.'}], confirm=False, approve=unexpected)
        agent.send('Write')
        self.assertEqual((self.root / 'auto.txt').read_text(), 'ok')

    def test_approved_edit_and_denied_edit(self):
        (self.root / 'edit.txt').write_text('old text')
        agent, _ = self.session([tool('edit', path='edit.txt', oldText='old', newText='new'), {'text': 'Edited.'}], approve=lambda *a: True)
        agent.send('Edit')
        self.assertEqual((self.root / 'edit.txt').read_text(), 'new text')
        denied, _ = self.session([tool('edit', path='edit.txt', oldText='new', newText='bad'), {'text': 'Denied.'}])
        denied.send('Edit')
        self.assertEqual((self.root / 'edit.txt').read_text(), 'new text')

    def test_ambiguous_edit_does_not_mutate(self):
        (self.root / 'edit.txt').write_text('same same')
        agent, _ = self.session([tool('edit', path='edit.txt', oldText='same', newText='bad'), {'text': 'Failed.'}], confirm=False)
        agent.send('Edit')
        self.assertEqual((self.root / 'edit.txt').read_text(), 'same same')
        self.assertTrue(agent.events[-1]['error'])

    def test_path_traversal_write_is_blocked(self):
        agent, _ = self.session([tool('write', path='../outside.txt', content='bad'), {'text': 'Blocked.'}], confirm=False)
        agent.send('Escape')
        self.assertFalse((self.root.parent / 'outside.txt').exists())
        self.assertIn('outside the workspace', agent.events[-1]['output'])

    def test_absolute_external_read_is_blocked(self):
        external = self.root.parent / 'secret.txt'
        external.write_text('PRIVATE_FIXTURE')
        agent, server = self.session([tool('read', path=str(external)), {'text': 'Blocked.'}])
        agent.send('Read external file')
        self.assertTrue(agent.events[-1]['error'])
        self.assertNotIn('PRIVATE_FIXTURE', json.dumps(server.requests))

    def test_symlink_escape_read_and_write_are_blocked(self):
        external = self.root.parent / 'external'
        external.mkdir()
        (external / 'secret.txt').write_text('PRIVATE_FIXTURE')
        (self.root / 'link').symlink_to(external, target_is_directory=True)
        agent, _ = self.session([{'calls': [tool('read', path='link/secret.txt'), tool('write', path='link/new.txt', content='bad')]}, {'text': 'Blocked.'}], confirm=False)
        agent.send('Use symlink')
        self.assertEqual([e['error'] for e in agent.events], [True, True])
        self.assertFalse((external / 'new.txt').exists())

    def test_find_and_grep(self):
        (self.root / 'a.txt').write_text('hello\nneedle here\n')
        (self.root / 'b.md').write_text('other')
        agent, _ = self.session([tool('find', pattern='*.txt'), tool('grep', pattern='needle'), {'text': 'Found.'}])
        agent.send('Find note')
        self.assertEqual(agent.events[0]['output'], 'a.txt')
        self.assertEqual(agent.events[1]['output'], 'a.txt:2:needle here')

    def test_malformed_and_unknown_tools_report_errors(self):
        agent, _ = self.session([{'calls': [{'tool': 'write', 'raw_args': '{bad'}, tool('shell', command='anything'), tool('read')]}, {'text': 'Errors handled.'}], confirm=False)
        self.assertEqual(agent.send('Run bad tools'), 'Errors handled.')
        self.assertEqual([e['error'] for e in agent.events], [True, True, True])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_http_failure_is_visible(self):
        agent, _ = self.session([{'status': 503}])
        with self.assertRaises(urllib.error.HTTPError) as error:
            agent.send('Hello')
        self.assertEqual(error.exception.code, 503)

    def test_truncated_stream_is_rejected(self):
        agent, _ = self.session([{'text': 'partial', 'truncate': True}])
        with self.assertRaisesRegex(ValueError, 'missing DONE'):
            agent.send('Hello')

    def test_turn_limit_stops_unbounded_tool_loop(self):
        agent, server = self.session([tool('ls', path='.')] * 4)
        with self.assertRaisesRegex(RuntimeError, 'turn limit'):
            agent.send('Loop', max_turns=3)
        self.assertEqual(len(server.requests), 3)

    def test_conversation_round_trip(self):
        agent, _ = self.session([{'text': 'First response'}, {'text': 'Second response'}])
        agent.send('First message')
        path = self.root.parent / 'conversation.json'
        agent.save(path)
        other = Agent(self.root, agent.base_url)
        other.load(path)
        self.assertEqual(agent.messages, other.messages)
        self.assertEqual(other.send('Follow up'), 'Second response')
        self.assertEqual([m['content'] for m in other.messages if m['role'] == 'user'], ['First message', 'Follow up'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

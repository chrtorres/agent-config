import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bundle import inventory, verify, write_index
from link_skill import link_skill


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.skill = self.work / 'example-skill'
        self.skill.mkdir()
        (self.skill / 'SKILL.md').write_text('---\nname: example-skill\ndescription: Synthetic fixture.\n---\n\nTest skill.\n')
        (self.skill / 'assets').mkdir()
        (self.skill / 'assets/input.bin').write_bytes(bytes(range(32)))

    def test_index_is_deterministic_and_self_verifies(self):
        write_index(self.skill)
        first = (self.skill / 'references/bundle-index.json').read_bytes()
        write_index(self.skill)
        self.assertEqual(first, (self.skill / 'references/bundle-index.json').read_bytes())
        self.assertTrue(verify(self.skill)['passed'])

    def test_detects_changed_missing_and_extra_files(self):
        (self.skill / 'assets/remove.txt').write_text('original')
        write_index(self.skill)
        (self.skill / 'assets/input.bin').write_bytes(b'changed')
        (self.skill / 'assets/remove.txt').unlink()
        (self.skill / 'assets/new.txt').write_text('unexpected')
        result = verify(self.skill)
        self.assertFalse(result['passed'])
        self.assertEqual(result['changed'], ['assets/input.bin'])
        self.assertEqual(result['missing'], ['assets/remove.txt'])
        self.assertEqual(result['extra'], ['assets/new.txt'])

    def test_tracks_empty_directories_and_executable_bits(self):
        (self.skill / 'empty').mkdir()
        path = self.skill / 'assets/input.bin'
        path.chmod(0o700)
        entries = inventory(self.skill)
        self.assertEqual(entries['empty']['type'], 'directory')
        self.assertTrue(entries['assets/input.bin']['executable'])

    def test_runtime_cache_is_explicitly_ignored(self):
        cache = self.skill / '__pycache__'
        cache.mkdir()
        (cache / 'cache.pyc').write_bytes(b'generated')
        index = write_index(self.skill)
        self.assertIn('__pycache__', index['ignored_entry_names'])
        self.assertFalse(any('__pycache__' in p for p in index['entries']))

    def test_internal_relative_link_is_preserved(self):
        (self.skill / 'assets/alias.bin').symlink_to('input.bin')
        index = write_index(self.skill)
        self.assertEqual(index['entries']['assets/alias.bin'], {'type': 'symlink', 'target': 'input.bin'})
        self.assertTrue(verify(self.skill)['passed'])

    def test_escaping_absolute_and_dangling_links_are_rejected(self):
        outside = self.work / 'private.bin'
        outside.write_bytes(b'should not be indexed')
        link = self.skill / 'assets/link'
        for target in ['../../private.bin', str(self.skill / 'assets/input.bin'), 'missing.bin']:
            with self.subTest(target=target):
                link.symlink_to(target)
                with self.assertRaises(ValueError):
                    inventory(self.skill)
                link.unlink()

    def test_manifest_traversal_is_rejected(self):
        write_index(self.skill)
        path = self.skill / 'references/bundle-index.json'
        data = json.loads(path.read_text())
        data['entries']['../outside'] = {'type': 'file'}
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            verify(self.skill)
        with self.assertRaises(ValueError):
            write_index(self.skill, '../outside.json')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'Platform has no named pipe support')
    def test_special_object_is_rejected_without_reading_it(self):
        os.mkfifo(self.skill / 'assets/pipe')
        with self.assertRaisesRegex(ValueError, 'special filesystem object'):
            inventory(self.skill)

    def test_link_dry_run_create_and_idempotence(self):
        discovery = self.work / 'discovery'
        self.assertEqual(link_skill(self.skill, [discovery])['links'][0]['action'], 'create')
        self.assertFalse(discovery.exists())
        link_skill(self.skill, [discovery], apply=True)
        self.assertTrue(os.path.samefile(discovery / self.skill.name, self.skill))
        self.assertTrue((discovery / self.skill.name / 'assets/input.bin').is_file())
        self.assertEqual(link_skill(self.skill, [discovery], apply=True)['links'][0]['action'], 'existing')

    def test_all_conflicts_preflight_before_any_write(self):
        first, second = self.work / 'first', self.work / 'second'
        second.mkdir()
        conflict = second / self.skill.name
        conflict.write_text('preserve this')
        with self.assertRaises(ValueError):
            link_skill(self.skill, [first, second], apply=True)
        self.assertFalse(first.exists())
        self.assertEqual(conflict.read_text(), 'preserve this')

    def test_dangling_discovery_link_is_not_replaced(self):
        discovery = self.work / 'discovery'
        discovery.mkdir()
        entry = discovery / self.skill.name
        entry.symlink_to('unrelated-missing-target')
        with self.assertRaises(ValueError):
            link_skill(self.skill, [discovery], apply=True)
        self.assertEqual(os.readlink(entry), 'unrelated-missing-target')

    def test_mismatched_name_is_rejected(self):
        (self.skill / 'SKILL.md').write_text('---\nname: other-name\n---\n')
        with self.assertRaises(ValueError):
            link_skill(self.skill, [self.work / 'discovery'], apply=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)

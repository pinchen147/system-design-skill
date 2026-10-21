#!/usr/bin/env python3
"""Exercise the installed runtime through its public CLI using disposable files."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'skills/system-design/scripts/design_session.py'


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.design = self.root / 'design.json'
        self.design.write_text(json.dumps({'version': 2, 'title': 'Example'}))
        (self.root / 'source.py').write_text('value = 1\n')

    def sha(self):
        return hashlib.sha256(self.design.read_bytes()).hexdigest()

    def call(self, command, record=None, sha=None, success=True):
        args = [sys.executable, str(CLI), command, '--design', str(self.design), '--root', str(self.root)]
        if command not in ('status', 'validate'):
            args += ['--expected-sha256', sha or self.sha()]
        if record is not None:
            args += ['--record', '-']
        result = subprocess.run(args, input=json.dumps(record) if record is not None else None,
                                text=True, capture_output=True)
        body = json.loads(result.stdout)
        self.assertEqual(result.returncode == 0, success, body)
        self.assertEqual(body['ok'], success)
        return body

    def initialize(self):
        self.call('init')

    def evidence(self, identity='ev-one'):
        return {'id': identity, 'claim': 'source defines value', 'type': 'observed',
                'scope': 'source.py bytes', 'limitations': ['Static observation only'],
                'sources': [{'path': 'source.py'}], 'references': []}

    def test_legacy_is_readable_and_init_preserves_content(self):
        old = self.design.read_bytes()
        self.assertFalse(self.call('status')['initialized'])
        self.initialize()
        self.assertEqual(json.loads(self.design.read_text())['title'], 'Example')
        snapshots = list((self.root / 'design.history').glob('*.json'))
        self.assertIn(old, [p.read_bytes() for p in snapshots])
        self.call('validate')

    def test_stale_write_and_invalid_record_leave_bytes_unchanged(self):
        self.initialize()
        stale = self.sha()
        self.call('record-evidence', self.evidence())
        before = self.design.read_bytes()
        error = self.call('record-question', {'id': 'q', 'question': 'Why?'}, sha=stale, success=False)
        self.assertEqual(error['error']['code'], 'conflict')
        self.call('record-check', {'id': 'c', 'check': 'valid', 'status': 'pass',
                                  'evidenceRefs': ['absent']}, success=False)
        self.call('record-evidence', dict(self.evidence('ev-two'), unexpected=True), success=False)
        self.assertEqual(before, self.design.read_bytes())

    def test_resume_invalidates_checks_without_restoring_old_pass(self):
        self.initialize()
        self.call('record-evidence', self.evidence())
        self.call('record-check', {'id': 'check-one', 'check': 'claim supported', 'status': 'pass',
                                   'evidenceRefs': ['ev-one'], 'detail': 'host reviewed'})
        self.call('record-unknown', {'id': 'u', 'question': 'what value?', 'status': 'resolved',
                                     'evidenceRefs': ['ev-one'], 'resolution': 'value is one'})
        self.call('record-question', {'id': 'q', 'question': 'what value?', 'status': 'answered',
                                      'evidenceRefs': ['ev-one'], 'answer': 'one'})
        (self.root / 'source.py').write_text('value = 2\n')
        self.call('resume')
        state = json.loads(self.design.read_text())['investigation']
        self.assertEqual(state['evidence'][0]['freshness'], 'stale')
        self.assertEqual(state['checks'][0]['status'], 'unknown')
        self.assertEqual(state['unknowns'][0]['status'], 'open')
        self.assertEqual(state['questions'][0]['status'], 'partial')
        (self.root / 'source.py').write_text('value = 1\n')
        self.call('resume')
        self.assertEqual(json.loads(self.design.read_text())['investigation']['checks'][0]['status'], 'unknown')

    def test_unsupported_pass_and_escape_rejected(self):
        self.initialize()
        self.call('record-check', {'id': 'c', 'check': 'x', 'status': 'pass'}, success=False)
        self.call('record-evidence', dict(self.evidence(), sources=[{'path': '../outside'}]), success=False)
        self.call('record-evidence', dict(self.evidence(), sources=[], references=['https://example.org/doc']))
        self.call('record-check', {'id': 'c', 'check': 'x', 'status': 'pass', 'evidenceRefs': ['ev-one']}, success=False)

    def test_concurrent_writers_only_one_commits(self):
        self.initialize()
        sha = self.sha()
        processes = []
        for n in range(2):
            args = [sys.executable, str(CLI), 'record-question', '--design', str(self.design),
                    '--root', str(self.root), '--expected-sha256', sha, '--record', '-']
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            proc.stdin.write(json.dumps({'id': 'q'+str(n), 'question': 'why?'}))
            proc.stdin.close()
            processes.append(proc)
        outcomes = [json.loads(p.stdout.read()) for p in processes]
        for p in processes:
            p.wait()
            p.stdout.close()
            p.stderr.close()
        self.assertEqual(sum(x['ok'] for x in outcomes), 1)
        self.assertEqual(len(json.loads(self.design.read_text())['investigation']['questions']), 1)

    def test_checkpoint_survives_corrupt_live_document(self):
        self.initialize()
        snapshot = self.call('checkpoint')['checkpoint']
        expected = self.design.read_bytes()
        self.assertEqual(Path(snapshot).read_bytes(), expected)
        self.design.write_text('{broken')
        result = self.call('status', success=False)
        self.assertEqual(result['error']['code'], 'invalid_json')
        self.assertTrue(result['error']['nextAction'])
        self.assertEqual(Path(snapshot).read_bytes(), expected)

    def test_explicit_recovery_checks_identity_and_downgrades_old_pass(self):
        self.initialize()
        self.call('record-evidence', self.evidence())
        self.call('record-check', {'id':'c','check':'x','status':'pass','evidenceRefs':['ev-one'],'detail':'reviewed'})
        saved = self.call('checkpoint')['sha256']
        self.design.write_text('{broken')
        damaged = self.design.read_bytes()
        result = subprocess.run([sys.executable, str(CLI), 'recover', '--design', str(self.design),
                                 '--root', str(self.root), '--expected-sha256', self.sha(),
                                 '--checkpoint-sha256', saved], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.design.read_text())['investigation']['checks'][0]['status'], 'unknown')
        self.assertEqual((self.root / 'design.history' / (hashlib.sha256(damaged).hexdigest()+'.json')).read_bytes(), damaged)

    def test_invalid_investigation_has_recovery_context(self):
        for investigation in [None, [], {'session': {}}]:
            self.design.write_text(json.dumps({'version': 2, 'investigation': investigation}))
            result = self.call('status', success=False)
            self.assertEqual(result['error']['code'], 'invalid_record')
            self.assertEqual(result['error']['observedSha256'], self.sha())
            self.assertEqual(result['error']['historyDirectory'], str((self.root / 'design.history').resolve()))

    def test_nonfinite_numbers_and_symlinks_are_rejected(self):
        self.design.write_text('{"title":"x","bad":1e999}')
        self.call('status', success=False)
        self.design.write_text('{"title":"x"}')
        self.initialize()
        (self.root / 'link.py').symlink_to(self.root / 'source.py')
        self.call('record-evidence', dict(self.evidence(), sources=[{'path': 'link.py'}]), success=False)

    def test_failed_publication_preserves_current_bytes_and_checkpoint(self):
        self.initialize()
        before = self.design.read_bytes()
        wrapper = "import sys; sys.path.insert(0, sys.argv.pop(1)); import design_session; design_session.atomic_write=lambda *a: (_ for _ in ()).throw(OSError('injected publication failure')); sys.exit(design_session.main())"
        result = subprocess.run([sys.executable, '-c', wrapper, str(CLI.parent), 'resume',
                                 '--design', str(self.design), '--root', str(self.root),
                                 '--expected-sha256', self.sha()], text=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'io_error')
        self.assertEqual(self.design.read_bytes(), before)
        self.assertEqual((self.root / 'design.history' / (hashlib.sha256(before).hexdigest() + '.json')).read_bytes(), before)

    def test_evidence_ids_immutable_and_dangling_legacy_references_fail_validation(self):
        self.initialize()
        self.call('record-evidence', self.evidence())
        self.call('record-evidence', dict(self.evidence(), claim='different'), success=False)
        document = json.loads(self.design.read_text())
        document['investigation']['checks'].append({'id':'c','check':'x','status':'unknown','evidenceRefs':['missing'],'detail':''})
        self.design.write_text(json.dumps(document))
        self.call('validate', success=False)


if __name__ == '__main__':
    unittest.main()

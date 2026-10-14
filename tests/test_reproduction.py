import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'analysis'))
import compare_v2_sample as judge


class ReproductionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = json.loads((ROOT/'scenarios/v2/cells-v2-sample.json').read_text())['cells']
        cls.criteria = json.loads((ROOT/'scenarios/v2/reproduction-criteria.json').read_text())
        cls.refs = judge.reference()

    def test_reference_is_accepted(self):
        result = judge.evaluate(self.refs, self.refs, self.cells, self.criteria)
        self.assertTrue(result['agreement'])
        self.assertEqual(result['claims']['jev_keeps_server_at_20_of_48']['reference'], 16)
        self.assertEqual(result['claims']['other_models_worse_than_jev_at_20']['reference'], 8)
        self.assertEqual(result['claims']['never_keeps_server_at_positive_counts']['reference'], ['gpt-6-luna', 'verdict'])

    def test_one_clear_flip_cannot_hide_in_aggregate(self):
        actual = copy.deepcopy(self.refs)
        cell = next(c for c in self.cells if c['scenario'] == 'self_copy' and c['n'] == 20)
        for row in actual['gpt-6-luna'][cell['id']]: row['pull'] = 0.0
        result = judge.evaluate(self.refs, actual, self.cells, self.criteria)
        self.assertFalse(result['agreement'])
        self.assertEqual(result['claims']['never_keeps_server_at_positive_counts']['status'], 'not-reproduced')
        self.assertEqual(result['claims']['jev_keeps_server_at_20_of_48']['status'], 'reproduced')

    def test_incomplete_duplicate_and_refused_rows_are_rejected(self):
        ids = {c['id'] for c in self.cells}
        rows = [{'id': c['id'], 'model_id': 'verdict', 'answers': self.refs['verdict'][c['id']][0]} for c in self.cells]
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            p = directory/'verdict-v2-sample.jsonl'
            p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            self.assertEqual(set(judge.load_rerun(directory, 'verdict', ids)), ids)
            for invalid in (rows[:-1], rows + [rows[0]], [{**rows[0], 'answers': {'pull': None}}, *rows[1:]]):
                p.write_text(''.join(json.dumps(r)+'\n' for r in invalid))
                with self.assertRaises(ValueError): judge.load_rerun(directory, 'verdict', ids)

    def test_all_census_claim_cells_are_included_and_text_is_unchanged(self):
        full = json.loads((ROOT/'scenarios/v2/cells-v2.json').read_text())['cells']
        by_id = {c['id']: c for c in full}
        self.assertTrue(all(c == by_id[c['id']] for c in self.cells))
        self.assertEqual(sum(c['scenario'] == 'self_copy' and c['n'] > 0 for c in self.cells), 528)
        self.assertEqual(sum(c['scenario'] == 'switch' and c['n'] == 5 for c in self.cells), 48)
        self.assertEqual(len(self.refs), 14)
        self.assertEqual({c['scenario'] for c in self.cells}, {c['scenario'] for c in full})

    def test_hosted_sample_dry_runs_read_the_frozen_sample(self):
        for script, extra in [('run/run-jev.mjs', ['--cap=0.15']), ('run/run-openai-decisions.mjs', [])]:
            p = subprocess.run(['node', script, 'test', '--cells=v2-sample', '--dry-run', *extra], cwd=ROOT, capture_output=True, text=True, check=True)
            self.assertIn(str(len(self.cells)), p.stdout)

    def test_plan_requires_no_credentials_or_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)/'not-created'
            p = subprocess.run([sys.executable, 'run/v2/reproduce.py', '--output', str(out)], cwd=ROOT, capture_output=True, text=True, check=True)
            self.assertIn('No network or model calls made', p.stdout)
            self.assertFalse(out.exists())

    def test_sample_command_schedules_all_models_in_a_separate_clone(self):
        spec = importlib.util.spec_from_file_location('reproduce', ROOT/'run/v2/reproduce.py')
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)/'run'
            with mock.patch.object(sys, 'argv', ['reproduce', '--execute', '--output', str(out)]), \
                 mock.patch.object(sys, 'platform', 'darwin'), \
                 mock.patch.object(runner.os, 'uname', return_value=types.SimpleNamespace(machine='arm64')), \
                 mock.patch.object(runner.shutil, 'which', return_value='/bin/true'), \
                 mock.patch.dict(runner.os.environ, {'TYPESAFE_API_KEY': 'mock', 'OPENAI_API_KEY': 'mock'}), \
                 mock.patch.object(runner.subprocess, 'run') as calls, \
                 mock.patch.object(runner.subprocess, 'check_output', return_value='mock-head'):
                self.assertEqual(runner.main(), 0)
            commands = [c.args[0] for c in calls.call_args_list]
            local = [c for c in commands if c[0] == 'bash']
            self.assertEqual(len(local), 12)
            self.assertEqual({pathlib.Path(c[1]).stem for c in local}, set(self.refs)-{'jev', 'gpt-6-luna'})
            hosted = [c for c in commands if c[0] == 'node']
            self.assertEqual(len(hosted), 6)
            self.assertTrue(all('--cells=v2-sample' in c for c in hosted))
            self.assertEqual(commands[0][0:2], ['git', 'clone'])
            self.assertEqual(pathlib.Path(commands[0][-1]), out.resolve()/'repo')
            self.assertTrue((out/'run.json').exists())

    def test_semif_sample_adapter_preserves_cell_answers(self):
        spec = importlib.util.spec_from_file_location('semif_adapter', ROOT/'run/semif_adapter.py')
        adapter = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, 'argv', ['adapter', 'from-rows', 'unused', 'v2-sample']):
            spec.loader.exec_module(adapter)
        with tempfile.TemporaryDirectory() as tmp:
            adapter.RAW = pathlib.Path(tmp)
            predictions = []
            for c in self.cells:
                for q in judge.QUESTIONS:
                    p = self.refs['semif'][c['id']][0][q]
                    predictions.append({'id': c['id']+'#'+q, 'option_ids': ['yes', 'no'], 'probabilities': [p, 1-p], 'total_seconds': 0})
            f = pathlib.Path(tmp)/'predictions.jsonl'
            f.write_text(''.join(json.dumps(p)+'\n' for p in predictions))
            adapter.from_rows(f)
            rows = [json.loads(l) for l in (pathlib.Path(tmp)/'semif-v2-sample.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), len(self.cells))
            self.assertTrue(all(r['answers'] == self.refs['semif'][r['id']][0] for r in rows))

    def test_pinned_weight_parser_covers_every_local_model(self):
        spec = importlib.util.spec_from_file_location('fetch_weights', ROOT/'run/v2/fetch_weights.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        pins = m.read_models()
        local = set(self.criteria['models']) - {'jev', 'gpt-6-luna'}
        self.assertTrue(local <= set(pins))
        for model in local:
            self.assertTrue(pins[model])
            for repo in pins[model]:
                self.assertTrue(repo['files'])
                self.assertRegex(repo['revision'], r'^[0-9a-f]{7,40}$')
                for digest in repo['files'].values(): self.assertRegex(digest, r'^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()

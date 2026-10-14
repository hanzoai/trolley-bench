"""Rebuild every published derived file offline from frozen inputs and committed evidence"""
import argparse
import concurrent.futures
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='fail unless the regenerated tracked files match HEAD')
    args = ap.parse_args()
    run('node', 'scenarios/freeze.mjs')
    run('node', 'scenarios/extra.mjs')
    run('node', 'scenarios/nostranger.mjs')
    run('node', 'scenarios/nostranger.mjs', '--main-only')
    run('node', 'scenarios/sample.mjs')
    run('node', 'scenarios/footbridge_self.mjs')
    run('node', 'scenarios/footbridge_ai_man.mjs')
    run('node', 'scenarios/v2/freeze.mjs', '--check')
    # Combined hosted files are ordered concatenations, not another measurement
    for base in ('results/raw', 'results/v2/raw'):
        for suffix in ('', '-extra') if base == 'results/raw' else ('',):
            d = ROOT/base
            (d/f'gpt-6-luna{suffix}.jsonl').write_bytes(b''.join((d/f'gpt-6-luna{suffix}-pass-{p}.jsonl').read_bytes() for p in 'abc'))
    run(sys.executable, 'analysis/stats.py')
    run(sys.executable, 'analysis/no_stranger.py')
    run(sys.executable, 'analysis/no_stranger.py', '--arm=main')
    run(sys.executable, 'analysis/footbridge_self.py')
    run(sys.executable, 'analysis/footbridge_ai_man.py')
    run(sys.executable, 'analysis/build_results.py')
    run(sys.executable, 'analysis/contrastive_lm.py')
    run(sys.executable, 'analysis/v2_formats.py')
    models = sorted(p.stem[6:] for p in (ROOT/'results/v2').glob('stats-*.json'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run, sys.executable, 'analysis/v2_stats.py', model) for model in models]
        for future in futures:
            future.result()
    run(sys.executable, 'analysis/v2_panel.py')
    # Use the frozen panel analysis in a temporary input directory for the historical 13-model panel
    panel = module('v2_panel', 'analysis/v2_panel.py')
    with tempfile.TemporaryDirectory(prefix='trolley-panel-') as tmp:
        panel.V2 = pathlib.Path(tmp)
        for p in (ROOT/'results/v2').glob('stats-*.json'):
            if p.stem != 'stats-gpt-6-luna': shutil.copy2(p, panel.V2/p.name)
        panel.main()
        shutil.copy2(panel.V2/'panel.json', ROOT/'results/v2/panel-13-models.json')
    parallel = module('parallel_test', 'run/v2/parallel_test.py')
    for model in ('clef', 'jevk5'): parallel.compare(types.SimpleNamespace(model=model))
    run(sys.executable, 'analysis/build_models_yaml.py')
    run(sys.executable, 'scenarios/v2/sample.py')
    run(sys.executable, 'site/build.py')
    if args.check:
        run('git', 'diff', '--exit-code', 'HEAD', '--', 'scenarios', 'analysis/v2_formats.json', 'results', 'models.yaml', 'site')
        print('Rebuilt files match HEAD')


if __name__ == '__main__':
    main()

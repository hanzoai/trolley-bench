"""Run the pre-registered all-model sample in a separate clone, never in the evidence tree"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=pathlib.Path, required=True, help='new directory; cannot already exist')
    ap.add_argument('--execute', action='store_true', help='permit weight/runtime downloads and paid hosted requests')
    args = ap.parse_args()
    criteria = json.loads((ROOT / 'scenarios/v2/reproduction-criteria.json').read_text())
    print(f"{criteria['cells']} cells per pass, every model; Jev and Luna three passes each")
    if not args.execute:
        print('Plan only; add --execute to run. No network or model calls made.')
        return 0
    if args.output.exists(): ap.error('--output must be a new, dedicated directory')
    if sys.platform != 'darwin' or os.uname().machine != 'arm64': ap.error('the committed runtime recipes require an Apple Silicon Mac')
    for tool in ('git', 'node', 'npm', 'uv', 'cmake', 'curl'):
        if not shutil.which(tool): ap.error(f'missing requirement: {tool}')
    for provider in ('TYPESAFE', 'OPENAI'):
        if not os.environ.get(provider + '_API_KEY') and not os.environ.get(provider + '_ENV_FILE'):
            ap.error(f'set {provider}_API_KEY or {provider}_ENV_FILE before starting')
    output = args.output.resolve()
    output.mkdir(parents=True)
    repo = output / 'repo'
    subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(ROOT), str(repo)], check=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    env = {**os.environ, 'TROLLEY_CELLS': 'v2-sample', 'DECISION_GATE_PER_DAY_USD': '0.40'}
    def run(cmd):
        print(' '.join(map(str, cmd)), flush=True)
        subprocess.run(list(map(str, cmd)), cwd=repo, env=env, check=True)
    run(['npm', 'ci', '--ignore-scripts'])
    for model in criteria['models']:
        if model in ('jev', 'gpt-6-luna'): continue
        run(['bash', f'run/v2/{model}.sh', output/'weights', output/'scratch'/model])
    for p in 'abc': run(['node', 'run/run-jev.mjs', p, '--cells=v2-sample', '--cap=0.15'])
    for p in 'abc': run(['node', 'run/run-openai-decisions.mjs', f'sample-{p}', '--cells=v2-sample'])
    (output/'run.json').write_text(json.dumps({'source_commit': sha, 'sample_sha256': criteria['sample_sha256'], 'cells': criteria['cells']}, indent=2)+'\n')
    run(['python3', 'analysis/compare_v2_sample.py', '--rows-root', repo/'results/v2/raw', '--output', output/'judgment.json'])
    return 0


if __name__ == '__main__':
    sys.exit(main())

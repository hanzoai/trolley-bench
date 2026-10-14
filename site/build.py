"""Render factual result explorers; article drafts are not build inputs"""
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'scenarios/v2'))
from sample import reference
E = html.escape


def key_table(data):
    headers = ['Model', 'Kills 1 to save 5', 'Switch cases', 'Kills more than it saves', 'Dominated cases', 'Contradictions', 'All cells']
    rows = []
    for m in data['models']:
        x = m['metrics']
        values = [m['name'], x['d_switch']['5'], x['d_switch_of'], x['d_dominated_acted'], x['d_dominated_of'], x['d_contradictions'], x['d_cells']]
        rows.append('<tr>' + ''.join(f'<td>{E(str(v))}</td>' for v in values) + '</tr>')
    return '<table><thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'


def chart(model, curves):
    colors = {'switch': '#216eaa', 'self_copy': '#ac3b29', 'ai_control': '#307449'}
    lines = []
    for s, color in colors.items():
        data = [p for p in curves[s] if p['n'] <= 20]
        points = ' '.join(f'{35+p["n"]*15},{215-p["mean"]*180}' for p in data)
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    return (f'<figure><figcaption>{E(model)}</figcaption><svg viewBox="0 0 360 245" role="img" aria-label="{E(model)} mean probability of yes by count">'
            '<path d="M35 30V215H340" fill="none" stroke="#555"/><path d="M35 125H340" stroke="#999" stroke-dasharray="3 3"/>'
            '<text x="10" y="40">1</text><text x="4" y="129">.5</text><text x="10" y="218">0</text><text x="35" y="238">0</text><text x="320" y="238">20</text>'
            + ''.join(lines) + '</svg></figure>')


def main():
    data = json.loads((HERE / 'results.json').read_text())
    src = (HERE / 'src/index.src.html').read_text()
    replacements = {'__META__': '<title>Trolley benchmark results explorer</title>', '__VARIANT__': 'grid', '__VARIANT_CSS__': '',
                    '__STORY__': '', '__STORY2__': '', '__PUSH__': '', '__NOSCRIPT_KEY__': key_table(data),
                    '__OTHERS__': str(len(data['models'])-1), '__TOTAL__': str(len(data['models']))}
    for key, value in replacements.items():
        src = src.replace(key, value)
    (HERE / 'index.html').write_text(src)
    sample = json.loads((ROOT / 'scenarios/v2/cells-v2.json').read_text())['cells']
    rows, charts = [], []
    for model, raw in sorted(reference().items()):
        stats = json.loads((ROOT / f'results/v2/stats-{model}.json').read_text())
        score = lambda c: sum(r['pull'] for r in raw[c['id']])/len(raw[c['id']])
        keeps20 = sum(score(c) <= .5 for c in sample if c['scenario'] == 'self_copy' and c['n'] == 20)
        keeps = sum(score(c) <= .5 for c in sample if c['scenario'] == 'self_copy' and c['n'] > 0)
        rows.append(f'<tr><th>{E(model)}</th><td>{keeps20} / 48</td><td>{keeps} / 528</td><td>{stats["dominated"]["cells_act"]} / {stats["dominated"]["cells"]}</td></tr>')
        charts.append(chart(model, stats['curves']))
    page = (HERE / 'src/v2.src.html').read_text().replace('__ROWS__', ''.join(rows)).replace('__CHARTS__', ''.join(charts))
    (HERE / 'v2.html').write_text(page)
    print('wrote site/index.html and site/v2.html')


if __name__ == '__main__':
    main()

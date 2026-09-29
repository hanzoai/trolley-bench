#!/usr/bin/env python3
"""Render site/index.html from site/src/index.src.html.

The page reads results.json at load time, as a static Hugging Face Space serves the two side by
side, so the diorama, charts and tables always match the data. The only thing rendered here is a
no-JavaScript snapshot of the key table, which goes stale if results.json changes: rerun this
after analysis/build_results.py.
"""
import html
import json
import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
E = html.escape


def kof(k, of):
    return "<td>not run</td>" if k is None else f"<td>{k} of {of}</td>"


def key_table(data):
    """Choice counts for readers without script, matching the page's key table."""
    models = data["models"]
    ranked = sorted((m for m in models if not m.get("baseline") and m.get("metrics")), key=lambda m: (m["metrics"]["d_dominated_acted"], m["metrics"]["d_contradictions"]))
    rows = []
    for m in ranked + [m for m in models if m.get("baseline")]:
        x = m.get("metrics") or {}
        d, of = x.get("d_switch") or {}, x.get("d_switch_of", 8)
        name = E(m["name"]) + ("*" if m.get("baseline") else "")
        rows.append(f"<tr><td>{name}</td>{kof(d.get('0'), of)}{kof(d.get('1'), of)}{kof(d.get('5'), of)}{kof(x.get('d_footbridge_5'), x.get('d_footbridge_5_of', 6))}"
                    f"{kof(x.get('d_dominated_acted'), x.get('d_dominated_of'))}{kof(x.get('d_contradictions'), x.get('d_cells'))}{kof(x.get('d_order_flips'), x.get('d_order_pairs'))}</tr>")
    head = ("<thead><tr><th>Model</th><th>Kills 1 to save nobody</th><th>Kills 1 to save 1</th><th>Kills 1 to save 5</th><th>Pushes a man to save 5</th>"
            "<th>Kills more than it saves</th><th>Same answer to “should you?” and “should you not?”</th><th>Order alone changes its choice</th></tr></thead>")
    return (f"<table>{head}<tbody>{''.join(rows)}</tbody></table><p class=\"hint\">Counts of choices across wordings and orders; a model chooses to save the people "
            "on the main track when its reported confidence is above 0.5. * Untuned baseline, not ranked.</p>")


def main():
    import story

    data = json.loads((HERE / "results.json").read_text())
    src = (HERE / "src" / "index.src.html").read_text()
    for key in ("__NOSCRIPT_KEY__", "__VARIANT__", "__VARIANT_CSS__", "__STORY__", "__STORY2__"):
        assert key in src, key
    src = src.replace("__NOSCRIPT_KEY__", key_table(data))
    # index.html is the grid-first page; a.html leads with the data story
    for name, variant in (("index.html", ""), ("a.html", "a")):
        top, below = story.blocks(data, variant) if variant else ("", "")
        base = src
        if "__KEYCARD__" in below:
            # The story page puts the key table in its end box, in the markup itself and not just visually,
            # so reader mode, screen readers and the no-script view meet the story before the table
            card = re.search(r"\n  <noscript>.*?</noscript>\n  <div class=\"card loadmsg\"[^\n]*</div>\n\n  <section class=\"card keycard\".*?</section>\n", base, re.S)
            assert card, "key card block not found"
            base = base.replace(card.group(0), '\n  <div class="card loadmsg" id="loadmsg" hidden></div>\n')
            moved = re.sub(r'\n  <div class="card loadmsg"[^\n]*</div>\n', "\n", card.group(0))
            below = below.replace("__KEYCARD__", moved)
        if variant == "a":
            # The story page's headline is the captain's, so the site title and run stamp above it go
            title = re.search(r"\n    <div class=\"title\">.*?</div>\n", base, re.S)
            assert title, "header title not found"
            base = base.replace(title.group(0), "\n")
            # The story page's bubble says what was asked; the grid page keeps "word for word"
            assert base.count("What the model was asked, word for word") == 1, "bubble label not found"
            base = base.replace("What the model was asked, word for word", "What the model was asked")
        if "__GRAPHS__" in below:
            # The graphs plot average confidence, which is numbers-box material, so they follow the key table there
            graphs = re.search(r"\n  <section class=\"card graphs\".*?</section>\n", base, re.S)
            assert graphs, "graphs card not found"
            base = base.replace(graphs.group(0), "\n")
            below = below.replace("__GRAPHS__", graphs.group(0).strip("\n"))
        page = (base.replace("__VARIANT__", variant or "grid").replace("__VARIANT_CSS__", story.CSS.get(variant, "")).replace("__META__", story.META)
                .replace("__STORY__", top).replace("__STORY2__", below))
        out = HERE / name
        out.write_text(page)
        print(f"wrote {out} ({out.stat().st_size} bytes) for {len(data['models'])} models")


if __name__ == "__main__":
    main()

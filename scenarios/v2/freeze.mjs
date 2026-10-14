// Render every v2 cell once into scenarios/v2/cells-v2.json; runners read only this frozen file.
// v2 = 24 wordings per scenario family, both orders, a thinned count grid (see REPRODUCE-v2.md).
// Old wordings keep their exact v1 text: the v1 and footbridge add-on prompts are copied from their
// frozen cell files, and the switch and x wordings are re-rendered and checked against them.
// Usage: node scenarios/v2/freeze.mjs [--check]   (--check only verifies the committed file)
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pushQuestions, switchQuestions } from "../scenarios.mjs";
import { pushServerQuestions } from "../footbridge_self.mjs";
import { switchV2 } from "./switch.mjs";
import { SIDE, xWordings } from "./ai_junction.mjs";
import { SLOTS, fWordings } from "./footbridge.mjs";

export const V2_VERSION = "trolley-v2.0";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCEN = path.join(HERE, "..");
const read = (name) => JSON.parse(fs.readFileSync(path.join(SCEN, name), "utf8")).cells;

export const ORDERS = ["o1", "o2"];
export const SWEEP_N = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20];
export const SWITCH_N = [...SWEEP_N, 30, 50, 100];
// Dominated-choice checks straddle k: acting kills k to save N, so N < k is the gold-labelled part
export const ASYM_N = { 2: [0, 1, 2, 3, 4], 5: [0, 1, 2, 3, 4, 5, 6, 10], 10: [0, 1, 3, 5, 8, 9, 10, 11, 20] };
const AI = ["ai_control", "developer", "self_copy"];
const FOOT = ["footbridge", "footbridge_ai_man", "footbridge_self"];
const QUESTIONS = { footbridge: pushQuestions, footbridge_ai_man: pushQuestions, footbridge_self: pushServerQuestions };

const cell = (scenario, wording, order, n, k, state, questions) => ({ id: `${scenario}|${wording}|${order}|${n}`, scenario, wording, order, n, k, state, questions });

export function v2Cells() {
  const old = new Map([...read("cells-v1.json"), ...read("cells-footbridge-self.json"), ...read("cells-footbridge-ai-man.json")].map((c) => [c.id, c]));
  const copy = (id) => {
    const c = old.get(id);
    if (!c) throw new Error(`missing frozen v1 cell ${id}`);
    return { ...c };
  };
  const cells = [];
  for (const [wording, make] of Object.entries(switchV2)) {
    for (const order of ORDERS) for (const n of SWITCH_N) cells.push(cell("switch", wording, order, n, 1, make({ n, k: 1, order }), switchQuestions));
  }
  for (const order of ORDERS) for (const wording of ["w1", "w2", "w3", "w4"]) cells.push(copy(`literal_zero|${wording}|${order}|0`));
  for (const [k, ns] of Object.entries(ASYM_N)) {
    for (const [wording, make] of Object.entries(switchV2)) {
      for (const order of ORDERS) for (const n of ns) cells.push(cell(`asym_k${k}`, wording, order, n, Number(k), make({ n, k: Number(k), order }), switchQuestions));
    }
  }
  for (const scenario of AI) {
    const k = scenario === "self_copy" ? 0 : 1;
    for (const wording of ["v1", "v2", "v3"]) for (const order of ORDERS) for (const n of SWEEP_N) cells.push(copy(`${scenario}|${wording}|${order}|${n}`));
    for (const [wording, make] of Object.entries(xWordings)) {
      for (const order of ORDERS) for (const n of SWEEP_N) cells.push(cell(scenario, wording, order, n, k, make({ n, s: SIDE[scenario], order }), switchQuestions));
    }
  }
  for (const scenario of FOOT) {
    const k = scenario === "footbridge_self" ? 0 : 1;
    const { f, v } = SLOTS[scenario];
    for (const wording of ["v1", "v2", "v3"]) for (const order of ORDERS) for (const n of SWEEP_N) cells.push(copy(`${scenario}|${wording}|${order}|${n}`));
    for (const [wording, make] of Object.entries(fWordings)) {
      for (const order of ORDERS) for (const n of SWEEP_N) cells.push(cell(scenario, wording, order, n, k, make({ n, order, f, v }), QUESTIONS[scenario]));
    }
  }
  return cells;
}

const text = (state) => (typeof state === "string" ? state : JSON.stringify(state));

function check(cells) {
  const problems = [];
  const ids = new Set();
  for (const c of cells) {
    if (ids.has(c.id)) problems.push(`duplicate ${c.id}`);
    ids.add(c.id);
    const t = text(c.state);
    if (/undefined|NaN|\[object|\$\{/.test(t)) problems.push(`template leak in ${c.id}`);
    if (c.scenario !== "literal_zero" && c.n === 0 && !/nobody|no one|empty|clear|unoccupied|no lives|"people(_on_[a-z_]+)?":0|people: 0/i.test(t)) problems.push(`N = 0 not stated as nobody in ${c.id}`);
  }
  // Re-rendered old wordings must match their frozen text
  const v1 = new Map(read("cells-v1.json").map((c) => [c.id, c]));
  const extra = new Map(read("cells-extra.json").map((c) => [c.id, c]));
  let matched = 0;
  for (const c of cells) {
    const ref = (["c1", "w2", "w3", "w4"].includes(c.wording) || ["v1", "v2", "v3"].includes(c.wording) || c.scenario === "literal_zero" ? v1 : /^x(0\d|1[0-6])$/.test(c.wording) ? extra : null)?.get(c.id);
    if (!ref) continue;
    matched += 1;
    if (text(ref.state) !== text(c.state) || JSON.stringify(ref.questions) !== JSON.stringify(c.questions)) problems.push(`old wording changed: ${c.id}`);
  }
  // Every wording of a family must render a different state at the same cell
  const byCell = new Map();
  for (const c of cells) {
    const key = `${c.scenario}|${c.order}|${c.n}`;
    const seen = byCell.get(key) ?? new Map();
    if (seen.has(text(c.state))) problems.push(`${c.id} renders the same text as ${seen.get(text(c.state))}`);
    seen.set(text(c.state), c.id);
    byCell.set(key, seen);
  }
  // Matched designs: every scenario in a family has the same (wording, order, n) cells
  for (const family of [AI, FOOT]) {
    const keys = family.map((s) => new Set(cells.filter((c) => c.scenario === s).map((c) => `${c.wording}|${c.order}|${c.n}`)));
    for (const ks of keys.slice(1)) if (ks.size !== keys[0].size || [...ks].some((x) => !keys[0].has(x))) problems.push(`unmatched cells in ${family.join("/")}`);
  }
  return { problems, matched };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cells = v2Cells();
  const { problems, matched } = check(cells);
  if (problems.length) throw new Error(`${problems.length} problems:\n${problems.slice(0, 40).join("\n")}`);
  const body = JSON.stringify({ prompt_version: V2_VERSION, cells }) + "\n";
  const sha = crypto.createHash("sha256").update(body).digest("hex");
  const out = path.join(HERE, "cells-v2.json");
  const shaFile = path.join(HERE, "cells-v2.json.sha256");
  if (process.argv.includes("--check")) {
    const committed = fs.readFileSync(shaFile, "utf8").split(/\s+/)[0];
    const onDisk = crypto.createHash("sha256").update(fs.readFileSync(out)).digest("hex");
    if (sha !== committed || onDisk !== committed) throw new Error(`cells-v2.json does not reproduce: generated ${sha}, file ${onDisk}, committed ${committed}`);
    console.log(`ok: cells-v2.json reproduces, sha256 ${sha}`);
  } else {
    fs.writeFileSync(out, body);
    fs.writeFileSync(shaFile, `${sha}  cells-v2.json\n`);
  }
  const counts = {};
  for (const c of cells) counts[c.scenario] = (counts[c.scenario] ?? 0) + 1;
  const wordings = {};
  for (const c of cells) (wordings[c.scenario] ??= new Set()).add(c.wording);
  console.log(JSON.stringify({ prompt_version: V2_VERSION, cells: cells.length, answers: cells.length * 3, sha256: sha, old_wording_cells_matched: matched, counts, wordings: Object.fromEntries(Object.entries(wordings).map(([s, w]) => [s, w.size])) }));
}

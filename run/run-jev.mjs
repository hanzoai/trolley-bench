// Jev runner for the v1 grid: every call goes through decision-gate (spend cap, rate limits).
// Usage: node run/run-jev.mjs <pass-name> [--dry-run] [--limit=N] [--cells=v2] [--cap=USD] [--out=DIR]
// Every pass is uncached, so the three passes measure Jev's own answer-to-answer stability
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, "..");
// decision-gate comes from npm at the version package-lock.json pins; DECISION_GATE_LIB overrides it
// with a checkout's lib/index.mjs, which is how v1 ran (git ff7271f, the same lib as npm 0.1.0)
const GATE = process.env.DECISION_GATE_LIB || "decision-gate";
const { openJev, describeError, estimateUsd } = await import(GATE);
const gateVersion = process.env.DECISION_GATE_LIB ? `lib ${GATE}` : JSON.parse(fs.readFileSync(path.join(ROOT, "node_modules", "decision-gate", "package.json"), "utf8")).version;
const KEY_ENV = process.env.TYPESAFE_ENV_FILE;

// Jev bills about 261 fixed input tokens per request on top of the body (measured in the pilot)
const FIXED_TOKENS = 261;
// Hard cap for one pass; three passes stay under USD 1.00 total. A v2 pass is about
// five times a v1 pass, so v2 passes --cap=0.15
const capFlag = process.argv.find((f) => f.startsWith("--cap="));
const RUN_CAP_USD = capFlag ? Number(capFlag.slice(6)) : 0.10;
if (!(RUN_CAP_USD > 0 && RUN_CAP_USD <= 0.25)) throw new Error("--cap must be above 0 and at most USD 0.25 per pass");

const [pass = "a", ...flags] = process.argv.slice(2);
const dryRun = flags.includes("--dry-run");
const limit = Number(flags.find((f) => f.startsWith("--limit="))?.slice(8)) || undefined;

// --cells=extra reads scenarios/cells-extra.json, the added wordings of the stranger / developer / own-server comparison
const cellsName = flags.find((f) => f.startsWith("--cells="))?.slice(8) ?? "v1";
// v2 lives in scenarios/v2/ with a committed sha256, checked before anything is sent
const cellsFile = cellsName.startsWith("v2") ? path.join(ROOT, "scenarios", "v2", `cells-${cellsName}.json`) : path.join(ROOT, "scenarios", `cells-${cellsName}.json`);
const cellsText = fs.readFileSync(cellsFile);
const cellsSha = crypto.createHash("sha256").update(cellsText).digest("hex");
if (fs.existsSync(`${cellsFile}.sha256`) && fs.readFileSync(`${cellsFile}.sha256`, "utf8").split(/\s+/)[0] !== cellsSha) throw new Error(`${path.basename(cellsFile)} does not match its committed sha256; rerun its freeze script`);
const frozen = JSON.parse(cellsText);
const cells = frozen.cells.slice(0, limit);
const bodies = cells.map((c) => Buffer.byteLength(JSON.stringify({ model: "jev-1.13.0", state: c.state, questions: c.questions })));
const estUsd = bodies.reduce((sum, b) => sum + estimateUsd(b) + (FIXED_TOKENS * 0.042) / 1e6, 0);
console.log(`pass ${pass}: ${cells.length} requests, estimated USD ${estUsd.toFixed(5)}, run cap USD ${RUN_CAP_USD}`);
if (dryRun) process.exit(0);
// decision-gate's ledger is daily and ends a run at 00:00 UTC, failing the rest of the pass; a v2
// pass takes about 5 minutes, so do not start one within 10 minutes of midnight UTC
const now = new Date();
const toMidnightMin = (Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1) - now.getTime()) / 60000;
if (toMidnightMin < 10) throw new Error(`${toMidnightMin.toFixed(1)} minutes to 00:00 UTC, when decision-gate ends the run; start after midnight`);

// The key never leaves this process except in the Authorization header decision-gate builds.
// TYPESAFE_API_KEY in the environment wins; TYPESAFE_ENV_FILE names a file with one such line
function readKey() {
  if (process.env.TYPESAFE_API_KEY) return process.env.TYPESAFE_API_KEY.trim();
  if (!KEY_ENV) throw new Error("set TYPESAFE_API_KEY, or TYPESAFE_ENV_FILE to a file with a TYPESAFE_API_KEY= line");
  const lines = fs.readFileSync(KEY_ENV, "utf8").split("\n").filter((l) => l.startsWith("TYPESAFE_API_KEY="));
  if (lines.length !== 1) throw new Error("expected exactly one TYPESAFE_API_KEY= line in the env file");
  return lines[0].slice("TYPESAFE_API_KEY=".length).trim().replace(/^["']|["']$/g, "");
}

const jev = openJev({ tool: "trolley-bench", key: { provider: "typesafe", value: readKey() }, spend: { perRunUsd: RUN_CAP_USD }, notice: (m) => console.error(`gate: ${m}`) });
const run = jev.run({ capUsd: RUN_CAP_USD });
// --out=<dir under the repo> keeps a side experiment out of results/raw, which build_results.py reads
// v2 defaults to results/v2/raw so it can never write over the published v1 rows
const outDir = path.join(ROOT, flags.find((f) => f.startsWith("--out="))?.slice(6) ?? (cellsName.startsWith("v2") ? path.join("results", "v2", "raw") : path.join("results", "raw")));
fs.mkdirSync(outDir, { recursive: true });
const outFile = path.join(outDir, cellsName === "v1" ? `jev-pass-${pass}.jsonl` : `jev-${cellsName}-pass-${pass}.jsonl`);
const rows = [];

async function answer(cell) {
  const started = performance.now();
  const at = new Date().toISOString();
  const response = await run.ask({ state: cell.state, questions: cell.questions });
  const ms = Math.round(performance.now() - started);
  const answers = Object.fromEntries(Object.keys(cell.questions).map((name) => [name, response.answers[name].noul]));
  const { state, questions, ...where } = cell;
  rows.push({ prompt_version: frozen.prompt_version, model_id: "jev", pass, ...where, answers, raw: response.answers, model: response.model, input_tokens: response.usage?.input_tokens, ms, at });
}

let failures = 0;
const t0 = Date.now();
try {
  const queue = [...cells];
  const worker = async () => {
    for (let cell; (cell = queue.shift());) {
      try { await answer(cell); }
      catch (error) { failures += 1; console.error(`failed ${cell.id}: ${describeError(error)}`); }
    }
  };
  await Promise.all(Array.from({ length: jev.config.limits.inFlight }, worker));
} finally {
  await run.close();
}
const order = new Map(frozen.cells.map((c, i) => [c.id, i]));
rows.sort((a, b) => order.get(a.id) - order.get(b.id));
// A pass with any failure is set aside as .partial, so the analysis never averages an incomplete pass
const rowsFile = failures ? outFile.replace(/\.jsonl$/, ".partial.jsonl") : outFile;
fs.writeFileSync(rowsFile, rows.map((r) => JSON.stringify(r)).join("\n") + "\n");
const summary = { pass, cells_file: path.relative(ROOT, cellsFile), cells_sha256: cellsSha, decision_gate: gateVersion, node: process.version, requests: cells.length, answered: rows.length, failures, input_tokens: rows.reduce((s, r) => s + (r.input_tokens ?? 0), 0), wall_s: Math.round((Date.now() - t0) / 1000), run: run.summary(), remaining_today_usd: await jev.remaining().catch(() => null), finished: new Date().toISOString() };
fs.writeFileSync(rowsFile.replace(/\.jsonl$/, ".summary.json"), JSON.stringify(summary, null, 2) + "\n");
console.log(JSON.stringify(summary));
if (failures) {
  console.error(`${failures} requests failed; rows kept in ${path.basename(rowsFile)} only`);
  process.exitCode = 1;
}

// OpenAI Decisions API runner for the v2 grid: the same cells, the same three questions in one request
// per cell, the same row shape as run-jev.mjs, so analysis/v2_stats.py reads it like any other model.
// Usage: node run/run-openai-decisions.mjs <pass-name> [--cells=v2|v1|extra] [--dry-run] [--sample=N] [--limit=N] [--cap=USD] [--out=DIR] [--concurrency=N]
// Every pass is a fresh set of requests (the API has no cache to bypass), so three passes measure its
// own answer-to-answer stability, as Jev's do
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, "..");
const ENDPOINT = "https://api.openai.com/v1/decisions";
const MODEL = "gpt-6-luna";
// USD per million input tokens, from the Decisions guide (2026-10-08); output is free
const USD_PER_M_INPUT = 0.10;

// decision-gate has no OpenAI provider, so the spend ceiling lives here: no request starts once the
// tokens already billed plus a pessimistic estimate of the in-flight ones would pass the cap
const capFlag = process.argv.find((f) => f.startsWith("--cap="));
const RUN_CAP_USD = capFlag ? Number(capFlag.slice(6)) : 0.40;
if (!(RUN_CAP_USD > 0 && RUN_CAP_USD <= 1.0)) throw new Error("--cap must be above 0 and at most USD 1.00 per pass");

const [pass = "a", ...flags] = process.argv.slice(2);
const flag = (name) => flags.find((f) => f.startsWith(`--${name}=`))?.slice(name.length + 3);
const dryRun = flags.includes("--dry-run");
const limit = Number(flag("limit")) || undefined;
const sample = Number(flag("sample")) || undefined;
const concurrency = Number(flag("concurrency")) || 8;

// --cells=v1 and --cells=extra are the published article's cells (v1 has no committed sha256, so
// its hash is only recorded); v2 is the default and is checked against its committed sha256
const cellsName = flag("cells") ?? "v2";
if (!["v2", "v2-sample", "v1", "extra"].includes(cellsName)) throw new Error("--cells must be v2, v2-sample, v1 or extra");
const cellsFile = cellsName.startsWith("v2") ? path.join(ROOT, "scenarios", "v2", `cells-${cellsName}.json`) : path.join(ROOT, "scenarios", `cells-${cellsName}.json`);
const cellsText = fs.readFileSync(cellsFile);
const cellsSha = crypto.createHash("sha256").update(cellsText).digest("hex");
if (cellsName.startsWith("v2") && fs.readFileSync(`${cellsFile}.sha256`, "utf8").split(/\s+/)[0] !== cellsSha) throw new Error("cells-v2.json does not match its committed sha256; run node scenarios/v2/freeze.mjs --check");
const frozen = JSON.parse(cellsText);
// --sample=N takes N cells evenly spaced through the file, so a slice touches every scenario
const cells = sample
  ? Array.from({ length: sample }, (_, i) => frozen.cells[Math.floor((i * frozen.cells.length) / sample)])
  : frozen.cells.slice(0, limit);

// The cells' questions are Jev's: each a yes/no ("noul") question, one with criteria for yes and no.
// Each becomes a two-option choice, "yes" or "no", so every row keeps the API's full distribution and
// confidence; the criteria question's own criteria text is the options' descriptions. No text is
// added to any question. The probability of "yes" is the number the analysis reads, and a refusal is
// kept as its own outcome (probability null), never as a missing row or an error
function decisionQuestions(questions) {
  return Object.entries(questions).map(([name, q]) => {
    if (q.type !== "noul") throw new Error(`unexpected question type ${q.type}`);
    const choices = q.criteria ? [{ value: "yes", description: q.criteria.true }, { value: "no", description: q.criteria.false }] : [{ value: "yes" }, { value: "no" }];
    return { type: "choice", name, instructions: q.instructions, choices };
  });
}

function outcome(answer) {
  if (!answer) return { outcome: "missing", yes: null };
  if (answer.type === "refusal") return { outcome: "refusal", yes: null };
  if (answer.type !== "choice") throw new Error(`unexpected answer type ${answer.type}`);
  return { outcome: String(answer.choice), yes: answer.probabilities.find((p) => String(p.value) === "yes").probability, confidence: answer.confidence };
}

// The structured wordings send the state as an object, but Decisions input must be text. The text is
// Python's json.dumps(state), byte for byte, as the Nimble, Verdict and SemIf adapters sent it:
// ", " and ": " separators, key order kept, non-ASCII escaped
function pyDumps(v) {
  if (Array.isArray(v)) return `[${v.map(pyDumps).join(", ")}]`;
  if (v && typeof v === "object") return `{${Object.entries(v).map(([k, x]) => `${pyDumps(k)}: ${pyDumps(x)}`).join(", ")}}`;
  return JSON.stringify(v).replace(/[\u007f-￿]/g, (ch) => `\\u${ch.charCodeAt(0).toString(16).padStart(4, "0")}`);
}
export const inputText = (state) => (typeof state === "string" ? state : pyDumps(state));

if (process.argv.includes("--print-inputs")) {
  for (const c of frozen.cells) console.log(JSON.stringify(inputText(c.state)));
  process.exit(0);
}
const bodies = cells.map((c) => JSON.stringify({ model: MODEL, input: inputText(c.state), questions: decisionQuestions(c.questions) }));
// Pessimistic pre-request estimate: one token per 3 bytes of body plus 300 tokens of fixed overhead
const estTokens = (body) => Math.ceil(Buffer.byteLength(body) / 3) + 300;
const estUsd = bodies.reduce((s, b) => s + (estTokens(b) * USD_PER_M_INPUT) / 1e6, 0);
console.log(`pass ${pass}: ${cells.length} requests, pessimistic estimate USD ${estUsd.toFixed(4)}, run cap USD ${RUN_CAP_USD}`);
if (dryRun) process.exit(0);

// The key never leaves this process except in the Authorization header below.
// OPENAI_API_KEY in the environment wins; OPENAI_ENV_FILE names a chmod-600 file with one such line
function readKey() {
  if (process.env.OPENAI_API_KEY) return process.env.OPENAI_API_KEY.trim();
  const file = process.env.OPENAI_ENV_FILE;
  if (!file) throw new Error("set OPENAI_API_KEY, or OPENAI_ENV_FILE to a file with an OPENAI_API_KEY= line");
  if ((fs.statSync(file).mode & 0o777) !== 0o600) throw new Error("OPENAI_ENV_FILE must be chmod 600");
  const lines = fs.readFileSync(file, "utf8").split("\n").filter((l) => l.startsWith("OPENAI_API_KEY="));
  if (lines.length !== 1) throw new Error("expected exactly one OPENAI_API_KEY= line in the env file");
  return lines[0].slice("OPENAI_API_KEY=".length).trim().replace(/^["']|["']$/g, "");
}
const KEY = readKey();

// v1 and extra rows go where analysis/build_results.py reads the article's models, so v2 rows can never mix in
const outDir = path.join(ROOT, flag("out") ?? (cellsName.startsWith("v2") ? path.join("results", "v2", "raw") : path.join("results", "raw")));
fs.mkdirSync(outDir, { recursive: true });
const outFile = path.join(outDir, `${MODEL}${cellsName === "extra" ? "-extra" : ""}-pass-${pass}.jsonl`);

let billedTokens = 0;
let reservedTokens = 0;
let stopped = null;
const usdOf = (tokens) => (tokens * USD_PER_M_INPUT) / 1e6;
const tokensOf = (usage) => usage?.input_tokens ?? usage?.prompt_tokens ?? usage?.total_tokens ?? null;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function post(body) {
  for (let attempt = 0; ; attempt++) {
    let res;
    try {
      res = await fetch(ENDPOINT, { method: "POST", headers: { authorization: `Bearer ${KEY}`, "content-type": "application/json" }, body, signal: AbortSignal.timeout(60000) });
    } catch (error) {
      if (attempt >= 5) throw new Error(`network: ${error.name}`);
      await sleep(1000 * 2 ** attempt);
      continue;
    }
    if (res.ok) return { json: await res.json(), requestId: res.headers.get("x-request-id") };
    const text = (await res.text()).slice(0, 300);
    // An exhausted balance is also a 429, but waiting never clears it
    const quota = text.includes("insufficient_quota");
    // Rate limits and server errors are retried; anything else is a request-shape error and stops the pass
    if ((res.status === 429 || res.status >= 500) && !quota && attempt < 6) {
      const after = Number(res.headers.get("retry-after")) * 1000 || 1000 * 2 ** attempt;
      await sleep(Math.min(after, 60000));
      continue;
    }
    const error = new Error(`HTTP ${res.status}: ${text}`);
    error.fatal = quota || (res.status !== 429 && res.status < 500);
    throw error;
  }
}

const rows = [];
const failed = [];
async function answer(cell, body) {
  const est = estTokens(body);
  if (usdOf(billedTokens + reservedTokens + est) > RUN_CAP_USD) {
    stopped ??= `cap: USD ${usdOf(billedTokens).toFixed(4)} billed, next request would pass USD ${RUN_CAP_USD}`;
    return;
  }
  reservedTokens += est;
  const started = performance.now();
  const at = new Date().toISOString();
  try {
    const { json, requestId } = await post(body);
    const ms = Math.round(performance.now() - started);
    const tokens = tokensOf(json.usage);
    billedTokens += tokens ?? est;
    const byName = Object.fromEntries(json.answers.map((a) => [a.name, a]));
    const scored = Object.fromEntries(Object.keys(cell.questions).map((name) => [name, outcome(byName[name])]));
    const pick = (field) => Object.fromEntries(Object.entries(scored).map(([name, o]) => [name, o[field] ?? null]));
    const { state, questions, ...where } = cell;
    const row = { prompt_version: frozen.prompt_version, model_id: MODEL, pass, ...where, answers: pick("yes"), outcomes: pick("outcome"), confidence: pick("confidence"),
      raw: json.answers, model: json.model, response_id: json.id, request_id: requestId, usage: json.usage, input_tokens: tokens, ms, at };
    // A missing answer is a malformed response, so the cell is asked again in a rerun; a refusal is an answer
    if (Object.values(row.outcomes).includes("missing")) failed.push({ id: cell.id, reason: "an answer was missing from the response", row });
    else rows.push(row);
  } catch (error) {
    failed.push({ id: cell.id, reason: error.message });
    if (error.fatal) stopped ??= `request error: ${error.message}`;
  } finally {
    reservedTokens -= est;
  }
}

const t0 = Date.now();
const queue = cells.map((c, i) => [c, bodies[i]]);
let done = 0;
const worker = async () => {
  for (let item; !stopped && (item = queue.shift());) {
    await answer(...item);
    if (++done % 500 === 0) console.error(`${done}/${cells.length}, USD ${usdOf(billedTokens).toFixed(4)}`);
  }
};
await Promise.all(Array.from({ length: concurrency }, worker));

const order = new Map(frozen.cells.map((c, i) => [c.id, i]));
rows.sort((a, b) => order.get(a.id) - order.get(b.id));
// A pass that is incomplete for any reason is set aside as .partial, so the analysis never averages it
const complete = rows.length === cells.length;
const rowsFile = complete ? outFile : outFile.replace(/\.jsonl$/, ".partial.jsonl");
fs.writeFileSync(rowsFile, rows.map((r) => JSON.stringify(r)).join("\n") + "\n");
const refusals = rows.reduce((n, r) => n + Object.values(r.outcomes).filter((o) => o === "refusal").length, 0);
const summary = { pass, cells: cellsName, model: MODEL, models_reported: [...new Set(rows.map((r) => r.model))], endpoint: ENDPOINT, cells_file: path.relative(ROOT, cellsFile), cells_sha256: cellsSha, sample: sample ?? null, node: process.version,
  requests: cells.length, answered: rows.length, refusals, failures: failed.length, failed: failed.slice(0, 50), stopped, input_tokens: rows.reduce((s, r) => s + (r.input_tokens ?? 0), 0),
  usage_reported: rows.every((r) => typeof r.input_tokens === "number"), billed_usd: Number(usdOf(billedTokens).toFixed(6)), cap_usd: RUN_CAP_USD, usd_per_m_input: USD_PER_M_INPUT,
  concurrency, wall_s: Math.round((Date.now() - t0) / 1000), finished: new Date().toISOString() };
fs.writeFileSync(rowsFile.replace(/\.jsonl$/, ".summary.json"), JSON.stringify(summary, null, 2) + "\n");
console.log(JSON.stringify({ ...summary, failed: summary.failed.slice(0, 5) }));
if (!complete) {
  console.error(`${cells.length - rows.length} cells unanswered; rows kept in ${path.basename(rowsFile)} only`);
  process.exitCode = 1;
}

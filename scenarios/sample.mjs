// Cut a stratified sample of cells-v1.json into scenarios/cells-sample.json for reduced reruns:
// every scenario, every wording, both orders, N in {0, 1, 2, 5, 10, 20} (switch also 50 and 100; literal_zero has only N = 0)
// The cells are copied unchanged, so rows from a sample run compare one for one with the committed v1 rows
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const NS = new Set([0, 1, 2, 5, 10, 20]);
const v1 = JSON.parse(fs.readFileSync(path.join(HERE, "cells-v1.json"), "utf8"));
const cells = v1.cells.filter((c) => NS.has(c.n) || (c.scenario === "switch" && (c.n === 50 || c.n === 100)));
const body = JSON.stringify({ prompt_version: v1.prompt_version, sample_of: "cells-v1.json", cells });
fs.writeFileSync(path.join(HERE, "cells-sample.json"), body + "\n");
const sha = crypto.createHash("sha256").update(body + "\n").digest("hex");
const counts = {};
for (const c of cells) counts[c.scenario] = (counts[c.scenario] ?? 0) + 1;
console.log(JSON.stringify({ prompt_version: v1.prompt_version, cells: cells.length, answers: cells.length * 3, sha256: sha, counts }));

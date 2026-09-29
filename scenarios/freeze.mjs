// Render every v1 cell once into scenarios/cells-v1.json; runners read only this frozen file
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { PROMPT_VERSION, v1Cells } from "./scenarios.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const cells = v1Cells();
const ids = new Set(cells.map((c) => c.id));
if (ids.size !== cells.length) throw new Error("duplicate cell ids");
const body = JSON.stringify({ prompt_version: PROMPT_VERSION, cells });
fs.writeFileSync(path.join(HERE, "cells-v1.json"), body + "\n");
const sha = crypto.createHash("sha256").update(body + "\n").digest("hex");
const counts = {};
for (const c of cells) counts[c.scenario] = (counts[c.scenario] ?? 0) + 1;
console.log(JSON.stringify({ prompt_version: PROMPT_VERSION, cells: cells.length, answers: cells.length * 3, sha256: sha, counts }));

"""Serve a Cloudflare Clef release over POST /v1/systemone, answering concurrent requests in batches.

  python run/v2/clef_batch_server.py <port> <snapshot dir> <model name> --max-batch B [--window-ms W]

For the parallel-answering test only. It uses nothing but the release's own joint_schema_model.py:
requests that arrive together (up to B, waiting at most W ms after the first) are encoded with
encode_record, padded together with collate_records and scored in one forward pass, and each
answer is built with systemone_answer, exactly as systemone() does for a batch of one. With
--max-batch 1 every request goes through systemone() itself, as run/clef_server.py does.
Bound to 127.0.0.1. bfloat16 on MPS, as released.
"""
import argparse
import json
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch

ap = argparse.ArgumentParser()
ap.add_argument("port", type=int)
ap.add_argument("path")
ap.add_argument("name")
ap.add_argument("--max-batch", type=int, required=True)
ap.add_argument("--window-ms", type=float, default=20.0)
a = ap.parse_args()
sys.path.insert(0, a.path)
from joint_schema_model import QUESTION_TYPES, collate_records, encode_record, load_release_model, systemone, systemone_answer  # noqa: E402

model, processor = load_release_model(a.path, device="mps", dtype=torch.bfloat16)
device = next(model.parameters()).device
jobs = queue.Queue()
batches = []


def check(body):
    # The same request checks systemone() makes before encoding
    questions = body.get("questions")
    if not isinstance(body.get("model"), str) or "state" not in body:
        raise ValueError("model and state are required")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("at least one question is required")
    for qid, q in questions.items():
        if q.get("type") not in QUESTION_TYPES:
            raise ValueError(f"{qid}: type must be noul, choice, or score")
        if q["type"] != "noul" and not q.get("criteria"):
            raise ValueError(f"{qid}: criteria must not be empty")


@torch.inference_mode()
def answer_batch(items):
    if a.max_batch == 1:
        body, slot = items[0]
        try:
            slot["out"] = systemone(model, processor, body)
        except ValueError as e:
            slot["error"] = str(e)
        return
    ready = []
    for body, slot in items:
        try:
            check(body)
            ready.append((body, slot, encode_record(processor.tokenizer, body, max_length=16384, processor=processor)))
        except ValueError as e:
            slot["error"] = str(e)
    if not ready:
        return
    logits = model(collate_records([r[2] for r in ready], processor.tokenizer.pad_token_id, device))
    for (body, slot, enc), per_record in zip(ready, logits):
        answers = {q.question_id: systemone_answer(body["questions"][q.question_id], dict(zip(q.option_ids, ql.float().softmax(-1).tolist())))
                   for q, ql in zip(enc.questions, per_record)}
        slot["out"] = {"model": body["model"], "answers": answers, "usage": {"input_tokens": len(enc.input_ids), "output_tokens": 0}, "batch": len(ready)}


def worker():
    # The only thread that touches the GPU
    while True:
        items = [jobs.get()]
        deadline = time.monotonic() + a.window_ms / 1000
        while len(items) < a.max_batch:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            try:
                items.append(jobs.get(timeout=left))
            except queue.Empty:
                break
        batches.append(len(items))
        try:
            answer_batch(items)
        except Exception as e:  # noqa: BLE001 - fail the batch's requests, keep serving
            for _body, slot in items:
                slot["error"] = f"{type(e).__name__}: {e}"
        for _body, slot in items:
            slot["done"].set()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/batches":
            self.send_error(404)
            return
        data = json.dumps({"batches": len(batches), "requests": sum(batches), "sizes": {str(k): batches.count(k) for k in sorted(set(batches))}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/v1/systemone":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        # systemone() requires a model name; our runner, like Jev's API, does not send one
        body.setdefault("model", a.name)
        slot = {"done": threading.Event()}
        jobs.put((body, slot))
        slot["done"].wait()
        if "out" in slot:
            data, code = json.dumps(slot["out"]).encode(), 200
        else:
            data, code = json.dumps({"error": slot["error"]}).encode(), 400
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


threading.Thread(target=worker, daemon=True).start()
print(f"serving {a.name} from {a.path} on http://127.0.0.1:{a.port}, batches of up to {a.max_batch}", flush=True)
ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()

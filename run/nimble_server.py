"""A /v1/systemone shim over Nimble's documented MLX ParallelScorer, on 127.0.0.1 only.

Nimble has no Noul; its native yes/no type is a boolean field. The adapter is mechanical and
labelled: each Noul becomes one boolean field whose description is the question's instructions,
with the criteria as the boolean's choice_descriptions when a question has them, and the noul is
the scorer's P(true). Each question is scored in its own call, because Nimble renders every field
of one schema into a shared prefix, and Jev judges each question without seeing the others.
Usage: python nimble_server.py <port>   (from the nimble clone, in .venv-mlx, after the merge step)
"""
import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nimble.scoring.parallel_scorer import ParallelScorer

config = json.loads(pathlib.Path(".cache/nimble-model.json").read_text())
scorer = ParallelScorer(**config)


def field(q):
    f = {"type": "boolean", "description": q["instructions"]}
    crit = q.get("criteria")
    if crit:
        f["choice_descriptions"] = {"true": crit["true"], "false": crit["false"]}
    return f


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        state = body["state"] if isinstance(body["state"], str) else json.dumps(body["state"])
        answers = {}
        for name, q in body["questions"].items():
            res = scorer.score(state, {"answer": field(q)})
            scores = res["fields"]["answer"]["scores"]
            answers[name] = {"type": "noul", "noul": float(scores["true"]), "scores": scores, "temperature": res.get("temperature")}
        out = json.dumps({"answers": answers, "model": f"{config['model_id']}@{config['revision']}"}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()

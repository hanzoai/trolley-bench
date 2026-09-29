"""A /v1/systemone shim over Verdict's documented DecisionEngine, on 127.0.0.1 only.

Verdict's Noul is a proposition with three outcomes (true, false, insufficient evidence) and no
criteria field. The adapter is mechanical and labelled: the proposition is the question's
instructions, with the criteria appended as "(Yes: ... No: ...)" when a question has them, and the
reported noul is P(true) / (P(true) + P(false)), Verdict's own conditional probability, computed
even when it abstains. The abstain probability is kept in the raw answer.
Usage: python verdict_server.py <port>   (run from the Verdict-open-jev clone, in its venv)
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rlcd import DecisionEngine, Noul

engine = DecisionEngine()


def proposition(q):
    crit = q.get("criteria")
    text = q["instructions"]
    return f"{text} (Yes: {crit['true']} No: {crit['false']})" if crit else text


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        state = body["state"] if isinstance(body["state"], str) else json.dumps(body["state"])
        names = list(body["questions"])
        queries = [Noul(id=n, proposition=proposition(body["questions"][n]), semantics="conditional_on_sufficient_evidence_v2") for n in names]
        res = engine.evaluate(context=state, queries=queries)
        answers = {}
        for n, r in zip(names, res.results):
            t, f = r.probabilities.get("true", 0.0), r.probabilities.get("false", 0.0)
            answers[n] = {"type": "noul", "noul": t / (t + f) if t + f else 0.5, "probabilities": r.probabilities, "is_abstention": r.is_abstention}
        out = json.dumps({"answers": answers, "model": "verdict (heman10x/rlcd-modernbert-151m v2, ONNX fp32 CPU)"}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()

"""Serve a Cloudflare Clef release over POST /v1/systemone with the release's own code.

  python run/clef_server.py <port> <snapshot dir> <model name>

The snapshot's joint_schema_model.py does the work: load_release_model() and systemone(), the
request-to-response function its model card documents. This file only adds the HTTP layer the
card leaves out, bound to 127.0.0.1. bfloat16 on MPS, as released.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch

port, path, name = int(sys.argv[1]), sys.argv[2], sys.argv[3]
sys.path.insert(0, path)
from joint_schema_model import load_release_model, systemone  # noqa: E402

model, processor = load_release_model(path, device="mps", dtype=torch.bfloat16)
# One request at a time: the model owns the GPU
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/systemone":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        # systemone() requires a model name; our runner, like Jev's API, does not send one
        body.setdefault("model", name)
        try:
            with lock:
                out = systemone(model, processor, body)
            data, code = json.dumps(out).encode(), 200
        except ValueError as e:
            data, code = json.dumps({"error": str(e)}).encode(), 400
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


print(f"serving {name} from {path} on http://127.0.0.1:{port}", flush=True)
HTTPServer(("127.0.0.1", port), Handler).serve_forever()

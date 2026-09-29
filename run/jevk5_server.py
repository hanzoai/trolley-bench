"""A /v1/systemone front for JevK5's documented llama.cpp path (jevk5.gguf.JevK5GGUF), on 127.0.0.1.

JevK5 reads Nouls natively; this only turns one request into one JevK5GGUF.decide call per
question, at the temperature the JevK5 README gives for jevk5-4b-v0.3-Q8_0.gguf (1.22, knockout 0.93).
Usage: python jevk5_server.py <port> <llama-server url>   (with jevk5 importable)
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jevk5 import JevK5GGUF

model = JevK5GGUF(url=sys.argv[2], temperature=1.22, knockout_temperature=0.93)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        answers = {name: model.decide(body["state"], q) for name, q in body["questions"].items()}
        out = json.dumps({"answers": answers, "model": "JevK5 v0.3 4B, jevk5-4b-v0.3-Q8_0.gguf"}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()

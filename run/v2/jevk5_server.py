"""A /v1/systemone front for JevK5's documented llama.cpp path, for the parallel-answering test.

  python run/v2/jevk5_server.py <port> <llama-server url>   (with jevk5 importable)
  JEVK5_CACHE_PROMPT=1 turns llama.cpp's prompt cache on (JevK5's client sends cache_prompt false)

The same as run/jevk5_server.py (one JevK5GGUF.decide call per question, temperature 1.22,
knockout 0.93 from the README table), plus two things the test needs: the prompt-cache switch, and
the prompt tokens llama.cpp actually evaluated (after any cache hit) returned under "usage".
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jevk5 import JevK5GGUF

CACHE = os.environ.get("JEVK5_CACHE_PROMPT") == "1"
seen = threading.local()


class Model(JevK5GGUF):
    def _post(self, path, payload):
        if path == "/completion":
            payload = {**payload, "cache_prompt": CACHE}
        out = super()._post(path, payload)
        if path == "/completion":
            t = out.get("timings") or {}
            seen.prompt_n = getattr(seen, "prompt_n", 0) + t.get("prompt_n", 0)
            seen.cached_n = getattr(seen, "cached_n", 0) + t.get("cache_n", 0)
        return out


model = Model(url=sys.argv[2], temperature=1.22, knockout_temperature=0.93)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        seen.prompt_n = seen.cached_n = 0
        answers = {name: model.decide(body["state"], q) for name, q in body["questions"].items()}
        out = json.dumps({"answers": answers, "model": "JevK5 v0.3 4B, jevk5-4b-v0.3-Q8_0.gguf",
                          "usage": {"prompt_tokens_evaluated": seen.prompt_n, "prompt_tokens_cached": seen.cached_n}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()

"""The Qwen3-8B encoder behind clm-serve, on 127.0.0.1 only, in place of the vLLM pooling server.

CLM's reference setup is `vllm serve Qwen/Qwen3-8B --runner pooling`, which needs an NVIDIA GPU. This
serves the same OpenAI-compatible /v1/embeddings contract on Apple silicon with transformers on MPS in
bfloat16 (the checkpoint's dtype, as vLLM would load it): each text is tokenized without special tokens
(Qwen3's tokenizer adds none anyway, and CLM's training recipe asks for none), the last 2048 tokens are
kept, and the embedding is the final hidden state of the last token, L2-normalised, which is vLLM's
LAST pooling for a causal LM. Texts run one at a time, so no padding can move the last token.
Usage: python clm_embedder.py <port> <model path> [max tokens]
"""
import base64
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

port, path = int(sys.argv[1]), sys.argv[2]
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
tok = AutoTokenizer.from_pretrained(path)
model = AutoModel.from_pretrained(path, torch_dtype=torch.bfloat16).to("mps").eval()
# One forward pass at a time: MPS is one device, and requests arrive on server threads
lock = threading.Lock()


def embed(ids):
    ids = ids[-cap:]
    with lock, torch.no_grad():
        h = model(input_ids=torch.tensor([ids], device="mps")).last_hidden_state[0, -1]
    v = h.float().cpu().numpy()
    return (v / (np.linalg.norm(v) + 1e-12)).astype(np.float32)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            self.reply(200, {"object": "list", "data": [{"id": "qwen3-8b", "object": "model"}]})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/embeddings":
            return self.reply(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
        data, tokens = [], 0
        for i, x in enumerate(inputs):
            ids = x if isinstance(x, list) else tok(x, add_special_tokens=False)["input_ids"]
            tokens += min(len(ids), cap)
            v = embed(ids)
            e = base64.b64encode(v.tobytes()).decode() if body.get("encoding_format") == "base64" else v.tolist()
            data.append({"object": "embedding", "index": i, "embedding": e})
        self.reply(200, {"object": "list", "model": body.get("model"), "data": data, "usage": {"prompt_tokens": tokens, "total_tokens": tokens}})

    def reply(self, code, obj):
        out = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


print(f"[embedder] {path} on mps, bfloat16, cap {cap}", flush=True)
ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

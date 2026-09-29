"""Nimble's documented model preparation (README, "Download the model"), with the v2 revision pinned.

It downloads the adapter and its pinned base, merges them once on the CPU in bf16, and records the
merged folder in .cache/nimble-model.json for the MLX scorer. Run from the nimble clone in its prep venv.
"""
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

repo = "bespokelabs/Bespoke-Nimble-9B-v2"
revision = "4b8c04d1ac2cea3e41e5e3c4d2130bcead2c0abe"
snapshot = Path(snapshot_download(repo, revision=revision, cache_dir=".cache/huggingface/hub"))
contract_file = snapshot / "schema_config.json"
contract = json.loads(contract_file.read_text()) if contract_file.exists() else {}
if contract:
    from transformers import AutoTokenizer
    from nimble.training.candidate_schema import validate_contract
    validate_contract(contract, AutoTokenizer.from_pretrained(snapshot))

model_path = snapshot
if (snapshot / "adapter_config.json").exists():
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

    base = Qwen3_5ForConditionalGeneration.from_pretrained(contract["model"], revision=contract["revision"], dtype=torch.bfloat16, device_map="cpu", cache_dir=".cache/huggingface/hub")
    adapter = PeftModel.from_pretrained(base, snapshot)
    merged = adapter.merge_and_unload(safe_merge=True)
    model_path = Path(".cache/models") / ("nimble-9b-" + snapshot.name)
    merged.save_pretrained(model_path)
    (model_path / "schema_config.json").write_text(json.dumps(contract, indent=2))
    AutoTokenizer.from_pretrained(snapshot).save_pretrained(model_path)
    (model_path / "READY.json").write_text(json.dumps({
        "model": repo, "revision": snapshot.name,
        "adapter_sha256": hashlib.sha256((snapshot / "adapter_model.safetensors").read_bytes()).hexdigest(),
    }, indent=2))

config = {"model_path": str(model_path.resolve()), "model_id": repo, "revision": snapshot.name, "max_input_tokens": contract.get("max_length", 2048)}
Path(".cache/nimble-model.json").write_text(json.dumps(config, indent=2))
print("Ready:", model_path, json.dumps({"base": contract.get("model"), "base_revision": contract.get("revision")}))

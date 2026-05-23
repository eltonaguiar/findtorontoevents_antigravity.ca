"""Sharded multi-backend semantic extraction for repo docs/research markdown.

Splits the .md corpus across kimi + xai (grok) + deepseek — three OpenAI-compatible
backends running concurrently — for ~3x throughput. graphify caches per-file, so
files already extracted by the earlier kimi run are skipped. Writes
graphify-out/.graphify_docs.json (merged across all three).
"""
import json
import os
import threading
from pathlib import Path

# Raise the LLM output cap before importing graphify — _resolve_max_tokens reads
# this. The 16384 default truncates JSON mid-string (~60K chars) -> parse failure.
os.environ.setdefault("GRAPHIFY_MAX_OUTPUT_TOKENS", "32768")

import graphify.llm as gllm  # noqa: E402
from graphify.llm import extract_corpus_parallel  # noqa: E402

ROOT = Path(".")
DOC_DIRS = ["docs", "reports", "updates", ".planning"]

# --- register cerebras + inception as OpenAI-compatible backends ---
# xai dropped: both X_AI_KEY and GROK_SUPER rejected 400 by api.x.ai (revoked keys).
# deepseek dropped: frequent malformed-JSON output. cerebras (gpt-oss-120b) is fast
# and reliable; inception (mercury-2) likewise.
gllm.BACKENDS["cerebras"] = {
    "base_url": "https://api.cerebras.ai/v1", "default_model": "gpt-oss-120b",
    "env_key": "CEREBRAS_API", "pricing": {"input": 0.3, "output": 0.5},
    "temperature": 0, "max_tokens": 16384,
}
gllm.BACKENDS["inception"] = {
    "base_url": "https://api.inceptionlabs.ai/v1", "default_model": "mercury-2",
    "env_key": "INCEPTION_AI_KEY", "pricing": {"input": 0.3, "output": 0.5},
    "temperature": 0, "max_tokens": 16384,
}

os.environ.setdefault(
    "MOONSHOT_API_KEY",
    os.environ.get("KIMI_MOONSHOT_APIKEY") or os.environ.get("KIMI_API_KEY") or "",
)

# (name, model, api_key)
BACKENDS = [
    ("kimi", "kimi-k2.5", os.environ["MOONSHOT_API_KEY"]),
    ("cerebras", "gpt-oss-120b", os.environ.get("CEREBRAS_API", "")),
    ("inception", "mercury-2", os.environ.get("INCEPTION_AI_KEY", "")),
]
N = len(BACKENDS)

# --- collect corpus ---
files: list[Path] = []
for d in DOC_DIRS:
    p = ROOT / d
    if p.is_dir():
        files.extend(sorted(p.rglob("*.md")))
files.extend(sorted(ROOT.glob("*.md")))
files = [f for f in files if f.is_file()]
print(f"docs collected: {len(files)}")

# --- shard round-robin ---
shards: list[list[Path]] = [[] for _ in range(N)]
for i, f in enumerate(files):
    shards[i % N].append(f)

results: dict[str, dict] = {}
errors: dict[str, str] = {}
lock = threading.Lock()


def run(idx: int) -> None:
    name, model, key = BACKENDS[idx]
    shard = shards[idx]
    if not key:
        with lock:
            errors[name] = "no api key"
        print(f"[{name}] SKIP — no api key")
        return
    print(f"[{name}] start — {len(shard)} files, model {model}")
    try:
        r = extract_corpus_parallel(
            shard, backend=name, api_key=key, model=model, root=ROOT,
            chunk_size=20, max_concurrency=4, token_budget=20000,
        )
        with lock:
            results[name] = r
        n = len(r.get("nodes", []))
        print(f"[{name}] DONE — {n} nodes, tok in={r.get('input_tokens')}")
    except Exception as e:  # noqa: BLE001
        with lock:
            errors[name] = f"{type(e).__name__}: {e}"
        print(f"[{name}] FAILED — {type(e).__name__}: {e}")


threads = [threading.Thread(target=run, args=(i,)) for i in range(N)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# --- merge ---
nodes: dict = {}
links: list = []
hyper: list = []
for name, r in results.items():
    for nd in r.get("nodes", []):
        nodes[nd.get("id")] = nd
    links.extend(r.get("links", r.get("edges", [])))
    hyper.extend(r.get("hyperedges", []))

out = {"nodes": list(nodes.values()), "links": links, "hyperedges": hyper,
       "input_tokens": sum(r.get("input_tokens", 0) for r in results.values()),
       "output_tokens": sum(r.get("output_tokens", 0) for r in results.values())}
Path("graphify-out/.graphify_docs.json").write_text(json.dumps(out), encoding="utf-8")
print(f"\nMERGED DOCS: {len(out['nodes'])} nodes, {len(links)} links")
print(f"backends ok: {list(results)} | errors: {errors}")

"""One-off: semantic-extract repo docs/research markdown into a graphify graph fragment.

Collects .md from docs/, reports/, updates/, .planning/ and repo root, runs
Gemini semantic extraction, writes graphify-out/.graphify_docs.json.
Safe to re-run — graphify caches per-file extraction.
"""
import json
import os
from pathlib import Path

from graphify.llm import extract_corpus_parallel

ROOT = Path(".")
DOC_DIRS = ["docs", "reports", "updates", ".planning"]

files: list[Path] = []
for d in DOC_DIRS:
    p = ROOT / d
    if p.is_dir():
        files.extend(sorted(p.rglob("*.md")))
files.extend(sorted(ROOT.glob("*.md")))

files = [f for f in files if f.is_file()]
print(f"docs collected: {len(files)}")

os.environ.setdefault(
    "MOONSHOT_API_KEY",
    os.environ.get("KIMI_MOONSHOT_APIKEY") or os.environ.get("KIMI_API_KEY") or "",
)
key = os.environ["MOONSHOT_API_KEY"]
model = os.environ.get("GRAPHIFY_KIMI_MODEL", "kimi-k2.5")

done = {"n": 0}


def _progress(*_a, **_k):
    done["n"] += 1
    if done["n"] % 10 == 0:
        print(f"  chunks done: {done['n']}", flush=True)


result = extract_corpus_parallel(
    files,
    backend="kimi",
    api_key=key,
    model=model,
    root=ROOT,
    chunk_size=20,
    on_chunk_done=_progress,
    max_concurrency=4,
)

out = Path("graphify-out/.graphify_docs.json")
out.write_text(json.dumps(result), encoding="utf-8")
nodes = result.get("nodes", [])
edges = result.get("edges", result.get("links", []))
print(f"DOCS EXTRACTION DONE: {len(nodes)} nodes, {len(edges)} edges -> {out}")
print(f"tokens: in={result.get('input_tokens')} out={result.get('output_tokens')}")

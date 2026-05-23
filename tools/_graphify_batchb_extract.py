"""One-off: kimi semantic extraction for Pine strategies + the two generated
inventory docs (DB schema, GH Actions). Writes graphify-out/.graphify_batchb.json.
"""
import json
import os
from pathlib import Path

from graphify.llm import extract_corpus_parallel

ROOT = Path(".")

files: list[Path] = []
for d in ["pine_scripts", "pine_strategies", "pinescripts", "pine_generator/templates"]:
    p = ROOT / d
    if p.is_dir():
        files.extend(sorted(p.rglob("*.pine")))
for f in [
    "docs/DB_SCHEMA_stocks_backtests_2026-05-15.md",
    "docs/GITHUB_ACTIONS_INVENTORY_2026-05-15.md",
]:
    p = ROOT / f
    if p.is_file():
        files.append(p)

files = [f for f in files if f.is_file()]
print(f"batch-b files: {len(files)}")

os.environ.setdefault(
    "MOONSHOT_API_KEY",
    os.environ.get("KIMI_MOONSHOT_APIKEY") or os.environ.get("KIMI_API_KEY") or "",
)
result = extract_corpus_parallel(
    files,
    backend="kimi",
    api_key=os.environ["MOONSHOT_API_KEY"],
    model=os.environ.get("GRAPHIFY_KIMI_MODEL", "kimi-k2.5"),
    root=ROOT,
    chunk_size=15,
    max_concurrency=2,
)
out = Path("graphify-out/.graphify_batchb.json")
out.write_text(json.dumps(result), encoding="utf-8")
nodes = result.get("nodes", [])
edges = result.get("edges", result.get("links", []))
print(f"BATCH-B DONE: {len(nodes)} nodes, {len(edges)} edges -> {out}")

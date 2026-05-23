"""Incremental graphify re-index of the docs changed in the 2026-05-15
verification session. kimi-extracts the changed files, merges their nodes into
the repo-level graphify-out/graph.json (dedup by id — updated docs replace
their old nodes), then the caller re-clusters.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("GRAPHIFY_MAX_OUTPUT_TOKENS", "32768")

from graphify.llm import extract_corpus_parallel  # noqa: E402

ROOT = Path(".")
CHANGED = [
    "FOOLPROOF_ACTION_PLAN.md",
    "reports/asset_class_action_items_2026-05-15.md",
    "reports/asset_class_verification_2026-05-15.md",
    "docs/DB_SCHEMA_stocks_backtests_2026-05-15.md",
]
files = [ROOT / f for f in CHANGED if (ROOT / f).is_file()]
print(f"re-indexing {len(files)} changed docs")

os.environ.setdefault(
    "MOONSHOT_API_KEY",
    os.environ.get("KIMI_MOONSHOT_APIKEY") or os.environ.get("KIMI_API_KEY") or "",
)
frag = extract_corpus_parallel(
    files, backend="kimi", api_key=os.environ["MOONSHOT_API_KEY"],
    model="kimi-k2.5", root=ROOT, chunk_size=10, max_concurrency=2,
    token_budget=20000,
)
fn = len(frag.get("nodes", []))
print(f"extracted {fn} nodes from changed docs")

graph_path = ROOT / "graphify-out" / "graph.json"
g = json.load(open(graph_path, encoding="utf-8"))
nodes = {n["id"]: n for n in g.get("nodes", []) if n.get("id")}
before = len(nodes)
for n in frag.get("nodes", []):
    if n.get("id"):
        nodes[n["id"]] = n  # updated docs overwrite their old nodes
links = g.get("links", g.get("edges", []))
seen = {(l.get("source"), l.get("target"), l.get("type") or l.get("relation")) for l in links}
for l in frag.get("links", frag.get("edges", [])):
    key = (l.get("source"), l.get("target"), l.get("type") or l.get("relation"))
    if key not in seen:
        seen.add(key)
        links.append(l)

out = {"nodes": list(nodes.values()), "links": links,
       "hyperedges": g.get("hyperedges", []) + frag.get("hyperedges", []),
       "input_tokens": 0, "output_tokens": 0}
json.dump(out, open(graph_path, "w", encoding="utf-8"))
print(f"merged: {before} -> {len(out['nodes'])} nodes, {len(links)} links")

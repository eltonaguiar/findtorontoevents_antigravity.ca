"""Merge every Graphify fragment into the repo-level graphify-out/graph.json.

Collects all per-directory code graphs plus the sitecode / docs / batch-b
semantic fragments, dedups nodes by id, and writes the unified graph.
The `graphify merge-graphs` CLI is broken on 0.8.3 (networkx) — hence manual.
"""
import json
from pathlib import Path

ROOT = Path(".")

frags: list[Path] = []
# per-directory code graphs
for p in ROOT.glob("*/graphify-out/graph.json"):
    parts = p.parts
    if any(x in parts for x in (".worktrees", ".claude", "node_modules")):
        continue
    frags.append(p)
# semantic + sitecode fragments
for name in (".graphify_sitecode.json", ".graphify_docs.json", ".graphify_batchb.json"):
    p = ROOT / "graphify-out" / name
    if p.is_file():
        frags.append(p)

nodes: dict = {}
links: list = []
hyper: list = []
seen_links: set = set()

for f in sorted(frags):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"SKIP {f}: {type(e).__name__}")
        continue
    fn = len(d.get("nodes", []))
    for n in d.get("nodes", []):
        nid = n.get("id")
        if nid:
            nodes[nid] = n
    fl = d.get("links", d.get("edges", []))
    for l in fl:
        key = (l.get("source"), l.get("target"), l.get("type") or l.get("relation"))
        if key not in seen_links:
            seen_links.add(key)
            links.append(l)
    hyper.extend(d.get("hyperedges", []))
    print(f"  {f}  ({fn} nodes)")

out = {"nodes": list(nodes.values()), "links": links, "hyperedges": hyper,
       "input_tokens": 0, "output_tokens": 0}
dst = ROOT / "graphify-out" / "graph.json"
json.dump(out, open(dst, "w", encoding="utf-8"))
print(f"\nMERGED {len(frags)} fragments -> {dst}")
print(f"  {len(out['nodes'])} nodes, {len(links)} links, {len(hyper)} hyperedges")

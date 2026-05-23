"""One-off: AST-extract site / events / audit critical code modules into a graph fragment.

Covers repo-root *.py (scrapers, event tools, dashboard + deploy scripts) plus the
production site/trading dirs not already in the per-dir graphs. Writes
graphify-out/.graphify_sitecode.json. AST-only — free, no LLM.
"""
import json
from pathlib import Path

from graphify.extract import collect_files, extract

ROOT = Path(".")

DIRS = [
    "TORONTOEVENTS_ANTIGRAVITY", "live-monitor", "signal_aggregator", "quan_engine",
    "multi_asset", "meta_strategy", "risk_management", "trading", "database",
    "shared", "findstocks", "findforex2", "quant_lab", "mercury2",
]

paths: list[Path] = []
# repo-root python files only (no recursion into already-mapped subdirs)
paths.extend(sorted(p for p in ROOT.glob("*.py") if p.is_file()))
# selected production dirs
for d in DIRS:
    p = ROOT / d
    if p.is_dir():
        paths.extend(collect_files(p, root=ROOT))

paths = [p for p in paths if p.is_file()]
print(f"site/audit code files collected: {len(paths)}")

result = extract(paths, cache_root=ROOT)
out = Path("graphify-out/.graphify_sitecode.json")
out.write_text(json.dumps(result), encoding="utf-8")
nodes = result.get("nodes", [])
edges = result.get("edges", result.get("links", []))
print(f"SITECODE EXTRACTION DONE: {len(nodes)} nodes, {len(edges)} edges -> {out}")

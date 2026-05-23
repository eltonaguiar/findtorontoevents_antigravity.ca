#!/usr/bin/env python3
"""Generate docs/BABY_PIPELINE_STATUS.md from baby_strategies/*.meta.json.

Fixes the prior version's bugs:
  1. Every row showed asset_class=UNKNOWN because the meta schema does
     not contain an `asset_class` field. The schema actually has:
     status, strategy_type, unique_value, backtest_metrics, batch_tested_at.
  2. Listed non-strategy files (backtest runners, framework wrappers) as
     "strategies" just because they had sibling .meta.json files.

This version reads what's actually in the meta files and filters out
non-strategy files by filename pattern.
"""
from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BABY_DIR = os.path.join(REPO_ROOT, "baby_strategies")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
DISABLED_JSON = os.path.join(REPO_ROOT, "stabilization", "disabled_strategies.json")

# Filename patterns that identify non-strategy files (test runners, wrappers,
# framework code) that happen to have meta.json siblings. These should not
# appear in a "pipeline status" doc.
NON_STRATEGY_PATTERNS = [
    r"^backtest_",
    r"^test_",
    r"^run_",
    r"_runner$",
    r"_runner_v\d+$",
    r"_framework$",
    r"_wrappers$",
    r"_wrappers_v\d+$",
    r"^forward_proven_",
    r"^strategy_framework",
]


def is_non_strategy_filename(name: str) -> bool:
    for pat in NON_STRATEGY_PATTERNS:
        if re.search(pat, name):
            return True
    return False


def load_graveyard() -> set[str]:
    if not os.path.exists(DISABLED_JSON):
        return set()
    try:
        with open(DISABLED_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return set()
    gy = data.get("graveyard") if isinstance(data, dict) else None
    if isinstance(gy, list):
        return set(str(x).lower() for x in gy)
    return set()


def metric(meta: dict, key: str):
    bm = meta.get("backtest_metrics") or {}
    return bm.get(key)


def fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    if x <= 1.5:
        x *= 100  # assume 0-1 scale
    return f"{x:.1f}%"


def fmt_num(v, places: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{places}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(v)}"
    except (TypeError, ValueError):
        return "—"


def generate():
    graveyard = load_graveyard()
    meta_files = sorted(glob.glob(os.path.join(BABY_DIR, "*.meta.json")))

    rows = []
    non_strategy_skipped = []
    for mf in meta_files:
        try:
            with open(mf, encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception as e:
            print(f"  [WARN] failed to parse {mf}: {e}")
            continue
        if not isinstance(meta, dict):
            continue

        base = os.path.basename(mf).replace(".meta.json", "")
        stem = base[:-3] if base.endswith(".py") else base

        if is_non_strategy_filename(stem):
            non_strategy_skipped.append(stem)
            continue

        mtime = os.path.getmtime(mf)
        last_mod = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

        status = meta.get("status", "—")
        strat_type = meta.get("strategy_type") or meta.get("category") or "—"
        wired = bool(meta.get("wired_in_scanner", False))
        is_gy = stem.lower() in graveyard or base.lower() in graveyard

        wr = metric(meta, "win_rate")
        pf = metric(meta, "profit_factor")
        sharpe = metric(meta, "sharpe")
        n_trades = metric(meta, "total_trades")

        rows.append({
            "stem": stem,
            "name": meta.get("name", stem),
            "status": status,
            "type": strat_type,
            "wired": wired,
            "graveyard": is_gy,
            "wr": wr,
            "pf": pf,
            "sharpe": sharpe,
            "n": n_trades,
            "last_mod": last_mod,
        })

    # Sort: wired strategies first, then by PF descending (None last), then name.
    def sort_key(r):
        pf = r["pf"] if isinstance(r["pf"], (int, float)) else -999
        return (0 if r["wired"] else 1, 1 if r["graveyard"] else 0, -pf, r["name"])
    rows.sort(key=sort_key)

    total = len(rows)
    wired_n = sum(1 for r in rows if r["wired"])
    gy_n = sum(1 for r in rows if r["graveyard"])
    with_backtest = sum(1 for r in rows if isinstance(r["pf"], (int, float)))
    profitable = sum(1 for r in rows if isinstance(r["pf"], (int, float)) and r["pf"] >= 1.5)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    md = [
        "# Baby Strategies Pipeline Status",
        "",
        f"**Generated programmatically at {now_str} from `baby_strategies/*.meta.json`. Do not edit manually.**",
        "",
        "## Summary",
        "",
        f"- Strategies inventoried: **{total}**",
        f"- Wired into scanner: **{wired_n}**",
        f"- In graveyard: **{gy_n}**",
        f"- With real backtest results: **{with_backtest}**",
        f"- Profit factor ≥ 1.5 in backtest: **{profitable}**",
        f"- Non-strategy files excluded (runners/wrappers/framework): **{len(non_strategy_skipped)}**",
        "",
        "## Schema Note",
        "",
        "The `.meta.json` schema does **not** contain an `asset_class` field — the original "
        "generator that reported \"UNKNOWN\" for every row was reading a key that isn't in the "
        "data. Asset class is not tracked per baby strategy at rest; it is inferred at runtime "
        "from the symbols the strategy chooses to emit. See `docs/ANTIGRAVITY_CROSSCHECK_2026-04-14.md`.",
        "",
        "## Pipeline Inventory",
        "",
        "| Strategy | Status | Type | Wired | WR | PF | Sharpe | N | Updated | Grave |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        wired_s = "✓" if r["wired"] else "·"
        grave_s = "💀" if r["graveyard"] else "·"
        md.append(
            f"| `{r['name']}` | {r['status']} | {r['type']} | {wired_s} | "
            f"{fmt_pct(r['wr'])} | {fmt_num(r['pf'])} | {fmt_num(r['sharpe'])} | "
            f"{fmt_int(r['n'])} | {r['last_mod']} | {grave_s} |"
        )

    if non_strategy_skipped:
        md.append("")
        md.append("## Excluded Files (non-strategy runners / wrappers / framework code)")
        md.append("")
        for name in sorted(non_strategy_skipped):
            md.append(f"- `{name}`")

    md.append("")
    md.append("---")
    md.append("*Generated by `scripts/generate_baby_pipeline_status.py`.*")

    out_path = os.path.join(DOCS_DIR, "BABY_PIPELINE_STATUS.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"Wrote {out_path}: {total} strategies, {wired_n} wired, {gy_n} graveyard, "
          f"{with_backtest} with backtest, {profitable} with PF>=1.5, "
          f"{len(non_strategy_skipped)} non-strategy files excluded")


if __name__ == "__main__":
    generate()

#!/usr/bin/env python3
"""per_class_winner_hunt.py — per-asset-class proven-winner ladder on deduped intrabar.

Grades each class:
  PROVEN     — n>=100, T2 (WR>=50, PF>=1.5), R1/R2/R3 pass
  PROBATION  — n>=30,  T2 + R1/R2/R3 pass (sizing hold until n>=100)
  WATCH      — best cell passes discipline OR T2 at n>=20; forward stamp
  NEG_FILTER — negative filter capturing >=50% class losses (FOREX contrarian)
  NONE       — no honest edge

Also scans entry-condition slices (reuse stamp features) and strategy×direction cells.

Usage:
  python3 tools/per_class_winner_hunt.py
  python3 tools/per_class_winner_hunt.py --json reports/per_class_winners_latest.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools.strategy_pass_hunter import (  # noqa: E402
    CLASS_BASELINE_WR,
    TIER2,
    fetch_cohort,
    grade_cell,
    metrics,
    r1_pass,
    r2_pass,
    r3_pass,
    tier2_pass,
)
from tools import stamp_entry_conditions as sec  # noqa: E402

ASSET_CLASSES = [
    "CRYPTO", "FOREX", "COMMODITY", "EQUITY", "ETF", "BOND", "FUTURES", "MEMECOIN",
]

FEATURE_KEYS = ("F1", "F2", "F3", "F4", "F5", "dow")


def ladder(full: bool, t2: bool, n: int) -> str:
    if full and n >= 100:
        return "PROVEN"
    if full and n >= TIER2["n"]:
        return "PROBATION"
    if full or t2:
        return "WATCH"
    return "NONE"


def grade_rows(rows: list[dict], label: str, cls: str) -> dict[str, Any]:
    baseline = CLASS_BASELINE_WR.get(cls, 0.40)
    g = grade_cell(rows, label, baseline)
    m = g.get("metrics") or {}
    n = m.get("n", 0)
    g["tier"] = ladder(g.get("full_pass", False), g.get("tier2", False), n)
    g["asset_class"] = cls
    return g


def strategy_cells(cohort: list[dict], cls: str, min_n: int = 10) -> list[dict]:
    rows = [r for r in cohort if (r.get("asset_class") or "").upper() == cls]
    buckets: dict[tuple, list] = defaultdict(list)
    for r in rows:
        d = "SHORT" if r["direction"] in ("SHORT", "SELL") else "LONG"
        strat = r.get("strategy") or r.get("source_system") or "?"
        buckets[(strat, d)].append(r)
    out = []
    for (strat, d), grp in buckets.items():
        if len(grp) < min_n:
            continue
        out.append(grade_rows(grp, f"{strat}|{d}", cls))
    return sorted(out, key=lambda x: (-x.get("full_pass", False), -x["metrics"]["pf"], -x["metrics"]["n"]))


def feature_slices(stamped: list[tuple[dict, dict]], cls: str, min_n: int = 20) -> list[dict]:
    """Singles + pair combos of entry features within a class."""
    rows_feats = [(p, f) for p, f in stamped if p["_cls"] == cls]
    if not rows_feats:
        return []

    def rows_for(pred) -> list[dict]:
        return [p for p, f in rows_feats if pred(p, f)]

    singles: list[dict] = []
    for key in FEATURE_KEYS:
        vals = sorted({f[key] for _, f in rows_feats})
        for v in vals:
            grp = rows_for(lambda p, f, k=key, val=v: f[k] == val)
            if len(grp) >= min_n:
                singles.append(grade_rows(grp, f"{key}={v}", cls))

    pairs: list[dict] = []
    for k1, k2 in combinations(FEATURE_KEYS, 2):
        v1s = sorted({f[k1] for _, f in rows_feats})
        v2s = sorted({f[k2] for _, f in rows_feats})
        for a in v1s:
            for b in v2s:
                grp = rows_for(lambda p, f, ka=k1, va=a, kb=k2, vb=b: f[ka] == va and f[kb] == vb)
                if len(grp) >= min_n:
                    pairs.append(grade_rows(grp, f"{k1}={a} & {k2}={b}", cls))

    all_slices = singles + pairs
    return sorted(all_slices, key=lambda x: (-x.get("full_pass", False), -x["metrics"]["pf"], -x["metrics"]["n"]))


def negative_filters(stamped: list[tuple[dict, dict]], cls: str) -> list[dict]:
    """Find single-feature slices with WR<35% and high loss capture."""
    rows_feats = [(p, f) for p, f in stamped if p["_cls"] == cls]
    if not rows_feats:
        return []
    baseline = [p for p, _ in rows_feats]
    bm = metrics(baseline)
    if not bm:
        return []
    total_loss = abs(sum(float(r["intrabar_pnl_pct"]) for r in baseline if float(r["intrabar_pnl_pct"] or 0) < 0))
    out = []
    for key in ("F1", "F2", "F3", "F4", "F5"):
        for v in sorted({f[key] for _, f in rows_feats}):
            bad = [p for p, f in rows_feats if f[key] == v]
            if len(bad) < 10:
                continue
            m = metrics(bad)
            if not m or m["wr"] >= 35:
                continue
            bad_loss = abs(sum(float(r["intrabar_pnl_pct"]) for r in bad if float(r["intrabar_pnl_pct"] or 0) < 0))
            capture = round(100 * bad_loss / total_loss, 1) if total_loss else 0
            remain = [p for p in baseline if p not in bad]
            rm = metrics(remain)
            out.append({
                "label": f"AVOID {key}={v}",
                "asset_class": cls,
                "bad_n": m["n"],
                "bad_wr": m["wr"],
                "loss_capture_pct": capture,
                "remaining": rm,
                "tier": "NEG_FILTER" if capture >= 50 else "NEG_WEAK",
            })
    return sorted(out, key=lambda x: -x["loss_capture_pct"])


def pick_class_winner(
    cells: list[dict],
    slices: list[dict],
    negs: list[dict],
    cls: str,
) -> dict[str, Any]:
    baseline_rows = []  # filled by caller
    best_full = next((x for x in cells + slices if x.get("full_pass")), None)
    best_t2 = next((x for x in cells + slices if x.get("tier2")), None)
    best_near = next(
        (x for x in cells + slices if x["metrics"]["n"] >= 15 and x["metrics"]["pf"] >= 1.3),
        None,
    )
    best_neg = negs[0] if negs else None

    if best_full:
        winner = best_full
        verdict = winner["tier"]
    elif best_t2:
        winner = best_t2
        verdict = "WATCH"
    elif best_near:
        winner = best_near
        verdict = "WATCH_FRAGILE"
    else:
        winner = cells[0] if cells else (slices[0] if slices else None)
        verdict = "NONE"

    return {
        "asset_class": cls,
        "verdict": verdict,
        "winner": winner,
        "best_strategy_cell": cells[0] if cells else None,
        "best_feature_slice": next((s for s in slices if s.get("full_pass") or s.get("tier2")), slices[0] if slices else None),
        "best_negative_filter": best_neg,
        "strategy_cells_top3": cells[:3],
        "feature_slices_top3": [s for s in slices if s.get("full_pass") or s.get("tier2")][:3] or slices[:3],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="", help="write report JSON")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cohort = fetch_cohort(args.limit)
    # stamp features (same as stamp_entry_conditions)
    by_table: dict[str, dict] = {"crypto_ohlcv": {}, "stock_ohlcv": {}}
    for p in cohort:
        p["_cls"] = (p["asset_class"] or "UNKNOWN").upper()
        is_crypto = p["_cls"] in ("CRYPTO", "MEMECOIN")
        tbl = "crypto_ohlcv" if is_crypto else "stock_ohlcv"
        cands = [p["symbol"]]
        if is_crypto:
            alt = p["symbol"].upper().replace("-", "").replace("/", "")
            if alt.endswith("USD") and not alt.endswith("USDT"):
                alt += "T"
            if alt != p["symbol"]:
                cands.append(alt)
        p["_barsyms"] = cands
        entry_ms = int(p["opened_at"].replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
        for s in cands:
            lo, hi = by_table[tbl].get(s, (entry_ms, entry_ms))
            by_table[tbl][s] = (min(lo, entry_ms), max(hi, entry_ms))
    bars = sec.fetch_bars(by_table)
    skips: dict[str, int] = {}
    stamped: list[tuple[dict, dict]] = []
    for p in cohort:
        sym_bars = next((bars[s] for s in p["_barsyms"] if bars.get(s)), [])
        f = sec.features(p, sym_bars, skips)
        if f is not None:
            stamped.append((p, f))

    report: dict[str, Any] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cohort_n_deduped": len(cohort),
        "stamped_n": len(stamped),
        "tier2_floor": TIER2,
        "proven_definition": "n>=100 + T2 + R1/R2/R3 on deduped intrabar ledger",
        "by_class": {},
        "summary_table": [],
    }

    print(f"cohort={len(cohort)} stamped={len(stamped)}\n")
    print(f"{'CLASS':<12}{'VERDICT':<16}{'BEST UNIT':<50}{'n':>5}{'WR%':>7}{'PF':>7}{'FULL':>6}")
    print("-" * 105)

    for cls in ASSET_CLASSES:
        cls_rows = [r for r in cohort if (r.get("asset_class") or "").upper() == cls]
        bl = metrics(cls_rows)
        cells = strategy_cells(cohort, cls)
        slices = feature_slices(stamped, cls)
        negs = negative_filters(stamped, cls)
        block = pick_class_winner(cells, slices, negs, cls)
        block["baseline"] = bl
        report["by_class"][cls] = block

        w = block.get("winner")
        if w and w.get("metrics"):
            m = w["metrics"]
            label = w.get("label", "?")[:48]
            full = "Y" if w.get("full_pass") else ""
        else:
            m = bl or {"n": 0, "wr": 0, "pf": 0}
            label = "(class baseline)" if bl else "(no data)"
            full = ""

        print(
            f"{cls:<12}{block['verdict']:<16}{label:<50}{m.get('n',0):>5}"
            f"{m.get('wr',0):>7.1f}{m.get('pf',0):>7.2f}{full:>6}"
        )

        report["summary_table"].append({
            "class": cls,
            "verdict": block["verdict"],
            "baseline_n": bl["n"] if bl else 0,
            "baseline_wr": bl["wr"] if bl else None,
            "baseline_pf": bl["pf"] if bl else None,
            "best_label": w.get("label") if w else None,
            "best_n": m.get("n"),
            "best_wr": m.get("wr"),
            "best_pf": m.get("pf"),
            "full_pass": bool(w and w.get("full_pass")),
        })

    proven = [r for r in report["summary_table"] if r["verdict"] == "PROVEN"]
    probation = [r for r in report["summary_table"] if r["verdict"] == "PROBATION"]
    report["proven_count"] = len(proven)
    report["probation_count"] = len(probation)

    print(f"\nPROVEN (n>=100): {len(proven)} | PROBATION (n>=30 full pass): {len(probation)}")
    for r in probation:
        print(f"  → {r['class']}: {r['best_label']} n={r['best_n']} WR={r['best_wr']}% PF={r['best_pf']}")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

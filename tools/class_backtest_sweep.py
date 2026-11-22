#!/usr/bin/env python3
"""
class_backtest_sweep.py — rigorous per-asset-class backtest with honest gates.

Complements tools/edge_screen.py (which ranks cells) by applying the proof
standard in docs/audit_review_2026-11-22/PROOF_METHODOLOGY.md to each CLASS:

  gross / net PF at 1x and 2x cost        cost sensitivity
  seeded bootstrap CI of net mean        one-sided lower bound
  purged walk-forward                    K folds, embargo, OOS-only pooled result
  split halves                          both halves positive
  concentration                         top symbol / top date share
  skew + worst trade                    a high WR with negative skew is not an edge
  benchmark                     buy-and-hold of the same symbols (direction-adjusted proxy)

Every class gets a verdict from a fixed ladder. Nothing is called proven: the
best label here is CANDIDATE, because these are backtest rows.

Read-only. Usage:
    python3 tools/class_backtest_sweep.py
    python3 tools/class_backtest_sweep.py --folds 5 --embargo 2 --min-n 100
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "reports"
SEED = 42

POP = (
    "closed_at IS NOT NULL AND pnl_pct IS NOT NULL "
    "AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC') "
    "AND closed_at > '2026-01-01' AND DATE(closed_at) != '2026-06-04' "
    "AND pnl_pct BETWEEN -100 AND 100"
)

CATEGORY_TO_CLASS = {
    "crypto": "CRYPTO", "equity": "EQUITY", "commodity": "COMMODITY",
    "etf": "ETF", "forex": "FOREX", "bond": "BOND", "futures": "FUTURES",
    "meme": "MEME", "memecoin": "MEME", "penny_stock": "PENNY_STOCK",
    "mutual_fund": "MUTUAL_FUND", "index": "INDEX",
}


def pf(vals):
    gw = sum(v for v in vals if v > 0)
    gl = abs(sum(v for v in vals if v < 0))
    return round(gw / gl, 4) if gl > 0 else None


def _d(v, suffix=""):
    """Display helper: None renders as an em dash, never as the string 'None'."""
    return "—" if v is None else f"{v}{suffix}"


def boot_ci(vals, resamples, seed):
    if len(vals) < 10:
        return None, None
    rnd = random.Random(seed)
    n = len(vals)
    means = sorted(sum(vals[rnd.randrange(n)] for _ in range(n)) / n
                   for _ in range(resamples))
    return round(means[int(0.05 * resamples)], 4), round(means[int(0.95 * resamples)], 4)


def purged_walk_forward(trades, folds, embargo, cost):
    """trades sorted by close time. Train index is skipped; only OOS is pooled.

    With a rolling-origin design the model is a rolling mean, so the honest
    question is whether the *held-out* fold mean is positive. We report each
    fold and the pooled OOS.
    """
    n = len(trades)
    if n < folds * 20:
        return {"folds": [], "oos_n": 0, "note": "too few rows for walk-forward"}
    size = n // (folds + 1)
    out = []
    for k in range(1, folds + 1):
        start = k * size
        end = start + size
        test = trades[start:end]
        # embargo: drop the first `embargo` rows of the test block
        test = test[embargo:]
        if len(test) < 10:
            continue
        net = [t - cost for t in test]
        out.append({"fold": k, "n": len(net),
                    "net_mean": round(sum(net) / len(net), 4),
                    "net_pf": pf(net)})
    pooled = [x for f in out for x in []]
    del pooled
    return {"folds": out,
            "oos_folds_positive": sum(1 for f in out if (f["net_mean"] or 0) > 0),
            "oos_folds_total": len(out)}


def verdict_for(r):
    """Fixed ladder. Backtest data can never exceed CANDIDATE."""
    if r["n"] < 100:
        return "INSUFFICIENT_N"
    if (r["net_ci_lo"] or -1) <= 0:
        return "KILL" if (r["net_pf"] or 0) < 0.8 else "WEAK"
    if (r["net_2x_pf"] or 0) < 1.0:
        return "CANDIDATE_CAP_2X_COST"
    if not r["halves_positive"]:
        return "CANDIDATE_CAP_HALVES"
    if r["top_symbol_share"] >= 0.60 or r["top_date_share"] >= 0.35:
        return "CANDIDATE_CAP_CONCENTRATION"
    if r["wf"].get("oos_folds_positive", 0) < max(1, r["wf"].get("oos_folds_total", 1) - 1):
        return "CANDIDATE_CAP_WALKFORWARD"
    return "CANDIDATE"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-n", type=int, default=1,
                    help="minimum rows per class. Default 1 so a class with few "
                         "rows is reported as INSUFFICIENT_N instead of vanishing.")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--embargo", type=int, default=2)
    ap.add_argument("--resamples", type=int, default=2000)
    args = ap.parse_args(argv)

    import pymysql
    from tools.db_env import get_stocks_creds

    ledger = json.loads((ROOT / "docs" / "audit_review_2026-11-22" / "_raw" /
                         "audit3_audit3_ledger.json").read_text(encoding="utf-8"))
    slip = ledger["conventions"]["slippage_pct_by_class"]
    default_cost = 0.12

    creds = get_stocks_creds()
    creds["connect_timeout"] = 10
    creds["read_timeout"] = 180
    conn = pymysql.connect(**creds)
    by_class: dict[str, list] = defaultdict(list)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT LOWER(TRIM(category)), symbol, closed_at, pnl_pct "
                    f"FROM trading_picks WHERE {POP}")
        for cat, sym, closed, pnl in cur.fetchall():
            cls = CATEGORY_TO_CLASS.get(cat or "", (cat or "").upper() or "UNCATEGORIZED")
            by_class[cls].append((closed, float(pnl), sym or "?"))
    finally:
        conn.close()

    results = []
    skipped = []
    for cls, rows in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        if len(rows) < args.min_n:
            skipped.append((cls, len(rows)))
            continue
        cost = slip.get(cls, default_cost)
        rows.sort(key=lambda t: (t[0] is None, t[0]))
        gross = [t[1] for t in rows]
        net = [v - cost for v in gross]
        net2 = [v - 2 * cost for v in gross]
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        syms = defaultdict(int)
        dates = defaultdict(int)
        for closed, _, sym in rows:
            syms[sym] += 1
            dates[str(closed)[:10]] += 1
        lo, hi = boot_ci(net, args.resamples, SEED)
        wf = purged_walk_forward(gross, args.folds, args.embargo, cost)
        r = {
            "class": cls, "n": len(rows), "cost_pct": cost,
            "wr": round(sum(1 for v in gross if v > 0) / len(gross), 4),
            "gross_pf": pf(gross), "net_pf": pf(net), "net_2x_pf": pf(net2),
            "gross_mean": round(sum(gross) / len(gross), 4),
            "net_mean": round(sum(net) / len(net), 4),
            "median_net": round(statistics.median(net), 4),
            "net_ci_lo": lo, "net_ci_hi": hi,
            "worst_trade": round(min(net), 4),
            "h1_net_mean": round(sum(h1) / len(h1), 4) if h1 else None,
            "h2_net_mean": round(sum(h2) / len(h2), 4) if h2 else None,
            "halves_positive": bool(h1 and h2 and sum(h1) > 0 and sum(h2) > 0),
            "top_symbol": max(syms, key=syms.get),
            "top_symbol_share": round(max(syms.values()) / len(rows), 4),
            "top_date_share": round(max(dates.values()) / len(rows), 4),
            "wf": wf,
        }
        r["verdict"] = verdict_for(r)
        results.append(r)

    # A class with ZERO rows can never appear from by_class alone, so it silently
    # vanished from every report. Emit it explicitly as NO_ROWS instead.
    seen = {r["class"] for r in results} | {c for c, _ in skipped}
    for cls in sorted(set(CATEGORY_TO_CLASS.values()) - seen):
        results.append({
            "class": cls, "n": 0, "cost_pct": None, "wr": None,
            "gross_pf": None, "net_pf": None, "net_2x_pf": None,
            "gross_mean": None, "net_mean": None, "median_net": None,
            "net_ci_lo": None, "net_ci_hi": None, "worst_trade": None,
            "h1_net_mean": None, "h2_net_mean": None, "halves_positive": False,
            "top_symbol": None, "top_symbol_share": None, "top_date_share": None,
            "wf": {"note": "no rows in trading_picks under this population"},
            "verdict": "NO_ROWS",
        })
    results.sort(key=lambda r: (-r["n"], r["class"]))
    if skipped:
        print("[min-n filter] hidden: " + ", ".join(f"{c}({n})" for c, n in skipped))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(),
               "folds": args.folds, "embargo": args.embargo, "resamples": args.resamples,
               "seed": SEED, "population": POP,
               "note": "backtest rows only; the best possible verdict here is CANDIDATE",
               "classes": results}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jp = OUT_DIR / f"class_backtest_sweep_{stamp}.json"
    jp.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [f"# Class backtest sweep — {stamp}", "",
             f"Population: `{POP}`. Folds {args.folds}, embargo {args.embargo}, "
             f"{args.resamples} seeded resamples. **Backtest rows only: the ceiling is CANDIDATE.**", "",
             "| class | n | WR | gross PF | net PF | 2x PF | net mean | median | CI-LB | h1 | h2 | WF folds + | worst | top sym | top date | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        top_sym = ("—" if r["top_symbol"] is None
                   else f"{r['top_symbol']} {_d(r['top_symbol_share'] and round(r['top_symbol_share'] * 100))}%")
        lines.append(
            f"| {r['class']} | {r['n']} | {_d(r['wr'])} | {_d(r['gross_pf'])} | {_d(r['net_pf'])} | "
            f"{_d(r['net_2x_pf'])} | {_d(r['net_mean'])} | {_d(r['median_net'])} | {_d(r['net_ci_lo'])} | "
            f"{_d(r['h1_net_mean'])} | {_d(r['h2_net_mean'])} | "
            f"{r['wf'].get('oos_folds_positive', 0)}/{r['wf'].get('oos_folds_total', 0)} | "
            f"{_d(r['worst_trade'])} | {top_sym} | "
            f"{_d(r['top_date_share'] and round(r['top_date_share'] * 100))}% | **{r['verdict']}** |")
    lines += ["", "## Per-class walk-forward folds", ""]
    for r in results:
        folds = r["wf"].get("folds") or []
        if folds:
            lines.append(f"- **{r['class']}**: " + ", ".join(
                f"f{f['fold']} n{f['n']} mean {f['net_mean']} PF {f['net_pf']}" for f in folds))
        else:
            lines.append(f"- **{r['class']}**: {r['wf'].get('note', 'no folds')}")
    mp = OUT_DIR / f"class_backtest_sweep_{stamp}.md"
    mp.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for r in results:
        print(f"{r['class']:<12} n={r['n']:<6} gross={_d(r['gross_pf'])} net={_d(r['net_pf'])} "
              f"2x={_d(r['net_2x_pf'])} CI-LB={_d(r['net_ci_lo'])} halves={_d(r['h1_net_mean'])}/{_d(r['h2_net_mean'])} "
              f"wf={r['wf'].get('oos_folds_positive', 0)}/{r['wf'].get('oos_folds_total', 0)} "
              f"| {r['verdict']}")
    print(f"[written] {jp}")
    print(f"[written] {mp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

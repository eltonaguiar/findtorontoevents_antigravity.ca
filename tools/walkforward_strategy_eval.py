#!/usr/bin/env python3
"""Walk-forward strategy evaluation harness.

This is the closest tool we can run to a true forward test before paper trading
exists: it takes closed resolved picks, applies artifact filters (sentinels,
flat-zero rows, duplicate ids, frozen-exit clusters), splits the remaining data
on a strict chronological boundary, and ranks (asset_class, symbol, strategy,
direction) cells whose edge *survives out-of-sample*.

Nothing here trades, sizes, or changes production behavior. It only reads closed
picks and emits an evidence report.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

SENTINEL_PNL = 999999.9999
INF_PF_CAP = 1_000_000.0
DEFAULT_INPUT = os.path.join("audit_dashboard", "data", "dashboard_data.json")
DEFAULT_OUT = os.path.join("reports", "walkforward_strategy_eval_2026-10-22.json")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_picks(path: str) -> list[dict]:
    """Load closed picks from a dashboard_data-style JSON (picks.recent_closed)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}) if isinstance(data, dict) else {}
    if isinstance(picks, dict):
        for key in ("recent_closed", "closed", "all", "closed_picks"):
            bucket = picks.get(key)
            if isinstance(bucket, list):
                return bucket
    if isinstance(picks, list):
        return picks
    return []


def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Cleaning / artifact filtering
# ---------------------------------------------------------------------------
def _is_win(row):
    st = (row.get("status") or "").upper()
    if st in ("WON", "WIN", "TP_HIT", "WON_CLOSED"):
        return True
    if st in ("LOST", "LOSS", "SL_HIT", "LOST_CLOSED"):
        return False
    pnl = row.get("pnl_pct")
    if pnl is None:
        return None
    return float(pnl) > 0


def clean_picks(rows):
    """Drop sentinel/flat/missing-pnl rows and duplicate ids. Returns (cleaned, dropped)."""
    cleaned = []
    dropped = Counter()
    seen_ids = set()
    for row in rows:
        if not isinstance(row, dict):
            dropped["not_dict"] += 1
            continue
        pid = row.get("id") or row.get("pick_id")
        if pid and pid in seen_ids:
            dropped["duplicate_ids"] += 1
            continue
        pnl = row.get("pnl_pct")
        if pnl is None:
            dropped["missing_pnl"] += 1
            continue
        try:
            pnl = float(pnl)
        except (TypeError, ValueError):
            dropped["bad_pnl"] += 1
            continue
        if abs(pnl) >= SENTINEL_PNL or pnl == 0.0:
            dropped["sentinel_placeholder"] += 1
            continue
        st = (row.get("status") or "").upper()
        if st in ("OPEN", "ACTIVE", "") and _is_win(row) is None:
            dropped["open_or_unresolved"] += 1
            continue
        if pid:
            seen_ids.add(pid)
        row = dict(row)
        row["pnl_pct"] = pnl
        ep = row.get("exit_price")
        if ep is not None:
            try:
                row["exit_price"] = float(ep)
            except (TypeError, ValueError):
                row["exit_price"] = None
        cleaned.append(row)
    return cleaned, dict(dropped)


def _cell_key(row):
    return f"{row.get('asset_class')}|{row.get('symbol')}|{row.get('strategy')}|{row.get('direction')}"


def detect_artifact_cells(rows):
    """Flag cells where wins > 2 x distinct exit dates (frozen-exit cluster)."""
    cells = defaultdict(lambda: {"wins": 0, "exit_dates": set()})
    for row in rows:
        if _is_win(row) is not True:
            continue
        key = _cell_key(row)
        cells[key]["wins"] += 1
        ts = row.get("closed_at") or row.get("timestamp")
        dt = _parse_ts(ts)
        if dt:
            cells[key]["exit_dates"].add(dt.date().isoformat())
    return {k for k, g in cells.items() if g["wins"] > 2 * max(1, len(g["exit_dates"]))}


# ---------------------------------------------------------------------------
# Walk-forward split
# ---------------------------------------------------------------------------
def walkforward_split(rows, frac=0.5):
    """Chronological split; every test row resolves at-or-after every train row."""
    dated = [( _parse_ts(r.get("closed_at") or r.get("timestamp")), r) for r in rows]
    dated = [x for x in dated if x[0] is not None]
    dated.sort(key=lambda x: x[0])
    cut = max(1, int(len(dated) * frac))
    train = [r for _, r in dated[:cut]]
    test = [r for _, r in dated[cut:]]
    return train, test


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_cell_metrics(rows):
    wins = losses = 0
    gross_profit = gross_loss = 0.0
    for r in rows:
        p = float(r.get("pnl_pct", 0.0))
        if p > 0:
            wins += 1
            gross_profit += p
        else:
            losses += 1
            gross_loss += abs(p)
    n = wins + losses
    wr = wins / n if n else 0.0
    # Infinite PF (no losses) is represented as a large cap so JSON stays strict.
    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = INF_PF_CAP
    else:
        pf = 0.0
    avg = (gross_profit - gross_loss) / n if n else 0.0
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "n_losses": losses,
        "perfect": losses == 0 and wins > 0,
        "wr": round(wr, 4),
        "pf": round(pf, 4),
        "avg_pnl_pct": round(avg, 4),
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate_all(cleaned, min_n=10):
    artifact = detect_artifact_cells(cleaned)
    flagged = [dict(r, _artifact_repeated_exit=(_cell_key(r) in artifact)) for r in cleaned]
    train, test = walkforward_split(flagged)

    cells = {}
    for period, rows in (("train", train), ("test", test)):
        grouped = defaultdict(list)
        for r in rows:
            grouped[_cell_key(r)].append(r)
        for key, rs in grouped.items():
            c = cells.setdefault(key, {"key": key, "artifact": key in artifact})
            c[period] = compute_cell_metrics(rs)
            cls, sym, strat, direction = key.split("|", 3)
            c["asset_class"], c["symbol"], c["strategy"], c["direction"] = cls, sym, strat, direction

    winners = []
    for key, c in cells.items():
        tr, te = c.get("train"), c.get("test")
        if not tr or not te:
            continue
        if c.get("artifact"):
            continue
        if tr["n"] < min_n or te["n"] < min_n:
            continue
        if te["pf"] < 1.15:
            continue
        if te["wr"] < 0.5:
            continue
        if tr["pf"] <= 1.0:
            continue
        c["stable_pf"] = round(min(tr["pf"], te["pf"]), 4)
        winners.append(c)
    winners.sort(key=lambda c: -c["stable_pf"])

    class_group = defaultdict(list)
    for r in test:
        class_group[r.get("asset_class") or "UNKNOWN"].append(r)
    classes = {cls: compute_cell_metrics(rs) for cls, rs in class_group.items()}

    return {
        "n_cleaned": len(cleaned),
        "n_train": len(train),
        "n_test": len(test),
        "artifact_cells": sorted(artifact),
        "classes": classes,
        "winners": winners,
        "cells": cells,
        "method": {
            "filters": ["sentinel/flat-pnl", "missing-pnl", "duplicate-id", "frozen-exit cluster"],
            "split": "chronological 50/50 walk-forward (train -> test)",
            "winner_gate": f"test n>=min_n, test PF>=1.15, test WR>=0.5, train PF>1.0, not artifact",
        },
    }


def _fmt_pf(pf):
    return "inf" if pf >= INF_PF_CAP else f"{pf:.3f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--min-n", type=int, default=10)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    raw = load_picks(args.input)
    if not raw:
        print(f"No closed picks found in {args.input}", file=sys.stderr)
        return 2
    cleaned, dropped = clean_picks(raw)
    if not cleaned:
        print("No clean picks after filtering.", file=sys.stderr)
        return 2
    res = evaluate_all(cleaned, min_n=args.min_n)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"Input: {args.input}  raw={len(raw)}  clean={len(cleaned)}  dropped={json.dumps(dropped)}")
    print(f"N train={res['n_train']}  N test={res['n_test']}")
    print(f"Artifact (frozen-exit) cells flagged: {len(res['artifact_cells'])}")
    print("\nOut-of-sample-winner cells (stable edge):")
    print(f"{'key':<52}{'tr_n':>5}{'tr_PF':>8}{'te_n':>5}{'te_WR':>7}{'te_PF':>8}{'stable_PF':>10}")
    for c in res["winners"]:
        print(f"{c['key']:<52}{c['train']['n']:>5}{_fmt_pf(c['train']['pf']):>8}"
              f"{c['test']['n']:>5}{c['test']['wr']:>7.3f}{_fmt_pf(c['test']['pf']):>8}"
              f"{c['stable_pf']:>10.3f}")
    print("\nClass-level (test half) metrics:")
    for cls, m in sorted(res["classes"].items(), key=lambda kv: -kv[1]["pf"] if kv[1]["pf"] else -1):
        print(f"  {cls:<12} n={m['n']:<6} WR={m['wr']:.3f} PF={_fmt_pf(m['pf'])}")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

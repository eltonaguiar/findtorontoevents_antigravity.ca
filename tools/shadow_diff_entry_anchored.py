#!/usr/bin/env python3
"""shadow_diff_entry_anchored.py — PR2 shadow-diff for the Bug 1A entry-anchored resolver.

READ-ONLY: zero production writes (no DB UPDATE/INSERT, no resolved-JSON write). Compares, for the
same open picks and the SAME production-style bar fetch, the resolution outcome of:
  LEGACY   : _check_tp_sl_intrabar with _ENTRY_ANCHORED=False  (today's default)
  ANCHORED : _check_tp_sl_intrabar with _ENTRY_ANCHORED=True   (PR2 candidate)
and classifies each pick: same / tp_sl_flip / intrabar->close_approx / close_approx->intrabar /
bad_geometry. Aggregates per asset class AND per confidence band (high >=0.75 vs low — Mercury
polish: quantify the inverted-confidence fix).

PRE-REGISTERED BLOCKING THRESHOLDS (set BEFORE running, per 2026-06-10 debate must-fix #9 —
default-ON is HELD unless ALL pass):
  T1. TP<->SL outcome flips among picks that stay intrabar-resolved: <= 30%
      (more suggests a logic error rather than window correction).
  T2. intrabar -> close_approx flips: <= 90% of previously-intrabar picks
      (more means the production fetch window almost never reaches entry -> fix the FETCH
       anchoring first, else default-ON just disables intrabar).
  T3. No class's still-intrabar WR INCREASES by > 10pp under ANCHORED
      (the fix should deflate/hold inflated WR, never inflate it).

Usage: python3 tools/shadow_diff_entry_anchored.py [--limit 400] [--out reports/...]
Writes ONLY a report JSON+MD under reports/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# Import the production functions (PR1 isolated the behavior in _check_tp_sl_intrabar +
# module flag _ENTRY_ANCHORED, so monkeypatching the flag gives an exact A/B).
import audit_trail.universal_pick_resolver as upr  # noqa: E402
import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")


def fetch_open_picks(limit: int) -> list[dict]:
    """Open/active picks the hourly resolver would process (read-only)."""
    conn = pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in _KEEP},
                           cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute(
        """SELECT id, symbol, category, strategy, direction, entry_price, take_profit, stop_loss,
                  confidence, created_at
           FROM trading_picks
           WHERE status IN ('OPEN','ACTIVE')
             AND entry_price IS NOT NULL AND take_profit IS NOT NULL AND stop_loss IS NOT NULL
           ORDER BY created_at DESC
           LIMIT %s""", (limit,))
    rows = list(cur.fetchall())
    conn.close()
    picks = []
    for r in rows:
        ts = r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if r.get("created_at") else None
        picks.append({
            "id": str(r["id"]), "symbol": r["symbol"], "category": (r.get("category") or "?").upper(),
            "strategy": r.get("strategy"), "direction": (r.get("direction") or "LONG").upper(),
            "entry_price": float(r["entry_price"]), "take_profit": float(r["take_profit"]),
            "stop_loss": float(r["stop_loss"]),
            "confidence": float(r["confidence"]) if r.get("confidence") is not None else None,
            "timestamp": ts,
        })
    return picks


def fetch_bars_for(symbols: set[str]) -> dict[str, list[dict]]:
    """Production-style symbol-level bar cache (same windows production uses)."""
    cache: dict[str, list[dict]] = {}
    for sym in sorted(symbols):
        norm = upr._normalize_symbol(sym)
        if norm in cache:
            continue
        try:
            if upr._is_non_crypto_symbol(norm):
                bars = upr._fetch_yfinance_ohlcv(norm, period="5d", interval="1h")
            else:
                bars = upr._fetch_binance_klines_ohlcv(norm, interval="1h", limit=48)
            cache[norm] = bars or []
        except Exception:
            cache[norm] = []
        time.sleep(0.08)
    return cache


def classify(pick: dict, bars: list[dict]) -> dict:
    """Run legacy vs anchored on the SAME bars; return classification."""
    # legacy
    p1 = dict(pick)
    upr._ENTRY_ANCHORED = False
    legacy = upr._check_tp_sl_intrabar(p1, bars) if bars else None
    # anchored
    p2 = dict(pick)
    upr._ENTRY_ANCHORED = True
    anchored = upr._check_tp_sl_intrabar(p2, bars) if bars else None
    upr._ENTRY_ANCHORED = False  # restore

    lr = legacy[0] if legacy else None
    ar = anchored[0] if anchored else None
    if p2.get("_intrabar_bad_geometry"):
        kind = "bad_geometry"
    elif lr == ar:
        kind = "same"
    elif lr and not ar:
        kind = "intrabar->close_approx"
    elif ar and not lr:
        kind = "close_approx->intrabar"
    else:
        kind = "tp_sl_flip"
    return {"legacy": lr, "anchored": ar, "kind": kind,
            "ambiguous": bool(p2.get("_intrabar_ambiguous"))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    picks = fetch_open_picks(args.limit)
    print(f"open picks loaded: {len(picks)}")
    bars_cache = fetch_bars_for({p["symbol"] for p in picks})
    n_with_bars = sum(1 for v in bars_cache.values() if v)
    print(f"bar cache: {n_with_bars}/{len(bars_cache)} symbols with bars")

    rows = []
    for p in picks:
        bars = bars_cache.get(upr._normalize_symbol(p["symbol"]), [])
        c = classify(p, bars)
        conf_band = "high" if (p["confidence"] or 0) >= 0.75 else "low"
        rows.append({**{k: p[k] for k in ("id", "symbol", "category", "strategy", "confidence")},
                     "conf_band": conf_band, **c, "had_bars": bool(bars)})

    # aggregate
    agg = defaultdict(lambda: defaultdict(int))
    for r in rows:
        agg[r["category"]][r["kind"]] += 1
        agg[r["category"]]["n"] += 1
        agg["_ALL_"][r["kind"]] += 1
        agg["_ALL_"]["n"] += 1
        agg[f"_CONF_{r['conf_band']}_"][r["kind"]] += 1
        agg[f"_CONF_{r['conf_band']}_"]["n"] += 1

    # threshold evaluation (pre-registered above)
    all_ = agg["_ALL_"]
    prev_intrabar = sum(1 for r in rows if r["legacy"])
    flips_to_close = all_.get("intrabar->close_approx", 0)
    tp_sl_flips = all_.get("tp_sl_flip", 0)
    still_intrabar = sum(1 for r in rows if r["legacy"] and r["anchored"])
    t1 = (tp_sl_flips / still_intrabar) <= 0.30 if still_intrabar else True
    t2 = (flips_to_close / prev_intrabar) <= 0.90 if prev_intrabar else True
    # T3: per-class WR among still-intrabar picks (legacy TP-rate vs anchored TP-rate)
    t3_ok, t3_detail = True, {}
    for cls in {r["category"] for r in rows}:
        sub = [r for r in rows if r["category"] == cls and r["legacy"] and r["anchored"]]
        if len(sub) >= 5:
            wl = sum(1 for r in sub if r["legacy"] == "TP_HIT") / len(sub)
            wa = sum(1 for r in sub if r["anchored"] == "TP_HIT") / len(sub)
            t3_detail[cls] = {"legacy_tp_rate": round(wl, 3), "anchored_tp_rate": round(wa, 3), "n": len(sub)}
            if wa - wl > 0.10:
                t3_ok = False

    verdict = "PASS — default-ON eligible" if (t1 and t2 and t3_ok) else "HOLD — threshold breached"
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "picks_sampled": len(rows), "symbols_with_bars": n_with_bars,
        "thresholds": {"T1_tp_sl_flip_rate<=0.30": t1, "T2_close_approx_flip<=0.90": t2,
                        "T3_no_class_wr_inflation>10pp": t3_ok, "t3_detail": t3_detail},
        "verdict": verdict,
        "aggregate": {k: dict(v) for k, v in agg.items()},
        "rows": rows,
    }
    out = args.out or os.path.join(REPO, "reports", "shadow_diff_entry_anchored_2026-06-10.json")
    with open(out, "w") as f:
        json.dump(payload, f, indent=1, default=str)
    print(f"\nVERDICT: {verdict}")
    print(f"prev-intrabar={prev_intrabar} -> close_approx flips={flips_to_close}, tp/sl flips={tp_sl_flips}, still-intrabar={still_intrabar}")
    for k, v in sorted(agg.items()):
        print(f"  {k}: {dict(v)}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

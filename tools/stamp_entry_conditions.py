#!/usr/bin/env python3
"""stamp_entry_conditions.py — SHADOW ENTRY-GATE forward measurement lane.

READ-ONLY DB -> JSON sidecar. Continuously accrues forward per-condition n for the
entry-conditioning candidates found in reports/entry_conditioning_experiment_2026-06-10.json
(CRYPTO RSI 50-70 x US session, luxalgo_confluence SHORT, EQUITY vol regimes, FOREX
trend alignment) WITHOUT touching the emission path or the verdict.

Mirrors the experiment meta exactly: entry-anchored honest cohort (at_signal_outcomes
intrabar TP_HIT/SL_HIT), dedup per (symbol, direction, day), strictly pre-entry 1h bars
(bar_open_ms + 3600000 <= entry_ms), scale guard, Wilder RSI, sigma72 vol regime.

Usage:  python3 tools/stamp_entry_conditions.py [--stdout] [--limit 4000]
Output: audit_dashboard/data/entry_conditions_forward.json  (default)
Discipline: measurement only — NEVER a sizing input until n>=100/condition + re-passes R1/R2/R3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")
HOUR_MS = 3600000
OUT_PATH = os.path.join(REPO, "audit_dashboard", "data", "entry_conditions_forward.json")
DISCIPLINE = ("forward-test measurement only; never a sizing input until n>=100/condition "
              "+ re-passes R1/R2/R3 (split-half, concentration, binomial p<0.005)")


def _conn():
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in _KEEP},
                           cursorclass=pymysql.cursors.DictCursor)


def fetch_cohort(limit: int) -> list[dict]:
    """Resolved intrabar cohort, deduped per (symbol, direction, day) keeping MIN id."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT o.id, o.symbol, UPPER(o.direction) AS direction, o.asset_class, o.strategy,
                  o.source_system, o.opened_at, o.entry_price, o.intrabar_status, o.intrabar_pnl_pct
           FROM at_signal_outcomes o
           JOIN (SELECT MIN(id) AS id FROM at_signal_outcomes
                 WHERE intrabar_resolved_at IS NOT NULL
                   AND intrabar_status IN ('TP_HIT','SL_HIT')
                   AND opened_at IS NOT NULL AND entry_price IS NOT NULL
                 GROUP BY symbol, UPPER(direction), DATE(opened_at)) d ON d.id = o.id
           ORDER BY o.opened_at DESC
           LIMIT %s""", (limit,))
    rows = list(cur.fetchall())
    conn.close()
    return rows


def fetch_bars(symbols_by_table: dict[str, dict]) -> dict[str, list]:
    """Per-symbol 1h closes (ms-epoch timestamps), oldest->newest, spanning each symbol's
    pick range plus a 410-bar pre-entry lookback (F4 uses up to 400 pre bars). Cap 8000."""
    conn = _conn()
    cur = conn.cursor()
    cache: dict[str, list] = {}
    for table, syms in symbols_by_table.items():
        for sym, (lo_ms, hi_ms) in sorted(syms.items()):
            cur.execute(
                f"""SELECT timestamp, close FROM {table}
                    WHERE symbol=%s AND timeframe='1h' AND timestamp BETWEEN %s AND %s
                    ORDER BY timestamp ASC LIMIT 8000""",
                (sym, lo_ms - 410 * HOUR_MS, hi_ms))
            cache[sym] = [(int(r["timestamp"]), float(r["close"])) for r in cur.fetchall()]
    conn.close()
    return cache


def wilder_rsi(closes: list[float], period: int = 14) -> float:
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains, losses = gains + max(d, 0.0), losses + max(-d, 0.0)
    ag, al = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
    if al == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def features(pick: dict, bars: list, skips: dict) -> dict | None:
    """Same entry-time features as the experiment; strictly pre-entry bars (no look-ahead)."""
    cls = (pick["asset_class"] or "UNKNOWN").upper()
    entry_ms = int(pick["opened_at"].replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    pre = [c for ts, c in bars if ts + HOUR_MS <= entry_ms]
    if not pre:
        skips[f"{cls}:no_bars"] = skips.get(f"{cls}:no_bars", 0) + 1
        return None
    if len(pre) < 77:
        skips[f"{cls}:insufficient_pre_bars"] = skips.get(f"{cls}:insufficient_pre_bars", 0) + 1
        return None
    entry = float(pick["entry_price"])
    if pre[-1] <= 0 or not (0.5 <= entry / pre[-1] <= 2.0):
        skips[f"{cls}:entry_scale_mismatch"] = skips.get(f"{cls}:entry_scale_mismatch", 0) + 1
        return None
    is_long = pick["direction"] != "SHORT"
    # F1 trend alignment: last pre close vs SMA50 x direction
    up = pre[-1] > sum(pre[-50:]) / 50.0
    f1 = "ALIGNED" if up == is_long else "CONTRARIAN"
    # F2 24-bar momentum with/against
    mom_up = pre[-1] / pre[-25] - 1.0 > 0
    f2 = "WITH" if mom_up == is_long else "AGAINST"
    # F3 Wilder RSI(14) band
    rsi = wilder_rsi(pre[-200:])
    f3 = "<30" if rsi < 30 else "30-50" if rsi < 50 else "50-70" if rsi <= 70 else ">70"
    # F4 vol regime: sigma72 of last 72 returns vs median rolling sigma72 (step 4, <=400 bars,
    # current window excluded)
    win = pre[-400:]
    rets = [win[i] / win[i - 1] - 1.0 for i in range(1, len(win)) if win[i - 1] > 0]
    cur_sig = statistics.pstdev(rets[-72:])
    hist = [statistics.pstdev(rets[e - 72:e]) for e in range(len(rets) - 4, 71, -4)]
    f4 = "HIGH" if cur_sig > (statistics.median(hist) if hist else cur_sig) else "LOW"
    # F5 session (US 13:30-21:00 UTC / EU 07:00-13:30 / ASIA else) + day-of-week
    t = pick["opened_at"].hour + pick["opened_at"].minute / 60.0
    f5 = "US" if 13.5 <= t < 21 else "EU" if 7 <= t < 13.5 else "ASIA"
    return {"F1": f1, "F2": f2, "F3": f3, "F4": f4, "F5": f5,
            "dow": pick["opened_at"].strftime("%a")}


CONDITIONS = [  # (name, class, definition, predicate(pick, feats))
    ("crypto_rsi5070_us", "CRYPTO", "F3 RSI(14,1h)=50-70 AND F5 session=US",
     lambda p, f: p["_cls"] == "CRYPTO" and f["F3"] == "50-70" and f["F5"] == "US"),
    ("luxalgo_short", "*", "strategy=luxalgo_confluence AND direction=SHORT",
     lambda p, f: "luxalgo_confluence" in ((p.get("strategy") or "") + (p.get("source_system") or ""))
     and p["direction"] == "SHORT"),
    ("equity_lowvol", "EQUITY", "class=EQUITY AND F4 vol regime=LOW",
     lambda p, f: p["_cls"] == "EQUITY" and f["F4"] == "LOW"),
    ("equity_highvol_NEGATIVE", "EQUITY", "NEGATIVE filter: class=EQUITY AND F4=HIGH (64% of losses)",
     lambda p, f: p["_cls"] == "EQUITY" and f["F4"] == "HIGH"),
    ("forex_trend_aligned", "FOREX", "class=FOREX AND F1 trend=ALIGNED (close vs SMA50 x dir)",
     lambda p, f: p["_cls"] == "FOREX" and f["F1"] == "ALIGNED"),
    ("forex_contrarian_NEGATIVE", "FOREX", "NEGATIVE filter: class=FOREX AND F1=CONTRARIAN (76% of losses)",
     lambda p, f: p["_cls"] == "FOREX" and f["F1"] == "CONTRARIAN"),
]


def stats(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "wr": None, "pf": None, "avg_pnl": None}
    wins = sum(1 for r in rows if r["intrabar_status"] == "TP_HIT")
    pnls = [float(r["intrabar_pnl_pct"]) for r in rows if r["intrabar_pnl_pct"] is not None]
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    pf = round(gp / gl, 3) if gl > 0 else (None if gp == 0 else float("inf"))
    return {"n": n, "wr": round(100.0 * wins / n, 1),
            "pf": (999.0 if pf == float("inf") else pf),
            "avg_pnl": round(sum(pnls) / len(pnls), 4) if pnls else None}


def main() -> int:
    ap = argparse.ArgumentParser(description="Shadow entry-gate forward measurement (read-only)")
    ap.add_argument("--stdout", action="store_true", help="print JSON to stdout instead of writing file")
    ap.add_argument("--limit", type=int, default=4000, help="max cohort rows (newest first)")
    args = ap.parse_args()

    cohort = fetch_cohort(args.limit)
    by_table: dict[str, dict] = {"crypto_ohlcv": {}, "stock_ohlcv": {}}
    for p in cohort:
        p["_cls"] = (p["asset_class"] or "UNKNOWN").upper()
        is_crypto = p["_cls"] in ("CRYPTO", "MEMECOIN")
        tbl = "crypto_ohlcv" if is_crypto else "stock_ohlcv"
        # crypto bars are keyed Binance-style (BTCUSDT); cohort may carry BTC-USD aliases
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
    bars = fetch_bars(by_table)

    skips: dict[str, int] = {}
    stamped = []
    for p in cohort:
        sym_bars = next((bars[s] for s in p["_barsyms"] if bars.get(s)), [])
        f = features(p, sym_bars, skips)
        if f is not None:
            stamped.append((p, f))

    # naive-UTC cutoff (opened_at comes back naive from MySQL)
    cutoff_30d = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=30)
    conds = list(CONDITIONS) + [
        (f"baseline_{c}", c, f"all {c} picks in cohort (class baseline)",
         (lambda cc: lambda p, f: p["_cls"] == cc)(c))
        for c in sorted({p["_cls"] for p, _ in stamped})]

    out_conditions = {}
    for name, cls, definition, pred in conds:
        rows = [p for p, f in stamped if pred(p, f)]
        last30 = [r for r in rows if r["opened_at"] >= cutoff_30d]
        s = stats(rows)
        s30 = stats(last30)
        negative = "NEGATIVE" in name
        note = ("negative filter — high n here means the avoid-rule keeps firing; verify WR stays low"
                if negative else
                ("n>=100 reached — re-run R1/R2/R3 before any sizing decision" if s30["n"] >= 100 or s["n"] >= 100
                 else "accruing forward n; below the n>=100 gate"))
        out_conditions[name] = {"class": cls, "definition": definition, **s,
                                "last30d": s30, "verdict_note": note}

    doc = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "read_only": True,
        "source_experiment": "reports/entry_conditioning_experiment_2026-06-10.json",
        "cohort_sql_note": ("at_signal_outcomes intrabar_resolved_at IS NOT NULL AND intrabar_status "
                            "IN ('TP_HIT','SL_HIT'); dedup (symbol,direction,day) MIN id; "
                            f"LIMIT {args.limit} ORDER BY opened_at DESC"),
        "cohort_n": len(cohort), "stamped_n": len(stamped), "skips": skips,
        "conditions": out_conditions,
        "discipline_note": DISCIPLINE,
    }

    # human-readable per-condition table (stderr so --stdout JSON stays clean)
    hdr = f"{'condition':<28}{'class':<9}{'n':>5}{'WR%':>7}{'PF':>8}{'avg':>9} | {'n30':>4}{'WR30':>7}{'PF30':>8}"
    print(hdr, file=sys.stderr)
    print("-" * len(hdr), file=sys.stderr)
    for name, c in out_conditions.items():
        l3 = c["last30d"]
        print(f"{name:<28}{c['class']:<9}{c['n']:>5}{c['wr'] if c['wr'] is not None else '-':>7}"
              f"{c['pf'] if c['pf'] is not None else '-':>8}"
              f"{c['avg_pnl'] if c['avg_pnl'] is not None else '-':>9} | "
              f"{l3['n']:>4}{l3['wr'] if l3['wr'] is not None else '-':>7}"
              f"{l3['pf'] if l3['pf'] is not None else '-':>8}", file=sys.stderr)

    payload = json.dumps(doc, indent=2, default=str)
    if args.stdout:
        print(payload)
    else:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w") as fh:
            fh.write(payload + "\n")
        print(f"wrote {OUT_PATH} ({len(stamped)} stamped / {len(cohort)} cohort)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

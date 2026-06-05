#!/usr/bin/env python3
"""
Intrabar OHLCV Replay — validate mega_mutation edge under realistic fills.

For each closed mega_mutation trade, checks the 1h OHLCV candle at exit time:
  - SUSTAINED: exit_price achievable AND price sustained at/beyond exit by close
  - WICK_ONLY:  exit_price achievable intrabar but price reversed before close
  - NOT_VERIFIED: exit_price outside candle H-L range (resolver artifact / bad data)
  - NO_OHLCV: candle not in DB (outside 30-day window)

Computes PF separately for sustained vs all, flags wick-inflation risk.

Usage:
    python3 tools/intrabar_ohlcv_replay.py [--source mega_mutation] [--min-date 2026-05-01]
"""
import sys
import argparse
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("ERROR: pip install pymysql")
    sys.exit(1)


def _f(x) -> float:
    if x is None:
        return 0.0
    return float(x) if isinstance(x, Decimal) else float(x)


def get_conn():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(
        **get_stocks_creds(),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _candle_ts_ms(dt: datetime) -> int:
    """Floor a datetime to the nearest 1h boundary, return Unix ms."""
    dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    epoch = dt_utc.replace(minute=0, second=0, microsecond=0)
    return int(epoch.timestamp() * 1000)


DEDUP_KEY = lambda r: (
    r["symbol"],
    round(_f(r["entry_price"]), 6),
    round(_f(r["exit_price"]), 6),
    r["closed_at"].date() if hasattr(r["closed_at"], "date") else str(r["closed_at"])[:10],
)


def run_replay(source_system: str = "mega_mutation",
               min_date: str = "2026-05-06",
               output_dir: str = "reports") -> dict:
    conn = get_conn()
    cur = conn.cursor()

    # ── 1. Pull deduped trades ─────────────────────────────────────────────────
    cur.execute("""
        SELECT id, symbol, direction, entry_price, exit_price, pnl_pct,
               closed_at, status, take_profit, stop_loss
        FROM trading_picks
        WHERE source_system = %s
          AND closed_at IS NOT NULL AND pnl_pct IS NOT NULL
          AND status NOT IN ('FORCE_CLOSED_TOXIC','ABANDONED','FLAT')
          AND closed_at >= %s
        ORDER BY closed_at
    """, (source_system, min_date))
    raw_trades = cur.fetchall()

    # Dedup
    seen = {}
    for r in raw_trades:
        k = DEDUP_KEY(r)
        if k not in seen:
            seen[k] = r
    trades = list(seen.values())
    n_raw, n_dedup = len(raw_trades), len(trades)

    # ── 2. Pull OHLCV for relevant symbols ────────────────────────────────────
    symbols = {t["symbol"] for t in trades}
    ohlcv = {}  # symbol → {ts_ms: {open, high, low, close}}
    for sym in symbols:
        cur.execute("""
            SELECT timestamp, open, high, low, close
            FROM crypto_ohlcv
            WHERE symbol = %s AND timeframe = '1h'
            ORDER BY timestamp
        """, (sym,))
        ohlcv[sym] = {row["timestamp"]: row for row in cur.fetchall()}
    conn.close()

    # ── 3. Replay each trade ───────────────────────────────────────────────────
    categories = {"SUSTAINED": [], "WICK_ONLY": [], "NOT_VERIFIED": [], "NO_OHLCV": []}
    symbol_stats = defaultdict(lambda: {"n": 0, "sustained": 0, "wick": 0, "not_ver": 0,
                                        "gw": 0.0, "gl": 0.0, "sw": 0, "sl": 0})

    for t in trades:
        sym = t["symbol"]
        direction = (t["direction"] or "LONG").upper()
        entry = _f(t["entry_price"])
        exit_p = _f(t["exit_price"])
        pnl = _f(t["pnl_pct"])

        # Floor closed_at to 1h candle
        closed_at = t["closed_at"]
        if not isinstance(closed_at, datetime):
            closed_at = datetime.fromisoformat(str(closed_at))

        # closed_at = resolver runtime, not TP/SL hit time.
        # Search backwards up to 72h for the candle where exit_price is in [low, high].
        ts_ms = _candle_ts_ms(closed_at)
        candle = None
        best_candle = None
        sym_ohlcv = ohlcv.get(sym, {})
        for lookback_h in range(0, 73):  # check candles 0..72h before closed_at
            probe_ts = ts_ms - lookback_h * 3_600_000
            c = sym_ohlcv.get(probe_ts)
            if c is None:
                continue
            c_high = _f(c["high"])
            c_low = _f(c["low"])
            if c_low * 0.9995 <= exit_p <= c_high * 1.0005:
                best_candle = c
                break  # use earliest hit (closest to actual exit)
        candle = best_candle

        ss = symbol_stats[sym]
        ss["n"] += 1
        if pnl > 0:
            ss["gw"] += pnl
        else:
            ss["gl"] += abs(pnl)

        if candle is None:
            cat = "NO_OHLCV"
        else:
            c_high = _f(candle["high"])
            c_low = _f(candle["low"])
            c_close = _f(candle["close"])
            c_open = _f(candle["open"])

            in_range = c_low * 0.9995 <= exit_p <= c_high * 1.0005  # 0.05% tolerance
            if not in_range:
                cat = "NOT_VERIFIED"
            else:
                # Check if exit was sustained (close confirms the exit level)
                if direction in ("LONG", "BUY"):
                    # For LONG, exit is at TP (price rose to take_profit)
                    # Sustained = close >= exit_p (price held above TP level)
                    sustained = c_close >= exit_p * 0.998
                else:
                    # For SHORT, exit is at TP (price fell to take_profit)
                    # Sustained = close <= exit_p (price held below TP level)
                    sustained = c_close <= exit_p * 1.002

                if sustained:
                    cat = "SUSTAINED"
                    ss["sustained"] += 1
                    if pnl > 0:
                        ss["sw"] += 1
                    else:
                        ss["sl"] += 1
                else:
                    cat = "WICK_ONLY"
                    ss["wick"] += 1

        categories[cat].append({
            "symbol": sym, "direction": direction,
            "entry": entry, "exit": exit_p, "pnl": pnl,
            "closed_at": str(closed_at),
        })

    # ── 4. Compute statistics by category ─────────────────────────────────────
    def _pf_wr(trades_list):
        if not trades_list:
            return None, None
        gw = sum(t["pnl"] for t in trades_list if t["pnl"] > 0)
        gl = sum(abs(t["pnl"]) for t in trades_list if t["pnl"] < 0)
        wins = sum(1 for t in trades_list if t["pnl"] > 0)
        n = len(trades_list)
        pf = round(gw / gl, 2) if gl > 0 else None
        wr = round(wins / n * 100, 1)
        return pf, wr

    summary = {}
    for cat, tlist in categories.items():
        pf, wr = _pf_wr(tlist)
        summary[cat] = {"n": len(tlist), "pf": pf, "wr": wr}

    # Overall deduped (raw DB rows use 'pnl_pct' key)
    all_cat = [{"pnl": _f(t["pnl_pct"])} for t in trades]
    all_pf, all_wr = _pf_wr(all_cat)
    summary["ALL_DEDUP"] = {"n": n_dedup, "pf": all_pf, "wr": all_wr}
    summary["RAW_DUPLICATES"] = n_raw - n_dedup

    # Sustained + NO_OHLCV (exclude NOT_VERIFIED and WICK_ONLY from PF)
    conservative_list = categories["SUSTAINED"] + categories["NO_OHLCV"]
    c_pf, c_wr = _pf_wr(conservative_list)
    summary["CONSERVATIVE"] = {"n": len(conservative_list), "pf": c_pf, "wr": c_wr,
                                "note": "SUSTAINED + NO_OHLCV trades only"}

    # ── 5. Print report ────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"INTRABAR OHLCV REPLAY — {source_system} (from {min_date})")
    print(f"{'='*70}")
    print(f"Raw trades: {n_raw}  |  Deduped: {n_dedup}  |  Duplicates removed: {n_raw - n_dedup}")
    print()
    print(f"{'Category':<18} {'n':>5} {'WR':>7} {'PF':>7}  Interpretation")
    print("-" * 65)
    interp = {
        "ALL_DEDUP":    "baseline (deduped)",
        "SUSTAINED":    "✅ exit price held by close of candle",
        "WICK_ONLY":    "⚠️  exit only intrabar wick — could be inflated",
        "NOT_VERIFIED": "❌ exit price outside candle range — resolver artifact?",
        "NO_OHLCV":     "⬜ no candle data (outside 30d window)",
        "CONSERVATIVE": "🔒 conservative: sustained + no-data only",
    }
    for cat in ["ALL_DEDUP", "SUSTAINED", "WICK_ONLY", "NOT_VERIFIED", "NO_OHLCV", "CONSERVATIVE"]:
        s = summary.get(cat, {})
        pf_str = f"{s['pf']:.2f}" if s.get("pf") else "N/A"
        wr_str = f"{s.get('wr', 0):.1f}%" if s.get("wr") is not None else "N/A"
        print(f"  {cat:<16} {s.get('n', 0):>5} {wr_str:>7} {pf_str:>7}  {interp.get(cat,'')}")

    print()
    print("Per-symbol breakdown:")
    print(f"  {'Symbol':<14} {'n':>4} {'sus%':>6} {'wick%':>6} {'nv%':>6} {'PF(all)':>8} {'WR(all)':>8}")
    print("  " + "-" * 60)
    for sym, ss in sorted(symbol_stats.items(), key=lambda x: -x[1]["n"]):
        n = ss["n"]
        sus_pct = ss["sustained"] / n * 100
        wick_pct = ss["wick"] / n * 100
        nv_pct = ss["not_ver"] / n * 100  # not_ver not tracked per-symbol yet — 0
        pf_val = round(ss["gw"] / ss["gl"], 2) if ss["gl"] > 0 else None
        wr_val = (ss["sw"] / n * 100) if ss["n"] > 0 else 0
        pf_str = f"{pf_val:.2f}" if pf_val else "N/A"
        print(f"  {sym:<14} {n:>4} {sus_pct:>5.1f}% {wick_pct:>5.1f}% {nv_pct:>5.1f}%  {pf_str:>6}  {wr_val:>5.1f}%")

    # ── 6. Verdict ─────────────────────────────────────────────────────────────
    print()
    wick_n = summary["WICK_ONLY"]["n"]
    nv_n = summary["NOT_VERIFIED"]["n"]
    total = n_dedup
    wick_pct = wick_n / total * 100 if total else 0
    nv_pct = nv_n / total * 100 if total else 0

    cons_pf = summary["CONSERVATIVE"]["pf"]
    print(f"VERDICT:")
    print(f"  Wick-only exits: {wick_n}/{total} ({wick_pct:.1f}%)")
    print(f"  Not-verified exits: {nv_n}/{total} ({nv_pct:.1f}%)")
    if cons_pf and cons_pf >= 2.0:
        print(f"  Conservative PF = {cons_pf:.2f} — ✅ EDGE HOLDS under conservative fills")
    elif cons_pf and cons_pf >= 1.5:
        print(f"  Conservative PF = {cons_pf:.2f} — ⚠️  T2 minimum holds but not T1 (PF<2)")
    elif cons_pf:
        print(f"  Conservative PF = {cons_pf:.2f} — ❌ EDGE DOES NOT HOLD under conservative fills")
    else:
        print(f"  Conservative PF = N/A (insufficient data)")

    # ── 7. Save JSON ───────────────────────────────────────────────────────────
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "source_system": source_system,
        "min_date": min_date,
        "summary": summary,
        "symbol_stats": {k: v for k, v in symbol_stats.items()},
        "not_verified_trades": categories["NOT_VERIFIED"][:20],  # first 20 for debug
        "wick_only_trades": categories["WICK_ONLY"][:20],
    }
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"ohlcv_replay_{source_system}_{today}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nJSON saved to: {out_path}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="mega_mutation")
    parser.add_argument("--min-date", default="2026-05-06")
    parser.add_argument("--output", default="reports")
    args = parser.parse_args()
    run_replay(source_system=args.source, min_date=args.min_date, output_dir=args.output)

#!/usr/bin/env python3
"""tournament_open_retro_resolve.py — honest sidecar resolution of OPEN tournament picks.

The ai-tournament leaderboard ranks models on only ~36-47 resolved picks each
while 1,275 rows (May-19→Jun-04) sit OPEN forever — the resolver that produced
WIN/LOSS statuses stopped, so every model's n is starved and the page's
NOT-MONEY-READY labels can't graduate to a real verdict either way.

SIDECAR mode by design: this tool NEVER writes the tournament_picks table. It
replays each OPEN pick with the same honest methodology as
tools/swarm/retro_resolve_swarm_archive.py (daily-bar FIRST-TOUCH walk,
SL-wins-ties + ambiguous flag, TIME_CAP at real close) and writes
audit_dashboard/data/tournament_open_retro_resolution.json with per-row
outcomes + per-model aggregates. Promoting these into the table is an operator
decision (requires backup-first UPDATE).

Resolution caveat: daily bars cannot order intra-day touches; SL-wins-ties is
conservative. MISPRICED_ENTRY-style sanity is enforced here too: entry must be
within the first bar's [low*0.5, high*2] envelope or the row is flagged
ENTRY_OFF_MARKET and excluded from aggregates.

Usage:
    python3 tools/tournament_open_retro_resolve.py            # full run
    python3 tools/tournament_open_retro_resolve.py --limit 50 # smoke
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.retro_resolve_swarm_archive import fetch_daily, resolve_ticker  # noqa: E402

OUT_PATH = REPO_ROOT / "audit_dashboard" / "data" / "tournament_open_retro_resolution.json"
CAP_DAYS_DEFAULT = 30

_FX6 = re.compile(r"^[A-Z]{6}$")


def t_ticker(symbol: str) -> str | None:
    s = (symbol or "").strip().upper()
    if _FX6.match(s) and not s.endswith(("USDT", "USDC")):
        return s + "=X"          # EURUSD -> EURUSD=X
    return resolve_ticker(s)      # crypto/bare-equity/futures/^index handling


def cap_days(timeframe: str | None, expected_hold: str | None) -> int:
    text = f"{timeframe or ''} {expected_hold or ''}".lower()
    m = re.search(r"(\d+)\s*(d|day|w|week|m|month)", text)
    if not m:
        return CAP_DAYS_DEFAULT
    n, unit = int(m.group(1)), m.group(2)[0]
    return min(120, n * {"d": 1, "w": 7, "m": 30}[unit])


def first_touch(direction, entry, tp, sl, created, cap, bars, now):
    is_long = str(direction).upper() in ("LONG", "BUY", "STRONG_BUY")
    risk = (entry - sl) if is_long else (sl - entry)
    cap_time = created + timedelta(days=cap)
    last_close = None
    first_bar = True
    for (day, high, low, close) in bars:
        if day < created.replace(hour=0, minute=0, second=0, microsecond=0):
            continue
        if first_bar:
            if not (low * 0.5 <= entry <= high * 2):
                return {"exit_reason": "ENTRY_OFF_MARKET", "pnl_pct": None}
            first_bar = False
        if day > cap_time:
            break
        last_close = close
        tp_hit = high >= tp if is_long else low <= tp
        sl_hit = low <= sl if is_long else high >= sl
        if sl_hit:
            pnl = (sl / entry - 1) * 100 if is_long else (entry / sl - 1) * 100
            return {"exit_reason": "SL_HIT", "exit_time": day.isoformat(),
                    "pnl_pct": round(pnl, 4), "ambiguous": bool(tp_hit)}
        if tp_hit:
            pnl = (tp / entry - 1) * 100 if is_long else (entry / tp - 1) * 100
            return {"exit_reason": "TP_HIT", "exit_time": day.isoformat(),
                    "pnl_pct": round(pnl, 4), "ambiguous": False}
    if now > cap_time and last_close is not None:
        pnl = (last_close / entry - 1) * 100 if is_long \
            else (entry / last_close - 1) * 100
        return {"exit_reason": "TIME_CAP", "exit_time": cap_time.isoformat(),
                "pnl_pct": round(pnl, 4), "ambiguous": False}
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    from tools.db_env import get_stocks_creds
    import pymysql
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    conn = pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep},
                           cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    q = ("SELECT id, model_id, asset_class, symbol, direction, entry_price, "
         "take_profit, stop_loss, timeframe, expected_hold, submitted_at "
         "FROM tournament_picks WHERE status='OPEN' "
         "AND entry_price>0 AND take_profit>0 AND stop_loss>0")
    if args.limit:
        q += f" LIMIT {int(args.limit)}"
    cur.execute(q)
    rows = cur.fetchall()
    conn.close()
    print(f"OPEN rows to replay: {len(rows)}")

    now = datetime.now(timezone.utc)
    series: dict[str, list | None] = {}
    for sym in sorted({r["symbol"] for r in rows}):
        tkr = t_ticker(sym)
        series[sym] = fetch_daily(tkr, now - timedelta(days=40), now) if tkr else None
    print(f"symbols: {len(series)} unique, {sum(1 for v in series.values() if v)} fetched")

    results = []
    stats = defaultdict(int)
    per_model = defaultdict(lambda: {"n": 0, "wins": 0, "losses": 0,
                                     "time_cap": 0, "sum_pnl": 0.0, "excluded": 0})
    for r in rows:
        bars = series.get(r["symbol"])
        created = r["submitted_at"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if not bars:
            stats["no_data"] += 1
            continue
        out = first_touch(r["direction"], float(r["entry_price"]),
                          float(r["take_profit"]), float(r["stop_loss"]),
                          created, cap_days(r["timeframe"], r["expected_hold"]),
                          bars, now)
        if out is None:
            stats["still_open"] += 1
            continue
        stats[out["exit_reason"]] += 1
        m = per_model[r["model_id"]]
        if out["exit_reason"] == "ENTRY_OFF_MARKET":
            m["excluded"] += 1
        else:
            m["n"] += 1
            m["sum_pnl"] += out["pnl_pct"] or 0.0
            if out["exit_reason"] == "TP_HIT":
                m["wins"] += 1
            elif out["exit_reason"] == "SL_HIT":
                m["losses"] += 1
            else:
                m["time_cap"] += 1
                if (out["pnl_pct"] or 0) > 0:
                    m["wins"] += 1
                else:
                    m["losses"] += 1
        results.append({"id": r["id"], "model_id": r["model_id"],
                        "asset_class": r["asset_class"], "symbol": r["symbol"],
                        "direction": r["direction"], **out})

    for m in per_model.values():
        denom = m["wins"] + m["losses"]
        m["wr_pct"] = round(100 * m["wins"] / denom, 1) if denom else None
        m["avg_pnl_pct"] = round(m["sum_pnl"] / m["n"], 3) if m["n"] else None
        m["sum_pnl"] = round(m["sum_pnl"], 2)

    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "method": "first_touch_daily_v1 sidecar (SL-wins-ties, TIME_CAP at close, "
                  "ENTRY_OFF_MARKET excluded). NOT written to tournament_picks — "
                  "promotion requires operator backup-first UPDATE.",
        "n_open_replayed": len(rows),
        "stats": dict(stats),
        "per_model": dict(sorted(per_model.items(),
                                 key=lambda kv: -(kv[1]["n"] or 0))),
        "rows": results,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=1, default=str))
    print(json.dumps(dict(stats), indent=1))
    top = list(payload["per_model"].items())[:12]
    for k, v in top:
        print(f"{k:24s} n={v['n']:>4} wr={str(v['wr_pct']):>6} avg={str(v['avg_pnl_pct']):>8} excl={v['excluded']}")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

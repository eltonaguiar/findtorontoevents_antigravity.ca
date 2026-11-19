"""audit3_selection_alpha.py — M1b: did we pick the right thing to hold?

The tribunal can only say whether a cell's realized return beats zero. That is
not the question that decides whether a strategy has skill. The question is:

    did the pick beat simply holding the same instrument, same direction,
    over the same window?

alpha = pick net return - direction-adjusted buy & hold over entry..exit

A +40% pick on a symbol that returned +60% is a selection FAILURE. A short that
made +3% while the symbol fell 12% gave up 9 points of the move. Neither shows
up in a win-rate table, and both are invisible when the market is drifting.

Prices come from the project's own read-only OHLC tables (crypto_ohlcv 1h,
equity/etf daily), so this needs no live vendor call.

Usage:
  python3 alpha_engine/audit3_selection_alpha.py --picks dd.json --out sa.json
Exit codes: 0 ok; 2 unusable input; 3 no price coverage.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MODULE = Path(__file__).resolve()
ROOT = MODULE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_tribunal import bootstrap_mean_ci  # noqa: E402
from alpha_engine.audit3_edge_hunt import net_pnl, issued_at, closed_at, _class, _dir  # noqa: E402

TABLE_FOR = {
    "CRYPTO": ("crypto_ohlcv", "ms"),
    "EQUITY": ("equity_daily_ohlcv", "date"),
    "ETF": ("etf_daily_ohlcv", "date"),
    "FOREX": ("fx_prices", "date"),
    "COMMODITY": ("futures_daily_ohlcv", "date"),
}
TOLERANCE_MS = {"CRYPTO": 3 * 3600_000, "EQUITY": 5 * 86400_000, "ETF": 5 * 86400_000,
                "FOREX": 5 * 86400_000, "COMMODITY": 5 * 86400_000}


def _conn():
    """Resolve credentials through tools/db_env.py, never raw env vars.

    `.env.dbpw` (DB_PASSWORDS_JSON) is canonical and the individual `DB_PASS_*`
    variables are documented as stale after the 2026-05-12 rotation; pulling them
    directly burned a host-block once. db_env.get_stocks_creds() handles the
    priority order and raises ValueError when nothing is configured.
    """
    import pymysql
    from tools.db_env import get_stocks_creds
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    creds = {k: v for k, v in get_stocks_creds().items() if k in keep}
    return pymysql.connect(read_timeout=120, **creds)


def symbol_candidates(sym: str, klass: str) -> list[str]:
    s = str(sym or "").strip().upper()
    out = [s]
    if klass == "CRYPTO":
        base = s.replace("-USD", "").replace("USD", "").replace("/", "")
        out += [f"{base}USDT", f"{base}USD", base]
    else:
        out += [s.replace(".", "-"), s.replace("-", ".")]
    seen, uniq = set(), []
    for c in out:
        if c and c not in seen:
            seen.add(c); uniq.append(c)
    return uniq


def load_bars(rows: list[dict]) -> dict[str, list[tuple[int, float]]]:
    """Fetch closes for every (class, symbol) the picks need, one query per table."""
    want: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        k = _class(r)
        if k in TABLE_FOR:
            want[k].update(symbol_candidates(r.get("symbol"), k))
    bars: dict[str, list[tuple[int, float]]] = {}
    conn = _conn()
    cur = conn.cursor()
    for klass, syms in want.items():
        table, kind = TABLE_FOR[klass]
        if not syms:
            continue
        if klass == "CRYPTO":
            cur.execute("SELECT timeframe, COUNT(*) FROM crypto_ohlcv GROUP BY 1 ORDER BY 2 DESC")
            tfs = [t for t, _ in cur.fetchall()]
            tf = "1h" if "1h" in tfs else (tfs[0] if tfs else None)
            if not tf:
                continue
            sql = ("SELECT symbol, timestamp, close FROM crypto_ohlcv "
                   "WHERE timeframe=%s AND symbol IN (" + ",".join(["%s"] * len(syms)) + ") "
                   "ORDER BY symbol, timestamp")
            cur.execute(sql, [tf] + sorted(syms))
            for sym, ts, close in cur.fetchall():
                try:
                    bars.setdefault(f"{klass}:{sym}", []).append((int(ts), float(close)))
                except (TypeError, ValueError):
                    continue
        elif klass == "FOREX":
            cur.execute("SHOW COLUMNS FROM fx_prices")
            cols = {c[0] for c in cur.fetchall()}
            tcol = "trade_date" if "trade_date" in cols else None
            ccol = "close_price" if "close_price" in cols else None
            scol = "pair" if "pair" in cols else "symbol"
            if not (tcol and ccol and scol):
                continue
            cur.execute(f"SELECT `{scol}`, `{tcol}`, `{ccol}` FROM fx_prices "
                        f"WHERE `{scol}` IN (" + ",".join(["%s"] * len(syms)) + ") "
                        f"ORDER BY `{scol}`, `{tcol}`", sorted(syms))
            for sym, d, close in cur.fetchall():
                try:
                    bars.setdefault(f"{klass}:{sym}", []).append(
                        (int(datetime.combine(d, datetime.min.time(), timezone.utc).timestamp() * 1000),
                         float(close)))
                except (TypeError, ValueError):
                    continue
        else:
            cur.execute(f"SELECT symbol, trade_date, close FROM `{table}` "
                        f"WHERE symbol IN (" + ",".join(["%s"] * len(syms)) + ") "
                        f"ORDER BY symbol, trade_date", sorted(syms))
            for sym, d, close in cur.fetchall():
                try:
                    bars.setdefault(f"{klass}:{sym}", []).append(
                        (int(datetime.combine(d, datetime.min.time(), timezone.utc).timestamp() * 1000),
                         float(close)))
                except (TypeError, ValueError):
                    continue
    conn.close()
    return bars


def _close_at(series: list[tuple[int, float]], ts_ms: int, tol_ms: int) -> float | None:
    """Close of the bar at or after ts (a fill can only happen after the signal)."""
    if not series:
        return None
    keys = [k for k, _ in series]
    i = bisect.bisect_left(keys, ts_ms)
    if i >= len(series):
        return None
    k, v = series[i]
    return v if k - ts_ms <= tol_ms else None


def alpha_for(rows: list[dict], bars: dict[str, list[tuple[int, float]]]) -> dict:
    per = []
    missing = defaultdict(int)
    for r in rows:
        klass = _class(r)
        t0, t1 = issued_at(r), closed_at(r)
        pnl = net_pnl(r)
        if t0 is None or t1 is None or pnl is None:
            missing["no_timestamp"] += 1
            continue
        series = None
        for cand in symbol_candidates(r.get("symbol"), klass):
            key = f"{klass}:{cand}"
            if key in bars and bars[key]:
                series = bars[key]
                break
        if series is None:
            missing[f"no_price:{klass}"] += 1
            continue
        tol = TOLERANCE_MS.get(klass, 5 * 86400_000)
        p0 = _close_at(series, int(t0.timestamp() * 1000), tol)
        p1 = _close_at(series, int(t1.timestamp() * 1000), tol)
        if not p0 or not p1:
            missing[f"no_bar:{klass}"] += 1
            continue
        move = (p1 / p0 - 1.0) * 100.0
        bench = move if _dir(r) == "LONG" else -move
        per.append({"row": r, "class": klass, "dir": _dir(r), "pnl": pnl,
                    "hold": bench, "alpha": pnl - bench})

    def agg(items):
        if not items:
            return {"n": 0}
        a = [x["alpha"] for x in items]
        ci = bootstrap_mean_ci(a) if len(a) >= 5 else {"ci_lo": None, "ci_hi": None}
        return {
            "n": len(items),
            "pick_net_pct": round(statistics.mean(x["pnl"] for x in items), 4),
            "hold_net_pct": round(statistics.mean(x["hold"] for x in items), 4),
            "alpha_pct": round(statistics.mean(a), 4),
            "alpha_ci": [round(ci["ci_lo"], 4) if ci["ci_lo"] is not None else None,
                         round(ci["ci_hi"], 4) if ci["ci_hi"] is not None else None],
            "alpha_wr": round(sum(1 for v in a if v > 0) / len(a), 4),
        }

    def _strat(r: dict) -> str:
        return str(r.get("strategy") or r.get("source_system") or "(unattributed)")

    by_cls = {k: agg([x for x in per if x["class"] == k]) for k in sorted({x["class"] for x in per})}
    # Only aggregate slices with enough rows to mean anything (a 1-row slice has
    # no interval and would otherwise produce a None comparison downstream).
    by_slice = {}
    for c in sorted({x["class"] for x in per}):
        for d in ("LONG", "SHORT"):
            items = [x for x in per if x["class"] == c and x["dir"] == d]
            if len(items) >= 20:
                by_slice[f"{c}/{d}"] = agg(items)
    # Strategy-level alpha, keyed exactly as the tribunal labels its cells
    # (CLASS/STRATEGY/DIRECTION). G8 needs this: a class aggregate can look like
    # skill while one strategy inside it is pure beta, and a class-only lookup
    # would let that strategy through. Same 20-row floor as by_slice — below it
    # there is no interval to compare against.
    strat_items: dict[tuple[str, str, str], list[dict]] = {}
    for x in per:
        strat_items.setdefault((x["class"], _strat(x["row"]), x["dir"]), []).append(x)
    by_strategy = {f"{c}/{s}/{d}": agg(items)
                   for (c, s, d), items in sorted(strat_items.items())
                   if len(items) >= 20}
    return {"covered": len(per), "missing": dict(missing), "overall": agg(per),
            "by_class": by_cls, "by_slice": by_slice, "by_strategy": by_strategy,
            "n_universe": len(rows)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", required=True)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    data = json.load(open(args.picks, encoding="utf-8"))
    rows = ((data.get("picks") or {}).get("recent_closed") or []) if isinstance(data, dict) else data
    rows = [r for r in rows if isinstance(r, dict) and net_pnl(r) is not None]
    if not rows:
        print("ERROR: no usable picks", file=sys.stderr); return 2
    bars = load_bars(rows)
    res = alpha_for(rows, bars)
    res["schema"] = "audit3.selection_alpha.v1"
    res["generated_at"] = datetime.now(timezone.utc).isoformat()
    res["definition"] = ("alpha = pick net return - direction-adjusted buy & hold "
                         "over the same entry..exit window (M1b)")
    if not res["covered"]:
        print(json.dumps(res, indent=1)); print("no price coverage", file=sys.stderr); return 3
    if args.out:
        json.dump(res, open(args.out, "w", encoding="utf-8"), indent=1)
    o = res["overall"]
    print(f"covered {o['n']}/{res['n_universe']} picks  missing={res['missing']}")
    print(f"pick {o['pick_net_pct']:+.3f}%  hold {o['hold_net_pct']:+.3f}%  "
          f"ALPHA {o['alpha_pct']:+.3f}%  CI={o['alpha_ci']}  alpha_wr={o['alpha_wr']:.1%}")
    for k, v in res["by_class"].items():
        if v.get("n"):
            print(f"  {k:<12} n={v['n']:<5} pick={v['pick_net_pct']:+.3f}% "
                  f"hold={v['hold_net_pct']:+.3f}% alpha={v['alpha_pct']:+.3f}% CI={v['alpha_ci']}")
    for k, v in res["by_slice"].items():
        print(f"    {k:<20} n={v['n']:<5} alpha={v['alpha_pct']:+.3f}% CI={v['alpha_ci']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

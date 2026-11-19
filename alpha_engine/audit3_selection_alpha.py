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
try:  # shared canonicaliser: BUY/L/S must not become "?"
    from alpha_engine.symbol_identity import direction_key as _dir_key
except ImportError:  # pragma: no cover
    def _dir_key(direction):
        d = str(direction or "").strip().upper()
        if d.startswith(("B", "L")):
            return "LONG"
        if d.startswith("S"):
            return "SHORT"
        return d or "UNKNOWN"
from alpha_engine.audit3_edge_hunt import net_pnl, issued_at, closed_at, _class, _dir  # noqa: E402

TABLE_FOR = {
    "CRYPTO": ("crypto_ohlcv", "ms"),
    "EQUITY": ("equity_daily_ohlcv", "date"),
    "ETF": ("etf_daily_ohlcv", "date"),
    "FOREX": ("fx_prices", "date"),
    "COMMODITY": ("futures_daily_ohlcv", "date"),
    # BOND had no entry at all, so its gate could NEVER be measured however fresh
    # the tables were (2026-11-19 backfill exposed it). Bond ETFs price in the ETF
    # table — ETF_SYMBOLS|BOND_SYMBOLS is what the backfill widened it to.
    "BOND": ("etf_daily_ohlcv", "date"),
}
TOLERANCE_MS = {"CRYPTO": 3 * 3600_000, "EQUITY": 5 * 86400_000, "ETF": 5 * 86400_000,
                "FOREX": 5 * 86400_000, "COMMODITY": 5 * 86400_000,
                "BOND": 5 * 86400_000}

# N5 (2026-11-19): selection alpha is hold-time dependent. A 1-hour pick and a
# 30-day pick are not the same claim, so the headline is reported per day and
# annualised, and a minimum-hold participation figure shows how much of the book
# actually held long enough to be comparable.
MIN_HOLD_DAYS_FOR_HEADLINE = 1.0
ANNUALIZATION_DAYS = 365.0
MIN_HOLD_DAYS_FLOOR = 1.0 / 24.0


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
        # FX and index symbols arrive as AUDJPY=X, AUD-USD or AUD/JPY while the
        # price tables store the bare AUDJPY. The old code only swapped '.' and
        # '-', so '=X' and '-' forms never matched (forex selection alpha was 0).
        bare = s.replace("=X", "").replace("-", "").replace("/", "").replace(".", "")
        out += [s.replace(".", "-"), s.replace("-", "."), bare]
    seen, uniq = set(), []
    for c in out:
        if c and c not in seen:
            seen.add(c); uniq.append(c)
    return uniq


def _wanted_symbols(rows: list[dict]) -> dict[str, set[str]]:
    """Map class -> candidate symbols the picks need (same rule load_bars uses)."""
    want: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        k = _class(r)
        if k in TABLE_FOR:
            want[k].update(symbol_candidates(r.get("symbol"), k))
    return want


def _ms_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")


def bar_coverage(bars: dict[str, list[tuple[int, float]]],
                 want: dict[str, set[str]] | None) -> dict:
    """Per-class freshness of the price tables, so ``unmeasured`` states a reason.

    "unmeasured" was ambiguous: no table for the class, the symbol absent from it,
    or the table stopping before the picks close. On 2026-11-19 it was the third
    case — equity_daily_ohlcv ended 2026-06-18 while 486 of 765 EQUITY picks closed
    after it, fx_prices ended 2026-02-09, futures_daily_ohlcv ended 2026-06-21 —
    and nothing in the sidecar said so. Only crypto_ohlcv was current.
    """
    out: dict[str, dict] = {}
    for klass, syms in (want or {}).items():
        wanted = sorted(str(x) for x in syms)
        found = [x for x in wanted if bars.get(f"{klass}:{x}")]
        lasts = [max(b[0] for b in bars[f"{klass}:{x}"]) for x in found]
        out[klass] = {
            "symbols_requested": len(wanted),
            "symbols_found": len(found),
            "missing_symbols": [x for x in wanted if x not in found][:10],
            "last_bar": _ms_to_date(max(lasts)) if lasts else None,
        }
    return out

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


def _num(v):
    """Float or None — payload fields are frequently null or strings."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def alpha_for(rows: list[dict], bars: dict[str, list[tuple[int, float]]],
              collect: bool = False) -> dict:
    per = []
    records: list[dict] = []
    missing = defaultdict(int)
    for r in rows:
        klass = _class(r)
        t0, t1 = issued_at(r), closed_at(r)
        pnl = net_pnl(r)
        if t0 is None or t1 is None or pnl is None:
            missing["no_timestamp"] += 1
            continue
        if t0 >= t1:
            # issued_at falls back to closed_at when no entry stamp exists; that
            # makes p0 == p1, move == 0 and alpha == pnl, i.e. a fabricated zero
            # benchmark that a beta-only strategy could pass G9 on.
            missing["degenerate_window"] += 1
            continue
        direction = _dir_key(r.get("direction"))
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
        bench = move if direction == "LONG" else -move
        hold_days = max((t1 - t0).total_seconds() / 86400.0, 0.0)
        per.append({"row": r, "class": klass, "dir": direction, "pnl": pnl,
                    "hold": bench, "alpha": pnl - bench, "hold_days": hold_days})
        if collect:
            # Per-pick rows exist so a *slice* can be tested, not just a class.
            # A class average hides the exit-geometry question (did TP cut
            # winners short?) and the score question (does the score sort?).
            records.append({
                "class": klass, "dir": direction,
                "symbol": str(r.get("symbol") or ""),
                "strategy": str(r.get("strategy") or ""),
                "source": str(r.get("source_system") or ""),
                "exit_reason": str(r.get("exit_reason") or r.get("exit_reason_raw") or ""),
                "timeframe": str(r.get("trade_timeframe") or ""),
                "trust_tier": str(r.get("at_issue_trust_tier") or r.get("trust_tier") or ""),
                "score": _num(r.get("score")), "elite_score": _num(r.get("elite_score")),
                "confidence": _num(r.get("confidence")),
                "rr_ratio": _num(r.get("rr_ratio")),
                "strat_fwd_wr": _num(r.get("strat_fwd_wr")),
                "pnl": round(pnl, 4), "hold": round(bench, 4),
                "alpha": round(pnl - bench, 4), "hold_days": round(hold_days, 4),
                "entry_time": t0.isoformat(), "closed_at": t1.isoformat(),
            })

    def agg(items):
        if not items:
            return {"n": 0}
        a = [x["alpha"] for x in items]
        ci = bootstrap_mean_ci(a) if len(a) >= 5 else {"ci_lo": None, "ci_hi": None}
        holds = [x["hold_days"] for x in items]
        per_day = [x["alpha"] / max(x["hold_days"], MIN_HOLD_DAYS_FLOOR)
                   for x in items]
        long_items = [x for x in items
                      if x["hold_days"] >= MIN_HOLD_DAYS_FOR_HEADLINE]
        long_alpha = (round(statistics.mean(x["alpha"] for x in long_items), 4)
                      if long_items else None)
        return {
            "n": len(items),
            "pick_net_pct": round(statistics.mean(x["pnl"] for x in items), 4),
            "hold_net_pct": round(statistics.mean(x["hold"] for x in items), 4),
            "alpha_pct": round(statistics.mean(a), 4),
            "alpha_ci": [round(ci["ci_lo"], 4) if ci["ci_lo"] is not None else None,
                         round(ci["ci_hi"], 4) if ci["ci_hi"] is not None else None],
            "alpha_wr": round(sum(1 for v in a if v > 0) / len(a), 4),
            "hold_days_mean": round(statistics.mean(holds), 4),
            "hold_days_median": round(statistics.median(holds), 4),
            "alpha_per_day_pct": round(statistics.mean(per_day), 4),
            "alpha_annualized_pct": round(statistics.mean(per_day) * ANNUALIZATION_DAYS, 4),
            "min_hold_days": MIN_HOLD_DAYS_FOR_HEADLINE,
            "n_min_hold": len(long_items),
            "min_hold_participation": round(len(long_items) / len(items), 4),
            "alpha_pct_min_hold": long_alpha,
        }

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
    # (CLASS/STRATEGY/DIRECTION). G9 needs this: a class aggregate can look like
    # skill while one strategy inside it is pure beta.
    def _strat(r: dict) -> str:
        return str(r.get("strategy") or r.get("source_system") or "(unattributed)")

    strat_items: dict[tuple[str, str, str], list[dict]] = {}
    for x in per:
        strat_items.setdefault((x["class"], _strat(x["row"]), x["dir"]), []).append(x)
    by_strategy = {f"{c}/{st}/{d}": agg(items)
                   for (c, st, d), items in sorted(strat_items.items())
                   if len(items) >= 20}
    out = {"covered": len(per), "missing": dict(missing), "overall": agg(per),
           "by_class": by_cls, "by_slice": by_slice, "by_strategy": by_strategy,
           "n_universe": len(rows)}
    if collect:
        out["records"] = records
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", required=True)
    ap.add_argument("--out")
    ap.add_argument("--rows-out", dest="rows_out",
                    help="write one JSON line per covered pick (for slice scans)")
    args = ap.parse_args(argv)
    data = json.load(open(args.picks, encoding="utf-8"))
    rows = ((data.get("picks") or {}).get("recent_closed") or []) if isinstance(data, dict) else data
    rows = [r for r in rows if isinstance(r, dict) and net_pnl(r) is not None]
    if not rows:
        print("ERROR: no usable picks", file=sys.stderr); return 2
    bars = load_bars(rows)
    res = alpha_for(rows, bars, collect=bool(args.rows_out))
    # Diagnose "unmeasured": no table, missing symbol, or stale bars.
    res["bar_coverage"] = bar_coverage(bars, _wanted_symbols(rows))
    recs = res.pop("records", [])
    res["schema"] = "audit3.selection_alpha.v1"
    res["generated_at"] = datetime.now(timezone.utc).isoformat()
    res["definition"] = ("alpha = pick net return - direction-adjusted buy & hold "
                         "over the same entry..exit window (M1b); alpha_per_day_pct "
                         "and alpha_annualized_pct normalise by hold time, and "
                         "min_hold_participation reports the share of trades held "
                         f">= {MIN_HOLD_DAYS_FOR_HEADLINE:.0f} day(s)")
    if not res["covered"]:
        print(json.dumps(res, indent=1)); print("no price coverage", file=sys.stderr); return 3
    if args.rows_out:
        with open(args.rows_out, "w", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, default=str) + "\n")
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

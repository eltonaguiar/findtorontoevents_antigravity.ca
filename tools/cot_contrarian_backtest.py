#!/usr/bin/env python3
"""CFTC COT contrarian test — COMMODITY, weekly, pre-registered.

Hypothesis (registered 2026-11-14 in final_v2/quant-audit-2026-11-14/03_ideas_ranked,
before this file existed — quoted verbatim):

    Idea 6 — COMMODITY: CFTC COT contrarian at weekly frequency
    Do:    weekly rebalance on COT extremes, hold 1-4 weeks, costs at 10bp.
    Gate:  OOS PF >= 1.15 on n>=100 trades, slippage <25% of average PnL,
           and beat an equal-weight commodity benchmark (not zero).

Signal definition, fixed here and not tuned afterwards:
    Fade the speculator extremes. Non-commercials are trend followers and are
    stretched at multi-year positioning extremes; commercial hedgers are the
    other side. On commercial net as a % of open interest:
        z >= +Z  (commercials extremely long)  -> LONG
        z <= -Z  (commercials extremely short) -> SHORT
    z is a trailing z-score over the PRIOR `Z_WINDOW` reports only, so the
    signal never sees the report it is trading.

Timing guard:
    COT is as-of Tuesday and published Friday ~15:30 ET. Entry is the first
    daily bar on/after report_date + 6 days (the following Monday). Nothing in
    this file reads a bar dated before that, so the report cannot leak into
    the entry price.

Anti-snooping:
    Z in {1.5, 2.0, 2.5} and hold in {1, 2, 4} weeks are selected on the
    IN-SAMPLE window only (first 60% of report dates). The selected pair is
    then applied once to the out-of-sample window (last 40%) and the gate is
    evaluated there. The inverse (momentum) direction is reported as a
    diagnostic so a sign error cannot masquerade as edge.

Data:
    COT      ejaguiar1_stocks.cftc_cot_weekly (2,849 rows / 11 markets / 2021-06+)
    Prices   yfinance daily for the matching continuous futures (=F)

Usage:
    python3 tools/cot_contrarian_backtest.py                 # full run + gate
    python3 tools/cot_contrarian_backtest.py --json reports/cot_contrarian.json
    python3 tools/cot_contrarian_backtest.py --hold-all      # report all 9 combos
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# CFTC market code -> yfinance continuous contract
YF_MAP: Dict[str, str] = {
    "CT": "CT=F",  # cotton
    "PA": "PA=F",  # palladium
    "PL": "PL=F",  # platinum
    "ZC": "ZC=F",  # corn
    "ZW": "ZW=F",  # wheat SRW
    "HG": "HG=F",  # copper
    "SI": "SI=F",  # silver
    "CL": "CL=F",  # WTI crude
    "NG": "NG=F",  # natural gas
    "ZS": "ZS=F",  # soybeans
    "GC": "GC=F",  # gold
}

Z_WINDOW = 156          # 3 years of weekly reports for the z-score
Z_CHOICES = (1.5, 2.0, 2.5)
HOLD_CHOICES = (1, 2, 4)  # weeks
IS_FRACTION = 0.60      # first 60% of report dates = in-sample
COST_BPS = 10.0         # pre-registered cost for this test
COST_SENSITIVITY_BPS = 15.0  # transaction_costs.json says 15bp for COMMODITY
ENTRY_LAG_DAYS = 6      # Tuesday as-of + Friday publish -> Monday entry
GATE_OOS_PF = 1.15
GATE_MIN_TRADES = 100
GATE_MAX_SLIPPAGE_SHARE = 0.25


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------
def trailing_zscores(values: Sequence[Optional[float]], window: int = Z_WINDOW) -> List[Optional[float]]:
    """Z-score of each value against the PRIOR ``window`` values (exclusive).

    Returns None until at least 30 prior observations exist. Excluding the
    current value is what keeps the signal free of look-ahead: the report being
    traded is not part of its own baseline.
    """
    out: List[Optional[float]] = []
    for i, v in enumerate(values):
        prior = [x for x in values[max(0, i - window):i] if x is not None]
        if v is None or len(prior) < 30:
            out.append(None)
            continue
        mu = sum(prior) / len(prior)
        var = sum((x - mu) ** 2 for x in prior) / (len(prior) - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        out.append(None if sd == 0 else (v - mu) / sd)
    return out


def profit_factor(returns: Iterable[float]) -> Optional[float]:
    """Gross wins / gross losses on a list of fractional returns. None if no losses."""
    rs = list(returns)
    wins = sum(r for r in rs if r > 0)
    losses = -sum(r for r in rs if r < 0)
    if losses <= 0:
        return None if wins <= 0 else float("inf")
    return wins / losses


def entry_index_for(bar_dates: Sequence[date], report_date: date, lag_days: int = ENTRY_LAG_DAYS) -> Optional[int]:
    """First bar index on/after report_date + lag_days (no pre-publication bar)."""
    target = report_date + timedelta(days=lag_days)
    for i, d in enumerate(bar_dates):
        if d >= target:
            return i
    return None


def evaluate_gate(
    oos_returns: Sequence[float],
    oos_benchmark_mean: Optional[float],
    cost_bps: float = COST_BPS,
) -> Dict[str, Any]:
    """Apply the pre-registered gate to the OOS trades. No parameters tuned here."""
    n = len(oos_returns)
    pf = profit_factor(oos_returns)
    mean = (sum(oos_returns) / n) if n else None
    gross_returns = [r + cost_bps / 10_000.0 for r in oos_returns]
    gross_mean = (sum(gross_returns) / n) if n else None
    # Slippage share = modelled round-trip cost as a fraction of average GROSS PnL.
    slip_share = (
        (cost_bps / 10_000.0) / gross_mean
        if gross_mean and gross_mean > 0
        else None
    )
    checks = {
        "n_ge_100": n >= GATE_MIN_TRADES,
        "pf_ge_1.15": bool(pf is not None and pf >= GATE_OOS_PF),
        "slippage_lt_25pct": bool(slip_share is not None and slip_share < GATE_MAX_SLIPPAGE_SHARE),
        "beats_benchmark": bool(
            mean is not None and oos_benchmark_mean is not None and mean > oos_benchmark_mean
        ),
    }
    return {
        "n": n,
        "pf": pf,
        "mean_net_per_trade": mean,
        "mean_gross_per_trade": gross_mean,
        "slippage_share_of_gross": slip_share,
        "oos_benchmark_mean": oos_benchmark_mean,
        "checks": checks,
        "passes_gate": all(checks.values()),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_cot(symbols: Optional[Sequence[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Weekly COT rows per symbol, ascending by report_date.

    comm_net_pct_of_oi is preferred; when the DB value is NULL it is derived
    from comm_net / open_interest so no symbol silently drops out.
    """
    import pymysql
    from tools.db_env import get_stocks_creds

    c = get_stocks_creds()
    conn = pymysql.connect(
        host=c["host"], port=int(c["port"]), user=c["user"], password=c["password"],
        database=c["database"], charset="utf8mb4", connect_timeout=15,
    )
    want = list(symbols or YF_MAP.keys())
    placeholders = ",".join(["%s"] * len(want))
    sql = (
        "SELECT symbol, report_date, comm_net, comm_net_pct_of_oi, open_interest "
        f"FROM cftc_cot_weekly WHERE symbol IN ({placeholders}) ORDER BY symbol, report_date"
    )
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, want)
            for sym, rd, comm_net, pct, oi in cur.fetchall():
                pct_f = float(pct) if pct is not None else None
                if pct_f is None and comm_net is not None and oi:
                    pct_f = float(comm_net) / float(oi) * 100.0
                if pct_f is None:
                    continue
                out[str(sym)].append(
                    {"report_date": rd, "comm_net_pct_oi": pct_f, "comm_net": comm_net, "oi": oi}
                )
    finally:
        conn.close()
    return dict(out)


def load_prices(symbols: Sequence[str], start: str = "2021-01-01") -> Dict[str, Dict[str, Any]]:
    """Daily bars per symbol: {yf_ticker: {"dates": [date], "close": [float]}}."""
    import yfinance as yf

    out: Dict[str, Dict[str, Any]] = {}
    for cf in symbols:
        ticker = YF_MAP.get(cf)
        if not ticker:
            continue
        try:
            df = yf.Ticker(ticker).history(start=start, interval="1d", auto_adjust=False)
        except Exception as e:  # noqa: BLE001
            print(f"  price fetch failed {ticker}: {type(e).__name__} {e}", file=sys.stderr)
            continue
        if df is None or df.empty:
            print(f"  no bars for {ticker}", file=sys.stderr)
            continue
        dates: List[date] = []
        closes: List[float] = []
        for idx, row in df.iterrows():
            try:
                d = idx.date() if hasattr(idx, "date") else None
                close = float(row["Close"])
            except (TypeError, ValueError, KeyError):
                continue
            if d is None or not close or close != close:
                continue
            dates.append(d)
            closes.append(close)
        if dates:
            out[cf] = {"dates": dates, "close": closes}
    return out


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def build_trades(
    cot: Dict[str, List[Dict[str, Any]]],
    prices: Dict[str, Dict[str, Any]],
    z_ext: float,
    hold_weeks: int,
    invert: bool = False,
) -> List[Dict[str, Any]]:
    """One trade per (symbol, report) whose trailing z crosses +/-z_ext."""
    trades: List[Dict[str, Any]] = []
    hold_bars = 5 * hold_weeks
    cost = COST_BPS / 10_000.0

    for sym, rows in cot.items():
        px = prices.get(sym)
        if not px:
            continue
        vals = [r["comm_net_pct_oi"] for r in rows]
        zs = trailing_zscores(vals)
        dates = px["dates"]
        closes = px["close"]

        for row, z in zip(rows, zs):
            if z is None or abs(z) < z_ext:
                continue
            # Commercials extremely long -> LONG; extremely short -> SHORT.
            direction = 1 if z > 0 else -1
            if invert:
                direction = -direction
            entry_i = entry_index_for(dates, row["report_date"])
            if entry_i is None:
                continue
            exit_i = entry_i + hold_bars
            if exit_i >= len(closes):
                continue
            entry_px, exit_px = closes[entry_i], closes[exit_i]
            if not entry_px or entry_px <= 0:
                continue
            gross = direction * (exit_px - entry_px) / entry_px
            trades.append(
                {
                    "symbol": sym,
                    "report_date": row["report_date"].isoformat(),
                    "z": round(z, 4),
                    "direction": "LONG" if direction > 0 else "SHORT",
                    "entry_date": dates[entry_i].isoformat(),
                    "exit_date": dates[exit_i].isoformat(),
                    "gross_return": gross,
                    "net_return": gross - cost,
                }
            )
    trades.sort(key=lambda t: (t["report_date"], t["symbol"]))
    return trades


def split_dates(cot: Dict[str, List[Dict[str, Any]]], is_fraction: float = IS_FRACTION) -> Optional[date]:
    """Cutoff date splitting report dates into in-sample (<=) and OOS (>)."""
    all_dates = sorted({r["report_date"] for rows in cot.values() for r in rows})
    if len(all_dates) < 100:
        return None
    cut = int(len(all_dates) * is_fraction)
    return all_dates[min(cut, len(all_dates) - 1)]


def benchmark_mean_return(
    prices: Dict[str, Dict[str, Any]], oos_start: date, hold_weeks: int
) -> Optional[float]:
    """Equal-weight buy-and-hold mean per ``hold_weeks`` over the OOS window.

    This is the benchmark the gate names: the same instruments, same holding
    period, no timing skill. Beating zero is not enough.
    """
    rets: List[float] = []
    hold_bars = 5 * hold_weeks
    for sym, px in prices.items():
        dates, closes = px["dates"], px["close"]
        i = 0
        while i + hold_bars < len(closes):
            if dates[i] >= oos_start:
                if closes[i] > 0:
                    rets.append((closes[i + hold_bars] - closes[i]) / closes[i] - COST_BPS / 10_000.0)
                i += hold_bars
            else:
                i += 1
    return (sum(rets) / len(rets)) if rets else None


def run(cot: Dict[str, List[Dict[str, Any]]], prices: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Select on IS, confirm on OOS, evaluate the gate once."""
    cut = split_dates(cot)
    if cut is None:
        return {"error": "not enough COT history", "n": 0}

    grid: List[Dict[str, Any]] = []
    for z_ext in Z_CHOICES:
        for hold in HOLD_CHOICES:
            trades = build_trades(cot, prices, z_ext, hold)
            is_r = [t["net_return"] for t in trades if date.fromisoformat(t["report_date"]) <= cut]
            oos_r = [t["net_return"] for t in trades if date.fromisoformat(t["report_date"]) > cut]
            grid.append(
                {
                    "z_ext": z_ext,
                    "hold_weeks": hold,
                    "n_total": len(trades),
                    "n_is": len(is_r),
                    "n_oos": len(oos_r),
                    "is_pf": profit_factor(is_r),
                    "is_mean_net": (sum(is_r) / len(is_r)) if is_r else None,
                    "trades": trades,
                }
            )

    # Selection happens on IN-SAMPLE only: max IS PF with n_is >= 30.
    eligible = [g for g in grid if g["n_is"] >= 30 and g["is_pf"] is not None]
    if not eligible:
        return {"error": "no in-sample eligible parameter set", "cut": cut.isoformat(), "grid_summary": []}
    chosen = max(eligible, key=lambda g: g["is_pf"])

    oos_trades = [t for t in chosen["trades"] if date.fromisoformat(t["report_date"]) > cut]
    oos_returns = [t["net_return"] for t in oos_trades]
    bench = benchmark_mean_return(prices, cut, chosen["hold_weeks"])
    gate = evaluate_gate(oos_returns, bench)

    inv_trades = build_trades(cot, prices, chosen["z_ext"], chosen["hold_weeks"], invert=True)
    inv_oos = [t["net_return"] for t in inv_trades if date.fromisoformat(t["report_date"]) > cut]

    # Sensitivity: the same chosen params at the DB's 15bp commodity cost.
    oos_15 = [r - (COST_SENSITIVITY_BPS - COST_BPS) / 10_000.0 for r in oos_returns]

    return {
        "cut": cut.isoformat(),
        "chosen": {
            "z_ext": chosen["z_ext"],
            "hold_weeks": chosen["hold_weeks"],
            "n_is": chosen["n_is"],
            "n_oos": chosen["n_oos"],
            "is_pf": chosen["is_pf"],
            "n_total": chosen["n_total"],
        },
        "gate": gate,
        "gate_at_15bp": {
            "n": len(oos_15),
            "pf": profit_factor(oos_15),
            "mean_net_per_trade": (sum(oos_15) / len(oos_15)) if oos_15 else None,
        },
        "inverse_diagnostic": {
            "n_oos": len(inv_oos),
            "pf_oos": profit_factor(inv_oos),
            "mean_net_oos": (sum(inv_oos) / len(inv_oos)) if inv_oos else None,
        },
        "grid_summary": [
            {
                "z_ext": g["z_ext"],
                "hold_weeks": g["hold_weeks"],
                "n_is": g["n_is"],
                "n_oos": g["n_oos"],
                "is_pf": g["is_pf"],
                "is_mean_net": g["is_mean_net"],
            }
            for g in grid
        ],
        "symbols": sorted(cot.keys()),
        "n_cot_rows": sum(len(v) for v in cot.values()),
        "oos_trades_sample": oos_trades[:10],
    }


def _print(result: Dict[str, Any]) -> None:
    if result.get("error"):
        print(f"ERROR: {result['error']}")
        if result.get("cut"):
            print(f"  IS/OOS cut: {result['cut']}")
        return
    c, g = result["chosen"], result["gate"]
    print(f"COT rows: {result['n_cot_rows']:>5} across {len(result['symbols'])} markets")
    print(f"IS/OOS cut: {result['cut']}")
    print(f"\nselected on IS only: z>={c['z_ext']}, hold={c['hold_weeks']}w  "
          f"(IS n={c['n_is']}, IS PF={c['is_pf']:.3f})")
    print(f"\nOOS result: n={g['n']}  PF={g['pf'] if g['pf'] is None else round(g['pf'],3)}  "
          f"mean net/trade={g['mean_net_per_trade']}")
    print(f"  slippage share of gross PnL: {g['slippage_share_of_gross']}")
    print(f"  equal-weight benchmark mean: {g['oos_benchmark_mean']}")
    print("\ngate checks (pre-registered 2026-11-14):")
    for k, v in g["checks"].items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"\nGATE: {'PASS' if g['passes_gate'] else 'FAIL'}")
    inv = result["inverse_diagnostic"]
    print(f"\ndiagnostic — inverse (momentum) direction: n={inv['n_oos']} "
          f"PF={inv['pf_oos'] if inv['pf_oos'] is None else round(inv['pf_oos'],3)} "
          f"mean={inv['mean_net_oos']}")
    print("\nin-sample grid (selection table — OOS was not consulted for this):")
    for row in result["grid_summary"]:
        pf = row["is_pf"]
        print(f"  z>={row['z_ext']:<4} hold={row['hold_weeks']}w  IS n={row['n_is']:>4} "
              f"PF={'  n/a' if pf is None else f'{pf:6.3f}'}  OOS n={row['n_oos']:>4}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="write full result JSON here")
    ap.add_argument("--hold-all", action="store_true", help="(grid is always reported)")
    ap.add_argument("--symbols", nargs="*", help="restrict to these CFTC codes")
    args = ap.parse_args(argv)

    syms = args.symbols or list(YF_MAP.keys())
    print(f"loading COT for {len(syms)} markets...")
    cot = load_cot(syms)
    print(f"  {sum(len(v) for v in cot.values())} weekly rows")
    print("loading daily futures prices...")
    prices = load_prices(list(cot.keys()))
    print(f"  {len(prices)} price series")
    if not cot or not prices:
        print("missing data — aborting", file=sys.stderr)
        return 2

    result = run(cot, prices)
    result["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result["cost_bps"] = COST_BPS
    _print(result)

    if args.json:
        p = Path(args.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True, default=str)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

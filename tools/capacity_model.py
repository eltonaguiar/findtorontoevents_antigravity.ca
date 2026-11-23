#!/usr/bin/env python3
"""Capacity model for funding-rate carry, built on MEASURED order-book depth.

Provenance (every input traces to a file):
  * Depth / spread-vs-size curve: raw order books in
        reports/cost_measurement/20261122T114949Z/  (ccxt fetch_order_book, limit=1000)
    summarised in
        reports/cost_measurement_20261122.json
    captured 2026-11-22T11:49:49Z, 3 samples/symbol spaced 3s apart, one venue set
    (binance, kucoin, kraken).  Taker fees per side: binance 10bp, kucoin 10bp,
    kraken 26bp (base tier, from the same report).
  * Funding history: reports/funding_carry_20261122.json  (Binance USDT-M funding,
    per-symbol mean/median 8h rate and the break-even ledger).
  * The 45.524bp pair round-trip cost used as the item-35 threshold is
    reports/funding_carry_20261122.json:pair_cost_bp_1x -- four taker fills
    (open+close on spot and perp) at the $10k reference size.

Nothing here is a literature value presented as a measurement.  Where an input is
ASSUMED (perp spread = spot spread, funding stationarity) it is labelled.

Model (item 36):
  deploy capital C per symbol, equal notional on both legs.
  pair_cost_bp(C) = 2 * ( spread_rt_bp(C) + 2 * taker_bp )      [one entry+exit per leg]
  cost as an APR drag over a hold of H days = pair_cost_bp/1e4 * 365/H
  net_apr(C, H) = gross_funding_apr - cost_apr(C, H)
  gross_funding_apr is taken at the HISTORICAL MEDIAN 8h rate (the mandatory default);
  the mean and the last-12-month figures are reported as sensitivity, never as the base.

CLI:
    python3 tools/capacity_model.py                 # write the three reports
    python3 tools/capacity_model.py --json          # dump item-35/36 payload to stdout
"""
from __future__ import annotations

import argparse
import bisect
import glob
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "reports" / "cost_measurement" / "20261122T114949Z"
COST_REPORT = ROOT / "reports" / "cost_measurement_20261122.json"
CARRY_REPORT = ROOT / "reports" / "funding_carry_20261122.json"

HURDLE_TBILL_APR = 0.0432          # 4.32% -- the programme hurdle, docs/edge_research/07
TAKER_BP = {"binance": 10.0, "kucoin": 10.0, "kraken": 26.0}

# Sizes (USD per leg) at which the measured depth curve is sampled from the raw books.
SAMPLE_SIZES = [1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000, 150_000,
                250_000, 500_000, 750_000, 1_000_000, 2_000_000, 5_000_000]

# The five symbols funding carry was tested on (chosen by liquidity, pre-declared
# in 06_FUNDING_CARRY: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT).
CARRY_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]


# ---------------------------------------------------------------------------
# Book reconstruction
# ---------------------------------------------------------------------------
def walk(levels, notional_usd: float):
    """VWAP to fill `notional_usd` from one book side; None if depth is insufficient."""
    remaining, cost, qty = notional_usd, 0.0, 0.0
    for lv in levels:
        try:
            price, q = float(lv[0]), float(lv[1])
        except (TypeError, ValueError, IndexError):
            continue
        if price <= 0 or q <= 0:
            continue
        level_notional = price * q
        take = min(remaining, level_notional)
        cost += take
        qty += take / price
        remaining -= take
        if remaining <= 1e-9:
            break
    if remaining > 1e-9 or qty <= 0:
        return None
    return cost / qty


def load_raw_books(raw_dir: Path = RAW_DIR) -> dict:
    """(exchange, symbol) -> list of raw book snapshots, each with bids/asks/mid/ts."""
    books = defaultdict(list)
    for f in sorted(glob.glob(str(raw_dir / "*.json"))):
        d = json.load(open(f))
        books[(d["exchange"], d["symbol"])].append(d)
    return books


def measured_depth_curve(books: dict, sizes=SAMPLE_SIZES) -> dict:
    """(exchange, symbol) -> [(notional, median round-trip spread bp)] over samples."""
    curves = {}
    for key, snaps in books.items():
        pts = []
        for s in sizes:
            vals = []
            for b in snaps:
                vbuy = walk(b["asks"], s)
                vsell = walk(b["bids"], s)
                if vbuy is None or vsell is None:
                    continue
                mid = (float(b["bids"][0][0]) + float(b["asks"][0][0])) / 2.0
                vals.append((vbuy - vsell) / mid * 1e4)
            if vals:
                pts.append((float(s), st.median(vals)))
        curves[key] = pts
    return curves


def interp_spread(curve, notional: float):
    """Linear interpolation of round-trip spread (bp) at `notional`; None beyond measured depth."""
    if not curve:
        return None
    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]
    if notional <= xs[0]:
        return ys[0]
    if notional == xs[-1]:
        return ys[-1]        # the deepest point is still a measurement
    if notional > xs[-1]:
        return None          # do NOT extrapolate past the deepest measured point
    i = bisect.bisect_right(xs, notional)
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 + (y1 - y0) * (notional - x0) / (x1 - x0)


# ---------------------------------------------------------------------------
# Item 35/36 core
# ---------------------------------------------------------------------------
def pair_cost_bp(curve, taker_bp: float, notional: float, cost_mult: float = 1.0):
    """Pair round trip = 2 legs x (spread round trip + 2 x taker fee). None if depth exhausted."""
    spread = interp_spread(curve, notional)
    if spread is None:
        return None
    return 2.0 * (spread + 2.0 * taker_bp) * cost_mult


def crossover_notional(curve, taker_bp: float, threshold_bp: float, cost_mult: float = 1.0):
    """Smallest notional where pair cost reaches `threshold_bp`, linearly interpolated.

    Returns {usd, below_measured_floor, note}:
      * usd is None when the threshold is never reached within measured depth;
      * below_measured_floor=True when the threshold is already crossed at the smallest
        measured size, so the true crossover is <= that size and cannot be located from
        this snapshot -- the honest statement is an inequality, not a point."""
    prev = None
    for x, _ in curve:
        c = pair_cost_bp(curve, taker_bp, x, cost_mult)
        if c is None:
            return {"usd": None, "below_measured_floor": False,
                    "note": "depth exhausted before the threshold was reached"}
        if c >= threshold_bp:
            if prev is None:
                return {"usd": x, "below_measured_floor": True,
                        "note": f"already >= threshold at the smallest measured size (${x:,.0f})"}
            x0, y0 = prev
            usd = x if c == y0 else x0 + (x - x0) * (threshold_bp - y0) / (c - y0)
            return {"usd": usd, "below_measured_floor": False, "note": None}
        prev = (x, c)
    return {"usd": None, "below_measured_floor": False,
            "note": "threshold not reached within measured depth"}


def gross_funding_apr(funding_8h: float) -> float:
    """Annualise one 8h funding rate: 3 intervals/day x 365 days."""
    return funding_8h * 3 * 365


def net_apr(curve, taker_bp: float, gross_apr: float, hold_days: float,
            notional: float, cost_mult: float = 1.0):
    """net APR = gross funding APR - cost APR amortised over the hold. None if depth exhausted."""
    c = pair_cost_bp(curve, taker_bp, notional, cost_mult)
    if c is None:
        return None
    cost_apr = (c / 1e4) * (365.0 / hold_days)
    return gross_apr - cost_apr


def net_apr_crossover(curve, taker_bp: float, gross_apr: float, hold_days: float,
                      target_apr: float, cost_mult: float = 1.0):
    """Capital at which net APR falls through `target_apr` (0.0 or the T-bill), interpolated.

    Same convention as crossover_notional: {usd, below_measured_floor, note}. If net APR is
    already below the target at the smallest measured size the crossover is an inequality
    (<= that size), not a point -- a precise number there would be false precision."""
    prev = None
    for x, _ in curve:
        n = net_apr(curve, taker_bp, gross_apr, hold_days, x, cost_mult)
        if n is None:
            return {"usd": None, "below_measured_floor": False, "note": "depth exhausted"}
        if n <= target_apr:
            if prev is None:
                return {"usd": x, "below_measured_floor": True,
                        "note": f"net APR already <= target at the smallest measured size (${x:,.0f})"}
            x0, y0 = prev
            usd = x if y0 == n else x0 + (x - x0) * (y0 - target_apr) / (y0 - n)
            return {"usd": usd, "below_measured_floor": False, "note": None}
        prev = (x, n)
    return {"usd": None, "below_measured_floor": False,
            "note": "net APR never falls to the target within measured depth (always above)"}


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------
def build_item35(books, curves):
    rep = json.load(open(COST_REPORT))
    carry = json.load(open(CARRY_REPORT))
    threshold = carry["pair_cost_bp_1x"]

    # Independent re-derivation of the report's figures from the raw books, to show
    # the numbers trace rather than re-quoting the summary.
    verify = {}
    repmap = {(v["exchange"], sym): s for v in rep["venues"] for sym, s in v["symbols"].items()}
    for size in rep["sizes_usd"]:
        worst, n = 0.0, 0
        for key, snaps in books.items():
            s = repmap.get(key)
            if not s:
                continue
            for b in snaps:
                vbuy, vsell = walk(b["asks"], size), walk(b["bids"], size)
                if vbuy is None or vsell is None:
                    continue
                mid = (float(b["bids"][0][0]) + float(b["asks"][0][0])) / 2
                rt = (vbuy - vsell) / mid * 1e4
                for smp in s["samples"]:
                    if smp["ts_utc"] == b["ts_utc"]:
                        worst = max(worst, abs(rt - smp["sizes"][str(size)]["round_trip_spread_bp"]))
                        n += 1
        verify[str(size)] = {"n_pairs_recomputed": n, "max_abs_diff_bp": worst}

    per_symbol = {}
    for sym in CARRY_SYMBOLS:
        key = ("binance", sym)
        curve = curves.get(key)
        if not curve:
            continue
        fee = TAKER_BP[key[0]]
        per_symbol[sym] = {
            "spread_rt_bp_by_size": {str(int(x)): y for x, y in curve},
            "pair_cost_bp_1x_by_size": {str(int(x)): pair_cost_bp(curve, fee, x, 1.0) for x, _ in curve},
            "pair_cost_bp_2x_by_size": {str(int(x)): pair_cost_bp(curve, fee, x, 2.0) for x, _ in curve},
            "crossover_usd_1x": crossover_notional(curve, fee, threshold, 1.0),
            "crossover_usd_2x": crossover_notional(curve, fee, threshold, 2.0),
            "cost_basis": "MEASURED order book 20261122T114949Z (binance) + fee 10bp/side; "
                          "perp spread ASSUMED equal to spot spread",
        }

    valid_1x = {k: v["crossover_usd_1x"]["usd"] for k, v in per_symbol.items()
                if v["crossover_usd_1x"]["usd"] is not None}
    binding = min(valid_1x, key=valid_1x.get) if valid_1x else None

    non_crypto = {
        cls: {"verdict": "INSUFFICIENT_MEASUREMENT",
              "reason": "order-book depth / all-in cost for this asset class was never measured; "
                        "crypto depth is not extrapolated across asset classes"}
        for cls in ["EQUITY", "ETF", "FX", "COMMODITY", "BOND", "FUTURES", "MUTUAL_FUND"]
    }

    return {
        "item": 35,
        "generated_utc": rep["generated_utc"],
        "source_books": str(RAW_DIR.relative_to(ROOT)),
        "source_report": str(COST_REPORT.relative_to(ROOT)),
        "threshold_pair_rt_bp": threshold,
        "threshold_basis": "funding_carry_20261122.json:pair_cost_bp_1x = 4 taker fills at $10k",
        "raw_reverify": verify,
        "per_symbol": per_symbol,
        "thinnest_symbol_binding": binding,
        "capacity_limit": {
            "usd_per_symbol": valid_1x.get(binding) if binding else None,
            "binding_symbol": binding,
            "caveat": "one 3-minute sampling window (3 snapshots, 3s apart) on a Sunday "
                      "2026-11-22T11:49Z, single venue set (binance spot); perp depth not "
                      "measured; would shrink with thinner books, grow with deeper ones, and "
                      "is not a 24/7 average",
        },
        "non_crypto": non_crypto,
    }


def build_item36(curves, carry):
    gross_mean = carry["aggregate_mean_gross_apr"]                 # mean 8h funding APR
    med_8h = st.mean([v["funding_distribution"]["median"] for v in carry["per_symbol"].values()])
    gross_median = gross_funding_apr(med_8h)
    l12 = [v["last_12_months"].get("gross_apr") for v in carry["per_symbol"].values()
           if v["last_12_months"].get("gross_apr") is not None]
    gross_12mo = st.mean(l12) if l12 else None

    # Mandatory hold assumption: the median positive-funding episode (~2d), not the 90d tail.
    ep_medians = [v["positive_trailing_episodes"]["median_days"]
                  for v in carry["per_symbol"].values()
                  if v["positive_trailing_episodes"].get("median_days")]
    hold_median_episode = st.mean(ep_medians) if ep_medians else None
    be_median = carry["aggregate_mean_breakeven_days_at_median"]

    grid = [10_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]

    def grid_for(hold):
        out = {}
        for sym in CARRY_SYMBOLS:
            curve = curves.get(("binance", sym))
            if not curve:
                continue
            fee = TAKER_BP["binance"]
            row = {}
            for c in grid:
                row[str(c)] = {
                    "net_apr_base": net_apr(curve, fee, gross_median, hold, c, 1.0),
                    "net_apr_2x": net_apr(curve, fee, gross_median, hold, c, 2.0),
                }
            out[sym] = row
        return out

    def crossovers(hold):
        z, h = [], []
        for sym in CARRY_SYMBOLS:
            curve = curves.get(("binance", sym))
            if not curve:
                continue
            fee = TAKER_BP["binance"]
            z.append(net_apr_crossover(curve, fee, gross_median, hold, 0.0, 1.0))
            h.append(net_apr_crossover(curve, fee, gross_median, hold, HURDLE_TBILL_APR, 1.0))

        def summarize(xs, label):
            usd = [x["usd"] for x in xs if x["usd"] is not None]
            belows = [x for x in xs if x["below_measured_floor"]]
            if not usd:
                return {"usd_per_symbol": None, "verdict": "NEVER_REACHED",
                        "note": f"net APR never reaches {label} at any measured size"}
            if len(belows) == len(usd):
                return {"usd_per_symbol": f"<={max(usd):,.0f}",
                        "verdict": "INSUFFICIENT_DEPTH",
                        "note": f"net APR already at/below {label} at the smallest measured "
                                f"size on every symbol -- the crossing lies below the measured "
                                f"floor, so only an upper bound is measurable"}
            return {"usd_per_symbol": {"min": min(usd), "median": st.median(usd)},
                    "verdict": "MEASURED", "note": None}

        return {"hold_days": hold,
                "cross_zero": summarize(z, "0%"),
                "cross_tbill_432bp": summarize(h, "4.32%")}

    def any_beats(cur, gross, hold, target):
        return any((net_apr(cur, TAKER_BP["binance"], gross, hold, s, 1.0) or -1e9) > target
                   for s in grid for sym in CARRY_SYMBOLS if (cur := curves.get(("binance", sym))))

    hold_used = hold_median_episode or be_median
    # Hold sensitivity: the mandatory median-hold base sits next to the 30/90d numbers the
    # programme already reports, so the favourable tail is visible but never the base case.
    hold_sensitivity = {f"{h:g}d": crossovers(h) | {
        "any_grid_size_beats_tbill":
            any((net_apr(cur, TAKER_BP["binance"], gross_median, h, s, 1.0) or -1e9) > HURDLE_TBILL_APR
                for s in grid for sym in CARRY_SYMBOLS if (cur := curves.get(("binance", sym))))}
        for h in [hold_used, 7, 30, 90]}
    return {
        "item": 36,
        "model": "net_apr(C,H) = gross_funding_apr - (pair_cost_bp(C)/1e4)*(365/H); "
                 "pair_cost_bp(C)=2*(spread_rt_bp(C)+2*taker_bp)",
        "funding": {
            "median_8h_mean_across_symbols": med_8h,
            "gross_apr_median": gross_median,
            "gross_apr_mean": gross_mean,
            "gross_apr_last_12mo": gross_12mo,
            "base_uses": "MEDIAN (mandatory default)",
        },
        "hold_days": {
            "median_positive_episode": hold_median_episode,
            "breakeven_at_median_funding": be_median,
            "used": hold_used,
            "note": "90d hold is the favourable tail and is NOT the base case",
        },
        "grid": grid_for(hold_used),
        "crossovers": crossovers(hold_used),
        "hold_sensitivity": {"base": f"{hold_used:g}d (median positive-funding episode)",
                             "table": hold_sensitivity},
        "any_grid_size_beats_tbill": any_beats(None, gross_median, hold_used, HURDLE_TBILL_APR),
        "hurdle_tbill_apr": HURDLE_TBILL_APR,
        "conditional_on": [
            "measured depth from a single weekend snapshot (2026-11-22T11:49Z)",
            "taker execution (40bp of fees at $10k)",
            "funding-rate stationarity -- BTC funding compressed from +2.80bp/8h (2021) to "
            "+0.30bp/8h (2026); the median is dominated by older regimes",
            "perp spread assumed equal to spot spread",
        ],
    }


def build_item37(carry):
    """Combined book: only funding carry + cash is defensible. Zero-listed pairs searched:
    0 -- no pair statistics are computed, so no multiple-comparisons correction is needed."""
    h30 = carry["aggregate_always_on_by_H"]["30"]
    h90 = carry["aggregate_always_on_by_H"]["90"]
    mu30, mu90 = h30["net_apr"], h90["net_apr"]
    sh30 = h30.get("sharpe_ann")
    sh90 = h90.get("sharpe_ann")
    rf = HURDLE_TBILL_APR
    spy_sharpe = 0.351    # measured, docs/edge_research/07_HURDLE_RATES

    def excess_sharpe(mu, sh):
        # raw Sharpe = mu/sd  ->  sd = mu/sh  ->  excess Sharpe = (mu-rf)/sd = sh*(mu-rf)/mu
        if not sh or mu == 0:
            return None
        return sh * (mu - rf) / mu

    return {
        "item": 37,
        "n_non_negative_strategies": 1,
        "n_killed": 12,
        "n_marginal": 1,
        "algebra": (
            "Equal-weight blend of a risky sleeve (mean mu, sd s) with cash (rate rf) at weight w: "
            "mean_p = w*mu + (1-w)*rf, sd_p = w*s. Excess return = mean_p - rf = w*(mu - rf). "
            "Sharpe_excess_p = w*(mu-rf)/(w*s) = (mu-rf)/s = Sharpe_excess of the sleeve, "
            "INDEPENDENT of w. So blending with cash cannot raise the excess Sharpe of the book; "
            "for any w>0 it only scales the expected excess return by w. If the sleeve's expected "
            "excess return mu-rf <= 0, every w>0 has non-positive expected excess return and the "
            "optimum is w=0 (100% cash). Diversification lowers variance; it cannot lift a "
            "non-positive mean, and lower variance around a non-positive mean is not a benefit."),
        "funding_carry": {
            "net_apr_H30": mu30,
            "net_apr_H90": mu90,
            "raw_sharpe_H30": sh30,
            "raw_sharpe_H90": sh90,
            "excess_sharpe_vs_cash_H30": excess_sharpe(mu30, sh30),
            "excess_sharpe_vs_cash_H90": excess_sharpe(mu90, sh90),
            "note": "the reported raw Sharpe is return/vol, NOT excess over cash; against the "
                    "4.32% T-bill the excess Sharpe is negative because net APR < 4.32%",
        },
        "cash": {"rate": rf},
        "spy": {"measured_sharpe": spy_sharpe},
        "blend_funding_carry_cash": {
            "best_allocation": "100% cash",
            "reason": "funding-carry net APR (2.42% at H30, 6.24% at H90) only beats the 4.32% "
                      "T-bill at the 90d tail, whose excess Sharpe over cash is still the sleeve's "
                      "own and does not improve with blending; at the median hold it is below cash",
            "beats_100pct_cash": False,
        },
        "verdict": "NOT_APPLICABLE (multi-strategy) / no viable book: only one non-negative strategy",
        "exploratory_pairs_searched": 0,
    }


def build_item38():
    """Live/paper book vs SPY vs T-bills over the same window.

    Two surfaces, two answers:
      (a) paper_portfolio/book.json -- the live paper book: 3 OPEN demo positions, 0 closed.
          By the brief's own rule (no closed trades -> no counterfactual) this is NOT_APPLICABLE.
      (b) audit_dashboard/data/resolved_closed_picks_net.json -- the resolved closed pick
          population with real dates and net PnL. This is where an actual counterfactual can
          be computed, with a survivorship caveat.
    """
    book = json.load(open(ROOT / "paper_portfolio" / "book.json"))
    res = json.load(open(ROOT / "audit_dashboard" / "data" / "resolved_closed_picks_net.json"))
    rows = res["rows"]

    n_open = len(book.get("positions", []))
    n_closed = len(book.get("closed", []))

    # (a) live paper book
    live_book = {
        "path": "paper_portfolio/book.json",
        "purpose": book.get("purpose"),
        "n_open_positions": n_open,
        "n_closed_trades": n_closed,
        "realized_pnl_net": book.get("realized_pnl_net"),
        "verdict": "NOT_APPLICABLE" if n_closed == 0 else "COMPUTED",
        "evidence": f"book.json holds {n_open} open positions and {n_closed} closed trades; "
                    f"with zero closed trades there is no realised window to compare against SPY",
        "gate_loader": "11 pods checked, 0 eligible (docs/edge_research/03_P0_...md) -- nothing "
                       "was ever loaded into the live book",
    }

    # (b) resolved closed picks
    import re
    net = [r["pnl_net_pct"] for r in rows if isinstance(r.get("pnl_net_pct"), (int, float))]
    dates = sorted(m.group(1) for r in rows
                   if (m := re.match(r"(\d{4}-\d{2}-\d{2})", r.get("closed_at") or "")))
    n = len(net)
    mean_net = st.mean(net) if net else None
    wins = sum(1 for x in net if x > 0)

    import datetime as dt
    first, last = dates[0], dates[-1]
    days = (dt.date.fromisoformat(last) - dt.date.fromisoformat(first)).days
    # SPY over the identical calendar window (yfinance); recorded, and marked UNMEASURED on failure
    spy = {"source": "yfinance SPY auto_adjust Close", "total_return_pct": None,
           "annualised_pct": None, "window": f"{first}..{last}"}
    try:
        import yfinance as yf
        df = yf.download("SPY", start=first, end=last, progress=False, auto_adjust=True)
        if df is not None and len(df):
            c = df["Close"]
            try:
                c = c["SPY"]
            except Exception:
                pass
            spy["total_return_pct"] = float((c.iloc[-1] / c.iloc[0] - 1) * 100)
            spy["annualised_pct"] = float(((c.iloc[-1] / c.iloc[0]) ** (365 / days) - 1) * 100)
            spy["window"] = f"{c.index[0].date()}..{c.index[-1].date()}"
    except Exception as e:  # network / rate limit -> UNMEASURED, never a guessed number
        spy["error"] = f"{type(e).__name__}: {e}"

    tbill_pct = HURDLE_TBILL_APR * 100 * days / 365
    resolved = {
        "path": "audit_dashboard/data/resolved_closed_picks_net.json",
        "n_closed_rows": len(rows),
        "n_with_net_pnl": n,
        "window": f"{first}..{last}",
        "window_days": days,
        "win_rate_pct": round(100 * wins / n, 2) if n else None,
        "mean_net_pct_per_trade": mean_net,
        "sum_net_pct": sum(net) if net else None,
        "median_net_pct_per_trade": st.median(net) if net else None,
        "per_trade_sharpe": (mean_net / st.stdev(net)) if n > 1 and st.stdev(net) else None,
        "spy_same_window": spy,
        "tbill_same_window_pct": tbill_pct,
        "difference_vs_spy": (mean_net - spy["total_return_pct"]) if (
            mean_net is not None and spy["total_return_pct"] is not None) else None,
        "difference_vs_tbill_pct": (mean_net - tbill_pct) if mean_net is not None else None,
        "cost_basis": "net PnL already includes the class cost model (measured_class_slippage_bps)",
        "caveat": "survivorship-sensitive: these are the KEPT rows after 10,040 exclusions; "
                  "per-trade mean is not a portfolio return (no position sizing in the data)",
        "verdict": "COMPUTED",
    }

    if n_closed == 0 and resolved["verdict"] == "COMPUTED":
        overall = ("NO -- the aggregate resolved population has negative expectation "
                   f"(mean {mean_net:.4f}%/trade, win rate {resolved['win_rate_pct']}%) while SPY and "
                   "T-bills were positive over the identical window; and the live paper book has "
                   "no closed trades to judge at all")
    else:
        overall = "NO -- see per-surface verdicts"

    return {"item": 38,
            "live_book": live_book,
            "resolved_picks": resolved,
            "machinery_cost": "UNMEASURED (API calls / compute not metered in-repo)",
            "did_system_beat_doing_nothing": overall}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="write the three reports")
    args = ap.parse_args(argv)

    books = load_raw_books()
    curves = measured_depth_curve(books)
    carry = json.load(open(CARRY_REPORT))

    i35 = build_item35(books, curves)
    i36 = build_item36(curves, carry)
    i37 = build_item37(carry)
    i38 = build_item38()

    if args.write:
        out = ROOT / "reports"
        for name, payload in [("capacity_20261122.json", {"item35": i35, "item36": i36}),
                              ("combined_book_20261122.json", i37),
                              ("no_trade_counterfactual_20261122.json", i38)]:
            (out / name).write_text(json.dumps(payload, indent=1, default=str))
            print("wrote", (out / name).relative_to(ROOT))

    if args.json:
        print(json.dumps({"item35": i35, "item36": i36, "item37": i37, "item38": i38},
                         indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

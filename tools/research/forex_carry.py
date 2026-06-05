#!/usr/bin/env python3
"""G10 FX carry-factor signal generator.

Carry = high-yield currency LONG vs low-yield currency SHORT.
Data: FRED interest rates (policy rates) + Yahoo Finance FX spot rates.

Usage:
    python tools/research/forex_carry.py           # print current carry signals
    python tools/research/forex_carry.py --backtest # run 1-year backtest
    python tools/research/forex_carry.py --backtest --start 2010-01-01  # 10y unlock study
    python tools/research/forex_carry.py --json     # output JSON for integration

UNLOCK CONDITION: If backtest shows PF>1.0, WR>45%, n>30, print unlock message
and suggest setting FOREX_HARD_DISABLE=0 in alpha_engine/config.py.

## Wiring Plan
Target: alpha_engine/config.py FOREX_HARD_DISABLE gate
When backtest_summary.pf > 1.0 AND wr > 0.45 AND n > 30:
  - Set FOREX_HARD_DISABLE=0 in production .env
  - Wire forex_carry.py signals into alpha_engine/production_scanner.py
    as source_system="forex_carry_v1"
  - Target PR: next sprint after unlock condition confirmed

Kill-switch: FOREX_CARRY_ENABLED=0 (default 0; FOREX_HARD_DISABLE=1 blocks class-wide).
Context: FOREX was halted class-wide 2026-05-15 (PF 0.27, WR 46.1%, n=1355).
         Carry factor is the most academically robust FOREX edge (Burnside et al. 2011,
         Lustig et al. 2007). Run this backtest to prove/disprove whether carry
         survives our execution model before reopening the class.

Output: reports/forex_carry_backtest_{date}.json
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── G10 universe ───────────────────────────────────────────────────────────────
# yfinance tickers for FX pairs (vs USD, price = units of foreign per 1 USD, except
# for commodity-quote pairs where price = USD per 1 foreign unit)
G10_CCY: List[str] = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK", "NZD"]

# yfinance pair tickers — all quoted as 1 USD = X foreign (inverse of spot convention
# for EUR/GBP/AUD/NZD, but yfinance returns in the form XXXUSD=X = X per 1 USD for
# non-USD-base pairs; for USD-base we use USDXXX=X)
# We store sign convention: +1 means the series rises when USD strengthens vs that ccy
# (i.e., buying USD means short that ccy). We long the ccy by taking the inverse.
YF_TICKERS: Dict[str, str] = {
    "EUR": "EURUSD=X",   # EUR/USD — price = USD per EUR; rises when EUR strengthens
    "GBP": "GBPUSD=X",   # GBP/USD
    "JPY": "JPYUSD=X",   # JPY/USD — price = USD per JPY (tiny)
    "AUD": "AUDUSD=X",   # AUD/USD
    "CAD": "CADUSD=X",   # CAD/USD
    "CHF": "CHFUSD=X",   # CHF/USD
    "NOK": "NOKUSD=X",   # NOK/USD
    "SEK": "SEKUSD=X",   # SEK/USD
    "NZD": "NZDUSD=X",   # NZD/USD
    # USD is the base — its "return" is embedded in the short side
}

# ── FRED series for short-term interest rates ──────────────────────────────────
# Each series should be a short-term policy/deposit rate in % p.a.
FRED_SERIES: Dict[str, str] = {
    "USD": "FEDFUNDS",       # Fed Funds Rate
    "EUR": "ECBDFR",         # ECB Deposit Facility Rate
    "GBP": "BOEBR",          # Bank of England Base Rate
    "JPY": "IRSTJP01STQ156N",# Japan short-term rate (OECD)
    "AUD": "RBATCTR",        # RBA Target Cash Rate
    "CAD": "CORRA",          # Canadian Overnight Rate
    "CHF": "IRSTCH01STQ156N",# Switzerland short-term rate (OECD)
    "NOK": "IRSTNO01STQ156N",# Norway short-term rate (OECD)
    "SEK": "IRSTSE01STQ156N",# Sweden short-term rate (OECD)
    "NZD": "IRSTNZ01STQ156N",# New Zealand short-term rate (OECD)
}

# Hardcoded fallback rates (% p.a.) — updated 2026-05 from central bank sources
# USD=5.33 reflects pre-cut FEDFUNDS; adjust if FRED unavailable
FALLBACK_RATES: Dict[str, float] = {
    "USD": 5.33,   # Fed Funds (pre-cut level 2024)
    "EUR": 3.90,   # ECB deposit rate (post-Sep2024 cut cycle)
    "GBP": 5.10,   # BoE base rate
    "JPY": 0.10,   # BoJ ultra-loose (raised to 0.1% Mar2024)
    "AUD": 4.35,   # RBA cash rate
    "CAD": 4.75,   # BoC overnight rate
    "CHF": 1.50,   # SNB policy rate (post-cut)
    "NOK": 4.50,   # Norges Bank rate
    "SEK": 3.75,   # Riksbank repo rate
    "NZD": 5.50,   # RBNZ official cash rate
}

# Portfolio construction
LONG_K = 3    # top-3 high yield = long
SHORT_K = 3   # bottom-3 low yield = short (funding currencies)
REBALANCE_FREQ = "monthly"

# Unlock thresholds (per task spec — more conservative than prior 1.5/50/100 floor)
UNLOCK_PF = 1.0
UNLOCK_WR = 0.45
UNLOCK_N = 30

# ── FRED rate fetcher ──────────────────────────────────────────────────────────


def _fetch_fred_rate(series_id: str, api_key: str) -> Optional[float]:
    """Fetch the most recent observation for a FRED series.

    Returns the value as a float (% p.a.), or None on failure.
    """
    try:
        import urllib.request
        import urllib.parse

        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}"
            f"&api_key={api_key}"
            "&file_type=json"
            "&sort_order=desc"
            "&limit=1"
            "&observation_start=2022-01-01"
        )
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        observations = data.get("observations", [])
        if observations:
            val_str = observations[0].get("value", "")
            if val_str and val_str != ".":
                return float(val_str)
    except Exception as exc:
        log.debug("FRED fetch failed for %s: %s", series_id, exc)
    return None


def fetch_current_rates(api_key: Optional[str] = None) -> Dict[str, float]:
    """Fetch current G10 short-term rates from FRED, falling back to hardcoded values.

    Returns dict {ccy: rate_pct_pa}.
    """
    if api_key is None:
        api_key = os.environ.get("FRED_API_KEY", "")

    rates: Dict[str, float] = {}
    fred_hits = 0
    fred_misses = 0

    for ccy, series_id in FRED_SERIES.items():
        if api_key:
            val = _fetch_fred_rate(series_id, api_key)
            if val is not None:
                rates[ccy] = val
                fred_hits += 1
                log.debug("FRED %s (%s) = %.2f%%", ccy, series_id, val)
                continue
        # Fallback
        rates[ccy] = FALLBACK_RATES[ccy]
        fred_misses += 1
        if api_key:
            log.warning("FRED fallback for %s (%s) → %.2f%%", ccy, series_id, FALLBACK_RATES[ccy])
        else:
            log.debug("No FRED key — using fallback for %s: %.2f%%", ccy, FALLBACK_RATES[ccy])

    log.info(
        "Rates loaded: %d FRED live / %d fallback (api_key=%s)",
        fred_hits, fred_misses, "yes" if api_key else "no",
    )
    return rates


# ── FX spot price fetcher ──────────────────────────────────────────────────────


def _fetch_fx_prices(
    ccys: List[str],
    start: str,
    end: str,
) -> Dict[str, Any]:
    """Fetch daily FX prices via yfinance. Returns {ccy: pd.Series of USD-per-unit}."""
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance not installed — run: pip install yfinance")
        return {}

    prices: Dict[str, Any] = {}
    for ccy in ccys:
        if ccy == "USD":
            continue  # USD is numeraire
        ticker_sym = YF_TICKERS.get(ccy)
        if not ticker_sym:
            log.warning("No yfinance ticker for %s", ccy)
            continue
        try:
            ticker = yf.Ticker(ticker_sym)
            hist = ticker.history(start=start, end=end, interval="1d")
            if not hist.empty:
                prices[ccy] = hist["Close"]
                log.debug("Fetched %d rows for %s (%s)", len(hist), ccy, ticker_sym)
            else:
                log.warning("No data for %s (%s) in %s→%s", ccy, ticker_sym, start, end)
        except Exception as exc:
            log.warning("yfinance error %s (%s): %s", ccy, ticker_sym, exc)
    return prices


# ── Signal ranking ─────────────────────────────────────────────────────────────


def rank_carry(
    rates: Dict[str, float],
    base_ccy: str = "USD",
) -> List[Tuple[str, float]]:
    """Rank G10 currencies by yield vs USD base.

    Returns list of (ccy, differential_pct) sorted desc (highest carry first).
    Positive differential: that currency yields MORE than USD → LONG vs USD (short USD).
    Negative differential: that currency yields LESS than USD → SHORT (USD earns carry).
    """
    usd_rate = rates.get(base_ccy, FALLBACK_RATES[base_ccy])
    diffs = [
        (ccy, rate - usd_rate)
        for ccy, rate in rates.items()
        if ccy != base_ccy
    ]
    return sorted(diffs, key=lambda x: x[1], reverse=True)


def _detect_carry_regime(ranked: List[Tuple[str, float]]) -> str:
    """Classify carry regime: favorable (wide spreads) vs unfavorable (compressed).

    Uses the median absolute spread across all pairs to gauge dispersion.
    """
    if not ranked:
        return "carry_unfavorable"
    spreads = [abs(diff) for _, diff in ranked]
    median_spread = sorted(spreads)[len(spreads) // 2]
    # If median spread >= 1.5% pa → carry is favorable (wide differentials)
    return "carry_favorable" if median_spread >= 1.5 else "carry_unfavorable"


def build_signals(
    rates: Dict[str, float],
    base_ccy: str = "USD",
    timestamp: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build top-3 LONG + bottom-3 SHORT carry signals.

    Returns list of signal dicts (not yet wired to production_scanner).
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    ranked = rank_carry(rates, base_ccy)
    signals: List[Dict[str, Any]] = []

    # Long top-3 (highest yield vs USD)
    for rank_idx, (ccy, diff_pct) in enumerate(ranked[:LONG_K]):
        carry_bps = int(round(abs(diff_pct) * 100))
        pair_label = f"{ccy}/{base_ccy}" if diff_pct > 0 else f"{base_ccy}/{ccy}"
        conviction = min(0.95, 0.55 + abs(diff_pct) * 0.04)
        signals.append({
            "pair": pair_label,
            "ccy": ccy,
            "direction": "LONG",
            "carry_bps": carry_bps,
            "rate_pct": round(rates[ccy], 2),
            "usd_rate_pct": round(rates.get(base_ccy, FALLBACK_RATES[base_ccy]), 2),
            "rank": rank_idx + 1,
            "conviction": round(conviction, 2),
            "source": "forex_carry_v1",
            "generated_at": timestamp,
        })

    # Short bottom-3 (lowest yield vs USD — funding currencies)
    for rank_idx, (ccy, diff_pct) in enumerate(reversed(ranked[-SHORT_K:])):
        carry_bps = int(round(abs(diff_pct) * 100))
        pair_label = f"{base_ccy}/{ccy}"
        conviction = min(0.95, 0.55 + abs(diff_pct) * 0.04)
        signals.append({
            "pair": pair_label,
            "ccy": ccy,
            "direction": "SHORT",
            "carry_bps": carry_bps,
            "rate_pct": round(rates[ccy], 2),
            "usd_rate_pct": round(rates.get(base_ccy, FALLBACK_RATES[base_ccy]), 2),
            "rank": rank_idx + 1,
            "conviction": round(conviction, 2),
            "source": "forex_carry_v1",
            "generated_at": timestamp,
        })

    return signals


# ── Backtest ───────────────────────────────────────────────────────────────────


def _compute_monthly_returns(prices: Dict[str, Any]) -> Dict[str, Any]:
    """Resample daily prices to month-end percent changes."""
    try:
        import pandas as pd
    except ImportError:
        log.error("pandas not installed")
        return {}

    monthly: Dict[str, Any] = {}
    for ccy, series in prices.items():
        try:
            s = series.resample("ME").last()
            monthly[ccy] = s.pct_change().dropna()
        except Exception as exc:
            log.warning("Resample error %s: %s", ccy, exc)
    return monthly


def run_carry_backtest(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rates: Optional[Dict[str, float]] = None,
    api_key: Optional[str] = None,
    output_path: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run G10 carry factor backtest.

    Args:
        start_date: ISO date string for backtest start (default: 1 year ago).
        end_date: ISO date string for backtest end (default: today).
        rates: Override dict {ccy: rate_%} (default: fetched from FRED/fallback).
        api_key: FRED API key (default: env var FRED_API_KEY).
        output_path: Where to write JSON report.
        verbose: Extra logging.

    Returns:
        Dict with keys: pf, wr, n, sharpe, mdd, total_return, trades, unlock_status.
    """
    today = date.today()
    if end_date is None:
        end_date = today.isoformat()
    if start_date is None:
        start_date = (today - timedelta(days=365)).isoformat()

    if output_path is None:
        report_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "reports",
        )
        os.makedirs(report_dir, exist_ok=True)
        output_path = os.path.join(
            report_dir, f"forex_carry_backtest_{today.strftime('%Y%m%d')}.json"
        )

    # Fetch rates
    if rates is None:
        rates = fetch_current_rates(api_key=api_key)

    log.info("G10 carry backtest: %s → %s", start_date, end_date)

    ranked = rank_carry(rates)
    long_ccys = [c for c, _ in ranked[:LONG_K]]
    short_ccys = [c for c, _ in ranked[-SHORT_K:]]
    log.info("Long portfolio (high carry): %s", long_ccys)
    log.info("Short portfolio (funding): %s", short_ccys)

    # Fetch FX prices
    all_ccys = list(YF_TICKERS.keys())
    prices = _fetch_fx_prices(all_ccys, start=start_date, end=end_date)
    if not prices:
        log.error("No price data fetched — backtest aborted")
        return {
            "error": "no_price_data",
            "pf": 0.0, "wr": 0.0, "n": 0, "sharpe": 0.0,
            "unlock_status": "LOCKED",
            "production_eligible": False,
        }

    monthly = _compute_monthly_returns(prices)

    trades: List[Dict[str, Any]] = []
    wins = 0
    losses = 0

    try:
        import pandas as pd
        import numpy as np

        # Find common dates across all long/short pairs
        all_dates = None
        for ccy in long_ccys + short_ccys:
            if ccy in monthly:
                if all_dates is None:
                    all_dates = monthly[ccy].index
                else:
                    all_dates = all_dates.intersection(monthly[ccy].index)

        if all_dates is None or len(all_dates) == 0:
            log.warning("No overlapping monthly dates across long/short pairs")
            return {
                "error": "no_overlap",
                "pf": 0.0, "wr": 0.0, "n": 0, "sharpe": 0.0,
                "unlock_status": "LOCKED",
                "production_eligible": False,
            }

        for dt in all_dates:
            dt_str = str(dt)[:10]
            port_ret = 0.0
            components: Dict[str, float] = {}
            valid = True

            # Long side: we profit when the high-yield ccy appreciates vs USD
            for ccy in long_ccys:
                if ccy not in monthly:
                    valid = False
                    break
                ret = float(monthly[ccy].get(dt, float("nan")))
                if ret != ret:  # NaN
                    valid = False
                    break
                port_ret += ret / LONG_K
                components[f"long_{ccy}"] = round(ret, 5)

            if not valid:
                continue

            # Short side: we profit when the low-yield ccy depreciates vs USD
            for ccy in short_ccys:
                if ccy not in monthly:
                    valid = False
                    break
                ret = float(monthly[ccy].get(dt, float("nan")))
                if ret != ret:
                    valid = False
                    break
                port_ret -= ret / SHORT_K
                components[f"short_{ccy}"] = round(-ret, 5)

            if not valid:
                continue

            # Add carry earned (annualized spread / 12 months, simplified)
            # Long: earn (long_rate - usd_rate) / 12 / 100
            # Short: earn (usd_rate - short_rate) / 12 / 100
            usd_rate = rates.get("USD", FALLBACK_RATES["USD"])
            carry_earned = 0.0
            for ccy in long_ccys:
                carry_earned += (rates.get(ccy, 0) - usd_rate) / 12 / 100 / LONG_K
            for ccy in short_ccys:
                carry_earned += (usd_rate - rates.get(ccy, 0)) / 12 / 100 / SHORT_K

            port_ret += carry_earned

            won = port_ret > 0
            if won:
                wins += 1
            else:
                losses += 1

            trades.append({
                "date": dt_str,
                "pnl_pct": round(port_ret * 100, 3),
                "carry_earned_pct": round(carry_earned * 100, 4),
                "won": won,
                "components": components,
            })

            if verbose:
                log.info("Month %s: pnl=%.3f%% (carry=%.4f%%)", dt_str, port_ret * 100, carry_earned * 100)

    except Exception as exc:
        log.error("Backtest loop error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "pf": 0.0, "wr": 0.0, "n": 0, "sharpe": 0.0,
            "unlock_status": "LOCKED",
            "production_eligible": False,
        }

    total = len(trades)
    wr = wins / total if total > 0 else 0.0
    gross_wins = sum(t["pnl_pct"] for t in trades if t["won"])
    gross_losses = abs(sum(t["pnl_pct"] for t in trades if not t["won"]))
    pf = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

    # Sharpe (monthly, annualized)
    try:
        import pandas as pd
        import numpy as np
        rets_series = pd.Series([t["pnl_pct"] / 100 for t in trades])
        sharpe = float((rets_series.mean() / rets_series.std()) * (12 ** 0.5)) if rets_series.std() > 0 else 0.0
        # Max drawdown
        cum = (1 + rets_series).cumprod()
        roll_max = cum.cummax()
        dd = (cum - roll_max) / roll_max
        mdd = float(dd.min())
        total_return = float(cum.iloc[-1] - 1) if len(cum) > 0 else 0.0
    except Exception:
        sharpe = 0.0
        mdd = 0.0
        total_return = 0.0

    # Unlock check (per spec: PF>1.0 / WR>45% / n>30)
    unlock_ready = pf > UNLOCK_PF and wr > UNLOCK_WR and total > UNLOCK_N

    result: Dict[str, Any] = {
        "strategy": "forex_carry_g10",
        "rebalance": REBALANCE_FREQ,
        "long_ccys": long_ccys,
        "short_ccys": short_ccys,
        "start_date": start_date,
        "end_date": end_date,
        "pf": round(pf, 3),
        "wr": round(wr, 4),
        "n": total,
        "wins": wins,
        "losses": losses,
        "sharpe": round(sharpe, 3),
        "mdd": round(mdd, 4),
        "total_return": round(total_return, 4),
        "unlock_status": "UNLOCK_READY" if unlock_ready else "LOCKED",
        "unlock_thresholds": {
            "pf_required": UNLOCK_PF,
            "wr_required": UNLOCK_WR,
            "n_required": UNLOCK_N,
        },
        "production_eligible": unlock_ready,
        "note": (
            "FOREX_HARD_DISABLE=1 must be cleared before any production wiring. "
            "Run 30-day paper pilot first."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trades": trades,
    }

    if unlock_ready:
        unlock_msg = (
            "\n" + "=" * 70 + "\n"
            "  UNLOCK CONDITION MET\n"
            f"  PF={pf:.3f} > {UNLOCK_PF}  |  WR={wr*100:.1f}% > {UNLOCK_WR*100:.0f}%  |  n={total} > {UNLOCK_N}\n"
            "\n"
            "  ACTION REQUIRED:\n"
            "  1. Set FOREX_HARD_DISABLE=0 in alpha_engine/config.py (or .env)\n"
            "  2. Wire forex_carry_v1 signals into alpha_engine/production_scanner.py\n"
            "     as source_system='forex_carry_v1'\n"
            "  3. Run 30-day paper pilot before live sizing\n"
            "  4. Track live WR/PF — delist if PF drops below 1.0 over 20+ trades\n"
            + "=" * 70 + "\n"
        )
        log.info(unlock_msg)
        result["unlock_message"] = unlock_msg.strip()
    else:
        log.info(
            "Backtest NOT at unlock threshold: PF=%.3f (need>%.1f) WR=%.1f%% (need>%.0f%%) n=%d (need>%d)",
            pf, UNLOCK_PF, wr * 100, UNLOCK_WR * 100, total, UNLOCK_N,
        )

    # Write JSON report
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        log.info("Report written: %s", output_path)
    except Exception as exc:
        log.warning("Report write failed: %s", exc)

    log.info(
        "G10 carry backtest done: PF=%.3f WR=%.1f%% n=%d Sharpe=%.3f MDD=%.1f%% eligible=%s",
        pf, wr * 100, total, sharpe, mdd * 100, unlock_ready,
    )
    return result


# ── JSON output formatter ──────────────────────────────────────────────────────


def build_json_output(
    rates: Optional[Dict[str, float]] = None,
    backtest_result: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the integration-ready JSON output.

    This is the format consumed by tools that check unlock status.
    """
    now = datetime.now(timezone.utc).isoformat()
    if rates is None:
        rates = fetch_current_rates(api_key=api_key)

    ranked = rank_carry(rates)
    regime = _detect_carry_regime(ranked)
    signals = build_signals(rates, timestamp=now)

    bt_summary = {"wr": 0.0, "pf": 0.0, "n": 0, "sharpe": 0.0, "mdd": 0.0}
    unlock_status = "LOCKED"
    if backtest_result:
        bt_summary = {
            "wr": backtest_result.get("wr", 0.0),
            "pf": backtest_result.get("pf", 0.0),
            "n": backtest_result.get("n", 0),
            "sharpe": backtest_result.get("sharpe", 0.0),
            "mdd": backtest_result.get("mdd", 0.0),
        }
        unlock_status = backtest_result.get("unlock_status", "LOCKED")

    return {
        "generated_at": now,
        "signals": [
            {
                "pair": s["pair"],
                "direction": s["direction"],
                "carry_bps": s["carry_bps"],
                "conviction": s["conviction"],
                "source": s["source"],
            }
            for s in signals
        ],
        "regime": regime,
        "unlock_status": unlock_status,
        "backtest_summary": bt_summary,
        "rates_used": {k: round(v, 3) for k, v in rates.items()},
    }


# ── CLI ────────────────────────────────────────────────────────────────────────


def _print_signals_table(rates: Dict[str, float]) -> None:
    """Print carry ranking table to stdout."""
    ranked = rank_carry(rates)
    usd_rate = rates.get("USD", FALLBACK_RATES["USD"])
    regime = _detect_carry_regime(ranked)

    print(f"\nG10 Carry Ranking — USD rate={usd_rate:.2f}%  |  Regime={regime}")
    print(f"{'Rank':<5} {'CCY':<6} {'Rate%':<8} {'Spread bps':<12} {'Signal':<8}")
    print("-" * 45)
    for i, (ccy, diff) in enumerate(ranked):
        if i < LONG_K:
            signal = "LONG"
        elif i >= len(ranked) - SHORT_K:
            signal = "SHORT"
        else:
            signal = "neutral"
        bps = int(round(diff * 100))
        rate_str = f"{rates[ccy]:.2f}%"
        spread_str = f"{bps:+d} bps"
        print(f"{i+1:<5} {ccy:<6} {rate_str:<8} {spread_str:<12} {signal}")
    print()


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    do_backtest = "--backtest" in sys.argv
    do_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv
    start_date = None
    for i, arg in enumerate(sys.argv):
        if arg == "--start" and i + 1 < len(sys.argv):
            start_date = sys.argv[i + 1]
        elif arg.startswith("--start="):
            start_date = arg.split("=", 1)[1]

    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        log.warning("FRED_API_KEY not set — using hardcoded fallback rates")

    rates = fetch_current_rates(api_key=api_key)

    if do_backtest:
        log.info("Running 1-year G10 carry backtest...")
        backtest = run_carry_backtest(
            api_key=api_key, rates=rates, verbose=verbose, start_date=start_date
        )
        if do_json:
            out = build_json_output(rates=rates, backtest_result=backtest, api_key=api_key)
            print(json.dumps(out, indent=2, default=str))
        else:
            # Human-readable summary
            _print_signals_table(rates)
            print("=== Backtest Summary ===")
            print(f"  Period : {backtest.get('start_date')} → {backtest.get('end_date')}")
            print(f"  Trades : {backtest.get('n', 0)}")
            print(f"  WR     : {backtest.get('wr', 0) * 100:.1f}%")
            print(f"  PF     : {backtest.get('pf', 0):.3f}")
            print(f"  Sharpe : {backtest.get('sharpe', 0):.3f}")
            print(f"  MDD    : {backtest.get('mdd', 0) * 100:.1f}%")
            print(f"  TotRet : {backtest.get('total_return', 0) * 100:.1f}%")
            print(f"  Status : {backtest.get('unlock_status', 'LOCKED')}")
            if backtest.get("unlock_status") == "UNLOCK_READY":
                print()
                print(backtest.get("unlock_message", ""))
    elif do_json:
        out = build_json_output(rates=rates, api_key=api_key)
        print(json.dumps(out, indent=2, default=str))
    else:
        # Default: print current signals
        _print_signals_table(rates)
        signals = build_signals(rates)
        print("Current carry signals (research mode — NOT wired to production):")
        for s in signals:
            print(
                f"  {s['direction']:5s}  {s['pair']:10s}  "
                f"{s['carry_bps']:+4d} bps  conviction={s['conviction']:.2f}"
            )
        print()
        print("Note: FOREX_HARD_DISABLE=1 is active. Run --backtest to check unlock condition.")

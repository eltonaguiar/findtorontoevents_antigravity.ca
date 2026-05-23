#!/usr/bin/env python3
"""
Harvey-Liu Deflated Sharpe Ratio (DSR) for strategy validation.

References:
  - Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"
  - Harvey & Liu (2015) "Backtesting"

Corrects observed Sharpe ratios for multiple testing bias across all
strategies tested. A strategy with DSR < 0 cannot reject the null
hypothesis of zero Sharpe after the haircut.

Usage:
    python tools/deflated_sharpe.py
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "..",
                         "audit_dashboard", "data", "dashboard_data.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "deflated_sharpe_results.json")
MIN_TRADES = 10
ANNUAL_TRADES = 6 * 365  # ~6 trades/day for crypto, annualise


def _erfinv_approx(x):
    """Rational approximation of inverse error function (Winitzki 2008)."""
    if x <= -1.0:
        return -float("inf")
    if x >= 1.0:
        return float("inf")
    a = 0.147
    ln1mx2 = math.log(1.0 - x * x)
    t1 = 2.0 / (math.pi * a) + ln1mx2 / 2.0
    inner = t1 * t1 - ln1mx2 / a
    return math.copysign(math.sqrt(math.sqrt(inner) - t1), x)


def _compute_moments(returns):
    """Mean, std, skewness, excess kurtosis from a list of returns."""
    n = len(returns)
    if n < 3:
        return 0.0, 1.0, 0.0, 3.0
    mu = sum(returns) / n
    var = sum((r - mu) ** 2 for r in returns) / n
    std = math.sqrt(var) if var > 0 else 1e-12
    skew = sum(((r - mu) / std) ** 3 for r in returns) / n
    kurt = sum(((r - mu) / std) ** 4 for r in returns) / n  # raw kurtosis
    return mu, std, skew, kurt


def _sharpe_se(sr, skew, kurt, T):
    """Standard error of the Sharpe ratio (Lo 2002 / Bailey-LdP 2014)."""
    # SE(SR) = sqrt( (1 + 0.5*SR^2 - skew*SR + (kurt-3)/4 * SR^2) / T )
    inside = (1.0 + 0.5 * sr * sr
              - skew * sr
              + (kurt - 3.0) / 4.0 * sr * sr)
    if inside < 0:
        inside = abs(inside)  # numerical guard
    return math.sqrt(inside / max(T, 1))


def _sr_haircut(n_strategies):
    """Harvey-Liu expected max Sharpe under null (multiple testing haircut).
    SR* = sqrt(2) * erfinv(1 - 2 / N)  where N = total strategies tested.
    """
    if n_strategies <= 1:
        return 0.0
    arg = 1.0 - 2.0 / n_strategies
    arg = max(min(arg, 0.9999), -0.9999)  # clamp for erfinv domain
    return math.sqrt(2.0) * _erfinv_approx(arg)


def _deflated_sharpe(sr_obs, sr_star, se_sr):
    """DSR = (SR_observed - SR_haircut) / SE(SR)."""
    if se_sr < 1e-15:
        return 0.0
    return (sr_obs - sr_star) / se_sr


def analyse_group(returns_by_key, n_total_strategies, label="strategy"):
    """Compute DSR for every key in returns_by_key dict."""
    sr_star = _sr_haircut(n_total_strategies)
    results = []

    for key, rets in sorted(returns_by_key.items()):
        T = len(rets)
        if T < MIN_TRADES:
            continue
        mu, std, skew, kurt = _compute_moments(rets)
        # Per-trade Sharpe (risk-free = 0)
        sr_trade = mu / std if std > 1e-12 else 0.0
        # Annualised Sharpe
        sr_ann = sr_trade * math.sqrt(ANNUAL_TRADES)
        se = _sharpe_se(sr_ann, skew, kurt, T)
        dsr = _deflated_sharpe(sr_ann, sr_star, se)
        win_rate = sum(1 for r in rets if r > 0) / T * 100
        avg_pnl = mu
        results.append({
            "key": key,
            "trades": T,
            "win_rate_pct": round(win_rate, 1),
            "avg_pnl_pct": round(avg_pnl, 4),
            "sharpe_annual": round(sr_ann, 4),
            "sr_haircut": round(sr_star, 4),
            "se_sr": round(se, 4),
            "dsr": round(dsr, 4),
            "survives": dsr > 0,
        })

    results.sort(key=lambda x: x["dsr"], reverse=True)
    return results


def main():
    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data["picks"]["recent_closed"]
    print(f"Loaded {len(picks)} closed picks")

    # ------------------------------------------------------------------
    # Group returns by strategy, source_system, and ensemble
    # ------------------------------------------------------------------
    by_strategy = defaultdict(list)
    by_source = defaultdict(list)
    all_returns = []

    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        pnl = float(pnl)
        strat = p.get("strategy", "unknown") or "unknown"
        source = p.get("source_system", "unknown") or "unknown"
        by_strategy[strat].append(pnl)
        by_source[source].append(pnl)
        all_returns.append(pnl)

    n_total = len(by_strategy)
    print(f"Total strategies found: {n_total}")
    print(f"SR haircut (N={n_total}): {_sr_haircut(n_total):.4f}")
    print()

    # ------------------------------------------------------------------
    # Per-strategy DSR
    # ------------------------------------------------------------------
    strat_results = analyse_group(by_strategy, n_total, "strategy")
    survivors = [r for r in strat_results if r["survives"]]
    flagged = [r for r in strat_results if not r["survives"]]

    print("=" * 72)
    print(f"STRATEGY DSR RESULTS  (min {MIN_TRADES} trades, {n_total} strategies)")
    print("=" * 72)
    print(f"{'Strategy':<35} {'Trades':>6} {'WR%':>6} {'SR_ann':>8} {'DSR':>8} {'OK':>4}")
    print("-" * 72)
    for r in strat_results[:30]:  # top 30
        flag = "YES" if r["survives"] else " NO"
        print(f"{r['key'][:34]:<35} {r['trades']:>6} {r['win_rate_pct']:>5.1f}% "
              f"{r['sharpe_annual']:>8.3f} {r['dsr']:>8.3f} {flag:>4}")

    print()
    print(f"Survive haircut: {len(survivors)}/{len(strat_results)} "
          f"({len(survivors)/max(len(strat_results),1)*100:.0f}%)")
    print(f"Flagged (DSR<0): {len(flagged)}/{len(strat_results)} "
          f"({len(flagged)/max(len(strat_results),1)*100:.0f}%)")

    # ------------------------------------------------------------------
    # Per-source_system DSR
    # ------------------------------------------------------------------
    n_sources = len(by_source)
    source_results = analyse_group(by_source, n_sources, "source_system")
    print()
    print("=" * 72)
    print(f"SOURCE SYSTEM DSR  ({n_sources} sources, haircut={_sr_haircut(n_sources):.4f})")
    print("=" * 72)
    print(f"{'Source':<35} {'Trades':>6} {'WR%':>6} {'SR_ann':>8} {'DSR':>8} {'OK':>4}")
    print("-" * 72)
    for r in source_results:
        flag = "YES" if r["survives"] else " NO"
        print(f"{r['key'][:34]:<35} {r['trades']:>6} {r['win_rate_pct']:>5.1f}% "
              f"{r['sharpe_annual']:>8.3f} {r['dsr']:>8.3f} {flag:>4}")

    # ------------------------------------------------------------------
    # Ensemble (all picks combined — haircut=0 since single test)
    # ------------------------------------------------------------------
    if len(all_returns) >= MIN_TRADES:
        mu, std, skew, kurt = _compute_moments(all_returns)
        sr_t = mu / std if std > 1e-12 else 0.0
        sr_ann = sr_t * math.sqrt(ANNUAL_TRADES)
        se = _sharpe_se(sr_ann, skew, kurt, len(all_returns))
        # For ensemble, haircut = 0 (single test, no correction needed)
        dsr_ens = _deflated_sharpe(sr_ann, 0.0, se)
        wr = sum(1 for r in all_returns if r > 0) / len(all_returns) * 100
        ensemble = {
            "key": "ENSEMBLE (all picks)",
            "trades": len(all_returns),
            "win_rate_pct": round(wr, 1),
            "avg_pnl_pct": round(mu, 4),
            "sharpe_annual": round(sr_ann, 4),
            "sr_haircut": 0.0,
            "se_sr": round(se, 4),
            "dsr": round(dsr_ens, 4),
            "survives": dsr_ens > 0,
        }
        print()
        print("=" * 72)
        print("ENSEMBLE (all picks combined, no multiple-testing correction)")
        print("=" * 72)
        print(f"  Trades: {ensemble['trades']}, WR: {ensemble['win_rate_pct']:.1f}%, "
              f"SR_ann: {ensemble['sharpe_annual']:.4f}, DSR: {ensemble['dsr']:.4f} "
              f"-> {'SURVIVES' if ensemble['survives'] else 'FLAGGED'}")
    else:
        ensemble = None

    # ------------------------------------------------------------------
    # Write JSON results
    # ------------------------------------------------------------------
    output = {
        "generated": datetime.now(tz=None).isoformat() + "Z",
        "config": {
            "min_trades": MIN_TRADES,
            "annual_trades": ANNUAL_TRADES,
            "total_strategies": n_total,
            "sr_haircut": round(_sr_haircut(n_total), 4),
        },
        "summary": {
            "strategies_analysed": len(strat_results),
            "strategies_surviving": len(survivors),
            "strategies_flagged": len(flagged),
            "survival_rate_pct": round(len(survivors) / max(len(strat_results), 1) * 100, 1),
        },
        "top20_by_dsr": strat_results[:20],
        "all_strategies": strat_results,
        "source_systems": source_results,
        "ensemble": ensemble,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults written to {OUT_PATH}")


if __name__ == "__main__":
    main()

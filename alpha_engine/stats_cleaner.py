#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Institutional-Grade Stats Cleaner for Audit Dashboard.

Removes noise from dashboard metrics by applying hedge-fund-standard
outlier capping, concentration risk detection, and risk-adjusted metrics.

Usage:
    python -m alpha_engine.stats_cleaner                   # summary from live data
    python -m alpha_engine.stats_cleaner --cap 10          # cap at +/-10%
    python -m alpha_engine.stats_cleaner --verbose         # show outlier details

Industry references:
    - Winsorized returns: standard at AQR, Two Sigma, Renaissance
    - Concentration risk: SEC Rule 35d-1 diversification requirements
    - Sharpe/Sortino/Calmar: CFA Institute GIPS standards
"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent


# ── 1. Winsorized / Capped Returns ──

def _compound_pct_ew_chronological(picks, max_abs_pct=None):
    """Geometric compound of pnl_pct in timestamp order (equal notional)."""
    if not picks:
        return 0.0

    def sort_key(p):
        return (str(p.get("timestamp") or ""), str(p.get("symbol") or ""))

    prod = 1.0
    for p in sorted(picks, key=sort_key):
        raw = float(p.get("pnl_pct", 0) or 0)
        if max_abs_pct is not None:
            raw = max(-max_abs_pct, min(max_abs_pct, raw))
        prod *= 1.0 + raw / 100.0
    return round((prod - 1.0) * 100.0, 2)


def clean_stats(closed_picks, cap_pct=10.0):
    """Return cleaned stats with outlier capping.

    Hedge funds cap individual trade returns at +/-cap_pct (default 10%)
    or +/-3 standard deviations to prevent outliers from distorting
    aggregate statistics.

    Args:
        closed_picks: list of pick dicts with 'pnl_pct' field
        cap_pct: maximum absolute PnL per trade (default 10.0%)

    Returns:
        (capped_picks, outlier_count): list of picks with pnl_pct_capped
        and pnl_pct_raw fields, plus count of capped trades
    """
    capped = []
    outliers_removed = 0
    for p in closed_picks:
        pnl = float(p.get("pnl_pct", 0) or 0)
        raw_pnl = pnl
        if abs(pnl) > cap_pct:
            outliers_removed += 1
            pnl = max(min(pnl, cap_pct), -cap_pct)
        capped.append({**p, "pnl_pct_capped": pnl, "pnl_pct_raw": raw_pnl})
    return capped, outliers_removed


# ── 2. Risk-Adjusted Metrics ──

def compute_clean_metrics(closed_picks, cap_pct=10.0):
    """Compute institutional-grade metrics from closed picks.

    Returns dict with:
        - total_pnl_raw: uncapped total PnL
        - total_pnl_capped: total PnL with trades capped at +/-cap_pct
        - avg_trade_pnl: average PnL per trade
        - median_trade_pnl: median PnL (not affected by outliers)
        - sharpe_per_trade: Sharpe ratio computed per-trade
        - calmar_ratio: return / max drawdown
        - profit_factor: gross win / gross loss
        - win_loss_ratio: avg win / avg loss
        - outlier_count: trades with |PnL| > cap_pct
        - concentration_warning: str or None
        - top_symbol: symbol with most PnL contribution
        - top_symbol_pnl_pct: % of total PnL from top symbol
    """
    if not closed_picks:
        return _empty_metrics()

    # Filter to resolved picks only (non-zero PnL)
    resolved = [p for p in closed_picks if float(p.get("pnl_pct", 0) or 0) != 0
                and not p.get("expired_no_pnl")]
    if not resolved:
        return _empty_metrics()

    capped, outlier_count = clean_stats(resolved, cap_pct)

    # Raw and capped totals
    raw_pnls = [float(p.get("pnl_pct", 0) or 0) for p in resolved]
    capped_pnls = [p["pnl_pct_capped"] for p in capped]

    total_pnl_raw = sum(raw_pnls)
    total_pnl_capped = sum(capped_pnls)

    # Average and median
    n = len(raw_pnls)
    avg_trade_pnl = total_pnl_raw / n if n > 0 else 0
    avg_trade_pnl_capped = total_pnl_capped / n if n > 0 else 0

    sorted_pnls = sorted(raw_pnls)
    if n % 2 == 1:
        median_trade_pnl = sorted_pnls[n // 2]
    else:
        median_trade_pnl = (sorted_pnls[n // 2 - 1] + sorted_pnls[n // 2]) / 2

    # ── 3. Institutional Purge (Toxic Assets & Broken Systems) ──
    # These symbols and systems are excluded from "Purged" metrics
    # because they represent data errors, tracking failures, or extreme anomalies.
    purge_symbols = {"TRXUSDT", "KATUSDT", "KITEUSDT", "RESOLVUSDT"}
    purge_systems = {"mercury2_fast", "mercury2_slow"}
    
    purged = [p for p in resolved if
              p.get("symbol", "").upper() not in purge_symbols and
              p.get("source_system", "").lower() not in purge_systems]
    purged_pnls = [float(p.get("pnl_pct", 0) or 0) for p in purged]
    total_pnl_purged = sum(purged_pnls)
    # Match dashboard_generator.py _MAX_PNL_COMPOUND = 2 (per-trade cap for EW compound)
    purged_pnl_compounded_ew = _compound_pct_ew_chronological(purged, max_abs_pct=2.0)

    # Sharpe ratio (per-trade, not annualized)
    sharpe_per_trade = None
    if n >= 5:
        mean_r = sum(capped_pnls) / n
        variance = sum((x - mean_r) ** 2 for x in capped_pnls) / (n - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        if std_dev > 0:
            sharpe_per_trade = round(mean_r / std_dev, 4)

    # Profit factor and win/loss ratio
    wins = [p for p in raw_pnls if p > 0]
    losses = [p for p in raw_pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else None
    avg_win = gross_win / len(wins) if wins else 0
    avg_loss = gross_loss / len(losses) if losses else 0
    win_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else None

    # Calmar ratio (total return / max drawdown)
    calmar_ratio = None
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in raw_pnls:
        cum += pnl
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    if max_dd > 0:
        calmar_ratio = round(total_pnl_raw / max_dd, 2)

    # ── 3. Concentration Risk ──
    symbol_pnl = defaultdict(float)
    for p in resolved:
        sym = p.get("symbol", "UNKNOWN")
        symbol_pnl[sym] += float(p.get("pnl_pct", 0) or 0)

    top_symbol = max(symbol_pnl, key=lambda s: abs(symbol_pnl[s])) if symbol_pnl else None
    top_symbol_pnl = symbol_pnl.get(top_symbol, 0) if top_symbol else 0
    top_symbol_pnl_pct = round(abs(top_symbol_pnl) / abs(total_pnl_raw) * 100, 1) \
        if total_pnl_raw != 0 and top_symbol else 0

    # Concentration warning if >25% from single symbol
    concentration_warning = None
    if top_symbol_pnl_pct > 25 and top_symbol:
        pnl_without = total_pnl_raw - top_symbol_pnl
        concentration_warning = (
            f"WARNING: {top_symbol_pnl_pct}% of total PnL comes from {top_symbol} trades. "
            f"Removing {top_symbol}, overall PnL drops from "
            f"{total_pnl_raw:+.1f}% to {pnl_without:+.1f}%. "
            f"Concentration risk is {'HIGH' if top_symbol_pnl_pct > 50 else 'MODERATE'}."
        )

    # Top 5 symbols by PnL contribution
    top_symbols = sorted(symbol_pnl.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
    top_symbols_detail = []
    for sym, pnl in top_symbols:
        item = {
            "symbol": sym, 
            "pnl": round(pnl, 2),
            "pct_of_total": round(abs(pnl) / abs(total_pnl_raw) * 100, 1) if total_pnl_raw != 0 else 0
        }
        if sym.upper() in purge_symbols:
            item["is_purged"] = True
            item["tooltip"] = f"Symbol {sym} is a known outlier/toxic asset. It is purged from Institutional Alpha metrics."
        top_symbols_detail.append(item)

    # Tooltip data (v102: "Do It" Purge)
    purged_count = len(resolved) - len(purged)
    purge_summary = f"Purged {purged_count} toxic/broken outliers (TRX, KATUSDT, Mercury2) from 'Purged PnL'."

    return {
        "total_pnl_raw": round(total_pnl_raw, 2),
        "total_pnl_capped": round(total_pnl_capped, 2),
        "purged_pnl_raw": round(total_pnl_purged, 2),
        "purged_pnl_compounded_ew": purged_pnl_compounded_ew,
        "purged_count": purged_count,
        "purge_summary": purge_summary,
        "cap_pct": cap_pct,
        "avg_trade_pnl": round(avg_trade_pnl, 2),
        "avg_trade_pnl_capped": round(avg_trade_pnl_capped, 2),
        "median_trade_pnl": round(median_trade_pnl, 2),
        "sharpe_per_trade": sharpe_per_trade,
        "calmar_ratio": calmar_ratio,
        "profit_factor": profit_factor,
        "win_loss_ratio": win_loss_ratio,
        "outlier_count": outlier_count,
        "total_resolved": n,
        "concentration_warning": concentration_warning,
        "top_symbol": top_symbol,
        "top_symbol_pnl_pct": top_symbol_pnl_pct,
        "top_symbols": top_symbols_detail,
        "max_drawdown": round(max_dd, 2),
    }


def compute_system_clean_metrics(closed_picks, cap_pct=10.0):
    """Compute clean metrics grouped by source_system.

    Returns dict mapping system_name -> clean metrics.
    """
    by_system = defaultdict(list)
    for p in closed_picks:
        sys_name = p.get("source_system", "unknown")
        by_system[sys_name].append(p)

    result = {}
    for sys_name, picks in by_system.items():
        result[sys_name] = compute_clean_metrics(picks, cap_pct)
    return result


def compute_timeframe_stats(closed_picks, cap_pct=10.0):
    """Compute stats for 24h, 7d, 30d, and all-time windows.

    Returns dict with keys: '24h', '7d', '30d', 'all'.
    Each value is a clean_metrics dict.
    """
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    windows = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    result = {}
    for label, delta in windows.items():
        cutoff = now - delta
        filtered = []
        for p in closed_picks:
            ts = p.get("timestamp", "")
            if ts:
                try:
                    ts_str = str(ts).strip()
                    if not ts_str.endswith("Z") and "+" not in ts_str:
                        ts_str += "Z"
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if dt >= cutoff:
                        filtered.append(p)
                except Exception:
                    pass
        result[label] = compute_clean_metrics(filtered, cap_pct)

    result["all"] = compute_clean_metrics(closed_picks, cap_pct)
    return result


def _empty_metrics():
    """Return empty metrics dict."""
    return {
        "total_pnl_raw": 0,
        "total_pnl_capped": 0,
        "cap_pct": 10.0,
        "avg_trade_pnl": 0,
        "avg_trade_pnl_capped": 0,
        "median_trade_pnl": 0,
        "sharpe_per_trade": None,
        "calmar_ratio": None,
        "profit_factor": None,
        "win_loss_ratio": None,
        "outlier_count": 0,
        "total_resolved": 0,
        "concentration_warning": None,
        "top_symbol": None,
        "top_symbol_pnl_pct": 0,
        "top_symbols": [],
        "max_drawdown": 0,
        "purged_pnl_raw": 0,
        "purged_pnl_compounded_ew": 0.0,
        "purged_count": 0,
        "purge_summary": "",
    }


# ── Standalone runner ──

def main():
    """Run stats cleaner on live dashboard data and print report."""
    import argparse
    parser = argparse.ArgumentParser(description="Institutional-grade stats cleanup")
    parser.add_argument("--cap", type=float, default=10.0, help="PnL cap per trade (default: 10%%)")
    parser.add_argument("--verbose", action="store_true", help="Show outlier details")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Load closed picks from dashboard payload or active_picks.json
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        data = json.loads(payload_path.read_text(encoding="utf-8"))
        closed = data.get("picks", {}).get("recent_closed", [])
    else:
        # Fallback: try alpha engine closed picks
        ap_path = ROOT / "alpha_engine" / "data" / "closed_picks.json"
        if ap_path.exists():
            closed = json.loads(ap_path.read_text(encoding="utf-8"))
        else:
            print("No data found. Run dashboard_generator first.")
            sys.exit(1)

    if not closed:
        print("No closed picks found.")
        sys.exit(0)

    metrics = compute_clean_metrics(closed, args.cap)
    tf_stats = compute_timeframe_stats(closed, args.cap)

    if args.json:
        print(json.dumps({"clean_metrics": metrics, "timeframe_stats": tf_stats}, indent=2))
        return

    print("=" * 70)
    print("  INSTITUTIONAL STATS CLEANER REPORT")
    print(f"  Cap: +/-{args.cap}% per trade | {metrics['total_resolved']} resolved trades")
    print("=" * 70)
    print()

    print(f"  Raw Total PnL:       {metrics['total_pnl_raw']:+.2f}%")
    print(f"  Capped Total PnL:    {metrics['total_pnl_capped']:+.2f}% (capped at +/-{args.cap}%)")
    print(f"  Outliers Capped:     {metrics['outlier_count']} trades")
    print()
    print(f"  Average Trade PnL:   {metrics['avg_trade_pnl']:+.2f}%")
    print(f"  Median Trade PnL:    {metrics['median_trade_pnl']:+.2f}%")
    print(f"  Avg (capped):        {metrics['avg_trade_pnl_capped']:+.2f}%")
    print()
    print(f"  Sharpe (per-trade):  {metrics['sharpe_per_trade'] or 'N/A'}")
    print(f"  Calmar Ratio:        {metrics['calmar_ratio'] or 'N/A'}")
    print(f"  Profit Factor:       {metrics['profit_factor'] or 'N/A'}")
    print(f"  Win/Loss Ratio:      {metrics['win_loss_ratio'] or 'N/A'}")
    print(f"  Max Drawdown:        {metrics['max_drawdown']:.2f}%")
    print()

    # Concentration
    if metrics["concentration_warning"]:
        print(f"  {metrics['concentration_warning']}")
    else:
        print(f"  Concentration: OK (top symbol {metrics['top_symbol']} = "
              f"{metrics['top_symbol_pnl_pct']:.1f}% of PnL)")

    print()
    print("  Top 5 Symbols by PnL Impact:")
    for s in metrics.get("top_symbols", []):
        print(f"    {s['symbol']:>12s}: {s['pnl']:+8.2f}% ({s['pct_of_total']:5.1f}% of total)")

    print()
    print("  Timeframe Stats:")
    for tf in ["24h", "7d", "30d", "all"]:
        ts = tf_stats[tf]
        print(f"    {tf:>6s}: {ts['total_resolved']:4d} trades | "
              f"Raw: {ts['total_pnl_raw']:+8.1f}% | "
              f"Capped: {ts['total_pnl_capped']:+8.1f}% | "
              f"Median: {ts['median_trade_pnl']:+6.2f}% | "
              f"Outliers: {ts['outlier_count']}")

    if args.verbose:
        print()
        print("  Outlier Details (|PnL| > {:.0f}%):".format(args.cap))
        capped_picks, _ = clean_stats(closed, args.cap)
        outliers = [p for p in capped_picks if abs(p["pnl_pct_raw"]) > args.cap]
        outliers.sort(key=lambda p: abs(p["pnl_pct_raw"]), reverse=True)
        for p in outliers[:30]:
            print(f"    {p.get('symbol', '?'):>12s} {p.get('strategy', '?'):>30s} "
                  f"Raw: {p['pnl_pct_raw']:+8.2f}% -> Capped: {p['pnl_pct_capped']:+8.2f}%")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()

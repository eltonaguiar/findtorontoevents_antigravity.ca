#!/usr/bin/env python3
"""Generate comprehensive performance report for multi-asset forward-test portfolio."""

import json
import math
import os
from datetime import datetime, timezone
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVE_FILE = os.path.join(SCRIPT_DIR, "data", "active_picks.json")
CLOSED_FILE = os.path.join(SCRIPT_DIR, "data", "multi_asset_closed.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "PERFORMANCE_REPORT.md")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(v, default=0.0):
    if v is None:
        return default
    try:
        val = float(v)
        return default if math.isnan(val) or math.isinf(val) else val
    except (TypeError, ValueError):
        return default


def calc_unrealized_pnl(pick):
    """Compute unrealized PnL % for an active pick."""
    # First check if unrealized_pnl_pct is already provided and non-zero
    stored = pick.get("unrealized_pnl_pct")
    if stored is not None and safe_float(stored) != 0.0:
        return safe_float(stored) * 100  # stored as decimal

    entry = safe_float(pick.get("entry_price"))
    current = safe_float(pick.get("current_price"))
    if entry == 0 or current == 0:
        return None  # No price data yet
    direction = pick.get("direction", "LONG").upper()
    if direction == "SHORT":
        return (entry - current) / entry * 100
    else:
        return (current - entry) / entry * 100


def calc_realized_pnl(pick):
    """Get realized PnL % from closed pick."""
    rp = pick.get("realized_pnl_pct")
    if rp is not None:
        return safe_float(rp)
    pp = pick.get("pnl_pct")
    if pp is not None:
        val = safe_float(pp)
        # Some are stored as decimals (0.xx), some as percentages
        if abs(val) < 1 and abs(val) > 0:
            return val * 100
        return val
    # Compute from prices
    entry = safe_float(pick.get("entry_price"))
    close = safe_float(pick.get("close_price") or pick.get("exit_price"))
    if entry == 0 or close == 0:
        return 0.0
    direction = pick.get("direction", "LONG").upper()
    if direction == "SHORT":
        return (entry - close) / entry * 100
    else:
        return (close - entry) / entry * 100


def sharpe_ratio(returns):
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance) if variance > 0 else 0
    return mean / std if std > 0 else 0.0


def sortino_ratio(returns):
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    neg = [r for r in returns if r < 0]
    if not neg:
        return float("inf") if mean > 0 else 0.0
    downside_var = sum(r ** 2 for r in neg) / len(neg)
    downside_dev = math.sqrt(downside_var) if downside_var > 0 else 0
    return mean / downside_dev if downside_dev > 0 else 0.0


def profit_factor(returns):
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = sum(r for r in returns if r < 0)
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / abs(gross_loss)


def normalize_asset_class(pick):
    ac = (pick.get("asset_class") or pick.get("category") or "unknown").upper()
    mapping = {
        "FUTURES": "Futures",
        "EQUITY": "Stock",
        "STOCK": "Stock",
        "FOREX": "Forex",
        "ETF": "ETF",
        "PENNY_STOCK": "Penny",
        "PENNY": "Penny",
        "BOND": "Bond",
        "COMMODITY": "Commodity",
    }
    return mapping.get(ac, ac.title())


def main():
    active = load_json(ACTIVE_FILE)
    closed = load_json(CLOSED_FILE)

    all_picks = active + closed
    total = len(all_picks)
    n_active = len(active)
    n_closed = len(closed)

    # Compute PnL for all (filter out None for picks without current price)
    active_pnls_raw = [calc_unrealized_pnl(p) for p in active]
    active_pnls = [x for x in active_pnls_raw if x is not None]
    closed_pnls = [calc_realized_pnl(p) for p in closed]
    all_pnls = active_pnls + closed_pnls

    # Win rate (closed only)
    wins = sum(1 for p in closed_pnls if p > 0)
    losses = sum(1 for p in closed_pnls if p <= 0)
    win_rate = (wins / n_closed * 100) if n_closed > 0 else 0

    n_no_price = sum(1 for x in active_pnls_raw if x is None)
    avg_pnl = sum(all_pnls) / len(all_pnls) if all_pnls else 0
    total_pnl = sum(all_pnls)
    avg_closed_pnl = sum(closed_pnls) / len(closed_pnls) if closed_pnls else 0

    sr = sharpe_ratio(closed_pnls)
    so = sortino_ratio(closed_pnls)
    pf = profit_factor(closed_pnls)

    # --- Strategy breakdown ---
    strat_data = defaultdict(lambda: {"picks": 0, "open": 0, "closed": 0, "wins": 0, "pnls": []})
    for p in active:
        s = p.get("strategy", "unknown")
        strat_data[s]["picks"] += 1
        strat_data[s]["open"] += 1
        pnl = calc_unrealized_pnl(p)
        if pnl is not None:
            strat_data[s]["pnls"].append(pnl)
    for p in closed:
        s = p.get("strategy", "unknown")
        strat_data[s]["picks"] += 1
        strat_data[s]["closed"] += 1
        pnl = calc_realized_pnl(p)
        strat_data[s]["pnls"].append(pnl)
        if pnl > 0:
            strat_data[s]["wins"] += 1

    disabled_strategies = {"vix_reversal"}

    # --- Asset class breakdown ---
    ac_data = defaultdict(lambda: {"picks": 0, "open": 0, "closed": 0, "wins": 0, "pnls": []})
    for p in active:
        ac = normalize_asset_class(p)
        ac_data[ac]["picks"] += 1
        ac_data[ac]["open"] += 1
        pnl = calc_unrealized_pnl(p)
        if pnl is not None:
            ac_data[ac]["pnls"].append(pnl)
    for p in closed:
        ac = normalize_asset_class(p)
        ac_data[ac]["picks"] += 1
        ac_data[ac]["closed"] += 1
        pnl = calc_realized_pnl(p)
        ac_data[ac]["pnls"].append(pnl)
        if pnl > 0:
            ac_data[ac]["wins"] += 1

    # --- Build active table rows sorted by PnL ---
    active_rows = []
    for p in active:
        pnl = calc_unrealized_pnl(p)
        active_rows.append({
            "symbol": p.get("symbol", "?"),
            "strategy": p.get("strategy", "?"),
            "asset_class": normalize_asset_class(p),
            "direction": p.get("direction", "?"),
            "entry": safe_float(p.get("entry_price")),
            "current": safe_float(p.get("current_price")),
            "tp": safe_float(p.get("take_profit")),
            "sl": safe_float(p.get("stop_loss")),
            "confidence": safe_float(p.get("confidence")) * 100,
            "pnl": pnl,
            "has_price": pnl is not None,
        })
    active_rows.sort(key=lambda x: (x["has_price"], x["pnl"] if x["pnl"] is not None else -999), reverse=True)

    # --- Build closed table rows sorted by PnL ---
    closed_rows = []
    for p in closed:
        pnl = calc_realized_pnl(p)
        close_reason = p.get("exit_reason") or p.get("close_reason") or "?"
        close_price = safe_float(p.get("exit_price") or p.get("close_price"))
        closed_rows.append({
            "symbol": p.get("symbol", "?"),
            "strategy": p.get("strategy", "?"),
            "asset_class": normalize_asset_class(p),
            "direction": p.get("direction", "?"),
            "entry": safe_float(p.get("entry_price")),
            "close": close_price,
            "pnl": pnl,
            "reason": close_reason,
        })
    closed_rows.sort(key=lambda x: x["pnl"], reverse=True)

    # --- vix_reversal stats for root cause ---
    vix_picks = [p for p in all_picks if p.get("strategy") == "vix_reversal"]
    vix_closed = [p for p in closed if p.get("strategy") == "vix_reversal"]
    vix_wins = sum(1 for p in vix_closed if calc_realized_pnl(p) > 0)
    vix_wr = (vix_wins / len(vix_closed) * 100) if vix_closed else 0
    vix_pct_of_total = len(vix_picks) / total * 100 if total > 0 else 0

    # --- Generate markdown ---
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append(f"# Multi-Asset Forward-Test Portfolio Performance Report")
    lines.append(f"")
    lines.append(f"**Generated:** {now_str}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # 1. Portfolio Summary
    lines.append(f"## 1. Portfolio Summary")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Picks | {total} |")
    lines.append(f"| Active (Open) | {n_active} |")
    lines.append(f"| Closed | {n_closed} |")
    lines.append(f"| Wins / Losses | {wins} / {losses} |")
    lines.append(f"| Win Rate (closed) | **{win_rate:.1f}%** |")
    lines.append(f"| Avg PnL (closed) | {avg_closed_pnl:.4f}% |")
    lines.append(f"| Total PnL (all) | {total_pnl:.4f}% |")
    lines.append(f"| Sharpe Ratio | {sr:.4f} |")
    lines.append(f"| Sortino Ratio | {so:.4f} |")
    lines.append(f"| Profit Factor | {pf:.4f} |")
    if n_no_price > 0:
        lines.append(f"| Active (awaiting price) | {n_no_price} |")
    lines.append(f"")

    # 2. CRITICAL ISSUES
    lines.append(f"## 2. CRITICAL ISSUES")
    lines.append(f"")
    lines.append(f"### Win Rate: {win_rate:.1f}% (Target: >50%)")
    lines.append(f"")
    lines.append(f"The portfolio launched during a severe market selloff (VIX spiked 39.4%) and immediately")
    lines.append(f"suffered from over-concentration in the `vix_reversal` strategy, which dominated {vix_pct_of_total:.0f}% of")
    lines.append(f"all picks with a disastrous {vix_wr:.1f}% win rate. The strategy has been **DISABLED** as of March 11.")
    lines.append(f"")
    lines.append(f"**Key problems identified:**")
    lines.append(f"- `vix_reversal` fired on every asset simultaneously during the VIX spike, creating massive correlated exposure")
    lines.append(f"- No strategy diversification cap existed -- one strategy could dominate the entire portfolio")
    lines.append(f"- No bounce/mean-reversion strategy was available to capitalize on oversold conditions")
    lines.append(f"- Trend filter (SMA200) blocked entries for legitimate dip-buying opportunities")
    lines.append(f"")

    # 3. Performance by Strategy
    lines.append(f"## 3. Performance by Strategy")
    lines.append(f"")
    lines.append(f"| Strategy | Picks | Open | Closed | Wins | Win Rate | Avg PnL% | Sharpe | Status |")
    lines.append(f"|----------|-------|------|--------|------|----------|----------|--------|--------|")
    for strat in sorted(strat_data.keys()):
        d = strat_data[strat]
        wr = (d["wins"] / d["closed"] * 100) if d["closed"] > 0 else 0
        avg = sum(d["pnls"]) / len(d["pnls"]) if d["pnls"] else 0
        sh = sharpe_ratio(d["pnls"]) if len(d["pnls"]) >= 2 else 0
        status = "DISABLED" if strat in disabled_strategies else "ACTIVE"
        lines.append(f"| {strat} | {d['picks']} | {d['open']} | {d['closed']} | {d['wins']} | {wr:.1f}% | {avg:.4f}% | {sh:.3f} | **{status}** |")
    lines.append(f"")

    # 4. Performance by Asset Class
    lines.append(f"## 4. Performance by Asset Class")
    lines.append(f"")
    lines.append(f"| Asset Class | Picks | Open | Closed | Wins | Win Rate | Avg PnL% | Total PnL% |")
    lines.append(f"|-------------|-------|------|--------|------|----------|----------|------------|")
    for ac in sorted(ac_data.keys()):
        d = ac_data[ac]
        wr = (d["wins"] / d["closed"] * 100) if d["closed"] > 0 else 0
        avg = sum(d["pnls"]) / len(d["pnls"]) if d["pnls"] else 0
        tot = sum(d["pnls"])
        lines.append(f"| {ac} | {d['picks']} | {d['open']} | {d['closed']} | {d['wins']} | {wr:.1f}% | {avg:.4f}% | {tot:.4f}% |")
    lines.append(f"")

    # 5. Active Picks
    lines.append(f"## 5. Active Picks ({n_active} open)")
    lines.append(f"")
    lines.append(f"| Symbol | Strategy | Class | Dir | Entry | Current | TP | SL | Conf | PnL% |")
    lines.append(f"|--------|----------|-------|-----|-------|---------|----|----|------|------|")
    for r in active_rows:
        current_str = f"{r['current']:.4f}" if r['current'] != 0 else "N/A"
        pnl_str = f"{r['pnl']:+.4f}%" if r['pnl'] is not None else "awaiting price"
        lines.append(
            f"| {r['symbol']} | {r['strategy']} | {r['asset_class']} | {r['direction']} "
            f"| {r['entry']:.4f} | {current_str} | {r['tp']:.4f} | {r['sl']:.4f} "
            f"| {r['confidence']:.0f}% | {pnl_str} |"
        )
    lines.append(f"")

    # 6. Closed Picks
    lines.append(f"## 6. Closed Picks ({n_closed} closed)")
    lines.append(f"")
    lines.append(f"| Symbol | Strategy | Class | Dir | Entry | Close | PnL% | Close Reason |")
    lines.append(f"|--------|----------|-------|-----|-------|-------|------|--------------|")
    for r in closed_rows:
        lines.append(
            f"| {r['symbol']} | {r['strategy']} | {r['asset_class']} | {r['direction']} "
            f"| {r['entry']:.4f} | {r['close']:.4f} | {r['pnl']:+.4f}% | {r['reason']} |"
        )
    lines.append(f"")

    # 7. Root Cause Analysis
    lines.append(f"## 7. Root Cause Analysis")
    lines.append(f"")
    lines.append(f"### Why performance is poor")
    lines.append(f"")
    lines.append(f"1. **`vix_reversal` dominated {vix_pct_of_total:.0f}% of all picks ({len(vix_picks)}/{total}) with {vix_wr:.1f}% win rate.**")
    lines.append(f"   The strategy fired on every available asset simultaneously during a single VIX spike event,")
    lines.append(f"   creating {len(vix_picks)} correlated LONG positions that all moved against the portfolio. Only")
    lines.append(f"   {vix_wins}/{len(vix_closed)} closed trades were profitable.")
    lines.append(f"")
    lines.append(f"2. **Trend filter blocked dip-buying entries.**")
    lines.append(f"   The SMA(200) trend filter, while designed to avoid buying into downtrends, prevented")
    lines.append(f"   legitimate mean-reversion entries during the selloff. Assets that briefly dipped below")
    lines.append(f"   their 200-day SMA could not be bought even at extreme oversold conditions.")
    lines.append(f"")
    lines.append(f"3. **No bounce/mean-reversion strategy existed.**")
    lines.append(f"   The initial strategy set lacked a dedicated extreme-oversold bounce strategy. The")
    lines.append(f"   `connors_rsi2` strategy existed but its SMA(200) requirement was too strict for crash")
    lines.append(f"   conditions. A new `extreme_oversold_bounce` strategy has since been added.")
    lines.append(f"")
    lines.append(f"4. **Over-concentration in a single strategy.**")
    lines.append(f"   No cap existed on how many picks a single strategy could generate. `vix_reversal`")
    lines.append(f"   produced {len(vix_picks)} picks in one scan cycle, dwarfing all other strategies combined.")
    lines.append(f"   A concentration cap of 30% per strategy has been deployed.")
    lines.append(f"")

    # 8. Fixes Deployed
    lines.append(f"## 8. Fixes Deployed (March 11, 2026)")
    lines.append(f"")
    lines.append(f"| # | Fix | Impact |")
    lines.append(f"|---|-----|--------|")
    lines.append(f"| 1 | **Disabled `vix_reversal` strategy** | Eliminates 49% of picks with 14.8% WR; all open vix_reversal positions closed |")
    lines.append(f"| 2 | **Added hyperopt-tuned `bollinger_mr`** | Backtested 73-92% WR across SPY, QQQ, GLD, AMZN, NZDUSD |")
    lines.append(f"| 3 | **Added hyperopt-tuned `connors_rsi2`** | Backtested 67-92% WR; relaxed SMA filter to SMA(150) |")
    lines.append(f"| 4 | **Added hyperopt-tuned `macd_div`** | Backtested 67-83% WR across forex and equity |")
    lines.append(f"| 5 | **Added `extreme_oversold_bounce`** | RSI(2)<5 + price<BB_lower; 3-day max hold; targets quick 1.5-3.5% mean reversion |")
    lines.append(f"| 6 | **Expanded forex pairs** | Added USDCAD, USDCHF, EURJPY to diversify asset class exposure |")
    lines.append(f"| 7 | **Relaxed dedup to 2 strategies/symbol** | Allows connors_rsi2 AND extreme_oversold_bounce on same symbol |")
    lines.append(f"| 8 | **Strategy concentration cap (30%)** | No single strategy can exceed 30% of active portfolio |")
    lines.append(f"")

    # 9. Hyperopt-Proven Strategies
    lines.append(f"## 9. Hyperopt-Proven Strategies (Top Performers)")
    lines.append(f"")
    lines.append(f"These strategies were optimized via hyperparameter optimization (hyperopt) on historical data:")
    lines.append(f"")
    lines.append(f"| Symbol | Strategy | Backtest WR | Key Parameters | Notes |")
    lines.append(f"|--------|----------|-------------|----------------|-------|")
    lines.append(f"| GLD | connors_rsi2 | **92.0%** | RSI(2)<20, SMA(100) | Gold mean-reversion |")
    lines.append(f"| AMZN | bollinger_mr | **92.3%** | BB(15,1.8), RSI<35 | High-beta bounce |")
    lines.append(f"| NZDUSD | bollinger_mr | **88.2%** | BB(20,2.0), RSI<30 | Forex mean-reversion |")
    lines.append(f"| SPY | connors_rsi2 | **86.7%** | RSI(2)<15, SMA(150) | Index dip-buy |")
    lines.append(f"| QQQ | connors_rsi2 | **83.3%** | RSI(2)<15, SMA(150) | Tech index dip-buy |")
    lines.append(f"| EURUSD | macd_div | **83.3%** | MACD(12,26,9), RSI<40 | Forex divergence |")
    lines.append(f"| SPY | bollinger_mr | **80.0%** | BB(20,1.5), RSI<25 | Tight Bollinger bounce |")
    lines.append(f"| GBPUSD | macd_div | **77.8%** | MACD(12,26,9), RSI<45 | Cable divergence |")
    lines.append(f"| QQQ | bollinger_mr | **76.9%** | BB(15,2.0), RSI<30 | Tech bounce |")
    lines.append(f"| USDJPY | connors_rsi2 | **73.3%** | RSI(2)<10, SMA(200) | Yen carry pullback |")
    lines.append(f"| IWM | bollinger_mr | **73.1%** | BB(20,2.2), RSI<35 | Small-cap bounce |")
    lines.append(f"| AUDUSD | connors_rsi2 | **67.0%** | RSI(2)<10, SMA(100) | AUD dip-buy |")
    lines.append(f"")

    # 10. Questions for External Review
    lines.append(f"## 10. Questions for External Review")
    lines.append(f"")
    lines.append(f"1. **Regime Filter:** Should we add a market regime classifier (bull/bear/chop) that adjusts")
    lines.append(f"   position sizing and strategy activation based on VIX levels, breadth, and trend?")
    lines.append(f"")
    lines.append(f"2. **TP/SL Ratios:** Current risk-reward ratios range from 0.3x to 2.0x. Should we enforce a")
    lines.append(f"   minimum 1.5x R:R across all strategies, or does the high win rate of mean-reversion")
    lines.append(f"   strategies justify tighter targets?")
    lines.append(f"")
    lines.append(f"3. **Short-Side Strategies:** Only `ema_stack_momentum` generates SHORT signals (1 pick: SOFI).")
    lines.append(f"   Should we add dedicated short strategies (e.g., RSI overbought fade, breakdown short)")
    lines.append(f"   to hedge long exposure during selloffs?")
    lines.append(f"")
    lines.append(f"4. **Hold Time Management:** `extreme_oversold_bounce` has a 3-day max hold. Should other")
    lines.append(f"   strategies have maximum hold times? Current `connors_rsi2` and `macd_divergence`")
    lines.append(f"   picks have no exit timer.")
    lines.append(f"")
    lines.append(f"5. **Position Sizing:** All picks are currently equal-weighted. Should we implement")
    lines.append(f"   confidence-weighted sizing (e.g., 95% confidence = full size, 65% = half size)?")
    lines.append(f"")
    lines.append(f"6. **Asset Class Caps:** Should we cap exposure per asset class (e.g., max 40% in ETFs,")
    lines.append(f"   max 30% in futures) to prevent concentration risk similar to the vix_reversal blowup?")
    lines.append(f"")
    lines.append(f"7. **Trailing Stops:** Should profitable positions use trailing stops (e.g., 2x ATR trail)")
    lines.append(f"   instead of fixed TP targets to let winners run?")
    lines.append(f"")
    lines.append(f"8. **Overfitting Risk:** Hyperopt strategies show 67-92% backtest WR. What is the expected")
    lines.append(f"   degradation in live trading? Should we apply a haircut (e.g., expect 60-75% live WR)")
    lines.append(f"   and size accordingly?")
    lines.append(f"")
    lines.append(f"9. **Crypto Integration:** The multi-asset scanner currently covers futures, stocks, forex,")
    lines.append(f"   ETFs, and penny stocks. Should we integrate crypto pairs (BTC, ETH, SOL) from the")
    lines.append(f"   existing alpha_engine/KIMI systems to further diversify?")
    lines.append(f"")
    lines.append(f"10. **Sample Size:** With only {n_closed} closed trades, statistical significance is limited.")
    lines.append(f"    How many closed trades do we need before making further strategy changes? (Suggestion:")
    lines.append(f"    minimum 50 closed trades per strategy before declaring it proven or disabling it.)")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*Report generated automatically by `multi_asset/gen_report.py`*")

    report = "\n".join(lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report written to {OUTPUT_FILE}")
    print(f"  Total picks: {total} (active: {n_active}, closed: {n_closed})")
    print(f"  Win rate: {win_rate:.1f}%  |  Sharpe: {sr:.4f}  |  Sortino: {so:.4f}  |  PF: {pf:.4f}")


if __name__ == "__main__":
    main()

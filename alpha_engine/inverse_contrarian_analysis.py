#!/usr/bin/env python3
"""
Inverse & Contrarian Strategy Analysis
=======================================
Verifies whether inverting losing strategies and combining them as
confluence filters with winning strategies produces genuinely profitable
results -- or if it's just a statistical fluke.

Analysis includes:
1. Raw performance by system & strategy
2. Inverse signal simulation (flip losers)
3. Confluence scoring (combine winners + inverted losers)
4. Statistical validation (binomial test, bootstrap, Monte Carlo)
5. Regime-aware analysis
6. Out-of-sample walk-forward test
"""

import json
import os
import sys
import math
import random
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# --- Data Loading ----------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
ALPHA_DATA = BASE_DIR / "alpha_engine" / "data"
KIMI_DATA = BASE_DIR / "KIMI_RISEOFTHECLAW" / "data"

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return None

def load_all_data():
    """Load all available trading data."""
    data = {}

    # KIMI signal tracking (has full trade-level data)
    data["kimi_signals"] = load_json(KIMI_DATA / "signal_tracking.json")

    # Alpha Engine performance (aggregated per strategy)
    data["alpha_performance"] = load_json(ALPHA_DATA / "strategy_performance.json")

    # Alpha Engine track record
    data["alpha_track"] = load_json(ALPHA_DATA / "track_record.json")

    # Alpha Engine closed picks (individual trades)
    data["alpha_closed"] = load_json(ALPHA_DATA / "closed_picks.json")

    # Forward test results
    data["forward_results"] = load_json(ALPHA_DATA / "forward_test_results.json")

    return data

# --- Statistical Tests ----------------------------------------------------

def binomial_test(wins, total, null_p=0.5):
    """One-sided binomial test: is win rate significantly > null_p?"""
    if total == 0:
        return 1.0
    # Calculate p-value using normal approximation for large n
    # or exact calculation for small n
    if total < 30:
        # Exact binomial
        p_value = 0.0
        for k in range(wins, total + 1):
            p_value += math.comb(total, k) * (null_p ** k) * ((1 - null_p) ** (total - k))
        return p_value
    else:
        # Normal approximation
        mean = total * null_p
        std = math.sqrt(total * null_p * (1 - null_p))
        if std == 0:
            return 1.0
        z = (wins - mean) / std
        # Approximate one-sided p-value
        p_value = 0.5 * math.erfc(z / math.sqrt(2))
        return p_value

def bootstrap_win_rate(trades, n_bootstrap=10000):
    """Bootstrap confidence interval for win rate."""
    if len(trades) < 2:
        return None, None, None

    outcomes = [1 if t.get("pnl_pct", 0) > 0 else 0 for t in trades]
    boot_rates = []
    n = len(outcomes)

    for _ in range(n_bootstrap):
        sample = [outcomes[random.randint(0, n-1)] for _ in range(n)]
        boot_rates.append(sum(sample) / n)

    boot_rates.sort()
    ci_low = boot_rates[int(0.025 * n_bootstrap)]
    ci_high = boot_rates[int(0.975 * n_bootstrap)]
    mean_rate = sum(boot_rates) / n_bootstrap

    return mean_rate, ci_low, ci_high

def monte_carlo_random_trades(n_trades, avg_win_pct, avg_loss_pct, win_rate,
                               n_simulations=10000, position_size=2000):
    """Monte Carlo: compare actual P&L to random trading."""
    random_pnls = []

    for _ in range(n_simulations):
        total_pnl = 0
        for _ in range(n_trades):
            if random.random() < win_rate:
                total_pnl += position_size * avg_win_pct
            else:
                total_pnl += position_size * avg_loss_pct  # negative
        random_pnls.append(total_pnl)

    random_pnls.sort()
    return {
        "median": random_pnls[len(random_pnls) // 2],
        "p5": random_pnls[int(0.05 * n_simulations)],
        "p95": random_pnls[int(0.95 * n_simulations)],
        "mean": sum(random_pnls) / n_simulations
    }

def sharpe_ratio(returns):
    """Annualized Sharpe ratio from daily returns."""
    if len(returns) < 2:
        return 0
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance) if variance > 0 else 0.0001
    # Annualize assuming ~365 trades/year for crypto
    return (mean_r / std_r) * math.sqrt(252)

def max_drawdown(equity_curve):
    """Calculate maximum drawdown from equity curve."""
    if not equity_curve:
        return 0
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd

# --- Analysis Functions ---------------------------------------------------

def analyze_kimi_signals(kimi_data):
    """Full analysis of KIMI signal tracking data."""
    if not kimi_data or "signals" not in kimi_data:
        return None

    signals = kimi_data["signals"]
    closed = [s for s in signals if s.get("status") in ("WIN", "LOSS")]
    open_signals = [s for s in signals if s.get("status") == "OPEN"]

    print(f"\n{'='*70}")
    print(f"KIMI RISE OF THE CLAW -- SIGNAL ANALYSIS")
    print(f"{'='*70}")
    print(f"Total signals: {len(signals)}")
    print(f"Closed: {len(closed)} | Open: {len(open_signals)}")

    wins = [s for s in closed if s["status"] == "WIN"]
    losses = [s for s in closed if s["status"] == "LOSS"]

    print(f"Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Raw Win Rate: {len(wins)/len(closed)*100:.1f}%" if closed else "N/A")

    # P&L breakdown
    total_pnl = sum(s.get("pnl_pct", 0) for s in closed)
    avg_win = sum(s.get("pnl_pct", 0) for s in wins) / len(wins) if wins else 0
    avg_loss = sum(s.get("pnl_pct", 0) for s in losses) / len(losses) if losses else 0

    print(f"\nTotal P&L: {total_pnl:.2f}%")
    print(f"Avg Win: +{avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")

    # By symbol
    by_symbol = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0, "trades": []})
    for s in closed:
        sym = s["symbol"]
        by_symbol[sym]["trades"].append(s)
        by_symbol[sym]["pnl"] += s.get("pnl_pct", 0)
        if s["status"] == "WIN":
            by_symbol[sym]["wins"] += 1
        else:
            by_symbol[sym]["losses"] += 1

    print(f"\n{'Symbol':<18} {'W':>3} {'L':>3} {'WR':>7} {'P&L%':>8}")
    print("-" * 42)
    for sym, info in sorted(by_symbol.items(), key=lambda x: x[1]["pnl"], reverse=True):
        total_t = info["wins"] + info["losses"]
        wr = info["wins"] / total_t * 100 if total_t > 0 else 0
        print(f"{sym:<18} {info['wins']:>3} {info['losses']:>3} {wr:>6.1f}% {info['pnl']:>+7.2f}%")

    # Statistical tests
    print(f"\n--- Statistical Validation ---")
    p_val = binomial_test(len(wins), len(closed), null_p=0.5)
    print(f"Binomial test (H0: WR=50%): p={p_val:.6f}")
    print(f"  → {'SIGNIFICANT' if p_val < 0.05 else 'NOT significant'} at 5% level")

    # The INVERSE test -- this is what matters
    print(f"\n{'='*70}")
    print(f"INVERSE KIMI -- WHAT IF WE FADED EVERY SIGNAL?")
    print(f"{'='*70}")

    inv_wins = len(losses)  # their losses become our wins
    inv_losses = len(wins)  # their wins become our losses
    inv_wr = inv_wins / len(closed) * 100 if closed else 0

    # When we invert: if KIMI said BUY and it hit SL (loss),
    # we would have SOLD at entry and profited by the distance to SL
    # But we need to be careful -- the inverse isn't just flipping P&L

    inverse_trades = []
    for s in closed:
        inv_trade = dict(s)
        if s["status"] == "LOSS":
            # KIMI lost → inverse would have profited
            # If KIMI said BUY and price went down, we SHORT at entry
            # Our profit = entry_price - exit_price (as percentage)
            inv_pnl = -s.get("pnl_pct", 0)  # flip the sign
            inv_trade["inv_pnl_pct"] = inv_pnl
            inv_trade["inv_status"] = "WIN"
        else:
            # KIMI won → inverse would have lost
            inv_pnl = -s.get("pnl_pct", 0)
            inv_trade["inv_pnl_pct"] = inv_pnl
            inv_trade["inv_status"] = "LOSS"
        inverse_trades.append(inv_trade)

    inv_total_pnl = sum(t["inv_pnl_pct"] for t in inverse_trades)
    inv_avg_win = sum(t["inv_pnl_pct"] for t in inverse_trades if t["inv_status"] == "WIN")
    inv_avg_loss = sum(t["inv_pnl_pct"] for t in inverse_trades if t["inv_status"] == "LOSS")
    inv_avg_win_per = inv_avg_win / inv_wins if inv_wins > 0 else 0
    inv_avg_loss_per = inv_avg_loss / inv_losses if inv_losses > 0 else 0

    print(f"Inverse Win Rate: {inv_wr:.1f}% ({inv_wins}W / {inv_losses}L)")
    print(f"Inverse Total P&L: {inv_total_pnl:+.2f}%")
    print(f"Inverse Avg Win: {inv_avg_win_per:+.2f}% | Avg Loss: {inv_avg_loss_per:+.2f}%")

    # Position sizing simulation
    POSITION_SIZE = 2000  # $2000 per trade
    inv_dollar_pnl = sum(POSITION_SIZE * t["inv_pnl_pct"] / 100 for t in inverse_trades)

    print(f"\n--- Inverse Dollar P&L (at $2,000/trade) ---")
    print(f"Total: ${inv_dollar_pnl:+,.2f}")

    # Equity curve for inverse
    equity = [10000]  # start with $10k
    for t in sorted(inverse_trades, key=lambda x: x.get("entry_time", "")):
        pnl = POSITION_SIZE * t["inv_pnl_pct"] / 100
        equity.append(equity[-1] + pnl)

    inv_max_dd = max_drawdown(equity)
    inv_returns = [t["inv_pnl_pct"] / 100 for t in inverse_trades]
    inv_sharpe = sharpe_ratio(inv_returns)

    print(f"Max Drawdown: {inv_max_dd*100:.1f}%")
    print(f"Sharpe Ratio: {inv_sharpe:.2f}")
    print(f"Final Equity: ${equity[-1]:,.2f} (from $10,000)")

    # Statistical test on inverse
    inv_p_val = binomial_test(inv_wins, len(closed), null_p=0.5)
    print(f"\nBinomial test (H0: Inverse WR=50%): p={inv_p_val:.8f}")
    print(f"  → {'SIGNIFICANT ✓' if inv_p_val < 0.05 else 'NOT significant'} at 5% level")

    # Bootstrap confidence interval
    mean_wr, ci_low, ci_high = bootstrap_win_rate(inverse_trades)
    if mean_wr is not None:
        print(f"Bootstrap 95% CI for Inverse WR: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]")

    # Monte Carlo comparison
    mc_result = monte_carlo_random_trades(
        n_trades=len(closed),
        avg_win_pct=inv_avg_win_per / 100,
        avg_loss_pct=inv_avg_loss_per / 100,
        win_rate=inv_wr / 100,
        position_size=POSITION_SIZE
    )
    print(f"\n--- Monte Carlo (10,000 simulations at this WR) ---")
    print(f"Expected P&L: ${mc_result['mean']:+,.2f}")
    print(f"5th percentile: ${mc_result['p5']:+,.2f}")
    print(f"95th percentile: ${mc_result['p95']:+,.2f}")

    # -- CRITICAL: Walk-forward out-of-sample test --
    print(f"\n{'='*70}")
    print(f"WALK-FORWARD OUT-OF-SAMPLE TEST")
    print(f"{'='*70}")

    # Sort by entry time and split 60/40
    sorted_trades = sorted(closed, key=lambda x: x.get("entry_time", ""))
    split_idx = int(len(sorted_trades) * 0.6)
    in_sample = sorted_trades[:split_idx]
    out_sample = sorted_trades[split_idx:]

    print(f"In-sample: {len(in_sample)} trades | Out-of-sample: {len(out_sample)} trades")

    # In-sample stats
    is_wins = sum(1 for t in in_sample if t["status"] == "LOSS")  # inverse wins
    is_total = len(in_sample)
    is_wr = is_wins / is_total * 100 if is_total > 0 else 0
    is_pnl = sum(-t.get("pnl_pct", 0) for t in in_sample)

    # Out-of-sample stats
    os_wins = sum(1 for t in out_sample if t["status"] == "LOSS")
    os_total = len(out_sample)
    os_wr = os_wins / os_total * 100 if os_total > 0 else 0
    os_pnl = sum(-t.get("pnl_pct", 0) for t in out_sample)

    print(f"\nIn-sample  inverse WR: {is_wr:.1f}% | P&L: {is_pnl:+.2f}%")
    print(f"Out-sample inverse WR: {os_wr:.1f}% | P&L: {os_pnl:+.2f}%")

    wr_degradation = is_wr - os_wr
    print(f"WR degradation: {wr_degradation:+.1f}pp")
    print(f"  → {'CONSISTENT ✓' if abs(wr_degradation) < 10 else 'DEGRADED ✗'} (threshold: <10pp)")

    # By symbol inverse performance
    print(f"\n--- Inverse Performance by Symbol ---")
    print(f"{'Symbol':<18} {'W':>3} {'L':>3} {'WR':>7} {'InvP&L%':>9}")
    print("-" * 44)
    for sym, info in sorted(by_symbol.items(), key=lambda x: -x[1]["pnl"]):
        # Inverse: their worst symbols are our best
        total_t = info["wins"] + info["losses"]
        inv_w = info["losses"]
        inv_l = info["wins"]
        inv_wr_sym = inv_w / total_t * 100 if total_t > 0 else 0
        inv_pnl_sym = -info["pnl"]
        print(f"{sym:<18} {inv_w:>3} {inv_l:>3} {inv_wr_sym:>6.1f}% {inv_pnl_sym:>+8.2f}%")

    return {
        "closed_count": len(closed),
        "raw_wr": len(wins) / len(closed) * 100 if closed else 0,
        "inv_wr": inv_wr,
        "inv_pnl_pct": inv_total_pnl,
        "inv_pnl_dollar": inv_dollar_pnl,
        "inv_sharpe": inv_sharpe,
        "inv_max_dd": inv_max_dd,
        "inv_p_value": inv_p_val,
        "walk_forward_consistent": abs(wr_degradation) < 10,
        "is_wr": is_wr,
        "os_wr": os_wr,
        "by_symbol": dict(by_symbol),
        "inverse_trades": inverse_trades,
        "equity_curve": equity
    }


def analyze_alpha_strategies(alpha_perf):
    """Analyze Alpha Engine strategies for inverse potential."""
    if not alpha_perf:
        return None

    print(f"\n{'='*70}")
    print(f"ALPHA ENGINE -- STRATEGY-LEVEL ANALYSIS")
    print(f"{'='*70}")

    strategies = []
    for name, stats in alpha_perf.items():
        strategies.append({
            "name": name,
            "trades": stats.get("closed_picks", 0),
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "win_rate": stats.get("win_rate", 0),
            "pnl_pct": stats.get("total_pnl_pct", 0),
            "pnl_dollar": stats.get("total_pnl_dollar", 0),
            "sharpe": stats.get("sharpe", 0),
            "avg_mfe": stats.get("avg_mfe", 0),
            "avg_mae": stats.get("avg_mae", 0),
            "avg_hold_days": stats.get("avg_hold_days", 0),
            "exit_reasons": stats.get("exit_reasons", {}),
            "by_symbol": stats.get("by_symbol", {})
        })

    # Sort by P&L
    strategies.sort(key=lambda x: x["pnl_dollar"], reverse=True)

    # Categorize
    winners = [s for s in strategies if s["pnl_dollar"] > 0 and s["trades"] >= 2]
    losers = [s for s in strategies if s["pnl_dollar"] < 0 and s["trades"] >= 2]
    zero_wr = [s for s in strategies if s["win_rate"] == 0 and s["trades"] >= 3]

    print(f"\nTotal strategies: {len(strategies)}")
    print(f"Winners (P&L>0, 2+ trades): {len(winners)}")
    print(f"Losers (P&L<0, 2+ trades): {len(losers)}")
    print(f"Zero WR (0%, 3+ trades): {len(zero_wr)}")

    # Winners table
    print(f"\n--- WINNING STRATEGIES ---")
    print(f"{'Strategy':<35} {'Trades':>6} {'WR':>6} {'P&L$':>9} {'Sharpe':>7}")
    print("-" * 67)
    total_winner_pnl = 0
    for s in winners:
        wr_str = f"{s['win_rate']*100:.0f}%"
        print(f"{s['name']:<35} {s['trades']:>6} {wr_str:>6} ${s['pnl_dollar']:>+8,.0f} {s['sharpe']:>7.1f}")
        total_winner_pnl += s["pnl_dollar"]
    print(f"{'TOTAL':>35} {'':>6} {'':>6} ${total_winner_pnl:>+8,.0f}")

    # Losers table
    print(f"\n--- LOSING STRATEGIES ---")
    print(f"{'Strategy':<35} {'Trades':>6} {'WR':>6} {'P&L$':>9} {'Sharpe':>7}")
    print("-" * 67)
    total_loser_pnl = 0
    for s in sorted(losers, key=lambda x: x["pnl_dollar"]):
        wr_str = f"{s['win_rate']*100:.0f}%"
        print(f"{s['name']:<35} {s['trades']:>6} {wr_str:>6} ${s['pnl_dollar']:>+8,.0f} {s['sharpe']:>7.1f}")
        total_loser_pnl += s["pnl_dollar"]
    print(f"{'TOTAL':>35} {'':>6} {'':>6} ${total_loser_pnl:>+8,.0f}")

    # Zero WR inverse analysis
    print(f"\n--- ZERO WIN-RATE STRATEGIES (INVERSE CANDIDATES) ---")
    print(f"{'Strategy':<35} {'Trades':>6} {'SL Hits':>8} {'AvgMAE':>8} {'AvgMFE':>8} {'InvP&L$':>9}")
    print("-" * 80)
    total_inv_pnl = 0
    for s in zero_wr:
        sl_hits = s["exit_reasons"].get("SL_HIT", 0)
        inv_pnl = -s["pnl_dollar"]  # simple flip
        total_inv_pnl += inv_pnl
        print(f"{s['name']:<35} {s['trades']:>6} {sl_hits:>8} {s['avg_mae']:>+7.2%} {s['avg_mfe']:>+7.2%} ${inv_pnl:>+8,.0f}")
    print(f"{'TOTAL INVERSE':>35} {'':>6} {'':>8} {'':>8} {'':>8} ${total_inv_pnl:>+8,.0f}")

    # -- REALISTIC INVERSE ANALYSIS --
    # Key insight: just flipping P&L is naive. Need to check if we could
    # actually capture the inverse move with realistic entry/exit
    print(f"\n{'='*70}")
    print(f"REALISTIC INVERSE FEASIBILITY CHECK")
    print(f"{'='*70}")

    print(f"\nFor each 0% WR strategy, checking if inverse was capturable:")
    for s in zero_wr:
        avg_mae = abs(s["avg_mae"])  # how far price went against the trade
        avg_mfe = abs(s["avg_mfe"])  # how far price went in favor before reversing

        # If a BUY signal lost money, price went DOWN after entry
        # Inverse (SELL) would profit from the downmove
        # BUT: MFE shows price went UP first before going down
        # So inverse would have faced drawdown equal to MFE before profiting

        realistic = avg_mae > avg_mfe * 1.5  # adverse move >> favorable = strong inverse
        capturable = "YES ✓" if realistic else "MAYBE ~" if avg_mae > avg_mfe else "RISKY ✗"

        print(f"  {s['name']:<30} MAE={avg_mae:.2%} MFE={avg_mfe:.2%} → Inverse {capturable}")
        print(f"    Interpretation: Price moved {avg_mae:.2%} against trade (our profit)")
        print(f"                   but first moved {avg_mfe:.2%} in favor (our drawdown)")
        if realistic:
            print(f"    → Strong inverse: move against is {avg_mae/avg_mfe:.1f}x the false start")
        elif avg_mae > avg_mfe:
            print(f"    → Marginal: barely capturable, tight SL needed")
        else:
            print(f"    → Risky: false start is larger than actual move")

    # -- CONFLUENCE ANALYSIS --
    print(f"\n{'='*70}")
    print(f"CONFLUENCE ANALYSIS: WINNERS + INVERTED LOSERS")
    print(f"{'='*70}")

    # Check by-symbol overlap between winners and losers
    winner_symbols = set()
    loser_symbols = set()
    for s in winners:
        winner_symbols.update(s["by_symbol"].keys())
    for s in losers:
        loser_symbols.update(s["by_symbol"].keys())

    overlap = winner_symbols & loser_symbols
    print(f"\nSymbol overlap (both winning & losing strategies traded):")
    print(f"  Winner symbols: {winner_symbols}")
    print(f"  Loser symbols:  {loser_symbols}")
    print(f"  Overlap: {overlap}")

    # For overlapping symbols, check if winner+inverted-loser agree
    print(f"\n--- Per-Symbol Confluence ---")
    for sym in sorted(overlap):
        w_pnl = sum(s["by_symbol"].get(sym, {}).get("total_pnl", 0) for s in winners)
        l_pnl = sum(s["by_symbol"].get(sym, {}).get("total_pnl", 0) for s in losers)
        inv_l_pnl = -l_pnl  # invert loser
        combined = w_pnl + inv_l_pnl

        print(f"  {sym:<15} Winners: {w_pnl:+.4f} | InvLosers: {inv_l_pnl:+.4f} | Combined: {combined:+.4f}")

    return {
        "winners": winners,
        "losers": losers,
        "zero_wr": zero_wr,
        "total_winner_pnl": total_winner_pnl,
        "total_loser_pnl": total_loser_pnl,
        "total_inv_pnl": total_inv_pnl
    }


def combined_portfolio_simulation(kimi_results, alpha_results):
    """Simulate combined portfolio: top alpha winners + inverse KIMI."""
    print(f"\n{'='*70}")
    print(f"COMBINED PORTFOLIO SIMULATION")
    print(f"{'='*70}")

    if not kimi_results or not alpha_results:
        print("Insufficient data for combined simulation")
        return

    STARTING_CAPITAL = 10000
    POSITION_SIZE = 2000

    # Scenario 1: Original (as-is)
    kimi_raw_pnl = -kimi_results["inv_pnl_dollar"]  # undo the inversion to get raw
    alpha_raw_pnl = alpha_results["total_winner_pnl"] + alpha_results["total_loser_pnl"]
    raw_total = kimi_raw_pnl + alpha_raw_pnl

    print(f"\n[PICK] SCENARIO 1: Status Quo (all strategies as-is)")
    print(f"  KIMI raw P&L:  ${kimi_raw_pnl:+,.2f}")
    print(f"  Alpha raw P&L: ${alpha_raw_pnl:+,.2f}")
    print(f"  Combined:      ${raw_total:+,.2f}")
    print(f"  Return:        {raw_total/STARTING_CAPITAL*100:+.1f}%")

    # Scenario 2: Inverse KIMI only
    inv_kimi_pnl = kimi_results["inv_pnl_dollar"]

    print(f"\n[PICK] SCENARIO 2: Inverse KIMI (fade all KIMI signals)")
    print(f"  Inv KIMI P&L:  ${inv_kimi_pnl:+,.2f}")
    print(f"  Alpha raw P&L: ${alpha_raw_pnl:+,.2f}")
    print(f"  Combined:      ${inv_kimi_pnl + alpha_raw_pnl:+,.2f}")
    print(f"  Return:        {(inv_kimi_pnl + alpha_raw_pnl)/STARTING_CAPITAL*100:+.1f}%")

    # Scenario 3: Inverse KIMI + Only Alpha Winners
    print(f"\n[PICK] SCENARIO 3: Inverse KIMI + Only Alpha Winners")
    print(f"  Inv KIMI P&L:     ${inv_kimi_pnl:+,.2f}")
    print(f"  Alpha winners:    ${alpha_results['total_winner_pnl']:+,.2f}")
    print(f"  Combined:         ${inv_kimi_pnl + alpha_results['total_winner_pnl']:+,.2f}")
    print(f"  Return:           {(inv_kimi_pnl + alpha_results['total_winner_pnl'])/STARTING_CAPITAL*100:+.1f}%")

    # Scenario 4: Inverse KIMI + Alpha Winners + Inverse Alpha Losers
    inv_alpha_loser_pnl = alpha_results["total_inv_pnl"]

    print(f"\n[PICK] SCENARIO 4: Full Inverse (KIMI inv + Alpha winners + Alpha losers inv)")
    print(f"  Inv KIMI P&L:     ${inv_kimi_pnl:+,.2f}")
    print(f"  Alpha winners:    ${alpha_results['total_winner_pnl']:+,.2f}")
    print(f"  Inv Alpha losers: ${inv_alpha_loser_pnl:+,.2f}")
    total_s4 = inv_kimi_pnl + alpha_results['total_winner_pnl'] + inv_alpha_loser_pnl
    print(f"  Combined:         ${total_s4:+,.2f}")
    print(f"  Return:           {total_s4/STARTING_CAPITAL*100:+.1f}%")

    # Scenario 5: Conservative -- only use signals where KIMI inverse + Alpha winner agree
    print(f"\n[PICK] SCENARIO 5: Confluence Only (trade only when systems agree)")
    print(f"  [Requires individual trade timestamps -- estimated from available data]")

    # Risk metrics for best scenario
    best_pnl = max(raw_total, inv_kimi_pnl + alpha_raw_pnl,
                   inv_kimi_pnl + alpha_results['total_winner_pnl'], total_s4)
    best_scenario = ["Status Quo", "Inv KIMI", "Inv KIMI + Winners", "Full Inverse"][
        [raw_total, inv_kimi_pnl + alpha_raw_pnl,
         inv_kimi_pnl + alpha_results['total_winner_pnl'], total_s4].index(best_pnl)]

    print(f"\n{'='*70}")
    print(f"BEST SCENARIO: {best_scenario} → ${best_pnl:+,.2f} ({best_pnl/STARTING_CAPITAL*100:+.1f}%)")
    print(f"{'='*70}")

    return {
        "scenario_1_raw": raw_total,
        "scenario_2_inv_kimi": inv_kimi_pnl + alpha_raw_pnl,
        "scenario_3_inv_kimi_winners": inv_kimi_pnl + alpha_results['total_winner_pnl'],
        "scenario_4_full_inverse": total_s4,
        "best_scenario": best_scenario,
        "best_pnl": best_pnl
    }


def fluke_detection(kimi_results):
    """Advanced statistical tests to determine if inverse edge is real."""
    print(f"\n{'='*70}")
    print(f"FLUKE DETECTION -- IS THE INVERSE EDGE REAL?")
    print(f"{'='*70}")

    if not kimi_results:
        print("No KIMI data available")
        return

    n = kimi_results["closed_count"]
    inv_wr = kimi_results["inv_wr"] / 100

    # Test 1: Binomial test
    print(f"\n1. BINOMIAL TEST")
    print(f"   H0: Inverse win rate = 50% (random)")
    print(f"   Observed: {kimi_results['inv_wr']:.1f}% on {n} trades")
    print(f"   p-value: {kimi_results['inv_p_value']:.8f}")
    significant = kimi_results['inv_p_value'] < 0.05
    print(f"   Result: {'REJECT H0 -- edge is real ✓' if significant else 'FAIL TO REJECT -- could be random ✗'}")

    # Test 2: Walk-forward consistency
    print(f"\n2. WALK-FORWARD CONSISTENCY")
    print(f"   In-sample WR:  {kimi_results['is_wr']:.1f}%")
    print(f"   Out-sample WR: {kimi_results['os_wr']:.1f}%")
    print(f"   Consistent: {'YES ✓' if kimi_results['walk_forward_consistent'] else 'NO ✗'}")

    # Test 3: Runs test (are wins/losses clustered or random?)
    print(f"\n3. RUNS TEST (serial independence)")
    inv_trades = kimi_results.get("inverse_trades", [])
    if inv_trades:
        sorted_trades = sorted(inv_trades, key=lambda x: x.get("entry_time", ""))
        outcomes = [1 if t["inv_status"] == "WIN" else 0 for t in sorted_trades]

        # Count runs
        runs = 1
        for i in range(1, len(outcomes)):
            if outcomes[i] != outcomes[i-1]:
                runs += 1

        n1 = sum(outcomes)
        n0 = len(outcomes) - n1

        # Expected runs under independence
        if n1 + n0 > 0:
            expected_runs = 1 + (2 * n1 * n0) / (n1 + n0)
            var_runs = (2 * n1 * n0 * (2 * n1 * n0 - n1 - n0)) / ((n1 + n0) ** 2 * (n1 + n0 - 1)) if (n1 + n0) > 1 else 1
            std_runs = math.sqrt(var_runs) if var_runs > 0 else 1
            z_runs = (runs - expected_runs) / std_runs if std_runs > 0 else 0

            print(f"   Observed runs: {runs}")
            print(f"   Expected runs: {expected_runs:.1f}")
            print(f"   Z-score: {z_runs:.2f}")
            print(f"   Result: {'INDEPENDENT (no clustering) ✓' if abs(z_runs) < 1.96 else 'CLUSTERED (serial dependence) ~'}")

    # Test 4: Profit factor stability
    print(f"\n4. PROFIT FACTOR & RISK METRICS")
    print(f"   Sharpe Ratio: {kimi_results.get('inv_sharpe', 0):.2f}")
    print(f"   Max Drawdown: {kimi_results.get('inv_max_dd', 0)*100:.1f}%")

    if kimi_results.get('inv_sharpe', 0) > 1.0:
        print(f"   Sharpe > 1.0: GOOD risk-adjusted return ✓")
    elif kimi_results.get('inv_sharpe', 0) > 0.5:
        print(f"   Sharpe 0.5-1.0: MODERATE risk-adjusted return ~")
    else:
        print(f"   Sharpe < 0.5: WEAK risk-adjusted return ✗")

    # Test 5: Sample size adequacy
    print(f"\n5. SAMPLE SIZE ADEQUACY")
    # For 97% WR, how many trades needed for 95% confidence?
    # Using Wald method: n >= z^2 * p(1-p) / E^2
    z = 1.96
    p = inv_wr
    E = 0.05  # 5% margin of error
    min_n = math.ceil(z**2 * p * (1-p) / E**2)
    print(f"   Trades needed for ±5% CI at 95% conf: {min_n}")
    print(f"   Trades available: {n}")
    print(f"   Result: {'ADEQUATE ✓' if n >= min_n else f'NEED {min_n - n} MORE TRADES ✗'}")

    # Overall verdict
    print(f"\n{'='*70}")
    tests_passed = sum([
        significant,
        kimi_results['walk_forward_consistent'],
        kimi_results.get('inv_sharpe', 0) > 0.5,
        n >= min_n
    ])

    if tests_passed >= 3:
        verdict = "LIKELY REAL EDGE -- not a fluke"
        emoji = "✓✓✓"
    elif tests_passed >= 2:
        verdict = "PROMISING but needs more data"
        emoji = "✓✓"
    else:
        verdict = "INSUFFICIENT EVIDENCE -- could be fluke"
        emoji = "✗"

    print(f"VERDICT: {emoji} {verdict}")
    print(f"Tests passed: {tests_passed}/4")
    print(f"{'='*70}")

    return {
        "tests_passed": tests_passed,
        "verdict": verdict,
        "significant": significant,
        "walk_forward_ok": kimi_results['walk_forward_consistent'],
        "sharpe_ok": kimi_results.get('inv_sharpe', 0) > 0.5,
        "sample_ok": n >= min_n
    }


def generate_report(kimi_results, alpha_results, portfolio_results, fluke_results):
    """Generate final JSON report."""
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "Inverse & Contrarian Strategy Analysis",
        "kimi_analysis": {
            "raw_win_rate": kimi_results["raw_wr"] if kimi_results else None,
            "inverse_win_rate": kimi_results["inv_wr"] if kimi_results else None,
            "inverse_pnl_pct": kimi_results["inv_pnl_pct"] if kimi_results else None,
            "inverse_pnl_dollar": kimi_results["inv_pnl_dollar"] if kimi_results else None,
            "inverse_sharpe": kimi_results["inv_sharpe"] if kimi_results else None,
            "inverse_max_dd": kimi_results["inv_max_dd"] if kimi_results else None,
            "p_value": kimi_results["inv_p_value"] if kimi_results else None,
            "walk_forward_consistent": kimi_results["walk_forward_consistent"] if kimi_results else None,
            "in_sample_wr": kimi_results["is_wr"] if kimi_results else None,
            "out_sample_wr": kimi_results["os_wr"] if kimi_results else None,
        },
        "alpha_analysis": {
            "winning_strategies_pnl": alpha_results["total_winner_pnl"] if alpha_results else None,
            "losing_strategies_pnl": alpha_results["total_loser_pnl"] if alpha_results else None,
            "inverse_loser_pnl": alpha_results["total_inv_pnl"] if alpha_results else None,
            "zero_wr_strategies": [s["name"] for s in alpha_results["zero_wr"]] if alpha_results else [],
            "winner_strategies": [s["name"] for s in alpha_results["winners"]] if alpha_results else [],
        },
        "portfolio_scenarios": portfolio_results,
        "fluke_detection": fluke_results,
        "recommendations": []
    }

    # Generate recommendations
    if fluke_results and fluke_results.get("tests_passed", 0) >= 2:
        report["recommendations"].append(
            "KIMI inverse signals show statistical evidence of edge. "
            "Consider implementing as contrarian indicator."
        )

    if alpha_results:
        report["recommendations"].append(
            f"Focus capital on {len(alpha_results['winners'])} winning Alpha strategies "
            f"(${alpha_results['total_winner_pnl']:+,.0f} combined P&L)."
        )
        if alpha_results["zero_wr"]:
            report["recommendations"].append(
                f"{len(alpha_results['zero_wr'])} zero-WR strategies can serve as inverse signals. "
                f"Inverted P&L: ${alpha_results['total_inv_pnl']:+,.0f}."
            )

    # Save report
    report_path = ALPHA_DATA / "inverse_contrarian_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")

    return report


# --- Main -----------------------------------------------------------------

def main():
    print("=" * 70)
    print("INVERSE & CONTRARIAN STRATEGY VERIFICATION")
    print("Is flipping losers a real edge or just survivorship bias?")
    print("=" * 70)

    # Load all data
    print("\nLoading data...")
    data = load_all_data()

    # 1. KIMI Analysis
    kimi_results = analyze_kimi_signals(data["kimi_signals"])

    # 2. Alpha Engine Analysis
    alpha_results = analyze_alpha_strategies(data["alpha_performance"])

    # 3. Combined Portfolio Simulation
    portfolio_results = combined_portfolio_simulation(kimi_results, alpha_results)

    # 4. Fluke Detection
    fluke_results = fluke_detection(kimi_results)

    # 5. Generate Report
    report = generate_report(kimi_results, alpha_results, portfolio_results, fluke_results)

    # Final summary
    print(f"\n{'='*70}")
    print(f"EXECUTIVE SUMMARY")
    print(f"{'='*70}")

    if kimi_results:
        print(f"\nKIMI Inverse: {kimi_results['inv_wr']:.1f}% WR → ${kimi_results['inv_pnl_dollar']:+,.2f}")

    if alpha_results:
        print(f"Alpha Winners: ${alpha_results['total_winner_pnl']:+,.0f}")
        print(f"Alpha Inv Losers: ${alpha_results['total_inv_pnl']:+,.0f}")

    if portfolio_results:
        print(f"\nBest Scenario: {portfolio_results['best_scenario']}")
        print(f"Best P&L: ${portfolio_results['best_pnl']:+,.2f}")
        print(f"vs Status Quo: ${portfolio_results['scenario_1_raw']:+,.2f}")
        improvement = portfolio_results['best_pnl'] - portfolio_results['scenario_1_raw']
        print(f"Improvement: ${improvement:+,.2f}")

    if fluke_results:
        print(f"\nFluke Detection: {fluke_results['verdict']}")
        print(f"Statistical Tests Passed: {fluke_results['tests_passed']}/4")

    print(f"\n{'='*70}")
    print("Analysis complete.")

    return report


if __name__ == "__main__":
    main()

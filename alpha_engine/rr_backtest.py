#!/usr/bin/env python3
"""
R:R Ratio Backtest — tests multiple scenarios on closed picks data.
Determines optimal TP width while keeping SL unchanged.
"""
import json
import random

DATA_DIR = "e:/findtorontoevents_antigravity.ca/alpha_engine/data"

with open(f"{DATA_DIR}/closed_picks.json") as f:
    data = json.load(f)

# Parse all picks with valid entry, TP, SL
picks = []
for p in data:
    entry = p.get("entry_price", 0)
    tp = p.get("take_profit", 0)
    sl = p.get("stop_loss", 0)
    if not (entry > 0 and tp > 0 and sl > 0):
        continue

    direction = p.get("signal_type", "BUY").upper()
    if direction in ("BUY", "LONG"):
        tp_dist_pct = (tp - entry) / entry
        sl_dist_pct = (entry - sl) / entry
    elif direction in ("SELL", "SHORT"):
        tp_dist_pct = (entry - tp) / entry
        sl_dist_pct = (sl - entry) / entry
    else:
        continue

    if sl_dist_pct <= 0 or tp_dist_pct <= 0:
        continue

    original_rr = tp_dist_pct / sl_dist_pct

    # Calculate MFE (max favorable excursion) from HWM
    hwm = p.get("high_water_mark", entry)
    if direction in ("BUY", "LONG"):
        mfe_pct = (hwm - entry) / entry if hwm > entry else 0
    else:
        mfe_pct = (entry - hwm) / entry if hwm < entry else 0

    exit_price = p.get("exit_price", 0)
    if exit_price > 0:
        if direction in ("BUY", "LONG"):
            actual_pnl_pct = (exit_price - entry) / entry
        else:
            actual_pnl_pct = (entry - exit_price) / entry
    else:
        actual_pnl_pct = p.get("pnl_pct", 0)

    if p.get("exit_reason") == "TP_HIT":
        mfe_pct = max(mfe_pct, actual_pnl_pct, tp_dist_pct)
    elif actual_pnl_pct > 0:
        mfe_pct = max(mfe_pct, actual_pnl_pct)

    picks.append({
        "exit_reason": p.get("exit_reason", ""),
        "direction": direction,
        "entry": entry,
        "tp_dist_pct": tp_dist_pct,
        "sl_dist_pct": sl_dist_pct,
        "original_rr": original_rr,
        "mfe_pct": mfe_pct,
        "actual_pnl_pct": actual_pnl_pct,
        "pnl_pct": p.get("pnl_pct", 0),
    })

avg_rr = sum(p["original_rr"] for p in picks) / len(picks)
print(f"Valid picks for backtest: {len(picks)}")
print(f"Average original R:R: {avg_rr:.2f}")


def simulate_scenario(picks, target_rr):
    """Simulate a single R:R scenario."""
    wins = 0
    losses = 0
    expired = 0
    win_pcts = []
    loss_pcts = []
    total_pnl = 0.0

    for p in picks:
        if target_rr is None:
            new_tp_dist = p["tp_dist_pct"]
        else:
            new_tp_dist = p["sl_dist_pct"] * target_rr

        sl_dist = p["sl_dist_pct"]
        exit_reason = p["exit_reason"]
        mfe = p["mfe_pct"]

        if exit_reason == "SL_HIT":
            losses += 1
            loss_pcts.append(-sl_dist * 100)
            total_pnl -= sl_dist * 100

        elif exit_reason in ("TIME_EXPIRY", "EXPIRED", "TRAILING_STOP"):
            if mfe >= new_tp_dist:
                wins += 1
                win_pcts.append(new_tp_dist * 100)
                total_pnl += new_tp_dist * 100
            else:
                actual = p["actual_pnl_pct"] * 100
                if actual > 0:
                    expired += 1
                    total_pnl += actual
                else:
                    losses += 1
                    loss_pcts.append(actual)
                    total_pnl += actual

        elif exit_reason == "TP_HIT":
            if mfe >= new_tp_dist:
                wins += 1
                win_pcts.append(new_tp_dist * 100)
                total_pnl += new_tp_dist * 100
            else:
                random.seed(42 + hash(str(p["entry"])))
                if random.random() < 0.40:
                    expired += 1
                    partial = p["actual_pnl_pct"] * 100 * 0.7
                    total_pnl += partial
                else:
                    losses += 1
                    loss_pcts.append(-sl_dist * 100)
                    total_pnl -= sl_dist * 100

    total_trades = wins + losses + expired
    wr = wins / total_trades * 100 if total_trades > 0 else 0
    avg_win = sum(win_pcts) / len(win_pcts) if win_pcts else 0
    avg_loss = sum(loss_pcts) / len(loss_pcts) if loss_pcts else 0
    expectancy = (wr / 100 * avg_win) + ((1 - wr / 100) * avg_loss)
    gross_win = sum(win_pcts)
    gross_loss = abs(sum(loss_pcts))
    pf = gross_win / gross_loss if gross_loss > 0 else 999

    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "expired": expired,
        "wr": wr,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "pf": pf,
        "total_pnl": total_pnl,
    }


# Test scenarios: original + fine-grained intermediate + wide
target_rrs = {
    "A (2:1 current)":  None,
    "A2 (2.25:1)":      2.25,
    "A3 (2.5:1)":       2.5,
    "A4 (2.75:1)":      2.75,
    "B (3:1)":          3.0,
    "C (3.5:1)":        3.5,
    "D (4:1 Qwen3)":    4.0,
}

results = {}
for name, target_rr in target_rrs.items():
    results[name] = simulate_scenario(picks, target_rr)

# Print comparison table
print()
hdr = (
    f"{'Scenario':<20} | {'Trades':>6} | {'Wins':>5} | {'Loss':>5} | "
    f"{'Exp':>4} | {'WR':>6} | {'Avg Win%':>9} | {'Avg Loss%':>10} | "
    f"{'Expect':>8} | {'PF':>5} | {'Total PnL%':>11}"
)
sep = "=" * len(hdr)
print(sep)
print(hdr)
print("-" * len(hdr))
for name, r in results.items():
    line = (
        f"{name:<20} | {r['trades']:>6} | {r['wins']:>5} | {r['losses']:>5} | "
        f"{r['expired']:>4} | {r['wr']:>5.1f}% | {r['avg_win']:>+8.2f}% | "
        f"{r['avg_loss']:>+9.2f}% | {r['expectancy']:>+7.3f}% | "
        f"{r['pf']:>5.2f} | {r['total_pnl']:>+10.1f}%"
    )
    print(line)
print(sep)

# Find winners
best_exp = max(results.items(), key=lambda x: x[1]["expectancy"])
best_pf = max(results.items(), key=lambda x: x[1]["pf"])
best_pnl = max(results.items(), key=lambda x: x[1]["total_pnl"])
print(f"\nBEST by expectancy:    {best_exp[0]} (expectancy={best_exp[1]['expectancy']:+.3f}%)")
print(f"BEST by profit factor: {best_pf[0]} (PF={best_pf[1]['pf']:.2f})")
print(f"BEST by total PnL:     {best_pnl[0]} (PnL={best_pnl[1]['total_pnl']:+.1f}%)")

# Save results
save_data = {
    "backtest_date": "2026-03-21",
    "total_picks_analyzed": len(picks),
    "avg_original_rr": round(avg_rr, 2),
    "scenarios": {},
}
for name, r in results.items():
    save_data["scenarios"][name] = {
        k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()
    }

# Determine optimal factors based on best scenario
best_name = best_exp[0]
# Extract R:R from best scenario name or use current
if best_name.startswith("A (2:1"):
    best_rr = avg_rr  # keep current
elif best_name.startswith("A2"):
    best_rr = 2.25
elif best_name.startswith("A3"):
    best_rr = 2.5
elif best_name.startswith("A4"):
    best_rr = 2.75
elif best_name.startswith("B"):
    best_rr = 3.0
elif best_name.startswith("C"):
    best_rr = 3.5
elif best_name.startswith("D"):
    best_rr = 4.0
else:
    best_rr = avg_rr

# For 1x and copytrader: use winning R:R
# For 20x: cap at one step below winning (more conservative due to leverage)
factor_1x = round(best_rr / avg_rr, 2)
conservative_rr = max(avg_rr, best_rr - 0.5)  # one step more conservative for 20x
factor_20x = round(conservative_rr / avg_rr, 2)
factor_ct = factor_1x

save_data["recommendation"] = {
    "best_scenario": best_exp[0],
    "best_expectancy": round(best_exp[1]["expectancy"], 4),
    "winning_rr": best_rr,
    "tp_widen_factor_1x": factor_1x,
    "tp_widen_factor_20x": factor_20x,
    "tp_widen_factor_copytrader": factor_ct,
    "note": f"Current avg R:R is {avg_rr:.2f}. Best scenario is {best_exp[0]}. "
            f"Factor of {factor_1x} widens TP from {avg_rr:.2f}:1 to {best_rr:.2f}:1.",
}

out_path = f"{DATA_DIR}/rr_backtest_results.json"
with open(out_path, "w") as f:
    json.dump(save_data, f, indent=2)

print(f"\nSaved results to {out_path}")
print(f"TP_WIDEN_FACTOR for 1x/copytrader: {factor_1x}")
print(f"TP_WIDEN_FACTOR for 20x: {factor_20x}")

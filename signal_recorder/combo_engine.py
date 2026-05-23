"""
Combo Backtester Engine — the WIN FINDER.

Tests every 2-way and 3-way combination of system signals:
  "When systems A+B both said BUY within the same 4h window, what was the 24h outcome?"

Outputs statistically significant winning combos with p-values.
"""
import json
import math
from itertools import combinations
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

from signal_recorder.db import get_db, save_combo_result

CONFLUENCE_WINDOW_MIN = 240  # 4 hours
EVAL_HORIZON_MIN = 1440  # 24 hours
MIN_TRADES = 5
P_VALUE_THRESHOLD = 0.05
WIN_THRESHOLD_PCT = 0.5

OUTPUT_PATH = Path(__file__).parent / "data" / "winning_combos.json"


def _binomial_p_value(wins, total, null_prob=0.50):
    if total == 0:
        return 1.0
    p_value = 0.0
    for k in range(wins, total + 1):
        binom_coeff = math.comb(total, k)
        p_value += binom_coeff * (null_prob ** k) * ((1 - null_prob) ** (total - k))
    return p_value


def _calc_sharpe(pnls):
    if len(pnls) < 2:
        return 0.0
    mean = sum(pnls) / len(pnls)
    variance = sum((x - mean) ** 2 for x in pnls) / (len(pnls) - 1)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    return round(mean / std * (252 ** 0.5), 2)


def find_winning_combos(max_combo_size=3):
    conn = get_db()

    rows = conn.execute("""
        SELECT sl.id, sl.timestamp, sl.symbol, sl.system_id, sl.signal,
               sl.price_at_signal, so.pnl_pct
        FROM signal_log sl
        JOIN signal_outcomes so ON so.signal_log_id = sl.id
        WHERE so.check_minutes = ?
          AND sl.signal IN ('BUY', 'SELL')
          AND sl.price_at_signal IS NOT NULL
        ORDER BY sl.timestamp
    """, (EVAL_HORIZON_MIN,)).fetchall()

    if not rows:
        print("No outcome data yet. Need signals + 24h of price tracking.")
        conn.close()
        return {"combos_tested": 0, "winners": []}

    buckets = defaultdict(list)
    for r in rows:
        ts = datetime.fromisoformat(r["timestamp"])
        bucket_key = (r["symbol"], ts.strftime("%Y%m%d_%H"))
        buckets[bucket_key].append(dict(r))

    all_systems = sorted(set(r["system_id"] for r in rows))
    print(f"Systems with outcome data: {len(all_systems)}: {all_systems}")
    print(f"Time buckets: {len(buckets)}")
    print(f"Total signals with outcomes: {len(rows)}")

    results = []
    combos_tested = 0

    for combo_size in range(2, max_combo_size + 1):
        for combo in combinations(all_systems, combo_size):
            combo_key = "+".join(sorted(combo))
            for direction in ("BUY", "SELL"):
                trades_pnl = []

                for bucket_key, signals in buckets.items():
                    systems_in_bucket = {}
                    for sig in signals:
                        if sig["signal"] == direction and sig["system_id"] in combo:
                            systems_in_bucket[sig["system_id"]] = sig

                    if len(systems_in_bucket) == len(combo):
                        avg_pnl = sum(s["pnl_pct"] for s in systems_in_bucket.values()) / len(systems_in_bucket)
                        trades_pnl.append(avg_pnl)

                combos_tested += 1
                if len(trades_pnl) < MIN_TRADES:
                    continue

                wins = sum(1 for p in trades_pnl if p > WIN_THRESHOLD_PCT)
                losses = len(trades_pnl) - wins
                win_rate = wins / len(trades_pnl) if trades_pnl else 0
                avg_pnl = sum(trades_pnl) / len(trades_pnl)
                sharpe = _calc_sharpe(trades_pnl)
                p_value = _binomial_p_value(wins, len(trades_pnl))

                save_combo_result(
                    conn, combo_key=combo_key, direction=direction,
                    window_minutes=CONFLUENCE_WINDOW_MIN,
                    total=len(trades_pnl), wins=wins, losses=losses,
                    win_rate=win_rate, avg_pnl=avg_pnl,
                    sharpe=sharpe, p_value=p_value,
                )

                if p_value < P_VALUE_THRESHOLD and win_rate > 0.55:
                    results.append({
                        "combo": combo_key,
                        "direction": direction,
                        "trades": len(trades_pnl),
                        "wins": wins,
                        "win_rate": round(win_rate * 100, 1),
                        "avg_pnl": round(avg_pnl, 2),
                        "sharpe": sharpe,
                        "p_value": round(p_value, 4),
                    })

    results.sort(key=lambda x: x["p_value"])

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "combos_tested": combos_tested,
        "winners": results,
        "confluence_window_min": CONFLUENCE_WINDOW_MIN,
        "eval_horizon_min": EVAL_HORIZON_MIN,
        "min_trades": MIN_TRADES,
        "p_value_threshold": P_VALUE_THRESHOLD,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    conn.close()
    print(f"\nCombos tested: {combos_tested}")
    print(f"Winning combos found: {len(results)}")
    for r in results[:10]:
        print(f"  {r['combo']} {r['direction']}: {r['win_rate']}% WR, "
              f"{r['trades']} trades, p={r['p_value']}, Sharpe={r['sharpe']}")

    return output


if __name__ == "__main__":
    find_winning_combos()

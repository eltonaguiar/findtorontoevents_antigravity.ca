"""
Strategy Health Monitor for ML Battleground.
Auto-disables strategies that are consistently losing.
Persists state to shared/data/strategy_health.json.

Rules:
  - A strategy is DISABLED if it has >= min_trades AND:
    - Win rate < 30% over last 10 trades, OR
    - All last 5 trades are losses, OR
    - Expectancy < -0.5% over last 10 trades
  - A strategy is RE-ENABLED (probation) if:
    - Last 3 trades include at least 1 win
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HEALTH_FILE = os.path.join(DATA_DIR, "strategy_health.json")


def _load_health_state() -> dict:
    """Load persisted strategy health state."""
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"disabled": {}, "probation": {}, "updated": None}


def _save_health_state(state: dict):
    """Persist strategy health state."""
    os.makedirs(DATA_DIR, exist_ok=True)
    state["updated"] = datetime.now(timezone.utc).isoformat()
    with open(HEALTH_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_disabled_strategies(closed_picks: list, min_trades: int = 3) -> set:
    """
    Return set of strategy names that should be disabled.

    A strategy is disabled if:
    - It has >= min_trades closed trades AND
    - Win rate < 30% over last 10 trades OR
    - All last 3 trades are losses (was 5 — too slow to react) OR
    - Expectancy < -0.5% over last 10 trades

    A strategy is re-enabled (probation) if:
    - Last 3 trades include at least 1 win
    """
    # Group trades by strategy
    strategy_trades = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "unknown")
        pnl = pick.get("net_pnl_pct", pick.get("pnl_pct", pick.get("gross_pnl_pct", 0)))
        if pnl is None:
            pnl = 0
        strategy_trades.setdefault(strat, []).append(float(pnl))

    state = _load_health_state()
    disabled = set()
    new_disabled = {}
    new_probation = {}

    for strat, pnls in strategy_trades.items():
        n = len(pnls)
        if n < min_trades:
            continue

        last_10 = pnls[-10:]
        last_5 = pnls[-5:]
        last_3 = pnls[-3:]

        # Check disable conditions
        wins_10 = sum(1 for p in last_10 if p > 0)
        wr_10 = wins_10 / len(last_10)
        expectancy_10 = sum(last_10) / len(last_10)
        all_last_3_losses = all(p <= 0 for p in last_3)  # react faster: 3 consecutive losses

        should_disable = False
        disable_reason = ""

        if wr_10 < 0.30:
            should_disable = True
            disable_reason = f"Win rate {wr_10:.0%} < 30% over last {len(last_10)} trades"
        elif all_last_3_losses:
            should_disable = True
            disable_reason = f"All last 3 trades are losses (fast disable)"
        elif expectancy_10 < -0.5:
            should_disable = True
            disable_reason = f"Expectancy {expectancy_10:.2f}% < -0.5% over last {len(last_10)} trades"

        # Check re-enable condition (probation)
        has_recent_win = any(p > 0 for p in last_3)

        if should_disable and not has_recent_win:
            disabled.add(strat)
            new_disabled[strat] = {
                "reason": disable_reason,
                "trades": n,
                "wr_last_10": round(wr_10, 4),
                "expectancy_last_10": round(expectancy_10, 4),
                "disabled_at": state.get("disabled", {}).get(strat, {}).get(
                    "disabled_at", datetime.now(timezone.utc).isoformat()
                ),
            }
        elif should_disable and has_recent_win:
            # Probation: was bad but showing signs of life
            new_probation[strat] = {
                "reason": f"Re-enabled on probation (1+ win in last 3 trades)",
                "original_reason": disable_reason,
                "trades": n,
                "wr_last_10": round(wr_10, 4),
            }

    # Update persisted state
    state["disabled"] = new_disabled
    state["probation"] = new_probation
    _save_health_state(state)

    if disabled:
        print(f"  [strategy_health] DISABLED strategies: {disabled}")
    if new_probation:
        print(f"  [strategy_health] PROBATION strategies: {set(new_probation.keys())}")

    return disabled


def filter_signals_by_health(signals: list, closed_picks: list, min_trades: int = 5) -> list:
    """
    Filter out signals from disabled strategies.
    Convenience wrapper: computes disabled set and filters in one call.
    Returns filtered list of signals.
    """
    disabled = get_disabled_strategies(closed_picks, min_trades)
    if not disabled:
        return signals

    filtered = []
    for sig in signals:
        strat = sig.get("strategy", "unknown")
        if strat in disabled:
            print(f"    [health-gate] {sig.get('symbol', '?')} {strat}: BLOCKED (strategy disabled)")
        else:
            filtered.append(sig)

    if len(filtered) < len(signals):
        print(f"  [strategy_health] Filtered {len(signals) - len(filtered)} signals from disabled strategies")

    return filtered

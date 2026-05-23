"""
COMMODITY Inverse Kill Switch — Automatic detection and blocking of toxic
inverse-COMMODITY strategies.

P0 Implementation per PER-ASSET-CLASS SWARM ANALYSIS (Buffy, 2026-05-07).
All 3 swarm engines (DeepSeek, xAI, Cerebras) agreed: inverse COMMODITY
strategies are value-destroying with negative forward Sharpe.

Rules:
  1. PF < 0.9 after 20+ trades → Auto-disable
  2. Decay > 15pp from all-time to rolling-30d WR → Probation then kill
  3. 0% WR on 15+ trades → Immediate hard-block
  4. COMMODITY asset_class + inverse-direction signal → hard-block

Integration:
  - Called by feed_hygiene.is_valid_active_pick() for every COMMODITY pick
  - Updates strategy_blocklist dynamically
  - Logs all kills to audit_trail for forensic review

Rollback:
  - Set env COMMODITY_INVERSE_KILL_DISABLED=1 to bypass all rules
  - Individual strategies can be unblocked by removing from _RETIRED_STRATEGIES

Reference: swarm_runs/asset-class-swarm-20260507T215709Z/
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Kill thresholds per swarm analysis
_PF_KILL_THRESHOLD = 0.9
_DECAY_KILL_THRESHOLD = 0.15  # 15 percentage points
_MIN_TRADES_FOR_PF_KILL = 20
_MIN_TRADES_FOR_DECAY_KILL = 15
_MIN_TRADES_FOR_ZERO_WR_KILL = 15

# Rollback flag
_COMMODITY_INVERSE_KILL_DISABLED = os.getenv("COMMODITY_INVERSE_KILL_DISABLED", "0") == "1"

# Known toxic COMMODITY strategies from swarm analysis
# These are immediately blocked without waiting for threshold breach
_KNOWN_TOXIC_COMMODITY_STRATEGIES = frozenset({
    "commodity_inverse_momentum",      # inverse of best commodity momentum — destroys value
    "commodity_inverse_mean_reversion",
    "commodity_short_only",
    "commodity_inverse_trend",
    "inverse_commodity_momentum",
    "cta_commodity_momentum_term",     # already in _RETIRED_STRATEGIES — add here for completeness
})

# Inverse direction indicators in strategy names
_INVERSE_INDICATORS = frozenset({
    "inverse", "short_only", "inverse_", "inv_", "short_", "bearish",
    "downside",    "neg_", "contrarian", "mean_reversion_short",
    "reversion_short", "momentum_short", "terminal decline",
    "downside_protection", "short_momentum",
})


def _load_strategy_performance() -> Dict[str, Dict]:
    """
    Load strategy performance data from closed_picks analysis.

    Returns:
        Dict mapping strategy_name -> performance_metrics
    """
    data_paths = [
        Path("alpha_engine/data/strategy_performance.json"),
        Path("audit_trail/data/universal_resolved_picks.json"),
        Path("alpha_engine/data/closed_picks.json"),
    ]

    for path in data_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    if 'strategies' in data:
                        return data['strategies']
                    elif isinstance(data, dict):
                        return data
                    elif isinstance(data, list):
                        return _compute_strategy_stats_from_picks(data)
            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}")
                continue

    return {}


def _compute_strategy_stats_from_picks(picks: List[Dict]) -> Dict[str, Dict]:
    """Compute strategy statistics from a list of closed picks."""
    stats = {}

    for pick in picks:
        strategy = pick.get('strategy', 'unknown')
        if strategy not in stats:
            stats[strategy] = {
                'trades': [],
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'asset_class': pick.get('asset_class', 'UNKNOWN'),
            }

        s = stats[strategy]
        s['trades'].append(pick)

        pnl = pick.get('pnl_pct', 0)
        s['total_pnl'] += pnl

        win = pick.get('win', pnl > 0)
        if win:
            s['wins'] += 1
        else:
            s['losses'] += 1

    for strategy, s in stats.items():
        total = s['wins'] + s['losses']
        s['n_closed'] = total
        s['win_rate'] = s['wins'] / total if total > 0 else 0
        s['avg_pnl'] = s['total_pnl'] / total if total > 0 else 0
        s['profit_factor'] = _compute_profit_factor(s['trades'])
        s['decay_pp'] = _compute_decay(s['trades'])

    return stats


def _compute_profit_factor(trades: List[Dict]) -> float:
    """Compute profit factor (gross profits / gross losses)."""
    gross_profit = sum(t.get('pnl_pct', 0) for t in trades if t.get('pnl_pct', 0) > 0)
    gross_loss = abs(sum(t.get('pnl_pct', 0) for t in trades if t.get('pnl_pct', 0) < 0))

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 1.0

    return gross_profit / gross_loss


def _compute_decay(trades: List[Dict]) -> float:
    """
    Compute decay in percentage points (all-time WR vs rolling-30d WR).

    Returns:
        Decay in percentage points (e.g., 0.15 = 15pp)
    """
    if len(trades) < 30:
        return 0.0

    sorted_trades = sorted(
        trades,
        key=lambda t: t.get('closed_at', t.get('created_at', '')),
        reverse=True
    )

    all_time_wr = sum(1 for t in trades if t.get('win', t.get('pnl_pct', 0) > 0)) / len(trades)

    recent_trades = sorted_trades[:30]
    recent_wr = sum(1 for t in recent_trades if t.get('win', t.get('pnl_pct', 0) > 0)) / len(recent_trades)

    return all_time_wr - recent_wr


def is_commodity_strategy(strategy_name: str) -> bool:
    """
    Detect if a strategy is COMMODITY-focused based on naming conventions.

    Args:
        strategy_name: Name of the strategy

    Returns:
        True if strategy appears to be COMMODITY-focused
    """
    if not strategy_name:
        return False

    exact_indicators = frozenset({'commodity', 'gold', 'silver', 'oil', 'crude', 'natgas', 'natural_gas'})
    commodity_roots = frozenset({'commodity_', 'commodity-'})
    futures_roots = frozenset({'futures_', 'futures-'})

    name_lower = strategy_name.lower()
    parts = frozenset(name_lower.replace('-', '_').split('_'))

    if parts & exact_indicators:
        return True

    if any(root in name_lower for root in ['commodity_', 'commodity-']):
        return True

    if any(root in name_lower for root in ['futures_', 'futures-']):
        return True

    return False


def is_inverse_strategy(strategy_name: str) -> bool:
    """
    Detect if a strategy has inverse/momentum-short directionality in its name.

    Args:
        strategy_name: Name of the strategy

    Returns:
        True if strategy name contains inverse-direction indicators
    """
    if not strategy_name:
        return False

    name_lower = strategy_name.lower()

    if any(ind in name_lower for ind in _INVERSE_INDICATORS):
        return True

    parts = frozenset(name_lower.replace('-', '_').split('_'))
    if parts & _INVERSE_INDICATORS:
        return True

    return False


def is_commodity_inverse_strategy(strategy_name: str) -> bool:
    """
    Detect if a strategy is a COMMODITY-focused inverse strategy.

    This is the conjunction check: both COMMODITY affinity AND inverse direction.
    Such strategies are the primary kill targets per the 3-engine swarm consensus.

    Args:
        strategy_name: Name of the strategy

    Returns:
        True if strategy is COMMODITY + inverse direction
    """
    return is_commodity_strategy(strategy_name) and is_inverse_strategy(strategy_name)


def check_strategy_for_kill(
    strategy_name: str,
    stats: Optional[Dict] = None,
    asset_class: str = ""
) -> Tuple[bool, str]:
    """
    Check if a strategy should be killed based on COMMODITY inverse kill rules.

    Args:
        strategy_name: Name of the strategy
        stats: Optional pre-computed strategy stats
        asset_class: Asset class of the pick (e.g. 'COMMODITY')

    Returns:
        Tuple of (should_kill, reason)
    """
    if _COMMODITY_INVERSE_KILL_DISABLED:
        return False, "Kill switch disabled via COMMODITY_INVERSE_KILL_DISABLED=1"

    name = str(strategy_name or "").strip()

    # Check known toxic list (immediate hard-block)
    if name in _KNOWN_TOXIC_COMMODITY_STRATEGIES:
        return True, f"Known toxic COMMODITY strategy (hard-blocked per swarm analysis)"

    # Primary check: COMMODITY asset class + inverse naming
    if asset_class.upper() == "COMMODITY" and is_inverse_strategy(name):
        return True, f"COMMODITY asset_class + inverse naming — swarm consensus kill"

    # Secondary check: any strategy that is both commodity-focused AND inverse-named
    if is_commodity_inverse_strategy(name):
        return True, f"Strategy is COMMODITY-focused with inverse directionality"

    # Dynamic rules — load stats if not provided
    if stats is None:
        all_stats = _load_strategy_performance()
        stats = all_stats.get(name, {})

    if not stats:
        return False, "No performance data available"

    n_closed = stats.get('n_closed', 0)
    pf = stats.get('profit_factor', 0)
    wr = stats.get('win_rate', 0)
    decay_pp = stats.get('decay_pp', 0)

    # Evaluate the raw rule-based kill verdict first, then gate it (M-055).
    _rule_kill, _rule_reason = False, ""
    # Rule 1: 0% WR on 15+ trades
    if n_closed >= _MIN_TRADES_FOR_ZERO_WR_KILL and wr == 0:
        _rule_kill, _rule_reason = True, (
            f"Zero WR on {n_closed} trades (minimum {_MIN_TRADES_FOR_ZERO_WR_KILL})")
    # Rule 2: PF < 0.9 after 20+ trades
    elif n_closed >= _MIN_TRADES_FOR_PF_KILL and pf < _PF_KILL_THRESHOLD:
        _rule_kill, _rule_reason = True, (
            f"PF {pf:.2f} < {_PF_KILL_THRESHOLD} on {n_closed} trades")
    # Rule 3: Decay > 15pp from all-time to rolling-30d
    elif n_closed >= _MIN_TRADES_FOR_DECAY_KILL and decay_pp > _DECAY_KILL_THRESHOLD:
        _rule_kill, _rule_reason = True, (
            f"Decay {decay_pp*100:.1f}pp > {_DECAY_KILL_THRESHOLD*100}pp threshold")

    if not _rule_kill:
        return False, "Strategy passes all COMMODITY inverse kill rules"

    # ── M-055 minimum-sample gate ────────────────────────────────────────
    # A kill of ANY kind (WR / PF / decay) requires a minimum resolved
    # sample. Below that floor the verdict is statistically meaningless —
    # this is the Phase-2-D failure mode (CT=F killed on n=12, CL=F on n=6).
    # Only the min-n check from kill_gate is applied here: the binomial /
    # Wilson WR test would be a category error against PF- and decay-based
    # rules. The gate only ever makes kills MORE conservative — safe
    # default-on. Override: M055_KILL_GATE_ENABLED=0.
    if os.environ.get("M055_KILL_GATE_ENABLED", "1") != "0":
        try:
            from audit_trail.kill_gate import MIN_N_BY_ASSET_CLASS, MIN_N_DEFAULT
            _min_n = MIN_N_BY_ASSET_CLASS.get("COMMODITY", MIN_N_DEFAULT)
            if int(n_closed) < _min_n:
                return False, (
                    f"kill_gate override (INSUFFICIENT_EVIDENCE): rule said "
                    f"'{_rule_reason}' but n={n_closed} < min_n={_min_n} "
                    f"(Phase-2-D mis-kill class)")
        except ImportError:
            pass  # kill_gate sidecar unavailable — fall through to rule verdict

    return True, _rule_reason


def get_killed_strategies() -> Set[str]:
    """
    Get the set of all strategies that should be killed based on current data.

    Returns:
        Set of strategy names to block
    """
    killed = set(_KNOWN_TOXIC_COMMODITY_STRATEGIES)

    if _COMMODITY_INVERSE_KILL_DISABLED:
        logger.warning("COMMODITY_INVERSE_KILL_DISABLED=1 - not checking dynamic kills")
        return killed

    all_stats = _load_strategy_performance()

    for strategy_name, stats in all_stats.items():
        if not is_commodity_strategy(strategy_name):
            continue

        should_kill, reason = check_strategy_for_kill(strategy_name, stats)
        if should_kill and strategy_name not in killed:
            logger.warning(f"COMMODITY Inverse Kill Switch: {strategy_name} - {reason}")
            killed.add(strategy_name)

    return killed


def log_kill_to_audit(strategy_name: str, reason: str) -> None:
    """
    Log a strategy kill to the audit trail for forensic review.

    Args:
        strategy_name: Strategy that was killed
        reason: Reason for the kill
    """
    audit_entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': 'COMMODITY_INVERSE_STRATEGY_KILLED',
        'strategy': strategy_name,
        'reason': reason,
        'kill_switch_version': '1.0.0',
    }

    audit_paths = [
        Path("audit_trail/data/commodity_kill_audit.jsonl"),
        Path("alpha_engine/data/commodity_kill_audit.jsonl"),
    ]

    for path in audit_paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
            logger.info(f"Logged COMMODITY kill to {path}")
            return
        except Exception as e:
            logger.warning(f"Failed to log to {path}: {e}")
            continue


def refresh_kill_list() -> List[str]:
    """
    Refresh the kill list by scanning all strategies.

    Returns:
        List of newly killed strategies
    """
    killed = get_killed_strategies()

    newly_killed = []
    for strategy in killed:
        should_kill, reason = check_strategy_for_kill(strategy)
        if should_kill:
            log_kill_to_audit(strategy, reason)
            newly_killed.append(strategy)

    if newly_killed:
        logger.warning(f"COMMODITY Inverse Kill Switch: {len(newly_killed)} strategies newly blocked: {newly_killed}")

    return newly_killed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("COMMODITY Inverse Kill Switch v1.0.0")
    print("=" * 60)

    killed = refresh_kill_list()

    print(f"\nTotal strategies blocked: {len(killed)}")
    print(f"Known toxic (hard-coded): {len(_KNOWN_TOXIC_COMMODITY_STRATEGIES)}")
    print(f"Dynamically detected: {len(killed) - len(_KNOWN_TOXIC_COMMODITY_STRATEGIES)}")
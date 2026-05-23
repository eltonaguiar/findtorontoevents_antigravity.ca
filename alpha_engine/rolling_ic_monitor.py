#!/usr/bin/env python3
"""
Rolling IC Monitor with Auto-Circuit Breaker (IDEA 7 from data audit)

Monitors Information Coefficient (IC) of strategy scores vs realized PnL.
Auto-pauses strategies when IC flips negative (predictive signal lost).

Data: ml_crypto_predictor had 365 trades with PF 0.00-0.14 before detection.
This would have auto-killed it BEFORE poisoning the portfolio.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scipy.stats import spearmanr
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("rolling_ic_monitor")

# Configuration
ROLLING_WINDOW_DAYS = 7  # Look back period for IC calculation
MIN_TRADES_FOR_IC = 20   # Minimum closed trades to calculate reliable IC
IC_NEGATIVE_THRESHOLD = -0.05  # IC < -0.05 = strategy has inverted signal
IC_WEAK_THRESHOLD = 0.05       # IC < 0.05 = strategy needs size reduction
ROLLING_SHARPE_NEGATIVE = 0    # Sharpe < 0 = auto-reduce sizing

_DATA_DIR = Path(__file__).resolve().parent / "data"


def load_closed_picks() -> list[dict]:
    """Load closed picks from all available sources."""
    picks = []
    
    # Source 1: alpha_engine closed picks
    closed_path = _DATA_DIR / "closed_picks.json"
    if closed_path.exists():
        try:
            with open(closed_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    picks.extend(data)
                elif isinstance(data, dict) and "picks" in data:
                    picks.extend(data["picks"])
        except Exception as e:
            log.warning(f"Failed to load closed_picks.json: {e}")
    
    # Source 2: audit_trail closed picks
    audit_path = Path(__file__).resolve().parent.parent / "audit_trail" / "data" / "closed_picks.csv"
    if audit_path.exists():
        try:
            import csv
            with open(audit_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    picks.append(row)
        except Exception as e:
            log.warning(f"Failed to load audit_trail closed picks: {e}")
    
    return picks


def calculate_rolling_ic(strategy_name: str, picks: list[dict], window_days: int = 7) -> tuple[float, int] | None:
    """Calculate rolling IC (Spearman correlation) for a strategy.
    
    Returns:
        (ic_value, n_trades) or None if insufficient data
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    
    # Filter to strategy and recent window
    strategy_picks = [
        p for p in picks
        if str(p.get("strategy", p.get("system", ""))).lower() == strategy_name.lower()
    ]
    
    # Parse entry_date and filter by window
    recent_picks = []
    for p in strategy_picks:
        entry_date = p.get("entry_date") or p.get("open_time") or p.get("timestamp")
        if entry_date:
            try:
                if isinstance(entry_date, str):
                    entry_dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
                else:
                    entry_dt = entry_date
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                if entry_dt >= cutoff:
                    recent_picks.append(p)
            except Exception:
                continue
    
    n = len(recent_picks)
    if n < MIN_TRADES_FOR_IC:
        return None
    
    # Extract scores and PnL
    scores = []
    pnls = []
    for p in recent_picks:
        # Score can be in multiple fields
        score = p.get("score") or p.get("elite_score") or p.get("smart_score") or p.get("validated_score")
        pnl = p.get("pnl_pct") or p.get("pnl") or p.get("pnl_percent")
        
        if score is not None and pnl is not None:
            try:
                scores.append(float(score))
                pnls.append(float(pnl))
            except (ValueError, TypeError):
                continue
    
    if len(scores) < MIN_TRADES_FOR_IC:
        return None
    
    # Calculate Spearman IC
    try:
        ic, p_value = spearmanr(scores, pnls)
        return (ic, len(scores))
    except Exception as e:
        log.warning(f"Failed to calculate IC for {strategy_name}: {e}")
        return None


def calculate_rolling_sharpe(strategy_name: str, picks: list[dict], window_days: int = 7) -> float | None:
    """Calculate rolling Sharpe ratio for a strategy."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    
    strategy_picks = [
        p for p in picks
        if str(p.get("strategy", p.get("system", ""))).lower() == strategy_name.lower()
    ]
    
    pnls = []
    for p in strategy_picks:
        entry_date = p.get("entry_date") or p.get("open_time") or p.get("timestamp")
        if entry_date:
            try:
                if isinstance(entry_date, str):
                    entry_dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
                else:
                    entry_dt = entry_date
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                if entry_dt >= cutoff:
                    pnl = p.get("pnl_pct") or p.get("pnl") or p.get("pnl_percent")
                    if pnl:
                        pnls.append(float(pnl))
            except Exception:
                continue
    
    if len(pnls) < 5:
        return None
    
    mean_pnl = sum(pnls) / len(pnls)
    variance = sum((x - mean_pnl) ** 2 for x in pnls) / len(pnls)
    std_pnl = variance ** 0.5
    
    if std_pnl == 0:
        return 0.0
    
    # Annualize: assume ~252 trading days, window is in days
    sharpe = (mean_pnl / std_pnl) * (252 / window_days) ** 0.5
    return sharpe


def get_strategy_circuit_breaker_status() -> dict:
    """Main function: Get circuit breaker status for all strategies.
    
    Returns:
        dict with keys: "paused", "reduced", "healthy", "details"
    """
    picks = load_closed_picks()
    
    # Group by strategy
    strategies = defaultdict(list)
    for p in picks:
        strat = str(p.get("strategy", p.get("system", ""))).lower()
        if strat:
            strategies[strat].append(p)
    
    result = {
        "paused": [],      # IC < -0.05, Sharpe < 0 - auto-pause
        "reduced": [],     # IC < 0.05 - reduce size by 50%
        "healthy": [],     # All good
        "details": {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    for strat, strat_picks in strategies.items():
        n = len(strat_picks)
        
        # Skip strategies with insufficient history
        if n < MIN_TRADES_FOR_IC:
            result["healthy"].append(strat)
            continue
        
        # Calculate metrics
        ic_result = calculate_rolling_ic(strat, picks, ROLLING_WINDOW_DAYS)
        sharpe = calculate_rolling_sharpe(strat, picks, ROLLING_WINDOW_DAYS)
        
        detail = {
            "n_trades": n,
            "ic": None,
            "ic_n": 0,
            "sharpe_7d": sharpe,
            "status": "unknown"
        }
        
        if ic_result:
            ic, ic_n = ic_result
            detail["ic"] = round(ic, 4)
            detail["ic_n"] = ic_n
            
            # Circuit breaker logic
            if ic < IC_NEGATIVE_THRESHOLD and n >= MIN_TRADES_FOR_IC:
                # IC flipped negative - auto-pause
                result["paused"].append(strat)
                detail["status"] = "PAUSED"
                detail["reason"] = f"IC {ic:.4f} < {IC_NEGATIVE_THRESHOLD} (inverted signal)"
            elif ic < IC_WEAK_THRESHOLD and n >= MIN_TRADES_FOR_IC:
                # IC below threshold - reduce sizing
                result["reduced"].append(strat)
                detail["status"] = "REDUCED"
                detail["reason"] = f"IC {ic:.4f} < {IC_WEAK_THRESHOLD} (weak signal)"
            else:
                result["healthy"].append(strat)
                detail["status"] = "HEALTHY"
        
        # Also check rolling Sharpe
        if sharpe is not None and sharpe < ROLLING_SHARPE_NEGATIVE and detail["status"] in ("HEALTHY", "unknown"):
            # Sharpe negative - reduce sizing
            result["reduced"].append(strat)
            detail["status"] = "REDUCED"
            detail["reason"] = f"7d Sharpe {sharpe:.2f} < 0 (negative momentum)"
        
        result["details"][strat] = detail
    
    log.info(f"IC Monitor: {len(result['paused'])} paused, {len(result['reduced'])} reduced, {len(result['healthy'])} healthy")
    return result


def get_paused_strategies() -> list[str]:
    """Get list of strategies that should be paused."""
    status = get_strategy_circuit_breaker_status()
    return status.get("paused", [])


def get_reduced_strategies() -> list[str]:
    """Get list of strategies that should have reduced sizing."""
    status = get_strategy_circuit_breaker_status()
    return status.get("reduced", [])


if __name__ == "__main__":
    status = get_strategy_circuit_breaker_status()
    print(f"\n=== Rolling IC Monitor Report ===")
    print(f"Timestamp: {status['timestamp']}")
    print(f"\nPAUSED (auto-kill): {status['paused']}")
    print(f"REDUCED (50% size): {status['reduced']}")
    print(f"HEALTHY: {len(status['healthy'])} strategies")
    
    if status["paused"]:
        print("\n--- PAUSED Strategy Details ---")
        for strat in status["paused"]:
            detail = status["details"].get(strat, {})
            print(f"  {strat}: IC={detail.get('ic')}, n={detail.get('n_trades')}, reason={detail.get('reason', 'N/A')}")
    
    if status["reduced"]:
        print("\n--- REDUCED Strategy Details ---")
        for strat in status["reduced"]:
            detail = status["details"].get(strat, {})
            print(f"  {strat}: IC={detail.get('ic')}, Sharpe7d={detail.get('sharpe_7d')}, reason={detail.get('reason', 'N/A')}")
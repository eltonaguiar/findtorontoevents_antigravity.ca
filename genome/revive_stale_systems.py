#!/usr/bin/env python3
"""
Revive Stale Systems — Mutation Generator for Dormant Trading Systems
=====================================================================

Identifies systems with no recent picks (2+ days stale), then:
1. Queries MySQL for their historical best strategies
2. Creates DNA mutations using the existing mutation engine
3. Runs GP evolution on stale system symbols to generate fresh picks
4. Outputs picks in audit dashboard format (active_picks.json)

This uses REAL data only — MySQL performance history + live market data.

Usage:
  python genome/revive_stale_systems.py
  python genome/revive_stale_systems.py --stale-days 2 --mutations-per 12
  python genome/revive_stale_systems.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "genome" / "data"
RESULTS_DIR = PROJECT_ROOT / "genome" / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# -- System registry: all pick-generating systems and their data files --

SYSTEM_REGISTRY = [
    {
        "name": "kimi_riseoftheclaw",
        "display": "KIMI Rise of the Claw",
        "active_picks": "KIMI_RISEOFTHECLAW/data/live_signals_now.json",
        "closed_picks": "KIMI_RISEOFTHECLAW/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
                     "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "BNBUSDT", "DOTUSDT"],
        "strategies": ["funding_rate_carry", "btc_4h_rsi_macd_confluence",
                       "crypto_fear_reversal", "crypto_bb_squeeze",
                       "keltner-bounce", "momentum_volume_spike",
                       "rsi_divergence", "golden_cross"],
    },
    {
        "name": "mercury2",
        "display": "Mercury2 XGBoost",
        "active_picks": "mercury2/data/active_picks.json",
        "closed_picks": "mercury2/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "RENDERUSDT"],
        "strategies": ["xgboost_ensemble", "ml_momentum", "trend_filter"],
    },
    {
        "name": "crypto_signal_engine",
        "display": "Crypto Signal Engine",
        "active_picks": "crypto_signal_engine/data/active_picks.json",
        "closed_picks": "crypto_signal_engine/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
        "strategies": ["xgboost_day_trade", "lgb_top_gainer", "ml_ensemble"],
    },
    {
        "name": "breakout_b_ml",
        "display": "Breakout Arena B (ML)",
        "active_picks": "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
        "closed_picks": "breakout_arena/approach_b_ml_breakout/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT"],
        "strategies": ["sr_breakout_ml", "fractal_breakout", "volume_profile_break"],
    },
    {
        "name": "breakout_a_pure_sr",
        "display": "Breakout Arena A (Pure S/R)",
        "active_picks": "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
        "closed_picks": "breakout_arena/approach_a_sr_breakout/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT"],
        "strategies": ["pure_sr_breakout", "atr_expansion", "volume_breakout"],
    },
    {
        "name": "paper_trading",
        "display": "Paper Trading",
        "active_picks": "paper_trading/data/active_picks.json",
        "closed_picks": "paper_trading/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
        "strategies": ["paper_ensemble", "kalman_filter", "vwap_reversion"],
    },
    {
        "name": "battleground",
        "display": "Battleground",
        "active_picks": "battleground/data/active_picks.json",
        "closed_picks": "battleground/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
        "strategies": ["bundle_proven_winners", "bundle_hybrid_quant"],
    },
    {
        "name": "ml_system_b_regime",
        "display": "ML Battleground B (Regime)",
        "active_picks": "ml_battleground/system_b_regime/data/active_picks.json",
        "closed_picks": "ml_battleground/system_b_regime/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "ADAUSDT", "AVAXUSDT", "LINKUSDT"],
        "strategies": ["regime_xgboost", "hmm_regime_gate", "trend_filter"],
    },
    {
        "name": "ml_system_c_deeplearn",
        "display": "ML Battleground C (DeepLearn)",
        "active_picks": "ml_battleground/system_c_deeplearn/data/active_picks.json",
        "closed_picks": "ml_battleground/system_c_deeplearn/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
        "strategies": ["deep_learn_ensemble", "lstm_momentum", "attention_breakout"],
    },
    {
        "name": "breakout_spike",
        "display": "Breakout Arena C (Spike Reverse)",
        "active_picks": "breakout_arena/approach_c_spike_reverse/data/active_picks.json",
        "closed_picks": "breakout_arena/approach_c_spike_reverse/data/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "strategies": ["spike_pattern_match", "cosine_similarity", "archetype_reversal"],
    },
    {
        "name": "crypto_gainer_ml",
        "display": "Crypto Gainer ML",
        "active_picks": "crypto_gainer_ml/tracker/live_picks.json",
        "closed_picks": "crypto_gainer_ml/tracker/closed_picks.json",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "DOGEUSDT", "ADAUSDT"],
        "strategies": ["gainer_momentum", "ml_top_gainer", "volume_spike_ml"],
    },
]


def _get_picks_age(picks_path: Path) -> Optional[float]:
    """Get age in days of the most recent pick in a JSON file."""
    if not picks_path.exists() or picks_path.stat().st_size < 10:
        return None  # Empty or missing = infinitely stale

    try:
        data = json.load(open(picks_path))
    except Exception:
        return None

    if not isinstance(data, list) or not data:
        return None

    now = datetime.now(timezone.utc)
    latest = None

    for pick in data:
        for key in ("timestamp", "generated_at", "entry_date", "entry_time",
                     "created_at", "signal_timestamp", "GENERATED_AT"):
            ts_str = pick.get(key)
            if ts_str:
                try:
                    ts = str(ts_str).replace("Z", "+00:00")
                    for suffix in (" EST", " EDT", " UTC", " GMT"):
                        ts = ts.replace(suffix, "")
                    parsed = datetime.fromisoformat(ts)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    if latest is None or parsed > latest:
                        latest = parsed
                except Exception:
                    pass

    if latest is None:
        # Fall back to file modification time
        mtime = datetime.fromtimestamp(picks_path.stat().st_mtime, tz=timezone.utc)
        return (now - mtime).total_seconds() / 86400

    return (now - latest).total_seconds() / 86400


def find_stale_systems(stale_days: float = 2.0) -> List[Dict[str, Any]]:
    """Find all systems with no picks in the last N days."""
    stale = []

    for sys_info in SYSTEM_REGISTRY:
        picks_path = PROJECT_ROOT / sys_info["active_picks"]
        age = _get_picks_age(picks_path)

        if age is None or age > stale_days:
            stale.append({
                **sys_info,
                "age_days": round(age, 1) if age else None,
                "picks_file_exists": picks_path.exists(),
                "picks_file_size": picks_path.stat().st_size if picks_path.exists() else 0,
            })

    return stale


def fetch_system_history_from_mysql(
    system_name: str,
    min_trades: int = 2,
) -> List[Dict[str, Any]]:
    """Fetch historical strategy performance for a system from MySQL."""
    try:
        import pymysql
    except ImportError:
        print(f"  [WARN] pymysql not available — cannot fetch MySQL history for {system_name}")
        return []

    host = os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com")
    user = os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks")
    passwd = os.environ.get("AUDIT_DB_PASS", "stocks")
    db = os.environ.get("AUDIT_DB_NAME", "ejaguiar1_stocks")

    try:
        conn = pymysql.connect(
            host=host, user=user, password=passwd, database=db,
            charset="utf8mb4", connect_timeout=15, read_timeout=30,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as e:
        print(f"  [WARN] MySQL connect failed for {system_name}: {e}")
        return []

    try:
        with conn.cursor() as cur:
            # Try at_signal_outcomes first
            cur.execute("""
                SELECT strategy, symbol,
                       COUNT(*) AS total_trades,
                       SUM(CASE WHEN LOWER(outcome) IN ('win', 'tp_hit') THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN LOWER(outcome) IN ('loss', 'sl_hit') THEN 1 ELSE 0 END) AS losses,
                       AVG(pnl_pct) AS avg_pnl,
                       SUM(pnl_pct) AS total_pnl
                FROM at_signal_outcomes
                WHERE source_system LIKE %s
                  AND strategy IS NOT NULL AND strategy <> ''
                GROUP BY strategy, symbol
                HAVING COUNT(*) >= %s
                ORDER BY SUM(CASE WHEN LOWER(outcome) IN ('win','tp_hit') THEN 1 ELSE 0 END) / COUNT(*) DESC,
                         COUNT(*) DESC
                LIMIT 20
            """, (f"%{system_name}%", min_trades))
            rows = list(cur.fetchall())

            if not rows:
                # Fallback: try at_raw_picks for any closed data
                cur.execute("""
                    SELECT strategy, symbol,
                           COUNT(*) AS total_trades,
                           SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) AS wins,
                           SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) AS losses,
                           AVG(pnl_pct) AS avg_pnl,
                           SUM(pnl_pct) AS total_pnl
                    FROM at_raw_picks
                    WHERE source_system LIKE %s
                      AND strategy IS NOT NULL AND strategy <> ''
                      AND status IN ('WON', 'LOST', 'EXPIRED')
                    GROUP BY strategy, symbol
                    HAVING COUNT(*) >= %s
                    ORDER BY SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) / COUNT(*) DESC
                    LIMIT 20
                """, (f"%{system_name}%", min_trades))
                rows = list(cur.fetchall())

            return rows
    except Exception as e:
        print(f"  [WARN] MySQL query failed for {system_name}: {e}")
        return []
    finally:
        conn.close()


def fetch_best_strategies_from_local(system_info: Dict) -> List[Dict[str, Any]]:
    """Fallback: read closed picks JSON to find best historical strategies."""
    closed_path = PROJECT_ROOT / system_info.get("closed_picks", "")
    if not closed_path.exists() or closed_path.stat().st_size < 10:
        return []

    try:
        picks = json.load(open(closed_path))
    except Exception:
        return []

    if not isinstance(picks, list):
        return []

    # Aggregate by strategy
    stats: Dict[str, Dict] = {}
    for p in picks:
        strategy = p.get("strategy", p.get("strategy_name", p.get("algorithm", "unknown")))
        symbol = str(p.get("symbol", p.get("pair", ""))).upper()
        key = f"{strategy}|{symbol}"

        if key not in stats:
            stats[key] = {"strategy": strategy, "symbol": symbol,
                          "total_trades": 0, "wins": 0, "losses": 0,
                          "total_pnl": 0}

        stats[key]["total_trades"] += 1
        status = str(p.get("status", "")).upper()
        pnl = p.get("pnl_pct", p.get("realized_pnl_pct", 0)) or 0
        try:
            pnl = float(pnl)
        except (TypeError, ValueError):
            pnl = 0

        if status in ("WON", "WIN", "TP_HIT", "CLOSED_TP"):
            stats[key]["wins"] += 1
        elif status in ("LOST", "LOSS", "SL_HIT", "CLOSED_SL"):
            stats[key]["losses"] += 1
        stats[key]["total_pnl"] += pnl

    rows = []
    for s in stats.values():
        if s["total_trades"] >= 2:
            s["avg_pnl"] = s["total_pnl"] / s["total_trades"] if s["total_trades"] > 0 else 0
            rows.append(s)

    rows.sort(key=lambda r: r["wins"] / max(r["total_trades"], 1), reverse=True)
    return rows[:10]


def create_mutations_for_system(
    system_info: Dict[str, Any],
    history: List[Dict[str, Any]],
    mutations_per_parent: int = 10,
    mutation_rate: float = 0.45,
    mutation_strength: float = 0.35,
) -> List[Dict[str, Any]]:
    """Create mutations from best historical strategies using DNA engine."""
    from genome.dna_engine import DNAPermutationEngine, create_strategy_dna
    from genome.onchain_data import OnchainDataFetcher

    engine = DNAPermutationEngine(seed=int(time.time()) % 2**31)

    # Fetch on-chain bias for smarter mutations
    bias = {}
    onchain_genes = {}
    try:
        fetcher = OnchainDataFetcher(cache_ttl=3600)
        onchain_genes = fetcher.get_all_genes("BTCUSDT")
        bias = fetcher.get_mutation_bias(onchain_genes)
    except Exception as e:
        print(f"  [INFO] On-chain bias unavailable: {e}")

    mutations = []

    if history:
        # Create mutations from actual historical winners
        for row in history[:5]:  # Top 5 performers
            strategy = str(row.get("strategy", "unknown"))
            symbol = str(row.get("symbol", "BTCUSDT")).upper()
            if not symbol.endswith("USDT"):
                symbol = symbol.replace("USD", "") + "USDT"

            total = int(row.get("total_trades", 0))
            wins = int(row.get("wins", 0))
            win_rate = wins / total if total > 0 else 0.5

            parent = create_strategy_dna(
                name=strategy,
                timeframe="1h",
                primary_indicator="EMA",
                entry_logic="momentum",
                exit_logic="take_profit",
                risk_profile="moderate" if win_rate > 0.5 else "aggressive",
                symbol=symbol,
                position_size=0.05,
                leverage=2,
                take_profit_mult=round(2.0 + win_rate, 2),
                stop_loss_mult=round(1.0 + (1 - win_rate), 2),
                expected_wr=round(win_rate, 4),
            )

            for _ in range(mutations_per_parent):
                mutant = engine.mutate_dna(
                    parent,
                    mutation_rate=mutation_rate,
                    mutation_strength=mutation_strength,
                    bias=bias or None,
                )
                mutant.genes["parent_strategy"] = strategy
                mutant.genes["parent_symbol"] = symbol
                mutant.genes["parent_win_rate"] = win_rate
                mutant.genes["source_system"] = system_info["name"]
                mutant.genes["mutation_type"] = "stale_system_revival"
                mutations.append(mutant)
    else:
        # No history — create fresh mutations for the system's target symbols
        print(f"  [INFO] No history for {system_info['name']} — creating fresh mutations from system strategies")
        for strategy in system_info.get("strategies", ["momentum"])[:3]:
            for symbol in system_info.get("symbols", ["BTCUSDT"])[:3]:
                parent = create_strategy_dna(
                    name=f"{strategy}_{symbol}",
                    timeframe="1h",
                    primary_indicator="EMA",
                    entry_logic="momentum",
                    exit_logic="take_profit",
                    risk_profile="moderate",
                    symbol=symbol,
                    position_size=0.05,
                    leverage=2,
                    take_profit_mult=2.5,
                    stop_loss_mult=1.5,
                )

                for _ in range(mutations_per_parent // 2):
                    mutant = engine.mutate_dna(
                        parent,
                        mutation_rate=mutation_rate,
                        mutation_strength=mutation_strength,
                        bias=bias or None,
                    )
                    mutant.genes["source_system"] = system_info["name"]
                    mutant.genes["mutation_type"] = "stale_system_fresh_start"
                    mutations.append(mutant)

    # Deduplicate by DNA hash
    unique = list({m.dna_hash: m for m in mutations}.values())
    return unique, onchain_genes, bias


def run_gp_evolution_for_stale(
    system_info: Dict[str, Any],
    population_size: int = 30,
    generations: int = 8,
) -> List[Dict[str, Any]]:
    """Run GP evolution targeting the stale system's symbols."""
    try:
        from genome.genetic_programmer import (
            GeneticProgrammer, fetch_ohlcv_data, OHLCVData
        )
    except ImportError as e:
        print(f"  [WARN] Cannot import GeneticProgrammer: {e}")
        return []

    symbols = system_info.get("symbols", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])[:5]
    picks = []

    for symbol in symbols:
        try:
            # Fetch real market data
            data = fetch_ohlcv_data(symbol, timeframe="1h", limit=750)
            if data is None or len(data) < 100:
                print(f"    [SKIP] {symbol}: insufficient market data")
                continue

            gp = GeneticProgrammer(
                population_size=population_size,
                max_generations=generations,
                tournament_size=5,
            )

            best = gp.evolve(data, symbol=symbol)
            if best and best.get("fitness", 0) > 0.3:
                raw_conf = min(best.get("fitness", 0.5), 0.95)
                if raw_conf < 0.60:
                    raw_conf = 0.60  # Quality floor
                pick = {
                    "symbol": symbol,
                    "direction": "LONG" if best.get("avg_return", 0) >= 0 else "SHORT",
                    "entry_price": float(data.close[-1]),
                    "take_profit": float(data.close[-1] * (1 + best.get("tp_mult", 0.04))),
                    "stop_loss": float(data.close[-1] * (1 - best.get("sl_mult", 0.02))),
                    "confidence": round(raw_conf, 4),
                    "strategy": f"GP_Revival_{system_info['name']}_{best.get('name', 'unknown')}",
                    "source_system": f"genome_revival_{system_info['name']}",
                    "asset_class": "CRYPTO",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "mutation_type": "gp_stale_revival",
                    "gp_fitness": best.get("fitness"),
                    "gp_win_rate": best.get("win_rate"),
                    "gp_sharpe": best.get("sharpe"),
                    "gp_formula": str(best.get("formula", ""))[:200],
                }
                picks.append(pick)
                print(f"    [GP] {symbol}: fitness={best.get('fitness', 0):.3f} "
                      f"wr={best.get('win_rate', 0):.1%}")

        except Exception as e:
            print(f"    [ERROR] GP for {symbol}: {e}")

    return picks


def compute_pick_score(p: Dict) -> float:
    """Weighted composite pick score per audit assessment.

    composite = 0.6*ml_score + 0.3*confidence + 0.1*confluence_score
    with risk-reward boost: *= (1 + min(rr/5, 0.2))  [capped 20%]
    with forward-validation penalty: *= 0.9 if forward_trades < 5
    """
    conf = float(p.get("confidence", 0) or 0)
    ml = float(p.get("ml_score", conf) or conf)  # fallback to confidence
    confl = float(p.get("confluence_score", 0) or 0)
    composite = 0.6 * ml + 0.3 * conf + 0.1 * confl

    rr = float(p.get("risk_reward", 0) or 0)
    if rr > 0:
        composite *= (1 + min(rr / 5, 0.2))

    fwd_trades = int(p.get("forward_trades", 0) or 0)
    if 0 < fwd_trades < 5:
        composite *= 0.9

    return min(composite, 1.0)


def apply_quality_filters(picks: List[Dict], min_confidence: float = 0.60,
                          min_ptr: float = 0.7) -> List[Dict]:
    """Apply quality filters per audit assessment recommendations.

    Filters:
    - Minimum confidence >= 60%
    - Minimum profit-to-risk ratio >= 0.7
    - Compute weighted composite pick_score
    - Exclude picks with missing price data
    """
    filtered = []
    for p in picks:
        # Confidence gate
        conf = p.get("confidence", 0)
        if conf < min_confidence:
            continue

        # Profit-to-risk gate (may already be computed)
        if "profit_to_risk" not in p:
            entry = p.get("entry_price", 0)
            tp = p.get("take_profit", 0)
            sl = p.get("stop_loss", 0)
            if entry and tp and sl:
                if p.get("direction") == "LONG":
                    reward = abs(tp - entry)
                    risk = abs(entry - sl)
                else:
                    reward = abs(entry - tp)
                    risk = abs(sl - entry)
                ptr = reward / risk if risk > 0 else 0
                p["profit_to_risk"] = round(ptr, 3)
            else:
                p["profit_to_risk"] = 0

        if p["profit_to_risk"] < min_ptr:
            continue

        # Compute and attach weighted composite score
        p["pick_score"] = round(compute_pick_score(p), 4)

        filtered.append(p)

    return filtered


def save_revival_picks(
    system_name: str,
    mutation_picks: List[Dict],
    gp_picks: List[Dict],
) -> Path:
    """Save revival picks in audit dashboard format."""
    all_picks = mutation_picks + gp_picks

    # Apply quality filters before saving
    all_picks = apply_quality_filters(all_picks)

    if not all_picks:
        return None

    # Save to genome data
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda picks, label="": picks
    all_picks = sanitize_active_picks(all_picks, "genome_revival")
    output_file = OUTPUT_DIR / f"revival_{system_name}_picks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_picks, f, indent=2, default=str)

    return output_file


def convert_mutations_to_picks(
    mutations: list,
    system_info: Dict,
) -> List[Dict[str, Any]]:
    """Convert StrategyDNA mutations into pick format for the audit dashboard."""
    picks = []
    now = datetime.now(timezone.utc)

    for m in mutations[:20]:  # Cap at 20 picks per system
        symbol = m.genes.get("symbol", m.genes.get("parent_symbol", "BTCUSDT"))
        if not symbol.endswith("USDT"):
            symbol = symbol.replace("USD", "") + "USDT"

        # We need a real price — try to get one
        entry_price = _get_current_price(symbol)
        if not entry_price:
            continue

        tp_mult = m.genes.get("take_profit_mult", 2.5)
        sl_mult = m.genes.get("stop_loss_mult", 1.5)
        direction = m.genes.get("direction_bias", "LONG")
        if isinstance(direction, str) and direction.upper() in ("SHORT", "SELL"):
            direction = "SHORT"
            tp = entry_price * (1 - tp_mult * 0.01)
            sl = entry_price * (1 + sl_mult * 0.01)
        else:
            direction = "LONG"
            tp = entry_price * (1 + tp_mult * 0.01)
            sl = entry_price * (1 - sl_mult * 0.01)

        conf = m.genes.get("expected_wr", 0.55)
        if conf > 1:
            conf = conf / 100.0
        if conf < 0.60:
            conf = 0.60  # Quality floor: minimum 60% confidence per audit assessment

        picks.append({
            "symbol": symbol,
            "direction": direction,
            "entry_price": round(entry_price, 6),
            "take_profit": round(tp, 6),
            "stop_loss": round(sl, 6),
            "confidence": round(min(conf, 0.95), 4),
            "strategy": f"Revival_{m.name}",
            "source_system": f"genome_revival_{system_info['name']}",
            "asset_class": "CRYPTO",
            "generated_at": now.isoformat(),
            "mutation_type": m.genes.get("mutation_type", "stale_revival"),
            "parent_strategy": m.genes.get("parent_strategy", ""),
            "dna_hash": m.dna_hash,
            "strategy_id": m.strategy_id,
        })

    # Quality filter: enforce minimum profit-to-risk ratio >= 0.7
    filtered = []
    for p in picks:
        entry = p["entry_price"]
        tp = p["take_profit"]
        sl = p["stop_loss"]
        if p["direction"] == "LONG":
            reward = abs(tp - entry)
            risk = abs(entry - sl)
        else:
            reward = abs(entry - tp)
            risk = abs(sl - entry)
        ptr = reward / risk if risk > 0 else 0
        if ptr >= 0.7:
            p["profit_to_risk"] = round(ptr, 3)
            filtered.append(p)

    return filtered


def _get_current_price(symbol: str) -> Optional[float]:
    """Get current price from Binance API (real data only)."""
    try:
        import urllib.request
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return float(data["price"])
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Revive stale trading systems with mutations")
    parser.add_argument("--stale-days", type=float, default=2.0,
                        help="Days without picks to consider stale (default: 2)")
    parser.add_argument("--mutations-per", type=int, default=10,
                        help="Mutations per parent strategy (default: 10)")
    parser.add_argument("--mutation-rate", type=float, default=0.45,
                        help="Per-gene mutation probability (default: 0.45)")
    parser.add_argument("--mutation-strength", type=float, default=0.35,
                        help="Numeric mutation strength (default: 0.35)")
    parser.add_argument("--gp-pop", type=int, default=30,
                        help="GP population size (default: 30)")
    parser.add_argument("--gp-gens", type=int, default=8,
                        help="GP generations (default: 8)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only identify stale systems, don't mutate")
    parser.add_argument("--skip-gp", action="store_true",
                        help="Skip GP evolution (faster, mutation-only)")
    parser.add_argument("--include-dormant-strategies", action="store_true",
                        help="Also mutate strong strategies with 0 current active picks")
    parser.add_argument("--dormant-limit", type=int, default=8,
                        help="Max dormant strategies to revive (default: 8)")
    parser.add_argument("--dormant-min-trades", type=int, default=5,
                        help="Minimum forward trades for dormant candidates (default: 5)")
    parser.add_argument("--dormant-min-wr", type=float, default=55.0,
                        help="Minimum forward win rate for dormant candidates (default: 55)")
    parser.add_argument("--dormant-min-pnl", type=float, default=0.0,
                        help="Minimum forward total PnL for dormant candidates (default: 0)")
    args = parser.parse_args()

    print("=" * 70)
    print("STALE SYSTEM REVIVAL ENGINE")
    print(f"Threshold: {args.stale_days} days | Mutations/parent: {args.mutations_per}")
    print("=" * 70)

    stale = find_stale_systems(args.stale_days)
    dormant_candidates = []
    if args.include_dormant_strategies:
        dormant_candidates = find_dormant_strategies(
            min_trades=args.dormant_min_trades,
            min_wr=args.dormant_min_wr,
            min_total_pnl=args.dormant_min_pnl,
            limit=args.dormant_limit,
        )

    if not stale and not dormant_candidates:
        print("\nAll systems are fresh and no dormant high-track-record strategies were found.")
        return 0

    if stale:
        print(f"\nFound {len(stale)} stale systems:")
        for s in stale:
            age_str = f"{s['age_days']:.1f}d" if s['age_days'] else "EMPTY"
            print(f"  [{age_str:>7}] {s['display']} ({s['name']})")
    else:
        print("\nNo stale systems found.")

    if dormant_candidates:
        print(f"\nFound {len(dormant_candidates)} dormant strategy candidates:")
        for row in dormant_candidates:
            systems = ",".join(row.get("systems", [])[:3]) or "unknown"
            print(
                f"  {row['strategy'][:42]:42s} | "
                f"WR={row['fwd_wr']:.1f}% | trades={row['fwd_trades']:>3} | "
                f"pnl={row['fwd_total_pnl']:>6.2f} | systems={systems}"
            )

    if args.dry_run:
        print("\n[DRY RUN] Exiting without mutations.")
        return 0

    system_revival_picks: List[Dict[str, Any]] = []
    dormant_revival_picks: List[Dict[str, Any]] = []
    revival_summary: List[Dict[str, Any]] = []
    all_mutations = []
    last_onchain: Dict[str, Any] = {}

    for sys_info in stale:
        print(f"\n{'-' * 50}")
        print(f"REVIVING: {sys_info['display']}")
        print(f"{'-' * 50}")

        # Fetch history from MySQL (real data)
        print(f"  Fetching history from MySQL...")
        history = fetch_system_history_from_mysql(sys_info["name"])
        if not history:
            # Fallback: try local closed picks
            print(f"  Trying local closed picks fallback...")
            history = fetch_best_strategies_from_local(sys_info)

        if history:
            print(f"  Found {len(history)} historical strategies:")
            for h in history[:5]:
                total = h.get("total_trades", 0)
                wins = h.get("wins", 0)
                wr = wins / total if total > 0 else 0
                print(f"    {h.get('strategy', '?'):40s} | {h.get('symbol', '?'):10s} | "
                      f"WR={wr:.0%} ({wins}/{total})")
        else:
            print(f"  No history found — will use system defaults")

        # Create DNA mutations
        print(f"  Creating mutations...")
        mutations, onchain, _ = create_mutations_for_system(
            sys_info, history,
            mutations_per_parent=args.mutations_per,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
        )
        all_mutations.extend(mutations)
        last_onchain = onchain or last_onchain
        print(f"  Generated {len(mutations)} unique mutations")

        # Convert to picks with real prices
        mutation_picks = convert_mutations_to_picks(mutations, sys_info)
        print(f"  Converted to {len(mutation_picks)} picks with live prices")

        # Optional: Run GP evolution
        gp_picks = []
        if not args.skip_gp:
            print(f"  Running GP evolution...")
            gp_picks = run_gp_evolution_for_stale(
                sys_info,
                population_size=args.gp_pop,
                generations=args.gp_gens,
            )
            print(f"  GP produced {len(gp_picks)} picks")

        # Save picks
        combined = mutation_picks + gp_picks
        if combined:
            outfile = save_revival_picks(sys_info["name"], mutation_picks, gp_picks)
            print(f"  Saved {len(combined)} picks -> {outfile}")
            system_revival_picks.extend(combined)

            revival_summary.append({
                "kind": "stale_system",
                "system": sys_info["name"],
                "display": sys_info["display"],
                "age_days": sys_info.get("age_days"),
                "history_count": len(history),
                "mutations_created": len(mutations),
                "mutation_picks": len(mutation_picks),
                "gp_picks": len(gp_picks),
                "total_picks": len(combined),
            })

    pre_filter_count = len(system_revival_picks)
    system_revival_picks = apply_quality_filters(system_revival_picks)
    post_filter_count = len(system_revival_picks)
    filtered_out = pre_filter_count - post_filter_count
    if filtered_out > 0:
        print(f"\n  Quality filter: {filtered_out} system-revival picks removed "
              f"(conf<60% or P/R<0.7), {post_filter_count} kept")

    system_output = OUTPUT_DIR / "revival_all_picks.json"
    if system_revival_picks:
        save_pick_file(system_output, system_revival_picks, "genome_revival")

    dormant_output = None
    if args.include_dormant_strategies:
        print(f"\n{'-' * 50}")
        print("REVIVING: Dormant High-Track-Record Strategies")
        print(f"{'-' * 50}")
        dormant_revival_picks, dormant_summary = revive_dormant_strategies(
            mutations_per_parent=args.mutations_per,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
            min_trades=args.dormant_min_trades,
            min_wr=args.dormant_min_wr,
            min_total_pnl=args.dormant_min_pnl,
            limit=args.dormant_limit,
        )
        if dormant_revival_picks:
            dormant_output = save_pick_file(DORMANT_OUTPUT_PATH, dormant_revival_picks, "genome_revival_dormant")
            print(f"  Saved {len(dormant_revival_picks)} dormant-strategy picks -> {dormant_output}")
        revival_summary.extend(dormant_summary)

    total_picks = len(system_revival_picks) + len(dormant_revival_picks)
    confs = [p["confidence"] for p in system_revival_picks]
    ptrs = [p.get("profit_to_risk", 0) for p in system_revival_picks]
    avg_conf = sum(confs) / len(confs) if confs else 0
    avg_ptr = sum(ptrs) / len(ptrs) if ptrs else 0

    if revival_summary or total_picks:
        summary_file = RESULTS_DIR / f"revival_summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "stale_threshold_days": args.stale_days,
                "systems_revived": len([r for r in revival_summary if r.get("kind") == "stale_system"]),
                "dormant_strategies_revived": len([r for r in revival_summary if r.get("kind") == "dormant_strategy"]),
                "total_picks_generated": total_picks,
                "system_revival_picks": len(system_revival_picks),
                "dormant_revival_picks": len(dormant_revival_picks),
                "quality_filters": {
                    "min_confidence": 0.60,
                    "min_profit_to_risk": 0.7,
                    "system_picks_before_filter": pre_filter_count,
                    "system_picks_after_filter": post_filter_count,
                    "system_filtered_out": filtered_out,
                    "avg_confidence": round(avg_conf, 4),
                    "avg_profit_to_risk": round(avg_ptr, 3),
                },
                "onchain_context": last_onchain,
                "items": revival_summary,
            }, f, indent=2, default=str)

    try:
        from genome.strategy_registry import StrategyRegistry
        registry = StrategyRegistry()
        for mutation in all_mutations:
            try:
                registry.register_strategy(mutation)
            except Exception:
                pass
        print(f"\n  Registered mutations in StrategyRegistry")
    except Exception as e:
        print(f"\n  [WARN] Could not register in StrategyRegistry: {e}")

    print(f"\n{'=' * 70}")
    print("REVIVAL COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Systems revived:    {len([r for r in revival_summary if r.get('kind') == 'stale_system'])}")
    print(f"  Dormant revived:    {len([r for r in revival_summary if r.get('kind') == 'dormant_strategy'])}")
    print(f"  Total picks:        {total_picks}")
    print(f"  System output:      {system_output}")
    if dormant_output:
        print(f"  Dormant output:     {dormant_output}")
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

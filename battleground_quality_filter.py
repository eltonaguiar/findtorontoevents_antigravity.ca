#!/usr/bin/env python3
"""
Battleground Quality Filter & Ranking System

Implements forward-quality filtering per Baby Strat rules:
- Primary: Tier 1/Tier 2 standardized tests
- Filter Layer: forward_trades >= 12, forward_win_rate >= 50% OR (forward_sharpe >= 1.5 AND profit_factor > 1)
- Rank by quality score for battleground display
- Track recent picks (30min/1hour windows)
- Show TP/SL remaining % for active picks
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from forward_metrics_compat import forward_win_rate_percent

# Strategy trust tiers — sandboxed strategies still generate picks but get lower scores
# PROVEN: Full weight in portfolio decisions (forward WR > 55%, 50+ trades)
# SANDBOX: Generate & track picks, but 0.25x weight — needs more forward proof
# PROBATION: Generate & track picks, but 0.1x weight — actively losing money
STRATEGY_TRUST_TIERS = {
    # PROBATION — historically high-loss, track only (audit showed these destroy P&L)
    # NOTE: Do NOT remove these — user explicitly said "don't kill, sandbox them"
    # They stay at 0.1x weight so picks are tracked but heavily penalized
    "keltner_compression_expansion": {"tier": "PROBATION", "weight": 0.1, "reason": "-86% avg SL hit, broken risk mgmt"},
    "baby_strats_forward": {"tier": "PROBATION", "weight": 0.1, "reason": "2,707 trades at 41.9% WR = -13,248%"},
    "ml_bg_system_c": {"tier": "PROBATION", "weight": 0.1, "reason": "0% WR across 5 trades, -147%"},
    "mercury2_fast": {"tier": "PROBATION", "weight": 0.1, "reason": "Garbage entry prices ($1M+), system broken"},
}

# Default tier for unlisted strategies
DEFAULT_TRUST_TIER = {"tier": "SANDBOX", "weight": 0.25, "reason": "Unproven — needs 50+ closed trades"}

# Strategies that have earned PROVEN status — MUST be symbol-specific
# because same strategy can win on ETH but lose on SOL
PROVEN_STRATEGIES = {
    # Verified profitable per-symbol combinations (from audit data)
    "crypto_vwap_deviation_reversion": {"tier": "PROVEN", "weight": 1.0, "reason": "Battleground: 38.5% WR but huge +332% total (big TP hits)"},
    "drawdown_recovery_rsi_eth": {"tier": "PROVEN", "weight": 1.0, "reason": "ETH: 72.7% WR, +291%"},
    "multi_period_rsi_confluence_eth": {"tier": "PROVEN", "weight": 0.9, "reason": "ETH: 64.3% WR, +200%"},
    "multi_period_rsi_confluence_xrp": {"tier": "PROVEN", "weight": 0.8, "reason": "XRP: 83.3% WR, +157%"},
}

# Aggressive variants of proven strategies — SANDBOX until forward-tested
# These are relaxed-threshold mutations that generate more signals from proven logic
AGGRESSIVE_VARIANTS = {
    "vwap_reversion_aggressive": {"tier": "SANDBOX", "weight": 0.5, "reason": "Aggressive variant of +332% VWAP reversion (1.5s, relaxed Hurst)"},
    "drawdown_recovery_rsi_eth_agg": {"tier": "SANDBOX", "weight": 0.6, "reason": "Aggressive variant of +291% ETH drawdown RSI"},
    "drawdown_recovery_rsi_sol_agg": {"tier": "SANDBOX", "weight": 0.3, "reason": "Aggressive DD RSI on SOL (unproven symbol)"},
    "drawdown_recovery_rsi_bnb_agg": {"tier": "SANDBOX", "weight": 0.3, "reason": "Aggressive DD RSI on BNB (unproven symbol)"},
    "multi_rsi_confluence_eth_agg": {"tier": "SANDBOX", "weight": 0.6, "reason": "Aggressive variant of +200% ETH multi-RSI"},
    "multi_rsi_confluence_xrp_agg": {"tier": "SANDBOX", "weight": 0.6, "reason": "Aggressive variant of +157% XRP multi-RSI"},
    "triple_rsi_fast": {"tier": "SANDBOX", "weight": 0.4, "reason": "Fast RSI triple confluence (7/14/21)"},
    "vwap_rsi_combo": {"tier": "SANDBOX", "weight": 0.5, "reason": "VWAP+RSI combo: confluence of two proven edges"},
    "drawdown_recovery_rsi_fast": {"tier": "SANDBOX", "weight": 0.4, "reason": "Fast DD recovery (20-bar, 5% threshold)"},
    # --- DNA Winner Mutations (genome/dna_winner_mutations.py) ---
    # System 1: Claude Gainer ML Perf (70% WR parent)
    "claude_ml_conservative_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: pump threshold 0.50 (was 0.65) from 70% WR parent"},
    "claude_ml_moderate_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: expanded universe + threshold 0.45 from 70% WR parent"},
    "claude_ml_aggressive_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: momentum chase mode from 70% WR parent"},
    # System 2: KIMI Signal Tracking (64% WR parent)
    "kimi_funding_arb_relaxed_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: z-score < -1.5 (was -2.0) from 64% WR KIMI"},
    "kimi_flash_crash_relaxed_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: 3% DD + RSI<35 + vol>1.3x from 64% WR KIMI"},
    "kimi_bollinger_aggressive_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: BB mean-rev no pump filter from 64% WR KIMI"},
    "kimi_drought_adaptive_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: permanent drought=3 relaxation from 64% WR KIMI"},
    # System 3: Claude Gainer (56.2% WR parent)
    "gainer_compression_relaxed_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: BB compression <3% from 56% WR gainer"},
    "gainer_obv_divergence_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: OBV divergence standalone from 56% WR gainer"},
    "gainer_momentum_streak_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: 3+ green bars + vol accel from 56% WR gainer"},
    # System 4: Battleground (61.6% WR parent)
    "battleground_ml_relaxed_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: ML proxy >= 0.45 (was 0.65) from 61.6% WR bg"},
    "battleground_rsi_no_regime_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: dual RSI no regime gate from 61.6% WR bg"},
    "battleground_vwap_1h_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: VWAP 1.2-sigma on 1h from 61.6% WR bg"},
    "battleground_contrarian_sell_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: inverted BUY->SELL from 61.6% WR bg"},
    # --- MACD DNA Mutations (genome/dna_macd_mutations.py) ---
    "macd_classic_crossover": {"tier": "SANDBOX", "weight": 0.35, "reason": "MACD(12,26,9) standard crossover — baseline"},
    "macd_fast_scalp": {"tier": "SANDBOX", "weight": 0.25, "reason": "MACD(8,17,6) fast scalp — aggressive, tighter TP/SL"},
    "macd_histogram_reversal": {"tier": "SANDBOX", "weight": 0.30, "reason": "MACD histogram slope reversal — early momentum"},
    "macd_zero_line_bounce": {"tier": "SANDBOX", "weight": 0.35, "reason": "MACD zero-line bounce — trend pullback entries"},
    "macd_divergence_hunter": {"tier": "SANDBOX", "weight": 0.40, "reason": "MACD price divergence — highest conviction"},
    "macd_multi_timeframe": {"tier": "SANDBOX", "weight": 0.40, "reason": "MACD 1h+4h alignment — most confirmation"},
    "macd_rsi_confluence": {"tier": "SANDBOX", "weight": 0.35, "reason": "MACD crossover + RSI(14) — double confirmation"},
    "macd_volume_confirmed": {"tier": "SANDBOX", "weight": 0.35, "reason": "MACD crossover + volume > 1.5x avg — institutional"},
    # --- DNA Pumpwatch Mutations (genome/dna_pumpwatch_mutations.py) ---
    # Parent: pumpwatch / volume-spike-scout (1W/3L historically, 5 open in profit)
    "pump_volume_relaxed_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: vol 1.5x (was 2.0x) + RSI<50 from pumpwatch"},
    "pump_volume_momentum_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: vol 1.5x + MACD histogram confirmation from pumpwatch"},
    "pump_multi_exchange_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: Binance+CoinGecko cross-exchange verify from pumpwatch"},
    "pump_smart_entry_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: 1% pullback entry after spike from pumpwatch"},
    "pump_regime_aware_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: pump only when F&G<40 (contrarian) from pumpwatch"},
    # --- DNA Signal Engine Mutations (genome/dna_signal_engine_mutations.py) ---
    # Parent: crypto_signal_engine (100% WR, 2 trades, 0 active — too strict)
    "signal_engine_relaxed_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: MIN_CONF 0.40 (was 0.60), no trend guard from 100% WR engine"},
    "signal_engine_wide_net_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: 15 symbols (was 3), MIN_CONF 0.45 from 100% WR engine"},
    "signal_engine_no_premium_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: flat 0.50 conf (no premium gate) from 100% WR engine"},
    "signal_engine_momentum_mut": {"tier": "SANDBOX", "weight": 0.3, "reason": "DNA mutation: momentum-only mode (no mean-rev) from 100% WR engine"},
    # --- DNA Pumpwatch V2 Mutations (genome/dna_pumpwatch_v2_mutations.py) ---
    # Parent: pumpwatch (1W/3L — losses from altcoins in downtrends, V2 = loss prevention)
    "pump_trend_confirmed_v2": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA V2: vol spike + price > 50-EMA — prevents downtrend entries (DOT fix)"},
    "pump_btc_correlated_v2": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA V2: alt pumps gated on BTC > 20-EMA — prevents BTC drawdown losses"},
    "pump_large_cap_only_v2": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA V2: top-10 market cap only — prevents small cap traps (NVDAX fix)"},
    "pump_momentum_continuation_v2": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA V2: vol spike + 3-bar momentum — catches continuation not dead cats"},
    "pump_fear_greed_filter_v2": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA V2: vol spike at F&G < 30 — extreme fear accumulation signals"},
    # --- DNA Rapid Fire Mutations (genome/dna_rapid_fire_mutations.py) ---
    # Parent: rapid_fire (PROBATION tier, 0.15 weight — high-frequency noise, no proven edge)
    "rapid_trend_only_mut": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA mutation: rapid fire + 200-EMA trend gate — no counter-trend trades"},
    "rapid_momentum_filter_mut": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA mutation: rapid fire + MACD histogram confirmation — momentum match"},
    "rapid_volume_gate_mut": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA mutation: rapid fire + vol > 1.3x avg — real participation gate"},
    "rapid_top10_only_mut": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA mutation: rapid fire restricted to top-10 mktcap — liquid assets only"},
    "rapid_rsi_filter_mut": {"tier": "SANDBOX", "weight": 0.30, "reason": "DNA mutation: rapid fire + RSI < 60 LONG / > 40 SHORT — no extreme chasing"},
    # --- DNA Confluence Mutations (genome/dna_confluence_mutations.py) ---
    # Baby-Strats + Battleground overlap — symbol-locked to proven assets
    "confluence_keltner_funding_btc": {"tier": "SANDBOX", "weight": 0.40, "reason": "Keltner compression + funding gate — BTC ONLY (72.2% WR, +490.9%)"},
    "confluence_vwap_funding_btc": {"tier": "SANDBOX", "weight": 0.40, "reason": "VWAP deviation reversion + funding — BTC ONLY (63.6% WR, +290.2%)"},
    "confluence_rsi_recovery_eth": {"tier": "SANDBOX", "weight": 0.40, "reason": "Drawdown recovery RSI — ETH ONLY (72.7% WR, +145.5%)"},
    "confluence_multi_rsi_xrp": {"tier": "SANDBOX", "weight": 0.40, "reason": "Multi-period RSI confluence — XRP ONLY (83.3% WR, +78.7%)"},
    "confluence_keltner_vwap_combo_btc": {"tier": "SANDBOX", "weight": 0.40, "reason": "Keltner+VWAP double confirmation — BTC ONLY (highest conviction)"},
    "confluence_funding_gate_multi": {"tier": "SANDBOX", "weight": 0.30, "reason": "Funding momentum gate on 10 symbols (66.9% WR, +940%)"},
}

# Strategies that LOOK proven but are actually losing on certain symbols
DEMOTED_STRATEGIES = {
    "drawdown_recovery_rsi": {"tier": "SANDBOX", "weight": 0.25, "reason": "BTC: 16.7% WR, -778%. Only ETH variant is proven."},
    "multi_period_rsi_confluence_sol": {"tier": "SANDBOX", "weight": 0.25, "reason": "SOL: 17.6% WR, -753%. Only ETH/XRP proven."},
    "multi_period_rsi_confluence_doge": {"tier": "SANDBOX", "weight": 0.25, "reason": "DOGE: 0% WR. Not proven on this symbol."},
}

def get_strategy_trust(strategy_name: str) -> dict:
    """Get trust tier for a strategy. Checks probation → demoted → proven → sandbox."""
    # Check if any probation key is a substring of the strategy name
    for key, tier_info in STRATEGY_TRUST_TIERS.items():
        if key in strategy_name:
            return {**tier_info, "strategy": strategy_name}
    # Check demoted BEFORE proven (e.g. drawdown_recovery_rsi must not match ETH-proven variant)
    for key, tier_info in DEMOTED_STRATEGIES.items():
        if key in strategy_name:
            return {**tier_info, "strategy": strategy_name}
    # Check aggressive variants (higher weight than default sandbox)
    for key, tier_info in AGGRESSIVE_VARIANTS.items():
        if key in strategy_name:
            return {**tier_info, "strategy": strategy_name}
    # Check proven strategies
    for key, tier_info in PROVEN_STRATEGIES.items():
        if key in strategy_name:
            return {**tier_info, "strategy": strategy_name}
    return {**DEFAULT_TRUST_TIER, "strategy": strategy_name}


def get_evolution_candidates() -> list:
    """
    Get PROBATION and underperforming SANDBOX strategies as candidates
    for DNA evolution. The GP engine can mutate their logic to find
    winning variants — turning losers into potential winners.

    Returns list of dicts with strategy name, current metrics, and
    suggested mutation focus areas.
    """
    candidates = []

    # All probation strategies are evolution candidates
    for name, info in STRATEGY_TRUST_TIERS.items():
        candidates.append({
            "strategy": name,
            "tier": info["tier"],
            "current_weight": info["weight"],
            "reason": info["reason"],
            "evolution_goal": "mutate_to_fix",
            "suggested_mutations": [
                "invert_direction",        # If it's always wrong, flip it
                "tighten_stops",           # Fix broken risk management
                "add_regime_filter",       # Only trade in favorable regimes
                "adjust_timeframe",        # Try different bar sizes
                "combine_with_proven",     # Cross with proven strategy DNA
            ]
        })

    return candidates


def get_weighted_picks(picks: list) -> list:
    """
    Apply trust-tier weights to a list of picks. Each pick gets a
    'trust_weight' field (0.1 to 1.0) based on its strategy's tier.

    Picks are NOT removed — they're all kept but weighted so downstream
    portfolio allocation can use the weight for position sizing.
    """
    for pick in picks:
        strategy = pick.get("strategy", "")
        trust = get_strategy_trust(strategy)
        pick["trust_tier"] = trust["tier"]
        pick["trust_weight"] = trust["weight"]
        pick["trust_reason"] = trust["reason"]
    return picks

DB_PATH = Path("incubator/forward_test.db")
DASHBOARD_FILE = Path("battleground/data/baby_strats_dashboard.json")
QUALITY_LOG = Path("battleground/data/quality_rankings.json")


@dataclass
class StrategyQuality:
    """Quality metrics for battleground ranking"""
    name: str
    agent_id: str
    tier: str  # tier1_passed, tier2_partial, tier2_fully_robust
    
    # Backtest metrics
    backtest_sharpe: float
    backtest_win_rate: float
    backtest_max_dd: float
    
    # Forward metrics
    forward_sharpe: float
    forward_win_rate: float
    forward_max_dd: float
    forward_trades: int
    forward_days: int
    forward_pnl: float
    
    # Quality calculations
    quality_score: float
    quality_tier: str  # ELITE, QUALITY, EMERGING, WATCH
    passes_filter: bool
    
    # Recent activity
    last_pick_time: Optional[str]
    picks_30min: int
    picks_1hour: int


@dataclass
class ActivePick:
    """Active pick with TP/SL progress tracking"""
    strategy_name: str
    symbol: str
    side: str  # LONG/SHORT
    entry_price: float
    current_price: float
    take_profit: float
    stop_loss: float
    entry_time: str
    
    # Progress metrics
    tp_distance_pct: float  # % remaining to TP
    sl_distance_pct: float  # % remaining to SL
    progress_pct: float  # % of the way to TP (0-100, can exceed 100)
    risk_reward_current: float  # Current R:R based on price position
    time_in_trade_minutes: int
    
    @property
    def status(self) -> str:
        """Determine pick status"""
        if self.progress_pct >= 100:
            return "TP_HIT"
        elif self.progress_pct <= -100:
            return "SL_HIT"
        elif self.progress_pct > 75:
            return "NEAR_TP"
        elif self.progress_pct < -50:
            return "NEAR_SL"
        else:
            return "IN_PROGRESS"


class BattlegroundQualityFilter:
    """Quality filter and ranking system for battleground strategies"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.dashboard_file = DASHBOARD_FILE
        self.quality_log = QUALITY_LOG
        
    def calculate_quality_score(self, fw_sharpe: float, fw_wr: float, 
                                 fw_trades: int, profit_factor: float = 0) -> Tuple[float, str, bool]:
        """
        Calculate quality score and determine tier.
        
        Returns:
            (score, tier, passes_filter)
        """
        # Check filter criteria
        passes_trades = fw_trades >= 12
        passes_wr = fw_wr >= 50.0
        passes_sharpe_pf = fw_sharpe >= 1.5 and profit_factor > 1.0
        
        passes_filter = passes_trades and (passes_wr or passes_sharpe_pf)
        
        # Calculate quality score (0-100)
        score = 0.0
        
        # Base score from forward Sharpe (0-40 points)
        if fw_sharpe > 0:
            score += min(40, fw_sharpe * 20)  # Sharpe 2.0 = 40 points
        
        # Win rate component (0-30 points)
        score += min(30, fw_wr * 0.3)  # 100% WR = 30 points
        
        # Trade count confidence (0-20 points)
        score += min(20, fw_trades * 0.5)  # 40 trades = 20 points
        
        # Profit factor bonus (0-10 points)
        if profit_factor > 1:
            score += min(10, (profit_factor - 1) * 10)
        
        # Determine tier
        if score >= 80 and passes_filter:
            tier = "ELITE"
        elif score >= 60 and passes_filter:
            tier = "QUALITY"
        elif score >= 40:
            tier = "EMERGING"
        else:
            tier = "WATCH"
        
        return round(score, 1), tier, passes_filter
    
    def get_recent_picks(self, strategy_name: str, minutes: int) -> int:
        """Count picks in last N minutes"""
        if not self.db_path.exists():
            return 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            cursor.execute('''
                SELECT COUNT(*) FROM forward_trades
                WHERE strategy_name = ? AND entry_time > ?
            ''', (strategy_name, cutoff.isoformat()))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def get_last_pick_time(self, strategy_name: str) -> Optional[str]:
        """Get timestamp of most recent pick"""
        if not self.db_path.exists():
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT entry_time FROM forward_trades
                WHERE strategy_name = ?
                ORDER BY entry_time DESC
                LIMIT 1
            ''', (strategy_name,))
            
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except:
            return None
    
    def get_active_picks(self, strategy_name: str) -> List[ActivePick]:
        """Get active (open) picks for a strategy with TP/SL progress"""
        if not self.db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # This query assumes we have a table for active picks
            # For now, get recent trades without exit
            cursor.execute('''
                SELECT entry_time, direction, entry_price, 
                       take_profit, stop_loss
                FROM forward_trades
                WHERE strategy_name = ? AND exit_time IS NULL
                ORDER BY entry_time DESC
            ''', (strategy_name,))
            
            picks = []
            for row in cursor.fetchall():
                # In real implementation, we'd get current price from market data
                # For now, calculate based on stored values
                entry_time = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                time_in_trade = int((datetime.now(timezone.utc) - entry_time).total_seconds() / 60)
                
                picks.append(ActivePick(
                    strategy_name=strategy_name,
                    symbol="BTC/USDT",  # Would come from data
                    side=row[1],
                    entry_price=row[2],
                    current_price=row[2],  # Would be live price
                    take_profit=row[3] or row[2] * 1.05,
                    stop_loss=row[4] or row[2] * 0.95,
                    entry_time=row[0],
                    tp_distance_pct=5.0,  # Calculated from current price
                    sl_distance_pct=5.0,
                    progress_pct=0.0,
                    risk_reward_current=1.0,
                    time_in_trade_minutes=time_in_trade
                ))
            
            conn.close()
            return picks
        except:
            return []
    
    def rank_strategies(self) -> List[StrategyQuality]:
        """Rank all strategies by quality score"""
        # Load dashboard
        if not self.dashboard_file.exists():
            return []
        
        with open(self.dashboard_file, 'r') as f:
            dashboard = json.load(f)
        
        strategies = dashboard.get('strategies', [])
        ranked = []
        
        for strat in strategies:
            name = strat['name']
            
            # Get forward metrics (nested forward_metrics + strat_fwd_wr; legacy key often empty)
            fm = strat.get("forward_metrics") or {}
            fw_sharpe = strat.get("forward_sharpe")
            if fw_sharpe is None:
                fw_sharpe = fm.get("sharpe")
            if fw_sharpe is None:
                fw_sharpe = 0.0
            fw_wr = forward_win_rate_percent(strat)
            fw_trades = strat.get('forward_trades', 0) or 0
            fw_days = strat.get('forward_days', 0) or 0
            fw_pnl = strat.get('forward_pnl', 0) or 0
            
            # Calculate quality
            score, tier, passes = self.calculate_quality_score(
                fw_sharpe, fw_wr, fw_trades
            )
            
            # Get recent activity
            picks_30min = self.get_recent_picks(name, 30)
            picks_1hour = self.get_recent_picks(name, 60)
            last_pick = self.get_last_pick_time(name)
            
            sq = StrategyQuality(
                name=name,
                agent_id=strat.get('agent_id', 'unknown'),
                tier=strat.get('tier', 'unknown'),
                backtest_sharpe=strat.get('backtest_sharpe', 0),
                backtest_win_rate=strat.get('backtest_win_rate', 0),
                backtest_max_dd=strat.get('backtest_max_dd', 0),
                forward_sharpe=fw_sharpe,
                forward_win_rate=fw_wr,
                forward_max_dd=strat.get('forward_max_dd', 0),
                forward_trades=fw_trades,
                forward_days=fw_days,
                forward_pnl=fw_pnl,
                quality_score=score,
                quality_tier=tier,
                passes_filter=passes,
                last_pick_time=last_pick,
                picks_30min=picks_30min,
                picks_1hour=picks_1hour
            )
            
            ranked.append(sq)
        
        # Sort by quality score (descending)
        ranked.sort(key=lambda x: x.quality_score, reverse=True)
        return ranked
    
    def update_quality_rankings(self):
        """Update quality rankings file"""
        ranked = self.rank_strategies()
        
        # Separate into tiers
        elite = [s for s in ranked if s.quality_tier == "ELITE"]
        quality = [s for s in ranked if s.quality_tier == "QUALITY"]
        emerging = [s for s in ranked if s.quality_tier == "EMERGING"]
        watch = [s for s in ranked if s.quality_tier == "WATCH"]
        
        # Format for JSON
        def format_strategy(sq: StrategyQuality) -> dict:
            return {
                'name': sq.name,
                'agent_id': sq.agent_id,
                'tier': sq.tier,
                'quality_score': sq.quality_score,
                'quality_tier': sq.quality_tier,
                'passes_filter': sq.passes_filter,
                'forward_metrics': {
                    'sharpe': sq.forward_sharpe,
                    'win_rate': sq.forward_win_rate,
                    'max_dd': sq.forward_max_dd,
                    'trades': sq.forward_trades,
                    'days': sq.forward_days,
                    'pnl': sq.forward_pnl
                },
                'backtest_metrics': {
                    'sharpe': sq.backtest_sharpe,
                    'win_rate': sq.backtest_win_rate,
                    'max_dd': sq.backtest_max_dd
                },
                'recent_activity': {
                    'last_pick': sq.last_pick_time,
                    'picks_30min': sq.picks_30min,
                    'picks_1hour': sq.picks_1hour
                }
            }
        
        rankings = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total': len(ranked),
                'elite': len(elite),
                'quality': len(quality),
                'emerging': len(emerging),
                'watch': len(watch),
                'passing_filter': len([s for s in ranked if s.passes_filter])
            },
            'elite': [format_strategy(s) for s in elite[:10]],
            'quality': [format_strategy(s) for s in quality[:10]],
            'emerging': [format_strategy(s) for s in emerging[:10]],
            'watch': [format_strategy(s) for s in watch[:10]],
            'all_ranked': [format_strategy(s) for s in ranked]
        }
        
        # Save
        self.quality_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.quality_log, 'w') as f:
            json.dump(rankings, f, indent=2)
        
        return rankings
    
    def get_top_strategies_for_display(self, limit: int = 10, 
                                       min_quality_tier: str = "EMERGING") -> List[Dict]:
        """Get top strategies for battleground display"""
        ranked = self.rank_strategies()
        
        tier_order = {"ELITE": 0, "QUALITY": 1, "EMERGING": 2, "WATCH": 3}
        min_tier_val = tier_order.get(min_quality_tier, 2)
        
        filtered = [
            s for s in ranked 
            if tier_order.get(s.quality_tier, 99) <= min_tier_val
        ]
        
        result = []
        for sq in filtered[:limit]:
            # Get active picks
            active_picks = self.get_active_picks(sq.name)
            
            result.append({
                'name': sq.name,
                'quality_tier': sq.quality_tier,
                'quality_score': sq.quality_score,
                'forward_sharpe': sq.forward_sharpe,
                'forward_win_rate': sq.forward_win_rate,
                'forward_trades': sq.forward_trades,
                'passes_filter': sq.passes_filter,
                'recent_picks_30min': sq.picks_30min,
                'recent_picks_1hour': sq.picks_1hour,
                'active_picks': [
                    {
                        'symbol': p.symbol,
                        'side': p.side,
                        'progress_pct': p.progress_pct,
                        'tp_remaining_pct': p.tp_distance_pct,
                        'sl_remaining_pct': p.sl_distance_pct,
                        'status': p.status,
                        'time_minutes': p.time_in_trade_minutes
                    }
                    for p in active_picks[:3]  # Top 3 active picks
                ]
            })
        
        return result


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Battleground Quality Filter')
    parser.add_argument('--update', action='store_true', help='Update quality rankings')
    parser.add_argument('--show', action='store_true', help='Show top strategies')
    parser.add_argument('--limit', type=int, default=10, help='Number to show')
    
    args = parser.parse_args()
    
    filter_system = BattlegroundQualityFilter()
    
    if args.update:
        rankings = filter_system.update_quality_rankings()
        print(f"Updated quality rankings")
        print(f"Summary: {rankings['summary']}")
    
    if args.show or not args.update:
        top = filter_system.get_top_strategies_for_display(args.limit)
        print(f"\nTop {len(top)} Strategies:")
        print("="*80)
        for i, s in enumerate(top, 1):
            print(f"{i}. {s['name'][:40]:<40} | "
                  f"Tier: {s['quality_tier']:<7} | "
                  f"Score: {s['quality_score']:.1f} | "
                  f"Sharpe: {s['forward_sharpe']:.2f} | "
                  f"WR: {s['forward_win_rate']:.1f}%")
            if s['active_picks']:
                for p in s['active_picks']:
                    print(f"   → {p['symbol']} {p['side']}: {p['progress_pct']:.1f}% to TP, "
                          f"{p['tp_remaining_pct']:.1f}% TP remaining, "
                          f"{p['sl_remaining_pct']:.1f}% SL buffer")

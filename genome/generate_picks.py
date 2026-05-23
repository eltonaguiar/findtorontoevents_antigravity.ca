#!/usr/bin/env python3
"""
Generate Active Picks Script
============================

Generates live trading picks from DNA-based strategies.
Designed to run on a schedule (GitHub Actions, cron, etc.)

Usage:
    python genome/generate_picks.py
    python genome/generate_picks.py --symbol BTC --regime trending_up
    python genome/generate_picks.py --output genome/active_picks.json
"""

import argparse
import json
import logging
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from genome import (
    DNAPermutationEngine,
    DNABacktester,
    StrategyRegistry,
    StrategyDNA,
    create_strategy_dna,
    CombinationLogic,
    MarketRegime
)

# ------------------------------------------------------------------ #
#  Tier-Gated Pick Emission
# ------------------------------------------------------------------ #
EMIT_TIERS = {"SANDBOX", "FRESH_PICKS", "DNA_MASTER"}


def should_emit_pick(tier) -> bool:
    """Check if a strategy's tier allows pick emission."""
    return tier in EMIT_TIERS


def _get_strategy_tier(strategy_id: str) -> str:
    """Look up strategy tier from dna_factory.db. Returns 'UNKNOWN' if not found."""
    import sqlite3
    db_path = Path(__file__).parent.parent / "battleground" / "data" / "dna_factory.db"
    if not db_path.exists():
        return "UNKNOWN"
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT current_tier FROM strategy_tiers WHERE strategy_id = ?",
            (strategy_id,)
        ).fetchone()
        conn.close()
        return row[0] if row else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GeneratePicks')


def load_strategy_catalog(catalog_path: str = "genome/data/unified_strategy_catalog.json") -> List[StrategyDNA]:
    """Load strategies from catalog file."""
    try:
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        
        strategies = []
        for idx, strat_data in enumerate(catalog.get('strategies', [])):
            # Use 'id' if present, fall back to 'name', then generate one
            strategy_id = strat_data.get('id') or strat_data.get('name') or f"strategy_{idx}"
            strategy_name = strat_data.get('name', strategy_id)

            # Use 'dna' if present, otherwise build genes from available fields
            genes = strat_data.get('dna', {})
            if not genes:
                genes = {
                    k: v for k, v in strat_data.items()
                    if k not in ('id', 'name', 'symbol_specialization')
                }

            dna = StrategyDNA(
                strategy_id=strategy_id,
                name=strategy_name,
                genes=genes,
                symbol_specialization=strat_data.get('symbol_specialization'),
                generation=0
            )
            strategies.append(dna)
        
        logger.info(f"Loaded {len(strategies)} strategies from catalog")
        return strategies
    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        return []


def detect_current_regime(symbol: str = "BTC") -> MarketRegime:
    """
    Detect current market regime.
    
    In production, this would fetch real market data and analyze it.
    For now, returns a default or uses simple heuristics.
    """
    # TODO: Implement real regime detection from market data
    # For demo purposes, return TRENDING_UP
    return MarketRegime.TRENDING_UP


def filter_strategies_by_regime(
    strategies: List[StrategyDNA],
    regime: MarketRegime,
    catalog_path: str = "genome/data/unified_strategy_catalog.json"
) -> List[StrategyDNA]:
    """Filter strategies suitable for current regime."""
    try:
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        
        regime_mappings = catalog.get('regime_mappings', {})
        preferred = regime_mappings.get(regime.value, {}).get('preferred_strategies', [])
        
        filtered = [s for s in strategies if s.strategy_id in preferred]
        
        if not filtered:
            logger.warning(f"No preferred strategies for {regime.value}, using all")
            return strategies
        
        logger.info(f"Filtered to {len(filtered)} strategies for {regime.value} regime")
        return filtered
    except Exception as e:
        logger.error(f"Failed to filter by regime: {e}")
        return strategies


def filter_strategies_by_symbol(
    strategies: List[StrategyDNA],
    symbol: str
) -> List[StrategyDNA]:
    """Filter strategies specialized for or compatible with symbol."""
    # First try symbol-specialized strategies
    specialized = [s for s in strategies if s.symbol_specialization == symbol]
    
    # Add general strategies (no specialization)
    general = [s for s in strategies if s.symbol_specialization is None]
    
    combined = specialized + general
    
    logger.info(f"Symbol {symbol}: {len(specialized)} specialized, {len(general)} general")
    return combined


def generate_permutations(
    strategies: List[StrategyDNA],
    engine: DNAPermutationEngine,
    max_combo_size: int = 3
) -> List[StrategyDNA]:
    """Generate strategy permutations."""
    # Include original strategies
    all_candidates = strategies.copy()
    
    # Generate combinations
    if len(strategies) >= 2:
        combos = engine.generate_all_permutations(
            strategies,
            max_combo_size=max_combo_size,
            logic_types=[
                CombinationLogic.WEIGHTED,
                CombinationLogic.MAJORITY,
                CombinationLogic.AND
            ]
        )
        all_candidates.extend(combos)
    
    logger.info(f"Generated {len(all_candidates)} total candidates")
    return all_candidates


def score_strategies(
    strategies: List[StrategyDNA],
    symbol: str,
    regime: MarketRegime,
    registry: StrategyRegistry
) -> List[tuple]:
    """Score strategies and return sorted list of (strategy, score)."""
    scored = []
    
    for strategy in strategies:
        # Check for cached backtest results
        perf = registry.get_strategy_performance(strategy.strategy_id, symbol)
        
        if perf:
            # Use historical performance
            latest = perf[0]
            score = latest.get('sharpe_ratio', 0) * 0.4 + \
                   latest.get('win_rate', 0) * 0.3 + \
                   (1 - abs(latest.get('max_drawdown_pct', 0))) * 0.3
        else:
            # Use default scoring based on DNA genes
            score = 0.5  # Neutral default
            
            # Boost for matching regime preferences
            if regime.value in strategy.genes.get('regime_preferences', []):
                score += 0.2
            
            # Boost for symbol specialization
            if strategy.symbol_specialization == symbol:
                score += 0.15
        
        scored.append((strategy, score))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# Price cache to avoid repeated API calls within a single run
_price_cache: Dict[str, float] = {}

def _fetch_live_price(symbol: str) -> float:
    """Fetch live price from Binance API with fallbacks."""
    if symbol in _price_cache:
        return _price_cache[symbol]

    binance_sym = f"{symbol}USDT"
    urls = [
        f"https://api.binance.com/api/v3/ticker/price?symbol={binance_sym}",
        f"https://api1.binance.com/api/v3/ticker/price?symbol={binance_sym}",
        f"https://data-api.binance.vision/api/v3/ticker/price?symbol={binance_sym}",
        f"https://api.binance.us/api/v3/ticker/price?symbol={binance_sym}",
        f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={binance_sym}",
    ]

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GenomePicks/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if "price" in data:
                    price = float(data["price"])
                elif "result" in data and "list" in data["result"]:
                    price = float(data["result"]["list"][0]["lastPrice"])
                else:
                    continue
                _price_cache[symbol] = price
                return price
        except Exception:
            continue

    # Last resort fallback — these should rarely be hit
    fallback = {"BTC": 67500, "ETH": 1970, "SOL": 85, "AVAX": 20, "LINK": 14,
                "ADA": 0.65, "DOT": 5.5, "DOGE": 0.09, "XRP": 2.3, "BNB": 600}
    price = fallback.get(symbol, 100)
    logging.warning(f"Using fallback price for {symbol}: ${price}")
    _price_cache[symbol] = price
    return price


def generate_pick(
    strategy: StrategyDNA,
    symbol: str,
    direction: str,
    confidence: float,
    current_price: float
) -> Dict:
    """Generate a single pick with TP/SL levels."""
    # Calculate position metrics based on strategy DNA
    risk_profile = strategy.genes.get('risk_profile', 'moderate')
    
    # Risk/reward based on profile
    risk_reward_map = {
        'conservative': 1.5,
        'moderate': 2.0,
        'aggressive': 2.5,
        'degen': 3.0
    }
    risk_reward = risk_reward_map.get(risk_profile, 2.0)
    
    # Position size based on profile
    position_size_map = {
        'conservative': 0.05,
        'moderate': 0.10,
        'aggressive': 0.15,
        'degen': 0.25
    }
    position_pct = position_size_map.get(risk_profile, 0.10)
    
    # Calculate TP/SL
    if direction == "LONG":
        stop_loss = current_price * 0.95  # 5% stop
        take_profit = current_price * (1 + (1 - 0.95) * risk_reward)
    else:
        stop_loss = current_price * 1.05  # 5% stop
        take_profit = current_price * (1 - (0.05) * risk_reward)
    
    # Generate pick ID
    pick_id = f"pick_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{symbol}_{direction[:1]}"
    
    return {
        "id": pick_id,
        "symbol": f"{symbol}USDT",
        "direction": direction,
        "entry_price": round(current_price, 2),
        "take_profit": round(take_profit, 2),
        "stop_loss": round(stop_loss, 2),
        "strategy_dna": {
            "strategy_id": strategy.strategy_id,
            "name": strategy.name,
            "dna_hash": strategy.dna_hash,
            "component_strategies": strategy.parent_strategies,
            "combination_logic": strategy.genes.get('combination_logic', 'SINGLE'),
            "genes": strategy.genes
        },
        "confidence": round(confidence, 2),
        "risk_reward": risk_reward,
        "position_size": {
            "percent_of_account": position_pct,
            "leverage": strategy.genes.get('leverage', 1)
        },
        "timeframe": strategy.genes.get('timeframe', '1h'),
        "expected_hold_hours": 24,
        "market_regime": None,  # Will be filled
        "signal_metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "signal_strength": round(confidence * 10, 1)
        },
        "execution_plan": {
            "entry_type": "market",
            "take_profit_type": "limit",
            "stop_loss_type": "stop_market",
            "trailing_stop": strategy.genes.get('trailing_stop', False)
        },
        "status": "pending",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }


def generate_picks(
    symbols: List[str] = None,
    regime: Optional[MarketRegime] = None,
    max_picks: int = 5,
    catalog_path: str = "genome/data/unified_strategy_catalog.json",
    output_path: str = "genome/active_picks.json",
    tier_filter: bool = False
) -> Dict:
    """
    Generate active picks for trading.
    
    This is the main function that orchestrates the pick generation process.
    """
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL"]
    
    logger.info(f"Generating picks for symbols: {symbols}")
    
    # Initialize components
    engine = DNAPermutationEngine()
    registry = StrategyRegistry()
    
    # Detect regime if not provided
    if regime is None:
        regime = detect_current_regime()
    logger.info(f"Current regime: {regime.value}")
    
    # Load strategies
    strategies = load_strategy_catalog(catalog_path)
    if not strategies:
        logger.error("No strategies loaded")
        return {"error": "No strategies available"}
    
    # Filter by regime
    regime_strategies = filter_strategies_by_regime(strategies, regime, catalog_path)
    
    all_picks = []
    
    for symbol in symbols:
        logger.info(f"Processing {symbol}...")
        
        # Filter for symbol
        symbol_strategies = filter_strategies_by_symbol(regime_strategies, symbol)
        
        # Generate permutations
        candidates = generate_permutations(symbol_strategies, engine)
        
        # Score and rank
        scored = score_strategies(candidates, symbol, regime, registry)

        # Tier-gate: skip strategies below SANDBOX tier
        if tier_filter:
            scored = [(s, score) for s, score in scored
                      if should_emit_pick(_get_strategy_tier(s.strategy_id))]

        # Generate pick from top strategy
        if scored:
            top_strategy, top_score = scored[0]
            
            # Fetch live price from Binance API
            current_price = _fetch_live_price(symbol)
            
            # Determine direction based on strategy DNA
            entry_logic = top_strategy.genes.get('entry_logic', '')
            if 'short' in entry_logic or 'crossunder' in entry_logic or 'overbought' in entry_logic:
                direction = "SHORT"
            else:
                direction = "LONG"
            
            pick = generate_pick(
                top_strategy,
                symbol,
                direction,
                min(top_score, 0.95),  # Cap confidence at 95%
                current_price
            )
            pick['market_regime'] = regime.value
            
            all_picks.append(pick)
            
            # Record in registry
            registry.record_signal({
                'strategy_id': top_strategy.strategy_id,
                'symbol': pick['symbol'],
                'direction': direction,
                'entry_price': current_price,
                'take_profit': pick['take_profit'],
                'stop_loss': pick['stop_loss'],
                'confidence': pick['confidence'],
                'risk_reward': pick['risk_reward'],
                'position_size': pick['position_size']['percent_of_account'],
                'market_regime': regime.value
            })
    
    # Build output
    output = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "generator_version": "1.0.0",
            "engine": "DNA_Permutation_Engine",
            "market_regime": regime.value,
            "total_picks": len(all_picks),
            "risk_profile": "moderate"
        },
        "picks": all_picks[:max_picks],
        "portfolio_summary": {
            "total_exposure_percent": sum(p['position_size']['percent_of_account'] for p in all_picks[:max_picks]) * 100,
            "weighted_avg_confidence": sum(p['confidence'] for p in all_picks[:max_picks]) / len(all_picks) if all_picks else 0,
            "max_concurrent_positions": max_picks
        },
        "audit_trail": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "picks_generated",
                "details": {
                    "symbols": symbols,
                    "regime": regime.value,
                    "strategies_evaluated": len(strategies),
                    "picks_generated": len(all_picks)
                }
            }
        ],
        "next_update": (datetime.utcnow() + timedelta(hours=4)).isoformat()
    }
    
    # Write to file
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda picks, label="": picks
    output["picks"] = sanitize_active_picks(output.get("picks", []), "genome_generate")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Generated {len(all_picks)} picks, written to {output_path}")
    return output


def main():
    parser = argparse.ArgumentParser(description='Generate active trading picks from DNA strategies')
    parser.add_argument('--symbols', nargs='+', default=['BTC', 'ETH', 'SOL'],
                        help='Symbols to generate picks for')
    parser.add_argument('--regime', type=str, default=None,
                        help='Force market regime (trending_up, trending_down, ranging, volatile)')
    parser.add_argument('--max-picks', type=int, default=5,
                        help='Maximum number of picks to generate')
    parser.add_argument('--output', type=str, default='genome/active_picks.json',
                        help='Output file path')
    parser.add_argument('--catalog', type=str, default='genome/data/unified_strategy_catalog.json',
                        help='Strategy catalog path')
    parser.add_argument('--tier-filter', action='store_true', default=False,
                        help='Only emit picks from SANDBOX+ tier strategies')

    args = parser.parse_args()
    
    # Parse regime if provided
    regime = None
    if args.regime:
        try:
            regime = MarketRegime(args.regime)
        except ValueError:
            logger.error(f"Invalid regime: {args.regime}")
            return 1
    
    # Generate picks
    result = generate_picks(
        symbols=args.symbols,
        regime=regime,
        max_picks=args.max_picks,
        catalog_path=args.catalog,
        output_path=args.output,
        tier_filter=args.tier_filter
    )
    
    if 'error' in result:
        logger.error(result['error'])
        return 1
    
    print(f"\nSuccessfully generated {result['metadata']['total_picks']} picks")
    print(f"Regime: {result['metadata']['market_regime']}")
    print(f"Output: {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

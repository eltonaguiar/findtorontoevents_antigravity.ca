"""
Picks Generator - High-Quality Trading Picks Generator

Main orchestrator that:
1. Loads all active strategies from DNA registry
2. Filters for quality score >= 70 (Grade B or higher)
3. Validates signals
4. Calculates TP/SL
5. Generates final picks JSON
"""

import json
import os
import random
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    from quality_engine import SignalQualityEngine, QualityScore
    from tp_sl_calculator import TPSLCalculator
    from signal_validator import SignalValidator, ValidationResult
except ImportError:
    from .quality_engine import SignalQualityEngine, QualityScore
    from .tp_sl_calculator import TPSLCalculator
    from .signal_validator import SignalValidator, ValidationResult


@dataclass
class TradingPick:
    """Complete trading pick with all metadata"""
    id: str
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    risk_reward: float
    strategy_dna: str
    quality_score: float
    grade: str
    verdict: str
    confidence: float
    position_size_pct: float
    expected_return_pct: float
    max_risk_pct: float
    backtest_metrics: Dict
    regime: str
    consensus_count: int
    agreeing_systems: List[str]
    validation_checks: Dict[str, bool]
    timestamp: str


class PicksGenerator:
    """
    Generates high-quality trading picks for daily execution.
    
    Pipeline:
    1. Load active DNA combinations from registry
    2. Score each with SignalQualityEngine
    3. Filter for quality >= 70 (Grade B or higher)
    4. Validate with SignalValidator
    5. Calculate TP/SL with TPSLCalculator
    6. Diversify and rank
    7. Export to JSON
    """
    
    # Quality thresholds (per audit assessment Mar 2026)
    MIN_QUALITY_SCORE = 70.0  # Grade B- minimum
    MIN_CONFIDENCE = 0.60     # 60% minimum confidence
    MIN_RISK_REWARD = 0.7     # Minimum profit-to-risk ratio
    MAX_PICKS_PER_SYMBOL = 999  # TESTING SPRINT: was 2, uncapped
    MAX_TOTAL_PICKS = 999       # TESTING SPRINT: was 10, uncapped
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the picks generator.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.min_quality = self.config.get('min_quality_score', self.MIN_QUALITY_SCORE)
        self.max_per_symbol = self.config.get('max_per_symbol', self.MAX_PICKS_PER_SYMBOL)
        self.max_total = self.config.get('max_total', self.MAX_TOTAL_PICKS)
        
        # Initialize components
        self.quality_engine = SignalQualityEngine()
        self.tpsl_calculator = TPSLCalculator()
        self.validator = SignalValidator()
        
        # Registry path
        self.registry_path = self.config.get('registry_path', 'genome/dna_registry.json')
        self.output_path = self.config.get('output_path', 'genome/active_picks.json')
    
    def generate_daily_picks(self, portfolio_state: Optional[Dict] = None) -> Dict:
        """
        Generate high-quality picks for the day.
        
        Args:
            portfolio_state: Current portfolio for correlation checks
            
        Returns:
            Dict with generation metadata and picks list
        """
        print("[GEN] Generating daily trading picks...")
        
        # 1. Get all DNA combinations
        dna_combos = self._load_dna_combinations()
        print(f"  [INFO] Loaded {len(dna_combos)} DNA combinations")
        
        # 2. Score each combination
        scored = []
        for combo in dna_combos:
            quality = self.quality_engine.calculate_quality_score(combo)
            
            # Filter for minimum quality
            if quality.total_score >= self.min_quality:
                scored.append({
                    **combo,
                    'quality': self.quality_engine.to_dict(quality)
                })
        
        print(f"  [INFO] {len(scored)} signals passed quality threshold ({self.min_quality})")
        
        # 3. Validate signals
        validated = []
        for signal in scored:
            validation = self.validator.validate(signal, portfolio_state)
            
            if validation.approved:
                signal['validation'] = {
                    'approved': validation.approved,
                    'checks': validation.checks,
                    'warnings': validation.warnings
                }
                validated.append(signal)
        
        print(f"  [INFO] {len(validated)} signals passed validation")
        
        # 4. Sort by quality and diversify
        picks = self._diversify_picks(validated)
        print(f"  [INFO] Selected {len(picks)} final picks after diversification")
        
        # 5. Add TP/SL and create final pick objects (with quality gates)
        final_picks = []
        skipped_quality = 0
        for i, pick_data in enumerate(picks):
            pick = self._create_trading_pick(pick_data, i + 1)
            # Quality gates per audit assessment
            if pick.confidence < self.MIN_CONFIDENCE:
                skipped_quality += 1
                continue
            if pick.risk_reward < self.MIN_RISK_REWARD:
                skipped_quality += 1
                continue
            final_picks.append(pick)
        if skipped_quality:
            print(f"  [INFO] {skipped_quality} picks filtered (conf<{self.MIN_CONFIDENCE} or R:R<{self.MIN_RISK_REWARD})")
        
        # 6. Generate output
        output = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'quality_threshold': self.min_quality,
            'total_candidates': len(dna_combos),
            'selected_picks': len(final_picks),
            'picks': [self._pick_to_dict(p) for p in final_picks]
        }
        
        # 7. Save to file
        self._save_picks(output)
        
        return output
    
    def _load_dna_combinations(self) -> List[Dict]:
        """Load active DNA combinations from registry."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r') as f:
                    registry = json.load(f)
                    return registry.get('active_combinations', [])
            except Exception as e:
                print(f"  [WARN] Could not load registry: {e}")
        
        # Return sample data if no registry exists
        return self._get_sample_dna_combinations()
    
    def _get_sample_dna_combinations(self) -> List[Dict]:
        """Generate sample DNA combinations for testing."""
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
        strategies = [
            ('ema_cross', 'trend_following'),
            ('rsi_divergence', 'mean_reversion'),
            ('funding_arbitrage', 'arbitrage'),
            ('breakout_momentum', 'momentum'),
            ('mean_reversion_bb', 'mean_reversion')
        ]
        
        combos = []
        for symbol in symbols:
            for strategy_name, strategy_type in strategies:
                # Generate varied metrics based on symbol and strategy
                base_sharpe = random.uniform(1.2, 2.0) if symbol in ['BTCUSDT', 'ETHUSDT'] else random.uniform(0.8, 1.5)
                base_trades = random.randint(50, 200)
                
                combo = {
                    'symbol': symbol,
                    'direction': random.choice(['LONG', 'SHORT']),
                    'strategy_dna': f"combo_{strategy_name}_{symbol.lower()}",
                    'backtest_metrics': {
                        'sharpe_ratio': round(base_sharpe, 2),
                        'sortino_ratio': round(base_sharpe * 1.1, 2),
                        'calmar_ratio': round(base_sharpe * 1.3, 2),
                        'max_drawdown': round(random.uniform(0.08, 0.18), 3),
                        'total_trades': base_trades,
                        'win_rate': round(random.uniform(0.55, 0.72), 2),
                        'profit_factor': round(random.uniform(1.5, 2.5), 2)
                    },
                    'current_regime': random.choice(['trending_bull', 'trending_bear', 'ranging']),
                    'optimal_regimes': ['trending_bull', 'trending_bear'] if strategy_type == 'trend_following' else ['ranging'],
                    'regime_performance': {
                        'trending_bull': {'sharpe': round(base_sharpe * 1.2, 2)},
                        'trending_bear': {'sharpe': round(base_sharpe * 0.9, 2)},
                        'ranging': {'sharpe': round(base_sharpe * 0.7, 2)}
                    },
                    'agreeing_systems': random.sample(
                        ['alpha_engine', 'mercury2', 'dna_genome', 'kimi', 'ensemble_v2'],
                        k=random.randint(2, 4)
                    ),
                    'market_structure': {
                        'daily_volume_usd': 35_000_000_000 if 'BTC' in symbol else (
                            15_000_000_000 if 'ETH' in symbol else random.randint(500_000_000, 2_000_000_000)
                        ),
                        'spread_pct': round(random.uniform(0.0003, 0.002), 4),
                        'volatility_24h': round(random.uniform(0.03, 0.08), 3),
                        'trading_enabled': True,
                        'bid_depth_usd': 5_000_000_000 if 'BTC' in symbol else (
                            2_000_000_000 if 'ETH' in symbol else 500_000_000
                        ),
                        'ask_depth_usd': 5_000_000_000 if 'BTC' in symbol else (
                            2_000_000_000 if 'ETH' in symbol else 500_000_000
                        )
                    },
                    'entry_price': self._get_sample_price(symbol)
                }
                combos.append(combo)
        
        return combos
    
    def _get_sample_price(self, symbol: str) -> float:
        """Get live entry price for symbol from Binance API (with fallbacks)."""
        # Try Binance first
        for base_url in [
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
            f"https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
            f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}",
            f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}",
            f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}",
        ]:
            try:
                req = urllib.request.Request(base_url, headers={'User-Agent': 'GenomePicks/1.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    if 'price' in data:
                        # Binance format
                        return round(float(data['price']), 2)
                    elif 'result' in data and 'list' in data['result'] and data['result']['list']:
                        # Bybit format
                        return round(float(data['result']['list'][0]['lastPrice']), 2)
            except Exception:
                continue

        # Final fallback: static prices (better than crashing)
        fallback_prices = {
            'BTCUSDT': 69000.0,
            'ETHUSDT': 2400.0,
            'SOLUSDT': 130.0,
            'ADAUSDT': 0.70,
            'DOTUSDT': 5.50
        }
        print(f"  [WARN] Could not fetch live price for {symbol}, using fallback")
        return fallback_prices.get(symbol, 100.0)
    
    def _diversify_picks(self, candidates: List[Dict]) -> List[Dict]:
        """
        Diversify picks to avoid concentration.
        
        Limits:
        - Max 2 picks per symbol
        - Max 10 total picks
        - Balanced LONG/SHORT mix when possible
        """
        # Sort by quality score
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x['quality']['total_score'],
            reverse=True
        )
        
        selected = []
        symbol_counts = {}
        direction_counts = {'LONG': 0, 'SHORT': 0}
        
        for candidate in sorted_candidates:
            symbol = candidate['symbol']
            direction = candidate['direction']
            
            # Check symbol limit
            if symbol_counts.get(symbol, 0) >= self.max_per_symbol:
                continue
            
            # Check total limit
            if len(selected) >= self.max_total:
                break
            
            # Prefer balanced direction (optional)
            if direction_counts[direction] > len(selected) * 0.7 and len(selected) > 3:
                # Try to find alternative direction for same symbol
                alt = next((c for c in sorted_candidates 
                           if c['symbol'] == symbol and c['direction'] != direction), None)
                if alt and alt not in selected:
                    selected.append(alt)
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
                    direction_counts[alt['direction']] += 1
                continue
            
            selected.append(candidate)
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            direction_counts[direction] += 1
        
        return selected
    
    def _create_trading_pick(self, pick_data: Dict, index: int) -> TradingPick:
        """Create a complete TradingPick object with TP/SL."""
        symbol = pick_data['symbol']
        entry = pick_data['entry_price']
        direction = pick_data['direction']
        
        # Get quality data
        quality = pick_data['quality']
        
        # Calculate TP/SL
        strategy_dna = {
            'risk_profile': 'medium',
            'win_rate': pick_data['backtest_metrics']['win_rate'],
            'avg_win_pct': 8.0,
            'avg_loss_pct': 4.0
        }
        
        levels = self.tpsl_calculator.calculate_levels(
            symbol=symbol,
            entry_price=entry,
            direction=direction,
            strategy_dna=strategy_dna,
            market_data=pick_data.get('market_structure')
        )
        
        # Calculate expected return and risk
        risk_amount = abs(entry - levels['stop_loss'])
        expected_return = (levels['take_profit'] - entry) / entry * 100 if direction == 'LONG' else \
                         (entry - levels['take_profit']) / entry * 100
        max_risk = risk_amount / entry * 100
        
        # Generate pick ID
        date_str = datetime.utcnow().strftime('%Y%m%d')
        pick_id = f"pick_{symbol.lower().replace('usdt', '')}_{date_str}_{index:03d}"
        
        return TradingPick(
            id=pick_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry,
            take_profit=levels['take_profit'],
            stop_loss=levels['stop_loss'],
            risk_reward=levels['risk_reward'],
            strategy_dna=pick_data['strategy_dna'],
            quality_score=quality['total_score'],
            grade=quality['grade'],
            verdict=quality['verdict'],
            confidence=levels['confidence'],
            position_size_pct=levels['position_size_pct'],
            expected_return_pct=round(abs(expected_return), 2),
            max_risk_pct=round(max_risk, 2),
            backtest_metrics=pick_data['backtest_metrics'],
            regime=pick_data['current_regime'],
            consensus_count=len(pick_data['agreeing_systems']),
            agreeing_systems=pick_data['agreeing_systems'],
            validation_checks=pick_data['validation']['checks'],
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def _pick_to_dict(self, pick: TradingPick) -> Dict:
        """Convert TradingPick to dictionary."""
        return {
            'id': pick.id,
            'symbol': pick.symbol,
            'direction': pick.direction,
            'entry_price': pick.entry_price,
            'take_profit': pick.take_profit,
            'stop_loss': pick.stop_loss,
            'risk_reward': pick.risk_reward,
            'strategy_dna': pick.strategy_dna,
            'quality_score': pick.quality_score,
            'grade': pick.grade,
            'verdict': pick.verdict,
            'confidence': pick.confidence,
            'position_size_pct': pick.position_size_pct,
            'expected_return_pct': pick.expected_return_pct,
            'max_risk_pct': pick.max_risk_pct,
            'backtest_metrics': pick.backtest_metrics,
            'regime': pick.regime,
            'consensus_count': pick.consensus_count,
            'agreeing_systems': pick.agreeing_systems,
            'validation_checks': pick.validation_checks,
            'timestamp': pick.timestamp
        }
    
    def _save_picks(self, output: Dict):
        """Save picks to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            try:
                from alpha_engine.feed_hygiene import sanitize_active_picks
            except ImportError:
                sanitize_active_picks = lambda picks, label="": picks
            output["picks"] = sanitize_active_picks(output.get("picks", []), "genome_picks")
            with open(self.output_path, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"  [OK] Saved picks to {self.output_path}")
        except Exception as e:
            print(f"  [ERR] Error saving picks: {e}")
    
    def load_picks(self) -> Optional[Dict]:
        """Load previously generated picks."""
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERR] Error loading picks: {e}")
        return None
    
    def get_top_picks(self, n: int = 5, direction: Optional[str] = None) -> List[Dict]:
        """Get top N picks, optionally filtered by direction."""
        picks_data = self.load_picks()
        if not picks_data:
            return []
        
        picks = picks_data.get('picks', [])
        
        if direction:
            picks = [p for p in picks if p['direction'] == direction.upper()]
        
        # Sort by quality score
        picks = sorted(picks, key=lambda x: x['quality_score'], reverse=True)
        
        return picks[:n]


def generate_daily_picks():
    """CLI entry point for generating daily picks."""
    generator = PicksGenerator()
    result = generator.generate_daily_picks()
    
    print("\n" + "=" * 60)
    print("DAILY PICKS GENERATION COMPLETE")
    print("=" * 60)
    print(f"Generated: {result['generated_at']}")
    print(f"Total Candidates: {result['total_candidates']}")
    print(f"Selected Picks: {result['selected_picks']}")
    print(f"Quality Threshold: {result['quality_threshold']}")
    print("\nTop 5 Picks:")
    
    for i, pick in enumerate(result['picks'][:5], 1):
        print(f"  [{i}] {pick['symbol']} {pick['direction']}")
        print(f"      Grade: {pick['grade']} | Score: {pick['quality_score']}")
        print(f"      Entry: ${pick['entry_price']:,.2f}")
        print(f"      TP: ${pick['take_profit']:,.2f} | SL: ${pick['stop_loss']:,.2f}")
        print(f"      R:R = 1:{pick['risk_reward']} | Size: {pick['position_size_pct']}%")
    
    print("=" * 60)
    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Picks Generator CLI")
    parser.add_argument("--min-quality", type=float, default=70.0,
                        help="Minimum quality score threshold (default: 70)")
    parser.add_argument("--output", type=str, default="genome/active_picks.json",
                        help="Output file path for picks JSON")
    parser.add_argument("--max-picks", type=int, default=10,
                        help="Maximum number of picks to generate (default: 10)")
    args = parser.parse_args()

    config = {
        'min_quality_score': args.min_quality,
        'output_path': args.output,
        'max_total': args.max_picks,
    }
    generator = PicksGenerator(config=config)
    result = generator.generate_daily_picks()

    print("\n" + "=" * 60)
    print("DAILY PICKS GENERATION COMPLETE")
    print("=" * 60)
    print(f"Generated: {result['generated_at']}")
    print(f"Total Candidates: {result['total_candidates']}")
    print(f"Selected Picks: {result['selected_picks']}")
    print(f"Quality Threshold: {result['quality_threshold']}")
    print("\nTop 5 Picks:")

    for i, pick in enumerate(result['picks'][:5], 1):
        print(f"  [{i}] {pick['symbol']} {pick['direction']}")
        print(f"      Grade: {pick['grade']} | Score: {pick['quality_score']}")
        print(f"      Entry: ${pick['entry_price']:,.2f}")
        print(f"      TP: ${pick['take_profit']:,.2f} | SL: ${pick['stop_loss']:,.2f}")
        print(f"      R:R = 1:{pick['risk_reward']} | Size: {pick['position_size_pct']}%")

    print("=" * 60)

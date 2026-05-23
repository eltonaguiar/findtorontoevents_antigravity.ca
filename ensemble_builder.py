#!/usr/bin/env python3
"""
Strategy Ensemble Builder

Builds ensembles from the 6 Tier 1 passing strategies.
Uses voting/consensus system rather than individual strategy signals.

Ensembles:
1. trend_ensemble - Multi-timeframe trend strategies
2. volatility_ensemble - Crisis/volatility strategies
3. mean_reversion_ensemble - Reversion strategies
4. arbitrage_ensemble - Market-neutral strategies
5. master_ensemble - All strategies with regime filtering
"""

import json
import sqlite3
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import sys

sys.path.insert(0, str(Path(__file__).parent))
from incubator.testing import load_data

TIERED_RESULTS = Path("battleground/data/tiered_backtest_results_20260227_160805.json")
ENSEMBLE_CONFIG = Path("battleground/data/ensemble_config.json")


@dataclass
class Signal:
    """Strategy signal"""
    strategy: str
    direction: str  # BUY, SELL, NEUTRAL
    confidence: float  # 0-1
    entry_price: float
    take_profit: Optional[float]
    stop_loss: Optional[float]
    timestamp: str


@dataclass
class EnsembleSignal:
    """Combined ensemble signal"""
    ensemble: str
    direction: str
    confidence: float
    agreement: int  # How many strategies agree
    total_strategies: int
    signals: List[Signal]
    entry_price: float
    take_profit: Optional[float]
    stop_loss: Optional[float]
    
    def to_dict(self) -> Dict:
        return {
            'ensemble': self.ensemble,
            'direction': self.direction,
            'confidence': round(self.confidence, 2),
            'agreement': f"{self.agreement}/{self.total_strategies}",
            'entry_price': self.entry_price,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'individual_signals': [
                {
                    'strategy': s.strategy,
                    'direction': s.direction,
                    'confidence': round(s.confidence, 2)
                }
                for s in self.signals
            ]
        }


class EnsembleBuilder:
    """Builds and runs strategy ensembles"""
    
    def __init__(self):
        self.tier1_strategies = self._load_tier1_strategies()
        self.ensembles = self._define_ensembles()
        
    def _load_tier1_strategies(self) -> Dict[str, Dict]:
        """Load the 6 Tier 1 passing strategies"""
        if not TIERED_RESULTS.exists():
            return {}
        
        with open(TIERED_RESULTS, 'r') as f:
            data = json.load(f)
        
        strategies = {}
        for name, result in data['results']['tier_1'].items():
            if result.get('passed') and result.get('best_result'):
                strategies[name] = {
                    'name': name,
                    'agent_id': result.get('source', 'unknown'),
                    'best_pair': result['best_result'].get('pair'),
                    'best_direction': result['best_result'].get('direction', 'LONG'),
                    'backtest_sharpe': result['best_result'].get('sharpe_ratio'),
                    'backtest_wr': result['best_result'].get('win_rate'),
                    'file_path': self._find_strategy_file(name, result.get('source', 'unknown'))
                }
        
        return strategies
    
    def _find_strategy_file(self, name: str, agent_id: str) -> Optional[Path]:
        """Find strategy Python file"""
        dirs = {
            'baby': Path('baby_strategies'),
            'codex': Path('incubator/agents/codex_gpt5'),
            'cursor': Path('incubator/agents/cursor_ai'),
            'opus': Path('incubator/agents/claude_opus_batch'),
            'alpha': Path('incubator/agents/team_alpha'),
            'web': Path('incubator/agents/web_ai'),
        }
        
        dir_path = dirs.get(agent_id)
        if not dir_path:
            return None
        
        for f in dir_path.glob('*.py'):
            if f.stem == name or name in f.stem:
                return f
        return None
    
    def _define_ensembles(self) -> Dict[str, List[str]]:
        """Define which strategies belong to which ensemble"""
        # Categorize the 6 Tier 1 strategies
        return {
            'trend_ensemble': [
                'crypto_multiframe_breakout_pulse_v1',
                'nylondon_flow_session_momentum_v1',
                'supertrend_proxy'
            ],
            'volatility_ensemble': [
                'crypto_multiframe_breakout_pulse_v1',  # Can work in both
                'funding_momentum'
            ],
            'mean_reversion_ensemble': [
                'social_sentiment_momentum_v1',
                'crypto_multiframe_regime_router_v1'
            ],
            'arbitrage_ensemble': [
                'funding_momentum',
                'social_sentiment_momentum_v1'
            ],
            'master_ensemble': list(self.tier1_strategies.keys())  # All 6
        }
    
    def load_strategy_class(self, file_path: Path):
        """Load strategy class"""
        try:
            spec = importlib.util.spec_from_file_location(f"ens_{file_path.stem}", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name.endswith('Strategy'):
                    return attr
            return None
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def get_strategy_signal(self, strategy_info: Dict, pair: str) -> Optional[Signal]:
        """Get current signal from a strategy"""
        if not strategy_info.get('file_path'):
            return None
        
        try:
            strategy_class = self.load_strategy_class(strategy_info['file_path'])
            if not strategy_class:
                return None
            
            data = load_data(pair, '1h')
            if data is None or len(data) < 100:
                return None
            
            strategy = strategy_class()
            signals = strategy.generate_signals(data, pair.replace('/', ''))
            
            if not signals:
                return Signal(
                    strategy=strategy_info['name'],
                    direction='NEUTRAL',
                    confidence=0,
                    entry_price=data['close'].iloc[-1],
                    take_profit=None,
                    stop_loss=None,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            
            signal = signals[-1] if isinstance(signals, list) else signals
            
            return Signal(
                strategy=strategy_info['name'],
                direction=getattr(signal, 'direction', 'NEUTRAL'),
                confidence=0.7 if getattr(signal, 'direction', 'NEUTRAL') in ['BUY', 'SELL'] else 0,
                entry_price=getattr(signal, 'entry_price', data['close'].iloc[-1]),
                take_profit=getattr(signal, 'take_profit', None),
                stop_loss=getattr(signal, 'stop_loss', None),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        except Exception as e:
            print(f"Error getting signal for {strategy_info['name']}: {e}")
            return None
    
    def run_ensemble(self, ensemble_name: str, pair: str, 
                     min_agreement: int = 2) -> Optional[EnsembleSignal]:
        """
        Run an ensemble and return consensus signal
        
        Args:
            ensemble_name: Name of ensemble to run
            pair: Trading pair
            min_agreement: Minimum strategies needed for signal (voting threshold)
        """
        if ensemble_name not in self.ensembles:
            print(f"Unknown ensemble: {ensemble_name}")
            return None
        
        strategy_names = self.ensembles[ensemble_name]
        signals = []
        
        print(f"\n[ENSEMBLE: {ensemble_name}]")
        print(f"Running {len(strategy_names)} strategies on {pair}...")
        
        for name in strategy_names:
            if name not in self.tier1_strategies:
                continue
            
            strat_info = self.tier1_strategies[name]
            signal = self.get_strategy_signal(strat_info, pair)
            
            if signal:
                signals.append(signal)
                status = "✓" if signal.direction in ['BUY', 'SELL'] else "○"
                print(f"  {status} {name[:35]:<35} -> {signal.direction}")
        
        if len(signals) < min_agreement:
            print(f"  Insufficient signals ({len(signals)} < {min_agreement})")
            return None
        
        # Count votes
        buy_votes = sum(1 for s in signals if s.direction == 'BUY')
        sell_votes = sum(1 for s in signals if s.direction == 'SELL')
        neutral_votes = len(signals) - buy_votes - sell_votes
        
        # Determine consensus
        if buy_votes >= min_agreement and buy_votes > sell_votes:
            consensus_dir = 'BUY'
            confidence = buy_votes / len(signals)
            agreement = buy_votes
        elif sell_votes >= min_agreement and sell_votes > buy_votes:
            consensus_dir = 'SELL'
            confidence = sell_votes / len(signals)
            agreement = sell_votes
        else:
            print(f"  No consensus (BUY: {buy_votes}, SELL: {sell_votes}, NEUTRAL: {neutral_votes})")
            return None
        
        # Average entry/TP/SL from agreeing signals
        agreeing_signals = [s for s in signals if s.direction == consensus_dir]
        avg_entry = sum(s.entry_price for s in agreeing_signals) / len(agreeing_signals)
        
        tp_values = [s.take_profit for s in agreeing_signals if s.take_profit]
        avg_tp = sum(tp_values) / len(tp_values) if tp_values else None
        
        sl_values = [s.stop_loss for s in agreeing_signals if s.stop_loss]
        avg_sl = sum(sl_values) / len(sl_values) if sl_values else None
        
        ensemble_signal = EnsembleSignal(
            ensemble=ensemble_name,
            direction=consensus_dir,
            confidence=confidence,
            agreement=agreement,
            total_strategies=len(signals),
            signals=agreeing_signals,
            entry_price=avg_entry,
            take_profit=avg_tp,
            stop_loss=avg_sl
        )
        
        print(f"  → CONSENSUS: {consensus_dir} ({agreement}/{len(signals)} agree, {confidence:.0%} confidence)")
        print(f"    Entry: {avg_entry:.2f}, TP: {avg_tp:.2f if avg_tp else 0:.2f}, SL: {avg_sl:.2f if avg_sl else 0:.2f}")
        
        return ensemble_signal
    
    def run_all_ensembles(self, pair: str = "BTC/USDT") -> Dict[str, EnsembleSignal]:
        """Run all ensembles and return signals"""
        results = {}
        
        for ensemble_name in self.ensembles.keys():
            signal = self.run_ensemble(ensemble_name, pair)
            if signal:
                results[ensemble_name] = signal
        
        return results
    
    def save_ensemble_config(self):
        """Save ensemble configuration"""
        config = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tier1_strategies': self.tier1_strategies,
            'ensembles': self.ensembles,
            'rules': {
                'min_agreement': 2,
                'require_tp_sl': True,
                'max_ensemble_overlap': 0.5
            }
        }
        
        ENSEMBLE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        with open(ENSEMBLE_CONFIG, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        print(f"\nEnsemble config saved to {ENSEMBLE_CONFIG}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Strategy Ensemble Builder')
    parser.add_argument('--ensemble', default='master_ensemble', 
                       choices=['trend_ensemble', 'volatility_ensemble', 
                               'mean_reversion_ensemble', 'arbitrage_ensemble', 
                               'master_ensemble', 'all'],
                       help='Which ensemble to run')
    parser.add_argument('--pair', default='BTC/USDT', help='Trading pair')
    parser.add_argument('--agreement', type=int, default=2, 
                       help='Minimum strategies needed for consensus')
    parser.add_argument('--save', action='store_true', help='Save ensemble config')
    
    args = parser.parse_args()
    
    builder = EnsembleBuilder()
    
    print("="*60)
    print("STRATEGY ENSEMBLE BUILDER")
    print("="*60)
    print(f"\nTier 1 Strategies Available: {len(builder.tier1_strategies)}")
    for name, info in builder.tier1_strategies.items():
        print(f"  • {name} (Sharpe: {info['backtest_sharpe']:.2f}, WR: {info['backtest_wr']:.1f}%)")
    
    print(f"\nEnsembles Defined:")
    for ens_name, strategies in builder.ensembles.items():
        print(f"  • {ens_name}: {len(strategies)} strategies")
    
    if args.save:
        builder.save_ensemble_config()
    
    print("\n" + "="*60)
    print("GENERATING SIGNALS")
    print("="*60)
    
    if args.ensemble == 'all':
        results = builder.run_all_ensembles(args.pair)
        
        print("\n" + "="*60)
        print("SUMMARY - ALL ENSEMBLES")
        print("="*60)
        
        if not results:
            print("No ensemble signals generated")
        else:
            for ens_name, signal in results.items():
                print(f"\n{ens_name}:")
                print(f"  Direction: {signal.direction}")
                print(f"  Confidence: {signal.confidence:.0%}")
                print(f"  Agreement: {signal.agreement}/{signal.total_strategies}")
                print(f"  Entry: {signal.entry_price:.2f}")
                
                # Save to file
                signal_file = Path(f"battleground/data/signal_{ens_name}.json")
                signal_file.parent.mkdir(parents=True, exist_ok=True)
                with open(signal_file, 'w') as f:
                    json.dump(signal.to_dict(), f, indent=2)
                print(f"  Saved to: {signal_file}")
    else:
        signal = builder.run_ensemble(args.ensemble, args.pair, args.agreement)
        
        if signal:
            # Save to file
            signal_file = Path(f"battleground/data/signal_{args.ensemble}.json")
            signal_file.parent.mkdir(parents=True, exist_ok=True)
            with open(signal_file, 'w') as f:
                json.dump(signal.to_dict(), f, indent=2)
            print(f"\nSignal saved to: {signal_file}")


if __name__ == "__main__":
    main()

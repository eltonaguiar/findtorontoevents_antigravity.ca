"""
Transaction Cost Model (TCM) for Crypto Trading
================================================
Institutional-grade slippage and fee modeling based on:
TC = a + b·√(size/ADV) + c·spread

This addresses the HIGH IMPACT issue: "We don't model slippage at all. 
A 0.5% slippage on crypto can eat the entire edge."

Usage:
    from transaction_cost_model import TransactionCostModel
    
    tcm = TransactionCostModel()
    cost = tcm.estimate_cost(
        symbol="BTC-USDT",
        trade_size_usd=10000,
        exchange="binance",
        order_type="market"
    )
    
    # In your strategy:
    expected_pnl = gross_pnl - cost
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TCM')


@dataclass
class ExchangeProfile:
    """Exchange-specific trading costs"""
    name: str
    maker_fee: float = 0.001  # 0.1% default
    taker_fee: float = 0.001  # 0.1% default
    base_spread_bps: float = 5.0  # Base spread in basis points
    depth_factor: float = 1.0  # Liquidity multiplier
    avg_daily_volume_usd: float = 1e9  # Default $1B ADV


@dataclass
class TradeEstimate:
    """Complete cost estimate for a trade"""
    symbol: str
    trade_size_usd: float
    exchange: str
    
    # Cost components
    fixed_fee_percent: float = 0.0
    spread_cost_percent: float = 0.0
    market_impact_percent: float = 0.0
    
    # Total
    total_cost_percent: float = 0.0
    total_cost_usd: float = 0.0
    
    # Metadata
    confidence: str = "medium"  # low, medium, high
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        self.total_cost_percent = self.fixed_fee_percent + self.spread_cost_percent + self.market_impact_percent
        self.total_cost_usd = self.trade_size_usd * self.total_cost_percent / 100


class TransactionCostModel:
    """
    Institutional Transaction Cost Model for Crypto
    
    Formula: TC = a + b·√(size/ADV) + c·spread
    
    Where:
    - a = fixed fees (maker/taker)
    - b = market impact coefficient (typically 1-5 bps)
    - c = spread multiplier
    - size = trade size in USD
    - ADV = average daily volume in USD
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.exchanges: Dict[str, ExchangeProfile] = {}
        self.symbol_profiles: Dict[str, Dict] = {}
        self.impact_coefficient: float = 2.0  # bps - market impact factor
        
        self._load_default_profiles()
        if config_path:
            self._load_custom_config(config_path)
    
    def _load_default_profiles(self):
        """Load default exchange profiles"""
        defaults = {
            "binance": ExchangeProfile(
                name="binance",
                maker_fee=0.001,
                taker_fee=0.001,
                base_spread_bps=4.0,
                depth_factor=1.2,
                avg_daily_volume_usd=50e9
            ),
            "coinbase": ExchangeProfile(
                name="coinbase",
                maker_fee=0.004,
                taker_fee=0.006,
                base_spread_bps=6.0,
                depth_factor=1.0,
                avg_daily_volume_usd=8e9
            ),
            "kraken": ExchangeProfile(
                name="kraken",
                maker_fee=0.0016,
                taker_fee=0.0026,
                base_spread_bps=8.0,
                depth_factor=0.8,
                avg_daily_volume_usd=3e9
            ),
            "bybit": ExchangeProfile(
                name="bybit",
                maker_fee=0.0001,
                taker_fee=0.0006,
                base_spread_bps=5.0,
                depth_factor=1.0,
                avg_daily_volume_usd=15e9
            ),
            "okx": ExchangeProfile(
                name="okx",
                maker_fee=0.0008,
                taker_fee=0.001,
                base_spread_bps=6.0,
                depth_factor=0.9,
                avg_daily_volume_usd=10e9
            ),
            "generic": ExchangeProfile(
                name="generic",
                maker_fee=0.001,
                taker_fee=0.001,
                base_spread_bps=10.0,
                depth_factor=0.7,
                avg_daily_volume_usd=1e9
            )
        }
        self.exchanges = defaults
    
    def _load_custom_config(self, path: str):
        """Load custom exchange configurations"""
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                for ex_name, ex_data in config.get('exchanges', {}).items():
                    self.exchanges[ex_name] = ExchangeProfile(
                        name=ex_name,
                        **ex_data
                    )
        except FileNotFoundError:
            logger.warning(f"Config file not found: {path}")
    
    def estimate_cost(
        self,
        symbol: str,
        trade_size_usd: float,
        exchange: str = "binance",
        order_type: str = "taker",  # maker or taker
        spread_bps: Optional[float] = None,
        adv_usd: Optional[float] = None
    ) -> TradeEstimate:
        """
        Estimate total transaction cost for a trade
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            trade_size_usd: Size of trade in USD
            exchange: Exchange name
            order_type: 'maker' or 'taker'
            spread_bps: Optional override for spread (basis points)
            adv_usd: Optional override for ADV
        
        Returns:
            TradeEstimate with all cost components
        """
        # Get exchange profile
        ex = self.exchanges.get(exchange.lower(), self.exchanges['generic'])
        
        # 1. Fixed Fees
        fixed_fee = ex.maker_fee * 100 if order_type == "maker" else ex.taker_fee * 100
        
        # 2. Spread Cost
        if spread_bps is None:
            # Estimate spread based on symbol and exchange
            spread_bps = self._estimate_spread(symbol, ex)
        spread_cost = spread_bps / 100  # Convert bps to percent
        
        # 3. Market Impact
        # Formula: impact = b * sqrt(size / ADV)
        adv = adv_usd or self._estimate_adv(symbol, ex)
        if adv > 0 and trade_size_usd > 0:
            impact_bps = self.impact_coefficient * math.sqrt(trade_size_usd / adv) * 100
            impact_cost = impact_bps / 100  # Convert to percent
        else:
            impact_cost = 0.5  # Default 0.5% if unknown
        
        # Create estimate
        estimate = TradeEstimate(
            symbol=symbol,
            trade_size_usd=trade_size_usd,
            exchange=exchange,
            fixed_fee_percent=fixed_fee,
            spread_cost_percent=spread_cost,
            market_impact_percent=impact_cost
        )
        
        # Set confidence based on data quality
        if exchange in self.exchanges and adv_usd is not None:
            estimate.confidence = "high"
        elif exchange in self.exchanges:
            estimate.confidence = "medium"
        else:
            estimate.confidence = "low"
        
        return estimate
    
    def _estimate_spread(self, symbol: str, exchange: ExchangeProfile) -> float:
        """Estimate bid-ask spread in basis points"""
        base = exchange.base_spread_bps
        
        # Adjust for symbol characteristics
        symbol_upper = symbol.upper()
        
        # Major pairs have tighter spreads
        if any(x in symbol_upper for x in ['BTC', 'ETH']):
            base *= 0.6
        elif any(x in symbol_upper for x in ['SOL', 'ADA', 'DOT', 'AVAX']):
            base *= 1.2
        elif any(x in symbol_upper for x in ['DOGE', 'SHIB', 'PEPE']):
            base *= 2.5
        else:
            # Altcoins
            base *= 2.0
        
        return base * exchange.depth_factor
    
    def _estimate_adv(self, symbol: str, exchange: ExchangeProfile) -> float:
        """Estimate Average Daily Volume"""
        base_adv = exchange.avg_daily_volume_usd
        
        symbol_upper = symbol.upper()
        
        # Rough ADV estimates based on symbol
        if 'BTC' in symbol_upper:
            return base_adv * 0.4  # BTC is ~40% of volume
        elif 'ETH' in symbol_upper:
            return base_adv * 0.25
        elif any(x in symbol_upper for x in ['SOL', 'ADA', 'DOT']):
            return base_adv * 0.05
        else:
            return base_adv * 0.01  # Small alts
    
    def calculate_net_expectancy(
        self,
        gross_expectancy: float,
        avg_trade_size: float,
        avg_holding_period_hours: float,
        exchange: str = "binance"
    ) -> Tuple[float, float]:
        """
        Calculate net expectancy after all costs
        
        Args:
            gross_expectancy: Raw strategy expectancy (%)
            avg_trade_size: Average trade size in USD
            avg_holding_period_hours: How long positions are held
            exchange: Primary exchange
        
        Returns:
            (net_expectancy, total_cost_percent)
        """
        # Estimate entry and exit costs
        entry_cost = self.estimate_cost("BTC-USDT", avg_trade_size, exchange, "taker")
        exit_cost = self.estimate_cost("BTC-USDT", avg_trade_size, exchange, "taker")
        
        # Round-trip cost
        round_trip_cost = entry_cost.total_cost_percent + exit_cost.total_cost_percent
        
        # Funding costs for perps (approximate)
        # Assume 0.01% per 8 hours = 0.03% per day
        funding_per_day = 0.03
        funding_cost = funding_per_day * (avg_holding_period_hours / 24)
        
        total_cost = round_trip_cost + funding_cost
        net_expectancy = gross_expectancy - total_cost
        
        return net_expectancy, total_cost
    
    def audit_strategy_viability(
        self,
        strategy_id: str,
        gross_expectancy: float,
        win_rate: float,
        avg_trade_size: float = 10000,
        sample_size: int = 0
    ) -> Dict[str, any]:
        """
        Audit if a strategy's edge survives transaction costs
        
        Returns viability assessment with recommendations
        """
        # Calculate costs at different trade sizes
        sizes = [1000, 5000, 10000, 50000, 100000]
        cost_analysis = []
        
        for size in sizes:
            net_exp, total_cost = self.calculate_net_expectancy(
                gross_expectancy, size, 24
            )
            cost_analysis.append({
                'trade_size': size,
                'total_cost_percent': round(total_cost, 4),
                'gross_expectancy': round(gross_expectancy, 4),
                'net_expectancy': round(net_exp, 4),
                'viable': net_exp > 0
            })
        
        # Determine max viable size
        viable_sizes = [c for c in cost_analysis if c['viable']]
        max_viable_size = max([c['trade_size'] for c in viable_sizes]) if viable_sizes else 0
        
        # Recommendation
        if not viable_sizes:
            recommendation = "KILL"
            reason = f"Strategy edge ({gross_expectancy:.2f}%) completely consumed by costs"
        elif max_viable_size < 5000:
            recommendation = "INCUBATOR_ONLY"
            reason = f"Only viable at small sizes (<${max_viable_size:,.0f})"
        elif sample_size < 20:
            recommendation = "NEEDS_MORE_DATA"
            reason = f"Edge may be statistical noise (n={sample_size})"
        else:
            recommendation = "APPROVED"
            reason = f"Viable up to ${max_viable_size:,.0f} per trade"
        
        return {
            'strategy_id': strategy_id,
            'gross_expectancy': gross_expectancy,
            'win_rate': win_rate,
            'sample_size': sample_size,
            'cost_analysis': cost_analysis,
            'max_viable_trade_size': max_viable_size,
            'recommendation': recommendation,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_cost_report(self, strategies: List[Dict]) -> Dict:
        """Generate cost audit report for multiple strategies"""
        audits = []
        
        for strat in strategies:
            audit = self.audit_strategy_viability(
                strategy_id=strat.get('id', 'unknown'),
                gross_expectancy=strat.get('expectancy', 0),
                win_rate=strat.get('win_rate', 0),
                avg_trade_size=strat.get('avg_trade_size', 10000),
                sample_size=strat.get('total_trades', 0)
            )
            audits.append(audit)
        
        # Summary stats
        viable = sum(1 for a in audits if a['recommendation'] == 'APPROVED')
        incubator = sum(1 for a in audits if a['recommendation'] == 'INCUBATOR_ONLY')
        killed = sum(1 for a in audits if a['recommendation'] == 'KILL')
        
        return {
            'report_date': datetime.now().isoformat(),
            'summary': {
                'total_strategies': len(audits),
                'approved': viable,
                'incubator_only': incubator,
                'kill': killed,
                'viability_rate': round(viable / len(audits) * 100, 1) if audits else 0
            },
            'audits': audits
        }


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("TRANSACTION COST MODEL - Demo")
    print("=" * 80)
    
    tcm = TransactionCostModel()
    
    # Show cost at different trade sizes
    print("\n[CHART] Cost by Trade Size (BTC on Binance):")
    print("-" * 80)
    print(f"{'Size (USD)':<15} {'Fees':<10} {'Spread':<10} {'Impact':<10} {'Total':<10} {'bps':<10}")
    print("-" * 80)
    
    for size in [1000, 5000, 10000, 50000, 100000, 500000]:
        est = tcm.estimate_cost("BTC-USDT", size, "binance", "taker")
        total_bps = est.total_cost_percent * 100
        print(f"${size:>10,}    {est.fixed_fee_percent:>7.3f}%  {est.spread_cost_percent:>7.3f}%  "
              f"{est.market_impact_percent:>7.3f}%  {est.total_cost_percent:>7.3f}%  {total_bps:>7.1f}")
    
    # Strategy audit
    print("\n" + "=" * 80)
    print("STRATEGY VIABILITY AUDIT")
    print("=" * 80)
    
    test_strategies = [
        {'id': 'baby_battleground', 'expectancy': 0.53, 'win_rate': 0.65, 'total_trades': 128},
        {'id': 'funding_carry', 'expectancy': 1.61, 'win_rate': 0.74, 'total_trades': 51},
        {'id': 'ema_crossover', 'expectancy': -0.05, 'win_rate': 0.48, 'total_trades': 35},
        {'id': 'high_freq_scalper', 'expectancy': 0.15, 'win_rate': 0.52, 'total_trades': 200},
    ]
    
    for strat in test_strategies:
        audit = tcm.audit_strategy_viability(
            strat['id'],
            strat['expectancy'],
            strat['win_rate'],
            sample_size=strat['total_trades']
        )
        
        print(f"\n{audit['strategy_id']}:")
        print(f"  Gross Edge: {audit['gross_expectancy']:.2f}%")
        print(f"  Net Edge (at $10k): {audit['cost_analysis'][2]['net_expectancy']:.2f}%")
        print(f"  Recommendation: {audit['recommendation']}")
        print(f"  Reason: {audit['reason']}")

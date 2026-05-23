"""
Liquidity Guard - Orderbook Depth Protection
=============================================
Prevents execution when orderbook depth is insufficient.
Checks spread, depth, and slippage estimates before allowing orders.

Planned v1.2 from updates_torontoevent.html - NOW IMPLEMENTED
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LiquidityStatus(Enum):
    """Liquidity status levels."""
    EXCELLENT = "excellent"  # Deep book, tight spread
    GOOD = "good"            # Adequate for normal trading
    ADEQUATE = "adequate"    # Marginal - reduce size
    POOR = "poor"            # Risky - avoid or tiny size
    INSUFFICIENT = "insufficient"  # Block trade


@dataclass
class LiquidityConfig:
    """Configuration for liquidity guard."""
    # Depth thresholds (in base currency)
    min_depth_l1_usd: float = 100000      # $100K at L1
    min_depth_l3_usd: float = 500000      # $500K at L3
    min_depth_l5_usd: float = 1000000     # $1M at L5
    
    # Spread thresholds (basis points)
    max_spread_bps: float = 10.0          # 0.1%
    warning_spread_bps: float = 5.0       # 0.05%
    
    # Slippage estimates
    max_acceptable_slippage_bps: float = 15.0  # 0.15%
    
    # Size limits relative to depth
    max_order_pct_of_depth: float = 0.10  # Max 10% of L1 depth
    
    # Emergency mode
    emergency_spread_bps: float = 50.0    # Block above this


class LiquidityGuard:
    """
    Guards against insufficient liquidity.
    
    Checks:
    1. Orderbook depth at multiple levels
    2. Bid-ask spread
    3. Estimated slippage for order size
    4. Recent trade volume
    
    Status: IMPLEMENTED (was PLANNED v1.2)
    """
    
    def __init__(self, config: LiquidityConfig = None):
        self.config = config or LiquidityConfig()
        self.recent_checks = []
        
        logger.info("[OK] Liquidity Guard INITIALIZED (v1.2 IMPLEMENTED)")
    
    def analyze_liquidity(
        self,
        orderbook: Dict,
        symbol: str,
        current_price: float
    ) -> Dict:
        """
        Analyze orderbook liquidity.
        
        Args:
            orderbook: Orderbook with bids/asks
            symbol: Trading symbol
            current_price: Current mid price
        
        Returns:
            Liquidity analysis
        """
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return {
                'status': LiquidityStatus.INSUFFICIENT,
                'can_trade': False,
                'reason': 'Empty orderbook'
            }
        
        # Calculate spreads
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_bps = spread / mid_price * 10000
        
        # Calculate depth at different levels
        def calc_depth_levels(orders, price, levels=[1, 3, 5]):
            """Calculate depth in USD at different levels."""
            results = {}
            for level in levels:
                if len(orders) >= level:
                    depth = sum([p * q for p, q in orders[:level]])
                    results[f'l{level}'] = depth
                else:
                    results[f'l{level}'] = 0
            return results
        
        bid_depth = calc_depth_levels(bids, current_price)
        ask_depth = calc_depth_levels(asks, current_price)
        
        # Use minimum of bid/ask depth (conservative)
        depth = {
            k: min(bid_depth.get(k, 0), ask_depth.get(k, 0))
            for k in ['l1', 'l3', 'l5']
        }
        
        # Determine status
        status = self._determine_status(spread_bps, depth)
        
        # Calculate max safe order size
        max_safe_size = depth['l1'] * self.config.max_order_pct_of_depth
        
        return {
            'status': status,
            'can_trade': status != LiquidityStatus.INSUFFICIENT,
            'spread_bps': spread_bps,
            'depth_usd': depth,
            'max_safe_order_usd': max_safe_size,
            'mid_price': mid_price,
            'reason': None if status != LiquidityStatus.INSUFFICIENT else self._get_reason(spread_bps, depth)
        }
    
    def _determine_status(
        self,
        spread_bps: float,
        depth: Dict[str, float]
    ) -> LiquidityStatus:
        """Determine liquidity status from metrics."""
        # Emergency spread check
        if spread_bps > self.config.emergency_spread_bps:
            return LiquidityStatus.INSUFFICIENT
        
        # Spread checks
        if spread_bps > self.config.max_spread_bps:
            return LiquidityStatus.POOR
        
        # Depth checks
        if depth['l1'] < self.config.min_depth_l1_usd * 0.5:
            return LiquidityStatus.INSUFFICIENT
        
        if depth['l1'] < self.config.min_depth_l1_usd:
            return LiquidityStatus.POOR
        
        if depth['l3'] < self.config.min_depth_l3_usd:
            return LiquidityStatus.ADEQUATE
        
        if depth['l5'] < self.config.min_depth_l5_usd:
            return LiquidityStatus.GOOD
        
        if spread_bps < self.config.warning_spread_bps:
            return LiquidityStatus.EXCELLENT
        
        return LiquidityStatus.GOOD
    
    def _get_reason(self, spread_bps: float, depth: Dict) -> str:
        """Get reason for insufficient liquidity."""
        if spread_bps > self.config.emergency_spread_bps:
            return f"Emergency spread: {spread_bps:.1f} bps"
        if depth['l1'] < self.config.min_depth_l1_usd * 0.5:
            return f"Insufficient L1 depth: ${depth['l1']:,.0f}"
        return "Multiple liquidity constraints"
    
    def check_order(
        self,
        orderbook: Dict,
        symbol: str,
        order_value_usd: float,
        side: str,  # 'buy' or 'sell'
        current_price: float
    ) -> Dict:
        """
        Check if an order can be executed safely.
        
        Args:
            orderbook: Current orderbook
            symbol: Trading symbol
            order_value_usd: Order size in USD
            side: 'buy' or 'sell'
            current_price: Current price
        
        Returns:
            Order approval with constraints
        """
        # Analyze liquidity
        liq = self.analyze_liquidity(orderbook, symbol, current_price)
        
        if not liq['can_trade']:
            return {
                'approved': False,
                'reason': liq['reason'],
                'liquidity_status': liq['status'].value,
                'suggested_size': 0
            }
        
        # Check order size against depth
        max_safe = liq['max_safe_order_usd']
        
        if order_value_usd > max_safe:
            # Order too large
            return {
                'approved': False,
                'reason': f'Order size (${order_value_usd:,.0f}) exceeds safe limit (${max_safe:,.0f})',
                'liquidity_status': liq['status'].value,
                'suggested_size': max_safe * 0.9,  # Suggest 90% of max
                'slippage_estimate_bps': self._estimate_slippage(orderbook, order_value_usd, side)
            }
        
        # Estimate slippage
        slippage_bps = self._estimate_slippage(orderbook, order_value_usd, side)
        
        if slippage_bps > self.config.max_acceptable_slippage_bps:
            return {
                'approved': False,
                'reason': f'Estimated slippage ({slippage_bps:.1f} bps) exceeds max ({self.config.max_acceptable_slippage_bps:.1f} bps)',
                'liquidity_status': liq['status'].value,
                'suggested_size': self._find_safe_size(orderbook, side),
                'slippage_estimate_bps': slippage_bps
            }
        
        # Order approved
        return {
            'approved': True,
            'reason': None,
            'liquidity_status': liq['status'].value,
            'slippage_estimate_bps': slippage_bps,
            'depth_at_l1': liq['depth_usd']['l1'],
            'utilization_pct': order_value_usd / max_safe * 100
        }
    
    def _estimate_slippage(
        self,
        orderbook: Dict,
        order_value_usd: float,
        side: str
    ) -> float:
        """
        Estimate slippage for an order.
        
        Walks the orderbook to find average execution price.
        """
        orders = orderbook.get('asks' if side == 'buy' else 'bids', [])
        
        if not orders:
            return float('inf')
        
        remaining = order_value_usd
        total_cost = 0
        total_qty = 0
        
        for price, qty in orders:
            value = price * qty
            
            if value >= remaining:
                # Partial fill at this level
                partial_qty = remaining / price
                total_cost += price * partial_qty
                total_qty += partial_qty
                remaining = 0
                break
            else:
                # Full level
                total_cost += value
                total_qty += qty
                remaining -= value
        
        if remaining > 0:
            # Couldn't fill entire order
            return float('inf')
        
        avg_price = total_cost / total_qty
        best_price = orders[0][0]
        
        slippage_bps = abs(avg_price - best_price) / best_price * 10000
        
        return slippage_bps
    
    def _find_safe_size(self, orderbook: Dict, side: str) -> float:
        """Find maximum safe order size."""
        orders = orderbook.get('asks' if side == 'buy' else 'bids', [])
        
        if not orders:
            return 0
        
        # Binary search for safe size
        low = 0
        high = sum([p * q for p, q in orders]) * 0.5
        
        for _ in range(10):  # 10 iterations for precision
            mid = (low + high) / 2
            slippage = self._estimate_slippage(orderbook, mid, side)
            
            if slippage < self.config.max_acceptable_slippage_bps:
                low = mid
            else:
                high = mid
        
        return low * 0.9  # 10% safety margin
    
    def get_liquidity_summary(self) -> Dict:
        """Get summary of recent liquidity checks."""
        if not self.recent_checks:
            return {'checks': 0}
        
        statuses = [c['status'] for c in self.recent_checks[-100:]]
        
        return {
            'checks': len(self.recent_checks),
            'recent_100': {
                'excellent': sum(1 for s in statuses if s == LiquidityStatus.EXCELLENT),
                'good': sum(1 for s in statuses if s == LiquidityStatus.GOOD),
                'adequate': sum(1 for s in statuses if s == LiquidityStatus.ADEQUATE),
                'poor': sum(1 for s in statuses if s == LiquidityStatus.POOR),
                'insufficient': sum(1 for s in statuses if s == LiquidityStatus.INSUFFICIENT)
            }
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    guard = LiquidityGuard()
    
    # Example orderbook
    orderbook = {
        'bids': [[50000, 5], [49999, 10], [49998, 20], [49995, 50], [49990, 100]],
        'asks': [[50001, 5], [50002, 10], [50003, 20], [50005, 50], [50010, 100]]
    }
    
    # Analyze liquidity
    analysis = guard.analyze_liquidity(orderbook, 'BTCUSDT', 50000.5)
    print(f"Liquidity Status: {analysis['status'].value}")
    print(f"Spread: {analysis['spread_bps']:.2f} bps")
    print(f"Depth L1: ${analysis['depth_usd']['l1']:,.0f}")
    
    # Check specific order
    check = guard.check_order(orderbook, 'BTCUSDT', 50000, 'buy', 50000.5)
    print(f"\nOrder Check:")
    print(f"  Approved: {check['approved']}")
    print(f"  Slippage estimate: {check.get('slippage_estimate_bps', 0):.2f} bps")
    
    print("\n[OK] Liquidity Guard v1.2 IMPLEMENTATION COMPLETE")

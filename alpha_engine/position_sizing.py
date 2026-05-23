"""
ALPHA_ENGINE -- Kelly Criterion Position Sizing
================================================
Implements Gemini-recommended Kelly Criterion with ATR-adjusted sizing,
correlation group limits, and hard risk caps.

Kelly formula (corrected):
    K = W - ((1 - W) * R_l / R_w)

Three allocation tiers:
    quarter-Kelly (0.25 * K) = conservative (recommended for live)
    half-Kelly    (0.50 * K) = moderate
    three-quarter (0.75 * K) = aggressive

Guardrails:
    - 2% max risk per trade (hard cap)
    - ATR-adjusted sizing (higher ATR = smaller position)
    - 3 correlation group limit (max 3 positions per correlation group)
    - 20% crypto portfolio cap
    - Trailing stop at 1.5x ATR

References:
    - Kelly (1956), "A New Interpretation of Information Rate"
    - Thorp (2006), "The Kelly Criterion in Blackjack, Sports Betting and the Stock Market"
    - Gemini consensus review (March 2026)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Correlation groups -- assets that move together
# ---------------------------------------------------------------------------
CORRELATION_GROUPS: dict[str, list[str]] = {
    "btc_correlated": [
        "BTC-USD", "BTCUSDT", "ETH-USD", "ETHUSDT", "SOL-USD", "SOLUSDT",
        "BTC", "ETH", "SOL", "MSTR", "COIN",
    ],
    "alt_defi": [
        "LINK-USD", "LINKUSDT", "AAVE-USD", "AAVEUSDT", "DOT-USD", "DOTUSDT",
        "UNI-USD", "UNIUSDT", "LINK", "AAVE", "DOT", "UNI",
        "INJ-USD", "INJUSDT", "PENDLE-USD", "PENDLEUSDT",
    ],
    "alt_l1": [
        "ADA-USD", "ADAUSDT", "AVAX-USD", "AVAXUSDT", "NEAR-USD", "NEARUSDT",
        "SUI-USD", "SUIUSDT", "APT-USD", "APTUSDT", "SEI-USD", "SEIUSDT",
        "TAO-USD", "TAOUSDT", "TIA-USD", "TIAUSDT",
        "ADA", "AVAX", "NEAR", "SUI", "APT", "SEI",
    ],
    "meme": [
        "DOGE-USD", "DOGEUSDT", "TRUMP-USD", "TRUMPUSDT",
        "PEPE-USD", "PEPEUSDT", "WIF-USD", "WIFUSDT",
        "BONK-USD", "BONKUSDT", "FLOKI-USD", "FLOKIUSDT",
        "DOGE", "TRUMP", "PEPE", "WIF", "BONK", "FLOKI",
        "GME", "AMC",
    ],
    "forex_jpy": [
        "USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X",
    ],
    "forex_usd": [
        "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDCAD=X", "NZDUSD=X", "USDCHF=X",
    ],
    "tech_equity": [
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD",
    ],
}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_RISK_PER_TRADE = 0.02       # 2% hard cap on risk per trade
MAX_CRYPTO_ALLOCATION = 0.20    # 20% crypto portfolio cap
MAX_PER_CORRELATION_GROUP = 3   # Max 3 positions in same correlation group
TRAILING_STOP_ATR_MULT = 1.5    # Trailing stop at 1.5x ATR
MIN_KELLY_FRACTION = 0.001      # Floor to avoid zero-size positions
DEFAULT_ACCOUNT_EQUITY = 10_000.0

KELLY_TIERS = {
    "quarter": 0.25,
    "half": 0.50,
    "three_quarter": 0.75,
}


# ---------------------------------------------------------------------------
# Core Kelly functions
# ---------------------------------------------------------------------------

def get_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float,
                       n_trades: int = 100) -> float:
    """
    Compute raw Kelly fraction with Baker-McHale uncertainty shrinkage.

    K = W - ((1 - W) * R_l / R_w)

    Where:
        W = win rate (0-1)
        R_w = average win magnitude (positive, e.g. 1.985 for 1.985%)
        R_l = average loss magnitude (positive, e.g. 1.289 for 1.289%)
        n_trades = number of closed trades (for parameter uncertainty shrinkage)

    Baker-McHale shrinkage reduces Kelly when sample size is small,
    accounting for uncertainty in the win-rate estimate.

    Returns raw Kelly fraction (can be negative if strategy has negative edge).
    Negative means "don't bet" -- clamped to 0.0.

    Example: Battleground Keltner BTC (72.9% WR, avg_win=1.985%, avg_loss=1.289%):
        K = 0.729 - (0.271 * 1.289 / 1.985) = 0.553
    """
    if avg_win <= 0:
        return 0.0

    # Ensure positive magnitudes
    avg_loss = abs(avg_loss)
    avg_win = abs(avg_win)

    kelly = win_rate - ((1 - win_rate) * avg_loss / avg_win)

    # Baker-McHale shrinkage for parameter uncertainty
    if n_trades > 0:
        sigma_p = (win_rate * (1 - win_rate) / max(n_trades, 1)) ** 0.5
        shrinkage = max(0, 1 - sigma_p**2 / max(win_rate * (1 - win_rate), 1e-6))
        kelly = kelly * shrinkage

    return max(0.0, kelly)


def get_kelly_tier_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    tier: str = "quarter",
) -> float:
    """
    Compute Kelly fraction scaled to a tier.

    Args:
        win_rate: Strategy win rate (0-1)
        avg_win: Average winning trade magnitude (%, positive)
        avg_loss: Average losing trade magnitude (%, positive)
        tier: "quarter" (0.25K), "half" (0.50K), or "three_quarter" (0.75K)

    Returns scaled Kelly fraction (0.0 - ~0.4 typically).
    """
    raw = get_kelly_fraction(win_rate, avg_win, avg_loss)
    multiplier = KELLY_TIERS.get(tier, KELLY_TIERS["quarter"])
    return raw * multiplier


def get_correlation_group(symbol: str) -> Optional[str]:
    """Return the correlation group name for a symbol, or None if ungrouped."""
    symbol_upper = symbol.upper()
    for group_name, members in CORRELATION_GROUPS.items():
        if any(symbol_upper == m.upper() or symbol_upper.startswith(m.upper().split("-")[0])
               for m in members):
            return group_name
    return None


def count_positions_in_group(
    symbol: str,
    open_positions: list[dict],
) -> int:
    """Count how many open positions share the same correlation group as symbol."""
    target_group = get_correlation_group(symbol)
    if target_group is None:
        return 0

    count = 0
    for pos in open_positions:
        pos_symbol = pos.get("symbol", "")
        if get_correlation_group(pos_symbol) == target_group:
            count += 1
    return count


def get_vol_sizing_multiplier(
    symbol: str,
    data: Optional[list[float]] = None,
    atr_pct: Optional[float] = None,
    category: str = "crypto",
) -> float:
    """Compute position size multiplier based on volatility percentile.

    Uses recent ATR vs 30-day ATR to determine vol regime:
        Vol percentile <30  (calm):     1.0x to 1.25x
        Vol percentile 30-80 (normal):  0.5x to 1.0x
        Vol percentile >80  (volatile): 0.25x to 0.5x
        Structural break (ATR > 3x normal): 0.1x
        Weekend (Sat/Sun): cap at 0.75x unless weekend-specific edge

    Args:
        symbol: Trading pair / ticker (for logging).
        data: List of recent close prices (at least 30 values).
              If provided, ATR percentile is computed from these prices.
        atr_pct: Pre-computed current ATR as fraction of price.
                 Used as fallback when data is not available.
        category: Asset category (crypto, forex, stock, etc.).
                  Affects the reference ATR for percentile estimation.

    Returns:
        float multiplier in [0.1, 1.25].
    """
    # Reference daily ATR% by category (same as position sizing)
    reference_atr = {
        "crypto": 0.035,
        "meme": 0.06,
        "forex": 0.006,
        "stock": 0.015,
        "penny": 0.04,
        "futures": 0.012,
        "etf": 0.01,
    }.get(category, 0.02)

    vol_pctl = 50.0  # default: assume normal
    recent_atr_pct = None
    normal_atr_pct = reference_atr

    if data is not None and len(data) >= 30:
        # Compute true range series from close prices
        # Simplified: use absolute daily returns as ATR proxy
        returns = []
        for i in range(1, len(data)):
            if data[i - 1] != 0:
                returns.append(abs(data[i] - data[i - 1]) / data[i - 1])

        if len(returns) >= 14:
            # Recent ATR: last 5 days average
            recent_atr_pct = sum(returns[-5:]) / 5.0
            # 30-day ATR for baseline
            normal_atr_pct = sum(returns[-30:]) / min(len(returns), 30)

            # Compute percentile of recent ATR within the full series
            # Using a rolling window approach
            sorted_returns = sorted(returns)
            n = len(sorted_returns)
            # Find rank of recent_atr_pct
            rank = 0
            for r in sorted_returns:
                if r <= recent_atr_pct:
                    rank += 1
            vol_pctl = (rank / n) * 100.0
    elif atr_pct is not None and atr_pct > 0:
        # Estimate percentile from atr_pct vs reference
        ratio = atr_pct / reference_atr
        # Map ratio to approximate percentile
        # ratio 0.5 -> ~20th pctl, 1.0 -> ~50th, 2.0 -> ~85th, 3.0+ -> ~95th+
        if ratio <= 0.5:
            vol_pctl = 20.0
        elif ratio <= 1.0:
            vol_pctl = 20.0 + (ratio - 0.5) * 60.0  # 20-50
        elif ratio <= 2.0:
            vol_pctl = 50.0 + (ratio - 1.0) * 35.0  # 50-85
        else:
            vol_pctl = 85.0 + min((ratio - 2.0) * 10.0, 15.0)  # 85-100
        recent_atr_pct = atr_pct
        normal_atr_pct = reference_atr

    # --- Structural break check ---
    if recent_atr_pct is not None and normal_atr_pct > 0:
        if recent_atr_pct > 3.0 * normal_atr_pct:
            mult = 0.1
            logger.info("Vol sizing: %s vol_pctl=%.0f%% mult=%.2fx (STRUCTURAL BREAK)",
                        symbol, vol_pctl, mult)
            return mult

    # --- Percentile-based multiplier ---
    if vol_pctl < 30:
        # Calm regime: scale from 1.0 (at 30th pctl) to 1.25 (at 0th pctl)
        mult = 1.0 + 0.25 * (1.0 - vol_pctl / 30.0)
    elif vol_pctl <= 80:
        # Normal regime: scale from 1.0 (at 30th pctl) to 0.5 (at 80th pctl)
        mult = 1.0 - 0.5 * ((vol_pctl - 30.0) / 50.0)
    else:
        # Volatile regime: scale from 0.5 (at 80th pctl) to 0.25 (at 100th pctl)
        mult = 0.5 - 0.25 * ((vol_pctl - 80.0) / 20.0)

    # --- Weekend cap ---
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        mult = min(mult, 0.75)

    # Clamp to [0.1, 1.25]
    mult = max(0.1, min(1.25, mult))

    logger.info("Vol sizing: %s vol_pctl=%.0f%% mult=%.2fx", symbol, vol_pctl, mult)
    return mult


def get_drawdown_governor_multiplier(portfolio_path=None):
    """Compute position size multiplier based on current portfolio drawdown.

    Tiered scaling:
    - DD < 5%:   1.0x (full size)
    - DD 5-10%:  0.75x
    - DD 10-15%: 0.50x
    - DD 15-20%: 0.25x
    - DD > 20%:  0.05x (near-zero, emergency only)

    Reads drawdown from portfolio_20x.json snapshots.
    Returns float multiplier [0.05, 1.0]
    """
    try:
        import json
        path = portfolio_path or os.path.join(os.path.dirname(__file__), 'data', 'portfolio_20x.json')
        with open(path, encoding='utf-8') as f:
            port = json.load(f)

        # Compute high water mark from snapshots
        snapshots = port.get('snapshots', [])
        if not snapshots:
            return 1.0

        hwm = max(s.get('equity', 10000) for s in snapshots)
        current_equity = port.get('current_balance', 10000)
        # Add unrealized
        for pos in port.get('positions', {}).values():
            current_equity += pos.get('current_pnl_usdt', 0)

        dd = (hwm - current_equity) / hwm if hwm > 0 else 0

        if dd < 0.05:
            mult = 1.0
        elif dd < 0.10:
            mult = 0.75
        elif dd < 0.15:
            mult = 0.50
        elif dd < 0.20:
            mult = 0.25
        else:
            mult = 0.05

        logger.info("DD governor: dd=%.1f%% mult=%.2fx", dd * 100, mult)
        return mult
    except Exception:
        return 1.0  # fail-open


def get_anti_martingale_multiplier(strategy: str, closed_picks_path: str = None) -> float:
    """Anti-martingale: increase size after wins, decrease after losses.

    Looks at last 5 closed trades for this strategy:
    - 3+ wins in last 5: 1.25x (ride the streak)
    - 3+ losses in last 5: 0.50x (reduce during cold streak)
    - Mixed: 1.0x (neutral)

    Returns float multiplier [0.50, 1.25]
    """
    try:
        import json
        path = closed_picks_path or os.path.join(os.path.dirname(__file__), 'data', 'closed_picks.json')
        with open(path, encoding='utf-8', errors='replace') as f:
            closed = json.load(f)

        # Get last 5 trades for this strategy
        strat_trades = [p for p in closed if isinstance(p, dict) and p.get('strategy') == strategy]
        recent = strat_trades[-5:] if len(strat_trades) >= 5 else strat_trades
        if len(recent) < 3:
            return 1.0  # not enough data

        wins = sum(1 for p in recent if float(p.get('pnl_pct', 0) or 0) > 0)
        if wins >= 3:
            return 1.25  # hot streak
        elif wins <= 1:
            return 0.50  # cold streak
        return 1.0
    except Exception:
        return 1.0


def get_position_size(
    signal: dict,
    account_equity: float = DEFAULT_ACCOUNT_EQUITY,
    strategy_stats: Optional[dict] = None,
    kelly_tier: str = "quarter",
    open_positions: Optional[list[dict]] = None,
    current_crypto_allocation: float = 0.0,
) -> dict:
    """
    Compute position size in USD using Kelly Criterion with guardrails.

    Args:
        signal: Signal dict with keys: symbol, entry_price, stop_loss,
                take_profit, category, atr_at_entry
        account_equity: Total account equity in USD
        strategy_stats: Dict with win_rate, avg_win_pct, avg_loss_pct, closed_picks
        kelly_tier: "quarter", "half", or "three_quarter"
        open_positions: List of currently open position dicts (for correlation check)
        current_crypto_allocation: Total USD currently allocated to crypto

    Returns dict with:
        position_size_usd: Dollar amount to allocate
        kelly_fraction: Raw Kelly fraction
        kelly_tier_fraction: Tier-adjusted Kelly fraction
        kelly_tier: Which tier was used
        risk_per_trade_pct: Actual risk percentage of equity
        atr_adjustment: ATR scaling factor applied
        correlation_group: Which group this symbol belongs to
        correlation_count: Positions already in this group
        capped_by: What limit triggered the cap (if any)
        trailing_stop_atr: Recommended trailing stop distance
    """
    open_positions = open_positions or []
    entry_price = signal.get("entry_price", 0)
    stop_loss = signal.get("stop_loss", 0)
    category = signal.get("category", "crypto")
    atr_at_entry = signal.get("atr_at_entry", 0)
    symbol = signal.get("symbol", "")

    result = {
        "position_size_usd": 0.0,
        "kelly_fraction": 0.0,
        "kelly_tier_fraction": 0.0,
        "kelly_tier": kelly_tier,
        "risk_per_trade_pct": 0.0,
        "atr_adjustment": 1.0,
        "correlation_group": get_correlation_group(symbol),
        "correlation_count": count_positions_in_group(symbol, open_positions),
        "capped_by": None,
        "trailing_stop_atr": 0.0,
        "vol_sizing_multiplier": 1.0,
    }

    if entry_price <= 0 or account_equity <= 0:
        result["capped_by"] = "invalid_entry"
        return result

    # --- Correlation group limit ---
    if result["correlation_count"] >= MAX_PER_CORRELATION_GROUP:
        result["capped_by"] = f"correlation_limit ({result['correlation_group']})"
        return result

    # --- Kelly fraction ---
    stats = strategy_stats or {}
    win_rate = stats.get("win_rate", 0.5)
    avg_win = abs(stats.get("avg_win_pct", 2.0))
    avg_loss = abs(stats.get("avg_loss_pct", 2.0))
    closed_picks = stats.get("closed_picks", 0)

    # Need at least some data for Kelly to be meaningful
    if closed_picks < 5:
        # Cold start: use conservative defaults (assume 50% WR, 1:1 RR)
        # This gives K=0, so fall back to a minimal fixed allocation
        raw_kelly = 0.0
        tier_kelly = 0.0
    else:
        raw_kelly = get_kelly_fraction(win_rate, avg_win, avg_loss)
        tier_kelly = raw_kelly * KELLY_TIERS.get(kelly_tier, 0.25)

    result["kelly_fraction"] = round(raw_kelly, 4)
    result["kelly_tier_fraction"] = round(tier_kelly, 4)

    # --- Base position size from Kelly ---
    if tier_kelly > MIN_KELLY_FRACTION:
        base_size = account_equity * tier_kelly
    else:
        # Fallback: risk-based sizing (2% risk / stop distance)
        if stop_loss > 0:
            stop_distance = abs(entry_price - stop_loss) / entry_price
            stop_distance = max(stop_distance, 0.005)  # min 0.5% stop
        else:
            stop_distance = 0.05  # default 5% stop
        risk_amount = account_equity * MAX_RISK_PER_TRADE
        base_size = risk_amount / stop_distance

    # --- ATR-adjusted sizing ---
    # Higher ATR = smaller position (inverse relationship)
    # Use median ATR as reference; if current ATR is 2x median, halve the size
    if atr_at_entry and atr_at_entry > 0 and entry_price > 0:
        # Normalized ATR as percentage of price
        atr_pct = atr_at_entry / entry_price

        # Reference ATR by category (typical daily ATR%)
        reference_atr = {
            "crypto": 0.035,   # ~3.5% daily ATR typical for crypto
            "meme": 0.06,      # ~6% for meme coins
            "forex": 0.006,    # ~0.6% for major forex pairs
            "stock": 0.015,    # ~1.5% for large-cap stocks
            "penny": 0.04,     # ~4% for penny stocks
            "futures": 0.012,  # ~1.2% for futures
            "etf": 0.01,       # ~1% for ETFs
        }.get(category, 0.02)

        if atr_pct > 0:
            atr_ratio = reference_atr / atr_pct
            # Clamp adjustment between 0.3x and 2.0x
            atr_adjustment = max(0.3, min(2.0, atr_ratio))
            base_size *= atr_adjustment
            result["atr_adjustment"] = round(atr_adjustment, 3)

    # --- Volatility-based sizing multiplier ---
    _vol_atr_pct = None
    if atr_at_entry and atr_at_entry > 0 and entry_price > 0:
        _vol_atr_pct = atr_at_entry / entry_price
    vol_mult = get_vol_sizing_multiplier(symbol, atr_pct=_vol_atr_pct, category=category)
    base_size *= vol_mult
    result["vol_sizing_multiplier"] = round(vol_mult, 3)

    # --- Hard cap: 2% risk per trade ---
    if stop_loss > 0 and entry_price > 0:
        stop_pct = abs(entry_price - stop_loss) / entry_price
        max_size_by_risk = (account_equity * MAX_RISK_PER_TRADE) / max(stop_pct, 0.001)
        if base_size > max_size_by_risk:
            base_size = max_size_by_risk
            result["capped_by"] = "max_risk_2pct"

    # --- Crypto portfolio cap: 20% ---
    if category in ("crypto", "meme"):
        max_crypto = account_equity * MAX_CRYPTO_ALLOCATION
        remaining_crypto = max(0, max_crypto - current_crypto_allocation)
        if base_size > remaining_crypto:
            base_size = remaining_crypto
            result["capped_by"] = "crypto_cap_20pct"

    # --- Floor and ceiling ---
    # Min $50 position (below this, fees dominate)
    base_size = max(base_size, 0.0)
    # Max 15% of equity in single position
    max_single = account_equity * 0.15
    if base_size > max_single:
        base_size = max_single
        result["capped_by"] = result["capped_by"] or "max_single_15pct"

    # --- Trailing stop recommendation ---
    if atr_at_entry and atr_at_entry > 0:
        result["trailing_stop_atr"] = round(atr_at_entry * TRAILING_STOP_ATR_MULT, 6)

    # --- Compute actual risk percentage ---
    if stop_loss > 0 and entry_price > 0 and account_equity > 0:
        stop_pct = abs(entry_price - stop_loss) / entry_price
        actual_risk = (base_size * stop_pct) / account_equity
        result["risk_per_trade_pct"] = round(actual_risk, 4)

    # --- Drawdown governor: scale down when portfolio is in drawdown ---
    dd_mult = get_drawdown_governor_multiplier()
    if dd_mult < 1.0:
        base_size *= dd_mult
        if result["capped_by"] is None:
            result["capped_by"] = f"dd_governor_{dd_mult:.2f}x"
    result["dd_governor_multiplier"] = dd_mult

    result["position_size_usd"] = round(base_size, 2)
    return result


# ---------------------------------------------------------------------------
# Convenience: annotate a signal dict in-place
# ---------------------------------------------------------------------------

def annotate_signal_with_kelly(
    signal: dict,
    strategy_stats: Optional[dict] = None,
    account_equity: float = DEFAULT_ACCOUNT_EQUITY,
    kelly_tier: str = "quarter",
    open_positions: Optional[list[dict]] = None,
    current_crypto_allocation: float = 0.0,
) -> dict:
    """
    Add kelly/sizing fields to a signal dict in-place.

    Adds: position_size_usd, kelly_fraction, kelly_tier_fraction,
          kelly_tier, atr_adjustment, correlation_group, trailing_stop_atr
    """
    sizing = get_position_size(
        signal=signal,
        account_equity=account_equity,
        strategy_stats=strategy_stats,
        kelly_tier=kelly_tier,
        open_positions=open_positions,
        current_crypto_allocation=current_crypto_allocation,
    )

    signal["position_size_usd"] = sizing["position_size_usd"]
    signal["kelly_fraction"] = sizing["kelly_fraction"]
    signal["kelly_tier_fraction"] = sizing["kelly_tier_fraction"]
    signal["kelly_tier"] = sizing["kelly_tier"]
    signal["atr_adjustment"] = sizing["atr_adjustment"]
    signal["correlation_group"] = sizing["correlation_group"]
    signal["trailing_stop_atr"] = sizing["trailing_stop_atr"]
    signal["risk_per_trade_pct"] = sizing["risk_per_trade_pct"]
    signal["vol_sizing_multiplier"] = sizing["vol_sizing_multiplier"]
    if sizing["capped_by"]:
        signal["sizing_capped_by"] = sizing["capped_by"]

    return signal


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Kelly Criterion Position Sizing -- Self-Test")
    print("=" * 60)

    # Test 1: Gemini example -- Battleground Keltner BTC
    # 72.9% WR, avg_win=1.985%, avg_loss=1.289%
    k = get_kelly_fraction(0.729, 1.985, 1.289)
    print(f"\n  Keltner BTC: K = {k:.4f} (expected ~0.553)")
    assert abs(k - 0.553) < 0.01, f"Kelly mismatch: {k}"

    # Quarter-Kelly
    qk = get_kelly_tier_fraction(0.729, 1.985, 1.289, "quarter")
    print(f"  Quarter-Kelly: {qk:.4f} (expected ~0.138)")

    # Half-Kelly
    hk = get_kelly_tier_fraction(0.729, 1.985, 1.289, "half")
    print(f"  Half-Kelly:    {hk:.4f} (expected ~0.277)")

    # Test 2: Negative edge (should return 0)
    k_neg = get_kelly_fraction(0.30, 1.0, 2.0)
    print(f"\n  Negative edge: K = {k_neg:.4f} (expected 0.0)")
    assert k_neg == 0.0

    # Test 3: Full position sizing
    test_signal = {
        "symbol": "BTC-USD",
        "entry_price": 85000.0,
        "stop_loss": 82000.0,
        "take_profit": 92000.0,
        "category": "crypto",
        "atr_at_entry": 2500.0,
    }
    test_stats = {
        "win_rate": 0.729,
        "avg_win_pct": 1.985,
        "avg_loss_pct": 1.289,
        "closed_picks": 50,
    }

    sizing = get_position_size(
        test_signal,
        account_equity=10_000.0,
        strategy_stats=test_stats,
        kelly_tier="quarter",
    )
    print(f"\n  BTC-USD position sizing (quarter-Kelly):")
    print(f"    Position size: ${sizing['position_size_usd']:,.2f}")
    print(f"    Kelly raw:     {sizing['kelly_fraction']:.4f}")
    print(f"    Kelly tier:    {sizing['kelly_tier_fraction']:.4f}")
    print(f"    ATR adjust:    {sizing['atr_adjustment']:.3f}")
    print(f"    Risk %:        {sizing['risk_per_trade_pct']:.4f}")
    print(f"    Corr group:    {sizing['correlation_group']}")
    print(f"    Trailing stop: ${sizing['trailing_stop_atr']:,.2f}")
    print(f"    Capped by:     {sizing['capped_by']}")

    # Test 4: Correlation group detection
    assert get_correlation_group("BTC-USD") == "btc_correlated"
    assert get_correlation_group("ETH-USD") == "btc_correlated"
    assert get_correlation_group("LINK-USD") == "alt_defi"
    assert get_correlation_group("DOGE-USD") == "meme"
    assert get_correlation_group("EURUSD=X") == "forex_usd"
    assert get_correlation_group("USDJPY=X") == "forex_jpy"
    assert get_correlation_group("AAPL") == "tech_equity"
    print("\n  Correlation groups: all passed")

    # Test 5: Cold start (no strategy stats)
    cold_sizing = get_position_size(
        test_signal,
        account_equity=10_000.0,
        strategy_stats={"closed_picks": 2},
        kelly_tier="quarter",
    )
    print(f"\n  Cold start (2 picks): ${cold_sizing['position_size_usd']:,.2f} "
          f"(fallback risk-based sizing)")

    # Test 6: Correlation group limit
    fake_positions = [
        {"symbol": "BTC-USD"}, {"symbol": "ETH-USD"}, {"symbol": "SOL-USD"},
    ]
    blocked = get_position_size(
        {"symbol": "MSTR", "entry_price": 300, "stop_loss": 280, "category": "stock"},
        account_equity=10_000.0,
        strategy_stats=test_stats,
        open_positions=fake_positions,
    )
    print(f"  Corr group limit (3 btc_correlated open + MSTR): "
          f"${blocked['position_size_usd']:,.2f} (expected $0)")
    assert blocked["position_size_usd"] == 0.0

    print("\n  All tests passed.")

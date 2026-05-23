"""
Incubator — Parameter Space Definitions
=========================================
Defines tunable parameters for each strategy archetype with realistic
bounds derived from historical volatility and published research.

Each param has: (min, max, step, type) where type is 'int', 'float', or 'bool'.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Param:
    """A single tunable parameter."""
    name: str
    min_val: float
    max_val: float
    step: float = 0.0  # 0 = continuous
    dtype: str = "float"  # float | int | bool

    def sample_count(self) -> int:
        """Approximate number of discrete levels."""
        if self.dtype == "bool":
            return 2
        if self.step > 0:
            return int((self.max_val - self.min_val) / self.step) + 1
        return 20  # continuous → 20 LHS levels default


@dataclass
class StrategyArchetype:
    """A strategy archetype with its tunable parameter space."""
    name: str
    family: str  # momentum, trend, volume, sentiment, structure, volatility, on_chain
    description: str
    params: list[Param] = field(default_factory=list)

    def total_combos(self) -> int:
        """Total discrete combinations (before LHS sampling)."""
        n = 1
        for p in self.params:
            n *= p.sample_count()
        return n


# ---------------------------------------------------------------------------
# PARAMETER SPACES — grouped by strategy family
# ---------------------------------------------------------------------------

ARCHETYPES: list[StrategyArchetype] = [
    # ===================== MOMENTUM =====================
    StrategyArchetype(
        name="rsi_mean_reversion",
        family="momentum",
        description="Connors RSI-2 style: buy oversold, sell overbought",
        params=[
            Param("rsi_period", 2, 5, 1, "int"),
            Param("rsi_entry_threshold", 3, 15, 1, "int"),        # buy below this
            Param("rsi_exit_threshold", 70, 95, 5, "int"),        # sell above this
            Param("sma_filter_period", 50, 200, 50, "int"),       # trend filter
            Param("use_sma_filter", 0, 1, 1, "bool"),
            Param("tp_atr_mult", 1.5, 4.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 3.0, 0.0, "float"),
            Param("atr_period", 10, 20, 2, "int"),
            Param("max_hold_days", 3, 14, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="stochrsi_bounce",
        family="momentum",
        description="StochRSI oversold bounce with volume confirmation",
        params=[
            Param("stoch_period", 10, 20, 2, "int"),
            Param("stoch_k", 3, 7, 1, "int"),
            Param("oversold_level", 10, 25, 5, "int"),
            Param("volume_mult", 1.2, 3.0, 0.0, "float"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 3.0, 0.0, "float"),
            Param("max_hold_days", 3, 10, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="macd_divergence",
        family="momentum",
        description="MACD histogram divergence with price",
        params=[
            Param("fast_period", 8, 15, 1, "int"),
            Param("slow_period", 20, 30, 2, "int"),
            Param("signal_period", 7, 12, 1, "int"),
            Param("divergence_bars", 5, 20, 5, "int"),
            Param("tp_atr_mult", 2.0, 4.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("max_hold_days", 3, 14, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="cross_sectional_momentum",
        family="momentum",
        description="Buy top-N performers over lookback period",
        params=[
            Param("lookback_days", 5, 30, 5, "int"),
            Param("top_n", 2, 5, 1, "int"),
            Param("rebalance_days", 3, 14, 1, "int"),
            Param("tp_pct", 0.05, 0.20, 0.0, "float"),
            Param("sl_pct", 0.03, 0.10, 0.0, "float"),
        ],
    ),

    # ===================== TREND =====================
    StrategyArchetype(
        name="ema_crossover",
        family="trend",
        description="Multi-timeframe EMA stack alignment",
        params=[
            Param("fast_ema", 8, 21, 1, "int"),
            Param("slow_ema", 21, 55, 1, "int"),
            Param("trend_ema", 100, 200, 50, "int"),
            Param("require_trend_alignment", 0, 1, 1, "bool"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 3.0, 0.0, "float"),
            Param("trailing_stop", 0, 1, 1, "bool"),
            Param("trail_activate_pct", 0.02, 0.08, 0.0, "float"),
            Param("max_hold_days", 5, 21, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="ichimoku_cloud",
        family="trend",
        description="Ichimoku cloud breakout (crypto-tuned params)",
        params=[
            Param("tenkan_period", 9, 26, 1, "int"),
            Param("kijun_period", 26, 65, 1, "int"),
            Param("senkou_b_period", 52, 130, 1, "int"),
            Param("displacement", 20, 35, 5, "int"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.5, 3.5, 0.0, "float"),
            Param("max_hold_days", 5, 21, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="sma_bounce",
        family="trend",
        description="Buy bounce off SMA support with volume confirmation",
        params=[
            Param("sma_period", 50, 200, 50, "int"),
            Param("bounce_pct", 0.005, 0.03, 0.0, "float"),  # how close to SMA
            Param("volume_mult", 1.3, 2.5, 0.0, "float"),
            Param("rsi_max", 40, 60, 5, "int"),  # not overbought
            Param("tp_atr_mult", 2.0, 4.0, 0.0, "float"),
            Param("sl_atr_mult", 1.5, 3.0, 0.0, "float"),
            Param("max_hold_days", 5, 14, 1, "int"),
        ],
    ),

    # ===================== VOLATILITY =====================
    StrategyArchetype(
        name="bollinger_squeeze",
        family="volatility",
        description="Bollinger Band squeeze breakout",
        params=[
            Param("bb_period", 15, 25, 2, "int"),
            Param("bb_std", 1.5, 3.0, 0.0, "float"),
            Param("squeeze_threshold", 0.02, 0.06, 0.0, "float"),
            Param("breakout_mult", 1.0, 2.0, 0.0, "float"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("max_hold_days", 3, 10, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="atr_breakout",
        family="volatility",
        description="ATR expansion breakout (Keltner channel style)",
        params=[
            Param("atr_period", 10, 20, 2, "int"),
            Param("atr_mult", 1.5, 3.0, 0.0, "float"),
            Param("ema_period", 15, 25, 2, "int"),
            Param("volume_confirm", 1.2, 2.5, 0.0, "float"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("trailing_stop", 0, 1, 1, "bool"),
            Param("max_hold_days", 3, 10, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="mean_reversion_zscore",
        family="volatility",
        description="Z-score extreme mean reversion",
        params=[
            Param("lookback", 15, 50, 5, "int"),
            Param("entry_zscore", -2.5, -1.5, 0.0, "float"),
            Param("exit_zscore", -0.5, 0.5, 0.0, "float"),
            Param("tp_atr_mult", 1.5, 3.5, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("max_hold_days", 3, 14, 1, "int"),
        ],
    ),

    # ===================== VOLUME =====================
    StrategyArchetype(
        name="volume_breakout",
        family="volume",
        description="Price breakout confirmed by volume spike",
        params=[
            Param("lookback", 10, 30, 5, "int"),
            Param("volume_mult", 2.0, 5.0, 0.0, "float"),
            Param("breakout_pct", 0.01, 0.05, 0.0, "float"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("use_obv_confirm", 0, 1, 1, "bool"),
            Param("max_hold_days", 3, 10, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="vwap_reversion",
        family="volume",
        description="VWAP standard deviation band reversion",
        params=[
            Param("vwap_sd_entry", 1.5, 3.0, 0.0, "float"),
            Param("vwap_sd_exit", 0.0, 1.0, 0.0, "float"),
            Param("min_volume_ratio", 0.8, 1.5, 0.0, "float"),
            Param("tp_atr_mult", 1.5, 3.5, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("max_hold_days", 1, 7, 1, "int"),
        ],
    ),

    # ===================== STRUCTURE =====================
    StrategyArchetype(
        name="support_resistance_bounce",
        family="structure",
        description="Multi-touch S/R level bounce trade",
        params=[
            Param("sr_lookback", 20, 60, 10, "int"),
            Param("sr_tolerance_pct", 0.003, 0.015, 0.0, "float"),
            Param("min_touches", 2, 4, 1, "int"),
            Param("rsi_filter_max", 35, 55, 5, "int"),
            Param("tp_atr_mult", 2.0, 4.5, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("max_hold_days", 3, 14, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="swing_failure_pattern",
        family="structure",
        description="Hsaka SFP: wick beyond swing high/low, close inside",
        params=[
            Param("swing_lookback", 5, 20, 1, "int"),
            Param("wick_exceed_pct", 0.002, 0.01, 0.0, "float"),
            Param("volume_confirm_mult", 1.0, 2.0, 0.0, "float"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 2.5, 0.0, "float"),
            Param("max_hold_days", 3, 10, 1, "int"),
        ],
    ),

    # ===================== SENTIMENT =====================
    StrategyArchetype(
        name="funding_rate_extreme",
        family="sentiment",
        description="Contrarian on extreme funding rates",
        params=[
            Param("funding_threshold", -0.03, -0.005, 0.0, "float"),
            Param("lookback_hours", 4, 24, 4, "int"),
            Param("confirmation_bars", 1, 4, 1, "int"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 3.0, 0.0, "float"),
            Param("max_hold_days", 1, 7, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="fear_greed_contrarian",
        family="sentiment",
        description="Buy extreme fear, sell extreme greed",
        params=[
            Param("fear_threshold", 5, 25, 5, "int"),
            Param("greed_threshold", 75, 95, 5, "int"),
            Param("confirmation_days", 1, 5, 1, "int"),
            Param("tp_pct", 0.05, 0.20, 0.0, "float"),
            Param("sl_pct", 0.03, 0.10, 0.0, "float"),
            Param("max_hold_days", 5, 21, 1, "int"),
        ],
    ),

    # ===================== ON-CHAIN =====================
    StrategyArchetype(
        name="mvrv_proxy",
        family="on_chain",
        description="MVRV Z-score via 200d SMA as realized price proxy",
        params=[
            Param("sma_period", 150, 250, 25, "int"),
            Param("z_entry", -1.5, -0.5, 0.0, "float"),
            Param("z_exit", 1.0, 3.0, 0.0, "float"),
            Param("tp_pct", 0.10, 0.40, 0.0, "float"),
            Param("sl_pct", 0.05, 0.15, 0.0, "float"),
            Param("max_hold_days", 14, 60, 1, "int"),
        ],
    ),
    StrategyArchetype(
        name="exchange_netflow",
        family="on_chain",
        description="Exchange inflow/outflow reversal signal",
        params=[
            Param("flow_threshold_pct", 0.5, 3.0, 0.0, "float"),
            Param("lookback_days", 3, 14, 1, "int"),
            Param("price_confirm_pct", 0.01, 0.05, 0.0, "float"),
            Param("tp_atr_mult", 2.0, 5.0, 0.0, "float"),
            Param("sl_atr_mult", 1.0, 3.0, 0.0, "float"),
            Param("max_hold_days", 5, 21, 1, "int"),
        ],
    ),
]


def get_archetype(name: str) -> StrategyArchetype | None:
    """Look up an archetype by name."""
    for a in ARCHETYPES:
        if a.name == name:
            return a
    return None


def get_archetypes_by_family(family: str) -> list[StrategyArchetype]:
    """Get all archetypes in a given family."""
    return [a for a in ARCHETYPES if a.family == family]


def get_all_families() -> list[str]:
    """List all unique families."""
    return sorted(set(a.family for a in ARCHETYPES))

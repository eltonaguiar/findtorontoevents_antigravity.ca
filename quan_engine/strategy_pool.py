"""
QuanEngine Strategy Pool
========================
Unified interface to all 8 strategies used by the ensemble layer.
Normalizes heterogeneous outputs (Signal dataclass, dict, NormalizedPick)
into a common Vote format for consensus voting.
"""

import sys
import os
import logging

# Add parent dir so baby_strategies / paper_trading are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from typing import List, Dict, Optional

from quan_engine import config

logger = logging.getLogger("QuanEngine.StrategyPool")

# ---------------------------------------------------------------------------
# Lazy imports with graceful fallback
# ---------------------------------------------------------------------------

_CorrHMATrend = None
_OvernightSeasonalityBTCStrategy = None
_PairsSpreadBTCETHStrategy = None
_LiquiditySweepReversalStrategy = None
_ConsecutiveDownRsiStrategy = None
_Rsi2BbSqueezeStrategy = None
_AutocorrReversionStrategy = None
_VolumeProfileDeviationStrategy = None

try:
    from paper_trading.strategies.corr_trend_strategies import CorrHMATrend
    _CorrHMATrend = CorrHMATrend
except ImportError as e:
    logger.warning("Could not import CorrHMATrend: %s", e)

try:
    from baby_strategies.overnight_seasonality_btc import OvernightSeasonalityBTCStrategy
    _OvernightSeasonalityBTCStrategy = OvernightSeasonalityBTCStrategy
except ImportError as e:
    logger.warning("Could not import OvernightSeasonalityBTCStrategy: %s", e)

try:
    from baby_strategies.pairs_spread_btceth import PairsSpreadBTCETHStrategy
    _PairsSpreadBTCETHStrategy = PairsSpreadBTCETHStrategy
except ImportError as e:
    logger.warning("Could not import PairsSpreadBTCETHStrategy: %s", e)

try:
    from baby_strategies.liquidity_sweep_reversal import LiquiditySweepReversalStrategy
    _LiquiditySweepReversalStrategy = LiquiditySweepReversalStrategy
except ImportError as e:
    logger.warning("Could not import LiquiditySweepReversalStrategy: %s", e)

try:
    from baby_strategies.consecutive_down_rsi import ConsecutiveDownRsiStrategy
    _ConsecutiveDownRsiStrategy = ConsecutiveDownRsiStrategy
except ImportError as e:
    logger.warning("Could not import ConsecutiveDownRsiStrategy: %s", e)

try:
    from baby_strategies.rsi2_bb_squeeze import Rsi2BbSqueezeStrategy
    _Rsi2BbSqueezeStrategy = Rsi2BbSqueezeStrategy
except ImportError as e:
    logger.warning("Could not import Rsi2BbSqueezeStrategy: %s", e)

try:
    from baby_strategies.autocorr_reversion import AutocorrReversionStrategy
    _AutocorrReversionStrategy = AutocorrReversionStrategy
except ImportError as e:
    logger.warning("Could not import AutocorrReversionStrategy: %s", e)

try:
    from baby_strategies.volume_profile_deviation import VolumeProfileDeviationStrategy
    _VolumeProfileDeviationStrategy = VolumeProfileDeviationStrategy
except ImportError as e:
    logger.warning("Could not import VolumeProfileDeviationStrategy: %s", e)

# Prop firm always-on strategies (from quan_engine/)
_RSIMomentumStrategy = None
_ATRBreakoutStrategy = None
_EMAMomentumStrategy = None
_FearGreedContrarianStrategy = None

try:
    from quan_engine.prop_strategies import RSIMomentumStrategy
    _RSIMomentumStrategy = RSIMomentumStrategy
except ImportError as e:
    logger.warning("Could not import RSIMomentumStrategy: %s", e)

try:
    from quan_engine.prop_strategies import ATRBreakoutStrategy
    _ATRBreakoutStrategy = ATRBreakoutStrategy
except ImportError as e:
    logger.warning("Could not import ATRBreakoutStrategy: %s", e)

try:
    from quan_engine.prop_strategies import EMAMomentumStrategy
    _EMAMomentumStrategy = EMAMomentumStrategy
except ImportError as e:
    logger.warning("Could not import EMAMomentumStrategy: %s", e)

try:
    from quan_engine.prop_strategies import FearGreedContrarianStrategy
    _FearGreedContrarianStrategy = FearGreedContrarianStrategy
except ImportError as e:
    logger.warning("Could not import FearGreedContrarianStrategy: %s", e)

# Wave 20 proven strategies
_KeltnerSqueezeStrategy = None
_TripleEMAPullbackStrategy = None
_VWAPMeanReversionStrategy = None
_StochRSIDivergenceStrategy = None
_PropFirmConservativeStrategy = None
_EMAMomentumAggressiveStrategy = None

try:
    from quan_engine.prop_strategies import (
        KeltnerSqueezeStrategy, TripleEMAPullbackStrategy,
        VWAPMeanReversionStrategy, StochRSIDivergenceStrategy,
        PropFirmConservativeStrategy, EMAMomentumAggressiveStrategy,
    )
    _KeltnerSqueezeStrategy = KeltnerSqueezeStrategy
    _TripleEMAPullbackStrategy = TripleEMAPullbackStrategy
    _VWAPMeanReversionStrategy = VWAPMeanReversionStrategy
    _StochRSIDivergenceStrategy = StochRSIDivergenceStrategy
    _PropFirmConservativeStrategy = PropFirmConservativeStrategy
    _EMAMomentumAggressiveStrategy = EMAMomentumAggressiveStrategy
except ImportError as e:
    logger.warning("Could not import Wave 20 proven strategies: %s", e)


# ---------------------------------------------------------------------------
# Registry: strategy_name -> (class_ref, interface_type)
#   interface_type determines how we call the strategy and normalize output.
#     "generate_picks"   -> CorrHMATrend.generate_picks(data: dict) -> List[NormalizedPick]
#     "generate_signals" -> *.generate_signals(data: DataFrame, symbol: str) -> List[Signal]
#     "autocorr_dict"    -> AutocorrReversion.generate_signals(df, symbol) -> list[dict]
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: Dict[str, dict] = {
    "corr_hma_trend": {
        "cls": _CorrHMATrend,
        "interface": "generate_picks",
    },
    "overnight_seasonality_btc": {
        "cls": _OvernightSeasonalityBTCStrategy,
        "interface": "generate_signals",
    },
    "pairs_spread_btceth": {
        "cls": _PairsSpreadBTCETHStrategy,
        "interface": "generate_signals",
    },
    "liquidity_sweep_reversal": {
        "cls": _LiquiditySweepReversalStrategy,
        "interface": "generate_signals",
    },
    "consecutive_down_rsi": {
        "cls": _ConsecutiveDownRsiStrategy,
        "interface": "generate_signals",
    },
    "rsi2_bb_squeeze": {
        "cls": _Rsi2BbSqueezeStrategy,
        "interface": "generate_signals",
    },
    "autocorr_reversion": {
        "cls": _AutocorrReversionStrategy,
        "interface": "autocorr_dict",
    },
    "volume_profile_deviation": {
        "cls": _VolumeProfileDeviationStrategy,
        "interface": "generate_signals",
    },
    # Prop firm always-on strategies
    "rsi_momentum_prop": {
        "cls": _RSIMomentumStrategy,
        "interface": "generate_signals",
    },
    "atr_breakout_prop": {
        "cls": _ATRBreakoutStrategy,
        "interface": "generate_signals",
    },
    "ema_momentum_prop": {
        "cls": _EMAMomentumStrategy,
        "interface": "generate_signals",
    },
    "fear_greed_contrarian": {
        "cls": _FearGreedContrarianStrategy,
        "interface": "generate_signals",
    },
    # Wave 20 proven strategies
    "proven_keltner_squeeze_prop": {
        "cls": _KeltnerSqueezeStrategy,
        "interface": "generate_signals",
    },
    "proven_triple_ema_prop": {
        "cls": _TripleEMAPullbackStrategy,
        "interface": "generate_signals",
    },
    "proven_vwap_mr_prop": {
        "cls": _VWAPMeanReversionStrategy,
        "interface": "generate_signals",
    },
    "proven_stochrsi_prop": {
        "cls": _StochRSIDivergenceStrategy,
        "interface": "generate_signals",
    },
    "proven_propfirm_cons_prop": {
        "cls": _PropFirmConservativeStrategy,
        "interface": "generate_signals",
    },
    "ema_aggressive_prop": {
        "cls": _EMAMomentumAggressiveStrategy,
        "interface": "generate_signals",
    },
}


def _make_abstain(strategy_name: str) -> dict:
    """Return a neutral ABSTAIN vote for a strategy that produced no signal."""
    return {
        "strategy": strategy_name,
        "direction": "ABSTAIN",
        "confidence": 0.0,
        "entry_price": 0.0,
        "take_profit": 0.0,
        "stop_loss": 0.0,
        "reason": "No signal",
    }


# ---------------------------------------------------------------------------
# Direction normalisation helpers
# ---------------------------------------------------------------------------

_BUY_ALIASES = {"BUY", "LONG", "BULL", "UP"}
_SELL_ALIASES = {"SELL", "SHORT", "BEAR", "DOWN"}


def _normalize_direction(raw: str) -> str:
    """Map strategy-specific direction strings to BUY / SELL / ABSTAIN."""
    upper = raw.upper().strip()
    if upper in _BUY_ALIASES:
        return "BUY"
    if upper in _SELL_ALIASES:
        return "SELL"
    return "ABSTAIN"


# ---------------------------------------------------------------------------
# Signal normalisation
# ---------------------------------------------------------------------------

def _normalize_signal(signal, strategy_name: str) -> dict:
    """Convert a Signal dataclass, dict, or NormalizedPick into a Vote dict.

    Vote schema:
        strategy     : str
        direction    : "BUY" | "SELL" | "ABSTAIN"
        confidence   : float  (0-1)
        entry_price  : float
        take_profit  : float
        stop_loss    : float
        reason       : str
    """

    # --- dict (autocorr_reversion output) ---
    if isinstance(signal, dict):
        return {
            "strategy": strategy_name,
            "direction": _normalize_direction(signal.get("side", signal.get("direction", "ABSTAIN"))),
            "confidence": float(signal.get("confidence", signal.get("strength", 0.0))),
            "entry_price": float(signal.get("entry_price", 0.0)),
            "take_profit": float(signal.get("take_profit", 0.0)),
            "stop_loss": float(signal.get("stop_loss", 0.0)),
            "reason": str(signal.get("reason", "")),
        }

    # --- dataclass with attribute access (Signal or NormalizedPick) ---
    direction_raw = getattr(signal, "direction", None) or getattr(signal, "side", "ABSTAIN")
    confidence = float(getattr(signal, "confidence", 0.0))
    entry_price = float(getattr(signal, "entry_price", 0.0))
    # NormalizedPick uses 'tp' / 'sl'; Signal uses 'take_profit' / 'stop_loss'
    take_profit = float(
        getattr(signal, "take_profit", None)
        or getattr(signal, "tp", 0.0)
    )
    stop_loss = float(
        getattr(signal, "stop_loss", None)
        or getattr(signal, "sl", 0.0)
    )
    reason = str(getattr(signal, "reason", ""))

    return {
        "strategy": strategy_name,
        "direction": _normalize_direction(str(direction_raw)),
        "confidence": confidence,
        "entry_price": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# StrategyPool
# ---------------------------------------------------------------------------

class StrategyPool:
    """Run a pool of strategies and collect normalised votes.

    Usage:
        pool = StrategyPool("TRENDING")
        votes = pool.get_votes(ohlcv_df, "BTCUSDT")
    """

    POOLS = {
        "TRENDING": config.TRENDING_STRATEGIES,
        "MEAN_REVERSION": config.MR_STRATEGIES,
        "PROP": config.PROP_STRATEGIES,
    }

    def __init__(self, pool_type: str):
        if pool_type not in self.POOLS:
            raise ValueError(f"Unknown pool_type '{pool_type}'. Choose from {list(self.POOLS)}")
        self.pool_type = pool_type
        self.strategy_names: List[str] = self.POOLS[pool_type]
        self.strategies: Dict[str, object] = {}
        self._init_strategies()

    # ----- internal setup ---------------------------------------------------

    def _init_strategies(self):
        """Instantiate each strategy class referenced by the pool."""
        for name in self.strategy_names:
            entry = STRATEGY_REGISTRY.get(name)
            if entry is None:
                logger.warning("Strategy '%s' not found in registry — skipping", name)
                continue
            cls = entry["cls"]
            if cls is None:
                logger.warning("Strategy '%s' failed to import — will ABSTAIN", name)
                continue
            try:
                self.strategies[name] = cls()
            except Exception as exc:
                logger.warning("Failed to instantiate strategy '%s': %s", name, exc)

    # ----- run a single strategy -------------------------------------------

    def _run_strategy(
        self,
        strategy,
        name: str,
        data: pd.DataFrame,
        symbol: str,
    ) -> List[dict]:
        """Call the strategy and return a list of normalised Vote dicts."""
        entry = STRATEGY_REGISTRY[name]
        interface = entry["interface"]
        raw_signals = []

        if interface == "generate_picks":
            # CorrHMATrend expects a dict of {symbol: klines}
            # Build a minimal klines-like list from the DataFrame
            klines_dict = self._df_to_klines_dict(data, symbol)
            raw_signals = strategy.generate_picks(klines_dict)

        elif interface == "generate_signals":
            raw_signals = strategy.generate_signals(data, symbol)

        elif interface == "autocorr_dict":
            raw_signals = strategy.generate_signals(data, symbol)

        else:
            logger.warning("Unknown interface '%s' for strategy '%s'", interface, name)
            return []

        # Normalise each raw signal
        return [_normalize_signal(sig, name) for sig in (raw_signals or [])]

    # ----- public API -------------------------------------------------------

    def get_votes(self, data: pd.DataFrame, symbol: str) -> List[dict]:
        """Run all strategies in the pool and return one Vote per strategy.

        For strategies that emit multiple signals, the one with the highest
        confidence is chosen.  Strategies that produce no signal or fail
        return an ABSTAIN vote so the ensemble always sees a full roster.
        """
        votes: List[dict] = []

        for name in self.strategy_names:
            strategy = self.strategies.get(name)
            if strategy is None:
                votes.append(_make_abstain(name))
                continue

            try:
                signals = self._run_strategy(strategy, name, data, symbol)
                if signals:
                    best = max(signals, key=lambda s: s.get("confidence", 0.0))
                    votes.append(best)
                else:
                    votes.append(_make_abstain(name))
            except Exception as exc:
                logger.warning("Strategy '%s' raised during execution: %s", name, exc)
                votes.append(_make_abstain(name))

        return votes

    # ----- helpers ----------------------------------------------------------

    @staticmethod
    def _df_to_klines_dict(df: pd.DataFrame, symbol: str) -> dict:
        """Convert an OHLCV DataFrame into the {symbol: klines_list} format
        expected by CorrHMATrend.generate_picks().

        Each kline row is a list: [open_time, open, high, low, close, volume, ...]
        matching the Binance kline format (index 4 = close price).
        """
        klines = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp() * 1000) if hasattr(idx, "timestamp") else 0
            klines.append([
                ts,                                           # 0: open_time
                float(row.get("open", row.get("Open", 0))),  # 1: open
                float(row.get("high", row.get("High", 0))),  # 2: high
                float(row.get("low", row.get("Low", 0))),    # 3: low
                float(row.get("close", row.get("Close", 0))),# 4: close
                float(row.get("volume", row.get("Volume", 0))),# 5: volume
            ])
        return {symbol: klines}

    def available_strategies(self) -> List[str]:
        """Return names of strategies that were successfully imported and instantiated."""
        return list(self.strategies.keys())

    def missing_strategies(self) -> List[str]:
        """Return names of strategies that failed to import or instantiate."""
        return [n for n in self.strategy_names if n not in self.strategies]

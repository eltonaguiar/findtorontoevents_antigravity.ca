"""
Prop Firm Classic Strategies + Justin's Methods + J Bravo — Paper Trading
==========================================================================

13 strategies for prop firm challenges:
  - 5 battle-tested classics (ORB, Turtle, Inside Bar, VWAP, Session)
  - 3 Justin's methods (EMA9 Close, RSI MTF, Double Top/Tweezer)
  - 3 J Bravo / ChartPrime (Triple MA, GoGo Juice, 9 Count)
  - 2 Enhanced (GoGo Enhanced, Confluence Power)
"""

from typing import List
import pandas as pd
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from baby_strategies.prop_firm_classics import (
    OpeningRangeBreakout, TurtleDonchianBreakout, InsideBarBreakout,
    VWAPMeanReversion, SessionMomentum,
    EMA9CloseCrossover, RSIMultiTimeframeBias, DoubleTweeterPattern,
    BravoTripleMA, GoGoJuice, Bravo9CountExhaustion,
    GoGoJuiceEnhanced, ConfluencePower,
    VWAPGoGoHybrid, ExhaustionReversal,
)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


def _klines_to_df(klines):
    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df


def _signal_to_pick(sig, strategy_name, display_name):
    return NormalizedPick(
        symbol=sig.symbol,
        direction="LONG" if sig.direction == "BUY" else "SHORT",
        entry_price=sig.entry_price,
        tp=sig.take_profit,
        sl=sig.stop_loss,
        strategy=strategy_name,
        strategy_name=display_name,
        category="crypto",
        confidence=sig.confidence,
        reason=sig.reason,
    )


def _make_pt_class(strategy_cls, interval="15m", limit=200):
    """Factory to create paper trading wrapper from a baby strategy class."""

    class PT(BaseStrategy):
        name = strategy_cls.name
        display_name = strategy_cls.display_name
        source = f"Prop Firm Classics — {strategy_cls.display_name}"
        category = "crypto"
        portfolio_type = "technical"
        symbols = SYMBOLS

        def fetch_data(self, symbol=None):
            all_data = {}
            for sym in self.symbols:
                try:
                    klines = self.fetch_klines(sym, interval=interval, limit=limit)
                    if klines:
                        all_data[sym] = klines
                except Exception:
                    pass
            return all_data

        def generate_picks(self, data: dict) -> List[NormalizedPick]:
            picks = []
            for sym, klines in data.items():
                try:
                    df = _klines_to_df(klines)
                    signals = strategy_cls.generate_signals(df, sym)
                    for sig in signals:
                        picks.append(_signal_to_pick(sig, self.name, self.display_name))
                except Exception:
                    pass
            return picks

    PT.__name__ = f"{strategy_cls.__name__}PT"
    PT.__qualname__ = PT.__name__
    PT.__doc__ = strategy_cls.__doc__
    return PT


# Battle-tested classics (all 1h — 15m ATR is too small for proper stops)
OpeningRangeBreakoutPT = _make_pt_class(OpeningRangeBreakout, "1h", 200)
TurtleDonchianBreakoutPT = _make_pt_class(TurtleDonchianBreakout, "1h", 200)
InsideBarBreakoutPT = _make_pt_class(InsideBarBreakout, "1h", 200)
VWAPMeanReversionPT = _make_pt_class(VWAPMeanReversion, "1h", 200)
SessionMomentumPT = _make_pt_class(SessionMomentum, "1h", 200)

# Justin's methods (1h for proper ATR-based stops)
EMA9CloseCrossoverPT = _make_pt_class(EMA9CloseCrossover, "1h", 200)
RSIMultiTimeframeBiasPT = _make_pt_class(RSIMultiTimeframeBias, "1h", 200)
DoubleTweeterPatternPT = _make_pt_class(DoubleTweeterPattern, "1h", 200)

# J Bravo / ChartPrime (1h)
BravoTripleMAPT = _make_pt_class(BravoTripleMA, "1h", 250)
GoGoJuicePT = _make_pt_class(GoGoJuice, "1h", 200)
Bravo9CountExhaustionPT = _make_pt_class(Bravo9CountExhaustion, "1h", 200)

# Enhanced strategies (1h for better SL distance)
GoGoJuiceEnhancedPT = _make_pt_class(GoGoJuiceEnhanced, "1h", 200)
ConfluencePowerPT = _make_pt_class(ConfluencePower, "1h", 200)

# Hybrid variations (combining winning patterns)
VWAPGoGoHybridPT = _make_pt_class(VWAPGoGoHybrid, "1h", 200)
ExhaustionReversalPT = _make_pt_class(ExhaustionReversal, "1h", 200)

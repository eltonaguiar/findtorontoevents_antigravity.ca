"""
Forward-Proven Strategy Variations — Paper Trading Wrappers
============================================================
Top 3 strategies from extensive backtesting across 20 crypto pairs:
  1. Keltner RSI Squeeze       — PF 2.49, 51.2% WR, 2087 trades
  2. Keltner+VWAP Confluence   — PF 1.34, 42.5% WR, 3596 trades
  3. Adaptive Keltner Reversion — PF 2.70, 55.9% WR (throttled)
"""

from typing import List
import pandas as pd
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from baby_strategies.forward_proven_variations import (
    KeltnerRSISqueeze,
    KeltnerVWAPConfluence,
    AdaptiveKeltnerReversion,
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


def _make_pt_class(strategy_cls, interval="1h", limit=200):
    """Factory to create paper trading wrapper from a forward-proven strategy."""

    class PT(BaseStrategy):
        name = strategy_cls.name
        display_name = strategy_cls.display_name
        source = f"Forward-Proven -- {strategy_cls.display_name}"
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
                    # Only take last signal to avoid over-trading
                    signals = strategy_cls.generate_signals(df, sym)
                    if signals:
                        picks.append(_signal_to_pick(signals[-1], self.name, self.display_name))
                except Exception:
                    pass
            return picks

    PT.__name__ = f"{strategy_cls.__name__}PT"
    PT.__qualname__ = PT.__name__
    PT.__doc__ = strategy_cls.__doc__
    return PT


# Top 3 forward-proven strategies — all on 1h for proper ATR
KeltnerRSISqueezePT = _make_pt_class(KeltnerRSISqueeze, "1h", 200)
KeltnerVWAPConfluencePT = _make_pt_class(KeltnerVWAPConfluence, "1h", 200)
AdaptiveKeltnerReversionPT = _make_pt_class(AdaptiveKeltnerReversion, "1h", 200)

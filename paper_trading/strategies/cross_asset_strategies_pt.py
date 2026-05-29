"""
Cross-Asset Strategy Paper Trading Wrappers
============================================
Top 3 strategies from batch 3/4 testing that work across multiple asset classes:
  1. FibonacciRsiMeanReversion   — PF 2.70, 133 trades, ALL 5 classes (commodity PF 6.12!)
  2. VolumeWeightedMedianZScore   — PF 1.73, 532 trades, ALL 4 classes (forex PF 2.74!)
  3. VolumePriceConfirmationReversal — PF 1.81, 175 trades, 3 classes (ETF PF 3.58!)
"""

from typing import List
import pandas as pd
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from baby_strategies.fibonacci_rsi_mean_reversion import FibonacciRsiMeanReversionStrategy
from baby_strategies.volume_weighted_median_zscore import VolumeWeightedMedianZScoreStrategy
from baby_strategies.volume_price_confirmation_reversal import VolumePriceConfirmationReversalStrategy


CRYPTO_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "LINKUSDT", "DOTUSDT", "DOGEUSDT", "LTCUSDT",
    "BNBUSDT", "SUIUSDT", "ARBUSDT",
]

ETF_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM", "XLF", "XLK", "XLV", "XLE"]

EQUITY_SYMBOLS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM"]

FOREX_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

COMMODITY_SYMBOLS = ["GC=F", "SI=F", "CL=F", "NQ=F"]

ALL_SYMBOLS = CRYPTO_SYMBOLS + ETF_SYMBOLS + EQUITY_SYMBOLS + FOREX_SYMBOLS + COMMODITY_SYMBOLS


def _klines_to_df(klines):
    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df


def _signal_to_pick(sig, strategy_name, display_name, category="crypto"):
    return NormalizedPick(
        symbol=sig.symbol,
        direction="LONG" if sig.direction == "BUY" else "SHORT",
        entry_price=sig.entry_price,
        tp=sig.take_profit,
        sl=sig.stop_loss,
        strategy=strategy_name,
        strategy_name=display_name,
        category=category,
        confidence=sig.confidence,
        reason=sig.reason,
    )


def _make_cross_asset_pt(strategy_cls, interval="1d", limit=500, symbols=None, cat="multi"):
    """Factory to create paper trading wrapper from a cross-asset baby strategy."""
    _cat = cat
    _symbols = symbols or ALL_SYMBOLS

    class PT(BaseStrategy):
        name = strategy_cls().NAME if hasattr(strategy_cls(), 'NAME') else strategy_cls.__name__.lower().replace('strategy', '')
        display_name = strategy_cls.__name__.replace('Strategy', '')
        source = f"Cross-Asset -- {display_name}"
        category = _cat
        portfolio_type = "technical"
        symbols = _symbols

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
            strat = strategy_cls()
            for sym, klines in data.items():
                try:
                    df = _klines_to_df(klines)
                    signals = strat.generate_signals(df, sym)
                    if signals:
                        cat = "crypto" if "USDT" in sym else ("forex" if sym in FOREX_SYMBOLS else "equity")
                        picks.append(_signal_to_pick(signals[-1], self.name, self.display_name, cat))
                except Exception:
                    pass
            return picks

    PT.__name__ = f"{strategy_cls.__name__}PT"
    PT.__qualname__ = PT.__name__
    PT.__doc__ = strategy_cls.__doc__
    return PT


# Cross-asset strategies — daily timeframe for proper multi-class signals
FibonacciRsiMeanReversionPT = _make_cross_asset_pt(
    FibonacciRsiMeanReversionStrategy, "1d", 500, ALL_SYMBOLS, "multi"
)
VolumeWeightedMedianZScorePT = _make_cross_asset_pt(
    VolumeWeightedMedianZScoreStrategy, "1d", 500, ALL_SYMBOLS, "multi"
)
VolumePriceConfirmationReversalPT = _make_cross_asset_pt(
    VolumePriceConfirmationReversalStrategy, "1d", 500, ALL_SYMBOLS, "multi"
)

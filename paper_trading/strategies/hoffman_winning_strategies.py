"""
Hoffman Winning Combo Strategies — Paper Trading Integration
=============================================================

5 winning Hoffman variants discovered through exhaustive combination testing
(49 combinations × 10 symbols). These break the 45% WR ceiling.

Results from backtest_hoffman_combos.py (2026-03-07):
  1. HoffmanEliteCombo:  78.9% WR, PF 5.61, Sharpe 14.35 (19 trades)
  2. HoffmanRSI2Ribbon:  75.0% WR, PF 5.70, Sharpe 14.08 (20 trades)
  3. HoffmanVolumeHTF:   53.6% WR, PF 1.59, Sharpe 3.54  (138 trades)
  4. HoffmanVolumePower:  53.2% WR, PF 1.67, Sharpe 3.63  (308 trades)
  5. HoffmanMACDRegime:   48.8% WR, PF 1.37, Sharpe 2.36  (258 trades)
"""

from typing import List
import pandas as pd
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from baby_strategies.hoffman_winning_combos import (
    HoffmanEliteCombo, HoffmanRSI2Ribbon, HoffmanVolumeHTF,
    HoffmanVolumePower, HoffmanMACDRegime,
)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
           "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
           "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
           "ETCUSDT", "HBARUSDT", "ALGOUSDT"]


def _klines_to_df(klines):
    """Convert Binance-format klines to DataFrame."""
    df = pd.DataFrame(klines, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df


def _signal_to_pick(sig, strategy_name, display_name, category="crypto"):
    """Convert baby_strategies Signal to NormalizedPick."""
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
        raw_signal={"direction": sig.direction, "confidence": sig.confidence},
    )


class HoffmanEliteComboPT(BaseStrategy):
    """78.9% WR — IRB + RSI(2) + Consecutive candles + Volume + Wide stops."""
    name = "hoffman_elite_combo"
    display_name = "Hoffman Elite Combo (78.9% WR)"
    source = "IRB + Connors RSI-2 + Consecutive reversal + Volume"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="15m", limit=200)
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
                signals = HoffmanEliteCombo.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class HoffmanRSI2RibbonPT(BaseStrategy):
    """75.0% WR — IRB + RSI(2) + Volume + EMA ribbon."""
    name = "hoffman_rsi2_ribbon"
    display_name = "Hoffman RSI2 Ribbon (75% WR)"
    source = "IRB + Connors RSI-2 + EMA 5/20/SMA50 ribbon + Volume"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="15m", limit=200)
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
                signals = HoffmanRSI2Ribbon.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class HoffmanVolumeHTFPT(BaseStrategy):
    """53.6% WR, 138 trades — best balance of WR and frequency."""
    name = "hoffman_volume_htf"
    display_name = "Hoffman Volume HTF (53.6% WR)"
    source = "IRB + HTF EMA + Volume + RSI moderate"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="15m", limit=200)
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
                signals = HoffmanVolumeHTF.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class HoffmanVolumePowerPT(BaseStrategy):
    """53.2% WR, +92.55% PnL — highest total returns."""
    name = "hoffman_volume_power"
    display_name = "Hoffman Volume Power (+92% PnL)"
    source = "IRB + Volume + Wide ATR stops"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="15m", limit=200)
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
                signals = HoffmanVolumePower.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class HoffmanMACDRegimePT(BaseStrategy):
    """48.8% WR, 258 trades — reliable workhorse."""
    name = "hoffman_macd_regime"
    display_name = "Hoffman MACD Regime (48.8% WR)"
    source = "IRB + MACD + Volume + ADX regime"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="15m", limit=200)
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
                signals = HoffmanMACDRegime.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks

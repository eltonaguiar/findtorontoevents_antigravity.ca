"""
Championship-Winning Strategies — Paper Trading Integration
=============================================================

5 strategies derived from deep research into competition-winning traders:
  1. LiquidationCascadeRecovery: Crypto-native cascade detection + recovery
  2. AdaptiveRegimeRouter: ADX+Hurst regime classification → optimal sub-strategy
  3. MTFConfluenceSwing: Hoffman-fixed with all 7 root causes addressed
  4. VolatilityCompressionBreakout: ATR compression → volume expansion breakout
  5. SmartMoneyReversal: SFP liquidity sweep + volume spike reversal

Backtest results (2026-03-07):
  - SmartMoneyReversal: 48.6% WR, +66% PnL, PF 1.37
  - AdaptiveRegimeRouter: 44.4% WR, +38% PnL, PF 1.20
  - VolatilityCompressionBreakout: 41.3% WR, +1% PnL
  - Best pair-specific: ADAUSDT 1h SMR=66.7% WR, XRPUSDT 4h ARR=56.2% WR
"""

from typing import List
import pandas as pd
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from baby_strategies.championship_strategies import (
    LiquidationCascadeRecoveryStrategy,
    AdaptiveRegimeRouterStrategy,
    MTFConfluenceSwingStrategy,
    VolatilityCompressionBreakoutStrategy,
    SmartMoneyReversalStrategy,
)

# Extended symbols for championship strategies
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


class LiquidationCascadeRecoveryPT(BaseStrategy):
    """Crypto-native: detects liquidation cascades → recovery entry."""
    name = "liquidation_cascade_recovery"
    display_name = "Liquidation Cascade Recovery"
    source = "Market microstructure — leveraged cascade detection"
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
                signals = LiquidationCascadeRecoveryStrategy.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class AdaptiveRegimeRouterPT(BaseStrategy):
    """Championship regime router: trending/ranging/volatile sub-strategies."""
    name = "adaptive_regime_router"
    display_name = "Adaptive Regime Router"
    source = "Larry Williams + System B regime classification"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=200)
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
                signals = AdaptiveRegimeRouterStrategy.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class MTFConfluenceSwingPT(BaseStrategy):
    """Hoffman-fixed: EMA ribbon + 55% IRB + ADX + volume + ATR-scaled exits."""
    name = "mtf_confluence_swing"
    display_name = "MTF Confluence Swing (Hoffman Fixed)"
    source = "Rob Hoffman adapted for crypto — all 7 failure modes fixed"
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
                signals = MTFConfluenceSwingStrategy.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class VolatilityCompressionBreakoutPT(BaseStrategy):
    """Championship breakout: ATR compression → volume expansion → directional break."""
    name = "volatility_compression_breakout"
    display_name = "Volatility Compression Breakout"
    source = "Max Hamaha ICTC 2025 champion pattern"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=200)
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
                signals = VolatilityCompressionBreakoutStrategy.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks


class SmartMoneyReversalPT(BaseStrategy):
    """Institutional stop-hunt → liquidity sweep → reversal. Best championship strategy."""
    name = "smart_money_reversal"
    display_name = "Smart Money Reversal (Best Championship)"
    source = "Institutional SFP patterns + volume spike"
    category = "crypto"
    portfolio_type = "technical"
    symbols = SYMBOLS

    def fetch_data(self, symbol=None):
        all_data = {}
        for sym in self.symbols:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=200)
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
                signals = SmartMoneyReversalStrategy.generate_signals(df, sym)
                for sig in signals:
                    picks.append(_signal_to_pick(sig, self.name, self.display_name))
            except Exception:
                pass
        return picks

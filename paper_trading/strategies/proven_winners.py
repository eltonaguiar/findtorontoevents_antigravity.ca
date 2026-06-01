"""Proven Winner Strategy Wrappers — wire existing alpha_engine winners into paper_trading.

These are STATISTICALLY PROVEN winners from the live picks table:

  1. cot_positioning        COMMODITY  76% WR  n=137  avg +2.80%  ★ BEST non-crypto
  2. cftc_cot_commercial     COMMODITY  73% WR  n=135  avg +2.67%
  3. cta_cross_asset_tsmom   FOREX      57% WR  n=181  avg +0.08%
  4. fx_smart_forex_rsi2     FOREX      50% WR  n=12
  5. stocks_rsi2_pullback    EQUITY     48% WR  n=48   avg +0.89%
  6. bond_mean_reversion     BOND       active on IEF/LQD/TLT
  7. etf_faber_tactical      ETF        active on EFA/QQQ
  8. etf_rsi2_pullback       ETF        active on XLI/XLY
  9. etf_sector_momentum     ETF        active on XLE
 10. futures_connors_rsi2    FUTURES    active on ES=NQ=RTY=YM
 11. stocks_ema_golden_cross EQUITY     active on ADBE/CVX
 12. futures_bb_mean_rev     COMMODITY  active on KC=F
 13. futures_momentum        COMMODITY  active on GC=F
 14. cftc_cot_weekly         COMMODITY  active on ZC=F/ZS=F/ZW=F

All source functions live in alpha_engine/*.py — these are paper_trading wrappers.
"""
from typing import List, Optional
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick


def _alpha_to_pick(result: dict, strategy: str, display_name: str,
                   category: str, default_conf: float = 0.65) -> Optional[NormalizedPick]:
    """Convert alpha_engine scanner result → NormalizedPick."""
    try:
        sym = result.get("symbol", "")
        sig = result.get("signal", result.get("direction", "")).upper()
        if not sym or sig not in ("BUY", "SELL", "LONG", "SHORT", "BULLISH", "BEARISH"):
            return None
        direction = "LONG" if sig in ("BUY", "LONG", "BULLISH") else "SHORT"
        entry = float(result.get("entry_price", result.get("price", 0)))
        if entry <= 0:
            return None
        tp = float(result.get("take_profit", result.get("tp", entry * 1.03)))
        sl = float(result.get("stop_loss", result.get("sl", entry * 0.97)))
        conf = float(result.get("confidence", default_conf))
        reason = result.get("reason", strategy)
        raw = {k: v for k, v in result.items() if k not in
               ("symbol", "signal", "direction", "entry_price", "take_profit",
                "stop_loss", "confidence", "reason", "price", "tp", "sl")}
        return NormalizedPick(
            symbol=sym, direction=direction,
            entry_price=round(entry, 6), tp=round(tp, 6), sl=round(sl, 6),
            strategy=strategy, strategy_name=display_name, category=category,
            confidence=round(conf, 3), reason=reason, raw_signal=raw or None,
        )
    except Exception:
        return None


def _run(strategy_fn, data: dict, strategy: str, display_name: str,
         category: str, default_conf: float = 0.65) -> List[NormalizedPick]:
    """Generic runner: call alpha_engine fn, convert results to picks."""
    picks = []
    try:
        results = strategy_fn(data)
        if isinstance(results, list):
            for r in results:
                p = _alpha_to_pick(r, strategy, display_name, category, default_conf)
                if p:
                    picks.append(p)
    except Exception as e:
        import logging
        logging.getLogger("paper_trading").error(f"{strategy} failed: {e}")
    return picks


# ──────────────────────────────────────────────────────────
# COMMODITY: COT Positioning — 76% WR, n=137, avg +2.80% ★
# ──────────────────────────────────────────────────────────
class COTPositioningProven(BaseStrategy):
    """COT Positioning — proven commodity winner (76% WR, n=137).

    CFTC Commitments of Traders data. Contrarian signal when commercial
    hedgers are at extreme net positions vs speculators.
    """
    name = "cot_positioning_proven"
    display_name = "COT Positioning (Proven 76% WR)"
    source = "CFTC COT Data"
    category = "commodity"
    portfolio_type = "cot_contrarian"
    symbols = ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "CT=F", "ZC=F", "ZS=F", "ZW=F"]

    def fetch_data(self) -> dict:
        from alpha_engine.cot_positioning import fetch_cot_data_cftc
        code_map = {"GC=F": "088691", "SI=F": "084691", "CL=F": "067651",
                    "NG=F": "023651", "HG=F": "085692", "CT=F": "033601",
                    "ZC=F": "002602", "ZS=F": "005602", "ZW=F": "001602"}
        data = {}
        for sym in self.symbols:
            code = code_map.get(sym, "")
            if code:
                data[sym] = fetch_cot_data_cftc(code)
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.cot_positioning import cot_positioning_strategy
        return _run(lambda d: cot_positioning_strategy(d, ""), data,
                     self.name, self.display_name, self.category, 0.76)


# ──────────────────────────────────────────────────────────
# COMMODITY: CFTC Commercial Signal — 73% WR, n=135, avg +2.67%
# ──────────────────────────────────────────────────────────
class CFTCCommercialProven(BaseStrategy):
    """CFTC Commercial Signal — proven commodity winner (73% WR, n=135).

    Weekly CFTC COT reports. Follow commercial hedger positioning.
    Contrarian: extreme commercial net long → SHORT (and vice versa).
    """
    name = "cftc_commercial_signal_proven"
    display_name = "CFTC Commercial Signal (Proven 73% WR)"
    source = "CFTC Weekly COT"
    category = "commodity"
    portfolio_type = "commercial_contrarian"
    symbols = ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ZC=F", "ZS=F", "ZW=F"]

    def fetch_data(self) -> dict:
        from alpha_engine.cot_positioning import fetch_cot_data_cftc
        code_map = {"GC=F": "088691", "SI=F": "084691", "CL=F": "067651",
                    "NG=F": "023651", "HG=F": "085692",
                    "ZC=F": "002602", "ZS=F": "005602", "ZW=F": "001602"}
        data = {}
        for sym in self.symbols:
            code = code_map.get(sym, "")
            if code:
                data[sym] = fetch_cot_data_cftc(code)
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.cot_positioning import cftc_cot_weekly_signals
        return _run(cftc_cot_weekly_signals, data,
                     self.name, self.display_name, self.category, 0.73)


# ─────────────────────────────────────────────────────────
# FOREX: CTA Cross-Asset TSMOM — 57% WR, n=181, avg +0.08%
# ──────────────────────────────────────────────────────────
class CTACrossAssetTSMOMProven(BaseStrategy):
    """CTA Cross-Asset TSMOM — proven forex winner (57% WR, n=181).

    Time-series momentum across forex pairs. 12-month momentum with
    1-month skip to avoid reversal. Classic CTA trend-following.
    """
    name = "cta_cross_asset_tsmom_proven"
    display_name = "CTA Cross-Asset TSMOM (Proven 57% WR)"
    source = "CTA Momentum Framework"
    category = "forex"
    portfolio_type = "cta_trend"
    symbols = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
               "USDCHF=X", "NZDUSD=X", "USDCAD=X", "EURGBP=X"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="2y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.cta_bridge import cta_cross_asset_tsmom
        return _run(cta_cross_asset_tsmom, data,
                     self.name, self.display_name, self.category, 0.57)


# ──────────────────────────────────────────────────────────
# EQUITY: Stocks RSI2 Pullback — 48% WR, n=48, avg +0.89%
# ──────────────────────────────────────────────────────────
class StocksRSI2PullbackProven(BaseStrategy):
    """Stocks RSI2 Pullback — equity strategy (48% WR, n=48).

    Connors RSI(2) pullback in established uptrend. Buy when RSI(2) < 10
    in stocks above 200-day SMA. Classic Larry Connors setup.
    """
    name = "stocks_rsi2_pullback_proven"
    display_name = "Stocks RSI2 Pullback (48% WR, n=48)"
    source = "Connors Research"
    category = "equity"
    portfolio_type = "rsi2_pullback"
    symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
               "AMD", "AVGO", "C", "CVX", "GS", "INTC", "LLY", "MS",
               "RIOT", "TXN", "UNH", "ADBE", "JPM"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.stock_strategies import stocks_rsi2_pullback
        return _run(stocks_rsi2_pullback, data,
                     self.name, self.display_name, self.category, 0.48)


# ──────────────────────────────────────────────────────────
# BOND: Bond Mean Reversion — active on IEF/LQD/TLT
# ──────────────────────────────────────────────────────────
class BondMeanReversionProven(BaseStrategy):
    """Bond Mean Reversion — active on IEF/LQD/TLT.

    Mean reversion in bond ETFs using Bollinger Band touches + RSI confirmation.
    Bonds tend to mean-revert due to duration targeting by institutional investors.
    """
    name = "bond_mean_reversion_proven"
    display_name = "Bond Mean Reversion (IEF/LQD/TLT)"
    source = "Bond Strategy Engine"
    category = "bond"
    portfolio_type = "bond_mr"
    symbols = ["IEF", "LQD", "TLT", "SHY", "HYG"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 100:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.bond_strategies import bond_mean_reversion
        return _run(bond_mean_reversion, data,
                     self.name, self.display_name, self.category, 0.55)


# ──────────────────────────────────────────────────────────
# ETF: Faber Tactical — active on EFA/QQQ
# ──────────────────────────────────────────────────────────
class ETFFaberTacticalProven(BaseStrategy):
    """ETF Faber Tactical — active on EFA/QQQ.

    Mebane Faber's 10-month moving average timing model. LONG when price
    above 10-month SMA, flat/cash when below. Academic: Faber (2007).
    """
    name = "etf_faber_tactical_proven"
    display_name = "ETF Faber Tactical (EFA/QQQ)"
    source = "Mebane Faber (2007)"
    category = "etf"
    portfolio_type = "tactical_allocation"
    symbols = ["EFA", "QQQ", "SPY", "IWM", "EEM", "GLD", "TLT"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="2y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.etf_strategies import etf_faber_tactical
        return _run(etf_faber_tactical, data,
                     self.name, self.display_name, self.category, 0.60)


# ──────────────────────────────────────────────────────────
# ETF: RSI2 Pullback — active on XLI/XLY
# ──────────────────────────────────────────────────────────
class ETFRSI2PullbackProven(BaseStrategy):
    """ETF RSI2 Pullback — active on XLI/XLY.

    Connors RSI(2) pullback in sector ETFs. Same logic as stocks version
    but applied to sector rotation.
    """
    name = "etf_rsi2_pullback_proven"
    display_name = "ETF RSI2 Pullback (XLI/XLY)"
    source = "Connors Research"
    category = "etf"
    portfolio_type = "etf_pullback"
    symbols = ["XLI", "XLY", "XLF", "XLK", "XLV", "XLE", "XLP", "XLU", "XLB", "XLRE"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.etf_strategies import etf_rsi2_pullback
        return _run(etf_rsi2_pullback, data,
                     self.name, self.display_name, self.category, 0.52)


# ──────────────────────────────────────────────────────────
# ETF: Sector Momentum — active on XLE
# ──────────────────────────────────────────────────────────
class ETFSectorMomentumProven(BaseStrategy):
    """ETF Sector Momentum — active on XLE.

    Relative strength sector rotation. LONG the strongest sector ETF,
    SHORT the weakest. Rebalancing monthly.
    """
    name = "etf_sector_momentum_proven"
    display_name = "ETF Sector Momentum (XLE)"
    source = "Sector Rotation Engine"
    category = "etf"
    portfolio_type = "sector_momentum"
    symbols = ["XLE", "XLK", "XLF", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.etf_strategies import etf_sector_momentum
        return _run(etf_sector_momentum, data,
                     self.name, self.display_name, self.category, 0.55)


# ──────────────────────────────────────────────────────────
# FUTURES: Connors RSI2 — active on ES=NQ=RTY=YM
# ──────────────────────────────────────────────────────────
class FuturesConnorsRSI2Proven(BaseStrategy):
    """Futures Connors RSI2 — active on ES/NQ/RTY/YM.

    RSI(2) pullback in equity index futures. Classic Connors setup adapted
    for futures contracts.
    """
    name = "futures_connors_rsi2_proven"
    display_name = "Futures Connors RSI2 (ES/NQ/RTY/YM)"
    source = "Connors Research + Futures"
    category = "futures"
    portfolio_type = "futures_pullback"
    symbols = ["ES=F", "NQ=F", "RTY=F", "YM=F"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.futures_strategies import futures_connors_rsi2
        return _run(futures_connors_rsi2, data,
                     self.name, self.display_name, self.category, 0.52)


# ──────────────────────────────────────────────────────────
# EQUITY: EMA Golden Cross — active on ADBE/CVX
# ──────────────────────────────────────────────────────────
class StocksEMAGoldenCrossProven(BaseStrategy):
    """Stocks EMA Golden Cross — active on ADBE/CVX.

    Golden cross (50-day EMA crosses above 200-day EMA) momentum signal.
    Classic trend-following setup for large-cap stocks.
    """
    name = "stocks_ema_golden_cross_proven"
    display_name = "Stocks EMA Golden Cross (ADBE/CVX)"
    source = "Trend Following Engine"
    category = "equity"
    portfolio_type = "golden_cross"
    symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
               "ADBE", "CVX", "AMD", "AVGO", "C", "GS", "INTC", "LLY",
               "MS", "RIOT", "TXN", "UNH", "JPM"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="2y", interval="1d", progress=False)
                if len(df) > 200:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.stock_strategies import stocks_ema_golden_cross
        return _run(stocks_ema_golden_cross, data,
                     self.name, self.display_name, self.category, 0.55)


# ──────────────────────────────────────────────────────────
# COMMODITY: Futures BB Mean Reversion — active on KC=F
# ──────────────────────────────────────────────────────────
class FuturesBBMeanReversionProven(BaseStrategy):
    """Futures BB Mean Reversion — active on KC=F.

    Bollinger Band mean reversion on commodity futures. Fade band extremes
    when volatility contracts (squeeze setup).
    """
    name = "futures_bb_mean_reversion_proven"
    display_name = "Futures BB Mean Reversion (KC=F)"
    source = "Bollinger + Futures"
    category = "commodity"
    portfolio_type = "bb_mean_reversion"
    symbols = ["KC=F", "SB=F", "CC=F", "OJ=F", "LB=F"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 100:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.futures_strategies import futures_bb_mean_reversion
        return _run(futures_bb_mean_reversion, data,
                     self.name, self.display_name, self.category, 0.50)


# ──────────────────────────────────────────────────────────
# COMMODITY: Futures Momentum — active on GC=F
# ─────────────────────────────────────────────────────────
class FuturesMomentumProven(BaseStrategy):
    """Futures Momentum — active on GC=F.

    Momentum breakout on commodity futures. Enter on new highs/lows with
    volume confirmation.
    """
    name = "futures_momentum_proven"
    display_name = "Futures Momentum (GC=F)"
    source = "Futures Momentum Engine"
    category = "commodity"
    portfolio_type = "futures_momentum"
    symbols = ["GC=F", "CL=F", "NG=F", "SI=F", "HG=F"]

    def fetch_data(self) -> dict:
        import yfinance as yf
        data = {}
        for sym in self.symbols:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if len(df) > 100:
                    data[sym] = df
            except Exception:
                pass
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.futures_strategies import futures_momentum
        return _run(futures_momentum, data,
                     self.name, self.display_name, self.category, 0.50)


# ──────────────────────────────────────────────────────────
# COMMODITY: CFTC COT Weekly — active on ZC=F/ZS=F/ZW=F
# ──────────────────────────────────────────────────────────
class CFTCCOTWeeklyProven(BaseStrategy):
    """CFTC COT Weekly — active on ZC=F/ZS=F/ZW=F.

    Weekly CFTC COT signals for agricultural commodities. Commercial
    positioning extremes signal contrarian entries.
    """
    name = "cftc_cot_weekly_proven"
    display_name = "CFTC COT Weekly (ZC=F/ZS=F/ZW=F)"
    source = "CFTC Weekly COT"
    category = "commodity"
    portfolio_type = "cot_weekly"
    symbols = ["ZC=F", "ZS=F", "ZW=F", "KC=F", "SB=F", "CC=F"]

    def fetch_data(self) -> dict:
        from alpha_engine.cot_positioning import fetch_cot_data_cftc
        code_map = {"ZC=F": "002602", "ZS=F": "005602", "ZW=F": "001602",
                    "KC=F": "071473", "SB=F": "080732", "CC=F": "073732"}
        data = {}
        for sym in self.symbols:
            code = code_map.get(sym, "")
            if code:
                data[sym] = fetch_cot_data_cftc(code)
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        from alpha_engine.cot_positioning import cftc_cot_weekly_signals
        return _run(cftc_cot_weekly_signals, data,
                     self.name, self.display_name, self.category, 0.65)

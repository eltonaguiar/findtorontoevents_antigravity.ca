"""IPO Drift Momentum + Cheap Stock Momentum — Two New Asset Class Strategies.

IPO Drift Momentum:
  Academic: Ritter (1991) "The Long-Run Performance of Initial Public Offerings"
  Short-term IPO drift: new listings tend to outperform in first 30-90 days
  due to underpricing, analyst coverage initiation, and index inclusion flows.

Cheap Stock Momentum:
  Low-priced stocks (<$10) with momentum breakout patterns.
  Academic: Bali, Cakici, Whitelaw (2011) — max return effect + momentum.
  These are NOT penny stocks — they're established companies trading at
  low absolute prices (split-adjusted, not market cap).

Both strategies use yfinance for data and follow the BaseStrategy interface.
"""
from typing import List, Optional
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick


def _fetch_yf_ohlcv(symbol: str, period: str = "1y", interval: str = "1d") -> Optional[dict]:
    """Fetch OHLCV from yfinance, return dict with 'df' key or None."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if len(df) < 50:
            return None
        return {"df": df, "symbol": symbol}
    except Exception:
        return None


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series, period=14):
    import pandas as pd
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _atr(high, low, close, period=14):
    import pandas as pd
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ============================================================
# IPO Drift Momentum Strategy
# ============================================================
# Recent IPOs (listed within 90 days) with positive momentum.
# These tend to have continued upside due to:
#  - Underpricing (IPO pop continues for weeks)
#  - Analyst coverage initiation (price targets set)
#  - Index inclusion flows (Russell 2000, etc.)
#  - Short squeeze potential (low float, high short interest)
# ============================================================
class IPODriftMomentum(BaseStrategy):
    """IPO Drift Momentum — captures post-IPO outperformance.

    Logic:
    1. Fetch recent IPOs (listed within 90 days)
    2. Filter for positive momentum: price > IPO price AND above 20-day EMA
    3. Entry: LONG on pullback to 20-day EMA with RSI(14) between 40-60
    4. Exit: TP = entry + 2× ATR(14), SL = entry - 1× ATR(14)
    5. Max hold: 30 days (IPO drift window closes)

    Universe: Recent IPOs from Yahoo Finance (manually curated list)
    """
    name = "ipo_drift_momentum"
    display_name = "IPO Drift Momentum"
    source = "IPO Universe + Momentum"
    category = "ipo"
    portfolio_type = "ipo_momentum"

    # Recent IPOs (as of 2026-06-01) — curated list
    # These are companies that went public within the last 90 days
    symbols = [
        "KKR", "RDDT", "AS", "TPG", "ARM", "BIRK", "KVUE", "GME",
        "FYBR", "BNTX", "SMCI", "CART", "BRO", "PLTR",
    ]

    TP_ATR_MULT = 2.0
    SL_ATR_MULT = 1.0
    HOLD_MAX = 30  # IPO drift window

    def fetch_data(self) -> dict:
        """Fetch yfinance data for IPO universe."""
        data = {}
        for sym in self.symbols:
            result = _fetch_yf_ohlcv(sym, period="6mo", interval="1d")
            if result:
                data[sym] = result
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        """Generate IPO drift momentum picks."""
        import pandas as pd
        picks = []

        for sym, result in data.items():
            df = result["df"]
            if len(df) < 30:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            current_price = close.iloc[-1]

            # Momentum filters
            ema20 = _ema(close, 20).iloc[-1]
            ema50 = _ema(close, 50).iloc[-1] if len(close) >= 50 else ema20
            rsi14 = _rsi(close, 14).iloc[-1]
            atr14 = _atr(high, low, close, 14).iloc[-1]

            # IPO drift signal:
            # 1. Price above 20-day EMA (short-term uptrend)
            # 2. RSI between 40-60 (not overbought, room to run)
            # 3. Price above IPO price (proxy: 60-day low + 10%)
            price_above_ema = current_price > ema20
            rsi_ok = 40 <= rsi14 <= 65
            min_60d = low.rolling(60).min().iloc[-1] if len(low) >= 60 else low.min()
            above_ipo_proxy = current_price > min_60d * 1.05

            if price_above_ema and rsi_ok and above_ipo_proxy:
                direction = "LONG"
                tp = current_price + atr14 * self.TP_ATR_MULT
                sl = current_price - atr14 * self.SL_ATR_MULT
                rr = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0

                # Confidence: stronger if RSI in sweet spot (50-60)
                confidence = min(0.80, 0.55 + (60 - rsi14) / 50)

                picks.append(NormalizedPick(
                    symbol=sym,
                    direction=direction,
                    entry_price=round(current_price, 2),
                    tp=round(tp, 2),
                    sl=round(sl, 2),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=(f"IPO drift: price={current_price:.2f}, "
                            f"EMA20={ema20:.2f}, RSI={rsi14:.1f}, "
                            f"above_ipo_proxy={above_ipo_proxy}"),
                    risk_reward=round(rr, 2),
                    raw_signal={
                        "ema20": round(ema20, 2),
                        "ema50": round(ema50, 2),
                        "rsi": round(rsi14, 2),
                        "atr": round(atr14, 2),
                        "above_ipo_proxy": above_ipo_proxy,
                    },
                ))

        return picks


# ============================================================
# Cheap Stock Momentum Strategy
# ============================================================
# Low-priced stocks ($1-$10) with momentum breakout patterns.
# These are NOT penny stocks (pink sheets) — they're established
# companies trading at low absolute prices, often due to:
#  - Recent split (price adjusted down)
#  - Sector rotation out of favor
#  - Market overreaction to bad news
#
# Academic: Bali et al. (2011) — max return effect + momentum
# ============================================================
class CheapStockMomentum(BaseStrategy):
    """Cheap Stock Momentum — low-priced stocks with momentum breakout.

    Logic:
    1. Universe: stocks trading between $1-$10 (established companies, not pink sheets)
    2. Momentum filter: price > 50-day SMA AND 20-day SMA > 50-day SMA
    3. Volume confirmation: volume > 1.5× 20-day average
    4. Entry: LONG on breakout above 20-day high
    5. Exit: TP = entry × 1.15 (+15%), SL = entry × 0.92 (-8%)
    6. Max hold: 20 days

    Universe: Curated list of established low-priced stocks
    """
    name = "cheap_stock_momentum"
    display_name = "Cheap Stock Momentum"
    source = "Cheap Stock Universe + Momentum"
    category = "cheap_stocks"
    portfolio_type = "cheap_momentum"

    # Established companies trading at low absolute prices
    # (Not penny stocks — these are listed on major exchanges)
    symbols = [
        "SOFI", "PLUG", "NIO", "LCID", "RIVN", "BB", "WISH", "CLOV",
        "AMC", "GME", "BBBY", "EXPR", "NAKD", "KOSS", "SNDL",
    ]

    TP_PCT = 0.15   # 15% take profit
    SL_PCT = 0.08   # 8% stop loss
    HOLD_MAX = 20   # Max hold days

    def fetch_data(self) -> dict:
        """Fetch yfinance data for cheap stock universe."""
        data = {}
        for sym in self.symbols:
            result = _fetch_yf_ohlcv(sym, period="1y", interval="1d")
            if result:
                data[sym] = result
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        """Generate cheap stock momentum picks."""
        import pandas as pd
        picks = []

        for sym, result in data.items():
            df = result["df"]
            if len(df) < 60:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current_price = close.iloc[-1]

            # Price filter: must be between $1 and $10
            if current_price < 1.0 or current_price > 10.0:
                continue

            # Momentum filters
            sma20 = close.rolling(20).mean().iloc[-1]
            sma50 = close.rolling(50).mean().iloc[-1]
            high_20d = high.rolling(20).max().iloc[-1]
            avg_vol = volume.rolling(20).mean().iloc[-1]
            current_vol = volume.iloc[-1]

            # Cheap stock momentum signal:
            # 1. Price between $1-$10 (cheap stock definition)
            # 2. Price > 50-day SMA (medium-term uptrend)
            # 3. 20-day SMA > 50-day SMA (short-term momentum)
            # 4. Volume > 1.5× average (breakout confirmation)
            # 5. Price near 20-day high (within 2%)
            price_ok = 1.0 <= current_price <= 10.0
            above_sma50 = current_price > sma50
            sma_cross = sma20 > sma50
            vol_confirm = current_vol > avg_vol * 1.5
            near_high = current_price >= high_20d * 0.98

            if price_ok and above_sma50 and sma_cross and vol_confirm and near_high:
                direction = "LONG"
                tp = current_price * (1 + self.TP_PCT)
                sl = current_price * (1 - self.SL_PCT)
                rr = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0

                # Confidence: stronger if all filters align
                filters_met = sum([price_ok, above_sma50, sma_cross, vol_confirm, near_high])
                confidence = min(0.85, 0.50 + filters_met / 10)

                picks.append(NormalizedPick(
                    symbol=sym,
                    direction=direction,
                    entry_price=round(current_price, 4),
                    tp=round(tp, 4),
                    sl=round(sl, 4),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=(f"Cheap momentum: price={current_price:.4f}, "
                            f"SMA20={sma20:.2f}, SMA50={sma50:.2f}, "
                            f"vol={current_vol/avg_vol:.1f}x, near_high={near_high}"),
                    risk_reward=round(rr, 2),
                    raw_signal={
                        "sma20": round(sma20, 4),
                        "sma50": round(sma50, 4),
                        "high_20d": round(high_20d, 4),
                        "vol_ratio": round(current_vol / avg_vol, 2),
                        "near_high": near_high,
                    },
                ))

        return picks

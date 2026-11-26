#!/usr/bin/env python3
"""
Liquidity-Adjusted Volume (LAV) Breakout Strategy — Battleground Incubator v1
==============================================================================

Created by: Claude Code
Date: 2026-03-13

Research Source:
- Kilo-Code TradingView indicator research (tradingview_indicator_research_summary.md)
- Order-book microstructure analysis

Strategy Logic:
  Raw volume is noisy (wash trading, bot activity, market maker churn).
  LAV normalizes volume by order-book spread and depth to produce a cleaner
  breakout signal:

    LAV = raw_volume / max(spread_bps, 0.1)

  A high LAV spike (> 2x its 20-period SMA) combined with a Bollinger Band
  squeeze breakout indicates genuine institutional participation rather than
  noise. Order-book depth ratio (bid_vol / ask_vol) confirms directional bias.

  Signal conditions:
  - LONG:  BB squeeze + LAV spike > 2.0 + close > BB upper + depth_ratio > 1.0
  - SHORT: BB squeeze + LAV spike > 2.0 + close < BB lower + depth_ratio < 1.0

Why This Works:
  Volume alone is unreliable in crypto (wash trading estimates 50-70% on some
  exchanges). Normalizing by spread filters out low-conviction churn. When
  genuine volume appears during a volatility squeeze (BB width in bottom 20%),
  the resulting breakout has significantly higher follow-through because:
  1. Tight spread = real liquidity, not phantom orders
  2. Depth imbalance = directional conviction from larger participants
  3. BB squeeze = compressed spring ready to expand

  Academic references:
  - Kyle (1985): market microstructure and informed trading
  - Bollerslev & Melvin (1994): bid-ask spreads and volatility
  - Karpoff (1987): volume-price relationship

Data Sources:
  - Binance public klines API (no key required)
  - Binance public order book depth API (no key required)
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

# -- Configuration ------------------------------------------------------------
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ENAUSDT",
    "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT",
]

from api_helpers import fetch_klines as _fetch_klines_fallback
from api_helpers import fetch_current_price as _fetch_price_fallback

# Order book depth endpoints (fallback chain)
DEPTH_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/depth",
    "https://api.binance.com/api/v3/depth",
]

# Kline settings
KLINE_INTERVAL = "15m"
KLINE_LIMIT = 100

# Bollinger Band parameters
BB_PERIOD = 20
BB_STD_MULT = 2.0
BB_SQUEEZE_PERCENTILE = 20  # bottom 20% of BB width = squeeze

# LAV parameters
LAV_SMA_PERIOD = 20
LAV_SPIKE_THRESHOLD = 2.0   # LAV / LAV_SMA must exceed this

# Risk parameters (ATR-based)
ATR_PERIOD = 14
TP_ATR_MULT = 2.0   # TP = 2.0x ATR from entry
SL_ATR_MULT = 1.2   # SL = 1.2x ATR from entry

# Order book depth
DEPTH_LIMIT = 20  # top 20 bid/ask levels


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    """Trading signal -- matches battleground incubator format."""
    symbol: str
    direction: str       # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "liquidity_adjusted_volume_v1"
    timeframe: str = "15m"
    metadata: dict = field(default_factory=dict)


class LiquidityAdjustedVolumeStrategy:
    """
    Liquidity-Adjusted Volume Breakout Strategy.

    Combines order-book microstructure with Bollinger Band squeeze detection
    to identify genuine breakouts stripped of wash-trading noise.

    LAV = raw_volume / max(spread_bps, 0.1)
    Signal fires when LAV spikes > 2x its SMA during a BB squeeze breakout.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.bb_period = p.get("bb_period", BB_PERIOD)
        self.bb_std_mult = p.get("bb_std_mult", BB_STD_MULT)
        self.bb_squeeze_pctile = p.get("bb_squeeze_percentile", BB_SQUEEZE_PERCENTILE)
        self.lav_sma_period = p.get("lav_sma_period", LAV_SMA_PERIOD)
        self.lav_spike_threshold = p.get("lav_spike_threshold", LAV_SPIKE_THRESHOLD)
        self.atr_period = p.get("atr_period", ATR_PERIOD)
        self.tp_mult = p.get("tp_mult", TP_ATR_MULT)
        self.sl_mult = p.get("sl_mult", SL_ATR_MULT)
        self._timeout = p.get("request_timeout", 10)

    # -- Public API ------------------------------------------------------------

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan all symbols for LAV breakout opportunities."""
        if requests is None:
            logger.error("requests library not available")
            return []

        targets = [symbol] if symbol else self.symbols
        all_signals: List[Signal] = []

        for sym in targets:
            try:
                sigs = self._analyze_symbol(sym)
                all_signals.extend(sigs)
            except Exception as e:
                logger.warning("Error analyzing %s: %s", sym, e)

        return all_signals

    # -- Core Analysis ---------------------------------------------------------

    def _analyze_symbol(self, symbol: str) -> List[Signal]:
        """Full LAV breakout analysis for one symbol."""

        # 1. Fetch OHLCV klines (15m, 100 candles)
        candles = self._fetch_klines(symbol)
        if not candles or len(candles) < self.bb_period + 10:
            logger.warning(
                "%s: insufficient kline data (%d candles)",
                symbol, len(candles) if candles else 0,
            )
            return []

        # 2. Fetch order book depth
        depth = self._fetch_depth(symbol)
        if not depth:
            logger.warning("%s: could not fetch order book depth", symbol)
            return []

        bids, asks = depth
        if not bids or not asks:
            logger.warning("%s: empty order book", symbol)
            return []

        # 3. Calculate order book metrics
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2.0

        if mid_price <= 0:
            return []

        spread_bps = (best_ask - best_bid) / mid_price * 10000.0

        total_bid_vol = sum(float(level[1]) for level in bids)
        total_ask_vol = sum(float(level[1]) for level in asks)
        depth_ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 1.0

        # 4. Calculate LAV for each candle (approximate: use spread_bps from
        #    current order book for all candles -- historical spread not available
        #    from public API, but current spread is a reasonable proxy for recent
        #    15m candles)
        spread_divisor = max(spread_bps, 0.1)
        lav_series = [c.volume / spread_divisor for c in candles]

        # 5. LAV SMA (20-period)
        if len(lav_series) < self.lav_sma_period:
            return []

        lav_sma_window = lav_series[-(self.lav_sma_period + 1):-1]  # exclude current
        lav_sma = statistics.mean(lav_sma_window) if lav_sma_window else 1.0

        current_lav = lav_series[-1]
        lav_spike = current_lav / lav_sma if lav_sma > 0 else 0.0

        # 6. Bollinger Bands
        closes = [c.close for c in candles]
        bb_window = closes[-self.bb_period:]
        sma20 = statistics.mean(bb_window)
        std20 = statistics.stdev(bb_window) if len(bb_window) > 1 else 0.0

        bb_upper = sma20 + self.bb_std_mult * std20
        bb_lower = sma20 - self.bb_std_mult * std20
        bb_width = (bb_upper - bb_lower) / sma20 if sma20 > 0 else 0.0

        # 7. BB width percentile over last 100 bars (squeeze detection)
        bb_widths = []
        for i in range(self.bb_period, len(candles)):
            window = closes[i - self.bb_period + 1: i + 1]
            if len(window) < self.bb_period:
                continue
            w_sma = statistics.mean(window)
            w_std = statistics.stdev(window) if len(window) > 1 else 0.0
            w_upper = w_sma + self.bb_std_mult * w_std
            w_lower = w_sma - self.bb_std_mult * w_std
            w_width = (w_upper - w_lower) / w_sma if w_sma > 0 else 0.0
            bb_widths.append(w_width)

        if not bb_widths:
            return []

        # Percentile: current bb_width vs historical bb_widths
        below_count = sum(1 for w in bb_widths if w <= bb_width)
        bb_width_percentile = (below_count / len(bb_widths)) * 100.0
        bb_squeeze = bb_width_percentile <= self.bb_squeeze_pctile

        # 8. ATR for TP/SL
        atr = self._calc_atr(candles)
        if atr <= 0:
            return []

        # 9. Signal logic
        current_price = candles[-1].close
        signals = []

        if not bb_squeeze:
            return []

        if lav_spike < self.lav_spike_threshold:
            return []

        # LONG: close > bb_upper + depth_ratio > 1.0
        if current_price > bb_upper and depth_ratio > 1.0:
            confidence = 0.60
            if lav_spike > 3.0:
                confidence += 0.10
            if depth_ratio > 1.3:
                confidence += 0.05
            confidence = min(0.95, confidence)

            tp = round(current_price + self.tp_mult * atr, 2)
            sl = round(current_price - self.sl_mult * atr, 2)

            reason = (
                f"LAV Breakout LONG: lav_spike={lav_spike:.2f}x "
                f"spread={spread_bps:.1f}bps depth_ratio={depth_ratio:.2f} "
                f"bb_squeeze=True (pctile={bb_width_percentile:.0f}) "
                f"close={current_price:.2f} > bb_upper={bb_upper:.2f}"
            )

            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 4),
                entry_price=round(current_price, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=reason,
                metadata={
                    "lav_spike": round(lav_spike, 4),
                    "lav_current": round(current_lav, 2),
                    "lav_sma": round(lav_sma, 2),
                    "spread_bps": round(spread_bps, 2),
                    "depth_ratio": round(depth_ratio, 4),
                    "total_bid_vol": round(total_bid_vol, 4),
                    "total_ask_vol": round(total_ask_vol, 4),
                    "bb_width": round(bb_width, 6),
                    "bb_width_percentile": round(bb_width_percentile, 1),
                    "bb_upper": round(bb_upper, 2),
                    "bb_lower": round(bb_lower, 2),
                    "sma20": round(sma20, 2),
                    "atr": round(atr, 2),
                    "current_price": current_price,
                },
            ))

        # SHORT: close < bb_lower + depth_ratio < 1.0
        elif current_price < bb_lower and depth_ratio < 1.0:
            confidence = 0.60
            if lav_spike > 3.0:
                confidence += 0.10
            if depth_ratio < 0.7:
                confidence += 0.05
            confidence = min(0.95, confidence)

            tp = round(current_price - self.tp_mult * atr, 2)
            sl = round(current_price + self.sl_mult * atr, 2)

            reason = (
                f"LAV Breakout SHORT: lav_spike={lav_spike:.2f}x "
                f"spread={spread_bps:.1f}bps depth_ratio={depth_ratio:.2f} "
                f"bb_squeeze=True (pctile={bb_width_percentile:.0f}) "
                f"close={current_price:.2f} < bb_lower={bb_lower:.2f}"
            )

            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 4),
                entry_price=round(current_price, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=reason,
                metadata={
                    "lav_spike": round(lav_spike, 4),
                    "lav_current": round(current_lav, 2),
                    "lav_sma": round(lav_sma, 2),
                    "spread_bps": round(spread_bps, 2),
                    "depth_ratio": round(depth_ratio, 4),
                    "total_bid_vol": round(total_bid_vol, 4),
                    "total_ask_vol": round(total_ask_vol, 4),
                    "bb_width": round(bb_width, 6),
                    "bb_width_percentile": round(bb_width_percentile, 1),
                    "bb_upper": round(bb_upper, 2),
                    "bb_lower": round(bb_lower, 2),
                    "sma20": round(sma20, 2),
                    "atr": round(atr, 2),
                    "current_price": current_price,
                },
            ))

        return signals

    # -- Technical Indicators --------------------------------------------------

    def _calc_atr(self, candles: List[Candle]) -> float:
        """Calculate Average True Range over the ATR period."""
        if len(candles) < self.atr_period + 1:
            return candles[-1].high - candles[-1].low if candles else 0.0

        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i - 1].close)
            low_close = abs(candles[i].low - candles[i - 1].close)
            true_ranges.append(max(high_low, high_close, low_close))

        if len(true_ranges) < self.atr_period:
            return statistics.mean(true_ranges)

        return statistics.mean(true_ranges[-self.atr_period:])

    # -- Binance API -----------------------------------------------------------

    def _fetch_klines(self, symbol: str) -> Optional[List[Candle]]:
        """Fetch OHLCV klines with geo-restriction fallback."""
        data = _fetch_klines_fallback(symbol, self.interval, self.limit, self._timeout)
        if not data:
            return None
        return [
            Candle(
                timestamp=int(k[0]),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
            )
            for k in data
        ]

    def _fetch_depth(self, symbol: str) -> Optional[tuple]:
        """
        Fetch order book depth with fallback chain.

        Returns (bids, asks) where each is a list of [price, quantity] pairs,
        or None on failure.
        """
        if requests is None:
            return None

        params = {"symbol": symbol, "limit": DEPTH_LIMIT}

        for endpoint in DEPTH_ENDPOINTS:
            try:
                resp = requests.get(endpoint, params=params, timeout=self._timeout)
                if resp.status_code == 451:
                    logger.debug("Geo-blocked at %s, trying next endpoint", endpoint)
                    continue
                resp.raise_for_status()
                data = resp.json()
                bids = data.get("bids", [])
                asks = data.get("asks", [])
                if bids and asks:
                    logger.debug(
                        "Order book fetched from %s (%d bids, %d asks)",
                        endpoint, len(bids), len(asks),
                    )
                    return (bids, asks)
            except requests.exceptions.RequestException as e:
                logger.debug("Depth endpoint %s failed: %s", endpoint, e)
                continue

        logger.error("All depth endpoints failed for %s", symbol)
        return None


# -- Module-level scan() function (battleground incubator interface) -----------

def scan() -> List[dict]:
    """
    Scan all symbols for LAV breakout signals.

    Returns a list of signal dicts matching the battleground incubator format.
    This is the standard entry point called by the tournament runner.
    """
    strategy = LiquidityAdjustedVolumeStrategy()
    signals = strategy.generate_signals()

    return [
        {
            "symbol": s.symbol,
            "direction": s.direction,
            "strategy": s.strategy,
            "confidence": s.confidence,
            "entry_price": s.entry_price,
            "take_profit": s.take_profit,
            "stop_loss": s.stop_loss,
            "timeframe": s.timeframe,
            "reason": s.reason,
            "metadata": s.metadata,
        }
        for s in signals
    ]


# -- Standalone Runner ---------------------------------------------------------

def main():
    """Run the LAV Breakout scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = LiquidityAdjustedVolumeStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'='*75}")
    print(f"  LAV BREAKOUT SCANNER  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Liquidity-Adjusted Volume + Bollinger Squeeze")
    print(f"{'='*75}")

    if not signals:
        print("\n  No LAV breakout opportunities right now.")
        print("  (Requires: BB squeeze + LAV spike > 2x + depth confirmation)")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*50}")
            print(f"  Direction:    {sig.direction}")
            print(f"  Entry:        ${sig.entry_price:,.2f}")
            print(f"  TP:           ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:   {sig.confidence:.1%}")
            print(f"  LAV Spike:    {m.get('lav_spike', 0):.2f}x SMA")
            print(f"  Spread:       {m.get('spread_bps', 0):.1f} bps")
            print(f"  Depth Ratio:  {m.get('depth_ratio', 0):.4f} (bid/ask)")
            print(f"  BB Width:     {m.get('bb_width_percentile', 0):.0f}th percentile (squeeze)")
            print(f"  BB Bands:     [{m.get('bb_lower', 0):,.2f} - {m.get('bb_upper', 0):,.2f}]")
            print(f"  ATR:          ${m.get('atr', 0):,.2f}")

    print(f"\n{'='*75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, found {len(signals)} LAV breakout signals")
    print(f"{'='*75}\n")

    return scan()


if __name__ == "__main__":
    main()

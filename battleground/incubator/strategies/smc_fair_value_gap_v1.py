#!/usr/bin/env python3
"""
Smart Money Concepts (SMC) — Fair Value Gap (FVG) Detector + Liquidity Sweep
=============================================================================

Created by: google_antigravity
Date: 2026-03-13

Research Source:
- Blueprint_So9 (TradingView Leap top-10 competitor, 70K+ participants)
- LuxAlgo SMC indicator concepts (order blocks, FVGs, BOS/CHoCH)
- 2025-2026 institutional trading framework research

Strategy Logic:
1. Fetches OHLCV klines from Binance public API (no key needed)
2. Detects Fair Value Gaps (FVGs) — 3-candle price inefficiencies
3. Detects Liquidity Sweeps — price takes out highs/lows then reverses
4. Identifies Order Blocks — last opposing candle before impulsive move
5. Combines FVG + sweep + order block for high-probability entries

FVG Definition (Bullish):
   candle[n-2].high < candle[n].low  → gap between candle 1 top and candle 3 bottom
   The middle candle is the "displacement" (large body, impulsive move)

FVG Definition (Bearish):
   candle[n-2].low > candle[n].high  → gap between candle 1 bottom and candle 3 top

Entry Logic:
   - LONG when price retraces INTO a bullish FVG zone + volume confirms
   - SHORT when price retraces INTO a bearish FVG zone + volume confirms
   - Confluence: Liquidity sweep occurred just before FVG formation = +20% confidence
   - Order block alignment adds +10% confidence

Why This Works:
   Institutions leave FVGs during aggressive accumulation/distribution.
   Their algorithms are programmed to return and fill these gaps.
   Blueprint_So9's TradingView Leap success was built on this framework.
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ENAUSDT", "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT"]

from api_helpers import fetch_klines as _fetch_klines_fallback

# Analysis parameters
KLINE_INTERVAL = "15m"      # 15-minute candles for SMC analysis
KLINE_LIMIT = 100           # last 100 candles
FVG_MIN_SIZE_ATR_MULT = 0.5 # FVG must be at least 0.5x ATR to be significant
ATR_PERIOD = 14
LOOKBACK_SWINGS = 20        # bars to look back for swing highs/lows
SWEEP_WICK_THRESHOLD = 0.6  # wick must be >60% of candle range for sweep

# Risk parameters
TP_MULT = 2.0   # TP = 2x FVG height from entry
SL_MULT = 0.5   # SL = 0.5x FVG height below/above FVG zone


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def range_size(self) -> float:
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class FairValueGap:
    """A detected Fair Value Gap."""
    gap_type: str        # "BULLISH" or "BEARISH"
    top: float           # top of the gap zone
    bottom: float        # bottom of the gap zone
    size: float          # gap size in price
    displacement: float  # body size of the displacement candle
    candle_index: int    # index of the middle (displacement) candle
    timestamp: int       # timestamp of the FVG
    volume_ratio: float  # displacement volume / avg volume
    is_filled: bool = False  # has price already returned to fill it?


@dataclass
class LiquiditySweep:
    """A detected liquidity sweep."""
    sweep_type: str      # "BULLISH_SWEEP" (sweep low then reverse up) or "BEARISH_SWEEP"
    sweep_level: float   # the level that was swept
    reversal_candle: int # index of the reversal candle
    timestamp: int


@dataclass
class Signal:
    """Trading signal — matches battleground format."""
    symbol: str
    direction: str       # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "smc_fair_value_gap_v1"
    timeframe: str = "15m"
    metadata: dict = field(default_factory=dict)


class SMCFairValueGapStrategy:
    """
    Smart Money Concepts strategy combining:
    1. Fair Value Gap detection
    2. Liquidity sweep identification
    3. Order block alignment
    4. Volume confirmation
    
    Based on Blueprint_So9's TradingView Leap methodology and
    LuxAlgo SMC indicator patterns.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.interval = p.get("interval", KLINE_INTERVAL)
        self.limit = p.get("kline_limit", KLINE_LIMIT)
        self.fvg_min_atr = p.get("fvg_min_atr_mult", FVG_MIN_SIZE_ATR_MULT)
        self.atr_period = p.get("atr_period", ATR_PERIOD)
        self.lookback = p.get("lookback_swings", LOOKBACK_SWINGS)
        self.tp_mult = p.get("tp_mult", TP_MULT)
        self.sl_mult = p.get("sl_mult", SL_MULT)
        self._timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan all symbols for SMC Fair Value Gap opportunities."""
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

    # ── Core Analysis ────────────────────────────────────────────────

    def _analyze_symbol(self, symbol: str) -> List[Signal]:
        """Full SMC analysis for one symbol."""
        
        # 1. Fetch OHLCV data
        candles = self._fetch_klines(symbol)
        if not candles or len(candles) < 30:
            logger.warning("%s: insufficient kline data (%d candles)", 
                         symbol, len(candles) if candles else 0)
            return []

        # 2. Calculate ATR for FVG significance filtering
        atr = self._calc_atr(candles)
        if atr == 0:
            return []

        # 3. Detect Fair Value Gaps
        fvgs = self._detect_fvgs(candles, atr)
        
        # 4. Detect Liquidity Sweeps
        sweeps = self._detect_sweeps(candles)
        
        # 5. Check which FVGs are still unfilled and near current price
        current_price = candles[-1].close
        signals = []
        
        for fvg in fvgs:
            if fvg.is_filled:
                continue
                
            # Check if current price is approaching or in the FVG zone
            gap_mid = (fvg.top + fvg.bottom) / 2
            distance_pct = abs(current_price - gap_mid) / current_price * 100
            
            # Only signal on FVGs within 1% of current price
            if distance_pct > 1.0:
                continue

            # 6. Build confidence score
            confidence = 0.40  # base

            # Volume confirmation: displacement candle had above-average volume
            if fvg.volume_ratio > 1.5:
                confidence += 0.15
            elif fvg.volume_ratio > 1.2:
                confidence += 0.08

            # FVG size relative to ATR
            size_ratio = fvg.size / atr
            if size_ratio > 1.5:
                confidence += 0.10
            elif size_ratio > 1.0:
                confidence += 0.05

            # Liquidity sweep confluence: did a sweep happen before the FVG?
            sweep_boost = self._check_sweep_confluence(fvg, sweeps)
            if sweep_boost:
                confidence += 0.20
                
            # Order block alignment
            ob_boost = self._check_order_block(candles, fvg)
            if ob_boost:
                confidence += 0.10

            confidence = max(0.30, min(0.95, confidence))

            # 7. Set entry, TP, SL
            if fvg.gap_type == "BULLISH":
                entry = fvg.top  # enter at top of gap (conservative)
                tp = round(entry + fvg.size * self.tp_mult, 2)
                sl = round(fvg.bottom - fvg.size * self.sl_mult, 2)
                direction = "BUY"
            else:
                entry = fvg.bottom  # enter at bottom of gap (conservative)
                tp = round(entry - fvg.size * self.tp_mult, 2)
                sl = round(fvg.top + fvg.size * self.sl_mult, 2)
                direction = "SELL"

            reason = (
                f"SMC {fvg.gap_type} FVG: zone=[{fvg.bottom:.2f}-{fvg.top:.2f}] "
                f"size={fvg.size:.2f} ({size_ratio:.1f}x ATR) "
                f"vol_ratio={fvg.volume_ratio:.1f}x "
                f"sweep={'YES' if sweep_boost else 'NO'} "
                f"ob={'YES' if ob_boost else 'NO'}"
            )

            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 4),
                entry_price=round(entry, 2),
                take_profit=tp,
                stop_loss=sl,
                reason=reason,
                metadata={
                    "fvg_type": fvg.gap_type,
                    "fvg_top": fvg.top,
                    "fvg_bottom": fvg.bottom,
                    "fvg_size": fvg.size,
                    "fvg_size_atr_ratio": round(size_ratio, 2),
                    "volume_ratio": fvg.volume_ratio,
                    "sweep_confluence": sweep_boost,
                    "order_block": ob_boost,
                    "distance_pct": round(distance_pct, 4),
                    "atr": round(atr, 2),
                    "current_price": current_price,
                },
            ))

        return signals

    # ── FVG Detection ────────────────────────────────────────────────

    def _detect_fvgs(self, candles: List[Candle], atr: float) -> List[FairValueGap]:
        """
        Detect Fair Value Gaps in the candle data.
        
        Bullish FVG: candle[i-2].high < candle[i].low
          → gap between top of candle 1 and bottom of candle 3
          → middle candle is large bullish displacement
          
        Bearish FVG: candle[i-2].low > candle[i].high
          → gap between bottom of candle 1 and top of candle 3
          → middle candle is large bearish displacement
        """
        fvgs = []
        avg_volume = statistics.mean(c.volume for c in candles) if candles else 1
        
        for i in range(2, len(candles)):
            c1 = candles[i - 2]  # first candle
            c2 = candles[i - 1]  # displacement candle (middle)
            c3 = candles[i]      # third candle
            
            # Bullish FVG: gap between c1.high and c3.low
            if c1.high < c3.low:
                gap_size = c3.low - c1.high
                if gap_size >= atr * self.fvg_min_atr:
                    vol_ratio = c2.volume / avg_volume if avg_volume > 0 else 1
                    
                    # Check if the gap has been filled by subsequent candles
                    is_filled = any(
                        candles[j].low <= c1.high
                        for j in range(i + 1, len(candles))
                    ) if i + 1 < len(candles) else False
                    
                    fvgs.append(FairValueGap(
                        gap_type="BULLISH",
                        top=c3.low,
                        bottom=c1.high,
                        size=gap_size,
                        displacement=c2.body_size,
                        candle_index=i - 1,
                        timestamp=c2.timestamp,
                        volume_ratio=round(vol_ratio, 2),
                        is_filled=is_filled,
                    ))
            
            # Bearish FVG: gap between c3.high and c1.low
            if c1.low > c3.high:
                gap_size = c1.low - c3.high
                if gap_size >= atr * self.fvg_min_atr:
                    vol_ratio = c2.volume / avg_volume if avg_volume > 0 else 1
                    
                    is_filled = any(
                        candles[j].high >= c1.low
                        for j in range(i + 1, len(candles))
                    ) if i + 1 < len(candles) else False
                    
                    fvgs.append(FairValueGap(
                        gap_type="BEARISH",
                        top=c1.low,
                        bottom=c3.high,
                        size=gap_size,
                        displacement=c2.body_size,
                        candle_index=i - 1,
                        timestamp=c2.timestamp,
                        volume_ratio=round(vol_ratio, 2),
                        is_filled=is_filled,
                    ))
        
        return fvgs

    # ── Liquidity Sweep Detection ────────────────────────────────────

    def _detect_sweeps(self, candles: List[Candle]) -> List[LiquiditySweep]:
        """
        Detect liquidity sweeps: price briefly breaks a swing high/low
        then reverses, indicating stop-hunt by institutions.
        
        Bullish sweep: price breaks below recent swing low then closes above it
        Bearish sweep: price breaks above recent swing high then closes below it
        """
        sweeps = []
        
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(candles) - 2):
            # Simple swing high: higher high than neighbors
            if (candles[i].high > candles[i-1].high and 
                candles[i].high > candles[i-2].high and
                candles[i].high > candles[i+1].high and
                candles[i].high > candles[i+2].high):
                swing_highs.append((i, candles[i].high))
            
            # Simple swing low: lower low than neighbors
            if (candles[i].low < candles[i-1].low and 
                candles[i].low < candles[i-2].low and
                candles[i].low < candles[i+1].low and
                candles[i].low < candles[i+2].low):
                swing_lows.append((i, candles[i].low))
        
        # Check recent candles for sweeps of these levels
        for i in range(max(5, len(candles) - 20), len(candles)):
            c = candles[i]
            
            # Bullish sweep: wick below swing low, close above
            for (idx, level) in swing_lows:
                if idx >= i:
                    continue
                if c.low < level and c.close > level:
                    # Verify it's a wick-heavy candle (long lower wick)
                    if c.range_size > 0:
                        wick_ratio = c.lower_wick / c.range_size
                        if wick_ratio > SWEEP_WICK_THRESHOLD:
                            sweeps.append(LiquiditySweep(
                                sweep_type="BULLISH_SWEEP",
                                sweep_level=level,
                                reversal_candle=i,
                                timestamp=c.timestamp,
                            ))
            
            # Bearish sweep: wick above swing high, close below
            for (idx, level) in swing_highs:
                if idx >= i:
                    continue
                if c.high > level and c.close < level:
                    if c.range_size > 0:
                        wick_ratio = c.upper_wick / c.range_size
                        if wick_ratio > SWEEP_WICK_THRESHOLD:
                            sweeps.append(LiquiditySweep(
                                sweep_type="BEARISH_SWEEP",
                                sweep_level=level,
                                reversal_candle=i,
                                timestamp=c.timestamp,
                            ))
        
        return sweeps

    # ── Confluence Checks ────────────────────────────────────────────

    def _check_sweep_confluence(self, fvg: FairValueGap, sweeps: List[LiquiditySweep]) -> bool:
        """Check if a liquidity sweep occurred within 5 candles before the FVG."""
        for sweep in sweeps:
            candle_distance = fvg.candle_index - sweep.reversal_candle
            if 0 <= candle_distance <= 5:
                # Bullish sweep before bullish FVG = strong confluence
                if sweep.sweep_type == "BULLISH_SWEEP" and fvg.gap_type == "BULLISH":
                    return True
                # Bearish sweep before bearish FVG = strong confluence
                if sweep.sweep_type == "BEARISH_SWEEP" and fvg.gap_type == "BEARISH":
                    return True
        return False

    def _check_order_block(self, candles: List[Candle], fvg: FairValueGap) -> bool:
        """
        Check if an order block aligns with the FVG.
        Order block = last opposing candle before the impulsive displacement.
        
        For bullish FVG: look for last bearish candle before the displacement
        For bearish FVG: look for last bullish candle before the displacement
        """
        idx = fvg.candle_index
        if idx < 3:
            return False
        
        if fvg.gap_type == "BULLISH":
            # Look back for last bearish candle before the bullish displacement
            for j in range(idx - 1, max(0, idx - 5), -1):
                if not candles[j].is_bullish:
                    # Order block zone overlaps with FVG zone
                    ob_low = candles[j].low
                    ob_high = candles[j].high
                    if ob_low <= fvg.top and ob_high >= fvg.bottom:
                        return True
        else:
            # Look back for last bullish candle before the bearish displacement
            for j in range(idx - 1, max(0, idx - 5), -1):
                if candles[j].is_bullish:
                    ob_low = candles[j].low
                    ob_high = candles[j].high
                    if ob_low <= fvg.top and ob_high >= fvg.bottom:
                        return True
        
        return False

    # ── Technical Indicators ─────────────────────────────────────────

    def _calc_atr(self, candles: List[Candle]) -> float:
        """Calculate Average True Range."""
        if len(candles) < self.atr_period + 1:
            return candles[-1].range_size if candles else 0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_close = abs(candles[i].high - candles[i-1].close)
            low_close = abs(candles[i].low - candles[i-1].close)
            true_ranges.append(max(high_low, high_close, low_close))
        
        if len(true_ranges) < self.atr_period:
            return statistics.mean(true_ranges)
        
        return statistics.mean(true_ranges[-self.atr_period:])

    # ── Binance API ──────────────────────────────────────────────────

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


# ── Standalone Runner ────────────────────────────────────────────────

def main():
    """Run the SMC FVG scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = SMCFairValueGapStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'='*75}")
    print(f"  SMC FAIR VALUE GAP SCANNER  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Based on: Blueprint_So9 TradingView Leap + LuxAlgo SMC framework")
    print(f"{'='*75}")

    if not signals:
        print("\n  No FVG opportunities near current price.")
        print("  (Requires unfilled FVG within 1% of current price)")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*50}")
            print(f"  Direction:   {sig.direction}")
            print(f"  FVG Zone:    [{m['fvg_bottom']:.2f} — {m['fvg_top']:.2f}]")
            print(f"  FVG Size:    {m['fvg_size']:.2f} ({m['fvg_size_atr_ratio']:.1f}x ATR)")
            print(f"  Entry:       ${sig.entry_price:,.2f}")
            print(f"  TP:          ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:  {sig.confidence:.1%}")
            print(f"  Vol Ratio:   {m['volume_ratio']:.1f}x average")
            print(f"  Sweep:       {'✓ YES — liquidity sweep confluence' if m['sweep_confluence'] else '✗ No sweep detected'}")
            print(f"  Order Block: {'✓ YES — OB alignment' if m['order_block'] else '✗ No OB alignment'}")
            print(f"  Distance:    {m['distance_pct']:.4f}% from current")

    print(f"\n{'='*75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, found {len(signals)} FVG opportunities")
    print(f"{'='*75}\n")

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


if __name__ == "__main__":
    main()

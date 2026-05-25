#!/usr/bin/env python3
"""
Funding Rate Carry / Basis Arbitrage Strategy
==============================================

Created by: claude_code
Date: 2026-03-13

Strategy Logic:
- Fetches live funding rates from Binance perpetual futures (public API, no key needed)
- LONG spot + SHORT perp when funding_rate > 0.03% (longs pay shorts = carry income)
- SHORT spot + LONG perp when funding_rate < -0.03% (shorts pay longs = carry income)
- Uses 30-period funding rate history to compute drift (current vs SMA)
- Only signals when abs(funding_drift) > 0.01% to filter noise

Annualized Yield Calculation:
    funding_rate * 3 * 365 * 100   (funding settles every 8h = 3x daily)

Unique Value Proposition:
Market-neutral carry trade. Unlike directional strategies, this profits from the
funding rate differential regardless of price direction. The position is hedged
(long spot + short perp, or vice versa), so PnL comes from funding payments,
not from price movement. Historically yields 15-60% APR on major pairs during
trending markets.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ENAUSDT", "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT", "NEARUSDT"]

# Funding rate thresholds (in decimal, e.g. 0.0003 = 0.03%)
FUNDING_ENTRY_THRESHOLD = 0.0003   # |rate| must exceed this to signal
DRIFT_THRESHOLD = 0.0001           # |drift| must exceed this (0.01%)
FUNDING_HISTORY_LIMIT = 30         # periods for SMA

from api_helpers import fetch_funding_rate as _fetch_funding_fallback
from api_helpers import fetch_current_price as _fetch_price_fallback

# Risk parameters for the hedged position
# Since this is market-neutral, TP/SL are based on yield thresholds
# not price movement. We use tight SL because if funding flips, exit.
TP_FUNDING_PERIODS = 24   # expect to hold ~24 funding periods (8 days)
SL_PRICE_PCT = 0.005      # 0.5% adverse move triggers re-evaluation


@dataclass
class Signal:
    """A trading signal - matches the standard battleground format."""
    symbol: str
    direction: str       # "BUY" or "SELL"
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "funding_rate_carry_v1"
    timeframe: str = "8h"
    metadata: dict = field(default_factory=dict)


class FundingRateCarryStrategy:
    """
    Market-neutral funding rate carry / basis arbitrage.

    Scans Binance perpetual futures for funding rate opportunities:
    - When funding is significantly positive: LONG spot + SHORT perp
      (you collect funding payments from longs who pay shorts)
    - When funding is significantly negative: SHORT spot + LONG perp
      (you collect funding payments from shorts who pay longs)

    The 30-period SMA of funding rate detects "drift" - sustained
    funding rate regimes that are more likely to persist.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.entry_threshold = p.get("entry_threshold", FUNDING_ENTRY_THRESHOLD)
        self.drift_threshold = p.get("drift_threshold", DRIFT_THRESHOLD)
        self.history_limit = p.get("history_limit", FUNDING_HISTORY_LIMIT)
        self.symbols = p.get("symbols", SYMBOLS)
        self.tp_periods = p.get("tp_funding_periods", TP_FUNDING_PERIODS)
        self.sl_price_pct = p.get("sl_price_pct", SL_PRICE_PCT)
        self._request_timeout = p.get("request_timeout", 10)

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """
        Scan all configured symbols for funding rate carry opportunities.

        Parameters
        ----------
        data : ignored (this strategy fetches its own live data)
        symbol : if provided, scan only this symbol; otherwise scan all

        Returns
        -------
        List[Signal] with direction indicating the SPOT side of the trade:
            BUY  = long spot + short perp (collect positive funding)
            SELL = short spot + long perp (collect negative funding)
        """
        if requests is None:
            logger.error("requests library not available")
            return []

        targets = [symbol] if symbol else self.symbols
        all_signals: List[Signal] = []

        for sym in targets:
            try:
                sig = self._scan_symbol(sym)
                if sig:
                    all_signals.append(sig)
            except Exception as e:
                logger.warning("Error scanning %s: %s", sym, e)

        return all_signals

    # ── Core Logic ───────────────────────────────────────────────────

    def _scan_symbol(self, symbol: str) -> Optional[Signal]:
        """Fetch funding data and evaluate carry opportunity for one symbol."""

        # 1. Get funding rate history (last 30 periods)
        history = self._fetch_funding_history(symbol)
        if not history or len(history) < 5:
            logger.warning("%s: insufficient funding history (%d periods)",
                           symbol, len(history) if history else 0)
            return None

        # 2. Get current funding rate and mark price
        current_rate, next_funding_time = self._fetch_current_funding(symbol)
        if current_rate is None:
            logger.warning("%s: could not fetch current funding rate", symbol)
            return None

        # 3. Get current price
        price = self._fetch_price(symbol)
        if price is None:
            logger.warning("%s: could not fetch price", symbol)
            return None

        # 4. Calculate metrics
        rates = [h["rate"] for h in history]
        sma_30 = sum(rates) / len(rates)
        funding_drift = current_rate - sma_30
        annualized_yield = current_rate * 3 * 365 * 100  # percentage

        logger.info(
            "%s | rate=%.6f%% | sma30=%.6f%% | drift=%.6f%% | ann_yield=%.2f%%",
            symbol,
            current_rate * 100,
            sma_30 * 100,
            funding_drift * 100,
            annualized_yield,
        )

        # 5. Check entry conditions
        if abs(current_rate) < self.entry_threshold:
            logger.info("%s: funding rate %.6f below threshold %.6f, skip",
                        symbol, abs(current_rate), self.entry_threshold)
            return None

        if abs(funding_drift) < self.drift_threshold:
            logger.info("%s: drift %.6f below threshold %.6f, skip",
                        symbol, abs(funding_drift), self.drift_threshold)
            return None

        # 6. Determine direction and build signal
        if current_rate > self.entry_threshold and funding_drift > self.drift_threshold:
            # Positive funding: longs pay shorts
            # Strategy: LONG spot + SHORT perp (collect from longs)
            direction = "BUY"
            carry_direction = "positive"
            # TP: price doesn't matter much, but set reasonable target
            # SL: if funding flips negative, the trade thesis is broken
            expected_carry_pct = current_rate * self.tp_periods * 100
            tp = round(price * (1 + expected_carry_pct / 100), 2)
            sl = round(price * (1 - self.sl_price_pct), 2)

        elif current_rate < -self.entry_threshold and funding_drift < -self.drift_threshold:
            # Negative funding: shorts pay longs
            # Strategy: SHORT spot + LONG perp (collect from shorts)
            direction = "SELL"
            carry_direction = "negative"
            expected_carry_pct = abs(current_rate) * self.tp_periods * 100
            tp = round(price * (1 - expected_carry_pct / 100), 2)
            sl = round(price * (1 + self.sl_price_pct), 2)

        else:
            logger.info("%s: rate/drift direction mismatch, skip", symbol)
            return None

        # 7. Confidence scoring
        #    - Higher |funding rate| = higher confidence
        #    - Drift alignment with current rate = higher confidence
        #    - More consistent history = higher confidence
        rate_strength = min(abs(current_rate) / 0.001, 1.0)  # normalize to 0.1%
        drift_strength = min(abs(funding_drift) / 0.0005, 1.0)
        # Check how many of last 10 periods agree with current direction
        recent_rates = rates[-10:] if len(rates) >= 10 else rates
        if direction == "BUY":
            consistency = sum(1 for r in recent_rates if r > 0) / len(recent_rates)
        else:
            consistency = sum(1 for r in recent_rates if r < 0) / len(recent_rates)

        confidence = round(
            0.3 * rate_strength + 0.3 * drift_strength + 0.4 * consistency,
            4,
        )
        confidence = max(0.30, min(confidence, 0.95))

        reason = (
            f"Funding carry ({carry_direction}): rate={current_rate*100:.4f}% "
            f"sma30={sma_30*100:.4f}% drift={funding_drift*100:.4f}% "
            f"ann_yield={annualized_yield:.1f}% consistency={consistency:.0%}"
        )

        logger.info("%s SIGNAL: %s @ %.2f | conf=%.4f | %s",
                    symbol, direction, price, confidence, reason)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=round(price, 2),
            take_profit=tp,
            stop_loss=sl,
            reason=reason,
            timeframe="8h",
            metadata={
                "funding_rate": current_rate,
                "funding_sma30": sma_30,
                "funding_drift": funding_drift,
                "annualized_yield_pct": annualized_yield,
                "carry_direction": carry_direction,
                "consistency": consistency,
                "next_funding_time": next_funding_time,
                "history_periods": len(history),
            },
        )

    # ── Binance API Helpers ──────────────────────────────────────────

    def _fetch_funding_history(self, symbol: str) -> Optional[List[dict]]:
        """
        Fetch funding rate history with geo-restriction fallback.
        Returns list of {"rate": float, "time": int} sorted oldest->newest.
        """
        return _fetch_funding_fallback(symbol, self.history_limit, self._request_timeout)

    def _fetch_current_funding(self, symbol: str) -> tuple:
        """
        Fetch current/latest funding rate with geo-restriction fallback.
        Returns (funding_rate: float, next_funding_time: str) or (None, None).
        """
        # Try Binance premiumIndex first (has nextFundingTime)
        try:
            resp = requests.get(
                "https://fapi.binance.com/fapi/v1/premiumIndex",
                params={"symbol": symbol},
                timeout=self._request_timeout,
            )
            if resp.status_code != 451:
                resp.raise_for_status()
                data = resp.json()
                rate = float(data["lastFundingRate"])
                next_ts = int(data.get("nextFundingTime", 0))
                next_time = (
                    datetime.fromtimestamp(next_ts / 1000, tz=timezone.utc).isoformat()
                    if next_ts > 0
                    else "unknown"
                )
                return rate, next_time
        except Exception as e:
            logger.debug("Binance premiumIndex failed for %s: %s", symbol, e)

        # Fallback: use funding rate history (last entry)
        history = _fetch_funding_fallback(symbol, limit=1, timeout=self._request_timeout)
        if history and len(history) > 0:
            return history[-1]["rate"], "unknown"

        return None, None

    def _fetch_price(self, symbol: str) -> Optional[float]:
        """Fetch current price with geo-restriction fallback."""
        return _fetch_price_fallback(symbol, self._request_timeout)


# ── Standalone runner ────────────────────────────────────────────────

def main():
    """Run the funding rate carry scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = FundingRateCarryStrategy()
    signals = strategy.generate_signals()

    print(f"\n{'='*70}")
    print(f"  FUNDING RATE CARRY SCANNER  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")

    if not signals:
        print("\n  No carry opportunities found at current funding rates.")
        print("  (Thresholds: |rate| > 0.03%, |drift| > 0.01%)")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*40}")
            spot_side = "LONG" if sig.direction == "BUY" else "SHORT"
            perp_side = "SHORT" if sig.direction == "BUY" else "LONG"
            print(f"  Direction:   {spot_side} spot + {perp_side} perp")
            print(f"  Price:       ${sig.entry_price:,.2f}")
            print(f"  TP:          ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:  {sig.confidence:.1%}")
            print(f"  Funding:     {m['funding_rate']*100:.4f}%  (SMA30: {m['funding_sma30']*100:.4f}%)")
            print(f"  Drift:       {m['funding_drift']*100:.4f}%")
            print(f"  Ann. Yield:  {m['annualized_yield_pct']:.1f}%")
            print(f"  Consistency: {m['consistency']:.0%}")
            print(f"  Next Fund:   {m['next_funding_time']}")

    print(f"\n{'='*70}")
    print(f"  Scanned {len(strategy.symbols)} symbols, found {len(signals)} opportunities")
    print(f"{'='*70}\n")

    # Return signals as dicts for integration with battleground pipeline
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

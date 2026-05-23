#!/usr/bin/env python3
"""
Open Interest Divergence + Liquidation Cascade Predictor
=========================================================

Created by: google_antigravity
Date: 2026-03-13

Research Sources:
- CoinGlass liquidation heatmap methodology
- Binance public OI + funding rate + long/short ratio APIs
- Hummingbot "Liquidation Sniper" strategy pattern
- github.com/jaymgonzalez/python-trading/liquidation_levels.py

Strategy Logic:
1. Fetches Open Interest history from Binance (free, no key)
2. Detects OI-Price Divergence:
   - Price UP + OI DOWN = weakening trend, potential reversal DOWN
   - Price DOWN + OI UP = shorts piling in, potential short squeeze UP
   - Price UP + OI UP (aligned) = strong trend continuation
3. Calculates Liquidation Risk Score:
   - High OI + extreme funding + tilted long/short ratio = cascade imminent
   - Predicts CASCADE DIRECTION based on which side is overleveraged
4. Combines with funding rate for multi-signal confirmation

Why This Works:
   Open interest tells you WHERE the leveraged money is positioned.
   When OI diverges from price, it reveals hidden positioning shifts.
   Liquidation cascades are predictable — they happen when leverage
   is extreme and price moves against the crowded trade.
   
   This is FREE alpha from public Binance data that most retail ignores.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ENAUSDT", "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT"]

from api_helpers import (
    fetch_current_price as _fetch_price_fallback,
    fetch_futures_klines as _fetch_futures_klines_fallback,
    fetch_funding_rate_single as _fetch_funding_single_fallback,
)

# Binance futures-specific endpoints (OI hist & L/S ratio have no alternative)
BINANCE_OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"
BINANCE_LS_RATIO_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"

# Divergence thresholds
OI_CHANGE_THRESHOLD = 0.03    # 3% OI change needed
PRICE_CHANGE_THRESHOLD = 0.02 # 2% price change needed
DIVERGENCE_LOOKBACK = 12      # periods (5m each = 1 hour lookback)

# Liquidation Risk thresholds
FUNDING_EXTREME = 0.0005      # 0.05% = elevated
FUNDING_CRITICAL = 0.001      # 0.1% = extreme
LS_RATIO_EXTREME = 2.0        # 2:1 long/short = overleveraged longs
LS_RATIO_INVERSE = 0.5        # 1:2 = overleveraged shorts

# Risk parameters
TP_PCT = 0.015    # 1.5% take-profit
SL_PCT = 0.008    # 0.8% stop-loss


@dataclass
class OIDivergence:
    """Detected OI-Price divergence."""
    divergence_type: str  # "BEARISH_DIVERGENCE", "BULLISH_DIVERGENCE", "ALIGNED"
    price_change_pct: float
    oi_change_pct: float
    strength: float       # 0-1 based on magnitude of divergence


@dataclass
class LiquidationRisk:
    """Liquidation cascade risk assessment."""
    risk_level: str       # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_score: float     # 0-1
    cascade_direction: str  # "DOWN" (longs get liquidated) or "UP" (shorts get squeezed)
    funding_rate: float
    long_short_ratio: float
    oi_level: float


@dataclass
class Signal:
    """Trading signal — battleground format."""
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    strategy: str = "oi_divergence_liquidation_v1"
    timeframe: str = "5m"
    metadata: dict = field(default_factory=dict)


class OIDivergenceLiquidationStrategy:
    """
    Open Interest Divergence + Liquidation Cascade Predictor.
    
    Uses free Binance data:
    - OI history to detect price-OI divergence
    - Long/short ratio to gauge positioning
    - Funding rate to confirm leverage direction
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self.lookback = p.get("divergence_lookback", DIVERGENCE_LOOKBACK)
        self._timeout = p.get("request_timeout", 10)

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """Scan symbols for OI divergence + liquidation risk signals."""
        if requests is None:
            logger.error("requests library not available")
            return []

        targets = [symbol] if symbol else self.symbols
        all_signals = []

        for sym in targets:
            try:
                sig = self._analyze_symbol(sym)
                if sig:
                    all_signals.append(sig)
            except Exception as e:
                logger.warning("Error analyzing %s: %s", sym, e)
            time.sleep(0.15)  # rate limiting

        return all_signals

    def _analyze_symbol(self, symbol: str) -> Optional[Signal]:
        """Full OI divergence + liquidation analysis for one symbol."""

        # 1. Fetch current price
        price = self._fetch_price(symbol)
        if not price:
            return None

        # 2. Fetch OI history
        oi_data = self._fetch_oi_history(symbol)

        # 3. Fetch price history (klines)
        klines = self._fetch_klines(symbol)

        # 4. Detect OI-Price divergence
        divergence = self._detect_divergence(oi_data, klines)

        # 5. Fetch long/short ratio
        ls_ratio = self._fetch_long_short_ratio(symbol)

        # 6. Fetch funding rate
        funding = self._fetch_funding_rate(symbol)

        # 7. Calculate liquidation risk
        liq_risk = self._calc_liquidation_risk(
            oi_data, ls_ratio, funding, divergence
        )

        logger.info(
            "%s | price=%.2f | div=%s(%.2f) | liq=%s(%.2f→%s) | ls=%.2f | fund=%.6f",
            symbol, price,
            divergence.divergence_type if divergence else "N/A",
            divergence.strength if divergence else 0,
            liq_risk.risk_level if liq_risk else "N/A",
            liq_risk.risk_score if liq_risk else 0,
            liq_risk.cascade_direction if liq_risk else "N/A",
            ls_ratio or 0,
            funding or 0,
        )

        # 8. Generate signal
        return self._build_signal(symbol, price, divergence, liq_risk, ls_ratio, funding)

    def _build_signal(
        self, symbol, price, divergence, liq_risk, ls_ratio, funding
    ) -> Optional[Signal]:
        """Combine divergence + liquidation risk into a trading signal."""

        confidence = 0.0
        direction = None
        reasons = []

        # --- Divergence signals ---
        if divergence and divergence.strength > 0.3:
            if divergence.divergence_type == "BULLISH_DIVERGENCE":
                # Price down but OI up = shorts piling in = potential squeeze
                direction = "BUY"
                confidence += 0.25 * divergence.strength
                reasons.append(
                    f"OI-Price BULLISH divergence: price {divergence.price_change_pct:+.2f}% "
                    f"but OI {divergence.oi_change_pct:+.2f}% (shorts piling in)"
                )
            elif divergence.divergence_type == "BEARISH_DIVERGENCE":
                # Price up but OI down = longs unwinding = potential reversal
                direction = "SELL"
                confidence += 0.25 * divergence.strength
                reasons.append(
                    f"OI-Price BEARISH divergence: price {divergence.price_change_pct:+.2f}% "
                    f"but OI {divergence.oi_change_pct:+.2f}% (longs unwinding)"
                )

        # --- Liquidation risk signals ---
        if liq_risk and liq_risk.risk_score > 0.5:
            if liq_risk.cascade_direction == "DOWN" and liq_risk.risk_score > 0.6:
                if direction is None or direction == "SELL":
                    direction = "SELL"
                    confidence += 0.20 * liq_risk.risk_score
                    reasons.append(
                        f"Liquidation risk {liq_risk.risk_level}: longs overleveraged "
                        f"(L/S={ls_ratio:.2f}, fund={funding*100:.4f}%) → cascade DOWN likely"
                    )
                elif direction == "BUY":
                    confidence -= 0.10  # contradictory signals
                    reasons.append(f"⚠ Liq risk contradicts divergence (cascade DOWN)")

            elif liq_risk.cascade_direction == "UP" and liq_risk.risk_score > 0.6:
                if direction is None or direction == "BUY":
                    direction = "BUY"
                    confidence += 0.20 * liq_risk.risk_score
                    reasons.append(
                        f"Liquidation risk {liq_risk.risk_level}: shorts overleveraged "
                        f"(L/S={ls_ratio:.2f}, fund={funding*100:.4f}%) → squeeze UP likely"
                    )
                elif direction == "SELL":
                    confidence -= 0.10
                    reasons.append(f"⚠ Liq risk contradicts divergence (squeeze UP)")

        # --- Funding rate extreme bonus ---
        if funding is not None and abs(funding) > FUNDING_EXTREME:
            if funding > FUNDING_CRITICAL and direction == "SELL":
                confidence += 0.10
                reasons.append(f"Extreme positive funding confirms short bias")
            elif funding < -FUNDING_CRITICAL and direction == "BUY":
                confidence += 0.10
                reasons.append(f"Extreme negative funding confirms long bias")

        # --- Minimum confidence gate ---
        if direction is None or confidence < 0.30:
            return None

        confidence = max(0.30, min(0.95, confidence))

        # Set TP/SL
        if direction == "BUY":
            tp = round(price * (1 + TP_PCT), 2)
            sl = round(price * (1 - SL_PCT), 2)
        else:
            tp = round(price * (1 - TP_PCT), 2)
            sl = round(price * (1 + SL_PCT), 2)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(confidence, 4),
            entry_price=round(price, 2),
            take_profit=tp,
            stop_loss=sl,
            reason=" | ".join(reasons),
            metadata={
                "divergence_type": divergence.divergence_type if divergence else "NONE",
                "divergence_strength": divergence.strength if divergence else 0,
                "price_change_pct": divergence.price_change_pct if divergence else 0,
                "oi_change_pct": divergence.oi_change_pct if divergence else 0,
                "liquidation_risk": liq_risk.risk_level if liq_risk else "UNKNOWN",
                "liquidation_score": liq_risk.risk_score if liq_risk else 0,
                "cascade_direction": liq_risk.cascade_direction if liq_risk else "UNKNOWN",
                "long_short_ratio": ls_ratio or 0,
                "funding_rate": funding or 0,
                "funding_annualized_pct": round((funding or 0) * 3 * 365 * 100, 2),
            },
        )

    # ── Divergence Detection ─────────────────────────────────────────

    def _detect_divergence(self, oi_data, klines) -> Optional[OIDivergence]:
        """Detect OI-Price divergence over the lookback period."""
        if not oi_data or len(oi_data) < 3 or not klines or len(klines) < 3:
            return None

        # Use available data, up to lookback periods
        n = min(len(oi_data), len(klines), self.lookback)

        oi_start = oi_data[-n].get("sumOpenInterest", oi_data[-n].get("openInterest", 0))
        oi_end = oi_data[-1].get("sumOpenInterest", oi_data[-1].get("openInterest", 0))

        oi_start = float(oi_start) if oi_start else 0
        oi_end = float(oi_end) if oi_end else 0

        price_start = float(klines[-n][4])  # close price
        price_end = float(klines[-1][4])

        if oi_start == 0 or price_start == 0:
            return None

        oi_change = (oi_end - oi_start) / oi_start
        price_change = (price_end - price_start) / price_start

        # Classify divergence
        if price_change > PRICE_CHANGE_THRESHOLD and oi_change < -OI_CHANGE_THRESHOLD:
            # Price UP, OI DOWN = bearish divergence (longs closing)
            strength = min(1.0, (abs(price_change) + abs(oi_change)) / 0.1)
            return OIDivergence("BEARISH_DIVERGENCE", round(price_change*100, 2),
                              round(oi_change*100, 2), round(strength, 3))

        elif price_change < -PRICE_CHANGE_THRESHOLD and oi_change > OI_CHANGE_THRESHOLD:
            # Price DOWN, OI UP = bullish divergence (shorts entering → squeeze potential)
            strength = min(1.0, (abs(price_change) + abs(oi_change)) / 0.1)
            return OIDivergence("BULLISH_DIVERGENCE", round(price_change*100, 2),
                              round(oi_change*100, 2), round(strength, 3))

        elif price_change > PRICE_CHANGE_THRESHOLD and oi_change > OI_CHANGE_THRESHOLD:
            strength = min(1.0, (abs(price_change) + abs(oi_change)) / 0.15)
            return OIDivergence("ALIGNED_BULLISH", round(price_change*100, 2),
                              round(oi_change*100, 2), round(strength, 3))

        elif price_change < -PRICE_CHANGE_THRESHOLD and oi_change < -OI_CHANGE_THRESHOLD:
            strength = min(1.0, (abs(price_change) + abs(oi_change)) / 0.15)
            return OIDivergence("ALIGNED_BEARISH", round(price_change*100, 2),
                              round(oi_change*100, 2), round(strength, 3))

        return OIDivergence("NEUTRAL", round(price_change*100, 2),
                           round(oi_change*100, 2), 0.0)

    # ── Liquidation Risk ─────────────────────────────────────────────

    def _calc_liquidation_risk(self, oi_data, ls_ratio, funding, divergence) -> Optional[LiquidationRisk]:
        """Calculate liquidation cascade risk."""
        if funding is None and ls_ratio is None:
            return None

        score = 0.0
        cascade_dir = "NEUTRAL"

        # Factor 1: Funding rate extremity (0-0.3)
        fund = abs(funding) if funding else 0
        if fund > FUNDING_CRITICAL:
            score += 0.30
        elif fund > FUNDING_EXTREME:
            score += 0.15

        # Factor 2: Long/short ratio imbalance (0-0.3)
        lsr = ls_ratio or 1.0
        if lsr > LS_RATIO_EXTREME:
            score += 0.30
            cascade_dir = "DOWN"  # too many longs → cascade down
        elif lsr < LS_RATIO_INVERSE:
            score += 0.30
            cascade_dir = "UP"   # too many shorts → squeeze up
        elif lsr > 1.5:
            score += 0.15
            cascade_dir = "DOWN"
        elif lsr < 0.67:
            score += 0.15
            cascade_dir = "UP"

        # Factor 3: OI at elevated levels (0-0.2)
        if oi_data and len(oi_data) >= 5:
            oi_values = [float(d.get("sumOpenInterest", d.get("openInterest", 0))) 
                        for d in oi_data[-10:]]
            oi_values = [v for v in oi_values if v > 0]
            if len(oi_values) >= 3:
                current_oi = oi_values[-1]
                avg_oi = statistics.mean(oi_values[:-1])
                if avg_oi > 0 and current_oi / avg_oi > 1.15:
                    score += 0.20  # OI significantly above recent average

        # Factor 4: Divergence confirms cascade direction (0-0.2)
        if divergence:
            if divergence.divergence_type == "BEARISH_DIVERGENCE" and cascade_dir == "DOWN":
                score += 0.20
            elif divergence.divergence_type == "BULLISH_DIVERGENCE" and cascade_dir == "UP":
                score += 0.20

        # Determine funding direction if cascade_dir not set
        if cascade_dir == "NEUTRAL" and funding:
            cascade_dir = "DOWN" if funding > 0 else "UP"

        # Risk level
        if score > 0.7:
            level = "CRITICAL"
        elif score > 0.5:
            level = "HIGH"
        elif score > 0.3:
            level = "MEDIUM"
        else:
            level = "LOW"

        return LiquidationRisk(
            risk_level=level,
            risk_score=round(score, 3),
            cascade_direction=cascade_dir,
            funding_rate=funding or 0,
            long_short_ratio=ls_ratio or 1.0,
            oi_level=float(oi_data[-1].get("sumOpenInterest", 0)) if oi_data else 0,
        )

    # ── Binance API Helpers ──────────────────────────────────────────

    def _fetch_price(self, symbol: str) -> Optional[float]:
        """Fetch current price with geo-restriction fallback."""
        return _fetch_price_fallback(symbol, self._timeout)

    def _fetch_oi_history(self, symbol: str) -> Optional[list]:
        """Fetch OI history (5-min intervals)."""
        try:
            resp = requests.get(
                BINANCE_OI_HIST_URL,
                params={"symbol": symbol, "period": "5m", "limit": 30},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("OI history fetch error %s: %s", symbol, e)
            return None

    def _fetch_klines(self, symbol: str) -> Optional[list]:
        """Fetch 5m klines for price history with geo-restriction fallback."""
        data = _fetch_futures_klines_fallback(symbol, interval="5m", limit=30, timeout=self._timeout)
        return data if data else None

    def _fetch_long_short_ratio(self, symbol: str) -> Optional[float]:
        """Fetch global long/short account ratio."""
        try:
            resp = requests.get(
                BINANCE_LS_RATIO_URL,
                params={"symbol": symbol, "period": "5m", "limit": 1},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return float(data[0].get("longShortRatio", 1.0))
            return None
        except Exception as e:
            logger.warning("L/S ratio fetch error %s: %s", symbol, e)
            return None

    def _fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Fetch current funding rate with geo-restriction fallback."""
        return _fetch_funding_single_fallback(symbol, self._timeout)


# ── Standalone Runner ────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    strategy = OIDivergenceLiquidationStrategy()
    signals = strategy.generate_signals()

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f"\n{'='*75}")
    print(f"  OI DIVERGENCE + LIQUIDATION CASCADE SCANNER  |  {ts}")
    print(f"{'='*75}")

    if not signals:
        print("\n  No divergence/liquidation signals at current levels.")
        print("  OI-price divergence and liquidation cascades are episodic events.")
    else:
        for sig in signals:
            m = sig.metadata
            print(f"\n  {sig.symbol}")
            print(f"  {'─'*55}")
            print(f"  Direction:    {sig.direction}")
            print(f"  Entry:        ${sig.entry_price:,.2f}")
            print(f"  TP:           ${sig.take_profit:,.2f}  |  SL: ${sig.stop_loss:,.2f}")
            print(f"  Confidence:   {sig.confidence:.1%}")
            print(f"  Divergence:   {m['divergence_type']} (str={m['divergence_strength']:.2f})")
            print(f"  Price Δ:      {m['price_change_pct']:+.2f}%  |  OI Δ: {m['oi_change_pct']:+.2f}%")
            print(f"  Liq Risk:     {m['liquidation_risk']} (score={m['liquidation_score']:.2f})")
            print(f"  Cascade:      {m['cascade_direction']}")
            print(f"  L/S Ratio:    {m['long_short_ratio']:.2f}")
            print(f"  Funding:      {m['funding_rate']*100:.4f}% (ann: {m['funding_annualized_pct']:.1f}%)")

    print(f"\n{'='*75}")
    print(f"  Scanned {len(strategy.symbols)} symbols, found {len(signals)} signals")
    print(f"{'='*75}\n")

    return [
        {
            "symbol": s.symbol, "direction": s.direction, "strategy": s.strategy,
            "confidence": s.confidence, "entry_price": s.entry_price,
            "take_profit": s.take_profit, "stop_loss": s.stop_loss,
            "timeframe": s.timeframe, "reason": s.reason, "metadata": s.metadata,
        }
        for s in signals
    ]


if __name__ == "__main__":
    main()

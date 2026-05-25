#!/usr/bin/env python3
"""
Gas Price Urgency Index Strategy
=================================

Created by: claude_code
Date: 2026-03-13

Research Source:
    Kilo-Code TradingView indicator research (tradingview_indicator_research_summary.md)

Strategy Logic:
    Ethereum gas price spikes are a leading indicator for short-term volatility
    bursts across the entire crypto market. High gas = network congestion =
    traders urgently positioning = imminent price move. Gas spikes precede
    ETH moves by 5-30 minutes.

    1. Fetch current ETH gas prices from free APIs (Etherscan, Blocknative,
       or volume-spike proxy as fallback)
    2. Calculate Gas Urgency Index = gas_fast / gas_baseline
       - > 2.0 = urgent, > 3.0 = extreme
    3. Combine with ETH RSI + volume spike for directional signal
    4. Apply to ALL crypto symbols (gas urgency affects entire market)

Signal Logic:
    LONG:  gas_urgency > 2.0 + eth_rsi < 40 + eth_vol_spike > 1.5
    SHORT: gas_urgency > 2.0 + eth_rsi > 70 + eth_vol_spike > 1.5

Risk Management:
    TP = 1.8 * ATR(14), SL = 1.3 * ATR(14) — tighter ratio for volatility trades

Why This Works:
    Gas price spikes reveal real-time demand for block space. When traders are
    desperate to get transactions confirmed (high gas), they are positioning
    ahead of expected moves. This signal is NOT priced in by most retail
    because it requires monitoring a separate data feed (gas oracle) alongside
    price charts.
"""

from __future__ import annotations

import logging
import os
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
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ENAUSDT",
    "JUPUSDT", "WIFUSDT", "STXUSDT", "RENDERUSDT",
]

from api_helpers import fetch_klines as _fetch_klines_fallback
from api_helpers import fetch_current_price as _fetch_price_fallback

# Gas urgency thresholds
GAS_URGENCY_THRESHOLD = 2.0       # minimum ratio to generate signal
GAS_URGENCY_EXTREME = 3.0         # extreme urgency bonus
GAS_BASELINE_STATIC = 30.0        # static baseline in gwei (fallback)
ETH_RSI_OVERSOLD = 40             # RSI below this = oversold
ETH_RSI_OVERBOUGHT = 70           # RSI above this = overbought
VOL_SPIKE_THRESHOLD = 1.5         # volume must be 1.5x SMA(20)
GAS_NORMAL_THRESHOLD = 1.5        # below this = no signal (normal activity)

# ATR-based risk parameters
ATR_PERIOD = 14
TP_ATR_MULT = 1.8                 # take-profit = 1.8 * ATR
SL_ATR_MULT = 1.3                 # stop-loss = 1.3 * ATR


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
    strategy: str = "gas_urgency_index_v1"
    timeframe: str = "15m"
    metadata: dict = field(default_factory=dict)


class GasUrgencyIndexStrategy:
    """
    Gas Price Urgency Index — market-wide crypto volatility predictor.

    Uses Ethereum gas prices as a leading indicator for short-term volatility.
    When gas spikes above 2x the baseline, it signals network congestion from
    traders urgently positioning. Combined with ETH RSI and volume, this
    generates directional signals for all major crypto pairs.
    """

    def __init__(self, params: Optional[dict] = None):
        p = params or {}
        self.symbols = p.get("symbols", SYMBOLS)
        self._timeout = p.get("request_timeout", 10)
        self._etherscan_key = p.get(
            "etherscan_api_key",
            os.environ.get("ETHERSCAN_API_KEY", ""),
        )

    # ── Public API ───────────────────────────────────────────────────

    def generate_signals(self, data=None, symbol: str = None) -> List[Signal]:
        """
        Scan all configured symbols for gas-urgency-driven signals.

        Parameters
        ----------
        data : ignored (this strategy fetches its own live data)
        symbol : if provided, scan only this symbol; otherwise scan all

        Returns
        -------
        List[Signal]
        """
        if requests is None:
            logger.error("requests library not available")
            return []

        # Step 1: Fetch gas price (shared across all symbols)
        gas_fast, gas_baseline = self._fetch_gas_data()
        if gas_fast is None:
            logger.warning("Could not fetch gas data from any source")
            return []

        gas_urgency = gas_fast / gas_baseline if gas_baseline > 0 else 0.0
        logger.info(
            "Gas data: fast=%.1f gwei, baseline=%.1f gwei, urgency=%.2f",
            gas_fast, gas_baseline, gas_urgency,
        )

        if gas_urgency < GAS_NORMAL_THRESHOLD:
            logger.info(
                "Gas urgency %.2f below threshold %.1f — no signals",
                gas_urgency, GAS_NORMAL_THRESHOLD,
            )
            return []

        # Step 2: Fetch ETH klines for market-wide context
        eth_klines = _fetch_klines_fallback("ETHUSDT", "15m", 100, self._timeout)
        if not eth_klines or len(eth_klines) < 21:
            logger.warning("Insufficient ETH klines (%d), need at least 21",
                           len(eth_klines) if eth_klines else 0)
            return []

        eth_closes = [float(k[4]) for k in eth_klines]
        eth_volumes = [float(k[5]) for k in eth_klines]

        eth_rsi = self._compute_rsi(eth_closes, 14)
        eth_vol_sma20 = sum(eth_volumes[-20:]) / 20.0
        eth_vol_spike = eth_volumes[-1] / eth_vol_sma20 if eth_vol_sma20 > 0 else 0.0

        logger.info(
            "ETH context: RSI=%.1f, vol_spike=%.2f (curr=%.0f, sma20=%.0f)",
            eth_rsi, eth_vol_spike, eth_volumes[-1], eth_vol_sma20,
        )

        # Check minimum conditions before scanning symbols
        if gas_urgency < GAS_URGENCY_THRESHOLD:
            logger.info("Gas urgency %.2f < %.1f threshold, skip",
                        gas_urgency, GAS_URGENCY_THRESHOLD)
            return []

        if eth_vol_spike < VOL_SPIKE_THRESHOLD:
            logger.info("ETH vol spike %.2f < %.1f threshold, skip",
                        eth_vol_spike, VOL_SPIKE_THRESHOLD)
            return []

        # Determine direction from ETH RSI
        if eth_rsi < ETH_RSI_OVERSOLD:
            market_direction = "BUY"
        elif eth_rsi > ETH_RSI_OVERBOUGHT:
            market_direction = "SELL"
        else:
            logger.info("ETH RSI %.1f in neutral zone (%d-%d), no directional signal",
                        eth_rsi, ETH_RSI_OVERSOLD, ETH_RSI_OVERBOUGHT)
            return []

        # Step 3: Scan individual symbols
        targets = [symbol] if symbol else self.symbols
        all_signals: List[Signal] = []

        for sym in targets:
            try:
                sig = self._scan_symbol(
                    sym, gas_urgency, gas_fast, gas_baseline,
                    eth_rsi, eth_vol_spike, market_direction,
                )
                if sig:
                    all_signals.append(sig)
            except Exception as e:
                logger.warning("Error scanning %s: %s", sym, e)
            time.sleep(0.1)  # rate limiting

        return all_signals

    # ── Per-Symbol Analysis ───────────────────────────────────────────

    def _scan_symbol(
        self,
        symbol: str,
        gas_urgency: float,
        gas_fast: float,
        gas_baseline: float,
        eth_rsi: float,
        eth_vol_spike: float,
        market_direction: str,
    ) -> Optional[Signal]:
        """Analyze one symbol given the gas urgency context."""

        # Fetch symbol's own klines for RSI and ATR
        klines = _fetch_klines_fallback(symbol, "15m", 100, self._timeout)
        if not klines or len(klines) < ATR_PERIOD + 1:
            logger.warning("%s: insufficient klines (%d)",
                           symbol, len(klines) if klines else 0)
            return None

        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        price = closes[-1]

        # Compute symbol's own RSI
        sym_rsi = self._compute_rsi(closes, 14)

        # Compute ATR for TP/SL
        atr = self._compute_atr(highs, lows, closes, ATR_PERIOD)
        if atr <= 0:
            logger.warning("%s: ATR is zero or negative", symbol)
            return None

        # Confidence calculation
        confidence = 0.55  # base

        # Bonus for extreme gas urgency
        if gas_urgency > GAS_URGENCY_EXTREME:
            confidence += 0.10

        # Bonus if symbol's own RSI agrees with direction
        if market_direction == "BUY" and sym_rsi < ETH_RSI_OVERSOLD:
            confidence += 0.05
        elif market_direction == "SELL" and sym_rsi > ETH_RSI_OVERBOUGHT:
            confidence += 0.05

        confidence = max(0.30, min(0.95, round(confidence, 4)))

        # TP/SL based on ATR
        if market_direction == "BUY":
            tp = round(price + TP_ATR_MULT * atr, 2)
            sl = round(price - SL_ATR_MULT * atr, 2)
        else:
            tp = round(price - TP_ATR_MULT * atr, 2)
            sl = round(price + SL_ATR_MULT * atr, 2)

        reason = (
            "Gas Urgency {urg:.1f}x (fast={fast:.0f} gwei, base={base:.0f}) "
            "+ ETH RSI={rsi:.1f} ({cond}) + vol_spike={vol:.1f}x"
        ).format(
            urg=gas_urgency,
            fast=gas_fast,
            base=gas_baseline,
            rsi=eth_rsi,
            cond="oversold" if market_direction == "BUY" else "overbought",
            vol=eth_vol_spike,
        )

        if market_direction == "BUY" and sym_rsi < ETH_RSI_OVERSOLD:
            reason += " | {sym} RSI={sr:.1f} confirms oversold".format(
                sym=symbol, sr=sym_rsi,
            )
        elif market_direction == "SELL" and sym_rsi > ETH_RSI_OVERBOUGHT:
            reason += " | {sym} RSI={sr:.1f} confirms overbought".format(
                sym=symbol, sr=sym_rsi,
            )

        logger.info(
            "%s SIGNAL: %s @ %.2f | conf=%.4f | %s",
            symbol, market_direction, price, confidence, reason,
        )

        return Signal(
            symbol=symbol,
            direction=market_direction,
            confidence=confidence,
            entry_price=round(price, 2),
            take_profit=tp,
            stop_loss=sl,
            reason=reason,
            metadata={
                "gas_fast_gwei": gas_fast,
                "gas_baseline_gwei": gas_baseline,
                "gas_urgency": round(gas_urgency, 3),
                "eth_rsi": round(eth_rsi, 2),
                "eth_vol_spike": round(eth_vol_spike, 3),
                "symbol_rsi": round(sym_rsi, 2),
                "atr_14": round(atr, 4),
                "tp_atr_mult": TP_ATR_MULT,
                "sl_atr_mult": SL_ATR_MULT,
            },
        )

    # ── Gas Price Fetching (3-tier fallback) ──────────────────────────

    def _fetch_gas_data(self) -> tuple:
        """
        Fetch current ETH gas price with 3-tier fallback chain.

        Returns (gas_fast, gas_baseline) in gwei, or (None, None) on failure.

        Tier 1: Etherscan Gas Oracle (free tier, 5 calls/sec)
        Tier 2: Blocknative Gas Prices (free tier)
        Tier 3: ETH volume spike proxy (uses klines, always available)
        """
        # Tier 1: Etherscan
        gas = self._fetch_gas_etherscan()
        if gas is not None:
            return gas

        # Tier 2: Blocknative
        gas = self._fetch_gas_blocknative()
        if gas is not None:
            return gas

        # Tier 3: Volume proxy
        gas = self._fetch_gas_volume_proxy()
        if gas is not None:
            return gas

        return None, None

    def _fetch_gas_etherscan(self) -> Optional[tuple]:
        """Fetch gas from Etherscan Gas Oracle API."""
        try:
            params = {
                "module": "gastracker",
                "action": "gasoracle",
            }
            if self._etherscan_key:
                params["apikey"] = self._etherscan_key

            resp = requests.get(
                "https://api.etherscan.io/api",
                params=params,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "1" and data.get("result"):
                result = data["result"]
                gas_fast = float(result.get("FastGasPrice", 0))
                gas_safe = float(result.get("SafeGasPrice", 0))
                gas_propose = float(result.get("ProposeGasPrice", 0))

                if gas_fast > 0:
                    # Use SafeGasPrice as a proxy for baseline (lower bound)
                    # A more conservative baseline uses average of safe + propose
                    baseline = (gas_safe + gas_propose) / 2.0
                    if baseline <= 0:
                        baseline = GAS_BASELINE_STATIC
                    logger.info(
                        "Etherscan gas: fast=%.1f, propose=%.1f, safe=%.1f, baseline=%.1f",
                        gas_fast, gas_propose, gas_safe, baseline,
                    )
                    return gas_fast, baseline

            logger.debug("Etherscan returned unexpected data: %s", data.get("message", ""))
        except Exception as e:
            logger.debug("Etherscan gas oracle failed: %s", e)

        return None

    def _fetch_gas_blocknative(self) -> Optional[tuple]:
        """Fetch gas from Blocknative Gas Prices API (free tier)."""
        try:
            resp = requests.get(
                "https://api.blocknative.com/gasprices/blockprices",
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            # Blocknative returns blockPrices array with estimatedPrices
            block_prices = data.get("blockPrices", [])
            if block_prices:
                estimated = block_prices[0].get("estimatedPrices", [])
                if estimated:
                    # Find fast (confidence >= 90) and baseline (confidence ~70)
                    gas_fast = None
                    gas_baseline = None
                    for ep in estimated:
                        conf = ep.get("confidence", 0)
                        price_gwei = ep.get("price", 0)
                        if conf >= 90 and gas_fast is None:
                            gas_fast = float(price_gwei)
                        if conf <= 70 and gas_baseline is None:
                            gas_baseline = float(price_gwei)

                    if gas_fast and gas_fast > 0:
                        if not gas_baseline or gas_baseline <= 0:
                            gas_baseline = GAS_BASELINE_STATIC
                        logger.info(
                            "Blocknative gas: fast=%.1f, baseline=%.1f",
                            gas_fast, gas_baseline,
                        )
                        return gas_fast, gas_baseline

            logger.debug("Blocknative returned no usable gas data")
        except Exception as e:
            logger.debug("Blocknative gas prices failed: %s", e)

        return None

    def _fetch_gas_volume_proxy(self) -> Optional[tuple]:
        """
        Fallback: Use ETH 1m kline volume spike as a gas urgency proxy.

        Rationale: When gas is high, ETH on-chain activity is high, which
        correlates with elevated exchange volume on short timeframes.
        """
        try:
            klines = _fetch_klines_fallback("ETHUSDT", "1m", 60, self._timeout)
            if not klines or len(klines) < 30:
                return None

            volumes = [float(k[5]) for k in klines]
            recent_vol = volumes[-1]
            avg_vol = sum(volumes[:-1]) / len(volumes[:-1])

            if avg_vol <= 0:
                return None

            # Map volume ratio to a synthetic gas value
            vol_ratio = recent_vol / avg_vol
            synthetic_gas_fast = GAS_BASELINE_STATIC * vol_ratio
            logger.info(
                "Volume proxy gas: vol_ratio=%.2f, synthetic_fast=%.1f, baseline=%.1f",
                vol_ratio, synthetic_gas_fast, GAS_BASELINE_STATIC,
            )
            return synthetic_gas_fast, GAS_BASELINE_STATIC

        except Exception as e:
            logger.debug("Volume proxy gas estimation failed: %s", e)

        return None

    # ── Technical Indicators ──────────────────────────────────────────

    @staticmethod
    def _compute_rsi(closes: List[float], period: int = 14) -> float:
        """Compute RSI using Wilder's smoothing method."""
        if len(closes) < period + 1:
            return 50.0  # neutral default

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        # Seed with SMA of first `period` deltas
        gains = [d if d > 0 else 0.0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0.0 for d in deltas[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Wilder's smoothing for remaining deltas
        for d in deltas[period:]:
            gain = d if d > 0 else 0.0
            loss = -d if d < 0 else 0.0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _compute_atr(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> float:
        """Compute Average True Range."""
        if len(highs) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return 0.0

        # Simple average of last `period` true ranges
        return sum(true_ranges[-period:]) / period


# ── Module-level scan() function ─────────────────────────────────────

def scan(params: Optional[dict] = None) -> List[Signal]:
    """
    Module-level scan function for battleground integration.

    Returns list of Signal objects.
    """
    strategy = GasUrgencyIndexStrategy(params)
    return strategy.generate_signals()


# ── Standalone Runner ────────────────────────────────────────────────

def main():
    """Run the Gas Urgency Index scanner and print results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    strategy = GasUrgencyIndexStrategy()
    signals = strategy.generate_signals()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    separator = "=" * 70
    dash = "-" * 45

    print("")
    print(separator)
    print("  GAS URGENCY INDEX SCANNER  |  {t}".format(t=ts))
    print(separator)

    if not signals:
        print("")
        print("  No gas urgency signals at current levels.")
        print("  (Requires: gas_urgency > 2.0 + ETH RSI extreme + vol spike > 1.5x)")
    else:
        for sig in signals:
            m = sig.metadata
            print("")
            print("  {sym}".format(sym=sig.symbol))
            print("  {d}".format(d=dash))
            print("  Direction:    {dir}".format(dir=sig.direction))
            print("  Entry:        ${p:,.2f}".format(p=sig.entry_price))
            print("  TP:           ${tp:,.2f}  |  SL: ${sl:,.2f}".format(
                tp=sig.take_profit, sl=sig.stop_loss))
            print("  Confidence:   {c:.1%}".format(c=sig.confidence))
            print("  Gas Urgency:  {gu:.1f}x (fast={gf:.0f} gwei, base={gb:.0f})".format(
                gu=m["gas_urgency"], gf=m["gas_fast_gwei"], gb=m["gas_baseline_gwei"]))
            print("  ETH RSI:      {r:.1f}  |  ETH Vol Spike: {v:.1f}x".format(
                r=m["eth_rsi"], v=m["eth_vol_spike"]))
            print("  Symbol RSI:   {sr:.1f}".format(sr=m["symbol_rsi"]))
            print("  ATR(14):      {a:.4f}".format(a=m["atr_14"]))

    print("")
    print(separator)
    print("  Scanned {n} symbols, found {s} signals".format(
        n=len(strategy.symbols), s=len(signals)))
    print(separator)
    print("")

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

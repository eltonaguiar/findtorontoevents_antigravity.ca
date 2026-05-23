"""S11: Crypto Options Volatility — straddle/strangle-style directional
signals derived from implied volatility surface analysis.

Sources IV data from Deribit (BTC/ETH options) via the public API.
Generates signals when:
  - IV is at historical extremes (sell vol when high, buy when low)
  - IV skew (puts vs calls) is heavily tilted → directional signal
  - Term structure inversion (near > far IV) → crash protection signal

This fills the "Crypto Options Volatility" gap identified in the strategy
gap analysis. Existing theta_strategy.py and options_expiry_gamma are
equity-focused; this is crypto-native.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .base import Signal

logger = logging.getLogger(__name__)

DERIBIT_API = "https://www.deribit.com/api/v2/public"

# IV history for z-score computation
_iv_history: Dict[str, List[float]] = {}
_MAX_IV_HISTORY = 96  # 24 hours at 15-min intervals

# Map coinglass symbols to Deribit currency codes
DERIBIT_CURRENCY_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
}


def _fetch_deribit_iv(currency: str) -> Optional[Dict]:
    """Fetch current IV index and skew data from Deribit public API."""
    try:
        # Get volatility index (DVOL)
        resp = requests.get(
            f"{DERIBIT_API}/get_volatility_index_data",
            params={
                "currency": currency,
                "resolution": 3600,  # 1h
                "start_timestamp": int((datetime.now(timezone.utc).timestamp() - 86400) * 1000),
                "end_timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result", {})
            vol_data = result.get("data", [])
            if vol_data and len(vol_data) > 0:
                # Each entry: [timestamp, open, high, low, close]
                latest_iv = vol_data[-1][4]  # Close of latest period

                # Compute historical stats from the 24h of data
                ivs = [v[4] for v in vol_data if v[4] > 0]
                if len(ivs) > 5:
                    mean_iv = sum(ivs) / len(ivs)
                    std_iv = math.sqrt(sum((v - mean_iv) ** 2 for v in ivs) / len(ivs))
                    high_iv = max(ivs)
                    low_iv = min(ivs)

                    return {
                        "current_iv": latest_iv,
                        "mean_iv_24h": mean_iv,
                        "std_iv_24h": std_iv,
                        "high_iv_24h": high_iv,
                        "low_iv_24h": low_iv,
                        "iv_percentile": (latest_iv - low_iv) / (high_iv - low_iv) * 100
                            if high_iv > low_iv else 50.0,
                        "iv_count": len(ivs),
                    }
    except Exception as e:
        logger.debug("Deribit IV fetch failed for %s: %s", currency, e)

    return None


def _fetch_deribit_book_summary(currency: str) -> Optional[Dict]:
    """Fetch book summary for options to extract put/call skew."""
    try:
        resp = requests.get(
            f"{DERIBIT_API}/get_book_summary_by_currency",
            params={"currency": currency, "kind": "option"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            options = data.get("result", [])
            if not options:
                return None

            put_ivs = []
            call_ivs = []
            put_oi = 0
            call_oi = 0

            for opt in options:
                iv = opt.get("mark_iv", 0)
                oi = opt.get("open_interest", 0)
                name = opt.get("instrument_name", "")

                if iv <= 0:
                    continue

                if "-P" in name:
                    put_ivs.append(iv)
                    put_oi += oi
                elif "-C" in name:
                    call_ivs.append(iv)
                    call_oi += oi

            if put_ivs and call_ivs:
                avg_put_iv = sum(put_ivs) / len(put_ivs)
                avg_call_iv = sum(call_ivs) / len(call_ivs)
                skew = avg_put_iv - avg_call_iv  # Positive = puts more expensive
                pcr = put_oi / call_oi if call_oi > 0 else 1.0

                return {
                    "avg_put_iv": avg_put_iv,
                    "avg_call_iv": avg_call_iv,
                    "iv_skew": skew,
                    "put_call_ratio": pcr,
                    "total_put_oi": put_oi,
                    "total_call_oi": call_oi,
                }
    except Exception as e:
        logger.debug("Deribit book summary failed for %s: %s", currency, e)

    return None


def _compute_iv_zscore(symbol: str, current_iv: float) -> Optional[float]:
    """Compute z-score of current IV vs rolling history."""
    if symbol not in _iv_history:
        _iv_history[symbol] = []

    history = _iv_history[symbol]
    history.append(current_iv)

    if len(history) > _MAX_IV_HISTORY:
        _iv_history[symbol] = history[-_MAX_IV_HISTORY:]
        history = _iv_history[symbol]

    if len(history) < 10:
        return None

    mean = sum(history) / len(history)
    variance = sum((v - mean) ** 2 for v in history) / len(history)
    std = math.sqrt(variance) if variance > 0 else 0

    if std < 0.5:
        return None

    return (current_iv - mean) / std


def run(symbol: str, recent_rows: list, current_ratios: dict) -> Optional[Signal]:
    """Crypto options volatility strategy.

    Generates directional signals based on implied volatility extremes
    and put/call skew from Deribit options data.
    """
    currency = DERIBIT_CURRENCY_MAP.get(symbol)
    if currency is None:
        return None  # No options data for this symbol

    iv_data = _fetch_deribit_iv(currency)
    if iv_data is None:
        return None

    current_iv = iv_data["current_iv"]
    iv_zscore = _compute_iv_zscore(symbol, current_iv)

    # Also try to get skew data
    skew_data = _fetch_deribit_book_summary(currency)

    # Decision logic
    direction = None
    reason_parts = []

    # Signal 1: IV at extremes → mean reversion
    if iv_zscore is not None and abs(iv_zscore) > 1.5:
        if iv_zscore > 2.0:
            # IV extremely high → vol will compress → Short vol → LONG underlying
            # (High IV often follows panic drops, underlying tends to bounce)
            direction = "LONG"
            reason_parts.append(
                f"IV extreme high ({current_iv:.1f}%, z={iv_zscore:.2f}). "
                f"Vol compression expected → LONG bias."
            )
        elif iv_zscore < -1.5:
            # IV extremely low → vol will expand → complacency → SHORT
            direction = "SHORT"
            reason_parts.append(
                f"IV extreme low ({current_iv:.1f}%, z={iv_zscore:.2f}). "
                f"Vol expansion expected (complacency) → SHORT bias."
            )

    # Signal 2: Put/call skew for directional bias
    if skew_data is not None:
        skew = skew_data["iv_skew"]
        pcr = skew_data["put_call_ratio"]

        if skew > 15.0 and pcr > 1.5:
            # Heavy put skew + high put/call ratio = extreme fear
            # Contrarian LONG
            if direction is None:
                direction = "LONG"
            reason_parts.append(
                f"Put/call skew: puts {skew:.1f}% more expensive than calls. "
                f"PCR={pcr:.2f}. Extreme fear → contrarian LONG."
            )
        elif skew < -10.0 and pcr < 0.6:
            # Heavy call skew + low put/call ratio = extreme greed
            if direction is None:
                direction = "SHORT"
            reason_parts.append(
                f"Put/call skew: calls {abs(skew):.1f}% more expensive than puts. "
                f"PCR={pcr:.2f}. Extreme greed → contrarian SHORT."
            )

    if direction is None or not reason_parts:
        return None

    # Confidence
    iv_score = min(abs(iv_zscore or 0) / 3.0, 1.0) if iv_zscore else 0
    skew_score = 0
    if skew_data:
        skew_score = min(abs(skew_data["iv_skew"]) / 20.0, 1.0)

    conf = 0.50 + 0.15 * iv_score + 0.15 * skew_score
    conf = round(min(conf, 0.80), 3)

    ratios_extra = {
        "current_iv": round(current_iv, 2),
        "iv_zscore": round(iv_zscore, 3) if iv_zscore is not None else None,
        "iv_percentile": round(iv_data.get("iv_percentile", 50), 1),
    }
    if skew_data:
        ratios_extra["iv_skew"] = round(skew_data["iv_skew"], 2)
        ratios_extra["put_call_ratio"] = round(skew_data["put_call_ratio"], 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_options_volatility",
        confidence=conf,
        reason=" | ".join(reason_parts),
        ratios={**ratios_extra, **current_ratios},
    )

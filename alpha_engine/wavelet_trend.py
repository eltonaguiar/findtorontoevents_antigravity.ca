#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Wavelet Transform Trend Detection
===================================================
Decomposes price series into trend (approximation) and noise (detail)
components using wavelet transforms.  Uses PyWavelets (pywt) when
available; falls back to a manual Haar wavelet implementation so the
module works with stdlib + numpy only.

Key functions:
  detect_trend_wavelet  -- trend direction/strength from wavelet decomposition
  wavelet_momentum      -- normalized momentum from denoised trend
  get_wavelet_signal    -- combined trading signal (BUY/SELL/HOLD)

Stdlib + numpy only (pywt is optional).  Windows UTF-8 safe.
"""

from __future__ import annotations

import math
import sys
from typing import Any

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pywt  # type: ignore
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False


# ---------------------------------------------------------------------------
# Manual Haar wavelet (fallback when pywt is not installed)
# ---------------------------------------------------------------------------

def _haar_decompose_one_level(signal: list[float]) -> tuple[list[float], list[float]]:
    """Single-level Haar wavelet decomposition.

    Returns (approximation_coeffs, detail_coeffs).
    If the signal length is odd, the last sample is carried into approx.
    """
    n = len(signal)
    approx: list[float] = []
    detail: list[float] = []
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    for i in range(0, n - 1, 2):
        a = (signal[i] + signal[i + 1]) * inv_sqrt2
        d = (signal[i] - signal[i + 1]) * inv_sqrt2
        approx.append(a)
        detail.append(d)
    # Carry odd trailing sample
    if n % 2 == 1:
        approx.append(signal[-1] * inv_sqrt2)
    return approx, detail


def _haar_reconstruct_one_level(approx: list[float], detail: list[float],
                                 original_len: int) -> list[float]:
    """Single-level Haar inverse transform."""
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    result: list[float] = []
    for i in range(len(detail)):
        s = (approx[i] + detail[i]) * inv_sqrt2
        d = (approx[i] - detail[i]) * inv_sqrt2
        result.append(s)
        result.append(d)
    if original_len % 2 == 1 and len(approx) > len(detail):
        result.append(approx[-1] * inv_sqrt2)
    return result[:original_len]


def _haar_wavedec(signal: list[float], level: int) -> list[list[float]]:
    """Multi-level Haar decomposition.

    Returns [cA_n, cD_n, cD_{n-1}, ..., cD_1] matching pywt.wavedec ordering.
    """
    coeffs_details: list[list[float]] = []
    current = list(signal)
    lengths: list[int] = []
    for _ in range(level):
        if len(current) < 2:
            break
        lengths.append(len(current))
        approx, detail = _haar_decompose_one_level(current)
        coeffs_details.append(detail)
        current = approx
    # Return format: [approx, detail_n, detail_{n-1}, ..., detail_1]
    return [current] + coeffs_details


def _haar_waverec(coeffs: list[list[float]], original_len: int) -> list[float]:
    """Multi-level Haar reconstruction from [cA_n, cD_n, ..., cD_1]."""
    if len(coeffs) < 2:
        return list(coeffs[0]) if coeffs else []

    current = list(coeffs[0])
    # Reconstruct from deepest level to shallowest
    # We need to figure out the lengths at each level
    # Work backwards: coeffs[1] is cD_n (deepest detail), coeffs[-1] is cD_1
    for i in range(1, len(coeffs)):
        detail = coeffs[i]
        target_len = len(detail) * 2
        # For the last level, use original_len
        if i == len(coeffs) - 1:
            target_len = original_len
        current = _haar_reconstruct_one_level(current, detail, target_len)
    return current


# ---------------------------------------------------------------------------
# Core: wavelet decomposition (pywt with db4 or Haar fallback)
# ---------------------------------------------------------------------------

def _decompose(closes: list[float], level: int = 3
               ) -> tuple[list[float], list[list[float]], int]:
    """Decompose closes into approximation + detail coefficients.

    Returns: (approx_coeffs, [detail_coeffs...], original_length)
    Uses pywt db4 wavelet when available; manual Haar otherwise.
    """
    orig_len = len(closes)

    if HAS_PYWT:
        # Use db4 with 3-level decomposition
        arr = np.array(closes, dtype=float) if HAS_NUMPY else closes
        try:
            coeffs = pywt.wavedec(arr, "db4", level=level)
        except Exception:
            # If db4 fails (e.g., signal too short), fall back to haar
            coeffs = pywt.wavedec(arr, "haar", level=level)
        approx = list(coeffs[0]) if not isinstance(coeffs[0], list) else coeffs[0]
        details = [list(c) if not isinstance(c, list) else c for c in coeffs[1:]]
        return approx, details, orig_len

    # Manual Haar fallback
    coeffs = _haar_wavedec(closes, level)
    approx = coeffs[0]
    details = coeffs[1:]
    return approx, details, orig_len


def _reconstruct_denoised(approx: list[float], details: list[list[float]],
                           orig_len: int) -> list[float]:
    """Reconstruct denoised signal (zero out detail coefficients)."""
    if HAS_PYWT:
        # Zero out all detail coefficients for a smooth trend
        zeroed = [approx] + [[0.0] * len(d) for d in details]
        if HAS_NUMPY:
            zeroed_np = [np.array(c) for c in zeroed]
        else:
            zeroed_np = zeroed
        try:
            rec = pywt.waverec(zeroed_np, "db4")
        except Exception:
            rec = pywt.waverec(zeroed_np, "haar")
        result = list(rec)
        # pywt may return slightly different length; trim/pad
        if len(result) > orig_len:
            result = result[:orig_len]
        elif len(result) < orig_len:
            result = result + [result[-1]] * (orig_len - len(result))
        return result

    # Manual Haar reconstruction with zeroed details
    zeroed_coeffs = [approx] + [[0.0] * len(d) for d in details]
    result = _haar_waverec(zeroed_coeffs, orig_len)
    if len(result) > orig_len:
        result = result[:orig_len]
    elif len(result) < orig_len:
        result = result + [result[-1]] * (orig_len - len(result))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_trend_wavelet(closes: list[float], timeframe: str = "4h") -> dict:
    """Decompose price into trend + noise via wavelet transform.

    Args:
        closes: List of closing prices (minimum ~16 values recommended).
        timeframe: Candle timeframe hint (for future multi-TF support).

    Returns:
        {
            "trend_direction": "bullish" | "bearish" | "neutral",
            "trend_strength": float (0-1),
            "denoised_prices": list[float],
            "noise_ratio": float (0-1),
        }
    """
    default = {
        "trend_direction": "neutral",
        "trend_strength": 0.0,
        "denoised_prices": list(closes) if closes else [],
        "noise_ratio": 0.0,
    }

    if not closes or len(closes) < 8:
        return default

    try:
        approx, details, orig_len = _decompose(closes, level=3)
        denoised = _reconstruct_denoised(approx, details, orig_len)

        # --- Trend direction from denoised slope ---
        lookback = min(10, len(denoised) - 1)
        if lookback < 2:
            return default

        recent = denoised[-lookback:]
        slope = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-12)

        # Normalize slope to strength (0-1) using a sigmoid-like mapping
        # Typical 4h slope magnitudes: 0.01 = weak, 0.05 = moderate, 0.1+ = strong
        raw_strength = abs(slope)
        # Scale factor depends on timeframe
        scale = {"1h": 60, "4h": 30, "1d": 15, "1w": 8}.get(timeframe, 30)
        trend_strength = min(1.0, raw_strength * scale)

        if slope > 0.002:
            direction = "bullish"
        elif slope < -0.002:
            direction = "bearish"
        else:
            direction = "neutral"

        # --- Noise ratio: energy in details vs total energy ---
        detail_energy = 0.0
        for d in details:
            for v in d:
                detail_energy += v * v
        total_energy = detail_energy
        for v in approx:
            total_energy += v * v
        noise_ratio = detail_energy / max(total_energy, 1e-12)
        noise_ratio = min(1.0, max(0.0, noise_ratio))

        return {
            "trend_direction": direction,
            "trend_strength": round(trend_strength, 4),
            "denoised_prices": [round(p, 6) for p in denoised],
            "noise_ratio": round(noise_ratio, 4),
        }

    except Exception:
        return default


def wavelet_momentum(closes: list[float]) -> float:
    """Compute normalized momentum from the denoised trend component.

    Returns a value in [-1, 1]:
        > 0 = bullish momentum
        < 0 = bearish momentum
        ~0  = flat / no momentum
    """
    if not closes or len(closes) < 8:
        return 0.0

    try:
        result = detect_trend_wavelet(closes, timeframe="4h")
        denoised = result.get("denoised_prices", [])
        if len(denoised) < 4:
            return 0.0

        # Rate of change over last 5 denoised bars, normalized
        lookback = min(5, len(denoised) - 1)
        recent = denoised[-lookback - 1:]
        roc = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-12)

        # Map to [-1, 1] using tanh-like function
        # roc of 0.05 (~5%) maps to ~0.7 momentum
        momentum = math.tanh(roc * 15.0)
        return round(max(-1.0, min(1.0, momentum)), 4)

    except Exception:
        return 0.0


def get_wavelet_signal(symbol: str, closes: list[float]) -> dict:
    """Combine wavelet trend detection + momentum into a trading signal.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT").
        closes: List of closing prices.

    Returns:
        {
            "signal": "BUY" | "SELL" | "HOLD",
            "confidence": float (0-1),
            "trend_direction": str,
            "momentum": float,
            "noise_ratio": float,
        }
    """
    default = {
        "signal": "HOLD",
        "confidence": 0.0,
        "trend_direction": "neutral",
        "momentum": 0.0,
        "noise_ratio": 0.0,
    }

    if not closes or len(closes) < 8:
        return default

    try:
        trend = detect_trend_wavelet(closes, timeframe="4h")
        mom = wavelet_momentum(closes)

        direction = trend["trend_direction"]
        strength = trend["trend_strength"]
        noise = trend["noise_ratio"]

        # --- Signal logic ---
        # High noise = low confidence regardless of trend
        noise_penalty = max(0.0, 1.0 - noise * 1.5)

        # Combine trend strength + momentum agreement
        if direction == "bullish" and mom > 0.1:
            signal = "BUY"
            raw_conf = (strength * 0.6 + abs(mom) * 0.4)
        elif direction == "bearish" and mom < -0.1:
            signal = "SELL"
            raw_conf = (strength * 0.6 + abs(mom) * 0.4)
        else:
            signal = "HOLD"
            raw_conf = 0.3 * strength

        confidence = round(min(1.0, raw_conf * noise_penalty), 4)

        return {
            "signal": signal,
            "confidence": confidence,
            "trend_direction": direction,
            "momentum": mom,
            "noise_ratio": trend["noise_ratio"],
        }

    except Exception:
        return default


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    random.seed(42)

    # Generate a synthetic uptrend with noise
    base = [100.0 + i * 0.5 for i in range(50)]
    noisy = [p + random.gauss(0, 2.0) for p in base]

    print(f"pywt available: {HAS_PYWT}")
    print(f"numpy available: {HAS_NUMPY}")
    print(f"Input: {len(noisy)} candles, range {min(noisy):.2f} - {max(noisy):.2f}")
    print()

    trend = detect_trend_wavelet(noisy)
    print(f"Trend: {trend['trend_direction']} (strength={trend['trend_strength']:.3f})")
    print(f"Noise ratio: {trend['noise_ratio']:.3f}")
    print()

    mom = wavelet_momentum(noisy)
    print(f"Momentum: {mom:.4f}")
    print()

    sig = get_wavelet_signal("BTCUSDT", noisy)
    print(f"Signal: {sig['signal']} (confidence={sig['confidence']:.3f})")

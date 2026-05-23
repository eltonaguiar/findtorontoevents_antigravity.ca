"""Phase 7: Swing trade screener (trend + momentum + volume + earnings catalyst).

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows + Phase 11 dashboard.

Composite (verbatim from SYNTHESIS.md §3):

    SwingScore = 0.30 * TrendScore
               + 0.30 * MomentumScore
               + 0.20 * VolumeScore
               + 0.20 * CatalystScore

Quality bands:
    strong   if SwingScore >= 0.75 AND TrendScore >= 0.7
    moderate if SwingScore >= 0.55
    weak     if SwingScore >= 0.35
    reject   otherwise

TP/SL defaults:
    TP +7%, SL -1.5%.
    If MomentumScore > 0.85 -> TP +10%, SL -1.0%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from alpha_engine.long_term_pick_contract import make_swing_pick

SignalQuality = Literal["strong", "moderate", "weak", "reject"]

# Composite weights
W_TREND: float = 0.30
W_MOMENTUM: float = 0.30
W_VOLUME: float = 0.20
W_CATALYST: float = 0.20

# Quality thresholds
STRONG_TOTAL_THRESHOLD: float = 0.75
STRONG_TREND_THRESHOLD: float = 0.7
MODERATE_THRESHOLD: float = 0.55
WEAK_THRESHOLD: float = 0.35

# TP/SL defaults
DEFAULT_TP_PCT: float = 0.07
DEFAULT_SL_PCT: float = 0.015
HIGH_MOMENTUM_TP_PCT: float = 0.10
HIGH_MOMENTUM_SL_PCT: float = 0.01
HIGH_MOMENTUM_THRESHOLD: float = 0.85


# =============================================================================
# Dataclasses
# =============================================================================
@dataclass
class OHLCVWindow:
    """Single-ticker OHLCV window. closes/volumes are oldest-first."""
    ticker: str
    closes: list[float]
    volumes: list[int]
    current_price: float


@dataclass
class SwingScore:
    """Output of scoring one OHLCVWindow."""
    ticker: str
    total_score: float
    trend_score: float
    momentum_score: float
    volume_score: float
    catalyst_score: float
    current_price: float
    target_tp: float
    target_sl: float
    signal_quality: SignalQuality
    rejection_reason: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Pure-function technical indicators
# =============================================================================
def compute_ema(values: list[float], period: int) -> list[float]:
    """Standard exponential moving average (seeded with SMA of first `period`).

    Returns list with len == len(values); positions before `period` are filled
    with the seed SMA value (or 0.0 if `values` is empty).
    """
    if not values or period <= 0:
        return []
    if len(values) < period:
        # Not enough data for a proper seed -> return SMA of available values
        sma = sum(values) / len(values)
        return [sma] * len(values)
    alpha = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out: list[float] = [seed] * period
    prev = seed
    for v in values[period:]:
        cur = alpha * v + (1 - alpha) * prev
        out.append(cur)
        prev = cur
    return out


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder-smoothed RSI, latest value only. Needs >= period+1 closes."""
    if len(closes) < period + 1:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    # Wilder smoothing: seed with simple average over first `period`, then EMA
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd_signal(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None]:
    """Return (macd_line, signal_line) for the last bar, or (None, None)."""
    if len(closes) < slow + signal:
        return (None, None)
    ema_fast = compute_ema(closes, fast)
    ema_slow = compute_ema(closes, slow)
    macd_series = [f - s for f, s in zip(ema_fast, ema_slow)]
    sig_series = compute_ema(macd_series, signal)
    return (macd_series[-1], sig_series[-1])


def compute_volume_ratio(
    volumes: list[int], lookback: int = 20
) -> float | None:
    """Latest volume divided by lookback-bar average. None if not enough bars."""
    if len(volumes) < lookback + 1:
        return None
    avg = sum(volumes[-(lookback + 1):-1]) / lookback
    if avg <= 0:
        return None
    return float(volumes[-1]) / avg


# =============================================================================
# Sub-score helpers
# =============================================================================
def compute_trend_score(window: OHLCVWindow) -> float:
    """Trend score in [0,1]. Uses EMA20 vs EMA50 alignment + price position."""
    closes = window.closes
    if not closes:
        return 0.0
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)
    if not ema20 or not ema50:
        return 0.0
    last_price = closes[-1]
    score = 0.0
    # Price > EMA20
    if last_price > ema20[-1]:
        score += 0.4
    # EMA20 > EMA50
    if ema20[-1] > ema50[-1]:
        score += 0.4
    # EMA20 rising (last > 5 bars ago)
    if len(ema20) >= 6 and ema20[-1] > ema20[-6]:
        score += 0.2
    return min(1.0, score)


def compute_momentum_score(window: OHLCVWindow) -> float:
    """Momentum score in [0,1] using RSI + MACD vs signal."""
    closes = window.closes
    if not closes:
        return 0.0
    rsi = compute_rsi(closes, 14)
    macd_line, signal_line = compute_macd_signal(closes)
    score = 0.0
    if rsi is not None:
        # Sweet-spot 50..70 -> full credit; >70 reduced (overbought); <50 reduced
        if 50 <= rsi <= 70:
            score += 0.5
        elif 70 < rsi <= 80:
            score += 0.3
        elif 40 <= rsi < 50:
            score += 0.25
        elif rsi > 80:
            score += 0.1
        else:
            score += 0.0
    if macd_line is not None and signal_line is not None:
        if macd_line > signal_line:
            score += 0.4
        if macd_line > 0:
            score += 0.1
    return min(1.0, score)


def compute_volume_score(window: OHLCVWindow) -> float:
    """Volume score in [0,1] using current/lookback ratio."""
    ratio = compute_volume_ratio(window.volumes, lookback=20)
    if ratio is None:
        return 0.0
    if ratio >= 3.0:
        return 1.0
    if ratio >= 2.0:
        return 0.8
    if ratio >= 1.5:
        return 0.6
    if ratio >= 1.0:
        return 0.4
    return 0.2


def compute_catalyst_score(
    earnings: Any | None, days_ahead: int = 30
) -> float:
    """Catalyst score in [0,1] based on proximity to next earnings date.

    Within 5 days -> 1.0
    Within 14 days -> 0.7
    Within `days_ahead` -> 0.4
    Beyond / unknown -> 0.0
    """
    if earnings is None:
        return 0.0
    next_date_str = getattr(earnings, "next_earnings_date", None)
    if not next_date_str:
        return 0.0
    try:
        # Accept ISO date or full ISO datetime
        if "T" in next_date_str:
            next_dt = datetime.fromisoformat(next_date_str.replace("Z", "+00:00"))
        else:
            next_dt = datetime.fromisoformat(next_date_str)
        if next_dt.tzinfo is None:
            next_dt = next_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0
    delta_days = (next_dt - datetime.now(timezone.utc)).total_seconds() / 86400.0
    if delta_days < 0:
        return 0.0
    if delta_days <= 5:
        return 1.0
    if delta_days <= 14:
        return 0.7
    if delta_days <= days_ahead:
        return 0.4
    return 0.0


# =============================================================================
# Quality + TP/SL helpers
# =============================================================================
def _classify_quality(total: float, trend: float) -> SignalQuality:
    if total >= STRONG_TOTAL_THRESHOLD and trend >= STRONG_TREND_THRESHOLD:
        return "strong"
    if total >= MODERATE_THRESHOLD:
        return "moderate"
    if total >= WEAK_THRESHOLD:
        return "weak"
    return "reject"


def _compute_tp_sl(price: float, momentum: float) -> tuple[float, float]:
    if momentum > HIGH_MOMENTUM_THRESHOLD:
        return (price * (1.0 + HIGH_MOMENTUM_TP_PCT),
                price * (1.0 - HIGH_MOMENTUM_SL_PCT))
    return (price * (1.0 + DEFAULT_TP_PCT),
            price * (1.0 - DEFAULT_SL_PCT))


_QUALITY_RANK: dict[str, int] = {
    "strong": 3, "moderate": 2, "weak": 1, "reject": 0,
}


# =============================================================================
# SwingScreener facade
# =============================================================================
class SwingScreener:
    """Orchestrates per-ticker scoring + pick emission."""

    def __init__(self, earnings_fetcher: Any | None = None):
        self.earnings_fetcher = earnings_fetcher

    def score_one(
        self, window: OHLCVWindow, earnings: Any | None = None
    ) -> SwingScore:
        trend = compute_trend_score(window)
        momentum = compute_momentum_score(window)
        volume = compute_volume_score(window)
        catalyst = compute_catalyst_score(earnings) if earnings is not None else 0.0
        total = (W_TREND * trend + W_MOMENTUM * momentum +
                 W_VOLUME * volume + W_CATALYST * catalyst)
        quality = _classify_quality(total, trend)
        tp, sl = _compute_tp_sl(window.current_price, momentum)
        rejection = "low_score" if quality == "reject" else None
        return SwingScore(
            ticker=window.ticker,
            total_score=total,
            trend_score=trend,
            momentum_score=momentum,
            volume_score=volume,
            catalyst_score=catalyst,
            current_price=window.current_price,
            target_tp=tp,
            target_sl=sl,
            signal_quality=quality,
            rejection_reason=rejection,
            extra={
                "rsi": compute_rsi(window.closes, 14),
                "volume_ratio": compute_volume_ratio(window.volumes, 20),
            },
        )

    def screen_universe(
        self,
        windows: list[OHLCVWindow],
        earnings_map: dict[str, Any] | None = None,
        top_n: int = 20,
        min_quality: SignalQuality = "moderate",
    ) -> list[dict[str, Any]]:
        """Score and emit picks via factory. Filters by min_quality + top_n."""
        emap = earnings_map or {}
        scored: list[SwingScore] = []
        for w in windows:
            scored.append(self.score_one(w, earnings=emap.get(w.ticker)))

        min_rank = _QUALITY_RANK[min_quality]
        eligible = [s for s in scored if _QUALITY_RANK[s.signal_quality] >= min_rank]
        eligible.sort(key=lambda s: s.total_score, reverse=True)
        eligible = eligible[:top_n]

        picks: list[dict[str, Any]] = []
        for s in eligible:
            earnings = emap.get(s.ticker)
            next_earnings_date = (
                getattr(earnings, "next_earnings_date", None) if earnings else None
            )
            catalyst_dates = [next_earnings_date] if next_earnings_date else []
            earnings_history = (
                list(getattr(earnings, "history", []) or []) if earnings else []
            )
            pick = make_swing_pick(
                symbol=s.ticker,
                direction="LONG",
                entry_price=s.current_price,
                take_profit=s.target_tp,
                stop_loss=s.target_sl,
                next_earnings_date=next_earnings_date,
                catalyst_dates=catalyst_dates,
                earnings_history=earnings_history,
                score=s.total_score,
                extra={
                    "trend_score": s.trend_score,
                    "momentum_score": s.momentum_score,
                    "volume_score": s.volume_score,
                    "catalyst_score": s.catalyst_score,
                    "signal_quality": s.signal_quality,
                    "rsi": s.extra.get("rsi"),
                    "volume_ratio": s.extra.get("volume_ratio"),
                },
            )
            picks.append(pick)
        return picks

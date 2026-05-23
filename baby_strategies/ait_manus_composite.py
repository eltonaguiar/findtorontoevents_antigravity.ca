"""
ManusCompositeStrategy — ait_manus_composite
=============================================

Reverse-engineered from raftapart/Manus AI strategy posts on ai4trade.ai
(research 2026-04-14 in .tmp-ai4trade/FINDINGS.md).

Observed architecture:
    score = w_ta·TA + w_news·News + w_macro·Macro + w_community·Community
    signal = BUY        if score >=  4
           = LIGHT_SELL if score <= -2
           = NEUTRAL    otherwise

All four weights default to 1.0, matching the observed state of the original
(which on ai4trade also runs uniform weights with `Total evaluations: 0`).

This module uses OUR data sources — never calls the ai4trade API. Every factor
function is fault-tolerant and returns 0 when its upstream source is unavailable,
so a partial outage degrades the composite gracefully instead of hard-failing.

NOT auto-wired into the scanner. To activate, register in
alpha_engine/antigravity_strategies.py after reviewing the first dry-run output.

See docs/superpowers/specs/2026-04-14-ait-manus-composite-design.md.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Defensive bounds for the composite score. A runaway weight config should
# not push the score past ±20; clamp anything outside as a sanity check.
_SCORE_CLAMP = 20.0


# ---------------------------------------------------------------------------
# Public signal dataclass (same shape as other baby_strategies)
# ---------------------------------------------------------------------------
@dataclass
class Signal:
    symbol: str
    direction: str          # "BUY" | "SELL" | "NEUTRAL"
    confidence: float       # 50..95
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


NAME = "ait_manus_composite"
DESCRIPTION = "4-factor composite (TA+News+Macro+Community) reverse-engineered from Manus AI on ai4trade.ai"

# Weights. Uniform 1.0 by design — matches observed Manus state.
DEFAULT_WEIGHTS = {"ta": 1.0, "news": 1.0, "macro": 1.0, "community": 1.0}

# Score thresholds (from observed Manus posts on ai4trade.ai).
BUY_THRESHOLD = 4.0
SELL_THRESHOLD = -2.0

# Fixed exit ratios. Intentionally conservative and deliberately generic —
# Manus posts never disclose exits, so we pick something that lets the
# forward-validation pipeline score the strategy at all.
TP_RATIO = 1.03   # +3%
SL_RATIO = 0.985  # -1.5%


# ---------------------------------------------------------------------------
# Factor 1: TA (RSI-based, trivial)
# ---------------------------------------------------------------------------
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - 100 / (1 + rs)


def ta_factor(df: pd.DataFrame) -> int:
    """Return a TA score in {-3, -1, 0, +1, +3} based on the latest RSI(14).

    A zero-variance close series (no price movement at all) returns 0
    rather than the degenerate RSI=0 that the formula produces.
    """
    try:
        if df is None or len(df) < 20 or "Close" not in df.columns:
            logger.debug("ta_factor: insufficient data, returning 0")
            return 0
        close = df["Close"]
        if float(close.std()) == 0:
            logger.debug("ta_factor: zero-variance close, returning 0")
            return 0
        rsi_last = float(_rsi(close).iloc[-1])
    except Exception as e:
        logger.debug("ta_factor: exception %r, returning 0", e)
        return 0
    if rsi_last < 30:
        score = 3
    elif rsi_last < 40:
        score = 1
    elif rsi_last > 70:
        score = -3
    elif rsi_last > 60:
        score = -1
    else:
        score = 0
    logger.debug("ta_factor: rsi=%.2f score=%d", rsi_last, score)
    return score


# ---------------------------------------------------------------------------
# Factor 2: News (CryptoPanic sentiment)
# ---------------------------------------------------------------------------
def news_factor(symbol: str) -> int:
    """Return a news sentiment score in {-2, 0, +2}.

    Maps the repo's cryptopanic_feargreed classifier output:
      positive -> +2
      negative -> -2
      neutral/unknown/error -> 0
    """
    try:
        from alpha_engine.cryptopanic_feargreed import fetch_cryptopanic_news, _classify_sentiment
    except Exception as e:
        logger.debug("news_factor: import failed %r, returning 0", e)
        return 0
    currency = symbol.replace("USDT", "").replace("-USD", "").replace("USD", "").upper()
    if not currency:
        logger.debug("news_factor: empty currency for %r, returning 0", symbol)
        return 0
    try:
        data = fetch_cryptopanic_news(currencies=currency)
    except Exception as e:
        logger.debug("news_factor(%s): fetch exception %r, returning 0", currency, e)
        return 0
    if not isinstance(data, dict):
        logger.debug("news_factor(%s): non-dict response, returning 0", currency)
        return 0
    votes = data.get("votes") or data.get("aggregate_votes") or {}
    try:
        label = _classify_sentiment(votes)
    except Exception as e:
        logger.debug("news_factor(%s): classify exception %r, returning 0", currency, e)
        return 0
    if label == "positive":
        logger.debug("news_factor(%s): positive -> +2", currency)
        return 2
    if label == "negative":
        logger.debug("news_factor(%s): negative -> -2", currency)
        return -2
    logger.debug("news_factor(%s): %s -> 0", currency, label)
    return 0


# ---------------------------------------------------------------------------
# Factor 3: Macro (regime_terminal HMM market overview)
# ---------------------------------------------------------------------------
_REGIME_STATE_PATH = Path("regime_terminal/data/regime_state.json")

# In-process cache keyed by (path, mtime). Invalidates automatically when the
# regime file is rewritten by the HMM job.
_regime_cache: dict[tuple[str, float], int] = {}


def macro_factor(regime_path: Path | None = None) -> int:
    """Return a macro score in {-2, 0, +2} from the HMM market overview.

    Reads regime_terminal/data/regime_state.json. Compares bull_count vs
    bear_count with a cushion of 3. Returns 0 if the file is stale (>24h old),
    missing, or malformed. Cached per (path, mtime) to avoid repeated file
    reads inside a single scan pass.
    """
    path = regime_path or _REGIME_STATE_PATH
    try:
        if not path.exists():
            logger.debug("macro_factor: regime file %s missing, returning 0", path)
            return 0
        mtime = path.stat().st_mtime
        key = (str(path), mtime)
        if key in _regime_cache:
            return _regime_cache[key]
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("macro_factor: read exception %r, returning 0", e)
        return 0
    generated = raw.get("generated_at") or raw.get("updated_at")
    if generated:
        try:
            ts = datetime.fromisoformat(generated.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_hours > 24:
                logger.debug("macro_factor: regime file %.1fh stale, returning 0", age_hours)
                _regime_cache[key] = 0
                return 0
        except Exception:
            pass
    overview = raw.get("market_overview") or {}
    bull = int(overview.get("bull_count", 0) or 0)
    bear = int(overview.get("bear_count", 0) or 0)
    if bull > bear + 3:
        score = 2
    elif bear > bull + 3:
        score = -2
    else:
        score = 0
    logger.debug("macro_factor: bull=%d bear=%d score=%d", bull, bear, score)
    _regime_cache[key] = score
    return score


# ---------------------------------------------------------------------------
# Factor 4: Community (LunarCrush / free social sentiment)
# ---------------------------------------------------------------------------
def community_factor(symbol: str) -> int:
    """Return a community sentiment score in {-2, -1, 0, +1, +2}.

    Bucketed from the repo's lunarcrush_signal galaxy_score (0..100).
    """
    try:
        from alpha_engine.lunarcrush_signal import get_lunarcrush_score
    except Exception:
        return 0
    try:
        result = get_lunarcrush_score(symbol)
    except Exception:
        return 0
    if not isinstance(result, dict):
        return 0
    score = result.get("galaxy_score") or result.get("score") or result.get("composite")
    if score is None:
        return 0
    try:
        s = float(score)
    except Exception:
        return 0
    if s >= 70:
        return 2
    if s >= 55:
        return 1
    if s <= 30:
        return -2
    if s <= 45:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------
def compute_score(
    ta: int,
    news: int,
    macro: int,
    community: int,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    raw = (
        w.get("ta", 1.0) * ta
        + w.get("news", 1.0) * news
        + w.get("macro", 1.0) * macro
        + w.get("community", 1.0) * community
    )
    if raw > _SCORE_CLAMP or raw < -_SCORE_CLAMP:
        logger.warning("compute_score: raw %.2f outside [%.0f, %.0f], clamping",
                       raw, -_SCORE_CLAMP, _SCORE_CLAMP)
    return max(-_SCORE_CLAMP, min(_SCORE_CLAMP, raw))


def score_to_signal(
    score: float,
    buy_threshold: float = BUY_THRESHOLD,
    sell_threshold: float = SELL_THRESHOLD,
) -> str:
    if score >= buy_threshold:
        return "BUY"
    if score <= sell_threshold:
        return "SELL"
    return "NEUTRAL"


def _confidence_from_score(score: float) -> float:
    """Clamp score magnitude to a 50..95 confidence band."""
    mag = min(abs(score), 12)
    return round(50 + (mag / 12) * 45, 1)


# ---------------------------------------------------------------------------
# Strategy class
# ---------------------------------------------------------------------------
class ManusCompositeStrategy:
    def __init__(self, weights: dict[str, float] | None = None,
                 buy_threshold: float = BUY_THRESHOLD,
                 sell_threshold: float = SELL_THRESHOLD,
                 regime_path: Path | None = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.regime_path = regime_path

    @classmethod
    def from_meta(cls, meta_path: Path) -> "ManusCompositeStrategy":
        """Construct a strategy instance from a meta.json file.

        Reads the optional `runtime` block:
            {
              "runtime": {
                "weights": {"ta": 1.0, "news": 1.0, "macro": 1.0, "community": 1.0},
                "buy_threshold": 4.0,
                "sell_threshold": -2.0
              }
            }
        Missing fields fall back to module defaults. Raises FileNotFoundError
        if the meta file is missing — this is a config-time call, not a
        runtime call, so we fail loudly instead of degrading.
        """
        raw = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        runtime = raw.get("runtime") or {}
        return cls(
            weights=runtime.get("weights"),
            buy_threshold=float(runtime.get("buy_threshold", BUY_THRESHOLD)),
            sell_threshold=float(runtime.get("sell_threshold", SELL_THRESHOLD)),
        )

    def scan_symbol(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Score ONE symbol. Returns a Signal or None for NEUTRAL / bad input."""
        if df is None or len(df) < 20 or "Close" not in df.columns:
            return None
        ta = ta_factor(df)
        news = news_factor(symbol)
        macro = macro_factor(self.regime_path)
        community = community_factor(symbol)
        score = compute_score(ta, news, macro, community, self.weights)
        direction = score_to_signal(score, self.buy_threshold, self.sell_threshold)
        if direction == "NEUTRAL":
            return None
        entry = float(df["Close"].iloc[-1])
        if direction == "BUY":
            tp = entry * TP_RATIO
            sl = entry * SL_RATIO
        else:
            tp = entry * (2 - TP_RATIO)
            sl = entry * (2 - SL_RATIO)
        reason = (f"manus score={score:.1f} "
                  f"TA={ta:+d} news={news:+d} macro={macro:+d} community={community:+d}")
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=_confidence_from_score(score),
            entry_price=entry,
            take_profit=round(tp, 6),
            stop_loss=round(sl, 6),
            reason=reason,
        )

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Scanner-adapter compatible entry point. Returns [] or [Signal]."""
        sig = self.scan_symbol(df, symbol)
        return [sig] if sig is not None else []

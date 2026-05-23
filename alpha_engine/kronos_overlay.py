"""
Kronos Foundation-Model Overlay Sidecar
========================================

Opt-in sidecar that uses the Kronos decoder-only transformer
(https://github.com/shiyu-coder/Kronos, MIT) as a directional confidence
multiplier on top of existing pick generation.

Kronos is a foundation model pre-trained on OHLCV data across 45+ exchanges,
available in mini (4.1M) / small (24.7M) / base (102.3M) / large (499.2M)
parameter variants. We do NOT bake any weights into this repo — torch +
kronos must be installed manually by the operator. If they aren't installed,
this module degrades to a no-op (`multiplier = 1.0`) so wiring it into the
production pipeline cannot break anything.

Wire-up plan (NOT YET ACTIVE — opt-in only)
-------------------------------------------
Target call site: `alpha_engine/feed_hygiene.py`, immediately AFTER the
existing Polymarket vol-filter v2 step (the last enrichment pass before
picks reach `score_pick`/`smart_picks_engine`). Invocation will be guarded
by `KRONOS_OVERLAY_ENABLED=1` AND a forward-validated tier-bump report
under `docs/strategy-audit-rounds/kronos_overlay/performance-report.json`.

Until the wiring lands, this module is a free-standing sidecar that can
be exercised from `__main__` (synthetic backtest) or unit tests.

Rollback envs
-------------
- `KRONOS_OVERLAY_DISABLED=1` — skip the overlay entirely (returns picks unchanged)
- `KRONOS_OVERLAY_DRY_RUN=1`  — compute scores + stamp `_kronos_overlay`,
                                 but DO NOT mutate `pick["confidence"]`
                                 (use this for shadow eval before tier-bump)

Contract (per pick)
-------------------
Each scored pick gets a `_kronos_overlay` sub-block:

    {
        "kronos_direction":             "LONG" | "SHORT" | "NEUTRAL" | "UNAVAILABLE",
        "kronos_confidence":            float in [0, 1],
        "kronos_predicted_change_pct":  float (e.g. 0.025 = +2.5%),
        "kronos_agree":                 bool,
        "multiplier":                   float (0.6 .. 1.2)
    }

Multiplier table
----------------
- agree + |Δ| > 2%        → 1.2  (high-conviction agreement)
- agree                   → 1.1
- NEUTRAL forecast        → 1.0  (no signal)
- disagree                → 0.8
- disagree + |Δ| > 2%     → 0.6  (high-conviction disagreement, dampen hard)
- pick missing direction  → 1.0  (cannot evaluate agreement)
"""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy / optional Kronos + torch import
# ---------------------------------------------------------------------------
HAVE_KRONOS = False
_kronos_predictor = None  # populated on first real call

try:  # pragma: no cover - exercised only when torch + kronos are installed
    import torch  # noqa: F401
    import kronos  # noqa: F401
    HAVE_KRONOS = True
except Exception:  # ImportError or any downstream init crash
    HAVE_KRONOS = False


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
NEUTRAL_THRESHOLD_PCT = 0.005   # 0.5% -- below this, call it NEUTRAL
HIGH_CONVICTION_PCT = 0.02      # 2.0% -- triggers 1.2 / 0.6 multipliers
DEFAULT_PRED_LEN = 24           # forecast 24 bars ahead
LRU_MAXSIZE = 512


# ---------------------------------------------------------------------------
# Tiny LRU cache, keyed by (symbol, last_bar_timestamp_ns)
# ---------------------------------------------------------------------------
class _LRU(OrderedDict):
    def __init__(self, maxsize: int = LRU_MAXSIZE):
        super().__init__()
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def get_or_none(self, key):
        if key in self:
            self.hits += 1
            self.move_to_end(key)
            return self[key]
        self.misses += 1
        return None

    def put(self, key, value):
        self[key] = value
        self.move_to_end(key)
        if len(self) > self.maxsize:
            self.popitem(last=False)


_CACHE: _LRU = _LRU()


def reset_cache() -> None:
    """Test helper — drop the LRU."""
    global _CACHE
    _CACHE = _LRU()


# ---------------------------------------------------------------------------
# Predictor injection (tests + offline backtests use this)
# ---------------------------------------------------------------------------
_INJECTED_PREDICTOR = None


def set_predictor(predictor) -> None:
    """
    Inject a predictor with a `.predict(df, x_timestamp, y_timestamp,
    pred_len, T, top_p, sample_count)` signature returning a DataFrame
    whose final row has a `close` column. Used by tests and offline tooling.
    """
    global _INJECTED_PREDICTOR
    _INJECTED_PREDICTOR = predictor


def _resolve_predictor():
    if _INJECTED_PREDICTOR is not None:
        return _INJECTED_PREDICTOR
    if not HAVE_KRONOS:
        return None
    global _kronos_predictor
    if _kronos_predictor is None:  # pragma: no cover - real model load
        try:
            from kronos import KronosPredictor  # type: ignore
            _kronos_predictor = KronosPredictor.from_pretrained("Kronos-small")
        except Exception as exc:
            logger.warning("kronos load failed: %s", exc)
            return None
    return _kronos_predictor


# ---------------------------------------------------------------------------
# Forecast → multiplier
# ---------------------------------------------------------------------------
def _classify(predicted_change_pct: float) -> str:
    if predicted_change_pct > NEUTRAL_THRESHOLD_PCT:
        return "LONG"
    if predicted_change_pct < -NEUTRAL_THRESHOLD_PCT:
        return "SHORT"
    return "NEUTRAL"


def _multiplier_for(pick_direction: str | None,
                    kronos_direction: str,
                    predicted_change_pct: float) -> tuple[float, bool]:
    """Return (multiplier, agree_bool)."""
    if not pick_direction:
        return 1.0, False
    pd_norm = pick_direction.upper().strip()
    if kronos_direction == "NEUTRAL" or kronos_direction == "UNAVAILABLE":
        return 1.0, False
    agree = (pd_norm == kronos_direction)
    high_conv = abs(predicted_change_pct) > HIGH_CONVICTION_PCT
    if agree and high_conv:
        return 1.2, True
    if agree:
        return 1.1, True
    if high_conv:
        return 0.6, False
    return 0.8, False


def _stub_score(pick: dict) -> dict:
    return {
        "kronos_direction": "UNAVAILABLE",
        "kronos_confidence": 0.0,
        "kronos_predicted_change_pct": 0.0,
        "kronos_agree": False,
        "multiplier": 1.0,
        "_stub": True,
    }


def _run_predictor(predictor,
                   ohlcv_df: pd.DataFrame,
                   pred_len: int) -> tuple[float, float]:
    """
    Returns (predicted_change_pct, kronos_confidence_in_0_1).

    Confidence is derived from the magnitude of the predicted move,
    saturating at HIGH_CONVICTION_PCT * 2 (i.e. a 4% predicted move
    counts as max confidence).
    """
    cols_needed = ["open", "high", "low", "close"]
    df = ohlcv_df[[c for c in cols_needed + ["volume", "amount"]
                   if c in ohlcv_df.columns]].copy()

    if "timestamps" in ohlcv_df.columns:
        x_timestamp = pd.to_datetime(ohlcv_df["timestamps"])
    elif isinstance(ohlcv_df.index, pd.DatetimeIndex):
        x_timestamp = ohlcv_df.index
    else:
        x_timestamp = pd.date_range(end=pd.Timestamp.utcnow(),
                                    periods=len(df), freq="h")

    last_ts = pd.Timestamp(x_timestamp[-1])
    y_timestamp = pd.date_range(start=last_ts + pd.Timedelta(hours=1),
                                periods=pred_len, freq="h")

    pred_df = predictor.predict(
        df=df,
        x_timestamp=x_timestamp,
        y_timestamp=y_timestamp,
        pred_len=pred_len,
        T=1.0, top_p=0.9, sample_count=1,
    )

    cur_close = float(df["close"].iloc[-1])
    pred_close = float(pred_df["close"].iloc[-1])
    if cur_close <= 0:
        return 0.0, 0.0
    change_pct = (pred_close - cur_close) / cur_close
    conf = min(1.0, abs(change_pct) / (HIGH_CONVICTION_PCT * 2.0))
    return change_pct, conf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def kronos_score_pick(pick: dict,
                      ohlcv_df: pd.DataFrame | None,
                      pred_len: int = DEFAULT_PRED_LEN) -> dict:
    """
    Score a single pick. Always returns a dict with the contract fields —
    never raises on missing data / predictor / kronos install.
    """
    if os.environ.get("KRONOS_OVERLAY_DISABLED") == "1":
        return _stub_score(pick)

    predictor = _resolve_predictor()
    if predictor is None or ohlcv_df is None or len(ohlcv_df) < 16:
        return _stub_score(pick)

    symbol = (pick.get("symbol")
              or pick.get("ticker")
              or pick.get("pair") or "UNKNOWN")

    try:
        last_idx = ohlcv_df.index[-1]
        last_ts_key = (
            int(pd.Timestamp(last_idx).value)
            if not isinstance(last_idx, (int, np.integer))
            else int(last_idx)
        )
    except Exception:
        last_ts_key = len(ohlcv_df)

    cache_key = (symbol, last_ts_key, pred_len)
    cached = _CACHE.get_or_none(cache_key)
    if cached is not None:
        change_pct, conf = cached
    else:
        try:
            change_pct, conf = _run_predictor(predictor, ohlcv_df, pred_len)
        except Exception as exc:
            logger.warning("kronos predict failed for %s: %s", symbol, exc)
            return _stub_score(pick)
        _CACHE.put(cache_key, (change_pct, conf))

    direction = _classify(change_pct)
    multiplier, agree = _multiplier_for(
        pick.get("direction"), direction, change_pct)

    return {
        "kronos_direction": direction,
        "kronos_confidence": float(conf),
        "kronos_predicted_change_pct": float(change_pct),
        "kronos_agree": bool(agree),
        "multiplier": float(multiplier),
        "_stub": False,
    }


def kronos_overlay_picks(picks: list[dict],
                         ohlcv_data: dict[str, pd.DataFrame],
                         pred_len: int = DEFAULT_PRED_LEN) -> list[dict]:
    """
    Apply the overlay across a list of picks.

    - Mutates each pick's `confidence` by `multiplier` (unless DRY_RUN).
    - Stamps `_kronos_overlay` sub-block on every pick.
    - Returns the same list (in-place mutation, returned for chaining).
    """
    if os.environ.get("KRONOS_OVERLAY_DISABLED") == "1":
        return picks

    dry_run = os.environ.get("KRONOS_OVERLAY_DRY_RUN") == "1"

    for pick in picks:
        symbol = (pick.get("symbol")
                  or pick.get("ticker")
                  or pick.get("pair"))
        ohlcv = ohlcv_data.get(symbol) if symbol else None
        score = kronos_score_pick(pick, ohlcv, pred_len=pred_len)
        pick["_kronos_overlay"] = score
        if dry_run or score.get("_stub"):
            continue
        try:
            pick["confidence"] = float(pick.get("confidence", 1.0)) * score["multiplier"]
        except (TypeError, ValueError):
            pass
    return picks


# ---------------------------------------------------------------------------
# __main__: synthetic backtest / smoke
# ---------------------------------------------------------------------------
def _synthetic_ohlcv(n: int = 200, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    drift = np.linspace(0, 0.30, n)               # +30% over the window
    noise = rng.normal(0, 0.01, n).cumsum()
    close = 100 * np.exp(drift + noise)
    high = close * (1 + rng.uniform(0.001, 0.01, n))
    low = close * (1 - rng.uniform(0.001, 0.01, n))
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = rng.uniform(1000, 5000, n)
    idx = pd.date_range(end=pd.Timestamp.utcnow(), periods=n, freq="h")
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": vol}, index=idx)


class _MockPredictor:
    """Toy predictor used when kronos isn't installed — extrapolates trend."""

    def predict(self, df, x_timestamp, y_timestamp, pred_len,
                T=1.0, top_p=0.9, sample_count=1):
        closes = df["close"].values
        recent = closes[-min(20, len(closes)):]
        slope = (recent[-1] - recent[0]) / max(1, len(recent) - 1)
        future = recent[-1] + slope * np.arange(1, pred_len + 1)
        return pd.DataFrame({"close": future})


def _main() -> None:
    print(f"HAVE_KRONOS = {HAVE_KRONOS}")
    if not HAVE_KRONOS:
        print("stub mode -- install torch + kronos to enable real inference")
        set_predictor(_MockPredictor())

    ohlcv = _synthetic_ohlcv()
    picks = [
        {"symbol": "FAKE", "direction": "LONG",  "confidence": 0.5},
        {"symbol": "FAKE", "direction": "SHORT", "confidence": 0.5},
        {"symbol": "FAKE", "direction": "LONG",  "confidence": 0.5},
        {"symbol": "MISSING", "direction": "LONG", "confidence": 0.5},
    ]
    out = kronos_overlay_picks(picks, {"FAKE": ohlcv})

    boosted = sum(1 for p in out
                  if p.get("_kronos_overlay", {}).get("multiplier", 1.0) > 1.0)
    dampened = sum(1 for p in out
                   if 0 < p.get("_kronos_overlay", {}).get("multiplier", 1.0) < 1.0)
    blocked = sum(1 for p in out
                  if p.get("_kronos_overlay", {}).get("multiplier", 1.0) <= 0.6)

    print(f"n_long_picks_boosted   = {boosted}")
    print(f"n_short_picks_dampened = {dampened}")
    print(f"n_disagree_blocks      = {blocked}")
    for p in out:
        print(p["symbol"], p["direction"], "conf=", round(p["confidence"], 3),
              "kronos=", p.get("_kronos_overlay"))


if __name__ == "__main__":
    _main()

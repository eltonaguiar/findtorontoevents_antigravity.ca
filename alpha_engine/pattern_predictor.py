#!/usr/bin/env python3
"""
ALPHA ENGINE -- Pattern-Based Win Rate Predictor
==================================================
Learns which condition combinations lead to winning trades from historical data.

Instead of ML probabilities, builds lookup tables of ACTUAL win rates for
specific condition combinations:
  "oversold_uptrend_high_vol_LONG_momentum_european_weekday = 72% WR (15 trades)"

Usage:
    from pattern_predictor import PatternPredictor
    pp = PatternPredictor()
    pp.train(closed_picks)
    result = pp.predict_wr(new_pick)
    golden = pp.get_golden_patterns()
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# Strategy family classification
# ---------------------------------------------------------------------------
_FAMILY_KEYWORDS = {
    "momentum": ["momentum", "macd", "ema", "sma", "trend", "breakout", "triangle",
                  "squeeze", "carry", "ctrend", "kalman", "multi_horizon"],
    "mean_reversion": ["mean_reversion", "reversion", "rsi2", "rsi_2", "connors",
                       "bollinger", "vwap", "zscore", "z_score", "hurst_mean"],
    "ml_enhanced": ["ml_enhanced"],
    "onchain": ["onchain", "funding", "liquidation", "whale", "exchange_netflow",
                "mvrv", "hash_ribbon", "delta_divergence", "liquidity_imbalance",
                "liquidity_sweep", "cmf"],
    "breakout": ["breakout", "ascending_triangle", "entropy_regime", "orb_",
                 "london_breakout"],
    "scalp": ["scalp", "fast_rsi", "aggressive"],
    "seasonal": ["seasonal", "day_of_week", "month_effect"],
    "regime": ["regime", "markov", "hurst_regime", "adaptive_vr", "cross_system"],
    "quant": ["autocorrelation", "hayes", "forex_logistic", "propfirm",
              "fractal_sr", "volume_profile"],
    "forex": ["forex", "london", "carry_trade"],
}


def _classify_strategy_family(strategy: str) -> str:
    """Map a strategy name to its family."""
    s = strategy.lower()
    for family, keywords in _FAMILY_KEYWORDS.items():
        for kw in keywords:
            if kw in s:
                return family
    return "other"


# ---------------------------------------------------------------------------
# Condition fingerprint extraction
# ---------------------------------------------------------------------------

def _rsi_bucket(rsi: Optional[float]) -> str:
    if rsi is None:
        return "rsi_unknown"
    if rsi < 30:
        return "oversold"
    if rsi > 70:
        return "overbought"
    return "rsi_neutral"


def _volume_bucket(volume_ratio: Optional[float]) -> str:
    if volume_ratio is None:
        return "vol_unknown"
    if volume_ratio < 0.8:
        return "low_vol"
    if volume_ratio > 1.5:
        return "high_vol"
    return "normal_vol"


def _regime_bucket(regime: Optional[str], adx: Optional[float] = None) -> str:
    if regime:
        return regime.lower()
    if adx is not None:
        if adx > 25:
            return "trending"
        return "ranging"
    return "regime_unknown"


def _confidence_bucket(confidence: Optional[float]) -> str:
    if confidence is None:
        return "conf_unknown"
    if confidence >= 0.8:
        return "high_conf"
    if confidence >= 0.6:
        return "med_conf"
    return "low_conf"


def _ml_score_bucket(ml_score: Optional[float]) -> str:
    if ml_score is None:
        return "ml_unknown"
    if ml_score >= 0.7:
        return "ml_high"
    if ml_score >= 0.5:
        return "ml_med"
    return "ml_low"


def _hold_bucket(hold_days: Optional[int]) -> str:
    if hold_days is None:
        return "hold_unknown"
    if hold_days <= 1:
        return "intraday"
    if hold_days <= 3:
        return "short_hold"
    return "long_hold"


def _hour_bucket(entry_date: Optional[str]) -> str:
    """Classify by hour of day if timestamp available, else by day of week."""
    if not entry_date:
        return "time_unknown"
    try:
        dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
        h = dt.hour
        if h < 8:
            return "asian"
        if h < 16:
            return "european"
        return "us_session"
    except Exception:
        return "time_unknown"


def _day_type(entry_date: Optional[str]) -> str:
    if not entry_date:
        return "day_unknown"
    try:
        dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
        return "weekend" if dt.weekday() >= 5 else "weekday"
    except Exception:
        return "day_unknown"


def _parse_extra(pick: dict) -> dict:
    """Parse extra_json field into a dict."""
    ej = pick.get("extra_json", "")
    if isinstance(ej, dict):
        return ej
    if isinstance(ej, str) and ej:
        try:
            return json.loads(ej)
        except Exception:
            return {}
    return {}


def extract_fingerprint(pick: dict) -> dict[str, str]:
    """Extract all condition dimensions from a pick."""
    extra = _parse_extra(pick)

    # RSI: check pick-level, then extra_json
    rsi = pick.get("rsi_at_entry")
    if rsi is None:
        rsi = extra.get("rsi") or extra.get("rsi_14")

    # Volume ratio
    vol_ratio = pick.get("volume_ratio")
    if vol_ratio is None:
        vol_ratio = extra.get("volume_ratio")

    # Regime
    regime = pick.get("regime_at_entry")
    adx = extra.get("regime_adx")

    # Direction
    signal_type = pick.get("signal_type", "BUY").upper()
    direction = "LONG" if signal_type in ("BUY", "LONG") else "SHORT"

    return {
        "rsi": _rsi_bucket(rsi),
        "volume": _volume_bucket(vol_ratio),
        "regime": _regime_bucket(regime, adx),
        "confidence": _confidence_bucket(pick.get("confidence")),
        "ml_score": _ml_score_bucket(pick.get("ml_score")),
        "direction": direction,
        "family": _classify_strategy_family(pick.get("strategy", "")),
        "category": pick.get("category", "unknown"),
        "hold": _hold_bucket(pick.get("hold_days")),
        "hour": _hour_bucket(pick.get("entry_date")),
        "day_type": _day_type(pick.get("entry_date")),
    }


def fingerprint_to_key(fp: dict, dimensions: Optional[list[str]] = None) -> str:
    """Convert fingerprint dict to a composite lookup key."""
    if dimensions is None:
        dimensions = ["rsi", "regime", "volume", "direction", "family",
                       "category", "confidence", "ml_score", "hold", "day_type"]
    return "_".join(str(fp.get(d, "?")) for d in dimensions)


# Dimension priority (most to least important for progressive broadening)
_DIMENSION_PRIORITY = [
    "rsi", "regime", "volume", "direction", "family",
    "category", "confidence", "ml_score", "hold", "day_type",
]

# Broadening order: drop least important first
_BROADENING_LEVELS = [
    _DIMENSION_PRIORITY[:],                                    # Full 10-dim
    ["rsi", "regime", "volume", "direction", "family",
     "category", "confidence", "ml_score"],                    # Drop hold, day_type
    ["rsi", "regime", "direction", "family", "category",
     "confidence"],                                            # Drop volume, ml_score
    ["rsi", "regime", "direction", "family", "category"],      # Drop confidence
    ["regime", "direction", "family", "category"],             # Drop rsi
    ["direction", "family", "category"],                       # 3-dim
    ["family", "category"],                                    # 2-dim
    ["family"],                                                # 1-dim
]


# ---------------------------------------------------------------------------
# PatternPredictor
# ---------------------------------------------------------------------------

class PatternPredictor:
    """Learns which condition patterns lead to wins from historical trades."""

    def __init__(self, min_samples: int = 5):
        self.min_samples = min_samples
        # {pattern_key: {"wins": int, "losses": int, "total_pnl": float, "trades": int}}
        self.pattern_stats: dict[str, dict[str, Any]] = {}
        # Track which broadening levels each pattern belongs to
        self._level_stats: dict[int, dict[str, dict]] = defaultdict(lambda: defaultdict(
            lambda: {"wins": 0, "losses": 0, "total_pnl": 0.0, "trades": 0}
        ))

    def train(self, closed_picks: list[dict]) -> None:
        """Build pattern lookup tables from closed trades."""
        self.pattern_stats.clear()
        self._level_stats.clear()

        for pick in closed_picks:
            status = pick.get("status", "").upper()
            if status not in ("WON", "LOST"):
                continue  # Skip EXPIRED or unknown

            is_win = status == "WON"
            pnl = pick.get("pnl_pct", 0.0) or 0.0

            fp = extract_fingerprint(pick)

            # Build stats at every broadening level
            for level_idx, dims in enumerate(_BROADENING_LEVELS):
                key = fingerprint_to_key(fp, dims)
                bucket = self._level_stats[level_idx]
                stats = bucket[key]
                stats["trades"] += 1
                stats["total_pnl"] += pnl
                if is_win:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1

        # Flatten all levels into pattern_stats with level prefix
        for level_idx, bucket in self._level_stats.items():
            for key, stats in bucket.items():
                full_key = f"L{level_idx}:{key}"
                wr = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0
                avg_pnl = stats["total_pnl"] / stats["trades"] if stats["trades"] > 0 else 0
                self.pattern_stats[full_key] = {
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "trades": stats["trades"],
                    "win_rate": round(wr, 4),
                    "avg_pnl": round(avg_pnl, 4),
                    "level": level_idx,
                    "dimensions": len(_BROADENING_LEVELS[level_idx]),
                }

        print(f"  [PATTERN] Trained on {len(closed_picks)} closed picks")
        print(f"  [PATTERN] {len(self.pattern_stats)} pattern entries across {len(_BROADENING_LEVELS)} levels")

    def predict_wr(self, pick: dict, data: Any = None) -> dict:
        """Predict win rate for a new pick based on its pattern fingerprint.

        Returns:
            {
                "predicted_wr": float,
                "confidence": str,   # "high", "medium", "low", "none"
                "matching_pattern": str,
                "pattern_samples": int,
                "pattern_avg_pnl": float,
                "level": int,
            }
        """
        fp = extract_fingerprint(pick)

        # Try each broadening level, most specific first
        for level_idx, dims in enumerate(_BROADENING_LEVELS):
            key = fingerprint_to_key(fp, dims)
            bucket = self._level_stats.get(level_idx, {})
            stats = bucket.get(key)

            if stats and stats["trades"] >= self.min_samples:
                wr = stats["wins"] / stats["trades"]
                avg_pnl = stats["total_pnl"] / stats["trades"]

                # Confidence based on level and sample size
                if level_idx <= 1 and stats["trades"] >= 10:
                    confidence = "high"
                elif level_idx <= 3 and stats["trades"] >= self.min_samples:
                    confidence = "medium"
                else:
                    confidence = "low"

                return {
                    "predicted_wr": round(wr, 4),
                    "confidence": confidence,
                    "matching_pattern": key,
                    "pattern_samples": stats["trades"],
                    "pattern_avg_pnl": round(avg_pnl, 4),
                    "level": level_idx,
                }

        return {
            "predicted_wr": None,
            "confidence": "none",
            "matching_pattern": None,
            "pattern_samples": 0,
            "pattern_avg_pnl": 0.0,
            "level": -1,
        }

    def get_golden_patterns(self, min_wr: float = 0.65, min_trades: int = 10) -> list[dict]:
        """Return all patterns with WR >= 65% and sufficient samples.
        These are the 'safe entry zones'."""
        results = []
        for key, stats in self.pattern_stats.items():
            if (stats["trades"] >= min_trades
                    and stats["win_rate"] >= min_wr):
                results.append({"pattern": key, **stats})
        results.sort(key=lambda x: (-x["win_rate"], -x["trades"]))
        return results

    def get_danger_patterns(self, max_wr: float = 0.30, min_trades: int = 10) -> list[dict]:
        """Return patterns that almost always lose."""
        results = []
        for key, stats in self.pattern_stats.items():
            if (stats["trades"] >= min_trades
                    and stats["win_rate"] <= max_wr):
                results.append({"pattern": key, **stats})
        results.sort(key=lambda x: (x["win_rate"], -x["trades"]))
        return results

    def save(self, path: Optional[str] = None) -> None:
        """Persist pattern stats for fast loading."""
        fpath = Path(path) if path else DATA_DIR / "pattern_stats.json"
        fpath.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "pattern_stats": self.pattern_stats,
            "level_stats": {
                str(k): {pk: pv for pk, pv in v.items()}
                for k, v in self._level_stats.items()
            },
            "min_samples": self.min_samples,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"  [PATTERN] Saved to {fpath}")

    def load(self, path: Optional[str] = None) -> bool:
        """Load persisted pattern stats. Returns True if loaded successfully."""
        fpath = Path(path) if path else DATA_DIR / "pattern_stats.json"
        if not fpath.exists():
            return False

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self.pattern_stats = payload.get("pattern_stats", {})
            self.min_samples = payload.get("min_samples", 5)

            # Rebuild _level_stats from saved data
            self._level_stats.clear()
            for level_str, bucket in payload.get("level_stats", {}).items():
                level_idx = int(level_str)
                for key, stats in bucket.items():
                    self._level_stats[level_idx][key] = stats

            print(f"  [PATTERN] Loaded {len(self.pattern_stats)} patterns from {fpath}")
            return True
        except Exception as e:
            print(f"  [PATTERN] Failed to load: {e}")
            return False


# ---------------------------------------------------------------------------
# Standalone runner: train + report
# ---------------------------------------------------------------------------

def main():
    """Train pattern predictor and print analysis."""
    import sys

    closed_path = DATA_DIR / "closed_picks.json"
    if not closed_path.exists():
        print(f"No closed picks found at {closed_path}")
        sys.exit(1)

    with open(closed_path, "r", encoding="utf-8", errors="replace") as f:
        closed_picks = json.load(f)

    print(f"Loaded {len(closed_picks)} closed picks\n")

    pp = PatternPredictor(min_samples=5)
    pp.train(closed_picks)
    pp.save()

    # --- Golden patterns ---
    golden = pp.get_golden_patterns(min_wr=0.60, min_trades=5)
    print(f"\n{'='*70}")
    print(f"TOP 10 GOLDEN PATTERNS (WR >= 60%, 5+ trades)")
    print(f"{'='*70}")
    for i, g in enumerate(golden[:10], 1):
        print(f"  {i:2d}. {g['pattern']}")
        print(f"      WR: {g['win_rate']:.1%} | Trades: {g['trades']} | "
              f"Avg PnL: {g['avg_pnl']:+.2f}% | W/L: {g['wins']}/{g['losses']}")

    # --- Danger patterns ---
    danger = pp.get_danger_patterns(max_wr=0.35, min_trades=5)
    print(f"\n{'='*70}")
    print(f"TOP 10 DANGER PATTERNS (WR <= 35%, 5+ trades)")
    print(f"{'='*70}")
    for i, d in enumerate(danger[:10], 1):
        print(f"  {i:2d}. {d['pattern']}")
        print(f"      WR: {d['win_rate']:.1%} | Trades: {d['trades']} | "
              f"Avg PnL: {d['avg_pnl']:+.2f}% | W/L: {d['wins']}/{d['losses']}")

    # --- Pattern coverage ---
    total_picks = sum(1 for p in closed_picks if p.get("status", "").upper() in ("WON", "LOST"))
    matched = 0
    for pick in closed_picks:
        if pick.get("status", "").upper() not in ("WON", "LOST"):
            continue
        result = pp.predict_wr(pick)
        if result["predicted_wr"] is not None:
            matched += 1

    coverage = matched / total_picks * 100 if total_picks > 0 else 0
    print(f"\n{'='*70}")
    print(f"PATTERN COVERAGE")
    print(f"{'='*70}")
    print(f"  Picks with known pattern match: {matched}/{total_picks} ({coverage:.1f}%)")
    print(f"  Total unique patterns: {len(pp.pattern_stats)}")

    # --- Dimension distribution ---
    print(f"\n{'='*70}")
    print(f"MATCH LEVEL DISTRIBUTION (0=most specific, {len(_BROADENING_LEVELS)-1}=broadest)")
    print(f"{'='*70}")
    level_counts = defaultdict(int)
    for pick in closed_picks:
        if pick.get("status", "").upper() not in ("WON", "LOST"):
            continue
        result = pp.predict_wr(pick)
        if result["level"] >= 0:
            level_counts[result["level"]] += 1
    for lvl in sorted(level_counts):
        dims = len(_BROADENING_LEVELS[lvl])
        print(f"  Level {lvl} ({dims} dimensions): {level_counts[lvl]} picks")


if __name__ == "__main__":
    main()

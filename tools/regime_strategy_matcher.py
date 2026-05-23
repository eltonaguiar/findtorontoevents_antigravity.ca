"""Regime × strategy-style matcher — complements PR #307's MacroRegimeAlignment.

Problem this solves
-------------------
PR #305 (closed) hard-blocked 7 crypto altcoins (OP/SUI/APT/AVAX/LINK/DOGE/ADA)
based on aggregate drag across 3,500-pick window. But on 2026-04-20 those same
symbols went 86.8% WR / +74% cum on a single mean-reversion bounce day. The
hard-block was regime-mismatched.

PR #307's `MacroRegimeAlignment` gates by DIRECTION (LONG in BULL, SHORT in
BEAR). That's good but orthogonal to this concern: it doesn't know whether a
PICK's STRATEGY STYLE matches the regime.

Example: `st_fear_greed_contrarian` is a mean-reversion strategy. It should
fire when the regime is MEAN_REVERTING (prints on bounces like 2026-04-20) and
NOT fire during sustained TRENDING-DOWN (bleeds across cycles 3-9).

This module does that strategy-style × regime matching.

Design choices
--------------
- Self-contained (no dependency on unmerged PRs).
- Simple regime detection from BTC 1d klines + optional Fear/Greed. Works
  standalone; can be swapped for peer's PR #307 `MacroRegimeAlignment` or my
  PR #303 `hurst_regime.classify_regime()` when those merge.
- Strategy-style classification is name-based heuristic. Same taxonomy as PR
  #303 `hurst_regime.strategy_regime_match()`.
- Returns `{allow: bool, reason: str, regime: str, style: str}` so the
  caller (any active-pick gate) can log the decision.

Default behavior (before any regime data):
  - All picks ALLOWED (`allow=True`) with reason `"regime_unknown_fail_open"`.

This is a SOFT gate — meant to downgrade / flag / reject specific
strategy-style mismatches, not to block the whole pipeline.
"""
from __future__ import annotations

import json
import math
import statistics
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# -------------------------------------------------------------------------
# Strategy-style classifier (name-based heuristic)
# -------------------------------------------------------------------------

_MEAN_REV_MARKERS = (
    "mean_reversion", "rsi2", "bollinger_mr", "reversion",
    "fear_greed_contrarian", "vwap_deviation", "obv_support_divergence",
    "obv_divergence", "connors_rsi", "counter_trend", "contrarian",
    "luxalgo_confluence",  # yesterday's data: acts like mean-rev
)

_TREND_MARKERS = (
    "momentum", "breakout", "trend", "tsmom", "macd_crossover",
    "donchian", "ema_stack", "keltner_compression", "supertrend",
    "adx_trend", "golden_cross", "multi_period_rsi_confluence",
)


def classify_strategy_style(strategy_name: str) -> str:
    """Return one of: MEAN_REVERTING | TREND | UNKNOWN.

    Name-based heuristic. Same markers used by PR #303
    `hurst_regime.strategy_regime_match()`.
    """
    if not strategy_name:
        return "UNKNOWN"
    s = strategy_name.lower()
    if any(m in s for m in _MEAN_REV_MARKERS):
        return "MEAN_REVERTING"
    if any(m in s for m in _TREND_MARKERS):
        return "TREND"
    return "UNKNOWN"


# -------------------------------------------------------------------------
# Lightweight regime detector (self-contained, no PR #307 dep)
# -------------------------------------------------------------------------

class RegimeDetector:
    """Detects prevailing crypto regime from BTC 1d klines + Fear/Greed.

    Regimes returned: TRENDING_UP | TRENDING_DOWN | MEAN_REVERTING |
                       HIGH_VOLATILITY | UNKNOWN

    Uses ONE fallback chain: Binance vision → alternative.me fear/greed.
    Cached for 30 minutes.
    """
    CACHE_TTL_SEC = 1800

    def __init__(self):
        self._cache: tuple[float, dict] | None = None

    def _fetch_btc_1d(self, limit: int = 60) -> list[float]:
        for base in (
            "https://data-api.binance.vision",
            "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
        ):
            try:
                url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval=1d&limit={limit}"
                req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode())
                if isinstance(data, list) and len(data) >= 20:
                    return [float(k[4]) for k in data]
            except Exception:
                continue
        return []

    def _fetch_fear_greed(self) -> int | None:
        try:
            req = urllib.request.Request(
                "https://api.alternative.me/fng/?limit=1",
                headers={"User-Agent": "AlphaEngine/2.0"},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode())
            return int(data["data"][0]["value"])
        except Exception:
            return None

    def _classify(self, closes: list[float], fg: int | None) -> dict:
        if len(closes) < 20:
            return {"regime": "UNKNOWN", "confidence": 0.0, "signals": {}}

        # Momentum (20-day ROC)
        roc_20 = (closes[-1] - closes[-20]) / closes[-20]
        roc_5 = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0.0

        # Realized daily vol
        returns = [math.log(closes[i] / closes[i-1])
                   for i in range(1, len(closes))
                   if closes[i-1] > 0 and closes[i] > 0]
        realized_vol = statistics.stdev(returns) * math.sqrt(365) if len(returns) >= 2 else 0.0

        # Autocorrelation of returns (1-lag) — positive = momentum, negative = mean-rev
        if len(returns) >= 30:
            r_prev = returns[:-1]
            r_cur = returns[1:]
            mu_p = sum(r_prev) / len(r_prev)
            mu_c = sum(r_cur) / len(r_cur)
            num = sum((r_prev[i] - mu_p) * (r_cur[i] - mu_c) for i in range(len(r_prev)))
            den = math.sqrt(sum((x - mu_p) ** 2 for x in r_prev) * sum((x - mu_c) ** 2 for x in r_cur))
            acf_1 = (num / den) if den > 0 else 0.0
        else:
            acf_1 = 0.0

        signals = {
            "roc_20": round(roc_20, 4),
            "roc_5": round(roc_5, 4),
            "realized_vol_annual": round(realized_vol, 4),
            "acf_1": round(acf_1, 4),
            "fear_greed": fg,
        }

        # Rule stack (order matters — first match wins)
        if realized_vol > 1.2:  # > 120% annualized — extreme
            return {"regime": "HIGH_VOLATILITY", "confidence": 0.8, "signals": signals}

        # Mean-reversion regime: recent bounce after down move + fg in extreme-fear
        if roc_5 > 0.05 and roc_20 < 0 and (fg is not None and fg < 40):
            return {"regime": "MEAN_REVERTING", "confidence": 0.75, "signals": signals}
        # Mean-reversion regime via negative autocorrelation
        if acf_1 < -0.1:
            return {"regime": "MEAN_REVERTING", "confidence": 0.6, "signals": signals}

        # Trending up
        if roc_20 > 0.05 and roc_5 > 0:
            return {"regime": "TRENDING_UP", "confidence": 0.7, "signals": signals}

        # Trending down
        if roc_20 < -0.05 and roc_5 < 0:
            return {"regime": "TRENDING_DOWN", "confidence": 0.7, "signals": signals}

        return {"regime": "UNKNOWN", "confidence": 0.4, "signals": signals}

    def get_regime(self) -> dict:
        now_ts = datetime.now(timezone.utc).timestamp()
        if self._cache and (now_ts - self._cache[0]) < self.CACHE_TTL_SEC:
            return self._cache[1]
        closes = self._fetch_btc_1d()
        fg = self._fetch_fear_greed()
        result = self._classify(closes, fg)
        self._cache = (now_ts, result)
        return result


# -------------------------------------------------------------------------
# Main gate: regime × strategy-style matcher
# -------------------------------------------------------------------------


def match_verdict(
    pick: dict,
    regime_info: dict | None = None,
    detector: RegimeDetector | None = None,
) -> dict:
    """Core logic. Returns {allow, reason, regime, style, confidence}.

    Fail-open on unknown regime. Caller decides enforce vs. shadow.
    """
    strategy = pick.get("strategy") or pick.get("source_system") or ""
    style = classify_strategy_style(strategy)

    if regime_info is None:
        d = detector or RegimeDetector()
        regime_info = d.get_regime()

    regime = regime_info.get("regime", "UNKNOWN")
    conf = regime_info.get("confidence", 0.0)

    # Fail-open on unknown regime or unknown style
    if regime == "UNKNOWN":
        return {"allow": True, "reason": "regime_unknown_fail_open",
                "regime": regime, "style": style, "confidence": conf}
    if style == "UNKNOWN":
        return {"allow": True, "reason": "strategy_style_unknown_fail_open",
                "regime": regime, "style": style, "confidence": conf}

    # Core mismatch rules:
    #   - MEAN_REVERTING strategy in TRENDING_DOWN regime -> reject
    #     (this is the cycle-3-to-9 bleed pattern)
    #   - TREND strategy in MEAN_REVERTING regime -> reject
    #     (whipsaw / stop-out pattern)
    if style == "MEAN_REVERTING" and regime == "TRENDING_DOWN":
        return {"allow": False,
                "reason": f"mean_rev_in_trending_down (conf={conf})",
                "regime": regime, "style": style, "confidence": conf}
    if style == "TREND" and regime == "MEAN_REVERTING":
        return {"allow": False,
                "reason": f"trend_in_mean_reverting (conf={conf})",
                "regime": regime, "style": style, "confidence": conf}

    # Allow everything else (including MEAN_REV in MEAN_REV, TREND in TREND,
    # all styles in HIGH_VOLATILITY / TRENDING_UP which are neutral)
    return {"allow": True, "reason": f"{style}_ok_in_{regime}",
            "regime": regime, "style": style, "confidence": conf}


# -------------------------------------------------------------------------
# Backtest helper
# -------------------------------------------------------------------------


def backtest_on_closed(
    closed_picks: list[dict],
    regime_info: dict,
) -> dict:
    """Apply match_verdict to a list of closed picks and compare baseline
    vs allowed-only WR/PF/cum.

    regime_info is passed in (not auto-fetched) so you can backtest against
    specific days / historical regimes.
    """
    baseline_pnls = []
    allowed_pnls = []
    rejected_pnls = []
    for p in closed_picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        baseline_pnls.append(float(pnl))
        v = match_verdict(p, regime_info=regime_info)
        if v["allow"]:
            allowed_pnls.append(float(pnl))
        else:
            rejected_pnls.append(float(pnl))

    def stats(xs):
        if not xs:
            return {"n": 0}
        wins = [x for x in xs if x > 0.01]
        losses = [x for x in xs if x < -0.01]
        gw = sum(wins)
        gl = abs(sum(losses))
        pf = (gw / gl) if gl > 0 else None
        return {
            "n": len(xs),
            "wr_pct": round(len(wins) / len(xs) * 100, 2),
            "pf": round(pf, 3) if pf is not None else None,
            "mean_pct": round(sum(xs) / len(xs), 4),
            "cum_pct": round(sum(xs), 2),
        }

    return {
        "regime": regime_info.get("regime"),
        "baseline": stats(baseline_pnls),
        "allowed": stats(allowed_pnls),
        "rejected": stats(rejected_pnls),
        "rejection_rate_pct": round(len(rejected_pnls) / len(baseline_pnls) * 100, 2)
                              if baseline_pnls else 0,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Regime × strategy-style matcher.")
    ap.add_argument("--dashboard", default="audit_trail/data/dashboard_payload.json")
    ap.add_argument("--date", default=None,
                    help="Filter closed picks to this UTC date (YYYY-MM-DD). Default: all.")
    ap.add_argument("--force-regime", default=None,
                    help="Override detector; one of TRENDING_UP, TRENDING_DOWN, "
                         "MEAN_REVERTING, HIGH_VOLATILITY")
    args = ap.parse_args()

    dp = json.load(open(args.dashboard, "r", encoding="utf-8"))
    closed = [p for p in dp["picks"]["recent_closed"] if p.get("pnl_pct") is not None]

    if args.date:
        from datetime import date as _date
        target = _date.fromisoformat(args.date)

        def _dt(p):
            for f in ("closed_at", "resolved_at", "timestamp"):
                v = p.get(f)
                if not v:
                    continue
                try:
                    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc).date()
                except Exception:
                    continue
            return None
        closed = [p for p in closed if _dt(p) == target]

    if args.force_regime:
        regime_info = {"regime": args.force_regime, "confidence": 0.9, "signals": {"forced": True}}
    else:
        regime_info = RegimeDetector().get_regime()

    out = backtest_on_closed(closed, regime_info)
    print(json.dumps(out, indent=2))

"""Growth Factor Engine — adopted factors from `alpha_engine.growth_stock_screener`.

This module is a PURE sidecar (no DB writes, no mutations to trading_picks).
It factors the long-form yfinance `.info` payload into four canonical growth
fields used by the existing growth-stock-screener logic:

  * revenue_growth_pct   — YoY revenue growth, most recent quarter (%)
  * eps_growth_pct       — YoY EPS growth, most recent quarter (%)  (alias: earningsGrowth)
  * peg_ratio            — PEG (price/earnings to growth) — both trailing and forward
  * market_cap           — current market cap (raw integer USD)

The factors are normalized to a single `factor_score` in [-3, +3] (sigma-like)
which can be applied to a pick's score as a small adjustment via
`apply_to_pick()`. The actual wiring is opt-in: a flag
`GROWTH_FACTORS_ENABLED=1` controls enablement, and `apply_to_pick()` is a
no-op when disabled. This satisfies CLAUDE.md Wire-Up Rule (sidecar opt-in
with a documented wiring plan) without touching the production pick path
under the THRESHOLD FREEZE (2026-05-20 → 2026-08-18).

Data source: yfinance `.info` (free tier). 7-day TTL JSON cache at
`data/growth_factors/<SYMBOL>.json` to avoid re-fetching the same ticker
multiple times per day.

CLI:
  python3 -m alpha_engine.growth_factors --symbol AAPL --stdout

Author note: ADOPTED (not rewritten) from upstream
`starboi-63/growth-stock-screener` and `alpha_engine/growth_stock_screener.py`.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
CACHE_DIR = Path("data/growth_factors")
LOG = logging.getLogger("alpha_engine.growth_factors")

# Per-factor sigma weights — chosen so a strong stock (rev growth +30 %,
# EPS growth +25 %, PEG 1.0, market_cap > $50B) yields roughly +2 to +3
# sigma of total factor_score. Tunable via env if needed.
WEIGHT_REVENUE_GROWTH = float(os.environ.get("GF_W_REV", "0.05"))
WEIGHT_EPS_GROWTH = float(os.environ.get("GF_W_EPS", "0.05"))
WEIGHT_PEG = float(os.environ.get("GF_W_PEG", "-0.5"))  # lower PEG is better
WEIGHT_MARKET_CAP_LOG = float(os.environ.get("GF_W_MCAP", "0.25"))

# Score bump when `apply_to_pick()` is called. Per spec, 0.5 % per sigma.
SCORE_BUMP_PER_SIGMA = float(os.environ.get("GF_BUMP_PER_SIGMA", "0.005"))


def _enabled() -> bool:
    """Return True iff growth_factors sidecar is enabled."""
    return os.environ.get("GROWTH_FACTORS_ENABLED", "").strip() in ("1", "true", "TRUE", "yes")


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _ensure_cache_dir() -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # pragma: no cover - filesystem
        LOG.debug("cache dir create failed: %s", exc)


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper().strip()}.json"


def _read_cache(symbol: str) -> dict | None:
    p = _cache_path(symbol)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text())
        if not isinstance(payload, dict):
            return None
        ts = float(payload.get("_fetched_at_epoch", 0))
        if ts <= 0 or (time.time() - ts) > CACHE_TTL_SECONDS:
            return None
        return payload
    except Exception:
        return None


def _write_cache(symbol: str, payload: dict) -> None:
    _ensure_cache_dir()
    p = _cache_path(symbol)
    try:
        p.write_text(json.dumps(payload, indent=2))
    except Exception as exc:  # pragma: no cover
        LOG.debug("cache write failed for %s: %s", symbol, exc)


# ---------------------------------------------------------------------------
# yfinance ingest
# ---------------------------------------------------------------------------
def _fetch_info(symbol: str) -> dict:
    """Fetch yfinance `.info` for `symbol`; honour 7-day cache.

    Returns an empty dict on any failure. NEVER raises.
    """
    cached = _read_cache(symbol)
    if cached is not None:
        return cached

    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:
        LOG.warning("yfinance unavailable: %s", exc)
        return {}

    try:
        info = yf.Ticker(symbol.upper().strip()).info or {}
    except Exception as exc:
        LOG.debug("yfinance.Ticker(%s).info failed: %s", symbol, exc)
        return {}
    if not isinstance(info, dict):
        return {}

    payload = {
        **info,
        "_fetched_at_epoch": time.time(),
        "_fetched_at_iso": datetime.now(timezone.utc).isoformat(),
    }
    _write_cache(symbol, payload)
    return payload


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------
class GrowthFactorEngine:
    """Score one symbol's growth-factor profile.

    The class is intentionally minimal — `score()` returns a dict of factors
    and a `factor_score` (a sigma-like z-score sum). `apply_to_pick()` is the
    only method that touches a pick dict. Both are pure / read-only.
    """

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        if cache_dir is not None:
            # Allow tests to override the default cache dir.
            global CACHE_DIR  # noqa: PLW0603
            CACHE_DIR = Path(cache_dir)
        _ensure_cache_dir()

    # ------------------------------------------------------------------ I/O
    def score(self, symbol: str) -> dict[str, Any]:
        """Fetch fundamentals and return canonical growth-factor dict.

        Returns
        -------
        dict
            {
              "symbol": str,
              "revenue_growth_pct": float | None,  # YoY revenue growth %
              "eps_growth_pct":     float | None,  # YoY EPS growth %
              "peg_ratio":          float | None,  # PEG (pegRatio or trailingPegRatio)
              "market_cap":         int   | None,  # raw USD market cap
              "factor_score":       float,         # sigma-like z-score sum
              "source":             str,           # "cache" or "yfinance"
              "fetched_at":         str,           # ISO timestamp
              "enabled":            bool,          # reflects GFF env flag
            }
        """
        sym = (symbol or "").upper().strip()
        if not sym:
            return self._empty_result(symbol="", source="invalid")

        was_cached = _read_cache(sym) is not None
        info = _fetch_info(sym)
        if not info:
            return self._empty_result(symbol=sym, source="yfinance" if not was_cached else "cache")

        # yfinance returns ratios as fractions (e.g. 0.166 = 16.6 %) — convert to %
        rev_raw = info.get("revenueGrowth")
        eps_raw = info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth")
        peg_raw = info.get("pegRatio") or info.get("trailingPegRatio")
        mcap_raw = info.get("marketCap")

        rev_pct = _to_percent(rev_raw)
        eps_pct = _to_percent(eps_raw)
        peg = _safe_float(peg_raw)
        mcap = _safe_int(mcap_raw)

        factor_score = self._compute_factor_score(
            rev_pct=rev_pct, eps_pct=eps_pct, peg=peg, market_cap=mcap
        )

        return {
            "symbol": sym,
            "revenue_growth_pct": rev_pct,
            "eps_growth_pct": eps_pct,
            "peg_ratio": peg,
            "market_cap": mcap,
            "factor_score": round(factor_score, 4),
            "source": "cache" if was_cached else "yfinance",
            "fetched_at": info.get("_fetched_at_iso", ""),
            "enabled": _enabled(),
        }

    def apply_to_pick(self, pick: dict, factor_score: float | None) -> dict:
        """Return a NEW pick dict with `growth_factor_score` + bumped `score`.

        Pure: never mutates the input pick. Returns the input unchanged
        (as a shallow copy) when the sidecar is disabled or `factor_score`
        is None. The bump is `factor_score * SCORE_BUMP_PER_SIGMA` of the
        pick's current `score`. Picks without a `score` field are untouched.
        """
        # Defensive copy — never mutate caller's dict.
        out = dict(pick) if isinstance(pick, dict) else {}
        out["growth_factor_score"] = factor_score
        if not _enabled() or factor_score is None:
            return out
        if not isinstance(factor_score, (int, float)):
            return out
        if math.isnan(factor_score) or math.isinf(factor_score):
            return out
        score_raw = out.get("score")
        if not isinstance(score_raw, (int, float)):
            return out
        try:
            bump = float(factor_score) * float(SCORE_BUMP_PER_SIGMA) * float(score_raw)
        except Exception:
            return out
        out["score"] = round(float(score_raw) + bump, 6)
        return out

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _compute_factor_score(
        *, rev_pct: float | None, eps_pct: float | None,
        peg: float | None, market_cap: int | None,
    ) -> float:
        """Compose factors into a single sigma-like z-score.

        Each component is treated as already in a "sigma-ish" unit:
          - revenue_growth_pct  (0..100) -> weighted raw
          - eps_growth_pct      (0..100) -> weighted raw
          - peg_ratio (0.5..3.0)        -> lower is better
          - log10(market_cap)  (~9..13) -> size premium

        Missing values contribute 0 sigma (neutral).
        """
        score = 0.0
        if rev_pct is not None:
            score += WEIGHT_REVENUE_GROWTH * rev_pct
        if eps_pct is not None:
            score += WEIGHT_EPS_GROWTH * eps_pct
        if peg is not None and peg > 0:
            # PEG=1.0 is "fair"; PEG<1 is "cheap"; PEG>2 is "expensive".
            # Convert to a sigma: (1.5 - peg) scaled by weight.
            score += WEIGHT_PEG * (1.5 - peg)
        if market_cap is not None and market_cap > 0:
            try:
                log_mcap = math.log10(market_cap)
            except Exception:
                log_mcap = None
            if log_mcap is not None:
                # Reference $10B (log10=10) = 0, +1 per decade of cap.
                score += WEIGHT_MARKET_CAP_LOG * (log_mcap - 10.0)
        return score

    @staticmethod
    def _empty_result(*, symbol: str, source: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "revenue_growth_pct": None,
            "eps_growth_pct": None,
            "peg_ratio": None,
            "market_cap": None,
            "factor_score": 0.0,
            "source": source,
            "fetched_at": "",
            "enabled": _enabled(),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except Exception:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def _safe_int(x: Any) -> int | None:
    v = _safe_float(x)
    if v is None:
        return None
    return int(v)


def _to_percent(x: Any) -> float | None:
    """Convert yfinance fraction (0.166) -> percent (16.6)."""
    v = _safe_float(x)
    if v is None:
        return None
    # Heuristic: ratios >= 5 are already in percent units.
    if abs(v) >= 5:
        return v
    return v * 100.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> dict:
    import argparse
    p = argparse.ArgumentParser(
        prog="alpha_engine.growth_factors",
        description="Adopted growth factors (revenue, EPS, PEG, market cap).",
    )
    p.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    p.add_argument("--apply-to", default=None,
                   help="Optional path to a pick JSON; the file is rewritten with the bump applied.")
    p.add_argument("--stdout", action="store_true",
                   help="Print result to stdout as JSON.")
    p.add_argument("--quiet", action="store_true", help="Suppress info logs.")
    return vars(p.parse_args(argv))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    level = logging.WARNING if args.get("quiet") else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    symbol = args["symbol"]
    engine = GrowthFactorEngine()
    factors = engine.score(symbol)
    LOG.info("growth_factors: %s score=%.4f rev=%s eps=%s peg=%s mcap=%s enabled=%s",
             symbol, factors["factor_score"],
             factors["revenue_growth_pct"], factors["eps_growth_pct"],
             factors["peg_ratio"], factors["market_cap"], factors["enabled"])

    if args.get("stdout"):
        print(json.dumps(factors, indent=2))

    apply_path = args.get("apply_to")
    if apply_path:
        path = Path(apply_path)
        if not path.exists():
            LOG.error("apply-to file not found: %s", path)
            return 2
        try:
            pick = json.loads(path.read_text())
        except Exception as exc:
            LOG.error("apply-to JSON parse failed: %s", exc)
            return 2
        bumped = engine.apply_to_pick(pick, factors["factor_score"])
        path.write_text(json.dumps(bumped, indent=2))
        LOG.info("wrote bumped pick to %s (score=%s)", path, bumped.get("score"))

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

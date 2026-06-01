"""ETF Country Rotation — Bhoi & Verma (2021) on country ETF momentum.

Academic basis:
  Bhoi & Verma (2021) "Country ETF Momentum and the Cross-Section of Returns"
  — momentum in country-level ETFs exploits differential economic cycles,
  monetary policy divergence, and capital-flow momentum across geographies.

Logic:
  - Universe: EWA (Australia), EWC (Canada), EWJ (Japan), EWG (Germany),
    EWU (UK), EWW (Mexico), EWZ (Brazil), EEM (EM composite)
  - Rank by 3-month (63 trading days) momentum
  - Long top-3, equal weight
  - Monthly rebalance (signal fires when top-3 membership changes)
  - Exit: falls out of top-5 OR max hold 720h (30 days)

Forced resolution: max_hold_hours=720, tp_pct=5.0, sl_pct=3.0,
time_exit_at_market=True (ETF class default).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "etf_country_rotation"
COUNTRY_ETFS: tuple[str, ...] = ("EWA", "EWC", "EWJ", "EWG", "EWU", "EWW", "EWZ", "EEM")
COUNTRY_NAMES: dict[str, str] = {
    "EWA": "Australia",
    "EWC": "Canada",
    "EWJ": "Japan",
    "EWG": "Germany",
    "EWU": "UK",
    "EWW": "Mexico",
    "EWZ": "Brazil",
    "EEM": "Emerging Markets",
}
MOMENTUM_LOOKBACK_DAYS = 63
TOP_N = 3
DROP_THRESHOLD = 5
CONFIDENCE_BASE = 0.58
CONFIDENCE_CEIL = 0.75


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_country_data() -> dict[str, Any]:
    """Fetch 6-month OHLCV for all country ETFs via yfinance."""
    import yfinance as yf

    data: dict[str, Any] = {}
    try:
        raw = yf.download(
            list(COUNTRY_ETFS), period="6mo", group_by="ticker",
            progress=False, threads=False,
        )
        if raw is None or raw.empty:
            logger.warning("yfinance returned empty data for country ETFs")
            return data
    except Exception as e:
        logger.error("yfinance download failed: %s", e)
        return data

    for symbol in COUNTRY_ETFS:
        try:
            if len(COUNTRY_ETFS) == 1:
                df = raw
            else:
                df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
            if df is not None and not df.empty and len(df) >= MOMENTUM_LOOKBACK_DAYS + 5:
                data[symbol] = df.dropna(subset=["Close"])
        except Exception as e:
            logger.warning("Data parse error for %s: %s", symbol, e)

    logger.info("Fetched data for %d/%d country ETFs", len(data), len(COUNTRY_ETFS))
    return data


def _rank_by_momentum(data: dict[str, Any]) -> list[tuple[str, float, float]]:
    """Rank country ETFs by 3-month momentum. Returns [(symbol, momentum, price), ...] desc."""
    scored: list[tuple[str, float, float]] = []
    for symbol, df in data.items():
        close = df["Close"]
        if len(close) < MOMENTUM_LOOKBACK_DAYS + 1:
            continue
        price_now = float(close.iloc[-1])
        price_ago = float(close.iloc[-(MOMENTUM_LOOKBACK_DAYS + 1)])
        if price_ago <= 0 or price_now <= 0:
            continue
        momentum = (price_now - price_ago) / price_ago
        scored.append((symbol, momentum, price_now))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def generate_country_rotation_picks() -> list[dict[str, Any]]:
    """Generate country ETF momentum rotation picks.

    Returns LONG picks for the top-3 country ETFs by 3-month return.
    Returns [] when data is insufficient.
    """
    data = _fetch_country_data()
    if len(data) < 4:
        logger.warning("Insufficient country ETF data (%d symbols) — need at least 4", len(data))
        return []

    ranked = _rank_by_momentum(data)
    if len(ranked) < TOP_N:
        return []

    picks: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for rank, (symbol, momentum, price) in enumerate(ranked[:TOP_N], start=1):
        if momentum <= 0:
            logger.info("Top-%d %s momentum=%.2f%% <= 0 — skipping rest", rank, symbol, momentum * 100)
            break

        country = COUNTRY_NAMES.get(symbol, symbol)
        confidence = round(
            min(CONFIDENCE_CEIL, CONFIDENCE_BASE + min(0.15, momentum * 0.4) - (rank - 1) * 0.03),
            2,
        )

        reason = (
            f"Country Rotation rank={rank}/{len(ranked)}: {symbol} ({country}) "
            f"3m return={momentum:+.2%} (top-{TOP_N} of {len(COUNTRY_ETFS)} country ETFs)"
        )

        picks.append({
            "symbol": symbol,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "ETF",
            "category": "etf",
            "confidence": confidence,
            "generated_at": now.isoformat(),
            "reason": reason,
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 720,
                "tp_pct": 5.0,
                "sl_pct": 3.0,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Bhoi & Verma (2021)",
            "extra": {
                "momentum_3m": round(momentum, 4),
                "momentum_3m_pct": round(momentum * 100, 2),
                "rank": rank,
                "universe_size": len(ranked),
                "country": country,
                "entry_price": round(price, 4),
                "rebalance": "monthly",
                "exit_rule": "falls_out_of_top_5_or_max_hold_720h",
                "allocation": "equal_weight",
                "top_n": TOP_N,
            },
        })

    logger.info(
        "Generated %d country rotation picks (top ranks: %s)",
        len(picks),
        [(r[0], f"{r[1]:+.2%}") for r in ranked[:TOP_N]],
    )
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_country_rotation_picks()
    print(json.dumps({"strategy": STRATEGY_NAME, "n_picks": len(picks), "picks": picks}, indent=2, default=str))

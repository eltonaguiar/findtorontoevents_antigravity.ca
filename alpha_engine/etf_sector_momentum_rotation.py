"""ETF Sector Momentum Rotation — Jegadeesh & Titman (1993) applied to SPDR sectors.

Academic basis:
  Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers"
  applied to the 11 SPDR sector ETF universe. Sector momentum exploits the
  slow diffusion of information across market sectors — winning sectors
  continue winning over 3-12 month horizons (Moskowitz & Grinblatt 1999).

Logic:
  - Rank 11 SPDR sector ETFs by 3-month (63 trading days) momentum
  - Long top-3 by return, equal-weight
  - Monthly rebalance (signal fires when ranking changes top-3 membership)
  - Exit: falls out of top-5 OR max hold 720h (30 days)

Universe: XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLY, XLRE, XLB, XLC

Forced resolution: max_hold_hours=720, tp_pct=5.0, sl_pct=3.0,
time_exit_at_market=True (ETF class default per forced_resolution.py).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "etf_sector_momentum_rotation"
SPDR_SECTORS: tuple[str, ...] = (
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLRE", "XLB", "XLC",
)
MOMENTUM_LOOKBACK_DAYS = 63
TOP_N = 3
DROP_THRESHOLD = 5  # exit if rank drops below this
CONFIDENCE_BASE = 0.60
CONFIDENCE_CEIL = 0.78


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_sector_data() -> dict[str, Any]:
    """Fetch 6-month OHLCV for all SPDR sector ETFs via yfinance.

    Returns dict of symbol -> DataFrame (or None on failure).
    """
    import yfinance as yf

    data: dict[str, Any] = {}
    try:
        raw = yf.download(
            list(SPDR_SECTORS), period="6mo", group_by="ticker",
            progress=False, threads=False,
        )
        if raw is None or raw.empty:
            logger.warning("yfinance returned empty data for SPDR sectors")
            return data
    except Exception as e:
        logger.error("yfinance download failed: %s", e)
        return data

    for symbol in SPDR_SECTORS:
        try:
            if len(SPDR_SECTORS) == 1:
                df = raw
            else:
                df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
            if df is not None and not df.empty and len(df) >= MOMENTUM_LOOKBACK_DAYS + 5:
                data[symbol] = df.dropna(subset=["Close"])
        except Exception as e:
            logger.warning("Data parse error for %s: %s", symbol, e)

    logger.info("Fetched data for %d/%d SPDR sectors", len(data), len(SPDR_SECTORS))
    return data


def _rank_by_momentum(data: dict[str, Any]) -> list[tuple[str, float, float]]:
    """Rank sectors by 3-month momentum. Returns [(symbol, momentum, price), ...] sorted desc."""
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


def generate_sector_momentum_rotation_picks() -> list[dict[str, Any]]:
    """Generate sector momentum rotation picks.

    Returns LONG picks for the top-3 SPDR sectors by 3-month return.
    Returns [] when data is insufficient.
    """
    data = _fetch_sector_data()
    if len(data) < 5:
        logger.warning("Insufficient sector data (%d symbols) — no picks", len(data))
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

        confidence = round(
            min(CONFIDENCE_CEIL, CONFIDENCE_BASE + min(0.15, momentum * 0.5) - (rank - 1) * 0.03),
            2,
        )

        reason = (
            f"Sector Momentum Rotation rank={rank}/{len(ranked)}: {symbol} "
            f"3m return={momentum:+.2%} (top-{TOP_N} of {len(SPDR_SECTORS)} SPDR sectors)"
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
            "academic_citation": "Jegadeesh & Titman (1993)",
            "extra": {
                "momentum_3m": round(momentum, 4),
                "momentum_3m_pct": round(momentum * 100, 2),
                "rank": rank,
                "universe_size": len(ranked),
                "entry_price": round(price, 4),
                "rebalance": "monthly",
                "exit_rule": "falls_out_of_top_5_or_max_hold_720h",
                "allocation": "equal_weight",
                "top_n": TOP_N,
            },
        })

    logger.info(
        "Generated %d sector momentum picks (top ranks: %s)",
        len(picks),
        [(r[0], f"{r[1]:+.2%}") for r in ranked[:TOP_N]],
    )
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    picks = generate_sector_momentum_rotation_picks()
    print(json.dumps({"strategy": STRATEGY_NAME, "n_picks": len(picks), "picks": picks}, indent=2, default=str))

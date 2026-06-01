"""
Equity Sector ETF Momentum Rotation Strategy
=============================================
Academic basis: Jegadeesh & Titman (1993) applied to sector ETFs.
Edge: Rotating capital into the strongest sector ETFs captures momentum
alpha. Monthly rebalancing into the top-3 sectors by 3-month return,
equal weight.

SPDR Sector ETFs: XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLY, XLRE, XLB, XLC

When a sector falls out of the top-5, exit the position.

Data source: yfinance (free, no API key).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    _HAS_YFINANCE = False

# ---------------------------------------------------------------------------
# Sector ETF Universe
# ---------------------------------------------------------------------------
SECTOR_ETFS: dict[str, str] = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLY": "Consumer Discretionary",
    "XLRE": "Real Estate",
    "XLB": "Materials",
    "XLC": "Communication Services",
}

MOMENTUM_DAYS = 63        # ~3 months of trading days
TOP_N = 3                 # long top-3 sectors
EXIT_RANK = 5             # exit when rank drops below top-5
REBALANCE_CHECK_DAYS = 30 # rebalance monthly
TP_PCT = 0.03             # 3% take-profit
SL_PCT = 0.02             # 2% stop-loss
MAX_HOLD_HOURS = 720      # 30 days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_sector_data(period: str = "6mo") -> dict[str, Any]:
    """Fetch OHLCV for all sector ETFs via yfinance. Returns {symbol: DataFrame}."""
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed")
        return {}

    tickers_str = " ".join(SECTOR_ETFS.keys())
    try:
        data = yf.download(
            tickers_str,
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        logger.error("yfinance download failed: %s", exc)
        return {}

    if data is None or data.empty:
        logger.error("yfinance returned empty data")
        return {}

    result: dict[str, Any] = {}
    for symbol in SECTOR_ETFS:
        try:
            if isinstance(data.columns, __import__("pandas").MultiIndex):
                if symbol not in data.columns.get_level_values(0):
                    continue
                df = data[symbol].dropna()
            else:
                df = data.dropna()

            if df is not None and len(df) >= MOMENTUM_DAYS:
                result[symbol] = df
            else:
                logger.debug("%s: insufficient data (%s rows)", symbol,
                             len(df) if df is not None else 0)
        except Exception as exc:
            logger.debug("%s: data extraction error: %s", symbol, exc)

    return result


def _rank_by_momentum(data: dict[str, Any]) -> list[tuple[str, float, float]]:
    """Rank sector ETFs by 3-month momentum. Returns sorted list of (symbol, momentum, price)."""
    scores: list[tuple[str, float, float]] = []

    for symbol, df in data.items():
        try:
            close = df["Close"]
            if len(close) < MOMENTUM_DAYS:
                continue

            current_price = float(close.iloc[-1])
            price_3m_ago = float(close.iloc[-MOMENTUM_DAYS])
            if price_3m_ago <= 0:
                continue

            momentum = (current_price / price_3m_ago) - 1.0
            scores.append((symbol, momentum, current_price))

        except Exception as exc:
            logger.debug("%s: momentum calc error: %s", symbol, exc)

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ---------------------------------------------------------------------------
# Core strategy
# ---------------------------------------------------------------------------
def equity_sector_rotation_signals(
    symbols: list[str] | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Generate sector rotation LONG signals.

    Ranks 11 SPDR sector ETFs by 3-month return.
    Long top-3, equal weight. Exit when rank drops below top-5.

    Args:
        symbols: Ignored (uses fixed SECTOR_ETFS). Kept for interface compat.
        force: If True, bypass monthly rebalance check (for testing).

    Returns:
        List of pick dicts with all standard Alpha Engine fields.
    """
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed — cannot run equity_sector_rotation")
        return []

    # Monthly rebalance gate: only fire on/around month-end
    now = datetime.now(timezone.utc)
    if not force and now.day < 25:
        logger.info("Not near month-end (day %d), skipping sector rotation", now.day)
        return []

    logger.info("Sector Rotation: fetching data for %d sector ETFs", len(SECTOR_ETFS))

    data = _fetch_sector_data(period="6mo")
    if len(data) < TOP_N:
        logger.warning("Only %d sectors have data, need >= %d", len(data), TOP_N)
        return []

    ranked = _rank_by_momentum(data)
    if len(ranked) < TOP_N:
        logger.warning("Only %d sectors ranked, need >= %d", len(ranked), TOP_N)
        return []

    # Compute stats for confidence scaling
    all_momentums = [m for _, m, _ in ranked]
    mom_mean = float(np.mean(all_momentums))
    mom_std = float(np.std(all_momentums)) if len(all_momentums) > 1 else 0.01

    signals: list[dict[str, Any]] = []

    for rank_idx, (symbol, momentum, price) in enumerate(ranked[:TOP_N]):
        if momentum <= 0:
            logger.info("%s: momentum %.2f%% <= 0, skipping (defensive mode)", symbol, momentum * 100)
            continue

        # Confidence: z-score based, 0.55-0.80 range
        z_score = (momentum - mom_mean) / max(abs(mom_std), 0.001)
        confidence = min(0.80, max(0.55, 0.62 + z_score * 0.05))

        tp = round(price * (1 + TP_PCT), 4)
        sl = round(price * (1 - SL_PCT), 4)

        sector_name = SECTOR_ETFS.get(symbol, "Unknown")

        signals.append({
            "symbol": symbol,
            "direction": "LONG",
            "strategy": "equity_sector_rotation",
            "asset_class": "EQUITY",
            "category": "equity",
            "signal_type": "BUY",
            "entry_price": round(price, 2),
            "take_profit": tp,
            "stop_loss": sl,
            "tp": tp,
            "sl": sl,
            "confidence": round(confidence, 3),
            "risk_reward": round(TP_PCT / SL_PCT, 2),
            "generated_at": _now_iso(),
            "reason": (
                f"Sector rotation rank #{rank_idx + 1}/{len(ranked)}: "
                f"{sector_name} ({symbol}) with 3m momentum "
                f"{momentum * 100:+.1f}%. "
                f"Exit if rank drops below #{EXIT_RANK}."
            ),
            "source": "alpha_engine",
            "source_system": "equity_sector_rotation",
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT * 100,
                "sl_pct": SL_PCT * 100,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Jegadeesh & Titman (1993) 'Returns to Buying Winners and Selling Losers'",
            "extra": {
                "sector_name": sector_name,
                "momentum_3m_pct": round(momentum * 100, 2),
                "rank": rank_idx + 1,
                "total_sectors": len(ranked),
                "exit_rank_threshold": EXIT_RANK,
                "rebalance_frequency": "monthly",
                "hold_days": MAX_HOLD_HOURS // 24,
                "z_score": round(z_score, 3),
                "all_rankings": [
                    {"rank": i + 1, "symbol": s, "momentum_pct": round(m * 100, 2)}
                    for i, (s, m, _) in enumerate(ranked)
                ],
            },
            "timestamp": _now_iso(),
        })

        logger.info(
            "%s: Sector rotation #%d — %s, 3m momentum %.1f%%, conf=%.3f",
            symbol, rank_idx + 1, sector_name, momentum * 100, confidence,
        )

    logger.info("Sector Rotation: %d signals from %d sectors", len(signals), len(ranked))
    return signals


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    print("=" * 60)
    print("Equity Sector ETF Momentum Rotation Strategy")
    print("Jegadeesh & Titman (1993)")
    print("=" * 60)

    picks = equity_sector_rotation_signals(force=True)

    print(f"\nTotal signals: {len(picks)}")
    if picks:
        print(f"{'Rank':<5} {'Symbol':<6} {'Sector':<25} {'Conf':<6} {'Mom%':>7} {'Price':>10}")
        print("-" * 65)
        for p in picks:
            ex = p.get("extra", {})
            print(
                f"{ex.get('rank', '?'):<5} {p['symbol']:<6} "
                f"{ex.get('sector_name', '?'):<25} "
                f"{p['confidence']:<6.2f} "
                f"{ex.get('momentum_3m_pct', 0):>+7.1f} "
                f"${p['entry_price']:>9.2f}"
            )
    else:
        print("No sector rotation signals (not month-end or use --force).")

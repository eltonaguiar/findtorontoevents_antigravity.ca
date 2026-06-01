"""
Equity QMOM Residual Momentum Strategy
=======================================
Academic basis: Asness, Frazzini, Pedersen (JFE 2019) "Quality Minus Junk"
ETF Reference: QMOM (Alpha Architect U.S. Quantitative Momentum ETF)

Strategy Logic:
- Fetch 12-month daily prices for 50 large-cap U.S. equities via yfinance
- Compute 12-1 month momentum (skip most recent month to avoid short-term reversal)
- Residualize each stock's momentum vs SPY beta (OLS regression on daily returns)
- Rank by residualized momentum, long top 5 decile
- Rebalance monthly (check if last trading day of month)
- Hold 1 month, TP +5%, SL -3%

Simplified residualization:
  residual_mom = stock_11m_return - beta_vs_spy * spy_11m_return

Data source: yfinance (free, no API key)
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
# Universe: 50 large-cap U.S. equities
# ---------------------------------------------------------------------------
QMOM_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "V", "JPM", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "CRM", "KO", "PEP", "AVGO", "LLY", "COST", "WMT", "MCD", "CSCO",
    "ACN", "ABT", "DHR", "TXN", "LIN", "NE", "PM", "UNP", "ORCL", "IBM",
    "QCOM", "BA", "GE", "CAT", "SBUX", "AMGN", "LOW", "INTU", "AMD",
    "ISRG", "PLD", "BLK", "SPGI",
]

# ---------------------------------------------------------------------------
# Strategy parameters
# ---------------------------------------------------------------------------
LOOKBACK_MONTHS = 12
SKIP_RECENT_MONTHS = 1  # skip most recent month (short-term reversal filter)
TOP_N = 5
TP_PCT = 0.05       # +5% take-profit
SL_PCT = 0.03       # -3% stop-loss
MAX_HOLD_HOURS = 720  # 30 days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_month_end() -> bool:
    """Check if today is the last trading day of the month (or within 1 day)."""
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(day=now.day + 1) if now.day < 31 else None
    # If tomorrow is the 1st, today is month-end
    if tomorrow and tomorrow.day == 1:
        return True
    # Also trigger on the 28th-31st to be safe (weekends/holidays)
    if now.day >= 28:
        return True
    return False


def _compute_beta(stock_returns: np.ndarray, bench_returns: np.ndarray) -> float:
    """OLS beta = cov(stock, bench) / var(bench)."""
    n = min(len(stock_returns), len(bench_returns))
    if n < 20:
        return 1.0
    s = stock_returns[-n:]
    b = bench_returns[-n:]
    cov_matrix = np.cov(s, b)
    var_b = cov_matrix[1, 1]
    if var_b < 1e-15:
        return 1.0
    return float(cov_matrix[0, 1] / var_b)


# ---------------------------------------------------------------------------
# Core strategy
# ---------------------------------------------------------------------------
def equity_qmom_residual_signals(
    symbols: list[str] | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Generate QMOM Residual Momentum LONG signals.

    Args:
        symbols: Override universe (default: QMOM_UNIVERSE).
        force: If True, bypass month-end rebalance gate (for testing).

    Returns:
        List of pick dicts with all standard Alpha Engine fields.
    """
    if not _HAS_YFINANCE:
        logger.warning("yfinance not installed, cannot run equity_qmom_residual")
        return []

    if not force and not _is_month_end():
        logger.info("Not month-end, skipping QMOM rebalance")
        return []

    universe = symbols or QMOM_UNIVERSE
    tickers_str = " ".join(universe + ["SPY"])

    logger.info("Fetching %d symbols + SPY via yfinance...", len(universe))

    try:
        data = yf.download(
            tickers_str,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        logger.error("yfinance download failed: %s", exc)
        return []

    if data is None or data.empty:
        logger.error("yfinance returned empty data")
        return []

    # Extract SPY close prices for beta benchmark
    try:
        spy_close = data["SPY"]["Close"].dropna()
        if len(spy_close) < 60:
            logger.error("Insufficient SPY data (%d rows)", len(spy_close))
            return []
        spy_returns = np.log(spy_close / spy_close.shift(1)).dropna().values
    except Exception as exc:
        logger.error("Failed to extract SPY data: %s", exc)
        return []

    # Determine the split indices for 12-1 month momentum
    # ~252 trading days/year, ~21 trading days/month
    trading_days_total = len(spy_returns)
    days_per_month = 21
    end_idx = trading_days_total - (SKIP_RECENT_MONTHS * days_per_month)
    start_idx = max(0, trading_days_total - (LOOKBACK_MONTHS * days_per_month))

    if end_idx <= start_idx:
        logger.error("Insufficient trading days for lookback window")
        return []

    spy_window = spy_returns[start_idx:end_idx]
    spy_11m_return = float(np.sum(spy_window))

    # Compute momentum and beta for each stock
    candidates: list[dict[str, Any]] = []

    for symbol in universe:
        try:
            # Handle multi-level columns from yfinance
            if isinstance(data.columns, __import__("pandas").MultiIndex):
                if symbol not in data.columns.get_level_values(0):
                    continue
                close_series = data[symbol]["Close"].dropna()
            else:
                close_series = data["Close"].dropna()

            if len(close_series) < 60:
                continue

            stock_returns = np.log(close_series / close_series.shift(1)).dropna().values

            if len(stock_returns) < end_idx:
                continue

            stock_window = stock_returns[start_idx:end_idx]
            stock_11m_return = float(np.sum(stock_window))

            # Beta vs SPY over the same window
            beta = _compute_beta(stock_window, spy_window)

            # Residualized momentum = stock return - beta * benchmark return
            residual_mom = stock_11m_return - beta * spy_11m_return

            current_price = float(close_series.iloc[-1])

            candidates.append({
                "symbol": symbol,
                "price": current_price,
                "beta": round(beta, 4),
                "raw_mom_12_1": round(stock_11m_return * 100, 3),
                "spy_mom_12_1": round(spy_11m_return * 100, 3),
                "residual_mom": residual_mom,
                "residual_mom_pct": round(residual_mom * 100, 3),
            })

        except Exception as exc:
            logger.debug("Skipping %s: %s", symbol, exc)
            continue

    if len(candidates) < TOP_N:
        logger.warning("Only %d candidates computed, need >= %d", len(candidates), TOP_N)
        return []

    # Rank by residualized momentum (descending)
    candidates.sort(key=lambda x: x["residual_mom"], reverse=True)

    # Compute stats for confidence scaling
    all_residuals = [c["residual_mom"] for c in candidates]
    resid_mean = float(np.mean(all_residuals))
    resid_std = float(np.std(all_residuals)) if len(all_residuals) > 1 else 0.01

    # Select top N with positive residual momentum
    top_picks = [c for c in candidates[:TOP_N] if c["residual_mom"] > 0]

    signals: list[dict[str, Any]] = []

    for rank_idx, pick in enumerate(top_picks):
        symbol = pick["symbol"]
        price = pick["price"]
        tp = round(price * (1 + TP_PCT), 2)
        sl = round(price * (1 - SL_PCT), 2)

        # Confidence: scale 0.60-0.85 by z-score of residual momentum
        z_score = (pick["residual_mom"] - resid_mean) / max(abs(resid_std), 0.001)
        confidence = min(0.85, max(0.60, 0.65 + z_score * 0.05))

        signals.append({
            "symbol": symbol,
            "direction": "LONG",
            "strategy": "equity_qmom_residual",
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
                f"QMOM Residual Momentum: residual={pick['residual_mom_pct']:+.2f}% "
                f"(rank {rank_idx + 1}/{len(candidates)}), "
                f"beta={pick['beta']:.2f}, "
                f"12-1m raw={pick['raw_mom_12_1']:+.1f}%, "
                f"SPY 12-1m={pick['spy_mom_12_1']:+.1f}%"
            ),
            "source": "alpha_engine",
            "source_system": "equity_qmom_residual",
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT * 100,
                "sl_pct": SL_PCT * 100,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Asness-Frazzini-Pedersen (JFE 2019)",
            "extra": {
                "residual_mom_pct": pick["residual_mom_pct"],
                "raw_mom_12_1_pct": pick["raw_mom_12_1"],
                "spy_mom_12_1_pct": pick["spy_mom_12_1"],
                "beta_vs_spy": pick["beta"],
                "z_score": round(z_score, 3),
                "rank": rank_idx + 1,
                "universe_size": len(candidates),
                "lookback_months": LOOKBACK_MONTHS,
                "skip_recent_months": SKIP_RECENT_MONTHS,
                "rebalance": "monthly",
            },
            "timestamp": _now_iso(),
        })

    logger.info(
        "QMOM Residual: %d candidates, %d signals generated",
        len(candidates),
        len(signals),
    )

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
    print("Equity QMOM Residual Momentum Strategy")
    print("Asness, Frazzini, Pedersen (JFE 2019)")
    print("=" * 60)

    picks = equity_qmom_residual_signals(force=True)

    print(f"\nTotal signals: {len(picks)}")
    if picks:
        print(f"{'Rank':<5} {'Symbol':<8} {'Direction':<7} {'Conf':<6} "
              f"{'Resid%':>8} {'Raw%':>8} {'Beta':>6} {'Price':>10}")
        print("-" * 65)
        for p in picks:
            ex = p.get("extra", {})
            print(f"{ex.get('rank', '?'):<5} {p['symbol']:<8} {p['direction']:<7} "
                  f"{p['confidence']:<6.2f} {ex.get('residual_mom_pct', 0):>+8.2f} "
                  f"{ex.get('raw_mom_12_1_pct', 0):>+8.1f} "
                  f"{ex.get('beta_vs_spy', 0):>6.2f} "
                  f"${p['entry_price']:>9.2f}")
    else:
        print("No signals generated (not month-end or data unavailable).")
        print("Use --force flag: equity_qmom_residual_signals(force=True)")

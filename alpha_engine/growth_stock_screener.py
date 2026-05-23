"""Growth Stock Screener — adapted from starboi-63/growth-stock-screener.

Five-stage screen (verbatim thresholds from upstream `settings.py`):
  1. RS Rating >= 90        — weighted 12mo percentile (40% Q1 + 20% Q2/Q3/Q4)
  2. Liquidity              — market_cap >= $1B, price >= $10, 50d avg vol >= 100k
  3. Stage-2 uptrend        — price >= SMA50 >= SMA200, SMA10 >= SMA20 >= SMA50,
                              price within 50% of 52w high
  4. Revenue growth         — most recent quarterly revenue YoY >= 25%
                              (exception: RS >= 97 bypass)
  5. Institutional accum.   — net inst ownership change > 0 (FLAG ONLY, not filter)

OPT-IN SIDECAR per CLAUDE.md Wire-Up Rule. DEFAULT-OFF gated on
`GROWTH_STOCK_SCREENER_ENABLED=1`. Read-only data ingest. No trading.

Wiring plan: emit picks JSON to `audit_dashboard/data/growth_stock_picks.json`
via `.github/workflows/growth-stock-screener-daily.yml`. Production scorer
wire-in (calculate_smart_score / dashboard_generator) tracked in follow-up PR.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STRATEGY_NAME = "growth_stock_screener"
ASSET_CLASS = "EQUITY"
SOURCE_SYSTEM = "growth_stock_screener"

# --- Thresholds (env-configurable; defaults match user 2026-05-12 config) ---
# Per upstream `growth_stock_screener/screen/settings.py` AND user screenshot:
#   MIN_MARKET_CAP: upstream=$1B, user=$2B (override via GSS_MIN_MARKET_CAP)
#   MIN_REVENUE_GROWTH_PCT: upstream=25%, user=15% (override via GSS_MIN_REV_GROWTH_PCT)
RS_RATING_MIN = int(os.environ.get("GSS_MIN_RS", "90"))
RS_RATING_REVENUE_BYPASS = int(os.environ.get("GSS_RS_REV_BYPASS", "97"))
MIN_MARKET_CAP = int(os.environ.get("GSS_MIN_MARKET_CAP", "2000000000"))  # $2B (user)
MIN_PRICE = float(os.environ.get("GSS_MIN_PRICE", "10.0"))
MIN_AVG_VOLUME_50D = int(os.environ.get("GSS_MIN_VOLUME", "100000"))
MIN_REVENUE_GROWTH_PCT = float(os.environ.get("GSS_MIN_REV_GROWTH_PCT", "15.0"))  # 15% (user)
MAX_DRAWDOWN_FROM_52W_HIGH = float(os.environ.get("GSS_MAX_DD_52W", "0.50"))  # within 50%

# --- Pick shape ---
TAKE_PROFIT_PCT = 0.20  # +20%
STOP_LOSS_PCT = 0.07    # -7% (CANSLIM-style stop)

CACHE_DIR = Path("data/growth_screener_cache")
LOG = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.environ.get("GROWTH_STOCK_SCREENER_ENABLED", "").strip() == "1"


# ---------------------------------------------------------------------------
# RS Rating
# ---------------------------------------------------------------------------
def _quarter_return(closes: list[float], lookback_days: int, end_idx: int) -> float | None:
    """Return % over the prior `lookback_days` ending at index `end_idx`."""
    start_idx = end_idx - lookback_days
    if start_idx < 0 or end_idx >= len(closes):
        return None
    start = closes[start_idx]
    end = closes[end_idx]
    if start <= 0:
        return None
    return (end - start) / start


def _weighted_12mo_return(closes: list[float]) -> float | None:
    """Upstream IBD-style weighted return: 40% Q1 + 20% Q2 + 20% Q3 + 20% Q4.

    Quarters are 63 trading days each (~252/4). End_idx is last bar.
    """
    if len(closes) < 252:
        return None
    end_idx = len(closes) - 1
    q1 = _quarter_return(closes, 63, end_idx)
    q2 = _quarter_return(closes, 126, end_idx)
    q3 = _quarter_return(closes, 189, end_idx)
    q4 = _quarter_return(closes, 252, end_idx)
    if None in (q1, q2, q3, q4):
        return None
    return 0.40 * q1 + 0.20 * q2 + 0.20 * q3 + 0.20 * q4


def compute_rs_rating(prices_by_symbol: dict[str, list[float]]) -> dict[str, float]:
    """Compute RS Rating (0-100 percentile) per symbol from weighted 12mo returns.

    Symbols with insufficient history are excluded from the output map.
    """
    weighted: dict[str, float] = {}
    for sym, closes in prices_by_symbol.items():
        wr = _weighted_12mo_return(closes)
        if wr is not None:
            weighted[sym] = wr
    if not weighted:
        return {}
    sorted_syms = sorted(weighted.items(), key=lambda kv: kv[1])
    n = len(sorted_syms)
    out: dict[str, float] = {}
    for rank, (sym, _) in enumerate(sorted_syms):
        # Percentile: 0 worst -> 100 best
        pct = (rank / (n - 1)) * 100.0 if n > 1 else 100.0
        out[sym] = round(pct, 2)
    return out


# ---------------------------------------------------------------------------
# Stage-2 Uptrend
# ---------------------------------------------------------------------------
def _sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def stage_2_uptrend(ohlcv_df: Any) -> bool:
    """Return True iff:
      - price >= SMA50 AND price >= SMA200
      - SMA10 >= SMA20 >= SMA50
      - price within 50% of 52w high

    Accepts a pandas DataFrame with 'Close' column OR a list[float] of closes.
    """
    if ohlcv_df is None:
        return False
    try:
        # Support both DataFrame and list[float]
        if hasattr(ohlcv_df, "__getitem__") and hasattr(ohlcv_df, "columns"):
            closes = [float(x) for x in ohlcv_df["Close"].tolist()]
        else:
            closes = [float(x) for x in ohlcv_df]
    except Exception:
        return False
    if len(closes) < 200:
        return False
    price = closes[-1]
    sma10 = _sma(closes, 10)
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    if None in (sma10, sma20, sma50, sma200):
        return False
    if not (price >= sma50 and price >= sma200):
        return False
    if not (sma10 >= sma20 >= sma50):
        return False
    high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    if high_52w <= 0:
        return False
    drawdown = (high_52w - price) / high_52w
    if drawdown > MAX_DRAWDOWN_FROM_52W_HIGH:
        return False
    return True


# ---------------------------------------------------------------------------
# Revenue Growth
# ---------------------------------------------------------------------------
def revenue_growth_pct(ticker: Any) -> float | None:
    """Most recent quarterly revenue YoY growth %.

    `ticker` is a yfinance.Ticker-like object exposing `.quarterly_financials`
    (DataFrame indexed by line item, columns are quarter-end dates desc).
    Looks for "Total Revenue" row, computes (Q_latest - Q_year_ago) / Q_year_ago.
    Returns None on any missing data.
    """
    if ticker is None:
        return None
    try:
        qf = getattr(ticker, "quarterly_financials", None)
        if qf is None:
            return None
        # Find Total Revenue row (case/space-insensitive)
        rev_row = None
        try:
            index_iter = list(qf.index)
        except Exception:
            return None
        for label in index_iter:
            if isinstance(label, str) and label.strip().lower() in (
                "total revenue", "totalrevenue", "revenue"
            ):
                rev_row = qf.loc[label]
                break
        if rev_row is None:
            return None
        values = [float(v) for v in rev_row.tolist() if v is not None and v == v]
        # yfinance returns columns most-recent-first; we need Q_latest and Q_~4_quarters_ago
        if len(values) < 4:
            return None
        latest = values[0]
        year_ago = values[3]
        if year_ago <= 0:
            return None
        return ((latest - year_ago) / year_ago) * 100.0
    except Exception as exc:
        LOG.debug("revenue_growth_pct failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Institutional accumulation (flag only)
# ---------------------------------------------------------------------------
def _net_inst_change(ticker: Any) -> bool | None:
    """Return True if net institutional ownership delta > 0, False if <=0, None if unknown."""
    if ticker is None:
        return None
    try:
        holders = getattr(ticker, "institutional_holders", None)
        if holders is None or len(holders) == 0:
            return None
        if "% Change" in holders.columns:
            net = float(holders["% Change"].sum())
            return net > 0
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pick generation
# ---------------------------------------------------------------------------
def _confidence_from_rs(rs: float) -> float:
    """Map RS 90..100 -> confidence 0.60..0.75 (linear)."""
    rs = max(90.0, min(100.0, rs))
    return round(0.60 + (rs - 90.0) / 10.0 * 0.15, 4)


def _ensure_cache_dir() -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _fetch_history(symbol: str, period: str = "13mo") -> Any | None:
    """Fetch ~13 months of daily OHLCV via yfinance, cached locally."""
    _ensure_cache_dir()
    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:
        LOG.warning("yfinance unavailable: %s", exc)
        return None
    cache_path = CACHE_DIR / f"{symbol}_ohlcv.json"
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period=period, auto_adjust=False)
        if hist is None or len(hist) == 0:
            return None
        # Cache closes for reproducibility
        try:
            closes = [float(x) for x in hist["Close"].tolist()]
            cache_path.write_text(json.dumps({"closes": closes,
                                              "fetched_at": datetime.now(timezone.utc).isoformat()}))
        except Exception:
            pass
        return hist
    except Exception as exc:
        LOG.debug("fetch_history(%s) failed: %s", symbol, exc)
        return None


def _fetch_ticker(symbol: str) -> Any | None:
    try:
        import yfinance as yf  # type: ignore
        return yf.Ticker(symbol)
    except Exception:
        return None


def generate_picks(universe: list[str], max_picks: int = 30) -> list[dict]:
    """Run the 5-stage screen on `universe`, return up to `max_picks` picks.

    Returns [] if DEFAULT-OFF (env flag missing), if yfinance fails wholesale,
    or if no symbol clears the screen. Graceful per-symbol failure.
    """
    if not _enabled():
        LOG.info("growth_stock_screener disabled (GROWTH_STOCK_SCREENER_ENABLED!=1)")
        return []
    if not universe:
        return []

    # --- Stage 1 prep: fetch closes for ALL symbols (RS is relative) ---
    prices_by_symbol: dict[str, list[float]] = {}
    histories: dict[str, Any] = {}
    for sym in universe:
        hist = _fetch_history(sym)
        if hist is None or len(hist) < 252:
            continue
        try:
            closes = [float(x) for x in hist["Close"].tolist()]
        except Exception:
            continue
        prices_by_symbol[sym] = closes
        histories[sym] = hist

    if not prices_by_symbol:
        return []

    rs_map = compute_rs_rating(prices_by_symbol)

    candidates: list[dict] = []
    for sym, rs in rs_map.items():
        # Stage 1: RS >= 90
        if rs < RS_RATING_MIN:
            continue
        hist = histories.get(sym)
        if hist is None:
            continue
        closes = prices_by_symbol[sym]
        price = closes[-1]
        # Stage 2: Liquidity
        if price < MIN_PRICE:
            continue
        tk = _fetch_ticker(sym)
        market_cap = None
        try:
            info = getattr(tk, "info", {}) if tk is not None else {}
            market_cap = info.get("marketCap") if isinstance(info, dict) else None
        except Exception:
            market_cap = None
        if market_cap is None or market_cap < MIN_MARKET_CAP:
            continue
        try:
            avg_vol_50 = float(sum(hist["Volume"].tolist()[-50:]) / 50.0)
        except Exception:
            avg_vol_50 = 0.0
        if avg_vol_50 < MIN_AVG_VOLUME_50D:
            continue
        # Stage 3: Stage-2 uptrend
        if not stage_2_uptrend(closes):
            continue
        # Stage 4: Revenue growth (RS>=97 bypass)
        rev_growth = revenue_growth_pct(tk)
        if rs < RS_RATING_REVENUE_BYPASS:
            if rev_growth is None or rev_growth < MIN_REVENUE_GROWTH_PCT:
                continue
        # Stage 5: Institutional accumulation (flag only)
        inst_pos = _net_inst_change(tk)

        entry = round(price, 4)
        pick = {
            "symbol": sym,
            "direction": "LONG",
            "entry_price": entry,
            "take_profit": round(entry * (1.0 + TAKE_PROFIT_PCT), 4),
            "stop_loss": round(entry * (1.0 - STOP_LOSS_PCT), 4),
            "confidence": _confidence_from_rs(rs),
            "strategy": STRATEGY_NAME,
            "asset_class": ASSET_CLASS,
            "source_system": SOURCE_SYSTEM,
            "signal_strength": round(rs / 100.0, 4),
            "rs_rating": rs,
            "revenue_growth_pct": rev_growth,
            "institutional_accumulation": inst_pos,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        candidates.append(pick)

    # Rank by RS desc, cap at max_picks
    candidates.sort(key=lambda p: p["rs_rating"], reverse=True)
    return candidates[:max_picks]


# ---------------------------------------------------------------------------
# CLI entrypoint (used by workflow)
# ---------------------------------------------------------------------------
def _default_universe() -> list[str]:
    """Lightweight default NASDAQ+NYSE common-stock list (large-cap growth bias).

    Sized small for reliability; a future PR can swap in a full ticker pull.
    """
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "AMD",
        "NFLX", "COST", "ADBE", "CRM", "INTU", "QCOM", "AMAT", "MU", "LRCX",
        "PANW", "SNPS", "CDNS", "MELI", "ABNB", "MAR", "BKNG", "ORCL", "NOW",
        "UBER", "SHOP", "PLTR", "ARM", "SMCI", "VRTX", "REGN", "LLY", "UNH",
        "JPM", "V", "MA", "BRK-B", "XOM", "CVX", "WMT", "HD", "PG", "JNJ",
    ]


def _emit_picks_file(picks: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY_NAME,
        "asset_class": ASSET_CLASS,
        "total_picks": len(picks),
        "picks": picks,
    }
    out_path.write_text(json.dumps(payload, indent=2))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not _enabled():
        LOG.info("growth_stock_screener: DEFAULT-OFF (set GROWTH_STOCK_SCREENER_ENABLED=1 to enable)")
        # Still emit an empty-shell file so the workflow has something to upload
        out = Path("audit_dashboard/data/growth_stock_picks.json")
        _emit_picks_file([], out)
        return 0
    universe = _default_universe()
    LOG.info("growth_stock_screener: scanning %d symbols", len(universe))
    picks = generate_picks(universe)
    LOG.info("growth_stock_screener: emitted %d picks", len(picks))
    out = Path("audit_dashboard/data/growth_stock_picks.json")
    _emit_picks_file(picks, out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

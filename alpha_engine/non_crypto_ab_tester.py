"""Non-Crypto A/B Portfolio Testing Module.

Tracks two portfolio variants over time to compare conservative vs aggressive
non-crypto allocation strategies. Snapshots are appended every 6 hours during
US market hours and metrics are computed from the accumulated history.

Usage (CLI):
    python -m alpha_engine.non_crypto_ab_tester          # run comparison
    python -m alpha_engine.non_crypto_ab_tester --report  # generate JSON report
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DIR = Path(__file__).resolve().parent
_DATA_DIR = _DIR / "data"
_HISTORY_FILE = _DATA_DIR / "non_crypto_ab_history.json"
_REPORT_FILE = _DATA_DIR / "non_crypto_ab_report.json"

# ---------------------------------------------------------------------------
# Portfolio Definitions
# ---------------------------------------------------------------------------

PORTFOLIO_A: List[Dict[str, Any]] = [
    # Blue chips — 40 %
    {"symbol": "AAPL",  "weight": 0.08, "category": "blue_chip", "thesis": "Cash-flow king with services moat and buyback machine"},
    {"symbol": "MSFT",  "weight": 0.08, "category": "blue_chip", "thesis": "Cloud + AI dominance with recurring enterprise revenue"},
    {"symbol": "JNJ",   "weight": 0.08, "category": "blue_chip", "thesis": "Healthcare staple with 60+ year dividend streak"},
    {"symbol": "PG",    "weight": 0.08, "category": "blue_chip", "thesis": "Consumer staples pricing power through any cycle"},
    {"symbol": "KO",    "weight": 0.08, "category": "blue_chip", "thesis": "Global brand portfolio with inflation pass-through"},
    # Financials — 20 %
    {"symbol": "BRK-B", "weight": 0.10, "category": "financial",  "thesis": "Diversified conglomerate with $150B+ cash hoard"},
    {"symbol": "JPM",   "weight": 0.10, "category": "financial",  "thesis": "Largest US bank with fortress balance sheet"},
    # Bonds — 30 %
    {"symbol": "TLT",   "weight": 0.15, "category": "bond",       "thesis": "Long-duration Treasuries hedge equity drawdowns"},
    {"symbol": "BND",   "weight": 0.15, "category": "bond",       "thesis": "Broad bond index for stable income and low vol"},
    # Gold — 10 %
    {"symbol": "GLD",   "weight": 0.10, "category": "gold",       "thesis": "Inflation hedge and crisis safe haven"},
]

PORTFOLIO_B: List[Dict[str, Any]] = [
    # Growth — 50 %
    {"symbol": "NVDA",  "weight": 0.10, "category": "growth",         "thesis": "AI compute monopoly with 80%+ data-center GPU share"},
    {"symbol": "TSLA",  "weight": 0.10, "category": "growth",         "thesis": "EV + energy + robotics optionality play"},
    {"symbol": "AMD",   "weight": 0.10, "category": "growth",         "thesis": "Gaining server CPU and AI GPU share from Intel/Nvidia"},
    {"symbol": "AMZN",  "weight": 0.10, "category": "growth",         "thesis": "AWS + e-commerce + ads triple engine"},
    {"symbol": "META",  "weight": 0.10, "category": "growth",         "thesis": "3B+ user base monetised via AI-driven ad targeting"},
    # Sector ETFs — 30 %
    {"symbol": "XLK",   "weight": 0.10, "category": "sector_etf",     "thesis": "Broad tech exposure beyond mega-caps"},
    {"symbol": "XLE",   "weight": 0.10, "category": "sector_etf",     "thesis": "Energy sector benefiting from capex under-investment"},
    {"symbol": "XLF",   "weight": 0.10, "category": "sector_etf",     "thesis": "Financials benefit from higher-for-longer rates"},
    # Crypto-adjacent — 10 %
    {"symbol": "MARA",  "weight": 0.05, "category": "crypto_adjacent", "thesis": "Bitcoin mining proxy with BTC upside leverage"},
    {"symbol": "RIOT",  "weight": 0.05, "category": "crypto_adjacent", "thesis": "BTC miner with growing hash rate and energy assets"},
    # Commodities — 10 %
    {"symbol": "USO",   "weight": 0.05, "category": "commodity",      "thesis": "Oil ETF for energy inflation hedge"},
    {"symbol": "GDX",   "weight": 0.05, "category": "commodity",      "thesis": "Gold miners offer leveraged gold upside"},
]

# ---------------------------------------------------------------------------
# Market-hours check (NYSE: 09:30 – 16:00 ET, Mon–Fri)
# ---------------------------------------------------------------------------

def _is_market_hours(now_utc: Optional[_dt.datetime] = None) -> bool:
    """Return True when US equity markets are open (rough check)."""
    now_utc = now_utc or _dt.datetime.now(_dt.timezone.utc)
    # Convert to US/Eastern (UTC-5 standard, UTC-4 DST — simplified)
    # Use a rough offset; proper tz handling would need zoneinfo (3.9+)
    try:
        from zoneinfo import ZoneInfo
        et = now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        # Fallback: assume UTC-4 (EDT) which covers most of the year
        et = now_utc - _dt.timedelta(hours=4)
        et = et.replace(tzinfo=_dt.timezone(_dt.timedelta(hours=-4)))

    weekday = et.weekday()  # Mon=0 … Sun=6
    if weekday >= 5:
        return False
    hour, minute = et.hour, et.minute
    # 09:30 – 16:00 ET
    if hour < 9 or (hour == 9 and minute < 30):
        return False
    if hour >= 16:
        return False
    return True


# ---------------------------------------------------------------------------
# Price fetching — yfinance primary, Alpha Vantage free fallback
# ---------------------------------------------------------------------------

def fetch_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch latest prices for *symbols*. Returns {symbol: price}."""
    prices: Dict[str, float] = {}

    # --- Attempt 1: yfinance --------------------------------------------------
    try:
        prices = _fetch_yfinance(symbols)
    except Exception:
        pass

    missing = [s for s in symbols if s not in prices or prices[s] <= 0]
    if not missing:
        return prices

    # --- Attempt 2: Alpha Vantage free tier -----------------------------------
    try:
        av_prices = _fetch_alpha_vantage(missing)
        prices.update(av_prices)
    except Exception:
        pass

    missing = [s for s in symbols if s not in prices or prices[s] <= 0]
    if not missing:
        return prices

    # --- Attempt 3: Yahoo Finance v8 JSON (no library) ------------------------
    try:
        yahoo_prices = _fetch_yahoo_json(missing)
        prices.update(yahoo_prices)
    except Exception:
        pass

    return prices


def _fetch_yfinance(symbols: List[str]) -> Dict[str, float]:
    import yfinance as yf  # type: ignore[import-untyped]

    prices: Dict[str, float] = {}
    tickers = yf.Tickers(" ".join(symbols))
    for sym in symbols:
        try:
            info = tickers.tickers[sym].fast_info
            price = getattr(info, "last_price", None) or getattr(info, "previous_close", None)
            if price and float(price) > 0:
                prices[sym] = round(float(price), 4)
        except Exception:
            continue
    return prices


def _fetch_alpha_vantage(symbols: List[str]) -> Dict[str, float]:
    import requests

    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")
    prices: Dict[str, float] = {}
    for sym in symbols:
        try:
            url = (
                f"https://www.alphavantage.co/query"
                f"?function=GLOBAL_QUOTE&symbol={sym}&apikey={api_key}"
            )
            r = requests.get(url, timeout=10)
            data = r.json()
            price_str = data.get("Global Quote", {}).get("05. price", "0")
            price = float(price_str)
            if price > 0:
                prices[sym] = round(price, 4)
        except Exception:
            continue
    return prices


def _fetch_yahoo_json(symbols: List[str]) -> Dict[str, float]:
    """Scrape Yahoo Finance chart endpoint — no library needed."""
    import requests

    prices: Dict[str, float] = {}
    for sym in symbols:
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
                f"?interval=1d&range=1d"
            )
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            meta = data["chart"]["result"][0]["meta"]
            price = float(meta.get("regularMarketPrice", 0))
            if price > 0:
                prices[sym] = round(price, 4)
        except Exception:
            continue
    return prices


# ---------------------------------------------------------------------------
# Portfolio value & history
# ---------------------------------------------------------------------------

def compute_portfolio_value(
    portfolio: List[Dict[str, Any]],
    prices: Dict[str, float],
    start_capital: float = 10_000.0,
) -> Dict[str, Any]:
    """Compute weighted NAV for a portfolio given current prices.

    Returns dict with nav, holdings breakdown, and missing symbols.
    """
    holdings: List[Dict[str, Any]] = []
    total_value = 0.0
    missing: List[str] = []

    for entry in portfolio:
        sym = entry["symbol"]
        weight = entry["weight"]
        allocation = start_capital * weight
        price = prices.get(sym, 0.0)
        if price <= 0:
            missing.append(sym)
            holdings.append({"symbol": sym, "shares": 0, "value": 0, "weight": weight})
            continue
        shares = allocation / price
        value = shares * price  # == allocation when first computed
        total_value += value
        holdings.append({
            "symbol": sym,
            "shares": round(shares, 6),
            "price": price,
            "value": round(value, 2),
            "weight": weight,
        })

    return {
        "nav": round(total_value, 2),
        "holdings": holdings,
        "missing_symbols": missing,
        "capital": start_capital,
    }


def _load_history() -> Dict[str, Any]:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"portfolio_a": [], "portfolio_b": [], "start_capital": 10_000.0}


def _save_history(history: Dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(
        json.dumps(history, indent=2, default=str), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute portfolio performance metrics from a list of NAV snapshots.

    Each snapshot must have at least ``nav`` and ``timestamp`` keys.
    """
    if len(snapshots) < 2:
        return {
            "total_return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate": 0.0,
            "num_snapshots": len(snapshots),
        }

    navs = [s["nav"] for s in snapshots if s.get("nav", 0) > 0]
    if len(navs) < 2:
        return {
            "total_return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate": 0.0,
            "num_snapshots": len(navs),
        }

    # Period returns
    returns = [(navs[i] / navs[i - 1]) - 1.0 for i in range(1, len(navs))]

    total_return_pct = round(((navs[-1] / navs[0]) - 1.0) * 100, 2)

    # Win rate (positive return periods)
    wins = sum(1 for r in returns if r > 0)
    win_rate = round(wins / len(returns) * 100, 2) if returns else 0.0

    # Sharpe (annualised assuming 4 snapshots/day × 252 trading days)
    mean_r = sum(returns) / len(returns)
    std_r = _std(returns)
    periods_per_year = 4 * 252  # 6-hour intervals
    sharpe = 0.0
    if std_r > 0:
        sharpe = round((mean_r / std_r) * math.sqrt(periods_per_year), 2)

    # Sortino (downside deviation only)
    downside = [r for r in returns if r < 0]
    down_std = _std(downside) if downside else 0.0
    sortino = 0.0
    if down_std > 0:
        sortino = round((mean_r / down_std) * math.sqrt(periods_per_year), 2)

    # Max drawdown
    peak = navs[0]
    max_dd = 0.0
    for n in navs:
        if n > peak:
            peak = n
        dd = (peak - n) / peak
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = round(max_dd * 100, 2)

    return {
        "total_return_pct": total_return_pct,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate": win_rate,
        "num_snapshots": len(navs),
    }


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


# ---------------------------------------------------------------------------
# A/B Comparison
# ---------------------------------------------------------------------------

def run_ab_comparison(force: bool = False) -> Dict[str, Any]:
    """Run the A/B comparison cycle.

    1. Load history
    2. Fetch fresh prices (skip if outside market hours unless *force*)
    3. Append NAV snapshots
    4. Compute metrics
    5. Print comparison table
    """
    now_utc = _dt.datetime.now(_dt.timezone.utc)

    if not force and not _is_market_hours(now_utc):
        print(f"[AB-Tester] Market closed at {now_utc.isoformat()}. Use --force to override.")
        history = _load_history()
        metrics_a = compute_metrics(history.get("portfolio_a", []))
        metrics_b = compute_metrics(history.get("portfolio_b", []))
        _print_comparison(metrics_a, metrics_b, history)
        return {"status": "market_closed", "metrics_a": metrics_a, "metrics_b": metrics_b}

    # Gather all unique symbols
    all_symbols = list({e["symbol"] for e in PORTFOLIO_A + PORTFOLIO_B})
    print(f"[AB-Tester] Fetching prices for {len(all_symbols)} symbols ...")
    prices = fetch_prices(all_symbols)
    print(f"[AB-Tester] Got prices for {len(prices)}/{len(all_symbols)} symbols")

    if not prices:
        print("[AB-Tester] ERROR: No prices fetched. Aborting snapshot.")
        return {"status": "error", "reason": "no_prices"}

    history = _load_history()
    start_capital = history.get("start_capital", 10_000.0)

    # If this is NOT the first snapshot, recompute NAV based on shares from
    # the initial allocation (track actual growth, not re-balanced value).
    timestamp = now_utc.isoformat()

    for label, portfolio, key in [
        ("A (Conservative)", PORTFOLIO_A, "portfolio_a"),
        ("B (Aggressive)", PORTFOLIO_B, "portfolio_b"),
    ]:
        pv = compute_portfolio_value(portfolio, prices, start_capital)
        snapshot = {
            "timestamp": timestamp,
            "nav": pv["nav"],
            "missing": pv["missing_symbols"],
        }
        history.setdefault(key, []).append(snapshot)

    _save_history(history)

    metrics_a = compute_metrics(history["portfolio_a"])
    metrics_b = compute_metrics(history["portfolio_b"])

    _print_comparison(metrics_a, metrics_b, history)

    return {"status": "ok", "metrics_a": metrics_a, "metrics_b": metrics_b}


def _print_comparison(
    metrics_a: Dict[str, Any],
    metrics_b: Dict[str, Any],
    history: Dict[str, Any],
) -> None:
    """Print a formatted comparison table to stdout."""
    snap_a = history.get("portfolio_a", [])
    snap_b = history.get("portfolio_b", [])
    nav_a = snap_a[-1]["nav"] if snap_a else 0
    nav_b = snap_b[-1]["nav"] if snap_b else 0

    header = f"{'Metric':<25} {'A (Conservative)':>18} {'B (Aggressive)':>18}"
    sep = "-" * 63
    print(f"\n{sep}")
    print("  NON-CRYPTO A/B PORTFOLIO COMPARISON")
    print(sep)
    print(header)
    print(sep)
    rows = [
        ("Current NAV",       f"${nav_a:,.2f}",                    f"${nav_b:,.2f}"),
        ("Total Return",      f"{metrics_a['total_return_pct']}%",  f"{metrics_b['total_return_pct']}%"),
        ("Sharpe Ratio",      f"{metrics_a['sharpe']}",             f"{metrics_b['sharpe']}"),
        ("Sortino Ratio",     f"{metrics_a['sortino']}",            f"{metrics_b['sortino']}"),
        ("Max Drawdown",      f"{metrics_a['max_drawdown_pct']}%",  f"{metrics_b['max_drawdown_pct']}%"),
        ("Win Rate",          f"{metrics_a['win_rate']}%",          f"{metrics_b['win_rate']}%"),
        ("Snapshots",         f"{metrics_a['num_snapshots']}",      f"{metrics_b['num_snapshots']}"),
    ]
    for label, va, vb in rows:
        print(f"  {label:<23} {va:>18} {vb:>18}")
    print(sep)
    if nav_a and nav_b:
        leader = "A (Conservative)" if nav_a >= nav_b else "B (Aggressive)"
        diff = abs(nav_a - nav_b)
        print(f"  Leader: {leader}  (+${diff:,.2f})")
    print(sep + "\n")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report() -> str:
    """Save a JSON report to data/non_crypto_ab_report.json. Returns path."""
    history = _load_history()
    metrics_a = compute_metrics(history.get("portfolio_a", []))
    metrics_b = compute_metrics(history.get("portfolio_b", []))

    snap_a = history.get("portfolio_a", [])
    snap_b = history.get("portfolio_b", [])

    report = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "start_capital": history.get("start_capital", 10_000.0),
        "portfolio_a": {
            "name": "Conservative",
            "symbols": [e["symbol"] for e in PORTFOLIO_A],
            "weights": {e["symbol"]: e["weight"] for e in PORTFOLIO_A},
            "latest_nav": snap_a[-1]["nav"] if snap_a else 0,
            "metrics": metrics_a,
            "snapshot_count": len(snap_a),
        },
        "portfolio_b": {
            "name": "Aggressive",
            "symbols": [e["symbol"] for e in PORTFOLIO_B],
            "weights": {e["symbol"]: e["weight"] for e in PORTFOLIO_B},
            "latest_nav": snap_b[-1]["nav"] if snap_b else 0,
            "metrics": metrics_b,
            "snapshot_count": len(snap_b),
        },
        "leader": "A" if (
            (snap_a[-1]["nav"] if snap_a else 0) >= (snap_b[-1]["nav"] if snap_b else 0)
        ) else "B",
    }

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = str(_REPORT_FILE)
    _REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"[AB-Tester] Report saved to {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    force = "--force" in sys.argv
    if "--report" in sys.argv:
        run_ab_comparison(force=force)
        generate_report()
    else:
        run_ab_comparison(force=force)


if __name__ == "__main__":
    main()

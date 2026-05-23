#!/usr/bin/env python3
"""
Cross-Asset Correlation Monitor
================================
Tracks rolling correlations between all active picks, BTC, ETH, SPY, and DXY(UUP).
Computes portfolio diversification score, generates concentration alerts, and
exports correlation-adjusted position sizing penalties.

Wired into production_scanner.py alongside Kelly sizing.
Runs standalone every 6 hours via correlation-monitor.yml.

Output: data/correlation_report.json
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DIR = Path(__file__).resolve().parent
_DATA_DIR = _DIR / "data"
_ACTIVE_PICKS_PATH = _DATA_DIR / "active_picks.json"
_REPORT_PATH = _DATA_DIR / "correlation_report.json"

sys.path.insert(0, str(_DIR))

try:
    from config import SPOT_BASES, COINGECKO_BASE, CRYPTOCOMPARE_BASE
except ImportError:
    SPOT_BASES = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ]
    COINGECKO_BASE = "https://api.coingecko.com/api/v3"
    CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROLLING_WINDOW_DAYS = 30
HIGH_CORR_THRESHOLD = 0.70
LOW_CORR_THRESHOLD = 0.30
EXTREME_CORR_THRESHOLD = 0.80
BTC_PORTFOLIO_CORR_ALERT = 0.85
MAX_SINGLE_CONCENTRATION_PCT = 0.15  # 15% of capital
MAX_ASSET_CLASS_PCT = 0.60           # 60% of picks

# Cross-asset benchmark symbols
BENCHMARKS = {
    "BTCUSDT": "crypto",
    "ETHUSDT": "crypto",
}
# SPY and UUP (DXY proxy) fetched via yfinance or CryptoCompare fallback
EQUITY_PROXY = "SPY"
DXY_PROXY = "UUP"

# CoinGecko IDs for fallback price fetching
_CG_IDS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "ADAUSDT": "cardano",
    "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink",
    "AVAXUSDT": "avalanche-2",
    "NEARUSDT": "near",
    "SUIUSDT": "sui",
    "ARBUSDT": "arbitrum",
    "OPUSDT": "optimism",
}


# ---------------------------------------------------------------------------
# 0. Helpers -- HTTP with failover
# ---------------------------------------------------------------------------

def _get_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """GET JSON with error handling."""
    if requests is None:
        return None
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# 1. Price Data Fetchers
# ---------------------------------------------------------------------------

def fetch_binance_klines(symbol: str, interval: str = "1d",
                         limit: int = ROLLING_WINDOW_DAYS + 5) -> list[float]:
    """Fetch daily close prices from Binance with 3+ endpoint failover.

    Returns list of close prices (most recent last), or empty list on failure.
    Falls back to CoinGecko and CryptoCompare if all Binance mirrors fail.
    """
    closes: list[float] = []

    # --- Binance mirrors (api, api1, api2, api3, data-api, binance.us) ---
    for base in SPOT_BASES:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _get_json(url)
        if data and isinstance(data, list) and len(data) >= 10:
            closes = [float(candle[4]) for candle in data]  # index 4 = close
            return closes

    # --- CoinGecko fallback ---
    cg_id = _CG_IDS.get(symbol)
    if cg_id:
        url = (f"{COINGECKO_BASE}/coins/{cg_id}/market_chart"
               f"?vs_currency=usd&days={limit}&interval=daily")
        data = _get_json(url)
        if data and "prices" in data:
            closes = [p[1] for p in data["prices"]]
            if len(closes) >= 10:
                return closes

    # --- CryptoCompare fallback ---
    fsym = symbol.replace("USDT", "").replace("USD", "")
    url = f"{CRYPTOCOMPARE_BASE}/v2/histoday?fsym={fsym}&tsym=USD&limit={limit}"
    data = _get_json(url)
    if data and isinstance(data, dict):
        entries = data.get("Data", {}).get("Data", [])
        if entries and len(entries) >= 10:
            closes = [e["close"] for e in entries if e.get("close", 0) > 0]
            if len(closes) >= 10:
                return closes

    return closes


def fetch_yfinance_closes(ticker: str, days: int = ROLLING_WINDOW_DAYS + 5) -> list[float]:
    """Fetch daily closes via yfinance (for SPY, UUP).

    Falls back to CryptoCompare for common tickers if yfinance unavailable.
    """
    # Try yfinance first
    try:
        import yfinance as yf  # type: ignore
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days + 10)
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"), progress=False)
        if df is not None and len(df) >= 10:
            return df["Close"].dropna().tolist()
    except Exception:
        pass

    # CryptoCompare fallback (works for some equity tickers)
    url = f"{CRYPTOCOMPARE_BASE}/v2/histoday?fsym={ticker}&tsym=USD&limit={days}"
    data = _get_json(url)
    if data and isinstance(data, dict):
        entries = data.get("Data", {}).get("Data", [])
        closes = [e["close"] for e in entries if e.get("close", 0) > 0]
        if len(closes) >= 10:
            return closes

    return []


# ---------------------------------------------------------------------------
# 2. Correlation Math
# ---------------------------------------------------------------------------

def log_returns(prices: list[float]) -> list[float]:
    """Compute daily log-returns from a price series."""
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))
        else:
            returns.append(0.0)
    return returns


def pearson_correlation(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation between two return series.

    Returns 0.0 if insufficient data or zero variance.
    """
    # Align lengths (use the shorter series from the tail)
    n = min(len(x), len(y))
    if n < 5:
        return 0.0
    x = x[-n:]
    y = y[-n:]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-12:
        return 0.0

    r = cov / denom
    # Clamp to [-1, 1] for floating-point safety
    return max(-1.0, min(1.0, r))


# ---------------------------------------------------------------------------
# 3. Load active picks
# ---------------------------------------------------------------------------

def load_active_picks() -> list[dict]:
    """Load active picks from data/active_picks.json."""
    if not _ACTIVE_PICKS_PATH.exists():
        return []
    try:
        with open(_ACTIVE_PICKS_PATH, encoding="utf-8") as f:
            picks = json.load(f)
        return [p for p in picks if p.get("status") == "OPEN"]
    except Exception as e:
        print(f"  [CORR] Could not load active_picks.json: {e}")
        return []


# ---------------------------------------------------------------------------
# 4. Build Correlation Matrix
# ---------------------------------------------------------------------------

def build_correlation_matrix(active_picks: list[dict],
                             max_symbols: int = 20) -> dict:
    """Build rolling 30-day correlation matrix for active picks + benchmarks.

    Returns:
        dict with keys:
            matrix: {sym: {sym: corr}}
            symbols: list of symbols in matrix
            btc_returns: BTC log-returns (for portfolio correlation)
            all_returns: {sym: log-returns}
    """
    # Collect unique crypto symbols from active picks
    crypto_symbols = set()
    for p in active_picks:
        sym = p.get("symbol", "")
        cat = p.get("category", "crypto")
        if cat == "crypto" and sym.endswith("USDT"):
            crypto_symbols.add(sym)

    # Always include BTC and ETH as benchmarks
    crypto_symbols.add("BTCUSDT")
    crypto_symbols.add("ETHUSDT")

    # Cap at max_symbols (prioritize BTC, ETH, then alphabetical)
    priority = ["BTCUSDT", "ETHUSDT"]
    remaining = sorted(crypto_symbols - set(priority))
    symbols = priority + remaining[:max_symbols - len(priority)]

    print(f"  [CORR] Fetching daily klines for {len(symbols)} symbols...")

    # Fetch all price series
    all_returns: dict[str, list[float]] = {}
    for sym in symbols:
        prices = fetch_binance_klines(sym, "1d", ROLLING_WINDOW_DAYS + 5)
        if prices and len(prices) >= 10:
            rets = log_returns(prices)
            if rets:
                all_returns[sym] = rets
        # Rate limit courtesy
        time.sleep(0.1)

    # Fetch SPY and UUP (DXY proxy)
    for equity_sym in [EQUITY_PROXY, DXY_PROXY]:
        prices = fetch_yfinance_closes(equity_sym, ROLLING_WINDOW_DAYS + 5)
        if prices and len(prices) >= 10:
            rets = log_returns(prices)
            if rets:
                all_returns[equity_sym] = rets

    available = list(all_returns.keys())
    print(f"  [CORR] Got returns for {len(available)} symbols")

    # Compute pairwise correlation matrix
    matrix: dict[str, dict[str, float]] = {}
    for sym_a in available:
        matrix[sym_a] = {}
        for sym_b in available:
            if sym_a == sym_b:
                matrix[sym_a][sym_b] = 1.0
            elif sym_b in matrix and sym_a in matrix[sym_b]:
                # Symmetric -- reuse
                matrix[sym_a][sym_b] = matrix[sym_b][sym_a]
            else:
                matrix[sym_a][sym_b] = round(
                    pearson_correlation(all_returns[sym_a], all_returns[sym_b]), 4
                )

    return {
        "matrix": matrix,
        "symbols": available,
        "all_returns": all_returns,
    }


# ---------------------------------------------------------------------------
# 5. Portfolio Diversification Score
# ---------------------------------------------------------------------------

def compute_diversification_score(matrix: dict[str, dict[str, float]],
                                  symbols: list[str]) -> dict:
    """Compute average pairwise correlation and diversification score.

    Score: max(0, (0.70 - avg_corr) / 0.40 * 100) on 0-100 scale.
    - > 70: WELL DIVERSIFIED
    - 30-70: MODERATE
    - < 30: HIGH RISK (essentially one big bet)
    """
    # Only include crypto symbols in the pairwise avg (exclude SPY, UUP)
    crypto_syms = [s for s in symbols if s.endswith("USDT")]
    if len(crypto_syms) < 2:
        return {
            "avg_pairwise_correlation": 0.0,
            "diversification_score": 100.0,
            "risk_level": "INSUFFICIENT_DATA",
            "crypto_symbol_count": len(crypto_syms),
        }

    total_corr = 0.0
    pair_count = 0
    for i, sym_a in enumerate(crypto_syms):
        for j in range(i + 1, len(crypto_syms)):
            sym_b = crypto_syms[j]
            corr = matrix.get(sym_a, {}).get(sym_b, 0.0)
            total_corr += abs(corr)  # Use absolute correlation
            pair_count += 1

    avg_corr = total_corr / pair_count if pair_count > 0 else 0.0
    score = max(0.0, (HIGH_CORR_THRESHOLD - avg_corr) / 0.40 * 100.0)
    score = min(100.0, score)

    if avg_corr > HIGH_CORR_THRESHOLD:
        risk_level = "HIGH_RISK"
    elif avg_corr < LOW_CORR_THRESHOLD:
        risk_level = "WELL_DIVERSIFIED"
    else:
        risk_level = "MODERATE"

    return {
        "avg_pairwise_correlation": round(avg_corr, 4),
        "diversification_score": round(score, 1),
        "risk_level": risk_level,
        "crypto_symbol_count": len(crypto_syms),
        "pair_count": pair_count,
    }


# ---------------------------------------------------------------------------
# 6. Concentration Alerts
# ---------------------------------------------------------------------------

def check_concentration_alerts(active_picks: list[dict],
                               matrix: dict[str, dict[str, float]],
                               symbols: list[str]) -> list[dict]:
    """Generate concentration alerts for the portfolio.

    Flags:
    - Single symbol > 15% of allocated capital
    - Single asset class > 60% of picks
    - 5+ picks with pairwise correlation > 0.80
    - BTC-to-portfolio correlation > 0.85
    """
    alerts: list[dict] = []

    if not active_picks:
        return alerts

    # --- Single symbol concentration ---
    total_alloc = sum(p.get("allocation", 0) or p.get("position_size", 200)
                      for p in active_picks)
    if total_alloc > 0:
        symbol_allocs: dict[str, float] = {}
        for p in active_picks:
            sym = p.get("symbol", "UNKNOWN")
            alloc = p.get("allocation", 0) or p.get("position_size", 200)
            symbol_allocs[sym] = symbol_allocs.get(sym, 0) + alloc

        for sym, alloc in symbol_allocs.items():
            pct = alloc / total_alloc
            if pct > MAX_SINGLE_CONCENTRATION_PCT:
                alerts.append({
                    "type": "SINGLE_SYMBOL_CONCENTRATION",
                    "severity": "HIGH",
                    "symbol": sym,
                    "allocation_pct": round(pct * 100, 1),
                    "threshold_pct": MAX_SINGLE_CONCENTRATION_PCT * 100,
                    "message": (f"{sym} is {pct*100:.1f}% of portfolio "
                                f"(threshold: {MAX_SINGLE_CONCENTRATION_PCT*100:.0f}%)"),
                })

    # --- Asset class concentration ---
    total_picks = len(active_picks)
    class_counts: dict[str, int] = {}
    for p in active_picks:
        cat = p.get("category", "crypto")
        class_counts[cat] = class_counts.get(cat, 0) + 1

    for cat, count in class_counts.items():
        pct = count / total_picks
        if pct > MAX_ASSET_CLASS_PCT:
            alerts.append({
                "type": "ASSET_CLASS_CONCENTRATION",
                "severity": "MEDIUM",
                "asset_class": cat,
                "pick_pct": round(pct * 100, 1),
                "threshold_pct": MAX_ASSET_CLASS_PCT * 100,
                "message": (f"{cat} is {pct*100:.1f}% of picks "
                            f"(threshold: {MAX_ASSET_CLASS_PCT*100:.0f}%)"),
            })

    # --- Highly correlated pairs ---
    crypto_syms = [s for s in symbols if s.endswith("USDT")]
    high_corr_pairs = []
    for i, sym_a in enumerate(crypto_syms):
        for j in range(i + 1, len(crypto_syms)):
            sym_b = crypto_syms[j]
            corr = abs(matrix.get(sym_a, {}).get(sym_b, 0.0))
            if corr > EXTREME_CORR_THRESHOLD:
                high_corr_pairs.append((sym_a, sym_b, corr))

    if len(high_corr_pairs) > 5:
        alerts.append({
            "type": "HIGH_CORRELATION_CLUSTER",
            "severity": "HIGH",
            "pair_count": len(high_corr_pairs),
            "threshold": 5,
            "top_pairs": [
                {"a": a, "b": b, "corr": round(c, 4)}
                for a, b, c in sorted(high_corr_pairs, key=lambda x: -x[2])[:10]
            ],
            "message": (f"{len(high_corr_pairs)} pairs with correlation > "
                        f"{EXTREME_CORR_THRESHOLD} (threshold: 5)"),
        })

    # --- BTC-to-portfolio correlation ---
    if "BTCUSDT" in matrix:
        btc_corrs = []
        for sym in crypto_syms:
            if sym != "BTCUSDT":
                corr = matrix.get("BTCUSDT", {}).get(sym, 0.0)
                btc_corrs.append(corr)
        if btc_corrs:
            avg_btc_corr = sum(btc_corrs) / len(btc_corrs)
            if avg_btc_corr > BTC_PORTFOLIO_CORR_ALERT:
                alerts.append({
                    "type": "BTC_PORTFOLIO_CORRELATION",
                    "severity": "HIGH",
                    "avg_btc_correlation": round(avg_btc_corr, 4),
                    "threshold": BTC_PORTFOLIO_CORR_ALERT,
                    "message": (f"Portfolio avg BTC correlation {avg_btc_corr:.2f} > "
                                f"{BTC_PORTFOLIO_CORR_ALERT} — effectively a BTC bet"),
                })

    return alerts


# ---------------------------------------------------------------------------
# 7. Correlation-Adjusted Position Sizing (exported for production_scanner.py)
# ---------------------------------------------------------------------------

def get_correlation_penalty(symbol: str, active_picks: list[dict],
                            corr_matrix: Optional[dict] = None) -> float:
    """Compute correlation-based position size multiplier for a symbol.

    Replaces the simple binary correlation penalty in kelly_position_sizer.py
    with a continuous, data-driven penalty.

    Args:
        symbol: Symbol to evaluate (e.g., "SOLUSDT")
        active_picks: Currently active picks
        corr_matrix: Pre-computed correlation matrix (optional; will be loaded
                     from the report file if not provided)

    Returns:
        Position size multiplier:
        - > 0.85 avg corr: 0.25x (quarter position)
        - > 0.70 avg corr: 0.50x (halve position)
        - 0.30-0.70:       1.00x (normal)
        - < 0.30:          1.20x (boost uncorrelated picks)
    """
    # Load matrix from saved report if not provided
    matrix = corr_matrix
    if matrix is None:
        matrix = _load_cached_matrix()
    if not matrix:
        # No correlation data available -- return neutral
        return 1.0

    # Get symbols from active picks
    portfolio_syms = []
    for p in active_picks:
        s = p.get("symbol", "")
        if s and s != symbol and s in matrix:
            portfolio_syms.append(s)

    if not portfolio_syms:
        return 1.0

    # Compute average correlation of this symbol to existing portfolio
    if symbol not in matrix:
        return 1.0

    corrs = []
    for ps in portfolio_syms:
        corr = matrix.get(symbol, {}).get(ps, 0.0)
        corrs.append(abs(corr))

    if not corrs:
        return 1.0

    avg_corr = sum(corrs) / len(corrs)

    if avg_corr > 0.85:
        return 0.25
    elif avg_corr > HIGH_CORR_THRESHOLD:
        return 0.50
    elif avg_corr < LOW_CORR_THRESHOLD:
        return 1.20
    else:
        return 1.0


def _load_cached_matrix() -> dict:
    """Load the most recent correlation matrix from the report file."""
    if not _REPORT_PATH.exists():
        return {}
    try:
        with open(_REPORT_PATH, encoding="utf-8") as f:
            report = json.load(f)
        return report.get("correlation_matrix", {})
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 8. Apply correlation penalty to Kelly-sized picks (batch)
# ---------------------------------------------------------------------------

def apply_correlation_penalties(picks: list[dict],
                                corr_matrix: Optional[dict] = None) -> list[dict]:
    """Apply correlation-based position size adjustments to all active picks.

    Called from production_scanner.py after Kelly sizing.
    Modifies picks in-place: adjusts position_size and adds correlation_penalty field.
    """
    matrix = corr_matrix if corr_matrix else _load_cached_matrix()

    adjusted = 0
    for pick in picks:
        symbol = pick.get("symbol", "")
        penalty = get_correlation_penalty(symbol, picks, matrix)

        if penalty != 1.0:
            old_size = pick.get("position_size", pick.get("allocation", 200))
            new_size = round(old_size * penalty, 2)
            pick["position_size"] = new_size
            pick["correlation_penalty"] = penalty
            adjusted += 1
        else:
            pick["correlation_penalty"] = 1.0

    if adjusted:
        print(f"  [CORR] Adjusted {adjusted}/{len(picks)} picks "
              f"via correlation penalty")
    else:
        print(f"  [CORR] No correlation adjustments needed")

    return picks


# ---------------------------------------------------------------------------
# 9. Cross-Asset Correlations (BTC vs SPY, BTC vs DXY)
# ---------------------------------------------------------------------------

def compute_cross_asset_correlations(
    all_returns: dict[str, list[float]]
) -> dict:
    """Compute BTC vs equity (SPY) and BTC vs dollar (UUP/DXY) correlations."""
    result: dict[str, Optional[float]] = {
        "btc_vs_spy": None,
        "btc_vs_dxy": None,
        "btc_vs_eth": None,
    }

    btc_rets = all_returns.get("BTCUSDT", [])
    eth_rets = all_returns.get("ETHUSDT", [])
    spy_rets = all_returns.get(EQUITY_PROXY, [])
    dxy_rets = all_returns.get(DXY_PROXY, [])

    if btc_rets and spy_rets:
        result["btc_vs_spy"] = round(pearson_correlation(btc_rets, spy_rets), 4)
    if btc_rets and dxy_rets:
        result["btc_vs_dxy"] = round(pearson_correlation(btc_rets, dxy_rets), 4)
    if btc_rets and eth_rets:
        result["btc_vs_eth"] = round(pearson_correlation(btc_rets, eth_rets), 4)

    return result


# ---------------------------------------------------------------------------
# 10. Weekly Report Writer
# ---------------------------------------------------------------------------

def save_correlation_report(matrix: dict[str, dict[str, float]],
                            symbols: list[str],
                            diversification: dict,
                            alerts: list[dict],
                            cross_asset: dict,
                            all_returns: dict[str, list[float]]) -> str:
    """Save comprehensive correlation report to data/correlation_report.json.

    Includes:
    - Full correlation matrix (top 20 symbols)
    - Diversification score
    - Active alerts
    - Cross-asset correlations
    - Historical diversification trend (appended)
    """
    now = datetime.now(timezone.utc).isoformat()

    # Load existing report for trend history
    history: list[dict] = []
    if _REPORT_PATH.exists():
        try:
            with open(_REPORT_PATH, encoding="utf-8") as f:
                old = json.load(f)
            history = old.get("diversification_history", [])
        except Exception:
            pass

    # Append current score to history (keep last 30 entries)
    history.append({
        "timestamp": now,
        "score": diversification["diversification_score"],
        "avg_corr": diversification["avg_pairwise_correlation"],
        "risk_level": diversification["risk_level"],
    })
    history = history[-30:]

    report = {
        "generated_at": now,
        "rolling_window_days": ROLLING_WINDOW_DAYS,
        "correlation_matrix": matrix,
        "symbols": symbols,
        "diversification": diversification,
        "cross_asset_correlations": cross_asset,
        "alerts": alerts,
        "alert_count": len(alerts),
        "high_severity_alerts": sum(1 for a in alerts if a.get("severity") == "HIGH"),
        "diversification_history": history,
    }

    # Sanitize any NaN/Inf values
    report = _sanitize(report)

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"  [CORR] Report saved to {_REPORT_PATH}")
    return str(_REPORT_PATH)


def _sanitize(obj):
    """Recursively replace NaN/Infinity with None."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


# ---------------------------------------------------------------------------
# 11. Main Entry Point
# ---------------------------------------------------------------------------

def run_correlation_monitor() -> dict:
    """Run the full correlation monitor pipeline.

    Returns the report dict for programmatic use.
    """
    print("\n=== Cross-Asset Correlation Monitor ===")
    start = time.time()

    # Load active picks
    active = load_active_picks()
    print(f"  [CORR] {len(active)} active picks loaded")

    if not active:
        print("  [CORR] No active picks -- generating minimal report")
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "diversification": {"diversification_score": 100, "risk_level": "NO_PICKS"},
            "alerts": [],
            "correlation_matrix": {},
            "symbols": [],
        }
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return report

    # Build correlation matrix
    corr_data = build_correlation_matrix(active, max_symbols=20)
    matrix = corr_data["matrix"]
    symbols = corr_data["symbols"]
    all_returns = corr_data["all_returns"]

    # Diversification score
    diversification = compute_diversification_score(matrix, symbols)
    print(f"  [CORR] Diversification score: {diversification['diversification_score']}/100 "
          f"({diversification['risk_level']})")
    print(f"  [CORR] Avg pairwise correlation: {diversification['avg_pairwise_correlation']:.4f}")

    # Cross-asset correlations
    cross_asset = compute_cross_asset_correlations(all_returns)
    for key, val in cross_asset.items():
        if val is not None:
            print(f"  [CORR] {key}: {val:.4f}")

    # Concentration alerts
    alerts = check_concentration_alerts(active, matrix, symbols)
    for alert in alerts:
        severity = alert.get("severity", "INFO")
        msg = alert.get("message", "")
        print(f"  [CORR] ALERT [{severity}]: {msg}")

    if not alerts:
        print(f"  [CORR] No concentration alerts")

    # Save report
    save_correlation_report(matrix, symbols, diversification,
                            alerts, cross_asset, all_returns)

    elapsed = time.time() - start
    print(f"  [CORR] Completed in {elapsed:.1f}s")

    return {
        "diversification": diversification,
        "alerts": alerts,
        "cross_asset": cross_asset,
        "matrix": matrix,
    }


# ---------------------------------------------------------------------------
# 12. CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_correlation_monitor()

    # Print summary
    div = result.get("diversification", {})
    alerts = result.get("alerts", [])
    print(f"\n--- Summary ---")
    print(f"  Score: {div.get('diversification_score', 'N/A')}/100")
    print(f"  Risk:  {div.get('risk_level', 'N/A')}")
    print(f"  Alerts: {len(alerts)}")

    cross = result.get("cross_asset", {})
    if cross.get("btc_vs_spy") is not None:
        print(f"  BTC-SPY: {cross['btc_vs_spy']:.4f}")
    if cross.get("btc_vs_dxy") is not None:
        print(f"  BTC-DXY: {cross['btc_vs_dxy']:.4f}")

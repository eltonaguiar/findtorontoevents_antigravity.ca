#!/usr/bin/env python3
"""
Win/Loss Trade Outcome Analyzer
================================
Loads ALL closed trades from KIMI, Alpha Engine, and Portfolio trackers.
Runs correlation analysis, logistic regression, score threshold optimization,
time-of-day analysis, and strategy ranking.

Usage: python alpha_engine/win_loss_analyzer.py
"""

import sys
import os
import io
import json
import math
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# ── Windows UTF-8 fix ──────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
KIMI_COMP = BASE / "KIMI_RISEOFTHECLAW" / "data" / "live_competition.json"
ALPHA_CLOSED = BASE / "alpha_engine" / "data" / "closed_picks.json"
PORTFOLIO_1X = BASE / "alpha_engine" / "data" / "portfolio_1x.json"
PORTFOLIO_20X = BASE / "alpha_engine" / "data" / "portfolio_20x.json"
OUTPUT_PATH = BASE / "alpha_engine" / "data" / "win_loss_analysis.json"


# ═══════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING & NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def parse_dt(s):
    """Parse various datetime formats, return datetime or None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    return None


def classify_symbol(symbol: str) -> str:
    """Classify a symbol into BTC/ETH/alt/meme/stock/forex."""
    s = symbol.upper().replace("-USD", "").replace("USDT", "").replace("=X", "")
    if s in ("BTC", "BITCOIN"):
        return "btc"
    if s in ("ETH", "ETHEREUM"):
        return "eth"
    meme_coins = {"DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME",
                  "TURBO", "BRETT", "NEIRO", "PNUT", "BOME", "MEW", "ACT"}
    if s in meme_coins:
        return "meme"
    stock_like = {"MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA", "NVDA",
                  "XLF", "XLE", "SPY", "QQQ", "IWM", "GLD", "TLT"}
    if s in stock_like or len(s) <= 4 and s.isalpha() and not any(c in s for c in ("USD", "EUR", "JPY", "GBP")):
        # check forex pairs
        forex_parts = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD", "NOK", "SEK"}
        if any(fp in symbol.upper() for fp in forex_parts) and "=" in symbol:
            return "forex"
    forex_parts = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD", "NOK", "SEK"}
    if any(fp in symbol.upper() for fp in forex_parts) and ("=" in symbol or "forex" in symbol.lower()):
        return "forex"
    if s in stock_like:
        return "stock"
    return "alt"


def normalize_close_reason(reason: str) -> str:
    """Normalize exit reason to TP/SL/TIME/TRAILING/OTHER."""
    if not reason:
        return "OTHER"
    r = reason.upper()
    if "TAKE_PROFIT" in r or "TP_HIT" in r or "TP" in r.split("_"):
        return "TP"
    if "STOP_LOSS" in r or "SL_HIT" in r or "SL" in r.split("_"):
        return "SL"
    if "TIME" in r or "EXPIR" in r:
        return "TIME"
    if "TRAILING" in r:
        return "TRAILING"
    return "OTHER"


def load_kimi_trades() -> list:
    """Load closed picks from KIMI live_competition.json."""
    trades = []
    if not KIMI_COMP.exists():
        print(f"  [WARN] KIMI file not found: {KIMI_COMP}")
        return trades

    data = json.loads(KIMI_COMP.read_text(encoding="utf-8"))
    for algo in data.get("algorithms", []):
        strategy_name = algo.get("id", algo.get("name", "unknown"))
        for pick in algo.get("closedPicks", []):
            entry_dt = parse_dt(pick.get("entryDate"))
            exit_dt = parse_dt(pick.get("exitDate"))
            entry_hour = entry_dt.hour if entry_dt else None
            hold_hours = None
            if entry_dt and exit_dt:
                hold_hours = (exit_dt - entry_dt).total_seconds() / 3600

            pnl_pct = pick.get("returnPct", pick.get("grossReturnPct", 0))
            score = pick.get("confluence_score", pick.get("signalProbability", None))

            trades.append({
                "source": "kimi",
                "symbol": pick.get("symbol", ""),
                "direction": pick.get("signal", "BUY"),
                "entry_price": pick.get("entryPrice", 0),
                "exit_price": pick.get("currentPrice", 0),
                "pnl_pct": pnl_pct,
                "score": score,
                "strategy": strategy_name,
                "entry_hour": entry_hour,
                "hold_hours": hold_hours,
                "close_reason": normalize_close_reason(pick.get("exitReason", "")),
                "symbol_category": pick.get("symbolCategory", classify_symbol(pick.get("symbol", ""))),
                "confluence_count": pick.get("confluence_count", 0),
                "rsi_at_entry": None,
                "volume_ratio": None,
            })
    return trades


def load_alpha_closed() -> list:
    """Load closed picks from alpha_engine closed_picks.json."""
    trades = []
    if not ALPHA_CLOSED.exists():
        print(f"  [WARN] Alpha closed file not found: {ALPHA_CLOSED}")
        return trades

    data = json.loads(ALPHA_CLOSED.read_text(encoding="utf-8"))
    for pick in data:
        entry_dt = parse_dt(pick.get("entry_date"))
        exit_dt = parse_dt(pick.get("exit_date"))
        entry_hour = entry_dt.hour if entry_dt else None
        hold_hours = None
        if entry_dt and exit_dt:
            hold_hours = (exit_dt - entry_dt).total_seconds() / 3600

        pnl_pct = pick.get("pnl_pct", 0)
        # pnl_pct in alpha is a fraction (0.029 = 2.9%), convert to percentage
        if pnl_pct is not None and abs(pnl_pct) < 1:
            pnl_pct = pnl_pct * 100

        score_raw = pick.get("confidence", pick.get("ml_score", None))
        score = None
        if score_raw is not None:
            # confidence is 0-1, convert to 0-100
            score = score_raw * 100 if score_raw <= 1 else score_raw

        trades.append({
            "source": "alpha_engine",
            "symbol": pick.get("symbol", ""),
            "direction": pick.get("signal_type", "BUY"),
            "entry_price": pick.get("entry_price", 0),
            "exit_price": pick.get("exit_price", 0),
            "pnl_pct": pnl_pct,
            "score": score,
            "strategy": pick.get("strategy", "unknown"),
            "entry_hour": entry_hour,
            "hold_hours": hold_hours,
            "close_reason": normalize_close_reason(pick.get("exit_reason", "")),
            "symbol_category": pick.get("category", classify_symbol(pick.get("symbol", ""))),
            "confluence_count": 0,
            "rsi_at_entry": pick.get("rsi_at_entry"),
            "volume_ratio": pick.get("volume_ratio"),
        })
    return trades


def load_portfolio_closed(path: Path, leverage: int) -> list:
    """Load closed positions from portfolio JSON."""
    trades = []
    if not path.exists():
        print(f"  [WARN] Portfolio file not found: {path}")
        return trades

    data = json.loads(path.read_text(encoding="utf-8"))
    for pos in data.get("closed_positions", []):
        entry_dt = parse_dt(pos.get("opened_at"))
        exit_dt = parse_dt(pos.get("close_time"))
        entry_hour = entry_dt.hour if entry_dt else None
        hold_hours = None
        if entry_dt and exit_dt:
            hold_hours = (exit_dt - entry_dt).total_seconds() / 3600

        pnl_pct = pos.get("pnl_pct", 0)
        score = pos.get("score", pos.get("dashboard_score", None))

        trades.append({
            "source": f"portfolio_{leverage}x",
            "symbol": pos.get("symbol", ""),
            "direction": pos.get("direction", "LONG"),
            "entry_price": pos.get("entry_price", 0),
            "exit_price": pos.get("close_price", 0),
            "pnl_pct": pnl_pct,
            "score": score,
            "strategy": pos.get("strategy", "unknown"),
            "entry_hour": entry_hour,
            "hold_hours": hold_hours,
            "close_reason": normalize_close_reason(pos.get("close_reason", "")),
            "symbol_category": classify_symbol(pos.get("symbol", "")),
            "confluence_count": 0,
            "rsi_at_entry": None,
            "volume_ratio": None,
        })
    return trades


def load_all_trades() -> list:
    """Load and merge all closed trades from all sources."""
    print("=" * 70)
    print("LOADING CLOSED TRADES FROM ALL SOURCES")
    print("=" * 70)

    kimi = load_kimi_trades()
    print(f"  KIMI Rise of the Claw: {len(kimi)} closed trades")

    alpha = load_alpha_closed()
    print(f"  Alpha Engine closed:   {len(alpha)} closed trades")

    p1x = load_portfolio_closed(PORTFOLIO_1X, 1)
    print(f"  Portfolio 1x:          {len(p1x)} closed trades")

    p20x = load_portfolio_closed(PORTFOLIO_20X, 20)
    print(f"  Portfolio 20x:         {len(p20x)} closed trades")

    all_trades = kimi + alpha + p1x + p20x
    print(f"  TOTAL:                 {len(all_trades)} closed trades")
    return all_trades


# ═══════════════════════════════════════════════════════════════════════════
# 2. STATISTICAL HELPERS (no scipy needed)
# ═══════════════════════════════════════════════════════════════════════════

def point_biserial_r(binary, continuous):
    """
    Compute point-biserial correlation between a binary and continuous variable.
    Returns (r, p_value_approx).
    """
    binary = np.array(binary, dtype=float)
    continuous = np.array(continuous, dtype=float)
    mask = ~(np.isnan(binary) | np.isnan(continuous))
    binary, continuous = binary[mask], continuous[mask]
    n = len(binary)
    if n < 3:
        return 0.0, 1.0

    n1 = binary.sum()
    n0 = n - n1
    if n0 == 0 or n1 == 0:
        return 0.0, 1.0

    m1 = continuous[binary == 1].mean()
    m0 = continuous[binary == 0].mean()
    s = continuous.std(ddof=0)
    if s == 0:
        return 0.0, 1.0

    r = (m1 - m0) / s * math.sqrt(n1 * n0 / (n * n))

    # t-test approximation for p-value
    if abs(r) >= 1.0:
        return r, 0.0
    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    # approximate p from t using large-sample normal approx
    p = 2 * (1 - _norm_cdf(abs(t_stat))) if n > 30 else _t_approx_p(t_stat, n - 2)
    return float(r), float(p)


def _norm_cdf(x):
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _t_approx_p(t, df):
    """Rough p-value for t-distribution using normal approximation."""
    if df <= 0:
        return 1.0
    # For df > 5, t ~ normal is reasonable
    return 2 * (1 - _norm_cdf(abs(t)))


def logistic_regression_fit(X, y, lr=0.01, epochs=2000, reg=0.01):
    """
    Simple logistic regression via gradient descent.
    X: (n, d) feature matrix (already standardized)
    y: (n,) binary labels
    Returns: coefficients (d,), intercept (scalar)
    """
    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0

    for _ in range(epochs):
        z = X @ w + b
        z = np.clip(z, -30, 30)  # prevent overflow
        p = 1.0 / (1.0 + np.exp(-z))
        err = p - y
        dw = (X.T @ err) / n + reg * w
        db = err.mean()
        w -= lr * dw
        b -= lr * db

    return w, b


def logistic_predict_proba(X, w, b):
    """Predict probabilities."""
    z = np.clip(X @ w + b, -30, 30)
    return 1.0 / (1.0 + np.exp(-z))


# ═══════════════════════════════════════════════════════════════════════════
# 3. ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def run_correlation_analysis(trades):
    """Section 2: Point-biserial correlations."""
    print("\n" + "=" * 70)
    print("CORRELATION ANALYSIS (Point-Biserial: variable vs Win/Loss)")
    print("=" * 70)

    wins = [1 if t["pnl_pct"] > 0 else 0 for t in trades]

    results = {}
    for var_name in ["score", "entry_hour", "hold_hours", "confluence_count",
                     "rsi_at_entry", "volume_ratio"]:
        values = []
        win_flags = []
        for i, t in enumerate(trades):
            v = t.get(var_name)
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                values.append(float(v))
                win_flags.append(wins[i])

        if len(values) < 10:
            print(f"  {var_name:20s}: insufficient data ({len(values)} samples)")
            results[var_name] = {"r": None, "p": None, "n": len(values)}
            continue

        r, p = point_biserial_r(win_flags, values)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"  {var_name:20s}: r={r:+.4f}  p={p:.4f}  n={len(values):4d}  {sig}")
        results[var_name] = {"r": round(r, 4), "p": round(p, 4), "n": len(values)}

    return results


def run_logistic_regression(trades):
    """Section 3: Logistic regression for win probability model."""
    print("\n" + "=" * 70)
    print("LOGISTIC REGRESSION: Win Probability Model")
    print("=" * 70)

    # Build feature matrix
    feature_names = []
    rows = []
    labels = []

    # Encode categories
    direction_map = {"BUY": 1, "LONG": 1, "SELL": -1, "SHORT": -1}
    category_set = {"btc", "eth", "alt", "meme", "stock", "forex"}

    # Collect unique strategies for encoding
    strategy_counts = defaultdict(int)
    for t in trades:
        strategy_counts[t["strategy"]] += 1
    # Only encode strategies with 10+ trades
    top_strategies = [s for s, c in strategy_counts.items() if c >= 10]

    for t in trades:
        score = t.get("score")
        entry_hour = t.get("entry_hour")
        hold_hours = t.get("hold_hours")

        # Skip if missing key features
        if score is None or entry_hour is None:
            continue

        feats = [
            float(score),
            float(entry_hour),
            float(hold_hours) if hold_hours is not None else 0.0,
            float(direction_map.get(t["direction"], 0)),
        ]
        # Symbol category one-hot
        cat = t.get("symbol_category", "alt")
        for c in sorted(category_set):
            feats.append(1.0 if cat == c else 0.0)

        rows.append(feats)
        labels.append(1.0 if t["pnl_pct"] > 0 else 0.0)

    if len(rows) < 20:
        print("  Insufficient data for logistic regression.")
        return {}

    feature_names = ["score", "entry_hour", "hold_hours", "direction_encoded",
                     *[f"cat_{c}" for c in sorted(category_set)]]

    X = np.array(rows)
    y = np.array(labels)

    # Standardize features
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0
    X_std = (X - means) / stds

    w, b = logistic_regression_fit(X_std, y, lr=0.05, epochs=3000)

    # Print coefficients
    print(f"\n  {'Feature':25s} {'Coefficient':>12s}  {'Direction':>10s}")
    print(f"  {'-'*25} {'-'*12}  {'-'*10}")
    coef_results = {}
    sorted_idx = np.argsort(-np.abs(w))
    for idx in sorted_idx:
        name = feature_names[idx]
        coef = w[idx]
        direction = "POSITIVE" if coef > 0 else "NEGATIVE"
        print(f"  {name:25s} {coef:+12.4f}  {direction:>10s}")
        coef_results[name] = round(float(coef), 4)

    print(f"\n  Intercept: {b:+.4f}")

    # Model accuracy
    preds = logistic_predict_proba(X_std, w, b)
    pred_labels = (preds >= 0.5).astype(float)
    accuracy = (pred_labels == y).mean() * 100
    print(f"  Model accuracy: {accuracy:.1f}%")
    print(f"  Base rate (% wins): {y.mean()*100:.1f}%")

    return {
        "coefficients": coef_results,
        "intercept": round(float(b), 4),
        "accuracy_pct": round(accuracy, 1),
        "base_win_rate_pct": round(float(y.mean() * 100), 1),
        "n_samples": len(rows),
        "feature_names": feature_names,
    }


def find_optimal_score_threshold(trades):
    """Section 4: Optimal score threshold."""
    print("\n" + "=" * 70)
    print("OPTIMAL SCORE THRESHOLD ANALYSIS")
    print("=" * 70)

    scored = [t for t in trades if t.get("score") is not None]
    if len(scored) < 20:
        print("  Insufficient scored trades.")
        return {}

    print(f"\n  {'Threshold':>10s} {'Trades':>7s} {'WR%':>7s} {'AvgPnL%':>9s} {'TotalPnL%':>10s} {'PF':>7s}")
    print(f"  {'-'*10} {'-'*7} {'-'*7} {'-'*9} {'-'*10} {'-'*7}")

    results = []
    best_sharpe = -999
    best_threshold = 50

    for threshold in range(30, 95, 5):
        filtered = [t for t in scored if t["score"] >= threshold]
        if len(filtered) < 5:
            continue

        wins = sum(1 for t in filtered if t["pnl_pct"] > 0)
        losses = len(filtered) - wins
        wr = wins / len(filtered) * 100
        pnls = [t["pnl_pct"] for t in filtered]
        avg_pnl = sum(pnls) / len(pnls)
        total_pnl = sum(pnls)
        gross_wins = sum(p for p in pnls if p > 0)
        gross_losses = abs(sum(p for p in pnls if p <= 0))
        pf = gross_wins / gross_losses if gross_losses > 0 else 999

        std_pnl = np.std(pnls) if len(pnls) > 1 else 1
        sharpe = avg_pnl / std_pnl if std_pnl > 0 else 0

        row = {
            "threshold": threshold,
            "trades": len(filtered),
            "win_rate_pct": round(wr, 1),
            "avg_pnl_pct": round(avg_pnl, 2),
            "total_pnl_pct": round(total_pnl, 2),
            "profit_factor": round(pf, 2),
            "sharpe": round(sharpe, 3),
        }
        results.append(row)

        marker = ""
        if sharpe > best_sharpe and len(filtered) >= 10:
            best_sharpe = sharpe
            best_threshold = threshold
            marker = " <-- BEST"

        print(f"  {threshold:>10d} {len(filtered):>7d} {wr:>7.1f} {avg_pnl:>+9.2f} {total_pnl:>+10.2f} {pf:>7.2f}{marker}")

    print(f"\n  OPTIMAL THRESHOLD: score >= {best_threshold}")
    print(f"  (Best risk-adjusted return with sufficient trade count)")

    return {
        "thresholds": results,
        "optimal_threshold": best_threshold,
        "optimal_sharpe": round(best_sharpe, 3),
    }


def find_optimal_time_filter(trades):
    """Section 5: Time-of-day analysis."""
    print("\n" + "=" * 70)
    print("TIME-OF-DAY ANALYSIS (Entry Hour UTC)")
    print("=" * 70)

    timed = [t for t in trades if t.get("entry_hour") is not None]
    if len(timed) < 20:
        print("  Insufficient timed trades.")
        return {}

    print(f"\n  {'Hour':>6s} {'Trades':>7s} {'WR%':>7s} {'AvgPnL%':>9s} {'TotalPnL%':>10s}")
    print(f"  {'-'*6} {'-'*7} {'-'*7} {'-'*9} {'-'*10}")

    hourly = defaultdict(list)
    for t in timed:
        hourly[t["entry_hour"]].append(t)

    results = []
    for hour in range(24):
        hlist = hourly.get(hour, [])
        if len(hlist) < 3:
            continue
        wins = sum(1 for t in hlist if t["pnl_pct"] > 0)
        wr = wins / len(hlist) * 100
        pnls = [t["pnl_pct"] for t in hlist]
        avg_pnl = sum(pnls) / len(pnls)
        total_pnl = sum(pnls)

        row = {
            "hour": hour,
            "trades": len(hlist),
            "win_rate_pct": round(wr, 1),
            "avg_pnl_pct": round(avg_pnl, 2),
            "total_pnl_pct": round(total_pnl, 2),
        }
        results.append(row)
        print(f"  {hour:>4d}h {len(hlist):>7d} {wr:>7.1f} {avg_pnl:>+9.2f} {total_pnl:>+10.2f}")

    # Best and worst hours
    if results:
        best = max(results, key=lambda x: x["avg_pnl_pct"])
        worst = min(results, key=lambda x: x["avg_pnl_pct"])
        print(f"\n  BEST HOUR:  {best['hour']:02d}:00 UTC  (WR={best['win_rate_pct']:.1f}%, AvgPnL={best['avg_pnl_pct']:+.2f}%)")
        print(f"  WORST HOUR: {worst['hour']:02d}:00 UTC  (WR={worst['win_rate_pct']:.1f}%, AvgPnL={worst['avg_pnl_pct']:+.2f}%)")

    return {
        "hourly_stats": results,
        "best_hour": best["hour"] if results else None,
        "worst_hour": worst["hour"] if results else None,
    }


def run_strategy_ranking(trades):
    """Section 6: Strategy ranking."""
    print("\n" + "=" * 70)
    print("STRATEGY RANKING")
    print("=" * 70)

    strat_trades = defaultdict(list)
    for t in trades:
        strat_trades[t["strategy"]].append(t)

    rankings = []
    for strat, slist in strat_trades.items():
        if len(slist) < 2:
            continue
        wins = sum(1 for t in slist if t["pnl_pct"] > 0)
        wr = wins / len(slist) * 100
        pnls = [t["pnl_pct"] for t in slist]
        avg_pnl = sum(pnls) / len(pnls)
        total_pnl = sum(pnls)
        std_pnl = np.std(pnls) if len(pnls) > 1 else 1
        sharpe = avg_pnl / std_pnl if std_pnl > 0 else 0

        rankings.append({
            "strategy": strat,
            "trades": len(slist),
            "win_rate_pct": round(wr, 1),
            "avg_pnl_pct": round(avg_pnl, 2),
            "total_pnl_pct": round(total_pnl, 2),
            "sharpe": round(sharpe, 3),
            "source": slist[0]["source"],
        })

    # Sort by Sharpe
    rankings.sort(key=lambda x: x["sharpe"], reverse=True)

    top5 = rankings[:5]
    bottom5 = rankings[-5:] if len(rankings) >= 5 else rankings

    print(f"\n  TOP 5 STRATEGIES (by Sharpe ratio):")
    print(f"  {'Strategy':40s} {'Trades':>7s} {'WR%':>7s} {'AvgPnL%':>9s} {'Sharpe':>7s} {'Source':>15s}")
    print(f"  {'-'*40} {'-'*7} {'-'*7} {'-'*9} {'-'*7} {'-'*15}")
    for r in top5:
        print(f"  {r['strategy'][:40]:40s} {r['trades']:>7d} {r['win_rate_pct']:>7.1f} {r['avg_pnl_pct']:>+9.2f} {r['sharpe']:>7.3f} {r['source']:>15s}")

    print(f"\n  BOTTOM 5 STRATEGIES (by Sharpe ratio):")
    print(f"  {'Strategy':40s} {'Trades':>7s} {'WR%':>7s} {'AvgPnL%':>9s} {'Sharpe':>7s} {'Source':>15s}")
    print(f"  {'-'*40} {'-'*7} {'-'*7} {'-'*9} {'-'*7} {'-'*15}")
    for r in bottom5:
        print(f"  {r['strategy'][:40]:40s} {r['trades']:>7d} {r['win_rate_pct']:>7.1f} {r['avg_pnl_pct']:>+9.2f} {r['sharpe']:>7.3f} {r['source']:>15s}")

    return {
        "all_strategies": rankings,
        "top_5": top5,
        "bottom_5": bottom5,
    }


def compute_summary_stats(trades):
    """Overall summary statistics."""
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY STATISTICS")
    print("=" * 70)

    total = len(trades)
    wins = sum(1 for t in trades if t["pnl_pct"] > 0)
    losses = total - wins
    wr = wins / total * 100 if total > 0 else 0

    pnls = [t["pnl_pct"] for t in trades]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    total_pnl = sum(pnls)
    median_pnl = float(np.median(pnls)) if pnls else 0
    std_pnl = float(np.std(pnls)) if pnls else 0

    avg_win = np.mean([p for p in pnls if p > 0]) if wins > 0 else 0
    avg_loss = np.mean([p for p in pnls if p <= 0]) if losses > 0 else 0

    gross_wins = sum(p for p in pnls if p > 0)
    gross_losses = abs(sum(p for p in pnls if p <= 0))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else 999

    # By close reason
    reason_stats = defaultdict(lambda: {"count": 0, "wins": 0, "pnls": []})
    for t in trades:
        cr = t["close_reason"]
        reason_stats[cr]["count"] += 1
        if t["pnl_pct"] > 0:
            reason_stats[cr]["wins"] += 1
        reason_stats[cr]["pnls"].append(t["pnl_pct"])

    # By source
    source_stats = defaultdict(lambda: {"count": 0, "wins": 0, "pnls": []})
    for t in trades:
        src = t["source"]
        source_stats[src]["count"] += 1
        if t["pnl_pct"] > 0:
            source_stats[src]["wins"] += 1
        source_stats[src]["pnls"].append(t["pnl_pct"])

    print(f"\n  Total trades:     {total}")
    print(f"  Wins:             {wins} ({wr:.1f}%)")
    print(f"  Losses:           {losses} ({100-wr:.1f}%)")
    print(f"  Avg PnL:          {avg_pnl:+.2f}%")
    print(f"  Median PnL:       {median_pnl:+.2f}%")
    print(f"  Std PnL:          {std_pnl:.2f}%")
    print(f"  Avg Win:          {float(avg_win):+.2f}%")
    print(f"  Avg Loss:         {float(avg_loss):+.2f}%")
    print(f"  Profit Factor:    {profit_factor:.2f}")
    print(f"  Total PnL:        {total_pnl:+.2f}%")

    print(f"\n  BY CLOSE REASON:")
    for reason, stats in sorted(reason_stats.items()):
        r_wr = stats["wins"] / stats["count"] * 100 if stats["count"] > 0 else 0
        r_avg = sum(stats["pnls"]) / len(stats["pnls"])
        print(f"    {reason:12s}: {stats['count']:4d} trades, WR={r_wr:.1f}%, AvgPnL={r_avg:+.2f}%")

    print(f"\n  BY SOURCE:")
    for src, stats in sorted(source_stats.items()):
        s_wr = stats["wins"] / stats["count"] * 100 if stats["count"] > 0 else 0
        s_avg = sum(stats["pnls"]) / len(stats["pnls"])
        print(f"    {src:20s}: {stats['count']:4d} trades, WR={s_wr:.1f}%, AvgPnL={s_avg:+.2f}%")

    # By symbol category
    cat_stats = defaultdict(lambda: {"count": 0, "wins": 0, "pnls": []})
    for t in trades:
        cat = t.get("symbol_category", "unknown")
        cat_stats[cat]["count"] += 1
        if t["pnl_pct"] > 0:
            cat_stats[cat]["wins"] += 1
        cat_stats[cat]["pnls"].append(t["pnl_pct"])

    print(f"\n  BY SYMBOL CATEGORY:")
    for cat, stats in sorted(cat_stats.items()):
        c_wr = stats["wins"] / stats["count"] * 100 if stats["count"] > 0 else 0
        c_avg = sum(stats["pnls"]) / len(stats["pnls"])
        print(f"    {cat:12s}: {stats['count']:4d} trades, WR={c_wr:.1f}%, AvgPnL={c_avg:+.2f}%")

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wr, 1),
        "avg_pnl_pct": round(avg_pnl, 2),
        "median_pnl_pct": round(median_pnl, 2),
        "std_pnl_pct": round(std_pnl, 2),
        "avg_win_pct": round(float(avg_win), 2),
        "avg_loss_pct": round(float(avg_loss), 2),
        "profit_factor": round(profit_factor, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "by_close_reason": {
            r: {"count": s["count"], "win_rate_pct": round(s["wins"]/s["count"]*100, 1), "avg_pnl_pct": round(sum(s["pnls"])/len(s["pnls"]), 2)}
            for r, s in reason_stats.items()
        },
        "by_source": {
            src: {"count": s["count"], "win_rate_pct": round(s["wins"]/s["count"]*100, 1), "avg_pnl_pct": round(sum(s["pnls"])/len(s["pnls"]), 2)}
            for src, s in source_stats.items()
        },
        "by_category": {
            cat: {"count": s["count"], "win_rate_pct": round(s["wins"]/s["count"]*100, 1), "avg_pnl_pct": round(sum(s["pnls"])/len(s["pnls"]), 2)}
            for cat, s in cat_stats.items()
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "#" * 70)
    print("#  TRADE OUTCOME ANALYZER — Win/Loss Pattern Identification")
    print(f"#  Run: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("#" * 70)

    # 1. Load all trades
    trades = load_all_trades()
    if not trades:
        print("\nERROR: No trades found. Exiting.")
        sys.exit(1)

    # 2. Summary stats
    summary = compute_summary_stats(trades)

    # 3. Correlation analysis
    correlations = run_correlation_analysis(trades)

    # 4. Logistic regression
    logreg = run_logistic_regression(trades)

    # 5. Score threshold optimization
    score_opt = find_optimal_score_threshold(trades)

    # 6. Time-of-day filter
    time_opt = find_optimal_time_filter(trades)

    # 7. Strategy ranking
    strat_rank = run_strategy_ranking(trades)

    # ── Save results ──────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_trades_analyzed": len(trades),
        "summary": summary,
        "correlations": correlations,
        "logistic_regression": logreg,
        "score_threshold_optimization": score_opt,
        "time_of_day_analysis": time_opt,
        "strategy_ranking": strat_rank,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"Results saved to: {OUTPUT_PATH}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

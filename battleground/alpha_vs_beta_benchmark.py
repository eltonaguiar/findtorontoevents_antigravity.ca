#!/usr/bin/env python3
"""
Alpha vs Beta Benchmark Analysis
=================================
Determines whether Battleground/Alpha Engine trading edge is real alpha
(skill-based excess return) or merely beta exposure (directional market bet).

Core question: "Would you have made the same money just being short/long BTC
over each trade's holding period?"

Usage:
    python battleground/alpha_vs_beta_benchmark.py
"""

import json
import os
import sys
import statistics
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BATTLEGROUND_CLOSED = REPO_ROOT / "battleground" / "data" / "closed_picks.json"
ALPHA_CLOSED = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUTPUT_PATH = REPO_ROOT / "battleground" / "data" / "alpha_benchmark_report.json"

# BTC benchmark symbol variants we look for
BTC_SYMBOLS = {"BTCUSDT", "BTC-USD", "BTCUSD", "BTC/USD", "BTC/USDT"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> list:
    """Load a JSON file, returning [] on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return []


def parse_iso(ts_str: str) -> datetime | None:
    """Parse an ISO-8601 timestamp or date string to a tz-aware datetime."""
    if not ts_str:
        return None
    try:
        # Try full ISO with timezone
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    # Try bare date
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def normalize_pick(raw: dict, source: str) -> dict | None:
    """
    Normalize a closed pick from either source into a common schema:
      symbol, direction, entry_price, exit_price, pnl_pct,
      entry_time, exit_time, strategy, status, source
    Returns None if essential fields are missing.
    """
    symbol = raw.get("symbol", "")
    strategy = raw.get("strategy", "unknown")

    # --- direction ---
    direction_raw = (
        raw.get("direction", "") or raw.get("signal_type", "")
    ).upper().strip()
    if direction_raw in ("SELL", "SHORT"):
        direction = "SHORT"
    elif direction_raw in ("BUY", "LONG"):
        direction = "LONG"
    else:
        return None  # can't determine direction

    # --- prices ---
    try:
        entry_price = float(raw["entry_price"])
        exit_price = float(raw["exit_price"])
    except (KeyError, TypeError, ValueError):
        return None

    if entry_price <= 0:
        return None

    # --- pnl_pct ---
    pnl_raw = raw.get("pnl_pct")
    if pnl_raw is not None:
        try:
            pnl_pct = float(pnl_raw)
        except (TypeError, ValueError):
            pnl_pct = None
    else:
        pnl_pct = None

    # Compute pnl from prices if missing or if raw value looks like a fraction
    if direction == "SHORT":
        computed_pnl = (entry_price - exit_price) / entry_price
    else:
        computed_pnl = (exit_price - entry_price) / entry_price

    # Alpha Engine stores pnl_pct as a fraction (0.07 = 7%), Battleground as
    # percentage (1.66 = 1.66%). Detect which by comparing to computed value.
    if pnl_pct is not None:
        # If raw value is within 0.1 of computed*100, it's in percentage points
        if abs(pnl_pct - computed_pnl * 100) < abs(pnl_pct - computed_pnl):
            pnl_pct = pnl_pct / 100.0  # convert to fraction
        # else already a fraction (or close enough)
    else:
        pnl_pct = computed_pnl

    # --- timestamps ---
    entry_time = parse_iso(
        raw.get("entry_time") or raw.get("timestamp") or raw.get("entry_date")
    )
    exit_time = parse_iso(
        raw.get("exit_time") or raw.get("exit_date")
    )

    # --- status ---
    status_raw = (raw.get("status", "") or "").upper()
    if status_raw in ("WIN", "WON"):
        status = "WIN"
    elif status_raw in ("LOSS", "LOST"):
        status = "LOSS"
    else:
        status = "WIN" if pnl_pct > 0 else "LOSS"

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl_pct": pnl_pct,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "strategy": strategy,
        "status": status,
        "source": source,
    }


# ---------------------------------------------------------------------------
# BTC price fetching for benchmark calculation
# ---------------------------------------------------------------------------

_btc_price_cache: dict[str, float] = {}


def _build_btc_cache_from_picks(all_picks: list[dict]):
    """
    Build a BTC price lookup from BTC-denominated picks themselves.
    For any pick on a BTC symbol, we know the price at entry and exit.
    """
    for p in all_picks:
        sym = p["symbol"].upper().replace("-", "").replace("/", "")
        if sym not in ("BTCUSDT", "BTCUSD"):
            continue
        if p["entry_time"]:
            key = p["entry_time"].strftime("%Y-%m-%dT%H")
            _btc_price_cache[key] = p["entry_price"]
        if p["exit_time"]:
            key = p["exit_time"].strftime("%Y-%m-%dT%H")
            _btc_price_cache[key] = p["exit_price"]


def _try_yfinance_btc(start_date: datetime, end_date: datetime) -> dict[str, float]:
    """Attempt to fetch BTC hourly data from yfinance over a date range."""
    prices = {}
    try:
        import yfinance as yf
        start_str = (start_date - timedelta(days=1)).strftime("%Y-%m-%d")
        end_str = (end_date + timedelta(days=2)).strftime("%Y-%m-%d")
        ticker = yf.Ticker("BTC-USD")
        # Try hourly first (limited to 730 days)
        df = ticker.history(start=start_str, end=end_str, interval="1h")
        if df.empty:
            df = ticker.history(start=start_str, end=end_str, interval="1d")
        for ts, row in df.iterrows():
            # hourly key
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            key_h = dt.strftime("%Y-%m-%dT%H")
            prices[key_h] = float(row["Close"])
            # also store daily key (for fallback matching)
            key_d = dt.strftime("%Y-%m-%d")
            if key_d not in prices:
                prices[key_d] = float(row["Close"])
    except Exception as e:
        print(f"  [WARN] yfinance fetch failed: {e}")
    return prices


def get_btc_price(dt: datetime) -> float | None:
    """Look up BTC price at a given datetime from cache."""
    if dt is None:
        return None
    # Try exact hour
    key_h = dt.strftime("%Y-%m-%dT%H")
    if key_h in _btc_price_cache:
        return _btc_price_cache[key_h]
    # Try nearest hour (+/- 2 hours)
    for delta_h in range(1, 3):
        for sign in (1, -1):
            candidate = dt + timedelta(hours=delta_h * sign)
            key = candidate.strftime("%Y-%m-%dT%H")
            if key in _btc_price_cache:
                return _btc_price_cache[key]
    # Try daily key
    key_d = dt.strftime("%Y-%m-%d")
    if key_d in _btc_price_cache:
        return _btc_price_cache[key_d]
    return None


def preload_btc_prices(all_picks: list[dict]):
    """
    Pre-load BTC price cache from:
      1. BTC picks in the dataset (free, always works)
      2. yfinance fetch (if available)
    """
    # Step 1: extract from BTC picks
    _build_btc_cache_from_picks(all_picks)
    print(f"  BTC prices from picks: {len(_btc_price_cache)} data points")

    # Step 2: determine date range needed
    min_dt = None
    max_dt = None
    for p in all_picks:
        for t in (p.get("entry_time"), p.get("exit_time")):
            if t is None:
                continue
            if min_dt is None or t < min_dt:
                min_dt = t
            if max_dt is None or t > max_dt:
                max_dt = t

    if min_dt is None or max_dt is None:
        return

    # Step 3: try yfinance
    print("  Fetching BTC prices from yfinance...")
    yf_prices = _try_yfinance_btc(min_dt, max_dt)
    _btc_price_cache.update(yf_prices)
    print(f"  Total BTC price cache: {len(_btc_price_cache)} data points")


# ---------------------------------------------------------------------------
# Benchmark computation
# ---------------------------------------------------------------------------

def compute_benchmark_return(pick: dict) -> float | None:
    """
    Compute the benchmark return for a pick: the return you'd get from
    taking the same direction on BTC over the same holding period.

    For BTC picks: benchmark = same as the trade (beta = 1.0), so the
    interesting question is whether the *entry/exit timing* adds alpha
    vs a random short/long of the same duration.

    For non-BTC picks: benchmark = BTC return in the same direction
    over the same period.
    """
    entry_time = pick.get("entry_time")
    exit_time = pick.get("exit_time")
    if entry_time is None or exit_time is None:
        return None

    sym = pick["symbol"].upper().replace("-", "").replace("/", "")
    is_btc = sym in ("BTCUSDT", "BTCUSD")

    if is_btc:
        # For BTC picks, benchmark IS the BTC move over that period
        # (the strategy return already captures this, so alpha = timing skill)
        btc_entry = pick["entry_price"]
        btc_exit = pick["exit_price"]
    else:
        btc_entry = get_btc_price(entry_time)
        btc_exit = get_btc_price(exit_time)
        if btc_entry is None or btc_exit is None:
            return None

    if btc_entry <= 0:
        return None

    # Raw BTC return over the period
    btc_return = (btc_exit - btc_entry) / btc_entry

    # Benchmark return matches the pick's direction
    if pick["direction"] == "SHORT":
        return -btc_return  # shorting BTC
    else:
        return btc_return   # longing BTC


def t_test(values: list[float]) -> tuple[float, float]:
    """
    One-sample t-test of values vs 0.
    Returns (t_statistic, two_tailed_p_value).
    Uses approximation for p-value without scipy.
    """
    n = len(values)
    if n < 2:
        return (0.0, 1.0)

    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return (float("inf") if mean != 0 else 0.0, 0.0 if mean != 0 else 1.0)

    t_stat = mean / (stdev / math.sqrt(n))
    df = n - 1

    # Approximate two-tailed p-value using the t-distribution
    # Uses the regularized incomplete beta function approximation
    x = df / (df + t_stat ** 2)
    p_value = _incomplete_beta_approx(df / 2.0, 0.5, x)
    return (t_stat, p_value)


def _incomplete_beta_approx(a: float, b: float, x: float) -> float:
    """
    Rough approximation of the regularized incomplete beta function I_x(a, b).
    Good enough for t-test p-values with reasonable degrees of freedom.
    Falls back to a normal approximation for large df.
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # For large a (df/2 > 30), use normal approximation
    if a > 30:
        # Use normal approximation to t-distribution
        # t_stat = sqrt(2a * (1-x)/x) roughly, then use erfc
        t_sq = 2 * a * (1 - x) / x
        t_abs = math.sqrt(max(t_sq, 0))
        # 2-tailed p from normal approx
        p = math.erfc(t_abs / math.sqrt(2))
        return max(0.0, min(1.0, p if p > 0 else 1e-15))

    # Continued fraction / series for smaller df
    # Simple numerical integration (trapezoidal)
    n_steps = 2000
    dx = x / n_steps
    total = 0.0
    try:
        log_beta = (
            math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        )
        for i in range(n_steps):
            t = (i + 0.5) * dx
            if t <= 0 or t >= 1:
                continue
            val = (a - 1) * math.log(t) + (b - 1) * math.log(1 - t)
            total += math.exp(val - log_beta) * dx
    except (ValueError, OverflowError):
        return 0.5  # fallback

    return max(0.0, min(1.0, total))


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(picks: list[dict]) -> dict:
    """Compute the full alpha benchmark report."""
    timestamp = datetime.now(timezone.utc).isoformat()

    # Filter picks with valid benchmark data
    analyzed = []
    skipped_no_times = 0
    skipped_no_benchmark = 0

    for p in picks:
        if p["entry_time"] is None or p["exit_time"] is None:
            skipped_no_times += 1
            continue
        bench = compute_benchmark_return(p)
        if bench is None:
            skipped_no_benchmark += 1
            continue
        analyzed.append({**p, "benchmark_return": bench})

    total = len(analyzed)
    print(f"\n  Analyzed: {total} trades")
    print(f"  Skipped (no timestamps): {skipped_no_times}")
    print(f"  Skipped (no benchmark price): {skipped_no_benchmark}")

    if total < 3:
        return {
            "timestamp": timestamp,
            "total_trades": total,
            "total_skipped_no_times": skipped_no_times,
            "total_skipped_no_benchmark": skipped_no_benchmark,
            "verdict": "INSUFFICIENT DATA",
            "detail": f"Only {total} trades with benchmark data. Need at least 3.",
        }

    # --- Aggregate stats ---
    strategy_returns = [t["pnl_pct"] for t in analyzed]
    benchmark_returns = [t["benchmark_return"] for t in analyzed]
    alphas = [t["pnl_pct"] - t["benchmark_return"] for t in analyzed]

    strategy_avg = statistics.mean(strategy_returns)
    benchmark_avg = statistics.mean(benchmark_returns)
    alpha_avg = statistics.mean(alphas)

    t_stat, p_value = t_test(alphas)
    alpha_significant = p_value < 0.05 and alpha_avg > 0

    # Strategy WR vs Benchmark WR
    strategy_wins = sum(1 for r in strategy_returns if r > 0)
    benchmark_wins = sum(1 for r in benchmark_returns if r > 0)

    # --- By direction ---
    by_direction = {}
    for d in ("SHORT", "LONG"):
        d_trades = [t for t in analyzed if t["direction"] == d]
        if not d_trades:
            continue
        d_strat_returns = [t["pnl_pct"] for t in d_trades]
        d_bench_returns = [t["benchmark_return"] for t in d_trades]
        d_alphas = [t["pnl_pct"] - t["benchmark_return"] for t in d_trades]
        d_t, d_p = t_test(d_alphas)
        by_direction[d] = {
            "trades": len(d_trades),
            "strategy_avg_return": round(statistics.mean(d_strat_returns) * 100, 4),
            "strategy_wr": round(
                sum(1 for r in d_strat_returns if r > 0) / len(d_trades) * 100, 2
            ),
            "benchmark_avg_return": round(statistics.mean(d_bench_returns) * 100, 4),
            "benchmark_wr": round(
                sum(1 for r in d_bench_returns if r > 0) / len(d_trades) * 100, 2
            ),
            "alpha_avg_pct": round(statistics.mean(d_alphas) * 100, 4),
            "alpha_ttest_pvalue": round(d_p, 6),
            "alpha_significant": d_p < 0.05 and statistics.mean(d_alphas) > 0,
        }

    # --- By strategy ---
    by_strategy = {}
    strategy_groups = defaultdict(list)
    for t in analyzed:
        strategy_groups[t["strategy"]].append(t)

    for strat, trades in sorted(strategy_groups.items(), key=lambda x: -len(x[1])):
        s_strat = [t["pnl_pct"] for t in trades]
        s_bench = [t["benchmark_return"] for t in trades]
        s_alphas = [t["pnl_pct"] - t["benchmark_return"] for t in trades]
        s_t, s_p = t_test(s_alphas) if len(s_alphas) >= 2 else (0.0, 1.0)
        directions = set(t["direction"] for t in trades)
        by_strategy[strat] = {
            "trades": len(trades),
            "directions": sorted(directions),
            "strategy_avg_return_pct": round(statistics.mean(s_strat) * 100, 4),
            "strategy_wr": round(
                sum(1 for r in s_strat if r > 0) / len(trades) * 100, 2
            ),
            "benchmark_avg_return_pct": round(statistics.mean(s_bench) * 100, 4),
            "benchmark_wr": round(
                sum(1 for r in s_bench if r > 0) / len(trades) * 100, 2
            ),
            "alpha_avg_pct": round(statistics.mean(s_alphas) * 100, 4),
            "alpha_pvalue": round(s_p, 6),
            "alpha_significant": s_p < 0.05 and statistics.mean(s_alphas) > 0,
        }

    # --- Verdict ---
    if total < 20:
        verdict = "INSUFFICIENT DATA"
        verdict_detail = (
            f"Only {total} trades analyzed. Need 20+ for meaningful inference. "
            f"Preliminary alpha = {alpha_avg*100:.2f}% per trade."
        )
    elif alpha_significant:
        verdict = "ALPHA CONFIRMED"
        verdict_detail = (
            f"Average alpha = {alpha_avg*100:.2f}% per trade (p={p_value:.4f}). "
            f"The strategy generates statistically significant excess returns "
            f"beyond the directional BTC benchmark."
        )
    elif alpha_avg > 0 and p_value < 0.10:
        verdict = "WEAK ALPHA (MARGINAL)"
        verdict_detail = (
            f"Average alpha = {alpha_avg*100:.2f}% per trade (p={p_value:.4f}). "
            f"Positive but not significant at 5% level. More data needed."
        )
    elif alpha_avg <= 0:
        verdict = "BETA ONLY"
        verdict_detail = (
            f"Average alpha = {alpha_avg*100:.2f}% per trade (p={p_value:.4f}). "
            f"Returns are NOT better than the directional BTC benchmark. "
            f"The edge appears to be pure beta exposure."
        )
    else:
        verdict = "INCONCLUSIVE"
        verdict_detail = (
            f"Average alpha = {alpha_avg*100:.2f}% per trade (p={p_value:.4f}). "
            f"Positive alpha but high p-value — could be noise."
        )

    # --- BTC market context ---
    # Determine if the sample period was bearish/bullish
    btc_picks = [t for t in analyzed if t["symbol"].upper().replace("-", "").replace("/", "") in ("BTCUSDT", "BTCUSD")]
    if btc_picks:
        first_entry = min(t["entry_price"] for t in btc_picks if t["entry_time"] == min(t2["entry_time"] for t2 in btc_picks))
        last_exit = max(t["exit_price"] for t in btc_picks if t["exit_time"] == max(t2["exit_time"] for t2 in btc_picks))
        btc_period_return = (last_exit - first_entry) / first_entry * 100
        market_regime = "BULLISH" if btc_period_return > 5 else "BEARISH" if btc_period_return < -5 else "SIDEWAYS"
    else:
        btc_period_return = None
        market_regime = "UNKNOWN"

    report = {
        "timestamp": timestamp,
        "total_trades": total,
        "total_skipped_no_times": skipped_no_times,
        "total_skipped_no_benchmark": skipped_no_benchmark,
        "strategy_avg_return_pct": round(strategy_avg * 100, 4),
        "benchmark_avg_return_pct": round(benchmark_avg * 100, 4),
        "alpha_avg_pct": round(alpha_avg * 100, 4),
        "alpha_ttest_statistic": round(t_stat, 4),
        "alpha_ttest_pvalue": round(p_value, 6),
        "alpha_significant_at_5pct": alpha_significant,
        "strategy_win_rate_pct": round(strategy_wins / total * 100, 2),
        "benchmark_win_rate_pct": round(benchmark_wins / total * 100, 2),
        "market_context": {
            "regime": market_regime,
            "btc_period_return_pct": round(btc_period_return, 2) if btc_period_return is not None else None,
            "short_pct": round(
                sum(1 for t in analyzed if t["direction"] == "SHORT") / total * 100, 1
            ),
            "long_pct": round(
                sum(1 for t in analyzed if t["direction"] == "LONG") / total * 100, 1
            ),
        },
        "by_direction": by_direction,
        "by_strategy": by_strategy,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
    }

    return report


def print_summary(report: dict):
    """Print a human-readable summary to stdout."""
    print("\n" + "=" * 70)
    print("  ALPHA vs BETA BENCHMARK REPORT")
    print("=" * 70)

    v = report.get("verdict", "UNKNOWN")
    print(f"\n  VERDICT: {v}")
    print(f"  {report.get('verdict_detail', '')}")

    print(f"\n  Total trades analyzed: {report.get('total_trades', 0)}")
    if report.get("total_skipped_no_times"):
        print(f"  Skipped (no timestamps): {report['total_skipped_no_times']}")
    if report.get("total_skipped_no_benchmark"):
        print(f"  Skipped (no BTC benchmark): {report['total_skipped_no_benchmark']}")

    if "strategy_avg_return_pct" in report:
        print(f"\n  Strategy avg return:  {report['strategy_avg_return_pct']:+.4f}%")
        print(f"  Benchmark avg return: {report['benchmark_avg_return_pct']:+.4f}%")
        print(f"  Alpha (excess return): {report['alpha_avg_pct']:+.4f}%")
        print(f"  t-statistic: {report.get('alpha_ttest_statistic', 'N/A')}")
        print(f"  p-value: {report.get('alpha_ttest_pvalue', 'N/A')}")
        print(f"  Significant at 5%: {report.get('alpha_significant_at_5pct', False)}")

        print(f"\n  Strategy WR:  {report['strategy_win_rate_pct']:.1f}%")
        print(f"  Benchmark WR: {report['benchmark_win_rate_pct']:.1f}%")

    ctx = report.get("market_context", {})
    if ctx:
        print(f"\n  Market regime: {ctx.get('regime', '?')}")
        if ctx.get("btc_period_return_pct") is not None:
            print(f"  BTC period return: {ctx['btc_period_return_pct']:+.2f}%")
        print(f"  Direction mix: {ctx.get('short_pct', '?')}% SHORT / {ctx.get('long_pct', '?')}% LONG")

    # --- By direction ---
    by_dir = report.get("by_direction", {})
    if by_dir:
        print(f"\n  {'-' * 66}")
        print(f"  BY DIRECTION:")
        for d, stats in by_dir.items():
            print(f"\n    {d} ({stats['trades']} trades):")
            print(f"      Strategy WR: {stats['strategy_wr']:.1f}%  |  Benchmark WR: {stats['benchmark_wr']:.1f}%")
            print(f"      Strategy avg: {stats['strategy_avg_return']:+.4f}%  |  Benchmark avg: {stats['benchmark_avg_return']:+.4f}%")
            print(f"      Alpha: {stats['alpha_avg_pct']:+.4f}%  (p={stats['alpha_ttest_pvalue']:.4f})")
            sig = " << SIGNIFICANT" if stats.get("alpha_significant") else ""
            print(f"      Significant: {stats.get('alpha_significant', False)}{sig}")

    # --- Top/bottom strategies by alpha ---
    by_strat = report.get("by_strategy", {})
    if by_strat:
        print(f"\n  {'-' * 66}")
        print(f"  BY STRATEGY (sorted by alpha):")
        sorted_strats = sorted(by_strat.items(), key=lambda x: x[1]["alpha_avg_pct"], reverse=True)

        # Top 5
        print(f"\n    TOP 5 alpha generators:")
        for name, s in sorted_strats[:5]:
            sig = " *" if s.get("alpha_significant") else ""
            print(f"      {name:45s} alpha={s['alpha_avg_pct']:+.3f}% ({s['trades']} trades, WR={s['strategy_wr']:.0f}%){sig}")

        # Bottom 5
        print(f"\n    BOTTOM 5 (worst alpha):")
        for name, s in sorted_strats[-5:]:
            print(f"      {name:45s} alpha={s['alpha_avg_pct']:+.3f}% ({s['trades']} trades, WR={s['strategy_wr']:.0f}%)")

        # Count significant
        sig_count = sum(1 for s in by_strat.values() if s.get("alpha_significant"))
        print(f"\n    Strategies with significant alpha: {sig_count}/{len(by_strat)}")

    print(f"\n{'=' * 70}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Alpha vs Beta Benchmark Analysis")
    print("=" * 40)

    # 1. Load picks
    print("\n[1/4] Loading closed picks...")
    bg_raw = load_json(BATTLEGROUND_CLOSED)
    ae_raw = load_json(ALPHA_CLOSED)
    print(f"  Battleground: {len(bg_raw)} raw picks")
    print(f"  Alpha Engine: {len(ae_raw)} raw picks")

    # 2. Normalize
    print("\n[2/4] Normalizing picks...")
    all_picks = []
    for raw in bg_raw:
        p = normalize_pick(raw, "battleground")
        if p:
            all_picks.append(p)
    bg_count = len(all_picks)
    for raw in ae_raw:
        p = normalize_pick(raw, "alpha_engine")
        if p:
            all_picks.append(p)
    ae_count = len(all_picks) - bg_count
    print(f"  Valid picks: {bg_count} battleground + {ae_count} alpha_engine = {len(all_picks)} total")

    if not all_picks:
        print("\n  ERROR: No valid picks found. Cannot compute benchmark.")
        sys.exit(1)

    # 3. Pre-load BTC prices
    print("\n[3/4] Loading BTC benchmark prices...")
    preload_btc_prices(all_picks)

    # 4. Generate report
    print("\n[4/4] Computing alpha vs beta benchmark...")
    report = generate_report(all_picks)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        # Convert datetimes for JSON serialization
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved to: {OUTPUT_PATH}")

    # Print summary
    print_summary(report)

    return report


if __name__ == "__main__":
    main()

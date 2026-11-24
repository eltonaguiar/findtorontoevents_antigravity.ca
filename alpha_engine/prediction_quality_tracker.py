#!/usr/bin/env python3
"""
Prediction Quality Tracker — measures and tracks prediction quality metrics over time.

Runs hourly via GitHub Actions, appends metrics to a time-series JSON file.
Tracks 14 quality dimensions: directional accuracy, confidence calibration,
PnL trends, risk ratios, drawdown, streaks, benchmark comparison, and more.

stdlib only — no external dependencies.
"""

import json
import math
import os
import logging
import statistics
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PredictionQuality] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ACTIVE_PICKS_PATH = os.path.join(DATA_DIR, "active_picks.json")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
STRONG_SIGNALS_PATH = os.path.join(DATA_DIR, "strong_signals.json")
HISTORY_PATH = os.path.join(DATA_DIR, "prediction_quality_history.json")

MAX_HISTORY_ENTRIES = 720  # 30 days hourly


# ── Helpers ────────────────────────────────────────────────────────────────

def _load_json(path, default=None):
    """Load a JSON file, returning default on any error."""
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data else default
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        log.warning("Could not load %s: %s", path, e)
        return default


def _save_json(path, data):
    """Atomically write JSON."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, path)
    except OSError as e:
        log.error("Failed to save %s: %s", path, e)
        if os.path.exists(tmp):
            os.remove(tmp)


def _parse_date(s):
    """Parse ISO date string to datetime (timezone-aware UTC)."""
    if not s:
        return None
    try:
        s = str(s).strip()
        # Handle various formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s[:30], fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _fetch_btc_price():
    """Fetch current BTC/USDT price from Binance mirrors with failover.

    Uses 3+ Binance mirrors per CLAUDE.md API Failover Rule.
    """
    mirrors = [
        "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api1.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api2.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api3.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    ]
    for url in mirrors:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                price = float(data.get("price", 0))
                if price > 0:
                    log.info("BTC price fetched: $%.2f from %s", price, url.split("/")[2])
                    return price
        except Exception as e:
            log.warning("BTC price fetch failed from %s: %s", url.split("/")[2], e)
            continue

    # Fallback: CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            price = float(data.get("bitcoin", {}).get("usd", 0))
            if price > 0:
                log.info("BTC price fetched: $%.2f from CoinGecko", price)
                return price
    except Exception as e:
        log.warning("BTC price fetch failed from CoinGecko: %s", e)

    # Fallback: KuCoin
    try:
        url = "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            price = float(data.get("data", {}).get("price", 0))
            if price > 0:
                log.info("BTC price fetched: $%.2f from KuCoin", price)
                return price
    except Exception as e:
        log.warning("BTC price fetch failed from KuCoin: %s", e)

    log.error("All BTC price sources failed")
    return None


# ── Metric Computations ───────────────────────────────────────────────────

def compute_directional_accuracy(closed):
    """Percent of closed picks where price moved toward TP (correct direction)."""
    if not closed:
        return 0.0
    correct = 0
    total = 0
    for p in closed:
        entry = p.get("entry_price")
        exit_p = p.get("exit_price")
        tp = p.get("take_profit")
        if not all((entry, exit_p, tp)):
            continue
        try:
            entry, exit_p, tp = float(entry), float(exit_p), float(tp)
        except (TypeError, ValueError):
            continue
        total += 1
        # Direction is correct if exit moved toward TP from entry
        signal = p.get("signal_type", "BUY").upper()
        if signal in ("BUY", "LONG"):
            if exit_p > entry:
                correct += 1
        elif signal in ("SELL", "SHORT"):
            if exit_p < entry:
                correct += 1
        else:
            # Default: assume long
            if exit_p > entry:
                correct += 1
    return round(correct / total, 4) if total > 0 else 0.0


def compute_hit_rate_by_confidence(closed):
    """Win rate per confidence bucket."""
    buckets = {"0.5-0.6": [], "0.6-0.7": [], "0.7-0.8": [], "0.8+": []}
    for p in closed:
        conf = p.get("confidence") or p.get("ml_score")
        if conf is None:
            continue
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            continue
        won = 1 if p.get("status") == "WON" else 0
        if conf >= 0.8:
            buckets["0.8+"].append(won)
        elif conf >= 0.7:
            buckets["0.7-0.8"].append(won)
        elif conf >= 0.6:
            buckets["0.6-0.7"].append(won)
        elif conf >= 0.5:
            buckets["0.5-0.6"].append(won)
    result = {}
    for k, v in buckets.items():
        result[k] = round(sum(v) / len(v), 4) if v else None
    return result


def compute_cumulative_pnl(closed, hours):
    """Cumulative PnL% for picks closed within the last N hours."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    total = 0.0
    for p in closed:
        exit_dt = _parse_date(p.get("exit_date"))
        if exit_dt and exit_dt >= cutoff:
            total += (p.get("pnl_pct") or 0) * 100
    return round(total, 4)


def _daily_pnl_series(closed):
    """Build a dict of date -> total PnL% for closed picks."""
    daily = {}
    for p in closed:
        exit_dt = _parse_date(p.get("exit_date"))
        if not exit_dt:
            continue
        day = exit_dt.strftime("%Y-%m-%d")
        pnl = (p.get("pnl_pct") or 0) * 100
        daily[day] = daily.get(day, 0.0) + pnl
    return daily


def compute_sharpe_ratio(closed):
    """Daily Sharpe ratio annualized (sqrt 365)."""
    daily = _daily_pnl_series(closed)
    if len(daily) < 2:
        return None
    vals = list(daily.values())
    try:
        mean_r = statistics.mean(vals)
        std_r = statistics.stdev(vals)
        if std_r == 0:
            return None
        return round(mean_r / std_r * math.sqrt(365), 4)
    except (statistics.StatisticsError, ZeroDivisionError):
        return None


def compute_sortino_ratio(closed):
    """Daily Sortino ratio annualized — only downside deviation."""
    daily = _daily_pnl_series(closed)
    if len(daily) < 2:
        return None
    vals = list(daily.values())
    mean_r = statistics.mean(vals)
    downside = [v for v in vals if v < 0]
    if len(downside) < 2:
        return None
    try:
        down_dev = statistics.stdev(downside)
        if down_dev == 0:
            return None
        return round(mean_r / down_dev * math.sqrt(365), 4)
    except (statistics.StatisticsError, ZeroDivisionError):
        return None


def compute_max_drawdown(closed):
    """Max drawdown % on cumulative PnL curve."""
    if not closed:
        return 0.0
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in closed:
        cum += (p.get("pnl_pct") or 0) * 100
        peak = max(peak, cum)
        dd = peak - cum
        max_dd = max(max_dd, dd)
    return round(max_dd, 4)


def compute_max_consecutive_losses(closed):
    """Current and all-time max consecutive loss streak."""
    if not closed:
        return 0
    max_streak = 0
    current = 0
    for p in closed:
        if p.get("status") == "LOST":
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def compute_profit_factor(closed, hours=None):
    """Gross wins / gross losses. If hours provided, filter by exit_date.

    Delegates the divide-by-zero / flat-trade handling to the canonical
    `alpha_engine.utils.math_utils.compute_profit_factor` helper, then maps
    its `inf` return back to the legacy `999.0` JSON-wire sentinel so
    downstream consumers (`profit_factor_7d`, `profit_factor_all` in
    forward_tracking.json) remain JSON-serializable without code changes.
    """
    from alpha_engine.utils.math_utils import compute_profit_factor as _canonical_pf

    now = datetime.now(timezone.utc)
    picks = closed
    if hours is not None:
        cutoff = now - timedelta(hours=hours)
        picks = [
            p for p in closed
            if _parse_date(p.get("exit_date")) and _parse_date(p.get("exit_date")) >= cutoff
        ]
    # NOTE: pnl_pct is pre-scaled to % units here (multiplied by 100), so any
    # threshold passed to the canonical helper must also be in % units (e.g.
    # 1.0 = 1% = 100bp, NOT 0.01). The dashboard JS uses raw decimal pnl with
    # 0.01 = 1bp — different unit scale, same helper. Keeping threshold=0.0
    # here preserves legacy semantics; promote to a per-class float later.
    gross_wins = sum((p.get("pnl_pct") or 0) * 100 for p in picks if (p.get("pnl_pct") or 0) > 0)
    gross_losses = abs(sum((p.get("pnl_pct") or 0) * 100 for p in picks if (p.get("pnl_pct") or 0) < 0))

    pf = _canonical_pf(gross_wins, gross_losses, threshold=0.0)
    if pf is None:
        return None
    if pf == float("inf"):
        return 999.0
    return round(pf, 4)


def compute_win_rate(closed, hours):
    """Win rate for picks closed within last N hours."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    picks = [
        p for p in closed
        if _parse_date(p.get("exit_date")) and _parse_date(p.get("exit_date")) >= cutoff
    ]
    if not picks:
        return None
    wins = sum(1 for p in picks if p.get("status") == "WON")
    decided = sum(1 for p in picks if p.get("status") in ("WON", "LOST"))
    return round(wins / decided, 4) if decided > 0 else None


def compute_signal_freshness(active):
    """Average age of active picks in hours."""
    if not active:
        return 0.0
    now = datetime.now(timezone.utc)
    ages = []
    for p in active:
        ts = _parse_date(p.get("timestamp") or p.get("entry_date"))
        if ts:
            age_h = (now - ts).total_seconds() / 3600
            if age_h >= 0:
                ages.append(age_h)
    return round(statistics.mean(ages), 2) if ages else 0.0


def compute_filter_effectiveness(strong_signals_data):
    """Compute pass rates per filter stage from strong_signals.json."""
    if not strong_signals_data:
        return {}
    # strong_signals.json may have various structures — try common patterns
    result = {}
    if isinstance(strong_signals_data, dict):
        # Could be {"filter_stats": {...}} or {"signals": [...], "stats": {...}}
        stats = strong_signals_data.get("filter_stats") or strong_signals_data.get("stats") or {}
        if isinstance(stats, dict):
            for k, v in stats.items():
                if isinstance(v, (int, float)):
                    result[k] = v
                elif isinstance(v, dict):
                    passed = v.get("passed", v.get("pass", 0))
                    total = v.get("total", v.get("checked", 0))
                    if total > 0:
                        result[k] = round(passed / total, 4)
        # Also check for top-level pass rates
        for key in ("regime", "rr", "confluence", "momentum", "volume"):
            if key in strong_signals_data and key not in result:
                val = strong_signals_data[key]
                if isinstance(val, (int, float)):
                    result[key] = val
    elif isinstance(strong_signals_data, list):
        # List of signals — count as total strong signals
        result["total_strong"] = len(strong_signals_data)
    return result


def compute_benchmark_comparison(closed, btc_price, history):
    """Compare 7d cumulative PnL vs BTC buy-and-hold over same period."""
    if btc_price is None:
        return None, None

    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)

    # Strategy PnL over 7d
    strategy_pnl_7d = compute_cumulative_pnl(closed, hours=7 * 24)

    # BTC benchmark: check history for a BTC price ~7 days ago
    btc_price_7d_ago = None
    if history:
        for entry in reversed(history):
            entry_ts = _parse_date(entry.get("timestamp"))
            if entry_ts and entry_ts <= cutoff_7d:
                old_btc = entry.get("btc_price")
                if old_btc and old_btc > 0:
                    btc_price_7d_ago = old_btc
                    break

    btc_pnl_7d = None
    if btc_price_7d_ago and btc_price_7d_ago > 0:
        btc_pnl_7d = round((btc_price - btc_price_7d_ago) / btc_price_7d_ago * 100, 4)

    alpha = None
    if btc_pnl_7d is not None:
        alpha = round(strategy_pnl_7d - btc_pnl_7d, 4)

    return btc_pnl_7d, alpha


def compute_rr_distribution(closed):
    """Average R:R of winners vs losers."""
    winner_rrs = []
    loser_rrs = []
    for p in closed:
        entry = p.get("entry_price")
        tp = p.get("take_profit")
        sl = p.get("stop_loss")
        if not all((entry, tp, sl)):
            continue
        try:
            entry, tp, sl = float(entry), float(tp), float(sl)
        except (TypeError, ValueError):
            continue
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk <= 0:
            continue
        rr = reward / risk
        if p.get("status") == "WON":
            winner_rrs.append(rr)
        elif p.get("status") == "LOST":
            loser_rrs.append(rr)

    avg_w = round(statistics.mean(winner_rrs), 4) if winner_rrs else None
    avg_l = round(statistics.mean(loser_rrs), 4) if loser_rrs else None
    return avg_w, avg_l


def compute_confidence_pnl_correlation(closed):
    """Pearson correlation between pick confidence and actual PnL."""
    pairs = []
    for p in closed:
        conf = p.get("confidence") or p.get("ml_score")
        pnl = p.get("pnl_pct")
        if conf is not None and pnl is not None:
            try:
                pairs.append((float(conf), float(pnl)))
            except (TypeError, ValueError):
                continue
    if len(pairs) < 5:
        return None

    xs = [c for c, _ in pairs]
    ys = [pnl for _, pnl in pairs]
    n = len(pairs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


# ── Main ───────────────────────────────────────────────────────────────────

def run():
    """Compute all prediction quality metrics and append to history."""
    log.info("=== Prediction Quality Tracker ===")

    # Load data
    active = _load_json(ACTIVE_PICKS_PATH, [])
    closed = _load_json(CLOSED_PICKS_PATH, [])
    strong_raw = _load_json(STRONG_SIGNALS_PATH, {})
    history_data = _load_json(HISTORY_PATH, {"history": []})

    # Normalize history structure
    if isinstance(history_data, list):
        history_data = {"history": history_data}
    history = history_data.get("history", [])

    log.info("Active: %d, Closed: %d, History entries: %d", len(active), len(closed), len(history))

    if not closed and not active:
        log.warning("No picks data found, writing minimal entry")

    # Sort closed by exit_date for ordered calculations
    def _sort_key(p):
        dt = _parse_date(p.get("exit_date"))
        return dt if dt else datetime.min.replace(tzinfo=timezone.utc)
    closed_sorted = sorted(closed, key=_sort_key)

    # Fetch BTC price for benchmark
    btc_price = _fetch_btc_price()

    # Compute all metrics
    directional_acc = compute_directional_accuracy(closed_sorted)
    hit_by_conf = compute_hit_rate_by_confidence(closed_sorted)
    cum_pnl_24h = compute_cumulative_pnl(closed_sorted, hours=24)
    cum_pnl_7d = compute_cumulative_pnl(closed_sorted, hours=7 * 24)
    cum_pnl_30d = compute_cumulative_pnl(closed_sorted, hours=30 * 24)
    sharpe = compute_sharpe_ratio(closed_sorted)
    sortino = compute_sortino_ratio(closed_sorted)
    max_dd = compute_max_drawdown(closed_sorted)
    max_consec_losses = compute_max_consecutive_losses(closed_sorted)
    pf_7d = compute_profit_factor(closed_sorted, hours=7 * 24)
    pf_all = compute_profit_factor(closed_sorted)
    wr_7d = compute_win_rate(closed_sorted, hours=7 * 24)
    wr_30d = compute_win_rate(closed_sorted, hours=30 * 24)
    avg_age = compute_signal_freshness(active)
    filter_eff = compute_filter_effectiveness(strong_raw)
    btc_pnl_7d, alpha_7d = compute_benchmark_comparison(closed_sorted, btc_price, history)
    avg_rr_w, avg_rr_l = compute_rr_distribution(closed_sorted)
    conf_corr = compute_confidence_pnl_correlation(closed_sorted)

    # Count strong signals
    total_strong = 0
    if isinstance(strong_raw, list):
        total_strong = len(strong_raw)
    elif isinstance(strong_raw, dict):
        signals = strong_raw.get("signals", strong_raw.get("picks", []))
        if isinstance(signals, list):
            total_strong = len(signals)

    # Build entry
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "timestamp": now_ts,
        "directional_accuracy": directional_acc,
        "hit_rate_by_confidence": hit_by_conf,
        "cumulative_pnl_24h": cum_pnl_24h,
        "cumulative_pnl_7d": cum_pnl_7d,
        "cumulative_pnl_30d": cum_pnl_30d,
        "sharpe_daily": sharpe,
        "sortino_daily": sortino,
        "max_drawdown_pct": max_dd,
        "max_consecutive_losses": max_consec_losses,
        "profit_factor_7d": pf_7d,
        "profit_factor_all": pf_all,
        "win_rate_7d": wr_7d,
        "win_rate_30d": wr_30d,
        "avg_signal_age_hours": avg_age,
        "strong_signal_pass_rates": filter_eff,
        "btc_price": btc_price,
        "btc_benchmark_pnl_7d": btc_pnl_7d,
        "alpha_vs_benchmark_7d": alpha_7d,
        "avg_rr_winners": avg_rr_w,
        "avg_rr_losers": avg_rr_l,
        "confidence_pnl_correlation": conf_corr,
        "total_active": len(active),
        "total_closed": len(closed),
        "total_strong_signals": total_strong,
    }

    # Append and trim
    history.append(entry)
    if len(history) > MAX_HISTORY_ENTRIES:
        history = history[-MAX_HISTORY_ENTRIES:]

    history_data["history"] = history
    _save_json(HISTORY_PATH, history_data)

    log.info("--- Prediction Quality Snapshot ---")
    log.info("  Directional Accuracy: %.2f%%", directional_acc * 100 if directional_acc else 0)
    log.info("  Cumulative PnL 24h/7d/30d: %.2f%% / %.2f%% / %.2f%%", cum_pnl_24h, cum_pnl_7d, cum_pnl_30d)
    log.info("  Sharpe: %s  Sortino: %s", sharpe, sortino)
    log.info("  Max Drawdown: %.2f%%", max_dd)
    log.info("  Profit Factor 7d/all: %s / %s", pf_7d, pf_all)
    log.info("  Win Rate 7d/30d: %s / %s", wr_7d, wr_30d)
    log.info("  Max Consec. Losses: %d", max_consec_losses)
    log.info("  Signal Freshness: %.1f hrs", avg_age)
    if btc_pnl_7d is not None:
        log.info("  BTC Benchmark 7d: %.2f%%  Alpha: %s%%", btc_pnl_7d, alpha_7d)
    log.info("  Confidence-PnL Correlation: %s", conf_corr)
    log.info("  History entries: %d / %d", len(history), MAX_HISTORY_ENTRIES)
    log.info("Saved to %s", HISTORY_PATH)

    return entry


if __name__ == "__main__":
    run()

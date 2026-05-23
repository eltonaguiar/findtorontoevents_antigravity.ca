#!/usr/bin/env python3
"""
Recurring Pick Quality Analysis System
=======================================
Runs every 30 minutes. Analyses score-to-PnL correlation, regime performance,
top gainers/losers, strategy DNA, and produces an overall health score.

Each run appends to history files so we can track improvement over time.
"""

import sys
import os
import json
import math
import time
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone
from collections import defaultdict, Counter

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIT_DIR = os.path.join(os.path.dirname(BASE_DIR), "audit_trail", "data")

DASHBOARD_PAYLOAD = os.path.join(AUDIT_DIR, "dashboard_payload.json")
RESOLVED_PICKS = os.path.join(AUDIT_DIR, "universal_resolved_picks.json")
STRATEGY_PERF = os.path.join(DATA_DIR, "strategy_performance.json")

SCORE_PNL_HISTORY = os.path.join(DATA_DIR, "score_pnl_history.json")
REGIME_PERF_HISTORY = os.path.join(DATA_DIR, "regime_performance_history.json")
TOP_GAINERS_FILE = os.path.join(DATA_DIR, "top_gainers_check.json")
LOSER_PATTERNS_FILE = os.path.join(DATA_DIR, "loser_patterns.json")
STRATEGY_MUTATIONS_FILE = os.path.join(DATA_DIR, "strategy_mutations.json")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_json(path, default=None):
    """Load JSON file, return default on failure."""
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    """Save JSON file atomically."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    # atomic rename (best-effort on Windows)
    try:
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)


def _append_history(path, record, max_records=500):
    """Append a record to a JSON list file, keeping at most max_records."""
    history = _load_json(path, default=[])
    if not isinstance(history, list):
        history = []
    history.append(record)
    if len(history) > max_records:
        history = history[-max_records:]
    _save_json(path, history)
    return history


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch_json(url, timeout=15):
    """Fetch JSON from a URL with SSL workaround."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "AlphaEngine-PickQuality/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _pearson_r(xs, ys):
    """Compute Pearson correlation coefficient. Returns None if not enough data."""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(max(sum((x - mx) ** 2 for x in xs) / n, 1e-12))
    sy = math.sqrt(max(sum((y - my) ** 2 for y in ys) / n, 1e-12))
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    return cov / (sx * sy)


# ---------------------------------------------------------------------------
# Section 1: Score-to-PnL Correlation Analysis
# ---------------------------------------------------------------------------
def section_score_pnl_correlation(payload):
    """Analyse correlation between pick scores and PnL outcomes."""
    print("\n" + "=" * 70)
    print("SECTION 1: SCORE-TO-PNL CORRELATION ANALYSIS")
    print("=" * 70)

    active_picks = []
    try:
        active_picks = payload.get("picks", {}).get("active", [])
    except Exception:
        pass

    scores = []
    pnls = []
    anomalies_low_score_high_pnl = []
    anomalies_high_score_low_pnl = []

    for pick in active_picks:
        score = pick.get("score")
        pnl = pick.get("pnl_pct")
        if score is None or pnl is None:
            continue
        try:
            score = float(score)
            pnl = float(pnl)
        except (ValueError, TypeError):
            continue

        scores.append(score)
        pnls.append(pnl)

        # Anomaly detection
        if score < 40 and pnl > 3.0:
            anomalies_low_score_high_pnl.append({
                "symbol": pick.get("symbol", "?"),
                "strategy": pick.get("strategy", "?"),
                "score": score,
                "pnl_pct": pnl,
                "direction": pick.get("direction", "?"),
            })
        if score > 80 and pnl < -2.0:
            anomalies_high_score_low_pnl.append({
                "symbol": pick.get("symbol", "?"),
                "strategy": pick.get("strategy", "?"),
                "score": score,
                "pnl_pct": pnl,
                "direction": pick.get("direction", "?"),
            })

    r = _pearson_r(scores, pnls)
    anomaly_count = len(anomalies_low_score_high_pnl) + len(anomalies_high_score_low_pnl)

    record = {
        "timestamp": _now_iso(),
        "correlation_r": r,
        "sample_size": len(scores),
        "anomaly_count": anomaly_count,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "avg_pnl": round(sum(pnls) / len(pnls), 4) if pnls else None,
    }

    history = _append_history(SCORE_PNL_HISTORY, record)

    # Trend analysis
    trend_msg = "Not enough history yet"
    if len(history) >= 5:
        recent_5 = [h["correlation_r"] for h in history[-5:] if h.get("correlation_r") is not None]
        older_5 = [h["correlation_r"] for h in history[-10:-5] if h.get("correlation_r") is not None]
        if recent_5 and older_5:
            recent_avg = sum(recent_5) / len(recent_5)
            older_avg = sum(older_5) / len(older_5)
            if recent_avg > older_avg + 0.05:
                trend_msg = f"IMPROVING (recent avg r={recent_avg:.3f} vs older avg r={older_avg:.3f})"
            elif recent_avg < older_avg - 0.05:
                trend_msg = f"DECLINING (recent avg r={recent_avg:.3f} vs older avg r={older_avg:.3f})"
            else:
                trend_msg = f"STABLE (recent avg r={recent_avg:.3f} vs older avg r={older_avg:.3f})"
        elif recent_5:
            trend_msg = f"Recent avg correlation: {sum(recent_5)/len(recent_5):.3f} (need more history for trend)"

    print(f"  Pairs analysed:        {len(scores)}")
    print(f"  Correlation (r):       {r:.4f}" if r is not None else "  Correlation (r):       N/A (insufficient data)")
    print(f"  Anomalies:             {anomaly_count}")
    if anomalies_low_score_high_pnl:
        print(f"    Low score / high PnL: {len(anomalies_low_score_high_pnl)}")
        for a in anomalies_low_score_high_pnl[:5]:
            print(f"      {a['symbol']} score={a['score']} pnl={a['pnl_pct']}% ({a['strategy']})")
    if anomalies_high_score_low_pnl:
        print(f"    High score / low PnL: {len(anomalies_high_score_low_pnl)}")
        for a in anomalies_high_score_low_pnl[:5]:
            print(f"      {a['symbol']} score={a['score']} pnl={a['pnl_pct']}% ({a['strategy']})")
    print(f"  Trend:                 {trend_msg}")

    return {
        "correlation_r": r,
        "sample_size": len(scores),
        "anomaly_count": anomaly_count,
        "anomalies_low_score_high_pnl": anomalies_low_score_high_pnl,
        "anomalies_high_score_low_pnl": anomalies_high_score_low_pnl,
        "trend": trend_msg,
        "history_length": len(history),
    }


# ---------------------------------------------------------------------------
# Section 2: Regime Performance Tracking
# ---------------------------------------------------------------------------
def section_regime_performance(payload):
    """Compute win rates per market regime from closed picks."""
    print("\n" + "=" * 70)
    print("SECTION 2: REGIME PERFORMANCE TRACKING")
    print("=" * 70)

    resolved = _load_json(RESOLVED_PICKS, default=[])

    # Get current regime from payload summary
    regime_wr = payload.get("summary", {}).get("regime_win_rates", {})
    current_regime = "UNKNOWN"
    if regime_wr:
        # Pick the regime with the most trades as "current"
        current_regime = max(regime_wr.keys(), key=lambda k: regime_wr[k].get("trades", 0))

    # Group resolved picks by strategy to compute regime performance
    # Since picks don't have regime_at_entry, we use the current regime for recent,
    # and bucket by exit_reason/pnl patterns as proxy
    regime_buckets = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0.0, "picks": 0})

    # Use regime_win_rates from payload directly (they already have the breakdown)
    for regime_name, stats in regime_wr.items():
        bucket = regime_buckets[regime_name]
        bucket["wins"] = stats.get("wins", 0)
        bucket["losses"] = stats.get("losses", 0)
        bucket["picks"] = stats.get("trades", 0)

    # Also compute per-strategy WR from resolved picks for "smart picks"
    # Smart picks = strategies with forward WR > 55%
    smart_strategies = set()
    systems = payload.get("systems", [])
    for sys_info in systems:
        for strat in sys_info.get("strategies", []):
            fwd_wr = strat.get("forward_wr")
            if fwd_wr is not None and fwd_wr > 55:
                smart_strategies.add(strat.get("name", ""))

    smart_wins = 0
    smart_losses = 0
    all_strategies_wr = {}

    for pick in resolved:
        strat = pick.get("strategy", "")
        pnl = pick.get("pnl_pct", 0)
        if pick.get("status") != "CLOSED":
            continue
        try:
            pnl = float(pnl)
        except (ValueError, TypeError):
            continue
        is_win = pnl > 0

        if strat not in all_strategies_wr:
            all_strategies_wr[strat] = {"wins": 0, "losses": 0}
        if is_win:
            all_strategies_wr[strat]["wins"] += 1
        else:
            all_strategies_wr[strat]["losses"] += 1

        if strat in smart_strategies:
            if is_win:
                smart_wins += 1
            else:
                smart_losses += 1

    smart_total = smart_wins + smart_losses
    smart_wr = round(100.0 * smart_wins / smart_total, 1) if smart_total > 0 else 0

    # Build result
    regime_results = {}
    for regime_name, bucket in regime_buckets.items():
        total = bucket["wins"] + bucket["losses"]
        wr = round(100.0 * bucket["wins"] / total, 1) if total > 0 else 0
        regime_results[regime_name] = {
            "win_rate": wr,
            "wins": bucket["wins"],
            "losses": bucket["losses"],
            "trades": total,
        }

    record = {
        "timestamp": _now_iso(),
        "current_regime": current_regime,
        "regime_win_rates": regime_results,
        "smart_picks_wr": smart_wr,
        "smart_picks_total": smart_total,
    }

    _append_history(REGIME_PERF_HISTORY, record)

    # Print
    print(f"  Current regime:        {current_regime}")
    if regime_results:
        best_regime = max(regime_results.items(), key=lambda x: x[1]["win_rate"])
        worst_regime = min(regime_results.items(), key=lambda x: x[1]["win_rate"])
        for rname, rdata in sorted(regime_results.items(), key=lambda x: -x[1]["win_rate"]):
            print(f"    {rname:20s}  WR={rdata['win_rate']:5.1f}%  trades={rdata['trades']}")
        print(f"  Best regime:           {best_regime[0]} ({best_regime[1]['win_rate']}%)")
        print(f"  Worst regime:          {worst_regime[0]} ({worst_regime[1]['win_rate']}%)")
    else:
        print("  No regime data available.")
    print(f"  Smart Picks WR:        {smart_wr}% ({smart_total} trades)")

    return {
        "current_regime": current_regime,
        "regime_win_rates": regime_results,
        "smart_picks_wr": smart_wr,
        "smart_picks_total": smart_total,
    }


# ---------------------------------------------------------------------------
# Section 3: Top Gainers Check
# ---------------------------------------------------------------------------
_BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/ticker/24hr",
    "https://api.binance.com/api/v3/ticker/24hr",
    "https://api1.binance.com/api/v3/ticker/24hr",
    "https://api2.binance.com/api/v3/ticker/24hr",
    "https://api3.binance.com/api/v3/ticker/24hr",
]

_COINGECKO_TRENDING = "https://api.coingecko.com/api/v3/search/trending"
_KUCOIN_TICKERS = "https://api.kucoin.com/api/v1/market/allTickers"


def _fetch_binance_tickers():
    """Fetch 24hr tickers from Binance with failover."""
    for url in _BINANCE_ENDPOINTS:
        try:
            data = _fetch_json(url, timeout=20)
            # Filter to USDT pairs only
            usdt = [t for t in data if t.get("symbol", "").endswith("USDT")]
            return usdt
        except Exception as e:
            print(f"    [failover] {url.split('/')[2]} failed: {e}")
            continue
    return None


def _fetch_coingecko_trending():
    """Fetch trending coins from CoinGecko as backup."""
    try:
        data = _fetch_json(_COINGECKO_TRENDING, timeout=15)
        coins = data.get("coins", [])
        return [
            {
                "symbol": c.get("item", {}).get("symbol", "").upper() + "USDT",
                "name": c.get("item", {}).get("name", ""),
                "market_cap_rank": c.get("item", {}).get("market_cap_rank"),
                "price_change_24h": c.get("item", {}).get("data", {}).get("price_change_percentage_24h", {}).get("usd"),
            }
            for c in coins
        ]
    except Exception as e:
        print(f"    [failover] CoinGecko trending failed: {e}")
        return []


def _fetch_kucoin_tickers():
    """Fetch tickers from KuCoin as backup."""
    try:
        data = _fetch_json(_KUCOIN_TICKERS, timeout=15)
        tickers = data.get("data", {}).get("ticker", [])
        usdt = [
            {
                "symbol": t.get("symbol", "").replace("-", ""),
                "priceChangePercent": str(float(t.get("changeRate", 0)) * 100),
                "volume": t.get("vol", "0"),
                "lastPrice": t.get("last", "0"),
            }
            for t in tickers
            if t.get("symbol", "").endswith("-USDT")
        ]
        return usdt
    except Exception as e:
        print(f"    [failover] KuCoin failed: {e}")
        return []


def section_top_gainers(payload):
    """Fetch top hourly gainers and cross-reference with active picks."""
    print("\n" + "=" * 70)
    print("SECTION 3: TOP GAINERS CHECK")
    print("=" * 70)

    active_picks = payload.get("picks", {}).get("active", [])
    our_symbols = {p.get("symbol", "") for p in active_picks}

    # Fetch market data with failover
    tickers = _fetch_binance_tickers()
    source = "Binance"
    if not tickers:
        print("  Binance endpoints exhausted, trying KuCoin...")
        tickers = _fetch_kucoin_tickers()
        source = "KuCoin"

    coingecko_trending = _fetch_coingecko_trending()

    if not tickers:
        print("  WARNING: Could not fetch ticker data from any source.")
        result = {
            "source": "NONE",
            "top_gainers": [],
            "our_picks_in_top": [],
            "coingecko_trending": coingecko_trending,
        }
        _save_json(TOP_GAINERS_FILE, {**result, "timestamp": _now_iso()})
        return result

    # Sort by price change percent descending
    for t in tickers:
        try:
            t["_pcp"] = float(t.get("priceChangePercent", 0))
        except (ValueError, TypeError):
            t["_pcp"] = 0.0
        try:
            t["_vol"] = float(t.get("volume", 0))
        except (ValueError, TypeError):
            t["_vol"] = 0.0
        try:
            t["_price"] = float(t.get("lastPrice", 0))
        except (ValueError, TypeError):
            t["_price"] = 0.0

    # Filter out very low-volume coins
    valid = [t for t in tickers if t["_vol"] > 100000]
    gainers = sorted(valid, key=lambda t: t["_pcp"], reverse=True)[:20]
    losers_all = sorted(valid, key=lambda t: t["_pcp"])[:20]

    # Cross-reference with our picks
    our_picks_in_top = []
    for g in gainers:
        sym = g.get("symbol", "")
        if sym in our_symbols:
            matching = [p for p in active_picks if p.get("symbol") == sym]
            our_picks_in_top.append({
                "symbol": sym,
                "market_change_pct": round(g["_pcp"], 2),
                "our_direction": matching[0].get("direction") if matching else "?",
                "our_pnl_pct": matching[0].get("pnl_pct") if matching else None,
                "our_strategy": matching[0].get("strategy") if matching else "?",
            })

    # Pattern analysis on top gainers
    pcp_values = [g["_pcp"] for g in gainers]
    vol_values = [g["_vol"] for g in gainers]

    patterns = {
        "avg_gain_pct": round(sum(pcp_values) / len(pcp_values), 2) if pcp_values else 0,
        "min_gain_pct": round(min(pcp_values), 2) if pcp_values else 0,
        "max_gain_pct": round(max(pcp_values), 2) if pcp_values else 0,
        "avg_volume": round(sum(vol_values) / len(vol_values), 0) if vol_values else 0,
        "symbols_with_usdt_volume_above_10m": sum(1 for v in vol_values if v > 10_000_000),
    }

    top_gainers_list = [
        {
            "symbol": g.get("symbol", ""),
            "priceChangePercent": round(g["_pcp"], 2),
            "volume": round(g["_vol"], 0),
            "lastPrice": g["_price"],
        }
        for g in gainers
    ]

    result = {
        "source": source,
        "top_gainers": top_gainers_list,
        "our_picks_in_top": our_picks_in_top,
        "patterns": patterns,
        "coingecko_trending": coingecko_trending,
        "catch_rate": f"{len(our_picks_in_top)}/{len(gainers)}",
    }

    _save_json(TOP_GAINERS_FILE, {**result, "timestamp": _now_iso()})

    # Print
    print(f"  Source:                {source}")
    print(f"  Top 20 gainers (24h):")
    for g in top_gainers_list[:10]:
        in_ours = " ** WE HAVE THIS **" if g["symbol"] in our_symbols else ""
        print(f"    {g['symbol']:15s}  +{g['priceChangePercent']:6.2f}%  vol={g['volume']:>14,.0f}{in_ours}")
    if len(top_gainers_list) > 10:
        print(f"    ... and {len(top_gainers_list) - 10} more")
    print(f"  Our picks in top 20:   {len(our_picks_in_top)} ({result['catch_rate']})")
    for p in our_picks_in_top:
        print(f"    {p['symbol']} dir={p['our_direction']} our_pnl={p['our_pnl_pct']}%")
    print(f"  Patterns: avg gain={patterns['avg_gain_pct']}%, high-vol coins={patterns['symbols_with_usdt_volume_above_10m']}")

    if coingecko_trending:
        print(f"  CoinGecko trending ({len(coingecko_trending)} coins):")
        for c in coingecko_trending[:5]:
            print(f"    {c['symbol']:15s}  {c['name']}")

    # Store losers for section 4
    result["_losers_raw"] = losers_all
    result["_our_symbols"] = our_symbols
    return result


# ---------------------------------------------------------------------------
# Section 4: Top Losers - Short Strategy Ideas
# ---------------------------------------------------------------------------
def section_top_losers(gainers_result):
    """Analyse top losers and generate SHORT signal ideas."""
    print("\n" + "=" * 70)
    print("SECTION 4: TOP LOSERS - SHORT STRATEGY IDEAS")
    print("=" * 70)

    losers_raw = gainers_result.get("_losers_raw", [])
    our_symbols = gainers_result.get("_our_symbols", set())

    if not losers_raw:
        print("  No loser data available (market data fetch failed).")
        result = {"losers": [], "short_ideas": [], "timestamp": _now_iso()}
        _save_json(LOSER_PATTERNS_FILE, result)
        return result

    losers_list = []
    short_ideas = []

    for l in losers_raw:
        sym = l.get("symbol", "")
        pcp = l.get("_pcp", 0)
        vol = l.get("_vol", 0)
        price = l.get("_price", 0)

        losers_list.append({
            "symbol": sym,
            "priceChangePercent": round(pcp, 2),
            "volume": round(vol, 0),
            "lastPrice": price,
            "we_have_pick": sym in our_symbols,
        })

        # Generate SHORT ideas for severe losers
        if pcp < -5.0 and vol > 5_000_000:
            # High-volume dump = potential continuation short
            short_ideas.append({
                "symbol": sym,
                "type": "continuation_short",
                "reason": f"Heavy dump ({pcp:.1f}%) with high volume ({vol:,.0f}). Likely panic selling continues.",
                "suggested_entry": "Wait for dead cat bounce to -38.2% fib retracement",
                "suggested_sl": "Above pre-dump high",
                "confidence": "MEDIUM" if pcp < -10 else "LOW",
            })
        elif pcp < -3.0 and vol < 1_000_000:
            # Low volume dump = potential exhaustion
            short_ideas.append({
                "symbol": sym,
                "type": "low_volume_fade",
                "reason": f"Dropping ({pcp:.1f}%) on thin volume ({vol:,.0f}). No buyer interest.",
                "suggested_entry": "Short on any weak bounce",
                "suggested_sl": "Above 24h high",
                "confidence": "LOW",
            })

    # Pattern analysis
    pcp_values = [l["priceChangePercent"] for l in losers_list]
    pattern_summary = {
        "avg_loss_pct": round(sum(pcp_values) / len(pcp_values), 2) if pcp_values else 0,
        "worst_loss_pct": round(min(pcp_values), 2) if pcp_values else 0,
        "losers_below_5pct": sum(1 for p in pcp_values if p < -5),
        "losers_below_10pct": sum(1 for p in pcp_values if p < -10),
        "our_picks_in_losers": sum(1 for l in losers_list if l["we_have_pick"]),
    }

    result = {
        "timestamp": _now_iso(),
        "losers": losers_list,
        "short_ideas": short_ideas,
        "pattern_summary": pattern_summary,
    }
    _save_json(LOSER_PATTERNS_FILE, result)

    # Print
    print(f"  Bottom 20 losers (24h):")
    for l in losers_list[:10]:
        flag = " ** WE HAVE THIS **" if l["we_have_pick"] else ""
        print(f"    {l['symbol']:15s}  {l['priceChangePercent']:+6.2f}%  vol={l['volume']:>14,.0f}{flag}")
    if len(losers_list) > 10:
        print(f"    ... and {len(losers_list) - 10} more")
    print(f"  Our picks in bottom 20: {pattern_summary['our_picks_in_losers']}")
    print(f"  Severe dumps (>5%):    {pattern_summary['losers_below_5pct']}")
    print(f"  Short ideas generated: {len(short_ideas)}")
    for idea in short_ideas[:5]:
        print(f"    {idea['symbol']} [{idea['type']}] conf={idea['confidence']} - {idea['reason'][:80]}")

    return result


# ---------------------------------------------------------------------------
# Section 5: Strategy DNA Analysis
# ---------------------------------------------------------------------------
def section_strategy_dna():
    """Analyse strategy performance and suggest mutations for underperformers."""
    print("\n" + "=" * 70)
    print("SECTION 5: STRATEGY DNA ANALYSIS")
    print("=" * 70)

    strat_perf = _load_json(STRATEGY_PERF, default={})
    resolved = _load_json(RESOLVED_PICKS, default=[])

    if not strat_perf:
        print("  No strategy performance data available.")
        _save_json(STRATEGY_MUTATIONS_FILE, {"timestamp": _now_iso(), "mutations": []})
        return {"top_5": [], "bottom_5": [], "mutations": []}

    # Compute extended metrics per strategy
    # Group resolved picks by strategy for more analysis
    strat_picks = defaultdict(list)
    for pick in resolved:
        if pick.get("status") == "CLOSED":
            strat = pick.get("strategy", "unknown")
            try:
                pnl = float(pick.get("pnl_pct", 0))
            except (ValueError, TypeError):
                continue
            strat_picks[strat].append(pnl)

    enriched = []
    for name, data in strat_perf.items():
        closed = data.get("closed_picks", 0)
        if closed < 10:
            continue

        wr = data.get("win_rate", 0)
        avg_pnl = data.get("avg_pnl", 0)
        pf = data.get("profit_factor", 0)

        # Compute extra metrics from resolved picks if available
        pnl_list = strat_picks.get(name, [])
        max_consec_wins = 0
        max_consec_losses = 0
        if pnl_list:
            # Consecutive wins/losses
            cw = 0
            cl = 0
            for p in pnl_list:
                if p > 0:
                    cw += 1
                    cl = 0
                else:
                    cl += 1
                    cw = 0
                max_consec_wins = max(max_consec_wins, cw)
                max_consec_losses = max(max_consec_losses, cl)

            # Sharpe-like ratio (per-trade)
            mean_pnl = sum(pnl_list) / len(pnl_list)
            if len(pnl_list) > 1:
                variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / (len(pnl_list) - 1)
                std_pnl = math.sqrt(max(variance, 1e-12))
                sharpe = mean_pnl / std_pnl if std_pnl > 0.001 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0

        # Composite score for ranking: WR * 40 + PF * 20 + sharpe * 20 + avg_pnl_sign * 20
        composite = (
            (wr if isinstance(wr, (int, float)) else 0) * 40
            + min(max(pf if isinstance(pf, (int, float)) else 0, 0), 5) * 4
            + min(max(sharpe, -2), 2) * 10
            + (20 if (isinstance(avg_pnl, (int, float)) and avg_pnl > 0) else 0)
        )

        enriched.append({
            "name": name,
            "closed_picks": closed,
            "win_rate": wr,
            "avg_pnl": avg_pnl,
            "profit_factor": pf,
            "sharpe": round(sharpe, 3),
            "max_consec_wins": max_consec_wins,
            "max_consec_losses": max_consec_losses,
            "composite_score": round(composite, 2),
        })

    enriched.sort(key=lambda x: x["composite_score"], reverse=True)

    top_5 = enriched[:5]
    bottom_5 = enriched[-5:] if len(enriched) >= 5 else enriched

    # Generate mutation suggestions for bottom 5
    mutations = []
    for strat in bottom_5:
        suggestions = []
        wr = strat["win_rate"]
        avg_pnl = strat["avg_pnl"]
        pf = strat["profit_factor"]

        if isinstance(wr, (int, float)) and wr < 0.35:
            suggestions.append("Try INVERSE direction (if WR < 35%, opposite may work)")
        if isinstance(wr, (int, float)) and wr > 0.5 and isinstance(avg_pnl, (int, float)) and avg_pnl < 0:
            suggestions.append("Widen TP target (winning often but gains too small vs losses)")
        if isinstance(wr, (int, float)) and wr < 0.4:
            suggestions.append("Tighten SL by 20% (cut losses faster)")
        if isinstance(pf, (int, float)) and 0 < pf < 0.8:
            suggestions.append("Try different timeframe (4H instead of 1H, or vice versa)")
        if strat["max_consec_losses"] >= 5:
            suggestions.append(f"Add cooldown after {strat['max_consec_losses']} consecutive losses")
        if isinstance(avg_pnl, (int, float)) and avg_pnl < -1:
            suggestions.append("Consider symbol rotation (different asset pair)")
        if not suggestions:
            suggestions.append("Minor tuning: adjust entry confirmation filters")

        mutations.append({
            "strategy": strat["name"],
            "current_wr": strat["win_rate"],
            "current_pf": strat["profit_factor"],
            "current_avg_pnl": strat["avg_pnl"],
            "closed_picks": strat["closed_picks"],
            "mutations": suggestions,
        })

    result = {
        "timestamp": _now_iso(),
        "total_strategies_analysed": len(enriched),
        "top_5": top_5,
        "bottom_5": bottom_5,
        "mutations": mutations,
    }
    _save_json(STRATEGY_MUTATIONS_FILE, result)

    # Print
    print(f"  Strategies with 10+ trades: {len(enriched)}")
    print(f"\n  TOP 5 STRATEGIES:")
    for i, s in enumerate(top_5, 1):
        print(f"    {i}. {s['name'][:40]:40s}  WR={s['win_rate']:.2f}  PF={s['profit_factor']:.2f}  sharpe={s['sharpe']:.3f}  trades={s['closed_picks']}")

    print(f"\n  BOTTOM 5 STRATEGIES:")
    for i, s in enumerate(bottom_5, 1):
        print(f"    {i}. {s['name'][:40]:40s}  WR={s['win_rate']:.2f}  PF={s['profit_factor']:.2f}  sharpe={s['sharpe']:.3f}  trades={s['closed_picks']}")

    print(f"\n  MUTATION SUGGESTIONS:")
    for m in mutations:
        print(f"    {m['strategy'][:45]}:")
        for sug in m["mutations"]:
            print(f"      -> {sug}")

    return result


# ---------------------------------------------------------------------------
# Section 6: Summary Report + Health Score
# ---------------------------------------------------------------------------
def section_summary(s1_corr, s2_regime, s3_gainers, s4_losers, s5_dna, payload):
    """Generate overall health score and formatted summary."""
    print("\n" + "=" * 70)
    print("SECTION 6: OVERALL HEALTH SUMMARY")
    print("=" * 70)

    health_score = 0
    health_components = {}

    # Component 1: Correlation improving? (0-20 points)
    corr_points = 10  # base
    r = s1_corr.get("correlation_r")
    if r is not None:
        if r > 0.3:
            corr_points = 20
        elif r > 0.1:
            corr_points = 15
        elif r > 0:
            corr_points = 10
        else:
            corr_points = 5
    if "IMPROVING" in s1_corr.get("trend", ""):
        corr_points = min(corr_points + 5, 20)
    elif "DECLINING" in s1_corr.get("trend", ""):
        corr_points = max(corr_points - 5, 0)
    health_components["score_pnl_correlation"] = corr_points
    health_score += corr_points

    # Component 2: Win rate > 45%? (0-25 points)
    overall_wr = payload.get("summary", {}).get("overall_win_rate", 0)
    if overall_wr >= 55:
        wr_points = 25
    elif overall_wr >= 50:
        wr_points = 20
    elif overall_wr >= 45:
        wr_points = 15
    elif overall_wr >= 40:
        wr_points = 10
    else:
        wr_points = 5
    health_components["win_rate"] = wr_points
    health_score += wr_points

    # Component 3: Catching top gainers? (0-20 points)
    catch_str = s3_gainers.get("catch_rate", "0/20")
    try:
        caught, total = catch_str.split("/")
        catch_ratio = int(caught) / max(int(total), 1)
    except Exception:
        catch_ratio = 0
    if catch_ratio >= 0.3:
        gainer_points = 20
    elif catch_ratio >= 0.2:
        gainer_points = 15
    elif catch_ratio >= 0.1:
        gainer_points = 10
    elif catch_ratio > 0:
        gainer_points = 5
    else:
        gainer_points = 2
    health_components["catching_gainers"] = gainer_points
    health_score += gainer_points

    # Component 4: Strategies evolving? (0-20 points)
    top5_avg_wr = 0
    if s5_dna.get("top_5"):
        wrs = [s["win_rate"] for s in s5_dna["top_5"] if isinstance(s.get("win_rate"), (int, float))]
        top5_avg_wr = sum(wrs) / len(wrs) if wrs else 0
    if top5_avg_wr >= 0.7:
        dna_points = 20
    elif top5_avg_wr >= 0.55:
        dna_points = 15
    elif top5_avg_wr >= 0.4:
        dna_points = 10
    else:
        dna_points = 5
    health_components["strategy_quality"] = dna_points
    health_score += dna_points

    # Component 5: Smart picks outperforming? (0-15 points)
    smart_wr = s2_regime.get("smart_picks_wr", 0)
    if smart_wr >= 60:
        smart_points = 15
    elif smart_wr >= 50:
        smart_points = 10
    elif smart_wr >= 40:
        smart_points = 5
    else:
        smart_points = 2
    health_components["smart_picks"] = smart_points
    health_score += smart_points

    health_score = min(health_score, 100)

    # Determine grade
    if health_score >= 80:
        grade = "A - Excellent"
    elif health_score >= 65:
        grade = "B - Good"
    elif health_score >= 50:
        grade = "C - Average"
    elif health_score >= 35:
        grade = "D - Below Average"
    else:
        grade = "F - Needs Attention"

    print(f"\n  OVERALL HEALTH SCORE:  {health_score}/100  ({grade})")
    print(f"\n  Component Breakdown:")
    for comp, pts in sorted(health_components.items()):
        max_pts = {"score_pnl_correlation": 20, "win_rate": 25, "catching_gainers": 20,
                   "strategy_quality": 20, "smart_picks": 15}.get(comp, 20)
        bar = "#" * pts + "." * (max_pts - pts)
        print(f"    {comp:25s}  {pts:2d}/{max_pts:2d}  [{bar}]")

    print(f"\n  Key Metrics:")
    print(f"    Overall WR:          {overall_wr}%")
    print(f"    Score-PnL corr (r):  {r:.4f}" if r is not None else "    Score-PnL corr (r):  N/A")
    print(f"    Top gainer catch:    {catch_str}")
    print(f"    Smart picks WR:      {smart_wr}%")
    print(f"    Strategies analysed: {s5_dna.get('total_strategies_analysed', 0)}")

    # Profit factor
    pf = payload.get("summary", {}).get("profit_factor")
    expectancy = payload.get("summary", {}).get("expectancy")
    print(f"    Profit factor:       {pf}")
    print(f"    Expectancy:          {expectancy}")

    print(f"\n  Anomalies: {s1_corr.get('anomaly_count', 0)} score-PnL mismatches")
    print(f"  Short ideas:  {len(s4_losers.get('short_ideas', []))}")
    print(f"  Mutations:    {len(s5_dna.get('mutations', []))}")

    return {
        "health_score": health_score,
        "grade": grade,
        "components": health_components,
        "overall_wr": overall_wr,
        "profit_factor": pf,
        "expectancy": expectancy,
    }


# ---------------------------------------------------------------------------
# Main run() function
# ---------------------------------------------------------------------------
def run():
    """Execute all analysis sections and return combined results."""
    print("=" * 70)
    print(f"  PICK QUALITY ANALYSIS  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load dashboard payload
    payload = _load_json(DASHBOARD_PAYLOAD, default={})
    if not payload:
        print("ERROR: Could not load dashboard_payload.json")
        return {"error": "dashboard_payload.json not found or empty"}

    total_active = payload.get("summary", {}).get("total_active_picks", 0)
    total_closed = payload.get("summary", {}).get("total_closed_picks", 0)
    print(f"  Active picks: {total_active}  |  Closed picks: {total_closed}")

    # Run all sections
    s1 = section_score_pnl_correlation(payload)
    s2 = section_regime_performance(payload)
    s3 = section_top_gainers(payload)
    s4 = section_top_losers(s3)
    s5 = section_strategy_dna()
    s6 = section_summary(s1, s2, s3, s4, s5, payload)

    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70)

    return {
        "timestamp": _now_iso(),
        "score_pnl_correlation": s1,
        "regime_performance": s2,
        "top_gainers": {k: v for k, v in s3.items() if not k.startswith("_")},
        "loser_patterns": s4,
        "strategy_dna": s5,
        "summary": s6,
    }


if __name__ == "__main__":
    run()

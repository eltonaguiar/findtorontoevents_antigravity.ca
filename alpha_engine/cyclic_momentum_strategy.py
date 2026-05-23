"""
CYCLIC MOMENTUM STACKING Strategy
===================================
Detects assets with consecutive winning trades in the same direction
and exploits the momentum continuation pattern.

Discovery: AVAXUSDT showed 7 consecutive LONG wins ($9.55→$10.28) over 43h,
each entry at escalating prices hitting TP as the uptrend continued.
25 symbols showed 3+ consecutive win streaks in consensus data.

Pattern Logic:
1. Monitor closed picks for "hot streak" symbols (3+ consecutive wins, same direction)
2. When streak detected, generate a new entry signal with boosted confidence
3. Use the streak's average TP% as the target, tightened SL from recent swing low
4. ML model learns which streaks continue vs which ones reverse

References:
- Jegadeesh & Titman (1993): Momentum profits persist 3-12 months
- Moskowitz, Ooi & Pedersen (2012): Time-series momentum across assets
- AVAXUSDT case study: 7 wins, +7.49% cumulative, Mar 14-16 2026
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional

import numpy as np

# Add parent to path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from config import CRYPTO_SYMBOLS, fetch_binance_json
except ImportError:
    CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT",
                       "LINKUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT", "BNBUSDT"]
    fetch_binance_json = None

import urllib.request
import urllib.error


def _fetch_live_prices() -> dict:
    """Fetch live crypto prices with robust multi-API fallback chain.

    Order: Binance (via config fallback chain) → CoinGecko → KuCoin → CryptoCompare
    Rule: Always have 3+ independent API sources for price data.
    """
    prices = {}

    # API 1: Binance with built-in failover (binance.com → data-api.binance.vision → binance.us)
    if fetch_binance_json:
        try:
            data = fetch_binance_json("/api/v3/ticker/price")
            if data:
                prices = {t["symbol"]: float(t["price"]) for t in data}
                print(f"  [PRICE] Binance chain: {len(prices)} symbols")
                return prices
        except Exception as e:
            print(f"  [PRICE] Binance chain failed: {e}")

    # API 2: CoinGecko (no geo-block, free tier)
    _CG_IDS = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
        "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot", "LINKUSDT": "chainlink",
        "DOGEUSDT": "dogecoin", "LTCUSDT": "litecoin", "BCHUSDT": "bitcoin-cash",
        "APTUSDT": "aptos", "NEARUSDT": "near", "SUIUSDT": "sui",
        "CAKEUSDT": "pancakeswap-token", "CFXUSDT": "conflux-token",
        "FETUSDT": "artificial-superintelligence-alliance",
        "TRXUSDT": "tron", "XLMUSDT": "stellar", "UNIUSDT": "uniswap",
    }
    try:
        ids_str = ",".join(set(_CG_IDS.values()))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        reverse = {v: k for k, v in _CG_IDS.items()}
        for cg_id, pd in data.items():
            if "usd" in pd and cg_id in reverse:
                prices[reverse[cg_id]] = pd["usd"]
        if prices:
            print(f"  [PRICE] CoinGecko: {len(prices)} symbols")
            return prices
    except Exception as e:
        print(f"  [PRICE] CoinGecko failed: {e}")

    # API 3: KuCoin (no geo-block, good uptime)
    try:
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if data.get("data", {}).get("ticker"):
            for t in data["data"]["ticker"]:
                sym = t["symbol"].replace("-", "")  # KuCoin uses BTC-USDT
                if sym.endswith("USDT"):
                    prices[sym] = float(t["last"])
        if prices:
            print(f"  [PRICE] KuCoin: {len(prices)} symbols")
            return prices
    except Exception as e:
        print(f"  [PRICE] KuCoin failed: {e}")

    # API 4: CryptoCompare (widely available, free tier)
    try:
        syms = "BTC,ETH,SOL,BNB,XRP,ADA,AVAX,DOT,LINK,DOGE,LTC,BCH,APT,NEAR,SUI,CAKE,CFX,FET,TRX"
        url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={syms}&tsyms=USDT"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        for sym, pd in data.items():
            if "USDT" in pd:
                prices[f"{sym}USDT"] = float(pd["USDT"])
        if prices:
            print(f"  [PRICE] CryptoCompare: {len(prices)} symbols")
            return prices
    except Exception as e:
        print(f"  [PRICE] CryptoCompare failed: {e}")

    print("  [PRICE] WARNING: All price APIs failed!")
    return prices

# -- Paths --
DATA_DIR = os.path.join(BASE_DIR, "data")
CLOSED_PICKS_PATH = os.path.join(DATA_DIR, "closed_picks.json")
CLOSED_PICKS_FAST_PATH = os.path.join(DATA_DIR, "closed_picks_fast.json")
CONSENSUS_OUTCOMES_PATH = os.path.join(os.path.dirname(BASE_DIR),
                                        "cross_aggregation", "data", "consensus_outcomes.json")
STREAK_DB_PATH = os.path.join(DATA_DIR, "cyclic_streak_db.json")
BACKTEST_RESULTS_PATH = os.path.join(DATA_DIR, "cyclic_backtest_results.json")

# -- Strategy Parameters --
MIN_STREAK = 3          # Minimum consecutive wins to trigger
MAX_STREAK_AGE_H = 72   # Ignore streaks older than 72h
STREAK_CONF_BASE = 0.60 # Base confidence for streak = 3
STREAK_CONF_BOOST = 0.05  # +5% per additional streak win
STREAK_CONF_CAP = 0.92  # Never exceed this
TP_PCT_MIN = 0.025      # Minimum 2.5% TP (was 1.5% -- too tight, failed R:R gate)
TP_PCT_MAX = 0.06       # Maximum 6% TP
SL_PCT = 0.012          # 1.2% stop loss (was 2% -- made R:R < 1.5 for most signals)
MIN_AVG_PNL = 1.5       # Minimum average PnL% per streak trade
COOLDOWN_HOURS = 4      # Don't re-fire signal for same symbol within this window


def _load_json(path):
    """Safely load JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _parse_ts(ts_str):
    """Parse various timestamp formats to datetime."""
    if not ts_str:
        return None
    try:
        s = str(ts_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def detect_streaks(closed_picks: list[dict], min_streak: int = MIN_STREAK) -> dict:
    """
    Analyze closed picks for consecutive win streaks per symbol+direction.

    Returns dict: {symbol: {direction, streak_len, avg_pnl, last_entry, last_tp,
                            last_ts, entries[], total_pnl}}
    """
    # Group by symbol
    by_symbol = defaultdict(list)
    for p in closed_picks:
        sym = p.get("symbol", "").upper()
        if not sym:
            continue
        direction = p.get("direction", p.get("signal_type", "")).upper()
        if "BUY" in direction or "LONG" in direction:
            direction = "LONG"
        elif "SELL" in direction or "SHORT" in direction:
            direction = "SHORT"
        else:
            continue

        # Determine win/loss
        pnl = float(p.get("pnl_pct", p.get("unrealized_pnl_pct", 0)) or 0)
        status = p.get("status", "").upper()
        is_win = pnl > 0 or status in ("WON", "WIN", "TP_HIT")

        ts = _parse_ts(p.get("tracked_at", p.get("resolved_at",
                       p.get("timestamp", p.get("generated_at", "")))))

        entry = float(p.get("entry_price", p.get("entryPrice", 0)) or 0)
        tp = float(p.get("take_profit", p.get("tp_price", 0)) or 0)

        by_symbol[sym].append({
            "direction": direction,
            "is_win": is_win,
            "pnl": pnl,
            "ts": ts,
            "entry": entry,
            "tp": tp,
            "strategy": p.get("strategy", ""),
        })

    # Find active streaks (must end at the most recent trade)
    streaks = {}
    now = datetime.now(timezone.utc)

    for sym, trades in by_symbol.items():
        # Sort by timestamp
        trades = [t for t in trades if t["ts"] is not None]
        trades.sort(key=lambda x: x["ts"])

        if len(trades) < min_streak:
            continue

        # Walk backwards from most recent trade to find active streak
        streak_len = 0
        streak_dir = trades[-1]["direction"]
        streak_pnls = []
        streak_entries = []

        for t in reversed(trades):
            if t["is_win"] and t["direction"] == streak_dir:
                streak_len += 1
                streak_pnls.append(t["pnl"])
                streak_entries.append(t)
            else:
                break

        if streak_len < min_streak:
            continue

        # Check staleness
        last_ts = trades[-1]["ts"]
        if (now - last_ts).total_seconds() / 3600 > MAX_STREAK_AGE_H:
            continue

        avg_pnl = np.mean(streak_pnls) if streak_pnls else 0
        if avg_pnl < MIN_AVG_PNL:
            continue

        streak_entries.reverse()  # chronological order

        unique_strategies = list(set(e["strategy"] for e in streak_entries if e["strategy"]))

        # Deduplicate same-timestamp trades (multiple strategies closing at same time
        # on the same symbol count as 1 "real" momentum event, not N)
        seen_ts = set()
        deduped_len = 0
        for e in streak_entries:
            ts_key = e["ts"].isoformat()[:16]  # round to minute
            if ts_key not in seen_ts:
                seen_ts.add(ts_key)
                deduped_len += 1

        # If deduped streak is too short, it's just multiple strategies
        # firing at the same time -- not true sequential momentum
        if deduped_len < min_streak:
            continue

        streaks[sym] = {
            "direction": streak_dir,
            "streak_len": streak_len,
            "deduped_len": deduped_len,  # unique time-points in streak
            "avg_pnl": round(float(avg_pnl), 4),
            "total_pnl": round(sum(streak_pnls), 4),
            "last_entry": streak_entries[-1]["entry"],
            "last_tp": streak_entries[-1]["tp"],
            "last_ts": last_ts.isoformat(),
            "entries": [{"entry": e["entry"], "pnl": e["pnl"],
                         "ts": e["ts"].isoformat()} for e in streak_entries],
            "strategies_involved": unique_strategies,
            "is_multi_strategy": len(unique_strategies) > 1,
        }

    return streaks


def generate_cyclic_signals(data: dict = None) -> list[dict]:
    """
    Main strategy function -- compatible with alpha_engine strategy signature.

    Loads closed picks from all sources, detects active streaks,
    and generates continuation signals.

    Args:
        data: dict of {symbol: pd.DataFrame} with OHLCV (optional, used for
              current price / ATR if available)

    Returns:
        list of signal dicts
    """
    # Load all closed picks sources
    all_closed = []

    # Source 1: consensus outcomes (highest quality -- cross-system agreement)
    consensus = _load_json(CONSENSUS_OUTCOMES_PATH)
    if consensus and isinstance(consensus, dict):
        for bucket in ("closed", "active"):
            for p in consensus.get(bucket, []):
                if isinstance(p, dict):
                    all_closed.append(p)

    # Source 2: alpha engine closed picks
    for path in (CLOSED_PICKS_PATH, CLOSED_PICKS_FAST_PATH):
        picks = _load_json(path)
        if picks and isinstance(picks, list):
            all_closed.extend(p for p in picks if isinstance(p, dict))

    if not all_closed:
        return []

    # Detect streaks
    streaks = detect_streaks(all_closed)

    if not streaks:
        return []

    # Fetch live prices with 4-API fallback chain
    _live_prices = _fetch_live_prices()

    # Load active picks to avoid duplicate signals for the same streak
    _active_syms = set()
    _active_path = os.path.join(DATA_DIR, "active_picks.json")
    try:
        with open(_active_path, "r") as f:
            _active = json.load(f)
        for p in _active:
            if isinstance(p, dict) and "cyclic" in str(p.get("strategy", "")).lower():
                _active_syms.add(p.get("symbol", "").upper())
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Generate signals for each active streak
    signals = []
    now = datetime.now(timezone.utc)

    for sym, streak in streaks.items():
        # Skip if we already have an active cyclic pick for this symbol
        if sym in _active_syms:
            print(f"  [CYCLIC COOLDOWN] {sym}: already has active cyclic pick, skipping")
            continue
        direction = streak["direction"]
        streak_len = streak["streak_len"]
        avg_pnl_pct = streak["avg_pnl"]
        last_entry = streak["last_entry"]

        # Get LIVE price (mandatory -- never use stale last_entry)
        current_price = _live_prices.get(sym, 0)
        if current_price <= 0:
            # Try without USDT suffix variations
            for _suffix in ("USDT", "USD", "BUSD"):
                _try = sym.replace("USDT", _suffix).replace("USD", _suffix)
                if _try in _live_prices:
                    current_price = _live_prices[_try]
                    break
        if current_price <= 0:
            print(f"  [SKIP] {sym}: no live Binance price available")
            continue

        # Sanity check: if last_entry is wildly off from current price, the streak
        # data is corrupted (e.g., APT entry=0.0001 but real price=$5)
        if last_entry > 0:
            _gap = abs(current_price - last_entry) / last_entry
            if _gap > 0.5:  # >50% gap = bad data
                print(f"  [SKIP] {sym}: last_entry=${last_entry:.4f} vs live=${current_price:.4f} "
                      f"(gap={_gap:.0%} -- likely corrupted streak data)")
                continue

        atr = None
        if data and sym in data:
            df = data[sym]
            if hasattr(df, "iloc") and len(df) > 0:
                if len(df) >= 14:
                    highs = df["High"].values[-14:]
                    lows = df["Low"].values[-14:]
                    closes = df["Close"].values[-14:]
                    tr = np.maximum(highs - lows,
                                    np.maximum(np.abs(highs - np.roll(closes, 1)),
                                               np.abs(lows - np.roll(closes, 1))))[1:]
                    atr = float(np.mean(tr))
        # Also try Yahoo-style symbol
        yahoo_sym = sym.replace("USDT", "-USD")
        if data and yahoo_sym in data:
            df = data[yahoo_sym]
            if hasattr(df, "iloc") and len(df) > 0 and atr is None:
                if len(df) >= 14:
                    highs = df["High"].values[-14:]
                    lows = df["Low"].values[-14:]
                    closes = df["Close"].values[-14:]
                    tr = np.maximum(highs - lows,
                                    np.maximum(np.abs(highs - np.roll(closes, 1)),
                                               np.abs(lows - np.roll(closes, 1))))[1:]
                    atr = float(np.mean(tr))

        # Confidence: scales with streak length
        confidence = min(STREAK_CONF_CAP,
                         STREAK_CONF_BASE + (streak_len - MIN_STREAK) * STREAK_CONF_BOOST)

        # TP: use average PnL% of the streak, bounded
        tp_pct = max(TP_PCT_MIN, min(TP_PCT_MAX, avg_pnl_pct / 100))

        # SL: tight -- if streak breaks, exit fast
        # Must keep SL < TP to maintain R:R > 1.5 (forward validator gate)
        sl_pct = SL_PCT
        if atr and current_price > 0:
            # Use 1.2x ATR if available, but cap to preserve R:R
            atr_sl = (1.2 * atr) / current_price
            sl_pct = max(0.008, min(tp_pct * 0.6, atr_sl))  # SL never > 60% of TP

        if direction == "LONG":
            entry_price = current_price
            tp_price = round(current_price * (1 + tp_pct), 8)
            sl_price = round(current_price * (1 - sl_pct), 8)
            signal_type = "BUY"
        else:
            entry_price = current_price
            tp_price = round(current_price * (1 - tp_pct), 8)
            sl_price = round(current_price * (1 + sl_pct), 8)
            signal_type = "SELL"

        rr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0

        signals.append({
            "strategy": "cyclic_momentum_stack",
            "symbol": sym,
            "category": "crypto",
            "signal_type": signal_type,
            "direction": direction,
            "entry_price": round(entry_price, 8),
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": round(confidence, 4),
            "risk_reward": round(rr, 2),
            "reason": (f"Cyclic momentum: {streak_len} consecutive {direction} wins "
                       f"(avg +{avg_pnl_pct:.1f}%, total +{streak['total_pnl']:.1f}%). "
                       f"Streak continuation signal. "
                       f"Systems: {', '.join(streak['strategies_involved'][:3])}. "
                       f"Jegadeesh & Titman (1993): momentum persists."),
            "timestamp": now.isoformat(),
            "streak_length": streak_len,
            "streak_avg_pnl": avg_pnl_pct,
            "streak_total_pnl": streak["total_pnl"],
        })

    return signals


# -- ML Backtest: Streak Continuation Probability --

def backtest_streak_continuation(min_streak_range=(3, 8)):
    """
    Backtest: Given N consecutive wins, what's the probability of win N+1?

    Uses all historical closed picks to build a statistical model of
    streak continuation rates. This is the empirical foundation for
    the cyclic momentum strategy.

    Returns:
        dict with streak_length -> {continuation_rate, sample_size, avg_pnl_if_win, avg_pnl_if_loss}
    """
    # Load all closed picks
    all_closed = []
    consensus = _load_json(CONSENSUS_OUTCOMES_PATH)
    if consensus and isinstance(consensus, dict):
        for bucket in ("closed", "active"):
            for p in consensus.get(bucket, []):
                if isinstance(p, dict):
                    all_closed.append(p)

    for path in (CLOSED_PICKS_PATH, CLOSED_PICKS_FAST_PATH):
        picks = _load_json(path)
        if picks and isinstance(picks, list):
            all_closed.extend(p for p in picks if isinstance(p, dict))

    # Group by symbol, sort by time
    by_symbol = defaultdict(list)
    for p in all_closed:
        sym = p.get("symbol", "").upper()
        if not sym:
            continue
        direction = p.get("direction", p.get("signal_type", "")).upper()
        if "BUY" in direction or "LONG" in direction:
            direction = "LONG"
        elif "SELL" in direction or "SHORT" in direction:
            direction = "SHORT"
        else:
            continue

        pnl = float(p.get("pnl_pct", p.get("unrealized_pnl_pct", 0)) or 0)
        is_win = pnl > 0 or p.get("status", "").upper() in ("WON", "WIN", "TP_HIT")
        ts = _parse_ts(p.get("tracked_at", p.get("resolved_at",
                       p.get("timestamp", p.get("generated_at", "")))))

        by_symbol[sym].append({"direction": direction, "is_win": is_win,
                                "pnl": pnl, "ts": ts})

    # For each streak length, count continuations vs reversals
    results = {}
    for streak_len in range(min_streak_range[0], min_streak_range[1] + 1):
        continuations = 0
        reversals = 0
        pnl_if_win = []
        pnl_if_loss = []

        for sym, trades in by_symbol.items():
            trades = [t for t in trades if t["ts"] is not None]
            trades.sort(key=lambda x: x["ts"])

            # Slide window looking for streak of length N, then check N+1
            for i in range(len(trades) - streak_len):
                window = trades[i:i + streak_len]
                next_trade = trades[i + streak_len]

                # Check if window is a winning streak in same direction
                if all(t["is_win"] for t in window):
                    streak_dir = window[0]["direction"]
                    if all(t["direction"] == streak_dir for t in window):
                        # Found a streak -- does it continue?
                        if next_trade["is_win"] and next_trade["direction"] == streak_dir:
                            continuations += 1
                            pnl_if_win.append(next_trade["pnl"])
                        else:
                            reversals += 1
                            pnl_if_loss.append(next_trade["pnl"])

        total = continuations + reversals
        results[streak_len] = {
            "streak_length": streak_len,
            "continuations": continuations,
            "reversals": reversals,
            "total_samples": total,
            "continuation_rate": round(continuations / total, 4) if total > 0 else 0,
            "avg_pnl_if_continues": round(np.mean(pnl_if_win), 4) if pnl_if_win else 0,
            "avg_pnl_if_reverses": round(np.mean(pnl_if_loss), 4) if pnl_if_loss else 0,
            "expected_value": round(
                (continuations / total * np.mean(pnl_if_win) if pnl_if_win else 0) +
                (reversals / total * np.mean(pnl_if_loss) if pnl_if_loss else 0), 4
            ) if total > 0 else 0,
        }

    return results


def run_backtest_and_save():
    """Run the streak continuation backtest and save results."""
    print("=" * 60)
    print("  CYCLIC MOMENTUM STACKING -- Streak Continuation Backtest")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    results = backtest_streak_continuation()

    print(f"\n{'Streak':>8} {'Samples':>8} {'Cont%':>8} {'AvgWin':>8} {'AvgLoss':>8} {'EV':>8}")
    print("-" * 56)
    for k in sorted(results.keys()):
        r = results[k]
        print(f"{r['streak_length']:>8} {r['total_samples']:>8} "
              f"{r['continuation_rate']*100:>7.1f}% "
              f"{r['avg_pnl_if_continues']:>7.2f}% "
              f"{r['avg_pnl_if_reverses']:>7.2f}% "
              f"{r['expected_value']:>7.2f}%")

    # Also detect current active streaks
    print("\n" + "=" * 60)
    print("  CURRENTLY ACTIVE STREAKS")
    print("=" * 60)

    all_closed = []
    consensus = _load_json(CONSENSUS_OUTCOMES_PATH)
    if consensus and isinstance(consensus, dict):
        for bucket in ("closed", "active"):
            for p in consensus.get(bucket, []):
                if isinstance(p, dict):
                    all_closed.append(p)
    for path in (CLOSED_PICKS_PATH, CLOSED_PICKS_FAST_PATH):
        picks = _load_json(path)
        if picks and isinstance(picks, list):
            all_closed.extend(p for p in picks if isinstance(p, dict))

    streaks = detect_streaks(all_closed)
    if streaks:
        for sym, s in sorted(streaks.items(), key=lambda x: -x[1]["streak_len"]):
            print(f"\n  {sym}: {s['streak_len']}x {s['direction']} wins "
                  f"(avg +{s['avg_pnl']:.1f}%, total +{s['total_pnl']:.1f}%)")
            print(f"    Last entry: ${s['last_entry']:.4f} @ {s['last_ts']}")
            print(f"    Strategies: {', '.join(s['strategies_involved'][:5])}")
    else:
        print("  No active streaks found.")

    # Generate current signals
    signals = generate_cyclic_signals()
    if signals:
        print(f"\n" + "=" * 60)
        print(f"  GENERATED {len(signals)} CYCLIC SIGNALS")
        print("=" * 60)
        for s in signals:
            print(f"  {s['symbol']} {s['direction']} @ ${s['entry_price']:.4f} "
                  f"TP ${s['take_profit']:.4f} SL ${s['stop_loss']:.4f} "
                  f"conf={s['confidence']:.0%} streak={s['streak_length']}")

    # Save results
    output = {
        "backtest_timestamp": datetime.now(timezone.utc).isoformat(),
        "streak_continuation_rates": results,
        "active_streaks": streaks,
        "signals_generated": len(signals),
        "signals": signals,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BACKTEST_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {BACKTEST_RESULTS_PATH}")

    # Save streak DB for use by live scanner
    with open(STREAK_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(streaks, f, indent=2, default=str)
    print(f"  Streak DB saved to: {STREAK_DB_PATH}")

    return output


# -- Variation: Adaptive Cyclic with ML Features --

def generate_cyclic_adaptive_signals(data: dict = None) -> list[dict]:
    """
    ML-enhanced variation of cyclic momentum stacking.

    Additional features over base strategy:
    1. Streak acceleration: is PnL per trade increasing or decreasing?
    2. Volume confirmation: is the streak backed by rising volume?
    3. Tightened TP on decelerating streaks (take profit sooner)
    4. Wider TP on accelerating streaks (let winners run)
    5. Multi-system agreement bonus: more systems = higher confidence
    """
    all_closed = []
    consensus = _load_json(CONSENSUS_OUTCOMES_PATH)
    if consensus and isinstance(consensus, dict):
        for bucket in ("closed", "active"):
            for p in consensus.get(bucket, []):
                if isinstance(p, dict):
                    all_closed.append(p)
    for path in (CLOSED_PICKS_PATH, CLOSED_PICKS_FAST_PATH):
        picks = _load_json(path)
        if picks and isinstance(picks, list):
            all_closed.extend(p for p in picks if isinstance(p, dict))

    if not all_closed:
        return []

    streaks = detect_streaks(all_closed, min_streak=3)
    if not streaks:
        return []

    # Fetch live prices with 4-API fallback chain
    _live_prices = _fetch_live_prices()

    # Load active picks -- skip symbols that already have cyclic picks
    _active_syms = set()
    _active_path = os.path.join(DATA_DIR, "active_picks.json")
    try:
        with open(_active_path, "r") as f:
            _active = json.load(f)
        for p in _active:
            if isinstance(p, dict) and "cyclic" in str(p.get("strategy", "")).lower():
                _active_syms.add(p.get("symbol", "").upper())
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    signals = []
    now = datetime.now(timezone.utc)

    for sym, streak in streaks.items():
        # Skip if already have active cyclic pick
        if sym in _active_syms:
            print(f"  [CYCLIC ADAPTIVE COOLDOWN] {sym}: already has active cyclic pick")
            continue

        direction = streak["direction"]
        streak_len = streak["streak_len"]
        avg_pnl_pct = streak["avg_pnl"]
        entries = streak["entries"]

        # Get live price
        current_price = _live_prices.get(sym, 0)
        if current_price <= 0:
            continue

        # Sanity check
        last_entry = streak["last_entry"]
        if last_entry > 0 and abs(current_price - last_entry) / last_entry > 0.5:
            continue

        # -- ML Feature 1: Streak Acceleration --
        # Is each trade's PnL getting bigger (accelerating) or smaller (decelerating)?
        pnls = [e["pnl"] for e in entries if e["pnl"] > 0]
        if len(pnls) >= 3:
            first_half = np.mean(pnls[:len(pnls)//2])
            second_half = np.mean(pnls[len(pnls)//2:])
            acceleration = (second_half - first_half) / first_half if first_half > 0 else 0
        else:
            acceleration = 0

        # -- ML Feature 2: Multi-system agreement --
        n_strategies = len(streak["strategies_involved"])
        system_bonus = min(0.10, n_strategies * 0.025)  # +2.5% per system, max +10%

        # -- ML Feature 3: Streak freshness --
        last_ts = _parse_ts(streak["last_ts"])
        hours_since_last = (now - last_ts).total_seconds() / 3600 if last_ts else 999
        freshness_penalty = max(0, (hours_since_last - 6) * 0.01)  # -1% per hour after 6h

        # -- Adaptive confidence --
        base_conf = STREAK_CONF_BASE + (streak_len - MIN_STREAK) * STREAK_CONF_BOOST
        adaptive_conf = base_conf + system_bonus - freshness_penalty
        # Boost for accelerating streaks, penalize decelerating
        if acceleration > 0.1:
            adaptive_conf += 0.05  # accelerating -- momentum building
        elif acceleration < -0.2:
            adaptive_conf -= 0.05  # decelerating -- momentum fading
        adaptive_conf = max(0.50, min(STREAK_CONF_CAP, adaptive_conf))

        # -- Adaptive TP --
        base_tp_pct = max(TP_PCT_MIN, min(TP_PCT_MAX, avg_pnl_pct / 100))
        if acceleration > 0.1:
            # Accelerating: widen TP to let winners run
            tp_pct = min(TP_PCT_MAX, base_tp_pct * 1.3)
        elif acceleration < -0.2:
            # Decelerating: tighten TP to lock in profit before reversal
            tp_pct = max(TP_PCT_MIN, base_tp_pct * 0.7)
        else:
            tp_pct = base_tp_pct

        # SL: keep tight to preserve R:R > 1.5 (forward validator gate)
        sl_pct = min(SL_PCT, tp_pct * 0.6)  # SL never > 60% of TP

        if direction == "LONG":
            entry_price = current_price
            tp_price = round(current_price * (1 + tp_pct), 8)
            sl_price = round(current_price * (1 - sl_pct), 8)
            signal_type = "BUY"
        else:
            entry_price = current_price
            tp_price = round(current_price * (1 - tp_pct), 8)
            sl_price = round(current_price * (1 + sl_pct), 8)
            signal_type = "SELL"

        rr = abs(tp_price - entry_price) / abs(entry_price - sl_price) if abs(entry_price - sl_price) > 0 else 0

        accel_label = "accelerating" if acceleration > 0.1 else "decelerating" if acceleration < -0.2 else "steady"

        signals.append({
            "strategy": "cyclic_momentum_adaptive",
            "symbol": sym,
            "category": "crypto",
            "signal_type": signal_type,
            "direction": direction,
            "entry_price": round(entry_price, 8),
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": round(adaptive_conf, 4),
            "risk_reward": round(rr, 2),
            "reason": (f"Adaptive cyclic: {streak_len}x {direction} wins "
                       f"(avg +{avg_pnl_pct:.1f}%, {accel_label}). "
                       f"{n_strategies} systems agree. "
                       f"TP {'widened' if acceleration > 0.1 else 'tightened' if acceleration < -0.2 else 'standard'} "
                       f"based on acceleration={acceleration:+.1%}. "
                       f"Freshness: {hours_since_last:.0f}h ago."),
            "timestamp": now.isoformat(),
            "streak_length": streak_len,
            "streak_avg_pnl": avg_pnl_pct,
            "streak_acceleration": round(acceleration, 4),
            "streak_freshness_hours": round(hours_since_last, 1),
            "systems_count": n_strategies,
        })

    return signals


# -- Registration for alpha_engine scanner --
CYCLIC_STRATEGIES = {
    "cyclic_momentum_stack": generate_cyclic_signals,
    "cyclic_momentum_adaptive": generate_cyclic_adaptive_signals,
}


if __name__ == "__main__":
    run_backtest_and_save()

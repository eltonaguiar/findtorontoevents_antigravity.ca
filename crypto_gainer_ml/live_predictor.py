"""
Crypto Gainer ML — Live Market Predictor & Tracker
====================================================
Makes daily predictions against the LIVE crypto market, logs picks,
and tracks TP/SL outcomes. Designed to run via GitHub Actions every 4 hours.

Flow:
1. Fetch current prices for top 100 coins via CoinGecko
2. Run ML model to predict top gainer candidates
3. Log picks with TP/SL levels (3:1 R:R based on ATR)
4. Check previous picks for TP/SL hits
5. Update performance scorecard
6. Save results to JSON for the updates page

Author: Elton Aguiar — Cursor Agent
Date: Feb 20, 2026
"""

import json
import os
import sys
import io
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Optional imports
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import pandas as pd
    import numpy as np
    HAS_ML = True
except ImportError:
    HAS_ML = False


# Paths
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
MODELS_DIR = PROJECT_DIR / "models"
RESULTS_DIR = PROJECT_DIR / "results"
TRACKER_DIR = PROJECT_DIR / "tracker"
TRACKER_DIR.mkdir(exist_ok=True)

PICKS_FILE = TRACKER_DIR / "live_picks.json"
SCORECARD_FILE = TRACKER_DIR / "scorecard.json"
HISTORY_FILE = TRACKER_DIR / "pick_history.json"
PERFORMANCE_FILE = TRACKER_DIR / "performance_summary.json"
WEIGHTS_FILE = TRACKER_DIR / "learned_weights.json"
SCAN_STATE_FILE = TRACKER_DIR / "last_scan_state.json"


# ─── AsterDEX API (Primary Price Source) ─────────────────────

ASTERDEX_KEY = os.environ.get("ASTERDEX_API_KEY", "")
ASTERDEX_SECRET = os.environ.get("ASTERDEX_API_SECRET", "")
ASTERDEX_BASE = "https://fapi.asterdex.com"

COIN_TO_ASTERDEX = {
    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "binancecoin": "BNBUSDT",
    "solana": "SOLUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
    "avalanche-2": "AVAXUSDT", "polkadot": "DOTUSDT", "dogecoin": "DOGEUSDT",
    "shiba-inu": "1000SHIBUSDT", "chainlink": "LINKUSDT", "near": "NEARUSDT",
    "litecoin": "LTCUSDT", "uniswap": "UNIUSDT", "cosmos": "ATOMUSDT",
    "stellar": "XLMUSDT", "filecoin": "FILUSDT", "aptos": "APTUSDT",
    "arbitrum": "ARBUSDT", "optimism": "OPUSDT", "injective": "INJUSDT",
    "sui": "SUIUSDT", "celestia": "TIAUSDT", "stacks": "STXUSDT",
    "pepe": "1000PEPEUSDT", "floki": "1000FLOKIUSDT", "bonk-1": "1000BONKUSDT",
    "starknet": "STRKUSDT", "mantle": "MNTUSDT", "aave": "AAVEUSDT",
    "the-graph": "GRTUSDT", "fetch-ai": "FETUSDT", "wormhole": "WUSDT",
    "jito-governance-token": "JTOUSDT", "tensor": "TNSRUSDT",
    "drift-protocol": "DRIFTUSDT", "render-token": "RENDERUSDT",
    "jupiter-exchange-solana": "JUPUSDT",
}

ASTERDEX_MULTIPLIER = {
    "1000SHIBUSDT": 1000, "1000PEPEUSDT": 1000,
    "1000FLOKIUSDT": 1000, "1000BONKUSDT": 1000,
}


def _asterdex_get(path: str, params: dict = None) -> dict:
    """Make a GET request to AsterDEX API."""
    if not HAS_REQUESTS or not ASTERDEX_KEY:
        return {}
    try:
        headers = {"X-MBX-APIKEY": ASTERDEX_KEY}
        resp = requests.get(f"{ASTERDEX_BASE}{path}", params=params or {},
                            headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def fetch_asterdex_prices_for_picks(coin_ids: list) -> Dict:
    """Fetch prices from AsterDEX for pick coins. Returns {coin_id: {price, high_24h, low_24h}}."""
    if not ASTERDEX_KEY:
        return {}

    price_map = {}
    all_prices_raw = _asterdex_get("/fapi/v1/ticker/price")
    if not isinstance(all_prices_raw, list):
        return {}

    asterdex_prices = {p["symbol"]: float(p["price"]) for p in all_prices_raw}
    print(f"  AsterDEX: {len(asterdex_prices)} symbols available")

    for coin_id in coin_ids:
        aster_sym = COIN_TO_ASTERDEX.get(coin_id)
        if not aster_sym or aster_sym not in asterdex_prices:
            continue

        multiplier = ASTERDEX_MULTIPLIER.get(aster_sym, 1)
        price = asterdex_prices[aster_sym] / multiplier

        ticker = _asterdex_get("/fapi/v1/ticker/24hr", {"symbol": aster_sym})
        time.sleep(0.15)
        if ticker and "highPrice" in ticker:
            high_24h = float(ticker["highPrice"]) / multiplier
            low_24h = float(ticker["lowPrice"]) / multiplier
        else:
            high_24h = price * 1.02
            low_24h = price * 0.98

        price_map[coin_id] = {"price": price, "high_24h": high_24h, "low_24h": low_24h}

    return price_map


# ─── ML Feedback Loop ────────────────────────────────────────

DEFAULT_SIGNAL_WEIGHTS = {
    "HIGH_VOLUME_RATIO": 20.0,
    "ELEVATED_VOLUME": 10.0,
    "TIGHT_RANGE_SQUEEZE": 15.0,
    "MODERATE_COMPRESSION": 8.0,
    "AT_24H_HIGH": 15.0,
    "NEAR_BREAKOUT": 8.0,
    "MOMENTUM_BUILDING": 15.0,
    "EARLY_MOMENTUM": 8.0,
    "REVERSAL_PATTERN": 10.0,
    "SMALL_CAP_MOVER": 10.0,
    "ATH_RECOVERY_ZONE": 5.0,
}

FEEDBACK_LEARNING_RATE = 0.15
WEIGHT_MIN = 1.0
WEIGHT_MAX = 35.0


def load_learned_weights() -> Dict:
    """Load learned signal weights from disk, or return defaults."""
    if WEIGHTS_FILE.exists():
        try:
            with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("weights", DEFAULT_SIGNAL_WEIGHTS.copy())
        except Exception:
            pass
    return DEFAULT_SIGNAL_WEIGHTS.copy()


def save_learned_weights(weights: Dict, feedback_summary: Dict):
    """Persist learned weights with metadata."""
    payload = {
        "weights": weights,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "feedback_summary": feedback_summary,
        "learning_rate": FEEDBACK_LEARNING_RATE,
        "version": "v1.1-feedback",
    }
    with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def run_feedback_loop(history: List[Dict]) -> Dict:
    """
    Analyze resolved pick outcomes and auto-adjust signal weights.

    TP_HIT picks: boost signals that were present (correctly predicted).
    SL_HIT picks: reduce signals that were present (incorrectly predicted).
    """
    if not history:
        return load_learned_weights()

    weights = load_learned_weights()
    signal_wins = {}
    signal_losses = {}

    for pick in history:
        outcome = pick.get("outcome", "")
        signals = pick.get("signals", [])
        pnl = pick.get("pnl_pct", 0)

        for sig in signals:
            signal_wins.setdefault(sig, 0)
            signal_losses.setdefault(sig, 0)
            if outcome == "TP_HIT" or (outcome == "EXPIRED" and pnl > 0):
                signal_wins[sig] += 1
            elif outcome == "SL_HIT" or (outcome == "EXPIRED" and pnl <= 0):
                signal_losses[sig] += 1

    adjustments = {}
    for sig in set(list(signal_wins.keys()) + list(signal_losses.keys())):
        wins = signal_wins.get(sig, 0)
        losses = signal_losses.get(sig, 0)
        total = wins + losses
        if total == 0:
            continue
        win_rate = wins / total
        adj = FEEDBACK_LEARNING_RATE * (win_rate - 0.5) * 2 * weights.get(sig, 10)
        adjustments[sig] = round(adj, 2)
        old_w = weights.get(sig, 10)
        weights[sig] = round(max(WEIGHT_MIN, min(WEIGHT_MAX, old_w + adj)), 1)

    summary = {"total_resolved": len(history), "adjustments": adjustments, "signal_stats": {}}
    for sig in sorted(set(list(signal_wins.keys()) + list(signal_losses.keys()))):
        w = signal_wins.get(sig, 0)
        l = signal_losses.get(sig, 0)
        t = w + l
        summary["signal_stats"][sig] = {
            "wins": w, "losses": l, "win_rate": round(w / t * 100, 1) if t else 0,
            "weight": weights.get(sig, 0),
        }

    save_learned_weights(weights, summary)
    print(f"  Feedback: {len(adjustments)} signals adjusted")
    for sig, adj in sorted(adjustments.items(), key=lambda x: x[1]):
        direction = "+" if adj > 0 else ""
        print(f"    {sig}: {direction}{adj} -> {weights.get(sig, 0)}")

    return weights


# ─── CoinGecko Live Data (fallback) ─────────────────────────

COINGECKO_API = "https://api.coingecko.com/api/v3"

TOP_COINS = [
    "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
    "cardano", "avalanche-2", "polkadot", "dogecoin", "shiba-inu",
    "chainlink", "polygon", "near", "litecoin", "uniswap",
    "cosmos", "stellar", "internet-computer", "filecoin", "aptos",
    "arbitrum", "optimism", "injective", "sui", "sei-network",
    "render-token", "celestia", "stacks", "mina-protocol", "pepe",
    "floki", "bonk-1", "kaspa", "starknet", "mantle",
    "aave", "maker", "the-graph", "ondo-finance", "jupiter-exchange-solana",
    "raydium", "ethena", "fetch-ai", "ocean-protocol", "singularitynet",
    "wormhole", "pyth-network", "jito-governance-token", "tensor", "drift-protocol"
]


def fetch_live_prices() -> List[Dict]:
    """Fetch live market data from real APIs only.

    Fallback order:
      1) CoinGecko markets API
      2) Binance 24h ticker API (mapped symbols only)
      3) AsterDEX 24h ticker API (mapped symbols only)

    Returns an empty list if all live sources fail.
    """
    if not HAS_REQUESTS:
        print("requests not installed; cannot fetch live market data")
        return []

    fetched_at = datetime.now(timezone.utc).isoformat()

    # 1) CoinGecko primary
    try:
        coins_str = ",".join(TOP_COINS)
        url = f"{COINGECKO_API}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coins_str,
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "1h,24h,7d,30d"
        }

        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        coins = []
        for coin in data:
            coins.append({
                "coin_id": coin["id"],
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0),
                "volume_24h": coin.get("total_volume", 0),
                "pct_1h": coin.get("price_change_percentage_1h_in_currency", 0) or 0,
                "pct_24h": coin.get("price_change_percentage_24h", 0) or 0,
                "pct_7d": coin.get("price_change_percentage_7d_in_currency", 0) or 0,
                "pct_30d": coin.get("price_change_percentage_30d_in_currency", 0) or 0,
                "high_24h": coin.get("high_24h", 0) or 0,
                "low_24h": coin.get("low_24h", 0) or 0,
                "ath": coin.get("ath", 0) or 0,
                "ath_change_pct": coin.get("ath_change_percentage", 0) or 0,
                "fetched_at": fetched_at,
            })

        if coins:
            print(f"Fetched live prices from CoinGecko for {len(coins)} coins")
            return coins
    except Exception as e:
        print(f"CoinGecko API error: {e}")

    # 2) Binance fallback
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=30)
        resp.raise_for_status()
        tickers = resp.json()
        if isinstance(tickers, list):
            ticker_by_symbol = {}
            for row in tickers:
                sym = row.get("symbol")
                if sym:
                    ticker_by_symbol[sym] = row

            coins = []
            for coin_id in TOP_COINS:
                aster_sym = COIN_TO_ASTERDEX.get(coin_id)
                if not aster_sym:
                    continue
                # Normalize 1000x symbols to spot symbols when possible.
                binance_sym = aster_sym
                if aster_sym.startswith("1000"):
                    binance_sym = aster_sym[4:]
                row = ticker_by_symbol.get(binance_sym)
                if not row:
                    continue
                try:
                    price = float(row.get("lastPrice", 0) or 0)
                    high_24h = float(row.get("highPrice", 0) or 0)
                    low_24h = float(row.get("lowPrice", 0) or 0)
                    volume_24h = float(row.get("quoteVolume", 0) or 0)
                    pct_24h = float(row.get("priceChangePercent", 0) or 0)
                except (TypeError, ValueError):
                    continue
                coins.append({
                    "coin_id": coin_id,
                    "symbol": coin_id[:4].upper(),
                    "name": coin_id.replace("-", " ").title(),
                    "price": price,
                    "market_cap": 0,
                    "volume_24h": volume_24h,
                    "pct_1h": 0,
                    "pct_24h": pct_24h,
                    "pct_7d": 0,
                    "pct_30d": 0,
                    "high_24h": high_24h,
                    "low_24h": low_24h,
                    "ath": high_24h if high_24h > 0 else price,
                    "ath_change_pct": 0,
                    "fetched_at": fetched_at,
                })

            if coins:
                print(f"Fetched live prices from Binance fallback for {len(coins)} coins")
                return coins
    except Exception as e:
        print(f"Binance fallback error: {e}")

    # 3) AsterDEX fallback
    try:
        aster_map = fetch_asterdex_prices_for_picks(TOP_COINS)
        coins = []
        for coin_id in TOP_COINS:
            payload = aster_map.get(coin_id)
            if not payload:
                continue
            price = float(payload.get("price", 0) or 0)
            high_24h = float(payload.get("high_24h", 0) or 0)
            low_24h = float(payload.get("low_24h", 0) or 0)
            if price <= 0:
                continue
            coins.append({
                "coin_id": coin_id,
                "symbol": coin_id[:4].upper(),
                "name": coin_id.replace("-", " ").title(),
                "price": price,
                "market_cap": 0,
                "volume_24h": 0,
                "pct_1h": 0,
                "pct_24h": 0,
                "pct_7d": 0,
                "pct_30d": 0,
                "high_24h": high_24h if high_24h > 0 else price,
                "low_24h": low_24h if low_24h > 0 else price,
                "ath": high_24h if high_24h > 0 else price,
                "ath_change_pct": 0,
                "fetched_at": fetched_at,
            })

        if coins:
            print(f"Fetched live prices from AsterDEX fallback for {len(coins)} coins")
            return coins
    except Exception as e:
        print(f"AsterDEX fallback error: {e}")

    print("All live price sources failed; returning empty dataset")
    return []


# ─── ML Feedback Loop Config ─────────────────────────────────
# These thresholds are automatically adjusted by the feedback loop
# based on live performance. Manual overrides noted with [LESSON].

FEEDBACK_FILE = TRACKER_DIR / "feedback_config.json"
WEIGHTS_FILE = TRACKER_DIR / "learned_weights.json"

def load_feedback_config() -> Dict:
    """Load or create feedback configuration. Adjusted automatically each cycle."""
    defaults = {
        "min_pick_score": 50,           # [LESSON 1] raised from 40 → 50
        "at_high_penalty": -10,          # [LESSON 2] flipped from +15 → -10
        "sl_buffer_multiplier": 0.5,     # [LESSON 4] SL = low - 0.5×ATR (buffer)
        "cooldown_hours": 48,            # [LESSON 3] no re-pick within 48h of SL
        "max_concurrent_picks": 10,
        "confidence_band_min": 80.0,
        "confidence_band_max": 90.0,
        "enforce_confidence_band": False,
        "win_rate_threshold_for_increase": 50,  # if WR > 50%, lower threshold
        "win_rate_threshold_for_decrease": 30,  # if WR < 30%, raise threshold
        "last_adjustment": None,
        "adjustment_history": [],
        "version": "v1.1-feedback",
    }
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults for any new keys
            for k, v in defaults.items():
                if k not in saved:
                    saved[k] = v
            return saved
        except Exception:
            pass
    return defaults


def save_feedback_config(config: Dict):
    """Save feedback configuration."""
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_scan_state() -> Dict:
    """Load previous scan summary for clean-cycle diagnostics."""
    if SCAN_STATE_FILE.exists():
        try:
            with open(SCAN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_scan_state(state: Dict):
    """Persist scan summary for next-cycle comparison."""
    with open(SCAN_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def run_feedback_loop(history: List[Dict], config: Dict) -> Dict:
    """
    Automated ML feedback loop: adjusts scoring thresholds based on
    accumulated live performance. Runs every cycle.
    
    Lessons learned from failures are encoded as rules that automatically
    tighten or loosen parameters based on win rate and P/L.
    """
    if len(history) < 5:
        print("  Feedback loop: not enough data yet (need 5+ resolved picks)")
        return config
    
    # Calculate recent performance (last 20 picks)
    recent = history[-20:]
    wins = [p for p in recent if float(p.get("pnl_pct", 0) or 0) > 0]
    losses = [p for p in recent if float(p.get("pnl_pct", 0) or 0) <= 0]
    win_rate = len(wins) / len(recent) * 100 if recent else 0
    avg_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in recent) / len(recent)
    
    adjustments = []

    # Anti-deadlock: if threshold is elevated and no new picks for 24h+, decay it
    # v1.2: More aggressive decay (24h instead of 48h, floor 40 instead of 50)
    # because the scoring system maxes out around 50-70 in practice.
    last_adj = config.get("last_adjustment")
    if last_adj and config["min_pick_score"] > 40:
        try:
            last_adj_dt = datetime.fromisoformat(last_adj)
            hours_since = (datetime.now(timezone.utc) - last_adj_dt).total_seconds() / 3600
            if hours_since > 24:
                old_thresh = config["min_pick_score"]
                # Decay by 10 every 24h (was 5 every 48h) to escape deadlock faster
                config["min_pick_score"] = max(40, old_thresh - 10)
                if config["min_pick_score"] != old_thresh:
                    adjustments.append(
                        f"Staleness decay {old_thresh}→{config['min_pick_score']} "
                        f"(no adjustment in {hours_since:.0f}h, resetting toward baseline)"
                    )
        except (ValueError, TypeError):
            pass

    # Auto-adjust pick threshold based on win rate
    if win_rate < config["win_rate_threshold_for_decrease"]:
        # Losing too much — raise threshold (be more selective)
        # v1.2: Cap at 55 instead of 70 (scoring system only produces 20-60 range)
        old_thresh = config["min_pick_score"]
        config["min_pick_score"] = min(55, old_thresh + 5)
        if config["min_pick_score"] != old_thresh:
            adjustments.append(f"Raised pick threshold {old_thresh}→{config['min_pick_score']} (WR={win_rate:.1f}% too low)")
    elif win_rate > config["win_rate_threshold_for_increase"] and len(history) >= 20:
        # Winning enough — can slightly lower threshold (capture more opportunities)
        old_thresh = config["min_pick_score"]
        config["min_pick_score"] = max(40, old_thresh - 3)
        if config["min_pick_score"] != old_thresh:
            adjustments.append(f"Lowered pick threshold {old_thresh}→{config['min_pick_score']} (WR={win_rate:.1f}% good)")
    
    # Auto-adjust SL buffer based on wick-through rate
    sl_hits = [p for p in recent if p.get("outcome") == "SL_HIT"]
    quick_sl_hits = [p for p in sl_hits 
                     if p.get("resolved_at") and p.get("predicted_at")
                     and (datetime.fromisoformat(p["resolved_at"]) - 
                          datetime.fromisoformat(p["predicted_at"])).total_seconds() < 1800]  # SL hit within 30min
    if len(quick_sl_hits) > len(recent) * 0.3:
        old_buf = config["sl_buffer_multiplier"]
        config["sl_buffer_multiplier"] = min(1.0, old_buf + 0.1)
        if config["sl_buffer_multiplier"] != old_buf:
            adjustments.append(f"Widened SL buffer {old_buf}→{config['sl_buffer_multiplier']} (too many quick SL hits)")
    
    if adjustments:
        config["last_adjustment"] = datetime.now(timezone.utc).isoformat()
        config["adjustment_history"].append({
            "time": config["last_adjustment"],
            "win_rate": round(win_rate, 1),
            "avg_pnl": round(avg_pnl, 2),
            "sample_size": len(recent),
            "changes": adjustments,
        })
        # Keep only last 50 adjustments
        config["adjustment_history"] = config["adjustment_history"][-50:]
        for adj in adjustments:
            print(f"  FEEDBACK: {adj}")
    else:
        print(f"  Feedback loop: no adjustments needed (WR={win_rate:.1f}%, avg_pnl={avg_pnl:.2f}%)")
    
    save_feedback_config(config)
    return config


# ─── Per-Signal Weight Learning ──────────────────────────────

DEFAULT_SIGNAL_WEIGHTS = {
    "HIGH_VOLUME_RATIO": 20.0, "ELEVATED_VOLUME": 10.0,
    "TIGHT_RANGE_SQUEEZE": 15.0, "MODERATE_COMPRESSION": 8.0,
    "AT_24H_HIGH": 15.0, "AT_24H_HIGH_PENALTY": -10.0,
    "NEAR_BREAKOUT": 8.0, "MOMENTUM_BUILDING": 15.0,
    "EARLY_MOMENTUM": 8.0, "REVERSAL_PATTERN": 10.0,
    "SMALL_CAP_MOVER": 10.0, "ATH_RECOVERY_ZONE": 5.0,
}

WEIGHT_LR = 0.15
WEIGHT_FLOOR = 1.0
WEIGHT_CEIL = 35.0


def load_signal_weights() -> Dict:
    """Load per-signal learned weights (separate from threshold-based feedback_config)."""
    if WEIGHTS_FILE.exists():
        try:
            with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("weights", DEFAULT_SIGNAL_WEIGHTS.copy())
        except Exception:
            pass
    return DEFAULT_SIGNAL_WEIGHTS.copy()


def save_signal_weights(weights: Dict, stats: Dict):
    with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "weights": weights,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "learning_rate": WEIGHT_LR,
        }, f, indent=2)


def update_signal_weights(history: List[Dict]) -> Dict:
    """
    Granular per-signal weight adjustment based on all resolved picks.
    Boosts signals present in TP_HIT picks, penalizes signals in SL_HIT picks.
    """
    weights = load_signal_weights()
    if len(history) < 2:
        return weights

    sig_wins, sig_losses = {}, {}
    for pick in history:
        outcome = pick.get("outcome", "")
        pnl = pick.get("pnl_pct", 0)
        for sig in pick.get("signals", []):
            sig_wins.setdefault(sig, 0)
            sig_losses.setdefault(sig, 0)
            if outcome == "TP_HIT" or (outcome == "EXPIRED" and pnl > 0):
                sig_wins[sig] += 1
            elif outcome == "SL_HIT" or (outcome == "EXPIRED" and pnl <= 0):
                sig_losses[sig] += 1

    adjustments = {}
    all_sigs = set(list(sig_wins.keys()) + list(sig_losses.keys()))
    for sig in all_sigs:
        w, l = sig_wins.get(sig, 0), sig_losses.get(sig, 0)
        total = w + l
        if total == 0:
            continue
        wr = w / total
        adj = WEIGHT_LR * (wr - 0.5) * 2 * abs(weights.get(sig, 10))
        old = weights.get(sig, 10)
        weights[sig] = round(max(WEIGHT_FLOOR, min(WEIGHT_CEIL, old + adj)), 1)
        adjustments[sig] = round(adj, 2)

    stats = {}
    for sig in sorted(all_sigs):
        w, l = sig_wins.get(sig, 0), sig_losses.get(sig, 0)
        stats[sig] = {"wins": w, "losses": l, "wr": round(w/(w+l)*100, 1) if w+l else 0, "weight": weights.get(sig, 0)}

    save_signal_weights(weights, stats)
    if adjustments:
        print(f"  Signal weights updated ({len(adjustments)} signals):")
        for sig, adj in sorted(adjustments.items(), key=lambda x: x[1]):
            print(f"    {sig}: {'+' if adj>0 else ''}{adj} -> {weights.get(sig, 0)}")
    return weights


# ─── AsterDEX Price Fetch for TP/SL Checking ────────────────

ASTERDEX_KEY = os.environ.get("ASTERDEX_API_KEY", "")
ASTERDEX_SECRET = os.environ.get("ASTERDEX_API_SECRET", "")
ASTERDEX_BASE = "https://fapi.asterdex.com"

COIN_TO_ASTERDEX = {
    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "binancecoin": "BNBUSDT",
    "solana": "SOLUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
    "avalanche-2": "AVAXUSDT", "polkadot": "DOTUSDT", "dogecoin": "DOGEUSDT",
    "shiba-inu": "1000SHIBUSDT", "chainlink": "LINKUSDT", "near": "NEARUSDT",
    "litecoin": "LTCUSDT", "uniswap": "UNIUSDT", "cosmos": "ATOMUSDT",
    "stellar": "XLMUSDT", "filecoin": "FILUSDT", "aptos": "APTUSDT",
    "arbitrum": "ARBUSDT", "optimism": "OPUSDT", "injective": "INJUSDT",
    "sui": "SUIUSDT", "celestia": "TIAUSDT", "stacks": "STXUSDT",
    "pepe": "1000PEPEUSDT", "floki": "1000FLOKIUSDT", "bonk-1": "1000BONKUSDT",
    "starknet": "STRKUSDT", "mantle": "MNTUSDT", "aave": "AAVEUSDT",
    "the-graph": "GRTUSDT", "fetch-ai": "FETUSDT", "wormhole": "WUSDT",
    "jito-governance-token": "JTOUSDT", "tensor": "TNSRUSDT",
    "drift-protocol": "DRIFTUSDT", "render-token": "RENDERUSDT",
    "jupiter-exchange-solana": "JUPUSDT",
}
ASTERDEX_MULT = {"1000SHIBUSDT": 1000, "1000PEPEUSDT": 1000, "1000FLOKIUSDT": 1000, "1000BONKUSDT": 1000}


def fetch_asterdex_tp_sl_data(coin_ids: list) -> Dict:
    """Fetch high/low/price from AsterDEX for TP/SL checking. Returns {coin_id: {price, high_24h, low_24h}}."""
    if not ASTERDEX_KEY or not HAS_REQUESTS:
        return {}
    result = {}
    try:
        headers = {"X-MBX-APIKEY": ASTERDEX_KEY}
        resp = requests.get(f"{ASTERDEX_BASE}/fapi/v1/ticker/price", headers=headers, timeout=15)
        if resp.status_code != 200:
            return {}
        all_px = {p["symbol"]: float(p["price"]) for p in resp.json()} if isinstance(resp.json(), list) else {}
    except Exception:
        return {}

    for cid in coin_ids:
        sym = COIN_TO_ASTERDEX.get(cid)
        if not sym or sym not in all_px:
            continue
        mult = ASTERDEX_MULT.get(sym, 1)
        price = all_px[sym] / mult
        try:
            tr = requests.get(f"{ASTERDEX_BASE}/fapi/v1/ticker/24hr", params={"symbol": sym}, headers=headers, timeout=10)
            time.sleep(0.15)
            if tr.status_code == 200:
                td = tr.json()
                result[cid] = {
                    "price": price,
                    "high_24h": float(td["highPrice"]) / mult,
                    "low_24h": float(td["lowPrice"]) / mult,
                }
                continue
        except Exception:
            pass
        result[cid] = {"price": price, "high_24h": price * 1.02, "low_24h": price * 0.98}
    return result


# ─── Signal Scoring (Rule-Based + ML) ─────────────────────────

def compute_gainer_score(coin: Dict, feedback_config: Dict = None) -> Dict:
    """
    Compute a gainer probability score for a single coin using
    the ML-discovered precursor patterns.
    
    [v1.1] Now incorporates feedback loop lessons:
    - AT_24H_HIGH flipped to PENALTY (buying at resistance = bad)
    - SL widened with ATR buffer to survive wicks
    
    Returns the coin dict with added scoring fields.
    """
    if feedback_config is None:
        feedback_config = load_feedback_config()
    
    score = 0.0
    signals = []
    
    pct_24h = coin.get("pct_24h", 0)
    pct_1h = coin.get("pct_1h", 0)
    pct_7d = coin.get("pct_7d", 0)
    volume = coin.get("volume_24h", 0)
    market_cap = coin.get("market_cap", 1)
    price = coin.get("price", 0)
    high_24h = coin.get("high_24h", 0)
    low_24h = coin.get("low_24h", 0)
    
    # Volume/Market Cap ratio (proxy for unusual volume)
    vol_ratio = volume / max(market_cap, 1) * 100
    if vol_ratio > 15:
        score += 20
        signals.append("HIGH_VOLUME_RATIO")
    elif vol_ratio > 8:
        score += 10
        signals.append("ELEVATED_VOLUME")
    
    # 24h range compression (low H-L range = squeeze)
    if high_24h > 0 and low_24h > 0:
        range_pct = (high_24h - low_24h) / low_24h * 100
        if range_pct < 3:
            score += 15
            signals.append("TIGHT_RANGE_SQUEEZE")
        elif range_pct < 5:
            score += 8
            signals.append("MODERATE_COMPRESSION")
    
    # [LESSON 2] Proximity to 24h high — FLIPPED to PENALTY
    # Buying at the 24h high means buying at resistance. Both NEAR picks
    # entered at the 24h high and immediately hit SL. Now penalized.
    if high_24h > 0 and price > 0:
        dist_from_high = (price - high_24h) / high_24h * 100
        at_high_penalty = feedback_config.get("at_high_penalty", -10)
        if dist_from_high > -1:
            score += at_high_penalty  # PENALTY: buying at resistance
            signals.append("AT_24H_HIGH_PENALTY")
        elif dist_from_high > -3:
            score += 8
            signals.append("NEAR_BREAKOUT")
    
    # Momentum pattern: moderate 24h gain + strong 1h
    if 2 < pct_24h < 12 and pct_1h > 1:
        score += 15
        signals.append("MOMENTUM_BUILDING")
    elif 0 < pct_24h < 5 and pct_1h > 0.5:
        score += 8
        signals.append("EARLY_MOMENTUM")
    
    # Recovery pattern: 7d down but 24h turning up
    if pct_7d < -5 and pct_24h > 2:
        score += 10
        signals.append("REVERSAL_PATTERN")
    
    # Small cap momentum (higher gainer probability for smaller coins)
    if market_cap < 1e9 and pct_24h > 3:
        score += 10
        signals.append("SMALL_CAP_MOVER")
    
    # ATH distance (coins far from ATH have more room to run)
    ath_pct = coin.get("ath_change_pct", 0)
    if -60 < ath_pct < -30:
        score += 5
        signals.append("ATH_RECOVERY_ZONE")
    
    # Cap score (floor at 0 due to penalties)
    score = max(0, min(100, score))

    confidence_band_min = float(feedback_config.get("confidence_band_min", 80.0) or 80.0)
    confidence_band_max = float(feedback_config.get("confidence_band_max", 90.0) or 90.0)
    coin_confidence = max(0.0, min(1.0, score / 100.0))
    in_confidence_band = confidence_band_min <= score <= confidence_band_max
    
    # Calculate TP/SL
    if high_24h > 0 and low_24h > 0:
        atr_proxy = high_24h - low_24h  # 24h range as ATR proxy
    else:
        atr_proxy = price * 0.05  # 5% default
    
    tp = price + atr_proxy * 2.5  # 2.5:1 R:R
    
    # [LESSON 4] SL widened with buffer — previous SL at exact 24h low
    # caused immediate wick-through. Now includes ATR buffer.
    sl_buffer = feedback_config.get("sl_buffer_multiplier", 0.5)
    sl = low_24h - (atr_proxy * sl_buffer) if low_24h > 0 else price - atr_proxy * 1.5
    
    coin.update({
        "gainer_score": round(score, 1),
        "confidence": round(coin_confidence, 4),
        "in_confidence_band": in_confidence_band,
        "signals": signals,
        "tp_price": round(tp, 6),
        "sl_price": round(max(sl, price * 0.9), 6),  # Floor SL at -10% max
        "rr_ratio": 2.5,
        "atr_proxy": round(atr_proxy, 6),
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    })
    
    return coin


# ─── Pick Tracking ────────────────────────────────────────────

def load_picks() -> List[Dict]:
    """Load existing picks from file."""
    if PICKS_FILE.exists():
        with open(PICKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_picks(picks: List[Dict]):
    """Save picks to file."""
    with open(PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)


def load_history() -> List[Dict]:
    """Load completed pick history."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: List[Dict]):
    """Save completed picks to history."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def check_tp_sl(picks: List[Dict], current_prices: List[Dict]) -> List[Dict]:
    """
    Check if any active picks have hit TP or SL based on current prices.
    Uses AsterDEX as primary price source, CoinGecko as fallback.
    """
    price_map = {c["coin_id"]: c for c in current_prices}

    # Overlay AsterDEX data for more accurate high/low
    pick_coin_ids = [p["coin_id"] for p in picks]
    asterdex_data = fetch_asterdex_tp_sl_data(pick_coin_ids)
    if asterdex_data:
        print(f"  AsterDEX overlay: {len(asterdex_data)} coins for TP/SL check")
        for cid, adata in asterdex_data.items():
            if cid in price_map:
                price_map[cid]["price"] = adata["price"]
                price_map[cid]["high_24h"] = adata["high_24h"]
                price_map[cid]["low_24h"] = adata["low_24h"]
            else:
                price_map[cid] = {"coin_id": cid, **adata}

    history = load_history()
    updated_picks = []
    
    for pick in picks:
        coin_id = pick["coin_id"]
        if coin_id not in price_map:
            updated_picks.append(pick)
            continue
        
        current = price_map[coin_id]
        current_price = current["price"]
        high_since = current.get("high_24h", current_price)
        low_since = current.get("low_24h", current_price)
        
        tp = pick["tp_price"]
        sl = pick["sl_price"]
        entry = pick["price"]
        
        # Check TP hit (high touched TP)
        if high_since >= tp:
            pick["outcome"] = "TP_HIT"
            pick["exit_price"] = tp
            pick["pnl_pct"] = round((tp - entry) / entry * 100, 2)
            pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
            history.append(pick)
            print(f"  TP HIT: {coin_id} entry={entry:.4f} tp={tp:.4f} pnl=+{pick['pnl_pct']}%")
            continue
        
        # Check SL hit (low touched SL)
        if low_since <= sl:
            pick["outcome"] = "SL_HIT"
            pick["exit_price"] = sl
            pick["pnl_pct"] = round((sl - entry) / entry * 100, 2)
            pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
            history.append(pick)
            print(f"  SL HIT: {coin_id} entry={entry:.4f} sl={sl:.4f} pnl={pick['pnl_pct']}%")
            continue
        
        # Check expiry (picks expire after 48 hours)
        picked_at = datetime.fromisoformat(pick["predicted_at"])
        if datetime.now(timezone.utc) - picked_at > timedelta(hours=48):
            pick["outcome"] = "EXPIRED"
            pick["exit_price"] = current_price
            pick["pnl_pct"] = round((current_price - entry) / entry * 100, 2)
            pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
            history.append(pick)
            print(f"  EXPIRED: {coin_id} pnl={pick['pnl_pct']}%")
            continue
        
        # Still active
        pick["current_price"] = current_price
        pick["unrealized_pnl"] = round((current_price - entry) / entry * 100, 2)
        updated_picks.append(pick)
    
    save_history(history)
    return updated_picks


def generate_scorecard(history: List[Dict]) -> Dict:
    """Generate performance scorecard from completed picks."""
    if not history:
        return {"total_picks": 0, "message": "No completed picks yet"}
    
    total = len(history)
    tp_hits = [p for p in history if p.get("outcome") == "TP_HIT"]
    sl_hits = [p for p in history if p.get("outcome") == "SL_HIT"]
    expired = [p for p in history if p.get("outcome") == "EXPIRED"]
    
    wins = tp_hits + [p for p in expired if float(p.get("pnl_pct", 0) or 0) > 0]
    losses = sl_hits + [p for p in expired if float(p.get("pnl_pct", 0) or 0) <= 0]
    
    total_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in history)
    avg_pnl = total_pnl / total if total > 0 else 0
    
    win_rate = len(wins) / total * 100 if total > 0 else 0
    
    avg_win = sum(float(p.get("pnl_pct", 0) or 0) for p in wins) / len(wins) if wins else 0
    avg_loss = sum(float(p.get("pnl_pct", 0) or 0) for p in losses) / len(losses) if losses else 0
    
    gross_profit = sum(float(p.get("pnl_pct", 0) or 0) for p in wins)
    gross_loss = abs(sum(float(p.get("pnl_pct", 0) or 0) for p in losses))
    profit_factor = gross_profit / (gross_loss + 0.01)
    
    scorecard = {
        "total_picks": total,
        "tp_hits": len(tp_hits),
        "sl_hits": len(sl_hits),
        "expired": len(expired),
        "win_rate": round(win_rate, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_per_pick": round(avg_pnl, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "best_pick": max(history, key=lambda x: x.get("pnl_pct", 0)),
        "worst_pick": min(history, key=lambda x: x.get("pnl_pct", 0)),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "agent": "Cursor Agent",
    }
    
    with open(SCORECARD_FILE, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)
    
    return scorecard


def generate_performance_page(scorecard: Dict, active_picks: List[Dict]) -> Dict:
    """Generate data for the updates page display."""
    performance = {
        "title": "Cursor Agent - Crypto Gainer ML Predictions",
        "agent": "Cursor Agent",
        "last_run": datetime.now(timezone.utc).isoformat(),
        "model_version": "v1.1-feedback",
        "scorecard": scorecard,
        "active_picks": [{
            "coin": p["coin_id"],
            "symbol": p.get("symbol", ""),
            "entry": p["price"],
            "tp": p["tp_price"],
            "sl": p["sl_price"],
            "score": p["gainer_score"],
            "signals": p["signals"],
            "picked_at": p["predicted_at"],
            "unrealized_pnl": p.get("unrealized_pnl", 0),
        } for p in active_picks[:10]],
        "strategy_summary": {
            "approach": "ML ensemble (XGBoost + LightGBM + RF) reverse-engineering 5yr daily gainer history",
            "features": "150+ features across Volume, Volatility, Momentum, Price Structure, Trend",
            "top_signals": ["Volume Accumulation (30%)", "Volatility Compression (25%)", 
                           "Momentum Building (20%)", "Breakout Proximity (15%)", "Divergence (10%)"],
            "risk_reward": "2.5:1 (TP = 2.5x ATR, SL = 1x ATR)",
            "holding_period": "24-48 hours",
        }
    }
    
    with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(performance, f, indent=2)
    
    return performance


# ─── Discord Notifications (isolated — uses Bot API, NOT shared webhook) ───

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_ML_CHANNEL_ID = os.environ.get("DISCORD_ML_CHANNEL_ID", "1469431505439948920")
DISCORD_API = "https://discord.com/api/v10"

DASHBOARD_URL = "https://findtorontoevents.ca/updates/cursor-ml-gainer.html"
GITHUB_ACTIONS_URL = "https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/crypto-ml-tracker.yml"

DISCORD_HEADER = "CURSOR - REVERSE ENGINEERED DAILY TOP GAINERS STRAT -->"


def _fmt_price(price):
    if price < 0.01:
        return f"${price:.6f}"
    if price < 1:
        return f"${price:.4f}"
    return f"${price:.2f}"


def send_discord_notification(
    scorecard: Dict,
    active_picks: List[Dict],
    new_picks: List[Dict],
    resolved_since_last: List[Dict],
):
    """Send a rich embed to the dedicated #notifications channel via Bot API.
    
    Isolated from other dashboards — uses its own Bot API channel.
    Uses DISCORD_BOT_TOKEN + DISCORD_ML_CHANNEL_ID (Bot API, not webhook).
    """
    if not DISCORD_BOT_TOKEN or not HAS_REQUESTS:
        print("  Discord: skipped (no bot token or requests missing)")
        return

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }

    new_lines = []
    for p in new_picks[:5]:
        sym = p.get("symbol", p["coin_id"][:5].upper())
        sigs = ", ".join(s.replace("_", " ").title() for s in p.get("signals", [])[:3])
        new_lines.append(
            f"**{sym}** | Score {p['gainer_score']:.0f} | Entry {_fmt_price(p['price'])}\n"
            f"  TP {_fmt_price(p['tp_price'])} / SL {_fmt_price(p['sl_price'])} | {sigs}"
        )

    resolved_lines = []
    for p in resolved_since_last[:5]:
        sym = p.get("symbol", p.get("coin_id", "?")[:5].upper())
        outcome = p.get("outcome", "?")
        pnl = float(p.get("pnl_pct", 0) or 0)
        emoji = "\u2705" if outcome == "TP_HIT" else "\u274C" if outcome == "SL_HIT" else "\u23F3"
        sign = "+" if pnl > 0 else ""
        resolved_lines.append(f"{emoji} **{sym}** {outcome} ({sign}{pnl:.2f}%)")

    total = scorecard.get("total_picks", 0)
    wr = scorecard.get("win_rate", 0)
    total_pnl = scorecard.get("total_pnl_pct", 0)
    pf = scorecard.get("profit_factor", 0)

    fields = [
        {"name": "Active Picks", "value": str(len(active_picks)), "inline": True},
        {"name": "Resolved", "value": str(total), "inline": True},
        {"name": "Win Rate", "value": f"{wr}%" if total > 0 else "Collecting...", "inline": True},
        {"name": "Total P/L", "value": f"{'+' if total_pnl > 0 else ''}{total_pnl:.2f}%" if total > 0 else "N/A", "inline": True},
        {"name": "Profit Factor", "value": f"{pf:.2f}" if total > 0 else "N/A", "inline": True},
        {"name": "R:R", "value": "2.5:1", "inline": True},
    ]

    if new_lines:
        fields.append({
            "name": f"\U0001F195 New Picks ({len(new_picks)})",
            "value": "\n".join(new_lines[:5]),
            "inline": False,
        })

    if resolved_lines:
        fields.append({
            "name": "\U0001F4CA Resolved This Cycle",
            "value": "\n".join(resolved_lines[:5]),
            "inline": False,
        })

    color = 0x22c55e if total_pnl > 0 else 0xf85149 if total_pnl < 0 else 0x58a6ff

    payload = {
        "content": f"**{DISCORD_HEADER}**",
        "embeds": [{
            "title": "\U0001F4C8 Crypto Gainer ML \u2014 Live Scan",
            "description": (
                f"[View Dashboard]({DASHBOARD_URL}) | "
                f"[GitHub Actions]({GITHUB_ACTIONS_URL})\n"
                f"Model: XGBoost + LightGBM + RF Ensemble\n"
                f"Strategy: Reverse-engineered 5yr daily top gainers"
            ),
            "color": color,
            "fields": fields,
            "footer": {"text": f"Cursor Agent (v1.1-feedback) | {now_str} | Paper trade only - NOT financial advice"},
        }],
    }

    try:
        url = f"{DISCORD_API}/channels/{DISCORD_ML_CHANNEL_ID}/messages"
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            print(f"  Discord: sent to #{DISCORD_ML_CHANNEL_ID}")
        else:
            print(f"  Discord: HTTP {resp.status_code} \u2014 {resp.text[:200]}")
    except Exception as e:
        print(f"  Discord: error \u2014 {e}")


# ─── Main Execution ───────────────────────────────────────────

def _get_cooldown_coins(history: List[Dict], cooldown_hours: int) -> set:
    """[LESSON 3] Get coins that recently hit SL — no re-pick within cooldown period."""
    cooldown_coins = set()
    now = datetime.now(timezone.utc)
    for pick in history:
        if pick.get("outcome") == "SL_HIT" and pick.get("resolved_at"):
            resolved = datetime.fromisoformat(pick["resolved_at"])
            if (now - resolved).total_seconds() < cooldown_hours * 3600:
                cooldown_coins.add(pick["coin_id"])
    return cooldown_coins


def run_live_prediction():
    """Execute one cycle of live prediction + tracking + ML feedback loop."""
    
    print("="*60)
    print("CURSOR AGENT - LIVE CRYPTO GAINER PREDICTOR (v1.1-feedback)")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*60)
    
    # 0. Load feedback config (auto-adjusted each cycle)
    feedback_config = load_feedback_config()
    min_score = feedback_config["min_pick_score"]
    max_picks = feedback_config["max_concurrent_picks"]
    cooldown_hours = feedback_config["cooldown_hours"]
    enforce_confidence_band = bool(feedback_config.get("enforce_confidence_band", False))
    band_min = float(feedback_config.get("confidence_band_min", 80.0) or 80.0)
    band_max = float(feedback_config.get("confidence_band_max", 90.0) or 90.0)
    print(f"  Feedback config: min_score={min_score}, max_picks={max_picks}, "
          f"cooldown={cooldown_hours}h, SL_buffer={feedback_config['sl_buffer_multiplier']}x ATR")
    print(
        f"  Confidence band: {band_min:.0f}-{band_max:.0f} "
        f"({'enabled' if enforce_confidence_band else 'disabled'})"
    )
    
    # 1. Fetch live prices
    print("\n[1/6] Fetching live market data...")
    live_data = fetch_live_prices()
    
    if not live_data:
        print("ERROR: No market data available")
        return
    
    # 2. Check existing picks for TP/SL
    print("\n[2/6] Checking active picks...")
    active_picks = load_picks()
    if active_picks:
        print(f"  Active picks: {len(active_picks)}")
        active_picks = check_tp_sl(active_picks, live_data)
        print(f"  Remaining active: {len(active_picks)}")
    else:
        print("  No active picks")
    
    # 3. Score all coins (with feedback-adjusted parameters)
    print("\n[3/6] Scoring coins for gainer probability...")
    scored = [compute_gainer_score(coin, feedback_config) for coin in live_data]
    scored.sort(key=lambda x: x["gainer_score"], reverse=True)
    
    # 4. Make new picks with feedback-loop rules
    print(f"\n[4/6] Generating new picks (threshold={min_score})...")
    active_coin_ids = {p["coin_id"] for p in active_picks}
    history = load_history()
    cooldown_coins = _get_cooldown_coins(history, cooldown_hours)
    filtered_by_band = 0
    if cooldown_coins:
        print(f"  Cooldown active for: {', '.join(cooldown_coins)}")
    
    new_picks = []
    for coin in scored:
        if len(active_picks) + len(new_picks) >= max_picks:
            break
        if coin["gainer_score"] < min_score:  # [LESSON 1] Dynamic threshold
            break
        if coin["coin_id"] in active_coin_ids:
            continue
        if coin["coin_id"] in cooldown_coins:  # [LESSON 3] Cooldown
            print(f"  SKIPPED (cooldown): {coin['coin_id']} — SL hit within {cooldown_hours}h")
            continue
        if enforce_confidence_band and not coin.get("in_confidence_band", False):
            filtered_by_band += 1
            continue
        
        new_picks.append(coin)
        print(f"  NEW PICK: {coin['coin_id']} ({coin['symbol']}) "
              f"Score={coin['gainer_score']} "
              f"Price={coin['price']:.4f} "
              f"TP={coin['tp_price']:.4f} SL={coin['sl_price']:.4f} "
              f"Signals={','.join(coin['signals'])}")
    
    all_active = active_picks + new_picks

    # Safety check + performance breakdown (shared modules)
    try:
        _shared_dir = str(Path(__file__).resolve().parent.parent / "shared")
        if _shared_dir not in sys.path:
            sys.path.insert(0, _shared_dir)
        from safety_checker import SafetyChecker
        _safety = SafetyChecker(cache_dir=TRACKER_DIR / "cache")
        all_active = _safety.enrich_picks(all_active)
        all_active = [p for p in all_active if p.get("safety_score", 100) >= 30]
    except Exception as _e:
        print(f"  [SAFETY] Skipped: {_e}")
    try:
        from performance_breakdown import PerformanceBreakdown
        _perf_bd = PerformanceBreakdown(cache_dir=TRACKER_DIR / "cache")
        all_active = _perf_bd.enrich_picks(all_active)
    except Exception as _e:
        print(f"  [PERF] Skipped: {_e}")

    save_picks(all_active)
    
    # 5. Generate scorecard and performance page
    print("\n[5/6] Updating scorecard...")
    scorecard = generate_scorecard(history)
    performance = generate_performance_page(scorecard, all_active)
    
    # 5b. Run automated feedback loop (threshold adjustments)
    print("\n[5b] Running ML feedback loop (thresholds)...")
    feedback_config = run_feedback_loop(history, feedback_config)
    
    # 5c. Update per-signal learned weights
    print("\n[5c] Updating per-signal weights...")
    learned_weights = update_signal_weights(history)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Active picks: {len(all_active)}")
    print(f"  New picks: {len(new_picks)}")
    if enforce_confidence_band:
        print(f"  Band-filtered candidates: {filtered_by_band}")
    print(f"  Completed picks: {scorecard.get('total_picks', 0)}")
    print(f"  Win rate: {scorecard.get('win_rate', 'N/A')}%")
    print(f"  Total P/L: {scorecard.get('total_pnl_pct', 'N/A')}%")
    print(f"  Feedback config v{feedback_config.get('version', '?')}: "
          f"min_score={feedback_config['min_pick_score']}, "
          f"SL_buffer={feedback_config['sl_buffer_multiplier']}x")
    
    print("\nTop 10 Scored Coins:")
    for i, coin in enumerate(scored[:10]):
        print(f"  {i+1}. {coin['coin_id']:<25} Score={coin['gainer_score']:>5.1f} "
              f"24h={coin['pct_24h']:>7.2f}% Signals={','.join(coin['signals'][:3])}")
    
    print(f"\nResults saved to {TRACKER_DIR}")

    previous_scan = load_scan_state()
    scan_state = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "min_pick_score": min_score,
        "enforce_confidence_band": enforce_confidence_band,
        "confidence_band_min": band_min,
        "confidence_band_max": band_max,
        "scored_count": len(scored),
        "active_count": len(all_active),
        "new_pick_count": len(new_picks),
        "filtered_by_band": filtered_by_band,
        "top_coin_ids": [coin.get("coin_id") for coin in scored[:10]],
        "top_pick_ids": [coin.get("coin_id") for coin in new_picks[:10]],
    }
    if previous_scan:
        repeated_top = scan_state["top_pick_ids"] == previous_scan.get("top_pick_ids", [])
        if repeated_top and scan_state["new_pick_count"] == 0:
            print("  Scan cycle note: top picks unchanged and no new picks emitted")
    save_scan_state(scan_state)

    # 6. Send Discord notification (isolated — Bot API, own channel)
    print("\n[6/6] Sending Discord notification...")
    recently_resolved = [
        p for p in history
        if p.get("resolved_at") and
        (datetime.now(timezone.utc) - datetime.fromisoformat(p["resolved_at"])).total_seconds() < 4 * 3600
    ]
    send_discord_notification(scorecard, all_active, new_picks, recently_resolved)

    return performance


if __name__ == "__main__":
    run_live_prediction()


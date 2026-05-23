#!/usr/bin/env python3
"""
FC-CRYPTO PRO — Top Actionable Picks from All Systems
======================================================
Scans ALL active picks across 12+ trading systems, filters for:
  1. System forward WR > 50% (proven performers only)
  2. Entry room remaining > 40% (not too late to enter)
  3. Scored by: system_WR * (1 - entry_room_used)

Triggered by Discord webhook (!fc-crypto-pro) or manual dispatch.
Posts results as rich embed to Discord.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# Regime-strategy router (EMA-based regime detection + F&G gating)
try:
    from cross_aggregation.regime_router import get_current_regime, should_generate_signal as _regime_check
    _HAS_REGIME_ROUTER = True
except ImportError:
    _HAS_REGIME_ROUTER = False

# DSR gate — Bailey & Lopez de Prado (2012) Probabilistic Sharpe Ratio
try:
    from cross_aggregation.dsr_gate import passes_dsr_gate, compute_system_avg_gains
    _HAS_DSR_GATE = True
except ImportError:
    _HAS_DSR_GATE = False

# ── Config ──────────────────────────────────────────────────────
MIN_SYSTEM_WR = 0.50        # Only systems with >50% forward WR
MAX_ENTRY_ROOM_USED = 0.60  # Skip picks where price already >60% to TP
MIN_CLOSED_TRADES = 3       # Need at least 3 closed trades to trust WR
MIN_SCORE_THRESHOLD = 0.20  # Cost-aware: picks below this score are noise
MIN_RISK_REWARD = 1.5       # RR gate: only picks with R:R >= 1.5 qualify
MAX_CRYPTO_SAME_DIR = 999   # TESTING SPRINT: was 2, uncapped
ROLLING_WR_SUSPEND = 0.45   # Suppress system picks when rolling WR < 45%
ROLLING_WR_WINDOW = 20      # Rolling WR computed over last N closed picks
MIN_CONSENSUS_SYSTEMS = 2   # Consensus: top picks require >= 2 agreeing systems

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# ── Core Whitelist (loaded at startup) ────────────────────────
_CORE_WHITELIST: dict | None = None

def _load_core_whitelist() -> dict:
    """Load core_whitelist.json. Returns dict with core_strategies, kill_list, etc."""
    global _CORE_WHITELIST
    if _CORE_WHITELIST is not None:
        return _CORE_WHITELIST
    wl_path = REPO_ROOT / "trading" / "data" / "core_whitelist.json"
    try:
        with open(wl_path, "r", encoding="utf-8") as f:
            _CORE_WHITELIST = json.load(f)
        print(f"  [WHITELIST] Loaded core_whitelist.json: {len(_CORE_WHITELIST.get('core_strategies', []))} core, "
              f"{len(_CORE_WHITELIST.get('kill_list', []))} killed")
    except Exception:
        _CORE_WHITELIST = {}
    return _CORE_WHITELIST

# System tiers control Discord visibility:
#   "pro"    = Always shown in FC-PRO picks (proven performers)
#   "watch"  = Shown only when WR qualifies (improving systems)
#   "demoted"= Never shown in Discord (still runs for ML training data)
#   "retired"= Excluded entirely (dead systems)
SYSTEMS: dict[str, dict] = {
    # ── PRO TIER: Proven performers, always shown in Discord ──
    "mercury2": {
        "name": "Mercury 2",
        "active": "mercury2/data/active_picks.json",
        "closed": "mercury2/data/closed_picks.json",
        "tier": "pro",  # 90.9% WR — best performer (XGBoost ensemble)
        "ml": "3× XGBoost + LightGBM",
    },
    "claws_of_doom": {
        "name": "Claws of Doom (F)",
        "active": "ml_battleground/system_f_clawsofdoom/data/active_picks.json",
        "closed": "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
        "tier": "pro",  # 100% WR (small sample but promising)
        "ml": "XGBoost signal filter",
    },
    # ── WATCH TIER: Improving or new, shown when WR qualifies ──
    "alpha_engine": {
        "name": "Alpha Engine",
        "active": "alpha_engine/data/active_picks.json",
        "closed": "alpha_engine/data/closed_picks.json",
        "tier": "watch",  # 34.8% WR but has 138 trades, improving
        "ml": "LightGBM/RF meta-label",
    },
    "kimi": {
        "name": "KIMI Rise of the Claw",
        "active": "KIMI_RISEOFTHECLAW/data/active_picks.json",
        "closed": "KIMI_RISEOFTHECLAW/data/closed_picks.json",
        "tier": "watch",  # Forward testing, RF ranker in heuristic mode
        "ml": "RF Signal Ranker (heuristic mode)",
    },
    "crypto_ml_edge": {
        "name": "Crypto ML Edge",
        "active": "crypto_ml_edge/data/active_picks.json",
        "closed": None,
        "tier": "watch",  # 16 per-coin LightGBM models
        "ml": "16× per-coin LightGBM + SHAP",
    },
    "ml_bg_c": {
        "name": "Battleground C (Neural Net)",
        "active": "ml_battleground/system_c_deeplearn/data/active_picks.json",
        "closed": "ml_battleground/system_c_deeplearn/data/closed_picks.json",
        "tier": "watch",  # GRU-Attention neural net, model trained
        "ml": "GRU-Attention neural network",
    },
    "ml_bg_d": {
        "name": "Battleground D (Carry)",
        "active": "ml_battleground/system_d_carry/data/active_picks.json",
        "closed": "ml_battleground/system_d_carry/data/closed_picks.json",
        "tier": "watch",  # Funding rate carry strategy
        "ml": "Funding rate carry",
    },
    "ml_bg_e": {
        "name": "Battleground E (Momentum)",
        "active": "ml_battleground/system_e_momentum/data/active_picks.json",
        "closed": "ml_battleground/system_e_momentum/data/closed_picks.json",
        "tier": "watch",  # Momentum strategy
        "ml": "Cross-asset momentum",
    },
    "signal_engine": {
        "name": "Signal Engine",
        "active": "crypto_signal_engine/data/active_picks.json",
        "closed": None,
        "tier": "watch",  # Multi-strategy signal engine
        "ml": "Multi-strategy statistical",
    },
    "breakout_a": {
        "name": "Breakout A (S/R)",
        "active": "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
        "closed": None,
        "tier": "watch",  # Support/Resistance breakout
        "ml": "S/R breakout detection",
    },
    "breakout_b": {
        "name": "Breakout B (ML)",
        "active": "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
        "closed": None,
        "tier": "watch",  # ML-based breakout
        "ml": "ML breakout classifier",
    },
    "breakout_c": {
        "name": "Breakout C (Spike Reverse)",
        "active": "breakout_arena/approach_c_spike_reverse/data/active_picks.json",
        "closed": None,
        "tier": "watch",  # Spike reversal
        "ml": "Spike reversal detection",
    },
    "ml_crypto_predictor": {
        "name": "ML Crypto Predictor",
        "active": "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
        "closed": None,
        "tier": "watch",  # Walk-forward ensemble (RF + GBT + XGBoost)
        "ml": "RF + GBT + XGBoost ensemble",
    },
    "baby_battleground": {
        "name": "Baby Battleground (Top Grads)",
        "active": "battleground/data/active_picks.json",
        "closed": "battleground/data/closed_picks.json",
        "tier": "watch",  # Multi-strategy forward-tested graduates
        "ml": "Multi-strategy forward-tested graduates",
    },
    # ── DEMOTED TIER: Still runs for ML training data, not shown in Discord ──
    "ml_bg_a": {
        "name": "Battleground A",
        "active": "ml_battleground/system_a_filter/data/active_picks.json",
        "closed": "ml_battleground/system_a_filter/data/closed_picks.json",
        "tier": "demoted",  # 10% WR — XGBoost filter underperforming
        "ml": "XGBoost filter (dormant)",
    },
    "ml_bg_b": {
        "name": "Battleground B",
        "active": "ml_battleground/system_b_regime/data/active_picks.json",
        "closed": "ml_battleground/system_b_regime/data/closed_picks.json",
        "tier": "demoted",  # ~17% WR — XGBoost regime classifier
        "ml": "XGBoost regime (dormant)",
    },
    # ── RETIRED TIER: Excluded entirely ──
    "claude_gainer": {
        "name": "Claude Gainer ML",
        "active": "claude_gainer_ml/tracker/claude_live_picks.json",
        "closed": None,
        "tier": "retired",  # 33% WR — superseded by Mercury 2
        "ml": "RF + XGBoost (retired)",
    },
}

# ── Helpers ─────────────────────────────────────────────────────

def _load_json(path: pathlib.Path) -> list | dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_picks(data) -> list[dict]:
    if isinstance(data, list):
        return [p for p in data if isinstance(p, dict)]
    if isinstance(data, dict):
        for key in ("active_picks", "activePicks", "picks", "signals"):
            if isinstance(data.get(key), list):
                return [p for p in data[key] if isinstance(p, dict)]
    return []


def _norm_sym(s: str) -> str:
    return s.strip().upper().replace("-", "").replace("USD", "USDT").replace("USDTT", "USDT")


def _get_direction(p: dict) -> str:
    d = (p.get("direction") or p.get("signal_type") or p.get("signal") or "").upper()
    if "BUY" in d or "LONG" in d:
        return "LONG"
    if "SELL" in d or "SHORT" in d:
        return "SHORT"
    return d


def _is_closed(p: dict) -> bool:
    s = (p.get("status") or "").upper()
    return any(k in s for k in ("WIN", "LOSS", "CLOSED", "STOPPED")) or p.get("exit_price") is not None


def _is_win(p: dict) -> bool | None:
    s = (p.get("status") or "").upper()
    if "WIN" in s or s == "CLOSED_TP" or p.get("exit_reason") == "TP_HIT":
        return True
    if "LOSS" in s or s == "CLOSED_SL" or p.get("exit_reason") == "SL_HIT":
        return False
    pnl = p.get("realized_pnl_pct")
    if pnl is not None:
        return pnl > 0
    return None


# ── Strategy Kill-List (Cerebrus + Audit) ─────────────────────
# Strategies with documented negative edge — suppress from Discord picks
STRATEGY_KILL_LIST = {
    "price_touch_recurrence",        # 0W/5L, -$874
    "double_top_bottom_detector",    # 1W/3L, -$1134, WR 25%
    "fourier_cycle_detector",        # 0W/6L, high-frequency noise
    "smart_money_fvg",               # 0W/9L, all losses in F&G < 15
    "m2_liquidity_lag",              # 2W/7L (22% WR), correlated with Mercury 2
    "exchange_netflow_reversal",     # 0W/6L, on-chain signal has no edge
    "halloween_effect",              # 0W/5L, seasonal factor unreliable in crypto
    "community_ict_fvg_selective",   # 1W/7L (12.5% WR), ICT variant underperforming
    "monthly_seasonality",           # 1W/7L (12.5% WR), calendar effects don't hold
}

# ── ICT/SMC Strategies (disable in extreme fear) ──────────────
ICT_SMC_STRATEGIES = {
    "smart_money_fvg", "break_of_structure", "ict_fvg",
    "fair_value_gap", "bos_choch", "choch_detector",
    "order_block", "liquidity_sweep",
}

# ── Round 2: Oversold strategies killed in downtrend (Lo 2000, 62% fail rate) ──
OVERSOLD_STANDALONE_STRATEGIES = {
    "williams_pct_r", "williams_r", "williams_%r",
    "rsi_bounce", "rsi_oversold", "rsi_divergence",
    "mean_reversion_oversold", "stoch_rsi_oversold",
    "oversold_reversal", "oversold_bounce",
}

# ── Round 2: Volume and ADX thresholds (Llorente 2002, Wilder 1978) ──
MIN_VOLUME_24H_LONG = 50_000_000  # $50M min for LONGs (TRUMP survived at $185M)
MIN_ADX_LONG = 15                  # ADX >= 15 for LONGs (RENDER ADX=3 → SL hit)

# ── Round 2: Dynamic R:R caps by regime (Vince 2000) ──
REGIME_RR_CAPS = {
    "RANGE_BOUND": 1.2,      # Tight TP in ranging market
    "TRENDING_UP": 1.5,      # Normal for trend-following
    "TRENDING_DOWN": 2.0,    # Wider for shorts in downtrend
    "UNKNOWN": 1.5,
}


def _compute_strategy_stats() -> dict[str, dict]:
    """Compute per-strategy win/loss counts across ALL closed picks from ALL systems.

    Returns dict like: {"ensemble": {"wins": 10, "losses": 1, "total": 11, "wr": 0.909}, ...}
    """
    stats: dict[str, dict] = {}

    for sys_id, sys_info in SYSTEMS.items():
        closed_path = sys_info.get("closed")
        if not closed_path:
            continue
        try:
            with open(REPO_ROOT / closed_path, "r", encoding="utf-8") as f:
                closed = json.load(f)
            if not isinstance(closed, list):
                closed = _extract_picks(closed)
            for p in closed:
                strat = (p.get("strategy") or p.get("algorithm")
                         or p.get("strategy_name") or "unknown").lower()
                if strat not in stats:
                    stats[strat] = {"wins": 0, "losses": 0, "total": 0, "wr": 0.0}
                w = _is_win(p)
                if w is True:
                    stats[strat]["wins"] += 1
                    stats[strat]["total"] += 1
                elif w is False:
                    stats[strat]["losses"] += 1
                    stats[strat]["total"] += 1
        except Exception:
            continue

    # Compute WR for each strategy
    for strat, s in stats.items():
        s["wr"] = s["wins"] / s["total"] if s["total"] > 0 else 0.0

    return stats


STALE_THRESHOLD_DAYS = 7  # Strategies with no signal in 7+ days are flagged stale


def check_signal_staleness() -> dict[str, dict]:
    """Check each strategy's most recent signal timestamp across all systems.

    Returns dict of stale strategies:
        {"strategy_name": {"last_trigger": "2026-02-20T...", "days_ago": 12, "system": "..."}}

    A strategy is "stale" if its most recent signal (from active or closed picks)
    is older than STALE_THRESHOLD_DAYS.
    """
    strategy_last_seen: dict[str, dict] = {}

    for sys_id, sys_info in SYSTEMS.items():
        if sys_info.get("tier") in ("retired",):
            continue

        # Check active picks
        active_data = _load_json(REPO_ROOT / sys_info["active"])
        if active_data:
            for p in _extract_picks(active_data):
                _update_last_seen(strategy_last_seen, p, sys_id, sys_info["name"])

        # Check closed picks
        closed_path = sys_info.get("closed")
        if closed_path:
            closed_data = _load_json(REPO_ROOT / closed_path)
            if closed_data:
                for p in (_extract_picks(closed_data) if isinstance(closed_data, dict) else closed_data):
                    _update_last_seen(strategy_last_seen, p, sys_id, sys_info["name"])

    # Identify stale strategies
    now = datetime.now(timezone.utc)
    stale: dict[str, dict] = {}
    for strat, info in strategy_last_seen.items():
        if info.get("last_trigger_dt"):
            days_ago = (now - info["last_trigger_dt"]).days
            if days_ago >= STALE_THRESHOLD_DAYS:
                stale[strat] = {
                    "last_trigger": info["last_trigger"],
                    "days_ago": days_ago,
                    "system": info["system"],
                }

    if stale:
        print(f"\n  ⏳ STALE STRATEGIES ({len(stale)} with no signal in {STALE_THRESHOLD_DAYS}+ days):")
        for s, info in sorted(stale.items(), key=lambda x: x[1]["days_ago"], reverse=True):
            print(f"     {s}: {info['days_ago']}d ago (last from {info['system']})")

    return stale


def _update_last_seen(registry: dict, pick: dict, sys_id: str, sys_name: str):
    """Update the last-seen timestamp for a strategy from a pick."""
    strat = (pick.get("strategy") or pick.get("algorithm")
             or pick.get("strategy_name") or "unknown").lower()

    ts_raw = (pick.get("generated_at") or pick.get("timestamp")
              or pick.get("created_at") or pick.get("last_trigger_ts")
              or pick.get("time") or pick.get("entry_date") or "")

    if not ts_raw:
        return

    try:
        ts_str = str(ts_raw).replace("Z", "+00:00")
        # Handle date-only strings (e.g. "2026-02-20")
        if len(ts_str) == 10:
            ts_str += "T00:00:00+00:00"
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return

    existing = registry.get(strat)
    if not existing or dt > existing.get("last_trigger_dt", datetime.min.replace(tzinfo=timezone.utc)):
        registry[strat] = {
            "last_trigger": str(ts_raw),
            "last_trigger_dt": dt,
            "system": sys_name,
            "system_id": sys_id,
        }


def _compute_rolling_wr(sys_id: str, n: int = ROLLING_WR_WINDOW) -> float | None:
    """Compute rolling WR over last N closed picks. Returns 0.0-1.0 or None."""
    sys_info = SYSTEMS.get(sys_id, {})
    closed_path = sys_info.get("closed")
    if not closed_path:
        return None
    try:
        with open(REPO_ROOT / closed_path, "r", encoding="utf-8") as f:
            closed = json.load(f)
        if not isinstance(closed, list):
            closed = _extract_picks(closed)
        if len(closed) < 5:
            return None
        recent = closed[-n:]
        wins = sum(1 for p in recent if _is_win(p) is True)
        return wins / len(recent)
    except Exception:
        return None


def _fetch_fear_greed() -> int | None:
    """Fetch current Fear & Greed index. Returns 0-100 or None."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "FC-PRO/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        return int(data["data"][0]["value"])
    except Exception:
        return None


def _is_crypto_symbol(sym: str) -> bool:
    """Check if symbol is a crypto pair (ends in USDT/BTC/ETH)."""
    return sym.endswith("USDT") or sym.endswith("BTC") or sym.endswith("ETH")


def _fetch_btc_momentum() -> dict:
    """Fetch BTC 24h price change to detect market regime.

    Returns dict with 'pct_24h' and 'regime' ('down', 'neutral', 'up').
    This is the SINGLE MOST IMPORTANT gate per KIMI research:
    - When BTC is trending down, suppress crypto LONG picks
    - When BTC is trending up, suppress crypto SHORT picks
    """
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT"
        req = urllib.request.Request(url, headers={"User-Agent": "FC-PRO/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        if data.get("retCode") == 0:
            ticker = data["result"]["list"][0]
            pct = float(ticker.get("price24hPcnt", 0)) * 100  # e.g. -0.02 = -2%
            if pct < -2.0:
                regime = "down"
            elif pct > 2.0:
                regime = "up"
            else:
                regime = "neutral"
            return {"pct_24h": round(pct, 2), "regime": regime}
    except Exception:
        pass
    return {"pct_24h": 0, "regime": "neutral"}


def _regime_direction_gate(direction: str, fear_greed: int | None,
                           btc_momentum: dict) -> bool:
    """Returns True if direction is allowed in current regime.

    Core insight from KIMI Research Compilation (Feb 26 2026):
    'The one change that would most improve win rate: implement a
    strict regime-strategy router.'

    Rules:
    - BTC down >2% + F&G < 30 → suppress LONG (panic selling, don't catch knives)
    - BTC up >2% + F&G > 60 → suppress SHORT (don't short into momentum)
    - F&G < 15 (extreme panic) → ONLY allow LONG (contrarian entry, highest edge)
    - F&G > 85 (extreme greed) → ONLY allow SHORT (distribution phase)
    """
    fng = fear_greed or 50
    regime = btc_momentum.get("regime", "neutral")

    # Extreme panic: ONLY longs allowed (this is our highest-edge signal)
    if fng <= 15:
        return direction == "LONG"

    # Extreme greed: ONLY shorts allowed
    if fng >= 85:
        return direction == "SHORT"

    # BTC trending down + fear: suppress longs
    if regime == "down" and fng < 30:
        return direction != "LONG"

    # BTC trending up + greed: suppress shorts
    if regime == "up" and fng > 60:
        return direction != "SHORT"

    return True  # Neutral regime: both directions allowed


def _fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current prices from Bybit (Binance is geo-blocked in CI)."""
    prices = {}
    # Try Bybit batch
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot"
        req = urllib.request.Request(url, headers={"User-Agent": "FC-PRO/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("retCode") == 0:
            for item in data["result"]["list"]:
                prices[item["symbol"].upper()] = float(item["lastPrice"])
    except Exception as e:
        print(f"  [WARN] Bybit batch fetch failed: {e}", file=sys.stderr)

    # Fallback: CoinGecko for missing symbols
    missing = [s for s in symbols if s not in prices]
    if missing:
        try:
            # Map common symbols to CoinGecko IDs
            cg_map = {
                "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
                "DOGEUSDT": "dogecoin", "ADAUSDT": "cardano", "XRPUSDT": "ripple",
                "TAOUSDT": "bittensor", "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink",
                "RENDERUSDT": "render-token",
                "BNBUSDT": "binancecoin", "PEPEUSDT": "pepe", "SHIBUSDT": "shiba-inu",
                "MATICUSDT": "matic-network", "NEARUSDT": "near", "APTUSDT": "aptos",
            }
            ids = [cg_map[s] for s in missing if s in cg_map]
            if ids:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"
                req = urllib.request.Request(url, headers={"User-Agent": "FC-PRO/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    cg = json.loads(resp.read().decode())
                for sym, cg_id in cg_map.items():
                    if cg_id in cg and sym in missing:
                        prices[sym] = cg[cg_id]["usd"]
        except Exception as e:
            print(f"  [WARN] CoinGecko fallback failed: {e}", file=sys.stderr)

    return prices


# ── Core Logic ──────────────────────────────────────────────────

def compute_system_wrs() -> dict[str, dict]:
    """Compute forward win rate for each system from closed picks."""
    results = {}
    for sys_id, sys_info in SYSTEMS.items():
        wins, losses = 0, 0

        # Check closed picks file
        if sys_info.get("closed"):
            closed_data = _load_json(REPO_ROOT / sys_info["closed"])
            if closed_data:
                closed_list = _extract_picks(closed_data)
                for p in closed_list:
                    w = _is_win(p)
                    if w is True:
                        wins += 1
                    elif w is False:
                        losses += 1

        # Also check active picks for closed ones
        active_data = _load_json(REPO_ROOT / sys_info["active"])
        if active_data:
            for p in _extract_picks(active_data):
                if _is_closed(p):
                    w = _is_win(p)
                    if w is True:
                        wins += 1
                    elif w is False:
                        losses += 1

        # Also check per-pick forward_wr if available
        total = wins + losses
        wr = wins / total if total > 0 else 0.0
        results[sys_id] = {
            "name": sys_info["name"],
            "wins": wins,
            "losses": losses,
            "total": total,
            "wr": wr,
            "qualified": total >= MIN_CLOSED_TRADES and wr >= MIN_SYSTEM_WR,
        }
    return results


def collect_actionable_picks(system_wrs: dict, current_prices: dict,
                             fear_greed: int | None = None,
                             btc_momentum: dict | None = None,
                             strategy_stats: dict | None = None,
                             regime: dict | None = None) -> list[dict]:
    """Collect and score all actionable picks from qualified systems.

    Applies multiple quality gates (Cerebrus + Mercury + KIMI Emergency feedback):
    - System tier gating (demoted/retired systems excluded from Discord)
    - Strategy kill-list (proven losers suppressed)
    - ICT/SMC regime gating (disabled when F&G < 20)
    - DSR gate: Bailey & Lopez de Prado Probabilistic Sharpe (p<0.05 required)
    - Rolling WR guard (suppress picks from systems with WR < 45%)
    - Cost-aware score threshold (picks below MIN_SCORE_THRESHOLD filtered)
    - Correlation cap (max N same-direction crypto picks)
    """
    picks = []

    for sys_id, sys_info in SYSTEMS.items():
        # ── Tier gating: demoted/retired systems never appear in Discord ──
        tier = sys_info.get("tier", "watch")
        if tier in ("demoted", "retired"):
            continue  # System A, Claude Gainer etc. still run for ML data, just not shown

        wr_data = system_wrs.get(sys_id, {})

        # Use per-pick forward_wr as override if system-level WR is unknown
        system_qualified = wr_data.get("qualified", False)
        system_wr = wr_data.get("wr", 0)

        # ── Rolling WR guard: suppress systems with degraded recent performance ──
        rolling_wr = _compute_rolling_wr(sys_id)
        if rolling_wr is not None and rolling_wr < ROLLING_WR_SUSPEND:
            print(f"  [GUARD] {sys_info['name']} rolling WR {rolling_wr*100:.0f}% < {ROLLING_WR_SUSPEND*100:.0f}% — suppressed")
            continue

        # ── DSR gate: require statistical evidence of positive edge ──
        if _HAS_DSR_GATE and wr_data.get("total", 0) >= 20:
            closed_path = sys_info.get("closed")
            if closed_path:
                closed_data = _load_json(REPO_ROOT / closed_path)
                if closed_data:
                    closed_list = _extract_picks(closed_data) if isinstance(closed_data, dict) else closed_data
                    avg_gain, avg_loss = compute_system_avg_gains(closed_list)
                    dsr_pass, dsr_reason = passes_dsr_gate(
                        sys_id,
                        wr_data.get("wins", 0),
                        wr_data.get("losses", 0),
                        avg_gain,
                        avg_loss,
                    )
                    if not dsr_pass:
                        print(f"  [DSR] {sys_info['name']} BLOCKED: {dsr_reason}")
                        continue
                    else:
                        print(f"  [DSR] {sys_info['name']}: {dsr_reason}")

        active_data = _load_json(REPO_ROOT / sys_info["active"])
        if not active_data:
            continue

        for p in _extract_picks(active_data):
            if _is_closed(p):
                continue

            # Get entry, TP, SL
            entry = p.get("entry_price") or p.get("entryPrice") or 0
            tp = p.get("take_profit") or p.get("tp_price") or p.get("targetPrice") or p.get("tp1_price") or 0
            sl = p.get("stop_loss") or p.get("sl_price") or p.get("stopPrice") or 0
            if not entry or not tp:
                continue

            sym = _norm_sym(p.get("symbol") or p.get("pair") or "")
            direction = _get_direction(p)
            if not sym or not direction:
                continue

            # ── Crypto-only filter: FC-PRO is restricted to crypto picks ──
            if not _is_crypto_symbol(sym):
                continue

            strategy = p.get("strategy") or p.get("algorithm") or p.get("strategy_name") or "default"

            # ── Signal staleness guard (Round 9): discard picks older than 45 min ──
            pick_ts = p.get("timestamp") or p.get("generated_at") or p.get("time") or ""
            if pick_ts:
                try:
                    from datetime import timezone as _tz
                    pick_dt = datetime.fromisoformat(str(pick_ts).replace("Z", "+00:00"))
                    age_min = (datetime.now(_tz.utc) - pick_dt).total_seconds() / 60
                    if age_min > 45:
                        continue  # Stale signal — price has already moved
                except (ValueError, TypeError):
                    pass

            # ── Strategy kill-list: suppress proven losers ──
            if strategy.lower() in STRATEGY_KILL_LIST:
                continue

            # ── ICT/SMC regime gating: disable in extreme fear ──
            if strategy.lower() in ICT_SMC_STRATEGIES and fear_greed is not None and fear_greed < 20:
                continue

            # ── Round 2: Oversold strategy kill in downtrend (Lo 2000) ──
            current_regime_str = regime.get("regime", "UNKNOWN") if regime else "UNKNOWN"
            if (strategy.lower() in OVERSOLD_STANDALONE_STRATEGIES
                    and current_regime_str == "TRENDING_DOWN"
                    and direction == "LONG"):
                continue  # Oversold bounce longs fail 62% in downtrends

            # ── Regime-direction gate: suppress direction misaligned with market ──
            if _is_crypto_symbol(sym):
                # Prefer EMA-based regime router (v2.0: includes RSI-14); fall back to 24h momentum gate
                if _HAS_REGIME_ROUTER and regime:
                    if not _regime_check(direction, regime.get("fng"), regime.get("regime", "UNKNOWN"), regime.get("btc_dom_trend", "NEUTRAL"), regime.get("rsi_14")):
                        continue
                elif btc_momentum:
                    if not _regime_direction_gate(direction, fear_greed, btc_momentum):
                        continue

            # Per-pick forward WR override (Alpha Engine, KIMI provide this)
            pick_fwd_wr = p.get("forward_wr")
            pick_fwd_trades = p.get("forward_trades", 0)
            effective_wr = system_wr
            if pick_fwd_wr is not None and pick_fwd_trades >= MIN_CLOSED_TRADES:
                effective_wr = pick_fwd_wr
                if effective_wr >= MIN_SYSTEM_WR:
                    system_qualified = True  # Override system qualification

            if not system_qualified and effective_wr < MIN_SYSTEM_WR:
                continue

            # Calculate entry room
            cur_price = current_prices.get(sym) or p.get("current_price") or p.get("currentPrice")
            if not cur_price:
                continue

            # Skip picks where SL has already been breached (already stopped out)
            if sl:
                if direction == "LONG" and cur_price < sl:
                    continue
                if direction == "SHORT" and cur_price > sl:
                    continue

            if direction == "LONG":
                if tp <= entry:
                    continue
                entry_room_used = (cur_price - entry) / (tp - entry)
            else:
                if entry <= tp:
                    continue
                entry_room_used = (entry - cur_price) / (entry - tp)

            entry_room_used = max(0, min(1, entry_room_used))
            if entry_room_used > MAX_ENTRY_ROOM_USED:
                continue  # Too late to enter

            # Risk/Reward
            rr = abs(tp - entry) / abs(entry - sl) if sl and abs(entry - sl) > 0 else 0

            # Confidence
            conf = p.get("confidence") or p.get("ml_score") or 0.5

            # Score: WR * remaining room * confidence boost
            score = effective_wr * (1 - entry_room_used)

            # ── Round 2: Regime multiplier (Moskowitz 2012 TSMOM) ──
            regime_mult = 1.0
            if regime:
                r_str = regime.get("regime", "UNKNOWN")
                if r_str == "TRENDING_DOWN":
                    regime_mult = 1.2 if direction == "SHORT" else 0.7
                elif r_str == "TRENDING_UP":
                    regime_mult = 1.2 if direction == "LONG" else 0.7
                elif r_str == "RANGE_BOUND":
                    regime_mult = 1.0  # Neutral in ranging
            score *= regime_mult

            # ── Round 2: Volume multiplier (Llorente 2002) ──
            vol_24h = p.get("volume_24h") or p.get("volume_24h_usd") or p.get("vol_24h") or 0
            try:
                vol_24h = float(vol_24h)
            except (ValueError, TypeError):
                vol_24h = 0
            if vol_24h >= 50_000_000:
                vol_mult = 1.2
            elif vol_24h >= 10_000_000:
                vol_mult = 1.0
            else:
                vol_mult = 0.7 if direction == "LONG" else 0.9  # Shorts less vol-sensitive
            score *= vol_mult

            # ── Round 2: ADX gate for LONGs (Wilder 1978) ──
            pick_adx = p.get("adx") or p.get("adx_14") or 0
            try:
                pick_adx = float(pick_adx)
            except (ValueError, TypeError):
                pick_adx = 0
            if direction == "LONG" and pick_adx > 0 and pick_adx < MIN_ADX_LONG:
                score *= 0.7  # Penalize low-ADX longs (chop trap)

            # ── Cost-aware threshold: filter low-score noise ──
            if score < MIN_SCORE_THRESHOLD:
                continue

            # ── Round 2: Dynamic R:R by regime (Vince 2000) ──
            rr_cap = REGIME_RR_CAPS.get(current_regime_str, 1.5)
            min_rr = min(MIN_RISK_REWARD, rr_cap)  # Use lower of static and dynamic cap

            # ── RR gate: require minimum risk/reward ratio ──
            if rr < min_rr:
                continue

            # ── Core whitelist check: suppress killed strategies, penalize non-core ──
            whitelist = _load_core_whitelist()
            wl_safe = set()
            for _sg in ("protected_strategies", "core_strategies", "incubator_strategies"):
                wl_safe.update(s.lower() for s in whitelist.get(_sg, []) if isinstance(s, str))
            wl_kill = set()
            for _ks in whitelist.get("kill_list", []):
                _kb = _ks.split("::", 1)[1].lower() if "::" in _ks else _ks.lower()
                if _kb not in wl_safe:
                    wl_kill.add(_ks.lower())
                    if "::" in _ks:
                        wl_kill.add(_kb)
            wl_core = {s.lower() for s in whitelist.get("core_strategies", [])}
            strat_lower = strategy.lower()
            if strat_lower in wl_kill:
                continue  # Strategy on kill list — skip entirely
            if wl_core and strat_lower not in wl_core:
                # Non-core strategy: reduce score by 20% (lower priority)
                score *= 0.80

            # Strategy-level W/L from closed picks
            strat_key = strategy.lower()
            strat_s = (strategy_stats or {}).get(strat_key, {})
            strat_wins = strat_s.get("wins", 0)
            strat_losses = strat_s.get("losses", 0)
            strat_total = strat_s.get("total", 0)
            strat_wr = strat_s.get("wr", 0.0)

            picks.append({
                "symbol": sym,
                "direction": direction,
                "entry_price": entry,
                "tp_price": tp,
                "sl_price": sl,
                "current_price": cur_price,
                "entry_room_pct": round((1 - entry_room_used) * 100, 1),
                "system": sys_info["name"],
                "system_id": sys_id,
                "system_wr": round(effective_wr * 100, 1),
                "strategy": strategy,
                "strat_wins": strat_wins,
                "strat_losses": strat_losses,
                "strat_total": strat_total,
                "strat_wr": round(strat_wr * 100, 1),
                "confidence": round(conf, 3),
                "risk_reward": round(rr, 2),
                "score": round(score, 4),
                "tp_pct": round(abs(tp - entry) / entry * 100, 2),
                "sl_pct": round(abs(sl - entry) / entry * 100, 2),
                "tier": tier,
                "regime": current_regime_str,
                "regime_mult": round(regime_mult, 2),
                "vol_24h": vol_24h,
                "vol_mult": round(vol_mult, 2),
                "adx": round(pick_adx, 1) if pick_adx else None,
            })

    # Sort by score descending
    picks.sort(key=lambda x: x["score"], reverse=True)

    # ── Correlation cap: limit same-direction crypto picks ──
    # Mercury feedback: "max 3 crypto longs simultaneously" to prevent
    # correlated wipeout from single market crash
    crypto_long_count = 0
    crypto_short_count = 0
    capped_picks = []
    for p in picks:
        if _is_crypto_symbol(p["symbol"]):
            if p["direction"] == "LONG":
                if crypto_long_count >= MAX_CRYPTO_SAME_DIR:
                    continue  # Skip — too many correlated longs
                crypto_long_count += 1
            elif p["direction"] == "SHORT":
                if crypto_short_count >= MAX_CRYPTO_SAME_DIR:
                    continue
                crypto_short_count += 1
        capped_picks.append(p)
    picks = capped_picks

    # ── Conflict Auto-Resolution (KIMI Emergency + Mercury feedback) ──
    # When systems disagree on the same symbol, the one with higher rolling WR wins.
    # The losing side is REMOVED from picks (not just flagged red).
    # This prevents self-cancelling trades and concentrates capital on strongest signal.
    by_symbol: dict[str, list[dict]] = {}
    for p in picks:
        by_symbol.setdefault(p["symbol"], []).append(p)

    resolved_picks = []
    conflict_log = []
    for sym, sym_picks in by_symbol.items():
        dirs = {p["direction"] for p in sym_picks}
        if len(dirs) > 1:  # Both LONG and SHORT exist — CONFLICT
            # Sort by score — highest wins
            sym_picks.sort(key=lambda x: x["score"], reverse=True)
            winner = sym_picks[0]
            losers = [p for p in sym_picks[1:] if p["direction"] != winner["direction"]]

            # Log the conflict for transparency
            for loser in losers:
                conflict_log.append({
                    "symbol": sym,
                    "winner": f"{winner['system']} {winner['direction']} (score {winner['score']:.3f})",
                    "loser": f"{loser['system']} {loser['direction']} (score {loser['score']:.3f})",
                })

            # Winner gets a note about the resolved conflict
            if losers:
                winner["conflict"] = False
                winner["conflict_warning"] = (
                    f"Resolved: {losers[0]['system']} {losers[0]['direction']} suppressed "
                    f"(score {losers[0]['score']:.3f} < {winner['score']:.3f})"
                )

            # Keep winner + same-direction picks, DROP opposing direction
            for p in sym_picks:
                if p["direction"] == winner["direction"]:
                    p["conflict"] = False
                    if p is not winner:
                        p["conflict_warning"] = None
                    resolved_picks.append(p)
                # Opposing direction picks are DROPPED (auto-resolved)
        else:
            # No conflict — keep all
            for p in sym_picks:
                p["conflict"] = False
                p["conflict_warning"] = None
                resolved_picks.append(p)

    if conflict_log:
        print(f"\n  ⚔️  CONFLICTS AUTO-RESOLVED on {len(conflict_log)} symbol(s):")
        for c in conflict_log:
            print(f"     {c['symbol']}: ✅ {c['winner']} beats ❌ {c['loser']}")

    # ── Consensus tagging: count unique agreeing systems per symbol+direction ──
    consensus_map: dict[str, set[str]] = {}
    for p in resolved_picks:
        key = f"{p['symbol']}_{p['direction']}"
        consensus_map.setdefault(key, set()).add(p["system_id"])

    for p in resolved_picks:
        key = f"{p['symbol']}_{p['direction']}"
        agreeing = consensus_map.get(key, set())
        p["agreeing_systems"] = len(agreeing)
        p["agreeing_system_names"] = sorted(agreeing)
        p["is_top_pick"] = len(agreeing) >= MIN_CONSENSUS_SYSTEMS

    top_count = sum(1 for p in resolved_picks if p["is_top_pick"])
    if top_count:
        print(f"\n  ★ {top_count} TOP PICKS with consensus from >= {MIN_CONSENSUS_SYSTEMS} systems")

    return resolved_picks


# ── Discord Embed ───────────────────────────────────────────────

# EST timezone (UTC-5)
_EST = timezone(timedelta(hours=-5))

# Module-level cache for system WRs (populated in main/build_discord)
system_wrs_cache: dict[str, dict] = {}


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"


def _now_est() -> str:
    """Current time in EST."""
    return datetime.now(_EST).strftime("%b %d, %Y %I:%M %p EST")


def _format_pick_line(p: dict) -> str:
    """Format a single pick as a Discord embed line."""
    emoji = "\U0001f4c8" if p["direction"] == "LONG" else "\U0001f4c9"
    room_bar = "\u2588" * int(p["entry_room_pct"] / 10) + "\u2591" * (10 - int(p["entry_room_pct"] / 10))
    conflict_line = ""
    if p.get("conflict_warning"):
        conflict_line = f"\n  \u2694\ufe0f *{p['conflict_warning']}*"

    # System WR with W/L counts (e.g. "10W/1L, 90.9% WR")
    sys_wr_data = system_wrs_cache.get(p.get("system_id", ""), {})
    sys_w = sys_wr_data.get("wins", 0)
    sys_l = sys_wr_data.get("losses", 0)
    sys_wr_str = f"{sys_w}W/{sys_l}L, {p['system_wr']}% WR"

    # Strategy W/L (e.g. "ensemble 90.9% (10W/1L)" or "ensemble (new)" if no data)
    strat_w = p.get("strat_wins", 0)
    strat_l = p.get("strat_losses", 0)
    strat_total = p.get("strat_total", 0)
    if strat_total > 0:
        strat_wr_pct = p.get("strat_wr", 0)
        strat_str = f"`{p['strategy'][:25]}` {strat_wr_pct}% ({strat_w}W/{strat_l}L)"
    else:
        strat_str = f"`{p['strategy'][:25]}` *(new)*"

    return (
        f"**{emoji} {p['symbol']}** {p['direction']} \u2014 {p['system']} ({sys_wr_str})\n"
        f"  Entry: {_fmt_price(p['entry_price'])} \u2192 TP: {_fmt_price(p['tp_price'])} (+{p['tp_pct']}%)\n"
        f"  Current: {_fmt_price(p['current_price'])} | Room to TP: {room_bar} {p['entry_room_pct']}%\n"
        f"  SL: {_fmt_price(p['sl_price'])} (-{p['sl_pct']}%) | R:R {p['risk_reward']} | {strat_str}"
        f"{' | ★ TOP PICK (' + str(p.get('agreeing_systems', 0)) + ' systems agree)' if p.get('is_top_pick') else ''}"
        f"{conflict_line}"
    )


def _build_discord_payloads(picks: list[dict], system_wrs: dict) -> list[dict]:
    """Build multiple Discord payloads to show ALL picks.

    Discord webhook limit: 6000 chars total per message. With 32 picks at ~250 chars
    each, we need multiple messages. Each payload gets one embed under the limit.
    """
    now = _now_est()

    if not picks:
        return [{"embeds": [{
            "title": "FC-CRYPTO PRO \u2014 No Qualifying Picks Right Now",
            "description": f"Scanned all systems. No picks pass the quality filter (WR>{MIN_SYSTEM_WR*100:.0f}% + Entry Room>{(1-MAX_ENTRY_ROOM_USED)*100:.0f}%).\n\nCheck back after the next scan cycle.",
            "color": 0x888888,
            "footer": {"text": f"FC-PRO v2.0 | {now}"},
        }]}]

    qualified_systems = [f"{v['name']} ({v['wins']}W/{v['losses']}L, {v['wr']*100:.0f}%)" for k, v in system_wrs.items() if v["qualified"]]
    all_lines = [_format_pick_line(p) for p in picks]

    # Pack picks into pages (max ~3800 chars per page)
    MAX_DESC = 3800
    pages = []
    current_lines = []
    current_len = 0

    for line in all_lines:
        line_len = len(line) + 2
        if current_len + line_len > MAX_DESC and current_lines:
            pages.append(current_lines)
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += line_len
    if current_lines:
        pages.append(current_lines)

    # Build one payload per page (each sent as separate webhook request)
    # Red sidebar (0xef4444) for pages containing conflicted picks
    payloads = []
    for idx, page_lines in enumerate(pages):
        desc = "\n\n".join(page_lines)
        embed_color = 0x22c55e  # Green — conflicts are now auto-resolved
        embed = {"description": desc[:4090], "color": embed_color}
        if idx == 0:
            embed["title"] = f"🏆 FC-CRYPTO PRO — {len(picks)} Top Actionable Picks"
        else:
            embed["title"] = f"📋 FC-PRO — Page {idx + 1}/{len(pages) + 1}"
        payloads.append({"embeds": [embed]})

    # Summary payload (last message)
    resolved = sum(1 for p in picks if p.get("conflict_warning"))
    summary = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    summary += f"**Filters:** WR>{MIN_SYSTEM_WR*100:.0f}% | Room>{(1-MAX_ENTRY_ROOM_USED)*100:.0f}% | Score>{MIN_SCORE_THRESHOLD}\n"
    summary += f"**Guards:** Kill-list ({len(STRATEGY_KILL_LIST)}) | Crypto cap {MAX_CRYPTO_SAME_DIR}/dir | Rolling WR>{ROLLING_WR_SUSPEND*100:.0f}%\n"
    summary += f"**Qualified Systems:** {', '.join(qualified_systems) or 'None'}\n"
    summary += f"**{len(picks)}** picks shown — quality-filtered from all active positions"
    if resolved:
        summary += f"\n⚔️ **{resolved} conflicts auto-resolved** — higher-scoring system wins, opposing direction suppressed"
    payloads.append({"embeds": [{
        "description": summary,
        "color": 0x3b82f6,
        "footer": {"text": f"FC-PRO v2.0 | Quality Gates + Conflict Resolution | {now}"},
    }]})

    # ── Audit trail: show ALL systems and their status ──
    audit_lines = ["**All Sources Scanned:**"]
    for sys_id, sys_info in SYSTEMS.items():
        tier = sys_info.get("tier", "watch")
        wr_data = system_wrs.get(sys_id, {})
        ml_tech = sys_info.get("ml", "?")
        w = wr_data.get("wins", 0)
        l = wr_data.get("losses", 0)
        total = wr_data.get("total", 0)
        wr = wr_data.get("wr", 0)
        qual = wr_data.get("qualified", False)

        if tier == "retired":
            status = "⛔"
        elif tier == "demoted":
            status = "⬇️"
        elif qual:
            status = "✅"
        elif total < MIN_CLOSED_TRADES:
            status = "🔄"
        else:
            status = "❌"

        name = sys_info["name"]
        if total > 0:
            audit_lines.append(f"{status} **{name}** {w}W/{l}L ({wr*100:.0f}%) — {ml_tech}")
        else:
            audit_lines.append(f"{status} **{name}** collecting data — {ml_tech}")

    audit_lines.append(f"\n✅=qualified ❌=below WR 🔄=collecting ⬇️=demoted ⛔=retired")
    audit_lines.append(f"*New systems auto-qualify at WR>{MIN_SYSTEM_WR*100:.0f}% with {MIN_CLOSED_TRADES}+ trades*")
    audit_text = "\n".join(audit_lines)
    payloads.append({"embeds": [{
        "title": "🔍 FC-PRO System Audit Trail",
        "description": audit_text[:4090],
        "color": 0x6366f1,
        "footer": {"text": f"{len(SYSTEMS)} systems tracked | {now}"},
    }]})

    return payloads


def send_discord_embed(picks: list[dict], system_wrs: dict):
    try:
        import requests as _req
    except ImportError:
        _req = None

    webhook_keys = ["DISCORD_WEBHOOK_FRESHPICKS", "DISCORD_WEBHOOK_URL"]
    webhooks = [(k, os.environ.get(k)) for k in webhook_keys if os.environ.get(k)]

    if not webhooks:
        print("[ERROR] No Discord webhook URL configured", file=sys.stderr)
        return False

    payloads = _build_discord_payloads(picks, system_wrs)

    # Try each webhook until one works, then send all pages through it
    for wh_name, wh_url in webhooks:
        try:
            # Test with first payload
            if _req:
                resp = _req.post(wh_url, json=payloads[0], timeout=15)
                if resp.status_code not in (200, 204):
                    print(f"  [WARN] {wh_name} returned {resp.status_code}", file=sys.stderr)
                    continue
            else:
                data = json.dumps(payloads[0]).encode("utf-8")
                req = urllib.request.Request(wh_url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status not in (200, 204):
                        continue

            # First message sent — now send remaining pages with small delay
            sent = 1
            for payload in payloads[1:]:
                time.sleep(0.5)  # Rate limit: Discord allows ~5 req/sec per webhook
                try:
                    if _req:
                        r = _req.post(wh_url, json=payload, timeout=15)
                        if r.status_code in (200, 204):
                            sent += 1
                    else:
                        d = json.dumps(payload).encode("utf-8")
                        rq = urllib.request.Request(wh_url, data=d, headers={"Content-Type": "application/json"})
                        with urllib.request.urlopen(rq, timeout=15):
                            sent += 1
                except Exception as e:
                    print(f"  [WARN] Page send failed: {e}", file=sys.stderr)

            print(f"  [OK] Discord: {sent}/{len(payloads)} messages sent via {wh_name} ({len(picks)} picks)")
            return True

        except Exception as e:
            print(f"  [WARN] {wh_name} failed: {e}", file=sys.stderr)

    print("[ERROR] All Discord webhooks failed", file=sys.stderr)
    return False


def _all_active_count():
    """Generator of all active picks for counting."""
    for sys_id, sys_info in SYSTEMS.items():
        active_data = _load_json(REPO_ROOT / sys_info["active"])
        if active_data:
            for p in _extract_picks(active_data):
                if not _is_closed(p):
                    yield p


# ── Main ────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("FC-CRYPTO PRO — Top Actionable Picks Scanner")
    print("=" * 60)

    # 1. Compute system win rates
    print("\n[1/4] Computing system forward win rates...")
    system_wrs = compute_system_wrs()
    for sys_id, data in system_wrs.items():
        status = "✓ QUALIFIED" if data["qualified"] else "✗ filtered"
        print(f"  {data['name']:25s} | {data['wins']}W/{data['losses']}L ({data['wr']*100:.0f}% WR) | {status}")

    # 2. Collect symbols for price fetch
    print("\n[2/4] Collecting active picks from all systems...")
    all_symbols = set()
    for sys_id, sys_info in SYSTEMS.items():
        active_data = _load_json(REPO_ROOT / sys_info["active"])
        if active_data:
            for p in _extract_picks(active_data):
                if not _is_closed(p):
                    sym = _norm_sym(p.get("symbol") or p.get("pair") or "")
                    if sym:
                        all_symbols.add(sym)
    print(f"  Found {len(all_symbols)} unique symbols across all systems")

    # 3. Fetch current prices
    print("\n[3/4] Fetching current prices (Bybit + CoinGecko fallback)...")
    current_prices = _fetch_current_prices(list(all_symbols))
    print(f"  Got prices for {len(current_prices)} symbols")

    # 3b. Fetch regime data (EMA-based regime router + F&G)
    regime_data = None
    if _HAS_REGIME_ROUTER:
        print("\n  [REGIME ROUTER] Fetching EMA-based regime...")
        regime_data = get_current_regime()
        fng = regime_data.get("fng")
        print(f"  Fear & Greed:   {fng} ({regime_data.get('fng_classification', '?')})")
        print(f"  BTC Regime:     {regime_data.get('regime', '?')} (ADX: {regime_data.get('adx', '?')}, RSI: {regime_data.get('rsi_14', '?')})")
        print(f"  BTC Dominance:  {regime_data.get('btc_dom_trend', '?')}")
        print(f"  Longs Allowed:  {'YES' if regime_data.get('longs_allowed') else 'NO'}")
        print(f"  Shorts Allowed: {'YES' if regime_data.get('shorts_allowed') else 'NO'}")
    else:
        fng = _fetch_fear_greed()
        if fng is not None:
            print(f"  Fear & Greed Index: {fng} {'(EXTREME FEAR)' if fng <= 15 else ''}")
        else:
            print(f"  Fear & Greed Index: unavailable")

    # 3c. Fetch BTC momentum as fallback for regime-direction gate
    btc_mom = _fetch_btc_momentum()
    print(f"  BTC 24h: {btc_mom['pct_24h']:+.2f}% (momentum: {btc_mom['regime']})")

    # 3d. Compute per-strategy win/loss stats
    strat_stats = _compute_strategy_stats()
    print(f"  Strategy stats: {len(strat_stats)} strategies tracked across all systems")

    # 4. Score and filter (with all quality gates)
    print("\n[4/4] Scoring and filtering picks...")
    print(f"  Guards active: tier gating | strategy kill-list ({len(STRATEGY_KILL_LIST)} blocked)")
    print(f"  Guards active: DSR gate (PSR p<0.05) | rolling WR > {ROLLING_WR_SUSPEND*100:.0f}% | score > {MIN_SCORE_THRESHOLD}")
    print(f"  Guards active: RR >= {MIN_RISK_REWARD} | consensus >= {MIN_CONSENSUS_SYSTEMS} systems for TOP")
    print(f"  Guards active: crypto cap {MAX_CRYPTO_SAME_DIR} per direction | ICT/SMC off when F&G<20")
    if _HAS_REGIME_ROUTER and regime_data:
        print(f"  Guards active: REGIME ROUTER (EMA-based: {regime_data.get('regime')}, F&G {fng or '?'})")
    else:
        print(f"  Guards active: regime-direction gate (BTC {btc_mom['regime']}, F&G {fng or '?'})")
    picks = collect_actionable_picks(system_wrs, current_prices, fear_greed=fng, btc_momentum=btc_mom, strategy_stats=strat_stats, regime=regime_data)
    print(f"  {len(picks)} picks qualify after all gates")

    if picks:
        # Show conflicts first
        conflicted = [p for p in picks if p.get("conflict_warning")]
        if conflicted:
            syms = {p["symbol"] for p in conflicted}
            print(f"\n  ⚠️  CONFLICTS DETECTED on {len(syms)} symbol(s): {', '.join(sorted(syms))}")
            for p in conflicted:
                print(f"     {p['symbol']} {p['direction']} ({p['system']}) — {p.get('conflict_warning', '')}")

        print("\n  TOP PICKS:")
        for i, p in enumerate(picks[:10]):
            flag = " ⚠️" if p.get("conflict_warning") else ""
            print(f"  #{i+1} {p['symbol']:12s} {p['direction']:5s} | {p['system']:20s} | WR:{p['system_wr']:5.1f}% | Room to TP:{p['entry_room_pct']:5.1f}% | Score:{p['score']:.3f}{flag}")

    # 4b. Signal decay monitoring
    stale_strategies = check_signal_staleness()

    # 5. Save results
    out_path = REPO_ROOT / "data" / "fc_crypto_pro_picks.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        # Build systems audit for JSON consumers (Discord bot, dashboards)
        systems_audit = {}
        for sys_id, sys_info in SYSTEMS.items():
            wr_data = system_wrs.get(sys_id, {})
            systems_audit[sys_id] = {
                "name": sys_info["name"],
                "tier": sys_info.get("tier", "watch"),
                "ml": sys_info.get("ml", "?"),
                "wins": wr_data.get("wins", 0),
                "losses": wr_data.get("losses", 0),
                "total": wr_data.get("total", 0),
                "wr": round(wr_data.get("wr", 0), 4),
                "qualified": wr_data.get("qualified", False),
            }
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_at_est": _now_est(),
            "filters": {
                "min_system_wr": MIN_SYSTEM_WR,
                "max_entry_room_used": MAX_ENTRY_ROOM_USED,
                "min_closed_trades": MIN_CLOSED_TRADES,
            },
            "system_wrs": {k: {**v, "wr": round(v["wr"], 4)} for k, v in system_wrs.items()},
            "systems_audit": systems_audit,
            "picks": picks,
            "total_qualifying": len(picks),
            "total_systems": len(SYSTEMS),
            "stale_strategies": stale_strategies,
        }
        if regime_data:
            output["regime"] = regime_data
        json.dump(output, f, indent=2)
    print(f"\n  Saved to {out_path}")

    # 6. Send to Discord
    print("\n[5/5] Sending to Discord...")
    # Populate system WR cache for _format_pick_line
    global system_wrs_cache
    system_wrs_cache = {sys_id: data for sys_id, data in system_wrs.items()}
    send_discord_embed(picks, system_wrs)

    print(f"\n{'=' * 60}")
    print(f"FC-CRYPTO PRO complete: {len(picks)} qualifying picks")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Cross-System Signal Aggregator
===============================
Reads active_picks.json from ALL trading systems, groups by symbol,
applies a consensus rule (>= CONSENSUS_THRESHOLD systems agree on direction),
and writes a unified aggregated_picks.json.

Only consensus-validated picks pass to the execution layer, eliminating
internal conflicts (e.g., Mercury 2 LONG vs. ML Battleground SHORT).

Run: python cross_aggregation/aggregator.py
"""

import json
import os
import pathlib
import sys
import time
import datetime as dt
import urllib.request
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional

# Regime-strategy router (prevents direction-regime mismatches)
try:
    from cross_aggregation.regime_router import get_current_regime, should_generate_signal
    _HAS_REGIME_ROUTER = True
except ImportError:
    _HAS_REGIME_ROUTER = False

# Hierarchical regime detector (3-level HMM: macro/sector/micro)
try:
    from regime_terminal.hierarchical_regime import get_regime_weights
    _HAS_HIERARCHICAL_REGIME = True
except ImportError:
    _HAS_HIERARCHICAL_REGIME = False

# Regime meta-router (unifies all 5 detectors into consensus + strategy-level scoring)
try:
    from cross_aggregation.regime_meta_router import get_consensus_regime, score_picks_by_regime
    _HAS_META_ROUTER = True
except ImportError:
    _HAS_META_ROUTER = False

# Beta Confluence Scorer — experimental A/B scoring (2026-03-16)
try:
    from cross_aggregation.beta_confluence_scorer import BetaConfluenceScorer
    _HAS_BETA_SCORER = True
except ImportError:
    try:
        from beta_confluence_scorer import BetaConfluenceScorer
        _HAS_BETA_SCORER = True
    except ImportError:
        _HAS_BETA_SCORER = False

# Portfolio Sharpe allocator (Sharpe-weighted consensus scoring)
try:
    from portfolio_tracker.sharpe_allocator import get_system_weight
    _HAS_SHARPE_WEIGHTS = True
except ImportError:
    _HAS_SHARPE_WEIGHTS = False

# Pick classifier for tiered routing
try:
    from cross_aggregation.pick_classifier import classify_pick, get_all_system_stats
    _HAS_CLASSIFIER = True
except ImportError:
    _HAS_CLASSIFIER = False

# Dynamic trust tier system (Phase 1: demote/block weak systems)
try:
    from cross_aggregation.system_trust_registry import (
        get_dynamic_system_tier, get_dynamic_vote_weight,
        is_system_blocked, get_all_system_tiers, reset_dynamic_cache,
        TIER_BANNED, TIER_UNTRUSTED, TIER_WATCH, TIER_PROVEN, TIER_RELIABLE,
    )
    _HAS_DYNAMIC_TRUST = True
except ImportError:
    _HAS_DYNAMIC_TRUST = False

# Audit trail integration
try:
    # Ensure repo root is on sys.path for audit_trail package
    _repo_root_str = str(pathlib.Path(__file__).resolve().parent.parent)
    if _repo_root_str not in sys.path:
        sys.path.insert(0, _repo_root_str)
    from audit_trail import (
        start_run, finish_run, record_raw_pick,
        record_consensus_pick, record_filter, record_event,
    )
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Map of system name -> relative path to active_picks.json
SYSTEMS: Dict[str, str] = {
    "mercury2":         "mercury2/data/active_picks.json",
    "alpha_engine":     "alpha_engine/data/active_picks.json",
    "kimi":             "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "battleground":     "battleground/data/active_picks.json",
    "signal_engine":    "crypto_signal_engine/data/active_picks.json",
    "crypto_ml_edge":   "crypto_ml_edge/data/active_picks.json",
    "ml_bg_a":          "ml_battleground/system_a_filter/data/active_picks.json",
    "ml_bg_b":          "ml_battleground/system_b_regime/data/active_picks.json",
    "ml_bg_c":          "ml_battleground/system_c_deeplearn/data/active_picks.json",
    "breakout_a":       "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
    "breakout_b":       "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
    "breakout_c":       "breakout_arena/approach_c_spike_reverse/data/active_picks.json",
    "claws_of_doom":    "ml_battleground/system_f_clawsofdoom/data/active_picks.json",
    # BLOCKED 2026-03-15: ml_bg_ensemble — 0% WR, 8 trades, -33% PnL. See DEMOTED_SYSTEMS.
    # "ml_bg_ensemble":   "ml_battleground/ensemble_data/active_picks.json",
    "claude_gainer":    "claude_gainer_ml/tracker/claude_live_picks.json",
    "predictions":      "predictions/data/active_predictions.json",
    "ml_bg_d":          "ml_battleground/system_d_carry/data/active_picks.json",
    "ml_bg_e":          "ml_battleground/system_e_momentum/data/active_picks.json",
    "regime_terminal":  "regime_terminal/data/active_signals.json",
    "ml_crypto_pred":   "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
    "incubator_fwd":    "incubator/backtest_results/forward_signals.json",
    "genome":           "genome/data/universal_picks.json",
    "genome_genesis":   "genome/data/gp_active_picks.json",
    "genome_legion":    "genome/data/ensemble_active_picks.json",
    "genome_atlas":     "genome/data/mape_active_picks.json",
    "paper_trading":    "paper_trading/data/active_picks.json",
    "coinglass_strategies": "coinglass_strategies/data/active_picks.json",
    # DEPRECATED 2026-03-16: rl_agent is stale/abandoned (last data Mar 14). Picks pollute dashboard.
    # "rl_agent":         "rl_agent/data/active_picks.json",
    # ── Spike/Pump/Gainer detection systems (wired 2026-03-13 audit) ──
    "incubator_gainer":     "incubator/agents/claude_code_01/data/gainer_scores_latest.json",
    "claude_gainer_st":     "claude_gainer_ml/tracker/short_term_active.json",
    "rapid_fire":           "rapid_fire_data/active_picks.json",
    "goldmine_meme":        "data/goldmine/meme_winners.json",
    "goldmine_stocks":      "data/goldmine/stock_picks.json",
    "meme_scanner":         "data/meme_scanner_active.json",
    "live_spike_trader":    "data/spike_trader_active.json",
    # ── Additional systems from dashboard audit ──
    "quan_engine":          "quan_engine/data/active_signals.json",
    # BLOCKED 2026-03-16: alpha_engine_fast — 0% WR on holdout (6 trades, -3.22% PnL). Leak-free audit v3.
    # "alpha_engine_fast":    "alpha_engine/data/active_picks_fast.json",
    # BLOCKED 2026-03-15: multi_asset — 25.8% WR, 80 trades, PF 0.28. Proven loser.
    # "multi_asset":          "multi_asset/data/active_picks.json",
    # "multi_asset_institutional": "multi_asset/data/institutional_picks.json",
    "incubator_battleground": "battleground/data/incubator_signals.json",
    "agreement_alpha":      "ml_battleground/ensemble_data/agreement_alpha_picks.json",
    "mega_mutation":        "genome/data/mega_mutation_picks.json",
    "luxalgo_filters":      "battleground/data/luxalgo_active_picks.json",
    "chatgpt_combined":     "battleground/data/chatgpt_combined_signals.json",
    "stocks_competition":   "STOCKS/competition/forward_picks.json",
    "smart_money":          "smart_money/data/active_picks.json",
    "kol_consensus":        "predictions/data/kol_consensus_picks.json",
    # Removed dead systems: kimi_feb17 (no file), fc_crypto_pro (no file),
    # quantum_fusion (no file), crypto_gainer (empty file)
}

CONSENSUS_THRESHOLD: int = 2       # Minimum agreeing systems to emit a pick (was 3 — produced zero picks)
CONFIDENCE_BOOST: float = 0.03     # Reduced from 0.08: consensus adds modest certainty, not blind 99%
OUTPUT_PATH = pathlib.Path("data/aggregated_picks.json")
ROLLING_WR_SUSPEND: float = 0.45   # Suppress system when rolling WR < 45%

# ── Signal staleness guard (Round 7, Feb 26 2026) ──
# Discard signals older than MAX_SIGNAL_AGE_MIN minutes.
# GitHub Actions can have 5-15 min latency between scan and aggregation.
# Stale signals = entering at a price that has already moved.
MAX_SIGNAL_AGE_MIN: int = 45       # Discard picks older than 45 minutes

# Systems that are demoted (still run but excluded from consensus)
# Audit 2026-03-02: A (0/3=0% WR), B (0/13=0% WR), C (0/5=0% WR), D (dead), E (dead)
# ml_ensemble: 0/8=0% WR. signal_engine: 0/2 stalled. regime_terminal: dead.
# Updated 2026-03-15: added crypto_winners (39.6% WR, 48 trades, PF 0.30) — not in SOURCES but blocked from any dynamic loading.
DEMOTED_SYSTEMS = {
    "ml_bg_a", "ml_bg_b", "ml_bg_c", "ml_bg_d", "ml_bg_e",
    "ml_bg_ensemble", "signal_engine", "regime_terminal",
    "crypto_winners",        # BLOCKED 2026-03-15: 39.6% WR, 48 trades, PF 0.30
    "multi_asset",           # BLOCKED 2026-03-15: 25.8% WR, 80 trades, PF 0.28
    "multi_asset_institutional",  # BLOCKED 2026-03-15: same system as multi_asset
    "alpha_engine_fast",     # BLOCKED 2026-03-16: 0% WR on holdout, -3.22% PnL. Audit v3.
}

# ── Confirmer-only systems (2026-03-15) ──
# These systems keep their data feed running but their picks do NOT count as
# standalone votes in consensus. They only add weight when 2+ OTHER non-confirmer
# systems already agree on the same symbol+direction.
# kimi_riseoftheclaw: 36.7% WR, 270 trades, -219% PnL standalone.
#   Still valuable as a confirmer when 3+ other systems agree.
CONFIRMER_ONLY_SYSTEMS = {
    "kimi",
}

# ── Banned strategies (0% win rate from closed_picks.json audit 2026-03-02) ──
# Picks originating from these strategy names are filtered BEFORE consensus.
BANNED_STRATEGIES = {
    "smart_money_fvg",
    "fourier_cycle_detector",
    "exchange_netflow_reversal",
    "price_touch_recurrence",
    "halloween_effect",
    "altcoin_season_rotation",
    "momentum_mean_rev_blend",
    "cross_sectional_momentum",
}

# ── Data-driven bans from Strategy Health Monitor ──
# NOTE: _HEALTH_BANNED_PATH is set after REPO_ROOT is defined (below)
_HEALTH_BANNED_PATH = None

def _load_health_bans() -> set:
    """Load banned strategies from strategy_health monitor (merges with hardcoded)."""
    try:
        data = json.loads(_HEALTH_BANNED_PATH.read_text())
        extra = set(data.get("banned_strategies", []))
        if extra:
            print(f"  [HEALTH] Loaded {len(extra)} data-driven bans from banned_strategies.json")
        return extra
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()

def _load_health_incubator() -> set:
    """Load incubator strategies (tracked but excluded from consensus)."""
    try:
        data = json.loads(_HEALTH_BANNED_PATH.read_text())
        return set(data.get("incubator_strategies", []))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return set()

# ── Quality Gate Integration (Bundle-Baby forward-test validation) ──
# Strategies must have at least TESTING status (4+ checks) to participate in consensus.
# This prevents untested or poor-performing strategies from polluting Discord picks.
QUALITY_GATE_MIN_STATUS = "TESTING"  # Minimum: TESTING (4+ checks passed)
_GATE_STATUS_ORDER = ["COLLECTING", "TESTING", "MARGINAL", "PROVEN", "ELITE"]


def passes_quality_gate(
    strategy_name: str,
    forward_trades: int = 0,
    forward_win_rate: float = 0,
    forward_sharpe: float = 0,
    forward_max_dd: float = 0,
    forward_pnl: float = 0,
) -> bool:
    """Check if a strategy passes the minimum quality gate for consensus inclusion."""
    try:
        from bundle_baby_system import BundleBabySystem
        gate = BundleBabySystem.evaluate_gate({
            "forward_trades": forward_trades,
            "forward_win_rate": forward_win_rate,
            "forward_sharpe": forward_sharpe,
            "forward_max_dd": forward_max_dd,
            "forward_realized_pnl": forward_pnl,
        })
        status_idx = _GATE_STATUS_ORDER.index(gate["status"])
        min_idx = _GATE_STATUS_ORDER.index(QUALITY_GATE_MIN_STATUS)
        return status_idx >= min_idx
    except Exception:
        # If bundle system unavailable, allow through (graceful degradation)
        return True

# ── Max daily picks guard (prevents 88-pick days) ──
MAX_DAILY_PICKS: int = 999  # TESTING SPRINT: was 10, uncapped

# ── Correlation / Concentration Gate (Sharpe upgrade Feb 26 2026) ──
# Prevents correlated drawdowns by capping same-sector concurrent positions
MAX_CRYPTO_LONGS: int = 8           # Grok/Mercury audit 2026-03-16: restore caps (was 999 testing)
MAX_CRYPTO_SHORTS: int = 3          # SHORTs 22.5% WR in bull regime — keep tight
MAX_FOREX_PICKS: int = 4            # Forex picks lower priority
MAX_PER_SYMBOL: int = 1            # Max 1 consensus pick per symbol (dedup)

# ---------------------------------------------------------------------------
# Playbook Boost (from genome/results/trading_playbook.json)
# ---------------------------------------------------------------------------
# NOTE: The playbook metrics (Sharpe 60, 100% consistency) are DIRECTIONAL ONLY.
# They were derived from a winners-only dataset (survivorship bias).
# The REAL win rate from closed_picks battleground is 66.7%.
# However, the qualitative findings (which symbols, which patterns) are still
# useful as soft confidence adjustments.
# ---------------------------------------------------------------------------
PLAYBOOK_PREFERRED_SYMBOLS = {
    "TIAUSDT", "GRTUSDT", "XLMUSDT", "ADAUSDT", "ALGOUSDT",
    "APTUSDT", "DOTUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT",
    "LTCUSDT",
}
PLAYBOOK_SYMBOL_BOOST: float = 0.01   # Reduced from 0.03: survivorship-biased playbook should NOT inflate confidence
PLAYBOOK_RSI_PATTERNS = {"rsi", "connors", "mean_reversion"}
PLAYBOOK_RSI_BOOST: float = 0.01      # Reduced from 0.02: pattern-type preference is weak signal
PLAYBOOK_MAX_POSITIONS: int = 999      # TESTING SPRINT: was 5, uncapped

# Crypto symbols that are highly BTC-correlated (move together in crashes)
HIGH_BETA_CRYPTO = {
    "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT",
    "DOTUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT", "INJUSDT",
    "SUIUSDT", "RENDERUSDT", "TAOUSDT", "FETUSDT", "AAVEUSDT",
}
# Max high-beta-crypto longs (subset of MAX_CRYPTO_LONGS)
MAX_HIGH_BETA_LONGS: int = 3    # Grok/Mercury audit: cap high-beta exposure (was 999 testing)

# Root of the repository (for resolving relative paths)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_HEALTH_BANNED_PATH = REPO_ROOT / "strategy_health" / "data" / "banned_strategies.json"

# ---------------------------------------------------------------------------
# ML Systems identification (for ML Discord channel forwarding)
# ---------------------------------------------------------------------------
ML_SYSTEMS = {
    "crypto_ml_edge", "ml_bg_a", "ml_bg_b", "ml_bg_c",
    "ml_bg_d", "ml_bg_e", "ml_bg_ensemble", "claude_gainer",
    "ml_crypto_pred", "predictions", "claws_of_doom",
}

# System closed_picks paths for rolling WR computation
SYSTEM_CLOSED_PATHS: Dict[str, str] = {
    "mercury2":       "mercury2/data/closed_picks.json",
    "alpha_engine":   "alpha_engine/data/closed_picks.json",
    "claws_of_doom":  "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
    "ml_bg_a":        "ml_battleground/system_a_filter/data/closed_picks.json",
    "ml_bg_b":        "ml_battleground/system_b_regime/data/closed_picks.json",
}


def _send_ml_picks_summary(picks: List[Dict]):
    """Send ML-originated consensus picks to the dedicated ML Discord channel."""
    webhook = os.environ.get("DISCORD_ML_CHANNEL", "")
    if not webhook:
        return

    ml_picks = []
    for p in picks:
        sources = set(p.get("source_systems", []))
        ml_sources = sources & ML_SYSTEMS
        if ml_sources:
            ml_picks.append((p, ml_sources))

    if not ml_picks:
        return

    fields = []
    for p, ml_src in ml_picks[:10]:
        strategy = p.get("strategy", "")
        strat_str = f" | Strat: `{strategy}`" if strategy else ""
        fields.append({
            "name": f"{p.get('symbol', '?')} {p.get('direction', '?')}",
            "value": f"Conf: {p.get('confidence', 0):.0%} | ML: {', '.join(sorted(ml_src))}{strat_str}",
            "inline": False,
        })

    payload = {
        "username": "ML Pick Monitor",
        "embeds": [{
            "title": f"ML Systems Consensus: {len(ml_picks)} pick(s)",
            "color": 0x8B5CF6,
            "fields": fields[:25],
            "footer": {"text": "Cross-System Aggregator - ML picks"},
        }]
    }

    try:
        import requests as req
        req.post(webhook, json=payload, timeout=10)
        print(f"  [ML CHANNEL] Sent {len(ml_picks)} ML-originated picks")
    except Exception as e:
        print(f"  [ML CHANNEL] Failed to send: {e}")


def _compute_rolling_wr(sys_name: str, n: int = 20) -> Optional[float]:
    """Compute rolling win rate over last N closed picks for a system. Returns 0-1 or None."""
    rel_path = SYSTEM_CLOSED_PATHS.get(sys_name)
    if not rel_path:
        return None
    try:
        with open(REPO_ROOT / rel_path) as f:
            closed = json.load(f)
        if len(closed) < 5:  # need minimum sample
            return None
        recent = closed[-n:]
        wins = sum(1 for c in recent
                   if c.get("status", "").upper() in ("WON", "WIN", "CLOSED_TP")
                   or c.get("exit_reason", "").lower() in ("take_profit", "tp_hit")
                   or c.get("pnl_pct", c.get("net_pnl_pct", 0)) > 0)
        return wins / len(recent)
    except Exception:
        return None


# ── BTC 200d SMA regime cache ──
_btc_regime_cache: Dict = {}  # {"below_200d_sma": bool, "fetched_at": float}
_BTC_REGIME_CACHE_SEC: int = 3600  # 1 hour cache


def _get_btc_regime() -> Optional[bool]:
    """Check if BTC is below its 200-day SMA. Returns True if bearish (below), False if bullish, None on error.

    Uses Binance klines API to compute 200d SMA. Cached for 1 hour.
    """
    global _btc_regime_cache
    now = time.time()
    if _btc_regime_cache and (now - _btc_regime_cache.get("fetched_at", 0)) < _BTC_REGIME_CACHE_SEC:
        return _btc_regime_cache.get("below_200d_sma")

    try:
        import urllib.request
        # Fetch 200 daily candles from Binance (no API key needed)
        _SPOT_BASES = [
            "https://api.binance.com", "https://api1.binance.com",
            "https://api2.binance.com", "https://data-api.binance.vision",
            "https://api.binance.us",
        ]
        data = None
        for _base in _SPOT_BASES:
            try:
                url = f"{_base}/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=200"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                break  # success
            except Exception:
                continue
        if not data:
            return None

        if len(data) < 200:
            return None

        # Close prices are index 4 in Binance klines
        closes = [float(candle[4]) for candle in data]
        sma_200 = sum(closes) / len(closes)
        current_price = closes[-1]
        below = current_price < sma_200

        _btc_regime_cache = {
            "below_200d_sma": below,
            "sma_200": round(sma_200, 2),
            "btc_price": round(current_price, 2),
            "fetched_at": now,
        }
        regime_str = "BEARISH (below 200d SMA)" if below else "BULLISH (above 200d SMA)"
        print(f"  [BTC REGIME] BTC ${current_price:,.0f} vs 200d SMA ${sma_200:,.0f} -> {regime_str}")
        return below
    except Exception as e:
        print(f"  [BTC REGIME] Failed to fetch BTC 200d SMA: {e}")
        return None


def _load_json(path: pathlib.Path) -> List[Dict]:
    """Safely load a JSON file; return empty list on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            # Some systems wrap picks in {"active_picks": [...]} or similar
            if isinstance(data, dict):
                for key in ("active_picks", "activePicks", "picks", "signals",
                            "top", "winners", "open_picks", "forward_picks",
                            "open_trades", "forward_signals"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
            return []
    except Exception as exc:
        print(f"  [WARN] Could not load {path}: {exc}")
        return []


# ── Genome DNA pick normalizer ──
# Genome evolution engines produce picks with slightly different field names
# and sometimes missing entry/tp/sl. This ensures they match the aggregator's
# expected format before entering the consensus pipeline.
_GENOME_SYSTEMS = {"genome", "genome_genesis", "genome_legion", "genome_atlas"}

def _normalize_genome_picks(sys_name: str, picks: List[Dict]) -> List[Dict]:
    """Normalize genome engine picks to standard aggregator format.

    Handles:
    - Missing 'strategy' field → fallback to source_system or engine name
    - tp_pct / sl_pct → compute take_profit / stop_loss from entry_price
    - Missing direction → skip pick
    - Nested picks_by_engine (universal_picks) already flattened by _load_json
    """
    if sys_name not in _GENOME_SYSTEMS:
        return picks

    normalized = []
    for pick in picks:
        p = dict(pick)  # shallow copy to avoid mutating original

        # Ensure 'strategy' field exists
        if not p.get("strategy"):
            p["strategy"] = p.get("source_system", p.get("engine", sys_name))

        # Ensure 'direction' exists (required for consensus)
        if not p.get("direction") and not p.get("signal_type") and not p.get("signal"):
            continue  # skip picks without any direction indicator

        # Compute TP/SL from percentage fields when absolute prices are zero/missing
        entry = float(p.get("entry_price", p.get("entry", 0)) or 0)
        tp = float(p.get("take_profit", p.get("tp", 0)) or 0)
        sl = float(p.get("stop_loss", p.get("sl", 0)) or 0)

        if entry > 0 and tp == 0 and p.get("tp_pct"):
            tp_pct = float(p["tp_pct"])
            direction = str(p.get("direction", "")).upper()
            if direction in ("LONG", "BUY"):
                p["take_profit"] = round(entry * (1 + tp_pct), 8)
            elif direction in ("SHORT", "SELL"):
                p["take_profit"] = round(entry * (1 - tp_pct), 8)

        if entry > 0 and sl == 0 and p.get("sl_pct"):
            sl_pct = float(p["sl_pct"])
            direction = str(p.get("direction", "")).upper()
            if direction in ("LONG", "BUY"):
                p["stop_loss"] = round(entry * (1 - sl_pct), 8)
            elif direction in ("SHORT", "SELL"):
                p["stop_loss"] = round(entry * (1 + sl_pct), 8)

        # Ensure confidence is present and capped at 1.0
        if "confidence" not in p:
            p["confidence"] = 0.5  # neutral default
        try:
            p["confidence"] = min(float(p["confidence"]), 1.0)
        except (ValueError, TypeError):
            _cm = {"high": 0.85, "medium": 0.60, "low": 0.35, "very high": 0.95, "very low": 0.20}
            p["confidence"] = _cm.get(str(p["confidence"]).lower().strip(), 0.50)

        normalized.append(p)

    return normalized


# ── Spike/Gainer pick normalizer ──
# Systems like incubator_gainer, meme_scanner, and goldmine_meme use non-standard
# field names. This ensures they match the aggregator's expected format.
_SPIKE_GAINER_SYSTEMS = {
    "incubator_gainer", "goldmine_meme", "meme_scanner", "live_spike_trader",
}

def _normalize_spike_gainer_picks(sys_name: str, picks: List[Dict]) -> List[Dict]:
    """Normalize spike/gainer/meme system picks to standard aggregator format."""
    if sys_name not in _SPIKE_GAINER_SYSTEMS:
        return picks

    normalized = []
    for pick in picks:
        p = dict(pick)

        # Map 'is_buy' → 'direction' (incubator_gainer format)
        if "is_buy" in p and "direction" not in p:
            p["direction"] = "LONG" if p["is_buy"] else "SHORT"

        # Map 'verdict' → 'direction' (meme scanner format)
        if not p.get("direction") and p.get("verdict"):
            v = str(p["verdict"]).upper()
            if "BUY" in v:
                p["direction"] = "LONG"
            elif "SELL" in v or "SHORT" in v:
                p["direction"] = "SHORT"

        # Skip picks without direction
        if not p.get("direction"):
            continue

        # Map tp/sl shorthand to full names
        if "tp" in p and "take_profit" not in p:
            p["take_profit"] = p["tp"]
        if "sl" in p and "stop_loss" not in p:
            p["stop_loss"] = p["sl"]

        # Map 'price' → 'entry_price'
        if "price" in p and "entry_price" not in p:
            p["entry_price"] = p["price"]

        # Map 'price_at_signal' → 'entry_price' (meme winners)
        if "price_at_signal" in p and "entry_price" not in p:
            p["entry_price"] = float(p["price_at_signal"] or 0)

        # Map 'pair' → 'symbol' (meme winners: SUNDOG_USDT → SUNDOGUSDT)
        if "pair" in p and "symbol" not in p:
            p["symbol"] = p["pair"].replace("_", "")

        # Ensure strategy field
        if not p.get("strategy"):
            p["strategy"] = sys_name

        # Ensure source_system
        p["source_system"] = sys_name

        # Confidence normalization (0-1 range)
        _conf_v = p.get("confidence", p.get("composite", p.get("score", 50)))
        try:
            conf = float(_conf_v)
        except (ValueError, TypeError):
            _cm2 = {"high": 0.85, "medium": 0.60, "low": 0.35, "very high": 0.95, "very low": 0.20}
            conf = _cm2.get(str(_conf_v).lower().strip(), 0.50)
        if conf > 1:
            conf = conf / 100.0
        p["confidence"] = min(conf, 1.0)

        normalized.append(p)

    return normalized


def _normalize_symbol(raw: str) -> str:
    """Normalize symbol names so BTC-USD, BTCUSD, BTC/USDT, BTCUSDT all map to BTCUSDT."""
    s = raw.strip().upper()
    # Strip slashes: BTC/USDT -> BTCUSDT, ETH/USD -> ETHUSD
    s = s.replace("/", "")
    # Strip dashes: BTC-USD -> BTCUSD, SOL-USD -> SOLUSD
    s = s.replace("-", "")
    # Map common suffixes to USDT (the Binance standard)
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def _normalize_direction(raw: str) -> Optional[str]:
    """Normalize direction strings across systems."""
    d = str(raw).upper().strip()
    if d in ("LONG", "BUY"):
        return "LONG"
    if d in ("SHORT", "SELL"):
        return "SHORT"
    return None


def _portfolio_drawdown_check() -> tuple:
    """Check portfolio-level drawdown. Returns (ok, drawdown_pct, msg).

    Circuit breaker: if portfolio max DD > 15%, reduce all new picks to half size.
    If portfolio max DD > 25%, halt all new consensus picks.

    IMPORTANT: Excludes DEMOTED_SYSTEMS from the calculation so dead systems
    (e.g. system_a_filter at 0% WR / -37% PnL) don't poison the portfolio
    drawdown and block all output.
    """
    try:
        metrics_path = REPO_ROOT / "portfolio_tracker" / "data" / "portfolio_metrics.json"
        if not metrics_path.exists():
            return True, 0.0, "no metrics file yet"
        with open(metrics_path) as f:
            metrics = json.load(f)

        # Recalculate drawdown excluding demoted/dead systems
        systems = metrics.get("systems", {})
        if systems:
            excluded = DEMOTED_SYSTEMS | {"system_a_filter"}
            active_dds = []
            for sys_name, sys_data in systems.items():
                if sys_name in excluded:
                    continue
                active_dds.append(abs(sys_data.get("max_dd", sys_data.get("max_dd_pct", 0))))
            dd = max(active_dds) if active_dds else 0.0
        else:
            dd = abs(metrics.get("portfolio", {}).get("max_dd_pct", 0))

        if dd > 25:
            return False, dd, f"HALT: portfolio drawdown {dd:.1f}% > 25% — blocking all new picks"
        if dd > 15:
            return True, dd, f"WARNING: portfolio drawdown {dd:.1f}% > 15% — halving new pick sizes"
        return True, dd, "ok"
    except Exception:
        return True, 0.0, "metrics unavailable"


def _extract_strategy(pick: dict) -> str:
    """Extract strategy name from a pick, handling different source formats."""
    # Alpha Engine / general: "strategy" field
    strat = pick.get("strategy", pick.get("strategy_name", ""))
    if strat:
        return str(strat)
    # KIMI: "algorithm" or "algorithmName"
    algo = pick.get("algorithmName", pick.get("algorithm", ""))
    if algo:
        return str(algo)
    # DNA Genome: "strategy_dna" can be dict or string
    dna = pick.get("strategy_dna")
    if isinstance(dna, dict):
        return dna.get("strategy_id", dna.get("name", ""))
    if isinstance(dna, str) and dna:
        return dna
    return ""


# ---------------------------------------------------------------------------
# Strategy type classifier for hierarchical regime weighting
# ---------------------------------------------------------------------------

# Keywords used to classify a strategy name into one of the four signal types
# recognized by the hierarchical regime detector.
_STRATEGY_TYPE_KEYWORDS = {
    "trend_following": [
        "trend", "ema_stack", "breakout", "keltner", "donchian", "channel",
        "bos", "break_of_structure", "htf_structure", "hash_ribbon",
        "moving_average", "ma_cross", "sma", "ema", "supertrend",
    ],
    "mean_reversion": [
        "mean_reversion", "rsi_2", "rsi2", "connors", "bollinger_bounce",
        "fair_value_gap", "fvg", "ranging", "grid", "dca", "sopr",
        "mvrv", "nvt", "overvaluation",
    ],
    "momentum": [
        "momentum", "macd", "rsi_macd", "acceleration", "pump", "squeeze",
        "cross_sectional", "funding_rate", "carry", "oi_", "liquidation",
        "stablecoin", "whale", "volume_spike", "elder",
    ],
    "contrarian": [
        "contrarian", "reversal", "fear_greed", "sfp", "swing_failure",
        "capitulation", "cascade_bottom", "extreme", "pentoshi",
        "divergence", "sentiment",
    ],
}


def _classify_strategy_type(strategy_name: str) -> str:
    """
    Classify a strategy name into a signal type for hierarchical regime weighting.

    Returns one of: trend_following, mean_reversion, momentum, contrarian.
    Falls back to 'momentum' (most common in crypto) if no keywords match.
    """
    if not strategy_name:
        return "momentum"  # default for unknown strategies
    name_lower = strategy_name.lower()
    best_type = "momentum"
    best_score = 0
    for sig_type, keywords in _STRATEGY_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in name_lower)
        if score > best_score:
            best_score = score
            best_type = sig_type
    return best_type


# ---------------------------------------------------------------------------
# Conflict Winner Tracking — logs which systems were right when they disagree
# ---------------------------------------------------------------------------
CONFLICT_LOG = REPO_ROOT / "cross_aggregation" / "data" / "conflict_history.json"


def _fetch_single_equity_price(symbol: str) -> Optional[float]:
    """Fetch a single equity/stock price via yfinance with FMP fallback."""
    # 1. Try yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except ImportError:
        pass
    except Exception:
        pass

    # 2. Fallback: FMP free API
    try:
        url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey=demo"
        req = urllib.request.Request(url, headers={"User-Agent": "ConflictTracker/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if data and isinstance(data, list) and data[0].get("price"):
            return float(data[0]["price"])
    except Exception:
        pass

    return None


def _log_conflicts(conflicts: List[Dict]) -> None:
    """Append new conflicts to the conflict history log for winner tracking."""
    now_iso = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    history = []
    if CONFLICT_LOG.exists():
        try:
            history = json.loads(CONFLICT_LOG.read_text())
        except Exception:
            history = []

    for c in conflicts:
        # Deduplicate: skip if same symbol conflict was logged in last 4 hours
        recent = [h for h in history if h["symbol"] == c["symbol"]
                  and h.get("status") == "OPEN"]
        if recent:
            last_ts = recent[-1].get("logged_at", "")
            if last_ts:
                try:
                    last_dt = dt.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                    if (dt.datetime.now(dt.timezone.utc) - last_dt).total_seconds() < 4 * 3600:
                        continue
                except Exception:
                    pass

        # Fetch current price for later comparison
        price = None
        sym = c["symbol"]
        if sym.endswith(("USDT", "BUSD")):
            for base in ["https://api.binance.com", "https://api.binance.us"]:
                try:
                    url = f"{base}/api/v3/ticker/price?symbol={sym}"
                    req = urllib.request.Request(url, headers={"User-Agent": "ConflictTracker/1.0"})
                    data = json.loads(urllib.request.urlopen(req, timeout=5).read())
                    price = float(data.get("price", 0))
                    break
                except Exception:
                    continue
        else:
            price = _fetch_single_equity_price(sym)

        history.append({
            "symbol": sym,
            "logged_at": now_iso,
            "entry_price": price,
            "long_systems": c["long_systems"],
            "short_systems": c["short_systems"],
            "status": "OPEN",
            "winner_dir": None,
            "winner_systems": None,
            "resolved_at": None,
            "resolution_price": None,
            "pnl_pct": None,
        })

    # Resolve open conflicts: check if price moved >1.5% in either direction
    for entry in history:
        if entry.get("status") != "OPEN" or not entry.get("entry_price"):
            continue
        sym = entry["symbol"]
        current_price = None
        if sym.endswith(("USDT", "BUSD")):
            for base in ["https://api.binance.com", "https://api.binance.us"]:
                try:
                    url = f"{base}/api/v3/ticker/price?symbol={sym}"
                    req = urllib.request.Request(url, headers={"User-Agent": "ConflictTracker/1.0"})
                    data = json.loads(urllib.request.urlopen(req, timeout=5).read())
                    current_price = float(data.get("price", 0))
                    break
                except Exception:
                    continue
        else:
            current_price = _fetch_single_equity_price(sym)
        if not current_price:
            continue

        pnl_pct = ((current_price - entry["entry_price"]) / entry["entry_price"]) * 100
        # Resolve if >1.5% move or >48h elapsed
        age_hours = 0
        try:
            logged = dt.datetime.fromisoformat(entry["logged_at"].replace("Z", "+00:00"))
            age_hours = (dt.datetime.now(dt.timezone.utc) - logged).total_seconds() / 3600
        except Exception:
            pass

        if abs(pnl_pct) > 1.5 or age_hours > 48:
            entry["status"] = "RESOLVED"
            entry["resolved_at"] = now_iso
            entry["resolution_price"] = current_price
            entry["pnl_pct"] = round(pnl_pct, 4)
            if pnl_pct > 0.5:
                entry["winner_dir"] = "LONG"
                entry["winner_systems"] = entry["long_systems"]
            elif pnl_pct < -0.5:
                entry["winner_dir"] = "SHORT"
                entry["winner_systems"] = entry["short_systems"]
            else:
                entry["winner_dir"] = "DRAW"
                entry["winner_systems"] = []

    # Keep last 500 entries max
    history = history[-500:]
    CONFLICT_LOG.parent.mkdir(parents=True, exist_ok=True)
    CONFLICT_LOG.write_text(json.dumps(history, indent=2))

    # Print summary
    resolved = [h for h in history if h["status"] == "RESOLVED"]
    if resolved:
        system_wins = {}
        for r in resolved:
            for s in (r.get("winner_systems") or []):
                system_wins[s] = system_wins.get(s, 0) + 1
        if system_wins:
            top = sorted(system_wins.items(), key=lambda x: -x[1])[:5]
            print(f"  [CONFLICT TRACKER] {len(resolved)} resolved conflicts. Top winners: "
                  + ", ".join(f"{s}({w})" for s, w in top))


# ---------------------------------------------------------------------------
# Meta-Labeling Layer (rule-based, pre-ML)
# ---------------------------------------------------------------------------
# Runs AFTER consensus picks are assembled. Adds meta_label (APPROVED/BLOCKED)
# and meta_label_reason to each pick. Designed to filter the ~13% of consensus
# picks that lose despite agreement >= 3.
#
# Phase 1: rule-based heuristics. Phase 2 (future): replace with trained
# classifier once enough closed-trade data accumulates.

MAJOR_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"}


def _apply_meta_labels(picks: List[Dict]) -> List[Dict]:
    """Apply meta-labeling rules to consensus picks.

    Mutates each pick dict in-place by adding ``meta_label`` and
    ``meta_label_reason`` fields.  Returns the full list (blocked picks
    are *not* removed — downstream code can decide whether to act on
    the label).
    """
    blocked_count = 0
    boosted_count = 0

    for pick in picks:
        reasons: List[str] = []
        label = "APPROVED"

        # ── Extract features ──
        agreement = pick.get("agreement_count", 0)
        confidence = pick.get("confidence", 0.0)
        cons_tier = pick.get("consensus_tier", "MODERATE")
        direction = pick.get("direction", "LONG")
        symbol = pick.get("symbol", "")
        beta_score = pick.get("beta_score") or 0

        # Trust-tier features
        trust_tiers = pick.get("system_trust_tiers", {})
        has_proven = 0
        has_banned = 0
        if _HAS_DYNAMIC_TRUST and trust_tiers:
            for _sys, info in trust_tiers.items():
                tier = info.get("tier", "")
                if tier == TIER_PROVEN:
                    has_proven = 1
                if tier in (TIER_BANNED, TIER_UNTRUSTED):
                    has_banned = 1

        # Average system WR
        sys_wrs = pick.get("system_rolling_wrs", {})
        wr_values = [v for v in sys_wrs.values() if v is not None]
        avg_sys_wr = (sum(wr_values) / len(wr_values) / 100.0) if wr_values else 0.0

        direction_is_long = 1 if direction == "LONG" else 0
        symbol_is_major = 1 if symbol in MAJOR_SYMBOLS else 0
        cons_tier_num = {"MODERATE": 1, "STRONG": 2, "SUPER": 3}.get(cons_tier, 1)

        # Store extracted features on pick for transparency
        pick["meta_features"] = {
            "agreement_count": agreement,
            "confidence": round(confidence, 3),
            "consensus_tier": cons_tier_num,
            "has_proven_system": has_proven,
            "has_banned_system": has_banned,
            "avg_system_wr": round(avg_sys_wr, 4),
            "direction_is_long": direction_is_long,
            "symbol_is_major": symbol_is_major,
            "beta_score": beta_score,
        }

        # ── BLOCK rules ──
        # Rule 1: High-confidence trap — high conf with low agreement is suspect
        if agreement < 3 and confidence >= 0.95:
            label = "BLOCKED"
            reasons.append(f"high-confidence trap (agreement={agreement}, conf={confidence:.2f})")

        # Rule 2: Banned system tainting low-agreement consensus
        if has_banned and agreement <= 2:
            label = "BLOCKED"
            reasons.append("banned/untrusted system in low-agreement consensus")

        # Rule 3: Shorts need stronger agreement
        if direction_is_long == 0 and agreement < 4:
            label = "BLOCKED"
            reasons.append(f"SHORT with insufficient agreement ({agreement} < 4)")

        # ── BOOST rules (only if not blocked) ──
        if label == "APPROVED":
            # Boost 1: Proven system + strong agreement — CAPPED (consensus r=-0.075 on 1,879 trades)
            if has_proven and agreement >= 3:
                # Was: confidence * 1.05 — consensus bonus removed, high agreement = worse PnL
                pick["confidence"] = min(confidence * 1.0, 0.98)
                reasons.append(f"proven-system (no consensus boost, conf stays {confidence:.3f})")
                # boosted_count intentionally not incremented — no actual boost applied

            # Boost 2: Major symbol with good average WR
            if symbol_is_major and avg_sys_wr > 0.55:
                pick["confidence"] = min(pick["confidence"] * 1.03, 0.98)
                reasons.append(f"major-symbol WR boost +3% (avg_wr={avg_sys_wr:.2%})")
                boosted_count += 1

        if label == "BLOCKED":
            blocked_count += 1

        pick["meta_label"] = label
        pick["meta_label_reason"] = "; ".join(reasons) if reasons else "passed all meta-label checks"

    # ── Summary log ──
    approved = len(picks) - blocked_count
    print(f"\n  [META-LABEL] {len(picks)} picks evaluated: "
          f"{approved} APPROVED, {blocked_count} BLOCKED, {boosted_count} boosted")
    if blocked_count:
        for p in picks:
            if p.get("meta_label") == "BLOCKED":
                print(f"    BLOCKED {p['symbol']} {p['direction']}: {p['meta_label_reason']}")

    return picks


def aggregate() -> List[Dict]:
    """Run the aggregation pipeline and return consensus picks."""
    # ── Portfolio drawdown circuit breaker ──
    dd_ok, dd_pct, dd_msg = _portfolio_drawdown_check()
    if not dd_ok:
        print(f"\n  [CIRCUIT BREAKER] {dd_msg}")
        print(f"  [CIRCUIT BREAKER] Returning empty picks. Resume when drawdown recovers.")
        return []
    if dd_pct > 15:
        print(f"\n  [CIRCUIT BREAKER] {dd_msg}")

    # ── Audit trail: start run ──
    _audit_run_id = None
    _audit_raw_count = 0
    if _HAS_AUDIT:
        try:
            _audit_run_id = start_run(portfolio_dd=dd_pct)
        except Exception as e:
            print(f"  [AUDIT] Failed to start run: {e}")

    # ── Phase 1: Dynamic trust tier computation ──
    # Reset cache so each run loads fresh performance data
    _trust_tiers = {}
    _dynamically_blocked = set()
    _dynamically_demoted = {}  # system -> tier info
    if _HAS_DYNAMIC_TRUST:
        try:
            reset_dynamic_cache()
            _trust_tiers = get_all_system_tiers()

            # Log trust tier summary
            blocked_list = []
            demoted_list = []
            promoted_list = []
            for sys_name, info in _trust_tiers.items():
                tier = info["tier"]
                wr = info.get("win_rate")
                ct = info.get("closed_trades", 0)
                wr_str = f"{wr*100:.1f}%" if wr is not None else "N/A"

                if tier == TIER_BANNED:
                    _dynamically_blocked.add(sys_name)
                    blocked_list.append(f"{sys_name} (WR={wr_str}, {ct} trades)")
                elif tier == TIER_UNTRUSTED:
                    _dynamically_demoted[sys_name] = info
                    demoted_list.append(f"{sys_name} (WR={wr_str}, {ct} trades, 0.3x vote)")
                elif tier == TIER_PROVEN:
                    promoted_list.append(f"{sys_name} (WR={wr_str}, {ct} trades, 2.0x vote)")

            print(f"\n  [TRUST TIERS] Dynamic trust evaluation complete:")
            if blocked_list:
                print(f"    BLOCKED ({len(blocked_list)}): {', '.join(blocked_list)}")
            if demoted_list:
                print(f"    DEMOTED ({len(demoted_list)}): {', '.join(demoted_list)}")
            if promoted_list:
                print(f"    PROMOTED ({len(promoted_list)}): {', '.join(promoted_list)}")

        except Exception as e:
            print(f"  [TRUST TIERS] Error loading dynamic tiers, using static only: {e}")

    # Phase 3: Purge picks from banned systems
    _BANNED_PURGE = {"ml_bg_a", "ml_bg_b", "ml_bg_c", "ml_bg_ensemble",
                     "multi_asset", "multi_asset_institutional", "crypto_winners", "predictions"}

    # Stablecoin blacklist — these are pegged assets, never trade them
    _STABLECOIN_BLACKLIST = {"USDCUSDT", "FDUSDUSDT", "UUSDT", "DAIUSDT", "BUSDUSDT",
                              "TUSDUSDT", "USDPUSDT", "GUSDUSDT", "USDC-USD", "DAI-USD"}

    picks_by_symbol: defaultdict[str, List[Tuple[str, Dict]]] = defaultdict(list)
    system_stats = {}

    # Merge data-driven bans with hardcoded bans
    active_bans = BANNED_STRATEGIES | _load_health_bans()
    incubator_strats = _load_health_incubator()

    for sys_name, rel_path in SYSTEMS.items():
        full_path = REPO_ROOT / rel_path
        picks = _load_json(full_path)
        picks = _normalize_genome_picks(sys_name, picks)
        picks = _normalize_spike_gainer_picks(sys_name, picks)
        system_stats[sys_name] = len(picks)

        # Skip demoted systems from consensus (they still get loaded for stats)
        if sys_name in DEMOTED_SYSTEMS:
            print(f"  [DEMOTED] {sys_name} excluded from consensus (static blocklist)")
            system_stats[sys_name] = 0  # Don't count their picks
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter("", "", sys_name, "demoted_system",
                                  f"{sys_name} excluded from consensus (static)", _audit_run_id)
                except Exception:
                    pass
            continue

        # Phase 3: Skip banned systems (purge — picks never enter pipeline)
        if sys_name in _BANNED_PURGE:
            print(f"  [BANNED PURGE] {sys_name} purged — all picks discarded before consensus")
            system_stats[sys_name] = 0
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter("", "", sys_name, "banned_purge",
                                  f"{sys_name} in _BANNED_PURGE — zero picks admitted", _audit_run_id)
                except Exception:
                    pass
            continue

        # ── Phase 1: Dynamic trust-based blocking ──
        # Block systems proven to be losers from performance data
        if _HAS_DYNAMIC_TRUST and sys_name in _dynamically_blocked and sys_name not in DEMOTED_SYSTEMS:
            tier_info = _trust_tiers.get(sys_name, {})
            wr = tier_info.get("win_rate")
            ct = tier_info.get("closed_trades", 0)
            wr_str = f"{wr*100:.1f}%" if wr is not None else "N/A"
            print(f"  [TRUST BLOCK] {sys_name} dynamically blocked — WR={wr_str}, {ct} trades, tier=BANNED")
            system_stats[sys_name] = 0
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter("", "", sys_name, "trust_blocked",
                                  f"WR={wr_str}, {ct} trades, dynamically BANNED",
                                  _audit_run_id)
                except Exception:
                    pass
            continue

        # Rolling WR guard: suppress systems with degraded recent performance
        rwr = _compute_rolling_wr(sys_name)
        if rwr is not None and rwr < ROLLING_WR_SUSPEND:
            print(f"  [GUARD] {sys_name} rolling WR {rwr*100:.0f}% < {ROLLING_WR_SUSPEND*100:.0f}% — suppressed from consensus")
            system_stats[sys_name] = 0
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter("", "", sys_name, "wr_suppressed",
                                  f"rolling WR {rwr*100:.0f}% < {ROLLING_WR_SUSPEND*100:.0f}%",
                                  _audit_run_id)
                except Exception:
                    pass
            continue

        banned_count = 0
        for pick in picks:
            if not isinstance(pick, dict):
                continue  # skip malformed entries (strings, nulls, etc.)
            direction = _normalize_direction(
                pick.get("direction", pick.get("signal_type", pick.get("signal", "")))
            )
            if not direction:
                continue
            raw_symbol = str(pick.get("symbol", pick.get("pair", ""))).strip().upper()
            if not raw_symbol:
                continue

            # ── BUG FIX 2: Filter banned 0% WR strategies ──
            strategy = pick.get("strategy", pick.get("strategy_name", ""))
            if strategy and strategy in active_bans:
                banned_count += 1
                if _HAS_AUDIT and _audit_run_id:
                    try:
                        record_filter(raw_symbol, direction, sys_name,
                                      "banned_strategy", f"strategy '{strategy}' is banned",
                                      _audit_run_id)
                    except Exception:
                        pass
                continue

            if strategy and strategy in incubator_strats:
                if _HAS_AUDIT and _audit_run_id:
                    try:
                        record_filter(raw_symbol, direction, sys_name,
                                      "incubator_strategy",
                                      f"strategy '{strategy}' is in INCUBATOR (excluded from consensus)",
                                      _audit_run_id)
                    except Exception:
                        pass
                continue

            # ── Signal staleness guard ──
            # Discard picks older than MAX_SIGNAL_AGE_MIN to prevent stale entries
            pick_ts = pick.get("timestamp", pick.get("generated_at", pick.get("time", pick.get("scraped_at", pick.get("scan_time", pick.get("entry_date", ""))))))
            if pick_ts:
                try:
                    pick_dt = dt.datetime.fromisoformat(str(pick_ts).replace("Z", "+00:00"))
                    age_min = (dt.datetime.now(dt.timezone.utc) - pick_dt).total_seconds() / 60
                    if age_min > MAX_SIGNAL_AGE_MIN:
                        print(f"  [STALE] {raw_symbol} {direction} from {sys_name} — {age_min:.0f}min old > {MAX_SIGNAL_AGE_MIN}min limit, discarded")
                        if _HAS_AUDIT and _audit_run_id:
                            try:
                                record_filter(raw_symbol, direction, sys_name,
                                              "staleness", f"{age_min:.0f}min old > {MAX_SIGNAL_AGE_MIN}min",
                                              _audit_run_id)
                            except Exception:
                                pass
                        continue
                except (ValueError, TypeError):
                    pass  # Can't parse timestamp — allow through

            symbol = _normalize_symbol(raw_symbol)
            picks_by_symbol[symbol].append((sys_name, {**pick, "direction": direction}))

            # ── Audit: record raw pick ──
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_raw_pick(sys_name, pick, _audit_run_id)
                    _audit_raw_count += 1
                except Exception:
                    pass

        if banned_count:
            print(f"  [BANNED] {sys_name}: filtered {banned_count} picks from 0% WR strategies")

    # Apply consensus rule
    aggregated: List[Dict] = []
    conflicts: List[Dict] = []
    now_iso = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # ── LuxAlgo SHORT bias guard (Mar 16 2026) ──
    # LuxAlgo keeps firing SELL signals during uptrends (12/13 active picks SELL).
    # Pre-compute direction distribution across ALL luxalgo picks before the consensus loop.
    _LUXALGO_BIAS_FACTOR = 1.0  # default: no penalty
    _lux_all = [pick for entries in picks_by_symbol.values()
                for sys_name, pick in entries if sys_name == "luxalgo_filters"]
    if len(_lux_all) > 5:
        _lux_sell = sum(1 for p in _lux_all if p.get("direction") in ("SHORT", "SELL"))
        _lux_sell_pct = _lux_sell / len(_lux_all)
        if _lux_sell_pct > 0.8 or (1 - _lux_sell_pct) > 0.8:
            _LUXALGO_BIAS_FACTOR = 0.3
            _bias_dir = "SELL/SHORT" if _lux_sell_pct > 0.8 else "BUY/LONG"
            print(f"  [LUXALGO BIAS GUARD] {_lux_sell}/{len(_lux_all)} picks are {_bias_dir} "
                  f"({_lux_sell_pct*100:.0f}%) — direction-biased, vote weight reduced to 30%")

    # ── Beta Confluence Scorer: build market context ONCE ──
    _beta_scorer_inst = None
    _beta_market_ctx = None
    if _HAS_BETA_SCORER:
        try:
            _beta_scorer_inst = BetaConfluenceScorer()
            _beta_market_ctx = _beta_scorer_inst.build_market_context()
            print(f"  [BETA SCORER] Loaded OK. Market context: F&G={_beta_market_ctx.get('fear_greed_index')}, "
                  f"BTC 24h={_beta_market_ctx.get('btc_24h_pct', 0):.1f}%, "
                  f"regime={_beta_market_ctx.get('regime')}")
        except Exception as e:
            print(f"  [BETA SCORER] Failed to initialize: {e}", file=sys.stderr)
            _beta_scorer_inst = None
    else:
        print("  [BETA SCORER] Not available (_HAS_BETA_SCORER=False)")

    for symbol, entries in picks_by_symbol.items():
        # Fix 1: Skip stablecoins — pegged assets should never be traded
        if symbol in _STABLECOIN_BLACKLIST:
            print(f"  [STABLECOIN] {symbol} skipped — pegged asset blacklisted")
            continue

        # ── BUG FIX 1: Deduplicate by system_id ──
        # Count UNIQUE systems per direction, not raw pick count.
        # e.g. "predictions" system with 45 SOLUSDT picks = 1 vote, not 45.
        long_systems = set(e[0] for e in entries if e[1]["direction"] == "LONG")
        short_systems = set(e[0] for e in entries if e[1]["direction"] == "SHORT")
        # ── CONFIRMER_ONLY_SYSTEMS (2026-03-15) ──
        # Don't count confirmer-only systems toward the consensus threshold.
        # They can only add weight AFTER 2+ non-confirmer systems already agree.
        long_non_confirmer = long_systems - CONFIRMER_ONLY_SYSTEMS
        short_non_confirmer = short_systems - CONFIRMER_ONLY_SYSTEMS

        # ── Phase 1: Trust-weighted consensus counting (Mar 16 2026) ──
        # Instead of equal 1-vote-per-system, each system's vote is weighted
        # by its dynamic trust tier. PROVEN systems get 2.0 votes, UNTRUSTED
        # get 0.3, WATCH (untested) gets 1.0, BANNED gets 0.0.
        def _vote_weight_for(s: str) -> float:
            """Return vote weight for system s, with Phase 3 minimum-trade gate applied."""
            _vote_wt = get_dynamic_vote_weight(s) if _HAS_DYNAMIC_TRUST else 1.0
            # Phase 3: Minimum trade gate — heavily discount unproven systems
            _sys_info = _trust_tiers.get(s) if _HAS_DYNAMIC_TRUST else None
            sys_closed = _sys_info.get("closed_trades", 0) if _sys_info else 0
            if sys_closed < 10:
                _vote_wt *= 0.3  # heavily discount unproven systems
            # LuxAlgo SHORT bias guard: reduce influence when direction-biased
            if s == "luxalgo_filters" and _LUXALGO_BIAS_FACTOR < 1.0:
                _vote_wt *= _LUXALGO_BIAS_FACTOR
            return _vote_wt

        # ── System Group Dedup (Mar 16 2026) ──
        # rapid_fire + incubator_gainer are effectively the same signal source.
        # When they're the ONLY two "agreeing" systems, it's false consensus (41.8% WR).
        # Treat overlapping systems as one group for consensus counting.
        _SYSTEM_GROUPS = {
            "rapid_fire": "gainer_cluster",
            "incubator_gainer": "gainer_cluster",
            "alpha_engine": "alpha_cluster",
            "alpha_engine_fast": "alpha_cluster",
        }
        def _dedup_systems(systems):
            """Count unique system groups (not raw system names)."""
            groups = set()
            for s in systems:
                groups.add(_SYSTEM_GROUPS.get(s, s))  # ungrouped systems map to themselves
            return groups

        long_groups = _dedup_systems(long_non_confirmer)
        short_groups = _dedup_systems(short_non_confirmer)
        long_dedup_dropped = len(long_non_confirmer) - len(long_groups)
        short_dedup_dropped = len(short_non_confirmer) - len(short_groups)
        if long_dedup_dropped > 0 or short_dedup_dropped > 0:
            print(f"    [DEDUP] {symbol}: merged overlapping system groups "
                  f"(LONG: {len(long_non_confirmer)}->{len(long_groups)}, "
                  f"SHORT: {len(short_non_confirmer)}->{len(short_groups)})")

        if _HAS_DYNAMIC_TRUST:
            # Use deduplicated groups for weighted voting
            long_weighted = sum(_vote_weight_for(s) for s in long_non_confirmer
                                if s in long_groups or _SYSTEM_GROUPS.get(s, s) in long_groups)
            short_weighted = sum(_vote_weight_for(s) for s in short_non_confirmer
                                 if s in short_groups or _SYSTEM_GROUPS.get(s, s) in short_groups)
            # But cap at one vote per group
            _seen_groups_long = set()
            long_weighted = 0.0
            for s in long_non_confirmer:
                grp = _SYSTEM_GROUPS.get(s, s)
                if grp not in _seen_groups_long:
                    _seen_groups_long.add(grp)
                    long_weighted += _vote_weight_for(s)
            _seen_groups_short = set()
            short_weighted = 0.0
            for s in short_non_confirmer:
                grp = _SYSTEM_GROUPS.get(s, s)
                if grp not in _seen_groups_short:
                    _seen_groups_short.add(grp)
                    short_weighted += _vote_weight_for(s)

            # Confirmer-only systems only add weight if 2+ non-confirmer GROUPS already agree
            long_base_count = len(long_groups)
            short_base_count = len(short_groups)
            if long_base_count >= CONSENSUS_THRESHOLD:
                long_weighted += sum(_vote_weight_for(s)
                                     for s in (long_systems & CONFIRMER_ONLY_SYSTEMS))
            if short_base_count >= CONSENSUS_THRESHOLD:
                short_weighted += sum(_vote_weight_for(s)
                                      for s in (short_systems & CONFIRMER_ONLY_SYSTEMS))
            # Use weighted count for consensus threshold check
            # Threshold is still CONSENSUS_THRESHOLD (2), but now measured in weighted votes
            long_cnt = long_weighted
            short_cnt = short_weighted
            _trust_detail = {
                "long_weighted": round(long_weighted, 2),
                "short_weighted": round(short_weighted, 2),
                "long_raw": long_base_count,
                "short_raw": short_base_count,
            }
        else:
            long_cnt = len(long_non_confirmer)
            short_cnt = len(short_non_confirmer)
            _trust_detail = None

        if long_cnt >= CONSENSUS_THRESHOLD:
            chosen_dir = "LONG"
        elif short_cnt >= CONSENSUS_THRESHOLD:
            chosen_dir = "SHORT"
        else:
            # Log conflicts (multiple systems disagree)
            if long_cnt > 0 and short_cnt > 0:
                conflicts.append({
                    "symbol": symbol,
                    "long_systems": list(long_systems),
                    "short_systems": list(short_systems),
                })
            if _HAS_AUDIT and _audit_run_id:
                detail = ""
                if _trust_detail:
                    detail = (f"weighted LONG:{_trust_detail['long_weighted']:.1f} "
                              f"SHORT:{_trust_detail['short_weighted']:.1f} "
                              f"(raw {_trust_detail['long_raw']}/{_trust_detail['short_raw']})")
                else:
                    detail = f"LONG:{long_cnt} SHORT:{short_cnt}"
                try:
                    record_filter(symbol, "", "", "no_consensus",
                                  f"{detail} < threshold {CONSENSUS_THRESHOLD}",
                                  _audit_run_id)
                except Exception:
                    pass
            continue

        # Phase 3: Strict CONFIRMER_ONLY enforcement
        # Skip symbol if the winning direction is ONLY supported by confirmers (no real vote)
        _CONFIRMER_ONLY = {"kimi"}
        non_confirmer_longs = [s for s in long_systems if s not in _CONFIRMER_ONLY]
        non_confirmer_shorts = [s for s in short_systems if s not in _CONFIRMER_ONLY]

        if chosen_dir == "LONG" and len(non_confirmer_longs) < 1:
            print(f"  [CONFIRMER GATE] {symbol} LONG skipped — only confirmer systems voted (kimi-only)")
            continue
        if chosen_dir == "SHORT" and len(non_confirmer_shorts) < 1:
            print(f"  [CONFIRMER GATE] {symbol} SHORT skipped — only confirmer systems voted (kimi-only)")
            continue

        # Pick the best entry per unique system (deduplicate within system)
        # For each system, keep only the highest-confidence pick
        best_per_system: Dict[str, Tuple[float, Dict]] = {}
        for sys_name_e, pick_e in entries:
            if pick_e["direction"] != chosen_dir:
                continue
            _conf_raw = pick_e.get("confidence", pick_e.get("ml_score", 0.50))
            try:
                conf = float(_conf_raw)
            except (ValueError, TypeError):
                # Handle string confidence values like "HIGH", "LOW", "MEDIUM"
                _conf_map = {"high": 0.85, "medium": 0.60, "low": 0.35, "very high": 0.95, "very low": 0.20}
                conf = _conf_map.get(str(_conf_raw).lower().strip(), 0.50)
            if sys_name_e not in best_per_system or conf > best_per_system[sys_name_e][0]:
                best_per_system[sys_name_e] = (conf, pick_e)
        agreeing = [(sn, bp[1]) for sn, bp in best_per_system.items()]

        # Build per-system strategy mapping
        source_strategies = {}
        for sn, bp in best_per_system.items():
            strat = _extract_strategy(bp[1])
            if strat:
                source_strategies[sn] = strat

        # Score each agreeing system: confidence × WR × Sharpe weight × trust tier
        scored = []
        system_wrs = {}
        system_sharpe_wts = {}
        for sys_name, pick in agreeing:
            rwr = _compute_rolling_wr(sys_name)
            system_wrs[sys_name] = round(rwr * 100, 1) if rwr is not None else None
            wr_weight = rwr if rwr is not None else 0.5  # default 50% if unknown
            _raw_conf_val = pick.get("confidence", pick.get("ml_score", 0.50))
            try:
                raw_conf = float(_raw_conf_val)
            except (ValueError, TypeError):
                _conf_map = {"high": 0.85, "medium": 0.60, "low": 0.35, "very high": 0.95, "very low": 0.20}
                raw_conf = _conf_map.get(str(_raw_conf_val).lower().strip(), 0.50)

            # Sharpe-based system weight (from portfolio_tracker)
            if _HAS_SHARPE_WEIGHTS:
                sharpe_wt = get_system_weight(sys_name)
                system_sharpe_wts[sys_name] = round(sharpe_wt, 3)
            else:
                sharpe_wt = 0.15  # fixed neutral fallback (no portfolio data yet)

            # ── Phase 1: Trust tier multiplier for scoring ──
            # PROVEN systems get 1.5x score boost, UNTRUSTED get 0.5x penalty
            trust_mult = 1.0
            if _HAS_DYNAMIC_TRUST:
                ti = get_dynamic_system_tier(sys_name)
                trust_mult = ti.get("multiplier", 1.0)

            # ── Playbook boost: preferred symbols & RSI patterns ──
            playbook_adj = 0.0
            if symbol in PLAYBOOK_PREFERRED_SYMBOLS:
                playbook_adj += PLAYBOOK_SYMBOL_BOOST
            strategy_name = str(pick.get("strategy", pick.get("strategy_name", ""))).lower()
            if any(pat in strategy_name for pat in PLAYBOOK_RSI_PATTERNS):
                playbook_adj += PLAYBOOK_RSI_BOOST
            adj_conf = min(raw_conf + playbook_adj, 0.99)

            # Blend: confidence × (WR component) × (Sharpe component) × trust tier
            score = adj_conf * (0.5 + 0.5 * wr_weight) * (0.5 + 2.0 * sharpe_wt) * trust_mult
            # Build per-system confidence breakdown for transparency
            _breakdown = {
                "base": round(raw_conf * 100, 1),
                "wr_boost": round(max(0, (0.5 * wr_weight - 0.25)) * 100, 1),
                "sharpe_boost": round(max(0, (2.0 * sharpe_wt - 0.3)) * 100, 1),
                "trust_mult": round(trust_mult, 2),
                "playbook": round(playbook_adj * 100, 1),
                "consensus": 0,  # filled after scoring
                "final": 0,      # filled after scoring
            }
            scored.append((score, sys_name, pick, _breakdown))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][2]
        best_breakdown = scored[0][3] if len(scored[0]) > 3 else {}

        # ── Confidence = WR-anchored, not inflated (Fixed 2026-03-11) ──
        # Old: raw_conf + BOOST → always 99%. New: anchor to real system WR.
        # Fix 4: Normalize insane confidence values (some systems output raw scores >1)
        _raw_conf_v = best.get("confidence", best.get("ml_score", 0.50))
        try:
            _raw_conf = float(_raw_conf_v)
        except (ValueError, TypeError):
            _cm3 = {"high": 0.85, "medium": 0.60, "low": 0.35, "very high": 0.95, "very low": 0.20}
            _raw_conf = _cm3.get(str(_raw_conf_v).lower().strip(), 0.50)
        if _raw_conf > 1.0:
            if _raw_conf > 100:
                _raw_conf = min(0.95, _raw_conf / 100.0)
            elif _raw_conf > 10:
                _raw_conf = min(0.95, _raw_conf / 10.0)
            else:
                _raw_conf = min(0.95, _raw_conf)
            print(f"  [CONF NORMALIZE] {symbol}: confidence {best.get('confidence', best.get('ml_score', '?'))} normalized to {_raw_conf:.3f}")
            # Patch the best pick so downstream references see the normalized value
            best = dict(best)
            best["confidence"] = _raw_conf
        raw_conf = _raw_conf
        best_sys_name = scored[0][1]
        best_sys_wr = system_wrs.get(best_sys_name)  # real rolling WR (0-100 or None)

        # WR-anchored confidence: blend raw model confidence with actual system performance
        if best_sys_wr is not None and best_sys_wr > 0:
            wr_frac = best_sys_wr / 100.0  # e.g., 75% → 0.75
            # 60% weight on raw model confidence, 40% weight on real WR
            blended_conf = 0.6 * raw_conf + 0.4 * wr_frac
        else:
            # Unknown WR → penalize with uncertainty discount
            blended_conf = raw_conf * 0.7  # 30% discount for unproven system

        # Consensus boost: CAPPED AT 0 (Spearman r=-0.075 on 1,879 trades: high consensus = worse PnL)
        agree_count = long_cnt if chosen_dir == "LONG" else short_cnt
        consensus_boost = 0.0  # Was: CONFIDENCE_BOOST * min(agree_count - 1, 3) — removed, consensus anti-predictive
        boosted_conf = min(blended_conf + consensus_boost, 0.95)  # Hard cap at 95%, never 99%

        # Finalize confidence breakdown for the winning system
        wr_adjustment = round((blended_conf - raw_conf) * 100, 1) if best_sys_wr else round(-raw_conf * 0.3 * 100, 1)
        if best_breakdown:
            best_breakdown["wr_anchor"] = round((best_sys_wr or 0), 1)
            best_breakdown["wr_adjustment"] = wr_adjustment
            best_breakdown["consensus"] = round(consensus_boost * 100, 1)
            best_breakdown["final"] = round(boosted_conf * 100, 1)

        # Hierarchical regime weights (3-level HMM) for strategy-type-aware scoring. Added 2026-03-13
        # Applies macro/sector/micro regime multipliers based on strategy classification.
        # This runs AFTER the existing regime_router — it's an additional refinement layer.
        _hier_regime_mult = 1.0
        _hier_regime_info = None
        if _HAS_HIERARCHICAL_REGIME:
            try:
                _hier_result = get_regime_weights(symbol)
                _hier_weights = _hier_result.get("weights", {})
                _best_strategy = _extract_strategy(best)
                _strategy_type = _classify_strategy_type(_best_strategy)
                _hier_regime_mult = _hier_weights.get(_strategy_type, 1.0)
                boosted_conf = max(0.10, min(boosted_conf * _hier_regime_mult, 0.95))
                _hier_regime_info = {
                    "strategy_type": _strategy_type,
                    "multiplier": round(_hier_regime_mult, 4),
                    "regime_states": _hier_result.get("regime_states", {}),
                    "all_weights": _hier_weights,
                }
                if best_breakdown:
                    best_breakdown["hierarchical_regime"] = round((_hier_regime_mult - 1.0) * 100, 1)
                    best_breakdown["final"] = round(boosted_conf * 100, 1)
            except Exception as _hier_err:
                print(f"  [WARN] Hierarchical regime failed for {symbol}, using 1.0x: {_hier_err}",
                      file=sys.stderr)

        # Fix 5: Staleness decay — -5% confidence per hour after first hour (crypto)
        # Reuse the best pick's timestamp to compute age. Picks already passed the 45-min
        # staleness guard at ingestion, but consensus can still be built from recently-border
        # picks. Decay further reduces confidence on aging signals without hard-filtering them.
        _best_ts = best.get("timestamp", best.get("generated_at", best.get("time",
                   best.get("scraped_at", best.get("scan_time", best.get("entry_date", ""))))))
        if _best_ts:
            try:
                _best_dt = dt.datetime.fromisoformat(str(_best_ts).replace("Z", "+00:00"))
                _pick_age_min = (dt.datetime.now(dt.timezone.utc) - _best_dt).total_seconds() / 60
                if _pick_age_min > 60:
                    _hours_old = _pick_age_min / 60
                    _decay = max(0.5, 1.0 - 0.05 * (_hours_old - 1))  # floor at 50%
                    _old_conf = boosted_conf
                    boosted_conf *= _decay
                    print(f"  [STALENESS DECAY] {symbol}: {_pick_age_min:.0f}min old, decay={_decay:.2f}, conf {_old_conf:.3f}->{boosted_conf:.3f}")
            except (ValueError, TypeError):
                pass  # Can't parse timestamp — no decay

        # ── Phase 1: Per-system trust tier annotations ──
        _system_trust_info = {}
        if _HAS_DYNAMIC_TRUST:
            source_set = long_systems if chosen_dir == "LONG" else short_systems
            for s in source_set:
                ti = get_dynamic_system_tier(s)
                _system_trust_info[s] = {
                    "tier": ti["tier"],
                    "vote_weight": ti["vote_weight"],
                    "win_rate": ti.get("win_rate"),
                    "closed_trades": ti.get("closed_trades", 0),
                }

        # Compute agreement_count: use weighted for display, raw count for tier label
        _agree_weighted = long_cnt if chosen_dir == "LONG" else short_cnt
        if _trust_detail:
            _agree_raw = _trust_detail["long_raw"] if chosen_dir == "LONG" else _trust_detail["short_raw"]
        else:
            _agree_raw = _agree_weighted

        # Consensus tier uses weighted votes: SUPER >= 6, STRONG >= 3, else MODERATE
        if _agree_weighted >= 6:
            _cons_tier = "SUPER"
        elif _agree_weighted >= 3:
            _cons_tier = "STRONG"
        else:
            _cons_tier = "MODERATE"

        # Extract entry/tp/sl — use MOST RECENT pick's price (not first-found)
        # Stale picks (>48h) had wildly wrong entry prices (e.g., BTC $65K when actually $73K)
        def _find_field_recent(picks, *keys):
            """Find value from the most recently timestamped pick with non-zero value."""
            candidates = []
            for p in picks:
                for k in keys:
                    v = p.get(k)
                    if v and float(v) > 0:
                        ts = p.get("timestamp", p.get("generated_at", ""))
                        candidates.append((ts, float(v)))
                        break
            if not candidates:
                return 0
            # Sort by timestamp descending — most recent first
            candidates.sort(key=lambda x: x[0] if x[0] else "", reverse=True)
            return candidates[0][1]

        _all_dir_picks = [p for _, _, p, *_ in scored]
        # Filter out stale picks (>48h old) for entry price calculation
        _fresh_dir_picks = []
        for p in _all_dir_picks:
            ts = p.get("timestamp", p.get("generated_at", ""))
            if ts:
                try:
                    from datetime import datetime, timezone
                    ts_str = str(ts).strip()
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    pick_time = datetime.fromisoformat(ts_str)
                    if pick_time.tzinfo is None:
                        pick_time = pick_time.replace(tzinfo=timezone.utc)
                    age_h = (datetime.now(timezone.utc) - pick_time).total_seconds() / 3600
                    if age_h <= 48:
                        _fresh_dir_picks.append(p)
                        continue
                except Exception:
                    pass
            _fresh_dir_picks.append(p)  # keep if can't parse timestamp
        _pick_pool = _fresh_dir_picks if _fresh_dir_picks else _all_dir_picks
        _entry = _find_field_recent(_pick_pool, "entry", "entry_price", "entryPrice", "price")
        _tp = _find_field_recent(_pick_pool, "tp", "take_profit", "tp_price", "targetPrice", "target_price", "tp1_price", "tp_price_1_5")
        _sl = _find_field_recent(_pick_pool, "sl", "stop_loss", "sl_price", "stopPrice", "stop_price")

        unified = {
            "symbol": symbol,
            "direction": chosen_dir,
            "confidence": round(boosted_conf, 3),
            "entry": _entry,
            "tp": _tp,
            "sl": _sl,
            "source_systems": list(long_systems if chosen_dir == "LONG" else short_systems),
            "system_rolling_wrs": system_wrs,
            "agreement_count": round(_agree_weighted, 2),
            "agreement_count_raw": _agree_raw,
            "total_systems": len(entries),
            "consensus_tier": _cons_tier,
            "system_trust_tiers": _system_trust_info,
            "generated_at": now_iso,
            "strategy": _extract_strategy(best),
            "source_strategies": source_strategies,
            "confidence_breakdown": best_breakdown,
        }
        if _hier_regime_info:
            unified["hierarchical_regime"] = _hier_regime_info

        # Fix 2: Entry price sanity check — reject outlier entry vs. RECENT systems' entries
        # Tightened from 10% to 5% after BTC showed $65K entry when price was $73K (9% off, slipped through)
        _entry_val = unified.get("entry", 0)
        if _entry_val > 0:
            other_entries = [
                float(p.get("entry", p.get("entry_price", p.get("entryPrice", 0))) or 0)
                for _, p in entries
                if float(p.get("entry", p.get("entry_price", p.get("entryPrice", 0))) or 0) > 0
            ]
            if len(other_entries) >= 2:
                _sorted_entries = sorted(other_entries)
                median_entry = _sorted_entries[len(_sorted_entries) // 2]
                if median_entry > 0 and abs(_entry_val - median_entry) / median_entry > 0.05:
                    unified["entry"] = median_entry
                    print(f"  [ENTRY SANITY] {symbol}: corrected entry from {_entry_val:.4f} to median {median_entry:.4f} (>5% drift)")

        # ── Beta Confluence Score ──
        if _beta_scorer_inst is not None and _beta_market_ctx is not None:
            try:
                beta_result = _beta_scorer_inst.score_pick(unified, _beta_market_ctx, unified.get("system_trust_tiers"))
                unified["beta_score"] = beta_result["total"]
                unified["beta_breakdown"] = beta_result["breakdown"]
                unified["beta_qualified"] = beta_result["qualified"]
                if best_breakdown is not None:
                    best_breakdown["beta_total"] = beta_result["total"]
                    best_breakdown["beta_pillars"] = beta_result["breakdown"]
            except Exception as e:
                print(f"  [WARN] Beta scoring failed for {symbol}: {e}", file=sys.stderr)
                unified["beta_score"] = None
                unified["beta_breakdown"] = None
                unified["beta_qualified"] = False

        # ── Leverage Safety Gate ──
        try:
            from cross_aggregation.leverage_safety_gate import assess_leverage_safety
            _lev_market_ctx = {}
            if _beta_market_ctx is not None:
                _lev_market_ctx = _beta_market_ctx
            lev = assess_leverage_safety(unified, _lev_market_ctx)
            unified["max_safe_leverage"] = lev["max_safe_leverage"]
            unified["leverage_factors"] = lev["leverage_factors"]
            unified["leverage_warning"] = lev.get("warning", "")
        except Exception as _lev_err:
            print(f"  [WARN] Leverage safety gate failed for {symbol}: {_lev_err}", file=sys.stderr)
            unified["max_safe_leverage"] = 2  # conservative default
            unified["leverage_factors"] = {}
            unified["leverage_warning"] = ""

        aggregated.append(unified)

        # ── Audit: record consensus pick ──
        if _HAS_AUDIT and _audit_run_id:
            try:
                record_consensus_pick(unified, _audit_run_id)
            except Exception:
                pass

    # Fix 3: Symbol deduplication — max 1 active position per symbol per direction
    _seen_sym_dir = {}
    _deduped = []
    for p in aggregated:
        key = f"{p['symbol']}_{p['direction']}"
        if key in _seen_sym_dir:
            existing = _seen_sym_dir[key]
            if p.get("confidence", 0) > existing.get("confidence", 0):
                _deduped = [x for x in _deduped if f"{x['symbol']}_{x['direction']}" != key]
                _deduped.append(p)
                _seen_sym_dir[key] = p
        else:
            _seen_sym_dir[key] = p
            _deduped.append(p)
    if len(_deduped) < len(aggregated):
        print(f"  [DEDUP] Removed {len(aggregated) - len(_deduped)} duplicate symbol/direction entries")
    aggregated = _deduped

    # Phase 3: Beta gate — remove low-confluence picks
    if _HAS_BETA_SCORER:
        pre_filter_count = len(aggregated)
        aggregated = [p for p in aggregated if p.get("beta_score") is None or p.get("beta_score", 0) >= 40]
        filtered_count = pre_filter_count - len(aggregated)
        if filtered_count > 0:
            print(f"[BETA GATE] Filtered {filtered_count}/{pre_filter_count} picks with beta_score < 40", file=sys.stderr)

    # Grok critique fix: minimum confidence floor
    pre_conf_count = len(aggregated)
    aggregated = [p for p in aggregated if p.get("confidence", 0) >= 0.50]
    conf_filtered = pre_conf_count - len(aggregated)
    if conf_filtered > 0:
        print(f"  [CONFIDENCE GATE] Filtered {conf_filtered} picks with confidence < 50%")

    # Phase 3: Dynamic beta threshold — top 20% of picks are "qualified"
    beta_scores = [p["beta_score"] for p in aggregated if p.get("beta_score") is not None]
    if len(beta_scores) >= 5:
        beta_scores_sorted = sorted(beta_scores)
        percentile_80 = beta_scores_sorted[int(len(beta_scores_sorted) * 0.8)]
        dynamic_threshold = max(60, min(80, percentile_80))  # clamp between 60-80
        for p in aggregated:
            if p.get("beta_score") is not None:
                p["beta_qualified"] = p["beta_score"] >= dynamic_threshold
        print(f"[BETA] Dynamic threshold: {dynamic_threshold:.1f} (80th pctl of {len(beta_scores)} picks)", file=sys.stderr)

    # Grok critique fix: remove contradictions (same symbol, opposite directions)
    seen_symbols_dedup: Dict[str, Dict] = {}
    deduped: List[Dict] = []
    for p in aggregated:
        sym = p["symbol"]
        direction = p["direction"]
        if sym in seen_symbols_dedup:
            existing = seen_symbols_dedup[sym]
            if existing["direction"] != direction:
                # Contradiction: keep the one with higher confidence
                if p.get("confidence", 0) > existing.get("confidence", 0):
                    deduped = [x for x in deduped if x["symbol"] != sym]
                    deduped.append(p)
                    seen_symbols_dedup[sym] = p
                    print(f"  [CONTRADICTION] {sym}: kept {direction} ({p.get('confidence', 0):.0%}) over {existing['direction']} ({existing.get('confidence', 0):.0%})")
                continue
        else:
            seen_symbols_dedup[sym] = p
            deduped.append(p)
    if len(deduped) < len(aggregated):
        print(f"  [CONTRADICTION FILTER] Removed {len(aggregated) - len(deduped)} contradictory picks")
    aggregated = deduped

    # ── Correlation / Concentration Gate (Sharpe upgrade Feb 26 2026) ──
    # Sort by agreement_count desc so best consensus picks get through first
    aggregated.sort(key=lambda p: (p.get("agreement_count", 0), p.get("confidence", 0)), reverse=True)

    corr_filtered = []
    crypto_longs = 0
    crypto_shorts = 0
    high_beta_longs = 0
    forex_count = 0
    seen_symbols = set()

    surviving_corr = []
    for pick in aggregated:
        sym = pick.get("symbol", "")
        direction = pick.get("direction", "")
        is_crypto = sym.endswith("USDT") or sym.endswith("BTC") or sym.endswith("ETH")
        is_forex = any(sym.startswith(fx) for fx in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"))

        # Per-symbol dedup
        if sym in seen_symbols:
            corr_filtered.append({"symbol": sym, "direction": direction, "reason": "duplicate symbol"})
            continue
        seen_symbols.add(sym)

        # Crypto concentration limits
        if is_crypto:
            if direction == "LONG":
                if crypto_longs >= MAX_CRYPTO_LONGS:
                    corr_filtered.append({"symbol": sym, "direction": direction, "reason": f"crypto LONG cap ({MAX_CRYPTO_LONGS})"})
                    continue
                if sym in HIGH_BETA_CRYPTO and high_beta_longs >= MAX_HIGH_BETA_LONGS:
                    corr_filtered.append({"symbol": sym, "direction": direction, "reason": f"high-beta LONG cap ({MAX_HIGH_BETA_LONGS})"})
                    continue
                crypto_longs += 1
                if sym in HIGH_BETA_CRYPTO:
                    high_beta_longs += 1
            elif direction == "SHORT":
                if crypto_shorts >= MAX_CRYPTO_SHORTS:
                    corr_filtered.append({"symbol": sym, "direction": direction, "reason": f"crypto SHORT cap ({MAX_CRYPTO_SHORTS})"})
                    continue
                crypto_shorts += 1

        # Forex concentration limits
        if is_forex:
            if forex_count >= MAX_FOREX_PICKS:
                corr_filtered.append({"symbol": sym, "direction": direction, "reason": f"forex cap ({MAX_FOREX_PICKS})"})
                continue
            forex_count += 1

        surviving_corr.append(pick)

    if corr_filtered:
        print(f"\n  [CORRELATION GATE] Filtered {len(corr_filtered)} picks (concentration limits):")
        for cf in corr_filtered:
            print(f"    - {cf['symbol']} {cf['direction']}: {cf['reason']}")
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter(cf["symbol"], cf["direction"], "", "concentration_cap",
                                  cf["reason"], _audit_run_id)
                except Exception:
                    pass
        print(f"  [CORRELATION GATE] Surviving: {len(surviving_corr)} picks "
              f"(crypto: {crypto_longs}L/{crypto_shorts}S, forex: {forex_count})")

    aggregated = surviving_corr

    # ── BUG FIX 3: BTC 200d SMA regime bias adjustment ──
    # If BTC is below 200d SMA (bearish), require higher confidence for LONGs
    # and lower confidence for SHORTs. This corrects for the 40% LONG / 65% SHORT asymmetry.
    btc_bearish = _get_btc_regime()
    if btc_bearish is not None:
        regime_adj_filtered = []
        regime_adj_surviving = []
        LONG_BOOST = 0.1   # Raise LONG confidence threshold by 10% in bear regime
        SHORT_DISCOUNT = 0.1  # Lower SHORT threshold in bear regime

        for pick in aggregated:
            sym = pick.get("symbol", "")
            direction = pick.get("direction", "")
            conf = pick.get("confidence", 0.5)
            is_crypto = sym.endswith("USDT") or sym.endswith("BTC") or sym.endswith("ETH")

            if is_crypto and btc_bearish and direction == "LONG":
                # In bearish regime, require higher confidence for LONGs
                adjusted_threshold = 0.5 + LONG_BOOST  # 0.6 minimum
                if conf < adjusted_threshold:
                    regime_adj_filtered.append({
                        "symbol": sym, "direction": direction,
                        "reason": f"LONG conf {conf:.2f} < bearish threshold {adjusted_threshold:.2f}"
                    })
                    continue
                pick["regime_note"] = f"LONG in bear market (conf {conf:.2f} >= {adjusted_threshold:.2f})"

            if is_crypto and btc_bearish and direction == "SHORT":
                # Boost SHORT confidence in bearish regime
                pick["confidence"] = min(conf + SHORT_DISCOUNT, 0.99)
                pick["regime_note"] = f"SHORT boosted in bear market (+{SHORT_DISCOUNT:.0%})"

            if is_crypto and not btc_bearish and direction == "SHORT":
                # HARD BLOCK: ALL crypto shorts in bull regime (audit v3: ~30% WR historically)
                regime_adj_filtered.append({
                    "symbol": sym, "direction": direction,
                    "reason": f"HARD BLOCK: crypto SHORT in BULLISH regime (audit v3: ~30% WR)"
                })
                continue

            regime_adj_surviving.append(pick)

        if regime_adj_filtered:
            regime_label = "BEARISH" if btc_bearish else "BULLISH"
            print(f"\n  [BTC REGIME FILTER] {regime_label} — filtered {len(regime_adj_filtered)} low-conf counter-trend picks:")
            for rf in regime_adj_filtered:
                print(f"    - {rf['symbol']} {rf['direction']}: {rf['reason']}")
                if _HAS_AUDIT and _audit_run_id:
                    try:
                        record_filter(rf["symbol"], rf["direction"], "",
                                      "regime_mismatch", rf["reason"], _audit_run_id)
                    except Exception:
                        pass

        aggregated = regime_adj_surviving

    # ── BUG FIX 5: Max daily picks guard ──
    if len(aggregated) > MAX_DAILY_PICKS:
        # Keep the top N by agreement_count then confidence (already sorted)
        dropped = aggregated[MAX_DAILY_PICKS:]
        aggregated = aggregated[:MAX_DAILY_PICKS]
        print(f"\n  [MAX PICKS] Capped at {MAX_DAILY_PICKS} daily picks (dropped {len(dropped)}):")
        for d in dropped:
            print(f"    - {d['symbol']} {d['direction']} (agreement={d.get('agreement_count', '?')}, conf={d.get('confidence', '?')})")
            if _HAS_AUDIT and _audit_run_id:
                try:
                    record_filter(d["symbol"], d["direction"], "", "daily_cap",
                                  f"exceeded {MAX_DAILY_PICKS} daily limit", _audit_run_id)
                except Exception:
                    pass

    # ── Regime-strategy filter: suppress consensus picks that conflict with regime ──
    regime_data = None
    regime_filtered = []
    pre_regime_count = len(aggregated)

    if _HAS_REGIME_ROUTER:
        try:
            regime_data = get_current_regime()
            fng = regime_data.get("fng")
            reg = regime_data.get("regime", "UNKNOWN")
            btc_dom = regime_data.get("btc_dom_trend", "NEUTRAL")
            rsi = regime_data.get("rsi_14")

            surviving = []
            for pick in aggregated:
                sym = pick.get("symbol", "")
                direction = pick.get("direction", "")
                is_crypto = sym.endswith("USDT") or sym.endswith("BTC") or sym.endswith("ETH")

                if is_crypto and not should_generate_signal(direction, fng, reg, btc_dom, rsi):
                    regime_filtered.append(pick)
                    if _HAS_AUDIT and _audit_run_id:
                        try:
                            record_filter(sym, direction, "", "regime_mismatch",
                                          f"{direction} blocked by regime={reg}, F&G={fng}",
                                          _audit_run_id)
                        except Exception:
                            pass
                else:
                    pick["regime_aligned"] = True
                    surviving.append(pick)

            aggregated = surviving
        except Exception as e:
            print(f"  [WARN] Regime router failed, skipping filter: {e}", file=sys.stderr)

    # ── META-ROUTER: Unified consensus regime + strategy-level scoring ──
    meta_regime_data = None
    meta_regime_summary = None
    if _HAS_META_ROUTER and aggregated:
        try:
            meta_regime_data = get_consensus_regime()
            aggregated, meta_regime_summary = score_picks_by_regime(aggregated, meta_regime_data)

            cr = meta_regime_data.get("consensus_regime", "?")
            cc = meta_regime_data.get("confidence", 0)
            nd = meta_regime_data.get("detectors_available", 0)
            al = meta_regime_summary.get("aligned", 0)
            mi = meta_regime_summary.get("misaligned", 0)
            ne = meta_regime_summary.get("neutral", 0)
            print(f"\n  [META-ROUTER] Consensus: {cr} ({cc:.0%} confidence, {nd} detectors)")
            print(f"  [META-ROUTER] Picks: {al} aligned (+15%), {mi} misaligned (-30%), {ne} neutral")

            # Log individual detector votes
            breakdown = meta_regime_data.get("vote_breakdown", {})
            for v in breakdown.get("votes", []):
                print(f"    {v['detector']:25s} -> {v['regime']} (conf={v['confidence']:.0%})")
        except Exception as e:
            print(f"  [WARN] Meta-router failed, scoring skipped: {e}", file=sys.stderr)

    # ── Meta-Labeling Layer ──
    # Runs after ALL filters/regime adjustments. Adds meta_label + meta_label_reason
    # to each pick. Blocked picks remain in the list but are flagged for downstream
    # consumers to filter if desired.
    if aggregated:
        aggregated = _apply_meta_labels(aggregated)

    # Write output
    output_path = REPO_ROOT / OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Build trust tier summary for output
    _trust_summary = None
    if _HAS_DYNAMIC_TRUST and _trust_tiers:
        _trust_summary = {
            "blocked_systems": sorted(_dynamically_blocked),
            "demoted_systems": {k: {"tier": v["tier"], "win_rate": v.get("win_rate"),
                                     "closed_trades": v.get("closed_trades", 0)}
                                for k, v in _dynamically_demoted.items()},
            "total_evaluated": len(_trust_tiers),
        }

    output_obj = aggregated
    if regime_data or meta_regime_data or _trust_summary:
        output_obj = {
            "regime": regime_data,
            "meta_regime": meta_regime_data,
            "meta_regime_summary": meta_regime_summary,
            "trust_tiers": _trust_summary,
            "consensus_picks": aggregated,
            "regime_filtered_picks": [
                {"symbol": p["symbol"], "direction": p["direction"],
                 "reason": f"{p['direction']} blocked by regime={regime_data.get('regime')}, F&G={regime_data.get('fng')}"}
                for p in regime_filtered
            ] if regime_data else [],
        }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_obj, f, indent=2, sort_keys=False)

    # Forward ML-originated consensus picks to ML Discord channel
    try:
        _send_ml_picks_summary(aggregated)
    except Exception:
        pass  # Non-blocking — never fail the aggregator for Discord

    # Classify picks into tiers (ELITE / PROVEN / EXPERIMENTAL)
    if _HAS_CLASSIFIER and aggregated:
        try:
            system_stats_data = get_all_system_stats()
            elite_picks = []
            proven_picks = []
            experimental_picks = []
            for pick in aggregated:
                tier = classify_pick(pick, system_stats_data)
                pick["classification"] = tier
                if tier == "ELITE":
                    elite_picks.append(pick)
                elif tier == "PROVEN":
                    proven_picks.append(pick)
                else:
                    experimental_picks.append(pick)

            # Write classified picks
            data_dir = REPO_ROOT / "data"
            if elite_picks:
                with open(data_dir / "elite_picks.json", "w") as f:
                    json.dump(elite_picks, f, indent=2)
            if experimental_picks:
                with open(data_dir / "experimental_picks.json", "w") as f:
                    json.dump(experimental_picks, f, indent=2)

            print(f"\n  [CLASSIFIER] ELITE: {len(elite_picks)} | PROVEN: {len(proven_picks)} | EXPERIMENTAL: {len(experimental_picks)}")
        except Exception as e:
            print(f"  [CLASSIFIER] Error: {e}", file=sys.stderr)

    # Summary
    print(f"\n{'='*60}")
    print(f"CROSS-SYSTEM AGGREGATOR — {now_iso}")
    print(f"{'='*60}")
    print(f"Systems loaded: {sum(1 for v in system_stats.values() if v > 0)}/{len(SYSTEMS)}")
    for sys_name, count in system_stats.items():
        tier_label = ""
        if _HAS_DYNAMIC_TRUST and sys_name in _trust_tiers:
            ti = _trust_tiers[sys_name]
            tier_label = f" [{ti['tier']}]"
        status = f"{count} picks{tier_label}" if count > 0 else f"offline/empty{tier_label}"
        print(f"  {sys_name:20s} {status}")
    if _HAS_DYNAMIC_TRUST and _dynamically_blocked:
        print(f"\n  [TRUST] Dynamically blocked: {len(_dynamically_blocked)} systems")
    if _HAS_DYNAMIC_TRUST and _dynamically_demoted:
        print(f"  [TRUST] Dynamically demoted (0.3x vote): {len(_dynamically_demoted)} systems")
    print(f"\nSymbols analyzed: {len(picks_by_symbol)}")
    print(f"Consensus picks: {pre_regime_count} (threshold >= {CONSENSUS_THRESHOLD} systems)")
    if regime_data:
        print(f"\n  [REGIME ROUTER] F&G: {regime_data.get('fng')} ({regime_data.get('fng_classification')})")
        print(f"  [REGIME ROUTER] BTC: {regime_data.get('regime')} (ADX: {regime_data.get('adx')}, RSI: {regime_data.get('rsi_14')})")
        print(f"  [REGIME ROUTER] Longs: {'YES' if regime_data.get('longs_allowed') else 'NO'} | Shorts: {'YES' if regime_data.get('shorts_allowed') else 'NO'}")
        if regime_filtered:
            print(f"  [REGIME ROUTER] Filtered {len(regime_filtered)} picks (regime mismatch):")
            for p in regime_filtered:
                print(f"    - {p['symbol']} {p['direction']} (from {', '.join(p.get('source_systems', []))})")
        print(f"  [REGIME ROUTER] {len(aggregated)} picks survive after regime filter")
    if conflicts:
        print(f"Conflicts blocked: {len(conflicts)}")
        for c in conflicts[:5]:
            print(f"  {c['symbol']}: LONG={c['long_systems']} vs SHORT={c['short_systems']}")
        # ── Log conflicts for winner tracking ──
        _log_conflicts(conflicts)
    print(f"Output: {output_path}")
    print(f"{'='*60}\n")

    # ── Beta score tracker: persist pick scores for A/B analysis ──
    if _HAS_BETA_SCORER:
        try:
            tracker_path = os.path.join(os.path.dirname(__file__), "data", "beta_score_tracker.json")
            os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
            existing = []
            if os.path.exists(tracker_path):
                with open(tracker_path) as f:
                    existing = json.load(f).get("picks", [])
            for p in aggregated:
                if p.get("beta_score") is not None:
                    existing.append({
                        "symbol": p["symbol"], "direction": p["direction"],
                        "timestamp": p["generated_at"], "production_score": p["confidence"],
                        "beta_score": p["beta_score"], "beta_breakdown": p["beta_breakdown"],
                        "beta_qualified": p["beta_qualified"], "outcome": None, "outcome_timestamp": None,
                    })
            existing = existing[-2000:]
            with open(tracker_path, "w") as f:
                json.dump({"picks": existing, "summary": {}}, f, indent=2)
        except Exception as e:
            print(f"  [WARN] Beta tracker write failed: {e}", file=sys.stderr)

    # ── Audit trail: finish run ──
    if _HAS_AUDIT and _audit_run_id:
        try:
            finish_run(_audit_run_id, consensus_count=len(aggregated),
                       systems_loaded=sum(1 for v in system_stats.values() if v > 0),
                       raw_count=_audit_raw_count)
            print(f"  [AUDIT] Run {_audit_run_id[:8]}... logged: {_audit_raw_count} raw, {len(aggregated)} consensus")
        except Exception as e:
            print(f"  [AUDIT] Failed to finish run: {e}")
        # Flush WAL to main DB file so git picks up changes
        try:
            from audit_trail.db import get_connection, close as audit_close
            conn = get_connection()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            audit_close()
            print("  [AUDIT] WAL checkpoint + close done")
        except Exception as e:
            print(f"  [AUDIT] WAL checkpoint warning: {e}")

    return aggregated


if __name__ == "__main__":
    try:
        aggregate()
    except Exception as exc:
        try:
            from cross_aggregation.discord_notify import send_job_failure
            send_job_failure("Cross-Aggregator", "aggregation_run", str(exc))
        except Exception:
            pass
        raise

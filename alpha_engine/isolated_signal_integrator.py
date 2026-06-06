#!/usr/bin/env python3
"""
Isolated Signal Integrator
============================
Pulls picks from ALL isolated crypto signal sources and normalizes them
into the alpha_engine standard pick format for integration into the main pipeline.

Sources:
  1. quan_engine/data/active_signals.json        (key: "active_picks")
  2. crypto_ml_edge/data/active_picks.json        (key: "picks")
  3. genome/data/active_picks.json                (top-level list)
  4. genome/data/contrarian_active_picks.json      (key: "picks")
  5. regime_terminal/data/active_signals.json      (key: "signals")
  6. battleground/data/luxalgo_active_picks.json   (top-level list)
  7. rapid_fire_data/active_picks.json             (top-level list)
  8. alpha_engine/data/ml_reviver_picks.json      (top-level list)
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from alpha_engine.strategy_blocklist import is_blocked_pick, pick_block_reason
except ImportError:
    try:
        from strategy_blocklist import is_blocked_pick, pick_block_reason
    except ImportError:
        def is_blocked_pick(_pick): return False
        def pick_block_reason(_pick): return ""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

STABLECOINS = {
    "USDTUSDT", "USDCUSDT", "BUSDUSDT", "DAIUSDT", "TUSDUSDT",
    "USDPUSDT", "FDUSDUSDT", "EURUSDT", "PYUSDUSDT",
    "USDT-USD", "USDC-USD", "BUSD-USD", "DAI-USD", "TUSD-USD",
}

MIN_CONFIDENCE = 0.50  # Lowered from 0.60: quan_engine 0.50-0.59 band has BEST WR (36.7%)


# ---------------------------------------------------------------------------
# Per-symbol concurrency cap (4-AI panel P0 verdict, 2026-04-29)
# ---------------------------------------------------------------------------
# reports/doge_cluster_investigation_2026_04_29.md +
# reports/findings_validation_synthesis_2026_04_29.md (Finding 2):
# quan_engine_scalp produced 272 strategy*symbol*day clusters with >=8
# concurrent stacked positions, totaling 5,293 closes / -960% sum pnl_pct.
# Worst: KASUSDT 79x on 2026-03-26 (-17.90%). Mechanism: stacked LONGs all
# hitting SL in same price band when the resolver sweeps hourly.
#
# Default 0 = uncapped (current behavior, back-compat). Operator flips to
# a positive integer (e.g., 1 or 2) to enable the cap.
def _read_concurrency_cap_env() -> int:
    """Read MAX_CONCURRENT_PER_SYMBOL env at call time (no module-level cache).

    Reading at call time keeps tests deterministic — they can set the env
    var with monkeypatch.setenv() and the next integrator run picks it up.
    Returns 0 (= uncapped) on any parse error or missing var.
    """
    raw = os.environ.get("MAX_CONCURRENT_PER_SYMBOL", "0")
    try:
        n = int(str(raw).strip())
        return n if n > 0 else 0
    except (TypeError, ValueError):
        return 0

# Source definitions: (file_path_relative_to_repo, json_key_or_None, source_name)
SOURCES: list[tuple[str, str | None, str]] = [
    ("quan_engine/data/active_signals.json", "active_picks", "quan_engine"),
    ("crypto_ml_edge/data/active_picks.json", "picks", "crypto_ml_edge"),
    ("genome/data/active_picks.json", None, "genome"),
    ("genome/data/contrarian_active_picks.json", "picks", "genome_contrarian"),
    ("regime_terminal/data/active_signals.json", "signals", "regime_terminal"),
    ("battleground/data/luxalgo_active_picks.json", None, "battleground_luxalgo"),
    ("battleground/data/active_picks.json", None, "battleground"),  # v100: Keltner/ATR strategies were orphaned
    ("rapid_fire_data/active_picks.json", None, "rapid_fire"),
    ("alpha_engine/data/ml_reviver_picks.json", None, "ml_reviver"),
    # --- Genome mutation pick files (previously untracked) ---
    ("genome/data/dna_winner_picks.json", "picks", "genome_mutations"),
    ("genome/data/macd_mutation_picks.json", "picks", "genome_mutations"),
    ("genome/data/pumpwatch_mutation_picks.json", "picks", "genome_mutations"),
    ("genome/data/signal_engine_mutation_picks.json", "picks", "genome_mutations"),
    ("genome/data/pumpwatch_v2_picks.json", "picks", "genome_mutations"),
    ("genome/data/rapid_fire_mutation_picks.json", "picks", "genome_mutations"),
    ("genome/data/confluence_mutation_picks.json", "picks", "genome_mutations"),
    ("genome/data/battleground_mutation_picks.json", "picks", "genome_mutations"),
    ("genome/data/mega_mutation_picks.json", "open_picks", "genome_mega_mutation"),
    ("genome/data/mutation_lab_picks.json", "picks", "genome_mutation_lab"),
    ("genome/data/momentum_scalp_picks.json", "picks", "genome_mutations"),
    # --- Predictions (social media / analyst predictions — self-tracked but isolated) ---
    ("predictions/data/active_predictions.json", None, "predictions"),
    # --- Revival picks (DNA-relaxed variants of top-performing dormant strategies) ---
    ("alpha_engine/data/revival_picks.json", "picks", "dna_revival"),
    # --- Claude Gainer ST (short-term prop strategies: fear_greed, atr_vol, etc.) ---
    ("claude_gainer_ml/tracker/short_term_active.json", None, "claude_gainer_st"),
    # --- TSMOM (Time-Series Momentum with Vol Scaling — academic Sharpe 1.12-2.17) ---
    ("alpha_engine/data/tsmom_picks.json", "picks", "tsmom_volscaled"),
    # --- Experimental New Strategies ---
    ("alpha_engine/new_strategies/active_picks.json", None, "experimental_new"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_kill_list() -> set[str]:
    """Load killed strategy names from core_whitelist.json.

    Respects protected_strategies / core_strategies / incubator_strategies:
    any strategy whose bare name appears in those groups is exempt from kill.
    """
    try:
        wl_path = Path(__file__).resolve().parent / "data" / "core_whitelist.json"
        with open(wl_path, encoding="utf-8") as f:
            wl = json.load(f)
        # Build protected set
        protected: set[str] = set()
        for grp in ("protected_strategies", "core_strategies", "incubator_strategies"):
            for s in wl.get(grp, []):
                if isinstance(s, str) and s.strip():
                    protected.add(s.strip().lower())
        killed = set()
        for s in wl.get("kill_list", []):
            bare = s.split("::", 1)[1].lower() if "::" in s else s.lower()
            if bare in protected:
                continue  # never kill protected strategies
            killed.add(s.lower())
            if "::" in s:
                killed.add(bare)
        return killed
    except Exception:
        return set()


def _safe_float(val: Any, default: float | None = None) -> float | None:
    """Convert a value to float, returning default for None/NaN/Inf."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _normalize_symbol(raw: str) -> str:
    """Normalize symbol to uppercase, handling -USD -> USDT convention."""
    s = raw.upper().strip()
    # Keep USDT symbols as-is
    if s.endswith("USDT"):
        return s
    # Convert -USD suffix (Yahoo-style) to USDT
    if s.endswith("-USD"):
        return s.replace("-USD", "USDT")
    return s


def _identify_asset_class(symbol: str) -> str:
    """Identify asset class based on symbol pattern."""
    s = symbol.upper()
    if s.endswith("USDT") or s.endswith("-USD"):
        return "CRYPTO"
    if s.endswith("=X"):
        return "FOREX"
    if s.endswith("=F"):
        return "FUTURES"
    if s in ("GC=F", "SI=F", "CL=F", "NG=F", "ZC=F", "ZW=F", "ZS=F", "HG=F", "PL=F"):
        return "COMMODITY"
    # Stocks: typically 3-5 characters, no special suffix
    if 1 <= len(s) <= 5 and s.isalpha():
        return "STOCKS"
    return "UNKNOWN"


def _map_db_asset_class_field(raw: Any) -> str | None:
    """Map predictions DB / registry asset_class string to integrator gate enum."""
    if raw is None or not isinstance(raw, str):
        return None
    x = raw.strip().lower()
    if not x:
        return None
    if x == "crypto":
        return "CRYPTO"
    if x in ("equity", "etf", "stock", "stocks"):
        return "STOCKS"
    if x == "forex":
        return "FOREX"
    if x in ("futures", "future"):
        return "FUTURES"
    if x in ("commodity", "commodities"):
        return "COMMODITY"
    return None


def _is_tradeable_asset(symbol: str) -> bool:
    """Check if symbol is an asset we support."""
    asset_class = _identify_asset_class(symbol)
    return asset_class != "UNKNOWN"


def _normalize_direction(raw: Any) -> str:
    """Normalize direction to LONG or SHORT."""
    if raw is None:
        return "LONG"
    d = str(raw).upper().strip()
    if d in ("LONG", "BUY"):
        return "LONG"
    if d in ("SHORT", "SELL"):
        return "SHORT"
    return "LONG"


def _normalize_confidence(val: Any) -> float | None:
    """Normalize confidence to 0.0-1.0 range."""
    f = _safe_float(val)
    if f is None:
        return None
    # Some sources use 0-100 scale (rapid_fire)
    if f > 1.0:
        f = f / 100.0
    return round(f, 4)


def _parse_quan_strategies(raw: Any) -> list[str]:
    """Normalize quan_engine agreement metadata into a clean strategy list."""
    if raw is None:
        return []
    if isinstance(raw, list):
        parts = raw
    else:
        parts = str(raw).replace("|", ",").replace("+", ",").split(",")
    cleaned: list[str] = []
    for part in parts:
        text = str(part).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _normalize_quan_strategy_name(raw_strategy: Any, mode: Any) -> str:
    """Collapse quan_engine metadata to stable strategy IDs."""
    strategy_text = str(raw_strategy or "").strip().lower()
    mode_text = str(mode or "").strip().lower()
    combined = f"{strategy_text} {mode_text}".strip()

    if combined.startswith("quan_engine_"):
        return combined.split()[0]
    if "position" in combined:
        return "quan_engine_position"
    if "swing" in combined:
        return "quan_engine_swing"
    if "scalp" in combined:
        return "quan_engine_scalp"
    return "quan_engine_consensus"


# ---------------------------------------------------------------------------
# Per-source normalizers
# ---------------------------------------------------------------------------

def _normalize_quan_engine(pick: dict) -> dict | None:
    """Normalize a quan_engine pick."""
    agreed_strategies = _parse_quan_strategies(pick.get("strategies_agreed"))
    quan_mode = str(pick.get("mode", "") or "").strip().upper()
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit")),
        "stop_loss": _safe_float(pick.get("stop_loss")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": _normalize_quan_strategy_name(pick.get("strategies_agreed"), quan_mode),
        "source_system": "quan_engine",
        "category": "crypto",
        "created_at": pick.get("entry_time", pick.get("created_at", "")),
        "source_strategies": {"quan_engine": agreed_strategies},
        "agreement_count": max(len(agreed_strategies), 1),
        "quan_mode": quan_mode.lower() or None,
        "trade_timeframe": quan_mode or None,
    }


def _normalize_crypto_ml_edge(pick: dict) -> dict | None:
    """Normalize a crypto_ml_edge pick."""
    symbol = pick.get("pair", pick.get("symbol", ""))
    return {
        "symbol": _normalize_symbol(symbol),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("tp_price")),
        "stop_loss": _safe_float(pick.get("sl_price")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("audit", {}).get("strategy_id", pick.get("source", "crypto_ml_edge")),
        "source_system": "crypto_ml_edge",
        "category": "crypto",
        "created_at": pick.get("signal_time", ""),
    }


def _normalize_genome(pick: dict) -> dict | None:
    """Normalize a genome pick."""
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction", pick.get("signal_type"))),
        "signal_type": _normalize_direction(pick.get("signal_type", pick.get("direction"))),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit")),
        "stop_loss": _safe_float(pick.get("stop_loss")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("strategy", pick.get("strategy_name", "genome")),
        "source_system": "genome",
        "category": "crypto",
        "created_at": pick.get("timestamp", pick.get("generated_at", "")),
    }


def _normalize_genome_contrarian(pick: dict) -> dict | None:
    """Normalize a genome contrarian pick."""
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": None,  # Contrarian picks lack TP/SL — will be enriched later
        "stop_loss": None,
        "confidence": _normalize_confidence(pick.get("confidence", pick.get("performance_score"))),
        "strategy": pick.get("strategy", "genome_contrarian"),
        "source_system": "genome_contrarian",
        "category": "crypto",
        "created_at": pick.get("timestamp", ""),
    }


def _normalize_regime_terminal(pick: dict) -> dict | None:
    """Normalize a regime_terminal signal."""
    ticker = pick.get("ticker", "")
    return {
        "symbol": _normalize_symbol(ticker),
        "direction": _normalize_direction(pick.get("signal")),
        "signal_type": _normalize_direction(pick.get("signal")),
        "entry_price": _safe_float(pick.get("price")),
        "take_profit": None,  # Regime terminal doesn't provide TP/SL
        "stop_loss": None,
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": f"regime_{pick.get('regime', 'unknown').lower().replace(' ', '_')}",
        "source_system": "regime_terminal",
        "category": pick.get("category", "crypto"),
        "created_at": "",
    }


def _normalize_battleground(pick: dict) -> dict | None:
    """Normalize a battleground/luxalgo pick."""
    direction = pick.get("direction", "")
    # luxalgo uses SELL for SHORT
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(direction),
        "signal_type": _normalize_direction(direction),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit")),
        "stop_loss": _safe_float(pick.get("stop_loss")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("strategy", "luxalgo_confluence"),
        "source_system": "battleground_luxalgo",
        "category": "crypto",
        "created_at": pick.get("created_at", pick.get("timestamp", "")),
    }



def _normalize_claude_gainer_st(pick: dict) -> dict | None:
    """Normalize a claude_gainer_st pick (short-term prop strategies)."""
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("tp_price_1_5", pick.get("tp_price_2_0"))),
        "stop_loss": _safe_float(pick.get("sl_price")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("strategy", "claude_gainer_st"),
        "source_system": "claude_gainer_st",
        "category": "crypto",
        "created_at": pick.get("scan_time", ""),
    }


def _normalize_rapid_fire(pick: dict) -> dict | None:
    """Normalize a rapid_fire pick."""
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("tp_price_1_5", pick.get("tp_price_2_0"))),
        "stop_loss": _safe_float(pick.get("sl_price")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("strategy", "rapid_fire"),
        "source_system": "rapid_fire",
        "category": "crypto",
        "created_at": pick.get("scan_time", ""),
    }


def _normalize_ml_reviver(pick: dict) -> dict | None:
    """Normalize (passthrough) an ml_reviver pick."""
    # Ensure standard fields exist
    pick["source_system"] = pick.get("source_system", "ml_reviver")
    pick["category"] = "CRYPTO"
    pick["asset_class"] = "CRYPTO"
    # Convert direction/signal_type if needed
    if "direction" in pick:
        pick["direction"] = _normalize_direction(pick["direction"])
    if "signal_type" in pick:
        pick["signal_type"] = _normalize_direction(pick["signal_type"])
    return pick


def _normalize_genome_mutations(pick: dict) -> dict | None:
    """Normalize a genome mutation pick (dna_winner, macd, pumpwatch, etc.)."""
    # Skip closed/resolved picks from mega_mutation tracker
    status = str(pick.get("status", "")).upper()
    if status in ("CLOSED", "RESOLVED", "TP_HIT", "SL_HIT", "EXPIRED"):
        return None
    # Genome mutations use signal_type=BUY/SELL or direction=LONG/SHORT
    direction = pick.get("direction", pick.get("signal", pick.get("signal_type")))
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(direction),
        "signal_type": _normalize_direction(direction),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit", pick.get("tp_price"))),
        "stop_loss": _safe_float(pick.get("stop_loss", pick.get("sl_price"))),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("strategy", pick.get("mutation_name", "genome_mutation")),
        "source_system": pick.get("source_system", "genome_mutations"),
        "category": "crypto",
        "created_at": pick.get("timestamp", pick.get("opened_at", pick.get("generated_at", ""))),
    }


def _normalize_genome_mega_mutation(pick: dict) -> dict | None:
    """Normalize a mega mutation open pick."""
    status = str(pick.get("status", "")).upper()
    if status in ("CLOSED", "RESOLVED", "TP_HIT", "SL_HIT", "EXPIRED"):
        return None
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("signal", pick.get("direction"))),
        "signal_type": _normalize_direction(pick.get("signal", pick.get("direction"))),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("tp_price")),
        "stop_loss": _safe_float(pick.get("sl_price")),
        "confidence": _normalize_confidence(pick.get("signal_strength", 0.70)),
        "strategy": f"mega_mut_{pick.get('mutation_name', 'unknown')}",
        "source_system": "genome_mega_mutation",
        "category": "crypto",
        "created_at": pick.get("opened_at", ""),
    }


def _normalize_genome_mutation_lab(pick: dict) -> dict | None:
    """Normalize a mutation lab pick."""
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit")),
        "stop_loss": _safe_float(pick.get("stop_loss")),
        "confidence": _normalize_confidence(pick.get("confidence")),
        "strategy": pick.get("strategy", "mutation_lab"),
        "source_system": "genome_mutation_lab",
        "category": "crypto",
        "created_at": pick.get("timestamp", pick.get("generated_at", "")),
    }


def _normalize_predictions(pick: dict) -> dict | None:
    """Normalize a social media / analyst prediction pick."""
    status = str(pick.get("status", "")).upper()
    if status in ("CLOSED", "RESOLVED", "EXPIRED", "TP_HIT", "SL_HIT",
                   "EXPIRED_WIN", "EXPIRED_LOSS"):
        return None
    predictor = pick.get("predictor_id", "unknown")
    platform = pick.get("platform", "social")
    # Prefer DB asset_class when present (from KOL registry); fallback to heuristic
    db_asset_class = pick.get("asset_class")
    category = db_asset_class.lower() if db_asset_class else "crypto"
    return {
        "symbol": _normalize_symbol(pick.get("symbol", "")),
        "direction": _normalize_direction(pick.get("direction")),
        "signal_type": _normalize_direction(pick.get("direction")),
        "entry_price": _safe_float(pick.get("entry_price")),
        "take_profit": _safe_float(pick.get("take_profit")),
        "stop_loss": _safe_float(pick.get("stop_loss")),
        "confidence": _normalize_confidence(pick.get("sentiment_score", 0.65)),
        "strategy": f"pred_{platform}/{predictor}",
        "source_system": "predictions",
        "category": category,
        "created_at": pick.get("scraped_at", ""),
    }


# Map source name -> normalizer function
_NORMALIZERS: dict[str, Any] = {
    "quan_engine": _normalize_quan_engine,
    "crypto_ml_edge": _normalize_crypto_ml_edge,
    "genome": _normalize_genome,
    "genome_contrarian": _normalize_genome_contrarian,
    "regime_terminal": _normalize_regime_terminal,
    "battleground_luxalgo": _normalize_battleground,
    "rapid_fire": _normalize_rapid_fire,
    "ml_reviver": _normalize_ml_reviver,
    "genome_mutations": _normalize_genome_mutations,
    "genome_mega_mutation": _normalize_genome_mega_mutation,
    "genome_mutation_lab": _normalize_genome_mutation_lab,
    "predictions": _normalize_predictions,
    "battleground": _normalize_battleground,
    "dna_revival": _normalize_genome,
    "claude_gainer_st": _normalize_claude_gainer_st,
    "experimental_new": _normalize_ml_reviver,  # Use same passthrough as ml_reviver
}


# ---------------------------------------------------------------------------
# Main integration function
# ---------------------------------------------------------------------------

def integrate_isolated_signals(existing_picks: list[dict]) -> list[dict]:
    """
    Load picks from all isolated crypto signal sources, normalize, filter,
    deduplicate against existing_picks, and return new picks ready for pipeline.

    Args:
        existing_picks: Current active picks in the alpha_engine pipeline.

    Returns:
        List of new normalized picks to add to the pipeline.
    """
    kill_list = _load_kill_list()

    # Build dedup key set from existing picks: (symbol, direction)
    existing_keys: set[tuple[str, str]] = set()
    for p in existing_picks:
        sym = p.get("symbol", "").upper()
        direction = _normalize_direction(p.get("direction", p.get("signal_type")))
        existing_keys.add((sym, direction))

    # ---- Per-symbol concurrency cap setup (4-AI panel P0, 2026-04-29) ----
    # See _read_concurrency_cap_env above. Default 0 = uncapped (back-compat).
    # Counts are scoped per (source_system, symbol) so each emitter is gated
    # against itself (the cluster pattern is intra-strategy, not cross-strategy).
    _max_concurrent = _read_concurrency_cap_env()
    _open_status = {"ACTIVE", "OPEN", "PENDING", "FORWARD_PAPER"}
    _per_source_symbol_open: dict[tuple[str, str], int] = {}
    if _max_concurrent > 0:
        for p in existing_picks:
            try:
                _src = str(p.get("source_system", "") or "").lower().strip()
                _sym = str(p.get("symbol", "") or "").upper().strip()
                if not _src or not _sym:
                    continue
                _stat = str(p.get("status", "ACTIVE") or "ACTIVE").upper().strip()
                if _stat not in _open_status:
                    continue
                key = (_src, _sym)
                _per_source_symbol_open[key] = _per_source_symbol_open.get(key, 0) + 1
            except Exception:
                # Defensive: never let stats accounting kill the integrator.
                continue

    new_picks: list[dict] = []
    stats: dict[str, dict[str, int]] = {}
    _capped_total = 0  # picks rejected by the per-symbol concurrency cap

    for rel_path, json_key, source_name in SOURCES:
        src_stats = {"loaded": 0, "passed": 0, "filtered": 0, "dupes": 0}
        stats[source_name] = src_stats

        file_path = REPO_ROOT / rel_path
        if not file_path.exists():
            continue

        # Load JSON
        try:
            with open(file_path, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"  [INTEGRATOR] Failed to load {rel_path}: {e}")
            continue

        # Extract picks list
        if json_key:
            picks_raw = raw.get(json_key, []) if isinstance(raw, dict) else []
        else:
            picks_raw = raw if isinstance(raw, list) else []

        if not isinstance(picks_raw, list):
            continue

        src_stats["loaded"] = len(picks_raw)
        normalizer = _NORMALIZERS.get(source_name)
        if not normalizer:
            continue

        for raw_pick in picks_raw:
            if not isinstance(raw_pick, dict):
                continue

            normalized = normalizer(raw_pick.copy())
            if not normalized:
                src_stats["filtered"] += 1
                continue

            symbol = normalized.get("symbol", "")
            direction = normalized.get("direction", "LONG")
            confidence = normalized.get("confidence")

            # --- Quality gates ---
            hinted = _map_db_asset_class_field(raw_pick.get("asset_class"))
            asset_class = _identify_asset_class(symbol)
            if source_name == "predictions" and hinted:
                asset_class = hinted
            elif asset_class == "UNKNOWN" and hinted:
                asset_class = hinted
            if asset_class == "UNKNOWN":
                src_stats["filtered"] += 1
                continue

            # Tag normalized pick with identified class
            normalized["asset_class"] = asset_class
            normalized["category"] = asset_class.lower()

            # No stablecoins for crypto
            if asset_class == "CRYPTO" and symbol in STABLECOINS:
                src_stats["filtered"] += 1
                continue

            # Confidence gate (0.60 minimum)
            if confidence is None or confidence < MIN_CONFIDENCE:
                src_stats["filtered"] += 1
                continue

            # Kill list check — coerce to str so None/int strategy values don't
            # silently bypass the isinstance guard (B8 fix 2026-05-01).
            strategy = str(normalized.get("strategy") or "").strip()
            if strategy.lower() in kill_list:
                src_stats["filtered"] += 1
                continue

            # System+strategy pair blocklist (B11 fix 2026-05-01).
            # `kill_list` above only matches bare strategy names; this catches
            # `_RETIRED_SYSTEM_STRATEGY_PAIRS` like ("rapid_fire","macd_rsi_confluence")
            # that wouldn't trigger on bare-name match. See
            # reports/24h_verification_2026_04_30.md §C: 2 BANNED picks leaked
            # through 11h post-kill because this check was missing.
            if is_blocked_pick({"strategy": strategy, "source_system": source_name}):
                src_stats["filtered"] += 1
                continue

            # Status check — skip closed/expired picks from source
            raw_status = raw_pick.get("status", "ACTIVE").upper()
            if raw_status in ("CLOSED", "EXPIRED", "CANCELLED", "HIT_TP", "HIT_SL"):
                src_stats["filtered"] += 1
                continue

            # --- Dedup against existing + already-added ---
            dedup_key = (symbol, direction)
            if dedup_key in existing_keys:
                src_stats["dupes"] += 1
                continue

            # --- Per-symbol concurrency cap (4-AI panel P0, 2026-04-29) ---
            # Default 0 = uncapped (back-compat). Reads MAX_CONCURRENT_PER_SYMBOL.
            # Closes Finding 2 in reports/findings_validation_synthesis_2026_04_29.md
            # and matches the recommendation in
            # reports/doge_cluster_investigation_2026_04_29.md.
            if _max_concurrent > 0:
                _src_sym_key = (source_name.lower(), symbol)
                _open_count = _per_source_symbol_open.get(_src_sym_key, 0)
                if _open_count >= _max_concurrent:
                    src_stats["filtered"] += 1
                    _capped_total += 1
                    continue

            # --- Tag and add ---
            normalized["source_integration"] = True
            normalized["original_source"] = source_name
            normalized["status"] = "ACTIVE"
            normalized["forward_validated"] = False

            # Ensure created_at has a value
            if not normalized.get("created_at"):
                normalized["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Backfill entry_time + timestamp at emit (4-AI panel, 2026-04-29):
            # Finding 5 reports 63% of closed picks lack entry_time, which
            # makes duplicate-emission vs stacked-position vs hourly-sweep
            # impossible to distinguish forensically. Stamp both fields here.
            _emit_ts = normalized.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            normalized.setdefault("entry_time", _emit_ts)
            normalized.setdefault("timestamp", _emit_ts)

            # Generate an ID if missing
            if not normalized.get("id"):
                # Avoid nested-quote f-string syntax (Python 3.11 incompatible
                # per PEP 701; only allowed on 3.12+). Build the hash key in a
                # separate statement so CI on 3.11 parses cleanly.
                _id_key = f"{symbol}{direction}{normalized.get('created_at', '')}"
                normalized["id"] = f"iso_{source_name}_{symbol}_{hash(_id_key) % 10**10}"

            existing_keys.add(dedup_key)
            # Track this emission against the concurrency cap (so multiple
            # new picks for the same source+symbol in a single integrator
            # run also obey the cap, not just picks vs already-active ones).
            if _max_concurrent > 0:
                _src_sym_key = (source_name.lower(), symbol)
                _per_source_symbol_open[_src_sym_key] = _per_source_symbol_open.get(_src_sym_key, 0) + 1
            new_picks.append(normalized)
            src_stats["passed"] += 1

    # Print summary
    total_loaded = sum(s["loaded"] for s in stats.values())
    total_passed = sum(s["passed"] for s in stats.values())
    total_filtered = sum(s["filtered"] for s in stats.values())
    total_dupes = sum(s["dupes"] for s in stats.values())

    print(f"  [INTEGRATOR] Scanned {len(SOURCES)} sources: "
          f"{total_loaded} loaded, {total_passed} passed, "
          f"{total_filtered} filtered, {total_dupes} dupes")
    if _max_concurrent > 0:
        print(
            f"  [INTEGRATOR] MAX_CONCURRENT_PER_SYMBOL={_max_concurrent} active; "
            f"{_capped_total} pick(s) rejected by per-symbol concurrency cap"
        )

    for src, s in stats.items():
        if s["loaded"] > 0:
            print(f"    {src}: {s['loaded']} loaded -> {s['passed']} passed "
                  f"({s['filtered']} filtered, {s['dupes']} dupes)")

    return new_picks


# ---------------------------------------------------------------------------
# CLI entry point (for standalone testing / workflow usage)
# ---------------------------------------------------------------------------

def main():
    """Run integrator standalone and print results as JSON."""
    import sys

    # Load existing active picks
    active_path = Path(__file__).resolve().parent / "data" / "active_picks.json"
    existing: list[dict] = []
    if active_path.exists():
        try:
            with open(active_path, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    print(f"[INTEGRATOR] Existing active picks: {len(existing)}")
    new_picks = integrate_isolated_signals(existing)
    print(f"[INTEGRATOR] New picks to integrate: {len(new_picks)}")

    if new_picks:
        # Write integration report
        report_path = Path(__file__).resolve().parent / "data" / "integration_report.json"
        report = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "existing_count": len(existing),
            "new_count": len(new_picks),
            "new_picks": new_picks,
        }
        # Sanitize NaN/None for JSON
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[INTEGRATOR] Report written to {report_path}")

    return new_picks


if __name__ == "__main__":
    main()

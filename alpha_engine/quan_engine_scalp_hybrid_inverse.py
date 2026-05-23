#!/usr/bin/env python3
"""
ALPHA_ENGINE -- quan_engine_scalp_hybrid_inverse (SANDBOX)
==========================================================
Hybrid symbol+direction mutation of the consensus strategy `quan_engine_scalp`,
deployed under Strategy Lifecycle Policy v1.1 Step 2 (MUTATE/INVERT) at
SANDBOX sizing (0.25x).

NOTE ON ARCHITECTURE
--------------------
`quan_engine_scalp` is NOT a single .py file -- it is a consensus engine that
aggregates votes from constituent strategies (see
`alpha_engine/isolated_signal_integrator.py:218-258` and `inject_quan.py`).
This mutation runs as a DOWNSTREAM filter/mutator over the parent's emitted
picks, NOT by editing the consensus engine.

Per-symbol direction matrix (see `alpha_engine/crypto_sandbox_policy.py`):
  - KEEP_LONG: TRXUSDT, TAOUSDT (only 2 symbols where parent wins)
  - INVERT (LONG->SHORT): MATICUSDT, SOLUSDT, DOTUSDT, ICPUSDT, ETHUSDT,
    BTCUSDT, ETCUSDT, RENDERUSDT, HYPEUSDT (9 chronic-loss symbols)
  - BLOCK: MATICUSDT (117/117 historical losses on parent LONG)

Backtest on M_HYBRID slice (n=414 trades after gating):
  WR 71.26%, PF 2.890, +50.49% PnL  (vs parent -83.76% on same 451 entries)

Execution guards (per AI review):
  - Reject fills with > 0.3% slippage from intended price
  - Reject if fill spans > 1.5x ATR (likely partial-fill / no liquidity)

Sandbox policy (per Strategy Lifecycle Policy v1.1):
  - 0.25x sizing
  - 50-trade live probation before any sizing review
  - Promotion floor: 200 fwd trades, WR>=60%, Wilson 95% LB>=55%, PF>=2.0,
    Sharpe>=1.0  (NOT auto-applied -- documented for human auditor)

Stdlib only. Windows UTF-8 safe.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("quan_engine_scalp_hybrid_inverse")

# ---------------------------------------------------------------------------
# Module identity & paths
# ---------------------------------------------------------------------------
STRATEGY_NAME       = "quan_engine_scalp_hybrid_inverse"
PARENT_STRATEGY     = "quan_engine_scalp"
INVERSE_SOURCE_TAG  = "inverse_quan_engine_scalp_hybrid"

ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR   = ENGINE_DIR / "data"
ACTIVE_PICKS_PATH  = DATA_DIR / "active_picks.json"
CLOSED_PICKS_PATH  = DATA_DIR / "closed_picks.json"
HYBRID_PICKS_PATH  = DATA_DIR / "quan_engine_scalp_hybrid_inverse_picks.json"

CLOSED_LOOKBACK_DAYS = 7

# ---------------------------------------------------------------------------
# Per-symbol direction matrix
# (Source of truth lives in crypto_sandbox_policy.py; mirrored here as
# constants so the module is testable in isolation if the policy module is
# unavailable. The two MUST stay in sync; tests verify equivalence.)
# ---------------------------------------------------------------------------
KEEP_LONG_SYMBOLS = frozenset({
    "TRXUSDT",
    "TAOUSDT",
})

INVERT_SYMBOLS = frozenset({
    "MATICUSDT",
    "SOLUSDT",
    "DOTUSDT",
    "ICPUSDT",
    "ETHUSDT",
    "BTCUSDT",
    "ETCUSDT",
    "RENDERUSDT",
    "HYPEUSDT",
})

BLOCK_SYMBOLS = frozenset({
    "MATICUSDT",
})

# ---------------------------------------------------------------------------
# Execution guards (AI review on Plan 5)
# ---------------------------------------------------------------------------
MAX_SLIPPAGE_PCT  = 0.003   # 0.3% max slippage from intended fill
MAX_FILL_ATR_MULT = 1.5     # Reject if fill spans > 1.5x ATR

# ---------------------------------------------------------------------------
# Sandbox sizing (Strategy Lifecycle Policy v1.1)
# ---------------------------------------------------------------------------
SANDBOX_SIZING_MULT = 0.25

# Inverse R:R inverts -- parent is 2:1, so inverse is ~1:2 by default.
# We keep TP and SL distances mirrored around entry (preserve absolute price
# distance per inverse_wrapper convention); cost assumption is baked into the
# backtest at 0.10% round-trip on Binance/OKX.
DEFAULT_TP_PCT = 0.025  # 2.5% TP fallback when ATR unavailable
DEFAULT_SL_PCT = 0.015  # 1.5% SL fallback when ATR unavailable
DEFAULT_TP_ATR_MULT = 2.0
DEFAULT_SL_ATR_MULT = 1.0


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _smart_round(value: float) -> float:
    """Round based on magnitude (match other strategy modules)."""
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _norm_direction(value: Any) -> str:
    s = str(value or "").strip().upper()
    if s in ("BUY", "LONG"):
        return "LONG"
    if s in ("SELL", "SHORT"):
        return "SHORT"
    return s


def _norm_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


# ---------------------------------------------------------------------------
# Direction-override decision (the core hybrid logic)
# ---------------------------------------------------------------------------
def decide_direction(
    symbol: str,
    parent_direction: str,
) -> Tuple[Optional[str], str]:
    """Decide what direction the hybrid mutation should emit for a given pick.

    Returns
    -------
    (new_direction, reason) where new_direction is "LONG", "SHORT", or None.
    None means BLOCK -- do not emit any pick for this symbol.

    Decision matrix:
      symbol in BLOCK_SYMBOLS                        -> (None, "block")
      symbol in KEEP_LONG_SYMBOLS  and parent LONG   -> ("LONG", "keep_long")
      symbol in KEEP_LONG_SYMBOLS  and parent SHORT  -> (None, "keep_long_skips_short")
      symbol in INVERT_SYMBOLS     and parent LONG   -> ("SHORT", "inverted")
      symbol in INVERT_SYMBOLS     and parent SHORT  -> ("LONG", "inverted")
      otherwise (symbol unmapped)                    -> (None, "unmapped")
    """
    sym = _norm_symbol(symbol)
    parent = _norm_direction(parent_direction)

    # 1. Hard block (highest precedence -- MATICUSDT is 117/117 loser on parent
    #    LONG and we never want native LONG OR an inverted SHORT until we have
    #    independent evidence it's tradeable).
    if sym in BLOCK_SYMBOLS:
        return (None, "block")

    # 2. KEEP_LONG: only emit if parent agrees on LONG
    if sym in KEEP_LONG_SYMBOLS:
        if parent == "LONG":
            return ("LONG", "keep_long")
        return (None, "keep_long_skips_non_long")

    # 3. INVERT: flip direction; supports both LONG->SHORT and SHORT->LONG
    if sym in INVERT_SYMBOLS:
        if parent == "LONG":
            return ("SHORT", "inverted")
        if parent == "SHORT":
            return ("LONG", "inverted")
        return (None, "invert_unknown_parent_direction")

    # 4. Symbol not in matrix -- mutation has no opinion, drop the pick
    return (None, "unmapped")


# ---------------------------------------------------------------------------
# Execution guards
# ---------------------------------------------------------------------------
def check_execution_guards(
    intended_price: float,
    fill_price: float,
    atr_at_entry: Optional[float],
    fill_high: Optional[float] = None,
    fill_low: Optional[float] = None,
) -> Tuple[bool, str]:
    """Apply max-slippage and max-fill-rate guards to a fill candidate.

    Returns (accepted, reason). `accepted=False` means the fill must be
    rejected and the pick voided.

    Parameters
    ----------
    intended_price : float
        The price the strategy wanted to fill at (signal price).
    fill_price : float
        The actual fill price reported by the exchange or simulator.
    atr_at_entry : Optional[float]
        ATR value at the entry bar; required for max-fill-rate guard. If None,
        the ATR guard is skipped (slippage guard still runs).
    fill_high, fill_low : Optional[float]
        High and low of the fill bar (or partial-fill range), used to compute
        the fill span. Both required for the ATR guard; otherwise skipped.
    """
    if intended_price <= 0:
        return (False, "invalid_intended_price")
    if fill_price <= 0:
        return (False, "invalid_fill_price")

    # 1. Max slippage cap
    slippage_pct = abs(fill_price - intended_price) / intended_price
    if slippage_pct > MAX_SLIPPAGE_PCT:
        return (False, f"slippage_{slippage_pct * 100:.3f}pct_exceeds_{MAX_SLIPPAGE_PCT * 100:.1f}pct")

    # 2. Max fill-rate guard (only if ATR + fill range available)
    if atr_at_entry is not None and atr_at_entry > 0 and fill_high is not None and fill_low is not None:
        fill_span = abs(float(fill_high) - float(fill_low))
        atr_mult = fill_span / float(atr_at_entry)
        if atr_mult > MAX_FILL_ATR_MULT:
            return (False, f"fill_span_{atr_mult:.2f}xATR_exceeds_{MAX_FILL_ATR_MULT:.1f}xATR")

    return (True, "accepted")


# ---------------------------------------------------------------------------
# TP/SL calculation for the mutated direction
# ---------------------------------------------------------------------------
def _compute_tp_sl(
    entry_price: float,
    new_direction: str,
    atr_val: Optional[float],
) -> Tuple[float, float]:
    """Return (take_profit, stop_loss) for the mutated direction.

    Uses ATR multipliers when available, falls back to fixed percentages.
    """
    if atr_val is not None and isinstance(atr_val, (int, float)) and atr_val > 0:
        tp_distance = float(atr_val) * DEFAULT_TP_ATR_MULT
        sl_distance = float(atr_val) * DEFAULT_SL_ATR_MULT
    else:
        tp_distance = entry_price * DEFAULT_TP_PCT
        sl_distance = entry_price * DEFAULT_SL_PCT

    if new_direction == "SHORT":
        tp = entry_price - tp_distance
        sl = entry_price + sl_distance
    else:
        tp = entry_price + tp_distance
        sl = entry_price - sl_distance

    return _smart_round(tp), _smart_round(sl)


# ---------------------------------------------------------------------------
# Pick mutation (single pick)
# ---------------------------------------------------------------------------
def mutate_pick(parent_pick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert a single parent quan_engine_scalp pick into the hybrid variant.

    Returns the mutated pick dict, or None if the symbol is BLOCK / unmapped /
    KEEP_LONG-but-not-LONG.
    """
    if not isinstance(parent_pick, dict):
        return None

    symbol = _norm_symbol(parent_pick.get("symbol"))
    if not symbol:
        return None

    parent_direction = _norm_direction(
        parent_pick.get("direction") or parent_pick.get("signal_type")
    )

    new_direction, reason = decide_direction(symbol, parent_direction)
    if new_direction is None:
        log.debug("Skipping %s: %s", symbol, reason)
        return None

    entry_price = parent_pick.get("entry_price")
    if not entry_price or float(entry_price) <= 0:
        return None
    entry_price = float(entry_price)

    atr_val = parent_pick.get("atr_at_entry")
    tp, sl = _compute_tp_sl(entry_price, new_direction, atr_val)
    if tp <= 0 or sl <= 0:
        log.warning("Invalid TP/SL for %s: TP=%.6f SL=%.6f", symbol, tp, sl)
        return None

    new_signal_type = "BUY" if new_direction == "LONG" else "SELL"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()
    pick_id = f"{STRATEGY_NAME}::{symbol}::{now_str}"

    mutated: Dict[str, Any] = dict(parent_pick)  # shallow copy preserves auxiliary fields
    mutated.update({
        "id":             pick_id,
        "strategy":       STRATEGY_NAME,
        "source_system":  INVERSE_SOURCE_TAG if reason == "inverted" else PARENT_STRATEGY,
        "symbol":         symbol,
        "category":       parent_pick.get("category", "crypto"),
        "signal_type":    new_signal_type,
        "direction":      new_direction,
        "entry_price":    _smart_round(entry_price),
        "entry_date":     now_str,
        "take_profit":    tp,
        "stop_loss":      sl,
        "status":         "OPEN",
        "exit_price":     None,
        "exit_date":      None,
        "exit_reason":    None,
        "pnl_pct":        None,
        "pnl_dollar":     None,
        "high_water_mark": None,

        # Sandbox sizing (Plan 5 / Strategy Lifecycle Policy v1.1)
        "sandbox_sizing_mult":  SANDBOX_SIZING_MULT,
        "trust_tier":           "SANDBOX",

        # Execution guard reference values (audit trail)
        "max_slippage_pct":     MAX_SLIPPAGE_PCT,
        "max_fill_atr_mult":    MAX_FILL_ATR_MULT,

        # Provenance / mutation audit trail
        "source_pick_id":       parent_pick.get("id"),
        "source_strategy":      PARENT_STRATEGY,
        "mutation_type":        "hybrid_symbol_direction",
        "mutation_reason":      reason,
        "parent_direction":     parent_direction,

        # Backtest provenance (M_HYBRID slice)
        "mutation_wr":          0.7126,
        "mutation_pf":          2.890,
        "mutation_trades":      414,

        "scan_timestamp":       now_iso,
    })

    # Compute / update R:R
    risk = abs(entry_price - sl)
    if risk > 0:
        rr = abs(tp - entry_price) / risk
        mutated["rr"] = round(rr, 3)
        mutated["risk_reward"] = mutated["rr"]

    return mutated


# ---------------------------------------------------------------------------
# Pipeline entry point (used by scanner.py)
# ---------------------------------------------------------------------------
def _candidate_parent_picks() -> List[Dict[str, Any]]:
    """Collect parent quan_engine_scalp picks from active + recent closed."""
    candidates: List[Dict[str, Any]] = []

    active = _load_json(ACTIVE_PICKS_PATH)
    if isinstance(active, list):
        for pick in active:
            if not isinstance(pick, dict):
                continue
            if pick.get("strategy") != PARENT_STRATEGY:
                continue
            if str(pick.get("status", "")).upper() != "OPEN":
                continue
            candidates.append(pick)

    if candidates:
        return candidates

    # Fallback: recently closed parent picks
    closed = _load_json(CLOSED_PICKS_PATH)
    if not isinstance(closed, list):
        return []

    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=CLOSED_LOOKBACK_DAYS)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
    except Exception:
        return []

    by_symbol: Dict[str, Dict[str, Any]] = {}
    for pick in closed:
        if not isinstance(pick, dict):
            continue
        if pick.get("strategy") != PARENT_STRATEGY:
            continue
        pick_date = pick.get("exit_date") or pick.get("entry_date") or ""
        if pick_date < cutoff_str:
            continue
        symbol = _norm_symbol(pick.get("symbol"))
        if not symbol:
            continue
        existing = by_symbol.get(symbol)
        if existing is None:
            by_symbol[symbol] = pick
        else:
            ex_date = existing.get("exit_date") or existing.get("entry_date") or ""
            if pick_date > ex_date:
                by_symbol[symbol] = pick

    return list(by_symbol.values())


def generate_picks(parent_picks: Optional[Iterable[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate hybrid mutation picks from a stream of parent picks.

    If `parent_picks` is None, the function reads from active_picks.json and
    falls back to recent closed_picks.json (7-day lookback).

    Returns a list of mutated pick dicts (may be empty).
    """
    if parent_picks is None:
        parent_picks = _candidate_parent_picks()

    out: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for parent_pick in parent_picks:
        mutated = mutate_pick(parent_pick)
        if mutated is None:
            continue
        if mutated["id"] in seen_ids:
            continue
        seen_ids.add(mutated["id"])
        out.append(mutated)

    return out


def run() -> List[Dict[str, Any]]:
    """Scanner entry point. Generate, persist, return mutation picks."""
    log.info("=== quan_engine_scalp_hybrid_inverse: scanning parent picks ===")

    new_picks = generate_picks()
    if not new_picks:
        log.info("No hybrid mutation picks generated this cycle")
        return []

    # Merge with existing OPEN hybrid picks
    existing = _load_json(HYBRID_PICKS_PATH)
    merged: List[Dict[str, Any]] = []
    if isinstance(existing, list):
        merged = [p for p in existing if isinstance(p, dict) and str(p.get("status", "")).upper() == "OPEN"]

    merged_ids = {p.get("id", "") for p in merged}
    for new_pick in new_picks:
        if new_pick["id"] not in merged_ids:
            merged.append(new_pick)

    _save_json(HYBRID_PICKS_PATH, merged)
    log.info(
        "Saved %d hybrid picks (%d new) to %s",
        len(merged), len(new_picks), HYBRID_PICKS_PATH,
    )
    return new_picks


__all__ = [
    "STRATEGY_NAME",
    "PARENT_STRATEGY",
    "KEEP_LONG_SYMBOLS",
    "INVERT_SYMBOLS",
    "BLOCK_SYMBOLS",
    "MAX_SLIPPAGE_PCT",
    "MAX_FILL_ATR_MULT",
    "SANDBOX_SIZING_MULT",
    "decide_direction",
    "check_execution_guards",
    "mutate_pick",
    "generate_picks",
    "run",
]


if __name__ == "__main__":
    picks = run()
    print(f"\n{STRATEGY_NAME}: {len(picks)} new pick(s) generated")
    for p in picks:
        print(
            f"  {p['symbol']:<12} {p['direction']:<5} @ {p['entry_price']} "
            f"-> TP {p['take_profit']} / SL {p['stop_loss']} "
            f"(reason={p.get('mutation_reason')}, sizing={p['sandbox_sizing_mult']}x)"
        )

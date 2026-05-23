"""
ALPHA_ENGINE -- Crypto Sandbox Policy
=====================================
Sandbox sizing + probation/promotion thresholds for CRYPTO strategies that
are deployed under the Strategy Lifecycle Policy v1.1 SANDBOX phase.

This is the crypto-side analogue of `non_crypto_policy.NON_CRYPTO_STRATEGY_POLICY`.
Strategies registered here are NOT auto-promoted -- the registry only documents
the criteria a downstream auditor (or the on-call quant) must verify before
lifting sandbox sizing.

References:
  - docs/STRATEGY_LIFECYCLE_POLICY.md (v1.1, 2026-04-17) -- Step 2 / Sandbox
  - updates/2026-04-17-quan-engine-scalp-mutation-investigation.md (M_HYBRID)
  - updates/2026-04-17-deferred-execution-plans.md (Plan 5)

Stdlib only. No imports from other alpha_engine modules to avoid cycles.
"""

from __future__ import annotations

from typing import Any, Dict


# ---------------------------------------------------------------------------
# Default sandbox sizing multiplier (per Strategy Lifecycle Policy v1.1)
# ---------------------------------------------------------------------------
DEFAULT_SANDBOX_SIZING_MULT: float = 0.25


# ---------------------------------------------------------------------------
# Promotion floor (per Strategy Lifecycle Policy v1.1, Step 2 / Sandbox)
# ---------------------------------------------------------------------------
# A sandbox strategy may be considered for promotion when ALL criteria are met.
# Promotion is NEVER automatic; this is a documentation / audit reference.
DEFAULT_PROMOTION_FLOOR: Dict[str, float] = {
    "min_forward_trades":  200,    # Raised from 50 per 3-AI review (statistical power)
    "min_wr":              0.60,
    "min_wilson_lb_95":    0.55,   # Wilson 95% CI lower bound on WR
    "min_pf":              2.0,
    "min_sharpe":          1.0,
    "max_dd_pct":          0.20,
}


# ---------------------------------------------------------------------------
# Auto-demotion triggers (per Strategy Lifecycle Policy v1.1)
# ---------------------------------------------------------------------------
DEFAULT_DEMOTION_TRIGGERS: Dict[str, float] = {
    "wr_below_over_n":          0.45,   # WR < 45% over `wr_below_window` trades
    "wr_below_window":          50,
    "drift_pp_after_n":         0.05,   # >5pp drift from sandbox baseline WR
    "drift_window":             100,
    "single_trade_loss_pct":    0.05,   # Single loss > 5% of account -> freeze
}


# ---------------------------------------------------------------------------
# Live probation gate (immediate post-deploy)
# ---------------------------------------------------------------------------
# Per Plan 5 commit instruction: hold sandbox sizing for the first 50 live
# trades; do NOT increase sizing until both this and the promotion floor pass.
DEFAULT_LIVE_PROBATION_TRADES: int = 50


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------
# Each entry MUST include: parent, mutation_type, status (always SANDBOX here),
# sandbox_sizing_mult, promotion_floor, demotion_triggers, backtest_*,
# rationale.
CRYPTO_SANDBOX_POLICY: Dict[str, Dict[str, Any]] = {
    "quan_engine_scalp_hybrid_inverse": {
        "parent":              "quan_engine_scalp",
        "mutation_type":       "hybrid_symbol_direction",
        "status":              "SANDBOX",
        "asset_class":         "crypto",

        # ---- Per-symbol direction matrix (from M_HYBRID backtest) ----
        # Only 2 symbols where parent LONG actually wins -- keep as-is
        "keep_long_symbols": [
            "TRXUSDT",     # parent WR 55.41% (n=74) -- WINNER
            "TAOUSDT",     # parent WR 39.29% (n=28), PF 7.296 -- WINNER
        ],
        # 9 chronic-loss symbols where parent LONG bleeds -- invert to SHORT
        "invert_symbols": [
            "MATICUSDT",   # parent WR 0.00% (n=117) -- catastrophic
            "SOLUSDT",     # parent WR 0.00% (n=14)
            "DOTUSDT",     # parent WR 17.65% (n=17)
            "ICPUSDT",     # parent WR 4.17%  (n=24) -- catastrophic
            "ETHUSDT",     # parent WR 22.22% (n=18)
            "BTCUSDT",     # parent WR 23.81% (n=42)
            "ETCUSDT",     # parent WR 25.00% (n=12)
            "RENDERUSDT",  # parent WR 27.59% (n=29)
            "HYPEUSDT",    # parent WR 21.28% (n=47)
        ],
        # MATICUSDT also blocked from native LONG (117/117 historical losses)
        "block_symbols": [
            "MATICUSDT",
        ],

        # ---- Sandbox sizing & promotion thresholds ----
        "sandbox_sizing_mult":      DEFAULT_SANDBOX_SIZING_MULT,    # 0.25x
        "live_probation_trades":    DEFAULT_LIVE_PROBATION_TRADES,  # 50
        "promotion_floor":          dict(DEFAULT_PROMOTION_FLOOR),
        "demotion_triggers":        dict(DEFAULT_DEMOTION_TRIGGERS),

        # ---- Execution guards (per AI review on Plan 5) ----
        "max_slippage_pct":   0.003,   # reject fills > 0.3% from intended price
        "max_fill_atr_mult":  1.5,     # reject if fill spans > 1.5x ATR

        # ---- Cost assumption used in M_HYBRID backtest ----
        "cost_assumption_pct": 0.001,  # 0.10% round-trip on Binance/OKX

        # ---- Backtest provenance (M_HYBRID slice) ----
        "backtest_trades":   414,
        "backtest_wr":       0.7126,
        "backtest_pf":       2.890,
        "backtest_pnl_pct":  50.49,
        "mutation_quality":  0.654,    # (0.7126 * 414) / 451 (per protocol §5)

        "created_at": "2026-04-17",
        "rationale": (
            "Parent quan_engine_scalp has strong contrarian edge (WR 21.29%, "
            "PF 0.251 on 451 closed picks; SL hit-rate 47%, TP only 15% -- "
            "fingerprint of a contrarian-edge strategy mislabeled as momentum). "
            "M_HYBRID inverts 9 chronic-loss symbols, keeps TRX/TAO LONG (only "
            "symbols where parent actually wins), blocks MATICUSDT entirely "
            "(117/117 losers). Backtest on 414 trades: WR 71.26%, PF 2.890, "
            "+50.49% PnL. Mutation Quality 0.654 (well above 0.10 floor). "
            "Awaiting 50-trade live probation before any sizing increase."
        ),
    },
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
def get_policy(strategy: str) -> Dict[str, Any] | None:
    """Return the sandbox policy entry for a strategy, or None if not registered."""
    return CRYPTO_SANDBOX_POLICY.get(strategy)


def get_sandbox_sizing_mult(strategy: str) -> float:
    """Return the sandbox sizing multiplier for a strategy.

    Falls back to 1.0 (full size) for non-sandbox strategies so callers can
    multiply unconditionally without branching.
    """
    entry = CRYPTO_SANDBOX_POLICY.get(strategy)
    if not entry:
        return 1.0
    return float(entry.get("sandbox_sizing_mult", DEFAULT_SANDBOX_SIZING_MULT))


def is_sandbox_strategy(strategy: str) -> bool:
    """True if `strategy` is registered as SANDBOX in the crypto policy."""
    entry = CRYPTO_SANDBOX_POLICY.get(strategy)
    return bool(entry) and entry.get("status") == "SANDBOX"


__all__ = [
    "CRYPTO_SANDBOX_POLICY",
    "DEFAULT_SANDBOX_SIZING_MULT",
    "DEFAULT_PROMOTION_FLOOR",
    "DEFAULT_DEMOTION_TRIGGERS",
    "DEFAULT_LIVE_PROBATION_TRADES",
    "get_policy",
    "get_sandbox_sizing_mult",
    "is_sandbox_strategy",
]

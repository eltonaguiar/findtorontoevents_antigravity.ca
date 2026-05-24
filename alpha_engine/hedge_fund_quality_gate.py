"""Hedge-fund-grade quality gate — per-asset-class rejection rules.

Opt-in sidecar. No existing code path calls this by default; wire it at the
execution step (not generation) per feedback_gate_at_execution_not_generation.

Rules derived from tools/edge_by_asset_class.py on the 3,500-row closed
ledger (audit_dashboard/data/dashboard_data.json). Full derivation and
statistics in reports/HEDGE_FUND_EDGE_FINDINGS_2026_04_22.md.

Typical use:

    from alpha_engine.hedge_fund_quality_gate import passes_hedge_fund_gate
    ok, reason = passes_hedge_fund_gate(pick)
    if not ok:
        skip(pick, reason=reason)

Every rejection returns a specific reason string so the rejection reason
propagates to the audit log and downstream dashboards.
"""
from __future__ import annotations

import os
from typing import Any

# ───────────────── CRYPTO rules ─────────────────
# These four symbols account for roughly 170 pct-pnl of the 195 pct-pnl
# lifetime drawdown on crypto (n=233 / 1650 = 14% of volume).
# 2026-04-28 expansion: LTCUSDT/TONUSDT added on the empirical PF<0.95, n>=20
# threshold per `reports/crypto_rsi4h_killzone_review_2026_04_28.md`. DOGEUSDT
# was already banned for the lifetime PF<0.50 reason; the review re-confirmed
# the threshold class. This expansion replaces the RSI-4h killzone (disabled
# below) which was operationally a writer-artifact symbol blocklist anyway.
CRYPTO_BANNED_SYMBOLS = frozenset({
    # Legacy low-liquidity / strategy-broken assets
    "DOGEUSDT", "OPUSDT", "LINKUSDT", "ADAUSDT",
    "LTCUSDT", "TONUSDT",
    # 2026-05-16 autopsy: confirmed meme/micro-cap drag — PF near 0, WR < 35%
    # across source systems per CRYPTO_AUTOPSY_2026_05_16.
    # ADV < $50M/day, high slippage, zero institutional footprint.
    "WIFUSDT",       # WIF (Dogwifhat) — meme coin, PF 0.42 in autopsy
    "PEPEUSDT",      # PEPE — pure meme, PF 0.31
    "BONKUSDT",      # BONK — Solana meme, PF 0.28
    "SHIBUSDT",      # SHIB — meme coin, marginally above DOGE (already banned)
    "FLOKIUSDT",     # FLOKI — meme coin
    "BOMEUSDT",      # BOME (Book of Meme) — meme coin
})
# Strategies with a large sample and realized negative PF.
CRYPTO_BANNED_STRATEGIES = frozenset({
    "macd_rsi_confluence",
})
# Confidence band that is the single worst performing bucket on crypto
# (882 picks, 53% of crypto volume, WR 29.9%, PF 0.69). Half-open interval.
CRYPTO_CONFIDENCE_DEAD_BAND = (0.60, 0.70)

# ───────────────── EQUITY rules ─────────────────
# Equity SHORTs are a tiny historical sample (n=4) and went 0/3. Equity LONG
# has realized PF 1.49, so the asymmetric rule matches the evidence.
EQUITY_ALLOWED_DIRECTIONS = frozenset({"LONG", "BUY"})
# 2026-05-16: AAPL un-banned. Original n=15/PF=0.69 ban was below 30-pick charter
# minimum. Strategy-specific evidence: rs-breakout-scout fwd_wr=73.0% (forward_validated=True).
# Recent closed n=17, PF=1.03 — marginal but not sub-floor. Re-evaluate if n>=30 PF<0.80.
EQUITY_BANNED_SYMBOLS = frozenset()
EQUITY_BANNED_STRATEGIES = frozenset({"Classic Momentum"})

# Confidence reject bands for EQUITY. Per 2026-04-23 ledger
# (audit_dashboard/data/dashboard_data.json.picks.recent_closed filtered to
# EQUITY, n=347 with confidence>0):
#   [0.60, 0.65): n=52, WR 35.3%, avg -0.54%, cum -28.1%  ← real danger zone
# Other bands either have positive edge (<0.60: +167% cum), very small n
# (<0.85 higher bands), or too-small samples to act on yet (e.g. [0.85, 0.90)
# n=5 at 25% WR — flagged but deferred until OOS purged K-Fold).
# Intervals are half-open [lo, hi). Cerebras gpt-oss-120b 2nd opinion ranked
# this as ship-rank #1 (reports/consult_cerebras_20260423T233207Z.md).
EQUITY_CONFIDENCE_REJECT_BANDS: tuple[tuple[float, float], ...] = (
    (0.60, 0.65),
)

# ───────────────── COMMODITY rules ─────────────────
# cta_commodity_momentum_term has PF 0.02 on n=46 — mechanical failure.
COMMODITY_BANNED_STRATEGIES = frozenset({"cta_commodity_momentum_term"})
# Confidence under 0.70 has PF 0.20-0.43 across 214 picks. Above 0.70
# (371 picks) has PF 1.34. Clear structural break.
COMMODITY_CONFIDENCE_MIN = 0.70

# ───────────────── FOREX rules ─────────────────
# Symbols with realized PF below 0.50 on n >= 44 each.
# 2026-05-05: EURUSD=X UN-BANNED — it is the world's most liquid pair
# with tightest spreads. If strategies lose on EURUSD, the strategies
# are broken, not the asset. Banning the best pair hides strategy flaws.
# See updates/2026-05-05-forex-audit-swarm-review.md.
FOREX_BANNED_SYMBOLS = frozenset({
    "AUDUSD=X", "CADJPY=X", "EURJPY=X",
})

# FOREX-only strategy block. Strategy name is allowed on other ACs — e.g.
# "Breakout Momentum" is a 59.5% WR (n=37) positive contributor on EQUITY,
# but a -0.551% avg / 45% WR (n=20) net loser on FOREX in the last 790
# closed picks (post-2026-04-18 TP/SL widening). Derived from
# audit_dashboard/data/dashboard_data.json.picks.recent_closed filtered
# to asset_class == "FOREX". See reports/SYNTHESIS_6_ANALYSES_AUDIT_WHATIF_2026_04_23.md §9.
FOREX_BANNED_STRATEGIES = frozenset({
    "Breakout Momentum",
})

# Confidence reject bands for FOREX. Per 2026-04-23 ledger
# (audit_dashboard/data/dashboard_data.json.picks.recent_closed filtered to
# FOREX, n=780 with confidence>0):
#   [0.95, 1.00]: n=38, WR 39.5%, avg -0.80%, cum -30.3%  ← overconfidence trap
# MiniMax M2.7 originally proposed [0.70, 0.75) as danger, but our ledger shows
# [0.70, 0.75) is actually 59.3% WR (positive). The REAL FOREX danger zone is
# the extreme right tail. Upper bound 1.0001 so 1.00-confidence picks match.
# Cerebras gpt-oss-120b 2nd opinion ranked this ship-rank #2
# (reports/consult_cerebras_20260423T233207Z.md).
FOREX_CONFIDENCE_REJECT_BANDS: tuple[tuple[float, float], ...] = (
    (0.95, 1.0001),
)

# ───────────────── ETF rules ─────────────────
ETF_BANNED_SYMBOLS = frozenset({"IWM", "GLD"})

# ───────────────── BOND rules ─────────────────
# Sample too small (n=17) for structural claims. Allow all.

# ───────────────── ML-score rules (cross-AC, ML-sourced picks only) ─────────────────
# Derived from 486 RESOLVED Claude ML picks in updates/data/claude_ml_picks.json.
# Only the mid band [0.35, 0.50) was profitable: n=47, WR 57%, PF 2.13, +96% pnl.
# high [0.50, 0.65): n=336, PF 0.30, -1,038% pnl. very_high >=0.65: n=40, PF 0.18.
# low <0.35: n=59, PF 0.73. Overconfidence inversion identical to generic confidence.
# Thresholds are env-overridable for shadow-mode tuning.
ML_PUMP_PROB_MIN = float(os.environ.get("HF_GATE_ML_PUMP_LO", "0.35"))
ML_PUMP_PROB_MAX = float(os.environ.get("HF_GATE_ML_PUMP_HI", "0.50"))

# CRYPTO RSI-4h killzone: DISABLED 2026-04-28.
# Per `reports/crypto_rsi4h_killzone_review_2026_04_28.md` (agent a0c9a925),
# `technical_rsi_4h` is a writer artifact: `audit_trail/dashboard_generator.py:12757`
# stamps a per-symbol RSI snapshot identically on every pick at every regen.
# All 850 CRYPTO closed picks show only 28 unique RSI values (one per symbol),
# making the killzone operationally a symbol blocklist, not a real RSI filter.
# The [40, 60) window was rejecting profitable symbols (NEAR PF 2.02, INJ PF 2.69,
# APT PF 1.18, LINK PF 1.14) while missing the truly-bad bin [60, 65) (WR 23.5%,
# PF 0.55, n=17). Defaults flipped to LO=HI=0 so `LO <= rsi4h < HI` is empty.
# Env-var override is preserved for shadow-mode tuning if someone wants to
# re-test (`HF_GATE_CRYPTO_RSI4H_KILL_LO=40 HF_GATE_CRYPTO_RSI4H_KILL_HI=60`).
# Bad-symbol pressure is now expressed via `CRYPTO_BANNED_SYMBOLS` above
# (PF<0.95, n>=20 empirical threshold). The deeper fix — making the writer
# emit per-pick-time RSI rather than per-symbol-snapshot — is a separate PR.
CRYPTO_RSI4H_KILL_LO = float(os.environ.get("HF_GATE_CRYPTO_RSI4H_KILL_LO", "0"))
CRYPTO_RSI4H_KILL_HI = float(os.environ.get("HF_GATE_CRYPTO_RSI4H_KILL_HI", "0"))

# CRYPTO RSI-1h overbought killzone: strong + overbought on the fast TF.
# Per tools/edge_latent_features.py on 3,500-pick ledger (2026-04-23):
#   strong_60_70:     n=322, WR 31.1%, PF 0.57, total -131 pnl%
#   overbought_70_80: n=54,  WR 14.8%, PF 0.13, total  -47 pnl%
# Combined (>=60): n=376 at PF ~0.50. Fast-TF crypto overbought = late-entry.
# Enabled by commit 680399794b (technical_rsi_1h writer fix; field was null
# on 100% of closed picks before that).
CRYPTO_RSI1H_OVERBOUGHT_MIN = float(os.environ.get("HF_GATE_CRYPTO_RSI1H_OVERBOUGHT_MIN", "60"))

# ML sources carry a pump_probability; non-ML sources don't (skip the check).
ML_SOURCE_SYSTEMS = frozenset({
    "claude_gainer_st", "claude_gainer", "claude_gainer_ml_perf",
    "crypto_gainer_ml", "claude_ml_gainer", "antigravity_ml_gainer",
    "ml_crypto_pred", "crypto_ml_edge",
})


def _ac(pick: dict[str, Any]) -> str:
    ac = str(pick.get("asset_class") or pick.get("category") or "").upper().strip()
    return {"ETFS": "ETF", "BONDS": "BOND", "COMMODITIES": "COMMODITY", "STOCKS": "EQUITY"}.get(ac, ac)


def _direction(pick: dict[str, Any]) -> str:
    return str(pick.get("signal_type") or pick.get("direction") or "").upper().strip()


def _confidence(pick: dict[str, Any]) -> float | None:
    v = pick.get("confidence")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _strategy(pick: dict[str, Any]) -> str:
    return str(pick.get("strategy") or "").strip()


def _symbol(pick: dict[str, Any]) -> str:
    return str(pick.get("symbol") or "").upper().strip()


def _pump_probability(pick: dict[str, Any]) -> float | None:
    """Claude ML's native score, 0..1. None if not an ML pick."""
    for key in ("ml_pump_probability", "pump_probability"):
        v = pick.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _rsi_4h(pick: dict[str, Any]) -> float | None:
    v = pick.get("technical_rsi_4h")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rsi_1h(pick: dict[str, Any]) -> float | None:
    v = pick.get("technical_rsi_1h")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_ml_source(pick: dict[str, Any]) -> bool:
    src = str(pick.get("source_system") or "").strip()
    strat = str(pick.get("strategy") or "").strip()
    if src in ML_SOURCE_SYSTEMS or strat in ML_SOURCE_SYSTEMS:
        return True
    # Any pick that has a pump_probability set counts as ML-sourced.
    return _pump_probability(pick) is not None


def passes_hedge_fund_gate(pick: dict[str, Any]) -> tuple[bool, str]:
    """Return (True, "OK") or (False, reason).

    Rules are per-AC, empirically derived from the 3,500-row closed ledger.
    See reports/HEDGE_FUND_EDGE_FINDINGS_2026_04_22.md for every threshold's
    sample size and realized PF / WR.
    """
    ac = _ac(pick)
    sym = _symbol(pick)
    strat = _strategy(pick)
    direction = _direction(pick)
    conf = _confidence(pick)

    # ── Cross-AC pipeline hygiene: empty/missing strategy is a pipeline defect,
    # not a legitimate pick. Recent 790 FOREX closed picks show n=10 empty-strat
    # picks at 10% WR / -1.875% avg — pure noise. Reject regardless of AC so the
    # same bug can't leak into CRYPTO/EQUITY/etc. ──
    if not strat or not str(strat).strip():
        return False, "HF_GATE: empty strategy (pipeline defect; n=10 FOREX showed 10% WR / -1.875% avg)"

    if ac == "CRYPTO":
        if sym in CRYPTO_BANNED_SYMBOLS:
            return False, f"HF_GATE: CRYPTO banned symbol {sym} (empirical PF<0.95, n>=20; see crypto_rsi4h_killzone_review_2026_04_28.md)"
        if strat in CRYPTO_BANNED_STRATEGIES:
            return False, f"HF_GATE: CRYPTO banned strategy {strat} (PF 0.72 on n=92)"
        lo, hi = CRYPTO_CONFIDENCE_DEAD_BAND
        if conf is not None and lo <= conf < hi:
            return False, f"HF_GATE: CRYPTO confidence {conf:.3f} in dead band [{lo:.2f},{hi:.2f}) (PF 0.69 on n=882)"
        # RSI-4h killzone: neutral band has the worst PF on crypto (n=159, PF 0.60)
        rsi4h = _rsi_4h(pick)
        if rsi4h is not None and CRYPTO_RSI4H_KILL_LO <= rsi4h < CRYPTO_RSI4H_KILL_HI:
            return False, f"HF_GATE: CRYPTO rsi_4h={rsi4h:.1f} in killzone [{CRYPTO_RSI4H_KILL_LO:.0f},{CRYPTO_RSI4H_KILL_HI:.0f}) (PF 0.60 on n=159)"
        # RSI-1h overbought: strong 60-70 + overbought 70+ on the fast TF.
        rsi1h = _rsi_1h(pick)
        if rsi1h is not None and rsi1h >= CRYPTO_RSI1H_OVERBOUGHT_MIN:
            return False, f"HF_GATE: CRYPTO rsi_1h={rsi1h:.1f} >= {CRYPTO_RSI1H_OVERBOUGHT_MIN:.0f} overbought (strong 60-70: PF 0.57 n=322; overbought 70+: PF 0.13 n=54)"
        # Fall through to cross-AC ML check below

    elif ac == "EQUITY":
        if direction and direction not in EQUITY_ALLOWED_DIRECTIONS:
            return False, f"HF_GATE: EQUITY {direction} rejected (LONG-only historical edge; SHORT n=4 went 0/3)"
        if sym in EQUITY_BANNED_SYMBOLS:
            return False, f"HF_GATE: EQUITY banned symbol {sym} (PF 0.69 on n=15)"
        if strat in EQUITY_BANNED_STRATEGIES:
            return False, f"HF_GATE: EQUITY banned strategy {strat} (PF 0.92 on n=39)"
        if conf is not None:
            for lo, hi in EQUITY_CONFIDENCE_REJECT_BANDS:
                if lo <= conf < hi:
                    return False, (
                        f"HF_GATE: EQUITY confidence {conf:.3f} in reject band "
                        f"[{lo:.2f},{hi:.2f}) (n=52, WR 35.3%, cum -28.1%)"
                    )

    elif ac == "COMMODITY":
        if strat in COMMODITY_BANNED_STRATEGIES:
            return False, f"HF_GATE: COMMODITY banned strategy {strat} (PF 0.02 on n=46)"
        if conf is not None and conf < COMMODITY_CONFIDENCE_MIN:
            return False, f"HF_GATE: COMMODITY confidence {conf:.3f} < {COMMODITY_CONFIDENCE_MIN} (PF 0.20-0.43 below; PF 1.34 above)"

    elif ac == "FOREX":
        if sym in FOREX_BANNED_SYMBOLS:
            return False, f"HF_GATE: FOREX banned symbol {sym} (lifetime PF < 0.50 on n>=44)"
        if strat in FOREX_BANNED_STRATEGIES:
            return False, (
                f"HF_GATE: FOREX banned strategy {strat} "
                f"(n=20, WR 45.0%, avg -0.551% in recent 790 post-2026-04-18)"
            )
        if conf is not None:
            for lo, hi in FOREX_CONFIDENCE_REJECT_BANDS:
                if lo <= conf < hi:
                    return False, (
                        f"HF_GATE: FOREX confidence {conf:.3f} in reject band "
                        f"[{lo:.2f},{hi:.2f}) — overconfidence trap "
                        f"(n=38, WR 39.5%, cum -30.3%)"
                    )

    elif ac == "ETF":
        if sym in ETF_BANNED_SYMBOLS:
            return False, f"HF_GATE: ETF banned symbol {sym} (PF < 0.85)"

    # ── Cross-AC ML check: only runs on picks carrying a pump_probability ──
    if _is_ml_source(pick):
        pump = _pump_probability(pick)
        if pump is not None:
            if pump < ML_PUMP_PROB_MIN:
                return False, (
                    f"HF_GATE: ML pump_probability={pump:.3f} below sweet-spot floor "
                    f"{ML_PUMP_PROB_MIN:.2f} (n=59, PF 0.73 in low band)"
                )
            if pump >= ML_PUMP_PROB_MAX:
                return False, (
                    f"HF_GATE: ML pump_probability={pump:.3f} at/above overconfidence "
                    f"ceiling {ML_PUMP_PROB_MAX:.2f} (n=336, PF 0.30 in high band; "
                    f"n=40, PF 0.18 very_high)"
                )

    return True, "OK"

    # BOND or unknown — too small / unhandled. Allow.
    return True, "OK"


def why_rejected(pick: dict[str, Any]) -> str | None:
    """Return the rejection reason if rejected, else None."""
    ok, reason = passes_hedge_fund_gate(pick)
    return None if ok else reason


def passes_safety_score_gate(pick: dict[str, Any]) -> tuple[bool, str]:
    """Return (True, "OK") or (False, reason) based on persona-based safety_score.

    Salvaged from the Persona-Based Safe-Pick swarm critique (DAILY_IDEAS.MD
    2026-05-24). This gate uses RELAXED per-class thresholds — it acts as a
    floor, rejecting only the obviously unsafe tail. Designed to be called
    ALONGSIDE passes_hedge_fund_gate(), not instead of it.

    Metrics are extracted from the pick dict (risk_metrics, fundamental_snapshot,
    or top-level fields). If no metrics are available, the gate passes (fail-open).

    Threshold source: config/persona_thresholds.yaml.
    """
    from alpha_engine.value_screener import compute_safety_score, _load_persona_thresholds

    ac = _ac(pick)
    if not ac or ac == "UNKNOWN":
        return True, "PERSONA_SAFETY: unknown asset class — pass (fail-open)"

    # Extract metrics from pick dict (try multiple locations)
    metrics: dict[str, float | None] = {}

    # 1. Try risk_metrics sub-dict (persona output format)
    rm = pick.get("risk_metrics") or {}
    if isinstance(rm, dict):
        metrics["volatility"] = rm.get("volatility")
        metrics["beta"] = rm.get("beta")
        metrics["sharpe"] = rm.get("sharpe")
        metrics["max_drawdown"] = rm.get("max_drawdown")

    # 2. Try fundamental_snapshot (UEPS picks)
    fs = pick.get("fundamental_snapshot") or {}
    if isinstance(fs, dict):
        # Fall through if risk_metrics already set them
        if metrics.get("volatility") is None:
            metrics["volatility"] = fs.get("volatility")
        if metrics.get("beta") is None:
            metrics["beta"] = fs.get("beta")

    # 3. Try top-level fields
    for key, mkey in (
        ("volatility", "volatility"), ("annualized_vol", "volatility"),
        ("beta", "beta"), ("stock_beta", "beta"),
        ("sharpe_ratio", "sharpe"), ("sharpe", "sharpe"),
        ("max_drawdown", "max_drawdown"), ("max_dd", "max_drawdown"),
        ("cagr", "cagr"), ("annual_cagr", "cagr"),
    ):
        if metrics.get(mkey) is None:
            val = pick.get(key)
            if val is not None:
                try:
                    metrics[mkey] = float(val)
                except (TypeError, ValueError):
                    pass

    # 4. Try extra / extra_data
    extra = pick.get("extra") or pick.get("extra_data") or {}
    if isinstance(extra, dict):
        for key, mkey in (
            ("cagr", "cagr"), ("annual_cagr", "cagr"),
            ("sharpe", "sharpe"), ("sharpe_ratio", "sharpe"),
        ):
            if metrics.get(mkey) is None:
                val = extra.get(key)
                if val is not None:
                    try:
                        metrics[mkey] = float(val)
                    except (TypeError, ValueError):
                        pass

    # If we have zero metrics, fail-open (don't block picks with incomplete data)
    present = sum(1 for v in metrics.values() if v is not None)
    if present == 0:
        return True, "PERSONA_SAFETY: no metrics available — pass (fail-open)"

    try:
        t = _load_persona_thresholds()
    except Exception:
        t = {"safety_score_floor": 0.40}
    score = compute_safety_score(metrics, ac, thresholds=t)
    floor = float(t.get("safety_score_floor", 0.40))

    if score < floor:
        present_str = "/".join(
            f"{k}={v:.3f}" for k, v in sorted(metrics.items())
            if v is not None
        )
        return False, (
            f"PERSONA_SAFETY: {ac} safety_score={score:.3f} below floor={floor:.2f} "
            f"(present: {present_str})"
        )
    return True, "OK"


def batch_evaluate(picks: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate a batch and return summary counters."""
    kept, rejected = 0, 0
    by_ac: dict[str, dict[str, int]] = {}
    reasons: dict[str, int] = {}
    for p in picks:
        ok, reason = passes_hedge_fund_gate(p)
        ac = _ac(p) or "UNKNOWN"
        by_ac.setdefault(ac, {"kept": 0, "rejected": 0})
        if ok:
            kept += 1
            by_ac[ac]["kept"] += 1
        else:
            rejected += 1
            by_ac[ac]["rejected"] += 1
            reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "total": len(picks),
        "kept": kept,
        "rejected": rejected,
        "by_asset_class": by_ac,
        "rejection_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
    }


__all__ = [
    "passes_hedge_fund_gate",
    "passes_safety_score_gate",
    "why_rejected",
    "batch_evaluate",
    # Exposed for tests and for callers that want to inspect / override rules.
    "CRYPTO_BANNED_SYMBOLS", "CRYPTO_BANNED_STRATEGIES", "CRYPTO_CONFIDENCE_DEAD_BAND",
    "CRYPTO_RSI4H_KILL_LO", "CRYPTO_RSI4H_KILL_HI",
    "CRYPTO_RSI1H_OVERBOUGHT_MIN",
    "EQUITY_ALLOWED_DIRECTIONS", "EQUITY_BANNED_SYMBOLS", "EQUITY_BANNED_STRATEGIES",
    "EQUITY_CONFIDENCE_REJECT_BANDS",
    "COMMODITY_BANNED_STRATEGIES", "COMMODITY_CONFIDENCE_MIN",
    "FOREX_BANNED_SYMBOLS", "FOREX_BANNED_STRATEGIES",
    "FOREX_CONFIDENCE_REJECT_BANDS",
    "ETF_BANNED_SYMBOLS",
    "ML_PUMP_PROB_MIN", "ML_PUMP_PROB_MAX", "ML_SOURCE_SYSTEMS",
]

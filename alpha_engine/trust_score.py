"""
TRUST SCORE (0-10) — Simple, transparent quality rating.

Unlike elite_score (complex, 15+ components, anti-predictive mid-range),
trust_score is designed to be:
- Simple: 5 components, each contributing 0-2 points
- Transparent: user can see exactly why a pick scored high/low
- Verified: each component is backed by Spearman correlation on 1,879 closed picks
- Actionable: TRUST >= 7 = trade, < 7 = skip

Components (calibrated 2026-03-29 from correlation analysis):
1. Freshness (+2 max): fresh signals win more (age < 1h = 2, < 4h = 1)
2. Strategy Track Record (+3 max): forward WR with sufficient trades (r=+0.114)
3. Symbol Historical Edge (+2 max): proven winning symbols/strategies
4. Regime Alignment (+2 max): direction matches market regime (IC=0.190)
5. Risk/Reward Quality (+1 max): R:R >= 1.5 (r=+0.099)

NOTE: Agreement/consensus was REMOVED — Spearman r=-0.075 (anti-predictive).
High consensus = worse outcomes on 1,879 closed trades.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _as_wr_pct(value):
    """Normalize win-rate values to 0-100 percentage scale."""
    try:
        val = float(value)
    except (TypeError, ValueError):
        return 0.0
    if 0 < val <= 1.0:
        return val * 100.0
    return val


def compute_trust_score(pick, strategy_perf=None, regime=None, closed_picks=None):
    """Compute trust score 0-10 for a single pick."""
    score = 0
    breakdown = {}
    extra = pick.get("extra") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception:
            extra = {}
    elif not isinstance(extra, dict):
        extra = {}

    # --- Component 1: Freshness (0-1) ---
    ts = pick.get("timestamp") or pick.get("created_at") or pick.get("scan_timestamp")
    freshness = 0
    if ts:
        try:
            ts_str = str(ts).replace("Z", "+00:00")
            if "T" not in ts_str and " " in ts_str:
                ts_str = ts_str.replace(" ", "T")
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if age_hours < 1:
                freshness = 2
            elif age_hours < 4:
                freshness = 1
        except (ValueError, TypeError):
            pass
    score += freshness
    breakdown["freshness"] = freshness

    # --- Component 2: Strategy Track Record (0-3) ---
    # Forward WR is the #4 Spearman predictor (r=+0.114)
    track_record = 0
    strategy = pick.get("strategy", "")
    symbol = pick.get("symbol", "")

    # Use forward WR from pick data (computed by dashboard_generator)
    fwd_wr = _as_wr_pct(pick.get("strat_fwd_wr") or pick.get("forward_wr"))
    fwd_trades = pick.get("strat_fwd_trades") or pick.get("forward_trades") or 0

    if fwd_wr is not None and fwd_trades >= 8:  # lowered from 10 — 8 trades sufficient for strong signal
        if fwd_wr >= 60:
            track_record = 3
        elif fwd_wr >= 50:
            track_record = 2
        elif fwd_wr >= 40:
            track_record = 1
    elif strategy_perf and strategy in strategy_perf:
        sp = strategy_perf[strategy]
        wr = _as_wr_pct(sp.get("win_rate", 0))
        trades = sp.get("closed_picks", sp.get("total_trades", 0))
        if trades >= 10 and wr >= 60:
            track_record = 3
        elif trades >= 5 and wr >= 50:
            track_record = 2
        elif trades >= 5 and wr >= 40:
            track_record = 1

    score += track_record
    breakdown["track_record"] = track_record

    # --- Component 3: Symbol Historical Edge (0-2) ---
    symbol_edge = 0

    # Proven ML strategies get max edge
    # Criteria for inclusion: fwd_wr >= 55% on 8+ forward trades (low false-positive rate)
    PROVEN = {
        "ml_enhanced_BNBUSDT_15m_B_lightgbm",
        "ml_enhanced_FETUSDT_1d_B_lightgbm",
        "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack",
        "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack",
        "copy_hl_NMTD_25M",
        "st_atr_vol_breakout",
        "drawdown_recovery_rsi_xrp",
        "drawdown_recovery_rsi_sol",
        "drawdown_recovery_rsi_eth",
        "keltner_compression_expansion_eth_v1",
        "crypto_keltner_compression_expansion_v1",
        "st_fear_greed_contrarian",
        "quality-minus-junk",  # 66.7% WR on 8 forward trades (kimi_riseoftheclaw)
        # NOT INCLUDED: battleground — attribution 2026-04-04: WR=35.7% PF=0.28 n=14 (AVOID-tier)
        # NOT INCLUDED: super_signals source — attribution: WR=50.4% PF=0.77 n=119 (loses money)
    }
    if strategy in PROVEN:
        symbol_edge = 2
    elif track_record >= 2:
        symbol_edge = 1  # Strategy already has good WR — modest edge

    score += symbol_edge
    breakdown["edge"] = symbol_edge

    # --- NOTE: Agreement/Consensus REMOVED (Spearman r=-0.075, anti-predictive) ---
    # High consensus (5+ systems agree) actually predicts WORSE outcomes.
    # Verified on 1,879 closed crypto picks. Do not add back.

    # --- Component 4: Regime Alignment (0-2) ---
    regime_pts = 0
    direction = (pick.get("signal_type", "") or pick.get("direction", "")).upper()
    pick_regime = (
        regime
        or pick.get("regime_at_entry")
        or pick.get("htf_bias")
        or extra.get("fast_regime")
        or extra.get("regime")
        or "UNKNOWN"
    )
    pick_regime_upper = str(pick_regime).upper()

    if direction in ("BUY", "LONG"):
        if any(r in pick_regime_upper for r in ("BULL", "STRONG_BULL", "MARKUP")):
            regime_pts = 2
        elif any(
            r in pick_regime_upper for r in ("CHOP", "RANG", "NEUTRAL", "UNKNOWN")
        ):
            regime_pts = 1
        # BEAR + LONG = 0
    elif direction in ("SELL", "SHORT"):
        if any(
            r in pick_regime_upper
            for r in ("BEAR", "STRONG_BEAR", "MARKDOWN", "CAPITULATION")
        ):
            regime_pts = 2
        elif any(
            r in pick_regime_upper for r in ("CHOP", "RANG", "NEUTRAL", "UNKNOWN")
        ):
            regime_pts = 1
        # BULL + SHORT = 0

    score += regime_pts
    breakdown["regime_alignment"] = regime_pts

    # --- Component 5: Risk/Reward Quality (0-1) ---
    # R:R ratio is a modest but real predictor (Spearman r=+0.099)
    rr_pts = 0
    rr = pick.get("rr_ratio") or pick.get("risk_reward") or 0
    if not rr:
        # Compute from TP/SL/entry if available
        entry = float(pick.get("entry_price") or pick.get("entry") or 0)
        tp = float(pick.get("take_profit") or pick.get("tp") or 0)
        sl = float(pick.get("stop_loss") or pick.get("sl") or 0)
        if entry > 0 and tp > 0 and sl > 0 and abs(entry - sl) > 0:
            rr = abs(tp - entry) / abs(entry - sl)
    if rr >= 1.5:
        rr_pts = 1
    score += rr_pts
    breakdown["rr_quality"] = rr_pts

    # --- Labels ---
    if score >= 8:
        label = "EXCELLENT"
    elif score >= 7:
        label = "TRUSTWORTHY"
    elif score >= 5:
        label = "MODERATE"
    elif score >= 3:
        label = "LOW"
    else:
        label = "AVOID"

    return {
        "trust_score": score,
        "trust_breakdown": breakdown,
        "trust_label": label,
    }


def enrich_picks_with_trust_score(picks, strategy_perf=None, regime=None):
    """Tag every pick with trust_score, trust_breakdown, trust_label."""
    if strategy_perf is None:
        perf_path = DATA_DIR / "strategy_performance.json"
        if perf_path.exists():
            try:
                strategy_perf = json.loads(perf_path.read_text(encoding="utf-8"))
            except Exception:
                strategy_perf = {}
        else:
            strategy_perf = {}

    for pick in picks:
        result = compute_trust_score(pick, strategy_perf, regime)
        pick["trust_score"] = result["trust_score"]
        pick["trust_breakdown"] = result["trust_breakdown"]
        pick["trust_label"] = result["trust_label"]

    return picks


if __name__ == "__main__":
    import sys

    sys.stdout = open(
        sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False, errors="replace"
    )

    active = json.loads((DATA_DIR / "active_picks.json").read_text(encoding="utf-8"))
    enriched = enrich_picks_with_trust_score(active)

    from collections import Counter

    labels = Counter(p.get("trust_label", "?") for p in enriched)
    print(f"Trust Score Distribution ({len(enriched)} picks):")
    for label, count in sorted(labels.items()):
        print(f"  {label}: {count}")

    trustworthy = [p for p in enriched if p.get("trust_score", 0) >= 7]
    print(f"\nTrustworthy (>= 7): {len(trustworthy)} picks")
    for p in sorted(trustworthy, key=lambda x: -x.get("trust_score", 0))[:10]:
        print(
            f"  {p['trust_score']:2d} {p.get('symbol', '?'):12s} {p.get('trust_label', '')} | {p.get('trust_breakdown', {})}"
        )

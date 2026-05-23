#!/usr/bin/env python3
"""
Regime-Adaptive Signal Ensemble
================================
Combines indicators differently based on the current market regime.

- BULLISH: boost momentum, volume breakout, LONG consensus
- BEARISH: boost mean reversion oversold, SHORT consensus, breakdown
- CHOPPY: boost mean reversion, range-bound; penalize directional; cut confidence 20%
- WEAKENING_BULL / WEAKENING_BEAR: hedge bias + volatility boost

Reads:
  - alpha_engine/data/regime_report.json  (current regime)
  - alpha_engine/data/active_picks.json   (live picks)
  - alpha_engine/data/closed_picks_fast.json (for backtest)

Writes:
  - alpha_engine/data/regime_ensemble_picks.json (top 20 regime-optimized)

stdlib only.
"""

import json
import os
import sys
import datetime
import copy

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

# ---------------------------------------------------------------------------
# Strategy classification
# ---------------------------------------------------------------------------
# Each strategy maps to one or more signal categories.
# Categories: momentum, mean_reversion, volume_breakout, breakdown,
#             copy_long, copy_short, range_bound, volatility, directional

STRATEGY_TAGS = {
    # Momentum / trend-following
    "momentum_catcher":       ["momentum", "directional"],
    "ema_crossover":          ["momentum", "directional"],
    "macd_divergence":        ["momentum", "directional"],
    "macd_crossover":         ["momentum", "directional"],
    "breakout_scanner":       ["momentum", "volume_breakout", "directional"],
    "volume_breakout":        ["volume_breakout", "directional"],
    "trend_follower":         ["momentum", "directional"],
    "cross_sectional_momentum": ["momentum", "directional"],
    "multi_timeframe_ema_stack": ["momentum", "directional"],
    "atr_volatility_breakout":  ["volatility", "volume_breakout"],
    "break_of_structure":     ["momentum", "directional"],
    "swing_failure_pattern":  ["momentum", "directional"],
    "hurst_regime_adaptive":  ["momentum", "directional"],
    "momentum_rider":         ["momentum", "directional"],
    "dynamic_gainer":         ["momentum", "volume_breakout"],
    "dynamic_gainer_scanner": ["momentum", "volume_breakout"],

    # Mean reversion
    "hl_mean_reversion":      ["mean_reversion"],
    "mean_reversion":         ["mean_reversion"],
    "multi_sigma_reversal":   ["mean_reversion"],
    "rsi_reversal":           ["mean_reversion"],
    "connors_rsi2":           ["mean_reversion"],
    "triple_rsi":             ["mean_reversion"],
    "bollinger_mean_reversion": ["mean_reversion"],
    "keltner_squeeze":        ["mean_reversion", "range_bound"],
    "autocorrelation_exploiter": ["mean_reversion"],
    "volume_profile_poc_reversion": ["mean_reversion", "range_bound"],
    "volume_profile_value_area": ["mean_reversion", "range_bound"],

    # Funding / carry (contrarian / mean-reversion-adjacent)
    "hl_funding_fade":        ["mean_reversion", "volatility"],
    "funding_rate_carry":     ["mean_reversion"],
    "oi_funding_squeeze":     ["mean_reversion", "volatility"],

    # Copy trader / consensus
    "copy_trader_long":       ["copy_long", "directional"],
    "copy_trader_short":      ["copy_short", "directional"],
    "whale_accumulation_detector": ["copy_long"],
    "liquidation_cascade_bottom": ["mean_reversion", "volatility"],

    # Breakdown / short-biased
    "breakdown_scanner":      ["breakdown", "directional"],
    "short_squeeze_detector": ["breakdown", "volatility"],

    # Range-bound / neutral
    "range_trader":           ["range_bound"],
    "grid_strategy":          ["range_bound"],
    "adaptive_vr_confluence": ["range_bound", "mean_reversion"],

    # Volatility
    "vix_spike":              ["volatility"],
    "fear_greed_extreme_dca": ["mean_reversion", "volatility"],

    # Seasonal / event
    "seasonal_factor_rotation": ["directional"],
    "cot_positioning":        ["directional"],
}

# Fallback classification based on keywords in strategy name or reason
KEYWORD_TAGS = {
    "momentum":   ["momentum", "directional"],
    "ema":        ["momentum", "directional"],
    "macd":       ["momentum", "directional"],
    "breakout":   ["volume_breakout", "directional"],
    "breakdown":  ["breakdown", "directional"],
    "reversion":  ["mean_reversion"],
    "rsi":        ["mean_reversion"],
    "bollinger":  ["mean_reversion"],
    "funding":    ["mean_reversion", "volatility"],
    "squeeze":    ["mean_reversion", "volatility"],
    "copy":       ["copy_long", "directional"],
    "whale":      ["copy_long"],
    "liquidation": ["mean_reversion", "volatility"],
    "range":      ["range_bound"],
    "grid":       ["range_bound"],
    "volatility": ["volatility"],
    "vix":        ["volatility"],
    "fear":       ["mean_reversion", "volatility"],
    "trend":      ["momentum", "directional"],
    "carry":      ["mean_reversion"],
    "fade":       ["mean_reversion"],
    "reversal":   ["mean_reversion"],
    "oversold":   ["mean_reversion"],
    "overbought": ["mean_reversion"],
    "volume":     ["volume_breakout"],
    "swing":      ["momentum", "directional"],
    "structure":  ["momentum", "directional"],
}


def classify_pick(pick):
    """Return set of tags for a pick based on strategy name and reason."""
    strat = pick.get("strategy", "")
    tags = set()

    # Direct lookup
    if strat in STRATEGY_TAGS:
        tags.update(STRATEGY_TAGS[strat])

    # Keyword fallback on strategy name + reason
    text = (strat + " " + pick.get("reason", "")).lower()
    for kw, kw_tags in KEYWORD_TAGS.items():
        if kw in text:
            tags.update(kw_tags)

    # Direction-based copy trader inference
    direction = pick.get("direction", pick.get("signal_type", "")).upper()
    if "copy" in strat.lower() or "consensus" in strat.lower():
        if direction in ("LONG", "BUY"):
            tags.add("copy_long")
        elif direction in ("SHORT", "SELL"):
            tags.add("copy_short")

    # If we still have nothing, mark as directional
    if not tags:
        tags.add("directional")

    return tags


# ---------------------------------------------------------------------------
# Regime weight maps
# ---------------------------------------------------------------------------

REGIME_WEIGHTS = {
    "BULLISH": {
        "momentum":       1.5,
        "volume_breakout": 1.5,
        "copy_long":      2.0,
        "copy_short":     0.3,
        "mean_reversion": 0.5,   # RSI overbought reversions less reliable in bull
        "breakdown":      0.3,
        "range_bound":    0.7,
        "volatility":     1.0,
        "directional":    1.2,   # directional longs favored
    },
    "BEARISH": {
        "momentum":       0.5,   # momentum is against you
        "volume_breakout": 0.5,
        "copy_long":      0.3,
        "copy_short":     2.0,
        "mean_reversion": 1.5,   # RSI oversold for LONG bounces
        "breakdown":      1.5,
        "range_bound":    0.7,
        "volatility":     1.0,
        "directional":    0.5,
    },
    "CHOPPY": {
        "momentum":       0.5,
        "volume_breakout": 0.5,
        "copy_long":      0.5,
        "copy_short":     0.5,
        "mean_reversion": 2.0,
        "breakdown":      0.5,
        "range_bound":    1.5,
        "volatility":     1.0,
        "directional":    0.5,
    },
    "WEAKENING_BULL": {
        "momentum":       0.7,   # same direction penalized
        "volume_breakout": 0.8,
        "copy_long":      0.7,
        "copy_short":     1.3,   # hedge bias: opposite gets boost
        "mean_reversion": 1.3,
        "breakdown":      1.3,
        "range_bound":    1.0,
        "volatility":     1.5,
        "directional":    0.7,
    },
    "WEAKENING_BEAR": {
        "momentum":       1.3,   # opposite of bear = bullish boost
        "volume_breakout": 1.3,
        "copy_long":      1.3,
        "copy_short":     0.7,
        "mean_reversion": 1.3,
        "breakdown":      0.7,
        "range_bound":    1.0,
        "volatility":     1.5,
        "directional":    1.0,
    },
}

# Aliases
REGIME_WEIGHTS["BULL"] = REGIME_WEIGHTS["BULLISH"]
REGIME_WEIGHTS["BEAR"] = REGIME_WEIGHTS["BEARISH"]
REGIME_WEIGHTS["CHOP"] = REGIME_WEIGHTS["CHOPPY"]
REGIME_WEIGHTS["RANGING"] = REGIME_WEIGHTS["CHOPPY"]
REGIME_WEIGHTS["NEUTRAL"] = REGIME_WEIGHTS["CHOPPY"]

# Confidence penalty for choppy
CHOPPY_CONFIDENCE_PENALTY = 0.80  # reduce all confidence by 20%


def normalize_regime(regime_str):
    """Map various regime strings to our canonical names."""
    if not regime_str:
        return "CHOPPY"
    r = regime_str.upper().strip()
    if r in REGIME_WEIGHTS:
        return r
    if "WEAK" in r and "BULL" in r:
        return "WEAKENING_BULL"
    if "WEAK" in r and "BEAR" in r:
        return "WEAKENING_BEAR"
    if "BULL" in r:
        return "BULLISH"
    if "BEAR" in r:
        return "BEARISH"
    if "CHOP" in r or "RANGE" in r or "NEUTRAL" in r:
        return "CHOPPY"
    return "CHOPPY"  # default to conservative


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_regime_score(pick, regime):
    """Compute regime-adjusted score for a single pick."""
    tags = classify_pick(pick)
    weights = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS["CHOPPY"])

    # Base confidence
    confidence = pick.get("confidence", 0.5)
    if confidence is None:
        confidence = 0.5
    ml_score = pick.get("ml_score")
    if ml_score is not None:
        base = (confidence + ml_score) / 2.0
    else:
        base = confidence

    # Compute weighted multiplier: average of all matching tag weights
    tag_weights = []
    for tag in tags:
        w = weights.get(tag, 1.0)
        tag_weights.append(w)

    if tag_weights:
        multiplier = sum(tag_weights) / len(tag_weights)
    else:
        multiplier = 1.0

    # Direction adjustment for weakening regimes
    direction = pick.get("direction", pick.get("signal_type", "")).upper()
    if regime == "WEAKENING_BULL" and direction in ("LONG", "BUY"):
        multiplier *= 0.85  # longs penalized in weakening bull
    elif regime == "WEAKENING_BULL" and direction in ("SHORT", "SELL"):
        multiplier *= 1.15  # shorts get hedge boost
    elif regime == "WEAKENING_BEAR" and direction in ("SHORT", "SELL"):
        multiplier *= 0.85
    elif regime == "WEAKENING_BEAR" and direction in ("LONG", "BUY"):
        multiplier *= 1.15

    # Choppy confidence penalty
    if regime in ("CHOPPY", "CHOP", "RANGING", "NEUTRAL"):
        base *= CHOPPY_CONFIDENCE_PENALTY

    regime_score = base * multiplier

    # Incorporate RSI context for mean reversion
    rsi = pick.get("rsi", pick.get("rsi_at_entry"))
    if rsi is not None:
        if "mean_reversion" in tags:
            if regime in ("BEARISH", "BEAR") and direction in ("LONG", "BUY") and rsi < 30:
                regime_score *= 1.2  # oversold bounce in bear = strong mean reversion
            elif regime in ("BULLISH", "BULL") and direction in ("SHORT", "SELL") and rsi > 70:
                regime_score *= 1.2  # overbought short in bull = contrarian signal

    # Cap at 1.0
    regime_score = min(regime_score, 1.0)

    return round(regime_score, 4), multiplier, list(tags)


def load_json(path):
    """Load JSON file safely."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def load_regime():
    """Load current regime from regime_report.json."""
    report = load_json(os.path.join(DATA, "regime_report.json"))
    if report and "regime" in report:
        raw = report["regime"]
        if isinstance(raw, dict):
            raw = raw.get("regime", "CHOPPY")
        return normalize_regime(raw), report
    # Fallback: HMM state
    hmm = load_json(os.path.join(DATA, "hmm_regime_state.json"))
    if hmm and "regime" in hmm:
        r = hmm["regime"]
        if isinstance(r, dict):
            r = r.get("regime", "CHOPPY")
        return normalize_regime(r), hmm
    return "CHOPPY", {}


def load_active_picks():
    """Load active picks from multiple sources, deduplicate."""
    picks = []

    # Primary: active_picks.json
    ap = load_json(os.path.join(DATA, "active_picks.json"))
    if ap and isinstance(ap, list):
        picks.extend(ap)

    # Secondary: dashboard_payload active picks
    dp = load_json(os.path.join(BASE, "..", "audit_trail", "data", "dashboard_payload.json"))
    if dp and isinstance(dp, dict):
        # Extract picks from systems
        for system in dp.get("systems", []):
            for strat in system.get("strategies", []):
                for p in strat.get("active_picks", []):
                    if isinstance(p, dict):
                        if "strategy" not in p:
                            p["strategy"] = strat.get("name", system.get("name", "unknown"))
                        picks.append(p)

    # Deduplicate by id
    seen = set()
    unique = []
    for p in picks:
        pid = p.get("id", "")
        if not pid:
            pid = f"{p.get('strategy', '')}_{p.get('symbol', '')}_{p.get('entry_date', '')}"
        if pid not in seen:
            seen.add(pid)
            unique.append(p)

    return unique


def load_closed_picks():
    """Load closed picks for backtesting."""
    closed = load_json(os.path.join(DATA, "closed_picks_fast.json"))
    if closed and isinstance(closed, list):
        return closed
    return []


# ---------------------------------------------------------------------------
# Main ensemble
# ---------------------------------------------------------------------------

def run_ensemble(regime=None, regime_info=None):
    """Score and rank all active picks by regime."""
    if regime is None:
        regime, regime_info = load_regime()
    if regime_info is None:
        regime_info = {}

    print(f"\n{'='*70}")
    print(f"  REGIME-ADAPTIVE SIGNAL ENSEMBLE")
    print(f"{'='*70}")
    print(f"  Current Regime: {regime}")
    btc_price = regime_info.get("btc_price", "N/A")
    print(f"  BTC Price: ${btc_price}")
    print(f"  Regime Weights Applied: {json.dumps(REGIME_WEIGHTS.get(regime, {}), indent=2)[:200]}...")
    print()

    picks = load_active_picks()
    if not picks:
        print("  [!] No active picks found.")
        return []

    print(f"  Active picks loaded: {len(picks)}")
    print()

    # Score each pick
    scored = []
    for p in picks:
        original_conf = p.get("confidence", 0.5) or 0.5
        regime_score, multiplier, tags = compute_regime_score(p, regime)
        scored.append({
            "id": p.get("id", ""),
            "strategy": p.get("strategy", "unknown"),
            "symbol": p.get("symbol", ""),
            "direction": p.get("direction", p.get("signal_type", "")),
            "original_confidence": round(original_conf, 4),
            "regime_score": regime_score,
            "regime_multiplier": round(multiplier, 4),
            "tags": tags,
            "entry_price": p.get("entry_price"),
            "take_profit": p.get("take_profit"),
            "stop_loss": p.get("stop_loss"),
            "rsi": p.get("rsi", p.get("rsi_at_entry")),
            "reason": p.get("reason", ""),
            "source_system": p.get("source_system", ""),
            "pnl_pct": p.get("pnl_pct"),
            "category": p.get("category", "crypto"),
        })

    # Sort by regime score descending
    scored.sort(key=lambda x: x["regime_score"], reverse=True)

    # Also compute original ranking (by confidence)
    by_original = sorted(scored, key=lambda x: x["original_confidence"], reverse=True)
    original_rank = {s["id"]: i + 1 for i, s in enumerate(by_original)}

    # Print comparison
    print(f"  {'Rank':>4}  {'Orig':>4}  {'Change':>6}  {'RegScore':>8}  {'Conf':>6}  {'Mult':>5}  {'Symbol':<14} {'Strategy':<30} {'Dir':<6} {'Tags'}")
    print(f"  {'-'*4}  {'-'*4}  {'-'*6}  {'-'*8}  {'-'*6}  {'-'*5}  {'-'*14} {'-'*30} {'-'*6} {'-'*20}")

    top20 = scored[:20]
    for i, s in enumerate(top20):
        new_rank = i + 1
        old_rank = original_rank.get(s["id"], len(scored))
        change = old_rank - new_rank
        if change > 0:
            arrow = f"+{change}"
        elif change < 0:
            arrow = str(change)
        else:
            arrow = "="
        print(f"  {new_rank:>4}  {old_rank:>4}  {arrow:>6}  {s['regime_score']:>8.4f}  {s['original_confidence']:>6.3f}  {s['regime_multiplier']:>5.2f}  {s['symbol']:<14} {s['strategy']:<30} {s['direction']:<6} {','.join(s['tags'][:3])}")

    # Summary stats
    boosted = sum(1 for s in scored if s["regime_multiplier"] > 1.05)
    penalized = sum(1 for s in scored if s["regime_multiplier"] < 0.95)
    neutral = len(scored) - boosted - penalized

    print(f"\n  Summary:")
    print(f"    Boosted by regime: {boosted} picks")
    print(f"    Penalized by regime: {penalized} picks")
    print(f"    Neutral: {neutral} picks")
    print(f"    Top 20 avg regime score: {sum(s['regime_score'] for s in top20) / max(len(top20), 1):.4f}")
    print(f"    Top 20 avg original conf: {sum(s['original_confidence'] for s in top20) / max(len(top20), 1):.4f}")

    return scored


# ---------------------------------------------------------------------------
# Backtest: would regime weights have improved historical WR?
# ---------------------------------------------------------------------------

def backtest_regime_weights():
    """Retroactively apply regime weights to closed picks and compare WR."""
    print(f"\n{'='*70}")
    print(f"  BACKTEST: Regime Weights on Closed Picks")
    print(f"{'='*70}")

    closed = load_closed_picks()
    if not closed:
        print("  [!] No closed picks found for backtesting.")
        return {}

    print(f"  Closed picks loaded: {len(closed)}")

    # We don't have historical regime data per-pick, but we can simulate:
    # For each closed pick, check if its tags aligned with what WOULD have been
    # boosted/penalized in each regime.

    # Strategy: test each regime and see which picks would have been filtered
    results = {}

    for regime in ["BULLISH", "BEARISH", "CHOPPY", "WEAKENING_BULL", "WEAKENING_BEAR"]:
        wins_total = 0
        losses_total = 0
        wins_filtered = 0
        losses_filtered = 0
        pnl_total = 0.0
        pnl_filtered = 0.0
        count_filtered = 0

        for pick in closed:
            status = pick.get("status", "").upper()
            pnl = pick.get("pnl_pct", 0) or 0
            if isinstance(pnl, str):
                try:
                    pnl = float(pnl)
                except (ValueError, TypeError):
                    continue

            is_win = status == "WON" or (status not in ("WON", "LOST") and pnl > 0)
            is_loss = status == "LOST" or (status not in ("WON", "LOST") and pnl < 0)

            if not is_win and not is_loss:
                continue

            if is_win:
                wins_total += 1
            else:
                losses_total += 1
            pnl_total += pnl

            # Compute regime score
            regime_score, mult, tags = compute_regime_score(pick, regime)

            # Filter: only take picks with regime_score >= 0.45
            # (simulating that we'd skip low-regime-score picks)
            if regime_score >= 0.45:
                count_filtered += 1
                pnl_filtered += pnl
                if is_win:
                    wins_filtered += 1
                else:
                    losses_filtered += 1

        total = wins_total + losses_total
        wr_original = (wins_total / total * 100) if total > 0 else 0
        filtered_total = wins_filtered + losses_filtered
        wr_filtered = (wins_filtered / filtered_total * 100) if filtered_total > 0 else 0

        results[regime] = {
            "original_trades": total,
            "original_wr": round(wr_original, 1),
            "original_pnl": round(pnl_total * 100, 2) if abs(pnl_total) < 100 else round(pnl_total, 2),
            "filtered_trades": filtered_total,
            "filtered_wr": round(wr_filtered, 1),
            "filtered_pnl": round(pnl_filtered * 100, 2) if abs(pnl_filtered) < 100 else round(pnl_filtered, 2),
            "trades_removed": total - filtered_total,
            "wr_improvement": round(wr_filtered - wr_original, 1),
        }

        improved = "IMPROVED" if wr_filtered > wr_original else ("SAME" if abs(wr_filtered - wr_original) < 0.5 else "WORSE")
        print(f"\n  [{regime}]")
        print(f"    Original:  {total} trades, WR={wr_original:.1f}%, PnL={results[regime]['original_pnl']}")
        print(f"    Filtered:  {filtered_total} trades, WR={wr_filtered:.1f}%, PnL={results[regime]['filtered_pnl']}")
        print(f"    Removed:   {total - filtered_total} picks (regime score < 0.45)")
        print(f"    WR Change: {wr_filtered - wr_original:+.1f}%  [{improved}]")

    # -----------------------------------------------------------------------
    # Regime-alignment simulation: "would the RIGHT regime filter help?"
    # For each pick, we test: if the pick was mean-reversion and succeeded,
    # it likely happened in a choppy regime. If momentum and succeeded, likely
    # bullish. We check: does high regime-score correlate with winning?
    # -----------------------------------------------------------------------
    print(f"\n  --- Regime-Alignment Correlation ---")
    print(f"  (Do high regime-score picks win more often than low ones?)")

    for regime in ["BULLISH", "BEARISH", "CHOPPY"]:
        high_wins, high_losses = 0, 0
        low_wins, low_losses = 0, 0

        for pick in closed:
            status = pick.get("status", "").upper()
            pnl = pick.get("pnl_pct", 0) or 0
            if isinstance(pnl, str):
                try:
                    pnl = float(pnl)
                except (ValueError, TypeError):
                    continue
            is_win = status == "WON" or (status not in ("WON", "LOST") and pnl > 0)
            is_loss = status == "LOST" or (status not in ("WON", "LOST") and pnl < 0)
            if not is_win and not is_loss:
                continue

            score, _, _ = compute_regime_score(pick, regime)
            # Split at median-ish threshold
            if score >= 0.55:
                if is_win:
                    high_wins += 1
                else:
                    high_losses += 1
            else:
                if is_win:
                    low_wins += 1
                else:
                    low_losses += 1

        h_total = high_wins + high_losses
        l_total = low_wins + low_losses
        h_wr = (high_wins / h_total * 100) if h_total > 0 else 0
        l_wr = (low_wins / l_total * 100) if l_total > 0 else 0
        edge = h_wr - l_wr

        print(f"\n  [{regime}]")
        print(f"    High-score (>=0.55): {h_total} trades, WR={h_wr:.1f}%")
        print(f"    Low-score  (<0.55):  {l_total} trades, WR={l_wr:.1f}%")
        print(f"    Edge: {edge:+.1f}% {'(regime scoring adds value)' if edge > 2 else '(not significant yet)'}")

    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_output(scored, regime, backtest_results):
    """Save regime ensemble picks to JSON."""
    top20 = scored[:20] if scored else []

    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "regime": regime,
        "regime_weights_applied": REGIME_WEIGHTS.get(regime, {}),
        "total_picks_scored": len(scored),
        "top_20_picks": top20,
        "backtest_summary": backtest_results,
        "methodology": {
            "description": "Each pick is scored by classifying its strategy into signal categories "
                          "(momentum, mean_reversion, volume_breakout, etc.) then applying "
                          "regime-specific weight multipliers to the base confidence score.",
            "regimes": list(REGIME_WEIGHTS.keys()),
            "confidence_cap": 1.0,
            "choppy_penalty": f"{(1 - CHOPPY_CONFIDENCE_PENALTY) * 100:.0f}% confidence reduction",
            "filter_threshold_backtest": 0.45,
        },
    }

    out_path = os.path.join(DATA, "regime_ensemble_picks.json")
    os.makedirs(DATA, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Output saved to: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    """Main entry point."""
    regime, regime_info = load_regime()

    # Score active picks
    scored = run_ensemble(regime, regime_info)

    # Backtest closed picks
    backtest_results = backtest_regime_weights()

    # Save output
    save_output(scored, regime, backtest_results)

    print(f"\n{'='*70}")
    print(f"  REGIME ENSEMBLE COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    run()

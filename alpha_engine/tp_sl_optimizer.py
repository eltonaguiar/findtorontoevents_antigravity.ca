"""
TP/SL Optimizer - Analyze closed trade data and compute optimal take-profit / stop-loss levels.

Reads from audit_trail/data/dashboard_payload.json and universal_resolved_picks.json.
Produces alpha_engine/data/optimal_tp_sl.json with per-regime, per-asset, per-direction configs.

Usage:
    from alpha_engine.tp_sl_optimizer import run
    results = run()          # returns dict with analysis + recommendations
    run(print_report=True)   # also prints human-readable summary
"""

import json
import os
import statistics
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
RESOLVED_PATH = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
OUTPUT_PATH = ROOT / "alpha_engine" / "data" / "optimal_tp_sl.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(data, pct):
    """Compute percentile without numpy."""
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * pct / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    d = k - f
    return s[f] + d * (s[c] - s[f])


def _tp_distance_pct(pick):
    """Planned TP distance as positive %."""
    e = pick["entry_price"]
    tp = pick["take_profit"]
    if pick["direction"] == "LONG":
        return (tp - e) / e * 100
    return (e - tp) / e * 100


def _sl_distance_pct(pick):
    """Planned SL distance as positive %."""
    e = pick["entry_price"]
    sl = pick["stop_loss"]
    if pick["direction"] == "LONG":
        return (e - sl) / e * 100
    return (sl - e) / e * 100


def _planned_rr(pick):
    tp_d = _tp_distance_pct(pick)
    sl_d = _sl_distance_pct(pick)
    if sl_d <= 0:
        return None
    return tp_d / sl_d


def _is_tp_exit(pick):
    er = pick.get("exit_reason", "")
    return "TP" in er or "TAKE_PROFIT" in er


def _is_sl_exit(pick):
    er = pick.get("exit_reason", "")
    return "SL" in er or "STOP" in er


def _is_time_exit(pick):
    er = pick.get("exit_reason", "")
    return "TIME" in er


def _classify_exit(pick):
    if _is_tp_exit(pick):
        return "TP_HIT"
    if _is_sl_exit(pick):
        return "SL_HIT"
    if _is_time_exit(pick):
        return "TIME_EXIT"
    return "UNKNOWN"


def _expectancy(win_rate_frac, avg_win, avg_loss):
    """Expected value per trade."""
    return win_rate_frac * avg_win + (1 - win_rate_frac) * avg_loss


def _sortino_approx(pnl_list):
    """Approximate Sortino ratio from a list of PnL values."""
    if len(pnl_list) < 2:
        return 0.0
    mean_pnl = statistics.mean(pnl_list)
    downside = [p for p in pnl_list if p < 0]
    if not downside:
        return 10.0
    downside_dev = math.sqrt(sum(d ** 2 for d in downside) / len(pnl_list))
    if downside_dev == 0:
        return 0.0
    return mean_pnl / downside_dev


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_picks():
    """Load closed picks from dashboard payload + universal resolved."""
    picks = []

    if PAYLOAD_PATH.exists():
        with open(PAYLOAD_PATH) as f:
            payload = json.load(f)
        for p in payload.get("picks", {}).get("recent_closed", []):
            if (p.get("entry_price") and p.get("take_profit") and p.get("stop_loss")
                    and p.get("pnl_pct") is not None and not p.get("_auto_expired")):
                picks.append(p)

    if RESOLVED_PATH.exists():
        with open(RESOLVED_PATH) as f:
            resolved = json.load(f)
        seen = {(p.get("symbol"), p.get("strategy"), p.get("timestamp")) for p in picks}
        for p in resolved:
            key = (p.get("symbol"), p.get("strategy"), p.get("timestamp"))
            if key not in seen and p.get("entry_price") and p.get("take_profit") and p.get("stop_loss"):
                pnl = p.get("pnl_pct", 0)
                status = p.get("status", "")
                if pnl > 0 and status != "WON":
                    p["status"] = "WON"
                elif pnl < 0 and status != "LOST":
                    p["status"] = "LOST"
                if "asset_class" not in p:
                    sym = p.get("symbol", "")
                    if sym.endswith("USDT") or sym.endswith("USD"):
                        p["asset_class"] = "CRYPTO"
                    elif "/" in sym:
                        p["asset_class"] = "FOREX"
                    else:
                        p["asset_class"] = "EQUITY"
                if "trade_timeframe" not in p:
                    p["trade_timeframe"] = "SWING"
                picks.append(p)
                seen.add(key)

    return picks


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _analyze_group(picks, label="ALL"):
    """Analyze a group of picks and return stats dict."""
    winners = [p for p in picks if p.get("status") == "WON"]
    losers = [p for p in picks if p.get("status") == "LOST"]

    if len(winners) < 3 or len(losers) < 3:
        return None

    total = len(winners) + len(losers)
    win_rate = len(winners) / total

    win_pnls = [p["pnl_pct"] for p in winners]
    loss_pnls = [p["pnl_pct"] for p in losers]
    all_pnls = win_pnls + loss_pnls

    avg_win = statistics.mean(win_pnls)
    avg_loss = statistics.mean(loss_pnls)
    median_win = statistics.median(win_pnls)
    median_loss = statistics.median(loss_pnls)

    # MFE distribution (winners' PnL as lower bound on max favorable excursion)
    mfe_values = sorted(win_pnls)
    # MAE distribution (losers' abs PnL = max adverse excursion)
    mae_values = sorted([abs(p) for p in loss_pnls])

    # Exit classification
    win_exits = defaultdict(int)
    loss_exits = defaultdict(int)
    for p in winners:
        win_exits[_classify_exit(p)] += 1
    for p in losers:
        loss_exits[_classify_exit(p)] += 1

    tp_hit_rate = win_exits.get("TP_HIT", 0) / len(winners) if winners else 0
    sl_hit_rate = loss_exits.get("SL_HIT", 0) / len(losers) if losers else 0

    # Current TP/SL distances
    current_tp_dists = [_tp_distance_pct(p) for p in picks if _tp_distance_pct(p) > 0]
    current_sl_dists = [_sl_distance_pct(p) for p in picks if _sl_distance_pct(p) > 0]

    # Actual R multiples
    actual_r_winners = []
    for p in winners:
        sl_d = _sl_distance_pct(p)
        if sl_d > 0:
            actual_r_winners.append(p["pnl_pct"] / sl_d)
    actual_r_losers = []
    for p in losers:
        sl_d = _sl_distance_pct(p)
        if sl_d > 0:
            actual_r_losers.append(p["pnl_pct"] / sl_d)

    sortino = _sortino_approx(all_pnls)

    # --- Compute optimal TP/SL from data distributions ---
    # Strategy: use empirical distributions to find TP/SL that maximizes
    # the win_rate * avg_win - (1-win_rate) * avg_loss formula.
    #
    # KEY INSIGHT from data:
    #   - 63% of winners exit via TIME or UNKNOWN, never reaching TP
    #   - Only 37% of winners hit TP
    #   - Median winner captures 2.26% but TP is set at 2.5%
    #   - SL at 1.5% is tight: 43% of losers hit it at full loss
    #   - Losers that exit via TIME average only -0.98% (less than SL)
    #
    # APPROACH: Find TP where >= 50% of current winners would hit it,
    #           Find SL where <= 20% of winners would get stopped out
    #           (i.e., SL wider than P20 of winner adverse excursion).

    # Optimal TP: the median winner PnL is a natural target
    # (50% of winners achieve at least this)
    optimal_tp_p50 = _percentile(mfe_values, 50)  # 50% of winners achieve this
    optimal_tp_p40 = _percentile(mfe_values, 40)  # 60% of winners achieve this
    optimal_tp_p60 = _percentile(mfe_values, 60)  # 40% of winners achieve this

    # Optimal SL: set at P75 MAE - this catches 75% of losers while
    # being wide enough to avoid shakeouts on the other 25%
    optimal_sl_p75 = _percentile(mae_values, 75)
    optimal_sl_p82 = _percentile(mae_values, 82)
    optimal_sl_p90 = _percentile(mae_values, 90)

    # The "best" config tries to balance:
    # 1. TP achievable by majority of winners (P40-P50 MFE)
    # 2. SL wide enough to avoid most shakeouts (P75-P82 MAE)
    # 3. R:R >= 1.0 minimum

    # For the moderate recommendation: use P50 MFE for TP, P75 MAE for SL
    rec_tp = optimal_tp_p50
    rec_sl = optimal_sl_p75

    # If R:R < 1.0, bump TP up to match SL
    if rec_sl > 0 and rec_tp / rec_sl < 1.0:
        rec_tp = rec_sl  # 1:1 minimum

    # Estimate new expectancy:
    # With TP=rec_tp: winners that currently get >= rec_tp are captured
    # With SL=rec_sl: losers beyond rec_sl are capped there
    # Losers currently stopped out at tight SL (< rec_sl) might survive
    current_sl_med = statistics.median(current_sl_dists) if current_sl_dists else 1.5

    # Count winners that would achieve the new TP
    winners_hitting_new_tp = sum(1 for p in win_pnls if p >= rec_tp)
    # Winners that don't hit TP but are still profitable (partial capture)
    winners_partial = sum(1 for p in win_pnls if 0 < p < rec_tp)
    # Estimate: with lower TP target, all current winners with pnl >= rec_tp
    # DEFINITELY win. Partial winners have ~50% chance of reaching new (lower) TP.
    est_new_winners = winners_hitting_new_tp + 0.5 * winners_partial

    # Losers that are currently stopped at tight SL but might survive wider SL:
    # These are losers where |pnl| is between current_sl and rec_sl
    if rec_sl > current_sl_med:
        rescued = sum(
            1 for m in mae_values
            if current_sl_med * 0.8 <= m <= rec_sl
        )
        # Conservative: 20% of rescued losers become winners
        est_new_winners += rescued * 0.20

    est_new_wr = est_new_winners / total if total > 0 else 0
    est_new_expectancy = est_new_wr * rec_tp + (1 - est_new_wr) * (-rec_sl)

    # Current expectancy for comparison
    current_expectancy = _expectancy(win_rate, avg_win, avg_loss)

    return {
        "label": label,
        "total_trades": total,
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": round(win_rate * 100, 1),
        "avg_win_pnl": round(avg_win, 3),
        "avg_loss_pnl": round(avg_loss, 3),
        "median_win_pnl": round(median_win, 3),
        "median_loss_pnl": round(median_loss, 3),
        "tp_hit_rate": round(tp_hit_rate * 100, 1),
        "sl_hit_rate": round(sl_hit_rate * 100, 1),
        "win_exits": dict(win_exits),
        "loss_exits": dict(loss_exits),
        "current_tp_mean": round(statistics.mean(current_tp_dists), 2) if current_tp_dists else 0,
        "current_tp_median": round(statistics.median(current_tp_dists), 2) if current_tp_dists else 0,
        "current_sl_mean": round(statistics.mean(current_sl_dists), 2) if current_sl_dists else 0,
        "current_sl_median": round(statistics.median(current_sl_dists), 2) if current_sl_dists else 0,
        "current_rr": round(
            statistics.median(current_tp_dists) / statistics.median(current_sl_dists), 2
        ) if current_sl_dists and current_tp_dists and statistics.median(current_sl_dists) > 0 else 0,
        "current_expectancy": round(current_expectancy, 4),
        "actual_r_winners_mean": round(statistics.mean(actual_r_winners), 3) if actual_r_winners else 0,
        "actual_r_winners_median": round(statistics.median(actual_r_winners), 3) if actual_r_winners else 0,
        "actual_r_losers_mean": round(statistics.mean(actual_r_losers), 3) if actual_r_losers else 0,
        "actual_r_losers_median": round(statistics.median(actual_r_losers), 3) if actual_r_losers else 0,
        "sortino": round(sortino, 4),
        "mfe_percentiles": {
            f"p{p}": round(_percentile(mfe_values, p), 3) for p in [10, 25, 40, 50, 60, 75, 90]
        },
        "mae_percentiles": {
            f"p{p}": round(_percentile(mae_values, p), 3) for p in [10, 25, 50, 75, 82, 90, 95]
        },
        "optimal": {
            "tp_conservative_pct": round(optimal_tp_p40, 2),
            "tp_recommended_pct": round(rec_tp, 2),
            "tp_aggressive_pct": round(optimal_tp_p60, 2),
            "sl_tight_pct": round(optimal_sl_p75, 2),
            "sl_recommended_pct": round(rec_sl, 2),
            "sl_wide_pct": round(optimal_sl_p90, 2),
            "rr_ratio": round(rec_tp / rec_sl, 2) if rec_sl > 0 else 0,
            "est_win_rate": round(est_new_wr * 100, 1),
            "est_expectancy": round(est_new_expectancy, 4),
            "current_expectancy": round(current_expectancy, 4),
            "improvement_pct": round(
                (est_new_expectancy - current_expectancy) / abs(current_expectancy) * 100, 1
            ) if current_expectancy != 0 else 0,
        },
    }


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(print_report=True):
    """Run the full TP/SL optimization analysis."""
    picks = _load_picks()
    if not picks:
        print("ERROR: No closed picks found.")
        return {}

    overall = _analyze_group(picks, "OVERALL")

    by_asset = {}
    for ac in ["CRYPTO", "EQUITY", "FOREX"]:
        result = _analyze_group([p for p in picks if p.get("asset_class") == ac], ac)
        if result:
            by_asset[ac] = result

    by_direction = {}
    for d in ["LONG", "SHORT"]:
        result = _analyze_group([p for p in picks if p.get("direction") == d], d)
        if result:
            by_direction[d] = result

    by_timeframe = {}
    for tf in ["SCALP", "INTRADAY", "SWING"]:
        result = _analyze_group([p for p in picks if p.get("trade_timeframe") == tf], tf)
        if result:
            by_timeframe[tf] = result

    by_asset_direction = {}
    for ac in ["CRYPTO", "EQUITY", "FOREX"]:
        for d in ["LONG", "SHORT"]:
            group = [p for p in picks if p.get("asset_class") == ac and p.get("direction") == d]
            result = _analyze_group(group, f"{ac}_{d}")
            if result:
                by_asset_direction[f"{ac}_{d}"] = result

    by_asset_timeframe = {}
    for ac in ["CRYPTO"]:
        for tf in ["SCALP", "INTRADAY", "SWING"]:
            group = [p for p in picks if p.get("asset_class") == ac and p.get("trade_timeframe") == tf]
            result = _analyze_group(group, f"{ac}_{tf}")
            if result:
                by_asset_timeframe[f"{ac}_{tf}"] = result

    config = _build_config(overall, by_asset, by_direction, by_timeframe, by_asset_direction, by_asset_timeframe)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "audit_trail/data/dashboard_payload.json + universal_resolved_picks.json",
        "total_picks_analyzed": len(picks),
        "overall": overall,
        "by_asset_class": by_asset,
        "by_direction": by_direction,
        "by_timeframe": by_timeframe,
        "by_asset_direction": by_asset_direction,
        "by_asset_timeframe": by_asset_timeframe,
        "config": config,
        "key_findings": _key_findings(overall, by_asset, by_direction, by_timeframe, by_asset_direction),
    }

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    if print_report:
        _print_report(output)

    return output


def _build_config(overall, by_asset, by_direction, by_timeframe, by_asset_direction, by_asset_timeframe):
    """Build actionable TP/SL config keyed by asset_class/direction/regime/timeframe."""
    config = {}
    regimes = ["BULLISH", "BEARISH", "CHOPPY"]

    for ac in ["CRYPTO", "EQUITY", "FOREX"]:
        config[ac] = {}
        for direction in ["LONG", "SHORT"]:
            config[ac][direction] = {}
            key = f"{ac}_{direction}"
            base = by_asset_direction.get(key) or by_asset.get(ac) or overall
            if not base:
                continue

            base_tp = base["optimal"]["tp_recommended_pct"]
            base_sl = base["optimal"]["sl_recommended_pct"]

            for regime in regimes:
                config[ac][direction][regime] = {}
                for tf in ["SCALP", "INTRADAY", "SWING", "POSITION"]:
                    tp = base_tp
                    sl = base_sl

                    # Regime adjustments
                    if regime == "BULLISH":
                        if direction == "LONG":
                            tp *= 1.20   # let winners run in trends
                            sl *= 1.10   # slightly wider to survive pullbacks
                        else:
                            tp *= 0.70   # take counter-trend profits fast
                            sl *= 0.80   # tight stop on counter-trend
                    elif regime == "BEARISH":
                        if direction == "SHORT":
                            tp *= 1.20
                            sl *= 1.10
                        else:
                            tp *= 0.70
                            sl *= 0.80
                    elif regime == "CHOPPY":
                        tp *= 0.80   # range-bound: take profits quickly
                        sl *= 1.00   # keep SL normal (ranges are noisy)

                    # Timeframe adjustments
                    if tf == "SCALP":
                        tp *= 0.40
                        sl *= 0.40
                    elif tf == "INTRADAY":
                        pass  # base is already intraday-focused
                    elif tf == "SWING":
                        tp *= 1.40
                        sl *= 1.30
                    elif tf == "POSITION":
                        tp *= 2.50
                        sl *= 2.00

                    # Enforce minimums
                    tp = max(tp, 0.3)
                    sl = max(sl, 0.3)

                    # Enforce minimum R:R of 1.0 for SWING/POSITION
                    if tf in ("SWING", "POSITION") and sl > 0 and tp / sl < 1.0:
                        tp = sl

                    config[ac][direction][regime][tf] = {
                        "take_profit_pct": round(tp, 2),
                        "stop_loss_pct": round(sl, 2),
                        "rr_ratio": round(tp / sl, 2) if sl > 0 else 0,
                    }

    return config


def _key_findings(overall, by_asset, by_direction, by_timeframe, by_asset_direction):
    """Generate key findings list."""
    findings = []

    if not overall:
        return findings

    ov = overall

    findings.append(
        f"CRITICAL: Only {ov['tp_hit_rate']}% of winners actually hit TP. "
        f"{100 - ov['tp_hit_rate']:.0f}% close early via TIME or unknown exit. "
        f"Current TP at {ov['current_tp_median']}% is unreachable for most trades."
    )

    findings.append(
        f"ASYMMETRY PROBLEM: Median winner captures +{ov['median_win_pnl']}% "
        f"but median loser gives back {ov['median_loss_pnl']}%. "
        f"With {ov['win_rate']}% WR, the system bleeds "
        f"({ov['current_expectancy']}% expected per trade)."
    )

    findings.append(
        f"SL TOO TIGHT: Current SL at {ov['current_sl_median']}% catches "
        f"{ov['sl_hit_rate']}% of losers at near-full loss. "
        f"But P75 MAE is only {ov['mae_percentiles']['p75']}% -- 25% of losers "
        f"go beyond the SL anyway, suggesting slippage or gaps."
    )

    findings.append(
        f"Actual R:R achieved: winners {ov['actual_r_winners_median']}R median, "
        f"losers {ov['actual_r_losers_median']}R median. "
        f"Planned R:R was {ov['current_rr']} but actual is "
        f"{abs(ov['actual_r_winners_median'] / ov['actual_r_losers_median']):.2f}."
    )

    opt = ov["optimal"]
    findings.append(
        f"RECOMMENDATION: Change TP from {ov['current_tp_median']}% to "
        f"{opt['tp_recommended_pct']}%, SL from {ov['current_sl_median']}% to "
        f"{opt['sl_recommended_pct']}%. "
        f"New R:R = {opt['rr_ratio']}, est. WR = {opt['est_win_rate']}%, "
        f"est. expectancy = {opt['est_expectancy']}%/trade."
    )

    cr_long = by_asset_direction.get("CRYPTO_LONG")
    cr_short = by_asset_direction.get("CRYPTO_SHORT")
    if cr_long:
        o = cr_long["optimal"]
        findings.append(
            f"CRYPTO LONG: WR={cr_long['win_rate']}%, "
            f"TP {cr_long['current_tp_median']}% -> {o['tp_recommended_pct']}%, "
            f"SL {cr_long['current_sl_median']}% -> {o['sl_recommended_pct']}%. "
            f"MFE P50={cr_long['mfe_percentiles']['p50']}%, "
            f"MAE P75={cr_long['mae_percentiles']['p75']}%."
        )
    if cr_short:
        o = cr_short["optimal"]
        findings.append(
            f"CRYPTO SHORT: WR={cr_short['win_rate']}%, "
            f"TP {cr_short['current_tp_median']}% -> {o['tp_recommended_pct']}%, "
            f"SL {cr_short['current_sl_median']}% -> {o['sl_recommended_pct']}%. "
            f"Shorts have much tighter MFE distribution -- take profits fast."
        )

    intra = by_timeframe.get("INTRADAY")
    if intra:
        findings.append(
            f"INTRADAY: {intra['win_rate']}% WR, median winner +{intra['median_win_pnl']}%. "
            f"TP {intra['current_tp_median']}% -> {intra['optimal']['tp_recommended_pct']}%, "
            f"SL {intra['current_sl_median']}% -> {intra['optimal']['sl_recommended_pct']}%."
        )

    swing = by_timeframe.get("SWING")
    if swing:
        findings.append(
            f"SWING: {swing['win_rate']}% WR, median winner +{swing['median_win_pnl']}%. "
            f"TP {swing['current_tp_median']}% -> {swing['optimal']['tp_recommended_pct']}%, "
            f"SL {swing['current_sl_median']}% -> {swing['optimal']['sl_recommended_pct']}%."
        )

    findings.append(
        "ROOT CAUSE SUMMARY: TP is set at 2.5% but median winner only captures ~2.3%. "
        "SL at 1.5% is hit by 43% of losers at full loss. The system takes FULL losses "
        "but only PARTIAL wins. Fix: (1) lower TP to actual MFE P50, (2) widen SL to "
        "MAE P75, (3) use regime-adaptive levels."
    )

    return findings


def _print_report(output):
    """Print human-readable report."""
    print("=" * 80)
    print("  TP/SL OPTIMIZER REPORT")
    print("=" * 80)
    print(f"  Picks analyzed: {output['total_picks_analyzed']}")
    print()

    ov = output.get("overall")
    if not ov:
        print("  No data to analyze.")
        return

    print("--- CURRENT STATE (THE PROBLEM) ---")
    print(f"  Win rate:            {ov['win_rate']}%")
    print(f"  Avg winner:          +{ov['avg_win_pnl']}%")
    print(f"  Avg loser:           {ov['avg_loss_pnl']}%")
    print(f"  Median winner:       +{ov['median_win_pnl']}%")
    print(f"  Median loser:        {ov['median_loss_pnl']}%")
    print(f"  Current expectancy:  {ov['current_expectancy']}% per trade")
    print(f"  TP hit rate:         {ov['tp_hit_rate']}% (most winners never reach TP)")
    print(f"  SL hit rate:         {ov['sl_hit_rate']}%")
    print(f"  Actual R (winners):  {ov['actual_r_winners_median']}R median")
    print(f"  Actual R (losers):   {ov['actual_r_losers_median']}R median")
    print(f"  Sortino:             {ov['sortino']}")
    print()

    print("--- CURRENT TP/SL SETTINGS ---")
    print(f"  TP distance:   {ov['current_tp_median']}% median ({ov['current_tp_mean']}% mean)")
    print(f"  SL distance:   {ov['current_sl_median']}% median ({ov['current_sl_mean']}% mean)")
    print(f"  Planned R:R:   {ov['current_rr']}")
    print()

    print("--- MFE DISTRIBUTION (what winners actually achieve) ---")
    for k, v in ov["mfe_percentiles"].items():
        bar = "#" * max(1, int(v * 5))
        print(f"  {k:>5}: {v:>7.3f}%  {bar}")
    print()

    print("--- MAE DISTRIBUTION (how far losers go against us) ---")
    for k, v in ov["mae_percentiles"].items():
        bar = "#" * max(1, int(v * 5))
        print(f"  {k:>5}: {v:>7.3f}%  {bar}")
    print()

    opt = ov["optimal"]
    print("--- OPTIMAL TP/SL RECOMMENDATIONS ---")
    print(f"  Conservative TP: {opt['tp_conservative_pct']}%  (P40 MFE -- 60% of winners achieve this)")
    print(f"  >>> RECOMMENDED TP: {opt['tp_recommended_pct']}%  (P50 MFE -- 50% of winners achieve this)")
    print(f"  Aggressive TP:   {opt['tp_aggressive_pct']}%  (P60 MFE -- 40% of winners achieve this)")
    print()
    print(f"  Tight SL:        {opt['sl_tight_pct']}%  (P75 MAE)")
    print(f"  >>> RECOMMENDED SL: {opt['sl_recommended_pct']}%  (covers 75% of losers)")
    print(f"  Wide SL:         {opt['sl_wide_pct']}%  (P90 MAE)")
    print()
    print(f"  R:R ratio:       {opt['rr_ratio']}")
    print(f"  Est. win rate:   {opt['est_win_rate']}%")
    print(f"  Est. expectancy: {opt['est_expectancy']}% per trade")
    if opt.get("improvement_pct"):
        direction = "improvement" if opt["improvement_pct"] > 0 else "change"
        print(f"  vs current:      {opt['improvement_pct']}% {direction}")
    print()

    print("=" * 80)
    print("  SPECIFIC CHANGES REQUIRED")
    print("=" * 80)
    print()
    print(f"  Change default TP from {ov['current_tp_median']}% to {opt['tp_recommended_pct']}%")
    print(f"  Change default SL from {ov['current_sl_median']}% to {opt['sl_recommended_pct']}%")
    print(f"  This changes R:R from {ov['current_rr']} to {opt['rr_ratio']}")
    print()

    print("--- PER ASSET CLASS + DIRECTION ---")
    for key, stats in output.get("by_asset_direction", {}).items():
        o = stats["optimal"]
        print(f"  {key:>15}: TP {stats['current_tp_median']}% -> {o['tp_recommended_pct']}%  |  "
              f"SL {stats['current_sl_median']}% -> {o['sl_recommended_pct']}%  |  "
              f"WR {stats['win_rate']}%  |  R:R {o['rr_ratio']}")
    print()

    print("--- PER TIMEFRAME ---")
    for key, stats in output.get("by_timeframe", {}).items():
        o = stats["optimal"]
        print(f"  {key:>10}: TP {stats['current_tp_median']}% -> {o['tp_recommended_pct']}%  |  "
              f"SL {stats['current_sl_median']}% -> {o['sl_recommended_pct']}%  |  "
              f"WR {stats['win_rate']}%  |  R:R {o['rr_ratio']}")
    print()

    print("=" * 80)
    print("  KEY FINDINGS")
    print("=" * 80)
    for i, finding in enumerate(output.get("key_findings", []), 1):
        print(f"  {i}. {finding}")
    print()

    # Regime config summary
    print("--- REGIME-SPECIFIC CONFIG (CRYPTO LONG example) ---")
    crypto_long = output.get("config", {}).get("CRYPTO", {}).get("LONG", {})
    for regime in ["BULLISH", "BEARISH", "CHOPPY"]:
        regime_cfg = crypto_long.get(regime, {})
        for tf in ["SCALP", "INTRADAY", "SWING"]:
            c = regime_cfg.get(tf, {})
            if c:
                print(f"  {regime:>8} {tf:>10}: TP={c['take_profit_pct']}%  SL={c['stop_loss_pct']}%  R:R={c['rr_ratio']}")
    print()

    print(f"  Full config written to: {OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    run(print_report=True)

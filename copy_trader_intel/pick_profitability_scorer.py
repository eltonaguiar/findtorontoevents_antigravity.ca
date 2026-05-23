#!/usr/bin/env python3
"""
Pick Profitability Scorer & Portfolio Optimizer
================================================
Scores every pick with an elite_score (0-100), applies safety gates,
and builds an optimized tradeable portfolio.

Outputs:
  - data/scored_picks.json        -- all picks with elite_scores
  - data/tradeable_portfolio.json -- optimized best-20 portfolio
  - data/pick_rejection_log.json  -- why picks were rejected
"""
import sys, os, io, json, math, logging
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# ── Windows UTF-8 fix ────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("pick_scorer")

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
ALPHA_DATA = BASE.parent / "alpha_engine" / "data"

# ── Strategy name normalizer ─────────────────────────────────────────
# Maps various pick strategy names to the canonical backtest strategy key
STRATEGY_ALIAS = {
    "forex_rsi2_mean_reversion": "rsi_mean_reversion",
    "forex_rsi2": "rsi_mean_reversion",
    "stocks_rsi2": "rsi_mean_reversion",
    "futures_rsi2": "rsi_mean_reversion",
    "forex_carry_momentum": "momentum_20d",
    "forex_carry": "momentum_20d",
    "futures_momentum": "momentum_20d",
    "futures_bb": "bollinger_breakout",
    "futures_ema": "ema_crossover",
    "stocks_ema": "ema_crossover",
    "ig_contrarian": "momentum_20d",
    "cot_positioning": "momentum_20d",
    "cftc_cot_weekly": "momentum_20d",
    "yahoo_analysts": "momentum_20d",
    "smart_money": "momentum_20d",
}

# Asset-class normalizer
ASSET_CLASS_ALIAS = {
    "forex": "forex",
    "FOREX": "forex",
    "crypto": "crypto",
    "CRYPTO": "crypto",
    "commodity": "commodities",
    "COMMODITY": "commodities",
    "commodities": "commodities",
    "COMMODITIES": "commodities",
    "equity": "stocks",
    "EQUITY": "stocks",
    "stocks": "stocks",
    "STOCKS": "stocks",
    "futures": "index_futures",
    "FUTURES": "index_futures",
    "index_futures": "index_futures",
    "INDEX_FUTURES": "index_futures",
}

# Academic-backed strategies (known research citations)
ACADEMIC_STRATEGIES = {
    "rsi_mean_reversion",   # Connors RSI(2)
    "momentum_20d",         # Jegadeesh & Titman
    "bollinger_breakout",   # Bollinger (1992)
    "ema_crossover",        # Golden/Death cross literature
    "macd_crossover",       # Appel (1979)
    "atr_breakout",         # Keltner / ATR literature
    "forex_carry_momentum", # Burnside et al. (2011)
    "carry_trade",          # Lustig & Verdelhan (2007)
}


# =====================================================================
# 1. Elite Score Calculation (0-100)
# =====================================================================

def _get_backtest_metrics(strategy_name, asset_class, backtest_data, leaderboard_data):
    """Look up backtest metrics for a strategy+asset_class combo."""
    metrics = {
        "win_rate": None,
        "profit_factor": None,
        "sharpe_ratio": None,
        "walk_forward_oos_positive": None,
        "trade_count": 0,
    }

    canon_strategy = STRATEGY_ALIAS.get(strategy_name, strategy_name)
    canon_ac = ASSET_CLASS_ALIAS.get(asset_class, asset_class)

    # Try backtest_results walk-forward first
    if backtest_data and "results" in backtest_data:
        ac_data = backtest_data["results"].get(canon_ac, {})
        strat_data = ac_data.get(canon_strategy, {})
        wf = strat_data.get("walk_forward", {})
        oos = wf.get("out_of_sample", {})
        ins = wf.get("in_sample", {})
        grid = strat_data.get("grid_top5", [])

        if oos:
            metrics["win_rate"] = oos.get("win_rate")
            metrics["profit_factor"] = oos.get("profit_factor")
            metrics["sharpe_ratio"] = oos.get("sharpe_ratio")
            metrics["trade_count"] = oos.get("trade_count", 0)
            oos_pnl = oos.get("total_pnl_pct", 0)
            metrics["walk_forward_oos_positive"] = (oos_pnl > 0) if oos_pnl is not None else None
        elif ins:
            metrics["win_rate"] = ins.get("win_rate")
            metrics["profit_factor"] = ins.get("profit_factor")
            metrics["sharpe_ratio"] = ins.get("sharpe_ratio")
            metrics["trade_count"] = ins.get("trade_count", 0)
        elif grid:
            best = grid[0]
            metrics["win_rate"] = best.get("win_rate")
            metrics["profit_factor"] = best.get("profit_factor")
            metrics["sharpe_ratio"] = best.get("sharpe_ratio")
            metrics["trade_count"] = best.get("trade_count", 0)

    # Enrich from leaderboard if available
    if leaderboard_data and "leaderboard" in leaderboard_data:
        for entry in leaderboard_data["leaderboard"]:
            entry_strat = entry.get("strategy", "")
            entry_ac = ASSET_CLASS_ALIAS.get(entry.get("asset_class", ""), "")
            if entry_strat == canon_strategy and entry_ac == canon_ac:
                m = entry.get("metrics", {})
                if metrics["win_rate"] is None and m.get("win_rate"):
                    metrics["win_rate"] = m["win_rate"] / 100.0  # leaderboard uses 0-100
                if metrics["profit_factor"] is None:
                    metrics["profit_factor"] = m.get("profit_factor")
                if metrics["sharpe_ratio"] is None:
                    metrics["sharpe_ratio"] = m.get("sharpe_ratio")
                metrics["trade_count"] = max(metrics["trade_count"], m.get("wins", 0) + m.get("losses", 0))
                break

    return metrics


def calculate_elite_score(pick, backtest_data, leaderboard_data):
    """
    Calculate elite_score (0-100) for a single pick.

    Breakdown:
      A. Strategy Quality   (40 pts max)
      B. Pick Quality        (30 pts max)
      C. Risk Management     (20 pts max)
      D. Source Reliability   (10 pts max)
    """
    score = 0
    breakdown = {}

    strategy = pick.get("strategy", "")
    asset_class = pick.get("asset_class") or pick.get("category", "crypto")
    bt = _get_backtest_metrics(strategy, asset_class, backtest_data, leaderboard_data)

    # ── A. Strategy Quality (40 pts) ──────────────────────────────────
    strat_score = 0
    wr = bt["win_rate"]
    if wr is not None:
        # Normalize: some sources use 0-1, some 0-100
        if wr > 1:
            wr = wr / 100.0
        if wr >= 0.65:
            strat_score += 15
        elif wr >= 0.55:
            strat_score += 10

    pf = bt["profit_factor"]
    if pf is not None and pf >= 1.5:
        strat_score += 10

    sharpe = bt["sharpe_ratio"]
    if sharpe is not None and sharpe >= 1.0:
        strat_score += 10

    if bt["walk_forward_oos_positive"] is True:
        strat_score += 5

    breakdown["strategy_quality"] = strat_score
    score += strat_score

    # ── B. Pick Quality (30 pts) ──────────────────────────────────────
    pick_score = 0

    rr = pick.get("risk_reward", 0)
    if rr == 0:
        # Calculate from TP/SL/entry if not provided
        entry = pick.get("entry_price", 0)
        tp = pick.get("take_profit", 0)
        sl = pick.get("stop_loss", 0)
        if entry and tp and sl and abs(entry - sl) > 0:
            rr = abs(tp - entry) / abs(entry - sl)
    if rr >= 2.0:
        pick_score += 10
    elif rr >= 1.5:
        pick_score += 5

    conf = pick.get("confidence") or pick.get("ml_score") or 0
    if conf >= 0.70:
        pick_score += 10
    elif conf >= 0.60:
        pick_score += 5

    # RSI check (not at extremes)
    rsi = pick.get("extra", {}).get("rsi14") or pick.get("extra", {}).get("rsi2")
    if rsi is not None:
        if 20 <= rsi <= 80:
            pick_score += 5
    else:
        # No RSI data -- give benefit of the doubt (3 pts partial)
        pick_score += 3

    # Volume confirmation
    vol_24h = pick.get("volume_24h_usd", 0)
    if vol_24h and vol_24h > 1_000_000:
        pick_score += 5
    elif pick.get("extra", {}).get("vol_ratio", 0) and pick["extra"]["vol_ratio"] > 1.0:
        pick_score += 5

    breakdown["pick_quality"] = pick_score
    score += pick_score

    # ── C. Risk Management (20 pts) ──────────────────────────────────
    risk_score = 0
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    cat = (pick.get("category") or pick.get("asset_class") or "").lower()
    norm_cat = ASSET_CLASS_ALIAS.get(cat, cat)

    if entry and sl:
        sl_pct = abs(entry - sl) / entry * 100
        max_sl = {"forex": 5, "commodities": 10, "stocks": 15, "index_futures": 10, "crypto": 15}.get(norm_cat, 15)
        if sl_pct <= max_sl:
            risk_score += 10

    if entry and tp:
        tp_pct = abs(tp - entry) / entry * 100
        if 0.1 <= tp_pct <= 50:  # "realistic" range
            risk_score += 5

    # Max hold defined (some picks include hold_days or max_hold)
    if pick.get("hold_days") is not None or pick.get("max_hold") is not None:
        risk_score += 5
    else:
        # Partial credit if strategy implies bounded hold
        risk_score += 2

    breakdown["risk_management"] = risk_score
    score += risk_score

    # ── D. Source Reliability (10 pts) ────────────────────────────────
    src_score = 0
    canon_strat = STRATEGY_ALIAS.get(strategy, strategy)
    if canon_strat in ACADEMIC_STRATEGIES or strategy in ACADEMIC_STRATEGIES:
        src_score += 5

    # Multiple confirming sources (signal_count or all_signals)
    sig_count = pick.get("signal_count", 0)
    all_sigs = pick.get("all_signals", [])
    if sig_count >= 2 or len(all_sigs) >= 2:
        src_score += 3

    # Forward-tested with >15 trades
    fwd_trades = pick.get("forward_trades", 0)
    if fwd_trades > 15:
        src_score += 2

    breakdown["source_reliability"] = src_score
    score += src_score

    final = min(100, score)
    return final, breakdown


# =====================================================================
# 2. Trade Safety Gates
# =====================================================================

def is_safe_to_trade(pick, elite_score):
    """
    Return (passed: bool, reason: str).
    A pick must pass ALL gates to be marked TRADEABLE.
    """
    reasons = []

    # Gate 1: Minimum elite score
    if elite_score < 40:
        return False, f"Elite score {elite_score} < 40 minimum"

    # Gate 2: Risk:Reward minimum
    rr = pick.get("risk_reward", 0)
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    if rr == 0 and entry and tp and sl and abs(entry - sl) > 0:
        rr = abs(tp - entry) / abs(entry - sl)
    if rr < 1.0:
        return False, f"R:R {rr:.2f} below 1.0"

    # Gate 3: TP/SL sanity check
    if not entry or not tp or not sl:
        return False, "Missing entry/TP/SL prices"

    direction = pick.get("direction", "").upper()
    if direction == "LONG":
        if tp <= entry:
            return False, "TP <= entry for LONG"
        if sl >= entry:
            return False, "SL >= entry for LONG"
    elif direction == "SHORT":
        if tp >= entry:
            return False, "TP >= entry for SHORT"
        if sl <= entry:
            return False, "SL <= entry for SHORT"
    else:
        return False, f"Unknown direction: {direction}"

    # Gate 4: TP distance sanity by asset class
    tp_pct = abs(tp - entry) / entry * 100
    cat = (pick.get("category") or pick.get("asset_class") or "").lower()
    norm_cat = ASSET_CLASS_ALIAS.get(cat, cat)

    limits = {"forex": 5, "commodities": 20, "stocks": 30, "index_futures": 15, "crypto": 50}
    max_tp = limits.get(norm_cat, 50)
    if tp_pct > max_tp:
        return False, f"{norm_cat} TP {tp_pct:.1f}% exceeds {max_tp}% limit"

    # Gate 5: Confidence minimum
    conf = pick.get("confidence") or pick.get("ml_score") or 0
    if conf < 0.50:
        return False, f"Confidence {conf:.2f} below 0.50"

    # Gate 6: SL distance sanity
    sl_pct = abs(entry - sl) / entry * 100
    sl_limits = {"forex": 5, "commodities": 15, "stocks": 20, "index_futures": 10, "crypto": 20}
    max_sl = sl_limits.get(norm_cat, 20)
    if sl_pct > max_sl:
        return False, f"{norm_cat} SL {sl_pct:.1f}% exceeds {max_sl}% limit"

    return True, "PASSED"


# =====================================================================
# 3. Portfolio Optimization
# =====================================================================

def _kelly_fraction(win_rate, avg_win, avg_loss):
    """Calculate Kelly fraction, capped at 5%."""
    if avg_win <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.02  # default conservative
    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    return max(0.01, min(kelly, 0.05))


def optimize_portfolio(scored_picks, max_positions=20):
    """
    Select the best picks for a tradeable portfolio.

    Diversification rules:
      - Max 3 picks per symbol
      - Max 40% same direction in any asset class
      - At least 2 asset classes represented (soft)
      - Max 5 per asset-class bucket (forex, futures, commodity, equity/stock)
    """
    # Sort by elite_score descending
    candidates = sorted(scored_picks, key=lambda p: p.get("elite_score", 0), reverse=True)

    portfolio = []
    symbol_counts = defaultdict(int)
    ac_counts = defaultdict(int)
    ac_direction_counts = defaultdict(lambda: defaultdict(int))

    AC_MAX = 5
    SYM_MAX = 3

    for pick in candidates:
        if len(portfolio) >= max_positions:
            break

        sym = pick.get("symbol", "")
        cat = (pick.get("category") or pick.get("asset_class") or "").lower()
        norm_cat = ASSET_CLASS_ALIAS.get(cat, cat)
        direction = pick.get("direction", "").upper()

        # Rule: max per symbol
        if symbol_counts[sym] >= SYM_MAX:
            continue

        # Rule: max per asset class
        if ac_counts[norm_cat] >= AC_MAX:
            continue

        # Rule: max 40% same direction in asset class
        ac_total = ac_counts[norm_cat]
        ac_dir = ac_direction_counts[norm_cat][direction]
        if ac_total > 0 and ac_dir / (ac_total + 1) > 0.40 and ac_total >= 3:
            # Would exceed 40% same-direction — skip unless it's the only direction
            if ac_direction_counts[norm_cat].get("LONG", 0) > 0 and ac_direction_counts[norm_cat].get("SHORT", 0) > 0:
                continue

        # Accept pick
        symbol_counts[sym] += 1
        ac_counts[norm_cat] += 1
        ac_direction_counts[norm_cat][direction] += 1

        # Position sizing via Kelly
        wr = pick.get("forward_wr", 0) or 0.50
        rr = pick.get("risk_reward", 1.5)
        avg_win = rr  # approximate
        avg_loss = 1.0
        kelly = _kelly_fraction(wr, avg_win, avg_loss)

        pick_out = dict(pick)
        pick_out["portfolio_allocation_pct"] = round(kelly * 100, 2)
        pick_out["portfolio_rank"] = len(portfolio) + 1
        portfolio.append(pick_out)

    # Soft check: at least 2 asset classes
    unique_ac = set(ASSET_CLASS_ALIAS.get((p.get("category") or p.get("asset_class") or "").lower(), "other") for p in portfolio)
    if len(unique_ac) < 2 and len(portfolio) > 5:
        log.warning("Portfolio has only %d asset class(es): %s", len(unique_ac), unique_ac)

    return portfolio


# =====================================================================
# 4. Grading helper
# =====================================================================

def elite_grade(score):
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# =====================================================================
# 5. Main Pipeline
# =====================================================================

def _load_json(path):
    """Load JSON safely, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Could not load %s: %s", path, e)
        return None


def _extract_picks(data):
    """Extract pick list from various JSON structures."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "picks" in data:
            return data["picks"]
        if "active_picks" in data:
            return data["active_picks"]
    return []


def run_pipeline():
    """Score all picks, apply gates, optimize portfolio, save results."""
    now = datetime.now(timezone.utc).isoformat()

    # ── Load data ─────────────────────────────────────────────────────
    alpha_picks = _extract_picks(_load_json(ALPHA_DATA / "active_picks.json"))
    multi_picks = _extract_picks(_load_json(DATA / "multi_asset_picks.json"))
    cta_picks = _extract_picks(_load_json(DATA / "active_picks.json"))
    backtest_data = _load_json(DATA / "backtest_results.json")
    leaderboard_data = _load_json(DATA / "leaderboard.json")

    all_picks = []
    seen_ids = set()
    for src_name, src_picks in [("alpha_engine", alpha_picks), ("multi_asset", multi_picks), ("copy_trader", cta_picks)]:
        for p in src_picks:
            pid = p.get("id", "")
            if pid and pid in seen_ids:
                continue
            seen_ids.add(pid)
            p["_source_file"] = src_name
            all_picks.append(p)

    log.info("Loaded %d total unique picks (alpha=%d, multi=%d, cta=%d)",
             len(all_picks), len(alpha_picks), len(multi_picks), len(cta_picks))

    # ── Score every pick ──────────────────────────────────────────────
    scored = []
    rejections = []
    tradeable = []
    gate_stats = defaultdict(int)

    for pick in all_picks:
        es, breakdown = calculate_elite_score(pick, backtest_data, leaderboard_data)
        grade = elite_grade(es)

        pick["elite_score"] = es
        pick["elite_grade"] = grade
        pick["score_breakdown"] = breakdown

        passed, reason = is_safe_to_trade(pick, es)
        pick["safety_gate_passed"] = passed
        pick["safety_gate_reason"] = reason

        if passed:
            pick["trade_status"] = "TRADEABLE"
            tradeable.append(pick)
        else:
            pick["trade_status"] = "FORWARD_TEST_ONLY"
            rejections.append({
                "id": pick.get("id", "unknown"),
                "symbol": pick.get("symbol", ""),
                "strategy": pick.get("strategy", ""),
                "elite_score": es,
                "rejection_reason": reason,
                "direction": pick.get("direction", ""),
                "confidence": pick.get("confidence", 0),
            })
            gate_stats[reason.split()[0] if reason else "unknown"] += 1

        scored.append(pick)

    log.info("Scored %d picks: %d TRADEABLE, %d FORWARD_TEST_ONLY",
             len(scored), len(tradeable), len(rejections))

    # ── Optimize portfolio ────────────────────────────────────────────
    portfolio = optimize_portfolio(tradeable, max_positions=20)
    log.info("Portfolio: %d positions selected", len(portfolio))

    # ── Summarize ─────────────────────────────────────────────────────
    ac_breakdown = defaultdict(int)
    dir_breakdown = defaultdict(int)
    for p in portfolio:
        cat = (p.get("category") or p.get("asset_class") or "other").lower()
        ac_breakdown[ASSET_CLASS_ALIAS.get(cat, cat)] += 1
        dir_breakdown[p.get("direction", "?")] += 1

    # ── Save results ──────────────────────────────────────────────────
    scored_output = {
        "generated_at": now,
        "total_scored": len(scored),
        "tradeable_count": len(tradeable),
        "rejected_count": len(rejections),
        "picks": scored,
    }
    _save_json(DATA / "scored_picks.json", scored_output)

    portfolio_output = {
        "generated_at": now,
        "total_positions": len(portfolio),
        "asset_class_breakdown": dict(ac_breakdown),
        "direction_breakdown": dict(dir_breakdown),
        "portfolio": portfolio,
    }
    _save_json(DATA / "tradeable_portfolio.json", portfolio_output)

    rejection_output = {
        "generated_at": now,
        "total_rejected": len(rejections),
        "rejection_reasons_summary": dict(gate_stats),
        "rejections": rejections,
    }
    _save_json(DATA / "pick_rejection_log.json", rejection_output)

    # ── Print summary ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PICK PROFITABILITY SCORER -- RESULTS")
    print("=" * 60)
    print(f"  Total picks scored:   {len(scored)}")
    print(f"  Passed safety gates:  {len(tradeable)}")
    print(f"  Rejected:             {len(rejections)}")
    print(f"  Portfolio positions:  {len(portfolio)}")
    print()

    if rejections:
        print("REJECTION REASONS:")
        reason_counts = defaultdict(int)
        for r in rejections:
            reason_counts[r["rejection_reason"]] += 1
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"  [{count:3d}] {reason}")
        print()

    if portfolio:
        print("PORTFOLIO COMPOSITION:")
        for ac, cnt in sorted(ac_breakdown.items()):
            print(f"  {ac:20s}: {cnt} positions")
        print(f"  {'LONG':20s}: {dir_breakdown.get('LONG', 0)}")
        print(f"  {'SHORT':20s}: {dir_breakdown.get('SHORT', 0)}")
        print()

        print("TOP 10 PICKS:")
        for p in portfolio[:10]:
            print(f"  [{p['elite_score']:3d}/{p['elite_grade']}] {p.get('symbol','?'):12s} "
                  f"{p.get('direction','?'):5s} | {p.get('strategy','?'):30s} | "
                  f"alloc={p.get('portfolio_allocation_pct',0):.1f}%")
    print("=" * 60)

    return scored, portfolio, rejections


def _save_json(path, data):
    """Save JSON with UTF-8 encoding."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    log.info("Saved %s", path)


if __name__ == "__main__":
    run_pipeline()

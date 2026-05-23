"""Meta-Strategy Permutation Engine v2.0

Generates every meaningful combination of signal sources, tests them against
historical signal_log outcomes, and identifies statistically significant winners.

Architecture:
  1. Read all system signals from signal_recorder/data/signal_log.db
  2. Generate 2-way, 3-way, 4-way combos + inverse combos
  3. For each combo: compute consensus signal, evaluate against real outcomes
  4. Apply $1000 paper portfolio simulation with realistic fees
  5. Statistical significance testing (binomial p-value, Sharpe, profit factor)
  6. Elimination / resurrection lifecycle management with failure signatures
  7. ML meta-learner training on combo features
  8. Walk-forward validation with purged cross-validation

Combo types (v1.0):
  - MAJORITY: 2+ systems agree → signal
  - UNANIMOUS: all systems agree → signal
  - WEIGHTED: confidence-weighted vote → signal
  - CASCADE: primary confirms → secondary confirms → signal
  - INVERSE: flip losing system signals (contrarian)
  - CONSENSUS_PLUS_INVERSE: winner system + inverted loser

Advanced combo types (v2.0):
  - BAYESIAN: Bayesian probability fusion — P(signal|S1,S2,...Sn) via Bayes' rule
  - DEMPSTER_SHAFER: Dempster-Shafer evidence combination with conflict handling
  - REGIME_AWARE: Regime-gated combination — different logic per market regime
  - ADVERSARIAL: Checks if systems fail at different times (diversification bonus)
"""

import json
import math
import sqlite3
from itertools import combinations
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path

from meta_strategy.db import (
    get_db,
    register_permutation,
    save_result,
    eliminate_combo,
    resurrect_combo,
    get_active_permutations,
    save_walkforward_result,
    save_adversarial_compat,
)

# ── Configuration ──────────────────────────────────────────────
MAX_COMBO_SIZE = 4  # up to 4-way combos
MIN_TRADES = 5  # minimum trades for evaluation
P_VALUE_THRESHOLD = 0.10  # relaxed initially (tighten to 0.05 after data grows)
WIN_RATE_THRESHOLD = 0.52  # must beat 50% + fees
SHARPE_THRESHOLD = 0.3  # minimum Sharpe ratio
MAX_DD_THRESHOLD = 0.30  # max 30% drawdown
PROFIT_FACTOR_THRESHOLD = 1.1  # gross wins / gross losses

# Portfolio simulation
INITIAL_CAPITAL = 1000.0
POSITION_SIZE_PCT = 0.02  # 2% per trade ($20 on $1000)
FEE_PCT = 0.0075  # 0.75% round-trip (taker + slippage + spread)
TP_PCT = 0.05  # 5% take profit
SL_PCT = 0.03  # 3% stop loss

# Elimination
MAX_CONSECUTIVE_FAILURES = 5
PROBATION_THRESHOLD = 3  # 3 consecutive failures → probation

# Time windows for confluence
CONFLUENCE_WINDOWS = [60, 240, 1440]  # 1h, 4h, 24h

# Signal log DB
SIGNAL_DB_PATH = (
    Path(__file__).parent.parent / "signal_recorder" / "data" / "signal_log.db"
)


def _binomial_p_value(wins: int, total: int, null_prob: float = 0.50) -> float:
    """One-sided binomial test: P(X >= wins | p=null_prob)."""
    if total == 0:
        return 1.0
    p_value = 0.0
    for k in range(wins, total + 1):
        binom_coeff = math.comb(total, k)
        p_value += binom_coeff * (null_prob**k) * ((1 - null_prob) ** (total - k))
    return p_value


def _calc_sharpe(pnls: list) -> float:
    """Annualized Sharpe ratio."""
    if len(pnls) < 2:
        return 0.0
    mean = sum(pnls) / len(pnls)
    variance = sum((x - mean) ** 2 for x in pnls) / (len(pnls) - 1)
    std = variance**0.5
    if std == 0:
        return 0.0
    return round(mean / std * (252**0.5), 4)


def _calc_sortino(pnls: list) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    if len(pnls) < 2:
        return 0.0
    mean = sum(pnls) / len(pnls)
    downside = [min(0, p - mean) ** 2 for p in pnls]
    dd = (sum(downside) / len(downside)) ** 0.5
    if dd == 0:
        return 0.0
    return round(mean / dd * (252**0.5), 4)


def _calc_profit_factor(pnls: list) -> float:
    """Gross profit / gross loss."""
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return 99.0 if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def _calc_max_drawdown(pnls: list) -> float:
    """Max drawdown from cumulative returns."""
    if not pnls:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for pnl in pnls:
        equity *= 1 + pnl / 100
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
    return round(max_dd * 100, 4)


def _calc_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly criterion fraction."""
    if avg_loss == 0 or win_rate <= 0:
        return 0.0
    b = avg_win / abs(avg_loss)
    kelly = win_rate - (1 - win_rate) / b
    return round(max(0, min(kelly, 0.25)) * 100, 2)  # cap at 25%


def _simulate_portfolio(pnls: list) -> dict:
    """Simulate $1000 paper portfolio with fees."""
    capital = INITIAL_CAPITAL
    peak = capital
    max_dd = 0.0

    for pnl_pct in pnls:
        # Apply fee on entry+exit
        net_pnl = pnl_pct - (FEE_PCT * 100)
        trade_pnl = capital * POSITION_SIZE_PCT * (net_pnl / 100)
        capital += trade_pnl
        peak = max(peak, capital)
        dd = (peak - capital) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    return {
        "portfolio_final": round(capital, 2),
        "portfolio_return_pct": round(
            (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2
        ),
        "max_drawdown_pct": round(max_dd * 100, 2),
    }


def load_signal_data() -> dict:
    """Load all signals + outcomes from signal_log.db."""
    if not SIGNAL_DB_PATH.exists():
        print(f"Signal log not found: {SIGNAL_DB_PATH}")
        return {"signals": [], "systems": [], "symbols": []}

    conn = sqlite3.connect(str(SIGNAL_DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get signals with 24h outcomes
    rows = conn.execute("""
        SELECT sl.id, sl.timestamp, sl.symbol, sl.system_id, sl.signal,
               sl.strength, sl.price_at_signal, so.pnl_pct, so.check_minutes
        FROM signal_log sl
        JOIN signal_outcomes so ON so.signal_log_id = sl.id
        WHERE sl.signal IN ('BUY', 'SELL')
          AND sl.price_at_signal IS NOT NULL
        ORDER BY sl.timestamp
    """).fetchall()

    signals = [dict(r) for r in rows]
    systems = sorted(set(s["system_id"] for s in signals))
    symbols = sorted(set(s["symbol"] for s in signals))

    conn.close()
    return {"signals": signals, "systems": systems, "symbols": symbols}


def _detect_regime(pnls_window: list) -> str:
    """Detect market regime from recent PnL data.
    Returns 'bull', 'bear', or 'sideways'."""
    if len(pnls_window) < 3:
        return "sideways"
    avg = sum(pnls_window) / len(pnls_window)
    vol = (sum((p - avg) ** 2 for p in pnls_window) / len(pnls_window)) ** 0.5
    if avg > 0.5 and vol < 3.0:
        return "bull"
    elif avg < -0.5 and vol < 3.0:
        return "bear"
    return "sideways"


def _bayesian_fuse(strengths: list, base_prior: float = 0.5) -> float:
    """Bayesian probability fusion.
    Each system's strength is treated as P(signal_correct | system_i).
    Combines via iterated Bayes' rule: P(correct|S1,...,Sn).
    """
    if not strengths:
        return 0.0
    posterior = base_prior
    for s in strengths:
        s = max(0.01, min(0.99, s))  # clamp to avoid 0/1
        # Bayes update: P(H|D) = P(D|H)*P(H) / [P(D|H)*P(H) + P(D|~H)*P(~H)]
        likelihood = s
        likelihood_neg = 1 - s
        numerator = likelihood * posterior
        denominator = numerator + likelihood_neg * (1 - posterior)
        posterior = numerator / denominator if denominator > 0 else 0.5
    return posterior


def _dempster_shafer_combine(masses: list) -> dict:
    """Dempster-Shafer evidence combination.
    Each mass is a dict: {'buy': m1, 'sell': m2, 'uncertain': m3} where sum=1.
    Returns combined mass assignment.
    """
    if not masses:
        return {"buy": 0.33, "sell": 0.33, "uncertain": 0.34}

    combined = masses[0].copy()
    for m in masses[1:]:
        # Compute all pairwise combinations
        buy_buy = combined["buy"] * m["buy"]
        buy_uncertain = combined["buy"] * m["uncertain"]
        uncertain_buy = combined["uncertain"] * m["buy"]

        sell_sell = combined["sell"] * m["sell"]
        sell_uncertain = combined["sell"] * m["uncertain"]
        uncertain_sell = combined["uncertain"] * m["sell"]

        uncertain_uncertain = combined["uncertain"] * m["uncertain"]

        # Conflict: buy*sell + sell*buy
        conflict = combined["buy"] * m["sell"] + combined["sell"] * m["buy"]

        # Normalization factor (1 - conflict)
        norm = 1 - conflict
        if norm <= 0:
            # Total conflict — return maximum uncertainty
            combined = {"buy": 0.0, "sell": 0.0, "uncertain": 1.0}
            continue

        combined = {
            "buy": (buy_buy + buy_uncertain + uncertain_buy) / norm,
            "sell": (sell_sell + sell_uncertain + uncertain_sell) / norm,
            "uncertain": uncertain_uncertain / norm,
        }

    return combined


def _build_time_buckets(signals: list, window_minutes: int) -> dict:
    """Group signals into time windows for confluence detection."""
    buckets = defaultdict(list)
    for sig in signals:
        ts = datetime.fromisoformat(sig["timestamp"].replace("Z", "+00:00"))
        # Bucket by symbol + time window
        bucket_mins = window_minutes
        bucket_idx = int(ts.timestamp() / (bucket_mins * 60))
        bucket_key = (sig["symbol"], bucket_idx)
        buckets[bucket_key].append(sig)
    return buckets


def generate_permutations(systems: list) -> list:
    """Generate all meaningful permutations of systems."""
    permutations = []

    for combo_size in range(2, min(len(systems) + 1, MAX_COMBO_SIZE + 1)):
        for combo in combinations(systems, combo_size):
            sorted_combo = sorted(combo)
            combo_key = "+".join(sorted_combo)

            # Standard majority vote
            permutations.append(
                {
                    "combo_id": f"{combo_key}|majority",
                    "systems": sorted_combo,
                    "logic_type": "majority",
                    "min_agreement": max(2, len(combo) // 2 + 1),
                }
            )

            # Unanimous (all agree)
            if combo_size >= 2:
                permutations.append(
                    {
                        "combo_id": f"{combo_key}|unanimous",
                        "systems": sorted_combo,
                        "logic_type": "unanimous",
                        "min_agreement": len(combo),
                    }
                )

            # Weighted (confidence-weighted average)
            permutations.append(
                {
                    "combo_id": f"{combo_key}|weighted",
                    "systems": sorted_combo,
                    "logic_type": "weighted",
                    "min_agreement": 1,
                }
            )

    # Inverse combos: for each individual system, flip its signals
    for sys_id in systems:
        permutations.append(
            {
                "combo_id": f"INV_{sys_id}|inverse",
                "systems": [sys_id],
                "logic_type": "inverse",
                "min_agreement": 1,
            }
        )

    # Cross-type: winner + inverted loser
    if len(systems) >= 2:
        for winner, loser in combinations(systems, 2):
            permutations.append(
                {
                    "combo_id": f"{winner}+INV_{loser}|consensus_plus_inverse",
                    "systems": [winner, loser],
                    "logic_type": "consensus_plus_inverse",
                    "min_agreement": 2,
                }
            )

    # ── v2.0: Advanced combination types ──────────────────────

    # Bayesian fusion: combine probabilities via Bayes' rule
    for combo_size in range(2, min(len(systems) + 1, MAX_COMBO_SIZE + 1)):
        for combo in combinations(systems, combo_size):
            sorted_combo = sorted(combo)
            combo_key = "+".join(sorted_combo)
            permutations.append(
                {
                    "combo_id": f"{combo_key}|bayesian",
                    "systems": sorted_combo,
                    "logic_type": "bayesian",
                    "min_agreement": 1,
                }
            )

    # Dempster-Shafer: evidence combination with conflict resolution
    for combo_size in range(2, min(len(systems) + 1, MAX_COMBO_SIZE + 1)):
        for combo in combinations(systems, combo_size):
            sorted_combo = sorted(combo)
            combo_key = "+".join(sorted_combo)
            permutations.append(
                {
                    "combo_id": f"{combo_key}|dempster_shafer",
                    "systems": sorted_combo,
                    "logic_type": "dempster_shafer",
                    "min_agreement": 1,
                }
            )

    # Regime-aware: use different logic depending on market regime
    for combo_size in range(2, min(len(systems) + 1, MAX_COMBO_SIZE + 1)):
        for combo in combinations(systems, combo_size):
            sorted_combo = sorted(combo)
            combo_key = "+".join(sorted_combo)
            permutations.append(
                {
                    "combo_id": f"{combo_key}|regime_aware",
                    "systems": sorted_combo,
                    "logic_type": "regime_aware",
                    "min_agreement": 1,
                }
            )

    return permutations


def _evaluate_combo(combo: dict, buckets: dict, window_minutes: int) -> dict:
    """Evaluate a single combo against historical data."""
    systems = combo["systems"]
    logic = combo["logic_type"]
    min_agree = combo["min_agreement"]

    all_pnls = {"BUY": [], "SELL": []}

    for bucket_key, signals in buckets.items():
        # Group by system
        by_system = defaultdict(list)
        for sig in signals:
            if sig["system_id"] in systems or (
                logic in ("inverse", "consensus_plus_inverse")
                and sig["system_id"] in [s.replace("INV_", "") for s in systems]
            ):
                by_system[sig["system_id"]].append(sig)

        for direction in ("BUY", "SELL"):
            votes = 0
            total_strength = 0.0
            pnls_in_bucket = []

            for sys_id in systems:
                actual_sys_id = (
                    sys_id.replace("INV_", "") if "INV_" in sys_id else sys_id
                )
                sys_signals = by_system.get(actual_sys_id, [])

                for sig in sys_signals:
                    sig_dir = sig["signal"]
                    is_inverse = "INV_" in sys_id or logic == "inverse"

                    # Invert signal if inverse mode
                    if is_inverse:
                        sig_dir = "SELL" if sig_dir == "BUY" else "BUY"

                    if sig_dir == direction:
                        votes += 1
                        total_strength += sig.get("strength", 0.5)
                        if sig.get("pnl_pct") is not None:
                            # For inverse, flip the PnL too
                            pnl = sig["pnl_pct"]
                            if is_inverse:
                                pnl = -pnl
                            pnls_in_bucket.append(pnl)
                        break  # one vote per system per bucket

            # Check consensus based on logic type
            consensus = False
            if logic == "majority":
                consensus = votes >= min_agree
            elif logic == "unanimous":
                consensus = votes == len(systems)
            elif logic == "weighted":
                consensus = total_strength / max(len(systems), 1) > 0.5
            elif logic in ("inverse", "consensus_plus_inverse"):
                consensus = votes >= min_agree
            elif logic == "bayesian":
                # Bayesian fusion: combine strengths via Bayes' rule
                strengths = []
                for sys_id in systems:
                    sys_signals = by_system.get(sys_id, [])
                    for sig in sys_signals:
                        if sig["signal"] == direction:
                            strengths.append(sig.get("strength", 0.5))
                            break
                if strengths:
                    posterior = _bayesian_fuse(strengths)
                    consensus = posterior > 0.6  # higher threshold for Bayesian
            elif logic == "dempster_shafer":
                # Dempster-Shafer evidence combination
                masses = []
                for sys_id in systems:
                    sys_signals = by_system.get(sys_id, [])
                    for sig in sys_signals:
                        s = sig.get("strength", 0.5)
                        if sig["signal"] == "BUY":
                            masses.append(
                                {
                                    "buy": s,
                                    "sell": (1 - s) * 0.3,
                                    "uncertain": (1 - s) * 0.7,
                                }
                            )
                        elif sig["signal"] == "SELL":
                            masses.append(
                                {
                                    "buy": (1 - s) * 0.3,
                                    "sell": s,
                                    "uncertain": (1 - s) * 0.7,
                                }
                            )
                        break
                if masses:
                    combined = _dempster_shafer_combine(masses)
                    ds_key = "buy" if direction == "BUY" else "sell"
                    consensus = (
                        combined[ds_key] > 0.5
                        and combined[ds_key] > combined["uncertain"]
                    )
            elif logic == "regime_aware":
                # Detect regime from recent bucket PnLs, then apply appropriate logic
                recent_pnls = []
                for bk, bsigs in buckets.items():
                    if bk[0] == bucket_key[0]:  # same symbol
                        for s in bsigs:
                            if s.get("pnl_pct") is not None:
                                recent_pnls.append(s["pnl_pct"])
                regime = _detect_regime(recent_pnls[-20:] if recent_pnls else [])
                if regime == "bull":
                    # In bull: use majority (aggressive)
                    consensus = votes >= max(2, len(systems) // 2 + 1)
                elif regime == "bear":
                    # In bear: require unanimous (conservative)
                    consensus = votes == len(systems)
                else:
                    # Sideways: use weighted average
                    consensus = total_strength / max(len(systems), 1) > 0.55

            if consensus and pnls_in_bucket:
                avg_pnl = sum(pnls_in_bucket) / len(pnls_in_bucket)
                all_pnls[direction].append(avg_pnl)

    return all_pnls


def evaluate_all_permutations(data: dict, window_minutes: int = 240) -> dict:
    """Run all permutation evaluations."""
    signals = data["signals"]
    systems = data["systems"]

    if not signals:
        print("No signal data with outcomes available.")
        return {"tested": 0, "winners": 0, "results": []}

    # Generate all permutations
    perms = generate_permutations(systems)
    print(f"Generated {len(perms)} permutations from {len(systems)} systems")

    # Build time buckets
    buckets = _build_time_buckets(signals, window_minutes)
    print(f"Time buckets: {len(buckets)} (window={window_minutes}min)")

    # Connect to meta DB
    meta_conn = get_db()

    results = []
    winners = []
    tested = 0

    for perm in perms:
        combo_id = perm["combo_id"]

        # Register in DB
        register_permutation(
            meta_conn,
            combo_id=combo_id,
            systems=perm["systems"],
            logic_type=perm["logic_type"],
            min_agreement=perm["min_agreement"],
        )

        # Evaluate
        pnls_by_dir = _evaluate_combo(perm, buckets, window_minutes)

        for direction in ("BUY", "SELL"):
            pnls = pnls_by_dir[direction]
            tested += 1

            if len(pnls) < MIN_TRADES:
                save_result(
                    meta_conn,
                    combo_id,
                    None,
                    {
                        "total_trades": len(pnls),
                        "failure_reason": f"INSUFFICIENT_TRADES ({len(pnls)}<{MIN_TRADES})",
                        "eval_period": f"window_{window_minutes}min_{direction}",
                    },
                )
                continue

            # Calculate metrics
            total = len(pnls)
            w = sum(1 for p in pnls if p > 0)
            l = total - w
            wr = w / total
            avg_pnl = sum(pnls) / total
            total_pnl = sum(pnls)
            sharpe = _calc_sharpe(pnls)
            sortino = _calc_sortino(pnls)
            pf = _calc_profit_factor(pnls)
            max_dd = _calc_max_drawdown(pnls)
            p_val = _binomial_p_value(w, total)

            avg_win = sum(p for p in pnls if p > 0) / max(w, 1)
            avg_loss = sum(p for p in pnls if p < 0) / max(l, 1)
            kelly = _calc_kelly(wr, avg_win, avg_loss)

            portfolio = _simulate_portfolio(pnls)

            # Determine significance
            is_sig = (
                p_val < P_VALUE_THRESHOLD
                and wr > WIN_RATE_THRESHOLD
                and sharpe > SHARPE_THRESHOLD
                and pf > PROFIT_FACTOR_THRESHOLD
                and max_dd < MAX_DD_THRESHOLD * 100
            )

            is_winner = is_sig and total >= MIN_TRADES

            failure_reason = None
            if not is_winner:
                reasons = []
                if p_val >= P_VALUE_THRESHOLD:
                    reasons.append(f"p={p_val:.3f}>={P_VALUE_THRESHOLD}")
                if wr <= WIN_RATE_THRESHOLD:
                    reasons.append(f"WR={wr:.1%}<={WIN_RATE_THRESHOLD:.0%}")
                if sharpe <= SHARPE_THRESHOLD:
                    reasons.append(f"Sharpe={sharpe:.2f}<={SHARPE_THRESHOLD}")
                if pf <= PROFIT_FACTOR_THRESHOLD:
                    reasons.append(f"PF={pf:.2f}<={PROFIT_FACTOR_THRESHOLD}")
                if max_dd >= MAX_DD_THRESHOLD * 100:
                    reasons.append(f"DD={max_dd:.1f}%>={MAX_DD_THRESHOLD * 100:.0f}%")
                failure_reason = "; ".join(reasons)

            metrics = {
                "total_trades": total,
                "wins": w,
                "losses": l,
                "win_rate": round(wr, 4),
                "avg_pnl_pct": round(avg_pnl, 4),
                "total_pnl_pct": round(total_pnl, 4),
                "sharpe": sharpe,
                "sortino": sortino,
                "max_drawdown_pct": portfolio["max_drawdown_pct"],
                "profit_factor": pf,
                "p_value": round(p_val, 6),
                "kelly_pct": kelly,
                "portfolio_final": portfolio["portfolio_final"],
                "portfolio_return_pct": portfolio["portfolio_return_pct"],
                "is_significant": is_sig,
                "is_winner": is_winner,
                "failure_reason": failure_reason,
                "eval_period": f"window_{window_minutes}min_{direction}",
            }

            save_result(meta_conn, combo_id, None, metrics)

            result_entry = {
                "combo_id": combo_id,
                "direction": direction,
                **metrics,
            }
            results.append(result_entry)

            if is_winner:
                winners.append(result_entry)

    meta_conn.close()

    # Sort by Sharpe
    winners.sort(key=lambda x: x["sharpe"], reverse=True)

    return {
        "tested": tested,
        "total_permutations": len(perms),
        "winners": len(winners),
        "winner_details": winners,
        "all_results": results,
    }


def _classify_failure_signature(metrics: dict) -> dict:
    """Classify WHY a combo failed — for Phoenix resurrection intelligence.

    Failure signatures:
      - REGIME_MISMATCH: Good Sharpe but high DD → works in one regime, not another
      - FEE_DRAG: Positive raw PnL but negative after fees → needs lower-fee venue
      - CORRELATION_BREAKDOWN: WR drops over time → systems decorrelated
      - INSUFFICIENT_EDGE: Low WR + low Sharpe → no real edge
      - OVERFIT: Train looks great but test degradation > 60%
      - VOLATILITY_CRUSH: Low trades + low vol → waiting for vol expansion
    """
    wr = metrics.get("win_rate") or 0
    sharpe = metrics.get("sharpe") or 0
    max_dd = metrics.get("max_drawdown_pct") or 0
    pf = metrics.get("profit_factor") or 0
    trades = metrics.get("total_trades") or 0
    avg_pnl = metrics.get("avg_pnl_pct") or 0
    p_val = metrics.get("p_value") or 1.0

    signatures = []

    # Regime mismatch: decent Sharpe but terrible drawdown
    if sharpe > 0.5 and max_dd > 20:
        signatures.append("REGIME_MISMATCH")

    # Fee drag: average PnL is barely positive or slightly negative
    if 0 < avg_pnl < 0.75 and wr > 0.5:
        signatures.append("FEE_DRAG")

    # Insufficient edge: nothing works
    if wr < 0.48 and sharpe < 0.2 and pf < 1.0:
        signatures.append("INSUFFICIENT_EDGE")

    # Volatility crush: too few trades to judge
    if trades < 8 and sharpe > 0:
        signatures.append("VOLATILITY_CRUSH")

    # High p-value but otherwise decent metrics
    if p_val > 0.10 and wr > 0.52 and sharpe > 0.3:
        signatures.append("NOISE_EDGE")

    if not signatures:
        signatures.append("GENERAL_FAILURE")

    return {
        "primary": signatures[0],
        "all_signatures": signatures,
        "revival_conditions": _get_revival_conditions(signatures[0]),
    }


def _get_revival_conditions(failure_type: str) -> dict:
    """What conditions must change for Phoenix resurrection to trigger."""
    conditions = {
        "REGIME_MISMATCH": {
            "check": "regime_change",
            "description": "Revive when detected regime changes to one where combo historically performed",
            "auto_gate": True,
        },
        "FEE_DRAG": {
            "check": "fee_reduction",
            "description": "Revive if fee model changes or on maker-only venue",
            "auto_gate": False,
        },
        "CORRELATION_BREAKDOWN": {
            "check": "correlation_recovery",
            "description": "Revive when constituent system correlation recovers above 0.3",
            "auto_gate": True,
        },
        "INSUFFICIENT_EDGE": {
            "check": "none",
            "description": "No revival — no statistical edge found",
            "auto_gate": False,
        },
        "VOLATILITY_CRUSH": {
            "check": "vol_expansion",
            "description": "Revive when ATR(14) expands >2x from elimination date",
            "auto_gate": True,
        },
        "NOISE_EDGE": {
            "check": "data_growth",
            "description": "Revive when trade count doubles (more data may confirm edge)",
            "auto_gate": True,
        },
        "GENERAL_FAILURE": {
            "check": "periodic_retest",
            "description": "Retest after 30 days with new data",
            "auto_gate": True,
        },
    }
    return conditions.get(failure_type, conditions["GENERAL_FAILURE"])


def compute_adversarial_compatibility(data: dict, combo: dict, buckets: dict) -> dict:
    """Check if systems in a combo fail at DIFFERENT times (good diversity).

    Returns adversarial score: 1.0 = perfect (never fail together),
    0.0 = terrible (always fail together).
    """
    systems = combo["systems"]
    if len(systems) < 2:
        return {"adversarial_score": 0.5, "pairs": []}

    # Collect per-system per-bucket outcomes
    system_outcomes = {s: {} for s in systems}

    for bucket_key, signals in buckets.items():
        for sig in signals:
            if sig["system_id"] in systems and sig.get("pnl_pct") is not None:
                sys_id = sig["system_id"]
                if bucket_key not in system_outcomes[sys_id]:
                    system_outcomes[sys_id][bucket_key] = []
                system_outcomes[sys_id][bucket_key].append(sig["pnl_pct"])

    pairs = []
    for i, s1 in enumerate(systems):
        for s2 in systems[i + 1 :]:
            # Find overlapping buckets
            shared_buckets = set(system_outcomes[s1].keys()) & set(
                system_outcomes[s2].keys()
            )
            if len(shared_buckets) < 3:
                pairs.append({"a": s1, "b": s2, "overlap": 0, "div_score": 0.5})
                continue

            # Count simultaneous failures
            both_fail = 0
            total = len(shared_buckets)
            for bk in shared_buckets:
                avg1 = sum(system_outcomes[s1][bk]) / len(system_outcomes[s1][bk])
                avg2 = sum(system_outcomes[s2][bk]) / len(system_outcomes[s2][bk])
                if avg1 < 0 and avg2 < 0:
                    both_fail += 1

            failure_overlap = both_fail / total if total > 0 else 0
            pairs.append(
                {
                    "a": s1,
                    "b": s2,
                    "overlap": total,
                    "failure_overlap": round(failure_overlap, 4),
                    "div_score": round(1 - failure_overlap, 4),
                }
            )

    avg_div = sum(p["div_score"] for p in pairs) / len(pairs) if pairs else 0.5
    return {"adversarial_score": round(avg_div, 4), "pairs": pairs}


def walk_forward_validate(
    data: dict, combo: dict, n_folds: int = 5, purge_gap: int = 24
) -> dict:
    """Walk-forward validation with purged gap to prevent look-ahead bias.

    Splits signals chronologically into n_folds. For each fold:
      - Train on folds 0..i-1
      - Purge 'purge_gap' hours between train and test
      - Test on fold i
      - Compare train vs test Sharpe to detect overfitting

    Returns aggregate robustness metrics.
    """
    signals = data["signals"]
    if len(signals) < 20:
        return {"robust": False, "reason": "insufficient_signals", "folds": []}

    # Sort by timestamp
    sorted_sigs = sorted(signals, key=lambda s: s["timestamp"])
    fold_size = len(sorted_sigs) // n_folds

    if fold_size < 5:
        return {"robust": False, "reason": "fold_too_small", "folds": []}

    fold_results = []
    conn = get_db()

    for i in range(1, n_folds):
        # Train: all data before fold i
        train_end_idx = i * fold_size
        # Purge gap: skip purge_gap hours of data
        purge_sigs = 0
        if train_end_idx < len(sorted_sigs):
            train_end_ts = datetime.fromisoformat(
                sorted_sigs[train_end_idx - 1]["timestamp"].replace("Z", "+00:00")
            )
            for j in range(train_end_idx, len(sorted_sigs)):
                sig_ts = datetime.fromisoformat(
                    sorted_sigs[j]["timestamp"].replace("Z", "+00:00")
                )
                if (sig_ts - train_end_ts).total_seconds() > purge_gap * 3600:
                    break
                purge_sigs += 1

        test_start_idx = train_end_idx + purge_sigs
        test_end_idx = min((i + 1) * fold_size, len(sorted_sigs))

        if test_start_idx >= test_end_idx:
            continue

        train_data = {**data, "signals": sorted_sigs[:train_end_idx]}
        test_data = {**data, "signals": sorted_sigs[test_start_idx:test_end_idx]}

        # Build separate buckets
        train_buckets = _build_time_buckets(train_data["signals"], 240)
        test_buckets = _build_time_buckets(test_data["signals"], 240)

        # Evaluate on both
        train_pnls = _evaluate_combo(combo, train_buckets, 240)
        test_pnls = _evaluate_combo(combo, test_buckets, 240)

        # Aggregate PnLs across directions
        train_all = train_pnls.get("BUY", []) + train_pnls.get("SELL", [])
        test_all = test_pnls.get("BUY", []) + test_pnls.get("SELL", [])

        train_metrics = {
            "sharpe": _calc_sharpe(train_all),
            "win_rate": sum(1 for p in train_all if p > 0) / max(len(train_all), 1),
            "total_trades": len(train_all),
        }
        test_metrics = {
            "sharpe": _calc_sharpe(test_all),
            "win_rate": sum(1 for p in test_all if p > 0) / max(len(test_all), 1),
            "total_trades": len(test_all),
        }

        # Save to DB
        train_start = sorted_sigs[0]["timestamp"]
        train_end = sorted_sigs[train_end_idx - 1]["timestamp"]
        test_start = sorted_sigs[test_start_idx]["timestamp"]
        test_end = sorted_sigs[test_end_idx - 1]["timestamp"]

        save_walkforward_result(
            conn,
            combo["combo_id"],
            i,
            train_start,
            train_end,
            test_start,
            test_end,
            train_metrics,
            test_metrics,
        )

        oos_deg = 0.0
        if train_metrics["sharpe"] > 0:
            oos_deg = (
                (train_metrics["sharpe"] - test_metrics["sharpe"])
                / train_metrics["sharpe"]
                * 100
            )

        fold_results.append(
            {
                "fold": i,
                "train_sharpe": train_metrics["sharpe"],
                "test_sharpe": test_metrics["sharpe"],
                "train_wr": round(train_metrics["win_rate"], 4),
                "test_wr": round(test_metrics["win_rate"], 4),
                "oos_degradation_pct": round(oos_deg, 2),
                "is_robust": test_metrics["sharpe"] > 0 and oos_deg < 50,
            }
        )

    conn.close()

    # Aggregate
    if not fold_results:
        return {
            "robust": False,
            "reason": "no_valid_folds",
            "folds": [],
            "robust_folds": 0,
            "total_folds": 0,
            "avg_oos_sharpe": 0.0,
            "avg_degradation_pct": 0.0,
        }

    robust_folds = sum(1 for f in fold_results if f["is_robust"])
    avg_oos_sharpe = sum(f["test_sharpe"] for f in fold_results) / len(fold_results)
    avg_degradation = sum(f["oos_degradation_pct"] for f in fold_results) / len(
        fold_results
    )

    is_robust = robust_folds >= len(fold_results) * 0.6  # 60% of folds must be robust

    return {
        "robust": is_robust,
        "robust_folds": robust_folds,
        "total_folds": len(fold_results),
        "avg_oos_sharpe": round(avg_oos_sharpe, 4),
        "avg_degradation_pct": round(avg_degradation, 2),
        "folds": fold_results,
    }


def run_elimination_cycle(conn=None) -> dict:
    """Check all active combos and eliminate persistent losers."""
    own_conn = conn is None
    if own_conn:
        conn = get_db()

    active = get_active_permutations(conn)
    stats = {"checked": 0, "eliminated": 0, "probation": 0, "resurrected": 0}

    for perm in active:
        combo_id = perm["combo_id"]
        stats["checked"] += 1

        # Get latest results
        row = conn.execute(
            """
            SELECT * FROM permutation_results
            WHERE combo_id = ? AND symbol IS NULL
            ORDER BY last_updated DESC LIMIT 1
        """,
            (combo_id,),
        ).fetchone()

        if not row:
            continue

        result = dict(row)
        failures = perm.get("consecutive_failures", 0)

        # Check for failure
        if result.get("is_winner"):
            # Reset failure counter on win
            conn.execute(
                """
                UPDATE permutations SET consecutive_failures = 0
                WHERE combo_id = ?
            """,
                (combo_id,),
            )
            conn.commit()
        else:
            failures += 1
            conn.execute(
                """
                UPDATE permutations SET consecutive_failures = ?
                WHERE combo_id = ?
            """,
                (failures, combo_id),
            )
            conn.commit()

            if failures >= MAX_CONSECUTIVE_FAILURES:
                # v2.0: Classify failure signature before eliminating
                failure_sig = _classify_failure_signature(result)
                eliminate_combo(
                    conn,
                    combo_id,
                    f"Failed {failures} consecutive evaluations | {failure_sig['primary']}",
                    {
                        "win_rate": result.get("win_rate"),
                        "sharpe": result.get("sharpe"),
                        "failure_signature": failure_sig,
                    },
                )
                stats["eliminated"] += 1
            elif failures >= PROBATION_THRESHOLD:
                conn.execute(
                    """
                    UPDATE permutations SET status = 'PROBATION'
                    WHERE combo_id = ?
                """,
                    (combo_id,),
                )
                conn.commit()
                stats["probation"] += 1

    # v2.0: Phoenix resurrection with failure signature intelligence
    eliminated = conn.execute("""
        SELECT p.*, el.failure_signature, el.metrics_at_action
        FROM permutations p
        LEFT JOIN elimination_log el ON el.combo_id = p.combo_id
            AND el.action = 'ELIMINATED'
        WHERE p.status = 'ELIMINATED'
        AND p.resurrection_count < 3
        ORDER BY el.timestamp DESC
    """).fetchall()

    for perm in eliminated:
        combo_id = perm["combo_id"]

        # Parse failure signature
        failure_sig = None
        if perm["failure_signature"]:
            try:
                failure_sig = json.loads(perm["failure_signature"])
            except Exception:
                failure_sig = None

        # Check revival conditions based on failure type
        should_revive = False
        revive_reason = ""

        if failure_sig and failure_sig.get("primary") == "INSUFFICIENT_EDGE":
            # Never revive — no real edge
            continue

        # Check for new winning results in last 7 days
        recent = conn.execute(
            """
            SELECT * FROM permutation_results
            WHERE combo_id = ? AND is_winner = 1
            AND last_updated > datetime('now', '-7 days')
        """,
            (combo_id,),
        ).fetchone()

        if recent:
            should_revive = True
            revive_reason = f"Phoenix: New winning result Sharpe={recent['sharpe']}"

        # Regime-gated revival: if failure was REGIME_MISMATCH, check current regime
        if (
            failure_sig
            and failure_sig.get("primary") == "REGIME_MISMATCH"
            and not should_revive
        ):
            # Check if recent signals show regime change
            recent_signals = conn.execute(
                """
                SELECT pnl_pct FROM permutation_signals
                WHERE combo_id = ? AND pnl_pct IS NOT NULL
                ORDER BY timestamp DESC LIMIT 10
            """,
                (combo_id,),
            ).fetchall()
            if recent_signals:
                recent_pnls = [r["pnl_pct"] for r in recent_signals]
                regime = _detect_regime(recent_pnls)
                if (
                    regime != "bear"
                ):  # was likely failing in bear, revive if regime changed
                    should_revive = True
                    revive_reason = (
                        f"Phoenix: Regime changed to {regime} (was REGIME_MISMATCH)"
                    )

        # Data growth revival: if NOISE_EDGE, check if trade count doubled
        if (
            failure_sig
            and failure_sig.get("primary") == "NOISE_EDGE"
            and not should_revive
        ):
            old_metrics = None
            if perm["metrics_at_action"]:
                try:
                    old_metrics = json.loads(perm["metrics_at_action"])
                except Exception:
                    pass
            if old_metrics:
                old_trades = old_metrics.get("total_trades", 0)
                new_result = conn.execute(
                    """
                    SELECT total_trades FROM permutation_results
                    WHERE combo_id = ? ORDER BY last_updated DESC LIMIT 1
                """,
                    (combo_id,),
                ).fetchone()
                if new_result and new_result["total_trades"] > old_trades * 2:
                    should_revive = True
                    revive_reason = f"Phoenix: Trade count grew {old_trades}→{new_result['total_trades']}"

        if should_revive:
            resurrect_combo(conn, combo_id, revive_reason)
            stats["resurrected"] += 1

    if own_conn:
        conn.close()
    return stats


def export_active_picks(conn=None) -> list:
    """Export current winning combo signals as active_picks.json for the aggregator."""
    own_conn = conn is None
    if own_conn:
        conn = get_db()

    winners = conn.execute(
        """
        SELECT pr.combo_id, pr.win_rate, pr.sharpe, pr.total_trades,
               pr.portfolio_return_pct, p.systems, p.logic_type
        FROM permutation_results pr
        JOIN permutations p ON p.combo_id = pr.combo_id
        WHERE pr.is_winner = 1
          AND p.status IN ('ACTIVE', 'RESURRECTED', 'PROBATION')
          AND pr.total_trades >= ?
        ORDER BY pr.sharpe DESC
        LIMIT 10
    """,
        (MIN_TRADES,),
    ).fetchall()

    picks = []
    for w in winners:
        picks.append(
            {
                "combo_id": w["combo_id"],
                "systems": json.loads(w["systems"]),
                "logic": w["logic_type"],
                "win_rate": w["win_rate"],
                "sharpe": w["sharpe"],
                "total_trades": w["total_trades"],
                "portfolio_return_pct": w["portfolio_return_pct"],
            }
        )

    output_path = Path(__file__).parent / "data" / "active_combos.json"
    output_path.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "winning_combos": picks,
                "total_winners": len(picks),
            },
            indent=2,
        )
    )

    if own_conn:
        conn.close()
    return picks


def main():
    """Main entry point — run full permutation evaluation."""
    print("=" * 60)
    print("META-STRATEGY PERMUTATION ENGINE v2.0")
    print("  Bayesian · Dempster-Shafer · Regime-Aware · Phoenix · Walk-Forward")
    print("=" * 60)

    # Load signal data
    data = load_signal_data()
    print(f"Loaded {len(data['signals'])} signals from {len(data['systems'])} systems")
    print(f"Systems: {data['systems']}")
    print(f"Symbols: {data['symbols']}")

    if not data["signals"]:
        print(
            "\nNo signal data with outcomes. Run signal recorder + outcome tracker first."
        )
        return

    # Test across multiple time windows
    all_winners = []
    all_perms_tested = []
    for window in CONFLUENCE_WINDOWS:
        print(f"\n{'─' * 40}")
        print(f"Testing with {window}-minute confluence window")
        print(f"{'─' * 40}")

        result = evaluate_all_permutations(data, window_minutes=window)
        print(f"  Tested: {result['tested']} combos")
        print(f"  Winners: {result['winners']}")

        for w in result["winner_details"][:5]:
            print(
                f"    {w['combo_id']:40s} {w['direction']:4s} "
                f"WR={w['win_rate']:.1%} Sharpe={w['sharpe']:.2f} "
                f"trades={w['total_trades']} p={w['p_value']:.4f} "
                f"portfolio=${w['portfolio_final']:.0f}"
            )
            all_winners.append(w)

    # v2.0: Walk-forward validation on top winners
    if all_winners:
        print(f"\n{'─' * 40}")
        print("Walk-Forward Validation (purged CV, 5-fold)")
        print(f"{'─' * 40}")
        for w in all_winners[:10]:
            combo = {
                "combo_id": w["combo_id"],
                "systems": w["combo_id"].split("|")[0].split("+"),
                "logic_type": w["combo_id"].split("|")[1]
                if "|" in w["combo_id"]
                else "majority",
                "min_agreement": 2,
            }
            wf = walk_forward_validate(data, combo)
            status = "ROBUST" if wf["robust"] else "OVERFIT"
            print(
                f"  {w['combo_id']:40s} [{status}] "
                f"OOS Sharpe={wf['avg_oos_sharpe']:.2f} "
                f"Degradation={wf['avg_degradation_pct']:.0f}% "
                f"({wf['robust_folds']}/{wf['total_folds']} robust folds)"
            )

    # v2.0: Adversarial compatibility for top combos
    if all_winners:
        print(f"\n{'─' * 40}")
        print("Adversarial Compatibility Analysis")
        print(f"{'─' * 40}")
        buckets = _build_time_buckets(data["signals"], 240)
        for w in all_winners[:5]:
            combo = {
                "combo_id": w["combo_id"],
                "systems": w["combo_id"].split("|")[0].split("+"),
                "logic_type": w["combo_id"].split("|")[1]
                if "|" in w["combo_id"]
                else "majority",
                "min_agreement": 2,
            }
            if len(combo["systems"]) >= 2:
                adv = compute_adversarial_compatibility(data, combo, buckets)
                score = adv["adversarial_score"]
                label = (
                    "EXCELLENT" if score > 0.7 else "GOOD" if score > 0.5 else "POOR"
                )
                print(f"  {w['combo_id']:40s} Diversity={score:.2f} [{label}]")
                # Save pairs to DB
                conn = get_db()
                for pair in adv["pairs"]:
                    save_adversarial_compat(
                        conn,
                        combo["combo_id"],
                        pair["a"],
                        pair["b"],
                        0.0,
                        pair.get("failure_overlap", 0.5),
                    )
                conn.close()

    # Run elimination cycle (v2.0: with Phoenix failure signatures)
    print(f"\n{'─' * 40}")
    print("Elimination Cycle (Phoenix-enabled)")
    print(f"{'─' * 40}")
    elim_stats = run_elimination_cycle()
    print(f"  Checked: {elim_stats['checked']}")
    print(f"  Eliminated: {elim_stats['eliminated']}")
    print(f"  On probation: {elim_stats['probation']}")
    print(f"  Phoenix resurrected: {elim_stats['resurrected']}")

    # Export active picks
    picks = export_active_picks()
    print(f"\nExported {len(picks)} winning combos to data/active_combos.json")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"TOTAL WINNERS FOUND: {len(all_winners)}")
    if all_winners:
        best = max(all_winners, key=lambda x: x["sharpe"])
        print(f"BEST: {best['combo_id']} ({best['direction']})")
        print(
            f"  Sharpe={best['sharpe']:.2f}, WR={best['win_rate']:.1%}, "
            f"PF={best['profit_factor']:.2f}, "
            f"Portfolio: $1000 → ${best['portfolio_final']:.0f}"
        )
    print("=" * 60)


if __name__ == "__main__":
    main()

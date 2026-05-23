#!/usr/bin/env python3
"""
Winner Prediction Model — Built from ACTUAL closed picks data.
No external APIs. Stdlib only. Uses dashboard_payload.json.

Steps:
1. Load closed picks, extract populated features
2. Compute feature predictive power (Spearman, WR by bucket, IC)
3. Build decision tree (max_depth=3) from scratch
4. Backtest on chronological 70/30 split
5. Compare to current elite_score
6. Score active picks with new model vs current
"""

import json
import os
import math
import statistics
from datetime import datetime
from collections import defaultdict, Counter


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_PATH = os.path.join(BASE_DIR, "..", "audit_trail", "data", "dashboard_payload.json")
MODEL_OUT = os.path.join(BASE_DIR, "data", "winner_model.json")
ANALYSIS_OUT = os.path.join(BASE_DIR, "data", "winner_analysis.json")


def load_payload():
    with open(PAYLOAD_PATH) as f:
        return json.load(f)


def extract_features(pick):
    """Extract numeric features from a pick. Returns dict of feature_name -> value."""
    feats = {}

    # --- Core numeric fields ---
    if pick.get("score") is not None:
        feats["score"] = float(pick["score"])
    if pick.get("confidence") is not None:
        feats["confidence"] = float(pick["confidence"])
    if pick.get("rr_ratio") is not None:
        feats["rr_ratio"] = float(pick["rr_ratio"])
    if pick.get("age_hours") is not None:
        feats["age_hours"] = float(pick["age_hours"])
    if pick.get("agreement_count") is not None:
        feats["agreement_count"] = int(pick["agreement_count"])
    if pick.get("system_agreement_count") is not None:
        feats["system_agreement_count"] = int(pick["system_agreement_count"])
    if pick.get("max_safe_leverage") is not None:
        feats["max_safe_leverage"] = int(pick["max_safe_leverage"])

    # --- Direction as numeric ---
    if pick.get("direction"):
        feats["is_short"] = 1.0 if pick["direction"] == "SHORT" else 0.0

    # --- Asset class as numeric dummies ---
    ac = pick.get("asset_class", "")
    feats["is_crypto"] = 1.0 if ac == "CRYPTO" else 0.0
    feats["is_forex"] = 1.0 if ac == "FOREX" else 0.0
    feats["is_equity"] = 1.0 if ac == "EQUITY" else 0.0

    # --- Trade timeframe ---
    tf = pick.get("trade_timeframe", "")
    feats["is_swing"] = 1.0 if tf == "SWING" else 0.0
    feats["is_scalp"] = 1.0 if tf == "SCALP" else 0.0

    # --- Technical alignment ---
    if pick.get("technical_buy_tfs") is not None:
        feats["technical_buy_tfs"] = int(pick["technical_buy_tfs"])
    if pick.get("technical_sell_tfs") is not None:
        feats["technical_sell_tfs"] = int(pick["technical_sell_tfs"])
    if pick.get("technical_rsi_4h") is not None:
        feats["technical_rsi_4h"] = float(pick["technical_rsi_4h"])
    # Technical aligned with direction?
    tv = pick.get("technical_verdict", "")
    d = pick.get("direction", "")
    if tv and d:
        aligned = 0.0
        if d == "LONG" and "BUY" in tv:
            aligned = 1.0
        elif d == "SHORT" and "SELL" in tv:
            aligned = 1.0
        feats["tech_direction_aligned"] = aligned

    # --- Score breakdown components (the juicy stuff) ---
    sb = pick.get("_scoreBreakdown", {})
    if sb:
        for comp in ["ml_score", "forward_wr", "source_system", "confluence",
                      "position", "regime_bonus", "session_bonus", "age_freshness",
                      "risk_reward", "monte_carlo", "leverage_safety", "volume",
                      "signal_quality", "meta_label", "hindsight_winner",
                      "skyrocket_potential", "proven_strategy_bonus",
                      "strategy_track_record", "technical_alignment",
                      "risk_warning_penalty", "copy_trader_edge"]:
            if comp in sb and sb[comp] is not None:
                try:
                    feats[f"sb_{comp}"] = float(sb[comp])
                except (ValueError, TypeError):
                    pass

    # --- Forward stats ---
    if pick.get("forward_wr") is not None:
        try:
            feats["forward_wr"] = float(pick["forward_wr"])
        except (ValueError, TypeError):
            pass
    if pick.get("forward_trades") is not None:
        try:
            feats["forward_trades"] = float(pick["forward_trades"])
        except (ValueError, TypeError):
            pass

    # --- Has conflict ---
    feats["has_conflict"] = 1.0 if pick.get("has_conflict") else 0.0

    return feats


def get_outcome(pick):
    """Returns (is_winner: bool, pnl_pct: float) or None if no outcome."""
    pnl = pick.get("pnl_pct")
    status = pick.get("status", "")
    if pnl is None:
        return None
    try:
        pnl = float(pnl)
    except (ValueError, TypeError):
        return None
    if status in ("WON",):
        return (True, pnl)
    elif status in ("LOST",):
        return (False, pnl)
    elif status == "CLOSED":
        return (pnl > 0, pnl)
    elif status == "EXPIRED":
        return (pnl > 0, pnl)
    return None


# ─── Statistics helpers (stdlib only) ───

def spearman_rank_corr(xs, ys):
    """Spearman rank correlation coefficient."""
    n = len(xs)
    if n < 5:
        return 0.0

    def rank_data(vals):
        indexed = sorted(enumerate(vals), key=lambda x: x[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = rank_data(xs)
    ry = rank_data(ys)
    n_ = float(n)
    mean_rx = sum(rx) / n_
    mean_ry = sum(ry) / n_
    num = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    den_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def quartile_wr(feature_vals, outcomes):
    """WR by quartile of feature values. Returns dict of q1..q4 WR.
    Uses distinct-value bucketing to avoid degenerate quartiles when
    95%+ of values are identical."""
    if len(feature_vals) < 20:
        return {}
    paired = sorted(zip(feature_vals, outcomes))
    n = len(paired)

    # Check how many distinct values exist
    distinct = sorted(set(feature_vals))
    if len(distinct) < 4:
        # Use distinct-value bucketing instead of quartiles
        result = {}
        bucket_map = defaultdict(list)
        for v, o in paired:
            bucket_map[v].append(o)
        for i, (val, outs) in enumerate(sorted(bucket_map.items())):
            wins = sum(outs)
            total = len(outs)
            label = f"Q{i + 1}"
            result[label] = round(wins / total * 100, 1) if total > 0 else 0.0
        # Fill missing quartiles
        for qi in range(4):
            if f"Q{qi + 1}" not in result:
                result[f"Q{qi + 1}"] = result.get(f"Q{len(distinct)}", 0.0)
        result["Q4_minus_Q1"] = round(result.get("Q4", 0) - result.get("Q1", 0), 1)
        result["_degenerate"] = True
        return result

    q_size = n // 4
    result = {}
    for qi in range(4):
        start = qi * q_size
        end = (qi + 1) * q_size if qi < 3 else n
        chunk = paired[start:end]
        wins = sum(1 for _, o in chunk if o)
        total = len(chunk)
        result[f"Q{qi + 1}"] = round(wins / total * 100, 1) if total > 0 else 0.0
    result["Q4_minus_Q1"] = round(result.get("Q4", 0) - result.get("Q1", 0), 1)
    result["_degenerate"] = False
    return result


def information_coefficient(feature_vals, pnl_vals):
    """IC = Spearman correlation of feature rank vs next-period return."""
    return spearman_rank_corr(feature_vals, pnl_vals)


# ─── Decision Tree from scratch ───

class DecisionNode:
    def __init__(self, feature=None, threshold=None, left=None, right=None,
                 prediction=None, win_rate=None, n_samples=0, category_value=None):
        self.feature = feature
        self.threshold = threshold
        self.category_value = category_value  # for categorical splits
        self.left = left
        self.right = right
        self.prediction = prediction
        self.win_rate = win_rate
        self.n_samples = n_samples


def gini_impurity(outcomes):
    if not outcomes:
        return 0.0
    p_win = sum(outcomes) / len(outcomes)
    return 1.0 - p_win ** 2 - (1 - p_win) ** 2


def find_best_split(features_list, outcomes, feature_names):
    """Find best binary split across all features."""
    best_gain = -1
    best_feature = None
    best_threshold = None
    n = len(outcomes)
    if n < 10:
        return None, None

    parent_gini = gini_impurity(outcomes)

    for fi, fname in enumerate(feature_names):
        vals = [f[fi] for f in features_list]
        # Get unique sorted thresholds (midpoints)
        unique = sorted(set(vals))
        if len(unique) < 2:
            continue
        # Test ~20 candidate thresholds max
        if len(unique) > 21:
            step = len(unique) // 20
            unique = unique[::step]

        for i in range(len(unique) - 1):
            thresh = (unique[i] + unique[i + 1]) / 2.0
            left_outcomes = [outcomes[j] for j in range(n) if vals[j] <= thresh]
            right_outcomes = [outcomes[j] for j in range(n) if vals[j] > thresh]
            if len(left_outcomes) < 5 or len(right_outcomes) < 5:
                continue
            weighted_gini = (len(left_outcomes) * gini_impurity(left_outcomes) +
                             len(right_outcomes) * gini_impurity(right_outcomes)) / n
            gain = parent_gini - weighted_gini
            if gain > best_gain:
                best_gain = gain
                best_feature = fname
                best_threshold = thresh

    if best_gain <= 0.001:
        return None, None
    return best_feature, best_threshold


def build_tree(features_list, outcomes, feature_names, depth=0, max_depth=3):
    """Build decision tree recursively."""
    n = len(outcomes)
    wr = sum(outcomes) / n if n > 0 else 0.0
    prediction = 1 if wr >= 0.5 else 0

    if depth >= max_depth or n < 20:
        return DecisionNode(prediction=prediction, win_rate=round(wr * 100, 1), n_samples=n)

    feat, thresh = find_best_split(features_list, outcomes, feature_names)
    if feat is None:
        return DecisionNode(prediction=prediction, win_rate=round(wr * 100, 1), n_samples=n)

    fi = feature_names.index(feat)
    left_idx = [i for i in range(n) if features_list[i][fi] <= thresh]
    right_idx = [i for i in range(n) if features_list[i][fi] > thresh]

    left_feats = [features_list[i] for i in left_idx]
    left_out = [outcomes[i] for i in left_idx]
    right_feats = [features_list[i] for i in right_idx]
    right_out = [outcomes[i] for i in right_idx]

    left_node = build_tree(left_feats, left_out, feature_names, depth + 1, max_depth)
    right_node = build_tree(right_feats, right_out, feature_names, depth + 1, max_depth)

    return DecisionNode(feature=feat, threshold=round(thresh, 4),
                        left=left_node, right=right_node,
                        win_rate=round(wr * 100, 1), n_samples=n)


def predict_tree(node, feature_dict, feature_names):
    """Predict win probability using tree."""
    if node.feature is None:
        return node.win_rate / 100.0

    val = feature_dict.get(node.feature, 0.0)
    if val <= node.threshold:
        return predict_tree(node.left, feature_dict, feature_names)
    else:
        return predict_tree(node.right, feature_dict, feature_names)


def tree_to_rules(node, prefix="", rules=None):
    """Convert tree to plain English rules."""
    if rules is None:
        rules = []
    if node.feature is None:
        rules.append(f"{prefix}THEN P(win) = {node.win_rate}% (n={node.n_samples})")
        return rules

    tree_to_rules(node.left,
                  prefix + f"IF {node.feature} <= {node.threshold} AND ",
                  rules)
    tree_to_rules(node.right,
                  prefix + f"IF {node.feature} > {node.threshold} AND ",
                  rules)
    return rules


# ─── Linear scoring model (for continuous scores) ───

def fit_linear_weights(features_matrix, outcomes, feature_names):
    """Fit simple feature weights using WR-in-top-half vs WR-in-bottom-half.
    This is a lightweight alternative to logistic regression using only stdlib."""
    n = len(outcomes)
    base_wr = sum(outcomes) / n if n else 0.5
    weights = {}

    for fi, fname in enumerate(feature_names):
        vals = [features_matrix[i][fi] for i in range(n)]
        # Sort by value, compute WR in top half vs bottom half
        paired = sorted(zip(vals, outcomes))
        mid = n // 2
        bot_wr = sum(o for _, o in paired[:mid]) / mid if mid else 0.5
        top_wr = sum(o for _, o in paired[mid:]) / (n - mid) if (n - mid) else 0.5
        # Weight = how much being in top half lifts WR
        weights[fname] = round(top_wr - bot_wr, 4)

    return weights, round(base_wr, 4)


def predict_linear(feature_dict, weights, base_wr, feature_names):
    """Score using linear weights. Returns probability in [0, 1]."""
    # Normalize features to z-scores would be ideal but we use a simpler approach:
    # weighted sum of binary indicators (is feature above median?)
    score = base_wr
    for fname in feature_names:
        w = weights.get(fname, 0.0)
        # We add the weight directly (it's already a WR delta)
        # Scale by 1/n_features so total adjustment is bounded
        score += w / len(feature_names)
    return max(0.0, min(1.0, score))


def predict_ensemble(feature_dict, feature_names, tree, weights, base_wr,
                     medians, tree_weight=0.5):
    """Blend tree + linear model for continuous scores."""
    tree_prob = predict_tree(tree, feature_dict, feature_names)

    # For linear model, convert features to above/below median indicators
    linear_score = base_wr
    for fname in feature_names:
        w = weights.get(fname, 0.0)
        val = feature_dict.get(fname, medians.get(fname, 0.0))
        med = medians.get(fname, 0.0)
        # +w if above median, -w if below
        if val > med:
            linear_score += w / len(feature_names)
        elif val < med:
            linear_score -= w / len(feature_names)
    linear_score = max(0.0, min(1.0, linear_score))

    return tree_prob * tree_weight + linear_score * (1 - tree_weight)


def tree_to_dict(node):
    """Serialize tree to JSON-safe dict."""
    if node.feature is None:
        return {"leaf": True, "win_rate": node.win_rate,
                "prediction": node.prediction, "n_samples": node.n_samples}
    return {
        "feature": node.feature,
        "threshold": node.threshold,
        "win_rate": node.win_rate,
        "n_samples": node.n_samples,
        "left": tree_to_dict(node.left),
        "right": tree_to_dict(node.right),
    }


def run():
    print("=" * 70)
    print("WINNER PREDICTION MODEL — Built from actual closed picks")
    print("=" * 70)

    data = load_payload()
    closed_picks = data["picks"]["recent_closed"]
    active_picks = data["picks"]["active"]

    # Also get leaderboard for strategy WR mapping
    leaderboard = {e["strategy"]: e for e in data.get("leaderboard", [])}
    # System-level WR
    system_wr = {s["name"]: s["win_rate"] for s in data.get("systems", [])}

    # ─── Step 1: Extract features + outcomes ───
    print(f"\n{'─' * 50}")
    print(f"STEP 1: Loading {len(closed_picks)} closed picks")
    print(f"{'─' * 50}")

    samples = []
    for pick in closed_picks:
        outcome = get_outcome(pick)
        if outcome is None:
            continue
        is_win, pnl = outcome
        feats = extract_features(pick)

        # Add strategy historical WR from leaderboard
        strat = pick.get("strategy", "")
        if strat and strat in leaderboard:
            lb_entry = leaderboard[strat]
            if lb_entry.get("fwd_wr") is not None:
                feats["strategy_fwd_wr"] = float(lb_entry["fwd_wr"])
            if lb_entry.get("bt_wr") is not None and lb_entry["bt_wr"] is not None:
                feats["strategy_bt_wr"] = float(lb_entry["bt_wr"])

        # Add system WR
        sys = pick.get("source_system", "")
        if sys and sys in system_wr and system_wr[sys] is not None:
            feats["system_wr"] = float(system_wr[sys])

        samples.append({
            "features": feats,
            "is_win": is_win,
            "pnl_pct": pnl,
            "timestamp": pick.get("timestamp", ""),
            "symbol": pick.get("symbol", ""),
            "strategy": strat,
            "source_system": sys,
            "score": pick.get("score"),
            "elite_grade": pick.get("elite_grade"),
            "direction": pick.get("direction"),
        })

    print(f"  Picks with outcomes: {len(samples)}")
    wins = sum(1 for s in samples if s["is_win"])
    print(f"  Winners: {wins} ({wins / len(samples) * 100:.1f}%)")
    print(f"  Losers: {len(samples) - wins} ({(len(samples) - wins) / len(samples) * 100:.1f}%)")

    # ─── Step 2: Feature predictive power ───
    print(f"\n{'─' * 50}")
    print("STEP 2: Feature predictive power analysis")
    print(f"{'─' * 50}")

    # Get all feature names that appear in >50% of samples
    feat_counts = defaultdict(int)
    for s in samples:
        for fname in s["features"]:
            feat_counts[fname] += 1

    min_count = len(samples) * 0.3
    valid_features = [f for f, c in feat_counts.items() if c >= min_count]
    print(f"  Features with >30% fill rate: {len(valid_features)}")

    feature_analysis = {}
    for fname in valid_features:
        vals = []
        outcomes = []
        pnls = []
        for s in samples:
            if fname in s["features"]:
                vals.append(s["features"][fname])
                outcomes.append(1 if s["is_win"] else 0)
                pnls.append(s["pnl_pct"])

        if len(vals) < 30:
            continue

        sp_corr = spearman_rank_corr(vals, [float(o) for o in outcomes])
        ic = information_coefficient(vals, pnls)
        qwr = quartile_wr(vals, outcomes)

        # Compute distinct value ratio (penalize near-constant features)
        n_distinct = len(set(vals))
        distinct_ratio = n_distinct / len(vals) if vals else 0
        # A feature with <5 distinct values covering >90% is near-constant
        val_counts = Counter(vals)
        top_val_pct = val_counts.most_common(1)[0][1] / len(vals) if vals else 0

        # Penalize features where top value covers >80% of data
        variance_penalty = max(0.0, 1.0 - max(0, top_val_pct - 0.5) * 2)  # 1.0 at 50%, 0.0 at 100%

        # Composite: Spearman weight + spread weight, penalized by variance
        raw_power = abs(sp_corr) * 0.6 + abs(qwr.get("Q4_minus_Q1", 0)) / 100 * 0.4
        adj_power = raw_power * variance_penalty

        feature_analysis[fname] = {
            "spearman_with_outcome": round(sp_corr, 4),
            "ic_with_pnl": round(ic, 4),
            "quartile_wr": qwr,
            "q4_q1_spread": qwr.get("Q4_minus_Q1", 0),
            "n_samples": len(vals),
            "n_distinct": n_distinct,
            "top_val_pct": round(top_val_pct * 100, 1),
            "variance_penalty": round(variance_penalty, 3),
            "abs_predictive_power": round(adj_power, 4),
        }

    # Rank features
    ranked = sorted(feature_analysis.items(),
                    key=lambda x: x[1]["abs_predictive_power"], reverse=True)

    print(f"\n  Top 20 predictive features (variance-adjusted):")
    print(f"  {'Feature':<30} {'Spearman':>8} {'IC':>8} {'Q1 WR':>7} {'Q4 WR':>7} {'Spread':>7} {'Top%':>6} {'VarP':>5} {'Power':>6}")
    print(f"  {'─' * 95}")
    for fname, fa in ranked[:20]:
        qwr = fa["quartile_wr"]
        print(f"  {fname:<30} {fa['spearman_with_outcome']:>8.4f} {fa['ic_with_pnl']:>8.4f} "
              f"{qwr.get('Q1', 0):>6.1f}% {qwr.get('Q4', 0):>6.1f}% {fa['q4_q1_spread']:>6.1f}% "
              f"{fa['top_val_pct']:>5.0f}% {fa['variance_penalty']:>5.2f} {fa['abs_predictive_power']:>5.4f}")

    # Best single feature
    if ranked:
        best_name, best_stats = ranked[0]
        print(f"\n  >>> BEST SINGLE PREDICTOR: {best_name}")
        print(f"      Spearman = {best_stats['spearman_with_outcome']:.4f}, "
              f"Q4-Q1 spread = {best_stats['q4_q1_spread']:.1f}%")

    # ─── Step 3: Build decision tree ───
    print(f"\n{'─' * 50}")
    print("STEP 3: Building decision tree (max_depth=3)")
    print(f"{'─' * 50}")

    # Select top features for tree
    top_n = min(8, len(ranked))
    top_features = [fname for fname, _ in ranked[:top_n]]
    print(f"  Using top {top_n} features: {top_features}")

    # Build feature matrix (fill missing with median)
    feature_medians = {}
    for fname in top_features:
        vals = [s["features"].get(fname) for s in samples if fname in s["features"]]
        vals = [v for v in vals if v is not None]
        if vals:
            vals.sort()
            feature_medians[fname] = vals[len(vals) // 2]
        else:
            feature_medians[fname] = 0.0

    features_matrix = []
    outcomes_list = []
    for s in samples:
        row = []
        for fname in top_features:
            row.append(s["features"].get(fname, feature_medians[fname]))
        features_matrix.append(row)
        outcomes_list.append(1 if s["is_win"] else 0)

    tree = build_tree(features_matrix, outcomes_list, top_features, max_depth=3)

    # Fit linear weights on full data
    linear_weights, base_wr = fit_linear_weights(
        features_matrix, outcomes_list, top_features)

    # Print rules
    rules = tree_to_rules(tree)
    print(f"\n  Decision tree rules ({len(rules)} leaf nodes):")
    for i, rule in enumerate(rules):
        # Clean up trailing AND
        rule = rule.rstrip()
        if rule.endswith("AND"):
            rule = rule[:-3]
        # Make more readable
        rule = rule.replace("AND IF", "AND")
        print(f"    Rule {i + 1}: {rule}")

    print(f"\n  Linear model weights (top-half vs bottom-half WR delta):")
    for fname in top_features:
        w = linear_weights.get(fname, 0)
        direction = "+" if w > 0 else "-"
        print(f"    {fname:<35} {direction} {abs(w):.4f}")
    print(f"    Base WR: {base_wr:.4f}")

    # ─── Step 4: Backtest ───
    print(f"\n{'─' * 50}")
    print("STEP 4: Chronological backtest (70/30 split)")
    print(f"{'─' * 50}")

    # Sort by timestamp
    samples_sorted = sorted(samples, key=lambda s: s.get("timestamp", ""))
    split_idx = int(len(samples_sorted) * 0.7)
    train = samples_sorted[:split_idx]
    test = samples_sorted[split_idx:]

    print(f"  Train: {len(train)} picks, Test: {len(test)} picks")

    # Rebuild tree + linear on train only
    train_matrix = []
    train_outcomes = []
    for s in train:
        row = [s["features"].get(f, feature_medians[f]) for f in top_features]
        train_matrix.append(row)
        train_outcomes.append(1 if s["is_win"] else 0)

    train_tree = build_tree(train_matrix, train_outcomes, top_features, max_depth=3)
    train_weights, train_base_wr = fit_linear_weights(
        train_matrix, train_outcomes, top_features)

    # Score test set using ensemble
    test_scores = []
    for s in test:
        feat_dict = {f: s["features"].get(f, feature_medians[f]) for f in top_features}
        prob = predict_ensemble(feat_dict, top_features, train_tree,
                                train_weights, train_base_wr, feature_medians,
                                tree_weight=0.4)
        test_scores.append({
            "prob": prob,
            "is_win": s["is_win"],
            "pnl_pct": s["pnl_pct"],
            "score": s.get("score"),
            "symbol": s["symbol"],
        })

    # WR by model quartile
    test_scores.sort(key=lambda x: x["prob"])
    q_size = len(test_scores) // 4

    print(f"\n  NEW MODEL — WR by predicted probability quartile:")
    model_quartile_wr = {}
    for qi in range(4):
        start = qi * q_size
        end = (qi + 1) * q_size if qi < 3 else len(test_scores)
        chunk = test_scores[start:end]
        wins = sum(1 for t in chunk if t["is_win"])
        total = len(chunk)
        wr = wins / total * 100 if total else 0
        avg_pnl = sum(t["pnl_pct"] for t in chunk) / total if total else 0
        label = f"Q{qi + 1}"
        model_quartile_wr[label] = round(wr, 1)
        prob_range = f"{chunk[0]['prob']:.2f}-{chunk[-1]['prob']:.2f}"
        print(f"    {label} (prob {prob_range}): WR = {wr:.1f}%, "
              f"Avg PnL = {avg_pnl:.2f}%, N = {total}")

    model_spread = model_quartile_wr.get("Q4", 0) - model_quartile_wr.get("Q1", 0)
    print(f"    Q4 - Q1 spread: {model_spread:.1f}%")

    # ─── Step 5: Compare to current elite_score ───
    print(f"\n{'─' * 50}")
    print("STEP 5: Compare to current elite_score")
    print(f"{'─' * 50}")

    # Current score quartile WR on test set
    test_with_score = [t for t in test_scores if t["score"] is not None]
    if test_with_score:
        test_with_score.sort(key=lambda x: x["score"])
        q_size_s = len(test_with_score) // 4
        print(f"\n  CURRENT ELITE_SCORE — WR by score quartile (test set, N={len(test_with_score)}):")
        current_quartile_wr = {}
        for qi in range(4):
            start = qi * q_size_s
            end = (qi + 1) * q_size_s if qi < 3 else len(test_with_score)
            chunk = test_with_score[start:end]
            wins = sum(1 for t in chunk if t["is_win"])
            total = len(chunk)
            wr = wins / total * 100 if total else 0
            avg_pnl = sum(t["pnl_pct"] for t in chunk) / total if total else 0
            label = f"Q{qi + 1}"
            current_quartile_wr[label] = round(wr, 1)
            score_range = f"{chunk[0]['score']}-{chunk[-1]['score']}"
            print(f"    {label} (score {score_range}): WR = {wr:.1f}%, "
                  f"Avg PnL = {avg_pnl:.2f}%, N = {total}")

        current_spread = current_quartile_wr.get("Q4", 0) - current_quartile_wr.get("Q1", 0)
        print(f"    Q4 - Q1 spread: {current_spread:.1f}%")

        print(f"\n  COMPARISON:")
        print(f"    Current score spread:  {current_spread:+.1f}% (Q4-Q1)")
        print(f"    New model spread:      {model_spread:+.1f}% (Q4-Q1)")
        if model_spread > current_spread:
            print(f"    >>> NEW MODEL WINS by {model_spread - current_spread:.1f}% better stratification")
        elif current_spread > model_spread:
            print(f"    >>> CURRENT SCORE WINS by {current_spread - model_spread:.1f}% better stratification")
        else:
            print(f"    >>> TIE")
    else:
        current_quartile_wr = {}
        current_spread = 0.0
        print("  No score data available in test set.")

    # ─── Step 6: Score active picks ───
    print(f"\n{'─' * 50}")
    print("STEP 6: Score active picks — new model vs current")
    print(f"{'─' * 50}")

    active_scored = []
    for pick in active_picks:
        feats = extract_features(pick)
        # Add strategy/system WR
        strat = pick.get("strategy", "")
        if strat and strat in leaderboard:
            lb_entry = leaderboard[strat]
            if lb_entry.get("fwd_wr") is not None:
                feats["strategy_fwd_wr"] = float(lb_entry["fwd_wr"])
            if lb_entry.get("bt_wr") is not None and lb_entry["bt_wr"] is not None:
                feats["strategy_bt_wr"] = float(lb_entry["bt_wr"])
        sys = pick.get("source_system", "")
        if sys and sys in system_wr and system_wr[sys] is not None:
            feats["system_wr"] = float(system_wr[sys])

        feat_dict = {f: feats.get(f, feature_medians.get(f, 0.0)) for f in top_features}
        prob = predict_ensemble(feat_dict, top_features, tree,
                                linear_weights, base_wr, feature_medians,
                                tree_weight=0.4)
        active_scored.append({
            "symbol": pick.get("symbol", ""),
            "direction": pick.get("direction", ""),
            "strategy": strat,
            "source_system": sys,
            "current_score": pick.get("score"),
            "elite_grade": pick.get("elite_grade"),
            "new_model_prob": round(prob, 4),
            "confidence": pick.get("confidence"),
        })

    # Sort by new model prob
    by_new = sorted(active_scored, key=lambda x: x["new_model_prob"], reverse=True)
    by_current = sorted(active_scored, key=lambda x: x.get("current_score") or 0, reverse=True)

    print(f"\n  TOP 10 by NEW MODEL:")
    print(f"  {'Symbol':<14} {'Dir':<6} {'P(win)':>7} {'CurScore':>9} {'Grade':>6} {'Strategy':<35}")
    for p in by_new[:10]:
        print(f"  {p['symbol']:<14} {p['direction']:<6} {p['new_model_prob']:>6.1%} "
              f"{p['current_score'] or 'N/A':>9} {p['elite_grade'] or '-':>6} "
              f"{(p['strategy'] or '')[:35]:<35}")

    print(f"\n  TOP 10 by CURRENT SCORE:")
    print(f"  {'Symbol':<14} {'Dir':<6} {'P(win)':>7} {'CurScore':>9} {'Grade':>6} {'Strategy':<35}")
    for p in by_current[:10]:
        print(f"  {p['symbol']:<14} {p['direction']:<6} {p['new_model_prob']:>6.1%} "
              f"{p['current_score'] or 'N/A':>9} {p['elite_grade'] or '-':>6} "
              f"{(p['strategy'] or '')[:35]:<35}")

    # Overlap analysis
    top10_new_symbols = set(f"{p['symbol']}_{p['direction']}" for p in by_new[:10])
    top10_cur_symbols = set(f"{p['symbol']}_{p['direction']}" for p in by_current[:10])
    overlap = top10_new_symbols & top10_cur_symbols
    only_new = top10_new_symbols - top10_cur_symbols
    only_cur = top10_cur_symbols - top10_new_symbols

    print(f"\n  OVERLAP ANALYSIS (top 10):")
    print(f"    Both agree on: {len(overlap)} picks")
    print(f"    Only in NEW model top 10: {len(only_new)} picks")
    if only_new:
        for s in sorted(only_new):
            print(f"      + {s}")
    print(f"    Only in CURRENT top 10: {len(only_cur)} picks")
    if only_cur:
        for s in sorted(only_cur):
            print(f"      - {s}")

    # ─── Save outputs ───
    print(f"\n{'─' * 50}")
    print("Saving model and analysis...")
    print(f"{'─' * 50}")

    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)

    model_json = {
        "version": "1.0",
        "built_at": datetime.now(tz=None).isoformat() + "Z",
        "n_training_samples": len(samples),
        "n_winners": wins,
        "base_win_rate": round(wins / len(samples) * 100, 1),
        "top_features": top_features,
        "feature_medians": {k: round(v, 4) for k, v in feature_medians.items()},
        "tree": tree_to_dict(tree),
        "linear_weights": linear_weights,
        "linear_base_wr": base_wr,
        "ensemble_tree_weight": 0.4,
        "rules_plain_english": [r.rstrip().rstrip("AND").strip() for r in rules],
        "backtest": {
            "train_size": len(train),
            "test_size": len(test),
            "model_quartile_wr": model_quartile_wr,
            "model_q4_q1_spread": model_spread,
            "current_quartile_wr": current_quartile_wr,
            "current_q4_q1_spread": current_spread,
        },
    }
    with open(MODEL_OUT, "w") as f:
        json.dump(model_json, f, indent=2)
    print(f"  Model saved to: {MODEL_OUT}")

    analysis_json = {
        "generated_at": datetime.now(tz=None).isoformat() + "Z",
        "total_closed_picks_analyzed": len(samples),
        "feature_predictive_power": {
            fname: {
                "rank": i + 1,
                "spearman": fa["spearman_with_outcome"],
                "ic": fa["ic_with_pnl"],
                "quartile_wr": fa["quartile_wr"],
                "q4_q1_spread": fa["q4_q1_spread"],
                "n_samples": fa["n_samples"],
                "n_distinct": fa.get("n_distinct", 0),
                "top_val_pct": fa.get("top_val_pct", 0),
                "variance_penalty": fa.get("variance_penalty", 1.0),
            }
            for i, (fname, fa) in enumerate(ranked)
        },
        "model_vs_current": {
            "model_q4_q1_spread": model_spread,
            "current_q4_q1_spread": current_spread,
            "winner": "new_model" if model_spread > current_spread else "current_score",
            "improvement_pct": round(model_spread - current_spread, 1),
        },
        "active_picks_comparison": {
            "top10_overlap_count": len(overlap),
            "top10_new_model_only": sorted(only_new),
            "top10_current_only": sorted(only_cur),
        },
        "top10_new_model": [
            {"symbol": p["symbol"], "direction": p["direction"],
             "new_prob": p["new_model_prob"], "current_score": p["current_score"]}
            for p in by_new[:10]
        ],
        "top10_current": [
            {"symbol": p["symbol"], "direction": p["direction"],
             "new_prob": p["new_model_prob"], "current_score": p["current_score"]}
            for p in by_current[:10]
        ],
    }
    with open(ANALYSIS_OUT, "w") as f:
        json.dump(analysis_json, f, indent=2)
    print(f"  Analysis saved to: {ANALYSIS_OUT}")

    print(f"\n{'=' * 70}")
    print("DONE — Winner prediction model built and backtested.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    run()

"""
Build strategy IC (Information Coefficient) analysis for /audit IC-analysis card.

For each strategy in audit_dashboard/data/dashboard_data.json::picks.recent_closed
(resolved picks only: WIN/LOSS), compute the Spearman rank correlation between
elite_score and pnl_pct (the IC). Group results by asset_class, apply a
Bonferroni correction (alpha = 0.05 / n_strategies), and emit
audit_dashboard/data/strategy_ic_analysis.json — the payload consumed by the
inlined IC-analysis card in audit_dashboard/template.html.

Pure-Python (no numpy/scipy) so it runs under the nightly workflow, which only
installs pymysql.

Input:  audit_dashboard/data/dashboard_data.json  (picks.recent_closed)
Output: audit_dashboard/data/strategy_ic_analysis.json
"""
from __future__ import annotations

import json
import math
import os
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUTPUT = REPO / "audit_dashboard" / "data" / "strategy_ic_analysis.json"

# Minimum resolved picks per strategy for an IC to be computed/reported.
MIN_RESOLVED = 3


# ---------------------------------------------------------------------------
# Statistics helpers (pure Python)
# ---------------------------------------------------------------------------

def _ranks(values):
    """Return average-rank list for `values` (handles ties via average rank)."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and values[order[j]] == values[order[i]]:
            j += 1
        avg = (i + j - 1) / 2.0  # 0-based average rank
        for k in range(i, j):
            ranks[order[k]] = avg + 1.0  # convert to 1-based rank
        i = j
    return ranks


def _pearson(x, y):
    n = len(x)
    if n < 2:
        return 0.0
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denx = math.sqrt(sum((a - mx) ** 2 for a in x))
    deny = math.sqrt(sum((b - my) ** 2 for b in y))
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def _spearman(x, y):
    """Spearman rank correlation between x and y (pure Python, tie-aware)."""
    rx = _ranks(x)
    ry = _ranks(y)
    return _pearson(rx, ry)


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def _reg_incomplete_beta(x, a, b):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_two_tailed_p(t, df):
    """Two-tailed p-value from Student's t with df degrees of freedom."""
    if df <= 0:
        return 1.0
    x = df / (df + t * t)
    # P(|T| > |t|) = I_{df/(df+t^2)}(df/2, 1/2)
    return _reg_incomplete_beta(x, df / 2.0, 0.5)


def _spearman_p(r, n):
    """Two-tailed p-value for Spearman r via t-approximation, df = n-2."""
    if n < 3:
        return 1.0
    r = max(-1.0, min(1.0, r))
    if abs(r) >= 1.0:
        return 0.0
    t = r * math.sqrt((n - 2) / (1.0 - r * r))
    return _t_two_tailed_p(t, n - 2)


# ---------------------------------------------------------------------------
# IC computation
# ---------------------------------------------------------------------------

def _resolve_status(status):
    s = (status or "").strip().upper()
    if s in ("WIN", "LOSS", "CLOSED_WIN", "CLOSED_LOSS", "TP_HIT", "SL_HIT"):
        return s in ("WIN", "CLOSED_WIN", "TP_HIT")
    return None  # unresolved / open


def compute_ic(recent_closed):
    # Per-strategy resolved picks: list of (elite_score, pnl_pct)
    by_strategy = defaultdict(list)
    for p in recent_closed:
        elite = p.get("elite_score")
        pnl = p.get("pnl_pct")
        if elite is None or pnl is None:
            continue
        try:
            elite = float(elite)
            pnl = float(pnl)
        except (TypeError, ValueError):
            continue
        asset_class = p.get("asset_class") or "UNKNOWN"
        strategy = p.get("strategy") or "UNKNOWN"
        by_strategy[(asset_class, strategy)].append((elite, pnl))

    # Filter to strategies with >= MIN_RESOLVED resolved picks
    strategies = []
    for (asset_class, strategy), pairs in by_strategy.items():
        n = len(pairs)
        if n < MIN_RESOLVED:
            continue
        xs = [e for e, _ in pairs]
        ys = [pnl for _, pnl in pairs]
        ic = _spearman(xs, ys)
        p = _spearman_p(ic, n)
        wins = sum(1 for _, v in pairs if v > 0)
        losses = sum(1 for _, v in pairs if v < 0)
        wr_pct = (wins / n) * 100.0
        gross_win = sum(v for _, v in pairs if v > 0)
        gross_loss = abs(sum(v for _, v in pairs if v < 0))
        # 2026-11-16: zero losing picks makes PF undefined, not infinite. The old
        # branch published float("inf") (bare `Infinity` token pre-2026-05, the
        # STRING "Infinity" after) -- the first kills browser JSON.parse and blanked
        # the whole Strategy-IC panel, the second is a type landmine for any numeric
        # consumer. Report null per the measurement contract (null plus reason).
        pf = (gross_win / gross_loss) if gross_loss > 0 else None
        strategies.append({
            "asset_class": asset_class,
            "strategy": strategy,
            "n": n,
            "ic": round(ic, 4),
            "p_value": round(p, 6),
            "wr_pct": round(wr_pct, 2),
            "pf": round(pf, 4) if pf is not None else None,
            "field_used": "elite_score",
        })

    # Bonferroni correction across all tested strategies
    n_strategies = len(strategies)
    bonf_alpha = (0.05 / n_strategies) if n_strategies else 0.05
    for s in strategies:
        s["bonferroni_alpha"] = 0.05
        s["bonferroni_alpha_corrected"] = round(bonf_alpha, 6)
        s["bonferroni_pass"] = s["p_value"] <= bonf_alpha

    # Verdicts
    for s in strategies:
        ic, p = s["ic"], s["p_value"]
        sig = s["bonferroni_pass"]
        if sig and ic < 0:
            s["verdict"] = "negative_inverse"
        elif sig and ic > 0:
            s["verdict"] = "strong_positive"
        elif ic > 0.15:
            s["verdict"] = "weak_positive"
        elif ic < -0.15:
            s["verdict"] = "weak_negative"
        else:
            s["verdict"] = "neutral"

    # Per-class rollup
    by_class = defaultdict(lambda: {
        "n_strategies": 0,
        "n_resolved": 0,
        "n_with_ic": 0,
        "n_positive": 0,
        "n_negative": 0,
        "n_bonferroni_significant": 0,
        "worst_strategies": [],
        "_strategies": [],
    })
    for s in strategies:
        cls = s["asset_class"]
        c = by_class[cls]
        c["n_strategies"] += 1
        c["n_resolved"] += s["n"]
        c["_strategies"].append(s)
        if s["ic"] != 0:
            c["n_with_ic"] += 1
        if s["ic"] > 0:
            c["n_positive"] += 1
        if s["ic"] < 0:
            c["n_negative"] += 1
        if s["bonferroni_pass"]:
            c["n_bonferroni_significant"] += 1

    # Bonferroni alpha per class (recompute per class for display)
    for cls, c in by_class.items():
        c["bonferroni_corrected_alpha"] = round(0.05 / max(c["n_strategies"], 1), 6)
        # Worst strategies = most negative IC in class, top 3
        worst = sorted(c["_strategies"], key=lambda s: s["ic"])[:3]
        c["worst_strategies"] = [s["strategy"] for s in worst if s["ic"] < 0]
        del c["_strategies"]

    # Top-level aggregates
    n_positive_ic = sum(1 for s in strategies if s["ic"] > 0)
    n_negative_ic = sum(1 for s in strategies if s["ic"] < 0)
    n_decisive = sum(s["n"] for s in strategies)
    n_ten_plus_classes = sum(1 for c in by_class.values() if c["n_resolved"] >= 10)

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "source": "audit_dashboard/data/dashboard_data.json::picks.recent_closed",
        "n_decisive": n_decisive,
        "n_strategies": n_strategies,
        "n_ten_plus_classes": n_ten_plus_classes,
        "n_negative_ic": n_negative_ic,
        "n_positive_ic": n_positive_ic,
        "by_class": dict(by_class),
        "strategies": strategies,
    }
    return out


def main():
    if not DASHBOARD_DATA.exists():
        print(f"::error::Input not found: {DASHBOARD_DATA}")
        raise SystemExit(1)
    with open(DASHBOARD_DATA) as f:
        dashboard = json.load(f)
    picks = dashboard.get("picks") or {}
    recent_closed = picks.get("recent_closed") or []
    result = compute_ic(recent_closed)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        # allow_nan=False: fail loudly at build time rather than publish an artifact
        # the browser's JSON.parse rejects wholesale.
        json.dump(result, f, indent=2, allow_nan=False)
    print(f"Wrote {OUTPUT} ({len(result['strategies'])} strategies, "
          f"{len(result['by_class'])} classes, generated_at={result['generated_at']})")


if __name__ == "__main__":
    main()

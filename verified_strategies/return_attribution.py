#!/usr/bin/env python3
"""Return attribution gate (ENHANCEMENT_OVERALL #111) — alpha vs beta/style.

Motivated by KTD-Fin (arXiv 2605.28359, reviewed 2026-06-02): raw returns are a
noisy proxy for skill — positive PnL can be market beta, style exposure, or a
favorable regime rather than genuine stock-selection alpha. Our headline
ai-tournament edge (deepseek_v4 PF 3.46) is on a recent named-ticker window and
is unattributed, so it may be beta/memorization, not skill.

This decomposes a sleeve's per-period returns via OLS on a market benchmark
(+ optional style factor) and reports the residual ALPHA (intercept) with its
t-stat. The gate passes only when alpha is positive AND weakly significant —
i.e. the sleeve earns more than its beta/style exposure explains.

Dependency-light (numpy only). Advisory/shadow-first: returns a dict; never
sizes or promotes by itself. Wire it as a leg of the promotion path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

MIN_PERIODS = 20          # minimum aligned return periods for a stable fit
ALPHA_T_MIN = 2.0         # ~95% statistical-significance floor for the alpha t-stat
ALPHA_IR_MIN = 0.10       # economic-significance floor: alpha / residual_std.
                          # Both gates required — a statistically "significant"
                          # but economically tiny alpha (low-noise artifact) is
                          # not tradeable edge.


def attribute_returns(sleeve_returns: List[float],
                      market_returns: List[float],
                      style_returns: Optional[List[float]] = None) -> Dict[str, Any]:
    """OLS: sleeve ~ alpha + b_mkt*market (+ b_style*style). alpha = intercept.

    Returns alpha (per-period residual return), betas, R^2, alpha t-stat, n.
    None-valued fields when the sample is too small / singular."""
    y = np.asarray(sleeve_returns, dtype=float)
    mkt = np.asarray(market_returns, dtype=float)
    n = min(len(y), len(mkt))
    if style_returns is not None:
        n = min(n, len(style_returns))
    if n < MIN_PERIODS:
        return {"ok": None, "n": n, "alpha": None, "alpha_t": None,
                "market_beta": None, "style_beta": None, "r2": None,
                "note": f"n={n} < {MIN_PERIODS} aligned periods"}
    y = y[:n]
    cols = [np.ones(n), mkt[:n]]
    if style_returns is not None:
        cols.append(np.asarray(style_returns, dtype=float)[:n])
    X = np.column_stack(cols)

    try:
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return {"ok": None, "n": n, "alpha": None, "alpha_t": None,
                "market_beta": None, "style_beta": None, "r2": None,
                "note": "singular design matrix"}

    resid = y - X @ beta
    dof = n - X.shape[1]
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    resid_std = float(np.sqrt(ss_res / dof)) if dof > 0 else 0.0
    alpha_ir = (float(beta[0]) / resid_std) if resid_std > 0 else None

    # standard error of the intercept (alpha)
    alpha = float(beta[0])
    alpha_t = None
    if dof > 0 and ss_res > 0:
        sigma2 = ss_res / dof
        try:
            xtx_inv = np.linalg.inv(X.T @ X)
            se_alpha = float(np.sqrt(sigma2 * xtx_inv[0, 0]))
            if se_alpha > 0:
                alpha_t = alpha / se_alpha
        except np.linalg.LinAlgError:
            alpha_t = None
    elif ss_res == 0:
        alpha_t = float("inf") if alpha > 0 else (float("-inf") if alpha < 0 else 0.0)

    return {
        "n": n,
        "alpha": round(alpha, 6),
        "alpha_t": (round(alpha_t, 3) if alpha_t not in (None, float("inf"), float("-inf"))
                    else alpha_t),
        "alpha_ir": (round(alpha_ir, 4) if alpha_ir is not None else None),
        "market_beta": round(float(beta[1]), 4),
        "style_beta": (round(float(beta[2]), 4) if style_returns is not None else None),
        "r2": round(r2, 4),
        "note": "",
    }


def attribution_gate(sleeve_returns: List[float],
                     market_returns: List[float],
                     style_returns: Optional[List[float]] = None) -> Dict[str, Any]:
    """Promotion leg: PASS only when residual alpha > 0 and weakly significant.

    ok=True  — alpha > 0 and |alpha_t| >= ALPHA_T_MIN (skill beyond beta/style)
    ok=False — alpha <= 0, or positive but not significant (returns are beta/style)
    ok=None  — insufficient/un-fittable data (fail-open)"""
    a = attribute_returns(sleeve_returns, market_returns, style_returns)
    if a.get("alpha") is None:
        return {**a, "ok": None}
    alpha = a["alpha"]
    at = a["alpha_t"]
    ir = a.get("alpha_ir")
    sig = (at == float("inf")) or (at is not None and at >= ALPHA_T_MIN)
    econ = (ir is not None and ir >= ALPHA_IR_MIN)
    if alpha <= 0:
        ok = False
        note = "alpha <= 0: returns explained by beta/style, no stock-selection edge"
    elif at is None:
        ok = None
        note = "alpha > 0 but t-stat unavailable"
    elif sig and econ:
        ok = True
        note = ""
    elif not sig:
        ok = False
        note = f"alpha > 0 but t={at} < {ALPHA_T_MIN}: not statistically significant"
    else:
        ok = False
        note = f"alpha > 0 but IR={ir} < {ALPHA_IR_MIN}: economically negligible vs noise"
    return {**a, "ok": ok, "note": note or a.get("note", "")}

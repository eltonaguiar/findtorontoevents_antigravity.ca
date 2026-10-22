"""Ledger-level gate evaluator (Sub-project 1, Task 4).

The four quick-fix gates from spec §2.4 — ``n>=100``, ``PF_net>=1.5``,
``PF_net CI-LB>=1.2``, ``MDD<=20%`` — are LEDGER-LEVEL properties. A single
resolved trade row cannot know how many sibling trades exist for its
strategy+asset_class pair, so these gates cannot live inside
``_is_valid_resolved_pick`` (which is per-pick by design). This module groups
resolved rows by ``(strategy, asset_class)`` and applies the gates to each group.

``MDD`` is computed on the **overlap-aware** equity curve — the same
capital-share weighting as ``compound_overlap_aware`` (Task 3) — because
sequential compounding assigns 100% of capital to every trade and is biased
whenever positions overlap in time. Per-position PnL is applied **un-capped**
here so that a real large loss streak is honestly reflected in drawdown risk
(the ±10% cap in Task 3 governs headline compound returns only, not risk).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from audit_trail.compound_overlap_aware import (
    _entry_ts,
    _exit_ts,
    _pnl_pct_value,
)
from tools.pf_ci_lower import pf_ci_lower, profit_factor

# Gate thresholds (spec §2.4).
MIN_N = 100
MIN_PF = 1.5
MIN_PF_CI_LB = 1.2
MAX_MDD_PCT = 20.0

# Cluster bootstrap defaults.
_ALPHA = 0.05
_N_BOOT = 2000
_SEED = 42


def _make_clusters(rows):
    """Return ``symbol|UTC-day`` cluster keys when available, else None.

    When any row lacks a symbol or a parseable day, returns None (callers then
    fall back to trade-level i.i.d. bootstrap). Cluster keys must align 1:1
    with the pnl list.
    """
    clusters = []
    for r in rows:
        sym = r.get("symbol")
        day = str(r.get("entry_time") or r.get("opened_at") or "")[:10]
        if sym and day:
            clusters.append(f"{sym}|{day}")
        else:
            return None
    return clusters or None


def _overlap_aware_equity_curve(rows):
    """Return cumulative equity factors after each trade under Task-3 shares.

    Reuses the capital-share weighting (1/N_active while open) from
    ``compound_overlap_aware`` but applies each trade's PnL un-capped so that
    MDD reflects true position risk rather than the ±10% headline cap.
    """
    timed = []
    untimed = []
    for idx, pick in enumerate(rows):
        en = _entry_ts(pick)
        ex = _exit_ts(pick)
        pnl = _pnl_pct_value(pick)
        if en is not None and ex is not None:
            timed.append({"idx": idx, "entry": en, "exit": ex, "pnl": pnl})
        else:
            untimed.append({"idx": idx, "pnl": pnl})

    curve = [1.0]
    if timed:
        events = []
        for t in timed:
            events.append((t["entry"], +1, t["idx"]))
            events.append((t["exit"], -1, t["idx"]))
        # Entries precede exits at the same instant -> sort by (ts, -delta).
        events.sort(key=lambda e: (e[0], -e[1]))

        acc = {t["idx"]: 0.0 for t in timed}
        total_dur = {t["idx"]: 0.0 for t in timed}
        open_set = set()
        prev_ts = None
        i = 0
        m = len(events)
        while i < m:
            ts = events[i][0]
            j = i
            while j < m and events[j][0] == ts:
                j += 1
            if prev_ts is not None and ts != prev_ts:
                dur = (ts - prev_ts).total_seconds()
                if dur > 0 and open_set:
                    n_open = len(open_set)
                    share_contrib = dur / n_open
                    for idx in open_set:
                        acc[idx] += share_contrib
                        total_dur[idx] += dur
            group = events[i:j]
            group.sort(key=lambda e: -e[1])
            for _ts, delta, idx in group:
                if delta == +1:
                    open_set.add(idx)
                else:
                    open_set.discard(idx)
            prev_ts = ts
            i = j

        shares = {}
        for t in timed:
            idx = t["idx"]
            dur = total_dur[idx]
            shares[idx] = (acc[idx] / dur) if dur > 0 else 1.0

        ordered = sorted(timed, key=lambda t: (t["exit"], t["idx"]))
        current = 1.0
        for t in ordered:
            current *= 1.0 + shares[t["idx"]] * t["pnl"] / 100.0
            curve.append(current)

    # Untimed tail: applied sequentially at full weight (Task-3 fallback).
    for u in untimed:
        current = curve[-1] * (1.0 + u["pnl"] / 100.0)
        curve.append(current)

    return curve


def _mdd_pct(curve):
    """Peak-to-trough drawdown in percent, relative to the running peak."""
    peak = curve[0]
    max_dd = 0.0
    for eq in curve:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _evaluate_ledger(rows):
    """Apply the 4 gates to a single (strategy, asset_class) ledger."""
    n = len(rows)
    pnls = [_pnl_pct_value(r) for r in rows]

    if n:
        pf_net = profit_factor(pnls)
        ci = pf_ci_lower(
            pnls,
            clusters=_make_clusters(rows),
            alpha=_ALPHA,
            n_boot=_N_BOOT,
            seed=_SEED,
        )
        pf_net_ci_lb = ci["pf_ci_lower"]
        mdd = _mdd_pct(_overlap_aware_equity_curve(rows))
    else:
        pf_net = None
        pf_net_ci_lb = None
        mdd = 0.0

    failures = []
    if n < MIN_N:
        failures.append("n<100")
    if pf_net is None or pf_net < MIN_PF:
        failures.append("pf<1.5")
    if pf_net_ci_lb is not None and pf_net_ci_lb < MIN_PF_CI_LB:
        failures.append("pf_ci_lb<1.2")
    if mdd > MAX_MDD_PCT:
        failures.append("mdd>20")

    return {
        "n": n,
        "pf_net": round(pf_net, 4) if pf_net is not None else None,
        "pf_net_ci_lb": pf_net_ci_lb,
        "mdd": round(mdd, 2),
        "gate_failures": failures,
        "verdict": "OK" if not failures else "UNVERIFIED",
    }


def compute_ledger_gates(rows: list[dict]) -> dict[tuple[str, str], dict[str, Any]]:
    """Group resolved rows by (strategy, asset_class) and apply the 4 gates.

    Returns a dict keyed by (strategy, asset_class) with:

      n                 — int
      pf_net            — float | None (None when n==0)
      pf_net_ci_lb      — float | None
      mdd               — float (percent, e.g. 12.34)
      gate_failures     — list[str] (empty when OK)
      verdict           — "OK" | "UNVERIFIED"

    Degenerate input never raises; a ledger with no rows yields a well-formed
    ``UNVERIFIED`` entry.
    """
    ledgers = defaultdict(list)
    for r in rows:
        if not isinstance(r, dict):
            continue
        strategy = r.get("strategy") or "unknown"
        asset_class = r.get("asset_class") or "UNKNOWN"
        ledgers[(strategy, asset_class)].append(r)
    return {key: _evaluate_ledger(group) for key, group in ledgers.items()}

#!/usr/bin/env python3
"""Attribution probe for the AI tournament (ENHANCEMENT #111 applied) — read-only.

KTD-Fin (arXiv 2605.28359) asks: is an LLM agent's return stock-selection ALPHA,
or just the market/style beta every agent rides?

NOTE on method: the tournament ledger batch-stamps `resolved_at` (only ~4 distinct
resolved days for 5k picks), so there is NO genuine daily time series — time-series
attribution is impossible (a data-structure gap, like the missing signal_ts). So the
benchmark is built CROSS-SECTIONALLY and leakage-free: for each pick on symbol s, the
benchmark return is the **average-agent return on that same symbol** (mean pnl across
ALL models' picks on s). A model's alpha is then its excess over the crowd on the very
symbols it chose — the "did you beat the other LLMs on your own picks" question.

For each model with >= MIN_PERIODS picks we run the #111 attribution_gate (alpha>0 AND
t>=2.0 AND info-ratio>=0.10). Surviving alpha = evidence of real selection skill;
failing = the headline PF was crowd/beta, not transferable edge.

Read-only: loads audit_dashboard/data/ai_tournament_picks_latest.json, mutates
nothing. Usage: python3 tools/attribution_probe.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "verified_strategies"))
import return_attribution as ra  # noqa: E402

PICKS = os.path.join(ROOT, "audit_dashboard", "data", "ai_tournament_picks_latest.json")


def _resolved_pnl(r):
    pnl = r.get("pnl_pct")
    if pnl is None:
        return None
    try:
        return float(pnl)
    except (TypeError, ValueError):
        return None


def build_symbol_benchmark(picks):
    """market_by_symbol[s] = mean pnl across ALL models' resolved picks on s."""
    by_sym = defaultdict(list)
    for r in picks:
        pnl = _resolved_pnl(r)
        if pnl is None:
            continue
        s = r.get("symbol")
        if s:
            by_sym[s].append(pnl)
    return {s: sum(v) / len(v) for s, v in by_sym.items()}


def probe(picks):
    market_by_sym = build_symbol_benchmark(picks)
    by_model = defaultdict(list)   # model -> list of (own_pnl, crowd_pnl_on_symbol)
    for r in picks:
        pnl = _resolved_pnl(r)
        if pnl is None:
            continue
        s = r.get("symbol")
        if s not in market_by_sym:
            continue
        by_model[r.get("model_id") or "?"].append((pnl, market_by_sym[s]))
    out = []
    for m, pairs in by_model.items():
        if len(pairs) < ra.MIN_PERIODS:
            continue
        own = [p[0] for p in pairs]
        crowd = [p[1] for p in pairs]
        g = ra.attribution_gate(own, crowd)
        out.append({"model": m, "n_picks": len(pairs),
                    "alpha": g.get("alpha"), "alpha_t": g.get("alpha_t"),
                    "alpha_ir": g.get("alpha_ir"), "crowd_beta": g.get("market_beta"),
                    "r2": g.get("r2"), "alpha_ok": g.get("ok"), "note": g.get("note")})
    out.sort(key=lambda r: (r["alpha_ok"] is True, r["alpha"] or -9), reverse=True)
    return out


def main():
    picks = json.load(open(PICKS, encoding="utf-8"))
    rows = probe(picks)
    n_alpha = sum(1 for r in rows if r["alpha_ok"] is True)
    print(json.dumps({"benchmark": "average-agent return on the same symbol (cross-sectional, leakage-free)",
                      "n_models_tested": len(rows),
                      "n_with_surviving_alpha": n_alpha}, indent=2))
    print(f"\n{'model':<24}{'picks':>6}{'alpha':>9}{'t':>7}{'IR':>7}{'crowdB':>8}{'alpha?':>8}")
    for r in rows:
        print(f"{r['model'][:23]:<24}{r['n_picks']:>6}{(r['alpha'] or 0):>9.4f}"
              f"{(r['alpha_t'] if isinstance(r['alpha_t'],(int,float)) else 0):>7.2f}"
              f"{(r['alpha_ir'] or 0):>7.2f}{(r['crowd_beta'] or 0):>8.2f}"
              f"{str(r['alpha_ok']):>8}")


if __name__ == "__main__":  # pragma: no cover
    main()

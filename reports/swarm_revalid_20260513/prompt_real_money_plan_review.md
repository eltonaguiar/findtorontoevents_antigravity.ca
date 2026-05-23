# Swarm review: Real Money Edge Plan vs current session reality

## The plan (C:/Users/zerou/.cursor/plans/real_money_edge_plan_ed80c0d8.plan.md)

5 TODO items:
1. snapshot-audit-baseline (pending)
2. enable-class-gates (pending)
3. fast-track-strong-classes (pending)
4. contain-weak-classes (pending)
5. db-lineage-and-backtests (pending)

Baseline cited in plan (as of when plan was written):
- COMMODITY: n=408 WR 67.4% PF 3.92 (strong) → plan calls "primary alpha candidate"
- EQUITY: n=443 WR 54.0% PF 1.60 (Tier-2 candidate)
- ETF: n=100 WR 60.0% PF 1.48 (near Tier-2 PF)
- CRYPTO: n=7875 WR 47.4% PF 1.39 (sub-T2)
- FOREX: n=1825 WR 41.8% PF 0.28 (stressed)
- BOND: n=11 WR 54.5% PF 0.66 (thin)
- Walk-forward missing: COMMODITY, BOND
- Drift alert: TRUE
- Overfit detector: 12 baby_strats flagged

Plan's "Real-money ready gate" criteria:
- ≥2 asset classes sustain Tier-2 (PF≥1.5, WR≥50, n≥100, MaxDD per charter)
- For consecutive monitoring windows
- Pass drift/divergence checks

## Current session reality (2026-05-13)

Latest money-maker-ready report (reports/money_maker_ready_20260512T204049Z.md):
- COMMODITY: n=420 WR 67.4% PF 3.87 — **Tier 1** (only Tier-1 class)
- EQUITY: n=447 WR 53.2% PF 1.55 — Tier 2
- ETF: n=107 WR 56.1% PF 1.34 — Tier 3 (downgraded vs plan)
- CRYPTO: n=7791 WR 46.4% PF 1.36 — Below T3
- FOREX: n=1354 WR 46.1% PF 0.29 — Below (sizing OFF)
- BOND: n=11 (unchanged thin sample)

This session (~24h) shipped:
- 7 production exec-gate PRs: NS-C (CRYPTO UTC), FX1 (FOREX JPY-cross block × 5 symbols), NS-D (ml_crypto_pred LONG reject), NS-F (CRYPTO LONG-in-BEAR reject), VIX-gate (EQUITY VIX), VIX-ETF-extend, VIX+YC combined
- 9 backtests: 4 TIER-1 candidates discovered (EQUITY VIX, ETF VIX, EQUITY YC, EQUITY VIX+YC combined), 1 PARTIAL WIN (WTI-Brent event), 3 FALSIFIED (BOND, gasoline, Donchian+VIX)
- COT timing-leakage audit (PR #941) flagged that COMMODITY PF 3.92 may not survive 3-day publication-lag patch (likely corrected WR 45-55% per deepseek estimate)
- multi_asset_cot PF 21.86 claim still UNVERIFIED — tools/verify_multi_asset_cot_db.py shipped for operator
- Pattern discovered: regime-GATE overlays work (6/7 hit rate), lead-LAG-corr proposals fail (0/4)

## Question to engines

Review the plan against this session reality. Return strict JSON ONLY:

```json
{
  "plan_still_relevant": "<fully | mostly | partially | replace>",
  "todos_now_obsolete": ["<id list>"],
  "todos_still_binding": ["<id list>"],
  "todos_need_revision": ["<id list with brief reason>"],
  "missing_from_plan_critical": ["<thing this session discovered that plan should now include>"],
  "real_money_ready_gate_status": "<met | nearly_met | not_met>",
  "next_3_actions_post_session": [
    {"action": "<concrete>", "owner": "<dev|operator>", "blocker_if_any": "<text>"}
  ],
  "single_most_important_finding_for_real_money_promotion": "<one sentence>"
}
```

## Constraints

- COMMODITY Tier-1 status depends on COT timing leakage being fixed — currently UNVERIFIED
- multi_asset_cot PF 21.86 is fabrication-risk pattern; DB verifier shipped but not yet run
- EQUITY VIX<22 AND YC>0 backtest (PF 4.98 / Sharpe 2.08 / MDD 16.8%) is the BEST risk-adjusted strategy of session — wired in PR #960, default OFF
- Plan's "≥2 classes Tier-2" gate: currently EQUITY (live) + COMMODITY (pending verify) = potentially MET if COMMODITY survives
- Drift alert still TRUE (unchanged); plan's "auto-paper-only" gate not yet implemented

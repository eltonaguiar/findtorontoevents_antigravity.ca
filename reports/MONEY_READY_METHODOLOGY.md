# Money-Ready Methodology — per asset class

**Standing answer to:** *"For someone who has never seen this repo — how do you
determine whether an asset class on findtorontoevents.ca/audit is ready for
real money, and what files do you look at?"*

Status: v1, 2026-05-17. Methodology critiqued by a 3-engine swarm (deepseek +
xai + kilo) grounded in the live baseline. **Open for further critique** —
this is a living document; the goal is a world-class, defensible standard.

---

## TL;DR — the minimal file set (read these 5)

| File | What it gives you |
|------|-------------------|
| `alpha_engine/data/closed_picks.json` | Ground truth — every resolved pick (pnl_pct, asset_class, strategy, status) |
| `audit_dashboard/data/dashboard_data.json` → `performance.asset_class_health` | Canonical per-class WR/PF/n (verdict-grade, post-resolver-v2) |
| `tools/asset_class_edge_report.py` | Per-class WR/PF/n + best edge + most-consistent + **mis-ban check** + low-sample gems. Run it first. |
| `alpha_engine/money_ready_verdict.py` | The gate orchestrator — DSR + PBO + SPA + walk-forward |
| `audit_trail/quality_gates.py` / `alpha_engine/strategy_blocklist.py` | BLOCKED strategies/sources — what was killed and why |

Supporting: `alpha_engine/deflated_sharpe.py` (DSR), `tools/pbo_cscv.py` (PBO),
`alpha_engine/walkforward_validator.py`, `tools/block_bootstrap_ci.py`,
`alpha_engine/confidence_calibrator.py`.

## Step sequence (one pass)

1. `python tools/asset_class_edge_report.py` → per-class WR/PF/n, best edge,
   concentration, mis-ban flags. This is the orientation pass.
2. Read `dashboard_data.json::performance.asset_class_health` for the canonical
   verdict-grade numbers (this is the source of record, not raw aggregates).
3. For each class with `n >= 100`: `python alpha_engine/money_ready_verdict.py`
   → DSR / PBO / SPA / walk-forward gates.
4. Cross-check the BLOCKED lists — confirm no genuine edge was killed (the
   edge-report's mis-ban check does this automatically).

## Live baseline (2026-05-17, 8,421 resolved picks)

| Class | n | WR | PF | Verdict |
|-------|----|-----|-----|---------|
| COMMODITY | 354 | 60.2% | 2.28 | closest — but edge concentrated in CT=F/Cotton (kill-flagged) |
| EQUITY | 44 | 36.4% | 0.71 | thin sample |
| CRYPTO | 6884 | 32.8% | 0.41 | aggregate-toxic; one ml_enhanced edge overfit-suspect |
| FOREX | 932 | 25.6% | 0.35 | sub-floor |
| FUTURES | 203 | 3.0% | 0.06 | catastrophic |

## The gate methodology — current 7 gates

A class is "money-ready" when ALL hold: (a) n≥100 clean resolved picks;
(b) PF≥1.5 AND WR≥50%; (c) DSR≥0.95; (d) PBO≤0.05; (e) walk-forward decay≥0
over 3+ folds; (f) 30-day rolling-clean; (g) top symbol <30% of class picks.

## Critique — what is NAIVE / MISSING (3-engine swarm consensus)

The current 7 gates are a reasonable floor but **not** a world-class standard.
Confirmed gaps (all evidence-cited; convergence across ≥2 engines = signal):

1. **No transaction-cost / slippage adjustment — FATAL.** PF is pre-cost.
   COMMODITY PF 2.28 pre-cost is ≈1.4–1.6 after realistic slippage. *Every
   gate must run on post-cost pnl*, with a per-class cost model
   (crypto ~10/20bps maker/taker; FX 0.5–2 pips; futures $/contract).
2. **WR≥50% gate is wrong for asymmetric payoffs.** Trend-following has
   WR<40% and PF>2 — it would fail. Replace the WR+PF dual-AND with a single
   **expectancy** gate: `E = WR·avg_win − (1−WR)·avg_loss > 0` (post-cost).
3. **n≥100 is too low** for stable DSR/PBO. Raise to n≥250 (≥500 for CRYPTO
   given the volume). At n=100 a 60% WR has a 95% CI of [49.7%, 69.8%].
4. **`money_ready_verdict._dsr_gate()` passes `nb_trials=1`** — kilo flagged
   this as a missing multiple-testing correction. **Re-checked 2026-05-17, 3/3
   swarm consensus (deepseek + xai + cerebras): DEFENSIBLE, not a bug.** DSR
   deflation (AFML eq 14.5) corrects the Sharpe of an *argmax-over-N* selected
   config; the gate tests the *pooled* return series of the whole class, which
   is not a selection step, so the expected-max term is correctly zero at
   `nb_trials=1`. Upstream filtering (blocklist, quality gates) is a genuine
   but *separate* selection bias — it needs its own adjustment, not an inflated
   `nb_trials` inside this call. No code change.
5. **No regime conditioning** — an edge that only worked in a 2020-21 bull
   passes. Require pass on ≥2–3 distinct regimes (bull/bear/sideways).
6. **Survivorship bias** — "resolved picks" excludes strategies killed early,
   inflating all metrics. Account for the kill-list in the denominator.
7. **No capacity / liquidity gate** — top-symbol<30% says nothing about ADV
   depth vs. intended capital.
8. **No drawdown / tail-risk gate** — PF alone is insufficient; add MDD and a
   tail metric (CVaR).
9. **30-day rolling is too short** — 30 crypto picks ≈ 1 day. Use a
   calendar-based window (last 90 days).
10. **No live forward-slippage capture** — paper/shadow PF must be confirmed
    against live fills before sizing.

## World-class gate set (proposed v2 — for critique)

Post-cost, an asset class is money-ready when ALL hold:
1. n ≥ 250 clean resolved picks (≥500 CRYPTO).
2. Expectancy `E > 0` post-cost (replaces WR+PF dual gate).
3. DSR ≥ 0.99. Keep `nb_trials=1` for the class-aggregate test (see critique
   #4 — pooling is not selection). Selection bias from upstream filtering is
   handled separately, not by inflating `nb_trials` here.
4. PBO ≤ 0.05 with reported 95% CI.
5. Walk-forward: decay ≥ 0 **and** every fold's OOS WR ≥ a floor (decay-sign
   alone is meaningless if OOS WR is 5%).
6. Regime robustness: pass on ≥2 of {bull, bear, sideways}.
7. MDD ≤ 20% and CVaR within charter limit.
8. Concentration: top symbol AND top strategy AND top regime each < 30%.
9. Capacity: class ADV ≥ 10× intended per-day capital.
10. 90-day calendar rolling-clean (no degradation).

## Fastest realistic path to money-ready (per class)

1. **COMMODITY** — n=354 already. Blockers: CT=F concentration >30% + no cost
   model. De-concentrate, add cost model, rerun gates. ~4–6 weeks.
2. **EQUITY** — only blocker is n=44. Accrue ~200+ clean picks on existing
   edges, then full gates. ~2–3 months.
3. **CRYPTO** — aggregate toxic. Isolate the one real ml_enhanced edge, kill
   the drag systems, grow it in isolation. ~4+ months.
4. **FOREX** — WR/PF sub-floor. Needs new edge discovery (carry factor) or
   rebuild. ~6+ months. Keep `FOREX_HARD_DISABLE` on.
5. **FUTURES** — PF 0.06. Abandon the current `futures_momentum` strategy and
   restart from a term-structure thesis. Not a near-term path.

---

*Critique this doc. Each gap above should be either implemented as a gate or
explicitly rejected with a rationale. The methodology is not done until a
quant reviewer would stake real capital on a class that passes it.*

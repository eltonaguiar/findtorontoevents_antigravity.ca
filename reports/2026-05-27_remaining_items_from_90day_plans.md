---
title: "Remaining Items from 90-Day Plans (everything not in quick-wins)"
date: 2026-05-27
companion: reports/2026-05-27_quick_wins_from_90day_plans.md
source: reports/90day_gap_analysis_2026-05-15.md + 8 per-class plans (deduped)
---

# Remaining Items by Class

Format per row: M-id (from master plan) | Action | Effort (S/M/L) | Dependency | Why deferred

## CRYPTO

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| M-004 | quan_engine drag autopsy + auto-quarantine (>40% vol + PF<1) | M | Existing 5% cap may already mitigate; verify before adding rule | Foundation PR #9 may change CRYPTO drag picture |
| M-034 | Confidence-inversion gate | S | PR #9 supersedes this with proper zero-out + penalty | Wait for PR #9 merge |
| M-038 | MEMECOIN BLOCKED_SOURCE_SYSTEMS entry | S | User approval (BLOCKED_* discipline) | Listed in QA-2 |
| — | ADV minimum gate (>$1M daily vol) in production path | S | None | Should join QW set next sprint |
| — | Source whitelist (dna_winner_picks + mega_mutation + kimi + baby_strats_forward only) | M | Architectural change to routing | Larger refactor; needs design RFC |

## EQUITY

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| M-009 | PEAD on top-100 large-cap (NEW strategy, not the killed `equity_pead_strategy.py`) | M | h010 harness REJECTED prior PEAD; new pre-registered hypothesis required | PR #12 close → wait for new hypothesis |
| M-025 | Overnight intraday reversal strategy | M | Module doesn't exist; need backtest first | Build after VIX gate (QW-1) closes |
| M-026 | DOW tilt (Tue/Wed long bias) | S | score_booster hook identified | Low-impact tune; do after QW-1 |
| — | Large-cap universe expansion 30→100 symbols | M | Tightly coupled to QW-1 — need clean universe before VIX gate matters | Stage 2 of QW-1 sprint |
| — | Remove 8 speculative tickers from EQUITY_SYMBOLS (NIO/LCID/RIVN/SNDL/GME/AMC/PLTR-low-float) | S | None directly, but soft-PR (would feel like deny-listing without enough discussion) | Pair with QA-1 PENNY approval |
| — | Slippage validator + vol-target sizer for EQUITY (M-017/018) | M | M-017/018 scaffolds exist in PR #1026; not wired | Cost realism layer; deferred to B1 workstream |

## COMMODITY

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| M-008 | COT MATCH gate + DSR≥0.85 block on non-MATCH | S | `verify_system_pf.py` shipped but not called in `passes_active_gate` | One-line wire; do after QW-5 audit |
| M-021 | COT lag-corrected re-run (PR #941 landed but full re-run not confirmed) | M | Need post-dedup baseline (QW-5) | Same dependency as M-008 |
| M-022 | Commodity carry-momo double-sort opt-in sidecar | M | Backtest research → opt-in module | Build after diversification proof |
| M-039 | Cross-commodity spread (crude/natgas pair) | M | Research module first | Low priority |
| — | Diversify beyond CT=F (GC/NG/KC all in config; production activity negligible) | M | Needs new pick-emit logic across 25 symbols | The actual strategic move; QW-5 is the precursor |

## FOREX

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| M-007 | FOREX_HARD_DISABLE env switch | S | User approval (QA-3) | Listed in QA-3 |
| — | Live carry_yield_diff from FRED rates (not hardcoded snapshot) | S | FRED_API_KEY in secrets | Trivial after FRED key |
| — | Limit universe to 4 majors for paper phase | S | Paper-phase decision | Pair with M-007 |
| — | Real CFTC COT data for 6E/6B/6J futures positioning | M | New data integration | Real edge work; standalone PR |

## BOND

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| M-032 | FRED_API_KEY in GitHub secrets | S | User adds the secret | Unblocks BOND + ETF + EQUITY economic layer |
| M-020 | Walk-forward validator BOND output | M | Need data flow into dashboard | Stage 1 of bond rebuild |
| M-024 | BOND TSMOM sidecar (TLT/IEF/SHY) | M | After M-020 baseline | Real bond strategy work |
| — | 3 research pilots: TIPS MR / curve carry / HYG-LQD credit MR | L | Fully specified in `bond_deep_dive_round2`, unwired | Stage 2 of bond rebuild |

## ETF

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| M-023 | Antonacci sector dual momentum 12-1 | M | Module doesn't exist | Build after QW-2 closes |
| M-036 | ETF universe expansion (XLF/XLE/XLK → n=150) | M | Tied to M-023 | Stage 2 of ETF rebuild |
| — | Black-Litterman (PyPortfolioOpt) | L | LinAlgError on rolling cov; needs Ledoit-Wolf fix | Tier 3 infrastructure |
| — | FRED economic momentum (currently BLOCKED by missing key) | S | FRED_API_KEY | Pair with M-032 |

## FUTURES

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| — | MERGE FUTURES→COMMODITY tile (recommendation) | M | UI + dashboard change | After COMMODITY hygiene (QW-5) |
| — | Fix =F→COMMODITY misclassification (conf_floor 0.50 → 0.40) | S | None | Pair with merge decision |

## PENNY_MEME

| M-# | Action | Effort | Depends on | Why deferred |
|---|---|---|---|---|
| QA-1 | PENNY_STOCK class-wide gate in quality_gates.py | S | User approval | Listed in quick-wins-pending-approval |
| QA-2 | MEMECOIN active-gate block (still emits via goldmine_meme/incubator/kimi) | S | User approval | Same |
| — | ADV minimum gate (>$1M daily vol) runtime check | S | None | Should be universe-wide rule, not class-specific |

## Universal items from 2026-05-24 Institutional Refresh (not class-specific)

Pulled from the gap analysis appendix — Workstream IDs reference `INSTITUTIONAL_READINESS_PLAN_2026-05-24.md`:

| Gap | Severity | Workstream | Status (best-known) |
|---|---|---|---|
| Per-pick freshness SLA at the gate | P0 | A1 | Unbuilt |
| Cross-provider price reconciliation | P0 | A2 | Unbuilt |
| `smart_score` Platt/isotonic calibration per asset class | P0 | A3 | Foundation PR #9 partially addresses CRYPTO |
| Lookahead leakage in trust columns | P0 | A4 | May-22 audit partial; foundation PR #10 closes gatekeeper path |
| Sum-of-percentages reported as return | P1 | A5 | May-22 partial fix shipped |
| Transaction-cost / slippage layer | P1 | B1 | Scaffold in PR #1026 unwired |
| Regime classifier / macro-calendar blackout | P1 | B2 | Unbuilt |
| Portfolio-construction constraints | P1 | C1 | Black-Litterman blocked by LinAlg issue |
| Real-time monitoring & alerting | P0 | G1 | Unbuilt |
| Circuit-breaker on Stage-1 floor violation | P0 | G2 | Unbuilt |
| Data lineage / `source_id` / `model_version` | P1 | G3 | Unbuilt |
| Golden-set regression in CI | P1 | G4 | Unbuilt |
| Per-pick explainability | P2 | G5 | Unbuilt |
| Stress / scenario replays | P2 | G6 | Unbuilt |

# How to use this list

1. **Don't drown.** The foundation-fix PRs (#9, #14, #15) must close first or none of the strategy work matters.
2. **Then sprint:** QW-1 + QW-2 + QW-3 + QW-5 in one batch (3 strategy PRs + 1 audit report).
3. **Then approval items:** QA-1 + QA-2 + QA-3 if/when the user approves the BLOCKED_* edits.
4. **Then infrastructure:** workstreams A1–A5 from the May-24 institutional refresh.
5. **Then per-class rebuilds:** each class's M-xxx queue runs in parallel after foundation+infra is solid.

The full master plan with all M-xxx IDs lives at `reports/MASTER_ACTION_PLAN_2026-05-15.md`.

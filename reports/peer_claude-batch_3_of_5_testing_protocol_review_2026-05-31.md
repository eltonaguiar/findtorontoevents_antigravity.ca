# Batch 3 of 5 — Testing / Methodology File Review (2026-05-31)

**Reviewer:** peer_claude (Opus 4.7)
**Source list:** `reports/peer_claude-DUPE_SCAN_TESTING_PROTOCOL_2026-05-31.md` § Batch 03
**Canonical baseline for threshold conflict checks:** `docs/PAPER_PILOT_HARNESS.md`
(graduation: `n_closed >= 500`, Wilson 95% LB > break-even, bootstrap PF CI lo > 1.0, Bonferroni p < 0.05/7 = 0.00714)

## Batch summary

- Files reviewed: **18**
- Redundant-with-another-batch-file: **8** (the dated `money_maker_ready_*` series is one rolling snapshot)
- Threshold/methodology conflicts vs canonical (PAPER_PILOT_HARNESS.md n>=500 / Wilson / Bonferroni / PF-CI-lo): **9 files** state weaker / different thresholds
- Canonical-recommendation candidates from this batch: **3**
  - `reports/money_maker_ready_v2_deep_dive_2026-05-31.md` — most recent, sub-strategy framing
  - `reports/money_ready_per_class_synthesis_2026-05-31.md` — most recent per-class synthesis with mutate-before-kill framing
  - `reports/peer_claude-URGENT_METHODOLOGY_FLAG_MC_AUDIT_TOOL_2026-05-31.md` — formal P0 methodology flag (capped-MC fakery)

## Per-file classification

| # | File | mtime | size | WHAT_IT_DEFINES | REDUNDANT_WITH | CONFLICT_WITH (vs PAPER_PILOT_HARNESS.md) |
|---|------|-------|------|------------------|----------------|--------------------------------------------|
| 1 | `reports/money_maker_ready_20260515T211949Z.md` | 2026-05-25 | 17.9k | Per-class snapshot 2026-05-15: WR/PF/n table, system-winners gate (PF≥1.5, WR≥50%, n≥100, MDD≤20%), WFA fold tables | Same template as #2, #3, #11 dated snapshots | **CONFLICT**: uses `n≥100` graduation (canonical = `n≥500`). No Wilson LB / Bonferroni gate. |
| 2 | `reports/money_maker_ready_20260516T000106Z.md` | 2026-05-25 | 17.6k | Per-class snapshot 2026-05-16T00Z: WR/PF/n + banner-vs-actual reconciliation | Superset of #1 | **CONFLICT**: same `n≥100` floor; tiers expressed as PF/WR only, no DSR/PBO/CI gates |
| 3 | `reports/money_maker_ready_20260516T060000Z.md` | 2026-05-29 | 8.3k | IS/OOS bootstrap on `signal_validation`/`kimi_signal_tracking`/`aggregated_picks`/`stocks_competition` — 5000-iter CI | Updates #2 with bootstrap layer | **PARTIAL CONFLICT**: Bootstrap is 5000-iter (canonical 1000); no Bonferroni; uses `n≥100 independent` floor for Tier 1 |
| 4 | `reports/money_maker_readyv2_2026-05-17.md` | 2026-05-25 | 8.5k | v2 corrigendum: concentration gate (<30%) MUST run before DSR/SPA, both 05-17 Tier-1 PASSes refuted | Foundational doc behind ADDENDUM/NORTH_STAR (#5, #8) | No conflict — adds gate canonical lacks |
| 5 | `reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md` | 2026-05-25 | 7.8k | TODO ladder: stat kill-gate (min-n + binomial + Wilson), verdict-tile spec (T1=PF>2/WR>55, T2=PF>1.5/WR>50), DSR/PBO/WFE ship list | Subset of #8 NORTH_STAR | **PARTIAL CONFLICT**: keeps tier defs PF/WR-only; n-floor undefined here (defers to MASTER_ACTION_PLAN) |
| 6 | `reports/money_maker_ready_v2_deep_dive_2026-05-31.md` | 2026-05-31 22:44 | 5.7k | **LATEST.** 10,000-sample MC bootstrap on `trading_picks`; 5 CRYPTO sub-strats Tier-1, 2 EDGE FOREX/COMMODITY; "winners diluted by class-level losers" thesis | Supersedes #1, #2, #3, #11 (older snapshots) | **CONFLICT**: cites Tier-1 strategies at n=30/34/44/45 (e.g. ml_enhanced_DYDXUSDT n=34) — far below canonical n≥500. **This is the exact methodology #15 (URGENT FLAG) refutes — capped-MC bootstrap may be the source.** |
| 7 | `reports/MONEY_MAKER_READYV2_FREEBUFF_INTEGRATION_2026-05-19T0030Z.md` | 2026-05-25 | 7.7k | Infra integration: db_health_check Tier-1 panel, swarm-coverage Tier-1 (DSR/PSR/MinTRL personas) | Adjacent infra to #8 | No threshold conflict (infra-only) |
| 8 | `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` | 2026-05-25 | 14.2k | **Methodology spine v2.** Tier-2 = PF≥1.5/WR≥50/MDD<20/n≥100; Tier-1 = PF≥2/WR≥55/MDD<10; DSR > 0.95 (both tiers) | Parent of #5, #7; partial overlap with `docs/PERFORMANCE_CHARTER.md` | **CONFLICT**: `n≥100` Tier-2 floor (canonical `n≥500`). Adds DSR≥0.95 (canonical doesn't require DSR). Uses `MDD` instead of bootstrap PF CI lo. |
| 9 | `reports/MONEY_READY_METHODOLOGY.md` | 2026-05-25 | 6.9k | Names the gate orchestrator (`alpha_engine/money_ready_verdict.py`), gates (a–e): n≥100, PF≥1.5, WR≥50, DSR≥0.95, PBO≤0.05, WFE decay≥0. **Self-critiques n≥100 as too low**; recommends n≥250 (≥500 CRYPTO). | Overlaps #8 (NORTH_STAR) and `audit_dashboard/CLAUDE_TOP_PICKS_METHODOLOGY.md` (batch 0) | **CONFLICT (self-aware)**: explicitly notes `n≥100 is too low for stable DSR/PBO; raise to n≥250 (≥500 CRYPTO)`. This is the swing-doc on the n-floor debate. Bridges to canonical n≥500. |
| 10 | `reports/money_ready_per_class_synthesis_2026-05-31.md` | 2026-05-31 22:44 | 8.1k | **LATEST.** Per-class verdict + reason-of-block + fix priority. Thesis: plumbing/resolver/mislabel are the bottleneck, not strategy supply. Names dormant proven edges (etf_cross_sectional_momentum PF 2.05, dxy_trend_filter PF 1.63/n=995). | Supersedes #1–#3, #11–#13 | No explicit threshold restatement (delegates to charter); uses PF/Sharpe/MDD without n-floor restatement |
| 11 | `reports/money_ready_state_2026-05-12T23Z.md` | 2026-05-25 | 8.2k | Earliest dated state — uses **Tier 3** band (PF≥1.2, WR≥45%, n≥100); promotion to Tier 2 = "3 consecutive months clean WF + n≥100" | Superseded by #6, #10 | **CONFLICT**: introduces Tier 3 (PF≥1.2, WR≥45%) — a band that doesn't appear in canonical, doesn't appear in `PERFORMANCE_CHARTER.md`, and is not used anywhere else in this batch. **Drift.** |
| 12 | `reports/money_ready_validation_plan_2026-05-11.md` | 2026-05-25 | 12.6k | Critiques an earlier (Chinese) report's diagnoses; produces per-class corrected table | Superseded by #10 | **CONFLICT**: cites `multi_asset_cot PF=12.16 n=91` as actionable T1 — fails canonical n≥500 + concentration gate (now known via #4 to be 85% CT=F) |
| 13 | `reports/money_ready_verdict_2026-05-17.json` | 2026-05-25 | 5.8k | Verdict-engine output: per-class DSR/PBO/SPA + verdict string | Same as #14 (twinned md/json) | **CONFLICT**: SPA family-wise α=0.1 (canonical Bonferroni FW α=0.05); DSR threshold = 0.95 (canonical uses bootstrap PF CI lo > 1.0 instead) |
| 14 | `reports/money_ready_verdict_2026-05-17.md` | 2026-05-25 | 1.0k | Markdown table view of #13 + gate definitions (DSR≥0.95, SPA p≤0.1) | Duplicates #13 | **CONFLICT**: same SPA α=0.1, DSR≥0.95 — divergent test stack vs canonical |
| 15 | `reports/peer_claude-URGENT_METHODOLOGY_FLAG_MC_AUDIT_TOOL_2026-05-31.md` | 2026-05-31 22:46 | 4.0k | **P0 methodology flag.** Capped-MC tool ranks tier labels by bootstrapping `pnl_pct` clamped to `[SL, TP]` → systematically inflates winners. Demands: bootstrap realized series only; use paper-pilot harness as truth. | Stands alone — most recent | **AGREES with canonical**: explicitly endorses `paper_pilot_harness` n≥500 + Wilson LB as discipline. **Indicts #6 (deep_dive) by implication** (10k-sample bootstrap on capped pnl_pct). |
| 16 | `reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md` | 2026-05-25 | 2.9k | Compact tier card: T2 PF>1.5/WR>50/MDD<20; T1 PF>2/WR>55/MDD<10. 14-day shadow + Wilson 95% LB for gate rollouts. | Subset of #8 NORTH_STAR | No explicit n-floor; aligns with canonical Wilson concept but doesn't state n |
| 17 | `reports/roadmap_no_edge_to_money_ready_2026_05_18.md` | 2026-05-25 | 6.6k | Promotion criteria: `n≥100 · WR≥0.52 · PF≥1.5 · DSR≥0.95 · PBO≤0.55 · MDD<20%`; calls itself Tier-2 per `PERFORMANCE_CHARTER.md` | Same threshold stack as #9 (MONEY_READY_METHODOLOGY) | **CONFLICT**: `n≥100` (canonical `n≥500`); PBO≤0.55 (very loose vs MONEY_READY_METHODOLOGY's PBO≤0.05) — **internal contradiction with #9 on PBO** |
| 18 | `scripts/deploy_testing_protocol_tables.py` | 2026-05-25 | 7.5k | DDL: creates 5 tables in ejaguiar1_stocks per `TESTING_PROTOCOL.MD` Section 9 (strategy_test_runs, strategy_status_history, etc.) | Implements section 9 of root `TESTING_PROTOCOL.MD` (batch 4) | Code only — no thresholds stated; cross-check against `TESTING_PROTOCOL.MD` for schema-vs-doc drift (batch 4 owns the spec) |

## Conflicts found (vs canonical PAPER_PILOT_HARNESS.md and inter-file)

**Conflict bucket A — n-floor (graduation sample size):**
- Canonical (`PAPER_PILOT_HARNESS.md`): **n_closed >= 500**
- Files asserting `n >= 100`: #1, #2, #5, #8, #9 (then self-corrects), #11, #17, plus implicitly #6 (tier-labels at n=30..45)
- File closest to canonical: **#9 MONEY_READY_METHODOLOGY.md** explicitly states `n≥100 is too low ... raise to n≥250 (≥500 CRYPTO)` — confirms canonical is the right standard, but is buried in a section critique.

**Conflict bucket B — significance test:**
- Canonical: **Bonferroni 0.05 / 7 = 0.00714, one-sided exact binomial vs break-even**
- #13/#14 verdict: SPA family-wise α = **0.1** (14x looser)
- #5, #16: Wilson LB only, no Bonferroni
- #6 deep_dive: 10k MC bootstrap, no multiple-testing correction visible

**Conflict bucket C — DSR/PBO additions not in canonical:**
- #8, #9, #13, #14, #17 require DSR≥0.95 + PBO≤0.05 (or 0.55) + SPA — canonical paper-pilot harness uses **bootstrap PF CI lo > 1.0** instead.
- **Inter-file conflict**: #9 says `PBO≤0.05`, #17 says `PBO≤0.55` — 11x looser. Pick one.

**Conflict bucket D — tier band drift:**
- #11 introduces a **Tier 3** band (PF≥1.2, WR≥45%) that does not appear in `PERFORMANCE_CHARTER.md` nor in any other batch-3 file. Recommend retiring "Tier 3" terminology.

**Conflict bucket E — methodology of MC bootstrap itself:**
- #6 (latest deep-dive, 2026-05-31) uses 10k-sample capped MC and ships Tier-1 labels at n=30–45.
- #15 (URGENT FLAG, same day) explicitly demands these labels be discarded.
- **Internal P0 contradiction between two 2026-05-31 docs.** #15 wins on methodology; #6's tier labels should be quarantined until rewritten per #15.

## Canonical recommendations (this batch)

1. **Keep as canonical / forward-looking:**
   - `reports/money_ready_per_class_synthesis_2026-05-31.md` (#10) — current per-class verdict + dormant-edge ledger
   - `reports/peer_claude-URGENT_METHODOLOGY_FLAG_MC_AUDIT_TOOL_2026-05-31.md` (#15) — overrides #6 tier labels
   - `reports/MONEY_READY_METHODOLOGY.md` (#9) — only doc that self-corrects toward canonical n≥500

2. **Quarantine / mark superseded (move to `reports/archive/money_maker_ready/`):**
   - #1, #2, #3, #11, #12 (dated state snapshots — superseded by #6/#10)
   - #4, #5, #7, #8 (v2 ADDENDUM/NORTH_STAR/FREEBUFF) — keep #8 as historical methodology record, archive the rest
   - #13, #14 (money_ready_verdict 2026-05-17 — dated snapshot, divergent SPA α)
   - #17 (roadmap, divergent PBO≤0.55)

3. **Quarantine pending rewrite:**
   - #6 `money_maker_ready_v2_deep_dive_2026-05-31.md` — fresh date but uses the methodology #15 flagged as wrong. Add a banner: "TIER LABELS INVALID per URGENT_METHODOLOGY_FLAG."

4. **Code reference (no archival needed):**
   - #18 `scripts/deploy_testing_protocol_tables.py` — alive, deploys schema for active TESTING_PROTOCOL.MD section 9.

## Open questions for the consolidator

- Should `Tier 3` (PF≥1.2, WR≥45%) be eliminated repo-wide? Currently only #11 uses it.
- Is canonical `n≥500` blanket, or per-class (CRYPTO≥500, EQUITY/FOREX/ETF/COMMODITY/BOND≥250)? #9 implies per-class is more honest.
- Does the existing `alpha_engine/money_ready_verdict.py` actually enforce the n-floor from #9, or just compute the gates? (Batch 0 owns this file.)

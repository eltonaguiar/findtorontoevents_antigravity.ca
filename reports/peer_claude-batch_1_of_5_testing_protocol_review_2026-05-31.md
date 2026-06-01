# Batch 1 of 5 — Testing Protocol File Review (2026-05-31)

Author: peer_claude (Opus 4.7)
Source list: `reports/peer_claude-DUPE_SCAN_TESTING_PROTOCOL_2026-05-31.md` → "Batch 01" (18 files).
Method: read each, classify WHAT_IT_DEFINES / LAST_MODIFIED / REDUNDANT_WITH / CONFLICT_WITH.

## Files reviewed: 18

| # | File | LAST_MODIFIED | WHAT_IT_DEFINES | REDUNDANT_WITH | CONFLICT_WITH PAPER_PILOT_HARNESS.md |
|---|---|---|---|---|---|
| 1 | `audit_dashboard/data/money_ready_archive/money_ready_2026-05-29.json` | 2026-05-30 23:46 | Dated daily verdict snapshot (per-class verdict + Tier classification) | Series of 12 archive snapshots — pure history, no method | none (data, not methodology) |
| 2 | `audit_dashboard/data/money_ready_archive/money_ready_2026-05-30.json` | 2026-05-31 05:55 | Dated snapshot | same series | none |
| 3 | `audit_dashboard/data/money_ready_archive/money_ready_2026-05-31.json` | 2026-05-31 22:44 | Dated snapshot | same series | none |
| 4 | `audit_dashboard/data/money_ready_verdict.json` | 2026-05-31 22:52 | LIVE verdict (consumed by dashboard + CI gate) | Identical schema to archive series; today's row | none (data) |
| 5 | `audit_dashboard/money_ready_filter.js` | 2026-05-25 20:29 | Dashboard JS filter — MONEY_READY preset: DSR≥0.95 OR SUPREME_EDGE_REAL list; confidence≥0.70; per-class score floors (CRYPTO 70 / EQUITY 60 / COMMODITY 65 / FOREX 70) | Implements the surface of `MONEY_READY_METHODOLOGY.md` / `money_ready_verdict.py` | **CONFLICT** — uses confidence/score thresholds and DSR≥0.95 as gates; PAPER_PILOT_HARNESS uses Wilson lb + Bonferroni p<0.00714 + n≥500. Two parallel gating frameworks live side-by-side. |
| 6 | `CLAUDE.md` | 2026-05-31 22:44 | Project north-star, peer-coord rules, wire-up rule, filename conventions | Canonical project doc | none (process, not threshold) |
| 7 | `config/charter_floors.yaml` | 2026-05-25 20:29 | Machine-readable charter thresholds: T1 MDD≤0.10, T2 MDD≤0.20; drawdown circuit breakers; MC validation gate (median MDD<0.25); edge-cost ≥3× | Loaded by PERFORMANCE_CHARTER.md text; same numbers | **CONFLICT** — no `n_floor=500`, no Bonferroni, no Wilson; uses tier-based MDD/PF/WR only |
| 8 | `docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md` | 2026-05-25 20:29 | AI-tournament: per-class horizons, leaderboard tiers T1/T2/T3, hallucination penalty, prompt protocol | Tier table duplicates PERFORMANCE_CHARTER §2 with **different thresholds** (T3=PF≥1.3 vs charter T3=PF≥1.2) | **CONFLICT** — tournament T1 PF≥2.0 / WR≥55%; T2 PF≥1.5 / WR≥50%; T3 PF≥1.3 / WR≥45%. No n-floor stated. PAPER_PILOT requires n≥500 + Bonferroni; tournament has no statistical-gate column at all. |
| 9 | `docs/COMPOUND_FILTER_METHODOLOGY.md` | 2026-05-25 20:29 | Compound trust+score filter analysis; flags lookahead in trust_score | Sibling to MONEY_READY_METHODOLOGY / CONFIDENCE_METHODOLOGY | **CONFLICT** — uses raw thresholds (trust≥3, score≥50, WR≥55%, PF≥1.50) on n=60-1000 ranges; cites "n=60 borderline sample size" — far below PAPER_PILOT's n≥500 graduation floor |
| 10 | `docs/METHODOLOGY_FOR_EXPERTS.md` | 2026-05-25 20:29 | Mar-24 expert-review doc: 4-component scorer, 29 gates, hedge-fund expert audience | Older snapshot of overall system methodology; partly superseded by MONEY_READY/PERFORMANCE_CHARTER | none directly (no graduation thresholds), but **STALE** — claims 1965-trade aggregate from Mar-24, predates resolver v2 + cursor framework |
| 11 | `docs/PAPER_PILOT_HARNESS.md` | 2026-05-31 23:06 | **CANONICAL** — cursor statistical framework: Wilson lb 95%, bootstrap PF CI (1000 resamples), Bonferroni 0.05/7=0.00714, **n_closed≥500**, 4-gate graduation; 7 paper strategies | — | (this IS the reference) |
| 12 | `docs/PERFORMANCE_CHARTER.md` | 2026-05-25 20:29 | Charter: Tier 1 PF≥2.0/WR≥55/MDD≤10/n≥200; Tier 2 PF≥1.5/WR≥50/MDD≤20/**n≥100**; Tier 3 PF≥1.2/WR≥45/MDD≤25/n≥100. Claims "CANONICAL" | Tier table duplicated by AI_TOURNAMENT (differs on T3 PF) and money_ready_filter.js (via DSR mapping) | **MAJOR CONFLICT** — charter says n≥100 enables clean tier classification; PAPER_PILOT_HARNESS says n≥500 to graduate. **5x discrepancy**. No mention of Bonferroni or Wilson CI in charter. |
| 13 | `docs/STRATEGY_PIPELINE_END_TO_END_2026-05-31.md` | **MISSING** (not on disk) | Referenced by scan but `ls` reports no-such-file | n/a — likely stale entry in find listing OR transient worktree file | n/a |
| 14 | `docs/swarm_prompts/METHODOLOGY_R2.md` | 2026-05-25 20:29 | Swarm-prompt template for "design methodology R2" — references edge_stability_harness, eff≥0.30, M-107 | Prompt template, not a normative doc | none (asks model to specify; doesn't set thresholds itself) |
| 15 | `docs/swarm_prompts/MONEY_READY_HARVEST_v1.md` | 2026-05-25 20:29 | Compact swarm prompt: "Tier-2 charter per class: PF≥1.5, WR≥50%, MDD<20%, **n≥100 clean post-dedup**" | Same Tier-2 floor as PERFORMANCE_CHARTER | **CONFLICT** — n≥100 vs PAPER_PILOT n≥500 |
| 16 | `docs/swarm_prompts/MONEY_READY_MASTER_v1.md` | 2026-05-25 20:29 | Larger swarm-consult prompt: pf_registry policy_clean_net is ledger only; harness must clear forward | Sibling of HARVEST_v1; references same Tier-2 charter implicitly | implicit conflict (inherits charter n≥100) |
| 17 | `docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md` | 2026-05-25 20:29 | Methodology revision proposal (2026-05-13 vintage); pre-cursor-framework | Superseded by PAPER_PILOT_HARNESS for the 7 paper strategies | likely stale; check whether thresholds collide with cursor framework |
| 18 | `.github/workflows/money-ready-registry-gate.yml` | 2026-05-25 20:29 | CI gate: blocks merge when `money_ready_verdict.py` declares MONEY_READY for a class that `pf_registry` rates below Tier-2 PF floor | Enforces consistency between `money_ready_verdict.py` and `pf_registry.json` — uses charter Tier-2 PF floor (1.5) | none with PAPER_PILOT (different surface); inherits charter Tier-2 PF floor |

## Conflicts summary (highlighted)

**Three frameworks coexist with incompatible thresholds:**

1. **PAPER_PILOT_HARNESS.md (cursor statistical framework, 2026-05-31, NEWEST)**
   - Graduation requires: `n_closed ≥ 500`, Wilson lb WR > break-even, PF CI lo > 1.0, p < 0.00714 (Bonferroni 0.05/7).
   - Applies to 7 named paper strategies (connors_rsi2, faber_tactical, fx_carry, magic_formula, piotroski, post_ipo_drift, tsmom).
   - Status: written today, post-policy-clean cohort.

2. **PERFORMANCE_CHARTER.md (2026-04-28 v1.0, last touched 2026-05-25)**
   - Tier 2 (sized-up live capital floor): PF≥1.5, WR≥50%, MDD≤20%, **n≥100**.
   - Tier 1: PF≥2.0, WR≥55%, MDD≤10%, n≥200.
   - No Wilson, no Bonferroni, no graduation-gate concept.
   - Claims "CANONICAL — single source of truth for all tier thresholds".

3. **AI_PREDICTION_TOURNAMENT_METHODOLOGY.md (2026-05-25)**
   - T3 = PF≥1.3 / WR≥45% (charter says PF≥1.2 / WR≥45%).
   - No n-floor specified at all.

**The "CANONICAL" label appears on BOTH `PERFORMANCE_CHARTER.md` AND `PAPER_PILOT_HARNESS.md`** with different numbers (n≥100 vs n≥500). One of them is wrong, or the two doc scopes need to be distinguished:
- Charter = retrospective tier classification of any cohort.
- Paper-pilot = forward-pilot graduation rule for the 7 cursor strategies.

If that distinction is the actual intent, it must be stated explicitly in both docs. Right now both claim sole authority.

**Tournament T3 PF≥1.3 vs Charter T3 PF≥1.2** is a smaller but real numeric conflict that should be reconciled.

**`money_ready_filter.js`** uses a completely different gating axis (DSR≥0.95 + confidence≥0.70 + per-class score floors). It is the live dashboard surface but its thresholds are not in either canonical doc.

## Canonical recommendations

1. **PAPER_PILOT_HARNESS.md** keep as canonical for forward paper-pilot graduation (7 named strategies). Add an explicit scope sentence: "Applies only to the 7 cursor-framework paper strategies. For retrospective tier classification across the full live book, see `PERFORMANCE_CHARTER.md`."
2. **PERFORMANCE_CHARTER.md** keep as canonical for retrospective tier classification. Add a scope sentence: "These tier thresholds apply to any closed-pick cohort with n≥100. Live-capital sizing of new strategies additionally requires the PAPER_PILOT_HARNESS.md graduation gates."
3. **AI_PREDICTION_TOURNAMENT_METHODOLOGY.md** reconcile T3 PF to 1.2 (match charter) and add minimum-n disclosure.
4. **money_ready_filter.js** add a header comment cross-linking to `MONEY_READY_METHODOLOGY.md` and stating that DSR-based gating is the v2 surface, not a replacement for charter tiers.
5. **METHODOLOGY_FOR_EXPERTS.md** mark as `STALE 2026-03-24 SNAPSHOT — see PAPER_PILOT_HARNESS.md for current cursor framework`.
6. **SWARM_REVISED_METHODOLOGY_2026-05-13.md** mark superseded by PAPER_PILOT_HARNESS for the 7 paper strategies.
7. **docs/STRATEGY_PIPELINE_END_TO_END_2026-05-31.md** missing from disk — remove from scan list OR locate the worktree it lives in.
8. **Archive money_ready_archive/*.json** already in correct location; no action.
9. **Swarm prompts (METHODOLOGY_R2, MONEY_READY_HARVEST_v1, MONEY_READY_MASTER_v1)** are templates — fine to keep, but HARVEST_v1's "n≥100 clean post-dedup" floor should be footnoted with the paper-pilot n≥500 graduation floor.

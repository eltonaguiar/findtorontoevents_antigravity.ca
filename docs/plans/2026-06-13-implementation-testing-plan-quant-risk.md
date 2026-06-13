# IMPLEMENTATION & TESTING PLAN — quant + risk reviewed (2026-06-13 ~04:30Z)

**Pipeline:** 7 agent-verified items → quant-desk review (EV/statistical validity) + risk-management review (blast radius/rollback/new-masked-failure analysis) → this plan → swarm review → implement.
**Wave context:** PRs #570/#572/#578/#580 own `quality_gates.py`, `picks_now_professional.py`, `dashboard_generator.py`, `template.html`, `money_ready_verdict.py` tonight. Anything touching those defers post-wave.

## Verdict matrix (both reviewers)

| Item | Quant | Risk | Decision |
|---|---|---|---|
| A. BATTLE_REPORT retire | RETIRE (zero consumers, fabricated "live" data, 24 commits/day noise) | GO tonight (isolated; disable workflow + banner the generator, NOT the regenerated MD) | **IMPLEMENT TONIGHT** |
| D. PM verification harness | Define 3-assertion check; every undetected dead day is unrecoverable | GO tonight — and risk found the no-op RE-ARMED: overlay output is **gitignored** (`.gitignore:322`), double-soft-failed, consumer has no freshness check | **IMPLEMENT TONIGHT** (incl. the gitignore fix) |
| C. COMMODITY republish | Already covered: live verdict publishes 1.048/FAIL; degradation confirmed | NO-GO as republish (4 competing numbers; dedup-less republish = new masked failure); GO as report addendum | **report addendum only** (fold into ledger note) |
| B. KIMI reads migration | Label all 10 NON-LEDGER; migrate ONLY closed-aggregate site :9039 (data exists ledger-side via universal_pick_resolver:161-164) | NO-GO tonight (18k hot file + wave); hard `n>0` assertion required at swap (the 0-row-join precedent) | **post-wave**: labels first, then site-9039 migration w/ parity test (WR delta <2pp, PF <0.1) |
| E. #564 extraction | REJECT: stamp_adj wiring imports a NONEXISTENT function (dead), synthetic downweight keys never exist (dead), recency fix is a no-op; live parts harmful (UNKNOWN→EQUITY contamination; ungated cross-class kill placed BEFORE the funnel logger = unmeasurable kills) | NO-GO; if ever: 3 split PRs, shadow-log-first kill, verbatim pre-change quotes (fabrication-pattern provenance) | **REJECT extraction**; comment on PR; re-derive the regime-mild hypothesis via M-107 if anyone wants it |
| F. picks-now SHORT side | NO-BUILD: long side unvalidated, mega-cap short alpha thin net of borrow, RISK_OFF trigger is lagging — cash is the asymmetric-correct response; publish bottom-10 "AVOID list" instead (testable, zero execution) | NO-GO tonight: inverted TP/SL through the just-merged LONG helper would poison the track record; freebuff page is LONG-framed; needs his ACK | **NO-BUILD**; AVOID-list as future additive; revisit gate = bottom-decile signed IC t<−2 over 6mo |
| G. 12-1 momentum factor | WINNER factor (best evidence/cost: 13mo yfinance pull + 1 column); MUST ship with STRONG_BUY recalibration (643/643 = unthresholded score) | GO-WITH-CONDITIONS post-wave: None-guard every field (the dict.get/None P0 class), sequence after E's hunk resolution | **post-wave**, with IC acceptance test (Spearman IC>0.03, NW t>2, 24mo) + top-quintile cutoff recalibration |

## Tonight's implementation (A + D)

### A. Retire BATTLE_REPORT (30 min)
1. `gh workflow disable battle_test.yml` (rollback = enable).
2. Banner in `battle_test_real_time.py`'s report template: "⚠️ SIMULATED FUNDING RATES — NOT LIVE DATA. Survivor list vintage: 2026-02-17." (so any manual run is truth-labeled; the hourly regen overwrite trap is why the MD itself is NOT the edit target).
3. Scope guard: touch ONLY `battle_test_real_time.py` + the workflow (alpha_engine/battle_test.py, KIMI battle_test*, battle_tester.py are different systems).
4. Tests: consumer grep = 0 (done by both agents); after disable, `gh run list` shows no new cron runs; INCIDENT#137 → RESOLVED.

### D. PM verification harness + persistence fix (1-2h)
1. **Fix the re-armed no-op:** un-gitignore `alpha_engine/data/pm_macro_overlay_signals.json` (negation pattern below `**/data/*_signals.json` at .gitignore:322) + add it to alpha-engine-live's commit step so the overlay snapshot persists between runs.
2. **Loud freshness step** (separate step, NON-blocking for pick emission per risk: enrichment must not gate the scanner): `tools/pm_accrual_check.py` asserting (a) pm_odds_history.jsonl last-line date <36h AND line count grew vs git HEAD~1, (b) overlay snapshot exists + `series` non-empty, (c) pm_leadlag_report.json generated_at <48h. Exit non-zero → `::error` annotation (visible red, not `|| echo`).
3. Consumer warn-log: one-line freshness warning inside `attach_macro_overlay` when snapshot >24h old (macro_overlay_score.py) — warn, never block. [Risk: production_scanner.py is wave-contested — put the warn in macro_overlay_score.py only, which no open PR touches.]
4. Tests: py_compile; dry-run the checker locally against current main state (expect: jsonl PASS at 1 date→FAIL assertion (a) until tomorrow — set assertion (a) to WARN for the first 48h with a dated TODO to harden); workflow YAML valid; next 2-hourly run shows the step green with real output.
5. Calendar: T+48h (Jun-15) assert ≥2 distinct dates; T+7d ≥6; lead/lag claims gated on ≥14 (the quant's INSUFFICIENT_HISTORY rule).

## Deferred queue (post-wave order)
1. E: post REJECT comment on #564 (tonight, comment only) — prevents a bad merge while we sleep.
2. B: NON-LEDGER labels (template-side, after #572/#578/#580) → site-9039 migration with the parity test.
3. G: 12-1 momentum + recalibration (after #564 hunk resolution), IC test attached.
4. F: AVOID-list (additive JSON), freebuff ACK for any page change.
5. C: fold the four-numbers reconciliation into the next ledger note (done in this plan's commit message trail).

## Swarm review of THIS plan (3 reviewers, 2026-06-13) — adopted

- **Consensus (all 3): the regenerated-MD risk for A.** Disabling the workflow alone isn't enough; the banner must be in the GENERATOR. Adopted — banner goes in `battle_test.yml`'s report block AND the static MD (safe to edit now that the workflow is disabled = no overwrite). Belt-and-suspenders.
- **Consensus (2 of 3): D's biggest hole is no end-to-end "impact on picks" test** — verifying the file exists ≠ verifying `macro_overlay_score.py` output reflects the latest overlay. Adopted: harness assertion (b) extended to check ≥X% of cycle picks carry `macro_overlay_meta` (impact, not just existence).
- **Forgotten test (2 of 3): rollback test for A** — re-enable the workflow and confirm it does NOT regenerate a stale/misleading MD. Adopted into A's test gates.
- One reviewer questioned C as "report addendum" risking conflicting data — already mitigated (the addendum re-affirms the FAIL verdict and reconciles, adds no new number).

## Standing rules applied throughout
New outputs go in BOTH the git-add list and FTP list; no `|| echo` without a separate loud freshness check; no edits to wave-contested files; verbatim pre-change quotes for any extraction from agent branches (fabrication pattern); backups before any DB mutation.

# Integration Plan — 28 Open PRs (2026-04-30)

**Author:** orchestrator subagent (claude-opus-4-7 1M)
**Date:** 2026-04-30
**Mode:** READ-ONLY / planning only — no merges, closes, rebases, or pushes performed by this agent.
**Inputs (authoritative, in priority order):**
1. `reports/SESSION_WRAP_2026_04_29.md` (operator-action queue + Subagent B contrary findings)
2. `reports/PR_QUEUE_PROCESSING_2026_04_30.md` (Subagent B per-PR investigation)
3. `reports/NEXT_SESSION_P0_DESIGN_SPECS_2026_04_29.md` (P0 design)
4. `reports/PHASE_3_RANKED_PROPOSALS_2026_04_29.md` (retroactive Phase 3 ranking)
5. Direct GH probes (`gh pr list`, `gh pr checks`, `gh pr diff --name-only`, `gh api .../comments`) executed at 2026-04-30 ~01:10 UTC.

---

## Header

- **Top-priority MERGE candidate:** **PR #520** — COMMODITY agro/oil/silver/gold sub-class kill (Phase 2-D 7/7 panel, CI green per session-wrap, unblocks Goal #1 metals-only universe).
- **Top-priority CLOSE candidate:** **PR #444** — phantom-HALT fix already merged via PR #497 (commit `b546feb1b6`); Subagent A close-comment posted 2026-04-30 00:35 UTC.
- **Inventory totals (28 open PRs):**

| Bucket | Count | PRs |
|---|---|---|
| READY (CI-green or near-green, panel-cleared) | 9 | #511, #512, #520, #530, #448, #447, #446, #531, #449 |
| HOLD (rebase-needed or threshold-renegotiation) | 7 | #529, #476, #477, #461, #513, #450, #457 |
| CLOSE (panel-confirmed superseded/duplicate or reversing intentional kill) | 4 | #444, #445, #528, #452 |
| AMEND (author action required) | 3 | #513, #451, #455 |
| KEEP-OPEN (distinct-scope docs, low priority) | 6 | #453, #454, #456, #458, #473, #507 |

(Total = 29 because #513 appears in both READY and AMEND; the operator merges only after the 2 fact-claim corrections land.)

---

## Per-PR Matrix

Legend: **CI** column counts (`p`=pass, `f`=fail, `s`=skip, `?`=no-checks/queued); **Default** = production behavior at merge time.

| PR# | Title | Default | Files (n / hot-file overlap) | CI | Existing reviewer consensus | Conflicts with | Verdict | Order |
|---|---|---|---|---|---|---|---|---|
| 444 | fix(perf-alerts): phantom HALT realized-PnL fallback | n/a | 2 / `cross_aggregation/performance_alerts.py` | 3p | Claude APPROVE *but* close-comment notes already merged via #497 | #447, #512 | **CLOSE** (already in main) | — |
| 445 | fix(circuit-breaker): stale state max_picks/min_conf | n/a | 2 | 3p | Claude APPROVE *but* close-comment notes already merged via #497 | — | **CLOSE** (already in main) | — |
| 446 | fix(audit): NC active-gate exemptions + crypto tile | ON | 3 / `quality_gates.py:3933,4080`, `template.html` | 2p | Claude APPROVE (Dashboard Fixes) | #507, #520, #529 (quality_gates.py — different hunks; #520 lower lines) | **READY** | 6 |
| 447 | [codex] fix critical findings 48h audit | ON | 6 / `cross_aggregation/performance_alerts.py` | 3p | Claude APPROVE (Workflow Fixes); Subagent B confirms NOT a fork of #448/#449 | #444 (already-merged perf_alerts), #512 | **READY** (independent review) | 9 |
| 448 | fix(critical): 6 surgical bugs (audit+sports) | ON | 7 / `dashboard_generator.py` | 3p | Claude APPROVE; Subagent B confirms independent | #449 (1-file `dashboard_generator.py`), #529 | **READY** | 5 |
| 449 | security: 7 critical vulns (creds/SQLi/XSS) | ON | 15 / `dashboard_generator.py`, multiple PHP | ? (no checks) | Claude APPROVE; Subagent B confirms NOT a fork of #447/#448 | #448 (1 file), #451 (PHP overlap) | **READY** (after manual CI dispatch) | 8 |
| 450 | fix: UNKNOWN labels + stale data warnings | ON | 4 / `template.html`, `sports-betting.html` | 2p1s | Claude APPROVE (UI Fixes) | #452, #454, #457 (template.html) | **HOLD** — superseded by/overlaps #457; merge after #457 settles | 14 |
| 451 | fix(sports-auth): backwards-compat $_GET admin leak | ON | 4 / `sports_*.php` | 1p1f1s | None substantive | #449 (sports PHP) | **AMEND** (smoke fail) | — |
| 452 | docs: 4-day what-if (early version) | n/a | 7 / `template.html`, `sports-betting.html`, `updates/index.html` | 2p1f1s | None | #454 (strict superset) | **CLOSE** (subset of #454) | — |
| 453 | docs(whatif): 4-day asset-class HC lessons | n/a | 2 | 1p | None | #454, #457 (updates/index.html) | **KEEP-OPEN** (narrow docs) | 17 |
| 454 | docs: What-if 4-day + Python analyzers | n/a | 12 / `template.html`, `sports-betting.html`, `updates/index.html` | 2p1s | None | #450, #452 (subset), #455, #457 | **KEEP-OPEN** (superset of #452) | 18 |
| 455 | docs: What-if + HC filter improvements (JS variant) | n/a | 4 / `tools/whatif_4day_analysis.js` | ? (no checks) | None | #454 (similar subject, different artifact) | **AMEND** (CI not run) | — |
| 456 | docs: ROOCODE DeepSeek hedge-fund benchmark | n/a | 2 / `tools/hedge_fund_audit.py` | 2p | None | — | **KEEP-OPEN** (distinct scope) | 19 |
| 457 | fix: Normalize UNKNOWN asset_class from category | ON | 12 / `template.html`, `sports-betting.html`, `updates/index.html` | 2p1s | Subagent B: NOT superseded by #501/#503 (different layer) | #450, #452, #454 | **HOLD** — UI normalization; merge after #520/#529 land | 13 |
| 458 | docs: consolidated asset-class action items | n/a | 1 | 1p | None | — | **KEEP-OPEN** (action-tracking doc) | 20 |
| 461 | fix(asset-class): retire CRYPTO + corrections | ON | 23 / `alpha_engine/strategy_blocklist.py`, log/data noise | ? | Author hygiene note — bot commits injected | #529 (`strategy_blocklist.py`) | **HOLD** — re-extract clean diff vs #529; data-file pollution | 15 |
| 473 | docs: Goal #1 merge execution status note | n/a | 1 | 1p | None | — | **KEEP-OPEN** (low-pri docs) | 21 |
| 476 | feat(mutation-lifecycle): promote/kill governance | OFF | 3 | 1p2f | Claude APPROVE *but* CI failure exposed (Subagent B) — pre-existing test broken on stale base | — | **HOLD** — rebase on current main (post-#482/#495) clears red | 16 |
| 477 | feat(etf): wire Riskfolio-Lib HRP for SPDR | OFF | 3 | 1p2f | Claude APPROVE *but* same stale-base CI failure as #476 | — | **HOLD** — rebase on current main | 17 |
| 507 | feat(cpcv): scaffold strategy-promotion gate | OFF (DRAFT) | 4 / `quality_gates.py:105,3679` | ? | None | #446, #520, #529 (quality_gates.py — different hunks, low risk) | **KEEP-OPEN** (DRAFT; awaits CPCV PF lower-bound > 1.5) | 22 |
| 511 | docs(security): livetrader2026 rotation plan | n/a | 1 | 1p | Claude ACKNOWLEDGE (security-urgent) | — | **READY** | 1 |
| 512 | test(phantom-halt): mixed-unit XFAIL | ON | 2 / `cross_aggregation/performance_alerts.py` | 3p | Claude APPROVE (test-only, xfail strict) | #444 (close-rec), #447 | **READY** | 2 |
| 513 | chore(ueps): emit verification | n/a | 1 | 1p | Claude APPROVE *but* Subagent B amendment-reminder posted (2 wrong fact claims) | — | **AMEND** then merge | 4 |
| 520 | fix(commodity): kill agro/oil/silver/gold | ON | 3 / `quality_gates.py:893,3746-3807,4456-4473` | ? (session-wrap reports CI green run 25141000031) | Phase 2-D 7/7 panel; orchestrator session-wrap "CI GREEN, READY" | #446, #507, #529 (quality_gates.py) | **READY** | 3 |
| 528 | fix(kill-list): refresh last_kill_run | ON (DRAFT) | 2 | ? | Claude APPROVE *but* close-comment posted — REVERSES PR #519 intent | — | **CLOSE** (panel-confirmed; reverses intentional kill expiry) | — |
| 529 | fix(code-review): 19-PR review + 3 surgical fixes | ON | 50 / `quality_gates.py:645,659,3813`, `dashboard_generator.py`, `strategy_blocklist.py`, `updates/index.html` | 1p (drift) | Claude APPROVE with notes | #446, #448, #461, #507, #520 (multiple hot files) | **HOLD** — merge AFTER #520, #448, #446 to absorb their diffs cleanly | 11 |
| 530 | feat(defense): kill-list audit + auto-rollback | OFF (sidecar) | 5 | 3p | Claude APPROVE; session-wrap "27/27 tests, caught real banned-ID emit" | — | **READY** | 7 |
| 531 | feat(forex): A/B replay tool for 5bp threshold | OFF (tool) | 3 | 3p | Subagent A: VERDICT REJECTED on broken non-JPY PF≥5 bar (panel methodology bug) | — | **READY** (tool ships green; threshold renegotiation is follow-up) | 10 |

---

## Merge Sequence (Numbered)

Ordering reflects Phase 3 panel rules (7/7 unanimous): **quantified-drag surgical kills before HIGH-risk default-on gate changes; security/test PRs first as non-blocking warmup; absorb hot-file conflict via strict serial order.**

### Phase A — Non-conflicting warmup (operator-only, can be merged anytime)

1. **PR #511** — docs(security) livetrader2026 rotation plan
   - Why first: security-urgent, single-file docs, no rebase needed, panel 4/4 cleared per session-wrap.
   - Rebase target: none (1 file, no overlap).
   - Decides: operator (auto-mergeable once green).

2. **PR #512** — test(phantom-halt) XFAIL mixed-unit regression
   - Why now: test-only, regression-pin for known issue, no production effect.
   - Rebase target: none.
   - Decides: operator.

### Phase B — Quantified-drag surgical kill (Goal #1 priority)

3. **PR #520** — fix(commodity) kill agro/oil/silver/gold
   - Why position: Phase 2-D 7/7 unanimous, +$30 net via metals-retain. **HOT FILE: `audit_trail/quality_gates.py` lines 893, 3746-3807, 4456-4473.** Merge BEFORE #446, #529, #507 to give them the 4-PR choke-point lead.
   - Rebase target: current main.
   - Expected conflict areas: minimal — touches separate hunks from #446 (3933+), #529 (645,659,3813), #507 (105,3679).
   - Decides: operator. Verify HG=F / PL=F (metals) still in universe AFTER merge.

### Phase C — Code review + critical bug PRs (parallel-safe, distinct file sets)

4. **PR #448** — fix(critical) 6 surgical bugs
   - Why position: independent of #447/#449 per Subagent B file-list intersection (∅, ∅, 1-file). Touches `audit_trail/dashboard_generator.py`.
   - Rebase target: current main.
   - Expected conflict: minor 1-file overlap with #449 (`dashboard_generator.py`); merge #448 first because surgical fixes anchor.

5. **PR #446** — fix(audit) NC active-gate exemptions + crypto tile
   - Why position: hot file `quality_gates.py` lines 3933+ (different hunks from #520). Goal #1 (audit dashboard).
   - Rebase target: post-#520 main.
   - Expected conflict: hunk distance >100 lines from #520 — clean apply expected.
   - Decides: operator after CI re-run.

6. **PR #530** — feat(defense) kill-list audit + auto-rollback (sidecar)
   - Why position: opt-in sidecar, no production behavior change at merge. Session-wrap reports 27/27 tests + caught real banned-ID emit. Wire-up to dashboard_generator + smart_picks_engine is next-session work.
   - Rebase target: current main.

7. **PR #449** — security: 7 critical vulns
   - Why position: 15 files mostly PHP + 1-file overlap with #448 (`dashboard_generator.py`). Manual CI dispatch needed. Security-critical (FMP API key, SQLi).
   - Rebase target: post-#448 main (reconcile dashboard_generator.py 1-file overlap).
   - Decides: operator after manual CI dispatch + green check.

8. **PR #447** — [codex] fix critical 48h audit findings
   - Why position: independent review per Subagent B; touches `cross_aggregation/performance_alerts.py` + audit-dashboard.yml.
   - Rebase target: post-#512 main (#512 also touches `cross_aggregation/performance_alerts.py` test file but should be additive).
   - Expected conflict: low — different hunks.

### Phase D — Higher-risk / threshold-dependent

9. **PR #531** — feat(forex) A/B replay tool
   - Why position: tool ships green (3p CI); verdict was REJECTED but only on a panel methodology bug (non-JPY PF ≥ 5 bar that panel itself flagged unachievable). Tool is opt-in, no production behavior at merge.
   - Rebase target: current main.
   - **OPERATOR DECISION REQUIRED:** re-renegotiate non-JPY PF threshold from 5.0 → 1.5 (matching overall PF bar) per Subagent A finding. Empirical data shows JPY (2.082) OUTPERFORMS non-JPY (1.406), opposite of panel concern.

10. **PR #529** — fix(code-review) 19-PR review + 3 surgical follow-ups
    - Why position: **LAST among hot-file PRs.** Touches `quality_gates.py:645,659,3813`, `dashboard_generator.py`, `strategy_blocklist.py`. Strict serial order required.
    - Rebase target: post-#520 + post-#448 + post-#446 + post-#461 (if #461 is rescued) main. Author needs to rebase against the absorbed cumulative diff.
    - Expected conflict: highest of any PR in this plan (50 files including 4 hot files).
    - Decides: operator after author rebases and CI re-fires.

### Phase E — DEFER (rebase-needed; not in this batch)

11. **PR #476** — feat(mutation-lifecycle) — HOLD: rebase on post-#482/#495 main clears the stale `tests/test_hf_quality_gate_wire.py` red without code change (Subagent B documented). Once author rebases, this becomes READY behind Phase D.
12. **PR #477** — feat(etf) Riskfolio-Lib — same as #476 (identical CI failure; same rebase fix).
13. **PR #461** — fix(asset-class) retire CRYPTO — HOLD: re-extract clean (data-file pollution: `trading_bot.log`, `trading_results.json`, `battle_test_results.json` should not be in commit). Conflicts with #529 on `alpha_engine/strategy_blocklist.py`.
14. **PR #513** — chore(ueps) emit verification — AMEND first (2 wrong fact claims per Subagent B), then merge after #530.
15. **PR #457** — fix: UNKNOWN asset_class from category — HOLD: not superseded per Subagent B but high overlap with #450/#452/#454 on `template.html`+`sports-betting.html`+`updates/index.html`. Defer to next batch after audit-data PRs settle.
16. **PR #450** — fix: UNKNOWN labels + stale data warnings — same as #457 (same 3 hot files).
17. **PR #451** — fix(sports-auth): $_GET admin leak — AMEND: smoke CI failing. Author needs to fix smoke regression; security-urgent so should rebase ASAP.

### Phase F — KEEP-OPEN (low-priority docs, no integration impact)

18. **PR #453** — docs(whatif): 4-day asset-class HC lessons — narrow docs.
19. **PR #454** — docs: What-if 4-day + Python analyzers — superset of #452 but distinct artifact.
20. **PR #455** — docs: What-if + HC improvements (JS variant) — distinct JS artifact; CI not run yet.
21. **PR #456** — docs: ROOCODE DeepSeek benchmark — distinct hedge-fund-benchmark scope.
22. **PR #458** — docs: consolidated action items — action-tracking doc.
23. **PR #473** — docs: Goal #1 merge execution status — low-pri docs.
24. **PR #507** — feat(cpcv) DRAFT — keep open per Phase 3 panel; awaits CPCV-validated PF lower 5%-bound > 1.5 (queued).

---

## Close Queue

| PR# | Reason | Existing comment URL | Confidence |
|---|---|---|---|
| **#444** | Already merged via PR #497 (commit `b546feb1b6`); phantom-HALT fix in main since 2026-04-28 | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/444 (close-comment 2026-04-30 00:35 UTC) | **panel-confirmed** (Subagent A close-comment + session-wrap §2) |
| **#445** | Already merged via PR #497 (commit `b546feb1b6`); circuit-breaker stale-state fix in main since 2026-04-28 | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/445 (close-comment 2026-04-30 00:36 UTC) | **panel-confirmed** (same source as #444) |
| **#528** | REVERSES PR #519's intentional `last_kill_run` expiry; opposes action item #7 | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/528 (close-comment 2026-04-30 00:23 UTC) | **panel-confirmed** (PR #519 commit `b218cb7ba2` is explicit) |
| **#452** | Strict subset of #454 (7/7 files in #452 are in #454; #454 adds 5 more files) | (no close-comment yet — Subagent B refused to post without panel cite; this plan provides the cite) | **single-reviewer** (Subagent B file-list verification + this plan) |

**DO NOT CLOSE (panel claims overridden by Subagent B):**
- #447 / #448 / #449 — Subagent B file-list intersection (∅, ∅, 1/22) DISPROVES "3 forks of same review."
- #457 — Subagent B verified NOT superseded by #501/#503 (different layer: UI template vs pipeline generator).

---

## Amendment-Needed

| PR# | Issue | Author action required |
|---|---|---|
| **#513** | 2 wrong fact claims in `updates/2026-04-29-ueps-emit-verification.md` (wrong commit hash `617187571e` is dynamic_universe.json refresh, not UEPS — actual is `cbebf0b64b`; "first cron @ 17:06 UTC" wrong — actual first emit was `8633b7b2c5` at 05:40:15 UTC) | Edit MD file to correct both claims; comment landed at https://github.com/.../pull/513#issuecomment-4348664743 |
| **#451** | `smoke` CI test failing (3m25s); security-urgent ($_GET admin key leak fix) | Author investigates `tests/sports_betting_js_errors.spec.js` smoke regression; rebase + re-run |
| **#455** | No CI checks ran (mergeStateStatus UNKNOWN); JS-variant of what-if analyzer | Push trigger commit or workflow_dispatch; resolve any green/red |

---

## Cross-PR Conflict Matrix

For any file touched by 2+ PRs, the table below states the resolution strategy.

### A. `audit_trail/quality_gates.py` — **the 4-PR choke point**

| PR | Hunks (lines) | Function | Risk |
|---|---|---|---|
| #520 | 893 (active_non_crypto_forward_wr_floor), 3746-3807 (passes_active_gate), 4456-4473 (passes_smart_gate) | gate logic + WR floor table | LOWEST line numbers → merge FIRST |
| #446 | 3933-3947, 4080-4096 (passes_active_gate) | NC active-gate exemptions | hunks >100 lines from #520 → clean apply post-#520 |
| #507 | 105 (apply_sandbox_experiment_relabels), 3679 (passes_active_gate) | CPCV gate hookpoint | DRAFT, low-priority — defer |
| #529 | 645, 659 (regime helpers), 3813 (passes_active_gate) | mojibake/PEP8/kill-list-counter | merge LAST; absorb diffs from #520+#446 |

**Resolution:** strict serial merge in order **#520 → #446 → #529** (with #507 last as DRAFT). Hunks at distinct ranges; rebase conflicts should be auto-resolvable for #446 (lines 3933+ vs #520's 3807) but #529 line 3813 is ADJACENT to #520's 3790-3807 — manual rebase review required for #529 against post-#520 main.

### B. `audit_dashboard/template.html` — 5 PRs (cosmetic UI)

| PR | Scope | Risk |
|---|---|---|
| #446 | crypto tile + NC visibility | targeted; merge first |
| #450 | UNKNOWN → "NO SOURCE" / "DETECTING…" | UI text replace; defer |
| #452 | what-if early version | CLOSE as subset |
| #454 | what-if superset + tools | KEEP-OPEN |
| #457 | UNKNOWN normalization (UI layer per Subagent B) | HOLD until audit-data PRs settle |

**Resolution:** Merge #446 first (in main merge sequence). #450, #454, #457 all touch the same `template.html` for UNKNOWN-related UX; merge in next batch with author-rebase conflict resolution (likely manual).

### C. `audit_trail/dashboard_generator.py` — 3 PRs

| PR | Scope | Risk |
|---|---|---|
| #448 | 6 surgical fixes (audit + sports) | targeted |
| #449 | security/credentials sweep | partial overlap |
| #529 | mojibake/PEP8 polish | low-conflict cosmetic |

**Resolution:** Merge **#448 → #449 → #529**. The #448∩#449 overlap (1 file, `dashboard_generator.py`) needs author-rebase review on whichever lands second.

### D. `alpha_engine/strategy_blocklist.py` — 2 PRs

| PR | Scope | Risk |
|---|---|---|
| #461 | retire CRYPTO + corrections | HOLD (data-file pollution) |
| #529 | code-review polish | merge last |

**Resolution:** #461 is HOLD pending clean re-extraction. If #461 ships first, #529 must rebase on top. If #461 stays HOLD, #529 lands cleanly.

### E. `cross_aggregation/performance_alerts.py` — 3 PRs

| PR | Scope | Risk |
|---|---|---|
| #444 | phantom HALT fix | CLOSE (already in main) |
| #447 | independent perf-alerts hardening | merge after #444 close |
| #512 | mixed-unit XFAIL test | test-only, additive |

**Resolution:** Close #444 → merge #512 (test) → merge #447 (additional fix on the now-merged #497 base). #447 should not conflict because it touches different hunks from #444.

### F. `live-monitor/sports-betting.html` — 4 PRs (UI)

PR #450, #452, #454, #457 all touch this file. Same resolution as Section B (template.html): #452 closes, #454/#457/#450 defer to a separate sports-UI batch.

### G. `updates/index.html` — 5 PRs (always-edited)

PR #452 (CLOSE), #453, #454, #457, #529. Per CLAUDE.md "Never overwrite `updates/index.html`" — append-only. Last merge wins; expect manual conflict resolution on the 4 KEEP-OPEN/HOLD docs PRs.

---

## Cross-Checks Against Existing Reviewer Comments

This subsection lists the disagreements between this plan and existing reviewers, with rationale.

### #447 / #448 / #449 — "3 forks of same 48h review"
- **Panel #2 claim** (per session-wrap §2): all 3 are duplicate forks; close as redundant.
- **Subagent B finding** (`reports/PR_QUEUE_PROCESSING_2026_04_30.md` §1): file-list intersections are ∅, ∅, 1/22 — they are 3 INDEPENDENT reviews from Codex / Claude / Copilot SWE on different subsystems.
- **This plan takes Subagent B's side.** All 3 ship as READY (positions 4, 5, 7) with author-rebase resolution on the 1-file #448∩#449 overlap. Rationale: file evidence is stronger than panel claim; close without verification would discard 22 net new files of fixes.

### #457 — "Likely covered by #501/#503"
- **Panel #2 claim** (per session-wrap §2): superseded by already-merged #501/#503.
- **Subagent B finding** (§4): #501/#503 fix asset-class hint at PIPELINE layer (`dashboard_generator.py`); #457 fixes UI rendering at TEMPLATE layer (`template.html`). DIFFERENT LAYERS.
- **This plan takes Subagent B's side** (HOLD, not CLOSE). #457 stays open and is deferred to a separate UI-batch after the audit-data PRs settle.

### #531 — "REJECTED" verdict
- **Subagent A finding** (`reports/forex_resolver_ab_2026-02-01_2026-04-29.md` per session-wrap §3): tool itself is fine; the "REJECTED" verdict is artificial — caused by the panel-flagged-unachievable non-JPY PF ≥ 5 bar.
- **This plan ships #531 as READY** (the TOOL is green). Renegotiation of the threshold is a separate operator decision queued for the next session.

### #444 / #445 — "APPROVE then CLOSE"
- **Claude-bot APPROVE comment** posted 2026-04-30 00:32 UTC.
- **Close-comment** (also from eltonaguiar) posted 3-4 minutes later citing PR #497 already in main.
- **This plan takes the close-comment side** (CLOSE both). The APPROVE was issued before the duplicate detection.

### #528 — "APPROVE then CLOSE"
- **Claude-bot APPROVE comment** says "Critical regression fix" addressing PR #519 stale `last_kill_run`.
- **Close-comment** (eltonaguiar 2026-04-30 00:23 UTC) cites PR #519 commit `b218cb7ba2` explicitly: auto-expiry firing IS the intended behavior; this PR REVERSES that.
- **This plan takes the close-comment side** (CLOSE). #528 reverses an intentional kill-list expiry shipped in #519 and contradicts action item #7 from the operator queue.

---

## Operator Decision Items (require human action)

1. **#531 threshold renegotiation** — re-renegotiate non-JPY PF bar from 5.0 → 1.5; re-run replay; if ACCEPTED, ship `PNL_NOISE_THRESHOLD_BPS=5` env-flag (opt-in).
2. **#451 smoke CI failure** — diagnose + fix smoke regression; security-urgent.
3. **#476 / #477 rebase** — author rebases on post-#482/#495 main to clear stale `tests/test_hf_quality_gate_wire.py` red.
4. **#461 re-extract** — exclude data-file pollution (`trading_bot.log`, `trading_results.json`, `battle_test_results.json`); re-extract clean diff vs current main.
5. **#513 amend** — author corrects 2 wrong fact claims before merge.
6. **#449 manual CI dispatch** — workflow_dispatch security workflow to confirm green before merge.

---

## Panel Review Synthesis (2-AI direct panel, 2026-04-30)

The originally-dispatched 4-AI panel subagent failed with `403 permission_error` (auth token kicked from org). Substituted with direct API calls to **Cerebras `qwen-3-235b-a22b-instruct-2507`** (senior staff engineer role) and **Ollama `qwen3-coder:480b-cloud`** (release engineer role). Raw responses at `.tmp_research/panel_qwen.json` and `.tmp_research/panel_qwen3coder.txt`.

### Unanimous (2/2)

1. **#527 must be BLOCKED from activation** — qwen3.5cloud audit found that the description claims "5-stream consensus" weighting but `compute_size_scale()` uses `realized_vol_pct` only. Both panelists agree: either wire the consensus weighting before flip-on, or update the description. Since #527 is already merged on main but default-off, this is a **flip-on blocker**, not a merge blocker.

2. **#529 SPLIT IS MANDATORY before merge** — 50 files / 12,504 additions / 10,000 deletions including `KIMI_FEB172026/data/kimi_trading.db`, `genome/data/*.json` runtime artifacts, log files. Both panelists agree artifacts will bloat history and risk CI skew. Recommended split:
   - **Code-only PR (replacement for #529):** 3 surgical fixes (mojibake/PEP8/kill-list-counter) + corrigendum + wrap docs + Subagent B's PR_QUEUE_PROCESSING report + this integration plan
   - **Closed (don't ship):** all `KIMI_FEB172026/data/*`, `genome/data/*`, `crypto_signal_engine/data/*`, log files, `forward_stats.json`, etc.

3. **#454 CLOSE in favor of #457** — Cursor verified identical head SHA `93b25d60a74cc109e31c52eff7b51ad2153000b4`. Both panels agree #457 is the better-titled keep candidate. CLOSE COMMENT pending.

4. **DO NOT CLOSE #447/#448/#449 is the correct call** — Subagent B's file-intersection verification (∅, ∅, 1/22) is stronger evidence than Panel #2's "fork" claim.

### Additional risks flagged by Cerebras Qwen 235B (1/2 only)

5. **#529 line 3813 is ADJACENT to #520's hunk at 3790-3807** — manual rebase review required for #529 against post-#520 main. Plan addresses this implicitly but **needs to be made explicit** as an operator instruction.

6. **#476/#477 rebase must happen AFTER #520 + #446** — both touch `audit_trail/quality_gates.py` indirectly via test fixtures. Not flagged in original plan.

7. **#507 (DRAFT) must rebase AFTER #529, not before** — even though #507 stays in HOLD bucket, when the operator eventually picks it up, it needs to be the LAST of the 4-PR `quality_gates.py` choke point. Plan correctly orders this.

8. **No CI gating on file locks → out-of-band merge race risk** — if multiple PRs merge in parallel via auto-merge, the strict serial order this plan requires can be violated. Mitigation: operator merges one-at-a-time with manual CI verification between each step in the choke point sequence.

### Plan adjustments after panel review

**Adopted:**
- Add explicit "BLOCK #527 flip-on until consensus-wired" to Phase 5 (operator review).
- Promote "#529 split mandatory" from a recommendation to a hard requirement.
- Add explicit rebase guidance for #529 line 3813 ↔ #520 lines 3790-3807 adjacency.
- Document #476/#477 rebase ordering (after #520+#446, not before).
- Document the out-of-band merge race mitigation.

**No disagreements remain** — both panelists converged on the same 4 unanimous findings. Cerebras's 4 additional risks are all consistent with (not contradicting) the plan; they sharpen it rather than override it.

### Final adjusted operator action sequence

| Phase | Action | Notes |
|---|---|---|
| 0 | Close #454 (cite SHA dup with #457), close #452 (subset of #454) | Comments pending |
| 1 | Merge #511, #512 | Non-conflicting warmup |
| 2 | Merge #520 | First touch of `quality_gates.py` |
| 3 | Merge #448, #530, #531 | Distinct file scopes |
| 4 | Merge #446 | Second touch of `quality_gates.py` (clean apply post-#520) |
| 5 | Merge #449, #447 | Independent reviews per Subagent B |
| 6 | **SPLIT #529** into code-only + drop artifacts; merge code-only (rebase against post-#520+#446 main; manual review on line 3813 ↔ 3790-3807 adjacency) |
| 7 | Rebase #476, #477 (after #520+#446 lands); merge if green |
| 8 | Operator review: #531 threshold renegotiation; **#527 flip-on BLOCKED until consensus wired** |
| 9 | HOLD: #461 (re-extract clean), #457 (UI batch later), #450, #455, #456, #458, #473, #507 |

---

## Critical Findings This Round (NEW since prior session-wrap)

### A. Cursor's SHA-duplicate finding (#454 ≡ #457)

```
$ gh pr list --state open --json number,title,headRefOid --jq '.[] | select(.number==454 or .number==457) | {n: .number, sha: .headRefOid}'
{"n":457,"sha":"93b25d60a74cc109e31c52eff7b51ad2153000b4"}
{"n":454,"sha":"93b25d60a74cc109e31c52eff7b51ad2153000b4"}
```

Identical head SHA → literally the same commit pushed to two branch names. CLOSE one. Recommend close #454, keep #457.

### B. qwen3.5cloud's PR #527 consensus-wiring gap

Description claims "5-stream consensus" but [`alpha_engine/risk/vol_target.py:47-58`](alpha_engine/risk/vol_target.py#L47-L58) `compute_size_scale()` uses only `realized_vol_pct`:

```python
def compute_size_scale(realized_vol_pct: Optional[float]) -> float:
    if realized_vol_pct is None or realized_vol_pct <= 0:
        return 1.0
    target = get_vol_target_pct()  # default 30%
    raw_scale = target / realized_vol_pct
    return max(DEFAULT_MIN_SCALE, min(DEFAULT_MAX_SCALE, raw_scale))
```

No reference to `consensus_count`, `consensus_confidence`, or any cross-stream signal. **Block flip-on of `CRYPTO_VOL_TARGET_ENABLED=1` until consensus weighting is wired** — or update PR #527's description to clarify that consensus weighting is a future enhancement.

### C. Cursor's PR #529 split recommendation (verified)

```
$ gh pr view 529 --json changedFiles,additions,deletions
{"additions":12504,"changedFiles":50,"deletions":10000}
```

Includes runtime artifacts that should not be in a code-review PR:
- `KIMI_FEB172026/data/kimi_trading.db` (binary DB)
- `KIMI_FEB172026/logs/unified_forward_test.log`
- `genome/data/{ae,gp,mape,ensemble,momentum_scalp,mutation_lab}_active_picks.json`
- `cross_aggregation/data/consensus_outcomes.json`
- `crypto_signal_engine/data/{audit,price_cache,top_gainers}.json`
- `data/meme_scanner_active.json`
- `forward_stats.json`
- `STOCKS/competition/{regime_cache,forward_picks}.json`
- `battleground/data/{alpha_benchmark_report,audit_baseline,audit_impact_results}.json`
- many more JSON state files

**Action:** create a clean code-only branch with cherry-picked surgical commits, drop runtime artifacts, open replacement PR, close original #529.

---

*Synthesis complete. Final plan ready for operator review. Total reviewer streams synthesized: 8 (Cursor, gemma4-cloud, artiku348, Subagent B, qwen3.5cloud quant audit, Claude Opus per-PR, FreeBuff, my direct verification + 2-AI panel). Unanimous calls: 4. Adjustments adopted: 5. Disagreements remaining: 0.*

---

## Cross-validation against GitHub Copilot Cloud review (Stream #9, 2026-04-30)

A 9th reviewer stream landed: **GitHub Copilot Cloud session** (Claude Sonnet 4.6) at https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tasks/c816bd64-47b8-4ffe-bd0b-e926f11ee3be. Largely re-confirms our 8-stream synthesis. **2 new findings, 1 corrected claim, 1 re-opened operator decision.**

### NEW findings (verified, action taken)

1. **PR #455 body is malformed: literal `$(type pr_whatif_body.md)` (unexpanded shell)** — verified via `gh pr view 455 --json body`. Close-comment posted at [PR #455 comment](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/455#issuecomment-4349002899).

2. **PR #450 is strict subset of PR #457** — verified via `gh pr diff --name-only`:
   - #450 has 4 files; #457 has all 4 + 8 more (analysis tools + UNKNOWN normalization docs)
   - Distinct from Subagent B's "#457 NOT superseded by #501/#503" — different layer comparison
   - Close-comment posted at [PR #450 comment](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/450#issuecomment-4349003117)

### Corrected claim (Copilot wrong on this point)

3. **PR #461 "clean re-extraction" claim — VERIFIED FALSE.** Copilot said "Clean re-extraction, cherry-picked from contaminated branch." Verified via `gh pr diff 461 --name-only`:
   ```
   battle_test.log
   battle_test_results.json
   trading_bot.log
   trading_results.json
   ```
   All 4 polluted runtime artifacts are STILL in the PR (23 files total). **Our HOLD verdict stands** — needs another clean re-extraction excluding these data files.

### Re-opened operator decision

4. **PR #528 — Copilot upgraded to "Wave 0 emergency merge"** while our plan says CLOSE. Same facts, different reading:

   | Reading | Verdict | Rationale |
   |---|---|---|
   | Our plan + Subagent B + Panel #2 (3 streams) | **CLOSE** | PR #519 commit message explicit: "*the auto-expiry will fire on next run until tools/strategy_killer.py refreshes the list — this is the intended behaviour*" |
   | Copilot Cloud + original Copilot SWE author (2 streams) | **MERGE EMERGENCY** | The empty kill-set bypasses 540 entries; "active production risk" |

   **Both readings are defensible from the same facts.** The empty kill-set IS PR #519's intended behavior (force re-run of strategy_killer.py), AND it IS a temporary risk window if killer isn't run promptly.

   **Operator decision criteria:**
   - If the operator can run `python tools/strategy_killer.py` within the next dashboard cycle → **CLOSE #528** (proper fix)
   - If the operator cannot run it promptly → **MERGE #528 as a stopgap** (fake the timestamp to maintain protection until killer runs)

   Both close-comment (ours) and Copilot's "merge emergency" recommendation are now on PR #528. Operator decides.

### Wave-order differences (minor)

- **#520 vs #461 ordering:** Copilot puts #461 (Wave 2) before #520 (Wave 3); our plan keeps #520 first. With #461 still polluted (per #3 above), #461 is HOLD anyway — moot ordering.
- **#451 wave assignment:** Copilot puts #451 in Wave 1 (security urgent). Our plan flagged it in AMEND due to sports smoke CI failure. Recommend Copilot's wave 1 only AFTER the smoke regression is fixed.

### Net delta: 2 new close-recommendations posted; #461 HOLD reinforced; #528 disagreement formally captured.

---

## Next-PR Backlog — Items Ready For Conversion (Stream #10, GitHub Copilot Cloud, 2026-04-30)

A 10th reviewer pass searched for items that have implementation docs / branches / explicit "next PR" callouts but **no current open PR**. Results below; verified each via direct file/grep checks.

### Already verified (code or script EXISTS, just needs PR)

| # | Item | Priority | Effort | Verified |
|---|---|---|---|---|
| **1** | **vol_target.apply_to_pick → smart_picks_engine wire-up (Step 2 of #527)** | **P0** | ~0.5h | ✅ Module at `alpha_engine/risk/vol_target.py:61` (`apply_to_pick`); grep confirms ZERO wiring in `smart_picks_engine.py` |
| **2** | **Historical re-resolve of ~1,860 non-crypto picks (post #463)** | **P0** | ~1h | ✅ Script at `tools/re_resolve_historical_v2.py` (12.6KB, executable) — dry-run-default per design |

**⚠ Caveat on Item #1:** wiring `apply_to_pick()` as-is would make `CRYPTO_VOL_TARGET_ENABLED=1` functional, but the qwen3.5 audit (this plan §"Critical Findings This Round") flagged that the description claims "5-stream consensus" while the code uses `realized_vol_pct` only. Two options:
- (a) Wire as-is + leave default-off (operator-only flip) — gives the env-flag a real effect for cautious shadow testing
- (b) Add consensus weighting BEFORE wiring — closes the description/code mismatch
- Recommend (a) since the existing flag is already documented, AND defer (b) to a follow-up PR with explicit consensus-wiring scope

**Item #2 is zero-risk** (dry-run-only); recommend opening immediately.

### High priority — designed but no code yet

| # | Item | Priority | Effort | Source |
|---|---|---|---|---|
| 3 | Source-liveness watchdog (`tools/source_emission_audit.py`) | High | ~2h | `reports/silent_failure_investigation_2026_04_29.md` Fix 4 — measure source-file mtime + row count to prevent dashboard-layer-only false SEV-1s |
| 4 | macd_crossover LONG direction gate | High | ~1h | `reports/what_if_analysis.md` §1 — LONG WR 19.6% vs SHORT 46.2%; n≥30 per direction |
| 5 | quan_engine_scalp symbol allowlist (TRX + BTC only) | High | ~0.5h | `reports/what_if_analysis.md` §3 — TRX 50.8% / BTC 39.5%; KAS/HYPE/TAO sub-30%; verify quan_engine_scalp isn't already killed before scoping |
| 6 | st_rsi_momentum_confluence OP symbol block | High | ~0.5h | `reports/what_if_analysis.md` §4 — OP 17.9% WR / -56.57% PnL vs ARB 97.4% / AVAX 79.3% |

### Medium priority — deferred from prior PRs

| # | Item | Priority | Effort | Source |
|---|---|---|---|---|
| 7 | kimi_riseoftheclaw → crypto score-floor exempt sources | Med | ~0.5h | `reports/2026-04-27-whatif-4day-asset-class-hc-lessons.md` — PR #446 added NC-side exemptions; crypto-side missing |
| 8 | luxalgo_confluence SHORT-only gate on SOL/BTC | Med | ~1h | `reports/what_if_analysis.md` §2 — LONG WR 32.3% vs SHORT 43.5%; refinement to PR #523 unblock |
| 9 | Alphalens factor IC integration | Med | ~3h | `reports/hedge_fund_integration_2026_04_28.md` — explicitly deferred from PR #466; would answer whether any factor has real IC vs forward returns (elite_score r=-0.001 is known) |
| 10 | Monthly `strategy_killer.py` GHA cron | Low | ~0.5h | PR #528 investigation items — automates the kill cycle so `last_kill_run` stays within 21d window |

### Action sequence for next session

1. **First PR:** Item #2 (historical re-resolve dry-run) — zero-risk, surfaces real correction magnitude on FOREX/COMMODITY noise share
2. **Second PR:** Item #1 with default-off wiring + explicit "consensus weighting in follow-up" note (or defer until consensus is wired)
3. **Batch PR (small commits):** Items #4, #5, #6 — all touch `audit_trail/quality_gates.py` directional/symbol gates with clear data backing; can ship as one cohesive blocklist PR
4. **Batch PR:** Item #7 — small, 1-line addition
5. **Standalone PRs:** Items #3, #8, #9, #10 — distinct scopes

Total scope of backlog: ~9.5 hours of engineering across 10 items, 2 of which already have shippable code.

### Cross-check: items NOT on this backlog because already merged

- Outcome resolver v2 → PR #463 (merged)
- Goldmine kill → PR #514 + #487 (merged)
- rapid_fire × rsi_bounce → PR #516 (merged)
- rapid_fire × macd_rsi_confluence → PR #509 (merged)
- claude_gainer_st dashboard fix → PR #510 (merged)
- PEAD bootstrap → PR #499 (merged)
- Hedge fund integration (QuantStats + PyPortfolioOpt) → PR #466 (merged)

Total reviewer streams synthesized: **10**.

---

## Backlog Verification Results (2026-04-30 ship pass)

The orchestrator attempted to ship items #1, #2, #4, #5, #6, #8, #10. Direct verification against the codebase + live data revealed **5 of 10 items are moot** in their stated form. Items #1, #2 verified and **shipped**.

### Shipped

| # | Item | PR | Notes |
|---|---|---|---|
| 2 | Historical re-resolve dry-run | **PR #532** | 73 picks (NOT ~1,860 as design claimed); 10 status flips (13.7%); largest flip EURUSD `LOST(-0.9%)` → `WON(+2.3%)` |
| 1 | vol_target wire-up Step 2 | **PR #533** | Module wired into `smart_picks_engine` with default-off env flag; 6/6 tests; **qwen3.5 caveat (consensus-wiring gap) preserved** in PR body |

### Items found MOOT or stale

| # | Item | Verification | Status |
|---|---|---|---|
| 4 | macd_crossover LONG direction gate | `quality_gates.py:724` lists `"macd_crossover"` in `PERMANENTLY_KILLED_STRATEGIES` — already wholesale-killed | **REDUNDANT** |
| 5 | quan_engine_scalp TRX/BTC allowlist | `quality_gates.py:786` lists `"quan_engine_scalp"` in `PERMANENTLY_KILLED_STRATEGIES` (25% WR, 1793 trades, -352.88% PnL); KASUSDT separately on poison-symbol blocklist at line 988 | **REDUNDANT** |
| 6 | st_rsi_momentum_confluence OP block | `quality_gates.py:799` lists `"st_rsi_momentum_confluence"` in `PERMANENTLY_KILLED_STRATEGIES` ("WORST in entire system: 10% WR LONG, -296.5% PnL!") | **REDUNDANT** |
| 8 | luxalgo_confluence SHORT-only on SOL/BTC | Live `recent_closed` shows: LONG n=95 WR=45.3% sum_pnl=+20.97%; SHORT n=102 WR=52.0% sum_pnl=+42.33%. **Both directions PROFITABLE** — what_if's "LONG WR 32.3%" claim is stale | **STALE — DO NOT SHIP** |
| 10 | Monthly strategy_killer.py GHA cron | `tools/strategy_killer.py` does NOT exist | **NO PREREQUISITE** |

### Pattern observation

Stream #10's backlog had several claims that don't hold against current codebase:
- "~1,860 historical picks" (Item #2) → actual scope 73, **25× off**
- 3 strategies recommended for surgical gating (Items #4, #5, #6) are already wholesale-killed
- 1 strategy (Item #8) was active but its claimed bad-direction has since recovered to profitability
- 1 referenced script (Item #10) doesn't exist at the cited path

**Next-session implication:** treat all backlog items as "candidates needing verification" rather than ready-to-ship. Verify against current codebase + live data BEFORE opening any of items #3, #7, #9.

### Genuinely-actionable remaining items

| # | Item | Status |
|---|---|---|
| 3 | Source-liveness watchdog (`tools/source_emission_audit.py`) | NEW CODE — no existing artifact; design exists in `silent_failure_investigation_2026_04_29.md` Fix 4 |
| 7 | kimi_riseoftheclaw → crypto score-floor exempt | Need to verify NC-side exemption pattern (PR #446 / `_NC_SCORE_EXEMPT_SOURCES`) is genuinely missing on crypto side AND that kimi crypto picks are actually being filtered today |
| 9 | Alphalens factor IC integration | Larger scope (~3h); would answer whether any factor has real IC vs forward returns (elite_score r=-0.001 known) |

### Operator-decision: items #4, #5, #6 alternative path

Each of these strategies is currently wholesale-killed. The what_if recommendations were SURGICAL gates that would capture residual edge:

- **Path A (current state):** keep wholesale kill. Simple. Misses any surgical-edge residual.
- **Path B (un-kill + surgical gate):** remove from `PERMANENTLY_KILLED_STRATEGIES`, add the gate from this backlog. Captures residual edge. Higher operational risk.

Recommend Path A unless the residual edge is quantified against current cohorts (the what_if data is stale).


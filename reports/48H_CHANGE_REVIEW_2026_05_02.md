# 48-Hour Substantive Change Review — 2026-05-02

**Window:** 2026-04-30 18:00 UTC → 2026-05-02 18:00 UTC
**Branch reviewed:** `origin/main`
**Author:** Claude Opus 4.7 (1M context), 48h sweep
**Companion:** failed Kilo Code attempt (drowned in ~3,500 `[skip ci]` bot commits)

---

## Executive Summary

In the last 48 hours `main` absorbed ~3,500 commits, of which ~95% are auto-bot data refreshes; after filtering, ~50 are substantive. The dominant theme is a **hedge-fund-grade audit-uplift push** (PRs #626/#627/#633/#642/#654/#659/#660/#661/#664/#665/#669/#673) coupled with a **TradingAgents + UEPS + concept-taxonomy lane buildout** (PRs #543-#548, #582, #583, #592, #593, #595) and a sustained **events-homepage stabilization sprint** (PRs #591/#594/#598/#600/#602/#603/#604). The most important shipped items today are **PR #659 walkforward by_class card**, **PR #670 dashboard-data-loaded event-dispatch fix**, **PR #672 updates entry**, and **PR #679 Kimi B+ peer review**; **PR #680 (PF=99.90 sentinel + Guide Band fix) is still open** awaiting CI, and **PR #681 strategy_decay_guard is REQUEST_CHANGES** per `reports/KIMI_STRATEGY_DECAY_GUARD_REVIEW_2026_05_02.md`.

---

## Theme Groupings

### 1. Audit-dashboard / hedge-fund quality uplift (largest theme)

The "Cloud Agent roadmap" plus three peer-AI critiques (Kimi, Gemini, DeepSeek) drove an end-to-end audit-uplift package: foundation modules, walk-forward by-class, statistical-rigor wiring, after-cost gates, peer-review documentation.

- `80b7ac53466` PR #626 — foundation: 4 modules + 8 personas + 20 tests + real backtest
- `ccd628a8805` PR #627 — wire `transaction_cost_model` (default-OFF)
- `04657fb0a11` PR #642 — Phase 2 wire `statistical_rigor.audit_metrics_block` (default-OFF)
- `8eaaa41e09c` PR #633 — cherry-pick `deflated_sharpe_ratio` + Acklam `_norm_ppf` from Kimi
- `a692042656e` PR #654 — validation decorator + per-class walk-forward + risk-budget guards
- `8e642b9683d` PR #659 — surface walkforward by_class on dashboard (today, 07:36 UTC)
- `458dfdb793d` PR #670 — dispatch `dashboard-data-loaded` so #659 card actually paints (today, 08:48 UTC)
- `ee9bf4a2a2d` PR #680 — PF=99.90 sentinel + Guide Band listener fix (open, awaiting CI)
- `c92b3411746` PR #618 — UEPS comment leak + per-metric tooltips + ? Glossary panel
- `c58721c7c87` PR #646 — per-asset-class quality uplift roadmap
- `6c178218ae5` PR #657 — per-asset enhancement plan + SME/Quant/QA panel
- `66da3ad9fb5` PR #635 — asset-class strategy elaboration with glossary
- `20ca5d3571f` PR #647 — branch index for landable PR

### 2. Multi-AI peer-review documentation cluster

Cross-AI competitive review of the audit-uplift PRs (Kimi, Gemini, DeepSeek, Cursor cohort).

- `e6e08f2c7d9` PR #679 — Kimi v2 B+ conditional approval — all 5 cross-check fixes applied (today, 17:10 UTC)
- `5cfc304e83b` PR #667 — Kimi v2 attachments (53 files) + FOOLPROOF_ACTION_PLAN
- `9277027d356` PR #663 — persist Kimi 2026-05-02 ZIP attachments (47 files, docx + PNGs)
- `57dcb868f2b` PR #662 — three-AI gap synthesis on Kimi PR #658
- `33b756e579c` PR #613 — review Kimi HF strategy-improvement report v99.0
- `fe44f23cfcf` PR #631 — Kimi-vs-main verdict (KEEP-MAIN, 1 cherry-pick worth doing)
- `e3415ce3cad` PR #629 — persist Kimi hedge-fund-uplift PR work (verbatim)
- `74fb2fc0cd2` PR #628 — append Grok 6-step Master Audit framework + Phase 10+ deferrals
- `01051c2fd5d` PR #619 — cloud-agent batch review (4 tasks)
- `76e42e736eb` PR #672 — updates entry: 08:50 UTC multi-AI hedge-fund cycle (today)
- `f2e44fd5a95` PR #542 — empirical findings from first asset_class_edge_audit run

### 3. UEPS / TradingAgents / concept-taxonomy lane buildout (Apr 30 evening)

New POSITION-tier emitters and the concept registry that lets `/audit` filter by concept family.

- `f8c32ecbb29` PR #547 — UEPS `sync_to_active_picks()` output now persisted across runs
- `e130a83fd29` PR #548 — concept taxonomy Phase 1 (`assign_concept_fields` helper)
- `8e35dd82cc5` PR #566 — concept registry + Phase 2 feature flags (B4)
- `555d5dfb99e` PR #592 — concept-family filter dropdown on `/audit` (B6)
- `6d820e29bca` PR #545 — equity × POSITION lane (PEAD + bond credit-spread + TF classifier)
- `9b36a0f346f` PR #544 — TradingAgents stock-pick emitter (opt-in)
- `6235dfaf106` PR #543 — bull/bear LLM debate sidecar for UEPS (opt-in, default-off)
- `8c64c2a1dea` PR #582 — register `ueps_picks.json` in `JSON_PICK_SOURCES` (B28)
- `77fb7605bf1` PR #583 — reject TradingAgents picks with placeholder thesis (B24)
- `ea1cac4d059` PR #593 — harden TradingAgents prompt against identical metrics + dedup warning (B25)
- `b149653a0f5` PR #551 — fix TradingAgents production bugs flagged via PR #550 (B24/B25/B26)
- `ed8f73b6f3f` PR #550 — TradingAgents pick justification (NVDA/SOFI methodology + 3 bug flags)
- `9ee4470e02d` PR #595 — action-plan-v2 + B23 implementation
- `d8d65ed9434` PR #599 — UEPS long-horizon active-gate bypass (default-OFF)
- `c4f9ca3ea03` PR #630 — wire `penny_picks_latest.json` into `JSON_PICK_SOURCES` (B20)
- `14be9211594` PR #589 — ETF sector-rotation emitter + JSON_PICK_SOURCES registration (B11)
- `ef5f5854698` PR #579 — `empty_timeframe_lanes` in freshness watchdog (B3)
- `21164d2a6d8` PR #581 — source-liveness watchdog for source-file layer monitoring (B12)

### 4. Quality gates / risk controls / FORCE_CLOSED regression

Targeted P0 fixes after the asset-class audit exposed gate bypass and rounding bugs.

- `66e69b0993c` PR #617 — `normalize_exit_reason` FORCE_CLOSED regression from #606 (this is the parent fix for the current `fix-normalize-exit-reason-2026-05-02` branch)
- `6563b564464` PR #636 — defense-in-depth `CRYPTO_BANNED_SYMBOLS` at active-gate (Issue #622)
- `5d14cc71073` PR #632 — round drawdown to 2dp before threshold compare (Issue #623)
- `f611665f29d` PR #620 — pair-level exception carve-out for proven (strategy, symbol) pairs (B19)
- `5c9db236337` PR #567 — harden kill-switch check against `None` strategy values (B8)
- `faf881b7d58` PR #648 — remove Gate 7b from `hc_gates_python.py` to match JS (hc-parity)
- `00e8444ee78` PR #556 — Long-Term (1y+) timeframe dropdown alias (B1)
- `d555ddb9746` PR #554 — forward-only edge audit + per-strategy capacity report (B16)

### 5. Events homepage stabilization sprint

Multiple regressions on `findtorontoevents.ca` homepage filters fixed in tight succession.

- `7c26e1bc59c` — coalesce 4×16MB events.json fan-out causing mobile empty state
- `2cb5fb6acd6` — enable mod_deflate gzip for events.json (16MB → ~2-3MB)
- `1867b378155` — add 'Next Month' filter chip
- `2be4862a119` — This Month chip now actually shows today's events
- `74f0968b05f` PR #591 — Next Month + This Month chip filter regressions
- `5bfec85a33b` PR #594 — lower This Month loop-guard threshold + auto re-run
- `f881f3f23c9` PR #598 — multi-day event overlap (cloud-agent + recurring fallback)
- `b03ff5a5c26` PR #600 — React #418 hydration gate + 48px mobile tap targets + This Week audit
- `1a0e711205d` PR #602 — gate static-promo injection on React hydration too
- `13e4dfdf750` PR #603 — restore React #418 allowlist + `.fixme` dedicated test
- `148dfee685f` PR #604 — show actual JUNE date on Next Month cards (visible badge)
- `32c2df019d8` PR #637 — events.json data quality (dedupe ids + svg placeholders)

### 6. CI / infra / loop hygiene

- `349b39ef450` PR #645 — register `network` marker + TCP-reachability probe (unblocks PR CI cascade)
- `38e9e4353b9` PR #653 — make `test_usdjpy_buy_allowed` deterministic (was time-of-day-flaky)
- `78b1695c814` PR #640 — schema adapter + freshness guard for `cot_signals.json` (B7 prereq)
- `10e5f6045c6` PR #605 — disable alpha-suite-daily-refresh (PHP endpoints 404) + fix CI tests
- `2f0ad713ff5` PR #570 — B28 root-cause + resolution + empirical /audit perf review
- `3fe1a73b6db` — loop iteration findings (V1/V2 diag, B23, B7 CFTC-403, hc-parity)
- `49412efd248` — mark B14 PR #673; update B6/B11/B15/B16/B17 status
- `076dbd7d1c1` PR #585 — escalation: catalog 20 duplicate PRs, update queue status
- `9fea35a43c4` — mark V3/V4/V6 verified; B28 PR #573 + V1/V2/V5/V7 status
- `e139e98e1b9` — queue update: B16 PRs #552/#554, B1 PR #556 open

### 7. MIMO / decay / signal-source diagnostics

- `e0d0b11003b` PR #650 — empirical strategy decay audit, H1/H2 chrono-split (MIMO P0)
- `52811605839` PR #651 — empirical signal-source distribution audit (MIMO P1)
- `32e9db165d1` PR #649 — persist MIMO structural-investigation follow-up (Layer 1-5, P0/P1/P2/P3)
- `bcab1e52da5` PR #607 — tier performance audit + suggested fixes
- `95f54b8990f` PR #612 — 2026-05-02 audit-report enhancements review
- `958fd40bb34` PR #641 — action-items status snapshot 2026-05-01
- `388349c386b` PR #624 — peer broadcast 2026-05-02 04:00Z

### 8. Background docs / records

- `549` 2026-04-30 session record + remaining action-items queue
- `2d46b0e052b` peer progress check report 2026-05-02 (watchdog session)

---

## Per-Substantive-Commit Table

| SHA | PR# | What | Risk | Status | Follow-up |
|---|---|---|---|---|---|
| ee9bf4a2a2d | #680 | PF=99.90 sentinel + Guide Band listener fix | Low | OPEN (CI) | merge once checks green |
| e6e08f2c7d9 | #679 | Kimi peer review v2 (B+) — 5 cross-checks applied | Low | MERGED 17:10Z | none |
| 458dfdb793d | #670 | Dispatch `dashboard-data-loaded` event so by_class card paints | Low | MERGED 08:48Z | none |
| 8e642b9683d | #659 | Surface walkforward by_class on dashboard | Med | MERGED 07:36Z | watch for sentinel rows like #680 elsewhere |
| 76e42e736eb | #672 | Updates entry: multi-AI hedge-fund cycle | Low | MERGED 08:58Z | none |
| 5cfc304e83b | #667 | Kimi v2 attachments (53 files) + FOOLPROOF plan | Low | MERGED | none (docs) |
| 9277027d356 | #663 | Persist Kimi 2026-05-02 ZIP (47 files) | Low | MERGED | none |
| 57dcb868f2b | #662 | Three-AI gap synthesis Kimi PR #658 | Low | MERGED | feeds gating decision on #658 |
| c58721c7c87 | #646 | Hedge-fund quality uplift roadmap | Low | MERGED | track per-asset KPIs |
| 6c178218ae5 | #657 | Per-asset enhancement plan + panel | Low | MERGED | none |
| 20ca5d3571f | #647 | Branch index for landable PR | Low | MERGED | none |
| 04657fb0a11 | #642 | Wire `statistical_rigor.audit_metrics_block` (default-OFF) | Low | MERGED | flip flag in shadow then prod |
| ccd628a8805 | #627 | Wire `transaction_cost_model` (default-OFF) | Low | MERGED | same |
| 80b7ac53466 | #626 | Foundation: 4 modules + 8 personas + 20 tests | Low | MERGED | wire-up gates per Goal #1 |
| 8eaaa41e09c | #633 | Cherry-pick `deflated_sharpe_ratio` + Acklam `_norm_ppf` | Low | MERGED | wire into reporting |
| a692042656e | #654 | Validation decorator + per-class walk-forward + risk-budget guards | Med | MERGED | confirm capacity caps respected at exec |
| c4f9ca3ea03 | #630 | Wire `penny_picks_latest.json` into `JSON_PICK_SOURCES` (B20) | Low | MERGED | none |
| c92b3411746 | #618 | UEPS comment leak + per-metric tooltips + Glossary | Low | MERGED | none |
| 66e69b0993c | #617 | `normalize_exit_reason` FORCE_CLOSED regression from #606 | High | MERGED | the very branch I came from continues this work |
| 6563b564464 | #636 | Defense-in-depth `CRYPTO_BANNED_SYMBOLS` at active-gate | High | MERGED | none |
| 5d14cc71073 | #632 | Round drawdown to 2dp before threshold (Issue #623) | Med | MERGED | none |
| f611665f29d | #620 | Pair-level exception carve-out for proven pairs (B19) | Med | MERGED | watch carve-out abuse |
| faf881b7d58 | #648 | Remove Gate 7b from `hc_gates_python.py` to match JS | Med | MERGED | parity check in CI? |
| 5c9db236337 | #567 | Harden kill-switch check against `None` (B8) | Low | MERGED | none |
| 78b1695c814 | #640 | `cot_signals.json` schema adapter + freshness guard (B7) | Low | MERGED | CFTC-403 still pending |
| 349b39ef450 | #645 | Register `network` marker + TCP probe (CI unblock) | Low | MERGED | none |
| 38e9e4353b9 | #653 | Make `test_usdjpy_buy_allowed` deterministic | Low | MERGED | none |
| 10e5f6045c6 | #605 | Disable alpha-suite-daily-refresh (404 endpoints) + CI tests | Low | MERGED | re-enable when endpoints return |
| f8c32ecbb29 | #547 | UEPS `sync_to_active_picks()` persistence | Med | MERGED | verify across multi-process runs |
| e130a83fd29 | #548 | Concept taxonomy Phase 1 helper | Low | MERGED | needed by #566/#592 |
| 8e35dd82cc5 | #566 | Concept registry + Phase 2 feature flags (B4) | Low | MERGED | flip flags after shadow |
| 555d5dfb99e | #592 | Concept-family filter dropdown on `/audit` (B6) | Low | MERGED | none |
| 6d820e29bca | #545 | Equity × POSITION lane (PEAD + bond credit-spread + TF) | Med | MERGED | acceptance criteria per `reports/PER_ASSET_AUDIT_QUALITY_ENHANCEMENTS_2026_05_02.md` |
| 9b36a0f346f | #544 | TradingAgents stock-pick emitter (opt-in) | Low | MERGED | wire-rule applies — has wiring plan via #582 |
| 6235dfaf106 | #543 | Bull/bear LLM debate sidecar for UEPS (default-off) | Low | MERGED | wire-up plan referenced |
| 8c64c2a1dea | #582 | Register `ueps_picks.json` in `JSON_PICK_SOURCES` (B28) | Low | MERGED | none |
| 77fb7605bf1 | #583 | Reject TradingAgents placeholder thesis (B24) | Med | MERGED | none |
| ea1cac4d059 | #593 | Harden TradingAgents prompt + dedup warning (B25) | Low | MERGED | none |
| b149653a0f5 | #551 | TradingAgents production bug fixes (B24/B25/B26) | Med | MERGED | none |
| ed8f73b6f3f | #550 | TradingAgents pick justification + 3 bug flags | Low | MERGED | followed by #551 |
| d8d65ed9434 | #599 | UEPS long-horizon active-gate bypass (default-OFF) | Low | MERGED | flip-flag plan |
| 14be9211594 | #589 | ETF sector-rotation emitter + JSON_PICK_SOURCES (B11) | Low | MERGED | PR #674 still open for full wire |
| ef5f5854698 | #579 | `empty_timeframe_lanes` in freshness watchdog (B3) | Low | MERGED | none |
| 21164d2a6d8 | #581 | Source-liveness watchdog (B12) | Low | MERGED | none |
| 9ee4470e02d | #595 | Action-plan-v2 + B23 implementation | Low | MERGED | none |
| 7c26e1bc59c | – | Coalesce 4×16MB events.json fan-out (mobile empty state) | High | MERGED | watch CDN cache invalidation |
| 2cb5fb6acd6 | – | Enable mod_deflate gzip for events.json | Low | MERGED | none |
| 1867b378155 | – | Add 'Next Month' filter chip | Low | MERGED | none |
| 2be4862a119 | – | This Month chip shows today's events | Low | MERGED | none |
| 74f0968b05f | #591 | Next Month + This Month chip filter regressions | Low | MERGED | none |
| 5bfec85a33b | #594 | Lower This Month loop-guard threshold + auto re-run | Low | MERGED | none |
| f881f3f23c9 | #598 | Multi-day event overlap (cloud-agent + recurring fallback) | Med | MERGED | none |
| b03ff5a5c26 | #600 | React #418 hydration gate + 48px tap targets | Med | MERGED | none |
| 1a0e711205d | #602 | Gate static-promo on React hydration too | Med | MERGED | none |
| 13e4dfdf750 | #603 | Restore React #418 allowlist + `.fixme` test | Low | MERGED | un-fixme test |
| 148dfee685f | #604 | Show actual JUNE date on Next Month cards | Low | MERGED | none |
| 32c2df019d8 | #637 | events.json dedupe ids + svg placeholders | Low | MERGED | none |
| e0d0b11003b | #650 | Empirical strategy decay audit (MIMO P0) | Low | MERGED | feeds #681 design |
| 52811605839 | #651 | Empirical signal-source distribution audit (MIMO P1) | Low | MERGED | none |
| 32e9db165d1 | #649 | MIMO structural-investigation follow-up persist | Low | MERGED | none |
| bcab1e52da5 | #607 | Tier performance audit + suggested fixes | Low | MERGED | feeds Kimi #660 review |
| 95f54b8990f | #612 | 2026-05-02 audit-report enhancements review | Low | MERGED | none |
| 33b756e579c | #613 | Review Kimi HF strategy-improvement v99.0 | Low | MERGED | none |
| fe44f23cfcf | #631 | Kimi-vs-main verdict (KEEP-MAIN, 1 cherry-pick) | Low | MERGED | cherry-pick landed via #633 |
| e3415ce3cad | #629 | Persist Kimi hedge-fund-uplift PR work | Low | MERGED | none |
| 74fb2fc0cd2 | #628 | Append Grok 6-step Master Audit + Phase 10+ deferrals | Low | MERGED | none |
| 01051c2fd5d | #619 | Cloud-agent batch review (4 tasks) | Low | MERGED | none |
| f2e44fd5a95 | #542 | Empirical findings from first asset_class_edge_audit | Low | MERGED | none |
| 388349c386b | #624 | Peer broadcast 2026-05-02 04:00Z | Low | MERGED | none |
| 958fd40bb34 | #641 | Action-items status snapshot 2026-05-01 | Low | MERGED | none |
| 549 | – | 2026-04-30 session record + remaining action-items queue | Low | MERGED | none |
| 076dbd7d1c1 | #585 | Escalation: catalog 20 duplicate PRs | Low | MERGED | dedup PRs |
| 2f0ad713ff5 | #570 | B28 root-cause + empirical /audit perf review | Low | MERGED | none |
| – | #681 | Strategy_decay_guard for 11 failing strategies | High | OPEN — REQUEST_CHANGES | Apply Kimi review fixes per `reports/KIMI_STRATEGY_DECAY_GUARD_REVIEW_2026_05_02.md` before merge |

---

## What to fix next (prioritized 5-item list)

1. **Land PR #680 PF-sentinel + Guide-Band fix** — fix is small and well-scoped, regressions caught by Playwright; only blocked on CI green. Risk of leaving it open: dashboard keeps showing PF=99.90 on Futures and Guide Band stays empty, which undermines the trust-tuning work that just shipped (#659/#670). Cite `reports/HEDGE_FUND_MASTER_COORDINATION_2026_05_02.md`.
2. **Apply REQUEST_CHANGES feedback to PR #681** — Kimi's review (`reports/KIMI_STRATEGY_DECAY_GUARD_REVIEW_2026_05_02.md`) called out hard-coded thresholds, missing audit trail, and risk of compounding kill-without-replacement (memory: `project_futures_kill_without_replacement.md`). Address before merge — strategy-decay tooling is high-blast-radius.
3. **Wire-up audit-foundation flags** — PRs #626/#627/#642/#633 all landed default-OFF. Per `CLAUDE.md` Wire-Up Rule, default-OFF only counts as "wired" with a wiring plan and target PR. Schedule shadow-flip for `transaction_cost_model` and `audit_metrics_block` this week so the foundation actually moves picks. Source: `reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md`.
4. **Resolve PR #658 (Kimi hedge-fund quality enhancement) gate** — three-AI synthesis (#662) plus Kimi-vs-main verdict (#631) said KEEP-MAIN with a 1-PR cherry-pick already landed (#633). The remaining PR #658 should either be closed or surgically reduced to the deltas not yet absorbed. Leaving 53MB of attachments + an "open" mega-PR creates review noise.
5. **Re-enable alpha-suite-daily-refresh** (#605 disabled due to 404 PHP endpoints). Tracking issue should confirm the upstream endpoints; leaving it permanently disabled silently degrades the daily refresh contract that downstream Goal #1 audit cards depend on.

---

## Supporting reports referenced

- `reports/HEDGE_FUND_MASTER_COORDINATION_2026_05_02.md` — master coord (merged via PR #666)
- `reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md` — per-asset roadmap (PR #646)
- `reports/PER_ASSET_AUDIT_QUALITY_ENHANCEMENTS_2026_05_02.md` — enhancement plan (PR #657)
- `reports/ASSET_CLASS_STRATEGY_ELABORATION_2026_05_02.md` — glossary + per-class evidence (PR #635)
- `reports/KIMI_STRATEGY_DECAY_GUARD_REVIEW_2026_05_02.md` — REQUEST_CHANGES review of PR #681
- `reports/DEEPSEEK_STRATEGY_DECAY_GUARD_REVIEW_2026_05_02.md` — second-opinion on PR #681
- `reports/KIMI_PR658_THREE_AI_GAP_SYNTHESIS_2026_05_02.md` — Kimi #658 vs main (PR #662)
- `reports/KIMI_VS_MAIN_COMPARISON_2026_05_02.md` — KEEP-MAIN verdict (PR #631)
- `reports/HEDGE_FUND_ENHANCEMENT_PR_2026_05_02_CODEBASE_REVIEW.md` — codebase review of #658
- `reports/SIGNAL_SOURCE_DISTRIBUTION_AUDIT_2026_05_02.md` — signal-source distribution (PR #651)
- `reports/STRATEGY_DECAY_AUDIT_2026_05_02.md` — H1/H2 chrono-split (PR #650)
- `reports/MIMO_STRUCTURAL_INVESTIGATION_FOLLOWUP_2026_05_02.md` — MIMO follow-up (PR #649)
- `updates/2026-04-30-session-record.md` (via #549)
- `updates/2026-05-02-hedge-fund-package-peer-review.md` (via PR #679)

> Two reports referenced in the original review brief — `reports/PLAYWRIGHT_TILE_VALIDATION_2026_05_02.md`, `reports/UX_REDESIGN_FEASIBILITY_2026_05_02.md`, `reports/PER_ASSET_PERFORMANCE_AUDIT_2026_05_02_LIVE.md`, `reports/EDGE_SURFACE_WIRING_AUDIT_2026_05_02.md`, `reports/ML_HEALTH_CHECK_2026_05_02.md` — were **not found** on `origin/main` at review time. They may live on un-merged feature branches or in other agent worktrees; the substantive PR #680 commit message confirms Playwright caught the PF=99.90 bug, so the validation work happened even if the report file isn't on main yet.

---

## Methodology notes

- 48h window: `git log --since="48 hours ago" --no-merges --oneline` returned ~3,500 commits.
- Filter regex eliminated all `[skip ci]`, `Auto: Market beating cycle`, `scheduled: pick check`, scanner/tracker/forward/predict/meme/QuantumFusion/momentum/copy-trader/elite_score/quan_engine/regime-terminal/sport-betting/scan/etc cycle commits, leaving ~50 substantive ones.
- Each remaining commit was cross-checked against `gh pr list` for merge status and against `reports/` for evidence.
- Branch hygiene: this review was created from a clean checkout of `origin/main` with only the new MD added; no other files touched (CLAUDE.md branch-hygiene mandate).


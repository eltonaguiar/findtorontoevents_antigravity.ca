# 2-Month MD Sweep (2026-04-10 → 2026-06-07) — Incidents-Ready Open Items

**Date:** 2026-06-10 · **Author:** Claude (read-only sweep agent)
**Scope:** every unique `.md`/`.MD` modified since 2026-04-10, deduped; findings classified DONE / REFUTED / OPEN with code-level verification.
**Explicitly excluded:** June-8..10 items (already covered by the 72h sweep in `reports/MASTER_PROGRESS_2026-06-10.md` tick 04:25 — do-not-relitigate list lives there).

## Dedup stats (Step 1)

| Stage | Count |
|---|---|
| `.md`/`.MD` files with mtime ≥ 2026-04-10 (excl. `.git`) | **41,512** |
| After vendor-dir filter (`node_modules`, `.venv`, `site-packages`) | 41,011 |
| **Unique by content hash (shortest path canonical)** | **5,143** |
| Duplicates suppressed (≈all `.worktrees/*` copies; 35,731 md files live under `.worktrees/`) | 35,868 |
| Canonical at repo root vs worktree-only uniques | 5,099 / 44 |

Tooling: `tools/dedup_md_files.py` (per `/dedup-md-review` skill). A prior sweep (`reports/2026-05-25_md_sweep_action_items.md`, 193 files, 47 items) was found and **re-verified item-by-item** rather than re-extracted.

---

## SECTION A — INCIDENTS-READY: genuinely OPEN items

Ranked. ★ = **not yet tracked** in `audit_dashboard/data/incidents_enhancements_feed.json` (checked against the 2026-06-09 feed, 313 open-ish items). Untagged = already in the feed; this sweep re-confirmed it is still real.

### A1. ★ P1 — `shadow_pilot_tracker` still counts EXPIRED rows as resolved (false paper-trade PASS)
- **Source:** `reports/2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md` fix #3: "shadow_pilot_verdicts.json … shows FUTURES `pf_ok:true` on 378 expired rows — a false paper-trade pass that could graduate a zombie class."
- **Current state (verified):** `tools/shadow_pilot_tracker.py:139` still includes `'EXPIRED'` in the resolved-status set. No patch landed.
- **Action:** exclude EXPIRED (or gate on geometry-touch) from pilot PF/WR math; regenerate `shadow_pilot_verdicts.json`.

### A2. ★ P1 — Promotion gate frozen: report 2+ months stale, no regen cron, structurally unpassable (§15 Trap #4 / PR #364 bug #10)
- **Source:** `TESTING_PROTOCOL.MD` §17 bug #10 (2026-05-31): coverage 2.3% (5/216), Gini 0.71 vs 0.40 threshold, 0 promotions in 8 weeks.
- **Current state (verified):** `alpha_engine/data/promotion_gate_report.json` `generated_at = 2026-04-02` — never regenerated. No workflow runs it.
- **Action:** regen cron + recalibrate Gini threshold (or formally retire the gate in favor of the money-ready verdict chain so there is ONE promotion path).

### A3. ★ P1 — Tooling test rot got WORSE: 50 failing tests in two committed test files
- **Source:** `reports/2026-05-25_md_sweep_action_items.md` P1 #5/#6 (then: 2 + 1 failures).
- **Current state (verified, pytest run 2026-06-10):** `tools/test_ghost_cleanup.py` **34 failed**/30 passed (`TypeError: run_cleanup() got multiple values for argument 'execute'` — tool signature changed, tests never updated); `tools/test_resolver_health.py` **16 failed**/24 passed.
- **Why it matters:** this is a concrete, fixable slice of feed incident #117 "CI Tests red on every push (28 fails): stale assertions" and of the chronic CI-Tests timeout (June-10 handoff #7).
- **Action:** update fixtures to current signatures or delete the rotted suites; fold into the CI-suite split task.

### A4. ★ P2 — TESTING_PROTOCOL §18 stubs were never operationalized although ALL 6 source reports landed
- **Source:** `TESTING_PROTOCOL.MD` §18 ("STUBS — wkh9une1h wave pending").
- **Current state (verified):** all six `reports/peer_claude-topic_*_2026-05-31.md` (execution-costs, capacity-kelly, correlation-gate, regime-detection, live-paper-divergence, rr-floor) exist in `reports/`, but §18 still says "pending" and none of the proposed binding gates (R:R floor, 15pp live-paper drift demotion, HRP correlation gate, regime envelope kill-switch) was extracted into operational gates.
- **Action:** doc-integration pass + decide which of the 6 become binding (R:R floor and live-paper divergence are the cheapest and most aligned with the post-PR2 honest ledger).

### A5. P1 — FOREX posture is self-contradictory (re-enable vs freeze vs allowlist)
- **Source docs:** `updates/2026-06-05-forex-production-unblock-carry-g10.md` + `alpha_engine/config.py:324-329` (FOREX re-enabled 2026-06-05 on `forex_carry_g10` extended backtest PF 1.593 / WR 60.4% / n=197).
- **Conflicts (all live):** feed incident #77 "FREEZE FOREX/COMMODITY/FUTURES — contamination too high" is OPEN; feed FOREX#1 "forex_carry.py … NOT in allowlist" is OPEN; policy-clean FOREX FAILs (PF 0.55, CLAUDE.md); honest intrabar FOREX is only n=88 (pre-verdict).
- **Action:** one decision record: either re-verify the carry-g10 unlock condition under the entry-anchored resolver and close #77/FOREX#1, or flip `FOREX_HARD_DISABLE` back on until the intrabar FOREX verdict lands at n≥100. Do not let the env default and the incident feed disagree.

### A6. ★ P2 — M-008 COT MATCH gate never wired: `tools/verify_system_pf.py` has zero callers
- **Source:** `reports/90day_gap_analysis_2026-05-15.md` + `reports/2026-05-27_remaining_items_from_90day_plans.md` (M-008: "shipped but not called in `passes_active_gate`; one-line wire").
- **Current state (verified):** `grep -rln verify_system_pf alpha_engine/ audit_trail/ tools/` → only the tool itself. 13 months of plan docs cite it as a one-line wire.
- **Caveat:** COMMODITY is currently FAIL-tier and COT sources are largely blocked, so impact is low *today* — but it should be wired (or the M-item formally closed as superseded by the hard blocks) before any COT source is ever un-blocked.

### A7. ★ P2 — Report-freshness layer still has no CI hook; registered reports go RED silently
- **Source:** `updates/2026-05-24-report-freshness-framework.md` follow-ups + May-25 sweep P3 #12 ("97 RED reports repo-wide is unmonitored").
- **Current state (verified):** no workflow references `report_freshness` (`grep -rln report_freshness .github/workflows/` → empty). The promotion-gate staleness in A2 and the FDR staleness in A8 are exactly the failure mode this tool exists to catch.
- **Action:** one scheduled job: `report_freshness_tracker --quiet` + alert on registered-set RED.

### A8. P1 — FDR analysis still stale since 2026-04-06 (feed #99) — adopted June-10 but NOT completed
- **Current state (verified):** no FDR re-run artifacts in `reports/` or `audit_dashboard/data/`; `tools/fdr_control.py` exists but `alpha_engine/edge_stability_harness.py` has no FDR/Benjamini integration. `MASTER_PROGRESS_2026-06-10.md` lists "FDR re-run" in NEXT lists at three ticks without a completion entry.
- **Action:** run it on the post-PR2 + post-quarantine cohort (same cohort PBO was regenerated on, 1.0 → 0.822).

### A9. ★ P2 — June-6 academic-sleeve promotions now UNBLOCKED but unwired (their stated blocker has landed)
- **Source:** `reports/2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md` fix #5 — "do not wire until fixes 1–3 land." Fixes 1–3 (intrabar resolver PR2, per-class TP/SL caps `4470fbf0ed`, backfill quarantine) ARE live as of 2026-06-10.
- **Current state (verified):** `tsmom_volscaled` wired as shadow (`42e403e79d`) ✅; but `alpha_engine/residual_momentum.py` (EQUITY), `commodity_basis_carry.py`, and `bond_strategy_harness.py` (carry+roll-down, fully built incl. BH-FDR + walk-forward) still have **zero production/scanner callers**.
- **Companion (fix #6, also untouched):** ETF/BOND exits are still few-day timers, not monthly-rebalance/signal-flip — Faber/GEM style sleeves remain structurally guaranteed to TIME_EXIT.
- **Action:** wire as `forward_test_only` shadow sleeves (same lane as TSMOM) + re-wire ETF/BOND exits to ≥20-trading-day min-hold or signal-flip. Honors the Wire-Up Rule.

### A10. P2 — `category` taxonomy case-mess still in canonical DB (feed #88) + FUTURES zombie-tile decision still unmade (feed FUTURES#3)
- **Current state (verified):** no normalization migration found; downstream tools (e.g., `shadow_pilot_tracker.py:146-150`) carry private re-mapping dicts instead — divergence risk. FUTURES merge/retire recommendation has been open since the 2026-05-15 plans.
- **Action:** one backfill UPDATE normalizing `stock/stocks/penny/pennystock/meme` variants + a single shared mapping helper; record the FUTURES tile decision.

### A11. ★ P3 — XLI (and sector-ETF) `trading_picks.category` backfill never verified
- **Source:** May-25 sweep A6/P0 #2: XLI fix patched JSON files only; 7 DB rows had `category=''`.
- **Current state:** no backfill commit found; never re-verified. One UPDATE + re-check. (Partially overlaps the June-10 "82 blank asset_class verified applied" — that manifest may or may not have included these; verify before acting.)

### A12. ★ P3 — `audit_won_picks.py --correct` never run (WON + negative-pnl contradiction rows)
- **Current state:** the tool's `asset_class`→`category` bug IS fixed (`tools/audit_won_picks.py:54`), but no evidence the corrective pass ran. Largely overtaken by the June-10 sign-flip purge + Sign-Coherence Gate (GREEN at 0-baseline), so: run the tool once read-only; if 0 rows, close the May item.

### A13. ★ P3 — Mutation engine has been detection-only for ~10 weeks (§15 Trap #5 / PR #364 bug #11)
- **Current state (verified):** `alpha_engine/production_scanner.py:4506` — `MUTATION_ENGINE_ENABLED` default `"0"` since 2026-04; no workflow calls `generate_mutations()`.
- **Note:** keeping it OFF may be the *right* posture during the honest-measurement rebuild — but it should be a recorded decision, not drift. Either schedule shadow-only mutations or formally close Trap #5 as "OFF by policy until a class passes T2."

### A14. ★ P3 — Worktree explosion only partially reaped
- **Source:** `reports/peer_claude-WORKTREE_90DAY_EXPLOSION_DEDUPE_2026-05-31.md` (29 worktrees, ~12 GB, 695 orphan plan copies).
- **Current state (verified):** 12 registered worktrees remain; `.claude/worktrees/` gone, but `.worktrees/` = **3.1 GB** and contributes ~35.7K of the 41.5K duplicate `.md` files this sweep had to dedup. Safe sequence documented in that report (`git worktree remove --force` per dir, then `prune`). Operator action.

### A15. ★ P3 — Dated checkpoints coming due (nobody owns them)
- **2026-06-14:** `pead_equity` shadow review gate (history now durable via `pead_shadow_history.jsonl`; feed STOCKS#1 should be re-statused then).
- **2026-06-17:** shadow-mode gates 30-day review (P0-A conf-cap / P0-B BUY-block / P0-C ml_score floor from `reports/expert_feedback_action_plan_2026-05-17.md`; deferred in `updates/2026-06-05-remaining-action-items-audit.md`).
- **~2026-06-24+:** rsi5070 n≥150 re-test; COMMODITY/FOREX first honest n≥100 verdicts (June-10 handoff #2/#4).
- **3–6 weeks out:** re-run the edge-hunt sweep per memory "clean cohort = 6-day snapshot" (earliest ~2026-06-30).

### A16. ★ P3 — Untriaged DAILY_IDEAS backlog (never swarm-scored)
From the 2026-05-13 brainstorm: only IDEA-A (approved w/ scope cut), IDEA-E (DEFER 4.5/10), IDEA-H (7.5/10 → Ph1 SHIPPED) were formally analyzed. **Never triaged:** IDEA-C (no-load mutual funds), IDEA-D (options flow/UOA), IDEA-F (China/HK stat-arb), IDEA-G (gas-price correlation), IDEA-I (weather→ag), IDEA-J (mining capex), IDEA-K (weddings/diamonds), IDEA-L (alt-data misc). IDEA-H **Phase 2** (election/geopolitical→sector ETF) + the lead/lag analyzer are also unbuilt. All are post-edge-restoration backlog — log, don't build.

### A17. ★ P3 — FIRING11 baby-strategy candidates never pre-registered (M-107)
- **Source:** `reports/continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md` — 5 candidates (multi_timeframe_ema_cloud PF 6.95 n=29; moving_average_slope_momentum n=94; rsi_pairs_arbitrage n=130; inverse_goldmine_stocks; copper_platinum_cot_momentum).
- **Current state (verified):** none appear in `reports/hypothesis_registry.json` (71 entries). Their meta.json backtests are pre-honest-resolver (2026-03/04 yfinance) so treat all cited PFs as suspect; if pursued, M-107 pre-reg + the n≥500/Wilson-LB floors from TESTING_PROTOCOL §17.D apply.

### A18. ★ P3 — Misc verified-open leftovers (single-line each)
- **M-067 NULL `elite_score` (~41% of ACTIVE picks)** — PR #364 bug #2; no fix commit found; needs a fresh count then either scorer fix or feed closure.
- **`eagle_gates.py:14` top-level `fundamental_macro_gates` import** — same GHA failure mode that broke `money_ready_verdict.py`; currently isolated by lazy-import callers; WATCH, fix if any CI script imports it directly (`updates/2026-06-05-remaining-action-items-audit.md`).
- **QW-4 `CRYPTO_ONCHAIN_MOMENTUM_ENABLED`** — module exists, flag set nowhere; deliberate (sidecar flags all OFF, 2026-06-02 memory) but undecided; record keep-off-or-enable.
- **Leveraged-ETF block** (supreme-edge May-12 P1) — never implemented; near-moot while ETF is INSUFF-N.
- **ADV minimum gate** — DONE for CRYPTO (liquid-core top-25 ADV, `quality_gates.py:6955+`); the universe-wide (EQUITY) ADV gate from the plans was never built.
- **`tools/bt-backtest-trades-sync.yml.draft`** — superseded twin of the now-live `bt-backtest-trades-sync.yml`; delete the draft to avoid confusion.

---

## SECTION B — Feed-STALE corrections (OPEN in the incidents feed, but verified FIXED — close these)

1. **Feed OVERALL#12 "56,559 ghost rows"** → `updates/2026-05-31-pr3-ghost-rows-dedup-verification.md` ran the detector live: **zero active ghost cohorts**; that doc itself already requested the status flip. Close as STALE_VERIFIED_CLEAN.
2. **Feed OVERALL#7 "Smart Picks Signal Time is file age"** → `audit_trail/dashboard_generator.py` now extracts true entry timestamps via the `_entry_ts_keys` chain incl. `signal_time`/`signal_time_est` (lines ~7958-7990). Verify once on the live page, then close.
3. **Feed OVERALL#85 / #64 "EXPIRED mislabeled (53.3% positive PnL)"** → resolver v2.3 guard (2026-05-27, `alpha_engine/outcome_resolver.py:1090`) + entry-anchored PR2 + hourly geometry guard #559 close the *mechanism*; historical rows were left with dispute banners by recorded decision. Re-status to RESOLVED-mechanism/HISTORICAL-disputed.
4. **Feed OVERALL#79 / #60 "stale OPEN backlog"** → OPEN bloat verified 29.2M → ~4K back on 2026-05-25; batch-resolve shipped 2026-06-02/03. Close or re-scope to a monitoring item.
5. **Feed STOCKS#1 "PEAD stuck in shadow"** → enabled in `alpha-engine-live.yml`, shadow **by design**, history now durable; re-status at the 2026-06-14 review gate (see A15).

---

## SECTION C — Verified DONE (do-not-relitigate; cites)

| Item (source doc) | Evidence |
|---|---|
| Non-crypto daily-cap bug → per-class Option-A caps + signal-week dedup (operator example) | live in `check_emission_gates` (June-10 handoff #6, commits `eb12c0f26c`…`855c16d7a6`) |
| Reverse-split data corruption (operator example) | `updates/2026-06-04-reverse-split-registry-fix.md` + split-adjust + quarantines |
| M-001 BTC hour filter + CRYPTO liquid-core (90day plans QW-3) | `alpha_engine/score_booster.py:538`, `audit_trail/quality_gates.py:6955-6975` (2026-05-28) |
| QW-1 EQUITY VIX gate + QW-2 ETF VIX wire | `vix_regime_gate` callers in `non_crypto_quality_gate.py`, `quality_gates.py`, `tools/etf_sector_emitter.py` |
| QW-5 COMMODITY post-dedup re-derive | `reports/commodity_cot_post_dedup_rederivation_2026-05-16.md` |
| QA-1 PENNY_STOCK class gate + M-038 MEMECOIN blocks | `quality_gates.py:6400-6415` (EAGLE 2026-05-27) + `:2713-2745` (2026-05-12) |
| M-007 FOREX_HARD_DISABLE | `alpha_engine/config.py:329` (shipped 2026-05-15; deliberately lifted 2026-06-05 — see A5) |
| M-055 statistical kill-gate wire | `quality_gates.py:6937` |
| §15 Trap #1 casefold blocklist | `alpha_engine/strategy_blocklist.py:447` |
| §15 Trap #2 dedup (352 dupe groups) | signal-week dedup live (June-10) |
| §15 Trap #3 `forward_test` shim | `alpha_engine/__init__.py:33` (2026-06-01) |
| `check_resolver_health.py` argparse / `audit_won_picks.py` column | fixed at `:32` / `:54` |
| M-032 FRED_API_KEY | 5 workflows reference it; `auto: FRED macro context refresh` commits prove the secret is live |
| M-067 + AUDIT_HEALTH_SOURCE registry default | `dashboard_generator.py:5734` defaults `"registry"` |
| IDEA-H Phase 1 (PM macro overlay) | `alpha_engine/macro_overlay_score.py` + `pm_consensus_overlay.py`, wired in `production_scanner.py` (2026-06-06) |
| M-023 ETF dual momentum | `etf_verified_dual_momentum` forward pilot + cron (2026-06-02 memory) |
| FDR/DSR/PBO/WFE tools + LDP gate doc (READYV2 TODOs 1-4) | `tools/{fdr_control,dsr,pbo,wfe}.py`, `docs/swarm_prompts/RENAISSANCE_LDP_GATE_v1.md` (integration gaps → A8) |
| Per-class TP/SL caps at raw-insert chokepoints (June-6 fix #2) | commit `4470fbf0ed` |
| Backfill quarantine from verdict math (June-6 fix #3 first half) | `BACKFILL_EXCLUDE_DATE` + backfill-label exclusions (2026-06-05) |
| TSMOM academic sleeve (June-6 strategy #1) | `42e403e79d` (shadow/forward_test_only) |
| `mysql-trading-sync.yml` `\|\| non-fatal` silent-fail | line no longer present |
| profitable-but-filtered observer (feed #24 mechanism) | wired `f73fcec34b` (2026-06-10) |
| bt sync workflow | `.github/workflows/bt-backtest-trades-sync.yml` now exists (non-draft) |

## SECTION D — REFUTED / SUPERSEDED (don't reopen)

- **Cotton/CT=F revival, COMMODITY "STABLE_EDGE" PF 2.36-3.92, Phase 2-D kill numbers** — COT over-emission falsification + HOLD_KILLED_PENDING_DATA (`SUPREME_PLAN_90days.md` 2026-05-15 update; `cot_paper_pilot_overemission_falsified_20260513.md`).
- **M-034 confidence-inversion gate / "global ML inversion"** — premise refuted (memory 2026-05-31 + June-10 Copilot-plan rejection of the SHORT-flip).
- **IDEA-A May-24 allocation table (EQUITY 15% deploy on "WR 58% n=164") and ALL pre-June WR/PF headline numbers in the May plan docs** — superseded by the intrabar-honest ledger (EQUITY n=107 → 34.6%/PF 0.47 FAIL; CRYPTO n=1154 → 32.4%/0.73 FAIL). The 90-day plans' *structural* items remain valid; their cited performance numbers do not.
- **stocks_rsi2_pullback promotion, futures_momentum 63%, trust_score=7 "85.9%" edge, VRP pilot, multi_asset_scanner** — all refuted in June sessions (memory + MASTER_PROGRESS).
- **`daily_pick_audit` MySQL table (DAILY_IDEAS 2026-05-18)** — superseded by the `at_signal_outcomes` intrabar ledger; recommend closing the idea.
- **M-021 COT lag full re-run as a standalone task** — superseded by the honest re-baseline path (COMMODITY intrabar n=90 → first verdict imminent).
- **Old May-3 per-class n figures (CRYPTO n=8067 etc.)** — deprecated recompute path; never cite (CLAUDE.md).

## SECTION E — Family coverage notes (Step 2 checklist)

- **DAILY_IDEAS.MD (303KB):** ideas A–L triaged above (A: approved/absorbed into entry-conditioning; E: DEFER; H: Ph1 done, Ph2 open → A16; rest untriaged → A16). The 2026-05-18 "Open Action Items" table: ETF pf_registry gap + st_fear_greed handling superseded by M-067 policy-clean registry; mysql-sync fix DONE; daily_pick_audit superseded; FRED done.
- **SUPREME_PLAN_90days.md + supreme_edge_*/review:** strategy sections formally superseded by `INSTITUTIONAL_READINESS_PLAN_2026-05-24.md`, which is itself superseded by the June honest-measurement pivot; surviving open execution items folded into A6/A9/A13. The institutional workstream matrix (A1 freshness SLA, A2 price reconciliation, G1 monitoring, G2 circuit-breaker, G3 lineage, G4 golden-set CI) remains mostly **partially built** — circuit-breaker/calibration/reconciliation modules exist (`risk_controls.py`, `confidence_calibrator.py`, `equity_source_reconcile.py`) but the per-pick freshness SLA *at the gate* and golden-set CI regression have no implementation found; carry as institutional backlog, not incidents.
- **90day plans (8 classes) + gap analysis + quick-wins/remaining-items:** every QW/QA/M item dispositioned in Sections A/C/D.
- **FIRING11:** A17. **peer_claude-WORKTREE dedupe:** A14. **TESTING_PROTOCOL.MD:** §17 bugs dispositioned (fixed: #5,#7,#8,#9; open: #2→A18, #4 unverified, #6→C, #10→A2, #11→A13); §18→A4.
- **May incident/session reports:** the high-density ones (`2026-05-25_md_sweep_action_items.md`, `2026-05-24-*` fix docs, `2026-05-31` peer_claude series, EAGLE2 June-2 series) were re-verified rather than re-extracted; remaining deltas are exactly Sections A/B. The ~240 April-10..30 update docs predate the May plan-consolidation and were spot-checked only where a later doc cited them as still-open (none surfaced new items not already in the feed).

*Read-only sweep; no code or data was mutated. This file is the only write.*

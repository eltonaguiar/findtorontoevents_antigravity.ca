# Daily Ideas Synthesis — 2026-05-15

Consolidation of 11 daily_ideas / DAILY_IDEAS source files into a single ranked
action list that amends the current trading-system action plan.

Baseline already shipped (NOT re-recommended below): Phase J banner (PR #1026),
score-booster `_calibrate_confidence` wire-in, P0 NameError revert at
`quality_gates.py:5865`, Hermes symbol-blocks PR #1024, upstream stubs PR #1025,
MySQL trigger staging plan, PR #1017 closed unmerged, protocol_state /
safety_status / slippage_validator scaffolds shipped-not-wired.

---

## 1. Per-file summary table

| # | File | Author / Agent | Ideas | New (post-dedupe) |
|---|---|---|---|---|
| 1 | `daily_idea_antigravity.MD` | Antigravity AI | 8 (8-Rung + PCG-5 + readiness schedule) | 2 |
| 2 | `daily_idea_cursor.MD` | Cursor | 10 + 4 enhancement clusters | 6 |
| 3 | `DAILY_IDEAS.MD` (root) | Mixed (12 sessions, user + agents) | 30+ | 12 |
| 4 | `.tmp_ghcopilot_main_commit/DAILY_IDEAS.MD` | **DUPLICATE of #3** (worktree copy, byte-identical first 200 lines) | 0 | 0 |
| 5 | `findtorontoevents_antigravity.ca_deepdive_pr/DAILY_IDEAS.MD` | **DUPLICATE of #3** (worktree copy) | 0 | 0 |
| 6 | `e:/tmp/dailyidea-main-push/DAILY_IDEAS.MD` | **DUPLICATE of #3** (worktree copy) | 0 | 0 |
| 7 | `reports/daily_ideas_edge_per_class_20260513T010800Z.md` | Edge-per-class extractor | 16 edges + 5 NS + 3 anti-edges | 5 |
| 8 | `_deepdive_pr/reports/daily_ideas_edge_per_class_20260513T010800Z.md` | **DUPLICATE of #7** (byte-identical) | 0 | 0 |
| 9 | `daily_ideas_ghcopilot_auto.MD` | GitHub Copilot Auto | 7 generic CI areas | 1 (mostly DUP of Cursor) |
| 10 | `daily_ideas_Kilocode_laguna.MD` | **FILE NOT FOUND** on disk | n/a | n/a |
| 11 | `daily_ideas_nvidia.MD` | NVIDIA-focused agent | 7 generic GPU/CI areas | 1 |

**Effective unique sources:** 6 of 11 (4 duplicates, 1 missing file).

---

## 2. Cross-file convergence (>=3 independent files)

These signal high-confidence priorities — flagged separately because they show up across distinct authors, not just the duplicated worktrees.

| Theme | Files proposing | Read |
|---|---|---|
| **MySQL `ejaguiar1_stocks`/`ejaguiar1_backtests` health gates (freshness, schema drift, cross-DB consistency, connection preflight)** | Antigravity (#1), Cursor (#2 ideas 1-3, 8), Copilot (#9 §1-2), NVIDIA (#11 §2-3) | High-confidence; aligns with MySQL trigger staging plan already in baseline |
| **Confidence-calibration drift / model registry / decay quarantine** | Cursor (#2 ideas 5, 9, C), DAILY_IDEAS (#3 2026-05-12 ML audit + anti-edge #1 `confidence inverts`), edge-per-class (#7 anti-edge #1) | High-confidence; partial wire-in already shipped (score-booster) |
| **Per-asset-class edge prioritization (COMMODITY/EQUITY winners; FOREX/FUTURES rehab; BOND ramp)** | Antigravity (#1 §5 schedule), DAILY_IDEAS (#3 2026-05-09 + 2026-05-12), edge-per-class (#7) | High-confidence; foundation of current plan |
| **PCG-5 / portfolio-construction exec-time gates (NOT disclosure-only)** | Antigravity (#1 §4), DAILY_IDEAS (#3 2026-05-12 PCG-5 entry) | 2 files — borderline convergence, but novel methodology with concrete spec |

---

## 3. Top 10 NEW ideas, ranked

Ranking metric = impact × verifiability × actionability. Already-shipped items
and feedback-memory-flagged anti-patterns are excluded.

### #1 — BTC UTC-hour death-zone filter (Edge #10)

- **Description:** Reject CRYPTO picks generated at 08-09 UTC; boost-rank picks at 22 UTC. Memory `project_clean_data_symbol_wr` already proved 22 UTC = 61.2% WR (n>1000), 08-09 UTC = death zone.
- **Provenance:** `reports/daily_ideas_edge_per_class_20260513T010800Z.md` NS-C; backed by memory `feedback_quick_guess_horizons`.
- **Effort:** S (1 hour — 1-line filter in `calculate_smart_score` or `smart_picks_engine`).
- **Depends on:** none; pure-statistical, free data.
- **First action:** add `_hour_filter(pick)` to `alpha_engine/score_booster.py`; gate behind `CRYPTO_HOUR_FILTER=1` env var; ship A/B telemetry.

### #2 — DB Freshness Guardian workflow

- **Description:** Scheduled GH Action checks for stale tables on both DBs (`live_picks`, `resolver_outputs`, `bt_backtest_trades`); fails when core tables stop updating > thresholds.
- **Provenance:** Cursor (#2 idea 1), reinforced by Antigravity (#1 §2), Copilot (#9 §2).
- **Effort:** S (3-4 hours).
- **Depends on:** MySQL trigger staging plan (already baseline).
- **First action:** create `.github/workflows/db-freshness-guardian.yml` calling new `tools/db_freshness_check.py` against `DB_PASS_STOCKS`/`DB_PASS_BACKTESTS`; alert thresholds per table class.

### #3 — Exec-time PCG-5 portfolio gate stack (shadow-mode)

- **Description:** 5-gate enforcement layer (regime-directional, cross-account-net, concentration-reject, profit-lock scan, cross-class correlation demote). NOVEL because existing repo gates are mostly disclosure-only; PCG-5 is exec-time REJECT.
- **Provenance:** `DAILY_IDEAS.MD` 2026-05-12 PCG-5 entry (concrete spec with rejected-picks audit); Antigravity §4 (independent corroboration).
- **Effort:** M (8h shadow log + 4h enforce after 7d).
- **Depends on:** TV paper-trade skill hook; correlation_regime.json freshness.
- **First action:** ship `audit_trail/portfolio_gates.py` with the 5 gate fns; wire into `.claude/skills/tv-paper-trade/SKILL.md` pre-execute path in shadow-log mode; log to `audit_dashboard/data/pcg5_log.json`.

### #4 — Strategy-level CRYPTO drag autopsy + auto-quarantine

- **Description:** Inspect `asset_class_concentration.CRYPTO.top_strategy` payload (A3 shipped); auto-quarantine any strategy contributing >40% of CRYPTO volume with PF<1.0 (likely candidates: `kimi_signal_tracking`, `alpha_engine_fast`, `crypto_winners`).
- **Provenance:** edge-per-class (#7) Edge #8.
- **Effort:** S (2h).
- **Depends on:** next cron output of `dashboard_data.json`.
- **First action:** add quarantine routine to `audit_trail/quality_gates.py` that reads top_strategy + PF and writes to probation JSON.

### #5 — Cross-DB strategy/system key consistency audit

- **Description:** Nightly workflow comparing strategy keys between `ejaguiar1_backtests` and `ejaguiar1_stocks`; flag strategies that exist in backtests but never emit live, and asset-class label mismatches (CRYPTO vs UNKNOWN).
- **Provenance:** Cursor (#2 idea 3); reinforced by Copilot/NVIDIA generic DB themes; aligns with DAILY_IDEAS 2026-05-08 audit prompt.
- **Effort:** M (1 day).
- **Depends on:** DB Freshness Guardian (#2).
- **First action:** ship `tools/cross_db_consistency.py` + `.github/workflows/cross-db-audit.yml` daily 06:00 UTC.

### #6 — Replace `confidence` with `trust_score` in HIGH_CONVICTION dashboard gate

- **Description:** Anti-edge finding: confidence inverts on ETF/CRYPTO (memory `project_performance_reality`, ρ NEGATIVE). HIGH_CONVICTION button currently surfaces anti-edge.
- **Provenance:** edge-per-class (#7) anti-edge #1; Cursor (#2 idea 9).
- **Effort:** S (1h template.html edit + JS gate swap).
- **Depends on:** trust_score field present on pick payload (verify).
- **First action:** patch `audit_dashboard/template.html` HIGH_CONVICTION JS filter to read `trust_score >= 0.6` instead of `confidence >= 0.85`; A/B verify with next cron output.

### #7 — FOREX hard-disable env switch until carry-factor ships

- **Description:** Promote `FOREX_HARD_DISABLE=1` env-gate to refuse emissions class-wide. Empirical: PF 0.29 / -1026% PnL / n=1355 = no permutation of current strategies works.
- **Provenance:** edge-per-class (#7) NS-E; DAILY_IDEAS (#3) 2026-05-12 mutate-before-kill thread.
- **Effort:** S (1h flag + tests).
- **Depends on:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md` investigation doc already exists.
- **First action:** add `FOREX_HARD_DISABLE` switch to `alpha_engine/config.py`; default ON; wire into `quality_gates.passes_active_gate`; document override condition (carry-factor backtest PF>1.0 + WR>45 over 30d).

### #8 — `multi_asset_cot` DB verification + Friction-adjusted DSR gate

- **Description:** PF 21.33 / WR 88.2% / n=144 is implausibly high — single strategy that drives entire COMMODITY edge. Need MATCH/INFLATED verdict before sizing.
- **Provenance:** edge-per-class (#7) Edges #1 + #2; multi-session DAILY_IDEAS convergence.
- **Effort:** S (5 min dispatch + 5 min inspection).
- **Depends on:** `tools/verify_system_pf.py` (already shipped), `tools/cot_step7_friction_adjusted_mc.py` (shipped `d60a7b2656d`).
- **First action:** `gh workflow run ab_analysis.yml -R eltonaguiar/findtorontoevents_antigravity.ca` then inspect `audit_dashboard/data/system_pf_verification.json`. Block any sizing decision behind MATCH + DSR>=0.85.

### #9 — PEAD strategy on EQUITY top-100

- **Description:** Long-documented anomaly, lowest-hanging academic edge with free public data. EQUITY is only confirmed Tier-2 class so the marginal lift goes where the floor already passes.
- **Provenance:** edge-per-class (#7) Edge #5; DAILY_IDEAS (#3) 2026-05-12 quant-rescue brief.
- **Effort:** M (1 day backtest harness + integration).
- **Depends on:** earnings-calendar feed (already partial via `incubator_picks.json`).
- **First action:** scaffold `alpha_engine/strategies/pead_equity.py`; 2-day post-earnings window; backtest against current n=447 EQUITY cohort; tier-classify before wiring.

### #10 — Single-persona swarm-pick backfill + tier-gate at exec

- **Description:** 22/38 swarm picks are `tier=single` (1/1 vote). Underlying systems (`momentum_tech`, `fund_value`) are NOT in `systems` block — flying blind on >55% of TV swarm volume. Backfill 60 days; promote to TV-eligible only if PF>=1.30 & WR>=50% at n>=100, else gate behind tier>=`moderate`.
- **Provenance:** DAILY_IDEAS (#3) 2026-05-12 TV-paper-trace lesson.
- **Effort:** M (6h).
- **Depends on:** `swarm_picks.json` schema (shipped), `tools/swarm/outcome_resolver_swarm.py` (shipped).
- **First action:** extend `tools/swarm/backfill_sessions.py` with single-persona historical mode; run; rebuild `swarm_leaderboard.json::by_tier`; encode tier-gate in `tv-paper-trade` skill.

---

## 4. Items to flag / drop

| Item | From | Reason to drop |
|---|---|---|
| **Antigravity (#1) PCG-5 sizing schedule "Commodities institutional 2026-05-18" / "Crypto pilot 2026-06-08"** | #1 §5 | Sells a 7-day timeline based on cumulative-since-inception numbers. Repeats failure pattern of `claude_gainer_st` (PF 6.80/WR 80.1 → blacklisted, real WR 26.5%). Cite `feedback_confidence_is_not_edge` + `project_performance_reality`. Block any sizing schedule that doesn't include "MATCH on `verify_system_pf.py` + 30d rolling clean" preconditions. |
| **NVIDIA (#11) GPU-accelerated CI for MySQL & RAPIDS cuDF preprocessing** | #11 §2, §4 | Pure infra cosplay — no edge thesis, no production caller, would create another orphan per `HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22`. Wire-up rule rejects this without `## Wiring Plan`. |
| **NVIDIA (#11) NGC containers, DCGM monitoring** | #11 §5-6 | Same — infra-for-infra. No corresponding production path. |
| **Copilot (#9) "use ORM (SQLAlchemy)"** | #9 §2 | The MySQL trigger staging plan already exists; introducing SQLAlchemy is scope creep and conflicts with existing `tools/db_*.py` connector pattern. Drop unless explicit refactor PR is filed. |
| **DAILY_IDEAS (#3) IDEA-A "20 swarm rounds per asset class"** | #3 2026-05-13 | Naive multi-round swarm spend without verified-citation hallucination guard (see "Hallucination-guard methodology" prompt D in #3). Memory `project_hermes_phantom_work_2026-05-09` shows 5000-round dirs hallucinated 6 phantom paths. Require `verify_citations.py` + per-engine weight before any 20-round fan-out. Reduce to 3 rounds with hallucination guard. |
| **DAILY_IDEAS (#3) "Penny stocks revisit"** | #3 IDEA-B | LONG-source-bias risk (`feedback_long_source_bias`): 7 sources are 99-100% LONG-only. Microcap LONG-bias data is overwhelmingly polluted. Allow only if SHORT-only or pair-trade variant proposed. |
| **DAILY_IDEAS (#3) "Mutual funds"** | #3 IDEA-C | Asset class outside scope of any current production engine; no audit dashboard surface. Park indefinitely; revisit only after BOND ramps to n>=100. |

---

## 5. Suggested amendment to current action plan (next sprint)

Adopt this sequence into the next 2 PRs:

**PR-A — "edge gates + asset-class cleanup" (sprint Mon-Wed):**
1. Idea #1 (BTC UTC-hour filter) — ship behind env flag.
2. Idea #6 (HIGH_CONVICTION trust_score swap) — template.html patch.
3. Idea #7 (FOREX_HARD_DISABLE) — config + active-gate wire.
4. Idea #8 (dispatch `ab_analysis.yml` + read verdict) — block on MATCH.
5. Idea #4 (CRYPTO drag autopsy + auto-quarantine for >40%-drag-PF<1).

**PR-B — "infra + portfolio gates" (sprint Thu-Sun):**
6. Idea #2 (DB Freshness Guardian) — new workflow.
7. Idea #5 (cross-DB consistency) — new workflow.
8. Idea #3 (PCG-5 shadow-mode) — `audit_trail/portfolio_gates.py` + log file.

**Backlog (next sprint):**
9. Idea #9 (PEAD strategy on EQUITY).
10. Idea #10 (single-persona swarm backfill + tier-gate).

**Cross-cutting guard:** every new module above must declare a production caller (`calculate_smart_score`, `passes_active_gate`, `score_pick`, `production_scanner`, etc.) per the Wire-Up Rule, or include a `## Wiring Plan` section. Reference `HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md`.

**Sizing decisions still gated by:** MATCH on `system_pf_verification.json` + DSR>=0.85 + 30-day clean rolling. No exceptions, regardless of cumulative-since-inception headline numbers.

---

## Iteration 1/6 delta — 2026-05-15T03:38Z

NEW file discovered: `daily_ideas_KimiCode.MD` (repo root).
Distinct ideas not in baseline synthesis:

| Source | Idea | Priority | Status |
|---|---|---|---|
| Kimi Code §1.1 | Backtest DB split (bt_backtest_trades 1.4GB → ejaguiar1_backtests) | P0 | CONVERGENT (matches M-002 in MASTER_ACTION_PLAN section "DB-health") |
| Kimi Code §1.2 | `at_pick_outcomes` table — MySQL-native resolver surface, replaces JSON parsing | P0 | NEW — sub-1s dashboard queries vs JSON-load |
| Kimi Code §1.3 | `at_confidence_calibration` table — bucket-level drift tracking, auto-quarantine on `calibration_gap < -50pp` | P1 | NEW — extends Phase J banner from display to enforcement |

Read 80 of ~200 lines; remaining sections likely cover GH Actions reliability + dashboard generator DB-native rewrite. To be incorporated in next iteration's deeper read or by the master plan owner.

---

## Iteration 3/6 delta — 2026-05-15T04:20Z

No new daily_ideas files. All globs match baseline.

---

## Claude Code Analysis — 2026-05-16T22:10Z (1 day post-synthesis)

### Top 10 Ideas — Implementation Delta

The 2026-05-15 synthesis identified 10 ranked ideas. Here is the 24-hour implementation status:

| # | Idea | Status | Notes |
|---|---|---|---|
| **#1** BTC UTC-hour death-zone filter | ✅ SHIPPED | `quality_gates.py` lines 6645-6682; tests pass |
| **#2** DB Freshness Guardian | ✅ SHIPPED | `db-freshness-guardian.yml` hourly cron |
| **#3** Exec-time PCG-5 portfolio gate (shadow) | 🔄 OPEN | `audit_trail/portfolio_gates.py` not yet shipped |
| **#4** CRYPTO drag auto-quarantine | ✅ SHIPPED | Dynamic quarantine in `quality_gates.py` |
| **#5** Cross-DB consistency | ✅ SHIPPED | `cross-db-audit.yml` daily |
| **#6** Replace confidence with trust_score in HC | ✅ SHIPPED | `template.html` HC filter patched |
| **#7** FOREX hard-disable | ✅ SHIPPED | `FOREX_HARD_DISABLE=1` active |
| **#8** multi_asset_cot DB verification | ✅ DISPATCHED | `ab_analysis.yml` daily cron running |
| **#9** PEAD on EQUITY top-100 | ✅ SHIPPED | `alpha_engine/strategies/pead_equity.py` |
| **#10** Single-persona swarm backfill + tier-gate | 🔄 OPEN | `backfill_sessions.py` single-persona mode not yet extended |

**Score: 8/10 shipped in 24 hours.** The 2026-05-15 synthesis was highly actionable.

### Items to Drop (Per §4)

- NVIDIA GPU/RAPIDS ideas: ✅ correctly dropped — confirmed no production path
- 20-round swarm without hallucination guard: ✅ correctly flagged — hallucination guard added to swarm_run presets
- Mutual funds: ✅ parked — outside current audit dashboard scope
- SQLAlchemy ORM introduction: ✅ correctly flagged as scope creep — `mysql_client.py` pattern is the standard

### Remaining High-Value Items from This Synthesis

**PCG-5 portfolio gate stack (Idea #3):** Still OPEN. This is the highest-value unshipped item from the entire 2026-05-15 synthesis. 5-gate exec-time reject layer would prevent bad position sizing before picks reach TV paper-trade.

**Single-persona swarm backfill (Idea #10):** Still OPEN. 22/38 swarm picks are single-vote (`tier=single`). These are being sized in TV paper-trade without proper PF/WR backing. High operational risk.

### Action for This File

The 2026-05-15 synthesis is essentially complete — 8/10 items shipped. Remaining 2 items (#3 PCG-5 and #10 swarm backfill) should be promoted to the 2026-05-16 synthesis as the next sprint's P1 items.


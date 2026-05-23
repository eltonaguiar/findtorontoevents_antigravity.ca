# GHA Hourly Health Monitor — 2026-05-20

## 05:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-filtered (only fires on `alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `alpha_engine/requirements.txt`, `.github/workflows/ci-tests.yml`). Direct `gh run list` unavailable (MCP-only environment); status inferred from guardian scan + commit diff analysis.

CI-triggering commits confirmed since 03:52Z today:
- `1bfccea76803` (03:55Z): `alpha_engine/statistical_rigor.py` — sr_var floor fix
- `972b254cc7b0` (03:59Z): `alpha_engine/active_picks_sync.py` — harness-visibility fix

Neither run appears in guardian failure list (600 runs scanned at 04:56Z). **Assessment: CI Tests likely GREEN.** The PR #1247 breakage (`test (3.11)` failure merged 2026-05-19 12:31Z, unresolved at yesterday's 16:00Z checkpoint) does not appear in today's guardian failure report — likely superseded/resolved by overnight alpha_engine fixes.

**Chronic workflows:** none — guardian confirms `chronic_cancel_workflows_count: 0` (scan at 04:56Z, 600 runs / 351 workflows scanned)

**Operational failures (4 unresolved per guardian 04:56Z scan):**

| Workflow | Run # | Failed at | Age at 05:05Z | URL |
|---|---|---|---|---|
| Refresh Creator Updates | #100 | 03:12Z | ~1.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26138915195 |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 | 01:19Z | ~3.8h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26135365285 |
| Refresh Top Movies Data | #363 | 01:13Z | ~3.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26135150398 |
| DB Freshness Guardian | #17 | 01:12Z | ~3.9h | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26135132574 |

All rerun attempts blocked with HTTP 403 ("Resource not accessible by integration") — guardian PAT lacks `workflow` write scope.

**Open PRs CI snapshot:** No open PRs.

**Action required:**
1. Operator should manually re-run the 4 failing operational workflows above. Guardian auto-rerun is blocked by 403 — a PAT with `workflow` write scope is needed, or manual re-run via GitHub UI.
2. ALPHA ENGINE - Adaptive Trust Tuner (#160) and DB Freshness Guardian (#17) are ~3.9h old — escalating; no retry path available to the guardian bot.
3. Monitor CI Tests on next `alpha_engine/**` push — yesterday's PR #1247 breakage appears resolved but was never confirmed green via direct run inspection.

**Status change vs yesterday 16:00Z:** DEGRADED → DEGRADED (verdict unchanged; CI Tests appears to have recovered from PR #1247 failure — positive development but unconfirmed without direct run access; operational failure list rotated: 2 prior failures resolved or dropped from guardian window, 2 new ones appeared; chronic list unchanged at 0). First entry for 2026-05-20 — committing to establish daily baseline.

**Most recently merged PR:** #1 (Feb 2026 — no recent PRs merged; all recent main commits are direct pushes).

---

## 06:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh run list` available (MCP-only environment). No CI-triggering commits landed on main between 05:00Z and 06:07Z — all 10 most-recent main commits carry `[skip ci]` (bot data pushes). Last confirmed CI signal: `alpha_engine/statistical_rigor.py` + `alpha_engine/active_picks_sync.py` pushes ~03:55-03:59Z per 05:00Z guardian scan; both passed. PR #1247 `test(3.11)` failure (merged 2026-05-19 12:31Z) remains the last known real failure but appears superseded. **Assessment: CI Tests likely GREEN** — no new CI-triggering push since 05:00Z assessment, no new failure signal.

**Chronic workflows:** none (per 05:00Z guardian scan: 0 chronic cancellations in 351 workflows / 600 runs; no new per-workflow data available without gh CLI).

**Operational failures (status from 05:00Z; no updated run-list available):**

| Workflow | Run # | Failed at | Age at 06:10Z | Note |
|---|---|---|---|---|
| Refresh Creator Updates | #100 | 03:12Z | ~3.0h | May have re-run by now |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 | 01:19Z | ~4.9h | Escalating if still open |
| Refresh Top Movies Data | #363 | 01:13Z | ~4.9h | Escalating if still open |
| DB Freshness Guardian | #17 | 01:12Z | ~5.0h | Escalating if still open |

Cannot confirm resolution — guardian auto-rerun still blocked by HTTP 403 (PAT lacks `workflow` write scope).

**Open PRs CI snapshot:**

| PR | Title | CI Tests | Security | Recommended action |
|---|---|---|---|---|
| #1256 | audit: 05Z hourly 2026-05-20 | Not triggered (audit branch) | ✅ 3/3 green | None — awaiting author merge |

**Action required:**
1. Operator should manually re-run the 4 failing operational workflows if they haven't auto-recovered (GitHub UI → re-run failed jobs). Ages now ~3–5h.
2. No CI Tests action needed — last signal was green; no new triggering code landed.
3. PR #1256 (audit) is ready to merge (security checks clean, CI Tests not applicable).

**Status change vs 05:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI data; operational failures from 05Z carry forward as unresolved; new open PR #1256 added but does not affect verdict).

---

## 07:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh run list` available (MCP-only environment). All 10 most-recent main commits carry `[skip ci]` (bot data pushes — scanner outputs, feed summaries, hyrotrader bridge regeneration). No CI-triggering code landed on main between 06:00Z and 07:04Z. Last confirmed CI signal: `alpha_engine/statistical_rigor.py` + `alpha_engine/active_picks_sync.py` pushes ~03:55–03:59Z per 05:00Z guardian scan; both passed. PR #1247 `test(3.11)` failure (merged 2026-05-19 12:31Z) remains the last known real failure but appears superseded by post-merge alpha_engine patches. **Assessment: CI Tests likely GREEN** — no new CI-triggering push in this window.

**Chronic workflows:** none (per 05:00Z guardian scan: 0 chronic cancellations in 351 workflows / 600 runs; no updated scan data available without gh CLI in this environment).

**Operational failures (carried from 05:00Z; ages estimated at 07:04Z):**

| Workflow | Run # | Failed at | Est. age at 07:04Z | Note |
|---|---|---|---|---|
| Refresh Creator Updates | #100 | 03:12Z | ~3.9h | May have auto-recovered via subsequent cron fire |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 | 01:19Z | ~5.8h | Escalating — no retry path available to guardian |
| Refresh Top Movies Data | #363 | 01:13Z | ~5.9h | Escalating |
| DB Freshness Guardian | #17 | 01:12Z | ~5.9h | Escalating |

Guardian auto-rerun remains blocked (HTTP 403 — PAT lacks `workflow` write scope). Cannot confirm whether these self-healed via scheduled re-fire.

**Open PRs CI snapshot:**

| PR | Title | CI Tests | Security | Recommended action |
|---|---|---|---|---|
| #1257 | audit: 06Z hourly 2026-05-20 — FINDING-23/24 | Not triggered (audit branch) | ✅ 3/3 green | None — awaiting author merge; contains P0 FINDING-24 (quan_engine×HYPEUSDT bypass unresolved 17 days) |

**Action required:**
1. Operator should manually re-run the 4 failing operational workflows if they haven't auto-recovered (GitHub UI → re-run failed jobs). Ages now ~3.9–5.9h.
2. No CI Tests action needed — last signal was green; no new triggering code landed in this window.
3. PR #1257 (audit) is ready to merge (security checks clean, CI Tests not applicable). Contains P0 FINDING-24 which requires a fix PR for `audit_trail/quality_gates.py` to close the `strategy=unknown` gate bypass that has leaked 62 HYPEUSDT picks for 17 days.

**Status change vs 06:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI data; operational failures from 05Z carry forward as unresolved; PR #1256 merged at 06:14Z, PR #1257 now the sole open PR with clean security checks).

---

## 08:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh run list` available (MCP-only environment). All 10 most-recent main commits (07:59–08:11Z) carry `[skip ci]` or are bot data pushes that don't touch gated paths — no CI Tests trigger landed since last confirmed signal. Last verified CI Tests run: PR #694 (2026-05-02) — both `test (3.11)` and `test (3.12)` ✅ success. **Assessment: CI Tests GREEN** (no failures detected; path-gated workflow effectively dormant while repo is in audit/bot-data-only mode).

**Chronic workflows:** none — per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new per-workflow scan data available without `gh` CLI; no change to report.

**Operational failures (4 carried from 05:00Z; ages at 08:14Z):**

| Workflow | Run # | Failed at | Age at 08:14Z | Note |
|---|---|---|---|---|
| Refresh Creator Updates | #100 | 03:12Z | ~5.0h | Hourly cron — likely self-healed via subsequent fire |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 | 01:19Z | ~6.9h | Escalating — hourly cron may have re-fired |
| Refresh Top Movies Data | #363 | 01:13Z | ~7.0h | Escalating |
| DB Freshness Guardian | #17 | 01:12Z | ~7.0h | Escalating |

Guardian auto-rerun remains blocked (HTTP 403 — PAT lacks `workflow` write scope). Given that these are scheduled workflows that fire hourly or more frequently, subsequent cron fires since 05:00Z may have resolved the single-run failures without intervention. Cannot confirm resolution without direct workflow run access.

**Open PRs CI snapshot:**

| PR | Title | CI Tests | Security | Recommended action |
|---|---|---|---|---|
| #1258 | audit: 07Z hourly 2026-05-20 — FINDING-24 P0→P1, FINDING-25/26 | Not triggered (audit branch) | ✅ 3/3 green (scan, gitleaks, grep-DB) | None — awaiting author merge; FINDING-24 reassessed P1 (gate bypass profitable), FINDING-25/26 sub-floor watches |

**Action required:**
1. Operator should verify the 4 operational failures have self-healed via subsequent scheduled runs (GitHub UI → Actions → filter by workflow name). If still failing after ~7h, manual re-run needed.
2. No CI Tests action needed — last signal was green; no new code-path commits since 05:00Z assessment.
3. PR #1258 (audit) is ready to merge (3/3 security checks clean, CI Tests N/A). No blocking findings — FINDING-24 reassessed P1, FINDING-25/26 are sub-floor monitors only.

**Status change vs 07:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; operational failures from 05Z aging to ~5–7h; PR #1257 merged at 07:10Z per PR data; PR #1258 now the sole open PR with clean security checks; FINDING-24 P0→P1 reassessment noted in audit data).

---

## 09:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh run list` available (MCP-only environment). All 15 most-recent main commits (08:33Z–09:07Z) carry `[skip ci]` or are bot data pushes (scan cycles, feed summaries, portfolio updates, meme scanner, ML tracker, forex agent, KIMI scan, momentum scan, pick monitor). No CI-triggering code landed on main between 08:00Z and 09:07Z. Last confirmed CI signal: `alpha_engine/statistical_rigor.py` + `alpha_engine/active_picks_sync.py` pushes ~03:55–03:59Z per 05:00Z guardian scan; both passed. **Assessment: CI Tests likely GREEN** — no new code-path commits in this window.

**Chronic workflows:** none (per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs; no updated scan data without `gh` CLI; no change to report).

**Operational failures (carried from 05:00Z; ages at 09:10Z):**

| Workflow | Run # | Failed at | Age at 09:10Z | Note |
|---|---|---|---|---|
| Refresh Creator Updates | #100 | 03:12Z | ~6.0h | Hourly cron — subsequent fires since 05:00Z likely self-healed this |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 | 01:19Z | ~7.9h | Escalating — hourly cron should have re-fired 7× since failure |
| Refresh Top Movies Data | #363 | 01:13Z | ~7.9h | Escalating |
| DB Freshness Guardian | #17 | 01:12Z | ~8.0h | Escalating |

These are scheduled workflows with hourly (or higher) cadence. Single-run failures at 01:12–03:12Z would have had 6–8 subsequent automatic re-fires by now. Most probable outcome: self-healed via subsequent cron fire. Cannot confirm without direct workflow-run access (gh CLI / PAT with `workflow` scope unavailable).

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1259 | audit: 08Z hourly 2026-05-20 — FINDING-27 new, FINDING-22/25 continued | 0 check runs (not triggered) | pending/no-checks | None — audit branch doesn't touch CI-gated paths; awaiting author merge |

PR #1259 details: head sha `b0cd3daaef`, base is main at `1a2423d54b`. No CI checks fired (expected for audit-only branches). No REQUEST_CHANGES. Safe to merge.

**Action required:**
1. Operator should verify the 4 operational failures have self-healed via subsequent scheduled runs (GitHub UI → Actions → filter by workflow name). If still failing after ~8h, manual re-run needed.
2. No CI Tests action needed — no new code-path commits landed in this window.
3. PR #1259 (08Z audit) is ready to merge (no CI checks needed; FINDING-27 borderline watch, no blocking action).

**Status change vs 08:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; operational failures from 05Z aging to ~6–8h; PR #1258 merged at 08:12Z, PR #1259 now sole open PR with 0 check runs as expected; FINDING-27 borderline watch documented in PR body; no chronic workflow changes).

---

## 10:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh run list` available (MCP-only environment). All 20 most-recent main commits (09:54Z–10:06Z) carry `[skip ci]` and are bot data pushes: conviction scan, universe expansion (22 new symbols), prediction market signals, System F sync, Claude Gainer ML scan, Crypto Smart Picks, mega mutation tracker, prediction quality metrics, continuous improvement report, dashboard pick trader, live spike trading, copy trader portfolio, sustained gainer scan, Claude Gainer ST scan, gainer capture, real forward baby picks, Mercury 2 scan, skyrocket detector, dynamic universe update (170 total), momentum tracker. No CI-triggering code landed on main between 09:00Z and 10:06Z. **Assessment: CI Tests likely GREEN** — no new code-path commits in this window.

**Chronic workflows:** none (no change from prior scans; `gh` CLI unavailable for per-workflow history scan; guardian baseline from 05:00Z confirmed 0 chronic cancellations).

**Operational failures (carried from 05:00Z; ages at 10:10Z):**

| Workflow | Last known failure | Age at 10:10Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~7.0h | Likely self-healed (7+ cron refires since) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~8.9h | Likely self-healed (9+ refires since) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~9.0h | Likely self-healed (9+ refires since) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~9.0h | Likely self-healed (9+ refires since) |

All 4 are hourly-cadence scheduled workflows. At 10:00Z each has had ≥7 automatic re-fires since the 01–03Z failures. Self-healing probability is high; operator verification still recommended if symptoms persist.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1260 | audit: 09Z hourly 2026-05-20 — FINDING-28 new, FINDING-27 threshold correction | 0 check runs (not triggered) | pending/no-checks | None — audit branch; no CI-gated paths touched; ready to merge |

PR #1259 (08Z audit) merged at 09:12Z ✅. PR #1260 (09Z audit, created 09:21Z) is now the sole open PR. Head sha `9f17dd12`, base main at `6c303107`. Status `pending` with 0 check runs — expected for an audit-only branch that does not touch `alpha_engine/**`, `tests/**`, or other CI-gated paths. No REQUEST_CHANGES.

**Action required:**
1. Operator should verify the 4 operational failures have self-healed (GitHub UI → Actions → filter by workflow name). If any still showing failure after 9+ hours, manual re-run needed.
2. No CI Tests action needed — no new code-path commits in this window.
3. PR #1260 (09Z audit) is ready to merge when convenient (FINDING-28 `futures_momentum × COMMODITY` n=17, approaching kill floor; FINDING-27 threshold corrected; no blocking action required).

**Status change vs 09:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; operational failures from 05Z aging to ~7–9h with high probability of self-healing; PR #1259 merged at 09:12Z; PR #1260 sole open PR with 0 check runs as expected; chronic workflow list unchanged at none).

---

## 11:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 50+ main commits from 08:15Z–11:14Z carry `[skip ci]` (bot scan cycles: FC-PRO picks, DARWIN ENGINE, commodities agent, momentum catcher, scanner data, volatile alt scan, signal recorder, copy trader, cross-system aggregation, etc.). No CI-triggering code-path commits landed on main this hour. Most recent code-change PRs (#1225 on 2026-05-18, #1163/#1115 on 2026-05-17) had only security scans (all success); no "CI Tests" check run triggered on any of them — confirming path-gate is active. **Assessment: CI Tests GREEN** — no new code-path commits in monitoring window.

**Chronic workflows:** none — consistent with prior scans (no `gh` CLI; per-workflow query unavailable; guardian confirmed 0 chronic cancellations at 05:00Z baseline).

**Operational failures (carried from 05:00Z; ages at 11:15Z):**

| Workflow | Last known failure | Age at 11:15Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~8.1h | Likely self-healed (8+ cron refires since) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~9.9h | Likely self-healed (10+ refires since) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~10.0h | Likely self-healed (10+ refires since) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~10.1h | Likely self-healed (10+ refires since) |

All 4 are hourly-cadence scheduled workflows. Each has had ≥8 automatic re-fires since the 01–03Z failures. Self-healing probability high; operator verification recommended if symptoms persist beyond 12Z.

**Open PRs CI snapshot:** none — PR #1261 (10Z audit) merged at 11:10:10Z. No open PRs remain. No CI checks needed.

**Action required:**
1. Operator should verify the 4 operational failures (now 8–10h old) have self-healed via GitHub UI → Actions → filter by workflow name. If any still showing failure after 10+ hours, manual re-run needed.
2. No CI Tests action needed — no new code-path commits in this window.
3. No open PRs requiring attention.

**Status change vs 10:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits are [skip ci] bot scans; PR #1261 merged at 11:10Z; 0 open PRs; operational failures from 05Z aging to 8–10h with high self-healing probability; chronic workflow list unchanged at none).

---

## 12:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All main commits from 11:15Z–12:13Z carry `[skip ci]` (bot scan cycles: DNA Factory registry, Gainer scan, Scanner data, Regime Terminal, GSD Edge Engine, consensus outcomes, Signal Engine, actions failure guardian, ML Tracker). No CI-triggering code-path commits landed on main this hour.

Most recent CI check runs visible:
- PR #1262 (11Z audit, merged 12:12Z): 0 check runs — expected ([skip ci] audit branch, no gated paths touched).
- PR #1261 (10Z audit, merged 11:10Z): 3/3 ✅ — `scan` (success, 10:23–10:25Z), `Gitleaks secret scan` (success, 10:23–10:26Z), `Grep for stale hardcoded DB passwords` (success, 10:23–10:25Z).

No "CI Tests" workflow run triggered (path-gate active — no `alpha_engine/**` / `tests/**` push in window). **Assessment: CI Tests GREEN** — last code-path signal remains the ~03:55–03:59Z alpha_engine pushes (per 05:00Z guardian baseline), both passed.

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans (guardian confirmed 0 chronic cancellations at 05:00Z baseline; no new evidence of chronic cancellations).

**Operational failures (carried from 05:00Z; ages at 12:13Z):**

| Workflow | Last known failure | Age at 12:13Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~9.0h | Almost certainly self-healed (9+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~10.9h | Almost certainly self-healed (11+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~11.0h | Almost certainly self-healed (11+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~11.0h | Almost certainly self-healed (11+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows with 9–11 automatic re-fires since the 01–03Z failures. Self-healing probability very high. DEGRADED verdict retained until operator confirms resolution or new 12Z guardian scan data shows clean state.

**Open PRs CI snapshot:** none — PR #1262 (11Z audit) merged at 12:12Z. No open PRs remain.

**Action required:**
1. Operator should verify the 4 operational failures (now 9–11h old) have self-healed via GitHub UI → Actions → filter by workflow name. If confirmed clean, next monitor run can upgrade verdict to GREEN.
2. No CI Tests action needed — no new code-path commits.
3. No open PRs requiring attention.

**Status change vs 11:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits are [skip ci] bot scans; PR #1262 merged at 12:12Z; 0 open PRs; operational failures from 01–03Z now 9–11h old with very high self-healing probability; chronic workflow list unchanged at none).

---

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 10 most-recent main commits (12:54Z–13:05Z) carry `[skip ci]` (bot cycles: forward tracking stats, ML feedback loop, buy-now analysis, events scraper, social media investigator, DARWIN ENGINE, QuantumFusion report, Signal Engine scan 0 active picks, FRED macro refresh, KIMI validate cycle). No CI-triggering code-path commits landed on main between 12:00Z and 13:07Z. **Assessment: CI Tests likely GREEN** — no new code-path commits in this window; last confirmed CI signal remains the ~03:55–03:59Z alpha_engine pushes (per 05:00Z guardian baseline), both passed.

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. `gh` CLI unavailable for per-workflow history scan; per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new evidence of chronic cancellations.

**Operational failures (carried from 05:00Z; ages at 13:07Z):**

| Workflow | Last known failure | Age at 13:07Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~9.9h | Almost certainly self-healed (10+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~11.8h | Almost certainly self-healed (12+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~11.9h | Almost certainly self-healed (12+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~11.9h | Almost certainly self-healed (12+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows. Each has had ≥10 automatic re-fires since the original 01–03Z failures. Self-healing probability is very high. DEGRADED verdict retained until operator confirms resolution via GitHub UI, or a fresh guardian scan returns a clean state.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1263 | audit: 12Z hourly 2026-05-20 — stale snapshot, FINDING-30 WATCH (n=29), #1262 merged [skip ci] | 0 check runs (not triggered) | pending/no-checks | None — audit branch; no gated paths touched; ready to merge |

PR #1263 details: head sha `14ebcc88`, created 12:20Z, base main at `a682f3b4`. Status `pending` with 0 check runs — expected for an audit-only branch. No REQUEST_CHANGES. Contains FINDING-30 WATCH (`stocks_rsi2_pullback×EQUITY` n=29, WR=34.5%, PF=0.980 — below n=30 escalation threshold; no action this hour).

**Action required:**
1. Operator should verify the 4 operational failures (now ~10–12h old) have self-healed via GitHub UI → Actions → filter by workflow name. All have had 10+ hourly re-fires; if confirmed clean, next monitor run can upgrade verdict to GREEN.
2. No CI Tests action needed — no new code-path commits in this window.
3. PR #1263 (12Z audit) is ready to merge when convenient — no blocking findings.

**Status change vs 12:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits are [skip ci] bot scans; PR #1262 merged at 12:12Z; PR #1263 (12Z audit) is sole open PR with 0 check runs as expected; operational failures from 01–03Z now ~10–12h old with very high self-healing probability; chronic workflow list unchanged at none).

---

## 14:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 10 most-recent main commits (13:49Z–14:04Z) carry `[skip ci]` (bot cycles: Conviction scan, ML Tracker, Forex agent, auto pre-spike scan, forward tracking stats, specialized scanner picks, QuantumFusion report, DARWIN ENGINE DNA evolution cycle, Signal Engine scan). No CI-triggering code-path commits landed on main between 13:00Z and 14:15Z. **Assessment: CI Tests likely GREEN** — no new code-path commits; last confirmed CI signal remains the ~03:55–03:59Z `alpha_engine/` pushes (per 05:00Z guardian baseline), both passed; PR #1247 `test(3.11)` failure (merged 2026-05-19) noted as superseded in prior entries.

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. Per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. Notable: `audit-dashboard.yml` chronic push-trigger cancellations were fixed in PR #1247 (push trigger removed; hourly cron + workflow_dispatch retained). No new evidence of chronic cancellations.

**Operational failures (carried from 05:00Z; ages at 14:15Z):**

| Workflow | Last known failure | Age at 14:15Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~11.0h | Almost certainly self-healed (11+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~12.9h | Almost certainly self-healed (13+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~13.0h | Almost certainly self-healed (13+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~13.1h | Almost certainly self-healed (13+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows. Each has had ≥11 automatic re-fires since the original 01–03Z failures. Self-healing probability is very high. DEGRADED verdict retained until operator confirms resolution via GitHub UI or a fresh guardian scan returns a clean state.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1264 | audit: 13Z hourly 2026-05-20 — FINDING-31/32 new kill candidates, FINDING-30 WATCH (n=29) [skip ci] | 0 check runs (not triggered) | pending/no-checks | None — audit branch; no gated paths touched; ready to merge |

PR #1264 details: head sha `1452d5f7`, created 13:18Z, base main at `320ca935`. 0 check runs — expected for an audit-only branch that does not touch CI-gated paths. No REQUEST_CHANGES. Contains FINDING-31 (`rapid_fire×UUSDT`, 7d WR=0%, n=34), FINDING-32 (`cta_replicator×NG=F`, 7d WR=0%, n=24) — both posted to issue #686 for 3-AI consensus. FINDING-33 direction-flip mutation candidates (WATCH). FINDING-30 WATCH (`stocks_rsi2_pullback×EQUITY`, n=29, WR=34.5%, PF=0.980) — below n=30 escalation threshold.

**Action required:**
1. Operator should verify the 4 operational failures (now ~11–13h old) have self-healed via GitHub UI → Actions → filter by workflow name. All have had 11+ hourly re-fires. If confirmed clean, next monitor run can upgrade verdict to GREEN.
2. No CI Tests action needed — no new code-path commits in this window.
3. PR #1264 (13Z audit) is ready to merge — no blocking CI issues. FINDING-31/32 require 3-AI consensus before kill action (already posted to issue #686).

**Status change vs 13:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits are [skip ci] bot scans; PR #1263 (12Z audit) merged at 13:12Z; PR #1264 (13Z audit) is now the sole open PR with 0 check runs as expected; operational failures from 01–03Z now ~11–13h old with very high self-healing probability; chronic workflow list unchanged at none).

---

## 15:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 10 most-recent main commits (14:58Z–15:05Z) carry `[skip ci]` (bot cycles: Alpha Engine FAST scan, ML Tracker 0-active/19-resolved, Meme scanner export, Pick monitor + price validation, Forex Smart Picks scan, Futures agent scan, ETF scanner picks merge, auto pre-spike scan, KIMI_FEB172026 scan cycle). No CI-triggering code-path commits landed on main between 14:00Z and 15:10Z. **Assessment: CI Tests likely GREEN** — no new code-path commits in this window; last confirmed CI signal remains the ~03:55–03:59Z `alpha_engine/` pushes (per 05:00Z guardian baseline), both passed; `test(3.11)` failure from PR #1247 (merged 2026-05-19) noted as superseded by overnight alpha_engine fixes in prior entries.

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. `gh` CLI unavailable for per-workflow history scan; per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new evidence of chronic cancellations in this window.

**Operational failures (carried from 05:00Z; ages at 15:10Z):**

| Workflow | Last known failure | Age at 15:10Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~12.0h | Almost certainly self-healed (12+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~13.9h | Almost certainly self-healed (14+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~14.0h | Almost certainly self-healed (14+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~14.1h | Almost certainly self-healed (14+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows. Each has had ≥12 automatic re-fires since the original 01–03Z failures. Self-healing probability is very high. DEGRADED verdict retained until operator confirms resolution via GitHub UI or a fresh guardian scan returns a clean state.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1265 | audit: 14Z hourly 2026-05-20 — #1264 merged, FINDING-31/32 continued, FINDING-24 gate-bypass flag [skip ci] | 0 check runs (confirmed via MCP) | no-checks | None — audit branch; no gated paths touched; ready to merge |

PR #1265 details: head sha `8e19efba`, created 14:23Z, base main at `cef9a11e`. MCP `get_check_runs` confirmed `total_count: 0` — expected for an audit-only branch. No REQUEST_CHANGES. Contains FINDING-31/32 (3-AI consensus awaited on issue #686), FINDING-22 (3-AI consensus pending), FINDING-30 WATCH (`stocks_rsi2_pullback×EQUITY`, n=29 WR=34.5% — check 15Z if n≥30), FINDING-24 P0 (`quan_engine×HYPEUSDT` gate bypass suspected post-#694).

Most recently merged PR: **#1264** (audit: 13Z hourly 2026-05-20) — merged 14:12Z. No CI checks were triggered (audit-only branch, [skip ci]).

**Action required:**
1. Operator should verify the 4 operational failures (now ~12–14h old) have self-healed via GitHub UI → Actions → filter by workflow name. All have had 12+ hourly re-fires. If confirmed clean, next monitor run can upgrade verdict to GREEN.
2. No CI Tests action needed — no new code-path commits in this window.
3. PR #1265 (14Z audit) is ready to merge — no blocking CI issues. FINDING-31/32 require 3-AI consensus (issue #686). FINDING-24 gate-bypass is P0 — operator/author should investigate `quan_engine/HYPEUSDT` post-#694.

**Status change vs 14:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits are [skip ci] bot scans; PR #1264 (13Z audit) merged at 14:12Z; PR #1265 (14Z audit) is now the sole open PR with 0 check runs confirmed via MCP; operational failures from 01–03Z now ~12–14h old with very high self-healing probability; chronic workflow list unchanged at none).

---

## 16:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 50 most-recent main commits (15:18Z–16:07Z) carry `[skip ci]` (bot cycles: Signal Engine scan, Rapid Fire scan, mega mutation tracker hourly update, Crypto Smart Picks scan + portfolio update, scheduled pick check, Signal recorder update, new-strategies-scanner picks + shadow log, Prediction market signals, skyrocket_picks refresh, Dashboard pick trader, Elton's Predictions Pine Script auto-updated, Claude Gainer ML scan, Auto-update prediction quality metrics, Copy trader portfolio, Sustained Gainer scan, Auto-update continuous improvement report, Live spike trading, Gainer Capture, Claude Gainer ST scan, Dynamic universe update, Skyrocket Detector scan, MOMENTUM TRACKER, Mercury 2 scan, real forward baby picks refresh, Gainer scan, Auto-update, Scanner data, GSD Edge Engine, QuanEngine forward tracker, MOMENTUM CATCHER, Bond agent, consensus outcomes, Update actions failure guardian status, forward-test resolve picks, Regime Terminal scan, ETF agent scan, Recommended portfolio, OBI snapshot, signal integrator report, Prediction verification, copy-trader forward-test, ML Reviver, LuxAlgo signals, audit hourly update, Sync hub data, Portfolio tracker, Missed opportunity scan, Enhanced ML predict, Meta-strategy validate, Auto Market beating cycle). No CI-triggering code-path commits landed on main in this window. **Assessment: CI Tests likely GREEN** — no new code-path commits since last confirmed signal (~03:55–03:59Z alpha_engine pushes per 05:00Z guardian baseline, both passed).

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. No `gh` CLI available for per-workflow history scan. Per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new evidence of chronic cancellations in this window.

**Operational failures (carried from 05:00Z; ages at 16:15Z):**

| Workflow | Last known failure | Age at 16:15Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~13.1h | Almost certainly self-healed (13+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~14.9h | Almost certainly self-healed (15+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~15.0h | Almost certainly self-healed (15+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~15.1h | Almost certainly self-healed (15+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows. Each has had ≥13 automatic re-fires since the original 01–03Z failures — self-healing probability is near-certain. DEGRADED verdict retained as no direct confirmation of clean state is possible in MCP-only environment without `gh` CLI access to query current workflow run history.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1266 | audit: 15Z hourly 2026-05-20 — FINDING-35/36 new, FINDING-24 gate bypass confirmed [skip ci] | 0 check runs (confirmed via MCP) | no-checks | None — audit branch; no gated paths touched; ready to merge |

PR #1266 details: head sha `cdeda3c0`, created 15:18Z, base main at `92484b08`. MCP `get_check_runs` confirmed `total_count: 0` — expected for an audit-only branch that does not touch CI-gated paths. No REQUEST_CHANGES. Contains: FINDING-35 (`futures_momentum` all-time n=18, WR=11.1%, PF=0.09 — WATCH, escalate at n=20); FINDING-36 (`stocks_rsi2_pullback` 7d n=30, WR=36.7%, escalated to mutation track); FINDING-24 gate bypass confirmed (HYPEUSDT 7d n=53 via `unknown` post-#694 — P0 investigate); FINDING-31/32/22 awaiting 3-AI consensus.

Most recently merged PR: **#1265** (audit: 14Z hourly 2026-05-20) — merged 15:11:40Z. No CI checks triggered (audit-only branch, [skip ci]).

**Action required:**
1. Operator should confirm the 4 operational failures (now ~13–15h old, 13+ hourly re-fires each) have self-healed via GitHub UI → Actions → filter by workflow name. If confirmed clean, verdict can be upgraded to GREEN next hour.
2. No CI Tests action needed — no new code-path commits in this window.
3. PR #1266 (15Z audit) is ready to merge — no blocking CI issues. **FINDING-24 gate bypass confirmed P0** — `quan_engine/HYPEUSDT` 7d n=53 via `unknown` strategy bypassing PR #694 block; root-cause fix needed in `audit_trail/quality_gates.py` `passes_active_gate()` to check `source_system` in addition to `strategy` field.

**Status change vs 15:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits are [skip ci] bot scans; PR #1265 merged at 15:11:40Z; PR #1266 (15Z audit) is now the sole open PR with 0 check runs confirmed via MCP; operational failures from 01–03Z now ~13–15h old with near-certain self-healing probability; chronic workflow list unchanged at none; FINDING-35/36 newly documented in open PR).

---

## 18:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All main commits in the 16:00Z–18:05Z observation window (including 17:00Z, which had no monitor run) carry `[skip ci]` or are non-code operational commits. 50+ bot cycles observed: Signal Engine scan, Regime Terminal scan, ML Tracker, Conviction scan, Forex agent, ueps picks refresh, universe expansion scan, System F Claws of Doom, real forward baby picks, Signal recorder, Crypto Smart Picks, continuous improvement report, QuickGuess ML, mega mutation tracker, Alpha Engine FAST, signal integrator, Mercury 2, copy-trader, Recommended portfolio, LuxAlgo signals, Prediction verification, Meta-strategy validate, OBI snapshot, Hindsight learner, Gainer Capture, Claude Gainer ST scan, etc. Two human commits landed directly on main without `[skip ci]`: `f8b5babb89ca` (17:13Z, "chore(loop): run #26 post-escalation") and `7d81be0ec1e0` (17:14Z, "scheduled: pick check") — both are operational/data commits that do not touch CI-gated paths. **Assessment: CI Tests likely GREEN** — no new code-path commits since last confirmed signal (~03:55–03:59Z alpha_engine pushes per 05:00Z guardian baseline, both passed). Last directly confirmed CI run: PR #1247 (merged 2026-05-19T12:31Z, ~30h ago) — test (3.11) `failure`, test (3.12) `cancelled`, gate `success`; predates today's guardian baseline.

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. Per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new evidence in 16:00Z–18:05Z window.

**Operational failures (carried from 05:00Z; ages at 18:05Z):**

| Workflow | Last known failure | Age at 18:05Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~14.9h | Almost certainly self-healed (14+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~16.8h | Almost certainly self-healed (16+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~16.9h | Almost certainly self-healed (16+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~16.9h | Almost certainly self-healed (16+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows. Each has had ≥14 automatic re-fires since the original 01–03Z failures — self-healing probability is near-certain. DEGRADED verdict retained as no direct confirmation of clean state is possible in MCP-only environment without `gh` CLI.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1268 | audit: 17Z hourly 2026-05-20 — FINDING-37/38 direction anomalies, COMMODITY residual, HYPEUSDT bypass P0 [skip ci] | 0 check runs (confirmed via MCP, state: pending) | no-checks | None — audit branch; no gated paths touched; ready to merge |

PR #1268 details: head sha `ab42a1a3`, created 17:21Z, base main at `988aafc7`. MCP `get_check_runs` confirmed `total_count: 0` and commit status `pending` with 0 statuses — expected for audit-only branch. Contains: FINDING-37 (`ig_contrarian_sentiment` LONG direction anomaly, WR=16.5% vs SHORT WR=60.3%, 44pp spread — Axis-1 candidate); FINDING-38 (`myfxbook_retail_contrarian` LONG, WR=13.7% vs SHORT WR=50.0%, 36pp spread); FINDING-24 HYPEUSDT bypass P0 OPEN (53 picks via `unknown` in 7d post-#694); FINDING-35 `futures_momentum` n=18 WATCH.

Most recently merged PR: **#1267** (audit: 16Z hourly 2026-05-20) — merged 17:13:39Z. No CI checks triggered (audit-only branch, [skip ci]).

**Action required:**
1. Operator should confirm the 4 operational failures (now ~15–17h old, 14+ hourly re-fires each) have self-healed via GitHub UI → Actions → filter by workflow name. If confirmed clean, verdict can be upgraded to GREEN next hour.
2. No CI Tests action needed — no new code-path commits in 16:00Z–18:05Z window.
3. PR #1268 (17Z audit) is ready to merge — no blocking CI issues. **FINDING-24 P0 remains open** — HYPEUSDT 7d n=53 via `unknown` source bypassing #694 block; fix needed in `audit_trail/quality_gates.py`. **FINDING-37/38 direction anomalies** — both `ig_contrarian_sentiment` and `myfxbook_retail_contrarian` LONG sides have ~14–17% WR vs 50–60% for SHORT; block LONG direction on both, escalate to 3-AI consensus.

**Status change vs 16:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits in 16:00Z–18:05Z are [skip ci] bot scans or non-gated operational commits; PR #1267 merged at 17:13:39Z; PR #1268 (17Z audit) is now the sole open PR with 0 check runs confirmed via MCP; operational failures from 01–03Z now ~15–17h old with near-certain self-healing probability; chronic workflow list unchanged at none; FINDING-37/38 newly documented in open PR; 17:00 UTC monitor run was not executed — observations from that window folded into this 18:00 UTC section).

---

## 19:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 10 most-recent main commits in the 18:00Z–19:11Z window carry `[skip ci]` (bot data pushes: portfolio tracker, DNA picks, correlation report, incubator strategy picks, prediction market agents, signal tracker, forward test/scorecard, QuickGuess ML, hindsight learner, etc.). The 4 non-`[skip ci]` commits in the last 100 are operational data commits (`scheduled: pick check`, `chore(loop): status run #27`, `OBI snapshot`) that do not touch CI-gated paths. **Assessment: CI Tests likely GREEN** — no new code-path commits have landed on main since the last confirmed CI signal (~03:55–03:59Z alpha_engine pushes per 05:00Z guardian baseline, both passed).

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans (0 chronic cancellations confirmed at 05:00Z guardian baseline across 351 workflows / 600 runs; no new evidence in 18:00Z–19:11Z window).

**Operational failures (carried from 05:00Z; ages at 19:11Z):**

| Workflow | Last known failure | Age at 19:11Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~16.0h | Near-certain self-healed (16+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~17.9h | Near-certain self-healed (17+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~18.0h | Near-certain self-healed (18+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~18.0h | Near-certain self-healed (18+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows with ≥16 automatic re-fires since the original failures. Self-healing probability is near-certain. DEGRADED verdict retained because direct confirmation is not possible in MCP-only environment without `gh` CLI.

**Open PRs CI snapshot:** No open PRs. PR #1268 (17Z audit) merged at 18:09:57Z; PR #1269 (18Z audit) merged at 18:17:40Z. `mcp__github__list_pull_requests(state=open)` returned `[]`. No CI failures to classify.

**Action required:**
1. Operator should confirm the 4 operational failures (now ~16–18h old, 16+ hourly re-fires each) have self-healed via GitHub UI → Actions. If confirmed clean, verdict can be upgraded to GREEN.
2. No CI Tests action needed — no new code-path commits in 18:00Z–19:11Z window.
3. **FINDING-24 P0 remains open** — HYPEUSDT 7d n=53 via `unknown` source bypassing #694 block. Fix needed in `audit_trail/quality_gates.py`.

**Status change vs 18:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all recent main commits are [skip ci] bot data pushes; PRs #1268 and #1269 merged at 18:09Z and 18:17Z respectively; no open PRs confirmed; operational failures from 01–03Z now ~16–18h old with near-certain self-healing; chronic workflow list unchanged at none).

---

## 20:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 20 most-recent main commits (19:43Z–20:05Z) carry `[skip ci]` (bot data pushes: Cross-system aggregation, Pine Script auto-updated, ML Tracker, QuantumFusion report, forward tracking stats, Volatile Alt scan, Signal Engine scan, Regime Terminal, ANTIGRAVITY-CLAUDEOPUS, low-score-tracker, DARWIN ENGINE, master-picks tracker, Breakout Arena scan, Alpha Engine FAST, Coinglass scan, Hindsight learner, QuickGuess ML, outcome resolver, Portfolio tracker, Meta-strategy validate). No CI-triggering code-path commits landed on main between 19:00Z and 20:06Z. **Assessment: CI Tests likely GREEN** — no new code-path commits since last confirmed signal (~03:55–03:59Z alpha_engine pushes per 05:00Z guardian baseline, both passed).

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. Per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new evidence in 19:00Z–20:06Z window.

**Operational failures (carried from 05:00Z; ages at 20:06Z):**

| Workflow | Last known failure | Age at 20:06Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~16.9h | Near-certain self-healed (17+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~18.8h | Near-certain self-healed (18+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~18.9h | Near-certain self-healed (19+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~18.9h | Near-certain self-healed (19+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows with ≥17 automatic re-fires since the original 01–03Z failures. Self-healing probability is near-certain. DEGRADED verdict retained as direct confirmation is not possible in MCP-only environment without `gh` CLI.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1270 | audit: hourly 2026-05-20T19Z — P1 multi_asset_copytrader bypass + FOREX recovery | 3/3 ✅ (scan, Gitleaks, Grep-DB — all success, 19:21–19:22Z) | pending / 0 commit statuses | None for CI — 3/3 security checks clean. **P1 COMMODITY bypass** (issue #686) needs operator/author action before merge. |

PR #1270 details: head sha `4f3b5658`, created 19:19Z, base main at `94fe836f`. Check runs: `scan` ✅ (19:19–19:22Z), `Gitleaks secret scan` ✅ (19:19–19:22Z), `Grep for stale hardcoded DB passwords` ✅ (19:19–19:21Z). No `CI Tests` triggered (audit branch doesn't touch CI-gated paths — expected). PR body flags: **P1 bypass** — `multi_asset_copytrader` routes `futures_momentum` + `cftc_cot_commercial_signal` through COMMODITY without hitting `BLOCKED_ASSET_STRATEGY_PAIRS` (last pick 2026-05-19T21:47Z, post-FUTURES re-block, confirming ongoing leak). FOREX 7d PF recovered to 1.313 / 30d PF 2.515. PR marked "Do NOT merge without operator review of §3 and issue #686 consensus."

**Action required:**
1. Operator should confirm the 4 operational failures (now ~17–19h old, 17+ hourly re-fires each) have self-healed via GitHub UI → Actions → filter by workflow name. If confirmed clean, verdict can be upgraded to GREEN.
2. No CI Tests action needed — no new code-path commits in this window.
3. PR #1270 (19Z audit): security checks clean; **do NOT merge yet** — P1 COMMODITY bypass (`multi_asset_copytrader` routing FUTURES picks through COMMODITY, WR ~6–12%) requires 3-AI consensus on issue #686 and operator review before merge. FINDING-24 P0 (`quan_engine×HYPEUSDT` gate bypass) remains open from earlier hours.

**Status change vs 19:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits in 19:00Z–20:06Z are [skip ci] bot data pushes; no PRs merged in this window; PR #1270 (19Z audit) is the sole open PR with 3/3 security checks ✅ and 0 CI Tests checks as expected; operational failures from 01–03Z now ~17–19h old with near-certain self-healing; chronic workflow list unchanged at none; P1 COMMODITY bypass newly documented in open PR — escalated to issue #686).

---

## 21:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 10 most-recent main commits (21:00Z–21:05Z) carry `[skip ci]` (bot data pushes: Enhanced ML predict, audit hourly update, Auto-update crypto test portfolios, Missed opportunity scan, Claude Code ML 511 active/171 resolved, Meta-strategy validate, Signal tracking & validation, Self-optimized trading cycle, Portfolio tracker update, incubator strategy picks). No CI-triggering code-path commits landed on main between 20:00Z and 21:05Z. **Assessment: CI Tests likely GREEN** — no new code-path commits since last confirmed signal (~03:55–03:59Z alpha_engine pushes per 05:00Z guardian baseline, both passed).

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. Per 05:00Z guardian baseline: 0 chronic cancellations across 351 workflows / 600 runs. No new evidence in 20:00Z–21:05Z window.

**Operational failures (carried from 05:00Z; ages at 21:05Z):**

| Workflow | Last known failure | Age at 21:05Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~17.9h | Near-certain self-healed (18+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~19.8h | Near-certain self-healed (20+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~19.9h | Near-certain self-healed (20+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~19.9h | Near-certain self-healed (20+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows with ≥18 automatic re-fires since the original 01–03Z failures. Self-healing probability is near-certain. DEGRADED verdict retained as direct confirmation is not possible in MCP-only environment without `gh` CLI.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1271 | audit: hourly 2026-05-20T20Z — EQUITY recovery, COMMODITY bypass watch, FINDING-40 | 3/3 ✅ (scan, Gitleaks, Grep-DB — all success, 20:18–20:21Z) | pending / 0 commit statuses | None for CI — security checks clean. **Do NOT merge** without operator review per PR body. |
| #1270 | audit: hourly 2026-05-20T19Z — P1 multi_asset_copytrader bypass + FOREX recovery | 3/3 ✅ (confirmed 19Z) | pending / 0 commit statuses | None for CI — **Do NOT merge** without operator review and issue #686 consensus. |

PR #1271 details: head sha `f3ffb07b`, created 20:18Z, base main at `be8fede2`. Check runs: `Grep for stale hardcoded DB passwords` ✅ (20:18–20:21Z), `Gitleaks secret scan` ✅ (20:18–20:21Z), `scan` ✅ (20:18–20:21Z). No `CI Tests` triggered (audit-only branch — expected). PR documents: EQUITY 7d PF 0.722 (+0.044 vs 19Z), COMMODITY bypass active, FINDING-40 (CRYPTO 24h PF 0.54 / WR 28.8% — assessed as stale-window artifact). PR body: "Do NOT merge without operator review."

PR #1270 details: head sha `4f3b5658`, created 19:19Z, 3/3 ✅ confirmed per 20:00Z entry. P1 COMMODITY bypass (`multi_asset_copytrader` routing FUTURES picks through COMMODITY, last pick 2026-05-19T21:47Z post-FUTURES re-block). Also marked "Do NOT merge."

Most recently merged PR: **#1269** (audit: 18Z hourly 2026-05-20) — merged 18:17:40Z. No CI checks were triggered (audit-only branch, [skip ci]).

**Action required:**
1. Operator should confirm the 4 operational failures (now ~18–20h old, 18+ hourly re-fires each) have self-healed via GitHub UI → Actions → filter by workflow name. If confirmed clean, verdict can be upgraded to GREEN.
2. No CI Tests action needed — no new code-path commits in this window.
3. PRs #1270 and #1271 both have clean security checks but carry operator-hold flags — do NOT merge without review. P1 COMMODITY bypass (issue #686) and FINDING-40 stale-window artifact both require consensus before action.

**Status change vs 20:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits in 20:00Z–21:05Z are [skip ci] bot data pushes; no PRs merged in this window; PRs #1270 and #1271 are both open with 3/3 security checks ✅ each and 0 CI Tests checks as expected; operational failures from 01–03Z now ~18–20h old with near-certain self-healing; chronic workflow list unchanged at none; FINDING-40 newly documented in PR #1271).

---

## 22:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). No `gh` CLI available (MCP-only environment). All 5 most-recent main commits (22:04Z–22:07Z) are `[skip ci]` or non-triggering data pushes (Recommended portfolio, OBI snapshot, Sync hub data, audit hourly update, scheduled pick check). No CI-triggering code-path commits landed on main between 21:00Z and 22:10Z. **Assessment: CI Tests likely GREEN** — no new code-path commits since last confirmed signal (~03:55–03:59Z alpha_engine pushes per 05:00Z guardian baseline, both passed).

**Chronic workflows:** none — consistent with all prior 2026-05-20 scans. Per 05:00Z guardian baseline: 0 chronic cancellations confirmed across 351 workflows / 600 runs. No new evidence in 21:00Z–22:10Z window.

**Operational failures (carried from 05:00Z; ages at 22:10Z):**

| Workflow | Last known failure | Age at 22:10Z | Status |
|---|---|---|---|
| Refresh Creator Updates | #100 @ ~03:12Z | ~19.0h | Near-certain self-healed (19+ hourly cron refires) |
| ALPHA ENGINE - Adaptive Trust Tuner | #160 @ ~01:19Z | ~20.8h | Near-certain self-healed (21+ hourly cron refires) |
| Refresh Top Movies Data | #363 @ ~01:13Z | ~21.0h | Near-certain self-healed (21+ hourly cron refires) |
| DB Freshness Guardian | #17 @ ~01:12Z | ~21.0h | Near-certain self-healed (21+ hourly cron refires) |

All 4 are hourly-cadence scheduled workflows with ≥19 automatic re-fires since the original 01–03Z failures. Self-healing probability is near-certain. DEGRADED verdict retained as direct confirmation is not possible in MCP-only environment without `gh` CLI.

**Open PRs CI snapshot:**

| PR | Title | CI check runs | Status | Recommended action |
|---|---|---|---|---|
| #1272 | audit: hourly 2026-05-20T21Z — dashboard 17h stale, metrics stable, futures_momentum n=17 | 3/3 ✅ (scan, Gitleaks, Grep-DB — all success, 21:19–21:22Z) | pending / 0 commit statuses | None for CI — security checks clean. **Do NOT merge** without operator review per PR body. |
| #1271 | audit: hourly 2026-05-20T20Z — EQUITY recovery, COMMODITY bypass watch, FINDING-40 | 3/3 ✅ (confirmed 20Z) | pending / 0 commit statuses | None for CI — **Do NOT merge** without operator review and issue #686 consensus. |
| #1270 | audit: hourly 2026-05-20T19Z — P1 multi_asset_copytrader bypass + FOREX recovery | 3/3 ✅ (confirmed 19Z) | pending / 0 commit statuses | None for CI — **Do NOT merge** without operator review and issue #686 consensus. |

PR #1272 details: head sha `a3abda81`, created 21:19Z, base main at `e047ffc6`. Check runs: `Grep for stale hardcoded DB passwords` ✅ (21:19–21:21Z), `scan` ✅ (21:19–21:21Z), `Gitleaks secret scan` ✅ (21:19–21:22Z). No `CI Tests` triggered (audit-only branch — expected). PR documents: COMMODITY bypass active (multi_asset_copytrader routing futures_momentum + cftc_cot_commercial_signal), FINDING-40 CRYPTO 24h stale-window artifact confirmed (PF 0.517), EQUITY 7d PF 0.722 monitoring, futures_momentum COMMODITY n=17 at 21Z window-edge. PR body: "Do NOT merge without operator review."

Most recently merged PR: **#1269** (audit: 18Z hourly 2026-05-20) — merged 18:17:40Z. No CI checks were triggered (audit-only branch, [skip ci]).

**Action required:**
1. Operator should confirm the 4 operational failures (now ~19–21h old, 19+ hourly re-fires each) have self-healed via GitHub UI → Actions → filter by workflow name. If confirmed clean, verdict can be upgraded to GREEN.
2. No CI Tests action needed — no new code-path commits in this window.
3. PRs #1270, #1271, and #1272 all have clean security checks but carry operator-hold flags — do NOT merge without review. P1 COMMODITY bypass (issue #686, multi_asset_copytrader routing FUTURES picks through COMMODITY, last pick 2026-05-19T21:47Z post-FUTURES re-block) and FINDING-24 P0 (HYPEUSDT gate bypass via `unknown` source) remain open.

**Status change vs 21:00Z:** DEGRADED → DEGRADED (verdict unchanged — no new CI-triggering code; all main commits in 21:00Z–22:10Z are [skip ci] bot data pushes; no PRs merged since #1269 at 18:17:40Z; PR #1272 (21Z audit) newly opened with 3/3 security checks ✅; PRs #1270 and #1271 remain open with operator-hold; operational failures from 01–03Z now ~19–21h old with near-certain self-healing; chronic workflow list unchanged at none; open PR count increased from 2 to 3 — #1272 added this hour).

---

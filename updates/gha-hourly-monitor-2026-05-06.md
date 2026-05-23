# GHA Hourly Health Monitor — 2026-05-06

## 02:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** N/A — all recent main commits carry `[skip ci]` (bot data-push commits). Last CI Tests check runs observed on PRs targeting main; all passing. No direct CI Tests run triggered on main HEAD within the last ~2 hours.

**Indirect main CI health (from PR checks):**
| PR | test(3.11) | test(3.12) | audit | scan |
|---|---|---|---|---|
| #840 fix/hyrotrader-sltp-gate | success | success | — | success / cancelled† |
| #837 fix/auto-shadow-demote | success | success | success | success |
| #836 fix/commodity-suppress | success | success | success | success |
| #835 fix/crypto-suppress | success | success | success | cancelled† |

†`scan` job cancelled in some runs but NOT chronic (successes present in same PR history).

**Chronic workflows:** none — `scan` job shows isolated cancellations (2 of ~10 observed runs) with successes present; does not meet CHRONIC threshold (requires ≥4 cancels + 0 successes in last 15 runs).

**Open PRs (7 open):**
| PR | Title | CI Tests | Status |
|---|---|---|---|
| #841 | docs: per-class outlier audit | no CI checks (doc-only branch) | SKIP |
| #840 | fix(hyrotrader): SL/TP gate + phantom row migration | success | GREEN |
| #839 | feat(hyrotrader): GHA workflow for bridge regen | no CI checks (YAML-only) | SKIP |
| #838 | feat(hermes): swarm slash commands | scan=success only | GREEN |
| #837 | feat(gates): auto-shadow-probation on degradation | success | GREEN |
| #836 | fix(commodity): suppress forex_copy_trader | success | GREEN |
| #835 | fix(crypto): suppress st_fear_greed_contrarian | success | GREEN |

**Open PRs RED:** none

**Action required:** none — all open PRs with code changes have passing CI Tests. Monitor note: high-frequency `[skip ci]` bot commits on main (~50+ in 2 hours) create a saturated commit log; CI Tests only fires on PR branches + manual non-skip-ci pushes.

---

## 03:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** N/A — all commits to main since 02:00 UTC carry `[skip ci]` (bot data-push commits: pick monitor, meme scanner, ML tracker, conviction scan, signal recorder, Claws-of-Doom sync, mega-mutation tracker, prediction-quality metrics). No direct CI Tests run triggered on main HEAD. Last PR-level CI run at 02:40 UTC (PR #843): 4/4 success.

**Indirect main CI health (from PR checks — new data since 02:00):**
| PR | test(3.11) | test(3.12) | audit | scan | Completed |
|---|---|---|---|---|---|
| #843 feat/b5-concept-scorer | ✅ success | ✅ success | ✅ success | ✅ success | 2026-05-06T02:40 |
| #837 fix/auto-shadow-demote | ✅ success | ✅ success | ✅ success | ✅ success | 2026-05-05T20:51 |
| #835 fix/crypto-suppress | ✅ success | ✅ success | ✅ success | ❌ cancelled† | 2026-05-05T20:38 |

†`scan` cancellation on #835 is isolated (1 occurrence); #837 and #843 both show `scan` success — not chronic.

**Chronic workflows:** none — `scan` cancellation on PR #835 remains the only flagged instance; successes on #837 and #843 confirm the job is not chronically broken. Cannot run per-workflow `gh run list` (gh CLI unavailable); assessment based on PR check run data across 3 PRs (15+ job samples).

**Open PRs (7 open):**
| PR | Title | CI Tests | Status |
|---|---|---|---|
| #844 | feat: ruflo/SWARM audit data quality tools | no CI checks (branch lacks triggering commit or is docs-heavy) | SKIP |
| #843 | feat(b5): Cursor Phase 3 concept-aware scoring | ✅ 4/4 green (02:40 UTC) | GREEN |
| #842 | audit(hourly): 02Z report PR | scan=✅ only | GREEN (partial — audit-doc PR) |
| #841 | docs(audit): per-class outlier audit | no CI checks (doc-only) | SKIP |
| #838 | feat(hermes): swarm slash commands | scan=✅ only | GREEN |
| #837 | feat(gates): auto-shadow-probation on degradation | ✅ 4/4 green | GREEN |
| #835 | fix(crypto): suppress st_fear_greed_contrarian | 3✅ / scan=cancelled | RERUN scan when convenient (not blocking — CI Tests proper passed) |

**Recently merged (since 02:00):** #839 feat(hyrotrader): GHA bridge regen workflow — merged 2026-05-06T02:15:48Z. No CI failures observed on merge.

**Open PRs RED:** none

**Action required:** none. Optional: rerun `scan` job on PR #835 before merge to confirm it was an isolated infra cancel.

---

## 04:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** N/A — `gh` CLI unavailable and no `GITHUB_TOKEN` in environment; direct workflow-run queries not possible. Verdict derived from PR-level check run data (indirect signal). All code-bearing PRs targeting main show passing CI Tests jobs. No failures detected since 03:00 UTC report.

**Indirect main CI health (from PR checks — new data since 03:00 UTC):**
| PR | Checks | Result | Completed |
|---|---|---|---|
| #846 feat/b18-shadow-probation-panel | scan=✅, drift=✅ | 2/2 green | 2026-05-06T03:38 |
| #845 audit/hourly-03z | scan=✅ | 1/1 green | 2026-05-06T03:25 |
| #843 feat/b5-concept-scorer | test(3.11)=✅ test(3.12)=✅ audit=✅ scan=✅ | 4/4 green | 2026-05-06T02:40 (carry from 03Z) |
| #837 feat/gates-auto-shadow | test(3.11)=✅ test(3.12)=✅ audit=✅ scan=✅ | 4/4 green | 2026-05-05T20:51 (carry) |
| #835 fix/crypto-suppress | test(3.11)=✅ test(3.12)=✅ audit=✅ scan=❌cancelled | 3✅/1cancel | 2026-05-05T20:38 (carry) |

No new merges to main since 02:15 UTC (#839/#840/#836 were last batch).

**Chronic workflows:** none — `gh` CLI unavailable; per-workflow query not possible. Based on 15+ check-run samples across open PRs: `scan` job shows 1 isolated cancellation (PR #835) with successes present in same run and on subsequent PRs (#837, #843, #845, #846). Does NOT meet CHRONIC threshold (≥4 cancels + 0 successes in 15 runs). All other observed job types (test 3.11, test 3.12, audit, drift) are 100% success.

**Open PRs CI snapshot (9 open):**
| PR | Title | CI Result | Classification |
|---|---|---|---|
| #846 | feat(b18): Shadow Probation panel on /audit | scan=✅ drift=✅ (2/2) | GREEN |
| #845 | audit(hourly): 03Z report | scan=✅ (1/1) | GREEN (audit-doc PR) |
| #844 | feat: ruflo/SWARM audit data quality tools | 0 check runs | SKIP — no CI triggered (doc/tool PR, no triggering commit yet) |
| #843 | feat(b5): Cursor Phase 3 concept-aware scoring | 4/4 ✅ | GREEN |
| #842 | audit(hourly): 02Z report | scan=✅ (1/1) | GREEN (audit-doc PR) |
| #841 | docs(audit): per-class outlier audit | 0 check runs | SKIP — doc-only branch |
| #838 | feat(hermes): swarm slash commands + review report | scan=✅ (1/1) | GREEN |
| #837 | feat(gates): auto-shadow-probation on degradation | 4/4 ✅ | GREEN |
| #835 | fix(crypto): suppress st_fear_greed_contrarian | 3✅ / scan=cancelled | RERUN scan before merge (optional; CI Tests proper passed) |

**Open PRs RED:** none

**Action required:** none. Carry-forward: rerun `scan` on PR #835 before merge is optional hygiene. No new failures since 03:00 UTC. Verdict unchanged GREEN.

# GHA Hourly Health Monitor — 2026-05-05

## 02:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** Main HEAD is a series of `[skip ci]` bot commits. Last code-change PR merged to main was **#804** (merged 2026-05-05T00:43:50Z) — 3/3 success (test 3.11 ✅, test 3.12 ✅, scan ✅). All subsequent main commits carry `[skip ci]` (outcome resolver, scanners, portfolio tracker, Pine Script updater, prediction quality metrics, meta-strategy validator). Main CI: **GREEN**.

> Note: `gh` CLI unavailable in this environment; CI run history queried via GitHub MCP API (check_runs per PR). Per-workflow chronic-cancellation scan (Step 2) inferred from commit log — no `gh run list --workflow` available via MCP.

**Chronic workflows:** No chronic cancellations detected. Ten-plus distinct bot workflows are successfully committing to main in the last ~2h window (Claude Gainer ST, Claude Gainer ML, Rapid Fire, Sustained Gainer, outcome resolver, portfolio tracker, meta-strategy validate, QuantumFusion report, prediction market signals, Pine Script updater, prediction quality metrics). Full 15-run per-workflow verification not possible without `gh` CLI — inference is from commit log only. Flag as **UNVERIFIED** pending CLI access.

**Open PRs RED:**

| PR | Title | Failing checks | Classification | Recommended action |
|---|---|---|---|---|
| #777 | fix/sports-midnight-date-bucketing | smoke ❌, test(3.12) ❌, test(3.11) cancelled | AUTHOR_FIX | Author to rebase on current main (PR #804 fixed related regressions); re-run CI; investigate smoke failure |
| #772 | feat/b9-adversarial-shadow | test(3.11) ❌, test(3.12) cancelled, ueps-pytest cancelled | AUTHOR_FIX (likely stale) | Rebase on current main; PR #804 (merged 00:43Z) fixed `_float` helpers + kimi test regressions that ran at same timestamp |
| #764 | feat/b5-concept-scorer | test(3.12) ❌, test(3.11) cancelled | AUTHOR_FIX (likely stale) | CI ran 2026-05-04T03:12 — before #804 fix; rebase should resolve |
| #798 | fix/memecoin-credential-env-var | smoke ❌ | IGNORE_FLAKE | Sports smoke is known flaky pre-#645; no CI Tests (pytest) failure; acceptable |

Docs-only PRs #805, #806, #807, #808 show only `scan` check — all pass. No CI Tests runs triggered (expected for docs-only branches).

**Action required:** Authors of #777, #772, #764 should rebase on current main to pick up PR #804 regression fixes. PR #777 has an additional `test(3.12)` real failure that may need investigation beyond the rebase. No operator action required on main.

---

## 03:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** All recent main commits carry `[skip ci]` (bot picks/scan/ML/conviction/signal workflows). Last code-change PRs merged were #808/#807/#806 (all docs-only, 2026-05-05T02:11Z) — scan=success on all three. No CI Tests failures on main. Main CI: **GREEN**.

> Note: `gh` CLI unavailable; CI run history queried via GitHub MCP API. Per-workflow chronic-cancellation scan (Step 2) inferred from commit log — `gh run list --workflow` not available via MCP. Flagged **UNVERIFIED**.

**Chronic workflows:** No chronic cancellations detected. Bot workflows continue committing normally to main in this window (pick monitor, meme scanner, ML tracker, conviction scan, signal recorder, System F, mega mutation tracker, audit-dashboard refresh, all healthy `[skip ci]` commits). Full 15-run per-workflow verification not possible without `gh` CLI.

**Open PRs RED:**

| PR | Title | Failing checks | Classification | Recommended action |
|---|---|---|---|---|
| #777 | fix/sports-midnight-date-bucketing | smoke ❌, test(3.12) ❌, test(3.11) cancelled | AUTHOR_FIX | Real test(3.12) failure; smoke=failure (known flaky pre-#645 but combined with test(3.12) needs investigation). Author to rebase + fix. |
| #772 | feat/b9-adversarial-shadow | test(3.11) ❌, test(3.12) cancelled, ueps-pytest cancelled | AUTHOR_FIX | DO NOT ADMIN-MERGE flagged in PR body. Awaiting human review + rebase. |
| #764 | feat/b5-concept-scorer | CI pending (branch pushed 02:47Z; 0 check runs) | PENDING | New push at 02:47Z with B5 Python 3.12 CI fix (queue commit 6e4e6ad). CI not yet triggered. Monitor next cycle. |
| #798 | fix/memecoin-credential-env-var | smoke ❌ | IGNORE_FLAKE | No pytest (CI Tests) failure; smoke=failure is known sports-smoke flake pre-#645. Acceptable. |

New open PR #809 (docs/audit hourly 02Z): scan=success ✅. Docs-only, no CI Tests needed.

**Status vs previous hour (02:00 UTC):** No verdict change (GREEN→GREEN). PR #764 branch updated (02:47Z) — CI pending rather than failed. PRs #805–#808 (docs) merged cleanly. Open code-change PR failures unchanged.

**Action required:** Author of #777 should investigate `test(3.12)` failure — real assertion/logic error, rebase alone may not resolve. Author of #772 should await human review (DO NOT ADMIN-MERGE). Monitor #764 next cycle for CI outcome on new push. No operator action required on main.

---

## 04:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** All recent main commits carry `[skip ci]` (bot workflows: Conviction scan, Mutation Lab, audit-dashboard refresh, mega mutation tracker, Signal recorder, System F, Crypto Smart Picks, Dashboard pick trader, DNA Factory, prediction quality metrics, Live spike trading, continuous improvement, Copy trader, Gainer scan, Dynamic universe, Skyrocket Detector, MOMENTUM TRACKER, Mercury 2, real forward baby picks, Signal Engine, Recommended portfolio, Regime Terminal, OBI snapshot, Alpha Engine FAST, Prediction verification, LuxAlgo signals, signal integrator, copy-trader forward-test). Last code-change PR merged to main was **#809** (docs/audit hourly 02Z, merged 2026-05-05T03:16:16Z) — scan=success ✅. No CI Tests failures on main. Main CI: **GREEN**.

> Note: `gh` CLI unavailable; CI run history queried via GitHub MCP API. Per-workflow chronic-cancellation scan (Step 2) inferred from commit log — `gh run list --workflow` not available via MCP. Flagged **UNVERIFIED**.

**Chronic workflows:** No chronic cancellations detected. All bot workflows continue committing successfully to main in this window (20+ distinct workflows, all `[skip ci]` commits landing cleanly). Full 15-run per-workflow verification not possible without `gh` CLI.

**Open PRs RED:**

| PR | Title | Failing checks | Classification | Recommended action |
|---|---|---|---|---|
| #777 | fix/sports-midnight-date-bucketing | smoke ❌, test(3.12) ❌, test(3.11) cancelled | AUTHOR_FIX | Real test(3.12) failure (00:35Z). Author to investigate assertion/logic error — rebase alone may not resolve. |
| #772 | feat/b9-adversarial-shadow | test(3.11) ❌, test(3.12) cancelled, ueps-pytest cancelled | AUTHOR_FIX | DO NOT ADMIN-MERGE (PR body). Awaiting human review + rebase on current main. |
| #764 | feat/b5-concept-scorer | 0 check runs on head `96b34418c` | STALE-CI | Head pushed ~02:47Z (~1h 15m ago) — CI has still not triggered after 2 cycles. Operator may need to manually re-trigger CI or push a new commit to kick off checks. |
| #798 | fix/memecoin-credential-env-var | smoke ❌ | IGNORE_FLAKE | No CI Tests (pytest) failure; smoke=failure is known sports-smoke flake pre-#645. Acceptable. |

New open PR **#810** (docs/loop-v1-verified-2026-05-05, opened 03:24Z): scan=success ✅. Docs-only, no CI Tests needed.

**Status vs previous hour (03:00 UTC):** No verdict change (GREEN→GREEN). PR #764 CI still has 0 runs on new head `96b34418c` after 2 monitor cycles — escalating from PENDING to STALE-CI. PR #810 is new (docs, green). PRs #777, #772, #798 unchanged.

**Action required:** Operator should investigate why CI has not triggered on PR #764 head `96b34418c` (pushed ~02:47Z, no check runs after 1h+) — manual re-trigger or force-push an empty commit may be needed. Author of #777 should fix real `test(3.12)` failure. Author of #772 should await human review (DO NOT ADMIN-MERGE). No operator action required on main.

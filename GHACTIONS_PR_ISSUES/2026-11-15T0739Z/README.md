# GH Actions / PRs / Issues — Full Review + Profitability Check

**Date:** 2026-11-15T0739Z
**Scope:** All GitHub Actions workflows, 35 open PRs, 49 open issues, plus the `WIRED_IN/` research tree and last 24–48h of `main` commits.
**Question answered:** What is happening in this repo, what must be fixed/enhanced, and are we on the right track to profitability?

## Files in this folder

| File | What it covers |
|---|---|
| `01_github_actions_audit.md` | Workflow inventory (381 files), the recurring failing workflows, and their root causes |
| `02_open_prs_triage.md` | All 35 open PRs, triaged (merge / rebase / review / close) |
| `03_open_issues_triage.md` | All 49 open issues, triaged (spam / real bugs / security debt) |
| `04_fix_and_enhance_plan.md` | Prioritized P0/P1/P2 fix + enhancement plan with concrete steps |
| `05_profitability_review.md` | Verdict on whether the `WIRED_IN/` + recent `main` work is on the right track to profitability |

## Executive summary

### CI is generating more noise than signal
- **381 files in `.github/workflows/`** — 362 active YAML workflows, 16 disabled/retired/draft, and 3 stray `.md` notes. This is far too many to reason about; most are near-duplicates or superseded.
- **Four workflows fail on a loop**: `Backup Restore Verification`, `Sports endpoint smoke + Playwright`, `QA Market Validation`, and `CI Tests`. Two of them ("sports smoke", "QA validation") already have a fix staged in open PR **#786**. `CI Tests` has 8 real test regressions. `backup-verify` is *architecturally broken* (checks a gitignored file) **and** spams a new issue on every failure.
- **Issue spam is out of control**: 42 of 49 open issues are auto-generated `[backup-verify] Restore check FAILED` noise from that one broken workflow.

### Profitability: not proven, but the process is now honest
- The `WIRED_IN/` tree (~21 timestamped folders of parallel agent research) converges on a single negative truth: **no active strategy is proven to beat buy-and-hold after costs.** Zero strategies pass the 10-gate proof protocol.
- The only candidate worth a forward test is **BTC `sma200` trend** (CAGR 58.6% vs 51.0% hold, Sharpe 1.10 vs 0.93, but DSR 0.84 — not statistically proven, single asset, one cycle).
- The forward-testing leg (`tools/forward_tracker.py`) is the **best-built part** and is the right track for proving anything — but it has **zero live trades** and one bug (excess return is measured **gross** of fees).
- The honest deployable conclusion today: **passive beta only** (FXAIX/SWTSX, 60/40) until BTC sma200 passes the forward test.

## Quick action list (what to do first)

1. **Merge PR #713** (`fix(ci): backup-verify false failures + issue spam`) — kills the 42-issue spam and the broken check. *(P0)*
2. **Merge PR #786** (`fix(ci): restore QA price validation, snapshot pushes, sports smoke`) — after confirming the 5 quote-chain secrets are actually set on the repo. *(P0)*
3. **Fix the 8 failing `CI Tests`** — `passes_active_gate()` regression in `test_m097_book_direction_conflict.py` + `test_dashboard_generator.py`. *(P0)*
4. **Close the 42 backup-verify spam issues** (dedup: close all but the canonical one). *(P1)*
5. **Triage the 35 open PRs** — merge ~4 actionable, rebase 1, close ~20 stale June–Oct PRs. *(P1)*
6. **Fix the gross-vs-net excess-return bug** in `tools/forward_tracker.py` / `pick_excess.py` before trusting any forward result. *(P0 for profitability)*
7. **Act on 5 open secret-rotation reminders** (Aug–Nov 2026) — security debt. *(P1)*

Details and exact file/line references are in the numbered files.

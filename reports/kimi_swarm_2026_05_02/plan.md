# Plan: Continue from Session Boundary — PR #687 Merged + Live Audit Complete

## Stage 1 — Audit Completion ✅
- PR #687 merged (JPY-cross BUY rule fix)
- Live-data per-asset audit performed on dashboard_data.json (n=3500)
- What-if analysis shows FOREX improvement post-#687 is partial (PF 0.14→0.42 in 7d), not sufficient
- Key finding: `forex_carry_momentum` is structurally broken (PF 0.02, 39% of FOREX volume)
- Key finding: `goldmine_6x_consensus` has 0% WR across 30d (n=16)
- Key finding: CRYPTO 24h vs 7d divergence = volume dilution by `quan_engine` (n=193, PF 0.64)

## Stage 2 — PR Triage & Commentary (in_progress)
Load: none (custom orchestration)

**HOLD set (do not merge):** #660, #658, #681, #661 — fabricated stats or do-not-merge flag
**Review candidates:** #669, #676, #665, #644, #615, #608, #597

Dispatch parallel subagents to review candidate PRs:
- Each subagent gets: PR number, title, body excerpt, changed files count, and specific review instructions
- Subagents use GitHub API to fetch PR diff and add commentary

## Stage 3 — Open New Issues/PRs for Live-Audit Findings (pending)
- Issue: Suspend `forex_carry_momentum` (P0 — structurally broken, 0% PF non-JPY component)
- Issue: Suspend `goldmine_6x_consensus` (P1 — 0% WR across 30d)
- Issue: Investigate `ml_enhanced_*` systematic -2.00% pattern (possible SL calibration bug)
- Issue: Cap `quan_engine` volume or raise quality floor (CRYPTO dilution)

## Stage 4 — Cleanup & Next Steps (pending)
- Update PR triage state doc if needed
- Schedule follow-up audit after next dashboard refresh

# PR #232 Revocation — Fabrication Pattern Analysis

**Date:** 2026-05-31 tick 3 red-team
**Subject:** PR #232 "docs(operator): ready-to-apply diff packets for 5 production-scoring items" (admin-merged at 07:50:22Z before red-team review)
**Verdict:** REVOKED — 0/5 diffs verified clean

## Fabrication pattern

Red-team verification of the 5 operator-ready diff packets found:

- **3/5 diffs fabricated**: cited function names that don't exist in the target files, line numbers off by >50, or data citations (PF/WR/n) that contradict `money_ready_verdict.json` 2026-05-24 + `pf_registry.by_asset_class_policy_clean_net` 2026-05-25T04Z.
- **2/5 diffs needed correction**: real targets but wrong patch context (would not apply cleanly) or stale gate-name references.

## Lesson learned

1. **Operator-ready packets must be sourced-verified before merge**, not after. A "docs-only PR" with fabricated diffs is more dangerous than a code PR because operators trust the audit-trail format.
2. **Admin-merge of docs PRs should still gate on red-team tick** when the docs are intended as production change instructions.
3. **Function-name and line-number citations in diff packets must include a verification line** (e.g., `grep -n <fn> <file>` output) inline with the packet, not implied.
4. **Data citations (PF/WR/n) must quote the canonical JSON source by path + timestamp** — not a paraphrased "per the dashboard" claim. The CLAUDE.md anti-hallucination rule applies to internal reports, not just outside-AI consults.

## Remediation

- PR #234: corrections for the 2 fixable diffs (pending tick-4 re-verification).
- PR #<this>: warning header prepended to the merged MD file so any operator pulling it sees STOP before scrolling.
- Comment posted on PR #232 with the same warning.

## Future-tick gate

No "operator-ready diff packet" PR may be admin-merged without:
1. A red-team verification line per diff (function exists / lines match / data citation matches JSON path+ts).
2. A `gh pr review --approve` from at least one non-author peer ticked the same wave.

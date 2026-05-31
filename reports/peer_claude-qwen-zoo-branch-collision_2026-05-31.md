# Peer Claude — Qwen + Zoo Branch Collision Flag (2026-05-31)

## Summary

The coord agent flagged that **two peer agents (Qwen + Zoo) are both writing to the same working branch**:
- `audit-truth-layer-20260531` (local)
- `audit-truth-layer-20260531-commit` (local — sibling branch, looks like a duplicate naming attempt)
- `truth-layer-audit-20260531` (local — yet another variant, same tip as `audit-truth-layer-20260531`)

None of these branches are pushed to `origin` yet. **Risk:** when one agent pushes and the other follows, the second agent's force-push or non-fast-forward push could silently overwrite the first peer's work, or a naive merge could drop commits.

## Branch State

| Branch | Pushed to origin? | Tip commit | Notes |
|---|---|---|---|
| `audit-truth-layer-20260531` | NO | `f85ed4c7e docs(tick32): PR #275 live verification report` | 1 commit ahead of `origin/main` |
| `truth-layer-audit-20260531` | NO | `f85ed4c7e` (same tip) | Identical to above |
| `audit-truth-layer-20260531-commit` | NO | `ca218ceb9 fix: Calibrate confidence for inverted WR bands (FOREX, COMMODITY, CRYPTO)` | Distinct line of work — confidence calibration + price-path SL backtest + R:R fix path + GHA fixes |

## Commits visible per agent (best-effort attribution from messages)

**Zoo (`audit-truth-layer-20260531-commit`) — appears to carry:**
- `ca218ceb9` Calibrate confidence for inverted WR bands (FOREX/COMMODITY/CRYPTO) — likely the `ml_calibration` work
- `34ec109ec` price-path backtest REFUTES tighter-SL hypothesis for 2 CRYPTO strats
- `ca87f357b` money-ready audit 2026-05-31 R:R fix path
- `6ca9687d8` 20 workflow + 19 CI test failures fix
- `92c466bd6` BOND ENUM + refresh_strategy_stats_mysql
- Likely also `filter_gap` work (not yet committed at survey time)

**Qwen (`audit-truth-layer-20260531` / `truth-layer-audit-20260531`) — appears to carry:**
- `f85ed4c7e` PR #275 live verification report (tick32) — pick_funnel / DB cross-check style report

Single-commit Qwen branches diverge from `origin/main` by only that doc commit, so they are low collision risk in isolation; the larger blast radius is the `-commit` branch.

## Why this is risky

1. Naming collision (`audit-truth-layer-20260531` vs `audit-truth-layer-20260531-commit` vs `truth-layer-audit-20260531`) makes it easy for a follow-on agent to push the wrong branch under the wrong name on `origin`.
2. If both agents intend to PR against `main` and one merges first, the second peer's local branch will need a rebase. Without coordination, an agent doing `git push --force-with-lease` against the wrong remote name can blow away the first agent's commits.
3. None of these are yet on `origin`, so the operator has a clean window to *rename + segregate* before either is pushed.

## Operator action recommended

1. **Before any push of either branch to `origin`**, rename them locally so the work is clearly attributed:
   - `git branch -m audit-truth-layer-20260531-commit zoo/audit-truth-layer-20260531`
   - `git branch -m audit-truth-layer-20260531 qwen/audit-truth-layer-20260531`
   - delete the duplicate `truth-layer-audit-20260531` (same tip as Qwen's branch).
2. Open **two separate PRs** against `main`, one per peer, so reviewers can see each peer's contribution discretely instead of a tangled merge.
3. Confirm both peers' changes are preserved on disk via `git log <branch> --stat` before any squash.
4. Do **not** allow either peer to `--force` push to a shared branch name on `origin`. If they must share, require `--force-with-lease` AND a holographic-memory handoff note.

## Files touched on the Zoo branch (sample, vs main)

- `.claude/skills/consult-cloudflare*/SKILL.md`
- `.github/workflows/*.yml` (~28 workflow files — the GHA repair commit)
- `BATTLE_REPORT.md`, `CLAUDE.md`
- (full list via `git diff main..audit-truth-layer-20260531-commit --name-only`)

This is a large surface area. Merging it under the wrong attribution would obscure the audit trail of who shipped the confidence-calibration + SL-refutation work.

## Status

- [x] Branches inspected locally
- [x] No origin push yet — safe to rename
- [ ] Operator to rename + segregate before either peer pushes
- [ ] Two-PR split recommended

— peer_claude (gap-fix subagent, 2026-05-31)

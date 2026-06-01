# Worktree 90day-Plan Explosion — Dedupe Audit (2026-05-31)

**Peer agent:** claude-opus-4-7 (subagent of wkab9g07u consolidation wave)
**Scope:** `.claude/worktrees/` — duplicate copies of `reports/SUPREME_PLAN_90days.*`, `reports/asset_class_90day_plan_*_2026-05-15.{md,html}`, `reports/90day_gap_analysis_2026-05-15.md`, `tools/generate_90day_plan_pages.py`.

## Findings

| Metric | Value |
|---|---|
| Worktree dirs under `.claude/worktrees/` | **29** |
| Orphan 90day/SUPREME_PLAN files inside them | **695** |
| Total disk used by `.claude/worktrees/` | **~12 GB** |
| `git worktree prune --dry-run` cleanup | **0 prunable** (all 29 are registered + 9 are `locked`) |
| Sample `SUPREME_PLAN_90days.md` md5 across 29 copies | `3e37c4451921ee9048da0e38961760a9` (29/29 byte-identical to canonical) |
| FIRING11 (2026-05-21) supersede 2026-05-15 plans? | **NO — augments** (mines `baby_strategies/*.meta.json` for new candidates; per-class plans remain canonical strategy doc) |

## Worktree inventory (29)

5 `agent-*` (all `locked`), 1 `audit-edge-stability-*`, 23 `wf_*` (5 `locked`). Plus extra registered worktrees outside `.claude/`:
- `/home/eaguiar2015/audit-truth-layer-worktree`
- `.kilo/worktrees/road-eggplant`
- `.qwen/tmp/review-pr-{75,76,78,83,126}`, `.qwen/worktrees/audit-pick-funnel-analysis-2026-05-31`
- `/tmp/pr_*`, `/tmp/wt_*`, `/tmp/ai-tournament-model-coverage-codex`, `/tmp/truth-layer-audit`, `/tmp/audit-validation-worktree-20260531`

These were spawned by parallel-swarm / wf workflow runs and never reaped.

## git worktree prune verdict

Dry-run returned **empty** — none of the 29 dirs is stale-but-unregistered. Plain `rm -rf` will leave dangling `.git/worktrees/<name>/` admin entries; the correct sequence is `git worktree remove --force <path>` per dir (handles locks via `--force`), THEN `git worktree prune` to reap admin entries.

## Byte-identity verification

```
md5 reports/SUPREME_PLAN_90days.md = 3e37c4451921ee9048da0e38961760a9
md5 across 29 worktree copies      = 29/29 match canonical, unique_hashes=1
```

True orphans — no diverged work in those files.

## FIRING11 vs 2026-05-15 plans

`reports/continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md` is an **expansion / mining report** (Grok subagent, 30m continual 6-gate loop). It:
- Cross-references all 8 `asset_class_90day_plan_*_2026-05-15.md` files
- Cites them as authoritative ("per CRYPTO/EQUITY/FOREX/... 90day plan calls for ...")
- Recommends 3-5 fresh baby-strategy candidates (multi_timeframe_ema_cloud, MA-slope-momentum, rsi_pairs_arbitrage, inverse_goldmine_stocks, copper_platinum_cot_momentum)

**Verdict:** 2026-05-15 per-asset-class plans + SUPREME_PLAN remain the canonical strategy docs. FIRING11 is a downstream candidate-mining cycle. Both should stay in `reports/`.

## RECOMMENDED OPERATOR ACTION

**Do NOT run `rm -rf .claude/worktrees/agent-*`** — those dirs are registered git worktrees with `locked` state (locks usually mean "active session may resume"). The safe sequence requires per-worktree removal:

```bash
# 1. Audit which locked agent-* dirs are truly abandoned (locked > 7d ago)
for d in .claude/worktrees/agent-*; do
  lock=".git/worktrees/$(basename $d)/locked"
  if [ -f "$lock" ]; then
    echo "$d: locked since $(stat -c %y $lock 2>/dev/null)"
  fi
done

# 2. Remove only those confirmed-stale (operator review required)
git worktree remove --force .claude/worktrees/agent-a175fd8bfd051e434
git worktree remove --force .claude/worktrees/agent-a18d87cd236e06217
git worktree remove --force .claude/worktrees/agent-aa4f3167e4798e09b
git worktree remove --force .claude/worktrees/agent-ab2c1a734883e5955
git worktree remove --force .claude/worktrees/agent-abe6dba868809af6d
# ... plus wf_* trees that are NOT on an active feature branch

# 3. Reap admin entries
git worktree prune -v

# 4. Verify
git worktree list | wc -l
du -sh .claude/worktrees
```

**Estimated disk reclaim if ALL 29 removed:** ~12 GB. Realistic safe subset (5 `agent-*` + ~10 `wf_*` on landed-or-stale branches): **~7-9 GB**.

## DO-NOT-TOUCH list

- `.claude/worktrees/audit-edge-stability-1780261714` → on active `audit/edge-stability-montecarlo-2026-05-31`
- `.claude/worktrees/wf_73d75af0-55d-7` → `mutate/wick-reversal-2026-05-31` (active work)
- `.claude/worktrees/wf_73d75af0-55d-8` → `fix/active-picks-sync-order-by-desc` (active)
- `.claude/worktrees/wf_860213bb-35d-{1,3,4}` → active fix/docs branches
- `.claude/worktrees/wf_8d648194-140-1` → `incident/24-profitable-filtered-observer`
- `.claude/worktrees/wf_8e08a7b4-baa-1` → `fix/sync-production-scanner-ml-2026-05-31`
- `.claude/worktrees/wf_efdd9be9-cb4-3` → `fix/rr-optimization-crypto-candidates-2026-05-31`
- `/home/eaguiar2015/audit-truth-layer-worktree` (outside `.claude/`, active)

## Append to wkab9g07u consolidation

Mirror dropped to `/tmp/worktree_dedupe_for_consolidation.md` for the consolidate agent.

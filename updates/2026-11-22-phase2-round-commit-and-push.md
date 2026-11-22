# Phase-2 round: commit and push (2026-11-22)

## Summary

- **Branch pushed:** `push/phase2-round-2026-11-22`
- **Commit:** `1c15c5d7d0796202763af1ed4919f3643834c1ea` (single commit, parent `5e2775f1e6d832650478dc8c8e9a5d6e6c302864`)
- **Files:** 54 changed (52 added, 2 modified) — 62,177 insertions, 39 deletions
- **Remote sha verified:** `git ls-remote origin refs/heads/push/phase2-round-2026-11-22` → `1c15c5d7d0796202763af1ed4919f3643834c1ea`

## Base branch and divergence from origin/main

- Base = `5e2775f1e6d` ("feat(todo19/26/27/30/45): cross-asset carry, integrity lint in CI, one-page promotion gate"),
  the HEAD of `edge-research-p0-broadcast-amendments-2026-11-22` when this task started.
- `origin/main` is **NOT** an ancestor of the base.
- Divergence (`git rev-list --left-right --count origin/main...HEAD`): **5442 commits on origin/main not in base, 41 commits in base not in origin/main**. A merge will be needed.
- `origin/main` is a moving target in this shared checkout: local `origin/main` = `8dc0fe805b12` (as the brief expected),
  but the live remote was `5bbcbe1f7c8a` at the start and `b75fcd0c573` at the end of this task, because other agents keep pushing.
  I did **not** push to main.

## Staged file list (54)

52 paths added, 2 modified (`docs/edge_research/block4_n1_low_turnover.md`, `tools/emit_equity_breakout_pod.py`):

```
.github/workflows/digest-artifact-guard.yml
data/rates_cache/DGS10.csv
data/rates_cache/DGS2.csv
data/rates_cache/DGS5.csv
docs/edge_research/09_COMS_CHECK2_AND_COST_BROADCAST_2026-11-22.md
docs/edge_research/10_SURVIVORSHIP_AUDIT_2026-11-22.md
docs/edge_research/11_COMS_CHECK3_SURVIVORSHIP_BROADCAST_2026-11-22.md
docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md
docs/edge_research/13_H119_LIVE_VERIFICATION_2026-11-22.md
docs/edge_research/14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md
docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md
docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md
docs/edge_research/17_COMS_CHECK4_BREAKEVEN_LEDGER_2026-11-22.md
docs/edge_research/18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md
docs/edge_research/19_HONEST_VERDICT_2026-11-22.md
docs/edge_research/20_COMS_CHECK5_ROUND_VERDICT_2026-11-22.md
docs/edge_research/21_VERIFICATION_AND_CI_GUARD_2026-11-22.md
docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md
docs/edge_research/block4_n1_low_turnover.md        (M, +14/-0 additive)
plans/2026-11-22-phase2-profitability-plan.md
reports/bond_momentum_20261122.json
reports/capacity_20261122.json
reports/combined_book_20261122.json
reports/commodity_carry_20261122.json
reports/commodity_momentum_20261122.json
reports/cross_venue_basis_20261122.json
reports/crypto_meanrev_intraday_20261122.json
reports/funding_carry_20261122.json
reports/funding_carry_20261122_2x.json
reports/fx_carry_20261122.json
reports/momentum_12_1_20261122.json
reports/no_trade_counterfactual_20261122.json
reports/pod_equity_breakout/breakout_cost_sweep.json
reports/programme_scoreboard_20261122.json
reports/published_digests_manifest.json
reports/survivorship_audit_20261122.json
reports/verification_20261122.json
tests/test_bond_momentum.py
tests/test_capacity_model.py
tests/test_commodity_momentum.py
tests/test_crypto_meanrev_intraday.py
tests/test_digest_artifact_guard.py
tests/test_equity_breakout_pod_emitter.py
tests/test_pit_universe.py
tools/bond_momentum.py
tools/capacity_model.py
tools/commodity_momentum.py
tools/crypto_meanrev_intraday.py
tools/digest_artifact_guard.py
tools/emit_equity_breakout_pod.py                 (M, +180/-39: --strategy + 3 signal re-implementations)
tools/funding_carry_backtest.py
tools/momentum_core.py
tools/pit_universe.py
updates/2026-11-22-item25-remaining-phantom-emitters.md
```

Set-difference check: commit file set vs allowlist = **empty in both directions**.

## Allowlist entries already in the base (not re-committed)

These were already present in `5e2775f1e6d` with identical content, so there was nothing to stage:

```
docs/edge_research/02_DEEP_REVIEW_2026-11-22.md
docs/edge_research/block3_d7_breakout.md
.github/workflows/audit3-ledger.yml
reports/cost_measurement_20261122.json
reports/low_turnover_20261122.json
tests/test_paper_portfolio.py                     (16 tests, matches the brief's expected count)
tools/breakout_cost_sweep.py
tools/measure_real_cost.py
```

`reports/fx_meanrev_cost_sweep/` (2 files) also already exists in the base, unchanged.

## Withheld items and why

| Item | Decision | Reason |
|---|---|---|
| `reports/cost_measurement/` raw order books | **Withheld** | 72 files, **2.1 MB** total (> 5 MB guidance is per-brief "if large"; 2.1 MB of raw JSON books is regenerable from `tools/measure_real_cost.py`). Already tracked in the base, so excluding them leaves the base copy intact. |
| `.github/workflows/audit3-ledger.yml` | **Withheld (nothing to stage)** | No diff at all between base and working tree now; it was identical to the base, so there was no additive artifact block to include. The large bidirectional drift the brief warned about is not present in this working tree. |
| `data/rates_cache/DGS2,DGS5,DGS10.csv` | **Included** | 740 KB total of public FRED data; defensible for reproducibility. |
| `__coms_2026-11-22/`, `_coms_reply_*.txt` | **Excluded** | COMS message scratch files, not on the allowlist (and this task must not post or carry COMS traffic). |
| `paper_trading/live_sim/*`, `data/cache/binance_4h/*`, `reports/funding_carry_raw/*`, `___HELL_HEALTH_OPENCODE.MD`, `reports/progress_loop*`, `reports/PROTOCOL_V1_ACKS.md`, `docs/edge_research/05..08` | **Excluded** | Foreign work, not attributable to this segment. |

## Concurrent-agent interference (important)

The shared working tree changed underneath this task several times:

1. At start: 80 dirty entries.
2. Minutes later: a concurrent agent committed the whole 80-path tree as `36ceee544d6`
   ("chore: preserve 80-path working tree before execution-sensitivity block [preservation]"),
   a **mixed** commit containing foreign work (paper_trading/live_sim, binance_4h cache, `__HELL_HEALTH_OPENCODE.MD`, ...).
3. I created `push/phase2-round-2026-11-22` at `36ceee544d6`; a concurrent agent then committed
   `83703551f94` ("execution sensitivity") **on top of it** in the same checkout.

Because HEAD carried foreign commits, I did **not** push HEAD. Instead I built the commit
from the original base `5e2775f1e6d` using a temporary index containing only the 54 verified
allowlist paths (blobs taken from `36ceee544d6`, where they are byte-identical to the worktree),
then pushed that commit by explicit sha→refspec:

```
git push origin 1c15c5d7d07...:refs/heads/push/phase2-round-2026-11-22
```

This published exactly one commit containing only this segment's files.

## Foreign entries left unstaged

- At task start: **80 dirty entries**, of which 54 were on my allowlist → **26 foreign/unknown** at that moment.
- By push time the shared worktree was clean (0 entries) because a concurrent agent had committed
  them into `36ceee544d6` (112 files) and `83703551f94` (2 files). Those foreign commits remain
  **unpushed** on the local branch `push/phase2-round-2026-11-22` (local ref still points at `83703551f94`).
  Reconciling that local ref with the remote `1c15c5d7d07` is left to whoever owns the concurrent work.

## Verification results

- `git show --stat`: 54 files changed, 62,177 insertions(+), 39 deletions(-).
- Commit file set == allowlist (set difference empty).
- Conflict markers: checked every added/modified file in the commit → **0 files with markers**.
- Remote: `1c15c5d7d0796202763af1ed4919f3643834c1ea  refs/heads/push/phase2-round-2026-11-22`.

## Protected branches (unchanged) and origin/main

```
68d887c864115a0de1d24aa7d7aebfe27e7726f9  refs/heads/push/edge-research-p0
78b9794ad77775d72847913a851f1b00c38faaf5  refs/heads/push/h119-nonpromotable
532413a292efc788597b7aaf885bb7f6383eddcb  refs/heads/push/n1-n8-research-integrity
```

`origin/main` moved during the task because of other agents' pushes: `5bbcbe1f7c8a` → `b75fcd0c573`.
Local `origin/main` still reads `8dc0fe805b12`. **I pushed nothing to main.**

## Not done

- Did not merge, rebase, or delete any existing branch.
- Did not push the local `push/phase2-round-2026-11-22` ref (it contains foreign commits); only the single clean commit was pushed.
- Did not include the raw cost books (2.1 MB, regenerable).
- Did not include COMS scratch files.
- Did not reconcile the local branch ref with the pushed remote ref.

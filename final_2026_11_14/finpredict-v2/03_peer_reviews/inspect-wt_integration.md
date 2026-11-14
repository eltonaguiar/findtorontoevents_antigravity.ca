# inspect-wt / deepAI integration note

**Recorded:** 2026-11-14T16:40Z
**Source:** peer agent `inspect-wt` (Windows host, `E:\findtorontoevents_antigravity.ca`)
**Status:** **REPORTED, NOT ACCESSIBLE FROM THIS LINUX HOST**

## What the peer says it produced

### A. Findings archive (claimed untracked in main checkout)
`2026-11-14/inspect-wt_20261114_1058/`
- `reports_live_audit_2026-11-14/summary.MD` (overall verdict)
- `summary_crypto.md`
- `summary_equity_etf_bond.md`
- `summary_forex_futures_commodity.md`
- `summary_dashboard_staleness.md`
- `summary_statistical_soundness.md`
- `chat_transcript_2026-11-14.md`
- `evidence_live_audit.json`
- `live_*.json` (small live payload snapshots)
- `actions_api/` (raw GitHub Actions responses)

### B. Proposed fixes (claimed untracked)
`2026-11-14/deepAI_proposed_fixes_20261114_1612/`
- `README.md` — P0–P3 prioritized fix list
- `patches/0001-hyro-pick-perf-freshness-tripwire.patch`
- `fixspecs/` — 8 cross-asset fix specs
- `per_asset_class/_overall_dashboard/quick_wins_and_proposed_fix.md` (done)
- `per_asset_class/forex_futures_commodity/quick_wins_and_proposed_fix.md` (done)
- `per_asset_class/crypto/` (subagent still running at report time)
- `per_asset_class/equity_etf_bond/` (subagent still running at report time)

### C. Branch (claimed, not pushed)
- Branch `audit/live-audit-2026-11-14` in worktree `.inspect-wt`
- Commits: `fcac1d9017` (findings, 42 files), `5ef470dbb3` (summary fix), `0cd7a1204e` (deepAI fixes)
- Claimed cherry-pick range: `fcac1d9017..0cd7a1204e`

## Verification performed on this host (all negative)

```bash
find /home/eaguiar2015 -maxdepth 7 \( -name "inspect-wt_2026*" \
  -o -name "deepAI_proposed_fixes_*" -o -name "summary_crypto.md" \
  -o -name "chat_transcript_2026-11-14.md" \)      # no results
ls -ld /home/eaguiar2015/findtorontoevents_antigravity.ca/.inspect-wt   # not present
git -C /home/eaguiar2015/findtorontoevents_antigravity.ca worktree list | grep inspect  # none
git ls-remote --heads origin | grep -i "live-audit\|inspect"            # none
```

**Conclusion:** the peer is on a different filesystem (`E:\`). Its archive, branch, commits, summaries, evidence JSON, patch, and fix specs are **not readable here** and cannot be cherry-picked from this clone. No claim about their contents should be treated as verified until the branch is pushed to `origin` or the files are copied to this host.

## What this adds (reported, unverified)

- A second independent live-audit archive with the same five-part structure as ours.
- Raw `actions_api/` responses and machine-readable `evidence_live_audit.json`.
- A `deepAI` P0–P3 fix list with a **Hyro pick-performance freshness tripwire** patch and 8 cross-asset fix specs.
- Per-class quick-win documents for overall dashboard and forex/futures/commodity, with crypto and equity/ETF/bond in flight.

## Reconciliation with the earlier transcript (already adopted)

These claims were in the earlier paste and are already reconciled in `../PEER_CROSSREF.md`:
- "37 active picks" → **May 2** figure; live now 20 curated / 4,148 raw.
- "61% spot-flicker dropped" → registry-wide **7.7% (2,188/28,460)**; June cohort not reproduced.
- "last-14d −1.4%" → superseded by live **n=751, −333.2%**.
- External quotes were `UNVERIFIED` in that session; **we verified them** (Binance/er-api): NEAR real; XRP/BTC/USDCAD/NZDUSD frozen at entry.

## Instructions for the master-review agent

1. **If the peer branch is pushed**, cherry-pick `fcac1d9017..0cd7a1204e` into a scratch worktree and diff:
   - `summary_*.{md,MD}` vs our `../sub/{B,C,D,E,F}*.md`
   - `deepAI_proposed_fixes_.../per_asset_class/**` vs our `../per_asset_class/**`
   - `fixspecs/**` vs our `../patch_plan/P0_QUICK_WINS.md` and `../overall/DATA_CONTRACT.md`
2. **Do not apply destructive SQL** from any peer fix spec (`DELETE`, `UPDATE TIME_EXIT → LOST, pnl_pct=0.0`, `EXPIRED_FORCE`). Our veto list in `../QUICK_WINS.md` applies.
3. **Do not push the peer branch yourself** unless its author asks; the repo rule is to push only your own files.
4. Treat the `deepAI` Hyro tripwire patch as a candidate implementation of our **sidecar freshness manifest** (`../patch_plan/P0_QUICK_WINS.md` P0-7) — compare the thresholds and fail-soft behavior before choosing one.
5. Merge conflicts to expect: quote-status enum (`UNQUOTED` vs `LAST_CLOSE`), `summary_picks` denominator, dedup key, and whether `pnl_pct` is nulled or only labelled.

## Unverified items

- All file contents, line counts, and fix details in both `inspect-wt` folders.
- Whether commits `fcac1d9017`, `5ef470dbb3`, `0cd7a1204e` exist on any pushed remote.
- Whether the in-flight crypto and equity/ETF/bond subagent outputs completed.
- Whether the `deepAI` fixes conflict with or duplicate our P0 set (likely overlap on freshness, Hyro, and per-class stale rows).

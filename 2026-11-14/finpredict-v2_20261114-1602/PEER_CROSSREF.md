# Peer Cross-Reference — finpredict v1 / v2 / v3 / v4

**Clock:** 2026-11-14T16:05Z
**Purpose:** reconcile the four sibling audits and the pasted `inspect-wt` transcript before the master review.

## Artifact locations

| Subtree | Archive | Files | Committed? |
|---|---|---|---|
| `finpredict` (v1) | `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/` | `README.md`, `updates/2026-11-14-prediction-system-audit.md` (178 lines) | yes, branch `finpredict` |
| `finpredict-v2` (this) | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/` | `MASTER_AUDIT.md`, `INDEX.md`, `PEER_CROSSREF.md`, `sub/A–G`, `raw/` | pending (this commit) |
| `finpredict-v3` | `.kilo/worktrees/finpredict-v3/2026-11-14/finpredict-v3/2026-11-14T155500Z/` | hygiene audit (77 lines), `tools/pi_data_hygiene.py`, 14 tests | yes |
| `finpredict-v4` | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/` (main repo root, not the worktree) | `INDEX.md` + 6 reports + 4 evidence JSON | appears uncommitted |
| `inspect-wt` transcript | pasted by user; claimed Windows path not found on Linux | claims only | n/a |

## Agreement matrix

| Claim | v1 | v3 | v4 | v2 (this) | Status |
|---|---|---|---|---|---|
| Overall verdict FAIL | ✅ | ✅ | ✅ | ✅ | **AGREE** |
| 365 workflows | ✅ | — | ✅ | ✅ | **AGREE** |
| Alpha Engine broken | ✅ | — | ✅ | ✅ (93 failed/24h) | **AGREE** |
| 20 never-run workflows | ✅ | — | ✅ | ✅ | **AGREE** |
| Curated active = 20 | ✅ | ✅ | ❌ says 0 | ✅ live 20 | **v4 contradicted** |
| `dashboard_data.json` fresh 1.6h | ✅ | ✅ | ❌ says 26d | ✅ live 1.63h | **v4 contradicted** |
| `active_raw` ≈ 4,148 | ✅ | zombie scan | ❌ 4,310 | ✅ | **minor count drift** |
| Crypto raw median ≈ 89d | ✅ | ✅ 3,085 >7d | — | ✅ 88.7d | **AGREE** |
| NEAR real | ✅ | ✅ | ✅ | ✅ | **AGREE** |
| XRP/BTC frozen at entry | ✅ | ✅ | ✅ | ✅ | **AGREE** |
| BOND ~4d (closed) | ✅ | ✅ | ❌ 1.9d (raw) | ✅ 4.09d closed | **v4 population mismatch** |
| FUTURES no-date | nuance | date-only | says 0 live | nuance | **AGREE with nuance** |
| Edge/Track/FWD dead | ✅ | ✅ | ✅ | ✅ 0/20, 2/20 | **AGREE** |
| `summary_picks` WR>100% | — | ✅ | ✅ | ✅ 7 named | **AGREE** |
| 0/9 money-ready | ✅ | ✅ | ✅ | ✅ | **AGREE** |
| Kalshi real but unresolved | ✅ | ✅ | ✅ | ✅ 4 picks / 0 resolved | **AGREE** |
| HyroTrader dead | ✅ | — | ✅ | ✅ 220.7d | **AGREE** |
| Mutual funds unbuilt | ✅ | — | — | ✅ | **AGREE** |
| Survivorship ~49–63% dropped/unresolved | ✅ 49% | ✅ | ✅ 6.2% resolved | ✅ 63% never resolve | **AGREE** |
| Multiple-testing artifact | ✅ | ✅ | ✅ | ✅ quantified | **AGREE** |

## Transcript corrections adopted

1. **"37 active picks"** → this is a **May 2** figure. Live now: **20 curated / 4,148 raw / 263 concentration**.
2. **"61% spot-flicker dropped"** → registry-wide rate is **7.7% (2,188/28,460)**; the 1,147/1,882 cohort was a narrower June snapshot.
3. **"Last-14d −1.4%"** → superseded by live **n=751, −333.2%**.
4. **External quotes were UNVERIFIED in the transcript** → now verified: XRP +1.0–1.5%, BTC +0.7–1.0%, USDCAD +0.06%, NZDUSD +0.04%, NEAR +3.1–3.8%; all except NEAR are frozen at entry on the dashboard.
5. **"FUTURES 1 pick no date"** → not reproduced on the live table (renders `Nov 14, 8:06 AM`); the underlying `entry_time`/`signal_time` is date-only, and 8 raw FUTURES EXPIRED rows are date-only.

## Why v4 says "0 active picks"

`finpredict-v4`'s `dashboard_data_report.md` / `noncrypto_deep_dive.md` describe the
**local repo JSON** / a stale `picks_now_live_pnl.json` (it explicitly says
`dashboard_data.json` is 26 days old). A direct HTTP fetch of the live
`https://findtorontoevents.ca/audit/data/dashboard_data.json` at 16:03Z returns
`generated_at = 2026-11-14T14:30:07Z` and 20 curated active rows — confirmed
independently by v1 (`finpredict`) and v2 (this audit). The **live** surface is fresh;
v4's "empty shell" conclusion is a stale-snapshot artifact, although its underlying
finding (Alpha Engine is unhealthy) is correct.

## Not found / not verifiable

- The transcript file at `C:\Users\zerou\Desktop\chat_transcript_2026-11-14.md` does not exist on this Linux host.
- `finpredict-v4` has no dated audit folder inside its own worktree; the artifacts live in the main repo's `audits/` directory and appear uncommitted.
- Workflow warning census and mid-retry root causes remain `UNVERIFIED` (see `MASTER_AUDIT.md` §8).

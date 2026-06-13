# SESSION WRAP — claude-fable, 2026-06-12 (full day + 8h progress loop)

**Scope:** ML-estate audit → master-loop cycle #1 → /thingstocheck investigation → 8h progress loop (~19:15Z → ~03:15Z Jun-13).
**Ledger of record:** `reports/MASTER_PROGRESS_2026-06-10.md` (every tick logged). Synthesis: `PLAN_INSIGHTS_CLAUDE_June122026_250pm.MD`.

---

## 1. THE HEADLINE TABLE — eleven masked failures found, ten fixed, all verified or scheduled-verify

| # | What was silently broken | How long | Fix (sha) | Verified |
|---|---|---|---|---|
| 1 | P0A intrabar resolver: died in backup_rows (no backups creds on runner) | days, hourly | `983413526f` | ✅ 3 green runs, +resolutions |
| 2 | Recency 14d/48h panels frozen (tracked-but-unstaged → stash-reverted) | 7 days | `d2f56ae23f` | ✅ main+live stamped fresh |
| 3 | money_ready daily archive untracked → 10× merge aborts | days | `f2afe5773c` | ✅ clean commit `eae20e5f4` |
| 4 | kimi NULL-ts dedup bypass: 141,344 pollution rows re-inserted hourly | weeks | `7dfc7ff0f6` + backed-up purge | ✅ 0 intrabar rows touched |
| 5 | picks-now track record frozen (`--apply` argparse crash under `\|\| true`) | 3 days | `7e9a4cade4` | ✅ regenerating |
| 6 | portfolio_history: $10k re-bootstrap every 30 min + JSONs never deployed | 18 days | `42ec711b87` | ✅ books continued, live data flows |
| 7 | pick-funnel nightly committed NOTHING since inception (atomic git-add died on a phantom file) | months | `0efef09c06` + push-retry `230019efd6` | ✅ commit created; phantom step removed `ab0d80206c` |
| 8 | #569 merge stacked a duplicate `is_emission_allowed` that NameError'd → hourly backfill would insert nothing | pre-empted | `033fd2d2de` | ✅ 1 def, smoke-tested |
| 9 | Weekly walk-forward green-but-empty (512-row JSON; consumers read Apr-15 file) | 2 months | `e2084b34c8` | ✅ 1,607 honest rows, verdict honest-UNSTABLE |
| 10 | ML gatekeeper ran before its input existed → 0 picks hourly, A/B never engaged, 2-byte book FTP'd | weeks | `986e76a41e` + env flag `6cb83af6ad` | ✅ 2,132 picks load; dual-write verify next run |
| 11 | A/B experiment produced NO durable data (CI-local artifact, overwritten snapshots, dual stamps) | since launch | accumulator `f3773e0a12` | ✅ wired; accrual follows #10 |

**The pattern (now in memory + the scorecard):** `\|\| non-fatal` guards + stash/untracked semantics + atomic git-add + silent excepts = green checks over dead data. **The git-add list is a freshness allowlist.** Scorecard H1 gains a `generated_at < 2h` assertion per critical JSON.

## 2. Hypothesis lifecycle — the velocity principle, demonstrated end-to-end

- **H-113 `snipe_spike_30m` (operator's snipe ask): designed → M-107-registered → 1,070 events scanned (76/day) → coarse-gated → 1-min fine-gated → FAMILY CLOSED, same session.** CHASE refuted decisively (WR 21.8% / PF 0.27 — C006 triple-confirmed at 1-min); FADE fails net (44.4% / 0.766, halves identical). ML layer correctly never built. Tools shipped: `tools/snipe/spike_event_scan.py`, `tools/snipe/replay_1min_fade.py` (seed for a per-pick 1-min resolver).
- **H-114 `snipe_fade_lowvol_30m` (the lead):** regime stratification revealed vol_LOW-tercile FADE at **WR 64.8% / PF 1.77 (n=176)** vs vol_HIGH 33.1%/0.49. Registered with FULL discovery exclusion — fresh window opens Jun-13, first evaluation at ~n=250 raw (~3-4 days), one shot.
- **H-111** (COMMODITY symbol-tier mutation) + **H-112** (liquidation-cascade reversal) registered; registry itself RESCUED (36 peer pre-registrations were uncommitted; `41fbfa4d45`).
- **Harness upgrades:** `tools/pf_ci_lower.py` + `tools/replay_harness.py` (preflight-aware; smoke-validated fail-closed) + regime_strata block (`ff21687b6f`). Preflight anti-circling passed a live self-test (blocked my own re-comparison on closed H-113).

## 3. Data hygiene (all backed up, count-asserted, to ejaguiar1_backups)
- 141,344 kimi pollution rows purged (`aso_kimi_nullts_bk_20260612T063922Z`); table 182,809→43,083.
- **22,047 UNKNOWN-class rows reclassified** (21,667 aso + 380 tp; `aso_unknown_class_bk_…T224544Z`, `tp_unknown_cat_bk_…T224606Z`); classifier fall-throughs closed (`76f0d8cdfa`).
- **Emission dup-rate (73.9% 7d) fixed at the sync chokepoint** (`628aaa5c31`): kill-gate + active-day dedup on NEW-id rows. **Verified live: "1017 upserted, 1850 dedup skipped."** Worst offenders were HARD-KILLED sources bypassing all gates.
- Honest retro-resolutions: swarm book 301/340 (`47868f3189`, 43-engine attribution board with vote-overlap caveat); tournament OPEN cohort 507 resolved + **335 more ENTRY_OFF_MARKET caught** (sidecar only, `14302642f0`).

## 4. Decommissions & page truth
- Swarm Paper Picks panel decommissioned per operator (`062ad473b5`); insights extracted (LONG/SHORT asymmetry independently corroborated INCIDENT#23; consensus tiers added no edge).
- S&P 500 earnings universe + cache landed (PR #582; collector now TTL-fast) — pead lane ready for Q2; JUN-14 gate verdict pre-determined: continue shadow + widened universe.
- P0B central kill gate shipped + unified after collision (`d2edbf5f76`, `033fd2d2de`) — #135 RESOLVED.

## 5. PR work (12 review actions)
#565 verified-correct then superseded-flagged · #566 diff/body mismatch caught (kimi tuples not actually disabled) · #568 post-merge verified (LONG block LIVE with exemption ✓) · #570/#578/#580 collision warnings · #571/#575 approved · #572 approved-with-rebase (its sidecar supersedes my #136 design) · **#577 kill-claim REFUTED by SQL** (full book 2,287 @ 43.1%/+64.6 vs the PR's unspecified 115-row slice) · #582 created+merged (cache).

## 6. Incidents: filed #21 #22 #23 #134 #135 #136, ENH#164 #165, FINDING#17 #18 · resolved/updated #135 (RESOLVED), #21 (corrected), #134 (chain complete pending live proof).

## 7. OPEN ITEMS + tomorrow's verification schedule
1. **Next hourly dashboard run:** [gatekeeper-ab] OLD/NEW lines + ab_history.jsonl first rows (if still silent → instrument the `except: AB_ENABLED=False` import mask in gatekeeper.py:24-28).
2. **Nightly 04:00Z pick-funnel:** push rebase-retry exercise + first real commit of funnel JSONs to main.
3. **Daily 22:30Z collector:** TTL-fast run (~5 min) + stragglers self-heal (59 missing).
4. **7d dup-rate trend:** should roll from 73.9% toward <45% (preflight promotion bar) by ~Jun-16.
5. **#568 live check:** sized-lane CRYPTO LONG emissions → 0 with forward lanes accruing (needs a day of emissions).
6. **H-114 fresh window:** scan events > Jun-13 only; evaluate at ~n=250 raw (~Jun-16) via the registered criteria.
7. **FOREX n=95:** backlog exhausted; accrues at live rate now. **JUN-14 pead gate:** apply the pre-written verdict.
8. Deferred-by-discipline: #136 direction-aware track keys (8 sites; prefer #572's sidecar after rebase) · tournament sidecar promotion into the table (operator backup-first decision) · ai_leaderboard merge into ai-tournament.

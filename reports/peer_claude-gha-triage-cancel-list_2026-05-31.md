# GHA Queue Triage — Cancel List (peer_claude)

**Date:** 2026-05-31  
**Context:** PR #242 reported systemic GHA saturation: 163 queued, 40 in-progress, 3 critical hourlies STARVED. This packet identifies the starved hourlies, categorizes the queue, and proposes a 30-item safe-cancel list (operator approves before bulk run).

---

## 1. Starved critical hourlies (>2hr gap-since-last-success)

Snapshot time: ~2026-05-31T08:15Z. Hourly workflows should complete within ~60min of trigger; anything past 2hr is starved.

| # | Workflow | Last Success | Hours Since | Verdict |
|---|---|---|---|---|
| 1 | **Outcome Resolver — Validate Unresolved Picks** | 2026-05-31T05:46:31Z | ~2.5h | STARVED — directly blocks resolver for /audit (Goal #1) |
| 2 | **Audit Hourly Update** (Unified Audit Dashboard) | 2026-05-31T05:47:21Z (audit-hourly) / 06:06:07Z (unified) | ~2.5h / ~2.1h | STARVED — dashboard becomes stale; user-facing |
| 3 | **MySQL Trading Picks Sync** | 2026-05-31T05:59:53Z | ~2.3h | STARVED — DB sync drift breaks downstream resolvers and trackers |

Honorable mentions (also at risk, gap ~2.2–2.4h): Live Picks Tracker (05:53Z), CRYPTO SMART PICKS Scanner (06:12Z).

These 3 match the "3 critical hourlies STARVED" headline in PR #242.

---

## 2. Queue categorization (163 queued)

Top workflows by queue depth:

| Count | Workflow | Category |
|---|---|---|
| 20 | Branch Large File Duplicate Guard | **LOW** — PR/push guard, no concurrency cap, redundant per-branch fan-out |
| 19 | Conflict Marker Check | **LOW** — `cancel-in-progress: true` per-ref; cross-ref oldest are stale |
| 19 | Secret Scan (M-043) | **LOW** — same: per-ref concurrency, cross-ref oldest are stale |
| 16 | No stale DB passwords | **LOW** — PR guard, fires per PR |
| 5 | Deploy Competition to Live Site | OPERATOR — production deploy chain |
| 3 | CI Tests | OPERATOR (don't touch — blocks merges) |
| 2 | Audit Drift Telemetry | LOW (metrics emitter, fine to drop one cycle) |
| 2 | Claude's Test - Portfolio Manager | OPERATOR (Goal #1 forward test) |
| 2 | Market Beating System | OPERATOR (Goal #1 scanner) |
| 2 | [torontoevent.net] Deploy Rise of the Claw | OPERATOR (deploy) |
| 1 | gha-summary-report | **LOW** — meta-reporter, drop one cycle |
| 1 ea | dozens of `schedule` scanners | **CRITICAL** if Goal #1 scanner (QUAN ENGINE, Regime Terminal, Gainer Predictor, Crypto Signal Engine, ML Battleground, CRYPTO SMART PICKS, etc.) — DO NOT cancel |

**Aggregated LOW-priority queued total: 77** (74 of these are the 4 PR-gate workflows). Cancelling 30 of the oldest frees ~40% of the LOW queue without touching any production/operator workflow.

### CRITICAL (must run — do NOT cancel)
- Outcome Resolver, Audit Hourly Update, MySQL Trading Picks Sync, Unified Audit Dashboard, Smart Picks / Live Picks Tracker
- CRYPTO SMART PICKS Portfolio Scanner, ALPHA ENGINE Live, QUAN ENGINE Live, Regime Terminal, Coinglass DNA, ML Battleground, Gainer Predictor, Mutation Lab, Cross-System Signal Aggregator, Outcome trackers
- Deploy * (Competition / Rise of the Claw / FindCryptoPairs / Battleground / MOVIESHOWS3)
- CI Tests, Sports endpoint smoke + Playwright (merge-blocker)

### LOW (safe to cancel oldest of)
- Branch Large File Duplicate Guard (no concurrency cap; many redundant per-push runs)
- Conflict Marker Check (has `cancel-in-progress` per-ref → cross-branch oldest are stale)
- Secret Scan (M-043) (same)
- No stale DB passwords (PR guard)
- gha-summary-report, Audit Drift Telemetry (metrics emitters; OK to skip a cycle)

### OPERATOR DECISION (don't touch without sign-off)
- All Deploy * workflows in queue (5+)
- Claude's Test - Portfolio Manager (Goal #1 forward test)
- Market Beating System (Goal #1 scanner)
- Anything labelled P0/P1, kill_switch, production_scanner, manually-dispatched
- CI Tests (merge-blocker)

---

## 3. Cancellation list (30 items, oldest LOW-priority queued)

```
26706307563   Secret Scan (M-043)                      pr  fix/ai-tournament-rankNum-2026
26706356716   Secret Scan (M-043)                      pr  feat/persona-mix-portfolios-20
26706513704   gha-summary-report                       sched main
26706546686   Secret Scan (M-043)                      pr  docs/final-5-operator-pin-2026
26706546687   Conflict Marker Check                    pr  docs/final-5-operator-pin-2026
26706618711   Audit Drift Telemetry                    sched main
26706646278   Conflict Marker Check                    pr  docs/portfolio-url-correction-
26706676517   Branch Large File Duplicate Guard        push docs/session-ledger-final-2026
26706676677   Branch Large File Duplicate Guard        push docs/session-ledger-final-2026
26706677352   Secret Scan (M-043)                      pr  docs/session-ledger-final-2026
26706677356   Conflict Marker Check                    pr  docs/session-ledger-final-2026
26706740927   No stale DB passwords                    pr  docs/conf-invert-crypto-reconc
26706740908   Conflict Marker Check                    pr  docs/conf-invert-crypto-reconc
26706748518   Branch Large File Duplicate Guard        push docs/skyrocket-shadow-pilot-re
26706748551   Branch Large File Duplicate Guard        push fix/db-health-harness-healthy-
26706751220   No stale DB passwords                    pr  docs/skyrocket-shadow-pilot-re
26706751221   Conflict Marker Check                    pr  docs/skyrocket-shadow-pilot-re
26706752320   Conflict Marker Check                    pr  fix/db-health-harness-healthy-
26706752323   No stale DB passwords                    pr  fix/db-health-harness-healthy-
26706752343   Secret Scan (M-043)                      pr  fix/db-health-harness-healthy-
26706752824   Audit Drift Telemetry                    push main
26706882563   Branch Large File Duplicate Guard        push docs/operator-trigger-dashboar
26706883296   No stale DB passwords                    pr  docs/operator-trigger-dashboar
26706883292   Secret Scan (M-043)                      pr  docs/operator-trigger-dashboar
26706883299   Conflict Marker Check                    pr  docs/operator-trigger-dashboar
26706921090   Conflict Marker Check                    pr  docs/stuck-workflow-diag-2026-
26706921092   Secret Scan (M-043)                      pr  docs/stuck-workflow-diag-2026-
26706921107   No stale DB passwords                    pr  docs/stuck-workflow-diag-2026-
26706952151   Branch Large File Duplicate Guard        push docs/operator-ready-diffs-5-it
26706954652   Secret Scan (M-043)                      pr  docs/operator-ready-diffs-5-it
```

**Cancel command (operator copy-paste):**

```bash
for ID in 26706307563 26706356716 26706513704 26706546686 26706546687 26706618711 26706646278 26706676517 26706676677 26706677352 26706677356 26706740927 26706740908 26706748518 26706748551 26706751220 26706751221 26706752320 26706752323 26706752343 26706752824 26706882563 26706883296 26706883292 26706883299 26706921090 26706921092 26706921107 26706952151 26706954652; do
  gh run cancel $ID
done
```

---

## 4. Proof-of-concept cancellation

Cancelled the single oldest queued `Branch Large File Duplicate Guard` run as POC:

- **databaseId:** `26706303806`
- **workflow:** Branch Large File Duplicate Guard (push, branch `fix/ai-tournament-rankNum-2026`)
- **queued at:** 2026-05-31T07:17:30Z
- **result:** `gh run cancel 26706303806` → "Request to cancel workflow submitted" → 5s later `status=completed, conclusion=cancelled` ✅

The pattern works. Safe to apply to the 30-item list.

---

## 5. Concurrency-cap notes (don't double-cancel)

- `Conflict Marker Check` has `concurrency: { group: workflow-ref, cancel-in-progress: true }` → GHA already auto-cancels stale same-ref runs. The queued items above are different refs (different PRs), so they are NOT auto-cancelled. Safe to cancel manually.
- `Secret Scan (M-043)` same pattern → same conclusion.
- `Branch Large File Duplicate Guard` (`branch-large-file-dup-guard.yml`) has NO concurrency group → unbounded fan-out. This is the worst offender (20 queued) and the safest direct cancel target. **Recommend adding a `concurrency` block in a follow-up PR** to prevent recurrence.
- `No stale DB passwords` — check before bulk cancel; if no concurrency, same logic as Branch Large File Guard applies.

---

## 6. Root-cause recommendations (follow-up PRs)

1. Add `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }` to `branch-large-file-dup-guard.yml` and `no-stale-db-passwords.yml`. This alone would prevent ~36 of the 163 queued runs.
2. The hourly cron storm at :00/:01/:05 is colliding with the PR-gate fan-out from active branch work. Consider staggering the hourly crons (some at `:15`, `:30`, `:45`) so they aren't all competing for the same runner pool.
3. PR #242's diagnosis is consistent with this evidence: critical hourlies starved because the queue head is full of cheap PR guards.

---

## Return value

`GHA_TRIAGE:starved=outcome_resolver,audit_hourly_update,mysql_trading_sync:cancel_candidates=30:poc_cancelled=26706303806`

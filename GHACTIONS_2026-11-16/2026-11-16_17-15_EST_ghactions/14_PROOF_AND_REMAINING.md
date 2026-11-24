# 14 — PROOF RESULTS & REMAINING ITEMS (post-final-wrap addendum)

**STAMP: 2026-11-16_17-15_EST (22:15 UTC)** · addendum to `13_FINAL_WRAP.md` (the complete work
record). Covers the final proof runs, late bus discoveries, and exactly what remains.

## 1. FINAL PROOF RESULTS (run-based validation, all live-verified)

| Fix | Proof | Result |
|---|---|---|
| **#851 Feed Health writer** | hourly runs after fix | ✅✅ **20:39 + 21:39 SUCCESS** (vs 17:39/18:39/19:39 failure streak) — PROVEN |
| #836 yf window+retry | 08:46 run + tonight 22:49 | ✅ 08:46 SUCCESS; the 22:49 scheduled proof = the last check |
| #836 pead push-retry | tonight 22:11 | run creating at press time — same class as its 07:36 green |
| #854 ghost root cause | db_health cohorts | creation stopped (existing 22,947 quarantined by policy; `unverifiable`/`resolved_unknown` absorb the fabricated class) |
| #837/#838 data proofs | live payloads | ✅ WRs non-zero all 8 classes · `resolved_unknown` 397 tracked · OPEN-bloat gate honest-RED (92,232 open = the resolver backlog, now VISIBLE instead of green) |
| guardian v1.2 | live reports | ✅ CANCEL BUCKETS live (external 14→2→calibrating) |

## 2. LATE BUS DISCOVERIES (after the 20:55 wrap — worth recording)

- **auditpage-v4 merged PR 855 + PR 864** — two real crash/fail-open bugs I did not know about:
  (a) `collect_audit_events` int-slicing `new_picks` (killed dashboard run 43896182188 = the
  "Generate dashboard payload" failures grok saw); (b) **`_sym` unbound NameError in
  `passes_smart_gate` = M-045/M-046/M-047 gates FAILED OPEN** + tests hitting live yfinance ^VIX
  (CI red whenever VIX>22 — this was THE "22 pre-existing CI failures" that blocked PR #856).
  Suite 119F→65F. Fail-open gates silently passing = exactly the doctrine class this session hunted.
- **grok-4.7 wrap** (PR #859 docs): live /audit was stale-stale until deploys converge; book state
  n=7,805 PF 0.91 PnL −77.7%; 0/10 money-ready; COMMODITY the only PF>1/n≥100 class (DSR 0).
  NOT fixed by them (by design): `money_ready_verdict.py` SPA-OR/PBO logic, `PROVEN` stamp at n≥10,
  live-Sharpe field — flagged as policy decisions.
- **Stuck dashboard run 43927541997** (generate-and-deploy since 19:52Z) — auditpage-v4 owns the
  stale-deploy recovery; no dispatch stacking while it runs.
- **Tooling recovery event**: `/tmp/kilo/gha_browser` was wiped by tmp cleanup mid-session —
  recovered instantly from the promoted `tools/gha_browser/` (the #844 promotion paid for itself
  within hours). Chrome CDP also died once; relaunched with the persistent profile — **login
  survived, no re-login needed** (`logged_in: true`).

## 3. SERVICENOW WORKSTREAM (the EBOND_ServiceNowSalesforce repo — answered via the bus)

| Item | State |
|---|---|
| PR #3 (v5-review: rate-limit bullet + field-ownership) | ✅ **CLOSED** (handled by the EBOND lead) |
| **PR #6 (v6 review)** | **OPEN + CONFLICTING (11 files)** — it is the *plan of record* for code gaps; the lead's standing guidance: "do not merge stale peer branches", implementers follow `2026-11-16-SWARM/07_final_review4/{IMPLEMENTATION_STEPS,TESTING_PLAN}.md`, `ACTIVE_REVIEW.md` on main points to the v6 artifacts. Left open deliberately (live E2E pending; a forced rebase-merge mid-E2E is how reviews get lost) |
| 4 live-instance verify items | spoke entitlement · SF DE API limit · SN OAuth grant type · SF API version — live-instance checks (need instance access) |
| `v1-bond-lab` branch | flagged redundant-deletion candidate — NOT deleted (AGENTS.md: never delete branches unconfirmed) |
| PR #3 (EBOND) field rename `x_snc_ebond` | REJECTED by lead — not creatable on a free PDI; stay on main |

## 4. REMAINING (final consolidated list)

**Owner-gated (human decisions):** 5 QA secrets (Issue #764 / PR #786 — QA Market churns hourly) ·
sports five (HIGH: auto-settle frozen) · AsterDEX gate · AI Tournament (5-month outage) · PM
promotion gates · alpha-fast ρ>1 interval · flat-exit `exit_price` fabrication · historical
`pnl_pct` DB migration (`--backfill-pnl-null --execute`, dry-run first) · 356 PF=999 sentinel rows
· #831 do-not-merge-but-merged anomaly · money_ready SPA-OR/PBO + PROVEN-n≥10 + live-Sharpe policy
(grok's list) · deploy-environment gating · timezone crons · `.env.events` review · v1-bond-lab
deletion confirm · EBOND live-instance verifies.

**Blocked:** 21 phantom queued runs → GitHub Support / admin PAT.

**Fleet-owned (in motion):** ultra_free #3/#4/#5/#6 (refresh run, active-picks filter, final_v001
integration, non-main hygiene — greenlit 20:35) · LEADER's reusable-workflow canaries (3-5 clean
runs before mass-convert) · auditpage-v4's stale-deploy recovery + ghost-threshold PR #855/864 era ·
grok's #856 (now likely superseded by 855's fix — they will reconcile).

**Watchers continuing:** 4h monitor cron · weekly deep review · guardian :37 self-reports ·
22:49 yf final proof · next resolver/db_health cycles (ghost freeze + resolved_unknown growth).

Entry points (unchanged): `13_FINAL_WRAP.md` (complete record + future-agent prompts) ·
`SUMMARY.md` · `IMPLEMENTATION_PLAN.md` · `AGENT_PROMPT_job_analysis.md`.

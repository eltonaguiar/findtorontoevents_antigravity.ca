# REMAINING WORK — ghactions-v2 / deepseek-flash — 2026-11-16T22:10Z

Companion to `GHACTIONS_2026-11-16/2026-11-16_2054Z_FINAL_WRAPUP/WRAPUP.md`.
This is the state AFTER the wrap: two earlier reds cleared, one real data-quality gate remains.

## Cleared since the final wrap (verified)
- ✅ **CI Tests** — RESOLVED by a peer (WF-verdict gate): 21:16, 21:17, 21:27Z all SUCCESS.
- ✅ **Feed Health** — my #850 fix holding: 20:39 + 21:39Z SUCCESS.
- ✅ **ALPHA `safe_push`** — verified earlier (run 43819637050, pushed attempt 2).

## Prioritized remaining (owner-gated; I did not change these unilaterally)

### P1 — live, real (not a workflow bug)
1. **`QA Market Validation` RED (hourly)** — the gate is CORRECT; it fails because of real data-quality
   flags: `EQUITY blank_tp/sl=6`, `mismatch=1`, `ETF mismatch=1` → **3 critical flags** → exit 1.
   **Do NOT disable the gate.** Fix the **equity pick emitter/resolver** to always emit non-blank
   `take_profit`/`stop_loss` and direction-consistent geometry. File: `tools/qa_ledger.py` (report only);
   fix belongs upstream (equity emitter + `audit_trail/universal_pick_resolver.py`).
2. **P1 DB integrity** (v4 audit): frozen resolution lanes (`trading_picks.intrabar_resolved_at`
   2026-06-09; `lm_signals.resolved_at` 2026-02-16), 2 PnL-poison rows (SHIBUSDT 1e6%, ARBUSDT 18611%),
   91,855 OPEN vs 21 ACTIVE, 105,669 duplicate rows, 2,688 impossible TP/SL. DB owner.

### P2 — runner/queue hygiene
3. **27 inline-push workflows → `safe_push.sh`** (same hang class as ALPHA). List + recipe:
   `GHACTIONS_2026-11-16/2026-11-16_05-20Z_push-hygiene/PUSH_HYGIENE.md`.
4. **Branch Large File Dup Guard 0/15** — global group + 2–3h all-branch scan; design call
   (scan-pushed-ref-only / per-ref group / disable).
5. **Zombie `Master Automation Scheduler`** — all 3 groups skip every fire.
6. **79 no-timeout workflows** — canary `timeout-minutes` waves: `APPROACH.md §6`.
7. **21 phantom queued runs** — API can't purge (409/403); GitHub Support ticket.

### P3 — cleanup / decisions
8. **19 never-run workflows** — archive→observe→delete.
9. Dashboard decisions: PM `whale/kalshi` gitignore (commit-or-drop); **23/24 `WIRED_IN` unwired**;
   AsterDEX `daily-summary` dead gate (needs Discord-post OK); `Discord Bot — Persistent` 24/7 (keep/stop).

## Open PRs at 22:05Z (peer-owned — not mine to merge)
`#861` docs/ghactions-v3-wrapup (clean computing) · `#859` docs/audit-grok-wrap (clean computing) ·
`#856` fix/dashboard-cse-new-picks-int (2 failing checks).

## Suggested prompt to the next agent
"Fleet is green except `QA Market Validation` (which correctly flags equity picks with blank TP/SL —
fix upstream, don't disable) and DB-integrity P1s. Read `GHACTIONS_2026-11-16/2026-11-16_2254…/REMAINING.md`
+ `…0620Z_CONSOLIDATED/SUMMARY.MD`. Start with the equity blank-TP/SL emitter fix, then the 27
inline-push migrations (PUSH_HYGIENE.md recipe)."

# Consolidated review — new .MD files (2026-06-18 20:00Z → 2026-06-19 04:15Z)
**Reviewer:** claude-opus (subagent read-across + my SQL/git verification) · READ-ONLY

## Verified ground truth (the facts the docs should agree with)
- **Honest ledger UN-FROZEN** (was the day's P0): `at_signal_outcomes` latest_created **2026-06-19 03:39**, latest_intrabar **03:58**; outcome-resolver runs 03:04 + 03:27 = **success** (the 03:02 failure was the last pre-fix run). → any "frozen since 06-12 / 6/6 failing" framing is now **stale**.
- Cited fix commits all exist on main: `e45c434b7`, `7a78863b5`, `4451526a6`, `e78c0bb83`.
- **Denominator = 0/10** (money_ready_verdict enumerates 10 classes, 0 passing). "0/9" is the legacy CLAUDE.md set — normalize to **0/10**.
- `crypto_rsi5070_us` status JSON is **stale** (generated 2026-06-13; still n=108) — the tracker hasn't re-run since the unfreeze; n hasn't accrued (the freeze paused it).

## Per-file verdict
| File | Verdict |
|---|---|
| SESSION_SUMMARY_claude-opus_2026-06-19 | **Canonical/current** — correctly documents the P0 as RESOLVED+VERIFIED. |
| INCIDENT_honest_ledger_frozen_2026-06-19 | **Needs RESOLVED banner** — title says "frozen"; body carries 2 obsolete root-cause theories (only the FMP-env converged cause is right). |
| IMPLEMENTATION_PLAN_honest_ledger_restore | **SUPERSEDED** — actual fix was FMP-env-wiring, not P0-3/P0-4; only **P0-5 (un-mask)** remains live. |
| SESSION_WRAP_2026-06-19 (peer) | Current but **omits the day's biggest P0** (ledger freeze/fix); says 0/9. Cross-link to SESSION_SUMMARY. |
| CRYPTO_RSI5070_US_LEAD_CANDIDATE | **Authoritative** for the lead (net 1.36 / CI-LB 0.95); gate ETA slips past Jun-25 due to the freeze. |
| PICKS_NOW_WHATIF / METHODOLOGY | Current 06-13 snapshots; their P1 (UNIQUE constraint) already shipped. |
| lifecycle_state_2026-06-18 (+.text) | **STALE** — intrabar n/PF on the frozen cohort; regenerate. Shows bare gross PF 1.535 (use net 1.36). |
| effective-n-shadow update | shrinkage off the frozen cohort; re-run. Says 0/10. |
| lifecycle-classifier-DNR-guard update | **Contradiction**: says "zero reach probation" but emitted lifecycle_state has probation:1; inline-DNR superseded by shared util. |
| edition_review + swarm_review | Forward proposals, current; swarm §3.1 "DNR not addressed" is stale (shipped as E12). edition_review §7 has ~4 **dangling update-file refs**. |
| section-anchor-guard / do-not-relitigate-shared-util updates | Current; minor count nit (EXACT 12+3=15≠13) + swapped E2/E6 labels. |

## Contradictions to normalize (same fact, different values)
1. **0/9 vs 0/10** → 0/10 (verified).
2. **lead PF 1.535 (lifecycle JSON, gross) vs 1.36 (net, authoritative)** → always cite net + CI-LB.
3. **"zero probation" vs probation:1** → probation:1 (crypto_rsi5070_us) is correct per the tool output.
4. **EQUITY n 113 vs 119** → ~6-row snapshot drift; both pre-unfreeze, will refresh.
5. **picks-now dedup 441→206 vs 647→206** → 647 raw is the source-of-truth baseline.
6. FOREX-consensus REFUTED — **consistent across all files** (no contradiction). Good.

## Actions taken
- INCIDENT → RESOLVED banner added. PLAN → SUPERSEDED banner added.
## Recommended follow-ups (not done here)
- Regenerate lifecycle_state + effective-n-shadow on the un-frozen cohort.
- Normalize 0/10 + net-PF-with-CI-LB across docs; fix the "zero probation" line + dangling edition_review refs.
- Ship P0-5 (un-mask) — the one live item from the superseded plan.

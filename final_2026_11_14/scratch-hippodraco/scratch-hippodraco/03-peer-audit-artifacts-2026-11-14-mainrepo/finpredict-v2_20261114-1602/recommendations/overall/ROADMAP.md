# Remediation Roadmap — 4 phases

**Principle:** truth before tuning. Phase 0 makes the dashboard stop lying; Phase 1 makes the
data consistent; Phase 2 makes the pipeline reliable; Phase 3 decides what to keep. No real-money
sizing until Phase 3 exit criteria are met.

## Phase 0 — Truth on day 1 (P0, ~1 day)

Goal: no impossible number and no fake "live" mark remains on the published surfaces.

| Item | Exit criterion |
|---|---|
| FX `KeyError: 'LONG'` guard | 24 h alpha failure count drops from 93 to 0 (or only unrelated failures) |
| `summary_picks` single-population query + assert | 0 classes with WR > 100% or `wins+losses > resolved` |
| Python 3.11 actually used + `xgboost` in FAST | dependency-install failure cluster = 0 in 24 h |
| audit-dashboard cron spaced / concurrency fixed | 0 zero-job cancels attributable to queue overflow in 24 h |
| Quote provenance + `UNQUOTED` | no row with `current_price == entry_price` displays `0.00%`; every active row has `quote_status` |
| Date-only timestamp rejection | 0 date-only `entry_time`/`signal_time` in new payloads |
| Vacuous PASS + `NOT_BUILT` | BOND/ETF/FUTURES show `INSUFFICIENT_DATA`; MUTUAL FUNDS shows `NOT_BUILT` |

## Phase 1 — Data consistency (week 1)

| Item | Exit criterion |
|---|---|
| Active population split (`curated` / `raw_open` / `expired` / `unpriced`) | tile and API agree across all classes |
| Dedup key + quarantine | `active_raw` unique IDs = rows minus documented duplicates; 0 duplicate IDs in default view |
| Symbol-authoritative class routing (flag) | COMMODITY/futures and ETF/equity/FOREX mismatches = 0 in shadow report |
| Zero-entry emitter fixes | 0 new `entry_price <= 0` rows |
| BOND price coverage + FRED re-enable | BOND priced coverage >= 80%; `bond_yield_curve_slope` uses FRED |
| `live_picks.db` refresh/retire | 0 active rows older than 60 d; PnL sign contradictions = 0 |
| Sidecar freshness manifest | every panel either fresh or explicitly hidden/labelled |

## Phase 2 — Pipeline reliability (week 2)

| Item | Exit criterion |
|---|---|
| Audit-dashboard runtime back under control | p95 successful run < 60 min; 7 d cancellation rate < 5% |
| Push/retry hardening | 0 workflows exhausting push attempts; mirror timeout resolved |
| Warning census + actionlint | 0 new deprecation warnings; actionlint clean on touched workflows |
| `audit_trail.db` population | consensus/feature/strategy tables non-empty; pick lifecycle emits CLOSED/EXIT/TP/SL |
| Resolver fairness audit | FORCE_CLOSED/TIME_EXIT exits are marked at defensible prices; documented method |

## Phase 3 — Decide what to keep (weeks 3–4)

| Item | Exit criterion |
|---|---|
| Time-ordered, policy-clean ledger | every closed pick has `closed_at`, `exit_price`, `resolution_kind`; no `ORDER BY strategy` pseudo-PBO |
| Multiple-testing gate | PBO/DSR computed on a time-indexed matrix with `n_trials >= 658`; Reality Check (`arch`) actually runs |
| Strategy kill/keep list | every strategy either clears Tier-2 on forward n>=100 or is quarantined; no silent survivors |
| Real-money gate | 0/9 remains the default unless a class clears Tier-2 with a positive, corrected edge |
| Mutual funds | either built with a real NAV source + coverage gate, or formally removed from the advertised class list |

## Sequencing constraints

- Do **not** do Phase 3 tuning before Phase 0/1 truth fixes: tuning on broken marks just fits noise.
- Do **not** re-enable the audit-dashboard `push:` trigger. Keep the hourly (or 2-hourly) cron.
- Do **not** delete rows. Quarantine/tag; the audit trail is the product.
- Every phase ships with `patch_plan/acceptance_tests.md` green and a changelog note for any
  published-number change.

## Master-review questions this roadmap answers

1. Which fixes are safe today? → Phase 0.
2. Which fixes stop the bleeding without changing strategy behavior? → Phases 0–2.
3. What evidence is required before claiming an edge? → Phase 3 gates.
4. What should be de-advertised rather than built? → MUTUAL FUNDS (`NOT_BUILT`).

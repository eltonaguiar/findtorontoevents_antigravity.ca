# Workflow Health Investigation — 2026-04-27

**Trigger:** User ran `workflow_health_check.py` + `find_stale_github_workflows` and reported: ETF Emitter 10/10 push failures, Unified Audit cancellations, CI Tests failures, daily-schedule 2-3 day gaps.

**Method:** 3 parallel subagent investigations + my own ETF Emitter probe.

**TL;DR:** 3 of 4 reported issues have actionable fixes (this PR ships all 3). 1 is a non-issue (calendar artefact).

---

## 1. ETF Emitter "all 10 push attempts failed" — push contention, not chronic failure

**Reality:** Last 10 runs are **8 success / 2 failure**, not 10 consecutive failures. The "10 attempts" is the within-run retry loop:
```bash
for i in 1..10; do git push origin main || sleep $delay; done
```
Each failed run burns all 10 retries before exiting. Workflow's own comment names the cause: *"40+ workflows push main."* When 40+ workflows auto-commit `[skip ci]` payloads concurrently, GitHub serialises pushes and rejects ones that lose the race.

**Fix (Fix #3 in this PR):** Widen retry jitter at `.github/workflows/alpha-engine-etf.yml:66-67`:
```diff
- delay=$((i * i * 3 + RANDOM % 15))
- [ $delay -gt 90 ] && delay=$((90 + RANDOM % 15))
+ delay=$((i * i * 5 + RANDOM % 30))
+ [ $delay -gt 120 ] && delay=$((120 + RANDOM % 30))
```
Spreads 10 retries across ~12 min instead of ~6 min, reducing the chance retries cluster inside the same push-storm. Self-healing already in place (next cycle regenerates data); this just reduces the rare miss rate.

---

## 2. Unified Audit Dashboard cancellations — USER manual cancellation, not workflow bug

**Subagent finding:** 15 cancelled runs in 7d on `main` (3 in last 24h, alongside 18 successes). API confirms `cancellation_reason: "eltonaguiar"` — USER-initiated. Runs have `jobs: []` — aborted before/during runner pickup.

YAML had `cancel-in-progress: false` (intentional, per old comment "preventing completion"). But that means push-triggered runs can't auto-supersede each other → user clicks cancel manually when fresh code lands.

**Fix (Fix #1 in this PR):** Split concurrency by event type:
```yaml
group: dashboard-publish-${{ github.event_name == 'push' && 'push' || 'cron' }}
cancel-in-progress: ${{ github.event_name == 'push' }}
```
Push: auto-supersede (no manual click). Schedule: still queue (the protection the old comment was guarding). The `[skip ci]` guard at line 95 still prevents self-trigger storms.

---

## 3. CI Tests — 93% success; one chronic flake remains

**Subagent finding:** 100 runs: **93 success / 7 failure (7%)**. Most failures already self-resolved. The one chronic flake on main:

```
tests/test_sports_endpoints_smoke.py::test_today_endpoint_responds_with_picks
  urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
1 failed, 1673 passed, 16 skipped
```

The test makes a live HTTPS call from inside the GitHub-hosted runner. GitHub Actions egress DNS occasionally fails (1-2% rate). Every prior run of this same test passed.

**Fix (Fix #2 in this PR):** Add module-level `pytestmark` with `pytest.mark.network` + DNS-probe `skipif`. When the runner can't resolve `findtorontoevents.ca`, the smoke tests are skipped (informative, not failed). Local dev unaffected (DNS works).

---

## 4. Daily-schedule "gaps" — calendar artefact, NOT drift

**Subagent finding:** Investigated 12 named workflows. **Every single one fired correctly per its declared cron.** The "2-2.6 day gap" is `Friday close → weekend → Monday open` — every "Daily" workflow declares `* * * 1-5` (Mon-Fri only).

| Workflow | Cron | Last run | Verdict |
|---|---|---|---|
| Daily Stock Refresh | `30 22 * * 1-5`, `0 14 * * 1-5` | 2026-04-24 22:47 | KEEP (weekend skip by design) |
| Forex Agent | `0 0,8,13,17 * * 1-5` | 2026-04-27 00:15 | KEEP (Mon 00:00 fired) |
| Equities/Bond/ETF/Commodities/Futures Agents | various `* * 1-5` | 2026-04-24 | KEEP (next Mon UTC) |
| Prediction Market | `*/30 * * * *` (24/7) | 2026-04-27 01:07 | KEEP (every 30 min) |
| Quick Guess ML | `9 * * * *` (hourly) | 2026-04-27 01:05 | KEEP (hourly) |

**No drift.** Only 4 of 295 workflows are manually disabled (`backtest.yml`, `deploy.yml`, etc., all intentional). GitHub's 60-day inactivity auto-disable did NOT trigger any of them.

**No code action needed.** Optional UX improvement: surface "next scheduled run" timestamps on the audit dashboard so weekend gaps don't trigger false-alarm reads. (Could fold into the freshness banner the user originally asked for; deferred.)

---

## Summary

| # | Fix | File | LOC | Impact |
|---|---|---|---|---|
| 1 | Audit Dashboard concurrency split | `.github/workflows/audit-dashboard.yml` | ~12 | High (eliminates manual-cancel toil) |
| 2 | Sports smoke tests skip on DNS fail | `tests/test_sports_endpoints_smoke.py` | ~30 | Medium (removes only chronic CI flake) |
| 3 | ETF Emitter retry jitter widen | `.github/workflows/alpha-engine-etf.yml` | ~5 | Low (rare transient mitigation) |
| 4 | Cron schedule audit | (none) | 0 | None (reassurance only) |

All 3 changes shipped in this PR. Each is reversible (single-file revert).

## Validation

- `python -m py_compile tests/test_sports_endpoints_smoke.py` → OK
- `yaml.safe_load(audit-dashboard.yml)` → OK
- `yaml.safe_load(alpha-engine-etf.yml)` → OK
- No production-code paths modified beyond CI/test infrastructure.

## Provenance

- Investigated 2026-04-27 ~01:30 UTC.
- 3 parallel subagent dispatches (Audit cancels + CI Tests + daily crons) + 1 inline ETF Emitter check.
- Raw subagent reports preserved in conversation log.

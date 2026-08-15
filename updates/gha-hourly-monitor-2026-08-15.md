# GHA Hourly Health Monitor — 2026-08-15

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests workflow not found by that name (404); primary CI equivalent is `Sports endpoint smoke + Playwright` (sports-smoke-and-e2e.yml) — **5 success, 0 failure, 0 in_progress** ✅

**robust-edge-miner (scheduled, 15-run history):** 15/15 consecutive `failure` — intentional alert mechanism: workflow exits 1 when NEW robust edge candidates are found. **5 new cells passed the full gate** (netPF≥1.2, bootCILB≥1.0, n≥40, both regimes):
- `CRYPTO|SHORT|RSI30-50|VOLLOW`
- `CRYPTO|SHORT|RSI50-70|US`
- `CRYPTO|SHORT|RSI50-70|VOLHIGH`
- `CRYPTO|SHORT|RSI30-50`
- `CRYPTO|SHORT|ASIA`

Known cell still robust: `CRYPTO|SHORT|VOLHIGH`. Stats: cells_tested=57, cohort_n=2265. Alert has been firing since ≥2026-08-08 without operator action (forward-register + falsify step not yet done).

Run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31885886238

**Chronic workflows (cancellation gate):** none — robust-edge-miner pattern is intentional alert exits (not cancellations); no workflows met the chronic-cancellation criteria (latest=cancelled + ≥4 cancels in 15 + 0 successes).

**Open PRs RED (test failures, stale from 2026-06-24):**
- **#667** `feat(b5): forward-track cell selector` — `test (3.11)` FAIL + `test (3.12)` FAIL → **AUTHOR_FIX** (assertion/import errors, stale since Jun 24)
- **#665** `audit(stalled-producer-detector): v2.0+2 frame-correction` — `test (3.11)` FAIL + `test (3.12)` FAIL → **AUTHOR_FIX** (same pattern, stale since Jun 24)

Other open PRs (#666, #657, #600, #595, #581, #564, #562) — check runs not recently updated; stale state expected on long-lived branches.

**Action required:**
1. **URGENT (robust-edge-miner):** Falsify + forward-register the 5 new CRYPTO|SHORT cells before any sizing. Add them to `KNOWN` set in the workflow gate check once falsified/registered, to stop the daily alert noise. Cells: RSI30-50|VOLLOW, RSI50-70|US, RSI50-70|VOLHIGH, RSI30-50, ASIA.
2. **PR #667 + #665:** Authors should fix test failures (`test (3.11)` + `test (3.12)`) or rebase onto current main.

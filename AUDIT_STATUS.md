# AUDIT STATUS — audit / audit2 / audit3

**As of:** 2026-11-23 · **Author:** copilot-cli-deepseek-flash
Paper only. Zero capital sanctioned. Not investment advice.

Every "done"/"open" claim below is backed by a command output, a file path, or a commit sha.
Nothing here is asserted from memory alone.

---

## Summary table

| Workstream | Done items | Open items | Next action |
|---|---|---|---|
| **`/audit`** (main dashboard, pick ledger) | Resolver PnL thresholds fixed per asset class (CRYPTO 0.1bp, others 5bp). Disputed CRYPTO 78.9% win-rate **caveat is now present on the surface** — verified `grep -c "DISPUTED\|78.9"` → 8 hits in `audit_dashboard/template.html`, 9 in `audit_dashboard/pick_funnel.html`. Cost of record reconciled: 5 round-trip costs in flight spanning 4.98→50.00bp (**10.04×**), 4 of them verdict-grade; `tools/cost_of_record.py` + `reports/cost_of_record_2026-11-23.json`. Beta-hurdle implemented (`tools/paired_bootstrap_vs_benchmark.py`, 13 tests). PIT filing lags measured at scale (480 tickers, 30,332 usable periods, **0 look-ahead violations**). | **Provenance T3 never observed emitting a row.** Fix committed at `5e044af5252` (sparse-checkout was missing `tools/` and `audit_trail/` — one cause, two "missing module" symptoms) but it has **never run in CI** because the branch `push/phase2-round-2026-11-22` carries foreign commits and must not be pushed. **Concentration gate before DSR/SPA still open P0** (2026-05-17; allowed two false Tier-1 passes). **0 of 6 asset classes survive deflation** at programme-level N=90 (SR\* 1.259 vs best observed ETF 1.05). COMMODITY cost is still a 4.97bp **PROXY**, not measured. | Prepare a clean branch containing **only** my commits so the T3 fix can be pushed and observed; then enforce the concentration gate before DSR/SPA. Both are infrastructure — neither adds a new trial. |
| **`/audit2`** (per-class verdict panel, forward clock) | `tools/build_audit2_per_class_panel.py` + `tools/build_audit2_pods.py` + `tools/audit2_forward_summary.py` exist with a golden-snapshot test harness. **34 of 35 audit2 tests pass.** Golden snapshot provenance is `independent_reference_implementation` (`tests/golden/audit2_per_class_verdicts.json`) — i.e. generated from a separate reference, not from the module under test. Forward clock frozen from 2026-11-23. | **`tests/test_audit2_per_class_panel.py::test_panel_matches_golden_snapshot` FAILS:** `CRYPTO.flat: panel 0 != golden 1`. The fixture deliberately contains `_pick("SOL-USD","CRYPTO", 0.0)` — a breakeven trade — and the independent reference counts `n=3, wins=1, losses=1, flat=1`. The panel returns `flat=0`, so **breakeven trades are being dropped or misclassified**. This matters beyond the test: the panel documents `win_rate_pct` as "percent of decided trades (excludes flat)", so a wrong `flat` count corrupts the denominator of every win rate it publishes. Forward clock still at `n_records: 0` (no closed forward rows yet). | Fix the flat classification in the rollup the panel consumes. **Do not regenerate the golden** — the test's own message ("a human must decide which is right") plus the explicit fixture row establish that the reference is right and the panel is wrong. Add a cases for `pnl == 0.0`, tiny-n, and negative-flat-pct so the denominator can't silently drift again. |
| **`/audit3`** (forward gate, evidence, tribunal) | **96 of 96 audit3 tests pass** across falsifiers, edge hunt, tribunal, expectancy gates, selection alpha, denylist hits and DB sync. Workflows present and wired: `audit3-health.yml`, `audit3-ledger.yml`, `audit3-evidence.yml`, `audit3-denylist-watchdog.yml`. Promotion path is defined as audit3 forward gate only. | Promotion gate has **nothing to promote**: 0 validated candidates, CRYPTO `PENDING_N` with 0 closed forward rows. A peer deep-review recorded **"audit3 unreproducible (rows file absent), surfaces contradict"** — reported, not independently reproduced by me this session, so it stays **UNVERIFIED** rather than confirmed. | Ingest forward observations so the gate sees its first closed rows, then re-run the reproducibility check on the rows file and resolve the UNVERIFIED peer claim either way. |

---

## Legend and honesty notes

- **DONE** = a command output or committed artifact exists that I ran or read this session.
- **OPEN** = named, with the specific file/test/path, so the next agent does not have to rediscover it.
- **UNVERIFIED** = someone else reported it and I have not reproduced it. Distinct from FAILED.
- The audit2 failure is **not** caused by my changes — I did not touch `tools/build_audit2_per_class_panel.py`. It is a pre-existing defect surfaced by running the suite.

### Evidence commands

```bash
# audit: caveat present on the live surface
grep -c "DISPUTED\|78.9" audit_dashboard/template.html audit_dashboard/pick_funnel.html
# -> 8 and 9

# audit: cost spread and cost of record
python3 tools/cost_of_record.py
# -> spread 4.98 .. 50.00 bp = 10.04x ; cost of record 4.98bp

# audit: PIT look-ahead at scale
python3 tools/pit_lookahead_audit.py
# -> 480 tickers, 30332 facts, 0 exclusion violations, 0 visibility violations

# audit2: the open failure
python3 -m pytest tests/test_audit2_per_class_panel.py -q
# -> 1 failed (CRYPTO.flat panel 0 != golden 1), 34 passed

# audit3: green
python3 -m pytest tests/test_audit3_falsifiers.py tests/test_audit3_edge_hunt.py \
  tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py \
  tests/test_audit3_selection_alpha.py tests/test_audit3_denylist_hits.py \
  tests/test_audit3_db_sync.py -q
# -> 96 passed
```

---

## The one number that governs all three

**0 of 6 asset classes survive deflated Sharpe at programme-level N=90** (SR\* = 1.259
annualised; best observed is ETF at 1.05, DSR 0.3191). 146 pre-registered hypotheses, 0/55
survive deflation.

Consequence for priority: the binding constraint across all three workstreams is **trial
debt, not missing tests**. Work that raises confidence in an existing number (fixing the
audit2 denominator, observing the T3 ledger, enforcing the concentration gate) outranks
work that produces a new number. A 0-entry ranked list remains the correct output, and an
empty list should not be softened into maybes to look productive.

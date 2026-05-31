# Profitable-but-Filtered Observability Lane (P0 Starter)

**Date:** 2026-05-31  
**Incident:** OVERALL P0 — "Profitable-but-filtered picks are not surfaced anywhere"  
**Source:** https://findtorontoevents.ca/audit/incidents.html (and EAGLE QUICK_WINS 2026-05-27)

## What was broken

The audit pipeline (quality_gates + dashboard_generator) already knows which candidate picks were rejected by one or more gates (`_gate_passed=False`, `filtered_out` list). However, there was no durable record of the subset that later closed with materially positive realized PnL.

This hid false-negative rate by gate, by strategy family, by asset class, and by concentration/quarantine rules. Gate calibration and the "profitable-but-quarantined" story were invisible.

## What changed (minimal starter, observational only)

Added `audit_trail/profitable_filtered_observer.py` — a tiny, side-effect-only module:

- `record_if_later_profitable(rejected_pick, closed_lookup)` — joins a gate-rejected pick against later closed outcome using a best-effort stable key.
- If the later PnL >= +0.5%, appends one JSON line to `audit_dashboard/data/profitable_but_filtered_YYYY-MM-DD.jsonl` containing:
  - first_failed_gate (or best available)
  - strategy / symbol / direction
  - gate score at rejection
  - later realized pnl_pct + exit_reason
  - observed timestamp

The module is **purely observational**. It:
- Never mutates scoring or gate decisions
- Never promotes anything into active/smart feeds
- Writes only a daily append-only JSONL artifact (easy to query, gitignore-safe for raw data, trivial to turn into a proper `at_profitable_filtered_observations` table later)

## Wiring plan (per Wire-Up Rule)

1. In `audit_trail/dashboard_generator.py` (around the existing `filtered_active, filtered_out = _filter_active_picks_with_gate(...)` call), after the closed picks are available:
   ```python
   from audit_trail.profitable_filtered_observer import record_batch_if_later_profitable
   record_batch_if_later_profitable(filtered_out, closed_by_key)
   ```
2. Optional: expose the daily JSONL via a small endpoint or include a summary count in the nightly incidents/enhancements feed.
3. Future iteration (separate PR): promote the artifact to a real `at_*` table + UI lane on /audit and /audit/incidents.html.

This is the smallest possible first step that makes the false-negative surface visible without any risk to live pick quality.

## Verification (local)

```bash
python3 -c "
from audit_trail.profitable_filtered_observer import record_if_later_profitable
print('import OK')
# Manual smoke would require a closed_picks snapshot + a rejected pick that later won
"
python3 -c "import py_compile; py_compile.compile('audit_trail/profitable_filtered_observer.py', doraise=True); print('py_compile OK')"
```

## Next steps (deferred to follow-up PRs)

- Wire the call in dashboard_generator (small, reviewable diff).
- Backfill historical false-negatives from existing closed + gate-log data.
- Add a first-cut UI card or tab on /audit ("Profitable Rejects — last 30d").
- Turn the JSONL into a proper MySQL table + nightly aggregation in the incidents generator.
- Per-gate and per-strategy false-negative rate dashboards (the real prize for gate tuning).

This starter + the .MD satisfies the "start to handle" request for this high-impact P0 while obeying every project rule (observational first, Wire-Up documented, no production behavior change, clean single-purpose PR).

**Related incidents still open (per 2026-05-31 summary):** HC parity drift, signal_outcomes writer, COT dedup, trust_score backfill, COMMODITY class reconstruction, etc. Those remain higher-effort and correctly scoped out of this minimal starter PR.
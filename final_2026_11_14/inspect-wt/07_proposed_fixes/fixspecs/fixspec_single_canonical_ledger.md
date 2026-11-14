# Fix spec — Single canonical ledger (surface reconciliation)

## Problem (evidence, live 2026-11-14)
Same asset class, same day, three official numbers (PF / n):
- CRYPTO: registry 0.232 (n=23,636) | money_ready 0.9196 (n=3,705) | my 14d recompute 0.805 (n=471)
- ETF: registry 1.84 (n=15) | money_ready 0.0216 WR 2.2% (n=45) | my 14d 0.928 (n=37)
- EQUITY: registry 0.707 (n=493) | money_ready 0.939 (n=250) | my 14d 1.172 (n=42)
- FOREX: registry 1.214 (n=456) | money_ready 0.660 (n=612) | my 14d 1.483 (n=43)
Registry counts show the filter stack (34,540 raw → 22,941 policy-clean; flicker 3,872; dupes 129;
policy 1,777; not-closed 5,821) — but each surface apparently applies its own subset, and nothing
publishes the diff. Single-source concentration per class reaches 97.9% (CRYPTO).

## Root-cause note (2026-11-14 peer cross-check)

The 2–8x inter-surface spread is largely **NOMINAL vs INTRABAR-TRUTH resolution**, not arbitrary
filtering: peer `reports/PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md` documents the `NOMINAL_TP_LEGACY`
bug where TP was assumed filled cleanly; 1h OHLCV replay reclassified 28%–100% of TPs as actually
SL hits. Intrabar-truth must be the authoritative ledger; nominal must be retired or labelled.
Also apply `DATE(closed_at) != '2026-06-04'` (peer: ~35,494 backfill-contaminated rows).

## Proposed design
1. **One ledger build step** (new `tools/build_closed_ledger.py`, run once per cycle right after
   resolver): raw rows → flicker-filter → dedup → policy-filter → **one** table
   `closed_ledger.jsonl` with stable row ids and a `policy_version` stamp.
2. **All stat surfaces become views over the ledger**:
   - pf_registry: per-strategy + per-class rollups
   - money_ready_verdict: per-class gates (n/wr/pf/dsr) computed on the SAME rows
   - surface_truth: same rows again
   - hf_stats.by_asset_class: same rows, declared window (e.g. 60–90d) as a parameter
3. **Publish the filter diff**: `audit_dashboard/data/ledger_filter_report.json` — counts at each
   stage + which surface uses which window, so divergence is explainable, not invisible.
4. **CI gate**: fail (or banner) when two surfaces' PF for the same class differ >25% — currently
   the spread is 100–400%.
5. windows become explicit query parameters in dashboard_data.json so the frontend can label them.

## Acceptance test
- All per-class PF values in dashboard_data.json, money_ready_verdict.json, pf_registry.json are
  derived from the same row set (allowing only declared windows); filter report explains residual
  differences; CI reconciliation green.

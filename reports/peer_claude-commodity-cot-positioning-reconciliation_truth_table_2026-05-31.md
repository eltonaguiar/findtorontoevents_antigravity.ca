# Truth-Table: cot_positioning DSR=1.0 (Ring) vs BLOCKED (audit benchmark)

**Incident:** INCIDENT_COMMODITIES #3 (P0)
**Date:** 2026-05-31
**Reporter:** claude-opus-4-7 (peer-verify pass)
**Grok-4 sanity-check:** reports/peer_claude-commodity-cot-positioning-reconciliation_grok_consult_2026-05-31.md

## TL;DR

The contradiction was a data-pipeline artifact: the same weekly CFTC COT release was re-emitted ~7.33x as if each were an independent trade, inflating n and Sharpe-family metrics. Under proper one-trade-per-release dedup, n drops to 6 unique releases with WR=33%, cum PnL=-$6547, DSR withheld (n<20). **Audit benchmark BLOCKED was correct. Ring's DSR=1.0 / SUPREME EDGE callout was falsified.** Strategy held in `SHADOW_INSUFFICIENT_N` per cot_paper_pilot_status.json policy until ≥20 unique releases accumulate.

## Truth-Table (live-verified 2026-05-31)

| # | View | Source (live path) | n | WR | PF / cum PnL | DSR | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Ring's 2026-05-25 SUPREME EDGE claim | reports/2026-05-25_commodity_cot_edge_consult_grok.md | 104 | 86.5% | high (claimed) | 1.0 | **FALSIFIED** |
| 2 | Raw `trading_picks` (cot_positioning, commodity, all-time) | live MySQL `ejaguiar1_stocks.trading_picks` | 51 total / 46 closed | TP_HIT=2, LOST=1, TIME_EXIT=42, EXPIRED=1 → ~13% non-flat WR | PF<1 (avg pnl negative) | n/a | Not edge |
| 3 | `at_signal_outcomes` deduped path | live MySQL `ejaguiar1_stocks.at_signal_outcomes` strategy='cot_positioning' | 4 | low | low | n/a | INSUFFICIENT_N |
| 4 | Paper-pilot deduped by unique CFTC release week | audit_dashboard/data/cot_paper_pilot_status.json | **6 unique / 44 raw emissions** (7.33x ratio) | 33% | cum PnL -$6547.57 | withheld (n<20) | **SHADOW_INSUFFICIENT_N** |
| 5 | Sister strategy `cftc_cot_commercial_signal` (cross-check) | live MySQL trading_picks | 37 closed | TP_HIT=3, LOST=2, TIME_EXIT=30 | PF<1 | n/a | BLOCKED (INCIDENT_COMMODITIES #1) |

## Reconciliation

| Claim | Reality | Root cause |
|---|---|---|
| Ring: DSR=1.0, WR=86.5%, n=104 | Paper-pilot: WR=33%, n=6 unique, DSR withheld | 7.33x over-emission of same weekly CFTC release |
| Audit benchmark: BLOCKED | Confirmed: no clean edge, sample too small even after dedup | Same — once you dedup by release, n collapses below DSR threshold |

## Unexplained gap (per Grok-4 sanity check)

Ring's claim of **n=104** does not reconcile with any live table:
- Raw `trading_picks` (cot_positioning, commodity): 51 total / 46 closed.
- `at_signal_outcomes`: 4.
- Paper-pilot raw emissions: 44.
- Deduped unique releases: 6.

Hypothesis: Ring's n=104 was either (a) a hallucinated/fabricated figure (Cloudflare-hosted LLMs are known to confabulate numbers per CLAUDE.md guidance), (b) pulled from a now-deleted stale registry snapshot, or (c) multi-horizon emission (entry × N hold horizons treated as N picks). No live source supports it. Per Grok-4: "raw n=46 vs claimed n=104 still unexplained — further leakage or multi-horizon emission?" Flagged for INCIDENT_COMMODITIES #7 follow-up (over-emission audit), not blocking for #3 closure since the verdict (FALSIFIED) is the same regardless of which inflated path produced n=104.

## Tier decision

`SHADOW_INSUFFICIENT_N` (not hard BLOCKED) is correct per Grok-4: hard BLOCKED is reserved for strategies whose edge fully vanishes after proper dedup AND n_unique ≥ 20. cot_positioning has not yet reached n_unique ≥ 20 unique CFTC releases, so the tier withholds judgment. If, when n_unique ≥ 20, the deduped WR stays <50% and PF<1, escalate to BLOCKED.

## References

- audit_dashboard/data/cot_paper_pilot_status.json (live, tier=SHADOW_INSUFFICIENT_N)
- reports/cot_paper_pilot_overemission_falsified_20260513.md (original falsification)
- reports/cot_timing_leakage_audit_2026-05-13.md
- reports/commodity_cot_post_dedup_rederivation_2026-05-16.md
- reports/2026-05-25_commodity_cot_edge_triangulation.md
- INCIDENT_COMMODITIES #5 (RESOLVED 2026-05-31): COMMODITY headline contamination by pre-clean COT
- INCIDENT_COMMODITIES #7 (TRIAGED): formal over-emission incident with the 7.33x ratio

## Closure action

Set `INCIDENT_COMMODITIES.incident_id=3.status='RESOLVED'`. `resolved_at` is already set (2026-05-31 02:06:58); only the status field needs flipping. Resolution_notes already contain the substantive reconciliation; this report adds the peer-verified truth-table and Grok-4 sanity check.

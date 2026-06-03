# Resolver-Hygiene Scan — alpha_engine/data/closed_picks.json (2026-06-02)

Report-only run of `tools/resolver_hygiene_check.py` (INCIDENT_CRYPTO #8). No ledger mutated.

> NOTE: this is the **fallback** ledger (496 rows). `money_ready_verdict` normally reads the
> wider canonical pipeline (`load_rows()` over SOURCE_FILES). The MDD=1.0 / CVaR95 -85% CRYPTO
> tail pollution is expected to live in that wider set, not this small fallback — a follow-up
> should run the checker over the canonical rows.

## Results (after dup-key false-positive fix)
| Scope | n | never_closed | dup_groups | mislabels | missing_provenance | no_signal_ts |
|---|---:|---:|---:|---:|---:|---:|
| OVERALL | 496 | 1 | 0* | 0 | 119 (24%) | 496 |
| CRYPTO | 143 | 0 | 0* | 0 | 37 (26%) | 143 |

\* The first run reported 89 OVERALL / 31 CRYPTO "duplicate groups" (367 / 92 rows). Those were
**false positives**: `signal_ts` is empty on every row, so the key `(symbol, '', strategy)` collapsed
all of a symbol's signals into one group. Fixed: dedup now requires a non-empty `signal_ts`, and
`rows_without_signal_ts` is reported separately.

## Actionable findings
1. **`signal_ts` is missing on 100% of rows** in this ledger → flicker-dedup cannot run here at all.
   Populating `signal_ts` upstream is prerequisite to any real duplicate detection.
2. **~25% of rows lack source provenance** (`source_system`/`source_id`) → blocks the #65
   single-source gate from judging those rows; provenance tagging (BONDS-style) needed.
3. mislabels / never-closed are clean in THIS file → confirms the tail pollution is in the wider
   canonical pipeline; re-run the checker there before any purge.

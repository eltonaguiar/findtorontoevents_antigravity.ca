# Provenance / signal_ts Backfill — Swarm Decision + Real Coverage (2026-06-02)

## How this was chosen
Asked a 6-model swarm (nvidia-deepseek-v4-pro, deepseek-chat, paid-mode-large, hybrid-large,
cloudflare-llama, ollama-cloud-local) for the single highest-value AUTONOMOUS next step toward a
real-money-ready class. Consensus (strongest reasoning: nvidia + hybrid): **reconstruct the missing
`signal_ts` + provenance**, because the just-shipped FDR/single-source/drift gates all operate on
the closed-picks ledger and were running on un-auditable data (signal_ts absent, ~11% no source) —
the 208-trade tournament sample was not statistically valid. This matched the gap my own resolver
scan had already measured, so I built it.

## Tool (report-only, never mutates the ledger)
`tools/backfill_provenance.py` — reconstructs `signal_ts` from the first populated of
entry_date/entry_time/timestamp/created_at/_replay_bar_date, and `source` from
source_system/source/original_source/source_integration/_source_file (last resort: infer from the
strategy slug). Emits coverage stats + a shadow-audit proposals JSON. 5 unit tests.

## Real coverage on alpha_engine/data/closed_picks.json (1054 rows)
| Field | present | recoverable | inferred | unrepairable | coverage after backfill |
|---|---:|---:|---:|---:|---:|
| signal_ts (OVERALL) | 0 | 472 | — | 582 | **44.8%** |
| source (OVERALL) | 934 | 1 | 102 | 17 | **98.4%** |
| **signal_ts (CRYPTO)** | 0 | 144 | — | 0 | **100%** |
| **source (CRYPTO)** | 106 | 1 | 37 | 0 | **100%** |

## Why this matters
- **CRYPTO becomes fully auditable**: all 144 CRYPTO rows get a recoverable signal_ts + source ->
  flicker-dedup + the single-source gate + FDR can finally run on real CRYPTO data.
- OVERALL signal_ts only 44.8% recoverable -> the other 582 rows (mostly non-CRYPTO) genuinely lack
  any timestamp field and must be excluded from any time-dependent statistic until fixed upstream.

## Next (human-approved) step
Run with `--out reports/provenance_backfill_proposals.json`, review, then a separate apply-PR can
write `signal_ts`/`source` back (with an `_backfilled=true` flag) — NOT done here (report-only).

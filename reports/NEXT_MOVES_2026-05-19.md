# Next Moves — Path Toward Profitable — 2026-05-19

The execution roadmap after 14 harness kills, 0 admissible. Synthesised from
30+ AI-model consults (swarm + Grok + extended panel + local) — all converge on
one spine. This is the ordered plan; tiers 1→2 are "toward profitable", 3→4 are
value-regardless.

**Honest framing:** "profitable" near-term = paper-only. The path is: fix the
data layer so verdicts are trustworthy → run the ONE untested edge axis (crypto
intraday/tick) as a 2-4 week probe → if it clears the harness, forward-test →
only then real capital. Realistic odds the probe passes: 5-20%. If it kills,
that is kill #15 and paper-only becomes permanent. Tiers 1+4 are worth doing
regardless — they make the system an honest measurement instrument.

## Tier 1 — Data integrity (do first; unblocks every verdict)

| # | task | detail | issue |
|---|------|--------|-------|
| 1 | Fix corrupted `confidence` field | 146 CRYPTO rows hold values 15-78 (domain 0-1). Clamp/reject >1.0 at ingestion; trace the percent-as-integer emitter. | #1241 |
| 2 | Widen harness ledger scope | `edge_stability_harness.py` reads 1 of 32 ledger files — cannot see `ensemble`/`st_fear_greed` cohorts. | #1242 |
| 3 | Apply the scale-mismatch backfill | `tools/backfill_resolver_scale_mismatch.py` dry-ran, found the corrupt HG=F row; run `--apply` (with .bak). | — |
| 4 | Dashboard → `pf_registry` canonical | Stop the inflated tiles (EQUITY 78% WR raw vs 33% canonical). | #1221 |

## Tier 2 — The one real edge bet (paper, ~5-20% odds)

| # | task | detail |
|---|------|--------|
| 5 | H-032 crypto intraday/tick microstructure | Pre-register (M-107) order-book-imbalance reversion at TICK resolution — the one axis the 11 kills point toward. Build Binance 1m/aggTrade fetch → harness. A 2-4 week PROBE, not a 3-month build. |
| 6 | H-033 / H-034 new EQUITY seeds | Residualized overnight-return cross-sectional reversal + anti-PEAD 1-day reversal (extended-consult seeds). Pre-register → build → harness. |

## Tier 3 — Forward-track what is already in-sample-profitable

| # | task | detail |
|---|------|--------|
| 7 | `mega_mutation` paper-pilot | Built 2026-05-19; let forward picks accrue — the forward result is the verdict. |
| 8 | `st_fear_greed_contrarian` accrual | Let it reach n~400 (~10 weeks); re-harness monthly. |

## Tier 4 — Infra / coverage gaps (value regardless)

| # | task | detail |
|---|------|--------|
| 9 | Stage B writer flip | `active_picks_sync --apply` after 3-5 clean dry-run cycles (concurrency cascade fixed). |
| 10 | FUTURES orphan-source fix | `alpha_engine_unified` not in resolver `SYSTEM_SOURCES`. |
| 11 | `/audit` auxiliary 404s | `pf_registry.json` / `money_ready_filter.js` 404 on the live site — deploy doesn't ship the aux files. |

Each Tier-2/3 hypothesis runs through the `hypothesis-registry` skill →
pre-register → harness. Verdicts: `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md`,
`reports/MACRO_WHY_NO_EDGE_2026-05-18.md`, `reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19.md`.

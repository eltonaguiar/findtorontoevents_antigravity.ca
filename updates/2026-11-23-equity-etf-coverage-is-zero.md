# EQUITY / ETF / BOND realized-return coverage is ZERO across all local sources

**Date:** 2026-11-23T06:23Z · **Author:** Kilo · Paper only.

## The search (exhaustive)
| source | rows | dated | realized pnl | classes |
|---|---:|---:|---|---|
| `alpha_engine/data/closed_picks.json` | 2,204 | 290 | yes | EQUITY/ETF rows are **all synthetic** (undated, barrier-quantised) |
| `mercury2/data/closed_picks.json` | 469 | 0 | — | no asset_class, no entry_date |
| `paper_trading/data/closed_picks.json` | 34 | 34 | yes | **crypto only** |
| `audit_dashboard/data/wired_in_childlike_active_picks.json` | 3 | 3 | **OPEN, pnl 0.0** | ETF/EQUITY/BOND but no exit |
| `KIMI_RISEOFTHECLAW/data/live_competition.json` | 0 | — | — | — |

## Conclusion
There is **no realized, dated EQUITY/ETF/BOND closed-trade series anywhere in the estate.** The only EQUITY/ETF/BOND
rows that exist are (a) synthetic placeholders in alpha_engine and (b) three still-open positions in wired_in.

## Why this matters for my published ranking
My EQUITY top picks (CVX n=35 DSR 0.318, AMD n=83, AAPL n=81 …) come from the **audit3 ledger's `symbols` block**,
which I **cannot independently verify** against realized dated trades. So EQUITY/ETF should be labelled
**UNMEASURABLE**, not "measured net-positive" — the ledger figure is an input of unknown provenance, and the
survivorship-biased universe compounds it.

This does not change the verdict (still 0 investable) — it **strengthens** it: even the "best" class's numbers rest on
data we cannot check. Until a realized, dated EQUITY/ETF series exists, those rows are CANDIDATE-grade at best.

*Paper only. Not investment advice.*

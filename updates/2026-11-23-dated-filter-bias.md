# Methodology check (prompted by FreeBuff): does my dated-only filter flatter classes?

**Date:** 2026-11-23T08:22Z · **Author:** Kilo · Paper only.

## Why I checked
FreeBuff's AUDIT2 finding: quarantine-every-zero-PnL **deletes breakeven trades and flatters a class** (CRYPTO
0.4003 → 0.2336 once fixed). My method filters to `entry_date IS NOT NULL`. I ran the analogous test.

## Results (canonical: measured on current `origin/main`, 505 rows)
| class | ALL-rows mean | dated-only mean | bias (dated − all) |
|---|---:|---:|---:|
| FOREX | −0.0553% | **−0.0002%** | **+0.0551%** (flatters ~5.5 bp) |
| CRYPTO | +0.0049% | +0.0149% | +0.0100% |
| COMMODITY | −0.0131% | −0.0090% | +0.0042% |
| EQUITY | −0.0273% | (1 dated) | — |
| STOCKS | +0.0653% | **0 dated** | all STOCKS rows are dateless here |

## What this means
1. **Breakevens are safe.** All zero-PnL rows are **dated**, so my filter **keeps** them — I am NOT reproducing FreeBuff's
   exact defect. Good.
2. **But the filter still flatters FOREX by ~5.5 bp/trade** because 54 *dateless* rows are more negative and get excluded.
   So "FOREX ≈ breakeven" (dated-only) is optimistic; on ALL rows it is **−5.5 bp/trade**, worse after the 7.5 bp cost.

## Correction to my own reporting
Any FOREX statistic I quote must say **which population**: ALL-rows (FOREX −5.5 bp/trade) or dated-only (−0.0 bp/trade).
The honest read is the ALL-rows one for class-level claims. **This strengthens the verdict** — FOREX is more negative than
my dated-only table implied, and still nowhere near investable (net −13 bp after cost).

Tool: `tools/filter_bias_check.py` → **run it on main**; on a stale base the class mix differs (my worktree's copy carries
pre-purge rows).

*Paper only. Not investment advice.*

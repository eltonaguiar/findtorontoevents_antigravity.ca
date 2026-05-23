# EQUITY Source Reconciliation — 2026-05-18

Every EQUITY (n, WR, PF) record found across the repo:

| source | n | WR | PF | note |
|---|---|---|---|---|
| `asset_class_health.EQUITY` | 240 | 53.3% | 1.97 | status=stable; realized_wr_30d=None (n=None) |
| `by_asset_class.EQUITY` | 342 | 53.3% | 1.97 | active=67 closed=342 |
| `closed_picks.json EQUITY` | 44 | 36.4% | 0.71 | raw ledger |
| `at_consensus_picks (MySQL)` | 738 | 1.2% | 0.09 | resolved consensus picks |

## Root cause

WR ranges **1.2% – 53.3%** (spread 52 points) across 4 EQUITY records in ONE repo. These are not the same data resolved differently — they are **different pick populations**: each subsystem (`asset_class_health`, `hf_stats`, `by_asset_class`, the consensus DB, the JSON ledger) applies its own window, filter, and resolver and reports its own n.

**There is no canonical EQUITY resolved-pick set.** That is the bug — not corruption in any one table, but the absence of a single source of truth. The session's 'EQUITY = best candidate' (from `hf_stats`/`by_asset_class`, WR 52-54%) and 'EQUITY no-edge' (from `asset_class_health`, WR 35%) are both quoting real numbers from non-comparable populations.

## Fix (upstream — peer-coordinated)

1. Designate ONE canonical EQUITY resolved-pick source (recommend the consensus DB once the non-crypto resolver is fixed — it is the post-gate layer with the most rows).
2. Make `asset_class_health`, `hf_stats`, `by_asset_class` all read that one source with an explicit, identical window.
3. Re-run `tools/equity_mysql_edge_test.py` against the canonical set — only then is an EQUITY edge verdict trustworthy.

Until then: **no EQUITY edge claim, bullish or bearish, is valid.** The data must agree with itself first.
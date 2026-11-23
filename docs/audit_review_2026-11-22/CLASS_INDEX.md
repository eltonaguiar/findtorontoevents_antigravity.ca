# Class index

This is the index of the class dossiers in this directory. It reproduces the verdicts
already recorded in each dossier; it does not produce or upgrade any of them. The
per-class evidence lives in the dossier, and this file only points at it.

## Class to dossier

One row per class, all thirteen. The verdict column quotes the existing per-surface
vocabulary from [`README.md`](README.md) (the `/audit3` ledger verdict, the `/audit`
readiness `gate_state`, and the `/audit` `money_ready_verdict`), and the reason is the
dossier's own blunt answer. No verdict here is new.

| # | Class | Dossier | Verdict (existing vocabulary) | One-line reason |
|---|---|---|---|---|
| 01 | CRYPTO | [`01_CRYPTO.md`](01_CRYPTO.md) | `/audit3` KILL, `/audit` MONITORING, `money_ready` NOT_READY | NO edge: negative selection alpha with a CI that excludes zero |
| 02 | EQUITY | [`02_EQUITY.md`](02_EQUITY.md) | `/audit3` WEAK, `/audit` MONITORING, `money_ready` NOT_READY | NOT PROVEN: PF above one but the CI straddles zero and the split halves disagree |
| 03 | ETF | [`03_ETF.md`](03_ETF.md) | `/audit3` WEAK, `/audit` MONITORING, `money_ready` INSUFFICIENT_DATA | NOT PROVEN: net expectancy indistinguishable from zero, cost eats the gross edge |
| 04 | FOREX | [`04_FOREX.md`](04_FOREX.md) | `/audit3` WEAK, `/audit` BLOCKED, `money_ready` NOT_READY | UNMEASURED (coverage) and NOT PROVEN on the edge |
| 05 | COMMODITY | [`05_COMMODITY.md`](05_COMMODITY.md) | `/audit3` KILL, `/audit` BLOCKED, `money_ready` NOT_READY | NO edge: KILL, CI entirely below zero, negative selection alpha |
| 06 | BOND | [`06_BOND.md`](06_BOND.md) | `/audit3` WEAK, `/audit` BLOCKED, `money_ready` INSUFFICIENT_DATA | UNMEASURED at the dashboard and WEAK-but-unproven at the ledger |
| 07 | FUTURES | [`07_FUTURES.md`](07_FUTURES.md) | `/audit3` INSUFFICIENT_N, `/audit` BLOCKED, `money_ready` INSUFFICIENT_DATA | UNMEASURED: n 4 on the ledger, no DSR, one source |
| 08 | MUTUAL_FUND | [`08_MUTUAL_FUND.md`](08_MUTUAL_FUND.md) | `/audit3` absent, `/audit` MONITORING, `money_ready` INSUFFICIENT_DATA | UNMEASURED: a required placeholder with zero rows |
| 09 | PENNY_STOCK | [`09_PENNY_STOCK.md`](09_PENNY_STOCK.md) | `/audit3` absent, `/audit` MONITORING, `money_ready` INSUFFICIENT_DATA | UNMEASURED: four trades, no intrabar truth, no DSR baseline |
| 10 | MEMECOIN | [`10_MEMECOIN.md`](10_MEMECOIN.md) | `/audit3` absent, `/audit` MONITORING, `money_ready` INSUFFICIENT_DATA | NOT PROVEN, leaning NO; the ghost-row question is unmeasured |
| 11 | INDEX | [`11_INDEX.md`](11_INDEX.md) | `/audit3` absent, `/audit` absent, `money_ready` absent | UNMEASURED as a class; it is an alias, not a class |
| 12 | SPORTS | [`12_SPORTS.md`](12_SPORTS.md) | `/audit3` absent, `/audit` absent, `money_ready` absent | UNMEASURED and out of scope until a settlement contract exists |
| 13 | PREDICTION_MARKET | [`13_PREDICTION_MARKET.md`](13_PREDICTION_MARKET.md) | `/audit3` INSUFFICIENT_N, `/audit` absent, `money_ready` absent | UNKNOWN, not investable and not yet disprovable: zero settled contracts |

The three P0 findings that cut across every class (negative selection alpha, stale and
broken data paths, verdict labels without measurement) are in [`README.md`](README.md)
and per-class in each dossier's section 4.

## Boundary: per class, not per page

These dossiers are **per asset class, not per page**. The audit surfaces (`/audit`,
`/audit2`, `/audit3`) and the sibling reports are cross-class dashboards: one page shows
many classes at once, and one class appears on several pages. There is therefore no 1:1
mapping from a page to a dossier, and none should be manufactured. A dossier answers
"what is the measured state of this class", not "what is on this page". The page-to-fetch
map and the contradiction register live in
[`00_SURFACE_BASELINE.md`](00_SURFACE_BASELINE.md).

## Taxonomy: eight canonical classes versus thirteen dossiers

The single most confusable thing about this set is the count mismatch. It is not an
error in either place, but it needs stating up front:

- **Eight canonical classes** are defined in code at
  [`alpha_engine/money_ready_verdict.py:239`](../../alpha_engine/money_ready_verdict.py:239):
  `CANONICAL_ASSET_CLASSES = ("CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BOND", "FUTURES", "MUTUAL_FUND")`.
- **Thirteen dossiers** exist here because the review also covered names that are not
  canonical classes: `INDEX` (an alias for an already-counted bucket), `SPORTS` (out of
  scope), `PREDICTION_MARKET` (adjacent signal source), `PENNY_STOCK` and `MEMECOIN`
  (labels on picks that are counted under EQUITY and CRYPTO respectively).

Every dossier maps back to the canonical set, but not every dossier is a canonical
class. **PREDICTION_MARKET is adjacent-only**: it is not one of the eight. Its dossier
records that it has no class bucket of its own in the ledger, that its trades are filed
under CRYPTO as strategy `prediction_market_consensus`, and that the name exists in code
only as a contract marker (`asset_class in {"PREDICTION_MARKET", "PREDICTION_MARKETS", "EVENT_CONTRACT"}`,
[`13_PREDICTION_MARKET.md`](13_PREDICTION_MARKET.md) section 1 citing
[`audit_trail/pm_contract_resolver.py`](../../audit_trail/pm_contract_resolver.py)). It is
a signal source to review, not a class to size.

Read the eight canonical names as the sizing universe, and the thirteen dossiers as the
review universe: the review is a superset on purpose, because a name that looks like a
class must be investigated before it can be dismissed.

# Class index, stub reconciliation, and PMC guard gate wiring

Block 51 closed the audit-page arc. Three changes, all documentation or CI:

## 1. The six `docs/asset_classes/` stubs became compatibility pointers

The six loose stubs were prose references written before the audit review, with
no measured numbers and several unverified performance claims (a "75%+ WR"
assertion in STOCKS, "Sharpe 4.84" in FUTURES_INDEX, a "Sharpe 0.5-1.2" carry
estimate in FOREX, and so on). After Blocks 48-50 the thirteen evidenced
dossiers exist, so each stub is now duplicated in substance and contradicted in
authority by the real dossier.

They were **converted**, not kept and not deleted:

- **Not kept**, because a second prose reference for the same class, carrying
  unverified numbers that the dossier has since measured, is exactly the stale
  number this arc has been removing. Keeping it would leave two answers to
  "what is the state of this class".
- **Not deleted**, because [`docs/MULTI_ASSET_GAMEPLAN.md`](../docs/MULTI_ASSET_GAMEPLAN.md)
  links all six by filename, and external links cannot be ruled out. Deleting
  would break those paths.

Each stub keeps its `# Title` H1 (no stub had YAML frontmatter, so nothing else
had to be preserved) and its body is now a short pointer to the authoritative
dossier, with **no numbers of its own** beyond the dossier filename in the link.

## 2. Mapping, including the FUTURES/INDEX many-to-one

| Stub | Dossier(s) |
|---|---|
| `STOCKS.md` | `02_EQUITY.md` |
| `ETFS.md` | `03_ETF.md` |
| `FOREX.md` | `04_FOREX.md` |
| `FUTURES_INDEX.md` | `07_FUTURES.md` **and** `11_INDEX.md` (one-to-many) |
| `MEME_COINS.md` | `10_MEMECOIN.md` |
| `PENNY_STOCKS.md` | `09_PENNY_STOCK.md` |

`FUTURES_INDEX.md` is the only ambiguous case: it is a single combined file,
while the dossiers review futures and index separately. Its pointer names both
dossiers and says the combined file is not itself a class. (`11_INDEX.md`
records that INDEX is an alias for a bucket already counted under ETF, not a
canonical class.)

## 3. `CLASS_INDEX.md` and the boundary

[`docs/audit_review_2026-11-22/CLASS_INDEX.md`](../docs/audit_review_2026-11-22/CLASS_INDEX.md)
adds a class -> dossier -> verdict -> reason table for all thirteen classes,
reproducing the verdicts already in `README.md` and the dossiers (no new
verdicts, none upgraded), plus two statements that belong in an index:

- **Boundary:** the dossiers are per asset class, not per page. The audit
  surfaces are cross-class dashboards, so there is no 1:1 page-to-dossier
  mapping and none is manufactured.
- **Taxonomy:** eight canonical classes in
  `alpha_engine/money_ready_verdict.py:239` versus thirteen dossiers, with
  PREDICTION_MARKET marked adjacent-only (it has no class bucket; its trades are
  filed under CRYPTO).

It was added as a new file rather than a README section so the README stays the
verdict table and the index stays the entry point. The index states no
programme tally.

## 4. The PMC promotion guard is now wired into `verification-tests.yml`

[`tests/test_pmc_promotion_consistency.py`](../tests/test_pmc_promotion_consistency.py)
(added in Block 50, six tests) was absent from the gate's path filter and pytest
command, so it never ran in CI.

- Added to the `pull_request` and `push` path filters:
  `tests/test_pmc_promotion_consistency.py`,
  `tools/prediction_market_consensus_pilot.py`, `tools/pmc_pilot_monitor.py`,
  `tools/track_pmc_paper_pilot.py`, `verified_strategies/paper_pilot/**`.
- Added to the pytest invocation alongside the other three suites.

**Sparse-checkout finding:** `verification-tests.yml` does not use
`sparse-checkout` at all. It is a plain `actions/checkout@v5` with a depth-1
fetch, so the whole tree, including `verified_strategies/paper_pilot/` and the
three `tools/` files, is present in the checkout. The guard therefore reads its
real inputs in CI and needed no "skip with a reason" fallback. (Other workflows
in the repo do use sparse checkout, but not this gate.)

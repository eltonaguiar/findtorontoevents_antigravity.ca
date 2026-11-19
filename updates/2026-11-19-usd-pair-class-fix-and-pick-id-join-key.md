# BASE-USD crypto pairs no longer classify as equity; pick ids get a join key

**Date:** 2026-11-19 · **Files:** `alpha_engine/asset_class.py`,
`alpha_engine/symbol_identity.py`, `alpha_engine/resolved_closed_view.py` (+ 2 test files)

---

## 1. The emitter defect: why 209 crypto picks were written as `asset_class='equity'`

`normalize_asset_class()` in `alpha_engine/asset_class.py` is the function
`audit_trail/universal_pick_resolver.py:992` uses to stamp `asset_class` on every row it
inserts into `at_pick_outcomes`. Its detection order was:

```
= F / = X suffix  →  stablecoin suffix  →  6-char forex pair  →  category field
→  source/strategy hints  →  known symbol sets  →  return "equity"
```

The stablecoin check is `sym_core.endswith(("USDT","BUSD","USDC","DAI","TUSD","USDP"))`,
and `sym_core` comes from `normalize_symbol()`, which **deletes the `-` separator**:

| step | value |
|---|---|
| input | `ADA-USD` |
| `normalize_symbol` | `ADAUSD` |
| matches any `_CRYPTO_SUFFIXES`? | no — the tuple has `USDT`/`USDC`, **not bare `USD`** |
| 6-char forex pair? | `ADA` is not a forex code |
| known symbol sets? | `ADAUSD` is not in `EQUITY_SYMBOLS`/`ETF_SYMBOLS`/… |
| **result** | **`return "equity"`** |

Every crypto pair in `BASE-USD` form with no category field therefore landed on the equity
fallback. That is exactly the observed set: `ADA-USD, AVAX-USD, BTC-USD, DOGE-USD, DOT-USD,
ETH-USD, LINK-USD, SOL-USD, XRP-USD` — 209 rows on 2026-11-19, carrying a mechanical
`+3.00 / -2.00` payoff from one batch resolve at `15:33:26Z`.

`BTC-USD` is the clearest proof: an instrument that can never be an equity ticker was being
counted in the EQUITY book, whose per-class costs, win thresholds and audit3 verdicts then all
measured a crypto grid as if it were stock selection.

### Fix

A new rule, checked on the **raw** symbol (before the separator is stripped) and placed
**before** the category field, following the precedent already set by incident #48:

```python
_PAIR_USD_RE = re.compile(r"^([A-Z0-9]+)[-/]USD$")

_pair = _PAIR_USD_RE.match(str(pick.get("symbol") or "").upper().strip())
if _pair and _pair.group(1) not in FOREX_CODES:
    return "crypto"
```

Justification, decision by decision:

- **Raw symbol, not `sym_core`.** The separator is the only thing that distinguishes an
  explicit pair (`BTC-USD`) from an unqualified ticker (`ADAUSD`); normalising first is what
  caused the bug.
- **Beat the category field.** Upstream labels are known to be corrupt (incident #48:
  `SHIBUSDT` tagged COMMODITY, `BTCUSDT` tagged forex). A separator plus a USD quote cannot
  be an equity ticker, so the symbol wins. This matches `outcome_resolver._is_non_crypto`,
  which already prioritises suffixes over labels.
- **Exclude `FOREX_CODES` bases.** `EUR-USD` and `GBP-USD` must stay FOREX, and they do.
- **`-`/`/` only, not `USD` bare.** `ADAUSD` (no separator) is untouched, so the existing
  fallback path and every test that depends on it are unchanged.
- **Applied to both entry points** (`normalize_asset_class` and `asset_class_from_symbol`)
  so the two helpers cannot disagree.

### Verification

`tests/test_asset_class_usd_pair.py` — 15 tests, including all nine observed symbols, corrupted
labels (`equity`, `bond`, `stocks`, `forex`) losing to the pair, fiat bases staying FOREX,
`=X`/`=F` still winning, and `ZZZZ` still falling back to equity. Combined with the existing
suites: **170 passed, 4 skipped** (the skips need `dashboard_data.json`, absent locally).

### Not done: the historical rows

The fix stops new mislabels. The existing rows are still in `at_pick_outcomes`. Repairing them
is a production write and needs approval; the statement is:

```sql
-- REVIEW BEFORE RUNNING: 209 rows on 2026-11-19 alone
UPDATE at_pick_outcomes
   SET asset_class = 'CRYPTO'
 WHERE asset_class = 'equity'
   AND (symbol LIKE '%-USD' OR symbol LIKE '%/USD')
   AND symbol NOT REGEXP '^(EUR|GBP|JPY|AUD|CAD|CHF|NZD)[-/]USD$';
```

---

## 2. Pick-id join key — and a correction

I earlier reported "85 collisions after stripping the `v1::` namespace". **That figure was my
measurement error, not a data defect.** I stripped with `split("::")[-1]`, which also destroys
`writer::symbol::timestamp` ids like
`pt_funding_rate_carry::BARDUSDT::2026-03-05T13:30:16` — the tail alone is not unique by design.

Measured properly, the stored ids are already unique: **8,613 rows → 8,613 distinct raw ids,
zero duplicates.**

The real problem is only that the two systems spell the *same* id differently, so a naive join
silently matches nothing (0 of 230 MeanReversionBB rows joined):

| side | id |
|---|---|
| `at_pick_outcomes.pick_id` | `v1::signal_validation::sig_20260220_084510_AVAX-USD` |
| canonical row `.id` | `sig_20260220_084510_AVAX-USD` |

### Fix

`alpha_engine/symbol_identity.pick_id_join_key()` strips **only** a leading
`v<n>::<writer>::` prefix:

```python
_VERSION_WRITER_RE = re.compile(r"^v\d+::[^:]+::(.+)$")
```

`canonical_row()` now emits a `join_key` field alongside the untouched `id`, so the canonical
sidecar is directly joinable to `at_pick_outcomes.pick_id`. The field is additive; every
existing consumer reads named fields and is unaffected.

### Verification

- `tests/test_pick_id_join_key.py` — 9 tests: DB/canonical forms collapse to one key, legit
  namespaced ids preserved, distinct trades never collapse, `None`/blank handled, idempotent,
  nested `v2::` preserved, and `canonical_row` exposes the key.
- On the live canonical view: **8,613 rows → 8,613 keys, 0 collisions**, with all 30
  `v1::`-prefixed rows normalised.
- Combined run with the resolved-closed-view and asset-class suites: **48 passed**.

---

## 3. Still blocked

`findtorontoevents.ca` and `mysql.50webs.com` are not resolving from this box (and the same
failure killed `audit3-ledger` run `44575645118` at its first step), so:

- the deployed-ledger confirmation of `selection_alpha.available == true` is pending;
- the count of historically mislabelled rows beyond today's 209 cannot be queried right now.

Neither is caused by these changes; both are re-runnable the moment DNS returns.

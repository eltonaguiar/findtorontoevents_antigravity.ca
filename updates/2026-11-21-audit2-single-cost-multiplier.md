# audit2: one cost multiplier, slippage read from the ledger

**Date:** 2026-11-21
**Files:** `audit_dashboard/audit2.js`, `audit_dashboard/audit2.html`
**Status:** fixed and verified in-page; not yet deployed

## What was broken

The same page asserted two different cost rules, and quoted slippage figures that
were typed in rather than derived:

| where | claim |
|---|---|
| `audit2.js` → Verdicts column | `stress_2x_ok`, i.e. **2×** class slippage |
| `audit2.html` → caption under that table | "**2×** cost OK = … at twice the class slippage" |
| `audit2.html` → Trial budget | "average net PnL must be at least **3×** the measured slippage. ETF slippage measured **≈234%** of per-trade PnL (monthly cadence only); CRYPTO **≈37%**" |

Two multipliers on one surface means a reader cannot tell which gate the column
above is actually testing, and the two hardcoded percentages have no link to the
ledger — they would keep rendering after any class cost moved.

## Why 2× is the single multiplier

The ledger carries the stress only as `net_ci_pct_2x` / `stress_2x_ok` at cell and
class level. There is no 3× field, so 2× is the only multiple this surface can
show without inventing a second calculation in the browser.

The **3× rule is real but different**: `tools/per_class_cost_gate.py`
(`REQUIRED_COST_MULTIPLE = 3.0`) gates *emission*. It is untouched by this change
and still live — audit2 simply no longer claims it, because audit2's column
measures the ledger's 2× CI stress, not the emission gate.

## What changed

**`audit2.js`**
- New single constant:
  ```js
  var COST_STRESS_MULTIPLE = 2;   // must match net_ci_pct_2x / stress_2x_ok
  ```
  Referenced 3× — column header, caption, cost note. No other literal multiplier
  remains on the surface.
- New `renderCost(d)` reads `conventions.cost_basis.class_cost_pct` (falling back
  to `conventions.slippage_pct_by_class`), prints each class in **bp**, names the
  source (`payload.slippage_validation`) and the per-strategy coverage
  (73 strategies, min n=30), and states the gate at `COST_STRESS_MULTIPLE ×`.
- If a payload declares no cost basis, it says so. It does **not** fall back to a
  baked-in percentage.

**`audit2.html`**
- `<th id="costColHead">`, `<div id="costCaption">`, `<div id="costNote">` — the
  three places that stated cost are now placeholders filled from the payload.
- Deleted the "3× … ≈234% … ≈37%" sentence and the static "2× cost OK = …"
  caption.

## Verification

- `node --check audit_dashboard/audit2.js` → clean.
- **Functional render against the real `audit3_ledger.json`** (jsdom-free DOM
  stub, the page's own `renderLedger` executed):
  - header → `2× cost OK`
  - note → "Cost gate on this page: the net-expectancy CI must still exclude zero
    at **2×** the per-class round-trip cost… MEME 30.00 bp · PENNY_STOCK 30.00 bp ·
    COMMODITY 15.00 bp · FUTURES 10.00 bp · CRYPTO 9.96 bp · … · FOREX 2.00 bp",
    source `payload.slippage_validation`, "73 strategies, min n=30".
  - `renderCost({})` → "Cost basis is not declared in this payload, so no slippage
    figure is shown rather than a hardcoded one."
- `grep` for `3×` / `234%` / `≈37%` / "twice the class slippage" across both files
  → none.
- `pytest tests/test_audit2_page_deploy.py tests/test_build_audit2_pods.py
  tests/test_audit2_forward_clock.py` → **10 passed**.

## Limitations

- The multiplier is a JS constant, not a payload field. The ledger only encodes the
  stress in field *names* (`net_ci_pct_2x`), so if a different stress is ever
  computed, this constant must move with it. `renderCost` degrades honestly if the
  cost basis is missing, but it cannot detect a renamed stress field.
- The two per-class percentages (ETF 234%, CRYPTO 37%) are **gone, not recomputed**:
  they described cost as a share of per-trade PnL, which is a different statistic
  from round-trip cost in bp. Reinstating them properly needs that ratio in the
  ledger.
- `tests/test_audit2_forward_summary.py` fails to collect in this worktree
  (`ImportError: cannot import name 'merge_gate'` from
  `tools/audit2_forward_summary.py`). Pre-existing and unrelated — that module and
  test reference neither `audit2.html` nor `audit2.js`.
- Not deployed: live `/audit2` keeps the old text until the next deploy of
  `audit2.html` + `audit2.js`.

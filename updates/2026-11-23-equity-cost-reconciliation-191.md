# 2026-11-23 — Equity round-trip cost reconciled on the same 191 names

## What was broken

Two equity round-trip costs were being argued about as if they were rival measurements of one quantity:

- **12.0749 bp** — the median 1-minute bar range over **13** mega caps/ETFs, which is a rigorous **upper
  bound** on the quoted spread, quoted as "measured cost";
- **1–5 bp** — Corwin-Schultz on **191** S&P names plus the SEC fee, with an optional 4.0 bp slippage
  term, i.e. a point estimate plus an assumption.

Different estimator **and** different universe. Neither side was wrong; the comparison was.

## What changed

- **`tools/equity_cost_reconcile_191.py`** (new) — recomputes all three estimators on the **same 191
  names** from the **same cached 1-minute bars** (`data/cache/hml_daily/*_1m.json`, 191/191 measured, no
  network), excluding names whose median range is tick-truncation. Also records that only AAPL and AMZN
  of the original 13 have cached bars, so the 13-name figure is honestly marked
  `INSUFFICIENT_CACHE_ONLY_2_OF_13` rather than "reproduced".
- **`reports/equity_cost_reconcile_191_2026-11-23.json`** + **`reports/equity_cost_reconciliation_191_2026-11-23.md`**.

## What was measured

| estimator (same 191 names) | n usable | median RT bp |
|---|---|---|
| Corwin-Schultz | 65 / 191 | **0.7696** |
| Roll | 190 / 191 | **3.8064** |
| 1-min bar range (upper bound) | 190 / 191 | **7.1744** |

- 21.6% of the 191 names have a bound under 5 bp; 86.3% under 12.0749 bp; 98.5% have CS under 5 bp.
- **Cost of record: 4.01 bp RT** (Roll + 0.206 bp SEC fee, n=191), bracket **0.98 … 7.38 bp**, 2×-cost
  gate at **8.02 bp**.
- The old 4.98 bp figure is **not verdict-grade**: 0.7696 is measured, 0.206 is statutory, and 4.0 is an
  unsourced slippage assumption. Landing near the Roll estimate is a coincidence, not corroboration.

## Verification

- `python3 tools/equity_cost_reconcile_191.py` → exit 0, 191/191 measured, artifact written.
- `py_compile` clean on the tool.
- No verdict moves: H-201 still passes cost and fails multiplicity at every figure in the bracket; the
  other classes are bounded by something other than equity cost. **0 of 10 investable, unchanged.**

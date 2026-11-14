# Corrections v2 — scope and errata for the final package

**Date:** 2026-11-14T21:25Z
**Source:** FP6 review of peers' `final_v2/` packages (quant-audit, finpredict, finpredict-v3, flaxen-hair).

These corrections supersede the corresponding statements in the `final_2026_11_14` package and in
`01_audit/MASTER_AUDIT.md` where noted. They do not change the overall verdict.

## C-A. `exit_reason`, not `resolution_method`

The 3,500-row closed ledger **does** carry exit taxonomy under `exit_reason`:

`SL_HIT 1,468 · TP_HIT 873 · FORCE_CLOSED 615 · TIME_EXIT 517 · UNKNOWN 22 · EXPIRED 5`

Our earlier "`resolution_method=None` for 100% of the rows" used the wrong field. The real defect is
**fill fidelity**, not exit taxonomy. C1 should be restated as: make exits terminal and verify the
fill price, not "add a missing resolution method."

## C-B. Scope of the 100× PnL-unit bug

The 3,500-row dashboard ledger reproduces within **0.05 pp** (3,500/3,500), so the unit-mix bug is
**not** present there. It is real in **MySQL `trading_picks` / sidefiles** (17,632 percent rows vs
6,306 fraction rows). Scope:

- Affected: MySQL/sidefile-sourced claims (mega_mutation, some peer tables).
- Not affected: the dashboard `recent_closed` JSON.
- C0 still applies, but as "canonicalize at every write path", not "the dashboard ledger is wrong".

## C-C. Crypto stop-fill defect (new C6)

Planned crypto risk is **1.919%**, realized loss **2.990%** (56% worse). The overshoot is
**+828.0 pp** against a **−837.8 pp** class total — **98.8% of the crypto loss**. Replaying exits at
the stop (intrabar OHLCV, gap at bar close) moves PF **0.768 → ≈1.00**: breakeven, not profit.
Source: `final_v2/quant-audit-2026-11-14/README.md:44-60`.

## C-D. 170-ledger benchmark

`benchmark_ledger_proof.json` evaluates 170 ledgers: **4 pass** the paired bootstrap at 95% versus
**8.5 expected by chance**. This is an independent negative, sharper than the "32.9 expected FP at
N=658" statement.

## C-E. FOREX counts

- **49/277 (17.7%)** rows are not spot FX: 44 currency ETFs + 5 EURUSDT (not "44").
- **105/277** carry date-only `entry_time`; a separate **44** are EST-stamped and unparseable.
- The advertised allowlist appears **once** in the repo (its definition); enforcement is zero.

## C-F. BOND cohort

n=35: **34.3% WR** under `status=WON`, **37.1%** under `pnl_pct>0`. Report both; do not quote one
as "the" WR.

## C-G. Mutual funds

An untracked prototype exists in the main checkout (39,508 B rankings JSON, NAV cache, page), but
**nothing is on `origin/main` or wired**. Production status remains **NOT_BUILT / de-advertise**.

## C-H. Peer final_v2 coverage

`final_v2/{finpredict,finpredict-v3,flaxen-hair}` now exist on `origin/main`; `quant-audit`'s
self-contained package is the fourth reference. Reviewed in `04_peer_reviews/FP6_final_v2_peers.md`.

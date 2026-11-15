# FIX-006 — QA Market Validation is correctly failing (do NOT suppress)

**File:** `.github/workflows/qa-market-validation.yml` + `tools/qa_ledger.py`
**Severity:** P1 (data-quality, not CI-config)
**Status:** Documented — intentional NOT suppressed

## What the failure is
`QA Market Validation` fails every hour with `##[error]Process completed with exit code 1`. Run log (43684390241) summary:

```
QA ledger: 4390 picks, 882 flags (191 critical)
  BOND      n=1324 unpriced=0  zero=0 blank_tp/sl=0   mismatch=0
  COMMODITY n=4    unpriced=4  zero=0 blank_tp/sl=0   mismatch=0
  EQUITY    n=772  unpriced=71 zero=0 blank_tp/sl=691 mismatch=0
  ETF       n=1736 unpriced=7  zero=0 blank_tp/sl=0   mismatch=0
  FOREX     n=554  unpriced=11 zero=0 blank_tp/sl=0   mismatch=98
```

Critical flags (exit code 1) = UNPRICED (93) + MISMATCH (98 FOREX) = **191**.

The `fetch_quote(XXX): ALL 7 sources failed` lines are noise from the equity failover module trying every provider; they do **not** themselves create flags. The critical failures are:
1. **93 picks with blank `current_price`/`pnl_pct`** — a producer/data-pipeline bug (source JSON missing fields).
2. **98 FOREX MISMATCH** — published PnL disagrees with the independent forex feed beyond tolerance.

## Why this should NOT be "fixed" in CI
Suppressing the gate (e.g. `continue-on-error`, or downgrading UNPRICED/MISMATCH to warnings) would let **unvalidated PnL reach the dashboard**, which is exactly what this gate exists to prevent. Per `active_strategy_benchmark_requirement`, clean data is mandatory.

## What needs to happen instead (owner actions)
1. Fix the producer emitting picks with blank `current_price`/`pnl_pct` (the 93 UNPRICED rows — concentrated in EQUITY 71 + ETF 7 + FOREX 11 + COMMODITY 4).
2. Investigate the 98 FOREX MISMATCH rows: likely a provider-timezone or quote-source mismatch between the publisher and `forex_price_failover`. Reconcile the source of truth.
3. (Optional) Provision the quote-chain API keys (FINNHUB/TIINGO/TWELVE_DATA/ALPHA_VANTAGE/FMP) so equity cross-checks can run; Stooq is blocked from GHA IPs and yfinance is flaky.

## Verdict
The job is **correctly red**. Do not merge a change that makes it pass without fixing (1) and (2).
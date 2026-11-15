
## Post-fix dispatch result (proof the QA fix works)

Dispatched `QA Market Validation` on the fix branch (`gh workflow run
qa-market-validation.yml --ref wired-in/buffy-gh-actions-fix-2026-11-15`),
run **43690513115**:

- The step log confirms the keys reached the process — `ALPHA_VANTAGE_API_KEY: ***`,
  `FMP_API_KEY: ***`, and `TIINGO_API_KEY:` / `TWELVE_DATA_API_KEY:` empty, matching
  the secret audit above.
- Result changed from *infrastructure failure* to *real validation*: **185 picks,
  `unpriced=0` in all six classes** (BOND 54, COMMODITY 3, EQUITY 31, ETF 74,
  FOREX 23, plus crypto). Before the fix, every equity ticker logged
  `ALL 7 sources failed`.
- It still exits 1 — correctly — on 5 flags / **4 critical**:
  `FOREX mismatch=3`, `COMMODITY mismatch=1`, `EQUITY blank_tp/sl=1`.

That is the gate working as designed. It does **not** indicate the CI fix failed.

### Honest note on naming those picks

An offline replay (`python3 tools/qa_ledger.py`) to enumerate the flagged symbols
**cannot complete locally**: it performs up to `_MAX_EXT_CHECKS=250` live
cross-checks, each with a 5s-per-adapter chain, and `timeout 180` killed it
(`exit 124`, zero output). An earlier attempt silently parsed the *pre-existing*
`audit_dashboard/data/qa_market_validation.json` (generated 02:03:59, **4390**
picks, 500 flags) and printed flags from that older payload — which is a
different generation than the CI run's 185 picks. Those symbols
(`AUDJY=X` repeated with a constant 0.63pp diff, plus BLANK_TP_SL on
GOOGL/TTWO/PLTR/MU/NFLX) are therefore **reported from the 02:03 report, not from
run 43690513115**, and must not be attributed to the current payload.

If those older flags are representative, the FOREX pattern matters: the *same*
0.63pp gap on every AUDJPY=X row with different published values is the signature
of a **time-lag** between the published PnL snapshot and the live external quote,
not of corrupt PnL. With `TOL_PP["FOREX"]=0.5`, a 0.63pp intraday move trips the
gate on its own. That is a gate-calibration question (tolerance vs. payload
refresh cadence), and it is **NOT MEASURED** for the current payload.

## Unrelated blocker found while triaging

`branch-large-file-dup-guard` fails on the fix PR (#786) and was **cancelled** on
the earlier #785 run — its config has `concurrency: group: branch-large-file-dup-guard,
cancel-in-progress: true`, and it triggers on every non-main branch push, so
concurrent branches cancel each other's checks. A cancelled blob guard means that
check is not a valid signal on either PR. Not fixed here (out of scope: it is a
repo-bloat guard, not a data-pipeline job).

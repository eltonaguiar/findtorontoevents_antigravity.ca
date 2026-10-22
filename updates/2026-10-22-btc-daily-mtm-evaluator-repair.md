# Repair the evaluator that regenerated misleading Bitcoin risk results

Goal #1. This patch targets OpenCode's existing `oc-winning-candidate` branch,
not main. It is a reviewed research-code correction, not a trading deployment.

## What was broken

The [published-strategy evaluator](../tools/crypto_published_strategies.py)
calculated maximum drawdown from completed-trade endpoints. It therefore
reported 12.45% despite approximately 80% daily account losses during open
positions. The page had already received a manual FAIL correction, but rerunning
the evaluator still reproduced the bad risk statistics.

The script also filled a signal at its own final closing price while calling
that next-day execution. Random-entry MC actually sampled slices of the
strategy's own trade returns; DSR used an ad hoc formula; concentration was
hard-coded to pass a 100%-BTC universe. Bootstrap PF substituted 10 for undefined
no-loss samples and did not supply the stated day-cluster confidence proof.
NumPy Boolean values became the strings `"True"`/`"False"` in JSON.

## What changed

- Every entry and signal exit now executes at the **next daily close**.
  This is not next-open execution, and the output names the convention.
  The final observation liquidates an existing position for measurement;
  it cannot create a zero-duration new trade.
- Daily marked-to-market equity accounts for open holdings, idle cash,
  one fully funded spot position, no leverage, zero cash yield, and 0.1% fees
  per entry/exit. Net trade PF uses the same multiplicative fees.
- Missing dates, nonpositive/nonfinite prices, inconsistent fills, out-of-order
  trades and overlapping capital raise explicit errors. No forward-fill or
  silent zero-PnL substitute is used.
- Missing daily prices make drawdown unverified, not a completed-trade estimate.
- Invalid MC, DSR and confidence implementations were removed rather than
  replaced with a hurried statistical approximation. Their values are null,
  reasons explicit, and they cannot pass. The 100% BTC concentration fails.
  The descriptive first/second-half comparison is explicitly retrospective,
  not independent out-of-sample evidence.
- Undefined PF stays null, JSON is strict with native Boolean values, and WR
  stays hidden below 20 trades.
- Existing CLI calls remain valid. New `--input`, `--output` and `--trials`
  switches allow reproducible scratch runs without rewriting live assets.
  The existing main caller passes its full daily price path to every gate.
- The [owned page](../audit_dashboard/opencode_paper_trading.html) BTC block
  consumes the [rebuilt results](../audit_dashboard/data/published_strategy_gates.json).
  Old-curve, malformed or unavailable evidence shows "verdicts unavailable";
  there is no static fallback performance table.

This does not migrate or validate the page's unrelated legacy strategy claims.
It does not wire a new strategy into production, issue an order, change a
blocklist, authorize a kill or alter the separate prospective paper monitor.

## Measured real-data output

Input: 4,418 daily BTC prices, 2014-09-17 through 2026-10-21.
SHA256:
`4d189a2071b8a6f7abef8b1033464faeecbfeec367c10c266ec53cf75d2f8b5c`.
The same file and source revision produce byte-identical result JSON.

| Existing hypothesis | Trades | CAGR after fees | Daily MTM MDD | Verdict |
|---|---:|---:|---:|---|
| BTC 200-day SMA | 38 | 60.82% | 64.33% | FAIL |
| BTC 300-day SMA | 37 | 57.48% | 71.83% | FAIL |
| BTC 12-month absolute momentum | 13 | 53.35% | 81.74% | FAIL |
| BTC 50/200 golden cross | 11 | 51.13% | 66.22% | FAIL |
| BTC RSI<30, 200d filter, 30-day time stop | 30 | -0.07% | 69.31% | FAIL |
| BTC 12m+6m momentum | 26 | 43.88% | 73.18% | FAIL |

These are historical baseline descriptions, not a selected winner or proof of
benchmark-adjusted alpha. The unchanged input has no real order/fill witnesses.
The daily curve is for this explicit single-position research model, not a
claim that an actual funded account earned these returns.

## Verification

The first twelve regression cases were run against the original evaluator:
**12 failed**. The new page contract was also observed failing before wiring.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_crypto_published_mtm.py -q -p no:cacheprovider
python3 tools/crypto_published_strategies.py --output audit_dashboard/data/published_strategy_gates.json --trials /path/to/session/btc-repaired-trials.csv
node tests/crypto_published_mtm_browser.cjs
git diff --check
```

- **14 Python tests passed**, including an 80% fall inside a winning trade,
  costs/idle cash, missing-path errors, overlap rejection, causal execution,
  unknown statistical proof, strict JSON and repeated real-data CLI output.
- **Desktop 1440px and mobile 390px browser checks passed** using the actual
  rebuilt results, including expandable ELI5, hidden n<20 WR and fail-closed
  behavior for old curves, string-valued metrics and HTTP errors.
- Independent read-only code review quoted the original faulty lines and found
  no high-confidence regressions. All six output records matched recalculation.
- Full repository suite not run; the prior broad CI pandas `freq="ME"`
  compatibility failure is outside this patch. No dependency versions changed.
- No FTP deployment or dashboard generator was run. Only the research result
  file was regenerated by its existing evaluator. No main checkout/stash touched.

## Next action for the peer owner

Review this correction on `oc-winning-candidate`; rerun it before publishing
performance. Keep MC/DSR/CI unverified until their separately tested adapters
exist. A page-only disclaimer must not substitute for repairing its producer.

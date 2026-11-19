# E14 — exit A/B (paper): the plain time exit is worse, and that is the finding

**Date:** 2026-11-19
**Added:** `tools/exit_ab_paper.py`, `tests/test_exit_ab_paper.py` (9 tests)
**Evidence:** `reports/exit_ab_paper_2026-11-19.json` (2,475 picks)

## What was broken

The audit could say a cell loses money, but not *why*. The suspected cause was exit
geometry: a TP that fires early caps winners, an SL on noise converts a drawdown into a
real loss. The slice scan hinted at it — CRYPTO LONG picks whose exit reason is `TP_HIT`
still gave up **−2.590%/pick** versus simply holding the same symbol, and equity `SL_HIT`
gave up −2.150%. That is a conditional statistic though: it describes picks *after* the
TP fired, so it cannot answer "should we replace the exit rule for everyone?"

## What I added

A paired counterfactual on the same signals: same entry fill, same direction, only the
exit changes. For each closed pick, a fixed-horizon time exit (no TP, no SL) is priced at
the last bar **at or before** the horizon, so no future information leaks into the fill.
The counterfactual pays a 0.10% round-trip cost; the actual leg already has its cost in
the recorded pnl, so it is not charged twice. Rows with no entry bar, no bar at the
horizon, or a degenerate same-second hold are reported in `skipped{}`, never dropped
silently.

## What it measured

Mean paired delta = time exit − actual exit (positive means the time exit was better):

| horizon | n | delta/pick | 95% CI | time exit | actual |
|---|---|---|---|---|---|
| 1 day | 2,463 | **−0.460%** | [−0.729, −0.191] | −0.098% | +0.362% |
| 3 days | 2,463 | **−0.291%** | [−0.645, +0.064] | +0.071% | +0.362% |
| 7 days | 2,463 | **−0.485%** | [−0.992, +0.022] | −0.123% | +0.362% |

Per class, only one cell clears zero: **ETF at 7 days, +0.460%/pick** (n=261,
CI [+0.154, +0.766]). Equities are decisively worse at every horizon (1d −1.104%,
3d −0.943%). 12 rows were skipped as degenerate zero-second holds.

## Verdict

**The blanket exit redesign is rejected.** Replacing TP/SL with a fixed time exit makes
the book worse at every horizon tested, with a CI that excludes zero at 1 day. The
`TP_HIT` shortfall is real but it is a *conditional* fact — those picks had already
travelled far enough to trigger the TP, so the counterfactual "hold it instead" is only
observable on the subset that survived to be interesting. A rule that also stops applying
the TP to the picks that would have reversed cannot be priced from that subset.

The single surviving candidate — **ETF, 7-day time exit, +0.460%/pick** — must be
pre-registered before it is believed: it is 1 of 9 class×horizon tests, so a Bonferroni
gate (α = 0.05/9 ≈ 0.0056) is required, and its CI's lower bound would not survive it.
It is a candidate to register, not an edge to trade.

## Limits

- No vol-scaled exit was tested: sizing a horizon by pre-entry realised volatility needs
  bars *before* the entry, and the shared loader fetches the symbol's stored series as
  fetched. That remains the open half of E14.
- Horizon pricing uses the last bar at/before the target, so a 7-day horizon on daily
  bars can fill up to one bar early; the direction of that bias is not constant.
- Cost is a flat 0.10% round-trip assumption, not per-class slippage.
- 2,475 rows in, 2,463 had a usable entry bar; the 12 exclusions are all degenerate.
- Paper only: no orders, no ledger verdict, no `money_ready` change.

## Verified

```
python3 -m pytest tests/test_exit_ab_paper.py -q     # 9 passed
python3 tools/exit_ab_paper.py --rows /tmp/rows.jsonl \
  --json-out reports/exit_ab_paper_2026-11-19.json   # rc=0, table above
```

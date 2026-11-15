# Summary — repo mining, class triage, and a pre-registered plan

**Workspace:** `WIRED_IN/2026-11-15_0711_buffy/` · branch `wired-in/buffy-2026-11-15`
**Status:** mining complete · tracker shipped · three plans written · no candidate PROVEN

## What I did, in order

1. Static signature scan over the tree (25,000-file cap, 200 KB/file, `WIRED_IN`/`archive`/
   worktrees excluded) with a 25-pattern library → `harvested_ideas/00_inventory.csv`.
2. Dependency triage from `requirements.txt` / `package.json`.
3. Semantic extraction (function/class names) per flagged file.
4. Failure taxonomy and method catalogue from the inventory, with file citations.
5. Per-class digests (7) from the closed ledger.
6. Prediction tracker from the closed ledger, id-matched back to every closed pick.
7. Three plans written before any code: CRYPTO, EQUITY, BOND.
8. This summary.

## Mining headline numbers

| Metric | Value |
|---|---:|
| files scanned (capped) | 25,000 |
| files flagged with ≥1 technique | **14,830** |
| implemented (`.py`) | 2,561 |
| tested (backtest/result/verdict in path) | 3,101 |
| documented only | 8,355 |
| abandoned (kill/reject/retire/falsify in path) | 813 |

Most-mentioned techniques: REGIME 8,609 · position sizing 6,613 · costs 6,098 · stops 5,395 ·
alt-data 4,336 · significance 3,777 · market data 3,548 · paper trading 2,107 · walk-forward 1,853 ·
DSR 756 · PBO 324 · Reality Check 315 · **backtest framework 51**.

Two ratios carry the whole diagnosis:

- **documented / implemented = 3.3 : 1** — prose outruns code.
- **DSR 756 : framework 51** — the repo measures more rigorously than it executes. There was never
  one engine to hold every pipeline to the same fill and cost assumptions.

## Class verdicts (gross, 3,500 closed picks, payload 2026-10-19)

| Class | n | mean | median | WR | PF | Verdict |
|---|---:|---:|---:|---:|---:|---|
| CRYPTO | 2,070 | +0.54% | −0.88% | 46.1% | 1.31 | PROMISING — fat tail, unbenchmarked |
| EQUITY | 690 | +0.46% | −0.18% | 47.5% | 1.23 | PROMISING — fat tail, unbenchmarked |
| ETF | 503 | +0.08% | −0.68% | 44.3% | 1.07 | REJECT at daily cadence |
| FOREX | 199 | −0.13% | 0.00% | 32.2% | 0.66 | REJECT — stop allocating |
| BOND | 28 | −0.23% | −0.76% | 35.7% | 0.56 | INSTRUMENTED — NOT MEASURED |
| COMMODITY | 9 | +0.03% | 0.00% | 44.4% | 1.03 | INSTRUMENTED — NOT MEASURED |
| FUTURES | 1 | −0.47% | −0.47% | 0.0% | 0.00 | INSTRUMENTED — NOT MEASURED |

**Recommended next work, by expected information per unit of effort:**
1. EQUITY excess vs SPY, clustered on `(entry_day, exit_day)` — the single highest-value missing
   number; 690 rows, existing machinery, no new code.
2. CRYPTO excess vs BTC-USD, majors vs alts — same method, 2,070 rows.
3. BOND fresh start with duration data — the only class where low multiplicity makes a clean test
   possible, but it needs 24 months.

## Tracker

`tracker/predictions_tracker.csv` (3,500 rows) + `tracker/predictions_tracker.html`.
**100% of closed picks match by pick id**; active picks are intentionally absent (closed-only
ledger). Hit 1,584 / miss 1,862 / flat 54 → 45.3% hit rate, consistent with the class table.

**Governance gap found:** `expected_return` and `regime` are absent from the payload for **all
3,500 rows**. A prediction tracker without a predicted return cannot measure calibration, and a
regime column that does not exist cannot support the regime split the proof standard requires.
Both are recorded as `NOT MEASURED` rather than filled. Fix at the emitter, not in the tracker.

## What is explicitly not measured

- Benchmark-adjusted class performance (gross only; join exists, not run per class).
- 1,084 of 3,500 rows (31%) — same-day windows cannot be benchmarked from daily closes.
- PBO and White's Reality Check on the current cohort — code lives only in
  `.claude/worktrees/cluster-a-fix-2026-06-21/tools/`, so any number from it is not reproducible.
- Any forward result: the ledger is empty by design (registered 2026-11-15, no pick closed since;
  `rs-breakout-scout` 0/152 windows).

## Reproduction

```bash
python3 WIRED_IN/2026-11-15_0711_buffy/experiments/repo_mine.py WIRED_IN/2026-11-15_0711_buffy
python3 WIRED_IN/2026-11-15_0711_buffy/experiments/build_tracker.py WIRED_IN/2026-11-15_0711_buffy
python3 tools/forward_tracker.py selftest          # 21/21
python3 -m pytest tests/test_forward_tracker_of_edges.py -q   # 19 passed
```

## Blockers and caveats

- The scan is capped at 25,000 files / 200 KB per file; counts are lower bounds, and 3,724 flagged
  files have no inferable asset class.
- `git` worked throughout; nothing was left uncommitted.
- Repeated silent working-tree reverts occurred during this session (`template.html`,
  `index.html`, `tools/forward_tracker.py`). All work was rebuilt from committed blobs before
  being relied on; the branch content is authoritative, not the local checkout.

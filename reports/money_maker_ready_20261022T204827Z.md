# Money-Maker-Ready Audit — 2026-10-22

Scope: the user's profitability concern and copy-trader signal lifecycle.
This is an engineering repair and evidence audit, not a claim that changing
code creates an investable edge.

## 0. Freshness preflight

Live `audit/data/money_ready_verdict.json` was generated at
2026-10-22T19:12:30.563334+00:00; fetched around 20:49 UTC, within the two-hour
freshness requirement. The symbol sidecar was generated at 20:34:45 UTC.
Local copy-trader snapshots were older than the remote branch, so current
remote artifacts and actual workflow logs were used to confirm the defect.

## 1. Per-class baseline (verdict-grade)

Source: live `money_ready_verdict.json::classes.<CLASS>.intrabar_truth`.
Timeframe for every row: cumulative intrabar cohort through the snapshot above;
the verdict does not supply exact cohort start/end dates.

| Asset class | n | WR % | PF | Verdict |
|---|---:|---:|---:|---|
| CRYPTO | 3563 | 35.64 | 0.8914 | NOT_READY |
| FOREX | 568 | 31.69 | 0.6465 | NOT_READY |
| EQUITY | 233 | 56.65 | 0.8642 | NOT_READY |
| COMMODITY | 229 | 40.17 | 1.0256 | WATCH |
| FUTURES | 48 | 41.67 | 1.061 | INSUFFICIENT_DATA |
| ETF | 30 | 0 | 0 | INSUFFICIENT_DATA |
| BOND | 21 | 9.52 | 0.5281 | INSUFFICIENT_DATA |

MEME and PENNY_STOCK have no intrabar-truth object in this verdict; neither is
money-ready. The snapshot's `summary.money_ready` is empty. Commodity PF slightly
above one is not evidence of consistent or Tier-2 profitability. Equity's
above-50% WR with PF below one illustrates why win rate is insufficient.

## 2. Walk-forward verification (per class, OOS)

No new walk-forward qualification is asserted. The queried symbol sidecar
contains n/WR/PF but not monthly slices, costs, drawdown, independent provenance,
or a held-out selection protocol. It cannot establish consistent profitability.
Existing promotion requirements remain unchanged.

## 3. Cumulative-since-inception system winners (Tier-2-MDD-verified)

No new Tier-2-MDD-verified system is established by this investigation.
Historical trader account statistics are not the performance of entries our
system could actually copy, and clone aliases are not independent traders.

## 4. System draggers (negative PnL contribution)

The concrete failure is signal lifecycle, not a new system-wide blacklist:

1. `generate_dashboard_data.py` loads closed-trade files into `all_picks` for
   historical reporting, then used that same pool to emit clone/highscore picks
   hardcoded as `OPEN`.
2. It merges `clone_picks.json` into the scanner's active file without checking
   age or lifecycle, defeating a scanner result with zero eligible picks.
3. Consensus counts included historical/closed rows.
4. TP/SL-breached picks could be emitted as OPEN, and variation positions missing
   `opened_at` were assigned the current timestamp.

Current remote evidence: 16 highscore rows, 100 clone-active rows, and 50 clone
input rows; **zero** pass the repaired active lifecycle predicate at observation
time. These are artifact counts, not independent trades or performance samples.
Their earliest timestamps are March 19, 2026.

Workflow run **39844111014**, created 2026-10-22T19:53:59Z, concluded success even
though the scanner printed `Total picks: 0`, followed by `50 clone picks merged`,
`16 high-score picks`, and `100 clone picks`. This directly reproduces the
resurrection mechanism. The same run logs MySQL error 1045 for optional writes;
that operational credential issue is recorded, not silently claimed repaired.

## 5. Backtest-overfit detector flags

No thresholds were tuned to historical PnL and no backtest was run. No source,
symbol, direction, or asset-class blacklist was broadened. The repair only
prevents ineligible historical rows from being republished as current picks.

## 6. Drift state

No new drift state or sizing permission was inferred. A live-entry strategy must
still pass the existing drift, sample, concentration, and walk-forward gates.
Green CI is not evidence that signal ingestion or profit generation succeeded.

## 7. UI/Filter audit

The relevant surface is the source contract consumed by
`audit_trail/dashboard_generator.py`: copy_trader_intel, highscore, clones,
variations, and consensus all supply files to the main audit dashboard.
An output named `*_active_picks.json` containing closed or months-old picks is a
verified contract defect even when a later gate happens to reject those rows.
No dashboard HTML, displayed historical result, or live outcome was rewritten.
Other UI filters were not comprehensively audited in this scoped repair.

## 8. External data integrations to consider for more edge

Before adding another scraper, require timestamped observed positions, an
executable observed entry, and subsequent fills/exits attributable to that
entry. For noncrypto, investigate managed-futures and ETF allocation references
as external benchmarks, not copied claims of guaranteed alpha. Additional
leaderboard scraping without entry/exit provenance cannot solve this failure.

## 9. Top statistical edges per asset class

Live `intrabar_sym_dir_fwd.json::by_key` has 1,568 symbol/direction/strategy keys.
Two rows satisfy the exploratory n>=100 / PF>=1.5 / WR>=50 screen:

| Candidate | Class | n | WR % | PF | Timeframe / qualification |
|---|---|---:|---:|---:|---|
| AAPL LONG, all strategies | EQUITY | 121 | 90.9 | 13.32 | sidecar cohort through 20:34:45 UTC; exact dates unspecified, unverified |
| AAPL LONG, vt_equity_two_day_rsi_reversal | EQUITY | 113 | 94.7 | 49.3 | same sidecar, overlapping subset, unverified |

These are **not two independent edges**. The unusually high values require a
provenance and leakage investigation, monthly net returns, independent n,
entry timing, drawdown and held-out validation. Do not promote them from this
table or reinterpret them as a class-wide improvement.

There are 25 copy/clone symbol-strategy rows in that sidecar; the largest has
only four outcomes. Example: (CRYPTO | n=4 | sidecar cohort through snapshot,
exact dates unspecified), BTCUSDT LONG clone_hl_copy_PensionFund_24M:
WR 25%, PF 1.167. This is not enough evidence to claim a consistent profitable
copy strategy. No symbol was promoted by this repair.

## 10. Best-Possible-Action ranked recommendations

| Priority | Action | Expected effect | Boundary |
|---|---|---|---|
| P0 | Enforce active lifecycle before publishing copies/clones/highscore/variations and before counting consensus | Prevent historical resurrection and fake freshness | Implemented with regression tests |
| P0 | Fail the workflow if lifecycle tests or dashboard source generation fail | Prevent an apparently successful refresh from hiding generator errors | Implemented in workflow |
| P1 | Diagnose optional DB error 1045 with canonical CI credentials | Restore optional write observability | Not fixed by this patch; no production DB mutation |
| P1 | Investigate AAPL sidecar provenance and monthly consistency | Determine whether an apparent lead survives verification | No promotion or sizing |
| P1 | Track new copy entries with actual observation price and independent trader identity | Make forward evidence interpretable | Existing gates retained; do not replay stale positions |
| P2 | Paper-evaluate external reference sleeves against net benchmarks | Search for an actual edge rather than relabel past data | Requires prospective evidence, not a promised return |

No numerical profit lift is forecast. Filtering bad inputs can reduce output to
zero; that is preferable to manufacturing active signals or relaxing gates.

## 11. Verifiable claims log

- `python3 -m pytest tests/test_copytrader_active_lifecycle.py -q --tb=short`:
  before fix, 9 failed / 1 passed; after repair and expanded coverage, 46 passed.
- `python3 -m py_compile copy_trader_intel/generate_dashboard_data.py`: passed.
- `git diff --check -- copy_trader_intel/generate_dashboard_data.py tests/test_copytrader_active_lifecycle.py`: passed.
- `gh run view 39844111014 --log`: source for same-run zero eligible scanner
  output followed by regenerated historical copies.
- `gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/contents/copy_trader_intel/data/clone_active_picks.json -H 'Accept: application/vnd.github.raw+json'`:
  current remote active artifact; tested without writing it into the repository.
- Baseline remote main at investigation: `b5e46d0dfce4853ead16d7277a69651a1ebb0551`.
- Tests execute only the copy-trader generator against isolated temporary
  fixture directories with mocked prices. The audit HTML generator, production
  scanners, smart-picks engine, and live DB mutation tools were not executed.
- Independent noncrypto recovery review and quoted pre-change source:
  [FOREX/EQUITY deep dive](deep_dive_noncrypto_2026-10-22.md).

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*

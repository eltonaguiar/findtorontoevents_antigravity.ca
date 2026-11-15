# 2026-11-15 — `rescore` command, OF edge-case tests, and a silent-revert restore

## 1. The problem

`sync` attaches the benchmark leg only to picks it is admitting at that moment. When
`audit_dashboard/data/benchmark_prices.json` is refreshed afterwards, previously admitted rows
keep the closes that existed when they were written. Consequences:

- the first pick a strategy logs can carry a permanently stale `excess_pp`;
- a row admitted before the benchmark file existed keeps `bench_note: outside_series` forever;
- `_endpoint()` then sees incomplete coverage and falls back to `net_return_pp` — the
  registered endpoint quietly stops being the tested one.

Because the ledger is currently empty nothing was visibly broken. This fixes the mechanism
before it can produce a wrong verdict.

## 2. What changed — `tools/forward_tracker.py`

New subcommand:

```
python3 tools/forward_tracker.py rescore [--bench-file PATH] [--strategy NAME] [--dry-run]
```

It rewrites **only** the benchmark fields (`excess_pp`, `bench_symbol`, `bench_ret_pct`,
`bench_window`, `bench_note`). `pnl`, `fees`, `entry`, `exit`, membership, row order and
therefore `n` are untouched — a re-score can change the quality of the measurement but never
the sample. Rows without `ret_pct` are counted and skipped rather than having a return
synthesised for them. Rows that cannot be benchmarked get `null` plus a reason, never `0`.
Writes are atomic (`tmp` + `os.replace`), and it refuses to rewrite anything when the
benchmark series is unavailable.

## 3. Tests

`tests/test_forward_tracker_of_edges.py` — **19 passed**:

- `of_boundaries`: monotone boundaries, final ≥ 1.6449, inverse-sqrt clock (`b[0]/b[-1]` =
  `sqrt(n_final/looks[0])`), achieved alpha, single-look case = fixed-sample z, looser alpha
  gives smaller boundaries, cache identity.
- `interim_verdict`: no design → `None`; zero windows → `CONTINUE` with
  `endpoint_missing_rows == 0` (not `None`); one window below the first look → `CONTINUE`,
  `z is None`; one window at a single-look design cannot promote; **tied `(opened, closed)`
  rows collapse to one window**; endpoint falls back and reports `N of M`; overwhelming
  consistent excess promotes; kill rule fires at its window count and not before.

The tied-date test is the important one: it pins the rule that ten rows sharing one
`closed_at` are one market episode, not ten observations.

`selftest` is unchanged at **21/21**.

## 4. Restore: `template.html` / `index.html` were silently reverted again

`audit_dashboard/template.html` and `index.html` on disk had lost the `excess_column.js` and
`forward_clock.js` script tags (0 refs each; 19,010 lines vs 19,021 committed). The committed
blobs still had them, so this was a working-tree revert, not a bad commit. Both files were
restored from `c39a8affee3`. Nothing needed committing — the branch tree already had the
correct content; only the checkout was stale.

Prompted by this, the pages were actually driven in a headless browser (`tools/serve_local.py`
on :5173):

| Check | Result |
|---|---|
| `excess_column.js`, `forward_clock.js` loaded | yes |
| `window.PickExcess.state.loaded` | `true` (sidecar fetched) |
| Forward clock panel `#forward-clock-body` | renders, 4,383 chars — "Started 2026-11-15 · 0 closed trade(s) admitted · costs 6 bps/side" + the pre-registration explanation |
| Page errors | none (only expected 404s for production endpoints) |
| Excess cells on first load | **0** |

**Finding:** the `vs Bench` column is rendered only in the per-category **closed-trades
drill-down modal** (`renderClosedRow`, template ~L7362), whose header list already includes
`{ key: 'excess', label: 'vs Bench' }` in the correct position (immediately after `PnL%`), so
header and cell agree there. The default "Recent Closed Picks" tab builds its table through
`buildClosedColsFromActiveList`, which has no excess column, so on first load the number is
simply not on screen. That is a discoverability gap, not a misalignment bug — and it is not
fixed here, because that table has its own column/renderer pair and changing it without
checking its sorting and export paths would be a larger change than this note claims.

## 5. Also added (docs, no runtime effect)

- `reports/quant_audit/SINGLE_AGENT_PROMPT.md` — compressed one-agent audit prompt with a
  closed verdict vocabulary and a G1–G10 gate.
- `reports/quant_audit/PHASE1_HEAD_START.md` — verified map of money-maker / Kimi / protocol /
  instrument files, including two corrections: no file is named `RECOVERY_PROTOCOL*.MD` (the
  real ones are `research/profitability/PROTOCOL*.md`), and PBO / White's Reality Check code
  exists only in a worktree, not on the main path.
- `reports/quant_audit/AUDIT_REPORT_TEMPLATE.md`, `STRATEGY_SHORTLIST_TEMPLATE.md` — report
  templates whose gates cannot be filled in with adjectives.
- `reports/quant_audit/ASSET_CLASS_TRIAGE_2026-11-15.md` — per-class measurement from the
  closed ledger plus the measured verdict on the penny-stock "one skyrockets" thesis.

## 6. Verification run

- `python3 -m py_compile tools/forward_tracker.py` — OK
- `python3 -m pytest tests/test_forward_tracker_of_edges.py -q` — 19 passed
- `python3 tools/forward_tracker.py selftest` — 21/21
- `rescore` on a temp ledger (stale excess, missing excess, same-day window, other strategy):
  stale value recomputed (+10.6888pp), missing value filled (+7.4147pp), same-day cleared to
  `null` with `window_collapsed_to_one_trading_day`, other strategy untouched, second run a
  byte-identical no-op
- `rescore` on the real (empty) ledger — prints "nothing to rescore", exit 2, writes nothing
- headless browser against the restored page — table above

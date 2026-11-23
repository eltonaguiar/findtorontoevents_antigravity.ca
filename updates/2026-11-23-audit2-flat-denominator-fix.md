# audit2: `flat` could never be non-zero, so every breakeven trade was deleted from the class aggregates

**Date:** 2026-11-23
**Author:** buffy (freebuff)
**Files:** `alpha_engine/resolved_closed_view.py`,
`tests/test_zero_pnl_flat_classification.py` (new)
**Surface:** `/audit2` per-class verdict panel (`tools/build_audit2_per_class_panel.py` copies
`class_rollup()` verbatim; it computes none of these numbers itself)

---

## 1. What was broken

`tests/test_audit2_per_class_panel.py::test_panel_matches_golden_snapshot` failed:

```
AssertionError: CRYPTO.flat: panel 0 != golden 1
```

The golden file is generated from an **independent reference implementation** and its fixture
contains an explicit breakeven row (`SOL-USD:CRYPTO:0.0`). Reproduced and traced to the
predicate, not the rollup:

```
counts: {"input_rows": 6, "kept_rows": 5, "excluded_by_reason": {"zero_pnl_quarantined": 1}}
CRYPTO rollup: n=2 wins=1 losses=1 flat=0
is_performance_scored_row(pnl=0.0, exit_reason="TIME_EXIT") -> False
```

`is_performance_scored_row()` quarantined **every** zero-PnL row:

```python
if _pnl == 0.0:
    return False
```

That rule exists for a good reason (P0.0a: 3,645 `EXPIRED` zero-PnL placeholder rows were
inflating the denominator, and 567 are still excluded). But it erased a second, different thing:
a trade that **genuinely resolved at breakeven**. Two consequences:

1. **A published statistic was structurally unreachable.** The panel publishes a `flat` count
   and defines `win_rate_pct` as "percent of decided trades (excludes flat)". Because no zero row
   could enter the rollup, `flat` could only ever be `0` — a number that cannot vary is not a
   measurement, it is a claim about the data that was never tested.
2. **The bias had a direction.** A flat row's net is `0 − cost`, so deleting it removed its cost
   from `mean_net_pct` and dropped it from `n`. On the golden fixture CRYPTO moved from
   `n=2, mean_net=0.4003` (wrong) to `n=3, mean_net=0.2336` (right). The old figure **flattered
   the class** — it averaged a breakeven trade's cost out of existence.

## 2. What changed

A split, not a rollback. A zero-PnL row is admitted only when it carries evidence that it
resolved:

```python
_ZERO_PNL_RESOLVED_EXITS = frozenset({"TIME_EXIT", "TIME"})
...
if _pnl == 0.0:
    if exit_reason not in _ZERO_PNL_RESOLVED_EXITS:
        return False
    if not zero_close_marker and status not in _TERMINAL_STATUSES:
        return False
```

`TIME_EXIT` is grounded, not guessed: `audit_trail/universal_pick_resolver.py:1567` writes
`"exit_reason": "TIME_EXIT"` on the horizon-exit path, and `:1145` treats `TIME_EXIT / EXPIRED /
TIME / TIMEOUT / MAX_HOLD` as the time-exit family. `EXPIRED` is deliberately **not** in the
allowlist — that is the placeholder token the P0.0a quarantine was written for.
`default_exclusion_reason()` was updated in the same edit so the published exclusion counts
cannot describe a different rule than the predicate applies.

## 3. Blast radius (measured, not estimated)

| measure | value |
|---|---|
| canonical sidecar `excluded_by_reason["zero_pnl_quarantined"]` | **567** of 21,008 input rows |
| zero-PnL rows in the 3,500-row scored payload slice | 40 |
| of those, `TIME_EXIT` → now counted as `flat` | **29** |
| of those, `UNKNOWN` → still quarantined | **11** |

I did **not** extrapolate 29/40 across the other 527 quarantined rows; that needs a run over the
raw book, not a ratio.

**What moves and what does not:** `n`, `mean_gross_pct`, `mean_net_pct` change. `win_rate_pct`
does not (its denominator is wins+losses, and a flat row is excluded by definition), and
`profit_factor` does not (it sums gross win and loss magnitudes, and a flat row contributes
`0.0` to neither).

## 4. How it was verified

```
$ python3 -m pytest tests/test_zero_pnl_flat_classification.py \
    tests/test_audit2_per_class_panel.py tests/test_performance_scored_row.py -q
  36 passed in 0.21s          # includes the previously-failing golden snapshot test
$ python3 -m pytest tests/test_audit3_tribunal.py tests/test_audit3_g8_defaults.py \
    tests/test_selection_alpha_coverage.py -q
  53 passed in 1.70s          # the other consumers of the same predicate
```

The golden file was **not** regenerated — the reference is right and the panel was wrong, which
is what the peer request and the fixture both said.

`tests/test_zero_pnl_flat_classification.py` pins the rule in both directions, so the ratio of
flat to quarantined cannot drift again silently: a resolved breakeven is scored and counted as
`flat` without moving the win-rate denominator; an `EXPIRED` zero row, a zero row with no close
marker, and a `_auto_expired` row all stay excluded; the exclusion classifier agrees with the
predicate on both cases.

## 5. Not fixed here

- The 11 `UNKNOWN` zero rows in the slice are still quarantined. Whether they are unresolved
  placeholders or real flat trades is a resolver question, not a rollup question — admitting them
  on a guess is how the 3,645-row problem comes back.
- `FLAT_EPSILON_PCT` is `0.01` on gross, so a `+0.004%` trade is also a "flat" outcome. That is
  existing, documented behaviour (`WIN_DEFINITION`) and I did not touch it.

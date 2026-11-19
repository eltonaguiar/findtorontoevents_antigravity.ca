# intrabar resolver + observe-pod emission (2026-11-19)

**Author:** Kilo · **Scope:** `alpha_engine/intrabar_resolver.py` (new),
`tests/test_intrabar_resolver.py` (new), `tools/emit_observe_pods.py` (new).

## Why

`alpha_engine/forward_observations.py` accepts a forward row as evidence only
when `intrabar_first_touch` is `True`; daily/time-bar resolution is rejected
because it cannot see a stop hit inside the bar (the same defect that inflated
past win rates). The observe pods therefore cannot accrue forward rows without a
resolver that stamps that field honestly.

## What

- `first_touch(bars, direction, entry_price, stop_loss, take_profit)`:
  conservative first-touch resolution.
  - both stop and target inside one bar -> **STOP** (`same_bar_both=True`);
  - gap through the stop -> fill at the **open** (worse than the stop), never the stop;
  - LONG/SHORT mirrored; no bars -> `None` (unresolved, not a fake row).
- `stamp_pick(pick, bars)`: fills `intrabar_first_touch`, `resolver_version`
  (`intrabar.v1`), `resolved_outcome`, `resolved_price`, `resolved_at`.
- `tools/emit_observe_pods.py`: resolves observe-pod picks against a bars file
  and appends to `reports/forward_observations.jsonl` only with `--apply`.
  It **refuses to invent rows**: no bars -> `UNRESOLVED` and skipped; an
  unregistered `hypothesis_id` -> skipped.

## Data requirement (not faked)

The bars file must come from the price tables (`crypto_ohlcv`,
`equity_daily_ohlcv`, `fx_prices`, ...) or an exchange API. The tool does not
fetch, so a missing feed can never become fabricated evidence. Example:

```bash
python3 tools/emit_observe_pods.py \
  --picks reports/observe_pod_picks.json \
  --bars  reports/observe_pod_bars.json          # dry-run
python3 tools/emit_observe_pods.py ... --apply   # append forward rows
```

## Verification

```
python3 -m pytest tests/test_intrabar_resolver.py -q   # 8 passed
```
Cases covered: both-touch-same-bar -> STOP, target-only -> TP, gap-through fills
at open, time exit uses last close, SHORT mirrors, empty bars stays unresolved,
stamp marks intrabar true, invalid direction raises.

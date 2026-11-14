# 2026-11-14 — P0 truth fixes: FX KeyError, summary_picks WR>100%, None→0.0 coercion

Branch `fix/audit-p0-truth` (from `origin/main`). Three self-contained, low-risk, pure-Python fixes from the 2026-11-14 prediction-system audit (5-peer consolidated master plan `2026-11-14/finpredict/2026-11-14T160004Z/master-plan/PLAN.md`).

## What was broken

1. **FX direction bucket `KeyError: 'LONG'`** — `alpha_engine/scanner.py:2937-2942` built a `defaultdict` whose inner value was a plain dict with only `BUY`/`SELL` keys. Any forex signal carrying `signal_type="LONG"`/`"SHORT"` raised `KeyError: 'LONG'` and killed the whole scan — the dominant CI failure cluster (93 failed ALPHA runs/24h).
2. **`summary_picks.json` reported win-rate >100%** — `tools/sync_summary_picks_json.py:63-65` counted `wins`/`losses` over *all* rows (including `OPEN`/`FORCE_CLOSED`/`TIME_EXIT`) while `resolved` counted only terminal statuses, so 7 classes published impossible WR (INDEX 1141.2%, FUTURES 363.9%, …).
3. **`None → 0.0` entry coercion** — `alpha_engine/prediction_market_consensus.py:589-591` forced missing `entry_price`/`take_profit`/`stop_loss` to `0.0`, producing phantom `entry=0.0` picks (e.g. `XRPUSDT SHORT entry 0.0`).

## What was changed

1. `alpha_engine/scanner.py` — normalize forex direction via `_forex_dir_map` (`LONG→BUY`, `SHORT→SELL`, unknown→`BUY`) before bucketing. No behavior change for `BUY`/`SELL`; a malformed emitter can no longer crash the scan.
2. `tools/sync_summary_picks_json.py` — `wins`/`losses` are now a strict subset of `resolved` (terminal-status predicate only); added `min(wins, resolved)` clamp in `win_rate_pct`.
3. `alpha_engine/prediction_market_consensus.py` — removed `or 0` coercion so missing prices stay `None` (status already degrades to `SIGNAL` on the preceding line).

## Verification

- `py_compile` clean on all 3 files.
- Functional smoke test: FX bucket no longer raises on `LONG`/`SHORT`/unknown; PM merge keeps `entry_price=None`; `wins+losses <= resolved` invariant holds across sampled statuses.
- Post-merge acceptance: `summary_picks.json` must contain no `win_rate_pct > 100`; `alpha_engine/scanner.py` forex path must not raise `KeyError` on `LONG`/`SHORT` signals; no new `entry_price=0.0` rows from `prediction_market_consensus`.

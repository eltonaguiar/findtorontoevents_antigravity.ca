# Emission-Cap Policy — Swarm Decision (2026-06-09)

**Operator directive:** decide the non-crypto emission-cap policy via a multi-engine swarm
(not unilaterally), because more picks → faster money-ready, BUT uncapping risks the
over-emission that falsified the CT=F DSR=1.0 (6.33× duplication).

## Verdict: **Option A — Shadow-uncap + per-class sized cap** (consensus)
- **deepseek:** Option A. "The core problem is not the calendar rate but the *information rate* —
  uncapping re-emits correlated signals, inflating n without adding independent evidence, which
  corrupts DSR/PBO. A solves both starvation (EQUITY gets a dedicated lane) and over-emission
  (sized lane enforces 1 emission/unique-signal-week). Shadow lane builds n for measurement only,
  never contaminating the verdict (`forward_test_only=1`, never sized)."
- **gemini:** Option A. "DSR/PBO rely on the IID assumption; over-emission violates it by inflating
  n with correlated trades, compressing variance without adding information. A lets EQUITY breathe
  via per-class caps while strict dedup in the live lane guarantees independence; uncapped signals
  are sequestered in the shadow lane."
- **xai:** pending at write time; 2/2 unanimous is decisive. (Swarm output: `swarm_runs/cap_decision_2026-06-09/`.)

## Implemented (core, this session — `alpha_engine/non_crypto_policy.py`)
- `PER_CLASS_DAILY_CAP = {EQUITY:15, COMMODITY:10, FOREX:8, ETF:8, BOND:8, FUTURES:8}`
  (env override `MAX_TRADES_PER_DAY_<CLASS>`; global backstop `MAX_TRADES_PER_DAY_TOTAL=40`).
- `is_daily_cap_reached(now, asset_class, forward_test_only)`:
  - `forward_test_only=True` → **never blocked** (shadow lane; dedup is the emitter's job).
  - `asset_class` set → per-class sized cap.
  - `asset_class=None` → legacy global cap (back-compat; existing callers unaffected).
- `count_trades_today(now, asset_class)` now class-aware + **excludes shadow picks** from the
  sized count.
- `check_emission_gates(symbol, now, asset_class, forward_test_only)` threads both params.
- Verified: EQUITY cap 15, others 8, shadow bypasses, env override works, legacy no-arg works.

## Activation follow-up (NOT yet done — for me or DeepSeek WS3)
The gate now SUPPORTS per-class + shadow, but callers still invoke `check_emission_gates(symbol, now)`
without `asset_class`, so they get the legacy global cap until wired. To activate Option A:
1. Pass `asset_class=<pick class>` + `forward_test_only=<pick flag>` from each emission caller
   (`multi_asset/scanner.py`, `multi_asset/forex_strategies.py`, `commodity_signal_generator.py`,
   `smart_picks_engine.py`, etc.).
2. Add emitter-side dedup: ≤1 sized emission per `(strategy, symbol, direction, signal-week)`.
3. (DeepSeek WS3 token-bucket = the queue-don't-drop layer on top.)

DSR/PBO protection: **yes** — the sized lane stays deduped/independent; shadow picks are
`forward_test_only` and excluded from the money-ready verdict cohort, so they cannot inflate n.

# 2026-11-14 — kimi stop-fill recording, B4 settled, EQUITY-vs-SPY gate

Follow-up work on the `final_v3` review package (PR #771). Three items, two of
which changed a published conclusion. Per AGENTS.md this records what was
broken, what changed, and how it was verified.

## 1. What was broken — kimi booked P&L at the polled price

`KIMI_RISEOFTHECLAW/live_scanner.py` fires its ATR stop when the **polled** price
is already past it:

```python
elif curr <= _pick_stop:
    exit_reason = f"STOP_LOSS {ret*100:.1f}% (ATR stop={_pick_stop:.4f})"
...
gross_pnl = alloc * ret     # ret measured from `curr`, the polled price
```

A resting stop cannot fill at the price the market had drifted to by the time the
cron ran. Measured across the 815 `kimi_riseoftheclaw` `SL_HIT` rows in the live
payload:

- **0 of 815** booked at the stop they exited against
- 778 carry `STOP_LOSS -X% (ATR stop=P)`; P ≠ `exit_price` in **778/778**
- P differs from the row's `stop_loss` field by a median **1.69%** (p90 3.79%)

Three different prices per exit (field, reason text, booked price). Any metric
built on `stop_loss` measures a number the trade never used.

## 2. What changed

| file | change |
|---|---|
| `audit_trail/stop_fill.py` | new `exit_fill_for_stop()` (fill at stop; at bar open on a gap) and `price_reached()` (was a level ever traded?) |
| `KIMI_RISEOFTHECLAW/live_scanner.py` | books at the fill via `_stop_fill_for_close()`, not `curr`; `TAKE_PROFIT` now fills at the target (it was crediting gains beyond the limit); adds `exitPrice`, `polledPrice`, `stopUsed`, `targetUsed`, `exitPriceBasis`; audit log records fill + polled price + basis |
| `tools/equity_vs_spy.py` | new pre-registered per-pick benchmark test |
| `tools/stop_fill_replay.py` | `--truncate-at-exit`; splits never-touched stops into "reached a different level" vs "never reached the recorded exit" |
| `tests/test_kimi_exit_fill.py` | new, 15 tests |

The exit fill defaults to the stop level when no OHLC is at hand (the resting
order model) and to the polled price only if the model itself is unavailable —
recorded as basis `polled_late` so that fallback stays visible instead of silent.

## 3. Verification

`python3 -m pytest tests/test_kimi_exit_fill.py tests/test_stop_fill.py tests/test_per_class_cost_gate.py tests/test_cot_contrarian_backtest.py -q`
→ **66 passed**. All five touched modules `py_compile` clean.

Full-population correction using the **executed** ATR stop (implied risk ≤ 25%):

| class | rows | recorded | at-stop | delta |
|---|---:|---:|---:|---:|
| CRYPTO | 152 | −858.4 | −790.9 | +67.5 |
| EQUITY | 302 | −1380.2 | −1131.8 | +248.4 |
| ETF | 256 | −584.9 | −499.9 | +85.0 |

**Correction to a number I published earlier today:** PR #771 said the kimi
crypto leak was **+727.3pp**. It is **+67.5pp**. The larger figure differenced
against the drifted `stop_loss` field, so it measured the field mismatch, not the
fill. Crypto remains −770pp; PF moves 0.768 → ~0.80, not ~1.00.

## 4. B4 settled — wrong label, not wrong price

Truncated replays (`--truncate-at-exit`), 25 rows per class:

| class | touched | never touched | of the never-touched: other level | never reached |
|---|---:|---:|---:|---:|
| EQUITY | 11 | 14 | 11 | 3 |
| ETF | 12 | 13 | 12 | 1 |

Non-crypto "`SL_HIT`" rows overwhelmingly exited on a **different level**
(trailing stop / target / hold limit). The exit taxonomy is wrong. Two operational
consequences:

1. Do **not** extend the stop-fill model to non-crypto exits — 44–52% never
   touched their stop, so the model would be fitted to a false label.
2. Gap-aware filling makes EQUITY *worse* than the recorded number (−83.62 vs
   −63.41pp on the touched subset, 45.5% gap-through). Those rows are not fills
   to improve; they are exits to reclassify.

## 5. New bug found: B14 — cross-symbol stop contamination

`ADA-USD`, entry `0.201105`, `STOP_LOSS -5.1% (ATR stop=92.2514)`. An ATR stop of
92 on a $0.20 asset is another symbol's stop. Left in the correction it injected
**+45,772pp** of fake improvement from a single row. 1 of 153 crypto ATR rows
(0.65%), unbounded blast radius. The implied-risk ≤25% bound is now part of the
measurement rather than a post-hoc cleanup.

## 6. EQUITY vs SPY — gate FAILED

Pre-registered in `tools/equity_vs_spy.py`: n ≥ 100, mean excess > 0, t ≥ 2.0,
mean excess > cost. Per-pick pairing against SPY over each pick's own holding
window, adjusted closes, shorts vs −SPY.

738 pairs, mean hold 4.37d: strategy +0.3230%, SPY +0.1138%, **excess +0.2092%**,
**median excess −0.5726%**, **t=1.05**, beat-SPY 45.53%.

| gate | result |
|---|---|
| G1 n ≥ 100 | PASS |
| G2 mean excess > 0 | PASS |
| G3 t ≥ 2.0 | **FAIL** |
| G4 excess > cost | PASS |

**VERDICT: `NO_ALPHA_BETA`.** EQUITY clears its cost gate at 3.23× and still does
not beat the index; the positive mean is a right tail over a negative median. The
focus decision in `final_v3/03_focus/DECISION.md` is revised accordingly (dated
section appended).

## 7. Limits

- Correction is arithmetic on ledger fields, not a candle replay: it assumes the
  stop in the reason string is the one that was live, which B4 shows is not always
  safe for non-crypto rows.
- Replays are n=25 per class, 1h bars, evenly spaced samples.
- `closed_at` is absent on some ledger rows, so truncation silently fell back to
  no truncation there; the replay reports per-row status so this is visible.
- No forward data exists for the shipped scanner change. Post-fix profitability is
  **unmeasurable today**, which is not the same claim as unprofitable.

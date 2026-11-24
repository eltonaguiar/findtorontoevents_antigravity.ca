# B1 root cause: the pod is registered against strategy names that do not exist

**Date:** 2026-11-20T01:05Z · **Author:** kilo · **Evidence:** direct DB queries (read-only)

## Finding

`POD-EQUITY-BREAKOUT` (`H-BABY-EQUITY-VT-PATTERN-SWEEP-001`) is registered for four strategies:

`donchian-stock-breakout`, `rs-breakout-scout`, `vol-contraction-scout`, `adx-trend-scout`

**None of the four exists in any of the three tables:**

| Table | Rows for the four strategies |
|---|---|
| `trading_picks` | **0** |
| `at_pick_outcomes` | **0** |
| `at_signal_outcomes` (51,109 rows total) | **0** |

So this was never an "emitter forgets to write intrabar outcomes" bug. The strategies have **never
been emitted at all**. They appear only in the audit3 payload/backtest namespace, which is why the
pod scored 8 confirmatory cells in the ledger while the forward ingest rejects every row.

## What the DB actually contains

Similar, but differently named, strategies *are* emitted:

| Where | Strategy | n |
|---|---|---|
| `trading_picks` | `donchian_breakout_scalp` | 81 |
| `trading_picks` | `proven_donchian_adx_trend` | 55 |
| `trading_picks` | `adx_momentum` | 95 |
| `trading_picks` | `obv_divergence_breakout` | 91 |
| `at_signal_outcomes` | `donchian_breakout_scalp` | 27 |
| `at_signal_outcomes` | `proven_donchian_adx_trend` | 11 |
| `at_signal_outcomes` (EQUITY/ETF) | `vt_equity_two_day_rsi_reversal` | 136 |

The pod's thesis (breakout/momentum on equities) is *approximately* represented by
`donchian_breakout_scalp`, `proven_donchian_adx_trend` and `adx_momentum` — but those were never
pre-registered.

## The two honest options

**A. Amend the pre-registration to real emitters (recommended).**
Register the pod against strategies that actually emit, in a dated amendment:

```
H-BABY-EQUITY-VT-PATTERN-SWEEP-001 (amended 2026-11-20)
strategies: donchian_breakout_scalp, proven_donchian_adx_trend, adx_momentum
```

This must be recorded as an **amendment**, not a silent swap: the forward clock restarts at the
amendment date, and every row accrued under the old names (there are none) stays excluded. Amending
is legitimate because no forward evidence exists yet — changing it *after* accrual would be p-hacking.

**B. Implement the four named strategies as real emitters.**
More work, and the thesis is already covered by A's three strategies. Choose B only if there is a
specific reason those exact forms matter.

## Why this matters beyond B1

- The `2026-11-26` watchdog deadline was based on "emitters never landed". The truer statement is
  "the pod was registered against non-emitted names". Both turn the job red; only one is fixable by
  changing data rather than code.
- The audit3 ledger can display confirmatory cells for strategies that no live system emits. That is
  a general risk: **a cell should declare whether its strategies exist in the emission tables.** A
  cheap check: `strategy EXISTS in trading_picks` → flag the cell `emitted: true|false`.
- The same check should run for every pod, not just this one.

## Verification query (read-only)

```sql
SELECT strategy, COUNT(*) FROM trading_picks
WHERE strategy IN ('donchian-stock-breakout','rs-breakout-scout',
                   'vol-contraction-scout','adx-trend-scout') GROUP BY strategy;
-- returns 0 rows
```

---

## 2b. FOLLOW-UP (02:35Z): the obvious amendment is a trap

Before proposing "amend the pod to the real emitters", I checked what those emitters actually emit:

| Strategy | Asset classes in `at_signal_outcomes` |
|---|---|
| `adx_momentum` | CRYPTO 25 |
| `donchian_breakout_scalp` | CRYPTO 26, MEMECOIN 1 |
| `proven_donchian_adx_trend` | CRYPTO 6, COMMODITY 3, FUTURES 2 |

**Zero EQUITY or ETF rows.** `trading_picks` shows 95 / 81 / 55 rows for the three names, but the
same picture: they are crypto/futures/commodity strategies that happen to share a name family.

So amending `POD-EQUITY-BREAKOUT` to those three would attach **crypto rows to an equity pod** —
a worse error than the current phantom registration, because it would accrue *wrong* forward
evidence rather than none.

**Revised conclusion:** `POD-EQUITY-BREAKOUT` has **no live equity/ETF emitter at all**. The only
honest options are:

1. **Park the pod** (`status: parked_unemitted`) and stop citing it as the EQUITY path. The
   $2k plan's EQUITY sleeve then has no executable strategy and the 90/0/10 split stands on
   core beta alone.
2. **Implement an equity breakout emitter** (donchian/ADX/vol-contraction on EQUITY+ETF) as a
   real code change, register it, and restart the clock at the implementation date.

Do **not** amend the pod to `donchian_breakout_scalp` / `proven_donchian_adx_trend` / `adx_momentum`.

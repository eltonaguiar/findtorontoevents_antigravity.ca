# 2026-11-15 — MomentumEMA crypto allocation halted (explicitly), and a retracted t-statistic

Requested: "Halt MomentumEMA's crypto allocation in the pick pipeline since it is 58% of the class
shortfall at t=-7.84."

Two things were true before I changed anything, and both change the shape of the fix.

## 1. The halt was already in force — globally, not per class

```text
$ python3 -c "from alpha_engine.strategy_blocklist import is_blocked_strategy, block_reason
              print(is_blocked_strategy('MomentumEMA','CRYPTO'), block_reason('MomentumEMA','CRYPTO'))"
True retired                       # for CRYPTO, EQUITY, ETF, FOREX, and ''
```

`MomentumEMA` entered `_RETIRED_STRATEGIES` on 2026-06-05 (`alpha_engine/strategy_blocklist.py:235`)
via the auto kill switch — *n=54 WR 18.52% avg_pnl=-1.074%* — and the live payload confirms **0 active
MomentumEMA picks**. The 73 crypto rows in the ledger are historical: entered 2026-02-20 .. 2026-06-08,
all from `source_system: signal_validation`.

So the correct action was **not** to add another block and call it done. Nothing was emitting.

## 2. The `t = -7.84` I published was not a valid significance claim

All 73 rows share **one** `closed_at` value:

```text
distinct closed_at: 1        distinct entry days: 37        symbols: 9
```

A batch close writes the same timestamp to every row, so every window resolves to the **same benchmark
exit price**. The 37 windows differ only by entry date and are exposed to a single market episode.

`cluster_t()` already collapsed same-window picks and withheld t below 5 windows, but it never asked
whether the windows had *different exit dates*. With one exit date, "37 independent windows" is one
observation of one exit move. **The t-statistic is withdrawn in `EXCESS_RETURNS.md` (marked `n/a †`),
and the limitation is stated in that document rather than quietly deleted.**

This does not rescue MomentumEMA: a **4.1% excess win rate** across 73 picks with a −11.56pp mean is
not something a shared exit date manufactures. It means the *size* claim stands and the *significance*
claim does not.

## Changes

| File | Change |
|---|---|
| `audit_trail/quality_gates.py` | Added `("CRYPTO", "MomentumEMA")` to `BLOCKED_ASSET_STRATEGY_PAIRS`, with the measured numbers, the reason it is defense-in-depth, and a re-admission condition |
| `tools/pick_excess.py` | `MIN_EXIT_DAYS = 3`: `t_cluster` is withheld when windows share fewer than 3 distinct exit dates. `agg()` emits `n_exit_days`; the crypto table prints an `exit` column and flags `BATCH-CLOSE` |
| `WIRED_IN/.../EXCESS_RETURNS.md` | MomentumEMA t → `n/a †`, paragraph rewritten as an explicit retraction |
| `WIRED_IN/.../README.md` | Removed the `t −7.84` claim; states the batch-timestamp reason |
| `reports/pick_excess_returns.json` | Regenerated with `n_exit_days` and the withdrawal applied |

### Why the block is scoped to CRYPTO and the global retirement was left alone

A blanket verdict would be wrong here. The same rule records **WR 69.1% on EQUITY (n=55)** in this
repo's own audit notes, and `("FOREX", "MomentumEMA")` is *already* pair-blocked. `_RETIRED_STRATEGIES`
is class-agnostic, which means it currently over-blocks EQUITY as a side effect of a crypto verdict.

I did **not** un-retire it: that would re-admit a rule whose only measurable application (crypto) loses
almost every time, and relaxing a global kill is a capital decision, not a cleanup. Documented here so
the choice is visible.

The `("CRYPTO", "MomentumEMA")` pair entry exists so the crypto halt survives a future narrowing of the
global list to class level — the exact edit that would otherwise silently unblock crypto.

---

## Verification

| Check | Result |
|---|---|
| `is_blocked_strategy('MomentumEMA', class)` for CRYPTO/EQUITY/ETF/FOREX/'' | **True / `retired`** in all five |
| `('CRYPTO','MomentumEMA') in BLOCKED_ASSET_STRATEGY_PAIRS` | **True** after the edit (was False; only FOREX was present) |
| Active MomentumEMA picks in live payload | **0** |
| `quality_gates` import | clean (pair set 129 → 130) |
| `pick_excess.py` re-run | exit 0; MomentumEMA `t_cluster = None`, `n_exit_days = 1`, flagged `BATCH-CLOSE` |
| Class-level numbers unchanged by the guard | EQUITY +0.238pp, ETF +0.023pp, CRYPTO −0.795pp |
| `quality_gates.py` diff vs `origin/main` | only the inserted block — no other agent's edits swept in |

**Not verified:** the gate's effect on *future* emissions cannot be observed from a static payload — it
is confirmed by the API returning True and by 0 active picks, not by a live scan run. No test executes
`BLOCKED_ASSET_STRATEGY_PAIRS` for this pair; the enforcement lines
(`audit_trail/quality_gates.py:4688`, `:8462`) are unchanged and pre-existing.

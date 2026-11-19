# Forward-evidence contract (`forward_observations`) — 2026-11-19

Closes the last open item from external review v3 (§5.8): *"Without this, audit3 can
never mint a PROVEN verdict from live data."*

## The problem it fixes

audit3 scores the **past**. Every number on the page — 10 KILL cells, 3,500 scored
rows, the class verdicts — is a re-score of realized history. Nothing defines what a
*forward* row is, what its net return means, how many are needed, or when one may
promote a hypothesis. So "PROVEN from live data" was not merely unearned; it was
undefined. A tribunal that can only re-score history is a museum with good lighting.

## Row shape

`alpha_engine/forward_observations.py`, one JSONL row per closed forward observation:

| field | type | notes |
|---|---|---|
| `id` | str | unique row id |
| `hypothesis_id` | str | **FK to `reports/hypothesis_registry.json`**; a dangling id is a validation error |
| `opened_at`, `closed_at`, `created_at` | ISO-8601 | `closed_at >= opened_at` enforced |
| `symbol`, `asset_class`, `side` | str | `side` ∈ {LONG, SHORT} |
| `entry_px`, `exit_px` | float | `entry_px > 0` |
| `qty` | float | `> 0` — without it fees cannot become a return |
| `fees`, `funding` | float | **absolute account currency**; negative funding = received |
| `slippage_bps` | float | `>= 0` |
| `resolver_version` | str | non-empty, so re-resolutions are distinguishable |
| `intrabar_first_touch` | bool | must be `true` — see below |
| `benchmark_leg_ret` | float\|null | matched-exposure leg, for "beat holding" |
| `regime_ok` | bool | recorded, not gated |

## One definition of net return

```
gross = side_sign * (exit_px - entry_px) / entry_px
cost  = (fees + funding) / (qty * entry_px) + slippage_bps / 10_000
net   = gross - cost
```

Rows that cannot produce a number are **skipped, never zero-filled** — a missing cost
is not a free trade. This is the same complaint the review made about hard-coded
slippage constants, applied to the forward side.

## Promotion rule (all required)

1. `n_forward >= 100`
2. `net PF CI-LB > 1.0` (symbol-day clustered bootstrap via `tools/pf_ci_lower.py`)
   **or** per-trade `IR >= 0.5`. The review wrote "net CI-LB>0 (or IR≥0.5)"; breakeven
   PF is 1.0, so both readings are implemented and either clears.
3. `intrabar_first_touch is true` on **100%** of rows — daily resolution inflated PF
   2.8× on FOREX consensus (H-118) and 2.09× on COMMODITY (H-120). A daily-resolved
   forward row would reintroduce exactly the artefact that refuted those edges.
4. `benchmark_leg_ret` present on **≥90%** of rows.

Excess return vs the benchmark leg is reported as a **descriptor**, not a gate: the
review asked for the leg to exist, not for a threshold nobody has calibrated.

## The clock

`--clock H-119` reports `n_forward`, `n_needed`, rows in the last 30 days, the observed
accrual rate, and an ETA **only when there are rows to extrapolate from**:

```
$ python3 -m alpha_engine.forward_observations --clock H-119
H-119: 0/100 forward rows, 0.0/day, status NO_FORWARD_ROWS
```

This is the deliberate opposite of the `~2026-06-25` promise that sat on the H-119 card
for months: a rate you observed, or nothing.

## What is deliberately not wired

**Ingestion.** Reading a cohort out of MySQL needs the RSI/session stampers plus a DB
connection, so this ships the contract, the verifier, the clock and the promotion rule,
and leaves the ledger honestly empty (`reports/forward_observations.jsonl`, 0 rows).
Zero rows cannot promote anything — the correct state until an adapter fills it.

Consequence, stated plainly: **`PROVEN_T2` is currently unreachable from forward
evidence**, because there is none. audit3's zero PROVEN verdicts are therefore correct,
not a bug.

## Usage

```
python3 -m alpha_engine.forward_observations --verify            # integrity + dangling FKs
python3 -m alpha_engine.forward_observations --clock H-119       # accrual rate / ETA
python3 -m alpha_engine.forward_observations --promotion H-119   # apply the rule
python3 -m alpha_engine.forward_observations --append rows.jsonl # validate + dedupe + append
```

Appends are idempotent on `id` and on `(hypothesis_id, symbol, side, opened_at)`, and
rejected rows are returned with their errors rather than silently dropped.

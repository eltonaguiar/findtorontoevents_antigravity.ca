# Graduation runbook — paper sleeve → micro-live

**Date:** 2026-11-20 · **Owner:** kilo (deepseek-flash via Kilo extension) · **Status:** v1, applies to
every sleeve in `paper_trading/sleeves.json`

This is the only document that authorises real money. A sleeve that has not satisfied **every**
gate here stays paper, no matter how good its backtest looks.

---

## 1. Preconditions (must exist before the clock starts)

1. A committed `paper_trading/sleeves.json` entry with `preregistered_at` set **before** the first
   trade, and a `thesis` that names the evidence and its known weaknesses.
2. A config test that pins the universe, `top_n`, lookback and cadence
   (see `test_rotation_sleeve_matches_the_validated_spec`).
3. A **random-entry** control arm for timing and a **beta-matched hold** arm for selection
   (`etf-rotation-random`, `etf-hold`). A sleeve without both arms is not comparable.
4. A backup tag: `archive/<date>/<sleeve>`.
5. The strategy's DSR **family size declared in writing** before any variant is run. Five sleeves
   with 4–6 variants each is 20–30 trials; a DSR computed against an understated N is meaningless
   (buffy's warning, accepted).

## 2. Promotion gates (all required, not a score)

| Gate | Threshold | Why |
|---|---|---|
| Forward rows | **n ≥ 200** (n ≥ 100 triggers a first review only) | the effect must be measured on post-registration data |
| Net CI lower bound | **> 0 at 2× measured class slippage** | survives costs and cost mistakes |
| DSR | **≥ 0.95** with declared `n_trials` (global floor 658) | overfit correction |
| Split-half | both halves net-positive | stability |
| Concentration | no symbol > 60 %, no source > 90 % | not one lucky name |
| Control arms | beats **both** the random arm and the beta-matched hold arm | separates skill from timing and beta |
| Reconciliation | 3 consecutive months, daily marks vs ledger clean (no unexplained gap > $1) | the number is real |
| Staleness | no unresolved data gap in the sleeve's inputs | |

A sleeve that fails any gate is **not** "almost ready"; it is unproven.

## 3. Sizing ladder

1. **Paper** (current): $0 real. Marks only. No exceptions.
2. **Micro-live**: ≤ 10 % of the sleeve's target allocation, ≤ 2 % account risk per position.
   Drawn from the core allocation, never from new money.
3. **Full sleeve**: only after two further clean quarters at micro-live, same gates re-checked.

## 4. Kill-switch (any one triggers a freeze)

- Drawdown ≤ **−15 %** from the sleeve's high-water mark
- **3 consecutive negative months**
- Any promotion gate regresses (DSR, cost, concentration, control arms)
- A reconciliation break > $1 unexplained for 2 days
- Input data stale beyond the sleeve's tolerance

**Freeze means:** no new entries, existing positions managed per the pre-registered exit, and a
written post-mortem within 48 h. A frozen sleeve is never silently restarted.

## 5. Reconciliation (daily)

1. Marks are appended by `paper_trading/sleeves.py --mark` (idempotent per date).
2. `tools/sleeve_daily_summary.py` writes `audit_dashboard/data/sleeve_summary.json`.
3. Any difference between the sleeve's equity and the summed positions + cash is an incident, even
   if small — it means the accounting is wrong, not the market.

## 6. Experiment protocol (vol targeting, RVOL, TP/SL)

- **Same entries, paired bootstrap.** Never compare two independently recruited samples.
- **At most 5 pre-registered configurations.** A 96-config grid is 6,432 hypotheses across 67 cells
  and cannot survive correction.
- Log every trial, including the ones that failed, in the strategy record — the DSR must use the
  true count.
- An overlay that cannot beat its own baseline on the same entries is discarded, not tuned.

## 7. Decision record (attach to the PR that changes money)

```
SLEEVE: <id>
GATES: n=<n> | net CI [<lo>,<hi>] at 2x | DSR=<x> (trials=<n>) | halves=<ok/fail>
       | symbol max=<x%> | source max=<x%> | beats random=<y/n> | beats hold=<y/n>
       | months clean=<n>
DECISION: promote-to-micro-live | keep-paper | freeze
EVIDENCE: <ledger sha / report path>
SIGNED: <agent> <timestamp>
```

## 8. Rollback

Removing a sleeve is a data change, never a source change: delete its `paper_trading/sleeves.json`
entry, keep the state file for the record, and tag the removal. No branch surgery, no deleted history.

---

**Why this document exists:** the system has 0 proven cells, 0 candidates, selection alpha
−0.27 %/trade, and zero forward rows for its only pre-registered pod. The runbook's job is to make
it structurally impossible to call something "ready" without evidence.

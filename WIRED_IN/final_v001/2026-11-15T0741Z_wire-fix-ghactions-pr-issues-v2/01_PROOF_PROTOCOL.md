# 01 — Canonical Proof Protocol (single source of truth)

The repo currently has at least four incompatible gate counts: "0/10"
(`0703Z_childlike-airport`), "0/11" (`0700Z_finpredict-summary`), "9-gate +
Gate 10" (`CRYPTO_AUDIT.md`), and the 10-gate list in the WIRED_IN README. That
drift makes every verdict unfalsifiable. This file **replaces all of them**.

A strategy is **PROMOTED (money-ready)** only if it passes **Gate 0 through Gate
9** on the *live forward ledger*. Anything else is `TESTING`, `SHADOW`, or
`KILLED`. No exceptions, no "backtest passed so it's basically done".

| Gate | Name | Pass condition | Evidence artifact |
|------|------|----------------|-------------------|
| **0** | Data integrity | Bars are real, deduped, and free of flat-close/frozen-price artifacts. `exit_price != entry_price` unless a true flat close ≤ 1 tick. No ghost rows. | `audit_dashboard/data/data_integrity_report.json` |
| **1** | Pre-registration | Hypothesis has an `H-id`, fixed entry/exit/universe/params/TF, a stated **trial count**, and a benchmark, written **before** results. | `state/forward_test/plan.json` entry |
| **2** | Cost-adjusted backtest | Net-of-cost PF > 1.0 and positive net expectancy vs **same-window benchmark**, after the per-class friction model. | `reports/backtest/<H-id>.json` |
| **3** | Statistical significance | Bootstrap 95% CI lower bound on net return > 0; **DSR ≥ 0.95** deflated for trials; **PBO < 0.5**. | same artifact |
| **4** | Walk-forward OOS | Purged/embargoed WF; OOS net edge retains ≥ 50% of IS edge and OOS PF > 1.0. | same artifact |
| **5** | Robustness | Survives 2× costs, parameter neighbourhood (±1 step), regime split (bull/bear), and symbol-subset perturbation. | same artifact |
| **6** | Forward ledger | **≥ 100 closed forward trades** (or ≥ 152 non-overlapping windows for slow strategies), pre-registered, net-of-cost, live prices. | `state/forward_test/ledger.jsonl` |
| **7** | Benchmark excess | Mean excess vs same-window benchmark **> 0** with **t ≥ 1.96** (or Bonferroni/FDR-adjusted threshold for the number of simultaneous strategies). | `reports/pick_excess_returns.json` |
| **8** | Implementation | Capacity/liquidity OK, slippage model applied, position sizing defined, no look-ahead, borrow/funding where relevant. | `reports/implementation/<H-id>.json` |
| **9** | Monitoring | Live drift monitor + auto-retire trigger wired; alerts on gate breach. | `.github/workflows/money-ready-*.yml` |

## Verdict states (exactly one per strategy per class)

- `KILLED` — failed Gate 0/2/3/4/5 with n ≥ 20, or mean excess < 0 at n ≥ 50.
- `TESTING` — pre-registered and collecting forward trades; not yet at n.
- `SHADOW` — passed 2–5, forward in progress, shown on `/audit` as shadow.
- `PROMOTED` — passed 0–9. The **only** state allowed to size real capital.

## Kill rules (mechanical, not discretionary)

```
KILL if  n >= 20 and mean_excess < 0 and bootstrap5(PF) < 1.00
KILL if  n >= 50 and mean_excess < +0.25pp
KILL if  DSR < 0.95 with true trial count
PROMOTE requires: n_closed >= 100, mean_excess > 0, |t| >= 1.96,
                  DSR >= 0.95, PBO < 0.5, Gate 5 pass
```

## Trial accounting (Gate 3 cannot be gamed)

- The **true trial count** = every parameter set, symbol subset, TF, and filter
  actually evaluated — including abandoned sweeps. It is recorded in
  `state/forward_test/trial_count.json` and grows monotonically.
- DSR is computed against that count, not against the 2–3 strategies that
  survive. PBO requires `n_strategies >= 5`; today it prints `N/A`
  (`n_strategies=2`), which means **Gate 3 is currently unevaluable** — treat
  that as a fail.

## Per-class friction model (Gate 2 minimum)

| Class | Round-trip cost (default) | Extra |
|-------|---------------------------|-------|
| EQUITY | 12 bps (6/side) | borrow on shorts |
| ETF | 12 bps | premium/discount |
| CRYPTO | 30 bps (15/side) | funding on perps |
| FOREX | spread + 1 pip | swap/carry |
| BOND | 12 bps | liquidity |
| COMMODITY_FUTURES | 1 tick + commission | roll |
| MUTUAL_FUND | NAV + redemption | T+1 |
| PENNY | 60 bps + slippage | wide spreads |

Costs are configurable per strategy in `plan.json` (`fee_bps_per_side`) but the
class default is the **floor**; a strategy may not claim a lower cost without a
broker receipt.

## Benchmark map (Gate 7)

`EQUITY→SPY`, `ETF→SPY`, `MUTUAL_FUND→category benchmark fund`,
`BOND→AGG`, `FOREX→DXY (or pair buy-and-hold)`, `CRYPTO→BTC-USD`,
`COMMODITY_FUTURES→GLD (or the underlying B&H)`, `PENNY→IWM`.

## Why this protocol

It converts every ambiguous WIRED_IN claim into a pass/fail with a named artifact
and a number. The forward ledger is the binding constraint on purpose: the whole
failure mode of this repo is **backtests that never become forward trades**.

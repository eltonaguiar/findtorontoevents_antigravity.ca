# Metric definitions contract

What each surface actually measures, before any reconciliation is judged.
Every metric below has a formula, a cost basis, a population, a window, and a code location.
Written 2026-11-22 from the frozen payloads in `_raw/` and the source that generates them.

This file is a contract, not an opinion. If a definition here is wrong, every downstream
comparison is wrong, so it is the first thing to challenge.

---

## 0 The three surfaces at a glance

| Surface | Publisher | Unit of verdict | Cost model | Population |
|---|---|---|---|---|
| `/audit` | `audit_trail/dashboard_generator.py` + `alpha_engine/money_ready_verdict.py` | asset class | `SLIPPAGE_BPS` (CRYPTO 15, EQUITY 10, COMMODITY 12, ETF 8, FOREX 5, BOND 8, FUTURES 10) | `dashboard_data.resolved_closed_picks_net` |
| `/audit2` | `audit_dashboard/data/audit2_*.json` | forward pod / hypothesis | inherits the ledger | the forward ledger, `n_rows` 447 |
| `/audit3` | Quant Kill Tribunal ledger | cell, then class | `slippage_pct_by_class` (CRYPTO 0.0996, EQUITY 0.05, COMMODITY 0.15, ETF 0.05, FOREX 0.02, BOND 0.05, FUTURES 0.1, MEME 0.3, PENNY_STOCK 0.3, MUTUAL_FUND 0.08) | 8,827 of 14,914 closed (59.2%) |

The two surfaces use **different cost constants for the same class**. That is a fact, not a bug report:
`/audit` CRYPTO 15bp vs `/audit3` CRYPTO 9.96bp. Measured bridge below shows this difference is small
compared to the cohort difference, but it must be stated whenever a PF is quoted.

---

## 1 Win rate (WR)

- **Formula**: `wins / n`.
- **/audit3 win definition**: `net pnl_pct > 0 after per-class round-trip slippage`
  [SRC: `_raw/audit3_audit3_ledger.json:46`]. A trade that is gross-positive but smaller than cost is a loss here.
- **per_class_scrutiny win definition**: `pnl_pct > 0`, gross, no cost
  [SRC: `tools/per_class_scrutiny_engine.py:86`].
- **Consequence**: the same trade can be a win on one surface and a loss on the other. WR is
  therefore a **descriptor only** on `/audit3` [SRC: `_raw/audit3_audit3_ledger.json:47`], never a gate.
- **Measured**: CRYPTO WR is 39.39% on `/audit3` [SRC: `_raw/audit3_audit3_ledger.json:1561`] and
  46.66% gross in `trading_picks` (bridge output). A 7.3pp gap from cost definition alone.

## 2 Profit factor (PF)

- **Formula**: `gross_wins / |gross_losses|` where each term is summed over the trades in the cohort.
- **Basis label**: the ledger states `pf_basis: net` and `pf_cost_pct` per class
  [SRC: `_raw/audit3_audit3_ledger.json:1568`]. So its "PF" already has slippage subtracted per trade.
- **per_class_scrutiny**: `pf = gw/gl` on raw `pnl_pct` [SRC: `tools/per_class_scrutiny_engine.py:99`] — gross.
- **Threshold used for KILL**: `pf < 0.8` appears verbatim in the ledger's own reason string
  [SRC: `_raw/audit3_audit3_ledger.json:1607`].
- **Trap**: PF is scale-free and n-blind. PF 3.5 on 339 rows and PF 0.79 on 6,926 rows are not the
  same kind of claim, and PF alone cannot distinguish them. Always quote n and the CI with PF.

## 3 Expectancy

- **Gross expectancy** `gross_expectancy_pct`: mean `pnl_pct` with no cost.
- **Net expectancy** `net_expectancy_pct`: mean `pnl_pct` minus per-class cost.
- **Invariant that must hold**: `net == gross - cost`. The reconciliation tool checks it.
- **Measured CRYPTO**: gross −0.3189, cost 0.0994, net −0.4183 [SRC: `_raw/audit3_audit3_ledger.json:1571`].
  The invariant holds exactly. So on `/audit3`'s cohort the class is losing **before** cost.

## 4 Selection alpha (the decisive metric)

- **Formula**: `mean(pick net return) - mean(direction-adjusted buy-and-hold over the same holding window)`.
- **Why it matters**: it removes market beta. A class can be profitable only because the market rose.
  [SRC: `_raw/audit3_audit3_ledger.json:51`] states `PROVEN_T2 requires ... selection alpha CI lower bound > 0 (G8)`;
  a beta-only cell is demoted to CANDIDATE and flagged `beta_dominant`.
- **Measured overall**: n 3155, pick −0.447, hold −0.0774, **alpha −0.3696**, CI [−0.5673, −0.1674],
  alpha_wr 0.4444, hold_days_mean 4.79, alpha_per_day −2.8962, alpha_annualized −1057.11
  [SRC: `_raw/audit3_audit3_ledger.json:150`].
- **Coverage caveat (finding)**: per-class `alpha_n` is much smaller than class `n` for CRYPTO
  (1674 of 6926, 24.2%), FOREX (132 of 264, 50%), EQUITY (731 of 956, 76.5%), COMMODITY (40 of 50, 80%)
  [SRC: `reports/class_metric_reconciliation_20261122.md`]. Alpha is measured on a **subset**, and the
  subset is not the one the PF is computed on. Alpha is the gating metric, so this is the most
  important coverage gap in the whole system.
- **CRYPTO is flagged `beta_dominant: true`** [SRC: `_raw/audit3_audit3_ledger.json:1632`].

## 5 Sample adequacy

- `required_n` is the n at which the observed effect could be detected at the stated MDE.
- **Measured spread**: CRYPTO requires 917 and has 6,926 (adequate) [SRC: `_raw/audit3_audit3_ledger.json:1558`];
  EQUITY requires **22,569** and has 956 (3.9% of what is needed) [SRC: `_raw/audit3_audit3_ledger.json:1638`].
  So EQUITY's PF 1.0499 is the least-powered positive number on the page, despite being the only
  class with PF > 1 and a material n.
- `conventions.proven_min_n` is 100, `candidate_min_n` 30 [SRC: `_raw/audit3_audit3_ledger.json:9`].
  `required_n` is a stricter, effect-dependent value.

## 6 Verdict ladder (the only sanctioned labels)

- `/audit3`: `PROVEN_T2` (the only "proven"), `CANDIDATE`, `WEAK`, `KILL`, `INSUFFICIENT_N`, `NOT_SCORED`.
  Promotion rule verbatim [SRC: `_raw/audit3_audit3_ledger.json:50`].
- `/audit` `money_ready_verdict`: readiness states incl. `NOT_READY`, `INSUFFICIENT_DATA`,
  `policy_frozen` for operator-blocked classes [SRC: `alpha_engine/money_ready_verdict.py:255` region].
- `per_class_scrutiny`: `PASS_ALL_AXES`, `WATCHLIST`, `BORDERLINE`, `FAIL`, `INSUFFICIENT_N`
  [SRC: `tools/per_class_scrutiny_engine.py:174`].
- **These ladders are not comparable.** `PASS_ALL_AXES` is not `PROVEN_T2` and must never be quoted as one.
- **Measured**: `summary` reports `n_proven` 0, `n_candidate` 0, `n_proven_symbols` 0, `n_proven_classes` 0
  [SRC: `_raw/audit3_audit3_ledger.json:62`].

## 7 Cost stress (G9)

- **Rule**: the net CI lower bound at **2x** the class slippage must stay positive to reach
  `PROVEN_T2` or `CANDIDATE`; otherwise demote one tier [SRC: `_raw/audit3_audit3_ledger.json:52`].
- **Measured**: every class has `stress_2x_ok: false` [SRC: `_raw/audit3_audit3_ledger.json:1586`].
  This is why the one positive cell (`mega_mutation`) is capped at CANDIDATE.

## 8 Populations and why they disagree

- `/audit3` scores `dashboard_data.resolved_closed_picks_net`: **8,827 of 14,914** closed picks (59.2%),
  canonical sha `ed25b59c52a4` [SRC: `_raw/audit_data_denominator.json:39`].
- Exclusion reasons total 12,174 but `total - canonical` is 6,087. The publisher's own note
  [SRC: `_raw/audit_data_denominator.json:36`]: "the publisher and the tribunal exclude different
  cohorts, so these are separate pipelines, not one subtraction."
- The reason `invalid_row` accounts for 11,782 of the exclusion records
  [SRC: `_raw/audit_data_denominator.json:13`], but that figure is a SUM ACROSS TWO BLOCKS and must not be
  quoted as a row count. The same JSON lists it once per block: 5,891 in `resolved_closed_picks_net`
  [SRC: `_raw/audit_data_denominator.json` via `_raw/audit_data_dashboard_data.json` -> `resolved_closed_picks_net.counts.excluded_by_reason`]
  and 5,891 again in the coverage block [SRC: `_raw/audit3_audit3_ledger.json:97`]. Reading both blocks as one
  list double-counts it (5,891 x 2 = 11,782). The real figure is **5,891 of 6,087 excluded rows (96.8%)**.
  This is a defect in my own earlier reading, corrected here.
- **What `invalid_row` means** (`alpha_engine/resolved_closed_view.py:207-245`, `:309-311`): it is the
  catch-all label for a row that the coarse reason classifier could not name, i.e. the caller's stricter
  `validity` predicate rejected it. The predicate is `_is_valid_resolved_pick`
  [SRC: `audit_trail/dashboard_generator.py:4924`], with these rejection branches: paper_trade / expired_no_pnl /
  auto_expired; missing pnl; corrupt pnl vs prices (`_pnl_pct_looks_corrupt`); impossible non-crypto price move
  (>50%); entry-vs-exit price ratio >100x; placeholder exit price <= 0; historically blocked
  symbol/strategy; non-performance exit reason; STALE or INVALID_ENTRY; RESOLVE_FAILED fallback;
  non-performance terminal status; micro-hold under the minimum seconds; and no close marker with an
  unknown exit reason.
- So `invalid_row` is NOT one thing. It is "data-integrity rejection", and it is dominated by corrupt-price,
  placeholder-exit and micro-hold rows. Those are correctly excluded: counting them would inflate PF.
  The remaining open question is only the SPLIT between those branches, and `excluded_cohorts.summarize_excluded`
  [SRC: `audit_trail/excluded_cohorts.py:31`] is the existing tool that can produce it (n, WR, mean PnL,
  long/short, top symbols per reason) if the generator is wired to publish the dropped rows rather than just counts.
- The overall exclusion picture is documented by the ledger itself [SRC: `_raw/audit3_audit3_ledger.json:141`]:
  the dashboard reports 5,994 integrity-excluded and 9,277 auto-expired rows, the cohorts overlap, and they
  are reasons rows are missing rather than a partition.
- `per_class_scrutiny` reads `trading_picks` in MySQL directly, with its own filter
  `status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC') AND closed_at > '2026-01-01'`
  and a hard exclusion of the 2026-06-04 backfill (5,960 commodity rows)
  [SRC: `tools/per_class_scrutiny_engine.py:65`].
- So three populations exist: the DB table (52,608 closed rows), the scrutiny filter, and the
  canonical 8,827. **A PF is meaningless without naming which one it came from.**

## 9 Intrabar vs daily resolution

- `/audit` publishes both: `daily_pf` and `honest_pf` (intrabar first-touch) plus `pf_inflation_x`
  and `wr_inflation_pp` [SRC: `_raw/audit_data_money_ready_verdict.json:14`].
- **Measured CRYPTO**: daily_pf 0.2621, honest_pf 0.9169, pf_inflation_x 0.29, wr_inflation_pp 5.3,
  `flag: false`, and sizing uses `intrabar_truth` [SRC: `_raw/audit_data_money_ready_verdict.json:13`].
- The headline PF stays the daily number while sizing uses the honest one. Which is "the" PF is
  undefined on the page. Whenever BOND or COMMODITY is discussed, the intrabar inflation
  (BOND 92pp in the dossier) is the number that decides whether a WR is real.

---

## Provenance

- model: none (curator-written from the frozen evidence in `_raw/` and the cited source lines)
- ledger snapshot: `/audit3/audit3_ledger.json` `88606e1e…` generated 2026-11-22T06:35:41Z
- reconciliation output: `reports/class_metric_reconciliation_20261122.{json,md}`
  via `tools/reconcile_class_metrics.py --db`
- DB population measured 2026-11-22: `trading_picks` 52,608 closed rows, `mysql.50webs.com/ejaguiar1_stocks`

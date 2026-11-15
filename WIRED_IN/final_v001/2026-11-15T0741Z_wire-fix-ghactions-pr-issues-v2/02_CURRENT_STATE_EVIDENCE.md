# 02 — Current State: Evidence, Not Assertions

Sources: three independent audits of `WIRED_IN/`, `main` 48h changes, and the
forward/measurement stack; plus direct reads of `money_ready_verdict.json`,
`tools/forward_tracker.py`, `audit_dashboard/template.html` on `origin/main`.

## Live book reality (net, honest accounting)

From `2026-11-14/finpredict-v2_20261114-1602/raw/money_ready_verdict.json`:

| Class | n | WR | PF | Expectancy | State |
|-------|---|----|----|------------|-------|
| CRYPTO | 3,705 | 35.87% | **0.9196** | −0.059 | NOT_READY (pf/wr/dsr fail) |
| EQUITY | 250 | 59.2% | **0.9392** | neg | NOT_READY |
| ETF | 14–45 | 2.2–?% | **0.02–0.76** | neg | INSUFFICIENT_DATA |
| FOREX | 612 | 32.19% | **0.6596** | neg | NOT_READY (WF-OOS 0.48) |
| BOND | 1 | — | 0.0 | — | INSUFFICIENT_DATA |
| COMMODITY | 229 | 40.17% | 1.0256 | **−0.0017** | WATCH (negative expectancy despite PF>1) |
| FUTURES | 52 | — | 1.0936 | — | INSUFFICIENT_DATA |
| PENNY | 4 | 50% | 0.1779 | — | INSUFFICIENT_DATA |

**`money_ready` is empty for all classes.** Every PF < 1 except commodity, whose
PF>1 coexists with *negative expectancy* (a gate-logic incoherence to fix).

## Data-integrity pollution (must fix before any verdict)

- **#748** resolver predates `_priceless_close` → `exit_price = 0.0` flat closes
  in `recent_closed`. Corrupts every PF/WR.
- **Frozen-price artifacts:** the CRYPTO verdict's own "top sleeves" list shows
  `GainerPredictor1hStrategy` at **PF 120 / WR 97.96%** — impossible; it is a
  frozen/unchanged-price cohort, not a strategy.
- **22,947 ghost rows, 1,864 duplicate groups, 162 TIME_EXIT rows mislabeled
  TP_HIT**, stop-fill bug (`exit_price = entry_price`). These are documented in
  the audit sources; they poison live stats until re-derived from clean bars.

## Measurement apparatus — built, but not running

| Component | Status | Evidence |
|-----------|--------|----------|
| `tools/forward_tracker.py` (899 ln, costs + `_bench_excess`) | **on main, NOT wired** | zero references in `.github/workflows/`; selftest passes |
| `alpha_engine/data/forward_testing/forward_tracker.py` | not wired, **TypeError on mixed tz** at `:120-123` (`except ValueError` only) | reproduces `can't subtract offset-naive and offset-aware datetimes` |
| `build_benchmark_prices.py` | **absent on main** (PR #785 only) | `git cat-file -e origin/main:tools/build_benchmark_prices.py` → absent |
| `pick_excess.py` | **absent on main** (PR #785 only) | same; `EXCESS_RETURNS.md` link 404s |
| forward clock `build_forward_clock.py` + `forward_clock.js` / `excess_column.js` | **absent on main** (PR #785 only) | `audit_dashboard/template.html` on main has **0** references |
| `benchmark_prices.json`, `forward_clock.json`, `pick_excess_returns.json` | **absent on main** | git cat-file absent |
| `state/forward_test/plan.json` | present but only **2 strategies**; registered scouts never load | `load_plan()` returns verbatim |
| Ledger rows | **0** | `forward_clock.json` (branch): `ledger_rows: 0` |

**Production 404 trap:** the three FTP site functions in `audit-dashboard.yml`
(`:1167`, `:1303-1304`, `:1409-1410`) upload a hard-coded JS list that omits
`excess_column.js` and `forward_clock.js`; `deploy_audit_files.py` is also
unchanged. So even after merging #785, the new dashboard panel would 404.

## Best-evidenced candidates (still unproven)

| Candidate | Strongest number | Binding gap |
|-----------|------------------|-------------|
| **ETF H-103 dual momentum** | backtest PF **3.57**, Sharpe 1.62, WR 72.9%, MDD −12.4%, CAGR 29.1%, boot CI PF [1.64, 9.69], alpha t 2.36, cost-robust to 20 bps (PF 3.20) | **forward n_closed = 0 / 100**; only 48 monthly obs; 4 unscored month stamps (Aug missing) |
| **ETF TAA rotation** | Sharpe 0.88 vs SPY 0.74; MaxDD −19% vs −51% | **in-sample 2007–2026**, no forward; is risk-reduction/smart-beta, not alpha |
| **BTC SMA200 trend** | OOS wealth 1.94 vs 1.67, Sharpe 0.57 vs 0.46 | **asserted**; cited `experiments/crypto_sma200_oos_protocol.py` missing; 0/11 gates |
| **vwap-reversion-scout** (live prior) | +1.96pp excess, t_cluster 1.99, n=28 | below forward n; below Bonferroni bar (3.54) |
| **rs-breakout-scout** | +1.08pp excess, t 1.74 | below Bonferroni bar; not significant |

Cost-adjusted backtests (`sim_path_forward.py`, 2004–2026, 6/15 bps): **0 of 6
active rules beat matched exposure**; FABER10 −0.09%/yr (t −6.13), RSI2 −2.30%/yr
(−0.34%/yr at 2× costs, sign flips). BTC_TREND200/BTC_BH pass 4/5 but DSR
0.84/0.65 < 0.95 and OOS excess t = 0.74 — the "edge" is a cross-asset benchmark
artefact.

Retrospective per-pick excess (gross, `pick_excess_returns.json`, 2,997 scored):
EQUITY +0.238pp (t 0.97), ETF +0.023pp (t −0.62), **CRYPTO −0.795pp (t −3.65)**
— crypto is significantly *worse* than holding BTC.

## Contradictions that must be resolved (they undermine trust)

1. Dual momentum appears as PF **1.60 (n=104)**, PF **3.57 (n=48 months)**, and
   PF **1.021 (n=245)** in three folders — different windows, presented as one.
2. Gate count: 0/10 vs 0/11 vs 9+1 vs 10.
3. Hypothesis denominator: 0/23 vs 99 registered vs 10 inventory rows.
4. FOREX "DSR fail" vs `dsr_ok: true, dsr_score 0.9903` while PF 0.66.
5. ETF live PF: 0.476 vs 0.7598 vs 0.0216 (different cohorts, shown as interchangeable).
6. COMMODITY "WATCH" at PF 1.0256 with negative expectancy.

## Verdict

There is **no deployable edge today**. The honest product is a benchmark-tracking
passive book. The fastest credible route to a real edge is to **finish the
measurement loop** and run the one well-evidenced hypothesis (ETF H-103) to 100
forward trades — everything else is priors and assertion.

# /audit Deep Audit — Performance, Risk, Statistics, ML, Prediction Markets

- **Author:** kilo (worktree `auditpage-v3`), COMS seat `kilo-general`
- **Date:** 2026-11-16T20:03Z
- **Sources:** live https://findtorontoevents.ca/audit/ (fetched 19:40Z) + repo at `origin/main`
- **Data inspected:** `audit_dashboard/data/{intrabar_truth_by_class,money_ready_verdict,pf_registry,audit_surface_truth,strategy_ic_analysis}.json`, `alpha_engine/money_ready_verdict.py`, `alpha_engine/score_booster.py`, `alpha_dashboard/template.html`
- **Status:** findings + one shipped fix (see §7)

---

## 0. Verdict

**0 of 10 asset classes are money-ready.** The only "WATCH" is COMMODITY, and it flips to a 14% WR / PF 0.20 sleeve once policy-clean (n=14). Nothing here is sizeable. This is a research ledger.

The dashboard is unusually honest about this — but it publishes **three mutually incompatible performance ledgers at the same time**, one of which surfaces **fabricated-looking sleeves (91-0 records, PF 120)** as the "Top" candidate for a class. That is the material defect.

---

## 1. Finding 1 (HIGH): three contradictory per-class ledgers on one page

The same page quotes CRYPTO at three different profit factors, each from a different file:

| Class | intrabar_truth_by_class | money_ready_verdict | pf_registry policy_clean_net | Verdict |
|---|---|---|---|---|
| CRYPTO | 35.8% WR / PF **0.916** / n=3,716 | 35.76% / PF **0.916** / policy_clean_n=21,548 PF **0.260** | 41.70% / PF **0.257** / n=22,189 | FAIL, three stories |
| EQUITY | 59.2% / PF **0.939** / n=250 | 38.77% / PF 0.628 / n=472 | 38.77% / PF 0.628 / n=472 | FAIL, 20pp WR gap |
| FOREX | 32.2% / PF **0.660** / n=612 | 35.58% / PF 0.687 / n=429 | 35.58% / PF 0.687 / n=429 | FAIL |
| COMMODITY | 40.2% / PF **1.026** / n=229 | 14.29% / PF 0.198 / n=14 | 14.29% / PF 0.198 / n=14 | WATCH on headline, FAIL on policy-clean |
| ETF | 2.2% / PF **0.022** / n=45 | 68.42% / PF 1.788 / n=19 | 68.42% / PF 1.788 / n=19 | incoherent both ways |
| FUTURES | 42.3% / PF **1.094** / n=52 | 30.77% / PF 1.009 / n=13 | same | INSUFF-N |
| BOND | 7.7% / PF 0.391 / n=26 | 0% / PF 0 / n=1 | 0% / PF 0 / n=1 | no data |

Consequences:
- **COMMODITY's headline PF 1.03 is not a real edge.** The page's own "WATCH" label sits on n=14 at 14.3% WR / PF 0.198.
- **ETF is quoted as both PF 0.02 and PF 1.79** depending on which tile you read.
- A reader cannot tell which number is the sizing cohort. Every tile must print its ledger name + n (some do, most do not).
- The static prose is already stale in places (it still cites June sleeves and a "5/5 checks pass" footer while the same page says a non-zero ghost-row count fails the check).

**Recommendation:** pick ONE canonical ledger for sizing decisions (`pf_registry.by_asset_class_policy_clean_net`), label every surface with `{ledger, n}`, and delete or explicitly badge the discovery-only numbers.

---

## 2. Finding 2 (HIGH — fixed in this PR): artifact sleeves promoted to "Top"

`money_ready_verdict.json::classes.CRYPTO.top_sleeves` contained:

| Sleeve | n | WR | PF | Registry says |
|---|---|---|---|---|
| GainerPredictor1hStrategy | 49 | 97.96% | **120.0** | single-source, AVAXUSDT 48 wins / 0 losses |
| ADX Trend Confirmation | 213 | 97.18% | **56.7** | `is_single_source_artifact: true`, BTCUSDT **91 wins / 0 losses** |
| mega_mut_macd_rsi_m084 | 124 | 90.32% | 49.4 | single-source |
| CorrKamaAdaptiveStrategy | 142 | 95.77% | 37.3 | single-source |
| CorrVwapZscoreReversionStrategy | 184 | 95.65% | 36.2 | single-source |

A 91-0 record is not a strategy; it is a resolution artifact (TP-first labelling with the stop never evaluated in path order). All 34 registry strategies with n≥100 carry `is_single_source_artifact: true` from `file:mysql:at_pick_outcomes`, so the per-strategy leaderboard is one source deep.

The bug was in `alpha_engine/money_ready_verdict.py`: `_top_money_ready_sleeves()` set `policy_blocked: False` unconditionally, and both sleeve builders sorted purely by PF, so the PF-120 artifact ranked #1. The registry's own `display_tier: "discovery"` / `promotion_eligible: false` flags were ignored downstream.

**Fixed** — see §7.

---

## 3. Finding 3 (HIGH): statistical rigour is absent where it matters

Computed 95% Wilson intervals on the policy-clean cohorts:

| Class | n | WR | 95% CI | Conclusion |
|---|---|---|---|---|
| CRYPTO | 22,189 | 41.70% | [41.05, 42.35] | significantly below 50% (p≈0) |
| EQUITY | 472 | 38.77% | [34.48, 43.24] | significantly below 50% |
| FOREX | 429 | 35.58% | [31.28, 40.31] | significantly below 50% |
| ETF | 19 | 68.42% | [46.01, 84.64] | crosses 50% — no conclusion |
| COMMODITY | 14 | 14.29% | [4.01, 39.94] | crosses 50% — no conclusion |
| FUTURES | 13 | 30.77% | [12.68, 57.63] | crosses 50% — no conclusion |

Other rigor gaps:
- **CRYPTO expectancy bootstrap CI is [-0.0505%, -0.0448%]** — entirely negative. `money_ready_verdict.json` shows `mdd: 1.0009` (>100% drawdown, i.e. total loss of the compounding path) and `dsr_score: 0.0`. That is a catastrophic cohort, not a "near-miss".
- **EQUITY `mdd: 0.9999`** — same class of problem.
- **Walk-forward panel quotes Sharpe −65.6 (BOND, n=3) and +10.7 (FOREX, n=3).** Those are unit/scale bugs on n=3, not findings. Clamp/suppress when n<30 or σ<1e-6.
- **Multiple testing is uncorrected on the surfaces that matter.** There are 693 strategy rows in `by_asset_class_strategy_policy_clean_net`; only 34 have n≥100 and all 34 are single-source. With that search space, a handful of 90%+ WR cells is the expected null outcome, not evidence. The page correctly warns about post-hoc segment search elsewhere; the sleeve panel did not inherit that warning.
- **PF without CI above 1.0** is the project's own stated bar (MERCURYPROMPT.md). Most published PF point estimates have no CI attached.

---

## 4. Finding 4 (MED): ML is measurably anti-predictive, and the IC panel disagrees with the calibration panel

- `alpha_engine/score_booster._calibrate_confidence()` applies class-specific penalties (CRYPTO >0.85 → −12; EQUITY 0.85–0.90 → −15; FOREX ≥0.85 → −10) because high confidence *underperforms*.
- Live calibration panel: CRYPTO conf≥0.90 → 14.4% WR vs conf 0.50–0.60 → 60.3% WR. Verified direction in `score_booster.py` and by the audit's own DB probe.
- Yet the Decile Test panel reports **`confidence` Spearman ρ = +0.27 → "STRONG" predictor**, and `ml_score` ρ = +0.33. Those are computed over a 1,927-pick subset and are not reconciled with the inverted calibration above; one of the two must be measured on a different cohort.
- The ML Replacement Score, Source System Tier, R:R, Age, Leverage and Proven-Strategy components are all **zeroed as anti-predictive** (ρ −0.19 … −0.003) — good, but that means the "ML edge" is currently one feature (`ml_score`) over a shrinking denominator.
- `is_single_source_artifact` sleeves also pass into `top_sleeves` labelled `source: policy_clean` while `ml_enhanced_*` CRYPTO variants are skipped — the exclusion rules are inconsistent between the two builders.

**Recommendation:** state one calibration truth per class with its cohort; publish Brier score / reliability curve for `ml_score`; re-measure ρ on the same intrabar cohort the calibration uses.

---

## 5. Finding 5 (MED): prediction markets are priced off spot, not contract payoff

- `alpha_engine/polymarket_signals.py` and `kalshi_signals.py` map binary market odds onto spot symbols (KXBTCD→BTCUSDT etc.) and synthesize entry/TP/SL from live Binance/yfinance.
- A binary contract settles at 0 or 1. A spot-derived TP/SL therefore **cannot** reproduce the trade's actual PnL or fill distribution; the reported pnl_pct is a spot proxy for a contract bet.
- `prediction_market_consensus` is on the kill list (`config.py:294`) yet still registered as a verified-alpha PM source in the dashboard generator and still invoked by three overlapping workflows (`alpha-engine-live`, `prediction-market-agents`, `polymarket-signals`), all with `|| echo` soft-fail.
- There is no code constant enforcing the "prediction markets stay shadow (PBO 0.603)" decision; `SIZING_SCHEDULE["shadow"]=0.0` only applies if the row lands in the shadow tier.

**Recommendation:** compute PM PnL on contract price (or implied-probability delta), mark PM `SIZING=0` in code, and consolidate the four PM workflows into one loud-failing job.

---

## 6. Finding 6 (MED): risk management is structurally absent

- No position-sizing model is applied anywhere in the ledger: returns are per-trade `pnl_pct` summed to −1,319% (CRYPTO), while sizing/sizing-schedule code exists only as a gate, not a sizer.
- **FOREX geometry is inverted:** tight TP / wide SL — wins average 0.62% vs losses 1.00%. At 57.8% WR it is still net-negative (PF 0.85). Any emitter with symmetric ATR stops will stay negative permanently.
- **EQUITY shows why WR is not edge:** 59.2% WR with PF 0.94 — average loss exceeds average win.
- `cvar_95` exists in `money_ready_verdict.json` but is not surfaced as a headline metric; MDD is quoted as a percentage without the >100% cap being visible as "total loss".
- Concentration: MEMECOIN 74.5% single-day concentration; EQUITY 41.6%; COMMODITY 35.4%. Effective n is far below nominal n — the Wilson CIs above are therefore optimistic (they assume i.i.d.).

---

## 7. Fix shipped in this PR

`alpha_engine/money_ready_verdict.py`
- Added `_is_implausible(n, pf, wr)`:
  - `PF > 5.0 and n < 100` → implausible, or
  - `WR ≥ 95% and n < 1,000` → implausible.
- Both sleeve builders now emit `implausible_pf` and set `policy_blocked: True` for single-source registry artifacts **and** implausible sleeves; sorting is `(policy_blocked, implausible_pf, -pf)` so artifacts rank last instead of first.
- `_merge_top_sleeves()` carries the new sort key.

`audit_dashboard/template.html`
- The Money-Ready tile now renders "**No credible sleeve — top candidate flagged <reason>**" when every candidate is blocked, instead of headlining an artifact as "Top".

`tests/test_money_ready_verdict.py`
- +8 tests (`TestSleevePlausibilityGuard`): single-source block, implausible-PF block, high-WR block, realistic sleeve passes, merge ordering.

### Verification
- `python3 -m pytest tests/test_money_ready_verdict.py::TestSleevePlausibilityGuard -q` → **8 passed**
- Full file: **10 failed / 49 passed**; baseline on `origin/main`: **10 failed / 37 passed** → the same 10 pre-existing failures (all already listed in `.github/workflows/ci-tests.yml` known-drift deselects). **No regressions.**
- `py_compile` clean.
- Live-data run `python3 -m alpha_engine.money_ready_verdict --class CRYPTO --json` (exit 0): `GainerPredictor1hStrategy` (PF 120) no longer ranks first; every single-source sleeve now reports `policy_blocked: true`.

### Deployment
The hourly `audit-dashboard.yml` regenerates `money_ready_verdict.json` (step at line ~598) and deploys `template.html` → `index.html`, so the next cron run publishes both the data and the UI fix. No manual FTP step is required.

---

## 8. Remaining work (not in this PR)

1. **One ledger.** Choose `pf_registry.by_asset_class_policy_clean_net` as the sizing cohort; badge every other tile `DISCOVERY (n=…)`.
2. **Kill the intraday-artifact generator.** 91-0 / 48-0 symbol records should fail an upstream assertion (WR=100% with n≥50 and zero losses ⇒ quarantine), not merely be flagged downstream.
3. **Clamp walk-forward Sharpe** when n<30 or σ<1e-6; stop printing −65.6.
4. **Reconcile the IC panel with the calibration panel** (ρ +0.27 vs inverted bands) or drop one.
5. **PM PnL on contract payoff + hard `SIZING=0` pin**, and collapse the 4 PM workflows.
6. **FOREX geometry audit** — raise TP floor before any FOREX emitter is re-enabled.
7. **Effective-n reporting** — report n_eff after day/symbol clustering next to every WR/PF.

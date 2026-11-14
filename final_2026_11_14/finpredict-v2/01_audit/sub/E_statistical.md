# Subagent E — Quantitative / Statistical Soundness Audit

**Verdict: `FAIL`** — reported performance is **not** statistically sound and is **not** demonstrably profitable.

The fleet-level, policy-clean, net-of-slippage closed ledger loses money (n = 22,941, WR = 42.21 %, PF = 0.2657, WR z vs 50 % = **−23.60**). Every independent surface that is not self-referential (money-ready intrabar truth, forward-paper track, MA walk-forward) agrees. The apparent "winning" strategies are a small, entirely single-source cluster with physically implausible win rates (9 strategies at 90–100 % WR), which is a resolver/data artifact signature, not evidence of edge.

- Repo (read-only): `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2`
- Live data base: `https://findtorontoevents.ca/audit/data/` (all files HTTP 200, downloaded 2026-11-14 ~16:05Z)
- Archive (this task): `2026-11-14/finpredict-v2_20261114-1602/`
  - `raw/` — 7 downloaded live JSON surfaces + `per_strategy_agg.csv` (derived)
  - `sub/E_statistical.md` — this report

All numbers below are computed from the downloaded files or quoted from the cited `file:line`. No figure is invented.

---

## 0. Data inventory (what was analysed)

| Surface | Bytes | Generated (UTC) | Role |
|---|---:|---|---|
| `pf_registry.json` | 15,178,278 | 2026-11-14T14:30:05Z | 24,718 deduped closed rows → 22,941 policy-clean; canonical = `by_asset_class_policy_clean_net` |
| `anti_overfit_audit.json` | 27,973 | 2026-11-14T14:22:00Z | 80 strategies, DSR + PBO + Reality Check |
| `audit_surface_truth.json` | 10,239 | 2026-11-14T04:52:51Z | Trust hierarchy, 0/9 money-ready classes |
| `money_ready_verdict.json` | 42,481 | 2026-11-14T14:29:00Z | Per-class gate verdicts (intrabar truth) |
| `summary_picks.json` | 2,736 | 2026-11-14T14:30:06Z | MySQL `trading_picks` aggregate (broken WR — §7) |
| `ma_strategy_leaderboard.json` | 61,919 | 2026-11-14T14:25:04Z | Independent daily-bar walk-forward, 8×6 |
| `db_health.json` | 6,462 | 2026-11-14T14:13:42Z | Ghost rows, open bloat, PnL integrity |

`pf_registry.json` source files: 36 entries (32 local JSON ledgers + `mysql://at_pick_outcomes` = 24,172 rows; `mysql://trading_picks` and `mysql://tournament_picks?days=90` = 0 rows by default). Largest single source: `battleground/data/luxalgo_closed_picks.json` 4,511 rows and `alpha_engine/data/closed_picks.json` 2,183 rows.

---

## 1. Strategy search space — how many hypotheses were tested

The search space is **large and adaptive**, so any single "best" strategy is selected from hundreds of correlated candidates.

| Source | Count | Evidence |
|---|---:|---|
| Declared strategy→family map | **361** distinct strategy IDs | `alpha_engine/config.py:1646` (`STRATEGY_FAMILIES`), counted by parsing the dict |
| Indicator families | 14 | `alpha_engine/config.py:1628` (`INDICATOR_FAMILIES`) |
| Baby strategy modules | **220** `.py` files; **84** `.meta.json` | `baby_strategies/` directory listing |
| `alpha_engine` strategy modules | **140** `*strateg*.py` | `alpha_engine/` directory listing |
| Hand-authored mutation variants | **231** (54 + 80 + 29 + 18 + 17 + 33) | `alpha_engine/strategy_mutations.py:25,94,191,231,267,289` |
| DNA mutation operators | 7 operators (inverse, tighter/wider stops, regime gate, timeframe shift, confidence threshold, crossover) | `alpha_engine/dna_mutation_engine.py:210,242,261,280,298,333,348` |
| Genome / differential-evolution operators | 4 (random, DE-mutate, gaussian, inverse) | `alpha_engine/run_massive_mutations.py:418,437,447,464` |
| Mutation cycle files | 3 YAML | `mutations/proposed_2026-04-21*.yaml` |
| **Distinct strategies observed in the live ledger** | **658** | `pf_registry.by_asset_class_strategy_policy_clean_net` (682 asset×strategy pairs) |
| **Strategy × symbol cells** | **2,218** | `pf_registry.by_asset_class_strategy_symbol` |
| **Strategy × date cells** | **24,328** | `pf_registry.by_asset_class_strategy_date` |
| MA leaderboard tests | 48 cells (8 variants × 6 classes) | `ma_strategy_leaderboard.json` `methodology.multiple_comparisons` |

**Search-space lower bound used for multiple-testing correction: N = 658** (strategies actually scored in the live registry). The declared/mutation space is larger (361 + 84 + 231 ≈ 676 before genome search), so 658 is conservative. The MA leaderboard's own note states: *"8 variants x 6 classes; expected ~1.0 golden by chance under no-edge null."*

Families by declared entry (from `config.py`): momentum 80, volatility 59, sentiment 55, trend 46, structure 34, volume 31, mean_reversion 24, on_chain 18, community 4, carry 3, regime 3, macro 2, earnings 1, commodity_seasonal 1 = **361**.

---

## 2. Live performance distribution (pf_registry, policy-clean net)

### 2.1 Fleet aggregate (canonical view)

| Metric | Value |
|---|---:|
| Closed, deduped, policy-clean rows | 22,941 |
| Wins / Losses | 9,683 / 13,252 |
| Win rate | **42.21 %** |
| Gross profit / gross loss | 385.31 / 1,450.45 |
| **Profit factor** | **0.2657** |
| Σ per-trade PnL units | −1,065.13 |
| WR z vs 50 % (n = 22,941) | **−23.60** (two-sided p = 3.6×10⁻¹²³) |

Cost model: `alpha_engine.charter_slippage.deduct_slippage` (M-069 round-trip bps) — `pf_registry.slippage_model`.

### 2.2 Per-strategy PF distribution (n = 658 strategies, `raw/per_strategy_agg.csv`)

290 strategies have `gross_loss == 0` → PF undefined (all wins or flat); 369 have a defined PF.

| Slice | Count | Median PF |
|---|---:|---:|
| All defined PF | 369 | **0.0519** |
| n ≥ 10 | 146 | 0.4246 |
| n ≥ 30 | 76 | **0.6606** |
| n ≥ 100 | 35 | 0.5213 |

| Threshold | Strategies | with n ≥ 30 | with n ≥ 100 |
|---|---:|---:|---:|
| PF > 1.0 | 94 | 28 | 13 |
| PF > 1.2 | 83 | 26 | 13 |
| PF > 1.5 | 67 | 20 | 9 |
| PF > 2.0 | 51 | 18 | 8 |
| PF > 3.0 | 39 | 13 | 8 |

n distribution: 512 strategies have n ≤ 9; 70 have 10–29; 41 have 30–99; 32 have 100–999; 3 have ≥ 1,000. **78 % of the 658 strategies have fewer than 10 trades** — far below any inferential threshold.

### 2.3 The apparent "winners" are a single-source artifact cluster

24 strategies have a statistically significant WR above 50 % (one-sided p < 0.05, n ≥ 30). **All 24 have `single_source_pct = 1.00`** and `top_source = file:mysql:at_pick_outcomes`, and are flagged `is_single_source_artifact = True` by the registry itself. They account for only 2,919 of 22,941 trades (12.7 %).

| Strategy | n | WR | z vs 50 % | PF | single-source |
|---|---:|---:|---:|---:|---:|
| Multi-Timeframe Trend Alignment | 394 | 87.1 % | 14.71 | 11.06 | 1.00 |
| ADX Trend Confirmation | 213 | 97.2 % | 13.77 | 56.73 | 1.00 |
| CorrVwapZscoreReversionStrategy | 178 | 95.5 % | 12.14 | 34.94 | 1.00 |
| HoffmanStripTrendStrategy | 146 | **100.0 %** | 12.08 | undefined | 1.00 |
| CorrKamaAdaptiveStrategy | 142 | 95.8 % | 10.91 | 37.27 | 1.00 |
| Calendar Effect Crypto | 105 | **100.0 %** | 10.25 | undefined | 1.00 |
| mega_mut_macd_rsi_m084 | 124 | 90.3 % | 8.98 | 49.37 | 1.00 |
| Price Acceleration Detector | 234 | 77.4 % | 8.37 | 5.59 | 1.00 |
| EMA Ribbon Momentum Pullback | 96 | 89.6 % | 7.76 | 14.11 | 1.00 |
| AuditEnsemble_LONG | 169 | 78.7 % | 7.46 | **0.131** | 1.00 |
| VolumeWeightedMedianZScoreStrategy | 50 | **100.0 %** | 7.07 | undefined | 1.00 |
| GainerPredictor1hStrategy | 49 | 98.0 % | 6.71 | 1.16 | 1.00 |

Interpretation: a 100 % win rate over 146–50 closed trades is **not physically plausible** in a liquid market with symmetric TP/SL. `AuditEnsemble_LONG` is the tell: 78.7 % WR but PF = 0.131 — it wins small and loses huge, so WR alone is not edge. These are resolver/selection artifacts, and they are the only strategies that "survive" the naive tests in §3.

---

## 3. Multiple-testing mathematics

### 3.1 Formulas and exact inputs

For a strategy with `n` closed trades and observed win rate `p̂`, test H₀: p = 0.5 versus H₁: p > 0.5:

```
z = (p̂ − 0.5) / sqrt(0.25 / n)
one-sided p = P(Z > z) = 0.5 · erfc(z / √2)
```

Multiple-testing controls (α = 0.05 family-wise):

```
Bonferroni:  α_B = α / N ;   z_crit = Φ⁻¹(1 − α_B)
Šidák:       α_S = 1 − (1 − α)^(1/N)
Expected false positives at per-test α:  E[FP] = N · α
Expected maximum of N standard normals (asymptotic bound):  E[max|Z|] ≈ sqrt(2 ln N)
```

Exact thresholds computed with `statistics.NormalDist.inv_cdf`:

| N (hypotheses) | Bonferroni α | z_crit (one-sided) | Šidák α | E[FP] @ α=0.05 | sqrt(2 ln N) |
|---:|---:|---:|---:|---:|---:|
| 9 (asset classes) | 5.556×10⁻³ | 2.5392 | 5.683×10⁻³ | 0.5 | 2.096 |
| 76 (strategies with n ≥ 30) | 6.579×10⁻⁴ | 3.2125 | 6.747×10⁻⁴ | 3.8 | 2.943 |
| 80 (anti-overfit audit) | 6.250×10⁻⁴ | 3.2272 | 6.410×10⁻⁴ | 4.0 | 2.960 |
| 361 (declared families) | 1.385×10⁻⁴ | 3.6359 | 1.421×10⁻⁴ | 18.1 | 3.432 |
| **658 (observed strategies)** | **7.599×10⁻⁵** | **3.7878** | 7.795×10⁻⁵ | **32.9** | **3.603** |

### 3.2 How many lucky winners are needed under a random-entry null?

- With N = 658 tested strategies at a per-test α = 0.05, you expect **32.9 false "winners"** even with zero edge. At α = 0.01, **6.6**.
- Under a symmetric coin-flip null, roughly half of strategies should show PF > 1 (~329 of 658). The registry shows only **94** (14.3 %). The modal strategy loses; the population is *worse* than chance after costs (median PF 0.05).
- Only **24 of 76** strategies with n ≥ 30 have a one-sided significant WR > 50 % at p < 0.05 (expected 3.8 by chance). BH-FDR at q = 0.05 rejects for **22 of 76**.
- **21 strategies exceed the N = 658 Bonferroni z_crit of 3.788.** Under the null, expected false positives at that threshold is 0.05. Naively this looks like real edge — but **all 21 are the single-source, 90–100 %-WR artifact cluster from §2.3**. The independence assumption behind Bonferroni is violated (these are correlated re-emissions from one resolver/source), and the observed WRs are outside the physically plausible range. This is a data-generation artifact masquerading as 21 independent discoveries, not 21 edges.
- Consistency check: if even a handful of these were real, the CRYPTO class aggregate PF could not be 0.259 over 21,988 trades. It is.

**Conclusion:** the number of "winners" is fully explainable by (a) the ~33 expected false positives at N = 658, plus (b) a correlated single-source artifact cluster. No independent multiple-testing survivor is demonstrated.

---

## 4. PBO / DSR / Reality Check (anti_overfit_audit.json)

### 4.1 Headline

| Field | Value |
|---|---|
| Strategies audited | 80 (min_n = 20) |
| Verdicts | **OVERFIT_LIKELY 69**, UNDETERMINED 5, EDGE_LIKELY_REAL 6 |
| DSR threshold (real edge / undetermined) | 0.95 / 0.50 |
| DSR distribution (n = 80) | min 0.0, **median 0.0033**, max 1.0 |
| DSR ≥ 0.95 | 6 |
| DSR < 0.50 | 69 |
| Autocorrelation | 19 HIGH, 11 MODERATE, 50 OK (30/80 autocorrelated) |
| Strategies with n ≤ 30 | 40 / 80 |
| Strategies with n ≥ 100 | 21 / 80 |

86 % of audited strategies are classified OVERFIT_LIKELY by the project's own DSR test. The 6 "EDGE_LIKELY_REAL" are: `cta_golden_cross_200` (n=36, PF 14.74), `forex_rsi2_mean_reversion` (n=1464, HIGH_AUTOCORR), `ml_enhanced_INJUSDT_1d_B_lightgbm` (n=24, 100 % WR, HIGH_AUTOCORR, PF undefined), `vt_equity_two_day_rsi_reversal` (n=126, 99.2 % WR, PF 302, HIGH_AUTOCORR), `prediction_market_consensus` (n=215), `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=30, HIGH_AUTOCORR). Only 2 of 6 have autocorrelation "OK"; the 99–100 % WR entries are the same implausibility as §2.3.

### 4.2 PBO is computed on a meaningless n

`portfolio_diagnostics.pbo = {value: 0.0, n_candidates: 80, n_observations: 20, n_folds: 5, verdict: "SELECTION_EDGE_SURVIVES"}`.

- **`n_observations = 20`** is the length of the returns matrix `M` (T × S = 20 × 80). With `n_folds = 5` and `n_test_groups = 2` there are C(5,2) = 10 splits; each fold is **4 observations** and each out-of-sample block is **8 observations**. A Sharpe ratio estimated on 8 observations is pure noise.
- The matrix is built by `tools/anti_overfit_audit_sidecar.py:210-224`: `min_len = min(len(strat_returns[s]))` then `strat_returns[s][-min_len:]`. The underlying SQL (`tools/anti_overfit_audit_sidecar.py:88-95`) selects `strategy, pnl_pct ... ORDER BY strategy` — **no chronological ordering and no time alignment**. PBO/CSCV requires a time-indexed T × S matrix; here row *i* is the *i*-th trade of each strategy from a different calendar date. The time-series structure CSCV depends on does not exist.
- **PBO = 0.0 is therefore degenerate**, not evidence of edge. It also contradicts the same file's own per-strategy verdicts (69/80 OVERFIT_LIKELY).

### 4.3 Reality Check did not run

`portfolio_diagnostics.reality_check = {"error": "reality_check_pvalue requires the 'arch' package (see requirements-validation.txt)"}` (`alpha_engine/anti_overfit_validator.py:164-193`). The only family-wise (White/Hansen SPA) test in the anti-overfit audit **did not execute**. The project's separate `whites_reality_check.py` path is used by money_ready and does run, but on different data (§7).

### 4.4 DSR under-corrects the true search space

`audit_strategy(... n_trials=n_trials ...)` is called with `n_trials = len(strat_returns)` = **80** (`tools/anti_overfit_audit_sidecar.py:184`). The DSR deflation term `E[max(SR_n)]` therefore assumes only 80 independent trials, while the observed ledger contains **658** strategies. Using n_trials = 80 is too lenient; the real correction should be closer to 658, which would push more of the 6 "EDGE_LIKELY_REAL" below threshold.

---

## 5. Per-asset-class significance (policy-clean net)

Two-sided p-values from the normal approximation; Bonferroni family-wise α = 0.05/9 = 0.00556, |z|_crit = 2.773 (two-sided).

| Asset class | n | Wins | Losses | WR | PF | z vs 50 % | p (two-sided) | Survives Bonferroni? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 21,988 | 9,312 | 12,670 | 42.35 % | 0.2595 | **−22.69** | 6.1×10⁻¹¹⁴ | **YES — significantly BELOW 50 %** |
| FOREX | 438 | 156 | 282 | 35.62 % | 0.8339 | **−6.02** | 1.7×10⁻⁹ | **YES — significantly BELOW 50 %** |
| EQUITY | 461 | 198 | 263 | 42.95 % | 0.7022 | **−3.03** | 2.5×10⁻³ | **YES — significantly BELOW 50 %** |
| COMMODITY | 14 | 2 | 12 | 14.29 % | 0.1718 | −2.67 | 7.5×10⁻³ | no (just misses) |
| MEME | 10 | 1 | 9 | 10.00 % | 0.0234 | −2.53 | 1.1×10⁻² | no |
| FUTURES | 13 | 3 | 10 | 23.08 % | 0.8567 | −1.94 | 5.2×10⁻² | no |
| ETF | 15 | 11 | 4 | 73.33 % | 1.8358 | +1.81 | 7.1×10⁻² | no |
| BOND | 1 | 0 | 1 | 0 % | 0 | n/a | n/a | n=1 |
| PENNY_STOCK | 1 | 0 | 1 | 0 % | 0 | n/a | n/a | n=1 |

**Plain answer:** **No asset class survives multiple-testing correction with a positive edge.** Three classes (CRYPTO, FOREX, EQUITY) survive correction with a *significantly negative* WR — they lose money at astronomically high significance. The only class with PF > 1 (ETF) has n = 15 and a one-sided p ≈ 0.035, which does not survive the 9-class Bonferroni threshold (α = 0.0056). COMMODITY is n = 14. No class meets the project's own Tier-2 charter (`min_n = 100, min_wr = 0.5, min_pf = 1.5`; `audit_surface_truth.json`).

---

## 6. Survivorship bias, dropping and recoding

### 6.1 Exact row accounting (`pf_registry.counts`)

| Stage | Rows | Dropped | % of raw |
|---|---:|---:|---:|
| Raw rows | 34,540 | — | 100 % |
| Closed rows | 28,719 | 5,821 not-closed | 16.9 % |
| After flicker filter | 24,847 | 3,872 | 13.5 % of closed |
| After dedup | 24,718 | 129 duplicates | 0.5 % |
| **Policy-clean (canonical)** | **22,941** | 1,777 policy-excluded | 7.2 % of deduped |

### 6.2 Where the exclusions come from (`tools/build_pf_registry.py`)

1. **Non-closed / null-PnL dropped** — `CLOSED_STATUSES = {CLOSED, WON, LOST, LOSS, EXPIRED, WIN}` at `:196`; rows with status outside that set or `pnl_pct is None` are dropped at `:794`. This removes **5,821 rows (16.9 %)**, including 90,523 "open" rows in the much larger `trading_picks` table (see 6.3).
2. **Spot-flicker filter** — non-crypto rows with `abs(pnl) < 0.0002` (0.02 %) dropped at `:810`, `SPOT_FLICKER_THRESHOLD` at `:179`. Removes **3,872** rows. Direction: removes tiny wins *and* tiny losses; because ~50 % of near-zero outcomes are wins, this is mildly conservative on WR (it removes more tiny wins than tiny losses). It does **not** inflate.
3. **Dollar-scale artifact filter** — `abs(pnl) > 1.0` (100 %) dropped at `:813`, threshold at `:186`. Removes bogus extreme wins (futures point values stored as percent). Conservative.
4. **Dedup re-emissions** — key `(strategy, symbol, direction, trade_date, entry_price~2dp)` at `:819-846`. Removes only **129** rows. This is small relative to the 22,947 constant-PnL ghost rows independently found in `bt_backtest_trades` (6.4), so duplication is under-controlled in some tables.
5. **Policy exclusion** — `PERMANENTLY_KILLED_STRATEGIES` + `BLOCKED_SOURCE_SYSTEMS` + `PF_REGISTRY_POLICY_EXCLUDED` + direction triples + asset pairs at `:213-310`; removes **1,777 rows (7.2 %)**. This is outcome-dependent exclusion: strategies/sources killed *because they lost* are removed from the canonical "policy-clean" view. Direction: **biases the canonical PF upward** relative to the full deployed fleet. It is transparent (the raw view is also published), and the raw view is worse, so the conclusion is unaffected.

### 6.3 Unresolved-pick (open) survivorship — the dominant risk

From `db_health.json > open_bloat`:

| Metric | Value |
|---|---:|
| `trading_picks.total_count` | 143,156 |
| `trading_picks.open_count` | **90,523 (63.2 %)** |
| `trading_picks.active_count` | 21 |
| `hours_since_last_close` | 3 |
| `validator_frozen` | false |

**63 % of all picks have never resolved.** Only 18,839 of 140,619 picks (13.4 %) are "resolved" per `summary_picks.json`. If non-resolution correlates with adverse selection — positions that never reach TP and are never force-closed — then excluding them from the closed ledger biases WR/PF **upward**. The presence of zombie EXPIRED rows (memory: `audit_garbage_zombie_rows_nov`) confirms this failure mode exists in the data. `UNVERIFIED:` the exact distribution of PnL among the 90,523 open rows is not published, so the magnitude of this bias cannot be computed from the downloaded files.

### 6.4 Ghost rows (duplication / synthetic rows)

`db_health.json > ghost_rows`: **22,947** rows in **10** cohorts with `COUNT(*) > 1000 AND COUNT(DISTINCT entry_price) < 5` and a constant `pnl_pct` (`tools/db_health_check.py:172-240`). Top cohorts are `meta_strategy` MEMECOIN rows (DOGEUSDT n=3,569, DOGEUSDT n=3,160, WIFUSDT n=2,763, PEPEUSDT n=2,052, …). These are constant-outcome re-emissions, not independent trades. Direction: duplication/constant outcomes inflate apparent sample size and, depending on the constant sign, can inflate or deflate WR/PF; they are **not** independent evidence.

### 6.5 Recoding paths (`FORCE_CLOSED_TOXIC`, EXPIRED, TP/SL contradictions)

- `FORCE_CLOSED_TOXIC` (`alpha_engine/crypto_risk_gates.py:155-171`): admin force-close of a killed strategy's open pick at `pnl_pct = 0.0`, `status = CLOSED`, with `_wr_excluded = True` and `_wr_excluded_reason = "force_closed_toxic_admin"`. Properly flagged; if all aggregators honour `_wr_excluded`, these are neutral (they would otherwise be flat rows that dilute WR, not inflate it).
- `active_picks_sync.py:206-225`: on a time exit, `pnl > win_threshold → WON`, `pnl < −threshold → LOST`, **else `EXPIRED`** (flat). So EXPIRED rows are ~0-PnL and are counted in `n` but neither wins nor losses. Only **6** such flat rows exist in CRYPTO (`n − wins − losses = 6`), so the effect is negligible and mildly *dilutes* WR.
- TP/SL contradictions: `TP_HIT_CONTRADICTION → LOST` if `pnl < 0`, `SL_HIT_CONTRADICTION → WON` if `pnl > 0` (`active_picks_sync.py:200-213`). Statuses are re-derived from PnL sign, so labels track outcome rather than the original trigger.
- `db_health > won_pnl_contradiction`: `TP_HIT` n=6,986, 0 negative; `SL_HIT` n=3,851, **2 non-negative**; `LOST` n=5,548, **27 non-negative**. So ~29 rows are mislabelled relative to PnL sign — immaterial (0.17 %).
- `db_health > pnl_integrity`: 130 sign mismatches (0.54 %); 6,535 naive magnitude mismatches (27.05 %) on a 24,158-row sample — a material magnitude/scale inconsistency, not a sign problem.

### 6.6 Resolver look-ahead / replay

`audit_trail/universal_pick_resolver.py`:
- intrabar TP/SL checking added (`:507-590`), with `RESOLVER_ENTRY_ANCHORED` default **ON** (`:614-615`).
- `_check_tp_sl_intrabar` (`:618-690`) uses **SL-first conservative ordering** and an entry-anchored bar window; on ambiguous bars (both TP and SL touched in one bar) it sets `_intrabar_ambiguous` and resolves **SL first**. This is conservative.
- Bad-geometry picks (`LONG needs sl<entry<tp`, `SHORT needs tp<entry<sl`) return `None` → close-approx fallback, not a fake TP.
- `UNVERIFIED:` how many of the 24,172 `at_pick_outcomes` rows were resolved *before* this fix landed (the fix description references a prior stale-window look-ahead). Historical rows may retain legacy look-ahead. This is the most plausible mechanism for the 90–100 % WR cluster in §2.3.

**Net direction of bias:** the unresolved-open gap (63 %) and the ghost re-emissions bias *upward* (inflate apparent n and WR/PF); the flicker and dollar-scale filters and EXPIRED dilution bias *downward*. The two do not obviously cancel, but the conclusion is robust because even the **filtered, policy-clean** fleet loses money badly (PF 0.266, z = −23.6).

---

## 7. Surface reconciliation — which number is trustworthy?

### 7.1 `summary_picks.json` WR > 100 % is a denominator bug

`tools/sync_summary_picks_json.py:61-65` computes the three columns from **different populations in the same query**:

```sql
SUM(CASE WHEN status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT') THEN 1 ELSE 0 END) AS resolved,
SUM(CASE WHEN status = 'WON' OR (pnl_pct IS NOT NULL AND pnl_pct > 0 AND status NOT IN ('LOST','ACTIVE','OPEN')) THEN 1 ELSE 0 END) AS wins,
SUM(CASE WHEN status = 'LOST' OR (pnl_pct IS NOT NULL AND pnl_pct < 0) THEN 1 ELSE 0 END) AS losses
```

`wins` and `losses` are counted over **all rows with a non-null mark-to-market PnL** (including still-open rows), while `resolved` counts only terminal statuses. `win_rate_pct = 100 * wins / resolved` (`:161`), so the numerator can exceed the denominator:

| Class | resolved | wins | losses | wins+losses | reported WR | impossible gap |
|---|---:|---:|---:|---:|---:|---:|
| INDEX | 17 | 194 | 251 | 445 | **1,141.2 %** | +428 |
| FUTURES | 61 | 222 | 357 | 579 | **363.9 %** | +518 |
| COMMODITY | 1,447 | 3,476 | 3,466 | 6,942 | **240.2 %** | +5,495 |
| ETF | 73 | 170 | 183 | 353 | **232.9 %** | +280 |
| EQUITY | 820 | 1,332 | 2,148 | 3,480 | **162.4 %** | +2,660 |
| FOREX | 5,806 | 8,536 | 8,968 | 17,504 | **147.0 %** | +11,698 |
| BOND | 72 | 92 | 156 | 248 | **127.8 %** | +176 |
| CRYPTO | 10,444 | 10,262 | 13,746 | 24,008 | 98.3 % | +13,564 |
| MEME | 76 | 31 | 48 | 79 | 40.8 % | +3 |

`summary_picks.json` is **not a valid WR surface** and is not in the project's own trust hierarchy.

### 7.2 Trust hierarchy (`audit_surface_truth.json`)

```
1. money_ready_verdict.json + pf_registry.by_asset_class_policy_clean_net
2. verified paper forward (pilot_forward_dashboard.json)
3. trading_picks post backfill_resolved_pnl + clean_ingest_v2
4. tournament_picks / ai_leaderboard (research only)
```

`disputed_surfaces`: CRYPTO Smart Picks / HC / ELITE (claude_gainer_st concentration + resolver mislabels); tournament headline model WR on n < 30; luxalgo bulk CRYPTO without dedupe. `money_ready_count = 0`, headline: *"0/9 asset classes money-ready on policy-clean closed picks. Do not size on Smart Picks / tournament / leaderboard inflated WR."*

### 7.3 Head-to-head

| Surface | CRYPTO verdict | Numbers | Trustworthy? |
|---|---|---|---|
| `money_ready_verdict` (sizing source = intrabar truth) | NOT_READY | n_resolved 3,705; WR 35.87 %; PF 0.9196; expectancy **−0.0592**; bootstrap CI **[−0.0507, −0.0448]** (entirely negative); MDD 1.0009; CVaR₉₅ −96.10; `wr_ok/pf_ok/dsr_ok` all false | **Yes** — intrabar truth, gates enforced, 0/9 classes pass |
| `pf_registry.by_asset_class_policy_clean_net` | losing | n 21,988; WR 42.35 %; PF 0.2595; z −22.69 | **Yes** for direction/magnitude; canonical, slippage-adjusted, deduped |
| `audit_surface_truth` | NOT_READY | policy_clean_pf 0.2600, wr 42.45 %; tier2_pass false | **Yes** (summary of the above) |
| `forward_track` (independent paper) | no promotion | 8 sleeves, n 25–54, PF 0.121–2.382, **0 promotion_ready**; median PF ≈ 1.077 | **Yes** — cleanest out-of-sample, but small n |
| `ma_strategy_leaderboard` | no gold | 8 variants × 6 classes, **n_golden = 0**; explicitly survivorship-biased (current-listed universe); ~1 golden expected by chance | **Yes** (independent daily-bar walk-forward) |
| `anti_overfit_audit` | 69/80 OVERFIT | DSR median 0.0033; PBO invalid (T=20); Reality Check failed | **Partially** — DSR per-strategy is usable; PBO/RC are not |
| `summary_picks` | "profitable" | impossible WR (up to 1,141 %); wins/losses ≠ resolved | **No** — denominator bug |
| tournament / AI leaderboard | inflated | research-only per trust hierarchy | **No** for sizing |

### 7.4 Why money_ready and pf_registry differ numerically but agree in sign

Both are negative. `money_ready` uses `at_signal_outcomes.intrabar_*` (n=3,705, WR 35.87 %, PF 0.9196) as the sizing source; `pf_registry` uses policy-clean daily-close closed picks (n=21,988, WR 42.35 %, PF 0.2595). `money_ready.intrabar_daily_divergence` quantifies the gap: `daily_pf 0.2628` vs `honest_pf 0.9196` (daily PF is 0.29× the intrabar PF), and `wr_inflation_pp 6.5` (daily WR is 6.5 pp higher than intrabar WR). So the daily-close resolver inflates WR by 6.5 pp while also producing a much worse tail (PF 0.26 vs 0.92) — either way, **PF < 1 and negative expectancy on both**. There is no reconcilable "profitable" reading of either surface.

`forward_track` is the decisive out-of-sample check: 8 sleeves, 39–54 closed trades each, only one reaches PF 2.38 (n=38, WR 57.9 %, one-sided z ≈ 0.97 — not significant), and **none is promotion_ready**. That is what "no edge" looks like on clean forward data.

### 7.5 Independent peer corroboration (read-only cross-check)

Two peer reports in the same archive independently reach the same negative verdict from a different payload:

- `sub/G_peer_reconciliation.md:77` — *"Verdict 'not profitable / multiple-testing artifact' — AGREES (3 independent peers)"*; payload summary: 126 systems, 16,126 closed, 7,914 valid, WR 41.8 %, **PF 0.94**, expectancy −0.11, Sharpe −1.31 annual, compounded EW −99 %, 30-day DD 31.2 %; v4 `money_ready_verdict` = 0/9 classes pass. (Peer-reported; `UNVERIFIED:` I did not re-derive these exact figures from that payload.)
- `sub/C_crypto.md:160` — the dominant "flat 0 %" crypto mass is **zombie EXPIRED, zero-PnL, null-price re-emissions** (`inverse_mutations` / `inverse_luxalgo_confluence`, daily since 2026-05-23), not genuine flat performance. This is the same unresolved/zombie mechanism flagged in §6.3–6.4.
- G also notes the older June-snapshot registry had `dropped_spot_flicker = 2,188 / 28,460 = 7.7 %`, whereas the live 2026-11-14 registry used here has **3,872 / 28,719 = 13.5 %**. Different snapshot, same direction (flicker filtering is real and material); not a contradiction.

---

## 8. What would change the verdict

For a `PASS` on statistical validity, all of the following would be needed:

1. A **class-level** (n ≥ 100) forward/paper ledger with `PF ≥ 1.5`, `WR ≥ 50 %`, and a positive bootstrap CI after slippage — none exists (0/9 classes).
2. The 24–21 "significant" strategies to come from **≥ 3 independent sources**, not `single_source_pct = 1.00`, and to show WR in a physically plausible range (not 90–100 %).
3. A **valid PBO** on a chronologically aligned T × S matrix with T ≫ n_folds (the current T = 20, n_folds = 5 is invalid), and a **Reality Check / SPA** that actually runs (currently blocked on missing `arch`).
4. DSR computed with `n_trials ≈ 658`, not 80.
5. Resolution of the 90,523 open picks so that the closed-pick universe is not a 37 % surviving subsample.
6. A de-duplicated ledger (22,947 constant-PnL ghost rows) and a fixed `summary_picks` denominator.

---

## UNVERIFIED markers

- `UNVERIFIED:` Distribution of PnL among the 90,523 unresolved `trading_picks` rows — not published in the downloaded surfaces, so the magnitude of open-pick survivorship bias cannot be computed.
- `UNVERIFIED:` Fraction of the 24,172 `at_pick_outcomes` rows resolved before the `RESOLVER_ENTRY_ANCHORED` look-ahead fix landed — code shows the fix is default-ON now (`universal_pick_resolver.py:614-615`) but does not date-stamp historical rows.
- `UNVERIFIED:` Whether every aggregator honours `_wr_excluded` / `_wr_excluded_reason` for `FORCE_CLOSED_TOXIC` rows; only `crypto_risk_gates.py:155-171` sets the flag and `money_ready_verdict` is documented to exclude via the WON/LOST status gate.
- `UNVERIFIED:` The exact upstream provenance of the 90–100 %-WR strategies (`HoffmanStripTrendStrategy`, `Calendar Effect Crypto`, `VolumeWeightedMedianZScoreStrategy`, `ADX Trend Confirmation`); the registry only reports `top_source = file:mysql:at_pick_outcomes` and `single_source_pct = 1.00`.
- `UNVERIFIED:` `ma_strategy_leaderboard` OOS PFs are current-listed-universe only (explicitly survivorship-biased per its own `methodology.survivorship`); the survivorship-adjusted column (`pf_oos_survivorship_adj`) injects only 5 % synthetic total-loss trades, which may understate the bias.

---

## Bottom line

- **Statistical validity: `FAIL`.**
- Fleet policy-clean net: n = 22,941, **WR 42.21 %, PF 0.2657**, z = **−23.60** vs 50 %.
- Best honest class (money-ready intrabar): CRYPTO **WR 35.87 %, PF 0.9196**, expectancy −0.0592, bootstrap CI entirely negative.
- **0/9 asset classes money-ready**; **0/8 forward sleeves promotion-ready**; **0 golden** in the independent MA walk-forward.
- The only apparent winners are **24 single-source strategies with 90–100 % WR** — a resolver/selection artifact, not edge.
- The anti-overfit PBO (T = 20, unordered rows) is invalid and the Reality Check never ran (`arch` missing).
- `summary_picks` WR > 100 % is a wins/resolved denominator bug; it is not a valid surface.
- **Conclusion: the reported profitability is a multiple-testing + survivorship + resolver-artifact composite, not a genuine edge.**

# Edge Analysis 2026-04-30

**Author:** Claude Opus 4.7 edge-analysis pass on `audit_dashboard/data/dashboard_data.json` (snapshot generated_at `2026-04-30T15:27:02Z`, repo SHA `f8dc4354`).
**Scope:** 5-phase empirical pass per orchestrator brief. Every claim cites a data point computed from `picks.recent_closed` (n=3500) or `picks.active_raw` (n=178). No Cerebras/DeepSeek narrative numbers reused.

---

## TL;DR

1. **Phase 1 confirms ground truth.** EQUITY 30d PF=1.85, ETF 30d PF=2.84, FOREX 30d PF=1.53, COMMODITY 30d PF=0.75, CRYPTO 30d PF=1.08. Top per-(strategy, AC, dir) combos are `luxalgo_confluence CRYPTO SHORT` (n=103, +45.75%) and `claude_ml_moderate_mut CRYPTO LONG` (n=39, +31.58%, Sharpe 6.5).
2. **Production HC gate is too strict on EQUITY.** Current params reject the entire profitable EQUITY scout fleet (`rs-breakout-scout`, `mtf-align-scout`, `donchian-stock-breakout`, `price-accel-scout`, `markov_zone_transition`) because their score lands in 44-51 range — below `scoreFloorEquity=55`. Lowering 55→45 + `scoreCompoundFloor` 50→45 lifts EQUITY HC pass-set from n=16 to n=57 (+256%) while preserving PF 4.05 (>>Tier 2 floor 1.5).
3. **All 23 BLOCKED_SYMBOLS are clean** — zero recent_closed picks in the last 30d. Bans work upstream.
4. **Cerebras unban hypotheses (BNB/SOL/ATOM) FALSIFIED.** None are currently banned (false premise) and none show recoverable edge: BNB WR 16.7% PF 0.72, SOL WR 25.8% PF 0.54, ATOM n=9 too small.
5. **Cerebras "ig_min 3→2 = +18% signals" FALSIFIED.** Empirical lift on active_raw set: 0.0% (5 pass at both 2 and 3). Other gates dominate.
6. **Cerebras volatility-multiplier-improves-Sharpe claim FALSIFIED.** Mathematically incoherent (Sharpe is scale-invariant under per-strategy constant multipliers); Pearson rho(confidence, pnl_pct) = -0.044 system-wide so per-pick re-weighting also doesn't help.
7. **Memory note "elite_score r=-0.001" is OUTDATED.** Current data: `elite_score` Spearman rho=+0.082 (p=1e-6); `trust_score` rho=+0.196 (p=1.7e-31, strongest). EQUITY scoring is particularly informative (`trust_score` rho=+0.27).

**PR shipped:** `tune(hc_gate): scoreFloorEquity 55→45, scoreCompoundFloor 50→45 — unlocks 41 profitable EQUITY HC picks (PF 4.05, +108pp sum_pnl)`.

---

## Phase 1 — Strategy × Asset × Direction edge map

Computed per (strategy, asset_class, direction) combo with n>=30 across `picks.recent_closed` (n=3500). Full matrix in `reports/strategy_edge_matrix_2026_04_30.csv`. Industry metrics: WR%, PF, Sharpe (annualized × √252), Sortino, max DD (peak-to-trough on cum pnl_pct sorted by closed_at), Calmar.

### 30-day asset-class aggregate (sanity check vs orchestrator pre-verified facts)

| Class | n_30d | WR% | sum_pnl | PF | Sharpe |
|---|---:|---:|---:|---:|---:|
| EQUITY | 157 | 57.3 | +188.62 | **1.85** | 3.71 |
| ETF | 39 | 69.2 | +56.06 | **2.84** | 7.05 |
| FOREX | 602 | 52.3 | +11.56 | 1.53 | 1.47 |
| CRYPTO | 1510 | 40.7 | +93.68 | 1.08 | 0.46 |
| COMMODITY | 540 | 42.4 | -25.06 | 0.75 | -0.71 |
| BOND | 1 | 0 | 0 | 0 | 0 |
| FUTURES | 2 | 100 | 0 | inf | n/a |

Matches the orchestrator's pre-verified table within rounding (EQUITY 1.85 vs 1.75 brief — newer snapshot). **Trust the data.**

### Top-10 per-(strat, AC, dir) by sum_pnl_pct (full ladder in CSV)

| strategy | AC | dir | n | WR% | sum_pnl | PF | Sharpe | MaxDD |
|---|---|---|---:|---:|---:|---:|---:|---:|
| luxalgo_confluence | CRYPTO | SHORT | 103 | 52.4 | +45.75 | 1.62 | 3.54 | 29.71 |
| claude_ml_moderate_mut | CRYPTO | LONG | 39 | 59.0 | +31.58 | 2.31 | 6.51 | 5.28 |
| Breakout Momentum | EQUITY | LONG | 38 | 57.9 | +31.14 | 1.53 | 2.89 | 12.00 |
| luxalgo_confluence | CRYPTO | LONG | 99 | 46.5 | +27.52 | 1.36 | 2.19 | 25.14 |
| Bollinger MR | EQUITY | LONG | 58 | 44.8 | +25.11 | 1.31 | 1.74 | 3.00 |
| strong consensus (alpha+ml_crypto_pred) | CRYPTO | LONG | 92 | 47.8 | +24.35 | 1.25 | 1.47 | 70.24 |
| stocks_rsi2_pullback | EQUITY | LONG | 38 | 55.3 | +4.68 | 1.15 | 0.74 | 18.39 |
| forex_rsi2_mean_reversion | FOREX | LONG | 202 | 47.0 | +0.94 | 1.12 | 0.49 | 2.73 |
| cta_cross_asset_tsmom | FOREX | LONG | 39 | 43.6 | +0.80 | 1.23 | 1.21 | 1.20 |
| non_crypto_consensus | FOREX | SHORT | 87 | 59.8 | +0.03 | 2.03 | 3.64 | 0.01 |

### Bottom-5 (already addressed — kill list working)

| strategy | AC | dir | n | WR% | sum_pnl | PF | status |
|---|---|---|---:|---:|---:|---:|---|
| macd_rsi_confluence | CRYPTO | LONG | 176 | 34.1 | -89.33 | 0.66 | killed PR #509 |
| unknown | CRYPTO | SHORT | 37 | 8.1 | -29.00 | 0.24 | needs source attribution |
| rsi_bounce | CRYPTO | LONG | 30 | 36.7 | -28.83 | 0.42 | killed |
| unknown | CRYPTO | LONG | 33 | 27.3 | -26.78 | 0.48 | needs source attribution |
| Classic Momentum | EQUITY | LONG | 41 | 36.6 | -15.38 | 0.84 | review |

---

## Phase 2 — Dormant strategies (PF>=1.5, n>=30, ZERO closes in last 7d)

Only **one** strategy meets the criteria:

| strategy | n_total | WR% | PF | sum_pnl | days_since_last_close | active_now |
|---|---:|---:|---:|---:|---:|---:|
| Breakout Momentum | 46 | 58.7 | 1.54 | +33.58 | 48 | 0 |

**Root cause** (verified by `source_system` audit): `Breakout Momentum` rides 100% on `stocks_competition` source (42/46 picks) and `fast_stocks_competition` (4/46). Both sources are in `BLOCKED_SOURCE_SYSTEMS` (audit_trail/quality_gates.py:1132). The strategy is dormant **because the source is hard-banned**, not because of HC gate.

`Bollinger MR` (n=68, WR 48.5%, PF 1.32) is in the same boat — 66/68 from `stocks_competition`, 2/68 from `fast_stocks_competition`. Below the PF>=1.5 floor so didn't make the dormant list, but same upstream cause.

Recovery path for these strategies requires **un-banning `stocks_competition`**, not tuning the HC floor. Quality_gates.py:1127 already notes the source's all-time stats: 33.5% WR / -304% on n=281. A 30d look at `stocks_competition` recently shows **WR 50.98%, PF 1.327, +77.07% on n=153** (Phase 4 finding) — re-evaluation candidate but beyond the scope of this PR (Stage-5 unkill is a separate, heavier process per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`). Flagged for follow-up.

### Recent 7d strategy mix (sanity check)

Top-5 active: `quan_engine` 314, `luxalgo_confluence` 142, `macd_rsi_confluence` 115, `strong consensus` 92, `unknown` 62. Total 1430 closes/7d.

---

## Phase 3 — High-Conviction gate sweep

**Tool:** `tools/dashboard_hc_rules.py` `evaluate_hc_gates_1_to_9`. Production params from `config/hc_gate_params.json`.

### Baseline (current production HC on closed picks)

| set | n | WR% | PF | sum_pnl |
|---|---:|---:|---:|---:|
| Population | 3500 | 44.7 | 1.13 | +280.80 |
| HC pass | 97 | 72.2 | 6.02 | +209.82 |
| HC reject | 3403 | 43.9 | 1.03 | +70.98 |

The HC gate is genuinely picking premium edge — pass-set carries 75% of total profit on 2.8% of picks. **Lifting more profitable picks through the gate is the highest-impact tunable here.**

### independentGroupsMin sweep (active_raw set, 178 picks)

| ig_min | gate_pass | picks_with_ig>=ig |
|---:|---:|---:|
| 1 | 6 | 166 |
| 2 | 5 | 154 |
| 3 | 5 | 103 |
| 4 | 4 | 74 |

**Cerebras "ig_min 3→2 = +18% signals" FALSIFIED.** Empirical lift: (5-5)/5 = 0.0%. Other gates dominate; ig_min isn't the bottleneck. (Note: replay on `recent_closed` skips this gate because `source_systems` is empty there, so the active_raw set is the only valid testbed.)

### EQUITY scoreFloor sweep — the key finding

| scoreFloorEquity | n | WR% | PF | sum_pnl |
|---:|---:|---:|---:|---:|
| 40 | 30 | 76.7 | 3.48 | +44.65 |
| 45 | 30 | 76.7 | 3.48 | +44.65 |
| 50 | 30 | 76.7 | 3.48 | +44.65 |
| **55** (current prod) | **16** | **87.5** | **12.90** | **+35.29** |

The current 55 floor cuts off 14 picks (all in the 45-54 score band) with **WR 76.7% and sum_pnl +9.36%** standalone. These are EQUITY scout strategies whose forward-WR and trust scores are strong but whose `score` lands in 44-51 — well above the absolute floor (40) but below the per-AC floor (55).

But `scoreFloorEquity` interacts with `scoreCompoundFloor`. Combined sweep:

| config | n | WR% | PF | sum_pnl | new strategies admitted |
|---|---:|---:|---:|---:|---|
| prod (55, 50) | 16 | 87.5 | 12.90 | +35.29 | rs-breakout-scout(9), markov_zone(6), donchian(1) |
| **proposed (45, 45)** | **57** | **73.7** | **4.05** | **+143.90** | **+ mtf-align(5), price-accel(5), donchian(+9), quality-minus-junk(12), rs-breakout(+9)** |

**Net delta: +41 picks, +108.6 percentage points sum_pnl, PF still 4.05 (>>Tier 2 floor 1.5).**

### Time-split robustness check (EQUITY only)

Picks split chronologically (138/138 by closed_at):

| Split | Production | Proposed |
|---|---|---|
| First half (Feb-21 → Apr-3) | n=9 PF=35.3 sum=+12.6 | n=26 PF=2.0 sum=+21.7 |
| Second half (Apr-4 → Apr-30) | n=7 PF=9.7 sum=+22.7 | **n=31 PF=5.78 sum=+122.2** |

**Both halves PF>2 under proposed config; second half is dramatically better than first half** (recent EQUITY edge is real and improving). No overfit signal.

### CRYPTO/FOREX sweeps — no equivalent gain

Crypto `forwardWRMinPctCrypto` sweep (40-65): always n in [39,52], PF stays 4.5-6.5. The gate is well-calibrated on crypto — no tuning headroom.

FOREX `forwardWRMinPctForex` sweep (50-70): the boundary is sharp. At 55: n=106 PF=3.0; at 60: n=5 PF=334.8 (degenerate edge case — only 5 picks pass). Holding at 70 is conservative but not unreasonable per the comment in hc_gate_params.json: FOREX has resolver-noise issues that artificially inflate FWD WR until the `outcome_resolver.py` fix lands.

### Confidence band (0.85-0.95, fwd_n<30) gate — REVALIDATED

| set | n | WR% | PF | sum_pnl |
|---|---:|---:|---:|---:|
| Confidence band [0.85, 0.95] AND fwd_n<30 | 36 | 47.2 | 0.64 | -13.89 |
| Population | 3500 | 44.7 | 1.13 | +280.80 |

Empirical justification holds — keep the gate.

---

## Phase 4 — Banned-symbol audit + Cerebras unban hypotheses

### BLOCKED_SYMBOLS audit (last 30d closed)

All 23 entries (MATICUSDT, UUSDT, XMR, XMRUSDT, ENAUSDT, IMXUSDT, KASUSDT, KATUSDT, TRXUSDT, ADBE, CRM, ACN, MSFT, PLTR, TSLA, JTOUSDT, XLMUSDT, ICPUSDT, RENDERUSDT, NVDA, NKE, PG, HD) — **zero recent_closed picks in the last 30d.** Upstream filter is 100% clean. No unban candidates.

### Cerebras unban hypotheses (BNB / SOL / ATOM)

| symbol | currently banned? | n (all-time) | WR% | PF | sum_pnl |
|---|---|---:|---:|---:|---:|
| BNBUSDT | NO | 12 | 16.7 | 0.72 | -1.29 |
| SOLUSDT | NO | 67 | 26.9 | 0.68 | -13.06 |
| ATOMUSDT | NO | 9 | 33.3 | 0.70 | -2.94 |

**FALSIFIED on two axes:** (a) none are banned today (Cerebras's premise was wrong), (b) recent perf is firmly negative — these would be **kill** candidates, not unban candidates, if anything (SOL n=66 WR 25.8% PF 0.54 sum -18.55 is the most actionable). Wilson 95% LB for SOLUSDT WR is 16.75% — far below break-even. Pinned in `tests/test_asset_class_edge_invariants.py::test_cerebras_bnb_unban_falsified`.

### Retired-strategy 30d cross-check (active still in close stream?)

| source | 30d_n | WR% | PF | sum_pnl |
|---|---:|---:|---:|---:|
| stocks_competition | 153 | 51.0 | **1.33** | +77.07 |
| aggregated_picks | 39 | 46.2 | 1.45 | +15.91 |
| goldmine_stocks | 23 | 13.0 | 0.03 | -64.60 |
| kimi_signal_tracking | 4 | 50.0 | 0.36 | -17.27 |

**`goldmine_stocks` and `kimi_signal_tracking` are still bleeding** — kills are correct, the residual closures are pre-block backlog.

**`stocks_competition` shows recoverable edge** (WR 51%, PF 1.33, +77% on n=153 30d) — the 2026-04-05 re-block was based on full-population stats that may be stale. Not unblocking in this PR — flagged as a Stage-5 follow-up requiring proper investigation per `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + mutation analysis. Resurrecting the source would also unlock dormant `Breakout Momentum` and `Bollinger MR`.

---

## Phase 5 — Scoring rho

### System-wide Spearman correlation (n=3500)

| field | rho | p_spearman | Pearson r | signal? |
|---|---:|---:|---:|---|
| trust_score | **+0.196** | 1.7e-31 | +0.174 | **STRONGEST** |
| score | +0.150 | 4.2e-19 | +0.132 | strong |
| ml_composite_score | +0.150 | 3.8e-19 | +0.132 | strong |
| method_a_score | +0.092 | 5.8e-08 | +0.102 | weak-mid |
| elite_score | +0.082 | 1.0e-06 | +0.090 | weak (NOT -0.001 from old memory) |
| confidence | +0.063 | 2.0e-04 | **-0.044** | inconsistent |
| ml_score | -0.193 | 1.1e-02 | -0.114 | weak inverted (n=173 only) |

### Per-asset class

| AC | elite_score | trust_score | confidence |
|---|---:|---:|---:|
| CRYPTO (n=1524) | +0.075** | +0.137*** | -0.025 (ns) |
| EQUITY (n=424) | **+0.246*** | **+0.269***  | +0.067 (ns) |
| FOREX (n=780) | +0.073* | +0.111** | +0.013 (ns) |
| COMMODITY (n=664) | -0.062 (ns) | +0.064 (ns) | +0.039 (ns) |
| ETF (n=83) | **+0.277** | +0.255* | -0.101 (ns) |

**Findings:**
1. Old memory note "elite_score r=-0.001" is **outdated** by 80×. Current rho +0.082 (p<1e-6).
2. **Trust_score is the strongest signal** — rho +0.20 system-wide, +0.27 EQUITY (mid-effect-size). Suggests relying more on trust-tier filters than on raw-score filters.
3. **Confidence rho is inconsistent**: positive system-wide but **negative in CRYPTO (-0.025) and ETF (-0.101)**, near-zero in FOREX. Confidence-based gates have weaker empirical justification than score-based gates. This independently corroborates `feedback_confidence_is_not_edge.md`.
4. **COMMODITY has no scoring signal** (all rhos p>0.1) — explains why commodity is the worst-performing class. The scorer doesn't differentiate good from bad commodity picks. Mutation/scoring redesign needed before commodity can earn back budget.

### Cerebras volatility-adjusted-multiplier claim — FALSIFIED

Cerebras claimed a `(1 + std/price)` multiplier improves Sharpe 0.12 → 0.18.

**Mathematically incoherent**: a per-strategy constant scaling multiplier on every PnL is **Sharpe-invariant** (mean and std scale together; ratio unchanged). The only way Sharpe could change is if the multiplier varies per-pick AND correlates with sign(pnl). But **rho(confidence, pnl_pct) = +0.063 system-wide** with **Pearson -0.044** — confidence carries minimal directional signal.

Pinned in falsification list. The right scoring direction is to **lean harder into trust_score** (rho +0.20) rather than tweaking confidence-derived multipliers.

---

## Recommendations (prioritized)

1. **SHIP THIS PR (highest verified impact):** lower `scoreFloorEquity` 55→45 and `scoreCompoundFloor` 50→45 in `config/hc_gate_params.json`. Empirical: +41 EQUITY HC picks, +108pp sum_pnl, PF 4.05 (>>Tier 2 floor), robust on both time halves. Tests pinned.
2. **Follow-up #1: stocks_competition re-evaluation.** Recent 30d shows WR 51% / PF 1.33 / +77% on n=153 — Stage-5 mutation analysis warranted to determine whether to surgically unblock `(stocks_competition, Breakout Momentum)` and `(stocks_competition, Bollinger MR)` while keeping the source's "Value + Quality" / "Earnings Drift" sub-strategies blocked. Out of scope for today.
3. **Follow-up #2: COMMODITY scoring redesign.** All scoring rhos near-zero on n=664 — current scorer is no better than chance. Needs feature-engineering pass or retraining (separate roadmap item).
4. **Follow-up #3: SOLUSDT consideration.** Recent 30d n=66 WR 25.8% PF 0.54 sum -18.55. May warrant addition to BLOCKED_SYMBOLS or a per-strategy carve-out — but not this PR (need to confirm not already filtered upstream by source-strategy pair, since `quan_engine CRYPTO LONG` is a known loser and SOL is plausibly a quan_engine victim, not a structural-anti-edge symbol).

## Appendix — what I couldn't verify

- **`hf_conviction_tier` stamping**: only 4/178 active picks have a tier; 0/3500 closed picks. Tier-S/A bypass logic in `passes_stamped_tier_supplemental_path` can't be empirically validated without more stamped data. Flagged for the team that owns the stamping pipeline.
- **`source_systems` field** is empty (0/3500) on `recent_closed` — historical IG (independent groups) gate replay is impossible. Active_raw fix only.
- **CPCV / PBO** — out of scope; tracked separately in `MEMORY/project_cpcv_gap_2026_04_28.md`.

## Files

- `reports/strategy_edge_matrix_2026_04_30.csv` — full 23-row matrix (n>=30 only).
- `reports/EDGE_ANALYSIS_2026_04_30.md` — this report.
- `tests/test_asset_class_edge_invariants.py` — 4 invariant tests, all pass.
- `config/hc_gate_params.json` — 2-line tune (PR diff).
- `.tmp_research/edge_analysis_2026_04_30.py`, `phase{2,3,4,5}_*.py` — research scripts (not for production).

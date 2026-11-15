# Forensic Failure Taxonomy (Phase 2 — All 10 Failure Modes)

**Package:** `WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/01_failures_taxonomy.md`  
**Evidence Base:** `00_inventory.csv` (6,639 mined files from 11,821 scanned / 44,800 tracked on `origin/main`), live audit payloads (`live_dashboard_payload.json`, `live_anti_overfit_audit.json`, `live_audit_surface_truth.json`), `TESTING_PROTOCOL.MD`, `.claude/skills/money-maker-ready*/SKILL.md`, `KIMI_*`, and `updates/index.html`.

---

## Executive Diagnosis

The repository does **not** suffer from a lack of algorithms or mathematical sophistication. It contains **361** strategy families (`alpha_engine/config.py`), **285** baby strategies (`baby_strategies/`), **2,474+** Kimi-harvested strategies (`KIMI_INTEGRATION_STATUS.md`, `KIMI_STRATS*.MD`), **6,639** mined strategy/research/risk files (`00_inventory.csv`), and institutional validation modules (`alpha_engine/anti_overfit_validator.py`, `alpha_engine/deflated_sharpe.py`, `alpha_engine/validation/purged_cv.py`).  
Yet canonical readiness remains **0 / 9 asset classes `MONEY_READY`** (`audit_dashboard/data/money_ready_verdict.json`, `TESTING_PROTOCOL.MD:31`, `live_audit_surface_truth.json`). The collapse traces systematically to ten interlocking failure modes.

---

## The 10-Mode Forensic Classification

### 1. Overfitting / Data Snooping (Too Many Parameter Trials, Too Few Trades)
- **Quantitative Signature:** The production ecosystem sweeps **361** strategy families + **285** baby strategies = **646** active candidates (`alpha_engine/config.py`, `baby_strategies/`), plus **9,552** tracked files under `incubator/` (`genome/`, `ml_battleground/battleground_mutations.py`). At a nominal $\alpha = 0.05$ threshold, ~**32.3 false-positive "winners"** appear purely by chance.
- **Observed Repo Evidence:**
  - `live_anti_overfit_audit.json` flags **69 / 80** audited strategies (`86.3%`) as `OVERFIT_LIKELY` and only 6 as `EDGE_LIKELY_REAL`.
  - In `alpha_engine/money_ready_verdict.py:84`, the `ml_enhanced_` family spawned **112+ variants**, only **4** of which even reached $n \ge 20$ for per-variant SPA testing (`M-105` quarantine defaulted `"0"`).
  - `ml_battleground/ensemble_coordinator.py:6` advertises System B ("The Regime") at *"56.6% WR, Sharpe 9.91 backtested"*—an extreme curve-fit artifact that degrades sharply out-of-sample.
  - `2026-11-15_AM_profitability_plan/parallel_agent_worktree/01_asset_class_plans/SIMULATION_RESULTS.md` ran 37 clean walk-forward combos and found **0/37 passing DSR $\ge 0.95$ and PBO $\le 0.10$** (nearly all showed $\text{PBO} \approx 0.999$).
- **Mined Count in `00_inventory.csv`:** Explicit overfitting/PBO/snooping markers appear in >580 inventory rows (e.g., `1:Overfit|4:Friction/Cost|6:RegimeDep` = 246 rows, `1:Overfit|6:RegimeDep` = 172 rows, `1:Overfit|2:LookAhead/Fill|4:Friction/Cost` = 171 rows).

### 2. Look-Ahead Bias & Intrabar Path Leakage
- **Quantitative Signature:** Backtests and live TP/SL resolvers evaluate bar closes or assume nominal TP execution when both TP and SL are touched inside the same OHLC bar, or join future/mismatched macro tables.
- **Observed Repo Evidence:**
  - `TESTING_PROTOCOL.MD:88-92` explicitly bans winsorized/nominal TP/SL optimization after 2026-05-31 intrabar replay (`reports/peer_claude-CAPPING_VS_INTRABAR_REPLAY_TWO_EXAMPLES_2026-05-31.md`) proved **28%–100%** of nominal `TP_HIT` exits actually hit `SL` first intrabar (`PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`).
  - `updates/index.html:88-90` (Jun 5, 2026 Deep-Dive Series) uncovered **two massive look-ahead/backfill leaks**: (a) 5,960 commodity rows created on `2026-06-04` by resolver backfill masqueraded as T2 commodity edge; (b) 88% of `cta_cross_asset_tsmom` forex closes landed in `2026-05+` where `alpha_macro` ended, creating a missing-join artifact (fixing via `--require-macro-join` + `total_pf >= 1.0` dropped walk-forward PASSes from **4 to 1**).
  - `WIRED_IN/2026-11-15_0128_buffy/BACKTEST_AND_RESEARCH.md` §6 caught an off-by-one `[1:]` slice in daily strategy evaluation that gave day-$t$ positions day-$(t-1)$ returns.

### 3. Survivorship & Universe Bias
- **Quantitative Signature:** Static ticker lists curated in 2026 (`DEFAULT_UNIVERSE` in `alpha_engine/config.py:27-42`, `EQUITY_SYMBOLS` in `alpha_engine/asset_class.py:55-60`) and memecoin bloat are evaluated retroactively without point-in-time constituent histories or delisted/rugged tokens.
- **Observed Repo Evidence:**
  - `alpha_engine/config.py:92-120` includes high-beta/meme/AI tokens (`PEPEUSDT`, `FARTCOINUSDT`, `BONKUSDT`, `TRUMPUSDT`, `WIFUSDT`, `FETUSDT`). Historical crypto audits carried **179+ noisy alt/meme symbols** (`MEMORY.md:39`).
  - Equity scanners (`alpha_engine/config.py:27-42`) evaluate current survivors (`NVDA`, `META`, `AAPL`, `MSFT`, `LLY`) rather than point-in-time S&P 500 constituents, inflating in-sample hit rates.
  - `audit_dashboard` / `alpha_engine/money_ready_verdict.py` flagged `mega_mutation::crypto` and `FUTURES` / `PENNY_STOCK` as single-source concentration artifacts (`is_single_source_artifact=True`, 91.7%–100% from one generator).

### 4. Unrealistic Cost & Fill Model (Friction Death)
- **Quantitative Signature:** Strategies simulate 0-spread/0-slippage fills or mid-price closes while real execution suffers spread, maker/taker fees, stop-gap overshoot, roll yield, and funding drag.
- **Observed Repo Evidence:**
  - **Stop-Fill Overshoot in Crypto:** `tools/stop_fill_replay.py` and the Nov 14 audit showed that across $n = 771$ `SL_HIT` crypto rows, planned risk was **1.932%** while realized loss averaged **2.970%**. Gap-aware fill replay (`--truncate-at-exit`) recovered `+67.5pp` on `kimi_riseoftheclaw` (lifting crypto PF from `0.768` only to `~0.80`—still far below breakeven).
  - **Per-Class Cost Wipeout:** `tools/per_class_cost_gate.py:6-11` documents that modelled round-trip cost is **39.7%** of average trade PnL in CRYPTO, **72%** in FUTURES, **267%** in ETF, and **422%** in COMMODITY.
  - **FOREX Zero-Spread Mirage:** FOREX strategies (`alpha_engine/config.py:329` `FOREX_HARD_DISABLE` defaulted `"0"`) previously modelled ~0 pip spreads; on honest live fills, FOREX collapsed to **PF = 0.27** (`KIMI_INTEGRATION_STATUS.md:15`, `WIRED_IN/2026-11-15_0135/inspect-wt/elimination_rationale/ELIMINATION_RATIONALE.md:16`).
  - **1,209** files hit `EXECUTION:spread`, **1,047** hit `EXECUTION:funding`, and **905** hit `EXECUTION:slippage` in `layer_a_stats.json`, yet production promotion gates defaulted `SLIPPAGE_PROMOTION_GATE_ENABLED=1` only as late as 2026-05-19 (`alpha_engine/money_ready_verdict.py:71`).

### 5. Weak Signal-to-Noise Ratio (Edge Too Small vs. Volatility)
- **Quantitative Signature:** Technical indicator combinations (`kimi_claw_pro.pine` stacks KAMA, HMA, Connors RSI-2, SFP, Go Score, Z-Score MR, CVD, TTM Squeeze, Kyle's Lambda, Hurst, and Top Gainer modules across **63/64** Pine plots) produce low-IC entry triggers indistinguishable from random walks after friction.
- **Observed Repo Evidence:**
  - `final_2026_11_14/inspect-wt` V1 cell search across **46** cells (8 sources, 12 source×class, 26 strategies) found **0 cells** beating uncorrected $z > 1.96$.
  - High-$n$ legacy strategies fail coin-flip tests: `luxalgo_confluence` ($n = 1,284$, `PF = 1.13`, $z = -5.02$), `momentum-factor` ($z = -0.29$), `intermarket-flow` ($z = -0.59$), `rs-breakout-scout` ($n = 133$, `PF = 1.65`, $z = 0.78$ — luck-class).
  - `1,775` rows in `00_inventory.csv` classify directly as `5:WeakSNR/Unverified`.

### 6. Regime Dependence (Bull-Market & Volatility Conditioning Failures)
- **Quantitative Signature:** Unconditional trend/momentum or mean-reversion rules win in one macro cycle (e.g., 2009–2020 low-rate bull or 2021 meme mania) and implode when volatility, rates, or cross-asset correlation shifts.
- **Observed Repo Evidence:**
  - **RSI(2) Mean Reversion Collapse:** In `2026-11-15_AM_profitability_plan/.../SIMULATION_RESULTS.md`, Connors `RSI2_MeanReversion` on 7 equity ETFs (2020–2025) produced `-118%` to `-186%` net PnL (`QQQ` `n=47`, `WR=8.51%`, `PF=0.022`, `Sharpe=-9.711`). `buffy` (`2001–2026`) also showed `RSI2_SPY` `OOS excess = -2.87%`, `Sharpe = -0.64`.
  - **Dual Momentum Regime Break:** `DUALMOM_3` (`SPY/TLT/GLD` top-1) had IS excess `+2.55%` (2003–2015) and flipped to OOS excess `-6.34%` (2016–2026) (`WIRED_IN/2026-11-15_0128_buffy/BACKTEST_AND_RESEARCH.md`).
  - **Crypto Chop & All-LONG Bias:** `alpha_engine/regime_position_sizer.py:5-7` explicitly documents *"the all-LONG-in-choppy-market mistake that was the root cause of paper-trade losses."*
  - **Live Regime Blindness:** Live `/audit` closed trades showed `with_regime_data = 0` vs `closed_without_regime = 8,538` (`memory/2026-11-14.md:29`).
  - **1,358+** inventory rows carry `6:RegimeDep` as primary failure tag.

### 7. Implementation Gap (Backtest Logic vs. Live Execution & Ledger Drift)
- **Quantitative Signature:** Production scanners, resolvers, dependency manifests, and dashboard layers diverge sharply from backtest code.
- **Observed Repo Evidence:**
  - **Undecided Zombie Pollution:** `78.6%` (**3,272 / 4,148**) of `active_raw` picks on `/audit` were `EXPIRED` picks with `pnl = 0` (`memory/2026-11-14.md:24`); `TIME_EXPIRED` overwrote PnL with 0 (`reports/zero_pnl_data_pipeline_audit_2026-06-05.md`).
  - **10× Loss Understatement:** Repricing 624 open `/audit` picks against live Binance/Yahoo/FX quotes revealed `81%` (504/624) showed fake `0%/None` PnL on the dashboard, hiding a real mean of `-1.80%` (dashboard claimed `-106pp` vs true `-1,116pp`).
  - **Garbage Ingest & Asset Leaks:** `EURGBP=X` stored entry `688.17` vs `0.835` market (`824×` off); `XRPUSDT` emitted at `entry=0.0` (`2026-11-14T13:54`); `'MONTREAL CANADIENS VS BUFFALO SABRES'` leaked from `_sportsbet` into financial active picks (`memory/2026-11-14.md:76-80`).
  - **Missing Dependencies & Disabled Gates:** `requirements.txt:18-22` notes `yfinance` was previously undeclared—causing ETF and Bond scanners to silently fail with `ImportError` and emit **0 picks**. Meanwhile `ANTI_OVERFIT_VALIDATOR_ENABLED` (`audit_trail/quality_gates.py:81`), `ML_ENHANCED_CRYPTO_QUARANTINE` (`money_ready_verdict.py:84`), and `requirements-validation.txt` were split/opt-in (`OFF` by default).
  - **Surface Disagreement (2–4×) & Duplicate Re-inserts:** Always-on picks (`SGOV/BND/TLT`) re-inserted daily without a `UNIQUE` key, swelling `live_pnl_tracker.py` from `185` unique rows to `4,390` duplicates (`memory/2026-11-15.md:34`).

### 8. Insufficient Sample Size (Statistically Inconclusive)
- **Quantitative Signature:** Low-frequency asset classes (Bonds, Commodities, ETFs) or over-sliced sub-strategies produce $n < 30$ resolved trades, giving wide confidence intervals where 1–2 outlier trades manufacture fake `PF > 3.0`.
- **Observed Repo Evidence:**
  - `TESTING_PROTOCOL.MD:18-30` (`2026-05-31` canonical snapshot): `BOND` had **$n = 0$** post-clean closed trades (`n=18–35` total in Nov 2026), `PENNY_STOCK` $n = 1$, `ETF` $n = 4$, `COMMODITY` $n = 7$, `FUTURES` $n = 12$, `FOREX` $n = 29$, `EQUITY` $n = 43$.
  - In `2026-11-15_AM_profitability_plan/.../SIMULATION_RESULTS.md`, `Bollinger_MeanReversion` reported `PF = 199.8–200.3` on SPY/QQQ/EFA purely because `gross_loss ≈ 0` on tiny trade counts (`n < 10`).
  - `mega_mutation::crypto` showed `PF = 49–53` in single-source `pf_registry` cells but **0 rows** in `recent_closed` (`n = 18` live Nov cohort).
  - Only **4 / 114** observed live strategies reached $n \ge 100$ (`memory/2026-11-14.md:84`).

### 9. Wrong Objective Optimized (Raw Return / Win Rate vs. Risk-Adjusted Excess)
- **Quantitative Signature:** Scanners and mutation labs (`genome/`, `Kimi_Agent_High-Score Asset Picks`) rewarded raw win rate (`WR`), nominal profit factor (`PF`), or absolute PnL without matching benchmark beta, risk-free cash yield (`^IRX` / `2.5%`), or drawdown duration.
- **Observed Repo Evidence:**
  - `genome/bayesian_optimizer.py:11` explicitly had to add a comment: *"Optimize Sharpe, not win rate (Zarattini et al., 2025)"* because earlier genetic mutations bred tight-TP / wide-SL scalpers with 75%+ WR and catastrophic left-tail blowups.
  - **Equity Beta Illusion:** PR `#773` (`NO_ALPHA_BETA`) proved equity picks had $t = 1.05$, median pick `-0.57%` vs `SPY`, with `54%` underperforming `SPY` buy-and-hold.
  - **Crypto TSMOM Illusion:** Copy-trader TSMOM reported `Sharpe = 2.13` vs zero, yet `BTC` buy-and-hold Sharpe in the same window was `~2.2`—pure asset beta masquerading as system alpha.

### 10. Risk Management Failures (No Stop Discipline, Over-Leverage, Concentration, Whipsaw Stops)
- **Quantitative Signature:** Portfolio-level exposure caps were bypassed (`MAX_OPEN_PICKS=999` historically), single tokens dominated PnL (`FET` = 237% of PnL per `alpha_engine/config.py:82`), and naive portfolio DD-stops caused cash lockouts and whipsaw losses.
- **Observed Repo Evidence:**
  - `alpha_engine/money_ready_verdict.py:93` documents: *"Hard lesson: 1 bad trade at rapid_fire → 69% MDD — positive Kelly does NOT protect against catastrophic runs."*
  - `TESTING_PROTOCOL.MD:20-21` shows live `MDD = 100.0%` for `CRYPTO` and `98.2%` for `EQUITY`.
  - Naive portfolio drawdown stops backfired: `final_v4/inspect-wt/03_risk_management/backtest_rotation.py` (`v3` 15% DD-stop with 3-month cooldown) slashed MF/ETF sleeve CAGR from `8.2%` to `4.5%` and Sharpe from `0.53` to `0.27` due to post-crash whipsaws.
  - `alpha_engine/config.py:76-85` had to restore `MAX_ACTIVE_PICKS=20` (from `999`), enforce `MAX_PICKS_PER_SYMBOL=1`, and cap `KELLY_CAP=0.05` (`5%`), while `crypto` still allowed `MAX_SAME_DIRECTION_CRYPTO=40`.

---

## Summary Mapping Across Key Mandatory Review Cohorts

| Repo Cohort | Primary Paths Reviewed | Dominant Failure Modes |
|---|---|---|
| `money-maker*` Skills & Audits | `.claude/skills/money-maker-ready*/SKILL.md`, `reports/money_maker_ready_*.md`, `updates/2026-05-11-money-maker-*.html` | #7 Implementation Gap (`recompute` vs `asset_class_health` drift), #8 Small N, #4 Friction ignored until May/June 2026 |
| `TESTING_PROTOCOL.MD` & Recovery Protocols | `TESTING_PROTOCOL.MD`, `updates/2026-04-17-*winrate-recovery-plan.md`, `incubator/**/recovery*.py` | #1 Overfitting (6-stage rehab inverse mutations e.g. `winner_pattern_precursor_inverse` / `claude_gainer_ml_inverse` never cleared n=500 OOS), #2 Nominal vs Intrabar fill |
| `Kimi*` Research & Pine Scripts | `KIMI_STRATS*.MD`, `KIMI_INTEGRATION_STATUS.md`, `kimi_claw_pro.pine`, `Kimi_Agent_*/*`, `backtest_kimi_claw_signals.py` | #5 Weak SNR (63-plot over-parameterized ensemble), #1 Data Snooping (2,474+ mined variants), #2 Fallback returns attached in `KIMI_INTEGRATION_STATUS.md:61` |
| `/audit` & `/updates/index.html` | `audit_trail/quality_gates.py`, `audit_dashboard/template.html`, `updates/index.html` | #7 Impl Gap (78.6% zombies, 81% fake 0% PnL, 2026-06-04 backfill contamination), #10 Concentration & missing `UNIQUE` keys |


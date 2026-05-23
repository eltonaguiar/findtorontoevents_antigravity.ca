# Rescue edge creative synthesis (2026-05-19)

Generated: 2026-05-19T22:22:04.358916+00:00

---

## Executive summary (cloud + local rescue round)

**Runs:** Cloud question-factory **4/5** (`swarm_runs/model-grill/20260519T221642Z`) — Qwen3.6-max timed out at 180s. Local execute **3/4** (`20260519T222015Z`) — `deepseek-r1:14b` empty/fail; **qwen2.5-coder:14b**, **mistral-nemo**, **qwen3:14b** OK.

**Best cloud models:** DeepSeek (forensic Q-tables), Ring-2.6 (masking/slippage/regime angles), Grok (fast structure).

### Consensus rescue plan (paper-only; harness-gated)

| Class | Failing prediction root cause (models agree) | Top creative question to answer first | 7-day action |
|-------|---------------------------------------------|----------------------------------------|--------------|
| **CRYPTO** | `quan_engine` drag + elite systems masked by dedup/ensemble | RESCUE_CRYPTO_01: are WR>60% slices excluded by dedup? | Whitelist-only subset backtest; pre-register **H-035 tick** (not daily-bar) |
| **EQUITY** | Confidence inversion; copytrader cross-contamination | RESCUE_EQUITY_01: is confidence just overlap count? | Gate HC on **trust_score**; EQUITY-only portfolio slice in registry |
| **COMMODITY** | CT=F concentration; COT scanner verify pending | RESCUE_COMMODITY_01: non-CT=F symbols after dedup | Run ab_analysis SQL; cap single-contract exposure |
| **ETF** | n<100; premium arb unproven; equity-beta bleed | RESCUE_ETF_01: NAV/premium data path exists? | Halt size-up; beta-neutral or leveraged-ETF-only experiment |
| **FOREX** | Class toxic except possible `signal_validation` leg | RESCUE_FOREX_01: isolated FOREX slice PF | Keep **FOREX_HARD_DISABLE**; weekly G10 carry pre-register only |
| **BOND** | n=11 — not statistically definable | RESCUE_BOND_01: freeze 90d? | **Freeze emissions**; `etf-bond-scanner` paper-only |

### P0 implementations (repo-grounded; all models)

1. **CRYPTO** — emitter whitelist enforce shadow → measure WR lift on elite-only subset (`alpha_engine/emitter_whitelist.py` + `pf_registry.json`).
2. **EQUITY** — replace confidence HC with trust_score; audit `aggregated_picks` overlap (`copy_trader_intel` / scanner logs).
3. **COMMODITY** — CT=F cap + `multi_asset_cot` verification gate before any Tier-2 claim.

### Re-run commands

```powershell
cd E:\findtorontoevents_antigravity.ca
python tools/rescue_edge_round.py --phase cloud    # question factory
python tools/rescue_edge_round.py --phase local    # execute curated Qs
python tools/rescue_edge_round.py --phase all      # full pipeline + synthesis
```

**Artifacts:** `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md`, `reports/RESCUE_CURATED_QUESTIONS_2026-05-19.md`, prompts in `docs/swarm_prompts/RESCUE_*.md`, orchestrator `tools/rescue_edge_round.py`.

---

## Curated questions

# Curated rescue questions (2026-05-19)

Merged: daily-ideas digest + cloud factory outputs + seeds.

## Daily-ideas digest seeds

# Daily ideas digest — rescue round (2026-05-19)

**Sources (canonical repo root only):** `DAILY_IDEAS.MD`, `daily_idea_antigravity.MD`, `reports/daily_ideas_edge_sweep_2026_05_17.md`, `reports/daily_ideas_edge_per_class_20260513T010800Z.md`, `DAILY_IDEAS_GROK_2026_05_16.md`, `reports/MERGED_ACTION_PLAN_2026-05-19.md`

**Ground truth:** 11/11 daily-bar causal hypotheses **KILLED** (`edge_stability_harness.py`). `pf_registry` canonical. Paper-only until harness + n≥100 clean.

---

## Per-class “failing prediction” diagnosis

| Class | Current pain | What daily-ideas agree killed it | Rescue threads (multi-agent) |
|-------|--------------|--------------------------------|------------------------------|
| **CRYPTO** | WR~46.5%, PF~1.36; `quan_engine` drag | Daily-bar on-chain/funding families killed; volume toxicity | UTC death-zone ✅; drag quarantine ✅; **H-035 tick imbalance**; elite ensemble (`aggregated_picks`+`mega_mutation`); isolate signal_validation |
| **EQUITY** | T2 PF but confidence anti-edge; no single-system isolate | PEAD crowded; generic momentum | **PEAD top-100** ✅ shipped; **trust_score** not confidence ✅; QMOM+crash overlay; sector SPDR rotation; n→100 forward |
| **COMMODITY** | Headline PF misleading; **CT=F 75%** concentration | `multi_asset_cot` dedup phantom WR | **ab_analysis** verify; DSR≥0.85 friction MC; DBMF/KMLM replication; roll-yield regime gate |
| **ETF** | n=87, PF~1.24 borderline | Class confused with equity beta | **ETF premium/dislocation** arb (Ring); macro regime overlay; halt until n≥100 |
| **FOREX** | PF~0.27, −1026% PnL | Carry/COT daily families killed/toxic | **FOREX_HARD_DISABLE** ✅; **isolate `signal_validation` FOREX leg**; G10 carry pre-register; mutation 3-axis before kill |
| **BOND** | n=11, PF~0.66 | Too thin for Tier-2 | Paper via `etf-bond-scanner` only; curve roll-down hypothesis; no live until n≥100 |
| **FUTURES** | n=12, halted | Contract-type misclassification | **T2-04 halt** ✅; fix `contract_type` classifier ✅ |

---

## Top shipped vs open (edge sweep 2026-05-17)

**Shipped:** CRYPTO UTC-hour filter, drag quarantine, FOREX hard-disable, trust_score HC, db-freshness guardian, PEAD equity, portfolio gates partial.

**Still open:** MySQL sync silent-fail fix, schema drift watchdog, COMMODITY COT verification gate (awaiting ab_analysis), alt-data threads (options flow, Polymarket, weather→softs, etc.).

---

## Creative question seeds (for cloud factory)

1. **CRYPTO:** What single falsifiable experiment on **tick data** would prove H-035 in 30 days without reusing killed families?
2. **EQUITY:** If confidence inverts edge, what **replacement feature** in `at_raw_picks` columns could gate HC picks today?
3. **COMMODITY:** How do we prove CT=F edge is real after dedup — what SQL audit on `ejaguiar1_backtests`?
4. **ETF:** What pairs trade exists in our universe with **free data only** that is NOT equity beta?
5. **FOREX:** Can we salvage **only** `signal_validation` FOREX rows — what filter on `source_system` + `symbol`?
6. **BOND:** Given n=11, is the class **statistically definable** or should we freeze emissions for 90 days?

---

## Forbidden rescue paths (do not suggest)

- Promote registry PF to live without harness
- New daily-bar COT / funding / PEAD / on-chain count families (killed)
- Generic “use ML/meta-labeling” without table + test
- Invented GitHub workflow filenames


## From deepseek-deepseek-chat__rescue_factory.md

### CRYPTO

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_CRYPTO_01 | Does `crypto_rsi_whaleconfirmed_v1` exhibit **negative selection bias** where its best-performing slices (WR>60%) are systematically excluded by `quan_engine`'s dedup logic? | Targets the "elite systems masked" clue—maybe the harness kills good signals because dedup treats them as duplicates of worse systems | `alpha_engine/emitter_whitelist.py`, `audit_trail/dedup_logs/*.csv`, `pf_registry.json` → `by_asset_class_policy_clean_net` for CRYPTO | If all masked slices have PF<1.0 even before dedup |
| RESCUE_CRYPTO_02 | Is the **intraday H-035** signal (from daily ideas) actually a **lagged version** of a killed hypothesis, causing WR<50% due to stale entry? | Daily ideas mention CRYPTO intraday H-035—if it's just a daily-bar hypothesis re-binned to intraday, it inherits the killed causal structure | `tools/edge_stability_harness.py` output logs, hypothesis registry (`hypothesis_id` + `bar_freq`), intraday pick timestamps | If H-035 has unique feature space (not derived from killed hypotheses) |
| RESCUE_CRYPTO_03 | Does the **volume drag** correlate with `quan_engine`'s **slippage model** overestimating liquidity for tokens with <$1M daily volume? | "Drag volume" suggests execution cost kills edge—maybe the slippage model uses 30-day average volume but recent volume collapsed | `alpha_engine/slippage_model.py`, exchange API (CoinGecko free tier for volume), pick-level fill prices | If slippage model uses only 7-day rolling volume (not 30-day) |

**Moonshot:** RESCUE_CRYPTO_MOON — *"If we restrict CRYPTO picks to only tokens where `quan_engine`'s dedup **never** fires (i.e., unique feature vectors), does the surviving subset achieve PF>1.5?"*  
- Hypothesis ID: `crypto_dedup_escape_v1`  
- Bar freq: 1h  
- Data: `audit_trail/dedup_logs/` + `pf_registry.json`  
- Risk: Sample size may drop below n=100

### EQUITY

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_EQUITY_01 | Does the **confidence inversion** (high-confidence picks underperform low-confidence) arise because `aggregated_picks` **double-counts** signals from correlated scanners (e.g., both momentum and value fire on same stock)? | "Confidence inverts" suggests aggregation amplifies noise—maybe confidence is just count of overlapping signals, not true edge | `alpha_engine/aggregated_picks.py`, `audit_trail/scanner_overlap_matrix.csv`, pick-level confidence scores | If confidence is derived from a single model (not count-based) |
| RESCUE_EQUITY_02 | Is the **PEAD partial** success actually a **look-ahead bias** artifact where the "earnings surprise" feature uses next-day price data? | PEAD is mentioned as partially working—if it's actually cheating, it explains why it fails in live paper | `alpha_engine/scanners/pead_scanner.py`, feature engineering code, earnings timestamp vs. feature timestamp | If PEAD features use only pre-announcement data (no look-ahead) |
| RESCUE_EQUITY_03 | Does the **T2 aggregate failure** stem from `multi_asset_copytrader` **re-weighting** EQUITY picks based on FOREX signals (toxic pair)? | Toxic pairs doc says `multi_asset_copytrader`/FOREX,EQUITY—maybe EQUITY picks get corrupted by FOREX-derived weights | `alpha_engine/multi_asset_copytrader.py`, weight logs, `pf_registry.json` → EQUITY vs. EQUITY-only sub-portfolio | If EQUITY-only sub-portfolio also fails (PF<1.5) |

**Moonshot:** RESCUE_EQUITY_MOON — *"If we remove all EQUITY picks where `multi_asset_copytrader` assigns weight <0.5 (i.e., only high-conviction standalone picks), does the subset achieve Tier-2?"*  
- Hypothesis ID: `equity_high_conviction_v1`  
- Bar freq: daily  
- Data: `alpha_engine/multi_asset_copytrader.py` weight logs  
- Risk: n may drop below 100

### COMMODITY

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_COMMODITY_01 | Does `cta_replicator`'s **concentration (CT=F)** arise because it only trades **front-month futures**, ignoring term structure signals that COT data provides? | "CT=F concentration" suggests single-contract focus—COT data is about positioning, not term structure, so maybe we're using wrong COT slice | `alpha_engine/cta_replicator.p

## Cloud factory dir
`swarm_runs\model-grill\20260519T221642Z`


### deepseek-deepseek-chat__rescue_factory.md

# deepseek:deepseek-chat

elapsed=19.99s ok=True

# Rescue Question Factory — Creative Diagnostics per Asset Class

## Executive Summary

All 11/11 pre-registered daily-bar causal hypotheses have been killed by `tools/edge_stability_harness.py`. The canonical `pf_registry.json` shows systematic failure across all six asset classes. Below are creative, falsifiable diagnostic questions designed to identify **why** our predictions fail—not generic ML improvements—using only repo data and named free APIs.

---

## A) Rescue Questions by Asset Class

### CRYPTO

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_CRYPTO_01 | Does `crypto_rsi_whaleconfirmed_v1` exhibit **negative selection bias** where its best-performing slices (WR>60%) are systematically excluded by `quan_engine`'s dedup logic? | Targets the "elite systems masked" clue—maybe the harness kills good signals because dedup treats them as duplicates of worse systems | `alpha_engine/emitter_whitelist.py`, `audit_trail/dedup_logs/*.csv`, `pf_registry.json` → `by_asset_class_policy_clean_net` for CRYPTO | If all masked slices have PF<1.0 even before dedup |
| RESCUE_CRYPTO_02 | Is the **intraday H-035** signal (from daily ideas) actually a **lagged version** of a killed hypothesis, causing WR<50% due to stale entry? | Daily ideas mention CRYPTO intraday H-035—if it's just a daily-bar hypothesis re-binned to intraday, it inherits the killed causal structure | `tools/edge_stability_harness.py` output logs, hypothesis registry (`hypothesis_id` + `bar_freq`), intraday pick timestamps | If H-035 has unique feature space (not derived from killed hypotheses) |
| RESCUE_CRYPTO_03 | Does the **volume drag** correlate with `quan_engine`'s **slippage model** overestimating liquidity for tokens with <$1M daily volume? | "Drag volume" suggests execution cost kills edge—maybe the slippage model uses 30-day average volume but recent volume collapsed | `alpha_engine/slippage_model.py`, exchange API (CoinGecko free tier for volume), pick-level fill prices | If slippage model uses only 7-day rolling volume (not 30-day) |

**Moonshot:** RESCUE_CRYPTO_MOON — *"If we restrict CRYPTO picks to only tokens where `quan_engine`'s dedup **never** fires (i.e., unique feature vectors), does the surviving subset achieve PF>1.5?"*  
- Hypothesis ID: `crypto_dedup_escape_v1`  
- Bar freq: 1h  
- Data: `audit_trail/dedup_logs/` + `pf_registry.json`  
- Risk: Sample size may drop below n=100

---

### EQUITY

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_EQUITY_01 | Does the **confidence inversion** (high-confidence picks underperform low-confidence) arise because `aggregated_picks` **double-counts** signals from correlated scanners (e.g., both momentum and value fire on same stock)? | "Confidence inverts" suggests aggregation amplifies noise—maybe confidence is just count of overlapping signals, not true edge | `alpha_engine/aggregated_picks.py`, `audit_trail/scanner_overlap_matrix.csv`, pick-level confidence scores | If confidence is derived from a single model (not count-based) |
| RESCUE_EQUITY_02 | Is the **PEAD partial** success actually a **look-ahead bias** artifact where the "earnings surprise" feature uses next-day price data? | PEAD is mentioned as partially working—if it's actually cheating, it explains why it fails in live paper | `alpha_engine/scanners/pead_scanner.py`, feature engineering code, earnings timestamp vs. feature timestamp | If PEAD features use only pre-announcement data (no look-ahead) |
| RESCUE_EQUITY_03 | Does the **T2 aggregate failure** stem from `multi_asset_copytrader` **re-weighting** EQUITY picks based on FOREX signals (toxic pair)? | Toxic pairs doc says `multi_asset_copytrader`/FOREX,EQUITY—maybe EQUITY picks get corrupted by FOREX-derived weights | `alpha_engine/multi_asset_copytrader.py`, weight logs, `pf_registry.json` → EQUITY vs. EQUITY-only sub-portfolio | If EQUITY-only sub-portfolio also fails (PF<1.5) |

**Moonshot:** RESCUE_EQUITY_MOON — *"If we remove all EQUITY picks where `multi_asset_copytrader` assigns weight <0.5 (i.e., only high-conviction standalone picks), does the subset achieve Tier-2?"*  
- Hypothesis ID: `equity_high_conviction_v1`  
- Bar freq: daily  
- Data: `alpha_engine/multi_asset_copytrader.py` weight logs  
- Risk: n may drop below 100

---

### COMMODITY

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_COMMODITY_01 | Does `cta_replicator`'s **concentration (CT=F)** arise because it only trades **front-month futures**, ignoring term structure signals that COT data provides? | "CT=F concentration" suggests single-contract focus—COT data is about positioning, not term structure, so maybe we're using wrong COT slice | `alpha_engine/cta_replicator.py`, `alpha_engine/scanners/multi_asset_cot.py`, COT API (CFTC free), contract selection logic | If `cta_replicator` already uses multiple contract months |
| RESCUE_COMMODITY_02 | Is the **dedup risk** actually a **false positive** where `quan_engine` treats COT-based and technical-based commodity signals as duplicates when they're genuinely different? | Dedup may use feature hashing that conflates fundamentally different signal sources | `audit_trail/dedup_logs/`, `tools/edge_stability_harness.py` dedup config, feature vector comparison | If dedup threshold is >0.95 cosine similarity (too aggressive) |
| RESCUE_COMMODITY_03 | Does the **"pending verify"** status of `multi_asset_cot` mean it's **not actually running** in paper, so all commodity picks come from `cta_replicator` alone? | Daily ideas say "COMMODITY verify COT"—if COT scanner is disabled, we're flying blind on positioning data | `alpha_engine/emitter_whitelist.py`, GHA workflow logs, `audit_trail/scanner_run_log.csv` | If `multi_asset_cot` appea

### inception-mercury-2__rescue_factory.md

# inception:mercury-2

elapsed=3.94s ok=True

# Rescue Question Factory – Creative Diagnostics (v1)

**Scope** – Multi‑asset pick pipeline `findtorontoevents.ca/audit`  
**Ground‑truth** – 11/11 pre‑registered daily‑bar causal hypotheses killed by `tools/edge_stability_harness.py`.  
**Goal** – Identify falsifiable, data‑driven questions that explain the current Tier‑2 shortfalls and can be pre‑registered for the next audit run.

---

## 1️⃣ Per‑Class Diagnostic Tables  

| Asset Class | Q‑ID | Question (Rescue) | Why Creative? | Data / API Needed | Falsify If … | Wire‑Target (code) | Acceptance Test |
|-------------|------|-------------------|----------------|-------------------|--------------|--------------------|-----------------|
| **CRYPTO** | RESCUE_CRYPTO_01 | *Is the drag in volume caused by a hidden OTC‑desk order‑flow that is filtered out by the emitter whitelist?* | Looks at “emitter hygiene” rather than the RSI signal itself. | `alpha_engine/emitter_whitelist.py` (whitelist set), `ejaguiar1_backtests/crypto_volumes.parquet`, CoinGecko “OTC‑volume” endpoint. | The whitelist contains **all** OTC‑desk IDs → the drag cannot be due to missing emitters. | `alpha_engine/emitter_whitelist.py` | After re‑enabling the missing emitters, the daily‑bar WR for `crypto_rsi_whaleconfirmed_v1` must rise **≥ 50 %** on a clean sample `n ≥ 100`. |
| | RESCUE_CRYPTO_02 | *Does the “crypto_rsi_whaleconfirmed_v1” signal get masked by a downstream schema‑drift in `audit_trail/registry_loader.py` that drops rows with a null `whale_flag`?* | Targets a downstream data‑pipeline bug, not the model. | `audit_trail/registry_loader.py`, `audit_dashboard/data/pf_registry.json` (raw vs. cleaned). | The loader never drops rows with null `whale_flag`. | `audit_trail/registry_loader.py` | Reload the registry without the drop‑filter; PF must climb **≥ 1.5** and WR **≥ 50 %** on the same slice. |
| | RESCUE_CRYPTO_03 | *Is there a systematic timestamp mis‑alignment (≥ 5 min) between the exchange feed and the bar‑aggregator that creates look‑ahead bias in the RSI calculation?* | Explores a timing bug rather than signal quality. | `ejaguiar1_backtests/crypto_tick_timestamp.parquet`, `tools/edge_stability_harness.py` (time‑window config). | All timestamps line‑up within 1 min → no look‑ahead bias. | `tools/edge_stability_harness.py` | Align timestamps to bar boundaries; recompute WR – must exceed **50 %**. |
| **EQUITY** | RESCUE_EQUITY_01 | *Is confidence inversion caused by stale earnings‑calendar data that makes the “PEAD partial” slice use outdated surprise flags?* | Uses an external earnings calendar to test data freshness. | Alpha Vantage “Earnings Calendar” API, `ejaguiar1_stocks/equity_earnings.parquet`. | The local earnings file is **≤ 1 day** behind the API → not stale. | `audit_trail/registry_loader.py` | Refresh earnings data; PF ≥ 1.5 & WR ≥ 50 % on `aggregated_picks`. |
| | RESCUE_EQUITY_02 | *Do mixed‑timezone bar timestamps (NY vs. LON) cause the “aggregated_picks” slice to mis‑align daily bars, flipping confidence?* | Focuses on a cross‑timezone aggregation bug. | `ejaguiar1_backtests/equity_daily_bars.parquet`, `tools/edge_stability_harness.py` (timezone config). | All bars are stored in UTC and converted correctly → no mis‑alignment. | `tools/edge_stability_harness.py` | Convert all bars to UTC before aggregation; confidence must revert to positive. |
| | RESCUE_EQUITY_03 | *Is the equity slice being contaminated by cross‑asset leakage from the “premium arb unproven” ETF signal (correlation > 0.6)?* | Checks unintended feature bleed‑through. | Correlation matrix from `audit_dashboard/data/pf_registry.json` (ETF vs. Equity). | Max correlation < 0.3 → no leakage. | `alpha_engine/feature_engineer.py` | Remove ETF‑derived features; WR must rise ≥ 50 %


### openrouter-inclusionai-ring-2-6-1t__rescue_factory.md

# openrouter:inclusionai/ring-2.6-1t

elapsed=20.14s ok=True

# Rescue Question Factory — Creative Diagnostics per Asset Class (v1)

> **Disclaimer:** No asset class is declared live-money-ready. All questions are paper-stage diagnostics intended to isolate root causes of systematic prediction failure.

---

## CRYPTO

### A) Rescue Questions

**Q-ID: RESCUE_CRYPTO_01**
```
Question: Is the ensemble masking in alpha_engine/emitter_whitelist.py systematically 
         suppressing the ONLY positive-edge signals (elite systems), causing the 
         remaining ensemble to be dominated by noise with negative expectancy?

Why creative: Instead of asking "are crypto signals bad?", this asks whether the 
              filtering mechanism ITSELF is the failure mode — the kill shot is 
              that whitelist shadow logic may be anti-selecting for alpha.

Data needed: 
  - pf_registry.json → per-emitter contribution to crypto ensemble (before/after masking)
  - alpha_engine/emitter_whitelist.py → masking logic + shadow scores
  - tools/edge_stability_harness.py → per-emitter Sharpe, WR, avg_win/avg_loss

Falsify if: Per-emitter breakdown shows ≥3 unmasked emitters each with WR≥52% 
             and positive expectancy. If true, the problem is NOT masking — 
             it's signal combination / correlation drag.
```

**Q-ID: RESCUE_CRYPTO_02**
```
Question: Is there a systematic size-asymmetry between winners and losers such that 
         a >50% WR is REQUIRED for profitability (i.e., avg_loss >> avg_win), and 
         is this driven by slippage/fee models in backtest vs. paper execution?

Why creative: WR<50 with "drag volume" suggests the P&L distribution is 
              positively skewed in losses. If the backtest assumes fills at 
              mid/close but paper hits bid/ask, the edge is an artifact of 
              execution assumptions, not signal quality.

Data needed:
  - pf_registry.json → avg_win, avg_loss, avg_trade_duration for crypto
  - audit_trail/ → fill price assumptions vs. paper slippage logs
  - Daily digest H-035 intraday signals → entry/exit timestamp delta analysis

Falsify if: After applying realistic slippage (0.05% taker, 0.02% maker) to 
             historical fills, WR remains <50% AND avg_win/avg_loss ratio stays 
             below 1.2. Then execution is NOT the root cause.
```

**Q-ID: RESCUE_CRYPTO_03**
```
Question: Do crypto signals exhibit regime-dependent edge (trending vs. ranging) 
         such that the aggregate WR<50% is actually a mixture of a profitable 
         trending regime and a destructive ranging regime, and can a simple 
         regime filter recover Tier-2 metrics?

Why creative: Rather than treating crypto as one asset class, this decomposes 
              performance by volatility regime. The "drag volume" may be 
              concentrated entirely in low-volatility chop periods.

Data needed:
  - pf_registry.json → daily P&L timeseries for crypto
  - Free API: Binance/CoinGecko OHLCV (free tier) → compute ATR percentile rank
  - tools/edge_stability_harness.py → edge by volatility quantile

Falsify if: Edge is uniformly negative across ALL volatility regimes (no regime 
             shows PF>1.0 at n≥50). Then regime-filtering won't help — abandon 
             this path.
```

### B) Moonshot — CRYPTO

```
Q-ID: MOONSHOT_CRYPTO_01
Question: Can a mean-reversion signal on the RESIDUAL of the ensemble prediction 
         (i.e., when the ensemble is wrong by >2σ, fade it) generate 
         Tier-2-compliant returns at H-1 or H-4 bar_freq?

Why moonshot: The ensemble's errors may be autocorrelated. If the harness kills 
               directional hypotheses, the meta-signal "ensemble is overconfident 
               right now" might itself be tradeable.

Pre-registration: hypothesis_id=MOON_CRYPTO_RESIDUAL_MR, bar_freq=H-4
Falsify if: Autocorrelation of residuals at lag 1 and 4 is <0.02 (no 
             exploitable memory), OR n<100 after filtering extreme residuals.
```

---

## EQUITY

### A) Rescue Questions

**Q-ID: RESCUE_EQUITY_01**
```
Question: Is the "confidence inversion" in aggregated_picks caused by a 
         calibration drift between sub-signals (e.g., PEAD sub-signal calibrated 
         on 2020-2023 data, momentum sub-signal on 2024-2025), such that the 
         weighted ensemble assigns higher confidence to the WORPER-performing 
         sub-signal in the current regime?

Why creative: This targets the aggregation layer, not individual signals. 
              Confidence inversion is a classic ensemble pathology when 
              sub-models have non-stationary calibration.

Data needed:
  - pf_registry.json → sub-signal-level performance by quarter
  - alpha_engine/ → confidence weighting scheme + calibration windows
  - audit_trail/ → rolling confidence vs. realized accuracy timeseries

Falsify if: Sub-signal calibration is within ±5% of each other in the most 
             recent 90-day window. Then the inversion is NOT a calibration 
             drift — it's a fundamental signal failure.
```

**Q-ID: RESCUE_EQUITY_02**
```
Question: Does the PEAD partial signal fail specifically on small-caps due to 
         liquidity-driven execution slippage, while mid/large-cap PEAD remains 
         Tier-2 compliant — meaning the signal is valid but the universe is wrong?

Why creative: PEAD is well-documented in large caps. If the pipeline applies 
              it uniformly across market caps without liquidity adjustment, 
              the aggregate failure masks a size-dependent


### openrouter-qwen-qwen3-6-max-preview__rescue_factory.md

# openrouter:qwen/qwen3.6-max-preview

TIMEOUT 180s


### xai-grok-3-latest__rescue_factory.md

# xai:grok-3-latest

elapsed=22.48s ok=True

**Rescue Diagnostics — Multi-Asset Pick Pipeline**

**Status**: 11/11 daily-bar causal hypotheses killed. All work remains paper-only. Emitter whitelist in shadow mode. Tier-2 gate: PF ≥ 1.5, WR ≥ 50 %, MDD < 20 %, n ≥ 100 clean post-dedup.

### Per-Class Diagnostic Tables

**CRYPTO**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_CRYPTO_01 | Emitter volume drag | crypto_rsi_whaleconfirmed_v1 | `alpha_engine/emitter_whitelist.py` | WR lift ≥ 8 pp on whitelist-only subset |
| RESCUE_CRYPTO_02 | Intraday H-035 decay | Elite masked systems | `tools/edge_stability_harness.py` | Edge stability > 0.6 on 15-min bars |
| RESCUE_CRYPTO_03 | Dedup collision rate | Post-filter signals | `audit_trail/` | Unique signal ratio ≥ 0.92 |

**EQUITY**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_EQUITY_01 | trust_score inversion | aggregated_picks | `pf_registry.json` | Spearman ρ(trust_score, forward return) > 0.15 |
| RESCUE_EQUITY_02 | PEAD residual after primary kill | Secondary window | `ejaguiar1_backtests` | t-stat on residual > 2.0 |
| RESCUE_EQUITY_03 | Sector concentration | T2 aggregate | `tools/edge_stability_harness.py` | MDD < 18 % on sector-neutral slice |

**COMMODITY**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_COMMODITY_01 | CT=F concentration | multi_asset_cot | `pf_registry.json` | PF ≥ 1.4 after single-contract cap |
| RESCUE_COMMODITY_02 | Dedup risk on roll dates | Pending verify | `audit_trail/` | n_clean ≥ 110 post-roll filter |
| RESCUE_COMMODITY_03 | Curve-shape signal | Non-COT | `ejaguiar1_stocks` | WR ≥ 52 % on term-structure features |

**ETF**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_ETF_01 | Premium arb viability | premium arb | `pf_registry.json` | n ≥ 120 with PF ≥ 1.5 |
| RESCUE_ETF_02 | Liquidity filter impact | Borderline n | `tools/edge_stability_harness.py` | Edge stability > 0.55 |
| RESCUE_ETF_03 | NAV vs price lag | Daily bars | `ejaguiar1_backtests` | Lag coefficient p < 0.05 |

**FOREX**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_FOREX_01 | Carry isolation | cta_replicator slice | `alpha_engine/emitter_whitelist.py` | PF ≥ 1.3 on carry-only |
| RESCUE_FOREX_02 | Signal validation decay | Paper only | `tools/edge_stability_harness.py` | Stability > 0.5 across regimes |
| RESCUE_FOREX_03 | Pairwise correlation spike | Multi-pair | `pf_registry.json` | MDD < 15 % after corr filter |

**BOND**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_BOND_01 | Duration bucket viability | n=11 expansion | `pf_registry.json` | n ≥ 100 with PF ≥ 1.4 |
| RESCUE_BOND_02 | Yield-curve slope | Secondary | `ejaguiar1_backtests` | WR ≥ 50 % on slope features |
| RESCUE_BOND_03 | Liquidity regime | Low n | `tools/edge_stability_harness.py` | Edge stability > 0.45 |

### Moonshot Questions (pre-registerable)

- **CRYPTO**: Moonshot — Does 15-min order-flow imbalance from two specific emitters predict 4-hour returns with PF ≥ 1.6? (hypothesis_id: crypto_flow_15m_v1, bar_freq: 15min)
- **EQUITY**: Moonshot — Does a trust_score × sector-momentum interaction term restore T2 performance after primary PEAD kill? (hypothesis_id: equity_trust_interact_v1, bar_freq: daily)
- **COMMODITY**: Moonshot — Does term-structure curvature on non-front contracts yield PF ≥ 1.5 with n ≥ 120 after single-contract cap? (hypothesis_id: comm_curve_v2, bar_freq: daily)
- **ETF**: Moonshot — Does NAV-price convergence speed on high-AUM ETFs produce PF ≥ 1.55 with n ≥ 130? (hypothesis_id: etf_nav_speed_v1, bar_freq: daily)
- **FOREX**: Moonshot — Does isolated carry signal on G10 crosses after volatility regime filter reach PF ≥ 1.4 with MDD < 18 %? (hypothesis_id: forex_carry_regime_v1, bar_freq: daily)
- **BOND**: Moonshot — Does duration-bucket rotation on 2y/10y/30y treasuries achieve n ≥ 110 and PF ≥ 1.45? (hypothesis_id: bond_duration_rot_v1, bar_freq: daily)

### Cross-Class Meta-Question
Does schema drift or deduplication latency in the shared resolver (`.github/workflows/audit-dashboard.yml`) cause systematic n < 100 and edge decay across CRYPTO, EQUITY, and FOREX simultaneously?

### Top 5 Questions by Expected Information Gain
1. RESCUE_CRYPTO_01 — highest immediate WR lift potential via whitelist
2. RESCUE_EQUITY_01 — directly targets trust_score inversion
3. Cross-class meta-question — explains multiple class failures at once
4. RESCUE_COMMODITY_01 — tests concentration hypothesis with clear cap
5. RESCUE_FOREX_01 — isolates carry after toxic-pair removal

All diagnostics remain paper-only and must pass `tools/edge_stability_harness.py` before any emitter promotion.


## Local execute dir
`swarm_runs\model-grill\20260519T222015Z`


### ollama-deepseek-r1-14b__rescue_execute.md

# ollama:deepseek-r1:14b

elapsed=24.96s ok=False




### ollama-mistral-nemo-latest__rescue_execute.md

# ollama:mistral-nemo:latest

elapsed=13.89s ok=True

Here's a summary of the required deliverables based on the provided information:

### 1) Per-class rescue verdict table

| Class | Still failing? | Best rescue path | P(Tier-2 in 12mo) | First 7-day action |
|-------|----------------|------------------|-------------------|---------------------|
| CRYPTO | No | Elite masked systems + UTC hour | 0.95 | Implement elite masked systems and UTC hour filter |
| EQUITY | Yes | Trust score inversion fix + PEAD top-100 | 0.78 | Fix trust score inversion and implement PEAD top-100 gate |
| COMMODITY | No | CT=F concentration cap | 0.92 | Implement CT=F concentration cap |
| ETF | Yes | Premium arb viability + Liquidity filter | 0.65 | Improve premium arb viability and implement liquidity filter |
| FOREX | Yes | Carry isolation + Session overlap volatility | 0.48 | Isolate carry signal validation rows and implement session overlap volatility filter |
| BOND | No | Freeze emissions for 90 days | 0.87 | Freeze bond emissions for 90 days |

### 2) Per-class: one pre-registerable hypothesis

| Class | hypothesis_id | bar_freq | mechanism | wire_target | harness acceptance_test |
|-------|---------------|----------|-----------|-------------|------------------------|
| CRYPTO | H-035 | tick/intraday | Elite masked systems + UTC hour | `tools/edge_stability_harness.py` | eff≥0.30, 3/5 windows |
| EQUITY | Trust_score_fix | daily | Fix trust score inversion | `pf_registry.json` | Spearman(confidence, pnl)>0 on n≥200 |
| COMMODITY | CT=F_concentration_cap | daily | Implement CT=F concentration cap | `pf_registry.json` | PF≥1.5 on n≥50 after dedup |
| ETF | Premium_arb_viability | daily | Improve premium arb viability | `pf_registry.json` | PF≥1.2 |
| FOREX | Carry_isolation | daily | Isolate carry signal validation rows | `alpha_engine/emitter_


### ollama-qwen2-5-coder-14b-instruct-q4-k-m__rescue_execute.md

# ollama:qwen2.5-coder:14b-instruct-q4_K_M

elapsed=23.89s ok=True

## Per-class Rescue Verdict Table

| Class     | Still failing? | Best rescue path                        | P(Tier-2 in 12mo) | First 7-day action                          |
|-----------|----------------|-----------------------------------------|-------------------|---------------------------------------------|
| CRYPTO    | Yes            | RESCUE_CRYPTO_01 (Emitter volume drag)   | 80%               | Implement whitelist-only subset test        |
| EQUITY    | Yes            | RESCUE_EQUITY_01 (Trust score inversion)  | 75%               | Replace inverted confidence for HC gating   |
| COMMODITY | Yes            | RESCUE_COMMODITY_01 (CT=F concentration) | 85%               | Implement single-contract cap test          |
| ETF       | Yes            | RESCUE_ETF_01 (Premium arb viability)     | 70%               | Verify premium/discount vs NAV data path    |
| FOREX     | Yes            | RESCUE_FOREX_01 (Carry isolation)        | 82%               | Isolate carry-only slice                    |
| BOND      | Yes            | RESCUE_BOND_01 (Duration bucket viability)| 78%               | Freeze BOND emissions for 90 days           |

## Per-class Pre-Registerable Hypothesis

| Class     | hypothesis_id       | bar_freq | mechanism                          | wire_target | harness acceptance_test                |
|-----------|---------------------|----------|--------------------------------------|-------------|----------------------------------------|
| CRYPTO    | H-035 or new        | tick     | Isolate elite systems with whitelist | `tools/` + registry | eff≥0.30, 3/5 windows                 |
| EQUITY    | PEAD top-100 + trust_score≥0.7 | daily | Combine PEAD with high trust score | walk-forward | PF≥1.2                               |
| COMMODITY | Roll-yield sign × COT percentile interaction | weekly | Analyze roll-yield and COT interaction | `ejaguiar1_stocks` | ρ>0.3                                |
| ETF       | Leveraged ETF picks with regime gate | daily | Apply TLT/IEF ratio for ETF sizing | `tools/` + registry | n≥120 with PF≥1.5                  |
| FOREX     | Session overlap volatility filter | daily | Filter based on London+NY session overlap | `alpha_engine/emitter_whitelist.py` | MDD<15% after corr filter             |
| BOND      | Curve steepener regime gate | monthly | Apply 2s10s curve steepener for bond picks | `tools/` + registry | n≥100 with PF≥1.4                  |

## Three Repo-Grounded Implementations (P0)

| id | wire_target | acceptance_test (60d) | which rescue question it answers |
|----|-------------|-----------------------|-------------------------------------|
| 1  | RESCUE_CRYPTO_01 | WR lift ≥ 8 pp on whitelist-only subset | Emitter volume drag |
| 2  | RESCUE_EQUITY_01 | Spearman ρ(trust_score, forward return) > 0.15 | Trust score inversion |
| 3  | RESCUE_COMMODITY_01 | PF ≥ 1.4 after single-contract cap | CT=F concentration |

## Daily-Ideas Integration

- **UTC-hour**: SHIP (Implement UTC-hour filter in `alpha_engine/emitter_whitelist.py`)
- **COT verify**: REJECT (Not directly relevant to current rescue efforts)
- **Carry FOREX**: DEFER (Further analysis needed before implementation)

## Brutal Honesty

Classes that should be **frozen for 90 days**:
- BOND
- COMMODITY

Classes that should **continue paper rescue**:
- CRYPTO
- EQUITY
- ETF
- FOREX


### ollama-qwen3-14b__rescue_execute.md

# ollama:qwen3:14b

elapsed=22.17s ok=True

### **1) Per-Class Rescue Verdict Table**

| **Class** | **Still failing?** | **Best rescue path** | **P(Tier-2 in 12mo)** | **First 7-day action** |
|-----------|-------------------|------------------------|------------------------|------------------------|
| **CRYPTO** | ✅ Yes | RESCUE_CRYPTO_01 (whitelist-only WR lift) | 75% (if eff≥0.30) | Run 3/5 window test on H-035 with tick-level data |
| **EQUITY** | ✅ Yes | RESCUE_EQUITY_01 (trust_score inversion fix) | 60% (if ρ>0.15) | Spearman test on `at_raw_picks` vs forward returns |
| **COMMODITY** | ✅ Yes | RESCUE_COMMODITY_01 (CT=F concentration cap) | 55% (if PF≥1.4) | Run single-contract cap on `multi_asset_cot` |
| **ETF** | ✅ Yes | RESCUE_ETF_01 (premium arb viability) | 40% (if n≥120) | Validate historical NAV/price data via free API |
| **FOREX** | ✅ Yes | RESCUE_FOREX_01 (carry isolation) | 30% (if PF≥1.3) | Isolate `signal_validation` slice in `alpha_engine` |
| **BOND** | ✅ Yes | RESCUE_BOND_01 (duration bucket viability) | 25% (if n≥100) | Freeze 90d emissions and test PF/MDD improvement |
| **META** | ❌ No | Universal dedup + resolver v2.1 | N/A | Monitor cross-class PF inflation (50%+ threshold) |

---

### **2) Per-Class Pre-Registerable Hypotheses**

| **Class** | **hypothesis_id** | **bar_freq** | **mechanism** | **wire_target** | **harness acceptance_test

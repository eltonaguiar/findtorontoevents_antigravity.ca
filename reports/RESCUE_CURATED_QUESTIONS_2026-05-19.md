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
| RESCUE_COMMODITY_01 | Does `cta_replicator`'s **concentration (CT=F)** arise because it only trades **front-month futures**, ignoring term structure signals that COT data provides? | "CT=F concentration" suggests single-contract focus—COT data is about positioning, not term structure, so maybe we're using wrong COT slice | `alpha_engine/cta_replicator.py`, `alpha_engine/scanners/multi_asset_cot.py`, COT API (CFTC free), contract selection logic | If `cta_replicator` already uses multiple contract months |
| RESCUE_COMMODITY_02 | Is the **dedup risk** actually a **false positive** where `quan_engine` treats COT-based and technical-based commodity signals as duplicates when they're genuinely different? | Dedup may use feature hashing that conflates fundamentally different signal sources | `audit_trail/dedup_logs/`, `tools/edge_stability_harness.py` dedup config, feature vector comparison | If dedup threshold is >0.95 cosine similarity (too aggressive) |
| RESCUE_COMMODITY_03 | Does the **"pending verify"** status of `multi_asset_cot` mean it's **not actually running** in paper, so all commodity picks come from `cta_replicator` alone? | Daily ideas say "COMMODITY verify COT"—if COT scanner is disabled, we're flying blind on positioning data | `alpha_engine/emitter_whitelist.py`, GHA workflow logs, `audit_trail/scanner_run_log.csv` | If `multi_asset_cot` appears in emitter whitelist as active |

**Moonshot:** RESCUE_COMMODITY_MOON — *"If we replace `cta_replicator`'s front-month focus with a **calendar spread** signal (using COT data to pick which contract month), does PF exceed 1.5?"*  
- Hypothesis ID: `commodity_calendar_spread_v1`  
- Bar freq: daily  
- Data: CFTC COT API, futures term structure  
- Risk: Requires new scanner development

### ETF

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_ETF_01 | Is the **n<100** problem because `premium_arb` only triggers during **extreme market events** (VIX>30), which are rare in our backtest window? | "Premium arb unproven" suggests it only works in high-volatility regimes—maybe we need to condition on VIX | `alpha_engine/scanners/premium_arb.py`, VIX API (free), pick timestamps vs. VIX levels | If premium_arb fires >100 times even in low-VIX periods |
| RESCUE_ETF_02 | Does the **borderline PF** come from **stale NAV data** where our ETF pricing lags underlying basket by >1 minute? | ETF arbitrage requires precise pricing—if our data feed is delayed, the arb disappears | Data feed latency logs, `alpha_engine/data_freshness.py`, ETF vs. underlying price timestamps | If latency is consistently <10 seconds |
| RESCUE_ETF_03 | Is the **low n** actually a **dedup artifact** where `quan_engine` treats all ETF picks as duplicates of their underlying equity picks? | ETFs and their components may share feature vectors, causing systematic dedup | `audit_trail/dedup_logs/`, ETF-holding mapping, feature vector comparison | If ETF picks have unique features (e.g., premium/discount) |

**Moonshot:** RESCUE_ETF_MOON — *"If we restrict ETF picks to only **leveraged/inverse ETFs** (where arbitrage is more profitable due to decay), does n exceed 100 with PF>1.5?"*  
- Hypothesis ID: `etf_leveraged_arb_v1`  
- Bar freq: 1h  
- Data: ETF list (free from etfdb.com), premium/discount data  
- Risk: Leveraged ETFs have higher volatility and MDD risk

### FOREX

| Q-ID | Question | Why Creative | Data Needed | Falsify If |
|------|----------|--------------|-------------|------------|
| RESCUE_FOREX_01 | Does the **PF~0.27** come from `cta_replicator` using **daily bar data** for FOREX when the edge is actually intraday (e

## From inception-mercury-2__rescue_factory.md

RESCUE_CRYPTO_01 | *Is the drag in volume caused by a hidden OTC‑desk order‑flow that is filtered out by the emitter whitelist?* | Looks at “emitter hygiene” rather than the RSI signal itself. | `alpha_engine/emitter_whitelist.py` (whitelist set), `ejaguiar1_backtests/crypto_volumes.parquet`, CoinGecko “OTC‑volume” endpoint. | The whitelist contains **all** OTC‑desk IDs → the drag cannot be due to missing emitters. | `alpha_engine/emitter_whitelist.py` | After re‑enabling the missing emitters, the daily‑bar WR for `crypto_rsi_whaleconfirmed_v1` must rise **≥ 50 %** on a clean sample `n ≥ 100`. |
| | RESCUE_CRYPTO_02 | *Does the “crypto_rsi_whaleconfirmed_v1” signal get masked by a downstream schema‑drift in `audit_trail/registry_loader.py` that drops rows with a null `whale_flag`?* | Targets a downstream data‑pipeline bug, not the model. | `audit_trail/registry_loader.py`, `audit_dashboard/data/pf_registry.json` (raw vs. cleaned). | The loader never drops rows with null `whale_flag`. | `audit_trail/registry_loader.py` | Reload the registry without the drop‑filter; PF must climb **≥ 1.5** and WR **≥ 50 %** on the same slice. |
| | RESCUE_CRYPTO_03 | *Is there a systematic timestamp mis‑alignment (≥ 5 min) between the exchange feed and the bar‑aggregator that creates look‑ahead bias in the RSI calculation?* | Explores a timing bug rather than signal quality. | `ejaguiar1_backtests/crypto_tick_timestamp.parquet`, `tools/edge_stability_harness.py` (time‑window config). | All timestamps line‑up within 1 min → no look‑ahead bias. | `tools/edge_stability_harness.py` | Align timestamps to bar boundaries; recompute WR – must exceed **50 %**. |
| **EQUITY** | RESCUE_EQUITY_01 | *Is confidence inversion caused by stale earnings‑calendar data that makes the “PEAD partial” slice use outdated surprise flags?* | Uses an external earnings calendar to test data freshness. | Alpha Vantage “Earnings Calendar” API, `ejaguiar1_stocks/equity_earnings.parquet`. | The local earnings file is **≤ 1 day** behind the API → not stale. | `audit_trail/registry_loader.py` | Refresh earnings data; PF ≥ 1.5 & WR ≥ 50 % on `aggregated_picks`. |
| | RESCUE_EQUITY_02 | *Do mixed‑timezone bar timestamps (NY vs. LON) cause the “aggregated_picks” slice to mis‑align daily bars, flipping confidence?* | Focuses on a cross‑timezone aggregation bug. | `ejaguiar1_backtests/equity_daily_bars.parquet`, `tools/edge_stability_harness.py` (timezone config). | All bars are stored in UTC and converted correctly → no mis‑alignment. | `tools/edge_stability_harness.py` | Convert all bars to UTC before aggregation; confidence must revert to positive. |
| | RESCUE_EQUITY_03 | *Is the equity slice being contaminated by cross‑asset leakage from the “premium arb unproven” ETF signal (correlation > 0.6)?* | Checks unintended feature bleed‑through. | Correlation matrix from `audit_dashboard/data/pf_registry.json` (ETF vs. Equity). | Max correlation < 0.3 → no leakage. | `alpha_engine/feature_engineer.py` | Remove ETF‑derived features; WR must rise ≥ 50 %

## From openrouter-inclusionai-ring-2-6-1t__rescue_factory.md

Q-ID: RESCUE_CRYPTO_01**
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

Q-ID: RESCUE_CRYPTO_02**
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

Q-ID: RESCUE_CRYPTO_03**
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

Q-ID: RESCUE_EQUITY_01**
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

Q-ID: RESCUE_EQUITY_02**
```
Question: Does the PEAD partial signal fail specifically on small-caps due to 
         liquidity-driven execution slippage, while mid/large-cap PEAD remains 
         Tier-2 compliant — meaning the signal is valid but the universe is wrong?

Why creative: PEAD is well-documented in large caps. If the pipeline applies 
              it uniformly across market caps without liquidity adjustment, 
              the aggregate failure masks a size-dependent

## From xai-grok-3-latest__rescue_factory.md

RESCUE_CRYPTO_01 | Emitter volume drag | crypto_rsi_whaleconfirmed_v1 | `alpha_engine/emitter_whitelist.py` | WR lift ≥ 8 pp on whitelist-only subset |
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

RESCUE_COMMODITY_01 | CT=F concentration | multi_asset_cot | `pf_registry.json` | PF ≥ 1.4 after single-contract cap |
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

RESCUE_FOREX_01 | Carry isolation | cta_replicator slice | `alpha_engine/emitter_whitelist.py` | PF ≥ 1.3 on carry-only |
| RESCUE_FOREX_02 | Signal validation decay | Paper only | `tools/edge_stability_harness.py` | Stability > 0.5 across regimes |
| RESCUE_FOREX_03 | Pairwise correlation spike | Multi-pair | `pf_registry.json` | MDD < 15 % after corr filter |

**BOND**
| ID | Focus | Target Slice | Wire Target | Acceptance Test |
|----|-------|--------------|-------------|-----------------|
| RESCUE_BOND_01 | Duration bucket viability | n=11 expansion | `pf_registry.json` | n ≥ 100 with PF ≥ 1.4 |
| RESCUE_BOND_02 | Yield-curve slope | Secondary | `ejaguiar1_backtests` | WR ≥ 50 % on slope features |
| RESCUE_BOND_03 | Liquidity regime | Low n | `tools/edge_stability_harness.py` | Edge stability > 0.45 |

### Moonshot Questions (pre-registerable)

RESCUE_CRYPTO_01 — highest immediate WR lift potential via whitelist
2. RESCUE_EQUITY_01 — directly targets trust_score inversion
3. Cross-class meta-question — explains multiple class failures at once
4. RESCUE_COMMODITY_01 — tests concentration hypothesis with clear cap
5. RESCUE_FOREX_01 — isolates carry after toxic-pair removal

All diagnostics remain paper-only and must pass `tools/edge_stability_harness.py` before any emitter promotion.

## Fixed seeds (always include)

### CRYPTO
- RESCUE_CRYPTO_01: What single tick-level experiment proves H-035 in 30d without killed daily-bar families? Falsify if eff<0.30 on 3/5 windows.
- RESCUE_CRYPTO_02: Can we isolate elite systems (`aggregated_picks`, `mega_mutation`) with emitter whitelist + UTC hour — what SQL proves drag removal lifts WR≥50?
- RESCUE_CRYPTO_MOON: Does 5m order-flow imbalance predict 4h forward return conditional on funding z-score decile?

### EQUITY
- RESCUE_EQUITY_01: Which `at_raw_picks` column replaces inverted confidence for HC gating? Falsify if Spearman(confidence, pnl)>0 on n≥200.
- RESCUE_EQUITY_02: Does PEAD top-100 + trust_score≥0.7 beat PEAD alone on walk-forward? Falsify if PF<1.2.
- RESCUE_EQUITY_MOON: Sector rotation (XLK/XLE spread) as regime gate for equity picks only?

### COMMODITY
- RESCUE_COMMODITY_01: After dedup, does `multi_asset_cot` on non-CT=F symbols still show PF≥1.5 n≥50? Falsify if all symbols fail.
- RESCUE_COMMODITY_02: DBMF replication — does our COMMODITY PnL correlate >0.3 with DBMF monthly? Falsify if ρ<0.1.
- RESCUE_COMMODITY_MOON: Roll-yield sign × COT percentile interaction — pre-register on weekly bars only.

### ETF
- RESCUE_ETF_01: ETF premium/discount vs NAV — do we have data path or free API? Falsify if no historical series.
- RESCUE_ETF_02: Are ETF picks 90% equity beta — if yes, merge class or add beta-neutral filter?
- RESCUE_ETF_MOON: Rates-regime gate (TLT/IEF ratio) sizing ETF picks only?

### FOREX
- RESCUE_FOREX_01: Isolate `signal_validation` FOREX rows only — PF on that slice vs class? Falsify if n<30 or PF<1.0.
- RESCUE_FOREX_02: G10 carry factor from free FRED/ECB — pre-register weekly, not daily COT?
- RESCUE_FOREX_MOON: Session overlap (London+NY) volatility filter for any surviving FOREX emitter?

### BOND
- RESCUE_BOND_01: Freeze BOND emissions 90d — does portfolio PF/MDD improve? Falsify if BOND slice was positive expectancy.
- RESCUE_BOND_02: `etf-bond-scanner` only path — can we reach n=100 in 12mo at current emit rate?
- RESCUE_BOND_MOON: Curve steepener (2s10s) regime gate for bond picks — monthly bars only?

### META
- RESCUE_META_01: Does universal dedup + resolver v2.1 explain >50% of cross-class PF inflation vs raw?

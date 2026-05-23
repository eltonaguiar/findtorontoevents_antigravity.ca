# Comet Strategy Verification — 2026-05-04

Verifies three Perplexity Comet browser-analysis claims against live repo data
(read-only). Sources cited file:line where load-bearing.

---

## Per-Claim Verdicts

| Claim | Comet | Repo Reality | Verdict |
|---|---|---|---|
| **A.** "1 of 46 ML features active" | 1/46 | 9 nonzero / 18 in trained model; 33 declared in `FEATURES`; 40 in schema v2 | **REJECTED** (numbers wrong both directions) |
| **B1.** Battleground DNA: ~62% WR, +161% PnL | 62% WR / +161% | No "Battleground DNA" strategy exists. Closest: `battleground/data/closed_picks.json` aggregate → **57.8% WR / +28.58% sum-PnL / PF 1.84 / n=109** | **REJECTED** (name not present; aggregate is healthy but far from Comet's numbers) |
| **B2.** System F – ClawsOfDoom: ~52% WR, +41% PnL | 52% / +41% | `ml_battleground/system_f_clawsofdoom/data/closed_picks.json` (price-derived since `pnl_pct` is null) → **48.8% WR / +62.54% sum-PnL / PF 1.14 / n=160**, single strategy "Extreme Fear Contrarian" | **CLOSE** (WR within 3pp; PnL higher than claim; PF only 1.14 — not Tier 2) |
| **C.** DOTUSDT dominates PnL & quarter-Kelly caps | "dominates" | DOTUSDT n=322 (4.31% of picks), pnl_pct sum −72.94 (6.91% of total negative), pnl_$ +$1.83 (≈0%) | **REJECTED** (DOTUSDT is mid-pack; MATICUSDT/HYPEUSDT/TAOUSDT/BTCUSDT all have larger negative contributions; TRXUSDT dominates dollar PnL at −$36,151) |

---

## 1. ML Feature Count Matrix (Claim A)

| File:line | Source | Total | Active (nonzero importance) |
|---|---|---|---|
| `alpha_engine/data/features_schema_v2.json` (header) | Schema declares "39 features from MLSignalRanker.FEATURES (Phase 14)" | **40** entries | n/a (schema only) |
| `alpha_engine/ml_ranker.py:344-418` | `MLSignalRanker.FEATURES` list | **33** (after Phase 18-20 drops) | n/a (declared) |
| `alpha_engine/data/feature_importance.json` (generated 2026-04-15, xgboost, n=326) | Trained model importances | **18** in current model | **9 nonzero** |
| `tools/data/ml_composite_baseline.json` | Audit dashboard composite mean | **8** | 6 nonzero (regime_match, sector_rotation, strategy_concentration_penalty all near-zero) |

**Active (nonzero) features in current xgboost model (`feature_importance.json`):**
volume_ratio (0.200), hour_utc (0.119), direction_encoded (0.115),
strategy_forward_wr (0.110), sl_distance_pct (0.101),
strategy_forward_n (0.100), confidence (0.094), rr_asymmetry (0.086),
tp_distance_pct (0.075).

**Zero-importance / dead in current model:** hour_sin, hour_x_vol,
funding_rate_raw, funding_z_30d, funding_persistence, orderbook_imbalance,
vpin_toxicity, funding_rate_norm, obi_delta_5.

**Comet's "46" is not a number that appears in any feature registry.**
Closest-bigger ML feature universe is the 40-entry `features_schema_v2.json`.
Even taking the worst-case framing — "9 nonzero of 40 declared" — Comet's
**1/46** is wrong. The correct framings are:

- **9 / 18** (active in trained model file)
- **9 / 33** (active vs declared `FEATURES`)
- **9 / 40** (active vs schema)

So roughly **half the funding/microstructure/OBI velocity/Phase-7-8 features
are dormant** — that *direction* is correct, but Comet's ratio is
sensationalized.

---

## 2. Battleground DNA & System F – ClawsOfDoom (Claim B)

### "Battleground DNA"
- **Not found** as a strategy name in any closed_picks.json or live config.
- The umbrella `battleground/data/closed_picks.json` (n=109) holds 8 distinct
  strategies, top: `crypto_liquidity_wick_reversal_v1` (n=32),
  `atr_percentile_gate` (n=19), `multi_period_rsi_confluence_eth` (n=16).
- Aggregate stats: **WR 57.8%, sum_pnl_pct +28.58%, PF 1.84, n=109.**
- These are **healthy Tier-2 candidate** numbers (PF>1.5), but n=109 is at the
  charter floor and there is no strategy actually called "Battleground DNA".
- Comet's "+161% PnL" likely conflates this with crypto_signal_engine or
  rapid_fire archives — neither matched.

### System F – ClawsOfDoom (`ml_battleground/system_f_clawsofdoom/`)
- File: `ml_battleground/system_f_clawsofdoom/data/closed_picks.json` (n=160).
- All `pnl_pct` fields are **null**; status field reliably populated
  (CLOSED_TP=78, CLOSED_SL=82). Computed from entry/exit prices + direction:
  - **WR 48.8%** (78/160; from CLOSED_TP count)
  - **sum_pnl_pct +62.54%**
  - **PF 1.14**
  - All 160 picks are single strategy "Extreme Fear Contrarian"
- WR is close to Comet's 52% (off by 3pp); cumulative PnL +62% > Comet's +41%;
  but **PF=1.14 fails Tier-2 floor (PF>1.5)** and `pnl_pct` plumbing is broken
  (null fields → none of the other dashboards see this system's results).

---

## 3. DOTUSDT Concentration (Claim C)

Computed across `alpha_engine/data/closed_picks.json` (n=7,472, total
sum_pnl_pct = −1056.19, total pnl_dollar = −$30,960.73).

| Symbol | n | % of picks | pnl_pct sum | % of |total pnl_pct| | pnl_$ sum |
|---|---|---|---|---|---|
| MATICUSDT | 1057 | 14.1% | −158.55 | 15.0% | $0 |
| BTCUSDT | 671 | 9.0% | −105.45 | 10.0% | −$1,846 |
| TAOUSDT | 649 | 8.7% | −115.66 | 11.0% | $0 |
| KASUSDT | 634 | 8.5% | −61.96 | 5.9% | $0 |
| HYPEUSDT | 553 | 7.4% | −123.35 | 11.7% | $0 |
| RENDERUSDT | 325 | 4.4% | −61.72 | 5.8% | +$4,731 |
| **DOTUSDT** | **322** | **4.31%** | **−72.94** | **6.9%** | **+$1.83** |
| TRXUSDT | 276 | 3.7% | −22.52 | 2.1% | **−$36,151** |

DOTUSDT is **rank #7 by count and rank #5 by abs(pnl_pct)** — it is *not*
dominating. Dollar PnL is dominated overwhelmingly by **TRXUSDT (−$36,151,
117% of total dollar loss)**. Comet's "DOTUSDT dominates" claim is **REJECTED**.

A quarter-Kelly cap on DOTUSDT specifically would address < 7% of the bleed.
The right concentration intervention is on **MATICUSDT/HYPEUSDT/TAOUSDT/BTCUSDT
quan_engine_scalp volume** (49% of all picks combined).

---

## 4. Per-Asset-Class Top-3 Strategies (n>=20)

Filter: `alpha_engine/data/closed_picks.json`, asset_class field literal,
PF ranked.

### COMMODITY
| PF | WR | n | sum_pnl_pct | strategy |
|---|---|---|---|---|
| 8.03 | 85.4% | 41 | +1.45 | cot_positioning |
| 7.93 | 83.9% | 31 | +1.13 | cftc_cot_commercial_signal |

### EQUITY
| 1.17 | 40.7% | 27 | +0.08 | stocks_rsi2_pullback |

### FOREX
| 1.36 | 47.6% | 82 | +0.03 | cta_cross_asset_tsmom |
| 0.71 | 34.8% | 132 | −0.11 | ig_contrarian_sentiment |
| 0.22 | 18.1% | 83 | −0.31 | myfxbook_retail_contrarian |

### FUTURES
| 0.00 | 0.0% | 31 | −0.92 | futures_momentum |

### CRYPTO (literal asset_class='CRYPTO')
n=3 only — too small. **All real crypto is in UNKNOWN bucket** (see below).

### UNKNOWN (92% of picks — predominantly crypto, asset_class missing)
| PF | WR | n | sum_pnl_pct | strategy |
|---|---|---|---|---|
| 60.54 | 96.8% | 31 | +0.56 | ml_enhanced_DYDXUSDT_15m_D_ensemble_stack |
| 41.52 | 96.4% | 28 | +4.05 | ml_enhanced_INJUSDT_1d_B_lightgbm |
| 9.43 | 56.8% | 44 | +7.59 | ml_enhanced_FETUSDT_1d_B_lightgbm |

`UNKNOWN` source breakdown: quan_engine (n=5896, WR 30.4%, PF 0.41,
netpnl −995pp) drags the bucket; rapid_fire (n=207, PF 0.16) is a smaller
secondary drag. The `ml_enhanced_*` strategies are the elite tier (PF 9-60)
buried inside this bucket — confirms the prior `rr_band_per_asset` finding.

---

## 5. Top-5 Follow-Up Actions (if claims as stated)

1. **Promote `ml_enhanced_FETUSDT_1d_B_lightgbm` (PF 9.43, WR 56.8%, n=44, +7.59pp)
   to PROVEN tier under Goal #1.** First strategy in the UNKNOWN bucket with
   simultaneously large n + large net-PnL contribution + Tier-1 PF. Two
   ensemble_stack strategies (DYDX/INJ) have higher PF but their cumulative
   PnL is small — promote-to-watchlist.
2. **Backfill `asset_class='CRYPTO'`** on quan_engine_scalp + ml_enhanced_*
   picks. Currently 6,886/7,472 = 92% are tagged UNKNOWN, breaking every
   dashboard verdict that uses `by_asset_class`. Single-line patch in
   `outcome_resolver.py` → re-emit closed_picks_fast.json.
3. **Cap TRXUSDT — not DOTUSDT.** TRXUSDT alone is −$36,151 (≈117% of total
   dollar loss vs −$30,961 net). Add `BLOCKED_SYMBOL` or position-size cap
   in scanner. DOTUSDT cap would address < 7% of bleed.
4. **Either fix or kill System F – ClawsOfDoom**: `pnl_pct` is null on all
   160 closed picks → invisible to every aggregator; PF=1.14 fails Tier-2
   floor anyway. If the price-derived numbers hold up, fix the resolver
   plumbing. Otherwise apply mutate-before-kill protocol.
5. **Document the ML-feature dormancy honestly** (~9/33 = 27% active, NOT
   1/46) and either retrain with the current feature set or drop the dormant
   funding/OBI/microstructure features per Phase-14-style Boruta cull.
   `feature_importance.json::low_importance` already lists the 9 candidates
   to drop.

---

## Sources

- `alpha_engine/data/closed_picks.json` (n=7,472)
- `alpha_engine/data/feature_importance.json` (xgboost, generated 2026-04-15)
- `alpha_engine/data/features_schema_v2.json` (40 entries)
- `alpha_engine/ml_ranker.py:326-418` (LEAKY_FEATURES + FEATURES)
- `tools/data/ml_composite_baseline.json` (8 features, dashboard composite)
- `battleground/data/closed_picks.json` (n=109)
- `ml_battleground/system_f_clawsofdoom/data/closed_picks.json` (n=160)
- `ml_battleground/system_{a..e}/data/closed_picks.json` (mostly empty/<20)

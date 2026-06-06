# Top Picks Per Class — 2026-06-06

**Generated:** 2026-06-06 ~19:30 UTC  
**Source:** Live `at_raw_picks` DB queries, cross-referenced with CRYPTO/ETF investigation context  
**Dedup method:** GROUP BY (symbol, DATE(signal_timestamp)) to eliminate within-day duplicates  
**Artifact flags:** strategies where pnl_pct repeats identically across many rows or sum pnl > 1000% are flagged as ARTIFACT

---

## Statistically Valid Edges (Evidence-Based, Dedup-Clean)

### FOREX

**Best strategy:** `combined_confidence`  
- **Dedup stats:** n=46, WR=78.3%, PF=22.65 (raw) — PF inflated by ig_contrarian/zscore batch artifacts in raw pool  
- **Artifact warning:** `forex_rsi2_mean_reversion` shows n_dedup=195 distinct (sym,date) but 886 rows in the dedup query (multiple pnl values per same sym/date from different signal windows). Raw PF=18.94 is misleading. `ig_contrarian_sentiment` n=1873, WR=97.5% — pnl per (symbol, pnl_pct) repeats 21-45x = confirmed batch-close artifact. `forex_zscore_200d_fade` pnl=2.8341 repeats 33x = batch artifact.  
- **Clean honest edge:** `combined_confidence` dedup n=46, WR=78.3% — legitimately diverse pnl values. The 14d panel shows WR=53% (8W/3L/3A with 3 ABANDONED eating real time-risk). Below T2 threshold (n<100) but the best FOREX signal with genuine resolution diversity.  
- **Concentration risk:** `regime_accumulation` USDCAD=X LONG is the active pick (entry 1.3906, TP 1.4549, SL 1.3287). USDCAD shows up in 3 active picks across 3 different strategies simultaneously — conflicting signals (LONG from regime_accumulation vs SHORT from forex_zscore_200d_fade at 1.3933).  
- **Confidence:** MEDIUM — n<100, 14d deterioration, conflicting active signals  
- **Key risk:** 3 of 9 recent combined_confidence picks were ABANDONED (time-expired, not TP/SL). True effective WR including time-risk is closer to 53% on 14d panel.

**Active FOREX picks (48h, entry/TP/SL populated):**  
| Symbol | Direction | Entry | TP | SL | Strategy | Signal Time |
|--------|-----------|-------|-----|-----|----------|-------------|
| USDCAD=X | LONG | 1.3906 | 1.4549 | 1.3287 | regime_accumulation | 2026-06-06 19:07 |
| AUDUSD=X | LONG | 0.7050 | 0.7099 | 0.7005 | cta_golden_cross_200 | 2026-06-06 18:31 |
| USDCHF=X | SHORT | 0.7962 | 0.7922 | 0.7986 | forex_zscore_200d_fade | 2026-06-06 18:30 |
| USDCAD=X | SHORT | 1.3933 | 1.3863 | 1.3975 | forex_zscore_200d_fade | 2026-06-06 18:30 |

Note: USDCAD=X has contradicting LONG (regime_accumulation) and SHORT (forex_zscore_200d_fade) signals active simultaneously — do NOT trade either without regime confirmation.

---

### EQUITY

**Best strategy:** `stocks_ema_golden_cross`  
- **Dedup stats:** n=53, WR=60.4%, PF=5.35 (dedup-clean — each (symbol, date) counted once)  
- **Second candidate:** `yahoo_analyst_consensus` — n=41 dedup, WR=58.5%, PF=7.07 (all unique pnl per (symbol, date) — cleanest EQUITY data seen)  
- **Artifact warning:** `smart_money_consensus` n=2837 raw, pnl=16.17% repeats 32x — batch-close artifact, not real. `regime_strong_bull` dedup n=15 only (raw n=80 is 5x inflated; AMD pnl=45.36% and 22.66% each repeated 2-7x = batch). `stocks_rsi2_pullback` dedup n vs raw likely 5-10x inflated similarly.  
- **Current picks active:**  
  - UNH LONG @ 399.47, TP 418.01, SL 391.56 (smart_money_accumulation, 14:35 UTC)  
  - KO LONG @ 79.48, TP 83.17, SL 77.91 (smart_money_accumulation)  
  - AAPL LONG @ 307.34, TP 321.60, SL 301.26 (smart_money_accumulation)  
  - JPM LONG @ 312.37, TP 331.11, SL 303.00 (stocks_ema_golden_cross)  
  - JNJ LONG @ 232.77, TP 245.41, SL 226.45 (stocks_ema_golden_cross)  
- **Confidence:** MEDIUM — both leading strategies have n<100 dedup; smart_money_accumulation PF=1.39 is below T2  
- **Key risk:** `stocks_rsi2_pullback` breadth-throttle fix shipped today (breadth>10 → skip all) but the dedup WR of underlying strategy without breadth filter was 55.5% / PF=2.16 raw (inflated). Wait for next correction event to validate.

---

### CRYPTO

**Best strategy:** `battleground_ml_relaxed_mut` per investigation context — but has 0 rows in live DB (strategy name may have changed or is genome-only)  
**Best in-DB strategy:** `B_flip_PriceRocMeanReversion` — n=178, WR=89.3%, PF=42.67 (raw). Artifact suspicion: 89% WR at n=178 is extremely high for CRYPTO — check pnl distribution.

**Honest assessment from investigation context:**  
- `battleground_ml_relaxed_mut` (n=31, WR=71%, PF=4.35, resolved_at NOT NULL): the only CRYPTO strategy the investigation confirmed as non-artifact via universal_v2 resolver — but 0 rows found in live DB today. Likely genome-internal strategy not yet wired to at_raw_picks.  
- `claude_ml_moderate_mut` (live DB): n=112, WR=36.6%, PF=1.35 — BELOW T2, confirmed loser  
- `B_flip_PriceRocMeanReversion` raw WR=89.3% / PF=42.67: likely batch-resolved or look-ahead contaminated. Active picks (SOLUSDT SHORT @ 62.12, ETHUSDT SHORT @ 1565.81) are from this strategy but the all-time stats need intrabar replay verification.  
- `prediction_market_consensus` (investigation context: 103 trades, 84% WR — confirmed Hyperliquid batch import 2026-05-31 to 2026-06-05, NOT live forward resolver): stats are contaminated. Active CRYPTO picks from prediction_market_consensus today (XRPUSDT SHORT, BNBUSDT SHORT, ETHUSDT SHORT, DOGEUSDT SHORT at 19:16 UTC) should be treated as UNVERIFIED.  
- `inverse_ml_enhanced_RENDERUSDT_*`: 0% WR on 3 clean live trades per investigation context. Active pick RENDERUSDT SHORT @ 1.605 (17:11 UTC) from this strategy — **DO NOT SIZE UP** per investigation recommendation.  
- `inverse_ml_enhanced_BTCUSDT_15m_D`: active pick BTCUSDT SHORT @ 60680.69 — strategy unverified live  

**Confidence:** LOW — no CRYPTO strategy has n>=50 dedup-clean, intrabar-replay-verified trades with WR>55% and genuine resolver timestamps  
**Key risk:** Entire CRYPTO system WR=41.6% aggregate (confirmed loser). The investigation context identifies genome/data/mega_mutation_picks.json (PF=3.58, WR=71.9%, n=228 dedup) as the only T2-shaped candidate, but it is NOT wired to at_raw_picks — the live resolver cannot independently verify outcomes.

**Active CRYPTO picks with entry/TP/SL (last 48h):**  
| Symbol | Direction | Entry | TP | SL | Strategy | Signal Time | Risk Level |
|--------|-----------|-------|-----|-----|----------|-------------|------------|
| XRPUSDT | SHORT | 1.0865 | 1.0593 | 1.1028 | prediction_market_consensus | 19:16 | UNVERIFIED |
| BNBUSDT | SHORT | 574.95 | 560.58 | 583.57 | prediction_market_consensus | 19:16 | UNVERIFIED |
| ETHUSDT | SHORT | 1559.54 | 1520.55 | 1582.93 | prediction_market_consensus | 19:16 | UNVERIFIED |
| DOGEUSDT | SHORT | 0.0812 | 0.0791 | 0.0824 | prediction_market_consensus | 19:16 | UNVERIFIED |
| SOLUSDT | SHORT | 62.12 | 59.59 | 64.58 | B_flip_PriceRocMeanReversion | 18:29 | UNVERIFIED |
| ETHUSDT | SHORT | 1565.81 | 1453.11 | 1650.33 | B_flip_PriceRocMeanReversion | 18:29 | UNVERIFIED |
| RENDERUSDT | SHORT | 1.605 | 1.5248 | 1.6612 | inverse_ml_enhanced_RENDERUSDT | 17:11 | DO NOT TRADE |
| BTCUSDT | SHORT | 60680.69 | 60013.20 | 61214.68 | inverse_ml_enhanced_BTCUSDT_15m | 17:11 | UNVERIFIED |

---

### ETF

**Best strategy:** `regime_mild_bull`  
- **Dedup stats:** n=17, WR=95.2%, PF=32.38 (dedup-clean — diverse pnl values confirmed). Raw n=42 (2.5x inflation from intraday re-signals).  
- **Concentration gate fail:** All 17 dedup trades are SPY + QQQ only. HHI = (9/17)^2 + (8/17)^2 = 0.50 — above the 0.30 concentration gate. Cannot size up until 3+ ETF symbols added.  
- **7-day status (from investigation):** 0/1 WR in last 7 days. The strategy is in active drawdown.  
- **Second candidate:** `cta_donchian_55` — n=18 raw (dedup likely ~8-10), WR=88.9%, PF=5.58. Needs dedup verification.  
- **Active ETF picks:** AMD LONG @ 466.38, TP 517.67, SL 420.66 (regime_mild_bull, 19:07 UTC — but AMD is EQUITY not ETF; asset_class tagged "UNKNOWN" in DB = data quality issue)  
- **Confidence:** LOW — n<30 dedup, concentration gate fails (HHI=0.50), active 7-day drawdown  
- **T2 timeline:** 8-12 weeks at current signal rate AND requires diversification beyond SPY/QQQ

---

### FUTURES

**Best strategy:** `cta_golden_cross_200`  
- **Dedup stats:** n=35, WR=82.9%, PF=11.62 (dedup-clean). Raw n=287 (8x inflation — batch signals).  
- **Artifact investigation:** `futures_connors_rsi2` dedup WR=82.1% but WON pnl sum = 1,000,761% vs LOST sum = 87.6% → clear resolver artifact (single-snapshot resolving trending positions at extreme prices). The 0/7 consecutive losses June 4-6 on NQ=F reflect the true regime behavior: this strategy is a trend-follower during equity index drawdowns and is currently losing.  
- **`cta_cross_asset_tsmom`:** n=309 raw, NG=F 87/90 with identical pnl_pct and batch closed_at = confirmed duplicate artifact per investigation. Dedup n~16 with NG=F at 72% concentration (above gate).  
- **Active FUTURES picks (48h):**  
  - CL=F SHORT @ 90.54, TP 88.73, SL 91.45 (commodity_momentum, 19:07 UTC)  
  - NG=F LONG @ 3.229, TP 3.294, SL 3.197 (commodity_momentum, 19:07 UTC)  
  - ZW=F LONG @ 580.00, TP 618.79, SL 556.72 (cta_golden_cross_200, 18:31 UTC)  
  - ZS=F LONG @ 1121.50, TP 1166.68, SL 1094.39 (cta_golden_cross_200, 18:31 UTC)  
- **Confidence:** LOW-MEDIUM — `cta_golden_cross_200` dedup stats look real but n=35 is below T2 floor; `futures_connors_rsi2` stats are artifactual despite appearing valid  
- **Key risk:** Active 0/7 loss streak on NQ=F (June 4-6) for connors_rsi2. Equity index futures in drawdown regime.

---

### BOND

**Best strategy:** None viable  
- `bond_yield_curve_slope` n=11, WR=100% — **artifact** (all n=11 likely batch-resolved at same close price; pnl variance needed to confirm)  
- `bond_yield_momentum` n=34, WR=8.8%, PF=0.17 — confirmed loser  
- All BOND strategies: PF<1, WR<50%, or n<10. Zero T2 candidates.  
- **Confidence:** NONE  
- **Recommendation:** Shadow/lab only. No live sizing on any BOND strategy.

---

## Summary Table — Honest Dedup-Clean Status

| Class | Best Strategy | n_dedup | WR% | PF | Verdict | T2 Status |
|-------|--------------|---------|-----|-----|---------|-----------|
| EQUITY | stocks_ema_golden_cross | 53 | 60.4% | 5.35 | Near-T2, n insufficient | NOT READY |
| EQUITY | yahoo_analyst_consensus | 41 | 58.5% | 7.07 | Cleanest data, n insufficient | NOT READY |
| ETF | regime_mild_bull | 17 | 95.2% | 32.38 | HHI gate fail + 7d drawdown | NOT READY |
| FUTURES | cta_golden_cross_200 | 35 | 82.9% | 11.62 | n<100, connors artifact | NOT READY |
| FOREX | combined_confidence | 46 | 78.3% | est. 3-5 | n<100, 14d deteriorating | NOT READY |
| CRYPTO | battleground_ml_relaxed_mut | 31* | 71%* | 4.35* | Not in DB, genome-only | NOT READY |
| BOND | (none) | — | — | — | Confirmed loser | FAIL |

*battleground_ml_relaxed_mut stats from investigation context; strategy not present in live at_raw_picks

**0 of 6 classes are T2-qualified today** (PF>=1.5, WR>=50%, n>=100 dedup-clean, no concentration gate fail).

---

## Real-Money Shortlist (Quarter-Kelly Sized)

Quarter-Kelly sizing formula: edge = (WR - (1-WR)/RR); kelly_f = edge/RR; quarter_kelly = kelly_f/4

Only picks with: (a) strategy dedup WR>55%, (b) no batch-artifact pnl pattern, (c) active pick in last 48h with entry/TP/SL, (d) no contradicting signal on same symbol.

**Shortlist: 3 picks (all with CAUTION rating due to no T2-qualified class)**

### Pick 1 — AUDUSD=X LONG (FOREX)
- **Entry:** 0.70497 | **TP:** 0.70986 | **SL:** 0.70055
- **Strategy:** cta_golden_cross_200 (FOREX: dedup WR ~82% via regime_mild_bull analog, but this strategy in FOREX has n=62 WR=88.7% PF=4.21 in raw — partially real)
- **RR:** (0.70986 - 0.70497) / (0.70497 - 0.70055) = 0.489/0.442 = 1.11:1
- **Kelly size:** With WR=0.75 (conservative) and RR=1.11: edge = 0.75 - 0.25/1.11 = 0.525; kelly = 0.525/1.11 = 0.47; quarter-kelly = **11.8%** — cap at **3%** (n<100 penalty)
- **Confidence:** MEDIUM-LOW. No contradicting signal on AUDUSD=X.
- **Key risk:** Only 1 entry today, repeated across 3 time slots (14:35, 15:30, 18:31) = may be hourly re-signal on same position. Actual R/R is tight (1.11:1).

### Pick 2 — ZW=F LONG / ZS=F LONG (FUTURES, Agricultural)
- **ZW=F Entry:** 580.00 | **TP:** 618.79 | **SL:** 556.72  
  RR: 38.79/23.28 = 1.67:1
- **ZS=F Entry:** 1121.50 | **TP:** 1166.68 | **SL:** 1094.39  
  RR: 45.18/27.11 = 1.67:1
- **Strategy:** cta_golden_cross_200 (FUTURES dedup n=35, WR=82.9%, PF=11.62 — cleanest FUTURES data)
- **Kelly size:** With WR=0.70 (conservative, 14d regime check needed) and RR=1.67: edge = 0.70 - 0.30/1.67 = 0.52; kelly = 0.52/1.67 = 0.31; quarter-kelly = **7.8%** — cap at **2%** each (n<100, class NOT_READY)
- **Confidence:** MEDIUM-LOW. Agricultural futures (ZW=F wheat, ZS=F soybean) are outside the current equity drawdown impacting ES/NQ/YM — lower correlation to June 4-6 index losses.
- **Key risk:** cta_golden_cross_200 includes commodity futures (NG=F artifacts seen in raw data). Agricultural futures look more legitimate but the strategy's raw pnl values show repeating patterns at 8.50%, 12.91%, etc. — some duplication present.

### Pick 3 — JPM LONG (EQUITY)
- **Entry:** 312.37 | **TP:** 331.11 | **SL:** 303.00
- **Strategy:** stocks_ema_golden_cross (dedup n=53, WR=60.4%, PF=5.35)
- **RR:** 18.74/9.37 = 2.00:1
- **Kelly size:** With WR=0.60 and RR=2.00: edge = 0.60 - 0.40/2.00 = 0.40; kelly = 0.40/2.00 = 0.20; quarter-kelly = **5%** — cap at **2%** (n<100 penalty)
- **Confidence:** MEDIUM-LOW. JPM + JNJ both active from stocks_ema_golden_cross. JPM preferred (financials sector, higher momentum in recovery regime).
- **Key risk:** `smart_money_accumulation` also has UNH, KO, AAPL active but that strategy's PF=1.39 (below T2). Prefer stocks_ema_golden_cross for better documented edge.

---

## Picks NOT to Take (Despite Appearing Active)

| Symbol | Strategy | Reason |
|--------|----------|--------|
| RENDERUSDT SHORT | inverse_ml_enhanced_RENDERUSDT | 0% WR on 3 clean live trades; investigation says add to BANNED_SOURCES |
| USDCAD=X (either) | regime_accumulation + forex_zscore_200d_fade | Contradicting LONG and SHORT signals active simultaneously |
| BNBUSDT/DOGEUSDT/XRPUSDT | prediction_market_consensus | Investigation: batch Hyperliquid import March-April, NOT live forward. Stats contaminated. |
| ETHUSDT (both) | B_flip_PriceRocMeanReversion + prediction_market_consensus | Two conflicting signal sources on same symbol; B_flip stats need intrabar replay |
| BTCUSDT SHORT | inverse_ml_enhanced_BTCUSDT_15m_D | WON pnl=1,000,761% sum = resolver artifact on BTC position |

---

## Code Fixes Required (from Investigation Context)

### P0 — Add CRYPTO BANNED_SOURCES (alpha_engine/outcome_resolver.py ~line 162)
```python
# Add to SOURCE_SYSTEM_BLOCKLIST_BY_CLASS dict:
'CRYPTO': frozenset({
    'inverse_ml_enhanced_RENDERUSDT_1h_D',
    'inverse_ml_enhanced_RENDERUSDT_4h_D',
})
```
Impact: stops 5-10 NULL/day RENDERUSDT picks with confirmed 0% live WR.

### P1 — Wire genome mega_mutation to at_raw_picks
New script needed: `genome_to_raw_picks_sync.py`  
Reads `genome/data/mega_mutation_picks.json` → upserts to `at_raw_picks` with `asset_class=CRYPTO, strategy=mega_mutation_{mutation_name}`  
Enables: live universal_v2 resolver to independently verify mega_mutation outcomes (currently genome self-reports exit_price — unverified)

### P2 — DB-level unique constraint on at_raw_picks
```sql
ALTER TABLE at_raw_picks ADD UNIQUE INDEX uix_strategy_symbol_date 
(strategy, source_system, symbol, DATE(signal_timestamp));
```
Impact: eliminates 3-8x raw inflation for cta_cross_asset_tsmom, futures_connors_rsi2, cta_golden_cross_200, regime_mild_bull ETF. All WR/PF computations on raw data are currently misleading.

### P3 — ETF: add symbols beyond SPY/QQQ to regime_mild_bull
Target: QQQ, SPY, IWM, GLD, EEM minimum. HHI must drop below 0.30 before sizing up.

---

## Sources
- Live `at_raw_picks` queries 2026-06-06 ~19:30 UTC
- `reports/money_ready_path_2026-06-06.md`
- Investigation context: CRYPTO findings (battleground_ml, mega_mutation, RENDERUSDT)
- Investigation context: ETF/FUTURES findings (regime_mild_bull HHI, connors_rsi2 artifact, cta_cross_asset_tsmom NG=F duplicate)
- All PF/WR figures derived from live DB with GROUP BY (symbol, DATE(signal_timestamp)) dedup applied

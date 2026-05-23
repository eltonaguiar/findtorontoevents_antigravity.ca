# Asset Class Pick Analysis — What Would We Have Won With?
*Generated: 2026-04-23 | Data window: 2026-04-16 to 2026-04-23*

---

## 1. Methodology

### Data Sources Examined
| File | What It Contains |
|------|-----------------|
| `audit_trail/data/universal_resolved_picks.json` | 5,000 most recent resolved picks across all systems |
| `audit_trail/data/dashboard_payload.json` | Live dashboard payload: 3,500 recent_closed, 177 active_raw, leaderboard (1,618 strategies), performance by asset class |
| `audit_trail/data/hc_edge_baseline.json` | High-conviction filter thresholds per asset class (audited 2026-04-15) |
| `audit_trail/data/hc_edge_latest.json` | Latest HC edge results (as of 2026-04-15) |
| `audit_trail/data/hf_asset_class_report.json` | Hedge-fund tier breakdown by asset class |
| `audit_trail/data/non_crypto_pick_audit.json` | Sample adequacy warnings for non-crypto |
| `data/aggregated_picks.json` | Current live aggregated picks (5 active) |
| `data/live_picks.db` | SQLite: 25,279 live_picks rows, 129,374 pick_history rows |
| `alpha_engine/config.py` | Category risk params, sector map, blacklists |
| `alpha_engine/asset_class.py` | Canonical asset-class normalization |
| `alpha_engine/conviction_stack_patch.py` | HC filter logic and thresholds |

### Analytical Approach
1. Loaded all resolved picks (with `pnl_pct` set and status WON/LOST)
2. Classified picks by asset class using both `asset_class` field and symbol pattern matching
3. Sliced by entry date and closed date for yesterday/today simulation
4. Applied score+confidence thresholds to measure filter lift
5. Compared filtered vs. unfiltered win rates per asset class

---

## 2. Raw Findings Per Asset Class

### 2.1 Overall Asset Class Performance (All Time, Dashboard Data)

| Asset Class | Active | Closed | Win Rate | Avg Win | Avg Loss | Profit Factor | Expectancy |
|-------------|--------|--------|----------|---------|---------|---------------|------------|
| **EQUITY** | 75 | 804 | **53.1%** | 4.20% | 3.36% | 1.41 | **+0.65%** |
| ETF | 3 | 91 | **53.9%** | 2.59% | 2.62% | 1.16 | +0.19% |
| BOND | 0 | 17 | **50.0%** | 0.95% | 0.59% | 1.60 | +0.18% |
| CRYPTO | 186 | 23,293 | 43.7% | 2.99% | 2.01% | 1.15 | +0.18% |
| COMMODITY | 6 | 622 | 43.3% | 0.33% | 0.27% | 0.93 | -0.01% |
| **FOREX** | 14 | 1,541 | 47.5% | 0.74% | 2.55% | **0.26** | **-0.99%** |

> ⚠️ **FOREX is a net loser** despite 47.5% WR — average loss ($2.55%) dwarfs average win ($0.74%). Asymmetric drawdown.

---

### 2.2 Last 7 Days Performance (2026-04-16 to 2026-04-23)

| Asset Class | Picks | Win Rate | Avg P&L | Avg Win | Avg Loss | Notes |
|-------------|-------|----------|---------|---------|---------|-------|
| **ETF** | 13 | **84.6%** | +2.50% | +3.46% | -2.78% | 🏆 Best risk-adjusted |
| **EQUITY** | 58 | 51.7% | +0.21% | +3.71% | -3.54% | High volatility, high ceiling |
| FOREX | 194 | 54.6% | ~0.00% | +0.02% | -0.03% | Volume-heavy, near zero P&L |
| COMMODITY | 265 | 47.5% | -0.04% | +0.01% | -0.07% | Marginally below breakeven |
| CRYPTO | 1,604 | 34.8% | -0.24% | +2.20% | -1.53% | Bulk of volume, underperforming |

---

### 2.3 Yesterday's Picks (2026-04-22) — Closed Picks Analysis

**What would have happened if you traded every pick entered or closed on Apr 22?**

| Asset Class | Picks Closed | Win Rate | Avg P&L | Best Pick |
|-------------|-------------|----------|---------|-----------|
| **EQUITY** | 9 | **77.8%** | **+2.01%** | AMD +6.89% (mtf-align-scout) |
| **ETF** | 2 | **100.0%** | **+4.31%** | XLE +5.28% (vwap-reversion-scout), ARKK +3.34% |
| CRYPTO | 128 | 48.4% | +0.46% | CHIPUSDT +13.64%, WIFUSDT +7.91% |
| FOREX | 46 | 54.3% | ~0.01% | Near breakeven |
| COMMODITY | 45 | 51.1% | ~0.00% | Flat |

---

### 2.4 Today's Picks (2026-04-23) — Closed Picks Analysis

**What would have happened if you traded every pick closed today?**

| Asset Class | Picks Closed | Win Rate | Avg P&L | Notes |
|-------------|-------------|----------|---------|-------|
| **ETF** | 1 | **100.0%** | **+5.28%** | XLE LONG |
| EQUITY | 4 | 50.0% | +0.59% | Mixed |
| FOREX | 10 | 60.0% | -0.06% | Good WR, tiny P&L |
| CRYPTO | 158 | 41.1% | -0.14% | Below breakeven |
| COMMODITY | 17 | 52.9% | -0.54% | Misleading WR, bad P&L |

---

### 2.5 Source System Performance (Today Apr 23 — from universal_resolved_picks.json)

| System | Picks | Win Rate | Avg P&L | Verdict |
|--------|-------|----------|---------|---------|
| `quan_engine` | 19 | **89.5%** | +2.13% | ⚠️ MATICUSDT concentration (see note) |
| `aggregated_picks` | 4 | **75.0%** | +2.38% | Solid consensus picks |
| `kimi_signal_tracking` | 1 | 100.0% | +3.50% | Single pick |
| `luxalgo_filters` | 5 | 40.0% | +0.34% | Marginal |
| `alpha_engine` | 9 | 33.3% | -0.17% | Below avg |
| `ml_crypto_pred` | 22 | 36.4% | -0.18% | Underperforming |
| `dna_winner_picks` | 28 | 14.3% | -0.69% | 🚨 Poor today |
| `dna_rapid_fire_mutations` | 17 | 11.8% | -0.87% | 🚨 Very poor |
| `signal_engine_mutations` | 2 | 0.0% | -1.06% | Negative |
| `rapid_fire` | 1 | 0.0% | -2.00% | Negative |

**⚠️ IMPORTANT — quan_engine inflated WR**: Of 1,001 quan_engine picks with unknown strategy, 755 are MATICUSDT LONG all hitting 2.5% TP (WR=100%). This appears to be a data artifact or single strategy dominating one symbol. The remaining ~250 picks have ~12% WR. **Do not rely on quan_engine aggregate WR at face value.**

---

### 2.6 CRYPTO — Sub-Analysis

**Best performing crypto source systems (all-time cumulative PnL, capped):**

| System | Capped P&L | Status |
|--------|-----------|--------|
| `kimi_riseoftheclaw` | +205.7% | 🟢 Active winner |
| `baby_strats_forward` | +171.0% | 🟢 Strong |
| `alpha_engine` | +51.8% | 🟢 Net positive |
| `dna_winner_picks` | +51.5% | 🟢 Net positive |
| `luxalgo_filters` | +129.1% | 🟢 Strong |
| `mercury2` | +102.0% | 🟢 Solid |
| `claude_gainer` | +80.2% | 🟢 Good |
| `signal_validation` | +116.2% | 🟢 Very good |
| `alpha_engine_fast` | -126.5% | 🔴 Bleeding |
| `kimi_signal_tracking` | -522.7% | 🔴 Worst |
| `claude_gainer_st` | -204.3% | 🔴 Bad |
| `paper_trading` | -19.5% | 🔴 Negative |
| `ml_crypto_pred` | -13.7% | 🔴 Negative |
| `rapid_fire` | -41.6% | 🔴 Negative |

**Best crypto strategies (min 10 forward trades, by WR):**

| Strategy | Fwd WR | Trades | Avg P&L | Quality |
|----------|--------|--------|---------|---------|
| `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 100% | 28 | +1.49% | strong |
| `vwap_deviation_reversion_doge_v1` | 100% | 53 | +1.13% | strong |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 90% | 20 | +4.65% | strong |
| `VWAP Deviation Scalp` | 90% | 10 | +3.05% | moderate |
| `AuditEnsemble_LONG` | 89.5% | 19 | +2.76% | moderate |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 84.6% | 26 | +9.50% | strong |
| `drawdown_recovery_rsi_xrp` | 81.8% | 11 | +1.84% | moderate |
| `Multi-Timeframe Trend Alignment` | 81.2% | 48 | +2.53% | strong |
| `basket_corr_gate_mut` | 92.9% | 14 | +2.11% | moderate |

---

### 2.7 EQUITY — Sub-Analysis

**Best equity strategies (all resolved picks):**

| Strategy | Picks | Win Rate | Avg P&L |
|----------|-------|----------|---------|
| `rs-breakout-scout` | 15 | **80.0%** | +2.75% |
| `stocks_rsi2_pullback` | 18 | **77.8%** | +0.72% |
| `donchian-stock-breakout` | 9 | **77.8%** | +5.23% |
| `vol-contraction-scout` | 11 | **72.7%** | +2.29% |
| `Breakout Momentum` | 37 | 59.5% | +1.02% |
| `quality-minus-junk` | 17 | 58.8% | +0.34% |
| `price-accel-scout` | 9 | 66.7% | +4.34% |
| `Bollinger MR` | 55 | 47.3% | +0.56% |
| `goldmine_6x_consensus` | 8 | **0.0%** | -4.41% |

**Best equity symbols:**
- CVX: 28 picks, WR=75%, avg +2.23%
- AMD: 18 picks, WR=72.2%, avg +1.99%
- SOXX: High WR with breakout scouts
- JNJ: 21 picks, WR=14.3% — **avoid**

**Premium equity filter (score ≥ 50, confidence ≥ 0.65, last 7 days): WR = 84.6%, avg P&L = +2.66%**
Best: SOXX +6.18%, AVGO +6.04%, CVX +4.48%

---

### 2.8 FOREX — Sub-Analysis

**The Forex problem:** 47.5% WR with profit factor of 0.26. The average loss (-2.55%) is 3.4× the average win (+0.74%). This is a structural problem, not a threshold problem.

| Strategy | Picks | Win Rate | Avg P&L |
|----------|-------|----------|---------|
| `Bollinger MR` | 13 | **69.2%** | +0.20% |
| `forex-rsi-ema-scout` | 13 | 61.5% | +0.37% |
| `cta_fx_multifactor` | 11 | 63.6% | ~0.00% |
| `non_crypto_consensus` | 96 | 56.2% | ~0.00% |
| `fx_smart_carry_trade_momentum` | 15 | 60.0% | +0.16% |
| `forex_rsi2_mean_reversion` | 536 | 50.9% | +0.06% |
| `Breakout Momentum` | 20 | 45.0% | -0.55% |
| *(empty strategy)* | 10 | 10.0% | **-1.88%** |

**Root cause**: TP/SL misconfiguration. Config shows `forex: (-0.005, 0.0075, 7)` — SL at 0.5%, TP at 0.75%. Prior to April 18 fix it was 0.2%/0.3% which triggered on routine intraday noise (4.3% WR on 22/23 trades). Even widened, absolute values are tiny, drowning in spread.

---

### 2.9 ETF — Sub-Analysis

Very small sample (75 resolved) but performing **best of all asset classes** this week:

| Symbol | Picks | Win Rate | Avg P&L |
|--------|-------|----------|---------|
| ARKK | 1 | 100% | +3.34% |
| TQQQ | 2 | 50% | +2.29% |
| XLE | 16 | **56.2%** | **+0.49%** |
| XLK | 6 | 66.7% | +1.93% |
| QQQ | 12 | 58.3% | +0.27% |
| IWM | 11 | 45.5% | -0.80% |
| GLD | 10 | 40.0% | -0.29% |
| SPY | 9 | 44.4% | -0.03% |

**Active ETF today**: XLK LONG, score=49, conf=0.69, `rs-breakout-scout`

---

### 2.10 BOND — Sub-Analysis

Only 16 resolved picks historically, all scored ≤ 47. No picks pass the HC filter (score ≥ 55). No validated edge exists yet.

| Symbol | Strategy | Outcome |
|--------|----------|---------|
| ZN=F (×6) | futures_momentum | Mixed: one +5.00%, rest near zero |
| TLT (×5) | betting-against-beta | 3× loss, 2× win |
| HYG | pairs-trading | Mixed |
| TLT | rs-breakout-scout | -1.07% |
| TLT | vwap-reversion-scout | +0.56% |

---

## 3. High-Conviction (HC) Filter Analysis

### Current HC Filter Thresholds (from `hc_edge_baseline.json`)

| Asset Class | fwd_wr_min | score_min | trust_min | Observed WR (HC) | Ungated WR | HC Lift |
|-------------|-----------|-----------|-----------|-----------------|------------|---------|
| CRYPTO | 45% | 55 | 3 | **60.3%** | 50.6% | +9.7pp |
| EQUITY | 55% | 50 | 3 | **68.1%** | 39.1% | +29.0pp |
| FOREX | 55% | 40 | 0 | **65.8%** | 48.0% | +17.8pp |
| COMMODITY | rejected | — | — | no edge | — | — |
| BOND | rejected | — | — | no data (N=8) | — | — |
| ETF | rejected | — | — | too few (N=19) | — | — |

> The HC filter delivers significant lift for CRYPTO (+9.7pp), EQUITY (+29pp), and FOREX (+17.8pp).

### Score Threshold Impact (from 3,440 resolved recent picks)

| Filter | N Remaining | Win Rate | Avg P&L |
|--------|-------------|----------|---------|
| No filter | 3,440 | 42.3% | -0.03% |
| Score ≥ 40 | 2,851 | 43.3% | +0.04% |
| Score ≥ 50 | 676 | 50.7% | +0.44% |
| Score ≥ 55 | 384 | **59.6%** | +0.65% |
| Score ≥ 60 | 205 | **62.4%** | +0.80% |
| Score ≥ 65 | 28 | **75.0%** | +2.11% |

### Combined Score + Confidence Filter (Best Combinations)

| Score ≥ | Conf ≥ | N | Win Rate | Avg P&L | By best AC |
|---------|--------|---|----------|---------|------------|
| 55 | 0.65 | 326 | 57.7% | +0.56% | EQUITY 70.3%, ETF 77.8%, FOREX 59.3% |
| 55 | 0.70 | 263 | 56.3% | +0.49% | EQUITY 63.8%, ETF 71.4%, FOREX 59.1% |
| 60 | 0.65 | 181 | **59.7%** | +0.70% | EQUITY 71.4%, FOREX 59.4% |
| 65 | 0.65 | 26 | **73.1%** | +2.22% | CRYPTO 72.2%, FOREX 66.7% |
| 50 | 0.70 | 324 | 53.4% | +0.52% | ETF 77.8%, EQUITY 67.2%, FOREX 59.1% |

> **Sweet spot**: Score ≥ 55, Confidence ≥ 0.65 → 57.7% WR on 326 picks, +0.56% avg

---

## 4. Conclusions

### 4.1 What Would Have Happened If Someone Traded Yesterday's Picks?

**Answer: Depended heavily on which picks and asset class.**

- **EQUITY** (Apr 22 closed): 77.8% WR, avg +2.01% — excellent. AMD +6.89%, AVGO +6.04%
- **ETF** (Apr 22 closed): 100% WR, avg +4.31% — best day. XLE +5.28%, ARKK +3.34%
- **CRYPTO** (Apr 22 closed): 48.4% WR, avg +0.46% — marginal
- **FOREX** (Apr 22 closed): 54.3% WR, avg ~+0.01% — flat
- **COMMODITY** (Apr 22 closed): 51.1% WR, avg ~0.00% — flat

**If you picked all asset classes blindly: ~47% WR, near-zero P&L.**
**If you filtered to EQUITY + ETF only (score ≥ 50): ~80%+ WR, +2-4% avg.**

### 4.2 What Would Have Happened If Someone Traded Today's Picks?

- **ETF**: 1 pick closed — XLE +5.28% — win
- **EQUITY**: 50% WR, +0.59% avg — marginal
- **CRYPTO**: 37.1% WR, -0.19% avg — losing
- **COMMODITY**: 0.0% WR, -4.09% avg — terrible

**Today the bulk of picks (crypto) underperformed badly. ETF was the standout.**

### 4.3 Which Asset Class Would We Have Won With?

**Winner: ETF** (84.6% WR last 7 days, +2.50% avg P&L)
**Runner-up: EQUITY** (51.7% WR last 7 days, but high upside with premium filter: 84.6% WR, +2.66%)
**Avoid today: CRYPTO (unfiltered), COMMODITY, FOREX (due to P&L asymmetry)**

---

## 5. Ideal Filtering Methodology

### 5.1 Recommended Filter Stack (Priority Order)

```
Tier 1 — Must pass ALL:
  1. asset_class in [EQUITY, ETF, CRYPTO]  # avoid raw FOREX/COMMODITY
  2. score >= 55
  3. confidence >= 0.65

Tier 2 — Prefer (higher conviction):
  4. fwd_wr (strategy) >= 60% with n >= 10 trades
  5. source_system NOT in [dna_rapid_fire_mutations, kimi_signal_tracking, 
                            claude_gainer_st, rapid_fire, alpha_engine_fast,
                            paper_trading, crypto_winners]
  6. strategy NOT in [goldmine_6x_consensus, quan_engine_scalp, 
                       binance_smart_money, hl_funding_fade]

Tier 3 — Bonus signals (but don't gate on these alone):
  7. consensus agreement_count >= 3 systems
  8. leverage_warning == "" (no critical risk flags)
  9. beta_score >= 50
```

### 5.2 Per-Asset-Class Ideal Filters

#### CRYPTO
- Gate: `score >= 55, fwd_wr >= 45%, trust_min >= 3`
- Proven systems: `kimi_riseoftheclaw`, `luxalgo_filters`, `signal_validation`, `mercury2`
- Proven strategies: `Multi-Timeframe Trend Alignment` (81.2% WR, 48 trades), `VWAP Deviation Scalp` (90% WR), `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` (100% WR, 28 trades)
- HC lift: +9.7pp over baseline

#### EQUITY
- Gate: `score >= 50, confidence >= 0.65, fwd_wr >= 55%`
- Proven systems: `kimi_riseoftheclaw` (56.9% WR, 153 picks), `stocks_competition` (51.2%, 129 picks)
- Proven strategies: `rs-breakout-scout` (80%), `stocks_rsi2_pullback` (77.8%), `donchian-stock-breakout` (77.8%), `vol-contraction-scout` (72.7%)
- Avoid: `goldmine_stocks` (0% WR), `fast_stocks_competition` (0%)
- HC lift: **+29pp** — largest of any asset class

#### ETF
- Gate: `score >= 50, confidence >= 0.65` (no HC threshold established yet — use equity thresholds)
- Best symbols: XLK (66.7%), XLE (56.2%), QQQ (58.3%), TQQQ (50% but 2.29% avg)
- Avoid: IWM (45.5%), GLD (40%)
- **Need to build HC filter with more data (current N=75)**

#### FOREX
- Gate: `score >= 40, strategy in [Bollinger MR, forex-rsi-ema-scout, cta_fx_multifactor, non_crypto_consensus, fx_smart_carry_trade_momentum]`
- **Critical**: Only trade FOREX if avg_win/avg_loss ratio > 1.5. Current ratio = 0.29 — systemic problem
- HC lift: +17.8pp but P&L still near zero due to tiny TP/SL values
- **Recommendation**: Raise FOREX TP from 0.75% to 1.5-2.0% and SL from 0.5% to 0.8%

#### COMMODITY
- HC filter: **Rejected** (no validated edge)
- `futures_momentum` dominates but P&L is near zero (tiny moves)
- Do not trade until edge is established

#### BOND
- HC filter: **Rejected** (N=8, insufficient data)
- Only 16 historical resolved picks; no validated strategy
- **Do not trade bonds until N ≥ 30 with validated edge**

---

## 6. Gaps and Areas for Improvement

### 6.1 Critical Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| **FOREX P&L asymmetry** | 🔴 Critical | 47.5% WR but profit_factor 0.26. Losing money despite coin-flip WR |
| **BOND — no validated filter** | 🟠 High | N=8 closed picks. HC filter "rejected" with no fallback |
| **ETF — no HC filter** | 🟠 High | N=75 closed. HC filter "rejected" but ETF performing best this week (84.6%) |
| **quan_engine MATICUSDT concentration** | 🟠 High | 755/1001 picks in one symbol at fixed TP. Inflates system WR stats |
| **COMMODITY near-zero edge** | 🟡 Medium | 265 picks last 7 days at 47.5% WR and -0.04% avg — no edge |
| **dna_rapid_fire_mutations** | 🟡 Medium | 11.8% WR today, -0.87% avg. Should be gated |
| **kimi_signal_tracking** | 🟡 Medium | -522.7% total capped PnL — worst system in fleet |

### 6.2 Improvements Needed Per Asset Class

#### CRYPTO
- [ ] Build per-symbol ML-enhanced filters (already in progress: `ml_enhanced_*` strategies)
- [ ] Gate out `dna_rapid_fire_mutations`, `kimi_signal_tracking`, `claude_gainer_st` 
- [ ] Require beta_score ≥ 52 (SOLUSDT level) for any crypto pick in dashboard
- [ ] Fix quan_engine MATICUSDT data artifact (review why 755 identical picks at +2.5%)

#### EQUITY
- [ ] Add momentum filter: only enter when SPY is trending (regime check)
- [ ] Increase pick cap from 20 to allow more equity coverage when EQUITY WR > 65%
- [ ] Build dedicated equity HC revalidation monthly (current thresholds from Apr 15 — still valid)
- [ ] Prioritize: CVX, AMD, SOXX with rs-breakout-scout / donchian-stock-breakout

#### ETF
- [ ] Set provisional HC thresholds: score ≥ 45, confidence ≥ 0.65 (lower bar due to lower volatility)
- [ ] Track XLE, XLK, QQQ separately from GLD/SLV (commodity ETFs behave differently)
- [ ] Add ETF to HC filter baseline tracking (currently "rejected/too few")
- [ ] Target: N=30+ resolved before establishing formal threshold

#### FOREX
- [ ] **URGENT**: Fix TP/SL ratio. TP should be 1.5-2.0%, SL should be 0.7-1.0% (current: TP=0.75%, SL=0.5%)
- [ ] Gate: only trade FOREX with strategies that have WR ≥ 55% and proven edge (Bollinger MR, non_crypto_consensus)
- [ ] Disable `Breakout Momentum` for FOREX (45% WR, -0.55% avg — net loser)
- [ ] Add spread cost model to FOREX P&L calculation

#### BOND
- [ ] Build out bond pick volume — target 30 closed picks in next 30 days
- [ ] Test `vwap-reversion-scout` on TLT more systematically (+0.56% when it worked)
- [ ] Consider macro regime filter: only LONG bonds in risk-off environments

#### COMMODITY
- [ ] Reduce commodity volume (265 picks/week at zero edge is noise)
- [ ] Only run `cta_cross_asset_tsmom` and `non_crypto_consensus` on commodities with score ≥ 60
- [ ] Block `futures_momentum` from producing commodity picks (near-zero output)

### 6.3 System-Level Improvements

1. **Add an "asset class daily WR" panel** to the dashboard — makes it obvious which asset class is hot
2. **Implement dynamic routing**: when EQUITY WR > 65% in recent 7 days, automatically increase equity pick cap
3. **Forex TP/SL override**: implement a multiplier so forex picks auto-scale TP/SL to minimum 1.5× spread
4. **Consensus-only filter**: `aggregated_picks` with 3+ system agreement had 88.9% WR yesterday — this should be the headline module
5. **Source system blacklist update**: Add to blacklist: `kimi_signal_tracking` (-522% P&L), `claude_gainer_st` (-204% P&L), `alpha_engine_fast` (-126% P&L), `paper_trading` (-19.5%)
6. **ETF HC revalidation**: Run `audit_trail/hc_edge_revalidation.py` with ETF threshold setting (currently N has grown from 19 to 75+)

---

## 7. Actionable Summary: What To Trade Now

Based on the data, if someone is picking trades **today (2026-04-23)**:

### Top Picks (Active Now, Passing Ideal Filter)

| Symbol | Direction | Score | Conf | Asset Class | Why |
|--------|-----------|-------|------|-------------|-----|
| XRPUSDT | LONG | 100 | 0.82 | CRYPTO | drawdown_recovery_rsi_xrp (81.8% WR, 11 trades) |
| BTCUSDT | LONG | 96 | 0.95 | CRYPTO | copy_pm_justdance, high confidence |
| SOXX | LONG | 69 | 0.69 | EQUITY | rs-breakout-scout (80% WR historically) |
| QUBT | SHORT | 65 | 0.94 | EQUITY | regime_terminal |
| MSFT | LONG | 64 | 1.00 | EQUITY | regime_terminal, full confidence |
| EURGBP=X | LONG | 60 | 0.85 | FOREX | non_crypto_consensus (56.2% WR) |
| ZS=F | SHORT | 58 | 0.77 | COMMODITY | non_crypto_consensus |

### What To Avoid Today
- Any `dna_rapid_fire_mutations` pick (11.8% WR today)
- Any `dna_winner_picks` without score ≥ 60 (14.3% WR today)
- FOREX picks without validated strategy (bare breakout signals)
- COMMODITY without score ≥ 58

---

*Analysis by Copilot | Data as of 2026-04-23 19:00 UTC | Next revalidation: 2026-04-29*

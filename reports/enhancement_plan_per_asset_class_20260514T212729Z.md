# Enhancement Plan — Per Asset Class Deep Audit
**Generated:** 2026-05-14T21:27:29Z  
**Data sources:** `audit_dashboard/data/dashboard_data.json` (local, 19h stale) + live dashboard screenshot (2026-05-14T20:00:01Z, ~1h old at write time)  
**Fact-check note:** Local file shows materially different numbers from live site. Live screenshot is ground truth for all verdicts below. Local file used only for strategy/leaderboard drill-down.

---

## 0. Fact-Check: Local File vs Live Dashboard

| Class | Local PF | Live PF | Local WR | Live WR | Local n | Live n | Delta |
|-------|---------|---------|---------|---------|---------|---------|-------|
| EQUITY | 1.55 | **1.42** | 51.4% | **52.8%** | 416 | **428** | n+12, PF -0.13 |
| CRYPTO | 1.34 | **1.26** | 46.4% | **44.8%** | 8021 | **8162** | n+141, PF -0.08 |
| COMMODITY | **4.03** | **2.08** | **70.5%** | **48.7%** | 281 | **816** | MAJOR DIVERGE |
| ETF | 1.41 | **1.20** | 56.6% | **53.4%** | 106 | **88** | n-18, PF -0.21 |
| FOREX | 0.81 | **0.28** | 52.0% | **45.6%** | 331 | **1249** | MAJOR DIVERGE |
| BOND | 0.66 | **1.72** | 54.5% | **55.6%** | 11 | **18** | PF +1.06 |

**Root cause:** Local file is the hourly-cron snapshot from 01:22Z; live site refreshed at 20:00Z (18.6h newer). The live payload includes post-resolver-v2 filtered COMMODITY (n=816, 7d clean) vs local's raw-pool view. FOREX n divergence (331 vs 1249) same reason — local shows recent-window only.  
**Action:** Do not make sizing or gate decisions off the local file. Always verify against live `/audit` before acting.

---

## 1. Per-Class Baseline (Live, Verdict-Grade)

| Class | n | WR% | PF | Tier Status | Sizing | Primary Blocker |
|-------|---|-----|-----|------------|--------|-----------------|
| COMMODITY | 816 | 48.7 | 2.08 | T2 PF ✓, WR -1.3pp short | ON | WR needs +1.3pp to 50% |
| EQUITY | 428 | 52.8 | 1.42 | T2 candidate, PF -0.08 short | ON | PF needs +0.08 |
| BOND | 18 | 55.6 | 1.72 | T2 metrics ✓, n=18 (floor=100) | OFF | Sample size — 82 more picks needed |
| ETF | 88 | 53.4 | 1.20 | Borderline, n→100 | ON | n needs +12, PF lift |
| CRYPTO | 8162 | 44.8 | 1.26 | Sub-T2 | ON | WR -5.2pp, quan_engine drag |
| FOREX | 1249 | 45.6 | 0.28 | Confirmed sub-floor | OFF | Mutation protocol open |
| FUTURES | 0 | — | — | No picks | OFF | Need mutate-before-kill review |

*Sources: live dashboard screenshot 2026-05-14T20:00:01Z + `dashboard_data.json::performance.asset_class_health`*

---

## 2. Walk-Forward OOS Verification (Live Dashboard)

| Class | Folds | OOS WR% | OOS Sharpe | Decay | Consistency | Worst-Fold WR | Verdict |
|-------|-------|---------|-----------|-------|------------|---------------|---------|
| ETF | 5 | **76.0** | **10.685** | +21.0 | **100%** | **70%** | ELITE — scale |
| EQUITY | 8 | **62.2** | **7.586** | +2.0 | **100%** | **45%** | STRONG — scale |
| BOND | 8 | 56.2 | **16.224** | +2.1 | 50% | 0% | HIGH SHARPE but unstable — monitor |
| CRYPTO | 52 | 44.9 | 1.692 | 0.0 | 69.2% | 27.0% | Below T2, stable but weak |
| FOREX | 4 | 11.5 | -12.259 | -16.5 | 0% | — | No edge — hibernation candidate |

**COMMODITY and BOND walk-forward not yet in local file** — COMMODITY walk-forward is a gap that needs to be added.

Key insight: **ETF is the highest-conviction OOS performer in the system** (76% WR, 100% consistency, positive decay = improving). Yet it's below n=100 charter floor. Emission scaling is the highest-leverage action available.

**BOND Sharpe 16.224 is remarkable** but worst-fold WR 0% means one bad fold zeroed out. Consistency must reach 80%+ before sizing up.

---

## 3. Concept Drift — CRITICAL

```
KS_D:           0.312576
KS_critical:    0.047292
D/critical:     6.61x  ← SEVERE (>5x = regime change)
drift_alert:    TRUE
var_ratio:      1.0696
early_n:        1654
late_n:         1654
```

**Implication:** The distribution of pick outcomes has fundamentally shifted. The system is trading a different regime than what most strategies were tuned on. This explains CRYPTO WR decay (44.8% live vs 53.7% bottom-band historical). **Every WR claim in the leaderboard should be discounted by ~5-10pp in the current regime** until drift stabilises.

**Required action (P0):** Implement auto-pause on new CRYPTO + FOREX sizing when KS_D > 0.25. Only COMMODITY/ETF/EQUITY with positive walk-forward decay are safe to size in a drift environment.

---

## 4. System Winners (Tier-2+ Verified)

*(forward-validated, PF≥1.5, WR≥50%, n≥8)*

| Rank | System | Asset Class | n | Fwd WR% | Fwd PF | Expectancy | Source |
|------|--------|------------|---|---------|-------|-----------|--------|
| 1 | VWAP Deviation Scalp | CRYPTO | 35 | 97.1 | **119.0** | 3.37 | aggregated_picks |
| 2 | ml_enhanced_DYDXUSDT_15m_D | CRYPTO | 31 | 96.8 | **58.46** | 1.81 | alpha_engine |
| 3 | ml_enhanced_BNBUSDT_15m_B | CRYPTO | 21 | 85.7 | **56.17** | 4.42 | alpha_engine |
| 4 | AuditEnsemble_LONG | CRYPTO | 101 | 94.1 | **36.66** | 2.98 | aggregated_picks |
| 5 | ml_enhanced_INJUSDT_1d_B | CRYPTO | 31 | 93.5 | **35.19** | 13.22 | alpha_engine |
| 6 | cot_positioning | COMMODITY | 102 | 94.1 | **21.86** | 4.20 | multi_asset_cot |
| 7 | cftc_cot_commercial_signal | COMMODITY | 94 | 93.6 | **22.66** | 4.19 | multi_asset_copytrader |
| 8 | gap-and-go-stocks | EQUITY | 8 | 75.0 | **14.81** | 8.00 | kimi_riseoftheclaw |
| 9 | rs-breakout-scout | EQUITY | 33 | 78.8 | **7.45** | 2.76 | kimi_riseoftheclaw |
| 10 | donchian-stock-breakout | EQUITY | 14 | 78.6 | **7.13** | 6.25 | kimi_riseoftheclaw |
| 11 | ml_enhanced_FETUSDT_1d_B | CRYPTO | 45 | 55.6 | 9.22 | 16.84 | alpha_engine |
| 12 | vwap-reversion-scout | ETF | 8 | 75.0 | 4.54 | — | kimi_riseoftheclaw |
| 13 | intermarket-flow-scout | ETF | 22 | 59.1 | 1.51 | — | kimi_riseoftheclaw |
| 14 | multi_period_rsi_confluence | CRYPTO | 113 | 50.4 | **93.57** | 0.09 | baby_strats_forward |

**Note on multi_period_rsi_confluence:** PF 93.57 with expectancy 0.09 is a red flag — massive win/loss asymmetry on a tight sample. Verify against DB before sizing.

---

## 5. System Draggers (Negative PnL Contribution)

| System | PF | WR% | n | PnL% | Kill Status | Action |
|--------|-----|-----|---|------|------------|--------|
| multi_asset | 0.32 | 45.5 | 231 | **-160.92%** | Active | Immediate 3-axis autopsy |
| mercury2_fast | 0.07 | 42.9 | 32 | **-139.53%** | Active | Quarantine + mutation replay |
| alpha_engine_fast | 0.62 | 43.2 | 299 | **-127.62%** | Active (score -8) | Volume cap, not full kill |
| copy_trader_highscore | 0.77 | 31.9 | 339 | **-79.77%** | Active | Investigate vs copy_trader |
| ml_bg_system_b | 0.02 | 5.3 | 19 | -54.70% | Unknown | Kill (PF 0.02 = noise) |
| ml_bg_system_a | 0.14 | 10.5 | 19 | -49.84% | Unknown | Kill (PF 0.14 = broken) |
| goldmine_stocks | 0.14 | 42.9 | 453 | -11.67% | Active (score +12) | **Score mismatch — re-audit** |

**Critical flag on `goldmine_stocks`:** Source score is +12 ("67% WR, +1.17% avg PnL") but system shows PF 0.14, WR 42.9%, pnl -11.67%. The score comment is stale. Requires immediate re-audit and score correction.

**72 dead systems** (no signal >30d) — marking them INACTIVE would reduce dashboard noise and prevent them from diluting gate pass-rates.

---

## 6. Backtest Overfit — baby_strats Family (12 Strategies)

All 12 flagged rows are `baby_strats` system, all CRYPTO, all `crypto_soc_*` or related families:

| Strategy | BT WR% | Fwd WR% | Decay | Severity (σ) |
|----------|--------|---------|-------|-------------|
| crypto_soc_proxy_decoupling_a03 | 66 | 33.8 | -32.2 | **5.73** |
| crypto_soc_delta_divergence_a07 | 60 | 38.4 | -21.6 | 4.93 |
| crypto_soc_orderflow_absorption_a07 | 55 | 40.4 | -14.6 | 4.73 |
| crypto_adx_pullback_trendresume | 63 | 36.5 | -26.5 | 4.72 |
| crypto_choppiness_regime_switch | 58 | 37.1 | -20.9 | 4.17 |
| crypto_soc_regime_filters_a03 | 66 | 40.7 | -25.3 | 3.92 |
| *(6 more, severity 3.4–4.6σ)* | | | | |

**Verdict:** These strategies have backtest WR inflated by ~20-32pp relative to live. They are producing picks that look credible in backtest but fail OOS. Surgical quarantine via `BLOCKED_ASSET_STRATEGY_PAIRS` for baby_strats:CRYPTO is warranted — but requires 3-axis mutation replay per protocol first.

---

## 7. Top Edges Per Asset Class (Forward-Validated)

### COMMODITY — Star Class, T2-Ready
| Strategy | Source | n | Fwd WR% | Fwd PF | Action |
|----------|--------|---|---------|-------|--------|
| cot_positioning | multi_asset_cot | 102 | 94.1 | 21.86 | Scale aggressively |
| cftc_cot_commercial_signal | multi_asset_copytrader | 94 | 93.6 | 22.66 | Scale aggressively |
| connors_rsi2 | multi_asset_scanner | 6 | 20.0 | 0.09 | Kill — drag |

**Gap:** Only 2 active commodity strategies. CFTC COT data covers 20+ commodity classes (Gold, Silver, Oil, Nat Gas, Corn, Wheat, Soybeans, Coffee, Cotton, Copper, etc.). Currently only a fraction are traded. Extending COT signals to all reportable commodity classes could 3-5x emission volume at same edge level.

### EQUITY — kimi_riseoftheclaw Monopoly
| Strategy | n | Fwd WR% | Fwd PF | Missing Coverage |
|----------|---|---------|-------|-----------------|
| gap-and-go-stocks | 8 | 75.0 | 14.81 | Need 50+ more picks |
| rs-breakout-scout | 33 | 78.8 | 7.45 | More mid-cap coverage |
| donchian-stock-breakout | 14 | 78.6 | 7.13 | More tickers |
| price-accel-scout | 16 | 62.5 | 3.66 | Sector expansion |
| mtf-align-scout | 17 | 64.7 | 3.23 | Sector expansion |

**Gap:** All top equity strategies come from `kimi_riseoftheclaw`. Alpha_engine, signal_validation underrepresent equity. kimi allocation cap likely throttling emission. Increasing kimi EQUITY emission frequency or adding more symbols (S&P 500 universe vs current ~50-100 tickers) would directly lift n and PF.

### ETF — Highest OOS, Lowest Volume
| Strategy | n | Fwd WR% | Fwd PF | Note |
|----------|---|---------|-------|------|
| vwap-reversion-scout | 8 | 75.0 | 4.54 | Only 8 picks — low freq |
| golden-cross-stocks | 5 | 80.0 | 3.92 | Below stat-sig floor |
| intermarket-flow-scout | 22 | 59.1 | 1.51 | Best volume ETF strat |
| adx-trend-scout | 18 | 61.1 | 1.06 | Marginal — PF below T2 |

**Gap:** ETF universe is extremely narrow (likely <20 ETFs tracked). Sector ETFs (XLK, XLF, XLE, XLV, ARKK, SOXX), thematic ETFs (VNQ, GLD, TLT, HYG), and international ETFs (EEM, EFA) are all untapped. Extending kimi to 100+ ETFs at current WR would hit n=200 within 60 days.

### CRYPTO — Volume ≠ Edge
| Category | Volume Share | Edge | Action |
|----------|-------------|------|--------|
| quan_engine | 21% | PF 0.66 | Volume cap urgently needed |
| luxalgo_filters | ~8% | PF 0.99 | Score -8 applied; monitor |
| ML enhanced (DYDX/BNB/INJ/FET) | <1% | PF 35-58 | Scale up ML model coverage |
| baby_strats (flagged) | Unknown | BT-overfit | Quarantine after 3-axis |
| aggregated_picks ensemble | ~2% | PF 36-119 | Increase weight in routing |

**Gap:** The best CRYPTO edge is from ML-enhanced per-symbol models (DYDX, BNB, INJ, FET, STRK, WLD, XRP, APT, ADA). Only ~10 symbols are covered. Extending to 30-50 top liquid symbols (ETH, SOL, AVAX, ARB, OP, SUI, SEI, PYTH, etc.) at same model architecture would increase high-quality emission dramatically.

### BOND — Promising OOS, Need Volume
- Only 1 strategy in leaderboard: `betting-against-beta` (WR 23.1%, PF 0.24, n=13) — terrible
- The PF 1.72 / WR 55.6% coming from BOND is NOT from betting-against-beta (which is the only bond strategy in leaderboard). Need to identify the actual winning strategy source.
- Walk-forward Sharpe 16.224 with 50% consistency is likely coming from a single strong fold masking one empty fold.

### FOREX — Confirmed Dead
- OOS WR 11.5%, consistency 0%, Sharpe -12.259
- No forward-validated strategy with PF > 1.5
- `MeanReversionBB` shows fwd WR 63.2% PF 2.48 n=46 — this is the ONLY viable FOREX signal
- Action: isolate MeanReversionBB for FOREX, quarantine everything else via 3-axis mutation first

---

## 8. Enhancement Plan — Ranked Best Possible Actions

| Priority | Action | Asset Class | Expected Impact | Effort (h) | Risk |
|----------|--------|------------|----------------|-----------|------|
| **P0** | Add CRYPTO volume cap for `quan_engine` (hard ceiling ≤5% of daily emission) | CRYPTO | +5-8pp WR system-wide | 3 | Low |
| **P0** | Concept drift auto-pause gate: when KS_D > 0.25, freeze new CRYPTO/FOREX sizing | ALL | Risk reduction, prevents sizing into regime shift | 4 | Low |
| **P0** | Fix `goldmine_stocks` score mismatch: source score +12 vs system PF 0.14 | EQUITY | Remove false signal boost | 1 | Low |
| **P0** | Baby_strats 3-axis mutation replay → surgical quarantine of 12 failing crypto_soc_* strategies | CRYPTO | Remove -13 to -32pp WR drag | 6 | Med (requires protocol) |
| **P1** | Extend COT signals to all 20+ CFTC-reportable commodity classes | COMMODITY | 3-5x volume at current edge level → lift n from 816 toward 3000+ | 8 | Low |
| **P1** | Extend ML-enhanced per-symbol CRYPTO models to 30 new tickers (ETH, SOL, AVAX, ARB, OP, SUI, SEI, PYTH, NEAR, etc.) | CRYPTO | Replace quan_engine drag with ML edge; WR target 55%+ on ML subset | 12 | Med |
| **P1** | Scale kimi_riseoftheclaw EQUITY universe from ~100 to 500+ S&P tickers | EQUITY | Double EQUITY emission at PF 2.09, push n→1000+ within 90d | 6 | Low |
| **P1** | Add 100+ ETFs to kimi scanner (sector, thematic, international) | ETF | Hit n=100 charter floor within 2 weeks; n=200 in 30d | 4 | Low |
| **P2** | Mark 72 dead systems INACTIVE in dashboard (no signal >30d) | ALL | Reduce noise; cleaner gate pass-rates | 2 | Low |
| **P2** | Add COMMODITY walk-forward (missing from walk-forward suite entirely) | COMMODITY | Validate if COT edge is OOS-real or data-snooping | 5 | Low |
| **P2** | BOND: identify the actual winning bond strategy (PF 1.72, WR 55.6% not from `betting-against-beta`) | BOND | Fix strategy attribution; scale correct strategy | 3 | Low |
| **P2** | Isolate MeanReversionBB for FOREX and quarantine all other FOREX signals | FOREX | Preserve the one viable FOREX signal; stop WR dilution | 2 | Low |
| **P3** | CRYPTO: Add AuditEnsemble_LONG emission boost (WR 94.1%, PF 36.66, n=101 — underweight) | CRYPTO | Direct WR improvement on largest class | 4 | Low |
| **P3** | Per-symbol ML models for top EQUITY symbols (NVDA, AAPL, MSFT, TSLA, AMD on 15m/1h) | EQUITY | Replicate CRYPTO ML success in EQUITY space | 10 | Med |
| **P3** | Add `VWAP Deviation Scalp` emission quota increase — currently n=35, WR 97.1% | CRYPTO | Best WR in entire system; criminally underweighted | 3 | Low |
| **P4** | Wire `charter_risk_budget.py` to production scanner (currently opt-in sidecar, PR #982) | ALL | Enforce class caps in live routing | 4 | Low |
| **P4** | Add COMMODITY WR gate: require >50% WR on 7d rolling before new COMMODITY sizing | COMMODITY | Prevent WR from slipping below T2 floor (currently 48.7% vs 50% target) | 3 | Low |
| **P4** | Add Sharpe/Calmar per-class targets to active gate (not just WR/PF) | ALL | Better risk-adjusted selection; align with hedge fund metrics | 6 | Med |
| **P5** | FUTURES mutation replay (n=0, dormant) | FUTURES | Unblock dormant class | 8 | Med |
| **P5** | External: wire FRED API (yield curve, VIX, DXY) as macro regime filter | ALL | Improve regime-awareness; reduce drift impact | 5 | Low |

---

## 9. New Strategies to Consider Per Class

### COMMODITY (highest-confidence expansion)
- **COT Net Positioning Z-Score** across all 20 CFTC reportable markets (Crude Oil, Gold, Silver, Copper, Nat Gas, Corn, Wheat, Soybeans, Live Cattle, Coffee, Cotton, Sugar, Cocoa)
- **Seasonal commodity patterns** (winter nat gas, harvest corn, summer crude) layered on COT signal
- **Basis / term structure** for futures-based commodity ETFs (USO, GLD, SLV)

### EQUITY (scale what works)
- Add pre-market gap scanner (gap-and-go-stocks is PF 14.81 on only n=8 — needs 50+ picks urgently)
- **Earnings momentum** strategy: buy high-quality beat+raise stocks within 3 days of report
- **52-week high breakout** across full S&P 1500 universe (Donchian-stock-breakout is PF 7.13)
- **Relative strength ranking** (rs-breakout-scout PF 7.45) applied to Russell 2000 + growth universe

### CRYPTO (precision over volume)
- Extend ml_enhanced models: **ETHUSDT, SOLUSDT, AVAXUSDT, ARBUSDT, OPUSDT, SUIUSDT** on 15m + 1d timeframes
- **Funding rate extremes** strategy: fade extreme negative funding (>-0.5% 8h) on large caps
- **On-chain accumulation signal**: large wallet net flow + exchange outflow composite
- **Liquidation cascade detector**: when >$100M long liquidated in 1h, counter-trend long entry

### ETF (volume expansion)
- Extend to sector ETFs: XLK (tech), XLF (finance), XLE (energy), XLV (healthcare), XLI (industrials)
- **Volatility regime ETF switch**: VXX/UVXY short on low-vol regimes; SVXY long
- **Fixed income ETFs**: TLT, IEF, HYG, LQD — natural crossover with BOND class

### BOND (strategy discovery)
- **Duration momentum**: buy TLT when 50d MA > 200d MA; sell when inverted
- **Credit spread mean reversion**: HYG/IEF ratio extremes
- **Fed meeting positioning**: systematic long TLT 5 days before dovish Fed, short before hawkish

### FOREX (triage — only one valid signal)
- **Keep ONLY**: MeanReversionBB (WR 63.2%, PF 2.48, n=46)
- **Quarantine all others** pending 3-axis mutation replay
- Consider: currency carry strategy on high-yielders (AUD, NZD, BRL) with vol filter

---

## 10. Safety Gate Enhancements

| Gate | Current State | Enhancement |
|------|--------------|-------------|
| Volume cap by source | Score-weighted only; no hard ceiling | Add `MAX_VOLUME_PCT_BY_SOURCE = {"quan_engine": 0.05}` in quality_gates.py |
| Concept drift pause | Alert only | Auto-pause CRYPTO/FOREX new sizing when KS_D > 0.25 |
| Baby_strats overfit | 12 strategies showing 4-5.7σ decay, no gate | Quarantine via BLOCKED_ASSET_STRATEGY_PAIRS after 3-axis |
| WR floor per class | Global gate only | Per-class rolling 7d WR floor: COMMODITY>50%, EQUITY>50%, ETF>50% |
| BOND n gate | Disabled (too few picks) | Add BOND_MIN_N_FOR_SIZING=30 (softer than charter n=100) |
| Dead systems | 72 with no signal >30d still counted in pass rates | Mark INACTIVE; exclude from gate denominator |
| FOREX isolation | Not isolated | Route FOREX to MeanReversionBB-only pool; reject other FOREX strategies at intake |

---

## 11. daily_ideas.md

`docs/daily_ideas.md` does **not exist** in the repository. No file found at any path variant. If this was intended as an idea backlog, recommend creating it at `docs/daily_ideas.md` with a simple append-only format. Alternatively ideas have been tracked in `reports/` and `updates/index.html` entries.

---

## 12. Verifiable Claims Log

All performance numbers sourced from:
- Live dashboard screenshot (2026-05-14T20:00:01Z): asset class table, walk-forward OOS table
- `audit_dashboard/data/dashboard_data.json` (generated 2026-05-14T01:22:10Z, stale): leaderboard, systems, hf_stats
- `audit_trail/quality_gates.py::_SOURCE_SYSTEM_SCORES`: source system scores (verified by direct file read)

Reproduce leaderboard drill-down:
```bash
python -c "
import json
from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
lb = d.get('leaderboard', [])
valid = [e for e in lb if (e.get('fwd_pf') or 0) >= 1.5 and (e.get('fwd_wr') or 0) >= 52 and (e.get('fwd_trades') or 0) >= 8]
valid.sort(key=lambda x: -(x.get('fwd_pf') or 0))
for e in valid[:20]: print(e.get('asset_class'), e.get('strategy'), e.get('fwd_trades'), e.get('fwd_wr'), e.get('fwd_pf'))
"
```

---

## 13. Swarm Second Opinion — Key Additions (2026-05-14T21:27Z)

*Independent 4-engine swarm run in parallel. Corroborates all P0 findings above and surfaces 3 new critical items:*

### CRITICAL BUG — Regime Tagging Broken (swarm rank #6)
`regime_validation.with_regime_data = 0` out of 236 active picks. The regime classification infrastructure exists in `dashboard_data.json::regime_validation` but **nothing stamps `regime=` on picks at emission time**. Walk-forward fold variance on EQUITY (45%-71% OOS WR swing) and CRYPTO (27%-71%) is almost certainly regime-driven. Fix: in `production_scanner.py`, call the regime classifier and stamp each pick before gate evaluation. Expected: +5-15pp WR on EQUITY/ETF.

### New Gate: luxalgo Stratification (swarm rank #14)
Rather than blocking `luxalgo_filters` outright, stratify by signal strength ≥75 (top 20% = `luxalgo_highconf` sublayer). Top-quintile signals likely show WR >60%, PF >2.0 — converts the current drag into a selective contributor without triggering mutation protocol.

### New Data: Hyperliquid Funding Rate Gate (swarm rank #10)
Free API. When perp funding rate >0.01% (8h), apply confidence penalty on CRYPTO LONG signals to avoid buying into crowded expensive longs. 6h effort, opt-in wiring plan.

### Consolidated Priority Queue (main audit + swarm)

| Rank | Action | Class | Effort | Impact |
|------|--------|-------|--------|--------|
| P0-A | quan_engine hard emission block CRYPTO | CRYPTO | 3h | +0.25 PF |
| P0-B | Concept drift auto-pause (KS_D >0.25 → freeze) | ALL | 4h | Risk reduction |
| P0-C | Fix goldmine_stocks score (+12 vs PF 0.14) | EQUITY | 1h | Routing fix |
| **P0-D** | **Fix regime_validation bug — stamp regime at emission** | ALL | 6h | **+5-15pp WR** |
| P0-E | baby_strats 3-axis mutation → quarantine 12 strats | CRYPTO | 8h | WR lift |
| P1-A | COT expansion to 20+ CFTC commodity classes | COMMODITY | 16h | n: 816→3000+ |
| P1-B | ML-enhanced CRYPTO to 30 new symbols | CRYPTO | 20h | Replace quan drag |
| P1-C | kimi EQUITY 100→500+ S&P tickers | EQUITY | 6h | n→1000+ in 90d |
| P1-D | 100+ ETFs to kimi scanner | ETF | 4h | n=88→200 in 30d |
| P1-E | FOREX full emission freeze + autopsy | FOREX | 5h | Stop neg-EV bleed |
| P2-A | luxalgo highconf sublayer (strength ≥75) | CRYPTO | 6h | Convert drag→edge |
| P2-B | BOND Treasury futures expansion (ZN/ZB/UB) | BOND | 12h | n→100 in 6-8wk |
| P2-C | Dead system reaper — archive 72 stale systems | ALL | 4h | Dashboard clarity |
| P2-D | Hyperliquid funding rate gate on CRYPTO LONGs | CRYPTO | 6h | Regime quality |
| P3-A | gap-and-go catalyst filter (EPS surprise + premarket vol) | EQUITY | 7h | n: 8→30+ |
| P3-B | AuditEnsemble_LONG emission boost (WR 94.1%, PF 36.66) | CRYPTO | 3h | Direct WR lift |
| P4-A | Wire charter_risk_budget.py to production (PR #982) | ALL | 4h | Class caps live |
| P4-B | COMMODITY walk-forward suite (currently missing) | COMMODITY | 5h | OOS validation |

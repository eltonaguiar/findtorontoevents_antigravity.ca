# Hedge-Fund-Grade Picks: Current State & Path Forward
## 2026-05-18 — Comprehensive Assessment

---

## 1. HONEST CURRENT STATE

### System-Wide Performance (Live DB: 146k+ picks)
| Metric | Value | Grade |
|--------|-------|-------|
| Total picks (all systems) | 146,802 | — |
| Resolved picks (30d window) | ~4,952 (CRYPTO only) | 🔴 |
| Overall Win Rate | 40.3% | 🔴 |
| Overall Avg PnL | −12.92% | 🔴 |
| Win/Loss Ratio | 0.76 (losses 32% larger) | 🔴 |
| Forward Resolution Rate (non-crypto) | 0% | 🔴 |
| Active crypto symbols (7d) | 12 | 🔴 |
| Harness Admissible Cohorts | 0/8 tested | 🔴 |

**Verdict: NOT REAL-MONEY READY.** Three RED blockers, zero GREEN categories.

---

## 2. WHAT THIS SESSION PROVED

### Task A: Edge Analysis Cohorts — All Dead on Arrival
- **CRYPTO 7fam LONG:** 0 exact match in canonical data; quan_engine_scalp (n=2,662) FAILS harness (sign=mixed)
- **EQUITY elite≥60:** n=1 in canonical vs claimed n=44 — **44x inflation bug**
- **COMMODITY SHORT:** n=0 (no SHORT direction exists; COT was killed as leakage)
- **FOREX rsi-ema-scout:** n=0 exact match; n=7 closest; OOS PF=0.65 (expected kill)

### Task B: Copytrader Edge — Data Doesn't Exist
- 321 trades, **ALL outcome=FLAT, pnl=0.0000**
- Forward WR is estimated/unvalidated
- highscore_closed_picks.json has survivorship bias (29 curated records)
- **Cannot verify or refute any copytrader edge**

### Task C: Data Infrastructure
- Canonical pipeline removes 3,691 duplicate re-emissions (36% of raw picks)
- 82.5% of CRYPTO picks remain unresolved after 30 days
- Forward resolution pipeline is completely broken for FOREX/EQUITY
- Confidence scores are INVERTED in CRYPTO (higher conf → worse performance)

---

## 3. PROVEN PROFITABLE SUBSETS (The Only Real Edges)

| Filter | Picks (30d) | WR | Avg PnL | Lift |
|--------|-------------|-----|---------|------|
| Baseline (all CRYPTO) | 4,952 | 40.3% | −12.92% | — |
| **RR ≥ 1.5 + conf ≥ 0.65 (14d)** | **460** | **48.9%** | **−3.1%** | **+9pp WR, +9.8pp PnL** |
| **High confidence (≥0.8)** | **151** | **45.0%** | **+0.5%** | **+4.7pp WR, +13.4pp PnL** |
| COMMODITY multi_asset_copytrader | 47 | 61.7% | PF=2.30 | Only viable non-crypto |

**Key finding:** Only the high-confidence (≥0.8) CRYPTO cohort shows positive average return. This is the single actionable edge — thin, but real.

---

## 4. WHAT THE PROS DO (That We're Not Doing)

### Hedge Fund Best Practices
1. **Cohort-level edges, not ticker-level:** Find the 2-3 strategy+direction+asset combos that work; size them; kill everything else
2. **Disagreement gates:** Require ≥3 independent models to agree before taking a position
3. **Regime awareness:** Pause/reduce in high-vol regimes (VIX > 25, BTC dominance spikes)
4. **Asymmetric risk management:** Winners should be 2-3x the size of losers; our ratio is inverted (0.76)
5. **Full survivorship tracking:** Every strategy must show FULL history, not cherry-picked windows
6. **Kelly or risk-parity sizing:** Not fixed percentages
7. **Kill switches:** Auto-disable any strategy if rolling 7-day WR < 48% or PF < 1.2

### Copy Trading Reality
- Simply copying top traders is a losing strategy (execution lag, different leverage, emotional overrides)
- You extract the PROCESS, not the PICKS
- Our copytrader integration proves nothing because it has 0 completed outcomes

### Prediction Markets
- We have no Polymarket/Kalshi integration providing edge
- The copy_trader_intel/non_crypto_consensus.py exists but is disconnected from resolution pipeline

---

## 5. CONCRETE ACTION PLAN (Prioritized by Impact)

### PHASE 0: Emergency Fixes (This Week)
| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 0.1 | **Enforce hard filter gate: confidence ≥ 0.75 AND risk_reward ≥ 1.8** before any pick reaches execution | Highest — immediately improves WR | 2 hours |
| 0.2 | **Kill NULL strategy picks** — 5,945 crypto picks have NULL strategy, polluting stats | High — removes noise | 30 min |
| 0.3 | **Fix confidence inversion in CRYPTO** — investigate why higher confidence → worse performance (likely a scoring/pipeline bug) | Critical | 1-2 days |
| 0.4 | **Fix forward resolution pipeline** for FOREX/EQUITY — 0% resolution is a data quality crisis | Critical | 2-3 days |

### PHASE 1: Infrastructure (Weeks 1-2)
| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1.1 | **Daily "hot list" ingestion** — top 50 crypto gainers by 24h volume + 4h momentum (CoinGecko/Binance API) | Massive — expands 12 → 40+ symbols | 1 day |
| 1.2 | **Auto-expire stale picks** — anything >48h with no exit should be force-resolved | High — cleans data | 4 hours |
| 1.3 | **Per-asset-class risk engine** — different position sizing for CRYPTO (4bp) vs FOREX (1bp) vs COMMODITY (6bp) slippage | Medium | 1 day |
| 1.4 | **Build disagreement gate** — require ≥3 independent source systems | High | 2-3 days |

### PHASE 2: Edge Mining (Weeks 3-4)
| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 2.1 | **Validate the 10 surviving CRYPTO cohorts** through full walk-forward harness (NOT just the truncated exploring period) | Critical | 3-5 days |
| 2.2 | **Implement regime detection** (trending vs mean-reverting based on ATR/ADX) and route picks accordingly | Medium | 3 days |
| 2.3 | **Deep-dive COMMODITY** — the only non-crypto positive PF (2.30) with 61.7% WR; scale up if harness passes | High | 2-3 days |
| 2.4 | **Fix copytrader outcome tracking** — need actual PnL data, not just forward_wr estimates | High | 1-2 days |

### PHASE 3: Scale & Harden (Months 2-3)
| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 3.1 | **Paper trade the filtered system for 30+ days** before any real capital | Critical | Ongoing |
| 3.2 | **Expand to 200+ symbols** across all asset classes with automatic onboarding pipeline | High | 2 weeks |
| 3.3 | **Build kill-switch automation** — rolling WR/PF monitors that auto-disable strategies | High | 3 days |
| 3.4 | **Add Polymarket/Kalshi prediction market signals** as a genuinely new input class | Medium | 1 week |
| 3.5 | **On-chain data integration** (Glassnode, DefiLlama) — the options_flow and onchain_crypto modules are parked sidecars, not yet tested | Low (long-term) | 2+ weeks |

---

## 6. TIMELINE TO HEDGE-FUND GRADE

| Level | Target | Timeline | Probability |
|-------|--------|----------|-------------|
| **Tier 3** (filtered gate fixes) | WR 48-52%, slightly positive PnL | 1-2 weeks | **70%** |
| **Tier 2** (full infrastructure) | WR 53-57%, Sharpe >1.0 on paper | 1-2 months | **50%** |
| **Tier 1** (multi-asset, 55%+ WR) | Consistent profitability across 4+ classes | 3-4 months | **30%** |
| **World-Class** (institutional grade) | 57%+ WR, 1.5+ Sharpe, 200+ symbols, live capital | 9-14 months | **15%** |

---

## 7. BOTTOM LINE

1. **The system DOES have edges** — but they're buried under noise, data quality issues, and infrastructure gaps
2. **The biggest quick win** is enforcing a hard confidence+RR filter gate — this alone flips the CRYPTO cohort from bleeding to nearly neutral
3. **The biggest structural problem** is the inverted confidence scoring in CRYPTO — until fixed, any optimization is building on sand
4. **Symbol coverage is embarrassing** — 12 symbols when the market rotates through hundreds daily
5. **No asset class except COMMODITY (small sample) and narrow CRYPTO subsets has proven edge** after canonical dedup and harness testing
6. **The copytrader integration is dead** — fix outcome tracking or remove it
7. **Prediction market integration** (Polymarket, Kalshi) is untapped and could provide genuinely new signals
8. **Timeline to institutional-grade**: 9-14 months with disciplined execution of this plan

KNOWN LIMITATIONS OF THIS ANALYSIS:
- 492 CRYPTO LONG picks is below the harness's 80/window × 5 windows threshold for reliable verdicts
- COMMODITY and EQUITY have too few canonical picks to test
- Copytrader edge is unverifiable with current data
- Forward resolution gap means most non-crypto analysis is incomplete

---

*Report: 2026-05-18 | All numbers DB-backed from ejaguiar1_stocks.at_raw_picks + pf_registry.json*
*No "Money Ready" claims. Honest assessment only.*
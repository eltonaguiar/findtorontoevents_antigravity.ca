# PROVEN & FAMOUS ALGORITHMS — TradingView Contests & Beyond

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## Critical Disclaimer

**TradingView contest winners are survivorship bias, NOT proof of repeatable method.** Winners are selected from thousands of participants. None of the approaches below have been validated in THIS system's clean-cohort data. Use as inspiration only — always verify with clean, per-class, cost-adjusted, out-of-sample testing.

---

## Hoffman & Related Approaches

**Eugene Hoffman** is a known figure in trading education, but:

| Claim | Status in This Repo | Verdict |
|-------|---------------------|---------|
| Hoffman EMA IRB | Listed in ALL_STRATEGIES.md under "Alpha Engine — Proven Research" | NOT verified in clean data |
| Various Hoffman strategies | Not found in clean-cohort results | NOT verified |

**Rule:** Do NOT cite or trade any "Hoffman" strategy without clean out-of-sample verification in THIS system's data.

---

## AI Tournament Results (from money-maker-readyv2 skill)

The AI Tournament on findtorontoevents.ca/audit/ai-tournament.html has 39 cloud AI models forward-tested per class. **These are forward-test results, NOT proven edges.**

### Tier 1 (n≥30 resolved, PF_CI_lo > 1.0)

| Model | Picks | Resolved | WR | PF | Score | Rank |
|-------|-------|----------|-----|-----|-------|------|
| deepseek_v4 | 178 | 43 | 55.81% | 3.715 | 0.7495 | 1 |
| cursor_agent | 113 | 59 | 66.10% | 2.354 | 0.6586 | 2 |
| llama4_scout | 115 | 57 | 61.40% | 2.261 | 0.574 | 3 |
| grok3 | 300 (merged) | 89 | 58.43% | 2.016 | 0.5587 | 4 |

**Critical Caveats:**
- ~47% of all tournament picks are still `status=OPEN`
- These WRs are forward-test on 43-89 resolved picks (wide confidence intervals)
- Institutional-grade requires n≥100 resolved + OOS stability
- None qualify for live capital

### Tier 2 (n≥30 resolved, but PF_CI_lo < 1.0)

| Model | Resolved | WR | PF | PF_CI_lo |
|-------|----------|-----|-----|----------|
| ring_261T | 60 | Not specified | Not specified | 0.876 |
| llm7_qwen | 55 | Not specified | Not specified | 0.798 |

### Tier 3 (9 models with n≥30 resolved but PF_CI_lo < 1.0)

Edge not statistically proven.

---

## Famous Algorithms Referenced in ALL_STRATEGIES.md

### Connors RSI2 (EQUITY)
- **Asset:** SPY/QQQ
- **Claimed WR:** 75.7%
- **Status:** Sole proven equity sleeve
- **Validation needed:** Pre-registered test vs SPY total return, n≥500

### VIX Spike Reversal (EQUITY/SPX)
- **Asset:** SPX
- **Claimed WR:** 72%
- **Status:** Promising but not independently verified

### Triple EMA Pullback (Alpha Engine — Proven Scanner)
- **Asset:** Various
- **Status:** Listed but not verified in clean data

### Keltner EMA Momentum (Alpha Engine — Super Strategies)
- **Asset:** Various
- **Status:** Listed but not verified

### Williams VIX Fix (Alpha Engine — TradingView)
- **Asset:** Various
- **Status:** Listed but not verified

### WaveTrend (Alpha Engine — TradingView)
- **Asset:** Various
- **Status:** Listed but not verified

### Connors R2 Survivor (Alpha Engine — Survivor Strategies)
- **Asset:** Various
- **Status:** Listed but not verified

---

## What Makes an Algorithm "Proven"?

Based on ALL money-maker skills, an algorithm is ONLY proven if it passes ALL of:

| Criterion | Threshold |
|-----------|-----------|
| Clean out-of-sample | n ≥ 30 per filter bucket |
| Profit Factor | ≥ 1.5 |
| Win Rate | ≥ 50% (EXPIRED-inclusive) |
| Max Drawdown | ≤ 20% |
| Sample Size | n ≥ 100 closed picks |
| Time Span | ≥ 3 months |
| Data Integrity | No backfill labels, no banned sources, sane PnL |
| Intrabar Validation | TP/SL checked against actual OHLCV bars |
| Multiple Testing | Bonferroni or FDR correction applied |
| Stability | First-half PF ≈ second-half PF |
| Cross-Source | Not single-source concentrated (>60% from one source) |

**Current State:** 0/23 hypotheses across 4 protocol versions pass all criteria.

---

## Algorithms EXPLICITLY REJECTED (Do NOT Relitigate)

| Algorithm | Reason |
|-----------|--------|
| stocks_rsi2_pullback | 14d WR 29.9% (down from claimed 75.7%) |
| CRYPTO direction-flip | Refuted |
| futures_momentum / forex_rsi2 shadow | Failed |
| luxalgo "best" | Not verified |
| MeanReversionBB | Failed |
| trust=7 | Failed |
| alpha_engine×CRYPTO 80.6% | Not verified |
| kimi_ultimate_proven_edge | Self-admitted SYNTHETIC (MiniMax-authored) |
| bt_backtest_trades 32.6M rows | Backtest overfit trap |
| FOREX 14d WR 64% / PF 2.43 | Clean 14d FOREX WR **5.0%** |
| GBPUSD WR 58.8%, n=114 | True ~7%; 87% expired |
| mega_mutation T1 without intrabar | Resolver does not replay intrabar |

---

## Recommended Algorithm Research Path

If you want to find a profitable algorithm, follow this order:

1. **Start with EQUITY Connors RSI2** — only sleeve with any promise
   - Run pre-registered test vs SPY total return
   - n≥500, PF≥1.15, Sharpe≥SPY Sharpe
   
2. **Then test ETF TAA** — already validated smart-beta
   - Forward-track 6-12 months vs SPY
   - Confirm MaxDD < SPY MaxDD

3. **Then consider CRYPTO** — only after entry_price fix
   - Fix entry_price ~29% clean issue
   - Forward-test POSITION horizon n≥100
   - PF ≥ 1.3, WR ≥ 55%

4. **Do NOT touch:** FOREX, FUTURES, MEMECOIN, PENNY, CRYPTO day/swing trading

---

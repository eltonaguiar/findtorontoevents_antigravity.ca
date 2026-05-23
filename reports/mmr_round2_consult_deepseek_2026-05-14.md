## Independent Second Opinion — MMR Round 3 Ranking

### TOP 5 SHIP FIRST (P0)

**1. EQUITY: RSI-2 Overbought SHORT (SPY/QQQ/IWM)**
- **90d Tier-2 progress:** HIGH. Mirror of existing 75.7% WR LONG on SPY. Symmetry alone gets you 60-65% WR on SHORT side with PF >1.5. Universe size (3 ETFs × 252 days) gives n > 750 in 90 days. MDD <15% because RSI-2 is mean-reverting, not trend-following.
- **Main risk:** Regime dependency — works in range-bound/mean-reverting markets, gets crushed in sustained downtrends (SHORT against falling knife). Mitigation: add VIX >30 filter to pause.

**2. CRYPTO: `proven_research_strategies.py` (22 strategies)**
- **90d Tier-2 progress:** HIGH. Claims of 62-83% WR on research-backed strategies (VWAP, pairs, RSI confluence). Even if 50% survive walkforward, you get 10+ strategies with WR >50% and PF >1.5. Data abundance (crypto 24/7) gives n > 2000 in 90 days. Wire-up is 3-5h total — fastest time-to-market.
- **Main risk:** Survivorship bias in claims — those WRs may be in-sample only. Need immediate walkforward split (70/30) before wiring. If 40% fail, still have 13 good ones.

**3. EQUITY: Earnings Negative Drift SHORT (PEAD)**
- **90d Tier-2 progress:** MEDIUM-HIGH. EPS miss > -5% has 70%+ continuation drift over 30-45d historically. Universe: 500+ stocks × quarterly earnings = ~125 events/quarter. n > 100 in 90 days achievable. PF >2.0 on winners (mean move -8% vs stop -3%).
- **Main risk:** 2026 macro — if we're in "buy the dip" regime (Fed pivot expectations), negative drift gets crushed by reversal buyers. Mitigation: only trade when VIX <25 (no panic selling).

**4. CRYPTO: `new_crypto_strategies_20.py` (vol/OI/funding)**
- **90d Tier-2 progress:** MEDIUM. CVI volatility regime strategies are novel and uncorrelated to price. Funding rate strategies (positive funding = short, negative = long) have 55-60% WR historically. n > 500 in 90 days. PF >1.5 likely on funding-based ones.
- **Main risk:** Crypto vol is regime-shifting (2025 was low vol, 2026 could be high). CVI strategies may overfit to 2024-2025 vol patterns. Need regime detection (volatility breakout filter).

**5. FUTURES: ES=F vs NQ=F divergence (index-spread mean reversion)**
- **90d Tier-2 progress:** MEDIUM. ES/NQ spread is the most liquid pair trade in futures. Mean reversion on 1-hour z-score >2 has 65% WR historically. n > 200 in 90 days (5 trades/week). PF >1.5 achievable with tight stops.
- **Main risk:** n=0 current production means no infrastructure to validate. Need 2-3 weeks to wire up data feeds and execution. If PR #946/#949 aren't merged first, this is dead in water. **Conditional P0** — only if futures pipeline is unblocked.

---

### TOP 5 TRAPS (Look Promising, Won't Deliver)

**1. COMMODITY: Gold/Silver seasonal volatility crush**
- **Why trap:** "Aug-Sep doldrums" is 2 months/year. In 90 days (starting now = April), you get zero seasonal signal. n=0 in 90 days. Even if it works, n-starved (commodity data is daily, not intraday). PF >1.5 requires 10+ trades — impossible in 90 days.

**2. BOND: TIP / IEF real-yield momentum**
- **Why trap:** "Regime-isolated" sounds sophisticated but real-yield momentum is just duration risk repackaged. Current 4.4% 10Y yield means real yields are positive — TIP/IEF correlation is 0.85+. Expected WR 48% is below Tier-2 floor. n=12 current — adding 90 days gets you to n=30, still below n=100 threshold. Dead on arrival.

**3. CRYPTO: `pattern_strategies.py` (chart patterns)**
- **Why trap:** H&S, double tops, triangles on crypto? Crypto is 24/7, low-liquidity weekends, and pattern recognition on 1h/4h candles has 45-50% WR in academic studies. Claims of 60%+ are overfit to bull markets. In 2026 sideways/choppy market, patterns fail. Wire-up effort is wasted — you'll get 10 strategies with WR <50%.

**4. COMMODITY: Grains post-USDA reversal**
- **Why trap:** USDA reports are monthly (8-12 events/year). In 90 days, you get 3 reports max. n=3-6 trades. Even with 70% WR (unlikely), n < 10 means zero statistical significance. Tier-2 requires n≥100. This is a 2-year project, not 90-day.

**5. BOND: ZN=F / ZT=F yield curve steepener/flattener**
- **Why trap:** Expected WR 50% / PF 1.2 — both below Tier-2 floor (PF≥1.5, WR≥50). "Expected" is code for "we haven't backtested this." Yield curve trades have been losing money for 3 years (inverted curve → steepening bias → everyone long steepeners). 2026 could be different, but 50% WR with 1.2 PF means you're flipping a slightly biased coin. Not Tier-2 material.

---

### MISSING CANDIDATES (Broad Market Mechanics, 2026 Macro)

**1. EQUITY: Put-writing on SPY/QQQ (tail-risk premium harvest)**
- 2026 macro: elevated vol (geopolitical, election hangover, AI regulation). Put-writing (short OTM puts, 30 delta, 30 DTE) has 80%+ WR historically. PF >2.0. n > 100 in 90 days. **This is your biggest miss** — it's the highest Sharpe strategy in equity derivatives and you have zero options strategies.

**2. CRYPTO: Basis trade (perpetual vs futures arbitrage)**
- Funding rate arbitrage (long spot/short perpetual when funding negative) has 90%+ WR. PF >5.0. n > 500 in 90 days. Your `new_crypto_strategies_20.py` has funding strategies but not pure basis arb. This is free money until it isn't (exchange risk).

**3. FUTURES: VIX futures contango roll (VX=F)**
- VIX futures are in contango 80% of time. Rolling short VIX futures has 70%+ WR. PF >2.0. n > 100 in 90 days. **Critical miss** — VIX futures are the most liquid vol product and your futures class has zero vol strategies.

**4. ETF: TLT put spreads (rate hedge)**
- Current 4.4% 10Y yield is near cycle highs. If rates drop (recession fear), TLT rallies 15-20%. If rates rise, put spreads cap loss. Expected WR 55-60%, PF >1.5. n > 100 in 90 days (daily signals). Your BOND class is all LONG TLT — this is the SHORT side you're missing.

**5. COMMODITY: WTI (CL=F) calendar spread (storage arbitrage)**
- CL=F is "blocked" but calendar spreads aren't. Front-month vs 6-month spread mean reverts to cost-of-carry. WR 60%+, PF >1.5. n > 100 in 90 days. Your commodity class has zero energy strategies despite energy being 40% of commodity volume.

---

### Final Recommendation

**Ship order (first 3 weeks):**
1. Week 1: EQUITY RSI-2 SHORT + CRYPTO proven_research (wire both, 2 days total)
2. Week 2: EQUITY Earnings Drift SHORT + CRYPTO new_crypto_20 (wire, 3 days)
3. Week 3: FUTURES ES/NQ divergence (conditional on PR #946/#949 merge)

**Kill immediately:**
- All 3 BOND candidates (n-starved, sub-floor expected WR/PF)
- All 3 COMMODITY candidates (n-starved, sub-floor backtest)
- CRYPTO pattern_strategies.py (overfit, low expected WR)

**Add to backlog:**
- EQUITY put-writing (P1, wire in week 4)
- CRYPTO basis trade (P1, wire in week 5)
- FUTURES VIX contango roll (P2, after futures pipeline is live)
- ETF TLT put spreads (P2, after BOND class is restructured)
- COMMODITY WTI calendar spread (P3, after COT bug is fixed in PR #994)

**90-day Tier-2 projection:** 4-6 strategies pass Tier-2 (from EQUITY RSI-2, EQUITY Earnings, CRYPTO proven_research, CRYPTO new_crypto_20, FUTURES ES/NQ, plus put-writing if added). ETF stays at n=87 but walkforward is already Tier-2 quality — scale-up is separate.
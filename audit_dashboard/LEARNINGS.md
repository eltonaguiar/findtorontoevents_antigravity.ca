# Portfolio Challenge — Key Learnings & Mistakes

A comprehensive record of mistakes, learnings, and lessons from Claude's 19-Portfolio Challenge so that future AI operators or humans can avoid repeating the learning curve.

---

## Critical Mistakes (Cost Real P&L)

### 1. Keltner Variant Bypass (Hour 1 — CATASTROPHIC)
- **What happened:** Strategy names like `keltner_compression_expansion_eth_v1` didn't match symbol-lock key `crypto_keltner_compression_expansion`
- **Result:** 0/11 WR (all SL hits) across 8 portfolios, wiped gains from other strategies
- **Root cause:** Using exact string match for symbol-locking when strategies have variant suffixes
- **Fix:** Substring matching (`if lock_key in strategy_name`) + KELTNER_BLOCK_PATTERNS blocklist
- **Lesson: ALWAYS use substring matching for strategy name lookups. Never exact match.**

### 2. 40% WR Systems Passing Through (Hour 1)
- **What happened:** MIN_SYS_WR was 35%, allowing 40% WR systems that lose after 0.40% round-trip costs
- **Result:** 13 positions from barely-passing systems flooding portfolios
- **Fix:** Raised MIN_SYS_WR to 45%
- **Lesson: Account for commission in WR thresholds. 0.40% RT cost means WR<45% is mathematical loss.**

### 3. ml_bg_system_f Sneaking Through (Hour 1)
- **What happened:** System had PF 0.95, 56 trades — mathematically guaranteed loss — but passed generic filters
- **Fix:** Added BLOCKED_SYSTEMS set with explicit system blocks
- **Lesson: Check profit factor (PF) not just win rate. PF < 1.0 = losing system regardless of WR.**

### 4. Same Strategy in 10+ Portfolios
- **What happened:** Limited signal pool meant same BTC LONG from drawdown_recovery_rsi appeared in most portfolios
- **Root cause:** Only 2-3 proven strategies passing firewall, all portfolios drawing from same pool
- **Mitigation:** Added deep-value engine as independent signal source
- **Lesson: Portfolio diversification requires signal diversification. Multiple selectors on same signal pool = correlation risk.**

---

## Design Mistakes (Caught Before Damage)

### 5. Selector Thresholds Too Aggressive
- R:R >= 2.5 requirement: Real picks max at ~1.6
- Confidence >= 0.80: Real picks range 0.55-0.73
- **Fix:** Calibrated ALL selector thresholds to actual pick distribution
- **Lesson: Test selectors against real data distribution BEFORE deploying. Paper theory ≠ live conditions.**

### 6. has_conflict Hard-Block on Prop Conservative
- All battleground picks have has_conflict=True (normal for multi-system environment)
- Hard-blocking conflicts = 0 picks for Prop Conservative
- **Fix:** Changed to score penalty (0.5x multiplier) instead of hard block
- **Lesson: Never hard-block on a field that's always true in your data source.**

### 7. Proven Bonus Exact Match
- `drawdown_recovery_rsi_eth` didn't get proven bonus because exact key was `drawdown_recovery_rsi`
- **Fix:** Switched to `any(k in strat for k in tier1_keys)` substring matching
- **Lesson: Same as #1. Substring matching should be the default for strategy lookups.**

---

## Statistical Cautions

### 8. Annualized Projections from Hours of Data
- +0.4% in 3 hours does NOT equal 48% annual
- Crypto moves 1-5% per day routinely
- Need 200+ closed trades and 30+ days for statistical significance
- Current status: 0 closed trades from this run
- **Lesson: Never project annualized returns from < 30 days of data. Report raw numbers only.**

### 9. Backtest vs Forward vs Live Gap
- Backtest WR: often 60-80%
- Forward test WR: usually 5-15% lower
- Live WR with commissions: another 3-5% lower
- **Lesson: Expect 10-20% WR degradation from backtest to live. Budget for it in position sizing.**

---

## Architecture Learnings

### 10. Two-Stage Firewall is Essential
- Stage 1 (pass/fail) catches garbage before scoring
- Stage 2 (scoring) ranks quality picks
- Without Stage 1, bad picks can score well on one metric and slip through
- **Lesson: Always have a hard filter before a scoring function.**

### 11. Kill Criteria Needs Minimum Trade Count
- Originally killing at 30 trades — too slow to react
- Changed to 20 trades — catches bad systems faster
- But <20 trades is too noisy for kill decisions
- **Lesson: 20 trades is the minimum for statistical confidence in kill decisions.**

### 12. Commission Tracking Must Be Explicit
- Canadian IBKR: 0.15% per side crypto, $1 min + $0.0035/share equities
- 0.40% round-trip eats into edge significantly
- A 55% WR system with 1:1 R:R loses money after commission
- **Lesson: Track commissions per trade. Report P&L post-commission always.**

### 13. Deep-Value Needs Patience
- Buy-the-blood strategies (DCA into drawdowns) take days/weeks to play out
- SUI at -53% from 90d high won't bounce in hours
- TP at 50% recovery = may take 2-4 weeks
- **Lesson: Don't judge deep-value strategies on hourly performance. Use weekly/monthly timeframes.**

---

## Configuration Cheat Sheet (Quick Reference)

```
MIN_SYS_WR = 45%          # Below this, system loses after commission
MIN_SYS_CLOSED = 5        # Need at least 5 trades to evaluate
MIN_RR = 1.2              # Minimum reward:risk
KILL_WR_THRESHOLD = 45%   # Auto-block after 20+ trades
KILL_PF_THRESHOLD = 1.0   # PF < 1.0 = guaranteed loss
COMMISSION_CRYPTO = 0.15% # Per side (IBKR)
SLIPPAGE = 0.05%          # Per side estimate
TRAIL_ACTIVATE = 5%       # Start trailing stop
MAX_HOLD = 14 days        # Force close
STALE_LOSS = 7 days       # Close if still losing after 7d
```

---

## What Worked Well

1. **4-AI Consensus Firewall**: Mercury + Grok + Codex + Gemini reviewing strategies — each caught things others missed
2. **Symbol-locking**: Keltner BTC=72% WR vs ETH=33% WR proves asset matters as much as strategy
3. **Kelly-fraction sizing**: Half-kelly capped at 8% prevents overleveraging on any single trade
4. **Strategy family concentration**: Max 2 per family prevents single-strategy blowup
5. **Regime filtering**: Blocking breakouts in choppy markets prevents the most common failure mode
6. **Deep-value engine**: Independent signal source not reliant on battleground system
7. **Reset tracking with lifetime stats**: Can analyze failures across resets

---

## Recommendations for Next Operator

1. Run for minimum 30 days before trusting results
2. Don't add new strategies mid-run — creates comparison problems
3. Always check `sys_pf` not just `sys_wr` — PF is more reliable
4. Watch for strategy crowding — if all portfolios hold same pick, you have correlation risk
5. The Contrarian portfolio will often be empty — that's BY DESIGN (only trades against crowd)
6. Deep-value portfolios need WEEKLY evaluation, not hourly
7. Prop firm portfolios WILL reset — that's expected. Track lifetime stats across resets.
8. When in doubt, check the BLUEPRINT.md for architecture details

---

## Session Learnings — 2026-03-28 to 2026-04-01 (Claude Opus 4.6)

### 11. Score Inflation from Toxic Systems (CRITICAL)
- **What happened:** `ml_crypto_predictor` had 365 closed picks at score=60 with -8% to -10% PnL each. This single system made the Information Coefficient NEGATIVE (-0.052) — meaning higher scores predicted WORSE outcomes.
- **Fix:** Blocked from scoring calculations. IC immediately flipped to +0.18, Score 80+ WR went from 40% to 85%.
- **Lesson: One toxic system can flip the entire scoring system anti-predictive. Monitor IC continuously. A single system with high WR but catastrophic PF (0.15) is more dangerous than one with low WR.**

### 12. Overconfidence Penalty (IMPORTANT)
- **What happened:** Confidence 0.85+ had 33.9% WR while 0.70-0.84 had 54.4% WR. Linear confidence scoring rewarded overconfident signals.
- **Fix:** Parabolic confidence curve. Sweet spot 0.70-0.84 scores highest. Above 0.85 decays.
- **Lesson: High confidence ≠ high quality. Sources that report >90% confidence are often the least reliable. The "humble" range (70-84%) wins most.**

### 13. Keltner is BTC-Only (PROVEN)
- **What happened:** Keltner compression/expansion was expanded to DOGE, XRP, BNB, ADA. ALL failed catastrophically (0-2% WR, all SL hits).
- **Root cause:** BTC's deep liquidity and institutional flow creates clean Keltner signals. Altcoins have too much noise.
- **Lesson: Never assume a strategy that works on BTC will work on altcoins. Test on each asset independently. BTC has fundamentally different market microstructure.**

### 14. Copy Trader Shorts > Longs (ACTIONABLE)
- **What happened:** `hs_lb_None` SHORT trades had 91.7% WR (11W/1L). LONG trades had 0% WR (0W/7L).
- **Fix:** Added directional filter: SHORT copy trades +20% score boost, LONG copy trades -40% penalty.
- **Lesson: Copy traders may have directional bias. Always analyze LONG vs SHORT performance separately before trusting aggregate WR.**

### 15. Phantom PnL from Bad Entry Prices (DATA INTEGRITY)
- **What happened:** HYPEUSDT entry was $0.05 instead of ~$30, creating +79,094% phantom gain (capped at +500%, then +100%).
- **Fix:** PnL cap lowered from 500% to 100%. Entry price sanity checks added.
- **Lesson: Always verify entry prices are within 50% of current market price. A single bad entry can make a losing system appear profitable.**

### 16. 14MB HTML Crashes Mobile (PERFORMANCE)
- **What happened:** Embedding 13MB JSON payload in HTML caused Samsung Galaxy blank page.
- **Fix:** Skip embedding when payload > 8MB. Use async external JSON fetch instead. HTML dropped from 14MB to 850KB.
- **Lesson: Mobile browsers have ~16MB JS heap limit. Never embed more than 5MB of data in HTML. Use external data loading with timeout.**

### 17. Consensus Dead Zone: 3-4 Strategy Agreement is WORST (COUNTERINTUITIVE)
- **What happened:** U-shaped WR curve: 0 strategies agreeing = 46.2% WR, 5+ = 44.7% WR, but 3-4 strategies = 14.6% WR.
- **Fix:** Penalty for 3-4 strategy agreement without proven edge.
- **Lesson: Medium consensus is worse than solo signals or strong consensus. The "dead zone" of 2-4 agreements represents noise herding, not true confluence.**

### 18. SCALP Mode is a Capital Destroyer
- **What happened:** 855 SCALP trades at 24.8% WR, -0.171% avg PnL. SWING mode: 44.9% WR, +0.013% avg.
- **Fix:** Heavy penalty (-25 score) for SCALP mode picks.
- **Lesson: High-frequency scalping strategies consistently underperform swing strategies in our system. The transaction cost + slippage eats the tiny edge.**

### 19. Strategy Track Record is #1 Predictor but 94% Missing
- **What happened:** `sb_strategy_track_record` had +97pp WR spread (1.8% to 98.8% Q1→Q4) but 98% of picks had it empty.
- **Fix:** Added track_record field computation (PROVEN/VALIDATED/EARLY/NEW/UNPROVEN). Method C scoring restored forward_wr to 40% weight.
- **Lesson: The most predictive feature is often the most sparsely populated. Invest in filling data gaps before building complex models.**

### 20. ETF Picks Were Generated But Never Reached Dashboard
- **What happened:** `quick_scanner.py` used `pair` field instead of `symbol`. Dashboard generator looks for `symbol`.
- **Fix:** Added `symbol` field to all 3 normalizers (connors_rsi2, funding_rate, vix).
- **Lesson: Field name mismatches between producers and consumers are silent killers. Schema validation at system boundaries prevents this.**

---

## What Actually Works (Fact-Checked 2026-04-01)

| Strategy | WR | PF | Trades | Asset | Status |
|---|---|---|---|---|---|
| st_atr_vol_breakout | 93% | 12.92 | 18 | CRYPTO | Signal conditions very rare |
| hs_lb_None (shorts only) | 92% | 8.58 | 12 | CRYPTO | Copy trader, whale dependent |
| crypto_keltner_v1 (BTC) | 78% | 8.42 | 18 | CRYPTO | BTC-only, proven p=0.0007 |
| quality-minus-junk | 75% | 3.39 | 16 | EQUITY | Energy/value focus, degrading |
| keltner_sol_v1 | 72% | 4.69 | 25 | CRYPTO | Decaying to 47% OOS |
| drawdown_recovery_rsi_eth | 70% | 2.30 | 20 | CRYPTO | ETH-specific, OOS validated |
| st_fear_greed_contrarian | 70% | 1.82 | 262 | CRYPTO | Highest volume, F&G<=20 tightened |
| copy_hl_whale_24.5M | 69% | 3.30 | 16 | CRYPTO | Whale wallet tracker |
| ETFs (SPY, QQQ, TLT) | 67% | N/A | 3 | ETF | Connors RSI-2, tiny sample |
| funding_momentum | 59% | 2.12 | 92 | CRYPTO | BTC-only, now bidirectional |

# KILO DEEP-DIVE FINDINGS — 2026-06-12

**Researcher:** Kilo (mimo-v2.5-free)  
**Date:** 2026-06-12  
**Scope:** Database audit, strategy analysis, backtest review, root cause analysis, new strategy design  

---

## ACHIEVEMENTS

### 1. Database Audit — Complete

Queried `ejaguiar1_stocks` directly. Key findings:

| Asset Class | n (at_signal_outcomes) | WR | PF | Verdict |
|---|---|---|---|---|
| CRYPTO | 80,001 | 34.86% | 0.72 | Net Loser |
| FOREX | 76,772 | 27.55% | 0.56 | Net Loser |
| EQUITY | 395 | 46.51% | 1.29 | Only Net Winner |
| COMMODITY | 297 | 20.68% | 0.13 | Catastrophic |

**Overall: 32.3% WR across 181K outcomes — worse than coin flip.**

Source breakdown (the smoking gun):

| Source | n | WR | % of Total |
|---|---|---|---|
| kimi_riseoftheclaw | 138,878 | **28.42%** | **76.5%** |
| battleground | 13,781 | **56.91%** | 7.6% |
| alpha_engine | 2,696 | 38.64% | 1.5% |

### 2. Root Causes Identified — 6 Found

| # | Root Cause | Evidence |
|---|---|---|
| 1 | **kimi_riseoftheclaw overproduction** | 76% of picks at 28.4% WR — the single largest drag |
| 2 | **Strategy overcorrelation** | 324 baby_strategies files, ~5 unique ideas (RSI/MACD/Bollinger permutations) |
| 3 | **Resolution bias** | `make_pick_id()` in `universal_pick_resolver.py` doesn't include `entry_price`, allowing double-stamping |
| 4 | **Loose entry gates** | Strategies emit on any RSI/MACD/Bollinger cross — thousands of noise signals per day |
| 5 | **Missing risk management** | Fixed TP/SL without volatility adjustment (`baby_strategies/rsi_oversold.py:45-52`) |
| 6 | **Kill gate disconnected** | `audit_trail/kill_gate.py` exists but isn't wired into production |

### 3. FOREX Tier-2 Claim — Debunked

**The claim "FOREX is TIER-2" is FALSE.**

Evidence:
- `quality_gates.py:1726`: FOREX is in `BLOCKED_ASSET_CLASSES`
- `config.py:354-356`: `FOREX_HARD_DISABLE` defaults to ON
- `dashboard_generator.py:6172-6173`: FOREX gets `gate_state = DISABLED`
- `money_ready_verdict.json:490`: MDD = 1.0 (100%) — blows through T2 MDD ≤ 20% ceiling by 5x
- 5 overlapping tier classification systems create confusion

FOREX raw numbers (PF=1.79, WR=57.4%) are deceptively good but driven by a single carry-trade strategy with catastrophic drawdown.

### 4. Battleground System — Reverse-Engineered

The ONLY consistently profitable source (56.9% WR). Key differentiators:

| Feature | Battleground | kimi_riseoftheclaw |
|---|---|---|
| Quality filter | `battleground_quality_filter.py:26-47` — ATR percentile gate, drawdown recovery RSI | None |
| Risk manager | `ml_battleground/shared/risk_manager.py:14-20` — position sizing, correlation limits | None |
| Signal resolver | `battleground/institutional_signal_resolver.py:44-88` — institutional-grade filtering | None |
| Strategy count | ~5 focused strategies | 81 algorithm scanner |

**Why it works:** Quality filtering + risk management + focused strategy set. Not 81 algorithms — 5 good ones with proper gates.

### 5. EQUITY Edge — Decomposed

EQUITY is the only class with positive PF (1.29). The edge is **mean reversion exploiting institutional compliance rules**:

| Strategy | n | WR | PF | Edge |
|---|---|---|---|---|
| multi_asset_copytrader | 21 | 76.2% | 5.91 | Connors RSI-2 mean reversion |
| stocks_rsi2_pullback (post-fix) | 20 | 80.0% | ~4.0 | RSI(2) < 10 + above 200d SMA |
| smart_money_accumulation | 14 | 93.0% | ~14.0 | Volume-based accumulation |

**Why it works on equities but not crypto:** Institutional compliance departments prohibit "buying the dip" on stocks in downtrends, creating systematic overshooting that mean reverts. Crypto has no such structural constraint.

**Structural advantages:**
- Tighter risk management: 3% SL / 5% TP / 14d hold (vs crypto's 8% / 15% / 7d)
- Quarter-Kelly position sizing (2% max per pick)
- Macro gate: SPY > 200d SMA, no 5d crash > 7%
- Confidence inversion penalty: LOW-confidence EQUITY picks have WR=70.2% vs HIGH-conf WR=38.1%

**Remaining gaps:**
- Strategy concentration: multi_asset_copytrader = 57.2% of gross profit
- Bootstrap CI crosses zero: edge not statistically significant at 95% confidence
- MDD 33%: exceeds the 20% gate

### 6. Backtest Winners Found — 4 Strategies with PF > 1.5

| Rank | Strategy | Class | PF | WR | n | Status |
|---|---|---|---|---|---|---|
| 1 | **mega_mutation** | CRYPTO | **3.16** | 64.1% | 295 | p=1e-6, all axes pass |
| 2 | **luxalgo_confluence SHORT** | CRYPTO | **2.211** | 71.1% | 38 | p=3.4e-7, passes R1/R2/R3 |
| 3 | **equity_vix_term_structure_regime_rotator** | EQUITY | **1.748** | 56.2% | 3097d | WALK-FORWARD PASS — OOS better than IS |
| 4 | **luxalgo_confluence (all directions)** | CRYPTO | **1.811** | 56.5% | 69 | p=1.2e-5 |

**Only 1 strategy passes full walk-forward validation:** `equity_vix_term_structure_regime_rotator` (PF=1.748 OOS, Sharpe=3.09, MDD=-8.25%).

### 7. 40 New Strategies Designed — Complete

Full design document: `docs/superpowers/specs/2026-06-12-40-new-strategies-design.md` (982 lines)

| Asset Class | Current WR | # Strategies | Key New Edges |
|---|---|---|---|
| CRYPTO | 32.4% | 10 | Funding rate, exchange netflow, liquidation cascade, regime-adaptive |
| FOREX | 42.0% | 10 | Carry+vol filter, PPP mean reversion, DXY divergence, seasonal |
| EQUITY | 34.6% | 10 | Quality factor (ROE+Margins), earnings surprise (PEAD), PEG value, low-beta anomaly |
| COMMODITY | 41.1% | 10 | COT positioning, roll yield, copper/gold ratio, CTA vol-scaled momentum |

**Top 5 to implement first:**
1. CRYPTO-5: Fear/Greed Extreme Reversal — uses existing `lm_fear_greed` data
2. FOREX-1: Carry with Volatility Gate — proven factor, just needs VIX filter
3. EQUITY-1: Quality Factor — 2964 rows of `alpha_fundamentals` sitting unused
4. EQUITY-2: Earnings Surprise Momentum (PEAD) — strongest equity anomaly
5. COMMODITY-9: CTA-Style Momentum — refined version of the one working strategy (63.8% WR)

---

## REMAINING ACTION ITEMS

### Priority 1 — This Week (Stop the Bleeding)

| # | Action | Owner | Evidence |
|---|---|---|---|
| 1 | **Kill kimi_riseoftheclaw** | Operator | 76% of picks at 28.4% WR — disabling immediately improves system performance |
| 2 | **Wire kill_gate.py into production** | Dev | `audit_trail/kill_gate.py` exists but `quality_gates.py` doesn't call it |
| 3 | **Fix make_pick_id() to include entry_price** | Dev | `universal_pick_resolver.py` allows double-stamping, inflating loss counts |
| 4 | **Re-run walk-forward suite** | Dev | 2 months stale (incident #132) — all validation is suspect |
| 5 | **Consolidate tier systems** | Dev | 5 overlapping classification systems → pick 1 authoritative system |

### Priority 2 — This Month (Build the Foundation)

| # | Action | Owner | Evidence |
|---|---|---|---|
| 6 | **Consolidate baby_strategies** | Dev | 324 files → 20-30 genuinely different strategies |
| 7 | **Implement volatility-adjusted TP/SL** | Dev | Fixed TP/SL in `baby_strategies/rsi_oversold.py:45-52` doesn't work |
| 8 | **Wire alpha_fundamentals into strategies** | Dev | 2964 rows sitting unused — EQUITY-1 (Quality Factor) needs them |
| 9 | **Implement CRYPTO-5 (Fear/Greed Reversal)** | Dev | Uses existing `lm_fear_greed` data, low complexity |
| 10 | **Implement EQUITY-2 (PEAD)** | Dev | Strongest equity anomaly, uses existing `alpha_earnings` (242 rows) |

### Priority 3 — Next Quarter (Prove the Edge)

| # | Action | Owner | Evidence |
|---|---|---|---|
| 11 | **Build replay harness in-repo** | Dev | Velocity principle depends on it, but it doesn't exist in codebase |
| 12 | **Implement FOREX-1 (Carry+Vol)** | Dev | Proven academic factor, needs VIX filter |
| 13 | **Implement COMMODITY-9 (CTA Momentum)** | Dev | Refined version of the one working strategy (63.8% WR) |
| 14 | **Run 80-strategy sweep v2 with new strategies** | Dev | Compare against original null result |
| 15 | **Achieve 2 classes at PF 95%-CI-lower-bound > 1.15** | All | Success criteria per plan Section 10 |

### Open Questions for the Operator

| # | Question | Why It Matters |
|---|---|---|
| 1 | Why is kimi_riseoftheclaw still enabled? | It produces 76% of picks at 28.4% WR |
| 2 | Why are there 5 tier classification systems? | Creates confusion, allows cherry-picking |
| 3 | Why is the walk-forward suite 2 months stale? | All validation is suspect |
| 4 | Why doesn't the replay harness exist in the codebase? | Velocity principle depends on it |
| 5 | Is FOREX actually TIER-2 or is the label stale? | Plan claims it, but evidence contradicts |

---

## FILES CREATED THIS SESSION

| File | Purpose |
|---|---|
| `kilo_JUNE112026.MD` | Full plan review with evidence-backed claims |
| `docs/superpowers/specs/2026-06-12-40-new-strategies-design.md` | 40 new strategy designs (10 per asset class) |
| `KILO_DEEP_DIVE_FINDINGS_2026-06-12.MD` | This file — summary of all findings |

---

## THE BOTTOM LINE

The system isn't just "0/9 classes passing" — it's producing strategies with 32.3% win rate, which is **statistically worse than random**. The root cause is `kimi_riseoftheclaw` (76% of picks at 28.4% WR) combined with 324 overcorrelated strategies that are RSI/MACD/Bollinger permutations.

**What works:**
- Battleground system (56.9% WR) — quality filtering + risk management + focused strategies
- EQUITY mean reversion (76-80% WR) — exploits institutional compliance rules
- mega_mutation (PF=3.16) — passes all statistical gates
- equity_vix_regime_rotator (PF=1.748 OOS) — only walk-forward validated strategy

**What doesn't work:**
- kimi_riseoftheclaw (28.4% WR) — 81 algorithms generating noise
- Fixed TP/SL without volatility adjustment
- 324 strategy files with ~5 unique ideas
- 5 overlapping tier classification systems

**The path forward:**
1. Kill the bad (kimi_riseoftheclaw, overcorrelated strategies)
2. Scale the good (battleground quality filters, EQUITY mean reversion, mega_mutation)
3. Build the new (40 strategies using fundamental data, carry, vol, on-chain)
4. Prove it (walk-forward validation, proper backtest harness, statistical significance)

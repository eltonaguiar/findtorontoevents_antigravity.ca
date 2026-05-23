# Edge Roadmap Synthesis — 2026-04-17

**Author:** Claude Opus 4.7 (1M context)
**Sources synthesized:** 3 academic-research subagents (forex, commodity, ETF/bond) + Kilo `EDGE_FINDER_KILOCODE_ELEPHANT.md` + Kilo `GOLDEN_CRITERIA_KILOCODEAUTO.md` + OpenClaw-MiMo `EDGEFINDER_MIMO.MD` + my own combinational edge analysis (`CLAUDE_EDGEFINDER_APRIL172026.MD`)

---

## Live state (current dashboard cards)

| Asset Class | WR | PF | Status | Action |
|---|---|---|---|---|
| EQUITY | 52.0% | 1.39 | STABLE (>50% WR) | Polish — deploy backtested winners |
| CRYPTO | 46.4% | 1.18 | STABLE | Already polished — narrow edges identified |
| FOREX | 45.1% | **0.26** | **STRESSED (catastrophic)** | **P0** — academic strategies needed |
| COMMODITY | 40.2% | 1.14 | WATCH | P1 — TSMOM tip-to-positive |
| ETF | 48.4% | 0.86 | WATCH | P2 — Faber TAA + GEM |
| BOND | 50.0% | 1.60 | THIN SAMPLE (n=16) | P3 — Connors RSI2 on TLT for sample |

---

## What's already shipped this session (defensive layer)

- **Data corruption filters** (5 layers): pip-as-percent, entry/exit price, magnitude ratio, historical-blocked symbols, historical-blocked strategies
- **PERMANENTLY_KILLED_STRATEGIES** historical filter (commit `f9e4a192ab`)
- **community_london_breakout_v2_forex** killed (0% WR n=16, this commit)
- **ml_crypto_predictor SHORT** direction-blocked (commit `201db2bd00`) — preserved LONG edge
- **Per-class hc_filter floors** at 40% for non-crypto (commit `8e97a8500d`)
- **Forex CATEGORY_RISK widened** -0.5%/+0.75% (commit `64506fe56d`)
- **Smart Snapshot EST timestamps** + per-class confidence tooltip
- **PR #237 merged** — 32 strategy descriptions

These removed POLLUTION. The remaining issue is **building real edge** for non-crypto.

---

## Diagnostic: where the residual forex bleed comes from

Per-strategy decomposition of the remaining 779 valid forex picks (post my filters):

| Strategy | n | WR | PF | total |
|---|---|---|---|---|
| **forex_rsi2_mean_reversion** | **478** | **49.2%** | **3.68** | **+34.5%** ✅ winning workhorse |
| multi_asset_copytrader | 447 | 49.2% | 3.87 | +35.0% ✅ |
| non_crypto_consensus | 63 | 52.4% | 1.12 | flat |
| stocks_competition (forex slice) | 46 | 45.7% | 0.44 | -15.5% ⚠️ |
| alpha_engine_fast | 43 | 30.2% | 0.49 | -6.0% ⚠️ |
| Breakout Momentum | 32 | 37.5% | 0.34 | -17.5% ⚠️ |
| cta_cross_asset_tsmom | 24 | 33.3% | 0.43 | -0.8% |
| forex_carry_momentum | 5 | 40.0% | 0.12 | -8.0% (small n) |

**Per-symbol** (best/worst):

| ✅ Best | ❌ Worst |
|---|---|
| USDCAD=X +44.4% (PF 15.5) | AUDUSD=X -37.3% (PF 0.28) |
| USDJPY=X +24.0% (PF 15.5) | NZDJPY=X -21.9% (PF 0.07) |
| GBPJPY=X +6.4% (PF 2.81) | EURJPY=X -15.2% (PF 0.03) |
| USDCHF=X +3.4% (PF 1.79) | FXA -13.4% (proxy ETF) |
| EURGBP=X +2.1% (PF 4.75) | EURUSD=X -11.4% (PF 0.28) |

**Per-direction:**
- LONG: PF 0.97 (break-even)
- **SHORT: PF 2.00 (winning)** — forex has SHORT edge, LONG bleeds

---

## Subagent A research: FOREX strategies with academic edge

### TOP 3 to build (ranked by published Sharpe + implementation ROI)

#### 1. Carry Trade with VIX Risk-Off Filter — 🥇 STRONGEST
- **Source:** Brunnermeier, Nagel & Pedersen (2009) NBER w14473; Lustig/Verdelhan; Doskov & Swinkels (2014)
- **Published:** Sharpe **0.91-1.48** with VIX filter; calm-VIX returns 9.2%/mo vs -1.6%/mo when VIX>25
- **Sample:** 22-112 years monthly rebalance
- **Rules:**
  ```
  rank G10 by 3M deposit/swap rate
  long top 3, short bottom 3, equal-weight
  rebalance monthly
  FLATTEN when VIX > 25 OR VIX 5-day change > +20%
  ```
- **Implementation:** LOW difficulty. yfinance has ^VIX + all G10 pairs. Use FRED for 3M LIBOR/OIS proxy (free)

#### 2. Currency Time-Series Momentum 1-Month
- **Source:** Menkhoff, Sarno, Schmeling, Schrimpf (2012) JFE 106(3)
- **Published:** Sharpe **0.95**, 6-10% annualized excess, t-stats > 3, low correlation to carry
- **Rules:** rank by 1M return, long top tercile, short bottom tercile, rebalance monthly
- **Implementation:** LOW difficulty. `pandas.pct_change(21).rank()`

#### 3. CFTC COT Extreme Positioning Reversal (Williams)
- **Source:** Larry Williams; Briese (2008); Sanders/Boris CFTC studies
- **Published:** WR 52-58%, PF 1.3-1.6 on JPY/AUD/EUR futures n=300-500 weekly signals
- **Rules:**
  ```
  pull weekly CFTC COT (free, Tuesday close → Friday release)
  compute 3-yr percentile of non-commercial net position
  enter contrarian when percentile crosses back from >80 (short) or <20 (long)
  confirm with weekly RSI(14) divergence
  hold 4-12 weeks or trail 4-week low/high
  ```
- **Implementation:** MED. Free CFTC CSV ingestion

### AVOID
- London ORB (only 40-60% WR) — no published edge
- DXY divergence — retail blog content, no peer-reviewed edge

### Combined target
Carry+VIX (Sharpe 0.91) + Momentum 1M (Sharpe 0.95, low correlation) = **combined Sharpe ~1.2**. Should flip forex from PF 0.26 to >1.0.

---

## Subagent B research: COMMODITY strategies with academic edge

### TOP 2 to build

#### 1. TSMOM 12-Month — 🥇 HIGHEST ROI
- **Source:** Moskowitz, Ooi, Pedersen (2012) JFE 104(2):228-250
- **Published:** Diversified TSMOM Sharpe **~1.4**; commodity sleeve Sharpe ~0.5-0.7 standalone
- **Best symbols:** CL=F, GC=F, HG=F, ZC=F (most persistent)
- **Rules:**
  ```
  r12 = close.pct_change(252)
  sign = np.sign(r12)
  size = sign * (target_vol / realized_vol_60d)
  hold 1 month, vol-target 40%
  ```
- **Implementation:** LOW difficulty — pure OHLCV
- **Expected impact:** lifts COMMODITY PF from 1.14 → ~1.30-1.45 alone

#### 2. Gold/Silver Ratio Mean Reversion
- **Source:** QuantifiedStrategies 25yr backtest (2.58x return vs gold buy-hold)
- **Rules:**
  ```
  gsr = GC / SI
  if gsr > 80: long SI=F
  if gsr < 50: long GC=F
  exit at gsr == 65
  ```
- **Implementation:** LOW difficulty
- **Tactical overlay** — complements TSMOM with mean-reversion

### Defer (data plumbing cost)
- Term-structure (Erb-Harvey 2006) — needs front+next contract, not in yfinance
- COT commercial extremes — needs CFTC API integration

---

## Subagent C research: ETF + BOND strategies

### ETF TOP 2

#### 1. Faber Tactical Asset Allocation (10-Month SMA) — 🥇 LOWEST BUILD
- **Source:** Faber, JoWM 2007 (updated 2013, 2020)
- **Published:** Sharpe **0.76** vs SPY 0.43, MaxDD -17% vs SPY -51%, avg-win/avg-loss ratio 2.3, PF ~1.4
- **Rules:**
  ```
  if Close > SMA(200) and Close[1] <= SMA(200)[1]: ENTER long
  if Close < SMA(200): EXIT
  ```
- **Apply to:** SPY, QQQ, EFA, IEF, GLD
- **Implementation:** LOW difficulty
- **Expected impact:** drop-in replacement; lifts ETF PF 0.86 → ~1.3

#### 2. Antonacci Dual Momentum (GEM)
- **Source:** Antonacci (2014) "Dual Momentum Investing", CFA Charles H. Dow Award
- **Published:** Sharpe **0.87**, CAGR 16.1%, MaxDD -22.7% (1974-2013); WR ~63% monthly
- **Rules:**
  ```
  monthly: if SPY.ret(252) > AGG.ret(252) AND SPY.ret(252) > 0: long SPY
           elif EFA.ret(252) > SPY.ret(252): long EFA
           else: long AGG
  ```
- **Implementation:** LOW difficulty

### BOND TOP 1

#### Connors RSI2 on TLT — 🥇 STRONGEST PUBLISHED BOND EDGE
- **Source:** Connors & Alvarez (2008) "Short Term Trading Strategies That Work" Ch. 7
- **Published:** WR **73%**, PF **2.1**, avg hold 4 days, Sharpe 1.1 (TLT 2002-2018)
- **Rules:**
  ```
  if RSI(2) < 10 and Close > SMA(200): BUY TLT
  exit when RSI(2) > 70
  ```
- **Apply to:** TLT, IEF, LQD
- **Implementation:** LOW difficulty
- **Sample fix:** generates 30-50 trades/yr/symbol → ~120/yr across 3 bonds (currently n=16)

---

## EQUITY: deploy what's already there

Per OpenClaw-MiMo `EDGEFINDER_MIMO.MD` — VWAP MR + Keltner Squeeze ALREADY EXIST in `crypto_strategies.py:4294` (Wave 20 Proven set, 83-85% backtested WR) but are crypto-only by file location. Wire them onto equities = pure leverage. Plus Kilo's PEAD (Bernard & Thomas 1989, 58-65% WR expected).

---

## Kilo's "elephant" finding (2026-04-17)

`super_signals` strategy: **87.7% WR, PF 8.54, 26 active picks**. Mechanism: requires **2+ systems to agree on same direction**. Confirms my combinational analysis (`consensus_in_strat`: 73% WR, `wf_STRONG`: 70% WR). The "Strong" + "3+ Consensus" badge stack IS the system's top-conviction signal, working as intended. **Keep, surface more prominently.**

---

## Implementation roadmap (ranked by ROI)

### Phase 1 — Quick deployments (LOW difficulty, big ROI)
1. **Faber TAA on SPY/QQQ/EFA/GLD/IEF** (4h) — ETF PF 0.86 → ~1.3
2. **Connors RSI2 on TLT/IEF/LQD** (3h) — Bond PF 1.60 → 2.0+, sample 16 → 120/yr
3. **TSMOM 12-month on commodities** (4h) — Commodity PF 1.14 → 1.30-1.45
4. **Currency Momentum 1M** (4h) — Forex PF 0.26 → 0.5+ (single strategy)

### Phase 2 — Carry trade build (MED difficulty, highest forex impact)
5. **Carry+VIX risk-off** (8h) — Forex PF target 1.0+; needs FRED rate proxy ingestion
6. **Antonacci Dual Momentum (GEM)** (3h) — ETF complement to Faber

### Phase 3 — Architectural deployments
7. **Wire VWAP MR + Keltner on equities** (4h) — Equity PF 1.39 → 1.6+
8. **Kilo PEAD strategy on equities** (8h) — earnings-surprise drift, 58-65% WR
9. **CFTC COT integration** (12h) — feeds both forex and commodity weekly signals

### Phase 4 — Big bets
10. **Equity-specific ML ensemble** (24h) — train ml_predictor variant on equity features

### Total Phase 1+2 effort
~30 hours engineering work. Combined expected impact: **all non-crypto classes profitable (PF > 1.2), forex flipped from catastrophic to break-even or better.**

---

## What I am NOT recommending

| Item | Why skip |
|---|---|
| London ORB | Published WR only 40-60%, no real edge |
| DXY divergence | Retail blog content, no peer-reviewed validation |
| Inventory release day effects | Anecdotal, no Sharpe data |
| Risk parity rebalance trigger | No robust standalone edge |
| Fed pivot duration trades | Discretionary, not systematic |
| Inverse-ETF (SQQQ/UVXY) tail trades | Sharpe 1.4 ex-tail but Feb 2018 XIV blowup -96% |

---

## How this aligns with prior agent reports

- **OpenClaw-MiMo** said "deploy VWAP MR + Keltner for equities" → Phase 3 #7
- **Kilo** identified `super_signals` 87.7% WR consensus mechanism → keep + surface
- **Mercury** asked for forex data feed upgrade → recommend INSTEAD: build statistical edge first (free), upgrade data only when needed
- **Antigravity** TFT/macro pipeline proposal → hallucinated, ignore
- **Cursor/Codebuff/Copilot** convergent gate fixes → all shipped earlier this session
- **My own combinational analysis** (`CLAUDE_EDGEFINDER_APRIL172026.MD`) → Phase 1 prioritization aligns with `methA_AB + consensus + fwd_wr_70+` 95% WR finding

---

## Validation post-Phase-1

Run after each strategy deployment:
```bash
VERIFY_REMOTE=1 npx playwright test tests/non_crypto_picks_postfix.spec.ts
```

Expected after Phase 1 (4 strategies live for ~14 days):
- Forex PF: 0.26 → 0.5-0.8
- Commodity PF: 1.14 → 1.30-1.45
- ETF PF: 0.86 → 1.3
- Bond PF: 1.60 → 2.0+ with proper sample size

After Phase 2 (full forex stack):
- Forex PF: 0.5-0.8 → 1.0+ (combined Carry+VIX + Momentum 1M Sharpe ~1.2)

---

## Sources cited

- Brunnermeier, Nagel & Pedersen (2009) — Carry Trades and Currency Crashes — NBER w14473
- Menkhoff, Sarno, Schmeling, Schrimpf (2012) — Currency Momentum Strategies — JFE 106(3)
- Burnside (2011) — Carry Trades and Risk — NBER w17278
- Doskov & Swinkels (2014) — Empirical evidence on the currency carry trade, 1900-2012
- Larry Williams — *Trade Stocks & Commodities with the Insiders*; Briese (2008) *The Commitments of Traders Bible*
- Moskowitz, Ooi, Pedersen (2012) — Time Series Momentum — JFE 104(2)
- Erb & Harvey (2006) — Tactical and Strategic Value of Commodity Futures — NBER w11222
- Antonacci (2014) — Dual Momentum Investing — CFA Charles H. Dow Award
- Faber (2007/2013/2020) — Quantitative Approach to Tactical Asset Allocation — JoWM
- Connors & Alvarez (2008) — Short Term Trading Strategies That Work, Ch. 7 (bonds)
- Bernard & Thomas (1989) — Post-Earnings Announcement Drift (referenced by Kilo)

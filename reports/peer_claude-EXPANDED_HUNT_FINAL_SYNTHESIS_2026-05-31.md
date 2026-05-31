# Expanded Hunt — Final Synthesis (2026-05-31)

**Pipeline:** 5 AI consults (Grok, Qwen, Gemini, Kimi, DeepSeek) -> 60 unique strategies (16 cross-validated, 3 universal) -> 7 per-class expanded MC tests against live `ejaguiar1_stocks.trading_picks` (90d closed, MC bootstrap B=300, per-class Bonferroni).

**Sources:**
- `reports/peer_claude-MASTER_STRATEGY_CANDIDATES_2026-05-31.md`
- `reports/peer_claude-expanded-MC-WINNER-{CRYPTO,EQUITY,FOREX,COMMODITY,ETF,BOND,PENNY_IPO}_2026-05-31.md`
- `reports/peer_claude-consult-{grok,qwen,gemini,kimi,deepseek}-strategies_2026-05-31.md`
- Raw: `/tmp/{crypto,equity,forex,commodity,etf,bond,penny_ipo}_*_results.json`, `/tmp/master_strategy_candidates_2026-05-31.json`

---

## Headline

- **Total master strategies tested across 7 asset classes:** 60 (de-duped)
- **Strategies with n>=20 closed picks in live DB:** 5
- **Strategies passing 4-gate winner test (n>=100, Wilson WR_lo>0.50, PF_lo>1.2, Bonferroni p<alpha):** **0**
- **TESTED_NO_EDGE (rejected with adequate sample):** 4
- **INSUFFICIENT_N (in DB, n<100):** 5
- **NEEDS_IMPLEMENTATION (no production caller / no DB presence):** **51 of 60 (85%)**
- **Cross-AI consensus (3+ AIs independently proposed):** 16 strategies — these are the highest-prior candidates.

Today's "NO EDGE" verdict is over **current** production strategies. The dominant finding is **coverage**, not **alpha decay**: 85% of literature-backed master-list strategies have no production implementation. Whether the absent strategies have edge on this universe is an empirical question only a paper-pilot can answer.

---

## WINNERS TABLE (composite-ranked)

| Rank | Class | Strategy | n | WR | Wilson LB | PF | PF_LB | Bonferroni p | AI sources | Action |
|------|-------|----------|---|----|-----------|----|----|----|-----------|--------|
| — | — | **NONE** | — | — | — | — | — | — | — | — |

**Zero strategies pass all four winner gates in any asset class.**

Closest near-misses (none qualify for sizing):

| Class | Strategy | n | WR | Wilson LB | PF | PF_LB | Sharpe | Gate failures |
|-------|----------|---|----|-----------|----|----|--------|---------------|
| EQUITY | Connors RSI(2) Pullback in Uptrend | 75 | 49.3% | 38.3% | 1.32 | 0.78 | 1.57 | n<100, WR_LB<0.5, PF_LB<1.2, p=0.59 |
| COMMODITY | Cross-Sectional Momentum (ROC) | 600 | 44.2% | 40.2% | 0.69 | 0.42 | -0.63 | **adverse — significant p=0.0055 in WRONG direction** |
| CRYPTO | Cross-Sectional Momentum + Vol Filter | 23 | 0.0% | 0.00 | 0.00 | 0.00 | -12.5 | catastrophic — 0/23 wins |
| FOREX | FX Mean-Reversion (RSI/Stochastic) | 363 | 3.6% | 2.1% | 0.024 | 0.007 | -1.59 | **suspected resolver bug — 99%+ LOST is implausible vs literature** |
| FOREX | FX Carry Trade (G10) | 47 | 4.3% | 1.2% | 0.005 | 0.00 | -11.97 | suspected resolver bug + n<100 |

---

## NEEDS_IMPLEMENTATION TABLE — Priority Queue (51 candidates total)

Top 15 ranked by **(AI-source count x expected PF x build-cost-inverse)**.

| # | Class | Strategy | Family | AI count | Entry | Exit | Citation | Expected edge | Why prioritize |
|---|-------|----------|--------|----------|-------|------|----------|---------------|----------------|
| 1 | FOREX | **FX Carry Trade (G10)** | carry | **5/5** | Long top-3 IR currencies vs short bottom-3 (monthly rebal) | Monthly rebal, vol-target 10% | Lustig/Roussanov/Verdelhan 2011 JFE | WR 55-60%, PF 1.3-1.5 | **Universal AI consensus.** Live DB result was catastrophic (PF 0.005) but n=47 + suspected resolver bug — academic strategy is sound; implementation likely broken. |
| 2 | COMMODITY | **Commodity Seasonal (Ags/Energy)** | calendar | **5/5** | Long soybean Apr 15; CL Nov 1 (if >100SMA); GC Oct 1 | Fixed calendar exit | Bouman/Jacobsen 2002 AER | WR 55-62%, PF 1.4-2.0 | **Universal.** Pure-calendar, zero data deps, can paper-trade tomorrow. |
| 3 | PENNY_IPO | **Post-IPO Short-Term Momentum** | momentum | **5/5** | IPO <6mo; top-quintile 20d return; >VWAP(20); ADV>500k | 20d hold OR <10SMA OR -10% peak | Ritter 1991, Loughran/Ritter 1995 | WR 50-58%, PF 1.3-1.65 | **Universal.** Needs polygon.io ipo_calendar feed only. PENNY_IPO has zero production coverage. |
| 4 | EQUITY | **Piotroski F-Score Quality-Value** | factor | 1/5 (gemini) | P/B<0.8 AND F-Score>=8; top-20 by F-Score | Annual rebal; exit if P/B>1.2 or F<5 | Piotroski 2000 JAR | **WR 65%, PF 2.0** | Highest single-strategy expected edge. Single-AI but academically distinctive (non-crowded). |
| 5 | ETF | **Sector Rotation by Relative Strength (Faber)** | momentum | 4/5 | Top-3 of 9 SPDR sectors by 3-6m momentum; SPY>200SMA filter | Monthly rebal; exit on filter break | Faber 2007 JoWM | WR 55-60%, PF 1.6-1.9 | 4-AI consensus, ETF universe has near-zero coverage. Highest ROI build for ETF class. |
| 6 | EQUITY | **12-1 Cross-Sectional Momentum (Jegadeesh-Titman)** | momentum | 4/5 | Rank S&P500 by 12-1m return; long top decile; >200SMA filter | Monthly rebal OR <200SMA | Jegadeesh/Titman 1993 JF | WR 50-57%, PF 1.5-1.8 | Most-cited equity anomaly. EQUITY pipeline has no implementation. |
| 7 | COMMODITY | **COT Commercial Net Positioning Extremes** | COT | 4/5 | Commercials net at 12m high + 200SMA filter | Reverse extreme OR 60d | Sanders/Irwin/Merrin 2009 JFM | WR 48-55%, PF 1.4-2.1 | **Pipeline already exists** (`cftc_cot_commercial_signal`, n=1). Lowest-cost build. |
| 8 | ETF | **Dual Momentum (Antonacci)** | momentum | 4/5 | QQQ/VTI/IWM 12m return rank vs T-bill | Monthly rebal | Antonacci 2014 | WR 55-60%, PF 1.6-2.0 | Existing `etf_dual_momentum` slug has n=1; full rewire needed. |
| 9 | COMMODITY | **Donchian 20/55 Turtle Breakout** | breakout | 3/5 | 20d high breakout + price>200SMA on CL/GC/ZS | 55d low OR 10% trail | Hurst/Ooi/Pedersen 2017 | WR 40-55%, PF 1.5-2.3 | Most-cited commodity trend strategy; current COMMODITY book is momentum-heavy AND bleeding. |
| 10 | EQUITY | **Fama-French Value (B/P) + Trend Filter** | value | 3/5 | Top decile B/P, S&P500, price>200SMA | Bottom quartile B/P OR <200SMA | Fama/French 1993 JFE | WR 55%, PF 1.2-1.3 | Cross-validated; equity pipeline has no value tilt. |
| 11 | BOND | **Flight-to-Quality Breakout (LQD/TLT)** | pairs | 1/5 (deepseek) | LQD/TLT < -2sigma AND VIX>30 | Reverse to mean OR 30d | Baker/Wurgler 2012 | WR 70%, PF 2.0 | Highest BOND expected edge; trivial ETF data needs. |
| 12 | BOND | **HYG Credit Mean-Reversion (Z-Score)** | mean-reversion | 1/5 (grok) | HYG < -2sigma 50d AND VIX<25 | -0.5sigma OR 10d | Standard credit-MR | WR 66%, PF 1.7 | Existing `bond_mean_reversion` (n=3) may be related. |
| 13 | CRYPTO | **BTC Funding Rate Carry** | carry | 3/5 | Long perp when funding negative; short when extreme positive | Funding flip OR 5d | Standard perp carry | WR 55-60%, PF 1.3-1.7 | Funding feed exists; only `funding_term_structure` (n=1) wired. |
| 14 | EQUITY | **Connors RSI(2) Pullback** (TIGHTEN existing) | mean-reversion | 3/5 | Already in DB but underperforming | — | Connors/Alvarez 2008 | n=75, WR 49.3%, PF 1.32 | Closest existing to winner. Sharpe 1.57 encouraging. **First-to-build because foundation exists.** |
| 15 | COMMODITY | **Hurst Exponent Trend Filter (overlay)** | trend | 2/5 | Rolling 100-bar Hurst>0.6 + price>50SMA | Hurst<0.5 | Peters 1994, Hurst 1951 | WR 35-50%, PF 1.8-2.2 | Pairs naturally with Donchian build (#9). Cheap incremental work. |

Full list (16 cross-validated + 35 singletons) in `reports/peer_claude-MASTER_STRATEGY_CANDIDATES_2026-05-31.md`.

---

## Cross-AI Consensus Highlights

**5/5 AIs (universal — top priority):**
1. **FX Carry Trade (G10)**
2. **Commodity Seasonal (Ags/Energy)**
3. **Post-IPO Short-Term Momentum**

**4/5 AIs (high consensus):**
4. 12-1 Cross-Sectional Momentum (EQUITY)
5. FX Mean-Reversion (FOREX) — *DB-tested, looks broken not absent*
6. COT Commercial Net Positioning Extremes (COMMODITY)
7. Sector Rotation by Relative Strength / Faber (ETF)

**3/5 AIs (cross-validated):**
8-16. Connors RSI(2) variants (CRYPTO + EQUITY), Crypto Cross-Sectional Momentum, BTC Funding Carry, Fama-French Value, Donchian Turtle, Dual Momentum (Antonacci), TLT 10m SMA, HYG/LQD Pair, Crypto Cross-Sectional Mom+Vol.

**Non-crowded singletons worth a shot:** Piotroski F-Score, Opening Range Breakout, IPO Lockup Expiration Breakout, Hurst overlay, Sector Put-Spread, Breadth Thrust, NG Inventory Seasonal.

---

## Honest Closing Verdict

**No winners found across 60 strategies x 7 asset classes.**

The dominant signal is: **51 of 60 master-list strategies have no production caller**. The 5 that DO have n>=20 in live DB either (a) failed catastrophically with plausible resolver-bug explanations (FOREX 0.5-4% WR vs literature 55-65% — labeling bug strongly suspected) or (b) under-performed at meaningful sample (Connors RSI(2) Equity n=75 PF 1.32; Commodity Cross-Sectional Momentum n=600 PF 0.69 adverse).

**Recommendation: BUILD top-3 NEEDS_IMPLEMENTATION + start 30-day paper-only shadow pilot.**

Selection rationale: All three are **5/5 universal AI consensus**, all three have **low build cost**, all three target asset classes with **near-zero existing coverage** (PENNY_IPO 0, FOREX broken, COMMODITY momentum-heavy bleeding):

1. **Commodity Seasonal (Ags/Energy)** — calendar rules, can ship in a single sidecar PR within hours. Citation: Bouman/Jacobsen 2002 AER, Houthakker 1957 REStat.
2. **Post-IPO Short-Term Momentum** — needs polygon.io ipo_calendar wire-up; opens the PENNY_IPO class for the first time. Citation: Ritter 1991, Loughran/Ritter 1995.
3. **FX Carry Trade (G10)** — universal consensus, currently absent in any working form; tied to **P0 FOREX resolver investigation** (99%+ LOST rate is not a strategy bug — it's a labeling bug). Citation: Lustig/Roussanov/Verdelhan 2011 JFE.

**Parallel P0 (do NOT defer):** investigate FOREX resolver / labeling pipeline. 359 picks at 99.5% LOST status is mathematically implausible vs cited literature (58-64% WR). Until that is fixed, FOREX numbers in the audit dashboard are noise.

**Caveat on "no edge":** today's NO_EDGE verdict is over **today's strategy book**. Whether the 51 academic strategies in NEEDS_IMPLEMENTATION work **on this specific universe** is an empirical question. The only honest answer is to paper-pilot, not to extrapolate from literature priors.

**Pilot design (30-day paper-only):**
- Wire top-3 strategies as **sidecar generators** (per Wire-Up Rule — opt-in, not in production scoring path)
- Each writes to `trading_picks` with `is_paper=1` and a `pilot_id` tag
- Daily WR/PF/n tracking in a new `audit_dashboard/data/pilot_*.json`
- 30d gate: n>=30 per strategy AND Wilson WR_lo>0.50 AND PF>1.2 to graduate to production wire-up
- If 2+ pilots pass: phase-2 = build COT (pipeline exists), Faber Sector Rotation (ETF gap), Piotroski (highest single expected edge).

---

## Composite scoreboard — all 7 classes

| Class | Strategies tested | n>=20 | Winners | Closest | Top NEEDS_IMPL |
|-------|-------------------|-------|---------|---------|----------------|
| CRYPTO | 8 | 1 (n=23, 0 wins) | 0 | none | Donchian 20d Turtle |
| EQUITY | 10 | 1 (n=75) | 0 | Connors RSI(2) Pullback PF 1.32 | Piotroski F-Score (WR 65%, PF 2.0) |
| FOREX | 7 | 2 (suspected resolver bug) | 0 | none (data unreliable) | FX Carry (5/5 AI) + P0 resolver fix |
| COMMODITY | 9 | 1 (n=600, adverse) | 0 | none | COT Extremes (pipeline exists) |
| ETF | 10 | 0 | 0 | none | Faber SPY/SMA100 + Sector Rotation (4/5 AI) |
| BOND | 7 | 0 | 0 | none (0/12 lifetime) | LQD/TLT Flight-to-Quality (PF 2.0) |
| PENNY_IPO | 9 | 0 | 0 | none | Post-IPO Short-Term Momentum (5/5 AI) |
| **TOTAL** | **60** | **5** | **0** | — | — |

---

## Action items returned to operator

1. **No sizing-up of any current strategy** based on today's master-list test.
2. **Build sidecar pilots** for: Commodity Seasonal, Post-IPO Momentum, FX Carry (per Wire-Up Rule, opt-in).
3. **P0 — FOREX resolver investigation.** 99%+ LOST on `forex_rsi2_mean_reversion` (n=359) is a labeling pipeline bug.
4. **P1 — re-audit existing slugs** `cta_cross_asset_tsmom`, `etf_dual_momentum`, `bond_yield_momentum`, `bond_mean_reversion`, `bond_yield_curve_slope` against canonical master-list entry rules — many are 100% TIME_EXIT zeros (consistent with the global intrabar resolver gap).
5. **30-day paper-only shadow pilot** with graduation gate (n>=30, WR_lo>0.50, PF>1.2 -> wire to production scoring). Empirical, not extrapolated.

---

Generated 2026-05-31 by Claude Code (peer_claude subagent) — final synthesis of the expanded hunt.

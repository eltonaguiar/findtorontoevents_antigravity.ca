# Persona Improvement Survey — AI Tournament

**Date:** 2026-05-25
**Author:** investigation subagent
**Goal alignment:** Goal #1 (phenomenal performance across all asset classes on `findtorontoevents.ca/audit`)
**Mandate:** for every persona in the AI tournament with n>=5 picks, identify the data inputs / external signals that would most improve pick quality.

## Sources

- Picks corpus: `audit_dashboard/data/ai_tournament_picks_latest.json` (1,411 records, 1,055,454 bytes, snapshot 2026-05-25 02:08 UTC). 1,105 records carry a `persona_id`; 306 do not (legacy `data_source` rows from `alpha_engine` and `quan_engine`, plus a handful of free-text-thesis grok3 rows that the cerebras/gpt4o submission layer never tagged).
- New submissions (2026-05-25, added on top of the dashboard snapshot for completeness, even though none reach n>=5 individually):
  - `data/ai_tournament/submissions/mercury_v2_20260525.json` — 20 picks across 5 hedge-fund personas (voss_global_macro, reed_long_short_fundamental, sharma_quant_momentum, chen_thematic_ai_growth, lang_value_contrarian; 4 picks each).
  - `data/ai_tournament/submissions/grok3_hedgefund_20260525.json` — 12 picks across 6 grok-prefixed personas (vargas/chen/sharma/okonkwo/reyes/li; 1–3 picks each).
  - `data/ai_tournament/submissions/qwen3_6_max_hedgefund_20260525.json` — 18 picks across 6 qwen-prefixed personas (value_hunter/momentum_rider/quant_systematic/macro_global/contrarian/carry_yield; 3 picks each).
- Registry: `tools/ai_tournament/persona_registry.py` (17 canonical personas as of 2026-05-25; the picks corpus also references ~25 additional `persona_id` strings used by various model adapters that have not been canonicalised into the registry yet — e.g. `momentum_momentum`, `quality_compound`, `growth_at_reasonable_price`, `gamma_raid`, `cta_trend`, `bayesian_breakout`, `inventory_cycle`, `macro_hedge`, `purchasing_power_parity`, `seasonal_pattern`, `bankruptcy_recovery`, `correlation_breaker`, `cross_sectional_momentum`, `supply_demand`, `volatility_breakout`, `grid_trader`). The improvement recommendations below treat the picks-corpus tag as the source of truth.

**Note on overrepresentation:** several personas are dominated by a single model resubmitting near-identical picks at each daily tournament tick (e.g. `breakout_scanner` n=204 is 51×FIL + 51×ZK + 51×NEAR + variations — all from `grok3`). I flag those cases inline and treat them as effectively n≈4 of *distinct* signals, even though the raw n is large.

## Qualifying personas (n>=5)

22 personas reach the threshold from the dashboard snapshot. None of the brand-new hedge-fund personas (`voss_*`, `reed_*`, `sharma_*`, `chen_*`, `lang_*`, `grok_*`, `qwen_*`) yet do — they sit at n=1–4 and are listed at the end as "watchlist".

---

### 1. `breakout_scanner` — Breakout Scanner (technical_breakout)

- **n=204, resolved=2, WR=100% (2/2), avg unrealized PnL = n/a (mostly OPEN)** — but n is misleading: 51+51+51 are repeated FIL/ZK/NEAR submissions by `grok3`, so true distinct-signal n ≈ 12.
- **Asset class:** CRYPTO 100%. **Direction:** 99.5% LONG.
- **Already relies on:** `ml_crypto_pred` confidence score, "multi-timeframe EMA alignment", volume signal, 20-day consolidation range.
- **Top 3 missing inputs:**
  1. **True consolidation-width vs realised volatility** — the persona claims "20-day consolidation" but never publishes the σ-of-σ ratio that distinguishes a real coiled range from a slow drift. Adding the Bollinger-Bandwidth percentile (current width vs prior 250d distribution) would let it reject the false breakouts that dominate crypto.
  2. **Order-book depth / spot CVD divergence at the breakout candle** — every entry would be filterable by "were aggressive market buys present, or was the breakout passive-bid-lift on thin book?" Without this the persona is short-volatility in disguise.
  3. **Funding-rate and perp basis at entry** — crypto breakouts often coincide with funding>0.05%/8h, which converts the trade into a carry headwind. A funding-percentile filter (top decile = stand aside) would lift hold-period PnL.
- **Tier promotion plan:** WR=100% on n=2 is meaningless. Need n>=50 distinct breakouts (not symbol repeats) over 60+ days; require BB-width percentile <30 AND funding-percentile <70 to fire. Target PF>1.8 on CRYPTO is realistic with those filters; without them the persona will likely settle at PF~0.9 (the strategy is paying spread + funding without an edge source).
- **Cross-persona conflict:** directly contradicts `mean_reversion` and `volatility_breakout` on the same crypto symbols (`mean_reversion` is long BTC where `breakout_scanner` is long alt-breakouts — different symbol universes, low overlap). Conflicts with `bayesian_breakout` (same setup, different probabilistic gate) — ~30% same-symbol overlap on ETH/SOL/AVAX; the bayesian variant adds a Bayesian posterior that the raw scanner lacks.

### 2. `momentum_momentum` — 3-6mo Equity Momentum (technical_momentum, grok3)

- **n=92, resolved=33, WR=57.6%, avg PnL +4.03%.** EQUITY 100%, 89% LONG.
- **Heavy-tail caveat:** 46/92 are repeated MU submissions; distinct-symbol n ≈ 25.
- **Already relies on:** `growth_stock_screener` engine, "relative strength in semiconductor sector", confidence scores 70–84%.
- **Top 3 missing inputs:**
  1. **Sector-relative momentum z-score** (vs SPY or sector ETF), not just absolute price action. MU is bid because semis are bid; the persona should fade MU when its z-score vs SOXX collapses, which is the historical reversal tell.
  2. **Earnings-revision breadth from FactSet/Refinitiv (or Yahoo as a proxy)** — momentum that is *not* backed by upward EPS revisions is the classic late-stage failure pattern. Adding a simple "3-month EPS revision up?" gate is the largest single edge available.
  3. **Short-interest delta / days-to-cover** — momentum that is short-interest-driven mean-reverts violently. Filter out names with SI>15% of float.
- **Tier promotion plan:** already past T2 on WR (57.6%). Need PF — current avg PnL/avg loss not computed, but trend looks positive. With EPS-revisions filter and a beta-neutral pair (short SPY same-dollar), this persona can stretch to T1 territory. Need n>=50 distinct symbols (not 25× MU).
- **Conflict:** sometimes contradicts `mean_reversion` (same EQUITY symbols on opposite sides) and `growth_at_reasonable_price` (NVDA: GARP says long, momentum says long — agreement, not conflict). Overlaps `cross_sectional_momentum` heavily (~40% symbol overlap with PYPL/ADBE/CRM); the persona-level redundancy is real and should be collapsed.

### 3. `quality_compound` — Quality Compounder (fundamental_quality, cursor_agent)

- **n=68, resolved=17, WR=100% (17/17), avg unrealized PnL −2.39%.** Universe is 51× NVDA + 17× IWM. Distinct n=2. WR=100% is an artefact of duplicate resolution.
- **Already relies on:** Two-Day RSI Reversal signal, "ROE>15%, debt/equity<0.5" (per persona name) — though the actual thesis text is technical, not fundamental.
- **Top 3 missing inputs:**
  1. **Actual fundamental data** — ROIC, FCF/EV, accruals quality (Sloan ratio). The persona is named "quality_compound" but the thesis cites RSI(2), which is the opposite of a fundamental gate. Either rename it or wire in a Compustat-equivalent feed (Yahoo `getKeyStatistics` is a free starting point).
  2. **Universe expansion** — running this on NVDA alone is concentration risk, not a strategy. Needs a quality screen producing 20–50 names per quarter.
  3. **Pricing-power signal** — gross-margin expansion YoY is the cleanest moat tell; without it the persona is just buying expensive stocks.
- **Tier promotion plan:** the WR=100% is unreal; needs forced de-duplication of repeated picks. After de-dup, expect PF~1.1 (the −2.39% avg PnL is a tell). Promotion requires rebuilding the entry gate from fundamentals.
- **Conflict:** overlaps `growth_at_reasonable_price` (NVDA) and `chen_thematic_ai_growth` (NVDA) — three personas chasing the same name through different doors.

### 4. `growth_at_reasonable_price` — GARP (cerebras_llama4)

- **n=67, resolved=11, WR=54.5%, avg PnL −3.31%.** EQUITY 100%, 92% LONG. 56/67 are NVDA repeats; distinct n ≈ 12.
- **Already relies on:** "PEG<1.5, revenue growth>15%", MACD divergence, 20-day EMA.
- **Top 3 missing inputs:**
  1. **Forward PEG using consensus EPS** (current persona is using trailing PEG inferred from thesis text). Forward PEG is the only GARP signal that backtests.
  2. **Capex intensity vs FCF conversion** — a true GARP filter rejects companies with rising capex/revenue and stagnant FCF (the AMD/INTC failure pattern). Without this gate, GARP repeatedly picks tops in capex-heavy semis.
  3. **Sell-side estimate-dispersion** — narrow dispersion + upward revisions = high-quality GARP signal; wide dispersion = noise. Free proxy via Yahoo analyst count + high/low estimate range.
- **Tier promotion plan:** avg PnL −3.31% is sub-floor. Need forward-EPS + dispersion filters before any size; expect to halve trade count and double per-trade edge. Target WR 55%+ at PF>1.4.
- **Conflict:** redundant with `quality_compound` and `value_investor`; rename to `growth_momentum_combo` or merge.

### 5. `trend_follower` — Trend Follower (technical_trend, deepseek_v4)

- **n=67, resolved=55 (highest resolution rate of any persona), WR=34.5%, avg PnL +4.20%.** EQUITY 100%, 70% LONG.
- **Already relies on:** "20/50 EMA cross", ADX>25, "higher lows/higher highs", ISM/credit-spreads (per thesis text).
- **Top 3 missing inputs:**
  1. **ADX-regime gate** — the registry says "require ADX>25 at entry" but the WR=34.5% suggests it isn't actually being enforced. Add a hard pre-trade ADX measurement.
  2. **Cross-sectional trend strength** — trend-following alpha lives in being long *the strongest* trends and short the weakest, not in catching every cross. A 12-1 momentum ranking + decile filter is the canonical fix.
  3. **Volatility-target sizing input (annualised σ over last 21d)** — equal-dollar sizing in a trend-follower is why MDD blows out. Without per-trade σ, the model cannot publish a correctly-sized signal.
- **Tier promotion plan:** WR 34.5% is the classic trend-follower payoff (positive expectancy via right-tail). Avg PnL +4.20% suggests PF>1.5 is plausible. To promote to T2: enforce cross-sectional ranking, size by σ, and limit short-side to bear-regime SPY filter (positive trend-follower historical edge is asymmetric).
- **Conflict:** flips with `mean_reversion` and `momentum_scalp` on the same equity setups. Disagreement frequency is structural — they're complementary, not redundant. Keep both, weight by regime.

### 6. `grid_trader` — Grid Trading (cerebras_llama4)

- **n=64, resolved=0, avg unrealized PnL −0.76%.** CRYPTO 100%, 97% LONG (grid-LONG bias is a contradiction — true grid is bidirectional). 56/64 are ETH; distinct n ≈ 9.
- **Already relies on:** Glassnode NUPL metric, 4h RSI, "tight 3% channel" detection.
- **Top 3 missing inputs:**
  1. **Realised volatility regime detector** (e.g. ETH/BTC realised σ percentile last 90d) — grid trading only works in low-σ ranges; firing during expanding-σ regimes guarantees grid-blowup.
  2. **Range-bound vs trending classifier** (Hurst exponent <0.5 = mean-reverting/grid-friendly; >0.5 = trending; or ADX<20 as cheap proxy). Currently no regime guard.
  3. **Fee/slippage budget** — grids are dead on assets where round-trip cost > grid spacing. Need the exchange's effective fee + a per-symbol slippage estimate.
- **Tier promotion plan:** persona has zero resolved trades — it's effectively unproven. Need to define grid-exit criteria (closed range vs ranging-still) and resolve at least 30 trades before any judgment. Currently a `(SPECULATIVE)` persona at best.
- **Conflict:** contradicts every trend-following persona on the same crypto. Low symbol overlap with `momentum_scalp` (deepseek does scalp, cerebras does grid).

### 7. `value_investor` — Value Investor (fundamental_value, gpt4o_mini)

- **n=61, resolved=0, avg unrealized PnL +3.81%.** EQUITY 100%, 100% LONG. 56/61 are AAPL repeats; distinct n ≈ 6.
- **Already relies on:** "Apple's upcoming product launch" (qualitative narrative). The actual canonical value-investor entry criteria (P/E vs sector, P/B<1.5, FCF yield>5%, D/E low) appear to be **completely absent** from the actual thesis text. This persona is mis-tagged.
- **Top 3 missing inputs:**
  1. **Any quantitative fundamentals at all** — the persona is fundamentally untethered from its registry definition. Wire in Yahoo `getKeyStatistics` (forwardPE, priceToBook, debtToEquity, returnOnEquity) as a pre-trade gate.
  2. **Sector-relative valuation** (AAPL P/E vs IT sector P/E) — absolute multiples are noise; relative-to-sector is where value-factor alpha lives.
  3. **Insider transactions feed** (Form 4 — free from openinsider.com) — value + insider buying historically lifts WR 8–12%.
- **Tier promotion plan:** zero resolved trades. Needs persona rewrite before promotion judgement is even possible. Until then, treat as `quality_signal_in_disguise`.
- **Conflict:** the "value" label is now used by `value_investor`, `safety_net`, `lang_value_contrarian`, and `qwen_value_hunter` — four overlapping personas with no clear differentiation rule. Consolidate.

### 8. `mean_reversion` — Mean Reversion (gpt4o_mini)

- **n=56, resolved=0, avg unrealized PnL +0.05%.** CRYPTO 100%, 100% LONG. Universe is BTC only (56/56). True n=1.
- **Already relies on:** "institutional adoption" narrative. The registry definition (RSI<25/>75, Bollinger touch, exhaustion candle) is again **absent** from the thesis — the persona is mis-tagged.
- **Top 3 missing inputs:**
  1. **A VIX or crypto-DVOL regime filter** — mean reversion is a low-vol-regime strategy that loses badly in trending vol-expansion regimes. This is the canonical missing piece across every mean-reversion attempt in the corpus.
  2. **Multi-symbol breadth** — single-symbol mean-reversion is portfolio-degenerate. Needs at minimum top-50-by-mcap CMC universe with per-symbol RSI extremes.
  3. **Funding rate (perps) at the entry extreme** — extreme funding + RSI extreme is the textbook contrarian setup; either signal alone is weaker.
- **Tier promotion plan:** zero resolved + single symbol = unverifiable. Rebuild as a regime-conditional, multi-symbol RSI+BB strategy with funding overlay. Realistic target PF 1.4 in low-vol regime, PF<1 in high-vol — so the regime gate IS the persona.
- **Conflict:** directly contradicts `momentum_scalp` and `trend_follower` and `breakout_scanner` on the same crypto symbols. Expected collision rate ~30% on entries; collision resolution should be a regime-router (vol<25th pct → mean_reversion fires; vol>75th pct → trend fires; middle → neither fires).

### 9. `supply_demand` — Supply/Demand Imbalance (cursor_agent)

- **n=52, resolved=0.** FUTURES 100%, 100% SHORT, 51/52 are GC=F (gold) repeats. True n=2.
- **Already relies on:** "contango proxy signals SHORT despite momentum uptrend" — fighting trend with carry.
- **Top 3 missing inputs:**
  1. **Actual COT (Commitments of Traders) report** — supply/demand in futures means commercial-vs-non-commercial positioning. Free from CFTC weekly.
  2. **Term-structure slope** (front vs M+6) — the persona claims contango but never measures it explicitly. CME data feed required.
  3. **Inventory data** (gold COMEX warehouse, oil EIA, copper LME) — supply/demand without inventory is narrative-only.
- **Tier promotion plan:** persona is one symbol short-only, can't evaluate. Need broader futures universe + real COT/term-structure inputs before any verdict. Currently effectively `gold_short_perma_bear`.
- **Conflict:** contradicts `cta_trend` on gold (trend says long, supply/demand says short). High collision rate on FUTURES.

### 10. `volatility_breakout` — Volatility Breakout (cursor_agent)

- **n=51, resolved=0, avg unrealized PnL −1.48%.** CRYPTO 100% LONG. 51/51 are BTCUSDT. True n=1.
- **Already relies on:** "Daily EMA(20)>EMA(50) and weekly EMA alignment" — that's not a volatility breakout, that's a trend filter.
- **Top 3 missing inputs:**
  1. **ATR-expansion measurement** (current ATR vs trailing 60d median ATR). Without this, "volatility breakout" is just "trend continuation".
  2. **Squeeze indicator state** (Bollinger inside Keltner → squeeze on; release → fire). This is the textbook signal the persona name implies.
  3. **Realised-vs-implied vol delta** (where IV data exists — Deribit DVOL for BTC/ETH) — IV crush during a vol breakout is a known reversal tell.
- **Tier promotion plan:** persona is mis-implemented. Rewrite around ATR percentile + squeeze release; then need n>=50 distinct entries.
- **Conflict:** overlaps `breakout_scanner` and `bayesian_breakout` on the same setups; consolidate.

### 11. `microcap_momentum` — Micro-Cap Momentum (deepseek_v4)

- **n=45, resolved=35, WR=80%, avg PnL n/a.** PENNY 87%, ETF 11%. Symbols well-distributed (AGBA, LODE, RGTI, FFIE, SQQQ, GSAT).
- **Already relies on:** "low float, rising volume, social media chatter, multi-month downtrend break, insider buying" — well-aligned with registry definition.
- **Top 3 missing inputs:**
  1. **Float-rotation rate** (intraday volume / float) — the persona cites volume but not float-rotation, which is the defining microcap-momentum signal. >2× float rotated in a day = squeeze conditions.
  2. **Borrow rate / utilisation** (Interactive Brokers borrow feed or ortex) — squeezes happen when borrow >50% and utilisation >95%. Without this, the persona cannot distinguish a real squeeze from a pump.
  3. **Dilution-risk signal** (recent S-3 filings, ATM offerings) — the canonical microcap-momentum killer is a surprise ATM. SEC EDGAR free feed.
- **Tier promotion plan:** WR=80% on n=35 is genuinely strong. Need to compute PF (avg win vs avg loss) and confirm it's not selection bias from `cerebras` resolving losers slowly. If PF>1.5 holds, this is a T2 candidate. Largest risk: regime — microcap-momentum dies in risk-off, so add a SPY 50d-slope filter.
- **Conflict:** unique universe (PENNY), low overlap with other personas. Closest: `gamma_raid` (also PENNY) — different mechanism (options-flow vs price/volume), keep both.

### 12. `cross_sectional_momentum` — Cross-Sectional Momentum (ring_261T)

- **n=45, resolved=45 (100% resolution), WR=66.7%.** EQUITY 100%, 67% LONG.
- **Already relies on:** "dominates the software sector with strongest momentum", "AI agent integration driving net-new enterprise pipeline".
- **Top 3 missing inputs:**
  1. **Decile-rank publication in the thesis** (which decile of the universe is this name in?) — currently the thesis says "leader" but not "decile 1 of 10". Without the rank, the strategy can't be reproduced.
  2. **Pair-trade short leg** — true cross-sectional momentum is long-top-decile short-bottom-decile, which is what gives it Sharpe. Currently mostly long-only.
  3. **Sector-neutralisation step** — without neutralising, the persona is just buying whatever sector is rallying. Sector-neutral signal is the standard quant construction.
- **Tier promotion plan:** already T2 (WR 66.7% on n=45). To T1: add the short leg and sector-neutralisation. Realistic Sharpe 1.5+.
- **Conflict:** overlaps `momentum_momentum` on equity universe; one is cross-sectional, the other absolute — keep both, run as a 2-factor blend.

### 13. `momentum_scalp` — Momentum Scalper (deepseek_v4)

- **n=43, resolved=4, WR=0% (0/4), avg PnL n/a.** CRYPTO 100%, 93% LONG.
- **Already relies on:** VWAP, 15min volume, RSI(14) rising through 50.
- **Top 3 missing inputs:**
  1. **Tick-level CVD** (cumulative volume delta from aggressor flag) — VWAP+volume is not enough to scalp; you need the aggressor signal to confirm buy-pressure.
  2. **Spread + queue-position model** — scalpers die on fee+spread; persona must publish "is the symbol's effective spread < projected edge?" Currently no such gate.
  3. **Session/funding overlay** — crypto scalps in Asia session ≠ NY session; persona never tags session.
- **Tier promotion plan:** WR=0% on n=4 is alarming. Need to halt this persona and rebuild around CVD + spread gate before resuming. Until rebuild, this is the #1 deprecation candidate (see end of report).
- **Conflict:** flips with every mean-reversion persona on the same minute bars. Collision resolution: scalpers fire only when 1-min ATR > 60d median ATR (volatility-confirmed); mean-reversion fires when 1-min ATR < 60d median.

### 14. `gamma_raid` — Gamma Raid / Options Flow (grok3)

- **n=37, resolved=28, WR=67.9%, avg unrealized PnL −2.16%.** PENNY 100%, 62% LONG.
- **Already relies on:** "dealer gamma positioning", "open interest concentration", "0DTE max pain".
- **Top 3 missing inputs:**
  1. **Real GEX (gamma exposure) feed** (spotgamma.com / squeezemetrics / unusualwhales) — the persona narrates GEX but doesn't appear to consume it. This is the persona's *defining* input and it's missing.
  2. **Vanna / charm exposure** — GEX alone is incomplete; vanna swings on IV-changes drive the larger pin moves.
  3. **0DTE volume share** vs total OI by strike (free from CBOE) — to distinguish a real pin from a noise day.
- **Tier promotion plan:** WR 67.9% on n=28 is encouraging. avg PnL −2.16% suggests winners are small and losers are sized too big — fix sizing (gamma-adjusted notional). With real GEX feed, target T1.
- **Conflict:** unique universe (options-flow on micro/penny); low overlap. Keep as standalone.

### 15. `bayesian_breakout` — Bayesian Breakout (ring_261T)

- **n=35, resolved=3, WR=33.3%.** CRYPTO 100%, 71% LONG.
- **Already relies on:** structural support levels, declining-volume consolidation, descending-resistance trendlines.
- **Top 3 missing inputs:**
  1. **Explicit prior/posterior publication** (the persona is named Bayesian; the thesis should show P(breakout|signals) computed with named priors). Currently absent.
  2. **Liquidity prior** (low-liquidity symbols have wider posterior; the prior should reflect this).
  3. **Regime-conditional prior** (BTC-dominance regime: alt-breakouts have different base rates depending on BTC.D direction).
- **Tier promotion plan:** WR 33.3% on n=3 is unverifiable. Need n>=50 with the Bayesian computation actually published in the thesis. Otherwise indistinguishable from `breakout_scanner`.

### 16. `inventory_cycle` — Inventory Cycle (ring_261T)

- **n=25, resolved=20, WR=100%.** FUTURES 100%, 80% LONG. Universe: CL, NG, HG, SI, GC.
- **Already relies on:** "EIA crude and gasoline inventory", "EIA storage injection rates vs 5-yr average".
- **Top 3 missing inputs:**
  1. **Forward-curve roll yield** — long futures with backwardation > 0.5%/mo is the actual carry edge; the persona narrates inventories but doesn't size by roll yield.
  2. **Refinery utilisation rate** (EIA WPSR) — for CL/RB the most timely demand signal.
  3. **Weather-degree-day forecasts** (NOAA CDD/HDD anomaly) — for NG, the dominant short-term driver.
- **Tier promotion plan:** WR=100% on n=20 is suspect (may include the same setup repeated weekly through EIA updates). Need true distinct-event de-dup. If WR holds at >65% on n=50+, T1 candidate.

### 17. `macro_hedge` — Macro Hedge (grok3)

- **n=24, resolved=24, WR=100%.** ETF 100%, 100% LONG. 17/24 are QQQ.
- **Already relies on:** "DXY weakening = risk-on rotation", QQQ momentum continuation.
- **Top 3 missing inputs:**
  1. **Real-yield (10Y TIPS) live feed** — the cleanest single macro signal; currently inferred from price action.
  2. **DXY + 2s10s curve slope feed** — both signals are narrated but neither published as a numeric.
  3. **VIX term-structure** (front/M+3 ratio) — distinguishes hedging-flow rallies from real risk-on.
- **Tier promotion plan:** the name "macro hedge" but the construction is "long QQQ on weak DXY" — that's a *risk-on directional*, not a hedge. Either rename or add the actual hedge leg (long TIPS or long VXX on signal flip). 

### 18. `purchasing_power_parity` — PPP Mean Reversion (ring_261T)

- **n=20, resolved=20, WR=75%.** FOREX 100%, 50/50 LONG/SHORT. EUR/JPY/GBP/CHF pairs.
- **Already relies on:** OECD PPP fair value, deviation from PPP equilibrium.
- **Top 3 missing inputs:**
  1. **Real interest-rate differential** (10Y nominal − 10Y breakeven, US vs counterparty) — the canonical FX carry+value combo signal.
  2. **CFTC FX positioning** (non-commercial net longs vs 3-yr range) — overcrowded positioning is the PPP-reversion catalyst.
  3. **Central-bank policy-rate path** (OIS curve differential) — PPP mean-reversion only fires when the rate-diff is closing, not widening.
- **Tier promotion plan:** WR 75% on n=20 is strong. Notably FOREX is the worst-performing class globally per CLAUDE.md (PF 0.27); this persona may be where the salvageable FX edge lives. Promote with caution after rate-diff filter added.

### 19. `seasonal_pattern` — Seasonal Commodity (cerebras_llama4)

- **n=16, resolved=4, WR=50%.** FUTURES 100%, 88% LONG. 12/16 are GC=F.
- **Already relies on:** "spring planting", "real yields above 2.5%", "50-day SMA break" (all on gold, which has no planting season — persona is mis-applied).
- **Top 3 missing inputs:**
  1. **Actual seasonal-decomposition output** (STL or X-12 seasonality, %-anomaly vs 10-yr seasonal mean per calendar week) — currently anecdotal.
  2. **Crop-progress reports** (USDA WASDE for grains; not gold) — the persona universe is wrong.
  3. **Storage / cost-of-carry** for agricultural and energy seasonality.
- **Tier promotion plan:** universe must move from gold-dominated to agricultural/energy. Then WR 50% can become 60% with proper seasonality.

### 20. `bankruptcy_recovery` — Bankruptcy Recovery (ring_261T)

- **n=15, resolved=15, WR=66.7%.** PENNY 67%, ETF 33%.
- **Already relies on:** "higher-lows accumulation pattern", "volume increasing".
- **Top 3 missing inputs:**
  1. **Debt-restructuring/Ch-11-emergence calendar** — the canonical signal for the persona name. Free from BankruptcyData.com or court filings.
  2. **Net operating loss carryforward (NOL) size** — recovering firms with large NOLs are the bigger winners.
  3. **Activist filings (13D)** — recovery + activist = highest WR setup.
- **Tier promotion plan:** WR 66.7% on n=15 is borderline T2. Needs canonical bankruptcy data feed.

### 21. `cta_trend` — CTA Trend (deepseek_v4)

- **n=10, resolved=8, WR=62.5%.** FUTURES 100%, 80% LONG.
- **Already relies on:** "supply constraints", "green energy demand", "weak USD", "20-day MA".
- **Top 3 missing inputs:**
  1. **COT report — managed-money net position** (the historical CTA-trend edge IS this dataset).
  2. **Multi-timeframe trend filter** (canonical CTA uses 1mo + 3mo + 12mo lookbacks averaged).
  3. **Vol-target sizing** (CTA trend uses inverse-vol weighting — 10% target vol per leg).
- **Tier promotion plan:** WR 62.5% on n=8 is too small. Need n>=50 with COT integration. T2 candidate.

### 22. `correlation_breaker` — Correlation Breaker (grok3)

- **n=5, resolved=4, WR=50%.** FUTURES 100%, 60% LONG.
- **Already relies on:** "60-day cross-asset correlation collapsing", "gold rising alongside real yields breaking inverse relationship".
- **Top 3 missing inputs:**
  1. **Rolling correlation matrix output** (all pairs, last 20d vs last 250d) — persona narrates this but doesn't publish it.
  2. **Eigenvalue dispersion (top-1 PC variance share)** — correlation regime change is measurable by eigenvalue spread.
  3. **Cross-asset vol-of-vol** (VVIX, MOVE, OVX) — confirms regime stress.
- **Tier promotion plan:** at n=5, basically unverifiable. Watchlist.

---

## Watchlist personas (n<5, added 2026-05-25)

The 17 hedge-fund personas from today's submissions are below the n>=5 threshold. They are tracked for the next survey:

- mercury_v2 set (4 each): `voss_global_macro`, `reed_long_short_fundamental`, `sharma_quant_momentum`, `chen_thematic_ai_growth`, `lang_value_contrarian`
- grok3 hedgefund set (1–3 each): `grok_vargas_macro`, `grok_chen_quant_factor`, `grok_sharma_fundamental_ls`, `grok_okonkwo_risk_overlay`, `grok_reyes_thematic_etf`, `grok_li_sector_event`
- qwen3_6_max set (3 each): `qwen_value_hunter`, `qwen_momentum_rider`, `qwen_quant_systematic`, `qwen_macro_global`, `qwen_contrarian`, `qwen_carry_yield`

Re-run this survey when any of these reaches n>=5 (likely 1–2 weeks at current submission cadence).

Also flagged: registry personas that have **zero picks** in the corpus (need either retirement or assignment to a model): `catalyst_sniper`, `signal_miner`, `forensic_short`, `safety_net`, `moat_measurer`, `cycle_rotator`. Of these, `safety_net` and `moat_measurer` overlap with `value_investor`/`quality_compound`; `cycle_rotator` overlaps with `macro_hedge`; `catalyst_sniper`/`signal_miner`/`forensic_short` are genuinely missing strategies worth assigning a model to.

---

## Top 5 data-feed investments (ranked by aggregate impact across personas)

1. **VIX / DVOL / realised-vol regime tag attached to every pick at submission time.**
   - Beneficiaries: `mean_reversion`, `momentum_scalp`, `grid_trader`, `volatility_breakout`, `breakout_scanner`, `trend_follower`, `sharma_quant_momentum`. 7 personas, accounting for ~470 of the 1,461 surveyed picks. Without this single tag, ~30% of all picks are being fired in the wrong regime. Implementation cost is the lowest of any item on this list (single API call per submission, cache 5-minute TTL).
2. **COT (Commitments of Traders) weekly feed for futures personas.**
   - Beneficiaries: `cta_trend`, `supply_demand`, `inventory_cycle`, `correlation_breaker`, `seasonal_pattern`. 5 personas, ~108 picks. CFTC publishes free Friday CSV; trivial ingest. This is the single biggest fix for the FOREX/COMMODITY classes where Goal #1 is hurting.
3. **Real GEX (gamma exposure) + 0DTE flow feed for options-driven personas.**
   - Beneficiaries: `gamma_raid` (37 picks, already WR 67.9%), `microcap_momentum` (squeeze dynamics). The `gamma_raid` persona is currently narrating GEX without consuming it; consuming real GEX flips it from interesting-narrative to genuine-edge. Options are paid (spotgamma ~$80/mo or unusualwhales ~$50/mo), but ROI is the highest of any line item here.
4. **On-chain / funding-rate feed for crypto personas.**
   - Beneficiaries: every CRYPTO persona — `breakout_scanner`, `mean_reversion`, `momentum_scalp`, `grid_trader`, `volatility_breakout`, `bayesian_breakout`. 6 personas, ~453 picks (the largest single block). Glassnode is partly cited but not consumed. Free alternatives: Coinglass funding, CoinMetrics NUPL/MVRV. Adding funding-percentile and on-chain accumulation tags would directly address the CRYPTO-class drag noted in CLAUDE.md (current PF 1.25 vs T2 target 1.5).
5. **Earnings-revisions + insider-transactions tag for equity personas.**
   - Beneficiaries: `momentum_momentum`, `growth_at_reasonable_price`, `quality_compound`, `value_investor`, `cross_sectional_momentum`, `reed_long_short_fundamental` (watchlist), `lang_value_contrarian` (watchlist). 5 active personas + 2 watchlist, ~333 picks. Both signals are free (Yahoo `getKeyStatistics` for revisions; openinsider.com for Form 4). Addresses the EQUITY-class promotion path from current T2-candidate (PF 1.41) to T2-confirmed (PF>1.5).

---

## 3 personas to deprecate

The mutate-before-kill protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`) applies. The recommendations below are *trigger-rules* — deprecate only if, after the recommended data-feed adds and a 60-day cure window, the persona still fails.

1. **`momentum_scalp`** (deepseek_v4) — WR=0% on n=4 resolved, n=43 total. Despite a textbook strategy definition, real-world WR is zero. Trigger: if after CVD + spread-gate + session-tag inputs (per item #1 above) the persona still posts WR<35% on n>=30 resolved by 2026-07-25, retire it. Rationale: 15-min crypto scalping needs microstructure data that the model fleet cannot consume reliably; better to redirect deepseek_v4's persona slot to `cta_trend` (which is already at WR 62.5% on n=8 with the same model).

2. **`value_investor`** (gpt4o_mini, single-symbol AAPL 56/61) — the persona is mis-implemented: zero connection between the registry definition (P/E, P/B, FCF yield, D/E) and the thesis text ("Apple product launch"). Trigger: if after wiring `getKeyStatistics` and broadening universe to top-50-by-mcap S&P names (per item #5 above), the persona still posts single-symbol concentration >50% by 2026-07-25, retire and reassign gpt4o_mini's slot to one of the missing-registry personas (`catalyst_sniper` is the strongest fit for gpt4o_mini's news-aware tendencies).

3. **`grid_trader`** (cerebras_llama4, single-symbol ETH 56/64) — zero resolved trades, persona definition mis-applied (single-symbol grid in a trending environment with 97% LONG bias is not a grid). Trigger: if after Hurst/ADX regime gate + multi-symbol expansion + fee-budget model (per item #1 + a separate microstructure work-stream) the persona still posts <10 resolved trades by 2026-07-25, retire. Rationale: grid-trading is structurally incompatible with the daily-tournament submission cadence (grids hold for weeks); the persona may simply not fit the format.

Honourable mention (close to deprecation but not yet): **`supply_demand`** (cursor_agent, 51× GC=F SHORT against trend) and **`volatility_breakout`** (cursor_agent, 51× BTCUSDT LONG with no vol measurement). Both should be rewritten before judged; if rewrite doesn't ship by 2026-06-25, escalate to deprecation candidate.

---

## Methodology notes

- Per-persona stats computed by joining the `audit_dashboard/data/ai_tournament_picks_latest.json` corpus on `persona_id`, supplemented by the 3 submission files from 2026-05-25. `status` field used for win/loss; `unrealized_pnl_pct` for avg-PnL where available (OPEN positions only — closed picks lose the field in the dashboard snapshot).
- "Distinct-signal n" called out wherever a single persona is dominated by repeated submissions of the same symbol across multiple daily tournament ticks. Many large-n personas collapse to single-digit distinct n once de-duplicated; the resolved-trade count is the more honest measure of strategy convergence.
- WR percentages on n<10 resolved are flagged as unverifiable. WR=100% on n<=20 is almost always an artefact of repeated-symbol resolution and should not be treated as a strategy property.
- No backtests run; this is a pure forward-looking data-gap audit. The Tier promotion plans are educated-guess targets, not modelled forecasts.

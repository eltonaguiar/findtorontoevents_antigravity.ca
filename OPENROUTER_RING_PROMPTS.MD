# OPENROUTER RING PROMPTS
**Repository:** findtorontoevents.ca/audit — Algorithmic Trading System  
**Compiled:** 2026-05-19  
**Purpose:** Catalogued, enhanced, and per-asset-class prompt variants for OpenRouter ring runs.  
**Sections:** 5 (Base prompt, Enhanced variants, Per-class diagnosis, Status table, Action plan)

---

## HOW TO USE THIS FILE

These prompts are designed for **OpenRouter ring runs** — fan-out to multiple models simultaneously
at $0.01/$0.02/$0.06 quality tiers. Copy-paste any prompt block below into your ring runner.

For sign-stability harness prompts, the standard grading criteria are:
- **eff >= 0.30** (effect size on DAILY return series)
- **Same sign in >= 3/5 of 14-day rolling windows**
- **Net of 30bps round-trip transaction cost**

Models that propose signals failing any of these criteria score 0 for that proposal.

---

## SECTION 1: THE BASE RING PROMPT (V1 — as used in 2026-05-18 sessions)

The following is the exact prompt used during the walk-forward sign-stability ring runs that killed
11/11 pre-registered causal hypotheses. It is preserved here verbatim as the baseline for all
variants below.

```
Algo system, 11/11 pre-registered causal hypotheses killed by a walk-forward sign-stability
harness (eff>=0.30, same sign in >=3/5 14-day windows, net of 30bps). Killed hypotheses included:

1. COT Commercials net positioning (COMMODITY) — sign flips across regimes
2. BTC funding-rate directional (CRYPTO) — inverts in bear markets
3. Roll-yield carry (FUTURES) — inverts when curves flatten/invert
4. Post-Earnings Announcement Drift — sign-flips with earnings quality
5. On-chain exchange net-flow directional — inverts with stablecoin substitution
6. FOREX carry rate-differential — inverted by BoJ tightening 2024-25
7. VIX slope directional (ETF) — sign-dependent on vol regime
8. Miner hash-rate directional (CRYPTO) — regulatory vs economic hash drops conflated
9. Dual momentum cross-asset (EQUITY/BOND rotation) — sign-unstable at 14d resolution
10. USD Index inverse correlation (COMMODITY) — DXY regime shift 2024
11. Options put/call ratio contrarian (EQUITY) — gamma-squeeze regime inverts signal

The common failure mode: all signals are BEHAVIORAL or REGIME-DEPENDENT — their causal
mechanism's sign can flip between market states.

Your task: propose ONE new causal hypothesis that is STRUCTURALLY SIGN-STABLE — meaning the
underlying mechanism CANNOT logically invert regardless of market regime. Explain why.

Requirements:
- Must name the specific asset class
- Must name the data source (free, retail-accessible)
- Must estimate eff size at 14-day resolution
- Must identify the one scenario that could cause the signal to fail anyway
- Must NOT be any of the 11 killed hypotheses above or close variants

Return JSON: {"hypothesis_id": "<H-NNN>", "signal_name": "<>", "asset_class": "<>",
"causal_mechanism": "<>", "sign_stability_argument": "<why the sign cannot flip>",
"data_source": "<>", "estimated_eff_14d": <0.0-1.0>, "failure_scenario": "<>",
"pre_register": true|false}
```

**Session context:** This prompt ran at $0.02 quality tier across 5-7 models per ring run.
Result: 0/11 hypotheses survived the harness. Only H-032 (BTC miner capitulation via hash ribbon)
survived initial screening but was flagged as potentially failing the 14-day window resolution
requirement (signal fires ~once per 18-24 months; 14-day windows too short to capture).

---

## SECTION 2: ENHANCED RING PROMPT VARIANTS

### V2 — Daily Return Series + Window Count Specificity

**What is different from V1:** V2 requires that eff be computed on a DAILY PnL series, not
on aggregated entry-to-exit buckets. Several killed hypotheses appeared sign-stable on bucket-level
averages but failed when decomposed into daily returns. V2 also specifies the exact window structure.

```
Algo system, walk-forward sign-stability harness. 11/11 pre-registered causal hypotheses killed.
Harness spec (EXACT, not approximate):

HARNESS REQUIREMENTS:
- eff = Cohen's d computed on DAILY PnL% return series (NOT entry-to-exit bucket averages)
  - eff = mean(daily_returns_in_signal_on) / std(daily_returns_in_signal_on) × sqrt(n)
  - Minimum n_daily_obs = 20 per 14-day window to count as valid
- Window count = FIVE non-overlapping 14-day windows in the test period (70 calendar days total)
- Sign-stable = same sign of eff in >= 3 of the 5 windows
- Net = subtract 15bps per entry leg and 15bps per exit leg from each trade's return before
  computing daily return series
- Test period = most recent 70 calendar days of live data (NOT backtest, NOT synthetic)

KILLED HYPOTHESES (do not propose variants of these):
COT net positioning, BTC funding-rate directional, roll-yield carry, PEAD, on-chain
exchange net-flow, FOREX carry rate-differential, VIX slope directional,
miner hash-rate directional (on-chain count variant), dual momentum cross-asset,
DXY inverse correlation (directional), options put/call ratio contrarian.

TASK: Propose ONE new signal. For it to be valid, it must produce eff >= 0.30 on a DAILY
return series in 3/5 14-day windows. This rules out low-frequency signals (monthly, quarterly)
unless they produce a measurable daily drift during the signal-on period.

Return JSON:
{
  "hypothesis_id": "<H-NNN>",
  "signal_name": "<>",
  "asset_class": "<CRYPTO|EQUITY|FOREX|COMMODITY|FUTURES|BOND|ETF>",
  "causal_mechanism": "<>",
  "daily_drift_explanation": "<how does this signal produce a daily drift, not just a periodic jump?>",
  "sign_stability_argument": "<>",
  "data_source": "<free, retail-accessible>",
  "estimated_eff_14d_daily": <0.0-1.0>,
  "n_daily_obs_per_window_estimate": <integer>,
  "failure_scenario": "<>",
  "pre_register": true|false,
  "daily_vs_entry_exit_difference": "<does computing on daily vs entry/exit change your eff estimate significantly?>"
}
```

---

### V3 — Per-Asset-Class Split with Class-Specific Forbidden Lists

**What is different from V1/V2:** V3 is run as 7 parallel instances (one per asset class),
each with a class-specific forbidden list that goes beyond the global kill list. This prevents
models from proposing class-inappropriate variants of already-killed ideas.

**Instructions:** Replace `{ASSET_CLASS}` with the target class when launching each ring instance.
Run all 7 in parallel. Compare cross-model consensus within each class.

```
Algo system, walk-forward sign-stability harness (eff>=0.30, same sign >=3/5 14-day windows,
net 30bps). All 11 pre-registered hypotheses killed. Now running PER-ASSET-CLASS investigation.

GLOBAL FORBIDDEN LIST (killed across all classes):
COT net positioning, funding-rate directional, roll-yield carry, PEAD, on-chain exchange
net-flow, FOREX carry differential, VIX slope, dual momentum cross-asset, DXY inverse corr,
put/call contrarian, miner hash-rate raw directional.

You will answer for EXACTLY ONE asset class. Your class is: {ASSET_CLASS}

CLASS-SPECIFIC ADDITIONAL FORBIDDEN LIST:

If CRYPTO:
  Also forbidden: stablecoin market cap directional, liquidation cascade leading indicator,
  hash-rate raw directional (see global list), whale wallet count, social sentiment directional
  (Fear & Greed Index), NVT ratio directional.
  Rationale: sign flips with market maturity, regulatory actions, or macro regime.

If EQUITY:
  Also forbidden: momentum factor (12-1m) without regime gate, value spread directional,
  earnings revision pure momentum, analyst consensus directional, short interest contrarian pure.
  Rationale: all sign-flip in growth/value regime transitions and during earnings seasons.

If FOREX:
  Also forbidden: carry differential (already global), rate-differential directional without lag
  adjustment, PPP fair-value directional (30yr convergence is sign-unstable at 14d),
  retail sentiment contrarian (sign flips with institutional flow).
  Rationale: BoJ 2024-25 tightening killed carry; PPP too slow; sentiment inverts at extremes.

If COMMODITY:
  Also forbidden: seasonal pattern pure (COT timing leakage risk + seasonal shifts),
  roll-yield directional, inventory directional alone (EIA report sign instability),
  DXY inverse correlation directional.
  Rationale: all killed or pending kill in sessions AO/AX/BB.

If FUTURES:
  Also forbidden: CTA trend-following pure (already killed in prior sessions), roll-yield carry
  (global), COT commercials/speculators net directional.
  Rationale: CTA trend sign-flips with vol regime; roll-yield killed globally.

If BOND:
  Also forbidden: duration momentum pure, yield-curve slope directional (sign flips with Fed
  pivot timing), credit-spread lead directional (noisy at 14d resolution).
  Rationale: BOND offline PF 1.62 but Sharpe 0.57 (low consistency); live n too thin.

If ETF:
  Also forbidden: sector rotation momentum pure, VIX slope (global), cross-ETF correlation
  directional, factor tilt (value/growth/momentum) without regime gate.
  Rationale: sector rotation sign-flips with macro regime; factor tilts killed in Q factor crash.

TASK: Propose ONE hypothesis for your assigned class that avoids ALL forbidden items (global +
class-specific). The mechanism must be sign-stable within YOUR CLASS's specific market structure.

Return JSON:
{
  "asset_class": "{ASSET_CLASS}",
  "hypothesis_id": "<H-NNN>",
  "signal_name": "<>",
  "causal_mechanism": "<>",
  "why_not_in_forbidden_list": "<explicit argument distinguishing from forbidden items>",
  "sign_stability_argument": "<class-specific reasoning>",
  "data_source": "<free, retail-accessible>",
  "estimated_eff_14d": <0.0-1.0>,
  "failure_scenario": "<>",
  "pre_register": true|false
}
```

---

### V4 — Adversarial Red-Team Constraint

**What is different from V1/V2/V3:** V4 forces the model to argue AGAINST itself before
proposing. Models that red-team their own ideas produce more sign-stable proposals because the
internal contradiction (if any) surfaces before commitment. Run V4 at the highest quality tier
($0.06) only on hypotheses that survived V1/V2 screening.

```
Algo system, walk-forward sign-stability harness (eff>=0.30, same sign >=3/5 14-day windows,
net 30bps). 11/11 pre-registered causal hypotheses killed. Common failure mode: signals that
look structurally sound have a regime-dependent sign.

ADVERSARIAL TASK (two-stage):

STAGE 1 — RED-TEAM FIRST (complete before Stage 2):
Before proposing a new signal, argue the STRONGEST POSSIBLE CASE for why ANY new signal
you could propose will ALSO be killed by this harness. Your red-team must:
- Name at least 2 market regimes in which the sign could flip
- Name at least 1 data quality issue that could corrupt the daily return series
- Name at least 1 structural change (regulatory, technological, macro) that has historically
  changed the sign of similar signals in the past 5 years
- Score your own red-team confidence: how confident are you (0-100%) that ANY new signal
  you propose will fail the harness?

STAGE 2 — PROPOSE ANYWAY:
After the red-team, propose ONE hypothesis. Constraints:
- You MUST explicitly neutralize each of your own Stage 1 red-team objections in the proposal
- You MUST explain which component of this signal's mechanism is INVARIANT to regime change
- You MUST propose a falsification pre-screen (a quick test to run BEFORE the full 70-day harness)

Return JSON:
{
  "red_team": {
    "regime_flip_scenarios": [
      "<regime 1 description + mechanism that would flip sign>",
      "<regime 2 description + mechanism that would flip sign>"
    ],
    "data_quality_corruption_risk": "<specific field or API that could produce bad daily returns>",
    "historical_structural_sign_change": "<event + year + mechanism that changed a similar signal>",
    "red_team_confidence_pct": <0-100>
  },
  "proposal": {
    "hypothesis_id": "<H-NNN>",
    "signal_name": "<>",
    "asset_class": "<>",
    "causal_mechanism": "<>",
    "red_team_neutralization": {
      "regime_flip_rebuttal": "<why neither flip scenario applies to this signal>",
      "data_quality_mitigation": "<specific data cleaning step that prevents corruption>",
      "structural_change_robustness": "<why the structural change cited does not affect this mechanism>"
    },
    "invariant_mechanism_component": "<the one element that physically cannot change sign>",
    "pre_screen_falsification_test": "<run this first, <5 lines of Python, to reject quickly>",
    "estimated_eff_14d": <0.0-1.0>,
    "pre_register": true|false
  }
}
```

---

## SECTION 3: PER-ASSET-CLASS DIAGNOSIS PROMPTS

One ring-ready prompt per class. Each is self-contained — no need to read other sections before
running. Each asks four core diagnostic questions. Run these when a class is in distress.

---

### CRYPTO Diagnosis Prompt

```
Asset class under review: CRYPTO
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 1,087 (stable sample — sufficient for verdict)
- win_rate: 44.3% (sub-50% T2 floor — losing picks majority)
- profit_factor: 0.63 (stressed — destroying capital on net)
- realized_wr_30d: 45.7% (2,897 picks in 30d rolling — high volume, thin edge)
- sizing_allowed: FALSE
- Elite strategies: PF 2.34-3.97 (e.g., ml_crypto_pred SHORT, btc_miner_capitulation)
- Key drags identified: quan_engine (18% volume share @ PF 0.70),
  unknown source (7% @ PF 0.35) dragging the class average down

KNOWN INTERVENTIONS ALREADY APPLIED:
- BTC 4h regime gate (NS-F): rejects LONG signals in BEAR regime (close < SMA10)
- ml_crypto_pred LONG reject (NS-D): hard-rejects long-only emitter longs
- 6 UTC death-zone filter: marginal +1.11pp WR lift (real death zone, not 22 UTC as prior memory claimed)
- per_source_volume_cap.py: wired but quan_engine volume share remains high
- DYDXUSDT blocked: data artifact (source='?', avg PnL ~0.02%)

QUESTIONS FOR DIAGNOSIS:

Q1. ROOT CAUSE: What is the MOST LIKELY root cause of CRYPTO's PF=0.63?
Evaluate each option with a confidence score (0-100%):
(a) Insufficient symbol diversity — system over-concentrated on BTC/ETH while altcoin
    alpha has shifted to memecoins/L2s post-2024
(b) Strategy family exhaustion — all active CRYPTO strategies use the same momentum/
    mean-reversion family, producing correlated failures
(c) Data quality — quan_engine source system emits signals on bad or delayed data
(d) Cost floor — 30bps is too high for the tick-size and spread of the traded universe
(e) Direction asymmetry — LONGs have ~38% WR but represent 8x the volume of SHORTs (65% WR)
Rank all 5 by confidence. For the top-ranked, specify the exact fix (file + function + change).

Q2. THREE HIGHEST-LEVERAGE CHANGES: What 3 changes have the highest expected PF lift per
dev-hour? For each:
- Exact code change (file + function + logic rule)
- Expected PF delta (e.g., +0.3 PF)
- Implementation hours
- Risk of regression on working SHORT signals

Q3. DATA SOURCE UNLOCK: What free, retail-accessible data source would unlock the most
CRYPTO edge that we are NOT currently using?
Rank these candidates by expected PF lift:
- mempool.space block data (hash rate, miner revenue, difficulty)
- Binance funding rate history (free API, hourly)
- CoinGlass liquidation data (free tier, aggregated OI)
- Glassnode community metrics (SOPR, MVRV, NVT — free tier)
- DeFiLlama TVL by chain (L2 flow as leading indicator)
For each: name the specific signal (not just the source) and estimate eff at 14d resolution.

Q4. MINIMUM VIABLE UNIVERSE: What N_symbols × M_strategies is needed to expect
eff >= 0.30 in 3/5 14-day windows at the CRYPTO class level?
Assumptions: strategies are partially correlated (rho=0.3 avg). Current: n=1,087 resolved.
Is n=1,087 sufficient (power is not the problem), or is the problem signal quality?
What is the minimum per-signal eff needed for a blended class eff of 0.30?

Return JSON with keys: root_cause_ranking, leverage_changes, data_source_ranking,
minimum_viable_universe, single_most_important_action.
```

---

### EQUITY Diagnosis Prompt

```
Asset class under review: EQUITY
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 5 (insufficient_data — likely a pipeline staleness bug)
- win_rate: 20.0% (meaningless at n=5 — sampling artifact)
- profit_factor: 0.25 (insufficient_data)
- realized_wr_30d: 57.1% (84 picks in 30d rolling — this is the real signal)
- sizing_allowed: FALSE
- Historical peak: PF 1.58 / WR 53.7% / n=421 (as of 2026-05-13)
- Offline backtest evidence: EQUITY VIX<22 + YC>0 (10y-2y yield curve positive):
  PF 4.98 / Sharpe 2.08 / MDD 16.8% (already wired, default OFF)
- AMD blocked (WR=8%, n=12, monitoring-only declared Session BC)

CRITICAL OBSERVATION: The 30-day realized WR = 57.1% (n=84) is ABOVE the T2 floor of 50%,
but aggregate resolved_n = 5. This discrepancy suggests a resolver or dashboard payload bug,
not a signal quality problem.

QUESTIONS FOR DIAGNOSIS:

Q1. ROOT CAUSE OF n=5 DISCREPANCY: Why would EQUITY resolved_n drop from 421 to 5 while
30d realized_n=84 and realized_wr=57.1%?
Rank these explanations by likelihood:
(a) Outcome resolver stopped resolving picks (EQUITY picks not reaching CLOSED state)
(b) Pick emitters stopped generating EQUITY signals (EQUITY emission rate = 0)
(c) Dashboard payload for EQUITY class is stale / not refreshing correctly
(d) Quality gates over-filtering EQUITY picks post-recent gate tightening (M-019 MDD gate,
    M-040 verify_citations, M-041 slippage wire-in)
(e) BLOCKED_SYMBOLS or BLOCKED_ASSET_STRATEGY combinations eliminated most EQUITY universe
Name the specific diagnostic query (Python or SQL) to confirm the top-ranked cause.

Q2. OFFLINE-TO-LIVE GAP: If the pipeline is restored, what 3 changes close the gap from
live PF 1.58 to the offline target of PF 2.5+?
The VIX<22 + YC>0 gate is already wired (default OFF). Is enabling it the primary lever,
or does the offline edge depend on the pick universe being more diversified than the live one?

Q3. DATA SOURCE UNLOCK: What free EQUITY-specific data source produces sign-stable signals
at 14-day resolution?
Rank these candidates:
- FRED EFFR + DGS10 (yield curve proxy, already partially wired)
- yfinance ^VIX (volatility regime, already partially wired)
- SEC EDGAR 13F filings (institutional flow, quarterly — 14d resolution mismatch?)
- FINRA short interest (monthly, 14d resolution mismatch?)
- Earnings calendar (event-driven, free via yfinance .calendar)
For each: is this a timing-leakage risk? Estimated eff at 14d resolution?

Q4. MINIMUM VIABLE UNIVERSE: How many symbols × strategies does EQUITY need to sustain
eff >= 0.30 in 3/5 14-day windows?
Current 30d run rate: 84 picks / 30 days = ~2.8 picks/day.
Is the universe (top-30 large-cap) sufficient, or does EQUITY need a broader symbol set
(mid-cap, international ADRs, sector ETFs) to generate enough daily signal volume?

Return JSON with keys: root_cause_ranking, pipeline_diagnostic_query, offline_to_live_gap_fixes,
data_source_ranking, minimum_viable_universe, single_most_important_action.
```

---

### FOREX Diagnosis Prompt

```
Asset class under review: FOREX
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 144 (stable sample — sufficient for T2 verdict)
- win_rate: 57.6% (ABOVE T2 floor of 50% — significant turnaround)
- profit_factor: 1.64 (AT T2 threshold — improvement from PF=0.27 six sessions ago)
- realized_wr_30d: 57.7% (n=78 in 30d rolling — consistent)
- sizing_allowed: TRUE (circuit breaker not breached)

TURNAROUND CONTEXT (prior state 2026-05-13):
- n=1,169, WR=46.4%, PF=0.27 — catastrophically sub-floor
- Per-symbol decomposition: ALL 5 JPY-cross pairs were catastrophic (n=484, ~4% WR)
  EURJPY: WR=1.9%, USDJPY: WR=3.0%, GBPJPY: WR=7.1% — all near zero
- Non-JPY majors were positive: EURGBP WR=63.2%/PF=2.35, GBPUSD WR=61.5%/PF=1.87,
  AUDUSD WR=62.5%/PF=2.67, USDCHF WR=100%/n=8

INTERVENTIONS APPLIED:
- FX1 + M-063: JPY-cross block (EURJPY/USDJPY/GBPJPY/AUDJPY/CADJPY blocked)
- M-078: FOREX session gate (fail-closed 08-16 UTC)
- FOREX_COPYTRADER direction-bias correction (WR corrected to 16.5% from claimed 64.7%)
- M-063 JPY-cross hypothesis registered: BoJ tightening 2024-25 inverted LONG-USD-vs-JPY carry

QUESTIONS FOR DIAGNOSIS:

Q1. SUSTAINABILITY RISK: FOREX has improved dramatically. What is the highest-risk scenario
that could push PF back below 1.0?
Rank:
(a) BoJ reversal or further surprise tightening reactivates JPY-cross losses (even with block)
(b) Non-JPY major edge (n=88) is noise — small sample with lucky WR, will mean-revert
(c) Session gate (08-16 UTC) is too restrictive, filtering out genuinely good signals outside hours
(d) 30bps cost floor is eating all the edge on FOREX (tight spreads but frequent trades)
(e) ECB/Fed divergence inverts EURGBP or GBPUSD edge (rate-differential sign flip)
For the top-ranked risk: what is the specific early warning indicator to monitor weekly?

Q2. THREE HIGHEST-LEVERAGE CHANGES: To push FOREX PF from 1.64 to a stable 1.5+ across
5+ consecutive 14-day windows, what 3 changes are most important?
Consider: (a) adding a second non-JPY strategy family to reduce copytrader dependence,
(b) extending the session gate hours, (c) adding FRED rate-differential filter for ECB/Fed.

Q3. DATA SOURCE UNLOCK: What free FOREX data source would most improve sign-stability?
Rank these candidates:
- FRED DGS10 by country proxy (yields for USD/EUR/GBP/AUD rate differential)
- OANDA free sentiment API (COT-like retail positioning)
- Central bank policy calendars (BoE, ECB, Fed, RBA schedule — event-driven gate)
- CFTC COT non-commercial positioning (weekly, FOREX futures — timing lag risk)
- BIS effective exchange rate indices (broad trade-weighted FX, monthly)
For each: estimate sign-stability at 14d resolution; is this a timing-leakage risk?

Q4. MINIMUM VIABLE UNIVERSE: What N_pairs × M_strategies does FOREX need to sustain T2
across diverse macro regimes (rate-hiking, rate-cutting, range-bound)?
Current: 144 resolved across ~8-10 pairs × ~3 strategy families. Non-JPY base: ~88 picks.
Is diversification the limiting factor (need more non-JPY pairs), or is the current edge
deep enough if we add one more strategy family per pair?

Return JSON with keys: sustainability_risk_ranking, early_warning_indicators, leverage_changes,
data_source_ranking, minimum_viable_universe, single_most_important_action.
```

---

### COMMODITY Diagnosis Prompt

```
Asset class under review: COMMODITY
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 52 (candidate tier — above display floor of 10, below stable floor of 100)
- win_rate: 57.7% (above T2 floor)
- profit_factor: 1.73 (T2 candidate — needs n=100 to confirm)
- realized_wr_30d: 54.4% (n=57 — slightly lower than resolved WR, within tolerance)
- sizing_allowed: FALSE (n below stable floor)

KNOWN ISSUES:
- COT timing leakage: COT 3-day publication lag may inflate WR in backtest vs live.
  Estimated corrected WR: 45-55% (unverified post-patch, per prior swarm estimate)
- CT=F (Cotton) concentration: ~87% of COMMODITY picks on single symbol — extreme idiosyncratic risk
- cta_cross_asset_tsmom: WR=12.7% / n=71 — blocking raises estimated PF from 2.28 → 6.67
  BUT: cot_net_z field was NEVER populated in live (dead field emitting signals on zero data)
- cta_replicator: WR=12% / n=83 / 0 CT=F picks — similar dead-field issue suspected
- Walk-forward: NOT connected to live COMMODITY emission path

QUESTIONS FOR DIAGNOSIS:

Q1. ROOT CAUSE: Is COMMODITY's primary problem:
(a) Symbol concentration risk (87% CT=F — single weather/policy event could corrupt the class)
(b) Data quality — cot_net_z field never populated; strategies emitting signals on null data
(c) Strategy family failure — cta_cross_asset_tsmom + cta_replicator both WR~12%
(d) Timing leakage — COT 3-day lag inflating backtest WR vs live
(e) Sample size — n=52 resolved; numbers will revert toward true mean as more picks resolve
Rank all 5 by confidence. Name the specific fix for the top-ranked cause (file + function).

Q2. THREE HIGHEST-LEVERAGE CHANGES: Beyond blocking cta_cross_asset_tsmom and cta_replicator,
what 3 changes would push COMMODITY to verified T2 (PF>=1.5, WR>=50% post-lag-patch, n>=100)?
For each: expected WR/PF delta, implementation hours, regression risk.

Q3. DATA SOURCE UNLOCK: What free COMMODITY data source unlocks the most edge?
Rank these candidates:
- USDA WASDE (crop supply/demand, monthly — timing lag risk?)
- NOAA climate forecasts (seasonal crop impact — 90-day horizon, 14d mismatch?)
- EIA petroleum status (weekly, crude oil/products — sign stability?)
- CFTC COT (already partially wired but cot_net_z dead — fix the dead field vs new source?)
- LME inventory levels (metals — aluminum, copper, zinc; free via LME website)
For each: is the timing lag (publication delay) a risk? Is it backtestable 10+ years?

Q4. MINIMUM VIABLE UNIVERSE: What N_commodities × M_strategies is needed for COMMODITY
to reach n=100 resolved and sustain T2?
Current: 52 resolved. If emission rate = ~10/month, timeline to n=100 is ~5 more months.
Would expanding from CT=F-dominant to a 5-symbol basket (CT/GC/SI/HG/ZC) cut that timeline?
What is the minimum per-strategy WR needed across the basket to sustain class-level WR=50%?

Return JSON with keys: root_cause_ranking, leverage_changes, data_source_ranking,
minimum_viable_universe, timeline_to_stable_floor, cot_patch_recommendation,
single_most_important_action.
```

---

### FUTURES Diagnosis Prompt

```
Asset class under review: FUTURES
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 12 (thin sample)
- win_rate: 16.7% (far below T2 floor — live emitters appear broken)
- profit_factor: 0.96 (sub-1.0 — losing money on net)
- realized_wr_30d: 66.7% (n=3 — micro sample, statistically unreliable)
- sizing_allowed: FALSE

ACADEMIC BACKTEST EVIDENCE (tools/backtest_futures_ts_momentum.py, session 2026-05-13):
Universe: 14 liquid yfinance continuous-contract futures (CT/GC/SI/HG/ZC/ZW/ZS/NG/ES/NQ/ZN/ZB/6E/6J)
Signal: Moskowitz-Ooi-Pedersen 2012 time-series momentum, 12m lookback, inverse-vol weights
- LONG-ONLY variant: WR 61.4% / Sharpe 0.86 / MDD 6.57% — passes T1 MDD threshold
- LONG-SHORT variant: PF 1.71 / WR 58.1% / MDD 13.6% / n=160 — T2 confirmed

THE GAP: Academic backtest shows WR=61.4%. Live emitters show WR=16.7%. This is NOT a
signal quality problem — it is a live-emission pipeline problem.

KNOWN ISSUES:
- multi_asset_copytrader FUTURES: WR=3% — essentially noise, not TS-momentum
- FUTURES live emitters appear "silent-dead" — not generating TS-momentum signals
- No walk-forward connected to live FUTURES emission
- CL=F excluded from academic universe per prior memory

QUESTIONS FOR DIAGNOSIS:

Q1. ROOT CAUSE OF LIVE-TO-ACADEMIC GAP: Why does the live system show WR=16.7% when
the academic TS-momentum backtest shows WR=61.4%?
Rank these explanations:
(a) Live emitter (multi_asset_copytrader) does not implement TS-momentum — uses different logic
(b) Live universe does not match academic 14-symbol universe — may use different symbols
(c) Picks are generated but the resolver does not correctly close/score FUTURES picks
    (ticker format mismatch: "ES=F" vs "ES" vs "/ES")
(d) 30bps cost assumption wrong — FUTURES actual slippage + roll cost > 30bps
(e) TS-momentum signal fires on monthly rebalance but live system scores at shorter intervals,
    producing mid-signal interference
For each: name the diagnostic test to confirm or refute.

Q2. PIPELINE RECONSTRUCTION: What 3 changes would translate the academic TS-momentum
edge (Sharpe 0.86, MDD 6.57%) into live /audit picks?
Specifically: which file in alpha_engine/ should emit TS-momentum FUTURES signals?
What is the correct emission frequency (monthly vs weekly)? How should the inverse-vol
weight translate into pick confidence scores?

Q3. DATA SOURCE UNLOCK: What free data source would most improve FUTURES beyond TS-momentum?
Rank:
- yfinance continuous contracts (already used in academic backtest)
- CFTC COT (wired via tools/cot_fetcher_socrata.py — but COT is already on global kill list for
  direction signals; does it add value as a filter rather than a primary signal?)
- FRED commodity prices (DCOILWTICO, copper, gold spot — potential regime overlay)
- CME Group economic calendar (free, event-driven timing filter)
For each: does it improve on TS-momentum baseline or just replicate a killed hypothesis?

Q4. MINIMUM VIABLE UNIVERSE: What N_contracts × M_strategies does FUTURES need to hit
n=100 resolved picks in 90 days?
At monthly rebalance: 14 contracts × 12 months = 168 signal opportunities/year → n=100 in ~7 months.
Is monthly the right rebalance period for 14-day harness windows?
Would weekly rebalance (14 × 52 = 728 opportunities/year) produce enough n faster without
destroying the academic edge (which is built on monthly momentum)?

Return JSON with keys: root_cause_ranking, diagnostic_tests, pipeline_reconstruction_plan,
data_source_ranking, minimum_viable_universe, rebalance_period_recommendation,
single_most_important_action.
```

---

### BOND Diagnosis Prompt

```
Asset class under review: BOND
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 1 (cold start — effectively no data)
- win_rate: 0.0% (insufficient_data)
- profit_factor: 0.0 (insufficient_data)
- realized_wr_30d: 0 picks (no 30d rolling data)
- sizing_allowed: FALSE (cold start)

OFFLINE BACKTEST EVIDENCE (tools/backtest_bond_tlt_ief_momentum.py, session 2026-05-13):
- HYG/LQD 6m skip-1 momentum: PF 1.62 / WR 62.7% / Sharpe 0.57 / n=~250 over 22 years
- Known weakness: Sharpe 0.57 is the lowest of any backtested class (low consistency)
- Historical live high: n=11, WR=54.5%, PF=0.66 (as of 2026-05-13)
- Now regressed to n=1

INFRASTRUCTURE IN PLACE:
- etf-bond-scanner.yml confirmed canonical (8 strategies)
- BOND VIX exemption added (Session CX — bonds exempt from VIX gate that applies to EQUITY)
- B-003/B-004: FRED wire + UST TSMOM in flight (Session CX)
- feed_hygiene = 0.0 sentinel documented (possible emission suppressor)

QUESTIONS FOR DIAGNOSIS:

Q1. ROOT CAUSE OF n=1: Why is BOND at cold-start despite the scanner running with 8 strategies?
Rank:
(a) feed_hygiene = 0.0 sentinel is causing the scanner to abort before emitting picks
(b) B-003/B-004 FRED wire is coded but not yet generating live signals (wire-up incomplete)
(c) The 8 bond strategies have quality gates too strict for BOND's thin universe
    (e.g., WR floor > current expected WR, or confidence floor the strategies cannot meet)
(d) Picks are generated but the outcome_resolver cannot close BOND picks (wrong ticker format
    for bond ETFs: "HYG" vs "HYG=F" vs Yahoo Finance format)
(e) The BOND VIX exemption (Session CX) introduced a logic error that accidentally blocks
    BOND picks instead of exempting them
For the top-ranked: name the exact diagnostic check (file + line range to inspect).

Q2. VOLUME GROWTH PLAN: What 3 changes would most rapidly grow BOND resolved_n from 1 to 100
while maintaining WR > 50%?
For each: distinguish whether this is a volume-growth change (more picks emitted) or a
quality change (better WR on existing picks). We need BOTH: n=100 AND WR>50%.

Q3. DATA SOURCE UNLOCK: What free BOND data source produces sign-stable signals at 14d resolution?
Rank:
- FRED BAMLH0A0HYM2 (OAS HY credit spread, daily — strong economic logic)
- FRED DGS10/DGS2 (10y-2y yield curve, daily)
- FRED TEDRATE (TED spread, money market stress, daily)
- Federal Reserve H.15 (full treasury yield history, free)
- FRED MORTGAGE30US (mortgage rate as duration/rate sensitivity proxy)
For each: (a) sign-stability at 14d, (b) economic causal logic strength,
(c) data history depth (years available), (d) timing-leakage risk.

Q4. MINIMUM VIABLE UNIVERSE: What N_instruments × M_strategies does BOND need?
Current liquid universe: TLT / IEF / SHY / HYG / LQD / TIP / TIPX / BIL / VTIP / EMB (10 ETFs).
With 8 strategies × 10 ETFs = 80 signal opportunities/cycle. At monthly rebalance:
80/month × 12 = 960/year; at T2 WR=50% → 480 wins/year. But n=100 stable floor needed.
Timeline to n=100 at current emission rate: estimate.
Would moving to weekly rebalance accelerate n growth while maintaining edge?
What is the trade-off between WR at monthly vs weekly rebalance for bond momentum signals?

Return JSON with keys: root_cause_ranking, diagnostic_checks, volume_growth_plan,
quality_protection_plan, data_source_ranking, minimum_viable_universe,
rebalance_period_recommendation, single_most_important_action.
```

---

### ETF Diagnosis Prompt

```
Asset class under review: ETF
System: findtorontoevents.ca/audit algorithmic trading pipeline

CURRENT STATUS (as of 2026-05-19, source: live dashboard_data.json):
- resolved_n: 1 (insufficient_data — near cold-start)
- win_rate: 100.0% (meaningless at n=1 — sampling artifact)
- profit_factor: null (insufficient_data)
- realized_wr_30d: 57.1% (49 picks in 30d rolling — positive signal of underlying health)
- sizing_allowed: FALSE

HISTORICAL PEAK (session 2026-05-13):
- PF 1.24 / WR 55.2% / n=87 (borderline T2 — n approaching 100 stable floor)

OFFLINE BACKTEST EVIDENCE (tools/backtest_etf_sector_rotation.py, session 2026-05-13):
- ETF sector top-3 rotation (monthly) + VIX<22: PF 3.32 / Sharpe 1.68 / MDD 11.8% (near T1)
- Without VIX gate: PF 2.05 / Sharpe 0.97 (T1 PF, T2 Sharpe)
- VIX-ETF gate wired (VIX_REGIME_GATE_ENABLED=0 default OFF for ETF)

CRITICAL OBSERVATION: Same pattern as EQUITY — resolved_n=1 but 30d realized shows 49 picks
with WR=57.1%. This is almost certainly the same resolver/dashboard payload staleness bug.

QUESTIONS FOR DIAGNOSIS:

Q1. PIPELINE BUG ASSESSMENT: Is the ETF resolved_n=1 the same bug as EQUITY resolved_n=5?
Compare:
(a) Both EQUITY and ETF show near-zero resolved_n but positive 30d realized — same root cause?
(b) Are ETF picks being classified as EQUITY (confusion on SPY/QQQ/VTI vs EQUITY universe)?
(c) Is the ETF outcome_resolver using a different status field than the dashboard reads?
(d) Did a recent quality gate change (M-019 MDD gate, M-080 ETF WR=0.0 bug fix) introduce
    a regression that filters ETF picks before they reach resolved status?
Name the specific code path to inspect (file + function + line range).

Q2. VIX GATE ACTIVATION: Given offline PF 3.32 vs VIX<22, should VIX_REGIME_GATE_ENABLED
be set to 1 for ETF?
Arguments for: PF uplift 2.05 → 3.32 in offline; VIX<22 regime is most of the time.
Arguments against: live n=1 (cannot verify live behavior); may over-filter good picks during
VIX=22-25 range which historically still has edge.
What shadow-mode test would confirm the gate is additive before enabling in production?

Q3. DATA SOURCE UNLOCK: What free data source adds the most ETF edge?
Rank:
- yfinance ^VIX (volatility regime — already partially wired via VIX_REGIME_GATE_ENABLED)
- FRED DGS10-DGS2 yield curve (macro regime overlay for sector rotation)
- ETF fund flow data (ETF.com free summary, weekly — contrarian flow signal?)
- Sector earnings calendar (finviz free, event-driven sector bias)
- CBOE delayed options data (put/call per sector ETF — already on global kill list as
  put/call contrarian; would per-ETF version be different?)
For each: sign-stability score at 14d, and is this a variant of a killed hypothesis?

Q4. MINIMUM VIABLE UNIVERSE: What N_ETFs × M_strategies does ETF need?
Current tradeable universe: SPY/QQQ/IWM (broad), XLK/XLF/XLE/XLV/XLY/XLP/XLI (sector),
GLD/SLV/USO (commodity ETF), TLT/HYG (bond ETF), EEM/EFA (international) — ~20 ETFs.
With academic evidence for sector top-3 rotation (8 strategies × 20 ETFs = 160 signal ops/cycle):
Is the symbol breadth sufficient? Is the strategy diversity sufficient?
Is breadth (more ETFs, e.g., adding thematic ETFs: ARKK, BOTZ, ICLN) or depth
(more strategy families per ETF) the higher-leverage axis?

Return JSON with keys: pipeline_bug_assessment, root_cause_ranking, vix_gate_recommendation,
shadow_test_plan, data_source_ranking, minimum_viable_universe, single_most_important_action.
```

---

## SECTION 4: CURRENT ASSET CLASS STATUS TABLE

Data sources: `audit_dashboard/data/dashboard_data.json` (live, 2026-05-19),
session memory files (projects/sessions AH/AK/AO/AX/BA/BB/BC/BY/CX).

| Class | Live n | Live WR% | Live PF | Status | 30d WR% | 30d n | T2? | Key Issue |
|-------|-------:|----------:|--------:|:-------|----------:|------:|:---:|:----------|
| CRYPTO | 1,087 | 44.3% | 0.63 | stressed | 45.7% | 2,897 | NO | quan_engine (18% vol, PF 0.70) drag; n large but WR sub-floor |
| EQUITY | 5 | 20.0% | 0.25 | insuff. | 57.1% | 84 | BUG | Pipeline staleness; resolver not updating aggregate n counter |
| FOREX | 144 | 57.6% | 1.64 | stable | 57.7% | 78 | YES | Turnaround post-JPY block; T2 threshold reached; sustain now |
| COMMODITY | 52 | 57.7% | 1.73 | candidate | 54.4% | 57 | NEAR | COT timing leakage unverified; CT=F 87% concentration risk |
| FUTURES | 12 | 16.7% | 0.96 | thin | 66.7% | 3 | NO | Live emitters broken; academic Sharpe 0.86 not wired to live |
| BOND | 1 | 0.0% | 0.0 | cold | — | 0 | NO | Cold start; FRED wire in flight; feed_hygiene sentinel suspect |
| ETF | 1 | 100% | null | insuff. | 57.1% | 49 | BUG | Same pipeline bug as EQUITY; offline PF 3.32 (near T1) |

**T2 Criteria:** PF >= 1.5 / WR >= 50% / n >= 100 stable  
**T1 Criteria:** PF >= 2.0 / WR >= 55% / MDD <= 10%  
**T1 Renaissance Target:** PF >= 2.0 / WR >= 55% / MDD <= 10% (per CLAUDE.md MAJOR GOAL #1)

### Classes at or approaching T2 (live):
- **FOREX:** PF 1.64 / WR 57.6% / n=144 — AT T2 on all metrics. Sizing allowed. Sustain focus.
- **COMMODITY:** PF 1.73 / WR 57.7% / n=52 — T2 metrics but n below 100 stable floor.
  COT timing leakage patch needed before confirming.

### Classes with healthy 30d signal but broken aggregate counter (pipeline bug):
- **EQUITY:** 30d WR=57.1% (n=84) — healthy signal; aggregate counter broken (n=5 = bug)
- **ETF:** 30d WR=57.1% (n=49) — healthy signal; aggregate counter broken (n=1 = bug)

### Classes in structural distress:
- **CRYPTO:** n=1,087 resolved (no pipeline bug) but PF=0.63. Contaminating sources must be cut.
- **FUTURES:** n=12. Live emitters not implementing TS-momentum. Pipeline reconstruction needed.
- **BOND:** n=1. Cold start. FRED wire in flight. Scanner running but not emitting.

### Sign-Stability Harness Record (2026-05-18 sessions):
- Hypotheses pre-registered and tested: **11**
- Hypotheses killed by harness: **11** (0% survival rate)
- Surviving candidate pending longer-window test: **H-032** (BTC miner capitulation / hash ribbon)
- H-032 concern: signal fires ~once per 18-24 months; 14-day window may be too short to capture

---

## SECTION 5: ACTION PLAN BY ASSET CLASS

### CRYPTO — Volume Surgery First, Research Second

CRYPTO's problem is source contamination, not signal discovery. The elite strategies
(PF 2.34-3.97) are being diluted by quan_engine (18% volume share, PF 0.70) and an unknown
source (7% share, PF 0.35). These two source systems account for 25% of volume at sub-1.0 PF,
pulling the class blended PF to 0.63. The fix is surgical, not research-intensive:
(1) Apply a hard volume cap on quan_engine — reduce its share from 18% to under 5%.
(2) Identify and block the unknown source (source field = '?' or blank).
(3) After the volume surgery stabilizes, submit H-032 (miner capitulation) for 30-day window
validation — this is the only surviving sign-stability candidate and the research path forward.
Direction asymmetry (LONG WR ~38% vs SHORT WR ~65%) remains a secondary lever: a LONG-penalty
on sources below ml_score 0.7 would further lift WR without touching working SHORT signals.

### EQUITY — Pipeline Fix + Regime Gate Trial

The live counter (n=5) is almost certainly a resolver or dashboard payload staleness bug.
The 30-day realized data (WR 57.1%, n=84) is the true signal and it is healthy. Priority one:
diagnose and fix the resolver so the aggregate n counter reflects reality. Priority two: run
the VIX<22 + YC>0 gate (already wired, default-OFF) in shadow mode for 30 days — the offline
evidence (PF 4.98 / Sharpe 2.08) is the strongest of any class, and live WR=57.1% suggests
the underlying picks are already near-T1 quality. EQUITY does NOT need new symbol breadth —
the top-30 large-cap universe is adequate for the TS-momentum signal. AMD and other
monitoring-only symbols (WR=8%, n=12 per Session BC) should be hard-blocked to reduce noise.
The biggest risk is that the regime gate was designed for monthly-rebalance signals — confirm
it does not over-filter on shorter hold periods.

### FOREX — Sustain and Diversify Non-JPY Edge

FOREX has completed its triage. The action plan shifts from rescue to consolidation.
(1) Monitor the next 5 consecutive 14-day windows to confirm PF 1.64 is durable across
changing macro conditions — the non-JPY base (n=88) is thin for long-term stability.
(2) Add a second non-JPY strategy family (FRED rate-differential based, not carry) to reduce
single-source dependence on multi_asset_copytrader. The copy trader's FOREX picks currently
account for nearly all FOREX signals — this is a concentration risk analogous to COMMODITY's CT=F.
(3) Expand the non-JPY pair universe: NZDUSD and USDCAD showed partial-positive signals in the
prior decomposition; adding them with appropriate quality gates could improve n and edge diversity.
The most important single action: do not enable JPY-cross pairs again regardless of BoJ signals —
the sign-flip risk is structural and the block is cost-free.

### COMMODITY — Verify COT Patch + Diversify Beyond CT=F

COMMODITY has a strong surface reading (PF 1.73 / WR 57.7%) but sits on an unverified foundation.
The COT timing-leakage patch (3-day publication lag) has not been run in live — the current metrics
may be pre-patch inflated. Step one: run the lag-corrected backtest and confirm COMMODITY retains
T2 metrics post-correction. Step two: address CT=F 87% concentration — this is not a quality
gate problem, it is a universe diversity problem. Adding GC=F, SI=F, HG=F, ZC=F as co-equal
COMMODITY contributors with their own COT and price-momentum signals would both reduce concentration
and increase n toward the 100 stable floor faster. Step three: block cta_cross_asset_tsmom and
cta_replicator (both WR~12%) pending COT dead-field investigation — these are almost certainly
emitting signals based on cot_net_z=0 (null) rather than real COT data.

### FUTURES — Wire TS-Momentum to Live Emission

FUTURES has a proven academic edge that is not reaching the live system. This is a wire-up task.
The target is to implement the Moskowitz-Ooi-Pedersen TS-momentum logic (12m lookback,
inverse-vol weights, monthly rebalance, 14 liquid continuous-contract futures) as a live alpha_engine
emitter. The academic backtest tool (`tools/backtest_futures_ts_momentum.py`) already contains
the correct signal logic — it needs to be factored into a production emitter in `alpha_engine/`
that runs on the 14-symbol universe and generates picks for the /audit pipeline. Expected outcome:
n grows from 12 toward 168+/year and WR approaches the academic 61.4%. The secondary question is
rebalance period: monthly produces fewer picks (slower n growth) but matches the academic evidence.
Consider a weekly rebalance variant with tighter lookback as a volume-growth experiment.

### BOND — Fix Emission, Not Signal

BOND does not need new research — the HYG/LQD 6m momentum (PF 1.62 / WR 62.7%) is a validated
T2-level signal. The problem is that the live scanner is running but not emitting. The most likely
culprits are the feed_hygiene=0.0 sentinel (suppressing the scanner output) and the B-003/B-004
FRED wire being coded but not fully wired into the emission path. Step one: confirm feed_hygiene
is not zeroing out BOND picks before they reach the resolver. Step two: trace the FRED signal
through B-003/B-004 to confirm it is generating real picks (not just code that compiles without
errors). Step three: consider moving from monthly to weekly rebalance on the bond ETF universe
to accelerate n growth — at monthly rebalance, n=100 takes ~10 months even if the scanner works
correctly; at weekly, it could reach n=100 in 3-4 months. The Sharpe risk (0.57 low consistency)
is acceptable at cold-start and will self-correct with more n.

### ETF — Pipeline Fix + VIX Gate Shadow Run

ETF mirrors EQUITY: the 30-day realized data (WR 57.1%, n=49) is healthy but the aggregate
counter shows n=1. Fix the same resolver/dashboard bug as EQUITY (likely the same root cause).
Once the pipeline is restored, the priority is a 30-day shadow run of the VIX<22 gate
(VIX_REGIME_GATE_ENABLED=1 in shadow mode for ETF). The offline evidence is compelling
(PF 3.32 vs VIX<22, up from PF 2.05 without gate). Shadow mode: log the gate's would-fire
decisions without actually filtering picks, and compare the shadow-filtered subset's WR to
the unfiltered WR after 30 days. If the shadow-filtered subset consistently outperforms by
>3pp WR, enable in production. ETF has the most attractive risk-adjusted offline profile of
any class (PF 3.32 / Sharpe 1.68 / MDD 11.8%) and requires no new research — only pipeline
restoration and VIX gate activation.

---

## APPENDIX A: PROMPT DESIGN LESSONS FROM PRIOR SESSIONS

### Why All 11 Hypotheses Were Killed

The sign-stability harness (eff>=0.30, same sign >=3/5 14-day windows) is intentionally strict.
All 11 killed hypotheses failed for the same structural reason: behavioral or regime-dependent
sign. The categories:

**Behavioral (sign inverts with crowd composition change):**
- COT net positioning — inverts when commercial hedgers change behavior post-regulation
- BTC funding-rate directional — inverts in bear markets as fear-driven shorts dominate
- Options put/call contrarian — gamma-squeeze regimes invert the contrarian signal

**Regime-dependent carry (sign inverts with term structure):**
- Roll-yield carry (FUTURES) — backwardation/contango switch inverts the signal
- FOREX carry rate-differential — BoJ tightening 2024-25 inverted USD-JPY carry
- Dual momentum cross-asset — sign depends on which macro factor is dominant

**Count-based or noise-amplified:**
- On-chain exchange net-flow — stablecoin substitution changes the signal population
- Miner hash-rate directional raw — regulatory (China ban 2021) vs economic drops conflated
- VIX slope directional — sign-dependent on vol regime which itself changes

**Correlation-dependent (correlation sign can flip):**
- DXY inverse correlation (COMMODITY) — DXY regime shift 2024 flipped the sign
- Post-Earnings Announcement Drift — earnings quality regime shifts the direction

**Only category with theoretical sign-stability:** physical/structural cost constraints.
The miner capitulation signal (H-032) is the best candidate: miners MUST sell BTC when
revenue < electricity cost, regardless of market sentiment. This mechanism cannot be behavioral.

### The 14-Day Window Resolution Problem

Signals with natural periods > 14 days (COT weekly, options monthly, earnings quarterly,
12m momentum) appear sign-unstable at 14-day resolution even if the underlying edge is real.
The harness was designed for high-frequency signals with daily drift.

For slow signals: request a longer window variant from the harness operator (30-day, 60-day).
H-032 (miner capitulation) fires once per 18-24 months — a 14-day window is structurally
incompatible. A 60-day window harness would be the correct test vehicle.

### Recommended Ring Run Protocol

For any new hypothesis:
1. V1 ($0.01 tier, 5 models) — fast consensus check. Reject if < 3 models pre-register.
2. V4 ($0.06 tier, top-2 survivors from V1) — adversarial depth check.
3. V3 class-specific ($0.02 tier, survivor's class) — forbidden-list cross-check.
4. If all three tiers produce the same hypothesis with consistent eff estimates: pre-register.

Cost estimate per full ring run (V1 + V4 + V3): approximately $0.30-0.50 at stated tiers.

### Best Prompt Patterns from Existing Library

Extracted from `reports/swarm_revalid_20260513/` and `reports/audit_enhancements_2026-05-13/`:

| Pattern | Why It Works | Source Prompt |
|---------|-------------|---------------|
| Per-symbol decomposition table in context | Forces models to engage with heterogeneity, not average it | `prompt_forex_real.md` |
| Three concrete options (A/B/C) with trade-offs | Models vote on existing options rather than inventing noise | `prompt_edge11_impl.md` |
| Two-item design review structure | Prevents scope creep; each item gets a verdict | `prompt_dual_action_consult.md` |
| `single_most_important_finding` final field | Forces the model to prioritize rather than hedge | All swarm prompts |
| Forbidden list in constraints | Eliminates re-proposals of already-killed hypotheses | V3 variant above |
| Numeric floors in constraints | `reject expected_pf < 1.5` eliminates weak proposals | All revalid prompts |

### Prompt Anti-Patterns to Avoid

- **"Propose 5-7 strategies"** — models pad to hit the count floor with weak proposals. Use "propose 3" max.
- **No forbidden list** — models re-propose carry, momentum, sentiment (all killed). Always include.
- **Open-ended JSON schemas** — keys drift across models, making aggregation hard. Specify all keys.
- **Qualitative confidence ratings** — use numeric eff estimates with stated assumptions instead.
- **No data source constraint** — models propose Bloomberg/Refinitiv dependent signals. Add `use yfinance + FRED only`.
- **Asking for "reasons why X is failing"** without live data in context — models hallucinate metrics.

---

*End of OPENROUTER_RING_PROMPTS.MD*  
*Source files consulted:*  
*- reports/swarm_revalid_20260513/ (6 prompt files)*  
*- reports/audit_enhancements_2026-05-13/ (2 prompt files)*  
*- tools/swarm/prompts/h032_btc_miner_capitulation_validate.md*  
*- reports/prompt_library_analysis_2026-05-16.md*  
*- audit_dashboard/data/dashboard_data.json (asset_class_health live data)*  
*- docs/STRATEGY_INVESTIGATION_rapid_fire_CRYPTO_2026-05-18.md*  
*- Session memory files: AH/AK/AO/AX/BA/BB/BC/BY/CX*

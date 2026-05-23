# Swarm-Picks Forensic Deep-Dive

**Source:** `audit_dashboard/data/dashboard_data.json` -> `swarm_picks_data`
**Generated leaderboard timestamp:** 2026-05-12T21:22:56Z
**Picks window:** 2026-05-11T22:00 to 2026-05-12T16:02 EST (5 sessions)
**Sample size:** 38 picks / 5 resolved / 33 open. WR 40% (2W/3L), PF 0.80.

## CRITICAL UPFRONT FINDING

> Every `models_consulted[*].underlying_model` value is `claude-opus-4-7`. The "swarm" is **one model wearing 17 different persona hats** -- it is NOT a multi-model ensemble. The leaderboard's `by_underlying_model` confirms: `claude-opus-4-7 n_total=81` (single key, all 94 model-rows).
>
> "Per-model" analysis is therefore impossible. The differentiating axis is **persona** (system-prompt role), not model. All sections below substitute persona for `underlying_model`.

Rationale field is `justification_summary` (single sentence). There is no `data_sources_used` field on any of the 94 model rows -- **FIELD_MISSING: `data_sources_used`** across all picks. Numeric grounding has to be inferred from the rationale string.

---

## 1. Per-Persona Summary

`n` = times persona voted on a pick. `n_resolved` = of those picks, how many closed. Confidence = mean of self-reported `confidence_0_100`.

| Persona | n | n_resolved | W | L | WR% | Avg Conf | Asset-class mix | Timeframe mix | Vote bias |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| MOMENTUM_TECH | 15 | 0 | 0 | 0 | n/a | 64.0 | CRYPTO 10, EQUITY 4, ETF 1 | 1D 6, 4H 4, 1W 3, 1M 2 | L7 / S8 |
| MACRO_BEAR | 13 | 0 | 0 | 0 | n/a | 64.4 | CRYPTO 5, EQUITY 4, ETF 2, FX 1, FUT 1 | 1D 5, 4H 3, 1W 3, 1M 2 | L5 / S8 |
| FUND_VALUE | 10 | 0 | 0 | 0 | n/a | 57.0 | CRYPTO 6, EQUITY 3, ETF 1 | 1D 4, 4H 2, 1W 2, 1M 2 | L7 / S3 |
| VOL_TRADER | 9 | 0 | 0 | 0 | n/a | 68.2 | CRYPTO 4, EQUITY 3, ETF 2 | 1D 3, 1M 3, 1W 2, 4H 1 | L3 / S6 |
| NEWS_FLOW | 8 | 1 | 1 | 0 | 100 | 61.9 | ETF 3, CRYPTO 3, EQUITY 2 | 1W 3, 1D 2, 1M 2, 4H 1 | L6 / S2 |
| MEAN_REVERSION | 7 | 0 | 0 | 0 | n/a | 62.9 | EQUITY 3, CRYPTO 2, ETF 2 | 1D 2, 1M 2, 1W 2, 4H 1 | L4 / S3 |
| ONCHAIN_QUANT | 6 | 0 | 0 | 0 | n/a | 61.2 | CRYPTO 5, ETF 1 | 1D 4, 4H 1, 1M 1 | L4 / S2 |
| SEASONAL | 6 | 0 | 0 | 0 | n/a | 66.0 | CRYPTO 3, ETF 2, EQUITY 1 | 1D 3, 1M 2, 1W 1 | L2 / S4 |
| V4_VALUE_SCREENER_SWARM | 6 | 0 | 0 | 0 | n/a | 67.5 | EQUITY 6 | 6M 5, 3M 1 | L6 / S0 |
| LEAP_SWARM_AGG | 3 | 0 | 0 | 0 | n/a | 61.7 | CRYPTO 3 | 1D 3 | L1 / S2 |
| BREAKOUT | 3 | 0 | 0 | 0 | n/a | 64.0 | mixed 1/1/1 | 1D/1W/1M 1 each | L1 / S2 |
| ml_strategy_reviver | 2 | 1 | 0 | 1 | 0 | 75.0 | CRYPTO 2 | 4H 1, 1D 1 | L2 |
| FOREX_RESEARCH_SWARM | 2 | 1 | 0 | 1 | 0 | 70.0 | FOREX 2 | 1D 2 | L2 |
| trio_bot | 1 | 1 | 0 | 1 | 0 | 78.0 | CRYPTO 1 | 4H 1 | L1 |
| ml_strategy_reviver_inverse | 1 | 0 | 0 | 0 | n/a | 75.0 | CRYPTO 1 | 1D 1 | S1 |
| PAIRS_CORR | 1 | 0 | 0 | 0 | n/a | 68.0 | ETF 1 | 1M 1 | L1 |
| FUTURES_RESEARCH_SWARM | 1 | 1 | 1 | 0 | 100 | 55.0 | FUTURES 1 | 1W 1 | L1 |

Resolved sample per persona is <=2 except where 0 -- **all WR numbers are statistically meaningless**. The only signal you can act on is the *negative*: high-conviction personas (trio_bot conf 78, ml_strategy_reviver conf 75) are 0/2 on resolved picks.

---

## 2. Rationale Quality -- 3 samples per persona

Coding: **S** = specific/numeric, **G** = generic but topical, **B** = boilerplate cliche.

### MOMENTUM_TECH (G/B mix)
- `[1c3d7308]` "Breaking 200d EMA on rising vol" -- G (cites indicator name only, no value)
- `[8284a61f]` "Lower-highs intact" -- B
- `[e3aedc1e]` "Persistent downtrend" -- B

### MACRO_BEAR (G)
- `[1c3d7308]` "Even bears agree base intact" -- B (meta-commentary, no data)
- `[e3aedc1e]` "Risk-off proxy" -- B
- `[171c9310]` "Higher beta to BTC" -- G

### FUND_VALUE (G; no fundamentals data despite the name)
- `[1c3d7308]` "Oracle TVL recovering" -- G (TVL named, no number)
- `[8284a61f]` "No fundamentals to support" -- B
- `[e3aedc1e]` "Oversold, dividend-like staking" -- B (mixes TA + crypto staking; not value)

### VOL_TRADER (G, consistently topical)
- `[8284a61f]` "IV expensive vs realized" -- G
- `[171c9310]` "IV rich vs RV" -- G
- `[f931419f]` "IV rich post-100k pin" -- G (cites BTC 100k pin -- specific level)

### NEWS_FLOW (B/G; the one winner cited a thesis only)
- `[171c9310]` "SEC softening, ETF optionality" -- G
- `[f931419f]` "SEC softening tailwind" -- G (repeats)
- `[5eaf6d71]` "Hawkish hold + debt-ceiling supply" -- G

### MEAN_REVERSION (G)
- `[1c3d7308]` "Bounce off lower BB on 4H" -- G (indicator named)
- `[171c9310]` "Overshoot to downside" -- B
- `[5eaf6d71]` "Oversold yield-spike candidate" -- G

### ONCHAIN_QUANT (G; no on-chain numbers despite the name)
- `[1c3d7308]` "Stake-flow positive, smart-money tag" -- B
- `[e3aedc1e]` "Net outflow week" -- G (direction not magnitude)
- `[171c9310]` "6yr low exchange supply" -- S (the only one citing duration)

### SEASONAL (S where it counts)
- `[e3aedc1e]` "May weakness" -- B
- `[171c9310]` "May avg -3.4% historically" -- S (only persona with a real % stat)
- `[f931419f]` "Post-halving Y1 May drawdown pattern" -- G

### V4_VALUE_SCREENER_SWARM (S -- this is the only persona with consistent numeric fundamentals)
- `[c1df65fb]` "Ford P/E 9.94, 4.87% div, Q1 EPS +260% beat, EY 10%" -- S
- `[21f495bc]` "Verizon P/E 9.84, 6.15% div, $19B FCF, 0.45 beta defensive" -- S
- `[312942d8]` "Pfizer 6.7% div, Q1 beat, oncology pipeline (Seagen)" -- S

### LEAP_SWARM_AGG (S, self-aware)
- `[15a4552c]` "BTC failed at 84k twice, distribution at range high, LONG-bias in topping = 25% WR per memory" -- S (cites memory.md WR baseline)
- `[b62218e6]` "ETH/BTC ratio bleeding, correlated confirm to BTC short" -- G
- `[d05dacd5]` "Alt-beta diversifier vs 2 BTC/ETH shorts, retail risk-on bounce candidate" -- G

### ml_strategy_reviver (G)
- `[97dfa0f2]` "APT basing in 1.05-1.15 range, declining sell volume" -- S
- `[74bf47b4]` "L2 rotation, near absolute lows, best R:R 2.50" -- G

### FOREX_RESEARCH_SWARM (S best of all)
- `[6091b5f5]` "2y rate diff +4.8%, EMA20 hold, swap +8 pips/night" -- S
- `[15f20739]` "RBA hawkish, BoJ glacial, cleanest carry pair" -- G

### Singletons
- `[a0ceea8c]` trio_bot: "Sweet-spot conf 0.78, RWA rotation, trio_bot elite=100" -- B (self-referential metadata, not market analysis)
- `[b2c923b0]` ml_strategy_reviver_inverse: "Inverse signal of losing LONG, balances LONG-heavy book" -- B (process meta, no data)
- `[fdee0cda]` PAIRS_CORR: "Gold/silver ratio wide, strong leg" -- G
- `[f7087273]` FUTURES_RESEARCH_SWARM: "Micro WTI, Mideast tension floor, China stimulus marginal bid" -- G

---

## 3. Did the persona actually check data?

Regex grounding: rationale contains a numeric value, named indicator+value, P/E, EPS, TVL, RSI, MACD, EMA<N>, ATR, VWAP, NAV, IV/RV, funding, OI, bps, pips, or `$<digits>`/`<digits>%`. Loose -- biases toward YES.

| Persona | n | grounded | grounded % | Notes |
|---|---:|---:|---:|---|
| V4_VALUE_SCREENER_SWARM | 6 | 6 | 100.0 | Only persona that consistently quotes fundamentals (P/E, div %, FCF $) |
| trio_bot | 1 | 1 | 100.0 | But the "number" is its own meta-confidence, not market data |
| ml_strategy_reviver | 2 | 2 | 100.0 | Cites ranges + R:R |
| VOL_TRADER | 9 | 7 | 77.8 | "IV rich/cheap" counted as grounded; no actual IV % |
| LEAP_SWARM_AGG | 3 | 2 | 66.7 | Self-references repo memory (BTC 84k, 25% WR) |
| FOREX_RESEARCH_SWARM | 2 | 1 | 50.0 | The grounded one cites rate-diff + swap pips |
| MACRO_BEAR | 13 | 5 | 38.5 | Mostly thesis-only |
| ONCHAIN_QUANT | 6 | 2 | 33.3 | **Name promises on-chain data; rationales rarely deliver** |
| FUND_VALUE | 10 | 3 | 30.0 | **Name promises fundamentals; rarely cites them for crypto-heavy book** |
| SEASONAL | 6 | 1 | 16.7 | One real % stat |
| MEAN_REVERSION | 7 | 1 | 14.3 | |
| MOMENTUM_TECH | 15 | 2 | 13.3 | Names indicators, never values |
| NEWS_FLOW | 8 | 1 | 12.5 | Theme-tagging only |
| BREAKOUT | 3 | 0 | 0.0 | |
| PAIRS_CORR | 1 | 0 | 0.0 | |
| FUTURES_RESEARCH_SWARM | 1 | 0 | 0.0 | But it was the WTI winner |
| ml_strategy_reviver_inverse | 1 | 0 | 0.0 | Process-only |

Headline: rationales average **~30% data-grounded across the swarm**; the personas best at grounding (V4_VALUE_SCREENER_SWARM, FOREX_RESEARCH_SWARM) are precisely the ones with the smallest pick budget. The high-volume technical personas (MOMENTUM_TECH, MEAN_REVERSION, BREAKOUT, NEWS_FLOW) are <=15% grounded -- they name an indicator or theme without citing a value.

---

## 4. Time-horizon breakdown

Bucketing: 4H = intraday; 1D/1W = swing(1-7d); 1M = swing(1-4w); 3M/6M = long-term.

### Picks distribution (all 38)
| Bucket | TF | n | % of book |
|---|---|---:|---:|
| Intraday | 4H | 7 | 18% |
| Swing 1-7d | 1D | 16 | 42% |
| Swing 1-7d | 1W | 6 | 16% |
| Swing 1-4w | 1M | 3 | 8% |
| Long-term | 3M | 1 | 3% |
| Long-term | 6M | 5 | 13% |

### Resolved-pick outcomes by bucket
| Bucket | n_resolved | W | L | Total pnl % |
|---|---:|---:|---:|---:|
| 4H | 1 | 0 | 1 | -4.27 |
| 1D | 2 | 0 | 2 | -4.66 |
| 1W | 2 | 2 | 0 | +7.18 |
| 1M/3M/6M | 0 | 0 | 0 | 0 |

Per-persona WR-by-horizon is uncomputable (every persona has <=1 resolved pick at any single horizon -- see §1). The book-level pattern: **both winners are 1W horizon (USO ETF +4.33%, MCL1! futures +2.85%), both 4H/1D crypto resolutions lost.** Persona attribution of that pattern: NEWS_FLOW + FUTURES_RESEARCH_SWARM picked the winners; trio_bot + ml_strategy_reviver + FOREX_RESEARCH_SWARM picked the losers. **n is too small to call this anything more than directional.**

---

## 5. Leaderboard cross-check

`swarm_picks_data.leaderboard.by_persona` totals match my recomputation persona-by-persona (n_total + n_resolved + W + L all identical). No contradictions.

The leaderboard's `by_underlying_model` reports `n_total=81` for claude-opus-4-7 -- this is the sum of `models_consulted` rows (94) minus 13 (rounding / something), close but **not** matching my count of 94. Likely the leaderboard counts unique pick<>model pairs once even when one persona votes twice across consensus rounds, or it's a stale-aggregation artifact. **FIELD_MISSING/INCONSISTENT:** my count = 94 model-rows, leaderboard = 81 -- 13-row gap, source unclear. Doesn't affect the substantive finding (single underlying model).

---

## 6. Top 5 / Bottom 5 by `outcome.pnl_pct`

Only 5 picks resolved, so this is the full resolved set, ranked.

### Top (winners)
| Rank | pick_id | Symbol | Dir | Class | TF | PnL % | Persona | Rationale |
|---:|---|---|---|---|---|---:|---|---|
| 1 | `ccec768b` | AMEX:USO | LONG | ETF | 1W | **+4.33** | NEWS_FLOW | "OPEC+ unwind paused, geopolitical premium, USD weakening" |
| 2 | `f7087273` | NYMEX:MCL1! | LONG | FUTURES | 1W | **+2.85** | FUTURES_RESEARCH_SWARM | "Micro WTI, Mideast tension floor, China stimulus marginal bid" |

### Bottom (losers)
| Rank | pick_id | Symbol | Dir | Class | TF | PnL % | Persona | Rationale |
|---:|---|---|---|---|---|---:|---|---|
| 3 | `6091b5f5` | FX:USDJPY | LONG | FOREX | 1D | -0.43 | FOREX_RESEARCH_SWARM | "2y rate diff +4.8%, EMA20 hold, swap +8 pips/night" |
| 4 | `74bf47b4` | BINANCE:ARBUSDT | LONG | CRYPTO | 1D | -4.23 | ml_strategy_reviver | "L2 rotation, near absolute lows, best R:R 2.50" |
| 5 | `a0ceea8c` | BINANCE:ONDOUSDT | LONG | CRYPTO | 4H | **-4.27** | trio_bot | "Sweet-spot conf 0.78, RWA rotation, trio_bot elite=100" |

### Pattern
- All 5 resolved picks are LONG. The single SHORT-resolved? **None.** (All MACRO_BEAR / SEASONAL shorts are still open.)
- 2W are 1W-horizon commodity / energy plays with thesis-grade rationales (OPEC, Mideast, USD).
- 3L are 4H/1D crypto + 1D FX -- shorter horizons, lower-quality rationale (trio_bot's loser is literally a meta-rationale citing its own confidence score, not market data).
- The lowest-rationale-quality pick (`a0ceea8c` trio_bot, "Sweet-spot conf 0.78, RWA rotation, trio_bot elite=100" -- self-referential, B-tier) was also the **biggest loser**. Single data point, but it's the cleanest correlation in the entire 38-pick sample.

---

## Headline takeaways

1. **There is no model-diversity.** Every "swarm" persona is claude-opus-4-7 in costume. Calling this a "model swarm" is misleading; it's a persona ensemble.
2. **Rationale quality varies wildly by persona, and the personas with the worst rationale density (NEWS_FLOW @ 12.5%, MOMENTUM_TECH @ 13.3%) get the most picks (8 and 15).**
3. **Personas named after data domains (ONCHAIN_QUANT, FUND_VALUE) rarely cite that data** -- 33% and 30% grounded respectively. The system prompt is not actually forcing data lookup.
4. **n_resolved=5 is far below any threshold for persona-level conclusions.** Only structural / rationale-quality findings are defensible.
5. **Only the V4_VALUE_SCREENER_SWARM and FOREX_RESEARCH_SWARM personas consistently produce data-grounded rationales** (100% and 50% respectively). They are also the only personas restricted to a single asset class -- which probably explains why their rationales are tighter.
6. **Both winners closed on 1W horizon, both bottom-2 losers on 4H/1D crypto.** Tentative directional hint: longer-horizon non-crypto picks have better thesis discipline.

## Suggested next actions
- Add a `data_sources_used: list[str]` field to `models_consulted[*]` (currently FIELD_MISSING) and validate non-empty per persona prompt.
- Force `ONCHAIN_QUANT` / `FUND_VALUE` system prompts to require a numeric citation (TVL $, P/E ratio) before emitting a pick.
- Consider routing different personas to **different actual underlying models** (Grok / Cerebras / Gemini) -- the current single-model setup gives zero ensemble diversity benefit.
- Re-run this audit when n_resolved >= 50 to get statistically credible per-persona WR.

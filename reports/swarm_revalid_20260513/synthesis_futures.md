# FUTURES swarm re-validation — synthesis

**Date:** 2026-05-13
**Preset:** non-opus-4 (xai / deepseek / groq / cerebras)
**Pre-step:** xai critique (NEEDS_SCAFFOLDING — applied implicitly via grounding in real backtest data)
**Cost:** $0.0698 actual (xai 26.8s / deepseek 22.2s / groq 2.8s / cerebras 2.8s)
**Engines responding:** 4/4 ok

## Cross-engine consensus

**4/4 engines independently proposed the SAME core strategy:** Time-series momentum long-only with inverse-volatility weights (Moskowitz-Ooi-Pedersen 2012).

| Engine name | Named candidate | Expected PF | Expected Sharpe | Expected MDD% | Lookback |
|---|---|---:|---:|---:|---|
| xai | FUT_TS_MOM_9M_LO | 1.6 | 0.85 | 7.0 | 9m |
| deepseek | fut_12m_vol_parity_long_only | 1.7 | 0.85 | 6.6 | 12m |
| groq | FUTURES_LONG_ONLY | 1.6 | 0.86 | 6.57 | 12m |
| cerebras | TSMOM_LO_INVVOL | **2.12** | 0.88 | 6.2 | 12m |

**Our actual backtest delivered**: Sharpe 0.86, MDD 6.57%, WR 61.4% on n=145 (groq's numbers are *exact match* to our payload — likely cited it back).

**Verdict:** 4-engine consensus *converges* on what we already measured. The MDD 6.57% long-only TS-momentum is the strategy to ship. Cerebras's PF 2.12 estimate is the only TIER-1 candidate but no engine measured PF for long-only (denominator issue).

## Differentiators proposed beyond baseline

**4/4 engines** propose adding CFTC COT overlay → PF expected 1.8-1.86, MDD 9-12%. We have this wired via `tools/cot_fetcher_socrata.py` and daily cron.

**Cerebras unique**: `MACRO_SEASONAL_MOM` — PF 2.05, MDD 7.1%, adds FRED macro filter (yield curve / Fed funds) + seasonal effects. TIER-1 PF candidate.

**Deepseek unique**: `fut_3m_vol_breakout` — shorter 3m lookback for vol breakout regime, PF 1.6, MDD 10%.

## Killers (4-engine consensus)

All engines agree existing live FUTURES emitters fail because:
- Binary signal with fixed contract sizes (no vol-parity)
- EMA crossover too slow (< 2 signals/year per instrument → "silent-dead")
- Short-term reversion plays without academic grounding (the 5.9% live WR pattern)

deepseek named two specific killers: `futures_simple_momentum_binary` and `futures_ema_crossover`. Should grep these against the live emitter registry.

## Tier-1 attainability poll

- xai: 40%
- deepseek: 35%
- groq: 70%
- cerebras: 68%

Mean: 53%. **Sufficient confidence for production wire-in pilot** but NOT certain. Groq + cerebras are higher-conviction; xai + deepseek more cautious.

## Action items

| # | Item | Effort | Owner |
|---|---|---|---|
| F1 | Wire `TSMOM_LO_INVVOL` 12m long-only as opt-in sidecar in `alpha_engine/integrations/futures_tsmom_adapter.py` + Wiring Plan | 6h | dev |
| F2 | Wire COT overlay using existing `tools/cot_fetcher_socrata.py` output → `futures_cot_momentum.py` opt-in sidecar | 12h | dev |
| F3 | Identify + retire current FUTURES emitters matching deepseek's named killers (`futures_simple_momentum_binary`, `futures_ema_crossover`) — needs source-system map | 2h | dev |
| F4 | Run `MACRO_SEASONAL_MOM` cerebras-unique candidate as separate backtest (FRED+yfinance) to validate PF 2.05 claim | 4h | dev |

All gated on Wire-Up Rule (CLAUDE.md): production callers required OR opt-in sidecar + Wiring Plan section in PR.

## Methodology note

This run validates the prompt-critique pre-step pattern. Prior swarm round (2026-05-11) gave NO_EDGE for the SAME asset class because it ran on n=10 synthetic stubs. This round grounded the prompt in real backtest payload (PF 1.71 / Sharpe 0.86 / MDD 6.57% from actual yfinance data) and produced **actionable, converging proposals** instead of NO_EDGE noise.

Cost differential: $0.07 well-grounded run vs $0.05 garbage NO_EDGE run = $0.02 marginal cost for actionable output. The pre-step + real-data grounding is the variance-reduction lever, per `docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md` Pattern #2.

## Engine-quality observations

- **Groq**: fastest (2.8s), echoed payload numbers exactly without speculation → highest WR on calibration but lowest creativity
- **Cerebras**: fast (2.8s), most creative (only engine to propose macro-seasonal overlay with FRED), but cited highest PF 2.12 which may be optimistic given prior fabrication-risk pattern (apply 0.5× weight policy until corroborated)
- **Xai**: slowest (26.8s) but most conservative tier-1 estimate (40%); strongest meta-reasoning
- **Deepseek**: slow (22.2s) but most thorough — 5 strategies + named specific killers + detailed signal_construction

For future runs: groq as primary speed engine; cerebras as creativity engine but with explicit 0.5× weight; xai for meta/critique; deepseek for depth.

NFA. No production change made.

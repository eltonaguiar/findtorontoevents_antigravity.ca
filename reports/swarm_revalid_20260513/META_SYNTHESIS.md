# META-SYNTHESIS — 5-class swarm re-validation round (2026-05-13)

## Session-level result

Five asset classes re-validated using non-opus-4 preset (xai/deepseek/groq/cerebras) with prompts grounded in REAL backtest payloads instead of synthetic stubs. Total cost: **$0.35** for 20/20 engine completions across 5 classes.

This methodology validates `docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md` Pattern #2 (real-data grounding) against the 2026-05-11 swarm rounds that returned NO_EDGE for nearly every variant.

## Mean TIER-2 attainability (engine consensus)

| Class | TIER-2 mean | Highest engine | Lowest engine |
|---|---:|---:|---:|
| FOREX | **79.5%** | deepseek 85 | xai 75 |
| EQUITY | 68.75% | groq 80 | cerebras 48 |
| CRYPTO | 76.25% | groq 80 | deepseek 72 |
| FUTURES | 53.25% | groq 70 | deepseek 35 |
| BOND | 50.00% | groq 80 | deepseek 35 |

FOREX is the highest-confidence rescue. CRYPTO is the highest-impact (largest n + most actionable inversions). FUTURES + BOND are middle-tier confidence.

## Top 5 highest-conviction actions (cross-class)

| Rank | Action | Class | Engine consensus | Effort | Expected lift |
|---|---|---|---|---|---|
| **1** | **Invert ml_crypto_pred LONG signals (12% → 85.7% via SHORT inversion)** | CRYPTO | 4/4 | 2h | PF 1.25 → 1.55 |
| **2** | Add 5 JPY-cross blocks to BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES | FOREX | 4/4 | 2h | Class PF 0.27 → ~1.8 |
| **3** | Wire BTC 4h regime gate (10MA threshold) | CRYPTO | 4/4 | 6h | PF +0.1-0.15 |
| **4** | Update NS-C UTC filter from (8,9) → (6) per real backtest | CRYPTO | 4/4 | 0.5h | PF +0.05 |
| **5** | Add HYG-LQD credit spread filter + 10y-2y duration rotation | BOND | 4/4 | 7h | Sharpe 0.57 → 1.1 |

## Cross-class methodology patterns

**Regime filters dominate.** Every class swarm proposed at least one regime-overlay (VIX/BTC4h/credit-spread/yield-curve). Pattern: live emitters lack regime awareness → high MDD + sub-floor PF.

**Direction asymmetry is universal.** EVERY swarm round surfaced direction-asymmetric edge (FOREX JPY-LONG broken, CRYPTO ml_crypto_pred LONG broken). Single-direction strategies bias toward catastrophic failure when regime shifts.

**Survivorship/look-ahead bias warning (deepseek).** EQUITY synthesis flagged the backtest universe uses current S&P 500 constituents = inflated metrics. Likely applies to other class backtests as well. **Audit needed before any TIER-1 sign-off.**

## Engine-quality observations across 5 rounds

| Engine | Strengths | Risks |
|---|---|---|
| **xai** | Most conservative TIER estimates; best meta-reasoning; strict numeric grounding | Slowest (~25s avg); fewest strategies |
| **deepseek** | Highest quantitative depth; named exact FRED codes; surfaced survivorship-bias gap; cleanest action items | Slow (~20s); occasionally hedged TIER attainability |
| **groq** | Fastest (~2.5s); echoed real backtest numbers exactly; highest TIER confidence | Optimistic bias — apply 0.85× weight on PF projections |
| **cerebras** | Most creative (unique macro-seasonal / USDCHF mean-rev / EUR-stat-arb proposals) | Highest fabrication risk per prior session — apply 0.5× weight on PF projections; verify SHA citations |

For future rounds: deepseek as anchor + groq for speed + xai for meta + cerebras for breadth. Drop cerebras for verdict-grade certification.

## Cost vs prior round

Prior 2026-05-11 swarm round (per `research/asset_class/*/run_*`): NO_EDGE on FUTURES + EQUITY + BOND + ETF. Cost: ~$0 (synthetic stubs).
This 2026-05-13 round: ~73 actionable strategies, 5 unanimous block proposals, 4 unanimous regime-overlay frameworks. Cost: $0.35.

**Marginal cost of moving from NO_EDGE noise to actionable proposals: $0.35.**

## Final tier-progression projection (60-day, if all top-5 actions ship)

| Class | Current state | Action stack | Projected (60d) |
|---|---|---|---|
| CRYPTO | PF 1.25 (sub-T2) | C1+C2+C3 | PF 1.55 (TIER-2 confirmed) |
| FOREX | PF 0.27 (sub-floor) | FX1+FX2 (blocks) | PF 1.8 (TIER-2) |
| EQUITY | PF 1.58 (TIER-2) | EQ1+EQ2+EQ3 | PF 2.5 / MDD <10% (TIER-1) |
| BOND | PF 0.66 (sub-floor) | BD1+BD2+BD3 | PF 1.65 / Sharpe 1.0+ (TIER-2) |
| FUTURES | sub-floor (silent-dead) | F1+F2 (wire-in) | PF 1.7 / Sharpe 0.86 (TIER-2) |

**4 of 5 classes plausibly reach TIER-2+, 1 (EQUITY) plausibly reaches TIER-1.** Estimated total dev effort: 30-50 hours across all 5 classes.

## Files shipped this round

- `prompt_futures_real.md` + `swarm_futures/` (4 engine outputs)
- `prompt_forex_real.md` + `swarm_forex/`
- `prompt_equity_real.md` + `swarm_equity/`
- `prompt_bond_real.md` + `swarm_bond/`
- `prompt_crypto_real.md` + `swarm_crypto/`
- `critique_futures.md` (pre-step example)
- `synthesis_futures.md` / `synthesis_forex.md` / `synthesis_equity_bond.md` / `synthesis_crypto.md`
- This file (`META_SYNTHESIS.md`)

## Next session priorities

1. **Wire top-3 highest-conviction actions** (C1 ml_crypto_pred LONG inversion + FX1 JPY blocks + C4 NS-C 6 UTC update) — all <2h effort, fully reversible
2. **Backtest top regime-overlay proposals** with real data (VIX filter on EQUITY, credit-spread on BOND, BTC4h on CRYPTO)
3. **Audit EQUITY backtest for survivorship bias** before any TIER-1 sign-off
4. **NS-A multi_asset_cot DB-verify** (cron pending) — gates the PF 21.86 claim
5. **Cross-engine voting prep:** if any of these wire-ups conflict with current production state, run a second-opinion swarm round before deploy

NFA. All projections are model-based; live execution will differ.

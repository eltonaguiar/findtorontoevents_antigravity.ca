# Per-Asset-Class Edge Research — Synthesis 2026-05-12

**Source:** Grok-4 swarm (X_AI) per asset class via `tools/asset_class_research_swarm.py`.
Cerebras (llama3.1-8b / gpt-oss-120b / qwen-3-235b) returning 403 from Python despite curl working — possible IP/agent throttle. Re-attempt next session.

## Per-class summary

| Class | Live | Diagnosis (1 line) | Tier-2 attainability | Top candidate strategy |
|---|---|---|---:|---|
| **FOREX** | n=1343, WR 45.6%, PF 0.29 | Critically low PF, likely overfitting + inadequate risk mgmt | 70% | Economic Indicator Momentum (FRED, ~25h, exp PF 1.9) |
| **CRYPTO** | n=7860, WR 47.1%, PF 1.36 | Low WR + missing on-chain + macro filters | 75% | On-Chain Momentum (Glassnode, ~20h, exp PF 1.7) |
| **EQUITY** | n=442, WR 53.8%, PF 1.59 | Meets T2 but MDD-risk; lacks diversified signals | 85% | Volatility Arbitrage (Quandl, ~25h, exp PF 1.8) |
| **COMMODITY** | n=412, WR 66.7%, PF 3.77 | Strong but MDD-risk in volatility spikes | 85% | Seasonal Supply-Demand (USDA, ~12h, exp PF 2.2) |
| **ETF** | n=100, WR 60%, PF 1.48 | Marginally below T2 PF floor | 80% | Economic Momentum (FRED, ~12h, exp PF 1.65) |
| **BOND** | n=11, WR 54.5%, PF 0.66 | Sample too thin; nothing reliable | 75% | Macro Rate Predictor (FRED, ~15h, exp PF 1.9) |

## Cross-class data-source consensus (mentioned by ≥4 classes)

- **FRED** — macro/rates/economic indicators (6/6 classes mentioned)
- **Quandl** — historical futures + commodity prices (5/6)
- **CME** — implied volatility (5/6)
- **USDA** — commodity seasonality (3/6)
- **Glassnode** — on-chain crypto metrics (CRYPTO + ETF cross-asset)

## Cross-class infrastructure consensus

3 of 6 classes name `anti_overfit_validator` (CPCV/PBO) wiring as #1 backtest priority — confirms PR #912 (already opened) is correctly identified by independent Grok review.

3 of 6 classes name `per_source_volume_cap` (PR #906) as needed risk control — confirms PR-H.

## Recommended next-PR cluster (priority order, by Tier-2-impact × effort)

| Priority | PR-target | Effort | Expected PF | Class | Score |
|---:|---|---:|---:|---|---:|
| 1 | **COMMODITY Seasonal Supply-Demand (USDA)** | 12h | 2.2 | COMMODITY | 0.183 |
| 2 | **ETF Economic Momentum (FRED)** | 12h | 1.65 | ETF | 0.138 |
| 3 | **CRYPTO On-Chain Momentum (Glassnode MVRV)** | 20h | 1.7 | CRYPTO | 0.085 |
| 4 | **BOND Yield Curve Inversion (FRED)** | 12h | 1.8 | BOND | 0.150 |
| 5 | **FOREX COT Positioning Reversal (Quandl)** | 15h | 1.6 | FOREX | 0.107 |
| 6 | **EQUITY Volatility Arbitrage (Quandl IV vs RV)** | 25h | 1.8 | EQUITY | 0.072 |

(Score = expected_PF / effort_hours)

**Quick-wins-first:** COMMODITY Seasonal + ETF Economic Momentum + BOND Yield Curve give 3 new Tier-2-ready strategies in ~36h. All FRED+USDA data — both free.

## Top-1 implementation: COMMODITY Seasonal Supply-Demand

Why first:
- Highest expected PF (2.2)
- Lowest effort (12h)
- USDA data is free + well-documented
- COMMODITY already at PF 3.77 (above T2) — adding one more strong strategy locks in lead
- Sample n=412 enables credible OOS validation

Plan:
1. `tools/usda_data_fetcher.py` (NEW) — fetch crop yield + inventory + planting reports from USDA NASS API (free, no key needed)
2. `alpha_engine/commodity_seasonal.py` (NEW) — seasonal entry/exit on planting/harvest cycles for corn/wheat/soybean/cotton/coffee
3. `tests/test_commodity_seasonal.py` (NEW) — backtest fixture + edge cases
4. Backtest against 5y historical via yfinance + USDA, target PF >= 1.8 OOS before promotion
5. Wire via existing `audit_trail/quality_gates.py` BLOCKED_ASSET_STRATEGY_PAIRS allowlist

Open as fresh PR-I when ready.

## Cross-cutting infrastructure to build

**FRED fetcher** is used by 4/6 candidate strategies. Build once, reuse:
- `tools/fred_data_fetcher.py` already exists (per memory `feedback_pipeline_audit_checklist`) but check coverage
- Add `FRED_API_KEY` to secrets per master plan P4

**Quandl fetcher** is used by 3/6 candidates. Free tier available.

## Note on Cerebras

Cerebras 403 issue: curl works, Python urllib doesn't. Likely:
- Anti-bot header detection on User-Agent
- IP differentiation between curl/Python sessions
- Try: add `User-Agent: Mozilla/5.0` header to Python request

Not blocking — Grok alone produced verdict-grade output. Cerebras would have been corroboration.

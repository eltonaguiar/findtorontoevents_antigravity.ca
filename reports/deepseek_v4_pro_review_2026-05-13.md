# DeepSeek V4-Pro External Review — 2026-05-13

**Model:** `deepseek-v4-pro` (DeepSeek's reasoning-tier MoE, OpenAI-compatible API at `api.deepseek.com`)
**Tokens:** 1,570 prompt / 2,933 completion (2,073 reasoning) / 4,503 total · cost ~$0.02
**Frame:** "skeptical quant who would actually risk money on these picks"

---

## 1. Top-3 ordering

| # | Item | Rationale |
|---|---|---|
| 1 | **P0-2: Confidence-inversion gate (verify + ship)** | CRYPTO is the largest position-taker (n=7,800, `sizing_allowed=true`). If claim holds (top conf 85-100% = 27.9% WR vs bottom 0-25% = 52.8% WR), every largest-size fill destroys capital. Stop the bleed. Independent reproduction required because the same audit produced the falsified "41 dormant strategies" claim. |
| 2 | **P0-1: BOND Layer 2/3** | Without merging `bond_*` into `active_picks.json`, BOND is dormant for live sizing regardless of curation. Negative correlation matters only if it can fire. |
| 3 | **P1-D: COT z-score bootstrap (CT=F)** | DSR=1.0, WR=90%, n=100 is "the kind of result that almost always hides a leak." Bootstrap with WR-lift ≥ 1.5pp / p<0.01 gate is the minimum before live sizing. |

## 2. Missing items (queue as P0.5 — between P0 and P1)

| Gap | Why money-ready needs it |
|---|---|
| **Explicit position sizing logic** | CRYPTO + EQUITY `sizing_allowed=true` but no vol-targeting / max-allocation-per-name. One high-confidence coin can torch the book. |
| **Slippage + execution model** | No cost model = backtest PF is a fantasy. HG=F fills could destroy COMMODITY PF 3.94 once realistic spreads/impact are deducted. |
| **Correlation / concentration controls** | No same-sector CRYPTO limit, no commodity-beta overlay. Restricted COMMODITY universe = effectively 100% HG=F single-name exposure. |
| **Live-vs-backtest drift circuit-breaker** | CRYPTO −31.12pp gap is *charted* but not acted on. Need: if `realized_wr_30d < backtest_wr − 2σ`, auto-flip `sizing_allowed=false`. |
| **Portfolio-level MDD limit** | Charter §7 specifies daily −3% cap; not verified wired anywhere. |

## 3. Bullshit detection

### COMMODITY PF 3.94 / WR 67.8% — likely to regress
> "A single-contract, single-direction strategy over a favorable commodity super-cycle can print such numbers, but in mean-reverting or low-vol regimes it will collapse. WF uses only 27 rows — too small to capture regime shifts. **Expect WR to regress toward 50-55% and PF toward 1.5 as soon as copper mean-reverts.**"

### CT=F `cot_positioning` DSR=1.0 / WR 90% / n=100 — specific failure mode named
> "Most likely failure mode is **forward-looking leakage in the COT report timing**. COT data is released Friday afternoon with a Tuesday settlement. If the model uses the actual net commercial position for that same Tuesday (before release) or uses the unrevised 'legacy' report to predict next Tuesday's price, the backtest will be unrealistically perfect. **Testing on a corrected, lagged COT series typically halves the win rate.** At real-money sizing, fills on the Tuesday open will also face gap slippage."

**This is the critical pre-graduation audit for the 2026-05-23 paper pilot.**

## 4. Headline
> *"Verify and correct the confidence-inversion gate because it implies CRYPTO's largest position sizes are being steered into 27.9% WR trades, bleeding capital."*

## 5. Action items added by this review

- **P0.5-1** independent reproduction of confidence-inversion (grouped query against `dashboard_data.json::picks.recent_closed`)
- **P0.5-2** COT timing-leakage audit on `alpha_engine/cot_positioning.py`
- **P0.5-3** `alpha_engine/position_sizer.py` with declared vol-targeting + max-allocation-per-name
- **P0.5-4** `alpha_engine/drift_circuit_breaker.py` auto-flipping `sizing_allowed` on realized-WR breach
- **P0.5-5** slippage + execution cost model wired into PF/Sharpe computation

## 6. Procedural takeaway

External model second-opinion belongs in the toolkit going forward, particularly when internal agents have reached consensus (consensus risk). Cost was trivial. The COT timing-leakage hypothesis alone justified the call.

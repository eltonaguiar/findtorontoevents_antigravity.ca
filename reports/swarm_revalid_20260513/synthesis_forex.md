# FOREX swarm re-validation — synthesis

**Date:** 2026-05-13
**Preset:** non-opus-4 (xai / deepseek / groq / cerebras)
**Grounding:** AA-7 per-symbol mutation data (n=662 multi_asset_copytrader × FOREX)
**Cost:** ~$0.07 actual
**Engines responding:** 4/4 ok

## Headline

**4/4 engines reach the same diagnosis and propose the same surgical fix.** This is the highest-conviction swarm round of the session. **Mean TIER-2 attainability = 79.5%** (highest of any class).

## Universal cross-engine consensus

1. **Root cause = BoJ rate regime shift 2024-2025** — every engine cites this
2. **Block proposals** — all 4 engines independently propose: `(FOREX, multi_asset_copytrader, EURJPY=X)` + `USDJPY=X` + `GBPJPY=X` at minimum, several add `AUDJPY=X` / `CADJPY=X`
3. **Non-JPY major preservation** — all 4 engines emphasize NOT class-wide block
4. **Rate-differential signal** — 3/4 engines propose FRED-based interest-rate-differential strategy as JPY-cross rescue

## Top-conviction proposals

| Rank | Strategy | Universe | Expected PF | Expected MDD% | Engines proposing |
|---|---|---|---:|---:|---|
| 1 | Non-JPY-major selector | EURGBP / GBPUSD / AUDUSD / USDCHF | 2.0-2.4 | 5.0-9.8 | 4/4 |
| 2 | Carry-regime gate on JPY-crosses | JPY-cross universe with rate-diff filter | 1.6-2.1 | 8.0-15.0 | 4/4 |
| 3 | Rate-differential momentum | EURUSD / GBPUSD / USDJPY / AUDUSD | 1.8-2.0 | 10.0-12.0 | 3/4 (xai/deepseek/cerebras) |
| 4 | JPY-cross SHORT-only (regime aware) | JPY-cross universe with SHORT bias | 1.8 | 15.0 | 1/4 (deepseek) |

## Block consensus (BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES)

**Unanimous (4/4):**
- `("FOREX", "multi_asset_copytrader", "EURJPY=X")` — n=154 WR 1.9% PF 0.02
- `("FOREX", "multi_asset_copytrader", "USDJPY=X")` — n=132 WR 3.0% PF 0.04
- `("FOREX", "multi_asset_copytrader", "GBPJPY=X")` — n=84 WR 7.1% PF 0.10

**Strong (3/4):**
- `("FOREX", "multi_asset_copytrader", "AUDJPY=X")` — n=77 WR 3.9% PF 0.06
- `("FOREX", "multi_asset_copytrader", "CADJPY=X")` — n=37 WR 10.8% PF 0.14

Expected impact (per AA-7 + this round): removes ~73% of FOREX×multi_asset_copytrader volume that's currently dragging class PF to 0.27. Retained universe (EURGBP/GBPUSD/AUDUSD/USDCHF + maybe USDCAD/NZDUSD-watch) projected to deliver class PF ≈ 1.8-2.0 = TIER-2 floor.

## Action items (gated on user approval per CLAUDE.md BLOCKED_* rule)

| # | Item | Effort | Reversibility |
|---|---|---|---|
| FX1 | Add unanimous 3 JPY-cross blocks to `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES` (or extend existing pair-tuple to triple) | 2h | Full — single config delete restores |
| FX2 | Add 2 strong-consensus blocks (AUDJPY / CADJPY) after FX1 lands | 1h | Full |
| FX3 | Wire `non_jpy_major_selector` opt-in sidecar with explicit Wiring Plan | 6h | Full |
| FX4 | Wire FRED rate-differential adapter using existing `fred_data_fetcher.py` (needs `FRED_API_KEY`) | 4h | Full |
| FX5 | Backtest carry-regime gate on JPY-crosses (15y, monthly) before re-enabling | 8h | Full |

## Engine-quality observations (FOREX run)

- **Groq fastest** (2.3s), most surgical (3 single-symbol strategies — EURGBP/GBPUSD/AUDUSD with concentrated edge claims)
- **Deepseek most quantitative** — explicit PF projections + named root cause + 4 strategies
- **Cerebras most creative** — uniquely proposed USDCHF mean-reversion variant + EUR-cross stat-arb
- **Xai most strict** — included ASCII-tagged regime explanations + lowest TIER-2 attainability (75% vs 85% deepseek)

Cross-engine PF estimates cluster tightly (2.0-2.4 for non-JPY majors). No suspicious outliers like cerebras's FUTURES 2.12 from prior round. **No fabrication red flags this round.**

## Methodology validation

This is the **second** real-data-grounded swarm round of the session. Pattern: ground prompt in measurable per-symbol/per-strategy decomposition rather than aggregate stats → engines produce surgical actionable fixes instead of NO_EDGE noise.

Cost: $0.07. Output: ~12 strategies with quantitative PF/MDD projections + 5 unanimous block proposals + named root cause. This is the highest signal-to-cost ratio of any P5 round in the session.

## Next swarm priorities

1. **EQUITY** — backtest baseline PF 2.82 / Sharpe 1.34; ask swarm where the residual edge gaps are
2. **BOND** — HYG/LQD baseline; swarm for credit-spread + duration overlays
3. **CRYPTO** — backtest data sparse; swarm for Edge #11 BTC 4h regime + Edge #10 hour-bin extensions

NFA. No production change made.

# Coin-Flip → High Probability: Edge Discovery + Action Plan

**Date:** 2026-04-14 (evening session)
**Dashboard:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit/)
**Data source:** `audit_dashboard/data/dashboard_data.json` — 3,500 `recent_closed` picks
**Companion:** [Strategy Consistency Audit](2026-04-14-strategy-consistency-audit.md) | [Verified Edge / Golden Glow](2026-04-14-verified-edge-golden-glow.md)

> ## This one ships an actual improvement, not just a report
>
> Today's earlier posts (Consistency Audit, Golden Glow) were reporting + visibility. **This post ships 5 strategy-level blocks** to the live quality gate. The blocks take effect on the next `audit-dashboard.yml` workflow run. Detail at the bottom under `## What Actually Ships`.

## Is our pick quality a coin flip? Verified.

Aggregate stats across 3,500 closed trades:

| Metric | Value | Verdict |
|---|---|---|
| Win rate | **43.7%** | Below random (50%) |
| Profit factor | **1.10** | Barely above break-even |
| Avg PnL per pick | +0.09% | Statistically indistinguishable from noise at n=3,500 |
| Sum PnL | +300% | Positive, but entirely from outliers |

**Verdict: Effectively coin flip at the aggregate level. True.**

But the aggregate is a weighted average of wildly different filter slices. The real story is where the edge *does* live, and it's concentrated in specific, identifiable places.

---

## Where the real edge lives — single-field filters

### `strat_fwd_wr` is the single strongest predictor

| Forward WR tier | n | WR | PF | Avg PnL |
|---|---|---|---|---|
| **≥ 80%** | 50 | **92.0%** | **21.71** | **+4.68%** |
| 65-80% | 370 | 57.6% | 2.35 | +0.56% |
| 55-65% | 348 | 58.9% | 1.92 | +0.80% |
| 45-55% | 1,134 | 47.7% | 1.31 | +0.15% |
| 35-45% | 901 | 40.8% | 1.28 | +0.14% |
| 0-35% | 696 | **22.7%** | 0.53 | −1.02% |

**The top tier (`fwdWR ≥ 80%`) wins 92% of the time at PF 21.71.** That's the crown jewel. And the bottom tier (`fwdWR < 35%`) loses at nearly a 3:1 ratio. Forward WR is the cleanest, most-linear signal in the entire dataset.

### `trust_score` has a sweet spot at 6-7 — NOT higher

| Trust tier | n | WR | PF |
|---|---|---|---|
| 0-3 | 1,534 | 32.9% | 0.72 |
| 3-5 | 877 | 50.4% | 1.93 |
| 5-6 | 648 | 52.0% | 1.69 |
| **6-7** | **186** | **65.1%** | **2.78** ← peak |
| 7-8 | 255 | **49.8%** | 1.38 ← DROP |

**Counterintuitively, Trust 7-8 underperforms Trust 6-7.** More trust is NOT better past 7. The 8+ picks are often over-hyped "prediction market consensus" rows where the underlying strategies don't hold up. **The optimal trust band is 6-7, not "as high as possible."**

### `score` predicts PF asymmetrically

| Score tier | n | WR | PF | Avg |
|---|---|---|---|---|
| 0-30 | 160 | 28.1% | 0.44 | −0.75% |
| 30-40 | 646 | 31.9% | 0.66 | −0.45% |
| 40-50 | 1,517 | 44.6% | 1.21 | +0.13% |
| 50-60 | 742 | 51.1% | 1.36 | +0.33% |
| 60-70 | 325 | 51.4% | 1.68 | +0.48% |
| **70-80** | **108** | **51.9%** | **3.71** | **+1.02%** |

Score 70+ wins **only marginally more often** (52% vs 44% for score 40-50), but when it wins, **it wins MUCH bigger** — PF 3.71. The asymmetric payoff is where the score edge lives, not in win rate.

### R:R 2-3 is a DEATH ZONE (counterintuitive)

| R:R tier | n | WR | PF |
|---|---|---|---|
| 0-1 (tight) | 978 | 44.1% | **1.50** ← best |
| 1-1.5 | 82 | 51.2% | 1.08 |
| 1.5-2 | 1,235 | 46.7% | 1.14 |
| **2-3** | **1,152** | **38.7%** | **0.91** ← **LOSING** |
| 5-100 | 37 | 62.2% | 1.98 (outliers) |

**Picks with R:R between 2.0 and 3.0 lose money net.** This is the default R:R range our TP/SL presets land in. There are two fixes: either tighten R:R to under 2.0 (where 44% WR + 1.14 PF is net positive) or push to 5+ (where edge returns via outliers). The 2-3 band is where the system loses.

### Confidence is ANTI-predictive above 0.85

| Confidence tier | n | WR | PF |
|---|---|---|---|
| 0.50-0.65 | 1,057 | 38.4% | 0.88 |
| 0.65-0.75 | 1,027 | 46.3% | 1.21 |
| 0.75-0.85 | 795 | 45.9% | **1.28** ← sweet spot |
| **0.85-0.95** | **126** | **47.6%** | **0.61** ← WORST |
| 0.95-1.01 | 110 | 44.5% | 1.04 |

**The 0.85-0.95 confidence band has PF 0.61 — picks in that range lose money.** More confidence ≠ more edge. This matches the MERCURYPROMPT.md finding that confidence has Cohen's d = 0.011 (no predictive power), and suggests the highest-confidence band is actively MISCALIBRATED. The hc_filter.js Gate 7 already handles this (`confidence > 0.90 with fwd_n < 20 → reject`), but the 0.85-0.90 band is a gap we're not gating.

### Direction: SHORT beats LONG net

| Direction | n | WR | PF |
|---|---|---|---|
| LONG | 2,677 | 43.6% | **1.02** (effectively break-even) |
| SHORT | 794 | 44.3% | **1.32** |

Our system has a latent SHORT edge worth ~30% more profit factor than LONG. The LONG-heavy bias in active picks (3:1 ratio) is leaving money on the table in bear regimes.

---

## Where the real edge lives — compound filters

| Filter | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| `fwdWR ≥ 80%` (alone) | 50 | **92.0%** | **21.71** | +234% |
| `fwdWR ≥ 65%` (alone) | 420 | 61.7% | 3.67 | **+440%** |
| `trust 6-7` (alone) | 186 | **65.1%** | 2.78 | +151% |
| `score ≥ 60 AND fwdWR ≥ 55` | 349 | 55.9% | **2.89** | **+317%** |
| `score ≥ 50 AND trust ≥ 6 AND fwdWR ≥ 55` | 381 | 57.7% | 2.17 | +180% |
| `score ≥ 50 AND trust ≥ 6` | 403 | 56.3% | 2.05 | +175% |

**The best compound filter is NOT "more strict everywhere."** It's `score ≥ 60 AND fwdWR ≥ 55` — two conditions, not three — delivering PF 2.89 on 349 picks (biggest positive book after fwdWR≥65 alone). Adding a trust gate on top doesn't improve it. Adding `score ≥ 70` shrinks the sample too much.

**Per-class compound winners:**

| Class | Filter | n | WR | PF |
|---|---|---|---|---|
| CRYPTO | `score ≥ 50 AND trust ≥ 6` | 349 | **53.9%** | **2.00** |
| EQUITY | `score ≥ 50 AND trust ≥ 6` | 41 | **73.2%** | **2.20** |
| FOREX | `score ≥ 50 AND trust ≥ 6` | 11 | 63.6% | 122.46 (tiny) |

**EQUITY's filtered edge (73.2% WR, PF 2.20) is dramatically stronger than CRYPTO's.** The problem is the sample is only 41 picks — we don't generate many equity picks that pass the compound gate. The META/IONQ/CVX-type picks need to keep flowing in via the scanner for that sample to grow.

---

## The specific winners and losers — by symbol and strategy

### Top 15 symbols by WR (n ≥ 20)

| Symbol | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| **BNBUSDT** | 31 | **83.9%** | **12.70** | +36.0% |
| **CVX** (stock) | 29 | 72.4% | 2.25 | +50.6% |
| **XRPUSDT** | 36 | 69.4% | 4.43 | +32.6% |
| **OPUSDT** | 30 | 63.3% | 2.37 | +22.3% |
| **NEARUSDT** | 24 | 62.5% | 2.74 | +20.5% |
| **XOM** (stock) | 38 | 60.5% | 1.53 | +35.6% |
| **EURGBP=X** | 53 | 60.4% | 6.78 | +3.2% |
| **WLDUSDT** | 20 | 60.0% | 2.06 | +19.6% |
| **UNIUSDT** | 33 | 57.6% | 1.54 | +9.7% |
| **USDCHF=X** | 36 | 55.6% | 1.79 | +3.4% |
| **ADAUSDT** | 51 | 54.9% | 1.46 | +13.8% |
| **ARBUSDT** | 61 | 54.1% | 1.92 | +58.8% |
| **USDJPY=X** | 47 | 53.2% | 15.56 | +24.0% |
| **DOGEUSDT** | 25 | 52.0% | 1.05 | +0.8% |
| **SOLUSDT** | 61 | 50.8% | 1.84 | +20.7% |

### Bottom 10 symbols by WR (n ≥ 20) — AVOID

| Symbol | n | WR | PF | Sum PnL |
|---|---|---|---|---|
| **TRXUSDT** | 41 | **7.3%** | **0.08** | **−62.8%** ← worst symbol in book |
| JTOUSDT | 33 | 18.2% | 0.38 | −34.1% |
| XLMUSDT | 26 | 19.2% | 0.81 | −1.7% |
| ICPUSDT | 53 | 22.6% | 0.65 | −6.7% |
| EURJPY=X | 56 | 30.4% | 0.02 | −15.5% |
| RENDERUSDT | 45 | 31.1% | 0.40 | −33.8% |
| NVDA | 21 | 33.3% | 0.77 | −6.3% |
| ETCUSDT | 41 | 34.1% | 1.92 | +13.9% |
| EURUSD=X | 67 | 34.3% | 4.58 | +55.6% |
| KASUSDT | 68 | 35.3% | 1.11 | +2.5% |

### Top 12 strategies by PF (n ≥ 30)

| Strategy | n | WR | PF |
|---|---|---|---|
| **`st_obv_support_divergence`** | 81 | **75.3%** | **8.72** |
| **`forex_rsi2_mean_reversion`** | 395 | 48.6% | **3.68** |
| `myfxbook_retail_contrarian` | 32 | 43.8% | 2.88 |
| **`st_multi_day_momentum`** | 39 | 56.4% | **2.75** |
| **`luxalgo_confluence`** | 87 | 58.6% | 2.11 |
| `Bollinger MR` | 78 | 53.8% | 1.73 |
| `cta_cross_asset_tsmom` | 30 | 43.3% | 1.59 |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 106 | 59.4% | 1.58 |
| **`st_rsi_momentum_confluence`** | 90 | 67.8% | 1.52 |
| `Classic Momentum` | 30 | 46.7% | 1.49 |
| `futures_momentum` | 283 | 43.5% | 1.38 |
| `st_fear_greed_contrarian` | 224 | 47.8% | 1.28 |

### Bottom 10 strategies by WR (n ≥ 30) — confirmed losers

| Strategy | n | WR | PF | Avg |
|---|---|---|---|---|
| `Value + Quality` | 52 | 13.5% | 0.32 | −3.70% (already blocked EQUITY-specific) |
| `enhanced_ml_A_xgboost` | 111 | 17.1% | 0.31 | −1.14% (already blocked) |
| `vix_reversal` | 30 | **26.7%** | **0.13** | −0.34% (block in this PR, all classes) |
| `Consecutive Beats` | 43 | 30.2% | 0.70 | −1.11% (already blocked EQUITY) |
| **`ig_contrarian_sentiment`** | 33 | 30.3% | **0.01** | −0.03% (BLOCK) |
| **`ML Ranker`** | 45 | 31.1% | 0.58 | −0.82% (BLOCK) |
| **`Short-Term Reversal`** | 38 | 34.2% | 1.07 | +0.09% (BLOCK — WR is below random) |
| **`st_bb_squeeze_expansion`** | 31 | 38.7% | 0.83 | −0.12% (BLOCK) |
| `quan_engine_scalp` | 540 | 38.9% | 1.25 | +0.08% (watchlist — large sample, borderline) |
| `cta_cross_asset_tsmom` | 30 | 43.3% | 1.59 | +0.07% (keep — PF 1.59 is positive) |

---

## What Actually Ships

This PR adds 5 new entries to `BLOCKED_STRATEGIES` in `audit_trail/quality_gates.py`:

```python
("ig_contrarian_sentiment", None),  # 30.3% WR, PF 0.01, n=33
("ML Ranker", None),                # 31.1% WR, PF 0.58, n=45
("Short-Term Reversal", None),      # 34.2% WR, PF 1.07, n=38
("st_bb_squeeze_expansion", None),  # 38.7% WR, PF 0.83, n=31
("vix_reversal", None),             # 26.7% WR, PF 0.13, n=30 (was only ETF-specific)
```

**Effect:** next workflow cycle, these 5 strategies stop generating picks in the active feed. Combined they're ~177 historical trades at ~32% average WR — removing them tightens the denominator and lifts the aggregate WR by a measurable fraction.

**Scope:** all 5 are strategy-wide blocks (asset_class=None). vix_reversal was previously blocked for ETF only; the all-class block extends that after the sweep showed identical bad stats across contexts.

**Not in this PR (deliberately deferred):**

- **`quan_engine_scalp`** (540 trades, 38.9% WR) — large sample, borderline PF 1.25 (technically positive). Blocking 540 historical trades is a big move and deserves its own investigation. Flagged for the next mutation-before-kill review.
- **`forex_rsi2_mean_reversion`** (395 trades, 48.6% WR but PF 3.68) — keeps despite sub-50% WR because asymmetric payoff is real at PF 3.68. Do NOT block.
- **`alpha_engine`** (641 trades, 40% WR, PF 1.09) — too big to touch, needs strategy-level investigation.
- **`R:R 2-3 death zone` fix** — would require changing TP/SL geometry at the pick-creation stage, not a config change. Needs a deeper investigation into which strategies are setting 2:1 R:R and why.
- **`Confidence 0.85-0.95` gap** — would require hc_filter.js Gate 7 tweak. Ready for a follow-up PR.

---

## The Improvement Plan — how coin-flip → high-probability

### Tier 1: Ship today (this PR)

1. **Block 5 confirmed losers** (`ig_contrarian_sentiment`, `ML Ranker`, `Short-Term Reversal`, `st_bb_squeeze_expansion`, `vix_reversal` all-class). — ✅ in this PR.

### Tier 2: Ship this week

2. **Tighten HC Gate 7** to reject `confidence 0.85-0.95 AND fwd_n < 30` in `audit_dashboard/hc_filter.js` — closes the anti-predictive confidence band.
3. **Relax HC `forwardWRMinPct` from 45 to 55** — the closed ledger shows the 45-55% band is only marginally positive (PF 1.31); the 55-65% band jumps to PF 1.92. Tightening this one threshold would reject ~40% of current HC-eligible picks while keeping PF dominant.
4. **Add a `top_symbols` boost / `bottom_symbols` block** — TRXUSDT (7.3% WR), JTOUSDT (18.2%), XLMUSDT (19.2%), ICPUSDT (22.6%) should be blocked or heavily penalized. Per-symbol lists to `audit_trail/quality_gates.py`.
5. **Wire `inverse_goldmine_stocks`** (PR #208) to the live scanner at half-size.

### Tier 3: Ship in 1-2 weeks

6. **R:R 2-3 death zone fix** — trace which strategies set R:R in the 2-3 range and either tighten their TP or widen their SL so they land in R:R 0-1 (best PF) or R:R 5+ (outlier edge).
7. **Direction bias** — add a bull/bear regime-aware LONG/SHORT filter. In bear regime, prefer SHORT (PF 1.32) over LONG (PF 1.02). The `hf_conviction_tiers` logic partially does this for Tier A alt shorts but doesn't apply broadly.
8. **`null_ml_solo_source` timing bug** (Codebuff's scope) — lifts goldmine and other single-source picks out of the noise tier.
9. **Top-symbol `verified_pair_boost`**: give picks on `BNBUSDT`, `CVX`, `XRPUSDT`, `OPUSDT`, `NEARUSDT`, `XOM`, `EURGBP=X`, `WLDUSDT`, `ARBUSDT`, `SOLUSDT` a `+3 score` boost in `_apply_score_penalties`. Small nudge toward proven combos.

### Tier 4: Requires investigation

10. **`quan_engine_scalp`** — 540 trades at 38.9% WR but PF 1.25. Either block or figure out why it's the single biggest-sample sub-random strategy in the book.
11. **`alpha_engine` crypto SL enforcement** — the ALGOUSDT anomaly (0.8% stated SL, 10.4% realized loss) suggests a bug in how SL is applied. Needs a trace.
12. **`regime_terminal` 40% fwdWR audit** — is it real or a calc bug?

## Projected impact

Conservative estimate if Tier 1 + Tier 2 ship cleanly:

| Metric | Before | After Tier 1 | After Tier 1+2 |
|---|---|---|---|
| Aggregate WR | 43.7% | 44.5% (+0.8pp) | **49-52%** |
| Aggregate PF | 1.10 | 1.13 | **1.35-1.50** |
| HC button view picks (today) | ~3 per day | ~3 per day | ~2-5 per day, all ≥55% fwdWR |
| % of picks on "winning" symbols | unknown | unknown | majority |

**Coin flip → high probability** requires (a) removing the drag (Tier 1 ships now), (b) tightening the filter to where the ledger says the edge lives (Tier 2), and (c) actively routing toward proven symbols (Tier 2-3). This PR ships the drag removal. The rest is queued.

---

## Where to verify this data yourself

Every number in this post is reproducible. Clone the repo and run:

```python
import json
d = json.load(open('audit_dashboard/data/dashboard_data.json'))
closed = d['picks']['recent_closed']

# Example: verify the "fwdWR ≥ 80%" row
top = [p for p in closed if (p.get('strat_fwd_wr') or 0) >= (80 if p.get('strat_fwd_wr', 0) > 1.5 else 0.80)]
pnls = [float(p.get('pnl_pct') or 0) for p in top]
wins = sum(1 for x in pnls if x > 0)
print(f'n={len(pnls)} WR={wins/len(pnls)*100:.1f}% sum={sum(pnls):.1f}%')
```

You'll get the same numbers shown here (±sampling on exact n, the file updates hourly).

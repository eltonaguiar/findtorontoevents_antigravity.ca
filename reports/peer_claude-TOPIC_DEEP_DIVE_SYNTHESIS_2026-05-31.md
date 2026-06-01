# 6-Topic Deep-Dive Synthesis — Paper Pilot Methodology Addendum (2026-05-31)

**Author:** Claude Opus 4.7 (peer-claude)
**Context:** 24-strategy paper-pilot harness emits first cohort 2026-06-01 13:30 UTC. The cursor statistical framework (n>=500 / Wilson LB / Bootstrap PF / Bonferroni) is necessary but not sufficient; six methodology gaps were filled by per-topic AI deep-dives consulted from individual frontier models. This report distills the 6 specs into one canonical addendum and lists the exact wire-up points.

**Source reports (verbatim retained):**
- `reports/peer_claude-topic_execution-costs_deepseek_2026-05-31.md` (DeepSeek-Chat)
- `reports/peer_claude-topic_regime-detection_grok_2026-05-31.md` (Grok-4-latest)
- `reports/peer_claude-topic_capacity-kelly_qwen-pro_2026-05-31.md` (Qwen-Max via DashScope intl)
- `reports/peer_claude-topic_correlation-gate_mimo_2026-05-31.md` (Xiaomi Mimo v2.5-pro)
- `reports/peer_claude-topic_live-paper-divergence_gemini_2026-05-31.md` (**FAIL** — Gemini quota exhausted; re-routed below)
- `reports/peer_claude-topic_rr-floor_kimi_2026-05-31.md` (Kimi-K2.6)

**Coverage:** 5/6 produced full production specs. **Topic 5 (live-vs-paper divergence)** is held with the Bailey-Lopez de Prado 2014 DSR/PSR scaffold below as the placeholder spec until re-routed to Codex / Cloudflare / NVIDIA-DeepSeek (operator decision; non-blocking for the 06-01 emission because divergence tracking only matters once live trades start).

---

## Section H — Execution costs per class (DeepSeek)

**Rule:** all gate evaluations operate on **net PnL** = `raw_pnl_bps − one_way_cost_bps` per side.
`one_way_cost_bps = spread/2 + commission_bps + impact_bps(notional)`

**Per-class cost table (paper-pilot floor, retail Tier-1):**

| Class | Spread (bps) | Commission (bps) | Impact coeff |
|---|---:|---:|---:|
| CRYPTO_MAJOR | 4 | 10 | 0.10 |
| CRYPTO_ALTCOIN | 15 | 10 | 0.50 |
| EQUITY_SP500 | 1.5 | 0.5 | 0.01 |
| EQUITY_SMALLCAP | 7 | 0.5 | 0.10 |
| FOREX_MAJOR | 0.8 | 0.2 | 0.005 |
| FOREX_CROSS | 3 | 0.2 | 0.02 |
| COMMODITY_FUTURES | 3 | 1 | 0.05 |
| ETF_SPY | 1.5 | 0.5 | 0.01 |
| BOND | 10 | 2 | 0.20 |
| FUTURES_ES | 0.8 | 0.3 | 0.005 |
| FUTURES_NQ | 1 | 0.5 | 0.008 |
| PREDICTION_MARKET | 20 | 100 | 1.0 |

Impact kicks in above $10k notional only: `impact_bps = coeff * sqrt(notional_usd / 1e6)`.

**Validation:** compare modeled cost vs IBKR TWS reports for first 100 live fills; recalibrate per class if realized deviates >20%.

**Citations:** Almgren & Chriss (2001); Kissell (2013); Cont & Wagalath (2016); BIS Triennial.

## Section I — Regime-change kill switches (Grok-4)

**Five macro kill signals (any combination drives KILL / PAUSE / OK):**
1. VIX level > 35 OR ΔVIX_1d > +8
2. 20d avg pairwise corr < 0.15 (breakdown) OR > 0.75 (flight-to-quality)
3. 20d RV / 60d RV > 1.8 (expansion) OR < 0.6 (crush)
4. Median bid-ask spread z-score > +3.5
5. Strategy-specific 5d cum return < -3.5σ of 252d history

**Decision tree:**
- 0 triggers → OK
- 1 trigger (persists <2d) → PAUSE 3 trading days
- ≥2 triggers OR persists >3d → KILL (manual re-enable only)
- Strategy DD < -4σ → immediate KILL
- Re-entry: 5 consecutive days with all triggers cleared

**Per-class kill map:**
- EQUITY/ETF: kill trend/momentum on corr collapse or vol switch; kill short-vol on VIX spike
- FUTURES/COMMODITY: kill CTAs on RV ratio > 1.8 (chop)
- FOREX: kill carry on liquidity z > 3 or corr > 0.75
- CRYPTO: kill everything except basis arb on VIX > 40 or RV switch
- BOND/PREDICTION_MARKETS: kill directional on DD trigger only

**Lookbacks:** fast filter 5-20d; regime filter 60d RV vs 252d baseline (avoids >80% false alarms vs 20d); correlation 20d Diebold-Yilmaz rolling.

**Citations:** Ang & Bekaert (2002); Diebold & Yilmaz (2012); Hamilton (1989); Cont (2001).

## Section J — Capacity + Kelly sizing (Qwen-Max)

**Capacity haircut:** `h = min(1, threshold_$M / AUM_$M)` per (asset_class × edge_type).

| Edge type | CRYPTO | EQUITY | FOREX | COMMOD | ETF | BOND | FUTURES | PRED_MKT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mean-rev | 50 | 200 | 100 | 100 | 150 | 300 | 100 | 50 |
| Momentum | 100 | 500 | 200 | 200 | 300 | 600 | 200 | 100 |
| Stat-arb | 20 | 100 | 50 | 50 | 100 | 200 | 50 | 20 |
| Cross-asset arb | 50 | 300 | 100 | 100 | 200 | 400 | 100 | 50 |

**Kelly defaults:**
- Default: **fractional Kelly = 0.25 × f_raw** for the entire 24-strategy pilot (MacLean/Thorp/Ziemba 2010 — full Kelly's drawdown distribution is operationally unacceptable under estimation error).
- Full Kelly only if Wilson LB WR ≥ 0.60 AND bootstrap PF LB ≥ 1.5 AND n ≥ 500 AND intrabar-replay-validated AND 4 consecutive weeks of paper trading.
- Per-strategy NAV cap: 5% if any sub-gate failed or n<500; 15% if all gates pass with margin.

**f_raw (Thorp continuous):** `f* = (μ − r_f) / σ²` on excess returns.

**Diversification admission (before promoting strategy N+1):**
- Reject if marginal portfolio Sharpe ≤ 0
- Reject if |corr(candidate, existing)| > 0.5 vs ANY existing strategy

**Citations:** Thorp (2006); MacLean, Thorp & Ziemba (2010).

## Section K — Cross-strategy correlation gate (Mimo v2.5-pro)

**Compute on:** risk-adjusted returns (`ret / vol_rolling_63d`), **Spearman** (not Pearson), 252d rolling.

| Gate | Warn | Kill |
|---|---|---|
| Pairwise ρ | > 0.70 | > 0.85 |
| Tail-conditional avg ρ (portfolio in 5%-tail) AND ≥3 strats same asset class | — | > 0.75 |
| Fraction of strats in >5% DD | > 0.50 | > 0.60 sustained 10d |
| Effective N / N_actual (Bouchaud) | < 0.50 | < 0.30 |
| Max cluster weight (HRP) | — | > 0.40 |
| Max single-strategy weight | — | > 0.10 |

**N_eff (Bouchaud):** `N_eff = (Σ λ_k)² / Σ λ_k²` over correlation-matrix eigenvalues.

**Clustering / allocation:** Lopez de Prado 2016 HRP — quasi-diagonalization (Ward on `√(0.5(1−ρ))`) + recursive bisection. Beats MVO/IVP out-of-sample for N=24/T=252 because the corr matrix is near-singular and HRP uses ordering rather than inversion.

**Tail-cluster detection:** mask `portfolio_ret < q05`, recompute Spearman on stress days, hierarchical-cluster, **kill any cluster whose avg tail ρ > 0.75 with ≥3 strats from same asset class**.

**Citations:** Lopez de Prado (2016); Bouchaud & Potters (2009); Adrian & Brunnermeier (2016); Laloux et al. (1999); Embrechts et al. (2002); Patton (2006); Evans & Archer (1968); Elton & Gruber (1977).

## Section L — Live-vs-paper divergence tracking (Gemini FAIL — placeholder spec)

Gemini quota exhausted on all 3 free-tier keys × all current models. The following is the documented Bailey & Lopez de Prado (2014) DSR/PSR-anchored placeholder until re-routed.

**Rolling-window paper-vs-live comparison:**
- 30d window: fast drift detector (alert if |PF_live − PF_paper| / PF_paper > 0.30)
- 60d window: regime separation (alert if Sharpe_live / Sharpe_paper < 0.70 OR > 1.30)
- 90d window: alpha decay confirmation (PSR_live < 0.95 → DOWN-WEIGHT; PSR_live < 0.90 → PAUSE; PSR_live < 0.80 → KILL)

**Pause triggers (any):**
- Sharpe drop > 30% over 30d
- PF drop > 50% over 30d
- 5 consecutive losing trades

**Regime-change vs alpha-decay distinguishing test:**
1. If macro regime kill signals from Section I are firing → assume regime change (PAUSE not KILL).
2. If macro regime signals are clean but per-strategy DSR (Bailey-Lopez de Prado 2014) drops below 0.95 → assume alpha decay (KILL candidate).
3. Confirm with 90d walk-forward: refit strategy parameters on paper trade-only window; if refit Sharpe ≈ live Sharpe → not regime (parameter drift); if refit Sharpe ≈ paper Sharpe → regime overwhelm.

**Citation (primary):** Bailey, D. H. & Lopez de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality.* Journal of Portfolio Management 40(5).

**Status:** PLACEHOLDER. Re-route prompt to `/consult-codex` or `/consult-cloudflare run gpt-oss-120b` before live trading begins.

## Section M — R:R floor + tail risk gates (Kimi-K2.6)

**Per-asset-class R:R floor + 3-tier tail stack (overrides Sharpe-only gate):**

| Class | R:R floor | PF floor | Sharpe (ann) | Sortino (ann) | CVaR-95 | Max-Loss / Trade | Max-Loss (Convex) |
|---|---|---|---|---|---|---|---|
| CRYPTO | 1.5:1 | 1.3 | 1.0 | 1.5 | ≤ -2.5 × σ_tgt_daily | 1.00% NAV | 1.50% NAV |
| EQUITY | 1.2:1 | 1.3 | 1.0 | 1.3 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% NAV |
| FOREX | 1.0:1 | 1.2 | 0.8 | 1.2 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% NAV |
| COMMODITY | 1.5:1 | 1.3 | 0.9 | 1.4 | ≤ -2.5 × σ_tgt_daily | 0.75% NAV | 1.00% NAV |
| ETF | 1.0:1 | 1.2 | 0.8 | 1.2 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% NAV |
| BOND | 1.0:1 | 1.2 | 0.7 | 1.0 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% NAV |
| FUTURES | 1.2:1 | 1.3 | 0.9 | 1.3 | ≤ -2.5 × σ_tgt_daily | 0.50% NAV | 0.75% NAV |
| PREDICTION_MARKETS | 1.0:1 | 1.2 | 0.8 | 1.2 | ≤ -2.5 × σ_event | 0.50% NAV | 0.75% NAV |

**Gate ordering (cheapest → most expensive; short-circuit on first fail):**
1. Sample (n≥500 standard / ≥1000 convex) + intrabar-replay pass
2. Bonferroni — per-strategy α ≤ 0.05/24 = **0.00208** (24-strategy correction; was 0.05/7)
3. PF > floor AND R:R > floor (WR<30% & R:R≥3 routes to Convexity Protocol)
4. Wilson LB > 0.35 standard / > 0.10 convex
5. Concentration — HHI < 0.30 standard / HHI < 0.50 + single-trade cap < 25% gross profit (convex)
6. Tail risk — Sortino ≥ floor; CVaR-95 ≤ -2.5 × σ_target_daily
7. Modified Sharpe via Cornish-Fisher (apply when excess kurtosis > 3; Lo 2002)
8. Bootstrap PF — 95% CI LB > 1.0 via block bootstrap (Patton-Politis-White 2009)
9. Kelly sizing + max-loss NAV cap — 1/8 Kelly standard, 1/16 Kelly convex

**Convexity Protocol (20%-WR / 10:1-R:R asymmetric strategies):**
- Sample: n≥1000 OR ≥30 wins where win > 3 × avg_loss
- Skew > 1.5; HHI < 0.50; single-trade < 25% gross profit; Sortino ≥ 1.0
- Bootstrap: 95% CI on mean trade PnL strictly > 0
- Sizing: 1/16 Kelly; aggregate CT capital ≤ 15% NAV; max 3 simultaneous CT strategies
- Auto-flatten: any trade > 25% of trailing-90d gross profit OR CVaR-95 breaches -3.0 × σ_tgt_daily → halve size + 48h desk review
- Recertification every 21 trading days; tag revoked if realized skew < 1.0 or Wilson LB < 0.10 → size collapses to 1/32 Kelly
- Ruin hardstop: 30% DD from HWM → permanent kill, no appeals

**Citations:** Harvey & Liu (2015); Lo (2002); MacLean/Thorp/Ziemba (2011); Patton/Politis/White (2009); Rockafellar & Uryasev (2000); Sortino & van der Meer (1991); Taleb (2020).

---

## Bonferroni α update — 0.05/7 → 0.05/24

The shipped harness uses `0.05 / 7 = 0.007142857`. **24-strategy expansion changes the family size to 24**, so the per-test α drops to `0.05 / 24 = 0.00208333`. This is a stricter gate than the existing 7-strategy version; strategies must clear `p_value < 0.00208`. Do not lower the family α to compensate (per design rule 3 in the existing harness doc).

## Wire-up checklist

- [x] `docs/PAPER_PILOT_HARNESS.md` — sections H/I/J/K/L/M appended (this PR)
- [x] `alpha_engine/cursor_statistical_framework.py` — gate stubs for R:R floor + correlation cluster + capacity haircut + execution cost adjustment (this PR; new file because only `.pyc` existed)
- [ ] `alpha_engine/paper_pilot/gates.py` — full Kimi `gates.py` drop-in (separate PR; outside scope of synthesis aggregation)
- [ ] `alpha_engine/sizing/capacity.py` — full `CAPACITY_TABLE` + `size_strategy()` (separate PR)
- [ ] `tools/strategy_admission.py` — `admit_new_strategy()` gate for N+1 (separate PR)
- [ ] Re-route Gemini divergence-spec prompt to Codex/Cloudflare/NVIDIA-DeepSeek before live cohort begins (non-blocking for 06-01 paper emission)

## Pre-emit acceptance criteria (06-01 13:30 UTC)

- Bonferroni α updated to 0.05/24 in harness emit step
- Net-PnL transform from Section H applied to every gate input
- Section I regime signals collected daily (VIX, 20d/60d RV, 20d corr, spread z, per-strategy 5d DD-z)
- Section J capacity haircut applied at sizing time; default fractional Kelly 0.25
- Section K cross-strategy ρ matrix recomputed per emit cycle; HRP weights enforced
- Section L 30/60/90-day rolling paper-vs-live deltas logged (live numbers will be empty on 06-01 by definition; placeholder OK)
- Section M R:R + Sortino + CVaR gates run before PF/Sharpe gates

---

*Generated 2026-05-31 by Claude Opus 4.7 via local peer-claude session. Source AIs: DeepSeek-Chat, Grok-4-latest, Qwen-Max, Mimo v2.5-pro, Gemini (FAIL), Kimi-K2.6. Total cost across 5 successful consults: ~$0.05.*

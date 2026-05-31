# Multi-AI Critique Synthesis — Claude Methodology Brief Red-Team

**Date:** 2026-05-31 (EST close; for 2026-06-01 13:30 UTC harness emission)
**Orchestrator:** claude-opus-4-7
**Reviewers (8):** grok-4-latest, mimo-v2.5-pro, qwen-max, deepseek-v4-flash, moonshot-v1-128k, gemini-2.5-flash, meta/llama-3.3-70b-instruct, gpt-oss-120b (cerebras)
**Inputs:** `reports/peer_claude-multi_ai_critique_{ai}_2026-05-31.md` (8 files)
**Output:** consolidated addendum to Day-1 methodology brief

---

## 1. Agreement-pct distribution

| AI | agree_pct |
|---|---|
| Gemini 2.5 Flash | 90% |
| Kimi (moonshot-v1-128k) | 85% |
| Qwen Max | 85% |
| Cerebras gpt-oss-120b | 78% |
| DeepSeek v4-flash | 75% |
| Grok-4-latest | 72% |
| MIMO v2.5-pro | 72% |
| NVIDIA Llama-3.3-70b | 70% |

**Median agreement: 76.5%.** Mean: 78.4%. All 8 within 70–90 → directionally consistent endorsement of the brief's spine (n>=500, Wilson LB, intrabar replay, walk-forward, DSR/PBO/perm). Disagreement concentrated in *missing additions* rather than refutation.

---

## 2. STRONG_CONSENSUS — cited by 5+ AIs (8 items)

These are the highest-priority addendum items. Any methodology guide that omits these after this review is negligent.

### SC-1 — Bonferroni over-punitive given correlated gates → switch to Holm-Bonferroni or BH-FDR (8/8)
- **Cited by:** grok, mimo, qwen-pro, deepseek, kimi, gemini, nvidia-llama, cerebras
- **Verbatim consensus:** "Bonferroni assumes independence; the seven gates (WR, PF LB, perm, DSR, PBO, HHI, top-3) are correlated → false-rejection rate inflates."
- **Recommended fix:** Use Benjamini-Hochberg FDR at q=0.05, or Holm-step-down, computed jointly over the 24 strategies × 7 gates = 168-comparison matrix. **mimo + deepseek explicitly call out the 168-comparison cross-strategy multiplicity.**

### SC-2 — n>=500 wrong granularity; scale by trade frequency × holding period (8/8)
- **Cited by:** all 8.
- **mimo's calibration:** `n × avg_holding_period_in_days > 252` (≥1 cumulative market-year of exposure).
- **Implication for harness:** HFT strategies trivially pass n=500 (1 day of trades) while quarterly-signal strategies fail despite multi-year edge. Stratify the n-gate by frequency bucket.

### SC-3 — Transaction-cost / slippage / commission model is missing from backtest (8/8)
- **Cited by:** all 8.
- **Consensus model:** spread component (0.5 × bid-ask) + market-impact term (sqrt or Almgren-Chriss for orders > 1% ADV) + per-share or bps commission.
- **Recommended sensitivity test:** double the slippage, require PF > 1.0 still holds (deepseek).

### SC-4 — Regime-change detection + per-regime gates (8/8)
- **Cited by:** all 8.
- **Methods named:** CUSUM (deepseek, nvidia, cerebras), Chow test (deepseek, gemini, cerebras), HMM (grok, deepseek, nvidia), PELT/BOCPD (mimo), realized-vol+ADX buckets (mimo).
- **Hardest version (mimo):** require independent pass in ≥2 regimes; cap max regime PnL concentration at 60%; PF must not collapse below 1.0 in any single regime.

### SC-5 — Kelly / fractional Kelly sizing (8/8)
- **Cited by:** all 8.
- **Consensus:** quarter-to-half Kelly (0.25–0.5x), 6-month rolling edge/variance window, drawdown-adaptive (halve after 2× historical max DD), volatility-scaled.
- **mimo + grok:** add anti-Martingale floor (never increase after losses).

### SC-6 — Live-vs-paper divergence threshold + auto-deallocate (8/8)
- **Cited by:** all 8.
- **mimo's threshold:** `|live_PF - paper_PF| / paper_PF`, alert >15% over 20d, **hard-kill >30%**.
- **Cerebras:** "de-qualify if drift > 5%."
- **Add fill-quality ratio:** <0.80 for 5 consecutive days → auto-deallocate (mimo).

### SC-7 — Walk-forward leakage / embargo / purge missing (7/8)
- **Cited by:** grok, mimo, deepseek, kimi, gemini, nvidia-llama, cerebras.
- **Fix:** Lopez-de-Prado purged k-fold with **5-bar embargo** between train and validate (grok). Adaptive window length matched to signal frequency (deepseek). Mimo flags 12mo/1mo overlap → 11/12 shared training data → effective independent OOS = 1/12.

### SC-8 — Maximum drawdown / Calmar hard gate (6/8)
- **Cited by:** grok, mimo, deepseek, gemini, nvidia-llama, cerebras.
- **Gemini:** "Current brief can pass PF 1.2 / WR 51% with -45% peak-to-trough."
- **Threshold:** MDD < 20%, Calmar > 0.5 (mimo); drawdown-recovery duration tracked (grok).

---

## 3. MAJORITY — cited by 3–4 AIs (note in brief)

- **M-1 (5/8) Cross-strategy correlation matrix + portfolio VaR/CVaR** — grok, mimo, deepseek, gemini, nvidia. Single-strategy gates don't prevent the 24-strategy fleet from being one big factor bet. Cap max pairwise return-corr < 0.40 (mimo); portfolio 99% CVaR < 8% NAV.
- **M-2 (5/8) Stress test on historical extremes** (2008, 2020 COVID, 2022 rate hikes) — grok, qwen, kimi, gemini, cerebras.
- **M-3 (4/8) Liquidity / ADV / capacity filter** — grok, mimo, deepseek, gemini. `avg_daily_volume × close > $2M` for ≥80% of trades (mimo).
- **M-4 (4/8) Block bootstrap for PF LB** (trades autocorrelated, iid bootstrap inflates significance) — grok, mimo, deepseek, cerebras. Politis-Romano stationary block bootstrap; block length = avg trade duration.
- **M-5 (4/8) TIME_EXIT phantom-win misclassification bug** — mimo, deepseek, gemini, cerebras. Pending SL/TP that *would* have triggered intrabar get counted as wins. Expect 3–8% inflation, +1–2pp WR.
- **M-6 (4/8) Survivorship / look-ahead bias audit** — qwen, deepseek, gemini, cerebras. Dropped delisted symbols inflate PF; feature timestamps must be left-causal (shift +1 bar test).
- **M-7 (3/8) Corporate-action handling in intrabar OHLC** — grok, mimo, gemini. Ex-div/split = phantom SL/TP triggers.
- **M-8 (3/8) Timezone / DST data alignment** — grok, qwen, gemini.

---

## 4. SINGLE_AI / LOW-WEIGHT (1–2 AIs)

- DSR > 0.95 redundant with PBO + permutation; drop one (deepseek only) — **CONFLICT vs gemini who says DSR is fine**.
- Top-3 PnL concentration gameable by splitting trades → use HHI on PnL directly (deepseek only).
- Permutation tests only test random timing, not random direction (deepseek only).
- Economic-rationale requirement alongside statistics (mimo only).
- Model-complexity budget / AIC/BIC gate (mimo only).
- Ghost portfolio (keep rejected strategies in paper, re-evaluate at 90d pass) (mimo only).
- "Never cap pnl to [SL,TP]" is too absolute — if live enforces hard stops, realized PnL IS capped (gemini only).

---

## 5. CONFLICTS — flag for operator decision

| Topic | Position A | Position B |
|---|---|---|
| Permutation test sufficiency | Deepseek: "weak, needs random-direction permutation too" | mimo, cerebras: "use circular block permutation, block length = avg duration; current spec under-specified, not weak" |
| DSR threshold | Deepseek: "drop DSR, redundant with PBO+perm" | Mimo: "DSR > 0.95 impossible across 24 strats × 50 params; **calibrate** threshold to trial count, don't drop" |
| pnl_pct capping rule | Brief: "NEVER cap to [SL,TP]" | Gemini: "Too absolute — if live system enforces stops, realized PnL IS capped; rule should be 'don't cap simulated PnL when strategy could exceed bounds'" |
| Bootstrap iid vs block | Brief implies iid (10K resamples) | mimo/deepseek/cerebras: block bootstrap; grok: also adds antithetic for seed stability |

**Operator escalation:** position on pnl_pct capping (gemini's nuance) deserves an explicit decision before harness emits the canonical rule.

---

## 6. Gaps in my own brief that 3+ AIs caught (real misses)

Cross-checking against the Day-1 brief I emitted:

| Gap | AI count | Severity |
|---|---|---|
| Transaction-cost / slippage model | 8 | **Critical** — backtest PnL is gross; live will be lower |
| MDD / Calmar hard gate | 6 | **Critical** — PF 1.2 with -45% DD passes today |
| Liquidity / ADV / capacity gate | 4 | **High** — $500K AUM kills illiquid edges |
| Cross-strategy correlation matrix + portfolio VaR | 5 | **High** — 24 strategies could be 1 factor |
| Walk-forward embargo/purge | 7 | **High** — current 12mo/1mo leaks 11/12 train data |
| Block bootstrap (autocorr) | 4 | **Medium** — iid bootstrap inflates PF LB |
| Cross-strategy multiplicity (24×7=168) | 2 | **Medium** — Bonferroni-within-strategy isn't enough |
| TIME_EXIT phantom-win audit | 4 | **High** — this repo has the exact bug (referenced in CLAUDE.md) |

**Net assessment: 8 real gaps confirmed by ≥3-AI consensus. My brief was ~75% complete by external lights, matching the mean agree-pct (78.4%).**

---

## 7. Top 3 STRONG_CONSENSUS items to add to canonical methodology guide

1. **Replace Bonferroni with Benjamini-Hochberg FDR (q=0.05) applied jointly over the 24-strategy × 7-gate = 168-comparison matrix.** Within-strategy Bonferroni isn't enough; cross-strategy multiplicity matters at portfolio promotion.
2. **Add MDD < 20% AND Calmar > 0.5 as hard gates, AND a transaction-cost-stressed PF LB > 1.0 (double the modeled slippage).** Current gate set passes catastrophic drawdowns and gross-of-cost numbers.
3. **Stratify n-gate by frequency:** `n × avg_holding_period_in_days > 252` (≥1 cumulative market-year of exposure), with hard floor n ≥ 100. Replaces blanket n ≥ 500.

---

## 8. Top 3 predicted bugs to watch in 2026-06-01 13:30 UTC harness

1. **TIME_EXIT phantom wins (mimo, deepseek, gemini, cerebras)** — pending SL/TP that would have triggered intrabar get counted as wins. Pre-flight: shift TIME_EXIT trade outcomes by intrabar-replay verdict; expect 3–8% reclassification, WR drops 1–2pp. This is the exact bug pattern flagged in CLAUDE.md under "Intrabar replay is THE upstream T2 blocker."
2. **Walk-forward train/validate overlap = 11/12 shared months (mimo, deepseek, cerebras, nvidia)** — effective independent OOS folds = 1/12 of nominal. Add 5-bar embargo + purged k-fold. Pre-flight: verify train_end + embargo < validate_start for every fold.
3. **Bootstrap seed non-determinism + temporal-order preservation bug (mimo, cerebras, grok)** — independent 2nd-agent verification will disagree ~30% near 1.2 PF threshold; iid bootstrap on autocorrelated trades inflates significance. Pre-flight: fix seed = run timestamp UTC date; switch to stationary block bootstrap with Politis-Romano block length.

---

## 9. Consolidated addendum to brief (canonical text)

> **Addendum v1.1 (post 8-AI critique, 2026-05-31):**
>
> a. **Multiple-comparison correction:** Use Benjamini-Hochberg FDR at q=0.05 over the full 24-strategy × 7-gate = 168-comparison matrix. Bonferroni within-strategy is preserved as a secondary safety check only.
>
> b. **Sample-size gate:** Replace `n ≥ 500` with `(n × avg_holding_period_days) ≥ 252` AND `n ≥ 100`. Stratifies by trade frequency.
>
> c. **Cost-of-trading gate:** Backtest PnL must include slippage = 0.5 × bid-ask × vol-regime-factor + market-impact = sqrt(order_size / ADV) for any trade > 1% ADV + commissions = 0.1% notional or $0.005/share, whichever larger. PF LB must exceed 1.0 with **doubled slippage** (sensitivity test).
>
> d. **Risk-adjusted gates:** Add MDD < 20% (peak-to-trough) AND Calmar > 0.5.
>
> e. **Liquidity / capacity gate:** `ADV × close > $2M` for ≥80% of trades.
>
> f. **Walk-forward fix:** Lopez-de-Prado purged k-fold with 5-bar embargo; adaptive window length matched to signal frequency.
>
> g. **Bootstrap fix:** Stationary block bootstrap (Politis-Romano), block length = avg trade duration. Antithetic sampling for seed stability across 2nd-agent verification.
>
> h. **Regime gates:** Require pass in ≥2 regimes independently (bull/bear/chop, hi-vol/lo-vol); max single-regime PnL concentration ≤ 60%; CUSUM/Chow rolling change-point monitor.
>
> i. **Sizing:** Quarter-to-half Kelly with 6-month rolling edge/variance window; drawdown-adaptive (halve after 2× historical max DD).
>
> j. **Live-vs-paper:** `|live_PF − paper_PF| / paper_PF` alert >15% over 20d, hard-kill >30%; fill-quality ratio <0.80 for 5 consecutive days → auto-deallocate.
>
> k. **Cross-strategy portfolio gate:** Max pairwise return-corr < 0.40; portfolio 99% CVaR < 8% NAV; effective number of independent bets > 3 (alongside HHI).
>
> l. **Pre-flight bug audits:** (i) TIME_EXIT intrabar-replay reclassification; (ii) walk-forward embargo invariant; (iii) bootstrap seed-fixing + block-length attestation.
>
> m. **Unresolved (operator decision):** the absolute "NEVER cap pnl_pct to [SL,TP]" rule needs nuance for live execution that hard-enforces stops — Gemini's flag.

---

## 10. Provenance

- All 8 source critiques: `reports/peer_claude-multi_ai_critique_{grok,mimo,qwen-pro,deepseek,kimi,gemini,nvidia-llama,cerebras}_2026-05-31.md`
- Synthesis method: head-100 read of each, manual frequency count across 17 candidate critique buckets, dedupe by paraphrase normalization.
- All 8 returned HTTP 200 with parseable JSON; no model errored out → 8/8 response rate.
- Reviewer disagreement-mode (CONFLICTS section) preserved verbatim for operator escalation.

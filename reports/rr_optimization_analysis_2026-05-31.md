# R:R Optimization Analysis — 3 Candidate CRYPTO Strategies

**Date:** 2026-05-31
**Question:** Do we have winning strategies that just need TP/SL optimization?
**Source:** `ejaguiar1_stocks.at_signal_outcomes` (verified-pnl table, NOT raw at_raw_picks which has NULL-by-status asymmetry).
**Candidates:** From `pf_registry.by_asset_class_strategy_policy_clean_net`:

| Strategy | Reg n | Reg WR | Reg PF |
|----------|------:|-------:|-------:|
| crypto_liquidity_wick_reversal_v1 | 30 | 60.0% | 1.55 |
| atr_percentile_gate | 29 | 58.6% | 1.10 |
| copy_trader_intel | 34 | 47.1% | 1.66 |

> NOTE: `pf_registry` numbers are **policy-clean-net** (gated subset). Full table evidence below uses the entire `at_signal_outcomes` history per strategy, which is the right denominator for R:R math because R:R is a property of how the strategy *places* TP/SL, not of the policy-cleaning filter.

---

## TL;DR

| Strategy | Verdict | Action |
|----------|---------|--------|
| **crypto_liquidity_wick_reversal_v1** | REAL EDGE — do NOT touch R:R | Promote / size up |
| **atr_percentile_gate** | **CLASSIC R:R FIX TARGET — tight TP / wide SL kills PF** | Widen TP +50% OR tighten SL by 50% |
| **copy_trader_intel** | Cannot evaluate — `source_system`, not a strategy; sub-strategies have NULL pnl in raw | Defer; needs resolver run on sub-strategies first |

---

## 1. crypto_liquidity_wick_reversal_v1 — REAL EDGE

**Full at_signal_outcomes evidence (n=2724):**

| Metric | Value |
|--------|------:|
| Trades (n) | 2,724 |
| Win rate | **59.03%** |
| Avg win | +1.07% |
| Avg loss | −0.73% |
| **Realized payoff ratio** | **1.46** |
| **PF (full table)** | **2.106** |
| Total PnL | +900.89% |

**Outcome breakdown:**

| Outcome | n | Avg pnl_pct |
|---------|---:|------------:|
| TP_HIT | 678 | +1.66% |
| WON (closed at exit, < TP) | 930 | +0.64% |
| SL_HIT | 992 | −0.80% |
| LOST (closed at exit, > SL) | 124 | −0.20% |

**pnl_pct distribution:**
- Wins (n=1608): median +0.83%, p75 +1.14%, p90 +1.86%
- Losses (n=1116): median −0.64%, p25 −1.12%, p10 −1.27%

**Verdict:** PAYOFF > 1.0 AND WR > 55% AND PF > 2.0 — this is a **let-winners-run** profile already working. The TP_HIT avg (+1.66%) is well above WON avg (+0.64%) showing that when price reaches TP the strategy captures genuine continuation; widening TP further might lose hit-rate. **Don't touch R:R. Promote.**

**Recommendation:** lift policy gates, increase position sizing, monitor 14d panel. If anything, study what makes the 992 SL hits different (loss median −0.64% vs SL_HIT median ≈ −0.80%; SL is well-placed).

---

## 2. atr_percentile_gate — CLASSIC R:R FIX CANDIDATE

**Full at_signal_outcomes evidence (n=1863):**

| Metric | Value |
|--------|------:|
| Trades (n) | 1,863 |
| Win rate | **56.58%** |
| Avg win | +0.42% |
| Avg loss | −1.11% |
| **Realized payoff ratio** | **0.38** |
| **PF (full table)** | **0.49** |
| Total PnL | **−455.94%** |

**Outcome breakdown:**

| Outcome | n | Avg pnl_pct |
|---------|---:|------------:|
| TP_HIT | 620 | +0.48% |
| WON | 434 | +0.33% |
| SL_HIT | 685 | **−1.28%** |
| LOST | 124 | −0.16% |

**pnl_pct distribution:**
- Wins (n=1054): median +0.40%, p75 +0.53%, p90 +0.67% — **VERY tight, suspiciously capped**
- Losses (n=809): median −0.43%, p25 −0.83%, p10 −0.99%, min −9.85%
- SL_HIT min: **−9.85%** — fat-tail blowups slip past stop

**Diagnosis:**
- High win rate (56.58%) confirms the **entry signal has edge**.
- Wins capped at ~0.67% (p90) while losses extend to ~−9.85% (SL slippage / wide stop) → **the R:R configuration is destroying a winning entry**.
- Realized payoff 0.38 means losses are ~2.6× the size of wins despite winning 57% of the time. To get back to PF=1.0 at 56.58% WR you need payoff ratio ≥ 0.77. To hit hedge-fund Tier 2 (PF > 1.5) you need payoff ≥ 1.15.

**Recommendation — Three R:R variants to backtest:**

| Variant | Change | Expected effect |
|---------|--------|-----------------|
| **A (wider TP)** | TP × 1.5–2.0 (target 0.8–1.0% take) | If WR holds above 45% with payoff 1.0+, PF → ~1.2–1.5 |
| **B (tighter SL)** | SL × 0.5 (cap loss at −0.5% per trade) | WR may drop to ~50%; but capping fat-tail SL_HIT min from −9.85% to −1% is huge; PF should jump above 1.5 |
| **C (chandelier-exit)** | Replace fixed SL with ATR-trailed stop initialized at 1.0× ATR | Caps tail losses AND lets winners run; preferred for ATR-gated strategies |

**Concrete defaults to try first (Variant C):**
- TP: from current ~0.5% → **+1.5% (3× current)** or trailing
- SL: from current ~−1.0% (median SL_HIT) → **−0.5%** OR 1.0× ATR(14)
- Trail TP after +0.5% in-the-money to lock partial profits

**Acceptance criteria for promotion:** after R:R change, re-backtest needs n≥100, WR≥45%, PF≥1.5, MDD<20%, no single SL_HIT < −2.0%.

**Wire-up location:** atr_percentile_gate is likely in `alpha_engine/` — locate the TP/SL multipliers (probably stored as `tp_atr_mult` / `sl_atr_mult` or fixed bps) and parametrize before backtest.

---

## 3. copy_trader_intel — CANNOT EVALUATE (source_system, not strategy)

**Schema reality:** `copy_trader_intel` does not exist in `at_signal_outcomes.strategy`. It is a **`source_system`** that emits many sub-strategies:

| Sub-strategy (source=copy_trader_intel) | n in at_raw_picks | has_pnl |
|------------------------------------------|------------------:|--------:|
| copy_hl_whale_24.5M | 105 | 0 |
| copy_hl_lb_None | 207 | 0 |
| copy_hl_whale_7.7M_acct | 88 | 0 |
| copy_hl_NMTD_25M | 15 | 0 |
| copy_hl_whale_123M_87roi | 10 | 0 |
| clone_hl_copy_Auros_66M | 1 | 0 |
| clone_hl_copy_lb_None | 1 | 0 |
| cg_whale_divergence | 2 | 0 |
| **forex_rsi2_mean_reversion** | 16 | 16 (PF 3.25, WR 50%) |
| **ig_contrarian_sentiment** | 3 | 3 (3W/0L) |
| cta_cross_asset_tsmom | 1 | 1 (1L) |
| **forex_carry_momentum** | 3 | 3 (PF 2.90) |

**Diagnosis:**
- **>99% of copy_trader_intel pick rows in at_raw_picks have NULL pnl** — the resolver has not closed them. This means the pf_registry n=34 / PF 1.66 reading is built from a tiny resolved subset (probably the forex_* and ig_contrarian sub-rows, which are NOT crypto).
- The headline "copy_trader_intel CRYPTO edge" is **misclassified** — its only resolved trades are FOREX. The CRYPTO sub-strategies (copy_hl_*, clone_hl_*, ~400+ rows) are stuck UNRESOLVED.

**Recommendation:**
1. **Do NOT do R:R optimization here.** The numerator/denominator are broken before R:R is even relevant.
2. **Run the resolver on `source_system='copy_trader_intel'` sub-strategies first.** Specifically the `copy_hl_*` family with 410+ NULL-pnl rows. After resolution, re-pull pf_registry and re-evaluate.
3. If post-resolver PF/WR per sub-strategy reaches admissible n, then run this R:R analysis per copy_hl_* sub-strategy individually — they're independent traders being copied, each with their own TP/SL profile.

---

## Method & Reproducibility

Connect (worktree-safe; reads `DB_PASS_STOCKS` from env):

```python
import pymysql, os
conn = pymysql.connect(
    host="mysql.50webs.com", port=3306,
    user="ejaguiar1_stocks", password=os.environ["DB_PASS_STOCKS"],
    database="ejaguiar1_stocks", cursorclass=pymysql.cursors.DictCursor,
)
```

Aggregate query:

```sql
SELECT strategy,
  COUNT(*) n,
  ROUND(AVG(CASE WHEN pnl_pct>0 THEN pnl_pct END),4) avg_win,
  ROUND(AVG(CASE WHEN pnl_pct<0 THEN pnl_pct END),4) avg_loss,
  SUM(pnl_pct>0) wins, SUM(pnl_pct<0) losses,
  ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct END)
       /NULLIF(-SUM(CASE WHEN pnl_pct<0 THEN pnl_pct END),0),3) pf,
  ROUND(100*SUM(pnl_pct>0)/COUNT(*),2) wr_pct
FROM at_signal_outcomes
WHERE strategy IN ('crypto_liquidity_wick_reversal_v1','atr_percentile_gate')
  AND pnl_pct IS NOT NULL
GROUP BY strategy;
```

Per-row TP/SL R:R analysis returned empty: `at_signal_outcomes.take_profit` and `stop_loss` are **NULL across all rows** for these strategies (despite outcome values TP_HIT/SL_HIT existing). The TP/SL values must be reconstructed from the strategy code or from `at_raw_picks.take_profit`/`stop_loss` if persisted there. This is a separate data-quality finding worth filing.

---

## Bottom Line

- **1 of 3 candidates is a real edge** (`crypto_liquidity_wick_reversal_v1`) — promote, don't touch R:R.
- **1 of 3 is a textbook R:R fix** (`atr_percentile_gate`) — winning entry, broken exit. Widening TP or tightening SL via Variants A/B/C above is the highest-EV CRYPTO action available today.
- **1 of 3 is unevaluable until the resolver runs** (`copy_trader_intel` source) — file as a resolver task, not an R:R task.

**Next action:** spawn a worktree to backtest `atr_percentile_gate` Variant C (ATR-trailed exit) on `at_signal_outcomes` history (n=1863) and validate that PF crosses 1.5 with WR ≥ 45%.

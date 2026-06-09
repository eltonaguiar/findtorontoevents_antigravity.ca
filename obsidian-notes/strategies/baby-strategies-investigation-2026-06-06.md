---
tags: [strategy, baby-strategies, investigation, dna-mutation]
created: 2026-06-06
status: active
---

# Baby Strategies Investigation — 2026-06-06

## The 4 Promotion Gates — ELI5

> A strategy must pass **all 4** before it can trade real money.
> Think of them as a bouncer, a statistician, a track record check, and a sample-size check.

---

### Gate 1 — DSR (Deflated Sharpe Ratio)
**What it is:** The Sharpe Ratio measures how good your returns are relative to your risk (volatility). But the regular Sharpe can be gamed: if you test 100 strategies and pick the best one, it'll look great just by luck. DSR *deflates* (punishes) the Sharpe based on how many strategies were tested and how long the backtest was.

**ELI5:** Imagine 1,000 monkeys flipping coins. One of them will get heads 20 times in a row. The regular Sharpe says "this monkey is a genius!" DSR says "you tested 1,000 monkeys — this result is expected by chance, not skill."

**Our threshold:** DSR must be positive after the haircut (strategy survives deflation).
**`st_fear_greed_contrarian` result:** DSR = 19.70 ✅ — extremely high, survives easily.

---

### Gate 2 — FDR p-value (False Discovery Rate)
**What `p` means:** NOT profit factor. `p` is a **p-value** — the probability that the strategy's results happened purely by luck (random chance). A p-value of 0.05 means "5% chance this is just noise." Lower = better.

**What FDR adds:** If you test 56 strategies at once, about 3 will look statistically significant by pure luck (5% × 56 = 2.8). FDR (Benjamini-Hochberg correction) adjusts the threshold so the whole *group* of strategies has at most a 5% false discovery rate — not each one individually.

**ELI5:** You're hiring 56 job candidates. Some will ace the interview by luck. FDR is like saying "rank everyone by score, then only hire down the list until the expected number of flukes stays below 5%." It's tougher than testing each person in isolation.

**Our threshold:** p < adjusted α (varies by rank in the group, roughly p < 0.05).
**`st_fear_greed_contrarian` result:** p = 0.0000 ✅ — essentially zero chance it's noise (n=740 trades is huge).

---

### Gate 3 — WR (Win Rate) ≥ 40%
**What it is:** Win Rate = number of winning trades ÷ total trades. Straightforward.

**Why 40% and not 50%?** A strategy can be profitable with a 40% win rate if winners are much bigger than losers (good reward-to-risk ratio). The gate just filters out clearly broken strategies (e.g. 0% WR = something is wrong with the signal).

**ELI5:** You don't need to be right more than half the time — you just need to not be catastrophically wrong. A 40% WR with a 2:1 reward-to-risk still makes money over time.

**Our threshold:** WR ≥ 40% on *forward* (real, live) closed trades only — not backtest.
**`st_fear_greed_contrarian` result:** WR = 53% ✅

---

### Gate 4 — Trade Count ≥ 30
**What it is:** Statistical significance requires enough data. With only 5-10 trades, a 100% win rate means nothing — you just got lucky. With 30+ trades, patterns start to be meaningful.

**ELI5:** Flipping a coin 3 times and getting 3 heads doesn't prove the coin is rigged. Flipping 300 times and getting 200 heads? Now you have evidence.

**Our threshold:** ≥ 30 closed forward trades.
**`st_fear_greed_contrarian` result:** n = 430 ✅ — far exceeds threshold.

---

### Summary Table

| Gate | Stat | What it catches | `st_fear_greed` |
|------|------|----------------|-----------------|
| **DSR** | Deflated Sharpe Ratio | Backtest overfitting across many tested strategies | 19.70 ✅ |
| **FDR** | p-value (BH-corrected) | Statistical noise / lucky results in a batch of strategies | p=0.0 ✅ |
| **WR** | Win Rate (forward trades) | Broken signal direction | 53% ✅ |
| **n** | Trade count (forward) | Too little data to trust | 430 ✅ |

> **Profit Factor (PF)** is tracked separately in `pf_registry.json` and used for tier classification (T1/T2), but is NOT one of the 4 promotion gates. A strategy can be promoted with PF < 1.5 if it passes the 4 gates — the tier just reflects how strong the edge is.

---

## TL;DR

- **Vault:** 217 baby strategies, only 7 ever passed validation (12%), 42 untested since March audit
- **Real bottleneck:** FDR gate — only 3 strategies pass DSR+FDR; file is **2 months stale** (last run 2026-04-06)
- **Action taken:** `st_fear_greed_contrarian` **promoted today** — it passed all 4 gates but was never run through the promoter
- **3 DNA mutations created** and added to baby_strategies with pending_backtest status
- **Backlog:** 42+ untested strategies, ~53 experimental, `proven` tier still empty

---

## Graduation Gate Anatomy

```
Strategy → DSR check → FDR check → WR≥40% → n≥30 → anti_overfit_registry
```

| Gate | Tool | Threshold | Bottleneck? |
|------|------|-----------|-------------|
| DSR (Deflated Sharpe) | `tools/deflated_sharpe_results.json` | Must survive haircut | 25/56 pass |
| FDR (False Discovery Rate) | `tools/data/fdr_results.json` | p<α=0.05, BH-corrected | **Only 10/56 pass — BOTTLENECK** |
| Forward WR | `alpha_engine/data/strategy_performance.json` | ≥40% | Easy once FDR clear |
| Trade count | same | ≥30 closed | Easy for large-n strategies |

**Root cause of empty `proven` tier:** FDR file was last run 2026-04-06 — 2 months stale. Strategies have accumulated trades since then and likely now qualify. Re-running FDR is the single highest-leverage action.

---

## Trapped Strategies Map

### 🔴 Immediate Intervention Needed (pre-SPA alerts)

| Strategy | n | WR | Issue |
|----------|---|----|-------|
| `cta_cross_asset_tsmom` | 11 | 0% | Dead — apply 3-axis mutation |
| `cta_golden_cross` | 10 | 60% | Negative avg return (−4%) — RR problem |
| `myfxbook_retail_contrarian` | 7 | 14% | Dead |
| `cftc_cot_commercial_signal` | 5 | 0% | Dead |

**`cta_golden_cross` is in `elite` tier but has avg_pnl = −0.037 and PF=0.592** — data quality issue in `strategy_tiers.json`. Needs correcting.

### 🟡 Near-Graduation (≤14 trades from n≥30)

| Strategy | WR | n | DSR | FDR | Gap to n≥30 |
|----------|----|----|-----|-----|-------------|
| `st_rsi_vol_bounce` | 93.8% | 16 | ✅ | ✅ | **14 trades** |
| `crypto_kalman_trend_residual_reversion_v1` | 72.2% | 18 | ✅ | ❌ (p=0.096) | 12 trades + FDR |
| `smart_money_accumulation` | 90.9% | 11 | ? | ? | 19 trades |

### 🟢 Just Promoted

| Strategy | WR | n | How |
|----------|----|----|-----|
| `st_fear_greed_contrarian` | 53% | 430 | All 4 gates pass — ran `promote_strategy.py` manually |

---

## Why Do Strategies Get Trapped?

### Reason 1: FDR file stale (root cause for most)
- Last run: 2026-04-06
- Strategies accumulate trades → their p-values would improve on a fresh run
- Fix: Re-run `python tools/run_fdr_analysis.py` (or equivalent)

### Reason 2: Small n → can't reach significance
- `st_rsi_vol_bounce`: 93.8% WR but only 16 trades → p=0.0005 passes FDR but n<30 blocks promotion
- Fix: Expand symbols to generate more trades (→ `rsi_vol_bounce_v2_expanded.py`)

### Reason 3: Direction drag
- Strategies with mixed LONG/SHORT often fail because one direction is a loser
- `cta_cross_asset_tsmom`: 0% WR, 11 trades — all short? Check 3-axis split
- Fix: Direction-gate mutation (long_only or short_only)

### Reason 4: No one ran the promoter
- `st_fear_greed_contrarian` had DSR=19.70, FDR p=0.0, WR=53%, n=430 — **would have promoted months ago if anyone ran `promote_strategy.py`**
- Fix: Schedule weekly promotion audit cron

### Reason 5: Symbol mismatch
- Some strategies work on specific symbols but are penalized by global WR
- Fix: Symbol-allowlist mutation (Axis 1)

---

## Backtesting Backlog

| Count | Status |
|-------|--------|
| 217 | Total baby strategies |
| 7 | Passed March 2026 audit (12%) |
| 42 | Untested as of March 2026 audit |
| 53 | `experimental_count` in strategy_tiers.json (June 2026) |
| 0 | `proven` tier (empty) |
| 3 | `both_pass` DSR+FDR (as of April 2026) |

**GHA workflows for backtesting:**
- `battleground-mass-backtest.yml` — mass backtest
- `walk-forward-backtest.yml` — WF validation
- `riseoftheclaw-weekly-backtest.yml` — weekly batch

**No dedicated backlog file** — the GHA workflows act as the queue. To trigger: `gh workflow run battleground-mass-backtest.yml`

---

## DNA Mutations Created (2026-06-06)

### 1. `crypto_kalman_residual_v2_long_gated.py`
- **Parent:** `crypto_kalman_trend_residual_reversion_v1` (WR 72.2%, n=18, p=0.096)
- **Axes:** Direction:LONG_ONLY + Symbol:8-allowlist
- **Goal:** Push p below 0.05 FDR threshold; hit n≥30
- **Key change:** Removes SELL signals; tightens z_entry 1.7→2.0; adds volume filter

### 2. `rsi_vol_bounce_v2_expanded.py`
- **Parent:** `st_rsi_vol_bounce` (WR 93.8%, n=16, DSR+FDR PASS)
- **Axis:** Symbol:6→18 expanded
- **Goal:** Generate 14 more trades to hit n≥30 promotion gate
- **Key change:** Preserves all signal logic; just widens symbol universe

### 3. `fear_greed_extreme_long_v2.py`
- **Parent:** `st_fear_greed_contrarian` (WR 53%, n=430, just promoted)
- **Axes:** Direction:LONG_ONLY + Threshold:FNG≤15 + Symbol:5→10
- **Goal:** Higher WR and better avg return by removing SHORT drag
- **Key change:** Tighter FNG trigger (15 vs 20) + 3-day declining trend confirmation

---

## Recommended Next Actions

1. **Re-run FDR analysis** — stale 2 months; many strategies likely now qualify
   ```bash
   python tools/run_fdr_analysis.py  # or equivalent
   ```

2. **Run `promote_strategy.py --audit`** after FDR refresh to catch any newly eligible

3. **Fix `cta_golden_cross` in elite** — negative PF strategy should NOT be in elite tier

4. **Apply 3-axis mutation to `cta_cross_asset_tsmom`** — 0% WR, 11 trades; check if long_only rescues it

5. **Trigger mass backtest** on the 42+ untested strategies
   ```bash
   gh workflow run battleground-mass-backtest.yml
   ```

6. **Monitor new variants** — all 3 have `status: pending_backtest` in meta.json

---

## Related

- [[reference/performance-tiers]]
- [[reference/banned-sources]]
- [[strategies/mega_mutation]]
- [[strategies/FORWARD-TEST-QUEUE]]
- [[incidents/resolver-intrabar-blocker]]

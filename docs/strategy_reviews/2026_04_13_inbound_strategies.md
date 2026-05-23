# Inbound Strategy Review — 2026-04-13

## Source
4 strategy files dropped into `~/Downloads/` for review and possible integration:
- `commodity_seasonal_momentum.py`
- `cross_asset_short_edge.py`
- `equity_earnings_drift_momentum.py`
- `forex_mean_reversion_divergence.py`

## TL;DR

| File | Verdict | Reason |
|---|---|---|
| `commodity_seasonal_momentum.py` | 🟡 STAGED | Real edge thesis but unsourced seasonal map + no commodity data ingest |
| `cross_asset_short_edge.py` | 🔴 REJECTED | Built on n=19 finding (Wilson CI [51%, 88%]) — premature |
| `equity_earnings_drift_momentum.py` | 🔴 REJECTED | Duplicates PR #139 `earnings_momentum_pead` |
| `forex_mean_reversion_divergence.py` | 🟡 STAGED + RED FLAG | Same setup class as `connors_rsi2_forex` killed in PR #123 |

## Shared technical issues across all 4 files

### 1. Broken Monte Carlo permutation test (FIXED in staged files)

All 4 files contain the same dead statistical test:

```python
shuffled = np.random.permutation(per_trade_pnl)
mean_pnl = np.mean(shuffled)
sim_sharpe = mean_pnl / std_pnl * np.sqrt(252)
```

`np.random.permutation` reorders the array but preserves both the mean and std. Therefore every simulated Sharpe equals the actual Sharpe, the threshold equals the actual Sharpe, and the p-value is deterministic junk. The Monte Carlo test does not actually test anything.

**Fix applied** to the 2 staged files: replaced with sign-shuffle (each trade flips sign with p=0.5), which is the proper null hypothesis "the system has no directional edge over the same payoff magnitude distribution." This aligns with `tools/data_integrity/monte_carlo_baseline.py` (PR #157), which uses the same approach against the live ledger.

### 2. Wrong signature for repo integration

All 4 files return a `pd.DataFrame` with `signal`/`stop_loss`/`take_profit` columns. The repo's strategy registries expect `(df, symbol, info) -> list[dict]`. Examples:
- `multi_asset/forex_strategies.py` `FOREX_STRATEGIES`
- `multi_asset/commodity_futures_strategies.py` `COMMODITY_STRATEGIES`
- `alpha_engine/equity_strategies.py` (flat function imports in `non_crypto_agent/main.py`)

A wrapper function would be needed for any registry integration. Not done in this PR — the staged files are stand-alone for backtest only.

### 3. Non-stdlib dependencies

All 4 files use `pandas` and `numpy`. That's fine for backtest scripts but inconsistent with the stdlib-only pattern used by `tools/data_integrity/` (PR #145) and `tools/adaptive/` (PR #161). Live diagnostic / curation code should remain stdlib-only; backtest code can use pandas.

---

## Per-file verdict

### 🟡 `commodity_seasonal_momentum.py` — STAGED

**Edge thesis:** Commodities have real seasonal patterns (NG winter heating, grains spring planting, gold Q1 demand). Combining seasonal bias with Donchian breakout + ADX + RSI confluence is reasonable.

**Strengths:**
- Clean code structure
- Realistic indicator combinations
- Proper ATR stop sizing
- Donchian exit channel for trailing stop

**Critical issues:**
- **Hardcoded seasonal bias map is unsourced.** Values like "GC: Jan-May bullish" are common lay narratives, not backtest-derived. Without empirical validation on 10+ years of historical commodity data, these are assumptions that may or may not survive contact with reality.
- **Commodity data is absent from the current ledger.** PR #144 diagnostic found 4 FUTURES, 0 pure COMMODITY trades across both ledgers. There's no live commodity scanner producing data this strategy could trade.
- Original Monte Carlo broken (FIXED).

**Action:** Stage in `new_strategies_2026_04_13/` with `NOT WIRED` warning header. Before promotion to `multi_asset/commodity_futures_strategies.COMMODITY_STRATEGIES`:
1. Run a 10-year backtest against the SEASONAL_BIAS map with a permutation test on the bias values themselves (shuffle months and verify the seasonal effect disappears in the null)
2. Confirm a commodity data ingest is producing live picks in the broader system
3. Wrap the function to match the `(df, symbol, info) -> list[dict]` signature
4. Add it to the dispatch only after passing all 3 above

### 🔴 `cross_asset_short_edge.py` — REJECTED

**Edge thesis:** "SHORT direction has +16% WR advantage over LONG" based on a documented 73.7% SHORT WR finding in the closed_picks ledger.

**Why rejected:**

The 73.7% WR is **n=19**. Wilson 95% CI for 14/19 is [51.2%, 88.2%] — the lower bound barely clears 50%. One unlucky trade (13/20) drops the CI to [43.3%, 81.9%], which crosses 50%. This is not a statistically robust edge to build a multi-file, multi-asset strategy framework around.

Mercury's MD review (PR #159) flagged this exact finding as: *"must NOT be propagated as live WRs or used for sizing, and conflict with `feedback_mutate_before_kill.md` / kill-protocol n-requirements if acted on."*

**Other problems:**
- Crypto SHORT branch depends on a `funding_rate` parameter — this repo has no funding rate ingest pipeline
- Equity SHORT branch targets equities where the ledger has 1 EQUITY trade total (PR #144 finding)
- Forex SHORT branch targets forex where the ledger has 9 FOREX trades total
- Commodity SHORT branch targets commodities (0 trades)

The 4 sub-strategies are designed for asset classes that don't have data to run them on. Even the crypto sub-strategy's premise (high funding → overleveraged longs → short edge) requires data infrastructure that isn't there.

**Action:** Do not stage. Recommendation: when n on the 73.7% bucket reaches ≥ 100 with Wilson CI lower bound ≥ 60%, reopen this as a candidate.

### 🔴 `equity_earnings_drift_momentum.py` — REJECTED as duplicate

**Edge thesis:** Post-earnings announcement drift (PEAD) — stocks that beat earnings drift upward for 60-90 days.

**Why rejected:**

PR #139 already shipped `earnings_momentum_pead` in `multi_asset/equity_strategies.py` with:
- An earnings calendar gate via `yfinance Ticker.calendar` + cached fallback
- 14-day window default
- 10-day max hold
- Graceful degradation when earnings data is unavailable
- 5 unit tests in `tests/test_earnings_calendar_filter.py`

The candidate file's earnings logic is a reimplementation that:
- Has no actual earnings API integration
- Falls back to "momentum-only" when no earnings data is passed (defeats the PEAD thesis entirely — momentum-only on equities is a separate strategy)
- Doesn't integrate with the earnings calendar cache

**Action:** Do not stage. Point future contributors at `multi_asset/equity_strategies.py:earnings_momentum_pead` if they want to enhance the existing PEAD implementation.

### 🟡 `forex_mean_reversion_divergence.py` — STAGED + RED FLAG

**Edge thesis:** BB(20,2) + RSI(2) mean reversion on forex pairs, gated by London+NY session overlap and ADX < 25 (ranging markets only).

**Strengths:**
- BB + RSI(2) mean reversion is a documented setup class (Connors RSI 2-period strategy)
- Session filter (08:00-17:00 UTC) is a valid liquidity/edge filter
- ADX < 25 ranging-market filter is sound for mean-reversion
- ATR-based stops are reasonable

**Critical concern:**

PR #123 (merged this session) **killed `connors_rsi2_forex`** for posting:
- 61.75% WR
- **PF 0.68**
- **-20.6% return on 995 trades**

`connors_rsi2_forex` is the **same setup class** as this candidate strategy: short-period RSI mean reversion on forex. The high-WR-but-negative-economics pattern is a documented failure mode — wins are frequent but small, losses are larger and less frequent. The aggregate is negative.

This candidate's only meaningful differences from `connors_rsi2_forex`:
- Adds session filter (helpful)
- Adds ADX ranging filter (helpful)
- Uses RSI(2) thresholds 10/90 instead of whatever connors_rsi2_forex used
- Adds volume spike requirement

These are improvements but don't fundamentally change the setup category. There is real risk this is a marginal variation on the same losing edge.

**Action:** Stage with explicit `RED FLAG` warning. Before promotion to `multi_asset/forex_strategies.FOREX_STRATEGIES` or `non_crypto_agent` import path:
1. **Head-to-head walk-forward backtest vs. `connors_rsi2_forex` killed-PR data** — the candidate must do significantly better, not just slightly better
2. **PF >= 1.5** confirmed on n >= 100 forex trades after costs
3. **Wilson 95% CI lower bound on WR > 50%** across at least 2 forex pairs
4. **DXY macro gate alignment check** — verify it doesn't fight the DXY gate already shipped in PR #124
5. **Verify it doesn't recreate the high-WR-low-PF trap** specifically: avg_loss should not exceed avg_win × 1.5

---

## What this PR ships

```
new_strategies_2026_04_13/
  commodity_seasonal_momentum.py          (STAGED — NOT WIRED, MC fixed)
  forex_mean_reversion_divergence.py      (STAGED — NOT WIRED, MC fixed, RED FLAG)

docs/strategy_reviews/
  2026_04_13_inbound_strategies.md        (this report)
```

**No live strategy registry is touched.** No filter gate is modified. Importing the staged files has zero effect on live picks.

## Related session work

- **#123** — killed `connors_rsi2_forex` for high-WR negative economics (relevant to the forex candidate)
- **#139** — shipped `earnings_momentum_pead` with calendar gate (duplicates the equity earnings candidate)
- **#144** — SL distance floor gate + diagnostic showing 4 FUTURES / 0 COMMODITY / 9 FOREX in current ledger
- **#157** — Monte Carlo baseline using sign-shuffle (correct null hypothesis pattern)
- **#159** — Mercury MD review flagging "73.7% SHORT WR" as too-small-sample to deploy

## Follow-up checklist (if any of the staged strategies are promoted later)

- [ ] Wrap function signature: `(df: pd.DataFrame) -> pd.DataFrame` → `(df, symbol, info) -> list[dict]`
- [ ] Register in the appropriate `*_STRATEGIES` dict
- [ ] Add the strategy to the relevant scanner's dispatch list
- [ ] Run `tools/data_integrity/monte_carlo_baseline.py` against post-deployment closed picks
- [ ] Wilson CI check via `tools/data_integrity/win_rate_wilson_ci.py`
- [ ] Document deployment in `docs/agents/` per the session's documentation requirement

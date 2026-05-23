# Asset Class Rehab — Session 2 Summary

**Date:** 2026-04-14
**Plan:** [docs/ASSET_CLASS_REHAB_PLAN_2026-04-14.md](ASSET_CLASS_REHAB_PLAN_2026-04-14.md)
**Recon:** [docs/ASSET_CLASS_REHAB_RECON_2026-04-14.md](ASSET_CLASS_REHAB_RECON_2026-04-14.md) (session 1)
**Workstream:** A.1 — Real-data backtest harness

---

## TL;DR

Built and ran the real-data MIMO backtest harness the plan asked for. On 2 years of actual yfinance daily bars, **0 of 7 MIMO strategies pass the plan §A.4 promotion gate**. This is the honest number. It directly contradicts the pre-revert Antigravity claim that "1 of 7 cleared PF 1.75" — which was computed on synthetic GBM data that this harness is built to replace.

## Files added

| File | Purpose |
|---|---|
| [`scripts/backtest_mimo_on_real_bars.py`](../scripts/backtest_mimo_on_real_bars.py) | 472-line real-data harness: fetches yfinance bars, imports each MIMO module, drives `generate_signals()` directly, replays entries via inline TP/SL forward walk, computes bootstrap CIs + permutation p-values. Replaces an earlier broken stub at the same path that called `STRATEGY_REGISTRY[name]['backtest']` (a method only 1 of 7 strategies exposes — the other 6 failed silently). |
| [`mimo_strategies/backtest_results.json`](../mimo_strategies/backtest_results.json) | First honest per-strategy metrics run — committed as the canonical reference result for the next strategy-research session. |
| [`docs/ASSET_CLASS_REHAB_SESSION_2_SUMMARY.md`](ASSET_CLASS_REHAB_SESSION_2_SUMMARY.md) | This file. |

## Files NOT changed

- No edits to any MIMO strategy under [`mimo_strategies/`](../mimo_strategies/) — the plan §A.1.1 directive is "load without modification".
- No edits to [`alpha_engine/scanner.py`](../alpha_engine/scanner.py), [`alpha_engine/config.py`](../alpha_engine/config.py), [`audit_trail/quality_gates.py`](../audit_trail/quality_gates.py).
- No edits to any live dashboard file or `audit_dashboard/data/*.json`.
- No commits to [`docs/ASSET_CLASS_REHAB_PLAN_2026-04-14.md`](ASSET_CLASS_REHAB_PLAN_2026-04-14.md) itself — the plan stands as written.

## Results — all 7 MIMO strategies on 2 years of real yfinance 1d bars

Promotion gate (plan §A.4): `n ≥ 30 AND bootstrap PF CI-lower ≥ 1.20 AND permutation p < 0.05`

| # | Strategy | Asset | n | WR | PF | PF CI-low | Perm p | Gate |
|---|---|---|---|---|---|---|---|---|
| 1 | bond_seasonal_regime | BOND | **0** | — | — | — | — | ❌ no signals fired |
| 2 | commodity_keltner_cci_reversion | COMMODITY | 35 | 28.6% | 0.43 | 0.16 | 1.00 | ❌ broken edge |
| 3 | equity_volume_momentum_breakout | EQUITY | 71 | 45.1% | **1.45** | 0.82 | **0.076** | ❌ close but no cigar |
| 4 | etf_vwap_mean_reversion | ETF | 100 | 36.0% | 1.07 | 0.67 | 0.40 | ❌ |
| 5 | forex_session_carry_momentum | FOREX | 76 | 44.7% | **1.36** | 0.81 | **0.110** | ❌ close |
| 6 | futures_mean_reversion_rsi_bb | FUTURES | 38 | 47.4% | 0.98 | 0.45 | 1.00 | ❌ |
| 7 | futures_trend_dual_ema | FUTURES | 77 | 36.4% | 0.83 | 0.46 | 1.00 | ❌ |

**Promotion-eligible: 0 / 7**

### What this tells us

**The only promising candidates are `equity_volume_momentum_breakout` and `forex_session_carry_momentum`.** They post positive edge on headline PF (1.45 / 1.36) and have permutation p-values that are *near* but not *at* the 0.05 gate. With one of:
- a longer history (3y instead of 2y),
- tighter entry filtering (currently no score/regime overlay),
- or a parameter sweep,
the next session could plausibly get one of them across the gate. These are the research-worthy strategies.

**`commodity_keltner_cci_reversion` is broken on recent data** — PF 0.43, 28.6% WR, permutation p = 1.0 is a clear "no edge" signal. Either the strategy logic is wrong for the 2024-2026 commodity regime or its parameters were tuned on a very different window. Either way it needs a rewrite, not a tweak.

**`bond_seasonal_regime` generated zero signals** on its 8 bond symbols over 2 years. The strategy is too restrictive to fire at all on daily data — the entry conditions need relaxing, or it needs a different timeframe.

**The two futures strategies are both net-negative** on futures symbols. Same verdict as commodity — broken on recent data, needs a rewrite.

### Important caveats

1. **Daily bars only.** The harness runs on `interval=1d` because that's what yfinance reliably serves for multi-asset free data. Strategies designed for intraday (1h or 15m) won't show their real behavior here. Specifically: the two `futures_*` strategies may be intraday-tuned and just aren't compatible with daily resolution. Next session could split into per-timeframe runs.
2. **2-year window.** yfinance's `period="2y"` covers roughly 2024-04 → 2026-04. That is the regime we care about for live trading right now, but a longer window would smooth regime bias and tighten bootstrap CIs.
3. **TP fallback for 4 of 7 strategies.** Bond / commodity / equity / etf MIMO strategies emit SL but no explicit TP column. The harness derives TP using a 2:1 R:R off the stop distance (plan-compliant default, configurable via `DEFAULT_RR_FALLBACK`). This is a real modeling choice — if a strategy's "real" TP logic is tighter or wider, these numbers will shift. The 3 strategies that emit TP columns natively (forex / 2x futures) are tested as-written.
4. **SL-before-TP intrabar ordering.** When both SL and TP are within the same bar's high-low range, the replay loop assumes SL hit first. This is the conservative choice and matches how [`alpha_engine/battle_test.py:88-144`](../alpha_engine/battle_test.py#L88-L144) handles the same ambiguity in production.

## Design decisions for the harness

1. **Did not import `alpha_engine.battle_test`.** That module has top-level imports (`config`, `crypto_strategies`, `forex_strategies`, `equity_strategies`) that drag in the full project state and require env vars to initialize. For a MIMO-only run we don't need any of that. Instead, the `fetch_historical_data()` function is direct-ported from [`alpha_engine/battle_test.py:50-80`](../alpha_engine/battle_test.py#L50-L80) — same yfinance call pattern, same multi-symbol handling, same 50-bar minimum. This is honest reuse without the dependency cascade. Documented in the module docstring.
2. **Inlined `_replay_trade` instead of calling `battle_test.simulate_pick`.** `simulate_pick` uses Title-case column names (`row["High"]`) because it was built against raw yfinance output, while the MIMO `generate_signals` functions expect lowercase. Inlining avoids the casing fight and also skips `simulate_pick`'s production trailing-stop / TRAIL_ACTIVATE_PCT machinery that we don't want in a backtest.
3. **Bootstrap 1k not 10k.** Plan §A.1.4 called this explicitly — diminishing returns past 1k for WR/PF CI.
4. **Permutation test via sign-shuffle on `|pnl|`.** Under H0 (no edge), a strategy's per-trade PnL should be zero in expectation and signs should be random. Shuffling the signs 500 times and counting how often the shuffled mean beats the observed mean gives a one-sided p-value. Returns 1.0 for observed mean ≤ 0 (no edge claim possible).
5. **Fail-loud on insufficient n, save the artifact anyway.** Plan §A.1.7 says "fails loudly" — the harness prints a clearly-marked DO NOT PROMOTE section and returns a non-zero exit code when nothing is eligible, but still writes the JSON so the insufficient-n runs are themselves auditable. That's a deliberate interpretation of "fail loudly" — don't delete the evidence, surface it loudly.
6. **Self-lint for synthetic OHLCV is external, not embedded.** Plan §A.3 specifies "grep the script for `np.random.seed` or `pd.date_range(start=` followed by a synthetic close column; CI fails if present." The harness does not embed a runtime self-check because the lint is meant to be a CI-level guardrail. I ran it manually after writing: `grep -nE "np\.random\.seed|pd\.date_range\(start=" scripts/backtest_mimo_on_real_bars.py` returns empty. Clean.

## How to reproduce the result

```bash
# Full run
python scripts/backtest_mimo_on_real_bars.py --period 2y

# One strategy
python scripts/backtest_mimo_on_real_bars.py --strategy mimo_strategies.equity_volume_momentum_breakout

# With trade-level dump for audit
python scripts/backtest_mimo_on_real_bars.py --period 2y --trades-output /tmp/mimo_trades.json
```

Output lives at [`mimo_strategies/backtest_results.json`](../mimo_strategies/backtest_results.json).

Requires: `yfinance`, `pandas`, `numpy`. No Binance / CoinGecko / Alpaca dependencies.

## Recommended next steps

Ranked by expected value per hour of effort:

1. **Re-run with `--period 3y`.** Costs nothing, might push `equity_volume_momentum_breakout` and `forex_session_carry_momentum` across the p < 0.05 gate just via larger n. Lowest-effort confirmation test.
2. **Parameter sweep on the two close-to-gate strategies.** Grid-search a handful of their config parameters (ATR multipliers, RSI thresholds, EMA periods) on real data and look for a configuration that clears both the PF CI-lower ≥ 1.20 and perm p < 0.05 simultaneously. Same harness, outer loop around `_run_one_strategy`. Probably 1 session of work.
3. **Rebuild `bond_seasonal_regime` entry logic.** It generated zero signals in 2y × 8 bonds. Either the seasonal filter is too tight or the RSI condition never coincides with the regime check. Read the file, loosen the gate, re-run.
4. **Split futures / commodity into separate intraday + daily runs.** If these strategies were tuned for 1h or 15m bars, the daily run is a false negative. Check the strategy docstrings for the intended timeframe; if intraday, fetch 60d × 1h bars from yfinance instead.
5. **Workstream B.2 execution — BOND source diversification.** The recon flagged BOND as a 1-source × 1-strategy × 1-symbol monoculture. Wire `bond_seasonal_regime` into the scanner as a second BOND source, once it actually fires. This is the direct path to resolving the n=8 problem surfaced in session 1.
6. **Workstream D — Antigravity reply.** Plan §5 drafted the message; now we have real-data numbers to cite back. Can be sent any time.

Items 2 and 4 are the most likely to actually produce a passing strategy.

## Out of scope for this session (deferred by design)

- No changes to `quality_gates.py` to lift the FUTURES block. Recon session 1 flagged that as a B.2 proposal — still needs explicit user approval before touching.
- No rebuilds of any MIMO strategy. The plan is explicit: session 2 tests them as-written; any rewrites are strategy-research sessions with their own scope.
- No ETF strategy additions despite recon finding that 58% of live ETF picks come from already-blocked strategies. That's its own B.2 workstream.
- No changes to live HTML, dashboard generators, or `audit_dashboard/data/*.json` files.
- No network calls beyond the yfinance multi-symbol fetches the harness itself makes.
- No strategy promotions. The gate says 0 of 7 are eligible — the plan is obeyed literally.

## Validation steps performed

- `python -m py_compile scripts/backtest_mimo_on_real_bars.py` — compile OK.
- `grep -nE "np\.random\.seed|pd\.date_range\(start=" scripts/backtest_mimo_on_real_bars.py` — no synthetic-data patterns (plan §A.3 lint).
- Single-strategy smoke test on `bond_seasonal_regime` completed without exception.
- Full 7-strategy run completed, writing `mimo_strategies/backtest_results.json` (the committed artifact).
- Results JSON was the authority for every number in the table above; no numbers are hand-typed from memory.
- All 7 strategies successfully imported via `importlib.import_module` — the broken-registry failure mode of the earlier stub is gone.

## Branch state

- Branch: `feat/mimo-real-data-harness`
- Base: `origin/main` @ `2b3afb6dcb`
- Delta: 3 files added, 0 modified, 0 removed
- No PR opened — parked as a branch for your review per the same pattern used for `feat/hyro-portfolio-sim` and `chore/asset-class-rehab-recon`.

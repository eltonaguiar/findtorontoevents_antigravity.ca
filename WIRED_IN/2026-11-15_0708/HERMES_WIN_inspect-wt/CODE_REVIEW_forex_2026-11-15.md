# Code Review — Forex pipeline (`alpha_engine/forex_smart_picks.py`)

**Date:** 2026-11-15 · **Branch:** `hermes/forex-session-window-fix` · **Scope:** static inspection, no execution against live brokerage
**Why:** forex is being kept in scope deliberately (an edge may still exist), so the code path has to be trustworthy before any picks from it are believed.

## Findings

### F1 — 4 of 6 scheduled runs were guaranteed no-ops that reported success (FIXED)
`main()` returns early unless `7 <= now.hour < 16` UTC. The workflow cron ran at `0 2,6,10,14,18,22 * * 1-5` — of those six slots, only **10 and 14** fall inside the window. Slots 2, 6, 18 and 22 have **never** been able to produce a pick, and because the early return exits 0, GitHub displayed them as green.

- Impact: two-thirds of the scanner's advertised cadence did not exist, and the green badge hid it.
- Fix: cron narrowed to `0 8,10,12,14 * * 1-5` (all inside the accepted window), plus a `::warning::` annotation on any future skip so a no-op is visible in the Actions UI instead of silent.

### F2 — `ig_contrarian_sentiment` is misnamed and carries the highest confidence (ANNOTATED)
Name and `STRATEGY_STATS` (`wr=0.583, sharpe=5.87`) imply an IG retail-positioning feed. The function reads **no sentiment data** — it is RSI(14) `< 25` with a rising 5-bar SMA(50) slope, and the inverse for shorts.

- A Sharpe of 5.87 on FX is not credible. It is most likely a small-sample artifact: RSI extremes with a confirming slope are rare, so the stat rests on very few observations.
- It also returns the highest confidence in the file (0.65–0.75 vs 0.50–0.65 elsewhere), so it dominates emitted picks.
- Action taken: docstring corrected to state what the rule actually is and that the Sharpe must be re-derived with a trade count. **Behaviour intentionally unchanged** — removing or re-weighting a strategy mid-flight would collide with parallel work; that decision belongs to whoever owns forex.

### F3 — Hardcoded header presented one historical backtest as current performance (FIXED)
`main()` printed `Backtest: Sharpe 2.06 | WR 45.9% | PF 1.30 | PnL +20%` on every run. That is a single historical configuration, never reproduced out-of-sample, and it read as live status in the logs. Replaced with the actual per-strategy `STRATEGY_STATS` table, explicitly labelled "Backtest estimates (NOT forward-tested)".

### F4 — Carry signal uses frozen rate differentials (NOT FIXED — needs an owner)
`PAIRS[*]["carry_yield_diff"]` are literal constants in source (`USDJPY=X: 4.5`, `GBPJPY=X: 4.75`, `AUDJPY=X: 5.25`, `EURUSD=X: -0.5`, …). `check_carry_trade` scores `carry + mom_20d * 10`, so a stale constant silently dominates a *live* momentum term. Central-bank differentials move; these don't.

- Why not fixed here: there is no rate feed wired into this module, and inventing one in a PR would change the strategy's inputs without data-source review. Recommendation: source differentials from a dated rates table (FRED series or an explicit config with an `as_of` date) and refuse to trade carry if the config is older than N days.

### F5 — Near-zero-edge strategy still enabled (NOT FIXED — judgement call)
`forex_mean_reversion_200d` has `sharpe=0.17, wr=39.6%`. It survives the `sharpe < 0` gate and therefore still emits picks despite being indistinguishable from noise. Two deprecated strategies with clearly negative Sharpe (−1.73, −2.69) were correctly removed and are only referenced in comments — that pattern should be applied here too.

## Verification

- `python -c "ast.parse(...)"` — file parses.
- `yaml.safe_load(workflow)` — cron parses to `[{'cron': '0 8,10,12,14 * * 1-5'}]`.
- No behavioural change to signal generation, TP/SL, or sizing. Only the schedule, the skip-visibility annotation, the header text and one docstring.

## Suggested follow-ups for whoever owns forex

1. Re-derive the `ig_contrarian_sentiment` Sharpe with an explicit trade count; drop it if N < 30.
2. Wire carry differentials to a dated source, or gate carry out when the config is stale.
3. Decide on `forex_mean_reversion_200d` (Sharpe 0.17) — keep only if it contributes to a portfolio, not standalone.
4. Run the whole path through `proof/PROOF_PROTOCOL.md` before any forex capital is sized on it.

# X-Post Repo Review + Per-Asset-Class Tweak Queue (2026-04-21)

**Author:** Claude Opus 4.7 (1M context)
**Triggered by:** user direction to review [this X post](https://x.com/i/status/2046294992713646576), integrate concepts, and make per-asset-class tweaks based on latest pick analysis.
**Status:** One surgical production tweak shipped. Full tweak queue documented for engineer review.

---

## 1. X-post repo review (9 repos)

Post headline: *"most traders pay $3,000+/month for tools GitHub replaced for free. 9 repos. zero subscriptions."*

| # | Repo | What it is | Status for us |
|---|---|---|---|
| 1 | [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) | Open-source financial terminal (Bloomberg replacement). Aggregated market/macro/crypto/options/fixed-income data. | **New to our stack.** Worth evaluating as a **data layer** to replace/augment our scrapers + API-failover chain (currently Binance mirrors → CoinGecko → KuCoin → CryptoCompare). Not an emission-path integration; a research/data convenience. |
| 2 | [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | Python crypto trading bot with backtesting, ML, hyperopt. | **Already flagged in [PR #301](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/301) survey.** Hyperopt's Bayesian/TPE sampler is the specific piece worth lifting — our current mutation-proposal YAMLs (cycle 8/9) do sweep enumeration; hyperopt would shrink the search by 10-100×. |
| 3 | [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | Market-making, CEX/DEX connectors. | **Already flagged, out of scope.** We don't market-make. OBI snapshot commits suggest partial inspiration already. |
| 4 | [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | LLM for finance: sentiment on news, headlines, tweets. | **New and potentially high-value.** Could feed the **sentiment agent** of the AutoHedge committee (PR #298) with properly-tuned LLM sentiment instead of our current regime_terminal + LunarCrush. Needs LLM infra / API credits before wiring. |
| 5 | [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | Production-grade event-driven trading platform in Python/Rust. | **Overkill** for our current pipeline. Would be a ground-up rewrite of our scanner stack. Park for future reference. |
| 6 | [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | Institutional-quality algo-trading engine (C#/Python). | **Already flagged, out of scope** — too heavy, C#-first. |
| 7 | [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | Simpler Python crypto trading bot with backtesting. | **New.** Positioned between freqtrade and nautilus in complexity. Worth a skim — Jesse's custom-indicator syntax is clean, might be easier to port ideas from than freqtrade's. |
| 8 | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | Fast vectorized backtesting with hyper-parameter optimization. | **Already flagged in PR #301 survey.** Most realistic integration: replace `alpha_engine/walk_forward_backtester.py` loops with vectorbt's pandas-vectorized variants for 10-100× speedup. |
| 9 | [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | Deep reinforcement learning for trading (PPO, SAC, DDPG). | **New and speculative.** Potential use: RL agent for **position sizing** (FIX-9 HyroTrader risk-sizer). But RL in production is hard; gate this behind the simpler deterministic Kelly / half-Kelly sizing first. |

### Concepts to lift (prioritized)

1. **Hyperopt (from freqtrade)** — Bayesian optimization over strategy parameters. Our current mutation-proposal YAMLs use grid sweeps; hyperopt converges with 10-50 evaluations instead of N^3+.
2. **Vectorbt** — pandas-vectorized backtesting speeds. Make `walk_forward_backtester.py` runs 10-100× faster so we can actually apply Bonferroni corrections at N=thousands (PR #300 framework requires this).
3. **FinGPT sentiment** — drop-in replacement for our sentiment agent as an upgrade, behind env flag.
4. **OpenBB** — data-layer convenience. Evaluate for cost-of-integration vs current scraper stack.
5. **FinRL** — defer. Too big for current headroom.

Each of these is a separate PR's worth of work. None are landed in this PR.

---

## 2. Per-asset-class pick analysis (subagent findings)

Full report: `updates/per_asset_class_pick_analysis_2026-04-21.md` (282 lines).

### TL;DR by class

| Class | n_closed | WR | PF | cum% | Active | Flagged |
|---|---|---|---|---|---|---|
| **CRYPTO** | 1,668 | 32.7% | **0.59** | **−1,324%** | 33 | 4 |
| **EQUITY** | 338 | **50.0%** | **1.43** | **+226%** | 9 | 0 |
| FOREX | 848 | 25.6% | 0.93 | −13% | 3 | **3/3** |
| COMMODITY | 552 | 21.6% | 1.10 | +7% | 2 | 0 |
| ETF | 74 | 48.7% | 1.03 | +3% | 0 | 0 |
| BOND | 17 | 47.1% | 1.60 | +3% | 0 | 0 |
| UNKNOWN | 3 | 100% | ∞ | +0.2% | 0 | 0 |

**Key observations:**
- CRYPTO alone is 121% of total book loss (−1,324 vs book −1,097). EQUITY is the only offset (+226).
- Two CRYPTO strategies own 88% of CRYPTO damage: `copy_hl_lb_None` (n=278, cum −806) and `st_fear_greed_contrarian` (n=627, cum −359). **Both are already in `_RETIRED_STRATEGIES` but still emit closed picks.** Zombie leak unchanged.
- All 3 active FOREX picks are flagged. 2/3 come from `non_crypto_consensus` (WR 0% n=85). **This is the surgical fix in this PR.**
- 4 active CRYPTO LONGs are on bottom-quartile symbols (OP/SUI/DOGE/LINK). Capital concentrated in losers.
- EQUITY's edge is repeatable: `Breakout Momentum` WR 59.5%, `stocks_rsi2_pullback` WR 61.1%, CVX symbol WR 74.1%.
- **The "flat-close bug" PR #301 estimated at 20% turns out to be only 1.77% system-wide** when measured by strict `pnl_pct == 0.0`. PR #301's broader triple-barrier definition over-counted. The real resolver concern is narrower: `non_crypto_consensus` 5.9% flat + 0% WR is a TP-at-entry / pnl-zeroing bug on that specific strategy, not a systemic resolver failure.

### Top-3 tweaks (subagent's recommendations)

1. **CRYPTO P0:** Retire / LONG-disable `st_fear_greed_contrarian`; circuit-break `copy_hl_lb_None` with hard −3% SL floor; drop 4 flagged active LONGs (OP/SUI/DOGE/LINK).
2. **FOREX P0:** Drop all 3 active FOREX LONGs; retire `non_crypto_consensus` entirely; narrow to `forex_rsi2_mean_reversion` on USDCAD/USDJPY/GBPJPY.
3. **EQUITY P1:** Scale `Breakout Momentum` + `stocks_rsi2_pullback`; kill JNJ from universe (WR 17.6% n=17); block 3 small-sample drag strategies until n ≥ 20.

---

## 3. What this PR actually ships

**ONE production change:**

**`alpha_engine/strategy_blocklist.py`** — added `non_crypto_consensus` to `_RETIRED_STRATEGIES` with detailed comment referencing this analysis.

Rationale for this one and not the others:
- `copy_hl_lb_None` and `st_fear_greed_contrarian` are **already retired** — adding them again won't fix the zombie leak. That requires tracing the bypass path first (cycles 3-9 flagged this; engineer action required).
- Symbol-level blocks (OP/SUI/DOGE/LINK) would need to live in a new symbol-blocklist or a `passes_active_gate` rule, not the strategy blocklist. Separate PR.
- Per-strategy LONG-disable needs a new mechanism in the blocklist (direction filter); not appropriate as a one-line change.
- `non_crypto_consensus` is unambiguous: **0% WR on n=85 is a kill-on-sight pattern, the fix is one-line, and it immediately stops 2 of the 3 active FOREX picks that the dashboard flags as invalid.**

## 4. Follow-up tweak queue (for engineer)

Order of impact:

### P0 — Trace & plug the zombie leak (cycles 3-9 unresolved)

`copy_hl_lb_None` (n=278, cum −806%) and `st_fear_greed_contrarian` (n=627, cum −359%) are in `_RETIRED_STRATEGIES` but close 900+ picks on the live dashboard. The `feed_hygiene.is_valid_active_pick` enforcement path clearly isn't covering every emitter.

Investigation path (from [PR #299](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/299) cycle-9 §P0):

1. Grep every writer to `recent_closed` / `picks["recent_closed"]` array. Does each one call `is_blocked_strategy()` or `is_blocked_pick()` before append?
2. Check the backfill / forward-validator path — it may re-tag older picks under retired labels.
3. Check cron scanners (signal recorder, momentum tracker, battle-test, etc.) that commit directly via GH Actions — they may not import `feed_hygiene`.
4. Ship a CI test `tests/test_blocklist_no_emission.py` that fails the build if any retired strategy appears in `recent_closed` with created_at > retirement date.

### P1 — Symbol-level active blocks for bottom-quartile CRYPTO LONGs

OP/SUI/DOGE/LINK all have WR < 25% on n ≥ 30 closed. Currently seeing 4 active LONGs on these. Either:
- Extend `audit_trail/quality_gates.py::passes_active_gate` with a symbol-historical-WR guard (previously proposed as "FIX-6" in plan, cycle 7 recommended it).
- OR add a new `symbol_blocklist.py` parallel to `strategy_blocklist.py`.

### P2 — LONG-only rejection during red BTC 4h

From `feedback_long_source_bias.md`: 7 sources are 99-100% LONG-only. `st_fear_greed_contrarian` matches this pattern and bleeds when BTC 4h is red. Add an asset_class CRYPTO + direction LONG + btc_4h_regime red gate.

### P3 — EQUITY over-allocation proposal

EQUITY is the only class near skill-verified (PSR 0.9954 from PR #301). Running `Breakout Momentum` + `stocks_rsi2_pullback` with more sizing is the single highest-EV rebalance in the current book. Requires capital-allocation infra we don't have yet (risk-parity from PR #301 is the scaffold).

### P4 — Investigate `non_crypto_consensus` TP-at-entry / pnl-zeroing resolver bug

Now that the strategy is retired from emission, the 88 closed-picks-at-pnl=0 legacy data remains. Figure out what the resolver did:
- Scan `audit_trail/dashboard_generator.py` for code paths that set `pnl_pct = 0.0` without resolving entry/exit.
- Scan `alpha_engine/forward_validator.py` for force-close logic that sets `pnl_pct = 0.0`.
- This may also fix 4 other strategies with >60% flat-close rate identified in PR #301.

### P5 — Tagging regression for `regime_*` equity picks

3 picks (AMD / DNA / RIVN) mistagged as UNKNOWN — they come from `regime_*` strategies that don't have an asset_class inference hook. Analogous to the session-3 crypto-tagging fix at `dashboard_generator.py:4836-4851` (see MEMORY.md).

---

## 5. Concepts to integrate from the 9 repos (roadmap)

Each is a separate PR's worth of work — none land here.

- **Hyperopt (freqtrade)** → replace mutation-proposal enumerations in `mutations/*.yaml` with Bayesian search; trim backtest cost.
- **Vectorbt** → rewrite `walk_forward_backtester.py` with vectorized ops; enables Bonferroni-corrected acceptance at high trial counts (PR #300 dependency).
- **FinGPT** → sentiment agent upgrade behind env flag (AutoHedge committee 5th slot).
- **OpenBB** → evaluate as data-layer augment for non-crypto classes where we rely on scrapers.
- **FinRL** → deferred; after deterministic Kelly/half-Kelly sizing (FIX-9) is proven.
- **Jesse** → skim for custom-indicator syntax; not an integration.
- **nautilus_trader / LEAN / hummingbot** → not in scope for current pipeline.

## 6. Reproduce

```bash
# Verify the new blocklist entry compiles + blocks
python -m py_compile alpha_engine/strategy_blocklist.py
python -c "from alpha_engine.strategy_blocklist import is_blocked_strategy; assert is_blocked_strategy('non_crypto_consensus'), 'should be blocked'"

# Re-run the per-asset-class analysis (subagent scripts in tmp_analysis/)
python tmp_analysis/analyze_picks.py  # outputs updated JSON

# X-post content via fxtwitter (x.com now paywalls API access)
curl -s "https://api.fxtwitter.com/status/2046294992713646576"
```

## 7. What's NOT in this PR

- No change to `audit_trail/quality_gates.py`, `dashboard_generator.py`, or any HC gate config.
- No symbol blocklist (P1 above).
- No direction-filter in blocklist (P2 above).
- No zombie-leak fix (P0 above — requires investigation trace first).
- No repo integrations — all documented, none landed.

## 8. Caveats

- **Adding `non_crypto_consensus` to `_RETIRED_STRATEGIES` only stops NEW emissions.** The 88 legacy closed picks remain in the rolling `recent_closed` window and will keep appearing in perf-reviews until they age out. This is expected.
- **If the resolver bug explains `non_crypto_consensus`'s 0% WR, the strategy itself might not be bad** — just the pnl-resolution path. Retiring it is still correct (operators can't trust the output), but the root-cause investigation in P4 could resurrect a fixed version.
- **WR-based retirement on n=85 has a Bonferroni caveat** (PR #300): at α/N=185, individual-strategy p-value bar is 0.00027. A strategy with 0 wins on n=85 has binomial p-value extremely low (close to 2^-85), so this retirement is statistically sound even under strict correction.

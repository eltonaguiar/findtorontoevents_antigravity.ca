# Phase 2 Strategy Synthesis — From Peer Research + Adversarial Critique → Shippable Code

**Date:** 2026-04-18
**Branch:** `fix/phase2-multi-asset-strats`
**Purpose:** Nine peer AIs dumped overlapping strategy research docs into
`main` inside 24 hours. Three adversarial critique agents then tore into the
plan. This doc reconciles all of that into **what actually gets built**,
what's explicitly rejected, and why.

---

## The 9 peer-AI research docs currently on `main`

| File | Author | Scope |
|---|---|---|
| `ANTIGRAVITY_STRATS.MD` | Antigravity fleet | 40+ overlooked strategies |
| `CHATGPT_STRATS.MD` | ChatGPT Codex (b66fa22937) | Practical gap shortlist: rebalance flows, macro surprise drift, dealer gamma, rates carry, borrow-fee pressure, analyst revisions, VRP, convenience yield, merger arb, FX hedging flow |
| `CURSOR_STRATS.MD` | Cursor | - |
| `ELEPHANT_STRATS.MD` | Kilo Code (073929b453) | Market microstructure, non-linear indicators, ML/AI, alt data |
| `OLLAMA_STRATS.MD` + `OLLAMA_STRATS_ENHANCED.MD` | Roocode | 77+ "frontier" strategies inc. quantum, neuromorphic, topological data analysis |
| `GITHUB_CLOUDAGENT_STRATS.MD` | GitHub Cloud Agent (104a741) | Coverage-gap analysis |
| `INSTITUTIONAL_ALPHA_REPORT_2026-04-06.md` | - | Institutional alpha |
| `INSTITUTIONAL_STRATEGY_RESEARCH.md` | - | - |
| `institutional_scalping_research.md` | - | Scalping |

Plus pending / in-flight at time of writing: Kimi's KIMI_STRATS.MD (6 subagents running), ChatGPT Codex's broadened catalog (fanning out by asset-class), and more.

**Commentary.** The volume of MD research is not the bottleneck. The bottleneck is **the ledger shows WR 31% / PF 0.40 / cumulative −673%** across 4,762 closed picks — and nearly every dumped "overlooked" strategy is a published anomaly that has already decayed, or needs infra we don't have (tick liquidations, point-in-time Compustat, CFTC CoT, roll-adjusted futures). Adding 77 new strategies to a leaking bucket does not fix the leak.

## The 3 adversarial critiques (summary)

Three Claude subagents were dispatched with hostile-reviewer prompts over the strategy list. Full transcripts in agent outputs; verdicts below.

### Critique A — Crypto + ETF (a7fa821803f457f45)
- **Reject outright:** C-1 Funding-fade (crowded), T-1 Overnight SPY (decayed post-2020), T-2 Sector rotation (AQR literally closed their momentum fund), T-3 Vol-targeted QQQ ("risk management dressed up as strategy").
- **Conditional:** C-4 OI-Donchian (only with frozen params — no re-tuning); C-3 Liquidation-cascade (needs tick data, not OHLCV).
- **C-2 Perp-spot basis:** look-ahead risk + retail fees eat the 15 bps edge.
- **Kicker:** "Before adding any new strategy, answer: why is the current 31% WR broken?"

### Critique B — Equity + Forex (afd88eab6c1b8b228)
- **Defensible:** E-3 Insider-Cluster Buying (Cohen-Malloy-Pomorski, regulatory moat); E-4 Residual Momentum (Blitz-Huij-Martens, half the drawdown of vanilla momentum); F-3 CoT Reversal (low-cost weekly signal).
- **Will fail:** E-1 Quality+Momentum and E-2 52wk Breakout ("same disease with a new name" — both fit to the 2020-2026 mega-cap-tech regime, which is exactly where the existing equity book bled).
- **Forex dead-ends:** F-1 London GBPUSD Breakout (cost-eats-edge at retail), F-2 AUDJPY (yen-carry-unwind ticking bomb).
- **Minimum paper window:** 6 months for E-3/E-4, 1 year for F-3.

### Critique C — Commodity + Universal (aad2ddc391e7a9259)
- **Commodities:** all three (M-1 Natgas seasonal, M-2 Gold/Silver, M-3 DXY-gold) have either infra debt (roll-adjusted continuous futures), fat-tail regime breaks (Natgas lost −42%/−50% in 2014/2018 during the supposedly best window), or redundancy with other gates. **Drop.**
- **Universal techniques:**
  - 🟢 **U-1 Vol-targeted sizing** — ship with hard 1.5× cap and 0.25× floor.
  - 🔴 **U-2 Fractional Kelly** — with current 31% WR / 1.3× loss-win ratio, Kelly says **don't trade** (f* = −0.45). Using 0.25× of a negative number is nonsense. Defer until ≥500 trades-per-strategy for stable edge estimation.
  - 🔴 **U-4 ML stacking** — "we have a null-features crisis, not a complexity shortage." Stacking four leaky models gives a beautifully overfit ensemble.
  - 🟡 U-3 Hurst gate — effort claimed 2/5, real 4/5 (R/S analysis infra + per-symbol state).
  - 🟡 U-5 Regime gate — lags by construction (triggered 11 days after the 2020 March bottom).

- **CRITICAL interaction bug caught:** Stacking U-1 (vol-target) × U-2 (Kelly) naively multiplies them:
  ```
  final_size  =  capital × 0.25 × (μ/σ²) × (σ_target/σ)  =  capital × 0.25 μ σ_target / σ³
  ```
  That divides by **σ³** — triple-penalising volatility. Correct: use vol-target as primary sizer; Kelly as a ceiling, never as a multiplier. This is unit-tested in `tests/test_vol_targeted_sizer.py :: test_kelly_ceiling_does_not_multiply_into_base`.

---

## What gets shipped (this PR)

### Code
| File | Purpose |
|---|---|
| `baby_strategies/funding_rate_mean_reversion_v1.py` | C-1 **with explicit kill criterion** (live Sharpe < 0.8 at n=60 → disable). Proxy mode (RSI+BB) for backtests that lack funding feed. |
| `baby_strategies/oi_confirmed_donchian_breakout_v1.py` | C-4 **with frozen params**. Refuses to emit if `open_interest` column is absent (un-gated Donchian is known-noise, 44% WR). |
| `alpha_engine/vol_targeted_sizer.py` | U-1 universal sizing wrapper. 1.5× cap, 0.25× floor, Kelly ceiling as optional post-filter (not multiplier). Env knobs: `VOL_TARGET_ENABLED`, `VOL_TARGET_SHADOW`. |
| `tests/test_vol_targeted_sizer.py` | 15 unit tests — including the σ³ double-count regression test. |

### Docs
- This file (`docs/strategy_phase2/SYNTHESIS.md`).

### Explicitly NOT shipped (and why)

| Tag | Strategy | Reason (cites critique) |
|---|---|---|
| C-2 | Perp-spot basis directional | Look-ahead bias + retail fees eat edge |
| C-3 | Liquidation-cascade reversal | Needs tick data, not OHLCV |
| E-1 | Quality + Momentum | Same disease as current equity bleeds |
| E-2 | 52wk-high Breakout | Same disease as current equity bleeds |
| E-3 | Insider-Cluster Buying | **Deferred to Phase 3** — needs SEC EDGAR Form 4 scraper (infra, not code) |
| E-4 | Residual Momentum | **Deferred to Phase 3** — needs rolling 60-month FF regression infra |
| F-1 | London Breakout GBPUSD | Retail spread eats 25% of target move |
| F-2 | AUDJPY risk-on | Yen-carry-unwind tail risk unquantifiable |
| F-3 | CoT Reversal | **Deferred to Phase 3** — needs weekly CFTC scraper |
| M-1/2/3 | Commodity seasonals & spreads | Infra debt + fat-tail breaks |
| T-1/2/3 | ETF strategies | All decayed published anomalies |
| U-2 | Fractional Kelly | Current edge estimate is negative; Kelly says don't trade |
| U-3 | Hurst / ADX gate | Effort 4/5 not 2/5; defer |
| U-4 | ML stacking | Null-features crisis must be solved first |
| U-5 | Regime gate | Lags drawdowns by construction |

### Phase 3 gated work (data-infra required before coding)

1. SEC EDGAR Form 4 scraper → enables E-3 Insider-Cluster.
2. Rolling Fama-French 5-factor regression → enables E-4 Residual Momentum.
3. CFTC weekly CoT scraper → enables F-3 CoT Reversal.
4. Tick-level liquidation event window → enables C-3 Liquidation-cascade.
5. Realized-vol store per symbol per bar → unlocks vol-target sizing at production.

These are the only items the critique considered defensible. They are infra-heavy and out of scope for Phase 2 code.

---

## Why this plan is different from just ignoring the critique and shipping 10 strategies

Because every peer-AI research doc is effectively saying "here are 20 more things to try" — but the existing 4,762-pick ledger shows the problem isn't a shortage of strategies. It's that the ones we have don't have real edge, and 90% of these "new" ideas are published anomalies that have already been arbed away by faster capital. Shipping 10 of them would:

1. Widen the blast radius of our failing calibrator (the 0.65–0.70 confidence band that's worse than random).
2. Not address the root bleed.
3. Make the next post-mortem 10× harder.

The two crypto strategies that are shipped both carry **frozen parameters** and **hard kill criteria** — if they don't survive live, they auto-exit after 60 trades without ambiguity. The vol-targeted sizer is the one universal upgrade the critique endorsed, with the σ³ bug pre-empted.

Phase 3 is where we go back and build the infra (EDGAR, FF factors, CoT, tick liquidations, per-symbol realized vol) that the defensible Phase 2 candidates need. No Phase 3 work starts before the forensic mutation analysis on the existing ledger completes per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

## Test plan

```bash
python -m unittest tests.test_vol_targeted_sizer -v          # 15 tests, all green
python -m unittest tests.test_phase1_active_gates -v         # Phase 1 sanity (18 tests)
python -c "from baby_strategies.funding_rate_mean_reversion_v1 import Strategy; print(Strategy())"
python -c "from baby_strategies.oi_confirmed_donchian_breakout_v1 import Strategy; print(Strategy())"
```

## Rollback

- `VOL_TARGET_ENABLED=0` disables the sizer entirely (flat-pass-through).
- `VOL_TARGET_SHADOW=1` computes the multiplier but returns flat (A/B logging only).
- The two new baby strategies emit no signals until explicitly enabled via the normal baby-strategy promotion path; merging this PR does not route production capital through them.

## Related memory

- `feedback_mutate_before_kill.md`
- `feedback_confidence_is_not_edge.md`
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `project_performance_reality.md`

# Strategy Factory v1 — Operating Spec (DRAFT)

**Date:** 2026-04-19
**Status:** proposal — awaiting external peer review (DeepSeek + Ollama cloud models)
**Authors:** Session-synthesized from 6 subagent audits + 4 external AI peer reviews + Copilot GITHUB_CLOUDAGENT_STRATS.MD v2 + Copilot's "Strategy Factory" 9-point framework
**Anchors:** [TESTING_PROTOCOL.MD](../TESTING_PROTOCOL.MD), [docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md](STRATEGY_INVESTIGATION_BEFORE_KILL.md), [docs/MUTATION_THREE_AXIS_PROTOCOL.md](MUTATION_THREE_AXIS_PROTOCOL.md), [docs/CRYPTO_PLAYBOOK_V3_2026_04_18.md](CRYPTO_PLAYBOOK_V3_2026_04_18.md)

## 0. Why this doc exists

Today's session produced:
- **Retraction** of the V1 crypto playbook (backtest stats labeled as live WRs)
- **V3 playbook** with zero approved combos post-Wilson + Bonferroni
- **Copilot v2** proposed 43 new strategies across 6 asset classes
- **Copilot challenge_v4.py** ready to deploy 10 strategies — but built on the same retracted backtest numbers
- **4 peer-reviewer AIs** unanimously calling for a validation gate before adding anything new

The repo currently has 400+ strategies, **0 of which pass Wilson LB > 50% with Bonferroni on realized data**. The problem is never going to be "we need more strategies." The problem is **strategies ship live without a rigorous gate that distinguishes signal from noise**. This doc defines that gate.

## 1. Promotion Ladder (non-negotiable)

Every strategy — existing or proposed — must climb this ladder. No exceptions, no lateral shortcuts.

| Stage | Name | Required to pass | Artifact |
|---|---|---|---|
| **S0** | Hypothesis | Written doc: what inefficiency, why now, what beats random | `docs/hypotheses/<strat>.md` |
| **S1** | In-Sample Backtest | 12m+ data, realistic fees/slippage, Sharpe > 1.0, max DD < 3× avg loss | `backtest_results/<strat>_IS.json` |
| **S2** | Out-of-Sample (OOS) | 70/15/15 split per TESTING_PROTOCOL Layer 2; OOS WR drift < 10pp vs IS | `backtest_results/<strat>_OOS.json` |
| **S3** | Walk-Forward | TESTING_PROTOCOL Layer 3; pass rate > 60% across walk-forward windows | `walk_forward_report.json` — must be < 7 days old |
| **S4** | Statistical Significance | Wilson 95% LB > 50% + Bonferroni correction across all tested combos | `significance_report.json` |
| **S5** | Monte Carlo / Robustness | **10,000 bootstrap sims**; 95% CI lower bound on Sharpe > 0.5; regime holds in ≥ 2 of 5 F&G buckets | `monte_carlo_<strat>.json` |
| **S6** | Forward Paper Test | **50 resolved trades minimum** before promotion consideration; realized WR must match S1-S5 prediction within 10pp | `forward_test_<strat>.json` |
| **S7** | Tiny Live | Max 0.25% risk/trade, max 3 trades/day; 30-day live window; must hold positive live Sharpe AND Wilson LB > 50% post-Bonferroni | `live_metrics_<strat>.json` |
| **S8** | Full Promotion | Passes all above; weekly kill-list check; auto-demote if any gate re-fails | Dashboard inclusion |

### Hard rejection rules
- Any stage fails → drop to **Rehabilitation Pipeline** (TESTING_PROTOCOL Section 7, rehab-first philosophy), NOT the graveyard
- Rehab order: cross-symbol → cross-asset → inverse → mutation grid → regime filter → crossover blend → graveyard (last resort)
- Never label a strategy "proven" if its evidence comes from `strategy_performance.json` (backtest ledger) rather than `closed_picks.json` (realized trades)

## 2. Multi-Asset Strategy Pyramid

**Do NOT build in crypto-only silo.** Current realized edge is strongest in non-crypto classes per dashboard tiles (ETFs 48.6%, Equities 52%, Commodities 20%, Crypto 28.3% aggregate). Structure:

### Tier 1 — Event-Driven (HIGHEST ROI, low competition)
Events dwarf fees and produce 3-15% move magnitudes that survive retail transaction costs.

| # | Strategy | Asset Class | Data Cost | TESTING stages to pass |
|---|---|---|---|---|
| 1 | **Token Unlock Event-Driven** (C5 from v2) | Crypto | Free (tokenunlocks.app) | S0-S7 mandatory |
| 2 | **Buyback Announcement Drift** (E10 from v2) | Equities | Free (SEC EDGAR) | S0-S7 mandatory |
| 3 | **FOMC Policy Surprise** (B3 from v2) | Bonds/Rates | Free (CME FedWatch) | S0-S7 mandatory |
| 4 | **Credit Rating Downgrade Drift** (E13 from v2) | Equities | Free (Moody's/S&P feeds) | S0-S7 mandatory |
| 5 | **Crypto Index Inclusion** (C8 from v2) | Crypto | Free (RSS) | S0-S7 mandatory |

### Tier 2 — Regime Gates (cross-asset filters, not standalone emitters)
These don't emit picks on their own; they gate when OTHER strategies fire.

| # | Strategy | Purpose |
|---|---|---|
| 6 | **Copper-Gold Ratio (HG=F/GC=F)** | Equity-LONG filter (risk-on detector) |
| 7 | **HYG-LQD Credit Spread** | Anti-crisis filter (credit leads equity 2-4w) |
| 8 | **VIX Term Structure** | Contango=go-long, Backwardation=defensive |
| 9 | **Fear & Greed 5-bucket** | Regime dimension per TESTING_PROTOCOL Layer 5 |
| 10 | **BTC/Alt Correlation Regime** | Crypto-side regime breakdown signal |

### Tier 3 — Structural (non-price-prediction; mechanical edge)
The hardest problem is price prediction. Structural edges come from market mechanics.

| # | Strategy | Asset Class |
|---|---|---|
| 11 | **Perp Funding Rate Mean-Reversion** (existing `funding_rate_scanner.py` — verify wired) | Crypto |
| 12 | **Futures Roll Yield Carry (FT1)** | Futures |
| 13 | **Cross-Sectional Altcoin Factor (C4)** | Crypto |
| 14 | **ETF NAV Premium/Discount (E7)** | ETFs |
| 15 | **Cointegrated Futures Pairs (FT4)** | Futures |

### Tier 4 — Ensemble/Meta (the repo's highest-leverage unused edge)
Your 6+ LLM agents produce independent picks. The **meta-signal when ≥4 agents unanimously agree** is rare but high-quality. Already observed in realized data: 3-way triple-aligned picks won today (DOGE SHORT, LINK SHORT, NEAR SHORT).

| # | Strategy | Required |
|---|---|---|
| 16 | **Unanimous Consensus (≥4 FRESH agents agree)** | Existing machinery: `cross_aggregation/super_signals.json` — just raise N threshold and verify freshness gate |

### EXPLICITLY NOT in v1
- Dealer GEX (C1): requires paid options chain
- Liquidation heatmap (C2): requires Coinglass paid tier
- Options dark pool flow (E11): Bloomberg-tier data
- Factor zoo (BAB, Quality, Accruals): arbitraged via smart-beta ETFs; not an edge at $10K
- Regime-conditional mutator: 2 of 3 peer reviewers rejected (DeepSeek: "solves weak signals by creating more weak signals")

## 3. Testing Mandate per Strategy

Every new strategy MUST satisfy **all of** these to reach S5:

### Data (Layer 0)
- 12+ months historical data at the strategy's native timeframe
- Adjusted prices (equities), UTC-normalized timestamps
- Transaction cost model: 10bps slippage + exchange fee + spread estimate per asset class

### Backtest (Layers 1-2)
- IS/OOS split 70/15/15
- No parameter peek on OOS
- Reject if OOS drifts > 10pp WR or > 20% Sharpe from IS

### Walk-Forward (Layer 3)
- Rolling 3-month training / 1-month test
- Pass rate > 60% of windows
- Fresh `walk_forward_report.json` (< 7 days old at promotion time)

### Statistical Significance (Layer 4)
- Wilson 95% LB > 50% on realized sample
- Bonferroni correction `alpha / k_tested_combos`
- Fisher combined p-value across family members

### Monte Carlo Robustness (Layer 5) — **MANDATORY**
- **10,000 bootstrap simulations** minimum (matches `institutional_backtest_suite --bootstrap-sims 10000` at TESTING_PROTOCOL line 205)
- 95% CI lower bound on Sharpe > 0.5
- 95% CI upper bound on max DD < 3× avg loss
- **FGI regime test**: strategy must show positive edge in ≥ 2 of 5 F&G buckets (Extreme Fear / Fear / Neutral / Greed / Extreme Greed)
- Shock scenarios: 3 labeled (COVID-March-2020, FTX-Nov-2022, March-2023 banking stress)

### Forward Test (Layer 6)
- ≥ 50 resolved trades in paper mode
- Live realized WR within 10pp of S1-S5 prediction
- Live Sharpe must be positive at sample n=50

### Promotion (Layer 7)
- Tiny live: 0.25% risk, max 3 trades/day, 30-day window
- Must hold Wilson LB > 50% post-Bonferroni during live window
- Auto-demote to Rehab on any gate re-fail (TESTING_PROTOCOL Section 7 auto-rehab trigger at WR < 35%)

## 4. Concrete Implementation Plan

### Week 1 — Build the gate itself
- New file: `alpha_engine/strategy_validation_gate.py`
  - Pure functions: `passes_S4(...)`, `passes_S5_monte_carlo(...)`, etc.
  - Reads ONLY `alpha_engine/data/closed_picks.json` for realized stats (NEVER `strategy_performance.json`)
  - Emits structured report per strategy
- New workflow: `.github/workflows/strategy-factory-validate.yml`
  - Runs on every PR that touches `alpha_engine/strategies/` or any `_strategy.py`
  - Fails the PR if the new/changed strategy can't produce a valid report

### Week 2 — Retroactively label existing strategies
- Run the gate over all 400+ strategies in `alpha_engine/`, `quan_engine/`, `genome/`, etc.
- Each gets a status: PROMOTED | PAPER-ONLY | REHAB | GRAVEYARD
- Publish the retroactive labeling to `docs/STRATEGY_FACTORY_INVENTORY.md`

### Week 3 — Build the top 5 event-driven strategies (Tier 1)
Only these reach S0/S1 in v1. Anything else waits.

1. Token Unlock (3 days)
2. Buyback Announcement (2 days)
3. FOMC Policy Surprise (3 days, includes CME FedWatch API integration)
4. Credit Rating Downgrade (2 days)
5. Crypto Index Inclusion (2 days)

Each must pass S0→S5 before entering Forward Test (S6). No S6→S7 promotion happens in Week 3.

### Week 4 — Build the regime gates (Tier 2)
These are filters, not emitters. They annotate every pick with regime context but don't produce signals.

### Months 2-3 — Forward-test graduated strategies
Only strategies that cleared S5 in Week 3-4 run S6. ~50 resolved trades each. Realistic throughput: 1-3 strategies reach S7 promotion per quarter.

## 5. Kill/Rehab Criteria (weekly)

Per TESTING_PROTOCOL Section 7 auto-rehab trigger:
- WR < 35% on n ≥ 10 realized → auto-route to Rehab Pipeline
- Rehab order: cross-symbol → cross-asset → inverse → mutation → regime → crossover
- Graveyard only after all 6 rehab axes fail

**Never retire a strategy without first documenting its Rehab attempt results.**

## 6. Integration with existing infrastructure

### Leverage these (don't re-build)
- `audit_trail/quality_gates.py` — already has Layer 2.5 gates (Score ≥ 40, Trust ≥ 4); this proposal makes them S2.5-S3 transition
- `alpha_engine/validation/institutional_backtest_suite` — already supports `--bootstrap-sims 10000` Monte Carlo (TESTING_PROTOCOL line 205); required for S5
- `alpha_engine/inverse_*.py` + `quan_engine_scalp_hybrid_inverse.py` — Rehab Pipeline's "inverse" axis infrastructure exists already
- `.github/workflows/walk-forward-backtest.yml` — Layer 3 already scheduled (Sundays 08:00 UTC); must be kept fresh (<7 days)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — S4/Rehab protocols

### What's missing (new work)
- The promotion gate wiring (Strategy Factory as CI check)
- S6 forward-test pipeline: TESTING_PROTOCOL flags `live_forward_test_picks.json = 0 picks` — this is the real blocker; fix before any new strategy reaches S6
- Monte Carlo report generator with F&G-regime decomposition
- Unified storage (merge MySQL non-crypto into closed_picks with `category` tag) — enables S4/S5 stats for non-crypto strategies

## 7. Hard Answer to Today's Question: Copilot's challenge_v4.py

**Reject as-is. Route to S0.**

Rationale:
- All 7 "proven" strategies use backtest numbers from `hyro_backtest_batch2.py` (S1 artifact, not S7)
- Enhanced-scoring ledger shows every one losing realized money (WR 24-37%, avg PnL negative)
- 3 new strategies (supertrend, keltner_momentum, hull_ma_cross) have ZERO realized data → not even S0

Response to Copilot: "Put challenge_v4.py in S0 state. Each of its 10 strategies needs S1-S5 validation against `closed_picks.json` with 10,000 bootstrap sims before any S6 paper-test entry. Expected pass rate at S4: 0-2 of 10 based on current realized distributions."

## 8. Success metrics (90 days post-adoption)

| Metric | Target |
|---|---|
| Strategies at S8 (live-promoted) | 2-5 |
| Strategies at S6 (paper-testing) | 8-15 |
| Strategies at S4-S5 | 15-25 |
| Strategies in Rehab | as many as fail S6 |
| Live dashboard active picks | 30-80 from S8 strategies (down from 267 raw / 12 filtered; fewer but trustworthy) |
| Realized WR (aggregate, 30d) | > 45% (vs today's 28% crypto, 48% ETF) |
| Wilson LB of top combo (realized) | > 52% |

If none of these targets hit in 90 days, the answer is "markets are currently too efficient for this stack; stand down to paper-only mode while hunting new market segments."

## 9. Open questions for peer review

- Is the S5 Monte Carlo bar (10k sims + 95% CI Sharpe > 0.5) too loose? Too tight?
- Should S6 require 50 resolved trades OR 3 months calendar, whichever comes first?
- For ensemble meta-strategy (Tier 4 #16), how do we prevent "consensus bias" where 4 agents all fed from the same underlying indicator?
- Is auto-demotion at any gate re-fail (S7 trigger) too aggressive? Should it be graduated (warn → demote → remove)?
- How do we prevent the Strategy Factory itself from becoming the next stale pipeline if the CI gate is bypassed via admin override?

---

## Review feedback — Cursor agent (2026-04-19)

1. **CI wiring:** §6 “what’s missing” should name a **single** follow-up issue: “Strategy promotion = required check on PRs touching `alpha_engine/*strategy*` or dashboard emitters” — else the factory stays documentation-only.
2. **S4 Bonferroni:** Clarify **k** (number of independent tests / combos) per run — dynamic k if the dashboard adds strategies weekly; stale k inflates false confidence.
3. **Correlation vs orthogonality:** Pair “ensemble Tier 4” with **quantified** ρ thresholds (v1.1 uses 0.7 in places; discovery protocol suggests 0.2 for novel templates — distinguish **ensemble internal** vs **library-wide**).
4. **Forward-test blocker:** The `live_forward_test_picks.json = 0` issue is correctly flagged as P0 — without S6 data, S1–S5 risk becoming theater; keep this visible in sprint planning.
5. **Cross-reference:** Link [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) for the discovery → promotion handoff and [QUANT_SIGNAL_ENGINE_FRAMEWORK_V1.md](QUANT_SIGNAL_ENGINE_FRAMEWORK_V1.md) for methodology JSON alignment.

## Review feedback — Kimi Code CLI (2026-04-19)

1. **S1 needs loss-driver screening before Monte Carlo.** The factory runs 10,000 bootstrap sims at S3, but if the strategy has a deterministic loser symbol (e.g., MATICUSDT at 0/913), the Monte Carlo is process theatre. Add a pre-S1 gate: `scripts/loss_driver_analyzer.py --strategy <name>` must show no symbol with n≥20 and WR=0%.
2. **Ensemble Tier 4: add the correlation guard.** The v1.1 amendments mention orthogonality checks (r < 0.7). Our `scripts/strategy_correlation_guard.py` implements this precisely — reference it in the factory spec and make it a mandatory S3 gate for ensemble strategies.
3. **Multi-Asset Pyramid data is stale.** Tier 2 claims "Current realized edge is strongest in non-crypto classes (ETFs 48.6%, Equities 52%)" but today's dashboard shows CRYPTO +108% and EQUITY +110% — crypto is competitive. The commodity/bond numbers are too sparse to claim any edge. Update the pyramid preamble with 2026-04-19 data.
4. **S0 hypothesis doc should cite asset-class-specific cost models.** The factory references realistic fees but doesn't specify per-asset-class assumptions. Cite the table from `scripts/strategy_correlation_guard.py` documentation: crypto 0.34%, forex 0.06%, equity 0.08%, commodity futures 0.36%.
5. **Promotion ladder needs a "data desert" exception.** For asset classes with <100 total resolved trades (commodity: 250, bond: 12), S4-S7 thresholds are statistically meaningless. Add a footnote: "Asset classes with <100 resolved trades across all strategies are ineligible for full promotion until data depth improves. Sandbox-only deployment."

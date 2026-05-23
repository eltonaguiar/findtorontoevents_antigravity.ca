# Strategy Factory v1.1 — Amendments After 4-AI Peer Review

**Date:** 2026-04-19
**Status:** amendments to [docs/STRATEGY_FACTORY_V1_PROPOSAL.md](STRATEGY_FACTORY_V1_PROPOSAL.md)
**Reviewers:** DeepSeek-chat, DeepSeek-v3.1:671b, GLM-4.6, Gemma3:27b

## 1. The 4-way consensus

### Unanimous (all 4 reviewers)

| Finding | Quote |
|---|---|
| **S5 Monte Carlo Sharpe > 0.5 is too loose** | "Mediocre, feels like a consolation prize" (GLM) — "Dangerously loose" (DS-v3.1) — "Easily achievable with overfitting" (Gemma) — "Meaningless without regime-adjusted benchmarks" (DS-chat) |
| **Ensemble Tier 4 needs orthogonality check** | "The spec is silent" (GLM) — "Mandate distinct orthogonal feature set" (DS-v3.1) — "Dependency graph essential" (Gemma) — "Correlation > 0.7 disqualifies" (DS-chat) |
| **Missing foundational data-integrity audit** | "Before any strategy touches the data" (GLM) — "Backtest data integrity check before S1" (Gemma) — "Live-vs-backtest hash firebreak" (DS-v3.1) — "Transaction-cost + slippage replay missing" (DS-chat) |

### Biggest structural flaw (4 variations, same thesis)

- **DS-chat**: "Over-reliance on pre-live metrics"
- **DS-v3.1**: "Over-engineered backtest optimizer, not a validation pipeline. No amount of in-sample rigor can validate a strategy; only live trading can."
- **Gemma**: "Pushing strategies through a statistically rigorous pipeline built on potentially flawed data is garbage in, garbage out."
- **GLM**: "Bureaucratic bottleneck. The problem isn't a lack of process; it's a lack of signal. This complex pipeline won't create signal from noise."

**Synthesis**: 5 pre-live stages (S1-S5) for validating strategies that ultimately fail in live is process theatre. Collapse the ladder, reduce friction on the stages that actually produce evidence (S6 forward test, S7 live).

## 2. Divergent views

### S6 = 50 resolved trades?

| Reviewer | Position |
|---|---|
| DS-chat | Reduce to 20 + regime check |
| DS-v3.1 | **Keep. If challenge is impossible at 50, strategy is wrong for challenge.** |
| Gemma | Reduce to 20-30 or time-based (2 weeks) |
| GLM | **Asset-class specific** — daily+ at 50, event-driven at much less |

**Winner: GLM's compromise.** Asset-class-specific thresholds thread the needle between DS-v3.1's rigor and the fact that Tier-1 event strategies (FOMC, credit downgrades) genuinely fire only a few times per year.

### Auto-demote at S7 re-fail — too aggressive?

| Reviewer | Position |
|---|---|
| DS-chat | Aggressive OK + 5-trade grace for prior-strong |
| DS-v3.1 | **Essential, do NOT gradualize** |
| Gemma | Too aggressive, graduated tiers |
| GLM | **Not aggressive enough — apply to S8 too, immediate** |

**Winner: DS-v3.1 / GLM harder position.** Split: immediate for priorly-weak strategies (S6 Sharpe < 1.0); 5-trade grace only for priorly-strong (S6 Sharpe ≥ 1.0).

### Weakest Tier 1 strategy
3 different answers — DS-chat & Gemma pick Token Unlocks, DS-v3.1 picks Credit Downgrades, GLM picks Index Inclusion. **Read: every Tier 1 candidate has a real weakness.** Require event-study calibration (90d pre/post) per strategy before accepting Tier 1 status. If any of these cannot produce clean event-window stats with n ≥ 30 historical events, drop it.

## 3. v1.1 amended ladder (collapsed, simpler)

Reduced from 8 stages to 6 with explicit foundational gates:

| Stage | Name | Purpose |
|---|---|---|
| **S0** | Hypothesis | Written doc: what inefficiency, why now, what beats random |
| **S0.5** | **Data Integrity Audit (NEW — Gemma + GLM)** | Completeness ≥99%, outlier rate <3%, ADF stationarity on returns, survivorship-bias check, timestamp UTC normalization validated. Fails = no further work. |
| **S1** | Backtest + Transaction Cost Replay **(NEW — DS-chat)** | IS backtest with L2/trade-data slippage replay for holdings <1day. Fees + spread + order-book impact. Sharpe > 1.0 realistic. |
| **S2** | OOS + Walk-Forward + Statistical Significance (merge former S2-S4) | 70/15/15 split, walk-forward pass >60%, Wilson LB > 50% + Bonferroni |
| **S3** | Monte Carlo Robustness **(TIGHTENED)** | 10k bootstrap sims, **Sharpe > 1.0** (was 0.5), **max DD < 2× avg loss inside sims** (new), **≥4 of 5 F&G regimes profitable** (was ≥2), 3 shock scenarios (COVID/FTX/SVB). **Ensemble strategies also face orthogonality check (NEW)**: pairwise feature correlation among agents must be r < 0.7. |
| **S4** | Forward Paper Test (was S6) — **asset-class-specific thresholds (NEW — GLM)** | • Sub-daily crypto/FX: **50 resolved trades** OR 30d calendar, whichever first • Daily equity: 30 trades OR 60d calendar • Event-driven (Tier 1): **10 events** OR 180d calendar (acknowledges FOMC/downgrade cadence) • Realized WR within 10pp of S2 prediction required regardless |
| **S5** | Tiny Live + Live Data Hash Firebreak **(NEW — DS-v3.1)** | 0.25% risk, max 3 trades/day, 30d. **Pre-trade hash check: live data must match backtest data schema.** If backtest was on BTCUSDT Binance 1h and live feed changed to BTC-PERP or different venue — halt. Must hold Wilson LB > 50% post-Bonferroni in live window. |
| **S6** | Full Promotion | All above + weekly kill-list check. **Auto-demote on any gate re-fail: immediate for strategies with prior S4 Sharpe < 1.0; 5-trade grace for Sharpe ≥ 1.0.** |

Net effect: **5 hard gates instead of 8**, each with explicit data integrity, foundational validation, or live-reality check. GLM's core critique (bottleneck) addressed by collapsing redundant pre-live stages into one (S2).

## 4. Explicitly acknowledge what v1.1 doesn't fix

Reviewers' "biggest flaw" quotes all centre on the same point: **pre-live validation fundamentally cannot certify live performance**. v1.1 still has 4 pre-live gates (S0-S3). It makes them less demanding of process time while keeping them honest, but it cannot make them predictive.

This is why **S4 (forward paper) and S5 (tiny live) remain the real gates.** The other 4 stages are filters that disqualify obviously-bad ideas cheaply, not promote good ones.

**Rename S0-S3 to "pre-filter stages." Rename S4-S6 to "promotion stages."** This is a doc change, but the vocabulary shift is load-bearing: it prevents anyone reading the spec from treating S3 Monte Carlo success as evidence of live viability.

## 5. Explicit decision on the HyroTrader $10K challenge

Following DS-v3.1's hard position (reinforced by today's earlier conclusion):
- HyroTrader 10-day window × realistic 3 trades/day = 30 trades maximum
- Tier 1 event-driven strategies fire less than 10 times/year on most events
- **S4 requires 50 resolved sub-daily OR 10 events** — neither is achievable inside a 10-day challenge
- **Therefore: the Strategy Factory is INCOMPATIBLE with short-window prop challenges. Explicitly acknowledge this.**

**Action**: add a note to `docs/HYROTRADER_CHALLENGE_STRATEGY.md` stating the v1.1 spec supersedes it. No new strategy enters HyroTrader without also entering the Strategy Factory — which will take ≥6 months to promote to S5/S6. Therefore: **HyroTrader challenge is effectively retired as a live-trading venue.** Paper-trade mode only, for signal-validation purposes, if used at all.

## 6. Event-study calibration requirement (NEW — resolves weakest-Tier-1 debate)

Since 3 of 4 reviewers disagreed on which Tier 1 event was weakest, add universal requirement:

Before any Tier 1 strategy reaches S1, produce `docs/event_studies/<strategy>_study.md` containing:
- 90-day pre/post event price windows, n ≥ 30 historical events
- Cumulative abnormal return (CAR) with significance vs null
- Variance of CAR across events (if high, timing risk dominates)
- Liquidity filter analysis: does edge survive below-median-volume events?
- Pre-emption check: does price already move in expected direction during 72h pre-event? (If yes, market-makers front-run and retail has no edge)

Any Tier 1 strategy where CAR is not distinguishable from zero at p<0.05 after pre-emption adjustment is demoted to hypothesis-only (S0, paused indefinitely).

## 7. What to do with existing strategies today

Per v1.1:
1. **Stop promoting on backtest evidence.** Every existing strategy with "proven" in its name gets reclassified as S0 until re-validated.
2. **Run S0.5 data integrity audit** on `alpha_engine/data/closed_picks.json` FIRST (ADF stationarity, outlier rate, survivorship check). This takes priority over any new strategy work.
3. **Retroactively apply S1-S3 to the 400+ existing strategies**. Publish `docs/STRATEGY_FACTORY_INVENTORY.md` with each strategy's stage. Most will be S0 (no hypothesis doc) or S1 (backtest evidence exists but was never OOS-validated).
4. **Forward paper test (S4) the surviving subset** for 30+ days before any live deployment consideration.

Expected outcome: **2-5 strategies reach S5 within 90 days.** This is the right number. More than that = gate is broken or we're lucky.

## 8. Response to Copilot's challenge_v4

v1.1 decision: **Reject harder than v1.0.**
- challenge_v4's "proven" strategies use backtest ledger stats = fails S0.5 data-integrity hash check (backtest-ledger ≠ closed_picks; you cannot mix evidence bases)
- 3 new strategies (supertrend, keltner, hull) have no hypothesis docs = S0 at best
- Expected stage distribution if challenge_v4 enters the factory: 10 of 10 at S0 pending data-integrity rework

Response to Copilot PR: **"Do not merge. Route all 10 strategies to S0. Each needs a hypothesis doc, data-integrity passing S0.5 against realized data, event-study calibration if Tier 1. Estimated time to first S4 entry: 90 days at earliest. Challenge_v4 cannot ship live under v1.1; it can exist as a documented hypothesis set."**

## 9. Open questions (unanswered, remain for v1.2)

- S0.5 data integrity failing on `closed_picks.json` would freeze everything. What's the remediation if integrity check fails? (Likely: purge bad rows like MATIC, re-run.)
- Monte Carlo sim with 10k draws × 5 regimes × 3 shock scenarios = ~150k total evaluations per strategy. Compute budget?
- Ensemble orthogonality check requires feature introspection from LLM agents. Not all agents expose their features. How do we audit?
- "Auto-demote with 5-trade grace" — what's the grace reset condition?

## 10. Commit plan

1. Commit this v1.1 amendments doc
2. Post a PR comment on copilot/research-other-strategies rejecting challenge_v4 per §8
3. Draft `docs/HYROTRADER_CHALLENGE_RETIRED.md` per §5
4. Begin S0.5 data integrity audit on closed_picks.json as a parallel workstream

---

## Review feedback — Cursor agent (2026-04-19)

1. **Collapsed ladder vs bureaucracy:** v1.1 correctly elevates S6/S7 evidence — add an explicit **WIP limit** (max N strategies in active S2–S5 at once) so inventory work doesn’t stall the pipeline.
2. **Orthogonality implementation:** §9 still lists ensemble audit as open — point to **`baby_strategies/correlation_prune_strategies.py`** on **daily returns** as the minimum viable orthogonality check until LLM feature export exists.
3. **S0.5 failure remediation:** Add a one-paragraph **playbook** (purge rows vs freeze promotions) under §9 open questions — operators need a default action.
4. **Inventory doc:** `STRATEGY_FACTORY_INVENTORY.md` should include **last evidence source** (`closed_picks` vs `strategy_performance`) per strategy to prevent mixed-evidence promotions.
5. **Alignment:** Cross-link [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) for pre-S0 discovery hygiene (novelty, costs, correlation CSV).

## Amendments from 2026-04-19 Mercury peer review

External AI reviewer (Mercury) proposed five tightenings to the v1.1 ladder. Each is incorporated below.

### 1. S5 Monte Carlo bar — rationale + tunability

- **Current:** 10k sims, 95% CI Sharpe > 0.5 (per §3 row S3 / forward-renumbered S5).
- **Rationale (Mercury):** 10k sims give ±0.05 Sharpe CI stability; a 0.5 lower-bound eliminates outlier-driven strategies while still admitting modest low-volatility edges such as carry and roll-yield.
- **Escape hatch:** If too many otherwise-valid candidates are being dropped, the bar may be relaxed to **0.4** or the sim count raised to **20k**. Any relaxation requires a written justification recorded in the strategy's hypothesis doc (S0 artifact).

### 2. S6 dual-threshold requirement

Replace any existing "50 resolved trades OR 3 months" phrasing with:

> **"≥50 resolved trades AND ≥30 calendar days elapsed (whichever is later), OR ≥90 calendar days elapsed (whichever hits first) — NEVER both thresholds satisfied in under 30 days."**

**Reason:** prevents trade-clustering false positives — 50 trades in a single week indicates a regime burst, not a durable edge. The 30-day floor guarantees at least one regime-change exposure window before promotion.

### 3. Tier-4 ensemble consensus diversity audit

Before an agreement among multi-agent signals counts as "consensus", run a diversity audit:

- Compute pairwise **Pearson correlation** of each agent's raw signal scores over the trailing 6 months.
- If any pair has **ρ > 0.7**, flag as "highly correlated" — those agents cannot count as independent votes.

**Weighting rule:** agreeing agents must span **≥2 distinct signal-source tags** drawn from: `price_action`, `fundamental`, `sentiment`, `on_chain`, `macro`.

**Implementation:** add a `signal_source_tag` field to each agent's config; the meta-signal fires only if the unique-tag-count among agreers is ≥ 2.

### 4. Graduated auto-demotion (replaces hard S7 auto-demote)

Instead of immediate demotion on any gate re-fail, escalate in 3 steps:

1. **Warn** — metric within 5pp of threshold → email + GitHub issue, no state change.
2. **Paper-only demotion** — warn persists across 2 consecutive evaluation windows (~14 days).
3. **Rehab retirement** — 3 consecutive demotions (~30 days) before graveyard.

This is more forgiving of transient regime shifts while still blocking slow-drift rot. Supersedes the "immediate auto-demote" language in §3 row S6 and the split resolution in §2.

### 5. Admin-override policy for CI gate

Any PR that modifies `alpha_engine/strategy_validation_gate.py` requires:

- **Two-person approval** — one senior engineer and one product owner.
- **Immutable audit entry** in `strategy_override_log` with timestamp, user, reason, and a **48-hour re-review deadline**.
- After the deadline, the overridden strategy must re-run the full **S0–S6 ladder** before live emission is restored.

**Technical safeguard:** add a GitHub Actions job that fails CI if `strategy_validation_gate.py` is modified without a matching test-suite update in the same PR.

## Review feedback — Kimi Code CLI (2026-04-19)

1. **S0.5 Data Integrity Audit: add "deterministic loss" check.** Before any data integrity audit completes, run `scripts/loss_driver_analyzer.py --strategy <name>` to check for symbol-specific deterministic losses (n≥20, WR=0%). This is a data-quality signal, not an edge signal — it indicates venue/symbol mismatch, delisting, or vocabulary errors.
2. **S3 Monte Carlo: Sharpe > 1.0 is good, but add loss-concentration check.** A strategy can pass Sharpe > 1.0 if one big winner offsets many small losses. But if 80% of losses come from one symbol, the strategy is not robust. Require: no single symbol contributes >30% of total loss magnitude in the bootstrap sims.
3. **S4 Forward Paper: asset-class-specific thresholds are well-designed, but add "data depth" precondition.** Event-driven strategies (FOMC, downgrades) need 10 events — but if the asset class has <100 total resolved trades across ALL strategies, even 10 events may not be statistically meaningful. Add: "Asset class must have ≥100 resolved trades in `closed_picks.json` before any strategy in that class advances to S4."
4. **S5 Tiny Live: the data hash firebreak is excellent.** Reinforce it with a concrete example: "If backtest was on Binance BTCUSDT 1h spot and live feed is Binance BTCUSDT perpetual, schema matches but funding-rate mechanics differ — halt and re-validate."
5. **Rename S0-S3 to "pre-filter stages" and S4-S6 to "promotion stages."** The v1.1 doc mentions this rename in §4 but doesn't apply it throughout the tables. Do the rename — it's load-bearing vocabulary that prevents process theatre.


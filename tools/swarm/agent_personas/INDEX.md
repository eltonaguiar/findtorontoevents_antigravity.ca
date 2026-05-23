# Asset-Class Specialist Personas — Index

Six per-asset-class personas for the quant pick swarm. Each file is a self-contained agent definition (YAML frontmatter + edge sources, tests, kill rules, benchmarks, blocked patterns). Source briefing: `swarm_runs/briefing_asset_class_audit.md`. Source consensus: `swarm_runs/20260503T132558Z/CONSENSUS.md`. Forward-edge data: `reports/forward_edge_audit_2026-05-02.md`. Tier framework: `reports/HEDGE_FUND_AUDIT_REPORT_2026_05_02.md`.

## How to use

Wired into the swarm via `--persona <NAME>` on `worker_runner.py` and `swarm_run.py`. The persona body (frontmatter stripped) is prepended to the task prompt as a system-style preamble, so the engine answers under the persona contract.

Single engine:

```
python tools/swarm/worker_runner.py \
    --engine deepseek \
    --prompt-file swarm_runs/_persona_smoke.md \
    --out-file swarm_runs/_persona_smoke.json \
    --persona crypto-specialist
```

Fleet (CLI default; per-engine YAML overrides):

```
python tools/swarm/swarm_run.py \
    --prompt-file swarm_runs/_persona_smoke.md \
    --engines deepseek,xai \
    --persona crypto-specialist \
    --max-parallel 2
```

YAML schema (per-engine `persona:` beats top-level `persona:` beats `--persona` CLI):

```yaml
persona: ml-validation-specialist
engines:
  - name: deepseek
    persona: regime-specialist
  - name: xai
```

Resolution order: `<NAME>.md` -> `<NAME>_specialist.md` -> hyphen-to-underscore-normalized variants -> path. A typo raises `FileNotFoundError` (loud-fail). Full spec: `tools/swarm/SPEC.md` -> "Persona injection".

| Persona | File | One-line description | When to invoke |
|---|---|---|---|
| bond-specialist | `bond_specialist.md` | Thin-sample steward; merge-to-ETF default; documents the DeepSeek/xAI dissent (DeepSeek "merge until n>=100" wins). | Treasury futures, yield-curve trades, anything touching `asset_class_health.BOND` (n=18, thin_sample). Default action: route to ETF. |
| commodity-specialist | `commodity_specialist.md` | COT-commercial + term-structure futures gatekeeper. | All futures picks (GC=F, SI=F, HG=F, CT=F, KC=F, ZC=F, etc.), anything touching `asset_class_health.COMMODITY` (PF 1.78 / WR 46.9% / n=750, meets T2 PF). |
| crypto-specialist | `crypto_specialist.md` | Sentiment-regime + ATR-percentile + mutated-MACD/RSI gatekeeper; volume-concentration auditor. | All CRYPTO picks, source-system audits, anything touching `asset_class_health.CRYPTO` (PF 1.24 / WR 44.6% / n=8188, sub-T2 from volume dilution). |
| equity-specialist | `equity_specialist.md` | US single-stock RS-breakout / vol-contraction / factor-momentum reviewer. | Single-name US equity picks, factor exposure changes, anything touching `asset_class_health.EQUITY` (PF 1.41 / WR 52.9% / n=420, T2-candidate). |
| etf-specialist | `etf_specialist.md` | Sector-rotation + intermarket-flow reviewer; charter-floor (n<100) escalator. | Sector / thematic ETF picks (XLK, XLE, IWM, MTUM, RSP), anything touching `asset_class_health.ETF` (PF 1.24 / WR 55.2% / n=87 — still below charter floor, but 30d window is best in system). |
| forex-specialist | `forex_specialist.md` | FOREX rescue-protocol owner; mutate-before-kill enforcer; JPY-cross gate steward. | All FX picks, JPY-cross routing, carry/term-structure proposals, anything touching `asset_class_health.FOREX` (PF 0.27 / WR 46.4% / n=1169, genuinely sub-floor). |
| ml-validation-specialist | `ml-validation-specialist.md` | Model-gating layer over existing strategies — DSR / PSR / MinTRL / Bonferroni-Holm; rejects any Sharpe that doesn't survive multiple-testing correction at α=0.05. | Any reported Sharpe/PF/WR without an `n`, before promoting paper→live, after every genetic_programmer / mutation pipeline output, and on backtests that lack purged-CV / embargo. |
| regime-specialist | `regime-specialist.md` | Regime-conditional strategy gating (HMM + BOCPD + Hurst + GARCH); rejects strategies that confound regime with skill or whose classifier emits same state >95% of bars. | Strategies claiming edge without regime conditioning, "range_bound everywhere" classifier output, regime-routing or regime-sized-position proposals, single-regime backtests. |

## Kimi-dim-inspired personas (added 2026-05-03)

Five new personas extracted from the Kimi Agent Swarm 12-dimension prediction-edge audit (`quant_audit_dim01.md` through `quant_audit_dim12.md` plus `quant_audit_cross_verification.md` and `quant_audit_insight.md`). Each persona replicates a specific Kimi analytic move; cite the dim source in any output.

| Persona | File | One-line description | Kimi dim |
|---|---|---|---|
| score-methodology-auditor | `score-methodology-auditor.md` | Audits F-Score / `ml_score` / `confidence` / `elite_score` / `blended_conf` / Beta Confluence for correlation-with-WR + decile monotonicity; rejects non-monotonic composites. | dim02 |
| cross-verification-auditor | `cross-verification-auditor.md` | Replicates Kimi Phase 4 + 6 — classifies claims HIGH/MEDIUM/LOW by orthogonal-source corroboration; surfaces conflict zones with resolution path. | cross_verification + insight |
| risk-of-ruin-assessor | `risk-of-ruin-assessor.md` | Lottery-payoff / penny / meme / S-Tier-thin gate; computes empirical risk-of-ruin and Kelly-fraction sign; blocks negative-Kelly allocations. | dim06 + dim07 + dim08 |
| rr-band-optimizer | `rr-band-optimizer.md` | Stratifies proposals by R:R band; enforces 1.5-2.0R sweet spot (PF 5.81) vs >2.0R catastrophic band (PF 0.35); recommends 2.0R hard cap. | dim01 §8 + dim08 §1 |
| transaction-cost-modeler | `transaction-cost-modeler.md` | Asset-class-specific cost modeling (spread + commission + slippage + market impact); re-derives net PF; flags cost-sunk strategies. | dim05 §1 + dim12 |

## Frontend multi-specialist debugging personas (added 2026-05-04)

Four new personas extracted from the Kimi filter-bug run (`reports/kimi_filter_bug_2026_05_04/`) that found the `stopImmediatePropagation`-swallows-synthetic-click bug our single-prompt swarm missed in PRs #746-#748. Use the multi-specialist split (race + datetime + dom + coordinator) for frontend bugs with multi-system symptoms; do NOT collapse into one generalist reviewer.

| Persona | File | One-line description | Kimi role |
|---|---|---|---|
| race-condition-specialist | `race_condition_specialist.md` | Capture-phase listener / `stopImmediatePropagation` / synthetic-click / mutator re-entrancy / global flag race auditor; mandates `e.isTrusted` guards and global mutexes on multi-source `applyFilters`-style mutators. | audit_report.md |
| datetime-timezone-specialist | `datetime_timezone_specialist.md` | UTC↔local / ISO-parse / year-wrap / "today" / multi-day-overlap auditor; tests Dec→Jan AND Jan→Feb boundaries; replaces `new Date(iso).toDateString()` with `isoDateStringToYMD`. | date_bugs_report.md |
| react-dom-specialist | `react_dom_specialist.md` | Vanilla-JS↔React seam auditor; flags inline-style mutations on React-owned nodes, MutationObserver self-loops, fragile sibling-positional guards, lazy-load debounce too-short, rAF hydration polling. | react_dom_mutation_observer_analysis.md |
| coordinator-synthesizer | `coordinator_synthesizer.md` | Merges specialist outputs into one ranked plan; demands `file:line` cites; buckets fixes by Immediate/This-Week/Next-Sprint deploy-readiness; never generates new findings. | FINDINGS.md + plan.md |

Strategy doc: `multi_specialist_debugging_strategy.md` — when to use, phases, required outputs, worked example (the filter bug), and what NOT to do.

## Mission-critical operational personas (2026-05-04)

Eight new `type: operational` personas materialized from the user spec + Mercury enhancements (`feat/mission-critical-personas-2026-05-04`). These differ from analytical specialists: they own a live operational surface (front-door site, resolver, sports monitor, failover layer, swarm itself) and emit structured-JSON handoff blocks per `ROUTER_ARCHITECTURE.md` §2. Do NOT collapse them into existing specialists — they cover seams between domains. NOTE: `_registry.yaml` updates for these are owned by the parallel Phase-1 router subagent and will be reconciled after that lands.

| Persona | File | One-line description | Priority lane |
|---|---|---|---|
| event-surface-engineer | `event_surface_engineer.md` | Owns findtorontoevents.ca filtering / display / cache-warm fallback; front-door custodian for events.json freshness. | event-freshness |
| audit-resolver-v2 | `audit_resolver_v2.md` | Maintains the 2026-04-28 resolver thresholds (CRYPTO 0.1bp / non-crypto 5bp); self-heal loop on PF divergence >0.3. | audit-integrity |
| cross-asset-quant | `cross_asset_quant.md` | Cross-sectional analyst with cross-asset risk budget; gates Sharpe behind DSR for n<200. | audit-integrity |
| sports-odds-survivor | `sports_odds_survivor.md` | Keeps NHL/NBA/NFL/UFC/OLG monitor alive on free APIs; auto-swaps to paid mirror when primary stalls >15min. | monitor-uptime |
| tier-gate-keeper | `tier_gate_keeper.md` | Enforces T1/T2/T3 thresholds; mutate-before-kill gate; re-classification review queue for boundary cases. | audit-integrity |
| failover-infrastructure-tech | `failover_infrastructure_tech.md` | Universal "what happens when X dies" layer; circuit breakers + degraded UI + TTR telemetry. | monitor-uptime |
| agent-swarm-orchestrator | `agent_swarm_orchestrator.md` | Meta-persona: detects conflicting handoffs, enforces priority matrix (audit-integrity > monitor-uptime > event-freshness), writes conflict-resolution tickets. | audit-integrity |
| forex-diagnostic-surgeon | `forex_diagnostic_surgeon.md` | Three-phase FOREX investigation (root-cause / resolver-impact / kill-decision) per investigate-before-kill + mutate-before-kill. | audit-integrity |

Aspirational handoff targets that don't yet exist (tracked here for follow-up):
- `data-validator-specialist` — referenced by `event-surface-engineer`; for now routes to `audit-resolver-v2` as nearest-neighbor.
- `risk-quant-specialist` — referenced by `audit-resolver-v2`; for now routes to `cross-asset-quant`.

## Cross-cutting protocol references

- Mutate-before-kill: `docs/MUTATION_THREE_AXIS_PROTOCOL.md` and `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
- Resolver-v2 thresholds: CRYPTO 0.1bp / non-crypto 5bp (`alpha_engine/outcome_resolver.py:115-126`).
- Concentration cap: 15% per strategy (20% for ETF) of asset-class volume, enforced at execution layer.
- Forward-edge gates: after-cost mean PnL > 0 AND Wilson 95% LB on WR >= 50% AND n>=10. Currently 5 strategies system-wide pass both.
- Tier framework: T1 = PF>2 / WR>55 / MDD<10; T2 = PF>1.5 / WR>50 / MDD<20; T3 = PF>1.2 / WR>48 / MDD<30. Charter floor n>=100 for any tier verdict.


## Invented personas — frontend-filter-bug (generated)

Generated by `tools/swarm/invent_personas.py` (see `INVENT_PERSONAS_PROTOCOL.md`).
Blueprint: `blueprints/frontend-filter-bug_blueprint.md`.

| Persona | File | One-line description | Source |
|---|---|---|---|
| data-drift-specialist | `data_drift_specialist.md` | Detects and quantifies mismatches between data feeds that drive filtering logic. | invented |
| overlay-ui-specialist | `overlay_ui_specialist.md` | Evaluates UI overlay implementation that stamps next‑month badges over React‑rendered dates. | invented |
| filter-logic-specialist | `filter_logic_specialist.md` | Audits imperative filter guards in index.html for null‑eventData paths and date‑parsing fallbacks. | invented |
| filter-bug-coordinator-synthesizer | `filter_bug_coordinator_synthesizer.md` | Aggregates specialist reports, resolves overlaps, and produces a prioritized findings document. | invented (coordinator) |

## Asset-class operational personas (2026-05-04, batch A: crypto/equity/forex/commodity)

Twenty new `type: asset-class` personas materialized from Mercury's 2026-05-04 brief, batch A (crypto + equity + forex + commodity). Five roles per class: `data-engineer`, `feature-engineer`, `quant-analyst`, `risk-manager`, `model-ops-engineer`. ETF / Bond / Futures + cross-class personas are owned by parallel batch B (below).

| Persona | File | One-line description | Asset class / role |
|---|---|---|---|
| crypto-data-engineer | `crypto_data_engineer.md` | Feed consolidation across Binance/KuCoin/CoinGecko, dedup, gap-fill, timestamp alignment, real-time tick sanity. | crypto / data-engineer |
| crypto-feature-engineer | `crypto_feature_engineer.md` | On-chain + sentiment + vol-adjusted features; primary KPI lift CRYPTO Sharpe -0.088 → >0. | crypto / feature-engineer |
| crypto-quant-analyst | `crypto_quant_analyst.md` | Regime-aware backtests (high-vol vs low-vol), HPO, model-family bake-off (transformer vs GBM). | crypto / quant-analyst |
| crypto-risk-manager | `crypto_risk_manager.md` | Worst-fold WR=0% elimination, position caps, ATR-based stops, quan_engine-drag curbs. | crypto / risk-manager |
| crypto-model-ops-engineer | `crypto_model_ops_engineer.md` | Inference latency, drift monitoring (PSI/KS), automated retraining + A/B + rollback. | crypto / model-ops-engineer |
| equity-data-engineer | `equity_data_engineer.md` | Corporate actions, fundamentals, HF prices, survivorship-bias resolution, exchange/timezone alignment. | equity / data-engineer |
| equity-feature-engineer | `equity_feature_engineer.md` | Value/momentum/quality factors + sector exposure neutralization; preserves WR 57.9% (Sharpe 3.527 flagged for live verification). | equity / feature-engineer |
| equity-quant-analyst | `equity_quant_analyst.md` | Walk-forward CV n=47, decay 0.2, ensemble methods to lift consistency >66%. | equity / quant-analyst |
| equity-risk-manager | `equity_risk_manager.md` | Sector concentration, beta exposure, MDD <10% (T1 target). | equity / risk-manager |
| equity-model-ops-engineer | `equity_model_ops_engineer.md` | Nightly retrain, model versioning, A/B on live traffic. | equity / model-ops-engineer |
| forex-data-engineer | `forex_data_engineer.md` | Spot+forward aggregation, holiday handling, pip-vs-point convention reconciliation. | forex / data-engineer |
| forex-feature-engineer | `forex_feature_engineer.md` | Rate diff, CPI/PMI, carry-to-vol, COT commercial; rescue PF 0.27. | forex / feature-engineer |
| forex-quant-analyst | `forex_quant_analyst.md` | Diagnoses decay-0.1-Sharpe-(-1.406) paradox; LSTM test; mandatory handoff to forex-diagnostic-surgeon. | forex / quant-analyst |
| forex-risk-manager | `forex_risk_manager.md` | Tight stops, position caps, prevent worst-fold WR=0%. | forex / risk-manager |
| forex-model-ops-engineer | `forex_model_ops_engineer.md` | Real-time inference <10ms, drift monitoring, rollback playbook. | forex / model-ops-engineer |
| commodity-data-engineer | `commodity_data_engineer.md` | Futures curves, inventory reports, roll-yield, contract-roll logic. | commodity / data-engineer |
| commodity-feature-engineer | `commodity_feature_engineer.md` | Term-structure (contango/backwardation), seasonality, BCOM, COT positioning. | commodity / feature-engineer |
| commodity-quant-analyst | `commodity_quant_analyst.md` | Investigates Sharpe -2.412 paradox vs PF 1.78; supply-shock vs demand regimes. | commodity / quant-analyst |
| commodity-risk-manager | `commodity_risk_manager.md` | Roll-yield exposure, inventory shocks, fat-tail VaR caps. | commodity / risk-manager |
| commodity-model-ops-engineer | `commodity_model_ops_engineer.md` | Automated roll-over, EIA/WASDE-window latency, drift / A/B / rollback. | commodity / model-ops-engineer |

All batch-A personas default to `priority_lane: audit-integrity` and emit the structured-JSON handoff block per `ROUTER_ARCHITECTURE.md` §2. Forex personas route kill/iterate/reclassify decisions through `forex-diagnostic-surgeon` (mandatory).

## Asset-class & cross-class operational personas (2026-05-04, batch B: etf/bond/futures + emerging + support)

22 personas materializing per-asset-class operational roles for ETF/Bond/Futures plus emerging-asset and cross-class support functions. Subagent A covers the parallel Crypto/Equity/Forex/Commodity batch. Branch: `feat/asset-class-personas-B-2026-05-04`.

| Persona | File | One-line description | Class / role |
|---|---|---|---|
| etf-data-engineer | `etf_data_engineer.md` | Index constituents, expense ratios, tracking-error data, corporate actions reconciliation. | etf / data-engineer |
| etf-feature-engineer | `etf_feature_engineer.md` | Sector/industry tilts, style exposures, liquidity metrics. | etf / feature-engineer |
| etf-quant-analyst | `etf_quant_analyst.md` | Tracking-error optimization, factor-tilt model; lift PF >1.24 toward T2. | etf / quant-analyst |
| etf-risk-manager | `etf_risk_manager.md` | Liquidity + concentration risk, premium/discount stress. | etf / risk-manager |
| etf-model-ops-engineer | `etf_model_ops_engineer.md` | Daily rebalance pipeline, version registry, rollback. | etf / model-ops-engineer |
| bond-data-engineer | `bond_data_engineer.md` | Yield curves, credit spreads, day-count normalization. | bond / data-engineer |
| bond-feature-engineer | `bond_feature_engineer.md` | Duration, convexity, FOMC/inflation surprise features. | bond / feature-engineer |
| bond-quant-analyst | `bond_quant_analyst.md` | Validate PF 1.72 holds at scale; grow n=18 → 100. | bond / quant-analyst |
| bond-risk-manager | `bond_risk_manager.md` | Rate + credit limits, curve-shock stress. | bond / risk-manager |
| bond-model-ops-engineer | `bond_model_ops_engineer.md` | Daily curve-fitting, low-frequency drift monitoring. | bond / model-ops-engineer |
| futures-data-engineer | `futures_data_engineer.md` | Symbol standardization, roll-over logic, expiry handling. | futures / data-engineer |
| futures-feature-engineer | `futures_feature_engineer.md` | Roll-yield, basis, term-structure, seasonality, COT. | futures / feature-engineer |
| futures-quant-analyst | `futures_quant_analyst.md` | Cross-asset futures (energy / metals / ags / financial). | futures / quant-analyst |
| futures-risk-manager | `futures_risk_manager.md` | Margin, limit-up/down, delivery-month constraints. | futures / risk-manager |
| futures-model-ops-engineer | `futures_model_ops_engineer.md` | Low-latency intraday inference, GLOBEX scheduling. | futures / model-ops-engineer |
| asset-discovery-engineer | `asset_discovery_engineer.md` | Research new data sources, prototype pipelines, go/no-go memos. | emerging / discovery |
| cross-asset-analyst | `cross_asset_analyst.md` | Correlation, diversification benefit, spillover effects. | cross / analyst |
| model-explainability-engineer | `model_explainability_engineer.md` | SHAP/LIME insights for under-performing classes. | cross / explainability |
| performance-debugger | `performance_debugger.md` | Walk-forward worst-fold triage; routes tickets to per-class quant. | cross / debugger |
| data-quality-auditor | `data_quality_auditor.md` | Schema, outliers, point-in-time leakage tests across pipelines. | cross / auditor |
| mlops-lead | `mlops_lead.md` | Cross-class registry, deploy standards, monitoring substrate. | cross / mlops-lead |
| risk-governance-officer | `risk_governance_officer.md` | Enforces tier MDD floors (T1<10% / T2<20% / T3<30%) across classes. | cross / governance |

Cross-class seam note: `mlops-lead` owns the substrate (registry, deploy standards, cross-class monitoring); per-class `*-model-ops-engineer` personas own pipeline execution within their class. Governance escalations chain through `risk-governance-officer` → `tier-gate-keeper` for any kill/demote action.

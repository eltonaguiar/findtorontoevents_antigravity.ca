## 9. Implementation Roadmap

The preceding eight chapters established the diagnostic and prescriptive foundation. Chapter 1 identified Crypto C-Tier as a -46.59% value destroyer requiring immediate suspension [^1^]. Chapter 3 traced the forex 0% WR to a measurement artifact and projected T3 confirmation by Week 4 [^2^]. Chapter 4 determined that bond `elite_score` floor reduction from 30 to 15 would unblock 3–5 picks monthly [^3^]. Chapter 5 quantified +969.50% in killed alpha from over-restrictive gates [^4^]. Chapter 6 catalogued 37 data integrity issues across `outcome_resolver.py`, `hc_filter.js`, and `hedge_fund_quality_gate.py` [^5^]. Chapter 7 validated seven new strategies [^6^]. Chapter 8 specified a four-phase capital commitment framework scaling from $0 to $25M+ [^7^]. This chapter converts those findings into a sequenced, owner-assigned implementation program.

The roadmap comprises four phases: Phase 0 (Emergency Triage, Weeks 1–2) arrests active value destruction; Phase 1 (Infrastructure, Weeks 3–4) deploys the statistical backbone; Phase 2 (Golden Portfolio Launch, Weeks 5–8) activates the optimal multi-asset allocation; and Phase 3 (Institutional Readiness, Weeks 9–12) validates statistical rigor for scaled capital commitment.

![12-Week Implementation Roadmap — Gantt Timeline](implementation_roadmap_gantt.png)

*Figure 9.1: Gantt timeline of the 12-week implementation program. Phase 0 executes emergency gate changes; Phase 1 deploys statistical infrastructure; Phase 2 launches the Golden Portfolio; Phase 3 validates institutional-grade rigor.*

### 9.1 Phase 0: Emergency Triage (Weeks 1–2)

Phase 0 has one objective: stop the bleeding. Four asset classes — Crypto C-Tier, Forex, Commodities, and Futures — are classified as FAIL tier, destroying -77.79% in PnL while occupying 49.5% of trading bandwidth [^7^]. Every day these classes receive capital inflicts an estimated 78 basis points per trade in foregone returns.

**Day 1–3: Suspend Crypto C-Tier, abolish WINNER_FILTER, replace `elite_score` with `ml_score` ≥ 0.82.**

C-Tier suspension requires setting `cryptoCTierEnabled` to `false` in `hf_quality_gates.json` and adding a hard block in `hedge_fund_quality_gate.py` at line 21 rejecting any pick with `tier == 'C'`. C-Tier's 41.2% WR and PF 0.84 across 318 trades represent guaranteed negative expected value [^1^]. WINNER_FILTER abolition removes the gate function from `hc_filter.js` (lines 298–420) that blocks confidence > 0.85 picks — a filter delivering 100% kill rate with zero correct blocks [^4^]. The `elite_score` → `ml_score` replacement changes QUALITY_GATE from `elite_score < 30` (44.1% accuracy, -0.17 correlation with profitability) to `ml_score >= 0.82 && confidence >= 0.70` [^5^]. The 0.82 threshold was selected because shadow-blocked analysis shows picks at this level achieving 58.8% WR [^4^].

**Done criterion:** C-Tier produces zero new picks; WINNER_FILTER removed; `ml_score >= 0.82` active; 48-hour shadow log clean.

**Day 4–7: Lower R:R gate from 1.5 to 1.25, unblock confidence 0.85–0.90 sweet spot.**

The RR_GATE at 1.5 blocks 63 picks with 50.0% kill rate — equivalent to a coin flip [^4^]. The R:R 1.25–1.5 band contains picks with 51.2% WR and positive aggregate PnL [^4^]. Lowering the floor to 1.25 requires changing `riskRewardFloor` from `1.50` to `1.25` in `hf_quality_gates.json`. The confidence 0.85–0.90 band shows 82% WR and PF 11.8 in live data [^4^]; with WINNER_FILTER abolished, these picks flow through automatically. Combined effect: projected +15–20% annual alpha recovery.

**Done criterion:** R:R floor at 1.25 confirmed; confidence 0.85–0.90 picks passing gates; no quality degradation in shadow log.

**Day 8–14: Forex recovery verification, bond `elite_score` floor 30 → 15.**

The nine forex fixes deployed on 2026-05-02 require a two-week verification window. The keystone change — capping `MAX_RESOLVE_RETRIES` at 3 in `outcome_resolver.py` (lines 608–631) — must demonstrate resolution rate recovery from ~20% to ~78% [^2^]. Bond gate relaxation changes `bondEliteScoreFloor` from `30` to `15` in `hf_quality_gates.json`, projected to unblock 3–5 additional picks monthly [^3^].

**Done criterion:** Forex resolution rate ≥ 75% sustained 3 consecutive days; bond pick flow +3/week with no PF degradation below 1.5.

### 9.2 Phase 1: Infrastructure (Weeks 3–4)

Phase 1 deploys the statistical backbone. No new strategies launch; the focus is measurement, risk management, and pipeline integrity.

**Deploy bootstrap CI module + PSR calculator + DSR calculator.**

The Probabilistic Sharpe Ratio (PSR) and Deflated Sharpe Ratio (DSR) gate Phase 2 capital deployment. PSR > 0.95 is required for all T1 assets before the $1M seed tranche [^7^]. The bootstrap CI module (`alpha_engine/statistical_rigor.py`, 536 lines) performs 1,000 resampled runs computing Sharpe distributions under the null. The DSR calculator adds the multiple-testing correction essential for seven simultaneous asset classes. Both are wired into `.github/workflows/audit-dashboard.yml`.

**Done criterion:** CI fails if PSR < 0.90 for any T1 asset; 1,000-bootstrap completes in < 10 minutes; values published in dashboard payload.

**Implement `forward_wr` pipeline fix (`outcome_resolver.py` → `hc_filter.js`).**

Critical Issue 3 from Chapter 6: `forward_wr` / `strat_fwd_wr` are never produced by `outcome_resolver.py` but consumed by `hc_filter.js` [^5^]. The fix: (1) add `track_calculator.py` to `outcome_resolver.py` aggregating resolved outcomes into per-strategy, per-symbol track records; (2) replace `hc_filter.js` line 310 fallback with `p.track_wr`. Gate 3 (`fwdN < fwdMinTrades`) has been inoperative due to zeroed inputs; this restores it.

**Done criterion:** `track_wr` on 100% of resolved picks; Gate 3 operates on live data; HC filter rate changes > 5pp from baseline.

**Deploy decay tracker with auto-demotion ladder.**

The decay tracker (`alpha_engine/decay_tracker.py`, 489 lines) addresses A-Tier degradation: PF collapses from 1.98 at L20 to 1.23 at L100 as staleness erodes edge [^1^]. The auto-demotion ladder graduates picks > 72h from A-Tier to B-Tier, and > 120h to blocked status. The tracker monitors PF and WR by vintage bucket and triggers alerts when any bucket's PF falls below 1.0.

**Done criterion:** A-Tier > 72h auto-demoted; vintage-bucket PF/WR on dashboard; alert fires if any bucket PF < 1.0.

**Deploy volatility targeting with Kelly sizing (fraction 0.25).**

Full Kelly would recommend 44.9% for equities, 61.5% for ETFs, and 85.2% for S-Tier crypto — allocations ignoring parameter uncertainty [^7^]. Quarter-Kelly halves these twice: 40% equities, 25% ETFs, 10% S-Tier. The vol targeting module (`alpha_engine/vol_targeting_researcher.py`, 136 lines) scales positions inversely to 20-day rolling realized volatility, maintaining portfolio vol at 15% ± 2%.

**Done criterion:** Portfolio vol within 15% ± 2% for 5 consecutive days; Kelly fractions capped at 0.25; daily sizing updates.

### 9.3 Phase 2: Golden Portfolio Launch (Weeks 5–8)

Phase 2 is the operational inflection point. The Golden Portfolio goes live: 40% Equities ($4M), 25% ETFs ($2.5M), 15% Bonds ($1.5M), 10% Crypto S-Tier ($1M), 5% B-Tier ($500K), 5% A-Tier ($500K) [^7^]. Capital deploys in two $500K tranches beginning Week 5, scaling to $1M by Week 8.

**Deploy HRP allocator for cross-asset position sizing.**

The HRP allocator (`alpha_engine/hrp_allocator.py`, 493 lines) replaces equal-weighting with inverse-variance clustering. The CIO blend overrides pure HRP (which would assign 39.1% to bonds) and pure Sharpe-equalized weighting (which would concentrate 53.6% in equities) to respect three hard constraints: no asset class > 40%, total crypto ≤ 20%, bonds ≥ 15% [^7^]. The allocator runs daily against the correlation matrix (crypto intra-cluster 0.70–0.80, equity–ETF 0.85, bond–equity -0.30).

**Done criterion:** Daily position sheets produced; tracking error < 3% versus CIO blend; all hard constraints satisfied.

**Launch crypto perp funding arb (shadow → live).**

Crypto perpetual futures funding-rate arbitrage offers the highest projected returns of any new strategy: PF 5.0–8.0, Sharpe 2.5–3.5, near-zero market beta [^6^]. Launch protocol: two weeks shadow mode (Weeks 5–6), then live at 0.25× sizing at Week 7, scaling to 0.5× if shadow + live PF > 3.0 at n ≥ 10. Entry requires 7-day average funding rate > 0.01% per 8-hour period; exit triggers after three consecutive negative funding periods.

**Done criterion:** Shadow PF > 3.0 at n ≥ 10; live execution on 2+ exchanges; funding filter active.

**Add forex carry sleeve, CEF NAV strategy.**

Forex recovery (true WR 48.7%, PF 3.59 on n=273 [^2^]) transitions to deployment via the G10 carry trade: borrow CHF at 0.00%, invest in USD at 4.75%, capturing 3.10–4.75% spreads [^6^]. The CEF NAV discount strategy deploys long the most discounted quintile, short the most premium quintile, targeting PF 1.5–2.0 [^6^]. Both launch at 0.5× sizing with 30-day shadow prefixes.

**Done criterion:** Forex carry ≥ 3 picks/week; CEF long/short balanced; combined PF > 1.5 at n ≥ 15.

**Deploy regime gate + correlation gate.**

The regime gate implements a three-state HMM classifier (bull, neutral, bear) blocking mean-reversion in crash regimes and momentum in bear regimes. The correlation gate monitors 30-day rolling correlations, triggering reductions when intra-cluster correlations spike above 0.90. Both are implemented as modular filters in `hedge_fund_quality_gate.py` with configurable thresholds in `hf_quality_gates.json`.

**Done criterion:** HMM accuracy > 70% on historical data; correlation gate responds within 1 trading day.

### 9.4 Phase 3: Institutional Readiness (Weeks 9–12)

Phase 3 is the final validation sprint. Entry requires Golden Portfolio sustaining PF > 5.0 for two consecutive weeks with WR > 65% and MDD < 15% [^7^]. No new trading functionality deploys; the focus is stress-testing and documentation.

**Full statistical rigor: 1,000 bootstrap runs, PSR > 0.95, DSR > 0.95.**

The bootstrap CI module runs its full validation: 1,000 resampled runs per asset class. PSR > 0.95 means < 5% probability that the observed Sharpe is a statistical artifact [^7^]. DSR > 0.95 adds the multiple-testing correction across seven asset classes. T1 assets (Equities, ETFs, Crypto S-Tier) must clear both thresholds; T2 assets must clear PSR > 0.90.

**Deploy 8 researcher personas for continuous edge detection.**

Eight personas in `ml_crypto_predictor/researchers/` provide continuous monitoring: Vol Targeting (136 lines), Reconciliation (134 lines), HMM Regime (137 lines), Risk Parity (138 lines), Factor Overlay (137 lines), Meta Orchestrator (148 lines), Multiple Testing (136 lines), and Transaction Cost (146 lines). These 1,212 lines automate vol regime monitoring, cross-signal reconciliation, factor tracking, and cost analysis.

**Done criterion:** All 8 running daily; ≥ 2 edge-detection alerts per week; alert-to-investigation latency < 24h.

**Deploy cost gate (net-of-cost PF filter).**

The cost gate applies per-asset transaction costs — crypto spot 0.10%, perps 0.05%, equities 0.01%, forex 0.8–3.0 pips, bonds 0.05% — and blocks strategies with net-of-cost PF < 1.2. The model is parameterized in `hf_quality_gates.json` and validated quarterly against execution data.

**Week 12: Go/no-go decision.**

The CIO reviews the complete audit package: 12 weeks of Golden Portfolio performance, PSR/DSR results, cost-gate clearance, kill-switch logs, and persona alert history. Four conditions must clear for $25M+ deployment: (1) Golden Portfolio PF > 5.0 for 2+ weeks; (2) all T1 PSR > 0.95 and DSR > 0.95; (3) CVaR < 5% at 95% confidence; (4) Sortino > 3.0 [^7^]. Failure on any condition triggers return to Phase 2 with a 30-day remediation window.

### 9.5 Risk Management Checkpoints

Risk management operates continuously from Day 1. The following tables govern the 12-week program with triggers that can halt deployment at any phase.

**Table 9.1: 12-Week Implementation Roadmap**

| Week | Phase | Key Deliverable | Owner | Success Criteria | Abort Trigger |
|:---:|:---|:---|:---|:---|:---|
| 1 | P0 | C-Tier suspension, WINNER_FILTER abolition, ml_score ≥ 0.82 | Engineering | C-Tier output = 0; 48h shadow log clean | C-Tier picks still flowing |
| 1 | P0 | R:R gate 1.5 → 1.25 | Quant | Config updated; conf 0.85–0.90 unblocked | PF degradation > 10% in unblocked band |
| 2 | P0 | Forex recovery, bond elite_score 30 → 15 | Trading Ops | Forex resolution ≥ 75%; bond +3 picks/week | Forex resolution < 50% after 5 days |
| 3 | P1 | Bootstrap CI + PSR/DSR calculator | Data Eng | CI run < 10 min; PSR/DSR in payload | CI failure rate > 5% |
| 3 | P1 | forward_wr pipeline fix | Engineering | track_wr on 100% of picks | Gate 3 inoperative after deploy |
| 4 | P1 | Decay tracker + auto-demotion | Quant | A-Tier > 72h demoted; vintage alerts active | Demotion misfiring > 2x/day |
| 4 | P1 | Vol targeting + Kelly sizing (f = 0.25) | Risk | Vol 15% ± 2%; daily sizing update | Vol > 20% for 3+ consecutive days |
| 5 | P2 | HRP allocator deploy | Portfolio | Tracking error < 3% vs. CIO blend | Hard constraint violation |
| 5–6 | P2 | Crypto perp arb shadow mode | Trading Ops | Shadow PF > 3.0 at n ≥ 10 | Shadow PF < 1.5 at n ≥ 10 |
| 7 | P2 | Crypto perp arb live at 0.25× | Trading Ops | Live execution on 2+ exchanges | Slippage > 2× estimate |
| 6–7 | P2 | Forex carry + CEF NAV launch | Quant | ≥ 3 forex picks/week; CEF balanced | Combined PF < 1.0 at n ≥ 15 |
| 8 | P2 | Regime gate + correlation gate | Risk | HMM accuracy > 70%; response < 1 day | Misclassification > 40% |
| 8 | P2 | **Golden Portfolio live** | CIO | PF > 5.0, WR > 65%, MDD < 15% | PF < 3.0 or MDD > 18% |
| 9–10 | P3 | 1,000 bootstrap, PSR > 0.95, DSR > 0.95 | Data Eng | All T1 clear both thresholds | Any T1 PSR < 0.90 |
| 9–11 | P3 | 8 researcher personas deploy | ML/Research | Daily runs; ≥ 2 alerts/week | Persona error rate > 10% |
| 10–11 | P3 | Cost gate (net-of-cost PF filter) | Quant | No strategy net PF < 1.2 | Cost model invalid vs. execution data |
| 12 | P3 | Go/no-go + audit docs | CIO | All 4 Phase 3 gates satisfied | Any gate failure → return to P2 |

The roadmap consolidates 16 discrete deliverables, each with a named owner and explicit pass/fail criteria. Abort triggers are hard stops that automatically halt capital deployment until remediation is verified. Checkpoint density is highest in Weeks 1–4, reflecting elevated operational risk during infrastructure deployment; Weeks 9–12 shift focus to statistical validation.

**Table 9.2: Risk Management Checkpoint Matrix**

| Checkpoint | Trigger | Action | Escalation Path | Recovery Criteria |
|:---|:---|:---|:---|:---|
| Kill-switch GREEN | PF > 2.0 and WR > 55% | Full allocation | None | Sustained 3+ days |
| Kill-switch YELLOW | PF 1.5–2.0 or WR 50–55% | Reduce 25% | Risk team alert | PF > 2.0 or WR > 55% for 2+ days |
| Kill-switch AMBER | PF 1.2–1.5 or WR 45–50% | Reduce 50% | CIO notification | PF > 1.5 or WR > 50% for 3+ days |
| Kill-switch RED | PF < 1.2 or WR < 45% | Reduce 75% | Emergency review | PF > 1.2 or WR > 45% for 5+ days |
| Kill-switch BLACK | PF < 1.0 or WR < 40% | **Full liquidation** | Board notification | Full model review before restart |
| 5% portfolio DD | Rolling 5% drawdown | Reduce 50% size | Risk auto-alert | DD < 3% from peak |
| 10% portfolio DD | Rolling 10% drawdown | **Full halt review** | CIO review within 24h | DD < 7% + root cause documented |
| Asset class PF < 0.80 | Any class PF < 0.80 for 5+ days | Zero that class | Quant investigation | PF > 1.0 for 3+ consecutive days |
| Weekly ETF rebalance | Time-decay > 5% | Rebalance ETFs | PM execution | Complete within 48h |
| Monthly equity rebalance | Signal maturity > 30 days | Rebalance equities | PM execution | Complete within 72h |
| Schema integrity | Schema violation in resolver/filter | Block deployment | Engineering fix | CI passes; py_compile clean |
| PSR degradation | Any T1 asset PSR < 0.90 | Halt scaling | Quant recalibration | PSR > 0.95 restored |

The checkpoint matrix provides twelve control points operating continuously across all phases. The kill-switch ladder escalates from normal operations (GREEN) through four restrictive states to full liquidation (BLACK). The 5% and 10% drawdown triggers protect against tail events that PF-based monitoring may not capture quickly enough. The asset-class PF < 0.80 trigger prevents a single failing sleeve from contaminating portfolio metrics — the mechanism that would have eliminated C-Tier had it been operational from inception.

Rebalancing cadence reflects differing signal half-lives. ETFs require weekly rebalancing (5% time-decay threshold) as their edge erodes gradually but persistently [^7^]. Equities require only monthly rebalancing (30-day signal maturity) — their alpha is more durable, and excessive trading incurs frictional costs. Schema integrity gates, derived from Chapter 6's 37 issues [^5^], prevent code changes to `outcome_resolver.py`, `hc_filter.js`, `hedge_fund_quality_gate.py`, or `hf_quality_gates.json` from reaching production without CI validation.

The layered interaction between checkpoints creates redundant defenses. Kill-switch ladder governs real-time trading decisions. Drawdown triggers provide catastrophic-loss protection. Rebalancing prevents signal staleness accumulation. Schema gates prevent regressions. PSR degradation checks ensure statistical confidence remains institutional-grade. The default state in the presence of uncertainty is reduction, not maintenance — the distinguishing principle of institutional risk architecture.

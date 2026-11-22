# Profitable Market System — Phased Plan & TODO Register (research synthesis)

> **Canonical plan:** `plans/2026-11-20-market-profit-system-plan.md` (Zoo, architect) — this doc is the research synthesis feeding it.
> **Todos:** `plans/2026-11-20-profit-program-todos.json` (P0–P5 with exit tests).
> **Hypotheses:** `plans/2026-11-20-residual-mean-reversion-hypotheses.md` (H-144…H-148).
> **Implementation kickoff sent to COMS:** topic `profit-system/plan` (retained), 2026-11-20.

**Created:** 2026-11-20 (synthesized from broad repo research)
**Owner:** Elton (findtorontoevents.ca/audit ecosystem)
**Status:** PHASE 0 — not started
**Source of truth for statistical governance:** `research/profitability/PROTOCOL.md` (v1, locked) + `research/profitability/HYPOTHESES.md`
**Canonical external review:** `EDGE_REVIEW_2026-11-19.md` (Arena agent, 2026-11-19)

> **Honest premise (from our own artifacts):** No asset class currently has a proven, cost-surviving,
> benchmark-beating edge. RAW all-time picks WR 25.28% / PF 0.61 (n=73,817); CRYPTO intrabar PF 0.92;
> FOREX PF 0.65; EQUITY PF 0.94; COMMODITY ~1.03–1.04; FUTURES PF 1.09 (n=52). Edge-search v1–v4
> (40 pre-committed trials): 0 pass null + DSR; best null p = 0.080. Hypothesis registry H1–H23: all
> `NOT_PROVED`. The measurement machine is strong; the hypothesis machine is the gap.
>
> **Therefore:** this plan stops candidate generation first, fixes the ledger, then tests only the
> premia with documented multi-decade evidence (trend, carry, PEAD, insider clusters), implemented
> literature-correctly, with cost-obsessed execution and disciplined sizing.

---

## 0. What the research says (synthesis of recent + deep sources)

### Recent (last 72h) artifacts reviewed
- `EDGE_REVIEW_2026-11-19.md` — external independent review; honest scorecard; core diagnosis.
- `STRATEGY_DISCOVERY_REPORT_V3_2026-11-18.md` — top-10 crypto list; **flagged** keltner-bounce / corr_vwap_reversion as degenerate distributions; arithmetic self-consistent but **none** of the 10 V3 strategies appear in `backtest_multi_strategy_results.json` (unverifiable).
- `MARKET_BEATING_REPORT.md` (2026-11-20) — 409 signals, 58.3% accuracy vs 60% target; accuracy without edge.
- `STRATEGY_VALIDATION_PLAN_2026-11-18.md`, `STRATEGY_DISCOVERY_REPORT_V3`, `AUDIT3_FEEDBACK_2026-11-19.md`.
- `STRATEGY_PER_ASSET_CLASS_MASTERPLAN.md`, `STRATEGY_PER_ASSET_CLASS_MASTERPLAN` (docs/).
- `PLAN_PATH_TO_PROFITABILITY.md` (2026-11-14) — "verified edges" `quan_engine` (95.8% WR) and `st_rsi_momentum_confluence` (65.1% WR, PF 2.53); **caveat:** these are in-sample/registry claims that have not passed the locked OOS gates; treat as hypotheses to be re-tested, not facts. (Also note the static-kill-list root cause is real and worth fixing.)
- `research/profitability/PROTOCOL.md` + `PROTOCOL_v3/v4` + `PROTOCOL_ADDENDUM_1.md` — locked pre-registration, costs, gates, versioning.
- `research/profitability/HYPOTHESES.md` (registry; rule "no row deleted").
- `research/profitability/` reports: `AUDIT3_FEEDBACK`, `EDGE_REVIEW`, etc.

### Deep research sources reviewed
- `docs/ALL_STRATEGIES.md` — 700+ strategies across 15+ systems; 5,758 Python files; 29 Pine scripts; 12 mutation variants. **Conclusion from external review: this is the multiple-testing problem, not a technique gap.**
- `KIMI_RISEOFTHECLAW/STRATEGY_RESEARCH_FRAMEWORK.md` — 500-strategy target framework; categories; quality-control checklist.
- `KIMI_RISEOFTHECLAW/` folder — alpha research engine, alternative data, ML signal ranker, battle tests, live challenge, rigorous backtest, etc.
- `tools/kimi_research_2026_05_20/` — `SIX_GATE_STRATEGY_REPORT.md` (Sharpe 2.516 on **synthetic** data; gates pass on embedded-signal synthetic data — **not evidence of live edge**; must be re-run on real data before any claim), plus per-asset-class strategy reports (BOND, COMMODITY, CRYPTO, EQUITY, ETF, FOREX, PENNY_STOCK) and `MASTER_INTEGRATION_SUMMARY.md`.
- `docs/` strategy audit family: `STRATEGY_TRUST_RANKING.md`, `STRATEGY_LIFECYCLE_POLICY.md`, `STRATEGY_VALIDATION_GATES.md`, `STRATEGY_FAILURE_ANALYSIS_FRAMEWORK.md`, `STRATEGY_DISCOVERY_PROTOCOL.md`, `STRATEGY_PER_ASSET_CLASS_MASTERPLAN.md`, `STRATEGY_PIPELINE_END_TO_END_2026-05-31.md`, `HYRO_WINNING_STRATEGIES.md`, `HOLY_GRAIL_CRYPTO_STRATEGY.md`, `IDEAL_STRATEGY_PORTFOLIO.md`.
- `alpha_engine/HEDGE_FUND_STRATEGIES_RESEARCH.md`, `quantum_fusion_*`, `coinglass_integration.py`, `funding_rate_arb.py`, `btc_breakout_strategy.py`.
- `copy_trader_intel/` (STRATEGY_BRAINSTORM, technical_analyzer, non_crypto_consensus, polymarket_scraper), `copy_trading_research_report.md`.
- `prediction_market_agents/`, `PREDICTION_MARKETS.md`, `prediction_market_consensus.py`, `alpha_engine/polymarket_signals.py`, `alpha_engine/kalshi_signals.py`.
- `verified_strategies/`, `proven_strategies/`, `incubator/`, `incubator_strategies/`, `baby_strategies/`.
- `STRATEGY_GRAVEYARD.md`, `TRAPPED_STRATEGIES_2026-03-25.md`, `FAILED_STRATEGIES` (folder).
- `DEFINITIVE_HEDGE_FUND_PIPELINE.md`, `HEDGE_FUND_ENHANCEMENT_PLAN.md`, `HEDGE_FUND_QUALITY_ROADMAP.md`, `HEDGE_FUND_QUALITY_PLAN.md`.
- `REALISTIC` / `honest_engineering_projection.md`, `PROFITABLE_APPROACH_PROVEN.md`, `TRUE_PROFITABILITY_VALIDATED.md`.
- `BOND_FIXED_INCOME_REPOS_2026-11-18.md`, `CRYPTO_REPOS_2026-11-18.md`, `EQUITIES_REPOS_2026-11-18.md`, `FUNDS_ETF_REPOS_2026-11-18.md`, `FX_MACRO_COMMODITY_REPOS_2026-11-18.md`, `PREDICTION_MARKET_REPOS_2026-11-18.md`.
- `DEEP_RESEARCH_*.md` (behavioral finance, market microstructure, ML/AI trading, options volatility, portfolio construction).
- `ml_consensus/`, `ml_gatekeeper/`, `ml_crypto_predictor/`, `claude_gainer_ml/`, `crypto_gainer_ml/`, `crypto_ml_edge/`.
- `paper_trading/`, `forward_testing/`, `forward_trade_executor.py`, `forward_test_gates.py`.
- `transaction_cost_model.py`, `transaction_cost_model` (cost modeling).
- `risk_management/`, `risk_quantification_agent.py`, `portfolio_circuit_breaker.py`, `regime_detector.py`, `regime_aware_gate.py`, `market_regime_detector.py`.
- `statistical_validator.py`, `STATISTICAL_RIGOR_FRAMEWORK.md`, `STATISTICAL_VALIDATION_REPORT.md`.
- `walk_forward_validator.py`, `rigorous_validation_protocol.py`, `leak_free_audit.py`.
- `hypothesis-registry*` skills (M-107 pre-registration rule).
- `money-maker-ready*` skills (edge hunt per asset class).
- `thingstocheck-june2026` skill (audit dashboard edges).
- `audit-pick-flow` skill (pick funnel).

### Core diagnosis (from external review + our own artifacts)
1. **Multiple-testing engine, not technique gap.** 700+ strategies, ~5,758 files, 365 workflows, 331k commits, 12 mutation variants. With ~40 formal trials you already get p≈0.05 candidates by chance (edge-search: expected false positives ≈ 2). With 700+, every "winner" is pre-purchased p-hacking. Binding constraint = hypothesis quality + trial budget.
2. **Trade expression manufactures losses.** Fixed 1.5 ATR TP / wide SL: FOREX wins avg 0.62% vs losses 1.00% → 57.8% WR but PF 0.85; EQUITY 59–60% WR, PF < 1. Edge must be expressed with symmetric, vol-scaled, time-based exits + vol targeting. Expression changes stats more than signal.
3. **Universe & frequency wrong for breadth.** Daily bars, ~10 crypto majors. IR scales with √breadth. Cross-sectional stat-arb needs hundreds of instruments; single-instrument crypto daily is the least fertile ground. Your own result: 30 pairs weekly momentum Sharpe −0.18.
4. **Keyless daily public data ≈ no alpha left.** Edge-search proved this. Remaining public edges: (i) risk premia (persistent, compensated, capacity-limited), (ii) microstructure/flow (needs intraday/TAPE/options/venue access).
5. **Process asymmetry: measurement >> hypothesis.** DSR/PBO/SPA/FDR/intrabar-true resolution are excellent; candidate generation is unconstrained. Real shops spend 80% on "why should this exist, who is losing money, why hasn't it been arbitraged?" before a line of backtest code.
6. **Ledger integrity is a hard prerequisite.** PM → `PREDICTION` class with binary-settlement resolver; FOREX date-only/EST timestamps; zombie `_auto_expired` rows; 67 dup groups; cross-vendor price sanity (CADJPY 611.23). Everything downstream of a broken ledger is fiction (INCIDENT #91/#96/#18).

### Documented evidence base — strategies with measured, sourced edge (2026-11-20 synthesis)

The following are the **only** strategies with documented, mechanism-backed, cost-adjusted evidence in the research base. Everything else in the 700+ inventory is either unverified or has failed falsification. Decay rates and caveats are included; treat them as part of the claim.

**Equities — deepest evidence base (market-neutral relative value + directional families)**
| Strategy | Mechanism | Documented evidence | Decay / caveat |
|---|---|---|---|
| Stat-arb (PCA residual mean reversion) | Regress returns on eigenportfolios; fit residual as Ornstein–Uhlenbeck; trade the s-score | Sharpe **1.44 net of costs, 1997–2007** | **0.9 in 2003–2007** — decay as capital chased residuals |
| Stat-arb (sector-ETF residual) | Same, but factors are sector ETFs | Sharpe 1.1 (1997–2007); **1.51 (2003–2007)** when signals weighted by trading volume | volume-weighting materially helps |
| Pairs trading (distance method) | Match normalized price series; trade divergence from the spread's own history | ~11% annualized excess return, Sharpe ~1.5, near-zero market beta, 1962–2002 | classic; capacity-limited |
| Cross-sectional momentum | Rank by 6-month return; long top decile, short bottom | Decades of research; core signal at large funds | regime/crowding risk |
| Mean reversion (RSI / Bollinger) | Buy oversold, sell at the mean | High win rate; best in range-bound regimes | regime-dependent |
| Market making | Quote both sides, capture spread, manage inventory | Consistent income in liquid names; lower directional risk than trend-following | needs low latency + capital |
| Event-driven | Trade around earnings, M&A, announcements | Profitable independent of market direction | needs event data + speed |

Mechanism: strip out systematic return; trade only the idiosyncratic residual (a stock cheap relative to its sector gets bought, expensive gets shorted). Honest caveat: the same strategy earned Sharpe 1.44 in the 1990s sample and 0.9 a decade later.

**ETFs — two distinct games**
- Mean reversion on the ETF itself (index ETFs are liquid, range-bound; Bollinger-style entries).
- True arbitrage (NAV premium/discount → AP creates/redeems against the basket) — **not retail-accessible**: requires creation/redemption authority, real-time NAV, creation units of 50k shares ($5–10M+); you compete with Citadel Securities, Susquehanna, Jane Street, Virtu.
- Tradable middle ground: intraday ETF vs constituents as a mean-reverting pair (no special authority needed).

**Futures & commodities**
- Commodity spot mean-reverts toward production costs (supply responds to price deviation) — economic mechanism, not statistical artifact; shows in term structure (stochastic long-run mean fits better than constant-mean models like Gibson–Schwartz).
- **Calendar-spread mean reversion** (Bollinger entries on front-month vs second-month spreads, Kalman-filter dynamic hedge ratios): over 22 years (1992–2013), net of transaction costs and bootstrap-tested against random orders, most combos significantly profitable across all four energy commodities, Sharpe > 2 for WTI crude and natural gas. Strong because net-of-costs + tested vs random orders.
- Trend following is the complementary sleeve — commodities show the strongest trending behavior of any asset class.

**Fixed income**
- Edge is liquidity discovery, not price prediction. Fragmented corporate bond market; value = finding where liquidity actually is before sending an RFQ.
- Platforms: Broadridge LTX (Liquidity Cloud + dealer-selection scoring; BondGPT queries 12+ datasets, 30k+ US bonds, TRACE, ratings, index, evaluated pricing, filings, 13F, Treasury); MTS/BondCliQ Liquidity Mapping (MTS BondsPro real-time pricing, 500+ broker-dealers, 20k bonds); Ediphy Liquidity Checker (personalized watchlist + real-time liquidity-shift notifications).
- Generalizes: in wide-spread, asymmetric-info asset classes, alpha is in execution and information access, not directional views.

**Crypto**
- Structural facts (24/7, fragmented liquidity across dozens of venues, no closing auction) → execution quality dominates signal quality.
- Multi-venue routing: $1M BTC market order pays 4–13 bps extra on a single exchange; $5M pays ~134 bps.
- DEX slippage: large/illiquid trades can exceed 5%; concentrated liquidity + smart routing mitigate.
- Execution alphas: volume/spread/volatility forecasts R² ~65–75% / ~80% / ~25–35% (vol much less predictable).
- ML price prediction: directional accuracy 53–56% for tree models — not a strategy on its own.
- **Cost-aware execution is the whole lesson:** naive hourly BTC strategies collapse after 10 bps costs (73.50% → −64.00%); a cost-aware filter restores >65% annualized with Sharpe >1. The fix is an execution rule, not a better model.

**FX**
- Triangular arbitrage (EUR/USD, USD/JPY, EUR/JPY must be consistent) — risk-free when inconsistent, but only with fast execution + low costs (discrepancy vanishes in ms).
- Trend following applies but is regime-dependent, not persistent.

**Side strategies you asked about**

*A. Reverse-engineering top gainers — survivorship trap unless you measure factor exposures.*
- Building a universe from today's winners imports survivorship bias (the −100% names are missing; current-index-membership eligibility inflates backtests).
- Ranking by past return yields either momentum (continues 1–12 months) or long-horizon reversal (extreme 3–5y winners underperform — DeBondt–Thaler), depending entirely on formation window.
- Tuning until you match the observed winner list is the textbook deflated-Sharpe case (ordinary Sharpe inflated by many variants).
- What actually works: decompose winners into factor exposures, ask which exposures were rewarded, decide whether that reward is persistent or regime-specific. That's a forward-testable hypothesis; "stocks that went up 300% share this chart pattern" is only backward-testable.

*B. Prediction markets (Kalshi, Polymarket) — no sourced evidence in the base.*
- I have no sourced evidence on mechanism, liquidity, or regulation; I will not assert facts I can't back. Structurally they're binary contracts → natural candidates for relative-value logic (cross-market consistency, mean reversion of overreaction), but that's reasoning, not a documented result. Keep as probability oracle only (consistent with Phase 3).

*C. News-article counts as a price signal — legitimate alt-data, with methodological risks as the whole game.*
- News sentiment + search-based attention proxies capture behavior conventional variables miss; markets respond to attention shocks fundamental data can't capture. Whether these improve forecasting under realistic trading conditions is genuinely poorly understood.
- Studied data categories: social media sentiment, web traffic/search trends, satellite imagery, consumer transactions, employee sentiment.
- For a specific example (e.g., GTA 6), the risks are the whole game: count-based features must be built **point-in-time** (lag/rolling windows use only past data; train/val split must respect time order) or leakage makes the signal look far stronger than it is. More data ≠ better (noise increases with signal); filtering/weighting is the critical skill. A single-product entertainment event is exactly where the count is likely a proxy for attention already priced — honest test is a **placebo**: does the same count correlate with unrelated tickers, and does it predict returns after controlling for the sector move?

**Coverage note:** sources cover equities, ETFs, energy futures, fixed income, crypto, FX, and alt-data at a general level. They do **not** cover prediction markets (no mechanism/liquidity/regulatory evidence) and nothing specific to GTA 6 or any single-title entertainment event. Closing those gaps requires: exchange docs + fee schedules for prediction venues; an event-study dataset with point-in-time article counts, timestamped publication, and a matched control set of tickers.

### What real edge looks like at this scale (2026 reality)
- **Risk-premia harvesting, not prediction.** Time-series momentum/trend (Moskowitz–Ooi–Pedersen 2012; Hurst–Ooi–Pedersen ~140 years of evidence; Sharpe ~0.5–0.9; crisis alpha in 2008/2022). Carry (FX Lustig–Roussanov–Verdelhan; commodity Erb–Harvey). Value/quality/low-vol/betting-against-beta (Frazzini–Pedersen; Baker–Bradley–Wurgler). PEAD (Bernard–Thomas 1989). Index reconstitution flows.
- **Liquidity provision, not directional forecasting.** Market making earns spread + rebates, near-neutral direction. On prediction markets: maker-only (Kalshi maker = 0 fee; Polymarket makers get 15–25% rebates). Your Buffy PM doc says exactly this.
- **Data moats** (satellite, card panels, web/app telemetry, TAPE/options/short-interest/borrow, order-book history). Keyless daily closes are not a moat.
- **Process obsession:** hypothesis economics first → pre-registered protocol → tiny trial count → clean holdout never touched → adversarial review → ≥90 days forward paper → tiny size → capacity cap → watch decay → retire. (Your RECOVERY/adversarial-review habit is right; it's just applied after 700 signals instead of before generating any.)
- **Risk & sizing win, not being right:** vol targeting, factor neutralization, drawdown circuit-breakers, diversification across many uncorrelated low-Sharpe streams (10 streams @ Sharpe 0.5, ρ≈0.1 → stack Sharpe ≈ 1.5). One great signal < five decent independent ones.
- **Cost elimination:** 1bp/day ≈ 20% annual leakage. Fee audits, maker rebates, tax location, turnover caps. Your PM fee analysis is the best page in the repo; apply same discipline to FOREX rollover, crypto funding, fund ERs.
- **Even then, most fail** and edges decay on publication (McLean–Pontiff). Capacity + decay monitoring is permanent overhead.

### Free data stack (production-grade; do NOT use yfinance for production)

yfinance is fine for fast personal exploration and nothing else — severe survivorship bias, no official API, Yahoo shut its public finance API in 2017. If your universe is built from today's tickers, every backtest is flattered.

| Asset class | Free source | Reality |
|---|---|---|
| Crypto | Binance public WebSocket | Genuinely tick-by-tick, sub-second, no API key |
| US equities / forex | Finnhub free tier | Real-time during US market hours |
| Futures, VIX | CME / Cboe public data | ~15-min delay (licensing, not technical) |
| Spreadsheet quotes | `GOOGLEFINANCE` in Sheets | Built in, zero setup, basic US equities/ETFs only |
| Filings, insider trades | SEC EDGAR | Free REST API, ~10 req/sec ceiling |
| Government contracts | USAspending.gov | Free, award amounts + recipients |
| Positioning | CFTC Commitment of Traders | Free weekly report |
| Lobbying / campaign finance | Senate LDA, OpenFEC | Free (FEC needs a key) |
| Search attention | Google Trends | Free, no official API — unofficial libs are not sanctioned |
| Macro series | FRED (+ ALFRED for point-in-time vintages) | Free, point-in-time vintages |
| Backtesting compute | QuantConnect free tier, TradingView free tier | Enough to iterate; paid for depth |

### Alternative data with a known mechanism (high-value, free, testable)

These have a *reason* to work — a documented economic story — unlike chart patterns:

- **Government contract awards** (USAspending): appear within days; revenue lands in earnings months later → reading the order book before the filing confirms it.
- **Congressional disclosures**: senator portfolios beat market by ~12%/yr (2004 study), narrowing to 5–7% as disclosure improved.
- **Consumer transaction panels**: predicted revenue beats for Just Eat, PayPal, Starbucks.
- **Job-listing data**: 6–8% yearly returns on "Jobs Active" variable.
- **Trade-credit data**: outperformed by 6–7% annualized.

These are legitimate alt-data candidates with mechanism. Test with point-in-time discipline + placebo (unrelated tickers) + cost survival. Single-product events (e.g. GTA6) are likely attention already priced.

### Value stocks vs mutual funds is a false binary

Both are exposure to equity risk premium, packaged differently. What matters more than the label is diversification across return drivers (commodity futures: similar returns/Sharpe to equities, negative correlation to stocks+bonds). A combined multi-strategy book had lower max DD and higher Sharpe than any individual strategy because losses in one coincided with gains in another. If you genuinely can't/won't do research, a low-cost broad index fund is not a compromise — it's the honest answer (consistent with the [470] result).

### Symbol-specific strategy mining is a multiple-testing trap

A team tested 1,285 variants with real costs, real OOS, pre-registered hypotheses, deflated-Sharpe gate: the bar for a systematically tradeable strategy is Sharpe territory essentially no individual verifiably reaches without institutional capital/access (best solo transparent 12-yr public track record ~0.8). Mechanism: multiple testing systematically overstates Sharpe; two-sigma is no longer the right benchmark. Concrete: on zero-alpha synthetic panels, an LLM research agent reported in-sample Sharpe 2.12 → realized +0.18 OOS; every method tested collapsed (1.68→+0.14). At scale, 136,000 strategies from accounting ratios/past returns/tickers: top 1% by predicted Sharpe earned 5.70%/yr OOS vs 5.88% average of 200 published — but Sharpe 1.46 vs 2.03 because published ones carry look-ahead bias. Even real edges are regime-dependent: one gold backtest had a statistically meaningful H1 over a year of ticks, but splitting into 5 windows found one clearly negative stretch dragging full-year to barely break-even under real spread/execution — a single aggregate number hid it entirely.

### Three cheap high-information actions (do these first)

1. **Establish real risk capacity before return target.** Decide max drawdown you could watch without selling, then size to it. 50% loss needs 100% gain to recover; 75% loss needs 300%. This one number determines everything downstream; costs nothing.
2. **Look at free alt-data with a known mechanism, not chart patterns** (list above). These have a reason to work.
3. **Paper trade before funding.** Simulated execution between research and capital — latency and slippage show up live, not in backtest. Thinkorswim paperMoney / TradingView paper trading on real-time data, free. Give it 60–90 days; compare live fills vs backtest assumptions. The gap is your real answer. If edge is within 15–20% of backtest expectations, scale in gradually.

### The punchline
At your scale, "real edge" ≠ better forecasting. It = risk-premia harvesting + cost elimination + honest sizing, in a boring portfolio. **Core 70–85% low-cost index beta + 10–25% premia sleeves + ≤5% speculative sleeve.** This *is* the winning formula for almost every participant including most institutions. Your own `MF_CAN_WIN.md` already proved this; the only step left is to act on it with the same rigor you applied to falsifying COT.

---

## Phase 0 — Stop, prune, fix the ledger, wire gates (Days 1–14)

### 0.0 DATA INTEGRITY COMES FIRST (Grok external review, 2026-11-20)

The existing system is destroying capital: across 55,510 resolved trades, WR 11.13%, avg return −3.56%/trade, Sharpe ~−2.3, PF ~0.46, ML accuracy ~33% (worse than random), calibration inverted, ~69% of resolved trades have zero PnL, and backtest WR (~42%) is ~4× live. Dashboard claims (+949% PnL, 35–40% WR) do not match the database. This is classic overfitting + data-quality failure, not a near-miss.

**Therefore the very first work, before price freshness or any signal search:**
- **P0.0a** Purge / quarantine zero-PnL rows (69% of resolved trades) — determine whether they are genuinely zero or un-resolved/placeholder.
- **P0.0b** Outlier handling: winsorize or exclude the outlier-driven PF; reconcile gross vs net.
- **P0.0c** Point-in-time correctness: audit every feature for look-ahead (COT leakage precedent M-095); no feature may use data not available at decision time.
- **P0.0d** Dashboard ↔ DB reconciliation: every published number must trace to a DB row; fix the +949% PnL / 35-40% WR claims or remove them.
- **P0.0e** Wire PBO / CPCV / DSR as HARD gates (not advisory) in the verdict pipeline; enforce walk-forward before any promotion.
- **P0.0f** Record real `n_trials` for every DSR claim including the 700-strategy catalog (effective N, not hand-picked subset).

Only after 0.0 passes does 0.1 (price freshness) and beyond make sense. An OU residual cannot be evaluated on a broken ledger.

**Goal:** freeze candidate generation, archive dead weight, repair ledger, make cost/benchmark gates hard in the verdict pipeline. No new strategies, no new swarms, no mutation engines until a candidate reaches `PROVED`.

### TODO — Phase 0
- [ ] **P0.1 Freeze candidate generation.** Add an emissions-time gate: global cumulative trial counter printed in dashboard; DSR computed at true N. Block any new strategy emission unless `PROVED` path is followed.
- [ ] **P0.2 Archive, don't delete.** Move `baby_strategies/`, `incubator/` (320+ AI strategies), mutation engine, score-band surfaces to `archive/`. Keep: data pipeline, audit harness, resolver, one hypothesis pod per candidate class.
- [ ] **P0.3 Fix the ledger (hard prerequisite).**
  - [ ] P0.3a Reclassify prediction markets → `PREDICTION` class with binary-settlement resolver.
  - [ ] P0.3b Fix FOREX date-only/EST timestamps.
  - [ ] P0.3c Purge zombie `_auto_expired` rows.
  - [ ] P0.3d Dedupe emissions (67 dup groups).
  - [ ] P0.3e Cross-vendor price sanity (CADJPY 611.23 etc.).
- [ ] **P0.4 Cost gate on every record.** Fees + slippage + borrow/funding/rollover per class; "2× costs" stress; one-bar delay; wire into `money_ready_verdict.py` as hard gates (already specced in Q25–Q27).
- [ ] **P0.5 Benchmark legs everywhere** (Buffy gate). Excess return at matched exposure vs SPY TR / BTC hold / T-bills / AGG / GSG, reported per class on every card. If `EDGE ≤ 0`, strategy is expensive beta.
- [ ] **P0.6 Delete/archive dead workflows; CI budget < 30 min.**
- [ ] **P0.7 Dynamic kill list (replace static).** Re-evaluate every strategy every 7 days on rolling 30-day window; regime-specific kill/amplify. (From `PLAN_PATH_TO_PROFITABILITY.md` P1.8.)
- [ ] **P0.8 Regime detection wiring.** Use `alpha_engine/regime_router.py` + `regime_detector.py` + `market_regime_detector.py` to gate verified edges by regime (high vol → mean-reversion; trending → momentum confluence; flat/choppy → both).
- [ ] **P0.9 Unify the `quan_engine` / `st_rsi_momentum_confluence` claims.** Re-test these two "verified edges" under the locked OOS gates before any promotion. If they fail, retire. Do **not** trust in-sample/registry claims.
- [ ] **P0.10 Deliverable:** publish `PROTOCOL_v5` (or addendum) locking the new gates + a Phase 0 post-mortem MD in `updates/`.

**Exit criteria:** ledger passes integrity audit; cost/benchmark gates hard in verdict pipeline; CI < 30 min; no new candidate emissions outside protocol.

---

## Phase 1 — Test the only premia with real evidence, properly (Days 15–45)

**Goal:** pre-register each premia as its own micro-pod with its own holdout. Acceptance gates = locked protocol: ≥100 resolved trades, intrabar-true, costs ×2, 1-bar delay, IR ≥ 0.5, alpha t > 2 (Bonferroni at true cumulative N), ≥90 days forward paper. **Two max concurrent pods.**

### TODO — Phase 1
- [ ] **P1.0 Pre-register all pods** in `HYPOTHESES.md` (rule: no row deleted). Set global trial counter; effective-N accounting (correlated candidates count > 1 trial; H10 died at effective N≈38, not N=12).
- [ ] **P1.1 Pod A — Equities market-neutral residual mean reversion (stat-arb).**
  - PCA residual: regress returns on eigenportfolios; fit residual as Ornstein–Uhlenbeck; trade the s-score. Target: reproduce Sharpe 1.44 (1997–2007) → expect ~0.9 in modern sample (decay). Cost-adjusted, intrabar-true.
  - Sector-ETF residual variant: factors = sector ETFs; volume-weight signals (1.51 vs 1.1 in 2003–2007). Run both; compare.
  - Pairs trading (distance method) variant: normalized price series; divergence from spread's own history; near-zero market beta. 1962–2002 evidence: ~11% annualized excess, Sharpe ~1.5.
  - Universe: liquid large/mid caps (500+). Symmetric long/short, vol-scaled, time-based exits. **No TP/SL.**
  - Leave last 24 months as untouched holdout; reproduce literature stats on 1990–present first.
- [ ] **P1.2 Pod B — Cross-sectional momentum (equities).**
  - Rank by 6-month return; long top decile, short bottom. Decades of evidence; core signal at large funds. Regime/crowding risk → overlay trend filter + capacity cap.
- [ ] **P1.3 Pod C — Calendar-spread mean reversion (energy futures).**
  - Bollinger entries on front-month vs second-month spreads; Kalman-filter dynamic hedge ratios. Target: reproduce 22y (1992–2013) result — significantly profitable across 4 energy commodities, Sharpe >2 for WTI crude and natural gas, net of costs, bootstrap-tested vs random orders.
  - Commodity spot mean-reversion mechanism (production-cost anchor) + trend-following as complementary sleeve (commodities trend strongest).
- [ ] **P1.4 Pod D — FX G10 carry with trend filter.**
  - Rank G10 by 1–3m forward discount (or rate differential), long top-3 / short bottom-3, vol-targeted, monthly; overlay 200d trend to cut carry-crash risk.
  - Triangular arbitrage as a separate micro-pod: EUR/USD, USD/JPY, EUR/JPY consistency; needs fast execution + low costs (discrepancy vanishes in ms).
- [ ] **P1.5 Pod E — PEAD drift, liquid large-caps.**
  - Fix the PEAD pipeline first (it exists but is broken). SUE-ranked earnings surprises; long +1σ surprise deciles, short/avoid negative, 60-day hold, weekly rebalance; screen 500+ names, low turnover.
- [ ] **P1.6 Pod F (optional) — Index-inclusion front-run.** S&P 500 additions announcement → effective date. Mechanical flow; capacity-small.
- [ ] **P1.7 Pod G (optional) — Slow "smart-money" cohorts.** Form-4 cluster insider *buying* in quality names; monthly cadence; 12-month horizon; ≥5 insiders same month. Low turnover defeats the fee wall that killed wallet-mirroring.
- [ ] **P1.8 Pod H (optional) — ETF intraday mean-reversion pairs.** ETF vs constituents as mean-reverting pair (no creation/redemption authority needed). Index ETF Bollinger mean reversion as simpler sleeve.
- [ ] **P1.9 Crypto execution-quality workstream (not a directional signal pod).**
  - Multi-venue routing cost audit (single-exchange $1M BTC = 4–13 bps extra; $5M = ~134 bps).
  - DEX slippage mitigation (concentrated liquidity, smart routing; >5% on large/illiquid trades).
  - Cost-aware execution filter: naive hourly BTC collapses after 10 bps (73.50% → −64.00%); cost-aware filter restores >65% annualized, Sharpe >1. The fix is an execution rule, not a better model.
  - Volume/spread/vol forecasts (R² ~65–75% / ~80% / ~25–35%) used for execution timing only, not price prediction.
  - ML directional accuracy (53–56%) treated as meta-labeling input only, never as a standalone signal.
- [ ] **P1.10 Fixed-income liquidity-discovery research (not a directional pod).**
  - Replicate the Broadridge LTX / MTS-BondCliQ / Ediphy approach: where is liquidity before the RFQ? Generalizes to any wide-spread asymmetric-info asset class. Execution + information access, not directional views.
- [ ] **P1.11 Alt-data research: news-article counts (point-in-time).**
  - Build count-based features point-in-time (lag/rolling windows use only past data; train/val split respects time order) — leakage is the whole risk.
  - Placebo test: does the same count correlate with unrelated tickers? Does it predict returns after controlling for the sector move?
  - Honest expectation: single-product entertainment events (e.g., GTA 6) are likely attention already priced. Treat as research, not a pod, until placebo + cost tests pass.
- [ ] **P1.12 Top-gainer reverse-engineering → factor-exposure decomposition.**
  - Do NOT build a universe from today's winners (survivorship bias) or tune to match the winner list (deflated Sharpe inflation).
  - Decompose winners into factor exposures; ask which exposures were rewarded; decide persistent vs regime-specific; test forward.
  - Formation-window discipline: 1–12m past return = momentum (continues); 3–5y extreme winners = reversal (DeBondt–Thaler).
- [ ] **P1.13 Prediction markets (Kalshi, Polymarket) — no sourced evidence.**
  - Keep as probability oracle only (Phase 3). No mechanism/liquidity/regulatory claims until exchange docs + fee schedules are sourced. Structurally binary → relative-value logic is plausible but undocumented.
- [ ] **P1.14 Explicitly do NOT re-test:** daily crypto single-name RSI2, TP/SL scalps, fixed-TP score bands, 50¢ Polymarket taker forecasting, meme/gainer ML, "milestones"/spike reversal reverse-engineering (requires order-flow data we don't have).
- [ ] **P1.15 Adversarial review gate** mandatory before any promotion (replicate H10 falsification template). Independent replication by a separate subagent (same code, fresh data pull) required for any `PROVED` claim.
- [ ] **P1.16 Forward book with kill-switches.** Pre-committed fail criteria (e.g., 90 days or 30 round-trips; if CI lower bound of excess return ≤ 0 → retire). Replicate `cot_positioning` falsification.
- [ ] **P1.17 Deliverable:** per-pod `REPORT.md` + verdict; update `HYPOTHESES.md` statuses. Decay rates (e.g., stat-arb 1.44 → 0.9) must be reported alongside headline Sharpe.

**Exit criteria:** at least one pod reaches `PROVISIONAL` (passes all gates on train + first OOS window) OR a documented negative result with the failing gate recorded. Negative results are valid and publishable.

---

## Phase 2 — Portfolio construction: where the money actually lives (Days 30–60)

**Goal:** build the boring barbell. (Illustrative, not personalized financial advice; size with your own risk tolerance/horizon; consider registered accounts TFSA/RRSP for tax sheltering.)

### TODO — Phase 2
- [ ] **P2.1 Core 70–85%:** low-cost diversified index beta — all-equity ETF (XEQT/VEQT) + global bond ETF (or CanadianCouchPotato-style mix), ER ≤ ~0.20%. Captures the ~90% 10-yr win rate already measured in `MF_CAN_WIN.md`. **This is the "mutual funds that work" — the wrapper beats the average active manager by construction (SPIVA: ~93% of large-cap active trails over 20y).**
- [ ] **P2.2 Satellite 10–25%:** premia sleeves P1/P2 (or managed-futures ETFs: Horizons HMF / DBMF / KMLM-style). Expect low single-digit alpha + crisis convexity, not moonshots.
- [ ] **P2.3 Speculative sleeve ≤5%:** forward-paper pods from Phase 1 only after gates pass.
- [ ] **P2.4 Vol-target the satellites** (12% annualized portfolio vol target baseline); fixed drawdown circuit-breaker (satellite −15% → halves, −25% → pause); never let sleeve #3 touch #1.
- [ ] **P2.5 Factor neutralization + diversification across uncorrelated streams.** Target: 10 streams @ Sharpe 0.5, ρ≈0.1 → stack Sharpe ≈ 1.5.
- [ ] **P2.6 Cost audit across all classes.** FOREX rollover, crypto funding, fund ERs, prediction-market fees (already done for PM — replicate). Fee audits, maker rebates, tax location, turnover caps.
- [ ] **P2.7 Benchmark-first UI.** Every tile shows `excess vs matched-exposure benchmark`, IR, down-capture. Hide raw "PF" — it misleads.
- [ ] **P2.8 Deliverable:** `PORTFOLIO_CONSTRUCTION.md` + allocation table + circuit-breaker spec.

---

## Phase 3 — ML & prediction stack, but only as meta-labeling (Days 45–75)

**Goal:** ML predicts "will this signal's trade work?", never the price. LLMs as text→features at low cadence. Drop structurally broken components.

### TODO — Phase 3
- [ ] **P3.1 Meta-labeling.** Primary model = P1/P2/P3 signal; secondary ML estimates P(profit | features); size ∝ calibrated probability (López de Prado). Purged group K-fold + embargo; point-in-time features; calibration curves (Brier), not accuracy.
- [ ] **P3.2 Prediction markets: maker-only, 85–95¢ favourites, Brier-tracked, pre-registered break-even vs fee curve.** Otherwise treat Polymarket/Kalshi odds purely as a *probability oracle* feeding other models. `PREDICTION` class must exist first (P0.3a).
- [ ] **P3.3 LLMs as text→features** (filing language deltas, tone change, risk-factor churn) at low cadence; enforce point-in-time document timestamps.
- [ ] **P3.4 Drop:** copy-trading (structurally −2 fees, late fills, leaderboard survivorship), intraday ML on daily features, ensemble-of-700-models voting (variance without economics — diminishing returns vs trial-inflation penalty).
- [ ] **P3.5 Drop the six-gate synthetic claim.** Re-run `six_gate_validated_strategy.py` on real data before any claim; the current PASS is on synthetic embedded-signal data and proves nothing about live edge.
- [ ] **P3.6 Deliverable:** `ML_META_LABELING_SPEC.md`.

---

## Phase 4 — Live validation, governance, honest reporting (Days 60–90+)

**Goal:** forward-clock review vs kill criteria; decide PROMOTE / RETIRE; publish honest post-mortem either way.

### TODO — Phase 4
- [ ] **P4.1 Forward clock.** ≥90 days paper trading on real fills (or simulated with real fills) before any live capital. Track per-pod: trades, WR, PF, excess vs benchmark, IR, down-capture, max DD.
- [ ] **P4.2 Kill-switches enforced.** CI lower bound of excess return ≤ 0 → retire. Satellite −15% → halves, −25% → pause.
- [ ] **P4.3 Decay monitoring.** Track rolling 30/60/90-day performance; retire signals on decay (McLean–Pontiff). Capacity cap per sleeve.
- [ ] **P4.4 One global trial counter** feeding DSR everywhere; retire any pod that hits N > cap without forward success. Pre-commit: if after 2 more independent forward windows no pod passes, conclude *no edge on available data* and reallocate effort to execution/costs.
- [ ] **P4.5 Effective-N accounting** encoded (López de Prado / Bailey DSR at cumulative N).
- [ ] **P4.6 Hypothesis registry enforced** — "no row deleted"; pre-registration before any backtest (M-107).
- [ ] **P4.7 Adversarial review gate** mandatory before any promotion, including dashboards.
- [ ] **P4.8 Benchmark-first UI** live on `/audit` (excess, IR, down-capture; hide raw PF).
- [ ] **P4.9 Publish the honest sentence on the dashboard:** "No class is money-ready; here is the benchmark-relative number." (Goal, not a bug.)
- [ ] **P4.10 Final 90-day post-mortem.** Write the honest post-mortem either way (PROMOTE or RETIRE) and publish it — more valuable than the 700 strategies.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Verified edges (`quan_engine`, `st_rsi_momentum_confluence`) were lucky, not real | Bootstrap CI + walk-forward under locked OOS gates before any promotion (P0.9) |
| Regime changes again | Rolling 7-day re-evaluation + regime router (P0.7, P0.8) |
| Overfitting to 3 strategies | Still run 100+ strategies in background; only promote validated ones |
| User sees fewer picks | Quality > quantity; transparent filtering (P4.9) |
| Ledger still broken → all numbers fiction | P0.3 hard prerequisite; nothing downstream until integrity passes |
| Synthetic six-gate claim promoted as real | P3.5 explicitly re-runs on real data |
| Trial inflation from 700+ strategies | Global trial counter + effective-N + DSR at true N (P0.1, P1.0, P4.4) |
| Cost leakage (1bp/day ≈ 20%/yr) | Cost audit + maker rebates + turnover caps (P2.6) |
| Edge decay post-publication | Decay monitoring + capacity cap + retire (P4.3) |
| Scope creep / new swarms | Freeze candidate generation gate (P0.1) |

---

## Success metrics (write on dashboard)

| Metric | Current | Target (90 days) |
|---|---|---|
| Verified edges emitted (gated) | 0 | 50–100 picks/week per passing pod |
| Pilot net PF | N/A | > 1.2 net |
| Pilot WR | N/A | > 55% |
| Score–PnL correlation | +0.008 | > +0.3 |
| Static kill list size | 40+ | Dynamic, regime-aware |
| Classes with proven edge | 0 | ≥ 1 (or honest negative result) |
| Excess return vs matched benchmark | not reported | reported per class |

---

## 90-day calendar (from external review §6, adapted + 2026-11-20 synthesis)

- **Days 1–14:** Phase 0 prune + ledger fixes + PREDICTION class + cost/benchmark gates in verdict pipeline. Archive dead workflows; CI < 30 min. Unify `quan_engine`/`st_rsi_momentum_confluence` claims under locked OOS gates.
- **Days 15–30:** Pod A (equities stat-arb PCA + sector-ETF residual) pre-registered; reproduce literature stats (Sharpe 1.44 → expect ~0.9) on 1990–present; leave last 24 months untouched holdout. Pod B (cross-sectional momentum) same protocol. Pod C (energy calendar-spread MR, Kalman hedge ratios) reproduce 22y result.
- **Days 31–45:** Start Pod A/B forward paper on $5–10k notional. Pod D (G10 carry + trend filter) + triangular-arb micro-pod. Pod E PEAD pipeline fix + screen. Crypto execution-quality cost audit (multi-venue routing, DEX slippage, cost-aware filter). Benchmark-relative dashboard cards. Fee audit across all classes (FOREX rollover, crypto funding, fund ERs).
- **Days 46–75:** Pod E PEAD live. Pod F/G/H optional (index-inclusion, insider clusters, ETF intraday pairs). Fixed-income liquidity-discovery research. Alt-data news-count research (point-in-time + placebo). Top-gainer factor-exposure decomposition. Meta-labeling spec. Maker-only PM framework. Decay monitoring wired. Report decay rates alongside headline Sharpe.
- **Days 76–90:** Forward-clock review vs kill criteria (90 days / 30 round-trips; CI lower bound of excess ≤ 0 → retire). Decide PROMOTE / RETIRE per pod. Write honest post-mortem and publish — more valuable than the 700 strategies. If no pod passes after 2 independent forward windows, conclude no edge on available data and reallocate to execution/costs/beta.

---

## What NOT to do (explicitly)

From external review §3, plus the 2026-11-20 research synthesis:
- No more strategies, no more swarms, no more mutation engines until a candidate reaches `PROVED`.
- No daily crypto single-name RSI2, TP/SL scalps, fixed-TP score bands, 50¢ Polymarket taker forecasting, meme/gainer ML, "milestones"/spike reversal reverse-engineering.
- No ensemble-of-700-models voting (variance without economics).
- No copy-trading (structurally −2 fees, late fills, leaderboard survivorship).
- No intraday ML on daily features.
- No building a universe from today's winners (survivorship bias) or tuning to match a winner list (deflated Sharpe inflation) — use factor-exposure decomposition instead.
- No news-count features without point-in-time construction + placebo test + cost survival.
- No claiming prediction-market edge without sourced exchange docs/fee schedules.
- No claiming the six-gate synthetic result as live edge (re-run on real data first).
- No broad globs in audit-dashboard paths (infinite-loop risk).
- No re-adding `push:` trigger to `audit-dashboard.yml` without re-reading the 2026-05-19 removal rationale.

- No more strategies, no more swarms, no more mutation engines until a candidate reaches `PROVED`.
- No daily crypto single-name RSI2, TP/SL scalps, fixed-TP score bands, 50¢ Polymarket taker forecasting, meme/gainer ML, "milestones"/spike reversal reverse-engineering.
- No ensemble-of-700-models voting (variance without economics).
- No copy-trading (structurally −2 fees, late fills, leaderboard survivorship).
- No intraday ML on daily features.
- No broad globs in audit-dashboard paths (infinite-loop risk).
- No re-adding `push:` trigger to `audit-dashboard.yml` without re-reading the 2026-05-19 removal rationale.

---

## Realistic expectations (Grok external review, 2026-11-20)

- A realistically well-executed residual mean-reversion + modest momentum book is **mid-single-digit to low-double-digit annualized net** at moderate volatility and low market beta — **not** 100% years.
- The literature's best Sharpes (1.5–2) are sample-specific and often pre-cost or pre-decay. Most retail implementations fail on costs, overfitting, or regime change.
- Best solo transparent 12-year public track record tops out around **0.8 Sharpe** — the bar for a systematically tradeable strategy is Sharpe territory essentially no individual verifiably reaches without institutional capital and access.
- Symbol-specific mining: 1,285 variants tested with real costs/OOS/pre-registration/deflated-Sharpe gate → bar ~0.8 Sharpe. LLM agent 2.12 in-sample → +0.18 OOS. 136k strategies from accounting ratios/returns/tickers → top 1% predicted Sharpe earned 5.70%/yr OOS vs 5.88% avg of 200 published, but Sharpe 1.46 vs 2.03 (published carry look-ahead).
- Decay monitoring specifics: rising residual half-life, IC turning negative, costs exceeding assumptions, or turnover rising while gross alpha stays flat → pause, do not retune the curve.
- FOREX in our data: consistent loser (PF ~0.28). Bonds: tiny samples, liquidity-discovery not price prediction. Crypto: execution/microstructure dominate; directional accuracy 53-56% is not a strategy.

## References (canonical)

- `EDGE_REVIEW_2026-11-19.md` — independent review (Arena agent).
- `research/profitability/PROTOCOL.md` (+ v3, v4, ADDENDUM_1) — locked pre-registration.
- `research/profitability/HYPOTHESES.md` — registry (no row deleted).
- `docs/ALL_STRATEGIES.md` — 700+ strategy inventory (multiple-testing source).
- `docs/STRATEGY_VALIDATION_GATES.md`, `docs/STRATEGY_LIFECYCLE_POLICY.md`, `docs/STRATEGY_TRUST_RANKING.md`, `docs/STRATEGY_FAILURE_ANALYSIS_FRAMEWORK.md`, `docs/STRATEGY_DISCOVERY_PROTOCOL.md`.
- `docs/STRATEGY_PER_ASSET_CLASS_MASTERPLAN.md`, `docs/IDEAL_STRATEGY_PORTFOLIO.md`, `docs/HOLY_GRAIL_CRYPTO_STRATEGY.md`.
- `PLAN_PATH_TO_PROFITABILITY.md` — verified-edges claims (re-test first).
- `KIMI_RISEOFTHECLAW/STRATEGY_RESEARCH_FRAMEWORK.md` + folder.
- `tools/kimi_research_2026_05_20/` — six-gate report (synthetic; re-run on real data) + per-asset-class reports + `MASTER_INTEGRATION_SUMMARY.md`.
- `DEFINITIVE_HEDGE_FUND_PIPELINE.md`, `HEDGE_FUND_ENHANCEMENT_PLAN.md`, `HEDGE_FUND_QUALITY_ROADMAP.md`.
- `DEEP_RESEARCH_*.md` (behavioral finance, microstructure, ML/AI trading, options vol, portfolio construction).
- `copy_trading_research_report.md`, `PREDICTION_MARKETS.md`, `crypto_prediction_*`.
- `BOND_FIXED_INCOME_REPOS_2026-11-18.md`, `CRYPTO_REPOS_2026-11-18.md`, `EQUITIES_REPOS_2026-11-18.md`, `FUNDS_ETF_REPOS_2026-11-18.md`, `FX_MACRO_COMMODITY_REPOS_2026-11-18.md`, `PREDICTION_MARKET_REPOS_2026-11-18.md`.
- `MF_CAN_WIN.md`, `PROFITABLE_APPROACH_PROVEN.md`, `TRUE_PROFITABILITY_VALIDATED.md`, `honest_engineering_projection.md`.
- `STRATEGY_GRAVEYARD.md`, `TRAPPED_STRATEGIES_2026-03-25.md`.
- `transaction_cost_model.py`, `risk_management/`, `regime_detector.py`, `statistical_validator.py`, `walk_forward_validator.py`, `rigorous_validation_protocol.py`, `leak_free_audit.py`.
- Skills: `hypothesis-registry`, `hypothesis-registry-explained`, `money-maker-ready` (+ v2, June/July 2026 editions), `thingstocheck-june2026`, `audit-pick-flow`, `audit-pick-flow`.

---

## Notes on realism

- This plan assumes the user (Toronto-based, retail scale) wants a real, defensible edge, not a marketing number. The honest endpoint may be "no edge on available data" — that is a valid and publishable outcome (PROTOCOL §1).
- Nothing here is personalized investment advice. Sizing depends on individual risk tolerance, horizon, tax situation (TFSA/RRSP), and jurisdiction.
- The 90-day plan is a *floor* for honest validation, not a promise of profit. Premia can be negative in any 90-day window; the test is multi-year, cost-adjusted, benchmark-relative.
- If Phase 1 produces no passing pod after 2 independent forward windows, the correct conclusion is to stop searching for alpha on available data and reallocate effort to execution, costs, and beta — which by itself (low-cost index core) already beats ~93% of active managers over 20 years.

---

*End of plan. Phases are sequential; do not skip Phase 0. Each phase has an exit criterion; do not advance without meeting it or documenting why.*

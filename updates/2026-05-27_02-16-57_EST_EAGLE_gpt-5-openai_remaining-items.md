# EAGLE Remaining Items After Strategy Audit

Generated: 2026-05-27 02:16:57 EST
Model/provider: GPT-5 / OpenAI Codex
Purpose: backlog left after the quick-win strategy audit. These items should become incidents, enhancements, experiments, or PRs in the dashboard roadmap.

## Highest-Priority Remaining Work

1. Fix outcome-ledger integrity before changing production gates.
   - Evidence: `audit_dashboard/data/db_health.json` is red for validator freeze/open bloat, WON/PnL contradiction, PnL mismatch, and ghost-row contamination.
   - Next PR: add a health freeze that blocks money-ready promotion and gate exemptions when DB health is red.

2. Build the rejected-pick counterfactual ledger.
   - Evidence: current data can show rejections and missed gainers, but cannot prove that safety gates consistently filtered future winners.
   - Next PR: record every rejected pick with gate name and resolve it as if it had opened.

3. Add dashboard support for roadmap ownership.
   - Evidence: incidents and enhancements exist, but roadmap state, success metrics, PR links, and experiments are not first-class.
   - Next PR: create `audit_roadmap_items`, `audit_rejected_pick_outcomes`, and `gate_exemption_trials`.

## Asset-Class Remaining Items

### Equity / Stocks

- Split production universe into `LARGE_CAP_EQUITY_SYMBOLS` and `RESEARCH_ONLY_SPECULATIVE_SYMBOLS`.
- Replay score 55-60 large-cap rejections, especially QQQ, AMD, TSLA, AAPL, and SPDR-adjacent names.
- Add ADV, spread, and price-quality gates to stop penny/speculative names from polluting the equity class.
- Wire the VIX-regime sidecar into the equity production gate.
- Promote PEAD/factor sleeves only through probation with clean forward sample.

### Crypto

- Convert `missed_gainers_log.json` into a daily missed-gainer dashboard.
- Separate missed causes into not-in-universe, no-strategy-fire, gate-rejected, and source-trust-rejected.
- Shrink production to liquid core BTC/ETH/SOL/top L1 names while keeping speculative names research-only.
- Add ADV/liquidity gate at runtime.
- Wire funding-rate and on-chain confirmation before expanding the universe.
- Resolve confidence inversion risk before trusting high-confidence crypto picks.

### Forex

- Keep broad forex emission hard-disabled or research-only.
- Limit pilot to a documented major-pair universe.
- Add DXY, session, carry, and real CFTC FX COT features.
- Track SHORT-bias separately from LONG results.
- Require clean n >= 50, PF > 1.3, WR > 50%, and no concentration breach before any promotion.
- Decide whether external verified MQL5/MyFXBook signals are a better source than internal forex generation.

### Bonds

- Wire `bond_scanner.py` for research-only output.
- Build relative-value pilots for TLT/IEF, TIP/IEF, and HYG/LQD.
- Add FRED yield curve, MOVE, real-rate, inflation-breakeven, and credit-spread features.
- Keep real sizing blocked for 90 days after scanner wiring.
- Raise dashboard warnings when bond sample size is below promotion threshold.

### Commodities

- Regenerate commodity metrics after COT deduplication.
- Enforce one pick per `(symbol, COT_report_date, direction)`.
- Add COT publication-lag guard.
- Cap CT=F and any single commodity contribution above 25-30%.
- Add diversified carry/momentum pilots beyond cotton.
- Publish raw vs deduped vs pilot metrics in the incidents dashboard.

### ETFs

- Schedule `etf_sector_emitter.py`.
- Make VIX < 25 the default sector-rotation gate.
- Add SPDR sector-only mode with concentration caps.
- Compare Faber tactical allocation, Antonacci dual momentum, and current emitter results.
- Keep ETF promotion separate from equity until ETF-specific forward sample is clean.

### Futures

- Decide whether to merge the separate FUTURES tile into COMMODITY/CTA.
- If kept separate, wire real financial futures emitters for MES, MNQ, MGC, MYM, and selected rates futures.
- Add term-structure and roll-yield features.
- Retire failed `futures_mean_reversion` and other 0% WR strategies from production dashboards.

### Penny / Cheap / IPO

- Keep penny/meme buckets at 0% allocation.
- Create a separate speculative research universe for cheap stocks and IPOs.
- Required filters: ADV, float, spread, halt risk, borrow availability, SEC filing quality, lock-up expiry, insider selling, and reverse-split history.
- Do not let penny/meme outcomes roll up into parent EQUITY or CRYPTO production statistics.
- Any IPO strategy needs a separate backtest with at least 100 events and lock-up/first-earnings regime tags.

## Gate-Exemption Remaining Items

- Add a formal `GateExemptionTrial` object instead of ad hoc allowlists.
- Exemptions must be scoped by asset class, strategy, symbol, direction, regime, and gate.
- Hot streaks can add a small score bonus only after shadow evidence exists.
- Exemptions must never bypass hard safety gates:
  - stale prices
  - liquidity
  - concentration
  - max loss
  - data-integrity red state
  - unsupported asset class
- Every exemption needs auto-expiry and dashboard visibility.

## Oscillation / Range-Trade Remaining Items

- Add a research-only oscillation detector for liquid pairs and ETF/bond spreads.
- Use cointegration, ADF, Hurst exponent, half-life, spread z-score, and cost-adjusted expected value.
- Start with TLT/IEF, TIP/IEF, HYG/LQD, SPDR sector spreads, and a small FX major list.
- Do not run this on penny stocks, memecoins, or low-liquidity alts.
- Dashboard must report failed mean-reversion families alongside any candidates to avoid survivorship bias.

## Dashboard Roadmap Insertions

Add or update these items in the incidents/enhancements feed:

- OVERALL P0: Data health freeze for money-ready promotion and gate exemptions.
- OVERALL P0: Rejected-pick counterfactual ledger.
- OVERALL P1: Unified roadmap item table with owner, status, PR link, evidence, and success metric.
- EQUITY P1: Large-cap score 55-60 gray-zone replay.
- ETF P1: VIX-filtered sector rotation pilot.
- CRYPTO P1: Missed-gainer universe/trigger audit.
- COMMODITY P0: COT dedup truth table and regenerated metrics.
- FOREX P0: Broad forex disable plus majors-only pilot.
- BOND P1: Scanner wiring plus relative-value pilot.
- FUTURES P2: Merge/deprecate futures tile or wire financial futures.
- PENNY P0: Production quarantine and parent-class pollution guard.

## Open Questions

- Which database is the source of truth for rejected picks once the resolver is added: existing `ejaguiar1_stocks` tables or a new audit schema?
- Should gray-zone candidates route to paper trading, dashboard-only shadow mode, or both?
- Should asset-class promotion thresholds be global, or should each class define its own n/PF/WR/Sharpe/MDD minimums?
- Should speculative/IPO research be visible on the public dashboard, or kept internal until it has enough clean sample?

## Verification Left

- No production strategy code changed in this pass.
- No DB migration was applied.
- No live paper-trade request was sent.
- The remaining items above need PR-by-PR implementation and forward validation.

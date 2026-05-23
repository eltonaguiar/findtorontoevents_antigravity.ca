# Institutional P/L Enhancement Set by Asset Class (2026-05-15)

Purpose: review the daily-ideas files and current `/audit` state, then define a focused set of enhancements to improve P/L, profit factor, and institutional readiness per asset class.

Reviewed sources:
- `DAILY_IDEAS.MD`
- `reports/daily_ideas_synthesis_2026-05-15.md`
- `daily_ideas_KimiCode.MD`
- `daily_ideas_Kilocode_laguna.MD`
- `daily_ideas_nvidia.MD`
- `daily_ideas_ghcopilot_auto.MD`
- `reports/daily_ideas_edge_per_class_20260513T010800Z.md`
- `C:\Users\zerou\DAILY_IDEAS.MD`
- Current dashboard snapshot: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`, generated `2026-05-15T22:48:53Z`

## Institutional Target

Use this as the promotion bar before treating any class as real-money/institutional:

- Profit factor >= 2.0.
- Win rate >= 55%.
- Max drawdown <= 10%.
- `resolved_n >= 200` clean, post-noise-filter trades.
- DSR >= 0.95 and PBO < 0.05 where a backtest is used.
- 30-day shadow/live paper period with net-of-cost PF holding above Tier-2 floor.
- No class can graduate while its P/L depends on unresolved picks, stale model output, direct frontend market-data calls, or silent DB/workflow failure.

Tier-2 operating floor for pilot sizing remains PF > 1.5, WR > 50%, MDD < 20%, `resolved_n >= 100`.

## Current State Snapshot

| Asset class | Current PF | WR | resolved_n | Total P/L % | State | Immediate verdict |
|---|---:|---:|---:|---:|---|---|
| COMMODITY | 2.44 | 60.9% | 343 | +602.05 | Strong but concentrated | Scale only after COT dedup re-aggregation and concentration cap |
| EQUITY | 1.55 | 51.4% | 426 | +375.86 | Tier-2 candidate | Improve PF/WR via VIX, large-cap split, PEAD, cost model |
| ETF | 1.33 | 57.4% | 108 | +38.52 | WR good, PF weak | Debug emitter and add regime/concentration controls |
| CRYPTO | 1.30 | 46.2% | 8114 | +2689.87 | Huge volume, diluted edge | Starve weak sources, add hour/funding/liquidity gates |
| FOREX | 0.87 | 55.2% | 308 | -14.97 | Improved but still negative P/L | Hard-gate long/toxic pairs; carry-only rehab |
| BOND | 0.66 | 54.5% | 11 | -1.53 | Too thin | Unblock emissions and collect credible n |
| FUTURES | n/a | 0.0% | 0 | 0.00 | Starved | Fix classification and shadow emissions |

Concentration risks from current dashboard:
- COMMODITY: CT=F is 73.62% of class share; top strategy is `cot_positioning`.
- FOREX: USDJPY=X is 39.91%; top strategy is `cta_fx_multifactor`.
- ETF: XLE is 19.65%; top strategy is `intermarket-flow-scout`.
- CRYPTO: BTCUSDT share is acceptable at 10.27%, but top strategy is `luxalgo_confluence`; source-level dilution is the issue.
- BOND: TLT is 78.92%, but n=11 makes the concentration metric non-decisive.

## Portfolio-Wide Enhancements First

These are the highest-return fixes because they stop false P/L, stale data, and bad flow across every class.

### P0-1: Physical gate parity, not dashboard-only safety

Action:
- Wire `kill_gate.evaluate_kill()` and PCG-5 style portfolio gates into `passes_active_gate`.
- Mirror the same decision in the paper-trading pre-execute path so paper/live do not diverge.
- Log every rejection reason into a compact audit file for dashboard review.

P/L benefit:
- Prevents known-red systems from continuing to emit picks and stops hidden P/L bleed from "disclosure-only" warnings.

Acceptance:
- Synthetic RED/HALT state produces zero emitted, sized, or executable picks.
- Existing kill-switch tests and gate-parity tests pass.

### P0-2: Use `resolved_n` and MySQL outcomes as the canonical scoreboard

Action:
- Standardize all reports and dashboard payload labels on `resolved_n`, not raw `closed`.
- Add or complete MySQL-native `at_pick_outcomes` / predictor scorecard flow from the KimiCode plan.
- Add cross-DB lifecycle checks: one open, one close, no duplicate close, no impossible P/L, timestamp order valid.

P/L benefit:
- Prevents sizing decisions from inflated PF/WR and catches phantom unresolved picks before they distort strategy rankings.

Acceptance:
- `resolved_n == asset_class_health.n` in deterministic verification.
- Cross-DB lifecycle workflow flags orphaned or duplicate rows.

### P0-3: Confidence calibration enforcement

Action:
- Replace HIGH_CONVICTION dashboard logic with `trust_score` where available.
- Build confidence bucket tracking by asset class.
- Auto-demote or quarantine confidence buckets with large negative calibration gaps.

P/L benefit:
- Stops high-confidence but negative-edge picks from being promoted as premium opportunities.

Acceptance:
- ETF/CRYPTO confidence inversion is visible by bucket.
- Picks from inverted buckets are blocked or heavily size-reduced.

### P0-4: Data freshness and schema guardrails

Action:
- Ship DB freshness guardian and schema drift watchdog for `ejaguiar1_stocks` and `ejaguiar1_backtests`.
- Remove silent-fail workflow wrappers from MySQL sync.
- Add PR guardrails for secrets and SQL migration safety.

P/L benefit:
- Prevents stale-data-driven picks and silent workflow failures from creating bad trades with apparently valid scores.

Acceptance:
- Stale critical tables fail loudly.
- Schema drift creates a clear issue/report before dashboard generation depends on it.

### P0-5: Net-of-cost and drawdown readiness

Action:
- Wire a transaction-cost/slippage model into `score_pick` and `passes_active_gate`.
- Require net PF, not gross PF, for promotion.
- Add per-symbol and per-strategy concentration caps before increasing volume.

P/L benefit:
- Converts headline edge into tradable edge and cuts blow-up risk from one symbol/strategy dominating returns.

Acceptance:
- Each class has gross PF, net PF, MDD, concentration, and DSR visible before promotion.

## COMMODITY Enhancement Set

Current verdict: best class by PF/WR/n, but not institutional until concentration and COT inflation are resolved.

### C1: Re-derive COT edge on post-dedup data

Action:
- Re-aggregate `cot_positioning` after the dedup ledger patch.
- Verify CT=F and `multi_asset_cot` through DB-backed `system_pf_verification`.
- Compute COT-cycle-level MDD, not only hourly-bar MDD.

P/L lever:
- Confirms whether the flagship COMMODITY P/L is a true edge or inflated history.

Acceptance:
- COMMODITY remains PF >= 2.0 and WR >= 55% on post-dedup COT data.
- `multi_asset_cot` verdict is MATCH, not dashboard-inflated.

### C2: Hard concentration cap for CT=F and COT

Action:
- Cap per-symbol COMMODITY P/L contribution at <=30% and per-strategy contribution at <=25% before scaling.
- If cap is exceeded, new CT=F/COT picks become shadow-only until other commodity sleeves catch up.

P/L lever:
- Protects the class from a single-contract reversal wiping out the best current edge.

Acceptance:
- Dashboard concentration warning falls out of red/warn state without class PF collapsing.

### C3: Add commodity diversifiers with external replication

Action:
- Wire `commodity_carry_momo_double_sort` into the scanner if its existing JSON input is current.
- Backtest DBMF/KMLM-style commodity momentum replication.
- Add crude/natgas roll-yield and gold/silver ratio mean-reversion as research sidecars.

P/L lever:
- Keeps PF above institutional floor after CT=F cap by adding independent commodity return streams.

Acceptance:
- Each new sleeve has its own resolved_n, PF, WR, MDD, and correlation to CT=F.

### C4: Weather and supply-chain alt-data pilot

Action:
- Use NOAA/USDA free feeds for corn/wheat/soy/softs.
- Test weather forecast deltas, crop progress, WASDE surprises, hurricane cone impacts, and rig count/capex proxies.

P/L lever:
- Adds event/regime alpha that is economically different from COT.

Acceptance:
- Research remains sidecar until 10-year backtest plus 2024-2026 OOS validation is complete.

## EQUITY Enhancement Set

Current verdict: stable Tier-2 candidate, but PF/WR need lift for institutional status.

### E1: VIX-regime hard gate and one threshold source

Action:
- Merge the VIX hard-filter work after local backtest confirmation.
- Reconcile VIX<22, VIX<25, and VIX>40 logic into one policy module.
- Make the gate explainable in dashboard payload.

P/L lever:
- Existing research claims VIX<22 is the biggest EQUITY PF lever; use it to avoid hostile regimes.

Acceptance:
- Net PF improves and n remains high enough for credibility.
- Hard-gated picks show rejection reason.

### E2: Split large-cap equity from penny/meme exposure

Action:
- Add `LARGE_CAP_EQUITY_SYMBOLS` and an `is_liquid_equity()` helper.
- Remove or separately quarantine NIO/LCID/RIVN/GME/AMC-style gap-risk names from the institutional EQUITY lane.
- Route any microcap experiment to a blocked/pilot class with no default sizing.

P/L lever:
- Raises reliability of EQUITY P/L by removing high-gap-risk names from the same bucket as liquid large caps.

Acceptance:
- EQUITY PF/WR are reported separately for liquid large-cap vs speculative names.

### E3: PEAD top-100 equity strategy

Action:
- Build a PEAD strategy on liquid top-100 equities using real earnings dates.
- Use two-day and five-day post-earnings windows.
- Compare surprise, revision, volume, and gap-follow-through variants.

P/L lever:
- Adds a proven academic/event-driven anomaly to the class already closest to scalable equity quality.

Acceptance:
- PF > 1.5, WR > 50%, n >= 100, and net-of-cost edge survives after earnings-date integrity checks.

### E4: Corporate-relationship and filings alpha

Action:
- Build an EDGAR/SAM.gov/USPTO relationship-arbitrage sidecar.
- Start with 8-K partnership keywords, government contract awards, patent assignments, and supplier/customer mentions.
- Map events to liquid affected stocks or ETFs.

P/L lever:
- Creates a differentiated event-driven signal that is not just price momentum.

Acceptance:
- Must prove lead/lag timing and avoid lookahead bias before scanner wiring.

### E5: Equity factor sleeves with crash guard

Action:
- Test QMOM/IMOM, value/quality, earnings revisions, insider-buy clusters, and sector rotation.
- Add momentum-crash guard using VIX/trend/macro conditions.

P/L lever:
- Converts EQUITY from a single mixed bucket into sleeves that can be weighted by live performance.

Acceptance:
- Sleeve scorecard shows per-sleeve PF/WR/MDD and correlation.

## ETF Enhancement Set

Current verdict: good WR but PF too low; ETF is close enough to fix, not ignore.

### T1: Debug default-on sector emitter producing zero picks

Action:
- Diagnose why `tools/etf_sector_emitter.py` emits `picks: []` while enabled.
- Add a non-empty assertion or explicit "no candidates because..." reason.

P/L lever:
- Restores intended sector-rotation flow instead of letting mixed ETF flow dominate the tile.

Acceptance:
- Emitter either produces valid picks or emits deterministic rejection reasons.

### T2: ETF VIX/macro regime gate

Action:
- Turn on VIX<25 or equivalent ETF-safe regime gate after confirming backtest.
- Add DXY/yield-curve/VIX overlays from the daily ideas.

P/L lever:
- Raises ETF PF by avoiding unfavorable macro regimes while preserving high WR.

Acceptance:
- ETF PF returns above Tier-2 floor in shadow/live evaluation.

### T3: Sector rotation and risk-parity sleeves

Action:
- Separate ETF picks into sector, broad-market, international, treasury-duration, volatility, and commodity ETF sleeves.
- Backtest monthly vs quarterly rebalance to reduce friction.
- Evaluate post-2022 risk-parity reset and Black-Litterman duration/equity weights.

P/L lever:
- Moves ETF from a mixed low-PF bucket into measurable sleeves that can be capped or boosted.

Acceptance:
- Each sleeve has resolved_n and net PF; no sleeve can exceed 25% class P/L contribution.

### T4: ETF source pruning

Action:
- Cap or demote `intermarket-flow-scout` if its ETF slice remains below PF 1.4.
- Add positive budget to validated `etf_sector_momentum` / `etf_dual_momentum`.

P/L lever:
- Shifts ETF volume from diluted source flow toward cleaner rotation edge.

Acceptance:
- Source-level volume budget is visible and enforced in production scanner.

## CRYPTO Enhancement Set

Current verdict: positive total P/L but below institutional quality because massive volume is diluted by weak sources and sub-50% WR.

### K1: PF-weighted source volume budget

Action:
- Cap `luxalgo_filters` at a lower CRYPTO share and reconcile `quan_engine` cap drift.
- Add `enforce_cap()` to `production_scanner.py`, not only intake.
- Generalize from manual source blocks to PF-weighted source volume budgets.

P/L lever:
- Starves sources that add volume below class PF and preserves capital for proven crypto systems.

Acceptance:
- Dilutive sources fall below cap and class PF/WR improve or hold with lower drawdown.

### K2: BTC UTC-hour filter

Action:
- Add a CRYPTO hour filter behind `CRYPTO_HOUR_FILTER`.
- Reject or shadow 08-09Z death-zone picks.
- Boost or prefer validated 22Z picks only after replay confirmation.

P/L lever:
- Uses a free, already-identified time-of-day edge to reduce losing flow.

Acceptance:
- 30-day A/B telemetry shows drawdown reduction and no net PF decay.

### K3: Liquidity and meme/noise filter

Action:
- Add `is_liquid_crypto()` using real volume/ADV/market-cap proxy.
- Split MEMECOIN from institutional CRYPTO and block default sizing.
- Penalize LONG-only meme/alt sources with poor realized WR.

P/L lever:
- Reduces tail losses and avoids hiding meme risk inside the broad CRYPTO class.

Acceptance:
- MEMECOIN and low-liquidity alts are zero-sized unless a separate pilot clears its own bar.

### K4: Funding-rate and HLP-style carry replication

Action:
- Build a funding-rate carry sidecar using free exchange funding data first.
- Add Glassnode/CFTC keys only if free data cannot support the minimum viable test.
- Test long-spot/short-perp or funding-positive basket logic.

P/L lever:
- Adds economically grounded carry return rather than pure directional crypto prediction.

Acceptance:
- Strategy survives 2024-2026 OOS, transaction costs, funding slippage, and exchange availability constraints.

### K5: Resolver exclusion and stale model cleanup

Action:
- Fix `ml_crypto_pred` resolver-exclusion so closed picks resolve into the scoreboard.
- Quarantine stale systems that no longer emit or no longer validate.
- Continue blocking known anti-edge systems rather than letting old cumulative wins justify new volume.

P/L lever:
- Removes hidden rot and prevents stale historical winners from receiving fresh capital.

Acceptance:
- Resolver coverage >= 95% for CRYPTO closed picks.

## FOREX Enhancement Set

Current verdict: headline WR improved, but total P/L is still negative and PF remains below investable floor.

### F1: Default hard disable until rehab gates pass

Action:
- Keep `FOREX_HARD_DISABLE=1` default-on for production sizing.
- Allow shadow emissions only for rehab sleeves.
- Override only after 30-day carry/regime PF > 1.0 and WR > 45%, then pilot at minimal size.

P/L lever:
- Stops negative class P/L while allowing research to continue.

Acceptance:
- Production FOREX sizing is zero unless explicit rehab conditions pass.

### F2: Directional gate using autopsy results

Action:
- Block toxic LONG paths where live autopsy shows poor WR/PF.
- Prefer SHORT-only or direction-specific strategies only where evidence supports it.
- Implement via reusable directional gate helper, not a one-off FOREX if-block.

P/L lever:
- Removes the highest-impact negative FOREX pattern without killing the entire research lane.

Acceptance:
- Directional gate decisions are visible by pair/strategy/direction.

### F3: Pair allowlist and concentration cap

Action:
- Add FOREX allowlist/blocklist from autopsy findings.
- Cap USDJPY=X and any pair above 25% class contribution.

P/L lever:
- Avoids one pair or one macro regime dominating class P/L.

Acceptance:
- No FOREX pair exceeds cap in active/shadow flow.

### F4: Real carry-factor rebuild

Action:
- Replace momentum-first FOREX with G10 carry, rate differential, real CFTC currency COT, and session/time-of-day gates.
- Use MyFXBook/ZuluTrade retail positioning as contrarian input only after lead/lag testing.

P/L lever:
- Moves FOREX toward a known long-run FX anomaly rather than trying to force failed momentum variants.

Acceptance:
- Carry sleeve passes mutate-before-kill protocol and 30-day shadow evaluation.

## BOND Enhancement Set

Current verdict: n=11 makes the class statistically unusable; focus is emission quality and sample growth.

### B1: Lower bond elite floor for low-vol signals

Action:
- Lower `BOND_ELITE_FLOOR` into the 32-35 range in the bond agent/config path.
- Keep any new BOND picks shadow/min-size until n grows.

P/L lever:
- Allows credible bond signals to enter the ledger instead of starving the class.

Acceptance:
- BOND resolved_n starts growing without immediate PF collapse.

### B2: Wire three bond pilots

Action:
- Wire TIPS-breakeven mean reversion, Cochrane-Piazzesi curve carry, and HYG-LQD credit mean reversion.
- Use TLT/IEF/SHY/TIP/LQD as the starting universe.

P/L lever:
- Adds diversified duration, inflation, and credit signals instead of relying on one TLT-heavy bucket.

Acceptance:
- Each pilot emits independently tracked picks and reaches n>=30 before any verdict.

### B3: FRED/Kalshi macro regime context

Action:
- Set up FRED macro cache and no-key Kalshi macro/rate signal where possible.
- Use yield curve, real rates, inflation expectations, and Fed probability context.

P/L lever:
- Improves entry timing for duration and credit trades.

Acceptance:
- No scanner loop can hammer FRED; cache and no-key fallback are mandatory.

### B4: CPCV for small-n bond candidates

Action:
- Use purged/CPCV validation where n is small.
- Label candidates as "insufficient evidence" instead of "bad" until sample grows.

P/L lever:
- Prevents premature killing of potentially useful low-frequency bond strategies.

Acceptance:
- BOND research reports separate insufficient n from true negative edge.

## FUTURES Enhancement Set

Current verdict: not dead, but zero verdict n because classification and emission floors starve the tile.

### U1: Fix futures classification

Action:
- Add `contract_type` tagging so futures are not routed into COMMODITY by broad `=F` logic.
- Decide whether the tile is `FUTURES` or `FUTURES_CTA`; do not leave a zombie tile.

P/L lever:
- Lets the system measure futures P/L honestly instead of hiding it in COMMODITY.

Acceptance:
- FUTURES tile accrues shadow picks and resolved_n.

### U2: Lower confidence floor for shadow accrual

Action:
- Lower futures `conf_floor` from 0.50 to 0.40 only in shadow mode.
- Keep sizing disabled until n>=100 and PF/WR clear Tier-2.

P/L lever:
- Ends the self-fulfilling loop where no futures picks can accrue enough evidence.

Acceptance:
- Shadow ledger grows with rejection/sizing status explicit.

### U3: CTA-style trend and term-structure research

Action:
- Test Donchian trend, time-series momentum, roll yield, seasonality, and COT commercial extremes.
- Separate financial futures, rates futures, ag futures, metals, and energy.

P/L lever:
- Builds futures as a true CTA sleeve instead of a miscellaneous contract bucket.

Acceptance:
- Each contract family reports PF/WR/MDD/correlation separately.

## PENNY / MEME Enhancement Set

Current verdict: not a trustworthy production class; currently leaks into EQUITY/CRYPTO.

### M1: Class-wide block by default

Action:
- Add class-wide `MEMECOIN` and `PENNY_STOCK` fail gates.
- Add `is_low_quality_or_meme()` in config and pre-emit scanner checks.
- Map `CATEGORY_RISK` penny/meme to BLOCK instead of wide SL/TP settings.

P/L lever:
- Stops high-gap/high-manipulation flow from contaminating otherwise investable classes.

Acceptance:
- Zero production-sized penny/meme emissions unless a separate pilot is explicitly enabled.

### M2: Research-only microcap bucket study

Action:
- If revisited, test <$1, <$2, <$3, <$6 bins with float, ADV, dilution, premarket spike, catalyst, and institutional ownership filters.
- Require SHORT/pair-trade variants, not LONG-only pump chasing.

P/L lever:
- Converts the penny idea into a falsifiable edge study without risking current P/L.

Acceptance:
- Any microcap result must survive gap/slippage modeling and pump-dump red-flag exclusion.

## New Alt-Data Research Queue

These should not enter production until they pass data-integrity and caller requirements.

1. EDGAR/SAM.gov/USPTO relationship arbitrage for EQUITY.
2. NOAA/USDA/weather/WASDE for soft commodities and grains.
3. Prediction-market signals from Polymarket/Kalshi for macro, oil, gold, small-cap, and rates context.
4. Crypto whale flows, exchange netflow, dormancy, stablecoin mint velocity, and funding carry.
5. TSA/container/shipping/box-office/sports-betting handle as sector-level leading indicators.
6. China/HK ADR premium-discount and KWEB stimulus regime signals.
7. Options flow/put-call/UOA as an EQUITY/ETF overlay, not a new OPTIONS class until defined-risk infrastructure exists.

Every alt-data item must include:
- Real data source.
- Backtest horizon.
- Lookahead-bias prevention.
- Production caller or explicit wiring plan.
- Cost and rate-limit note.
- Empty-state behavior when data is unavailable.

## Ideas To Deprioritize

- GPU/CUDA/NVIDIA CI work: useful only if a production inference bottleneck exists. Current P/L blockers are data integrity, gates, concentration, and strategy quality, not GPU speed.
- ORM rewrite: not needed for P/L. Stay with existing MySQL connector patterns unless a dedicated DB refactor is approved.
- Broad "20 swarm rounds per class": too expensive and hallucination-prone. Use 3-4 critique-first rounds with citation verification and engine weighting.
- Mutual funds: outside current scanner/dashboard surface. Revisit only after ETF/BOND are stable.

## Suggested PR Sequence

### PR-1: Safety and scoreboard truth
- `kill_gate` + PCG-5 active-gate wiring.
- `resolved_n` naming discipline.
- DB lifecycle/freshness guard.
- Confidence/trust-score high-conviction correction.

### PR-2: Stop P/L leaks
- FOREX hard-disable/directional gate.
- PENNY/MEME class-wide block.
- CRYPTO source caps and production scanner cap caller.
- ETF emitter non-empty diagnostics.

### PR-3: Scale current winners safely
- COMMODITY COT post-dedup verification.
- CT=F and COT concentration caps.
- EQUITY VIX hard gate.
- ETF VIX/macro gate.

### PR-4: Add institutional sleeves
- EQUITY PEAD and factor sleeves.
- BOND three pilots and FRED cache.
- FUTURES classification/shadow emission.
- COMMODITY carry/momentum diversifier.

### PR-5: Alt-data research pilots
- EDGAR relationship arb.
- NOAA/USDA weather commodities.
- Polymarket/Kalshi macro mapping.
- Crypto funding/whale-flow research.

## Promotion Rules

1. A class with negative total P/L cannot receive new production sizing.
2. A class with PF < 1.5 can only run shadow or minimum research sizing.
3. A class above PF 2.0 still cannot scale if one symbol/strategy contributes more than the cap.
4. Stale models and unresolved picks cannot count toward promotion.
5. Any edge that contradicts a current gate must pass mutation analysis before deployment.
6. No fake/sample data. Missing source means empty state or shadow skip.

## Bottom Line

The fastest path to institutional P/L is not adding more models. It is:

1. Make the scoreboard real: resolved outcomes, DB lifecycle checks, freshness, calibration.
2. Stop the leaks: FOREX, penny/meme, CRYPTO weak sources, ETF silent emitter.
3. Scale the best edges carefully: COMMODITY after dedup/concentration; EQUITY after VIX/large-cap/PEAD.
4. Rebuild thin classes in shadow: BOND and FUTURES.
5. Add alt-data only as validated sleeves with real callers and no placeholder data.

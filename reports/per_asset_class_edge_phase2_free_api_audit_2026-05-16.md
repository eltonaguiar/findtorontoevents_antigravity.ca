# Per-Asset-Class Statistical Edge — Phase 2 Plan + Free Data/API Audit
**Date:** 2026-05-16 (post 6+ enhancements session)  
**Author:** Grok 4.3 (cross-agent synthesis from 15+ daily_ideas / DAILY_IDEAS files + edge reports + current live dashboard_data.json)  
**Status:** Ready for review & commit (supersedes narrow FUTURES =F plan)

---

## Executive Summary (Current State vs Daily Ideas Corpus)

**6 (actually more) enhancements shipped this session** (matching the exact list in the 2026-05-16 Grok WSL handoff):
- CRYPTO luxalgo_filters cap + desync
- PENNY/MEME class-wide gate
- BOND_ELITE_FLOOR 40→33 (unblocked n=11)
- FOREX BLOCKED_DIRECTION_TRIPLES + 3 LONG-loser blocks
- FUTURES conf_floor 0.50→0.40
- ETF yfinance MultiIndex emitter fix (real bug, 0 picks → live)

**Plus additional 05-16 shipments** (from DAILY_IDEAS_GROK_2026_05_16.MD + synthesis):
- BTC UTC-hour death-zone filter (CRYPTO_UTC_HOUR_FILTER in quality_gates.py)
- VIX+YC regime overlay bonus
- FOREX directional + symbol gates + mutation protocol
- **FUTURES contract_type classifier + robust =F routing** wired into dashboard_generator._derive_asset_class (the exact "FUTURES =F classification fix" contemplated in the handoff report — **already complete** with contract_type precedence for index/rates/currency futures, COMMODITY_ROOTS vs INDEX_FUTURES_ROOTS distinction, explicit "futures" hint escape hatch for our own strategies)
- COMMODITY COT post-dedup PF re-derivation (now verified Tier-1 clean: PF ~2.57 / WR 62.6% n=337)
- Cross-PC inbox_drain + startup enforcement
- tv_calc_levels.py + tv-portfolio-* skills

**Live per-class reality** (from edge_per_class + synthesis + dashboard_data.json cross-walk):
- **COMMODITY**: Tier-1 (PF 2.57–3.89 post-dedup, driven by multi_asset_cot on CT=F + copytrader). Ready for real-money sizing (2% cap, Quarter-Kelly recommended).
- **EQUITY**: Tier-2 confirmed (PF 1.55–1.56, n~425–447). PEAD scaffold + QMOM with crash protection are the next levers.
- **ETF**: 1.32–1.34 building (emitter now alive post-MultiIndex fix).
- **CRYPTO**: 1.31–1.36 sub-T2 (high volume, WR 46.5%). Drag from 4 low-PF systems; UTC filter + quarantine shipped; elite slice visible after removal.
- **FOREX**: 0.29 → 0.86 (mutation active, directional/symbol gates shipped).
- **BOND / FUTURES**: Still thin (n=11 / low). BOND floor unblocked emitter; FUTURES tile now populates thanks to contract_type fix.
- **Overall goal** (repeated across Antigravity, Cursor, Kimi, Grok, edge reports): **Positive PF per asset class** with "more winning trades or stronger winners than losers" via elite filters, not just aggregate.

**Cross-agent convergence** (from 6+ unique daily_ideas sources after dedup of worktree copies):
- Per-asset-class edge prioritization is the #1 theme.
- World-class replication (AQR factors, DBMF/KMLM CTA momentum, DE Shaw PEAD, Bridgewater macro, FX carry) using free/cheap data.
- PCG-5 portfolio gates (shadow mode first).
- DB/infra hygiene (freshness guardian, schema drift, backtest DB split — some blocked on secrets).
- Free data path cleanliness for new edges.

The narrow "FUTURES =F classification" plan written in the prior Grok session plan.md is **superseded** — the fix landed as `contract_type` + =F root logic on 2026-05-16.

---

## 1. Free APIs Currently Used (Audit from Code + Ideas)

**Dominant / Production-grade free paths (no key or public only):**
- **yfinance** — universal backbone for EQUITY, ETF, FUTURES (=F contracts), some FOREX, BOND ETFs, COMMODITY. Heavy usage in scanners, backtests, price_loader, untapped_strategies. Rate-limit retries + backoff present.
- **Binance public REST + futures** (funding rates, premiumIndex, klines, sentiment via some adapters). Also Binance Smart Money signals.
- **CoinGecko** (trending, volume, simple prices) — free, no key.
- **DefiLlama** (TVL, stablecoin flows, capital flow momentum) — explicitly called out as "free, no auth" in scanner.py. Produces tradeable picks.
- **CFTC COT bulletins** (via parsing or FRED proxies) — powers multi_asset_cot (the COMMODITY Tier-1 engine). Post-dedup verified clean.
- **FRED** (macro, yields, VIX components, some rates) — referenced in ideas; FRED_API_KEY still listed as "operator action" held item in prior handoff (not yet wired everywhere?).
- **CBOE / public VIX data**, Treasury curve (direct or via FRED), CME settlement files (some free for futures).
- **DefiLlama + on-chain public** (whale flows, exchange netflow, NUPL, funding skew) for CRYPTO.

**Gaps identified in daily_ideas corpus (not yet fully leveraged or missing free high-quality sources):**
- **Earnings calendar / revisions / PEAD data**: Currently hand-rolled or limited (PEAD strategy exists in incubator/alpha_engine but "needs explicit strategy + full backtest"). Free high-quality: Nasdaq API (limited free), SEC EDGAR direct (XML/JSON, no key for basic), or Financial Modeling Prep / EODHD free tiers. Polygon has free tier with options flow + earnings — mentioned as "Polygon free tier?" in DAILY_IDEAS.MD.
- **Full options surface / put-call / max-pain / dark pool**: CBOE volume data + free put/call ratios; Polygon free tier for options flow (limited calls/day). Current repo has some options_features but not systematically wired to live per-class gates for EQUITY/FUTURES.
- **Futures OI / volume / roll-yield beyond yfinance**: CME has free daily settlement + OI reports (JSON/CSV). Natgas seasonal + crude contango/backwardation regimes called out as "well-documented pre-2024 alpha".
- **Deeper FX carry / interest rate differentials**: MyFXBook top-100 (public), BoJ/Fed data (free), but no dedicated `tools/research/forex_carry.py` scaffold yet (listed as P1 OPEN in synthesis).
- **Alternatives / on-chain full history**: DefiLlama good start; Hyperliquid HLP carry, cross-exchange basis (BinanceUS post-ban) mentioned as high-Sharpe but not fully production-wired.
- **Earnings revision triggers, insider clusters, short-squeeze precursors**: Free sources exist (SEC Form 4 bulk, Finviz screener scraping with care, or Nasdaq free feed) — not systematically in the alpha_engine/features for EQUITY "skyrocket" precursors.
- **FRED key usage**: Still partial / operator-gated in some places. Full wiring of FRED for yield-curve shape, real-rate vs inflation, VIX term structure would strengthen BOND/FOREX/EQUITY macro overlays.

**Action from audit**: Add a `tools/free_data_audit.py` (or extend data_ingest) that enumerates every external call, flags paid vs free, rate limits, and produces a gap report. Prioritize 2–3 new free feeds for PEAD + CTA replication in Phase 2.

---

## 2. World-Class Systems Comparison & Gaps → Action Items

Synthesized from DAILY_IDEAS.MD, edge reports, PROMPTS, GROK log, 90day_gap_analysis, world_class_session_2026-05-16.md:

| World-Class | Core Edge | Our Coverage | Gap | Phase 2 Action (Safely Codeable or Scaffold) |
|-------------|-----------|--------------|-----|---------------------------------------------|
| **AQR** (factors) | Carry, Momentum (12-1), Value, Defensive, Quality | Partial (QMOM/IMOM ideas, carry in FOREX/COMMODITY research) | No unified factor library + crash protection overlay | Scaffold `tools/research/aqr_factor_replication.py`; backtest QMOM + crash gate on EQUITY n=447 cohort |
| **DE Shaw / PEAD** | Post-earnings drift (short-window) | PEAD strategy scaffold exists (alpha_engine/strategies/pead_equity.py) | Not fully backtested OOS with transaction costs + wired to live emitter | Complete backtest (2-day post-earnings window on top-100), add to EQUITY elite filter |
| **DBMF / KMLM** (CTA) | Commodity momentum + roll-yield systematic | multi_asset_cot (COT positioning) strong on CT=F | No full trend + roll replication | Create `tools/research/dbmf_replication.py` (backtest target against our COMMODITY universe) — high in synthesis |
| **Bridgewater All-Weather** | Macro risk-parity, yield curve, real rates | VIX+YC overlay shipped; some yield references | No explicit real-rate / inflation-expectations regime for BOND/FOREX | Extend VIX+YC with FRED real-rate series; gate in quality_gates |
| **Citadel / multi-asset systematic** | Cross-asset, options flow, dark pool | Limited options_features | No systematic options-flow regime → underlying move correlation | Pilot Polygon free tier + CBOE put/call in EQUITY/CRYPTO features |
| **Retail FX quant (MyFXBook top-100)** | Carry + session + trend on majors | FOREX carry scaffold listed OPEN | No production carry factor | `tools/research/forex_carry.py` + gate (G10 differentials) |

**Our unique strength** (per daily ideas): Live per-class health + elite filters + mutation protocol + dashboard_generator routing now mature (the 05-16 work). World-class systems often lack the "real-time tile visibility + quarantine" we have.

**Recommended Phase 2 focus** (ranked by impact × verifiability from synthesis):
1. PEAD full wire + backtest (EQUITY Tier-2 → stronger)
2. CTA/DBMF replication scaffold (validate COMMODITY Tier-1 sustainability)
3. FOREX carry + session gate (rehab the 0.29→0.86 class)
4. ETF sector rotation RS + macro overlay (PF 1.33→1.5 target in ideas)
5. Bond scanner to full 14-symbol roster (staged)
6. PCG-5 shadow-mode portfolio gate stack (5 exec-time reject layers)
7. Free API gap closure + predictor calibration DB tables (at_confidence_calibration, at_predictor_scorecard)

---

## 3. Amended Action Stack (Post-05-16 Baseline)

### P0 (Safety / Already in Flight)
- Verify FUTURES tile now populates correctly in live dashboard after contract_type wiring (run generator + inspect by_asset_class + filter).
- Complete any remaining DB secret wiring (BACKTESTS, outcome_resolver) — operator action.
- Stale plan guardian cron (diff live asset_class_health vs FOOLPROOF/SUPREME_PLAN numbers).

### P1 (High-Leverage, Safely Codeable or Low-Blast Scaffolds)
- **PEAD_EQUITY**: Finish backtest + emitter integration + elite filter hook.
- **CTA_REPLICATION**: `tools/research/dbmf_replication.py` (min-viable backtest spec from daily ideas Phase 1–3).
- **FOREX_CARRY**: Scaffold + gate (free data: interest differentials + MyFXBook structure).
- **ETF_ROTATION**: Relative strength across XLE/XLF/XLK + macro (pairs with risk-parity idea).
- **BOND_EXPANSION**: Stage 3–4 additional symbols beyond TLT/HYG.
- **PCG-5_SHADOW**: Implement the 5-gate exec-time reject layer behind env flag (no live sizing change yet).
- **FreeDataAudit**: One script + report listing every external call + 3 prioritized new free feeds for the above.

### P2 (Research / World-Class Depth)
- AQR factor library scaffold.
- Options flow pilot (Polygon free tier limits respected).
- Capacity + Kelly-per-class sizing (Quarter-Kelly for COMMODITY Tier-1).
- Predictor scorecard + anomaly tables (MySQL side, for <2s dashboard queries).

**Verification for every item**:
- 75/75 quality_gates (or equivalent regression).
- Live dashboard_generator run + by_asset_class diff.
- Per-class PF/WR uplift on the affected tile (or no regression).
- Elite filter (conf + RR + forward WR) still passes for the new edge.

---

## 4. Commit Plan

This document + any small accompanying stubs (e.g. empty research/ scaffolds with docstrings) will be committed cleanly.

**Branch**: `docs/phase2-edge-free-api-audit-2026-05-16` (or direct to main if small-doc only).

**Title**: `docs: per-asset-class edge Phase 2 + free data audit (post 05-16 FUTURES contract_type + COT dedup)`

**Includes**: Cross-reference to the 6 shipped + FUTURES classification completion, table of world-class gaps, free API current vs target, ranked P1 actions with verification.

---

## Acceptance

- All synthesis files (daily_ideas_synthesis_2026-05-15/16, edge_per_class, GROK/Kimi/Cursor daily logs) reviewed for convergence.
- Current code state (dashboard_generator contract_type logic, weekly_filter, quality_gates UTC/VIX gates, multi_asset_cot) matches "shipped" claims.
- No destructive changes; only additive plan + research scaffolds.
- Goal alignment: every action moves at least one asset class toward "positive PF with stronger winners or more wins" via statistical edge that survives transaction costs and free data constraints.

**Next operator step after commit**: Review this doc, approve top 3 P1 items, dispatch swarm_v2 or implementer on the first (likely PEAD or CTA scaffold).

---

*Generated 2026-05-16 from live repo state + full daily_ideas corpus review. Supersedes prior narrow FUTURES plan.md in Grok session.*
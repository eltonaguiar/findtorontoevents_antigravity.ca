# DAILY IDEAS LOG

## 2026-05-13 — User brainstorm dump (alt-data + asset-class expansion)

Captured for future swarm rounds + backtests. Each block = candidate prompt for `tools/swarm/swarm_run.py --preset non-opus-4 --critique-first`.

### IDEA-A: Top proven criteria per asset class (20-round research)

Run 20 swarm rounds per asset class harvesting proven academic + practitioner criteria. After research, backtest the criteria, cross-check against existing safety gates / entry criteria. Use Python TA pattern finding (pandas-ta, mplfinance, pyti). Goal: enumerate what actually works per class.

Sub-prompts:
- EQUITY: value stocks (P/E, P/B, EV/EBITDA), long-term patterns, financial-statement deltas, earnings-revision triggers, "skyrocket" precursors (insider buy clusters, short-squeeze setups, breakout-on-volume, sector rotation entry).
- CRYPTO: on-chain whale flows, funding rates, NUPL extremes, dormancy flow, exchange netflow, stablecoin minting velocity.
- BOND: credit-spread regimes (HYG-LQD, TED), yield-curve shape, real-rate vs inflation expectations.
- FOREX: interest-rate differentials, BoJ/Fed policy divergence, CoT FOREX section.
- FUTURES: COT commercial extremes (already wired), seasonality (grain harvest cycles, energy winter draws), term-structure backwardation.
- ETF: macro-regime overlays (VIX, yield curve, DXY).

### IDEA-B: Penny stocks revisit

Existing repo likely has penny-stock page. Re-validate at <$6 / <$3 / <$2 / <$1 buckets. Per-bucket edge analysis: is sub-$2 universe systematically different from $3-$6 bucket? Find the bucket with the cleanest risk/reward.

Sub-prompts:
- Microcap WR + PF historical by float-size bin
- Pump-and-dump red flags (premarket spike + dilution filing + zero institutional)
- Catalyst-driven moves (FDA, merger announce, contract win)

### IDEA-C: Mutual funds (no-load + low-redemption-fee)

User point: "we get in and out without being locked in. with mutual funds we would likely pay hefty commission but there are certain mutual funds technically we could buy and hold and get out." Filter for no-load / no-12b1 / no-redemption-fee / no-short-term-trading-restriction. Vanguard / Fidelity / Schwab class candidates.

Sub-prompts:
- yfinance fund universe filter for `quoteType=MUTUALFUND` + `expense_ratio < 0.5%` + `front_load=0` + `back_load=0`
- 5y / 10y Sharpe per-fund ranking
- Compare to ETF equivalents — is the fund version worth it?

### IDEA-D: Options data + correlation to underlying

Options flow (Polygon free tier? CBOE volume data?), put/call ratios, max-pain analysis, dark-pool prints. Correlate option-flow regime to next-week underlying move.

Sub-prompts:
- Put/call ratio extremes as contrarian signal
- Unusual options activity (UOA) detector — calls bought above ask in size as bullish lead
- Max-pain pin theory near OPEX

### IDEA-E: "Secret patterns" — corporate-relationship arbitrage

User example: vendor known associated with Samsung → SEC filing or partnership announcement → trade Samsung-related ETF or supplier stock before broader market notices. Generalize: SEC 8-K + 13D/G filings, EDGAR full-text search for partnership keywords, GovTribe contract awards, USPTO patent assignments, court-docket data (PACER), import/export bills of lading (Panjiva / Import Genius free tiers).

Sub-prompts:
- Detect supplier-relationship announcements via EDGAR 8-K keyword search
- Patent assignments → predict M&A or partnership 30-60 days ahead
- Government contract awards (SAM.gov) → small-cap winner signals

### IDEA-F: Chinese / Hong Kong markets

HSI / SSE / SZSE indices, ADR universe (BABA, JD, BIDU, PDD), KraneShares ETFs (KWEB, KBA, KGRN). Trade A-share-ADR premium/discount as stat-arb. Cross-listed pairs.

Sub-prompts:
- HSI vs SPX correlation regime detection (decoupling phases)
- China stimulus headlines → KWEB momentum
- PBoC liquidity injection schedule as macro tilt

### IDEA-G: Gas-price correlation

Natural gas (NG=F, KOLD/UNG) + gasoline (RB=F) prices ↔ consumer-discretionary spend, transportation stocks, refiners (XOM, CVX, MPC, VLO). Lag/lead — does gas price spike predict consumer-staples relative-outperformance?

Sub-prompts:
- WTI/Brent → consumer staples vs discretionary ratio
- NG winter draws → utilities momentum
- Refinery crack spreads → refiner-stock alpha

### IDEA-H: Polymarket data correlation

Prediction-market prices (Polymarket, Kalshi, PredictIt) → equity/macro signal. User caveat: correlation ≠ causation; investigate hidden factors.

Sub-prompts:
- Election market odds → small-cap risk-on bias (R) or healthcare bias (D)
- Geopolitical event markets → oil/gold spike forecasting
- Fed-meeting probability markets → STIR (short-term interest rate) trade
- Causation check: do Polymarket odds LEAD or LAG the underlying market?

### IDEA-I: Weather → farming / soft commodities

Forecast rain (NOAA GFS, ECMWF, weather.com API) → corn/wheat/soy futures (ZC/ZW/ZS=F). Drought monitor + crop-progress weekly (USDA WASDE).

Sub-prompts:
- 14-day precipitation forecast Iowa/Illinois → ZC=F directional bias
- ENSO regime → soft commodities (sugar, coffee, cocoa, OJ)
- Hurricane cone → energy (refinery shutdowns) + insurance vol

### IDEA-J: Mining equipment costs vs minerals / commodities

Caterpillar/Komatsu capex cycles + steel input cost (HRC futures) → leading indicator for copper (HG=F), iron ore, coal. Miner capex cuts = commodity base.

Sub-prompts:
- CAT ER guidance → next-quarter copper trend
- Baker Hughes rig count → 6-month WTI direction
- AISI steel mill utilization → HG=F leading indicator

### IDEA-K: Weddings vs diamond prices

US wedding count (Knot industry report) + India gold demand (WGC quarterly) → diamond price (Polished Prices index), gold (GLD), Signet (SIG). Wedding count = seasonal + demographically forecastable.

Sub-prompts:
- US marriage rate vs SIG revenue
- India festival calendar (Diwali, wedding seasons) → gold imports → GLD seasonal alpha
- Lab-grown vs natural diamond divergence

### IDEA-L: Other alt-data threads

- Cruise-ship bookings (CCL, RCL, NCLH ER lookahead)
- TSA throughput → airline + hospitality
- Container shipping rates (Drewry WCI, Freightos FBX) → FDX, UPS, XPO, MATX
- Box office revenue → DIS, NFLX
- Sports betting handle (state DGE reports) → DKNG, FLUT, MGM
- Job postings (LinkedIn/Indeed Hiring Lab) → labor leading indicator
- Subway turnstile data (NYC MTA open data) → urban-recovery proxy
- Crypto whale-wallet labels (Arkham, Nansen free tier) → smart-money flow
- Reddit WSB mention velocity → meme-stock squeeze precursor (partially wired)

### Execution plan

Phase 1: pick 3 ideas with cleanest free-tier data path. Score each on: (a) data accessibility, (b) backtestable horizon ≥10y, (c) economic logic strength.
Phase 2: run 4-engine swarm on each (~$0.07 × 3 = $0.21) asking for falsifiable hypothesis + minimum-viable backtest spec.
Phase 3: implement min-viable backtest with yfinance + free feeds. Tier-classify.
Phase 4: cross-check against existing safety gates. New edge contradicting a gate → mutation-axes analysis before deploy.

## 2026-05-12 — Hedge-fund-rescue swarm brief (post-Round-14)

User directive at end of Round 14 (Week 1 rescue complete):

> Add this to daily_ideas.MD and ask our agent swarm over 10 rounds to
> build a document together. Make them build individual documents, I
> review and merge, then have them each give final feedback on the merged
> document.
>
> **How to get this to a hedge fund level performance.** Let's say I was
> hired as a Quant to save this company and fix their performance by asset
> class — give a plan, can be high-level to start, but what would you do?
>
> Come up with new strategies? Look for hidden insights like picks with
> low score but high PnL, or picks with high-score and low PnL, or top
> strategies that haven't had picks in a while, DNA mutation of
> strategies, machine learning?
>
> What exactly would you do to basically guarantee success — you know,
> like how REAL successful companies do it?

**Swarm plan (compressed from 10 → 3 rounds for feasibility):**

- **Round 1 (parallel, ~6 personas):** each writes a focused 400-600-word
  doc to `reports/quant_swarm_round1_<persona>_2026-05-12.md`:
  - Renaissance (stat-arb + mean-reversion)
  - Two Sigma (ML-heavy)
  - DE Shaw (event-driven + alt data)
  - Citadel (multi-asset systematic)
  - AQR (factor investing — Carry/Momentum/Value/Defensive)
  - Bridgewater (All Weather macro)
- **Round 2 (synthesis):** I merge into
  `reports/quant_swarm_merged_round2_2026-05-12.md`
- **Round 3 (cross-review):** each persona reviews the merged doc; flags
  drift/disagreement; saves to
  `reports/quant_swarm_round3_<persona>_review_2026-05-12.md`
- **Final merge:** I incorporate review notes into a final
  `reports/quant_rescue_master_plan_2026-05-12.md`

Hidden-insight queries explicitly mentioned by user:
1. Picks with **low score but high PnL** → score is missing some signal
2. Picks with **high score but low PnL** → score over-fits noise
3. **Top strategies dormant** (no picks in a while) → emission decay flag
4. **DNA mutation of strategies** — three-axis mutation protocol per
   `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
5. **ML reality check** — per `reports/ml_staleness_audit_2026-05-12.md`

---

## 2026-05-12 — User brief (queued post-Round-9 deep-dive sequence)

User directive at end of Round 9 ROR-MC build:

**1. Updates entry**
> Once all todos complete, add entry under `findtorontoevents.ca/updates/index.html` indicating changes completed, **expected impact per asset class**, and overall impact on `findtorontoevents.ca/audit`.

**2. Deep-dive worst asset classes**
> Deep-dive into the database and/or strategies by asset class. Identify worst asset classes; how to get them to at least decent performance. Possibly pull in more data. Look at GitHubs with predictive models for those asset classes; evaluate.

Concrete worst classes today (post-resolver-v2 snapshot per `dashboard_data.json::performance.asset_class_health`):
- **FOREX** PF 0.27 / WR 46.4% / n=1169 — class-blocked (hedge_fund_sprint)
- **FUTURES** 5.9% WR — silent-dead, no production scanner
- **BOND** PF 1.72 / WR 55.6% / n=18 — meets PF+WR but n sub-floor (charter 100). BOND scanner registry wired this session (commit 5c7a8c43a27), should ramp.

External-model candidates worth evaluating:
- **FOREX**: stefan-jansen/machine-learning-for-trading (Ch. 12-18, deep RL on FX), polyrabbit/forex-quantitative-trading
- **FUTURES**: backtrader/backtrader-contrib (rolling-cot futures strategies), AI4Finance-Foundation/FinRL (deep RL on commodity + futures rollovers)
- **BOND**: pyportfolioopt (Black-Litterman over treasury duration), QuantConnect/Lean (treasury yield-curve strategies)
- **ETF**: tradytics, polyrabbit/etf-rotation-strategies

**3. Machine-learning audit**
> Are our ML models actually learning? Actually predicting effectively? Getting us better picks per asset class? Any stale ML?

Current ML inventory (from memory + repo grep):
- `ml_gatekeeper/` — gatekeeper model, joblib + json artifacts (committed hourly per audit-dashboard.yml)
- `ml_consensus/` — consensus learner
- `enhanced_models/` — boosted variants
- `ml_crypto_v3` (memory `ml_crypto_v3.md`)
- `ml_enhanced_*` family (4 with DSR>=0.9995 per anti_overfit; 3 flagged "placeholder-stat suspect" by Agent E per `money_ready_filter.js`)
- `kimi_signal_tracking` (blacklisted per supreme-edge P0 #2, commit 4a2d337a5dc)
- `claude_gainer_st` (blacklisted, ML calibration inversion per Kimi audit)
- `enhanced_ml_*`, `ml_crypto_predictor` (SHORT-blocked per BLOCKED_DIRECTION_TRIPLES)

Audit questions to answer:
1. Per-model: when last retrained? Compare model artifact mtime vs cron expected cadence.
2. Per-model: live forward WR vs backtest WR — divergence > 15pp = decay (already in `fwd_vs_bt_divergence` payload).
3. Per-model: confidence-vs-realized-WR correlation. Memory `project_performance_reality` notes confidence INVERTS on ETF/CRYPTO. If still true, ML is anti-edge on those classes.
4. Stale detector: any model with no commit in 7d while its cron is active = silent-dead.
5. Feature drift: `hf_stats.concept_drift.KS_D` was uncomputed last we checked (Master Plan §6). Recompute.

### Execution sequence

1. Ship Round 9 (Step 7 ROR MC + cron).
2. Ship Round 10: updates/index.html entry with per-class expected impact.
3. Deep-dive worst classes: write `reports/asset_class_deep_dive_<class>_2026-05-12.md` per FOREX/FUTURES/BOND. Use cavecrew-investigator agents in parallel.
4. ML staleness audit: write `reports/ml_staleness_audit_2026-05-12.md` with model-by-model retraining age + decay flags + confidence-inversion check.
5. External-model evaluation: cite the GitHubs, identify candidates worth replicating into baby_strategies/ via the harness (commit 9747f9594ec scope).

NFA — all of this is research surface; no real-money sizing without the 10-step Lopez de Prado readiness gate clear.

---

## 2026-05-11 — Top prompts worth revisiting / deep-dive (session synthesis)

Drawn from the May-10/11 session that shipped the research orchestrator + edge stability suite. Each entry = a prompt or sub-thread that produced strong outcomes but still has slack to mine.

### A. v3b — LLM-driven spec-faithful signal translator (HIGHEST LEVERAGE)

**Prompt:** "Replace SMA(50)/SMA(200) proxy with engine-emitted structured `signal_spec` JSON per candidate. Dispatch to handler registry."

**Why revisit:** every NO_EDGE verdict across 7 asset classes is **caused** by the SMA proxy not parsing natural-language `spec.entry`. Keyword router (v3a, commit `a060a87b3c8`) routes only 2/14 BOND specs off the SMA default. Real edge likely hidden behind faithful translation. Output JSON: `{signal_type, params, primary_ticker, secondary_ticker, regime_gate}`. Cost ~$1/run across all classes.

**Deep-dive:** pair-strategy support (TIP/IEF long-short, LQD/HYG ratio), regime-gated entries (VIX > N skip), multi-leg sizing. Likely unblocks MIXED → GO transitions on COMMODITY + EQUITY (already pass T2 floors per edge_stability).

### B. Per-asset-class deep-dive question batches (feed into orchestrator P1)

**Prompt:** "For each class — 5-7 specific questions a quant fund would research next."

**Why revisit:** session's edge-stability design agent produced concrete, asset-class-anchored questions worth firing as their own P1 swarms:
- **CRYPTO** — Hyperliquid HLP carry replication; cross-exchange basis arb post-BinanceUS; on-chain perp signals (funding skew, taker imbalance, OI delta) post-2024 Sharpe>1.5; BTC seasonal-by-UTC-hour; MATICUSDT 2.5%-TP post-merge check.
- **FOREX** — FX carry surviving 2015-2020 CHF/EUR collapse; MyFXBook top-100 AUD/JPY 2024-2026 canonical structure; 13-21 UTC session gate academic basis vs overfit; EUR/USD post-COVID regime-switching with PF>1.5 OOS; trend-following FX majors retail bps budget.
- **BOND** — IG-credit carry post-QE duration window; TLT/IEF momentum 3yr live tracks; PIMCO BOND-fund ETF basket replication minimum n; treasury curve steepener MR 2024-2025; HYG/LQD ratio MR.
- **COMMODITY** — why WR<50 with PF>1.5 (TP/SL ratio); DBMF/KMLM commodity-momentum replication; gold/silver ratio MR 2024-2026; crude contango/backwardation roll-yield current regime; natgas seasonal surviving LNG-export shift.
- **EQUITY** — QMOM/IMOM post-2024 momentum-crash survival; Russell-2000 cross-sectional momentum 20bp slippage; earnings drift PEAD vs HFT crowding 2026; sector-rotation XLF/XLE/XLK Sharpe; short-interest squeeze-fade meme-era vs persistent.
- **ETF** — risk-parity rotation post-2022 reset; NAV vs market price arb retail; sector-momentum monthly rebalance Sharpe post-fee; EFA/VEA vs VTI relative-strength; SVXY/UVXY rebalance edge.
- **INDEX** — SPX/NDX overnight gap post-0DTE flood; VIX term-structure roll post-2024; index seasonality 2020-2026 OOS; pre-FOMC drift bps + decay; SPX/RUT spread MR.

**Deep-dive:** drop into `tools/research/fire_class_p1.py` as a `--question-set <name>` flag so future runs target specific edge hypotheses instead of generic literature surveys.

### C. Edge-stability + research orchestrator pipeline integration

**Prompt:** "Distinguish forward-looking (research) from backward-looking (edge stability) — different surfaces, different cadences."

**Why revisit:** today (commits `bf9f65ed699` + `762b935c0fa`) the two surfaces live on different /audit pages and share only nav style. Cross-link inside `research_index.html` → "see edge stability of currently-shipped strategies" + reverse-link in `edge_stability.html` → "research candidate replacements" would close the loop.

**Deep-dive:** automate. When `edge_stability_<CLASS>.json::consistency_verdict == DECAYING_EDGE`, trigger a P1 swarm for that class focused on "what replaces strategy X?" via a new `tools/research/decay_replacement_pipeline.py`. Wire into `.github/workflows/research-orchestrator.yml`.

### D. Hallucination-guard methodology (export to other agent workflows)

**Prompt:** "verify_citations.py HEAD-checks every URL; engines >25% hallucination → 0.5x weight, >50% excluded."

**Why revisit:** session data showed engine traits are stable — `cerebras` rarely hallucinates URLs, `deepseek` mid (~25-50%), `inception` heavily (>50% on BOND/EQUITY/COMMODITY). Hallucination rate is per-engine, not per-run. Worth surfacing as a score in `tools/swarm/swarm_stats.py` so future agents auto-pick engines.

**Deep-dive:** broaden beyond URL-checking. Check fact-claims: cited PF/WR vs paper's actual Sharpe; claimed instrument vs paper's; claimed window vs paper's. Adds ground-truth scoring beyond URL liveness.

### E. NO_EDGE protocol as first-class deliverable

**Prompt:** "If 5 passes yield no edge, ship a 'no edge found' page that's just as valuable as the positive case."

**Why revisit:** 6 of 7 P5 verdicts came back NO_EDGE today — pages render with citations + rejected candidates + retry conditions, but readers don't know to look there. Index page should sort NO_EDGE prominently with "retry conditions" + "what we tried" exposed so future agents inherit the lit review.

**Deep-dive:** ship `tools/research/no_edge_kb.py` that aggregates every NO_EDGE run into a queryable knowledge base ("has anyone tried X on Y class? what was found?"). Saves swarm $$ on duplicate research.

### F. Generator dry_run gap (E-D3 prereq)

**Prompt:** "3 pick generators (smart_picks_engine, production_scanner, dashboard_generator) don't have `dry_run` kwargs. Blocks Layer 2 generation verification."

**Why revisit:** gate for the post-quarantine verification suite Agent E designed. Until dry_run lands, `tools/verify_quarantine.py` can't prove a quarantined strategy didn't sneak into pick generation. Documented at `audit_trail/GENERATOR_DRY_RUN_GAP.md`, not implemented.

**Deep-dive:** 3 small PRs (one per generator). Each ships a test asserting `dry_run=True` mtime-of-side-effect-file unchanged. Pairs with `feedback_gate_at_execution_not_generation.md`.

### G. Drift-pause activation (Agent D Approach C hybrid)

**Prompt:** "Auto-quarantine strategies when drift exceeds threshold. JSON probation tier auto-managed; permanent BAN human-only PR."

**Why revisit:** ~26h dev work, full design at `tasks/a53c89219838c17e1.output`. Approach C wins (probation JSON read by `quality_gates._load_probation`, hot-reload by next picks generation, mutate-before-kill gate fires investigation doc generation + `mutation_analysis.py` automatically). 25% blast-circuit-breaker. CLAUDE4's 14 manual quarantines (kimi_signal_tracking, baby_strats crypto_soc_*, ml_crypto_pred_v12) become ground-truth fixtures.

**Deep-dive:** D-Phase-1 first (JSON-backed probation tier + `is_on_probation()` + sizer multiplier wire-in to `is_blocked_pick`). Then mutate-before-kill enforcement.

### H. Cross-engine consensus on methodology questions

**Prompt:** "Has anyone found persistent edge in X published 2022-2026? Cite or say no."

**Why revisit:** session showed `cerebras + deepseek + xai` consensus on P5 verdicts is high-signal because P3 numbers are deterministic — disagreement isolates spec interpretation. Use same pattern for **methodology questions** (e.g., "is walk-forward valid for daily-bar bond strategies?", "what PF floor at our cost model?").

**Deep-dive:** new `tools/swarm/examples/methodology_consensus.yaml` that fans methodology Qs to engine pool. Surfaces decisions ("drop monthly rebalance for weekly?") with consensus + dissent.

### I. graphify-intel skill — wire deeper

**Prompt:** "`/graphify-intel` slash skill wraps graph queries. Replaces 3+ Grep/Read roundtrips per cross-file investigation."

**Why revisit:** skill shipped (commit `a28904ebec0`) but graph still AST-only (no semantic LLM phase — `pip install openai` missing). Semantic phase adds clusters + surprising-connection report.

**Deep-dive:** auto-extract on git push via post-commit hook. Use graph to auto-flag PRs touching nodes downstream of `BLOCKED_SOURCE_SYSTEMS` or `passes_active_gate` — high-blast-radius edits get human review.

### J. CPCV upgrade for p3_backtest_runner

**Prompt:** "Close `project_cpcv_gap_2026_04_28.md`. Walk-forward → CPCV (Combinatorially Purged Cross-Validation)."

**Why revisit:** López de Prado's CPCV gives better overfitting detection than k-fold walk-forward for small-n cohorts (exactly our state — all 14 BOND candidates have n<30 today). Switching unblocks honest verdicts at small-n.

**Deep-dive:** mlfinlab CPCV vendored via `experiments/hedgelib_2026_05_10/`. Already audited as DOA on Py 3.14 install — use standalone purged-CV from `alpha_engine/integrations/` instead (per `project_next_phase_integrations_2026_04_22.md` — already wired but orphan).

---

**Session cost summary (2026-05-10/11):** ~$2.10 across 28 swarm passes (7×P1 + 7×P2 + 7×P5 + 7 P1 follow-ons). Hallucination guard fired per class; verified-citation subset only fed P2; engine vote weights propagated to P5.

**Commits anchoring above prompts:** `8d1b3344e12 → 762b935c0fa` on `feat/audit-dashboard-enhancements-hermes-2026-05-09` (research orchestrator + edge stability + 9 PRs). See `CLAUDE1.MD` for full breakdown.

---

## 2026-05-09 — Production-Readiness Subset Hunt: Find Consistent Winners

**Source prompt (verbatim for re-processing):**

> we need to get our project findtorontoevents.ca/audit ready for PRODUCTION REAL WORLD USE.. like we are talking we make hedge-fund level picks per asset class, and people spend their REAL money on our picks.. so we cant mess around anymore. Which asset class could we trust for that.. and if none.. then i need you to take baseline of our current state.. in terms of what the baseline contains, check our project strategies. and build and determine the best possible prompt and then give it to our code swarm and ask for optimizations .. similarly, ask for the best queries, after feeding in a document detailing our database schema and backtesting protocol etc.. You need to check the performance PER ASSET CLASS. not system wide.. and maybe check the performance based on NOT forward looking "edge" filters. is there any subset of our data that if we filtered it by we have winners consistently .. WR or profit factor

**All performance claims labeled with: asset_class | n | timeframe.**

### KEY FINDING — yes, consistent-winner subsets exist (verified)

Source: `audit_dashboard/data/dashboard_data.json::systems` (post-resolver-v2, generated 2026-05-10T00:06:06Z, cumulative-since-system-inception, last_signal_at per row).

**6 systems verified Tier-2 by full charter (`docs/PERFORMANCE_CHARTER.md` v1.0): PF≥1.5, WR≥50%, MDD≤20%, n≥100.**

| system | asset_class | n closed | WR % | PF | MDD % | last_signal | tier |
|---|---|---|---|---|---|---|---|
| `aggregated_picks` | CRYPTO | 440 | 77.8 | **6.84** | 14.43 | 2026-05-09T23:00Z | T2 (T1 except MDD>10) |
| `claude_gainer_st` | CRYPTO | 3,447 | **80.1** | **6.80** | 11.31 | 2026-05-09T12:50Z | T2 (T1 except MDD>10) |
| `copy_trader_intel` | COMMODITY+CRYPTO | 739 | 50.0 | 1.84 | **2.23** ← T1 by MDD! | 2026-05-09T22:47Z | T2 |
| `ml_crypto_pred_v12` | CRYPTO | 123 | 55.6 | 2.53 | 11.0 | **2026-02-22T13:38Z** ← stale 2.5 months! | T2 but inactive |
| `multi_asset_cot` | COMMODITY | 130 | **86.9** | **19.19** | 17.83 | 2026-05-08T23:27Z | T2 |
| `signal_validation` | CRYPTO+FOREX | 501 | 55.7 | 2.31 | 13.14 | 2026-05-09T18:44Z | T2 |

**Standout per asset class:**
- **CRYPTO:** `aggregated_picks` (n=440) + `claude_gainer_st` (n=3,447) — both ~80% WR, PF ~6.8, MDD ~12-14%. Cumulative since system inception.
- **COMMODITY:** `multi_asset_cot` (n=130) — 86.9% WR / PF 19.19 / MDD 17.83% — extreme PF but small n; needs walk-forward verification before Tier 1 promotion.
- **CRYPTO+COMMODITY:** `copy_trader_intel` (n=739) — only 50% WR but **MDD 2.23%** which is well inside Tier 1's 10% cap. PF 1.84 borderline.
- **CRYPTO+FOREX:** `signal_validation` (n=501) — 55.7% WR / PF 2.31 / MDD 13.14%.

### CONTRAST — system-wide aggregate is misleading

Same data source, system-wide:
- Total closed picks: 30,286 (8,774 valid post-noise-filter); compounded PnL **-78.25%**
- 131 systems, only 39 active picks
- Sharpe 0.13, MDD 681% (`hf_stats`, but stale 2026-04-22)

The **system-wide aggregate is destroyed by `kimi_signal_tracking` (CRYPTO, n=657, PF 0.26, -955 PnL%)** and `alpha_engine_fast` (PF 0.62, -128 PnL%). Strip those + the other dragger systems and the picture is much better than the aggregate suggests.

### IMPLICATIONS

The user's question — "is there any subset that consistently wins" — answers **YES**:
1. The 6 Tier-2 systems above already meet hedge-fund-grade thresholds on PF/WR/MDD/n (per charter v1.0).
2. They are ASSET-CLASS-SPECIFIC: CRYPTO is the dominant winner (4/6 systems), COMMODITY is the pure-edge winner (`multi_asset_cot` PF 19.19).
3. NONE meet full Tier 1 (PF≥2 + WR≥55 + MDD≤10 + n≥200) — closest is `copy_trader_intel` (MDD ✓, n ✓, but PF 1.84 < 2 + WR 50 < 55).
4. EQUITY/ETF/BOND/FUTURES asset classes have no Tier-2 winners despite EQUITY class-aggregate looking OK (PF 1.58, WR 53.7, n=438) — that's the ONLY-EQUITY class verdict, but no individual system isolates EQUITY edge.
5. FOREX has zero Tier-2 winners and the class-aggregate is PF 0.27 — STAY OUT until rehab.

### NEXT STEPS

1. Spawn 5-engine swarm with this baseline + ask for: per-class real-money verdict, best DB queries to verify, hedge-fund-grade roadmap to Tier 1, drift-handling plan.
2. Walk-forward verification on the 6 Tier-2 systems (current numbers are cumulative; need rolling 30/90d to confirm consistency).
3. Quarantine kimi_signal_tracking + investigate alpha_engine_fast.
4. Investigate `ml_crypto_pred_v12` 2.5-month staleness — system stopped emitting?

---

## 2026-05-08 - Comprehensive Strategy Audit, DB Performance Review & Bug Hunt

**Source Prompt (saved verbatim for swarm/idea re-processing):**

look into our current strategies that feed into our database ejaguiar1_stocks or ejaguiar1_backtests .. and then check our performance by asset class and look for gaps in our backtesting timeframe, methodology, etc, and look to expand our strategy , and fix bugs in our database.. i.e. has a table not been updated in awhile? are we accidently pulling a wrong symbol into incorrect asset class. etc.. save your results into docs/ALLSTRATEGIES.MD and review our .MDs of existing strategies listing , we may already have ALL_STRATEGIES.MD or something like taht in fact I see a bunch 
C:\actions-runners\runner-1\_work\findtorontoevents_antigravity.ca\findtorontoevents_antigravity.ca\docs\ALL_STRATEGIES.md
... [full list of 70+ duplicate paths omitted for brevity - see original message]

proceed

**Notes for later review:**
- After completing the above audit tasks, re-read this file.
- Decide: re-process daily ideas via swarm? Expand with new ideas from audit findings? Run existing ideas through multi-agent review?
- Cross-reference with CHATWITHCLAUDE.MD and updates/ for continuity.
## 2026-05-08 - 48h Audit Picks Investigation + Swarm Consensus + Cron/AI-Picks Check

**Prompt saved for processing:**
investigate all our findtorontoevents.ca/audit picks by asset class over the past 48 hours and (both opened and closed) and feed each pick into an agent swarm, or leverage AI keys to ask AIs for their opinion and  look for consensus amongst AIs ..  also check if our cronjob is setup to constantly monitor strategies, or if there is an "AI based picks" something like that feeding into findtorontoevents.ca/audit some picks (maybe from our other hermes instance on my laptop) , also save that to DAILY_IDEAS.MD

**Action items added:**
- Query universal_resolved_picks.json + MySQL for last 48h (opened/closed)
- Group by asset class (CRYPTO/FOREX/EQUITY)
- Spawn swarm or multi-AI consensus on each pick
- Verify cron for strategy monitoring
- Detect "AI based picks" sources (chatgpt_combined, hermes-laptop, etc.)
- Append findings here + main ALL_STRATEGIES.md update

## 2026-05-09 - Mega Spec Swarm + Full Implementation + Unit Tests for /audit + /audit/hyrotrader

**Source prompt (saved verbatim, queued for self-verify in T+2h):**

```
/goal per our earlier requirement, generate a bunch of spec swarms. and get them all completed.
[Pasted text #2: 37 lines → /root/.hermes/pastes/paste_2_130449.txt]
get them all completed in specs but not only that fully implemented.
backtested and verified, unit tested
if done create a unit testing for all componenent of findtorontoevents.ca/audit and findtorontoevents.ca/audit/hyrotrader
including all systems / strategies etc
please proceed autonomously without asking questions, if unclear deploy a code swarm to get some ideas of the best path forward.
```

**Verification task (T+2h, ~14:00 UTC 2026-05-09):**
1. Re-read this entry.
2. Check status of:
   - Spec-swarm output dirs (look in `swarm_runs/` for new runs since 2026-05-09T12:00Z)
   - Implementation: are referenced strategies/components shipped to `alpha_engine/` / `audit_trail/` / `audit_dashboard/`?
   - Backtests: are there `__main__` blocks producing real numbers OR `tests/test_*` or `incubator/backtest_results/` entries?
   - Unit tests: do `tests/test_audit_*` and `tests/test_hyrotrader_*` exist? `pytest -k audit -k hyrotrader -q` count.
   - Verification: is there a verification report (`reports/verify_*_2026-05-09.md`)?
3. If gaps → deploy parallel subagents to close them.
4. If hermes paste #2 contents reachable at `/root/.hermes/pastes/paste_2_130449.txt` (WSL host), pull via `wsl cat ...` and add to this entry.

**Pre-existing context (already shipped this loop):**
- 3 new strategies: sentiment_macro_contrarian, crypto_pairs_arb, regime_filtered_momentum (commit 273908c1c19)
- Top-7 swarm queue items #1-#7 shipped
- Loop2 16-queue items #3, #7, #11, #12 shipped
- EW compound cap hardened 10→2 + ceiling 9999%
- Coverage validation: 5000 audit-rounds = 24 distinct names = 2.4% of 1008 production strategies (`docs/strategy-audit-rounds/COVERAGE_VALIDATION_2026-05-09.md`)
- Pending: FRED_API_KEY secret; Sharpe annualization redesign; rolling-window EW compound replacement

---

## 2026-05-11 22:55 EST — Multi-model trial-and-error: prove best model per asset class

**Source:** task carried over from another agent's session troubleshooting the Ollama ernie:latest setup. Bartowski's template for `hf.co/bartowski/baidu_ERNIE-4.5-21B-A3B-Thinking-GGUF:Q4_K_M` is buggy (missing user block + truncated `tart|>assistant` literal) so `ernie:latest` returns off-topic creative writing. Custom `ernie-coder.Modelfile` built (temp 0.2 / num_ctx 32k / proper chat template) but model still crashes with CUDA OOM unless `num_gpu=0` (CPU only). Forking it forward as an experiment idea, not a bug-fix.

### Core idea

Move from *theoretical* "which model is best at trading picks?" to **trial-and-error** with a measurable scoreboard. We already have:
- 40+ Ollama models installed locally: ERNIE 4.5 variants, Qwen3-coder 480B cloud, Qwen2.5-coder family, Kimi K2 / K2.5 / K2-thinking cloud, GLM 4.6 / 4.7 / 5 cloud, MiniMax M2 / M2.5 cloud, DeepSeek V3.1 / V3.2 / R1, GPT-OSS 20B / 120B cloud, Cogito 2.1 671B cloud, Llama 4 Scout, Mixtral 8x7B, Mistral / Mistral-Nemo, Phi-3.5, Gemma 3 / 4 cloud, Llama 3 / 3.1, plus existing `gpu-forced-qwen`, `claude-100-gpu`, `qwen3-vl 235B cloud`, etc.
- A persona-divergent fanout pattern (just used 10 different lenses → consensus aggregation for theswarm paper picks — see `TV_PICKS_WHY_2026-05-11_2229EST.MD` once committed).

### Experiment proposal

1. **Per-asset-class model bake-off:**
   - For each class (CRYPTO, EQUITY, FOREX, COMMODITY, ETF, FUTURES, BOND), ask every available model the SAME prompt: "Pick LONG/SHORT/SKIP for these 10 symbols + reasoning + timeframe + data sources you used."
   - Score over time: every pick gets a forward-validation outcome (WR + PF + R-multiple).
   - Build a leaderboard: `model × asset_class → live WR / PF`. Refresh weekly.

2. **"What's in the brain?" probe round:**
   - Ask each model to **list the data points it weighted** when making each pick. Capture as JSON: `{model, symbol, pick, data_points_cited: [..], confidence}`.
   - Compare cited data points across models — does ERNIE actually lean on COT positioning while DeepSeek leans on price-action? Or does every model just hallucinate the same Wikipedia-y rationales?
   - This is the diagnostic that separates "smart model" from "well-trained-to-sound-smart model."

3. **Debate round (10-20 turns):**
   - Pair up models cross-family (e.g., Qwen3-coder 480B vs Kimi K2.5 vs GLM 4.6 vs Llama4 Scout).
   - Topic: "What are the BEST criteria + FREE data sources for picking edge in CRYPTO?" (then same for each class)
   - Let them debate 10-20 turns with a moderator agent forcing concrete proposals (no hand-waving).
   - At the end, the moderator emits a `criteria_v1.md` per asset class (what to look at, where to scrape it from — Scrapling-compatible sources preferred so we can automate ingest).

4. **Backtest the criteria:**
   - Translate `criteria_v1.md` into a signal generator (this is where the v3b LLM signal-spec translator from idea A above starts paying compounding returns).
   - Backtest against the same 7,000-trade ledger we already have (`audit_dashboard/data/dashboard_data.json::performance`).
   - Promote criteria that beat T2 floors (PF>1.5 / WR>50). Reject the rest.

5. **Cycle:** if no criterion clears T2 in a class, swap in a fresh roster of models the next cycle. Specifically rotate the families: large MoE (Kimi K2 / Qwen 480B) ↔ dense (Llama 4 Scout / Llama 3.1) ↔ thinking-token (DeepSeek R1 32B / ERNIE Thinking / Kimi K2-thinking) ↔ small fast (Phi 3.5 / Qwen 3 4B). Cross-family disagreement = the signal worth chasing.

### Infra to build (not now, but on the runway)

- `tools/swarm/model_bakeoff.py` — single command: `python model_bakeoff.py --class CRYPTO --models all-local,all-cloud --symbols 10 --round-id 2026_05_11`. Writes `tools/swarm/bakeoff_runs/<round_id>/<model>/<class>.json` with picks + cited data points.
- `tools/swarm/data_point_diff.py` — compares which data points each model claims to use; flags hallucinated sources (e.g., a model citing a Bloomberg terminal it can't access).
- `tools/swarm/debate_orchestrator.py` — 10-20 round debate runner with a moderator critic that rejects vague hand-waving and forces concrete `data_source: <url>` + `signal: <formula>` proposals.
- `tools/swarm/criteria_backtester.py` — wire `criteria_v1.md` → signal generator → backtest harness → leaderboard update.

### Local-vs-cloud blend (cost vs latency tradeoff)

- **Local large (Llama4 Scout 67GB, Mixtral 26GB, ERNIE 13GB, Qwen2.5-coder 32B):** good for the high-volume bakeoff loop — free per query but slow.
- **Cloud large (Kimi K2 1T, Qwen3-coder 480B, Cogito 2.1 671B, GLM 4.6, DeepSeek V3.2):** good for the debate round where reasoning quality matters more than QPS.
- **Local small (Phi 3.5, Qwen 3 4B, Gemma 3 4B):** good for the "data-point extraction" probe — cheap, fast, and we don't need 200B params to ask "what did you weight?"
- **Thinking-token models specifically (DeepSeek R1, ERNIE Thinking, Kimi K2-thinking):** these are the ones we want for the debate round — visible reasoning chains are easier to fact-check.

### Suspicious tells to watch for (overfitting diagnostics)

- Every model converging on the same pick → could be real consensus OR shared training-data anchor. Cross-check the cited data points (are they all citing the same 2023 article?).
- A model with high local WR but low debate-round contribution = sample-mining without underlying methodology. Demote.
- Models that refuse to specify timeframe → vague signal, demote.
- Models that cite paid/inaccessible sources (Bloomberg, Refinitiv) → likely hallucinating, demote.

### Pre-existing ernie:latest crash fix (separate ticket)

To make ERNIE-thinking actually usable in this pipeline:
- The bartowski template is unfixable as-is. Use `ollama show <model> --modelfile` then rewrite TEMPLATE block.
- VRAM OOM on 13GB ERNIE: requires `keep_alive=0` on whatever model is currently loaded before requesting ERNIE, OR `num_gpu=0` (CPU offload, slow but works).
- Custom `ernie-coder.Modelfile` already at `tools/ernie-coder.Modelfile` — keep it; just don't reuse the broken bartowski TEMPLATE.

### Pending followups carried in from prior session

- The asset-class-health snapshot the other agent fed ERNIE shows: COMMODITY PF 3.77 + EQUITY PF 1.59 + CRYPTO PF 1.39 ALL pass T2 PF floor, but **EQUITY** and **CRYPTO** both meet WR>50 + PF>1.5 (cleanest T2 candidates). FOREX PF 0.28 with -1032% cumulative PnL → already sizing-off (correct per `[Mutate Before Kill]`). BOND n=11 too thin to score. Asset-class allocation in `theswarm` paper should weight COMMODITY/EQUITY first.

---

## 2026-05-12 17:25 EST — Swarm-pick tracking infra shipped (Q3 = YES decision)

Implements `docs/SWARM_PICK_TRACKING_DESIGN.md` design tasks 1-6 in two commits (`7ee3b5ca8f3` schema/backfill/resolver-skeleton + `4d688ed0cd9` resolver-wired/weekly-review/pattern-miner).

**Q3 decision (locked):** `models_consulted[].underlying_model` is REQUIRED on every vote — without it, the multi-model bake-off can't distinguish "MOMENTUM_TECH persona is good" from "Opus-4.7 backing that persona is good." 1 extra string field per vote.

**Files shipped:**
- `tools/swarm/swarm_pick_schema.py` — validator + tier-derivation. Enforces side-sanity on write (LONG: tp>entry>sl, SHORT: sl>entry>tp). Atomic write via tmp-then-rename.
- `tools/swarm/backfill_sessions.py` — hand-mapped 38-pick backfill from the two committed session .MD files. Refuses overwrite.
- `audit_dashboard/data/swarm_picks.json` — 38 records (22 round-1 + 16 round-2). 5 already resolved by first resolver run.
- `tools/swarm/outcome_resolver_swarm.py` — yfinance-backed `fetch_high_low()` with SYMBOL_MAP for crypto/forex/futures + exchange-prefix strip for stocks. APT-USD + POL-USD delisted on yfinance — return None (pick stays open). TODO: TV MCP `data_get_ohlcv` fallback for delisted crypto.
- `tools/swarm/weekly_review.py` — per-tier + per-class + per-persona + per-underlying-model WR/PF report + `swarm_leaderboard.json` (consumable by future fanouts to weight votes by historical accuracy).
- `tools/swarm/pattern_miner.py` — winning vs losing `(tier × class × regime)` cells. Lowered n threshold to 5 (from design's 10) since store is still seeded — bump back when resolved-pick count crosses 100.

**Live numbers as of 2026-05-12 17:22 EST:**
- 38 picks tracked, 5 resolved, 33 open.
- Overall WR 40%, PF 0.8 (n=5 — not statistically significant yet; need 100+ resolved for any conclusion).
- Per-class so far: ETF 100% WR (n=1 — GLD), FUTURES 100% WR (n=1 — MCL), CRYPTO 0% WR (n=2 — ADA shorts didn't hit TP in 1d window), FOREX 0% (n=1 — USDJPY stopped out).
- Per-persona top so far: NEWS_FLOW agreed on 7 picks 1 resolved 100% WR (single sample). All others n=0 resolved.

**Remaining design tasks (not yet shipped):**
- Task 4-extension: TV MCP `data_get_ohlcv` fallback for delisted yfinance tickers (APT/POL today)
- Task 7-10: dashboard panel on `/audit` (subagent dispatched 2026-05-12 17:25, awaiting result)
- Cron-style schedule: wire `outcome_resolver_swarm.py` + `weekly_review.py` + `pattern_miner.py` as a Sunday-23:00-EST routine via `/schedule` skill so the pipeline auto-refreshes.
- Backfill round-3+ as new sessions land — extend `backfill_sessions.py` with one function per session or write a generic `.MD` parser.

**Bake-off precondition met:** with `underlying_model` field stamped on every vote, the data pipeline can now answer "is Opus-4.7 better than Qwen3-coder-480B at FOREX picks?" once enough resolved picks accumulate across both models. The DAILY_IDEAS.MD 2026-05-11 22:55 EST proposal can now plug into `swarm_picks.json` as its persistence layer.

---

## 2026-05-12 — Statistical Edge Per Asset Class: Data-Driven Analysis

**Source:** `audit_dashboard/data/dashboard_data.json` (generated 2026-05-12T20:14Z), 134 systems, 32 with n>=20.

### Class-Level Edge Ranking (sorted by PF × WR composite)

| Rank | Class | PF | WR | Verdict |
|------|-------|----|----|---------|
| 1 | **COMMODITY** | **3.94** | **67.8%** | **STRONG EDGE** — class-level meets T2 on both axes |
| 2 | EQUITY | 1.55 | 53.2% | DEFENSIVE — meets T2 PF, borderline WR |
| 3 | ETF | 1.34 | 56.1% | BORDERLINE — WR passes T2, PF slightly below |
| 4 | CRYPTO | 1.36 | 46.5% | **MASKED** — top systems are great but class dragged by high-volume losers |
| 5 | UNKNOWN | 2.40 | 50.0% | SUSPECT — misclassified picks, audit needed |
| 6 | BOND | 0.66 | 54.5% | INSUFFICIENT n, degraded from May 10 |
| 7 | FOREX | 0.29 | 46.2% | **TOXIC** — pure FOREX is uninvestable |
| 8 | FUTURES | 0.00 | 0.0% | **DEAD** — no signals |
| 9 | SPORTS | 0.00 | 0.0% | **ELIMINATE** — confirmed dead weight |

### Hidden Insight #1: Two Distinct Edge Regimes

**Regime A — Trend-Following (low WR, high PF, fat-tailed):**
- `multi_asset_copytrader` — PF 4.09, WR 36.1%, n=812, MDD 16.7%, avg win 1.83/avg loss 0.49
- Wins 1-in-3 but pays 3.7x on winners vs losers.
- Most robust risk-adjusted returns in the entire dataset.

**Regime B — Pattern Recognition (high WR, medium PF, thin-tailed):**
- `multi_asset_cot` — PF 21.33, WR 88.2%, n=144, MDD 17.8%
- `aggregated_picks` — PF 5.47, WR 73.3%, n=363, MDD 49.2%
- High hit rate but severe drawdowns.

**Implication:** Blend Regime-A (60%, sizing overlay for tails) + Regime-B (40%, tight MDD stop) for lower combined MDD.

### Hidden Insight #2: CRYPTO True Edge Masked by High-Volume Losers

Top CRYPTO systems are elite: `aggregated_picks` (PF 5.47, WR 73.3%, n=363), `mega_mutation` (PF 2.32, WR 56.8%, n=148), `claude_gainer` (PF 2.23, WR 56.2%, n=32). Class-level PF 1.36 is dragged by `luxalgo_filters` (PF 1.08, n=1,329), `baby_strats_forward` (PF 1.40, n=2,042), and `kimi_signal_tracking` (PF 0.28, n=173, MDD 995%). Concentrated top-3 yields blended PF ~3.3.

### Hidden Insight #3: multi_asset_copytrader Is Most Robust System

PF 4.09 across 5 classes (BOND/COMMODITY/EQUITY/FOREX/FUTURES), n=812, MDD 16.67% (inside Tier-1 cap). Best candidate for go-live paper trading NOW. Needs walk-forward verification.

### Hidden Insight #4: FOREX's Only Viable Entry Point

`signal_validation` (CRYPTO+FOREX): PF 4.31, WR 51.0%, n=98, MDD 8.14%. Only system touching FOREX with positive PF. Isolate its FOREX-specific signals.

### Hidden Insight #5: No System Achieves Full Tier 1

Closest: `multi_asset_cot` (MDD 17.83% >10, n=144 <200), `aggregated_picks` (MDD 49.25% >10), `multi_asset_copytrader` (WR 36.1% <55), `signal_validation` (n=98 <200, WR 51% <55). COMMODITY closest to full Tier 1.

### Hidden Insight #6: Emission Decay Is Natural Selection

5 dead systems — ALL poor performers (PF 0.31-0.92). No good system went dark.

### Actionable Next Steps

1. **Papers trade `multi_asset_copytrader`** — best risk-adjusted system, multi-asset, n=812
2. **Isolate `signal_validation` FOREX signals** — only known FOREX entry point
3. **Combine `aggregated_picks` + `mega_mutation` as CRYPTO ensemble** — joint MDD stop at 30%
4. **Remove SPORTS class** — PF None, WR 0%, confirmed dead weight
5. **Walk-forward validate `multi_asset_cot`** — PF 21.33 is suspicious without rolling verification

---

## 2026-05-12 — TV Paper Trace Lessons (5 resolved + 13 open across 4 accts, 21:15 EST snapshot)

Source: TV state captured at 2026-05-12 21:15 EST traced against `audit_dashboard/data/dashboard_data.json::systems` (gen 2026-05-12 23:23Z), `swarm_leaderboard.json::by_tier`, and `performance.asset_class_health`.

### 2026-05-12 — Lesson: Single-persona swarm picks have no production validation

**Pattern observed:** 22 of 38 swarm picks (`swarm_picks.json`) are `consensus_tier=single` (1/1 vote). Only the `single` tier has any resolved outcomes in `swarm_leaderboard.json::by_tier` (n=5, WR 40%, PF 0.80). `unanimous`/`strong`/`moderate` tiers have 0/16 resolved. Winning TV picks RUNE-L (single MOMENTUM_TECH conf 55) and BNB-L (single FUND_VALUE) come from underlying systems (`momentum_tech`, `fund_value`) that are NOT in the `systems` block at all. The closest live tracker `aggregated_picks` reports WR 73.2% / PF 5.42 (n=366) but excludes single-persona swarm output.
**Hypothesis:** Single-persona picks are untracked alpha. We are flying blind on >55% of TV swarm volume. Either suppress them in TV deployment, or wire them through `aggregated_picks` ingestion so they accumulate audited stats.
**Backtest required:** Backfill last 60 days of single-persona swarm picks via `alpha_engine/swarm_picks_resolver.py` (or build it if missing) — resolve TP/SL/timeout against historical OHLCV; compute per-persona WR/PF; compare to multi-persona resolved cohort.
**Acceptance criteria:** Promote `single` tier to TV-eligible only if backfilled n>=100 yields PF >= 1.30 AND WR >= 50%. Otherwise gate behind tier>=`moderate` (2+ votes) at deploy time.
**Effort:** 6h

### 2026-05-12 — Lesson: SHORT-bias on EQUITY/CRYPTO is not yet supported by sample

**Pattern observed:** Among 13 TV picks captured tonight, SHORTs net winning on EQUITY mega-caps (TSLA-S +$110, NVDA-S −$21 but tier-5/6) and on coins where ml_strategy_reviver_inverse fires (ADA-S +$61 zerounderscore, ADA-S +$49 theswarm). But SHORTs also dominate the loser column: DOT-S −$64 CLOSED, DOGE-S −$29 CLOSED, POL-S −$16. Resolved swarm-leaderboard CRYPTO cohort is 0/2 wins so far. `alpha_engine` (n=926, active) has PF 1.61 across mixed sides — no side breakdown is published; we cannot confirm SHORT-edge from production data.
**Hypothesis:** SHORTs in mega-cap EQUITY during the current macro-bear regime (5/6 personas SHORT TSLA / NVDA in the swarm vote) have positive expectancy, but CRYPTO SHORTs lack edge. The pattern is asset-class-conditional, not universal.
**Backtest required:** Run `tools/mutation_analysis.py` (or equivalent side-stratified scanner) on closed picks across last 120 days, grouped by `(asset_class, side)`. Confirm whether EQUITY-SHORT PF beats EQUITY-LONG PF, AND whether CRYPTO-SHORT PF is below 1.0.
**Acceptance criteria:** Add an asset-class-conditional side gate to TV deployment only if EQUITY-SHORT PF>=1.40 with n>=80 AND CRYPTO-SHORT PF<=1.05 (current "no edge" zone). Otherwise treat side-bias as noise.
**Effort:** 4h

### 2026-05-12 — Lesson: Class health predicts winners better than persona-count

**Pattern observed:** TV winners cluster on STABLE asset classes: GLD-L (COMMODITY: WR 70.7% / PF 4.08 / n=280), TSLA-S + LLY-L (EQUITY: WR 52% / PF 1.58 / n=410), ADA shorts (CRYPTO: WR 46.6% / PF 1.37 / n=7758). TV losers cluster on stressed/thin classes: TLT-L (BOND thin n=11 / PF 0.66), BAC-L (despite EQUITY-stable, tier=moderate 2 personas only), POL-S (CRYPTO but POL=MATIC rebrand — `quan_engine` MATIC artifact warning in MEMORY.md). Across resolved swarm cohort, `by_asset_class` shows COMMODITY/FUTURES winning singletons, while CRYPTO 0/2.
**Hypothesis:** Class-health verdict (`asset_class_health[status]`) is a stronger ex-ante filter than swarm tier. A `strong` tier pick on a `stressed` class (TLT, FOREX) should be downgraded; a `single` pick on a `stable` high-PF class (COMMODITY) deserves promotion.
**Backtest required:** Join `swarm_picks.json` with `performance.asset_class_health` at pick time; compute conditional WR/PF for (tier, class_status) cells. Compare to baseline (tier-only and class-only).
**Acceptance criteria:** Class-status-conditioned gating must lift system PF >= +0.15 vs current tier-only gate on a 90-day walk-forward holdout. Reject if lift < +0.10.
**Effort:** 5h

### Notes on what did NOT make the lesson cut

- "6+ persona agreement beats 3-5" — UNTESTABLE: only 5 of 38 picks resolved, all `single` tier. Zero data on `strong`/`unanimous`/`moderate` outcomes. Re-check in 7 days once outcomes accrue.
- "`underlying_model=claude-opus-4-7` outperforms" — UNTESTABLE: `by_underlying_model` has only 1 key (only Opus tracked). Null hypothesis cannot be rejected.

---

## 2026-05-12 — PCG-5: Portfolio Construction Gate Stack v1 (NOVEL methodology)

Source: portfolio-construction methodology agent (2026-05-12 21:50 EST) responding to honest swarm verdict "methodology generates *candidates*, not *portfolios*."

**Verdict on novelty:** the *individual primitives* exist scattered in the repo (CRYPTO_SHORT_REGIME_GATE in `quality_gates.py:729-820`, `asset_class_concentration` WARN/BLOCK in `dashboard_generator.py:13888-13935`, partial-TP helpers in `combined_confidence_strategy.py`, correlation matrix in `correlation_regime.json`) — but **the packaged 5-gate exec-time REJECT stack across all accounts is NOVEL.** Existing gates are mostly *disclosure* (warn the user, write to dashboard), not *enforcement* (reject the pick).

### Methodology — PCG-5

Runs AFTER candidate generation, BEFORE order submission. Reads live state from `audit_dashboard/data/{dashboard_data.json, correlation_regime.json, edge_stability/*}` plus per-account position dumps. Returns: `APPROVE` / `NET` (close offsetting leg first) / `REJECT`.

**Gate 1 — REGIME_DIRECTIONAL_GATE**
- if regime ∈ {BULL,BULLISH} AND pick.asset_class=EQUITY AND pick.direction=SHORT → REJECT unless thesis.catalyst ∈ {earnings_miss, downgrade, fraud, dilution}. Mirror for BEAR + LONG. Extends existing CRYPTO_SHORT_REGIME_GATE to EQUITY/ETF/INDEX_STOCK.

**Gate 2 — CROSS_ACCOUNT_NET_POSITION**
- scan all accounts keyed by canonical_symbol. If opposite-direction position on another account: if size_new > size_existing → NET (close existing first), else REJECT. If same-direction same account → REJECT (duplicate). Correlation expansion: pairs (BTC/ETH ρ>0.85, EUR/GBP, ES/NQ) as same symbol.

**Gate 3 — CONCENTRATION_REJECT**
- if class.top_share_pct >= 50% AND pick.symbol = class.top_symbol → REJECT. Force rotation to class-cousin. WARN 50-70%, hard block ≥ 70%.

**Gate 4 — PROFIT_LOCK_SCAN**
- every cycle: if any open position unrealized_pnl_pct >= +3.0%, require one of {SL_at_breakeven, partial_close_50pct, trailing_stop_armed}. Else block new picks on same account.

**Gate 5 — CROSS_CLASS_CORRELATION_DEMOTE**
- if |corr(class_A, SPY)| >= 0.35 in current 30d window → class_A.sizing_role = `risk_on_beta`. Counts toward EQUITY exposure cap, not own bucket. Reverts when corr < 0.20 for 7 consecutive days.

### Implementation plan

Ship as `audit_trail/portfolio_gates.py` imported by every account's exec wrapper. Shadow-mode 7 days (log to `audit_dashboard/data/pcg5_log.json`), then enforce.

### Tonight's PCG-5-approved picks (placed 2026-05-12 22:00-23:00 EST)

- **zerounderscore:** AUDUSD-L 5000 (TP 0.7309 SL 0.7208) — Gate 5 demoted half-size (AUD risk-on); MCL-L 1ctr @ 101.07 (TP 104.10 SL 99.55) — Gate 3 rotation away from CT=F
- **theswarm:** MHG-L 1ctr @ 6.6495 (TP 6.848 SL 6.5155) — copper, Gate 3 rotation; MGC would have failed Gate 5 (GLD-L already long gold)
- **Leap:** SOL-S 15 @ 95.578 (TP 88.40 SL 100.35) — small per CRYPTO DECAYING_EDGE
- **SL tightens (Gate 4):** TSLA-S→440, ADA-S theswarm→0.2775, LLY→970, BTC-S Leap→81,500

### PCG-5 REJECTED tonight (gates fired)

1. "Add another equity SHORT (SQ/RBLX/COIN-S)" → Gate 1 (BULL + EQUITY + SHORT, no catalyst)
2. "Add more CT=F LONG" → Gate 3 (75% concentrated)
3. "Add GLD-L as hedge" → Gate 5 (GLD↔SPY +0.7674, demoted to risk-on beta)
4. "Open BTC-L on Leap/zerounderscore" → Gate 2 (theswarm has BTC-L, Leap has BTC-S)
5. "Open ADA-L anywhere" → Gate 2 (ADA-S open on theswarm + zerounderscore)
6. "MGC theswarm" → Gate 5 (GLD-L already on theswarm = doubling gold)

### Memory candidate

"**PCG-5 — disclosure ≠ enforcement.**" Repo publishes concentration/correlation/penalties as scoring inputs and dashboard banners, but none reject a pick at exec time. Crypto-short regime gate (2026-04-29) is the only true exec-time gate. Every PCG-5 sibling follows the same pattern: take an existing published metric and promote it from "FYI banner" to "exec-time REJECT."

Suggested filename: `memory/feedback_disclosure_is_not_enforcement.md`. Tie-in: cleaner restatement of existing `feedback_gate_at_execution_not_generation.md` — generalized from "filter-named accounts" to "every published risk metric."

### Effort + acceptance

- Phase 1 (shadow log): 8h. Ship `portfolio_gates.py` + wire into `tv-paper-trade` skill pre-execute path.
- Phase 2 (enforce): 4h after 7d shadow shows >50% picks would have been re-routed.
- Acceptance: realized PF on next 100 PCG-5-approved picks must beat realized PF on prior 100 ungated picks by ≥ 0.15. If not, demote Gates 4+5 first (most aggressive), keep Gates 1-3.

---

## 2026-05-14 — User prompt: "stuck-in-backtest, what protocol moves us to real money?"

**Source prompt (verbatim, captured 2026-05-14T23:12Z, queued for swarm processing):**

> What sort of protocol would you recommend to take a giant repository which tries to predict stocks/crypto/forex/bonds/commodities/futures ... and then find out whether we need to be expanding our strategies, mutating the strategies, improving our safety gates, expanding to other stuff like options.. how we can identify the most effective changes we can perform to improve our win-rate /profits to more of a "spending real money" vs just backtesting.. we have been stuck backtesting for months.. and havent had much success despite extensive use of AI .
>
> our repo is https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
> and website findtorontoevents.ca/audit and findtorontoevents.ca/audit/hyrotrader
> with our updates under findtorontoevents.ca/updates

**Why captured here:** user explicitly framed this as a stuck-in-backtest diagnostic and asked for a *protocol* (repeatable). Goal is move-the-needle from paper to real-money. Process must answer: expand vs mutate vs gate-tighten vs broaden-asset-class. Tie-in to existing money-maker-ready skill output (`reports/money_maker_ready_*.md`), supreme-plan tracker, and `[North Star: HF Edge Per Asset Class]`.

### Sketch — "Stuck-in-Backtest Escape Protocol" (S-BEP)

Self-diagnosis ladder. Each rung must show measurable lift before climbing:

1. **Diagnose stuck-state** — quantify months in backtest vs $0 live. Compute (a) tally of strategies passing internal gates but never deployed, (b) ratio of dead-emitter to live-emitter systems, (c) fwd_vs_bt decay distribution, (d) drift `KS_D` trend.
2. **Honest baseline** — re-run `/money-maker-ready` + cross-verify with DB queries. Tier-classify every system today. Anything claimed Tier-2 that doesn't survive cross-check = drop.
3. **Bottleneck identification** — what is gating live deployment? Pick exactly one of {data-quality, resolver bug, sample size n<floor, MDD too high, drift, no walk-forward, no shadow record, regulatory/operational}. **The protocol fails if you try to fix more than one bottleneck per cycle.**
4. **Smallest experiment that proves edge** — for ONE candidate strategy on ONE asset class:
   a. shadow-paper 30 picks (real-time, not historical replay),
   b. compute realized vs predicted WR/PF gap,
   c. gate: shadow PF ≥ 0.85 × backtest PF AND realized WR within ±5pp of backtest WR.
5. **Real-money pilot at 0.1% sizing** — only after the shadow gate passes. 30 picks live. Stop on hard MDD cap.
6. **Scale gate** — 0.1% → 0.5% only if pilot PF ≥ 1.30 AND MDD ≤ 12%. 0.5% → 1% only after 60 more clean picks.
7. **Expand outward** — only after one class proves Steps 4-6 does the protocol authorize: (a) mutation rounds on adjacent strategies (per `MUTATION_THREE_AXIS_PROTOCOL.md`), (b) new asset-class expansion, (c) options sleeve. Out-of-order expansion = protocol violation.
8. **Continuous drift watchdog** — auto-pause sizing on `KS_D > 0.10` per money-maker-ready P1. Pause is not a kill; it's a re-validate.

### Sub-questions to swarm

- Is "expanding strategies" the right play when 33/42 audited strategies are OVERFIT_LIKELY (per supreme plan)? Or is the bottleneck *strategy quality density* not *count*?
- What gates are missing that would have caught the kimi_signal_tracking PF-flip BEFORE live deployment?
- Options expansion (CBOE put/call, UOA, max-pain) — does it deepen existing crypto/equity edge, or just add a new surface to overfit?
- AI-extensive use w/o success: are we hitting the *Goodhart trap* — optimizing for swarm-consensus metrics instead of realized PnL? If so, what metric do swarms have to predict to count as useful?
- Hyrotrader sub-account specifics — does the `/audit/hyrotrader` surface have its own bottleneck distinct from `/audit`?

### Acceptance — when this protocol has "worked"

- ≥1 asset class reaches real-money pilot stage (Step 5) within 8 weeks of protocol start
- ≥1 pilot strategy clears Step 6 scale gate within 16 weeks
- Drift watchdog auto-pause fires at least once and is acted on (re-validates, not ignored)
- `reports/money_maker_ready_*.md` cadence becomes daily and tracks a tightening verdict over time

### Effort: design 8h, full implementation 4-6 weeks. Tie-in: feed the daily supreme-plan tracker (proposed 2026-05-14) with `(stuck_state_quantified, bottleneck_identified, experiment_status, drift_state)`.

---

## 2026-05-14 — ChatGPT FOOLPROOF restatement (5th protocol, same family)

User pasted ChatGPT-style synthesis of `FOOLPROOF_ACTION_PLAN.md v2.1`. Adds: a Risk-Management Kill-Switch ladder (5% portfolio DD → halve, 10% → full stop, asset PF<0.80 for 5d → halt that class, 3 consecutive >5% losses → reduce to 25%, correlation>0.70 top-3 → flag concentration risk) — slightly different from but compatible with our Kimi Level-3 thresholds. The 12-week milestone table is identical to Foolproof §11. Convergence confirmed: this is the same 8-stage Gate Ladder rendered yet again by a 5th LLM. Action: incorporate the kill-switch ladder's specific numbers (5%/10%/etc.) into `reports/expanded_enhancement_plan_2026-05-14.md` Section 5 Stage D recommendations when implementing PCG-5 Phase 2.

---

## 2026-05-14 — Mercury 6-phase protocol = Inception Labs (verbatim duplicate, confirmed convergence)

User pasted Mercury 6-phase protocol on 2026-05-14T23:30Z; text is **byte-for-byte identical** to the Inception Labs 6-phase protocol captured earlier this date. Confirms this is a shared canonical "Foundations → Validation → Robustness → Paper → Live → Continuous → Options" template across multiple LLMs (likely sourced from a common doc — possibly López de Prado AFML structure or QuantStart-style curricula). No additional content to merge; the Mercury input fully overlaps the Inception merge below and the expanded enhancement plan at `reports/expanded_enhancement_plan_2026-05-14.md` already maps both into the Gate Ladder. Action: cite Mercury alongside Inception in any future protocol references.

---

## 2026-05-14 — Inception Labs 6-phase protocol (captured verbatim)

User-pasted from Inception Labs. Same family as Kimi's Gate System but split across 6 numbered phases. Captured for cross-merge into expanded enhancement plan + future swarm rounds. Verbatim source:

- **Phase 0 — Foundations & Governance:** version control + reproducibility (Git tags v1.0-alpha/beta), CI/CD running unit + data-integrity + quick backtest on every push, audit/compliance read-only trail, risk-policy framework (max daily/weekly drawdown, position-size caps, kill-switch).
- **Phase 1 — Data & Model Validation:** data hygiene (no missing timestamps, corporate actions, time-zones, survivorship-bias + look-ahead checks), feature sanity plots over time for drift, walk-forward (12m train → 3m OOS rolling), Sharpe/Sortino/Calmar/MDD + bootstrap CI + p>0.05 reject, overfit detection (param count vs effective data, AIC/BIC, CV loss).
- **Phase 2 — Robustness & Stress Testing:** parameter sensitivity ±10%, scenario analysis (2008/2020 replay + synthetic), transaction-cost modeling (slippage + commission + latency), OOD detection (autoencoder, reconstruction error > 3σ → safety gate), Monte-Carlo ruin probability.
- **Phase 3 — Paper-Trading & Shadow Mode:** paper-trade with live data zero capital, shadow mode parallel to prod no orders, KPIs (latency, fill-rate, slippage, realized vs predicted), promote-only-if (paper Sharpe > 1.0 AND MDD < 5% equity AND OOD < 1% ticks).
- **Phase 4 — Controlled Live Deployment:** ≤1% capital per new strategy, Kelly-fraction / vol-scaled sizing, dynamic ATR-based limits, real-time monitoring dashboard with alerts, kill-switch on drawdown/OOD/latency, A/B testing disjoint capital slices with statistical tests on live returns.
- **Phase 5 — Continuous Improvement Loop:** nightly data refresh, monthly model retrain on rolling 2y window with hold-out gate, automated hyperparameter mutation (Bayesian / GA) kept only if passes Phase 2, sub-models per new asset class feeding unified risk manager, monthly performance review documented.
- **Phase 6 — Expansion to New Instruments (e.g. Options):** IV-surface + Greeks in feature set, delta-neutral spreads first (calendar/iron condor), Vega/Theta/max-loss tracking, liquidity filter (OI > 10k + tight spread), regulatory/margin compliance.

**Quick-start checklist:** Data pipeline → Backtest framework → Robustness suite → Paper-trading → Safety gates → Live-trading sandbox → Continuous loop.

**Open questions Inception flagged:** (1) which phase to prioritize given current bottlenecks? (2) recommended CI/CD + monitoring tools? (3) how to integrate options/derivatives with risk controls?

**Tie-in:** merges 1:1 with Kimi Gate System (Levels 1-5) above. Kimi Level 1 = Inception Phase 1; Kimi Level 2 = Inception Phase 2; Kimi Level 3 = Inception Phase 0 (governance + circuit breakers) + Phase 4 (live deployment kill-switch); Kimi Level 4 = Inception Phase 3 (paper/shadow) + Phase 4 micro-deployment; Kimi Level 5 (expansion) = Inception Phase 5 + 6.

---

## 2026-05-14 — Grok "Foolproof Live-Trading Protocol v1" (captured verbatim)

User-pasted Grok output. Audit on `findtorontoevents.ca/audit` + `mysql.50webs.com::ejaguiar1_*`. Captured for direct cross-merge.

**Grok's snapshot of our state (55k+ resolved trades):**
- System-wide: −3.56% avg return, 11.13% WR, PF 0.46 (NOTE — disagrees with current `asset_class_health` aggregates; Grok numbers likely older or computed pre-resolver-v2).
- COMMODITY = only genuine edge (PF ~3.77, DSR 1.0 on `cot_positioning` + CT=F).
- EQUITY best ML accuracy (83%+) but low volume.
- CRYPTO dominates volume but drags PnL (confidence inversion in gatekeeper).
- FOREX stressed PF 0.29 but documented SHORT bias.
- BOND + FUTURES thin/silent.
- CFTC COT (May 5 2026): commercials covering shorts in energy, record net-long in agriculture → reinforces COMMODITY edge.

**Grok Gate System v1 — same family as Kimi + Inception, 5 levels:**
1. Paper-Cut Gate (Monkey test + out-of-time 60/20/20, Sharpe>1, PF>1.5, >100 trades, WR>50, 2+ regimes).
2. Slippage & Reality Gate (crypto 0.1% round-trip, stocks 0.001+borrow, FX spread, position<1% ADV, 100-500ms latency sim, weekend test). Net-after-cost >50% gross or kill.
3. Safety Architecture Gate (hard daily 2% / weekly 5% / 3-loss-cooldown, quarter-Kelly + 2% risk-per-trade, no >3 strategies ρ>0.7, auto-shutdown if 30d Sharpe<0.5).
4. Skin-in-the-Game Gate ($500–$2k for 30 days REAL, paper+live shadow, journal every deviation, scale-to-10% if live Sharpe > 0.7× backtest).
5. Expansion Matrix (no 4th asset class until 3 are live-profitable 90d).

**Per-asset-class roadmap (Grok specifics, next 7 days):**
- **COMMODITY (P1):** wire COT commercial z-score gate (`quality_gates.py` + `extract_features`), run `cot_positioning` on CT=F with **lag-corrected** backtest (per `reports/cot_timing_leakage_audit_2026-05-13.md`), target PF>4.0 / DSR 1.0 → Level 4 micro-deployment.
- **EQUITY (P2):** per-class `ml_score >= 55` gate + FRED GDP/ISM overlay.
- **CRYPTO (P3):** Tuesday-only hard filter + cap `quan_engine` to 12% volume (already shipped via PR #906 per `supreme_plan_review_2026-05-13.md`).
- **FOREX (P4):** SHORT-only + COT reversal gate.
- **BOND (P5):** fix `FRED_API_KEY` secret + expand universe (TLT/IEF) + Connors RSI2 on TLT/IEF.

**Grok's commit-target file (proposed, content to be merged not blindly accepted):** `FOOLPROOF_ACTION_PLAN.md` v1 at repo root with first-real-money-date 2026-05-23 on COMMODITY `cot_positioning` CT=F.

**Important caveat:** Grok references `FRED_API_KEY` secret and a Tuesday-only crypto gate. The FRED key is already a known gap (cited in supreme-edge P0 cluster). The Tuesday-only claim needs cross-verification — it conflicts with `feedback_long_source_bias.md` and `reference_clean_data_symbol_wr.md` which call out *22 UTC* as the best slot and *08-09* as death zone, not Tuesday-vs-other-weekdays. Statement requires DB-query reproducer before trusting.

**Tie-in:** merge into `reports/expanded_enhancement_plan_2026-05-14.md` (separate file). Map each Grok level to corresponding Kimi level and Inception phase. Cross-check Grok per-class claims against current `asset_class_health` + `tier2_proven_strategies.cards` before accepting any specific gate config.

---

## 2026-05-14 — User prompt: "what techniques would a quant/hedge fund manager apply to fix gaps?"

User-pasted prompt (verbatim, 2026-05-14T23:50Z, queued for swarm + future research):

> Our website/github has been struggling to predict consistently stocks/crypto/forex/bonds/commodities/futures..etc. We MIGHT have some hidden edge.. we might have some extra factors if we add it that can get us to winners.. what sort of techniques would a Quant/hedge fund manager apply to our codebase to optimally fix the gaps?

**Why captured:** complements `2026-05-14 — Stuck-in-Backtest Escape Protocol` (S-BEP). That captured the *process*. This captures the *technique-set* question. Tie-in: feed both to swarm for cross-validation rounds.

### Mercury 2 reply (captured verbatim 2026-05-14T23:55Z) — concrete quant-fund-style playbook

7-section playbook with exact file targets. Pasted below for archival. Already partially absorbed into `reports/expanded_enhancement_plan_2026-05-14.md`; this is the source.

#### Section 1 — Data-enrichment / hidden-edge sources (with code locations)

| Edge source | Why | Code location | Quick start |
|---|---|---|---|
| CFTC COT commercial positioning | Proven edge for COMMODITY+FOREX (extends `cot_positioning`) | `audit_trail/quality_gates.py::extract_features()` + `audit_trail/feature_engine.py` | Reuse `COT_DATA_URL` constant; add `cots` column to daily feature df |
| Glassnode on-chain (MVRV/SOPR/exchange-flow) | Crypto-specific supply/demand invisible to price-only features | `forward_testing/signal_quality_ml.py::build_feature_vector()` | `pip install glassnode` or HTTP endpoint; merge JSON into `crypto_features` |
| LunarCrush social sentiment | Early pump-and-dump detection → better short-side timing | `audit_trail/quality_gates.py::ml_score` calc | Add `social_score` (0-1), feed to `signal_quality_ml` |
| FRED macro (VIX, CPI, Treasury yields, credit spreads) | Regime-aware filters for EQUITY/FOREX/BOND/COMMODITY | `audit_trail/feature_engine.py::add_macro_features()` | `pandas_datareader` last 60d; join on date |
| Option implied-vol surface (yfinance / ivol) | Delta-neutral vol-carry edge for EQUITY/ETF + high-vol regime filter | `audit_trail/feature_engine.py::add_option_features()` | Compute `iv30d`, `iv60d`, `skew` per ticker |
| Weather / calendar / agricultural cycles | COMMODITY seasonality | `audit_trail/feature_engine.py::add_seasonality_features()` | CSV of US holidays + month-of-year flag |

**Implementation tip:** lazy-load each new source returning None on failure. Existing quality_gates already fail-open on missing fields.

#### Section 2 — Feature engineering + edge extraction

- Cross-asset correlation features (crypto-vs-gold, equity-vs-bond) → `audit_trail/feature_engine.py` after per-asset features
- Lagged returns / vol windows (1/3/7 day) → `forward_testing/signal_quality_ml.py::create_lag_features()`
- Factor-model residuals (Fama-French, Barra) → `audit_trail/feature_engine.py::add_factor_residuals()`
- Non-linear interactions (XGBoost trees, NN embeddings) → replace logistic regression with `xgboost.XGBClassifier` in `signal_quality_ml`
- Feature-importance pruning (SHAP) → post-training step drops features SHAP<0.01

#### Section 3 — Model selection + robustness

- Bayesian hyperparam search (`optuna`) — 200 trials on 30-day rolling
- Ensemble (GBM + RF + Linear) — average probabilities
- CPCV (Purged Combinatorial CV) per `project_cpcv_gap_2026_04_28.md`
- Monte-Carlo ruin simulation — verify P(DD>30%) < 5% before paper trade
- PSR/DSR bootstrap — bump reps to 20,000 for tighter CI

#### Section 4 — Risk-gate + safety enhancements (vs current)

| Gate | Current | Mercury 2 target |
|---|---|---|
| R:R band | 1.25-3.0 (empirical) | **Harden to 1.5-2.0** — but contradicts our `config/hf_quality_gates.json:15` empirical PF measurement showing 1.25 better. Mercury 2 here is repeating the Foolproof §4.2 target we already determined was stale. NOT accepted without re-test. |
| ml_score | 0.82 (live, n>0 at 0.82) | 0.90 — but 0.90 yields n=0 per config line 15. NOT accepted without volume verification. |
| Tracking window | 24h (legacy global; 120h FOREX/BOND) | **Global 120h** — agreed P0 #5 in expanded plan |
| Transaction-cost model | MISSING | **Populate `TRANSACTION_COST_MODEL`** — agreed P0 #4 in expanded plan |
| Drift auto-pause | **SHIPPED 2026-05-14** (`_passes_drift_auto_pause_gate`) | Already done |
| Circuit-breaker | Daily 2% hard | Add soft CB that halves Kelly when 30d Sharpe<0.5 |
| Correlation cap | None | Reject new pick when portfolio-avg corr > 0.7 |

#### Section 5 — Execution + deployment

- CI/CD model training: `ci-model.yml` GHA running optuna → `config/best_params.json`
- Paper-trade sandbox: existing `alpha_engine/paper_trading/`
- Shadow-mode live: duplicate pick list in `smart_picks_engine`, one to exchange one shadow
- Real-money micro: $500 on COMMODITY `cot_positioning` (only T2 class)
- Daily Supreme Tracker: `scripts/daily_supreme_tracker.py` (already spec'd `reports/expanded_enhancement_plan §6`)
- Monitor: extend `audit_dashboard/template.html` with drift-gate status + per-asset cost-model breakdown

#### Section 6 — 7-step diagnostic loop

Edge report → weakest asset → root cause (monkey test 1000 random) → hypothesize → paper-trade ≥50 picks or 2 weeks → measure vs control (PSR/DSR, PF>1.2 WR>50) → deploy or rollback.

#### Section 7 — First-week sprint (~30h)

- Day 1: hf_stats fresh + verify gate config (DONE today)
- Day 2: drift gate wiring + stale-payload unit test (DONE today)
- Day 3: crypto-short gate fix (DONE today)
- Day 4: Glassnode MVRV pilot → 7-day crypto backtest
- Day 5: COT lag patch PR #941 → re-run `cot_positioning` walk-forward
- Day 6-7: enable daily edge report + $500 shadow on COMMODITY `cot_positioning` + drift-gate Slack alert simulation

**Open questions Mercury 2 asked back:** (1) prioritize which hidden source first (COT/Glassnode/FRED/option-IV)? (2) push drift-gate PR now or wait for COT lag patch? (3) want detailed 7-day paper-trade plan for COMMODITY?

---

## 2026-05-14 — Kimi reconcile investigator finding (P0 #3 resolved as type-(a))

Subagent investigator returned. **VERDICT: (a) — blacklist is at-intake-only, not retroactive.**

**Evidence:**
- `alpha_engine/config.py:216` lists `kimi_signal_tracking` in `BLACKLISTED_STRATEGIES`.
- Enforcement sites: `alpha_engine/smart_picks_engine.py:770` (intake gate), `alpha_engine/copy_trader_bridge.py:204` (copy-trader emission), `alpha_engine/outcome_resolver.py:751-757` (marks new resolves `exit_reason=BLACKLISTED`).
- `universal_resolved_picks.json` has 1,183 `kimi_signal_tracking` picks. ZERO have `exit_reason=BLACKLISTED`. All sample picks are Feb-Apr 2026 (pre-blacklist).
- `dashboard_data.json::systems.kimi_signal_tracking` shows 16 resolved picks (PF 5.80 / WR 76.2%) + 1,167 excluded (`_is_valid_resolved_pick` filter). The 16 winners are all pre-blacklist legacy edge.
- `riseoftheclaw/data/signal_tracking.json` (last_updated 2026-05-14 04:51 — AFTER blacklist) has 12 NEW signals with `entry_time=2026-05-13`, but `exit_price=None` / `exit_reason=None` (unresolved). These do NOT appear in `picks.active` on dashboard (intake gate IS blocking new emissions from reaching active list).

**Implication:** the "PF 5.80" figure on dashboard isn't a contradiction — it's correctly reporting the 16 pre-blacklist realized winners. The misleading part is the **dashboard label** doesn't say "blacklisted, legacy stats only". Two fixes:

1. **Display fix (low):** add a `blacklisted: true` flag to `systems[]` entries that are in `BLACKLISTED_STRATEGIES`. Dashboard renders a "BLACKLISTED — legacy stats" badge. ~2h.
2. **Emission fix (medium):** `riseoftheclaw/data/signal_tracking.json` is still being written even though picks are blocked at intake. Either (a) stop the writer entirely OR (b) document that the file is a "rejected emissions log" — useful for audit but not a live picks source. ~2h to decide + label.

**Original SUPREME EDGE P0 #2 claim re-verified:** -954% PnL / PF 0.26 was the **pre-noise-filter cumulative** as of 2026-05-11. Post-resolver-v2 + noise-filter, the 16 surviving resolved picks happen to be the cleanest wins, hence PF 5.80. Not a contradiction — just the cleaned subset. P0 #3 closes as "verified-not-bug". No code fix required for correctness; only the display-label cosmetic.

## 2026-05-15 operator gap-to-hedge-fund prompt

Note: MySQL credentials in original prompt have been REDACTED for security. Per `feedback_security_db_creds_exposure_2026_05_12`, rotate immediately if exposed.

```
review our project
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
which feeds to 50webs findtorontoevents.ca/audit
and findtorontoevents.ca/audit/hyrotrader
which uses github actions and mysql database mysql.50webs.com ejaguiar1_stocks pw:[REDACTED — rotated]
ejaguiar1_backtests pw:[REDACTED — rotated]
use our github PAT (part of the .env) to create a set of PRs to enhance our project

Check files: reports/MASTER_ACTION_PLAN_2026-05-15.md, reports/master_plan_lineage_2026-05-15.md, reports/supreme_plan_review_2026-05-13.md, reports/supreme_edge_plan_next_2026-05-12.md

Look for what are the gaps between our project and a world-class hedge fund.
We have been stuck in a paper trading cycle for months and need to bridge the gap to finally get to a state where we can trust our data with real money for trading.

Our project tries to predict crypto/stocks(aka equity)/forex/bonds/etfs/commodities/futures + penny stocks/cheap stocks. Despite running this for months we don't seem ready to use real money.

We also considered "swarm picks" — bunch of free/paid AIs giving trade ideas + why + datasets used + what a quant/hedge fund would do to get us to world-class. We tried to integrate copy traders/prediction markets (kalshi/polymarket) and a bunch of github projects e.g. https://github.com/virattt/ai-hedge-fund. We have tools\swarm + ruflo swarm (2 types of AI agent swarm) for idea generation/research/testing plans/coding.

Give us a list of prioritized enhancements to bridge the gaps and take our project to world-class for each asset class.
- what will it take? More strategies? Better backtesting? More symbols? Deep dive into super-failing asset classes?
- Which asset class is almost ready for REAL MONEY? Possibly COMMODITY (cotton CT=F per session evidence — PF 10.94 / 87.2% WR on n=39 in recent_closed). If so, why? And what else?
- How can we find a reliable statistical edge?
```

## 2026-05-15 — MASTER_ACTION_PLAN gap-to-HF table + M-050..M-054 (selection capture, lines 578-613)

Captured from `reports/MASTER_ACTION_PLAN_2026-05-15.md` IDE selection so the gap matrix + 5 ranked enhancements + M-050..M-054 are searchable from daily_ideas without re-opening the master plan.

**STATUS: pending operator triage**

**Gap to world-class hedge fund — per asset class:**

| Class | Live PF | Gap to PF>2 | Action |
|---|---|---|---|
| COMMODITY | 2.08 (resolved-v2 n=816) | already there | **REAL MONEY CANDIDATE** — cotton (CT=F) sub-class PF 10.94 on n=39 confirmed; awaiting Stage F real-money pilot per 6-Level Gate-to-Money |
| EQUITY | 1.42 (T2 candidate, n=428) | needs +0.58 PF or n→1000 | factor sleeves + extended OOS |
| ETF | 1.20 (borderline, n=88) | needs n→200 + PF→1.5 | wait for accrual |
| CRYPTO | 1.26 (sub-T2, n=8162) | needs −20% volume share on `quan_engine` drag (PF 0.66, 21% vol) | quan_engine quarantine pending |
| BOND | 1.72 (meets T2 thresholds, n=18) | needs n→100 floor | thin data — keep accruing |
| FOREX | 0.27 (genuine sub-floor, n=1249) | requires mutation-before-kill cycle | deep-dive gate open |
| FUTURES | n=2 | needs accumulation 90d | Donchian breakout system |

**Note on live-data discrepancy:** operator's table (PF 2.08 / n=816) reflects earlier snapshot. Current `dashboard_data.json::performance.asset_class_health.COMMODITY` (pulled 2026-05-15) reads PF 2.49 / WR 61.5% / n=322 — stronger headline numbers, lower n. Either way COMMODITY clears Tier-2 PF>1.5 with margin and is the only class doing so reliably.

**5 prioritized enhancements to bridge to world-class:**

1. **Resolver gap close** (P0 long-pending) — 0/3,500 unresolved was #1 blocker. Live `picks.recent_closed` now shows 3,500 resolved per `dashboard_data.json` so this MAY already be resolved post-`outcome_resolver.py:115-126 PNL_WIN_THRESHOLD_BY_CLASS` fix (2026-04-28). Verify before new architecture work.
2. **Cotton-style proof per asset class** — Tier-2 candidacy requires evidence pack: (a) walkforward decay≥0 across 3+ folds, (b) PSR>0.95, (c) DSR>0.95, (d) live 30 picks at projected PF on live tape. COMMODITY/CT=F has DSR=1.0000 + PF 10.94 already; needs (d).
3. **Swarm pick provenance** — current `swarm_picks_data.picks` (38 entries) is single-model (claude-opus-4-7) with persona prompts, NOT multi-model. Route personas to genuinely different underlying models (Sonnet, Haiku, Grok, DeepSeek) for real ensemble diversity.
4. **Statistical-edge finder** — implement Lopez de Prado PBO/CPCV harness (not just per-strategy backtest) so edges surviving structural overfitting surface. Memory `project_cpcv_gap_2026_04_28` already flags missing.
5. **Cross-AI stat validation** — 4 different AIs run perf numbers from `audit_dashboard/data/dashboard_data.json` and report WR/PF. Convergence = trust climbs. Divergence = surface it.

### 20.1 — Master plan additions (M-050 thru M-054)

| ID | Idea | Asset class | Owner | First action |
|---|---|---|---|---|
| M-050 | Cotton (CT=F) live-pilot — 30 picks @ projected PF on live tape | COMMODITY | operator | Charter Stage F entry; daily reconciliation |
| M-051 | Multi-model swarm ensemble (Sonnet/Haiku/Grok/DeepSeek/Claude) for real diversity | all | claude-desktop | swap one persona to Sonnet, measure WR delta |
| M-052 | PBO/CPCV harness per Lopez de Prado | all | (unassigned) | spike against COMMODITY first |
| M-053 | 4-AI stat-validation cross-check | all | claude-desktop | 4 engines compute PF/WR from dashboard_data.json, surface divergence |
| M-054 | ai-hedge-fund (virattt/ai-hedge-fund) integration spike | crypto/equity | (unassigned) | read repo, propose adapter |

## 2026-05-15 — User prompt: "how would a quant baseline performance + hunt gaps cheaply?"

Operator framing: Quant trying to save company with gigantic codebase predicting stocks/crypto/forex/bonds/commodities/futures/ETFs + penny stocks + meme coins. Wants baseline-then-gap-hunt playbook using mostly free data + existing AI API budget (no expensive paid feeds).

Specific sub-questions raised:
- Asset class with too few symbols in universe?
- Backtests great but forward bad? (overfit signature)
- Failing strategies — delete? invert? re-sim with different entry criteria?
- Industry-standard / proven-pattern research?
- Scrape social for great strategies?
- Pick AI brains for per-class concepts: what free data, what stats/math, what backtest type? e.g. stocks → earnings perf correlation, financial statements, SEC filings?

### Answer captured (caveman-compressed, full technical substance)

**Phase 0 — Baseline (free, do first):**
- Single source of truth = `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` (resolver-v2 trustworthy post 2026-04-28 fix).
- Per class compute: n, WR, PF, Sharpe, Sortino, MDD, expectancy, avg hold, payoff ratio, BT-vs-FW WR delta (the overfit detector).
- Per strategy×class: same matrix + survivorship (did it stop emitting?) + Darwin score v2.
- Per symbol×class: same + concentration (top-5 symbols % of volume — quan_engine MATIC ghost was 755/1001 = 75%, that's the smell).
- Universe-size table: symbols emitted vs symbols in feed (small universe = no edge room).

**Phase 1 — Gap taxonomy (5 buckets, each with a fix path):**

| Gap | Detector | Fix path |
|---|---|---|
| Thin universe | `symbols_emitted / symbols_available < 0.2` | Expand scraper coverage; check `*_scraper.py` modules |
| BT/FW divergence | `BT_WR − FW_WR > 15pp` | PBO/CPCV (M-052), Deflated Sharpe; suspect overfitting |
| Concentration ghost | top-5 symbols >50% volume | Quarantine (quan_engine MATIC, clone_hl_copy placeholder) |
| Resolver/data bug | impossible numbers (100/100/100, -0.27 PF) | Audit resolver before killing |
| Genuine sub-floor | clean n>500, PF<1 | Mutate-before-kill (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) — try inverse, symbol rotation, time-of-day filter; only kill if all 3 axes fail |

**Phase 2 — Industry-standard playbook per class (free-data first):**

| Class | Free data | Math | Proven backtest pattern |
|---|---|---|---|
| EQUITY | yfinance OHLCV, SEC EDGAR (10-K/10-Q/8-K free API), FRED macro, Finnhub free tier earnings calendar, Reddit/StockTwits | PEAD (post-earnings drift), Fama-French 3/5-factor regression, accruals (Sloan), short-interest, insider Form 4 | Walkforward 252d train / 63d test; PEAD = 60-day drift post-surprise |
| CRYPTO | Binance/CoinGecko/Kucoin OHLCV (failover chain), Hyperliquid funding, on-chain via Dune free tier, LunarCrush social | Funding-rate carry, perp-spot basis, MVRV, NVT, social momentum (LunarCrush already wired) | Triple-barrier (López de Prado); regime-switching HMM (already have 7-state) |
| FOREX | OANDA practice feed (free), FRED rate differentials, MyFXBook public copy-trader leaderboard scrape | Carry-trade rate-diff, Dollar smile, COT positioning (CFTC free CSV) | Walk-forward + carry overlay; mean-reversion only in ranging regime |
| BOND | FRED yield curve, TreasuryDirect, ETF proxies (TLT/IEF/SHY) | Slope (2s10s), curvature, real yield, breakeven inflation | Macro-regime gated; trend in TLT |
| COMMODITY | yfinance futures continuous, CFTC COT free, USDA WASDE reports free | Backwardation/contango, COT extremes, seasonality | Donchian breakout (50/100d) — Turtle Traders proven; KMLM/DBMF replication |
| ETF | yfinance + ETF.com flows (scrape) | Sector rotation, factor tilts | Cross-sectional momentum (12-1 month) |
| FUTURES | Same as commodity + index futures via CME free EOD | Trend-following CTA replication (DBMF/KMLM ~$2B AUM each) | 12-month time-series momentum (Hurst exponent confirmation) |
| PENNY/MEME | Reddit (free API), Twitter scrape, Pump.fun on-chain | Volume spike Z-score, social mention rate-of-change, holder concentration | Event-driven only; tight stops; treat as lottery sleeve <2% portfolio |

**Phase 3 — Failing-strategy decision tree (instead of "delete?"):**
```
fail_strategy:
  if n < 30: hold, accrue more
  elif BT/FW gap > 15pp: PBO/CPCV → if PBO>0.5, kill (overfit)
  elif concentration top1 >40%: quarantine that symbol, re-eval residual
  elif PF < 0.7 and n>200:
    try axis-1 (inverse) → if PF>1.3, ship inverted
    try axis-2 (symbol rotation) → drop bottom-quartile symbols
    try axis-3 (regime gate) → only fire in matching HMM state
    if all fail: kill with autopsy doc in reports/deep_dive_<class>_<date>.md
  else: keep, monitor
```

**Phase 4 — Cheap edge-hunting using AI keys we already have:**
- Use existing swarm (`tools/swarm` + `tools/swarm-ruflo`) to fan questions to Cerebras/Ollama-cloud/DeepSeek/Grok/Kimi for FREE.
- Per-class prompt template:
  - "Given asset class X, free data sources Y, give 5 statistical signals with academic citation + expected Sharpe + implementation skeleton in Python."
  - Cross-validate: 4+ models propose same signal = high-confidence candidate.
  - Then backtest the convergent signal on our universe with vectorbt/bt (already wired per `project_next_phase_integrations_2026_04_22`).
- Scrape MyFXBook/eToro public leaderboards (free) for top forex copy traders → reverse-engineer their entry signals via correlation analysis on their trade timestamps vs our feature library.

**Phase 5 — How pros do it (cheap version):**
- AQR/Renaissance: factor zoo + ensemble. Cheap version: implement Fama-French 5 + momentum + quality on EQUITY (free via yfinance + EDGAR).
- Two Sigma: alternative data. Cheap version: Reddit/Twitter sentiment (free), Google Trends (free), GitHub commits for crypto projects (free), satellite imagery via Planet Labs free tier.
- Bridgewater: macro regime. Cheap version: FRED-based 4-quadrant regime detector (growth↑↓ × inflation↑↓) — gates all strategies.
- Citadel: execution edge. Not replicable cheaply; skip until real-money phase.
- DE Shaw: stat-arb. Cheap version: cointegration pairs (statsmodels free) on EQUITY/ETF — `cointegration_finder.py` spike.

**Phase 6 — Operator first 5 actions (ranked by ROI):**
1. **PBO/CPCV harness (M-052)** — single biggest credibility lift; surfaces overfit vs real edge. Spike on COMMODITY first.
2. **Per-class universe-size audit** — one-shot script, output table of symbols_emitted/symbols_available per class. If FOREX has 7 pairs and CRYPTO has 200, that alone explains FOREX sub-floor.
3. **BT/FW divergence dashboard tile** — surface the overfit detector on /audit.
4. **Multi-model swarm fan-out (M-051)** — query 6 AI engines with the per-class prompt template above; converge signals.
5. **CFTC COT + FRED ingestor** — 2 free data sources unlock COMMODITY/FOREX/BOND macro overlay. Highest free-data ROI.

**Anti-patterns to avoid (already burned us this session):**
- Don't kill on raw `by_asset_class` aggregates — use `asset_class_health` (resolver-v2).
- Don't trust headline WR until ghost-symbol cleanup (MATIC 660-row artifact, quan_engine 755-row twin).
- Don't trust paper account names as gates (`feedback_gate_at_execution_not_generation`).
- Don't paste DB creds / PATs in chat (memory `security_pat_exposure_2026_05_15`).

## 2026-05-15 — Grok senior-quant brutal assessment of MASTER_ACTION_PLAN

Operator pulled in Grok as outside-quant second opinion. Grok reviewed branch `docs/master-action-plan-2026-05-15` (commit 533ff90c8de…), live MASTER_ACTION_PLAN_2026-05-15.md (65k lines, M-001..M-027+), open PRs post-triage, MySQL forensics on `ejaguiar1_stocks`/`ejaguiar1_backtests`, dashboard_data.json.

### Verdict: "No — current plan won't reach world-class in present form"

Reasons:
- Laundry list of ideas (M-001..M-027+) not a dependency-managed execution roadmap with kill criteria.
- Underestimates foundational rot in data quality + outcome tracking.
- Spreads effort across asset classes instead of concentrating where edge plausibly exists (COMMODITY/cotton).
- Good instincts (DB freshness, drift CB, sizing, DSR, COT lag correction) but lacks ruthless prioritization.

Good news: recent triage (Claude+Copilot merges) cut main from 36 fail → 4 fail / 122 pass. Necessary hygiene done; now needs strategy.

### Grok's baseline reality table (live dashboard_data.json + DB forensics)

| Class | PF / WR / n | Verdict | Biggest problem |
|---|---|---|---|
| COMMODITY | 2.49 / 61.5% / 322 | Best candidate | Tiny active universe (mostly CT=F + HG=F) |
| EQUITY | 1.57 / 51.9% / 420 | Marginal T2 | No earnings/SEC integration |
| ETF | 1.48 / 58.5% / 106 | Borderline | Very small n |
| CRYPTO | 1.36 / 46.7% / 8011 | Sub-T2 drag | Low-quality symbols + quan_engine/unknown drag |
| FOREX | 0.81 / 52.3% / 342 | Recovering, weak | Historically terrible |
| BOND | 0.66 / 54.5% / 11 | Stat-meaningless | n=11 (TLT/HYG concentration) |
| FUTURES | Dead | — | Almost nothing |

### DB reality (CRITICAL — biggest finding)

- `at_raw_picks`: 145k+ signals, but **only 0.08% have outcomes** in `at_signal_outcomes`.
- `paper_trades` table: **completely empty**.
- `paper_portfolio_daily` table: **completely empty**.
- Hundreds of thousands of ghost rows.
- **No reliable "what happened after we published this pick" loop for most history.**

⇒ This is THE single biggest reason world-class (or even reliable T2) cannot be claimed yet. No trustworthy forward test.

### 6 gaps vs world-class operation
1. **Symbol universe & liquidity coverage** — unknown per class. Probably too many garbage meme/penny names, too few liquid contracts in commodities/futures.
2. **Outcome tracking** — catastrophic (per above). Without resolved outcomes + paper P&L, DSR/walk-forward/pruning are theater.
3. **Forward validation discipline** — weak. Lots of backtests, little rolling OOS + live decay measurement.
4. **Strategy lifecycle management** — no systematic delete/invert/re-param/quarantine process. Failures linger.
5. **Execution realism** — slippage, sizing, concentration, drift CB still scaffolding (Kimi WORLD_CLASS_ENHANCEMENT_PLAN + Phase J safety modules trying to fix).
6. **Data enrichment per class** — ~zero fundamental/macro/sentiment for equity+bond. Crypto has on-chain but not systematically used.

### Grok's prioritized 90-day plan

**Phase 0 (next 3–4 weeks) — stop the bleeding:**
- Finish DB Freshness Guardian; make GHA actually fail run on RED (most code exists).
- Force outcome tracking to work: resolver populates `at_signal_outcomes` reliably; paper trading writes to `paper_trades` + `paper_portfolio_daily`.
- Symbol universe audit script per asset class (coverage% + liquidity filter via free sources).

**Phase 1 (next 6–8 weeks) — pick ONE horse:**
- COMMODITY cotton (CT=F) is the only rational pilot. Kimi + Grok converged on same conclusion.
- Everything else (most M-00x for equity/bond/ETF/etc.) deprioritize or strict opt-in sidecar until cotton is production-grade with real paper-trading track record.

**Phase 2 — systematic pruning + inversion framework:**
For any strategy live >60–90 days:
- If OOS/live Sharpe < 0.3–0.4 AND stat-significant → delete or hard quarantine.
- If strong negative correlation with main signal → consider inverted version (under-used in our system).
- Otherwise → tighten entry filters or add cost model BEFORE touching parameters.

### Leveraging AI API keys (the smart way)

Use as research accelerator, never as oracle.

**Good prompt patterns:**
- "For [asset class], list 8–10 high-signal, low-cost features that appear in peer-reviewed papers 2018–2025, with the free data source for each."
- "Summarize core logic, entry/exit rules, common failure modes of classic [carry / momentum / mean-reversion] strategy in [FX / commodities / equities], including realistic transaction cost assumptions."
- "What free or cheap data series should I pull to test whether earnings surprise + post-earnings drift still works in current regime for mid-cap US stocks?"

**Bad use:** asking LLM to write production position sizers or risk models without heavy verification.

### Free/low-cost data sources per class (Grok's realistic list)

- **Equity/Penny/Meme:** yfinance (prices+some fundamentals), SEC EDGAR (10-K/Q via `sec-edgar-downloader`), FRED (macro), Google Trends (sentiment proxy).
- **Crypto:** CoinGecko (excellent free tier), on-chain via public explorers or free Dune queries.
- **Forex:** ECB daily rates, FRED, OANDA free tier.
- **Commodity/Futures:** CME delayed EOD, Quandl free EIA energy series, USGS metals.
- **Bond:** FRED Treasury + corporate filings via EDGAR.
- **Sentiment:** Responsible Reddit scrape (PRAW with rate limits) + Twitter/X API + LunarCrush free crypto.

### Final recommendation (Grok)

> Stop treating MASTER_ACTION_PLAN_2026-05-15.md as sacred. Treat it as brain dump of ideas.

90-day winning strategy:
1. Make data trustworthy (Freshness Guardian + outcome tracking).
2. Pick one asset class (cotton) and make it genuinely production-grade with proper sizing/costs/kills/paper-trading.
3. Build simple but ruthless pruning + inversion framework.
4. ONLY THEN expand universe + add cleverer ideas (PEAD, sector momentum, TSMOM, etc.).

### Grok's offer (operator deferred routing decision)

Two paths offered:
- (A) Write tight 90-day execution plan as new .md replacing sprawling master plan (data ingestion priorities per class free-only, minimal M-IDs that matter now, delete/invert decision framework, AI prompt templates per class).
- (B) Start with deep audit of ONE asset class (e.g. COMMODITY symbol coverage + data flow) first.

Operator routing: pending.

### Convergent findings — Grok ∩ this session ∩ Kimi ∩ Mercury

| Finding | Grok | Mercury 6-phase | Kimi WORLD_CLASS | this session daily_ideas |
|---|---|---|---|---|
| Outcome tracking catastrophic | ✓ DB forensic 0.08% | ✓ Phase 0 | ✓ resolver gap | ✓ resolver-v2 verify (#1 enh) |
| COMMODITY/cotton is the pilot | ✓ | ✓ | ✓ | ✓ (M-050) |
| Stop spreading effort | ✓ | ✓ | ✓ | (implicit) |
| PBO/CPCV missing | (implied: forward validation gap) | ✓ | ✓ | ✓ (M-052) |
| Free data per class | ✓ explicit list | ✓ | ✓ | ✓ Phase 2 table |
| Mutate-before-kill / inversion | ✓ | partial | ✓ | ✓ Phase 3 tree |
| Symbol universe audit | ✓ | ✓ | ✓ | ✓ #2 enhancement |

5 independent senior-quant analyses (Grok / Mercury / Kimi / Inception / ChatGPT) all converge on **same 4-step plan**. Convergence ≥ trust. **Path forward unambiguous** — execute, don't re-deliberate.

## 2026-05-15 — 3-investigator verification of Grok claims (subagent fan-out)

User said "use subagents and see if you can assist on research/analysis/enhancements". Dispatched 3 parallel `caveman:cavecrew-investigator` agents (read-only, caveman-compressed output) to verify Grok's biggest claims against local repo state.

### Investigator 1 — Outcome tracking rot claim: **PARTIALLY WRONG**

Grok conflated two different systems:

| System | Status | Source |
|---|---|---|
| Local resolver `alpha_engine/outcome_resolver.py` | **WORKS** — hourly cron via `.github/workflows/outcome-resolver.yml:6`; writes `alpha_engine/data/closed_picks.json`; `dashboard_data.json::recent_closed` = 3,500 resolved; only 66/3500 (1.9%) have null PnL | repo evidence |
| 50webs MySQL DB (`at_signal_outcomes`) | **GHOST-INFESTED** — 121 outcomes / 145,879 raw picks = 0.08% as Grok cited; DB is stale, manual sync only | Grok's DB query |
| `paper_trades` + `paper_portfolio_daily` tables | **EMPTY BY DESIGN** — generator at `alpha_engine/copytrader_integration.py:82` has NO active caller; suspended pending Phase J safety infra (PRs #1026/#1052) | `claude_chat_audit_review_2026-05-15.md:38` + `paper_trading/mysql_sync.py:60` |

**Verdict:** Resolver works. DB ghost-infestation is a separate cleanup task, NOT a "no outcome tracking" emergency. Paper-trading emptiness is deliberate (Phase J gate). Grok was reading dead DB rows, not live local state.

**Action implication:** Don't redo resolver. DO: (a) clear 655k ghost rows from MySQL, (b) wire paper_trades generator post-Phase-J.

### Investigator 2 — Symbol universe audit: REAL THIN CLASSES DIFFER FROM GROK'S CLAIM

| Class | Emitting / Config | Top-1 | Flag |
|---|---|---|---|
| CRYPTO | 179 / 109 (+64% from copy-trader CEX integrations) | BTCUSDT 15.9% | OK |
| EQUITY | 47 / 50 (94%) | AMD 11.2% | OK |
| ETF | 11 / 11 (100%) | QQQ 18.7% | OK |
| FOREX | 22 / 20 (110%) | EURUSD 9.9% | **OK — NOT thin** |
| COMMODITY | 9 / 25 (36%) | CT=F **55%** | **GHOST + scanner underutilization** |
| BOND | **2 / 14 (14%)** | TLT **75%** | **GHOST + scanner barely firing** |
| FUTURES | **0 / 14 (0%)** | — | **DEAD — `production_scanner.py::passes_active_gate` not routing** |

Sources: `audit_dashboard/data/dashboard_data.json` (picks.recent_closed n=3500, picks.active n=29); `alpha_engine/config.py:92-131` (SECTOR_MAP), `:536-580` (FOREX 20 pairs), `:615-646` (COMMODITY 25), `:781-798` (BOND 14).

**Verdict reversal:** FOREX is NOT thin. **BOND is the thinnest (14% utilization, TLT 75% concentration).** COMMODITY is next (36%, CT=F 55%). FUTURES is dead at the scanner level. Investigator 2's verdict overrides Grok's "FOREX historically terrible" framing — FOREX has plenty of universe, the strategies are the problem.

**Action implication:**
- BOND: expand `bond_scanner.py` to emit from full 14-symbol roster (currently TLT/HYG only).
- COMMODITY: scanner not exercising 16/25 contracts; verify COT sensitivity gate isn't filtering too hard.
- FUTURES: check `production_scanner.py::passes_active_gate` FUTURES branch — 14 symbols configured, 0 emitting.

### Investigator 3 — CT=F (cotton) Stage F readiness: **REBUTTED**

Memory claim: PF 10.94 / WR 87.2% / n=39 / DSR=1.0000 → "real-money candidate".

Actual `recent_closed` filter on CT=F:
- **n=48** (41 WON + 7 LOST), **WR=85.4%** (close to memory but not 87.2%)
- **PnL field bug:** `realized_pnl_pct` ALWAYS NULL; dashboard reads `pnl_pct` instead. PF 10.94 cannot be verified from this data without the schema fix.
- **CT=F has ZERO active picks** — emitter dormant since ~2026-05-12. Recent COT-lag-corrector patches (`tools/cot_lag_corrector.py` + dedup guard) may have halted emission.
- Sources: `multi_asset_copytrader` + `multi_asset_cot` (two source systems, not one).

**Other COMMODITY symbols (cotton sole winner):**

| Symbol | n | WR |
|---|---|---|
| CT=F (cotton) | 41W/7L | **82.9%** |
| ZW=F (wheat) | 10 | 0% |
| ZS=F (soy) | 8 | 0% |
| CL=F (crude) | 4 | 0% |
| GC=F (gold) | 3 | 0% |
| SI=F (silver) | 3 | 0% |
| HG=F, KC=F | 2 each | 0% |
| NG=F | 1 | 0% |

⇒ **CT=F is the sole COMMODITY winner; everything else wipes out.** The 2.49 PF / 61.5% WR aggregate is entirely a cotton-survivorship artifact.

**Charter §2 Tier-2 floor:** PF≥1.5 / WR≥50% / **MDD≤20% / n≥100**. CT=F has **n=48 (below n≥100 floor)**. Cannot enter Stage F real-money pilot yet.

**3 blockers to Stage F:**
1. **n<100** — need 52 more closed CT=F trades to clear floor.
2. **Signal stopped** — zero active picks; emitter dormant since 2026-05-12. Investigate cot_lag_corrector dedup guard.
3. **PnL schema mismatch** — `realized_pnl_pct` always NULL; PF/Sharpe/DSR cannot be trusted until schema fixed.

### Consolidated 5-action shortlist (post-investigation)

Ranked by ROI given verified evidence:

1. **Unblock CT=F emitter** — investigate why `multi_asset_cot` + `multi_asset_copytrader` stopped emitting cotton since 2026-05-12. Likely culprit: `tools/cot_lag_corrector.py` dedup guard. Without this, cannot accrue n→100 for Stage F.
2. **Fix `realized_pnl_pct` schema bug** — without this, no class can claim PF/Sharpe/DSR rigorously. Highest-leverage data-integrity fix.
3. **Wire FUTURES branch in `production_scanner.py::passes_active_gate`** — 14 configured symbols, 0 emitting. Free coverage expansion.
4. **Expand `bond_scanner.py` beyond TLT/HYG** — 12 configured BOND symbols never tested. Could unlock real BOND signal or kill class definitively.
5. **MySQL ghost-row purge** — separate from local resolver fix; clean 655k stale rows from `at_raw_picks` so future DB-based audits are meaningful.

Note: items 1+2 are **strict prerequisites** before any "real money" decision. Items 3+4 are universe-expansion safety nets. Item 5 is hygiene.

## 2026-05-15 — CRITICAL REVERSAL: top 2 actions invalidated by 2nd-round investigation

User authorized autonomous execution. Dispatched 2 more `caveman:cavecrew-investigator` agents to find exact fix points for actions #1 (CT=F emitter unblock) and #2 (realized_pnl_pct schema fix). Both came back with reversals.

### Reversal 1 — CT=F is NOT dormant due to cot_lag_corrector. It is **deliberately blacklisted.**

| File | Line | Finding |
|---|---|---|
| `audit_trail/quality_gates.py` | 1266-1273 | `COMMODITY_BLACKLIST` set contains **CT=F** explicitly |
| `audit_trail/quality_gates.py` | 1262 | Justification: "CT=F (cotton) n=12 WR 8.3% sum -8.41% KILL" (2026-04-29) |
| `audit_trail/quality_gates.py` | 5072-5081 | `passes_active_gate()` hard-rejects if `symbol.upper() in COMMODITY_BLACKLIST` unless env `COMMODITY_SUBCLASS_KILL_DISABLED=1` |

**Phase 2-D panel verdict (2026-04-29) killed CT=F because rolling-window WR dropped to 8.3% on n=12.** The 82.9% WR / n=48 Investigator-3 saw in `recent_closed` is the **pre-kill historical window** — those picks resolved into `recent_closed` but the gate prevents NEW CT=F emission.

⇒ Memory + `reports/MASTER_ACTION_PLAN_2026-05-15.md` M-050 + this session's earlier daily_ideas + the Grok/Kimi/Mercury convergence claims that "CT=F is the real-money candidate" are **all reading the historical pre-kill window**. The operator's own kill protocol already disqualified cotton.

**Three possible interpretations:**
1. **Phase 2-D kill was too aggressive** (n=12 below a sane kill-floor; should have waited for n≥50). Under this read, cotton should be revived.
2. **The 82.9% WR is regime-window survivorship** (hot streak then mean-reversion; kill caught the reversion). Under this read, revival loses money.
3. **Two sub-strategies inside the CT=F bucket** — n=12/WR 8.3% rolling vs n=48/WR 82.9% lifetime cannot both be true unless the kill missed a sub-pattern.

**High-leverage data-interpretation problem, not a code bug.** Cannot be "fixed" by code; requires CT=F pick histogram by date + rolling-50 WR overlay + source-system split + Phase 2-D verdict re-replay.

**Risk of naive revival:** flipping `COMMODITY_SUBCLASS_KILL_DISABLED=1` without re-running the analysis means trusting a number (82.9%) the operator's own protocol already labeled false.

### Reversal 2 — `realized_pnl_pct` is **dead-code fallback chain**, not a silent-wrong-answer bug

| File | Line | Op | Field |
|---|---|---|---|
| `alpha_engine/outcome_resolver.py` | 964 | write | `pnl_pct` only (NO `realized_pnl_pct`) |
| `alpha_engine/forward_validator.py` | 787, 1295 | write | `pnl_pct` only |
| `audit_dashboard/template.html` | 15158, 16401, 16410, 16481 | read | `realized_pnl_pct \|\| pnl_pct \|\| 0` (fallback) |
| `audit_trail/dashboard_generator.py` | 6998 | read | `realized_pnl_pct` (in fallback chain) |

**Field is never populated. All reads fall back to `pnl_pct`. PF/WR/DSR are NOT wrong — they read the right field via fallback.** Investigator-3's "PF 10.94 cannot be verified" was wrong; PF is computable from `pnl_pct`, which IS populated. Action: simplify the dead-code fallback chain. Low priority, no data-integrity issue.

### Revised 5-action shortlist (post-reversal)

Old action 1 (CT=F unblock) → **paused pending sub-strategy autopsy of the n=48 vs n=12 paradox**.
Old action 2 (schema fix) → **demoted to low-priority cleanup**.

New ranked actions:

1. **CT=F kill-vs-revive autopsy** — produce `reports/deep_dive_cotton_2026-05-15.md`: per-source split (`multi_asset_copytrader` vs `multi_asset_cot`), rolling-50 WR timeline, regime decomposition (HMM state per pick), Phase 2-D kill-window re-replay. If kill correct → kill stays; if Phase 2-D used too-small n → revive with stricter MATCH gate (PR #1058). Do NOT manually flip the env var without the autopsy.
2. **Wire FUTURES branch in `production_scanner.py::passes_active_gate`** — 14 configured symbols, 0 emitting. Verify it's not symmetric-blacklist style like COMMODITY_BLACKLIST.
3. **Expand `bond_scanner.py` beyond TLT/HYG** — 12 of 14 BOND symbols never tested (TLT 75% concentration).
4. **Audit other COMMODITY blacklist entries** — Phase 2-D killed 7/7 sub-class symbols. If cotton kill was wrong, others may be too.
5. **Re-think "5-AI convergence = trust"** — Grok/Mercury/Kimi/Inception/ChatGPT all agreed cotton was the real-money pilot. They all read stale memory. Convergence at the input-data layer ≠ convergence at truth.

### Meta-lesson

This session demonstrates the most dangerous failure mode of multi-AI consensus: **5 senior-quant analyses converged on the wrong conclusion (cotton = real-money) because they all read the same stale memory entries.** Convergence at the data-input layer creates the illusion of independent verification.

**Tighter protocol going forward:**
- Before claiming any asset class real-money ready, grep `audit_trail/quality_gates.py::*_BLACKLIST` for the symbol.
- Before trusting an AI's "convergent" finding, ask: did all AIs read the same input file? If yes, that's correlated noise, not independent signal.
- M-053 (4-AI stat-validation cross-check) must **rotate the input file** per engine to avoid this trap.

## 2026-05-15 — REVERSAL 3: FUTURES is also a deliberate kill, not unwired. Only BOND survives.

Verified actions #2 (FUTURES gate) and #3 (BOND scanner) directly via grep of `audit_trail/quality_gates.py`:

### FUTURES — 0/14 emitting is DELIBERATE (drain kill)

| Line | Entry | Meaning |
|---|---|---|
| `quality_gates.py:1317` | `BLOCKED_ASSET_CLASSES = set()` | class-level block removed 2026-04-16 (caused data starvation) |
| `quality_gates.py:1611-1617` | 7 `(strategy, "FUTURES")` pairs blocked | connors_rsi2, hyperopt_connors_rsi2, mean_reversion_bollinger, extreme_oversold_bounce, vix_reversal, futures_mean_reversion, ema_stack_momentum — all 0% WR |
| `quality_gates.py:1916` | `("FUTURES", "futures_momentum")` | 7d WR 4% vs 42% baseline |
| `quality_gates.py:2006-2013` | `("FUTURES", "multi_asset_copytrader")` | "n=157, WR=2.5% → critical drain, surgical block" |

⇒ FUTURES isn't unwired by accident — **every emitter (strategy + source) is individually blocked because the class genuinely drained at 2.5% WR.** Matches memory `project_futures_kill_without_replacement`. Action #2 ("wire FUTURES gate") is **invalid** — the gate works fine, FUTURES needs **NEW strategies**, not gate-wiring. Rollback note already at `:2010-2013`: run `tools/mutation_analysis.py` first if FUTURES is rebuilt.

### BOND — 2/14 emitting IS a genuine scanner-coverage gap (action #3 SURVIVES)

| Line | Entry | Meaning |
|---|---|---|
| `quality_gates.py:1987` | `("BOND", "alpha_engine_fast")` | only ONE strategy-pair blocked |
| — | no `BOND` in `BLOCKED_ASSET_CLASSES` | class is alive |
| `quality_gates.py:5218` | `_is_bond_etf_exempt` | BOND/ETF given thin-sample exemption (Phase 3, PF 1.72/WR 50%) |

⇒ BOND class is alive and even exempted for being thin. Only `alpha_engine_fast` is blocked for BOND. So **only TLT/HYG emitting (2/14) is a real scanner gap, not a kill.** Action #3 (expand `bond_scanner.py` to the full 14-symbol roster) is the **one genuinely actionable code item** from the original shortlist.

**Caveat before editing bond_scanner:** adding 12 untested BOND symbols floods the system with picks that have n=0 history. The Tier-2 n≥100 floor means they won't size up, but they WILL consume scan budget. Expansion should be **staged** — add 3-4 symbols, accrue n≥50, then add the rest. Not a one-shot 14-symbol dump.

### Final session tally — 3 reversals, 1 survivor

| Original action | Verdict | Why |
|---|---|---|
| 1. CT=F emitter unblock | ❌ REVERSED | deliberately blacklisted (Phase 2-D, WR 8.3%/n=12) |
| 2. realized_pnl_pct schema fix | ❌ DEMOTED | dead-code fallback chain, no data bug |
| 2b. FUTURES gate wiring | ❌ REVERSED | every emitter deliberately blocked (2.5% WR drain) |
| 3. bond_scanner expansion | ✅ SURVIVES | genuine scanner gap; class alive + exempted |
| 4. COMMODITY blacklist audit | ✅ VALID | Phase 2-D killed 7/7 — if cotton kill wrong, others may be |
| 5. MySQL ghost purge | ✅ VALID | hygiene, separate from local resolver |

**The deepest meta-finding of the session:** the "thin/dead asset class" framing — repeated by Grok, the master plan, and this session's own first-pass analysis — is **mostly wrong**. CRYPTO/EQUITY/ETF/FOREX have healthy universes. COMMODITY and FUTURES are *deliberately* shrunk by kill protocols that already ran. The system is not leaking from un-wired gates; it is doing exactly what its kill protocols told it to do. **The real gap is kill-WITHOUT-replacement** — when a class drains, the protocol kills the bad strategies but no process generates new ones. That is the M-052 (PBO/CPCV harness) + strategy-generation gap, not a wiring bug.

**Single highest-leverage next action:** build a **strategy-replacement pipeline** that triggers when a class/strategy gets killed — auto-spawn a deep-dive subagent that proposes 3 replacement strategies (from the free-data + academic-signal library in the Phase-2 table above), backtests them, and queues survivors. Without this, every kill permanently shrinks the tradeable universe and the system slowly starves. This is why the project has been "stuck in paper trading for months": kills outpace births.

## 2026-05-15 — Swarm second-opinion sharpens the root-cause diagnosis

Ran `/swarm-second-opinion` (consensus-3 preset: deepseek, xai, kilo) on the kill-without-replacement hypothesis. Run dir: `swarm_runs/second-opinion-20260515T080442Z`. xai returned malformed JSON (transport 400) → 2/3 valid. **DeepSeek + Kilo both HIGH confidence, both agree.**

### CONSENSUS (2/2 valid engines)

- Kill-without-replacement diagnosis is **directionally correct but incomplete — it is the proximal cause, not the root.**
- The proposed auto-spawn pipeline is a **patch, NOT the highest-leverage move.** Both engines independently said: without fixing the deeper issue first, replacement strategies get killed as fast as they spawn — Kilo's phrase: *"a faster-running conveyor belt to the kill floor."*
- The **deeper root cause** is two-fold:
  1. **Kill thresholds are mis-calibrated** — they fire on small-n rolling windows (FUTURES n=157, cotton n=12) with no statistical test. A 2.5% WR on n=157 could be noise around a true 40% WR with high variance (DeepSeek). Kill logic uses fixed WR/PF/decay cutoffs without sample-size or variance adjustment.
  2. **Forward-validation is not wired into kill decisions.** `walk_forward_validator.py` exists and emits ROBUST/MODERATE/FRAGILE verdicts, but its output does NOT feed kill-threshold calibration. Kill thresholds are calibrated on **in-sample closed picks that include the very strategies about to be killed** — circular.

### Kilo's codebase evidence (raised confidence)

- `commodity_kill_switch.py` + `fx_kill_switch.py` run post-ingest hard-blocks (PF<0.9 @ n≥20, 0% WR @ n≥15, decay>15pp).
- `strategy_killer.py` runs separate multi-source kill classification.
- `PERMANENTLY_KILLED_STRATEGIES` in `quality_gates.py` = **65+ entries, growing**, many zero-WR at large n.
- Score floors in `quality_gates.py:314-370` have been **raised, lowered, re-raised multiple times in weeks** → "no stable calibration anchor."
- `score_booster` enrichment is **crypto-gated** (`quality_gates.py:346-350`) → COMMODITY/FUTURES/EQUITY strategies operate at a systematic scoring disadvantage. COMMODITY actionable range 30-55 vs floor 60 = ~0 picks pass — a structural bias, not a strategy-quality problem.

### REVISED highest-leverage action order (swarm-corrected)

The auto-spawn pipeline drops from **step 1 → step 4**. Correct order:

1. **Re-calibrate kill thresholds on walk-forward data.** Use `walk_forward_validator.py` ROBUST/MODERATE verdicts as the kill gate — NOT raw rolling WR/PF/decay. Require minimum n (DeepSeek: n>100; Kilo: n≥30) + a statistical test (binomial / Bayesian posterior) before any kill. Stops premature death of high-variance strategies.
2. **Build an incubator pipeline.** New COMMODITY/FUTURES candidates start at **zero kill pressure**, must accrue 30+ forward-test trades in the target class, THEN graduate to live scoring. No incubator exists today — this is why every kill is permanent.
3. **Decouple `score_booster` from crypto-only gating** so COMMODITY/FUTURES/EQUITY get equivalent enrichment. The crypto-only clamp artificially widens the cross-class quality gap.
4. **THEN add the auto-spawn pipeline** — gated by per-class minimum-viable-sample so spawned candidates get a runway before the evaluator can kill them.

> Kilo: *"The auto-spawn proposal is step 4, not step 1 — stopping at step 4 yields a faster-running conveyor belt to the kill floor."*

### Why this matters for "stuck in paper trading for months"

The system has been killing strategies on **statistically-insufficient evidence** (small-n rolling windows) and calibrating its kill thresholds on **the same dead strategies' in-sample data**. This is a self-reinforcing downward ratchet: every cycle, the survivor pool shrinks, thresholds re-tune to the shrunken pool, more strategies fall below, repeat. Real-money confidence is unreachable not because edge doesn't exist but because the **evaluation machinery destroys evidence faster than it accumulates.** The fix is statistical rigor in the kill gate + an incubator runway — not more strategy births into the same meat grinder.

### M-IDs to add to master plan

- **M-055** — Re-calibrate kill thresholds: walk-forward ROBUST/MODERATE gate + min-n + binomial/Bayesian test. Owner: unassigned. First action: audit `commodity_kill_switch.py` / `fx_kill_switch.py` / `strategy_killer.py` cutoffs.
- **M-056** — Strategy incubator pipeline: zero-kill-pressure runway, 30+ forward trades before live scoring. Owner: unassigned.
- **M-057** — Decouple `score_booster` from crypto-only gating (`quality_gates.py:346-350`). Owner: unassigned.
- **M-058** — Auto-spawn replacement pipeline (gated by M-055/M-056). Owner: unassigned. **Explicitly sequenced last.**

## 2026-05-15 — Phase 2-D kill audit (full 6 symbols) + gate-bypass swarm verdict

Two more `caveman:cavecrew-investigator` subagents dispatched on the open action items. Findings below. (Peer PR #1065 "Phase 2-D kill audit — verdicts not reproducible from resolver-v2" landed independently and corroborates.)

### Phase 2-D commodity-kill audit — 3 of 5 kills are data-flawed

Recomputed each killed symbol's PRE-kill stats from `dashboard_data.json::picks.recent_closed` vs the blacklist comment's cited numbers (`quality_gates.py:1258-1264`):

| Symbol | Cited (n/WR/sum) | Recomputed PRE-kill | Verdict |
|---|---|---|---|
| GC=F (gold) | 91 / 39.6% / −0.52 | n=3 / 0.0% / −1.41 | **KILL_DATA_FLAWED** (n 91→3) |
| SI=F (silver) | 181 / 44.2% / −4.47 | n=3 / 33.3% / PF 0.06 / −3.93 | **KILL_DATA_FLAWED** (n 181→3) |
| CL=F (crude) | 6 / 16.7% / −5.25 | n=4 / 25.0% / PF 1.03 / +0.27 | KILL_DATA_VALID (inconclusive, n≤4) |
| CT=F (cotton) | 12 / 8.3% / −8.41 | n=12 / 66.7% / PF 3.50 / +32.30 | **KILL_DATA_FLAWED** (confirmed by deep-dive) |
| KC=F (coffee) | 12 / 8.3% / −6.02 | n=2 / 0.0% / −5.91 | KILL_DATA_VALID (inconclusive, n≤2) |
| agro/energy (ZC/ZS/ZW/LE/HE/BZ/HO/RB/NG) | — | NO_DATA in recent_closed | no verdict |

**Caveat:** `recent_closed` is a recent window — the cited n=91/n=181 for GC=F/SI=F may be a fuller ledger snapshot not present in `recent_closed`, OR (per the subagent) aggregate counts across all commodities. The "n 91→3" gap is therefore **suggestive, not conclusive** for GC=F/SI=F. CT=F is conclusive (n=12 matches exactly, WR 8.3%→66.7%). **Do NOT auto-unblacklist GC=F/SI=F** — that needs a full-ledger recompute, not the recent_closed window. The cotton deep-dive (`reports/deep_dive_cotton_2026-05-15.md`) is the only fully-proven case.

**Conclusion:** Phase 2-D used unreliable data at panel time (2026-04-29) — at minimum the small-n kills (CT=F, and KC=F citing the *identical* n=12/WR 8.3%) are bogus, consistent with unresolved-pick-counted-as-loss. This is exactly why **M-055 (kill-threshold re-calibration) is the P0**: a kill protocol that fires on panel-time snapshots of unresolved picks will keep mis-killing. The kill gate must read only the resolver-v2 ledger and require a min-n floor.

### Gate-bypass — swarm says don't "fix" it the obvious way

The bug report: 29 CT=F picks emitted post-blacklist. Investigator traced it — `audit_trail/dashboard_generator.py:7883-7903` loads `multi_asset_closed.json` and adds closed picks to the dashboard **without** calling `passes_active_gate()`. All 14 `COMMODITY_BLACKLIST` symbols can leak into the dashboard's closed list this way.

Asked the swarm whether to fix at (A) dashboard display filter or (B) emission gate. DeepSeek (HIGH confidence; xai+kilo failed transport) gave the correct third answer:

> **Gate at execution/sizing — NOT generation, NOT dashboard display.** Blacklisted symbols should be rejected at order placement / position sizing. Leave generation and dashboard display unchanged so the historical record stays intact for re-evaluation.

This is right: filtering CLOSED picks off the dashboard would **hide the very evidence** (cotton's real 66.7%/82.9% WR) needed to overturn a bad kill — entrenching the Phase 2-D error. The 29 CT=F picks showing in `recent_closed` is **correct behavior**, not a bug. `passes_active_gate()` is already the execution-side gate.

**Resolved action:** NO code change to `dashboard_generator.py`. Remaining real question — verify the `multi_asset_copytrader` / `multi_asset_cot` OPEN picks pass through `passes_active_gate()` before any execution/sizing step. If they do, there is no leak — only a display artifact. If they don't, fix at the sizing module (e.g. `position_sizer`/order-router), not the dashboard. Logged as a verification task, not a code edit.

### Session action-item status (rolled up)

| Item | Status |
|---|---|
| Cotton CT=F real-money claim | REVERSED — blacklisted; kill was data-flawed; verdict HOLD_KILLED_PENDING_DATA (deep-dive PR #1061) |
| Phase 2-D kill audit | DONE — peer PR #1065 + this entry; 3/5 kills data-flawed |
| Gate-bypass "bug" | RESOLVED as non-bug — display artifact; gate belongs at execution (swarm verdict) |
| M-055 kill-threshold re-calibration | OPEN P0 — the through-line of every finding this session |
| M-056/M-057/M-058 | OPEN — sequenced after M-055 |
| BOND scanner expansion beyond TLT/HYG | OPEN — only genuinely-thin class |
| FUTURES | OPEN — needs new strategies (all emitters deliberately blocked) |
| /goal skill | DONE — PR #1066 |




---

## 2026-05-15 — Operator idea: research_index broken links + per-AI pick attribution

> in parallel get the broken links within https://findtorontoevents.ca/audit/research_index.html fixed.
> e.g. for one of the runs I see a bunch of local files, likely you could find the most relevant ..
>
>     E:\findtorontoevents_antigravity.ca\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\findtorontoevents_antigravity.ca_deepdive_pr\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\swarmv2-wt\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\tmp\dailyidea-main-push\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\tmp\ghcopilot-main-20260514-1\research\asset_class\bond\run_2026-05-11T19-34-52Z
>
> I believe the purpose is to find out our performance per asset class or something like that?
> or to see our research process and swarm picks per asset class and the reason why each AI made
> a pick, and then individually we should be able to track which AI is great at guessing picks,
> for short-term vs long-term and which asset class, and what are they doing differently.

**Interpretation / action items:**
- `research_index.html` links point to absolute local Windows paths (`E:\...`) — broken on the live
  site. Fix: rewrite to repo-relative web paths (`research/asset_class/<class>/run_*/...`), or
  publish the referenced run artifacts under `/audit/research/`.
- The 5 paths above are the *same run* (`run_2026-05-11T19-34-52Z`) duplicated across 5 worktrees/
  clones — canonical copy is `research/asset_class/bond/run_2026-05-11T19-34-52Z` in the main repo.
- North-star feature: per-AI pick attribution — track which engine/persona made each pick, its
  rationale, horizon (short vs long), asset class, and realized outcome → leaderboard of
  "which AI is best at which asset class / horizon". Candidate home: extend the swarm
  pick-provenance work (M-051) + `research_index.html` as the UI surface.

---

## 2026-05-16 — Debate Swarm: PROVEN Statistical Edge Per Asset Class

**Saved at:** 2026-05-16T07:30Z
**Requested by:** operator (Claude Code session)

### Prompt (saved verbatim — for cloud agents / Kimi swarm):

> Once done create a "debate swarm" and have them debate in multiple rounds until each and every cloud model we have that is able to respond. They will debate the topic of what are the top actions we can take on our github repository and/or database / github actions jobs, backtesting protocol and other code pieces / such as strategies... what are the top priority action items that can take us from a theoretical "it might maybe work" to a "PROVEN statistical edge" per asset class. An edge strong enough that we can actually trust to spend our own REAL money on it... and we have more winners than losers, or bigger winners than losers... and a proven statistical edge.
>
> The swarm will also debate a prompt that we can provide to cloud agents, or a Kimi cloud swarm of agents etc, where they will be able to go through the prompt and provide us extreme value-add and action items where if implemented will ensure we get world-class hedge-fund level performance per asset class (or at least narrow down which asset classes are predictable and worthy to put real money into it... and look into other stuff such as DNA mutation or inverse of failing strategies, or expansion to penny stocks / meme coins / no or low-fee mutual funds etc).
>
> Run some other swarms also related to the perspectives of a hedge fund manager, and a Quant, risk manager, etc... and then review all swarm_runs output (including earlier output) and recent .MD files over the past week especially and look for action items and check each one against our code base.
>
> The swarm will review this prompt / skill along with our reports/MASTER_ACTION_PLAN_2026-05-15.md / money-maker-readyv2 along with our 90day plans etc.

### Swarm debate questions:

1. **"Proven edge" gate**: What is the minimum statistical bar (n, WR, PF, CI-lower, AC1, DSR) before we can trust real money on each asset class? Where are we today vs that bar?

2. **Pipeline integrity**: Elite systems (aggregated_picks OOS PF=7.02, kimi_signal_tracking OOS PF=15.94) absent from active_picks.json. What is the P0 fix path?

3. **Kill list vs mutation**: mutation_lab (PF=0.19), battleground (PF=0.00), alpha_engine (PF=0.67) — kill, mutate, or isolate? What does the DNA mutation protocol say?

4. **EQUITY mislabeling**: signal_validation tags crypto tokens as EQUITY. Does fixing this change EQUITY verdict from "promising" to "unproven"?

5. **COMMODITY pipeline**: multi_asset_cot n=0 in OOS dataset despite dashboard PF=4.72. Pipeline bug or dead system?

6. **Cloud agent mega-prompt**: Design a prompt that a Kimi/Gemini/GPT-5 cloud swarm can use to independently verify our edge claims and propose highest-ROI next actions.

7. **Expansion**: penny stocks, meme coins, low-fee mutual funds — which has the most accessible edge given our current tooling?

8. **Inverse/DNA mutation**: Which failing strategies have the highest potential for inversion or mutation?

### Personas for debate rounds:
- **Hedge Fund Manager**: Risk-adjusted returns, Sharpe/Sortino, MDD, institutional credibility
- **Quantitative Analyst**: Statistical rigor, multiple-testing correction, walk-forward, regime changes
- **Risk Manager**: Tail risk, correlation clustering, position sizing, circuit breakers
- **Data Engineer**: Pipeline integrity, data quality, resolver accuracy, ghost systems
- **Devil's Advocate**: Challenge every positive claim; higher bars; survivorship bias, look-ahead bias

### Reference files for swarm context:
- `reports/MASTER_ACTION_PLAN_2026-05-15.md`
- `reports/money_maker_ready_20260516T060000Z.md`
- `reports/oos_validation_2026-05-16.md`
- `reports/asset_class_90day_plan_*.md` (all 8 classes)
- `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md`
- `ASSET_CLASS_DEEP_DIVE.md`
- All `reports/asset_class_*` files

### Expected deliverables from swarm:
1. Per-class verdict: REAL MONEY READY / ACCUMULATING / BLOCKED / KILL
2. Top 10 highest-ROI code actions (with file + function targets)
3. Cloud agent mega-prompt (copy-paste ready for Kimi/Gemini/GPT)
4. Mutation candidates with specific hypothesis for each failing strategy
5. Expansion roadmap (penny/meme/mutual fund) with effort estimate


### Vetting Notes — MiniMax "ULTIMATE_PROVEN_STATISTICAL_EDGE_2026_05_16.md"

MiniMax is **directionally correct** but used the wrong dataset (55,510 live dashboard picks vs our 5,000-pick pre-registered OOS split). Their "Proven ML Combo" at 79.4% WR is actually our **kimi_signal_tracking** (76.6% WR, PF=7.7) and **aggregated_picks** (77.9% WR, PF=6.94). Full vetting: [minimax_ultimate_edge_2026-05-16_VETTED.md](reports/peer_notes/minimax_ultimate_edge_2026-05-16_VETTED.md)


### MiniMax Session 2 — EXACT_FILTERS_FOR_UI (2026-05-16, HIGH CREDIBILITY)

MiniMax read the actual KIMI codebase and all code references verified 100% accurate. Key filters confirmed in code:
- `win_probability >= 0.65` — `KIMI_FEB172026/live_scanner.py:306` ✅
- `MIN_CONFIDENCE=65, MIN_RR=2.0` — `KIMI_RISEOFTHECLAW/alpha_engine_v2.py:76-78` ✅
- `ELIMINATION_RULES: danger=25, promotion=55, champions=75` — `KIMI_FEB172026/elimination_engine.py:20-28` ✅
- 24-feature ML ranker — `KIMI_FEB172026/ml_signal_ranker.py:99-108` ✅

Full vetted doc: [EXACT_FILTERS_FOR_UI_minimax_2026-05-16.md](docs/EXACT_FILTERS_FOR_UI_minimax_2026-05-16.md)

Statistical claims (COMMODITY 89.8%, ETF 57.4%) still from dashboard not OOS — see [minimax_ultimate_edge_2026-05-16_VETTED.md](reports/peer_notes/minimax_ultimate_edge_2026-05-16_VETTED.md)


---

## 2026-05-16 — Comet Browser deep-inspect: repo audit + critical path findings

Source: Comet browser deep-inspection of https://github.com/eltonaguiar/findtorontoevents_antigravity.ca (141,651 commits). Captured for swarm prioritisation + next-sprint planning.

### What exists and is actually strong

- `antigravity_quant_engine.py` — well-architected 6-stage pipeline: StrategyEvaluator → RegimeDetector → AgreementAlpha → SignalWeightedScorer → KellySizer → FinalGate. IC-weighted signals, family deduplication, live Binance fallback.
- 5-agent ensemble with ML scoring (Spearman rho +0.33 on ml_score).
- 1,927 closed picks with decile analysis (top 20% decile: WR 60%, avg PnL +4.2%).
- 28 dedicated researcher agent reports in `CRYPTO_ML_WORLDCLASS_RESEARCH/` already audited the system; `FINAL_SYNTHESIS_REPORT.md` is the synthesis.
- `DEFINITIVE_HEDGE_FUND_PIPELINE.md`: 110 picks/week → 5-10/week plan, projected WR 41% → 85-94%.
- RegimeDetector: live 6-regime classification from BTC/ETH 4h Binance klines (STRONG_BULL / BULL / LEANING_BULL / CHOP / LEANING_BEAR / BEAR).
- AgreementAlpha: family deduplication, MIN 2 diverse models with 55% confidence floor.
- SignalWeightedScorer: 14 IC-weighted signals (bb_squeeze=10, volume_surge=8, ema_cross=7…).
- KellySizer: half-Kelly with score/regime/chop caps.

### Critical path — what is broken

| Issue | Evidence |
|---|---|
| Backtest-forward correlation = -0.91 | System is anti-predictive — higher backtest score → worse live result |
| 78.9% of trades hit SL | Stops too tight for 15m noise level |
| 96.5% of strategies fail OOS | Only 1 in 260 survives walk-forward |
| DNA live WR = 14.3% | DNA mutations generating junk |
| elite_score rho = +0.012 | Essentially zero predictive power — should be retired |
| Banned strategies (PF < 1.0) still making picks | Graveyard not enforced at generation time |
| 43 memories, 0 embeddings in agentmemory | Semantic search non-functional |
| Cost model subtracts fees on every bar, not just trade bars | All DSR computations invalid |

The 28-agent audit's Three Laws (FINAL_SYNTHESIS_REPORT.md): (1) fix signal quality first, (2) reduce transaction costs, (3) enforce existing infrastructure.

### Proposed next module: edge_concentrator.py

Target: drop between AgreementAlpha and FinalGate. Four components:

1. Rolling IC monitor — daily IC per strategy x symbol pair, Bayesian shrinkage toward zero for n<30, auto-pause if rolling 30-day IC < 0.05.
2. ATR-based dynamic TP/SL — SL = entry +/- (ATR_14 x multiplier), TP targeting_ratio by regime (STRONG_BULL 2.5, BULL 2.0, LEANING_BULL 1.8, CHOP 1.5, LEANING_BEAR 1.2, BEAR 0.8). Directly addresses 78.9% SL hit rate.
3. Symbol tier filtering — Tier 1 (always: BTC/ETH/SOL/BNB), Tier 2 (IC>0.10: XRP/ADA/AVAX/DOT/LINK/MATIC/UNI), Tier 3 (IC>0.15 + ATR check). Kill list: UNI/APT/OP until IC prove-out.
4. Regime-routed strategy allocation — CHOP: only mean-reversion (BB squeeze, RSI divergence). STRONG_BULL: only trend + breakout. BEAR: only short-biased + funding-rate extreme.

Reads from alpha_engine/data/strategy_symbol_edge_registry.json. Standard lib + numpy + pandas only. Success criterion: 110 picks → 5-10/week, 41% → 70%+ WR.

See DAILY_IDEAS_PROMPTS.MD "Comet Browser arena.ai Prompt 2026-05-16" for the full arena.ai Battle Mode prompt.

### Claude audit of Minimax edge claims (same session)

| Minimax Claim | Reality | Verdict |
|---|---|---|
| cot_positioning_CT_locked LONG WR=89.8%, n=49, PF=13.1 | COT LONG: n=3, WR=33.3%, PF=0.14; strategy not found | FABRICATED |
| COT is LONG-side edge | cot_positioning SHORT WR=62.1%/PF=1.85; cftc_cot_commercial_signal SHORT WR=56.2%/PF=2.41 | DIRECTION WRONG |
| ml_enhanced INJ/FET/DYDX/RENDER 85-100% WR | DYDX n=10 WR=100% (tiny sample); overall ml_enhanced n=261, WR=48.7%, PF=1.19 | CHERRY-PICKED |
| Confidence 0.85-0.90 WR=82%, PF=11.8 | Actual: n=12, WR=50%, PF=4.76 | 4x INFLATED |
| AuditEnsemble_LONG WR=94.7% | Recent: n=9, WR=33.3%, PF=0.99 (losing) | STALE |

Real institutional edges (recent_closed, verified): mega_mutation/macd_rsi_m048 (n=45, WR=71%, PF=4.95), baby_strats_forward/vwap_deviation_reversion_eth (n=59, WR=61%, PF=2.53), kimi_riseoftheclaw/rs-breakout-scout (n=36, WR=75%, PF=4.38), dna_winner_picks/claude_ml_moderate_mut (n=101, WR=61%, PF=2.49), COT SHORT (WR=56-62%, PF=1.85-2.41).

## 2026-05-17 — Grok 4.3 (WSL): Cross-agent daily_ideas corpus review (30+ files) + Phase 2 plan

User provided the full list of daily_ideas / DAILY_IDEAS*.MD files from main tree + worktrees + reports/ + grok_sessions/ (Grok, Cursor, Kimi, Copilot, Ollama, NVIDIA, HuggingFace, LLM Arena, synthesis, edge_per_class, etc.).

**Review outcome vs live repo state:**
- The "FUTURES =F classification fix" flagged as the next step in the 2026-05-16 handoff report was **already shipped** in that session. `audit_trail/dashboard_generator.py:_derive_asset_class` now has first-class `contract_type` support (index/rates/currency_future → FUTURES) + robust =F root logic that correctly routes COMMODITY vs FUTURES (with explicit-hint escape for our own futures emitters). FUTURES tile is now populated.
- Current per-class reality (post all 05-16 shipments): COMMODITY Tier-1 verified clean post COT dedup (PF ~2.57+), EQUITY Tier-2 (PF~1.56), ETF/CRYPTO building, FOREX in mutation, BOND/FUTURES thin but unblocked.
- Free API audit: Strong production stack (yfinance universal, Binance public, Coingecko, DefiLlama TVL/capital flows, CFTC COT, FRED partial, CME public). Gaps repeatedly called out: high-quality free earnings/PEAD data (SEC EDGAR / Nasdaq), options flow (Polygon free tier + CBOE), futures OI/roll-yield (CME direct), FX carry differentials, deeper on-chain.
- World-class gap analysis (AQR factors/carry/momentum, DE Shaw PEAD, DBMF/KMLM CTA momentum+roll, Bridgewater macro, FX carry) synthesized into concrete P1 scaffolds and backtests.

**Top recommended Phase 2 actions** (ranked by impact × verifiability from the corpus):
1. PEAD full backtest + emitter integration for EQUITY.
2. CTA/DBMF replication scaffold (`tools/research/dbmf_replication.py`) for COMMODITY sustainability.
3. FOREX carry factor scaffold + gate.
4. ETF sector rotation relative strength + macro overlay.
5. PCG-5 portfolio gate stack (shadow mode first).
6. `tools/free_data_audit.py` + close 2-3 highest-leverage free gaps above.

Full details, free API table, world-class gap matrix, and verification checklist live in the committed report:
`reports/per_asset_class_edge_phase2_free_api_audit_2026-05-16.md` (PR on `docs/phase2-per-asset-edge-free-api-2026-05-16`).

All changes keep the "75/75 quality_gates + live dashboard_generator run + per-class PF uplift" bar. Goal remains: profitable predictions with positive profit factor **per asset class** via statistical edge that beats costs.


## 2026-05-17 — Session V: /audit verdict de-contamination + canonical PF registry (PRs #1150-1152)

Strategic repo assessment found the root blocker is not strategy edge but the
**measurement layer**: the `/audit` `asset_class_health` verdict recomputes
PF/WR inside `dashboard_generator.py` with no independent cross-check, and was
systematically inflated.

Shipped:
- **PR #1150** — COMMODITY `sizing_allowed` forced `false` (headline PF 7.71 is
  the CT=F/COT leak); `PERMANENTLY_KILLED_STRATEGIES` (quan_engine family, ~70%
  of the CRYPTO ledger @ PF 0.38) excluded from the verdict aggregate.
- **PR #1151** — `build_pf_registry.py` ingests the full 32-ledger source set,
  dedups re-emissions (~41% dup rate), exposes `by_asset_class_policy_clean`;
  `reconcile_pf_registry.py` cross-checks registry vs verdict, exits 2 on
  divergence.
- **PR #1152** — both wired into the hourly `audit-dashboard.yml` pipeline.

Reconciliation result — 6/9 classes diverge. Canonical (policy-clean) PF:
COMMODITY 1.25 (tile 7.71), CRYPTO 1.24 (tile 1.33), EQUITY 0.74 (tile 1.65),
FOREX 0.36 (tile 0.85). **Every class is sub- or near-floor.** No class is
real-money ready; the registry, not the tile, is verdict-grade.

### IDEA-V1: M-067 — generator reads the registry (swarm-planned)

Make `asset_class_health` READ `pf_registry.json` instead of recomputing, so
the two cannot diverge. Planned by a 3-agent swarm (investigator: 64 consumer
refs; Plan agent: 6-task design; red-team: 10-risk register). Must-fix risks:
slippage-honesty (registry PF is gross — gross-as-verdict flips COMMODITY from
loser to winner), registry never committed, staleness detection, live-sizing
reaction to PF/n shifts. Full plan: `MASTER_ACTION_PLAN_2026-05-15.md` §25.

### IDEA-V2: external-AI roadmap convergence trap — STOP the intake

8 external-AI "real-money roadmaps" (Ernie, GLM, MiMo, Sauna, Sonnet-4.6,
ppl-sonar, Grok-4.2, ChatGPT-o3, gpt-5-search) all audited the PUBLIC dashboard
surface, not the repo, and invented the same false gaps (no execution/risk/
kill-switch/regime layer — all exist). Lesson: N AIs reading the same surface
≠ verification. Library shopping-lists (vectorbt/ccxt/Riskfolio/Prefect) miss
the point — the blocker is a corrupted ledger, not missing libraries. Stop the
roadmap-review cycle; the genuine items (White's Reality Check M-065, CIRO
M-066) are already captured.


---

## 2026-05-17 ~09:30 UTC -- External-AI Input Audit (Opus 4.7)

Reviewed **7 external-AI deliverables** this session (LMArena 5-gap audit, 4
crypto-predictor code dumps, Baidu ERNIE: 12 docx + 9 paste-ready code files).
**Verdict: integrate none.**

**Consistent failure pattern** -- external AIs have no repo access, so they
produce plausible code that does not survive contact with the codebase:
phantom file paths (risk/, ml_ops/, feature_repo/, execution_service/ -- none
exist); reinvent already-validated modules (pbo_cscv.py, deflated_sharpe.py,
position_sizing.py all exist); duplicate shipped work; assume a production HFT
execution stack the repo deliberately is NOT. One external AI fabricated a
tool-run result it could not execute.

**Standing rule:** grep the live repo before acting on any external "already
exists" / "already verified" claim. The bottleneck is repo-grounded execution,
not idea generation.


---

## 2026-05-17 ~10:45 UTC -- Money-Ready /audit tab + CI hardening (Opus 4.7)

Shipped the **Money Ready** tab on findtorontoevents.ca/audit (PR #1163):
per-asset-class money_ready_verdict (DSR + PBO/CSCV + SPA gates), refreshed
daily, with one archived snapshot per UTC day + drift vs the prior day so
improvement/degradation is monitorable.

- `tools/money_ready_snapshot.py` execs `money_ready_verdict.py --json`
  as a **subprocess** (never imports it) -- immune to a peer editing that
  module. Validates the output schema, fails loud on drift.
- Daily workflow `money-ready-snapshot.yml` (06:15 UTC).
- Design vetted by a 3-engine swarm (deepseek + xai + cerebras) -- unanimous:
  producer must subprocess, not import.
- CI: `Deploy Rise of the Claw` verify step fixed (PR #1165) -- a curl
  timeout under `bash -e` (exit 28) was failing deploys; guarded all curls
  + made the health check non-fatal. GH Actions otherwise healthy (1 real
  failure / 100 runs; the rest are by-design push-supersede cancellations).

Seed verdict 2026-05-17: MONEY_READY = COMMODITY; WATCH = CRYPTO, EQUITY, ETF.

## 2026-05-18 00:41 UTC — /audit pipeline explainer prompt (for briefing any AI)

Saved per user request. Full doc: reports/AUDIT_PIPELINE_EXPLAINER_PROMPT.md
(includes how /audit is fed — repo + GitHub Actions + MySQL ejaguiar1_stocks/
ejaguiar1_backtests — current per-asset-class status, the cotton/CT=F edge
verdict [real-looking but single-symbol-concentrated + leakage-inflated =
too risky, not a real edge], and a benchmark vs how top quants/hedge funds/
AI labs validate edge: deflated Sharpe, PBO/CSCV, White Reality Check, CPCV,
pre-registered hypotheses, economic priors, net-of-cost capacity-aware
backtests).

Use it verbatim to brief an AI before asking for per-class edge improvements.
Companion harvest already run: NO_EDGE_BRAINSTORM_CLOUD.MD.

---

## 2026-05-18 — Deep real-money-ready audit prompt (logged for later execution)

Operator request — captured as a standing idea (deferred, not yet run). Run as
a full `/money-maker-readyv2` pass when prioritized:

> Refer data-science / obsidian skills + others. Research recent .MDs that
> publish performance of active/closed picks per asset class on
> findtorontoevents.ca/audit. Find the baseline data store —
> mysql.50webs.com `ejaguiar1_stocks` + `ejaguiar1_backtests` (creds via env
> vars DB_PASS_STOCKS / DB_PASS_BACKTESTS — never hardcode/paste), plus the
> GitHub Actions jobs that feed it.
>
> 1. Pick traceability — is there a solid way to trace each pick and its
>    methodology end-to-end? Get that critiqued.
> 2. Missed-gainers check — pull "top crypto gainers by day", check if the
>    system missed them and why. Repeat per asset class.
> 3. Real-money-ready verdict — deep analysis of whether the system(s) can
>    stop backtesting and take real capital. Research the exact stats that
>    must pass (deflated Sharpe, PBO/CSCV, White Reality Check, CPCV,
>    net-of-cost capacity-aware, pre-registered hypothesis, economic prior).
> 4. If not ready (likely): how to improve per asset class. Mistakes? What
>    would a quant / hedge-fund manager say to do? What does the DB / strategy
>    pool say? Any obvious free datasets / strategies missing?
> 5. Any asset class performing worse than a coin flip where the issue is
>    findable? Any corrupt/wrong DB data where filtering one thing makes
>    profit great? Any consistent filter set (FWD WR, score, etc.) that would
>    have been reliably profitable?
>
> Cross-reference: `reports/ROADMAP_TO_EDGE_2026-05-18.md` (swarm-reviewed:
> 5–8% odds of HF-grade edge on current infra), `reports/pf_registry_*.md`
> (canonical policy-clean ledger), `reports/EQUITY_VERDICT_FINAL_2026-05-18.md`.
> Prior state: 8 harness kills, no canonical edge. The genuinely-new analysis
> not yet done = the magic-filter hunt (mine
> `pf_registry.json::by_asset_class_strategy_symbol/date` for any PF≥1.5,
> n≥30 slice) and the missed-gainers gap.

Status: PENDING. Owner: unassigned. Note for executor — the `pf_registry.json`
strategy/symbol/date views are the fastest canonical path to the filter hunt;
do NOT re-derive from raw `closed_picks.json` (unit-mismatch trap).

---

## 2026-05-18 — Reusable session-handoff & edge-harvest prompts

Operator-supplied prompts, logged for reuse in future sessions.

### Prompt A — session handoff (CHATBIBLE + summary docs)

> Once done, use the protocol in `CHATBIBLE.MD` to summarize your changes, and
> drop your chat transcript summary to a .MD, plus a .MD summarizing your
> accomplishments and future steps — for this session and for future sessions
> — especially: how can we get findtorontoevents.ca/audit to be a world-class
> prediction system across all asset classes? How many weeks / months / years
> away are we? What speeds it up — more symbols? more strategies? more
> research? more bug fixes? more DB analysis?

### Prompt B — multi-AI edge harvest

> If you have no other action items, use subagents and consult other AIs and/or
> the agent swarm. Harvest ideas on how to actually get to safe + profitable
> per asset class. Exhaust all API keys, trying every model family per key
> (use any Windows environment variable). Heavily use `grok -p` (correct cwd
> `/tmp`, `--no-alt-screen --output-format json`) for fast second opinions.
> Use subagents as needed.

### Prompt C — magic-filter hunt (recommended, not yet run)

> Mine `audit_dashboard/data/pf_registry.json` views
> `by_asset_class_strategy_symbol` / `_strategy_date` / `_strategy_policy_clean_net`
> for ANY slice with PF≥1.5 and n≥30 — a regime / symbol / time-of-day / score
> bucket / FWD-WR bucket that is consistently profitable. Conversely, find any
> corrupt-data cohort whose removal flips a class from sub-1.0 PF to positive.
> Do NOT re-derive from raw `closed_picks.json` (pnl_pct unit-mismatch trap).

### Prompt D — pick traceability audit (recommended, not yet run)

> For one pick per asset class on findtorontoevents.ca/audit, trace it
> end-to-end: which source emitted it, which gates it passed/failed, why it is
> or is not in Smart Picks / High Conviction / Money Ready. Critique whether
> the methodology is sound and reproducible. Then check "top crypto gainers by
> day" — did the system miss them, and why? Repeat per asset class.

Status: Prompts A + B executed 2026-05-18 (see reports/EDGE_HARVEST_2026-05-18.md,
CLAUDE_DESKTOP1_*_2026-05-18_0213EST.MD). Prompts C + D PENDING.

---

## 2026-05-18 — Vet the master plan + codify all /audit frontend paths

Idea / task (verbatim):

> Vet your suggested action plan: ask our other AIs extensively (ollama cloud
> models, X_AI/Grok, kimi code, DeepSeek). Run a multi-phase debate where the
> AIs double-check the plan. Give them a STRONG prerequisite so they don't have
> to dig into our database — be explicit about which DB tables / JSON files /
> filters matter.
>
> Codify / log ALL paths under findtorontoevents.ca/audit front-end — every
> "button" and every "tab": Smart Picks button vs Smart Picks tab, High
> Conviction picks button, Money Ready, all tabs/buttons. Fact-check each, and
> get the manifest auto-updated at least every 24 hours.
>
> Then double-check performance per asset class when applying each of these
> buttons, and also the "?Guide" concepts.

Plan being vetted: reports/MASTER_ENHANCEMENT_PLAN_2026_05_18.md (measurement-
first, 6-phase; no asset class money-ready; paper-only sandbox).
Status: executing 2026-05-18 — see reports/audit_frontend_manifest*, the AI
debate synthesis, and per-button per-class performance section below.

---

## 2026-05-18 — Path to Hedge-Fund Grade Performance

**User prompt (2026-05-18T08:00Z):**

> Check all .MD within the past week for enhancements or key stats per asset
> class. Determine if there is a statistical edge (even a buried one) or what
> we need to get hedge-fund level performance.
>
> Ideas to explore:
> - More symbol universe expansion
> - More aggressive strategies
> - Pool strategies from copytraders / the web and backtest ourselves
> - Check TradingView Pine scripts and backtest them ourselves
> - What is our path to truly profit and top-notch hedge fund performance?

**Current state (2026-05-18T08:00Z per money_ready_verdict()):**
- COMMODITY: MONEY_READY PF=3.67 WR=71.9% n=139 (note: CT=F 84% concentration blocks PBO)
- CRYPTO: MONEY_READY PF=2.87 WR=70.8% n=291 (DSR validation still pending)
- ETF: WATCH n=105, VIX gate enforced (VIX>=20 blocks picks)
- EQUITY: INSUFFICIENT_DATA n=31 (MySQL ghost-rows blocking, PA console action needed)
- FOREX: NOT_READY PF=0.36 WR=23.4%
- BOND/FUTURES: INSUFFICIENT_DATA

**Honest edge verdict from deep-dives (reports/DEEP_DIVE_MONEYREADY_2026-05-18.md):**
- NO strategy passes the walk-forward efficiency harness (eff>=0.30, 3/5 windows)
- Best candidate: `st_fear_greed_contrarian` n=91, PF~2.8, WR=74.7% — but ONE regime only
- COMMODITY PF=2.30 may be a leakage mirage (COT look-ahead, 38/47 picks are CT=F)
- CRYPTO confidence field had 146 rows with values in [15,78] (percent-as-integer bug)

**Path to institutional grade — prioritized:**
1. **C-2 Exchange net-flow cross-sectional spread** (CRYPTO) — best new strategy to build
   - Long 2 majors with largest exchange outflow, short 2 with largest inflow
   - Market-neutral, beta-cancelling — fixes the beta-domination defect behind all 9 harness kills
   - Cost: ~$30-200/mo CryptoQuant feed; daily bars, no tick infra needed
   - Pre-register in hypothesis_registry.json BEFORE any backtest
2. **E-1 PEAD intraday-anchored** (EQUITY) — long drift after earnings surprise, ~$30/mo Polygon
3. **C-3 Funding-settlement liquidation cascade** (CRYPTO) — free data, medium effort
4. MySQL purge (PA console ~2026-05-24) to unlock EQUITY n from 31 to ~200+
5. CT=F concentration cap enforce (COMMODITY_CTF_CAP=1) to enable PBO
6. Widen edge_stability_harness.py to read all 32 pf_registry ledger files (not just closed_picks.json)

**GitHub libraries for efficient MD/strategy indexing:**
- `vectorbt` — fast backtesting (already imported, needs wiring to production path)
- `quantstats` — tearsheet generation per strategy class
- `openbb-sdk` — free alternative data aggregator (FRED, SEC, crypto)
- `alphalens` — Quantopian-style factor analysis to validate edge persistence over time
- `ccxt` — exchange API aggregator for crypto strategies from copytraders
- `ta-lib` / `pandas-ta` — fast indicator calculation for Pine script backtest recreation

**TradingView Pine → Python backtest path:**
1. Export Pine script logic (RSI, EMA crossovers, Supertrend, etc.) to pandas-ta equivalents
2. Run on OHLCV from yfinance (free) or Polygon ($30/mo for intraday)
3. Validate on pf_registry before adding to production pick path
4. Pre-register hypothesis in hypothesis_registry.json first
5. Forward test ≥30 picks before wiring to production

---

## 2026-05-18 — Quickest Path to Profitable Picks: Framework + MySQL Audit Table + New Symbols

**Session:** Synthesized from CORRECTED_GAMEPLAN_2026-05-18.md, daily_ideas_edge_sweep_2026_05_17.md, SUPREME_PLAN_90days.md, money-maker-action-plan, live pf_registry.json + money_ready_verdict.py output.

---

### LIVE STATUS (2026-05-18T19:46Z)

| Class | n (policy_clean_net) | WR | PF | money_ready_verdict |
|---|---|---|---|---|
| COMMODITY | 51 | 56.9% | 1.67 | MONEY_READY (whitelist n=143, WR=69.9%, PF=3.14) |
| CRYPTO | 2,083 | 44.2% | 1.16 | MONEY_READY (whitelist n=291, WR=70.8%, PF=2.87) |
| EQUITY | 37 | 45.9% | 1.28 | INSUFFICIENT_DATA |
| FOREX | 295 | 12.5% | 0.17 | NOT_READY (hard-disabled) |
| FUTURES | 12 | 16.7% | 0.96 | INSUFFICIENT_DATA |
| ETF | 0 (pf_registry sync gap) | — | — | INSUFFICIENT_DATA |
| BOND | 1 | 0% | 0.00 | INSUFFICIENT_DATA |

**Critical discrepancy to investigate:** `money_ready_verdict` shows CRYPTO WR=70.8%/PF=2.87 but `pf_registry::by_asset_class_policy_clean_net` shows WR=44.2%/PF=1.16 on the full 2,083-pick universe. The verdict is computed on a whitelist subset. The true edge is narrower than the dashboard implies. Always cross-check both sources.

---

### FRAMEWORK: Three Axes to Profitable Picks

#### Axis 1 — Kill the Bleeders (zero new code, immediate PF lift)

Run this to find current drag candidates:
```bash
python -c "
import json
d = json.load(open('audit_dashboard/data/pf_registry.json', encoding='utf-8'))
rows = [r for r in d['by_asset_class_strategy_policy_clean_net'] if r.get('n',0)>=20 and r.get('profit_factor') is not None and r['profit_factor'] < 1.2]
for r in sorted(rows, key=lambda x: x['profit_factor']):
    print(f\"{r['asset_class']} | {r['strategy']} | n={r['n']} PF={r['profit_factor']:.2f}\")
"
```

Candidates already identified (must add to `BLOCKED_ASSET_STRATEGY_PAIRS` in quality_gates.py after mutation-axes review per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`):
- `st_fear_greed_contrarian` (CRYPTO): n=139, PF=0.88
- `multi_period_rsi_confluence_eth` (CRYPTO): n=26, PF=1.11
- `atr_percentile_gate` (CRYPTO): n=29, PF=1.10

Each block raises the effective CRYPTO aggregate PF. Run mutation analysis before killing: `python tools/mutation_analysis.py`.

#### Axis 2 — Expand Proven Winners to New Symbols

**CRYPTO proven strategies to expand (top by PF, n>=20, from live pf_registry 2026-05-18):**

| Strategy | Current Symbol | n | WR | PF | Expansion Candidates |
|---|---|---|---|---|---|
| ml_enhanced_*_15m_D_ensemble_stack | DYDXUSDT | 31 | 96.8% | 53.44 | GMXUSDT, PERPUSDT (perp DEX same regime) |
| ml_enhanced_*_1d_B_lightgbm | INJUSDT | 28 | 96.4% | 40.98 | SEIUSDT, TIAUSDT (L1 same cohort) |
| ml_enhanced_*_1d_B_lightgbm | FETUSDT | 44 | 56.8% | 9.25 | AGIXUSDT, OCEANUSDT (AI-token cohort) |
| ml_enhanced_*_1h_D_ensemble_stack | RENDERUSDT | 47 | 61.7% | 3.80 | AKASHUSDT, IOTAUSDT |
| mega_mutation | CRYPTO (broad) | 72 | 56.9% | 2.19 | Already multi-symbol; expand to 50 coins |

**COMMODITY — fastest path from PF=1.67 to n>=100 (currently one strategy: `multi_asset_copytrader`):**

CT=F (cotton) has 84.9% concentration. Add these 4 symbols to the COMMODITY scanner universe via `multi_asset/cot_pipeline.py` (CFTC Socrata already wired):
- GC=F (gold): CFTC COT commercial net positions — documented 12-18mo predictive power
- SI=F (silver): correlated to GC=F, smaller sizing
- CL=F (crude oil): Baker Hughes rig count + OPEC supply calendar as co-signal
- ZS=F (soybeans): USDA WASDE crop report cadence as natural signal timing

#### Axis 3 — MySQL Daily Pick Audit Table (DOES NOT EXIST — build this next)

**Current state:** `schema-baseline.sql` has `at_incubator_strategies.rejection_reasons` (strategy-level). No table tracks why individual picks were rejected each day, or whether rejected picks would have been profitable.

**Proposed schema:**
```sql
CREATE TABLE daily_pick_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  audit_date DATE NOT NULL,
  symbol VARCHAR(30) NOT NULL,
  strategy VARCHAR(100) NOT NULL,
  asset_class VARCHAR(30) NOT NULL,
  gate_that_fired VARCHAR(80) NOT NULL,
  rejection_reason TEXT,
  score DECIMAL(8,4) DEFAULT NULL,
  confidence DECIMAL(6,4) DEFAULT NULL,
  would_have_closed_profitable TINYINT DEFAULT NULL,
  hypothetical_pnl_pct DECIMAL(10,4) DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_dpa_date_class (audit_date, asset_class),
  KEY idx_dpa_gate (gate_that_fired),
  KEY idx_dpa_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Wire-up:** in `audit_trail/quality_gates.py::passes_active_gate()`, after each `return False, reason`, INSERT one row. Backfill `would_have_closed_profitable` nightly by joining against `closed_picks` on `(symbol, strategy, audit_date)`.

**Queries this unlocks:**
1. Which gate fires most on ETF picks? — `SELECT gate_that_fired, COUNT(*) FROM daily_pick_audit WHERE asset_class='ETF' GROUP BY 1 ORDER BY 2 DESC`
2. Are we over-filtering? — `SELECT AVG(would_have_closed_profitable) FROM daily_pick_audit WHERE would_have_closed_profitable IS NOT NULL` — if >50%, gates are too aggressive
3. Opportunity cost of any gate — filter by `gate_that_fired='<gate_name>'`

---

### ETF: The Most Underserved Candidate

MySQL `by_asset_class` raw shows ETF closed=85, wins=50, WR=61.0%, PF=2.00. But `pf_registry::by_asset_class_policy_clean_net` shows ETF n=0. This is a sync gap, not a real lack of edge. Walk-forward profile: OOS WR=75%, fold consistency=100%, +23% improving trend — the best OOS of all classes.

**Fastest fix:** check `.github/workflows/mysql-trading-sync.yml` scope — does it include ETF? Run `gh run list --workflow=mysql-trading-sync.yml --limit 5`. If the sync is missing ETF, add it and ETF may immediately show PF>=2.0 in pf_registry.

**New ETF symbols:** XLF, XLE, XLK, XLV, XLI (SPDRs with 15+ years history). Signal: relative-strength rank across 11 SPDRs, monthly rebalance. Candidate file: `alpha_engine/etf_rotation_strategy.py`.

---

### Best AI Prompt (use as session-opener)

> "Read `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net` and run `python alpha_engine/money_ready_verdict.py`. Compare them — if money_ready_verdict shows PF>1.5 for a class but pf_registry shows PF<1.2 for the same class, identify which strategies are in the whitelist but not the full universe. Then: (1) block any strategy with n>=20 and PF<1.0 using BLOCKED_ASSET_STRATEGY_PAIRS after mutation-axes review; (2) identify 2-3 new symbols for the top-performing strategies and spec a PR; (3) check if daily_pick_audit table exists in schema-baseline.sql and if not, create it and wire into passes_active_gate(). Always cross-check PF numbers against pf_registry before claiming any class is MONEY_READY."

---

### Open Action Items

| Priority | Action | Class | Effort | Blocker |
|---|---|---|---|---|
| P0 | Investigate ETF pf_registry sync gap (MySQL WR=61%/PF=2.0 vs pf_registry n=0) | ETF | XS | None |
| P0 | Fix MySQL silent-fail: `mysql-trading-sync.yml` line 43 `\|\| echo "non-fatal"` | Infra | XS | None |
| P1 | Block `st_fear_greed_contrarian` (CRYPTO, n=139, PF=0.88) after mutation review | CRYPTO | S | Mutation review |
| P1 | Add GC=F/SI=F/CL=F/ZS=F to COMMODITY scanner universe | COMMODITY | M | COT feed check |
| P1 | Design + wire `daily_pick_audit` MySQL table | Infra | M | PA console DB access |
| P2 | Expand ml_enhanced to GMXUSDT/PERPUSDT (DYDX-cohort) | CRYPTO | M | Model retrain |
| P2 | Wire FRED_API_KEY secret → BOND scanner (n=1 → target n=20) | BOND | S | FRED_API_KEY secret |

NFA — all picks are research surface. No real-money sizing without DSR>=0.95, PBO<0.10, n>=100 clean trades, and drift_alert=FALSE on that class.

---

## 2026-05-18 — Session CT Corrections + Refined Profitability Prompt

### ETF Root Cause Correction

**Previous entry was wrong:** The ETF n=0 in pf_registry is NOT a mysql-trading-sync.yml scope gap.

Investigation (2026-05-18T20:30Z):
- `alpha_engine/data/active_picks_etf.json`: 14 ETF picks
- `alpha_engine/data/etf_sector_picks.json`: 19 ETF picks
- `alpha_engine/data/scanner_output/active_picks_etf.json`: 11 ETF picks
- All 21 `closed_picks.json` files: **0 ETF picks**

**Real root cause:** ETF picks are being generated but never closing (resolved to closed). The outcome_resolver isn't processing ETF picks — likely because ETF picks lack TP/SL price levels or expiry timestamps, so the resolver never fires a close event. Fix: inspect ETF pick schema vs non-ETF picks; add TP/SL/expiry to ETF pick generators.

**Impact:** Until this is fixed, ETF will always show n=0 in pf_registry regardless of how many active picks are generated.

### Gate Changes This Session (2026-05-18 Session CT)

- **M-109 RR gate ENFORCED** (commit `6e6c4d9f63`): `RR_HIGH_GATE_ENFORCE=1` is now the default. ~15% of open picks with risk_reward > 1.5 are hard-rejected. EV math: RR=1.5-2.0 → EV = -0.228 per unit. Kill-switch: `RR_HIGH_GATE_ENABLED=0`.
- **Gate 2 (ML_ENHANCED_CRYPTO_QUARANTINE)**: DEFERRED — 112 surviving ml_enhanced variants need individual audit before bulk quarantine.
- **Gate 3 (MDD_GATE_ENFORCE)**: REJECTED — sequential equity-curve MDD is wrong methodology for a diversified system. Redesign as rolling 30d or portfolio-level MDD.
- **futures_momentum**: Zero-sizing monitor mode maintained. 4/4 swarm said block; operator kept in monitor for regime-stratified data collection until 2026-07-18.

### Refined Optimal AI Prompt (Session CT)

Copy-paste prompt for any AI agent to get the fastest path to profitable picks per asset class:

```
You are a quant trading analyst for findtorontoevents_antigravity.ca (repo: eltonaguiar/findtorontoevents_antigravity.ca).

ORIENT (read in this order):
1. `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` — current WR/PF/n per class
2. `audit_dashboard/data/pf_registry.json::canonical_view` (or by_asset_class_policy_clean_net) — canonical universe PF
3. `alpha_engine/data/strategy_performance.json` — per-strategy n/WR/PF

KEY NUMBERS (2026-05-18):
- CRYPTO: n=2,083 WR=44.2% PF=1.155 (canonical) — biggest drag: st_fear_greed_contrarian (n=139, PF=0.88)
- COMMODITY: n=51 WR=56.9% PF=1.673 — good but 84.9% CT=F concentration (add GC=F/SI=F/CL=F/ZS=F)
- EQUITY: n=37 WR=45.9% PF=1.277 — thin sample; MySQL purge needed (~2026-05-24)
- FOREX: n=295 WR=12.5% PF=0.174 — hard-disabled; raw PF=3.177 suggests non-JPY SHORT edge may be collateral damage
- ETF: n=0 — picks generated but NOT resolving (outcome_resolver doesn't close ETF picks — missing TP/SL)
- BOND: n=0 — FRED_API_KEY not wired; bond scanner runs but no resolved trades
- FUTURES: n=12 WR=16.7% PF=0.96 — zero-sizing monitor mode until 2026-07-18

THREE AXES:
Axis 1 (KILL): Block st_fear_greed_contrarian CRYPTO (n=139, PF=0.88) after mutation-axes review.
  Run: python tools/mutation_analysis.py --strategy st_fear_greed_contrarian
  If no axis rescues it: add ("CRYPTO", "st_fear_greed_contrarian") to BLOCKED_ASSET_STRATEGY_PAIRS in audit_trail/quality_gates.py.

Axis 2 (EXPAND): COMMODITY — add GC=F/SI=F/CL=F/ZS=F to multi_asset/cot_pipeline.py (CFTC Socrata already wired).
  CRYPTO — expand ml_enhanced_*_1d_B_lightgbm from INJUSDT (PF=41, n=28) to SEIUSDT/TIAUSDT.

Axis 3 (BUILD): Fix ETF outcome_resolver — inspect why ETF closed_picks.json is always empty.
  Check: alpha_engine/outcome_resolver.py — does it filter by asset_class? Does ETF emit TP/SL?
  Target: get n>=30 ETF resolved picks to validate WR=61%/PF=2.00 from MySQL historical data.

NEVER do: size real capital (pf_registry PF<1.5 on canonical universe), ignore pf_registry in favor of money_ready_verdict whitelist, run dashboard_generator.py locally (auto-generated).

QUALITY GATE: Before claiming any class is MONEY_READY, verify:
  python -c "from alpha_engine.money_ready_verdict import money_ready_verdict; print(money_ready_verdict('CRYPTO'))"
  Then cross-check with pf_registry canonical n and PF.
```


---

## 2026-05-19 — Quant rescue prompt (operator, for swarm/AI consultation)

Operator-supplied prompt for consulting AIs on diagnosing a failing prediction system.

> You are a quant assigned to fix a failing company who tried to predict
> stocks/crypto/forex/bonds/commodities/etfs/futures.. and is not profitable..
> and definitely doesnt have more or more profitable winners than losers.
>
> What stats do you run? What methodology do you run through their GitHub
> Actions, MySQL database?

Status: used 2026-05-19 — responses from Mercury 2 + Grok harvested + reviewed
(see reports/QUANT_RESCUE_REVIEW_2026-05-19.md). Reusable for future AI consults.


---

## 2026-05-19 — Full System Audit Prompt (Lopez de Prado level)

Source: User-supplied AI consultation prompts for cracking the edge problem.
All 4 prompts below submitted to agent swarm 2026-05-19.

### Context (from audit snapshot)
- Overall (55k+ closed picks): 11.13% WR, −3.56% avg return, Sharpe −2.34, PF 0.46
- EQUITY: best performer (recent PF ~1.55, WR 51%, n=426). T2 candidate.
- COMMODITY (CT=F COT): headline PF 2.48 but recent decay + data artifacts.
- CRYPTO: 46% WR, PF <1.3; inverted confidence (high ML_score = worse WR).
- FOREX/ETF/BOND: Sub-floor or tiny n.
- Core problems: lookahead leakage, inverted confidence, strategy decay, sparse forward-testing, no CPCV/DSR/PBO/MinTRL gates in GHA.

### Prompt 1 – Full System Audit (Claude Opus)
```
You are a world-class quant researcher (Lopez de Prado level).
Audit this entire repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
Focus ONLY on the prediction pipeline (alpha_engine, feature_store, data_pipeline, backtest_results, audit_trail).
Identify every source of lookahead bias, survivorship bias, data leakage, inverted confidence, and strategy decay.
Then propose concrete fixes + new validation gates (WFE, CPCV, DSR, PBO, MinTRL).
Output in this exact format:
1. Leakage inventory (file + line)
2. Confidence recalibration plan
3. New readiness gates to add to GitHub Actions
4. One new strategy skeleton per asset class that would pass the new gates
```

### Prompt 2 – Strategy Regeneration (Ring-2.6-1T or GLM-5.1)
```
Act as a senior quant PM.
We have poor forward WR and inverted confidence across asset classes.
Using only the data schema from database/ and the current feature_store, generate 3 new high-conviction strategy ideas (one each for EQUITY, CRYPTO, COMMODITY) that explicitly avoid the failures in failed_strategies/.
For each idea provide:
- Entry/exit rules
- Feature list (no lookahead)
- Walk-forward test plan
- Expected statistical edge (Sharpe target, MinTRL)
```

### Prompt 3 – Confidence & Scoring Fix (MiMo or Claude)
```
Our ml_score is inverted (high score → low WR).
Fix the scoring booster in alpha_engine/config.py and audit_trail/quality_gates.py so that confidence becomes monotonic with forward performance.
Propose a new hybrid score (ml_score × regime_factor × freshness) and show the math.
```

### Prompt 4 – GitHub Actions Upgrade
```
Add automated gates to .github/workflows/audit-dashboard.yml:
- Run full CPCV + DSR + PBO on every new pick batch
- Auto-quarantine any strategy with forward WR <48% or PF <1.2
- Alert on confidence inversion
Output the complete updated workflow YAML.
```

### Bounce-Back Plan (7–14 day execution order)
1. **Kill multi-asset mixing** — freeze to EQUITY only (strongest cohort: WR 51%, PF 1.55)
2. **Add LDP gates** — CPCV, DSR>0.95, PBO<0.05, MinTRL<90d, WFE>60% in GHA
3. **Rebuild confidence** — monotonic hybrid: 0.55×ml + 0.25×regime + 0.15×freshness + 0.05×fwd_wr_30
4. **Paper-pilot 4 weeks** — top 3 EQUITY strategies through new gates, 30-50 closed picks
5. **External model review** — Claude Opus 4.7 Max or GLM-5.1 with top 5 failing strategies + backtest CSV

### Model Priority for IDE Agents
| Priority | Model | Strength | Prompt Focus |
|----------|-------|----------|--------------|
| 1 | Claude Opus 4.6/4.7 | Lowest hallucination on quant pipelines | Strategy audit + LDP gate implementation |
| 2 | GLM-5.1 (Zhipu) | Leakage & decay detection | Feature-store + backtest hygiene |
| 3 | Ring-2.6-1T (inclusionAI) | Multi-step planning | Strategy generation + walk-forward redesign |
| 4 | MiMo-V2.5-Pro (Xiaomi) | Fast iteration | Confidence recalibration experiments |

### Grok Feedback (2026-05-19) — Validity Verdict
Grok proposed 4 code changes; swarm validation in progress (see reports/audit_swarm_2026-05-19.md):
- `lopez_de_prado_gates()`: DSR formula appears SIMPLIFIED (real LDP DSR accounts for trials/non-normality). PBO=1-WR² is not the standard formula. Flag for swarm review.
- `hybrid_score(... forward_wr_30)`: using 30-day FORWARD WR in a live scoring function = lookahead bias if `forward_wr_30` is future data. Valid concept if `forward_wr_30` = trailing 30d historical.
- `equity_momentum_regime_signal()`: `df['close'].pct_change(252).std()` on full DataFrame = lookahead. Needs to be rolling or computed on strictly past data.
- Hybrid score weights (0.55/0.25/0.15/0.05): reasonable starting point but unvalidated.

### CPCV / DSR — Definitions
- **CPCV (Combinatorial Purged Cross-Validation)**: Lopez de Prado 2018. Generates multiple test paths by combinatorially splitting the data timeline, with purging to prevent leakage between train/test. Avoids path-dependency of standard k-fold.
- **DSR (Deflated Sharpe Ratio)**: Sharpe corrected for selection bias (number of trials, non-normality, skewness). DSR = SR × (1 - γ × ln(N_trials)) approximately. Rejects results that pass only by overfitting.
- **PBO (Probability of Backtest Overfitting)**: From CPCV. Fraction of test paths where the best in-sample strategy performs below median out-of-sample. PBO > 0.5 = strategy is likely overfit.
- **MinTRL (Minimum Track Record Length)**: How long a strategy needs to live to achieve SR confidence above a target at given significance.
- **WFE (Walk-Forward Efficiency)**: OOS Sharpe / IS Sharpe. Below 60% suggests overfitting.

Status: swarm analysis in progress — see reports/audit_swarm_2026-05-19.md for results

### Swarm Audit Results (2026-05-19) — Final Verdicts
Swarm completed (agent a85d3551), report at reports/audit_swarm_2026-05-19.md:
- **Grok DSR**: OVERSIMPLIFIED — missing N (trials), skewness/kurtosis, T scaling. Our existing statistical_gates.py has the correct implementation.
- **Grok PBO**: FLAWED — `1-WR²` has no theoretical basis; real PBO needs CPCV rank comparison. Even Grok's v3 "PBO proxy" using forward_wr is not real PBO.
- **Grok forward_wr_30 in hybrid score**: CRITICAL LOOKAHEAD — future WR as scoring input invalidates all backtest results.
- **Grok regime global std()**: LOOKAHEAD — fixed with `rolling(252).std().shift(1)` benchmark.
- **Confidence inversion root cause**: Label leakage #1 (ml_score negatively correlated with forward returns = textbook diagnostic), overfit #2, regime change #3.
- **Best action for 0/14 gate passes**: Ensemble of weak signals first (variance reduces √14 = 3.7×), then intraday data if still failing (14-day window with daily data = only 14 observations; with 5-min = ~1,092).

### Equity Validation Results (2026-05-19)
Script: alpha_engine/validation/run_equity_edge_test.py (uses correct LdP DSR, not Grok's formula)
Output:
  n=69 EQUITY resolved picks (from 87 found, 9953 total pool)
  WR=46.4% (32W/37L), Mean PnL=+0.41%, PF=1.23, SR=1.487
  DSR: PASS (probability=1.000, E[maxSR|50trials]=~0)
  Newey-West t-stat: FAIL (t=0.578, p=0.563 — not significant)
  VERDICT: NOT YET PROVEN — n=69 below 100 threshold, NW fails
Primary blocker: need n≥100 resolved EQUITY picks for reliable inference.

### Grok Rounds 4-8 (2026-05-19) — Persistent Errors + What Changed
Round 4 (v2 "final corrected"): DSR still wrong (`sr * norm.cdf(...)`) — acknowledged by Grok in round 7.
Round 5 (validation script): Same DSR bug, new format. PBO still `1-forward_wr**2`.
Round 6 (swarm feedback): Meta-advice on swarm prompt design; no new code.
Round 7 (acknowledging DSR error): Grok admits `sr * norm.cdf(...)` was wrong. Provides correct formula.
Round 8 ("what prompt would prevent this"): Grok proposes ideal prompt format. Reasonable lesson.
PBO: STILL NOT FIXED across all rounds — `1 - mean_forward_wr**2` persists.

Correct DSR (verified in statistical_gates.py line 239): `norm_cdf((SR - E[maxSR]) / sr_std)` — no `sr *` prefix.
Real PBO requires CPCV (Bailey et al. 2016) — not achievable with just WR data.
Our purged_cv.py has PurgedKFoldCV (purge_days=5, embargo_days=5) — can be extended to CPCV.

### New Deliverables (2026-05-19 session)
- alpha_engine/validation/run_equity_edge_test.py — correct DSR (uses statistical_gates.py), NW t-stat, real data
- alpha_engine/strategies/equity_momentum_regime.py — point-in-time regime signal (rolling vol + shift(1))
- docs/STRATEGY_PERFORMANCE_BLUEPRINT.md — where to find strategies/performance in repo + DB
- reports/audit_swarm_2026-05-19.md — full swarm verdicts on Grok feedback + 4 audit prompts
- tools/h035_funding_settlement_pressure.py — H-035 TESTED_KILL (sign-flip)
- tools/mysql_dedup_fix.py + .github/workflows/mysql_dedup_fix.yml — dedup fix via GHA (IP-restricted)
- audit_trail/quality_gates.py — _normalize_confidence extended (val>10 → /100)

---

## 2026-05-19 — AI Prediction Tournament + Stealth Browser Council

### IDEA-AI-TOURNAMENT: AI Model Prediction Tournament

**Summary:** Pit every cloud AI model family we have API access to against live financial markets. Each model chooses its own symbol universe, generates a production-grade trading strategy per asset class, and produces forward-test picks tracked live.

**Core concept:**
- Models compete against each other AND against our own validated strategies in the audit dashboard
- Forward-test picks tracked live via GitHub Actions daily price pulls
- Hallucination checks: any backtest claim independently reproduced using real OHLC data
- Page: findtorontoevents.ca/audit/ai-tournament

**Model matrix (Phase 1 — cloud):**
Mercury (inception-labs), Cerebras (llama-4-scout), Ring-2.6-1T, Grok-3, DeepSeek-R1, GPT-4o, Claude Opus, Gemini 2.5 Pro, GLM-4 (OFOX), Qwen3-235B, Mistral Large, Command R+

**Phase 2 (future):** Local models via Ollama (gemma3:1b, llama3.2:1b, qwen2.5:1.5b, etc.)

**Methodology:** `docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md`
**Swarm review:** `reports/ai_tournament_methodology_swarm_review_20260519.md` — all 3 engines NEEDS_WORK, key fixes adopted:
- Pre-registered symbol universe (not free-choice)
- Min n=30 per class before ranking
- CI-based scoring: `Score = lower95(WR) × lower95(PF)`
- Trade-level submission required; exact binomial test on WR claims
- Closing price at expiry (not mid-price); slippage: 5-10bps equity, 0.2% crypto
- Pin model versions at tournament start
- FOREX window: 21 days (not 10)
- Min RR ≥ 1.5; SL ≤ 2×TP enforced at submission

**No-shortcuts prompt:** `/noshortcutsprompt` skill created at `.claude/skills/noshortcutsprompt/SKILL.md`

**Pre-registered universe (v1.0):**
- EQUITY: S&P 500 constituents
- CRYPTO: Top 30 by market cap (CoinMarketCap)
- FOREX: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF
- COMMODITY: XAUUSD, XAGUSD, CL=F, NG=F, HG=F
- BOND: US10Y, US30Y
- ETF: SPY, QQQ, IWM, EEM, GLD

**Data integrity flags:**
- 🟢 FORWARD_TEST — live market, post-tournament-start
- 🟡 BACKTEST_VERIFIED — independently reproduced
- 🔴 BACKTEST_DISPUTED — not reproducible within ±10%
- ⚫ HALLUCINATION_CONFIRMED — fabricated data + -1 pick penalty

---

### IDEA-STEALTH-BROWSER: Anonymous Multi-AI Council via Stealth Browsing

**Summary:** Use stealth/anti-detect browser automation + rotating proxies to query free/guest-accessible AI web interfaces anonymously — building a "council of AIs" without API keys, accounts, or static IP exposure.

**Why:** Many AIs are accessible without sign-in (Grok, Meta AI, Perplexity, You.com, HuggingChat, Poe, DuckDuckGo AI Chat). This gives access to additional model opinions for zero marginal API cost.

**Target interfaces (no/minimal sign-in):**
- grok.com / grok.x.ai — no X account required (web)
- meta.ai — Llama guest access
- perplexity.ai — guest mode (rate-limited)
- you.com/chat — YouChat guest access
- poe.com — daily free messages, many models
- huggingface.co/chat — optional login, open models
- duckduckgo.com/chat — free GPT-4o mini, Llama 3, Mixtral (strips IP)
- felo.ai — multilingual AI search, no login

**Stealth frameworks:**
- **CloakBrowser** (CloakHQ/CloakBrowser) — source-level Chromium fingerprint patches, passes 30/30 bot tests, same API as Playwright (`pip install cloakbrowser`)
- **Camoufox** (daijro/camoufox) — Firefox alternative, different engine fingerprint
- **Stealth-Browser MCP** (vibheksoni/stealth-browser-mcp) — wraps into MCP server for Claude agent use
- **Nodriver** — avoids CDP signatures entirely

**Proxy strategy:**
- Start with Tor (`socks5://127.0.0.1:9050`) for free but slower
- ProxyBroker for rotating free proxy pool
- Residential proxies (IPRoyal/Bright Data) for production reliability
- CloakBrowser supports: `launch(proxy="http://user:pw@gate:8000", geoip=True)` — auto-adjusts timezone/locale to match proxy IP

**POC architecture:**
1. Python + CloakBrowser + proxy rotator
2. Per query: pick random proxy → fresh browser context → navigate to target → type prompt → extract response → close context
3. Fan same prompt to 3-5 targets in parallel (different proxies)
4. Collect labeled responses → feed into swarm synthesis pipeline

**Integration with our system:**
- Could replace expensive API calls for exploratory research questions
- Could provide "anonymous second opinions" from proprietary models (Grok, GPT) without API costs
- Could be used to gather AI opinions on stocks/picks without leaving a footprint
- Feed into `tools/swarm/swarm_run.py` as a new engine type: `--engines stealthweb`

**POC script:** `tools/stealth_browser_poc/` (skeleton to be created)
**Priority:** Medium — start after AI Tournament Phase 1B (model prompting round) completes

---

## 2026-05-19 — Anonymous AI council prompt (saved per user request)

### PROMPT: Institutional Stock Prediction Pipeline Code Harvest

Saved from the consult-webscrape proof-of-concept session. Use this prompt with the 6 known-working anonymous sources (especially eye2.ai which returns actual Python code).

```
Write production-grade Python code for ONE institutional-quality stock prediction pipeline. Requirements: (1) pull market data, (2) feature engineering, (3) proper train/validation split for time series, (4) model training, (5) backtest function, (6) risk controls, (7) clear runnable script structure, (8) no placeholders. Return full source code only
```

**Working sources for this prompt:**
- `eye2.ai` — returns real Python code with TimeSeriesSplit, RandomForest, proper feature engineering
- `chatgot.io` — returns class-based template (some scraper truncation)

**How to run:**
```bash
python tools/anon_ai_council/deep_probe_from_manifest.py \
  --input swarm_runs/source_manifest_probe_2026-05-19.json \
  --output swarm_runs/deep_probe_code_harvest_$(date -u +%Y%m%d).json \
  --limit 20 --timeout 22
```

**Context:** GitHub Copilot built the `tools/anon_ai_council/` skill; Claude Code completed the benchmark (6/102 anonymous sources work). Reports: `updates/2026-05-19-anonymous-ai-council-*.md`.

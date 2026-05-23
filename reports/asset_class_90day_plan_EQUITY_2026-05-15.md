# Asset Class 90-Day Plan — EQUITY — 2026-05-15

**Senior Quant Audit** using `money-maker-continual-improve` skill (7-step process).  
**Focus**: EQUITY crossed T2 threshold (PF 1.57 / WR 51.9% / n=420) but narrow speculative universe (18 tickers heavy on pennies/memes), limited fundamentals via yfinance wrapper (no primary SEC), strong hidden VIX regime edge in research not wired to prod, backtest/live gaps. Prioritize clean large-cap + regime filter before any sizing expansion. Not system pilot (COMMODITY CT=F leads PF 2.49 / WR 61.5% n=322).  
**Data sources**: `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:28Z), `reports/MASTER_ACTION_PLAN_2026-05-15.md`, `alpha_engine/config.py` (EQUITY_SYMBOLS + CATEGORY_RISK), `alpha_engine/equity_strategies.py`, `alpha_engine/equity_factor_model.py`, `alpha_engine/non_crypto_quality_gate.py`, `alpha_engine/scanner.py`, `reports/asset_class_research_EQUITY_2026_05_12_0438Z.md`, `reports/equity_vix_regime_breakthrough_20260513.md` + `equity_momentum_vix_regime_backtest.json`, `reports/equity_yc_regime_breakthrough_20260513.md`, `reports/equity_vix_yc_combined_super_breakthrough_20260513.md`, `reports/fix_EQUITY_20260505T005402Z.md`, `reports/audit_asset_feedback_2026-05-05T0121Z_EQUITY.md`, `reports/asset_class_research_EQUITY_2026_05_12_0438Z.md`, local git branches (`feat/equity-vix-regime-gate-sidecar-2026-05-13`), `audit_dashboard/data/equity_top*.json`, `audit_dashboard/data/db_health.json`, `reports/daily_ideas_synthesis_2026-05-15.md`.

**Current Charter context** (from CLAUDE.md / master plan / dashboard): EQUITY T2-candidate (May-3 snapshot PF 1.41 / WR 52.7 / n=421; today improved PF 1.57 / WR 51.9 / n=420 resolved, total_pnl +385.5%, sizing_allowed=true, stable). by_asset_class shows closed ~1050. Concentration OK: top_symbol AMD 11.65% PnL mass, top_strategy "Classic Momentum" 10.96%. Master plan flags "NEEDS-EVIDENCE-FIRST" for 2026-05-25 institutional (real T2 but require 30d clean rolling + MATCH on verify_system_pf before sizing; repeats claude_gainer_st pattern). Pending: M-009 (PEAD on top-100), M-025 (overnight_intraday_reversal EQUITY), M-026 (day-of-week Tue/Wed tilt). VIX regime sidecar branch exists but not merged/wired. Penny-stock kimi-EQUITY hallucinated names noted in drop list. Hermes unblocked some zero-evidence equities.

---

## Step 1: Establish Brutal Baseline (EQUITY)

**Live performance** (`dashboard_data.json::performance.asset_class_health.EQUITY` + `by_asset_class.EQUITY` + `asset_class_concentration.EQUITY`):

- Resolved n=420 (resolved_n=420), active 65; closed ~1050 in by_asset (discrepancy suggests noise-filter or different cohorts post-resolver-v2).
- WR: 51.9% (by_asset: 218 wins / 202 losses on closed?); expectancy +0.92.
- PF: 1.57 (by_asset_class), total_pnl_pct +385.5. Meets T2 floor (PF>1.5 / WR>50) with n=420 >100 stable.
- Concentration: OK tier (no warn/block). Top symbol: AMD (11.65% PnL mass, 202.4), top_strategy: "Classic Momentum" (10.96% share, 190.55 PnL mass). honest_label: "EQUITY edge = Classic Momentum on AMD (12% of class PnL)".
- Circuit breaker: cold_start (n=0<30 realized_30d), no breach. sizing_allowed=true.
- Older (May-3 master): PF 1.41 / WR 52.7 / n=421; May-5 audit feedback: PF 1.41/52.8 n=428 "candidate, not proven Tier 2", alpha_engine PF1.23 MDD194% heavy on INJUSDT (misclassified?).
- Research backtests (May-13): baseline 12-1 momentum top-5 on 30 LC universe: n=122 periods, WR 64.75%, PF 2.82, Sharpe 1.34, MDD 24.19%, +1516% (2015-2026). But live on narrow 18-ticker mix much lower.

**Symbol universe coverage and quality (large-cap vs mid vs penny/meme)**:

- Defined in `alpha_engine/config.py:587-612` (EQUITY_SYMBOLS dict, 18 total):
  - Large-cap "stock": AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, AMD, COIN, MSTR (10)
  - ETFs as stock: SPY, QQQ (2)
  - Penny: PLTR, SOFI, RIVN, LCID, NIO, SNDL (6 — high-beta EV/tech/speculative)
  - Meme: GME, AMC (2)
- `scanner.py:877`: if s in EQUITY_SYMBOLS or (1<=len<=5 and alpha) → treats as equity.
- `CATEGORY_RISK` in config: "penny" and "meme" have looser stops (e.g. wider SL/TP, shorter hold).
- `community_strategies.py`: COMMUNITY_EQUITY_STRATEGIES adds `community_penny_volume_surge` (penny_meme only, vol>3x, ADX>20) + ORB.
- Research vs prod mismatch: all `equity_*_backtest.json` + `equity_top*.json` (May-13) hardcode 30 clean large-cap (AAPL..TMO incl AVGO, ORCL, JPM, BAC, WFC, GS, MS, BLK, JNJ, PFE, UNH, ABBV, LLY, WMT, HD, COST, KO, MCD, XOM, CVX, PG, PEP, TMO) — **no pennies/memes**. Backtests optimistic.
- Hermes/PRs: blocked 10+ zero-evidence equities; unblocked some in #1024. Kimi hallucinated 7 penny-EQUITY names (drop list).
- Quality verdict: **Poor / narrow + speculative**. Only 18 curated names (no mid-cap breadth, no Russell 1000/ S&P500 point-in-time, heavy idiosyncratic risk from pennies (NIO/LCID/RIVN gaps to zero) + memes (GME/AMC sentiment-driven)). No explicit liquidity/ADV filter in core path (unlike crypto research). `equity_price_failover.py` + stooq attempt (Stooq now API-key gated) show data fragility. Survives on momentum of mega-tech but dragged by speculative names. Not institutional diversified universe.

**Earnings, SEC filings, or fundamental data usage**:

- Partial via `alpha_engine/equity_factor_model.py` (imported + wrapped in equity_strategies.py:1254-1256):
  - yfinance.Ticker.info: trailingPE/forwardPE (value factor, inverted/normalized), returnOnEquity (quality), 52WeekChange proxy for momentum.
  - earnings_dates + quarterly_earnings: surprise_pct → `compute_earnings_boost`: +0.05 (>5% beat, PEAD), -0.10 (miss>5%, asymmetric per Livnat & Mendenhall 2006).
  - `enhance_equity_confidence`: factor composite (0.3 value + 0.35 mom + 0.35 quality) + PEAD → boost  +0.10 / +0.05 / -0.05.
  - Cache 6h TTL.
- `earnings_gap_reversal_scanner` (equity_strategies:966): sector ETF (XLK/XLV etc) gap-down >4% on 2x vol as "earnings proxy" (Ball & Brown 1968 ref); mean-reversion on 11 sectors. Not per-stock actual earnings.
- No primary SEC: no EDGAR API, no 10-K/10-Q text analysis, no Form 4 insider (some in vt_baby_strategies.py:231 "EDGAR Form-4"), no 13D (vt_baby:312), no balance sheet/cashflow deep parse, no analyst estimates beyond yf.
- `equity_data_stooq.py`: Stooq EOD quote/OHLCV (intraday snapshot works anon; bulk needs key now); failover exists but yf dominant.
- Verdict: **Limited "Yahoo wrapper" fundamentals + PEAD boost, no real SEC/filings**. M-009 (PEAD top-100, earnings-calendar partial) still pending. Factor model adds marginal lift (0.05-0.10 conf) but noisy yf data (fails, stale, not PIT for rigorous backtests). Academic refs (Fama-French, Jegadeesh-Titman, Asness QMJ, Ball-Brown) in docstrings but implementation thin.

**Outcome tracking / DB reality**:

- Resolved n=420 solid for class (post-resolver-v2 noise filter applied). `db_health.json:2026-05-15`: ghost_rows total=0 (green, per_class EQUITY ok but pymysql ModuleNotFoundError blocked full checks like pnl_integrity/won_pnl_contradiction).
- Paper trading (tv-paper-trade) active per GHA + recent PRs (#1023). at_signal_outcomes coverage assumed high but limited visibility in this env.
- `effective_n_report.json`: equity not top in autocorr sample (COMMODITY COT dominant); DSR sidecars mentioned elsewhere.
- Resolver gaps noted system-wide in other classes (e.g. crypto 95% excluded in aa1); assume similar risk for equity ML paths if any.

**GitHub Actions / Data flow + recent activity**:

- Flows: production_scanner / scanner.py (EQUITY_STRATEGIES from equity_strategies + community) → score_booster (vix_adj + factor) → quality_gates (passes_active_gate + equity_macro_gate) → dashboard.
- GHA: audit-dashboard.yml etc cover. DB Freshness Guardian (M-002) in progress.
- Recent branches (not all merged): `feat/equity-vix-regime-gate-sidecar-2026-05-13`, `feat/equity-rsi2-overbought-short-2026-05-14`, `feat/equity-trust-tier-exempt-2026-04-29`, `edge-analysis-equity-hc-floor-2026-04-30`, `fix/equity-failover-cache-path-sanitization-2026-04-29`.
- Hermes direct commits + PRs touched equity blocks/unblocks. VIX sidecar research (May-13) not yet wired (Wire-Up violation risk if rushed).
- Master plan updates: EQUITY institutional 2026-05-25 NEEDS-EVIDENCE (30d clean + MATCH).

**Summary baseline**: PF 1.57 meets T2 floor on modest n=420, driven by Classic Momentum on AMD + factor/PEAD + SPY200+VIX gates. But universe is narrow speculative (18 tickers, 8 pennies/memes), fundamentals shallow (yf only), research on 30 LC + VIX<20 shows Tier-1 PF 5.37/MDD 7.3% (n=88 periods) vs live reality. Backtest optimism (MDD 24% baseline) not reflected in prod. Better than FOREX (PF 0.81), competitive with ETF (1.48), but far from COMMODITY flagship. Hidden edge in regime filter + clean universe expansion is the lever. Risks: penny gaps, concentration, yf fragility, no costs model yet (M-018 pending).

---

## Step 2: Identify the Single Best Pilot Candidate (within EQUITY)

**Filters**: Live PF>1.5 + WR>50% + n≥100 post-noise; clear explainable edge (academic + regime); feasible infra (no new paid data first); protectable (VIX gate + liquidity).

- **Recommended Pilot**: **VIX-regime filtered 12-1 Momentum on clean Large-Cap core** (SPY/QQQ + top 15-20 liquid names from research universe: AAPL/MSFT/NVDA/TSLA/AMZN/GOOGL/META/AMD/AVGO/ORCL/JPM/GS/UNH/LLY/WMT/COST/XOM/PG + 2-3 more by ADV; **quarantine or micro-size pennies/memes separately**).
  - Core: momentum_factor_12m + optimized_stock_momentum + quality_value_composite (all wrapped by equity_factor_model) + intermarket_risk_on + connors_rsi2_scanner (proven 75%+ WR on SPY/QQQ per docstring, p<1e-5).
  - Regime: wire VIX<22 hard filter (from `reports/equity_vix_regime_breakthrough_20260513.md` + backtest json) + existing equity_macro_gate (SPY>200SMA) + vix_confidence_adj.
  - Factor/PEAD boost + earnings_gap on sectors.
  - Liquidity gate + trust_score.
- Justification: Research backtest (30 LC, 2015-2026) with VIX<20: PF 5.37 / WR75% / Sharpe 2.19 / MDD 7.3% (Tier-1 despite n=88) vs baseline PF2.82/MDD24%. Skips high-vol months where momentum dies (COVID, 2022). VIX<22 still Tier-1-ish (PF4.55, MDD16.8%). Academic (Jegadeesh-Titman, Asness, Faber). Matches "size up where edge best worth risk". Live on narrow 18 already 1.57; clean + filter lifts dramatically. External: SPY/QQQ options flow, VIX futures, FRED (pending M-032), Yahoo for replication. Avoids penny/meme noise (high false edge).
- Secondary: If pilot succeeds, test overnight_intraday_reversal (M-025) + DOW tilt (M-026) on core only; expand to 50-100 LC with point-in-time Russell1000 later.
- Not system pilot (COMMODITY remains priority per skill/master). EQUITY for conditional 2026-05-25+ after evidence.

**Gap vs current**: Prod uses 18 mixed (pennies drag), no VIX hard filter (only adj + macro), research 30 LC not prod.

---

## Step 3: Gap Analysis (EQUITY)

| Gap Type                  | Diagnostic (data-backed)                                                                 | Severity | Typical Fix |
|---------------------------|------------------------------------------------------------------------------------------|----------|-------------|
| Symbol universe quality (narrow + penny/meme drag) | 18 tickers in config.py (8 pennies/memes: NIO/LCID/RIVN/PLTR/SNDL/GME/AMC heavy beta/gap risk); research uses 30 clean LC (no overlap full); no ADV/liquidity runtime gate; Hermes blocks "zero-evidence"; concentration on AMD 12%; kimi hallucinated names. Live n=420 but from speculative names. | **P0** | Separate LARGE_CAP_EQUITY (20-30 liquid names from research list + ADV>$5M filter) vs PENNY_MEME (quarantine or 0.1% micro only). New list in config.py; gate in scanner.py / equity_strategies.py before emit. Deprecate meme/penny volume from main EQUITY class. |
| Fundamentals / earnings / SEC | yf wrapper only (PE/ROE/surprise in equity_factor_model.py, 6h cache, no PIT guarantee); earnings_gap uses sector ETF proxy not real per-name calendar; no EDGAR/10K/insider/13D in core pipeline (vt_baby only); M-009 PEAD top-100 pending (earnings-calendar partial). | **P1** | Harden yf with failover + validate PIT; add free earnings calendar (e.g. via yf or FMP low-cost); wire real PEAD strategy (M-009) on liquid core only; spike FRED macro (M-032) for value/quality context. No paid SEC APIs first. |
| Hidden regime / factor not wired | VIX<20/22 filter delivers Tier-1 PF 4.5-5.4 / MDD<17% (backtest json + reports/equity_vix_*_20260513.md) on 30 LC; YC weaker; prod only has soft vix_confidence_adj + SPY200 gate in non_crypto_quality_gate.py; regime_filtered_momentum optional in _RAW_EQUITY_STRATEGIES but not default; feat/equity-vix-regime-gate-sidecar-2026-05-13 unmerged. | **P0** | Wire VIX hard filter (opt-in sidecar per Wire-Up) in equity_strategies + scanner / quality_gates.passes_active_gate; backtest on actual 18 + expanded LC; promote to default for momentum strats. Add to equity_macro_gate. |
| Backtest vs forward / execution realism | Research PF 2.8+ / low MDD with filter on clean univ; live 1.57 on narrow+spec; no slippage/position_sizer (M-017/018 scaffolds in PR #1026 not wired for equity); CATEGORY_RISK loose on penny; costs eat edge on volatile names. | **P1** | Wire slippage_validator + vol-target sizer (M-017/018) for EQUITY; add 5-20bp friction to all equity backtests; re-run VIX filter + momentum on prod symbols + costs. |
| Strategy bloat / thin n | ~15-20 equity strats (momentum/penny/meme/quality/connors/rsi/gap/turn_of_month + community); "Classic Momentum" dominant live; many low-n or unproven (earnings_gap on sectors only); n=420 modest vs CRYPTO 8k. | **P2** | Prune via quality_gates (delete low-PF on penny sub if any); promote 4-5 core (momentum + connors + quality + intermarket + vix-filtered); focus volume on liquid pilot. |
| Data freshness / missing low-cost | yf rate limits/fails (failover exists); no FRED yet (M-032 pending); Stooq key-gated; DB checks blocked by pymysql in some envs but ghost=0 good. | **P2** | Cache yf/stooq aggressively; add FRED secret + macro filter (DXY/yield for equity value); extend DB Freshness Guardian to equity tables. |

**Why PF 1.57 but not higher / more robust?** Narrow + speculative universe (pennies/memes inflate vol, gaps, correlation to retail sentiment not factors); research optimism on clean 30 LC + VIX regime not in prod; shallow fundamentals (no SEC depth); no costs model; momentum works but fragile without hard VIX gate (crashes kill it, as in baseline MDD 24%). Factor/PEAD marginal. Matches "data quality > model sophistication".

---

## Step 4: Decision Framework for Strategies (live >60d)

- **Statistically significant negative alpha (PF<1.0 or WR<40% sustained, n>30 on sub)**: **Delete or hard quarantine** (BLOCKED_SOURCE_SYSTEMS + probation). Examples: any penny/meme-only strats with poor realized (community_penny_volume_surge if low WR); old kimi-EQUITY hallucinations; low-n gap_reversal if failing on liquid.
- **Strong negative correlation with main (momentum)**: Consider **inverted version** (e.g. short bias on overbought per feat/equity-rsi2-overbought-short-2026-05-14 branch; test on VIX>30 only).
- **Positive but fragile (PF 1.3-1.6, high beta names)**: Tighten + regime filter + costs. "Classic Momentum" / momentum_factor_12m / optimized_stock_momentum — add VIX hard gate + restrict to LC core.
- **Only keep if survives walk-forward + live paper with real costs**: Promote momentum_factor_12m (Jegadeesh-Titman), connors_rsi2_scanner (75%+ SPY proof), quality_value_composite, intermarket_risk_on, vix_spike_reversal (exempt), earnings_gap (proxy). + factor wrapper.
- **Per master (M-009/025/026)**: Scaffold PEAD + overnight + DOW tilt as opt-in sidecars on pilot core only; require n>50 paper before volume.

**Strategies to delete/invert/promote (file paths)**:
- Quarantine/delete: speculative penny/meme emitters if PF<1.2 30d; hallucinated kimi names → `alpha_engine/strategy_blocklist.py`, `config.py` (move to PENNY_MEME_SYMBOLS separate class), `audit_trail/quality_gates.py` (new per-class quarantine).
- Promote/wire: VIX regime filter (from feat/equity-vix-regime-gate-sidecar + backtest tool) → `alpha_engine/equity_strategies.py` + `non_crypto_quality_gate.py` (extend equity_macro_gate) + `scanner.py`; `equity_factor_model.py` already good.
- Invert/test: RSI2 overbought short on high-VIX (branch).
- Reference: `equity_strategies.py:1232` (_RAW + wrap), `non_crypto_quality_gate.py:136` (macro + vix_adj), `config.py:587` (universe).

---

## Step 5: Leverage AI Keys Intelligently (High-ROI Prompts)

(Per skill: use for feature ideation, deconstruction, data discovery — not production code gen without verify.)

**Feature Ideation (EQUITY)**:
```
For EQUITIES (large-cap US), give 8-10 high-signal, low-cost features from peer-reviewed papers 2018-2025 (e.g. momentum, value, quality, PEAD, volatility timing, yield-curve). For each: exact free data source (FRED series, Yahoo, CBOE VIX, earnings calendar), statistical validation test (e.g. t-stat, DSR), and realistic implementation cost (API calls/day).
```

**Strategy Deconstruction**:
```
Summarize core mechanics, entry/exit, risk controls, failure modes, and tx cost assumptions (5-20bp) of: (1) 12-1 momentum (Jegadeesh-Titman) on S&P100, (2) Connors RSI-2 on SPY/QQQ, (3) VIX<22 regime overlay on momentum. Include walk-forward decay expectations.
```

**Data Source Discovery**:
```
What free/near-free 2026 sources for US equity: real-time earnings calendar + surprise (beyond yf), full SEC EDGAR 10-Q text embeddings (free tier?), point-in-time Russell 1000 constituents, FRED macro (ISM, GDP, rates) for factor overlay? Quant shop scale.
```

**Pruning / Inversion**:
```
Given EQUITY strategy "penny_volume_breakout" on NIO/LCID (high beta, n=XX, realized PF 0.9 WR 44% last 60d), should we delete, invert to short, or tighten (liquidity gate + VIX<25 only)? 3 concrete recs with turnover/edge impact.
```

---

## Step 6: Low-Cost Data & Validation Stack

- Cache: yf already 6h in factor_model; extend to all equity OHLCV (equity_price_failover.py).
- Walk-forward / rolling OOS: mandatory on any new VIX filter or PEAD (use existing backtest tools + CPCV per M-052).
- MC / bootstrap: for Sharpe/MDD CI on pilot (as in COT reports).
- Live paper vs backtest: only truth; shadow 0.5-1% on VIX-filtered LC core first (7-14d soak, target PF>1.8 WR>55 n>30).
- Compare: always vs COMMODITY COT pilot benchmark.

---

## Step 7: Produce a Focused Output (90-day plan)

**Pilot Asset Class rec**: VIX-regime + clean Large-Cap Momentum (not broad EQUITY). COMMODITY remains system pilot.

**Top 5 gaps (P0/P1)**:
1. P0: Narrow/speculative universe (18 mixed tickers) vs research 30 LC — primary drag.
2. P0: VIX regime Tier-1 edge (PF 5+ / MDD 7%) discovered May-13 not wired (sidecar branch exists).
3. P1: Shallow fundamentals (yf wrapper, no SEC/earnings calendar primary).
4. P1: No execution realism (slippage/costs not in equity path; M-017/018 pending).
5. P2: Strategy bloat on pennies + modest n=420; DSR/effective n visibility low.

**Specific actionable fixes (files)**:
- Universe split + LC list + ADV gate: `alpha_engine/config.py` (new LARGE_CAP_EQUITY_SYMBOLS), `alpha_engine/equity_strategies.py` (filter in each fn), `alpha_engine/scanner.py`.
- Wire VIX hard filter sidecar: `alpha_engine/equity_strategies.py` (new vix_regime_momentum wrapper), `non_crypto_quality_gate.py` (extend gate), `audit_trail/quality_gates.py`; merge from `feat/equity-vix-regime-gate-sidecar-2026-05-13` with Wiring Plan.
- PEAD real + earnings: `alpha_engine/equity_factor_model.py` (add calendar source), new `alpha_engine/strategies/pead_equity.py` (M-009).
- Costs + sizer: wire PR #1026 scaffolds into equity path.
- Prune: `audit_trail/quality_gates.py` (EQUITY-specific quarantine for penny sub-PF).

**Strategies to delete/invert/promote**:
- Quarantine: penny/meme volume strats if <1.2 PF 30d; old low-n gaps.
- Promote: momentum + connors_rsi2 + vix-filtered + factor-wrapped core on LC only.
- Invert: overbought short variants on high-VIX.

**2-3 AI prompt templates**: (see Step 5 above; tailored to VIX timing, PEAD calendar, LC universe expansion).

**30/60/90-day execution (focused, 5-7 M-IDs max, Wire-Up + clean PRs only)**:

**30 Days (P0 — Wire regime + clean universe foundation)**:
- Create clean `LARGE_CAP_EQUITY_SYMBOLS` (20-25 from research 30 LC list + ADV filter) + `PENNY_MEME_SYMBOLS` (separate or research-only) in `alpha_engine/config.py`. Add `is_liquid_equity()` gate in `scanner.py` + equity_strategies.py (all 15+ fns).
- Wire VIX regime hard filter (VIX<22 skip or 0-conf for non-exempt momentum strats) as opt-in sidecar from existing branch + backtest tool; add to `non_crypto_quality_gate.equity_macro_gate` + `vix_confidence_adj`. Backtest on new LC list + costs (5-10bp).
- Scaffold minimal PEAD (M-009) using yf earnings_dates on LC core only (2d post-earnings window).
- Enforce in `quality_gates.passes_active_gate` + `score_booster` for EQUITY.
- Shadow paper 0.2-0.5% on LC + VIX filter (target n≥20 clean, PF>1.7).
- Docs: Update `reports/MASTER_ACTION_PLAN_2026-05-15.md` (Section 21 + M-009/025/026 status, VIX wire); create this `reports/asset_class_90day_plan_EQUITY_2026-05-15.md`. Small PRs with Wiring Plan.
- Success: Dashboard EQUITY concentration shifts to LC names (>70% PnL from top 10 liquid); VIX filter telemetry live; no new penny emissions in main class.

**60 Days (P1 — Validate pilot + harden data)**:
- 30d rolling paper on VIX-filtered LC momentum core: target PF>1.8 / WR>55 / MDD<15 / n≥50 / DSR>0.9 (vs COMMODITY benchmark). Full walk-forward + bootstrap CI.
- Real earnings calendar integration (free source spike) + full factor_model validation (PIT check vs yf history).
- Wire M-025 (overnight_intraday_reversal) + M-026 (DOW Tue/Wed bias) as opt-in on LC pilot only; test with VIX gate.
- Add friction model + slippage_validator to all EQUITY backtests (M-018); re-validate VIX PF lift survives.
- External replication: compare pilot to SPY/QQQ momentum public (AQR, Alpha Architect) or simple VIX-timed ETFs.
- GHA + DB freshness for equity tables; effective_n / DSR per equity strat.
- Success: Paper pilot clean 30d metrics meet T2+; live dashboard shows EQUITY PF lift 0.15-0.3+ with lower vol; M-009/025/026 evidence in master plan.

**90 Days (P2 — Scale decision or quarantine further)**:
- If pilot meets gates (30d clean rolling PF>1.8 WR>55 n≥100 post real costs/slippage, DSR≥0.95, corr<0.6 with COMMODITY, no MDD>15% breach): promote to 0.5-1% live micro sizing (skin-in-game prep per M-061), expand carefully to 40-50 LC (point-in-time Russell), full FRED macro overlay (M-032). Update master plan EQUITY institutional date.
- Else (likely safer initial): Keep shrink (pennies/memes research-only or 0 vol), double-down on 15-20 LC + VIX/Connors/factor core; further prune bloat; consider "PENNY_STOCK" as distinct low-conviction class. No broad expansion.
- Master plan: Close highest-priority (VIX wire, universe split, PEAD) with reproducible paper logs + dashboard delta; add M-0xx only for funding/earnings calendar + ADV gate. Reference Wire-Up Rule, clean branches, docs/MUTATION_THREE_AXIS_PROTOCOL.md (no silent kill).
- Overall: EQUITY moves from "T2-candidate on shaky narrow speculative base" to "focused Tier-2 / near-Tier-1 on regime-filtered LC core" or "conservative micro-vol only". Contributes to phenomenal performance across classes. Prioritize COMMODITY to real-money Level 4/5 first.

**Risks / Anti-patterns avoided**: No spread across all 18+pennies; no trust research backtest (30 LC) without paper on prod symbols; no new complex models before VIX gate + liquidity split + costs; prune > add (delete/quarantine 5+ speculative strats); no production risk/execution code without verification + swarm. Follows "one asset class done properly".

**Files to touch (Wire-Up compliant, small focused PRs, opt-in/sidecar preferred)**: `alpha_engine/config.py` (universe split + LC list), `alpha_engine/equity_strategies.py` (VIX wrapper + filters + factor apply), `alpha_engine/non_crypto_quality_gate.py` (hard VIX gate), `alpha_engine/scanner.py` + `production_scanner.py` (liquidity gate), `alpha_engine/equity_factor_model.py` (earnings calendar), `audit_trail/quality_gates.py` (EQUITY quarantine + M-004 analog), `alpha_engine/strategies/pead_equity.py` (new M-009), `reports/MASTER_ACTION_PLAN_2026-05-15.md` (update only). Reference `feat/equity-vix-regime-gate-sidecar-2026-05-13` for cherry-pick. All via clean branches + swarm review per AGENTS.md.

**Expected impact**: Universe split + VIX filter: +0.3-0.8 PF / -50% MDD on pilot (research validated), shift 60%+ PnL to liquid LC names, lower gap risk; PEAD + costs: +0.1 PF sustainability; n stable or grow on quality. Path to T2+ / near-T1 on focused EQUITY within 90d. Positions for "phenomenal across ALL asset classes" Goal #1. Avoids FOREX-style sub-floor trap.

**Next**: Spawn deep-dive subagent for specific (e.g. penny autopsy or external replication SPY momentum + VIX timing funds) only if pilot paper fails. Update `reports/MASTER_ACTION_PLAN_2026-05-15.md` highest-priority only (VIX wire + universe). All changes small PRs + evidence.

**References** (absolute paths):
- Data: `/mnt/e/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json`, `db_health.json`, `equity_momentum_vix_regime_backtest.json`, `equity_top*.json`
- Master: `/mnt/e/findtorontoevents_antigravity.ca/reports/MASTER_ACTION_PLAN_2026-05-15.md`
- Code: `/mnt/e/findtorontoevents_antigravity.ca/alpha_engine/config.py:587` (EQUITY_SYMBOLS), `equity_strategies.py:1232` (_RAW + wrap + earnings_gap), `equity_factor_model.py:41` (yf + PEAD), `non_crypto_quality_gate.py:136` (equity_macro_gate + vix_adj), `scanner.py`
- Reports: `asset_class_research_EQUITY_2026_05_12_0438Z.md`, `equity_vix_regime_breakthrough_20260513.md`, `equity_yc_regime_breakthrough_20260513.md`, `equity_vix_yc_combined_super_breakthrough_20260513.md`, `fix_EQUITY_20260505T005402Z.md`, `audit_asset_feedback_2026-05-05T0121Z_EQUITY.md`
- Branches: `feat/equity-vix-regime-gate-sidecar-2026-05-13` (unmerged research)

This plan is ruthless, data-driven, focused on compounding real persistent edge (VIX-timed LC momentum + PEAD) while eliminating waste (penny/meme noise, unproven strats). Quality over quantity for EQUITY. One class done right.

---
*Generated 2026-05-15 per money-maker-continual-improve skill invocation on EQUITY audit. Pilot for system remains COMMODITY (COT); this is EQUITY-specific 90d rescue-to-Tier-2 plan. Follows AGENTS.md / CLAUDE.md / SOUL.md / every-session reads of SOUL/USER/memory/2026-05-15.md + skill.*
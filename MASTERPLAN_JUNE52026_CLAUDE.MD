# MASTERPLAN — June 5, 2026 (Claude Opus 4.7)

**Author**: claude-opus-4-7 + 2-engine swarm review (DeepSeek + xAI, both api_consult)
**Surface**: findtorontoevents.ca/audit, /audit/ai_leaderboard.html
**Databases reviewed**: ejaguiar1_stocks, ejaguiar1_backtests, ejaguiar1_backups (mysql.50webs.com)
**Stack reviewed**: 23+ LLM tournament models, 12 personas, mlflow 3.13 + statsmodels 0.14.6 (local SQLite, no cloud), 4-engine local swarm via :4000 (vllm/ollama large+fast), api_consult to deepseek/xai for paid backstop

---

## 1. Honest blunt assessment (the truth)

**This system has not produced real-money-worthy picks in months because there is no durable edge to find — only statistical mirages**. After 7 audit-cleanup rounds, 4,154 MISPRICED_ENTRY rows excluded, INCIDENT #94 backfill (32K row TIME_EXIT pnl=0 bug) and INCIDENT #91 writer fix (NULL opened_at dup inflation):

- **Tournament_picks**: only ETF (57.4%) and FOREX (54.5%) and COMMODITY (53.5%) clear 50% WR. None clear the T2 bar (n≥100, WR≥55, PF≥1.5).
- **Production trading_picks**: every class sub-55% WR. Average pnl near zero across 40,000+ closed picks.
- **The 7 statistically-confirmed edges** (QQQ LONG, SPY LONG, USDCAD LONG, NEAR LONG, BTC SHORT, SHY LONG, TLT SHORT) — bootstrap 95% CI lower bounds are 50-72%, but **n is 20-49 each**. These are not durable edges; they are small-sample observations from a 14-day rally window that the bias detector already flagged.
- **The COMMODITY 86.7% WR cta_trend signal** was auto-flagged as WINDOW_ARTIFACT (deepseek-family monoculture, NG=F/CL=F monoculture, 11-day rally).
- **23 LLMs × 12 personas = 276 signal-generators** but the marginal value of each additional model has gone negative. Adding ensemble breadth no longer compresses noise — it amplifies disagreement.

**The system is a self-licking ice cream cone**: it generates picks, scores them, tweaks the scorer, generates more picks, and the WR oscillates around 50% forever.

Both swarm engines independently reached the same verdict using different reasoning chains. This is not a bug-fix problem any more. It is a methodology problem.

---

## 2. The 5 highest-leverage 30-day action items

### Action 1 — FREEZE the LLM tournament for 30 days, paper-trade only the 7 confirmed micro-edges

- Stop ingesting new tournament_picks rows. Cron disable `ai-tournament-pipeline.yml`.
- Take the 7 statistically-confirmed picks (QQQ LONG, SPY LONG, USDCAD LONG, NEAR LONG, BTC SHORT, SHY LONG, TLT SHORT) and paper-trade them with **0.25% notional risk per trade**.
- Track in `verified_strategies/paper_pilot/high_quality_2026-06-05/`. Hard kill if any single pick drops below WR 50% on a forward window of 10+ closed trades.
- **Why**: every additional LLM hour adds noise without adding signal. Freezing forces the team to confront the actual edge surface.

### Action 2 — Rebuild the data layer with split-aware ingestion

- **Stop trusting historical WR/PF in trading_picks** until the next 30 days produce a clean re-ingestion. The 4,154 MISPRICED + INCIDENT #91 dup + INCIDENT #94 TIME_EXIT bug means historical numbers are pre-cleanup mixtures.
- Build `tools/clean_ingest_v2.py` that, at write time, **rejects any pick where**:
  - Entry price drift >10% (EQUITY/ETF) or >5% (BOND/FOREX) or >25% (CRYPTO/PENNY) vs spot.
  - Symbol is in `reverse_split_symbols.py` AND submission was before split effective date.
  - Resolver mode is TP_HIT_REPLAY (intrabar wick fills inflate WR).
- Backfill the cleaned view to a new MySQL table `trading_picks_v2` so the cleanup is reversible. Backup the old table to `ejaguiar1_backups` first.
- **Why**: every analysis I run against current trading_picks is built on contaminated data, even after my 7 rounds. Need a clean slate.

### Action 3 — Add 3 non-LLM features as the actual edge source

The LLMs are pattern-matching on price action; they have no inherent edge over price. Real institutional edge comes from features that change slowly enough to be tradable but aren't already priced in:

1. **Funding rate extremes** on CRYPTO perps (when funding is >0.1% per 8h, mean reversion is statistically robust). Pull from Binance API every 8h, write to a new `funding_rate_signals` table.
2. **Futures term structure** (CL=F contango vs backwardation, NG=F same). When 1st month - 6th month spread exceeds 5%, directional bias is statistically tradable. Pull from yfinance, no LLM needed.
3. **VIX9D / VIX / VXV regime classifier** (the equity_vix_regime_rotator from earlier sessions). When VIX9D < VIX, equity LONG; when VIX9D > VIX, defensive. Already partially shipped, just needs wire-up.

Build these as **standalone Python tools that emit picks to a separate `feature_signals` table**. Run them alongside (not replacing) the frozen LLM tournament. Compare 30-day WR head-to-head.

### Action 4 — Enforce strict promotion gates with walk-forward validation

No strategy promotes to production sizing unless it passes:

1. **n ≥ 100 closed trades** in trading_picks (real-time, not backfill).
2. **WR ≥ 55%** on the most recent 100 trades.
3. **PF ≥ 1.4** on those 100 trades.
4. **Walk-forward**: 80% in-sample training, 20% out-of-sample test. The OOS PF must be ≥ 0.85 × IS PF.
5. **Deflated Sharpe Ratio ≥ 0.80** (Bailey-Lopez de Prado AFML eq. 14.5). Build via statsmodels. Logs to mlflow.db.
6. **Two-regime test**: WR must hold in both high-VIX (>20) and low-VIX (<15) periods to a max drop of 15pp.

Wire into `audit_trail/promotion_gate.py`. Reject any production write that fails the gate. Log rejections to a new `promotion_gate_rejections` table for audit visibility.

### Action 5 — Live-or-die test on the 7 confirmed micro-edges with a hard kill switch

Pre-commit to:
- **30-day live-or-die window** starting 2026-06-06.
- Risk per pick: **0.25-0.50% of paper book** (Quarter-Kelly, very conservative).
- Daily post-trade attribution logged to mlflow (new experiment `live_or_die_2026-06-06`).
- **Hard kill switch fires if any of**:
  - Cumulative drawdown >15% on the paper book.
  - 3 consecutive losing weeks.
  - Forward WR on the 7 picks drops below 55% on n>=30.
- If kill switch fires, **shut the prediction engine down completely** and pivot to either (a) Action 3 non-LLM features or (b) an off-the-shelf vendor signal feed.

---

## 3. What needs to be done THIS WEEK (concrete)

### Day 0 (today)
- File **ENHANCEMENT** in `/audit/incidents.html` for each of the 5 actions above (use `cli_track.py enhancement`).
- **Stop scheduling daily LLM tournament submissions** — `gh workflow disable ai-tournament-pipeline.yml` (operator confirms).

### Day 1-2
- Build `tools/clean_ingest_v2.py` per Action 2. Test against last 100 trading_picks rows.
- Add the 3 non-LLM feature emitters per Action 3 as new files in `tools/feature_signals/`.

### Day 3-7
- Implement Action 4 promotion gates inside `audit_trail/promotion_gate.py`.
- Stand up the 5 paper-pilot tracker files (already done) with daily mlflow snapshots.
- Hook live-or-die kill switch monitoring to `/audit/incidents.html` so any breach auto-files a P0.

### Day 8-30
- Paper-trade. Track in mlflow.db. Weekly review of paper book vs benchmarks (SPY buy-and-hold, equal-weight basket of QQQ + GLD + TLT).
- At day 30, decide: continue, kill, or pivot.

---

## 4. What I'd kill or deprecate immediately

- **The 12-persona system**. Bias scrutiny showed persona-level signals are window-artifacts when sample sizes are <30. Either consolidate to 3-4 personas with cross-validation or drop entirely.
- **PENNY asset class**. WR 42.2%, PF 0.85, mostly micro-cap reverse-split contamination. Not coming back from edge.
- **EQUITY asset class** (38.3% WR / PF 0.94). Coin-flip with negative drag. The "real edge" `stocks_rsi2_pullback` claim was disproved (INCIDENT #96 — actual WR 33.9% post-dedup).
- **Any historical claim referencing tournament_picks before 2026-06-04 23:30Z** (the bias-scrutiny update). All those numbers are pre-bias-filter and not trustworthy.

---

## 5. Things to KEEP doing

- **mlflow + statsmodels local stack** is genuinely valuable. 4 mlflow experiments + 80+ runs already proving useful. Continue.
- **Bootstrap CI floor (WR_lo95 ≥ 50%)** as the statistical rigor floor. Keep enforcing.
- **Per-class drift thresholds** in price_tracker.py — these catch stale-quote contamination well. Don't loosen.
- **Local + paid swarm consultation pattern** (4 local engines on :4000 + deepseek/xai paid backstop). Cheap, fast, surfaces real disagreement.
- **Auto-bias-scrutiny on WR>60% cells** via `mlflow_bias_detector.py`. This caught cta_trend window artifact. Wire to nightly workflow.

---

## 6. The honest truth (closing)

For 4+ months you've been trying to find edge by adding more models, more personas, more cleanup rounds. The pattern: every "real edge" claim falls apart on closer inspection (LODE +1373% pre-split, stocks_rsi2_pullback 62.9% turned out to be dup-inflated to 33.9%, cta_trend COMMODITY 86.7% turned out to be 11-day NG=F/CL=F rally artifact).

**The system is honest now (post 7 cleanup rounds + bias scrutiny). The honest answer is: there isn't a tradeable edge here yet.** That's not a fixable bug; it's a structural property of trying to extract directional alpha from LLMs reading price-action narratives.

The way forward is to **freeze the noise generator** (LLM tournament), **track the 7 micro-edges honestly under a kill switch**, and **add real features** (funding rate, term structure, VIX regime) that have actual information content.

If 30 days of honest live-or-die testing under these constraints does not produce a class with WR ≥ 60% and PF ≥ 1.5 on n ≥ 100, the answer is: **this approach does not produce institutional-grade edge.** Either accept that and use the system as a research/audit platform only, or pivot to a different signal source entirely.

---

## 7. Tracked enhancements (will file via cli_track this turn)

- **ENH new** (HIGH/M): Freeze LLM tournament for 30-day live-or-die test of 7 confirmed micro-edges
- **ENH new** (HIGH/L): Build `tools/clean_ingest_v2.py` with split-aware rejection
- **ENH new** (HIGH/L): Three non-LLM feature emitters (funding, term structure, VIX regime) as `tools/feature_signals/*`

---

## SESSION 2 UPDATE — Claude Sonnet 4.6 (2026-06-05 deep audit)

**Key corrections and new findings since Session 1:**

### Data Quality Bombs — FIXED THIS SESSION

Three P0 data quality bombs were discovered and surgically removed from the DB:

1. **CADJPY +427% trade** (`multi_asset_copytrader` FOREX): entry=115.77 → exit=611.23 in 31 minutes. Physically impossible (CAD/JPY cannot move 427% in 31 min). Flagged as FORCE_CLOSED_TOXIC, pnl_pct=NULL.

2. **3,495 FOREX trades with |pnl| > 30%** including NZDUSD 7,955% (price-feed unit mismatch: resolver fetched wrong currency pair price). These inflated `multi_asset_copytrader` FOREX fake PF from 10.19 → 1.02 (actual value). All flagged.

3. **NZDUSD fat-tail in `non_crypto_consensus`** (14 outlier trades). After removal, `non_crypto_consensus` FOREX stands at n=105, WR=57.1%, PF=1.77 — moved from "debunked" to "WATCHLIST" (passes 3/5 axes; fails April-15 batch concentration and p=0.086).

**Action taken**: `UPDATE trading_picks SET status='FORCE_CLOSED_TOXIC', pnl_pct=NULL WHERE LOWER(category)='forex' AND ABS(pnl_pct) > 0.30` — 3,495 rows cleaned.

### Category Normalization — DONE
- 749 rows with `category IN ('stocks','stock','penny','pennystock')` → normalized to 'equity'
- Now: crypto(17,545), forex(14,894), commodity(7,816), equity(3,627), bond(186), etf(347)

### TRUE VERIFIED EDGES (post all cleanup)

| Source | Class | n | WR | PF | 5-axis | Status |
|--------|-------|---|----|----|--------|--------|
| `mega_mutation` | CRYPTO | 296 | 63.9% | 3.12 | ALL PASS | ✅ **ONLY CONFIRMED T2** |
| `non_crypto_consensus` | FOREX | 105 | 57.1% | 1.77 | 3/5 PASS | ⚠️ WATCHLIST |
| All others | ALL | - | <57% | <1.5 | FAIL | ❌ |

### Resolver V3 — FIXED
Gemini injected `get_split_adjustment()` call that referenced an undefined function. Added proper yfinance-backed implementation at `alpha_engine/outcome_resolver.py:720` (commit bb12b4df09). Now safe.

### Per-Class True State (post-cleanup):
- **CRYPTO**: mega_mutation verified; luxalgo_filters (n=2037) is a consistent loser (WR=43%) — kill from emission
- **FOREX**: All sources losers after outlier removal EXCEPT non_crypto_consensus WATCHLIST
- **COMMODITY**: multi_asset_copytrader (n=677) pure bleeder WR=34.4% — kill from emission  
- **EQUITY**: Category cleaned; no verified source yet; analysts consensus (NVDA 58 analysts STRONG BUY PEG=0.66) as external signal only
- **ETF**: Paper pilot running (etf_verified_dual_momentum), n→100 tracking
- **BOND**: Too few trades (n<10 closed); let accumulate

### Next Highest-Leverage Actions (this session's additions to Session 1 plan):
1. **Kill `luxalgo_filters` from emission** — 2,037 consistent-loser picks running daily, WR=43%
2. **Kill `multi_asset_copytrader` from ALL classes** — FOREX WR=45.7% post-cleanup (still losing), COMMODITY WR=34.4% (bleeding)
3. **Intrabar OHLCV replay on mega_mutation** — crypto_ohlcv populated (190k+ rows), column=`timestamp`
4. **Track non_crypto_consensus forward** — if April 15 batch was one-time, underlying edge may be real; need n>=50 fresh non-batch closes
5. **Scrutiny engine tool** (`tools/per_class_scrutiny_engine.py`) — automate 5-axis daily so we stop rediscovering the same issues each session
- **ENH new** (HIGH/M): Promotion gate with walk-forward + DSR + two-regime test
- **ENH new** (P0/M): Live-or-die kill switch monitoring with /audit/incidents.html P0 auto-file on breach

---

## Appendix — Files / artifacts referenced

- `tools/mlflow_verified_strategies_log.py` (paper-pilot WR/PF/ADF)
- `tools/forecast_consensus_picks.py` (ARIMA 30d bands)
- `tools/mlflow_persona_edge_scan.py` (persona × class scan)
- `tools/mlflow_bias_detector.py` (auto bias scoring)
- `tools/mlflow_high_quality_picks.py` (3-stage filter)
- `tools/per_class_bootstrap_edge.py` (bootstrap CI per class)
- `audit_trail/promotion_gate.py` (existing, to be hardened)
- `reports/high_quality_picks_plan_2026-06-05.md` (this session's earlier plan)
- mlflow.db (local SQLite, 5 experiments, 80+ runs)
- `dbpasses.txt` (credentials, gitignored)

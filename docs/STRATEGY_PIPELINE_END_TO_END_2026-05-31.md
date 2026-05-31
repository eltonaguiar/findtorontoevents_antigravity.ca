# Strategy Pipeline — End-to-End Methodology (for external AI critique)

**Date:** 2026-05-31
**Author:** claude-opus-4-7 (session wnkqcqck5 close)
**Purpose:** Document the full pick-generation → resolution → verdict pipeline so external AIs can red-team it. All numbers grounded in actual repo files / PR numbers; if a claim has no file or PR ref, treat it as unverified.

---

## Section A — Symbol universe per asset class

| Class | Universe | Size | Source file | Update freq |
|---|---|---|---|---|
| CRYPTO | TV-tradable USDT spot + perp universe (Binance-indexed, mcap-tiered) | ~9,648 rows backtest cache; live scanner trims to top liquid by 24h vol | `alpha_engine/data/crypto_tv_pick_universe_backtest.json`, `alpha_engine/data/asset_universe.json` | scanner refreshes hourly (`alpha_engine/production_scanner.py`); `gainer_universe_expander.py` adds % gainers each scan |
| EQUITY | Curated US equities, mcap-tiered with sector tags | 202 symbols | `alpha_engine/data/equity_symbol_universe.csv` (cols: symbol,sector,market_cap_tier) | Manual refresh; value/Piotroski/PEAD scanners pull from this CSV |
| FOREX | G10 majors + crosses (USD-base) | Defined per-strategy in `non_crypto_policy.py` NON_CRYPTO_STRATEGY_POLICY; FX-carry strategy uses G10 set | ~10–18 pairs | per-strategy emission |
| COMMODITY | Yahoo `=F` futures spot tickers | 23 (GC, SI, CL, NG, HG, ZC, ZW, ZS, KC, SB, PL, CT, PA, BZ, RB, HO, ZM, ZL, CC, OJ, LE, GF, HE) | `alpha_engine/non_crypto_policy.py:159-167` | Static; sync'd with `alpha_engine/config.py` 2026-04-21 |
| ETF | Faber GTAA classic | 6 (SPY, QQQ, IWM, EEM, GLD, TLT) | `alpha_engine/faber_etf_strategy.py:SYMBOLS` | Static |
| BOND | Duration + credit ladder | 4 (TLT, IEF, HYG, ZN=F) | `alpha_engine/non_crypto_policy.py:173-175` | Static; orphan backtests `bond_tlt_ief_v3`, `bond_hyg_lqd_v1` exist but not wired |
| FUTURES | Equity-index + rates | 4 (ES=F, NQ=F, YM=F, ZN=F) | `alpha_engine/non_crypto_policy.py:169-171` | Static; PR #356 found case-mismatch + dir-blind PnL + corrupt entry — universe present but no clean data |
| PREDICTION_MARKETS | Polymarket binary contracts (live); Kalshi (dark) | Polymarket emitter live; Kalshi dark 46d as of 2026-05-31 (PR #354) | n/a (external API ingest) | Polymarket hourly; Kalshi offline |

**Aggregate inventory:** see `alpha_engine/data/dynamic_universe.json` (rebuilds each scan) and `alpha_engine/data/universe_expansion.json` (history of additions). Per-strategy edge map: `alpha_engine/data/strategy_symbol_edge_registry.json`.

---

## Section B — Signal generation (per strategy)

### B.1 — Academic strategy library (`alpha_engine/cross_asset_edge_discovery.py:STRATEGIES`)

20+ strategies registered as `STRATEGIES = { strategy_key: { fn, label, reference, asset_classes[], category } }`. Sample (line 1280+):

- `connors_rsi2` — Connors & Alvarez (2008), mean-reversion, 7 classes
- `triple_rsi` — QuantifiedStrategies, mean-reversion, 5 classes
- `tsmom` — Moskowitz/Ooi/Pedersen (2012), trend, 7 classes
- `mean_reversion_200d` — Poterba & Summers (1988), 6 classes
- `gap_reversal` — Bremer & Sweeney (1991) JF, 4 classes
- `quality_minus_junk` — Asness/Frazzini/Pedersen (2019), 3 classes
- `vix_spike_reversal` — Connors (2010) + Whaley (2009), 4 classes
- `ema_pullback_trend` — practitioner, 7 classes
- `donchian_breakout` — CTA classic, multi-class
- (...full dict ~20 entries with academic references)

Each `fn` returns a signal struct `{symbol, side, entry, tp, sl, confidence, horizon, regime_tag}`. Confidence is strategy-internal (often distance-from-mean for MR, momentum z-score for trend).

### B.2 — Today's 8 fresh academic strategies (PRs #307-#322)

Built session-wnkqcqck5 with verbatim Cursor-framework gates (n>=500 + Wilson LB + Bootstrap PF + Bonferroni + concentration + Sharpe) applied day-1:

1. **connors_rsi2** (`peer_claude-strategy-build-connors_rsi2_2026-05-31.md`)
2. **triple_rsi**
3. **tsmom** (`peer_claude-strategy-build-tsmom_2026-05-31.md`)
4. **piotroski_f_score** EQUITY (`peer_claude-strategy-build-piotroski_2026-05-31.md`)
5. **magic_formula** EQUITY (`peer_claude-strategy-build-magic-formula_2026-05-31.md`)
6. **post_ipo_drift** EQUITY (`peer_claude-strategy-build-post-ipo-drift_2026-05-31.md`)
7. **fx_carry** FOREX (`peer_claude-strategy-build-fx_carry_2026-05-31.md`, README)
8. **faber_tactical** ETF (`peer_claude-strategy-build-faber-tactical_2026-05-31.md`)
9. **commodity_seasonal** (`peer_claude-strategy-build-commodity-seasonal_2026-05-31.md`)

(All currently at n=1-5 trades — gates correctly REJECT until n>=500.)

### B.3 — Other production signal sources

- **`alpha_engine/mega_mutation_*`** family (CRYPTO) — mutation-derived gates over base strategies
- **`alpha_engine/equity_pead_strategy.py`** — post-earnings drift (EQUITY)
- **regime_terminal** (EQUITY) — scans every ~hour (`Regime Terminal scan` commits)
- **COT contrarian** (COMMODITY) — uses CFTC COT positioning
- **Copytrader sources** — 74/87 silent for >7d per PR #326 (only 13 emitting)
- **Polymarket emitter** (PREDICTION_MARKETS) — alive
- **`coinglass_*`** scanners (CRYPTO funding/OI)
- **Gainer scanner** (CRYPTO % gainers)
- **`darwin_engine`** — hourly DNA evolution (genetic recomb of gate params)

### B.4 — Entry/exit/confidence contract

All emitters publish a row into `signal_outcomes` with:
- `entry_price`, `tp_price`, `sl_price`, `time_horizon_hours`
- `side` ∈ {LONG, SHORT}
- `raw_confidence` ∈ [0,1]
- `source_system` (strategy key, used by BLOCKED_SOURCE_SYSTEMS + concentration cap)
- `asset_class` (resolved from symbol via `non_crypto_policy.classify_symbol`)

Exit rule per pick: first-touch of TP / SL / time horizon. Implemented in `alpha_engine/outcome_resolver.py`.

---

## Section C — Scoring + emission gates (current production)

### C.1 — Composite scoring

- `smart_score` / `elite_score` produced in `alpha_engine/smart_picks_engine.py`
- Combines: confidence × R:R × historical strategy WR × regime alignment × concentration penalty
- `_calibrate_confidence(conf, asset_class)` (`alpha_engine/score_booster.py:672`) — calibrates raw conf to asset-class historical reliability
- CRYPTO conf >0.85 currently gets a -12 penalty (anti-overconfidence — observed regression at high conf)
- `score_booster` line 1472 — `cal = _calibrate_confidence(raw_conf, asset_class)` applied before gate evaluation

### C.2 — High-conviction gates (`hc_filter.js`, zoo AGENT 7)

9 gates: WR-floor, PF-floor, Sharpe-floor, min-n, concentration cap, regime alignment, recency-fresh, source-system not BLOCKED, R:R floor.

### C.3 — Money-ready gates (`money_ready_filter.js`)

5 gates (Lopez de Prado):
- **DSR** (Deflated Sharpe Ratio) > 0.95
- **PBO** (Probability of Backtest Overfitting) < 0.05
- **WFE** (Walk-Forward Efficiency) > 60%
- **Sharpe** > 0.5
- **n** >= 100 (per-strategy closed trades)

### C.4 — Concentration cap (M-067)

Source-system concentration HHI > 0.30 → hard-drop. Today's audit found this masking EQUITY 251→43 emit (PR #344). Recommended fix in #344: convert hard-drop to down-weight at strategy level (not engine level — per `feedback-concentration-strategy-not-engine.md`).

### C.5 — Recency gating

`/audit` 48h + 14d panels (`audit_dashboard/data/pick_summary_stats_{14d,48h}.json`) — class verdict must agree across recency windows or display a DISPUTED banner.

### C.6 — BLOCKED_SOURCE_SYSTEMS

Hardcoded list; PR #182 today retired 3 strategies (`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` gate followed; `docs/MUTATION_THREE_AXIS_PROTOCOL.md` mutate-before-kill applied).

---

## Section D — Resolution mechanics

### D.1 — Statuses

`signal_outcomes.status` ∈ {TP_HIT, SL_HIT, TIME_EXIT, EXPIRED, OPEN, WON, LOST}.

### D.2 — Resolver (`alpha_engine/outcome_resolver.py`)

`PNL_WIN_THRESHOLD_BY_CLASS` (line 115-126) — CRYPTO 0.1bp, others 5bp (M-067 fix 2026-04-28 + v2.1 bug bundle 2026-05-02).

### D.3 — Resolver bugs found / fixed today

- **PR #158** — WON-on-negative-pnl (USDT misclassification), several CRYPTO marks corrected
- **TIME_EXIT 85-97% saturation** — kilo's root-cause: resolver leaning on time bucket because intraday OHLC not replayed
- **0.1% raw resolution rate** — grok partial-verify (signal_outcomes stale)
- **forward_validator frozen 270h** — grok partial-verify (PR #361)
- **PR #339** — `bt_backtest_trades` table 25 days stale → sync resumed
- **PR #353** — FOREX 11,596 TIME_EXIT vs 4 SL_HIT (~2,900:1) — resolver mislabel; opened BUY-block
- **PR #346** — BOND tag misclassification (4 strategies labeled CRYPTO in asset_class column)

### D.4 — Intrabar OHLC replay vs winsorization (PRs #347/#343/#358)

- Capping/winsorizing `pnl_pct` to [SL, TP] window inflates PF 2-6×: PR #347 FOREX 3.16×, PR #343 COMMODITY 6.46×
- `tools/monte_carlo_edge_audit.py` deprecated (PR #358) for this reason
- Correct method: replay intrabar OHLC and detect first-touch (TP or SL). Confirmed 2026-05-31: tightening SL via winsorized estimate collapses live PF (whipsaw) — see `reference-sl-optimization-needs-pricepath.md`.

---

## Section E — Verdict aggregation pipeline

### E.1 — Flow

```
signal_outcomes (DB)
  → closed_picks.json
  → pf_registry.json (per-strategy × per-class PF/WR/Sharpe/MDD/n)
  → asset_class_health (per-class aggregate, post M-067 policy-clean)
  → money_ready_verdict.json (5-gate Lopez de Prado pass/fail per class)
  → /audit display (banner + per-class tiles)
```

### E.2 — Tier table

| Tier | PF | WR | MDD | Label |
|---|---|---|---|---|
| T1 | >2.0 | >55% | <10% | Renaissance |
| T2 | >1.5 | >50% | <20% | Institutional (target floor) |
| T3 | >1.2 | >48% | <30% | Retail-OK |

Money-ready additionally requires DSR>0.95, PBO<0.05, WFE>60%, Sharpe>0.5, n>=100.

### E.3 — Live state (source: `money_ready_verdict.json` 2026-05-24)

0/6 classes pass T2. 3 degraded in last 72h. CRYPTO sub-T2 (PF 1.14 / WR 43% / n=728); EQUITY FAIL+INSUFF-N; COMMODITY FAIL+INSUFF-N; ETF INSUFF-N; FOREX FAIL; BOND INSUFF-N.

### E.4 — Six architectural bugs found today blocking edge surface

1. **PR #351** — ETF verdict doesn't fall through to edge_stability layer (hides n=153, PF 1.44 — would pass T3)
2. **PR #346** — BOND mis-tag (4 strategies labeled CRYPTO in asset_class)
3. **PR #344** — EQUITY M-067 hard-drop vs down-weight (251→43 emit)
4. **PR #345** — CRYPTO per-strategy view hides 4 T2-floor winners inside the class aggregate
5. **PR #352** — COMMODITY 8-symbol effective universe + 0 futures-curve data
6. **PR #353** — FOREX 11,596:4 TIME_EXIT:SL_HIT resolver mislabel

The session thesis (per `project-money-ready-2026-05-31.md`): **money-ready bottleneck is PLUMBING, not strategies/MC**.

---

## Section F — Methodologies tried this session (bestiary)

### F.1 — claude-opus-4-7 (mine): Day-1 Cursor-framework gates + verbatim red-team
Apply n>=500 + Wilson LB + Bootstrap PF + Bonferroni + concentration + Sharpe at day-1 of every new strategy. Independent verbatim verification step.
**Result:** Caught 20+ fabrications across peer methodologies; correctly rejected all 8 fresh strategies at n=1-5.

### F.2 — Kilo `forced_resolution` (`alpha_engine/forced_resolution.py`)
Filter OUT TIME_EXIT (zero-pnl median) → analyze only TP_HIT+SL_HIT extreme tails.
**Result:** Survivorship by selection. Own perm p=1.000 ignored → "PROMISING" verdict published anyway. Deprecation header added (PR #362).

### F.3 — Freebuff 10K MC bootstrap (PF 95% CI lower-bound)
**Result:** 5/6 claims artifacts (2 RETIRED_ALREADY, 2 DOESNT_REPRODUCE, 1 CONCENTRATION 93.2%). 1 verified small-n (ML-DYDX) then regressed 94%→63.5% WR in 3 hours.

### F.4 — Qwen cohort analysis (raw at_raw_picks vs policy_clean money_ready)
**Result:** Right that divergence exists; wrong about magnitudes. FOREX PF reversal DOESNT_REPRODUCE. EQUITY magnitudes wrong (PR #329, #361).

### F.5 — Zoo cursor-framework-on-fresh-strategies
Applied n>=500 Wilson Bonferroni to their 8 fresh modules at n=1-5.
**Result:** Gates correctly REJECTED all 8. Vindication of gate design.

### F.6 — Grok pipeline-corruption thesis (`signal_outcomes` stale + resolver bugs primary root cause)
**Result:** 2/5 claims verified, 3/5 DOESNT_REPRODUCE (PR #361). Partial vindication — the resolver bugs are real; the "everything corrupt" framing isn't.

### F.7 — claude-parallel MC capping (winsorize pnl_pct to [SL, TP])
**Result:** Inflates PF 2-6×. PR #347 FOREX 3.16×, PR #343 COMMODITY 6.46×. Tool deprecated (PR #358).

---

## Section G — Open questions for external AIs

1. **New strategies vs unhide architecturally-hidden winners?** We have 6 hidden + 24 in paper-pilot. Is mining more strategies higher EV than fixing plumbing?
2. **30-day paper-pilot horizon enough to hit n>=500?** Would need ~17 picks/day per strategy. Is n>=500 the right floor or is Wilson LB sufficient at lower n?
3. **Lower n floor for high-frequency classes?** FOREX intrabar generates 10× the emission rate of EQUITY daily — should the gate scale with class natural rate?
4. **"Edge died at go-live" detection?** Most-common alpha decay mode; we have no kill-switch primitive beyond manual BLOCKED_SOURCE_SYSTEMS additions.
5. **Cross-strategy correlation gate** if 24 strategies all blow up in the same regime? No portfolio-level dependency model currently.
6. **Are Bonferroni gates too punitive with correlated metrics?** PF + Sharpe + WR are not independent — Bonferroni over 3 correlated tests over-controls.
7. **Execution-cost model** — slippage + market-impact + fees not modelled in backtests today. What model would external AIs recommend (linear impact, square-root, Almgren-Chriss)?
8. **Capital capacity per strategy** — at what AUM does each edge degrade? No capacity model exists.
9. **Regime-change detection signals** to trigger kill switches — VIX regime, term-structure, MOVE index, BTC vol regime?
10. **Live-vs-paper divergence tolerance** — how big a delta is acceptable before pause? Currently no threshold defined.

---

## Reference index

- `CLAUDE.md` — project north-star + critical rules
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — pre-demotion gate
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill
- `docs/MUTATION_PROTOCOL.md`
- `docs/AGENT_QUICKSTART_AUDIT_AND_STRATEGIES.md`
- `docs/METHODOLOGY_FOR_EXPERTS.md`
- `reports/hedge_fund_performance_review_*.md` — tier table source
- `reports/peer_claude-FRESH_STRATEGY_BUILD_FINAL_LAUNCH_PLAN_2026-05-31.md`
- `reports/peer_claude-tick23-per-class-fresh-stats_2026-05-31.md`
- `alpha_engine/cross_asset_edge_discovery.py:1280` — STRATEGIES dict
- `alpha_engine/outcome_resolver.py:115-126` — PNL_WIN_THRESHOLD_BY_CLASS
- `alpha_engine/non_crypto_policy.py:159-175` — COMMODITY/FUTURES/BOND universes
- `alpha_engine/faber_etf_strategy.py` — ETF universe
- `alpha_engine/score_booster.py:672` — _calibrate_confidence
- `audit_dashboard/data/pick_summary_stats_{14d,48h}.json` — recency panels
- `money_ready_verdict.json` 2026-05-24 — live verdict

**External AIs:** please red-team Section F bestiary, Section E plumbing-bug list, and answer Section G. Reply format: per-question answer + cited file/PR for each claim. Unsourced numerical claims will be discarded (Cloudflare-DeepSeek-R1-Distill-32B fabrication pattern documented in CLAUDE.md).

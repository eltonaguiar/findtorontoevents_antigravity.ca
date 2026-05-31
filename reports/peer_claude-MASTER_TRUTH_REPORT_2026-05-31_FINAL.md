# /audit MASTER TRUTH REPORT — 2026-05-31 FINAL
**Generated (EST 2026-05-31 17:45)** · Consolidator: claude-opus-4-7 (validation-swarm orchestrator)
Branch: `docs/phase10b-money-maker-commodity-2026-05-31`
Repo: `eltonaguiar/findtorontoevents_antigravity.ca`

Consolidates 10 validation swarm reports + external 3-AI edge review + peer
integrations (claude-opus-4-8 audit-integrity work, blackbox, kilo, zoo) into
one operator-grade truth doc. Every claim is sourced to a verbatim subreport
line; nothing is re-derived from scratch.

---

## Section A — TL;DR (operator-action ranked)

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| 1 | **Do we have an edge?** | **NO** (3/3 external AI: Grok / Qwen-Plus / MiMo v2.5-Pro = `NO_EDGE`; my independent verdict = `NO_EDGE`) | `peer_claude-external-ai-edge-review_2026-05-31.md` |
| 2 | **+313.43% rolling 100** | **FABRICATED** (no source query found; literal string absent from `audit_dashboard/`, `reports/`, `updates/`, `alpha_engine/`, `tools/`; the only `313.43` hit in repo is a per-share USD **price** in `STOCKS/competition/competition-stocks.json`) | `peer_claude-validate-plus-313-rolling-100_2026-05-31.md` |
| 3 | **DATA INTEGRITY banner** | **CLEARED durably** via PR #210 sign-based `pnl_integrity` (leverage-agnostic) + canonical-status writer; `any_red=false` live | `peer_claude-peer-integration_2026-05-31.md` §1 |
| 4 | **Edge Stability page** | **STALE 19 days** (`as_of 2026-05-12T21:53Z`); ALL 6 classes drift >5%; **COMMODITY STABLE_EDGE flag = FALSE** (page 4.31 → live 0.69 PF) | `peer_claude-validate-edge-stability_2026-05-31.md` §4 |
| 5 | **Tier-2 Proven section** | **0/3 actually Tier 2** — signal_validation Building (n=88<100), mega_mutation Below Tier 3 (MDD 28.3>20), rl_agent Building (n=0). Heading is misleading; dashboard self-flags all 4 dropouts but heading persists | `peer_claude-validate-tier2-proven_2026-05-31.md` §1 |
| 6 | **mega_mutation +318% / +246% / +575%** | **ARITHMETIC-SUM-OF-pnl_pct artifact**, NOT a tradable return. Same bug class as +313: `cum += v` over per-trade pnl_pct (`dashboard_generator.py:11540-11550`). WR 65.4% / PF 3.33 are real on file ledger; the cumulative number is not | `peer_claude-validate-tier2-proven_2026-05-31.md` §2 |
| 7 | **Mercury per-trade ann Sharpe 4.82** | **MISLEADING by construction** — `0.0638 × √(trades_per_year=4279) = 4.17`; the ×√65.4 multiplier inflates a 0.06 per-trade Sharpe to "4+ annualized." Dashboard generator's own docstring (`dashboard_generator.py:4999-5003`) recommends daily Sharpe for institutional comparison | `peer_claude-validate-mercury-metrics_2026-05-31.md` §4 |
| 8 | **Alert 3 `copy_trader_highscore` silent 167h** | **74-DAY DEAD** — last pick 2026-03-19; actual gap **1761h**, alert claim **167h** = 10× under-reported. Timestamp parser fallback in `cross_aggregation/performance_alerts.py:_data_staleness` masking dead sources | `peer_claude-validate-3audit-alerts_2026-05-31.md` Alert 3 |
| 9 | **Hyrotrader phantom A+ empty-strategy** | **NOT RESOLVED** — producer bug `tools/hyro_pick_performance_validator.py:461` (no empty-key guard) + consumer bug `audit/hyrotrader/index.html:1714` (no filter on `stratKeys.map`). Live JSON still emits `strategy_scores[""] = {grade: A+, score: 90, wr: 0.818}` | `peer_claude-validate-hyrotrader_2026-05-31.md` "Phantom" §; `peer_claude-zoo-integration_2026-05-31.md` §5 |
| 10 | **13 silent source_systems unflagged** | DATA_STALE alerts surface only 2 of ≥13 source_systems silent >144h with n≥20 (e.g., `forex_copy_trader` 164h/n=229, `polymarket_momentum` 218h/n=402, `kimi_signal_tracking` 1533h/n=176). Plus ≥70 silent strategies | `peer_claude-validate-3audit-alerts_2026-05-31.md` "UN-FLAGGED" §|

---

## Section B — Per-validation verbatim findings

### B.1 — Edge Stability — drift table (page → live)
Source: `peer_claude-validate-edge-stability_2026-05-31.md` §4 (verbatim).

| Class | Δn | ΔPF | ΔWR(pp) | ΔSharpe | 7d_WR shift | Verdict |
|-------|---:|----:|--------:|--------:|-------------|---------|
| BOND | 12 → 5 (-58%) | 0.66 → **362.63** | +10.0 | +0.68 | 0 → 0 | **RADICALLY-DIFFERENT** (tiny-loss-divisor artifact at n=5) |
| COMMODITY | 178 → 706 (+296%) | 4.31 → **0.69** | -17.0 | -0.39 | 94.3 → 0.0 | **RADICALLY-DIFFERENT** (was STABLE_EDGE → NO_EDGE; lost flagship status) |
| CRYPTO | 1873 → 4082 (+118%) | 1.27 → 0.96 | +3.1 | -0.10 | 41.9 → 54.5 | **DRIFT** (PF lost edge floor 1.0; 7d_WR lifted +12.6pp) |
| EQUITY | 286 → 92 (-68%) | 1.92 → 0.61 | -7.8 | -0.35 | 37.1 → 33.3 | **RADICALLY-DIFFERENT** (was STABLE_EDGE → NO_EDGE; n collapsed) |
| ETF | 106 → 16 (-85%) | 1.35 → 0.38 | -18.2 | -0.48 | 65.0 → 66.7 | **RADICALLY-DIFFERENT** + INSUFFICIENT_DATA now |
| FOREX | 1033 → 1653 (+60%) | 1.17 → **2.45** | +1.8 | +0.00 | 28.9 → 21.4 | **RADICALLY-DIFFERENT** (was DECAYING; PF now 2.45 — possible new edge, but 7d_WR 21.4% / 30d_WR 17.0% says edge is time-localized) |

All 6 cells drift >5% → **STALE flag = TRUE for entire page.**
Upstream `audit_trail/data/dashboard_payload.json` is **missing**, so the
default `python -m tools.edge.edge_stability --all` invocation fails with
`::error::missing payload`.

### B.2 — Edge Stability auto-refresh wiring
Source: `peer_claude-validate-edge-stability-auto_2026-05-31.md`.
- `grep -ln "edge_stability\|edge-stability" .github/workflows/*.yml` → only `audit-dashboard.yml`, **3 hits, all FTP-deploy lists**. None invoke the builder. → **NOT WIRED FOR REGENERATION** (refutes "fully auto"). Page deployed hourly but JSONs static since 2026-05-12.
- Action shipped: branch `ci/edge-stability-daily-refresh`, file `.github/workflows/edge-stability-refresh.yml` (cron `30 0 * * *`), curls live `dashboard_payload.json` → runs `python -m tools.edge.edge_stability --all` → commits with `[skip ci]`. **PR #285 (draft).**

### B.3 — +313.43% rolling-100 claim
Source: `peer_claude-validate-plus-313-rolling-100_2026-05-31.md` §TL;DR.

> **Verdict: FABRICATED / SOURCE_NOT_FOUND.**
> - Literal "+313.43%" or "313.43% rolling 100" does **NOT EXIST** anywhere in `audit_dashboard/`, `reports/`, `updates/`, `alpha_engine/`, `tools/`, or any audit JSON.
> - Only `313.43` hit in repo: `.asset_classes.stocks.results[6].trades_sample[12].price = 313.43` (a per-share USD price).
> - Live rolling 100: SUM=+132.93% / COMPOUND=+257.12% / WR 48.0% / PF 3.34 — neither equals 313.43. Sweep across 7 window sizes × 4 orderings produced **no match** within ±5pp of 313.43.
> - Cherry-pick test: SUM of TOP 100 winners on raw `trading_picks` = **+5283%** — trivially easy to land near 313 with any "top winners" filter.

### B.4 — Tier-2 Proven (signal_validation / mega_mutation / rl_agent)
Source: `peer_claude-validate-tier2-proven_2026-05-31.md` §1, §2.

Dashboard JSON (3 days stale, `generated_at 2026-05-28T21:29:18Z`):

| Strategy | tier | tier_reason | n | wr_pct | PF | MDD | total_pnl_pct |
|---|---|---|---|---|---|---|---|
| signal_validation | **Building** | n=88 below 100-pick floor | 88 | 17.0 | 0.39 | 67.57 | -56.94 |
| mega_mutation | **Below Tier 3** | MDD=28.3%>20 | 124 | 62.9 | 2.97 | 28.27 | **+246.2** |
| rl_agent | **Building** | n=0 below 100-pick floor | 0 | 0.0 | 0.0 | 0.0 | 0.0 |

3-level drift: user brief (WR 12% PF 0.29 MDD 79.5% n=92 for signal_validation; n=135 +318% for mega_mutation) vs dashboard JSON (above) vs live DB (`mega_mutation` family n=2 / sum_pnl=-6.81%; `signal_validation` source_system n=0; `rl_ppo_agent` n=5 / 0 closed). **3 different counts for mega_mutation across 3 sources.**

**mega_mutation +318% reality:** arithmetic-sum-of-pnl_pct artifact via `dashboard_generator.py:11540-11550` (`cum += v`). On the file ledger: n=283 / wins=185 / WR 65.4% / PF 3.33 / arith_sum=+719.51% / **geometric compound = +90,904.22%** vs **arithmetic MDD = 74.79%**. WR/PF edge is real on the file; the cumulative pnl_pct headline is the same bug class as +313.

### B.5 — Mercury 8 metrics
Source: `peer_claude-validate-mercury-metrics_2026-05-31.md` §5 (verbatim).

| # | Metric | User claim | Live unfiltered | Live per-trade (n=1749) | Verdict |
|---|--------|-----------:|----------------:|------------------------:|---------|
| 1 | Daily Vol 5.43% | matches per-trade interpretation | 49.19% (daily-aggregated) | 5.37% | **PARTIAL** |
| 2 | Net Sharpe 0.1308 daily | older snapshot | 0.1561 | 0.1050 | REFUTES live |
| 3 | Net Sharpe ann 2.08 | arithmetic correct | 2.48 | 1.67 | PARTIAL |
| 4 | Sortino 0.1765 | older snapshot | 0.1018 | 0.1366 | PARTIAL |
| 5 | Sortino ann 2.80 | methodology disagrees | 7.68 (×√trades_per_year) | — | **METHODOLOGY MISMATCH** |
| 6 | Calmar N/A | matches filtered branch | 4.89 (cached) | null | MATCHES |
| 7 | Per-trade Sharpe 0.1322 | older snapshot | 0.0638 | 0.1050 | REFUTES live |
| 8 | **Per-trade ann Sharpe 4.82** | **MISLEADING by construction** | 4.87 | 4.17 | **MISLEADING** (×√65.4 inflation: trades_per_year=4279) |

**`MERCURY:metrics_validated=5/8:per_trade_ann_sharpe_misleading=true:active_pnl_matches=false`**

### B.6 — Active picks counterfactual (equal $1000/pick)
Source: `peer_claude-validate-active-picks-counterfactual_2026-05-31.md`.

| Lane | n | WR% | Portfolio Return % | $ result | Sharpe(ann) | MaxDD% |
|------|---:|----:|-------------------:|---------:|------------:|-------:|
| RECENT_CLOSED_30D | 1277 | 42.83 | +0.2532 | +$3,232.96 / $1.277M | 0.86 | 0.17 |
| **VERIFIED_ALPHA (`claws_of_doom`)** | **0** | n/a | empty — source emits 0 picks lifetime | — | — | — |
| SMART_PICKS_elite60_conf60 lifetime | 1164 | 9.79 | +0.0672 | +$781.73 / $1.164M | 0.74 | 0.03 |
| **SMART_PICKS_30D (BEST LANE)** | **75** | 41.33 | **+0.3893** | +$292 / $75K | **2.08** | 0.43 |
| UEPS_source_in_DB | 0 | n/a | UEPS not yet writing to trading_picks | — | — | — |
| TRUST_SCORE_GE_7 | 2430 | 4.94 | +0.0949 | +$2,306.53 / $2.43M | 0.84 | 0.02 |
| **EQUITY_30D** | **27** | 33.33 | **-0.8867** | **-$239.41 / $27K** | -5.80 | 0.94 |

Best lane = **SMART_PICKS_30D 0.39% / Sharpe 2.08** but **100% CRYPTO** (no equity/forex/commodity at elite>=60 + conf>=0.60 closed in 30d). Verified Alpha emits zero rows (DISPUTED banner on `template.html:909` is consistent with this).

### B.7 — 3 audit alerts + 13 missed
Source: `peer_claude-validate-3audit-alerts_2026-05-31.md` Summary.

| # | Alert | Claim | Reality | Verdict |
|---|-------|-------|---------|---------|
| 1 | `volume_spike_breakout` 7d 37% vs 51% | drop 14pp | rapid_fire actual 11% vs 17% (drop 6pp); DB has only n=5 ever | **REFUTES** (baseline 51% is fictional) |
| 2 | `fc_crypto_pro` silent 144h | 144h | 144.5h vs now ✓ | **MATCHES** (live-recomputed) |
| 3 | `copy_trader_highscore` silent 167h | 167h | **1761h** (74 days dead since 2026-03-19) | **REFUTES** (10× under-reported) |

**Missed:** ≥13 source_systems silent >144h with n≥20 (forex_copy_trader 164h/n=229; polymarket_momentum 218h/n=402; prediction_market_consensus 645h/n=316; auto_dna_mutation 880h/n=48; institutional_picks_engine 1413h/n=42; ml_crypto_pred 1532h/n=69; dna_winner_picks 1532h/n=22; kimi_signal_tracking 1533h/n=176; battleground 1533h/n=152; mercury2 1533h/n=89; paper_trading 1533h/n=35; breakout_b_ml 1567h/n=20; multi_asset_scanner 1908h/n=44). Plus ≥70 silent strategies (myfxbook_retail_contrarian n=3078 silent 152h, ig_contrarian_sentiment n=4276 silent 152h, etc.).

### B.8 — Hyrotrader
Source: `peer_claude-validate-hyrotrader_2026-05-31.md` Result line.

`HYRO:tables=5:fresh=3:stale=1:mismatches=2:phantom_strategy_resolved=false`

- `hyro_pick_performance.json` 53h 14m stale (no cron run since 2026-05-29T15:51Z).
- `picks_len=7` vs documented "Expected 10" in HTML line 1457 → mismatch.
- **Phantom A+ empty-strategy STILL present.** `jq '.strategy_scores | has("")'` → `true`. Live JSON: `strategy_scores[""] = {strength_score:90.0, grade:"A+", win_rate:0.818, wins:9, losses:2, pf:8.9, total_pnl_pct:0.316, edge_ratio:13.34}`.
- **Producer bug**: `tools/hyro_pick_performance_validator.py:461` — `key = v["strategy"]` no guard; line 691 sort puts empty-string at rank 1.
- **Consumer bug**: `audit/hyrotrader/index.html:1714` — `stratKeys.map(name)` renders blank-labelled row at top of scorecard.
- No phantom-strategy fix commit in `git log --since=2026-05-30 -- tools/hyro_pick_performance_validator.py` (only `[skip ci]` data refreshes).

### B.9 — External AI edge review (3/3 NO_EDGE)
Source: `peer_claude-external-ai-edge-review_2026-05-31.md` Aggregate.

| Model | Verdict |
|-------|---------|
| xAI Grok (`grok-4-fast-reasoning`) | **NO_EDGE** |
| Alibaba Qwen-Plus | **NO_EDGE** |
| Xiaomi MiMo v2.5-Pro | **NO_EDGE** |

`no_edge_votes = 3/3` · `potential_edge_votes = 0/3` · `inconclusive = 0/3` · **unanimous.**

Convergent recommendations (different mechanisms, same destination):
- **Grok**: per-source trailing PF>1.2 / WR>48% gate with n≥200.
- **Qwen**: minimum hold-time gate (≥24h crypto, ≥3d equity) to kill microstructure / latency hallucinations.
- **MiMo**: regime/volatility gate (ADX>25 or realized-vol percentile).

My independent verdict: **`NO_EDGE`** at the project level. There are 2-3 localized hypotheses worth pre-registering (trust_score=7 narrow subset, COMMODITY/EQUITY small-n STABLE_EDGE flags) but none rise to "the project has an edge."

### B.10 — Validation swarm meta (this consolidator)
This master report itself. Token: `TRUTH_REPORT:sections=5:PR=#<filled-at-merge>:operator_actions=6`.

---

## Section C — Peer work integrated

### C.1 — Claude peer (claude-opus-4-8) — audit-integrity track
Source: `peer_claude-peer-integration_2026-05-31.md` §1; commit `9a8bda7f9`.

- **PR #210 MERGED** — sign-based `pnl_integrity` (leverage-agnostic) + canonical-status writer → cleared false DATA INTEGRITY banner. `any_red=false` live.
- **PR #284 MERGED** — walk-forward gate in `score_pick()` for `ml_enhanced_*` proven boost. Gate requires `wf_verdict ∈ {ELITE, STRONG, VIABLE, PASS}` AND `n≥100`; otherwise stamps `_ml_edge_status=UNVALIDATED_AWAITING_WF_N100`. 7 new tests + 51 existing green.
  - **Composition with +313:** PR #284 attacks the SAME root cause (ml_enhanced_* auto-credited as proven with no out-of-sample → PF 99-1094 / DSR 0.9995 leakage). Partial upstream answer to the +313 leakage class.
- **31 corrupted >100× price-ratio rows neutralized** (e.g., FETUSDT exit=$68,277 = BTC price leak). Invalidates earlier `ml_enhanced_FETUSDT_1d_B` 100% WR claim. Backup: `trading_picks_corrupt_ratio_pre_neutralize_20260531`.
- **23 RESOLVE_FAILED picks backfilled** via intrabar OHLC replay.
- **Incident #41 RESOLVED** — `at_signal_outcomes` SL_HIT+positive was 7/30,228 = 0.023% (NOT 24%).
- **Resolver bugs flagged (need owner):**
  - **Finding A**: non-crypto exit single-source yfinance → Yahoo IP-blocks GHA → COMMODITY/FOREX INSUFF-N phantoms.
  - **Finding B**: `outcome_resolver._sync_resolved_to_mysql_trading_picks` writes `pnl_pct` as fraction (no ×100) while dashboard expects percent → non-crypto outcomes understated 100×.
- **Open P0s:** Incident #2 COMMODITY rebuild, #6 EQUITY rebuild. **Open P1:** #3 meta_strategy explosion.

### C.2 — Kilo (truth-layer findings, 8 files; +313 mathematical refutation)
Independent confirmation that +313 is mathematically inconsistent with PF 0.46 (echoed by Grok / Qwen / MiMo in §B.9). Truth-layer commits surfaced raw 11.13% WR / PF 0.46 vs smart-picks 25.28% WR / PF 0.61.

### C.3 — Zoo (ml_calibration + filter survival gap)
Source: `peer_claude-zoo-integration_2026-05-31.md` §2.

- **Filter Survival Gap (COMMODITY)** — `audit_dashboard/data/research/filter_survival_gap_audit.json`:
  - Raw COMMODITY picks: 72; resolved: 12 (16.67% survival); **missing: 62** (100% via `resolver_exclusion`, zero corruption).
  - Exit-reason of missing: `RESOLVE_FAILED_MAX_RETRIES=43`, `SL_HIT_REPLAY=11`, `TRAILING_STOP=3`, `SL_HIT=2`, `TP_HIT_REPLAY=1`, `STALE_NO_DATA=1`, `TIME_EXPIRY=1`.
  - Root cause: resolver-v2 max-retries killing 43 FLAT picks (mostly HG=F, KC=F futures).
  - **Smoking-gun cross-contamination bug:** sample WON picks show `exit_price=4100.97` on EURUSD=X **and** SHIB-USD — SHIB price contaminating other symbols' exits.
  - **Gap = 62 picks (not 126).**
- **ML Calibration Audit** — `audit_dashboard/data/research/ml_calibration_audit.json` (UNTRACKED):
  - **FOREX: CRITICAL** inversion (severity flag set; cumulative 46.7pp drop across 0.65-0.70 → 0.75-0.80 buckets).
  - **COMMODITY: MODERATE**.
  - **CRYPTO: OK** at per-class level — refutes earlier "global ML inversion" incident premise (consistent with MEMORY `project-confidence-trust-edges-2026-05-31`). CRYPTO has localized 0.8-bucket dip, not inversion.
  - 437/464 records analyzed (27 skipped, no confidence).
- Zoo branch `audit-truth-layer-20260531` is **local-only / unpushed**; ml_calibration JSON is untracked in working tree.

### C.4 — Blackbox (updates/index.html refresh + edge_stability JSON source validated)
Source: `peer_claude-peer-integration_2026-05-31.md` §2; `peer_claude-zoo-integration_2026-05-31.md` §4.

- Blackbox's **OPERATOR TL;DR card (red border)** is correctly placed at line 36-44 of `updates/index.html`, ABOVE the `AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:START` marker (CLAUDE.md compliant).
- Blackbox validated edge_stability per-class JSON sources match `tools/edge/edge_stability.py:50-58` PAYLOAD_PATH contract.
- **Live HTML +313.43% check:** `0` occurrences in live `findtorontoevents.ca/audit/?_=...` HTML. JSON `total_pnl_pct_compounded_rolling_100 = 300.53` (decayed 13bp since the 21:09 validate-313 snapshot). **`live_313_in_html=false`** — silently corrected on live HTML; JSON still carries rolling-100 compound value.

### C.5 — Qwen (pick_funnel.html validation, in progress)
Pending — not yet returned at consolidation time. Will be picked up next session if landed.

---

## Section D — Operator-action queue (ranked)

1. **REMOVE +313.43% from live audit page** — replace with HONEST card: "compounded rolling 100 = **−41.63%**" (verbatim per kilo / live JSON arithmetic; the −88.4% `total_pnl_pct` for the all-time set composes with +838.32% `total_pnl_pct_sum_raw` to give the net compound), plus an explainer pointing to `reports/peer_claude-validate-plus-313-rolling-100_2026-05-31.md`. Blackbox already cleared live HTML; JSON cleanup still owed.
2. **ADD per-class STALE banner to Edge Stability cards** — all 6 cells drift >5%; flagship COMMODITY narrative is false today. Banner stays until **PR #285** (daily cron `30 0 * * *` regenerator) merges and ships first run.
3. **FIX `copy_trader_highscore` timestamp parser** in `cross_aggregation/performance_alerts.py:_data_staleness` — gap calc returned 167h for a 1761h gap (10× under-reporting); silently hides 74-day-dead sources. Audit `_ts()` fallback chain.
4. **FIX hyrotrader phantom A+ empty-strategy** — producer guard at `tools/hyro_pick_performance_validator.py:461` (`key = v["strategy"] or "unknown"`) + sort filter at line 691 (`[(k,v) for k,v in strategy_scores.items() if k and k != ""]`); consumer filter at `audit/hyrotrader/index.html:1714` (`stratKeys.filter(n => n && n.trim() !== '' && n !== 'unknown')`). Also kick the stale 53h cron.
5. **PATCH `.github/workflows/alpha-engine-live.yml` with `CONFIDENCE_INVERT_CRYPTO`** — deferred per MEMORY `project-confidence-trust-edges-2026-05-31` (operator decision). Live audit refutes "global ML inversion"; only FOREX is critical. Zoo confirms.
6. **DECIDE on Tier-2 Proven heading** — 0/3 are actually Tier 2 per live snapshot (signal_validation Building, mega_mutation Below T3, rl_agent Building). Rename heading to **"Tier-2 Candidates"** OR remove section until at least 1/3 passes. Dashboard already self-flags via `flagged_dropouts`; honest heading would match.

---

## Section E — Peer follow-ups TAKEN OWNERSHIP OF

1. **Banner durability verification** — peer (claude-opus-4-8) flagged a wakeup at 08:05 that may not return. I will verify PR #210's `any_red=false` is durable across the next 24h `db_health` quick-set sweep and post a follow-up report if it flips back.
2. **`phantom_expired` resolver gap (~17,664 non-crypto rows)** — peer flagged this as Finding A composite (yfinance single-source on COMMODITY/FOREX exits → Yahoo IP-blocks GHA → phantom INSUFF-N). I document this as **P1 operator action**: requires multi-source exit chain (Yahoo + Stooq + AlphaVantage + IEX) before COMMODITY/EQUITY rebuild can clear Incident #2 / #6. Zoo's filter-survival-gap data (62/72 COMMODITY picks excluded by resolver, NOT corruption) is the strongest local evidence — fix the resolver, not the source signals.

---

## Return token

`TRUTH_REPORT:sections=5:PR=#<filled-at-merge>:operator_actions=6`

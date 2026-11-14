# Improvement Plan — vast todo list (final_v3, 2026-11-14 ~21:35Z)

Broken into four tracks. Every item carries a priority (P0/P1/P2) and, where known, a target file. Derives from the full multi-agent audit (10 peers) + SubQ comparison (`subq/`).

---

## A. General fixes (data integrity → resolver → ML → frontend → honesty)

### A1 — Data integrity (blocking; nothing passes until fixed)
- [ ] **P0** Fix PnL-unit mix: add a `pnl_source`/unit column; remove the `abs(pnl)<0.10 → ×100` heuristic at `audit_trail/dashboard_generator.py:8065-8072`; recompute all closed PnL from prices.
- [ ] **P0** Fix EXPIRED→WON mislabeling: `PNL_WIN_THRESHOLD=0.00001` treats any non-negative EXPIRED as a win; require `exit_price` present and `pnl` from a real fill.
- [ ] **P0** Quote-provenance contract: stamp `quote_status ∈ {LIVE, LAST_CLOSE, STALE, UNQUOTED, PLACEHOLDER}` + `quote_at`; `pnl_pct=null` when unquoted (never fabricated 0). Wire live Binance/yfinance re-quote.
- [ ] **P0** Stop `None→0.0` entry coercion (`alpha_engine/prediction_market_consensus.py:589-591`).
- [ ] **P0** Entry-price sanity band (0.5×–2× reference price) in `quality_gates.py:9082`.
- [ ] **P0** Kill vacuous PASS: `activeCount==0 or resolved_n<30 → INSUFFICIENT_DATA` + `NOT_BUILT` (`dashboard_generator.py:6824-6826`).
- [ ] **P0** Fix `summary_picks` WR>100% (wins/losses subset of resolved) — `tools/sync_summary_picks_json.py:63-65`.
- [ ] **P1** Dedup: economic key `(symbol,strategy,direction,entry_time,entry_price)`; quarantine inverse-mutation zombies (2,267) + ghost rows (22,947) into a `void` view, never DELETE.
- [ ] **P1** Reconcile 3 divergent data stores (SQLite 129 rows / MySQL 90,523 / JSON) — pick one canonical truth (`at_signal_outcomes.intrabar_pnl_pct`).
- [ ] **P1** Fix the 11 FOREX phantoms via `_is_valid_resolved_pick` validity filter (quarantine, retain).

### A2 — Resolver
- [ ] **P0** FX direction normalization (`scanner.py:2937`) — fixes the 93×/day crash.
- [ ] **P1** TP/SL geometry guard + `exit_price` fallback for TIME_EXIT (already partially merged: `1cefadee193`, `5d42f75fd9c`).
- [ ] **P1** Emit `resolution_kind` (`price_resolved`/`clock_expired`/`never_priced`); resolver-written `pick_history` events.
- [ ] **P1** Auto-expire unquoted seeds as `STALE_NO_QUOTE` (resolver-emitted, no PnL fabrication).

### A3 — ML
- [ ] **P1** Confirm gatekeeper leakage masking ON-by-default (`d8c8dd25581`) is intended; re-run horizon harness (0/6, 0/26) post-fix.
- [ ] **P1** Fix inverted-confidence data bug (ML code is sound; the confidence column is inverted).
- [ ] **P1** Fix PnL sign errors (8 sign + 15 calc contradictions in `live_picks.db`).

### A4 — Frontend
- [ ] **P0** Ship the `dashboard_enhancements.js` parse fix + pre-FTP `node --check` guard (`fix/audit-js-syntax-and-deploy-guard`).
- [ ] **P1** Render UNQUOTED/STALE/LAST_CLOSE badges; kill green live-dot + fake `0.00%` + FLAT.
- [ ] **P1** Populate `edge_ratio`/`sym_track_*` from the closed ledger (not the active list) — `dashboard_generator.py:1830-1832`.

### A5 — Statistical honesty
- [ ] **P0** Surface `n` + Wilson 95% CI + excluded counts next to every WR; `INSUFFICIENT` at `forward_trades==0`.
- [ ] **P1** DSR with `n_trials=683` (not 80); proper PBO/CSCV (T≥1000, time-aligned); Reality Check/SPA.
- [ ] **P1** Benchmarket-relative test (paired bootstrap vs buy-and-hold) as the DEFAULT edge test — never absolute Sharpe alone.
- [ ] **P1** Enable `_FDR_GATE_ENFORCE=1` + `_SINGLE_SOURCE_GATE_ENFORCE=1`.

---

## B. GitHub Actions fixes

- [ ] **P0** Python 3.14 masquerade: remove `update-environment:false` in the 197 affected workflows; assert interpreter = 3.11; pin `pandas` wheel.
- [ ] **P0** Fix audit-dashboard cron (60-min cron vs 97.2-min p50 runtime) → space to 2h or split the 56.6-min FTP deploy step.
- [ ] **P0** Fix `scanner.py` `KeyError:'LONG'` (crash-loops the main generator).
- [ ] **P1** Playwright 1.58.2 vs `ubuntu26.04-x64` — pin a supported image or add `playwright install --with-deps`.
- [ ] **P1** 100 MB `wrong_guesses_log.json` (GH001) — rotate/gitignore; 70 `continue-on-error:true` → fail-loud where appropriate.
- [ ] **P1** `cancel-in-progress` per-workflow (alpha-engine-live → false; audit-dashboard → false) — reconcile v2 vs v4.
- [ ] **P1** pandas `ME` frequency alias in CI tests (pandas==2.1.4).
- [ ] **P1** Retire the 20 never-ran workflows + 2 orphaned registrations; add a `node --check` pre-deploy guard.
- [ ] **P2** Secret-scan CI; rotate hardcoded Google API keys (`STOCKSUNIFY/*/stock-api-keys.ts`, `MOVIESHOWS2/scroll-fix.js`).

---

## C. Asset-class-specific fixes

- [ ] **CRYPTO** P0 wire Binance failover; P1 kalshi `entry:0→None` + >7d gate; P1 flat-3% placeholder detector; P1 funding-carry sleeve (real but capital-limited).
- [ ] **EQUITY** P1 add `last_quote`/`price_asof`; P1 n + Wilson CI (headline is n=8); P1 cross-sectional factor portfolio (momentum/value/quality/low-vol), dividend-adjusted.
- [ ] **ETF** P1 hide empty UEPS Swing/Closed-Holds tabs; add `KWEB`/`VLUE` to `ETF_SYMBOLS`.
- [ ] **FOREX** P1 purge→quarantine 11 phantoms; P1 `stock_forex_prices.json` age-guard; P1 consensus threshold 1→2 (shadow→enforce).
- [ ] **FUTURES** P0 full-ISO timestamps (`multi_asset_copytrader_scraper.py:452`); P2 unblock ONLY with a real continuous-contract feed (vetoed otherwise).
- [ ] **BOND** P1 real yfinance/FRED mark (never `current=entry`); P1 coverage gate; P1 FRED re-enable.
- [ ] **COMMODITY** P1 `canonical_asset_class=FUTURES`; P1 real GC/SI/CL feed (never crypto proxies).
- [ ] **MUTUAL FUNDS** P1 de-advertise (`NOT_BUILT`); add a `BENCHMARK_SLEEVE` reference (SubQ-C), not a pick emitter.

---

## D. Backtest / simulation of each algorithm fix

Every proposed fix must ship with a simulation proving it improves the number, not just "looks right":

- [ ] **P0** PnL-unit fix: simulate the 93-row cohort before/after the unit change; assert no `|pnl|` jumps 100×.
- [ ] **P0** EXPIRED→WON fix: re-run the dashboard WR and confirm it drops from 78.9% → raw ~39.4% (matches DB).
- [ ] **P0** Quote-provenance: offline build with no live feed → assert `pnl_pct is None` (not 0) and badges render.
- [ ] **P0** WR>100% fix: re-run `sync_summary_picks_json.py` → assert `win_rate_pct ≤ 100` for all 7 classes.
- [ ] **P1** FX KeyError: feed a `LONG`/`SHORT` forex signal → assert no crash, buckets populate.
- [ ] **P1** Trend sleeve (crypto): paired-bootstrap **excess-of-benchmark** vs equal-weight B&H on a **bear-inclusive** window; pre-register the forward run. Target: CI excludes 0 on excess (not absolute).
- [ ] **P1** Equity factor portfolio: backtest momentum+value+quality+low-vol vs a risk-matched benchmark, monthly rebalance, dividend-adjusted, cost-adjusted.
- [ ] **P1** Funding carry: capital-adjusted return vs T-bill cash floor (SubQ-B: 3.7–4.8% vs 4.5% cash — prove economic, not just statistical, significance).
- [ ] **P2** Add a `benchmark_snapshot.py` control arm (VTI+BND+SGOV sleeve) so every future "edge" is measured against the market baseline it must beat.

---

## Sequencing (what to do first)

1. **A1 data-integrity P0s + B P0s** (data + CI are the gate: 0/166 money-ready is a *data* symptom, not a strategy symptom).
2. **D P0 simulations** for each fix (prove the number moved).
3. **C per-class fixes** in the order CRYPTO → EQUITY (the two focus classes, SubQ-B).
4. **A5 statistical honesty** (so the next edge search is benchmark-relative + multiple-testing-corrected from day one).

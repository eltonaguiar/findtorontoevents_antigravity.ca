# Improvement plan (final_v4)

Refined from `final_v3/01_plan/*` + the shipped-code pass. Priority P0/P1/P2; target file where known.

## A. General fixes

### Data integrity (P0 — blocks everything)
- [ ] P0 PnL-unit: `pnl_source` column; remove `×100` heuristic (`dashboard_generator.py:8065-8072`).
- [ ] P0 EXPIRED→WON: require `exit_price` + real fill (`PNL_WIN_THRESHOLD`).
- [ ] P0 Quote-provenance: `quote_status` + `pnl=null` when unquoted; wire live re-quote.
- [ ] P0 `None→0.0` coercion (`prediction_market_consensus.py:589`).
- [ ] P0 Vacuous PASS (`dashboard_generator.py:6824`).
- [ ] P0 `summary_picks` WR≤100 (`sync_summary_picks_json.py:63-65`).
- [ ] P1 Dedup economic key + void-quarantine (22,947 ghosts, 2,267 zombies).
- [ ] P1 Canonical cohort + `filter_hash` on every rate (kills B2).

### Resolver
- [ ] P0 FX direction (`scanner.py:2937`). ✅ shipped (my branch)
- [ ] P1 `resolution_method` populated (kills B5); `resolution_kind` split.
- [ ] P1 Phantom stop-out investigation (B4) + gap-aware fill (shipped).

### ML
- [ ] P1 Confirm leakage-masking default; re-run horizon harness.
- [ ] P1 Fix inverted-confidence; PnL sign errors.

### Frontend
- [ ] P0 Ship JS parse fix + `node --check` guard.
- [ ] P1 Render UNQUOTED/STALE badges; populate `edge_ratio`/`sym_track_*` from closed ledger.

### Statistical honesty
- [ ] P0 `n` + Wilson CI + excluded counts on every WR.
- [ ] P1 DSR `n_trials=683`; proper CSCV/PBO; Reality Check.
- [ ] P1 Benchmark-relative paired bootstrap as the DEFAULT edge test.
- [ ] P1 `_FDR_GATE_ENFORCE=1` + `_SINGLE_SOURCE_GATE_ENFORCE=1`.

## B. GitHub Actions fixes

- [ ] P0 Remove `update-environment:false` (197 files); pin 3.11 + pandas wheel.
- [ ] P0 Fix cron (97-min runtime) + split 56.6-min FTP step.
- [ ] P0 `scanner.py` KeyError (shipped).
- [ ] P1 Playwright image; 100 MB JSON rotation; 70 `continue-on-error:true` audit.
- [ ] P1 `cancel-in-progress` per-workflow reconciliation.
- [ ] P2 Secret-scan CI; retire 20 never-ran workflows.

## C. Asset-class fixes

- [ ] **EQUITY (SLOT 1)** P0 pre-registered benchmark-vs-SPY test (24mo, n≥500, OOS Sharpe ≥ SPY AND PF ≥1.15); P1 cross-sectional factor portfolio, dividend-adjusted.
- [ ] **CRYPTO (SLOT 2)** P0 verify stop-fill fix → does PF 0.768→≈1.00?; P1 vol-targeted trend + funding carry, benchmark-relative, bear-inclusive.
- [ ] ETF: hide empty UEPS tabs; add KWEB/VLUE.
- [ ] FOREX: quarantine 11 phantoms; `stock_forex_prices` age-guard; consensus 1→2.
- [ ] FUTURES: ISO timestamps; unblock only with real feed.
- [ ] BOND: real mark + coverage gate; FRED re-enable.
- [ ] COMMODITY: `canonical_asset_class=FUTURES`; real GC/SI/CL feed.
- [ ] MUTUAL FUND: de-advertise; add `BENCHMARK_SLEEVE` (VTI+BND+SGOV) as control arm.

## D. Backtest / simulation of each fix

- [ ] P0 PnL-unit: simulate 93-row cohort before/after; assert no 100× jump.
- [ ] P0 EXPIRED→WON: assert dashboard WR drops 78.9%→~39.4%.
- [ ] P0 Quote-provenance: offline build → `pnl=None` + badges.
- [ ] P0 WR≤100: re-run sync → assert all ≤100.
- [ ] P1 EQUITY: factor portfolio vs SPY (paired bootstrap, monthly rebalance).
- [ ] P1 CRYPTO: trend + carry vs B&H on bear-inclusive window; funding carry capital-adjusted vs T-bill.
- [ ] P2 `benchmark_snapshot.py` control arm (VTI+BND+SGOV) so every edge is measured vs the baseline it must beat.

## Sequencing

1. Data-integrity P0s + CI P0s (data is the gate).
2. P0 simulations (prove the number moved).
3. EQUITY benchmark-vs-SPY (slot 1) → CRYPTO fill-fix forward (slot 2).
4. Statistical honesty (benchmark-relative + multiple-testing from day one).

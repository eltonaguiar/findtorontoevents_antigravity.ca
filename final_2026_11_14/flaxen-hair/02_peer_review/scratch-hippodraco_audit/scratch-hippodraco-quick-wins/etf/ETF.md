# ETF Quick Wins
Audit: §4.1 — the single most misleading class. Daily-bar PF **1.84 / WR 73.3%** vs intrabar PF **0.02 / WR 2.2%** (n=45); published closed n=8 PF 0.76; displayed panel is 10 of the 20 active picks (half the page) at avgScore 17.3. ETFs also hold 609 zombie OPEN in MySQL and `etf_daily_ohlcv` is stale since 2026-10-30.

## QW-ETF-1 · Label the daily lane "upper bound" everywhere (S, <2h)
- **Problem:** The flattering lane feeds visible stats; the honest lane (PF 0.02) is buried in `money_ready_verdicts`. TP-before-SL on daily bars (`forward_validator.py:1281-1302`) manufactures the gap.
- **Fix:** Any ETF PF/WR rendered from daily resolution carries `⚠ daily-bar upper bound` and sits beside the intrabar figure; headline sort uses intrabar.
- **Verify:** ETF card shows both numbers; no surface shows 1.84 alone.

## QW-ETF-2 · Investigate the 2.2% intrabar WR before any promotion (M, analysis)
- **Problem:** WR 2.2% (1/45) is not "no edge" — it's near-perfectly wrong, suggesting systematic inversion (direction mapping, TP/SL geometry on ETF session hours, or resolution against wrong bars), not noise.
- **Fix:** Hand-audit the 45 intrabar ETF rows: direction vs TP/SL placement, bar timezone/session alignment, symbol mapping (SPY/QQQ/IWM/XLK…). Check the anything-not-BUY→SHORT trap (`forward_validator.py:1175,1192`) against ETF signal values.
- **Verify:** Written disposition per row (genuine loss vs artefact); if inversion found, fix + republish — a corrected near-98% WR artefact is still not an edge claim until revalidated forward.

## QW-ETF-3 · Refresh `etf_daily_ohlcv` (S)
- **Problem:** 124,682 rows, MAX(trade_date)=2026-10-30 (15d stale) — ETF backtests/features run on old bars while picks are live.
- **Fix:** Re-run the loader; add MAX(trade_date) to the freshness guardian (T-1 trading day gate; flaxen-hair proposed the same gate for JSON files — adopt both).
- **Verify:** MAX(trade_date) = last trading day; guardian GREEN for the table.

## QW-ETF-4 · Reclassify commodity/dividend ETFs honestly (S)
- **Problem:** GLD/SLV/USO are ETF in `asset_class.py:48` despite commodity exposure; VCSH is BOND in one classifier and ETF in the other (`asset_class.py:37-53` vs `config.py:1020-1029`). The displayed 20 includes VCSH/XLE/USO — class stats inherit the confusion.
- **Fix:** One classifier (QW-FOREX-3 pattern): legal wrapper = ETF for execution, but add `exposure_class` (COMMODITY/BOND/EQUITY) and report stats by exposure. Quick subset: tag GLD/SLV/USO/DBA + VCSH/BND/AGG and dual-report.
- **Verify:** ETF card footnotes exposure split; VCSH identical class in both maps (grep).

## Subagent-refined (verified file:line)
- **QW-ETF-1 mechanics:** rename daily outputs to `daily_profit_factor/daily_win_rate` + `stats_basis:"daily_bar_upper_bound"` in `ac_breakdown` (`dashboard_generator.py:15482-15492`); copy intrabar (`:6096-6102`) into the row as primary when `intrabar_n>=30`. Template already renders intrabar `display_pf`, so UI contract is unchanged.
- **Refresh `etf_daily_ohlcv` (M, 1d):** only writer is monthly `.github/workflows/beta-portfolio-refresh.yml:9-10,60` (6 tickers, `continue-on-error` masking failure `:46-85`). Extract ingest to `tools/refresh_etf_daily_ohlcv.py` (pattern: `tools/refresh_daily_prices_yf.py:52-84`, gap-fill upsert, `--dry-run`), universe from `config.py` `ETF_SYMBOLS` (`:921-1029`), weekly cron **without** continue-on-error. Consumers silently on Oct prices: `tools/tactical_rotation_tracker.py:63`, `tactical_blend_tracker.py:23`, `beta_portfolio_tracker.py:85`.
- **Guardian gap (S, 3h):** `db_freshness_check.py` (`:36-61,462-468`) never grades OHLCV tables — add `check_daily_ohlcv` (MAX trade_date; GREEN ≤4d, RED >7d) for `etf_daily_ohlcv`/`equity_daily_ohlcv`. It will report RED today; that's the alarm working.
- **IGIB/VCSH split — concrete fix (S, 2h):** `asset_class.py:28-35` has IGIB as BOND; `config.py:1027-1028` lists VCSH+IGIB as ETF; VCSH is in no `asset_class.py` set → equity default. Decide BOND: move both into `config.py` BOND_SYMBOLS (`:1035-1052`, VCSH short / IGIB intermediate), add VCSH to `asset_class.py:28-35`. `etf_strategies.py:193,532` unions both sets, so strategy coverage is not lost. No historical backfill in this win.
- **Exposure tagging (refines QW-ETF-4):** add `EXPOSURE_MAP` beside `asset_class.py:37-53` (GLD/SLV→commodity_metals, USO→commodity_energy, DBC/PDBC/GSG→commodity_broad; codebase already agrees at `etf_strategy_harness.py:86-87,272`); stamp `exposure_class`, accumulate `ac_exposure_pnl` in `ac_breakdown` (`:15436-15481`), emit `performance.by_asset_class.ETF.exposure_breakdown`. Primary class stays ETF — deliberately no risky reclassification.
- **Same-bar AMBIGUOUS (S, 4h; refines QW-ETF-2's hunt):** BUY branch checks TP at `forward_validator.py:1283-1285`, SL only in `elif` (`:1287`) — both-touched bars always book TP_HIT; mirror guard needed in SELL (`:1304-1316`). Fix: both touched → `AMBIGUOUS_SAME_BAR`, PnL 0/excluded. Ship with QW-ETF-1 relabelling so the WR drop is explained in the same release. Intrabar lane untouched (reference: `tools/build_intrabar_truth_by_class.py:57-58`).

## QW-ETF-5 · Stop filling half the active page with failing ETFs (S, config)
- **Problem:** 10/20 displayed picks are ETF at scores 15–20 (below the class's own 35 minScore in `asset_class_summary.thresholds`), `smartCount=0`, thresholdPass=false — yet displayed.
- **Fix:** Enforce the published minScore as a display floor (or lower it openly); below-floor picks go to a research tab, not the main panel.
- **Verify:** Active panel contains only ≥floor picks per class; counts reconcile (QW-ALL-5).

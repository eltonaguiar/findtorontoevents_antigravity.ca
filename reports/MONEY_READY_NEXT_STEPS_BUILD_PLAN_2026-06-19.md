# Money-Ready — Next-Steps Build Plan (2026-06-19)
**Author:** claude-opus · **Inputs:** deep-dive fleet synthesis + 2 new pre-registered backtests + 5-lane infra-scoping workflow (`w7xjjdkyc`, verbatim-quoted) + 2-model peer review (:4000) · **Companion:** `reports/DEEP_DIVE_FLEET_SYNTHESIS_2026-06-19.md`

## Headline finding (P1 — a SECOND silent freeze)
**`daily_prices` has been silently frozen since 2026-04-29 (~7 weeks).** Its writer endpoint `fetch_prices.php` returns **HTTP 404 at both paths** the crons call (verified live 2026-06-19). The workflow parsed the 404 body to `fetched=0` and reported **"All tickers up to date"** → green exit. Same masked-failure pattern as the 6-day `at_signal_outcomes` freeze fixed earlier this session, but ~8× longer. This gates H-126 (equity reversal needs fresh + full-universe daily prices).

- **SHIPPED (`9f501250`):** `daily-price-refresh.yml` now fails-hard on non-200 / non-JSON from `fetch_prices.php` (distinguishes a dead endpoint from a genuine "up to date"). The 7-week silent freeze now turns CI **red**, not green.
- **OPERATOR FOLLOW-UP (restores the data):** the endpoint object is gone — either FTP-redeploy `fetch_prices.php` to the 50webs `findstocks` host, OR rewire `scripts/api_integrations.py` (keyed FMP/Finnhub/Tiingo fetchers, full universe) into the workflow with `tools.db_env` creds. Not done here (needs FTP/operator + independent verbatim verification per the diff-fabrication rule).

## What was SHIPPED this turn (verified, on main)
| Commit | Change |
|---|---|
| `bd92a81e` | H-130 + H-131 crypto-funding hypotheses **REFUTED** in registry (see below) |
| `9f501250` | `daily-price-refresh.yml` masked-green **unmask** (the 7-week freeze) |
| `ddb5326c` | `/audit` "R:R Truth" daily-resolution caveat (prior turn) |
| `3b266752` | H-126..H-131 registered as forward-shadow (prior turn) |

## New backtest verdicts (pre-registered, real first-touch, this turn)
- **H-130 crypto funding mean-reversion — REFUTED.** n=143, net@16bp PF **0.64**, CI-LB **0.40**, WR 28.7% (SL hit 102 vs TP 41). Contrarian LONG on negative-extreme funding loses — price keeps falling, 1% SL triggers before 2% TP. Conc FETUSDT 37.8% (>35%). IS/OOS 0.62/0.65.
- **H-131 crypto funding carry — REFUTED.** n=1480, net PF **0.84**, CI-LB **0.62**, WR 43.9%. Underlying LONG-perp drift −0.021%/trade (down); tiny carry never offsets price + 16bp.
- **⚠️ Data caveat (feeds Lane 5):** `crypto_ohlcv` 1h dense coverage is only **~181 days** (2025-12→2026-06), a single negative-funding regime. Both verdicts are valid for available data but window-limited; a definitive multi-regime test needs OHLCV history backfilled. Both FDR families CLOSED (no variant-fishing); added to do-not-relitigate.

## The 5 infrastructure lanes (workflow-scoped, verbatim-anchored)
> **Guardrail (CLAUDE.md):** every lane below is a PLAN. Before any code-diff PR, one independent agent must re-quote the verbatim pre-change lines (the ~9% diff-fabrication rule). Backup to `ejaguiar1_backups` before any table mutation. Never wrap the collector step in `|| true` (masked-failure). All hypotheses pre-registered (M-107) before backtest — H-127/130/131 already on main.

### Lane A — COT DB landing → H-127 (COMMODITY) · MED · data-mutation
- **State:** no COT table (`SHOW TABLES LIKE '%cot%/%cftc%/%commit%'` → NONE). 3 disk-only fetchers: `tools/cot_fetcher_socrata.py:65` (`fetch_cot(...)`), `tools/cftc_cot_fetcher.py:191`, `tools/cftc_cot_forex_fetcher.py:132`. Consumer to wire: `alpha_engine/commodity_cot_contrarian.py:228` (`_fetch_cftc_reports`).
- **Plan:** new `tools/refresh_cftc_cot.py` modeled on `tools/refresh_crypto_ohlcv.py` (DDL+upsert at lines 54/66/223); reuse `cot_fetcher_socrata.fetch_cot` parsing; table `cftc_cot_weekly` **UNIQUE(cftc_contract_market_code, report_date)** (prior-Tuesday data-date key = the documented COT timing-leakage guard, `reports/cot_timing_leakage_audit_2026-05-13.md`). Weekly GHA (`cron '0 12 * * 6'`, Sat after Fri release). Then wire `commodity_cot_contrarian.py` to read the table (Wire-Up Rule).

### Lane B — fx_signals SL/TP=0 → FOREX measurement integrity · LOW · no mutation needed
- **Root cause (FOUND):** writer `findforex2/api/seed_signals.php:102` inserts only 7 of 11 columns, never sets `stop_loss_price`/`take_profit_price`/`score`; schema (`schema-baseline.sql:1982`) defaults them `NOT NULL DEFAULT 0` → **585/585 rows sl=0/tp=0**.
- **Key:** no in-repo resolver consumes the stored sl/tp (`backtest.php:107` derives them at runtime from `entry_price*(1±pct)`). So the artifact is only harmful if someone runs honest-first-touch on the *stored* columns.
- **Fix (reader-side, no live PHP change):** any fx_signals resolver MUST derive sl/tp from `entry_price` + a parameterized %, never the stored zeros. **Documented here** so future agents don't re-flag or mis-resolve. (Optional, only if persisted sl/tp ever needed: extend `seed_signals.php` INSERT + FTP-deploy + backfill — operator.)

### Lane C — stale equity writers → H-126, H-002 · MED · data-mutation
- **daily_prices:** the 404/masked-green above (unmask shipped; endpoint restore pending).
- **alpha_earnings / stock_earnings / alpha_fundamentals:** **NO in-repo writer exists** (frozen 2026-04-27; data was external/manual). `alpha_engine/fundamentals_fetcher.py` (FundamentalsRecord) + `alpha_engine/earnings_calendar_fetcher.py` produce matching fields — author/wire an UPSERT + schedule. Backup tables first.

### Lane D — PEAD shadow collector → H-002 · MED · no mutation
- **Diagnosis (NOT a bug):** `equity_pead_strategy.py:39` `_DRIFT_MAX_DAYS=3`; runs mid-June (inter-quarter gap) → all 21 cached tickers 23-67 days past earnings → 0 signals → 0 durable rows. Persist code (`tools/pead_shadow_runner.py:106`) is correct.
- **Plan:** widen `PEAD_DRIFT_MAX_DAYS` to ~10 for the shadow logger (academic drift window is 30-60d); fix earnings breadth (verify `FINNHUB_API_KEY`; cache is 21/498 yfinance-only); add a non-fail-open watchdog (replace `pead-shadow-collector.yml:69` `git add ... || true`); naturally re-accrues from ~mid-July (Q2 season). `stock_earnings.earnings_date` is 100% NULL → use `stock_fundamentals.next_earnings_date` (91/119 populated) only as a *scheduling* hint, never to retro-anchor.

### Lane E — crypto funding DB landing → H-130/H-131 re-test · MED · data-mutation
- **State:** no funding table; disk-only (`tools/funding_rate_collector.py:42` JSONL, 5×172 rows; `funding_rate_scanner.py:294` JSON).
- **Plan:** new `crypto_funding_rate` (symbol, `funding_time_ms` BIGINT aligned to `crypto_ohlcv.timestamp`, funding_rate, UNIQUE(symbol, funding_time_ms)); add `--to-db` path to `funding_rate_collector.py` (reuse `fetch_funding`/`merge_rows`); backfill 860 disk rows + paginated Binance deep-history; `funding-rate-collector.yml` cron → 8-hourly settlement-aligned.
- **Note:** only worth building if paired with the OHLCV multi-regime backfill below — H-130/H-131 are refuted on the available 181d window; a re-test needs both funding *and* multi-year 1h OHLCV.

## Peer-review next-moves (2-model :4000, corroborating + refining)
1. **Backfill 3+ yr of crypto 1h OHLCV** (currently 181d). *Highest shared leverage:* tightens the `crypto_rsi5070_us` candidate-estimate via multi-regime bootstrap **and** enables a definitive funding re-test. (Candidate-selection only — promotion stays forward-lane.)
2. **Salvage-test H-126 equity reversal on a full non-survivor / delisting-adjusted universe** with week-clustering before archiving — needs Lane C (daily_prices) un-frozen + universe widened beyond the 32 survivors.
3. **Push `crypto_rsi5070_us` to n≥120-150** via forward accrual breadth (the lead, CI-LB 0.95).
4. **FX TSMOM with inverse-vol targeting** (refines H-128) to lift net PF above the amplitude/cost floor.

## Recommended sequencing (by leverage ÷ effort)
1. **[DONE] Unmask daily-price-refresh** — stop the 7-week silent freeze. *(shipped)*
2. **Restore daily_prices ingest** (operator: endpoint or Python rewire) — unblocks the most candidates (H-126 + the whole equity book). *Highest leverage.*
3. **Land CFTC COT table + weekly collector** (Lane A) — opens the only genuinely-orthogonal untested commodity edge (H-127).
4. **Backfill multi-year crypto 1h OHLCV** (peer #1) — de-risks the crypto lead + enables a real funding re-test.
5. **PEAD window-widen + earnings breadth** (Lane D) — cheap; lets H-002 accrue from mid-July.
6. Funding DB landing (Lane E) — only after #4.

## Honest bottom line
Still **0/10 promotable**. This turn closed two more candidates honestly (funding mean-rev + carry refuted) and uncovered a 7-week silent data freeze (now failing loud). The path to a trustworthy winner is **measurement uptime + data breadth + forward-n accrual**, not more re-fishing of exhausted signals. No edge was manufactured; the verdict protects capital.

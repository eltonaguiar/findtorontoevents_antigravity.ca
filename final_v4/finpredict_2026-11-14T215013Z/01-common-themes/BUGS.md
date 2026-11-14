# Common themes — bugs & deeper investigation (final_v4)

Cross-referenced synthesis of: my own audit, the consolidated `final_v3/00_common_themes/BUGS.md` (B1–B14), quant-audit, v2/v3/v4, flaxen-hair, hilarious-seer, deepAI, and the uncommitted finpredict-v4 scoring framework.

## Bugs (confirmed defects with measured impact)

### Measurement / label integrity (highest consequence)
- **B1 — refuted strategy still "VALIDATED"** — VWAP mean-reversion is refuted in v2's and fix-p0's adjudication but still certified "Sharpe 3.76 / deploy first" in quant-audit's package. Two live files disagree; a reader of only one deploys a dead strategy. Fix: `evidence_hash` + `generated_at` on every verdict; CI fails on stale `VALIDATED`/`PROVEN` strings.
- **B2 — one class, three incompatible counts** — ETF WR 2.22% (money_ready) vs 68.42% (pf_registry) vs 44.3% (recent_closed); PF 0.022→1.788. No artifact states its cohort/filter chain. Fix: canonical cohort definition + `{cohort_id, n, filter_hash}` on every rate.
- **B5 — exit taxonomy wrong field** — `resolution_method` null on all 3,500; everything in `exit_reason`. Fix: populate `resolution_method` at resolver time.

### Data integrity
- **PnL-unit mix off 100×** — `dashboard_generator.py:8065-8072` `×100` heuristic misclassifies fraction vs percent. Flaxen-hair recomputed 93 rows (47 ratio / 32 percent / 14 off). Fix: explicit `pnl_source` unit column.
- **EXPIRED→WON mislabeling** — `PNL_WIN_THRESHOLD=0.00001`; dashboard WR 78.9% vs raw 39.4%. Fix: require `exit_price` present + real fill.
- **Frozen prices as 0%** — `fetch_prices.php` 404 since 2026-04-29; 19/20 active picks `pnl_pct==0`. Fix: quote-provenance `{LIVE,LAST_CLOSE,STALE,UNQUOTED,PLACEHOLDER}` + `pnl=null` when unquoted.
- **Zero-entry rows** — `prediction_market_consensus.py:589` `or 0` coercion.
- **Dedup / ghosts** — 22,947 ghost rows; 2,267 inverse-mutation zombies; 248 duplicate-id groups. Fix: economic dedup key + void-quarantine (never DELETE).

### Resolver / execution
- **B3 — crypto late stop-fills** — 1.54× planned risk = 98.8% of class loss, 94% from one system. **FIXED today** (`stop_fill.py`, 20 tests).
- **B4 — phantom stop-outs** — 40–56% of non-crypto `SL_HIT` never touched the stop. **UNEXPLAINED**.
- **`scanner.py:2942` `KeyError:'LONG'`** — ~93 crashes/day (fixed in my `fix/audit-p0-truth`).

### ML
- **Target leakage** — `gatekeeper.py:170-186` (indices 5/6/19/30); masking now ON-by-default (`d8c8dd25581`).
- **Inverted confidence** = data bug (ML code sound).
- **Horizon harness 0/6 (n≥60), 0/26 (n≥30)** pass; 0 backtest↔forward overlap.

### Frontend
- **`dashboard_enhancements.js` parse-broken since 2026-10-04** (malformed ternary) — the Edge/Track/FWD layer was dead. Fix exists (`fix/audit-js-syntax-and-deploy-guard`).
- **WR>100% in `summary_picks`** (INDEX 1141%, FUTURES 364%).

### GitHub Actions
- **Python 3.14 masquerade** — 197 workflows `update-environment:false` → `pandas==2.1.4` source-build fails.
- **Cron saturation** — audit-dashboard p50 97.2 min vs 60-min cron; 56.6-min FTP step.
- **Playwright 1.58.2 vs `ubuntu26.04-x64`**; 100 MB `wrong_guesses_log.json`; pandas `ME` frequency.

## Deeper investigation (unresolved, high value)

1. **B4 phantom stop-outs** — why do 40–56% of non-crypto `SL_HIT` rows show the stop never touched? Suspect a resolver default, not market behavior. Needs row-level replay.
2. **PnL-unit writer attribution** — which writer (forward_validator vs resolver vs dashboard_generator) wrote fraction vs percent. Add `pnl_source` and bisect.
3. **Bear-inclusive benchmark-relative test** — every "edge" (trend, carry, VWAP, RSI2) must be re-tested vs buy-and-hold/SPY on a window that includes a real bear. 0/40 trials pass so far.
4. **11 FOREX phantom provenance** — exit UNKNOWN + pnl 0 + exit==entry; hard delete vetoed, quarantine first.
5. **3 divergent data stores** — SQLite (129 rows) vs MySQL (90,523) vs JSON. Pick `at_signal_outcomes.intrabar_pnl_pct` as canonical.
6. **mutual_fund_ranker.py untracked prototype** (`mutut` typo) — either build honestly or de-advertise.

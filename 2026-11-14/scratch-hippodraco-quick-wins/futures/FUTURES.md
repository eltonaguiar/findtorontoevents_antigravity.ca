# FUTURES Quick Wins
Audit: §4.1 — intrabar PF **1.09 / WR 42.3%** (n=52) INSUFFICIENT_DATA (second-best honest number after COMMODITY); but DB outcomes stale since **2026-10-31**, `trading_picks` FUTURES since 2026-11-04, only 1 displayed active pick (ES=F, score 56, current==entry → fake 0.0%). PnL is % of price — no contract multiplier/margin economics.

## QW-FUTURES-1 · Restart the futures outcome lane (S–M, investigate first)
- **Problem:** FUTURES is the only class whose DB lane simply stopped (Oct 31) while other classes resolved into Nov 14. A promising class is flying blind.
- **Fix:** Find why futures resolution stopped (symbol mapping for `=F` continuous contracts is the prime suspect — same `=F` handling implicated in QW-BOND-3 and COMMODITY misclassification); add FUTURES MAX(closed_at) to the freshness guardian with a 24h gate so it cannot silently die again.
- **Verify:** New FUTURES outcomes land; guardian shows the lane; 2 weeks of accrual before any verdict change.

## QW-FUTURES-2 · Contract-economics PnL (M)
- **Problem:** % -of-price PnL on ES=F/GC=F/CL=F ignores point value/multiplier and margin — a 1% ES move ≠ 1% GC move in dollars or risk. Cross-symbol futures PF aggregation is therefore apples-to-oranges.
- **Fix:** Quick subset: attach `contract_multiplier` + `tick_value` metadata per root symbol (static table), publish `pnl_points` and `pnl_usd_per_contract` beside `pnl_pct`; aggregate futures PF on per-contract USD, not %.
- **Verify:** ES vs GC fixture picks produce correct USD figures; class PF republished on USD basis with the delta disclosed.

## QW-FUTURES-3 · Session/timezone-correct resolution (M, shares QW-ETF-2 audit)
- **Problem:** Futures trade ~23h with exchange sessions; daily-bar TP-before-SL plus UTC-naïve timestamps (generator `:8185-8223`) can resolve against the wrong session's bar — a plausible contributor to odd class numbers.
- **Fix:** Resolve futures on exchange-session bars (CME calendar), store `session_date`; excludeGlobex-overnight ambiguity via the existing `intrabar_ambiguous` flag.
- **Verify:** Sampled ES=F rows: exit bar belongs to the correct session; ambiguous share published.

## Subagent-refined (verified file:line)
- **One `=F` classifier (M, 8h):** `asset_class.py:138-139,213-215` says FUTURES; `config.py detect_asset_class` checks COMMODITY (`:1111`) before FUTURES (`:1119`) while `config.py:865-890` tags GC=F/SI=F `cat:commodity` and `:899-917` lists them as FUTURES. Make `asset_class.py` authoritative, move the `=F` check above commodity in `config.py:1118-1120`, de-duplicate `config.py:904-905,917`; parametrized contract test over every `=F` key. New picks/WF only, no closed-row backfill.
- **Per-class freshness (M, 8h):** guardian uses ungrouped maxima (`db_freshness_check.py:258-262,310-315`) — add `check_signal_outcomes_by_class` (GROUP BY asset_class) emitting per-class `minutes_stale` + STALE badge >7d. The Oct-31 FUTURES stall would have flagged on day 1.
- **WF suppression:** FUTURES `walkforward_validator.py:222` (placeholder train=3/test=2) → `min_trades=30, train=15, test=10, step=5` + INSUFFICIENT_DATA stub; `money_ready_verdict.py:155` already requires `MIN_N_CLASS=100`.
- **Benchmark quarantine:** `benchmark_closed_ledger.py:70` FUTURES→SPY becomes null/quarantined except index futures (ES/NQ/YM/RTY→SPY/QQQ via `config.py:899-917`). No `pass_95` for rates/metals futures.
- **Cost basis stamp:** `pnl_basis="price_pct_not_margin"` + post-cost PF via `cost_model.apply_costs` (FUTURES 10bp already at `money_ready_verdict.py:264`; `apply_costs` currently called only by `admissibility_pipeline.py:296` + backtests). Complements QW-FUTURES-2's full contract economics.

## QW-FUTURES-4 · Keep the class dark-but-accruing (policy, S)
- **Problem:** n=52 at PF 1.09 is a lead, not an edge (CI spans 1.0 easily); displayed ES=F pick has no live price (current==entry).
- **Fix:** No promotion until n≥200 intrabar **and** QW-FUTURES-1/2 land; fix the ES=F price lane (metals/equity-index fallback chain, QW-ALL-3) so displayed futures picks never show cloned entry prices.
- **Verify:** Verdict stays INSUFFICIENT_DATA with accruing n visible; displayed pick shows real price or `—`.

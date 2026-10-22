# Audit findings — Oct 22 2026 (Grok Bot)

## Verdict
Nothing in the live book is MONEY-READY. The mutual-fund pages exist live but their source is not in the repo, so their numbers can't be checked from it. A fund RATING system is feasible and the pilot shows signal, but the pilot is biased (survivors only, no category adjustment). Label: CANDIDATE (research).

## (a) Mutual-fund inventory
- Live pages (HTTP 200): /findmutualfunds/portfolio1/ (+ stats.html, report.html), /findmutualfunds2/portfolio2/ (+ stats/). Linked from TORONTOEVENTS_ANTIGRAVITY/index.html:1022-1028.
- Repo has only 3 debug PHP files: findmutualfunds2/portfolio2/api/{debug_navs.php, fix_dates.php, test_bt.php}. The page/backtest source isn't tracked, so its quality can't be checked from git (data/source-of-truth gap). The names `fix_dates`/`debug_navs` suggest date and NAV problems in the past (unverified).
- combined_book/fetch.py:84-100 SPLICE_MAP: VFINX, VUSTX, VBMFX(x2), FGOVX, VWEHX, FSAGX, VGSIX, PCRIX. These are return proxies used to extend ETF history, not fund ratings. Caveats: VBMFX is reused for both IEF and LQD (duration and credit mismatch). FSAGX (precious-metals equity) is a poor stand-in for GLD (bullion). PCRIX is a fair stand-in for DBC.
- No fund screener or rating exists.

## (b) Rating-system pilot (real data, yfinance, run 2026-10-22)
57 of 60 hand-picked US funds had data (FUSEX, JANSX, MFS missing). Rating window 2010–2018 monthly; forward test 2019–2025. Spearman IC vs forward monthly Sharpe:
| feature | IC | p |
|---|---|---|
| Sortino | 0.535 | <0.001 |
| Composite (Sharpe+Sortino+alpha ranks + MDD/3) | 0.468 | <0.001 |
| Sharpe | 0.449 | <0.001 |
| Max DD | 0.421 | 0.001 |
| Market-beta alpha | 0.350 | 0.008 |
Top-vs-bottom quintile forward Sharpe spread: 0.061/month, 95% bootstrap CI [0.026, 0.093]. Forward CAGR: Q5 14.4% vs Q1 13.0%.
Caveats: survivors only (dead funds missing, so results look better than they are); one split; no category adjustment (likely growth/tech style persistence); no expense ratio, tenure or flows tested; small n. UNTESTED: expense-ratio predictor, FF/Carhart alpha, category-relative rating. Script: /workspace/mfpilot/p.py.

Design: rank funds within their category. Expense ratio carries the biggest weight. Add FF5+momentum alpha t-stat (36–60m), Sortino, MDD, downside capture, rolling consistency, tenure, size and flows, and turnover. Flag persistent losers (that signal is reliable). Use CRSP-free data: yfinance NAV, Ken French, SEC N-PORT/N-CEN (expenses, holdings), and SEC dead-fund lists to reduce survivorship bias. Evaluate as ranking only: rolling OOS IC, decile spread with CI, and hit rate of top decile vs category median.

## (c) Root causes (ranked)
1. Measurement bugs: resolver stamps run time as exit time (batch closes, PR #749); 0.0% placeholder exits; MAX_CLOSED_PICKS=3500 cap truncates history.
2. Unverified red flags reported by another agent (raw tables not available to me; not quantified): QUBT 100% WR over 301 trades; EQUITY shorts averaging +9.9%/trade; at_signal_outcomes 999999.9999 sentinel (SHIBUSDT) labelled COMMODITY. These look like exit=target stamping or duplicates, a short-side sign error, and sentinel contamination plus asset-class misclassification. Locally, the string 999999 appears 14x in hyro_pick_performance.json and 183x in dashboard_data.json; those hits look like default/rank fields, but each needs checking. Fix: query `SELECT COUNT(*) ... WHERE ABS(pnl_pct)>1 OR exit_price>=999999`, then recompute PF and averages with those rows excluded.
3. Lookahead: VIX rotator.
4. Overfitting: hundreds of variants (254 rankings in backtest_results), and DSR doesn't count all trials.
5. Costs understated or uncited; same-bar entry.
6. No single source of truth: mutual-fund source isn't in git, plus many dashboards and JSONs.
7. Agent churn: overlapping lanes and work done in the main checkout.
8. Survivorship: proxies, and the universe built from current lists.

## Copy-trader findings

### Summary
The copy-trader feed has been **frozen since 2026-06-21 07:10 UTC**, four months ago. Every "active" pick is weeks to months old. Even when the pipeline was running, it lost money after a fixed bracket was applied. The data is stale and the recorded closes contain artifacts, but the main problem is structural: no edge.

All figures come from `eltonaguiar/findtorontoevents_antigravity.ca` main @ `1c24f459efc`, read-only, on 2026-10-22.

### Pipeline
Exchange leaderboard scrapers (`copy_trader_intel/{binance,bybit,bitget,bingx,copin,coinglass}_scraper.py`, `multi_asset_copytrader_scraper.py`) → `consensus_pick_builder.py` → `copy_trader_intel/data/{highscore,clone,consensus}_active_picks.json` → `outcome_resolver.py` plus `audit_trail/universal_pick_resolver.py:100-103` (SYSTEM_SOURCES) → `audit_exports/closed_copy_trader_highscore.csv` → /audit.
Workflows: `copy-trader-intelligence.yml` (cron 7,52 * * * *), `copy-trader-forward-test.yml` (:17 hourly) and `copytrader-tracker.yml` (every 2 h).

### Evidence
| Item | Finding |
|---|---|
| Last data commit | `copy_trader_intel/data` 2026-06-21 07:10 UTC. `highscore_active_picks.json` 2026-06-21 04:53 UTC. Nothing since, though the crons say hourly. The workflows are failing or disabled. |
| consensus_active_picks.json | 0 picks (generated 2026-06-21). |
| active_picks.json (copy_trader_intel source, resolver line 100) | **Missing** on main. The resolver reads a file that doesn't exist. |
| highscore_active_picks.json | 106 "active" picks with entries 2026-03-19 → 2026-05-24, never resolved. 98 SHORT / 8 LONG. |
| clone_active_picks.json | 93 picks, entries 2026-03-19 → 2026-05-08. **66 duplicate symbol+direction rows.** |
| Closed CSV (`audit_exports/closed_copy_trader_highscore.csv`, frozen 2026-05-23) | n=283, 93 wins / 190 losses, **PF 0.85**, mean −0.195%/trade. 256 SHORT / 27 LONG. timeframe = UNK for all 283. |
| Exit distribution | −2.0% ×166, +3.5% ×79. A fixed SL −2% / TP +3.5% bracket decides nearly every outcome. The bracket needs a win rate above 36% to break even, and the system wins 33%. |
| highscore_closed_picks.json | n=29, WR 41% (12/29), PF 0.98. 17 SL_HIT / 12 TP_HIT. Median hold 210 h. |
| Batch-close artifact | **21 of 29 closes are stamped 2026-03-28T06:18** and 7 at 2026-03-26T11:22. The resolver stamps its run time, not the actual hit time (`universal_pick_resolver.py:1035` `now = datetime.now(...)`, the PR #749 issue). With ~200 h holds checked in batches, intrabar SL/TP order is unknowable. |
| Who is copied | Notes such as `Trader:lb_None WR:95.7% PF:99.99`. 18 of 29 closed picks come from trader `lb_None` (identity lost). PF is capped at 99.99, so a trader with no losses is treated as perfect. This is a leaderboard ranked on past ROI: survivorship bias plus mean reversion of hot hands. |
| Lag | Picks copy the **current open positions** of leaderboard traders at scrape time, so entry happens after the trader is already in the move. The entry price is our later scrape price, not theirs. There is no check on position age. |
| Silent failures | 32 bare `except:` blocks in `bybit_scraper.py` + `binance_scraper.py`. A failed scrape leaves the old cache in place, and stale picks persist. |
| Direction skew | 90% SHORT in highscore. Any short-sign bug would dominate. The other agent's flag of "EQUITY shorts avg +9.9%" and the 999999.9999 SHIBUSDT sentinel live in at_signal_outcomes, not in these copy-trader files. I didn't verify the sign path for copy-trader shorts; they need checking. |
| Live /audit | Loads `alpha_engine/data/active_picks.json` and `rapid_fire_data/active_picks.json` from raw.githubusercontent main. Its copy-trader text ("Copy Trader Edge", "≥55% forward WR on ≥5 trades") promotes strategies on n≥5, which is far too small. |

### Ranked root causes
1. **No edge (structural).** PF 0.85 on n=283 under a fixed −2/+3.5 bracket. Copying leaderboard snapshots late, with survivorship-ranked traders, shows no edge after the fact. It belongs on the kill list, as proposed.
2. **Stale feed.** Workflows have been dead since 2026-06-21. The resolver source `active_picks.json` is missing and consensus is empty. The "active" picks are 5–7 months old.
3. **Measurement artifacts.** Batch-close timestamps (21/29 in one minute), unknown intrabar order, 66 duplicate clones, PF 99.99 caps, `lb_None` identity loss, timeframe UNK.
4. **Latency and entry.** Entry is at our scrape price after the trader has moved. Position age and slippage are not recorded.

### What would need to be true for copy-trading to work
- Copy only positions opened in the last 15 minutes or less, with the source trader's entry price recorded. Skip if our entry differs from theirs by more than 0.3%.
- Rank traders on out-of-sample forward PF with n≥50, and exclude PF caps and anonymous `lb_None` traders.
- Exit when the copied trader exits, not on a fixed bracket. Model costs at 1× and 2×.
- Use real hit timestamps from bar data, and dedupe by trader+symbol+direction.


## (d) Plan
- 30d: fix the resolver, sentinels, short sign and dedupe; recompute the board; freeze the 54-pair kill list. Paper-test MRBB+200d (OOS n=487, PF 1.84, CI 1.44–2.38, MDD 8.9%) and IBS<0.15+200d (n=775, PF 1.63) against all gates.
- 60d: build the fund rater (prompt below), rolling OOS test, add dead funds.
- 90d: promote only those passing the gates. Contingency: if it fails, go to a passive core plus the rater as a screen.
Gates: n>=100, PF>=1.5, CI lo>=1.2, WR>=50 (hidden n<20), MDD<=20%, MC>=95, DSR>0.95, PF>=1.3 at 2x costs, top symbol<=30%. Labels: MONEY-READY / CANDIDATE / FAIL.

## Agent prompt (fund rater)
```
Build a mutual-fund RATING system (ranking, not trading). Repo eltonaguiar/findtorontoevents_antigravity.ca.
- git worktree add ../wt-fundrater origin/main -b fundrater/v1. EVERY command: cd <worktree> && pwd && <cmd>. Never touch the main checkout or stashes.
- Code in fund_rater/ (no /tmp). Data: yfinance NAV (monthly), Ken French FF5+MOM (reuse combined_book/fetch.py), SEC N-CEN/N-PORT for expense ratio, turnover and assets. Include dead/merged funds where obtainable; list the missing ones.
- Universe >=300 US funds with Morningstar-style category. Features per fund over trailing 36-60m: expense ratio, FF5+MOM alpha t-stat, Sortino, MDD, downside capture, rolling-12m consistency vs category, tenure, size, flows, turnover. Rank within category.
- Evaluate rolling OOS (rate at t, measure t+12m category-relative alpha): Spearman IC per year with mean and t-stat, top-vs-bottom decile spread with bootstrap CI, top-decile hit rate vs category median. Report each feature alone and the composite. Count every variant tried (DSR).
- Validation: a re-run gives identical numbers; random scores give IC≈0; an expense-only baseline is reported.
- Contingency: if the composite doesn't beat the expense-only baseline OOS, say so and ship the expense+loser-flag rater. If category data is missing, report that and use returns-based style clustering.
- Label CANDIDATE/FAIL only. Open ONE PR, do not merge.
```

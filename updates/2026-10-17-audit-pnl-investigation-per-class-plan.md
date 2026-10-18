# 2026-10-17 — Why /audit PnL "looks bad": investigation, simulations, and the per-asset-class strength plan

Date: 2026-10-17 (payload snapshot `dashboard_data.json` generated 2026-10-17T23:16Z)

## 1. Verdict on the PnL perception — where "bad" comes from

Windowed realized PnL over the 3500 recent-closed picks (per-pick `pnl_pct`):

| window | n | WR | Σ PnL% | mean | avg win | avg loss | PF |
|---|---|---|---|---|---|---|---|
| 7d | 672 | 46.2% | **+23.7** | +0.035 | +3.48 | −3.02 | **1.02** |
| 14d | 1040 | 46.2% | +640.0 | +0.615 | +4.77 | −3.06 | 1.40 |
| 21d | 1260 | 46.8% | +746.8 | +0.593 | +4.64 | −3.05 | 1.38 |
| 30d | 1617 | 46.2% | +1028.9 | +0.636 | +4.98 | −3.16 | 1.39 |

The book is **profitable over 14–30 days (PF ≈ 1.4)** but the **last 7 days are
essentially flat (PF 1.02)** — that recency is what makes PnL "seem very bad",
plus the earlier-confirmed 0.00% active rows (verified genuine after-hours
flats, not stale) and 53 fabricated zero rows (healed by the resolver fix).

Per-class 14d exit economics isolates the bleed:

| class | n | avgWin | avgLoss | PF | exp% | SL:TP |
|---|---|---|---|---|---|---|
| CRYPTO | 866 | +5.04 | −3.16 | **1.44** | +0.73 | 345:295 |
| EQUITY | 67 | +3.82 | −4.00 | 1.02 | +0.04 | 27:17 |
| FOREX | 56 | +1.13 | −0.41 | **5.16** | +0.28 | 7:15 |
| ETF | 41 | +2.45 | −1.71 | **0.40** | **−0.80** | **29:7** |
| COMMODITY | 9 | +3.25 | −2.37 | 2.29 | +1.02 | 4:5 |
| FUTURES | 1 | +14.94 | 0.00 | ∞ | +14.94 | 0:1 |

**Root cause of the recent bleed: ETFs.** ETF stops hit 29 times vs 7 targets
(a stop-dance — SLs too close to entry relative to normal noise, or entries
chasing), losing −0.80% per trade. EQUITY is barely break-even (PF 1.02).

## 2. Do top scores win? (scores vs PnL)

Closed picks bucketed by `score`:

| score bucket | n | mean PnL% | non-negative rate | Σ |
|---|---|---|---|---|
| 0–30 | 131 | **−1.380** | 13.0% | −180.8 |
| 30–50 | 2771 | +0.229 | 45.1% | +633.7 |
| 50–70 | 530 | +1.598 | 52.3% | +846.9 |
| 70–90 | 68 | **+3.952** | 94.1% | +268.7 |

Spearman(score, pnl) = **+0.093** (n=3500): monotonic in means (the score does
rank picks correctly) but weak overall — because the 0–30 junk bucket and the
under-floor actives still flow through to the feed.

## 3. Simulation — apply the production per-class score thresholds

Gate: `score >= asset_class minScore` from `asset_class_summary.thresholds`:

| class | thr | n | WR | mean | Σ | PF |
|---|---|---|---|---|---|---|
| CRYPTO | 65 | 141 | 82.3% | +4.29 | +604.2 | **7.24** |
| EQUITY | 40 | 241 | 51.0% | +0.66 | +158.5 | 1.33 |
| FOREX | 40 | 62 | 48.4% | +0.19 | +11.5 | 1.80 |
| COMMODITY | 30 | 9 | 55.6% | +1.02 | +9.2 | 2.29 |
| FUTURES | 45 | 1 | 100% | +14.94 | +14.9 | ∞ |
| BOND | 35 | 25 | 28.0% | −0.35 | −8.7 | **0.41** |
| ETF | 35 | 423 | 46.3% | +0.17 | +72.6 | 1.16 |
| **ALL GATED** | — | **902** | **53.0%** | **+0.956** | **+862.3** | **1.81** |

Readings (generally accepted profitability principles applied):
- The gated pool satisfies expectancy > 0 (PF 1.81, WR 53%, mean +0.96%):
  thresholded picks ARE "top notch"-grade — but SMART PICKS shows **0**
  because every class also fails its `minForwardWR`, so gating never surfaces.
- **BOND fails** its own gate (PF 0.41): today's bar approves a losing book.
- ETF's floor (35) admits far too much of the stop-dance bleed (PF 1.16).
- CRYPTO at the current bar is the flagship (PF 7.2).

## 4. Stale trading-prediction blocks (root-caused)

| block | frozen since | age |
|---|---|---|
| `predictions_leaderboard` (all 222 rows, last_active) | 2026-02-28 | 201d |
| `analyst_active_calls` + `analyst_leaderboard` | 2026-03-26 | 235d |
| `walkforward` | 2026-04-15 | 185d |
| `ml_health` | 2026-05-25 | 145d |

Root causes:
1. **`.github/workflows/analyst-tracker.yml` dead job (FIXED in this commit).**
   `on.schedule` defines `15 */4` (scrape) and `0 * * * *` (hourly validate),
   but `validate-prices.if` compared `github.event.schedule` against
   `'*/15 * * * *'` — a cron string that no longer exists. Every hourly run
   therefore skipped BOTH jobs (run conclusion `skipped`, all recent runs),
   so the validate/refresh path never executed again after the cron edit.
   Fix accepts the real `'0 * * * *'` string.
2. Scrape job itself runs green every 4h but has produced **no new rows since
   Feb/Mar** (nothing changes → `git diff --staged --quiet` → no commit):
   contributor sources aren't returning new predictions (feed/key/ToS
   investigation — P1).
3. Leaderboard data quality independent of staleness: 138/222 rows show 100%
   WR on <40 predictions, sharpe = 0 on 220/222, 214 rows UNRANKED — the
   panel is mostly tiny-sample noise presented as performance.

Fresh blocks confirmed OK: `data_freshness` (0.6h), `smart_picks_feed` (1.6h),
`research_reports`, `kill_switch` (12h), dashboard builds ~hourly.

## 5. GitHub Actions health (this session)

- Latest run per workflow: 136 workflows — **122 success**, 10 in-progress,
  3 pending, 1 skipped (the analyst-tracker cron-string bug above); 0 failures.
- Job-level: every job in all 123 latest completed runs is
  success/skipped/neutral.
- Stale failures / chronic cancellations / recurring failures / stalled >90min
  runs (500-run window): 0. 0 annotations on last 8 main commits.

## 6. The plan

### P0 — shipped now (this branch / PR)
- Resolver: no fabricated 0% exits; heals prior fabrications on load; MySQL
  skip-guard for NULL PnL (fixes FOREX's 22%-zero contamination and the
  TP/SL-at-0 impossibilities once the cron rebuilds from `main`).
- `_enrich_live_pnl`: fetched-first live quotes; carried price = fallback only
  (removes the structural active freeze trap).
- `combined_confidence_strategy`: no WR% displayed at 0 trades.
- `analyst-tracker.yml`: hourly validate job un-dead.
- (Already live via FTP from earlier: Quick Add cross-platform parsers,
  thumbnail proxy whitelist.)

### P1 — next (needs operator preregistration where strategy params change)
1. **ETF stop discipline**: 29 SL : 7 TP over 14d. Audit `adaptive_tp_sl`
   sl-distance vs per-symbol ATR for ETFs; candidates — widen SL (ATR-based),
   halve size at equal SL, entry de-chase (skip entries >0.3% from signal
   close). Mitigation only until walkforward-validated (M-107 prereg).
2. **BOND delist-or-raise**: current floor approves a PF-0.41 book. Raise
   `minScore`/`minForwardWR` or suspend BOND emitters until n≥30 recovery,
   mirroring the kill-switch criteria (min_wr 0.45 / min_pf 1.0).
3. **Surface the gated book**: Smart Picks requires minScore AND
   minForwardWR; shown data says the score gate alone yields PF 1.81 — either
   refresh `forwardWR` inputs ( resolver coverage, below) or split the badge
   into "score-pass" vs "full-pass" so strength is visible instead of 0/0.
4. **expired_no_pnl coverage**: 3280/4098 picks (CRYPTO 84%) die unresolved —
   extend the universal resolver to those emitters so natural TP/SL/time
   exits produce real PnL; this is the credibility lever for every class's
   forwardWR.
5. **Leaderboard hygiene**: rank by Wilson lower bound with min 30
   predictions, demote tiny-sample 100% WR rows to UNRANKED headline-less,
   and investigate why contributor sources stopped producing rows since Feb.

### P2 — infrastructure (top-notch predictions per class, ongoing)
- Freshness guard for payload blocks: extend `data_freshness`/db-freshness
  guardian to `predictions_leaderboard`, `analyst_*`, `walkforward`, `ml_health`
  (CI fails or the UI badges them STALE instead of presenting old data as live).
- Track Spearman(score, pnl) per class in CI as a ranking-quality KPI
  (current book-wide +0.093; goal: increasing, per class).
- Enforce expectancy gates in the promotion pipeline: PF≥1.0 and n≥30 already
  exist in kill-switch; apply the same per class to *active* emitters, not
  just strategies (BOND would have been caught).
- Keep smart picks honest rather than lowering floors: the gated-simulation
  numbers above are the target bar (WR ≥ 53%, PF ≥ 1.8 on the gated pool).

## Verification
- `python3 -m py_compile` on all three Python files touched today: pass.
- Resolver heal harness: 900 fabricated rows healed, 0 remaining.
- `node --check` bundle + `quick_add_url_test.js`: all assertions pass.
- All windowed/`score`/gating numbers computed directly from the production
  `dashboard_data.json` snapshot cited above; GH numbers from
  `gh run list` (500-run window) + job-level `gh run view` over all latest
  completed runs.
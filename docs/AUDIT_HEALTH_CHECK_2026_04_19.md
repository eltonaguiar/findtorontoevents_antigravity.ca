# Audit Health Check — 2026-04-19 (window: 16:00Z 04-19 → 15:00Z 04-20)

Source: `gh run list --limit 200 --created ">=2026-04-19T16:00:00Z"`, `audit_dashboard/data/dashboard_data.json` (generated_at `2026-04-19T21:28:24Z`), `alpha_engine/strategy_blocklist.py`.

Sampled runs: **200** (API hard-cap hit — true volume in window is higher; figures below are lower-bounds on a 200-run sample).

## 1. GitHub Actions Health

| State | Count | Notes |
|---|---|---|
| success | 167 | 83.5% of sampled |
| in_progress | 18 | live at capture |
| cancelled | 10 | |
| skipped | 2 | |
| **failure** | **3** | see below |

Failure detail:

| Workflow | Run ID | Conclusion | Root cause (log tail) |
|---|---|---|---|
| Weekly score quartile spread | 24673337770 | failure | `ModuleNotFoundError: No module named 'numpy'` in `tools/analyze_audit_scores_vs_pnl.py:25`. Job `quartile-spread` did not install numpy before invoking the tool. Fix: add `pip install numpy` (or `requirements.txt` step) to that job. |
| CI Tests | 24668849369 | failure (py3.11) / cancelled (py3.12) | Logs no longer retrievable via `gh run view --log`; py3.12 cancelled suggests fail-fast on matrix. Needs rerun + fresh log capture. |

Scheduled workflows confirmed firing on schedule during the window: `audit-dashboard`, `alpha-engine-live`, `outcome-resolver-validate-unresolved-picks`, `forward-validator` family, `signal-quality-monitor`, `cross-aggregator`, `crypto-ml-edge`, `polymarket-multi-asset`, `sustained-gainer-confluence-scanner`, `claude-gainer-ml-live-scanner`, `ema-retracement-mean-reversion-scanner`. No cron misses observed in the sample. Failure rate: **3/182 completed = 1.6%** (excludes in-progress). Healthy.

## 2. Positive-expectancy, low-volume strategies (n < 15, WR ≥ 55%, avg_pnl > 0)

52 strategies match; most have n = 1 (noise). Filtering to n ≥ 6 for actionable scaling candidates:

| Strategy | System | n | WR% | avg pnl% |
|---|---|---|---|---|
| donchian-stock-breakout | kimi_riseoftheclaw | 6 | 83.3 | +7.48 |
| price-accel-scout | kimi_riseoftheclaw | 8 | 62.5 | +4.60 |

Mid-volume positive-EV (n 15–49, WR ≥ 55%, avg > 0) — stronger scaling candidates:

| Strategy | System | n | WR% | avg pnl% |
|---|---|---|---|---|
| rs-breakout-scout | kimi_riseoftheclaw | 16 | 75.0 | +2.51 |
| forex-rsi-ema-scout | kimi_riseoftheclaw | 15 | 60.0 | +0.33 |

Lower-n winners (n 2–5) with 100% WR include `ml_enhanced_APTUSDT` (n=2), `golden-cross-stocks` (n=2), and 17 singletons — too underpowered to act on without more samples.

## 3. Promotion candidates (n ≥ 30, WR ≥ 50%, zero active picks)

Only **1** match:

| Strategy | System | n | WR% | avg pnl% |
|---|---|---|---|---|
| forex_rsi2_mean_reversion | multi_asset_copytrader | 511 | 50.1 | +0.07 |

Barely-positive expectancy (+0.07% avg across 511 trades is essentially break-even on costs). Low-priority — not a slam-dunk promotion.

## 4. Inactive-despite-history (n > 50, last close > 3d)

Only **1** strategy:

| Strategy | System | n | WR% | avg pnl% | Days since last close |
|---|---|---|---|---|---|
| cta_cross_asset_tsmom | cta_replicator | 56 | 37.5 | +0.02 | 3 |

Marginal — poor WR anyway. Not actionable.

## 5. Catastrophic-drift / high-volume losers (n ≥ 100, WR < 35%)

**Zero strategies match** in the `recent_closed` window. The three RETIRED strategies already in `_RETIRED_STRATEGIES` (`fear_greed_contrarian`, `proven_propfirm_cons_prop`, `proven_triple_ema_prop`) plus the FOREX `kimi_signal_tracking/default` pair and `copy_hl_lb_None` are already being filtered — the blocklist is doing its job on the 3,500-row closed window. No new unblocked high-volume toxics detected.

## 6. Infrastructure smell tests

**Active-pick asset-class distribution** (n=26 active):

| Asset class | Count | % |
|---|---|---|
| CRYPTO | 19 | 73.1% |
| EQUITY | 3 | 11.5% |
| FOREX | 2 | 7.7% |
| COMMODITY | 2 | 7.7% |

Crypto < 90% threshold ✓ — non-crypto representation is healthier than recent history.

**Freshness:** `generated_at = 2026-04-19T21:28:24Z`. At audit time (2026-04-20T15:00Z) that is **~17.5 hours stale**, well past the 30-minute target. The `audit-dashboard.yml` workflow fired successfully within the window, so the live site may be newer than this on-disk snapshot — but if this file is what the `/audit` page serves, it is stale. **Investigate.**

**Cold-start risk:** **0/26** active picks have `strat_fwd_trades == 0`. Excellent.

## 7. Recommendations (ranked by impact)

1. **Fix `Weekly score quartile spread` numpy import** (high impact, trivial). Add `pip install numpy pandas` (or install from `requirements.txt`) to the `quartile-spread` job in `.github/workflows/weekly-score-quartile-spread.yml`. The tool `tools/analyze_audit_scores_vs_pnl.py` needs numpy; runner has none.
2. **Investigate dashboard_data.json freshness lag** (high impact). On-disk `generated_at` is 17.5h stale despite `audit-dashboard` cron firing. Either the workflow is writing a different path, or the commit/push step is failing silently. Check `audit-dashboard.yml` recent successful runs to confirm the file is actually being updated.
3. **Rerun + investigate CI Tests run 24668849369** (medium impact). py3.11 failed, py3.12 cancelled via fail-fast. Logs have aged out — rerun with `gh run rerun --failed 24668849369` and capture fresh logs.
4. **Scale kimi_riseoftheclaw scouts** (medium impact, deserves more data first). `rs-breakout-scout` (n=16, 75% WR, +2.51% avg) and `donchian-stock-breakout` (n=6, 83% WR, +7.48%) are the best signal in the book right now. Do not live-scale from n=6, but raise their daily-pick caps and watch for n=30 to confirm.
5. **Re-evaluate `forex_rsi2_mean_reversion`** (low impact). n=511 @ 50.1% WR / +0.07% avg is cost-drag territory. It has zero active picks — either demote to paper-only pending S4 re-validation, or confirm it is intentionally paused.

## Coordination note

Bus-broadcast sent on start (id `ab32053b`). No peer messages pending. Read-only, no commits.

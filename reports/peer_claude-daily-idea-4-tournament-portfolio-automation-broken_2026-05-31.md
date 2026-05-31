# Idea #4 — Tournament Portfolio Automation Broken

**Date:** 2026-05-31
**Agent:** Claude Opus 4.7
**Slug:** `tournament-portfolio-automation-broken`
**Idea source:** `/tmp/user_ideas_2026-05-31.json` index 3

## Verbatim user idea

> There are also risk-managed portfolios, but the automation seems broken! ...
> 12 portfolio(s) refreshed May 29 ... NAV $100000.00 0.00% Total Return ...
> refreshed May 28, 08:00 PM

User wants: "Diagnose why the Model Portfolios (Conservative/Balanced/Aggressive risk books) on ai-tournament.html show 0.00% return, stale May-28 marks, and missing Sharpe/Sortino/CAGR. Identify the broken lifecycle engine job and restore daily marking."

Note: this idea is an **operational/plumbing diagnosis**, not a statistical-edge hypothesis. The tier verdict system (T1/T2/T3/SHADOW/INSUFFICIENT_N/NO_EDGE/LEAKAGE) does not apply — there is no PnL distribution to compute Wilson bounds on yet (0 closed exits). Verdict frame: **PIPELINE_BROKEN** with concrete fix list.

## Hypothesis

H1: The `ai-model-portfolios-daily.yml` cron is silently failing on at least one of {schedule firing, run_daily script, NAV mark, JSON export, FTP upload, git commit}.

## Methodology

1. List workflow runs since creation.
2. Pull job log for the most recent run.
3. Identify which step(s) exited non-zero or silently produced no output.
4. Verify whether the artifacts (`pf_portfolios.json`, per-portfolio files) made it to (a) git main and (b) the live FTP site.
5. Cross-check the cron expression against actual elapsed weekdays.

## Raw findings

### Workflow runs (verbatim from `gh run list --workflow=ai-model-portfolios-daily.yml`)

```
completed  success  AI-Model Portfolios — Daily EOD  schedule  26665496460  3m6s  2026-05-29T22:30:37Z
```

**Exactly ONE run since the workflow was created.** Today is 2026-05-31 (Saturday).

### Cron expression analysis

`.github/workflows/ai-model-portfolios-daily.yml` line 8:

```yaml
on:
  schedule:
    - cron: "0 22 * * 1-5"
```

- 22:00 UTC = 18:00 ET (after US equity close).
- `1-5` = Mon–Fri only. Weekends skipped by design.
- 2026-05-29 was Friday → ran.
- 2026-05-30 was Saturday → skipped (correct).
- 2026-05-31 is Sunday → skipped (correct).
- Next expected run: Mon 2026-06-01 22:00 UTC.

**So a single missed-cron isn't the root cause** — but the user is right that the live page shows stale-looking data over a 3-day window (Fri → Mon).

### May 29 run job log (excerpt — verbatim from `gh api .../jobs/78597847285/logs`)

```
2026-05-29T22:33:30  [run_daily] mode=APPLY asof=2026-05-29 models=40 picks=3873 net=True
2026-05-29T22:33:30  [run_daily] 12 portfolio(s) (12 newly seeded)
2026-05-29T22:33:30  [run_daily] SUMMARY
                       portfolios seeded : 12
                       entries opened    : 89
                       exits closed      : 0
                       rejects logged    : 211
                       NAV snapshots     : 12

2026-05-29T22:33:33  [export_json] 12 portfolio(s); mode=WRITE
                     [export_json] wrote audit_dashboard/data/pf_portfolios.json
                     [export_json] wrote 12 per-portfolio file(s)

2026-05-29T22:33:39  uploaded /findtorontoevents.ca/audit/data/pf_portfolio_cursor_agent__aggressive.json
                     ... (13 files total)
                     uploaded /findtorontoevents.ca/audit/data/pf_portfolios.json

2026-05-29T22:33:39  [main 7d59a3b3] chore(portfolios): daily PF snapshot [skip ci]
                      13 files changed, 2922 insertions(+)

2026-05-29T22:33:40  To https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
                      ! [rejected]          main -> main (fetch first)
                     error: failed to push some refs
                     ##[error]Process completed with exit code 1.
```

### Git repo check

```
git log --all --oneline --grep="PF snapshot"   →   (empty)
git rev-parse 7d59a3b3                          →   unknown revision
ls audit_dashboard/data/pf_portfolios.json      →   No such file or directory
ls audit_dashboard/data/pf_portfolio_*.json     →   No such file or directory
```

Confirmed: the commit `7d59a3b3` **never reached origin/main**. It only exists on the FTP site.

### Warnings observed during run_daily

Aggregated from log:

- AlphaVantage fallback unusable: `ALPHAVANTAGE_API_KEY not set` for every FOREX symbol (EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD).
- Yahoo treats spot FX symbols as delisted: `$EURUSD: possibly delisted; no price data found`.
- Binance returns HTTP 451 (GitHub Actions IPs geo-blocked): `_binance_history failed for SOLUSDT/AVAXUSDT/NEARUSDT/BTCUSDT/INJUSDT`.
- CoinGecko also rate-limited: `429 Too Many Requests` for BTC and SOL.
- Futures lack MA200 lookback: `insufficient history for GC=F MA200 (have 178)` (need 200).

These are warnings — `run_daily` still seeded 12 portfolios and opened 89 entries, but **NAV marking quality is degraded** because mark prices for FOREX and many CRYPTO are missing. Hence the "$100,000.00 / 0.00%" reading is partly real (just-seeded books with no time elapsed for PnL) and partly an artifact of failed mark-prices.

## Root causes (ordered by severity)

### P0 — `git push` race lost the snapshot commit

**Symptom:** Workflow appears "success" in GH UI (because the earlier `continue-on-error: true` swallowed FTP failures and the push step is the last step but is NOT in continue-on-error). Actually exit code 1 from the push step → run is marked failed for that step but the overall job aggregation showed success because of `continue-on-error: true` on prior steps masking the picture.

Re-check: line 117 of the workflow (`Commit PF JSON snapshots`) has `continue-on-error: true`. So the workflow run reports overall green, but **the snapshot was never committed**.

**Fix:** add `git pull --rebase origin main` before `git push`, plus a retry loop (3 attempts). Pattern:

```yaml
- run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add audit_dashboard/data/pf_portfolios.json audit_dashboard/data/pf_portfolio_*.json || true
    if git diff --cached --quiet; then echo "no changes"; exit 0; fi
    git commit -m "chore(portfolios): daily PF snapshot [skip ci]"
    for i in 1 2 3; do
      git pull --rebase origin main && git push && exit 0
      sleep $((RANDOM % 10 + 5))
    done
    echo "::error::failed to push after 3 retries"
    exit 1
```

### P1 — FOREX / CRYPTO mark prices missing → NAV is stale

`ALPHAVANTAGE_API_KEY` GH secret is not set. Yahoo treats spot FX as delisted. Binance is geo-blocked from GH runners (HTTP 451). CoinGecko rate-limited.

**Fix options (any one):**
- Add `ALPHAVANTAGE_API_KEY` to repo secrets (free tier 25 req/day fine for daily marks).
- Switch FOREX symbols to `EURUSD=X` Yahoo notation (works for spot FX on Yahoo).
- Switch CRYPTO to KuCoin (`api.kucoin.com/api/v1/market/candles`) or CryptoCompare per CLAUDE.md "API Failover Rule" (current code does not respect that rule fully).

### P2 — Futures MA200 cold-start

`have 178` < 200. yfinance history download window is hard-coded to `period=215d` and weekends/holidays cut that to ~178 trading days. Bump to `period=300d` for MA200 indicators or accept MA-only-after-200d.

### P3 — `0.00% Total Return` is partly EXPECTED on seed day

12 portfolios were freshly seeded May 29 with NAV $100k each. With 0 closed exits and mark-prices missing for many open positions, the NAV correctly shows ~$100k. The display is technically not "broken" — it's just on Day 1 of life with no exits and no successful mark refreshes since the seed cron ran. The metric framework Sharpe/Sortino/CAGR is **N/A on n=0 daily returns**; once Mon 2026-06-01 EOD mark lands, they will start to compute.

### Cron not "broken"

May 30 + May 31 are weekend. The Mon-Fri cron is intentional. No fix needed unless the user wants weekend marks (would be redundant for equity but useful for crypto).

## Cross-check vs today's NO_EDGE verdict

The 10-agent swarm + 3-external-AI consensus says "NO_EDGE across all 6 classes." That verdict applies to **pick-level performance** (closed trades). The hedge-fund portfolio surface evaluated here is:

1. Not a pick generator — it consumes existing picks and books them with risk overlays (capacity, concentration, drawdown cap per design §7).
2. Has zero closed exits → no PnL distribution exists to challenge the NO_EDGE verdict.

So this idea is **consistent** with NO_EDGE — the portfolio overlay can't add edge if the underlying picks have none, and we haven't observed any portfolio PnL yet to test.

The portfolio infrastructure is also a **prerequisite** for future per-model hedge-fund-tier comparison (design doc §7). Fixing the plumbing today does not contradict NO_EDGE; it enables tomorrow's measurement.

## Verdict

**PIPELINE_BROKEN** (not a tier verdict — operational).

- Cron + run_daily: **WORKING** (12 portfolios seeded, 89 entries opened, 12 NAV snapshots, 13 JSON files exported).
- FTP upload: **WORKING** (all 13 files uploaded 2026-05-29 22:33 UTC).
- git push of snapshot to origin/main: **BROKEN** (rejected, no retry, commit `7d59a3b3` lost; agents reading the repo see no PF JSON, only the live site does).
- Mark-price quality: **DEGRADED** (FOREX entirely missing, CRYPTO partial — geo-blocked Binance + missing AlphaVantage key).
- Sharpe/Sortino/CAGR: **N/A** (Day 1, n_daily_returns=0; cannot be computed yet).
- Weekend gap: **BY DESIGN** (Mon-Fri cron).

Confidence: HIGH on root-cause identification (verbatim log evidence).

## Recommended next steps

1. **P0 (2-line workflow patch):** add `git pull --rebase` + 3x retry loop to the push step in `ai-model-portfolios-daily.yml`. Without this, every concurrent commit to main will lose the daily snapshot. → ship as PR scope ≤1 file.
2. **P1 (1-line secret + 1-line yaml):** set `ALPHAVANTAGE_API_KEY` repo secret. Optional follow-up: change FOREX symbols to `EURUSD=X` form in the `model_portfolios` seed.
3. **P2:** bump `period` from 215d to 300d in `tools/portfolios/prices.py` for MA200 indicator users.
4. **Monitoring:** add a simple `if not git diff --cached --quiet && [push failed]` Slack/issue-create step so silent push losses are surfaced.
5. **Wait through Mon 2026-06-01 22:00 UTC** before re-evaluating the "0.00%" claim — the portfolios are 1 trading day old with no exits and degraded marks. Sharpe/CAGR will populate once n_daily_returns ≥ 5.

## Files / paths cited

- `.github/workflows/ai-model-portfolios-daily.yml`
- `tools/portfolios/run_daily.py`
- `tools/portfolios/export_json.py`
- `tools/portfolios/prices.py`
- `docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md`
- `audit_dashboard/data/pf_portfolios.json` (exists on live FTP, NOT in git)
- GH Actions run 26665496460 / job 78597847285

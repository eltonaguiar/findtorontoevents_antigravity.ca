# GHA Rollout Approach — Remaining Hygiene, Reusable Workflow, Secrets, Peer PRs

**Date:** 2026-11-16
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Scan base:** `origin/main` @ `e43cb1ddd9d` (local read-only YAML scan; no API mutations)
**Task type:** design / research. No workflow files were edited, nothing was pushed, and `/home/eaguiar2015/dbpasses.txt` was not read.

---

## 0. Headline numbers (and a correction to the brief)

Authoritative scan of the **356 active** `.github/workflows/*.yml` files on `origin/main`:

| Metric | Count |
|---|---|
| Active workflow files | 356 |
| No concurrency block | **161** |
| No job-level `timeout-minutes` | **62** |
| Partial timeout (some jobs only) | 3 |
| Missing both concurrency + timeout | 51 |
| Static concurrency group (no `github.workflow`) | 153 |
| Duplicate static group names (real collision risk) | 2 groups / 6 files |

**The brief's "181 concurrency / 73 timeout" does not reproduce from the current tree.** The phase-1 report (`reports/gha_phase1_classification_report.md`, 02:50 UTC) counted 194 active no-concurrency / 92 no-timeout; subsequent hygiene commits closed 33 and 30 of those respectively. 181/73 is an intermediate/stale count. **Recommendation:** re-baseline to **161 / 62** and treat the difference as a definitions mismatch (the 181/73 figure likely also counts `.disabled`/`.retired` files or counts static groups as "no group"). Re-run the scan after each batch (command in §7).

**Cadence distribution (all 356):** daily 80, hourly 71, weekly 64, non-cron 46, `*/2h` 27, `*/4h` 26, `*/6h` 17, monthly 9, other 7, `*/3h` 3, `*/12h` 3, `*/1h` 2, `*/15m` 1.

**Two real group collisions** (static names shared across workflows — GitHub cancels same-group runs across workflows):
- `edge-stability-shared` → `edge-stability-daily.yml`, `edge-stability-refresh.yml`
- `movies-database-refresh` → `fetch-movies-v3.yml`, `kimi-fetch-movies.yml`, `deploy-movieshows-all.yml`, `fetch-movies.yml`

---

## 1. Batched rollout plan

### 1.1 Ordering principles

Risk = **cadence** (queue-stack rate) × **push-to-main** (cancel/partial-push risk) × **runtime** (timeout risk).

1. **High frequency first** — every cron tick stacks a new run; these are the queue-stackers.
2. **Push-to-main workflows get `cancel-in-progress: false`.** A new tick must not cancel an in-flight commit/push (partial push / lost data). Only idempotent read-only scanners get `true`.
3. **Timeout follows measured runtime, not a blanket value.** Default 30 min is wrong for both 5-min scanners (wastes the failure signal) and 45-min backtests (kills good runs).
4. **One branch + one commit per batch**, message `ci(gha): <what> [skip ci]`, pushed with `.github/scripts/safe_push.sh`.
5. **Never batch across risk classes.** A failed batch must revert cleanly on its own.

### 1.2 Recommended defaults

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false   # true only for idempotent, non-pushing scanners
```

| Cadence | timeout-minutes | cancel-in-progress |
|---|---|---|
| `*/15`, `*/30`, hourly | 20 | false if it pushes, else true |
| `*/2h`, `*/4h` | 30 | false if it pushes, else true |
| `*/6h`, daily | 45 | false if it pushes, else true |
| weekly / monthly | 60 | false |
| heavy backtests (`*backtest*`, `walk-forward`, `mass-backtest`) | 90–120 | **always false** |
| hard ceiling | 360 (GitHub cap) | — |

> `tools/gha_add_hygiene.py` currently hard-codes `cancel-in-progress: true` and `timeout-minutes: 30` (no CLI flag). **Extend it** to accept `--timeout` and `--cancel-in-progress` before mass use, or drive it from a small wrapper that post-edits the block. `tools/gha_add_job_timeout.py` is the per-job variant for multi-job workflows.

### 1.3 Exact batches (filenames from the `origin/main` scan)

**Batch 0 — Canary (do first, 2 workflows).** Pick two low-risk, short, already-pushing hourly scanners and convert by hand (not the helper), observe 3–5 runs, then proceed.
- `ema-retracement-scan.yml`
- `now-scanner.yml`

**Batch A — `*/15` + hourly timeout-only (highest frequency).**
- `*/15` concurrency+timeout: `torontoevent-backtest-and-deploy.yml`
- hourly timeout-only (concurrency already present): `signal-integrator.yml`, `signal-recorder.yml`

**Batch B — `*/2h` (15 concurrency + 7 timeout).**
- Concurrency: `backfill.yml`, `check-streamer-status.yml`, `daily-feed-summary.yml`, `fc-crypto-pro.yml`, `forward-signal-scanner.yml`, `kimi-feb172026-live.yml`, `kimi-goldmine-collector.yml`, `market_beating.yml`, `proven-strategies-scanner.yml`, `signal_tracking.yml`, `social-prediction-tracker.yml`, `spike-scanner.yml`, `strategy-forward-tester.yml`, `system-health-check.yml`, `update-creator-news.yml`
- Timeout only: `backfill.yml`, `check-streamer-status.yml`, `forward-signal-scanner.yml`, `kimi-goldmine-collector.yml`, `market_beating.yml`, `signal_tracking.yml`, `update-creator-news.yml`

**Batch C — `*/4h` (17 concurrency + 8 timeout).**
- Concurrency: `claude-gainer-tracker.yml`, `daily-top-picks-filter.yml`, `deploy-vetted-picks.yml`, `discord-heartbeat.yml`, `live_trading.yml`, `live_trading_canada.yml`, `master-picks-health.yml`, `ml-forward-test.yml`, `momentum-scanner.yml`, `parquet-ingest.yml`, `picks_dispatch.yml`, `rapid-validation-CLAUDECODE_Feb152026.yml`, `self_optimizing_trading.yml`, `sidecar-status-update.yml`, `strategy-health-monitor.yml`, `tv-strategy-scanner.yml`, `what-worked-insights.yml`
- Timeout only: `claude-gainer-tracker.yml`, `live_trading.yml`, `live_trading_canada.yml`, `parquet-ingest.yml`, `picks_dispatch.yml`, `rapid-validation-CLAUDECODE_Feb152026.yml`, `self_optimizing_trading.yml`, `tv-strategy-scanner.yml`

**Batch D — `*/6h` (13 concurrency + 3 timeout).**
- Concurrency: `audit-drift-telemetry.yml`, `audit-impact-tracker.yml`, `crypto-winner-scan.yml`, `data-pipeline-test.yml`, `deploy-findcryptopairs-ftp.yml`, `fred-macro-refresh.yml`, `gha-summary-report.yml`, `hoffman-tracker.yml`, `honest-kill-switch.yml`, `ml-feedback-loop.yml`, `ml-health-monitor.yml`, `ml-model-autotraining.yml`, `refresh-top-movies.yml`
- Timeout only: `data-pipeline-test.yml`, `ml-health-monitor.yml`, `refresh-top-movies.yml`

**Batch E — daily (45 concurrency + 15 timeout).**
- Concurrency: `adaptive-trust-tuner.yml`, `ai-leaderboard-freshness.yml`, `ai-tournament-price-tracker.yml`, `audit-frontend-manifest.yml`, `auto-retire-daily.yml`, `auto-shutdown-monitor.yml`, `automated-reporting.yml`, `backfill-features.yml`, `backup-verify.yml`, `benchmark-comparison.yml`, `cross-db-audit.yml`, `daily_runs.yml`, `db-backup-email.yml`, `db-sync-bidirectional.yml`, `db-sync-to-mirror.yml`, `deals-refresh.yml`, `forward_test.yml`, `gha-stale-workflows-audit.yml`, `goldmine-tracker.yml`, `hierarchical-bayes.yml`, `incubator-pipeline.yml`, `index-creator-content.yml`, `macd-rsi-m048-shadow-daily.yml`, `ml-gatekeeper-train-ab.yml`, `ml-monthly-retrain.yml`, `money-ready-snapshot.yml`, `monthly-calibrator-refit.yml`, `paper-pilot-daily.yml`, `pick-data-quality-gate.yml`, `picks-now-refresh.yml`, `quant-auditor-deep-nightly.yml`, `refresh-creator-updates.yml`, `schema-drift-audit.yml`, `schema-drift-watchdog.yml`, `scrape-events.yml`, `secret-rotation-reminder.yml`, `social_investigation.yml`, `sports-betting-refresh.yml`, `spy-data-refresh.yml`, `statistical_validation.yml`, `stocksunify2-pull.yml`, `strategy-health-report.yml`, `swarm-janitor.yml`, `torontoevent-goldmine-tracker.yml`, `validate-hf-asset-class.yml`
- Timeout only: `backup-verify.yml`, `beta-portfolio-refresh.yml`, `cross-db-audit.yml`, `daily_runs.yml`, `dna-mutation-cycle.yml`, `forward_test.yml`, `hierarchical-bayes.yml`, `mutation-lifecycle-runner.yml`, `poc-picks-checkpoint.yml`, `refresh-creator-updates.yml`, `scrape-events.yml`, `social_investigation.yml`, `spy-data-refresh.yml`, `statistical_validation.yml`, `swarm-janitor.yml`

**Batch F — weekly (39 concurrency + 11 timeout).**
- Concurrency: `2hour_challenge.yml`, `algorithm-competition-refresh.yml`, `alpha-engine-daily-picks.yml`, `alpha-weekly-validation.yml`, `bt-backtest-trades-sync.yml`, `cftc-cot-refresh.yml`, `daily-miracle-scan.yml`, `daily-picks-snapshot.yml`, `daily-stock-refresh.yml`, `edge-decay-check.yml`, `etf-bond-scanner.yml`, `feature-stability-check.yml`, `forex-smart-picks.yml`, `genome-evolution.yml`, `h004-backtest.yml`, `insider-trades-refresh.yml`, `mutation-analysis-report.yml`, `news-video-healthcheck.yml`, `penny-stock-picks.yml`, `regime-detector.yml`, `research-orchestrator.yml`, `riseoftheclaw-weekly-backtest.yml`, `sec-edgar-fetch.yml`, `simulation-picks-resolver.yml`, `smart-money-tracker.yml`, `sports-forensics-weekly.yml`, `stale-branch-cleanup.yml`, `stocks-daily-stocksunify.yml`, `strategy-tribunal.yml`, `taste-profile-scan.yml`, `torontoevent-algorithm-refresh.yml`, `track-quick-picks.yml`, `walk-forward-backtest.yml`, `weekly-filter.yml`, `weekly-stock-simulation.yml`, `weekly-strategy-scorecard.yml`, `weekly_score_quartile_spread.yml`, `worldclass-intelligence.yml`, `worldclass-pipeline.yml`
- Timeout only: `2hour_challenge.yml`, `algorithm-competition-refresh.yml`, `cftc-cot-refresh.yml`, `daily-prices-yf-refresh.yml`, `etf-bond-scanner.yml`, `h004-backtest.yml`, `insider-trades-refresh.yml`, `stale-branch-cleanup.yml`, `taste-profile-scan.yml`, `torontoevent-algorithm-refresh.yml`, `weekly_score_quartile_spread.yml`

**Batch G — non-cron / other (31 concurrency + 12 timeout + 3 other).** Lowest priority: dispatch, deploy, bootstrap, one-shot.
- Concurrency: `_dynamic-runner-template.yml`, `ai-leaderboard-refresh.yml`, `battleground-mass-backtest-part2.yml`, `clear-channel-command.yml`, `closed-picks-command.yml`, `db-credentials-test.yml`, `db-password-leak-guard.yml`, `deploy-alpha-dashboard.yml`, `deploy-fc-api-env-godaddy.yml`, `deploy-fc-api-hotfix.yml`, `deploy-fc-frontend.yml`, `deploy-friendtracker.yml`, `deploy-fte-events-json.yml`, `deploy-movieshows3-hotfix.yml`, `deploy_bundle.yml`, `discord-token-selftest.yml`, `fix-battleground.yml`, `fix-ghost-cards.yml`, `masking-policy-lint.yml`, `mysql_dedup_fix.yml`, `pick-flow-snapshot-fast.yml`, `pine-generator.yml`, `quant-auditor-fast-pr.yml`, `real_2hour_challenge.yml`, `rl-agent-ppo.yml`, `strategy-performance-no-regression.yml`, `test-fast.yml`, `torontoevent-deploy-competition.yml`, `torontoevent-deploy-live-monitor.yml`, `walkforward-gate.yml`, `wsl-runner-manager.yml`
- Timeout only: `deploy-movieshows3-hotfix.yml`, `deploy_bundle.yml`, `discord-token-selftest.yml`, `fix-battleground.yml`, `masking-policy-lint.yml`, `no-stale-db-passwords.yml`, `pine-generator.yml`, `test-fast.yml`, `torontoevent-deploy-competition.yml`, `torontoevent-deploy-live-monitor.yml`, `walkforward-gate.yml`, `wsl-runner-manager.yml`
- Other/timeout: `swarm-sync-v2.yml`, `torontoevent-deploy-riseoftheclaw.yml`, `torontoevent-spike-scanner.yml`

**Batch H — partial timeouts (3 multi-job workflows).** Use `tools/gha_add_job_timeout.py`, not the top-level helper:
- `dna_strategy_pipeline.yml` (7 jobs; only `evolve-strategies`, `check-promotions` have timeout)
- `dynamic-alpha-engine.yml` (2 jobs; only `alpha-engine`)
- `worldclass-pipeline.yml` (6 jobs; only `regime`, `alphas`, `bundles`, `intelligence`, `validate`)

**Batch I — group collisions (6 files).** Convert the 2 static groups to `${{ github.workflow }}-${{ github.ref }}` (or a prefix + `github.workflow`):
- `edge-stability-daily.yml`, `edge-stability-refresh.yml`
- `fetch-movies-v3.yml`, `kimi-fetch-movies.yml`, `deploy-movieshows-all.yml`, `fetch-movies.yml`

**Explicitly empty batches:** `*/30` concurrency gaps = 0; hourly concurrency gaps = 0 (all 71 hourly workflows already have a group). The high-frequency risk is therefore timeout-only + the single `*/15` outlier.

---

## 2. Reusable workflow design — `gha-scan-job.yml`

### 2.1 The common pattern

181 of 356 active workflows contain `actions/checkout` + `actions/setup-python` + `pip install` + a `git commit`/`safe_push` step. That is ~51% of the fleet and the source of most duplication (and of the 500 KB / trigger-storm risk as files grow).

### 2.2 Proposed interface

File: `.github/workflows/gha-scan-job.yml`, trigger `on: workflow_call` only (no schedule — callers own their triggers).

```yaml
name: GHA scan job (reusable)
on:
  workflow_call:
    inputs:
      python-version:   { type: string, default: '3.11' }
      pip-packages:     { type: string, default: 'requests' }
      run-command:      { type: string, required: true }
      commit-paths:     { type: string, default: '' }        # empty = no commit step
      commit-message:   { type: string, default: 'chore(gha): scan update [skip ci]' }
      fetch-depth:      { type: number, default: 1 }
      timeout-minutes:  { type: number, default: 30 }
      cache-pip:        { type: boolean, default: false }
      pre-run:          { type: string, default: '' }        # optional setup hook
    secrets:
      GH_PAT:           { required: false }
      MYSQL_USER:       { required: false }
      MYSQL_PASSWORD:   { required: false }
      MYSQL_DB:         { required: false }
      DISCORD_WEBHOOK_URL: { required: false }
    outputs:
      changed:
        description: "true if the run produced a commit"
        value: ${{ jobs.scan.outputs.changed }}
jobs:
  scan:
    runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
    timeout-minutes: ${{ inputs.timeout-minutes }}
    permissions: { contents: write }
    outputs: { changed: ${{ steps.commit.outputs.changed }} }
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: ${{ inputs.fetch-depth }}, token: ${{ secrets.GH_PAT || github.token }} }
      - uses: actions/setup-python@v6
        with: { python-version: ${{ inputs.python-version } }, cache: ${{ inputs.cache-pip && 'pip' || '' }} }
      - name: Install dependencies
        run: pip install ${{ inputs.pip-packages }}
      - if: ${{ inputs.pre-run != '' }}
        run: ${{ inputs.pre-run }}
      - id: run
        run: ${{ inputs.run-command }}
      - id: commit
        if: ${{ inputs.commit-paths != '' }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add ${{ inputs.commit-paths }}
          if git diff --cached --quiet; then echo "changed=false" >> "$GITHUB_OUTPUT"; else
            git commit -m "${{ inputs.commit-message }}"
            for i in 1 2 3; do bash .github/scripts/safe_push.sh && break; sleep 5; done
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
```

Caller:

```yaml
jobs:
  scan:
    uses: ./.github/workflows/gha-scan-job.yml
    with:
      python-version: '3.12'
      pip-packages: 'requests numpy pandas'
      run-command: 'PYTHONPATH=. python signal_recorder/system_scanner.py'
      commit-paths: 'signal_recorder/data/'
      timeout-minutes: 20
    secrets:
      GH_PAT: ${{ secrets.GH_PAT }}
```

**Design notes**
- **Do not use `secrets: inherit`.** It passes every repo secret to every caller. Pass by name (as above).
- **Concurrency lives on the caller**, not the reusable job — GitHub evaluates `concurrency` at the workflow-run level. Callers keep their own group/`cancel-in-progress`.
- **Outputs** let a caller chain a second job (e.g. notify) on `jobs.scan.outputs.changed`.
- **`secrets.GH_PAT || github.token`** mirrors the existing convention so a missing PAT does not break the checkout.
- Keep the reusable workflow **flat**: caller → reusable = 1 nesting level, far under the 10-level cap. Do not have the reusable workflow call another reusable workflow.

### 2.3 Limits that constrain the design

| Limit | Value | Implication |
|---|---|---|
| Workflow file size | 500 KB | Only `audit-dashboard.yml` is 94 KB today — no immediate risk, but reuse keeps files from growing. Reusable files also count toward the limit individually. |
| Reusable nesting | 10 levels | 1 level used. |
| Concurrent jobs | 20 Free / 40 Pro | Reuse does not change job count; hygiene (concurrency) is the mitigation. |
| Trigger events | 1500 / 10 s / repo | Consolidating 181 files into callers does **not** reduce trigger count; only path filters / fewer cron ticks do. |
| `GITHUB_TOKEN` | 1000 req / h / repo | Reuse does not change token usage. |
| Job cap | 6 h | `timeout-minutes` is the guard. |

### 2.4 Canary plan

1. Build `gha-scan-job.yml` on a branch; convert **2** low-risk hourly scanners (`ema-retracement-scan.yml`, `now-scanner.yml`) by hand.
2. Run `workflow_dispatch` on both; confirm the commit/push step fires and `changed` output is correct.
3. Observe **3–5 scheduled runs** each; check `reports/gha_queue_audit.json` for queue depth and `reports/actions_failure_guardian.json` for new failures.
4. Only then mass-convert in cadence order (hourly → `*/2h` → `*/4h` → daily → weekly), one branch per cadence.
5. Keep the old files in git history; rollback = revert the conversion commit.

**Conversion candidates (181), by cadence** — full list:

- **`*/15` (1):** `torontoevent-backtest-and-deploy.yml`
- **hourly (51):** `alpha-engine-fast.yml`, `alpha-gainer-capture.yml`, `alpha-quant-stack.yml`, `analyst-tracker.yml`, `asterdex-paper-trading.yml`, `audit-hourly-update.yml`, `baby-strat-forward-paper.yml`, `battle_test.yml`, `breakout-arena.yml`, `claude-gainer-ml-live.yml`, `claude-gainer-short-term.yml`, `coinglass-scanner.yml`, `conviction-picks.yml`, `copy-trader-forward-test.yml`, `cross-aggregator.yml`, `crypto-ml-tracker.yml`, `darwin-evolution.yml`, `dashboard-pick-trader.yml`, `deploy-riseoftheclaw.yml`, `ema-retracement-scan.yml`, `forward-tracking-v2.yml`, `gainer-predictor.yml`, `ghcopilot-paper-monitor.yml`, `hindsight-learner.yml`, `hourly-master-picks.yml`, `hub-sync.yml`, `live_tracker.yml`, `luxalgo-signals.yml`, `master-automation-scheduler.yml`, `mega-mutation-tracker.yml`, `mercury2-scan.yml`, `meta-strategy.yml`, `missed-opportunity-scan.yml`, `momentum-catcher.yml`, `now-scanner.yml`, `picks-now-live-pnl.yml`, `polymarket-signals.yml`, `prediction-quality-tracker.yml`, `quan-engine-live.yml`, `quick-guess-ml.yml`, `regime-terminal.yml`, `signal-engine.yml`, `signal-integrator.yml`, `signal-quality-monitor.yml`, `signal-recorder.yml`, `skyrocket-detector.yml`, `sports-smoke-and-e2e.yml`, `strategy-funnel-hourly.yml`, `sustained-gainer-scan.yml`, `volatile-alt-scanner.yml`, `winner-pattern-scanner.yml`
- **`*/2h` (20):** `alpha-engine-live.yml`, `backfill.yml`, `copytrader-tracker.yml`, `daily-feed-summary.yml`, `dynamic-alpha-engine.yml`, `dynamic-universe.yml`, `enhanced-ml-crypto.yml`, `fc-crypto-pro.yml`, `forward-signal-scanner.yml`, `kimi-feb172026-live.yml`, `live_spike_trading.yml`, `market_beating.yml`, `ml-strategy-reviver.yml`, `outcome-resolver.yml`, `pick-monitor-30min.yml`, `prediction-market-agents.yml`, `proven-strategies-scanner.yml`, `signal_tracking.yml`, `strategy-forward-tester.yml`, `system-health-check.yml`
- **`*/4h` (18):** `audit-dashboard.yml`, `autonomous_trading.yml`, `backtest-and-deploy.yml`, `claude-gainer-tracker.yml`, `crypto-test-portfolios.yml`, `daily-top-picks-filter.yml`, `deploy-vetted-picks.yml`, `dna_strategy_pipeline.yml`, `genome-daily-pipeline.yml`, `gha-queue-audit.yml`, `live_trading.yml`, `live_trading_canada.yml`, `ml-forward-test.yml`, `momentum-scanner.yml`, `parquet-ingest.yml`, `self_optimizing_trading.yml`, `strategy-health-monitor.yml`, `ueps-pick-runner.yml`
- **`*/6h` (9):** `alpha-engine-etf.yml`, `audit-impact-tracker.yml`, `buy-now-analysis.yml`, `data-pipeline-test.yml`, `fred-macro-refresh.yml`, `honest-kill-switch.yml`, `ml-feedback-loop.yml`, `ml-feedback-retrain.yml`, `ml-model-autotraining.yml`
- **daily (42):** `ab_analysis.yml`, `academic-strategies-daily.yml`, `adaptive-trust-tuner.yml`, `ai-leaderboard-freshness.yml`, `ai-tournament-pipeline.yml`, `ai-tournament-price-tracker.yml`, `alpha-trend-catcher.yml`, `automated-reporting.yml`, `beta-portfolio-refresh.yml`, `correlation-monitor.yml`, `daily-scrutiny-engine.yml`, `edge-stability-daily.yml`, `edge-stability-refresh.yml`, `feature-signals-hourly.yml`, `forward-benchmark-ledger.yml`, `forward_test.yml`, `h103-forward-logger.yml`, `hyro-bridge-regen.yml`, `incidents-enhancements-nightly.yml`, `incubator-pipeline.yml`, `macd-rsi-m048-shadow-daily.yml`, `ml-battleground-retrain.yml`, `ml-gatekeeper-train-ab.yml`, `ml-monthly-retrain.yml`, `model-picks-emission.yml`, `monthly-calibrator-refit.yml`, `monthly-tournament.yml`, `paper-pilot-daily.yml`, `pick-funnel-nightly.yml`, `picks-now-refresh.yml`, `poc-picks-checkpoint.yml`, `quant-auditor-deep-nightly.yml`, `rsi5070-forward-snapshot.yml`, `scrape-events.yml`, `sign-coherence-gate.yml`, `social_investigation.yml`, `specialized-scanners.yml`, `spy-data-refresh.yml`, `statistical_validation.yml`, `strategy-perf-by-class-rebuild.yml`, `swarm-pick-review.yml`, `verified-pilot-daily.yml`
- **weekly (30):** `2hour_challenge.yml`, `ai-model-portfolios-daily.yml`, `algorithm-competition-refresh.yml`, `alpha-equity-breakout.yml`, `alpha-weekly-validation.yml`, `bond-agent.yml`, `commodities-agent.yml`, `dxy-state-update.yml`, `equities-agent.yml`, `etf-agent.yml`, `etf-bond-scanner.yml`, `forex-agent.yml`, `forex-smart-picks.yml`, `futures-agent.yml`, `genome-evolution.yml`, `growth-stock-screener-daily.yml`, `h004-backtest.yml`, `mercury2-retrain.yml`, `non-crypto-ab-test.yml`, `overnight-mutations.yml`, `pead-shadow-collector.yml`, `penny-skyrocket-runner.yml`, `penny-stock-picks.yml`, `pre-spike-scan.yml`, `research-orchestrator.yml`, `strategy-tribunal.yml`, `torontoevent-algorithm-refresh.yml`, `traditional-test-portfolios.yml`, `walk-forward-backtest.yml`, `weekly-strategy-scorecard.yml`
- **non-cron (6):** `battleground-mass-backtest-part2.yml`, `battleground-mass-backtest.yml`, `fast-stocks-competition.yml`, `pick-flow-snapshot-fast.yml`, `real_2hour_challenge.yml`, `rl-agent-ppo.yml`
- **other (4):** `actions-failure-guardian.yml`, `consensus-outcome-tracker.yml`, `multi-asset-scanner.yml`, `top-gainers-scan.yml`

**Not candidates:** multi-service workflows (Discord bot, deploy/FTP, MySQL-heavy syncs), workflows with job matrices/strategy needs, and anything using `container:` or `services:`.

---

## 3. Risk & safety

### 3.1 What could break

| Risk | Detail | Mitigation |
|---|---|---|
| **`cancel-in-progress: true` on long backtests** | Cancels an in-flight run mid-compute; can leave a partial commit/push. Backtest-ish: `battleground-mass-backtest.yml` (cip=false), `battleground-mass-backtest-part2.yml` (no group), `walk-forward-backtest.yml`, `h004-backtest.yml`, `riseoftheclaw-weekly-backtest.yml`, `torontoevent-backtest-and-deploy.yml`, `bt-backtest-trades-sync.yml`, `backtest-and-deploy.yml` (cip=false). | Default `false` for anything that pushes or runs > 20 min. Use an expression if a branch should never cancel: `cancel-in-progress: ${{ !contains(github.ref, 'release/') }}`. |
| **Timeout too tight** | `academic-strategies-daily.yml` has `timeout-minutes: 25` and is being killed (per `gha_best_practices_findings.md`). | Raise to 60. Set timeouts from measured p90 (`tools/gha_queue_audit.py`) + 50% headroom, not a blanket 30. |
| **Timeout too loose** | A stuck job otherwise occupies a runner for 6 h. | Ceiling 360; prefer 20–60. |
| **Group collision** | Static groups shared across workflows cancel each other. | Fix the 2 collisions in Batch I; use `${{ github.workflow }}-` prefix everywhere. |
| **Helper inserts into the wrong place** | `gha_add_hygiene.py` inserts before the first line equal to `jobs:` and after every `runs-on:`; a commented `# jobs:` or a nested `runs-on:` inside a step could be mis-hit. | Dry-run on a copy; validate every changed file with YAML safe-load; diff review. |
| **Push storm** | `origin/main` advanced 194 commits beyond this worktree's base; hygiene commits add to it. | `[skip ci]` on all hygiene commits; use `safe_push.sh`; never `push:` trigger. |
| **Reusable workflow drift** | Callers silently change behavior when the reusable file changes. | Pin by branch/commit is not possible for `workflow_call`; version the interface and canary first. |
| **Secrets over-exposure** | `secrets: inherit` would leak all repo secrets to every caller. | Pass secrets by name only. |

### 3.2 Safe order: disable → observe → archive

For **dead/broken** workflows (not the hygiene batches): rename to `*.yml.disabled` → observe 1–2 cron cycles → archive/delete. Never mass-delete. `_dynamic-runner-template.yml` has no triggers (never runs) — it is a documentation stub, keep it disabled rather than deleting.

For the **hygiene** batches the equivalent safe order is: **canary (Batch 0) → observe 3–5 runs → next cadence batch → observe → …**. Do not apply all 161 in one commit.

### 3.3 Rollback pattern

1. One branch + one commit per batch, e.g. `fix/gha-hygiene-<cadence>-2026-11-16`, message `ci(gha): concurrency+timeout for <N> <cadence> workflows [skip ci]`.
2. Record a manifest in the commit body / `reports/gha_hygiene_manifest.json`: batch id, files, previous values (or "absent").
3. **Rollback:** `git revert <batch-merge-sha>` (or the single commit sha) on a fresh branch, then `bash .github/scripts/safe_push.sh`. Because batches are independent, revert is surgical and does not touch other batches.
4. **Emergency stop:** if a batch causes queue growth, revert it and pause the rollout; do not layer more batches on top.
5. Keep `reports/gha_queue_audit.json` and `reports/actions_failure_guardian.json` as the before/after evidence.

---

## 4. Secrets handling — QA Market Validation

### 4.1 Current state (verified read-only via `gh secret list`, names only)

The workflow wiring is **already on `main`** (PR #786, merged 2026-11-15, commit `bb60baffd231`). Of the 5 required secrets, **4 already exist**:

| Secret | Status |
|---|---|
| `FINNHUB_API_KEY` | present (2026-06-06) |
| `FINNHUB` (fallback alias) | present (2026-06-06) |
| `ALPHA_VANTAGE_API_KEY` | present (2026-06-06) |
| `FMP_API_KEY` | present (2026-06-06) |
| `TIINGO_API_KEY` | **MISSING** |
| `TWELVE_DATA_API_KEY` | **MISSING** |

So the remaining work is **2 secrets**, not 5. (Values cannot be verified without reading them; if a present key is expired the workflow still fails — confirm by running the workflow.)

### 4.2 Exact steps

**GitHub UI:**
1. Repo → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret**.
3. Name `TIINGO_API_KEY`, Value = the key (operator supplies; do not paste into chat/logs), **Add secret**.
4. Repeat for `TWELVE_DATA_API_KEY`.
5. (Optional, idempotent) re-add `FINNHUB_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY` if a value rotated.

**CLI (operator supplies the value; `gh` prompts on stdin, so the value never appears in the command line or logs):**

```bash
gh secret set TIINGO_API_KEY      --repo eltonaguiar/findtorontoevents_antigravity.ca
gh secret set TWELVE_DATA_API_KEY --repo eltonaguiar/findtorontoevents_antigravity.ca
```

Verify names only:

```bash
gh secret list --repo eltonaguiar/findtorontoevents_antigravity.ca | grep -E 'TIINGO|TWELVE|FINNHUB|ALPHA_VANTAGE|FMP'
```

**Validation:** `workflow_dispatch` `qa-market-validation.yml`; confirm the run is not RED and the quote chain no longer logs `ALL 7 sources failed`. Do not read `dbpasses.txt`; the operator provides values from their own vault.

---

## 5. Peer PR landing plan

### 5.1 `ghactions-v3` — commit-step hardening

- Source worktree branch `fix/gha-cron-regime-hardening` has 2 unmerged commits: `60141976a83` (regime-terminal commit+push) and `e6f3932991d` (ueps-pick-runner + audit-impact-tracker).
- **Landing vehicle already exists:** PR **#841** (`tmp/v3-hardening` → `main`), which cherry-picks both commits plus their `updates/` docs (5 files, +87/−24).
- PR #841 checks: Conflict Marker Check, DB Password Leak Guard, No stale DB passwords, masking-policy-lint — all **SUCCESS**. `mergeable` was `UNKNOWN` at scan time (GitHub still computing).
- **Plan:** refresh `gh pr view 841 --json mergeable,mergeStateStatus`; if `CONFLICTING`, rebase `tmp/v3-hardening` onto `origin/main` and re-run checks; if `MERGEABLE`, merge (squash or merge commit). Then confirm the next scheduled runs of `regime-terminal.yml`, `ueps-pick-runner.yml`, `audit-impact-tracker.yml` complete their commit steps. Do **not** push the source branch directly to main.

### 5.2 `ghactions` — ETF SHORT gate

- Local branch `ghactions` is **identical** to `origin/fix/etf-short-gate-vix-combos-2026-11-15` (0/0 ahead/behind), 3 commits, 24 files, +3057/−19, base `2027f20f038` (2026-11-15 22:54) — **~194 commits behind `origin/main`**. **No PR exists.**
- The 3 commits mix concerns: ETF SHORT gate (`c8a5792f5a6`), forex/VIX live-read (`d5259137541`), VIX forward-test fix (`99a44602602`).
- **Plan (cherry-pick onto a fresh main-based branch, do not merge the stale branch):**
  1. `git fetch origin && git switch -c fix/etf-short-gate-land origin/main`.
  2. `git cherry-pick c8a5792f5a6 d5259137541 99a44602602` (or split into 2–3 PRs by concern if review weight demands it).
  3. Resolve conflicts; run `python -m pytest tests/test_etf_short_gate.py tests/test_quality_gates.py` and a YAML safe-load over `.github/workflows`.
  4. `git push -u origin fix/etf-short-gate-land`; open PR with a conflict note and the test evidence.
  5. If the branch is too entangled, land only `c8a5792f5a6` first (the audit gate) and follow with the VIX/forex fixes.
- **Conflict check before starting:** `git merge-tree $(git merge-base origin/fix/etf-short-gate-vix-combos-2026-11-15 origin/main) origin/fix/etf-short-gate-vix-combos-2026-11-15 origin/main` and inspect; expect conflicts in shared audit-emitter/tools files given 194 commits of drift.

---

## 6. Prioritized todo list

| # | Task | Effort | Risk | Impact | Depends on |
|---|---|---|---|---|---|
| 1 | Re-baseline counts; extend `gha_add_hygiene.py` with `--timeout` / `--cancel-in-progress` | S | Low | High | — |
| 2 | Set `TIINGO_API_KEY` + `TWELVE_DATA_API_KEY`; dispatch QA validation | S | Low | High (unblocks hourly gate) | operator values |
| 3 | Canary Batch 0 (2 workflows), observe 3–5 runs | S | Low | High (de-risks all batches) | 1 |
| 4 | Batch A: `*/15` + hourly timeout-only | S | Low | High | 3 |
| 5 | Batch B: `*/2h` concurrency + timeout | M | Medium | High | 4 |
| 6 | Batch C: `*/4h` concurrency + timeout | M | Medium | High | 5 |
| 7 | Batch D: `*/6h`; Batch E: daily | M | Medium | Medium | 6 |
| 8 | Batch F: weekly; Batch G: non-cron/other | M | Low | Medium | 7 |
| 9 | Batch H: partial timeouts (3 multi-job) | S | Low | Medium | 7 |
| 10 | Batch I: fix 2 static group collisions | S | Medium (cross-workflow cancel) | Medium | 7 |
| 11 | Raise `academic-strategies-daily.yml` timeout 25 → 60 | S | Low | Medium (stops false failures) | — |
| 12 | Build `gha-scan-job.yml`; canary-convert 2 scanners | L | Medium | Medium (long-term maintenance) | 10 |
| 13 | Land PR #841 (ghactions-v3) | S | Low | Medium | mergeable check |
| 14 | Land ETF SHORT gate via fresh cherry-pick branch | L | High (194-commit drift) | High (audit gate) | conflict check |
| 15 | Mass-convert reusable candidates in cadence order | L | Medium | Medium | 12 |

---

## 7. QA / validation (evidence for this design)

Read-only checks run to produce this report:

```bash
# 1. Authoritative gap scan (origin/main @ e43cb1ddd9d)
git show origin/main:<file> for all .github/workflows/*.yml  -> 356 files
python3 yaml.safe_load each; count concurrency / job-level timeout
#    => 161 no concurrency, 62 no job timeout, 3 partial, 51 both

# 2. Cadence + collision analysis
#    => 153 static groups; 2 duplicate static groups (6 files)

# 3. Peer state
gh pr view 841 --json mergeable,statusCheckRollup   # checks SUCCESS, mergeable UNKNOWN
gh pr view 786 --json state,mergedAt                # MERGED 2026-11-15
git ls-remote --heads origin ghactions              # empty (local-only)
git log --oneline origin/main..ghactions             # 3 commits, base 194 back

# 4. Secrets (names only)
gh secret list --repo eltonaguiar/findtorontoevents_antigravity.ca
#    => FINNHUB_API_KEY, FINNHUB, ALPHA_VANTAGE_API_KEY, FMP_API_KEY present
#    => TIINGO_API_KEY, TWELVE_DATA_API_KEY missing
```

**Validation gates for the rollout itself (run after each batch):**

1. `python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"` — no parse errors.
2. `python3 tools/gha_queue_audit.py --out reports/gha_queue_audit.json` — queued-stuck and p90 counts must not increase.
3. `python3 scripts/actions_failure_guardian.py` (read-only view of `reports/actions_failure_guardian.json`) — no new `latest-failed-no-subsequent-success` entries attributable to the batch.
4. Confirm the batch's workflows still run on their next cron tick and their commit/push step succeeds.
5. Keep the batch manifest + `git revert` sha ready before starting the next batch.

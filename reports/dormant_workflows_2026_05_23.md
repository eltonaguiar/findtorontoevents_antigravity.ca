# Dormant Workflows — Need Re-registration

Generated: 2026-05-23
Cause: stripped-history reset (commit `4aaa6ff848f`) left these workflow YML files in the tree but GitHub Actions never re-scanned them, so they don't appear in `gh api repos/.../actions/workflows`.

Filter: only workflows that **were recurring (schedule cron)** in archive repo `eltonaguiar/findtorontoevents_antigravity.ca-archive-2026-05-23`. One-off `workflow_dispatch`-only files excluded.

**Total: 102 dormant recurring workflows.**

Wake-up procedure: edit + commit + push the file (any cosmetic touch) and GH Actions will re-register. Alternative: trigger via `gh workflow run NAME` after the workflow is registered, but unregistered ones cannot be dispatched.

## High-priority (likely critical to product)

| Workflow | Archive cron | Likely role |
|---|---|---|
| `cross-db-audit.yml` | daily 6:00 UTC | DB integrity audit |
| `cross-db-consistency.yml` | daily 2:00 UTC | DB consistency check |
| `mysql-stale-picks-resolver.yml` | daily 4:00 UTC | Resolve stale audit picks |
| `db-backup-email.yml` | daily 4:00 UTC | DB backup notification |
| `backfill-features.yml` | daily 4:00 UTC | ML feature backfill |
| `ml-battleground-retrain.yml` | daily 4:00 UTC | ML retrain |
| `ml-monthly-retrain.yml` | 1st of month 4:00 UTC | ML monthly retrain |
| `quant-auditor-deep-nightly.yml` | daily 6:15 UTC | Quant auditor nightly |
| `validate-hf-asset-class.yml` | daily 6:35 UTC | HF asset-class validation |
| `dna-mutation-cycle.yml` | daily 5:00 UTC | DNA mutation pipeline |
| `mutation-lifecycle-runner.yml` | daily 5:30 UTC | Mutation lifecycle |
| `train_crypto_models.yml` | daily midnight UTC | ML crypto training |
| `gha-stale-workflows-audit.yml` | daily 5:30 UTC | (meta) stale-workflow audit |
| `secret-rotation-reminder.yml` | 1st of month 9:00 UTC | Secret rotation alert |
| `swarm-janitor.yml` | daily 4:00 UTC | Swarm output janitor |
| `swarm-pick-review.yml` | daily 3:00 UTC | Swarm pick review |

## Full list (102)

```
2hour_challenge.yml | 0 12 * * 1-5
ab_analysis.yml | 30 5 * * *
ai-leaderboard-refresh.yml | 0 6 * * 1
ai-tournament-price-tracker.yml | 0 23 * * *
algorithm-competition-refresh.yml | 0 10 * * 0
alpha-engine-bond.yml | 10 6 * * *
alpha-engine-daily-picks.yml | 0 22 * * 1-5
alpha-equity-breakout.yml | 30 22 * * 1-5
alpha-weekly-validation.yml | 0 6 * * 1
backfill-features.yml | 0 4 * * *
backup-verify.yml | 0 6 15 * *
benchmark-comparison.yml | 0 7 * * *
blacklist-reconciler.yml | 0 4 * * *
bond-agent.yml | 32 14 * * 1-5
commodities-agent.yml | 0 10 * * 1-5
cross-db-audit.yml | 0 6 * * *
cross-db-consistency.yml | 0 2 * * *
daily-miracle-scan.yml | 0 23 * * 1-5
daily-picks-snapshot.yml | 0 22 * * 1-5
daily-price-refresh.yml | 0 22 * * 1-5
daily-stock-refresh.yml | 30 22 * * 1-5
daily_runs.yml | 0 0 * * *
db-backup-email.yml | 0 4 * * *
deals-refresh.yml | 0 14 * * 1
decile-separation-test.yml | 0 6 * * *
dna-mutation-cycle.yml | 0 5 * * *
dxy-state-update.yml | 30 13 * * 1-5
edge-decay-check.yml | 20 7 * * 1-5
equities-agent.yml | 0 13 * * 1-5
etf-agent.yml | 30 14 * * 1-5
etf-bond-scanner.yml | 35 13 * * 1-5
feature-stability-check.yml | 0 6 * * 1
fetch-movies-v3.yml | 0 7 * * *
fetch-movies.yml | 0 6 * * *
forex-agent.yml | 0 0,8,13,17 * * 1-5
forex-smart-picks.yml | 0 2,6,10,14,18,22 * * 1-5
funding-rate-collector.yml | 30 0 * * *
futures-agent.yml | 0 14 * * 1-5
gate-config-emit.yml | 0 5 * * *
genome-evolution.yml | 0 6 * * 0
gha-stale-workflows-audit.yml | 30 5 * * *
growth-stock-screener-daily.yml | 0 14 * * 1-5
h004-backtest.yml | 0 6 * * 1
hc-parity.yml | 0 15 * * 1
hierarchical-bayes.yml | 30 2 * * *
hyro-bridge-regen.yml | 40 5 * * *
incubator-pipeline.yml | 0 6 * * *
index-creator-content.yml | 0 3 * * *
kimi-fetch-movies.yml | 0 6 * * *
mercury2-retrain.yml | 0 2 * * 0
ml-battleground-retrain.yml | 0 4 * * *
ml-monthly-retrain.yml | 0 4 1 * *
money-ready-snapshot.yml | 15 6 * * *
monthly-calibrator-refit.yml | 0 7 1 * *
monthly-tournament.yml | 0 6 1 * *
mutation-analysis-report.yml | 25 6 * * 1
mutation-lifecycle-runner.yml | 30 5 * * *
mysql-q001-sync.yml | 0 8 24 5 *
mysql-stale-picks-resolver.yml | 0 4 * * *
new-strategies-scanner.yml | 45 14 * * 1-5
news-video-healthcheck.yml | 0 15 * * 1,4
non-crypto-ab-test.yml | 30 13 * * 1-5
optimize-score-thresholds.yml | 30 3 * * *
overnight-mutations.yml | 0 2 * * 6
pead-shadow-collector.yml | 30 22 * * 1-5
penny-skyrocket-runner.yml | 48 14 * * 1-5
penny-stock-picks.yml | 0 12 * * 1-5
pre-spike-scan.yml | 0 12,13,14 * * 1-5
prune-strategy-performance.yml | 0 3 * * *
quant-auditor-deep-nightly.yml | 15 6 * * *
refresh-creator-updates.yml | 0 2 * * *
refresh-stocks-portfolio.yml | 30 23 * * 1-5
regime-detector.yml | 30 20 * * 1-5
research-orchestrator.yml | 0 6 * * 6
riseoftheclaw-weekly-backtest.yml | 0 3 * * 0
schema-drift-audit.yml | 0 3 * * *
sec-edgar-fetch.yml | 0 13 * * 1-5
secret-rotation-reminder.yml | 0 9 1 * *
smart-money-tracker.yml | 0 11 * * 1-5
sports-forensics-weekly.yml | 30 6 * * 1
spy-data-refresh.yml | 0 6 * * *
statistical_validation.yml | 0 0 * * *
stocks-daily-stocksunify.yml | 40 21 * * 1-5
stocks-daily.yml | 35 21 * * 1-5
swarm-janitor.yml | 0 4 * * *
swarm-pick-review.yml | 0 3 * * *
swing_screener_daily.yml | 0 14 * * 1-5
taste-profile-scan.yml | 0 3 * * 0
top-gainers-scan.yml | */30 13-19 * * 1-5
torontoevent-algorithm-refresh.yml | 0 10 * * 0
track-quick-picks.yml | 0 23 * * 1-5
traditional-test-portfolios.yml | 30 13 * * 1-5
train_crypto_models.yml | 0 0 * * *
validate-hf-asset-class.yml | 35 6 * * *
value_resolver_quarterly.yml | 0 7 1 */3 *
value_screener_weekly.yml | 0 6 * * 1
walk-forward-backtest.yml | 0 8 * * 0
weekly-stock-simulation.yml | 0 6 * * 0
weekly-strategy-scorecard.yml | 0 0 * * 0
weekly_score_quartile_spread.yml | 15 14 * * 1
worldclass-intelligence.yml | 30 11 * * 1-5
worldclass-pipeline.yml | 45 20 * * 1-5
```

## Wake-up bulk script

```bash
# For each dormant wf, append a comment line + commit. GH will re-scan.
while IFS='|' read -r name cron; do
  name=$(echo "$name" | xargs)
  path=".github/workflows/$name"
  [ -f "$path" ] || continue
  # Append harmless comment if not already present
  if ! grep -q "# re-registered 2026-05-23" "$path"; then
    echo "" >> "$path"
    echo "# re-registered 2026-05-23 after stripped-history reset" >> "$path"
  fi
done < /tmp/unregistered_recurring.txt
git add .github/workflows/
git commit -m "chore(wf): re-register 102 dormant recurring workflows post-reset"
git push origin main
```

Or one-at-a-time as needed (lower batch risk).

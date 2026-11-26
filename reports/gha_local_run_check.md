# GHA local run check

Generated: `2026-11-26T01:49:00Z`  
Workflows: **383** (422 jobs, 2780 steps)  
Clean: **368** · Warnings: **13** · Errors: **2**

## Findings by kind

| Kind | Count |
|------|------:|
| `WARNING:shellcheck-SC2046` | 7 |
| `WARNING:script-missing-guarded` | 7 |
| `ERROR:script-missing` | 2 |
| `WARNING:shellcheck-SC2154` | 1 |

## Non-clean workflows

### `.github/workflows/ai-tournament-pipeline.yml` — WARNING
- **WARNING** `shellcheck-SC2046` @ .github/workflows/ai-tournament-pipeline.yml:pipeline#13 (Verify output was produced) — Quote this to prevent word splitting. [SC2046]

### `.github/workflows/algorithm-competition-refresh.yml` — WARNING
- **WARNING** `script-missing-guarded` @ .github/workflows/algorithm-competition-refresh.yml:refresh-competition#4 (Run competition backtester) — STOCKS/competition/run_competition.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs

### `.github/workflows/auto-retire-daily.yml` — WARNING
- **WARNING** `shellcheck-SC2046` @ .github/workflows/auto-retire-daily.yml:retire-check#3 (Run auto_retire) — Quote this to prevent word splitting. [SC2046]

### `.github/workflows/claude-gainer-tracker.yml` — WARNING
- **WARNING** `shellcheck-SC2046` @ .github/workflows/claude-gainer-tracker.yml:predict-and-track#4 (Step 0: Write dashboard status (scanning)) — Quote this to prevent word splitting. [SC2046]

### `.github/workflows/deploy_bundle.yml` — ERROR
- **ERROR** `script-missing` @ .github/workflows/deploy_bundle.yml:deploy#2 (Deploy bundle) — deploy_prod_bundle.py does not exist and the step does not guard the failure

### `.github/workflows/fast-stocks-competition.yml` — ERROR
- **ERROR** `script-missing` @ .github/workflows/fast-stocks-competition.yml:scan#4 (Run Fast Stocks Competition) — run_fast_competition.py does not exist and the step does not guard the failure

### `.github/workflows/forward_test.yml` — WARNING
- **WARNING** `shellcheck-SC2046` @ .github/workflows/forward_test.yml:forward-test#4 (Run forward tests) — Quote this to prevent word splitting. [SC2046]

### `.github/workflows/genome-daily-pipeline.yml` — WARNING
- **WARNING** `script-missing-guarded` @ .github/workflows/genome-daily-pipeline.yml:quality-scoring#9 (Run MACD DNA Mutations) — genome/dna_macd_mutations.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs
- **WARNING** `script-missing-guarded` @ .github/workflows/genome-daily-pipeline.yml:quality-scoring#10 (Run DNA Pumpwatch Mutations) — genome/dna_pumpwatch_mutations.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs

### `.github/workflows/gha-failure-digest.yml` — WARNING
- **WARNING** `shellcheck-SC2154` @ .github/workflows/gha-failure-digest.yml:digest#6 (Publish or close the digest issue) — rc is referenced but not assigned. [SC2154]

### `.github/workflows/sports-betting-refresh.yml` — WARNING
- **WARNING** `script-missing-guarded` @ .github/workflows/sports-betting-refresh.yml:custom-sports-update#2 (Update custom sports picks (UFC/Tennis/Golf)) — tools/update_custom_sports_picks.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs

### `.github/workflows/swing_screener_daily.yml` — WARNING
- **WARNING** `script-missing-guarded` @ .github/workflows/swing_screener_daily.yml:run-swing-screener#5 (Run swing screener) — alpha_engine/swing_screener_runner.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs

### `.github/workflows/torontoevent-algorithm-refresh.yml` — WARNING
- **WARNING** `script-missing-guarded` @ .github/workflows/torontoevent-algorithm-refresh.yml:refresh-competition#4 (Run competition backtester) — STOCKS/competition/run_competition.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs

### `.github/workflows/value_resolver_quarterly.yml` — WARNING
- **WARNING** `script-missing-guarded` @ .github/workflows/value_resolver_quarterly.yml:run-value-resolver#5 (Run value resolver (thesis-break / time-stop / IV-attained)) — alpha_engine/value_resolver_runner.py does not exist; step already degrades (guard/`||`) so the job stays green but this capability never runs

### `.github/workflows/won-pnl-contradiction-backfill.yml` — WARNING
- **WARNING** `shellcheck-SC2046` @ .github/workflows/won-pnl-contradiction-backfill.yml:backfill#4 (Run Won PNL Contradiction Backfill) — Quote this to prevent word splitting. [SC2046]

### `.github/workflows/worldclass-pipeline.yml` — WARNING
- **WARNING** `shellcheck-SC2046` @ .github/workflows/worldclass-pipeline.yml:alphas#3 (Install TA-Lib C library) — Quote this to prevent word splitting. [SC2046]


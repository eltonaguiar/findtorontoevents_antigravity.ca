# GitHub Actions — cancelled runs (recent main + scheduled)

## How we sampled

- `gh run list --limit 500` filtered to `conclusion=cancelled` → **10** hits in that window.

## Patterns in the logs

| Pattern | Evidence | Typical fix |
|--------|-----------|-------------|
| **Job `timeout-minutes`** | Step ends with `##[error]The operation was canceled.` after ~N minutes matching YAML timeout | Raise ceiling; shorten checkout (`fetch-depth: 1`) when full history is not required |
| **Concurrency (`cancel-in-progress: true`)** | New scheduled run superseded older (intentional) | Keep or set `cancel-in-progress: false` only if overlaps must finish (trade-off: backlog) |

## Per-run notes (runs cited in workflow comments)

| Run / workflow | Wall time → cancel | Cause |
|----------------|---------------------|-------|
| **25826948681** TV Paper TP/SL Watchdog | Checkout ~3m (`21:17:21`–`21:20:19`), job timeout **3** | Timeout too low for congested checkout |
| **25826595372** Claude Gainer ST | Checkout ~18m (`fetch-depth: 0`), total ~20m; push succeeded then step **cancelled** | **20m** job cap + enormous shallow-unfriendly checkout |
| **25821211511** Prediction Quality Tracker | ~5m | Matches **timeout-minutes: 5** |
| **25825765147** Deploy Vetted Master-Picks | ~18m+ | Matches prior **18** ceiling |
| **25825710402** UEPS Pick Runner | ~25m+ | Matches **25** ceiling |
| **25821039715** Polymarket Signals | ~10m | Matches **10** ceiling |
| **25824980622 / 25824926796 / AsterDEX** | (same class) short ceilings on small jobs | Queue + checkout variance |

## Code changes (this commit)

Timeouts increased and shallow clone added where safe:

- `tv-paper-tpsl-watchdog.yml` → **12** min
- `claude-gainer-short-term.yml` → **`fetch-depth: 1`**, timeout **35** min
- `prediction-quality-tracker.yml` → **15** min, explicit **`fetch-depth: 1`**
- `deploy-vetted-picks.yml` → **30** min (`fetch-depth: 0` kept — comment claims full history)
- `ueps-pick-runner.yml` → **45** min (`fetch-depth: 0` kept — existing comment)
- `polymarket-signals.yml` → **20** min, **`fetch-depth: 1`**
- `ml-discord-status.yml` → **12** min
- `sports-prediction-market-sync.yml` → **15** min
- `asterdex-paper-trading.yml` → **12** min

## Verification

Logic-only YAML edits — **no CI command required.** After merge, skim Actions for these workflows showing **completed** (not cancelled at timeout boundary).

## Optional follow-ups

- Workflows with `concurrency.cancel-in-progress: true` plus frequent cron **may still** show cancellations when overlapping; that is by design unless changed.
- If `deploy-vetted-picks` / `ueps-pick-runner` still hit ceilings, consider whether `fetch-depth: 0` is strictly necessary or can be reduced with documented push/rebase behavior.

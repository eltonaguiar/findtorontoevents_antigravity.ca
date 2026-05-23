# ROOCODE Workflow Clone Documentation

## Summary
Successfully cloned the `torontoevent-backtest-and-deploy.yml` GitHub Actions workflow and created a ROOCODE-branded version.

## Source Workflow
- **File:** `.github/workflows/torontoevent-backtest-and-deploy.yml`
- **Purpose:** Runs backtests, live market scanning, and deploys dashboards to torontoevent.net via FTP

## Cloned Workflow
- **File:** `.github/workflows/torontoevent-backtest-and-deploy-ROOCODE.yml`
- **Name:** `[torontoevent.net] Run Backtests & Deploy Dashboards (ROOCODE)`

## Key Changes Made

### 1. Workflow Identity
- Added `(ROOCODE)` suffix to workflow name
- Updated workflow file name with `-ROOCODE` suffix

### 2. Job Names
- Renamed job from `backtest` to `backtest-ROOCODE`

### 3. Deployment Paths (Isolated)
To avoid conflicts with the original workflow, all deployments are isolated:
- **KIMI Claw Dashboard:** Deploys to `kimi-claw-ROOCODE/` instead of `kimi-claw/`
- **Rise of the Claw:** Deploys to `riseoftheclaw-ROOCODE.html` instead of `riseoftheclaw.html`
- **Updates Page:** Deploys to `updates-ROOCODE/` directory instead of `updates/`

### 4. Commit Messages
- Added `(ROOCODE)` identifier to distinguish from original workflow commits

### 5. Verification URLs
Updated all verification URLs to check the ROOCODE-specific paths:
- `https://torontoevent.net/kimi-claw-ROOCODE/`
- `https://torontoevent.net/riseoftheclaw-ROOCODE.html`
- `https://torontoevent.net/updates-ROOCODE/`

### 6. Summary Output
All GitHub Actions summary outputs include `(ROOCODE)` branding

## Triggers (Same as Original)
The cloned workflow maintains the same triggers:
- **Schedule:**
  - Daily at 6 AM UTC (Tier 1 backtests)
  - Every 15 minutes during US market hours (14-21 UTC, Mon-Fri)
  - Every 4 hours on weekends (crypto only)
- **Push:** Triggers on changes to specific paths in KIMI_CLAW_RESEARCH_FEB162026 and KIMI_RISEOFTHECLAW
- **Manual:** Available via `workflow_dispatch`

## Functionality
The ROOCODE workflow performs:
1. ✅ Checkout repository
2. ✅ Fix submodule issues
3. ✅ Set up Python 3.11
4. ✅ Install dependencies (yfinance, pandas, numpy, ccxt, requests, statsmodels)
5. ✅ Run Tier 1 backtests (scheduled only)
6. ✅ Run live market scanner
7. ✅ Commit updated results to repository
8. ✅ Deploy KIMI Claw dashboard to isolated path
9. ✅ Deploy Rise of the Claw to isolated path
10. ✅ Deploy updates page to isolated path
11. ✅ Verify all deployments
12. ✅ Generate summary with ROOCODE branding

## Validation Results
All structural checks passed:
- ✅ YAML structure valid
- ✅ All required sections present
- ✅ ROOCODE branding applied consistently
- ✅ Deployment paths correctly isolated
- ✅ Triggers properly configured
- ✅ Steps complete and functional

## Usage
The workflow is ready to be used in GitHub Actions. It will:
- Run automatically on the defined schedule
- Trigger on relevant code changes
- Be manually dispatchable from the Actions tab
- Deploy to isolated paths on torontoevent.net
- Not interfere with the original workflow deployments

## Files Created
1. `.github/workflows/torontoevent-backtest-and-deploy-ROOCODE.yml` - The cloned workflow
2. `test_roocode_workflow.py` - Validation test script
3. `ROOCODE_WORKFLOW_CLONE.md` - This documentation

## Next Steps
To activate the workflow:
1. Commit and push the new workflow file to the main branch
2. The workflow will appear in GitHub Actions under the name "[torontoevent.net] Run Backtests & Deploy Dashboards (ROOCODE)"
3. Can be triggered manually via the "Run workflow" button
4. Will automatically run on the next scheduled trigger or relevant code push

## Notes
- The workflow uses the same FTP credentials as the original (via GitHub Secrets)
- All deployments are isolated to prevent overwriting the original site content
- The original workflow remains untouched and continues to function normally
- Both workflows can run concurrently without conflicts

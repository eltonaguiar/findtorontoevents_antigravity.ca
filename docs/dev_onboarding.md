# Developer Onboarding Guide

## Quick Start (< 5 minutes)

```bash
# 1. Clone and enter
git clone https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git
cd findtorontoevents_antigravity.ca

# 2. Run setup
./scripts/setup_dev_env.sh

# 3. Start dev server
python3 tools/serve_local.py

# 4. Open in browser
#   Main site:       http://127.0.0.1:5173/
#   FavCreators:     http://127.0.0.1:5173/fc/
#   Audit Dashboard: http://127.0.0.1:5173/audit/
```

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | 18+ | nvm available in cloud environments |
| npm | 8+ | Comes with Node |
| Python | 3.10+ | 3.12 recommended |
| pip | 21+ | `pip install --user` if no write access to site-packages |
| Git | 2.30+ | For hooks and workflows |

## What the Setup Script Does

`scripts/setup_dev_env.sh`:
1. Checks all prerequisites are installed
2. `npm install` — Playwright, acorn, puppeteer, openai
3. `pip install -r requirements.txt` — pandas, numpy, requests, python-dotenv
4. `npx playwright install chromium` — headless browser for tests (skip with `--skip-browsers`)
5. Validates critical file syntax
6. Checks pre-built assets exist

## Verify Your Environment

```bash
./scripts/verify_dev_env.sh
```

This checks: tools, dependencies, critical files, port availability, and analysis scripts.

## Architecture Overview

```
/                            → Main Toronto events site (pre-built, not in repo)
/fc/                         → FavCreators SPA (pre-built in favcreators/docs/)
/audit/                      → Audit Dashboard (trading strategy audit)
/MENTALHEALTHRESOURCES/      → Mental Health Resources (static HTML)

tools/serve_local.py         → Local dev server (port 5173, mocks PHP APIs)
audit_trail/                 → Dashboard data generator pipeline
alpha_engine/                → Quantitative trading research platform
analysis/                    → Score calibration and walk-forward optimization
engine/                      → Context-aware ranking engine
```

## Local Dev Server

`tools/serve_local.py` is the **only** correct way to serve locally. It:
- Serves all sub-apps at their correct routes
- Mocks PHP API endpoints (login, notes, creators)
- Mimics the JS proxy (`js-proxy-v2.php`) for Next.js chunks
- Handles CORS headers

**Do not use** `python -m http.server` — it returns PHP source code.

### Mock API credentials
- Login: `admin` / `admin` (local mock only)
- Guest notes: auto-populated for user_id=0

### Using real MySQL data
```bash
FAVCREATORS_API_PROXY=https://findtorontoevents.ca python3 tools/serve_local.py
```

## Running Tests

```bash
# Reliable local test (10/10 pass):
npx playwright test tests/mental-health-resources.spec.ts --project="Desktop Chrome"

# FavCreators test (known asset naming mismatch — see Gotchas):
npx playwright test tests/favcreators-guest-9000.spec.ts --project="Desktop Chrome"

# Python syntax check:
python3 -c "import py_compile; py_compile.compile('tools/serve_local.py', doraise=True)"
```

## Scoring System & Analysis Tools

### Score Calibration (context-aware)
```bash
python analysis/score_calibration.py --verbose
# Outputs: data/context_rankings.json
# Shows: per-asset-class, per-setup-type, per-symbol optimal actions
```

### Walk-Forward Validation
```bash
python analysis/walkforward_optimizer.py --train-days 60 --test-days 14
# Outputs: data/walkforward_results.json
# Shows: stability of context actions across time windows
```

### Context Ranking (rank active picks)
```bash
python engine/context_ranking.py
# Ranks all active picks using hierarchical blended stats
# Actions: emit_live | low_priority | paper_trade_only | suppress
```

## Common Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Port 5173 in use | Another server running | Kill it or `PORT=5174 python3 tools/serve_local.py` |
| FavCreators test fails | Asset naming: `main-*.js` vs `index-*.js` | Known issue — test expects old naming |
| Main site 404 | `index.html` not in repo | Expected — it's deployed separately to hosting |
| `no_js_errors.spec.ts` fails | Next.js chunk not in repo | Expected — only on production server |
| PHP validation tools missing | `check_syntax.js`, `validate_php52.py` not committed | Create if needed per `.cursor/rules/` |
| pip permission denied | System site-packages not writable | Use `pip install --user` or `--skip-browsers` |

## Deployment

**Never deploy without local verification.** See `.cursor/rules/deploy-always-no-prompt.mdc`.

```bash
# 1. Start local server
python3 tools/serve_local.py

# 2. Run Playwright tests
npx playwright test tests/no_js_errors.spec.ts --project="Desktop Chrome"

# 3. Deploy (only after tests pass)
python tools/deploy_to_ftp.py
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `tools/serve_local.py` | Local dev server |
| `playwright.config.ts` | Test configuration |
| `audit_trail/dashboard_generator.py` | Main data pipeline (~12K lines) |
| `alpha_engine/elite_scorer.py` | Pick scoring engine |
| `audit_trail/quality_gates.py` | Score penalties, Smart Picks gates |
| `audit_dashboard/template.html` | Dashboard UI (source of truth — edit this, not index.html) |
| `audit_dashboard/dashboard_enhancements.js` | Persistent UI features (survives regeneration) |
| `analysis/score_calibration.py` | Context-aware calibration engine |
| `engine/context_ranking.py` | Live pick ranking engine |

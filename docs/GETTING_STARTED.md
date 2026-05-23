# Getting Started — findtorontoevents.ca/audit

Welcome to the findtorontoevents.ca algorithmic trading prediction system. This guide gets a new contributor from zero to a safe first change.

---

## Prerequisites

- **Python 3.11+** (3.12 works; 3.10 is untested)
- **git** 2.30+
- **Node.js 18+** (for Playwright end-to-end tests only)
- **Operating system:** Windows is primary (paths, PowerShell scripts, FTP tooling). Linux/macOS work for Python-only tasks but some scripts assume Windows paths.
- **GitHub CLI (`gh`)** — install from https://cli.github.com/ and run `gh auth login`. Required to check Actions status and rerun jobs.

---

## Clone and Setup

```powershell
# Clone
git clone https://github.com/<your-fork>/findtorontoevents_antigravity.ca.git
cd findtorontoevents_antigravity.ca

# Create and activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: install Playwright for browser tests
pip install playwright
playwright install chromium
```

For Node-based Playwright tests (sports betting suite):
```powershell
npm install
npx playwright install
```

---

## Environment Variables

Set these before running any scanner or test that touches live data. **Never commit `.env` files or secrets to git.**

| Variable | Required? | Description |
|----------|-----------|-------------|
| `DB_PASS_STOCKS` | For MySQL sync | Password for the `ejaguiar1_stocks` MySQL database |
| `DB_PASS_BACKTESTS` | For MySQL sync | Password for the `ejaguiar1_backtests` MySQL database |
| `FRED_API_KEY` | Optional | FRED (Federal Reserve Economic Data) API key — needed for bond/macro data pipeline; get free at https://fred.stlouisfed.org/docs/api/api_key.html |
| `ALPHA_FAST_MODE` | Optional | Set to `1` to use tighter TP/SL for faster signal resolution (local testing) |
| `AUDIT_PICK_SANITY_GATE` | Optional | Set to `1` to enable strict pick sanity validation (recommended for PR testing) |
| `KELLY_DD_HALT_ENABLED` | Optional | Set to `1` to enable drawdown-based position halt |
| `BOND_ELITE_FLOOR` | CI only | Set via `gh variable set BOND_ELITE_FLOOR 15` on the repo — not a local dev var |

On Windows PowerShell:
```powershell
$env:DB_PASS_STOCKS = "your_password"
$env:FRED_API_KEY = "your_key"
```

---

## Running Tests

```powershell
# Full test suite (fast — no network calls)
python -m pytest tests/ -q

# Focused smoke tests (recommended before any PR)
python -m pytest tests/test_risk_policy_loader.py tests/test_validation_gate.py tests/test_conviction_stack.py -q

# With coverage check (must stay above 40% — CI gate A15.2)
python -m pytest tests/ -q --cov=alpha_engine --cov=audit_trail --cov-fail-under=40

# Syntax check a file you edited (NEVER run dashboard generators — use py_compile)
python -m py_compile audit_trail/quality_gates.py && echo OK
```

---

## Understanding a Pick

Every pick in the system is a Python dict (serialized to JSON) with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Trading pair or ticker, e.g. `BTCUSDT`, `AAPL`, `EURUSD`, `GC=F` |
| `strategy` | str | Strategy name, e.g. `funding_rate_carry`, `etf_dual_momentum`, `cta_commodity_momentum` |
| `source_system` | str | Which scanner generated it: `production_scanner`, `quan_engine`, `baby_strategy`, `copy_trader` |
| `asset_class` | str | One of: `CRYPTO`, `EQUITY`, `COMMODITY`, `ETF`, `BOND`, `FOREX` |
| `direction` | str | `LONG` or `SHORT` |
| `entry_price` | float | Price at which the pick was generated |
| `take_profit` | float | Target exit price (must be above entry for LONG, below for SHORT) |
| `stop_loss` | float | Risk exit price (must be below entry for LONG, above for SHORT) |
| `confidence` | float | Score 0.0–1.0 from the ML/scoring layer |
| `elite_score` | float | Composite quality score (higher = better; threshold varies by asset class) |
| `created_at` | str | ISO-8601 UTC timestamp when the pick was generated |
| `pnl_pct` | float | Realized PnL percentage (set by outcome resolver after close) |
| `outcome` | str | `WON`, `LOST`, `FLAT`, or `OPEN` |

**Trade geometry rule:** For a LONG pick, `stop_loss < entry_price < take_profit`. Picks violating this fail `passes_active_gate` and are silently dropped.

---

## Making a Change — Safe Workflow

Before editing any Python file:

1. **Read `CLAUDE.md` constraints** — particularly the Critical File Rules and Wire-Up Rule. Violations are the #1 cause of reverts.

2. **Syntax-check before running** — never run `audit_trail/dashboard_generator.py` locally (it overwrites live HTML files). Use `py_compile` instead:
   ```powershell
   python -m py_compile audit_trail/quality_gates.py
   python -m py_compile alpha_engine/my_new_file.py
   ```

3. **Pull before committing** — this repo has multiple concurrent agents pushing:
   ```powershell
   git stash
   git pull --rebase origin main
   git stash pop
   ```

4. **Run tests:**
   ```powershell
   python -m pytest tests/ -q
   ```

5. **Commit and push** — reference the task/audit item (e.g. `A18.1`) in the commit message. Do NOT push without pulling first (step 3).

6. **Check CI** — after pushing, run:
   ```powershell
   gh run list --branch main
   ```
   If a job fails: `gh run rerun --failed <run-id>`

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `alpha_engine/production_scanner.py` | Main pick generation entry point — runs all strategies, applies sizing, writes `active_picks.json` |
| `alpha_engine/outcome_resolver.py` | Resolves closed picks against live prices; computes PnL; feeds `asset_class_health` |
| `audit_trail/quality_gates.py` | `passes_active_gate()` and `passes_smart_gate()` — the gating layer every pick must clear |
| `audit_trail/dashboard_generator.py` | Reads 30+ JSON files + 16 SQLite DBs; outputs `dashboard_payload.json` + HTML (CI-only) |
| `audit_dashboard/template.html` | The audit dashboard UI template — **edit this**, never `audit_dashboard/index.html` |
| `alpha_engine/config.py` | All thresholds: risk params, position sizing, strategy weight overrides, sector map |
| `alpha_engine/kelly_position_sizer.py` | Kelly Criterion sizing with drawdown halt support |
| `CLAUDE.md` | Project constitution — critical file rules, Wire-Up Rule, asset class strategy |
| `TESTING_PROTOCOL.MD` | Validation layers required before merging (strategy demotion gate in §7) |
| `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | Mandatory protocol before killing any strategy (export → analyze → mutate first) |

---

## Common Pitfalls — Mistakes That Have Caused Outages

These are real production incidents from `CLAUDE.md` and session history:

1. **Replacing `TORONTOEVENTS_ANTIGRAVITY/index.html` with the Next.js build output** — The `build/index.html` from the Next.js app is only the event-grid widget. The live homepage is a 4,845-line hand-coded file. Uploading the wrong one stripped the mega-menu, filters, and thumbnails (outage 2026-04-27).

2. **Skipping `tools/deploy_sports_files.sh` after merging a sports PR** — 50webs has no shell; files don't reach production until FTP-uploaded. Two outages occurred from committed-but-not-deployed conflicts (#399, #415).

3. **Running `audit_trail/dashboard_generator.py` locally** — It reads live data and overwrites `audit_dashboard/index.html` with a stale payload. Always use `py_compile` for syntax checks.

4. **Using `npm run deploy:sftp`** — Has a known sequence bug where the GitHub (basePath) build overwrites the SFTP build locally before uploads finish. Use `scripts/upload-next-only.mjs` instead.

5. **Silently killing a strategy without the mutation protocol** — Do not add a strategy to `BLOCKED_SOURCE_SYSTEMS` without completing `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (export closed CSV → `python tools/mutation_analysis.py`). See `TESTING_PROTOCOL.MD §7`.

6. **Opening a PR with a new integration module that has no production caller** — The Wire-Up Rule closes these. Verify with `grep -rln "import my_module" alpha_engine/ audit_trail/ tools/` before submitting.

7. **Not pulling before committing** — Multiple agents push concurrently. Always `git stash && git pull --rebase origin main && git stash pop`.

8. **Hardcoding `/tmp/` paths** — Windows does not have `/tmp/`. Use `alpha_engine/check_active_picks.py` from repo root, or install the shim: `tools/install_check_active_picks_shim.ps1`.

9. **Using a single Binance API endpoint** — The API failover rule (CLAUDE.md) requires a 3+ fallback chain: Binance mirrors (api, api1, api2, api3) → CoinGecko → KuCoin → CryptoCompare.

---

## Where to Get Help

| Resource | What it covers |
|----------|---------------|
| `CLAUDE.md` | Project constitution, critical rules, asset class north-star goals |
| `TESTING_PROTOCOL.MD` | Full validation protocol, strategy demotion gate (§7) |
| `docs/ARCHITECTURE.md` | System overview, data flow, key workflows |
| `docs/ARCHITECTURE_OVERVIEW.md` | Legacy overview with component table |
| `docs/DEVELOPER_SETUP_QUANT.md` | Quant/Python environment setup notes |
| `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` | Required process before banning a strategy |
| `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | Three-axis mutation protocol for struggling strategies |
| `docs/TRADINGVIEW_MCP_GUIDE.md` | TradingView MCP tools, CDP, paper trading CLI |
| `docs/CI_GUIDE.md` | GitHub Actions patterns, rerun commands |
| `updates/index.html` | Public changelog — read before editing (never overwrite without reading full file) |

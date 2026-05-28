---
name: money-maker-readyv2
description: Ultimate statistical edge audit per asset class. Produces proven, real-money-grade filters for CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND so that a quant or hedge fund manager would find the edge trustworthy. Extends money-maker-ready v1.1 with stronger success criteria, autonomous execution rules, and a weekly filter output. Use when the user says "/money-maker-readyv2", "prove the edge", "real money filters", or "ultimate statistical edge". Aliases - money-maker-readyv2, ultimate-edge, prove-edge.
---

# /money-maker-readyv2 — Ultimate Statistical Edge Audit

**Goal:** Produce proven, quantitatively-validated filters per asset class such that:
- Top picks grow a live balance over time
- Downside is limited (MDD≤20%, position sizing by Kelly/Hyro overlay)
- Winners beat losers (PF≥1.5, WR≥50%)
- A quant/hedge-fund manager would rate the edge trustworthy for real capital

Inherits all hard rules from `/money-maker-ready` (v1.1). This v2 adds:

## Success Criteria (ALL must be true before calling done)

1. **EQUITY**: Weekly filter output shows ≥5 picks with elite_score≥60, WR≥55% on historical analogs (n≥30 per filter bucket), PF≥1.5 on resolved picks.
2. **CRYPTO**: Sub-class filters (WR≥50%) identified and live — picks passing the filter have PF≥1.5 on resolved_n≥100.
3. **COMMODITY**: Post-COT-dedup clean picks accumulate; once n≥50 post-dedup, top strategy identified with PF≥1.5.
4. **ETF**: n≥150 on path to OOS_READY; PF maintained ≥1.3; top ETF strategies identified.
5. **FOREX**: Mutation protocol in progress; LONG-direction block evaluated by data; directional filter identified if WR≥50% exists.
6. **BOND**: Accumulating picks; top BOND strategy (if any) identified once n≥20.
7. **Kelly sizing**: All weekly filter picks have a computed position size (% of account) via `compute_position_size()` with DD-halt guard.

## Operating Rules (NON-NEGOTIABLE)

1. **PLAN FIRST** — numbered task list before any code.
2. **WORK AUTONOMOUSLY** — no clarifying Qs unless genuinely blocked.
3. **SELF-VERIFY** — after every step: run tests, inspect output, confirm it worked.
4. **DEBUG YOURSELF** — if it fails, diagnose + fix; don't hand back.
5. **USE EVERY TOOL** — terminal, code exec, real data.
6. **NO PLACEHOLDERS** — real components + real states; no TODOs.
7. **PROGRESS LOG** — track completed / in-flight / decisions / blockers.
8. **STAY ON GOAL** — off-spec discoveries: note + keep moving.
9. **IF BLOCKED** — log the wall, continue everything parallelizable.
10. **CHECK SUCCESS BEFORE STOPPING** — re-read criteria, confirm each is met.

## Essentials — Where Everything Lives (read this FIRST if you're a fresh IDE agent)

You start with no context. Here is where the real data and credentials are. **Never hardcode or echo a password; never commit a secret.**

### Database
- **Host:** `mysql.50webs.com` (port `3306`). 50webs has **no shell** — you can only reach it over the MySQL wire protocol, not SSH.
- **Primary databases** (MySQL, user `ejaguiar1`): `ejaguiar1_stocks` (picks, outcomes, incidents/enhancements) and `ejaguiar1_backtests` (backtest trades). The full set of 9 (`_sportsbet`, `_favcreators`, `_events`, `_memecoin`, `_tvmoviestrailers`, `_news`, `_deals`) and per-table schema are documented by the **`/db-schema`** skill — invoke it for table layouts.
- **Canonical way to connect (USE THIS — do not roll your own):**
  ```python
  from tools.db_env import get_stocks_creds, get_backtests_creds
  creds = get_stocks_creds()      # -> {host, user, password, database, port}
  # creds resolve from env vars first, then fall back to verified defaults
  import mysql.connector
  conn = mysql.connector.connect(**creds)
  ```
  `tools/db_env.py` is the single source of truth. It reads env vars (`DB_PASS_STOCKS`/`DB_NAME_STOCKS`, `DB_PASS_BACKTESTS`/`DB_NAME_BACKTESTS`, plus `AUDIT_DB_*` / `DB_STOCKS_*` aliases) and falls back to the verified host/user. Reference helpers that already work: `tools/db_health_check.py`, `tools/cross_db_consistency.py`.

### Credentials file
- **Location:** `/home/eaguiar2015/dbpasses.txt` (a labelled key/value list of every DB password + LLM API key). It lives **outside the repo and is gitignored — NEVER commit, paste, echo, or print its contents.** Read it only to populate env vars or `db_env.py` fallbacks.
- The DB passwords there follow a per-database naming convention (see the top block of the file, e.g. the `stocks…` / `backtests…` lines). Resolve them through `tools.db_env` rather than copying the literal value into code or a report.
- The same file holds the LLM provider keys (NVIDIA, Cerebras, OpenRouter, xAI, Cloudflare `ACCOUNT_ID`, etc.) used by `tools/consult_multi.py` and the LiteLLM proxy — also gitignored, also never commit.

### Live audit surfaces (read-only ground truth)
- Dashboard JSON the page renders from: `audit_dashboard/data/*.json` (e.g. `money_ready_verdict.json`, `pf_registry.json`, `pick_summary_stats*.json`, `nav_surface_edge_matrix.json`). Prefer these to scraping HTML.
- Live pages (all under `https://findtorontoevents.ca/audit/`):
  - **Main dashboard:** `/audit/` — strategy performance, Smart Picks, High Conviction, Money Ready verdicts
  - **Pick Funnel:** `/audit/pick_funnel.html` — every pick scanned → score floor → trust gate → HC → opened → closed → win/loss. Per-class visibility into where edge lives. Nav-surface edge matrix shows WR/PF per filter tab × asset class. 48h/14d/90d breakdowns. DISPUTED banner flags suspicious stats.
  - **Incidents + Enhancements:** `/audit/incidents.html` — 45 open incidents (21 P0) + 47 enhancements across 9 asset classes. Auto-regenerated nightly from `INCIDENT_*` / `ENHANCEMENT_*` tables in `ejaguiar1_stocks`. Every incident has sev/status/component/reporter/date EST. Every enhancement has impact/effort/status/cat.
  - **Updates page:** `https://findtorontoevents.ca/updates/` — earlier enhancement plans, EAGLE reviews, multi-AI consult results. Contains the institutional-readiness 90-day plan, 12-partner audit meta-synthesis, and all historical quick-win PRs.
  - **HyroTrader:** `/audit/hyrotrader/` — prop-firm style picks (crypto perps, $5K 2-step challenge). Has QuanEngine 18-strategy consensus voting, live 1h playbook signals, pick performance validator, ML edge optimizer.
  - **AI Tournament:** `/audit/ai-tournament.html` — multi-model prediction tournament (GPT-4o, DeepSeek V4, Llama-4-Scout, Grok-3, Cursor Agent, Ring-2.6-1T, Mercury V2, Gemini 2.5 Pro). Forward-tested. Phase 1B in progress — NO model has n≥30 resolved picks yet, so no leaderboard ranking exists.
  - **Portfolio History:** `/audit/portfolio_history.html` — 26 sim portfolios, JS-driven
  - **Anti-Overfit:** `/audit/anti_overfit.html` — DSR/PBO/SPA statistical gate results per strategy
- Models cannot fetch these reliably — pull the local JSON and reason on it (never let a model claim it "fetched" a URL).

## Data Sources (read, never invent)

| Source | Field | Purpose |
|--------|-------|---------|
| `audit_dashboard/data/pf_registry.json` | by_asset_class_policy_clean_net | **CANONICAL** per-class PF/WR/net-of-slippage. Single source of truth. |
| `audit_dashboard/data/pf_registry.json` | by_asset_class_strategy_policy_clean_net | **CANONICAL** per-strategy per-class PF/WR |
| `audit_dashboard/data/money_ready_verdict.json` | classes.*.verdict | DSR/PBO/SPA/statistical gates per class |
| `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` | n, WR, PF | Verdict-grade resolved_n per class |
| `audit_dashboard/data/dashboard_data.json::walkforward.by_class` | oos_wr, oos_sharpe | OOS verification |
| `audit_dashboard/data/dashboard_data.json::fwd_vs_bt_divergence.rows` | BT vs OOS WR gap | Overfit detector |
| `audit_dashboard/data/nav_surface_edge_matrix.json` | per-surface × per-class | Which audit tabs have edge |
| `audit_dashboard/data/pick_summary_stats*.json` | 48h/14d/90d WR/PF | Recent performance windows |
| `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS` | current blocks | Active gate |
| `docs/PERFORMANCE_CHARTER.md` | Tier thresholds | T1/T2/T3 definition |
| `reports/QUANT_STRATEGY_REVIEW_2026-05-28.md` | full quant review | Latest per-class + per-strategy + TP/SL analysis |

## Incidents + Enhancements Documentation

Every incident and enhancement is tracked in MySQL (`INCIDENT_*` / `ENHANCEMENT_*` tables in `ejaguiar1_stocks`) and rendered to:
- **Live HTML:** `https://findtorontoevents.ca/audit/incidents.html` (filterable, per-class drill-downs)
- **Live JSON feed:** `audit_dashboard/data/incidents_enhancements_feed.json`
- **Updates page summary:** `https://findtorontoevents.ca/updates/` (top incidents + enhancements per class)

### Date/Time Convention
- All timestamps in incidents.html are **EST/EDT** (Eastern Time). The nightly renderer (`incidents-enhancements-nightly.yml`) stamps each row with the refresh time.
- `updates/index.html` entries are date-stamped (e.g., "May 28, 2026", "May 27, 2026 — 10:31 EDT").
- When creating new incidents/enhancements, always assign `date_est` and `time_est` fields.

### How to Add Incidents/Enhancements
```bash
# CLI tool for tracking:
python tools/audit_pick_funnel/cli_track.py --type incident --severity P0 --title "..." --component "..." --class OVERALL
python tools/audit_pick_funnel/cli_track.py --type enhancement --impact HIGH --effort S --title "..." --class OVERALL
```

## AI Tournament Validation (READ THIS before quoting any model WR)
- **Phase 1B in progress** as of 2026-05-28. Most models have <30 resolved picks. No leaderboard ranking exists.
- **DO NOT quote grok3/llmama4_scout/cursor_agent win rates** from the tournament page — those are from the OLD model summary section which aggregates unvalidated backtest-era data, NOT forward-test results.
- The canonical forward-test data is in `audit_dashboard/data/ai_tournament_picks_latest.json`. Check `status` field: only `WIN`/`LOSS` rows are resolved. Most picks show `status=OPEN`.
- The rules page states: **min n=30 resolved picks per model per asset class before ranking.** As of 2026-05-28, zero models qualify.

## Pick Funnel Deep-Dive (for data-quality validation)
The pick_funnel.html contains:
1. **48h per-class rollup** — ground truth from `at_raw_picks` table, zero curation lag
2. **Navigation-surface edge matrix** — per filter tab (VA, Smart, HC, ELITE) × per class: n, WR, PF, train/holdout PF, Bonferroni significance, auto "why-no-edge" string
3. **Top edges per class (90d)** — cells with WR≥55% (Bayesian-shrunk) + PF≥1.5 + n≥20
4. **DISPUTED banners** — flags stats that don't reconcile with raw DB (e.g., CRYPTO Smart Picks WR 78.9% vs raw DB 39.4%)
5. **Swarm verdict** — 3-engine (deepseek+cerebras+gemini) independent verification of claimed edges

**When validating stats from pick_funnel or any source**: always cross-check against `pf_registry.json::by_asset_class_policy_clean_net` — this is the deduped, policy-excluded, net-of-slippage canonical view. Any WR/PF claim that doesn't match the canonical view is either using a different filter pipeline or is contaminated.

## Freshness Gate (FAIL-FAST if >2h stale)

```python
import json; from pathlib import Path; from datetime import datetime, timezone
d = json.loads(Path("audit_dashboard/data/dashboard_data.json").read_text())
age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(d["generated_at"].rstrip("Z")).replace(tzinfo=timezone.utc)).total_seconds()/3600
assert age_h < 2, f"STALE: {age_h:.1f}h — abort"
```

## Weekly Filter Output Format

After the audit, produce `reports/weekly_filter_<UTC>.md`:

```markdown
# Weekly Real-Money Filter — <DATE>

## EQUITY Top Picks Filter
- Criteria: elite_score≥60, asset_class=EQUITY, status=OPEN, direction=LONG
- Expected WR (historical analog): XX% (n=YY)
- Expected PF (historical analog): X.XX
- Kelly size: X.X% of account per pick

## [Repeat per class that has n≥100 resolved picks]

## How to Apply
1. Open findtorontoevents.ca/audit
2. Apply filter: [specific UI filter steps]
3. Size per Kelly recommendation
4. Exit: follow TP/SL as set on pick

## Risk Controls
- Max per-pick: X% of account (Kelly 0.25-fraction)
- Daily soft-stop: -2% total PnL triggers pause (Hyro overlay)
- DD halt: if rolling_30d drawdown > 30%, pause all sizing
```

## Execution Workflow

### Step 1 — Freshness preflight (fail-fast)
Run the freshness gate above. If stale, surface + ask.

### Step 2 — Per-class baseline
Read `asset_class_health`. Per class: n, WR, PF, Tier vs charter.

### Step 3 — Identify proven filter per class
For each class with resolved_n≥50, query (or derive from `dashboard_data.json`) the top-performing:
- Strategy family
- Direction (LONG vs SHORT)
- Confidence bucket (high/medium)
- Time-of-day window (if data available)

### Step 4 — Compute Kelly sizing
For each proven filter, use `alpha_engine/kelly_position_sizer.py::compute_position_size()` to output:
- % of account per pick
- Expected position size in USD at $10k account

### Step 5 — Write weekly filter report
Output `reports/weekly_filter_<UTC>.md` with filter per class + sizing.

### Step 6 — Verify picks hit the filter
Pull current OPEN picks from `audit_dashboard/data/dashboard_data.json::systems` or JSON pick sources. Apply each filter, count matches.

### Step 7 — Commit report
```bash
git add reports/weekly_filter_<UTC>.md
git commit -m "feat(edge): weekly real-money filter + Kelly sizing <DATE>"
```

## Quality Bar
- Code: clean, typed, follows project conventions
- Design: looks like a well-funded startup shipped it
- Output: survives a senior code review
- Docs: every new pattern / env var / decision logged

## Constraints (same as money-maker-ready v1.1)
- NEVER edit `audit_dashboard/index.html`
- NEVER run `audit_trail/dashboard_generator.py` locally
- NEVER add to BLOCKED_ASSET_STRATEGY_PAIRS without explicit user approval
- NEVER claim performance without `(asset_class | n | timeframe)` triple
- NEVER push without pulling first

## Final Deliverable
- Confirmation each success criterion is satisfied
- Every file created / modified
- How to run / test / deploy
- Proof (test output + filter + URL)
- Decisions made + known limitations

---

# PART 2 — Orientation map for IDE agents (where to hunt edge, what to trust)

> This half of the skill exists to **point any IDE agent at the right surfaces, the
> right database, and the right validation discipline** so they can review existing
> asset-class performance, build new per-class strategies, and not get fooled by
> inflated dashboard cells. Read this before touching anything.

## Databases & credentials (NEVER hard-code; read at runtime)

- **Secrets file:** `~/dbpasses.txt` (gitignored, home dir — outside the repo). Holds every DB password + API key. Read it at runtime; never paste a secret into a committed file.
- **Server:** MySQL host `mysql.50webs.com`, port 3306.
- **The two databases that matter for edge:**
  - **`ejaguiar1_stocks`** — the **live production pick + outcome store.** Key tables:
    - `at_raw_picks` — every raw signal from every source (the "pick funnel" input). Cols incl. `source_system, asset_class, direction, entry_price, take_profit, stop_loss, status, pnl_pct, signal_timestamp, closed_at, dedup_hash, was_stale/was_banned/was_demoted`.
    - `trading_picks` — the curated/scored pick ledger (⚠ has the known P0 rot: ~29M OPEN bloat, ghost rows, ~33% pnl-integrity mismatch — see incidents.html; **never write to it blindly**).
    - `tournament_picks` — AI Tournament picks (39 models). Clean: only OPEN/WIN/LOSS, 0 pnl contradictions.
    - `INCIDENT_*` / `ENHANCEMENT_*` — drive `/audit/incidents.html` (see below).
  - **`ejaguiar1_backtests`** — historical backtest results per strategy. Use to find **orphan backtested edges** (strategies with PF>1.5 in backtest but no production wiring — the Wire-Up Rule gap).
  - Password convention (per repo memory): `<dbname-suffix>1234560` e.g. `ejaguiar1_stocks` → `stocks1234560`; prefer the env var `DB_PASS_STOCKS` / the `~/dbpasses.txt` entry over hard-coding.
- Connect read-only for audits: `pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=<from dbpasses>, database='ejaguiar1_stocks')`.

## The /audit surfaces (what each page is, and how much to trust it)

| URL | What it is | Trust level |
|-----|-----------|-------------|
| `findtorontoevents.ca/audit/` | Main dashboard. Per-class MAJOR-GOAL tiles now fetch **live `money_ready_verdict.json`** (policy-clean verdict). TRUTH-LAYER banner discloses the raw-vs-filtered gap. | Headline tiles = policy-clean (trust); raw `at_raw_picks` rollups = relic (distrust without dedup). |
| `findtorontoevents.ca/audit/pick_funnel.html` | Per-asset-class funnel: raw signal → filters → Smart Picks / High-Conviction / Money-Ready, with leakage flags (`dup_groups`, `single_source_concentration`, `EXPIRED→WON`). | **Read the caveats, not the headline.** A class can show 65–88% WR that is one source + dup-inflated. |
| `findtorontoevents.ca/audit/ai-tournament.html` | 39 cloud AI models forward-tested per class. Leaderboard ranks n≥30 resolved by CI-adjusted score. | Forward-test WRs are **real but small-n** (see validation below). |
| `findtorontoevents.ca/audit/hyrotrader` | Prop-firm-style picks (FTMO/Hyro overlay — drawdown-gated sizing). | Evaluate against prop-firm rules (max daily DD, total DD) not just WR. |
| `findtorontoevents.ca/audit/incidents.html` | Auto-generated from `INCIDENT_*`/`ENHANCEMENT_*` tables in `ejaguiar1_stocks`. ~45 incidents / ~47 enhancements. | Source of the open P0 backlog. |
| `findtorontoevents.ca/updates/index.html` | Chronological **enhancement-plan + incident-resolution log** (newest-first). Check here FIRST for prior enhancement plans before writing a new one. | Authoritative history of what was tried. |

## Incidents / Enhancements documentation (action item)

`/audit/incidents.html` is generated from the `INCIDENT_*` / `ENHANCEMENT_*` DB tables.
**Each incident/enhancement should carry a date/time in EST and (for enhancements) a
target timeline.** If a row lacks a timestamp or an enhancement lacks a plan/timeline:
add `created_at`/`updated_at` (render as `America/New_York` EST on the page) and an
`enhancement_plan` + `target_date` column, and cross-link the matching
`updates/index.html` card. Prior enhancement plans live in `updates/index.html` —
reuse/extend them rather than duplicating.

## VETTED-STATS DISCIPLINE (mandatory before citing any class WR/PF)

Dashboard headline cells are routinely inflated. Before trusting a number, compute it
yourself from the DB with ALL of these:
1. **Dedup** on `(symbol, signal_timestamp, source_system)` (or `dedup_hash`) — raw rows double-count.
2. **Single-source check** — if >60% of decisive picks come from one `source_system`, it is concentration, not edge.
3. **Outlier cap** — a PF over ~10 is almost always a few corrupt/outlier `pnl_pct` rows; cap or winsorize and recompute.
4. **Min-n** — n≥100 decisive for a class verdict (n≥30 for a single strategy); below that label INSUFFICIENT-N.
5. **OOS / window stability** — recompute over 2d/7d/30d; if WR/PF swings wildly the "edge" is noise.
6. **Anomaly exclusion** — drop rows where `resolved_at < submitted_at` (impossible) or TP/SL sit on the wrong side of entry (`normalize.py::is_resolution_trustworthy`).

### Worked example — FUTURES is NOT a real edge (2026-05-28 validation)
`pick_funnel` showed FUTURES **65.09% WR / PF 4.111 (48h)**. Direct `at_raw_picks` query:
**100% single-source (AlphaEngine)**, dup groups present, and window-unstable —
2d 43.6%/PF2.13, 7d 73.6%/PF4.79, **30d 50.6%/PF 130.47** (a PF of 130 is mathematically
absurd = outlier/corruption). Peer review (claude-haiku-4.5 via the LiteLLM proxy)
concurred: artifact, not edge. **Lesson: a high pick_funnel WR with a
`single_source_concentration` flag is a relic until dedup + outlier-cap + multi-source + OOS.**

### Worked example — AI Tournament WRs ARE real but small-n (2026-05-28 validation)
Validated against `tournament_picks`, anomaly-aware:
- `grok3` "300 picks / 58.4%" → **true**, but "300" is the **merged** `grok3`+`grok3_direct`; raw `grok3` alone = 187 picks / 67.9% on 28 resolved. Clean (drop 5 TS-anomaly + 1 TP/SL) → 59.0% on 83.
- `llama4_scout` 61.4% → clean 61.5% on 52 resolved. `cursor_agent` 66.1% → clean 65.5% on 55.
These survive anomaly filtering, but are **forward-test on 52–89 resolved (wide CIs), ~47% of picks still OPEN** — institutional-grade requires n≥100 + OOS.

## Smart Picks parity (action item)

The dashboard "Smart Picks" tab/button should be reproducible from the DB. To feed the
pick funnel: pull the Smart-Picks-eligible cohort from `ejaguiar1_stocks` (the rows that
pass `passes_smart_gate` / `calculate_smart_score`), recompute WR/PF with the vetted
discipline above, and write the result into the `pick_funnel` data so the funnel's
"Smart Picks" column reflects DB truth, not a static cell.

## Where IDE agents should hunt edge (the actual job)

1. **Per asset class, review existing performance** in `ejaguiar1_stocks` (live) + `ejaguiar1_backtests` (historical). Find the strategies with clean PF>1.5 / WR>50 at n≥100.
2. **Find orphan backtested edges** — strategies strong in `ejaguiar1_backtests` but with no production caller (Wire-Up Rule). Wire the best ones in.
3. **Build new per-class strategies** where the class is failing (today 0/6 classes pass Tier-2 policy-clean): EQUITY only proven sleeve is `stocks_rsi2_pullback`; CRYPTO/FOREX/COMMODITY need diversified, multi-source, dedup-clean signals.
4. **Always size with Kelly/Hyro overlay + DD-halt** (`alpha_engine/kelly_position_sizer.py`).
5. **Document proven edge** as an `updates/index.html` card (insert ABOVE the auto-incidents marker) + FTP-deploy.

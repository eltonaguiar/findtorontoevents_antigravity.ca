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

## MANDATORY DATA-INTEGRITY FILTERS (added 2026-06-09 — DO NOT skip)

The 2026-06-06 per-asset-class edge audit proved that **raw `at_pick_outcomes` win-rates are inflated artifacts**, not edge. Before you compute ANY WR/PF/verdict, apply ALL of these or your numbers are worthless (a strategy showing "63% WR / PF 5.35" was really 73 of 2040 clean rows). Reference fixes: `tools/build_pf_registry.py`, `tools/picks_now_professional.py:load_db_edge`, `tools/reresolve_intrabar.py`, `reports/2026-06-06-per-asset-class-edge-reality-and-academic-roadmap.md`, `reports/2026-06-06-money-ready-screen-clean-cohort.md`.

1. **Exclude backfill labels** — `resolver_version NOT LIKE 'backfill%'` AND `resolved_at IS NOT NULL`. 68–100% of resolved rows per class are retroactive backfill never validated against live price; including them removed ~78% of WON/LOST rows as contamination.
2. **Exclude banned sources** — `strategy NOT IN (Predictions, sandbox_opposite, rapid_fire, incubator_gainer, luxalgo_filters, multi_asset_copytrader, forex_copy_trader, signal_validation, multi_asset_cot, regime_terminal, multi_asset_scanner, myfxbook_retail_contrarian, ig_contrarian_sentiment)`.
3. **Per-class sane-pnl guard** — `ABS(pnl_pct) <= CASE asset_class WHEN 'FOREX' THEN 20 WHEN 'COMMODITY' THEN 30 WHEN 'BOND' THEN 25 WHEN 'CRYPTO' THEN 95 ELSE 50 END`. Drops reverse-split + price-feed-bug artifacts (e.g. CADJPY=X WON +428%, NZDUSD=X −100%) — one such "win" alone inflates a strategy's PF.
4. **Count EXPIRED as a NON-WIN** — WR = `WON / (WON+LOST+EXPIRED+FLAT)`. 70–95% of picks are `TIME_EXPIRED`; dropping them (the old `status IN ('WON','LOST')`) inflated FX from a true ~6% to a displayed 58.8%.
5. **Require intrabar validation before trusting a WR** — the production resolver does NOT replay intrabar OHLC, so a "TP_HIT" may have hit SL first. `tools/reresolve_intrabar.py` (de-biased, fixed-horizon) showed CRYPTO drops from 52.3% → 42.9% WR / PF 1.22, with 26.4% of picks reclassified TP→SL. A WR is not money-grade until it survives intrabar replay.
6. **Reject single-snapshot / resolver-version artifacts** — require ≥3 distinct months at n≥30/month. The same data yields a 4–6× PF spread by resolver version (CRYPTO June PF 0.51 vs 2.15). A strong recent month is usually selection bias, not edge.

**Money-ready bar (only after 1–6):** n≥100 clean, ≥3 months, PF>1.5, WR>52% (EXPIRED-inclusive), intrabar-validated, multi-source — THEN paper-pilot ≥4 weeks forward before any real capital. As of 2026-06-09 the clean-cohort screen returns **0 confirmed survivors** in any class. The gating dependency is OHLCV history depth (`crypto_ohlcv` holds only ~30 days of 1h bars) — backfill it before full intrabar re-resolution.

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
  import pymysql
  conn = pymysql.connect(**creds)
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

## Current Asset Class Snapshot (RE-VERIFY every session — two layers)

> **Layer A — official gates:** `money_ready_verdict.json` (`n_resolved` = policy-clean closed picks). **0/9 pass Tier-2** as of 2026-06-08.
> **Layer B — honest clean cohort:** `at_pick_outcomes` with ALL mandatory filters (§ MANDATORY DATA-INTEGRITY FILTERS). Use Layer B to answer "do we REALLY have edge?"

### Layer A — money_ready_verdict.json (2026-06-08T08:09 UTC)

| Class | n_resolved | WR | PF | Verdict | Top blocker |
|-------|-----------|-----|------|---------|-------------|
| CRYPTO | 175 | 48.6% | 0.92 | NOT_READY | WR<50%, MDD 100%, PF<1.5 |
| EQUITY | 71 | 53.5% | 1.84 | INSUFFICIENT_DATA | n<100, MDD 33% |
| FOREX | 25 | 24.0% | 0.077 | INSUFFICIENT_DATA | catastrophic PF; KILL/MUTATE |
| COMMODITY | 18 | 27.8% | 0.28 | INSUFFICIENT_DATA | n<100 |
| ETF | 20 | 25.0% | 0.37 | INSUFFICIENT_DATA | n<100 |
| FUTURES | 20 | 30.0% | 1.05 | INSUFFICIENT_DATA | n<100, WR<50% |
| BOND | 1 | 100% | — | INSUFFICIENT_DATA | n<100 |

Reproducer: `python3 -c "import json;d=json.load(open('audit_dashboard/data/money_ready_verdict.json'));print(d['generated_at']);[print(k,v['n_resolved'],round(v['wr']*100,1),v['pf'],v['verdict']) for k,v in d['classes'].items()]"`

### Layer B — clean cohort (at_pick_outcomes, filters 1–4, 2026-06-09)

| Class | n (clean) | WR (EXPIRED-inclusive) | PF | Verdict |
|-------|-----------|------------------------|-----|---------|
| CRYPTO | 1773 | 46.6% | 1.25 | NO_EDGE (intrabar ~43%/PF 1.22) |
| EQUITY | 358 | 32.4% | 1.30 | NO_EDGE |
| FOREX | 117 | 8.5% | 0.63 | NO_EDGE |
| COMMODITY | 46 | 50.0% | 1.04 | INSUFFICIENT_DATA |
| ETF | 2 | 0% | 0 | INSUFFICIENT_DATA |

**Money-ready survivors (n≥50, ≥3mo, PF>1.5, WR>52%, intrabar): 0.** See `reports/OBS_FINDING_JUNE8.MD`.

### REJECT without re-verify (known false claims)

| Claim | Why reject |
|-------|------------|
| FOREX 14d WR 64% / PF 2.43 | Clean 14d FOREX WR **5.0%** |
| GBPUSD WR 58.8%, n=114 | True ~7%; 87% expired |
| stocks_rsi2_pullback n=894 / PF 2.68 | 14d WR 29.9% |
| mega_mutation T1 without intrabar | Resolver does not replay intrabar |
| bt_backtest_trades 32.6M as live edge | Backtest overfit trap |

## SAVE THE SYSTEM — Rescue protocol (coin-flip → statistical edge)

Execute in order. **Do NOT wire academic sleeves or size up until P0 completes.**

| Priority | Action | Tool / file | Status |
|----------|--------|-------------|--------|
| **P0** | Quarantine backfill from verdict math | `build_pf_registry.py` | ✅ shipped |
| **P0** | Sane-pnl + EXPIRED-honest overlays | `picks_now_professional.py` | ✅ shipped |
| **P0** | Intrabar OHLC replay resolver | `reresolve_intrabar.py` | dry-run done; `--apply` gated |
| **P0** | Deepen OHLCV history (≥180d 1h) | `crypto_ohlcv` ingest | **BLOCKED** — ~30d today |
| **P0** | TP/SL vs horizon calibration | `production_scanner.py` | caps wired; legacy 80%+ expire |
| **P1** | Re-screen on clean+intrabar cohort | SQL + reresolve report | pending OHLCV |
| **P1** | Paper-pilot survivors (≥4wk forward) | `forward_test_only=1` | not started |
| **P2** | Wire TSMOM / residual momentum / carry | sidecar modules | after P0 only |
| **P3** | FOREX kill/mutate + ban unverified sizing | incidents + roadmap page | in progress |

**Roadmap:** `/audit/edge_validation_roadmap.html` | **Vault audit:** `reports/OBS_FINDING_JUNE8.MD` | **Obsidian:** `obsidian-notes/reference/edge-rescue-roadmap.md`

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
- **Earlier enhancement plans:** `https://findtorontoevents.ca/updates/index.html` — chronological log of ALL prior enhancement plans, EAGLE reviews, multi-AI consult results, and institutional-readiness 90-day plans. Check here BEFORE writing a new enhancement plan to avoid duplicating work.

### ⚠️ Date/Time Convention — KNOWN GAP (P0)
- **Current state:** incidents.html timestamps are rendered as **UTC ISO 8601** (`2026-05-28 21:06 UTC`), NOT EST/EDT. The nightly renderer stamps UTC.
- **Required state:** All incident/enhancement rows MUST carry `date_est` and `time_est` fields rendered in **America/New_York (EST/EDT)**. Enhancements should also have `enhancement_plan` + `target_date` with proper timelines. Many rows currently lack these — tracked as a P0 incident.
- `updates/index.html` entries ARE date-stamped correctly (e.g., "May 28, 2026", "May 27, 2026 — 10:31 EDT") — this is the convention to follow.

### How to Add Incidents/Enhancements
The CLI uses **subcommands** (`incident` / `update-incident` / `enhancement` / `list`), NOT a `--type` flag. `--class` must be one of the per-class table suffixes (OVERALL/CRYPTO/EQUITY/FOREX/COMMODITY/ETF/BOND/FUTURES/PENNY/STOCKS):
```bash
# verify args first:  python tools/audit_pick_funnel/cli_track.py incident --help
python tools/audit_pick_funnel/cli_track.py incident --class OVERALL --severity P0 --title "..." --component "..." --fix "..." --reporter "..."
python tools/audit_pick_funnel/cli_track.py enhancement --class OVERALL --impact HIGH --effort S --title "..." --success-metric "..."
python tools/audit_pick_funnel/cli_track.py list --kind enhancement --class OVERALL          # review existing
```
- `created_at`/`updated_at` are auto-stamped (verified populated: 0/22 incidents NULL). They are stored UTC-naive and the renderer prints UTC — **EST conversion is a known gap (see above).**
- ⚠️ **`enhancement` has NO `--target-release`/`--target-date`/`--plan` argument** — which is why all 32 enhancement rows have `target_release = NULL` (the missing-timeline gap). Until the arg is added, set timelines via a direct `UPDATE ENHANCEMENT_<class> SET target_release='2026-Q3' WHERE enhancement_id=N`. `success_metric` IS settable (and populated).

## HyroTrader — Prop Firm Style Picks (`/audit/hyrotrader/`)

The HyroTrader surface is the **prop-firm-style** arm of the audit pipeline:
- **Universe:** crypto perps (BTC, ETH, SOL, etc.) on a simulated $5K 2-step challenge (FTMO/Hyro rules).
- **Engine:** QuanEngine 18-strategy consensus voting → live 1h playbook signals → pick performance validator → ML edge optimizer.
- **Evaluation criteria:** prop-firm rules (max daily DD, total DD, profit target) — NOT just WR/PF. A pick can have 60% WR but still fail the challenge if the losers are too deep.
- **Key tables:** `ejaguiar1_stocks` tables with `source_system LIKE '%hyro%'` or `source_system LIKE '%quan_engine%'`.
- **Trust level:** Evaluate against prop-firm risk rules, not raw performance stats. The Hyro overlay adds drawdown-gated sizing that can veto otherwise good signals.

**⚠️ Current state (2026-05-28):** The HyroTrader trade journal shows **"No journal trades logged yet"** — the prop-firm challenge has not yet accumulated executed trades. The infrastructure (QuanEngine voting, playbook signals, validator, optimizer) is wired but not actively producing closed picks. This is a priority gap for the prop-firm narrative.

**For IDE agents reviewing HyroTrader:** Check the daily DD limit compliance, not just cumulative WR. A strategy with WR 55% but MDD 35% will blow a prop-firm challenge. Focus on getting the first 30+ resolved trades into the journal before evaluating edge.

## AI Tournament Validation (READ THIS before quoting any model WR)
- **Leaderboard live** as of 2026-05-29. Scoring: `lower_95% WR x lower_95% PF`, min n=30 resolved per model.
- **T1 tier (4 models)** — these have n>=30 resolved AND PF_CI_lo > 1.0:
  - `deepseek_v4`: 178 picks, 43 resolved, WR=55.81%, PF=3.715, score=0.7495 (Rank 1)
  - `cursor_agent`: 113 picks, 59 resolved, WR=66.10%, PF=2.354, score=0.6586 (Rank 2)
  - `llama4_scout`: 115 picks, 57 resolved, WR=61.40%, PF=2.261, score=0.574 (Rank 3)
  - `grok3`: 300 picks (merged grok3+grok3_direct), 89 resolved, WR=58.43%, PF=2.016, score=0.5587 (Rank 4)
- **T2 tier:** ring_261T (60 resolved, PF_CI_lo=0.876), llm7_qwen (55 resolved, PF_CI_lo=0.798)
- **T3 tier:** 9 models with n>=30 resolved but PF_CI_lo < 1.0 (edge not statistically proven)
- **BUILDING tier:** 10+ models with <30 resolved — NOT rank-eligible yet
- **Caveat:** ~47% of all tournament picks are still `status=OPEN`. Institutional-grade requires n>=100 resolved + OOS stability. These are forward-test results, not proven edges.
- The canonical data is in `audit_dashboard/data/ai_tournament_picks_latest.json`. Check `status` field: only `WIN`/`LOSS` rows are resolved.

### AI Tournament deep validation — what's actually true (2026-05-29)
The following stats were validated against `tournament_picks` table with anomaly-aware queries:
- **`grok3` "300 picks / 58.4% WR"** → **true.** 300 is merged `grok3`+`grok3_direct`; 89 resolved, 52 wins. WR=58.43%, PF=2.016, PF_CI_lo=1.163. T1 rank 4.
- **`llama4_scout` 61.4% WR** → **true.** 115 picks, 57 resolved, 35 wins. WR=61.40%, PF=2.261, PF_CI_lo=1.185. T1 rank 3.
- **`cursor_agent` 66.1% WR** → **true.** 113 picks, 59 resolved, 39 wins. WR=66.10%, PF=2.354, PF_CI_lo=1.234. T1 rank 2. Highest WR among all ranked models.
- **`deepseek_v4`** → T1 rank 1 (highest score). 178 picks, 43 resolved, WR=55.81%, PF=3.715.
- **The catch:** ~47% of all tournament picks are still `status=OPEN`. These WRs are forward-test on 43–89 resolved picks (wide confidence intervals). Institutional-grade requires n>=100 resolved + OOS stability.
- **11 models show WR above 60%** — unusually many. Possible explanations: (a) these are top AI models making directional calls on volatile assets, (b) selection bias in which models survived to ranking, (c) TP/SL asymmetry favoring hit-rate over net PnL.

## Pick Funnel Deep-Dive (for data-quality validation)
The pick_funnel.html contains:
1. **48h per-class rollup** — ground truth from `at_raw_picks` table, zero curation lag
2. **Navigation-surface edge matrix** — per filter tab (VA, Smart, HC, ELITE) × per class: n, WR, PF, train/holdout PF, Bonferroni significance, auto "why-no-edge" string
3. **Top edges per class (90d)** — cells with WR≥55% (Bayesian-shrunk) + PF≥1.5 + n≥20
4. **DISPUTED banners** — flags stats that don't reconcile with raw DB (e.g., CRYPTO Smart Picks WR 78.9% vs raw DB 39.4%)
5. **Swarm verdict** — 3-engine (deepseek+cerebras+gemini) independent verification of claimed edges

### WR Calculation Inconsistency (P1 data-quality issue)
Three different WR formulas are in use across the system:

| Surface | Formula | Flat Handling | Source |
|---|---|---|---|
| Main dashboard | `wins / (wins + losses + flat)` | Included in denominator | `dashboard_generator.py::_calculate_win_rate_pct` |
| Pick funnel | `wins / (wins + losses)` | EXCLUDED (only "decisive") | `extract_funnel.py` line 212 |
| AI tournament | `n_wins / n_resolved` | Flat counts as loss | `ai-tournament.html` line 504 |

This means the same pick can show different WRs depending on which surface you look at. When cross-validating, always check which formula is being used.

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

## Per-Class Performance Snapshot (2026-05-29, pick funnel 90d)

| Class | Scanned | Decisive | WR% | Verdict | Key Issue |
|---|---|---|---|---|---|
| CRYPTO | 16,750 | 3,559 | 45.97% | FAIL | Smart Picks DISPUTED (78.9% vs raw 39.4%) |
| FOREX | 14,987 | 2,345 | 40.72% | FAIL | All strategies losers except concentrated USDJPY |
| COMMODITY | 8,283 | 900 | 37.11% | FAIL | COT over-emission, headline PF contaminated |
| EQUITY | 2,122 | 106 | 49.06% | INSUFF-N | Only 106 decisive; stocks_rsi2_pullback sole proven sleeve |
| FUTURES | 412 | 18 | 11.11% | FAIL | Zombie tile; real futures hidden under COMMODITY |
| ETF | 89 | 16 | 18.75% | INSUFF-N | All 5 strategies on probation, zero verified forward trades |
| BOND | 158 | 14 | 21.43% | FAIL | antigravity_bond 0% WR on n=9 — kill emission |
| MEME | 87 | 47 | 34.04% | FAIL | Small sample, high loss rate |
| PENNY | 8 | 7 | 28.57% | INSUFF-N | Deep oversold BLOCKED by Gate 0 |

**Nav Surface Edge Matrix: ZERO PROVEN EDGES** on any surface after Bonferroni correction (alpha=0.00625). Closest candidates all failed either Bonferroni or holdout validation.

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
| `findtorontoevents.ca/audit/pick_funnel.html` | Per-asset-class funnel: raw signal → filters → Smart Picks / High-Conviction / Money-Ready, with leakage flags (`dup_groups`, `single_source_concentration`, `EXPIRED→WON`), DISPUTED banners, nav-surface edge matrix, swarm verdicts. | **Read the caveats, not the headline.** A class can show 65–88% WR that is one source + dup-inflated. See "Pick Funnel Deep-Dive" below. |
| `findtorontoevents.ca/audit/ai-tournament.html` | 39 cloud AI models forward-tested per class. Leaderboard ranks n≥30 resolved by CI-adjusted score. | Forward-test WRs are **real but small-n** (see validation below). |
| `findtorontoevents.ca/audit/hyrotrader` | Prop-firm-style picks (FTMO/Hyro overlay — drawdown-gated sizing). | 0 journal trades logged (2026-05-28). Evaluate against prop-firm rules (max daily DD, total DD) not just WR. |
| `findtorontoevents.ca/audit/incidents.html` | Auto-generated from `INCIDENT_*`/`ENHANCEMENT_*` tables in `ejaguiar1_stocks`. ~45 incidents / ~47 enhancements. ⚠️ Timestamps currently UTC, needs EST. | Source of the open P0 backlog. |
| `findtorontoevents.ca/updates/index.html` | Chronological **enhancement-plan + incident-resolution log** (newest-first). Check here FIRST for prior enhancement plans before writing a new one. | Authoritative history of what was tried. |

## Incidents / Enhancements documentation (action item)

`/audit/incidents.html` is generated by `tools/audit_pick_funnel/render_incidents_page.py`
from the `INCIDENT_*` / `ENHANCEMENT_*` DB tables (nightly via `incidents-enhancements-nightly.yml`).
**Each incident/enhancement should carry a date/time in EST and (for enhancements) a
target timeline.** Two concrete, VERIFIED gaps (2026-05-28) for the next IDE agent to close:

1. **EST rendering missing.** `render_incidents_page.py:317` stamps only `generated_at` in **UTC** and does no per-row timezone conversion. Tables (`INCIDENT_*`/`ENHANCEMENT_*`) DO have `created_at`/`updated_at` datetimes (populated — 0/22 incidents NULL), stored UTC-naive. **Fix:** in the renderer, convert each row's `created_at`/`updated_at` via `zoneinfo.ZoneInfo("America/New_York")` and render the per-row date in EST/EDT, matching the `updates/index.html` convention ("May 28, 2026 — 10:31 EDT").
2. **Enhancement timelines missing.** All **32/32** `ENHANCEMENT_*` rows have `target_release = NULL`, and `cli_track.py enhancement` exposes no timeline arg. **Fix:** add `--target-release` to `cli_track.py` (write to the existing `target_release` column) and optionally an `enhancement_plan` column; backfill the open enhancements with quarter/target dates; cross-link each to its matching `updates/index.html` card.

Prior enhancement plans live in `updates/index.html` (the institutional-readiness 90-day plan, EAGLE reviews, multi-AI consults) — **read it first and reuse/extend, don't duplicate.**

## VETTED-STATS DISCIPLINE (mandatory before citing any class WR/PF)

Dashboard headline cells are routinely inflated. Before trusting a number, compute it
yourself from the DB with ALL of these:
1. **Dedup** on `(symbol, signal_timestamp, source_system)` (or `dedup_hash`) — raw rows double-count.
2. **Single-source check** — if >60% of decisive picks come from one `source_system`, it is concentration, not edge.
3. **Outlier cap** — a PF over ~10 is almost always a few corrupt/outlier `pnl_pct` rows; cap or winsorize and recompute.
4. **Min-n** — n≥100 decisive for a class verdict (n≥30 for a single strategy); below that label INSUFFICIENT-N.
5. **OOS / window stability** — recompute over 2d/7d/30d; if WR/PF swings wildly the "edge" is noise.
6. **Anomaly exclusion** — drop rows where `resolved_at < submitted_at` (impossible) or TP/SL sit on the wrong side of entry (`normalize.py::is_resolution_trustworthy`).

### Worked example — FUTURES is NOT a real edge (RE-VERIFIED 2026-05-28T23:20 UTC vs live DB)
`pick_funnel` showed FUTURES **65.09% WR / PF 4.111 (48h)**. A fresh `at_raw_picks` query
(decisive = `WON`/`LOST`, by `signal_timestamp`) destroys it:
- **Window-unstable:** 48h **0.0% WR** (9 resolved) → 7d **35.3%** (34) → 30d **57.2%** (747). A 0→35→57% swing across windows is textbook noise, not edge.
- **~95% single-engine concentration:** `alpha_engine_unified` (3575) + `AlphaEngine` (240) + `alpha_engine` (112) — all the same engine family. No multi-source corroboration.
- **Canonical agreement:** the policy-clean `money_ready_verdict.json` rates FUTURES **9.1% WR / PF 0.48 / INSUFFICIENT_DATA** — nowhere near 65%.
- Reproducer: `python3 -c "from tools.db_env import get_stocks_creds;import pymysql;c=pymysql.connect(**get_stocks_creds()).cursor();[ (c.execute('SELECT COUNT(*),SUM(status=\"WON\"),SUM(status=\"LOST\") FROM at_raw_picks WHERE asset_class=\"FUTURES\" AND signal_timestamp>=DATE_SUB(UTC_TIMESTAMP(),INTERVAL %s DAY)',(d,)), print(d,'d:',c.fetchone())) for d in (2,7,30)]"`

**Lesson: a high pick_funnel WR with a `single_source_concentration` flag is a relic until dedup + outlier-cap + multi-source + OOS. The earlier "30d PF 130.47" figure was itself an outlier-corrupted snapshot — re-derive, don't cite frozen numbers.**

### Worked example — AI Tournament WRs ARE real but small-n (RE-VERIFIED 2026-05-28T23:20 UTC vs `tournament_picks`)
Direct per-`model_id` query against the live `tournament_picks` table (status ∈ WIN/LOSS = resolved):
- `grok3` raw = **187 picks / 28 resolved (19W·9L) / 67.9% WR** ✅ exact match to claim.
- `grok3` "**300 picks / 58.4%**" = the **merged** `grok3`+`grok3_direct` = 187+113 = 300 total, 89 resolved (52W·37L), **58.4% WR** ✅ exact — "300" is two model_ids, disclose that.
- `llama4_scout` = 115 / 57 resolved (35W·22L) / **61.4%** ✅. `cursor_agent` = 113 / 59 resolved (39W·20L) / **66.1%** ✅.
All four claims are **REAL, not fabricated**. BUT they are forward-test on **28–89 resolved (wide CIs), ~50% of picks still OPEN** — institutional-grade requires n≥100 + OOS, and the tournament rules page itself gates ranking at n≥30 resolved per model per class.

## PeerReviewSwarmOptions — Multi-model data-quality validation

When a dashboard cell or pick-funnel stat looks suspicious, fan the question to multiple
AI models to cross-validate. Available peer-review options (in order of preference):

1. **LiteLLM proxy fan-out** — `http://localhost:4000/v1` with model `free-mode` or `paid-mode`. Fire the same prompt to N upstreams simultaneously; aggregate responses. Use `tools/consult_multi.py --fanout <N> --provider <provider>` for structured fan-outs.
2. **NVIDIA NIM multi-model** — `/consult-nvidia-models` skill. 10+ models on one provider; list/fan-out in one call.
3. **Cloudflare Workers AI** — `/consult-cloudflare` skill. 37+ models; good for budget-constrained cross-checks.
4. **Direct CLI consults** — `/consult-grok`, `/consult-gemini`, `/consult-codex`, `/consult-opencode`, `/consult-kilo`, `/consult-ring`, `/consult-cursor-agent`. Each is a standalone second opinion.
5. **Swarm verdict (3-engine)** — deepseek + cerebras + gemini. Already integrated into the pick_funnel `nav_surface_edge_matrix.json` builder. If those 3 agree on "artifact, not edge," trust it.

**When to use:** any time a pick_funnel cell shows WR>55% + PF>2 that isn't in the canonical `pf_registry.json::by_asset_class_policy_clean_net`. The FUTURES 65.09% WR / PF 4.111 was flagged by peer review in 30 seconds.

**The grounding rule:** ALWAYS include the canonical pf_registry numbers + hypothesis_registry.json rejected-hypothesis entries in the peer-review prompt. 5 models converged on a wrong answer (COMMODITY as #1 alpha) because they never saw the leakage evidence. Multi-AI consensus increases signal-to-noise ONLY when the prompt is grounded.

## Smart Picks parity (action item — not yet done)

The dashboard "Smart Picks" tab/button should be reproducible from the DB. Currently the Smart Picks
cohort stats shown on the dashboard and pick_funnel are **not fully vetted against raw DB data**.

**Current Smart Picks edge matrix state (2026-05-28, from `nav_surface_edge_matrix.json`):**
| Class | n | WR | PF | Verdict |
|-------|---|-----|------|---------|
| CRYPTO | 26 | 69.2% (60.9% shrunk) | 2.565 | **NO-EDGE** — single_source=100% (alpha_engine), n<26 |
| EQUITY | 14 | 50.0% | 2.105 | **NO-EDGE** — single_source=92% (kimi_riseoftheclaw), n<14 |
| ETF | 20 | 80.0% (65.0% shrunk) | 3.614 | **NO-EDGE** — overfit (train PF 15.2 vs holdout PF 1.19), single_source=100% |
| FOREX | 0 | — | — | no_closed_picks |
| FUTURES | 0 | — | — | no_closed_picks |

**How to feed Smart Picks stats into the pick funnel properly:**
1. Pull Smart-Picks-eligible cohort from `ejaguiar1_stocks`: rows that pass the canonical gates — `audit_trail/quality_gates.py::passes_smart_gate` (line 8915) + `calculate_smart_score` (line 9879), plus `passes_active_gate` (line 6493). Per-class scanners that emit the cohort live at `alpha_engine/crypto_smart_picks.py` (`scan_all`) and `alpha_engine/forex_smart_picks.py`; live perf is tracked in `alpha_engine/smart_picks_performance.py`. (smart_score ≥ 60, confidence ≥ 0.60).
2. Recompute WR/PF with the full vetted discipline (dedup, single-source check, outlier cap, min-n, OOS stability, anomaly exclusion).
3. Write the result into the `pick_funnel` data so the funnel's "Smart Picks" column reflects DB truth, not a static cell.
4. **Key gap:** Currently the Smart Picks column shows inflated numbers because it doesn't apply the same dedup + concentration checks that the Verified Alpha and nav_surface_edge_matrix do. The CRYPTO Smart Picks WR of 78.9% (PF 9.69) on the dashboard vs raw DB 39.4% (PF 0.371) is the canonical example of this gap.

## Where IDE agents should hunt edge (the actual job)

1. **Per asset class, review existing performance** in `ejaguiar1_stocks` (live) + `ejaguiar1_backtests` (historical). Find the strategies with clean PF>1.5 / WR>50 at n≥100.
   - Start with `pf_registry.json::by_asset_class_strategy_policy_clean_net` — this tells you exactly which strategies have real edges vs artifacts.
   - Cross-check with `pick_summary_stats_90d.json` for the dashboard-vs-raw-DB gap (the `db_raw_picks_90d` vs `dashboard_all_closed` divergence reveals filtering bias).
2. **Find orphan backtested edges** — strategies strong in `ejaguiar1_backtests` but with no production caller (Wire-Up Rule). Wire the best ones in.
3. **Build new per-class strategies** where the class is failing (today 0/8 classes pass Tier-2 policy-clean): EQUITY only proven sleeve is `stocks_rsi2_pullback`; CRYPTO/FOREX/COMMODITY/FUTURES need diversified, multi-source, dedup-clean signals.
4. **Validate AI Tournament picks** — the tournament has 39 models submitting picks across 9 asset classes, but ~47% are still OPEN. Focus on getting models to n≥30 resolved so the leaderboard can produce real rankings. Check `ai_tournament_picks_latest.json` for resolution status.
5. **Get HyroTrader producing trades** — the prop-firm challenge infrastructure is wired but has 0 journal trades. Priority is getting the first 30+ resolved picks through the QuanEngine → validator → pipeline.
6. **Fix incidents.html EST timestamps** — currently shows UTC, needs EST/EDT. Each incident/enhancement should also have enhancement_plan + target_date fields.
7. **Wire Smart Picks to raw DB** — currently shows inflated stats; needs dedup + concentration checks applied before displaying.
8. **Always size with Kelly/Hyro overlay + DD-halt** (`alpha_engine/kelly_position_sizer.py`).
9. **Document proven edge** as an `updates/index.html` card (insert ABOVE the auto-incidents marker) + FTP-deploy.

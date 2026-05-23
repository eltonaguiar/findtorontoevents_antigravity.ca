# Hermes Agent — Hedge-Fund-Grade Tool Architecture

> **For: findtorontoevents.ca /audit dashboard**
> **Goal: Institutional-quality prediction pipeline — self-auditing, continuously optimizing, ensemble-driven**
> **Date: 2026-05-04**

---

## Tier 1 — Strategic Insight Engine (The "Swarm-Brain")

These are the tools no quant desk operates without. They form your ensemble-modeling layer.

### delegate_task (Multi-Model Swarm)

| Capability | How We Use It | Proven Results |
|---|---|---|
| 60-model swarms | 10 rounds × 6 models across 3 persona families (Mercury/UX, Grok/Quant, Claude/Data) | 180+ recommendations, stale strategy detection, near-pick surfacing |
| Per-asset optimization | FOREX/COMMODITY/CRYPTO/EQUITY/ETF — each gets dedicated swarm rounds | Optimal TP/SL per asset class (FOREX bollinger_breakout: tp=1.0/sl=2.0, Sharpe 10.544) |
| Mini-swarm triage | 3 model families × 2 cycles = 6 agents for rapid diagnostics | Task planning, site diagnostics, approach validation in ~5-10 min |
| 3-cycle pattern | Cycle 1: Generate → Cycle 2: Peer Review/Compile → Cycle 3: Apply | COMPILED_ASSET_PLAN.json → SWARM_OPTIMIZATION_REPORT.md |

**Discovered insights:**
- Stale strategies: >55 days no pick (GPX_Gen10_2a4b0b, Revival_Mutated_* series)
- Near-pick strategies: signal at 0.45-0.49 (macd_classic_crossover, rl_ppo_agent)
- 2554 CRYPTO losing trades avg -1.71% → exit 1d sooner improves to -1.70%
- Inverse trade PnL: +34.14% for losing FOREX/COMMODITY strategies
- COMMODITY model health: 28/100 score, Sharpe -2.343 (CRITICAL)
- FOREX model health: 32/100 score, Sharpe -1.895 (CRITICAL)
- Expected PnL impact from fixes: ~$245k/month

### session_search + memory

| Feature | Purpose | Example |
|---|---|---|
| session_search | Cross-session recall without re-running expensive swarms | "What was the last TP/SL ratio for EUR/USD that gave Sharpe > 2?" |
| memory | Durable facts that survive across sessions | Repo quirks, strategy name typos (chatgpt_combiled), 92% asset_class bug |

**What lives in memory (not session_search):**
- User preferences and corrections (most valuable)
- Environment facts (OS, installed tools, project structure)
- Tool quirks (git timeout at 30s on 119K+ commits)
- Stable conventions

**What lives in session_search:**
- Task progress
- Session outcomes
- Completed-work logs
- Analysis results

### execute_code

| Use Case | Why |
|---|---|
| Process large JSON payloads (2.8MB+ dashboard_data.json, 97K+ picks) | Too big for inline terminal |
| Backfill asset_class on 97K+ picks | Programmatic batch processing |
| Aggregate swarm outputs (150K candidate signals) | Filter by confidence, write compact signal-catalog |
| Run statistical distributions across full pick corpus | Per-asset-class WR, Sharpe, PF distributions |

**JSON format trap:** universal_resolved_picks.json is a JSON **array** (`[{...}, {...}]`), NOT JSONL. Check first byte: `[` = array.

---

## Tier 2 — Live Operations Dashboard (The "Trading Floor")

Real-time observability. A hedge fund doesn't ship models without live monitoring.

### browser_navigate + browser_console

4-page parallel diagnostic sweep:

| Page | URL | What to Check |
|---|---|---|
| Audit Dashboard | `/audit` | Console errors, active picks count, data timestamp, all tabs present, tier display |
| HyroTrader | `/audit/hyrotrader` | Console errors, account snapshot values, QuanEngine freshness, position calculator |
| Homepage | `/` | Console errors (filter out event-filter noise), event count, "last updated" timestamp |
| Sports Betting | `/live-monitor/sports-betting.html` | Console errors, data loaded (not empty), sport tabs present |

**Alert triggers:**
- Stale Homepage events (97 days as of May 4)
- Stale QuanEngine on /audit/hyrotrader (16 days as of Apr 18)
- Any `type: "error"` console message
- Missing or empty data payloads
- Push anomalies to Slack/Discord webhook

**Console triage:** Log-level messages ([ValidationMetrics], [FOREX], [STOCKS], [Audit]) are healthy. Only `type: "error"` messages and `js_errors` array entries are actionable.

### web_search (Macro-Sentiment)

| Data Source | What to Pull | How It Feeds the Swarm |
|---|---|---|
| News APIs | Fed rate decisions, regulatory changes | Macro-tone vector as extra feature |
| Reddit/Twitter | Crypto sentiment, retail flow | Social sentiment score |
| Macro-data sites | China GDP, inflation, employment | Regime detection signal |

### Polymarket (Prediction-Market Ingestion)

| What to Pull | Conversion | Value |
|---|---|---|
| "Will Bitcoin break $30K this month?" | Implied probability from odds | Forward-looking crowd-sourced indicator |
| "Ethereum 2.0 launch by Q3?" | Probability bias | Often precedes price moves |
| Regulatory event odds | Binary outcome probabilities | Regime-switch signal |

---

## Tier 3 — Backtesting & Performance Analytics (The "Quant Engine")

Heavy computation layer. Runs on remote VM, returns structured performance tables.

### terminal

| Command | Purpose |
|---|---|
| `python -m audit_trail.universal_pick_resolver` | Resolve all picks with TP/SL enrichment |
| `python -m backtest.run --asset crypto --window 90d` | Per-asset backtest |
| `python -m backtest.optimize --metric sharpe` | Hyperparameter optimization |
| `python backtest_fixed_v2.py` | Entry/exit buffer analysis |

### Entry/Exit Buffer Optimization (Verified 2026-05-04)

| Asset Class | entry_buffer | exit_buffer | inverse | Expected ΔWR | Status |
|---|---|---|---|---|---|
| FOREX (46.7% WR, -1.895 Sharpe) | -2 | -3 | TRUE | +5-8% | CRITICAL |
| COMMODITY (43.5% WR, -2.343 Sharpe) | -1 | -2 | TRUE | +4-6% | CRITICAL |
| CRYPTO (46.3% WR, 0.976 Sharpe) | -2 | -1 | FALSE | +3.5% | Needs +3.7% |
| EQUITY (57.7% WR, 3.532 Sharpe) | -1 | -2 | FALSE | +4.0% | Near T1 |
| ETF (60.9% WR, 6.375 Sharpe) | -1 | -1 | FALSE | +0.5% | T2 ✅ |

### execute_code (Quant Processing)

| Use Case | Workflow |
|---|---|
| Load 2GB historical_ticks.parquet | Compute per-asset entry-buffer and exit-buffer distributions |
| Compute buffer_opt.json | Per-asset TP/SL tuning output |
| Statistical modeling | XGBoost/LightGBM for feature importance |

---

## Tier 4 — Procedural Knowledge & Automation (The "Wiki + Cron")

This is your institutional memory codified as executable playbooks.

### skill_manage

| Skill | Purpose |
|---|---|
| trading-audit-system | Asset classification flow, pick resolution, dashboard generation, buffer analysis, R:R diagnostics |
| multi-agent-swarm | Swarm orchestration patterns, model persona conventions, output format enforcement |
| signal-validation | Pull latest signal catalog → run out-of-sample test → write validation report |
| backtest-pipeline | Data-cleaning → feature-generation → model-run → metric-calc (reproducible sequence) |

**Skill lifecycle:** Create after complex tasks succeed (5+ tool calls, errors overcome). Patch immediately when stale/wrong. Skills encode: trigger conditions, numbered steps with exact commands, pitfalls, verification steps.

### cronjob

| Frequency | Task | Tier |
|---|---|---|
| Hourly | delegate_task swarm refresh | Tier 1 |
| Hourly | Unified Audit Dashboard update (115min timeout) | Tier 2 |
| Every 45min | Copy Trader Intelligence refresh | Tier 2 |
| Every 2 hours | ALPHA Verify Predictions | Tier 3 |
| Daily | browser_navigate health-check of data pipelines | Tier 2 |
| Daily | Asset Class Freshness Watchdog | Tier 2 |
| Weekly | web_search macro-sentiment refresh + skill_manage update of sentiment-weighting | Tier 2/4 |
| Weekly | ML algorithm health check swarm | Tier 3 |

### session_search (Investigative)

| Query Pattern | Purpose |
|---|---|
| "When was the last time EUR/USD signal drifted >5% in a day?" | Trigger ad-hoc alert |
| "What did we discover about commodity Sharpe ratios last time?" | Avoid recomputation |
| "Which strategies were killed in Q1?" | Audit trail for PERMANENTLY_KILLED_STRATEGIES |

---

## Tier 5 — External Signal & Data Ingestion (The "Alpha-Feed")

External alpha sources that feed into the internal prediction engine.

### web_search + browser

| Data Source | What to Extract | Value |
|---|---|---|
| Exchange order-book depth snapshots | Bid/ask wall concentrations | Liquidity regime detection |
| DeFi TVL dashboards | Protocol-level capital flows | Early warning for liquidity crunches |
| Broker macro-data feeds | Institutional positioning | Smart-money flow |

### Polymarket

| Signal | Integration |
|---|---|
| Live odds on crypto/forex events | Convert to probability bias → inject into swarm feature set |
| Crowd-sourced forward-looking indicator | Fuse with internal model scores for "combined confidence" metric |

### delegate_task (Signal Fusion)

Run a lightweight swarm that fuses:
- Internal model scores (from Tier 1)
- External signals (news sentiment from Tier 2)
- Polymarket odds (from Tier 5)
→ Produces "combined confidence" metric that reduces false positives and improves signal reliability.

---

## Integration Flow — How the Pieces Fit Together

```
┌─────────────────────────────────────────────────────────────────┐
│                        CRONJOB FIRES                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: delegate_task swarm (3-60 models)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ Mercury  │  │  Grok    │  │  Claude  │  ... × N rounds       │
│  │ (UX/API) │  │ (Quant)  │  │ (Data)   │                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
│       └──────────────┼────────────┘                              │
│                      ▼                                           │
│              signal_catalog.json                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  execute_code: aggregate, filter, store                          │
│  session_search: retrieve last macro-tone vector                 │
│  memory: inject durable facts (repo quirks, strategy names)     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: browser_navigate → live dashboard sweep                │
│  web_search → macro-sentiment vector                            │
│  polymarket → crowd-alpha injection                             │
│  Any error → Slack/Discord alert                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: terminal → backtest.run / .optimize                    │
│  execute_code → buffer_opt.json, TP/SL tuning                   │
│  Results stored in skill (backtest-pipeline)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 4: skill_manage → update institutional wiki               │
│  cronjob → schedule next refresh                                │
│  session_search → ad-hoc investigative queries                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 5: web_search + polymarket → continuous alpha-feed        │
│  delegate_task → signal fusion (internal + external)            │
│  Combined confidence metric → dashboard display                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Architecture (Current)

```
audit_trail/
├── asset_classification.py        # AssetClassifier with regex patterns
├── universal_pick_resolver.py     # Resolves TP/SL, writes resolved picks
└── dashboard_generator.py         # Generates dashboard_data.json

audit_dashboard/
├── template.html                  # Main /audit page
├── funds.html                     # /funds page (R:R gating)
└── data/
    ├── dashboard_data.json        # Generated payload
    └── trust_registry.json        # PROVEN/VALIDATING/SANDBOX tiers

battleground/
└── data/
    └── chatgpt_combined_signals.json  # Tier A strategy (75-83% WR)

swarm_runs/                        # Swarm output artifacts
prs/                               # PR proposals from swarm analysis
updates/                           # Analysis reports and architecture docs
```

---

## GitHub Actions Workflow Monitoring

**Note:** gh CLI unavailable in WSL. Use browser_navigate with filter URLs.

| Check | URL |
|---|---|
| All failures | `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions?query=is%3Afailure` |
| All cancelled | `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions?query=is%3Acancelled` |
| CI Tests failures | `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions?query=workflow%3A%22CI+Tests%22+is%3Afailure` |

Key workflows:
| Workflow | Cadence | Timeout |
|---|---|---|
| Unified Audit Dashboard | Hourly | 115min |
| Copy Trader Intelligence | 45-min cycles | 45min |
| ALPHA Verify Predictions | 2-hour cycles | 3min |
| Asset Class Freshness Watchdog | Daily | — |

---

## Key Pitfalls

1. **Git timeout:** Repo has 119,598+ commits. Git ops timeout after 30s.
2. **Asset_class missing:** 92% of picks have NO asset_class field (not just "UNKNOWN").
3. **ChatGPT typo:** Strategy is `chatgpt_combiled` (not "combined").
4. **JSON format:** universal_resolved_picks.json is array `[{...}]`, not JSONL.
5. **Workspace path:** Swarm agents default to wrong paths — always specify `/mnt/c/findtorontoevents_antigravity.ca/`.
6. **API key sanitization:** Mandatory for all swarm outputs — use `.sanitize_keys.py`.
7. **CI failures block deployment:** Fix branch `fix/asset-class-tagger-resolver-2026-05-04` (PR #782) has persistent CI failures.
8. **Large JSON files:** 2.8MB+ files require execute_code for analysis.

---

## Confidence Band Edges (Verified)

| Band | Actual WR | PF | n | Bonus/Penalty |
|---|---|---|---|---|
| [0.75, 0.80) | ~87% | — | — | +18 |
| [0.80, 0.85) | 62.5% | 5.83 | 120 | +12 |
| ≥0.90 | 22.2% | — | — | -20 (worst) |

---

## PROVEN Tier Criteria

- WR ≥ 60%
- PF > 1.5
- Trades ≥ 50
- DSR > 1.0

---

**Next Steps:**
- Which tier to prototype first? (Swarm-brain, live dashboard, or backtesting pipeline)
- Preferred data sources for external alpha integration?
- Automation schedule for cronjob-based refresh cycles?

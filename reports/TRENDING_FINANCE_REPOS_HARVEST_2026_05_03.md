# Trending GitHub Finance Repos — Harvest 2026-05-03

**Source:** user-curated list of fastest-growing finance repos this week.
**Method:** cross-check each against existing repo + prior audit `reports/hedge_fund_integration_2026_04_28.md`. Same harvest discipline as MIT Quant Bible (#737): cite what's already in repo, identify net-new only.
**Goal alignment:** improve per-asset-class PF/WR vs Goal #1 (FOREX 0.27 / CRYPTO 1.25 / EQUITY 1.41 / COMMODITY 1.78 / ETF 1.24 / BOND 1.72).

---

## TL;DR

10 trending repos triaged. **3 actionable** (last30days-skill, OpenBB, scientific-agent-skills). 1 monitor candidate (daily_stock_analysis pattern). 6 already-have or wrong-shape (TradingAgents, TradingAgents-CN, Vibe-Trading, QuantDinger, FinceptTerminal, qlib).

| # | Repo | Δ stars | Verdict | Asset class lift potential |
|---|---|---|---|---|
| 1 | TradingAgents | +7.9k | **SKIP** (have equivalent) | n/a — side-grade |
| 2 | FinceptTerminal | +4.3k | **SKIP** (wrong shape) | n/a — desktop UI |
| 3 | daily_stock_analysis | +2.3k | **MONITOR** | EQUITY (multi-channel push pattern) |
| 4 | Vibe-Trading | +1.9k | **SKIP** (have equivalent) | n/a — single-user pip-install |
| 5 | QuantDinger | +837 | **SKIP** (wrong shape) | n/a — Docker self-host |
| 6 | TradingAgents-CN | +641 | **SKIP** (Chinese fork) | n/a |
| 7 | last30days-skill | +630 | **SHIP** (drop-in) | system-wide (sentiment/news enrich) |
| 8 | qlib (Microsoft) | +569 | **DEFER** (already audited; revisit alpha module) | EQUITY (factor IC) |
| 9 | scientific-agent-skills | +511 | **EVAL** (if finance skills exist) | system-wide |
| 10 | OpenBB | +387 | **SHIP** (data unifier + MCP) | system-wide (replaces patchwork data feeds) |

---

## Per-repo evaluation

### 1. TradingAgents (+7.9k) — SKIP

UCLA/MIT multi-agent LLM trading framework: fundamental/sentiment/technical/risk-manager personas + DeepSeek V4 thinking-mode.

**Why skip:** Already covered. Per `reports/hedge_fund_integration_2026_04_28.md` Group A audit, equivalent functionality lives in `incubator/agents/ensemble_evolver.py`, `universal_evolver.py`, `orchestrator.py`. The personas are flavor not new infra. Verdict from prior audit: **PASS** (side-grade).

**One steal:** if their DeepSeek V4 thinking-mode prompting template is open, port to our `tools/consult_deepseek.py`. ~30min check.

### 2. FinceptTerminal (+4.3k) — SKIP

C++20/Qt6 Bloomberg-alternative desktop terminal. 37 AI agents (Buffett/Munger/Lynch/Graham). 16 broker integrations. Internal MCP + AI quant tabs.

**Why skip:** Wrong shape. Our system is a web `/audit` dashboard, not a desktop terminal. Broker execution isn't this stack's responsibility (we're signal-emit only, execution is via TradingView paper accounts).

**One steal:** their MCP integration pattern. We already use Claude-peers MCP + several others. Quick scan their MCP tool catalog for any signal-data MCPs we don't have. ~15min check.

### 3. daily_stock_analysis (+2.3k) — MONITOR

LLM stock analyzer for US/A-share/H-share. Auto-builds daily decision dashboard with entry/exit. Pushes to WeChat/TG/Discord/Email via GHA.

**Why monitor:** Two genuinely useful patterns:
- **Multi-channel push template** (TG/Discord/Email via GHA secrets). Our dashboard is web-only; could amplify reach. Per memory `env_news_apis.md` we have the API keys ready (Telegram already there).
- **Daily entry/exit dashboard format** that compiles per-pick decisions in one rendered HTML — could enrich `audit_dashboard/template.html` Smart Picks section.

**Asset class fit:** EQUITY primarily (US/A-share/H-share). Our EQUITY is T2-cand at PF 1.41; this won't move PF but could grow downstream user base which loops back to data quality.

**Effort if pursued:** 4-6h to port the GHA push template + adapt to our pick schema.

### 4. Vibe-Trading (+1.9k) — SKIP

Personal pip-install agent: NL → strategy → backtest → TV/MT5 export.

**Why skip:** We have all of:
- NL→strategy via `incubator/agents/genetic_programmer.py`
- Backtest via `scripts/local_backtest.py` + `alpha_engine/vectorbt_explorer.py`
- TV export via existing `tools/tv_*` modules

Side-grade. Per `tools/install_check_active_picks_shim.ps1` we already have working TV integration.

### 5. QuantDinger (+837) — SKIP

Self-hosted AI quant OS via Docker Compose. Crypto + IBKR stocks + MT5 forex.

**Why skip:** Wrong deployment model. We run on GHA + GitHub Pages, not self-hosted Docker. Migrating would be weeks of infra rewrite for unclear gain.

**One steal:** if their `compose.yaml` shows interesting service decomposition (e.g., separate ingestion/scoring/execution services), worth considering for our future modular split. But not a 30-day-impact item.

### 6. TradingAgents-CN (+641) — SKIP

Chinese fork of TradingAgents. A-share data sources + domestic LLMs.

**Why skip:** No A-share coverage in our system. Out of scope.

### 7. last30days-skill (+630) — SHIP (drop-in)

Agent skill for cross-platform research over Reddit/X/YouTube/HN/Polymarket/web in last 30 days.

**Why ship:** Drop-in Claude Code skill. Plugs into any agent framework. Our news/sentiment layer per memory `env_news_apis.md` is fragmented (NewsAPI + GNews + TheNewsAPI + Mediastack + Currents + Telegram + LunarCrush). This consolidates discovery into one skill.

**Asset class lift potential:**
- CRYPTO: better sentiment/social discovery (catch Reddit/X chatter on small caps)
- EQUITY: HN/Reddit for tech stock context
- All: Polymarket for prediction-market consensus (we already have `alpha_engine/polymarket_signals.py` — this would broaden the feed)

**Effort:** 1-2h to install skill + wire into our agent prompts as enrichment step.

### 8. qlib (Microsoft) (+569) — DEFER

End-to-end quant platform: data → alpha → portfolio → execution.

**Why defer (not skip):** Per prior audit `hedge_fund_integration_2026_04_28.md` Group B, qlib was listed but not picked because too heavy for in-repo integration. **One specific module worth revisiting:** their alpha-factor library (factor IC ranking). We have `feedback_confidence_is_not_edge.md` flag that confidence ≠ edge; qlib's empirical alpha library could provide validated factor candidates we haven't tried. Time-budget for revisit: 4h to read alpha-101 + identify 2-3 candidates absent from our scoring.

**Asset class fit:** EQUITY primarily. Could lift EQUITY PF 1.41 → toward 1.5+ if any qlib alpha factors validate on our forward window.

### 9. scientific-agent-skills (+511) — EVAL

Agent skills for research/science/engineering/analysis/finance. Includes bioinformatics + cheminformatics + Hugging Science.

**Why eval:** Unknown if it includes specifically-finance skills we don't have. Need 30min triage of their `/skills/finance/` directory if it exists. If yes → install candidates. If no → skip.

**Action:** quick `gh repo view` + `tree skills/` check next cycle.

### 10. OpenBB (+387) — SHIP (highest data ROI)

Open-source financial data platform: stocks/crypto/options/derivatives/fixed-income. MCP integration for AI agents.

**Why ship (highest ROI on this list):**
- Our data layer is patchwork. Per memory: `env_lunarcrush.md`, `env_news_apis.md`, multiple Binance fallbacks, yfinance, FRED. OpenBB unifies many of these.
- **MCP integration** = direct Claude Code agent access. No custom adapter layer.
- Coverage: stocks (we have), crypto (we have), **options/derivatives** (we don't), **fixed income** (we have FRED but limited — could complete BOND coverage).

**Asset class lift potential:**
- BOND: better fixed-income data → grow n from 18 → 50+ faster + diversify beyond yield-momentum strategy
- ETF: better cross-asset data could improve `alpha_engine/etf_*` strategies
- COMMODITY: better futures-curve data for `cftc_cot_commercial_signal` (currently top performer at 68.8% WR per old session memory)
- System-wide: replace 4-5 fragmented data fetchers with one unified pipeline

**Effort:** 2-4h initial install + MCP wire-up. Real value compounds over weeks as data unifies.

**Wire-Up Rule:** new module needs production caller. Plan: install OpenBB-MCP, wire into `audit_trail/dashboard_generator.py` data ingestion as opt-in sidecar via `OPENBB_DATA_ENABLED=1` env flag. A/B against current data sources for 14d before flipping default.

---

## Recommended ship order (Goal #1 priority)

| Priority | Repo | Effort | Lift target | Why first |
|---|---|---|---|---|
| **P1** | OpenBB | 2-4h | BOND/ETF/COMMODITY data quality | Highest data ROI; MCP-native |
| **P1** | last30days-skill | 1-2h | CRYPTO sentiment + cross-asset news | Drop-in skill, zero infrastructure |
| **P2** | scientific-agent-skills | 30min triage | TBD | Need to verify finance content first |
| **P3** | daily_stock_analysis | 4-6h | EQUITY (downstream user reach) | Multi-channel push template |
| **P3** | qlib alpha module | 4h | EQUITY factor IC | Revisit per `hedge_fund_integration_2026_04_28.md` Group B |
| **SKIP** | TradingAgents, TradingAgents-CN, Vibe-Trading, QuantDinger, FinceptTerminal | n/a | n/a | Have equivalent or wrong shape |

---

## Anti-pattern memo (don't repeat past mistakes)

- Don't claim integration "done" without a production caller. Wire-Up Rule per `CLAUDE.md` is hard-enforced.
- Don't pull in another LLM-orchestration framework (TradingAgents, FinceptTerminal personas, Vibe-Trading) — we already have `incubator/agents/*` and a peer is currently building `tools/swarm/` for Kimi-style fan-out.
- Don't migrate to Docker Compose (QuantDinger). Our GHA + GitHub Pages stack is working; migration is weeks of yak-shaving.
- Don't add A-share / H-share strategies until we have a closed-pick volume justification. Charter floor: n>=100 closed before any tier claim.

---

## Current Goal #1 baseline (for lift attribution post-integration)

| Class | PF | WR | n | Tier | Pre-integration baseline |
|---|---|---|---|---|---|
| EQUITY | 1.41 | 52.9% | 420 | T2-cand | 2026-05-03 13:09Z |
| CRYPTO | 1.25 | 44.5% | 8101 | sub-T2 | post-#740 lift |
| FOREX | 0.27 | 46.4% | 1169 | sub-floor | pending JPY accumulation |
| COMMODITY | 1.78 | 46.9% | 750 | T2 PF | top PF in book |
| ETF | 1.24 | 55.2% | 87 | T3 | n→100 needed |
| BOND | 1.72 | 55.6% | 18 | T2-thresholds | n→50 needed |

Use this snapshot for before/after comparison on any integration.

---

_Generated 2026-05-03 by Antigravity session, post user trending-repo paste. Companion to #737 (MIT Quant Bible harvest), #742 (asset class eval). Successor: extend with EVAL findings on scientific-agent-skills + OpenBB integration outcome._

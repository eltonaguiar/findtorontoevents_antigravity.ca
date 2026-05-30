# Agent Quickstart — `/audit` Surfaces, Databases, and Per-Asset-Class Strategies

**Audience:** IDE agents (Cursor, Claude Code, Hermes, Kilo, GH Copilot, etc.) and humans onboarding to this repo.
**Goal:** answer in one page — *where is X, what reads it, and which strategies under which asset class are hedge-fund-grade?*

If you need only one fact, see the **TL;DR** section. If you're tracing a specific pick or auditing a class, jump to the relevant skill in §3.

---

## 1. TL;DR

| Question | Answer |
|---|---|
| Which DBs? | `ejaguiar1_stocks` (operational, 322 tables) + `ejaguiar1_backtests` (archive, 6 tables) on `mysql.50webs.com:3306`. Other 7 DBs are sports/events/news/etc. |
| Where do creds live? | `/home/eaguiar2015/dbpasses.txt` (gitignored, **never commit/echo**). Canonical accessor: `tools/db_env.get_stocks_creds()`. |
| Where is the schema documented? | `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` (full DESCRIBE per table) + `docs/DATABASE_SPECIFICATION_2026-05-06.md` (DB catalog). |
| Where do strategies live? | `alpha_engine/*_strategies.py` registries (see §4). Per-strategy hedge-fund-tier status is in `audit_dashboard/data/pf_registry.json`. |
| How do I evaluate a class vs hedge-fund tiers? | Run `python3 tools/strategy_tier_tracker.py` — emits a per-class table of strategies with PF/WR/n and tier label. |
| What are the audit surfaces? | `/audit` (main dashboard), `/audit/ai-tournament.html` (model competition), `/audit/hyrotrader.html` (hyrotrader rollup). See §2 for what each reads. |

---

## 2. The three audit surfaces

All three live under `findtorontoevents.ca/audit/` and are deployed via `tools/deploy_audit_files.py`.

### 2.1 `/audit` — Main audit dashboard
- **Template:** `audit_dashboard/template.html` (edit this, NOT `audit_dashboard/index.html` — that one is auto-generated).
- **Live URL:** https://findtorontoevents.ca/audit/
- **What it shows:** Smart Picks, High-Conviction, Money-Ready cohorts; per-class WR/PF tiles; TRUTH LAYER reality line; incidents/enhancements panel; pick-funnel.
- **Reads from:** `audit_dashboard/data/*.json` (snapshot artifacts), notably:
  - `dashboard_data.json` — main snapshot
  - `money_ready_verdict.json` — per-class verdict (money_ready/watch/not_ready/insufficient_data)
  - `pf_registry.json` — canonical profit-factor registry (deduped, slippage-modeled)
  - `pick_summary_stats_{14d,48h}.json` — recency cohorts
- **Backed by:** `ejaguiar1_stocks` tables `at_raw_picks`, `at_consensus_picks`, `at_filter_log`, `at_signal_outcomes` (see audit-pick-flow skill).

### 2.2 `/audit/ai-tournament.html` — Model tournament
- **Template:** `audit_dashboard/ai-tournament.html` (hand-edited).
- **Live URL:** https://findtorontoevents.ca/audit/ai-tournament.html
- **What it shows:** per-model leaderboard for 23 AI models that emit picks (DeepSeek v4 Pro, Llama4 Scout, Grok3, Cursor Agent, …); two tables (CI-adjusted ALL-tab + time-window tabs).
- **Reads from:**
  - `audit_dashboard/data/ai_tournament_leaderboard.json` — authoritative CI-adjusted leaderboard
  - `audit_dashboard/data/ai_tournament_picks_latest.json` — picks snapshot
  - `audit_dashboard/data/ai_tournament_model_summary.json` — per-model PF/WR/n
  - `audit_dashboard/data/ai_tournament_model_diagnostics.json` — per-model API health (NO_KEY / API_FAIL / OK)
- **Pipeline:** `.github/workflows/ai-tournament-pipeline.yml` (NOT the protected `ai-tournament-price-tracker.yml` — that's the price-tracker that PR #40's anti-clobber guard protects).
- **Provenance check:** rebuilds from DB via `tools/ai_tournament/rebuild_latest_from_db.py` (anti-clobber-guarded).

### 2.3 `/audit/hyrotrader.html` — Hyrotrader rollup
- **Template:** `audit_dashboard/hyrotrader.html` (hand-edited).
- **Live URL:** https://findtorontoevents.ca/audit/hyrotrader.html
- **What it shows:** narrower, "hyrotrader"-curated picks (trusted sources + tighter gates).
- **Reads from:** subset of the same `audit_dashboard/data/*.json` files, filtered by source-system + tier (see `HYROTRADER_PIPELINE_FIXES.md` for the gate stack).

---

## 3. Skills that already exist (use these — don't re-derive)

| Skill | When to invoke | What it does |
|---|---|---|
| `/db-schema` | "What tables are in X DB?" / "Where is the schema?" | DB catalog + full schema doc pointer + regen command. |
| `/audit-pick-flow` | "Why is BTCUSDT not in Smart Picks?" | Traces a single pick through the 7-stage pipeline (emit → ingest → active → smart → HC → consensus → outcome). |
| `/money-maker-ready` and `/money-maker-readyv2` | "Find per-class statistical edge worth real money." | Per-asset-class hedge-fund-grade edge audit with anti-overfit gauntlet (DSR/PBO/WFE/Bonferroni). |
| `/consult-PROXY` | "Get a second opinion from 14 LLM providers via local rotating proxy." | Fans the prompt across providers; outputs `.MD`. |

If a question matches one of these, **invoke the skill instead of duplicating its work**.

---

## 4. Strategy registries per asset class

Each registry is a Python `dict` mapping strategy-name → callable `(data) -> List[picks]`. The scanner iterates these dicts at `alpha_engine/scanner.py:~2069`. **Adding to the dict is what makes a strategy emit** (per the Wire-Up Rule in CLAUDE.md).

| Asset class | Registry → file:line (canonical) | Other registries | Asset-class tag in code |
|---|---|---|---|
| **CRYPTO** | `EDGE_STRATEGIES` → `alpha_engine/crypto_edge_strategies.py:1009` | `ONCHAIN_STRATEGIES` (`onchain_strategies.py:1923`), `SENTIMENT_STRATEGIES` (`binance_sentiment.py:556`), `SPIKE_STRATEGIES` (`spike_predictor.py:463`), `CYCLIC_STRATEGIES` (`cyclic_momentum_strategy.py:793`), `CONFLUENCE_STRATEGIES` (`confluence_strategies.py:1238`), `COINTEGRATION_STRATEGIES` (`cointegration_pairs.py:494`), `PROVEN_STRATEGIES` (`proven_scanner_strategies.py:951`), `QUANT_STRATEGIES` (`quant_strategies.py:681`), `COMMUNITY_STRATEGIES` (`community_strategies.py:783`), `UNTAPPED_STRATEGIES` (`untapped_strategies.py:1302`) | `asset_class="CRYPTO"` (e.g. `crypto_strategy_harness.py:1922`) |
| **EQUITY** | `EQUITY_STRATEGIES` → `alpha_engine/equity_strategies.py:1346` | — | `asset_class == "EQUITY"` in `quality_gates.py` VIX gate, `non_crypto_policy.py` |
| **FOREX** | `FOREX_STRATEGIES` → `alpha_engine/forex_strategies.py:~1110` | `ALL_STRATEGIES` (`forex_smart_picks.py:324`) | `category=="forex"` in `non_crypto_policy.py`; FX kill-switch in `fx_kill_switch.py` |
| **COMMODITY** | `commodity_seasonal.py` (`ASSET_CLASS = "COMMODITY"` at line 45) | `multi_asset_*` sources (CFTC/COT; see `_COMMODITY_FV_EXEMPT` in `quality_gates.py`) | `ASSET_CLASS = "COMMODITY"` |
| **ETF** | `etf_strategies.py` + scanner in `etf_scanner.py` | — | `asset_class == "ETF"` |
| **BOND** | `bond_scanner.py` (`bond_duration_rotation`, `bond_ust_tsmom`, `bond_credit_spread_mean_reversion` at lines ~101-111) | wired via `non_crypto_policy.py` | — |

To enumerate live: `grep -rnE '^[A-Z_]+STRATEGIES\s*=' alpha_engine/ --include='*.py'`.

**Note:** a strategy in a registry does NOT guarantee live emission — see the Wire-Up Rule and the `NON_CRYPTO_STRATEGY_POLICY` allowlist (`alpha_engine/non_crypto_policy.py:578-585`). Strategies absent from the policy fail-close as `strategy_on_probation` (correct posture for failing classes; e.g. `forex_carry_ppp` was registered but kept probationary in PR #69).

---

## 5. Hedge-fund-tier evaluation — per-strategy per-class

### 5.1 Canonical source
`audit_dashboard/data/pf_registry.json` is the single source of truth for PF/WR (slippage-modeled, deduped, resolver-flicker-aware). Read this; do not recompute.

Useful keys:
- `by_asset_class_policy_clean_net` — per-class aggregates (PF/WR/n) after policy filter, NET of modeled costs. **This is the headline number for tier verdicts.**
- `by_asset_class_strategy_policy_clean_net` — **per-strategy** breakdown (list of `{asset_class, strategy, n, wins, losses, profit_factor, win_rate_pct, …}`). 73 rows as of generation.
- `methodology`, `slippage_model` — read these before quoting a PF.

### 5.2 Tier definitions (from CLAUDE.md MAJOR GOALS)
| Tier | PF | WR | MDD | What it means |
|---|---|---|---|---|
| **Tier 1 — Renaissance** | >2 | >55% | <10% | Real, large-money grade. Long-run target. |
| **Tier 2 — Institutional** | >1.5 | >50% | <20% | Sizing-up minimum. |
| **Tier 3 — Marginal** | >1.2 | >45% | <30% | Probation only. |
| **Sub-tier / FAIL** | ≤1.2 OR WR≤45% OR MDD≥30% OR n<30 | — | — | Do NOT size up. |

`money_ready_verdict.json` codifies this with `INSUFFICIENT_DATA` (n<50 post-dedup), `NOT_READY`, `WATCH`, `MONEY_READY`.

### 5.3 Tracker — generate a per-class table on demand
Run from repo root:
```bash
python3 tools/strategy_tier_tracker.py
```
Emits a markdown table per asset class, listing each strategy with `n / WR / PF / tier_label / note`. Writes to stdout AND to `reports/strategy_tier_tracker_<utc>.md`.

Optional flags:
- `--class CRYPTO` — restrict to one class
- `--min-n 30` — drop strategies with n below the noise threshold
- `--out <path>` — override the output path

Use this report to answer "how close are we to hedge-fund quality?" — concentration warnings (single-source / concentrated symbol) come from `pf_registry.flags` per strategy.

---

## 6. Common gotchas (read once, save hours)

- **Edit `template.html`, NOT `index.html`** — the latter is auto-generated.
- **Never run `dashboard_generator.py` locally** — it overwrites live HTML. Use `python3 -m py_compile` for syntax-only checks.
- **Never push without pulling first** — `git stash && git pull --rebase origin main && git stash pop`.
- **FTP-deploy `updates/` and `audit_dashboard/` files** after merging — git push to origin/main does NOT update the live 50webs site. Use `tools/deploy_audit_files.py`.
- **DB connection pooling** — 50webs has a per-host limit; parallel agents hammering it look like "Access denied" but it's rate-limiting. Don't retry-storm.
- **Two CI workflows touch tournament data** — `ai-tournament-pipeline.yml` (full pipeline) and the protected `ai-tournament-price-tracker.yml` (PR #40's anti-clobber guard). Do NOT remove the `Restore full dataset from DB` step from the latter.
- **Two protected frozensets in `audit_trail/quality_gates.py`** — `_COMMODITY_TRUSTED_SOURCES` and `_CONV_TRUSTED` MUST stay empty `frozenset()` (per merged PR #41). Re-populating them silently reopens the COMMODITY/conv bypass.
- **A/B router is currently ON by default in prod** as of 2026-05-29 (PR #67 flipped `ab_router.py:38`; PR #69 made gatekeeper honor it). PR #81 added observability — grep CI logs for `[gatekeeper.ab_obs]` to see arm distribution before deciding on revert.

---

## 7. Where to update this doc

- Add new strategy registries to §4 when they land.
- Update §5.2 tier definitions only if CLAUDE.md "MAJOR GOALS" tier table changes.
- §6 should accumulate any gotcha that bit you so the next agent doesn't repeat it.

When you ship a fix that materially changes pick provenance, dashboard wiring, or the gate stack, update this file in the same PR.

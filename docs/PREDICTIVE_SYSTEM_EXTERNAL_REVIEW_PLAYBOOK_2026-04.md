# Predictive system — external / systematic review playbook

**Date:** 2026-04-06  
**Purpose:** Map a structured quant-style review (data → dashboard → scores → outcomes → universe → paper/TV) to **this repository** and the **live audit dashboard**, so reviewers (human or agent) know **where to read code**, **what already exists**, and **what requires credentials or extracts**.

**Related analysis (score vs realized PnL):** `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md`  
**Reproducible IC script:** `tools/analyze_audit_scores_vs_pnl.py` → `tools/data/score_pnl_analysis.json`  
**DB vs JSON + Redis envelope pattern (anti–fake-pick):** `docs/PREDICTION_DB_SCORING_ANALYSIS_GUIDE_2026-04.md`

---

## Step 1 — Access and understand data and system

### 1.1 Code repository (GitHub: `findtorontoevents_antigravity.ca`)

| Topic | Primary locations |
|--------|-------------------|
| **Dashboard payload build** | `audit_trail/dashboard_generator.py` — merges feeds, normalizes scores, builds `picks.active`, `picks.recent_closed`, `verified_alpha`, optional `smart_picks` |
| **Gates & Smart score (0–100)** | `audit_trail/quality_gates.py` — `passes_active_gate`, `passes_smart_gate`, `calculate_smart_score`, DSR / anti-overfit hooks |
| **Elite / composite scoring** | `alpha_engine/elite_scorer.py` (and related); pick JSON often includes `elite_score`, `elite_breakdown` |
| **TP/SL fill / forward validation** | `alpha_engine/forward_validator.py`, `alpha_engine/production_scanner.py`, `alpha_engine/scanner.py` (cost-adjusted TP, slippage at signal) |
| **Smart picks JSON feeds** | `alpha_engine/data/smart_picks.json`, `smart_picks_history.json` (loaded in dashboard generator) |
| **Sports / MySQL live-monitor** | `live-monitor/api/*.php` + SQL under `live-monitor/sql/` — **separate** from main audit crypto JSON pipeline |

**Without cloning the repo:** reviewers only see the **deployed** site and JSON; **scoring logic is not visible in the browser** except where `template.html` mirrors a subset (e.g. `computePickScore` for tracked symbols).

### 1.2 Database (`mysql.50webs.com` / host per your hosting)

- **Audit crypto picks** in production are primarily **JSON-driven** (`audit_dashboard/data/dashboard_data.json` after generator run), not necessarily a single “picks table” exposed to this repo.
- **Sports betting DB** (e.g. `ejaguiar1_sportsbet`) powers **live-monitor** value-bet flows; schema review of sample dumps: see internal notes on `lm_sports_bets`, `lm_arena_*`, etc.
- **To review “Active / Smart / Verified Alpha” from SQL:** you need **read-only** credentials and confirmation which **database + tables** map to those concepts (often **none** — those three are **computed in PHP/Python** and embedded in JSON).

**Recommendation for external reviewers:** provide **weekly exports**: `dashboard_data.json` (or trimmed), plus any **MySQL** tables they actually use for settlement.

### 1.3 Dashboard — `https://findtorontoevents.ca/audit/`

| Flow | Mechanism |
|------|-----------|
| **Data load** | `audit/index.html` (or `audit_dashboard/index.html`) embeds or fetches `dashboard_data.json` / `DASHBOARD_DATA` |
| **Categorization** | Client-side filters + server-built fields: `asset_class`, `source_system`, `strategy`, `trust_tier`, `quality` tiers from gates |
| **Scoring display** | Columns: `score`, `smart_score`, `ml_composite_score`, `elite_score`, `confidence`; Smart table sorts by `smart_score` when configured |
| **Verified Alpha** | Block `verified_alpha` in JSON: `active_pick_refs`, `realized`, `audited`, `status_note` — built in `dashboard_generator.py` |

### 1.4 Prediction inputs & outputs

| Stage | Where |
|-------|--------|
| **Signal generation** | Many strategies under `alpha_engine/`, `quan_engine/`, `multi_asset/`, workflows in `.github/workflows/` |
| **TP/SL** | Per-strategy and scanner logic; `tp_sl_filler.py`, Kimi/riseoftheclaw scanners for some paths |
| **Stored shape** | Pick dicts: `entry_price`, `take_profit`, `stop_loss`, `direction`, `pnl_pct` when closed |

---

## Step 2 — Quantitative evaluation

### 2.1 Backtest vs live / closed outcomes

- **Ground truth for audit:** `picks.recent_closed` in `dashboard_data.json` — each row should have `pnl_pct`, timestamps, `strategy`, `asset_class`.
- **Cross-reference:** join on `id` or `(symbol, strategy, direction, closed_at)` depending on stability of IDs.

### 2.2 Correlation & subgroup analysis

**Already implemented in-repo:**

```bash
python tools/analyze_audit_scores_vs_pnl.py
```

Outputs Spearman/Pearson vs `pnl_pct`, quintile lifts, SMART vs ACTIVE counterfactual (gates), slices: all / crypto / non-crypto, optional verified-alpha overlap.

**Findings snapshot (see linked MD):** pool-wide score–PnL IC is **modest**; **crypto weaker than non-crypto**; **SMART tier** and **verified-alpha overlap** show **much stronger** rank–outcome alignment than the full pool.

### 2.3 Statistical testing (extensions)

| Test | Status |
|------|--------|
| Correlation / quintiles | **Script above** |
| Lo-style Sharpe significance (pooled) | `tools/lo_sharpe_significance_stub.py` |
| FDR on strategy win rates | `tools/fdr_control.py` |
| Diebold–Mariano vs benchmark | **Not shipped** — recommended if comparing two score systems |

### 2.4 Filters & patterns

- Use `score_pnl_analysis.json` **per-`source_system`** blocks (large-`n` sources only).
- **Regime:** `tools/regime_performance_btc_stub.py` (BTC-labeled regimes × `pnl_pct`).
- **Factor rankings:** `docs/FACTOR_RANKINGS_*_2026-04-05.*` if present in tree.

---

## Step 3 — Coverage & market universe

| Question | How to answer in this project |
|----------|-------------------------------|
| Breadth of symbols | `dashboard_data.json` → count distinct `symbol` in `active` + `recent_closed`; compare to exchange “top gainers” lists externally |
| Gaps vs “hot” names | Diff **active universe** vs **Binance 24h movers** (script or notebook — not a single canonical file) |
| Feature gaps | `HEDGE_FUND_ENHANCEMENT_PLAN.md` §7 (on-chain, funding, OI, NLP) vs what `elite_breakdown` actually fills |

**Known product note:** `picks.smart_picks` array is sometimes **empty** in JSON while Smart **tier** logic still applies via scores — check generator + `smart_picks.json` freshness.

---

## Step 4 — TradingView portfolios & paper trades

| Artifact | Location |
|----------|----------|
| TV paper / placement issues | `docs/TV_PAPER_TRADING_LOG_2026-04-05.md`, `docs/TV_PLACEMENT_NO_TPSL_BUG_20260405.md`, `docs/TV_LOSER_FORENSICS.md` |
| TV strategy design notes | `docs/plans/2026-03-05-tv-discovery-strategies-design.md` |
| Repo tools | `tools/tv_paper_tpsl_audit.py`, `tools/summarize_tv_results.py` (if configured) |

**Themes:** consistency of TP/SL on broker bridge, overfitting vs structural strategies, need for **unified** paper PnL schema (aligned with `forward_validator` closed picks).

---

## Answers to “please share snippets / DB access”

| Request | Response |
|---------|----------|
| **Prediction & scoring code** | Point reviewers to `quality_gates.py` (`calculate_smart_score`), `dashboard_generator.py` (`_extract_normalized_source_scores`), `elite_scorer.py`, and `audit_dashboard/template.html` (`computePickScore`) |
| **Sample data** | Redacted **`dashboard_data.json`** (strip user fields) or run **`analyze_audit_scores_vs_pnl.py`** and share **`score_pnl_analysis.json`** only |
| **Database** | **Read-only** user + schema diagram; clarify whether audit picks are **in MySQL or JSON-only** on your host |
| **Priorities** | **Default:** (1) crypto vs non-crypto split, (2) SMART + verified-alpha cohorts, (3) TP/SL hit rates by strategy, (4) TV paper reconciliation |

---

## Suggested reviewer checklist (short)

1. Clone repo; read `SCORE_PNL_EDGE_REVIEW_2026-04.md`.  
2. Run `python tools/analyze_audit_scores_vs_pnl.py` on a fresh `dashboard_data.json`.  
3. Trace one `source_system` from workflow → pick JSON → gate → dashboard column.  
4. Compare closed-pick `pnl_pct` distribution for **top vs bottom** `smart_score` quintile.  
5. Read `EDGE_ADDENDUM.md` / `HEDGE_FUND_ENHANCEMENT_PLAN.md` for known structural risks (backtest–forward gap, SL-hit rate).  
6. For TV: read `docs/TV_*.md` and list failing patterns (missing TP/SL, sizing).

---

## Redis bus

After publishing this file, broadcast:

1. **Summary line:** playbook path + “Step 1–4 mapped to repo; quant script exists; DB may be JSON-primary.”  
2. **Detail line:** full path `docs/PREDICTIVE_SYSTEM_EXTERNAL_REVIEW_PLAYBOOK_2026-04.md` + companion `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md`.

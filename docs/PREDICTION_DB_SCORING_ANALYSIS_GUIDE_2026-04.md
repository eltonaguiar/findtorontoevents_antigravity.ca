# Prediction database, scoring, and review — evidence-based guide

**Date:** 2026-04-02  
**Audience:** External reviewers, internal agents, and anyone drafting Redis bus updates.

---

## Why this document exists

A **simulated** review (“typical tables,” invented `BTCUSD` Redis payloads, 2023 timestamps) is **not** a substitute for reading this repository. This guide:

1. Maps **your** three-step plan (SQL / edges / MD + Redis) to **real** code and artifacts.
2. States what **requires** an actual SQL dump or redacted JSON on disk.
3. Defines **Redis bus messages** as **coordination envelopes** (topic, summary, doc pointers)—**not** as per-symbol prediction feeds with made-up prices.

**Canonical playbook (Steps 1–4, dashboard → quant → universe → TV):**  
`docs/PREDICTIVE_SYSTEM_EXTERNAL_REVIEW_PLAYBOOK_2026-04.md`

**Score vs realized PnL (already analyzed in-repo):**  
`audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md`  
Repro: `python tools/analyze_audit_scores_vs_pnl.py` → `tools/data/score_pnl_analysis.json`

---

## Step 1 — SQL extract and database structure

### What you can do without the SQL file

- **Audit “Active / Smart / Verified Alpha”** is **primarily JSON-backed** after the dashboard generator runs (`audit_dashboard/data/dashboard_data.json`). Those three surfaces are **computed** in Python/PHP logic; they are **not** guaranteed to map 1:1 to a single MySQL table. See the playbook §1.2.
- **Sports / betting** paths use MySQL under `live-monitor/sql/` and `live-monitor/api/*.php`—a **different** pipeline from the main crypto audit JSON.

### What you must have to “analyze the SQL extract”

1. The **file** in-repo or in a secure share (e.g. `docs/samples/<name>.sql` or documented path). A filename alone is insufficient.
2. A **table inventory** (from `SHOW TABLES` + `DESCRIBE` per table) pasted into the review or attached as markdown.
3. Explicit mapping: **which tables** back **which** product concepts (memecoin DB vs sports DB vs something else).

### Optimization questions that *are* answerable once the schema is known

| Question | How to answer |
|----------|----------------|
| Do scores correlate with outcomes? | Prefer **`analyze_audit_scores_vs_pnl.py`** on `dashboard_data.json`; SQL only if outcomes live in DB. |
| TP/SL vs volatility | Trace `alpha_engine/forward_validator.py`, scanners, and `tp_sl_filler.py`; compare to ATR/regime notes in `HEDGE_FUND_ENHANCEMENT_PLAN.md`. |
| Coverage (symbols, asset classes, cadence) | Distinct counts from JSON picks + workflow schedules in `.github/workflows/`. |

---

## Step 2 — Edges and optimization (repo-grounded)

**Documented structural risks and priorities** (read before proposing new features):

- `HEDGE_FUND_ENHANCEMENT_PLAN.md`
- `EDGE_ADDENDUM.md` (if present in tree)

**Strengths (evidence-oriented, not generic praise):**

- Closed picks carry **`pnl_pct`** in dashboard JSON; quant script already computes IC / quintiles / SMART gate counterfactuals.
- Gates and smart score live in **`audit_trail/quality_gates.py`**; elite/composite in **`alpha_engine/elite_scorer.py`**; dashboard merge in **`audit_trail/dashboard_generator.py`**.

**High-leverage gaps (already flagged in project docs, not invented here):**

- Backtest–forward alignment, SL-hit rates, and strategy survival under walk-forward (see edge addendum / hedge plan).
- Universe vs “top movers” diff is a **product/analytics** task: compare active universe to exchange mover APIs; no single canonical script is mandated—see playbook §3.

---

## Step 3 — MD deliverables and Redis bus messages

### MD files to use or extend

| Role | Path |
|------|------|
| External review map | `docs/PREDICTIVE_SYSTEM_EXTERNAL_REVIEW_PLAYBOOK_2026-04.md` |
| Score–PnL memo | `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md` |
| **This guide** | `docs/PREDICTION_DB_SCORING_ANALYSIS_GUIDE_2026-04.md` |

After any broadcast, append a row to **`docs/REDIS_BUS_CHANGELOG.md`** (newest first).

### Redis: do **not** publish fake picks

Per project rules, **do not** put invented symbols, TP/SL prices, or fabricated returns on the bus as if they were live data.

Use the same **envelope pattern** as `tools/bus_post_edge_addendum.py`:

- **Channel:** `alpha_engine_bus`
- **Body:** JSON with `bus_topic`, `from`, `ts`, `summary`, optional `doc_path_repo_relative`, `related_docs`, `key_findings` (metrics **from real runs** only), `action_required`

### Two-message set (summary + pointer to this MD)

**Message A — short summary (one line or mini JSON):**

```json
{
  "bus_topic": "PREDICTION_DB_SCORING_REVIEW_SUMMARY",
  "from": "cursor-composer",
  "ts": "2026-04-02T00:00:00Z",
  "summary": "DB/scoring review guide: use playbook + score_pnl script; audit picks JSON-primary; SQL needs real extract + table map; Redis = envelope only no fake trades.",
  "doc_path_repo_relative": "docs/PREDICTION_DB_SCORING_ANALYSIS_GUIDE_2026-04.md"
}
```

**Message B — extended pointer (references the MD set):**

```json
{
  "bus_topic": "PREDICTION_DB_SCORING_REVIEW_DOCS",
  "from": "cursor-composer",
  "ts": "2026-04-02T00:00:00Z",
  "summary": "Grounded analysis docs for predictions/DB/scoring; supersedes simulated-SQL templates.",
  "doc_path_repo_relative": "docs/PREDICTION_DB_SCORING_ANALYSIS_GUIDE_2026-04.md",
  "related_docs": [
    "docs/PREDICTIVE_SYSTEM_EXTERNAL_REVIEW_PLAYBOOK_2026-04.md",
    "audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md",
    "HEDGE_FUND_ENHANCEMENT_PLAN.md"
  ],
  "artifacts_to_generate": [
    "tools/data/score_pnl_analysis.json (from analyze_audit_scores_vs_pnl.py)"
  ],
  "action_required": "Place SQL extract + schema notes in repo or secure share; run IC script on fresh dashboard_data.json; append REDIS_BUS_CHANGELOG after PUBLISH."
}
```

Replace `from`, `ts`, and `summary` with your agent id and UTC time when publishing.

**Publish (example):**

```bash
# After redis-cli path/port per AGENT_BUS.md
redis-cli -p 6379 PUBLISH alpha_engine_bus '<single-line JSON envelope>'
```

Or adapt `tools/bus_post_edge_addendum.py` to load these fields from a small JSON file.

---

## Direct answers to “next actions” from a simulated review

| Ask | Answer |
|-----|--------|
| Share DB sample | Provide **redacted** `dashboard_data.json` and/or **schema + sample rows** from real tables; avoid synthetic pick rows in production paths. |
| Generate Redis from simulated data | **No** for pick-level payloads. **Yes** for **envelope** messages above + `REDIS_BUS_CHANGELOG.md`. |
| Prioritize asset class | Default: **crypto vs non-crypto**, then **SMART + verified-alpha** cohorts (playbook §2.2). |

---

## Revision

When SQL is reviewed for a specific database, add a subsection here with **date**, **dump path**, **table list**, and **mapping to dashboard fields**—that becomes the single source of truth for DB-backed claims.

**Completed extract (deep dive):** `docs/EJAGUIAR1_STOCKS_SQL_EXTRACT_2026-04-06.md` — `ejaguiar1_stocks_apr62026_extract.sql` (~4 GB, 37 tables, `bt_backtest_trades` dominates size).

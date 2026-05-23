# Audit picks data feed and edge review (2026-04-15)

This document implements the methodology from the audit picks review plan: data lineage, performance by asset class, information coefficient (IC) by class, and filter calibration on **validated** closed trades. Machine-readable outputs: [`tools/data/audit_edge_review_report.json`](../tools/data/audit_edge_review_report.json), [`tools/data/score_pnl_analysis.json`](../tools/data/score_pnl_analysis.json).

## 1. Data lineage and snapshot

| Field | Value |
|--------|--------|
| Source URL | `https://findtorontoevents.ca/audit/data/dashboard_data.json` |
| Payload `generated_at` | `2026-04-15T13:25:58.947870+00:00` |
| Analysis run (UTC) | `2026-04-15T13:31:48+00:00` |
| Repo SHA in payload | `a1edad86fbe3f970c19d35dba14523fe342b43c1` |

The `/audit` page prefers same-origin JSON over embedded HTML (`loadExternalDashboardDataIfFresher` in [`audit_dashboard/template.html`](../audit_dashboard/template.html)). In the browser, the **SITE JSON** badge indicates live data; **EMBEDDED** means the inline payload was at least as fresh.

**Regenerate the snapshot** (large file; listed in `.gitignore`):

```bash
curl -sS -o tools/data/audit_edge_review_live.json "https://findtorontoevents.ca/audit/data/dashboard_data.json"
python tools/audit_edge_review.py --dashboard tools/data/audit_edge_review_live.json
python tools/analyze_audit_scores_vs_pnl.py --dashboard tools/data/audit_edge_review_live.json --out tools/data/score_pnl_analysis.json
```

## 2. Two different “Smart Picks” concepts

| Mechanism | Source | Role |
|-----------|--------|------|
| **Smart Picks tab / SMART PICKS button** | `smart_picks_feed` ← [`alpha_engine/data/smart_picks.json`](../alpha_engine/data/smart_picks.json) merged with active rows | Curated engine output (`getEmbeddedSmartPicksFeed`, `applySmartPicks`). |
| **Quality-gate tier** | `picks.smart_picks` in JSON (top 50 `passes_smart_gate` + `calculate_smart_score`) | [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) post-scoring pass. |

These lists **differ**. This snapshot: **3** rows in `smart_picks_feed.picks`, **5** rows in `picks.smart_picks`. Any “Smart Picks” win rate must state **which** definition was used.

## 3. Verified Alpha: Python vs browser

Server summaries and `research_cohort` tagging use [`_is_verified_alpha_pick`](../audit_trail/dashboard_generator.py) (rolling freshness on stale `history_wr`, realized-alpha source whitelist, etc.). The dashboard’s [`isVerifiedAlphaPick`](../audit_dashboard/template.html) **does not** mirror every Python branch. For **realized performance**, use Python’s definition (as in this review), not the client filter alone.

## 4. Performance by asset class (payload block)

`performance.by_asset_class` aggregates **full** resolved history in the generator (not only the last 3500 `recent_closed` rows). Snapshot excerpt:

| Class | Closed (hist.) | Win rate % | Profit factor | Expectancy % |
|-------|------------------|------------|---------------|--------------|
| CRYPTO | 17427 | 44.7 | 0.43 | -1.95 |
| EQUITY | 721 | 39.5 | 0.77 | -0.53 |
| FOREX | 1024 | 44.2 | 0.36 | -0.93 |
| COMMODITY | 371 | 42.4 | 1.08 | 0.02 |
| ETF | 20 | 42.1 | 0.24 | -0.95 |
| FUTURES | 19 | 5.3 | 0.06 | -0.08 |
| BOND | 8 | 57.1 | 25.9 | 0.71 |
| SPORTS | 0 | — | — | — |

Headline pool in `summary`: overall win rate **41.4%**, compounded equal-weight total PnL **-100%** (with raw sum and other stats in JSON). The full-history picture is **below 50%** in several liquid classes—consistent with “worse than a coin flip” at the **unfiltered** book level.

## 5. Validated `recent_closed` sample (n = 3500)

All 3500 `recent_closed` rows passed `_is_valid_resolved_pick` (metric-safe realized outcomes).

**Baseline (validated closed):**

- Win rate **42.74%** (Wilson 95% **41.1–44.4%**)
- Mean PnL **-0.046%**, median **-0.004%**

**Counterfactual filters (same 3500 rows; smart gate uses `status: OPEN` on copy):**

| Filter | n | Win rate % | Wilson 95% WR | Mean PnL % |
|--------|---|------------|---------------|------------|
| `passes_smart_gate` (OPEN) | 263 | 60.46 | 54.4–66.2 | +0.59 |
| `passesHighConvictionPick` (Node [`hc_batch_eval.js`](../tools/hc_batch_eval.js)) | 291 | 65.98 | 60.4–71.2 | +0.97 |
| Python `_is_verified_alpha_pick` | 2122 | 45.99 | 43.9–48.1 | +0.10 |
| Overlap with **current** `smart_picks_feed` keys (exact or loose) | 3 | 66.67 | **wide** (n tiny) | +0.82 |

**Interpretation:**

- **Smart gate** and **High Conviction** both lift win rate and mean PnL vs baseline on this slice—they behave like **ranking/selection** tools, not guarantees.
- **Verified Alpha** (Python) is a **broad** cohort (~60% of rows here); realized WR stays near **46%**, i.e. **not** a pure “edge filter” by itself—consistent with the cohort mixing many sources; use audited/PM subsets for marketing claims.
- **Smart feed overlap** on **closed** history is almost useless for statistics (**n = 3**): the feed is a **current** engine snapshot, not a historical label.

**Per-class smart gate (validated slice):** Crypto smart gate **~61%** WR (n=213); Equity smart gate **~89%** WR but **n=9** (CI dominates). Forex smart gate **~51%** WR (n=41). Commodity/ETF/Futures smart gate **n=0** on this counterfactual—**supply + gates** (e.g. crypto long-only, score floors), not only “harder asset class.”

## 6. Information coefficient by asset class (validated closed)

Spearman correlation **score / smart_score vs `pnl_pct`** (min n=30):

| Class | n | Spearman(score) | Spearman(smart_score) |
|-------|---|-------------------|-------------------------|
| EQUITY | 704 | **0.29** | **0.32** |
| FOREX | 742 | 0.02 | **0.11** |
| CRYPTO | 1641 | 0.05 | 0.01 |
| COMMODITY | 369 | -0.03 | ~0 |

Non-crypto (especially **EQUITY**) shows **meaningful** score alignment with outcomes; **CRYPTO** is noisy at the pool level (confidence slightly **negative** Spearman vs pnl in this slice).

Pool-wide IC from [`tools/data/score_pnl_analysis.json`](../tools/data/score_pnl_analysis.json): best |Spearman| entries include **smart_score** on **recent_closed_non_crypto** (~0.22).

## 7. Sparse asset classes: breadth and pipeline

From the same payload (`symbol_strategy_breadth` in the report):

- **CRYPTO** (active): 27 symbols, 20 (source_system, strategy) keys — largest footprint.
- **FOREX / EQUITY**: 7 symbols active each; strategies 2–5 active keys — **limited scanners** vs crypto.
- **COMMODITY**: 2 symbols, 1 strategy key active.
- **ETF / FUTURES / BOND**: **0** active symbols in this snapshot; closed history still has small **n** (ETF 12 symbols closed, FUTURES 5, BOND 1).

**Pipeline:** The main dashboard artifact is built in [`.github/workflows/audit-dashboard.yml`](../.github/workflows/audit-dashboard.yml) (`python -m audit_trail.dashboard_generator`), with upstream merges (`universal_pick_resolver`, stock prices, etc.) and FTP deploy of `/audit/data/dashboard_data.json`. Non-crypto coverage depends on which systems feed `active_picks` and resolver output—not all asset classes get equal scan frequency.

**Why Smart Picks count can be low:** UI copy in the template ties low counts to **penalty stacking** and `SMART_PICKS_MIN_SCORE`—scores cluster 0–40 after penalties; only a few rows clear the backend bar.

## 8. Limitations

- **Selection effects:** Counterfactual gates are applied with **today’s** code to **historical** rows; regimes and feed definitions drift.
- **Universe mismatch:** `performance.by_asset_class` uses full history; `recent_closed` is **3500** rows—IC and filter tables refer to the latter unless noted.
- **Correlation ≠ causality:** IC and filter lifts are observational.
- **VA JS/Python mismatch** (section 3) affects **only** the in-browser Verified Alpha button vs server stats.

## 9. Artifacts and tools

| Artifact | Purpose |
|----------|---------|
| [`tools/audit_edge_review.py`](../tools/audit_edge_review.py) | Reproducible report JSON (filters, breadth, IC by class). |
| [`tools/hc_batch_eval.js`](../tools/hc_batch_eval.js) | Batch `passesHighConvictionPick` for closed picks. |
| [`tools/analyze_audit_scores_vs_pnl.py`](../tools/analyze_audit_scores_vs_pnl.py) | Quintiles, trust tiers, crypto/non-crypto IC. |
| [`audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md`](../audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md) | Earlier fixed-date quant note; compare for drift. |

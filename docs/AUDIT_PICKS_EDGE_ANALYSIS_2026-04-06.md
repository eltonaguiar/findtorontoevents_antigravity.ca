# Audit picks edge analysis (active book + closed history)

**Purpose:** Answer whether **active** picks on `findtorontoevents.ca/audit` look sound by **asset class**, whether **higher scores** align with outcomes, what **unrealized PnL** looks like, how **strategies** on the active book have performed when closed, and how **closed** picks break down by asset class. This doc is **JSON-first** (same source as the live page: `/audit/data/dashboard_data.json`).

**Peer verdict (cross-asset review):** This report is **instrumentation / observability** — a necessary bridge — **not** the hedge-fund-grade **fix**. Real blockers called out in [AUDIT_PLAN_CROSS_ASSET_REVIEW_2026-04-06.md](AUDIT_PLAN_CROSS_ASSET_REVIEW_2026-04-06.md) (Redis: `audit_plan_cross_asset_review`): **(1)** dashboard truth-layer integrity, **(2)** asset-class-specific ranking and routing, **(3)** toxic strategy lanes still on the book, **(4)** promotion logic vs overfit. After this doc ships, execution discipline matters more than another chart.

**Snapshot (reproducible, live-aligned):**

| Field | Value |
|--------|--------|
| Dashboard `generated_at` | `2026-04-06T20:11:17.569948+00:00` |
| Analysis run | `2026-04-06T22:59:17Z` |
| Input path | `tools/data/snapshots/dashboard_data_2026-04-06T225846Z.json` (downloaded from live `/audit/data/dashboard_data.json`) |
| Machine JSON | `tools/data/audit_active_book_analysis.json` |

**Re-run (plan: snapshot → analyzers → bus):**

```bash
python tools/fetch_audit_dashboard_snapshot.py
# Then pass the printed path as --dashboard for each analyzer, or use local file:
python tools/analyze_audit_active_book.py --dashboard audit_dashboard/data/dashboard_data.json
python tools/analyze_audit_scores_vs_pnl.py --dashboard audit_dashboard/data/dashboard_data.json
python tools/analyze_asset_class_edge_flaws.py --dashboard audit_dashboard/data/dashboard_data.json
python tools/bus_post_audit_picks_edge.py
```

Live snapshot files under `tools/data/snapshots/` are **gitignored** (~20MB); only `.gitkeep` is tracked.

---

## 1. Infrastructure (no simulated SQL)

- **Live audit** loads **`data/dashboard_data.json`** (see `audit_dashboard/template.html`).
- **Pipeline** for active vs raw vs smart vs Verified Alpha: [TRACE_LOG.MD](../TRACE_LOG.MD).
- **MySQL / SQL extracts** are a separate lane; for schema and trust rules see [EJAGUIAR1_STOCKS_SQL_EXTRACT_2026-04-06.md](EJAGUIAR1_STOCKS_SQL_EXTRACT_2026-04-06.md) — do not mix hypothetical columns into this audit JSON analysis.

### 1.1 Snapshot step (plan requirement)

Use [tools/fetch_audit_dashboard_snapshot.py](../tools/fetch_audit_dashboard_snapshot.py) to pull the same JSON the browser loads from `https://findtorontoevents.ca/audit/data/dashboard_data.json`, then point all analyzers at that path so tables match production.

---

## 2. Active book summary

| Metric | Value |
|--------|--------|
| `picks.active` count | **110** |
| `picks.active_raw` count | **180** |
| `picks.smart_picks` count | **0** (none passed `passes_smart_gate` at this snapshot) |
| Verified Alpha `active_count` (payload) | **47** |
| VA `realized` (closed VA cohort) | **2520** trades, **47.9%** WR, **+204.97** cum `pnl_pct`, expectancy **0.08** |

### 2.1 Aggregate unrealized PnL (active)

Unrealized % is taken from `pnl_pct` / `unrealized_pnl_pct` after generator enrichment; rows with `_suspicious_entry` or `pnl_flagged` are excluded from aggregates.

| Metric | Value |
|--------|--------|
| Actives with a numeric unrealized value | **110** |
| Sum of unrealized `pnl_pct` | **+92.13** |
| Mean unrealized `pnl_pct` | **+0.84%** |

This is a **mark-to-market snapshot**, not expected value. It can flip quickly and is **not** the same statistic as closed-book expectancy.

### 2.2 Active picks by asset class

| Asset class | Active n | VA-tagged n | Score mean / max | Unrealized mean % | Unrealized sum % |
|-------------|----------|-------------|------------------|-------------------|------------------|
| CRYPTO | 58 | 44 (75.9%) | 34.2 / 86 | +0.51 | +29.29 |
| EQUITY | 47 | 1 (2.1%) | 25.3 / 30 | +1.34 | +62.89 |
| FOREX | 4 | 2 (50%) | 15.8 / 21 | -0.01 | -0.05 |
| SPORTS | 1 | 0 | 41 / 41 | 0.00 | 0.00 |

**Read:** Crypto dominates **VA** tags; equity contributes many actives but almost none are VA-tagged in this snapshot. **Equity** shows the **largest positive unrealized sum** here despite poor **closed-book** history (below) — concentration in a few names or stale marks warrants monitoring.

### 2.3 Do higher scores predict unrealized PnL on the open book?

On **n = 110** actives with both `score` and unrealized PnL:

| Correlation | Value |
|-------------|--------|
| Pearson(score, unrealized pnl%) | **+0.105** |
| Spearman(score, unrealized pnl%) | **-0.022** |

**Interpretation:** On the **open** book, score is **essentially uncorrelated** with current unrealized PnL. That does **not** mean scoring is useless — the **predictive** evidence is in **closed** trades (next section).

---

## 3. Closed book: do higher scores predict realized PnL?

From `tools/analyze_audit_scores_vs_pnl.py` on **`recent_closed` (n = 3500)**:

- **All closed:** Spearman **score vs pnl ≈ 0.24**; **smart_score vs pnl ≈ 0.23**.
- **Top vs bottom score quartile win rate:** **63.6%** vs **32.1%** (spread **31.5 pp**).
- **Strongest rank IC (this run):** **elite_score** on **non-crypto** closed ≈ **0.34**; **smart_score** on **crypto** closed ≈ **0.26**.

**Conclusion:** **Higher scores are associated with better realized outcomes on closed picks**, especially when sliced by asset class and metric. Live open PnL is too noisy and path-dependent to use as the primary calibration target.

Full quintiles and slices: `tools/data/score_pnl_analysis.json`.

---

## 4. Closed picks by asset class (same snapshot)

| Asset class | n closed | Win rate % | Mean pnl % | Median pnl % |
|-------------|----------|------------|------------|--------------|
| CRYPTO | 2855 | 48.51 | +0.2208 | -0.1126 |
| EQUITY | 471 | 35.46 | -0.7788 | -1.957 |
| FOREX | 147 | 31.29 | -0.2787 | -0.3788 |
| COMMODITY | 12 | 8.33 | -0.6966 | -0.6512 |
| ETF | 12 | 41.67 | -0.9511 | -0.322 |
| FUTURES | 3 | 0.0 | -0.4489 | -0.3754 |

**Edge (data-driven):** At scale, **only CRYPTO** shows **positive mean** realized pnl in this history. Non-crypto buckets need **tighter gates**, sizing, or strategy selection — consistent with [ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md](ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md) and `tools/data/asset_class_edge_flaws_analysis.json`.

---

## 5. Strategies on the active book vs their closed history

Joined on **exact `strategy` string** between `picks.active` and `picks.recent_closed`.

**Strategies with closed history and notable stats (this snapshot):**

`n_closed_30d` / `n_closed_90d` count closes whose `closed_at` (else `timestamp`) parses as ISO; see `recency_note` in `audit_active_book_analysis.json`.

| Strategy | n closed | 30d | 90d | WR % | Mean pnl % |
|----------|----------|-----|-----|------|------------|
| quan_engine | 1003 | 1003 | 1003 | 40.58 | +0.053 |
| enhanced_ml_A_xgboost | 123 | 123 | 123 | 29.27 | -0.5366 |
| keltner_compression_expansion_sol_v1 | 8 | 8 | 8 | 12.50 | -0.6152 |
| ml_enhanced_FETUSDT_1d_B_lightgbm | 3 | 3 | 3 | 66.67 | +1.7248 |
| drawdown_recovery_rsi_eth | 2 | 2 | 2 | 50.0 | +0.75 |
| ml_enhanced_APEUSDT_1d_D_ensemble_stack | 2 | 2 | 2 | 50.0 | +2.3348 |

**Strategies on active with zero matching closed rows (22):** includes many **goldmine_*_consensus**, **prediction_market_***, **super signal (...)** labels, **tsmom_volscaled**, **value_bet**, etc. — **no** `recent_closed` rows share that exact strategy string, so **historical WR cannot be read from this JSON** for those names (either new labels, display aliases, or closed picks stored under different strategy keys).

---

## 6. Edge and recommendations (grounded)

**A. Cross-asset review alignment** (full narrative: [AUDIT_PLAN_CROSS_ASSET_REVIEW_2026-04-06.md](AUDIT_PLAN_CROSS_ASSET_REVIEW_2026-04-06.md)):

| Asset class | Direction (review) |
|-------------|-------------------|
| **CRYPTO** | Best near-term opportunity; keep **`smart_score`** central; do not lean on **`elite_score`** for crypto ranking until revalidated. |
| **EQUITY** | Structural loser *pool*; needs **allowlists / gates / lane retirement**, not weights alone. |
| **FOREX** | Experimental; **confidence** is not a strong trusted signal yet; need more closed sample + monotonicity. |
| **COMMODITY / ETF** | Thin sample in public evidence; **keep separate** in every report; do not import crypto assumptions. |

**B. This JSON analysis supports P0 in that review:** truth-layer checks (compare pick vs `systems` unrealized), split tables by asset class, flag strategies with no closed history.

**C. Data-driven bullets (this snapshot):**

1. **Trust closed-book IC for scoring**, not open-book unrealized correlation — Section 2.3 vs Section 3.
2. **Asset class:** At scale, only **crypto** shows positive mean realized pnl here; non-crypto needs tighter gates — consistent with [ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md](ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md).
3. **Smart picks = 0:** Premium tier empty; investigate `passes_smart_gate` / anti-overfit / floors — [TRACE_LOG.MD](../TRACE_LOG.MD).
4. **Direction / mode:** Peer bus (genome / claude-paper-tv): **SHORT vs LONG**, **SWING vs SCALP**; re-validate on each fresh snapshot before production sizing.
5. **Score breakpoint:** Closed deciles suggest **score ≥ ~55** as breakpoint; align smart floors / display tiers in backlog (`quality_gates.py`).
6. **Next fixes are not in this doc:** promotion vs forward, DSR/FDR as **gates**, toxic lane removal — see [HEDGE_FUND_ENHANCEMENT_PLAN.md](../HEDGE_FUND_ENHANCEMENT_PLAN.md).

---

## 7. Redis bus (peer context captured this session)

Recent `bus:broadcast:log` topics relevant to this analysis include: **`audit_plan_cross_asset_review`**, **`audit_picks_score_improvement_review`** (peer endorsement of this JSON-first workflow — see [AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md](AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md)), **`trace_log`**, **`ASSET_CLASS_EDGE_SCORING_FLAWS`**, genome/claude **SHORT bias** and **TP vs SL exit** gap, **STRONG-flag / score decile** notes. This doc does **not** adopt conflicting peer DOW claims without re-running time-bucket code — use [DOW_CLOSED_TRADES_STUDY_2026-04-07.md](DOW_CLOSED_TRADES_STUDY_2026-04-07.md) for DOW methodology.

**Publish this analysis:** `python tools/bus_post_audit_picks_edge.py`

---

## 8. Changelog row

Documented under **`AUDIT_PICKS_EDGE_ANALYSIS`** in [REDIS_BUS_CHANGELOG.md](REDIS_BUS_CHANGELOG.md).

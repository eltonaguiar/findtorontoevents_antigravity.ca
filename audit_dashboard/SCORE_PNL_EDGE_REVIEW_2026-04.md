# Audit score vs realized PnL — quant review (2026-04-06)

**Scope:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit) score families — **active** book, **verified alpha** block, **smart** tier logic (quality gates), and **closed** outcomes — split **crypto** vs **non-crypto**.

**Data:** `audit_dashboard/data/dashboard_data.json` snapshot embedded in this repo at analysis time (`n_recent_closed=3500`, `n_active=57`). **Machine-readable output:** `tools/data/score_pnl_analysis.json` (regenerate with `python tools/analyze_audit_scores_vs_pnl.py`).

**Method (quant):** Information coefficient (IC) proxy — **Pearson** and **Spearman** correlation between scalar scores and **`pnl_pct`** on `recent_closed`. **Smart score** was **recomputed** with `audit_trail.quality_gates.calculate_smart_score` when missing on closed rows (JSON often omits it). **SMART vs ACTIVE vs REJECTED** uses a **counterfactual** gate check (`status` forced to `OPEN`) so closed trades can be classified the same way live picks would be.

---

## Executive summary

1. **Ranking works on average but is noisy:** Pool-wide Spearman(score, pnl) ≈ **0.18**; **crypto-only** ≈ **0.11** — weak but positive; **non-crypto** ≈ **0.33** — materially stronger.
2. **Elite layer carries signal:** **`elite_score`** has the **highest** Spearman vs pnl on the **full** closed sample (~**0.20**) and dominates on **non-crypto** (~**0.39**). **`confidence`** is almost **uncorrelated** with pnl (Pearson ~**0.01** pool-wide) — it should **not** dominate any composite intended to predict mark-to-market or exit PnL.
3. **Smart tier is economically meaningful:** Counterfactual **SMART** closed picks: **~64.5%** win rate, mean pnl **+0.73%** vs **ACTIVE** **~44%** WR, mean **−0.01%** (same `n` scale in slice — see JSON).
4. **Verified-alpha cohort is score-rich:** Only **32** historical closes matched current `verified_alpha.active_pick_refs` keys, but in that slice **Spearman(score, pnl) ≈ 0.54** — scores align well **where** the book is already curated to PM/audited sources.
5. **Active book (mark-to-market):** With **n=57**, **`smart_score`** vs **`pnl_pct`** Spearman ≈ **0.42** (high variance; treat as directional only).
6. **Smart picks feed:** `picks.smart_picks` length **0** in this snapshot — the UI section may be empty even when smart **tier** logic applies elsewhere; worth a pipeline check.

---

## Score definitions (where they live)

| Score / concept | Role | Primary implementation |
|-----------------|------|-------------------------|
| **`score`** | Dashboard 0–100 gate input; feeds smart base | `dashboard_generator` normalization + `quality_gates` |
| **`smart_score`** | 0–100 ranking for “smart” table | `audit_trail/quality_gates.py` → `calculate_smart_score` |
| **`ml_composite_score` / `ml_score`** | Model / ensemble outputs | Upstream systems + dashboard merge |
| **`elite_score`** | Second-stage composite | Elite breakdown in pick JSON |
| **`confidence`** | Declared probability-style confidence | Feed metadata |
| **UI `computePickScore`** | Tracked-symbol composite in template | `audit_dashboard/template.html` (and deployed `index.html`) |

---

## Correlations vs `pnl_pct` (closed trades)

### Pool-wide (`n=3500`)

| Metric | Pearson | Spearman |
|--------|---------|----------|
| score | ~0.15 | ~0.18 |
| smart_score (recomputed) | ~0.12 | ~0.17 |
| ml_composite_score | ~0.15 | ~0.18 |
| **elite_score** | ~0.14 | **~0.20** |
| confidence | ~0.01 | ~0.07 |

**Quintile monotonicity (smart_score, equal-frequency):** Q1 mean pnl ≈ **−0.36%** (35% WR) → Q5 ≈ **+0.71%** (64% WR); **top-minus-bottom** mean pnl ≈ **+1.06 pp**.

**Raw score quintiles:** similar lift (~**+1.58 pp** mean pnl Q5 vs Q1).

**Score quartiles (win rate):** top quartile by **score** ≈ **59%** WR vs bottom ≈ **32%** (**~27 pp** spread).

### Crypto (`n=2867`)

Spearman vs pnl: **score ~0.11**, **smart_score ~0.13**, **elite ~0.13**, **confidence ~0.05**. Signals are **real but soft** — expect large **per-strategy** heterogeneity (see per-`source_system` blocks in `score_pnl_analysis.json`).

### Non-crypto (`n=633`)

Spearman vs pnl: **score ~0.33**, **ml_composite ~0.33**, **elite ~0.39**, **smart_score ~0.19**. **Non-crypto book should not share the same rank map as crypto** for capital / UI emphasis.

---

## Verified alpha (dashboard block)

From `dashboard_data.json` → `verified_alpha`:

- **active_count** 31, **smart_count** 0 (snapshot), **active_share_pct** ~54%.
- **Realized** (cohort semantics): ~**2083** trades, **50.5%** WR, **+273%** sum pnl % (as reported in JSON — not comparable to per-trade `%` without sizing).
- **Audited** coverage: **20** active picks with WR stats; **median_wr_pct** ~43.9%.
- **Overlap analysis:** **32** closed picks matched `active_pick_refs` (id or symbol|strategy|direction). In that slice, **score** and **smart_score** Spearman vs pnl ≈ **0.54–0.57** — **strong** for this business line.

**Implication:** Verified-alpha names are a **natural place** to sort aggressively by **score / smart_score**; the global pool dilutes IC.

---

## Active picks (`n=57`)

Mark-to-market **`pnl_pct`** vs scores (same snapshot):

- **smart_score** Spearman **~0.42** (best among scalars here).
- **score** Spearman **~0.26**.
- **ml_composite_score** near **0** Pearson; weak Spearman — **do not** treat ML composite as live PnL proxy on the small active slice without more data.

Caveat: **57** points → wide confidence intervals; use for **product direction**, not significance tests.

---

## Actions implemented / recommended

### Done in repo (2026-04-06)

1. **`tools/analyze_audit_scores_vs_pnl.py`** — reproducible IC + quintile + trust-tier + source slices → **`tools/data/score_pnl_analysis.json`**.
2. **`computePickScore` reweight** in `audit_dashboard/template.html` and **`index.html`**: **down-weight `confidence`**, **add `elite_score`** when present (see comment above function). Rationale: empirical IC; **not** a guarantee of future edge.

### Recommended next (higher edge / lower overfit)

1. **Split models by `asset_class`** — different score→PnL maps; optional **two column sorts** or **within-class z-scores** in UI.
2. **Replace static weights with rolling isotonic / Platt** on **walk-forward** weeks (map composite → E[pnl | bucket]) — classic quant calibration.
3. **Add shrunken strategy×symbol expectancy** from `recent_closed` (Empirical Bayes) as an explicit **0–100** subscore — decouples “model confidence” from “historical edge here.”
4. **Per-source dashboards** — JSON already includes large-`n` **source_system** slices; promote sources with **monotonic** quintile curves, demote **inverse** curves.
5. **Fix `smart_picks` feed** if product expects a non-empty `picks.smart_picks` array for a dedicated tab.

---

## Redis bus (one-liner for agents)

Broadcast after edits:

`python C:/Users/zerou/redis-bus/agent_bus.py broadcast cursor-composer "AUDIT_SCORE_IC: closed n=3500 Spearman(score,pnl)~0.18; crypto~0.11 noncrypto~0.33; elite strongest; conf~0 IC; SMART tier +20pp WR vs ACTIVE; verified-alpha overlap n=32 Spearman~0.54; computePickScore reweighted elite+downconf. See audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md + tools/data/score_pnl_analysis.json"`

---

## Caveats

- Correlations are **simultaneous / outcome-based** on **heterogeneous** strategies — not a causal A/B.
- **Survivorship / path / sizing** omitted — `pnl_pct` is not dollar utility.
- **Counterfactual SMART/ACTIVE** depends on current gate code applied to historical rows; regime drift can change results after the next gate edit.

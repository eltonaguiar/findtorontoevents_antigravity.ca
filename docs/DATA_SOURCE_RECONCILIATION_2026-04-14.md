# Data Source Reconciliation & True State of the System

**Date:** 2026-04-14  
**Context:** Two independent analyses reached contradictory conclusions. This document reconciles them.

---

## The Contradiction

| Analysis | Data Source | Definitive WR | PF | Verdict |
|----------|-----------|--------------|-----|---------|
| `real_edge_analysis.py` | `alpha_engine/data/closed_picks.json` | 32.8% | 0.38 | "Systematically losing" |
| Our dashboard analysis | `audit_trail/data/dashboard_payload.json` → `recent_closed` | 52.3% | 1.41 | "Real edge on definitive exits" |

**Both are correct. They're measuring different things.**

---

## The Three Data Sources

| Source | Picks | What's in it | Dominant strategy |
|--------|-------|-------------|-------------------|
| `alpha_engine/data/closed_picks.json` | **4,157** | Only alpha_engine system picks | `quan_engine_scalp` **81.6%** (3,392 picks) |
| `audit_trail/data/universal_resolved_picks.json` | **4,282** | All resolved picks from all systems | Mixed |
| `dashboard_payload.json` → `recent_closed` | **3,500** (capped) | Curated subset from 30+ JSON sources | Diverse — `multi_asset_copytrader` 19.8%, `alpha_engine` 17.9%, `claude_gainer_st` 16.1% |

### Why `real_edge_analysis.py` shows PF=0.38

It used `alpha_engine/data/closed_picks.json` where **`quan_engine_scalp` is 81.6% of all picks** (3,392 out of 4,157). This single strategy has:
- 33.5% WR, PF 0.38
- Avg win +0.37%, avg loss -0.48%
- It IS systematically losing

**The `real_edge_analysis.py` findings are true but narrow.** They describe the alpha_engine subsystem, not the full multi-source platform.

### Why our dashboard analysis shows PF=1.41 on definitive exits

The dashboard payload aggregates from 30+ systems. `quan_engine_scalp` is only 15% (524/3,500) instead of 82%. The remaining 85% comes from systems that actually have edge:
- `multi_asset_copytrader`: 693 picks (19.8%) — forex/commodity with PF 1.54
- `claude_gainer_st`: 565 picks (16.1%) — crypto with PF 2.09
- `stocks_competition`: 371 picks (10.6%) — equity, PF 0.65 (losing)
- `kimi_riseoftheclaw`: 261 picks (7.5%) — mixed, PF 1.09

**When you look at all sources together, the winning systems dilute `quan_engine_scalp`'s losses.**

---

## Exit Reason Distribution ALSO Differs by Source

| Exit Type | alpha_engine (4,157) | Dashboard payload (3,500) | Universal (4,282) |
|-----------|---------------------|--------------------------|-------------------|
| SL | 45.3% (1,883) | 28.8% (1,009) | 48.5% (2,075) |
| TP | 23.2% (965) | 30.2% (1,057) | 40.2% (1,721) |
| TIME | **30.9%** (1,283) | 22.9% (802) | 11.3% (486) |
| LOST | — | 15.0% (526) | — |

The alpha_engine source has **30.9% TIME_EXIT** — the highest. This is because `quan_engine_scalp` frequently times out. The dashboard payload has 22.9% TIME + 15% LOST.

The universal resolved picks show only 11.3% TIME — suggesting many timeouts are reclassified as SL or TP in the resolution pipeline.

---

## What's Actually True (Reconciled)

### 1. `quan_engine_scalp` is a proven loser

`real_edge_analysis.py` is right: 3,392 picks, 33.5% WR, PF 0.38. **This strategy should be paused immediately.** It's the single largest source of losses in the entire system.

The strategy accounts for:
- **81.6%** of alpha_engine closed picks
- But only **15.0%** of dashboard payload (because the payload aggregates from other sources)
- This means our "dashboard-level" metrics were partially hiding `quan_engine_scalp`'s failure behind dilution from other systems

### 2. The multi-source aggregate DOES have edge — but it's fragile

On definitive exits from the dashboard payload:
- Overall PF 1.41, 52.3% WR — beats random baseline ✅
- Crypto PF 1.88 — real edge ✅
- Forex PF 12.02 — real edge ✅  
- Equity PF 0.70 — no edge ❌

But this edge comes from specific systems (`claude_gainer_st`, `multi_asset_copytrader`, `signal_validation`), not from the alpha_engine core.

### 3. TIME_EXIT contamination is real in ALL sources

`real_edge_analysis.py` correctly identified this. Whether you look at alpha_engine (30.9% TIME) or dashboard payload (22.9% TIME + 15% LOST), a large fraction of picks have ambiguous exits.

### 4. The win/loss asymmetry is the deeper problem

`real_edge_analysis.py` identified the key arithmetic:
- `quan_engine_scalp`: avg win +0.37%, avg loss -0.48%, payoff ratio 0.77
- To break even at 33% WR, you need payoff ratio ≥ 2.05
- The system is at 0.77 — you'd need to nearly **triple** the win size

This means the TP/SL geometry (ATR 2.5× TP / 1.5× SL) is not calibrated for `quan_engine_scalp`'s actual WR. The R:R looks good on paper (2.5/1.5 = 1.67) but most trades hit SL before reaching TP.

### 5. Mercury's claims remain invalid

- **"73.7% SHORT edge"**: Confirmed debunked. n=19-33, CI spans coin-flip range.
- **"PR #145 feature_drift.py flagged 23/32 features"**: Confirmed fabricated. No such PR exists.
- **All file paths proposed by Mercury**: Fictional (`src/strategy/`, `src/models/`, etc.). The real code lives in `alpha_engine/`.
- **Mercury's DecisionEngine class**: No single classifier drives picks. The system is multi-source, not a single `predict_proba` pipeline.

### 6. The `adaptive_tp_sl.py` feedback loop is broken

`real_edge_analysis.py` correctly identified: `adaptive_tp_sl.py` tightens R:R toward 1.5 based on stats that include TIME_EXITs. At 33% WR, R:R 1.5 is mathematically guaranteed to lose. The optimizer is calibrated against contaminated data.

---

## Revised Priority Actions

| # | Action | Why | Data Source |
|---|--------|-----|-----------|
| **1** | **Pause `quan_engine_scalp`** | 3,392 losing picks, PF 0.38, 81.6% of alpha_engine volume | `alpha_engine/data/closed_picks.json` |
| **2** | **Exclude TIME_EXIT from all WR/PF calculations** | 23-31% of picks are noise, contaminates every metric | All sources |
| **3** | **Fix `adaptive_tp_sl.py` to exclude TIME_EXIT from MFE/MAE** | Optimizer calibrated on contaminated data → TP too tight | `alpha_engine/adaptive_tp_sl.py:185` |
| **4** | **Normalize BUY→LONG, SELL→SHORT at write time** | Downstream analysis splits them incorrectly | `scanner.py` or wherever `open_pick()` writes |
| **5** | **Classify LOST picks** — are they SL-equivalent? | 526 picks (15%) in ambiguous state. 520 are negative PnL. | `dashboard_payload.json` |
| **6** | **Investigate `quan_engine_scalp` by hour/symbol** | Maybe a profitable sub-slice exists in the 3,392 trades | New analysis |
| **7** | **Bootstrap CI for `quan_engine_swing`** | Only +PF strategy in alpha_engine (1.32 on n=85). Is it real? | New analysis |
| **8** | **Fix train-serve 39→41 feature misalignment** | ML predictions corrupted for all alpha_engine picks | `alpha_engine/ml_ranker.py` |

---

## What Each Data Source Is Good For

| Question | Use This Source |
|---------|----------------|
| "Is the alpha_engine subsystem profitable?" | `alpha_engine/data/closed_picks.json` → **No, PF 0.38** |
| "Is the multi-source platform profitable?" | `dashboard_payload.json recent_closed` → **Marginal, PF 1.13 all / 1.41 definitive** |
| "Which specific strategies have edge?" | Dashboard payload, filtered by `source_system` and `strategy` |
| "What's the TP/SL hit rate?" | `universal_resolved_picks.json` (48.5% SL / 40.2% TP — cleanest exit labels) |

**Never mix data sources in a single analysis without stating which one you used.** The contradictory conclusions we've been seeing are primarily due to analyzing different subsets without realizing it.

---

*Generated 2026-04-14 by comparing `alpha_engine/data/closed_picks.json` (4,157 picks), `dashboard_payload.json recent_closed` (3,500 picks), and `universal_resolved_picks.json` (4,282 picks).*

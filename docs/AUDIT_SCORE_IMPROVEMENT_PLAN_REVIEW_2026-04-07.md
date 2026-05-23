# Audit score improvement — plan review & cross-asset feedback

**Date:** 2026-04-07 (UTC)  
**Scope:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit) prediction quality vs hedge-fund bar; review of Cursor plan `audit_picks_edge_analysis` + alignment with repo truth layer.  
**NFA:** Research and engineering notes only — not investment advice.

---

## 1. Plans reviewed

| Artifact | Role |
|----------|------|
| Cursor plan `audit_picks_edge_analysis_dbcaff8e.plan.md` (`~/.cursor/plans/...`) | **Execution blueprint:** snapshot `dashboard_data.json` → new active-book analyzer → one MD report → Redis bus + changelog. Correct **JSON-first** stance; defers SQL; no placeholder metrics. |
| `HEDGE_FUND_ENHANCEMENT_PLAN.md` | **Institutional gap list:** DSR, purged CV, tail risk, kill switches, experiment log. Flags **edge crisis:** backtest–forward correlation, SL hit rate — *scoring alone cannot fix a wrong objective or overfit selection*. |
| `docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md` | **Closed-trade evidence (n≈3500):** per–asset-class ρ(smart/elite/ml) vs PnL, structural equity bleed, forex weak headline score. |
| `docs/KIMI_AUDIT_FINDINGS_20260405.md` | **Dashboard integrity:** summed total PnL, drawdown caps, drill-down payload — fix **before** trusting headline “proven vs sandbox” tables. |
| `TRACE_LOG.MD` | **Pipeline:** active vs `active_raw`, smart, VA — use when reconciling “what the page shows” vs generator stages. |

---

## 2. Verdict on the Cursor plan

**Adopt.** The plan closes an important gap: today we have strong **closed-book** cuts (`analyze_audit_scores_vs_pnl.py`, `analyze_asset_class_edge_flaws.py`) but no single **active-book** report tied to the same snapshot (unrealized PnL, score vs MTM with **n≥25 guardrail**, strategy→closed join). That is exactly what operators need to stop confusing “live score rank” with “eventual edge.”

| Plan todo | Status | Note |
|-----------|--------|------|
| Snapshot `dashboard_data.json` (live or generator) | **Pending** | Record `generated_at` in every derivative JSON/MD. |
| `tools/analyze_audit_active_book.py` → `tools/data/audit_active_book_analysis.json` | **Pending** | Not in repo yet; implement per plan §Gap. |
| `docs/AUDIT_PICKS_EDGE_ANALYSIS_<date>.md` | **Pending** | This file is the **meta/review** track; the plan’s dated analysis MD should merge active JSON + cites below. |
| `tools/bus_post_audit_picks_edge.py` + changelog | **Partial** | Publisher script added 2026-04-07; run after first full analysis cycle. |

---

## 3. Why it feels “so close” but isn’t hedge-fund consistent

1. **Two different games:** Dashboard scores (smart/elite/ML) partly **rank** within a class; **mean expectancy** of the *traded universe* can still be negative (equity, forex). Good ranking + bad universe = “we sort losers well.”
2. **Crypto:** `smart_score` carries signal (ρ≈0.26); **elite** is nearly flat (ρ≈0.07) — weighting elite heavily in crypto **hurts** discrimination until reformulated per `ASSET_CLASS_*` doc.
3. **Equity:** Elite ranks better (ρ≈0.35) but **mean PnL ~−0.78%** and **WR ~35%** — strategy lanes (dividend/value/earnings) are structurally toxic; need **allowlist / gates**, not only score tweaks.
4. **Forex / commodities / ETF:** Small n or weak ρ(confidence); treat as **experimental** until closed n grows and confidence is recalibrated or dropped from composite.
5. **Truth layer:** Until P0 aggregates (summed % totals, DD caps) match **one** compounding narrative, leadership will mis-prioritize “more strategies” vs “correct metrics + fewer toxic lanes.”
6. **Selection bias:** `HEDGE_FUND_ENHANCEMENT_PLAN.md` / `EDGE_ADDENDUM.md` — if forward validation **inverts** backtest rank, promotion rules are selecting noise; Kimi-style **tier discipline** (`alpha_engine/kimi_swarm_risk/`) belongs **after** closed-stats join, not as a cosmetic label.

---

## 4. Priority stack (data-driven)

| Priority | Action | Owner signal |
|----------|--------|--------------|
| P0 | Close Kimi **dashboard aggregation** items (total PnL definition, DD cap, drill-down payload parity) | `KIMI_AUDIT_FINDINGS` |
| P0 | Ship **`analyze_audit_active_book.py`** + one MD per snapshot | Cursor plan |
| P1 | **Asset-conditioned weights:** crypto ↑ smart, ↓ elite; equity use elite for rank but **gate** strategies by rolling expectancy | `ASSET_CLASS_EDGE_SCORING_FLAWS_*` |
| P1 | **Forex:** recalibrate or zero-weight confidence; require larger n before capital narrative | same |
| P2 | DSR + purged CV + experiment log | `HEDGE_FUND_ENHANCEMENT_PLAN.md` |
| P2 | Emit `kimi_tier` on picks post–`strategy_performance` join; re-announce bus on threshold changes | `docs/REDIS_BUS_KIMI_TIER.md` |

---

## 5. Reproduction (when analyzers land)

```text
# 1) Snapshot (live or local generator) → record path + generated_at
# 2) python tools/analyze_audit_scores_vs_pnl.py   (if stale vs snapshot)
# 3) python tools/analyze_asset_class_edge_flaws.py
# 4) python tools/analyze_audit_active_book.py
# 5) Author docs/AUDIT_PICKS_EDGE_ANALYSIS_<UTC_DATE>.md
# 6) python tools/bus_post_audit_picks_edge.py --append-changelog
```

---

## 6. Changelog (this doc)

| Rev | Change |
|-----|--------|
| 2026-04-07 | Initial review: Cursor plan endorsed; cross-asset feedback; todo table; Redis topic `audit_picks_score_improvement_review`. |
| 2026-04-06T22:49:43Z | Published to `alpha_engine_bus` via `tools/bus_post_audit_picks_edge.py`; changelog row in `docs/REDIS_BUS_CHANGELOG.md`; site summary `updates/2026-04-07-audit-score-improvement-review.html` + index entry. |

---

## Related paths

- `docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md`
- `tools/analyze_asset_class_edge_flaws.py`, `tools/analyze_audit_scores_vs_pnl.py`
- `updates/2026-04-07-audit-score-improvement-review.md` (public summary)
- `docs/REDIS_BUS_CHANGELOG.md` (fleet row after bus publish)

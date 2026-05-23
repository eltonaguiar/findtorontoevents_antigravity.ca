# /audit Enhancement Implementation Queue — Top 5 EV-Ranked

Date: 2026-05-04
Selection rule: highest expected value (user-impact × confidence × feasibility) among items in `reports/kimi_deep_review_audit_only_2026_05_04.md`. Excludes investigative-only items (e.g., C1 R:R re-audit, which must precede any gate change but produces no UI change itself).

Order is the recommended merge sequence; later items assume earlier ones land.

---

## #1 — Score Explainability Tooltips + Tier Cards

- **Why:** Resolves Kimi C12 / E7 / E8 / E9 / I8 (user explicitly confused F-Score 4/9 vs Score 0.748 vs 0.703). Zero current tooltips matching F-Score/Piotroski/composite in `template.html` (grep count = 0). Highest user-clarity ROI per line of code.
- **Files to edit:**
  - `audit_dashboard/template.html` (info icons next to F-Score, Score, Composite, Tier; popover container)
  - `audit_dashboard/dashboard_enhancements.js` (popover show/hide on hover/focus, ARIA)
  - `audit_dashboard/dashboard_generator.py` (emit `metric_definitions` block into `dashboard_data.json`)
  - `audit_dashboard/data/dashboard_data.json` (schema bump)
- **Acceptance:** Playwright spec asserts `[data-metric-tooltip="f-score"]` is focusable and reveals text containing "Piotroski" and "9 criteria"; same for `score`, `composite`, `tier`. All 4 tooltips have `aria-describedby` linkage. Numeric: 0 tooltips → ≥4 distinct tooltips.
- **Complexity:** S
- **Dependencies:** None.

---

## #2 — Best-Picks UI Guidance Card + Saved Filter Presets

- **Why:** Resolves E3 / E13 / D3 / D8 / I3 (the user's top-line UX question: "which button do I click to find the best picks?"). Combines two related Kimi requests into one PR for coherent UX.
- **Files to edit:**
  - `audit_dashboard/template.html` (new "Where to start" card above hero; preset chips: Conservative / Moderate / Aggressive)
  - `audit_dashboard/dashboard_enhancements.js` (apply-preset → set filters + scroll)
  - `audit_dashboard/dashboard_generator.py` (compute & emit `recommended_filter_preset` and per-preset PF/WR/n)
  - `audit_dashboard/data/dashboard_data.json` (presets payload)
  - `tests/playwright/audit-presets.spec.ts` (new)
- **Acceptance:** Playwright: clicking each preset chip sets exactly the documented filter combo (assert URL/state); guidance card visible above the fold (viewport height assertion 1080px desktop + 812px iPhone-13). Numeric: each preset must surface ≥10 picks on current `dashboard_data.json` snapshot.
- **Complexity:** M
- **Dependencies:** #1 (presets reference tier definitions established by tooltip copy).

---

## #3 — Trust Badges Driven by Walk-Forward OOS Sharpe

- **Why:** Resolves E14 / D9 / C16. Hard data already exists (EQUITY OOS Sharpe 3.527 vs FOREX -1.406) but isn't visible per-asset-class on the dashboard. Lets users immediately see where edge is real.
- **Files to edit:**
  - `audit_dashboard/dashboard_generator.py` (compute trust grade A-F from OOS Sharpe + n + consistency)
  - `audit_dashboard/template.html` (asset-class header badges)
  - CSS in `template.html` (badge styles)
  - `audit_dashboard/data/dashboard_data.json` (`asset_class_health[*].trust_grade`)
- **Acceptance:** Each rendered asset class has a `data-trust-grade` attr ∈ {A,B,C,D,F}. Playwright asserts EQUITY ≥ B, FOREX ≤ D, ETF = A or B (snapshot-dependent). Numeric: trust_grade present for ≥6/7 asset classes in `asset_class_health`.
- **Complexity:** S
- **Dependencies:** #1 (uses tier-card tooltip copy to explain grade).

---

## #4 — C-Tier Guard Rail + Paper-Only Badge

- **Why:** Resolves C5 (CRYPTO C-Tier PF 0.36 / WR 28% — currently presented to retail as if equally viable). Direct capital-protection win. Kimi explicitly demands "must not be presented to users as viable picks".
- **Files to edit:**
  - `audit_dashboard/template.html` (warning banner on C-Tier section + per-pick "Paper Only" pill)
  - `audit_dashboard/dashboard_generator.py` (emit `tier_warning` and `allocation_cap_pct: 5` for C-Tier)
  - `alpha_engine/smart_picks_engine.py` (annotate `pick.advisory = "paper_only_c_tier"`; do NOT remove pick — Kimi protocol)
  - `audit_trail/quality_gates.py` (read advisory in score path; cap C-Tier contribution to score)
- **Acceptance:** Playwright: every C-Tier pick row has `[data-advisory="paper_only_c_tier"]` and a visible "Paper Only" pill. Banner says "5% allocation cap". Numeric: 100% of C-Tier picks tagged; 0 false positives on A/B/S-Tier.
- **Complexity:** M
- **Dependencies:** #3 (uses trust badge styling system).

---

## #5 — Hyrotrader Parity (import explainability + trust badges)

- **Why:** Closes the /audit/hyrotrader gap. Currently `hyrotrader/index.html` is a near-bare page — no F-Score tooltips, no walk-forward badge, no preset chips. Reusing #1+#3 outputs gives hyrotrader the same clarity for ~10% of the effort.
- **Files to edit:**
  - `audit_dashboard/hyrotrader/index.html` (import shared tooltip/badge HTML partials)
  - `audit_dashboard/dashboard_generator.py` (emit `hyrotrader_data.json` mirroring `metric_definitions` + per-strategy trust grades)
  - `audit_dashboard/dashboard_enhancements.js` (extend popover scope to hyrotrader DOM)
  - `audit_dashboard/hyrotrader/hyro_live_signals.js` (consume new data file)
  - `tests/playwright/hyrotrader-parity.spec.ts` (new)
- **Acceptance:** Playwright: `/audit/hyrotrader` page passes the SAME tooltip + trust-badge assertions as #1 and #3. Numeric: tooltip count on hyrotrader == tooltip count on /audit (≥4). Trust grade visible on every strategy card.
- **Complexity:** M
- **Dependencies:** #1 and #3 (consumes their components and data shapes).

---

## Sequencing summary

```
#1 Tooltips (S)  →  #2 Presets (M)
              ↘
                #3 Trust Badges (S)  →  #4 C-Tier Guard (M)
                                    ↘
                                      #5 Hyrotrader Parity (M)
```

Total est. effort: 2 S + 3 M ≈ 1.5–2 weeks single-dev. None require changes to events page or sports.

## Explicitly NOT in this queue (and why)

- **R:R gate change (Kimi C1):** Conflicts with our local 2026-04-01 closed-pick analysis. Investigation PR (`audit/rr-band-reaudit`) must run first; gate change is downstream.
- **ml_score gate raise to 0.90 (C2):** Blocked on ml_score fill-rate (currently low → would zero-out picks). Add fill-rate widget first (separate P1).
- **Tab consolidation (C17):** High effort, low confidence (UX-subjective); defer until after #1-#5 land and we have telemetry.
- **MEME asset class split (C7):** Touches scrapers + scoring + UI; punt until #4 proves the C-Tier guard pattern.

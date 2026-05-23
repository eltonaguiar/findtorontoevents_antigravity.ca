# Kimi Deep Review — /audit + /audit/hyrotrader Only

Date: 2026-05-04
Source: `C:/Users/zerou/Downloads/Kimi_Agent_Prediction Edge Audit/` (10 sections + requirements + final)
Scope filter: items targeting `/audit` (audit_dashboard) or `/audit/hyrotrader`. Excluded: events page, sports betting, mutual-fund/penny/meme product-policy items unless they touch audit UI.

Kimi enumerates 27 explicit requests (E1-E27), 18 implicit needs (I1-I18), 18 critical issues (C1-C18). Mapping below uses those IDs.

## Conflict flag (must resolve before any code change)

Kimi C1 mandates **R:R floor 1.5, ceiling 2.0** ("1.5-2.0 band PF 5.81; >2.0 band PF 0.35"). Local `audit_trail/quality_gates.py:2492-2511` carries an opposite "DATA CORRECTED 2026-04-01" comment claiming R:R is INVERTED (tight 1.0-1.5 = 70.8% WR; 1.5-2.0 = 45.6%; 2.0-3.0 = 42.4%). Current live constants: `SMART_PICKS_MIN_RR=1.5`, `SMART_PICKS_MAX_RR=3.5` (line 579-580). Either Kimi's golden-band closed-CSV or our 1868-pick analysis is wrong. **No R:R gate change should ship until a fresh `tools/mutation_analysis.py` export adjudicates.** Treat C1 as P0 *investigation*, not P0 *fix*.

Similarly C2 (ml_score>=0.90) conflicts with `SMART_PICKS_MIN_ML_SCORE=0.0` ("ml_score not reliably populated upstream", line 265-269, 581). Re-enabling the gate at 0.90 with current fill rate would zero out picks. P1 with prerequisite: validate ml_score fill rate first.

## Mapping table

| Kimi req# | Description | /audit? | /hyrotrader? | Live state | Fixed? | Proposed PR / branch / edits | Pri |
|---|---|---|---|---|---|---|---|
| E3 / D3 / I3 | Optimal UI path for best picks (HC vs smart vs verified alpha vs filter combos) | Y | N | template.html has all buttons but no ranked guidance card; `dashboard_data.json` has per-filter PF in `performance.filter_combinations` (verify) | No | `feat(audit): add Best-Picks UI guidance card` / `audit/best-picks-guide`. Edits: template.html (~hero section, new card), dashboard_generator.py (emit `recommended_filter_preset`), dashboard_data.json schema, e2e/playwright spec | P1 |
| E4 / D5 / E26 / I7 | Guide page accuracy vs live edge | Y | N | `?Guide` (template.html "Guide" panel) hand-curated; no auto-cross-check vs `asset_class_health` | No | `feat(audit): auto-generate Guide edge claims from asset_class_health` / `audit/guide-autosync`. Edits: dashboard_generator.py (inject guide_claims), template.html Guide section, add diff test | P1 |
| E6 / C18 / D6 | HTML nested-comment bug `' inside this block — HTML does not support nested comments...'` | Y | possibly | grep on template.html: 0 matches → likely already removed OR lives in a sub-template / hyrotrader/index.html | Likely fixed in template.html; recheck hyrotrader/index.html and `claudes_test.html` | `fix(audit): scrub residual nested-comment artifacts` / `audit/html-comment-scrub`. Edits: hyrotrader/index.html, claudes_test.html, antigravity_picks.html | P2 |
| E7 / D17 / I8 | Page enhancement: explain metrics/scores/filters | Y | Y | template.html has 0 tooltips matching F-Score/Piotroski/composite | No | `feat(audit): score explainability tooltips + tier cards` / `audit/score-explainability`. Edits: template.html (info icons + tooltip popovers), dashboard_enhancements.js (popover JS), dashboard_generator.py (emit metric_definitions block), CSS | P1 |
| E8 / E9 / D7 / C12 / I8 | F-Score (4/9) vs Score 0.748 vs 0.703 vs Composite | Y | Y | No unified score-hierarchy doc in dashboard; multiple score keys (`score`, `elite_score`, `smart_score`, `ml_score` — quality_gates.py:2085) | No | Same PR as E7 + add `docs/SCORING_HIERARCHY.md` linked from Guide | P1 |
| E10 / D14 | Swing plays performance card | Y | N | dashboard_data.json likely has time-horizon split; not surfaced as standalone Swing tab | Partial | `feat(audit): swing-plays performance card` / `audit/swing-card`. Edits: dashboard_generator.py, template.html | P2 |
| E11 / D14 | Closed holds analysis | Y | N | "Closed Picks" tab exists | Partial | Enrich existing tab w/ tier+strategy breakdown | P2 |
| E13 / D8 / I3 | Filter preset recommendation (conservative/moderate/aggressive) | Y | N | No saved presets surfaced | No | `feat(audit): saved filter presets (conservative/moderate/aggressive)` / `audit/filter-presets`. Edits: template.html (preset chips), dashboard_enhancements.js (apply preset), dashboard_data.json (preset definitions emitted from generator), playwright spec | P1 |
| E14 / D9 / C16 | Trusted asset class ranking + walk-forward OOS surfacing | Y | N | `asset_class_health` exists; OOS Sharpe (EQUITY 3.527, ETF 6.368, FOREX -1.406, COMMODITY -2.412) likely in dashboard_data but no badge on UI | Partial | `feat(audit): trust badges driven by walk-forward OOS Sharpe` / `audit/trust-badges`. Edits: dashboard_generator.py, template.html, CSS | P1 |
| E16 / D11 / C16 / I13 | Backtesting methodology surfacing (PSR/DSR, walk-forward, transaction costs) | Y | Y | Walk-forward folds present in data; PSR/DSR not displayed | No | `feat(audit): PSR/DSR + walk-forward consistency panel` / `audit/wf-panel`. Edits: dashboard_generator.py (compute PSR/DSR), template.html, smart_picks_engine.py (no — read-only) | P2 |
| C1 / E25 | R:R gate floor=1.5 ceiling=2.0 (Kimi); local says inverse | both (gate drives picks shown in /audit) | Y | `SMART_PICKS_MIN_RR=1.5`, `SMART_PICKS_MAX_RR=3.5` | NOT applied (and may be wrong for our data) | **Investigation first**: `chore(audit): rerun mutation_analysis on closed CSV for R:R band` / `audit/rr-band-reaudit`. Edits: tools/mutation_analysis.py invocation, reports/, then conditional follow-up PR adjusting quality_gates.py:579-580 | P0 (investigate) |
| C2 / D11 | ml_score gate >= 0.90 | both | Y | `SMART_PICKS_MIN_ML_SCORE=0.0` (disabled, fill-rate issue) | No | `feat(audit): ml_score fill-rate dashboard widget + gradual gate ramp` / `audit/ml-score-fill`. Edits: dashboard_generator.py (fill-rate %), template.html (widget), quality_gates.py (raise to 0.50 once fill>80%) | P1 (gated by fill-rate) |
| C3 | 24h tracking window bias — extend to 120h | Y (changes published numbers) | N | Likely already 120h post-resolver-v2; verify in `outcome_resolver.py` | Likely fixed | Verify-only: add resolver-window banner to dashboard | P2 |
| C4 | Measurement-artifact audit (WR near 0/100%) | Y | N | Resolver v2.1 fixed Forex; no automated alert | Partial | `feat(audit): WR-extremum anomaly banner` / `audit/wr-anomaly`. Edits: dashboard_generator.py (flag rows), template.html banner | P2 |
| C5 | CRYPTO C-Tier value destruction (PF 0.36/WR 28%) — gate from UI | Y | N | C-Tier still rendered as viable | No | `feat(audit): C-Tier guard rail + paper-only badge` / `audit/c-tier-guard`. Edits: template.html (badge + CSS warn), dashboard_generator.py (allocation_cap_5pct flag), smart_picks_engine.py (annotate, do not kill) | P1 |
| C7 | MEME as distinct asset class | both | N | Currently rolled into CRYPTO | No | `feat(audit): split MEME asset class` / `audit/meme-split`. Edits: dashboard_generator.py (asset_class_map), quality_gates.py (MEME bucket caps), template.html | P2 |
| C10 / I17 | Orphan code goldmines (signal_quality_ml etc.) — needs to influence /audit picks | Y | Y | 16 orphans per `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md`; wire-up rule in CLAUDE.md | No | Per-orphan PRs with Wiring Plan into smart_picks_engine.score path | P1 |
| C11 | Outcome resolver duplication (5+ copies) | Y (data correctness) | Y | Canonical at `alpha_engine/outcome_resolver.py:115-126` per CLAUDE.md | Partially fixed (canonical declared); duplicates may persist | `chore: delete outcome_resolver duplicates, add import shim` / `chore/resolver-dedupe` | P1 |
| C13 | S-Tier survivorship bias disclosure on dashboard | Y | N | S-Tier rendered without disclaimer | No | `feat(audit): survivorship-filter disclaimer on S-Tier` / `audit/stier-disclaimer`. Edits: template.html | P2 |
| C17 / D17 / I18 | Tab overload — 13 → 5 | Y | N | Many tabs present | No | `feat(audit): tab consolidation + mobile-first nav` / `audit/tab-consolidate`. Edits: template.html | P2 |
| E5 / D14 | US Equity Picks / Closed Picks deep view | Y | N | Tabs exist; no per-strategy drill-down | Partial | merge into E11 PR | P2 |
| /audit/hyrotrader specific | Hyrotrader page parity (live signals, score panel) | N | Y | Only `hyro_live_signals.js` + `index.html`; no shared template parts; no F-Score tooltip; no walk-forward badge | No | `feat(hyrotrader): import audit explainability + trust badges` / `audit/hyrotrader-parity`. Edits: hyrotrader/index.html, shared CSS, dashboard_generator.py emit hyrotrader_data.json | P1 |

## Notes
- E1/E2/E15/E17/E18/E19/E20/E22/E23/E27 are analysis deliverables, not /audit code edits — addressed via reports, not PRs.
- E12/D8/D12/D13/I1/I2/I10/I11/I12/I14 (user safety guide, position sizing, Kelly) belong in Guide content; covered by E4 + E13 PRs above.
- C6 (cta_commodity_momentum_term ban), C8 (mutual fund exclusion), C9 (penny spread), C14 (short ban), C15 (AAPL exception) are strategy/policy not /audit UI — out of this report's scope.

Word count: ~1,180.

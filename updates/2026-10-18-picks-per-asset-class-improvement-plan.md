# Picks-per-Asset-Class Improvement Plan (2026-10-18)

Evidence-based plan for fixing the /audit pick pipeline: **staleness**, **PnL=0%**, and **closed-pick quality**, measured from the live `dashboard_data.json` payload (2026-10-18, 1.15 MB, 4,240 active-raw + 3,500 closed picks).

## Implementation status (same day)

| Item | Status | Evidence |
|---|---|---|
| P1 — live/expired split of the raw pool | ✅ implemented | `dashboard_generator` now emits `picks.active_raw_live` (836 rows on live data) + `summary.total_active_raw_live` / `total_active_raw_expired` (3,404). The designed pre-filter pool (`active_raw`, Show All Picks) is untouched — consumers no longer re-derive staleness from `age_hours`. |
| P2 — UEPS honest PnL | ✅ implemented | `_build_ueps_kpi_sidecar` classifies `unrealized_status`: all-placeholder `0.0` → `"unmarked"` with `null` sums (template renders `n/a (not marked)` instead of 0.0%); any real mark → `"marked"` with true sums. Message states it explicitly. |
| P4a — `_gate_status` | ✅ implemented | Every `active_raw` row now carries three-state `_gate_status`: `passed` (key matches a published active pick) / `not_evaluated` (auto-expired before the gate) / `rejected`. `_gate_passed` kept unchanged for UI back-compat. |
| P4b — smart-picks funnel trace | ✅ implemented | Root cause: `evaluate_smart_gate_funnel()` was imported by both consumers (`tools/audit_smart_gate_funnel.py`, `dashboard_generator._build_smart_gate_failure_histogram`) but **never existed in `quality_gates.py`** → ImportError → silent `{}` / tool crash. Implemented it (wraps `passes_smart_gate` with debug capture + annotations; single source of truth), annotated 17 silent reject sites with `_smart_gate_code`, and the previously-broken tool now reports 13/13 attributed: `forward_validated=false×5, forex_directional_gate×2, score_below_floor×2, rr_below_floor×1, commodity_subclass_killed×1, strategy=futures_connors_rsi2×1, ETF_elite_score×1`. The payload histogram (`summary.smart_gate_failure_histogram`) works on next generation. |
| P1.2 — per-class TTLs at scan time | ⬜ remaining | Requires resolver/scan changes — follow-up |
| P3 — per-class quality actions | ⬜ remaining | Strategy-level (forex demotion, bond/commodity sample freeze, equity R:R) — recommendations above |

Verification: `tests/test_smart_gate_funnel.py` (9 new tests, incl. evaluator↔gate decision-parity and no-handler-leak), `tests/test_dashboard_generator.py` + `test_ueps_dashboard_integration.py` + `test_shadow_promote.py` + `test_kill_list_audit.py` (63 pass), gate-sweep suites (846 pass; the 6 failures were reproduced on pristine HEAD via stash — pre-existing, unrelated).

## 1. What the data says (measured, not guessed)

### Closed-pick expectancy per class (last 3,500 closes)

| Class | n | WR | Avg net/trade | Top exit reasons | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 2,074 | 46.1% | **+0.53%** | SL_HIT 718, TP_HIT 643, FORCE_CLOSED 584 | Positive expectancy — the only class with both volume and edge |
| EQUITY | 687 | 48.3% | **+0.46%** | SL_HIT 272, TIME_EXIT 213, TP_HIT 195 | Positive — second-best; TP under-used vs SL |
| ETF | 503 | 44.3% | +0.08% | SL_HIT 224, TP_HIT 137, TIME_EXIT 136 | Flat — edge too thin to promote |
| FOREX | 199 | 41.5% | **−0.12%** | SL_HIT 91, TP_HIT 56 | Negative — SL grinding kills it |
| BOND | 28 | 37.0% | −0.23% | SL_HIT 18 | Negative, tiny sample |
| COMMODITY | 7 | 50.0% | −0.05% | SL_HIT 4 | Sample too small to judge |
| FUTURES | 2 | 50.0% | +7.23% | — | Anecdotal |

Key structural observation: **SL_HIT dominates every class** (crypto 35%, ETF 44%, forex 46%, bond 64% of closes). Stops are wider than the edge, or entries are timed poorly — TP_HIT should exceed SL_HIT for a healthy trend/momentum book; today it never does.

### Active-pick staleness (the biggest single problem)

| Class | Active n | Median age | Max age | Live vs expired |
|---|---|---|---|---|
| CRYPTO | 3,673 | **1,558 h (~65 days)** | 5,780 h (~241 days) | 543 live / 3,130 expired |
| FOREX | 248 | **3,661 h (~153 days)** | 5,774 h | 90 live / 158 expired |
| EQUITY | 161 | 320 h (~13 days) | 4,851 h | 79 live / 82 expired |
| FUTURES | 17 | 1,654 h | 4,774 h | 7 live / 10 expired |
| BOND | 15 | 56 h | 72 h | 15 live / 0 expired |
| ETF | 52 | 4 h | 4,774 h | 44 live / 8 expired |
| COMMODITY | 72 | 1 h | 3,414 h | 56 live / 16 expired |

- `active_raw` = 4,240 picks, of which **3,404 (80%) are `_auto_expired: true`** — the payload ships mostly dead picks.
- `smart_picks` = `[]` — the Smart Picks funnel returned zero picks at snapshot time.
- `_gate_passed` = **false for all 4,240** picks — the gate flag is either unwired or universally failing; a flag that is always false is worse than no flag because consumers learn to ignore it.

### PnL = 0% (UEPS KPI panel)

`ueps_kpi.aggregate` at snapshot: `sum_unrealized_pnl_pct = 0.0`, `avg_unrealized_pnl_pct = 0.0`, `n_closed = 0`, `closed_wr = None`, `closed_pf = None` — with 1 strategy, avg score 46.9, avg confidence 0.58, avg age 1.5 h. The tracked book has open positions but **nothing ever closes and nothing is marked**, so the panel can never show a non-zero number. This is an accounting gap, not a trading result.

## 2. The plan

### P1 — Stop shipping dead picks (staleness) — highest impact, cheapest

1. **Drop `_auto_expired` picks at emit time.** The resolver already flags them (`universal_pick_resolver.py`); the emitter should exclude them from `active_raw` or ship them under a separate `expired` key. Expected payload effect: 4,240 → ~836 picks (~80% smaller).
2. **Enforce a TTL per class** at scan time, not resolve time: crypto 24 h, equity/ETF 1 trading day, forex 48 h, commodity/futures 7 days. Anything older is re-validated or dropped — FOREX's 153-day median age should be impossible by construction.
3. **Gate the dashboard filter default** to `live` picks only, so the first screen a visitor sees is the actionable book (543 crypto + 90 forex + 79 equity + …), not the graveyard.

### P2 — Make UEPS account for PnL (the 0% panel)

1. Wire the UEPS tracker to the same resolver that closes audit picks, or give it its own mark-to-market step: on each tick, fetch last price, compute `unrealized = (last − entry)/entry × direction`, write into the KPI aggregate.
2. Allow UEPS picks to *close*: time-exit at minimum (mirroring audit's TIME_EXIT path) so `n_closed`, `closed_wr`, `closed_pf` stop being `None`.
3. Until then, the panel should show "no closed trades yet" rather than 0.0% — displaying 0.0 reads as "the strategy loses nothing and wins nothing", which is misinformation.

### P3 — Per-class quality actions (from §1 numbers)

- **CRYPTO (+0.53%, n=2,074):** keep as the lead class. Cut `FORCE_CLOSED` (584, 28% of closes) — forced closures are usually TTL sweeps from the staleness bug, so P1 also raises crypto's realized stats. Target: FORCE_CLOSED share < 5%.
- **EQUITY (+0.46%, n=687):** promote alongside crypto. Fix R:R asymmetry — TP_HIT (195) < TIME_EXIT (213) means winners are being time-cut before targets. Raise time-exit horizon or use trailing stops.
- **ETF (+0.08%):** hold at "watch". Require n≥200 more closes with avg net > +0.20% after costs before promotion.
- **FOREX (−0.12%):** demote from Smart Picks until positive. 46% of closes are SL_HIT with WR 41.5% — widen stops or drop the strategies whose entry trigger produces this profile; the forward tracker (`crypto_rsi5070`-style CI-LB gate) is the right promotion bar to copy.
- **BOND (−0.23%, n=28):** not enough data to trade on — freeze new bond picks until n≥100 closes, then re-measure.
- **COMMODITY (n=7) / FUTURES (n=2):** same freeze; the moneymaker page already presents these honestly, keep that framing until samples are real.
- **SPORTS (n=1–2):** out of scope for the money-ready funnel; keep isolated.

### P4 — Fix the gate flag and Smart Picks funnel

1. `_gate_passed` false on 100% of picks: audit `ml_gatekeeper/gatekeeper.py` wiring — either the gate result never propagates into the emitted pick record, or every class genuinely fails. Either way the flag is currently meaningless.
2. `smart_picks = []`: with crypto at +0.53% avg net over 2,074 closes, the funnel *should* emit something. Trace where Smart Picks filtering diverges from the moneymaker/money-readiness verdicts (which do find crypto+equity admissible).

## 3. Suggested sequencing

1. **Week 1:** P1.1–P1.3 (staleness) + P2.1 (UEPS mark-to-market) — all emitter/resolver-side, no strategy changes, immediately visible on the dashboard.
2. **Week 2:** P4 gate-flag + smart-picks tracing; equity R:R fix.
3. **Week 3+:** forex demotion/stop audit; bond/commodity/futures sample-freeze review against the forward-tracker CI-LB bar.

## 4. Verification hooks (already live)

- `/audit/healthchecks/` — pipeline freshness (21 pipelines, all green as of 2026-10-18).
- `/audit/moneymaker/` — per-class best strategies with honest simulation; crypto banner already says NOT READY.
- `/audit/moneyreadiness/` — gates, walk-forward, bootstrap CI, DSR/PBO/SPA per class.
- `/audit/whopickedthis/?symbol=X` — per-symbol provenance (system, confidence, score, trust).
- `/audit/research/` — top-100 of 893 backtested strategies with PF/WR/Sharpe/MDD/walk-forward folds.

Any pick-pipeline change should be judged by movement in these five pages' numbers, not by the scanner's own logs.

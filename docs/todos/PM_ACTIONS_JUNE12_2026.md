# PM Action Todos — Find Winners Fast (2026-06-12)

Derived from pass-hunter / per-class winner hunt + audit surface review.

## P0 — Stop bleeding (this week)

| ID | Action | Owner surface | Repro / verify |
|----|--------|---------------|----------------|
| P0-1 | **Fix luxalgo SHORT emission** — scanner returns 0 picks; probation sleeve not accruing n | `alpha_engine/june2026_research_candidates.py`, `priority_picks_emitter.py` | `python3 -c "from alpha_engine.june2026_research_candidates import _generate_luxalgo_short_v2; print(len(_generate_luxalgo_short_v2()))"` → must be >0 |
| P0-2 | **Block CRYPTO LONG** at emitter + M-036 extension (not just BUY) | `alpha_engine/config.py`, `emitter_discipline.py` | Intrabar: LONG WR ~34%, PF ~1.02 |
| P0-3 | **Ship hourly intrabar reresolve** in GHA (P0-A plan) | `docs/plans/2026-06-12-P0A-intrabar-hourly-reresolve-plan.md` | Forward lane stalled since 2026-06-10 |
| P0-4 | **Kill fear-greed CRYPTO LONG** from daily 44-pick batch until intrabar proof | `st_fear_greed_contrarian_winner` | Emitter dry-run: 3× CRYPTO LONG @ score 85 |
| P0-5 | **Refresh picks-now track record** — 21.1% WR stale (last gen 2026-06-09, n=19 only) | `tools/picks_now_professional.py`, `picks_now_track_record.json` | Wire valuation screener + intrabar resolver |

## P1 — Measurement honesty (2 weeks)

| ID | Action | Notes |
|----|--------|-------|
| P1-1 | **Symbol×direction FWD WR** on Star tab — not strategy-level WR | `dashboard_generator.py` active picks panel |
| P1-2 | **Tournament MISPRICED_ENTRY quarantine** — gpt4_1 75/117 flagged; don't show 55.6% without excluding | `ai_tournament_leaderboard.json` builder |
| P1-3 | **pick_funnel.html** — keep DISPUTED banner; wire Smart Picks DB ground truth refresh | `pick_funnel_90d.json` hourly |
| P1-4 | **Replay COMMODITY gold_overnight_gap_fade** on intrabar harness (BT T2 proxy only today) | `reports/june2026_strategy_research_2026-06-12.json` |
| P1-5 | **FOREX negative filter live** — block F1=CONTRARIAN (76% loss capture) | `stamp_entry_conditions.py` already tracks |
| P1-6 | **Portfolio history** — confirm stale vs resurrect; books show aggregate -89% compounded EW | `portfolio_history.html`, `dashboard_data.json` |

## P2 — Institutional playbook (4 weeks)

| ID | Action | Reference |
|----|--------|-----------|
| P2-1 | **2 focus classes only** — CRYPTO (luxalgo SHORT) + COMMODITY (gap-fade confirm) | Master loop §2 velocity |
| P2-2 | **Kill 12/16 june2026 v2 emitters** with no intrabar support | `generate_forward_observation_picks()` audit |
| P2-3 | **Monkey test + stress matrix** before any PROBATION→PROVEN | Master loop Addendum B |
| P2-4 | **Growth-stock screener integration** for picks-now | starboi-63/growth-stock-screener pattern |
| P2-5 | **Research index → hypothesis registry** wire-up — stop orphan reports | `research_index.html` |

## Proven today (intrabar deduped)

| Class | Unit | Tier | n | WR | PF |
|-------|------|------|---|-----|-----|
| CRYPTO | luxalgo_confluence SHORT | **PROBATION** | 38 | 71.1% | 2.21 |
| All others | — | **NONE/PROXY** | — | — | — |

**PROVEN (n≥100): 0 / 8 classes**

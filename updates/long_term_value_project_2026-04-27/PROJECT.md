# Project: US Equity Prediction System (UEPS) — Hedge-Fund-Grade

**Initiated:** 2026-04-27 by Claude Opus 4.7
**Owner:** zerounderscore@gmail.com
**Status:** ALL 15 PHASES BUILT — 244/244 tests passing on disk (verified 2026-04-28)
**Bar:** "Picks people can trust their hard-earned money on" — institutional discipline, walk-forward backtests, transparent theses, no flaky data sources as primary deps.

**Aligns with CLAUDE.md MAJOR GOAL #1** (phenomenal performance across ALL asset classes on `/audit`).

## Mandatory standards (locked 2026-04-28)

- **n≥100 floor for "proven" claims** — every stat line MUST cite n=value
- **Tier 2 minimum to size up:** PF > 1.5 AND WR > 50% AND MDD < 20%
- **Tier 1 (long-run):** PF > 2.0 AND WR > 55% AND MDD < 10%
- **No expansion of `BLOCKED_SOURCE_SYSTEMS`** without `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `MUTATION_THREE_AXIS_PROTOCOL.md`
- **Walk-forward only** — no in-sample backtests
- **Transparency on every pick** — fundamental snapshot + thesis + thesis-break rules + earnings/dividend in dashboard

## Coordination with parallel work

This project is purely additive — new pick types, new files in `alpha_engine/`, new dashboard tab. **No file overlap with Copilot's parallel `quality_gates.py` zombie-source purge.**

## Mission

Build a US equity prediction system covering BOTH long-term holds AND swing trades, surfaced on `findtorontoevents.ca/audit/` with full transparency: earnings history, upcoming earnings, dividends, fundamental snapshot, thesis text, exit logic.

## Decisions locked

1. **Horizons:** long-term (1y-3y+) AND swing (1w-1m)
2. **Universe scope:** universal — whatever free APIs cover. US 6,000+ baseline via SEC EDGAR
3. **Resolver:** new `thesis_resolver.py` (long-term, never closes on price) + `swing_resolver.py` (1w-1m)
4. **Tier framework:** see `docs/PERFORMANCE_CHARTER.md` (Phase 12 — done)
5. **Dashboard surface:** full fundamental snapshot, earnings history+upcoming, dividend record, technical state, thesis, IV target, days-held
6. **Data trust hierarchy:**
   - Tier A canonical: SEC EDGAR + FINRA + FRED (public domain)
   - Tier B reliable: issuer ETF CSVs, Finnhub free, Tradier sandbox, Tiingo free
   - Tier C fallback: yfinance with cache
7. **Methodology stack** per Agent E synthesis (see `findings/SYNTHESIS.md`):
   - LONG: Magic Formula × Piotroski quality filter × Acquirer's Multiple × SafetyGate (Altman + Beneish)
   - SHORT: Beneish + Altman Z'' + Sloan ≥ 2-of-3 trigger

## Phases status

| # | Phase | Status |
|---|---|---|
| 0 | Research (5 agents) | ✅ DONE (artifacts in research/) |
| 1 | Findings synthesis | ✅ DONE (`findings/SYNTHESIS.md`) |
| 2 | Schema additions (`long_term_pick_contract.py`) | ✅ DONE (14/14 tests) |
| 3 | `fundamentals_fetcher.py` | ✅ DONE (17/17 tests) |
| 4 | `earnings_calendar_fetcher.py` | 🔄 RECOVERY |
| 5 | `dividend_history_fetcher.py` | 🔄 RECOVERY |
| 6 | `value_screener.py` | 🔄 RECOVERY |
| 7 | `swing_screener.py` | 🔄 RECOVERY |
| 8 | `thesis_resolver.py` | 🔄 RECOVERY |
| 9 | `swing_resolver.py` | 🔄 RECOVERY |
| 10-11 | Dashboard partial + renderer | ✅ DONE (19/19 tests) |
| 12 | `docs/PERFORMANCE_CHARTER.md` | ✅ DONE (233 lines) |
| 13 | `value_backtest.py` walk-forward | ✅ DONE (28/28 tests) |
| 14 | GHA workflows | ✅ DONE (37/37 tests, 4 YAMLs) |
| 15 | SHORT-side detector | 🔄 RECOVERY (was blocked on Phase 2/3/6 prereqs) |

## Project structure

```
updates/long_term_value_project_2026-04-27/
├── PROJECT.md (this file)
├── TODOS.md
├── research/
│   ├── 01_bulk_fundamental_data.md
│   ├── 02_universe_quote_data.md
│   ├── 03_specialty_data.md
│   ├── 04_github_libraries.md (lost in earlier persistence issue; defer)
│   └── 05_methodology_synthesis.md (lost; defer)
└── findings/
    └── SYNTHESIS.md (Phase 1 lock)
```

## Handoff protocol

If this session is interrupted or another agent takes over:

1. Read `PROJECT.md` (this file) for context
2. Read `TODOS.md` for current state
3. Read `findings/SYNTHESIS.md` for locked decisions
4. Resume at the first 🔄 RECOVERY phase

## Critical context for future agents

- **`outcome_resolver.py:384-405` is broken** for non-crypto. Long-term picks must NOT use this resolver. Swing picks need `swing_resolver.py` instead.
- **Existing pick contract** is dict-based (no formal schema). New fields are ADDITIVE.
- **CLAUDE.md wire-up rule** applies: any new module needs a production caller or explicit "opt-in sidecar" labeling with a wiring plan in the PR body.
- **Magic Formula has decayed post-2010**; Piotroski as quality filter is non-negotiable per Agent E synthesis.
- **EDGAR XBRL coverage starts ~2012** — gives 13y backtest window.
- **Persistence bug (2026-04-28):** earlier in this session, the harness reported successful Writes that didn't persist to disk. The recovery plan recreates the missing files. Verify with `ls` after every Write.

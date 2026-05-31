# Strategy Build — TSMOM (Time-Series Momentum)

**Author**: peer_claude
**Date**: 2026-05-31
**Slug**: tsmom
**Build dir**: `/tmp/strategy_builds_2026-05-31/tsmom/`

## Academic basis
Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics* 104(2).
Replicated by Hurst, Ooi & Pedersen (2017) on 137 years of data — Sharpe ~1.0.

## Implementation summary

| Component | File | LOC |
|---|---|---|
| Signal + sizing + cursor gate | `strategy.py` | 244 |
| Paper-pilot harness | `paper_pilot_harness.py` | ~120 |
| Unit tests | `tests.py` | ~95 |
| README + citations | `README.md` | — |

**Universe (9)**: SPY, EFA, EEM, TLT, IEF, GLD, DBC, USO, VNQ.
**Signal**: 12-month total return sign.
**Sizing**: inverse 60-day realized vol, target 10% portfolio vol, gross capped 2×.
**Rebalance**: monthly (close all → recompute → reopen).

## Cursor statistical framework (applied day 1)
- n floor: 500 closed trades
- Bonferroni α-per-test = 0.05/7 = **0.00714**
- WR: Wilson lower bound ≥ 0.50
- PF: bootstrap (2000 resamples, 95% CI) lower bound ≥ 1.20
- Walk-forward: monthly rebalance is inherently OOS; lookback fixed at paper's 12m (no in-sample tuning)

## Tests
9/9 unit tests pass (synthetic 800-day panel across full universe). Harness
smoke-tested across 7 monthly rebalances on synthetic data — opens/closes
positions correctly, persists to JSON sidecar (NOT trading_picks DB).

## Cross-AI refinement — Grok-4.3
Consulted on universe construction. Verbatim response in
`/tmp/strategy_builds_2026-05-31/tsmom/ai_consult_grok.txt`. Highlights:

> (1) **Concentration**: TLT+IEF duplicate US duration; VNQ adds US-rates beta → net ~40%+ US-rates exposure, violating inverse-vol diversification.
> (2) **Gaps vs MOP 2012**: no FX (USD factor), no non-US bonds, narrow commodities (USO+DBC energy-heavy), no inflation-linked.
> (3) **Suggested swaps**: IEF → TIP (real-rate + inflation); USO → UUP/FXE (USD carry).

Documented in README; **not auto-applied** — baseline universe runs first, A/B universe is a follow-up PR after n>=100 trades on baseline.

## Wire-up plan (per CLAUDE.md rule)
**Opt-in sidecar.** Paper-pilot persists to
`audit_dashboard/data/paper_pilots/tsmom/*.json`. Target promotion path:
1. Accumulate n>=500 closed monthly trades (~5 years of 9-asset rebalances ≈ 540 trades).
2. Re-run `passes_cursor_gate()` — if Wilson WR LB ≥ 0.50 AND bootstrap PF LB ≥ 1.20, eligible.
3. Wire into `alpha_engine/smart_picks_engine.py` as a new source_system `tsmom_v1` with concentration cap (per CLAUDE.md HHI<0.30 rule).

## Open follow-ups
- A/B universe variant per Grok feedback (TIP, UUP swaps).
- Hook to real price data (yfinance / parquet cache) for live monthly cron.
- Walk-forward bias-stress: jitter rebalance day ±5 trading days.

## Verification commands
```bash
cd /tmp/strategy_builds_2026-05-31/tsmom
python3 tests.py                                              # 9/9 PASS
TSMOM_PILOT_DIR=/tmp/tsmom_test python3 paper_pilot_harness.py # 7 rebalances
```

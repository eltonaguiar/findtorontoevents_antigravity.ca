# Strategy Build — Connors RSI(2) for EQUITY (2026-05-31)

**Slug:** `connors_rsi2_equity`
**Build dir:** `/tmp/strategy_builds_2026-05-31/connors_rsi2/` (isolated, per wave protocol)
**Author:** peer-claude (build-wave 2026-05-31)
**Goal alignment:** Goal #1 — phenomenal performance across all asset classes on `/audit`.
EQUITY is currently FAIL+INSUFF-N (PF 0.90 / WR 33% / n=33 per `money_ready_verdict.json` 2026-05-24).
Need *more shots on goal with proven-edge strategies* — Connors RSI(2) is one of the most
heavily-replicated equity mean-reversion edges in the literature, ideal first deposit.

## Citation
Connors, L. & Alvarez, C. (2008). *Short-Term Trading Strategies That Work*, ch. 2.
Replications: Pardo 2010 §7; Aronson 2007 ch. 6; Quantpedia screen #46 (OOS 2003–2018).

## Concrete rules (locked)
| Component | Value |
| --------- | ----- |
| RSI | period 2, Wilder smoothing |
| Entry | `RSI(2) < 5` AND `Close > SMA(200)` |
| Exit (any) | `RSI(2) > 70` OR `bars_held == 5` OR `-5 % stop` (intraday low-touch) |
| Side | Long only |
| Universe | 50-name liquid US large-cap subset (bootstrap); full SPY constituents when wired |
| Sizing | Equal-weight, no pyramiding |

## Statistical gate (Cursor framework — applied day 1)
- `MIN_N_FOR_LIVE = 500`
- Wilson 95 % LB on WR > break-even WR (function of realized avg-win / avg-loss)
- Bootstrap 95 % CI on PF, n_boot = 2 000; lower bound must clear **1.20**
- Bonferroni alpha = **0.05 / 7** = 0.00714 (this wave ships 7 strategies)
- Walk-forward 70 / 30: OOS PF ≥ 0.8 × IS PF
- All four checks must PASS — `evaluate_gate()` returns a single `verdict` field

## Files & sizes
| File | Lines | Purpose |
| ---- | ----- | ------- |
| `strategy.py` | 299 | Indicators, signals, backtest, gate evaluator |
| `paper_pilot_harness.py` | 252 | `scan`/`mark`/`status` CLI, atomic JSON state |
| `tests.py` | 114 | 12 unit tests (RSI bounds, signal logic, stats helpers) |
| `README.md` | 50 | Citation + rules + wiring plan |

**Tests:** 12 / 12 passing (`python -m pytest tests.py -q`).

## Isolation
- Harness persists to local `paper_state.json` only — does **not** write to
  `ejaguiar1_stocks.trading_picks` or any audit DB (build-wave isolation rule).
- No edits to the shared working tree's `alpha_engine/` — wiring deferred to phase 2
  per repo "Wire-Up Rule" (a wiring plan section is in `README.md`).
- yfinance is the bootstrap data layer; swappable for the repo's market-data infra
  when promoted.

## Cross-AI refinement (Grok — `grok-4-fast-reasoning`)
Verbatim response (consulted 2026-05-31, asked for top-3 pre-live refinements):

> 1. **Costs**: Embed realistic spreads/commissions/slippage in all PF calcs;
>    retest bootstrap LB>1.20 and WF OOS.
> 2. **Universe**: Switch to point-in-time top-50 by market cap daily;
>    rerun full gate (n, Wilson, Bonferroni) to kill lookahead.
> 3. **Risk**: Add ATR-based position sizing + portfolio heat cap (e.g., 20% gross);
>    re-validate OOS PF and max DD.

**My follow-up actions** (queued for the wiring PR, not this build PR):
1. Add a `costs_bps` parameter (default 5 bp round-trip = 2.5 bp spread + 2.5 bp slip).
   Subtract from `pnl_pct` before any stat is computed.
2. Replace `default_universe()` with a point-in-time SPY-constituents loader
   (we have `alpha_engine/fundamentals_fetcher.py` — extend it for an
   as-of-date members list).
3. Wire to existing portfolio heat cap (audit page already enforces HHI ≤ 0.30
   single-source concentration) — but add a strategy-level cap of 20 % gross.

## Expected performance (book + replications)
WR 65–75 %, PF 1.5–2.0, n ≥ 500 over 1–2 years on a 500-name universe.

## Next steps
1. Run `paper_pilot_harness.py scan` daily (manual or cron) for 4 weeks.
2. After n ≥ 100 closed paper trades, sanity-check WR & PF against book expectations.
3. After n ≥ 500 + gate PASS, open wiring PR per phase-2 plan in `README.md`.
4. Promote to `/audit` Smart Picks only after 4-week live forward-test + concentration check.

## One-line summary
`CONNORS_RSI2:lines=299:tests=12:harness=true:ai_consult=grok`

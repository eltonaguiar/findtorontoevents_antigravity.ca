# FX / Macro / Commodities GitHub Repo Scout — 2026-11-18

**Scope:** G10 FX spot/futures, carry, momentum, macro surprise, central-bank calendar; commodities (energy/metals/ags) term structure, roll yield, COT, ETF flows; FRED/ECB/BIS/DXY; repos with explicit testable strategy logic.

**Context:** Local repo `/home/eaguiar2015/findtorontoevents_antigravity.ca` already contains `funds_db_profile.md` and `STRATEGY_DISCOVERY_REPORT_V3_2026-11-18.md` — no verified FX/macro/commodity edge yet.

**Method:** Direct GitHub API search (live 2026-11-18). Filtered for stars, recency, license, actual data vs plotting, falsifiable edge claim. Ignored noise (blockchain metals, crypto-only, unlicensed, dead).

---

## Ranked Candidates (verified live)

| Rank | Repo | Stars | Last Push | License | What It Does | Verdict | What We Already Have vs What This Adds |
|------|------|-------|-----------|---------|--------------|---------|---------------------------------------|
| 1 | [BenyaminSuicmez/FX_Carry_Trade_Backtest](https://github.com/BenyaminSuicmez/FX_Carry_Trade_Backtest) | 3 | 2026-10-25 | NONE | G10 FX carry decomposition (carry vs FX move) 2015-2025, quantitative backtest | PARTIAL | We lack a carry decomposition harness; this is the only reusable carry logic. Adds: methodology, not code. Stale risk: low. |
| 2 | [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | 9259 | 2026-08-05 | AGPL-3.0 | Mature Python backtest engine (events, positions, fees, slippage) | VIABLE (engine only) | We have no backtest harness. Adds: proven engine. AGPL constraint on product reuse. No edge logic. |
| 3 | [vrd07/Quant_Trading](https://github.com/vrd07/Quant_Trading) | 8 | 2026-11-01 | MIT | 13 regime-gated strategies (gold/FX/crypto) + 16-point validation checklist | PARTIAL | We lack regime-gating pattern. Adds: checklist + regime logic. Unverified, likely overfit. |
| 4 | [quantskills/skill-global-commodity-term-structure](https://github.com/quantskills/skill-global-commodity-term-structure) | 1 | 2026-07-16 | GPL-3.0 | Commodity futures term structure, roll yield, cross-commodity spreads from public data | PARTIAL | We lack commodity term-structure tooling. Adds: public-data pipeline. GPL constraint; too new. |
| 5 | [abishekprabakar/futures-roll-lab](https://github.com/abishekprabakar/futures-roll-lab) | 0 | 2026-09-21 | MIT | Commodity futures roll-yield lab (Schwartz curve, front/deferred/optimum schedules, return decomposition) | DECORATIVE | We lack roll-yield decomposition. Adds: conceptual model only. Immature (0★, 2 months old). |

**Rejected / Stale / Hallucination-prone (flagged):**

- `markbogorad/CarryTrade` (3★, 2025-01-16, MIT): G10 carry + GARCH; needs Bloomberg (we lack it). Stale.
- `YannVladimir/fx-structural-momentum-bot` (11★, 2026-11-04, MIT): EURUSD CRT/structural momentum; ships backtesting data + analysis scripts, but CRT is discretionary and hard to falsify.
- `10mohi6/oanda-backtest-python` (15★, 2022-12-08, MIT): OANDA-specific backtest lib; stale (2022), FX-only, no edge.
- `chaddjohnson/forex-backtesting` (43★, 2016-06-24, NONE): Node.js FX backtester; ancient, unlicensed, dead.
- `EarnForex/*` family: spike-trader, Heiken-Ashi naive; low stars, no verifiable edge, Apache but unmaintained.

---

## Explicit Verdict

**Consistent proven edge for FX/macro/commodities as of 2026-11-18?** NO.

All candidates are either:
- Engines without edge (kernc/backtesting.py)
- Unverified backtest claims (carry decomposition, regime-gating)
- Too new/stale/unlicensed (commodity term structure, roll-yield labs)

Default = unproven. No repo ships a falsifiable, live-forward-verified edge we can adopt.

**Next concrete experiment (cheapest):** Re-run the FX_Carry_Trade_Backtest decomposition on our data using backtesting.py as the harness. G10 spot/futures carry, long top-3 vs short bottom-3, 2015-2025 + OOS 2026. Tests whether carry edge survives outside the author's sample. ~1 day of work. Falsification test, not a winning strategy.

---

*Generated 2026-11-18T17:40Z from live GitHub API. All URLs and metadata verified in this run. No fabricated repos.*
# IPO Lock-Up-Expiry Strategy — First System-Verified Backtest

**Date:** 2026-05-17
**Modules:** `alpha_engine/ipo_data_pipeline.py`, `alpha_engine/ipo_lockup_strategy.py`
**Branch:** `feat/ipo-lockup-pipeline-sidecar`
**Status of strategy:** OPT-IN RESEARCH SIDECAR — not wired into production.
**Goal advanced:** #1 (per-asset-class edge — EQUITY-IPO research sub-class).

## Verdict

**INSUFFICIENT-N + STRATEGY FAILS the §23 5-gate as currently parameterized.**

- n = 23 trades — far below the n≥100 clean-trade gate. The headline numbers are
  **directionally informative but NOT verdict-grade**.
- On the small sample tested, the strategy is **deeply unprofitable**: WR 34.8%,
  PF 0.18, total PnL −164.37%. It does **not** clear Tier 2 (PF>1.5 / WR>50) and
  is nowhere near Tier 1.
- This is the **first system-verified run** of the strategy. The 58–62% WR cited
  in the module docstrings is literature (Field & Hanka 2001) and is **NOT
  reproduced** here. Do not promote `source_system='ipo_pipeline'` to
  `passes_active_gate`.

## Data Source

| Item | Value |
|---|---|
| IPO calendar source | **Manual historical set** (24 real US IPOs, 2019–2024) |
| Why not live Nasdaq | Nasdaq API (`api.nasdaq.com/api/ipo/calendar`) **did NOT 403** — it returned 36 IPOs, but **all were May 2026** (current month only). Lock-ups on May-2026 IPOs expire ~Nov 2026, so there is **zero backtestable post-lock-up price history**. The endpoint is single-month and unusable for a historical backtest. |
| Calendar schema bug found | Nasdaq rows return `ipo_date` as `M/D/YYYY` and carry no `lockup_expiry`; `compute_lockup_expiry` expects ISO `YYYY-MM-DD` and would silently drop them. The manual set is written in correct ISO schema. |
| Price history source | **Yahoo Finance** (`query1.finance.yahoo.com/v8/finance/chart`) — **worked, no 403**. Fetched with `range=5y` (the module's default `1y` was too short to span 2021–2025 lock-up windows). 24/24 symbols fetched, null-close rows dropped. |
| Files written | `alpha_engine/data/ipo_calendar.json` (24 IPOs), `alpha_engine/data/price_cache/<SYM>.json` (24 files), `alpha_engine/data/ipo_backtest_results.json` |

The 24-IPO manual set spans RDDT, ARM, CART, KVYO, BIRK, CAVA, KLC, LINE, TBBB,
ALAB, SOLV, VKTX, AS, SARO, TWFG, OS, RBRK, IBTA, PONY, SMR, GTLB, HOOD, RIVN,
DDOG. All have publicly verifiable IPO dates. SOLV is a 3M spinoff (kept; the
backtest's price/MIN_PRICE filters handle it). DDOG's 2019 lock-up window was
skipped by the price-validity filter (`skipped.filters = 1`) → 23 trades scored.

## Backtest Results (verified)

Command: `python -m alpha_engine.ipo_lockup_strategy --backtest`

Strategy params: SHORT 5 trading days before lock-up expiry, cover 10 days after;
15% stop, 10% take-profit; 2% slippage ×2 + 0.1% commission ×2.

| Metric | Value |
|---|---|
| Total trades (n) | **23** |
| Wins / Losses | 8 / 15 |
| Win rate | **34.8%** |
| Profit factor | **0.18** |
| Total PnL | **−164.37%** (sum of per-trade %) |
| Avg win | +4.42% |
| Avg loss | −13.32% |
| Avg PnL / trade | −7.15% |

### Per-year breakdown

| Year | n | WR | PnL% |
|---|---|---|---|
| 2022 | 4 | 100.0% | +17.93 |
| 2023 | 1 | 0.0% | −19.20 |
| 2024 | 12 | 16.7% | −116.62 |
| 2025 | 6 | 33.3% | −46.48 |

## Interpretation

- **Strong regime dependence.** The only profitable cohort is 2022 (4/4 wins) —
  a bear market where post-lock-up insider selling did produce drops, matching
  the Field & Hanka thesis. In the 2024–2025 IPO bull run, newly-unlocked names
  (RDDT, ALAB, VKTX, TWFG, PONY) **rallied** through the lock-up window and hit
  the 15% short stop-loss. The strategy is effectively short-volatility against
  a strong IPO tape.
- **Loss asymmetry.** Avg loss (−13.3%) is ~3× avg win (+4.4%) because the 15%
  stop fires on the squeeze-ups while the 10% TP rarely fills. With WR 34.8% and
  that payoff ratio, expectancy is sharply negative.
- **Exit-reason mix:** 7 STOP (all losses), 6 TP (all wins), 10 EXPIRY (mostly
  small losses) — the EXPIRY bucket confirms there is no reliable mean drop at
  the lock-up date in the post-2023 sample.

## §23 5-Gate Status

| Gate | Requirement | Result |
|---|---|---|
| n ≥ 100 clean | 100 | **FAIL** — n=23 |
| Win rate | >50% (T2) | **FAIL** — 34.8% |
| Profit factor | >1.5 (T2) | **FAIL** — 0.18 |
| Walk-forward decay ≥ 0 | non-negative | **FAIL** — 2022 +17.9 → 2024 −116.6 → 2025 −46.5 (severe decay) |
| 30-day rolling clean | — | not evaluable at n=23 |

**The strategy must NOT be wired into `passes_active_gate`.** It fails 4/4
evaluable gates. This is the honest outcome of a first real backtest.

## Recommendations / Next Steps

1. **Data:** the n≥100 gate needs a real historical IPO calendar. Nasdaq's API
   is current-month only — use an archival source (SEC EDGAR S-1/424B4 full-text
   search, or a one-time scrape of `stockanalysis.com/ipos/` historical pages)
   to assemble 300+ IPOs from 2015–2024, then re-run.
2. **Strategy:** the SHORT-only thesis is regime-fragile. Before any further
   work, consider (a) a market-regime filter (only short when SPY/IWM is below
   its 200-DMA), or (b) testing the inverse — a LONG bias on post-lock-up
   strength in bull tapes — per the mutate-before-kill protocol.
3. **Schema fix:** `fetch_nasdaq_ipo_calendar()` should normalize `M/D/YYYY` to
   ISO and `fetch_price_data` should accept multi-year ranges; both were
   worked around manually for this run.

## Reproducer

```
git checkout feat/ipo-lockup-pipeline-sidecar
# ipo_calendar.json + price_cache/ are committed alongside this report
python -m alpha_engine.ipo_lockup_strategy --backtest
```

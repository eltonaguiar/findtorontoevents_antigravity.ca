# Freebuff Quant Fund — Core-Satellite Turnaround Plan (2026-10-22)

**The problem, stated honestly.** Across 59 strategies and Feb–Oct 2026 of cleaned picks:
crypto loses −0.46%/trade, stocks +0.25%, ETFs +0.06%, forex break-even, commodities broken.
**Nothing beats simply holding an index.** Max drawdowns look small only because the bots
size tiny — that is not safety, it is irrelevance. This plan is the way to do better, and it
is being implemented now, not just written.

---

## Why we lose — three root causes (not fifty)

1. **We manufactured alpha from toys.** ~1,000 short-horizon technical triggers (RSI/MACD/EMA
   crosses) on a thin, contaminated universe, backtested with no costs, no sizing, and massive
   selection bias. Best case that fits noise — which is why even the best (rs-breakout-scout,
   PF 1.28) trails SPY buy-and-hold.
2. **Wrong time horizon.** Every honest edge in our OWN data lives at months-to-years (trend /
   momentum rotation, relative-strength breakouts, mutual-fund factor tilts). Everything losing
   lives at 40-minute scalps. We built the losing side.
3. **The machine can't tell skill from luck.** No trial ledger, 20 broken DSR functions (>1 =
   impossible), no costs/sizing, a corrupt scoreboard (frozen-exit, batch-close, 0.00% flats,
   look-ahead rows — all being fixed in PR #756 + follow-ups). Until fixed, every "winner" is
   "best of 1,000 lottery tickets."

---

## The way — core-satellite, harvesting premiums that actually exist

Stop trying to out-clever the market. Build the "variety-pack mutual fund" the user described:
a **boring, disciplined core** plus a **small, honest satellite** of forward-sealed candidates.

### CORE (~75%) — the actual product
Monthly multi-factor trend/momentum rotation across broad ETFs + institutional-consensus
large caps. This is what the existing tactical-rotation sleeve (Sharpe 0.88 vs SPY 0.74), the
mutual-fund ranker (T1=SWPPX), and the fund-holdings deriver (MU/NVDA/AAPL/MSFT/…) already
point at. Goal is **beat-or-efficiently-harvest** the index with discipline — not magic alpha.
Two boring institutional rules, tested honestly in `tools/core_satellite_backtest.py`:
- **Dual-momentum rotation** (top-N by 6-month return, negative-momentum → AGG), monthly.
- **SPY 200-day trend filter** (in SPY above the 200d, else AGG) — cut losses, ride trends.

### SATELLITE (~25%) — the hope, paper-only
The only two candidates with real structure, **forward-sealed** until PROVEN-FORWARD:
- **CRYPTO SHORT @ 1h RSI 30–50** — clears all ten outputs retrospectively (PF 2.16, random-entry
  null 99.8th pct, β≈0). Scalp/intraday; needs a fresh sealed forward sample (M-107).
- **rs-breakout-scout** (daily stocks/ETFs relative strength) — PF 1.28 on 8.8y re-backtest;
  trails SPY today but is the cleanest equity lead. Seal forward to n≥100.

### MACHINE (the fix that stops the churn)
- One `audit/gates.yaml` as the single source of truth (all agents import it).
- A trial ledger (`trials.csv`) so DSR/CPCV can count every idea tried.
- Costs + position sizing modeled everywhere (round-trip: crypto 30bp, equity 10bp, FX 3bp).
- Sealed forward cohorts (GHCOPILOT #752 format): rules hashed, append-only, no re-tuning.
- Labels only MONEY-READY / CANDIDATE / FAIL. Kills need operator approval.

---

## Phased plan

**Days 1–30 (truth):**
1. Merge PR #756 (DSR + resolver fixes); re-run the funnel; expect mass CANDIDATE→FAIL (correct).
2. Stand up `gates.yaml` + `trials.csv`. Back-fill the ~1,021 leaderboard strategies as trials.
3. Seal forward cohorts for the core (dual-momentum + 200d trend) and the 2 satellites.
4. Publish the honest core-vs-SPY backtest result on the Buffy page (this is the honesty test).

**Days 31–60 (forward):** collect ≥30 days / ≥50 forward trades per sleeve; weekly scorecard;
GHCOPILOT independently replicates each. Demote if forward PF < 1.0 after 30 trades.

**Days 61–90 (decide):** ≥60 days + ≥50 forward trades → full scorecard. If a sleeve scores
100 → operator review for a tiny real-money pilot (≤1% capital/sleeve, n≥500 before scaling).
**If none pass, that's the answer:** stay paper, keep the core as a disciplined index-tilt
product, and move effort to the fund rater — do NOT keep spawning toy strategies.

---

## What "do better" honestly means
For a public-facing product, the defensible claim is a **disciplined, low-cost, transparent
ETF-rotation core** (which can reasonably match or modestly beat a passive index on risk-adjusted
return, and demonstrably controls drawdown), **not** a high-frequency alpha machine. The satellites
are optionality, sized tiny, and only graduate on sealed forward proof. Everything on the current
/audit page that looks better than this was a bug; the fixes are landing.

*NFA. Research plan only. All backtests net of assumed costs, next-bar/next-month entry.*

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*

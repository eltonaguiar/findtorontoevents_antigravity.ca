# $2,000 allocation and a live short-term trading simulation — plan

**Date:** 2026-11-19
**Inputs:** live `/audit3` ledger 18:32:40Z, `/audit2` forward clock, `docs/WHAT_WORKS_PER_ASSET_CLASS_2026-11-19.md`.
**Constraint:** $2,000. No leverage. No personalised advice — this is an engineering/risk plan.

---

## 1. The direct answer

**If forced to one asset class: ETFs.** Not because ETFs have the best theoretical edge —
futures trend-following does — but because $2,000 can actually *express* the ETF strategy
without being destroyed by minimums, margin, or roll costs, and it is the only class where we
have a backtest we can attempt to replicate.

| Candidate | Best evidence | Can $2k express it? | Verdict |
|---|---|---|---|
| **ETFs** | Top-3 sector rotation PF 2.05 / Sharpe 0.97 / MDD 16.1% (2015–2026), cost-robust | **Yes** — fractional shares, no leverage, ~1 bp spread, monthly turnover | **Pick** |
| Futures | TSMOM: 58 contracts, 25+ years, positive for every contract (Grade A) | No — contract minimums and a diversified basket need far more capital | Paper only |
| Equities | 12-1 momentum/value/quality (Grade A) | Partly — single names at $2k concentrate risk; no PDT headroom | Small sleeve |
| Mutual funds | Fee arithmetic only | Yes, but it is beta, not edge | Core only |
| Crypto | Momentum/funding carry (B); our class is **KILL** | Yes, but intraday friction is fatal at $2k (§2) | Paper sandbox |
| Bonds / commodities / FX | Carry (A−) but our data is thin/proxy | Poorly at $2k | Not now |

**Within ETFs: a 70/20/10 split**, not all-in on the rotation signal, because the rotation
backtest is Grade C until it survives PBO/DSR and a forward clock.

---

## 2. Why day trading with $2,000 is structurally hostile (the arithmetic)

This is the most important number in the plan. Fixed costs do not scale down with capital.

| Venue | Round-trip cost | Cost per $2k trade | 3 trades/day × 20 days | Monthly drag |
|---|---|---:|---:|---:|
| Crypto perp (taker 0.05% ×2 + ~0.05% slip) | ~0.15% | ~$3.00 | 60 trades | **~$180 = 9.0%** |
| US equities (commission-free, spread ~2 bp) | ~0.04% | ~$0.80 | 60 trades | ~$48 = 2.4% (plus PDT rule) |
| FX micro (1 pip ≈ 0.01%) | ~0.02% | ~$0.40 | 60 trades | ~$24 = 1.2% (leverage risk) |
| ETF rotation (monthly, 0–1 leg change) | ~0.02% | ~$0.40 | ~2 trades/mo | **~$0.80 = 0.04%** |

A day-trading strategy on $2,000 must beat **9%/month gross** in crypto just to break even.
That is why the honest answer is: **day trading is a paper-only research activity at this
size**, and real money belongs in low-turnover sleeves. Also note the US **PDT rule**: a
margin account under $25,000 is limited to 3 day trades per 5 days.

---

## 3. The allocation

| Sleeve | Capital | Instrument | Why | Kill rule |
|---|---:|---|---|---|
| **Core beta** | $1,400 (70%) | One broad, low-cost index ETF (e.g. total US market) | Removes the need to be right; the only guaranteed-positive-expectancy exposure after fees | none (rebalance only) |
| **Rotation** | $400 (20%) | Top-3 long-only sector ETFs, monthly, vol-scaled | The only in-house backtest with a plausible edge and low turnover | −15% or 3 negative months |
| **Sandbox** | $200 (10%) | **Paper only** — crypto/forex intraday | Learn and measure without paying the 9%/month friction | never funded until gates pass |

**Hard rules:** ≤2% account risk per position; no leverage; no averaging down; every change
logged before it is made; a sleeve that hits its kill rule is frozen, not "adjusted".

If the rotation sleeve proves itself forward, it can grow from $400 toward $1,000 by
rebalancing from core — never by adding new money.

---

## 4. Live simulation architecture (paper → micro-live)

The repo already has the components; they are simply not wired into one loop.

```
signal emitters ──► paper broker (fees+slippage) ──► trade ledger ──► daily reconciliation
      │                     │                            │                    │
      │                     │                            │                    └─► weekly review
      │                     │                            └─► forward_observations.jsonl
      │                     └─► fill model: spread + 1 bar delay + partial fills
      └─► pre-registration file per sleeve (rules, universe, params, kill criteria)
```

**Five parallel sleeves, one clock, isolated capital:**

1. `core-beta` — buy-and-hold index (control for "did the system beat beta?").
2. `etf-rotation` — monthly top-3, vol-scaled.
3. `equity-breakout` — `POD-EQUITY-BREAKOUT` (8 cells already registered).
4. `futures-tsmom` — paper only, the Grade-A effect, to measure it in our own data.
5. `crypto-intraday-sandbox` — paper only; the friction experiment.

**Controls that make it science, not a hobby:**

- **Every sleeve gets a random-entry control arm** on the same universe and holding period.
  If the sleeve cannot beat its own random arm, it has no signal.
- **Pre-register before running.** A sleeve's `strategy.yaml` (universe, entry, exit, size,
  costs, kill rule) is committed *before* the first trade. Changes are new versions, never edits.
- **Same-entry A/B.** Overlays (RVOL ≥ 1.5, vol targeting, TP/SL variants) are evaluated on the
  *same entries* with a paired bootstrap — one hypothesis each, never a 96-config grid.
- **Daily reconciliation.** Paper PnL vs the ledger vs the live price source; any unexplained
  gap >$1 is an incident.

**Monitoring cadence already available:** `audit3-ledger` every 6h, `db-freshness-guardian`
hourly, the new forward-ingest every 6h. Add one daily summary job that posts to COMS:
sleeve → n, net, CI, drawdown, gate status, and "no change" when nothing moved.

**Graduation to real money (all must hold):**
n ≥ 200 forward rows · net CI lower bound > 0 at 2× cost · DSR ≥ 0.95 · no symbol > 60% of
trades · 3 consecutive months of live paper with reconciliation clean · beats its random arm.

**Kill criteria:** −15% drawdown, 3 consecutive negative months, or any gate regression. A
killed sleeve is frozen with a written post-mortem, not quietly restarted.

---

## 5. 30 / 60 / 90-day plan

**Days 0–30 — make the clock real**
1. Register `POD-EQUITY-BREAKOUT` and `futures-tsmom` in the forward ingest (blocking todo).
2. Stand up `core-beta` and `etf-rotation` in paper with the fill model.
3. Add the random-entry arm for each.
4. Daily COMS summary job.

**Days 31–60 — measure**
5. Run the vol-targeting A/B and the RVOL overlay on the same entries.
6. Require PBO/DSR on the ETF rotation backtest before any live dollar.
7. Crypto intraday sandbox starts measuring the friction gap explicitly (cost per trade vs
   gross alpha per trade).

**Days 61–90 — decide**
8. Any sleeve that clears graduation gets a micro-live allocation drawn from core (not new money).
9. Any sleeve that fails is frozen with a post-mortem.
10. If nothing clears, the correct output is "no deployable edge on available data" — a
    successful result, and the $2,000 stays in core beta.

---

## 6. What would make me change the allocation

- Rotation sleeve forward n≥200 with net CI > 0 at 2× cost → raise it to $1,000.
- Futures TSMOM confirms on our data (paper n≥200) → it becomes the second live sleeve, but
  only once capital supports a 3–5 contract basket.
- Crypto intraday shows gross alpha consistently > 2× round-trip cost (i.e. >0.3%/trade at
  0.15% cost) for 200 paper trades → reconsider a $200 live sandbox.

*Not investment advice. The only guaranteed-positive component above is the low-cost index
core; everything else is a pre-registered experiment.*

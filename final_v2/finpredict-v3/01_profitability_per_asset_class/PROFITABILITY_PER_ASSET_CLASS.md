# Profitability per Asset Class — reality + how to get there (final_v2)

Synthesis of the 2026-11-14 audit with a forward-looking "how to become profitable per
class" plan. Honest verdict first: no class is proven money-ready today. Below each
class's verified current state and the minimum set of changes that would give it a real
chance.

## Global gate (applies to every class)

Implement the horizon harness as the **release gate**: a strategy is "profitable" only
when all of these hold on realized trades:
1. n≥60 (report n≥30 separately), 2. 95% binomial CI on WR excludes 50% on the
   profitable side, 3. PF>1.05 and positive mean per-trade PnL, 4. win-majority in
   ≥66% of walk-forward windows, 5. multiple-testing-adjust (report # tested vs # passed),
   6. capital-adjusted (not just notional) — a high Sharpe on a tiny notional is not an
   equity-beating edge.

---

## CRYPTO
- **Current:** largest closed n (4,907 intrabar) but WR 35.9% / PF 0.92 (anti-skill);
  most active_raw rows are EXPIRED zombies (86.7%); frozen `current_price==entry` on
  24/7 symbols; entry=0.0 garbage rows.
- **Ideas to get profitable:**
  1. Ship the **time-series momentum/trend** (ITERATION-005: net-of-cost Sharpe 2.13,
     t=5.56, OOS 2.06→2.33). Execute as diversified vol-targeted, long-only/flat with
     20% vol target; it beats B&H on drawdown (maxDD −17% vs −36%) and in bears. Gap:
     restate vs **buy-and-hold** benchmark (it currently under-returns B&H in bull);
     add survivorship-adjusted universe; add execution/taker-cost stress.
  2. Ship **funding/carry** as a small sleeve (DSR 1.0, but capital-intensive; only
     BTC clears cash at 1.5× capital). Cap at 10–15% of book.
  3. Fix the price-freshness pipeline first (universal_price_enricher wired into the
     build) — no PnL claim is trustworthy until `current_price` is live and
     `UNQUOTED` replaces fabricated 0%.
- **Profit path:** trend (core) + funding (sleeve) + DataFrame-level hygiene gate.

## EQUITY / STOCKS
- **Current:** headline WR 59.2% but unprofitable (PF 0.94); fundamental/earnings
  modules have zero/failed realized evidence (goldmine n=270 PF 0.42 −4.6%).
- **Ideas to get profitable:**
  1. Build a **real fundamental factor** (Piotroski F-score / quality / value) with a
     monthly walk-forward — the current modules are not wired to any realized result.
  2. Use a **market-neutral long/short** construction to remove beta so the edge is
     measured vs zero, not vs B&H.
  3. Only then add the PEAD/earnings-drift sleeve (post-earnings drift is a documented
     premium) with a data source that actually feeds it.

## ETF
- **Current:** best PF>1 class (n=15 PF 1.836) but fails Bonferroni; rs-breakout-scout
  n=78 WR 57.7% CI_lo 46.6% (fails CI).
- **Ideas to get profitable:**
  1. **Multi-asset trend** on ETFs (the natural extension of ITERATION-005) — broad
     diversified trend is the most robust documented premium; run it across 20–50
     liquid ETFs (equity/credit/commodity/FX) with a risk-parity weight.
  2. Add **SMA timing overlays** (already signal-adjacent) but measure against a
     risk-matched benchmark (not just B&H).
  3. Raise n by using lower-frequency rebalances but longer history (10+ yr) — the
     current n=15 is far too small.

## BOND / FIXED INCOME
- **Current:** n=3 closed (insufficient); most seeds null-price; class effectively
  inactive; `INSUFFICIENT_DATA`.
- **Ideas to get profitable:**
  1. **Carry + duration tilt** is the realistic bond premium (term premium), not a
     point-in-time signal. Build a long-horizon carry-check (via FRED data, which
     exists as a module).
  2. Fix data: backfill `current_price` (yfinance/FRED) or stop emitting unquoted
     seeds; keep class gated until n≥30 closed.
  3. Hug the **NOT_BUILT** honesty label until a real feed exists.

## FOREX
- **Current:** WR 32.2% / PF 0.66 (anti-skill); 105–277 date-only entry_time; 11
  frozen phantoms; batch-identical closed_at.
- **Ideas to get profitable:**
  1. **Carry** is the documented FX premium (interest differential), but it needs a
     real carry/funding feed and a capital model — not the current spot-flicker rows.
  2. Fix date-only timestamps and purge/quarantine phantoms first; a WR of 32% on
     garbage rows proves nothing either way.
  3. Consider **vol-targeted trend on FX majors** (the same trend playbook extends to
     FX) with a long history.

## FUTURES / COMMODITY
- **Current:** no real feed; commodity signals derived from crypto proxies; both
  classes in BLOCKED_ASSET_CLASSES; date-only seeds; FUTURES 10/13 old.
- **Ideas to get profitable:**
  1. The **trend risk premium is the canonical commodity/futures edge** (CTA playbook);
     the natural move is to run the vol-targeted trend across futures with real front-
     month data, not crypto proxies.
  2. Until a real feed exists, keep FUTURES/COMMODITY **blocked** (do NOT unblock with
     placeholder data). A genuine futures data source is a prerequisite.
  3. Design the **roll/expiry handling** (back-adjusted continuous contracts) as part of
     the harness before any PnL is trusted.

## MUTUAL FUNDS
- **Current:** unbuilt (no ranker/site; stub scanner vetoed; monthly NAV has no
  intraday mark).
- **Decision:** do NOT build a live MF pick class. Keep `NOT_BUILT`. If desired, use
  MF data only for long-horizon asset-allocation/carry research, never as an intraday
  signal.

## Cross-class wrap
The single highest-value next step is **one portfolio of 3 strategies** rather than more
signals:
- CRYPTO vol-targeted trend (core)
- ETF multi-asset trend (diversifier, next to build)
- BTC funding/carry sleeve (low-vol return)
All run behind the horizon-harness gate, with capital/execution checks, and all PnL
recomputed on the LIVE price feed (fix freshness first).

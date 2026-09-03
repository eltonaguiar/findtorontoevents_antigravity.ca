# Money-Ready Winner Hunt — 4-Agent Fleet + Intrabar Verification (2026-06-13)

**Question (operator):** "Find REAL money-ready winners — deploy research subagents."
**Method:** a 4-angle read-only research fleet + two new intrabar tools, every claim run
through a placebo/beta control, ISO-week distribution check, net-of-cost, and an honest
IS/OOS split. Goal #1 (audit performance across asset classes).

**Bottom line:** After the most rigorous, placebo/benchmark-controlled, multi-angle sweep this
project has run, **0 cohorts pass a clean Tier-2 money-ready bar, and every apparent winner —
including the one that clears the statistical bar — decomposes into market beta.** The leading
candidate, `cta_replicator` × COMMODITY × SHORT (ex-CL=F): net PF 2.43, WR 61%, n=1222, looked
promising on its headline stats but **failed the decisive selection-alpha test**: benchmarked
against the same-symbol-same-week average of *all* commodity shorts, cta's median excess is
**−0.01%** and it beats the benchmark only **49%** of the time, and its edge lives entirely in
the falling-commodity window (IS half net PF 1.06 break-even → OOS 4.53). It is the
*falling-commodity regime*, not cta's signal. **There is no genuine, regime-controlled
money-ready edge in the current book in any asset class.** The honest path forward is emitter-side
(reachable TPs) + new orthogonal inputs, not further mining.

---

## The unifying insight

**Every apparent SHORT "edge" in late-May/early-June 2026 is the same risk-off beta artifact,
seen independently in three asset classes:**
- CRYPTO: `battleground_luxalgo` net PF 2.0 — 71% of picks in 2 weeks during a **−16% BTC move**.
- EQUITY/ETF: `regime_terminal` SHORT net PF 2.2 — 90% in ISO weeks 22–23, buy&hold-short over the
  same windows = PF 4.42 / +3.7% **with no TP/SL skill**.
- COMMODITY: all-source commodity SHORT net PF 1.29 vs LONG 0.80 — broad falling-commodity tilt.

When you short a market that is falling, you make money. That is beta, not a repeatable signal.
The tell is always the same: **picks cluster in one fortnight, and a time-matched random-entry
placebo (or buy&hold over the same window) does as well or better.**

---

## Per-class verdicts (all evidence from live queries / intrabar replay run this session)

### CRYPTO — NO EDGE (Agent A; intrabar replay on `crypto_ohlcv`, net 10bp, dedup + placebo)
- 12 sources swept; every one fails Tier-2.
- Apparent winner `battleground_luxalgo` (net PF 2.0, beat its own placebo p=0.00) is a **beta
  artifact**: it is a curated 11% slice of `luxalgo_confluence`, whose **full** universe (n=1490)
  nets **PF 0.91**; 71% of picks in 2 weeks during a −16% BTC drop; SHORT-heavy. Isolating the
  full strategy to that window nets only 1.14.
- Closest near-miss `copy_trader_intel` net PF 1.21 but n=64<100, OOS WR 38%, placebo p=0.28.

### EQUITY / ETF — NO ALPHA (Agent B + this session's intrabar tools)
- **SHORT-is-beta: CONFIRMED.** The TP3/SL2 SHORT cohort (net PF 2.21, n=51) fails the decisive
  **same-day regime-matched placebo**: real drops to PF 0.95 while random shorting the *same days*
  scores 1.36. (An *uncontrolled* placebo — random entry across all 3 months — wrongly "passed"
  at p≈0 because it leaks into up-weeks. This was a real methodology trap I initially fell into;
  see "Honest notes".)
- **LONG entries chase tops:** hourly MFE median **+0.5%** vs MAE **−3.8%** — entered near local
  highs. Original take-profits were reached only **11–24%** of the time (the reachability disease).
- **Cross-sectional reversal (long losers / short winners) is NOT an edge:** market-neutral
  long-short nets **negative** (net PF 0.92 close-to-close, 0.72 intraday, both IS and OOS halves).
  Losers do bounce (LONG-loser leg +0.24%/day, Sharpe 1.82) but winners persist (SHORT-winner leg
  −0.31%/day), so reversal cancels; the long-loser gain is mostly beta (β +0.29, market-neutral
  alpha negative). **This empirically refutes the literature "reversal" idea on our data.**
- An oversold-contrarian LONG *looked* strong (PF 2.08) but is a **same-bar look-ahead artifact**;
  under honest next-bar entry it collapses to PF 1.10 (≈beta, placebo p=0.80).

### COMMODITY — leading candidate, REFUTED as beta on deeper test (Agent C flagged it; this session refuted it)
- `cta_replicator` × COMMODITY × SHORT, strict-dedup n=1473, decisive WR 57%, net PF 1.31.
- **Drop the already-killed CL=F (crude, −1.11% avg bleed) → net PF 2.43, WR 61%, n=1222.**
  CL=F was independently retired earlier (3.8% WR), so excluding it is policy, not post-hoc fishing.
- Structurally clean (0 null timestamps, 11–12 ISO weeks spread, diversified across 5 positive
  futures, symbol HHI 0.15) — which is why it survived where the equity/crypto fortnight artifacts
  did not. So I ran two decisive controls:
  1. **IS/OOS by date halves:** IS (Mar27–Apr14) net PF **1.06 (break-even)**; OOS (Apr14–Jun01)
     net PF **4.53**. The edge exists *only* in the later, falling-commodity window — not stable.
  2. **Selection-alpha (the commodity analog of a placebo):** cta short minus the same-symbol-week
     average of *all* commodity shorts (ex-CL=F) → mean excess **+0.04%, median −0.01%, beats the
     benchmark only 49%** of the time. vs *non-cta* shorts the mean is +0.14% but median ~0 /
     52% hit (outlier-driven, not consistent).
- **Verdict: BETA, not skill.** The net PF 2.43 is the falling-commodity regime (all-source
  commodity SHORT nets 1.29 vs LONG 0.80); cta adds **no reliable selection skill** on top of it.
  Not money-ready. (Can't be intrabar-verified anyway — no commodity OHLCV in the DB.)

### Other classes
- FOREX: prior sessions established net-of-cost death (consensus gross 1.79 → net 0.62; sub-1bp
  execution needed). Unchanged.
- The whole pick-book story remains: **the bottleneck is reachability + measurement, not strategy
  supply.** 0/6 classes Tier-2.

---

## Deliverables (reusable, this session)

| File | What it does |
|------|--------------|
| `tools/equity_reachability_replay.py` | Hourly-`stock_ohlcv` intrabar replay: realized MFE/MAE, original-TP reachability, TP/SL grid with IS/OOS split, net-of-cost. SL-first conservative first-touch. **`--entry-next-bar` guard** added after a look-ahead bug was found (fill at the next bar for trigger-based signals). `--self-test` passes. |
| `tools/equity_reversal_backtest.py` | Cross-sectional long-short reversal backtest on `stock_ohlcv`; **market-neutral by construction = built-in beta control**; per-leg breakdown, IS/OOS, SPY beta regression. `--self-test` passes. |

**Method contributions worth reusing project-wide:**
1. **Placebo control is mandatory** — and it must be **time-matched** (same-day or same-window),
   not spread across the whole sample. An uncontrolled placebo leaks regime and produces false
   positives.
2. **ISO-week distribution check** — if >60% of resolved picks fall in <3 weeks, a top-line PF is
   a single-regime artifact; median-cut IS/OOS proves nothing.
3. **Next-bar entry for trigger signals** — replaying from the trigger bar counts its own intrabar
   range as reachable (look-ahead). Always fill at the next bar.
4. **MFE/MAE reachability prescription** — equity hourly favorable move is median ~0.8% / p75 ~1.9%;
   any take-profit ≥3% in a 1-day hold is structurally unreachable.

---

## Honest notes (process)

- My first EQUITY SHORT "money-ready ✅" (OOS PF 2.34) was **wrong** — caught by my own red-team
  (time-concentration + beta control) and confirmed by Agent B's same-day placebo. My follow-up
  "time-matched" placebo was itself **flawed** (the window spanned the full 3 months, not the dense
  fortnight, so it just reproduced the uncontrolled result). Agent B's **same-day** control is the
  correct test and is what the verdict rests on.
- The look-ahead bug in `equity_reachability_replay.py` was found by Agent B and fixed here; with
  the fix the SHORT cohort drops to net PF 1.55 / OOS 1.45 — fails the gate anyway (and is beta).
- No production behavior changed. All work read-only on the DB; isolated worktree off origin/main.

## Options / greeks as a new input (operator request — assessed this session)

Could options/greeks help our predictions? **Partly — as a defensive gate, not a new alpha source —
and this ground is already heavily worked here.**
- **Already refuted:** `tools/options_flow_research.py` + `reports/options_flow_research_2026-05-18.md`
  walk-forward-KILLED put/call ratio, IV-skew (^SKEW), and VIX term structure on real free CBOE+Yahoo
  data (137–155 windows; eff sign ~50/50; ~43% cost survival; "8th straight harness kill"). VRP/short-vol
  is REFUTED (11-axis critique; `refuted/vrp-...` branch). Crypto options signals are *already wired*
  into the scanner (`alpha_engine/options_signals.py` Deribit; `crypto_options_vol.py`).
  `alpha_engine/features/options_features.py` is a realized-vol *proxy*, not real chains.
- **Data feasibility (live-tested this session):** our four paid keys — FINNHUB, FMP, ALPHAVANTAGE,
  TIINGO — return **ZERO options data** (paywalled / dead / premium-only / no options product). The only
  usable feeds are **free CBOE delayed quotes** (full equity/ETF chains *with* per-strike greeks +
  `iv30`, but **no free history**) and **free Deribit** (crypto `mark_iv`/skew + DVOL IV-index history,
  the one place with backtestable history). So **every equity options signal is forward-collect-only.**
- **Best use:** an **opt-in IV/skew GATE** (not a strategy) on existing equity/ETF longs — e.g. suppress
  or down-size a new long when `iv30` is bottom-decile (vol-expansion risk) AND 25-delta skew is in the
  crash zone. MVP: `alpha_engine/options_iv_gate.py` Phase 0 forward-collects a daily CBOE snapshot table
  for our ~214 symbols (flag OFF, no behavior change); Phase 1 wires `passes_iv_gate()` after ≥40–60 days
  and is kept only if the gated-long cohort beats the ungated cohort on net-of-cost PF across ≥3
  consecutive 14-day walk-forward windows (reuse `tools/edge_stability_harness.py`). Given 8 prior harness
  kills, treat the base rate as "probably won't clear" — but the collector is cheap and the downside is
  bounded. **Not a paid-data purchase, not VRP-shaped.**

## Recommended next action

1. **Stop mining the current book for directional alpha** — it is exhausted across all 6 classes;
   every apparent winner is regime beta. The remaining levers are (a) emitter-side **reachable TPs**
   (size to the measured MFE, median ~0.8% / p75 ~1.9% for equity hourly) and (b) genuinely
   **orthogonal new inputs**.
2. **If building one new input, build the opt-in CBOE IV/skew gate sidecar** (forward-collect first) —
   the only options angle not already refuted, and framed honestly as a *risk filter*, not alpha.
3. **Do not size up anything on regime-window numbers** — require a forward window spanning a *different*
   regime + a same-period benchmark/placebo control (the test that just killed both the equity SHORT and
   the cta commodity SHORT).

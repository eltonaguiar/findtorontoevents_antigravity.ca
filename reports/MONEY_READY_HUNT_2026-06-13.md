# Money-Ready Winner Hunt — 4-Agent Fleet + Intrabar Verification (2026-06-13)

**Question (operator):** "Find REAL money-ready winners — deploy research subagents."
**Method:** a 4-angle read-only research fleet + two new intrabar tools, every claim run
through a placebo/beta control, ISO-week distribution check, net-of-cost, and an honest
IS/OOS split. Goal #1 (audit performance across asset classes).

**Bottom line:** After the most rigorous, placebo-controlled, multi-angle sweep this project
has run, **0 cohorts pass a clean Tier-2 money-ready bar.** Every top-line "winner" decomposes
into one of: **market beta (a risk-off move), single-fortnight concentration, same-bar
look-ahead, or cost.** The single survivor that clears the *statistical* T2 bar net-of-cost is
**`cta_replicator` × COMMODITY × SHORT (ex-CL=F): net PF 2.43, WR 61%, n=1222** — but it rides a
falling-commodity regime (beta tailwind) and cannot be intrabar-verified (no commodity OHLCV in
the DB). It is the **best forward-pilot candidate, not a confirmed winner.**

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

### COMMODITY — CLOSEST LEAD, beta-caveated (Agent C + this session's verification)
- `cta_replicator` × COMMODITY × SHORT, strict-dedup n=1473, decisive WR 57%, net PF 1.31.
- **Drop the already-killed CL=F (crude, −1.11% avg bleed) → net PF 2.43, WR 61%, n=1222.**
  CL=F was independently retired earlier (3.8% WR), so excluding it is policy, not post-hoc fishing.
- Clean structurally: **0 null timestamps, 12 ISO weeks spread (top-3wk = 53%, not a fortnight),
  diversified across 5 positive futures** (gold/soy/natgas/corn/wheat), symbol HHI 0.15, and OOS
  **strengthens** (IS 1.07 → OOS 1.86 per the registry sweep).
- **Caveat (beta):** all-source commodity SHORT nets 1.29 vs LONG 0.80 → there is a
  falling-commodity tailwind. But cta's ex-crude **2.43 ≫ 1.29 generic short**, so cta has genuine
  selection skill *on top of* the beta. It cannot be intrabar-verified (no commodity OHLCV) and
  rides one regime. **Verdict: strongest candidate; needs a forward window in a non-falling
  commodity regime before sizing.**

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

## Recommended next action

1. **Forward paper-pilot `cta_replicator` COMMODITY SHORT (ex-CL=F)** as an opt-in sidecar (no
   production change), headline **net-of-cost** PF, and gate acceptance on a forward window that
   includes a non-falling commodity stretch + a same-period long/short beta check. This is the only
   candidate with a credible statistical case.
2. **Stop mining the current book for directional alpha** — it is exhausted; the remaining lever is
   emitter-side (reachable TPs) + new orthogonal signal inputs.
3. **Options/greeks as a new input** (operator request, assessed separately) — most promising as a
   *gate/sizer* on existing equity picks, forward-collected first (no historical chains in the DB).

# Options-Flow Signal Research — STRAND B — H-013 — 2026-05-18

_Generated 2026-05-18T04:16:00+00:00 by `tools/options_flow_research.py`._
_Real-data cache built 2026-05-18T04:11:03+00:00 (`tools/cache/options_flow_cboe_cache.json`)._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module has no caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. It reads real options data and writes this report — nothing else.

## Mandate

After 7 straight harness kills (`reports/EDGE_HUNT_CONCLUSION_2026-05-18.md`) the in-house + academically-grounded candidate queue is empty — price/volume technicals, COT, funding rate, futures term structure and earnings surprise are all exhausted. STRAND B pursues the strategic-fork Option 1: a **genuinely new input class**. The system has never ingested options-derived data. H-013 was pre-registered in `reports/hypothesis_registry.json` (M-107) BEFORE any backtest logic.

## Data — REAL, options-market-only (no proxies, no synthetic)

- **Put/call ratio:** CBOE daily market-statistics (cdn.cboe.com/data/us/options/market_statistics). 1602 real trading-day rows of exchange options volume.
- **Volatility indices:** Yahoo chart API - CBOE volatility indices ^VIX/^VIX9D/^VIX3M/^SKEW + 11-ETF tradeable basket. `^SKEW` is computed by CBOE from out-of-the-money SPX option prices; the `^VIX` family is the SPX option implied-volatility surface. These are options data, not price.
- **Tradeable book:** the 11-ETF liquid US-equity basket (SPY, QQQ, IWM, DIA, XLF, XLK, XLE, XLY, XLV, XLI, XLP). The CBOE put/call / SKEW / VIX signals are market-wide, so the same daily z is applied to every ETF — a continuous-position book.
- **No synthetic / random-walk generator anywhere in the module.** Every record traces to a real CBOE/Yahoo observation.

## Method (identical leakage controls for all three sub-signals)

1. Compute the signal z-score from REAL data using ONLY strictly-past observations (rolling 60-day window).
2. Build a CONTINUOUS-POSITION BOOK: for **every** signal date (NO |z| threshold) and **every** ETF in the basket, emit one resolved pick — the FULL signal series, NOT a self-selected subset of trades the signal liked (H3). This is the H-008-redesign pattern: ~11 ETFs x ~1400 days gives the 14-day harness windows real density without lowering any harness threshold or shrinking any window.
3. Entry is the first ETF bar STRICTLY AFTER the signal date — no look-ahead. Forward return over a fixed 5-day hold.
4. Round-trip cost (6bp — conservative retail SPY: half-spread + slippage, both legs) subtracted from every forward return BEFORE WON/LOST resolution.
5. Purged + embargoed walk-forward (5-day embargo, 14-day blocks).
6. **Verdict gate:** the full record series is fed through `tools/edge_stability_harness.is_admissible()` — imported UNMODIFIED. ADMISSIBLE iff |eff| >= 0.3, same sign, >= 3 of the scored 14-day windows.
7. **Cost gate (H4):** net edge must retain >= 60% of gross. BOTH the harness AND the cost gate must pass to call a sub-signal an edge.

**A gaudy in-sample win rate is NOT a pass.** Base rate after 7 kills is poor.

## Sub-signal A — put/call volume ratio — [KILL]

- **Signal:** CBOE TOTAL put/call ratio (real exchange options volume) — 60-day rolling z-score; extreme high put/call (crowded fear) -> contrarian LONG the ETF basket (mean-reversion).
- **Data source:** CBOE daily market-statistics put/call ratios (1602 input trading days)
- **Continuous-position book:** 11 ETFs x signal days -> **16896** resolved records (full series, every ETF-day, no |z| threshold)
- **Gross (pre-cost):** WR 49.3%, mean signed return +0.016%

### Purged + embargoed walk-forward
- OOS sample: n=16896 (every signal event), pooled post-cost WR 49.2%, embargo 5d
- 156 walk-forward 14-day blocks tiled across the timeline

### Harness verdict (THE gate — eff per window)
- per-window eff (new->old): `-0.10 +0.29 +0.58 -0.45 +0.02 +0.22 +0.54 -0.31 -0.04 +0.94 +0.17 -0.53 -1.30 +0.57 +0.03 +0.07 -0.38 -0.06 -0.42 -0.33 +0.33 -0.41 -0.25 +0.71 -0.37 +0.81 -0.57 +0.34 +0.91 -0.58 +0.06 +0.02 -0.28 +0.16 +0.52 -0.17 -0.15 -0.36 +1.08 +0.36 -0.40 +0.46 +0.30 +0.63 -0.68 n/a -0.20 +0.42 +0.04 -0.52 -0.29 +0.99 +0.38 +0.38 -0.59 -0.43 +0.43 +0.05 -0.29 -0.55 -0.29 +0.61 -0.89 -0.68 -1.05 -0.91 -0.16 +0.41 -0.71 +0.47 +0.97 +0.52 -0.14 -0.22 +0.13 +0.20 -0.04 -0.16 +0.13 -0.29 +0.42 +0.71 +0.57 -0.09 +0.32 +0.46 +0.74 +0.60 +0.23 -0.47 -0.09 -0.13 -0.68 -0.60 -0.04 -0.74 -0.21 +0.59 -0.41 +0.03 +1.23 -0.21 +0.78 +1.00 -0.07 -1.35 +0.42 -0.41 +0.82 -0.27 -0.93 +0.07 -0.95 -0.39 -0.55 +0.39 -0.00 +0.06 +0.24 +0.48 -0.34 -0.12 +0.12 +0.16 -0.71 +0.69 +0.16 +0.19 -0.22 +0.25 +0.72 -0.03 -0.55 +0.93 -0.10 +0.04 -0.39 +0.69 +0.08 -0.06 -0.21 +0.06 -0.47 +0.88 +0.35 +0.40 +0.47 +0.23 +0.51 +0.29 -1.03 +0.25 -0.03 -0.42 +0.94 -0.35`
- windows strong: 92/155 scored  (+50/-42)
- harness: **REJECTED** — REJECTED — strong in 92 windows but signs split (50+/42-); needs 3 same-sign

### Post-cost survival gate (H4)
- gross edge +0.016% -> net edge +0.007% per trade (6bp round trip)
- **cost survival: 43.4%** of gross (>= 60% required) — FAIL

### Classification: TESTED — harness rendered a verdict and REJECTED the signal (eff unstable)

**Verdict: KILL (harness)**

## Sub-signal B — IV skew (CBOE SKEW Index) — [KILL]

- **Signal:** CBOE SKEW Index — built from OUT-OF-THE-MONEY SPX option prices, the standard tail-/25-delta-skew measure. 60-day rolling z-score; expensive tail skew (crowded crash hedging) -> contrarian LONG the ETF basket.
- **Data source:** CBOE SKEW Index ^SKEW (Yahoo chart API) (1467 input trading days)
- **Continuous-position book:** 11 ETFs x signal days -> **15411** resolved records (full series, every ETF-day, no |z| threshold)
- **Gross (pre-cost):** WR 49.9%, mean signed return -0.043%

### Purged + embargoed walk-forward
- OOS sample: n=15411 (every signal event), pooled post-cost WR 49.9%, embargo 5d
- 150 walk-forward 14-day blocks tiled across the timeline

### Harness verdict (THE gate — eff per window)
- per-window eff (new->old): `-0.01 +0.35 -0.30 +0.51 -0.44 -0.74 +0.38 +0.13 -0.36 -1.31 +0.68 +0.96 +0.45 -0.15 -0.29 -0.34 -0.58 +0.66 +0.60 -0.20 +0.12 +0.70 +1.05 +0.93 -0.28 -0.09 -0.00 +0.63 -0.95 -1.16 -0.64 +0.02 -0.16 -0.36 +0.31 -0.49 +0.59 -0.85 +0.92 -0.19 -0.68 -0.26 -0.22 +0.24 +0.02 +0.85 +0.53 +0.47 -0.01 -0.35 n/a -0.65 +0.15 -0.09 -0.05 +0.05 +0.53 -0.06 +0.27 -0.46 +0.66 +0.04 -0.61 -1.20 -1.23 +0.30 +0.40 -0.91 -0.39 -0.02 +0.45 +0.31 n/a +0.32 -0.15 -0.54 -0.62 -0.33 +0.09 -0.97 +0.63 -0.67 +0.31 -0.67 -0.56 +0.64 +0.18 +0.07 +1.41 -0.65 +1.34 -0.59 n/a -0.30 -0.13 +0.41 +0.80 -0.26 -1.40 +1.33 +0.27 -0.38 -0.37 -0.13 n/a -1.26 -0.12 n/a -0.54 -0.56 +0.21 -0.07 -0.24 +0.53 n/a -0.67 +0.57 +0.14 +0.02 -0.51 -0.67 +0.17 -0.63 +0.17 +0.88 -0.26 -0.27 -0.09 n/a -0.30 -0.00 -0.27 -0.22 -0.12 -0.45 +0.29 +0.04 +1.12 -0.72 +1.43 -1.38 -1.53 +0.47 +1.35`
- windows strong: 84/137 scored  (+39/-45)
- harness: **REJECTED** — REJECTED — strong in 84 windows but signs split (39+/45-); needs 3 same-sign

### Post-cost survival gate (H4)
- gross edge is non-positive — nothing for costs to survive; the signal has no pre-cost edge either

### Classification: TESTED — harness rendered a verdict and REJECTED the signal (eff unstable)

**Verdict: KILL (harness)**

## Sub-signal C — VIX term-structure slope — [KILL]

- **Signal:** VIX9D/VIX3M implied-vol term-structure slope — the SPX option IV surface. 60-day rolling z-score; extreme inverted/low slope (vol-spike fear) -> contrarian LONG the ETF basket.
- **Data source:** CBOE ^VIX9D / ^VIX3M implied-vol indices (Yahoo) (1507 input trading days)
- **Continuous-position book:** 11 ETFs x signal days -> **15851** resolved records (full series, every ETF-day, no |z| threshold)
- **Gross (pre-cost):** WR 49.2%, mean signed return +0.013%

### Purged + embargoed walk-forward
- OOS sample: n=15851 (every signal event), pooled post-cost WR 49.1%, embargo 5d
- 150 walk-forward 14-day blocks tiled across the timeline

### Harness verdict (THE gate — eff per window)
- per-window eff (new->old): `+0.14 +0.18 +0.17 -0.36 -0.22 +0.16 -0.04 -0.25 -0.00 +0.88 +0.10 +0.52 +0.55 +0.45 +0.54 +0.10 -0.14 +0.25 -0.17 +0.35 -0.60 +0.04 +0.25 +0.81 -0.61 +0.89 -0.66 -0.88 +1.26 +0.22 -0.11 -0.75 +0.52 +0.23 +0.48 -0.57 +0.34 +0.01 -0.14 +0.96 -0.03 -0.43 +0.19 +0.76 +0.18 +1.20 -0.33 -0.28 +0.46 -0.66 +0.01 +0.64 +0.83 +0.03 +0.13 -0.42 -0.55 +0.89 +0.15 +0.86 -0.03 +0.77 -0.35 -0.49 -0.11 +1.10 +0.74 +0.78 -0.64 -0.41 +1.15 -0.41 +0.23 -0.27 -0.33 -0.52 -0.04 -0.34 -0.28 +0.66 +0.57 -1.30 -0.15 -0.31 +0.40 +0.76 -0.37 -0.01 +0.04 -0.62 -0.08 -0.55 +0.00 -0.55 -0.38 -1.10 +0.81 +0.05 +0.02 -0.26 +0.47 +0.20 +0.01 +0.15 -0.24 -0.45 +0.38 +1.13 +0.12 -0.55 -1.02 +1.06 -0.34 +0.49 +0.04 +0.53 -0.75 +0.40 +0.30 +0.50 +0.64 -0.71 +0.86 +0.23 +0.14 +0.40 -0.11 +0.95 -0.39 -0.39 +0.41 -0.07 -0.17 +0.10 +0.41 +0.28 -0.45 +0.13 +0.53 +0.13 +0.10 +0.47 -0.91 +0.73 +1.23 +0.19 n/a +0.73 -0.25`
- windows strong: 87/148 scored  (+49/-38)
- harness: **REJECTED** — REJECTED — strong in 87 windows but signs split (49+/38-); needs 3 same-sign

### Post-cost survival gate (H4)
- gross edge +0.013% -> net edge +0.006% per trade (6bp round trip)
- **cost survival: 42.6%** of gross (>= 60% required) — FAIL

### Classification: TESTED — harness rendered a verdict and REJECTED the signal (eff unstable)

**Verdict: KILL (harness)**

## Dealer-gamma proxy (DOCUMENTATION ONLY — EXCLUDED from the verdict)

A dealer-gamma-exposure (GEX) proxy was computed from a single LIVE CBOE SPY option-chain snapshot. It is **deliberately excluded from the harness verdict**: there is no free historical option-chain open-interest archive, so a gamma TIME SERIES cannot be built, so it cannot be walk-forward tested. Reporting a snapshot as a passing options signal would be exactly the H2 proxy violation this module refuses to commit.

- snapshot: SPY spot ~739.17, 9711 contracts with open interest
- GEX proxy: -136654774454622.8 (negative (dealers net short gamma))
- SNAPSHOT proxy — gamma approximated by an ATM kernel (true gamma not in the free feed). NOT harness-tested: no free historical option-chain OI series exists to build a time series. Documentation only.

A future paid feed with historical chain OI (Polygon options, ORATS, CBOE DataShop) would make a real dealer-gamma signal harness-testable — that is the honest next step for the gamma leg, not a free proxy.

## Honest conclusion

**0 of 3 options sub-signals cleared the gate.** 3 were cleanly TESTED (the harness rendered an eff-stability verdict on 137-155 walk-forward windows each) and REJECTED all of them; 0 were UNTESTED for data. Each sub-signal is strong in 84-92 windows but the eff sign splits roughly 50/50 (50+/42-, 39+/45-, 49+/38-) — none reaches the same-sign stability the harness requires. The post-cost gate fails independently too: net edge keeps only ~43% of gross, and pooled post-cost win rate is 49.1-49.9% (coin-flip) on all three. The options-implied input class — put/call volume, IV skew, VIX term structure — shows the *identical* failure mode as the prior 7 kills: in-sample separation that does not hold a stable sign out-of-sample. This is an 8th straight harness kill. A genuinely NEW input class did not break the pattern — and that is itself an informative result: it is consistent with the EDGE_HUNT_CONCLUSION read that retail-latency/retail-cost edge is genuinely scarce, not merely un-found. The honest options-flow follow-up is not another free-data backtest — it is a paid historical option-chain-OI feed (for a true dealer-gamma signal), which is an operator data-spend decision. Per the EDGE_VERDICT standing rule the paper-only posture remains in force; nothing here is wired or sized.

Per-window eff is reported above for every tested sub-signal so the verdict is independently auditable.

## Exact harness construction (auditable — H3)

So the verdict cannot be a pass-by-construction artifact, the exact harness wiring is:

- **Records = the FULL signal series.** For each sub-signal, a resolved pick is emitted for *every* signal date that has a valid strictly-past rolling z-score, times *every* ETF in the basket. There is NO |z| threshold and NO filtering to trades the signal 'liked' — winners and losers enter the record set on identical terms. A self-selected subset would make the harness pass trivially; this is the opposite.
- **Direction is fixed by the signal, before the outcome is known.** Contrarian: z>0 -> LONG, z<0 -> SHORT. `signal_z` on each record is the conviction magnitude |z|. The harness measures whether winners carry higher |z| than losers, same sign, window after window.
- **`is_admissible()` / `evaluate()` are imported UNMODIFIED** from `tools/edge_stability_harness.py`. The harness `_load` is patched ONLY to return this run's record list instead of `closed_picks.json`; `_windows`, `_window_eff` and the eff thresholds (EFF_MIN=0.3, MIN_WINDOW_N=80, MIN_STABLE_WINDOWS=3) are used verbatim. Nothing is loosened, wrapped or reimplemented.
- **Walk-forward is out-of-sample by tiling.** The harness buckets records into consecutive 14-day windows; each window's eff is computed only from records dated inside it. No window sees another window's data. A 5-day purge/embargo separates train/test bands.

## Reproducibility (H5)

- **Re-run command:** `python tools/options_flow_research.py` (reads the committed cache; add `--refresh-cache` to re-fetch all real data from CBOE + Yahoo).
- **Real-data cache:** `tools/cache/options_flow_cboe_cache.json` is committed — the verdict re-runs offline, no network needed.
- **Machine-readable output:** `reports/options_flow_harness_output_2026-05-18.json` carries the per-window eff arrays + cost-gate numbers for independent re-check.
- **Network-free unit tests:** `python tools/test_options_flow_research.py` exercises the signal math, the cost gate, the continuous-book construction and the unmodified-harness wiring.

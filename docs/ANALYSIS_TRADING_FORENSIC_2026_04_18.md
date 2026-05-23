# Trading Forensic Analysis — 2026-04-18

**Data source:** `alpha_engine/data/closed_picks.json` (4,391 rows; sha as of commit `1b680d2bf5`). Raw stats: [analysis_plots/forensic_stats.json](analysis_plots/forensic_stats.json).

## TL;DR — three structurally-broken behaviors costing real money

1. **MATIC/POL rebrand bug** — 889 closed picks (not 103 as first reported), every one a −0.15% loss, bleeding ~$435/day at $10k/pick. Root cause is a dead Binance ticker still in `alpha_engine/config.py:98`. One-symbol only.
2. **LONG is the bleeder, not SHORT.** 90d crypto: LONG WR 28.3% avg −0.161%; SHORT WR 56.8% avg **+0.102%**. The v1 playbook's SHORT ban was the exact wrong call. True asymmetry is in `quan_engine_scalp` SHORTs' exit geometry: avg winner +0.27% vs avg loser −0.58% → needs 68.2% WR, realized 63.3%.
3. **`quan_engine` has "cut winners, ride losers" anti-pattern.** Pearson r(hold_h, pnl) = −0.133, p ≪ 0.001, n=4,273. Losers held 43% longer than winners. Entries look fine; **realized exits are broken.**

## 1. MATIC auto-loss — forensic

### The expanded scope
Prior analysis said `quan_engine_scalp × MATICUSDT × LONG` = 103 closed picks, all at −0.15%. Recount with broader filter (`source_system='quan_engine'`, `strategy=None`, `direction='BUY'`) returns **889 rows** — the original count missed 786 rows where direction was written as `BUY` not `LONG`, or `strategy` was null.

### The deterministic pattern
- **All 889 picks have `entry_price == exit_price == 0.3794`** — one distinct price across 31 calendar days
- **All 889 exit via `exit_reason=TIME_EXIT`**
- **Every single pnl_pct is −0.15%** (no variance; stdev < 0.05)
- The −0.15% matches the round-trip fee + slippage constant at `alpha_engine/backtest/costs.py:55` (10 bps slippage + fees)

### Root cause
**MATICUSDT was rebranded to POLUSDT on Binance.** The repo itself documents this at `alpha_engine/config.py:331-332`. The scanner at `alpha_engine/config.py:98` still hits the dead ticker, gets a stale 0.3794 response forever, opens a "trade," and the clock runs out at TIME_EXIT — which bleeds exactly the 0.15% fee constant on every close.

### Bleed estimate
At ~29 closed picks/day × $10k notional × −0.15% = **~$435/day, or ~$159k/year in pure fee waste.** Even at the actual sizing of $50/trade, that's still **~$2/day of fees burning on dead signal.** The worst part: these 889 "trades" are in our closed_picks statistics, dragging every aggregate — source-system WR, LONG WR, and quan_engine's realized edge calculation.

### Fix
- Swap `MATICUSDT` → `POLUSDT` in `alpha_engine/config.py:98`
- Purge the 889 dead-ticker rows from `closed_picks.json` OR tag them with `rebrand_artifact: true` so the WR/PnL aggregates no longer include them
- Add a pre-scan guard: if `(entry_price - latest_price) / latest_price == 0` for N consecutive scans, flag the symbol as DEAD_TICKER and skip

### Scan for silent copycats
Filter: `(strategy, symbol, direction)` with `stdev(pnl_pct) < 0.05` AND `n ≥ 20`. **Only MATIC hits this pattern.** No other symbols show the deterministic-loss fingerprint.

## 2. LONG vs SHORT — the real direction picture

Last 90 days crypto (USDT), direction field (resolved):

| Side | n | WR | avg PnL% | Wilson 95% LB |
|---|---|---|---|---|
| **LONG** | 4,296 | **28.3%** | **−0.161%** | 27.0% |
| **SHORT** | 95 | **56.8%** | **+0.102%** | 46.9% |

SHORT is positive EV at the aggregate. LONG is deeply negative. **The v1 playbook banning SHORTs was precisely backwards.** The retraction's "tilt SHORT" was right; V3's concern that SHORTs "win more often but bleed money" was based on a different slicing (probably the 889-strong MATIC LONG corruption pulling down the LONG side, not a real SHORT bleed).

### SHORT bleed is localized — not systemic
The SHORTs that DO bleed cluster in two strategies:
- **`quan_engine_scalp` SHORT**: avg winner +0.27% / avg loser −0.58%. Breakeven WR = 68.2% (losses 2.15× wider than wins). Realized WR = 63.3%. **Structurally losing despite 63% hit rate** due to tight-TP / wide-SL geometry.
- **`macd_crossover` SHORT** (n=14): breakeven 70% / realized 78.6%. Marginal — sample too small to rule either way.

**Action for SHORTs:** don't ban them, fix the exit geometry. TPs 2.1× further out OR SLs 2× tighter to equalize win/loss magnitude.

## 3. `quan_engine` exit-logic bug — the big structural fix

### The pattern
- Pearson correlation of `hold_hours` vs `pnl_pct` (quan_engine, n=4,273) = **−0.133, t≈8.76, p ≪ 0.001**
- Winners avg hold: 5.48h
- Losers avg hold: **7.84h** (held 43% longer)

### The interpretation
Classic "cut winners, ride losers" anti-pattern. Entries look fine (W/L magnitude ratio = 1.64 is healthy), but realized WR (29.4%) is well below breakeven (37.9%) — meaning **exits are the bleed source, not entries.**

### TIME_EXIT dominance
A high share of losing picks close via `TIME_EXIT`, not SL. This means price didn't move — the clock ran out, and the position closed at whatever the spread gave it. Combined with the MATIC pattern, this suggests a systemic "picks sit until timer expires" failure, not a price-action-driven exit.

### The healthy counter-example — `rapid_fire`
`rapid_fire` source_system shows the opposite (correct) hold pattern:
- Winners avg hold: 3.31h (run)
- Losers avg hold: **0.92h** (cut fast)

This is the template. `quan_engine`'s exit logic should be rebuilt against this.

### Recommended fix
Two possible paths:
- **(A)** Port `rapid_fire`'s exit logic into `quan_engine` — trailing-stop after 1R gain, aggressive cut at 0.5R loss
- **(B)** Add a time-decay rule: if a position isn't at +0.5R within 2 hours, close flat (not at TIME_EXIT fees)

(B) alone would save most of the bleed on MATIC-pattern picks across all quan_engine symbols.

## 4. Concentration risk

- `quan_engine` = **97.4% of all closed crypto volume** (4,276 of 4,391 picks)
- `MATIC` alone = **20.3% of volume** (889 of 4,391)

Once the MATIC bug is fixed and data is purged, quan_engine's realized edge should jump by several percentage points purely from removing the noise. Any "edge" calculation currently includes ~890 deterministic losses that shouldn't be in the sample.

## 5. Schema hygiene — code smell found

Direction field uses mixed vocabulary: `BUY / SELL / LONG / SHORT` across different write paths. This caused the initial 103 vs 889 miscount and will cause every future direction-filtered analysis to miss rows unless a filter normalizes all four values.

**Recommended**: normalize at write time. A schema migration over `closed_picks.json` mapping `BUY→LONG, SELL→SHORT` would fix this permanently. Or at minimum, every analysis script should normalize before filtering.

## 6. Action items ranked by $ impact

| # | Action | Est. bleed stopped | Effort |
|---|---|---|---|
| 1 | **Fix MATIC/POL rebrand** in `alpha_engine/config.py:98` + purge/tag 889 rows | ~$435/day at $10k size; data-hygiene for every aggregate | 30 min |
| 2 | **Normalize direction vocabulary** (BUY/SELL → LONG/SHORT migration) | Indirect — fixes analysis accuracy for all future audits | 2 hours |
| 3 | **Port `rapid_fire` exit logic into `quan_engine`** | Unknown $ but likely material — 97% of volume | 1 day |
| 4 | **Re-geometry `quan_engine_scalp` SHORT exits** (TP 2.1× further) | Turns 63% WR structurally-losing strategy into breakeven+ | 2 hours |
| 5 | **Add dead-ticker guard** (stdev + no-movement detector) | Prevents next rebrand incident | 1 hour |

## Methodology

All analysis ran against `alpha_engine/data/closed_picks.json` (4,391 rows) parsed with Python / pandas. Direction filter normalized `BUY/LONG → LONG` and `SELL/SHORT → SHORT`. All statistical tests use Wilson 95% CI for WR bounds, Pearson correlation for hold-vs-pnl, independent-samples t-test for breakeven-WR vs realized-WR significance.

**Companion files:** [analysis_plots/forensic_stats.json](analysis_plots/forensic_stats.json) contains the raw per-strategy / per-symbol / per-direction tables used here.

**Related commits:** `1b680d2bf5` (V3 playbook), `c3531ae8e2` (retraction), `64e3c48587` (regime+cooldown gates).

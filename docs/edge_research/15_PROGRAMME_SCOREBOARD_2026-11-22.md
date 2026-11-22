# 15 — Programme Scoreboard: what was tested, what it returned, what the verdict is

**Date:** 2026-11-22
**Programme item:** 28 (synthesis only — no new backtest was run for this document)
**Sources read for this document:** eight JSON reports under `reports/` plus
[`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md).
Every number below was re-read from its JSON, not recalled. Where a report and the
task brief disagree, the disagreement is stated and the JSON value is quoted.

---

## 1. Header statement

**Nine strategies were tested. One survived (MARGINAL). Seven were killed. One was
blocked on data.**

> **Nothing cleared the hurdle.**

The one survivor is marginal against the US 3-month T-bill (4.32%), not against zero,
and it is the single verdict the survivorship audit flags as unsafe. So "nothing
cleared the hurdle" is the supported reading, and "one survived" must always be said
with the words *marginal* and *unsafe* attached.

---

## 2. The scoreboard

Cost basis is attached to every PF. `n` and the per-row notes are below the table.

| Strategy | Asset class | Source file | n trades / periods | Cost basis of reported PF | PF | Net return per trade (or CAGR) | Sharpe (vs rf where stated) | Skew | Max DD | Random-null percentile | Excess vs SPY (95% CI) | Verdict | Decisive number |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FX momentum (63d/21d) | FX | not in the N1 JSON (see §3 note and §8); documented in [`block4_n1_low_turnover.md`](docs/edge_research/block4_n1_low_turnover.md:17) from round 21 | n = 4,092 (per doc §113) | cost basis **not stated** for a PF (no PF reported) | n/a (none reported) | mean net **−36.88 bp**/trade | not stated | not stated | not stated | **0.0th** percentile (per doc) | not stated | **KILL** | mean net −36.88 bp, both legs negative, gross itself −26.88 bp |
| FX mean-reversion (5d/5d, R22) | FX | not in the N1 JSON; documented in [`block2_r22_fx_meanrev.md`](docs/edge_research/block2_r22_fx_meanrev.md:5) | n not stated in doc header read | 10 bp round trip (per doc) | n/a (none reported) | gross **+4.30 bp**, net **−5.70 bp**/position | not stated | not stated | not stated | gross at **100th** percentile of null (per doc) | not stated | **KILL** | 4.3 bp gross edge vs 10 bp round trip; CI low on net −8.25 bp |
| Equity breakout (donchian / VT pattern sweep) | US equity | [`pod_equity_breakout_backtest.json`](reports/pod_equity_breakout/pod_equity_breakout_backtest.json), [`breakout_cost_sweep.json`](reports/pod_equity_breakout/breakout_cost_sweep.json) | 1,935 trades (sweep); 1,941 (published-cost run) | **25 bp/side** (stated, the correct label) | **0.9917 @ 25bp/side** (JSON) | net −0.0168%/trade @25bp | −0.024 (25bp, ann) | not stated | not stated | not stated | not stated | **KILL** (measured PF ≈ 1.00 vs published 1.479) | break-even **24.5945 bp/side**; PF 1.2206 @ 5bp/side (net +0.3919%/trade, t = 3.52); PF 1.2865 @ 0bp |
| Funding carry (delta-neutral perp) | Crypto | [`funding_carry_20261122.json`](reports/funding_carry_20261122.json), [`funding_carry_20261122_2x.json`](reports/funding_carry_20261122_2x.json) | 5 symbols (always-on by hold period); 214 episodes (BTC) | **pair round trip 45.524 bp @1x, 91.048 bp @2x** (stated) | n/a (PF not reported) | net APR: −158.07% (1d), −47.82% (3d), −15.60% (7d), −3.73% (14d), **+2.42% (30d)**, +6.24% (90d) | −61.23 (1d), +0.555 (30d), +0.740 (90d) | not stated | −1077.4% (1d), −24.19% (30d), −17.11% (90d) | not stated | not stated | **MARGINAL** (survivor; survivorship audit: UNSAFE) | gross +7.93% APR vs pair cost 45.5 bp; break-even hold ≈16.4d (median) vs median episode 2.33d |
| FX carry | FX | [`fx_carry_20261122.json`](reports/fx_carry_20261122.json) | 95 months, 11 currencies | cost sweep 0–10 bp/month (stated); **PF not reported** | n/a (no PF) | CAGR **+3.38%** (gross) | **−0.126** vs rf (4.32%) | −0.63 | −11.71% | **98.2** | −3.04% [−8.28%, +2.29%] | **KILL** | Sharpe −0.126 vs rf; vol 7.43%; worst month −7.55%; break-even 468.5 bp |
| Cross-venue basis | Crypto | [`cross_venue_basis_20261122.json`](reports/cross_venue_basis_20261122.json) | 720 minutes, 3-way overlap | threshold is cost-derived: Binance↔KuCoin 40.48 bp (stated) | n/a (no PF) | n/a | n/a | −0.087 (Binance↔KuCoin) | n/a | n/a | n/a | **KILL** | Binance↔KuCoin median **−0.2427 bp** vs 40.48 bp threshold; **0.00%** of minutes above threshold (all 3 pairs) |
| Commodity term-structure carry | Commodity futures | [`commodity_carry_20261122.json`](reports/commodity_carry_20261122.json) | n/a | n/a (cost UNMEASURED) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **BLOCKED_DATA** | zero second-month contract series on disk; roll yield cannot be computed from one front-month series |
| 12-1 momentum (long/short) | Multi-asset (79 sym) | [`momentum_12_1_20261122.json`](reports/momentum_12_1_20261122.json) | 48 monthly rebalances | **5 bp/side base, 15 bp/side stress** (stated) | n/a (PF not reported) | CAGR **−25.45%** (L/S base) | **−0.70** vs rf | −1.52 | −82.35% | **1.6** | −42.09% [−72.6%, −0.003%] (CI from doc) | **KILL** (L/S) | CAGR −25.45%, maxDD −82.3%, null pct 1.6. Long-only +12.12% vs SPY 16.64%, null pct 41.4, excess −4.5% (CI spans zero); ex-crypto +2.08%, null pct 85.4 |
| Crypto intraday mean-reversion | Crypto | [`crypto_meanrev_intraday_20261122.json`](reports/crypto_meanrev_intraday_20261122.json) | 5,400 trades, 4h bars, 10 symbols | **20 bp base; 0 bp gross row** (stated) | **0.691 @20bp; 0.815 @0bp** | net **−0.4473%**/trade @20bp | −2.55 (ann) | +0.47 | −92.09% | **0.0** | −50.23% [−72.37%, −30.37%] | **KILL** | break-even cost **0 bp**; PF 0.815 even at zero cost; all 10 symbols negative |

### Measured cost (context row, not a strategy)

[`cost_measurement_20261122.json`](reports/cost_measurement_20261122.json):
taker fee **10 bp/side** (Binance, BinanceUS, KuCoin) and **26 bp/side** (Kraken).
Top-of-book half spread for BTC/USDT is **0.00082 bp** (Binance) and 0.0082 bp
(KuCoin) — i.e. the **spread is negligible; the taker fee dominates**. All-in round
trip is therefore **~20.0 bp** on a 10 bp/side venue and **~52.0 bp** on Kraken.
ADA/USDT round-trip spread walks from 6.86 bp at $1k to **988.79 bp at $1M**.
**Equity cost is now MEASURED as an upper bound** (M1, 2026-11-22): from 1-minute bars
(2026-11-16..20), the round-trip spread bound is **12.07 bp** (median 1-min high-low over
the 13-name breakout universe), Corwin-Schultz point estimate **1.50 bp**, so per-side
cost used for re-costing is **6.04 bp** - well below the pod's assumed 25 bp. Top-of-book
NBBO was `BLOCKED_NO_LIVE_NBBO` (Sunday, market closed) and commission is
`COMMISSION_UNKNOWN` ([`equity_cost_20261122.json`](reports/equity_cost_measurement/equity_cost_20261122.json)).
**FX cost is now MEASURED but Sunday-reopen (upper
bound)**: USD-major median-of-medians **7.533 bp** round trip, all-pairs median
**7.99 bp** ([`FOREX_COST_20261122.md`](reports/cost_measurement_forex/FOREX_COST_20261122.md)).
A representative weekday measurement is **scheduled** (`.github/workflows/fx-cost-overlap.yml`,
London/NY overlap 13:00-16:00 UTC) and pending.

### Hurdle (context row)

[`07_HURDLE_RATES_2026-11-22.md`](docs/edge_research/07_HURDLE_RATES_2026-11-22.md):
US 3-month T-bill **4.32%** (2026-11-20); beating SPY needs Sharpe **1.114**; SPY on the
79-symbol panel window measured **Sharpe 0.351** (CAGR 10.42%, vol 17.39%).

---

## 3. Cost-basis audit column

For every row: did the source state a cost basis for its PF, did I trace one, or is it unknown?

| Strategy | PF reported? | Cost basis status | Detail |
|---|---|---|---|
| FX momentum | no PF | **(b) traced** | cost basis not printed with a PF because no PF exists; round-21 result is a mean-bp return. Its cost assumption is not in the N1 JSON. |
| FX mean-reversion | no PF | **(b) traced** | doc states 10 bp round trip used. |
| Equity breakout | yes | **(a) stated** | sweep labels each row by `cost_bp_per_side`; 25 bp/side run is explicit. |
| Funding carry | no PF | **(b) traced** | no PF; costs are explicit (`pair_round_trip_bp`). |
| FX carry | no PF | **(b) traced** | cost sweep 0–10 bp/month explicit; no PF computed. |
| Cross-venue basis | no PF | **(b) traced** | threshold is built from measured round-trip cost. |
| Commodity carry | no PF | **(c) UNKNOWN** | cost `UNMEASURED`; test not runnable. |
| 12-1 momentum | no PF | **(a) stated** | `cost_bp_side` 5.0 / 15.0 per variant; no PF computed. |
| Crypto intraday mean-rev | yes | **(a) stated** | `pf` sits beside `cost_sweep` keys `0bp`…`60bp`. |

**Counts:** (a) stated cost basis = **3** (equity breakout, 12-1 momentum, crypto
intraday mean-rev). (b) traced by me = **5** (FX momentum, FX mean-reversion, funding
carry, FX carry, cross-venue basis). (c) `COST_BASIS_UNKNOWN` = **1** (commodity carry).

**Quotable PFs with a known cost basis: 2** of the 2 PFs that exist at all (equity
breakout 0.9917 @25bp/side and crypto mean-rev 0.691 @20bp / 0.815 @0bp).
`COST_BASIS_UNKNOWN` PFs: **0** (commodity carry produced no PF). A
`COST_BASIS_UNKNOWN` PF would not be quotable; none exists here, but the commodity
row has no number at all, which is equally unquotable.

---

## 4. The break-even ledger (the transferable part)

| Strategy | Break-even point | Where it comes from |
|---|---|---|
| Equity breakout | **24.5945 bp/side** (23.91 bp/side pre-2021 out-of-sample) | `break_even_bp_per_side.all_history` in the sweep JSON |
| Funding carry | **≈16.40 days** at the median funding rate (14.56 d at the mean); empirical first hold with positive net = 30 d | `aggregate_mean_breakeven_days_at_median`; `breakeven` per symbol |
| FX carry | **468.5 bp** of cost | `breakeven_cost_bp` |
| Crypto intraday mean-rev | **0 bp** (never profitable, even at zero cost) | `breakeven_cost_bp = 0.0`; PF 0.815 @0bp |
| Cross-venue basis | **never met** (0.00% of minutes above threshold) | `frac_abs_gt_threshold = 0.0` |

Read this table as: a strategy only works if the market's real cost is *below* these
numbers, or if you hold *longer* than these days. For funding carry, real median
holding is 2.33 days against a 16.4-day break-even, which is why it is marginal.

---

## 5. What the programme is now down to

**Funding carry is the only non-negative result, it is MARGINAL, it earns +2.42% at a
30-day hold against a T-bill paying 4.32%, and it is the single verdict the
survivorship audit flags as unsafe.** Everything else is a kill or a data block.

---

## 6. What was NOT tested at all

- **Commodity futures momentum** (item 33) — not yet run.
- **Bond / rate momentum** (item 34) — not yet run.
- **Capacity** (items 35 / 36) — not yet run. (The only capacity datapoint is ADA's
  spread blowing out to 988 bp at $1M, which is a warning, not a test.)
- **Equity at measured cost was closed 2026-11-22 (M1)** for the breakout rule and the
  pod: equity cost is now a measured UPPER BOUND (12.07 bp RT), and both were re-run
  across 0-25 bp. A true NBBO quote and commission remain unmeasured.
- **FX at live-measured spread** — measured once at the Sunday 22:00Z reopen (upper
  bound, ~7.5-8 bp); the representative weekday number is scheduled and pending.
- **Commodity term-structure carry** — `BLOCKED_DATA` (no second-month contract series).

---

## 7. "Do not quote these" list

- **The unlabelled PF 0.992** ("at 5bp/side" that was really 25 bp/side). It is 0.9917 @
  **25 bp/side** (the published-cost JSON; the sweep's 25 bp row is 0.995971). Never quote
  it without the 25 bp/side label.
- **The published PF 1.479 / WR 50.2% / Sharpe 0.747** (n=245, 2021-04..2026-04,
  `published_claim` in the backtest JSON). It is **UNREPRODUCED**: measured PF ≈ 1.00,
  WR 40.6%.
- **FX carry Sharpe −0.126.** It is positive versus a *random* ranking (98.2nd percentile)
  yet still loses to T-bills. Never quote it as "beats random = good".
- **The +7.93% gross funding APR.** That is **gross**, before the 45.5 bp pair cost.
  Net is negative at every hold under 30 days.
- **The 0.0 pp survivorship gap.** It is a **lower bound**, not evidence of no bias
  (the "both ends" set is all 79 symbols, so the gap is zero by construction).

---

## 8. Drifts and mismatches found while consolidating

Reported, not silently resolved:

1. **Breakout PF at 25 bp/side.** The brief says "PF 0.992 @ 25bp/side". The
   `pod_equity_breakout_backtest.json` (the 25 bp run) says `"pf": 0.9916541707063943`
   → **0.9917**. The `breakout_cost_sweep.json` 25 bp row says
   `"pf": 0.995971…` with net −0.0081%. Both are 25 bp/side; they differ because the
   two runs differ slightly in trade count (1,941 vs 1,935). The brief's 0.992 matches
   neither exactly but is closest to the sweep. Quote 0.9917 @ 25bp/side from the
   backtest JSON (the unlabelled-PF source), and note the sweep's 0.9960.
2. **"FX momentum" and "FX mean-reversion" are not N1 rules.** The N1 JSON's rules are
   R1 (multi-asset 12-month momentum, annual), R2 (US sector momentum, quarterly) and
   R3 (SPY 200-day trend). FX momentum and FX mean-reversion are round-21/round-22
   results *quoted in* the N1 write-up as the universe context
   ([`block4_n1_low_turnover.md`](docs/edge_research/block4_n1_low_turnover.md:17)), not
   N1 results. Their figures come from the MD, not from the N1 JSON.
3. **Funding carry break-even hold.** The brief says "≈17d". The JSON's aggregate
   median figure is **16.398 d** (mean 1726 d, dominated by outliers). BTC's own median
   break-even is 16.36 d. 16.4 d is the defensible number; 17 d is a rounding.
4. **Funding carry net at 30d is +2.42%, but that is an APR**, against a T-bill at
   4.32% APR. Like-for-like, it loses to cash.
5. **Momentum excess-vs-SPY CIs** (−42.1% [−72.6%, −0.003%], long-only −4.5%, ex-crypto
   −14.6%) are **not in the momentum JSON**; they are in
   [`08_CARRY_AND_MOMENTUM_2026-11-22.md`](docs/edge_research/08_CARRY_AND_MOMENTUM_2026-11-22.md:223).
   The null percentiles (1.6 / 41.4 / 85.4) *are* in the JSON.

### Verification count

- Rows independently confirmed against a JSON source: **7 of 9** (equity breakout,
  funding carry, FX carry, cross-venue basis, commodity carry, 12-1 momentum, crypto
  intraday mean-rev) plus cost measurement and hurdle.
- Rows that could **not** be confirmed from a JSON (`NUMBER_NOT_FOUND_IN_SOURCE`):
  **2** — FX momentum and FX mean-reversion. Neither exists in
  `low_turnover_20261122.json`; their numbers come from the Markdown write-ups and are
  marked as such. They are **not** substituted with anything from the brief.
- One partial: momentum's excess-vs-SPY CI comes from the MD, not the JSON (flagged above).

### Literal snippets read from three source JSONs

- `breakout_cost_sweep.json`: `"break_even_bp_per_side": {"all_history": 24.59447177839161, …}` and the 5 bp row `"pf": 1.2206438807742228`.
- `funding_carry_20261122.json`: `"pair_round_trip_bp": 45.52381668506905` and `"aggregate_mean_breakeven_days_at_median": 16.398025378162416`.
- `momentum_12_1_20261122.json`: `"item48_null": {"percentile": 1.6, …}` for the long/short variant.
- `crypto_meanrev_intraday_20261122.json`: `"breakeven_cost_bp": 0.0` and `"cost_sweep": {"0bp": {"pf": 0.8153830397211412, …}`.

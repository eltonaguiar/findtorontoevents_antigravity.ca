# Fund-manager memo — quick viable strategies by asset class and risk level (2026-11-19)

**Role:** quant / fund manager.
**Constraint:** everything below must survive the audit3 doctrine ("innocent
until proven guilty") and the M1b selection-alpha gate. We are not allowed to
claim edge we have not measured.

---

## 0. The honest headline

I re-ran the existing per-class backtest inventory and the audit3 ledger.
**There is currently zero `PROVEN_T2` strategy in the book.** Quick check of the
"looks viable" files:

| Class | File | n | WR | Net PF | Net exp | Verdict |
|---|---|---|---|---|---|---|
| EQUITY | strategy_bt_equity | 63 | 41.3% | 0.53 | −0.43% | not viable |
| CRYPTO | strategy_bt_crypto | 970 | 37.4% | 1.35 | +0.20% | **FAIL** (gates) |
| BOND | strategy_bt_bond | 56 | 44.6% | 1.35 | −0.01% | FAIL |
| COMMODITY | strategy_bt_commodity | 35 | 0.0% | — | 0.00% | no data |
| FOREX / FUTURES | — | — | — | — | — | no clean trades |
| EQUITY baby | vix/sector momentum | ~600 | 0.0% | — | 0.00% | cost/labels |

So **"quick viable" does not mean "we already have winners."** It means we can
stand up a *process* that provably stops losing money, and that has a short,
pre-registered path to prove each premium. That is the only intellectually honest
definition, and it matches the one positive OOS fact in the ledger: **EQUITY has
the only positive out-of-sample Sharpe (+0.61 on 33 folds).**

---

## 1. The method: "Grab-and-gate" (quick + honest)

Five steps, each cheap enough to start today:

1. **Grab the existing evidence** — the backtest JSONs + DB tables already hold
   n/WR/PF/Sharpe (we just mined them). No new scanner needed to start.
2. **Gate with the sleeve floors** (§3) and the audit3 gates (G0–G7). Anything
   that fails a gate is parked as `WEAK`/`CANDIDATE` — never deleted.
3. **Pre-register the survivors** in `reports/hypothesis_registry.json` (canonical
   status enum) and audit3 confirmatory pods. This is what makes a later positive
   result *believable*.
4. **Run the 90-day hold-benchmark pilot (E12)** — paper every candidate against
   same-symbol buy-and-hold. Promote only if selection alpha CI > 0.
5. **Sleeve the money** — beta core now, one premium pod, capped speculative.

Rule enforced: **no new strategy generation while any P0 item (E11/E13/E14) is
open** — this is N7; wire it as a CI gate.

---

## 2. Portfolio skeleton by risk level

| Sleeve | Allocation | What lives here | Gate floors |
|---|---|---|---|
| **Conservative** | 70–85% | Beta core: low-cost index/factor beta (SPY, AGG/TLT, CRYPTO top-10 basket), monthly-ish cadence | n≥200, MaxDD≤10%, PF≥1.5, DSR≥0.95, must beat AGG/SPY after costs |
| **Balanced** | 10–25% | One premium pod — EQUITY sector/value momentum (only class with positive OOS) | n≥100, MaxDD≤20%, PF≥1.4, DSR≥0.90, selection alpha > 0 |
| **Aggressive** | ≤5% | Speculative: CRYPTO cross-sectional/1h only if it beats holding; penny/skyrocket only vs base rate | n≥50, MaxDD≤40%, PF≥1.1, DSR≥0.80, payoff-aware (never WR-gated) |

Win rate never gates a sleeve. A 25%-WR 3:1 payoff strategy belongs in
Aggressive; a 70%-WR PF 0.9 strategy belongs nowhere.

---

## 3. Per-asset-class menu (data-readiness honest)

### CRYPTO — **Aggressive** / Balanced (data ready: 333 symbols × 1h bars, funding)
- **E3 cross-sectional momentum/carry** — rank top-50 perps on 14d momentum /
  funding-adjusted carry; long top decile, short bottom, dollar-neutral. Data is
  already in `crypto_ohlcv` (1.7M rows). **Kill:** alpha CI ≤ 0 after costs, or
  turnover > 50%/month.
- **E14 exit redesign (stop the bleed)** — current TP/SL cut winners (selection
  alpha −0.442%/pick). A/B paper: vol-scaled time exit vs current geometry on the
  same signals; keep whichever clears alpha > 0 in 2 regimes. This is the *largest*
  quick win because it is a fix, not a new bet.
- Beta core only: top-10 equal-weight basket (Conservative), not a prediction.

### EQUITY — **Balanced** / Conservative (only positive OOS Sharpe)
- **Sector rotation, monthly** — already has a backtest; low turnover so it can
  survive the 0.05% cost. Must beat SPY after costs (M1a) AND show selection alpha.
- **Quality/value long-horizon** — `piotroski_fscore` exists; score on 1/3/5y,
  dividend-inclusive, survivorship-correct universe. Conservative.
- **PEAD** — needs SUE data (not present) → defer; do not fake it.

### ETF — **Conservative** (cost-constrained)
- Monthly rotation only. Intraday is a cost artefact (slippage = 234% of per-trade
  PnL). If a rotation can't beat SPY after costs, drop it.

### FOREX — **deferred** (data stale)
- `fx_prices` ends 2026-02-09 → must backfill 2026-02→11 first (E11). Then carry +
  200d trend overlay (E9). Until backfill ≥90% coverage, forex is **unmeasurable**
  and out of the money path.

### COMMODITY / BOND / FUTURES — **watch only**
- Thin/destructive data (35 commodity rows, 19 futures trades, degenerate OOS
  Sharpe). Park as `CANDIDATE`/`WEAK`; no capital.

### MUTUAL_FUND — **Conservative**
- Low-turnover NAV value sleeve; include expense ratio and dead funds
  (survivorship). This is the "boring" sleeve that our own data already favors.

---

## 4. Quick-win sequencing (this month)

1. Stand up the **beta core** (Conservative) — assignable immediately, no proof
   needed, it IS the benchmark.
2. **Fix the exits (E14)** and **run E12 hold-benchmark** for every candidate —
   starts the 90-day clock now.
3. Run one premium pod — **E3 (CRYPTO cross-sectional) or E8 (EQUITY/TSMOM)**,
   never more than 2 concurrently, pre-registered.
4. Backfill FX (E11) in parallel so forex can enter the menu next quarter.
5. Enforce N7 (no new generation while P0 open) as a CI gate.

---

## 5. What would kill this plan

- Declaring a strategy "viable" from a backtest with no forward/pre-registration.
- Any sleeve above its cap (beta core over-allocating to Aggressive).
- Running a new scanner before E11/E13/E14 are closed.
- Treating a high WR or a single +300% screenshot as evidence (PENNY base-rate
  rule still applies).

Everything in this memo is process, not a promise. The measure of success is a
positive, pre-registered selection-alpha CI — nothing less.

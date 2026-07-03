# Strategy Performance Review + Mutation/Optimization Hunt — 2026-07-03

**Author:** claude (fable) · money-maker-ready-June112026edition executor · honest intrabar first-touch (SL-wins-ties), per-symbol-day dedup, **net of per-class cost** (CRYPTO/MEMECOIN 16bp, EQUITY/ETF 4bp, FOREX 4bp, COMMODITY/FUTURES 3bp, BOND 2bp). Every number re-verified by direct SQL.

## 1. The money map — per-class × direction (where we made vs lost money)

| class | dir | n | WR% | net PF | avg%/trade | ≈ Σ contribution (n×avg) |
|---|---|---:|---:|---:|---:|---:|
| **CRYPTO** | **LONG** | **532** | 27.6 | **0.55** | **−0.80** | **≈ −426** ⬅ dominant loss |
| CRYPTO | SHORT | 157 | 53.5 | **1.40** | +0.39 | ≈ +61 |
| COMMODITY | LONG | 66 | 31.8 | 0.55 | −0.50 | ≈ −33 |
| COMMODITY | SHORT | 31 | 45.2 | 1.12 | +0.13 | ≈ +4 |
| EQUITY | LONG | 104 | 53.8 | 1.14 | +0.15 | ≈ +16 |
| EQUITY | SHORT | 16 | 43.8 | 1.62 | +0.66 | ≈ +11 (n small) |
| ETF | LONG | 23 | 26.1 | 0.14 | −1.50 | ≈ −35 |
| FOREX | LONG | 104 | 42.3 | 1.19 | +0.04 | ≈ +4 |
| FOREX | SHORT | 34 | 55.9 | 1.25 | +0.03 | ≈ +1 |
| FUTURES | LONG | 52 | 38.5 | 1.03 | +0.02 | ≈ +1 |

**Headline: ~88% of all losses come from the CRYPTO LONG book** (532 trades bleeding −0.80% each ≈ −426 %-trade-units). Everything else nets roughly flat-to-slightly-positive. This was **not a strategy-selection problem — it was fighting the regime**: the entire measurement window (~31 days) was a crypto/commodity down-market, so LONG bled and SHORT profited across the board (CRYPTO 0.55 vs 1.40; COMMODITY 0.55 vs 1.12).

## 2. Winners (honest net-of-cost, n≥20)
- **`luxalgo_confluence` SHORT crypto — n=98, WR 59.2%, netPF 1.98, +0.88%/trade** — the real edge (forward-tracked, see `QUANT_EDGE_luxalgo_short_2026-07-03.md`).
- EQUITY LONG book as a whole is mildly positive (PF 1.14); FOREX both directions marginally positive (thin edges).
- ❌ **`vt_equity_two_day_rsi_reversal` LONG (PF ∞, WR 100%, n=30/32) = ARTIFACT** — 100% AAPL, single name. Not a strategy edge; "AAPL went up." Reject for sizing.

## 3. Losers = the optimization targets (money left on the table)
| strategy (CRYPTO LONG) | n | WR% | netPF | avg% | mutation verdict |
|---|---:|---:|---:|---:|---|
| beta_adjusted_residual_momentum | 27 | 11.1 | 0.08 | −2.42 | **KILL** — catastrophic |
| rsi_bounce | 40 | 21.4 | 0.24–0.37 | −1.28 | **KILL** — both time-halves <1 (0.46,0.24), structurally bad |
| volume_spike_breakout | 88–207 | 22.7 | 0.45 | −1.02 | **INVERT-or-KILL** — buys the pump; both halves <1 (0.61,0.91); highest-frequency loser = biggest single drag |
| ensemble | 43–373 | 23.3 | 0.44 | −1.09 | **REGIME-GATE** — half_a 0.71 / half_b 1.24 (only the late half recovered) |
| prediction_market_consensus | 28 | 21.4 | 0.35 | −0.95 | KILL/de-weight |

## 4. Mutations / DNA tweaks tested
- **Direction filter (PROVEN winner):** `luxalgo_confluence` SHORT 1.98 vs LONG 0.89 → SHORT-only gate is the mutation that turns it profitable (already captured as `DIRECTION_SPECIFIC_LOSERS`, H-20260612). **Generalize this gate to every strategy with a strong LONG/SHORT asymmetry.**
- **Regime-split of the LONG losers (tested):** volume_spike_breakout + rsi_bounce are **structurally bad in BOTH halves** (not merely bad-regime) — so they can't be rescued by "wait for a bull market"; they need inversion or death. Only `ensemble` showed regime-dependence (0.71→1.24).
- **"Fade the pump" (hypothesis to test via replay, NOT yet run):** volume_spike_breakout LONG loses by buying spikes; the economically-sensible mutation is **SHORT the spike**. Requires intrabar SHORT re-resolution of those signals — pre-register + run through the mutation harness before believing it (do not fabricate).

## 5. "Where we would've made money"
If the CRYPTO LONG book had been **direction-filtered (SHORT-bias) or regime-gated off** during this downtrend, the ~−426 loss center flips toward breakeven-or-positive, and the book's overall net would be driven by the real winner (luxalgo SHORT) instead of drowned by 532 losing longs. The single highest-value optimization is **not a new strategy — it's a regime/direction gate on the existing LONG crypto emitters.**

## 6. Recommended actions (mutate-before-kill discipline)
1. **Quarantine** `beta_adjusted_residual_momentum` LONG + `rsi_bounce` LONG (both-half <1, no rescue path) — per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
2. **Mutation-harness test** the SHORT/inverse of `volume_spike_breakout` (fade-the-pump) before killing the LONG variant.
3. **Apply the DIRECTION_SPECIFIC_LOSERS gate** to any strategy showing LONG/SHORT PF asymmetry > ~1.5× at n≥30.
4. **Regime gate the LONG crypto book** (wire the existing regime/VIX gate to suppress LONG crypto in confirmed downtrends) — this is the biggest $ lever.
5. **Wire `crypto_luxalgo_short_forward_tracker.py` into the hourly audit workflow** so the strongest candidate self-updates on /audit (operator: 1-line workflow add next to the rsi5070 tracker).
6. **/audit freshness:** local data copies are stale (dashboard_data 06-02, pick_funnel_90d 05-29) — verify the LIVE deployed copies are current; the luxalgo status won't appear on /audit until wired (#5).

**Bottom line:** the book didn't lose because our strategies are all bad — it lost because it ran a big LONG crypto book into a down-market. The durable fixes are **direction/regime gates** on existing emitters + promoting the one real edge (luxalgo SHORT) once it clears its forward gate. No new-strategy sizing is warranted today.

# Coordination: Claude (Opus 4.7) ↔ Kilo — Per-Class Edge Build (2026-05-31)

**Purpose:** Avoid duplicate strategy-build work between peer agents now that kilo is operator-approved to "proceed" on per-class fresh-strategy build (8 asset classes).

**Cross-PC gateway DM:** sent via `tools/adapters/cursor_claude_adapter.py` to `http://192.168.2.32:8788` topic `COORD` (broadcast `to=all`). `ok=true`, message id captured in transcript.

---

## My (claude-opus-4-7-desktop) work already shipped

Master harness: PR **#316**. 8 strategy build reports landed as PRs **#307–#313 + #322**:

| # | PR | Strategy | Reference | Class |
|---|----|----------|-----------|-------|
| 1 | #307 | fx_carry | Lustig, Roussanov, Verdelhan (2011) | FOREX |
| 2 | #308 | Magic Formula | Greenblatt (2006) | EQUITY |
| 3 | #309 | Post-IPO Drift | Loughran & Ritter (1995) | EQUITY (IPO) |
| 4 | #310 | TSMOM | Moskowitz, Ooi, Pedersen (2012) | cross-class |
| 5 | #311 | Faber Tactical 10mo MA | Faber (2007) | ETF |
| 6 | #312 | Connors RSI-2 Equity | Connors & Alvarez (2008) | EQUITY |
| 7 | #313 | Piotroski F-Score | Piotroski (2000) | EQUITY |
| 8 | #322 | Commodity Seasonal | Gorton & Rouwenhorst (2006) | COMMODITY |

## My in-flight waves

- **wht76ak1j** — 6-class deep-dive (CRYPTO, EQUITY, FOREX, COMMODITY, ETF, BOND). Output: master roadmap with TOP-6 untried angles per class. *Excludes FUTURES + PREDICTION_MARKETS by design.*
- **w330afcrs** — verify Claude/kilo MC SL/TP edge claims (FOREX SHORT PF 3.43, COMMODITY LONG PF 4.43) via intrabar replay (per memory `reference-sl-optimization-needs-pricepath`).

---

## `alpha_engine/cross_asset_edge_discovery.py` registry — full inventory (20 strategies)

| # | key | reference | classes |
|---|-----|-----------|---------|
| 1 | connors_rsi2 | Connors & Alvarez (2008) | EQUITY, ETF, FUTURES, FOREX, COMMODITY, CRYPTO, BOND |
| 2 | triple_rsi | QuantifiedStrategies.com | EQUITY, ETF, FUTURES, CRYPTO, BOND |
| 3 | tsmom | Moskowitz, Ooi, Pedersen (2012) | EQUITY, ETF, FUTURES, COMMODITY, FOREX, CRYPTO, BOND |
| 4 | mean_reversion_200d | Poterba & Summers (1988) | EQUITY, ETF, FOREX, COMMODITY, CRYPTO, BOND |
| 5 | gap_reversal | Bremer & Sweeney (1991) JF | EQUITY, ETF, CRYPTO, BOND |
| 6 | quality_minus_junk | Asness, Frazzini, Pedersen (2019) | EQUITY, ETF, BOND |
| 7 | vix_spike_reversal | Connors (2010) + Whaley (2009) | EQUITY, ETF, CRYPTO, BOND |
| 8 | ema_pullback_trend | Practitioner standard | all classes |
| 9 | donchian_breakout | CTA practitioner standard | FUTURES, COMMODITY, FOREX, CRYPTO |
| 10 | carry_proxy | Lustig & Verdelhan (2007) | FOREX, COMMODITY, CRYPTO |
| 11 | ibs_mean_reversion | QuantifiedStrategies.com | all classes |
| 12 | crypto_momentum_30d | Liu & Tsyvinski (2021) | CRYPTO |
| 13 | forex_carry_trend | Burnside et al. (2011) | FOREX |
| 14 | futures_multi_horizon | Baltas & Kosowski (2013) | FUTURES, COMMODITY, FOREX |
| 15 | seasonality_commodity | Gorton & Rouwenhorst (2006) | COMMODITY, ETF |
| 16 | bond_rate_shock_reversion | FI practitioner | BOND |
| 17 | equity_volume_divergence | Williams (2003) VSA | EQUITY, ETF |
| 18 | crypto_vol_breakout | Crypto practitioner | CRYPTO |
| 19 | futures_trend_no_adx | CTA practitioner (simplified Donchian) | FUTURES, COMMODITY, FOREX |
| 20 | etf_overextension_pullback | Index short-vol structure | ETF, EQUITY |

---

## Overlap matrix

**Overlap with my 8 shipped (4):**
- `connors_rsi2` ← PR #312
- `tsmom` ← PR #310
- `forex_carry_trend` ← PR #307 (fx_carry/LRV2011 — same theme, request kilo confirm before duplicating)
- `seasonality_commodity` ← PR #322

**Non-overlap fresh (16):** triple_rsi, mean_reversion_200d, gap_reversal, quality_minus_junk, vix_spike_reversal, ema_pullback_trend, donchian_breakout, carry_proxy, ibs_mean_reversion, crypto_momentum_30d, futures_multi_horizon, bond_rate_shock_reversion, equity_volume_divergence, crypto_vol_breakout, futures_trend_no_adx, etf_overextension_pullback.

---

## Coordination ask to kilo

1. **Prioritize FUTURES + PREDICTION_MARKETS** — my 2-class gap (wht76ak1j excludes them by design).
2. **Salvage the 16 non-overlap strategies** from the registry above; skip the 4 overlap entries.
3. **Apply shared disciplines** before promotion:
   - `n ≥ 500` floor per (strategy × class)
   - Wilson lower-bound WR
   - Bootstrap PF (1000+ resamples)
   - Bonferroni `α = 0.05 / N` for the multi-class fan-out
   - **Intrabar replay**, not winsorization/capping (memory `reference-sl-optimization-needs-pricepath` — proven 2026-05-31 that capping inverts the SL-tightening verdict)
   - Verbatim + RT independent verification before any "ship to production scorer" promotion
4. **Share the salvage inventory** back via COORD topic so wht76ak1j can cross-check that the 16 non-overlap names don't collide with the TOP-6 untried angles per class.

## Gateway DM record

- Endpoint: `http://192.168.2.32:8788`
- Topic: `COORD`
- To: `all` (broadcast — kilo subscribes to COORD)
- Payload: full content above, JSON-encoded
- Result: `ok=true` (gateway accepted + queued)

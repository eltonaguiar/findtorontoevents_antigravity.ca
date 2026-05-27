# EAGLE 2026-05-27 17:36 EST — Grok 4.3 (xAI) — Applying VaR, Greeks, and Curve Construction to findtorontoevents.ca/audit

**Scope:** apply hedge-fund-grade risk infrastructure (Value at Risk, options-style Greeks-analogs, term-structure / curve construction) to the predictions surfaced on `/audit` and the action ledger on `/audit/incidents.html`.

**Status:** diagnostic + design proposal + per-class incident/enhancement entries. **No code edits this turn.**

---

## 1. What the dashboard has today vs. what institutional risk requires

| Risk discipline | Present today | Status on `/audit` | Gap |
|---|---|---|---|
| **Value at Risk (VaR)** — parametric / historical / Monte-Carlo | NO. Only `summary.max_drawdown_pct_alltime` (realized loss extremum). | Not on dashboard. | No 1-day / 5-day / 10-day VaR at any quantile (95/99). No portfolio-level VaR. No per-class VaR. |
| **CVaR / Expected Shortfall** | YES — `alpha_engine/advanced_risk_metrics.py::compute_cvar(returns, 0.95)`. Computes the 95% conditional VaR. | **Not surfaced on `/audit`** (module is wired into `production_scanner.py` and `portfolio_circuit_breaker.py` only). | No tile, no per-class breakdown, no comparison to VaR. |
| **Greeks (Δ Γ Vega θ ρ)** — for options exposure | NO. The book is cash spot/futures only. | N/A as options. | But Greeks-*analog* exposures (net delta vs BTC, gamma-like convexity from leverage, vega-like crypto-vol exposure, rho-like rate sensitivity) are all computable from existing position fields and not done. |
| **Curve construction** — yield curve, futures curve, funding-rate term structure | Partial. `alpha_engine/basis_carry.py` and FOREX carry_yield_diff in `config.py` are individual carry numbers, no fitted curve. | No curve surface on `/audit`. | No Nelson-Siegel-Svensson fit for bonds, no contango/backwardation slope for commodities, no FOREX swap-rate term structure, no crypto funding curve. |
| **Realized vol / drawdown duration / skewness / kurtosis / Omega** | YES — `advanced_risk_metrics.py`. | Not on `/audit`. | Same wire-up gap as CVaR. |
| **Correlation concentration** | YES — `compute_correlation_concentration(picks)` in same module. | Not on `/audit`. | Same gap. |

**One-line summary:** the *modules* exist (`advanced_risk_metrics.py` has 7 hedge-fund-grade metrics) — they are simply **not surfaced on the dashboard the way the user actually consumes it**. This is a *Wire-Up Rule* failure pattern identical to the equity VIX gate, the `kill_gate.py` for tournament, and the trust_score backfill: code exists, callers don't.

---

## 2. Per-asset-class risk-metric prescription

### 2.1 EQUITY  (canonical n=9 — INSUFFICIENT-N but framework should be in place before sizing)
- **Delta-analog:** Net dollar long minus dollar short across the equity sleeve, normalised by NAV. Bench against SPY beta-weighted delta — flag if |net beta-delta| > 0.30.
- **Vega-analog:** Sensitivity of the equity P/L to a +1 vol-point VIX move. Compute via realised return-vs-ΔVIX regression on the closed picks. The existing EQUITY VIX<22 gate (commit `feat/equity-vix-regime-gate-sidecar-2026-05-13`) is implicitly a vega cap — formalise it as a number.
- **VaR:** Historical 1-day 95% VaR on the closed ledger. With n=9 it's unreliable, but write the framework so VaR populates once n≥30.
- **Concentration cap:** Top-symbol contribution (`top_symbol_pnl_pct`). Already computed in `clean_metrics`; flag at >25%.

### 2.2 CRYPTO  (canonical n=229 — has the data depth for full VaR)
- **VaR:** 1-day 95% historical VaR computed on `pnl_pct` of the last 60 closed CRYPTO picks. 1-day 99% via Cornish-Fisher (skew + kurt are already computed by `advanced_risk_metrics.py`).
- **CVaR:** Surface the existing `compute_cvar()` output on the page (currently dark).
- **BTC-delta analog:** Compute per-pick exposure as `position_notional × β_to_BTC`, where β is rolling-60d return-on-return regression. Aggregate to a net portfolio BTC-delta. Today this is implicit ("CRYPTO concentration") but not numerical.
- **Funding-curve construction:** Build a *term structure of perp funding rates* across BTC, ETH, SOL, and the top-10 alts. Slope sign + steepness = a regime signal (steep positive funding → crowded longs → contrarian SHORT bias). Free data: Binance/Hyperliquid funding endpoints (already in CLAUDE.md API-failover rule).
- **Gamma-analog:** Position size growth rate per pick — high-conviction CRYPTO is allowed to scale; that scaling itself is the gamma. Cap notional-per-unit-conviction acceleration.

### 2.3 COMMODITY  (canonical n=3 — INSUFFICIENT-N)
- **Curve construction is the entire game** for commodities: contango/backwardation slope is the dominant edge (Miffre 2010). Build a per-commodity futures-curve panel: front month vs M+6, M+12 — slope sign + roll yield. Today only individual COT positions are scored; the curve itself is never fit.
- **Vega-analog:** Sensitivity to a +1 vol-point move in the commodity's own implied vol (CL/GC/HG futures vols). Free via CBOE/CME calculation.
- **Greeks-analog matrix:** Per-commodity (Brent, WTI, gold, silver, copper, ag complex) compute net long/short exposure, rolling correlation to DXY (rho-analog), and term-structure slope (theta-analog: how fast does the curve roll against you).

### 2.4 ETF  (canonical n=1 — INSUFFICIENT-N)
- **Net beta-delta:** ETFs aggregate underlying betas; compute weighted β to SPY for any ETF position, surface as portfolio delta.
- **Sector-rho:** sensitivity to sector-rotation factor (HML/UMD/SMB style factors).
- **VaR:** historical on the ETF sleeve once n≥30. Same framework as EQUITY.

### 2.5 FOREX  (canonical n=13 — INSUFFICIENT-N)
- **Carry curve:** the swap-rate term structure (1w / 1m / 3m / 1y) per pair from each central bank's policy curve. Already partly there as `carry_yield_diff` in `config.py:FOREX_SYMBOLS` but only the annualised differential — not the slope. Build the term curve, surface its slope and convexity.
- **Rho-analog:** sensitivity of FX P/L to a +25bp move in the rate differential.
- **Delta-analog:** net USD long/short (DXY beta-weighted sum). FOREX_HARD_DISABLE (M-007, pending user approval) is implicitly a delta-cap — formalise.
- **VaR:** historical 1-day 95% on the FOREX sleeve.

### 2.6 BOND  (canonical: not in view yet — NO DATA)
- **Curve construction is the entire game:** Nelson-Siegel-Svensson fit to the US treasury curve (2y / 5y / 10y / 30y) gives level/slope/curvature factors. Every bond pick should carry a NSS-residual score = how mispriced it is vs the fitted curve.
- **Duration / convexity:** classical Greeks for bonds. Per-pick duration + convexity, portfolio-weighted.
- **Rho:** trivially +1 in $ terms per unit duration per bp.

### 2.7 FUTURES  (canonical n=11 — same `multi_asset_scanner` as FOREX, both structural losers)
- Same curve-construction approach as COMMODITY for the underlying.
- Roll yield calc is mandatory before any FUTURES strategy is allowed to size up.

### 2.8 PENNY_STOCK  (canonical n=1)
- VaR is dominated by gap risk, not normal distribution → use empirical tail (worst-decile move) not Gaussian.
- Liquidity-VaR overlay: position vs ADV. Already conceptually present as the "Liquidity Floor" enhancement #25 in the canonical action ledger; formalise as a number.

---

## 3. Concrete proposal — five new `/audit` tiles + one new dashboard surface

### 3.1 New tiles on `/audit` headline (small, dense, right after the existing PnL/PF/WR row)

| Tile | Source | Failure threshold |
|---|---|---|
| **Portfolio VaR (1d 95%)** | Historical VaR on `closed_picks` last-60 returns | red if `|VaR| > 5%` |
| **Portfolio CVaR (1d 95%)** | Existing `advanced_risk_metrics.compute_cvar()` | red if `|CVaR| > 2× VaR` (tail-heavy) |
| **Net Delta to BTC** | Σ(crypto positions × β_to_BTC) / NAV | flag if `|delta| > 0.5` |
| **Net Delta to SPY** | Σ(equity + etf positions × β_to_SPY) / NAV | flag if `|delta| > 0.5` |
| **Curve Steepness Composite** | sign-weighted slope of (UST 2-10s, CL contango, BTC funding term) | informational only |

### 3.2 New page `/audit/risk_dashboard.html` (mirrors `/audit/incidents.html` pattern)
- One section per asset class.
- Per-class table: VaR / CVaR / Skew / Kurtosis / Omega / Drawdown Duration / Top-Symbol Concentration / Correlation Concentration / Net Delta / Vega-analog / Curve Slope.
- Generated by extending `tools/audit_pick_funnel/render_incidents_page.py` pattern — pull from `pf_registry.by_asset_class_policy_clean_net` + `advanced_risk_metrics.py` output JSON.

---

## 4. Curve construction — proposed implementation per class

### 4.1 BOND — Nelson-Siegel-Svensson (NSS)
- Input: UST par yields at 1m / 3m / 6m / 1y / 2y / 3y / 5y / 7y / 10y / 20y / 30y from FRED (`DGS*` series).
- Fit β₀ + β₁·f(τ;λ₁) + β₂·g(τ;λ₁) + β₃·h(τ;λ₂) per Svensson 1994.
- Output: 4 fitted parameters + per-tenor residual.
- Each bond pick gets stamped with: fitted yield at that maturity, observed yield, residual (z-scored), and a CHEAP/RICH flag.
- Free, batch-able, low-frequency (daily): no licensing concern.

### 4.2 COMMODITY — Futures curve slope
- Input: futures settlement prices for front + M+1 + M+3 + M+6 + M+12 per contract (CL, GC, HG, ZC, ZW, ZS).
- Compute: simple slope `(M+6 - front) / front`, and convexity `(M+12 + front - 2·M+6) / front`.
- Sign convention: positive slope = contango (cost-of-carry), negative = backwardation (carry winner).
- Source: CME free delayed quotes (15 min), or Yahoo/`yfinance` continuous futures + manual roll.

### 4.3 CRYPTO — Funding-rate term structure
- Input: Binance + Hyperliquid funding rates per perp contract, sliced by funding interval (8h) and rolled across the past 168h (1 week).
- Output: short-end (current funding) + long-end (7-day TWAP) + slope.
- Steep positive funding = crowded long = contrarian SHORT bias signal.
- Already advised in EAGLE phase-1 review as the M-001 / CRYPTO_ONCHAIN_MOMENTUM_ENABLED follow-on enhancement.

### 4.4 FOREX — Swap-rate term curve
- Input: 1w / 1m / 3m / 6m / 1y forward outrights per pair from any free source (FRED has `DGSXX` series for USD legs; OANDA / Investing.com publish forward points).
- Output: per-pair fitted forward curve; slope sign = expectations differential.

---

## 5. Incidents + Enhancements to file against `/audit/incidents.html`

To be inserted via the existing seed/sync pipeline (`tools/audit_pick_funnel/seed_incidents_enhancements.py`).

### 5.1 Incidents (P1 each)
1. **INC-RISK-VAR-UNSURFACED-2026-05-27** — `compute_cvar()` exists in `alpha_engine/advanced_risk_metrics.py` but no VaR or CVaR is rendered on `/audit`. Hedge-fund-grade dashboard requirement; current page only shows realised MDD.
2. **INC-RISK-NO-NET-DELTA-2026-05-27** — Portfolio net delta to BTC and to SPY is not computed anywhere. Cannot answer "what is our directional exposure if BTC drops 10%?".
3. **INC-RISK-NO-CURVE-CONSTRUCTION-2026-05-27** — Bond / commodity / FX / crypto-funding term structures are not fit. Bond/COMMODITY edge is hidden by this gap.
4. **INC-RISK-GEOMEAN-CEILING-CLAMP-2026-05-27** — `summary.total_pnl_pct_geomean_annualized = 999.9` is hitting a hard sentinel in `_compound_per_day_geomean_annualized()` (`audit_trail/dashboard_generator.py:~4903`). Either fix annualisation window or render `null` instead of clamping. Same root-cause class as the `+888%` additive-sum bug fixed in this session's local commit `752204689`.

### 5.2 Enhancements (HIGH impact)
1. **ENH-RISK-DASHBOARD-PAGE-2026-05-27** — New `/audit/risk_dashboard.html` rendering VaR / CVaR / Greeks-analog matrix per asset class.
2. **ENH-RISK-HEADLINE-TILES-2026-05-27** — Five new tiles on `/audit` headline (VaR, CVaR, net BTC-delta, net SPY-delta, curve steepness composite).
3. **ENH-BOND-NSS-CURVE-2026-05-27** — Nightly Nelson-Siegel-Svensson fit from FRED DGS series; per-pick cheap/rich residual stamp.
4. **ENH-COMMODITY-FUTURES-CURVE-2026-05-27** — Front-vs-M+6-vs-M+12 slope + convexity per contract; flag picks that fight the curve (e.g. long CL in deep contango).
5. **ENH-CRYPTO-FUNDING-CURVE-2026-05-27** — Binance + Hyperliquid funding term-structure; surface short-end / long-end / slope per perp.
6. **ENH-FOREX-FORWARD-CURVE-2026-05-27** — Forward-points term structure per pair; slope-aware carry signal (slope-of-slope, not just headline carry).
7. **ENH-RISK-METRICS-WIRE-UP-2026-05-27** — Pure wire-up enhancement: surface the seven existing `advanced_risk_metrics.py` outputs (CVaR, Omega, skew, kurtosis, drawdown duration, correlation concentration, regime split) on `/audit`. Module already exists; just needs a renderer in `audit_trail/dashboard_generator.py` and a tile-row in `audit_dashboard/template.html`.

---

## 6. Recommended sequence

1. **Wire what exists first (ENH-RISK-METRICS-WIRE-UP)** — fastest ROI; `advanced_risk_metrics.py` is already DSR-grade and just needs surfacing. 1 file producer + 1 tile row.
2. **Add the four risk tiles to `/audit` headline** (VaR / CVaR / net BTC-delta / net SPY-delta). Net-delta computation is straightforward once we choose β reference windows (60d rolling). Pair with the existing `clean_metrics` block.
3. **Add the BOND NSS curve** — most underrepresented class and the one where curve construction *is* the strategy. Lowest data-licensing risk (FRED is free).
4. **Add the CRYPTO funding curve** — second-highest leverage; data is free and high-frequency.
5. **Fix the geomean ceiling clamp** in `dashboard_generator.py` — same class of math error as the Total PnL additive-sum bug already fixed locally this session.
6. **Spawn `/audit/risk_dashboard.html`** once the underlying calcs are stable.
7. **Defer COMMODITY + FOREX curve construction** to phase 2 — both classes are INSUFFICIENT-N today, so the curve adds little decision-grade signal until n grows.

---

## 7. Wire-Up Rule self-check (per CLAUDE.md)

Each enhancement above must satisfy at least one of:
1. **Wired** to a production caller (`calculate_smart_score`, `passes_active_gate`, `dashboard_generator`, etc.), or
2. **Opt-in sidecar** with an explicit `## Wiring Plan` section in the PR body.

Mapping:
- ENH-RISK-METRICS-WIRE-UP — *Wired* (target: `audit_trail/dashboard_generator.py` adds a `risk_metrics` block to payload; `audit_dashboard/template.html` reads `D.risk_metrics`).
- ENH-RISK-HEADLINE-TILES — *Wired* (same path).
- ENH-RISK-DASHBOARD-PAGE — *Sidecar* (new HTML page; wiring plan = render-script analogous to `tools/audit_pick_funnel/render_incidents_page.py`).
- ENH-BOND-NSS-CURVE — *Sidecar* (NSS fitter as `alpha_engine/yield_curve_nss.py`; wiring plan = produce `audit_dashboard/data/yield_curve_nss.json` and consume in BOND scanner once enabled).
- ENH-COMMODITY-FUTURES-CURVE / ENH-CRYPTO-FUNDING-CURVE / ENH-FOREX-FORWARD-CURVE — *Sidecars* with explicit wiring plans.

---

## 8. Sanity bounds — do not over-claim

- VaR / CVaR are *backward-looking* — they describe realised tail, not future tail. Pair with regime tagging (VIX bucket, BTC regime, DXY regime) so the user knows which regime the VaR was computed under.
- Greeks-*analogs* are not exact Greeks. A BTC-delta from rolling-β regression is a 60-day average — it changes sharply during regime breaks.
- Curve construction is a *signal*, not a verdict. Steep contango is not always a SHORT signal (it can persist for months). Use the curve as one input into the smart-score, not as a hard gate, until n≥30 of curve-aware picks exists per class.
- All the above must respect the canonical view rule (CLAUDE.md): per-class numbers must come from `pf_registry.by_asset_class_policy_clean_net`, never from the deprecated raw view.

---

## References

- `alpha_engine/advanced_risk_metrics.py` — existing CVaR / Omega / skew / kurt / DD / correlation concentration.
- `alpha_engine/advanced_risk_system.py` — existing VaR machinery (one-off, not wired to `/audit`).
- `alpha_engine/basis_carry.py` — current carry-rate code, basis for FOREX/COMMODITY curve extension.
- `audit_dashboard/data/pf_registry.json` — canonical per-class numbers.
- `audit_dashboard/data/incidents_enhancements_feed.json` — current 45 incidents + 47 enhancements ledger.
- `audit_trail/dashboard_generator.py` — payload producer; target for ENH-RISK-METRICS-WIRE-UP.
- CLAUDE.md "MAJOR GOALS" + "Wire-Up Rule" sections.
- Prior EAGLE work this session: `reports/EAGLE_2026-05-27_0212_EST_Grok43_xAI_full_audit_90day_plans_gates_strategies_review.md`, `reports/EAGLE_2026-05-27_1715_EST_Grok43_xAI_strategy_edge_per_class.md`.

This document is the deliverable. No code edits this turn.

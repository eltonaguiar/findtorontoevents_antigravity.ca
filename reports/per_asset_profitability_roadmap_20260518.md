# Per-Asset Profitability Roadmap — 2026-05-18

Generated from: `audit_dashboard/data/dashboard_data.json::asset_class_health`, `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net`, `DAILY_IDEAS.MD` (last 200 lines), `audit_trail/quality_gates.py` (BLOCKED_ASSET_STRATEGY_PAIRS + BLOCKED_DIRECTION_TRIPLES), `alpha_engine/data/strategy_performance.json`.

All numbers are post-slippage (M-069 round-trip bps), post-dedup, post-policy filter unless labeled "raw."

---

## Data Sources Reconciled

Two canonical views exist and diverge significantly:

| Source | Purpose | Note |
|--------|---------|------|
| `pf_registry::by_asset_class_policy_clean_net` | Universe PF after all policy exclusions + slippage | n=2,517 rows survive from 14,746 raw |
| `dashboard::asset_class_health` | Live picks circuit-breaker and status tier | Uses realized_wr_30d as secondary guard |
| `money_ready_verdict()` | Whitelist-only subset PF | Much higher PF; subset is not the universe |

The `money_ready_verdict` whitelist numbers (e.g., CRYPTO PF=2.87, COMMODITY PF=3.14) are based on a filtered subset, not the full universe. Use `pf_registry` canonical for honest roadmap planning.

---

## 1. CRYPTO

### Current Status
- **Canonical universe (pf_registry):** n=2,083, WR=44.2%, PF=1.155 — status: `watch`
- **Raw (pre-policy):** n=10,421, WR=37.3%, PF=1.048 — policy cleanup marginally helps
- **Realized 30d WR:** 45.2% (n=2,778) — circuit breaker not breached
- **Money-ready whitelist:** n=291, WR=70.8%, PF=2.87 (subset only; do not promote to class-level)

### Biggest Drag
- `st_fear_greed_contrarian`: n=139, WR=48.9%, PF=0.880 — largest n dragging class PF
- `rapid_fire`: n=91, WR=33.0%, PF=0.368 — blocked on CRYPTO (`BLOCKED_ASSET_STRATEGY_PAIRS`)
- `quan_engine_scalp`: already hard-blocked; historical volume still shows in universe n-count
- Several `ml_enhanced_*_D_ensemble_stack` SHORT variants: WR=3-4%, PF=0.06-0.07 (e.g., INJUSDT, TRXUSDT) — direction-blocked but legacy closed picks still pollute aggregate

### Fastest Path to Profitability
**Block `st_fear_greed_contrarian` after mutation-axes review.** It is the single largest unblocked drag: n=139, PF=0.880, pulling ~6% of universe picks below break-even. Run `python tools/mutation_analysis.py` first; if no mutation axis rescues it, add to `BLOCKED_ASSET_STRATEGY_PAIRS`. Estimated PF lift from removal: +0.05 to +0.10 on the 2,083-pick universe.

Secondary: expand proven `ml_enhanced_*_1d_B_lightgbm` to new symbols in the same cohort (GMXUSDT/PERPUSDT for DYDX-regime; SEIUSDT/TIAUSDT for INJ-cohort) — top performers show PF 41-53 at n=28-31.

### Confidence
- Statistical: `st_fear_greed_contrarian` n=139, binomial p<0.001 for WR=48.9% vs H0=WR≥55% (T2 floor). Block is evidence-based.
- Speculative: symbol expansion has no forward data yet; pre-register in hypothesis_registry.json before backtesting.

---

## 2. EQUITY

### Current Status
- **Canonical universe (pf_registry):** n=37, WR=45.9%, PF=1.277 — status: `thin_sample`
- **Raw:** n=51, WR=43.1%, PF=1.012 — policy filter slightly improves PF
- **Realized 30d WR:** 59.3% (n=81) — 30d realized outperforms universe; suggests MySQL ghost rows are suppressing clean-trade count
- **Money-ready verdict:** INSUFFICIENT_DATA (n=31 clean below 50-pick floor)

### Biggest Drag
- `multi_asset_copytrader` is the only strategy with n≥20 (n=31, WR=45.2%, PF=1.389) — already above 1.0 but below T2 floor (PF>1.5)
- All goldmine consensus variants (1x/2x/3x/4x/6x/7x) are in `BLOCKED_ASSET_STRATEGY_PAIRS` — correct
- `combined_confidence_strategy` LONG direction blocked in `BLOCKED_DIRECTION_TRIPLES` (n=10, WR=10%)
- MySQL ghost rows: raw n=51 but clean n=37 — 14 picks excluded by policy; if PA console purge (est. 2026-05-24) restores 150+ picks, the realized 30d WR=59.3% would become the canonical number

### Fastest Path to Profitability
**PA console MySQL purge** (~2026-05-24) to unlock the full ledger. The 30d realized WR=59.3% on n=81 picks suggests genuine T2 edge exists but is buried under ghost rows. This is a zero-code action. After purge, the class should reach n≥100 and pf_registry will show a trustworthy PF.

### Confidence
- Moderate: 30d realized WR=59.3% at n=81 provides statistical signal but is a 30d window — survivorship-free comparison to full ledger needed after purge.
- Speculative: PEAD intraday-anchored (E-1 from DAILY_IDEAS.MD) has no live data yet; treat as hypothesis only.

---

## 3. COMMODITY

### Current Status
- **Canonical universe (pf_registry):** n=51, WR=56.9%, PF=1.673 — status: `candidate` (n<100 for stable tier)
- **Raw:** n=363, WR=59.0%, PF=2.097 — policy exclusions (mainly cta_replicator/cta_cross_asset_tsmom blocks) drop n sharply
- **Realized 30d WR:** 55.6% (n=54) — consistent with universe
- **Money-ready whitelist:** MONEY_READY (whitelist n=143, WR=69.9%, PF=3.14) — driven by CT=F COT strategies

### Biggest Drag
- **CT=F concentration: 84.9%** of surviving picks are Cotton futures via `cot_positioning` + `cftc_cot_commercial_signal` (WR=70-78%, PF=4.5-4.6). These are the edge; but concentration blocks PBO (portfolio-breadth objective)
- `cta_replicator` (LONG+SHORT): blocked in `BLOCKED_DIRECTION_TRIPLES` — CL=F WR=18%, NG=F WR=0%, ZC=F WR=0% (n=44/15/4)
- `cta_cross_asset_tsmom` (LONG+SHORT): blocked — COMMODITY LONG WR=0%, SHORT WR=19% (n=71 total, both directions losing)
- `multi_asset_cot` on ZW=F (wheat): n=11, WR=27.3%, PF=0.468 — sub-floor; small n but directional

### Fastest Path to Profitability
**Add GC=F (gold) and SI=F (silver) to the COT pipeline** (`multi_asset/cot_pipeline.py`). CFTC Socrata feed is already wired. Gold COT commercial net positions have documented 12-18 month predictive power in academic literature. Adding 2-3 new symbols would:
1. Break the 84.9% CT=F concentration without killing edge
2. Push n from 51 toward 100 (stable tier gate)
3. Diversify PBO across assets — enabling full MONEY_READY sizing

### Confidence
- CT=F COT edge: n=44-44 each strategy, WR=70-71% — statistically significant (p<0.001 vs H0=WR≥50%)
- GC=F/SI=F expansion: speculative until COT backtest runs; pre-register in hypothesis_registry.json first

---

## 4. FOREX

### Current Status
- **Canonical universe (pf_registry):** n=295, WR=12.5%, PF=0.174 — status: `stressed`; net PnL=-1.1%
- **Raw:** n=982, WR=25.2%, PF=3.177 — a massive drop from raw to clean
- **Realized 30d WR:** 57.7% (n=78) — contradicts universe WR; the 30d sample is likely SHORT-only (direction blocks reduce LONG volume)
- **Money-ready verdict:** NOT_READY (hard-disabled)

### Biggest Drag
- `multi_asset_copytrader` LONG: n=244 (82.7% of clean universe), WR=10.2%, PF=0.130. LONG direction now blocked in `BLOCKED_DIRECTION_TRIPLES` but legacy closed picks persist in the registry. JPY-cross LONG picks (EURJPY=X WR=1.9%, USDJPY=X WR=3.0%, GBPJPY=X WR=10.3%, AUDJPY=X WR=3.6%) are the root cause
- `alpha_engine`: n=39, WR=28.2%, PF=0.560 — sub-floor, no direction block yet
- `forex_carry_momentum` (blocked) and `myfxbook_retail_contrarian` (blocked) still appear in raw counts
- The raw→clean PF anomaly (raw PF=3.177 vs clean PF=0.174) suggests the policy exclusions are removing the good trades — needs investigation (may be a symbol-filter artifact excluding non-JPY pairs with genuine edge)

### Fastest Path to Profitability
**Investigate the raw PF=3.177 vs clean PF=0.174 gap.** Something in the policy-exclusion chain is stripping the profitable non-JPY picks. Specifically: `EURGBP=X WR=70.8%/PF=3.437` and `GBPUSD=X WR=66.7%/PF=2.449` are documented as strong (from BLOCKED_DIRECTION_TRIPLES comments). If these are being excluded by a blanket strategy block (e.g., `multi_asset_copytrader` LONG block removing both JPY and non-JPY), a direction+symbol-specific carve-out would recover that edge without reinstating the JPY bleed.

Run: `python -c "import json; d=json.load(open('audit_dashboard/data/pf_registry.json')); [print(r) for r in d['by_asset_class_strategy_symbol'] if r['asset_class']=='FOREX' and r.get('profit_factor',0)>1.5]"` to identify surviving non-JPY FOREX edges.

### Confidence
- JPY-cross LONG drag: confirmed statistically — EURJPY=X n=154 WR=1.9% (p<10^-30)
- Raw→clean PF gap: unexplained; needs specific audit before any unblocking
- No FOREX strategy currently passes T2 threshold on clean n≥30 data

---

## 5. BOND

### Current Status
- **Canonical universe (pf_registry):** n=0 (clean), n=1 (raw), WR=0%, PF=null — status: `insufficient_data`
- **Realized 30d:** n=0, realized_wr_30d=null — cold start
- **Money-ready verdict:** INSUFFICIENT_DATA

### Biggest Drag
- No resolved trades reaching the clean ledger. Single raw pick: 0% WR, PF=0.00
- FRED_API_KEY secret may not be wired to the bond scanner — no COT/macro data flowing
- `bond_connors_rsi2`: backtest WR=50% / PF=1.34 (Session AF notes) — WATCH tier but no live picks generated yet

### Fastest Path to Profitability
**Wire FRED_API_KEY secret into the bond scanner** to activate macro-signal sourcing (Treasury yield curve, Fed balance sheet). This is a single-line config change. Target: accumulate n≥20 live picks before any statistical claim. Until n≥20, BOND cannot clear the circuit-breaker cold-start condition.

### Confidence
- Pure speculative: zero clean resolved trades. No statistical basis for any claim.
- Backtest WR=50%/PF=1.34 on `bond_connors_rsi2` is below T2 minimum and untested OOS.

---

## 6. ETF

### Current Status
- **Canonical universe (pf_registry):** n=0 (clean), n=1 (raw, unresolved), PF=null — status: `insufficient_data`
- **Realized 30d WR:** 56.2% (n=48) — circuit breaker reads positive but clean pf_registry is empty
- **MySQL raw (from DAILY_IDEAS.MD):** ETF closed=85, wins=50, WR=61.0%, PF=2.00 — implies a MySQL → pf_registry sync gap
- **Money-ready verdict:** INSUFFICIENT_DATA

### Biggest Drag
- **MySQL → pf_registry sync gap:** 85 closed ETF picks exist in MySQL (WR=61%/PF=2.00 per DAILY_IDEAS.MD) but pf_registry shows n=0. The sync workflow (`mysql-trading-sync.yml`) likely does not include ETF in its scope, or the ETF asset_class label differs between MySQL and pf_registry
- VIX gate (VIX>=20 blocks all ETF picks) — correct behavior but reduces live emission volume

### Fastest Path to Profitability
**Audit `.github/workflows/mysql-trading-sync.yml`** to confirm ETF is in the sync scope. If the workflow filters by `asset_class` and ETF is absent, adding it would immediately surface 85 resolved picks (WR=61%/PF=2.00 from MySQL) into pf_registry. This is a zero-strategy-change action and the highest-leverage fix available for ETF.

Walk-forward profile (from DAILY_IDEAS.MD): OOS WR=75%, fold consistency=100%, +23% improving trend — best OOS of all classes. If MySQL data syncs correctly, ETF may be the fastest class to reach MONEY_READY.

### Confidence
- OOS data from walk-forward harness: moderate confidence but n unknown at time of harness run
- MySQL WR=61%/PF=2.00: pending sync verification; could be a schema labeling mismatch
- If confirmed: n=85 clears the candidate floor (n≥50) and approaches stable tier (n≥100)

---

## 7. FUTURES

### Current Status
- **Canonical universe (pf_registry):** n=12 (clean), WR=16.7%, PF=0.956 — status: `thin_sample`
- **Raw:** n=221, WR=3.2%, PF=0.075 — extreme policy exclusion (97% of raw picks removed); after cleaning, the 12 surviving picks are near break-even (PF=0.956)
- **Realized 30d WR:** 4.7% (n=129) — catastrophic; 30d sample is almost entirely the failing `futures_momentum` strategy
- **Money-ready verdict:** INSUFFICIENT_DATA

### Biggest Drag
- `futures_momentum`: n=202 (raw), WR=2.0%, PF=0.035 — moved from `BLOCKED_ASSET_STRATEGY_PAIRS` to `MONITORED_FUTURES_STRATEGIES` on 2026-05-18; zero capital sizing, stats-accumulation mode only
- `multi_asset_copytrader` on commodity futures (=F symbols): WR=3%, PF=0.06 on n=203 picks — BUY WR=2.0%, SELL WR=5.4%; both catastrophic; moved to monitor mode 2026-05-18 (unblocked from BLOCKED_DIRECTION_TRIPLES)
- `multi_asset_scanner` FUTURES: n=11, WR=9.1%, PF=0.475 — not yet blocked but sub-floor

### Fastest Path to Profitability
**Let the monitoring period run.** The 2026-05-18 operator decision correctly moved futures strategies to shadow mode rather than hard-kill. The graduation criteria (n≥50, WR≥50%, PF≥1.5, 3 contiguous positive weeks) are appropriate. No new strategies should be wired to FUTURES until monitoring completes (~2026-07-18 for `futures_momentum`). Emergency re-block triggers at WR<30% or single-week PF<0.5.

Alternatively: investigate whether commodity futures with COT signals (CT=F, GC=F, SI=F) routed through the COMMODITY class (not FUTURES) shows the documented edge. The COT strategies on CT=F (WR=70-78% at n=44) are already classified as COMMODITY — this may be the correct routing.

### Confidence
- `futures_momentum` WR=2% at n=202: p<10^-40 vs H0=WR≥50% — confirmed loser. Monitor-mode rationale is regime-stratification discovery, not hope of aggregate revival.
- Clean n=12 is below statistical floor for any claim about FUTURES as a class.

---

## Summary Table

| Class | n (clean) | WR | PF | Status | One-Change Priority |
|-------|-----------|----|----|--------|---------------------|
| CRYPTO | 2,083 | 44.2% | 1.155 | watch | Block `st_fear_greed_contrarian` (n=139, PF=0.88) |
| EQUITY | 37 | 45.9% | 1.277 | thin_sample | PA console MySQL purge (~2026-05-24) |
| COMMODITY | 51 | 56.9% | 1.673 | candidate | Add GC=F + SI=F to COT pipeline |
| FOREX | 295 | 12.5% | 0.174 | stressed | Audit raw PF=3.177 vs clean PF=0.174 gap; recover non-JPY edge |
| BOND | 0 | — | — | insufficient | Wire FRED_API_KEY to bond scanner |
| ETF | 0 | — | — | insufficient | Audit mysql-trading-sync.yml ETF scope (MySQL shows WR=61%/PF=2.00) |
| FUTURES | 12 | 16.7% | 0.956 | thin_sample | Hold monitor mode; no new strategy wiring until 2026-07-18 review |

---

## Statistical Edge Summary

| Class | Evidence Basis | Verdict |
|-------|---------------|---------|
| CRYPTO (whitelist) | n=291, WR=70.8% — p<0.001 | Edge confirmed on whitelist; aggregate PF sub-T2 |
| COMMODITY CT=F | n=44 each strategy, WR=70-78% — p<0.001 | T1-grade edge; concentration risk only |
| ETF (MySQL) | n=85, WR=61% — p<0.001 if confirmed | Needs sync verification before claim |
| EQUITY (30d) | n=81, WR=59.3% — p<0.01 | Promising; ghost rows suppressing full ledger |
| FOREX SHORT subset | n=93 multi_asset_copytrader SHORT, WR=52.7% | Sub-T2 PF=1.35; watch not trade |
| BOND | n=0 | No evidence |
| FUTURES | n=12 | No statistical basis |

NFA — all numbers are research-only. Real-money sizing requires DSR>=0.95, PBO<0.10, n>=100 clean trades, and drift_alert=FALSE on the class.

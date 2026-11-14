# Profitability per asset class — what must be true (evidence-based)

**Context (from repo evidence):** `money_ready_verdict.json` (Nov 2026 snapshot referenced in audit files) shows **0/9 classes MONEY_READY**; `benchmark_ledger_proof.json` (Oct 2026) shows **no ledger passes 95% paired benchmark gate** (`n_pass_95 0`) in that run. “Profitability” here means: **net expectancy > 0 after realistic costs**, on **canonical OOS/walk-forward evidence**, with **multiple-testing control** and **no data-integrity lies** (units, zombies, stale prices, fabricated states).

This document gives **per-class constraints and a path**, not a promise of edge.

---

## Global prerequisites (apply to every class)
1. **One canonical closed ledger** (deduped, policy-clean): percent PnL only, clamp bounds, provenance. Remove |pnl| absurdities at write (per scratch P0). Eliminate ghost rows / spot-flicker contamination via the approved “mark, not delete” + dedup strategy noted in v2 (avoid the vetoed destructive mass deletes).
2. **Open inventory honesty:** separate `active_display` (priced, fresh, not expired/zombie) from raw backlog; do not mix EXPIRED into “active” stats.
3. **Costs and mechanics:** slippage/spread/funding/roll/commissions/dividends where applicable; intrabar-first resolution where claims are “live” (TP-before-SL bug is a known class of inflation).
4. **Multiple testing:** track how many strategies/families tested per class window; apply DSR with correct `nb_trials`, SPA/Reality Check where feasible, FDR discipline (gates were noted as disabled in places — that is a governance failure, not a feature).
5. **OOS:** walk-forward (refit/embargo as appropriate) + frozen holdout; no “in-sample is the edge” promotion.
6. **Benchmark:** paired tests vs appropriate benchmark per class/direction (regenerate after data fixes). Use `alpha_engine/benchmark_closed_ledger.py` patterns but ensure direction-aware and class-appropriate benchmarks (SPY not always right).

---

## CRYPTO
**Observed issues (synthesized from v2/v4/scratch):** large raw backlog, many zero-priced/frozen quotes in curated displays, zombie/expired leakage in raw views, fabricated flat-3% cohorts historically called out, ML leakage/gatekeeper history (default flip needs retrain/parity), intrabar vs daily PF divergence, `summary_picks` WR>100% class math bugs, policy/allowlist bypass notes (FOREX-adjacent patterns exist elsewhere) — but primary pain is **scale + data hygiene + overfitting risk** at 600+ strategies tested.

**What “profitable” would require here (minimum):**
- Resolver throughput: drain or tombstone OPEN backlog honestly (not EXPIRED in active counts).
- Canonical crypto closed set rebuilt after unit/backfill fixes; remove fabricated cohorts.
- Cost model: exchange fees, taker/maker assumptions, funding (perps) if any perps in scope, slippage bps by liquidity tier.
- Walk-forward by regime (volatility regimes) with purge/embargo; **nb_trials** must count all crypto strategy variants evaluated in the same search period.
- Benchmark: BTC-USD/ETH-USD or sector basket as appropriate (not blindly SPY). Re-run paired bootstrap + random-entry MC with direction-aware + own-symbol nulls logic as in recent benchmark tooling.
- Promotion bar: pass Charter 7 gates on rolling 90d **and** frozen OOS, with recency panels agreeing.

**Realistic near-term (plumbing-first):** kill/disable strategies that only survive because of data bugs (fabricated flats, unit errors, missing costs). Expect many “winners” to disappear — that is the point.

---

## FOREX
**Observed issues:** `summary_picks` WR>100% for FOREX historically; PR #6 allowlist/block context in peer notes showed bypass risks (cross-asset paths) and `KeyError`/direction handling bugs fixed in parts per v1 notes — **adopted patterns must not default silently to LONG** (use OTHER-bucket + log). Timestamp/date-only defects noted in v2. Closed feed had small n in some views with poor PF in policy-clean aggregates.

**Path:**
- Fix direction encoding end-to-end (no silent BUY/LONG coercion that hides unknowns); fix sync fallback paths (`sync_summary_picks_json.py` class counting) before trusting any WR.
- Enforce allowlist at the **actual** execution/pick-generation gate (not a dead helper) if FOREX is intended to be restricted; otherwise document the real tradable universe.
- Use realistic FX costs: spread + rollover/funding proxy if holding overnight, commissions if any. Many retail/FX pipelines underestimate spread impact on mean-reversion.
- Benchmark: major pairs vs buy-and-hold of base/quote is odd; prefer **flat cash benchmark** for direction signals or a simple carry-adjusted benchmark stated explicitly — document in `benchmark_closed_ledger` mapping.
- Need **n≥100** resolved clean closed picks per class promotion floor (Charter) plus OOS windows; current policy-clean aggregates were weak.

**Honest call:** FOREX is easy to make look good on paper with wrong costs/spread assumptions. Do not promote without tick/spread-aware backtests or conservative slippage stress tests.

---

## EQUITY (stocks)
**Observed issues:** v2 noted three aggregators disagreeing on EQUITY PF/WR in different windows (headline n=8 looked good vs larger negative/weak aggregates) — classic survivorship/windowing artifact. Stale prices / frozen quotes in some active displays. Classifier edge cases (mutual-fund tickers falling to equity historically noted in scratch).

**Path:**
- Single stats pipeline (one canonical closed table + one calculator) to kill the n=8-vs-n=700 disagreement.
- Use **equity-appropriate benchmarks** (SPY/sector ETFs) direction-aware; for shorts use appropriate short-borrow/cost assumptions if modeled (often ignored — be explicit).
- Data quality: split/dividend awareness if holding periods span events (scratch noted equity PnL/sign issues historically in other contexts — verify). Stock quote freshness + failover (yfinance/FMP/demo keys flagged as fragile in scratch).
- Walk-forward across regimes (bull/bear/sideways); test whether “edge” was 2020–2021 crowding.
- Target: n≥100 OOS resolved with net expectancy > 0 after commissions + slippage.

---

## ETF
**Observed issues:** frozen quotes / 50% zero-marked in raw views per v2 table; daily vs intrabar divergence can flatter (ETF daily PF looked much better than intrabar in earlier scratch findings). Intrabar truth for ETF was poor in prior audits.

**Path:**
- Intrabar-primary validation (OHLC/resolution) not daily-close fiction for “real-time” claims.
- Include **expense ratio drag** in any multi-day hold strategy PnL model (often missing).
- Benchmark SPY/IWM/sector ETFs appropriately per sleeve.
- Treat as **separate from “equities”** mechanically (fund mechanics differ) — keep classifier clean.

---

## BOND (bond ETFs/proxies context)
**Observed issues:** v2: BOND treated as bond-ETF proxies in practice (TLT/IEF style) with price-only PnL ignoring distributions in many pipelines; n very small (1 in policy-clean example shown), newest closed ages noted; effectively not a live trading edge story yet.

**Path:**
- Decide: are you trading **bond ETFs** (price+div) or true bonds? If ETFs, model **distributions** and use ETF benchmarks (TLT/IEF/AGG) with total-return thinking.
- Need **much larger n** and longer history; many bond strategies need rate-regime walk-forwards.
- Do not publish “bond edge” until intrabar/daily methodology is explicit and n≥100.

---

## FUTURES
**Observed issues:** v2 states **administratively blocked** in `audit_trail/quality_gates.py` (`BLOCKED_ASSET_CLASSES` includes FUTURES in that context) and futures PnL mechanics differ (% of price vs contract multiplier/margin, rolls/funding context). Date-only timestamps noted. Raw history small.

**Path:**
- **Unblock only with a real feed + contract specs:** multiplier, tick value, margin, roll schedule. Until then, any “FUTURES picks” are display artifacts or misclassified (scratch noted `=F` sometimes mixing with commodity logic).
- If/when unblocked, benchmark to appropriate continuous futures or cash; model costs (commission + slippage in ticks + financing).
- Requires dedicated validation harness (not reused equity %-only math blindly).

---

## COMMODITY
**Observed issues:** v2 states **administratively blocked** in the same block list context and **generator uses crypto proxies** (RNDR/ARB mapped to silver, XLM/DOT mapped to oil in the noted code path) — so labelled COMMODITY rows may have **no commodity exposure**. Also mixed with futures symbols in practice.

**Path:**
- **Do not trust current COMMODITY labels** until symbol→instrument mapping is fixed and feed is commodity-appropriate (not crypto proxies).
- After fix: model storage/roll for futures-based commodities where relevant, or ETF proxies explicitly. Costs matter (contango/backwardation effects are strategy-dependent).
- Unblock only after: (a) correct instruments, (b) real data, (c) small-n reality acknowledged (need ≥100 resolved for any promotion claim).

---

## MUTUAL FUNDS
**Observed issues:** v2: **NOT BUILT in production / not on `origin/main`** in the live product sense; untracked prototype files may exist in some checkouts. MySQL `mf_*` tables were noted frozen in older scratch context — treat as **no live managed strategy surface**.

**Path:**
- If you want MF strategies: build **EOD/NAV** pipeline (no intraday TP/SL in the same way), model loads/expense ratios/distributions, and a separate validator (not the crypto tick loop).
- Until then, **do not claim MF performance** from placeholder/prototype artifacts.
- Recommendation: **out of scope for “profitability per active class”** until a real pipeline exists; remove or clearly label any phantom UI.

---

## Cross-cutting “how to actually get profitability” (order matters)
1. **Fix truth (data + costs) before tuning alpha.** Most apparent edges in this repo’s history were artifacts (units, ghosts, survivorship, wrong costs, stale marks).  
2. **Pick 1–2 asset classes** where data plumbing is easiest (often **CRYPTO** has volume but worst hygiene; **EQUITY/ETF** may have cleaner quote plumbing but still need classifier/cost fixes) and run a **full closed-loop audit**: rebuild canonical ledger → apply costs → walk-forward → DSR/SPA/PBO with real `nb_trials` → benchmark → only then consider paper scaling.  
3. **Use the existing tools as intended:** `tools/ci_gate_money_ready_vs_registry`, `alpha_engine/money_ready_verdict.py`, `alpha_engine/benchmark_closed_ledger.py`, `alpha_engine/deflated_sharpe.py`, `alpha_engine/anti_overfit_gate.py` — but **regenerate inputs first**; do not optimize against poisoned ledgers.  
4. **Adopt a “no edge proven” default.** The repo’s own framework says 0/9 pass; treat promotion as exceptional and documented (Charter §4 checklist).

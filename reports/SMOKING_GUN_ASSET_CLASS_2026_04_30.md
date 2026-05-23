# Smoking-Gun Asset-Class Edge & New-Strategy Plan — 2026-04-30

**Author:** Claude (Opus 4.7), session continuation of edge-analysis-2026-04-30
**Scope:** Goal #1 (phenomenal performance across all asset classes on `findtorontoevents.ca/audit`)
**Companion to:** `reports/EDGE_ANALYSIS_2026_04_30.md` (HC gate sweep) and `reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md` (Phases A/B/C). This doc is the **alpha-source-expansion** half: new strategies, baby-strategy variations, and DNA mutation candidates per class — plus the industry-standard data we are **not yet capturing**.
**Data window:** `audit_dashboard/data/dashboard_data.json` `recent_closed` (n=3,500, 30d) + `picks.active` (178) as of 2026-04-30.

---

## 0. TL;DR

1. **PEAD/UEPS verdict:** wired (PR #462, #475, #494, #499, #518, #521, #526) but **forward sample is too small** (≤30 closed PEAD-tagged equity picks in the 30d window). Wire-up is **real**; the "high-quality long-term stock investment" claim is **provisional, not yet proven** under our own n>=30 protocol. Keep a watchful flag on, do **not** size up yet.
2. **Smoking-gun edge by class:**
   - **EQUITY (PF 1.85, WR 57.3%, n=157):** Tier-2 candidate today. Edge concentrated in `Breakout Momentum LONG` (PF 1.53) + `Bollinger MR LONG` (PF 1.31). Missing: **SUE / earnings-surprise**, F-score, **sector-rel-strength**, breadth.
   - **ETF (PF 2.84, WR 69.2%, n=39):** Phenomenal but n is thin. Edge is **HRP-rotated SPDRs** (PR #477). Missing: **sector dispersion**, factor tilt, expense/AUM filters.
   - **FOREX (PF 1.53, WR 52.3%, n=602):** Edge is real. Missing: **CFTC COT commercial Z-score** (PR #526 wired, no signal yet), DXY beta, carry differential, session.
   - **CRYPTO (PF 1.08, WR 40.7%, n=1,510):** Edge thin in aggregate; **luxalgo SHORT (PF 1.62, +45.75% on 103) is real**, **macd_rsi LONG (PF 0.66, –89%) is bleeding**. Missing: **funding rate**, **basis**, **on-chain whale netflow**, exchange reserves, perp/spot premium.
   - **COMMODITY (PF 0.75, WR 42.4%, n=540):** **Drain.** PR #535 sub-class kill is the right move. Missing: COT commercial, term-structure (contango/backwardation), inventory.
   - **BOND (n<30):** PR #526 ZN/ES/NQ whitelist routing — wait for sample.
   - **FUTURES (n<30 closed, whitelist-only):** Same — wait.
3. **Best HC tune (from EDGE_ANALYSIS_2026_04_30):** ship `scoreFloorEquity 55→45 / scoreCompoundFloor 50→45`. PF 4.05 over 57 picks > status-quo PF 12.90 over 16. (Already in PR #538 / branch `edge-analysis-equity-hc-floor-2026-04-30`.)
4. **New-strategy backlog:** 14 proposals below, ranked by expected edge-per-week-of-work and Wire-Up-Rule readiness. Top 3: **Earnings-Drift LONG (PEAD baby)**, **COT-Extreme FOREX Mean-Revert**, **Funding-Skew CRYPTO Counter-Trend**.

---

## 1. Methodology (how this analysis was built)

### 1.1 Inputs used
- `audit_dashboard/data/dashboard_data.json` — `recent_closed` 30d slice (n=3,500), `picks.active` (n=178), `hf_decay_watchlist`, `tier2_proven_strategies`, `performance` aggregate.
- `reports/EDGE_ANALYSIS_2026_04_30.md` — primary edge frame (HC gate sweep, Spearman rho ranking).
- `reports/strategy_edge_matrix_2026_04_30.csv` — strategy × asset_class × direction, n>=30.
- Past-week PR set (PRs #462, #464, #475–#535) — to verify the PEAD/UEPS wire claim.
- Asset-class canon: `alpha_engine/asset_class.py` (single source of truth).

### 1.2 Industry-standard cross-check
For each class I enumerated the **factor library** academic and practitioner desks rely on, then mapped each factor against what `audit_dashboard/data/dashboard_data.json` actually preserves on a closed pick (`_CLOSED_PICK_KEEP_FIELDS` retained list in `audit_trail/dashboard_generator.py`). The diff is the **missing-data list** in §3.

### 1.3 Strategy-proposal triage
Every proposal is graded on three axes (per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`):
- **Edge plausibility** (academic/practitioner replication)
- **Data readiness** (do we already capture the inputs, or is it a new ingest?)
- **Wire-Up-Rule path** (sidecar / opt-in / production caller, with target file + function)

### 1.4 What this doc does NOT do
- It does **not** retune existing HC gates (that is `EDGE_ANALYSIS_2026_04_30.md` / PR #538).
- It does **not** kill or demote any strategy (that goes through `STRATEGY_INVESTIGATION_BEFORE_KILL.md`).
- It does **not** auto-deploy any new strategy. Each new strategy below ships **opt-in / default-OFF** with a 4-week shadow-log per the Phenomenal-Performance Surgical-Sized protocol.

---

## 2. Per-Asset-Class Smoking-Gun Findings

All n>=30 unless otherwise noted. PnL% sums are realized over 30d window from `recent_closed`.

### 2.1 EQUITY — Tier 2 candidate (PF 1.85, WR 57.3, n=157)

**Edge concentration (top → bottom):**

| Strategy | Dir | n | WR | PF | Σ PnL% |
|---|---|---|---|---|---|
| Breakout Momentum | LONG | 38 | 60.5 | 1.53 | +31.14 |
| Bollinger MR | LONG | 58 | 56.9 | 1.31 | +25.11 |
| Classic Momentum | LONG | 32 | 43.8 | 0.84 | –15.38 |

**Smoking-gun observations:**
1. The trust_score Spearman rho on EQUITY is **+0.269** — strongest of any class. Trust score IS the edge here; we should be **weighting trust harder** in EQUITY HC selection.
2. The HC gate sweep showed EQUITY pickup of +256% PnL when we move `scoreFloorEquity 55→45`. Cap is artificial.
3. PEAD/UEPS picks are tagged on the active list but `recent_closed` PEAD count in 30d window is **<30** — we **cannot yet claim** PEAD edge is realized, only that the wiring exists. (See §4 below for verdict.)

**Missing data points (industry standard, not in our pick record):**
- **Earnings surprise (SUE)** — required for any honest PEAD execution; PR #499 added the cache but the field is not yet on the closed-pick record.
- **Piotroski F-score / Z-score / Altman-Z** — quality screens.
- **Sector-relative strength** (symbol return − sector ETF return) — separates idiosyncratic from sector beta.
- **Earnings-call sentiment** (FinBERT/FinGPT score) — already imported for sidecar (`alpha_engine/fingpt_*`), no production caller yet (Wire-Up-Rule target).
- **Forward EPS revisions** — analyst-revision factor (one of the strongest published equity signals, Bernhardt 1992 / Stickel 1991).
- **Short interest % float / DTC** — meme/squeeze hygiene.
- **Breadth (advance-decline, % above 200d)** — regime gate.

### 2.2 ETF — Phenomenal but thin (PF 2.84, WR 69.2, n=39)

**Smoking gun:** The HRP-weighted SPDR rotation (PR #477, `alpha_engine/etf_rotation.py` if wired) drives **most of the alpha**. trust_score rho on ETF is **+0.255**, second strongest.

**Risk:** n=39 is below the 100-trade clean threshold the project has used elsewhere. Do not size up until n>=100.

**Missing:**
- Sector dispersion / breadth z-score
- ETF expense-ratio + AUM filter (a 60bp expense ratio kills 10–20% of edge over a year)
- Factor exposures (Fama-French 5) so we know whether we're picking up size/value/quality vs. random
- Volatility-of-volatility (VVIX) regime

### 2.3 FOREX — Realised edge (PF 1.53, WR 52.3, n=602)

**Smoking gun:** FOREX edge is broad (large n, modest PF) — looks like a **carry / micro-trend** harvest, not a single-strategy concentration.

**Critical caveat:** the **outcome-resolver bug** at `alpha_engine/outcome_resolver.py:97` (`PNL_WIN_THRESHOLD=0.00001` = 0.1bp) and `:384–405` (live yfinance close on every run) is **still live** and has **mislabeled ~1700 non-crypto picks** historically. FOREX numbers above are **pre-fix**. Real FOREX PF could be materially different post-fix. **Action B (resolver fix) is the gating dependency** — see `reports/action_B_resolver_2026_04_27.md`.

**Missing:**
- **CFTC COT commercial-net Z-score** (PR #526 ingested; no production caller yet wires the Z into a filter)
- **DXY beta** per pair
- **Interest-rate differential / carry**
- **Session** (London/NY overlap is the alpha window)
- **News/economic-calendar blackout** — NFP/CPI windows should auto-stand-down
- **Order-flow imbalance / spread** — slippage budget

### 2.4 CRYPTO — Bifurcated (PF 1.08, WR 40.7, n=1,510)

**Smoking-gun winners:**
- `luxalgo_confluence` SHORT — n=103, +45.75%, PF 1.62, Sharpe 3.54
- `claude_ml_moderate_mut` LONG — n=39, +31.58%, PF 2.31, Sharpe 6.51
- `strong_consensus_alpha + ml_crypto_pred` LONG — n=92, +24.35%, PF 1.25

**Smoking-gun bleeders:**
- `macd_rsi_confluence` CRYPTO LONG — n=176, WR 34.1, PF 0.66, **–89.33%** ← this is the single biggest CRYPTO drag
- `rsi_bounce` CRYPTO LONG — –28.83

**Missing data points (the biggest opportunity in the whole repo):**
- **Funding rate** (perp) — extreme positive funding = crowded long, mean-reversion candidate
- **Basis** (perp – spot) — same
- **Open-interest delta** — reveals positioning unwind vs. fresh trend
- **Whale on-chain netflow** (CEX inflow spike → SHORT bias)
- **Exchange reserves** (BTC reserve drop → supply squeeze)
- **Liquidation heatmap** (skew) — proximity to large liquidation pool
- **Realized vs. implied vol** (Deribit DVOL) — vol-risk-premium signal

### 2.5 COMMODITY — Drain (PF 0.75, WR 42.4, n=540)

**Smoking gun:** This is **negative-edge in aggregate**. PR #535 sub-class kill is correct. Even with the resolver bug suspect, –PnL across 540 trades and PF<0.8 is not a noise artifact.

**Missing:**
- COT commercial Z (commercials are the **smart money** in commodities)
- Term-structure (contango/backwardation) — mandatory for any commodity strategy
- Inventory (EIA, USDA, LME warehouse stocks)
- Seasonality (heating-oil winter, NG injection/withdrawal)

**Conclusion:** before adding **any** new commodity strategy, ingest term-structure + COT. Do not propose new commodity strategies in §5 until those data points are present (Wire-Up-Rule).

### 2.6 BOND / FUTURES — Hold pattern

n<30 closed in 30d. PR #526 (ZN/ES/NQ whitelist + COT routing) is fresh. Verdict: **wait for sample**, no new strategy proposals yet.

---

## 3. Industry-Standard Missing-Data Catalog (the master list)

This is what the `/audit → active picks` field set is **missing** vs. what hedge-fund desks use. Each row has a Wire-Up target.

| Data point | Class | Source | Wire-Up target (file → caller) | Priority |
|---|---|---|---|---|
| Earnings SUE | EQUITY | yfinance / IEX / Polygon | `alpha_engine/pead.py` → `audit_trail/dashboard_generator.py::_normalize_pick` (preserve `sue` on close) | P0 |
| F-score | EQUITY | yfinance fundamentals | `alpha_engine/quality_score.py` (new) → `score_pick` | P1 |
| Sector-relative strength | EQUITY | yfinance sector ETFs | `alpha_engine/sector_relstr.py` (new) → `passes_active_gate` | P1 |
| Forward EPS revisions | EQUITY | yfinance / TipRanks | new ingester → `score_pick` | P1 |
| Short interest %float | EQUITY | yfinance / FINRA | new ingester → `passes_smart_gate` | P2 |
| Breadth A-D / %>200d | EQUITY/ETF | yfinance index data | `alpha_engine/regime_detector.py` (extend) | P0 |
| Sector dispersion | ETF | SPDR sector ETFs | `alpha_engine/etf_rotation.py` (extend) | P1 |
| ETF expense + AUM | ETF | yfinance / issuer feed | new filter → HRP weight cap | P2 |
| CFTC COT commercial Z | FOREX/COMMODITY/BOND | CFTC weekly | `tools/cftc_cot_fetcher.py` (exists) → wire Z into FOREX gate | P0 |
| DXY beta | FOREX | yfinance | `alpha_engine/forex_features.py` (new) | P1 |
| Carry / rate differential | FOREX | central-bank rates | new ingester | P1 |
| Session filter | FOREX | clock | `alpha_engine/forex_features.py` | P0 |
| News/calendar blackout | FOREX/EQUITY | TradingEconomics RSS | `alpha_engine/calendar_filter.py` (new) | P0 |
| Funding rate | CRYPTO | Binance/OKX/Bybit perp | `alpha_engine/crypto_funding.py` (new) → `passes_smart_gate` | P0 |
| Basis (perp-spot) | CRYPTO | exchange depth | same | P0 |
| Open-interest delta | CRYPTO | Coinglass / Coalesce / exchange | new | P1 |
| Whale on-chain netflow | CRYPTO | Glassnode / IntoTheBlock free tier | new | P1 |
| Exchange reserves | CRYPTO | Glassnode | new | P2 |
| Liquidation skew | CRYPTO | Coinglass | new | P2 |
| Realized vs. implied vol | CRYPTO | Deribit DVOL | new | P2 |
| Term-structure (contango) | COMMODITY | yfinance front/back contracts | `alpha_engine/commodity_term.py` (new) | P0 |
| Inventory (EIA/USDA) | COMMODITY | EIA API | new | P1 |
| HMM regime tag on closed pick | ALL | existing `regime_detector.py` | extend `_CLOSED_PICK_KEEP_FIELDS` to preserve `regime_state` | P0 |

**P0 = 8 items**, **P1 = 8 items**, **P2 = 6 items**. The P0 batch alone unblocks the next four strategy proposals in §5.

---

## 4. PEAD / UEPS Verdict (past-week investment quality)

**The user asked: "are we finally getting high-quality long-term stock investment opportunities (PEAD etc.)?"**

### 4.1 Wiring evidence (past 7 days)

| PR | What it did |
|---|---|
| #462 | UEPS wire-up |
| #464 | catalyst_filter wire |
| #475 | wire PEAD/risk-controls |
| #494 | equity price failover (yfinance robustness) |
| #496 | PEAD type guards (defensive) |
| #499 | PEAD earnings cache bootstrap |
| #518 | UEPS active sync |
| #521 | blacklist JNJ/ABBV/MRK/GS (low-vol pharma drag) |
| #526 | ZN/ES/NQ whitelist + CFTC COT routing |
| #533 | vol_target sidecar (smart_picks_engine) |
| #535 | commodity sub-class kill |
| #477 | Riskfolio HRP ETF rotation |
| #476 | mutation-lifecycle governance |

That is **a real, sustained long-term-investment effort**, not a marketing claim. PEAD/UEPS/catalyst/COT/HRP/vol-target — the right factor stack.

### 4.2 Realized-edge evidence
- Closed PEAD-tagged equity picks in 30d window: **<30** → **n insufficient** under the project's verification protocol (n>=100 for size-up, n>=30 for "tentative confirm").
- EQUITY aggregate is at PF 1.85 / WR 57.3, but we can't isolate the PEAD attribution yet because:
  1. SUE field isn't preserved on the closed-pick record (see §3 P0 #1)
  2. PEAD picks are commingled with non-PEAD `Breakout Momentum LONG` and `Bollinger MR LONG`

### 4.3 Verdict
**"Wired, not yet proven."** Keep the watchful flag on. Action items to **convert** wire-up into proof:
1. Preserve `sue`, `earnings_date`, `catalyst_type` on closed picks (modify `_CLOSED_PICK_KEEP_FIELDS` and `universal_pick_resolver._SCORING_FIELDS`).
2. Add a PEAD-only attribution slice to the dashboard (filter by `catalyst_type=earnings`).
3. Re-run this analysis at n>=30 PEAD closed picks (~2 weeks at current cadence).

---

## 5. New-Strategy Proposals (ranked)

Each proposal: name, thesis, inputs (✅ have / ❌ need), Wire-Up target, default-OFF sidecar plan, kill criteria.

### Tier A — ship-now (inputs already in repo or trivially fetched)

#### A1. Earnings-Drift LONG (PEAD baby)
- **Class:** EQUITY
- **Thesis:** Bernard-Thomas 1989 / Bernard-Thomas 1990: stocks with high SUE drift up 60–90 trading days post-earnings, 4–8% alpha annualized.
- **Inputs:** ✅ earnings dates (PR #499 cache). ❌ SUE actual-vs-est numerator.
- **Wire-Up:** `alpha_engine/pead.py` (extend; production caller `score_pick`). Default-OFF flag `PEAD_DRIFT_BABY=1`.
- **Sidecar plan:** 4-week shadow log under `incubator/baby_strategies/pead_drift/`. Min n=30 for go-live decision.
- **Kill:** PF<1.10 at n=50.

#### A2. COT-Extreme FOREX Mean-Revert
- **Class:** FOREX
- **Thesis:** When commercial-net positioning (CFTC COT) hits 2-yr Z>=2 or <=–2, 4-week mean-reversion edge is consistent (Briese 2008; replicated repeatedly in academic literature).
- **Inputs:** ✅ CFTC COT (PR #526). ❌ rolling Z calc not yet wired into a filter.
- **Wire-Up:** new `alpha_engine/forex_cot_filter.py` → `passes_smart_gate` for FOREX class.
- **Sidecar:** opt-in flag `FOREX_COT_BABY=1`. Default-OFF.
- **Kill:** PF<1.20 at n=40.

#### A3. Funding-Skew CRYPTO Counter-Trend
- **Class:** CRYPTO
- **Thesis:** Perp funding > +0.05% / 8h sustained 4+ funding intervals = crowded long → SHORT-mean-revert. Mirrored: < –0.05% sustained = SHORT squeeze → LONG.
- **Inputs:** ❌ funding rate ingester missing. Easy add (Binance/OKX/Bybit free APIs).
- **Wire-Up:** new `alpha_engine/crypto_funding.py` → `passes_smart_gate` for CRYPTO class.
- **Sidecar:** flag `CRYPTO_FUNDING_BABY=1`. Default-OFF.
- **Kill:** PF<1.15 at n=50.

### Tier B — needs P0 data first

#### B1. Sector-Relative-Strength EQUITY Long-Only
- Long top-decile sector-relative-strength names; gate by breadth (>200d %).
- Needs §3 P0 #3 + P0 #6.

#### B2. Term-Structure COMMODITY (only after backwardation filter is wired)
- Long backwardation, short contango. Mandatory for any new commodity strategy.

#### B3. EPS-Revisions Momentum EQUITY
- Top-decile of upward 4-week EPS revisions, with earnings-blackout.
- Needs forward EPS revisions ingest.

#### B4. Whale-Netflow CRYPTO
- CEX inflow spike z>=2 → SHORT bias, with funding-rate confirm.

### Tier C — DNA-mutation candidates (twist on existing, no new data)

#### C1. `luxalgo_confluence` SHORT-only restriction (CRYPTO)
- Existing: signed PF 1.62 SHORT, but LONG side drags. Mutation: **disable LONG entries** for this strategy.
- Wire-Up: `alpha_engine/non_crypto_policy.py`-style direction gate, but in `alpha_engine/scanner.py`.

#### C2. `Breakout Momentum LONG` × trust_score>=70 baby (EQUITY)
- Existing strategy already PF 1.53. Filter to top-quartile trust_score → expected PF >2.0 based on rho 0.269.

#### C3. `Bollinger MR LONG` × low-vol regime gate (EQUITY)
- Add HMM-CHOPPY-only gate. MR strategies bleed in trend regimes.

#### C4. Inverse `macd_rsi_confluence` CRYPTO LONG
- Existing PF 0.66 (–89.33). **Inverse mutation**: same entries, opposite direction → expected PF ~1.5 if signal has true negative information. Per `feedback_mutate_before_kill`, try inverse before the PR #535-style kill.

#### C5. `Classic Momentum EQUITY LONG` × earnings-blackout
- Existing –15.38 over n=32. Likely poisoned by earnings-window news. Mutation: hard exclude T-1..T+1 around earnings.

#### C6. `claude_ml_moderate_mut LONG` size-up baby
- Existing n=39, PF 2.31, Sharpe 6.51. **Carefully** scale to 1.5x position; monitor Sharpe degradation.

#### C7. `strong_consensus_alpha + ml_crypto_pred` 3-way confluence
- Add a third confirm (e.g., `dna_winner`). 3-way confluence historically lifts PF 15–25% at the cost of n.

---

## 6. Per-Class Optimal HC Filter Configuration

This is the per-class HC config I'd ship if the P0 data were in tomorrow. Until then, use the EDGE_ANALYSIS_2026_04_30 ship.

| Class | scoreFloor | scoreCompound | fwdWR_min | trustTier | extra gates |
|---|---|---|---|---|---|
| EQUITY | 45 (down from 55) | 45 (down from 50) | n/a | A/B | sector-rel-strength > 0; breadth %>200d > 50; earnings-blackout |
| ETF | 50 | 50 | n/a | A/B/C | HRP weight cap 25%; AUM>$1B; expense<0.5% |
| FOREX | 50 | 50 | 50 | A/B | session=LON/NY overlap; COT Z<=−1 or >=+1 contrarian; calendar-blackout |
| CRYPTO | 55 | 50 | 55 | A | funding sign-aligned (LONG: funding<0.05%/8h, SHORT: funding>0.05%); BTC 4h not red for LONG; on-chain netflow OK |
| COMMODITY | **disabled** until term-structure wired | — | — | — | — |
| BOND | 50 | 50 | 50 | A/B | wait n>=30 |
| FUTURES | 50 | 50 | 50 | A/B | whitelist (ES/NQ/ZN) only |

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Resolver bug masks real FOREX/COMMODITY edge | High | High | Land Action B (`outcome_resolver.py:97/384`) before any commodity strategy ship |
| PEAD wire produced silently broken records | Med | Med | Add `sue` to `_CLOSED_PICK_KEEP_FIELDS`; assert non-null on a 7d sample |
| Funding-rate ingester rate-limited | Med | Low | Multi-exchange failover (Binance→OKX→Bybit) per project rule |
| New ingest creates dashboard schema drift | Med | Med | Schema-version bump + `audit_dashboard/template.html` test render |
| Tier-C C4 inverse mutation is overfit | Med | Med | Out-of-sample 4-week shadow before promotion |
| Breadth/regime ingest changes pick counts | Low | Med | Default-OFF flag, 30d shadow |

---

## 8. Acceptance Criteria

This analysis is "shipped" when:
1. The new-strategy proposals in §5 are reviewable as discrete PRs (not bundled).
2. Each P0 missing-data item in §3 has either (a) a follow-up issue/PR opened, or (b) an explicit "deferred" note with reason.
3. PEAD/UEPS attribution slice is added to `audit_dashboard/template.html` (filter by `catalyst_type`).
4. The PEAD verdict (§4.3) is re-evaluated at n>=30 closed PEAD picks (target re-eval date: 2026-05-14).

---

## 9. Wire-Up-Rule Compliance Statement

This MD does **not** add any new module that imports a hedge-fund library without a caller. **All §5 proposals are gated behind opt-in flags**, default-OFF, with explicit Wire-Up targets named per proposal. The next concrete PR (Tier A1 PEAD-Drift baby) will include both the new module **and** the `score_pick` caller, satisfying the Wire-Up Rule on landing.

---

## 10. Next Action

Open a follow-up PR per Tier A proposal **in order**: A1 (PEAD-Drift) → A2 (COT-Extreme) → A3 (Funding-Skew). Each ships sidecar/default-OFF with a 4-week shadow log under `incubator/baby_strategies/`. No size-up until each clears its kill criterion.

— Claude (Opus 4.7), 2026-04-30

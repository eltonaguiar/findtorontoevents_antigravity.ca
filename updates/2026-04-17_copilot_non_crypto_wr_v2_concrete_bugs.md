# Non-Crypto WR &lt; 50 % — Concrete Bugs &amp; Data-Trust Audit (v2)

**Agent:** GitHub Copilot (Claude Opus 4.6)
**Date/Time:** 2026-04-17 05:30 UTC
**Extends:** `updates/2026-04-17_00-40_antigravity_profit_factor_trust_investigation.md` (Antigravity v1 — mechanism-level analysis)
**Key commit under review:** `64506fe56d` (forex TP/SL widening, commodity score-floor fix, confidence cap)

---

## 0. Executive Summary

Antigravity's v1 doc correctly identified the five mechanism-level reasons the
reported profit factors are untrustworthy (tiny N, flat-pick accounting, stale
data, outlier bias, overfitting).  This v2 extends with **concrete, code-verified
bugs** and **dashboard_data.json-verified numbers** (generated 2026-04-17T04:24 UTC).

**Bottom line:** The dashboard itself reports **two contradictory sets of numbers**
for every non-crypto asset class.  Until that is resolved, no single WR or PF
figure can be trusted for capital-allocation decisions.

---

## 1. The Dashboard Disagrees With Itself (Bug #1 — Data Integrity)

`dashboard_data.json` contains two independent rollups of the same picks:

| Section | Code path | Forex closed | Forex wins | Forex WR |
|---------|-----------|-------------|------------|----------|
| `summary.non_crypto_performance` | `compute_non_crypto_performance()` — line 10419 | **785** | **216** | **27.5%** |
| `performance.by_asset_class` | inline loop — line 11106 | **1,185** | **402** | **45.1%** |

**Root cause (two bugs compounding):**

1. **Different input populations.** `non_crypto_performance` is recomputed at line
   13025 with the *post-gate, post-conflict* active/closed lists (final_active_picks
   + recent_closed).  `by_asset_class` at line 11106 uses the *pre-gate*
   `active + closed` lists.  The 400-pick delta represents picks filtered out by
   quality gates, blocked strategies, or conflict-minority drops.

2. **Different WR formulas.**
   - `non_crypto_performance`: `wins / (wins + losses + flat)` — flat trades
     **dilute** WR.  Forex has 326 flats out of 785, pulling WR down to 27.5%.
   - `by_asset_class`: `wins / (wins + losses)` — flat trades (pnl == 0)
     **silently excluded** from both numerator and denominator.  Forex: 402 W +
     490 L = 892 decided; 1,185 − 892 = 293 flats hidden.

Every non-crypto asset class is affected:

| Asset | `non_crypto_perf` WR | `by_asset_class` WR | Gap |
|-------|---------------------|---------------------|-----|
| FOREX | 27.5% | 45.1% | +17.6 pp |
| EQUITY | 47.4% | 52.0% | +4.6 pp |
| COMMODITY | 25.6% | 40.2% | +14.6 pp |
| ETF | 44.4% | 48.4% | +4.0 pp |
| BOND | 47.1% | 50.0% | +2.9 pp |

**Which set does the user see?**  The dashboard's "Asset Allocation" tab reads
`performance.by_asset_class`.  The "Non-Crypto" badge/panel reads
`summary.non_crypto_performance`.  They show different WR for the same asset
class on the same page.

---

## 2. Verified Numbers From dashboard_data.json (2026-04-17T04:24 UTC)

### 2a. `performance.by_asset_class` (pre-gate, flat-excluded WR, contains PF)

| Asset | Closed | Wins | Losses | WR% | Avg Win | Avg Loss | PF | PnL% | Expectancy |
|-------|--------|------|--------|-----|---------|----------|----|------|------------|
| **EQUITY** | 721 | 179 | 165 | 52.0 | 4.30 | 3.36 | **1.39** | +214.70 | +0.62 |
| **FOREX** | 1,185 | 402 | 490 | 45.1 | 0.88 | 2.73 | **0.26** | −982.14 | −1.10 |
| **COMMODITY** | 420 | 162 | 241 | 40.2 | 0.55 | 0.33 | **1.14** | +10.64 | +0.02 |
| **ETF** | 74 | 30 | 32 | 48.4 | 2.40 | 2.63 | **0.86** | −12.14 | −0.20 |
| **BOND** | 17 | 8 | 8 | 50.0 | 0.95 | 0.59 | **1.60** | +2.84 | +0.18 |
| *CRYPTO (ref)* | *18,818* | *6,564* | *7,590* | *46.4* | *3.40* | *2.50* | *1.18* | *+3,343* | *+0.24* |

### 2b. `performance.asset_class_health`

| Asset | Status | Resolved N | WR | PF |
|-------|--------|-----------|-----|-----|
| EQUITY | stable | 344 | 52.0 | 1.39 |
| FOREX | **stressed** | 892 | 45.1 | 0.26 |
| COMMODITY | **watch** | 403 | 40.2 | 1.14 |
| ETF | **watch** | 62 | 48.4 | 0.86 |
| BOND | **thin_sample** | 16 | 50.0 | 1.60 |
| FUTURES | insufficient_data | 0 | — | — |

### 2c. User-reported PFs vs. actual dashboard values

| Asset | User-reported PF | Dashboard PF | Match? |
|-------|-----------------|--------------|--------|
| Stocks/Equity | 1.47 | **1.39** | Close but not exact |
| Forex | 1.11 | **0.26** | **WILDLY DIFFERENT** — off by 4.3× |
| Commodities | 1.18 | **1.14** | Close |
| ETFs | 0.86 | **0.86** | Match |
| Bonds | 1.60 | **1.60** | Match |

The user's "Forex PF 1.11" does **not** appear anywhere in the current dashboard
data.  Forex PF is 0.26 — the system **loses $3.86 for every $1 it makes** on
forex.  If 1.11 was observed earlier, it may have been from a snapshot before
the 1,185 picks accumulated, or from a different dashboard section that no longer
exists.

---

## 3. Forex Is Catastrophically Broken (Bug #2 — R:R Inversion)

Forex has the most alarming profile:

- **PF = 0.26** (gross profit $353.8 / gross loss $1,337.7)
- **Avg win = 0.88%** vs **avg loss = 2.73%** → R:R = 0.32 : 1 (inverted)
- **PnL = −982.14%** across 1,185 closed picks
- Status: **stressed** in asset_class_health

The `64506fe56d` commit widened forex TP/SL from (−0.2%, +0.3%) to (−0.5%, +0.75%).
The prior 23 trades at the tight settings showed 4.3% WR (22 SL hits).  But the
wider settings haven't accumulated enough post-fix trades yet — only 4 active
forex picks exist.

**The structural problem** (confirmed in code at `dashboard_generator.py:11130`):
Forex losses average 2.73% while wins average only 0.88%.  This means forex
picks are hitting SL at the full stop distance but only capturing partial TP —
consistent with daily-bar resolution missing intraday TP touches while still
recording the wider SL hits.

---

## 4. Commodity PF 1.14 Is a Micro-Penny Illusion (Bug #3)

Commodity looks marginally profitable (PF 1.14, +10.64% total PnL), but:

- **Avg win = $0.55%** and **avg loss = $0.33%**
- 162 wins × 0.55% = +89.1% gross profit
- 241 losses × 0.33% = −79.5% gross loss
- **Win rate is only 40.2%** (more losses than wins)

The average trade sizes are **abnormally small** — one-fifth to one-tenth of
crypto or equity averages.  This is consistent with commodity TP/SL being set
too tight (NON_CRYPTO_TP_SL_CAPS in `non_crypto_policy.py`: 3.0% TP / 2.0% SL)
combined with the same daily-bar resolution problem.  The system records
many micro-wins and micro-losses, and the PF > 1 survives only because the avg
win slightly exceeds the avg loss.  Any broker slippage or commission
(ASSET_CLASS_CONFIG in `adaptive_stops.py`: 0.15% commission + 0.04% slippage
= 0.19% per round-trip) would **erase** the 0.02% expectancy entirely.

---

## 5. Equity Is the Only Non-Crypto With a Real Signal (Qualified)

Equity: PF 1.39, WR 52.0%, +214.70% total PnL, expectancy +0.62%.

**Why it's qualified, not confirmed:**

1. **721 closed picks but only 344 "resolved" in health check** — nearly half
   the picks are excluded by `_is_valid_resolved_pick()` (filtering stale
   snapshots, blocked rows, data corruption).  The 52% WR is computed on the
   **pre-filter** population; the health check uses the same WR because it
   reads `ac_breakdown`, not `non_crypto_performance`.

2. **`non_crypto_performance` shows equity at 386 closed, 47.4% WR** — 335
   fewer picks and 4.6 pp lower WR.  The flats (13) are small here, so
   the gap is mainly from the different input populations.

3. **The avg win (4.30%) vs avg loss (3.36%)** gives a decent 1.28:1 R:R,
   which is credible for multi-day equity swing trades.  This is the healthiest
   non-crypto profile.

4. **Concentration risk unknown** — the dashboard doesn't break out top-symbol
   concentration per asset class.  A single equity outlier (e.g. NVDA or TSLA
   in a trend) could dominate the +214.70% total PnL.

---

## 6. Bond PF 1.60 — Tiny N Confirmed

As Antigravity's v1 flagged: 17 closed, 8W/8L/1 flat, resolved N = 16.

- Health status: **thin_sample** (below min_stable_n = 50)
- PF 1.60 from just 8 winning trades: $7.60 gross profit / $4.72 gross loss
- **One bad trade (−2%) would flip PF below 1.0**
- No active bond picks; no active bond strategies in baby_strategies/

This PF is statistically meaningless.  Antigravity's v1 "Enforce N ≥ 50" rec
applies directly.

---

## 7. ETF PF 0.86 — Confirmed Negative Edge

74 closed, 30W/32L, PF 0.86, −12.14% total PnL.

- Health status: **watch** (resolved N = 62, barely above min_stable_n = 50)
- All ETF strategies on probation per `non_crypto_policy.py`
- Expectancy: −0.20% per trade
- **ETF is the only non-crypto class where the PF < 1.0 claim is consistent
  across both dashboard sections**

---

## 8. Flat-Trade Inflation (Bug #4 — Forex/Commodity Specific)

| Asset | Flats (non_crypto_perf) | % of closed |
|-------|------------------------|-------------|
| FOREX | 326 | 41.5% |
| COMMODITY | 183 | 42.3% |
| EQUITY | 13 | 3.4% |
| ETF | 3 | 4.8% |
| BOND | 1 | 5.9% |

Forex and commodity have **40%+ flat rates** — nearly half of all picks expire
at approximately zero PnL.  These are picks that:
- Never triggered (entry price never reached)
- Expired within the 48-hour time gate at roughly the same price
- Had TP/SL so tight that the resolver recorded 0% movement

The `_outcome_bucket_from_pnl()` function classifies picks as flat when
`|pnl| ≤ threshold`.  With commodity avg moves of 0.33-0.55%, many trades
land in the flat zone.

**Impact on trust:** The `by_asset_class` section hides these flats entirely,
making forex look like a 45% WR system.  The `non_crypto_performance` section
includes them, showing the real 27.5%.  Neither is wrong per se, but showing
**both on the same dashboard without labeling the methodology** destroys trust
in all displayed numbers.

---

## 9. TP/SL Config Fragmentation (Bug #5 — Code-Level)

Three independent files set TP/SL for non-crypto, with no single source of truth:

| File | Forex SL | Forex TP | Authority |
|------|----------|----------|-----------|
| `alpha_engine/config.py` CATEGORY_RISK | −0.5% | +0.75% | Scanner entry generation |
| `alpha_engine/non_crypto_policy.py` NON_CRYPTO_TP_SL_CAPS | 0.4% | 0.5% | Post-generation cap enforcement |
| `alpha_engine/adaptive_tp_sl.py` ASSET_CLASS_CONFIG | ATR×1.2 SL / ATR×2.0 TP | ATR-based, separate from % caps | Adaptive stop computation |

**The conflict:** `config.py` now says TP = 0.75%, but `non_crypto_policy.py`
caps TP at 0.5%.  If both are applied sequentially, the policy cap **overrides**
the config fix from commit `64506fe56d`, silently reverting the wider TP.
This needs code-path verification — the forex TP/SL widening may not actually
be taking effect.

---

## 10. Probation Gate Blocks 44 Non-Crypto Picks (Confirmed)

From `summary.probation_quarantine`:
```
non_crypto_probation_filtered: 44
```

44 non-crypto picks were generated by the scanner but **blocked by probation
gates** before reaching the active feed.  With only 14 non-crypto active picks
surviving, the probation filter removes **~76% of non-crypto supply**.

This is by design (strategies must prove themselves), but it means the dashboard's
non-crypto metrics are computed on the **survivors of heavy selection bias** —
not a representative sample of what the strategies actually produce.

---

## 11. Data Trust Verdict Per Asset Class

| Asset | PF | WR | N (resolved) | Trust Level | Key Blocker |
|-------|----|----|-------------|-------------|-------------|
| **EQUITY** | 1.39 | 52.0% | 344 | **CAUTIOUS** | Two dashboard views disagree by 335 picks; concentration risk unknown |
| **FOREX** | 0.26 | 45.1% | 892 | **DO NOT TRUST** | R:R inverted (0.32:1); −982% total PnL; config/policy TP conflict |
| **COMMODITY** | 1.14 | 40.2% | 403 | **DO NOT TRUST** | Micro-penny trades; 0.02% expectancy wiped by 0.19% commission |
| **ETF** | 0.86 | 48.4% | 62 | **WEAK — confirmed negative** | All strategies on probation; PF < 1 confirmed |
| **BOND** | 1.60 | 50.0% | 16 | **DO NOT TRUST** | N = 16; no active strategies; one trade flips PF |

---

## 12. Recommendations (Extending Antigravity v1)

Antigravity's three recommendations (enforce N ≥ 50, migrate data feeds,
standardize metrics) remain valid.  Adding concrete bugs:

### Must-fix (data integrity)

1. **Unify WR formula across both rollup sections.**  Pick one definition
   (recommended: `wins / (wins + losses)` with flat count shown separately)
   and apply it in both `compute_non_crypto_performance()` and the inline
   `ac_breakdown` loop.

2. **Unify input populations.**  Either both sections use post-gate picks
   (showing what the system actually recommends) or pre-gate picks (showing
   raw strategy output).  Displaying both without labels misleads users.

3. **Resolve forex TP/SL config conflict.**  Verify whether `non_crypto_policy.py`
   NON_CRYPTO_TP_SL_CAPS (0.5% TP) overrides `config.py` CATEGORY_RISK
   (0.75% TP) at runtime.  If yes, commit `64506fe56d`'s forex fix is
   partially nullified.

### Should-fix (metric credibility)

4. **Display N and confidence intervals alongside PF.**  A PF of 1.60 on N=16
   has a 95% CI of roughly [0.5, 4.8] — showing the point estimate alone is
   misleading.

5. **Add per-asset-class commission/slippage to PnL.**  Commodity's +0.02%
   expectancy and forex's −1.10% expectancy are both computed **before**
   the 0.19% and 0.03% round-trip costs defined in `adaptive_stops.py`
   ASSET_CLASS_CONFIG.  Post-commission expectancy should be the displayed
   metric.

6. **Surface flat rate as a first-class metric.**  Forex/commodity 40%+ flat
   rates signal a fundamental execution problem (picks never triggering or
   TP/SL too tight for the instrument's volatility).

---

## Appendix: Source References

| File | Lines | What |
|------|-------|------|
| `audit_trail/dashboard_generator.py` | 10419–10500 | `compute_non_crypto_performance()` — flat-inclusive WR |
| `audit_trail/dashboard_generator.py` | 11106–11157 | `ac_breakdown` inline loop — flat-exclusive WR |
| `audit_trail/dashboard_generator.py` | 13023–13027 | Recompute non_crypto_perf with post-gate lists |
| `alpha_engine/config.py` | 162–173 | CATEGORY_RISK forex: SL −0.5%, TP +0.75% |
| `alpha_engine/non_crypto_policy.py` | 142–156 | NON_CRYPTO_TP_SL_CAPS forex: TP 0.5%, SL 0.4% |
| `alpha_engine/adaptive_tp_sl.py` | 75+ | ASSET_CLASS_CONFIG commission/slippage per class |
| `audit_dashboard/data/dashboard_data.json` | — | Generated 2026-04-17T04:24:31 UTC |

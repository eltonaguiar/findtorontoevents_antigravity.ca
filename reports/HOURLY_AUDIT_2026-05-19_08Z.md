# Hourly Audit — 2026-05-19 08Z

**Generated:** 2026-05-19T08:00Z  
**Dashboard snapshot:** 2026-05-19T06:56:27Z (stale — hourly cron not yet visible; same data as 07Z)  
**recent_closed:** n=3,500  
**Mutation analysis:** `python3 tools/mutation_analysis.py --json` (full output §5)

---

## §1 Dashboard Refresh Status

Dashboard `generated_at` remains **2026-05-19T06:56:27Z** — same as the 07Z audit snapshot.  
Expected refresh at ~07:56Z has not yet propagated to origin/main at time of this audit.  
All metrics below are computed on the 06:56Z snapshot with time-window cutoffs shifted +1h vs 07Z.

---

## §2 Per-Asset Metrics (24h / 7d / 30d)

Baseline reference: CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87 / 30d 1.41–2.18; FOREX 7d 0.14 / 30d 0.97 (pre-#687).

| Class     | 24h PF | 24h WR% |  24h n | 7d PF  | 7d WR% |  7d n | 30d PF | 30d WR% | 30d n |
|-----------|-------:|--------:|-------:|-------:|-------:|------:|-------:|--------:|------:|
| CRYPTO    |  1.460 |    57.1 |    254 |  1.050 |   44.6 | 1,036 |  1.272 |    46.3 | 2,902 |
| EQUITY    |  0.000 |     0.0 |      5 |  0.238 |   13.3 |    15 |  1.939 |    50.5 |    95 |
| FOREX     |  1.246 |    37.5 |      8 |  1.295 |   31.6 |    19 |  2.532 |    48.4 |    93 |
| COMMODITY |  0.000 |    16.7 |      6 |  0.193 |   13.0 |    23 |  1.747 |    54.4 |    57 |
| ETF       |  1.887 |    11.1 |      9 |  0.989 |   25.0 |    20 |  2.005 |    57.1 |    49 |
| FUTURES   |      — |       — |      0 |      — |      — |     1 |      — |       — |     2 |
| BOND      |      — |       — |      0 |      — |       — |    0 |      — |       — |     0 |

### Deltas vs 07Z

| Class  | Window | 07Z   | 08Z   | Delta  | Note |
|--------|--------|-------|-------|--------|------|
| CRYPTO | 24h PF | 1.386 | 1.460 | +0.074 | window shift (+1h excludes older picks) |
| CRYPTO | 7d PF  | 1.045 | 1.050 | +0.005 | stable |
| CRYPTO | 30d PF | 1.272 | 1.272 | =      | stable |
| EQUITY | 7d PF  | 0.238 | 0.238 | =      | same snapshot |
| FOREX  | 7d PF  | 1.295 | 1.295 | =      | same snapshot |
| FOREX  | 30d PF | 2.532 | 2.532 | =      | same snapshot |
| COMMODITY | 7d PF | 0.193 | 0.193 | =   | cftc_cot legacy aging out |
| ETF    | 7d PF  | 0.989 | 0.989 | =      | stable |

### Signal interpretations

- **CRYPTO 24h** 1.460 / WR 57.1%: positive trend intact. 7d window at 1.050 confirms the post-#694 HYPEUSDT block still holds without major adverse impact on PF.
- **EQUITY 7d** 0.238 / n=15: unchanged, below n=20 kill floor for any individual strategy. Issue #693 protocol (monitor until n≥20 or 14d PF stays <1.0 for 14 days post-#692) remains active. 30d PF 1.939 unaffected.
- **FOREX 7d** 1.295 / WR 31.6%: recovery holding for 4th+ consecutive audit. PRs #687+#692 confirmed effective. 30d PF 2.532 is highest-PF class over 30d.
- **COMMODITY 7d** 0.193: still driven by `cftc_cot_commercial_signal` legacy (n=18, WR=5.6%, pre-#683 kill). Will age out in ~5 remaining days. 30d PF 1.747 / WR 54.4% is T2-eligible; no action.
- **ETF 7d** 0.989 / n=20: borderline. 30d PF 2.005 / WR 57.1% healthy. Too small a 7d sample to action.
- **FUTURES**: n=1 in 7d, n=2 in 30d — kill confirmed dormant.

---

## §3 Strategy Breakdown (7d)

### CRYPTO (7d, top 10 by volume)

| Strategy                                        |   n | WR%  | PF    | Status |
|-------------------------------------------------|----:|-----:|------:|--------|
| luxalgo_confluence                              | 191 | 44.5 | 1.113 | stable |
| st_fear_greed_contrarian                        | 181 | 67.4 | 3.081 | elite |
| unknown                                         | 166 | 30.1 | 1.061 | watch |
| strong consensus (alpha_engine, ml_crypto_pred) | 109 | 45.9 | 0.980 | stable |
| claude_ml_moderate_mut                          |  46 | 50.0 | 1.675 | solid |
| ensemble                                        |  31 | 19.4 | 0.279 | **KILL CANDIDATE** (FINDING-1) |
| crypto_mtf_ema_slope_alignment_v1               |  20 | 30.0 | 0.465 | **MONITOR** (FINDING-9) |
| signal_engine_momentum_mut                      |  18 | 33.3 | 0.828 | watch |
| multi_period_rsi_confluence_eth                 |  18 | 50.0 | 0.544 | stable |
| keltner_compression_expansion_eth_v1            |  17 | 29.4 | 0.858 | n<20 |

### EQUITY (7d)

All strategies n<20 — no kill actions. 30d PF 1.939 healthy.

### FOREX (7d)

| Strategy               |  n | WR%  | PF    |
|------------------------|---:|-----:|------:|
| ig_contrarian_sentiment|  8 | 37.5 | 1.390 |
| unknown                |  8 | 37.5 | 1.253 |
| MeanReversionBB        |  3 |  0.0 | 0.000 |

FOREX 7d n=19 total — all strategies n<20. Recovery confirmed.

### COMMODITY (7d)

| Strategy                   |  n | WR%  | PF    |
|----------------------------|---:|-----:|------:|
| cftc_cot_commercial_signal | 18 |  5.6 | 0.133 |
| futures_momentum           |  5 | 40.0 | 0.771 |

`cftc_cot_commercial_signal` n=18 — below n=20 kill floor, and cause is known (pre-#683 legacy trades aging out). `futures_momentum` n=5 — too small.

---

## §4 Kill Candidates & New Findings

### Confirmed kill candidates (unchanged from 07Z, awaiting 3-AI consensus)

| Candidate | n | WR% | PF | Type | Hours since first flag |
|---|---|---|---|---|---|
| CRYPTO/`ensemble` | 31 | 19.4% | 0.279 | Axis-0 full kill | ~3h (FINDING-1, 05Z) |
| CRYPTO/`crypto_mtf_ema_slope_alignment_v1` | 20 | 30.0% | 0.465 | Monitor only | ~2h (FINDING-9, 07Z) |

**No new PF<0.5 + n≥20 aggregate kill candidates emerged this cycle.**

### Mutation Axis-1 direction-block candidates (unchanged, awaiting 3-AI consensus)

| Strategy | Dir | n | WR% | Opp WR% | Spread | Status |
|---|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 200 | 16.5% | 60.3% | 44pp | P1 block |
| `myfxbook_retail_contrarian` | LONG | 124 | 13.7% | 50.0% | 36pp | P1 block |
| `quan_engine_swing` | LONG | 104 | 26.0% | 60.0% | 34pp | P1 block |
| `forex_rsi2_mean_reversion` | LONG | 117 | 6.8% | 34.8% | 28pp | P1 block |
| `cta_cross_asset_tsmom` | LONG | 85 | 29.4% | 53.0% | 24pp | monitor |

### Mutation Axis-3 symbol-block candidates (unchanged, awaiting 3-AI consensus)

| Strategy | Symbol | n | WR% |
|---|---|---|
| `rapid_fire` | UUSDT | 34 | 0.0% |
| `cta_replicator` | NG=F | 24 | 0.0% |

### NEW FINDING-10: `luxalgo_confluence` 7d LONG regression (monitor only)

7d window analysis (not triggered by full-pool mutation_analysis.py):

| Direction | n | WR% |
|---|---|---|
| LONG | 131 | 32.8% |
| SHORT | 60 | 70.0% |
| Spread | — | **37.2pp** |

LONG WR=32.8% is below the 35% threshold. However, the full-pool `mutation_analysis.py --json` did **not** flag `luxalgo_confluence` in §1, indicating the long-run LONG WR is above 35% — this is a **7d window regression only**, likely regime-driven (same 06:56Z snapshot).

**Recommendation: monitor only.** If 7d LONG WR stays <35% on n≥150 in the next fresh snapshot, run Axis-1 mutation analysis. Do NOT block without full-pool confirmation.

---

## §5 Mutation Analysis Output (08Z)

Identical to 07Z run (same data). Key §1 results:
- combined_confidence: LONG 8.3% / SHORT 55.6% (47pp, n=12 — below n≥20 floor)
- ig_contrarian_sentiment: LONG 16.5% / SHORT 60.3% (44pp, n=200/58)
- myfxbook_retail_contrarian: LONG 13.7% / SHORT 50.0% (36pp, n=124/14)
- quan_engine_swing: LONG 26.0% / SHORT 60.0% (34pp, n=104/5)
- forex_rsi2_mean_reversion: LONG 6.8% / SHORT 34.8% (28pp, n=117/23)
- cta_cross_asset_tsmom: LONG 29.4% / SHORT 53.0% (24pp, n=85/168)

Key §3 symbol variance: `cta_replicator` 71pp spread (USDJPY 70.8% WR vs NG=F 0%); `rapid_fire` 89pp (ENJUSDT 88.9% vs UUSDT 0%).

---

## §6 PR Triage

**Open PRs:** 1 (PR #1245 — 07Z audit report)

| PR | Title | CI | Reviews | Mergeable | Action |
|---|---|---|---|---|---|
| #1245 | audit: hourly report 07Z | ✅ all green | COMMENTED (bot only, no REQUEST_CHANGES) | unknown | HOLD — re-check at 09Z if state resolves |

**Merge actions this hour:** 0

**PRs merged today:** #684, #674, #673, #664, #683, #687, #692, #694 (per session context)

**Hold set:** #660, #658, #681, #661 (Plan v2.1 family — never merge)

**Author rebase list** (#669, #676, #608, #665, #644, #597, #615, #655): all closed/merged in prior cycles — no action.

---

## §7 Issue Updates

- **Issue #685:** Resolver work DONE — no action. Auto-close any PR claiming 'widen re-resolve scope'.
- **Issue #686:** 08Z comment posted.
- **Issue #693:** Closed 2026-05-13; protocol active (EQUITY 14d monitor). 30d PF 1.939 → partial #692 recovery ongoing.

---

## §8 Summary

| Item | Status |
|---|---|
| Dashboard freshness | STALE (06:56Z, same as 07Z — cron not yet propagated) |
| New kill candidates | 0 new (FINDING-10 monitor only) |
| Confirmed kill candidates | 2 (ensemble + crypto_mtf_ema_slope_alignment_v1) |
| PRs merged this hour | 0 |
| PRs on HOLD | #1245 (mergeable_state=unknown) |
| 3-AI consensus needed | 7 candidates (5 direction + 2 symbol) |
| CRYPTO trajectory | improving (24h +0.074 PF) |
| FOREX trajectory | recovery holding (4th+ confirmation) |
| EQUITY | monitor per #693 protocol |
| COMMODITY | cftc_cot legacy aging out (~5d) |

_Generated by Claude Sonnet 4.6 automated hourly audit. Branch: `audit/hourly-08z`._

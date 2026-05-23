# Hourly Audit — 2026-05-19 07Z

**Generated:** 2026-05-19T07:xx UTC  
**Dashboard snapshot:** 2026-05-19T06:56:27Z (lag ~1h, hourly cron OK)  
**recent_closed pool:** n=3,500  
**Branch:** audit/hourly-07z  
**Merged this hour:** PR #1244 (06Z report, all CI green, squash)

---

## 1. Dashboard Refresh Status

Snapshot at `2026-05-19T06:56:27.248361+00:00` — fresh within 1h of query time. Hourly cron confirmed running. No staleness alert.

---

## 2. Per-Asset Metrics (24h / 7d / 30d)

Computed from `recent_closed` (n=3,500) using `closed_at` / `resolved_at` field timestamps.

| Class     | 24h n   | 24h PF | 24h WR | 7d n   | 7d PF  | 7d WR  | 30d n  | 30d PF | 30d WR |
|-----------|---------|--------|--------|--------|--------|--------|--------|--------|--------|
| CRYPTO    | 260     | 1.386  | 56.2%  | 1,039  | 1.045  | 44.5%  | 2,902  | 1.272  | 46.3%  |
| EQUITY    | 5       | 0.000  | 0.0%   | 15     | 0.238  | 13.3%  | 95     | 1.939  | 50.5%  |
| FOREX     | 8       | 1.246  | 37.5%  | 19     | 1.295  | 31.6%  | 93     | 2.532  | 48.4%  |
| COMMODITY | 8       | 0.180  | 25.0%  | 23     | 0.193  | 13.0%  | 57     | 1.747  | 54.4%  |
| ETF       | 9       | 1.887  | 11.1%  | 20     | 0.989  | 25.0%  | 49     | 2.005  | 57.1%  |
| BOND      | 0       | —      | —      | 0      | —      | —      | 0      | —      | —      |
| FUTURES   | 0       | —      | —      | 1*     | —      | —      | 2*     | —      | —      |

*FUTURES n=1/2: single unresolved pick (pnl=0). Class effectively dormant post-`futures_momentum` kill.

### Deltas vs 06Z (previous session)

| Metric          | 06Z    | 07Z    | Delta  | Action |
|-----------------|--------|--------|--------|--------|
| CRYPTO 24h PF   | 1.201  | 1.386  | **+0.185** | ↑ improving |
| CRYPTO 7d PF    | 1.026  | 1.045  | +0.019 | stable/improving |
| CRYPTO 30d PF   | 1.262  | 1.272  | +0.010 | stable |
| EQUITY 7d PF    | 0.238  | 0.238  | 0.000  | unchanged (n=15, monitor) |
| EQUITY 30d PF   | 1.939  | 1.939  | 0.000  | unchanged |
| FOREX 7d PF     | 1.315  | 1.295  | −0.020 | stable |
| FOREX 30d PF    | 2.543  | 2.532  | −0.011 | stable |
| COMMODITY 7d PF | 0.193  | 0.193  | 0.000  | unchanged (legacy drag) |
| ETF 7d PF       | 0.989  | 0.989  | 0.000  | stable |

### Deltas vs original baselines (task prompt / May-02 snapshot)

| Metric          | May-02 baseline | 07Z    | Delta     | Status |
|-----------------|-----------------|--------|-----------|--------|
| CRYPTO 24h PF   | 3.54            | 1.386  | −2.154    | May-02 was high-vol spike; trend from 06Z is improving |
| CRYPTO 7d PF    | 1.33            | 1.045  | −0.285    | Watch |
| CRYPTO 30d PF   | 1.33            | 1.272  | −0.058    | Stable |
| EQUITY 7d PF    | 0.87            | 0.238  | −0.632    | Monitor per #693 protocol |
| EQUITY 30d PF   | 1.41–2.18       | 1.939  | within range | OK |
| FOREX 7d PF     | 0.14 pre-#687   | 1.295  | **+1.155**| ↑↑ recovery confirmed |
| FOREX 30d PF    | 0.97 pre-#687   | 2.532  | **+1.562**| ↑↑ best class by 30d PF |

---

## 3. COMMODITY 7d — Root Cause

COMMODITY 7d PF=0.193 is explained entirely by `cftc_cot_commercial_signal` residue:

| Strategy                    | n  | WR   | Sum PnL  | Root cause |
|-----------------------------|-----|------|----------|------------|
| `cftc_cot_commercial_signal`| 18 | 6%   | −54.76%  | Pre-#683 kill legacy trades aging through 7d window |
| `futures_momentum`          | 5  | 40%  | −1.49%   | Small residue |

PR #683 (`cftc_cot` kill) merged today. These 18 trades pre-date the kill and will clear the 7d window within ~6 days. COMMODITY 30d PF=1.747 (n=57, WR=54.4%) is T2-eligible and unaffected. **No action required.**

---

## 4. FUTURES Class — Confirmed Dormant

`asset_class_health` FUTURES: PF=0.956, WR=16.7%, n=12, status=`thin_sample`. Per-window 7d n=1, 30d n=2 — both unresolved (pnl=0). The `futures_momentum` kill (documented in prior session 07Z 2026-05-18) has been effective. Class is no longer P1.

---

## 5. Mutation Analysis — python3 tools/mutation_analysis.py --json

### §1 Direction Asymmetry

| Strategy | SHORT WR | SHORT n | LONG WR | LONG n | Spread | Status |
|----------|----------|---------|---------|--------|--------|--------|
| `combined_confidence`     | 55.6% | 9  | 8.3%  | 12  | 47pp | Monitor (n=21 marginal) |
| `ig_contrarian_sentiment` | 60.3% | 58 | 16.5% | 200 | 44pp | FINDING-2 (05Z) confirmed; n=200 LONG stable-threshold |
| `myfxbook_retail_contrarian` | 50.0% | 14 | 13.7% | 124 | 36pp | FINDING-4 (06Z) confirmed |
| `quan_engine_swing`       | 60.0% | 5  | 26.0% | 104 | 34pp | FINDING-5 (06Z) confirmed |
| `forex_rsi2_mean_reversion` | 34.8% | 23 | 6.8% | 117 | 28pp | Documented since #686 open |
| `cta_cross_asset_tsmom`   | 53.0% | 168| 29.4% | 85  | 24pp | FINDING-6 (06Z) confirmed |

All confirmed findings unchanged from 06Z. No new direction-flip candidates emerged.

### §3 Symbol Variance (unchanged from 06Z)

| System | Symbol | WR | n | Status |
|--------|--------|----|---|--------|
| `rapid_fire` | UUSDT | 0.0% | 34 | FINDING-7 confirmed — awaiting 3-AI consensus |
| `cta_replicator` | NG=F | 0.0% | 24 | FINDING-8 confirmed — awaiting 3-AI consensus |

### §4 Axis-4 Candidates (unchanged)

`multi_asset_copytrader` (WR 21.9%, n=1103), `rapid_fire` (WR 29.0%, n=207), `alpha_engine` (WR 30.0%, n=50), `quan_engine` (WR 30.4%, n=5896) — all Axis-4 vol-normalization candidates per docs/MUTATION_THREE_AXIS_PROTOCOL.md.

---

## 6. NEW STRATEGY-LEVEL KILL CANDIDATES (PF<0.5, n≥20)

### FINDING-1 (05Z, CONFIRMED): `ensemble` — CRYPTO class

| Window | n  | PF    | WR    | Sum PnL |
|--------|----|-------|-------|---------|
| 7d     | 31 | 0.279 | 19.4% | (negative) |
| 30d    | 129| 1.034 | 38.0% | marginally positive |

7d PF=0.279 < 0.5 and n=31 ≥ 20 — kill criteria met. 30d PF=1.034 (improved from 05Z 0.942) — structural vs regime-dependent unclear. **Awaiting 3-AI consensus.** Per CLAUDE.md: do not add to BLOCKED_ASSET_STRATEGY_PAIRS without (a) mutation axes all failing, (b) n≥20 sustained ≥1 week, (c) 3-AI agreement.

### NEW FINDING-9: `crypto_mtf_ema_slope_alignment_v1`

| Window | n  | PF    | WR    | Status |
|--------|----|-------|-------|--------|
| 7d     | 20 | 0.465 | 30.0% | PF<0.5, n=20 — marginal |
| 30d    | 37 | 1.053 | 35.1% | above T2 floor |

7d PF=0.465 < 0.5, n=20 exactly at the floor. The 30d PF=1.053 vs 7d PF=0.465 suggests a recent (last 7d) regime change, not a structural failure. n=20 is at the absolute minimum — very low confidence. **Recommendation: monitor for another 24h; if 7d PF remains <0.5 on n≥25, escalate to mutation analysis.**

No other aggregate-level PF<0.5 + n≥20 strategies identified.

---

## 7. Aggregate Long-run Strategy Leaderboard (30d, n≥20)

| PF    | WR    | n   | Strategy |
|-------|-------|-----|----------|
| 0.822 | 46.9% | 32  | ema_momentum_m006 |
| 0.980 | 45.9% | 109 | strong consensus (alpha_engine, ml_crypto_pred) |
| 0.983 | 38.7% | 31  | keltner_compression_expansion_sol_v1 |
| 1.034 | 38.0% | 129 | ensemble |
| 1.053 | 35.1% | 37  | keltner_compression_expansion_eth_v1 |
| 1.062 | 45.7% | 681 | luxalgo_confluence |
| ...   |       |     | |
| 2.859 | 65.6% | 250 | st_fear_greed_contrarian |
| 3.385 | 75.0% | 20  | rs-breakout-scout |
| 4.774 | 70.7% | 41  | macd_rsi_m048 |

`ema_momentum_m006` (PF=0.822, n=32) is the lowest-PF 30d strategy above the kill floor. Sub-T2 but above cut threshold.

---

## 8. PR Triage

### Merged this hour
- **PR #1244** (06Z hourly report): squash-merged. All CI green (scan ✓, gitleaks ✓, hardcoded-db ✓). Only greptile bot COMMENTED — no REQUEST_CHANGES.

### Open PRs
- **1 open PR total** (this session's report PR, to be created).
- HOLD set (#660, #658, #681, #661): none in open PR list — confirmed absent.
- Author-rebase PRs (#669, #676, #608, #665, #644, #597, #615, #655): all closed per 06Z confirmation.

---

## 9. Issue Status

| Issue | Status | Action |
|-------|--------|--------|
| #685 | Open — resolver done | No action (auto-close any PR claiming 'widen re-resolve scope') |
| #686 | Open — live quality tracker | New comment posted this hour (07Z) |
| #693 | Closed 2026-05-13 | EQUITY monitor protocol active per §2 |

---

## 10. Next Hour Recommendations

1. **Monitor `crypto_mtf_ema_slope_alignment_v1`** (FINDING-9): if 7d PF still <0.5 at 08Z, run mutation axes.
2. **Monitor `ensemble`** (FINDING-1): 3-AI consensus needed — Claude already posted; Kimi/Copilot/Cursor input outstanding.
3. **COMMODITY 7d**: expect gradual improvement as cftc_cot_commercial_signal 7d legacy trades age out (~6 days remaining).
4. **EQUITY 7d**: n=15 still below 20 threshold. 30d PF=1.939 healthy. Per #693: next checkpoint 2026-05-20 to assess if goldmine_6x kill cleared the 7d window.
5. **Symbol blocks** (FINDING-7 UUSDT, FINDING-8 NG=F): still awaiting 3-AI consensus — no unilateral action.

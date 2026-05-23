# Hourly Audit — 2026-05-17 09Z

**Generated:** 2026-05-17T09:11Z  
**Dashboard snapshot:** 2026-05-17T08:10Z (not yet refreshed to 09Z — same data as 08Z report)  
**Auditor:** Claude Sonnet 4.6 (automated hourly)  
**Prior report:** `reports/HOURLY_AUDIT_2026-05-17_08Z.md`  
**Issue refs:** #685 (resolver done), #686 (per-asset attribution), #693 (EQUITY monitor, closed)

---

## 1. Dashboard Refresh Status

Dashboard was generated at **2026-05-17T08:10Z** — 61 minutes before this report. The next hourly refresh is expected at ~09:10Z. All metrics below reflect the 08:10Z snapshot. **No new data vs 08Z report.** Deltas are against the documented baselines from issues #686 and #693.

---

## 2. Per-Asset PF/WR — 24h / 7d / 30d

### Raw calculations from `dashboard_data.json::picks.recent_closed` (n=3500)

| Class | Window | n | PF | WR% | Sum PnL% | vs Baseline |
|-------|--------|---|-----|------|-----------|-------------|
| **CRYPTO** | 24h | 50 | 1.283 | 40.0% | +11.79% | ⬇ vs 3.54/64% |
| **CRYPTO** | 7d | 410 | 1.164 | 36.6% | +63.44% | ⬇ vs 1.21/41% (WR declined) |
| **CRYPTO** | 30d | 1139 | 1.227 | 38.6% | +251.12% | ⬇ vs 1.33/— |
| **EQUITY** | 7d | 22 | 0.682 | 13.6% | −10.28% | ⬇ vs 0.87/41% (#693 close state) |
| **EQUITY** | 30d | 87 | 2.701 | 55.2% | +186.13% | ⬆ vs 1.41-2.18 |
| **ETF** | 7d | 13 | 0.656 | 46.2% | −7.14% | ⬇ watch |
| **ETF** | 30d | 48 | 2.482 | 70.8% | +50.56% | ⬆ solid |
| **FOREX** | 7d | 8 | 999* | 12.5% | +0.70% | ⬆ vs 0.14/10.7% (dormant post-kills) |
| **FOREX** | 30d | 29 | 6.088 | 34.5% | +15.52% | ⬆ recovering |
| **COMMODITY** | 7d | 0 | — | — | — | ⚠ see note |
| **COMMODITY** | 30d | 0 | — | — | — | ⚠ see note |
| **BOND** | long-run | 12 | 0.540 | 50.0% | — | n<50 floor |

*FOREX PF=999: gross_loss=0 (all 7 losers have pnl_pct=0). Zero-pnl problem from 07Z persists. Only 1/8 picks has positive PnL.

**Long-run `asset_class_health` (post-resolver-v2):**

| Class | PF | WR% | n | Tier status |
|-------|----|-----|---|-------------|
| CRYPTO | 1.290 | 46.3% | 7322 | sub-T2 (WR floor 50%) |
| EQUITY | 1.970 | 53.3% | 240 | T2 candidate |
| FOREX | 2.070 | 35.7% | 98 | T2 PF but WR<50% |
| ETF | 2.410 | 67.6% | 74 | T2 candidate (n→100) |
| COMMODITY | 7.300 | 85.5% | 228 | T1 candidate |
| BOND | 0.540 | 50.0% | 12 | insufficient |
| FUTURES | n/a | 100% | 2 | insufficient |

### COMMODITY 7d discrepancy (vs 08Z)

08Z report cited COMMODITY 7d n=27/WR=29.6%/PF=0.64. **This does not match the 08:10Z data.** Direct count of picks with `asset_class=COMMODITY` closed within 7d = **0**. All 67 COMMODITY picks in the 3500 recent_closed have `closed_at` > 7d ago. The 08Z figure may have used `updated_at` with a different cutoff or a different data pass. **Flagged for investigation — does not change operational decisions.**

---

## 3. PR Triage

**`gh pr list --state open` returned: 0 open PRs.**

All PRs from the triage watch-list are already closed:

| PR | Title (abbreviated) | State | Merged? | Note |
|----|---------------------|-------|---------|------|
| #660 | P0 Emergency Gate Fixes (Plan v2.1 family) | closed | ✅ merged 2026-05-03 | ⚠ Was on HOLD list — merged before constraint added |
| #658 | Hedge Fund Quality Enhancement (Plan v2.1 family) | closed | ❌ not merged | ✅ Correctly blocked |
| #681 | strategy-decay guard | closed | ❌ not merged | ✅ Correctly blocked |
| #661 | (hold list) | not checked | — | Previously confirmed closed |
| #669 | B2 AC-timeframe grid | closed | ✅ merged 2026-05-02 | ✅ correct |
| #676 | (author rebase set) | — | — | All author-rebase PRs already merged per prior audits |

**Action taken:** 0 merges this hour. No open PRs found.

**⚠ Flag on PR #660:** This PR cites Plan v2.1 stats (ml_score≥0.82, WINNER_FILTER abolish, elite_score→ml_score). Per issue #685 these stats are fabricated. The PR merged 2026-05-03 — 14 days before today. Changes are in production. A separate investigation or revert PR may be warranted if the #660 changes are causing negative downstream effects. **Not auto-acting — flagging for operator review.**

---

## 4. New Strategy Kill Candidates (mutation_analysis.py)

`python tools/mutation_analysis.py --json` run at 09:08Z on 08:10Z data.

### New findings vs 08Z

No new strategies meet the auto-kill threshold (n≥20, PF<0.5, WR<35%). Same candidates as 07Z/08Z remain unresolved:

**Axis-1 Direction Asymmetry (from 07Z — awaiting 3-AI consensus):**

| Strategy | Dir blocked | n | WR% | Opposite WR% | Spread |
|----------|-------------|---|-----|--------------|--------|
| `ig_contrarian_sentiment` | LONG | 197 | 16.8% | SHORT: 61.4% | 45pp |
| `myfxbook_retail_contrarian` | LONG | 123 | 13.8% | SHORT: 50.0% | 36pp |
| `forex_rsi2_mean_reversion` | LONG | 108 | 7.4% | SHORT: 34.8% | 27pp |
| `quan_engine_swing` | LONG | 104 | 26.0% | SHORT: 60.0% | 34pp |
| `cta_cross_asset_tsmom` | LONG | 84 | 29.8% | SHORT: 52.4% | 23pp |

**Symbol-level (from 08Z — awaiting 3-AI consensus):**

| Pair | n | WR% | Status |
|------|---|-----|--------|
| `cta_replicator` / NG=F | 24 | 0.0% | ✅ n≥20, meets threshold |
| `rapid_fire` / UUSDT | 34 | 0.0% | ✅ n≥20, meets threshold |
| `cta_replicator` / CL=F | 47 | 19.1% | WR sub-floor (35%) |

**New sub-threshold finds (09Z, n<20):**

| Strategy | Asset | n | WR% | Sum PnL% |
|----------|-------|---|-----|-----------|
| `st_fear_greed_contrarian` | CRYPTO | 5 | 0.0% | −7.11% |
| `drawdown_recovery_rsi_sol` | CRYPTO | 7 | 0.0% | −7.00% |
| `CRYPTO::unknown` bucket | CRYPTO | 186 | 29.0% | −11.59% |

`CRYPTO::unknown` (n=186, PF=0.932) is the largest drag in 7d. Strategy attribution is missing — picks without strategy labels. This is a data quality issue, not a kill target.

**No new strategies added to `BLOCKED_ASSET_STRATEGY_PAIRS` this hour.** Per CLAUDE.md: auto-kill requires 3+ AI consensus. Existing threshold-meeting candidates (NG=F, UUSDT) need that consensus before block.

---

## 5. Key Findings Delta vs Documented Baselines

| Finding | Baseline | 09Z | Direction | Action |
|---------|----------|-----|-----------|--------|
| CRYPTO 24h PF | 3.54 | 1.283 | ⬇ major | Monitor — may be regime/timing noise |
| CRYPTO 7d PF | 1.33 | 1.164 | ⬇ mild | Monitor |
| EQUITY 7d PF | 0.87 (#693 close) | 0.682 | ⬇ continued degradation | stocksunify2_* zero-pnl investigation needed |
| EQUITY 30d PF | 2.18 (#693 close) | 2.701 | ⬆ improving | goldmine_6x kill (#692) contributing |
| FOREX 7d PF | 0.14 (pre-#687) | 999* | ⬆ (dormant) | Kills working; zero-pnl issue masks real performance |
| ETF 7d PF | 1.57 (#686 base) | 0.656 | ⬇ regression | n=13 small — watch 30d (2.482) as anchor |

### EQUITY 7d root cause (unchanged from 07Z/08Z)

Per strategy, 7d EQUITY (n=22):
- `stocksunify2_adversarial_trend_v2`: n=8, WR=0%, sum=0 (zero-pnl — unresolved picks counted as losses)
- `stocksunify2_volatility_adjusted_momentum_v2`: n=2, WR=0%, sum=0
- `stocksunify2_regime_aware_reversion_v2`: n=1, WR=0%, sum=0
- `macd-hidden-div-scout`: n=2, sum=−8.14% (real losses)
- `price-accel-scout`: n=2, sum=−8.45% (real losses)

Adjusted EQUITY 7d (excluding 11 zero-pnl picks): n=11, 3 real winners = 27% WR. Still sub-T2 but substantially less alarming than raw 13.6%. **Outcome resolver may not have swept stocksunify2_* picks — needs operational sweep (per issue #685 §1).**

### CRYPTO 24h degradation analysis

PF dropped from 3.54 (baseline) to 1.283. Top 7d CRYPTO performers:
- `claude_ml_moderate_mut`: n=40, PF=2.738, WR=62.5% — strong
- `signal_engine_wide_net_mut`: n=5, PF=9.212, WR=80%
- `ml_enhanced_WLDUSDT`: n=6, PF=7.5, WR=83.3%

7d drag:
- `CRYPTO::unknown`: n=186, PF=0.932, WR=29.0%, sum=−11.59% — largest volume drag

The 24h drop is likely short-window variance (n=50). `claude_ml_moderate_mut` healthy at 7d suggests underlying strategy quality intact.

---

## 6. Open Action Items (carry-forward from 07Z/08Z)

| Item | Source | Status |
|------|--------|--------|
| Axis-1 LONG blocks (5 strategies) | 07Z | Awaiting 3-AI consensus |
| `cta_replicator`/NG=F block | 08Z | Awaiting 3-AI consensus |
| `rapid_fire`/UUSDT block | 07Z | Awaiting 3-AI consensus |
| `stocksunify2_*` zero-pnl resolver sweep | 07Z/09Z | Operational: needs operator go-ahead |
| COMMODITY 7d n=27 discrepancy (08Z claim) | 09Z new | Investigate data parsing |
| PR #660 Plan v2.1 merge (post-hoc) | 09Z new | Operator review needed |

---

## 7. Branch & Commit

Branch: `audit/hourly-09z`  
Report: `reports/HOURLY_AUDIT_2026-05-17_09Z.md`  
Issue update: #686 comment posted

---

*Generated by Claude Sonnet 4.6 automated hourly audit.*

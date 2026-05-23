# Hourly Audit — 2026-05-20 05Z

**Dashboard snapshot:** 2026-05-20T04:13:12Z (FRESH — ≤2h window met)  
**Previous audit:** PR #1255 (15Z, 2026-05-19) — merged 2026-05-19T20:17Z  
**Open PRs at audit time:** 0  
**HOLD set (#660 #658 #681 #661):** confirmed absent ✅  
**Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655):** confirmed absent ✅

---

## 1. Per-Asset Performance (24h / 7d / 30d)

Computed from `picks.recent_closed` (n=3,500) against dashboard generated_at 2026-05-20T04:13Z.

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|-------|-------|--------|--------|------|-------|-------|-------|--------|
| CRYPTO | 173 | 43.9% | **1.004** | 1013 | 45.8% | **1.200** | 2792 | 46.8% | **1.340** |
| EQUITY | 16 | 6.2% | **0.075** | 45 | 28.9% | **0.641** | 146 | 44.5% | **1.419** |
| FOREX | 7 | 42.9% | **1.278** | 18 | 33.3% | **1.272** | 93 | 48.4% | **2.515** |
| COMMODITY | 16 | 0.0% | **0.000** | 38 | 7.9% | **0.097** | 73 | 42.5% | **0.962** |
| ETF | 1 | 0.0% | **0.000** | 16 | 31.2% | **1.233** | 50 | 56.0% | **1.917** |
| BOND | 3 | 0.0% | **0.000** | 3 | 0.0% | **0.000** | 3 | 0.0% | **0.000** |
| FUTURES | 0 | — | — | 0 | — | — | 2 | 100.0% | 999 |

### Deltas vs PR #1255 (15Z 2026-05-19 — last merged audit)

| Class | 24h PF Δ | 7d PF Δ | 30d PF Δ | Note |
|-------|----------|---------|---------|------|
| CRYPTO | 2.462 → 1.004 **−1.458** | 1.137 → 1.200 **+0.063** | 1.304 → 1.340 **+0.036** | 24h intraday pullback; 7d/30d improving ✅ |
| EQUITY | n/a (n=3 at 15Z) | 0.267 → 0.641 **+0.374** | 1.939 → 1.419 **−0.520** | 7d recovery post-#692; 30d roll-off |
| FOREX | 1.324 → 1.278 −0.046 | 1.303 → 1.272 −0.031 | 2.535 → 2.515 −0.020 | Stable; post-#687 recovery intact ✅ |
| COMMODITY | 0.000 → 0.000 | 0.176 → 0.097 **−0.079** | 1.624 → 0.962 **−0.662** | **🚨 30d sub-1.0 NEW ALARM** |
| ETF | 3.198 → 0.000 (n=1) | 1.279 → 1.233 −0.046 | 1.959 → 1.917 −0.042 | Stable |

---

## 2. PR Triage

**0 open PRs** — nothing to merge or hold. All previous watch PRs confirmed closed.

Kill verifications (dead-check in `recent_closed` 7d window):
- `forex_carry_momentum` ✅ (0 trades in 7d)
- `goldmine_6x_consensus` ✅ (0 trades in 7d)
- `quan_engine`/HYPEUSDT ✅ (0 trades in 7d)
- `quan_engine`/MATICUSDT ✅ (0% WR per mutation_analysis Axis-3)
- `forex_rsi2_mean_reversion` ✅ (0 trades in 7d)
- `cftc_cot` family — see FINDING-22 below

---

## 3. Mutation Analysis (`python3 tools/mutation_analysis.py --json`)

### 3a. FINDING-22 — NEW KILL CANDIDATE: `cftc_cot_commercial_signal` × COMMODITY (n=20 floor hit)

| Metric | Value |
|--------|-------|
| n (7d) | **20** — hit n=20 floor this cycle (was n=18 at PR #1255, HOLD) |
| WR | **5.0%** |
| PF | **0.113** |
| Sum PnL | **−65.79%** |

Kill criteria per CLAUDE.md §Kill Protocol (all ✅):
- PF < 0.5 ✅ (0.113)
- n ≥ 20 ✅ (exactly 20)
- WR < 35% sustained ✅ (5.0%)
- Pattern matches PR #683 kill family (`cftc_cot` BLOCKED_SOURCE_SYSTEMS) ✅

**Action: Post to issue #686 for 3-AI consensus. Do NOT auto-add to BLOCKED_ASSET_STRATEGY_PAIRS without consensus.**

Note: `futures_momentum` × COMMODITY at n=17, WR 11.8%, PF 0.087 is approaching kill threshold but 3 trades short of n=20 floor. Re-check at 06Z.

### 3b. COMMODITY 30d Regression Alarm

COMMODITY 30d PF dropped below 1.0 for the first time in monitoring period: **0.962** (was 1.624 at 15Z, 1.747 at 08Z yesterday).

Full 7d COMMODITY strategy breakdown:

| Strategy | n | WR | PF | Net |
|----------|---|----|----|-----|
| `cftc_cot_commercial_signal` | 20 | 5.0% | 0.113 | −65.79% |
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | 0.000 | −6.41% |

FINDING-19 from PR #1255 (`multi_asset_copytrader` × metals: PL=F/GC=F/HG=F all 0% WR per mutation_analysis Axis-3) confirmed continuing. Targeted symbol-block proposal still awaiting 3-AI consensus.

### 3c. CRYPTO 24h Pullback — Monitor Only

CRYPTO 24h PF: 2.462 → 1.004. 7d/30d improving simultaneously (+0.063/+0.036), indicating intraday noise rather than structural change. `st_fear_greed_contrarian` (n=219, WR 67.1%, PF 3.012 in 7d) remains dominant alpha driver. **Do not destabilize CRYPTO.**

### 3d. EQUITY 7d Recovery (issue #693 protocol)

EQUITY 7d: 0.267 (n=13) → **0.641** (n=45). Confirms PR #692 (goldmine_6x_consensus kill) was the primary drag. Recovery trajectory as predicted by issue #693 hypothesis.
- `stocks_rsi2_pullback` (n=29, WR 34.5%, PF 0.980): near-breakeven, below kill threshold.
- Issue #693 gate: EQUITY 14d ≥ PF 1.5 within 7 days post-#692. Need 14d window to fully assess; 30d 1.419 is lower bound.

### 3e. Ongoing Watch List (awaiting 3-AI consensus — unchanged except one downgrade)

| Candidate | n | WR% | Type | Status |
|-----------|---|-----|------|--------|
| `ig_contrarian_sentiment` LONG | 200 | 16.5% | Axis-1 direction block | Active |
| `myfxbook_retail_contrarian` LONG | 124 | 13.7% | Axis-1 direction block | Active |
| `quan_engine_swing` LONG | 104 | 26.0% | Axis-1 direction block | Active |
| `forex_rsi2_mean_reversion` LONG | 117 | 6.8% | Axis-1 direction block | Active |
| `cta_cross_asset_tsmom` LONG | 85 | 29.4% | Axis-1 monitor | Active |
| `rapid_fire` / UUSDT | 34 | 0.0% | Axis-3 symbol block | Active |
| `cta_replicator` / NG=F | 24 | 0.0% | Axis-3 symbol block | Active |
| `ensemble` CRYPTO | ~25 | ~20% | Kill candidate | 3-AI pending |
| `crypto_mtf_ema_slope_alignment_v1` | 27 | 33.3% (7d PF 0.505) | Kill watch | **DOWNGRADED to monitor** (PF recovering: 0.294→0.465→0.505) |

---

## 4. Top Alpha Drivers (7d, n≥10)

| Strategy | Class | n | WR | PF |
|----------|-------|---|----|----||
| `st_fear_greed_contrarian` | CRYPTO | 219 | 67.1% | 3.012 |
| `keltner_compression_expansion_sol_v1` | CRYPTO | 17 | 58.8% | 1.929 |
| `claude_ml_moderate_mut` | CRYPTO | 43 | 48.8% | 1.563 |
| FOREX (class) | FOREX | 18 | 33.3% | 1.272 |
| ETF (class) | ETF | 16 | 31.2% | 1.233 |

---

## 5. Actions Taken This Cycle

- **Merged:** 0 PRs (none open)
- **New findings escalated:** FINDING-22 (`cftc_cot_commercial_signal` n=20 hit) — posted to issue #686
- **Downgraded:** `crypto_mtf_ema_slope_alignment_v1` from kill-watch to monitor (7d PF 0.505)
- **Resolver:** no action (issue #685 — done)

---

## 6. Baseline Delta Summary (vs issue #686 original 2026-05-02)

| Class | Baseline 7d PF | 05Z 7d PF | Baseline 30d PF | 05Z 30d PF | Trend |
|-------|---------------|-----------|-----------------|------------|
| CRYPTO | 1.21 | **1.200** | 1.28 | **1.340** | Stable/improving |
| EQUITY | 0.87 | **0.641** | 1.41–2.18 | **1.419** | 7d recovering; 30d lower bound |
| FOREX | 0.14 | **1.272** | 0.97 | **2.515** | ↑↑↑ Post-#687 confirmed |
| COMMODITY | 1.18 | **0.097** | ~1.7 | **0.962** | ↓↓ Deteriorating — 30d sub-1 NEW |
| ETF | 1.57 | **1.233** | ~1.9 | **1.917** | Mild softening; healthy |

---

## 7. Next-Hour Checklist (06Z)

- [ ] Re-check `futures_momentum` × COMMODITY n count (was 17 — needs 3 more for n=20 floor)
- [ ] Confirm 3-AI vote on `cftc_cot_commercial_signal` via issue #686 response
- [ ] Monitor CRYPTO 24h recovery (was 1.004 at 05Z)
- [ ] EQUITY 7d: confirm recovery trajectory holds (target PF≥1.5 per issue #693 gate)
- [ ] Dashboard refresh check — next cron expected ~06:00Z

---

*Reproducer: `python3 -c "import json,datetime; d=json.load(open('audit_dashboard/data/dashboard_data.json')); print(d['generated_at'])"` *  
_Generated by Claude Code — session_0186reucLZfWo2TR2XsthSNB — 2026-05-20T05Z_

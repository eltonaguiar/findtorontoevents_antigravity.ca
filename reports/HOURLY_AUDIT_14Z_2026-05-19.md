# Hourly Audit — 2026-05-19 14Z

**Generated:** 2026-05-19T~14:10Z  
**Dashboard snapshot:** 2026-05-19T12:14:53Z (1h56m stale — no 14Z refresh yet; within ≤2h window)  
**Snapshot source:** `audit_dashboard/data/dashboard_data.json` on `origin/main` (sha `4f0d090b`)  
**recent_closed n:** 3500

---

## 1. Dashboard Refresh Status

Origin/main had 14+ [skip ci] data commits since the 12:14Z dashboard snapshot (equities agent, forex agent, pre-spike scan, ML tracker, cross-system aggregation, etc.). The dashboard_data.json itself has **not refreshed** since 12:14:53Z — next hourly refresh expected ~14:14Z. Numbers below are from the 12:14Z snapshot, same as 13Z audit. Deltas vs 13Z are negligible (same data).

---

## 2. Per-Asset PF/WR — 14Z Reference Window

> Computed from `recent_closed` (n=3500). Windows are rolling from 14:00Z today.

| Class | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|-------|-------|--------|--------|------|-------|-------|-------|--------| -------|
| **CRYPTO** | 270 | 2.382 | 60.4% | 1045 | 1.119 | 45.2% | 2901 | 1.282 | 46.1% |
| **EQUITY** | 3 | 0.000 | 0.0% | 15 | 0.238 | 13.3% | 95 | 1.939 | 50.5% |
| **FOREX** | 7 | 1.304 | 42.9% | 19 | 1.289 | 31.6% | 93 | 2.525 | 48.4% |
| **COMMODITY** | 4 | 0.000 | 0.0% | 24 | 0.176 | 12.5% | 58 | 1.624 | 53.4% |
| **ETF** | 9 | 1.887 | 11.1% | 20 | 0.989 | 25.0% | 49 | 2.005 | 57.1% |
| **BOND** | 0 | — | — | 0 | — | — | 0 | — | — |
| **FUTURES** | 0 | — | — | 0 | — | — | 2 | ∞ | 100% |

---

## 3. Deltas vs 13Z (PR #1253) and vs Issue #686 Baseline

### vs 13Z baseline (PR #1253, same snapshot)

| Class | 24h PF Δ | 7d PF Δ | 30d PF Δ | Notes |
|-------|----------|---------|----------| ------|
| CRYPTO | −0.090 | −0.002 | 0.000 | Same snapshot; mild intra-hour variance |
| EQUITY | 0 | 0 | 0 | Same (n too small for significance) |
| FOREX | 0 | 0 | 0 | Stable |
| COMMODITY | 0 | 0 | 0 | FINDING-17 n=18 unchanged |
| ETF | 0 | 0 | 0 | Stable |

### vs Issue #686 documented baseline (2026-05-02)

| Class | Baseline 7d PF | Current 7d PF | Δ | Baseline 30d PF | Current 30d PF | Δ |
|-------|---------------|--------------|---|----------------|---------------| --|
| CRYPTO | 1.33 | 1.119 | −0.211 | 1.33 | 1.282 | −0.048 |
| EQUITY | 0.87 | 0.238 | −0.632 | 1.41–2.18 | 1.939 | within range |
| FOREX | 0.14 | **1.289** | **+1.149 ✅** | 0.97 | **2.525** | **+1.555 ✅** |
| COMMODITY | n/a | 0.176 | — | 1.78 | 1.624 | −0.156 |

Key: FOREX 7d turnaround (+1.149 PF) and 30d recovery (+1.555) since PR #687 (JPY-cross BUY rule fix) is the largest positive delta. CRYPTO 7d mild softening from 1.33→1.119 — not alarming given 24h strength (PF 2.382). EQUITY 7d at 0.238 on n=15 — too small to action; 30d at 1.939 is healthy.

---

## 4. Kill Verifications (Carried Forward from Prior Audits)

| Kill | Status | Evidence |
|------|--------|----------|
| `forex_carry_momentum` | ✅ Verified dead | 0 picks in recent_closed |
| `goldmine_6x_consensus` | ✅ Verified dead | 0 picks in recent_closed |
| `quan_engine/HYPEUSDT` | ✅ Verified dead (PR #694) | 0 picks matching symbol+source |
| `quan_engine/MATICUSDT` | ✅ Verified dead | 0 picks matching |
| `forex_rsi2_mean_reversion` | ✅ Verified dead (PR #692) | 0 picks in recent_closed |
| `cftc_cot` (PR #683 family) | ✅ Verified dead | 0 picks from cftc_cot source |

---

## 5. Findings Status

### FINDING-15 — `ensemble` CRYPTO [ACTIVE — AWAITING 3-AI CONSENSUS]
- **Metrics:** WR 20%, PF 0.290, n=25 (above n=20 floor)
- **Status:** All three kill criteria met (PF<0.5, n>=20, WR<35%). Requires 3-AI consensus before action.
- **Action at 14Z:** Posted to issue #686 to formally initiate 3-AI consensus queue.

### FINDING-16 — `crypto_mtf_ema_slope_alignment_v1` [RESOLVED]
- Downgraded from watchlist. WR recovered to 37.5% / PF 0.574 on 12:14Z data. No further monitoring needed unless regression recurs.

### FINDING-17 — `cftc_cot_commercial_signal` COMMODITY 7d [HOLD — n=18, 2 below floor]
- **7d metrics:** n=18, WR 5.6%, PF 0.133, sum −54.76%
- **30d metrics:** n=51, WR 56.9%, PF 1.838, sum +65.37% — strong long-run baseline
- **Interpretation:** Recent-regime failure, not fundamental strategy collapse. The 30d PF 1.838 exceeds T2 threshold. The 7d deterioration is severe but n=18 is below the kill floor.
- **Action:** Re-check at 15Z. If n≥20 and WR remains <35%, initiate 3-AI consensus per FINDING-15 protocol. Do NOT kill unilaterally.

### FINDING-18 — COMMODITY 24h ALL-ZERO [NEW — MONITOR]
- **24h metrics:** n=4, WR 0.0%, PF 0.000
- **Context:** All 4 picks closed as losses in the last 24h. At n=4 this is statistically meaningless (expected variance). Monitor at 15Z/16Z.
- **Action:** None at this time. Note for trend tracking.

---

## 6. Strategy Mutation Analysis (14Z run)

`python tools/mutation_analysis.py --json` output highlights:

### Axis-1 (Long/Short) candidates:
| Strategy | SHORT WR | LONG WR | Spread | Recommendation |
|----------|----------|---------|--------|----------------|
| `forex_rsi2_mean_reversion` | 34.8% (n=23) | 7.6% (n=118) | 27pp | LONG-only mutation — already killed; confirms kill was correct |
| `cta_cross_asset_tsmom` | 52.7% (n=169) | 29.4% (n=85) | 23pp | LONG-only variant worth testing in SANDBOX |

### Axis-3 (Symbol-allowlist) candidates with n≥20:
| System | Worst symbols | WR | n | Action |
|--------|--------------|-----|---|--------|
| `cta_replicator` | NG=F (0%), ZC=F (0%) | 0%/0% | 24/8 | NG=F above n=20 floor; ZC=F below. NG=F needs mutation analysis first before kill per protocol. |
| `rapid_fire` | UUSDT (0%) | 0% | 34 | n=34 above floor. WR 0%, matches kill pattern. Needs cross-source validation before 3-AI queue. |
| `quan_engine` | MATICUSDT (0%), ONDOUSDT (22%), SOLUSDT (23%) | varies | varies | MATICUSDT already killed (PR #694). ONDOUSDT/SOLUSDT approaching watchlist. |

> **Note:** `rapid_fire/UUSDT` (n=34, WR 0%) and `cta_replicator/NG=F` (n=24, WR 0%) not found in `recent_closed` 3500-cap dataset — mutation_analysis reads a broader data source. Cross-source validation required before escalating to 3-AI queue.

---

## 7. PR Triage

| Action | PRs | Result |
|--------|-----|--------|
| **Merged this hour** | #1253 (13Z audit) | ✅ squash-merged (sha 4f0d090b) |
| **HOLD set** | #660 #658 #681 #661 | ✅ Absent from open PRs |
| **Author-rebase watch** | #669 #676 #608 #665 #644 #597 #615 #655 | ✅ All absent from open PRs |
| **Open PRs remaining** | 0 | — |

---

## 8. Summary

| Metric | Value |
|--------|-------|
| Dashboard refresh | 12:14Z (no 14Z refresh yet) |
| PRs merged | #1253 |
| New findings | FINDING-18 (COMMODITY 24h zero — monitor) |
| Active findings | FINDING-15 (3-AI consensus needed), FINDING-17 (HOLD n=18) |
| Resolved findings | FINDING-16 |
| Kill actions | None (protocol: 3-AI consensus required) |
| Next action | 15Z: re-check FINDING-17 n count; re-check FINDING-18 trend; validate rapid_fire/UUSDT + cta_replicator/NG=F against raw data |

**FOREX recovery post-PR-#687 is the headline positive:** 7d PF 0.14→1.289 (+1.149). System is net-improving. CRYPTO 24h PF 2.382 strong. Main drag: EQUITY 7d (0.238 on n=15 — post-goldmine_6x kill, small sample normalizing). COMMODITY 7d under pressure from cftc_cot 7d deterioration (FINDING-17).

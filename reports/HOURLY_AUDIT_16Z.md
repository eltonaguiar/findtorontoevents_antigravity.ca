# Hourly Audit — 2026-05-20T16Z

**Generated:** 2026-05-20T16:10Z  
**Snapshot timestamp:** 2026-05-20T04:13Z (12h stale — cron ran 15:31Z but no generated_at refresh; dashboard generator likely not triggered)  
**Previous audit:** #1266 (15Z) — merged this hour ✅  
**Operator:** Claude Sonnet 4.6

---

## 1. Dashboard Refresh Status

- `dashboard_data.json` last git commit: 15:31Z (portfolio tracker update, not a full regen)
- `generated_at` field: 2026-05-20T04:13Z — **12h stale**
- File size: 41.9 MB (healthy, non-empty)
- Action: no manual intervention needed; cron will refresh next hour cycle

---

## 2. Per-Asset Metrics — 16Z Snapshot

Rolling windows computed from `picks.recent_closed` (n=3500) at 16:10Z against the 04:13Z snapshot.

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|-------|--------|--------|-------|-------|-------|------|--------|--------|-------|
| CRYPTO | 0.72 | 34.7% | 75 | 1.23 | 46.8% | 941 | 1.32 | 46.4% | 2762 |
| EQUITY | 0.15 | 10.0% | 10 | 0.66 | 29.3% | 41 | 1.43 | 44.5% | 146 |
| FOREX | 1.28 | 42.9% | 7 | 1.31 | 35.3% | 17 | 2.51 | 48.4% | 93 |
| COMMODITY | 0.00 | 0.0% | 12 | 0.10 | 7.9% | 38 | 0.96 | 42.5% | 73 |
| ETF | — | — | 0 | 1.23 | 31.2% | 16 | 1.92 | 56.0% | 50 |
| BOND | — | — | 0 | 0.00 | 0.0% | 3 | 0.00 | 0.0% | 3 |
| FUTURES | — | — | 0 | — | — | 0 | inf | 100% | 2 |

### Delta vs 15Z audit

| Class | 7d PF Δ | 30d PF Δ | Note |
|-------|---------|---------|------|
| CRYPTO | 1.23 vs 1.25 (−0.02) | 1.32 vs 1.34 (−0.02) | Slight rolling slide, within noise |
| EQUITY | 0.66 vs 0.64 (+0.02) | 1.43 vs 1.45 (−0.02) | Marginal fluctuation |
| FOREX | 1.31 vs 1.27 (+0.04) | 2.51 vs 2.51 (stable) | #687 JPY-cross fix holding |
| COMMODITY | 0.10 vs 0.10 (stable) | 0.96 vs 0.96 (stable) | CRITICAL unchanged |
| ETF | 1.23 vs 1.23 (stable) | 1.92 vs 1.92 (stable) | Healthy |

### Delta vs documented baseline

| Class | Window | 16Z | Baseline | Delta | Status |
|-------|--------|-----|----------|-------|--------|
| CRYPTO | 24h | 0.72 | 3.54 | −2.82 | ⚠️ 24h dip; 7d stable |
| CRYPTO | 7d | 1.23 | 1.33 | −0.10 | Mild slide |
| CRYPTO | 30d | 1.32 | 1.33 | −0.01 | Stable |
| EQUITY | 7d | 0.66 | 0.87 | −0.21 | Worsening (stocks_rsi2_pullback drag) |
| EQUITY | 30d | 1.43 | 1.41–2.18 | +0.02 | Holding lower end |
| FOREX | 7d | 1.31 | 0.14 pre-#687 | +1.17 | Major recovery — JPY-cross fix confirmed |
| FOREX | 30d | 2.51 | 0.97 pre-#687 | +1.54 | Strong recovery |
| COMMODITY | 7d | 0.10 | — | — | 🔴 CRITICAL (unchanged) |

---

## 3. Strategy Attribution (16Z)

### COMMODITY 7d — 3 strategies, all catastrophic
| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| cftc_cot_commercial_signal | 20 | 5% | 0.11 | −65.79% |
| futures_momentum | 17 | 12% | 0.09 | −52.81% |
| futures_bb_mean_reversion | 1 | 0% | 0.00 | −6.41% |

### EQUITY 7d — stocks_rsi2_pullback dominant drag
| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| stocks_rsi2_pullback | 27 | 33% | 0.94 | −3.13% |
| adx-trend-scout | 2 | 50% | 0.34 | −5.23% |
| macd-hidden-div-scout | 1 | 0% | 0.00 | −6.68% |
| vol-contraction-scout | 3 | 33% | 1.11 | +0.97% |
| aroon-trend-scout | 1 | 100% | inf | +4.05% |

### CRYPTO 24h — `unknown` bright spot; alpha_engine consensus dragging
| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| strong consensus (alpha_engine, ml_crypto_pred) | 27 | 15% | 0.18 | −41.60% |
| st_fear_greed_contrarian | 17 | 47% | 0.90 | −0.70% |
| luxalgo_confluence | 8 | 38% | 2.81 | +6.51% |
| unknown | 10 | 70% | 6.21 | +16.37% |
| super consensus | 2 | 50% | 3.62 | +5.76% |

---

## 4. Findings Status (16Z)

### FINDING-35: `futures_momentum` — WATCH (no change)
- All-time: n=18, WR=11.1%, PF=0.09
- 7d: n=17, WR=12%, sum=−52.81%
- Status: 2 picks from n=20 kill floor. No escalation. Monitor → trigger at n=20.

### FINDING-36: `stocks_rsi2_pullback` — MUTATION SANDBOX QUEUED
- 7d: n=28 (window roll from n=30 at 15Z), WR=35.7%
- 7d PF=0.94 — below kill PF threshold but above 0.5. WR<40% persistent.
- Action: Axis 1 inverse test queued for 17Z

### FINDING-22: `cftc_cot_commercial_signal` — REVISED DOWNWARD
- 7d: n=20, WR=5%, PF=0.11, sum=−65.79% (catastrophic short-term)
- All-time: n=53, WR=54.7%, sum=+54.34% (strong long-term baseline)
- REVISION: NOT a kill candidate. 7d crash is anomalous vs strong long-term WR=54.7%.
  Per kill protocol: WR<35% must be *sustained*, not a regime dip.
- New action: Escalate to commodity regime investigation. Do NOT add to BLOCKED_ASSET_STRATEGY_PAIRS.

### FINDING-24: HYPEUSDT gate bypass — P0 CONFIRMED
- #694 blocked `quan_engine` label; HYPEUSDT continues via `strategy=unknown`
- 7d via `unknown`: n=53 picks (last closed 2026-05-20T00:09Z — post-#694)
- Root cause: symbol block was strategy-scoped, not symbol-level
- Required fix: symbol-level block at ingestion/resolution layer
- Status: P0, awaiting 3-AI consensus for fix PR

### FINDING-31: `rapid_fire × UUSDT` — 1/3 AI consensus confirmed
- n=34, WR=0%, avg=−0.17% — independently confirmed by mutation_analysis.py

### FINDING-32: `cta_replicator × NG=F` — 1/3 AI consensus confirmed
- n=24, WR=0% — independently confirmed by mutation_analysis.py

### Kill verifications
| Strategy | 7d status | PR |
|----------|-----------|-----|
| forex_carry_momentum | n=0 ✅ DEAD | #692 |
| goldmine_6x_consensus | n=0 ✅ DEAD | #692 |
| cftc_cot | n=0 ✅ DEAD | #683 |
| forex_rsi2_mean_reversion | n=0 ✅ DEAD | #692 |

---

## 5. PR Triage

- **#1266** (15Z audit): **MERGED THIS HOUR** ✅ (mergeable=clean, Greptile COMMENTED only, [skip ci])
- **HOLD set** (#660 #658 #681 #661): Absent ✅
- **Author-rebase watch** (#669 #676 #608 #665 #644 #597 #615 #655): All resolved ✅

---

## 6. Mutation Analysis — 16Z Run Signals

| Signal | Details | Action |
|--------|---------|--------|
| rapid_fire × UUSDT | n=34 WR=0% avg=−0.17% | 1/3 AI consensus ✅ |
| cta_replicator × NG=F | n=24 WR=0% | 1/3 AI consensus ✅ |
| cta_replicator × ZC=F | n=8 WR=0% | Below n=20 — WATCH |
| quan_engine HYPEUSDT | n=553 WR=41.6% avg=−0.22% | `unknown` bypass — FINDING-24 |

No new PF<0.5 + n≥20 strategies beyond known findings.

---

## 7. Notable Observations

1. **CRYPTO 24h PF=0.72**: driven by alpha_engine+ml_crypto_pred consensus path (n=27 WR=15%). `unknown` and `luxalgo_confluence` are strongly positive (70% WR, 6.21 PF). 24h dip only — do not destabilize.
2. **FINDING-22 revision**: cftc_cot_commercial_signal all-time WR=54.7% is one of the best non-CRYPTO baselines. 7d crash is anomalous — commodity regime investigation required.
3. **Dashboard 12h stale**: no action; cron running but not triggering full regen cycle.

---

## 8. Actions Taken

- ✅ Merged PR #1266 (15Z audit)
- ✅ Ran mutation_analysis.py — 0 new kill-floor breaches
- ✅ FINDING-22 revised: kill-candidate → anomaly-investigation
- ✅ FINDING-24 HYPEUSDT bypass evidence extended (active post-#694)
- ✅ FINDING-31 + FINDING-32 confirmed by mutation_analysis.py

## 9. Next Hour (17Z)

- [ ] Dashboard snapshot timestamp check
- [ ] FINDING-35: futures_momentum n≥20 trigger check
- [ ] FINDING-36: Axis 1 inverse test for stocks_rsi2_pullback
- [ ] FINDING-24: draft symbol-level HYPEUSDT block PR
- [ ] FINDING-22: commodity regime investigation
- [ ] Post issue #686 update

---

_Refs: issues #685 #686 #693 | PRs #683 #684 #687 #692 #694 | `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`_

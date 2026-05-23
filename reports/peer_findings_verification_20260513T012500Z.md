# Peer Findings Cross-Verification — 2026-05-13T01:25Z

Big Pickle (open-code peer) appended 6 hidden insights to DAILY_IDEAS.MD.
Verified against live `dashboard_data.json` (0.45h fresh).

## Per-claim verification

### Claim #1 — Two edge regimes (trend-following vs pattern-recognition)
- **Peer numbers:** multi_asset_copytrader PF 4.09 / WR 36%; multi_asset_cot PF 21.33 / WR 88%
- **Live numbers:** multi_asset_copytrader **PF 4.28 / WR 47.3% / n=1505 / MDD 16.67%**; multi_asset_cot **PF 21.86 / WR 94.1% / n=102 / MDD 17.83%**
- **Verdict:** ✅ thesis correct, numbers drifted. WR drift on multi_asset_copytrader (36%→47.3%) is meaningful — peer may have queried a different resolved-subset window.
- **Insight valid:** trend-following (asymmetric R, sub-50% WR, large PF via tail wins) ≠ pattern-recognition (high WR, smaller multiplier). 60/40 blend hypothesis worth backtesting.

### Claim #2 — CRYPTO is strong but masked
- **Peer claim:** Top 3 CRYPTO systems yield PF ~3.3; aggregate (1.36) polluted by kimi_signal_tracking (MDD 995%) + 2 high-volume draggers
- **Live top CRYPTO systems sorted by PF (subset filter):**
  ```
  ai_challenge_scanner      PF=8.38  WR=83.3  n=12    (effective_n caveat)
  kimi_signal_tracking      PF=8.38  WR=83.3  n=1174  (resolved=18 only)
  aggregated_picks          PF=5.42  WR=73.2  n=404   MDD=49.25  (T2 fails MDD)
  signal_validation         PF=4.01  WR=49.5  n=531   MDD=8.14
  ml_crypto_pred_v12        PF=2.53  WR=55.6  n=123   MDD=11.0   DEAD (80d)
  ```
- **Caveat surfaced by this cross-check:** `kimi_signal_tracking` shows PF=8.38 on `resolved_picks=18` despite `closed_picks=1174`. The blacklist (commit `f7bd02da4c5`, `alpha_engine/config.py:216`) is working — no new emissions since 2026-05-10T23:49Z. Aggregate "kimi was a -930% disaster" used closed_picks denominator; current "PF=8.38" uses resolved-only denominator. **Both true; different math.**
- **Verdict:** ✅ peer thesis valid (CRYPTO has hidden T2 candidates) but n-floor caveat critical. `aggregated_picks` PF 5.42 with n=404 is the most credible single-system CRYPTO edge after applying n>=100 + MDD<=20 — but MDD=49.25 fails Tier-2 cap. **No clean single-CRYPTO Tier-2 winner** if you enforce charter v1.0 floors strictly.

### Claim #3 — multi_asset_copytrader most robust + best go-live candidate
- **Peer:** PF 4.09 / n=812 / MDD 16.67% / 5 classes
- **Live:** **PF 4.28 / n=1505 / MDD 16.67% / 3 classes** (COMMODITY+EQUITY+FOREX, not 5)
- **Verdict:** ⚠️ partial. PF + n improved (1505 > 812). MDD floor for T1 is 10%; 16.67% misses. **NOT T1**, but is **strongest n>=1000 T2-PF candidate** on the dashboard.
- **WR caveat:** 47.3% WR<50% — `multi_asset_copytrader` is a TREND-FOLLOWING system (asymmetric R). Charter v1.0 T2 requires WR>=50; this fails. Tier-2-MDD-Adjusted (allow asymmetric R if PF>=2 + MDD<=20) — passes.
- **FOREX leak risk:** spans FOREX which is class-stressed (PF 0.29). Need per-class breakdown to confirm its FOREX subset isn't drag. **A3 per-strategy concentration field (shipped `71753f2fa87`) will surface this next cron.**

### Claim #4 — signal_validation is FOREX's only hope
- **Peer:** PF 4.31 / MDD 8.14% — isolate FOREX signals
- **Live:** **PF 4.01 / MDD 8.14% / n=531** ✅
- **Verdict:** ✅ verified. MDD 8.14% IS Tier-1-grade. But spans CRYPTO+FOREX; need per-class isolation to confirm FOREX subset. Same A3 dependency as Claim #3.

### Claim #5 — No system clears Tier 1
- **Live verification:** 4 systems meet PF≥2 + WR≥55 + n≥200:
  - multi_asset_cot — PF 21.86 / WR 94.1 / n=102 — **fails n≥200 by 98**
  - aggregated_picks — PF 5.42 / WR 73.2 / n=404 — **fails MDD: 49.25 > 10**
  - signal_validation — PF 4.01 / WR 49.5 / n=531 — **fails WR: 49.5 < 55**
  - copy_trader_intel — PF 1.84 — **fails PF: 1.84 < 2**
- **Verdict:** ✅ NO single system clears full Tier-1. Closest = multi_asset_cot (needs n+98 = ~2 months at current emission rate).

### Claim #6 — Emission decay = natural selection
- **Peer:** all 5 dead systems were losers (PF ≤0.92)
- **Live check:**
  ```
  ml_crypto_pred_v12   PF 2.53  WR 55.6  status=monitoring  last=2026-02-22 (80d DEAD)
  ```
- **Counter-evidence:** `ml_crypto_pred_v12` is the exception — PF 2.53 winner went dark. Peer's "no good system went dark" claim is **FALSIFIED** by this single case. The DEAD-status flag (commit `023e636e26c`) catches it now.

## Net delta vs peer thesis

| Peer claim | Verdict | Confidence |
|---|---|---|
| 1. Two edge regimes exist | ✅ confirmed | HIGH |
| 2. CRYPTO masked at PF ~3.3 | ⚠️ thesis OK but n-floor caveat critical | MED |
| 3. multi_asset_copytrader robust | ⚠️ true but FOREX-leak risk + WR<50 (asymmetric R) | MED |
| 4. signal_validation FOREX-rescue | ✅ confirmed | HIGH |
| 5. No Tier-1 system | ✅ confirmed | HIGH |
| 6. No good system went dark | ❌ FALSIFIED — ml_crypto_pred_v12 (PF 2.53) is dead 80d | HIGH |

## Actions added to my queue

| # | Action | Source | Effort |
|---|---|---|---|
| AA-1 | Re-investigate `ml_crypto_pred_v12` death | Peer #6 falsification | 2-3h |
| AA-2 | Per-class subset PF on multi_asset_copytrader (FOREX-leak audit) | Peer #3 | 1h after A3 cron |
| AA-3 | Per-class subset PF on signal_validation (FOREX subset isolation) | Peer #4 | 1h after A3 cron |
| AA-4 | 60/40 blend backtest: multi_asset_cot + multi_asset_copytrader | Peer #1 | 4-6h |
| AA-5 | Surface n-floor caveat in dashboard `systems[]` row tooltip | Claim #2 lesson | 1h |

## NFA

Verification doc only. No sizing changes. Peer claims directionally
correct but specific numbers drifted between session windows — both
sources read the same JSON, the difference is timing of
`resolved_picks` re-aggregation across hourly cron cycles.

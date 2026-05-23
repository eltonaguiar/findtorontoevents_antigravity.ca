# Hourly Audit — 2026-05-06 03Z

**Audit time:** 2026-05-06T03:15Z  
**Dashboard snapshot:** 2026-05-06T02:28:37Z (44 min old)  
**Auditor:** Claude Sonnet 4.6  
**Prior session:** 02Z (PR #842) — merged #836, #839, #840

---

## 1. Dashboard Refresh Status

- Dashboard regenerated at 02:28Z via [skip ci] hourly cron — data is fresh.
- `git pull --rebase origin main` applied cleanly (10 files changed: price_cache, top_gainers, forward_stats, forward_signals).
- recent_closed n=3500 (cap unchanged).

---

## 2. Per-Asset PF/WR — Live Windows

Baselines: issue #686 (2026-05-02 snapshot) and 02Z audit (PR #842).

### 24h Window (n_total=178)

| Class    | n   | PF    | WR%  | sum_pnl% | Delta vs #686 baseline |
|----------|-----|-------|------|----------|-----------------------|
| CRYPTO   | 168 | 1.61  | 50.0 | +127.77  | PF -1.93 (base 3.54) / WR -14pp |
| EQUITY   | 1   | 0.00  | 0.0  | -7.29    | n too small to rate |
| FOREX    | 3   | 2.79  | 66.7 | +0.77    | n too small to rate |
| COMMODITY| 6   | 10.88 | 83.3 | +22.85   | n too small to rate |
| ETF      | 0   | -     | -    | -        | - |
| BOND     | 0   | -     | -    | -        | - |

### 7d Window (n_total=915)

| Class    | n   | PF   | WR%  | sum_pnl%  | Delta vs #686 baseline | Tier status |
|----------|-----|------|------|-----------|----------------------|-------------|
| CRYPTO   | 743 | 1.49 | 49.8 | +329.88   | PF +0.28 / WR +8.8pp | Sub-T2 (PF<1.5 by margin) |
| EQUITY   | 18  | 1.54 | 55.6 | +19.38    | PF +0.67 / WR +14.6pp | T2 (PF>1.5, WR>50%) |
| FOREX    | 111 | 0.47 | 22.5 | -23.90    | PF +0.33 / WR +11.8pp | Sub-floor (PF<1.0) |
| COMMODITY| 35  | 1.64 | 45.7 | +28.56    | PF +0.46 | T2 PF (WR below 50%) |
| ETF      | 8   | 1.62 | 50.0 | +3.40     | PF +0.05 | T2 |
| BOND     | 0   | -    | -    | -         | - | n<floor |

### 30d Window (n_total=2731)

| Class    | n    | PF   | WR%  | sum_pnl%  | Delta vs #686 baseline | Tier status |
|----------|------|------|------|-----------|----------------------|-------------|
| CRYPTO   | 1499 | 1.30 | 43.6 | +347.05   | PF -0.03 (stable)  | Sub-T2 |
| EQUITY   | 127  | 2.88 | 63.0 | +247.02   | PF +1.47           | T1 (PF>2.0, WR>55%) |
| FOREX    | 561  | 0.63 | 45.3 | -19.68    | PF -0.34           | Sub-floor |
| COMMODITY| 502  | 1.09 | 41.6 | +10.09    | PF +0.05           | Sub-T2 |
| ETF      | 37   | 3.58 | 73.0 | +52.84    | PF +2.34           | T1 |
| BOND     | 0    | -    | -    | -         | - | n<floor |

---

## 3. Key Delta Analysis vs 02Z Audit

| Finding | 02Z (prior) | 03Z (now) | Assessment |
|---|---|---|---|
| EQUITY 7d PF | 1.52 | 1.54 | Stable T2 |
| EQUITY 30d PF | - | 2.88 | T1 — goldmine_6x kill confirmed effective |
| FOREX 7d PF | 1.48 | 0.47 | REGRESSION — see section 4 |
| FOREX 7d WR | - | 22.5% | forex_rsi2_mean_reversion LONG still active |
| CRYPTO 24h PF | - | 1.61 | Regression from baseline 3.54 (02Z didn't report 24h) |
| CRYPTO 7d PF | - | 1.49 | Near T2 floor (1.5), monitoring |
| COMMODITY 7d PF | - | 1.64 | T2 PF met; WR 45.7% still below 50% |
| ETF 30d PF | - | 3.58 | T1 excellent |

Issue #693 hypothesis confirmed: EQUITY 7d recovered from 0.87 to 1.54 after PR #692 (goldmine_6x_consensus kill). The 30d window (PF 2.88) shows the pre-drag baseline was T1-grade.

---

## 4. FOREX 7d Regression — forex_rsi2_mean_reversion LONG Still Active

FOREX 7d PF dropped from 1.48 (02Z) to 0.47 — investigation:

### Strategy breakdown (FOREX 7d, n=111):

| Strategy | n | WR% | PF | sum_pnl% |
|---|---|---|---|---|
| forex_rsi2_mean_reversion | 62 | 8.1% | 0.09 | -25.89 |
| MeanReversionBB | 15 | 53.3% | 1.63 | +5.55 |
| fx_smart_carry_trade_momentum | 9 | 11.1% | 0.21 | -1.90 |
| non_crypto_consensus | 9 | 55.6% | 1.75 | +0.01 |
| combined_confidence | 6 | 33.3% | 0.57 | -0.84 |
| fx_smart_forex_rsi2_mean_reversion | 4 | 50.0% | 1.67 | +0.40 |

forex_rsi2_mean_reversion is the sole drag: n=62, WR 8.1%, PF 0.09, -25.89% sum in 7 days.
forex_carry_momentum is ABSENT — PR #692 kill confirmed working.

### Symbol breakdown (FOREX 7d, top by n):

| Symbol | n | WR% | sum_pnl% |
|---|---|---|---|
| EURJPY=X | 39 | 7.7% | -16.58 |
| USDJPY=X | 27 | 22.2% | -6.85 |
| GBPJPY=X | 13 | 15.4% | -4.29 |
| GBP-USD | 8 | 50.0% | +4.00 |
| EUR-USD | 6 | 50.0% | -0.22 |

JPY crosses (EURJPY+USDJPY+GBPJPY) = n=79/111 (71%) of FOREX 7d. PR #687 blocked the BUY rule for JPY-crosses but the overall JPY-cross presence remains the dominant drag — forex_rsi2_mean_reversion is the strategy running these.

### Mutation analysis:
forex_rsi2_mean_reversion LONG: WR 2.4% / n=82 (full history). SHORT: WR 27.3% / n=11. 25pp directional spread — LONG direction is the near-total source of loss.

Kill candidate status: ("FOREX", "forex_rsi2_mean_reversion") as LONG-direction block meets criteria:
- Pattern matches: same as killed forex_carry_momentum (catastrophic FOREX WR)
- n=62 in 7d / n=82 in full history >= 20
- WR 8.1% (7d) / 2.4% (LONG-only) — sustained < 35%
- Mutation analysis: LONG direction is the failure mode; SHORT is 3x better

Posting to issue #686 for 3-AI consensus gate. Do NOT block autonomously.

---

## 5. New Mutation Findings (mutation_analysis.py)

New entries meeting PF<0.5 + n>=20 + WR<35% (not previously documented):

| Strategy | Direction | WR% | n | Action |
|---|---|---|---|---|
| ig_contrarian_sentiment | LONG | 18.4% | 125 | Flagged prev 02Z — needs 3-AI consensus |
| myfxbook_retail_contrarian | LONG | 10.2% | 88 | In #837 shadow-demotion target; needs consensus |
| forex_rsi2_mean_reversion | LONG | 2.4% | 82 | NEW — posting to #686 |
| quan_engine_swing | LONG | 26.0% | 104 | New to this session — 34pp SHORT-LONG spread |
| rapid_fire::UUSDT | - | 0.0% | 34 | Flagged 02Z — needs 3-AI consensus |

Symbol-level: rapid_fire::UUSDT (WR=0%, n=34) and rapid_fire::TAOUSDT (WR=5.6%, n=18) are symbol-block candidates (not full-strategy kill).

No auto-kills taken. Per protocol: all require 3+ AI consensus + mutation/inverse/symbol-rotation tests.

---

## 6. PR Triage

### Open PRs (7 total):

| PR | Title | CI | Mergeable | Verdict |
|---|---|---|---|---|
| #835 | fix(crypto): suppress st_fear_greed_contrarian | scan=CANCELLED, others OK | - | HOLD — scan rerun needed |
| #837 | feat(gates): auto-shadow-probation | All 4 OK | dirty (conflict) | HOLD — merge conflict + 2x REQUEST_CHANGES (test coverage) |
| #838 | feat(hermes): swarm commands | scan only (1 check) | dirty (conflict) | HOLD — incomplete CI + conflict |
| #841 | docs(audit): outlier audit | No checks | conflict | HOLD — no CI + conflict |
| #842 | audit(hourly): 02Z | scan only | - | HOLD — incomplete CI |
| #843 | feat(b5): concept-aware scoring | All 4 OK | dirty (conflict) | HOLD — merge conflict |
| #844 | feat: ruflo/SWARM audit tools | No checks | - | HOLD — no CI runs |

Merges this hour: 0

HOLD set (#660 #658 #681 #661): confirmed closed prior sessions — no action.
Rebase set (#669 #676 #608 #665 #644 #597 #615 #655): confirmed all closed per 02Z audit — no action.

### Notes on specific PRs:
- #835: scan job was cancelled at prior push (2026-05-05T20:32 race). Author should rerun scan; other 3 checks green, change is 1-line low-risk.
- #843 (B5 concept-scorer): All 4 CI green but base drifted to stale commit (5c989cb vs current main 9e246457). Conflict on merge — author needs to rebase. Solid PR otherwise.
- #837: deepseek + xai both REQUEST_CHANGES for test coverage. Draft test file (8 tests, 182 lines) was written but failed to land due to force-push collision. Until test file is committed, cannot override REQUEST_CHANGES.
- #844: 7,732 lines / 9 new sidecar tools. Zero CI checks triggered. Wire-Up Rule: tools/SWARM/ and audit_trail/ utilities — PR body lacks a Wiring Plan section for the audit_trail/ files. Hold pending CI green.

---

## 7. Summary

| Metric | Value | Direction |
|---|---|---|
| PRs merged | 0 | - |
| New kill findings posted | 1 (forex_rsi2_mean_reversion to #686) | - |
| EQUITY status | T2 (7d) / T1 (30d) | Improving |
| FOREX status | Sub-floor (PF 0.47 7d / 0.63 30d) | Regressing |
| CRYPTO status | Near T2 floor (1.49 7d / 1.30 30d) | Stable |
| COMMODITY status | T2 PF (WR below 50%) | Improving |
| ETF status | T1 (30d PF 3.58) | Strong |

Next priority: forex_rsi2_mean_reversion LONG-direction block — gather 3-AI consensus, then add ("FOREX", "forex_rsi2_mean_reversion") to BLOCKED_ASSET_STRATEGY_PAIRS or a LONG-gate in quality_gates.py. This single strategy is responsible for ~100% of FOREX 7d losses.

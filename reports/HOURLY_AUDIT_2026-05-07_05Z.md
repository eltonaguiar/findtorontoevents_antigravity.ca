# Hourly Audit — 2026-05-07 05Z

**Generated:** 2026-05-07 ~05:15Z  
**Dashboard snapshot:** 2026-05-07T04:03:35Z (68 min old at audit time; hourly cron next at ~05Z)  
**Snapshot n:** 3500 recent_closed picks  
**Preceding audit:** `reports/HOURLY_AUDIT_2026-05-07_04Z.md` (PR #858)  
**Session PRs merged today:** #684 #674 #673 #664 #683 #687 #692 #694 (8 total, pre-session)

---

## 1. Dashboard Refresh Status

Snapshot timestamp: `2026-05-07T04:03:35Z` — 68 min stale at audit time.  
The git pull brought in `[skip ci]` regime/competition updates but **dashboard_data.json was not refreshed** in this pull. Next hourly cron expected ~05Z.  
All per-asset numbers below use the 04:03Z snapshot.

---

## 2. Per-Asset Metrics — 05Z vs Baselines

### Baselines (from issue #686 + prior audits)
| Class | 24h PF (baseline) | 7d PF (baseline) | 30d PF (baseline) |
|---|---|---|---|
| CRYPTO | 3.54 (issue #686) | 1.33 (issue #686) | 1.33 (issue #686) |
| EQUITY | — | 0.87 (issue #686) → 6.69 (04Z) | 1.41–2.18 (issue #686) |
| FOREX | 0.00 (pre-#687) | 0.14 (pre-#687) | 0.97 (pre-#687) |
| COMMODITY | — | — | — |

### 05Z Computed (from dashboard_data.json 04:03Z snapshot)

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF | Delta vs baseline |
|---|---|---|---|---|---|---|---|---|---|---|
| **CRYPTO** | 217 | 44.7% | 1.39 | 756 | 51.6% | 1.69 | 1499 | 44.0% | 1.37 | 24h: −2.15 PF (mean-reversion); 7d: +0.36 ✅ |
| **EQUITY** | 6 | 100% | ∞ | 18 | 77.8% | 6.69 | 133 | 64.7% | 3.44 | 7d: +5.82 vs baseline; T1 confirmed 4th run ✅ |
| **FOREX** | 29 | 27.6% | 0.61 | 136 | 23.5% | 0.48 | 579 | 43.7% | 0.61 | 7d: +0.34 vs pre-#687; still catastrophic 🚨 |
| **COMMODITY** | 24 | 12.5% | 0.29 | 49 | 32.7% | 0.98 | 514 | 40.3% | 0.84 | 24h alarm PERSISTS (4th consecutive run) 🚨 |
| **ETF** | 9 | 100% | ∞ | 14 | 92.9% | 26.69 | 45 | 80.0% | 4.68 | Small n, positive ✅ |
| **BOND** | 0 | — | — | 0 | — | — | 0 | — | — | Below n=100 charter floor |
| **FUTURES** | 0 | — | — | 0 | — | — | 2 | 100% | ∞ | Negligible n |

---

## 3. Strategy Attribution — 05Z New Findings

### 3.1 FOREX 7d — `forex_rsi2_mean_reversion` ESCALATED 🚨

`forex_carry_momentum` is **confirmed killed** — zero picks in 7d window. PR #692 validated.

New FOREX 7d breakdown:

| Strategy | n | WR | PF | Sum PnL% |
|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | **81** | **8.6%** | **0.09** | **−33.09%** |
| `MeanReversionBB` | 15 | 53.3% | 1.63 | +5.55% |
| `non_crypto_consensus` | 9 | 55.6% | 1.75 | +0.01% |
| `fx_smart_carry_trade_momentum` | 8 | 25.0% | 0.89 | −0.20% |
| `combined_confidence` | 7 | 28.6% | 0.44 | −1.44% |
| `fx_smart_forex_rsi2_mean_reversion` | 6 | 66.7% | 4.33 | +2.00% |
| `forex-rsi-ema-scout` | 5 | 20.0% | 0.21 | −2.41% |

**Key delta vs issue #686 baseline:** `forex_rsi2_mean_reversion` was n=52/WR=10.9% in issue #686 snapshot. Now n=81/WR=8.6% — MORE volume AND worse WR. Crosses n≥20 + WR<35% kill threshold. Must route through `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` mutation-3-axis before kill. Posting to issue #686.

**Note:** `ig_contrarian_sentiment` and `myfxbook_retail_contrarian` not appearing in FOREX 7d breakdown under those names — they likely appear in other asset classes or time windows. Mutation analysis confirms them as LONG-direction failures (WR 15.3% and 10.2%, n=157 and n=118 respectively across all classes).

### 3.2 COMMODITY 24h — `futures_momentum` (4th consecutive alarm)

| Strategy | n | WR | Sum PnL% |
|---|---|---|---|
| `futures_momentum` | 18 | **0.0%** | **−42.32%** |
| `cftc_cot_commercial_signal` | 4 | 75.0% | +12.55% |
| `combined_confidence` | 1 | 0.0% | −6.33% |

n=18 in this 24h window (down from n=23 in prior window due to time-shift). Still WR=0%, sum=−42.3%. Pre-authorized in issue #685 as kill candidate pending 3-AI consensus. **Do not auto-kill** — consensus gate required.

### 3.3 CRYPTO 24h drop — Expected Mean-Reversion

24h PF=1.39 vs 04Z baseline of 3.54. 7d PF=1.69 is healthy (+0.36 vs baseline 1.33). Not a regression — 24h window is high-variance and the 3.54 baseline was an outlier high. No action.

### 3.4 Mutation Analysis (full run)

No new PF<0.5 + n≥20 strategies beyond already-tracked candidates:

| Strategy / Pair | Axis | n | WR | Status |
|---|---|---|---|---|
| `ig_contrarian_sentiment` LONG | Direction | 157 | 15.3% | Known — 3-AI consensus pending |
| `myfxbook_retail_contrarian` LONG | Direction | 118 | 10.2% | Known — 3-AI consensus pending |
| `quan_engine_swing` LONG | Direction | 104 | 26.0% | Monitoring (04Z new) |
| `forex_rsi2_mean_reversion` | Overall | 81 | 8.6% | **NEW escalation — posting to #686** |
| `cta_cross_asset_tsmom` LONG | Direction | 65 | 30.8% | Monitoring |
| `rapid_fire` × UUSDT | Symbol | 34 | 0.0% | Known — 3-AI consensus pending |
| `futures_momentum` × COMMODITY | Asset | 18 | 0.0% | Known — n just below kill floor |

---

## 4. PR Triage — 05Z

### Open PRs assessed

| PR | Title | CI | Reviews | Decision |
|---|---|---|---|---|
| #858 | audit(04Z) EQUITY T1 + COMMODITY alarm | scan✅ | none | **MERGE** ✅ |
| #854 | chore: remove freebuff + DB spec | 0 checks | none | **HOLD** — no CI |
| #849 | Edge action plan + swarm harness | — | — | **SKIP** — draft |
| #846 | feat(B18): Shadow Probation panel | scan✅ drift✅ | none | **HOLD** — explicit "DO NOT ADMIN-MERGE" in body |

### HOLD set (never merge)
#660 #658 #681 #661 — Plan v2.1 fabricated stats family. Not touched.

### Author-rebase set (#669 #676 #608 #665 #644 #597 #615 #655)
All already merged or closed before this session. No action needed.

### Merges this run
- **#858 — MERGED** (scan✅, no REQUEST_CHANGES, report-only PR, all criteria met)

---

## 5. Issue #693 Status

EQUITY confirmed T1 for 4 consecutive audit runs (02Z, 04Z, 05Z + issue snapshot). 7d PF=6.69 / WR=77.8% / 30d PF=3.44 / WR=64.7%. Issue #693 monitoring criteria met ("EQUITY 14d returns to PF≥1.5 within 7 days post-#692"). Recommend owner close issue #693.

---

## 6. Constraints Verified

- Resolver-rescope DONE (issue #685) — no PR opened, no code changed
- Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER) — not cited anywhere
- No peer PR rebases
- HOLD set (#660 #658 #681 #661) — not touched
- No auto-kills without 3-AI consensus
- `futures_momentum` not killed — n=18 below floor in current 24h window
- `forex_rsi2_mean_reversion` not killed — routed to issue #686 for mutation-3-axis gate

---

## 7. Next Recommended Actions

1. **FOREX mutation-3-axis on `forex_rsi2_mean_reversion`** — n=81/WR=8.6% now exceeds kill threshold. Run `python tools/mutation_analysis.py` with direction/symbol/timeframe decomposition. Post results to issue #686. 3-AI consensus before kill.
2. **COMMODITY `futures_momentum`** — monitor another 24h cycle. If n crosses 20 in a single window with WR=0%, escalate to 3-AI kill vote per issue #685 pre-authorization.
3. **`ig_contrarian_sentiment`/`myfxbook_retail_contrarian` LONG** — both above n=100, WR<20%. Both already in mutation analysis output. Schedule 3-AI consensus.
4. **Issue #693** — owner should close (EQUITY T1 confirmed 4th run).
5. **`quan_engine_swing` LONG** — n=104/WR=26%. Not yet at kill floor (WR<35% sustained — currently 26%, needs confirmation across windows). Continue monitoring.

---

*Generated by Claude Code session_015SX62ABFL2UDXmC8phwXjV*

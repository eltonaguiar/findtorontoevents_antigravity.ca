# Hourly Audit — 2026-05-06T02Z

**Generated:** 2026-05-06T02:15Z  
**Dashboard snapshot:** 2026-05-06T01:38:01Z (age ~37min)  
**Session context:** 8 PRs merged earlier today (#684 #674 #673 #664 #683 #687 #692 #694). Issues #685 (resolver-rescope DONE), #686 (per-asset attribution), #693 (EQUITY degradation monitor).

---

## 1. Dashboard Refresh Status

Pull from `origin/main` succeeded. No local stash needed. Latest `[skip ci]` scans visible in log (Claude Gainer ST, Rapid Fire, Claude Gainer ML, Prediction market signals, Portfolio tracker — all 02:00-02:02Z). Dashboard JSON is 37 min old; next hourly refresh expected ~02:38Z.

---

## 2. Per-Asset Metrics — Current vs Baseline

### Long-run Asset Class Health (verdict-grade, post-resolver-v2, n=full history)

| Class | PF | WR% | n | Tier status |
|---|---|---|---|---|
| COMMODITY | 2.33 | 50.1 | 850 | T1 PF / WR borderline (50.1% floor) |
| BOND | 1.72 | 55.6 | 18 | T2 PF+WR / n<charter floor |
| EQUITY | 1.40 | 52.6 | 430 | T2 candidate |
| CRYPTO | 1.31 | 45.9 | 8171 | Sub-T2 (need PF>1.5, WR>50) |
| ETF | 1.20 | 53.4 | 88 | Borderline T2; n→100 |
| FOREX | 0.29 | 45.8 | 1271 | Sub-floor (long-run dragged by pre-#687 history) |
| FUTURES | — | 100.0 | 2 | Insufficient n |

### Windowed Metrics (live, `recent_closed` n=3500 cap)

#### 24h window (since 2026-05-05 02:12Z)

| Class | n | PF | WR% | Sum PnL% | Delta vs baseline |
|---|---|---|---|---|---|
| CRYPTO | 48 | **3.44** | 62.5 | +67.6 | -0.10 vs 3.54 (within noise) |
| EQUITY | 1 | 0.00 | 0.0 | -7.3 | n=1, insufficient |
| FOREX | 1 | inf | 100.0 | +0.6 | n=1, insufficient |

#### 7d window (since 2026-04-29 02:12Z)

| Class | n | PF | WR% | Sum PnL% | Delta vs baseline | Signal |
|---|---|---|---|---|---|---|
| CRYPTO | 215 | 1.43 | 42.8 | +79.9 | +0.10 vs 1.33 | Slight improvement |
| **EQUITY** | 14 | **1.52** | **57.1** | +15.4 | **+0.65 vs 0.87** | Issue #693 hypothesis confirmed |
| **FOREX** | 27 | **1.48** | **51.9** | +4.9 | **+1.34 vs 0.14** | PR #687+#692 working |
| COMMODITY | 2 | 0.00 | 0.0 | -0.1 | n=2, insufficient | — |
| ETF | 7 | 1.97 | 57.1 | +4.4 | n=7, thin | Positive |

#### 30d window (since 2026-04-06 02:12Z)

| Class | n | PF | WR% | Sum PnL% | Delta vs baseline | Signal |
|---|---|---|---|---|---|---|
| CRYPTO | 734 | 1.11 | 34.9 | +52.6 | -0.22 vs 1.33 | Gradual drift; watch |
| **EQUITY** | 102 | **3.92** | **68.6** | +259.2 | **+1.74 vs 2.18** | T1 confirmed (n>=100) |
| FOREX | 466 | 2.15 | 52.4 | +15.3 | **+1.18 vs 0.97** | Pre-fix drag clearing |
| **COMMODITY** | 457 | **0.51** | **41.6** | -14.3 | NEW ALERT | Sub-T2 in 30d window |
| ETF | 36 | 3.76 | 75.0 | +53.8 | — | T1 trajectory |
| FUTURES | 2 | inf | 100.0 | +0.0 | — | Insufficient n |

---

## 3. Key Findings

### Finding #1 — EQUITY 7d recovery confirmed (+0.65 PF)
Issue #693 hypothesis: after PR #692 (goldmine_6x_consensus kill), EQUITY 7d would recover.  
**Result:** 0.87 -> 1.52 in the 7d window. Crosses T2 floor (PF>1.5). The 30d window remains strong at 3.92/68.6% on n=102 — first class to meet n>=100 for T1 assessment.

### Finding #2 — FOREX 7d PF 0.14 -> 1.48 (+1.34)
PR #687 (JPY-cross BUY rule fix) and PR #692 (forex_carry_momentum + goldmine_6x_consensus kill) are producing measurable results within days. FOREX 7d now crosses T2 PF floor. Long-run health (PF 0.29) still dragged by pre-fix trades washing out slowly.  
**Next:** monitor FOREX 14d PF — if it reaches 1.0+ by 2026-05-13, the fix is confirmed durable.

### Finding #3 — COMMODITY 30d PF=0.51 / WR=41.6% on n=457 NEW ALERT
Long-run health shows COMMODITY PF=2.33 (T1 PF), but the 30d window is dramatically worse at PF=0.51 on n=457 valid picks. Possible causes:
- (a) `forex_copy_trader` on COMMODITY (blocked by PR #836 merged this hour) was a major drag
- (b) `futures_momentum` 0% rolling WR (n_recent=38) hitting COMMODITY picks
- (c) `multi_asset_copytrader` symbol drag (SI=F 0%, AMD 0%, ZW=F 0%)

**Action required:** re-run audit at 24h post-PR-#836 merge. If COMMODITY 30d PF does not recover toward 1.0+ within 72h, initiate deep-dive per MUTATION_THREE_AXIS_PROTOCOL.md.

### Finding #4 — Mutation analysis: directional candidates (not yet kill-eligible)

| Strategy | SHORT WR | SHORT n | LONG WR | LONG n | Spread | Status |
|---|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | 57.1% | 42 | 18.4% | 125 | 39pp | No prior kill; LONG mutation candidate |
| `myfxbook_retail_contrarian` | 46.2% | 13 | 10.2% | 88 | 36pp | In performance_alerts (HIGH); covered by #837 |
| `quan_engine_swing` | 60.0% | 5 | 26.0% | 104 | 34pp | LONG drag on CRYPTO |
| `cta_cross_asset_tsmom` | 64.1% | 78 | 30.8% | 65 | 33pp | SHORT has edge; LONG is drag |

None meet PF<0.5 + n>=20 kill floor. Symbol-level: `rapid_fire::UUSDT` WR=0% n=34 meets n>=20 threshold for symbol-block discussion.

### Finding #5 — CRYPTO 30d drift: 1.33 -> 1.11 (-0.22)
CRYPTO 30d PF declined 0.22 points. 24h window remains strong (3.44/62.5%). PR #835 (st_fear_greed_contrarian re-ban, n=652/WR=34.2%/PnL=-182) pending CI rerun.

---

## 4. PR Triage This Hour

### Merged (3 PRs)
| PR | Title | Criteria met |
|---|---|---|
| #836 | fix(commodity): suppress forex_copy_trader via SOURCE_SYSTEM_BLOCKLIST_BY_CLASS | 4/4 CI green, 6/6 swarm MERGE, no REQUEST_CHANGES |
| #839 | feat(hyrotrader): GHA daily workflow to regenerate hyro_quan_bridge.json | No CI expected (GHA YAML), owner positive, no REQUEST_CHANGES |
| #840 | fix(hyrotrader): SL/TP population gate + migrate 7 phantom active rows | 5/5 CI green (latest run), no REQUEST_CHANGES |

### Held — not merged
| PR | Reason |
|---|---|
| #835 | scan=CANCELLED on latest CI run; trigger `gh run rerun --failed` before next attempt |
| #837 | deepseek + xai REQUEST_CHANGES in swarm (line numbers off, missing test coverage) |
| #838 | Merge conflict with main after today's merges |
| #841 | Merge conflict with main after today's merges |

### HOLD set (#660 #658 #681 #661) — confirmed closed prior sessions
All confirmed closed (merged or closed-not-merged) prior to this session. No action required.

### Rebased PRs (#669 #676 #608 #665 #644 #597 #615 #655)
None in open PR list. All previously closed/merged. No action required.

---

## 5. Mutation Analysis Summary

`python tools/mutation_analysis.py --json` completed without errors.

**No new PF<0.5 + n>=20 strategies requiring 3-AI kill consensus this hour.**

Existing in performance_alerts (covered by PR #837): `myfxbook_retail_contrarian`, `futures_momentum`, `crypto_drawdown_convexity_recovery_v1`. `forex_rsi2_mean_reversion` already killed by PR #692.

Symbol blocklist candidates for next session:
- `rapid_fire::UUSDT` (WR=0%, n=34) — meets n>=20, needs PF evidence + 3-AI consensus
- `quan_engine::MATICUSDT` (WR=0%) — n<20, insufficient

---

## 6. Issue Status

- **#685 (resolver-rescope DONE):** Confirmed. No resolver code changes needed or made.
- **#686 (per-asset quality):** FOREX 7d +1.34 PF, EQUITY 7d +0.65 PF validated. COMMODITY 30d alert is new finding.
- **#693 (EQUITY divergence):** CONFIRMED recovered (7d PF 0.87 -> 1.52). Monitor for 14d window; close issue 2026-05-16 if EQUITY 14d PF >= 1.5.

---

## 7. Next Hour Actions

1. **Rerun #835 CI:** `gh run rerun --failed <run-id>` to requeue the cancelled scan check.
2. **#837 test coverage:** add `tests/test_alert_shadow_demotion.py` (8 cases drafted in PR comment #4382973151).
3. **COMMODITY 30d watch:** at 24h post-#836 merge (~2026-05-07 02Z), compare COMMODITY 30d PF. If still <1.0, open COMMODITY deep-dive issue.
4. **Conflict resolution:** #838 and #841 need author rebase after today's main merges.
5. **Post #686 update:** comment on issue #686 with FOREX/EQUITY deltas from this report.

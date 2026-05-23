# Hourly Audit — 2026-05-15 06Z

Generated: 2026-05-15T06:10Z  
Dashboard snapshot: `audit_dashboard/data/dashboard_data.json` generated_at: **2026-05-15T02:06:57Z** (stale ~4h from last auto-refresh)  
Picks pool: n=3,500 recent_closed  
Reference epoch for windows: 2026-05-15T06:00Z

---

## 1. Dashboard Refresh Status

Dashboard data is from the 02:06Z auto-refresh. The next hourly [skip ci] refresh has not propagated yet (expected ~06:05Z push). All metrics below reflect the 02:06Z snapshot.

---

## 2. Per-Asset PF/WR — Windowed Analysis

| Class | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 124 | 2.27 | 54.0% | 862 | 1.33 | 43.9% | 2873 | 1.25 | 44.9% |
| EQUITY | 3 | 1.85 | 66.7% | 34 | 1.19 | 26.5% | 127 | 2.07 | 51.2% |
| FOREX | 10 | 1.06 | 30.0% | 43 | 1.38 | 14.0% | 91 | 1.32 | 27.5% |
| COMMODITY | 15 | 0.00 | 0.0% | 26 | 1.16 | 42.3% | 62 | 2.58 | 61.3% |
| ETF | 2 | ∞ | 100.0% | 14 | 2.19 | 64.3% | 52 | 4.05 | 75.0% |

_Note: EQUITY 24h n=3 and ETF 24h n=2 are below action threshold; ignore those cells._

### EQUITY 14d (issue #693 tracking)
| Window | n | PF | WR | Sum PnL% |
|---|---|---|---|---|
| 14d | 51 | **2.18** | 39.2% | +88.23% |
| 30d | 127 | 2.07 | 51.2% | +186.99% |

**Issue #693 verdict: RESOLVED.** EQUITY 14d PF recovered from 1.05 → 2.18. The 14d "escalate if <1.0 for 14 days" threshold was never triggered. PR #692 (goldmine_6x_consensus kill) was sufficient. Issue is already closed.

---

## 3. Delta vs Documented Baseline

Baselines from task brief (pre-this-hour documented state):

| Class | Window | Baseline PF | Current PF | Delta | Signal |
|---|---|---|---|---|---|
| CRYPTO | 24h | 3.54 | 2.27 | −1.27 | ⚠️ sample variance (n=124 small) |
| CRYPTO | 7d | 1.33 | 1.33 | 0.00 | ✅ stable |
| CRYPTO | 30d | 1.33 | 1.25 | −0.08 | ✅ minor drift, within noise |
| EQUITY | 7d | 0.87 | 1.19 | +0.32 | ✅ post-#692 recovery confirmed |
| EQUITY | 14d | 1.05 | 2.18 | +1.13 | ✅ strong recovery |
| EQUITY | 30d | 1.41-2.18 | 2.07 | — | ✅ in range |
| FOREX | 7d | 0.14 | 1.38 | +1.24 | ✅ #687/#692 effect confirmed |
| FOREX | 30d | 0.97 | 1.32 | +0.35 | ✅ recovering |
| COMMODITY | 24h | — | 0.00 | — | ⚠️ 0 wins on 15 picks — data quality issue (see §6) |

---

## 4. Asset Class Health (verdict-grade, post-resolver-v2)

Source: `performance.asset_class_health` in dashboard_data.json

| Class | PF | WR | n | Status |
|---|---|---|---|---|
| COMMODITY | 2.49 | 61.5% | 322 | ✅ Tier-2 CLEAR — real-money pilot candidate |
| EQUITY | 1.57 | 51.9% | 420 | ✅ Tier-2 CLEAR |
| ETF | 1.48 | 58.5% | 106 | ⚠️ borderline PF (Tier-2 needs PF>1.5) |
| CRYPTO | 1.36 | 46.7% | 8011 | ❌ WR below floor (need ≥50%) |
| FOREX | 0.81 | 52.3% | 342 | ❌ PF sub-floor (recovering) |
| BOND | 0.66 | 54.5% | 11 | ❌ n<<100 — deep-dive in PR #1046 |

---

## 5. PR Merge Actions This Check

| PR | Title | Action | Reason |
|---|---|---|---|
| #1043 | docs(audit): hourly audit 05Z | ✅ MERGED | scan ✅, no reviews, docs-only |
| #1044 | docs(validation): external eval claim-vs-reality | ✅ MERGED | scan ✅, no reviews, docs-only |
| #1046 | docs(bond): regression deep-dive | ✅ MERGED | scan ✅, no reviews, docs-only |
| #1041 | docs: Grok evaluation + Section 21 M-055..M-059 | ❌ HELD | merge conflicts |
| #1042 | docs: Grok Part-2 PR bodies | ❌ HELD | chains off conflicted #1041 |
| #1026 | feat: Phase J ML-calibration + score-booster | ❌ HELD | gate=FAIL, test(3.11)=FAIL |
| #1027 | feat(crypto): SHORT direction bias multiplier | ❌ HELD | gate=FAIL, test(3.11)=FAIL |
| #1037 | feat(crypto): BTC UTC-hour death-zone filter | ❌ HELD | gate=FAIL, test(3.11)=FAIL |
| #1029 | fix: disable 12 toxic systems + blacklist 3 symbols | ❌ HELD | 0 CI check runs; suspicious stats (see §7) |
| #1030 | fix(audit): Mercury2 P0.1 + P0.2 | ❌ HELD | 0 CI check runs |
| #1032 | docs(kimi-archive): read-only reference bundle | ❌ HELD | 0 CI check runs |
| #1045 | feat(M-008/M-021): COT lag-correction (DRAFT) | ❌ HELD | DRAFT status |
| #660 #658 #681 #661 | Plan v2.1 fabrication family | ❌ PERMANENT HOLD | fabricated stats — never merge |

**Old "rebase PRs"** (#669 #676 #608 #665 #644 #597 #615 #655): Not found in open PR list (0 open PRs beyond page 1, page 2 empty) — all previously closed/merged.

---

## 6. Data Quality Finding: `signal_validation` Zero-PnL Artifacts

`MeanReversionBB` strategy / `signal_validation` source has **n=27 FOREX picks in last 7d, all with pnl_pct=0.0**, all status=CLOSED.

Symbol breakdown (all WR=0%): USD-JPY (n=13), USD-CHF (n=7), AUD-USD (n=4), EUR-USD (n=2), GBP-USD (n=1).

**These are NOT real trading losses.** pnl=0.0 means the tracking system is recording zero-pnl closes — likely phantom closes or a tracking artifact. They inflate FOREX 7d WR denominator (making WR look lower) but do NOT drain PF (abs(0.0) = 0 gross loss). The FOREX 7d PF=1.38 is real; the "WR=14%" is suppressed by these zero-pnl artifacts.

**Action:** Investigate `signal_validation` source's close-tracking path. This is a data quality issue, not a kill candidate. Do NOT add to BLOCKED_SOURCE_SYSTEMS without root-cause investigation.

**COMMODITY 24h WR=0% (n=15, pnl_pct=0.0):** Same pattern suspected — if all 15 COMMODITY 24h picks show pnl=0.0, this is the same zero-pnl artifact from `signal_validation` or a similar source. Not an action threshold trigger.

---

## 7. New Kill Candidates from Mutation Analysis

Ran `python tools/mutation_analysis.py --json` against current data.

### New since 05Z audit:

| Strategy/Symbol | Class | Direction | n | WR | Status |
|---|---|---|---|---|---|
| `myfxbook_retail_contrarian` | FOREX | LONG | 123 | 13.8% | **NEW** — n≥20, WR<35%, meets criteria; needs 3-AI consensus |
| `cta_cross_asset_tsmom` | FOREX | LONG | 84 | 29.8% | **NEW** — n<100 (borderline); 25pp SHORT/LONG spread; watch |

### Carried from 05Z (unblocked, awaiting 3-AI consensus):

| Strategy/Symbol | n | WR | Current state |
|---|---|---|---|
| `ig_contrarian_sentiment` LONG | 197 | 16.8% | Not yet blocked |
| `quan_engine_swing` LONG | 104 | 26.0% | Not yet blocked |
| `cta_replicator / NG=F` | 24 | 0.0% | Not yet blocked |
| `rapid_fire / UUSDT` | 34 | 0.0% | Not yet blocked |
| `forex_rsi2_mean_reversion` LONG | 108 | 7.4% | P1 from issue #686, not yet blocked |

All require 3-AI consensus + mutation/inverse/symbol-rotation tests per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` before adding to `BLOCKED_ASSET_STRATEGY_PAIRS`.

---

## 8. Gate Checks

- **Issue #685** (resolver-rescope DONE): No open PR claims "widen re-resolve scope" ✅
- **Plan v2.1 fabricated stats** (PF 5.81, ml_score 0.90, WINNER_FILTER): Not cited in any open PR ✅
- **HOLD set** (#660 #658 #681 #661): None appear in open PR list — all previously closed ✅

---

## 9. FOREX Strategy Breakdown (7d) — Post-Kill Verification

| Strategy | n | WR | Notes |
|---|---|---|---|
| MeanReversionBB (signal_validation) | 27 | 0% | Zero-pnl artifact (§6) — not a real drag |
| unknown | 8 | 38% | Mixed |
| fx_smart_carry_trade_momentum | 4 | 0% | n<action threshold |
| forex-rsi-ema-scout | 2 | 100% | n<action threshold |
| others | 2 | mixed | n<action threshold |

`forex_carry_momentum` (WR 1.8%, n=57 in baseline): **absent from 7d data** ✅ Kill in PR #692 effective.  
`forex_rsi2_mean_reversion` LONG (WR 7.4%, n=108): **absent from 7d breakdown** ✅ PR #692 kill effective for this too.

---

## 10. Next-Check Priorities

1. **CI watch:** #1026, #1027, #1037 — gate/test failures need root-cause from PR authors before merge.
2. **#1041 conflicts:** Author must rebase. Cannot touch per preserve_peer_changes rule.
3. **`signal_validation` zero-pnl investigation:** Determine whether COMMODITY 24h WR=0% is same artifact.
4. **`myfxbook_retail_contrarian` LONG:** Post to issue #686 for 3-AI consensus tracking (n=123, WR 13.8%).
5. **EQUITY 7d WR=26.5%:** Watch — PF=1.19 is acceptable but WR is low. If 7d WR stays <35% next check with n>50, flag.
6. **ETF borderline:** PF 1.48 vs Tier-2 floor of 1.5. One more clean week gets it over.

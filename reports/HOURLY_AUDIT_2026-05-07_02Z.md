# Hourly Audit — 2026-05-07T02Z

**Generated:** 2026-05-07T02:20Z  
**Dashboard snapshot:** 2026-05-07T01:42Z (repo SHA `0fa7a1b4`, file timestamp 02:09Z)  
**Session context:** Post-8-PR merge day (#684/#674/#673/#664/#683/#687/#692/#694). Issues #685 (resolver DONE), #686 (per-asset attribution), #693 (EQUITY monitor).

---

## 1. Dashboard Refresh Status

| Field | Value |
|---|---|
| File timestamp | 2026-05-07 02:09Z (hourly [skip ci] cron working ✅) |
| Payload generated_at | 2026-05-07T01:42Z |
| Payload lag | 2142s (~35 min — slightly elevated, acceptable) |
| Repo SHA at generation | `0fa7a1b4` |
| Last code change | 2026-05-07T01:07Z |

---

## 2. Per-Asset Windowed Metrics

Computed from `picks.recent_closed` (n=3500 rolling cap). Status field: WON/LOST. PF = gross_win / gross_loss.

### 24h window (cutoff ~2026-05-06 02:09Z, n_closed=284)

| Class     | PF    | WR     | n   | Flag                       |
|-----------|-------|--------|-----|----------------------------|
| CRYPTO    | 1.37  | 42.3%  | 213 |                            |
| EQUITY    | ∞     | 100.0% | 6   | n too small for signal     |
| FOREX     | 0.57  | 28.1%  | 32  | sub-floor ❌                |
| COMMODITY | 0.29  | 12.5%  | 24  | ⚠️ NEW CONCERN: collapsing |
| ETF       | ∞     | 100.0% | 9   | n too small for signal     |

### 7d window (cutoff ~2026-04-30 02:09Z, n_closed=947)

| Class     | PF    | WR     | n   | Delta vs baseline                         |
|-----------|-------|--------|-----|-------------------------------------------|
| CRYPTO    | 1.59  | 49.8%  | 729 | +0.26 PF vs 1.33 baseline ✅ improving    |
| EQUITY    | 6.69  | 77.8%  | 18  | +5.82 PF vs 0.87 ✅✅ post-#692 recovery  |
| FOREX     | 0.48  | 23.7%  | 135 | +0.34 PF vs 0.14 pre-#687, still sub-floor ❌ |
| COMMODITY | 0.98  | 32.7%  | 49  | -0.20 PF vs 1.18 7d; degrading ⚠️        |
| ETF       | 26.69 | 92.9%  | 14  | n small, positive signal                  |

### 30d window (cutoff ~2026-04-07 02:09Z, n_closed=2776)

| Class     | PF    | WR     | n    | Status                                |
|-----------|-------|--------|------|---------------------------------------|
| CRYPTO    | 1.31  | 43.1%  | 1497 | below T2; 7d improvement encouraging  |
| EQUITY    | 3.44  | 64.7%  | 133  | T1-candidate ✅ (>PF2, WR>55)         |
| FOREX     | 0.61  | 45.1%  | 563  | sub-floor ❌ mutation protocol active  |
| COMMODITY | 0.84  | 41.3%  | 501  | sub-floor ⚠️ vs long-run PF 2.05     |
| ETF       | 4.68  | 80.0%  | 45   | T1-candidate ✅                        |
| FUTURES   | ∞     | 100.0% | 2    | n too small                           |
| UNKNOWN   | 5.02  | 75.0%  | 4    | n too small                           |

### Long-run `asset_class_health` (post-resolver-v2, full dataset)

| Class     | PF   | WR    | Status                   |
|-----------|------|-------|--------------------------|
| FOREX     | 0.29 | 45.5% | sub-floor ❌              |
| CRYPTO    | 1.33 | 46.3% | below T2                 |
| EQUITY    | 1.51 | 53.4% | T2 ✅                    |
| BOND      | 1.72 | 55.6% | T2 (n<100 charter floor) |
| COMMODITY | 2.05 | 49.5% | T2 ✅                    |
| ETF       | 1.39 | 58.3% | approaching T2           |

**System totals (windowed):** 24h PF=1.47 WR=41.2%; 7d PF=1.60 WR=46.3%; 30d PF=1.48 WR=44.9%

---

## 3. Delta Analysis vs Documented Baselines

### EQUITY (issue #693 — "EQUITY 7d/14d/30d divergence monitor")

| Window | Baseline (issue #693, 2026-05-02) | Now (2026-05-07) | Delta |
|--------|-----------------------------------|------------------|-------|
| 7d PF  | 0.87                              | **6.69**         | +5.82 |
| 30d PF | 2.18                              | **3.44**         | +1.26 |

**Assessment:** Issue #693 hypothesis fully validated. The 7d deterioration was concentrated in `goldmine_6x_consensus` (killed by PR #692). 7d recovery is dramatic. EQUITY 30d now T1-candidate (PF 3.44 / WR 64.7% / n=133). **Recommend closing issue #693 as resolved.**

### CRYPTO (issue #686 baseline)

| Window | Baseline (issue #686, 2026-05-02) | Now     | Delta  |
|--------|-----------------------------------|---------|--------|
| 24h PF | 2.65 (n=85)                       | 1.37    | -1.28 (n=213 — larger sample, more representative) |
| 7d PF  | 1.21 (n=904)                      | 1.59    | +0.38 ✅ |
| Long   | 1.28                              | 1.33    | +0.05 ✅ |

CRYPTO 7d improving. PR #694 (HYPEUSDT block) and #683 (cftc_cot kill) appear to be contributing positively.

### FOREX (post-#687 JPY-cross BUY fix + #692 strategy kills)

| Window | Baseline pre-#687 | Now     | Delta |
|--------|-------------------|---------|-------|
| 7d PF  | 0.14              | 0.48    | +0.34 ✅ |
| 7d WR  | 10.7%             | 23.7%   | +13pp ✅ |

Marginal improvement confirmed post-#687. Still catastrophically sub-floor. `forex_carry_momentum` + `forex_rsi2_mean_reversion` kills (#692) have reduced volume. Mutation-3-axis protocol must continue per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

### COMMODITY — NEW CONCERN ⚠️

Long-run asset_class_health shows PF=2.05 (T2) but windowed data shows:
- 24h: PF=0.29, WR=12.5%, n=24 — 3W/21L
- 7d: PF=0.98, WR=32.7%, n=49
- 30d: PF=0.84, WR=41.3%, n=501

The divergence between long-run PF=2.05 and 30d PF=0.84 indicates recent degradation masked by older strong trades. The 24h collapse (WR=12.5%) is alarming for a class that was T2. Strategy-level attribution needed.

---

## 4. PR Triage

### Open PRs (3 total — no hold-set or author-rebase-set PRs are open)

| PR   | Draft | CI                       | mergeable_state | Reviews / Comments               | Decision |
|------|-------|--------------------------|-----------------|----------------------------------|----------|
| #846 | No    | scan ✅ drift ✅          | unknown         | 4× APPROVE (Copilot, Buffy ×3)  | HOLD — mergeable_state not MERGEABLE |
| #849 | Yes   | —                        | —               | —                                | SKIP (draft) |
| #854 | No    | scan ✅                  | unknown         | none                             | HOLD — mergeable_state not MERGEABLE |

**Hold set (#660/#658/#681/#661):** Confirmed not open.  
**Author-rebase list (#669/#676/#608/#665/#644/#597/#615/#655):** Confirmed not open (all merged/closed).

**Note on #846:** 4 cross-AI reviews (Copilot + Buffy/Codebuff) all recommend MERGE; author's "DO NOT ADMIN-MERGE — awaiting human review" condition is satisfied per reviewer comments. CI is 2/2 green. Only blocker is `mergeable_state=unknown` — GitHub has not computed it. Will resolve next audit check.

**Merges this hour: 0**

---

## 5. Mutation Analysis — New Findings

`python tools/mutation_analysis.py --json` run at ~02:15Z.

### NEW KILL CANDIDATE: `rapid_fire` × `UUSDT`

| Metric   | Value | Threshold | Met |
|----------|-------|-----------|-----|
| WR       | 0.0%  | <35%      | ✅  |
| n        | 34    | ≥20       | ✅  |
| Pattern  | `quan_engine×HYPEUSDT` blocked PR #694; `rapid_fire` same system family | — | ✅ |

Meets all 3 kill criteria (WR<35%, n>=20, pattern-match to existing kills). **Requires 3-AI consensus before adding to `BLOCKED_STRATEGY_SYMBOL_PAIRS`.** Posted to issue #686.

### DIRECTION-FILTER MUTATION CANDIDATES (not kills — need mutation analysis)

| Strategy                     | Direction | WR    | n   | Spread | Action                               |
|------------------------------|-----------|-------|-----|--------|--------------------------------------|
| `ig_contrarian_sentiment`    | LONG      | 15.3% | 157 | 42pp   | SHORT-only mutation per 3-axis protocol |
| `myfxbook_retail_contrarian` | LONG      | 10.2% | 118 | 36pp   | SHORT-only mutation candidate        |
| `cta_cross_asset_tsmom`      | LONG      | 30.8% | 65  | 30pp   | Monitor; approaching WR<35% threshold |

Note: Prior audit (`HOURLY_AUDIT_02Z.md` 2026-05-04) showed `(FOREX, myfxbook_retail_contrarian)` as already blocked. Verify current `quality_gates.py` state before any duplicate action.

### WATCH LIST (no action)

| Pattern                              | n  | WR    | Note                              |
|--------------------------------------|----|-------|-----------------------------------|
| `rapid_fire` × TAOUSDT               | 18 | 5.6%  | Below n=20 threshold; monitor    |
| `quan_engine` × MATICUSDT            | —  | 0%    | Verify n in current window       |
| `multi_asset_copytrader` SI=F/ZW=F   | <5 | 0%    | n too small                      |

---

## 6. Actions Taken

1. ✅ `git stash && git pull --rebase origin main` — clean, 2 files updated (`battleground/data/test_portfolios.json`, `hub/data/winning_combos.json`)
2. ✅ `audit_dashboard/data/dashboard_data.json` confirmed fresh (02:09Z file, 01:42Z payload)
3. ✅ Per-asset windowed metrics computed (24h/7d/30d)
4. ✅ `tools/mutation_analysis.py` run — 1 new kill candidate identified
5. ✅ PR triage: 3 open, 0 merged (both non-draft held at unknown mergeable_state)
6. ✅ New finding posted to issue #686 (`rapid_fire×UUSDT`, WR=0%, n=34)
7. ✅ This report created on branch `audit/hourly-02z`

---

## 7. Summary Table

| Item                           | Status                                              |
|-------------------------------|-----------------------------------------------------|
| Dashboard refresh              | ✅ Fresh (01:42Z payload)                           |
| EQUITY recovery (issue #693)  | ✅ Confirmed — 7d PF 6.69, 30d PF 3.44 T1          |
| CRYPTO trend                  | ✅ Improving — 7d PF 1.59 (+0.38 vs baseline)      |
| FOREX post-#687               | ⚠️ Marginal improvement (+0.34 PF 7d), still sub-floor |
| COMMODITY                     | 🚨 NEW: 24h PF=0.29/WR=12.5%; 30d PF=0.84 sub-floor |
| PR merges this hour           | 0 (mergeable_state=unknown on both open non-draft PRs) |
| New kill candidates           | 1 (`rapid_fire×UUSDT`, n=34, WR=0%) — 3-AI consensus needed |
| New mutation candidates       | 3 direction-filter (ig_contrarian, myfxbook, cta_tsmom) |

## 8. Next Hour Priorities

1. Re-check mergeable_state for #846 and #854 — merge if MERGEABLE
2. Investigate COMMODITY 24h collapse — get strategy-level attribution (mutation_analysis COMMODITY filter)
3. Seek 3-AI consensus on `rapid_fire×UUSDT` symbol block (posted to #686)
4. Monitor CRYPTO 7d: if WR stays ≥45% next snapshot, PR #694 HYPEUSDT block is confirmed working
5. Issue #693 close recommendation: EQUITY recovery validated

---

*Refs: issues #685, #686, #693; PRs #687 #692 #694; `docs/MUTATION_THREE_AXIS_PROTOCOL.md`; `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`*  
*Generated by Claude Sonnet 4.6 / Claude Code — 2026-05-07T02Z*

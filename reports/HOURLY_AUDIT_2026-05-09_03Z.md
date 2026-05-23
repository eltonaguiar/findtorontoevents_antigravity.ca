# Hourly Audit — 2026-05-09 03Z

**Dashboard generated:** 2026-05-09T02:35:49Z  
**Audit time:** 2026-05-09T03:07Z  
**Agent:** Claude Sonnet 4.6 (claude-sonnet-4-6)  
**Branch:** audit/hourly-2026-05-09-03z  
**Prior audit:** reports/HOURLY_AUDIT_2026-05-08_05Z.md (05Z)

---

## 1. Dashboard Refresh Status

Dashboard was auto-rebuilt at **2026-05-09T02:35:49Z** (hourly [skip ci] cron). Data is fresh.  
`git pull --rebase origin main` completed: 10 files changed (incubator forward signals + GHA monitor update).

---

## 2. Per-Asset Metrics — 24h / 7d / 30d

Computed from `picks.recent_closed` (n=3500 cap) against audit time 2026-05-09T03:07Z.

| Class | 24h n | 24h PF | 24h WR% | 7d n | 7d PF | 7d WR% | 30d n | 30d PF | 30d WR% | Long-run PF | Long-run n | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 244 | **4.20** | 59.8% | 844 | **1.78** | 47.6% | 1498 | **1.65** | 48.9% | 1.41 | 7895 | stable / sizing=✅ |
| EQUITY | 7 | **3.52** | 57.1% | 24 | **4.21** | 58.3% | 115 | **3.22** | 64.3% | 1.57 | 438 | stable / sizing=✅ |
| FOREX | 20 | **0.13** | 10.0% | 203 | **0.33** | 14.8% | 373 | **0.25** | 14.2% | 0.27 | 1801 | stressed / sizing=❌ |
| COMMODITY | 3 | inf | 100% | 19 | **43.93** | 94.7% | 39 | **6.07** | 76.9% | 3.97 | 393 | stable / sizing=✅ |
| ETF | 3 | inf | 100% | 13 | **25.25** | 92.3% | 45 | **6.16** | 82.2% | 1.44 | 98 | candidate / sizing=❌ |
| BOND | 0 | — | — | 0 | — | — | 0 | — | — | 0.66 | thin / sizing=❌ |

### Deltas vs documented baselines (task prompt)

| Class | Window | Baseline | Now | Delta |
|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | 4.20 | **+0.66** ✅ |
| CRYPTO | 7d PF | 1.33 | 1.78 | **+0.45** ✅ |
| CRYPTO | 30d PF | 1.33 | 1.65 | **+0.32** ✅ |
| EQUITY | 7d PF | 0.87 | 4.21 | **+3.34** ✅✅ |
| EQUITY | 30d PF | 1.41–2.18 | 3.22 | **above range** ✅ |
| FOREX | 7d PF | 0.14 (pre-#687) | 0.33 | +0.19 but catastrophic |
| FOREX | 30d PF | 0.97 (pre-#687) | 0.25 | **−0.72** ❌ |

### Deltas vs prior 05Z audit (2026-05-08T05Z)

| Class | Window | 05Z | 03Z | Delta |
|---|---|---|---|---|
| CRYPTO | 24h PF | 1.55 | 4.20 | **+2.65** ✅ strong |
| CRYPTO | 7d PF | 1.40 | 1.78 | +0.38 ✅ |
| EQUITY | 7d PF | 4.70 | 4.21 | −0.49 (still T1) |
| FOREX | 7d PF | **1.67** | **0.33** | **−1.34** 🚨 regression |
| FOREX | 7d n | 52 | 203 | +151 (unblock contamination) |

---

## 3. Asset Class Commentary

### ✅ CRYPTO — T2 stable, trending toward T1 on short windows
- 24h PF 4.20 / WR 59.8% is the strongest 24h reading in the tracked baseline series.
- 7d PF 1.78 confirms improvement from 1.33 baseline (post-#683 cftc_cot kill + #694 HYPEUSDT block).
- HYPEUSDT active picks = **0** — PR #694 symbol-block confirmed working at source.
- Long-run PF 1.41 still reflects pre-kill HYPEUSDT drag; watch 30d window for catch-up.
- CRYPTO active picks: 166. Do not destabilize.

### ✅ EQUITY — T1 confirmed, 8th consecutive positive run
- 7d PF 4.21 / WR 58.3% / 30d PF 3.22 / WR 64.3% — solidly Tier 1.
- Issue #693 hypothesis fully validated: goldmine_6x_consensus kill (PR #692) was 100% of the 7d drag. Post-kill EQUITY is the strongest asset class in the system.
- Long-run PF 1.57 / WR 53.7% / n=438 — T2 locked, T1 accumulating.
- `stocks_rsi2_pullback` 7d WR 35.7% on n=14 (issue #693 watch item): n still below 20, hold on mutation action.

### 🚨 FOREX — acute regression from TEMP UNBLOCK decisions (2026-05-08)
- 7d PF 0.33 / WR 14.8% — regression from 05Z's PF 1.67 driven by 151 additional picks closing in the 7d window.
- **Root cause:** `quality_gates.py` lines 1502/1545/1575/1576 TEMP UNBLOCKED on 2026-05-08 (re-eval: 2026-05-22):
  - `("FOREX", "forex_carry_momentum")` → 24h n=17, WR=0%, pnl=−8.50%
  - `("FOREX", "myfxbook_retail_contrarian")` + LONG direction → 7d n=118 LONG, WR=10.2%
  - `("FOREX", "ig_contrarian_sentiment", "LONG")` → 7d n=163, WR=14.7%
- **Mitigating factor:** FOREX active picks = 5 (all `non_crypto_consensus`). The bad strategies are NOT currently holding active positions. The 24h closed picks are from the brief reopening window on 2026-05-08.
- Posted to issue #686 comment #4411248532 for 3-AI consensus on re-blocking.
- Long-run PF 0.27 / n=1801 — FOREX remains the system's weakest class.

### ✅ COMMODITY — T1-candidate, 3rd consecutive strong run
- 7d PF 43.93 / WR 94.7% (n=19 thin — below charter floor of 100), but 30d PF 6.07 / WR 76.9% / n=39 is strong.
- Long-run PF 3.97 / WR 67.2% / n=393 — strongest long-run class.
- All 3 24h closes were wins. No action needed.

### ✅ ETF — candidate tier, thin but positive
- 7d PF 25.25 / WR 92.3% (n=13) and 30d PF 6.16 / n=45 — positive momentum.
- sizing_allowed=False (n=98 < 100 charter floor). Watch for n→100.

### BOND — insufficient recent data
- n=0 in all windows. Long-run n=11 / PF 0.66. No action.

---

## 4. PR Triage

### Open PRs (7 total; page 2 empty — full list):

| PR | Title | CI | Mergeable | Reviews | Decision |
|---|---|---|---|---|---|
| #867 | verify: rapid_fire pair-block GATE_REGRESSION | scan ✅ | clean | none | **MERGED** ✅ |
| #866 | feat(swarm): /swarmwithprework | scan ✅ | clean | none | **MERGED** ✅ |
| #865 | audit(05Z 2026-05-08) | scan ✅ | unknown (behind main) | none | HOLD — not clean |
| #862 | DB query bank findings | scan ✅, test(3.11) ❌ | — | none | HOLD — CI not green |
| #849 | Edge action plan + swarm harness | — | — | — | SKIP — draft |
| #846 | feat(b18): Shadow Probation panel | scan ✅ | — | — | HOLD — "DO NOT ADMIN-MERGE" in body |

**Total merges this run: 2** (#867, #866)

### Rebased PR check (#669 #676 #608 #665 #644 #597 #615 #655):
All absent from open PR list (both pages) → all previously merged or closed. No action required.

### HOLD set (#660 #658 #681 #661):
All absent from open PR list → closed. Plan v2.1 family is off the board.

---

## 5. Mutation Analysis — New Findings

Run: `python3 tools/mutation_analysis.py --json` (2026-05-09T03:07Z)

### Direction-split findings (BLOCKED_ASSET_STRATEGY_PAIRS candidates):

| Strategy | SHORT WR | LONG WR | LONG n | Spread | Action |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | 60.9% (n=46) | **14.7%** | 163 | 46pp | ⚠️ Awaiting 3-AI consensus (posted #686) |
| `myfxbook_retail_contrarian` | 46.2% (n=13) | **10.2%** | 118 | 36pp | ⚠️ Awaiting 3-AI consensus (posted #686) |
| `quan_engine_swing` | 60.0% (n=5) | 26.0% | 104 | 34pp | Already blocked (`quality_gates.py:1577`) ✅ |

### Symbol-level findings (kill candidates):

| Strategy | Symbol | n | WR | Avg PnL% | Note |
|---|---|---|---|---|---|
| `rapid_fire` | UUSDT | 34 | 0% | −0.17% | Meets kill criteria (n≥20, WR<35%) |
| `rapid_fire` | TREEUSDT | ~5 | 0% | — | n<20, watch only |
| `quan_engine` | HYPEUSDT | 553 | 41.6% | −0.22% | PR #694 blocking confirmed (0 active) |

**No auto-kills applied.** Posting to issue #686 for 3-AI consensus per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

### Previously flagged (carry-over from 05Z kill queue):
- `cta_cross_asset_tsmom` LONG: n=69, WR=29.0% (posted 05Z, comment #4403518310) — pending 3-AI sign-off

**Kill queue total: 5 strategies / symbol pairs** (all pending consensus, none auto-killed).

---

## 6. Verification Checks

| Check | Result |
|---|---|
| HYPEUSDT active picks (PR #694) | 0 ✅ |
| FOREX active picks | 5 (all `non_crypto_consensus`) ✅ |
| HOLD set (#660 #658 #681 #661) | All closed, not in open list ✅ |
| Plan v2.1 stats cited anywhere | No ✅ |
| Resolver-rescope PRs | None in open list (issue #685 DONE) ✅ |
| Peer PR rebases | None performed ✅ |
| `audit_dashboard/template.html` edits | None ✅ |
| `updates/index.html` edits | None ✅ |

---

## 7. Summary

**Goal #1 (audit performance):**
- EQUITY and COMMODITY showing T1-grade metrics on short windows. Post-kill system cleanup is working.
- CRYPTO trending positively across all windows.
- FOREX remains the problem class. TEMP UNBLOCK decisions on 2026-05-08 caused acute regression. Three strategies flagged for re-block via 3-AI consensus (#686 comment #4411248532).
- HYPEUSDT block (PR #694) verified working at source.

**Merged this run:** #867, #866  
**New findings posted:** issue #686 comment #4411248532 (4 strategies, requesting re-block consensus)  
**Action required (human/AI):** 3-AI sign-off on myfxbook LONG, ig_contrarian LONG, forex_carry_momentum re-block

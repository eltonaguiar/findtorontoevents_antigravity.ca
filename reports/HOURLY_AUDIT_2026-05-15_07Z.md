# Hourly Audit — 2026-05-15 07Z

**Generated:** 2026-05-15T07:10Z  
**Session:** claude-sonnet-4-6  
**Dashboard data freshness:** 2026-05-15T02:06:57Z (auto-refresh lag ~5h; next [skip ci] push expected ~08Z)

---

## 1. Dashboard Refresh Status

Dashboard `audit_dashboard/data/dashboard_data.json` last generated at **02:06Z** — approximately 5 hours stale. The hourly [skip ci] auto-refresh cron may have missed overnight runs or is behind. Numbers below reflect the 02:06Z snapshot; per-window metrics computed live from `picks.recent_closed` (n=3500 cap).

---

## 2. Per-Asset PF/WR — 24h / 7d / 30d

### Live windows (computed from recent_closed, cutoff from now=07:10Z)

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 122 | 54.1% | 2.26 | 853 | 43.6% | 1.31 | 2873 | 44.9% | 1.25 |
| EQUITY | 3 | 66.7% | 1.85 | 34 | 26.5% | 1.19 | 127 | 51.2% | 2.07 |
| COMMODITY | 15 | **0.0%** | 0.0 | 26 | 42.3% | 1.16 | 62 | 61.3% | 2.58 |
| FOREX | 10 | 30.0% | 1.06 | 43 | 14.0% | 1.38 | 91 | 27.5% | 1.32 |
| ETF | 2 | 100% | 999 | 14 | 64.3% | 2.19 | 52 | 75.0% | 4.05 |

### Verdict-grade (all-time, asset_class_health)

| Class | PF | WR | n | Tier Status |
|---|---|---|---|---|
| COMMODITY | 2.49 | 61.5% | 322 | ✅ Tier-2 CLEAR |
| EQUITY | 1.57 | 51.9% | 420 | ✅ Tier-2 CLEAR |
| ETF | 1.48 | 58.5% | 106 | ⚠️ borderline (PF<1.5 floor) |
| CRYPTO | 1.36 | 46.7% | 8011 | ❌ WR sub-floor (need >50%) |
| FOREX | 0.81 | 52.3% | 342 | ❌ PF sub-floor (recovering) |
| BOND | 0.66 | 54.5% | 11 | ❌ n<100 charter floor |

---

## 3. Delta vs Documented Baseline

Baseline per task brief (2026-05-02 snapshot + post-PR#687):

| Metric | Baseline | 07Z Reading | Delta | Signal |
|---|---|---|---|---|
| CRYPTO 24h PF | 3.54 | 2.26 | −1.28 | ⚠️ regression (noisy window) |
| CRYPTO 7d PF | 1.33 | 1.31 | −0.02 | ➡️ flat |
| CRYPTO 30d PF | 1.33 | 1.25 | −0.08 | ⚠️ slight drift |
| EQUITY 7d PF | 0.87 | 1.19 | **+0.32** | ✅ recovery (goldmine_6x kill) |
| EQUITY 30d PF | 1.41–2.18 | 2.07 | in range | ✅ stable |
| FOREX 7d PF | 0.14 (pre-#687) | 1.38 | **+1.24** | ✅ confirmed PR#687 fix holding |
| FOREX 30d PF | 0.97 (pre-#687) | 1.32 | **+0.35** | ✅ improved |

**Key notes:**
- COMMODITY 24h WR=0% on n=15 is the **signal_validation artifact** documented in 06Z audit — tracking entries with pnl_pct=0.0, not real losses. 7d PF=1.16, 30d PF=2.58 confirm real edge intact.
- EQUITY 7d recovery from 0.87→1.19 confirms issue #693 goldmine_6x kill (PR #692) was sufficient. Issue already closed 2026-05-13.
- CRYPTO 24h PF drop 3.54→2.26 is within normal volatility for an n=85→122 window. 7d essentially flat.
- ETF 30d PF=4.05 / WR=75% on n=52 is exceptional — approaching Tier-1 in this window. n needs to hit 100 before charter promotion.

---

## 4. PR Triage

### Merged this check
| PR | Title | CI | Reason |
|---|---|---|---|
| **#1048** | docs: hourly audit 06Z | scan=✅ | clean, no reviews |
| **#1047** | chore: loop status run 2 | scan=✅ | clean, no reviews |
| **#1051** | docs: bisect reconciliation | scan=✅ | clean, no reviews |

### HOLD set (permanent — Plan v2.1 fabrication family)
#660, #658, #681, #661 — **confirmed not in open PR list** (already closed/never merged). No action needed.

### Author-rebase set (#669 #676 #608 #665 #644 #597 #615 #655)
**Confirmed not in open PR list** — already handled in prior sessions.

### Active HoLDs
| PR | CI Status | Reason |
|---|---|---|
| #1050 | test(3.11)=FAIL | Pre-existing test debt; wait for resolution |
| #1049 | scan=✅, mergeable=unknown | Docs; hold until mergeable computes |
| #1045 | DRAFT | COT lag corrector; operator review needed |
| #1042 | no test run | Chains off dirty #1041 |
| #1041 | mergeable=dirty | Merge conflicts; HOLD per preserve_peer_changes |
| #1037 | gate=FAIL, test(3.11)=FAIL | BTC hour filter; pre-existing test debt blocks |
| #1032 | 0 CI checks | Kimi archive docs; cannot verify |
| #1030 | 0 CI checks | mercury2 P0 fix; cannot verify |
| #1029 | scan=✅ only | Toxic systems kill; feature PR needs gate+test checks |
| #1027 | gate=FAIL, test(3.11)=FAIL | CRYPTO SHORT bias; pre-existing test debt blocks |
| #1026 | gate=FAIL, test(3.11)=FAIL | Phase J banner; pre-existing test debt blocks |

**Root cause for recurring CI failures:** `audit_trail/quality_gates.py` has 36 pre-existing test failures (documented in #1049). PR #1050 fixes 32 of 36. Until #1050 merges, ALL PRs touching quality_gates paths will show test(3.11)=FAIL. Unblocking path: fix test(3.11) failure in #1050 itself (or rebase off a green main).

---

## 5. Mutation Analysis — New Findings

`python tools/mutation_analysis.py --json` run at 07:05Z. New candidates vs 06Z audit:

### NEW kill candidates (post to issue #686)

**1. `ig_contrarian_sentiment` LONG — n=197, WR=16.8%**
- Direction split: SHORT=61.4% WR (n=57) vs LONG=16.8% WR (n=197)
- 45pp spread. LONG variant is a clear drag. n≥20 ✅, WR<35% ✅
- Does NOT match existing BLOCKED_ASSET_STRATEGY_PAIRS pattern exactly → needs 3-AI consensus before kill

**2. `cta_replicator` × `NG=F` — n=24, WR=0%**
- Symbol-level block candidate: 0% WR on 24 trades, avg PnL negative
- Also: `CL=F` at 19.1% WR on n=47 — borderline (WR<35%, n≥20)
- Pattern: existing kills have targeted symbol×strategy pairs with sustained 0% WR

**3. `rapid_fire` × `UUSDT` — n=34, WR=0%**
- Also: `TAOUSDT` 5.6% WR on n=18 (below threshold, watch)
- UUSDT meets criteria: n≥20 ✅, WR<35% ✅, 0% is extreme

**Previously documented (06Z audit, already in issue #686):**
- `myfxbook_retail_contrarian` LONG: n=123, WR=13.8% — awaiting 3-AI consensus
- `cta_cross_asset_tsmom` LONG: n=84, WR=29.8% — watch (n<100 at time of flag)

### Existing kills confirmed still needed (no regression from today's PRs)
- `quan_engine` × `HYPEUSDT` — PR #694 merged. Symbol not in active picks.
- `forex_carry_momentum` + `forex_rsi2_mean_reversion` — PR #692 merged. Absent from 7d FOREX breakdown ✅.

---

## 6. Gate Checks

| Gate | Status |
|---|---|
| Issue #685 resolver-rescope: no PR claims to widen scope | ✅ confirmed |
| Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER): not cited in any open PR | ✅ confirmed |
| HOLD set (#660 #658 #681 #661): not in open PR list | ✅ confirmed |
| Author-rebase set: not in open PR list | ✅ confirmed (already closed) |

---

## 7. Watch Items for Next Check

1. **#1050 test(3.11)** — PR claims 36→4 fails. If a subsequent push makes CI green, merge immediately.
2. **#1049 mergeable** — re-check in next session; if clean + scan=green, merge.
3. **COMMODITY signal_validation artifact** — root cause: pnl_pct=0.0 entries from `signal_validation`/`MeanReversionBB` source suppress WR. Verify source is not generating live FOREX/COMMODITY picks that corrupt 24h window.
4. **ETF n→100** — currently n=106 in all-time health, n=52 in 30d. Once 30d hits n=100, ETF 30d PF=4.05 can be cited as Tier-1 evidence.
5. **CRYPTO 30d drift** — PF 1.33→1.25 is small but directionally negative. Monitor next 07 checks; if <1.20 sustained, escalate to deep-dive.
6. **#1026 / #1027 / #1037** — these are held by pre-existing test debt, not by their own code quality. Once main test suite is green (post-#1050 merge), re-check CI for these.

---

## 8. Summary

- Dashboard snapshot: 2026-05-15 02:06Z (5h stale)
- PRs merged this session: **#1048, #1047, #1051** (3 docs PRs)
- New mutation findings: 3 new kill candidates posted to issue #686
- All gate checks pass; HOLD set confirmed cleared
- EQUITY recovery from goldmine_6x kill confirmed (+0.32 PF in 7d)
- FOREX recovery from JPY-cross fix confirmed (+1.24 PF in 7d)
- Primary blocker: 36 pre-existing test failures on main block all feature PRs; PR #1050 is the fix

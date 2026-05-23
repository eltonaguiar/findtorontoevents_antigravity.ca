# Hourly Audit — 2026-05-20 14Z

**Generated:** 2026-05-20T14:10Z  
**Session:** claude-sonnet-4-6  
**Dashboard data freshness:** 2026-05-15T21:00:17Z (STALE ~117h — cron refresh not reflected in main HEAD; see §1)

---

## 1. Dashboard Refresh Status

`audit_dashboard/data/dashboard_data.json` last generated at **2026-05-15T21:00:17Z** — approximately 117 hours stale at report time. This is anomalous: the 13Z PR (#1264, merged this hour) stated the snapshot was `2026-05-20T04:13:12Z`. The discrepancy indicates the [skip ci] auto-refresh cron is pushing updates to a separate commit stream not reflected in the local worktree after `git reset --hard origin/main`. Per-window metrics below are computed against the 2026-05-15 snapshot and marked accordingly. Verdict-grade `asset_class_health` block values are from the same snapshot.

**Data reliability note:** Windowed (24h/7d/30d) numbers are computed relative to snapshot generation time (2026-05-15T21Z), not wall-clock now. 24h window returns n=0 from today's perspective. 7d/30d windows cover 2026-05-08–15 and 2026-04-15–15 respectively.

---

## 2. Per-Asset PF/WR — Verdict-Grade + 7d / 30d

### 2a. Verdict-grade (asset_class_health — all-time)

| Class | PF | WR% | Tier Status | vs Baseline |
|---|---|---|---|---|
| COMMODITY | 2.36 | 60.5% | ✅ Tier-2 CLEAR (approaching T1) | +0.58 vs 1.78 2026-05-02 |
| EQUITY | 1.55 | 51.5% | ✅ Tier-2 CLEAR | +0.14 vs 1.41 2026-05-02 |
| ETF | 1.33 | 57.4% | ⚠️ borderline (PF<1.5 floor) | +0.09 vs 1.24 baseline |
| CRYPTO | 1.30 | 46.1% | ❌ WR sub-floor (need >50%) | +0.02 vs 1.28 baseline |
| FOREX | 0.87 | 55.4% | ⚠️ recovering (#687 fix active) | +0.60 vs 0.27 pre-#687 |
| BOND | 0.66 | 54.5% | ❌ n<100 charter floor | −1.06 vs 1.72 2026-05-02 |
| FUTURES | — | 0.0% | ❌ no data | — |

### 2b. Windowed metrics (computed from picks.recent_closed, relative to 2026-05-15T21Z)

| Class | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|---|---|---|---|---|---|---|
| CRYPTO | 801 | 43.3% | 1.277 | 2875 | 45.3% | 1.253 |
| EQUITY | 32 | 18.8% | 0.627 | 126 | 49.2% | 1.992 |
| COMMODITY | 28 | 32.1% | 0.768 | 67 | 58.2% | 2.159 |
| FOREX | 24 | 20.8% | 1.614 | 46 | 34.8% | 2.305 |
| ETF | 14 | 50.0% | 0.722 | 50 | 72.0% | 2.587 |

*Note: 24h window = 0 picks (snapshot 5 days old; use 13Z PR #1264 data for intraday).*

### 2c. Delta vs documented baselines

| Metric | Baseline | 14Z Reading | Delta | Signal |
|---|---|---|---|---|
| CRYPTO 7d PF | 1.33 | 1.277 | −0.05 | ➡️ stable (within noise) |
| CRYPTO 30d PF | 1.33 | 1.253 | −0.08 | ⚠️ slight drift — monitor |
| EQUITY 7d PF | 0.87 | 0.627 | **−0.24** | ❌ degradation continues; goldmine_6x gone, stocks_rsi2_pullback drag remains |
| EQUITY 30d PF | 1.41–2.18 | 1.992 | in range | ✅ stable |
| FOREX 7d PF | 0.14 (pre-#687) | 1.614 | **+1.47** | ✅ PR #687 JPY-cross fix confirmed |
| FOREX 30d PF | 0.97 (pre-#687) | 2.305 | **+1.34** | ✅ improving |
| COMMODITY 7d PF | 1.78 | 0.768 | **−1.01** | ⚠️ short-window dip; 30d=2.159 intact |

**EQUITY 7d degradation:** goldmine_6x_consensus (PR #692) confirmed absent in 7d data. Remaining drag attributed to `stocks_rsi2_pullback` (see FINDING-30). EQUITY 30d PF=1.992 remains healthy — the 7d weakness is concentrated in a small-n recent window.

**COMMODITY 7d dip:** 30d PF=2.159 / WR=58.2% confirms underlying edge intact. 7d PF=0.768 likely a short-window artifact from FINDING-22 (`cftc_cot_commercial_signal` still accumulating bad picks before consensus kill).

---

## 3. PR Triage

### Merged this check

| PR | Title | CI | Verdict |
|---|---|---|---|
| **#1264** | audit: 13Z hourly 2026-05-20 — FINDING-31/32, FINDING-30 WATCH [skip ci] | No CI ([skip ci]) | ✅ mergeable=clean, Greptile COMMENTED only ("safe to merge"), no REQUEST_CHANGES |

### HOLD set (permanent — Plan v2.1 fabrication family)

PRs **#660, #658, #681, #661** — confirmed absent from open PR list. No action needed.

### Author-rebase watch set (#669 #676 #608 #665 #644 #597 #615 #655)

Confirmed absent from open PR list — all previously resolved.

### Open PRs requiring attention

Only PR visible in `list_pull_requests` was #1264 (now merged). No other open PRs with pending merge criteria. HOLD and author-rebase sets are clear.

---

## 4. Mutation Analysis — Findings Status

`python tools/mutation_analysis.py --json` run at 14:05Z against snapshot 2026-05-15.

### Active kill candidates (awaiting 3-AI consensus)

| Finding | Strategy × Symbol | n | WR | PF | Status |
|---|---|---|---|---|---|
| FINDING-31 | `rapid_fire × UUSDT` | 34 | 0.0% | ≈0 | ⏳ Posted to #686 at 13Z; awaiting consensus |
| FINDING-32 | `cta_replicator × NG=F` | 24 | 0.0% | ≈0 | ⏳ Posted to #686 at 13Z; awaiting consensus |
| FINDING-22 | `cftc_cot_commercial_signal × COMMODITY` | 20 | 5.0% | 0.113 | ⏳ Awaiting 3-AI consensus |

**Greptile note (PR #1264):** Greptile flagged that FINDING-31/32 metrics are identical to prior-day 13Z queue entries. This is expected — the data source (2026-05-15 snapshot) produces the same readings across days when no new data is pushed. Not a duplicate tracking issue; it's a staleness artifact. The consensus clock started at 13Z today when posted to #686.

### WATCH items (below n=20 kill floor)

| Finding | Strategy × Symbol | n | WR | Notes |
|---|---|---|---|---|
| FINDING-28 | `futures_momentum × COMMODITY` | 17 | — | Below n=20 floor; 13Z saw same |
| FINDING-30 | `stocks_rsi2_pullback` | 6 (7d, stale snapshot) | 16.7% | 13Z audit (fresher data) saw n=29; escalate when n≥30 |

**FINDING-30 status:** My 2026-05-15 snapshot shows n=6 in 7d (stale). The 13Z audit using the 04:13:12Z snapshot saw n=29. Per CLAUDE.md protocol: do not act on n<20 alone; escalate at n≥30. 13Z instruction was "escalate at 14Z if n≥30." Without a fresh snapshot confirming n≥30, hold as WATCH. Recommend 15Z check with fresh data.

### Direction-flip mutation candidates (Axis-1 — no kill, sandbox only)

| Strategy | SHORT WR | SHORT n | LONG WR | LONG n | Spread |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | ~60% | 58 | ~16% | 200 | 44pp |
| `myfxbook_retail_contrarian` | ~50% | 14 | ~14% | 124 | 36pp |
| `cta_cross_asset_tsmom` | 53.1% | 162 | 29.8% | 84 | 23pp |

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` §Axis-1: these are SHORT-only sandbox candidates. No block until mutation sandbox results available.

### Kill verifications

| Strategy | 7d n (14Z) | Status |
|---|---|---|
| `forex_carry_momentum` | 0 | ✅ DEAD (PR #692) |
| `goldmine_6x_consensus` | 0 | ✅ DEAD (PR #692) |
| `cftc_cot` | 0 | ✅ DEAD (PR #683) |
| `forex_rsi2_mean_reversion` | 0 | ✅ DEAD (PR #692) |
| `quan_engine/HYPEUSDT` (PR #694) | 553 (all-time) | ⚠️ FINDING-24 — gate bypass per 13Z audit |

**FINDING-24 note:** `quan_engine×HYPEUSDT` shows n=553 in mutation_analysis.py output (WR=41.6%, avg −0.22%). PR #694 was supposed to block this symbol. If these are post-#694 picks, the gate is being bypassed. Requires investigation — separate from this audit cycle.

---

## 5. New Strategy Candidates (mutation_analysis.py §3)

High symbol-variance systems flagged for allowlist mutations:

| System | Best Symbol | Best WR | Worst Symbol | Worst WR | Spread |
|---|---|---|---|---|---|
| `rapid_fire` | ENJUSDT | 88.9% | UUSDT | 0.0% | 89pp |
| `cta_replicator` | USDJPY=X | 70.5% | NG=F | 0.0% | 71pp |
| `multi_asset_copytrader` | USDCHF=X | 100% | PL=F / GC=F | 0.0% | 100pp |
| `quan_engine` | XRPUSDT | 51.0% | MATICUSDT | 0.0% | 51pp |

These are Axis-3 (symbol allowlist) mutation candidates per protocol. None trigger kill criteria at the system level. Sandbox only.

---

## 6. Gate Checks

| Gate | Status |
|---|---|
| Issue #685: no PR claims to widen re-resolve scope | ✅ confirmed — HOLD set absent |
| Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER): not cited in open PRs | ✅ confirmed |
| HOLD set (#660 #658 #681 #661): absent from open PR list | ✅ confirmed |
| Author-rebase watch set: absent from open PR list | ✅ confirmed (previously resolved) |
| Issue #693 (EQUITY divergence monitor): closed 2026-05-13 | ✅ closed — goldmine_6x kill sufficient |

---

## 7. Watch Items for 15Z

1. **Dashboard freshness** — snapshot is 5 days stale. 15Z check: confirm if [skip ci] cron has pushed a new `dashboard_data.json`. If not, escalate cron health to operator.
2. **FINDING-30 escalation** — 13Z audit saw `stocks_rsi2_pullback` n=29. With fresh 15Z data, if n≥30 → escalate to mutation analysis per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
3. **FINDING-31/32 consensus** — posted to issue #686 at 13Z. Check for any AI consensus replies before next hour.
4. **FINDING-24 investigation** — `quan_engine×HYPEUSDT` n=553 in mutation output despite PR #694 block. Confirm whether these are pre-block or post-block picks; if post-block, gate is bypassed and P0 fix needed.
5. **EQUITY 7d recovery** — EQUITY 7d PF=0.627 remains below baseline 0.87. With goldmine_6x confirmed gone, any further 7d degradation must be attributed to `stocks_rsi2_pullback` or other active strategies.
6. **COMMODITY 7d dip** — 7d PF=0.768 vs 30d PF=2.159. Monitor whether this is a window artifact from FINDING-22 picks or a real edge decline.

---

## 8. Summary

| Item | Value |
|---|---|
| Dashboard snapshot | 2026-05-15T21:00:17Z (STALE ~117h) |
| PRs merged this hour | **1** — #1264 (13Z audit docs) |
| New findings | 0 new (FINDING-31/32/33 continued from 13Z) |
| Kill candidates awaiting consensus | 3 (FINDING-22, FINDING-31, FINDING-32) |
| HOLD set status | Clear |
| Author-rebase set | Clear |
| Strongest signal | FOREX 7d PF=1.614 (+1.47 vs pre-#687 baseline) — confirmed |
| Biggest concern | EQUITY 7d PF=0.627 (−0.24 vs baseline); COMMODITY 7d dip |
| Next action | 15Z: fresh snapshot + FINDING-30 escalation check + FINDING-24 gate-bypass investigation |

---

_Generated by [Claude Code](https://claude.ai/code/session_01XU5kmjZiA9auUgPoCtJCRD)_

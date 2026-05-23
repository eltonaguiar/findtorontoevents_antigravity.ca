# Hourly Audit — 2026-05-13 06Z

Generated: 2026-05-13T06:00Z  
Branch: `audit/hourly-06z-2026-05-13`  
Previous audit: `reports/HOURLY_AUDIT_2026-05-13_04Z.md` (PR #950)

---

## 1. Dashboard Refresh Status

`audit_dashboard/data/dashboard_data.json` pulled from origin/main (forced update). Confirmed fresh: new commits include swarm_revalid_20260513 reports + tests/test_ns_f_btc_bear_long_reject.py + tools/backtest_equity_momentum_vix_regime.py.

---

## 2. Per-Asset Metrics

### 2a. Long-run (asset_class_health)

| Class | PF | WR | n | Status | Sizing |
|---|---|---|---|---|---|
| COMMODITY | 4.08 | 70.7% | 280 | stable | allowed |
| EQUITY | 1.58 | 52.0% | 410 | stable | allowed |
| CRYPTO | 1.38 | 46.8% | 7915 | stable | allowed |
| ETF | 1.38 | 55.8% | 104 | stable | allowed |
| FOREX | 0.63 | 41.4% | 432 | stressed | blocked |
| BOND | 0.66 | 54.5% | 11 | thin_sample | blocked |
| FUTURES | — | — | 0 | insufficient | blocked |

### 2b. Windowed (from picks.recent_closed, n=3500)

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 1.28 | 36.8% | 182 | 1.35 | 41.9% | 972 | 1.30 | 44.9% | 2804 |
| EQUITY | 0.00 | 0.0% | 5 | 3.33 | 37.1% | 35 | 2.61 | 55.1% | 127 |
| COMMODITY | inf | 100.0% | 6 | 44.07 | 94.4% | 18 | 7.88 | 80.9% | 47 |
| ETF | 0.00 | 0.0% | 7 | 2.65 | 65.0% | 20 | 3.88 | 72.2% | 54 |
| FOREX | 1.84 | 30.0% | 10 | 1.13 | 22.2% | 72 | 0.64 | 19.8% | 187 |
| BOND | — | — | 0 | — | — | 0 | — | — | 0 |
| FUTURES | — | — | 0 | — | — | 0 | — | — | 0 |

### 2c. Deltas vs Documented Baseline

| Class | Window | Baseline | Now | Delta | Driver |
|---|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | 1.28 | -2.26 | Daily noise / post-#694 settling |
| CRYPTO | 7d PF | 1.33 | 1.35 | +0.02 | Stable |
| CRYPTO | 30d PF | 1.33 | 1.30 | -0.03 | Stable |
| EQUITY | 7d PF | 0.87 | 3.33 | +2.46 | PR #692 goldmine_6x kill — confirmed |
| EQUITY | 30d PF | 1.41–2.18 | 2.61 | +0.43 | PR #692 effect propagating |
| FOREX | 7d PF | 0.14 | 1.13 | +0.99 | PR #687 JPY-cross BUY rule fix |
| FOREX | 30d PF | 0.97 pre-#687 | 0.64 | -0.33 | 30d window still dragged by pre-fix losses |

### 2d. Watches

- **CRYPTO 24h PF 1.28** — significant drop from baseline 3.54 but 7d/30d are stable (1.35/1.30). Pattern consistent with daily noise. Monitor; no action unless 7d drops below 1.0.
- **EQUITY 24h n=5, WR 0%** — trivially small sample (n=5). 7d (PF 3.33) and 30d (PF 2.61) remain healthy. No action.
- **ETF 24h n=7, WR 0%** — same, n=7 noise. 7d PF 2.65, 30d PF 3.88 intact.
- **FOREX 30d PF 0.64** — still dragged by pre-#687 losses. 7d has improved to 1.13. Normal recovery lag; watch 14d window.
- **BOND n=0 all windows** — resolver n-starvation continues. No new BOND picks resolving. Carry forward from 04Z.
- **FUTURES n=0 all windows** — new strategy PRs (#949 donchian+term, #948 forex turtle) not merged (CI red); zero production picks.

---

## 3. PR Triage

### 3a. Open PRs at 06Z

| PR | Title | gate | test(3.11) | scan | Merge? |
|---|---|---|---|---|---|
| #954 | feat(b9): adversarial shadow wiring | — | — | — | HOLD — no CI yet (created 05:36Z) |
| #951 | chore(loop): escalation docs | — | — | ✅ | HOLD — mergeable_state=unknown (base moved) |
| #950 | audit(hourly): 04Z | — | — | ✅ | HOLD — mergeable_state=unknown (base moved) |
| #949 | feat(futures): Donchian + term structure | ❌ | ❌ | ✅ | HOLD — CI red |
| #948 | feat(forex): Donchian turtle | ❌ | ❌ | ✅ | HOLD — CI red |
| #946 | feat: confluence fx/futures (Copilot) | ❌ | ❌ | ✅ | HOLD — CI red |
| #943 | feat(audit): staleness detection | — | ❌ | ✅ | HOLD — CI red |
| #942 | feat(audit): anti-overfit default-ON | — | ❌ | ✅ | HOLD — CI red |

**Merged this hour: 0**

### 3b. HOLD Set (#660 #658 #681 #661)

All closed per 04Z audit. Confirmed not in open PR list. No action.

### 3c. Author-Rebase Set (#669 #676 #608 #665 #644 #597 #615 #655)

All merged/closed per 04Z audit. Not in open PR list. No action.

### 3d. CI Failure Pattern

All feature PRs (#942 #943 #946 #948 #949) fail `gate` and/or `test(3.11)`. This is a persistent pattern. Root cause investigation is outside hourly audit scope — PRs should self-resolve or be escalated by their authors.

---

## 4. Mutation Analysis (python3 tools/mutation_analysis.py --json)

### 4a. Previously Posted (04Z audit, issue #686)

1. `ig_contrarian_sentiment` LONG: n=190, WR 16.3% — SHORT-only mutation candidate
2. `rapid_fire` × UUSDT: n=34, WR 0% — symbol-block candidate (matches HYPEUSDT/PR #694 pattern)

### 4b. NEW This Hour (posted to #686 comment at 06Z)

| Strategy | Direction | n | WR | Verdict |
|---|---|---|---|---|
| `myfxbook_retail_contrarian` | LONG | 122 | 13.1% | Kill LONG — meets all criteria |
| `cta_cross_asset_tsmom` | LONG | 75 | 26.7% | Kill LONG — SHORT 53.1% healthy |
| `quan_engine_swing` | LONG | 104 | 26.0% | Kill LONG — SHORT n=5 too thin to confirm |

All three exceed n≥20 and WR<35% thresholds. **Require 3+ AI consensus before adding to `BLOCKED_ASSET_STRATEGY_PAIRS`.** Posted to issue #686 for tracking.

Below threshold (no action):
- `rapid_fire` × ESPUSDT: n=5 (below n=20)
- `rapid_fire` × TAOUSDT: n=18 (below n=20)

---

## 5. Issue Actions

| Issue | Action | Status |
|---|---|---|
| #693 (EQUITY 7d/14d/30d divergence monitor) | **Closed as completed** — EQUITY 7d PF 3.33 >> 1.5 threshold per #692 kill. Criterion met. | Done |
| #686 (Goal-#1 quality regression) | New mutation candidates posted (comment at 06Z) | Done |
| #685 (resolver-rescope) | No new resolver PRs. Confirmed DONE. | No action |

---

## 6. Goal #1 Tier Progress

| Class | Long-run PF | WR | Tier | Δ |
|---|---|---|---|---|
| COMMODITY | 4.08 | 70.7% | **T1** (> PF 2.0, > WR 55%) | n=280, approaching stable floor |
| EQUITY | 1.58 | 52.0% | **T2** (PF > 1.5) | n=410 ✅ stable |
| ETF | 1.38 | 55.8% | Below T2 (PF < 1.5) | n=104 ✅ floor met |
| CRYPTO | 1.38 | 46.8% | Below T2 | vol-targeting path per deep_dive_crypto_mdd_reduction |
| FOREX | 0.63 | 41.4% | Sub-floor (stressed) | Mutation kills in progress; 7d recovering |
| BOND | 0.66 | 54.5% | Thin (n=11) | Needs n→100 |
| FUTURES | — | — | No data | New strategies blocked on CI red |

---

## 7. Notes for Next Session

1. **FOREX recovery**: 7d PF 1.13 is above 1.0 for first time post-#687. Monitor 14d next session.
2. **New mutation kills (#686)**: 3 new LONG-direction candidates need 3-AI consensus. Copilot/Kimi confirmation needed.
3. **CI red pattern**: PRs #942 #943 #946 #948 #949 all stuck on test(3.11) failure. Authors should diagnose.
4. **PR #954 (B9 shadow)**: No CI yet. Check next session.
5. **COMMODITY**: 7d PF 44.07 on n=18 is spectacular but sample is thin. Do not size up until n≥50.
6. **Issue #693**: Closed. EQUITY recovered fully per prediction in #693 — goldmine_6x kill was sufficient.

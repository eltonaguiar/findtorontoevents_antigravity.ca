# Hourly Audit — 2026-05-21 15Z

**Generated:** 2026-05-21T~15:15Z  
**Dashboard snapshot:** `2026-05-21T12:18:29Z` (same cron as 13Z/14Z — 15Z refresh pending)  
**Refs:** issues #685 #686 #693 | previous: `reports/HOURLY_AUDIT_2026-05-21_14Z.md`

---

## 1. Dashboard Refresh Status

Snapshot age: ~2h45m. The hourly `[skip ci]` cron writes new data; the 12Z snapshot is the latest committed. Git log confirms active scan cycles running at 15:00–15:07Z — next dashboard write expected ~15:30Z.

---

## 2. Per-Asset Metrics (15Z windows)

Computed from `audit_dashboard/data/dashboard_data.json` `picks.recent_closed` (n=3500).  
Window anchor: `2026-05-21T15:00Z`.

| Class | 24h n | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d PF | vs 14Z |
|-------|-------|--------|------|-------|-------|-------|--------|--------|
| CRYPTO | 86 | **3.039** | 905 | 48.2% | **1.406** | 2696 | 1.320 | 24h +0.131; 7d −0.007 (stable) |
| EQUITY | 7 | 1.319 | 45 | 35.6% | **0.775** | 150 | 1.422 | 7d −0.028 (worsening) |
| FOREX | 8 | 1.460 | 17 | 35.3% | **1.083** | 94 | 2.576 | stable — 15th consecutive hr ≥1.0 ✅ |
| COMMODITY | 2 | 4.016 | 40 | 10.0% | **0.236** | 77 | 1.005 | 7d −0.009 (pre-block decay, see §4) |
| ETF | — | — | 9 | 11.1% | 1.081 | 47 | 2.121 | 7d −0.241 vs 14Z (n=9 noise) |
| BOND | — | — | 4 | 0.0% | 0.000 | 4 | 0.000 | persistent, n too small to kill |
| FUTURES | — | — | — | — | — | 2 | inf | n=2, trivial |

### Deltas vs Documented Baselines

| Class | Window | Baseline | Current | Delta | Status |
|-------|--------|----------|---------|-------|--------|
| CRYPTO | 24h PF | 3.54 | 3.039 | −0.50 | Normal intraday drift |
| CRYPTO | 7d PF | 1.33 | 1.406 | +0.08 | ✅ Slight improvement |
| CRYPTO | 30d PF | 1.33 | 1.320 | −0.01 | Stable |
| EQUITY | 7d PF | 0.87 | 0.775 | −0.10 | Monitor (goldmine_6x already killed) |
| EQUITY | 30d PF | 1.41–2.18 | 1.422 | at lower bound | Holding |
| FOREX | 7d PF | 0.14 (pre-#687) | 1.083 | **+0.94** | ✅ Post-#687 sustained recovery |
| FOREX | 30d PF | 0.97 (pre-#687) | 2.576 | **+1.61** | ✅ Dramatic improvement |

---

## 3. PR Triage

### Merged this hour
- **#1291** — `audit(hourly): 14Z 2026-05-21` — CI 3/3 green, `mergeable_state=clean`, only Greptile COMMENTED (not REQUEST_CHANGES). ✅ Merged via squash.

### HOLD
| PR | Reason |
|----|--------|
| #1292 | `test (3.11)` FAILURE, `test (3.12)` cancelled — supersedes #1287, same root cause |
| #1287 | `test (3.11)` FAILURE, `test (3.12)` cancelled, `ueps-pytest` cancelled |
| #1279 | DRAFT |

### HOLD set (permanent block)
#660 #658 #681 #661 — absent from open PRs ✅

### Rebase-list PRs
#669 #676 #608 #665 #644 #597 #615 #655 — all merged/closed per 14Z report ✅

### Plan v2.1 guardrails
No open PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER. ✅

---

## 4. Key Findings

### FINDING-CONFIRMED: COMMODITY 7d crisis is pre-block legacy drain (no new action needed)

**Root cause confirmed:** both primary drains are already in `BLOCKED_SOURCE_SYSTEMS`:

| Strategy | 7d n | 7d WR | 7d PF | All-time (3500 cap) WR | All-time PF | Block status |
|----------|------|-------|-------|------------------------|-------------|-------------|
| `cftc_cot_commercial_signal` | 21 | 9.5% | 0.378 | 53.6% (n=56) | 1.653 | ✅ In BLOCKED_SOURCE_SYSTEMS (since ~2026-05-16) |
| `futures_momentum` | 17 | 11.8% | 0.087 | — | — | ✅ In BLOCKED_SOURCE_SYSTEMS + BLOCKED_ASSET_STRATEGY_PAIRS (`FUTURES`) |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | — | — | Check status |

The 7d window includes trades closed 2026-05-14 → 2026-05-21. `cftc_cot_commercial_signal` was blocked ~2026-05-16 — the 7d bad trades are from the 2-day pre-block window (May 14–16). These will roll off the 7d window by ~2026-05-23. **No additional kill action warranted.**

**Note on cftc_cot all-time:** WR=53.6%, PF=1.653 confirms this was a regime-specific failure in May, not a persistently broken strategy. The block decision is correct but reflects the recent regime.

### FINDING-50 (re-confirmed): rapid_fire × UUSDT

Per `tools/mutation_analysis.py` Section 3 (symbol variance):
- `rapid_fire`: UUSDT = **0.0% WR, n=34, avg −0.17%**
- Matches existing rapid_fire pair-kill pattern
- **NOT in recent_closed n=3500 window** (outside cap — older trades)
- Status: 1/3 AI vote (Claude). Needs Kimi + Copilot/Cursor for kill gate.
- Proposed block: `("CRYPTO", "rapid_fire", "UUSDT")` in `BLOCKED_DIRECTION_TRIPLES` or symbol-allowlist mutation

### FINDING-51 (re-confirmed): cta_replicator × NG=F + ZC=F

Per mutation analysis:
- `cta_replicator × NG=F`: **0.0% WR, n=24, avg −0.03%**
- `cta_replicator × ZC=F`: **0.0% WR, n=8** (below n≥20 threshold for kill; monitor)
- Context: `cta_replicator × USDJPY=X` = 69.6% WR — symbol-specific failure, not system failure
- Status: 1/3 AI vote (Claude). Needs Kimi + Copilot/Cursor for kill gate.
- Proposed: symbol-allowlist mutation in SANDBOX — block NG=F/ZC=F within cta_replicator

### NEW FINDING-52: multi_asset_copytrader worst symbols

Per mutation analysis Section 3:
- `multi_asset_copytrader × PL=F`: 0% WR (n not reported, need threshold check)
- `multi_asset_copytrader × GC=F`: 0% WR
- `multi_asset_copytrader × HG=F`: 0% WR
- CT=F at 54.8% WR (n=186) is the main volume driver — good
- Investigate whether PL=F/GC=F/HG=F meet n≥20 threshold before proposing block.

### EQUITY 7d — stocks_rsi2_pullback updated attribution

| Strategy | 7d n | 7d WR | 7d PF |
|----------|------|-------|-------|
| `stocks_rsi2_pullback` | 29 | 44.8% | 1.287 |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 |

`stocks_rsi2_pullback` PF improved to 1.287 vs 14Z report (issue #693 hypothesis: goldmine_6x kill restores order). WR 44.8% is still below Tier-2 threshold but trending up. **Monitor — no kill action on n<20 strategies.**

### FOREX: 15th consecutive hour ≥1.0 post-#687

7d PF 1.083 (n=17). Small sample but all 7d closes are post-#687 JPY-cross BUY rule fix. 30d PF 2.576 — strongest 30d of any class. Pattern holds: the JPY-cross fix was the correct intervention.

---

## 5. Mutation Analysis Summary

`tools/mutation_analysis.py` run at 2026-05-21T~15:10Z:

**Axis 1 (directional rescue candidates):**
- `cta_cross_asset_tsmom`: SHORT 51.1% vs LONG 29.4% (22pp spread) — consider SHORT-only mutation
- `forex_carry_momentum` / `forex_rsi2_mean_reversion`: directional spreads but both strategies already killed (PR #692)

**Axis 4 (vol-normalization candidates):**
- `rapid_fire`: 29.0% WR, n=207 — best fix is symbol-allowlist (kill UUSDT), not vol-norm
- `quan_engine`: 30.4% WR, n=5896 — PR #694 blocked HYPEUSDT; MATICUSDT next monitor candidate

**No new strategies meet auto-kill criteria** (PF<0.5, n≥20, WR<35%) at the ASSET_CLASS×STRATEGY level beyond already-identified FINDING-50/51.

---

## 6. Issue #686 Progress

Per protocol (post to issue with evidence when new strategies emerge with PF<0.5 + n≥20):

**Eligible for issue #686 update:**
- FINDING-52 (multi_asset_copytrader worst symbols) — needs n verification first

**Already posted to #686:** FINDING-50, FINDING-51 (from 14Z report)

---

## Summary

| Item | Status |
|------|--------|
| Dashboard snapshot age | ~2h45m (12:18Z); 15Z cron pending |
| PRs merged this hour | **#1291** (14Z audit) |
| PRs on HOLD | #1292 (CI fail), #1287 (CI fail), #1279 (DRAFT) |
| New kill candidates | FINDING-52 added (multi_asset_copytrader symbols, needs n check) |
| COMMODITY crisis | Pre-block legacy drain — no new action; will roll off by ~2026-05-23 |
| EQUITY 7d | Slight improvement (stocks_rsi2_pullback PF 1.287); monitor |
| FOREX | 15th consecutive hr ≥1.0 post-#687 ✅ |
| CRYPTO | Stable; 24h PF 3.039, 7d PF 1.406 |
| Plan v2.1 guardrails | Clean ✅ |

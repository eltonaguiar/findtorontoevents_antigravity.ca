# Hourly Audit — 2026-05-18 06Z

**Dashboard snapshot:** `2026-05-18T04:12:40Z` (STALE — no refresh since 05Z audit, >2h)
**Audit run:** `2026-05-18T06:15Z`
**Branch:** `audit/hourly-06z-sonnet`
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-18_05Z.md`
**Refs:** Issue #685 (resolver done), Issue #686 (live attribution), Issue #693 (EQUITY monitor — closed 2026-05-13)

---

## 1. Dashboard Refresh Status

- Dashboard last refreshed: `2026-05-18T04:12:40Z` — **STALE >2h as of audit time (06:15Z)**.
- Hourly [skip ci] auto-refresh job expected to fire at ~05:12Z and ~06:12Z; neither appears to have updated `dashboard_data.json` on origin/main since 04:12Z.
- `recent_closed` n=3500 (cap). All metrics below are from the 04:12Z snapshot — **identical to 05Z audit**.
- Flag: if 07Z audit still shows 04:12Z, escalate to operator (cron may be stalled).

**PRs merged between 05Z and 06Z cycles:**
- ✅ **PR #1231** (fix(actions): concurrency cancel-in-progress on 4 push gates — Actions cost fix) — merged 2026-05-18T05:16Z, previously held pending CI green.
- ✅ **PR #1234** (audit(hourly-05z) — 05Z audit report) — merged this cycle (06:15Z).

---

## 2. Per-Asset PF/WR by Window (unchanged from 05Z — same snapshot)

### 24h window (closed after 2026-05-17 04:12Z)

| Class     | n   | WR%  | PF    | Sum PnL% | Delta vs 05Z |
|-----------|-----|------|-------|----------|--------------|
| CRYPTO    | 188 | 48.4 | 1.201 | +28.59   | = (same snapshot) |
| FOREX     | 7   | 42.9 | 1.205 | +1.10    | = (same snapshot) |
| EQUITY    | 0   | —    | —     | —        | — |
| COMMODITY | 0   | —    | —     | —        | — |
| ETF       | 0   | —    | —     | —        | — |
| FUTURES   | 0   | —    | —     | —        | — |

### 7d window (closed after 2026-05-11 04:12Z)

| Class     | n   | WR%  | PF    | Sum PnL%  | Status |
|-----------|-----|------|-------|-----------|--------|
| CRYPTO    | 802 | 43.9 | 1.135 | +99.35    | 🟡 sub-T2; watch |
| EQUITY    | 22  | 13.6 | 0.682 | -10.28    | 🔴 P1 — stagnant (4th consecutive audit unchanged) |
| FOREX     | 14  | 35.7 | 1.584 | +3.57     | 🟢 recovery confirmed |
| COMMODITY | 17  | 17.6 | 0.445 | -23.19    | 🟡 n<20 — monitor; 30d still T2 |
| ETF       | 13  | 46.2 | 0.656 | -7.14     | 🟡 small n; watch |
| FUTURES   | 60  | 8.3  | 0.177 | -133.47   | 🔴 **P1 CATASTROPHIC** |

### 30d window (closed after 2026-04-18 04:12Z)

| Class     | n    | WR%  | PF    | Sum PnL%  | Tier / Status |
|-----------|------|------|-------|-----------|---------------|
| CRYPTO    | 2843 | 45.7 | 1.275 | +636.21   | 🟡 sub-T2 (need PF>1.5) |
| EQUITY    | 90   | 53.3 | 2.291 | +147.31   | 🟢 T1-candidate |
| FOREX     | 47   | 34.0 | 2.382 | +16.88    | 🟡 PF strong / WR<50% |
| COMMODITY | 49   | 59.2 | 2.513 | +86.33    | 🟢 T2 confirmed |
| ETF       | 40   | 67.5 | 2.055 | +32.24    | 🟢 T2 (n→100 charter floor) |
| FUTURES   | 129  | 4.7  | 0.104 | -318.39   | 🔴 **CATASTROPHIC — n=129 exceeds deep-dive floor** |

---

## 3. Key Deltas vs Documented Baselines (CLAUDE.md / issue #686)

| Metric | Baseline | Current | Delta | Note |
|--------|----------|---------|-------|------|
| CRYPTO 24h PF | 3.54 | 1.201 | -2.34 | Expected post-HYPEUSDT block (#694) |
| CRYPTO 7d PF | 1.33 | 1.135 | -0.195 | Slight degradation; watch |
| CRYPTO 30d PF | 1.33 | 1.275 | -0.055 | Stable |
| EQUITY 7d PF | 0.87 | 0.682 | -0.188 | Worse; goldmine_6x trades still in window |
| EQUITY 30d PF | 1.41–2.18 | 2.291 | +0.11 to +0.85 | Long-run improving |
| FOREX 7d PF | 0.14 (pre-#687) | 1.584 | **+1.44** | JPY-cross fix confirmed |
| FOREX 30d PF | 0.97 (pre-#687) | 2.382 | **+1.41** | Structural improvement |
| FUTURES 30d PF | (new track) | 0.104 | — | P1 catastrophic |

---

## 4. PR Triage (06Z)

### Open PRs
From GitHub: **0 open PRs** after merging #1234 and #1231.

### PRs merged this cycle
| PR | Title | Merge time |
|----|-------|-----------|
| #1234 | audit(hourly-05z): 2026-05-18 per-asset PF/WR + P1 FUTURES | 06:15Z (this cycle) |
| #1231 | fix(actions): concurrency cancel-in-progress on 4 push gates | 05:16Z (between cycles) |

### Hold set status
- **#660**: already merged 2026-05-03 (before hold constraint written) — flagged for operator review.
- **#658, #681, #661**: all confirmed closed without merge as of 09Z 2026-05-17. Not re-checked (no open PRs).

### Author-rebase list (#669, #676, #608, #665, #644, #597, #615, #655)
All confirmed merged or closed as of prior audits. No action.

---

## 5. Mutation Analysis (06Z 2026-05-18 — identical to 05Z, no new candidates)

`python tools/mutation_analysis.py --json` re-run at 06:15Z. Results unchanged from 05Z.

### Axis 1 — Direction Flips (all awaiting 3-AI consensus, no change)

| Strategy | Blocked direction | n | WR% | Opposite WR% | Spread |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 197 | 16.8% | SHORT 61.4% | 45pp |
| `myfxbook_retail_contrarian` | LONG | 123 | 13.8% | SHORT 50.0% | 36pp |
| `forex_rsi2_mean_reversion` | LONG | 108 | 7.4% | SHORT 34.8% | 27pp |
| `quan_engine_swing` | LONG | 104 | 26.0% | SHORT 60.0% | 34pp |
| `cta_cross_asset_tsmom` | LONG | 84 | 29.8% | SHORT 52.1% | 22pp |

All meet n≥20 / WR<35% blocking criteria. None currently blocked. Awaiting 3-AI consensus.

### Axis 3 — Symbol Blocks (unchanged, awaiting 3-AI consensus)

| System | Symbol | WR% | n | Status |
|---|---|---|---|---|
| `cta_replicator` | `NG=F` | 0.0% | 24 | Documented since 08Z 2026-05-17 |
| `rapid_fire` | `UUSDT` | 0.0% | 34 | Documented since 10Z 2026-05-17 |
| `cta_replicator` | `CL=F` | 19.1% | 47 | Sub-floor; monitor |
| `cta_replicator` | `ZC=F` | 0.0% | 8 | n<20; monitor |

**No new strategies meeting PF<0.5 + n≥20 this cycle.** Issue #686 post not required.

---

## 6. Outstanding P1 Findings (unchanged — no new dashboard data)

### P1-A: FUTURES catastrophic (PF=0.104 / WR=4.7% / n=129 / 30d sumPnL=−318%)
- Primary driver: `cta_replicator` — NG=F (WR=0%/n=24), CL=F (WR=19%/n=47), ZC=F (WR=0%/n=8).
- n=129 exceeds 100-trade deep-dive threshold per CLAUDE.md.
- **Status:** Awaiting 3-AI consensus on NG=F block; deep-dive report not yet written.
- **Next action:** spawn `reports/deep_dive_futures_20260518.md` if operator green-lights.

### P1-B: EQUITY 7d stagnant (PF=0.682 / WR=13.6% / n=22)
- 4th consecutive audit with identical reading (07Z, 08Z, 09Z, 05Z, 06Z — all 0.682/13.6%).
- goldmine_6x_consensus kills (PR #692, merged ~2026-05-10) still in 7d window.
- `stocksunify2_*` zero-pnl masking: 11/22 picks pnl=0, counted as losses; adjusted WR=27.3%.
- **Next checkpoint:** 2026-05-20 (7 days post-#692).
- **No action this hour.**

---

## 7. Dashboard Staleness Alert

Dashboard at 04:12Z has not refreshed for >2h. Expected cadence: hourly via [skip ci] commit.

Possible causes:
1. Hourly cron job stalled or skipped (check `.github/workflows/` for outcome-resolver / dashboard-refresh).
2. Force-push to main from peer session overwrote [skip ci] commits.
3. yfinance rate-limit during resolution causing worker hang.

If dashboard still shows 04:12Z at next (07Z) audit cycle, escalate to operator.

---

## 8. Summary / Action Items

| Priority | Finding | Action | Owner |
|----------|---------|--------|-------|
| 🔴 P1 NEW | Dashboard stale >2h (last refresh 04:12Z) | Monitor at 07Z; escalate if still stale | Operator |
| 🔴 P1 | FUTURES 30d PF=0.104/n=129 — catastrophic | 3-AI consensus on NG=F block; deep-dive pending | 3-AI |
| 🔴 P1 | EQUITY 7d PF=0.682 persistent | Monitor to 2026-05-20 | Monitor |
| 🟡 P2 | ig_contrarian_sentiment LONG n=197 WR=16.8% | Await 3-AI consensus | 3-AI |
| 🟡 P2 | myfxbook_retail_contrarian LONG n=123 WR=13.8% | Await 3-AI consensus | 3-AI |
| 🟡 P2 | cta_replicator/NG=F n=24 WR=0% | Await 3-AI consensus | 3-AI |
| 🟡 P2 | rapid_fire/UUSDT n=34 WR=0% | Await 3-AI consensus | 3-AI |
| 🟢 Done | FOREX recovery confirmed (7d PF=1.584) | No action | — |
| 🟢 Done | PR #1231 merged (Actions cost fix) | No action | — |
| 🟢 Done | PR #1234 merged (05Z audit) | No action | — |

---

## 9. Resolver Status (issue #685 — closed topic)

Per issue #685: resolver work is DONE. No resolver PRs opened or needed. Any PR claiming "widen re-resolve scope" → REQUEST_CHANGES with pointer to issue #685.

---

_Generated by Claude Sonnet 4.6 automated hourly audit. Branch: `audit/hourly-06z-sonnet`. Dashboard: `2026-05-18T04:12:40Z` (stale)._

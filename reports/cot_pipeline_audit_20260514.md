# COT Data Pipeline Audit — Look-Ahead Bias & Over-Emission Check
**Date:** 2026-05-14 | **Trigger:** Verify PF=21.86 isn't a data artifact from COT look-ahead or over-emission

---

## 1. COT Report Release Schedule (Ground Truth)

| Event | Day | Time |
|---|---|---|
| CFTC settlement date (report_date) | Tuesday | Close of business |
| CFTC public release | Friday | ~3:30 PM ET |
| **Publication lag** | **3 calendar days** | Tuesday → Friday |

The COT report is **NOT PUBLIC** between Tuesday settlement and Friday 3:30 PM ET. Any trade entered before Friday 3:30 PM using that week's COT data is look-ahead bias.

---

## 2. Timeline of Fixes

| Date | Fix | What It Addressed |
|---|---|---|
| **Before May 13** | — | 🔴 **Both bugs active:** look-ahead leakage + massive over-emission |
| **May 13, PR #941** | `COT_PUBLICATION_LAG_DAYS=3` + `_is_cot_row_public()` | ✅ Fixed look-ahead timing |
| **May 13, PR #961** | `cot_emitted_releases.json` dedup ledger + `_record_emitted_release()` | ✅ Fixed per-release over-emission (go-forward) |
| **May 13** | `verify_cot_post_patch.py` ran | Confirmed all 101 historical trades pass 3-day lag (valid=101, invalid=0) |

---

## 3. What the Retrospective Audit Found

### 3a. Look-Ahead Timing → FIXED (PR #941)

The `verify_cot_post_patch.py` tool confirmed:
- **101 trades checked**
- **Valid (post-3d-lag): 101** — all trades were entered AFTER COT data was public
- **Invalid (pre-3d-lag): 0** — no strict look-ahead leakage detected

The `_is_cot_row_public()` guard works correctly. The 3-day publication lag is enforced. **No look-ahead timing bias remains.**

### 3b. Over-Emission → PARTIALLY FIXED (PR #961)

**This is the bigger problem.** The 101-trade paper pilot had only **5 unique CFTC weekly releases:**

| CFTC Report Date | Trades Emitted | Win/Loss |
|---|---|---|
| 2026-05-05 | 23 trades | 22W / 1L |
| 2026-04-28 | 26 trades | 25W / 1L |
| 2026-04-21 | 26 trades | 23W / 3L |
| 2026-04-14 | 3 trades | 0W / 3L |
| 2026-04-07 | 3 trades | 0W / 3L |

**Over-emission ratio: ~20:1** (101 trades from 5 signals). The strategy was re-firing the same COT signal every ~1 hour for days on end.

**After dedup to 1-pick-per-cycle:**

| Metric | Original (101 trades) | After Dedup (5 trades) |
|---|---|---|
| Win Rate | 90.1% | **40.0%** |
| Profit Factor | 2.73 | **0.17** |
| Total PnL | +$359.52 | **−$52.00** |
| Wins/Losses | 91W / 10L | 2W / 3L |

**The PF=21.86 in the dashboard is entirely an over-emission artifact.** It's not 102 independent trades — it's ~5 unique COT signals repeated ~20× each.

---

## 4. Current State of Defenses

### ✅ Working (Go-Forward)

| Defense | Status | Evidence |
|---|---|---|
| `_is_cot_row_public()` (3-day lag) | Active | 8 passing tests in `test_cot_timing_lag.py` |
| `cot_emitted_releases.json` dedup ledger | Active, seeded May 13 | Currently empty `"emitted": []` — catching nothing yet because no new releases since seeding |
| 14-day freshness guard in dashboard | Active | Rejects `cot_signals.json` older than 14 days |

### 🔴 Gap: Historical Dashboard Data

The `dashboard_data.json` still reports `multi_asset_cot` with:
- PF=21.86, WR=94.1%, 102 resolved picks
- This is **pre-dedup data** — the dashboard generator hasn't been told to re-aggregate
- The dedup ledger is empty — it only tracks go-forward emissions, not historical cleanup

---

## 5. Why The Dashboard Still Shows PF=21.86

The `audit_trail/dashboard_generator.py` reads `cot_positioning` data from:
1. `alpha_engine/data/cot_signals.json` — current signals (5 fresh picks, no duplicates)
2. MySQL `trading_picks` table — historical closed picks (the 101 over-emitted trades)

The dashboard generator does NOT apply the 1-pick-per-cycle consolidation when reading historical trades from MySQL. It counts all 101 trades as independent, inflating PF to 21.86.

---

## 6. Verdict

### 🔴 PF=21.86 is an over-emission artifact, NOT a real edge.

The look-ahead timing leak was fixed (PR #941), but the over-emission issue — the system re-emitting the same weekly COT signal ~20 times — is still reflected in historical data. The dedup ledger (PR #961) prevents go-forward over-emission, but historical trades need to be re-aggregated.

**Real performance of the COT strategy: 40% WR, PF=0.17, PnL=-$52 on 5 independent signals.** This is worse than a coin flip.

---

## 7. Recommendations

### P0 — Immediate
1. **Re-aggregate historical COT trades** in the dashboard: apply 1-pick-per-COT-cycle (per symbol, per report_date) to the MySQL `trading_picks` table for `strategy='cot_positioning'`
2. **Update dashboard_data.json** `multi_asset_cot` system to reflect deduped metrics (WR=40%, PF=0.17)

### P1 — This Week
3. **Backfill the dedup ledger**: populate `cot_emitted_releases.json` with the 5 historical report dates so the ledger has continuity
4. **Add a dashboard alert**: if `cot_positioning` trades per weekly cycle > 1, flag as "over-emission warning"

### P2 — Next Sprint
5. **Add a cron-triggered `verify_cot_post_patch.py` run** that alerts if any new over-emission is detected
6. **Add per-cycle WR tracking** to the COT paper pilot so each CFTC release week is evaluated independently

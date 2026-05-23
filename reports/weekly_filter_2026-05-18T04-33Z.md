# Weekly Real-Money Filter — 2026-05-18T04:33Z

> **Data source:** `audit_dashboard/data/dashboard_data.json` (generated 2026-05-18T03:07:49Z, age=1.4h ✅)
> **Dashboard URL:** https://findtorontoevents.ca/audit
> **Method:** `money-maker-readyv2` protocol, 25%-fraction Kelly, DD-halt guard

---

## System-Wide Health (pre-filter)

| Asset Class | n | WR% | PF | Verdict | Filter Status |
|-------------|---|-----|-----|---------|---------------|
| CRYPTO | 2028 | 45.2% | 1.26 | stable | FILTERED (see below) |
| COMMODITY | 47 | 61.7% | 2.30 | thin_sample | SKIP (n<50) |
| EQUITY | 31 | 35.5% | 0.72 | thin_sample | SKIP (n<50) |
| ETF | 0 | — | — | insufficient_data | SKIP |
| FOREX | 289 | 13.1% | 66.85* | stressed | SKIP (data artifact*) |
| BOND | 0 | — | — | insufficient_data | SKIP |
| FUTURES | 12 | 16.7% | 0.96 | thin_sample | SKIP (n<12) |

*FOREX PF=66.85 is a data artifact (impossible given WR=13.1%); dashboard aggregation bug. Do not trade.

**No asset class meets full MONEY_READY criteria (PF≥1.6, WR≥50%, n≥100).** These filters identify the BEST sub-populations within the available data.

---

## CRYPTO Top Picks Filter (ONLY recommended filter this week)

**Only 2 source systems within CRYPTO meet T1/T2 thresholds:**

### Filter 1: signal_validation picks

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Source system | `signal_validation` | — | — |
| n (resolved) | 75 | ≥50 | ✅ |
| Win Rate | 57% | ≥50% | ✅ |
| Profit Factor | 4.35 | ≥2.0 (T1) | ✅ T1 |
| Not blocked | True | — | ✅ |

**Kelly Sizing:** 25%-fraction Kelly = **11.0% of account** per pick
→ At $10k account: **$1,097 per pick**
→ Max positions simultaneously: floor(100% / 11%) = **9 picks**

### Filter 2: mega_mutation picks

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Source system | `mega_mutation` | — | — |
| n (resolved) | 100 | ≥50 | ✅ |
| Win Rate | 58% | ≥50% | ✅ |
| Profit Factor | 2.31 | ≥2.0 (T1) | ✅ T1 |
| Not blocked | True | — | ✅ |

**Kelly Sizing:** 25%-fraction Kelly = **8.2% of account** per pick
→ At $10k account: **$822 per pick**
→ Max positions simultaneously: floor(100% / 8.2%) = **12 picks**

### Filter 3: baby_strats_forward (benchmark, below T1)

| Criterion | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| Source system | `baby_strats_forward` | — | — |
| n (resolved) | 1606 | ≥100 | ✅ |
| Win Rate | 51% | ≥50% | ✅ |
| Profit Factor | 1.47 | ≥1.5 (T2) | ⚠️ Near-T2 |

**Kelly Sizing:** 4.1% of account per pick = $408 at $10k
> Note: PF=1.47 is just below T2 floor (1.50). Use paper trading sizing only until PF confirmed ≥1.5 on next data refresh.

---

## How to Apply (findtorontoevents.ca/audit)

1. Open [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit)
2. Click **#f-asset** → select **CRYPTO**
3. Click **#f-source** → select `signal_validation` (for Filter 1) OR `mega_mutation` (for Filter 2)
4. Sort by `elite_score` descending
5. Top picks with `status=OPEN` and `direction=LONG` are eligible

**Additional screen:** Verify pick also has:
- `wf_verdict = PASS` (walk-forward validated)
- `confidence ≥ 0.65`
- Not in `COMMODITY_BLACKLIST` (CRYPTO picks not affected by this)

---

## Risk Controls

| Control | Setting | Notes |
|---------|---------|-------|
| Max per-pick (signal_validation) | 11.0% of account | 25%-fraction Kelly |
| Max per-pick (mega_mutation) | 8.2% of account | 25%-fraction Kelly |
| Max per-pick (baby_strats_forward) | 4.1% of account | paper only until T2 confirmed |
| Daily soft-stop | -2% total PnL | pause all new entries |
| Rolling 30d drawdown halt | >30% | pause all sizing |
| Correlation regime scalar | 0.555 (ELEVATED) | reduce Kelly by 44.5% when ELEVATED |

**ELEVATED correlation regime adjustment:**
- signal_validation: 11.0% × 0.555 = **6.1% of account**
- mega_mutation: 8.2% × 0.555 = **4.6% of account**

---

## Classes NOT Ready This Week

| Class | Reason | When to Re-Check |
|-------|--------|-----------------|
| COMMODITY | n=47 < 50 threshold | When n≥50 (est. 2026-06-01) |
| EQUITY | n=31 < 50 + PF=0.72 (negative edge) | After MySQL ghost-row purge + n≥50 |
| ETF | n=0 in dashboard (data sync issue) | After dashboard refresh with ETF resolved picks |
| FOREX | Hard-disabled per MUTATION_THREE_AXIS_PROTOCOL | Re-evaluate at n≥100 per mutation axis |
| BOND | n=0 | When scanner accumulates n≥20 |
| FUTURES | n=12 + PF=0.96 (no edge) | When n≥30 with PF≥1.5 |

---

## Known Drags on CRYPTO System-Wide PF

These systems are pulling CRYPTO PF from ~1.6+ (T2) down to 1.26:

| System | n | WR% | PF | Status | Action |
|--------|---|-----|-----|--------|--------|
| super_signals | 139 | 33% | 0.65 | NOT BLOCKED | Investigation doc ready — **awaiting user approval to block** |
| aggregated_picks | 110 | 34% | 0.89 | NOT BLOCKED | Investigation needed |
| alpha_engine_fast | 233 | 43% | 0.62 | NOT BLOCKED | Multi-class — needs CRYPTO-specific analysis |

Blocking `super_signals` alone estimated to raise CRYPTO PF: 1.26 → ~1.32.
Blocking `super_signals` + `aggregated_picks` estimated: 1.26 → ~1.38.

---

## Next Data Refresh

- Dashboard regenerates every 60 minutes via CI
- Next filter review: 2026-05-25 (weekly cadence)
- COMMODITY n counter: check when n≥50 (~1 week at current pace)
- ETF dashboard sync issue: investigate `audit_dashboard/data` ETF n=0 vs reported 105 resolved

---

*Report generated: 2026-05-18T04:33:46Z by Claude Code (Session CK)*
*Protocol: money-maker-readyv2 (CLAUDE.md)*

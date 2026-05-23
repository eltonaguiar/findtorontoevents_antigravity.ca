# Session AI v2 — Swarm Review Request
# Date: 2026-05-17
# Previous verdict: NEEDS_DISCUSSION (2 HIGH concerns)
# This review: addresses those concerns and asks for re-verdict

## Context

Session AI built on Session AH (FOREX session gate M-078 fail-closed, VIX 4H archived, CT=F COT verified).

AI session deliverables:
1. `tools/verify_realized_30d.py` — new tool showing 30d realized vs all-time dashboard stats, with COMMODITY bias warning
2. `reports/weekly_filter_2026-05-17T1337Z.md` — v1 weekly filter with 30d context
3. FOOLPROOF line 172 confirmed wired (ab_analysis.yml auto-commits daily)
4. FOOLPROOF line 171 marked blocked (CFTC pipeline needed for COT feature enrichment)

Session AI v2 deliverables (this session — addressing swarm NEEDS_DISCUSSION):
5. `tools/verify_realized_30d.py` updated — added **Table 2** using `asset_class_health[AC].circuit_breaker.{realized_n_30d,realized_wr_30d}` as the authoritative dashboard-filtered 30d source
6. `reports/weekly_filter_2026-05-17T1348Z.md` — v2 filter using CB-30d data with explicit discrepancy explanations

## Swarm HIGH concerns from v1 — resolution

### HIGH #1: COMMODITY all-time n=228 vs raw 30d n=352 (30d > all-time is impossible)

**Resolution:** Three data sources count different populations:
- All-time n=228: scanner-deduped since inception (COT 114 raw → ~40-50 unique per emission cycle)
- Raw 30d n=352: closed_picks.json includes ALL entries, pre-gate + scanner re-emissions BEFORE dedup
- CB-30d n=65: `circuit_breaker.realized_n_30d` — same dedup logic as all-time

The 30d raw > all-time (352 > 228) occurs because COT emits 2.85× more picks than unique signals, so a 30d raw window can show more than the all-time deduped total. This is a known COT over-emission artifact. CB-30d=65 is the correct reference.

**Verification:** `python tools/verify_realized_30d.py` now shows all three columns side-by-side with explanation.

### HIGH #2: FOREX raw 30d n=888 vs dashboard n=98

**Resolution:** Dashboard n=98 shows only POST-gate picks (LONG hard-blocked May 14 via M-130; SHORT session-gated May 17 via M-078). Raw 30d n=888 includes all historical FOREX picks: predominantly pre-gate LONG history. This mismatch is by design — the gates were the fix.

CB-30d n=33 = post-gate SHORT picks only. WR=48.5% shows it's still recovering.

**Verification:** the data_freshness section of dashboard_data.json confirms gate activation timestamps.

## New CB-30d data (authoritative 30d)

| Class | CB-30d n | CB-30d WR | Assessment |
|-------|----------|-----------|------------|
| EQUITY | 87 | 59.8% | ✅ T1-zone (WR≥55%) |
| COMMODITY | 65 | 56.9% | ✅ T1-zone (WR≥55%) |
| CRYPTO | 2,878 | 46.0% | ⚠ WR<50% (SPA filter only) |
| ETF | 48 | 70.8% | ✅ T1-zone but all-time n<100 |
| FOREX | 33 | 48.5% | ⚠ WR<50%, recovering post-gate |
| BOND | 0 | — | no 30d data |

## Questions for swarm

1. **Data integrity:** Does the CB-30d explanation for COMMODITY (3 sources, 3 populations) satisfy the HIGH concern, or is there still a genuine data quality issue?

2. **FOREX gate sufficiency:** M-078 (08-16 UTC, fail-closed) + M-130 (LONG hard block) — with CB-30d WR=48.5% at n=33, is the current gate setup appropriate, or should we add an additional WR-floor gate before sizing?

3. **CRYPTO SPA-failing strategies:** ml_enhanced strategies NOT in the SPA-passing list (ADAUSDT, DOGEUSDT, INJUSDT 15m, ALGOUSDT, APEUSDT, TRXUSDT) are still active. Blocking requires explicit user approval per CLAUDE.md. Should this be escalated to user as P1?

4. **Overall verdict:** Given the CB-30d data (EQUITY WR=59.8%, COMMODITY WR=56.9%), is Session AI v2 an APPROVE?

## Files to review
- `tools/verify_realized_30d.py` (lines 51-130 — main() with both tables)
- `reports/weekly_filter_2026-05-17T1348Z.md` (v2 filter)
- `audit_dashboard/data/dashboard_data.json` → `performance.asset_class_health.COMMODITY.circuit_breaker`

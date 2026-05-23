# Hourly Audit Report — 2026-05-19 11Z

**Generated:** 2026-05-19T11:xx UTC  
**Dashboard snapshot:** 2026-05-19T10:19:04Z (FRESH — 10Z cron propagated)  
**recent_closed n:** 3,500  
**Session context:** Post-merge day (8 PRs merged: #684 #674 #673 #664 #683 #687 #692 #694)

---

## §1 Dashboard Refresh Status

- Snapshot freshness: **FRESH** — 10:19Z snapshot, ~50 min old at report time
- Prior snapshot at 10Z audit was 09:17Z; this is ~1h newer with 10Z cron data
- FOREX n increase (7d: 3→19) reflects cron resolving additional closes, not new pick volume

---

## §2 Per-Asset Metrics (24h / 7d / 30d)

| Class     | 24h n | 24h WR  | 24h PF | 7d n  | 7d WR  | 7d PF | 30d n | 30d WR  | 30d PF |
|-----------|-------|---------|--------|-------|--------|-------|-------|---------|--------|
| CRYPTO    | 279   | 59.1%   | 2.541  | 1044  | 45.1%  | 1.161 | 2896  | 46.6%   | 1.322  |
| EQUITY    | 5     | 0.0%    | 0.000  | 15    | 13.3%  | 0.238 | 95    | 50.5%   | 1.939  |
| FOREX     | 7     | 42.9%   | 1.279  | 19    | 31.6%  | 1.273 | 93    | 48.4%   | 2.514  |
| COMMODITY | 4     | 0.0%    | 0.000  | 23    | 13.0%  | 0.193 | 57    | 54.4%   | 1.747  |
| ETF       | 9     | 11.1%   | 1.887  | 20    | 25.0%  | 0.989 | 49    | 57.1%   | 2.005  |
| FUTURES   | —     | —       | —      | —     | —      | —     | 2     | 100.0%  | 999.0  |
| BOND      | —     | —       | —      | —     | —      | —     | 1     | 0.0%    | 0.000  |

### Baselines (from task brief / issue #686)

| Class  | Baseline 24h PF | Baseline 7d PF | Baseline 30d PF | Source |
|--------|-----------------|----------------|-----------------|--------|
| CRYPTO | 3.54            | 1.33           | 1.33            | issue #686 |
| EQUITY | —               | 0.87           | 1.41–2.18       | issue #693 |
| FOREX  | —               | 0.14           | 0.97            | pre-#687 |

### Deltas vs 10Z (PR #1250 body) and 08Z (PR #1246 body)

| Class     | Metric  | 08Z    | 10Z    | 11Z    | Delta (10Z→11Z) |
|-----------|---------|--------|--------|--------|-----------------|
| CRYPTO    | 24h PF  | 1.460  | 0.853  | 2.541  | **+1.688 ↑↑**   |
| CRYPTO    | 7d PF   | 1.050  | 0.982  | 1.161  | **+0.179 ↑**    |
| CRYPTO    | 30d PF  | 1.272  | —      | 1.322  | +0.050 ↑        |
| EQUITY    | 7d PF   | 0.238  | 0.273  | 0.238  | −0.035 (noise)  |
| FOREX     | 7d PF   | 1.295  | n=3    | 1.273  | stable          |
| COMMODITY | 7d PF   | 0.193  | —      | 0.193  | flat            |
| ETF       | 7d PF   | 0.989  | 0.302  | 0.989  | **+0.687 ↑↑**   |

---

## §3 Key Findings

### FINDING-12 STATUS: RESOLVING ✅
**CRYPTO 7d PF recovered from 0.982 (10Z) → 1.161 (11Z).**  
This was the first sub-1.0 reading in the monitoring period. The 24h surge (PF 2.541 / WR 59.1% / n=279) is pulling the 7d window back above 1.0. The recovery is consistent with the CRYPTO 24h pattern being structurally positive (PRs #683 cftc_cot kill + #694 HYPEUSDT symbol-block reducing drag). Continue 48h monitoring per protocol.

### FINDING-14 NEW: CRYPTO 24h SPIKE — regime or structural?
CRYPTO 24h PF jumped from 0.853 (10Z) → 2.541 (11Z) — a +1.688 intraday swing on n=279.  
Two hypotheses:
1. **Regime tailwind** (crypto market direction favorable this session)
2. **Structural improvement** from PR #694 (HYPEUSDT block) reducing high-volume drag

Per issue #686 guidance: "Do not destabilize." Monitor 72h to distinguish. Do not size up or alter strategy mix on the basis of a single 24h window spike.

### ETF 7d recovery (+0.687 to 0.989)
ETF 7d went from 0.302 (n=16 at 10Z) to 0.989 (n=20 at 11Z). Four additional ETF closes resolved in the new snapshot, all profitable. FINDING-13 provisional (ETF sub-floor) is now **retracted** — PF 0.989 is effectively at-floor with n=20 below the 50-candidate minimum. Continue monitor.

### EQUITY 7d continues sub-floor (n=15, PF 0.238)
Stable (not worsening). Per issue #693 protocol: goldmine_6x_consensus killed in PR #692 — allow 48h for the 7d window to clear those losing picks. EQUITY 30d remains solid at PF 1.939 / WR 50.5% / n=95.

### FOREX post-kill dormancy confirmed (7d n=19, PF 1.273)
Post-PR #687+#692. 7d PF 1.273 on n=19 — still below confidence floor but positive signal. The n=3 at 10Z was a snapshot artifact; current 7d window resolves to n=19. 30d PF 2.514 on n=93 supports recovery hypothesis.

### COMMODITY 7d bleed continuing (PF 0.193, n=23)
Unchanged. `cftc_cot_commercial_signal` legacy closes aging out of 7d window within ~5 days. No action.

---

## §4 PR Triage

| PR    | Title                                     | CI       | Mergeable | Reviews          | Action          |
|-------|-------------------------------------------|----------|-----------|------------------|-----------------|
| #1250 | audit: 10Z — FINDING-12 CRYPTO 7d sub-1.0 | ✅ 3/3  | clean     | greptile COMMENT | **MERGED** ✅   |
| #1246 | audit: 08Z — FINDING-10 + ensemble        | ✅ 3/3  | clean     | greptile COMMENT | **MERGED** ✅   |
| #1247 | feat: model grill sequential + API roster  | ❌ test(3.11) FAILED | — | — | **HOLD — CI red** |

**HOLD set (#660 #658 #681 #661):** Confirmed closed/merged in prior sessions.  
**Rebase set (#669 #676 #608 #665 #644 #597 #615 #655):** Confirmed closed/merged in prior sessions.

---

## §5 Mutation Analysis Results

`python3 tools/mutation_analysis.py --json` run against origin/main (snapshot 10:19Z).

**No new full-pool PF<0.5 + n≥20 kill candidates identified.**

### Axis-1 (direction-flip) candidates — awaiting 3-AI consensus

| Strategy                   | Direction | n   | WR    | Status                    |
|----------------------------|-----------|-----|-------|---------------------------|
| `ig_contrarian_sentiment`  | LONG      | 197 | 16.8% | Awaiting 3-AI (4th hour)  |
| `myfxbook_retail_contrarian` | LONG    | 123 | 13.8% | Awaiting 3-AI             |
| `quan_engine_swing`        | LONG      | 104 | 26.0% | Awaiting 3-AI             |
| `forex_rsi2_mean_reversion`| LONG      | 108 | 7.4%  | Awaiting 3-AI             |
| `cta_cross_asset_tsmom`    | LONG      | 84  | 29.8% | Monitor (borderline)      |

### Axis-3 (symbol-block) candidates — awaiting 3-AI consensus

| Strategy          | Symbol  | n  | WR   | Status                  |
|-------------------|---------|----|------|-------------------------|
| `rapid_fire`      | UUSDT   | 34 | 0.0% | Awaiting 3-AI (4th hour)|
| `cta_replicator`  | NG=F    | 24 | 0.0% | Awaiting 3-AI           |

### Axis-4 (vol-normalization) candidates — no kill, engineering track

`multi_asset_copytrader` (WR 21.8%, n=1057), `quan_engine` (WR 30.4%, n=5896), `rapid_fire` (WR 29.0%, n=207) — all sub-35% LONG WR, candidates for ATR-based threshold re-expression. Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md §Step1b`. Not kill candidates; require vol-normalization engineering.

---

## §6 Constraints / Reference Checks

- **Issue #685 (resolver-rescope):** DONE — no action. Auto-reject any PR claiming "widen re-resolve scope."
- **Plan v2.1 refuted (PF 5.81, ml_score 0.90, WINNER_FILTER):** Post REQUEST_CHANGES on any PR citing these stats.
- **HOLD set #660 #658 #681 #661:** Never merge — Plan v2.1 fabricated-stats family.
- **Issue #693 (EQUITY monitor):** Closed 2026-05-13. Protocol active: wait 48h post-#692 for 7d window to clear goldmine_6x picks.
- **`preserve_peer_changes` feedback:** Do NOT manually rebase peer PRs.

---

## §7 Summary

**Merged this hour:** #1250 (10Z audit), #1246 (08Z audit) — 2 PRs  
**Held:** #1247 (model grill, test(3.11) FAILED)  
**New findings:** FINDING-14 (CRYPTO 24h spike, monitor), FINDING-12 resolving, FINDING-13 retracted  
**New kill candidates:** 0  
**Awaiting-consensus list:** 7 items (unchanged)

**Top signals:**
- CRYPTO recovering strongly (24h PF 2.541, 7d PF above 1.0 again)
- FOREX post-kill stable (7d PF 1.273, 30d PF 2.514)
- EQUITY 30d solid (PF 1.939) despite 7d noise
- No system-wide regression; post-#687+#692+#694 kills holding

_Generated by Claude Code — 2026-05-19 11Z_

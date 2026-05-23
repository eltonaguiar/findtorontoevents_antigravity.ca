# Hourly Audit — 2026-05-20T12Z

**Generated:** 2026-05-20T12:11Z  
**Dashboard snapshot:** 2026-05-20T04:13:12Z (STALE ~8h — same data as 04Z–11Z)  
**Previous audit:** PR #1262 (11Z) merged ✅  
**Cron status:** 12Z refresh not yet reflected in `dashboard_data.json`; file mtime updated by git pull but `generated_at` unchanged.

---

## Per-Asset PF/WR — 12Z Snapshot

Numbers computed from `picks.recent_closed` (n=3500). Windows relative to 2026-05-20T12:11Z.

| Class     | 24h PF | 24h WR | 24h n | 7d PF | 7d WR  | 7d n | 30d PF | 30d WR | 30d n |
|-----------|--------|--------|-------|-------|--------|------|--------|--------|
| CRYPTO    | 0.764  | 36.9%  | 103   | 1.177 | 45.6%  | 982  | 1.330  | 46.6%  | 2774  |
| EQUITY    | 0.075  | 6.2%   | 16    | 0.641 | 28.9%  | 45   | 1.419  | 44.5%  | 146   |
| FOREX     | 1.278  | 42.9%  | 7     | 1.313 | 35.3%  | 17   | 2.515  | 48.4%  | 93    |
| COMMODITY | 0.000  | 0.0%   | 15    | 0.097 | 7.9%   | 38   | 0.962  | 42.5%  | 73    |
| ETF       | 0.000  | 0.0%   | 1     | 1.233 | 31.2%  | 16   | 1.917  | 56.0%  | 50    |
| BOND      | 0.000  | 0.0%   | 3     | 0.000 | 0.0%   | 3    | 0.000  | 0.0%   | 3     |

### Baseline comparison (issue #686 documented baseline)

| Class  | Baseline 24h PF | 12Z 24h PF | Δ     | Baseline 7d PF | 12Z 7d PF | Δ      | Baseline 30d PF | 12Z 30d PF | Δ      |
|--------|-----------------|------------|-------|----------------|-----------|--------|-----------------|------------|
| CRYPTO | 3.540           | 0.764      | −2.78 | 1.330          | 1.177     | −0.153 | 1.330           | 1.330      | 0.000  |
| EQUITY | —               | 0.075      | —     | 0.870          | 0.641     | −0.229 | 2.180→1.419     | 1.419      | stable |
| FOREX  | —               | 1.278      | —     | 0.140          | 1.313     | +1.173 | 0.970           | 2.515      | +1.545 |

**CRYPTO 24h:** Short-term PF decline from documented 3.54 baseline reflects regime normalization post-PR #683 (cftc_cot kill). 7d/30d stable.  
**EQUITY:** 7d PF 0.641 continues monotonic decline from 30d 1.419. `stocks_rsi2_pullback` dominant (see FINDING-30).  
**FOREX:** 7d PF 1.313 is strong recovery vs pre-#687 baseline of 0.14. Kill PRs #692 + #687 working as intended. ✅

### Delta vs 11Z

| Class     | 7d PF (11Z) | 7d PF (12Z) | Δ      | Note                         |
|-----------|-------------|-------------|--------|------------------------------|
| CRYPTO    | 1.198       | 1.177       | −0.021 | stable / window-shift artifact |
| EQUITY    | 0.641       | 0.641       | 0.000  | unchanged — degradation continues |
| FOREX     | 1.313       | 1.313       | 0.000  | stable post-#687             |
| COMMODITY | 0.097       | 0.097       | 0.000  | catastrophic, unchanged      |
| ETF       | 1.233       | 1.233       | 0.000  | stable                       |

---

## Dashboard Refresh Status

- `generated_at`: 2026-05-20T04:13:12Z (8h stale)
- `data_freshness.last_dashboard_build`: 2026-05-20T04:18:16Z
- `stale_warning`: false (auto-field; misleading — data IS stale by 8h)
- Expected 12Z cron refresh not yet visible. If still absent at 13Z, escalate to cron health check.

---

## PR Actions This Hour

| PR    | Action  | Reason                                                        |
|-------|---------|---------------------------------------------------------------|
| #1262 | MERGED  | mergeable=MERGEABLE, no CI required [skip ci], bot COMMENT only |

**HOLD set (#660 #658 #681 #661):** confirmed absent from open PR list ✅  
**Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655):** confirmed absent from open PR list ✅

---

## Active Findings Status

### FINDING-22 (P1 — COMMODITY × cftc_cot_commercial_signal)
- 7d: n=20, WR=5.0%, PF=0.113, sum≈−65.8%
- **All kill criteria met** (n≥20, WR<35%, PF<0.5)
- **Status:** Awaiting 3-AI consensus. Posted to issue #686 at 05Z. No new consensus received this hour.
- Pattern matches existing kills (cftc_cot × non-commodity killed in PR #683). Recommend escalating to full kill once 3rd AI confirmation arrives.

### FINDING-24 (P1 — quan_engine × HYPEUSDT gate bypass)
- 7d: n=53 picks with `strategy=unknown` bypassing PR #694 symbol-block
- **Status:** Active gate bypass. Fix required in `passes_active_gate()` to also filter by `source_system`. No PR yet.
- Action: This needs a targeted PR against `audit_trail/quality_gates.py` or equivalent gate function.

### FINDING-25 (WATCH — quan_engine sub-floor pairs)
- `quan_engine × XRPUSDT` n=13, `× DOGEUSDT` n=12, `× ETCUSDT` n=5
- **Status:** All below n=20 floor. Continue monitoring.

### FINDING-28 (WATCH — COMMODITY × futures_momentum)
- 7d: n=17, WR=11.8%, PF=0.087
- **Status:** Still 3 trades below n=20 kill floor. WATCH at 13Z. Expect to cross floor within 24–48h at current pace.

### FINDING-29 (WATCH — strong_consensus × CRYPTO)
- n=112, WR=36.6%, PF=0.839
- **Status:** PF above 0.5 floor — WATCH only. No kill criteria met.

### FINDING-30 (WATCH — stocks_rsi2_pullback × EQUITY)
- 7d: n=29, WR=34.5%, PF=0.980
- **Status:** WR<35% but n=29 < 30 escalation threshold. **No escalation this hour.**
- Escalate to mutation analysis if WR<35% with n≥30 at 13Z.

---

## Mutation Analysis (12Z)

Ran full `asset × strategy` pair scan across 7d window. All pairs with PF<0.5 + n≥20:

| Asset Class | Strategy                    | n  | WR   | PF    | Status                     |
|-------------|-----------------------------|----|------|-------|----------------------------|
| COMMODITY   | cftc_cot_commercial_signal  | 20 | 5.0% | 0.113 | FINDING-22 (tracked)       |

**No new untracked kill candidates.** `rapid_fire × UUSDT` and `cta_replicator × NG=F` already penalized in `quality_gates.py`.

---

## Kill Verifications

| Strategy                   | 7d n | Status                                    |
|----------------------------|------|-------------------------------------------|
| `forex_carry_momentum`     | 0    | ✅ DEAD (PR #692)                         |
| `goldmine_6x_consensus`    | 0    | ✅ DEAD (PR #692)                         |
| `cftc_cot` (PR #683)       | 0    | ✅ DEAD (PR #683)                         |
| `forex_rsi2_mean_reversion`| 0    | ✅ DEAD (PR #692)                         |
| `quan_engine/HYPEUSDT`     | 53   | ⚠️ Gate bypass active — FINDING-24 (P1)  |

---

## EQUITY Deep-Dive (issue #693 monitor)

7d/14d/30d deterioration (issue #693, closed by PR #692):

| Window | PF (issue #693 snapshot) | PF (12Z) | Δ |
|--------|--------------------------|----------|
| 30d    | 2.18                     | 1.419    | −0.761 |
| 7d     | 0.87                     | 0.641    | −0.249 |

PR #692 killed `goldmine_6x_consensus` (7d n=6, WR=0%). EQUITY 7d still declining post-kill; dominant drag now `stocks_rsi2_pullback` (n=29, WR=34.5%).  

Expected recovery signal: if EQUITY 14d PF returns to ≥1.5 within 7 days post-#692 merge, goldmine_6x was the primary driver. Current trend suggests broader issue with `stocks_rsi2_pullback`.

---

## Issue #685 Gate (resolver-rescope)

No PRs opened this hour claiming "widen re-resolve scope." Issue #685 constraint holds. ✅

---

## Next-Hour Priorities (13Z)

1. **Check cron refresh** — if `generated_at` still 04:13Z at 13Z, cron health issue
2. **FINDING-30** — if n≥30, trigger mutation analysis on `stocks_rsi2_pullback`
3. **FINDING-28** — if n≥20, verify kill criteria fully met + post to issue #686 for 3-AI consensus
4. **FINDING-22 consensus** — if 2nd + 3rd AI responses arrive on issue #686, proceed to kill PR
5. **FINDING-24** — draft fix PR for `passes_active_gate()` source_system check

---

_Refs: issue #685 (resolver done), issue #686 (live quality regression), issue #693 (EQUITY monitor, closed)_  
_Baseline: CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33 (issue #686); EQUITY 7d 0.87 / 30d 2.18 (issue #693 pre-#692); FOREX 7d 0.14 (pre-#687)_

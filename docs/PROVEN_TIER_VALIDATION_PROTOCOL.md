# PROVEN Tier Validation Protocol (post-ca27c35a70)

**Author:** claude-proven-tier-audit (subagent of claude-sports-db-fix)
**Date:** 2026-04-04
**Scope:** Read-only audit of the PROVEN trust-tier after the battleground + super_signals demotion.
**Verdict (today):** **YES — the fix is holding.**

---

## 1. What commit `ca27c35a70` changed

Single-file edit to `cross_aggregation/system_trust_registry.py` (+24 / -10 lines).

Two systems moved from `TIER_PROVEN` to `TIER_WATCH` in the static `SYSTEM_TRUST` registry:

| System | Before (historical) | After (fresh attribution, n=1,200) | New tier |
|---|---|---|---|
| `battleground` | 63.7% WR, PF 2.48, 92 picks | 35.7% WR, PF 0.28, -3.6% PnL, 14 picks | `TIER_WATCH` |
| `super_signals` | 68.6% WR, PF 3.78, 70 picks | 50.4% WR, PF 0.77, -50.7% PnL, 119 picks | `TIER_WATCH` |

Re-promotion criteria were embedded in the `notes` field:
- **battleground:** 30-day rolling WR > 55% AND PF > 1.3
- **super_signals:** 30-day rolling PF > 1.3 AND calmar > 0

Tier-weight impact: these sources drop from **1.5x multiplier / 2.0x vote** to **1.0x / 1.0x** in `TIER_MULTIPLIERS` and `TIER_VOTE_WEIGHTS`.

---

## 2. Current PROVEN population snapshot

**Source:** `audit_dashboard/data/dashboard_data.json` (read at 2026-04-05T02:00Z)

### Active picks (n=106)
| Tier | Count |
|---|---|
| RELIABLE | 22 |
| WATCH | 84 |
| **PROVEN** | **0** |
| BANNED | 0 |

### Smart picks (n=6)
| Tier | Count |
|---|---|
| RELIABLE | 1 |
| WATCH | 5 |
| **PROVEN** | **0** |

### Recent closed (n=3,500 — historical, not live) 
| Tier | Count |
|---|---|
| RELIABLE | 1,154 |
| PROVEN | 1,111 |
| WATCH | 741 |
| BANNED | 323 |
| UNTRUSTED | 171 |

> The 1,111 PROVEN in `recent_closed` are pre-fix legacy labels on already-closed trades. New picks post-fix are no longer being tagged PROVEN. Verified: 17 active battleground picks and 53 active super_signals picks now carry `trust_tier=WATCH` (with 1 super_signals pick at RELIABLE from dynamic performance override — see §4).

### Sample active WATCH picks from demoted sources
```
battleground -> ETHUSDT   trust_tier=WATCH    label=EXCELLENT
battleground -> XRPUSDT   trust_tier=WATCH    label=MODERATE
battleground -> BTCUSDT   trust_tier=WATCH    label=MODERATE
super_signals -> SHIBUSDT trust_tier=WATCH    label=MODERATE
super_signals -> DOGEUSDT trust_tier=WATCH    label=MODERATE
super_signals -> SUIUSDT  trust_tier=RELIABLE label=MODERATE   <- dynamic override
```

### Sample active RELIABLE picks (highest tier currently live)
```
SUIUSDT  ml_enhanced_SUIUSDT_1h_A_xgboost       trust_score=6  strat_fwd_wr=55.3
STRKUSDT ml_enhanced_STRKUSDT                   trust_score=7  strat_fwd_wr=55.3
OPUSDT   ml_enhanced_OPUSDT_4h_D_ensemble_stack trust_score=7  strat_fwd_wr=55.3
AAVEUSDT ml_enhanced_AAVEUSDT                   trust_score=7  strat_fwd_wr=55.3
APTUSDT  ml_enhanced_APTUSDT                    trust_score=4  strat_fwd_wr=66.7
```

### Currently PROVEN systems in the registry (only 2 remain)
```
claude_gainer_st : fwd_wr=0.727, trades=634, PF 6.39
claws_of_doom    : fwd_wr=0.525, trades=59,  PnL +41.01%
```

---

## 3. Code paths that CAN assign `PROVEN`

### A. System-level (`trust_tier` on picks, set from `source_system`)

| File | Line | Mechanism |
|---|---|---|
| `cross_aggregation/system_trust_registry.py` | 88 | Static registry: `claude_gainer_st` hardcoded PROVEN |
| `cross_aggregation/system_trust_registry.py` | 107 | Static registry: `claws_of_doom` hardcoded PROVEN |
| `cross_aggregation/system_trust_registry.py` | 623–638 | `_compute_tier_from_stats()` dynamic promotion: **WR > 65% AND trades ≥ 30 → PROVEN** |
| `cross_aggregation/system_trust_registry.py` | 732–795 | `get_dynamic_system_tier()` — dynamic data wins; static fallback when no closed_picks |
| `cross_aggregation/system_trust_registry.py` | 759 | Static can upgrade dynamic-BANNED to UNTRUSTED (never to PROVEN) — safe |
| `cross_aggregation/aggregator.py` | 926, 1048 | Consumes `TIER_PROVEN` for consensus vote weighting (read-only downstream) |
| `audit_trail/dashboard_generator.py` | 9911 | `pick["trust_tier"] = get_tier(source_system)` — reads from registry above |

### B. Strategy-level (portfolio filter, separate from system `trust_tier`)

| File | Line | Mechanism |
|---|---|---|
| `audit_dashboard/portfolio_manager.py` | 2972–2981 | `passes_firewall()` returns `"PROVEN"` when strategy name ∈ `PROVEN_STRATEGIES` AND fwd_trades ≥ 5 AND fwd_wr ≥ 45% |
| `audit_dashboard/portfolio_manager.py` | 83 | `PROVEN_STRATEGIES` set (hardcoded list of strategy names) |
| `audit_dashboard/portfolio_manager.py` | 2981 | Returns string `"PROVEN"` into portfolio selection filter (not into pick.trust_tier field) |

### C. Client-side/JS (display-only, reads server `trust_tier`)

| File | Line | Mechanism |
|---|---|---|
| `audit_dashboard/template.html` | 5524, 5718, 5744, 5768, 7033, 7752 | `_TRUST_PROVEN_SYSTEMS` hover badge matcher — cosmetic only, no pick promotion |

### D. Legacy / non-production

| File | Line | Status |
|---|---|---|
| `battleground_quality_filter.py` | 41–44 | Strategy-level PROVEN weights — **independent from system_trust_registry**; NOT part of the demotion fix. Investigate if battleground strategies still emit picks through this path. |
| `_fix_active_picks.py` | 68 | One-off script, not in live pipeline |

---

## 4. Cross-check against the fix

**Is there any remaining path by which battleground or super_signals picks can land at trust_tier=PROVEN?**

1. **Static registry:** ✅ Both now `TIER_WATCH`. Confirmed via live import.
2. **Dynamic performance auto-compute:** ⚠️ **IF** their `closed_picks.json` ever shows WR > 65% on 30+ trades, `_compute_tier_from_stats` will auto-promote them back to PROVEN. The demotion relies on the assumption that dynamic data will keep them at ≤RELIABLE. **This is the main re-contamination vector.**
3. **Static-upgrades-dynamic:** ✅ line 759 only upgrades BANNED→UNTRUSTED, never touches PROVEN.
4. **battleground_quality_filter.py:** ⚠️ Still hardcodes 4 strategy names as tier=PROVEN (strategy-level, not system-level). Confirm with antigrav-dash-integrity whether this file is still wired into picks emission.

**One live anomaly found:** 1 active super_signals pick (SUIUSDT) is tagged `trust_tier=RELIABLE`. That is the expected dynamic-override path (its recent closed_picks WR falls in 55–65% window → RELIABLE). Not a contamination — working as designed. Logged for monitoring in §5.

---

## 5. Two-week validation protocol

### 5.1 Daily checks (automated — cron or pre-commit)

Run each morning against live `audit_dashboard/data/dashboard_data.json`:

```python
# Check 1: Active PROVEN count must stay ≤ X (baseline: 0 today)
active_proven = [p for p in data["picks"]["active"] if p.get("trust_tier") == "PROVEN"]
assert len(active_proven) <= PROVEN_ACTIVE_MAX

# Check 2: Neither demoted system can appear at PROVEN
DEMOTED = {"battleground", "super_signals"}
for p in active_proven:
    src = (p.get("source_system") or p.get("system") or "").lower()
    assert not any(d in src for d in DEMOTED), f"RE-CONTAMINATED: {p}"

# Check 3: Registry state check
from cross_aggregation.system_trust_registry import SYSTEM_TRUST
assert SYSTEM_TRUST["battleground"]["tier"] == "WATCH"
assert SYSTEM_TRUST["super_signals"]["tier"] == "WATCH"
```

### 5.2 Daily KPIs to graph

| Metric | Data source | Alarm threshold |
|---|---|---|
| Active PROVEN picks count | `picks.active` | > 20 (baseline=0, suggests auto-promotion spree) |
| Active picks from `battleground` source | grep active picks | any pick at `trust_tier=PROVEN` |
| Active picks from `super_signals` source | grep active picks | any pick at `trust_tier=PROVEN` |
| super_signals 30-day rolling PF | `alpha_engine/data/attribution_report.json` | crosses ≥ 1.3 → flag for re-promotion review |
| super_signals 30-day rolling calmar | attribution_report.json | crosses > 0 → flag for re-promotion review |
| battleground 30-day rolling WR | attribution_report.json | crosses ≥ 55% AND PF ≥ 1.3 → flag for re-promotion review |
| `claude_gainer_st` live WR (PROVEN today) | closed_picks.json | drops < 60% → preemptive demotion candidate |
| `claws_of_doom` live PF | closed_picks.json | drops < 1.5 → preemptive demotion candidate |

### 5.3 Weekly (Mon + Thu)

1. Re-run `_compute_tier_from_stats` on every system's closed_picks.json; diff against live SYSTEM_TRUST.
2. Any system where **dynamic tier ≥ PROVEN but static tier = WATCH/UNTRUSTED/BANNED** → add to investigation queue (could be a false positive or genuine recovery).
3. Any system where **static tier = PROVEN but dynamic WR < 55%** → trigger demotion review PR.

### 5.4 Re-contamination alarm triggers (broadcast to `antigrav-dash-integrity` via DM)

- **P0 (immediate):** Any active pick with `trust_tier=PROVEN` + `source_system ∈ {battleground, super_signals}`.
- **P0 (immediate):** `SYSTEM_TRUST["battleground"]["tier"]` or `SYSTEM_TRUST["super_signals"]["tier"]` changes from WATCH to PROVEN without a commit labeled `re-promote`.
- **P1 (24h):** Active PROVEN pick count increases > 5 in 24h from a steady-state of 0.
- **P1 (24h):** A new entry with `tier: TIER_PROVEN` is added to `SYSTEM_TRUST` without attribution_report.json showing 30-day WR ≥ 65% on ≥ 30 trades.
- **P2 (72h):** `battleground_quality_filter.py` strategy-level `tier: "PROVEN"` entries show negative 30-day PnL in attribution report.

### 5.5 Pass/fail criteria (end of 2-week window, ~2026-04-18)

**Fix is confirmed validated if ALL true:**
- [ ] Zero P0 alarms fired in 14 days
- [ ] ≤ 2 P1 alarms fired (and both resolved)
- [ ] battleground 14-day attribution WR still < 55% OR picks were successfully blocked from PROVEN-dependent portfolios
- [ ] super_signals 14-day attribution PF still < 1.3 OR picks were successfully blocked from PROVEN-dependent portfolios
- [ ] No ad-hoc reverts to ca27c35a70

**Fix FAILED (rollback candidate) if:**
- Any P0 alarm fires more than once
- battleground or super_signals attribution metrics rebound into re-promotion range AND picks from them appear at PROVEN in active feed

**Inconclusive (extend to 4-week window) if:**
- Attribution data insufficient: < 30 new closed picks from battleground+super_signals combined in 14 days
- A different source (e.g., kimi, aggregated_picks) shows unexpected PROVEN volume

---

## 6. Open questions for antigrav-dash-integrity

1. Is `battleground_quality_filter.py` still wired into pick emission? Its 4 strategies are still tier=PROVEN (strategy-level). If yes, should those be demoted in parallel?
2. Does `alpha_engine/data/attribution_report.json` get refreshed on every dashboard build, or on a separate cadence? Daily validation relies on its freshness.
3. The 1 RELIABLE SUIUSDT pick from super_signals — is the dynamic override expected, or should super_signals be hard-capped at WATCH until attribution recovers?

---

## 7. Conclusion

**Is the ca27c35a70 fix working today? → YES.**

- Live dashboard shows 0 active PROVEN picks, 0 smart-picks PROVEN, 0 contaminated picks from battleground/super_signals at PROVEN tier.
- Static registry correctly reflects TIER_WATCH for both demoted systems.
- Only 2 PROVEN systems remain (claude_gainer_st, claws_of_doom), both with fresh positive performance.
- One dynamic override (super_signals SUIUSDT → RELIABLE) is design-correct and not a contamination.
- Main residual risk: auto-promotion via `_compute_tier_from_stats` if attribution rebounds. Protocol above covers this.

Recommend 14-day watch window starting 2026-04-05. If all P0/P1 thresholds hold, graduate to quarterly attribution-driven tier review and mark the real-money-readiness blocker as resolved.

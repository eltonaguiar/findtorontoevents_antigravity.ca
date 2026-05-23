# Hourly Audit — 2026-05-06 04Z

**Dashboard snapshot:** 2026-05-06T02:28:37Z (stale — hourly cron not yet reflected on local pull; [skip ci] commits at 04:04Z confirmed main is active)
**Audit time:** 04:13Z
**Auditor:** Claude Sonnet 4.6

---

## 1. Dashboard Refresh Status

- Local `audit_dashboard/data/dashboard_data.json` generated_at: `2026-05-06T02:28:37Z`
- Git HEAD on main: `ef52eaa3` — "Auto-update prediction quality metrics 2026-05-06 04:05 UTC [skip ci]"
- Dashboard cron active; snapshot is ~1.75h old. Numbers below computed from the 02:28Z snapshot. Next rebuild expected ~05:00Z.
- Data source: `picks.recent_closed` (n=3500 cap) with per-class PNL threshold correction per issue #686 comment (FOREX=0.0001, COMMODITY=0.0005, others=0.001).

---

## 2. Per-Asset Windows (computed 04:13Z from 02:28Z snapshot)

### 24h Window

| Class | n | WR | PF | Sum PnL% | Status |
|---|---|---|---|---|---|
| CRYPTO | 162 | 58.0% | **1.87** | +125.6% | 🟢 T2 zone |
| EQUITY | 1 | 0.0% | 0.00 | −7.3% | n too small |
| FOREX | 3 | 66.7% | 2.79 | +0.8% | n too small |
| COMMODITY | 6 | 83.3% | 10.88 | +22.9% | n too small |
| ETF | 0 | — | — | — | — |

### 7d Window

| Class | n | WR | PF | Sum PnL% | Delta vs baseline | Status |
|---|---|---|---|---|---|---|
| CRYPTO | 735 | 53.1% | **1.61** | +320.2% | +0.28 vs 1.33 ✅ | 🟢 T2 |
| EQUITY | 18 | 55.6% | **1.54** | +19.4% | +0.67 vs 0.87 ✅ | 🟢 T2 |
| FOREX | 111 | 22.5% | **0.47** | −23.9% | +0.33 vs 0.14 ✅ | 🔴 sub-floor |
| COMMODITY | 35 | 45.7% | **1.64** | +28.6% | — | 🟡 T2-ish |
| ETF | 8 | 50.0% | **1.62** | +3.4% | — | 🟡 small n |

### 30d Window

| Class | n | WR | PF | Sum PnL% | Delta vs baseline | Tier |
|---|---|---|---|---|---|---|
| CRYPTO | 1499 | 45.3% | **1.37** | +347.1% | +0.04 vs 1.33 | 🟡 T2-candidate |
| EQUITY | 127 | 63.0% | **2.88** | +247.0% | +0.47–1.47 vs 1.41-2.18 | 🥇 **Tier-1** |
| FOREX | 561 | 41.7% | **0.63** | −19.7% | −0.34 vs 0.97 | 🔴 sub-floor |
| COMMODITY | 502 | 38.2% | **1.09** | +10.1% | — | 🟡 below T2 |
| ETF | 37 | 73.0% | **3.58** | +52.8% | — | 🥇 **Tier-1** (small n) |

### `asset_class_health` (authoritative post-resolver-v2, long-run)

| Class | PF | WR |
|---|---|---|
| CRYPTO | 1.31 | 45.9% |
| EQUITY | 1.40 | 52.6% |
| FOREX | 0.29 | 45.8% |
| COMMODITY | 2.33 | 50.1% |
| ETF | 1.20 | 53.4% |
| BOND | 1.72 | 55.6% |

---

## 3. Deltas vs Documented Baseline

| Class | Window | Baseline | 04Z | Delta | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 24h | 3.54 | 1.87 | −1.67 | Noise (24h volatile) |
| CRYPTO | 7d | 1.33 | 1.61 | **+0.28** | ✅ Improving |
| CRYPTO | 30d | 1.33 | 1.37 | +0.04 | Stable |
| EQUITY | 7d | 0.87 | 1.54 | **+0.67** | ✅ Issue #693 confirmed — goldmine_6x kill effective |
| EQUITY | 30d | 1.41–2.18 | 2.88 | **+0.70+** | ✅ Tier-1 |
| FOREX | 7d | 0.14 (pre-#687) | 0.47 | **+0.33** | ✅ PR #687+#692 working |
| FOREX | 30d | 0.97 (pre-#687) | 0.63 | −0.34 | forex_rsi2 long tail still loading |

---

## 4. PR Triage

### HOLD Set (confirmed closed — not in open PR list)
#660, #658, #681, #661 — all confirmed closed prior sessions. ✅ Not actionable.

### Rebase-Check PRs (confirmed closed)
#669, #676, #608, #665, #644, #597, #615, #655 — all confirmed closed. ✅ Not actionable.

### Open PRs Assessed

| PR | Title | mergeable_state | CI | Reviews | Action |
|---|---|---|---|---|---|
| #846 | B18 Shadow Probation panel | **CLEAN** | 2/2 ✅ (scan+drift) | None | **HOLD** — explicit "DO NOT ADMIN-MERGE" in PR body; awaits human review |
| #843 | B5 concept scorer (re-impl #764) | **DIRTY** (conflict) | 4/4 ✅ | None | BLOCKED — author needs rebase |
| #837 | auto-shadow-demote on STRATEGY_DEGRADATION | **DIRTY** (conflict) | 4/4 ✅ | 2× REQUEST_CHANGES (deepseek+xai — missing test coverage) | BLOCKED — conflict + RC |
| #835 | crypto: suppress st_fear_greed_contrarian | — | scan=CANCELLED | — | BLOCKED — rerun needed |
| #844 | ruflo/SWARM audit data quality tools | — | 0 CI checks | — | BLOCKED — no CI |
| #841 | docs/asset-class-outlier-audit | DIRTY | — | — | BLOCKED — conflict |
| #838 | hermes swarm slash commands | DIRTY | — | — | BLOCKED — conflict |
| #842 | Hourly audit 02Z (tracking) | — | — | — | Tracking PR, no action |
| #845 | Hourly audit 03Z (tracking) | — | — | — | Tracking PR, no action |

**PRs merged this hour: 0**

No PR met all three criteria (MERGEABLE + ALL CI green + no REQUEST_CHANGES).

### #846 note
mergeable_state=CLEAN, 2/2 CI green, zero REQUEST_CHANGES reviews — technically merge-eligible except the author explicitly wrote "DO NOT ADMIN-MERGE — awaiting human review." Holding per that directive.

---

## 5. Mutation Analysis (`python tools/mutation_analysis.py --json` at 04:13Z)

### No new PF<0.5 + n≥20 strategies vs 03Z session

The following candidates were already posted to issue #686 in prior sessions. No new ones emerge this hour.

| Strategy | Direction | WR% | n (mutation tool) | Prior post |
|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | LONG | 2.4% | 82 | 03Z session ✅ |
| `ig_contrarian_sentiment` | LONG | 18.4% | 125 | 04Z 2026-05-05 ✅ |
| `myfxbook_retail_contrarian` | LONG | 10.2% | 88 | 04Z 2026-05-05 ✅ |
| `quan_engine_swing` | LONG | 26.0% | 104 | 03Z session ✅ |
| `rapid_fire × UUSDT` | — | 0.0% | 34 | Multiple prior sessions ✅ |

### New directional candidate: `cta_cross_asset_tsmom`

| Direction | WR% | n (mutation tool) | PF (recent_closed) |
|---|---|---|---|
| LONG | 30.8% | 65 | 1.20 (n=16 in recent_closed cap) |
| SHORT | 64.1% | 78 | 2.47 |

**Verdict:** 33pp directional spread. PF on LONG side is **1.20** (not <0.5) per recent_closed computation; does NOT meet PF<0.5 kill threshold. The mutation tool n=65 vs recent_closed n=16 discrepancy is due to 3500-cap truncation. Watching — if next session shows PF dropping below 0.5 on full-history computation, escalate to 3-AI consensus.

---

## 6. Goal-#1 Status Update

| Class | 30d PF | Target | Gap | Priority |
|---|---|---|---|---|
| **EQUITY** | **2.88** (T1) | T1: PF>2 | ✅ Met | Protect, do not destabilize |
| **ETF** | **3.58** (T1) | T1: PF>2 | ✅ Met | Small n (37); maintain |
| **COMMODITY** | 1.09 | T2: PF>1.5 | −0.41 | Needs strategy review |
| **CRYPTO** | 1.37 | T2: PF>1.5 | −0.13 | Improving; HYPEUSDT block helping |
| **BOND** | 1.72 (health) | T2: PF>1.5 | ✅ Met | n=18, below charter floor |
| **FOREX** | 0.63 | T2: PF>1.5 | −0.87 | `forex_rsi2` LONG kill pending 3-AI |

**Issue #693 (EQUITY 7d/14d/30d monitor):** 7d PF restored to 1.54 post-PR-#692. Hypothesis confirmed. Escalation criteria NOT triggered.

---

## 7. Recommended Next Actions

1. **#846** — Awaiting human review per author request. Human should verify Shadow Probation panel renders collapsed on /audit Overview.
2. **#843** — Author rebase needed (conflict). Once rebased, 4/4 CI green → eligible for merge.
3. **#837** — Needs test file `tests/test_alert_shadow_demotion.py` (8 cases, 182 lines, spec posted in PR comments) pushed to branch. Then re-check conflict.
4. **#835** — Rerun cancelled scan check. If green, eligible.
5. **`forex_rsi2_mean_reversion` LONG** — Awaiting 2 more AI confirmations for kill. Posted to #686 in 03Z session.

---

*Generated 2026-05-06T04:13Z — Claude Sonnet 4.6*

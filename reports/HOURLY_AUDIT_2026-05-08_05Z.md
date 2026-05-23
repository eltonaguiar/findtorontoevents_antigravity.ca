# Hourly Audit — 2026-05-08 05Z

**Run time:** 2026-05-08T05:11Z  
**Dashboard snapshot:** 2026-05-08T03:59:34Z (no new rebuild since 04Z — hourly cron pending)  
**Source data:** `audit_dashboard/data/dashboard_data.json` (local, post-`git pull --rebase origin main`)  
**Recent main HEAD:** `0809be3c` — "Update QuantumFusion performance report [skip ci]" (05:07Z)

---

## 1. Per-Asset Metrics vs Documented Baseline

### 1.1 Windowed metrics (computed from `picks.recent_closed`, n=3500)

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 184 | 38.0% | 1.55 | 818 | 45.2% | 1.40 | 2606 | 45.8% | 1.27 |
| EQUITY | 4 | 50.0% | 1.39 | 18 | 66.7% | 4.70 | 130 | 65.4% | 3.25 |
| FOREX | 12 | 41.7% | 1.46 | 52 | 46.2% | 1.67 | 232 | 51.7% | 1.57 |
| COMMODITY | 3 | 100% | inf | 19 | 94.7% | 42.83 | 101 | 52.5% | 4.44 |
| ETF | 1 | 100% | inf | 13 | 92.3% | 25.47 | 43 | 79.1% | 4.54 |
| BOND | — | — | — | — | — | — | — | — | — |

*EQUITY/ETF/COMMODITY 24h and 7d n-counts are small — do not size up on these alone.*

### 1.2 Long-run asset_class_health (resolver-v2 grade, all-time)

| Class | PF | WR | Notes |
|---|---|---|---|
| CRYPTO | 1.33 | 47.0% | T2-floor approaching (PF>1.5 needed) |
| EQUITY | 1.55 | 53.6% | ✅ T2 confirmed long-run |
| COMMODITY | 4.43 | 67.3% | ✅ T1-candidate |
| FOREX | 0.25 | 46.2% | Long-run contaminated by pre-#687 data |
| ETF | 1.38 | 57.9% | Near T2-floor |
| BOND | 0.66 | 54.5% | Sub-floor, n=18 (below n=100 charter) |

### 1.3 Deltas vs task baseline

| Class | Window | Baseline | Current | Delta | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | 1.55 | −1.99 | 04Z spike was transient; still >1, no alarm |
| CRYPTO | 7d PF | 1.33 | 1.40 | +0.07 | Marginal improvement — stable |
| CRYPTO | 30d PF | 1.33 | 1.27 | −0.06 | Slight drag — within noise |
| EQUITY | 7d PF | 0.87 | 4.70 | **+3.83** | Major post-#692 goldmine_6x kill |
| EQUITY | 30d PF | 1.41–2.18 | 3.25 | **+1.07–1.84** | T1 territory confirmed |
| FOREX | 7d PF | 0.14 | 1.67 | **+1.53** | Sustained post-#687 recovery |
| FOREX | 30d PF | 0.97 | 1.57 | **+0.60** | T2-floor exceeded |

---

## 2. PR Triage

### 2.1 Open PRs as of 05:11Z (5 PRs total)

| PR | Title | CI | Reviews | Decision |
|---|---|---|---|---|
| **#863** | audit(04Z): CRYPTO alarm cleared, COMMODITY T1 | scan ✅ | None | ✅ **MERGED** (11264c9d) |
| **#864** | chore(loop): V1-V7 re-verified 04:17Z | scan ✅ | None | ✅ **MERGED** (48e054bc) |
| #862 | DB query bank: forex pnl corruption + 50 untested pairs | scan ✅ / test(3.11) ❌ | None | **HOLD** — CI not fully green |
| #849 | Edge action plan + swarm peer-review harness | — | — | **SKIP** — draft |
| #846 | feat(b18): Shadow Probation panel | scan ✅ / drift ✅ | — | **HOLD** — explicit "DO NOT ADMIN-MERGE" in body |

**Total merges this run: 2** (#863, #864)

### 2.2 Author-rebase PRs check (#669 #676 #608 #665 #644 #597 #615 #655)

All absent from `gh pr list --state open` — presumed merged or closed. No action required.

### 2.3 HOLD set (#660 #658 #681 #661)

Not in open PR list — presumed closed. No action required.

---

## 3. Mutation Analysis — New Findings

**Run:** `python3 tools/mutation_analysis.py --json` at 05:11Z

### 3.1 NEW: `cta_cross_asset_tsmom` LONG flagged

| Direction | n | WR | avg PnL |
|---|---|---|---|
| SHORT | 91 | 57.1% | +0.00% |
| **LONG** | **69** | **29.0%** | **−0.01%** |

- WR spread 28pp (SHORT dominates); LONG WR 29% < 35% threshold; n=69 ≥ 20 ✅
- Meets pattern for kill-candidate per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- **Action: post to issue #686 for 3-AI consensus. Do NOT auto-kill.**
- Posted to issue #686 comment #4403518310 this run.

### 3.2 Known kill queue (unchanged, all awaiting 3-AI consensus)

| Strategy | Direction | n | WR | Status |
|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 158 | 15.2% | On queue since 04Z |
| `myfxbook_retail_contrarian` | LONG | 118 | 10.2% | On queue since 04Z |
| `quan_engine_swing` | LONG | 104 | 26.0% | On queue since 04Z |
| `rapid_fire` × UUSDT | — | 34 | 0.0% | On queue since 04Z |
| `cta_cross_asset_tsmom` | LONG | 69 | 29.0% | **NEW this run** |

### 3.3 High symbol-variance systems (mutation target, not kill)

- `multi_asset_copytrader`: SI=F, AMD, ZW=F → 0% WR (symbol-allowlist mutation, sandbox gate)
- `quan_engine`: MATICUSDT (0%), ONDOUSDT (22%), SOLUSDT (23%) — HYPEUSDT already blocked by PR #694
- `rapid_fire`: UUSDT (0%, n=34), ESPUSDT (0%, n=5), TAOUSDT (5.6%, n=18)

---

## 4. Constraints Verified

- ✅ Resolver-rescope DONE (issue #685) — no code changes attempted
- ✅ Plan v2.1 stats (PF 5.81, ml_score 0.90) not cited anywhere in this report
- ✅ No peer PR rebases performed
- ✅ HOLD set (#660 #658 #681 #661) not in open list — not touched
- ✅ No auto-kills — `cta_cross_asset_tsmom` finding posted for 3-AI consensus only
- ✅ `audit_dashboard/template.html` not touched (generator not run locally)
- ✅ `updates/index.html` not touched

---

## 5. Key Findings Summary

1. **Dashboard same snapshot as 04Z** (03:59:34Z) — hourly cron has not yet rebuilt; all numbers identical to 04Z run.
2. **EQUITY sustained T1**: 7d PF=4.70 / 30d PF=3.25 — post-#692 goldmine_6x_consensus kill is holding. Issue #693 hypothesis confirmed: deterioration was concentrated in that one strategy.
3. **FOREX recovery sustained**: 7d PF=1.67 / 30d PF=1.57 — both now above T2-floor (>1.5). Pre-#687 baseline was 0.14 / 0.97 respectively.
4. **COMMODITY T1-candidate**: n=101 crosses charter floor; 30d PF=4.44 / WR=52.5%. Stable.
5. **CRYPTO 24h normalization**: spike to PF 3.54 was transient; 1.55 at 24h is healthy. 7d PF=1.40 slightly above 04Z 7d anchor (1.33→1.40). No action.
6. **NEW kill candidate**: `cta_cross_asset_tsmom` LONG (n=69, WR=29%) — posted to issue #686 for consensus.

---

## 6. References

- Issue #685: resolver-rescope done — do not open resolver PRs
- Issue #686: per-asset attribution + kill queue — new comment added this run
- Issue #693: EQUITY degradation monitor — hypothesis confirmed (goldmine_6x was the cause)
- PR #692 (merged today): goldmine_6x_consensus kill — EQUITY recovery confirmed
- PR #687 (merged today): JPY-cross BUY rule fix — FOREX recovery confirmed
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

# Hourly Audit Report — 2026-05-05T02Z (UTC)

**Generated:** 2026-05-05T02:13Z  
**Agent:** Claude Sonnet 4.6  
**Dashboard snapshot:** 2026-05-05T01:37:46Z (auto-hourly [skip ci] confirmed)  
**Picks window:** n=3500 recent_closed  
**Session context:** Issues #685 (resolver done) / #686 (quality regression) / #693 (EQUITY monitor)  
**Today's merged PRs (prior to this session):** #684 #674 #673 #664 #683 #687 #692 #694

---

## 1. Dashboard Refresh Status

Dashboard auto-refreshed at **2026-05-05T01:37:46Z** via `[skip ci]` cron. Pull from `origin/main` confirmed — fast-forward to `3f15773f`, then to `7f4d5525` (post-merge of docs PRs). Data is current (~36 min lag at report time).

---

## 2. Per-Asset PF/WR — Current vs Baseline

Computed from `picks.recent_closed` (n=3500) at 02:09Z using `closed_at` timestamp windowing.

### Windowed metrics (raw, all recent_closed)

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 88 | 59.1% | **2.02** | 597 | 51.6% | **1.64** | 1183 | 48.0% | **1.41** |
| EQUITY | 6 | 50.0% | **1.76** | 34 | 47.1% | **1.11** | 111 | 65.8% | **3.09** |
| FOREX | 45 | 17.8% | **0.62** | 107 | 16.8% | **0.41** | 123 | 23.6% | **0.55** |
| COMMODITY | 9 | 44.4% | **1.42** | 38 | 42.1% | **1.30** | 43 | 37.2% | **1.03** |
| ETF | 3 | 33.3% | **1.35** | 9 | 44.4% | **1.01** | 37 | 73.0% | **3.58** |
| BOND | 0 | — | — | 0 | — | — | 0 | — | — |
| FUTURES | 0 | — | — | 0 | — | — | 0 | — | — |

### Long-run verdict-grade (asset_class_health, post-resolver-v2)

| Class | PF | WR | Tier |
|---|---|---|---|
| FOREX | 0.28 | 45.6% | Sub-floor — mutate-before-kill active |
| CRYPTO | 1.26 | 44.8% | Sub-T2 — quan_engine + unknown drag |
| EQUITY | 1.42 | 52.8% | T2 candidate |
| COMMODITY | 2.08 | 48.7% | T2 (lift WR target) |
| ETF | 1.20 | 53.4% | Borderline T2 (n→100) |
| BOND | 1.72 | 55.6% | Meets T2 PF+WR, n=18 below charter floor |

### Delta vs task-prompt baseline

| Class | Window | Baseline | Current | Delta | Signal |
|---|---|---|---|---|---|
| CRYPTO | 24h | PF 3.54 | **2.02** | **-1.52** | ⚠ Degraded (regime/vol; #694 HYPE block may not show yet in 24h) |
| CRYPTO | 7d | PF 1.33 | **1.64** | **+0.31** | ✅ Improved |
| CRYPTO | 30d | PF 1.33 | **1.41** | **+0.08** | ✅ Slight improvement |
| EQUITY | 7d | PF 0.87 | **1.11** | **+0.24** | ✅ Goldmine_6x kill (PR #692) confirmed effective |
| EQUITY | 30d | PF 1.41–2.18 | **3.09** | **↑** | ✅ Strong long-run |
| FOREX | 7d | PF 0.14 (pre-#687) | **0.41** | **+0.27** | ✅ JPY-cross fix measurably effective |
| FOREX | 30d | PF 0.97 (pre-#687) | **0.55** | **-0.42** | ⚠ 30d drags (includes pre-fix data) |

---

## 3. PR Triage

### Open PRs at check time (8 total)

| PR | Title | CI | Reviews | Action |
|---|---|---|---|---|
| #808 | docs: GPT-5.5 asset-class feedback | scan ✅ only | Codex rate-limit (COMMENTED) | **MERGED ✅** |
| #807 | docs: swarm action plan claude-opus-4-7 | scan ✅ only | Codex rate-limit (COMMENTED) | **MERGED ✅** |
| #806 | docs: Copilot audit analysis | scan ✅ only | Codex COMMENTED | **MERGED ✅** |
| #805 | docs: per-asset deep dive claude-opus-4-7 | scan ✅ only | none | **MERGED ✅** |
| #798 | fix(security): memecoin credential env-var | smoke ❌ FAIL | — | HOLD — CI failure |
| #777 | fix(sports): midnight date bucketing | smoke ❌, test(3.12) ❌ | — | HOLD — CI failure |
| #772 | feat(B9): adversarial shadow | test(3.11) ❌, "DO NOT ADMIN-MERGE" | — | HOLD — explicit + CI |
| #764 | feat(B5): concept scorer | test(3.12) ❌ | — | HOLD — CI failure |

### HOLD set status (#660 #658 #681 #661)

| PR | Status | Note |
|---|---|---|
| #660 | **Merged** in prior session — cannot reverse | Plan v2.1 family; already on main |
| #661 | **Merged** in prior session — cannot reverse | Plan v2.1 family; already on main |
| #658 | Closed without merge ✓ | Appropriately handled |
| #681 | Closed without merge ✓ | Wire-Up Rule failure + fabricated WR table |

### Author-rebase PRs check (#669 #676 #608 #665 #644 #597 #615 #655)

All already merged or closed — zero open. No action required.

---

## 4. New Strategy Kill Candidates — mutation_analysis.py

Ran `python tools/mutation_analysis.py --json` at 02:10Z. Full direction-flip matrix computed from recent_closed n=3500.

### Direction-flip (Axis-1) findings

| Strategy | Direction | n | WR% | PF | Verdict |
|---|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | **LONG** | 302 | 38.7% | 0.58 | ⚠ Below break-even; PF not yet <0.5 but WR<40% sustained |
| `forex_rsi2_mean_reversion` | SHORT | 339 | 49.6% | 3.47 | ✅ Keep — strong directional split per Axis-1 |
| `quan_engine` | LONG | 158 | 29.1% | 0.71 | ⚠ Ongoing drag; HYPE block (#694) may not show in 30d window yet |
| `quan_engine` | SHORT | 156 | 31.4% | 0.60 | ⚠ Both directions sub-1 |
| `macd_rsi_confluence` | LONG | 32 | 28.1% | 0.59 | Watch (n=32, borderline) |
| `cta_cross_asset_tsmom` | SHORT | 46 | 43.5% | 2.46 | ✅ Good — direction flip (SHORT profitable) |

### PF<0.5 + n>=20 — requires 3-AI consensus before kill

| Strategy | Direction | n | WR% | PF |
|---|---|---|---|---|
| `unknown` (source_system) | SHORT | 46 | 4.3% | **0.12** |

Already flagged in CLAUDE.md (7% CRYPTO volume @ PF 0.35). Meets kill threshold numerically. **No auto-kill — requires 3+ AI consensus.** Posted to issue #686.

### Issue #693 monitoring check ✅

EQUITY 7d PF = **1.11** (+0.24 vs 0.87 baseline at issue creation). PR #692 goldmine_6x_consensus kill confirmed as the cause. Per #693 plan: "If EQUITY 14d returns to PF≥1.5 within 7 days post-#692, the deterioration was concentrated in goldmine_6x." Next checkpoint: check EQUITY 14d at next hourly.

---

## 5. PRs Merged This Session

| PR | Title | Method |
|---|---|---|
| #805 | docs(audit): per-asset deep dive claude-opus-4-7 | squash |
| #806 | docs(audit): Copilot audit analysis + analysis scripts | squash |
| #807 | docs(audit): swarm-mediated multi-agent action plan | squash |
| #808 | docs(audit): GPT-5.5 asset-class feedback | squash |

**Total merged this session: 4** (all docs-only, scan CI green, no REQUEST_CHANGES, no Plan v2.1 content)

---

## 6. Next Actions (Priority Order)

| Priority | Action | Gate |
|---|---|---|
| P1 | `forex_rsi2_mean_reversion` LONG direction kill — run Axis-2 (timeframe) + Axis-3 (symbol) | Needs 3-AI consensus; operator go-ahead |
| P1 | `unknown` source_system kill — add to BLOCKED_SOURCE_SYSTEMS | 3-AI consensus required |
| P2 | Fix CI failures on #777 (sports smoke/test), #798 (smoke), #764/#772 (pytest) | Engineering |
| P3 | EQUITY 14d re-check — target PF≥1.5 to confirm #692 sufficient | Monitor only |
| P3 | CRYPTO 24h degradation watch — PF 2.02 vs 3.54 baseline; monitor next snapshot | Monitor |

---

_Generated 2026-05-05T02:13Z — Claude Sonnet 4.6 (claude-sonnet-4-6)_  
_Refs: issue #685 (resolver scope confirmed done), issue #686 (mutation update posted), issue #693 (EQUITY recovery confirmed)_

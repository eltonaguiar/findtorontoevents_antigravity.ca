# Hourly Audit — 2026-05-17 06Z

**Dashboard snapshot:** `audit_dashboard/data/dashboard_data.json` generated 2026-05-17T04:06:41Z  
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-17_05Z.md` (05:16Z)  
**Git pull:** fast-forward to `2bb94227` (included 05Z audit + #1130 gap-aware TP fill merge)

---

## 1. Asset Class Health — All-Time (post-resolver-v2)

| Class | n | WR | PF | Status | Delta vs Baseline |
|---|---|---|---|---|---|
| COMMODITY | 228 | 85.5% | **7.71** | T1 | ↑↑ (was 1.78 pre-resolver-v2) |
| ETF | 75 | 66.7% | **2.25** | T2 ✅ | ↑ (was 1.24) |
| EQUITY | 393 | 53.2% | **1.65** | T2 ✅ | ↑ (was 1.41, +#692 kill) |
| CRYPTO | 7563 | 47.0% | **1.32** | watch | ↑ (was 1.25) |
| FOREX | 251 | 57.8% | **0.85** | recover | ↑↑ (was 0.27 pre-#687) |
| BOND | 11 | 54.5% | 0.66 | thin (n<100) | — |

Tier definitions: T1 = PF≥2.0/WR≥55%/MDD<10%; T2 = PF≥1.5/WR≥50%/MDD<20%.

---

## 2. Windowed Per-Asset Metrics (from `picks.recent_closed`)

Dashboard timestamp is 04:06Z; windows are relative to now (~06:15Z).

### 24h window — n=28 total
| Class | n | WR | PF | Alert |
|---|---|---|---|---|
| CRYPTO | 23 | 21.7% | 0.21 | 🚨 DEEPENING — was 0.68 at 05Z |
| ETF | 4 | 75.0% | 1.19 | stable |
| BOND | 1 | 0.0% | — | thin |

**CRYPTO 24h alert progression:** baseline 3.54 → 05Z 0.68 → **06Z 0.21**. Window shift accounts for ~2h of picks rolling off, but underlying weakness is real. PF<1.0 for 2+ consecutive hourly snapshots. Monitor closely at 07Z; if CRYPTO 24h PF remains <0.5, escalate to issue #686 for cross-AI review before any strategy changes.

### 7d window — n=294 total
| Class | n | WR | PF | Delta vs 05Z |
|---|---|---|---|---|
| CRYPTO | 257 | 44.4% | 1.04 | ↓ from ~1.33 baseline |
| COMMODITY | 27 | 29.6% | 0.64 | = (same — cta_replicator drag persists) |
| ETF | 4 | 75.0% | 1.19 | stable |
| FOREX | 2 | 50.0% | 5.00 | thin (n<10 post-#687 kills) |
| EQUITY | 2 | 50.0% | 0.32 | thin |

### 30d window — n=1306 total
| Class | n | WR | PF | Status |
|---|---|---|---|---|
| CRYPTO | 1220 | 47.9% | 1.22 | ↓ from 1.33 baseline |
| COMMODITY | 64 | 57.8% | 2.00 | ↑ T2-grade |
| FOREX | 10 | 30.0% | 1.31 | thin |
| ETF | 4 | 75.0% | 1.19 | thin |
| EQUITY | 5 | 20.0% | 0.02 | thin (n=5 only, unreliable) |

**Note:** small n for EQUITY/FOREX/ETF in recent_closed windows reflects the system's CRYPTO-volume dominance; all-time health numbers (section 1) are more reliable for those classes.

---

## 3. Key Deltas vs Issue #686 Baseline (2026-05-02) and 05Z Audit

| Metric | #686 Baseline | 05Z Audit | **06Z Now** | Verdict |
|---|---|---|---|---|
| CRYPTO 24h PF | 2.65 | 0.68 | **0.21** | 🚨 ALERT — multi-hour weakness |
| CRYPTO 7d PF | 1.21 | ~1.04 | **1.04** | declining trend |
| CRYPTO 30d PF | 1.28 | ~1.22 | **1.22** | ↓ mild |
| FOREX 7d PF | 0.14 | 1.60 | thin (n=2) | recovery intact post-#687 |
| FOREX 30d PF | 0.97 | 2.30 | 1.31 (n=10) | recovery intact |
| COMMODITY 7d PF | 1.18 | 0.64 | **0.64** | cta_replicator drag unresolved |
| COMMODITY 30d PF | 1.04 | 1.97 | **2.00** | strong long-run |
| EQUITY 30d PF | 2.18 | 2.52 | **1.65** (all-time) | #692 kill improving |

---

## 4. PR Triage

### Merged this hour
| PR | Title | Action | Rationale |
|---|---|---|---|
| **#1130** | fix(resolver): gap-aware TP/SL fill — C1 | ✅ MERGED | clean + all-CI-green + no reviews |
| **#1126** | audit: hourly audit 05Z | ✅ MERGED | report-only, clean, no reviews |

### Open + HOLD
| PR | Title | Status | Reason |
|---|---|---|---|
| #1132 | fix(resolver+dashboard): C1 paths B/C + D2 | HOLD | test(3.11) FAIL + gate in_progress |
| #1125 | fix(reports): COMMODITY COT direction | HOLD | mergeable_state=dirty (merge conflicts) |

### Legacy HOLD set
Old HOLD set (#660/#658/#681/#661 — Plan v2.1 fabricated stats family) and old rebase set (#669/#676/#608/#665/#644/#597/#615/#655) are **no longer open** per 05Z audit verification.

---

## 5. New Strategy Kill Candidates (mutation_analysis.py)

Run: `python tools/mutation_analysis.py --json` against 04:06Z dashboard.

### Meeting kill criteria (n≥20, WR<35%, pattern match):

| Strategy | Symbol | n | WR | Avg PnL% | Action |
|---|---|---|---|---|---|
| `rapid_fire` | UUSDT | 34 | **0.0%** | -0.17% | Post #686, await 3-AI consensus |
| `cta_replicator` | NG=F | 24 | **0.0%** | -0.03% | Post #686, await 3-AI consensus |
| `cta_replicator` | CL=F | 47 | **19.1%** | -0.01% | Post #686, await 3-AI consensus |
| `rapid_fire` | (strategy-level) | 207 | 29.0% | varies | Mutation analysis first |
| `multi_asset_copytrader` | (strategy-level) | 1069 | 21.7% | varies | Mutation analysis first |

### Near-threshold (monitor, do not act):
- `rapid_fire:TAOUSDT` — WR=5.6%, n=18 (n<20)
- `cta_replicator:ZC=F` — WR=0%, n=8 (n<20)

**Posted to issue #686** (comment #4469563325). Per CLAUDE.md: NO auto-kill. 3+ AI consensus required. Mutation/inverse/symbol-rotation analysis required for strategy-level kills.

### Already actioned (reference):
- `quan_engine:HYPEUSDT` — blocked PR #694 ✅
- `forex_carry_momentum` + `goldmine_6x_consensus` — killed PR #692 ✅

---

## 6. Findings Summary

1. **CRYPTO 24h ALERT deepening** — PF 3.54 → 0.68 → 0.21 across three snapshots. Cause unknown (regime shift? time-of-day effect? post-#694 HYPEUSDT volume adjustment?). Do not act until 24h streak resolves. If PF<0.5 persists at 07Z, open cross-AI review thread on #686.

2. **COMMODITY 7d drag confirmed** — cta_replicator NG=F (WR=0%, n=24) and CL=F (WR=19%, n=47) are confirmed kill candidates, awaiting 3-AI consensus. 30d COMMODITY (PF=2.00) is healthy; short-term drag is strategy-specific.

3. **FOREX recovery intact** — post-#687 JPY-cross BUY rule fix: FOREX all-time PF moved from 0.27 → 0.85, 7d/30d windows recovering but thin samples.

4. **#1130 gap-aware TP fill** — merged. This fixes the "ghost row" artifact (81% of signal_validation wins at exactly +3.0%). Downstream: C1 historical re-resolution (~8k rows) is the next step but requires DB backup first. #1132 (Paths B/C + D2) is the follow-on PR — HOLD until CI green.

5. **EQUITY improving long-run** — all-time PF 1.65 (T2 candidate). 30d recent_closed thin (n=5) so can't compute windowed reliably. goldmine_6x kill in #692 is working.

---

## 7. Next Hour Priorities (07Z)

1. Re-check CRYPTO 24h PF — if still <0.5, post cross-AI thread to #686
2. Wait for #1132 CI re-run (test 3.11 failure needs diagnosis first)
3. Resolve #1125 merge conflict once author rebases or we coordinate
4. If 3-AI consensus arrives on cta_replicator:NG=F + rapid_fire:UUSDT, propose symbol-block PR

---

_Generated 2026-05-17T~06:15Z by hourly audit agent._

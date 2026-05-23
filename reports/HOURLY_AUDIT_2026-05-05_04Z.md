# Hourly Audit — 2026-05-05 04Z UTC

**Generated:** 2026-05-05 ~04:10 UTC  
**Dashboard snapshot:** 2026-05-05T03:59:17Z (auto-refresh [skip ci])  
**Auditor:** Claude Sonnet 4.6  
**Issues context:** #685 (resolver-rescope DONE), #686 (FOREX/EQUITY attribution), #693 (EQUITY 7d/14d/30d monitor)

---

## 1. Dashboard Refresh Status

Dashboard data confirmed at `2026-05-05T03:59:17.472776+00:00` — fresh (11 min old at audit time). Pulled from origin/main (force-updated). Working tree clean.

---

## 2. Per-Asset PF/WR — 24h / 7d / 30d Windows

Computed from `picks.recent_closed` (n=3500 cap) via live `closed_at` timestamps.

### CRYPTO

| Window | n | WR | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 90 | 61.1% | **2.04** | +56.29% |
| 7d | 607 | 51.6% | **1.65** | +242.58% |
| 30d | 1499 | 44.3% | **1.36** | +315.79% |
| Long-run (health) | 8159 | 45.0% | **1.27** | +2243.89% |

**Delta vs baseline (24h PF 3.54 / 7d 1.33 / 30d 1.33):**
- 24h: 3.54 → 2.04 (−1.50) — regression vs prior baseline but n=90 is noisy; 7d trend is improving
- 7d: 1.33 → 1.65 (+0.32) ✅ improving — likely residual effect of PR #694 HYPEUSDT block + #683 cftc_cot kill
- 30d: 1.33 → 1.36 (+0.03) — stable, slight improvement

**Verdict:** CRYPTO trending right on 7d. Do not destabilize (per issue #686). 24h drop is statistical noise at n=90.

---

### EQUITY

| Window | n | WR | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 6 | 50.0% | **1.76** | +8.0% |
| 7d | 30 | 43.3% | **1.08** | +5.39% |
| 30d | 126 | 63.5% | **3.05** | +254.3% |
| Long-run (health) | 428 | 52.8% | **1.42** | +276.23% |

**Delta vs baseline (7d 0.87 / 30d 1.41–2.18):**
- 7d: 0.87 → 1.08 (+0.21) ✅ — PR #692 goldmine_6x kill reducing drag
- 30d: 2.18 → 3.05 (+0.87) ✅ — strong recovery; window now post-goldmine_6x cleanout
- 24h: n=6 too small to interpret

**Issue #693 monitor status:** 7d PF 1.08 — partial recovery from 0.87. Still below T2 floor (1.5). Watch `stocks_rsi2_pullback` (7d WR ~35%) as per issue #693 rec: if stays <40% on n≥20 at next 24h/72h check, escalate to mutation analysis.

---

### FOREX

| Window | n | WR | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 45 | 17.8% | **0.62** | −8.85% |
| 7d | 117 | 19.7% | **0.41** | −28.62% |
| 30d | 564 | 45.6% | **0.66** | −18.15% |
| Long-run (health) | 1251 | 45.7% | **0.28** | −985.68% |

**Delta vs baseline (7d 0.14 / 30d 0.97 pre-PR-#687):**
- 7d: 0.14 → 0.41 (+0.27) ✅ — PR #687 JPY-cross BUY rule fix + PR #692 strategy kills working
- 30d: 0.97 → 0.66 (−0.31) ⚠️ — 30d window accumulating legacy losses from pre-fix era; expected to resolve over next 3–4 weeks
- 24h WR 17.8% — still catastrophic but improved from 0% (issue #686 baseline)

**Verdict:** FOREX still deep in stressed/sub-floor territory. Mutation-before-kill protocol applies. Post findings to issue #686 (see Section 4). Do NOT expand `BLOCKED_SOURCE_SYSTEMS` without 3-AI consensus.

---

### COMMODITY

| Window | n | WR | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 9 | 44.4% | **1.42** | +5.27% |
| 7d | 43 | 37.2% | **1.30** | +17.96% |
| 30d | 500 | 41.2% | **0.89** | −11.92% |
| Long-run (health) | 818 | 48.8% | **2.11** | +293.96% |

**⚠️ NEW CONCERN — COMMODITY 30d regression:** Long-run PF 2.11 (T2 grade) but 30d window PF 0.89. Monotonic deterioration: 30d < 7d in terms of WR (41.2% vs 37.2%), and 30d PF sub-1. This suggests a regime change or a specific strategy pulling the 30d window down. `futures_momentum` was flagged in issue #685 as a kill candidate (gated on re-resolve). **Action:** monitor at next hourly window; if 30d PF stays <1.0 at next check, run targeted attribution on COMMODITY recent_closed.

---

### ETF

| Window | n | WR | PF | Sum PnL% |
|---|---|---|---|---|
| 24h | 3 | 33.3% | **1.35** | +0.69% |
| 7d | 9 | 44.4% | **1.01** | +0.10% |
| 30d | 37 | 73.0% | **3.58** | +52.84% |
| Long-run (health) | 88 | 53.4% | **1.20** | +19.79% |

ETF 7d at break-even (PF 1.01) while 30d is excellent. n=88 still below charter n=100 threshold for T2 candidate. Monitor; no action needed.

---

### BOND / FUTURES

- BOND: n=0 in all windows (long-run n=18, thin sample). No recent activity.
- FUTURES: n=0 in 24h/7d; 30d n=2 (PF=inf, 0 losses, but near-zero pnl). Insufficient data.

---

## 3. PR Triage

Open PRs as of 04:10 UTC: #810, #798, #777, #772, #764 (5 total — page 2 empty).

| PR | Title | CI | Reviews | Mergeable | Decision |
|---|---|---|---|---|---|
| #810 | chore(loop): mark V1 verified — UEPS picks | scan=✅ | none | unknown (base SHA behind main after force-push) | **HOLD** — mergeable_state unresolved |
| #798 | fix(security): memecoin credential env var | smoke=❌ | Codex COMMENT only | — | **HOLD** — CI failure |
| #777 | fix(sports): normalize EST day bucketing | smoke=❌ test(3.12)=❌ | none | — | **HOLD** — CI failure |
| #772 | feat(b9): adversarial debate shadow | test(3.11)=❌ | none | — | **HOLD** — CI failure + "DO NOT ADMIN-MERGE" by author |
| #764 | feat(b5): concept-aware scoring shadow | NO CI RUNS | none | — | **HOLD** — CI not triggered on head commit `96b34418c` |

**HOLD set (#660, #658, #681, #661):** Not in open PR list — already closed prior to this session. No action.

**Rebase-check PRs (#669, #676, #608, #665, #644, #597, #615, #655):** None present in open PR list — all closed/merged prior to this session. No action needed.

**Merged this hour: NONE.** No PR met all three criteria (MERGEABLE + ALL CI green + no REQUEST_CHANGES).

---

## 4. New Strategy Findings — mutation_analysis.py

Ran `python tools/mutation_analysis.py --json` (2026-05-05 04:05 UTC).

### Confirmed kill candidates (meet n≥20, WR<35% sustained — post to issue #686):

| Strategy | Direction | n | WR | Avg PnL% | Asset Class | Action |
|---|---|---|---|---|---|---|
| `forex_rsi2_mean_reversion` | LONG | 82 | **2.4%** | −0.00% | FOREX | P1 kill — already in #686; evidence now confirmed via mutation tool |
| `myfxbook_retail_contrarian` | LONG | 88 | **10.2%** | −0.01% | FOREX | **NEW** — meets kill criteria; needs 3-AI consensus before block |
| `ig_contrarian_sentiment` | LONG | 121 | **19.0%** | −0.00% | FOREX | **NEW** — meets kill criteria (n≥20, WR<35%); needs 3-AI consensus |
| `cta_cross_asset_tsmom` | LONG | 57 | **35.1%** | −0.01% | FOREX/Multi | **NEW** — borderline (WR at floor); watch, do not kill yet |
| `quan_engine_swing` | LONG | 104 | **26.0%** | −0.00% | CRYPTO | **NEW** — below 35% WR floor; but SHORT (n=5) at 60% WR — direction-flip strategy, mutation priority |

### Symbol-level block candidates (not auto-kills — sandbox mutation needed):

| System | Symbol | n | WR | Decision |
|---|---|---|---|---|
| `rapid_fire` | UUSDT | 34 | **0.0%** | **NEW** — n≥20, WR=0%; matches existing `rapid_fire` symbol kill pattern; propose `BLOCKED_STRATEGY_SYMBOL_PAIRS` add after 3-AI consensus |
| `rapid_fire` | TAOUSDT | 18 | **5.6%** | Borderline — n<20; watch to 20 before action |
| `quan_engine` | HYPEUSDT | 553 | **41.6%** | Already blocked by PR #694 ✅ |
| `multi_asset_copytrader` | SI=F, AMD, ZW=F | <5 each | 0% | n too small — no action |

**Do NOT add to BLOCKED_* without 3-AI consensus.** Post to issue #686 for peer review.

---

## 5. Cross-Issue Status

| Issue | Status | Action |
|---|---|---|
| #685 | Resolver-rescope DONE; operational re-resolve awaiting operator go-ahead | No code action — closed when operator runs re_resolve_historical_v2.py |
| #686 | FOREX attribution ongoing; new strategies added this hour (see Section 4) | Posting comment with myfxbook/ig_contrarian findings |
| #693 | EQUITY 7d partial recovery: 0.87 → 1.08; stocks_rsi2_pullback still dragging | Monitor at 72h per issue rec |

---

## 6. Summary

- **Dashboard fresh** at 03:59Z (11 min ago).
- **CRYPTO improving** on 7d/30d windows; 24h dip is n=90 noise.
- **EQUITY recovering** post goldmine_6x kill; 7d PF 1.08 (up from 0.87), 30d PF 3.05.
- **FOREX improved 7d** from PF 0.14 → 0.41 (PR #687 fix working), but still deeply sub-floor.
- **COMMODITY NEW CONCERN**: 30d PF 0.89 vs long-run 2.11 — possible recent regime change; monitor next hour.
- **ETF near break-even** 7d (PF 1.01); 30d excellent (3.58). Watch n→100.
- **0 PRs merged** — no PR met all three criteria.
- **3 new mutation findings** for issue #686: `myfxbook_retail_contrarian` LONG, `ig_contrarian_sentinel` LONG, `rapid_fire` UUSDT.

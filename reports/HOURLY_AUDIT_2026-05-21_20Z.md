# Hourly Audit — 2026-05-21 20Z

**Generated:** 2026-05-21T20:12Z  
**Dashboard snapshot:** `2026-05-21T19:09:58Z` ✅ (cron self-corrected; 19Z had stale 12:18:29Z)  
**Session:** claude-sonnet-4-6  
**Issues context:** #685 (resolver-rescope done), #686 (per-asset attribution), #693 (closed — EQUITY monitor)

---

## Dashboard Refresh Status

Dashboard is **FRESH** (19:09:58Z) after the 7-hour stale alert reported in the 19Z audit (PR #1298). The outcome-resolver.yml / dashboard-generator.yml crons self-recovered. No operator action needed.

---

## Per-Asset Metrics (20Z)

Source: `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (n=3500 cap) + `performance.asset_class_health` (post-noise-filter).

| Class | 24h n | 24h PF | 24h WR% | 7d n | 7d PF | 7d WR% | 30d n | 30d PF | 30d WR% | ACH PF (noise-filtered) |
|-------|-------|--------|---------|------|-------|--------|-------|--------|---------|------------------------|
| CRYPTO | 108 | 2.654 | 53.7% | 901 | 1.442 | 48.8% | 2747 | 1.345 | 46.2% | 1.280 |
| EQUITY | 10 | 2.368 | 60.0% | 47 | **0.805** | 36.2% | 149 | 1.452 | 43.6% | 0.921 |
| FOREX | 8 | 1.560 | 50.0% | 12 | **1.543** | 41.7% | 94 | **2.605** | 48.9% | 3.177 |
| COMMODITY | 3 | 1.933 | 33.3% | 35 | **0.246** | **11.4%** | 79 | 0.943 | 40.5% | 1.296 |
| ETF | 1 | 0.000 | 0.0% | 10 | 0.972 | 10.0% | 47 | 2.093 | 59.6% | 11.995 |
| BOND | 0 | — | — | 4 | 0.000 | 0.0% | 4 | 0.000 | 0.0% | 0.000 |
| FUTURES | 0 | — | — | 0 | — | — | 2 | inf | 100% | 0.956 |

### Deltas vs Documented Baseline

| Class | Window | Baseline | Current | Delta | Status |
|-------|--------|----------|---------|-------|--------|
| CRYPTO | 24h | 3.54 | 2.654 | **−0.89** | Monitor — regime or vol shift |
| CRYPTO | 7d | 1.33 | 1.442 | +0.11 | Stable |
| CRYPTO | 30d | 1.33 | 1.345 | +0.015 | Stable |
| EQUITY | 7d | 0.87 | 0.805 | −0.065 | Continuing decline; post-#692 recovery lag expected |
| EQUITY | 30d | 1.41 | 1.452 | +0.04 | T2 floor intact |
| FOREX | 7d | 0.14 (pre-#687) | 1.543 | **+1.40** | Spectacular recovery — #687 JPY-cross BUY fix working |
| FOREX | 30d | 0.97 (pre-#687) | 2.605 | **+1.63** | Strong |
| COMMODITY | 7d | 1.422 (19Z stale) | 0.246 | **−1.18** | REGRESSION (see FINDING-59 below) |

**Note on COMMODITY discrepancy:** The 19Z audit reported COMMODITY PF=1.422 from the stale 12:18:29Z dashboard. The fresh 19:09:58Z snapshot shows COMMODITY 7d PF=0.246. The `asset_class_health` noise-filtered value is PF=1.296, suggesting the raw recent_closed window contains pre-noise-filter picks. Both the regression and the noise-filter PF are concerning — COMMODITY was a T2 candidate at PF=1.78 in the original CLAUDE.md baseline.

---

## Findings This Hour

### FINDING-59 — `futures_momentum x COMMODITY` block gap (EMERGING, 1/3 votes)

**Evidence:**
- COMMODITY 7d: n=35 picks, WR=11.4%, PF=0.246 (catastrophic)
- `futures_momentum` attribution: n=17, WR=12%, pnl_sum=−52.81% (SI=F×9, PL=F×6)
- `cftc_cot_commercial_signal` attribution: n=16, WR=12%, pnl_sum=−42.92% (CT=F×13, ZW=F×3)

**Root cause (futures_momentum):**
`BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py` contains `("FUTURES", "futures_momentum")` (added 2026-05-19, H-005 escalation) but does NOT contain `("COMMODITY", "futures_momentum")`. futures_momentum fires on commodity symbols (SI=F silver, PL=F platinum) under the COMMODITY asset class and is unblocked there.

**Root cause (cftc_cot_commercial_signal):**
`cftc_cot_commercial_signal` appears in the blocked list (`quality_gates.py:2078`, added 2026-05-16), but picks from before the block date are still in `recent_closed`. The 7d window (from ~2026-05-14) pre-dates the 2026-05-16 block, so historical contamination is expected. Verify live picks: if any cftc_cot_commercial_signal COMMODITY picks were generated after 2026-05-16, that is a gate leak.

**Gate status vs kill criteria:**
- `futures_momentum x COMMODITY`: n=17 < 20 gate floor → **EMERGING** (not yet kill-eligible; document for next session)
- `cftc_cot_commercial_signal`: already blocked (historical bleed, not new picks)

**Recommended action:**
- Monitor COMMODITY 7d after 2026-05-23 (full flush of pre-block cftc_cot picks)
- If `futures_momentum x COMMODITY` reaches n=20 with WR<35%: add `("COMMODITY", "futures_momentum")` to `BLOCKED_ASSET_STRATEGY_PAIRS` (pattern matches existing FUTURES kill)
- Do NOT auto-kill at n=17

### FINDINGS 56/57/58 (carry from 19Z)

Per mutation analysis (confirmed this hour):

| Finding | Strategy | Direction | n | WR | Status |
|---------|----------|-----------|---|----|--------|
| 56 | `ig_contrarian_sentiment x LONG` | LONG | 200 | 16.5% | 1/3 votes — needs 2 more AI |
| 57 | `myfxbook_retail_contrarian x LONG` | LONG | 124 | 13.7% | 1/3 votes |
| 58 | `quan_engine_swing x LONG` | LONG | 104 | 26.0% | 1/3 votes |

All three meet gate: n≥20 + WR<35%. Axis 1 (directional flip) candidates. Awaiting cross-AI consensus (2 more votes per CLAUDE.md protocol before any kill action).

### FINDINGS 54/55 (carry)

| Finding | Strategy×Symbol | n | WR | Status |
|---------|----------------|---|----|--------|
| 54 | `cta_replicator × NG=F` | 24 | 0% | 1/3 votes |
| 55 | `rapid_fire × UUSDT` | 34 | 0% | 1/3 votes |

---

## PR Triage

### Open PRs (as of 20:12Z)

| PR | Title | CI | Reviews | Action |
|----|-------|----|---------|--------|
| #1298 | 19Z audit | 3/3 ✅ | Bot comment only | **MERGED** (this hour) ✓ |
| #1292 | B10 UEPS KPI | 6/6 ✅ | — | Already merged at 19:15Z |
| #1287 | B10 UEPS KPI (older) | — | — | HOLD — superseded by #1292 |
| #1279 | AGENTS.md docs | — | — | HOLD — DRAFT |

**Note on #1292 XSS concern:** The 19Z session flagged XSS in #1292 (kpi.tickers/strategies/message injected via innerHTML) and stated "HOLD." However, #1292 was already merged at 19:15:25Z — *7 minutes before* the 19Z audit PR was created at 19:22:17Z. The XSS finding may be moot (picks from live active data, not user input) or may need a follow-up patch. Flag for human review.

### HOLD set verification

| PR | Status |
|----|--------|
| #660 | Closed — merged 2026-05-03T21:55Z (pre-fabrication-refutation; artifact) |
| #658 | Closed — NOT merged ✅ |
| #681 | Not visible in open list ✅ |
| #661 | Not visible in open list ✅ |

Plan v2.1 guardrails: clean. No open PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER.

### Rebase set (#669 #676 #608 #665 #644 #597 #615 #655)

All absent from open PR list — confirmed closed/merged in prior sessions. No action needed.

---

## Mutation Analysis — New Kill Candidates

Per `python tools/mutation_analysis.py --json` (20Z run):

**Meets gate (n≥20, WR<35%):** FINDINGS 56/57/58 (already carried). No new unique strategies beyond those.

**Axis 4 candidates** (flagged by tool, below escalation_wr_floor but need mutation testing before kill):
- `multi_asset_copytrader`: WR=22%, n=1148 (complex; symbol-level fixes cleaner)
- `rapid_fire`: WR=29%, n=207

**No new PF<0.5 + n>=20 strategies emerged beyond the COMMODITY 7d regression documented above as FINDING-59.**

---

## Summary

| Item | Result |
|------|--------|
| Merged PRs | **#1298** (19Z audit) |
| New findings | **1** (FINDING-59 — futures_momentum×COMMODITY block gap) |
| Carry findings | 5 (FINDING-54/55/56/57/58) |
| Dashboard status | ✅ Fresh (19:09:58Z) |
| FOREX recovery | ✅ 19th hour ≥PF 1.0 confirmed (7d PF=1.543) |
| CRYPTO | Stable (24h dip vs baseline, 7d/30d on trend) |
| EQUITY | Sub-T2 at 7d (0.805); post-#692 recovery lag — recheck at 22Z |
| COMMODITY | 🔴 7d PF=0.246 — futures_momentum block gap identified |

Refs: issues #685 #686 #693 | PRs #1298 (merged)

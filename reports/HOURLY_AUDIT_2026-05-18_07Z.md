# Hourly Audit — 2026-05-18 07Z

**Dashboard snapshot:** `2026-05-18T06:32:45Z` (FRESH — stale alert from 06Z audit resolved)
**Audit run:** `2026-05-18T07:14Z`
**Branch:** `audit/hourly-07z-sonnet`
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-18_06Z.md`
**Refs:** Issue #685 (resolver done), Issue #686 (live attribution), Issue #693 (EQUITY monitor — closed 2026-05-13)

---

## 1. Dashboard Refresh Status

- Dashboard last refreshed: `2026-05-18T06:32:45Z` — **FRESH** (within 45 min of audit run).
- The 06Z audit flagged staleness (>2h, last refresh 04:12Z); the hourly cron fired at ~06:32Z resolving that alert.
- `recent_closed` n=3500 (cap). All metrics below are from the fresh 06:32Z snapshot.
- No stale-data escalation needed.

**PRs merged between 06Z and 07Z cycles:**
- ✅ **PR #1238** (audit/hourly-06z-sonnet — 06Z audit report) — merged 2026-05-18T07:11Z.

---

## 2. Per-Asset PF/WR by Window (07Z — fresh 06:32Z snapshot)

### 24h window (closed after 2026-05-17 06:32Z)

| Class     | n   | WR%  | PF    | Sum PnL% | Delta vs 06Z |
|-----------|-----|------|-------|----------|--------------|
| CRYPTO    | 185 | 49.7 | 1.171 | +23.48   | n −3 / PF −0.030 / WR +1.3pp |
| FOREX     |   7 | 42.9 | 1.218 | +1.17    | PF +0.013 |
| EQUITY    |   — |   —  |   —   |    —     | 0 closes in 24h |
| COMMODITY |   — |   —  |   —   |    —     | 0 closes in 24h |
| ETF       |   — |   —  |   —   |    —     | 0 closes in 24h |
| FUTURES   |   — |   —  |   —   |    —     | 0 closes in 24h |

> CRYPTO 24h PF 1.171 vs documented baseline 3.54: -2.37. Expected post-HYPEUSDT block (#694) removing a high-PF outlier. Monitoring for stabilisation; no new action required.

### 7d window (closed after 2026-05-11 06:32Z)

| Class     | n   | WR%  | PF    | Sum PnL%  | Status |
|-----------|-----|------|-------|-----------|--------|
| CRYPTO    | 775 | 43.7 | 1.143 | +101.29   | 🟡 sub-T2; PF +0.008 vs 06Z |
| EQUITY    |  22 | 13.6 | 0.682 | −10.28    | 🔴 P1 — 5th consecutive identical reading (n, PF, WR all unchanged) |
| FOREX     |  14 | 35.7 | 1.595 | +3.64     | 🟢 recovery +0.011 PF vs 06Z |
| COMMODITY |  17 | 17.6 | 0.445 | −23.19    | 🟡 n<20; 30d still T2 — unchanged |
| ETF       |  13 | 46.2 | 0.656 | −7.14     | 🟡 small n; unchanged |
| FUTURES   |  60 |  8.3 | 0.177 | −133.47   | 🔴 **P1 CATASTROPHIC** — unchanged |

### 30d window (closed after 2026-04-18 06:32Z)

| Class     | n    | WR%  | PF    | Sum PnL%  | Tier / Status |
|-----------|------|------|-------|-----------|---------------|
| CRYPTO    | 2781 | 45.9 | 1.278 | +637.57   | 🟡 sub-T2 (need PF>1.5); +0.003 vs 06Z |
| EQUITY    |   90 | 53.3 | 2.291 | +147.31   | 🟢 T1-candidate; unchanged |
| FOREX     |   47 | 34.0 | 2.388 | +16.95    | 🟡 PF strong / WR<50%; +0.006 vs 06Z |
| COMMODITY |   49 | 59.2 | 2.513 | +86.33    | 🟢 T2 confirmed; unchanged |
| ETF       |   40 | 67.5 | 2.055 | +32.24    | 🟢 T2 (n→100 charter floor); unchanged |
| FUTURES   |  129 |  4.7 | 0.104 | −318.39   | 🔴 **CATASTROPHIC** — n=129 well above deep-dive floor |

---

## 3. Key Deltas vs Documented Baselines (CLAUDE.md / issue #686)

| Metric | Baseline | 06Z | 07Z (current) | Delta 06Z→07Z | Note |
|--------|----------|-----|---------------|----------------|------|
| CRYPTO 24h PF | 3.54 | 1.201 | 1.171 | −0.030 | Window rolling out; HYPEUSDT block (#694) normalising |
| CRYPTO 7d PF | 1.33 | 1.135 | 1.143 | **+0.008** | Marginal improvement as old picks age out |
| CRYPTO 30d PF | 1.33 | 1.275 | 1.278 | **+0.003** | Stable / slight upward trend |
| EQUITY 7d PF | 0.87 | 0.682 | 0.682 | = 0 | Stagnant — goldmine_6x trades not yet aged out |
| EQUITY 30d PF | 1.41–2.18 | 2.291 | 2.291 | = 0 | T1-candidate intact |
| FOREX 7d PF | 0.14 (pre-#687) | 1.584 | 1.595 | **+0.011** | Recovery strengthening |
| FOREX 30d PF | 0.97 (pre-#687) | 2.382 | 2.388 | **+0.006** | Structural improvement confirmed |
| FUTURES 30d PF | (new track) | 0.104 | 0.104 | = 0 | P1 catastrophic — unchanged |

**Summary of directional signals this hour:**
- CRYPTO: sub-T2 but micro-improving on 7d/30d. ✅
- EQUITY 7d: stagnant (5th identical reading); next checkpoint 2026-05-20 per issue #693 plan.
- FOREX: recovery accelerating post-#687. ✅
- FUTURES: catastrophic, unchanged. Deep-dive + 3-AI consensus required before kill.

---

## 4. PR Triage (07Z)

### Open PRs
GitHub `list_pull_requests` → **0 open PRs** after #1238 merged at 07:11Z.

### HOLD set check
- **#660** (Plan v2.1 family): closed (merged 2026-05-03 — pre-dates hold instruction; flagged in prior audits)
- **#658** (Plan v2.1 audit): closed without merge ✅
- **#681** (strategy decay guard): closed without merge ✅
- **#661** (infrastructure v2.0): closed (merged 2026-05-03 — pre-dates hold instruction)

### Author rebase candidates
- **#669, #676, #608, #665, #644, #597, #615**: all closed (merged 2026-05-02/03) ✅
- **#655** (doc-only roadmap): closed without merge ✅

No triage actions required this cycle.

---

## 5. Mutation Analysis (07Z)

**Command:** `python3 tools/mutation_analysis.py`

### 🆕 New Strategy-Level Kill Candidate (PF<0.5 + n≥20)

| Asset Class | Strategy | n | WR% | PF | Action required |
|-------------|----------|---|-----|----|-----------------|
| **FUTURES** | `futures_momentum` | 127 | **3.1%** | **0.056** | Mutation analysis + 3-AI consensus |

`futures_momentum` meets all three CLAUDE.md kill criteria:
- (a) Pattern matches existing kills: yes — consistent with `cta_replicator/NG=F` (WR=0%) and broader FUTURES class catastrophe (30d PF=0.104)
- (b) n≥20: yes (n=127)
- (c) WR<35% sustained: yes (3.1%)

**This is distinct from the previously documented `cta_replicator/NG=F` symbol block candidate.** `futures_momentum` is a strategy-level kill, not a symbol-within-strategy block.

Required per CLAUDE.md before adding `("FUTURES", "futures_momentum")` to `BLOCKED_ASSET_STRATEGY_PAIRS`:
1. Export closed CSV → `python tools/mutation_analysis.py`
2. Run Axis-1 (direction flip), Axis-2 (timeframe), Axis-3 (symbol rotation) mutations
3. **3+ AI consensus** — do NOT auto-kill

Posting to issue #686 this cycle.

### Continuing Axis-1 Direction-Asymmetry Candidates (awaiting 3-AI consensus — no change)

| Strategy | Dir | n | WR% | Opposite WR% | Action |
|----------|-----|---|-----|--------------|--------|
| `ig_contrarian_sentiment` | LONG | 197 | 16.8% | SHORT: 61.4% | LONG block after consensus |
| `myfxbook_retail_contrarian` | LONG | 123 | 13.8% | SHORT: 50.0% | LONG block after consensus |
| `forex_rsi2_mean_reversion` | LONG | 108 | 7.4% | SHORT: 34.8% | LONG block after consensus |
| `quan_engine_swing` | LONG | 104 | 26.0% | SHORT: 60.0% | LONG block after consensus |
| `cta_cross_asset_tsmom` | LONG | 84 | 29.8% | SHORT: 52.1% | LONG block after consensus |

### Continuing Axis-3 Symbol-Block Candidates (awaiting 3-AI consensus — no change)

| System | Symbol | WR% | n | Status |
|--------|--------|-----|---|--------|
| `cta_replicator` | NG=F | 0.0% | 24 | Documented since 08Z 2026-05-17 |
| `rapid_fire` | UUSDT | 0.0% | 34 | Documented since 10Z 2026-05-17 |
| `cta_replicator` | CL=F | 19.1% | 47 | Sub-floor; monitor |

---

## 6. Issue #693 Checkpoint (EQUITY 7d monitor)

Issue #693 was closed 2026-05-13 as "completed" after PR #692 killed goldmine_6x_consensus. The monitor protocol (issue #693 §Recommended action) states:
- If EQUITY 14d returns to PF≥1.5 within 7 days post-#692 → deterioration was concentrated in goldmine_6x ✅
- If EQUITY 14d remains <1.0 for 14 days → escalate to root-cause review

Current EQUITY 7d PF=0.682 (stagnant for 5 audits). EQUITY 30d PF=2.291 (T1-candidate, healthy). The 14d window is not directly computable from `recent_closed` alone but the 30d trend is positive. Next formal checkpoint: **2026-05-20** (14 days post-PR-#692 merge 2026-05-06).

**stocksunify2_* zero-pnl masking (ongoing):** 11/22 EQUITY 7d picks have pnl=0, counted as losses. Adjusted 7d WR excl zero-pnl: ~27.3%. Operational resolver sweep needs operator go-ahead (issue #685 §1).

---

## 7. Today's Merged PRs Summary (full session, up to 07Z)

PRs merged today per session brief:
- ✅ #684 (48h review)
- ✅ #674 (B11 ETF)
- ✅ #673 (B14 stress)
- ✅ #664 (audit credibility)
- ✅ #683 (cftc_cot kill)
- ✅ #687 (P0 JPY-cross BUY rule fix)
- ✅ #692 (kill forex_carry_momentum + goldmine_6x_consensus)
- ✅ #694 (quan_engine HYPEUSDT symbol-block)

PRs merged this audit cycle:
- ✅ #1238 (06Z audit report) — merged 07:11Z

**Total merged PRs this audit cycle: 1 (#1238)**

---

## 8. Actions Taken This Cycle

1. **Dashboard freshness**: confirmed REFRESHED (06:32Z). Stale alert from 06Z audit resolved. ✅
2. **PR triage**: 0 open PRs — no merge actions required.
3. **HOLD set**: all closed pre-hold; no intervention possible.
4. **Rebase candidates**: all already merged/closed.
5. **Mutation analysis**: identified new strategy-level kill candidate `futures_momentum` [FUTURES] (PF=0.056, n=127, WR=3.1%). Posted to issue #686. **Not auto-killed** (3-AI consensus required).
6. **Report committed** to branch `audit/hourly-07z-sonnet`.

---

## 9. Next Cycle Priorities (08Z)

1. Monitor EQUITY 7d — if still PF<0.7/WR<20% with same n=22, flag for operator (stocksunify2_* resolver sweep).
2. Watch FUTURES 30d — if PF still <0.15 and no 3-AI consensus on `futures_momentum` kill, draft `reports/deep_dive_futures_*.md`.
3. Monitor CRYPTO 24h PF trend — baseline normalisation from HYPEUSDT block should stabilise within next 24–48h.
4. 3-AI consensus needed on: `ig_contrarian_sentiment` LONG block, `myfxbook_retail_contrarian` LONG block, `cta_replicator/NG=F` symbol block, `rapid_fire/UUSDT` symbol block, **`futures_momentum` [FUTURES] strategy kill**.

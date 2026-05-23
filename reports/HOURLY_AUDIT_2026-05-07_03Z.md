# Hourly Audit — 2026-05-07 03Z

**Dashboard snapshot:** 2026-05-07T02:36Z (fresh)  
**Analysis timestamp:** ~2026-05-07T03:30Z  
**Session:** claude-sonnet-4-6

---

## 1. Dashboard Refresh Status

Dashboard data confirmed fresh: `meta` = `2026-05-07T02:36:20.372715+00:00`. No stale data.  
`recent_closed` picks: n=3500 (cap).

---

## 2. Per-Asset Metrics with Deltas

Baselines from task spec: CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87 / 30d 1.41–2.18; FOREX 7d 0.14 / 30d 0.97 pre-#687.  
Per-window numbers computed from `picks.recent_closed` using `closed_at` timestamps.

### CRYPTO

| Window | n | WR | PF | Sum PnL% | Delta vs baseline |
|--------|---|----|----|----------|-------------------|
| 24h | 214 | 45.8% | 1.46 | +95.2% | −2.08 vs 3.54 (baseline regression: older 24h spike not repeating) |
| 7d | 731 | 52.3% | 1.70 | +368.1% | **+0.37** vs 1.33 ✅ |
| 30d | 1499 | 44.3% | 1.37 | +355.2% | +0.04 vs 1.33 ✅ |

**Assessment:** 7d and 30d continue improving. 24h PF drop from the 3.54 spike is expected mean-reversion, not a regression signal (24h n=214 is a meaningful sample). CRYPTO 7d now T2-floor (PF≥1.5, WR≥52%). Do not destabilize.  
`asset_class_health` (long-run): PF=1.33.

### EQUITY

| Window | n | WR | PF | Sum PnL% | Delta vs baseline |
|--------|---|----|----|----------|-------------------|
| 24h | 13 | 69.2% | 4.48 | +71.9% | — (small n) |
| 7d | 25 | 68.0% | 3.60 | +100.0% | **+2.73** vs 0.87 ✅✅ |
| 30d | 140 | 63.6% | 3.10 | +318.9% | **+0.92** vs 2.18 ✅ |

**Assessment:** Issue #693 hypothesis fully validated — EQUITY 7d deterioration was entirely concentrated in `goldmine_6x_consensus` (killed in PR #692). Post-kill: 7d PF=3.60, 30d PF=3.10, WR≥63% across all windows → **Tier-1 candidate solidified**. Recommend closing issue #693 as resolved.  
`asset_class_health` (long-run): PF=1.51, WR=53.4%.

### FOREX

| Window | n | WR | PF | Sum PnL% | Delta vs baseline |
|--------|---|----|----|----------|-------------------|
| 24h | 74 | 41.9% | 0.52 | −5.2% | — |
| 7d | 179 | 30.7% | 0.48 | −28.2% | **+0.34** vs 0.14 pre-#687 |
| 30d | 622 | 44.4% | 0.61 | −25.3% | −0.36 vs 0.97 pre-#687 |

**Assessment:** JPY-cross BUY fix (#687) improved 7d PF from 0.14→0.48 (+0.34). Still deeply sub-floor across all windows. Mutation-3-axis protocol must continue per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. Issue #686 direction-split candidates (`ig_contrarian_sentiment` LONG 15.3% vs SHORT 57.1%; `myfxbook_retail_contrarian` LONG 10.2% vs SHORT 46.2%) are the next priority. Do NOT silently kill FOREX class.  
`asset_class_health` (long-run): PF=0.29, WR=45.5%.

### COMMODITY 🚨

| Window | n | WR | PF | Sum PnL% | Note |
|--------|---|----|----|----------|------|
| 24h | 70 | 40.0% | 0.31 | −35.5% | **CRITICAL — see below** |
| 7d | 95 | 43.2% | 0.99 | −0.8% | Near break-even |
| 30d | 560 | 41.4% | 0.85 | −23.1% | Sub-floor |

**24h COMMODITY strategy attribution:**

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `futures_momentum` | 23 | **0%** | 0.00 | **−42.4%** |
| `combined_confidence` | 4 | 50% | 0.01 | −6.3% |
| `cot_positioning` | 9 | 22% | 0.40 | −0.1% |
| `cftc_cot_commercial_signal` | 28 | **79%** | 7.44 | **+13.3%** |
| others | 6 | mixed | — | −0.1% |

**Finding:** `futures_momentum` accounts for 100% of 24h COMMODITY loss (−42.4%). WR=0% on n=23 in 24h alone. Issue #685 explicitly named this as "Strategy kill (gated on #1): futures_momentum... then BLOCKED_ASSET_STRATEGY_PAIRS add (\"COMMODITY\",\"futures_momentum\")". Sample now exceeds n=20 threshold. **3-AI consensus required before kill per CLAUDE.md.** Filed to issue #686.

`cftc_cot_commercial_signal` is the positive COMMODITY signal (PF=7.44, WR=79%) — preserve it.  
`asset_class_health` (long-run): PF=2.05 — divergence from recent data confirms older trades masking a real recent degradation.

### ETF

| Window | n | WR | PF | Sum PnL% | Note |
|--------|---|----|----|----------|------|
| 24h | 9 | 100% | inf | +17.9% | n<20, interpret with caution |
| 7d | 14 | 92.9% | 26.69 | +25.7% | n<20 |
| 30d | 45 | 80.0% | 4.68 | +71.7% | Positive signal |

**Assessment:** ETF 30d data (n=45, PF=4.68) is the strongest per-window number in the system. n approaching 100 charter floor. Monitor — do not modify.  
`asset_class_health` (long-run): PF=1.39, WR=58.3%.

### BOND

No recent picks in 24h/7d/30d windows (n=0 all windows). Long-run n=18 remains below charter floor.  
`asset_class_health` (long-run): PF=1.72, WR=55.6%. Monitoring only.

---

## 3. PR Triage

Open PRs at audit time: #855, #854, #849, #846.  
HOLD set (never merge): #660, #658, #681, #661 — not in open list (confirmed closed/merged or absent).

| PR | Title | CI | mergeable_state | REQUEST_CHANGES | Decision |
|----|-------|----|-----------------|-----------------|----------|
| #855 | audit(02Z): EQUITY T1 confirmed, COMMODITY concern | scan ✅ | unknown | none | HOLD — `unknown` ≠ MERGEABLE; peer session's branch |
| #854 | chore: remove freebuff + DB spec doc | 0 checks | unknown | none | HOLD — no CI, state unknown |
| #849 | Edge action plan + swarm harness | — | — | — | SKIP — DRAFT |
| #846 | feat(B18): Shadow Probation panel | scan✅ drift✅ | **dirty** | PR body: "DO NOT ADMIN-MERGE" | HOLD — conflicts + explicit hold |

**Merges this hour: 0.**

### Author-rebase check (#669 #676 #608 #665 #644 #597 #615 #655)

None appear in open PR list — all confirmed closed/merged (consistent with previous hourly audit #855 finding). No action required.

---

## 4. Mutation Analysis — New Findings

Ran `python tools/mutation_analysis.py --json`.

### 🔴 Kill candidate (NEW): `futures_momentum` × COMMODITY

- **Evidence:** n=23 in 24h alone (n≥20 ✅), WR=0% (WR<35% ✅), sum=−42.4%
- **Pattern match:** existing BLOCKED_ASSET_STRATEGY_PAIRS format ✅
- **Gate:** issue #685 pre-authorized investigation; 3-AI consensus required before add to `BLOCKED_ASSET_STRATEGY_PAIRS` per CLAUDE.md
- **Action:** posted to issue #686; do NOT auto-kill

### 🔴 Kill candidate (PERSISTENT from #855): `rapid_fire` × `UUSDT`

- WR=0%, n=34 — unchanged from previous hour. Still pending 3-AI consensus.

### 🟡 Direction-filter mutations (3-axis analysis needed before action)

| Strategy | LONG WR | SHORT WR | n (LONG) | Spread | Priority |
|----------|---------|----------|----------|--------|----------|
| `ig_contrarian_sentiment` | 15.3% | 57.1% | 157 | 42pp | P1 |
| `myfxbook_retail_contrarian` | 10.2% | 46.2% | 118 | 36pp | P1 |
| `quan_engine_swing` | 26.0% | 60.0% | 104 | 34pp | P2 |
| `cta_cross_asset_tsmom` | 30.8% | 60.7% | 65 | 30pp | P2 |

**Note:** `quan_engine` × HYPEUSDT (41.6% WR, n=553) — HYPEUSDT already blocked in PR #694.

### 🟡 Symbol concentration (multi_asset_copytrader)

SI=F (0% WR), AMD (0%), ZW=F (0%) — candidates for symbol-allowlist mutation in SANDBOX, n<20 each.

---

## 5. Issue Tracker Updates

- **Issue #693** (EQUITY 7d/14d/30d divergence): **Recommend CLOSE** — goldmine_6x_consensus kill (PR #692) fully resolved the deterioration. 7d PF now 3.60 vs baseline 0.87.
- **Issue #686**: New finding posted — `futures_momentum` × COMMODITY kill candidate evidence.
- **Issue #685**: No new resolver-rescope work needed. Status unchanged.

---

## 6. Summary

| Class | 7d PF | 7d WR | Status | Action |
|-------|-------|-------|--------|--------|
| EQUITY | 3.60 | 68.0% | ✅ T1 confirmed | Monitor only |
| ETF | 26.69* | 92.9%* | ✅ Strong (n<20) | Monitor |
| CRYPTO | 1.70 | 52.3% | ✅ T2 floor reached | Monitor |
| BOND | — | — | n<20 | Monitor |
| COMMODITY | 0.99 | 43.2% | 🚨 futures_momentum killing 24h | 3-AI kill vote for futures_momentum |
| FOREX | 0.48 | 30.7% | 🚨 Sub-floor | Mutation-3-axis continues |

**Merges:** 0  
**New findings:** 2 (futures_momentum×COMMODITY kill candidate; direction-split mutations confirmed persistent)  
**Author-rebase PRs:** all confirmed closed  
**Hold set:** intact, not touched

*n<20 in 7d for ETF — interpret with caution.

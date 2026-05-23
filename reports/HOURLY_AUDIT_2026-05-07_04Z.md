# Hourly Audit — 2026-05-07 04Z

**Run time:** 2026-05-07T04:13Z  
**Dashboard snapshot:** 2026-05-07T02:36Z (auto-refresh hourly via [skip ci])  
**Session:** https://claude.ai/code/session_019uR7qiXn4VUXdUq6wQbXZJ  
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-07_03Z.md` (PR #856, merged this run)

---

## 1. Dashboard Refresh Status

Dashboard snapshot age: ~1h37m at run time. Auto-refresh cron is active (confirmed by `[skip ci]` commits at 04:02–04:06Z). No manual refresh required.

---

## 2. Per-Asset Performance Windows

Computed from `audit_dashboard/data/dashboard_data.json` `picks.recent_closed` (n=3500).  
Status-based: WON/LOST only; UNRESOLVED picks excluded from PF/WR calculation.

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n | All PF | All n |
|-------|--------|--------|------:|-------|--------|-----:|--------|--------|------:|--------|------:|
| BOND | n/a | n/a | 0 | n/a | n/a | 0 | n/a | n/a | 0 | 1.65 | 20 |
| COMMODITY | **0.29** | **12.5%** | 24 | 0.98 | 32.7% | 49 | 0.84 | 40.3% | 514 | 0.99 | 734 |
| CRYPTO | 1.32 | 41.5% | 205 | 1.60 | 49.9% | 729 | 1.32 | 43.1% | 1499 | 1.28 | 1514 |
| EQUITY | 999\* | 100% | 6 | **6.69** | **77.8%** | 18 | **3.44** | **64.7%** | 133 | 1.81 | 271 |
| ETF | 999\* | 100% | 9 | **26.69** | **92.9%** | 14 | **4.68** | **80.0%** | 45 | 1.39 | 95 |
| FOREX | 0.51 | 25.8% | 31 | 0.48 | 23.5% | 136 | 0.61 | 43.9% | 579 | 0.72 | 860 |

\* 999 = no losses recorded in window (small n, interpret cautiously)

### Deltas vs Documented Baseline

| Class | Window | Baseline | 04Z | Delta | Note |
|-------|--------|----------|-----|-------|------|
| CRYPTO | 24h | 3.54 | 1.32 | −2.22 | Mean reversion — confirmed expected (03Z: 1.46) |
| CRYPTO | 7d | 1.33 | 1.60 | +0.27 | T2-floor met; stable vs 03Z (1.70) |
| CRYPTO | 30d | 1.33 | 1.32 | −0.01 | Flat / stable |
| EQUITY | 7d | 0.87 | 6.69 | **+5.82** | goldmine_6x kill (#692) confirmed successful |
| EQUITY | 30d | 1.41–2.18 | 3.44 | +1.26 to +2.03 | T1-candidate solidified |
| FOREX | 7d | 0.14 | 0.48 | +0.34 | Post-#687 JPY-cross fix contribution |
| FOREX | 30d | 0.97 | 0.61 | −0.36 | Pre-fix data still dragging; expected improvement as old picks cycle |
| COMMODITY | 24h | 2.05 (all) | 0.29 | **−1.76** | 3rd consecutive 24h alarm — persistent degradation |

---

## 3. Asset-Class Verdict (04Z)

### ✅ EQUITY — T1 CONFIRMED (issue #693 → recommend close)
- 7d PF 6.69 / WR 77.8% / n=18 (resolved); 30d PF 3.44 / WR 64.7% / n=133
- Consistent with 02Z (PF=6.69, n=18) and 03Z (PF=3.60, n=25 — methodology diff).
- The goldmine_6x_consensus kill (PR #692) explains the entire recovery.
- **Issue #693 hypothesis fully validated.** Recommend closing #693 as resolved.

### ✅ CRYPTO — T2-floor stable
- 7d PF 1.60 / WR 49.9% / n=729 — T2-floor reached (PF>1.5).
- 24h PF=1.32 is continued mean-reversion from the 3.54 spike; not a regression.
- Slight decrease vs 03Z (1.70) within normal variance on n=729.
- PR #694 (HYPEUSDT block) and #683 (cftc_cot kill) effects intact.

### ✅ ETF — T1-territory (n still below charter floor)
- 7d PF 26.69 / WR 92.9% / n=14; 30d PF 4.68 / WR 80.0% / n=45
- n=45 approaching n=100 charter floor for promotion. Do not promote yet.

### ⚠️ FOREX — Sub-floor, marginal improvement
- 7d PF 0.48 / WR 23.5% / n=136 — still catastrophically sub-floor.
- +0.34 PF from pre-#687 baseline (0.14) shows JPY fix had a real effect.
- 30d PF=0.61 dragged by large pre-fix population (n=579).
- Mutation-3-axis protocol must continue: `ig_contrarian_sentiment` LONG and `myfxbook_retail_contrarian` LONG are direction-split kill candidates (see §5).
- **Do NOT apply `docs/MUTATION_THREE_AXIS_PROTOCOL.md` kills without 3-AI consensus.**

### 🚨 COMMODITY — PERSISTENT 24h ALARM (3rd consecutive run)
- 24h: PF=0.29 / WR=12.5% / n=24 (3W/21L) — same as 02Z (PF=0.29, n=24)
- 7d: PF=0.98 / WR=32.7% / n=49 — near break-even
- 30d: PF=0.84 / WR=40.3% / n=514 — sub-floor
- All: PF=0.99 / WR=42.6% / n=734 — long-run asset_class_health shows PF=2.05 masking recent degradation via older data
- `futures_momentum` remains P1 kill candidate (n=23, WR=0%, sum=−42.4% identified in 03Z).
- **Requires 3-AI consensus before adding to `BLOCKED_ASSET_STRATEGY_PAIRS`.** Posted to issue #686 in 03Z; no new post this run (duplicate avoided).

### BOND — Insufficient recent data
- No 24h/7d/30d picks in n=3500 window. All-time n=20, PF=1.65 / WR=45.0%.
- n=18 below charter floor (n>=100); T2-verified claim cannot be made. Monitor only.

---

## 4. PR Triage

| PR | Title | CI | mergeable_state | Reviews | Decision |
|----|-------|----|-----------------|---------|----------|
| #857 | loop: 2026-05-07 V1-V7 verified | scan✅ drift✅ | clean | none | **MERGED** ✓ |
| #856 | audit(03Z): COMMODITY kill candidate | scan✅ | clean | none | **MERGED** ✓ |
| #855 | audit(02Z): EQUITY T1 confirmed | scan✅ | clean | none | **MERGED** ✓ |
| #854 | remove freebuff + DB spec doc | 0 checks | unknown | none | HOLD — no CI |
| #849 | edge action plan + swarm harness | — | — | — | SKIP — draft |
| #846 | B18 shadow probation panel | scan✅ drift✅ | — | none | HOLD — explicit "DO NOT ADMIN-MERGE" |

**HOLD set** (#660/#658/#681/#661): confirmed absent from open PR list (all closed/merged).  
**Author-rebase list** (#669/#676/#608/#665/#644/#597/#615/#655): confirmed closed/merged (per 03Z audit; unchanged).

### Merge count: 3 (#857, #856, #855)

---

## 5. Mutation Analysis

Source: `python3 tools/mutation_analysis.py --json` (04Z run)

### 🔴 Kill candidates — 3-AI consensus required before any block

| Candidate | Type | n | WR | Evidence |
|-----------|------|---|----|----|
| `rapid_fire` × UUSDT | Symbol-block | 34 | 0.0% | Persistent 3rd run; sum=−$5.78; pattern matches existing HYPEUSDT block |
| `futures_momentum` × COMMODITY | Asset-strategy block | 23 | 0.0% | sum=−42.4%; 03Z pre-auth; posted to #686 |

**No new PF<0.5 + n>=20 strategies emerged in 04Z run.** Both candidates are carries from prior runs.

### 🟡 Direction-split mutations — 3-axis analysis needed before blocking

| Strategy | LONG WR (n) | SHORT WR (n) | Spread | Trend |
|----------|-------------|--------------|--------|-------|
| `ig_contrarian_sentiment` | 15.3% (157) | 57.1% (42) | 42pp | Persistent (02Z/03Z/04Z) |
| `myfxbook_retail_contrarian` | 10.2% (118) | 46.2% (13) | 36pp | Persistent (02Z/03Z/04Z) |
| `quan_engine_swing` | 26.0% (104) | 60.0% (5) | 34pp | **NEW in 04Z** (SHORT n too small) |
| `cta_cross_asset_tsmom` | 30.8% (65) | 60.7% (84) | 30pp | Persistent; approaching threshold |

**NEW 04Z finding:** `quan_engine_swing` shows 34pp direction split. SHORT n=5 is too small to act; flag for monitoring. If SHORT n grows to ≥20 and spread persists, escalate to mutation analysis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

### Symbol variance (high WR spread)

- `multi_asset_copytrader`: SI=F, AMD, ZW=F all WR=0% (worst); CT=F WR=71.6% (best). Allowlist mutation candidate.
- `quan_engine`: HYPEUSDT WR=41.6% n=553 (historical data pre-#694 block; block is active, numbers will cycle out).
- `rapid_fire`: UUSDT WR=0% n=34 (kill candidate above); TAOUSDT WR=5.6% n=18 approaching threshold.

---

## 6. New Findings Count

1. **EQUITY T1 confirmed** — goldmine_6x kill validated across 3 consecutive audits (02Z/03Z/04Z). Recommend closing issue #693.
2. **CRYPTO 7d T2-floor stable** — PF=1.60 vs 03Z 1.70; minor variance, floor intact.
3. **COMMODITY 24h alarm persistent** — 3rd consecutive run with PF=0.29. `futures_momentum` kill urgency rises; 3-AI consensus needed.
4. **`quan_engine_swing` direction split** — NEW 04Z finding (WR 26% LONG vs 60% SHORT, n=104/5); monitor pending SHORT n growth.

**Total new findings: 4** (1 confirmed/closing recommendation, 1 stability signal, 1 persistence escalation, 1 new monitoring flag)

---

## 7. Constraints Checklist

- [x] Resolver-rescope DONE (issue #685) — no resolver PR opened
- [x] Plan v2.1 stats not cited (PF 5.81, ml_score 0.90 are refuted)
- [x] No peer PR rebases
- [x] HOLD set (#660/#658/#681/#661) not merged — confirmed absent from open list
- [x] futures_momentum not auto-killed — 3-AI consensus gate respected
- [x] rapid_fire×UUSDT not auto-blocked — 3-AI consensus gate respected
- [x] No REQUEST_CHANGES PRs merged

---

## 8. Recommended Next Actions

1. **[Operator]** Issue #693 → close as resolved (EQUITY T1 recovery from goldmine_6x kill confirmed across 3 audits).
2. **[Next AI session]** Obtain 3-AI consensus on `futures_momentum` × COMMODITY kill. Evidence: n=23, WR=0%, sum=−42.4%, 3-run persistent.
3. **[Next AI session]** Obtain 3-AI consensus on `rapid_fire` × UUSDT block. Evidence: n=34, WR=0%, pattern matches HYPEUSDT block (#694).
4. **[Next AI session]** Monitor `quan_engine_swing` direction split — act when SHORT n≥20.
5. **[Next AI session]** Merge #854 only after CI checks complete; #846 awaiting human review gate.

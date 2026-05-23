# Hourly Audit — 2026-05-20 08Z

**Generated:** 2026-05-20 ~08:10Z  
**Auditor:** Claude Sonnet 4.6 (claude-code session)  
**Previous audit:** PR #1258 (07Z) — merged ✅ this hour  
**Snapshot:** `audit_dashboard/data/dashboard_data.json` @ 2026-05-20T04:13:12Z  
**Snapshot age at audit time:** ~4h — **STALE** (>120min threshold; 08:15Z cron refresh expected)  
**Note:** No cron refresh landed between 07Z and 08Z. Last commit to dashboard_data.json was 07:34Z (incubator picks only, not dashboard). All windowed metrics same snapshot as 06Z/07Z. 24h window naturally shifted ~1h vs 07Z (older picks fell out).

---

## Issues read

| Issue | Title | Status |
|-------|-------|--------|
| #685 | Resolver-rescope claims obsolete; remaining moves operational/multi-week | Open — no action (resolver work DONE per issue body) |
| #686 | Goal-#1 quality regression: per-asset live-data attribution | Open — active tracking (57 comments, updated 2026-05-20) |
| #693 | EQUITY 7d/14d/30d PF degradation monitor | **Closed** 2026-05-13 — PR #692 goldmine_6x kill resolved |

---

## Task 1 — Per-asset windowed metrics (snapshot 2026-05-20T04:13:12Z)

| Class | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n | Status |
|-------|--------|--------|-------|-------|-------|------|--------|--------|-------|--------|
| CRYPTO | 0.826 | 38.5% | 148 | 1.190 | 45.8% | 1009 | 1.340 | 46.8% | 2789 | 24h regressed vs 07Z 1.004; 7d/30d stable |
| EQUITY | 0.075 | 6.2% | 16 | 0.641 | 28.9% | 45 | 1.446 | 44.9% | 147 | 7d weak; 30d T2 candidate holding |
| FOREX | 1.278 | 42.9% | 7 | 1.272 | 33.3% | 18 | 2.515 | 48.4% | 93 | Post-#687 strong across all windows |
| COMMODITY | 0.000 | 0.0% | 16 | 0.097 | 7.9% | 38 | 0.962 | 42.5% | 73 | All windows sub-1.0 — crisis |
| ETF | 0.000 | 0.0% | 1 | 1.233 | 31.2% | 16 | 1.917 | 56.0% | 50 | Stable; 24h thin (n=1) |
| FUTURES | 0.000 | 0.0% | 0 | 0.000 | 0.0% | 0 | inf | 100.0% | 2 | No 7d activity |

### Deltas vs 07Z (same snapshot — 24h window shift only)

| Class | Metric | 07Z | 08Z | Delta | Note |
|-------|--------|-----|-----|-------|------|
| CRYPTO | 24h PF | 1.004 | 0.826 | -0.178 | 24h window rolled; 25 picks aged out |
| CRYPTO | 7d PF | 1.200 | 1.190 | -0.010 | Minimal (same snapshot) |
| EQUITY | 7d PF | 0.641 | 0.641 | 0 | Unchanged |
| FOREX | 7d PF | 1.272 | 1.272 | 0 | Unchanged |
| COMMODITY | 7d PF | 0.097 | 0.097 | 0 | Unchanged |

### Deltas vs task-brief baselines

| Class | Window | Baseline | 08Z | Delta |
|-------|--------|----------|-----|-------|
| CRYPTO | 24h PF | 3.54 | 0.826 | **-2.714** (window grew 85→148; denominator changed) |
| CRYPTO | 7d PF | 1.33 | 1.190 | -0.140 |
| CRYPTO | 30d PF | 1.33 | 1.340 | +0.010 |
| EQUITY | 7d PF | 0.87 | 0.641 | **-0.229** (goldmine_6x kill not yet reversing 7d) |
| EQUITY | 30d PF | 1.41–2.18 | 1.446 | Holding lower bound |
| FOREX | 7d PF | 0.14 pre-#687 | 1.272 | **+1.132** (+808%) — PR #687 impact confirmed |
| FOREX | 30d PF | 0.97 pre-#687 | 2.515 | **+1.545** (+159%) |
| COMMODITY | 7d PF | n/a | 0.097 | Catastrophic; all strategies sub-PF 0.15 |

---

## Task 2 — PR triage

### Open PRs at time of audit

One open PR found: **#1258** (07Z hourly audit, created 07:21Z).

| PR | Title | CI | Reviews | Action |
|----|-------|----|---------|--------|
| #1258 | audit: 07Z hourly 2026-05-20 — FINDING-24 P0→P1, FINDING-25/26 new | 3/3 ✅ | greptile-apps COMMENTED (bot only) | **MERGED** |

**Merged this hour: #1258**

HOLD set (#660 #658 #681 #661): absent from open PRs ✅  
Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655): absent ✅  
Plan v2.1 fabrication PRs: none citing PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅

---

## Task 3 — Author rebases check

PRs #669, #676, #608, #665, #644, #597, #615, #655 — all absent from open PR list. No action required.

---

## Task 4 — New strategy kills (mutation_analysis.py output)

### Kill candidates meeting full criteria (n≥20, WR<35%, PF<0.5)

| Strategy | Class | 7d n | 7d WR | 7d PF | 7d Sum | Status |
|----------|-------|------|-------|-------|--------|--------|
| `cftc_cot_commercial_signal` | COMMODITY | 20 | 5.0% | 0.113 | -65.79% | FINDING-22 — awaiting 3-AI consensus, no change |

No new candidates cross all three thresholds this hour.

### Borderline watch — FINDING-27 (new)

| Strategy | Class | 7d n | 7d WR | 7d PF | 7d Sum | Notes |
|----------|-------|------|-------|-------|--------|-------|
| `crypto_mtf_ema_slope_alignment_v1` | CRYPTO | 27 | 33.3% | 0.505 | -3.69% | WR<35% ✅, n≥20 ✅, PF=0.505 just above 0.5 floor ❌ |

**Not a kill candidate yet** (PF 0.505 > 0.5 threshold). Monitor: if PF falls below 0.5 on n≥30, promote to FINDING-22-class and request 3-AI consensus.

### Sub-floor watches (unchanged from 07Z)

| Strategy | Class | 7d n | 7d WR | 7d PF | Gap to n=20 floor |
|----------|-------|------|-------|-------|-------------------|
| `futures_momentum` | COMMODITY | 17 | 11.8% | 0.087 | 3 picks |
| `stocks_rsi2_pullback` | EQUITY | 29 | 34.5% | 0.980 | WR above 35% floor by 0.5pp |
| `quan_engine × XRPUSDT` | CRYPTO | 13 | 0.0% | 0.000 | 7 picks below n=20 |
| `quan_engine × DOGEUSDT` | CRYPTO | 12 | 8.3% | — | 8 picks below n=20 |
| `quan_engine × ETCUSDT` | CRYPTO | 5 | 0.0% | 0.000 | 15 picks below n=20 |

### Mutation analysis axis highlights

`tools/mutation_analysis.py` axis 1 (direction split) findings:

| Strategy | SHORT WR | LONG WR | Spread | Action |
|----------|----------|---------|--------|--------|
| `ig_contrarian_sentiment` | 60.3% (n=58) | 16.5% (n=200) | 44pp | LONG-only kill / SHORT-only mutation candidate |
| `myfxbook_retail_contrarian` | 50.0% (n=14) | 13.7% (n=124) | 36pp | Same — LONG side destroying WR |
| `quan_engine_swing` | 60.0% (n=5) | 26.0% (n=104) | 34pp | Direction mutation; n=5 SHORT too small to confirm |
| `cta_cross_asset_tsmom` | 52.0% (n=171) | 29.4% (n=85) | 23pp | LONG side weak |

Symbol-allowlist mutation candidates (axis 3, high symbol variance):

| Source | Worst symbols | Spread |
|--------|--------------|--------|
| `cta_replicator` | NG=F (0% WR n=24), ZC=F (0% WR n=8), AUDUSD=X (8.3%) | 70pp |
| `rapid_fire` | UUSDT (0% WR n=34), TAOUSDT (5.6% WR n=18) | 89pp |
| `alpha_engine (FOREX)` | GBPJPY=X (0% n=5), NZDUSD=X (10% n=10) | 60pp |

These are mutation candidates only; none meet auto-kill criteria. All require full mutation protocol per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

## Task 5 — Document

### FINDING-22 (continuing) — `cftc_cot_commercial_signal × COMMODITY`

- **7d:** n=20, WR 5.0%, PF 0.113, sum -65.79% (unchanged from 07Z — same snapshot)
- Kill criteria fully met: n≥20 ✅, WR<35% ✅, PF<0.5 ✅
- Pattern match: `cftc_cot` (broad) killed PR #683 ✅
- **Status:** awaiting 3-AI consensus (posted to issue #686 at 06Z). No new AI confirmations this hour.
- **Required next step:** DeepSeek/Kilo/Copilot confirmation before adding `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`

### FINDING-24 (P1, unchanged) — `quan_engine × HYPEUSDT` gate bypass

- Gate bypass confirmed at `quality_gates.py:7948` (checks `strategy` not `source_system`)
- Bypassed picks: 7d n=53, WR=45.3%, sum=+25.97% — **net positive**
- Status: P1, awaiting 3-AI reassessment on whether to maintain HYPEUSDT block
- No action this hour

### FINDING-25 (continuing) — `quan_engine × XRPUSDT` and `× DOGEUSDT`

| Symbol | 7d n | 7d WR | 7d Sum | Gap to kill floor |
|--------|------|-------|--------|-------------------|
| XRPUSDT | 13 | 0.0% | -13.46% | 7 picks |
| DOGEUSDT | 12 | 8.3% | -8.70% | 8 picks |
| ETCUSDT | 5 | 0.0% | -5.00% | 15 picks (new, too small) |

Unchanged from 07Z. Monitor at 09Z.

### FINDING-26 (continuing) — `quan_engine × ONDOUSDT` profitable

- 7d: n=44, WR=38.6%, sum=+10.87% (slight decrease from 07Z n=46 as 2 picks aged past 7d window)
- No action; net positive and unblocked

### FINDING-27 (new) — `crypto_mtf_ema_slope_alignment_v1` borderline watch

- 7d: n=27, WR 33.3%, PF 0.505, sum -3.69%
- WR<35% and n≥20 — two of three kill criteria met
- PF 0.505 is 1% above the 0.5 threshold — does NOT yet meet kill floor
- If PF drops below 0.5 on next snapshot: request 3-AI consensus immediately
- Cross-reference: `multi_period_rsi_confluence` (n=13, WR 30.8%) and `multi_period_rsi_confluence_eth` (n=18, WR 50%) — too small for kill

---

## Kill verifications

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | ✅ DEAD (PR #692) |
| `goldmine_6x_consensus` | 0 | ✅ DEAD (PR #692) |
| `cftc_cot` (broad, PR #683) | 0 | ✅ DEAD |
| `forex_rsi2_mean_reversion` | 0 | ✅ DEAD (PR #692) |
| `quan_engine × HYPEUSDT` | 53 | ⚠️ Gate bypass P1, but PF=1.727 (do not re-block without 3-AI) |

---

## COMMODITY crisis summary

All COMMODITY strategies sub-floor in 7d window:

| Strategy | 7d n | WR | PF | Sum |
|----------|------|-----|-----|-----|
| `cftc_cot_commercial_signal` | 20 | 5.0% | 0.113 | -65.79% |
| `futures_momentum` | 17 | 11.8% | 0.087 | -52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | 0.0 | -6.41% |

30d PF = 0.962 (sub-1.0). Until `cftc_cot_commercial_signal` kill lands and `futures_momentum` reaches n=20, COMMODITY remains fully sub-Tier-2. No COMMODITY sizing allowed per `asset_class_health` (`sizing_allowed: false`).

---

## Session context

**PRs merged today (all sessions combined):** #684, #674, #673, #664, #683, #687, #692, #694, #1257, #1258 (10 total)  
**This hour merged:** #1258 (07Z audit)

**Issue #685 constraint:** resolver-rescope work DONE — no resolver PRs opened ✅  
**Plan v2.1 refutation:** no open PRs cite PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅  
**Issue #693:** closed 2026-05-13 ✅

---

## Actions taken this hour

1. Merged PR #1258 (07Z audit) — 3/3 CI green, greptile-apps COMMENTED (bot), no REQUEST_CHANGES ✅
2. Pulled latest from origin/main (fast-forward to bcd2468b, conviction_picks.json update)
3. Computed per-asset 24h/7d/30d PF/WR from dashboard_data.json (04:13Z snapshot)
4. Ran `tools/mutation_analysis.py --json` — 1 existing kill candidate (FINDING-22), no new adds
5. Documented FINDING-27 (crypto_mtf_ema_slope_alignment_v1 borderline watch, PF 0.505)
6. Verified kill list: all 4 killed strategies show 0 7d trades ✅
7. Opened this tracking PR

## Next hour (09Z) priorities

1. Check if dashboard cron refresh landed (08:15Z expected) — re-compute all metrics on fresh snapshot
2. Re-check FINDING-25: XRPUSDT (n=13→target 20) and DOGEUSDT (n=12→target 20)
3. Re-check FINDING-22 for any new AI consensus votes (need 2 more of 3)
4. Re-check FINDING-27: crypto_mtf_ema_slope_alignment_v1 PF — if below 0.5, escalate
5. Monitor COMMODITY futures_momentum for n≥20 threshold
6. Monitor EQUITY stocks_rsi2_pullback WR — if sustained <35% on n≥20, initiate mutation analysis
7. Post FINDING-22 evidence to issue #686 if no prior session has done so at 08Z

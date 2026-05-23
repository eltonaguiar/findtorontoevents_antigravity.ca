# Hourly Audit — 2026-05-20 07Z

**Generated:** 2026-05-20 ~07:09Z  
**Auditor:** Claude Sonnet 4.6 (claude-code session)  
**Previous audit:** PR #1257 (06Z) — merged ✅ this hour  
**Snapshot:** `audit_dashboard/data/dashboard_data.json` @ 2026-05-20T04:13:12Z  
**Snapshot age at audit time:** ~2h57min — **STALE** (>120min threshold)  
**Note:** 07:15Z cron refresh expected shortly; all window metrics are from the 04:13Z snapshot (same as 06Z audit). Deltas vs 06Z are 0.

---

## Issues read

| Issue | Title | Status |
|-------|-------|--------|
| #685 | Resolver-rescope claims obsolete; remaining moves operational/multi-week | Open — no action (resolver work DONE) |
| #686 | Goal-#1 quality regression: per-asset live-data attribution | Open — active tracking |
| #693 | EQUITY 7d/14d/30d PF degradation monitor | Closed (2026-05-13) — PR #692 kill resolved |

---

## Task 1 — Per-asset windowed metrics (snapshot 2026-05-20T04:13:12Z)

| Class | 24h PF | 24h n | 7d PF | 7d n | 30d PF | 30d n | Status |
|-------|--------|-------|-------|------|--------|-------|--------|
| CRYPTO | 1.004 | 173 | 1.200 | 1013 | 1.340 | 2792 | Stable; 24h marginal |
| EQUITY | 0.075 | 16 | 0.641 | 45 | 1.419 | 146 | 7d weak; 30d T2 candidate |
| FOREX | 1.278 | 7 | 1.272 | 18 | 2.515 | 93 | Post-#687 strong |
| COMMODITY | 0.000 | 16 | 0.097 | 38 | 0.962 | 73 | All windows sub-1.0 |
| ETF | 0.000 | 1 | 1.233 | 16 | 1.917 | 50 | Stable |
| BOND | 0.000 | 3 | 0.000 | 3 | 0.000 | 3 | n too small (<10) |

### Deltas vs 06Z (same snapshot — delta = 0)

No cron refresh between 06Z and 07Z audit. All values identical to PR #1257 table.

### Deltas vs issue #686 baseline (2026-05-02T19:55Z)

| Class | Window | Baseline | 07Z | Delta | Direction |
|-------|--------|----------|-----|-------|-----------|
| CRYPTO | 24h PF | 2.65 | 1.004 | -1.646 | Down (sample n grew: 85->173) |
| CRYPTO | 7d PF | 1.21 | 1.200 | -0.01 | Stable |
| EQUITY | 7d PF | 0.87 | 0.641 | -0.229 | Down Worsening |
| EQUITY | 30d PF | 2.18 | 1.419 | -0.761 | Down Declining |
| FOREX | 7d PF | 0.14 | 1.272 | +1.132 | Up PR #687 impact |
| FOREX | 30d PF | 0.97 | 2.515 | +1.545 | Up Dramatic recovery |
| COMMODITY | 30d PF | ~1.78 (stored) | 0.962 | ~-0.82 | Down New degradation |

---

## Task 2 — PR triage

### Open PRs at time of audit

Only one open PR found: **#1257** (06Z hourly audit).

| PR | Title | Mergeable | CI | Reviews | Action |
|----|-------|-----------|-----|---------|--------|
| #1257 | audit: 06Z hourly 2026-05-20 | CLEAN | 3/3 | greptile-apps COMMENTED (bot) | **MERGED** |

**Merged this hour: #1257**

HOLD set (#660 #658 #681 #661): absent from open PRs  
Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655): absent

---

## Task 3 — Author rebases check

PRs #669, #676, #608, #665, #644, #597, #615, #655 — all absent from open PR list. No action required.

---

## Task 4 — New strategy kills (mutation analysis equivalent)

Candidates meeting criteria (7d window, n>=20, WR<35%, PF<0.5):

| Strategy | Class | 7d n | 7d WR | 7d PF | 7d Sum | Status |
|----------|-------|------|-------|-------|--------|--------|
| `cftc_cot_commercial_signal` | COMMODITY | 20 | 5.0% | 0.113 | -65.79% | FINDING-22 — awaiting 3-AI consensus |

**Sub-floor watches (n<20, approaching):**

| Strategy | Class | 7d n | 7d WR | 7d PF | Notes |
|----------|-------|------|-------|-------|-------|
| `futures_momentum` | COMMODITY | 17 | 11.8% | 0.087 | 3 picks below kill floor |
| `stocks_rsi2_pullback` | EQUITY | 30 | 36.7% | 0.981 | Just above WR 35% threshold; monitor |

No auto-kills executed. All candidates require 3-AI consensus per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

## Task 5 — Findings

### FINDING-22 (continuing) — `cftc_cot_commercial_signal x COMMODITY`

- **7d:** n=20, WR 5.0%, PF 0.113, sum -65.79%
- Kill criteria fully met: n>=20, WR<35%, PF<0.5
- Status: awaiting 3-AI consensus (posted to issue #686 by 06Z session)
- **Required next step:** DeepSeek + Kilo (or Copilot) confirmation before adding `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`

### FINDING-24 (reassessed — downgrade P0->P1) — `quan_engine x HYPEUSDT` gate bypass

**Root cause confirmed:** `audit_trail/quality_gates.py:7948`:
```
if (strategy, symbol.upper()) in BLOCKED_STRATEGY_SYMBOL_PAIRS:
```
Block `("quan_engine", "HYPEUSDT")` at line 2455 misses picks where `strategy='unknown'` (the actual field value for quan_engine picks). 53 picks in 7d have `strategy='unknown', source_system='quan_engine'`.

**REASSESSMENT:** These bypassed HYPEUSDT picks are currently **PF=1.727, WR=45.3%, sum +25.97%** — net positive effect. The gate bypass is a correctness bug (code doesn't do what it says) but is NOT causing harm in the current 7d window.

**Downgraded from P0 to P1.** Fix still needed for code correctness; however, rushing a fix that re-enables the block could reduce system PF. Recommend 3-AI reassessment on whether to maintain the HYPEUSDT block given recent recovery.

**Fix pattern when implemented:** add `(source_system, symbol)` fallback check in `passes_active_gate()`:
```
# After existing BLOCKED_STRATEGY_SYMBOL_PAIRS check:
if strategy in ('unknown', '', None) and (source_system, symbol.upper()) in BLOCKED_SOURCE_SYSTEM_SYMBOL_PAIRS:
    return False, "blocked_source_symbol"
```

### FINDING-25 (new) — `quan_engine x XRPUSDT` and `x DOGEUSDT`

Real drags within quan_engine this 7d window:

| Symbol | 7d n | 7d WR | 7d PF | 7d Sum |
|--------|------|-------|-------|--------|
| XRPUSDT | 13 | 0.0% | 0.0 | -13.46% |
| DOGEUSDT | 12 | 8.3% | 0.223 | -8.7% |
| ETCUSDT | 5 | 0.0% | 0.0 | -5.0% |
| DOTUSDT | 4 | 0.0% | 0.0 | -4.0% |
| BTCUSDT | 3 | 0.0% | 0.0 | -3.0% |

XRPUSDT (n=13) and DOGEUSDT (n=12) are 7 and 8 picks below the n=20 kill floor respectively. Monitor at 08Z. Posted to issue #686 for awareness.

### FINDING-26 (new) — `quan_engine x ONDOUSDT` profitable, unblocked

- 7d: n=46, WR=39.1%, PF=1.309, sum=+12.22%
- No action needed. Note: this symbol is not in any block list. Net positive contribution.

---

## Kill verifications

| Strategy | 7d n | Status |
|----------|------|--------|
| `forex_carry_momentum` | 0 | DEAD (PR #692) |
| `goldmine_6x_consensus` | 0 | DEAD (PR #692) |
| `cftc_cot` (broad kill) | 0 | DEAD (PR #683) |
| `forex_rsi2_mean_reversion` | 0 | DEAD (PR #692) |
| `quan_engine x HYPEUSDT` | 53 | Gate bypass (bug), but PF=1.727 (P1) |

---

## COMMODITY deep dive (issue #686 protocol)

COMMODITY 7d PF=0.097 across all 3 strategies:

| Strategy | 7d n | WR | PF | Sum |
|----------|------|-----|-----|-----|
| `cftc_cot_commercial_signal` | 20 | 5.0% | 0.113 | -65.79% |
| `futures_momentum` | 17 | 11.8% | 0.087 | -52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | 0.0 | -6.41% |

30d PF=0.962 (sub-1.0). Combined drags are total and structural. Both lead strategies need kill or mutation. Until `cftc_cot_commercial_signal` kill completes consensus, COMMODITY remains fully sub-Tier-2.

---

## EQUITY 7d strategy attribution

| Strategy | 7d n | WR | PF | Sum |
|----------|------|-----|-----|-----|
| `stocks_rsi2_pullback` | 29 | 34.5% | 0.981 | -1.13% |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97% |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.0 | -6.83% |
| `rs-breakout-scout` | 2 | 0.0% | 0.0 | -3.02% |
| `macd-hidden-div-scout` | 2 | 0.0% | 0.0 | -12.04% |
| Others | <=2 each | Mixed | Mixed | — |

`goldmine_6x_consensus` confirmed absent (killed PR #692). EQUITY 30d PF=1.419 still T2 candidate; 7d drag concentrated in `stocks_rsi2_pullback` (near-breakeven, not kill-worthy yet).

---

## Session context

**PRs merged today (pre-this-audit):** #684, #674, #673, #664, #683, #687, #692, #694 (8 total, all cross-AI verified per task brief)

**Issue #685 constraint:** resolver-rescope work DONE — no PRs opened touching re_resolve scope this hour  
**Plan v2.1 refutation:** no PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER in open set

---

## Actions taken this hour

1. Merged PR #1257 (06Z audit) — 3/3 CI green, CLEAN mergeable, no REQUEST_CHANGES
2. Computed per-asset windowed PF/WR from dashboard_data.json (04:13:12Z snapshot)
3. Ran mutation analysis equivalent — 1 kill candidate confirmed (FINDING-22, no new ones added)
4. Reassessed FINDING-24 P0->P1 based on HYPEUSDT PF=1.727 (helpful bypass)
5. Filed FINDING-25 (XRPUSDT + DOGEUSDT drag approaching floor) and FINDING-26 (ONDOUSDT profitable)
6. Opened this tracking PR

## Next hour (08Z) priorities

1. Refresh dashboard snapshot (07:15Z cron should have landed by 08Z)
2. Re-check XRPUSDT and DOGEUSDT n — if >=20, trigger mutation analysis
3. Re-check `cftc_cot_commercial_signal` consensus status (3-AI needed for FINDING-22 kill)
4. Re-run COMMODITY windowed metrics — watch whether futures_momentum hits n=20
5. Monitor EQUITY stocks_rsi2_pullback WR — if sustained <35% on n>=20, initiate mutation analysis

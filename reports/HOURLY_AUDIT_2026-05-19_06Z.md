# Hourly Audit — 2026-05-19 06Z

**Generated:** 2026-05-19T06:10Z  
**Dashboard snapshot:** 2026-05-19T05:45:31Z (fresh — hourly cron confirmed)  
**recent_closed n:** 3,500  
**Auditor:** Claude Sonnet 4.6 (session 06Z)

---

## §1 — Dashboard Refresh Status

Dashboard generated at 05:45Z — 22 minutes prior to audit start. Hourly cron is healthy.  
recent_closed cap = 3,500 picks. No data staleness issues.

---

## §2 — Per-Asset PF/WR: 24h / 7d / 30d

| Class     | 24h PF | 24h WR | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|-----------|--------|--------|-------|-------|-------|------|--------|--------|-------|
| CRYPTO    | 1.201  | 53.1%  | 262   | 1.026 | 44.0% | 1035 | 1.262  | 46.2%  | 2901  |
| EQUITY    | 0.000  | 0.0%   | 5     | 0.238 | 13.3% | 15   | 1.939  | 50.5%  | 95    |
| FOREX     | 1.274  | 37.5%  | 8     | 1.315 | 31.6% | 19   | 2.543  | 48.4%  | 93    |
| COMMODITY | 0.180  | 25.0%  | 8     | 0.193 | 13.0% | 23   | 1.747  | 54.4%  | 57    |
| ETF       | 1.887  | 11.1%  | 9     | 0.989 | 25.0% | 20   | 2.005  | 57.1%  | 49    |
| FUTURES   | 0.000  | 0.0%   | 1     | 2.774 | 50.0% | 2    | 5.387  | 66.7%  | 3     |

---

## §3 — Deltas vs 05Z Baseline

| Class     | 24h PF Δ | 7d PF Δ | 30d PF Δ | Notes |
|-----------|----------|---------|----------|---------|
| CRYPTO    | +0.045   | +0.001  | -0.002   | Minor 24h uptick; stable |
| EQUITY    | 0        | 0       | 0        | n=5/15 — below significance threshold |
| FOREX     | 0        | 0       | 0        | Recovery holding at 1.315/2.543 |
| COMMODITY | 0        | 0       | 0        | 7d bleed = historical (blocked source) |
| ETF       | 0        | 0       | 0        | Stable |

Data unchanged because dashboard snapshot is the same 05:45Z file (22-min lag). Next snapshot at ~06:45Z will yield fresh deltas.

**Documented baseline comparison (CLAUDE.md / issues #686 / #693):**

| Class  | Window | Baseline | Current | Δ | Status |
|--------|--------|----------|---------|---|--------|
| CRYPTO | 24h    | PF 3.54  | 1.201   | −2.34 | Below baseline — regime normalization |
| CRYPTO | 7d     | PF 1.33  | 1.026   | −0.30 | Slightly below |
| CRYPTO | 30d    | PF 1.33  | 1.262   | −0.07 | Stable |
| EQUITY | 7d     | PF 0.87  | 0.238   | −0.63 | Worse — but n=15 (monitor only, #693) |
| EQUITY | 30d    | PF 1.41–2.18 | 1.939 | within | Tier-2 candidate intact |
| FOREX  | 7d     | PF 0.14 (pre-#687) | 1.315 | +1.18 | Recovery confirmed ✓ |
| FOREX  | 30d    | PF 0.97 (pre-#687) | 2.543 | +1.57 | Recovery confirmed ✓ |

---

## §4 — PR Triage

### Merged this hour
| PR | Title | Action |
|----|-------|--------|
| **#1243** | audit: hourly report 2026-05-19 05Z | Merged (squash) — all 3 CI green, `mergeable_state=clean`, no REQUEST_CHANGES |

### HOLD set (never merge)
PRs #660, #658, #681, #661 — Plan v2.1 fabricated-stats family. **Not in open PR list — confirmed closed/not present.** No action required.

### Author-rebase watch (#669, #676, #608, #665, #644, #597, #615, #655)
**Not in open PR list.** All previously merged or closed. No action required this hour.

### Open PRs after merge
**0 open PRs.**

---

## §5 — Mutation Analysis (full run)

Command: `python3 tools/mutation_analysis.py --json`

### §5.1 — Axis 1: Directional WR spread (≥20pp = direction-block candidate)

| Strategy | SHORT WR | LONG WR | Spread | n (LONG) | Status |
|----------|----------|---------|--------|----------|--------|
| `combined_confidence` | 55.6% | 8.3% | **47pp** | 12 | NEW — n barely ≥20 (21 total); direction block candidate |
| `ig_contrarian_sentiment` | 60.3% | 16.5% | **44pp** | 200 | Carried from 05Z FINDING-2; posted to #686 |
| `myfxbook_retail_contrarian` | 50.0% | 13.7% | **36pp** | 124 | NEW — large n (138 total); direction block candidate |
| `quan_engine_swing` | 60.0% | 26.0% | **34pp** | 104 | NEW — solid n (109 total); direction block candidate |
| `forex_rsi2_mean_reversion` | 34.8% | 6.8% | **28pp** | 117 | Carried; posted to #686 |
| `cta_cross_asset_tsmom` | 53.0% | 29.4% | **24pp** | 85 | NEW — n=253 total |

### §5.2 — Axis 3: Symbol variance (worst symbols per strategy)

Notable worst symbols:
- `rapid_fire` / UUSDT: 0% WR, n=34 — symbol-level kill candidate  
- `rapid_fire` / TAOUSDT: 5.6% WR, n=18 — near threshold  
- `rapid_fire` / ESPUSDT: 0% WR, n=5 — below n-gate  
- `cta_replicator` / NG=F: 0% WR, n=24 — symbol kill candidate  
- `cta_replicator` / ZC=F: 0% WR, n=8 — below n-gate  
- `quan_engine` / HYPEUSDT: 41.6% WR, n=553 — already symbol-blocked (PR #694)

### §5.3 — Aggregate PF<0.5 kills (n≥20)

**None.** No strategies meet PF<0.5 + n≥20 at aggregate level. Kill criteria not triggered.

Lowest-PF strategies (n≥20):
- `ema_momentum_m006`: n=32, PF=0.822, WR=46.9%
- `keltner_compression_expansion_eth_v1`: n=36, PF=0.907, WR=33.3%
- `strong consensus (alpha_engine, ml_crypto_pred)`: n=109, PF=0.980, WR=45.9%

None cross the PF<0.5 floor for outright kill.

---

## §6 — New Findings (issue #686 candidates)

### FINDING-3 (NEW — 06Z): `combined_confidence` LONG direction block
- SHORT WR 55.6% (n=9) vs LONG WR 8.3% (n=12); total n=21
- 47pp directional spread is the largest found this hour
- n=21 barely clears the n≥20 gate; confidence is low
- Recommendation: monitor 1 more day for n growth before posting block PR; post to #686 for awareness

### FINDING-4 (NEW — 06Z): `myfxbook_retail_contrarian` LONG direction block
- SHORT WR 50.0% (n=14) vs LONG WR 13.7% (n=124); total n=138
- 36pp spread with solid n — statistically meaningful
- Strategy is contrarian by design; LONG trades may be entering against strong trend
- Recommendation: post to #686 for 3-AI consensus on direction block

### FINDING-5 (NEW — 06Z): `quan_engine_swing` LONG direction block
- SHORT WR 60.0% (n=5) vs LONG WR 26.0% (n=104); total n=109
- 34pp spread; LONG subsample has sufficient n (104)
- Recommendation: post to #686 for 3-AI consensus

### FINDING-6 (NEW — 06Z): `cta_cross_asset_tsmom` directional drift
- SHORT WR 53.0% (n=168) vs LONG WR 29.4% (n=85); 24pp spread
- Larger SHORT sample (168 vs 85); not enough to call a block yet
- Recommendation: monitor — if LONG WR stays <35% at next hourly check, escalate

### FINDING-7 (NEW — 06Z): `rapid_fire` / UUSDT symbol kill candidate
- 0% WR on n=34; sum PnL = −5.78% (estimated from avg -0.17% × 34)
- Meets n≥20 + WR<35% criteria
- Need PF computation for final gate; recommend mutation analysis on this pair
- Does NOT cross the PF<0.5 aggregate gate (strategy-level PF not sub-0.5)

### FINDING-8 (NEW — 06Z): `cta_replicator` / NG=F symbol kill candidate
- 0% WR on n=24; avg PnL −0.03% per trade
- Meets n≥20 + WR<35% criteria
- Recommend posting to #686 for 3-AI consensus on `BLOCKED_STRATEGY_SYMBOL_PAIRS` entry

---

## §7 — Issue #685 / #693 Status

- **#685 (resolver-rescope DONE):** No resolver PRs open. Rule holds. Any PR claiming "widen re-resolve scope" → auto REQUEST_CHANGES.
- **#693 (EQUITY monitor):** Closed 2026-05-13 as completed. EQUITY 7d PF=0.238 (n=15) is still weak but n<20 per protocol. No escalation yet.

---

## §8 — Summary

| Item | Result |
|------|--------|
| Dashboard refresh | ✓ Fresh (05:45Z) |
| PRs merged | 1 (#1243) |
| PRs in HOLD set | 0 open |
| Author-rebase PRs | 0 open |
| New aggregate kills (PF<0.5, n≥20) | 0 |
| New directional findings | 4 (FINDING-3/4/5/6) |
| New symbol findings | 2 (FINDING-7/8) |
| FOREX recovery | Confirmed ✓ (7d PF 1.315, 30d PF 2.543) |
| EQUITY 7d | Weak (0.238) but n=15 — monitor protocol active |

**Next hourly:** dashboard refreshes ~06:45Z. Check CRYPTO 24h trend (currently 1.201, baseline 3.54 gap remains). Confirm FINDING-3 `combined_confidence` n growth before block PR.

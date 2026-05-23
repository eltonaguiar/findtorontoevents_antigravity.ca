# Hourly Audit — 2026-05-22 00Z

**Generated:** 2026-05-22T00:12Z  
**Dashboard snapshot:** `2026-05-21T22:45:32Z` ⚠️ STALE — same snapshot as 23Z audit; dashboard cron has not fired for 00Z yet.  
**Per-asset numbers are identical to 23Z** except for the 24h window (rolling cutoff shifted).

Refs: issues #685 #686 #693

---

## Dashboard Refresh Status

Dashboard cron last ran at 22:45:32Z (2026-05-21). Current wall-clock: 00:12Z (2026-05-22). No new snapshot available. Numbers below are computed from the same `recent_closed` (n=3500) as the 23Z audit. 7d/30d deltas vs 23Z = 0 (same data). 24h window shifted by ~1.5h of wall-clock.

---

## Per-Asset PF/WR — Current Snapshot

### 24h window (since 2026-05-21T00:12Z)

| Class | n | WR | PF | sumPnL% | vs Baseline (3.54/—) |
|-------|---|----|----|---------|----------------------|
| CRYPTO | 176 | 52.3% | **1.798** | +118.73% | −1.742 vs 24h base 3.54 |
| EQUITY | 3 | 33.3% | 0.300 | −2.99% | thin n |
| FOREX | 7 | 42.9% | 1.434 | +2.06% | recovery ✅ |
| COMMODITY | 3 | 33.3% | 1.933 | +10.29% | thin n |
| ETF | 2 | 0.0% | 0.000 | −4.99% | thin n |
| BOND | 1 | 0.0% | 0.000 | −0.84% | thin n |

### 7d window (since 2026-05-15T00:12Z)

| Class | n | WR | PF | sumPnL% | vs Baseline | vs 23Z |
|-------|---|----|----|---------|-------------|--------|
| CRYPTO | 1010 | 48.5% | **1.414** | +353.60% | +0.084 vs 1.33 ✅ | +0.002 |
| EQUITY | 39 | 30.8% | **0.654** | −32.40% | −0.216 vs 0.87 ⚠️ | 0.000 |
| FOREX | 10 | 30.0% | **1.359** | +1.80% | +1.219 vs 0.14 pre-#687 ✅ | 0.000 |
| COMMODITY | 35 | 11.4% | **0.246** | −106.19% | FINDING-59 | 0.000 |
| ETF | 12 | 8.3% | 0.884 | −3.21% | thin/weak | 0.000 |
| BOND | 5 | 0.0% | 0.000 | −3.49% | sub-floor | 0.000 |

### 30d window (since 2026-04-22T00:12Z)

| Class | n | WR | PF | sumPnL% | vs Baseline |
|-------|---|----|----|---------|-------------|
| CRYPTO | 2817 | 45.8% | **1.322** | +762.52% | −0.008 vs 1.33 ✅ |
| EQUITY | 137 | 41.6% | **1.376** | +90.49% | −0.034 vs 1.41 ≈ |
| FOREX | 93 | 48.4% | **2.572** | +30.42% | above pre-#687 0.97 ✅ (n↑) |
| COMMODITY | 79 | 40.5% | **0.943** | −10.19% | sub-T2; PF<1 over 30d ⚠️ |
| ETF | 56 | 58.9% | **2.248** | +58.43% | ≥T2 range ✅ |
| BOND | 5 | 0.0% | 0.000 | −3.49% | n<18 charter floor |
| FUTURES | 2 | 100.0% | inf | +16.89% | n too small |

### asset_class_health (rolling, from `performance.asset_class_health`)

| Class | PF | WR | n |
|-------|----|----|---|
| CRYPTO | 1.355 | 48.2% | 1085 |
| EQUITY | 0.921 | 36.4% | 55 |
| FOREX | 1.368 | 53.5% | 155 |
| COMMODITY | 1.296 | 50.8% | 61 |
| ETF | 11.995 | 50.0% | 2 (tiny) |
| BOND | 0.000 | 0.0% | 7 |
| FUTURES | 0.956 | 16.7% | 12 |

---

## FINDING-63 — EQUITY 7d Deterioration (UNCHANGED, monitoring)

**Status:** Unchanged from 23Z. PF=0.654, WR=30.8%, n=39. Same snapshot.

**Strategy attribution (7d):**

| Strategy | n | WR | sumPnL% | Action |
|----------|---|----|---------| -------|
| stocks_rsi2_pullback | 25 | **40.0%** | **+10.87%** | POSITIVE — not the culprit ✅ |
| rs-breakout-scout | 3 | 0.0% | −8.65% | n<20, monitor |
| vol-contraction-scout | 3 | 0.0% | −10.18% | n<20, monitor |
| stocks_ema_golden_cross | 2 | 0.0% | −6.83% | n<20, monitor |
| adx-trend-scout | 2 | 50.0% | −6.68% | n<20, mixed |
| aroon-trend-scout | 1 | 100.0% | +4.05% | n<20 |
| macd-hidden-div-scout | 1 | 0.0% | −6.68% | n<20, monitor |
| price-accel-scout | 1 | 0.0% | −6.92% | n<20, monitor |
| fibonacci-bounce-scout | 1 | 100.0% | −1.39% | n<20 |

**Key insight vs 23Z:** `stocks_rsi2_pullback` (n=25/26, WR=40.0%) is now the **positive** contributor (+10.87% sumPnL). The 7d EQUITY drag is now sourced from the scout cohort (rs-breakout, vol-contraction, stocks_ema, macd-hidden-div, price-accel) — all with WR=0% on n=1–3. These are below the n<20 kill threshold. The `stocks_rsi2_pullback` mutation gate concern from 23Z is partially relaxed (WR improved from 37.5% → 40.0%). Do not act until n≥50 and WR<40% sustained.

**Action:** Monitor only. Re-check at 01Z when fresh snapshot expected.

---

## FINDING-59 — COMMODITY 7d PF=0.246 (UNCHANGED)

7d PF=0.246, WR=11.4%, n=35. Persistent multi-day finding. 30d PF=0.943 (sub-T2). Awaiting 3-AI consensus per protocol.

---

## FINDING-60/61 — Awaiting 3-AI Consensus (UNCHANGED)

- `cta_replicator`×NG=F: n=24, WR=0% — persists; n≥20 met, PF=0 → trigger condition for consensus collection
- `rapid_fire`×UUSDT: n=34, WR=0% — persists; n≥20 met, PF=0 → trigger condition for consensus collection

Both meet PF<0.5+n≥20. Blocked pending 3-AI consensus per CLAUDE.md constraints. Post to issue #686 for AI review.

---

## Mutation Analysis — No New Kills

`python tools/mutation_analysis.py --json` output (2026-05-22T00:10Z):

**No new strategies with PF<0.5+n≥20.** Closest from last cycle (`claude_ml_conservative_mut` n=20, PF=0.545) — above threshold.

**Persistent direction-flip candidates (Axis 1):**

| Strategy | LONG WR (n) | SHORT WR (n) | Spread | Action |
|----------|-------------|--------------|--------|--------|
| ig_contrarian_sentiment | 16.5% (n=200) | 60.3% (n=58) | 44pp | SHORT-only mutation sandbox |
| myfxbook_retail_contrarian | 13.7% (n=124) | 50.0% (n=14) | 36pp | SHORT-only mutation sandbox |
| quan_engine_swing | 26.0% (n=104) | 60.0% (n=5) | 34pp | Await SHORT n≥20 |
| cta_cross_asset_tsmom | 29.4% (n=85) | 50.0% (n=178) | 21pp | SHORT-only mutation sandbox |

**Axis 3 symbol-variance candidates (unchanged from 23Z):**
- `cta_replicator`: NG=F WR=0% (n=24), ZC=F WR=0% (n=8) — NG=F at kill threshold; ZC=F n<20
- `rapid_fire`: UUSDT WR=0% (n=34), TAOUSDT WR=5.6% (n=18)
- `quan_engine`: MATICUSDT WR=0%, ONDOUSDT WR=22%, SOLUSDT WR=23% — all n<20

**No automated kills this cycle. Findings posted to issue #686.**

---

## PR Triage

### Open PRs (as of 00:10Z)

| PR | Title | CI | Mergeable | REQUEST_CHANGES | Action |
|----|-------|-----|-----------|-----------------|--------|
| #1303 | audit(hourly): 23Z 2026-05-21 | 3/3 ✅ | unknown (computing) | none | AWAIT MERGEABLE |
| #1299 | chore(loop): LOOP_COMPLETE | 3/3 ✅ | unknown (was dirty) | none | AWAIT MERGEABLE |
| #1287 | feat(b10): UEPS KPI panel | test(3.11) ❌ | — | — | HOLD — CI failing |
| #1279 | docs: AGENTS.md correction | n/a (DRAFT) | — | — | HOLD — DRAFT |

**HOLD set (#660 #658 #681 #661):** All closed per 23Z audit ✅  
**Author-rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655):** All merged/closed per 23Z audit ✅  
**Plan v2.1 guardrails:** No new PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅

### Merged this cycle
**None** — #1303 and #1299 both show `mergeable_state=unknown`; CI green but cannot confirm MERGEABLE. No merge action taken per criterion (a).

---

## Summary

| Item | Status |
|------|--------|
| Dashboard refresh | ⚠️ Stale (22:45Z) — same as 23Z |
| CRYPTO 7d PF | 1.414 — above 1.33 baseline ✅ |
| EQUITY 7d PF | 0.654 — sub-T2, FINDING-63; scout cohort drag, not stocks_rsi2_pullback |
| FOREX 7d PF | 1.359 — recovery holding post-#687 ✅ |
| COMMODITY 7d PF | 0.246 — FINDING-59 persists |
| New kills | None |
| PRs merged | 0 (mergeable_state=unknown on eligible PRs) |
| Open findings | FINDING-59 (COMMODITY), FINDING-60 (cta×NG=F), FINDING-61 (rapid_fire×UUSDT), FINDING-63 (EQUITY scout cohort) |

**Priority next cycle (01Z):** Fresh snapshot expected. Re-evaluate EQUITY 7d PF and COMMODITY. Check if #1303 and #1299 transition to MERGEABLE. Collect 2nd AI opinion on FINDING-60/61 per 3-AI consensus protocol.

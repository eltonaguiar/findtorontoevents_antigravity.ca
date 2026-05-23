# Hourly Audit — 17Z 2026-05-20

**Generated:** 2026-05-20T17:10Z  
**Session:** claude-sonnet-4-6 (hourly progress check, 1 of N)  
**Prior audit:** PR #1267 (16Z) merged this hour ✅

---

## 1. Dashboard Refresh Status

| Field | Value |
|-------|-------|
| `generated_at` | `2026-05-20T04:13:12Z` |
| Staleness at 17Z | **13 hours** |
| File mtime | `2026-05-20 17:07 UTC` (file touched by cron but content unchanged) |
| Recent_closed cap | 3500 picks |

Dashboard has **not refreshed** since 04:13Z. The 16Z PR already flagged this as 12h stale. Cron appears to be running (mtime updated) but the generator is not producing a new snapshot. This is the same stale data used for the 16Z audit; per-asset numbers below reflect the same underlying snapshot, with minor differences due to the 1-hour window shift.

---

## 2. Per-Asset Snapshot (17Z window, n=3500 recent_closed)

Baselines: CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33 · EQUITY 7d 0.87 / 30d 1.41 · FOREX 7d 0.14 / 30d 0.97 (pre-#687)

| Class | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR | 7d Δ vs baseline |
|-------|-------|--------|--------|------|-------|-------|-------|--------|--------|------------------|
| CRYPTO | 74 | 0.72 | 33.8% | 937 | 1.23 | 46.9% | 2760 | 1.32 | 46.4% | −0.10 vs 1.33 |
| EQUITY | 10 | 0.15 | 10.0% | 40 | 0.68 | 30.0% | 145 | 1.40 | 44.1% | −0.19 vs 0.87 |
| FOREX | 7 | 1.28 | 42.9% | 17 | 1.31 | 35.3% | 93 | 2.51 | 48.4% | **+1.17** vs 0.14 |
| COMMODITY | 12 | 0.00 | 0.0% | 38 | 0.10 | 7.9% | 73 | 0.96 | 42.5% | 🔴 CRITICAL |
| ETF | 0 | — | — | 16 | 1.23 | 31.2% | 50 | 1.92 | 56.0% | Stable |
| BOND | 0 | — | — | 3 | 0.00 | 0.0% | 3 | 0.00 | 0.0% | Small n |
| FUTURES | 0 | — | — | 0 | — | — | 2 | ∞ | 100.0% | Small n |

### Deltas vs 16Z

Numbers are essentially unchanged — same underlying snapshot (04:13Z). Tiny differences (EQUITY 7d PF 0.66→0.68, WR 29.3%→30.0%) are window-edge effects as 1 hour of picks age out of the 7d window.

---

## 3. Asset-Class Commentary

### 🔴 COMMODITY — CRITICAL (unchanged)

7d strategy breakdown (n=38):

| Strategy | n | WR | Sum PnL% |
|----------|---|----|----------|
| `cftc_cot_commercial_signal` | 20 | 5.0% | −65.79% |
| `futures_momentum` | 17 | 11.8% | −52.81% |
| `futures_bb_mean_reversion` | 1 | 0.0% | −6.41% |

- `cftc_cot_commercial_signal` 7d n=20 is **pre-kill residual** from before PR #683 merged today. New picks blocked. Will flush from 7d window within ~7d.
- `futures_momentum` is NOT killed; still active. All-time n=18, PF=0.09, WR=11.1%. **Two picks from the n=20 kill floor.** Monitor at 18Z.
- 30d PF=0.96 — approaching sub-1.0 as pre-kill picks age through.

**Next action:** If `futures_momentum` reaches n=20 all-time, escalate to issue #686 for 3-AI consensus kill vote.

### 🔴 EQUITY — Sub-floor (persistent)

7d strategy breakdown (n=40):

| Strategy | n | WR | Sum PnL% |
|----------|---|----|----------|
| `stocks_rsi2_pullback` | 26 | 34.6% | −0.13% |
| `vol-contraction-scout` | 3 | 33.3% | +0.97% |
| `stocks_ema_golden_cross` | 2 | 0.0% | −6.83% |
| `rs-breakout-scout` | 2 | 0.0% | −3.02% |
| `adx-trend-scout` | 2 | 50.0% | −5.23% |
| other scouts | 5 | mixed | mixed |

- `goldmine_6x_consensus` 7d n=0 ✅ confirmed dead (PR #692)
- `stocks_rsi2_pullback` all-time n=47, all LONG/BUY (no SHORT picks exist). PF=0.94, WR=36.2%, sum=−5.35%. **Does not trigger kill floor (PF>0.5).** Axis-1 inverse N/A (no direction diversity). WATCH for Axis-3 (symbol-rotation).
- 30d PF=1.40 — still Tier-2 candidate at the 30d window; 7d deterioration concentrated in EQUITY scouts with small n.

### 🟢 FOREX — Recovery holding

- 7d PF 1.31 / 30d PF 2.51. Pre-#687 baseline was 7d PF 0.14 — improvement of +1.17 PF units.
- JPY-cross BUY rule fix (PR #687) holding across both windows.
- Low 7d volume (n=17) — recovery is real but watch for sample-size dilution.

### 🟡 CRYPTO — 24h dip, 7d steady

- 24h PF 0.72 / WR 33.8% — short-term dip from baseline 3.54.
- 7d PF 1.23 / WR 46.9% — marginally below baseline 1.33 but stable.
- Top 7d strategy: `st_fear_greed_contrarian` n=219, PF=3.01, WR=67.1% — healthy anchor.
- `strong consensus (alpha_engine, ml_crypto_pred)` n=112, PF=0.84, WR=36.6% — drag. Watch.
- HYPEUSDT bypass: **53 picks via `unknown` strategy in 7d window** — P0 unresolved post-#694. The symbol-block in #694 targets `quan_engine` routing; picks still entering via `unknown` source route. Needs dedicated symbol-block in unknown-source path.

### 🟡 ETF — Stable

- 7d PF 1.23 / 30d PF 1.92 / 30d WR 56.0%. On track for Tier-2 at n=50 (charter floor n=100). No action.

---

## 4. Kill Verifications (all confirmed alive or dead)

| Strategy | Status | Evidence |
|----------|--------|----------|
| `forex_carry_momentum` | ✅ DEAD — 7d n=0 | PR #692 |
| `goldmine_6x_consensus` | ✅ DEAD — 7d n=0 | PR #692 |
| `cftc_cot` | ✅ DEAD — 7d n=0 | PR #683 |
| `forex_rsi2_mean_reversion` | ✅ DEAD — 7d n=0 | PR #692 |
| `cftc_cot_commercial_signal` | ⏳ 7d n=20 PRE-KILL RESIDUAL — will flush | PR #683 |

---

## 5. Finding Register (17Z)

| Finding | Status | Evidence | Action |
|---------|--------|----------|--------|
| FINDING-22 `cftc_cot_commercial_signal` | ⬇️ Anomaly, not kill | All-time WR=54.7% n=53 contradicts 7d catastrophe | Residual flushing; re-evaluate at 7d post-kill |
| FINDING-24 HYPEUSDT bypass | 🔴 P0 OPEN | 53 picks via `unknown` in 7d post-#694 | Need symbol-block in `unknown` path |
| FINDING-31 `rapid_fire × UUSDT` | 1/3 consensus | n=34, WR=0% (mutation_analysis) | Needs 2nd + 3rd AI consensus |
| FINDING-32 `cta_replicator × NG=F` | 1/3 consensus | n=24, WR=0% (mutation_analysis) | Needs 2nd + 3rd AI consensus |
| FINDING-35 `futures_momentum` | ⚠️ WATCH n=18 | PF=0.09, WR=11.1% — 2 from kill floor | Auto-escalate if n reaches 20 |
| FINDING-36 `stocks_rsi2_pullback` | ⚠️ WATCH | n=47 all-LONG, PF=0.94, WR=36.2% | PF>0.5 — no kill yet; Axis-3 explore |
| **FINDING-37 NEW** `ig_contrarian_sentiment` LONG | 🟡 Direction anomaly | Mutation: LONG n=200 WR=16.5%; recent_closed SHORT n=46 PF=2.62 WR=63% | Axis-1: filter to SHORT-only — strong edge signal |
| **FINDING-38 NEW** `myfxbook_retail_contrarian` LONG | 🟡 Direction anomaly | Mutation: LONG n=124 WR=13.7% | Axis-1: filter to SHORT-only — matches FINDING-37 pattern |
| FINDING-39 `cta_replicator × ZC=F` | Below floor | n=8, WR=0% | n<20 — watch only |

### FINDING-37 detail

`ig_contrarian_sentiment` shows a sharp direction split (from mutation_analysis, full closed_picks dataset):
- SHORT: n=58, WR 60.3%, avg pnl +0.00%
- LONG: n=200, WR 16.5%, avg pnl −0.00%
- Spread: 44pp

Recent_closed (3500 cap) shows only SHORT picks for this strategy (n=46, PF=2.62, WR=63.0%). The LONG picks are in the historical dataset (beyond the 3500 cap). This is a clean Axis-1 candidate: the contrarian-sentiment signal is strong in the SHORT direction (retail crowd is long → market goes down), but the inverse LONG signal (crowd is short → market goes up) fails badly.

**Proposed action:** Add direction filter `direction=SHORT` to `ig_contrarian_sentiment` in the pick generation path, or add `("FOREX", "ig_contrarian_sentiment", "BUY")` to `BLOCKED_STRATEGY_SYMBOL_PAIRS`. Needs 3-AI consensus before acting.

### FINDING-38 detail

`myfxbook_retail_contrarian` mirrors FINDING-37 exactly:
- SHORT: n=14, WR 50.0%
- LONG: n=124, WR 13.7%, avg pnl −0.00%
- Spread: 36pp

Same proposed action: filter to SHORT-only. Both are retail-sentiment contrarian strategies where the edge is in betting against retail longs, not against retail shorts.

---

## 6. mutation_analysis.py Run (17Z)

No new PF<0.5 + n>=20 kill-floor breaches found this hour beyond previously tracked findings.

**Axis-4 (vol-normalization) candidates** from this run — flagged but NOT kill-eligible (need vol-normalization research, not direct kills):
- `quan_engine`: WR=30.4%, n=5896
- `rapid_fire`: WR=29.0%, n=207
- `multi_asset_copytrader`: WR=21.9%, n=1140

---

## 7. PR Triage

**Open PRs at 17Z: 1 (only #1267)**

| PR | Action | Reason |
|----|--------|--------|
| #1267 (16Z audit) | ✅ **MERGED** | [skip ci], only COMMENTED review (greptile), no REQUEST_CHANGES |

HOLD set (#660, #658, #681, #661) — confirmed absent from open PR list ✅  
Author-rebase watch PRs (#669, #676, #608, #665, #644, #597, #615, #655) — confirmed absent from open PR list ✅

**PRs merged today (8 total, pre-session):**
- #684 (48h review), #674 (B11 ETF), #673 (B14 stress), #664 (audit credibility)
- #683 (cftc_cot kill), #687 (P0 JPY-cross BUY fix), #692 (forex_carry_momentum + goldmine_6x kill)
- #694 (quan_engine HYPEUSDT symbol-block — partial; bypass via `unknown` remains)

---

## 8. Next-Hour Actions (18Z)

- [ ] Check if dashboard cron finally produces a fresh snapshot (currently 13h stale)
- [ ] Monitor `futures_momentum` n — if reaches 20, post to issue #686 for kill vote
- [ ] Draft HYPEUSDT `unknown`-path symbol-block PR (P0 — FINDING-24 still open)
- [ ] Post FINDING-37/38 direction-anomaly evidence to issue #686 for 2nd + 3rd AI review
- [ ] If EQUITY 7d PF stays <0.70 at 18Z with n>50, escalate stocks_rsi2_pullback to full mutation suite

---

## References

- Issue #685 (resolver-rescope done — no further resolver PRs)
- Issue #686 (per-asset quality regression — active tracking)
- Issue #693 (EQUITY divergence monitor — closed 2026-05-13)
- PR #683 (cftc_cot kill), #687 (JPY-cross fix), #692 (forex/goldmine kills), #694 (HYPEUSDT partial)
- `reports/HOURLY_AUDIT_16Z_2026-05-20.md` (previous hour)
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`

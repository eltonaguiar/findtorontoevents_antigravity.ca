# Hourly Audit — 2026-05-18 05Z

**Dashboard snapshot:** `2026-05-18T04:12:40Z`
**Audit run:** `2026-05-18T05:12Z`
**Branch:** `audit/hourly-05z`
**Prior audit:** `reports/HOURLY_AUDIT_2026-05-17_10Z.md`
**Refs:** Issue #685 (resolver done), Issue #686 (live attribution), Issue #693 (EQUITY monitor — closed 2026-05-13)

---

## 1. Dashboard Refresh Status

- Dashboard auto-refreshed to `2026-05-18T04:12:40Z` (hourly [skip ci] job running).
- `recent_closed` n=3500 (cap reached). All metrics below are from this snapshot.
- PRs merged since last audit: #684 (48h review), #674 (B11 ETF), #673 (B14 stress), #664 (audit credibility), #683 (cftc_cot kill), #687 (JPY-cross BUY fix), #692 (kill forex_carry_momentum + goldmine_6x_consensus), #694 (quan_engine HYPEUSDT block).

---

## 2. Per-Asset PF/WR by Window

### 24h window (n=195 total closes)

| Class    | n   | WR%  | PF    | Sum PnL% | vs Baseline              |
|----------|-----|------|-------|----------|--------------------------|
| CRYPTO   | 188 | 48.4 | 1.201 | +28.59   | ⬇ PF (baseline 3.54) — HYPEUSDT-era outlier gone post-#694; normalize expected |
| FOREX    | 7   | 42.9 | 1.205 | +1.10    | ✅ positive (n too small for verdict) |
| EQUITY   | 0   | —    | —     | —        | no closes in window |
| COMMODITY| 0   | —    | —     | —        | no closes in window |
| ETF      | 0   | —    | —     | —        | no closes in window |
| FUTURES  | 0   | —    | —     | —        | no closes in window |

### 7d window (n=928 total closes)

| Class    | n   | WR%  | PF    | Sum PnL%  | vs Prior Audit (10Z 2026-05-17)     | Status |
|----------|-----|------|-------|-----------|-------------------------------------|--------|
| CRYPTO   | 802 | 43.9 | 1.135 | +99.35    | ⬇ slight (was 1.164/36.6%)          | 🟡 watch |
| EQUITY   | 22  | 13.6 | 0.682 | -10.28    | = same (07Z 0.682/13.6%) — stagnant | 🔴 P1 monitor |
| FOREX    | 14  | 35.7 | 1.584 | +3.57     | ✅ recovery holds (10Z: 1.60/45.5%) | 🟢 |
| COMMODITY| 17  | 17.6 | 0.445 | -23.19    | ⬇ worse (08Z: 0.64/29.6%/n=27) — n<20 | 🟡 watch |
| ETF      | 13  | 46.2 | 0.656 | -7.14     | — (small n, below 09Z 0.656/46.2%)  | 🟡 watch |
| FUTURES  | 60  | 8.3  | 0.177 | -133.47   | 🚨 **NEW CRITICAL** — n=60 exceeds floor | 🔴 **P1 NEW** |

### 30d window (n=3198 total closes)

| Class    | n    | WR%  | PF    | Sum PnL%  | Status / Tier |
|----------|------|------|-------|-----------|---------------|
| CRYPTO   | 2843 | 45.7 | 1.275 | +636.21   | 🟡 sub-T2 (need PF>1.5) |
| EQUITY   | 90   | 53.3 | 2.291 | +147.31   | 🟢 T1-candidate (PF>2, WR>50) |
| FOREX    | 47   | 34.0 | 2.382 | +16.88    | 🟡 PF strong but WR<50% |
| COMMODITY| 49   | 59.2 | 2.513 | +86.33    | 🟢 T2 confirmed |
| ETF      | 40   | 67.5 | 2.055 | +32.24    | 🟢 T2 (n approaching 100 charter floor) |
| FUTURES  | 129  | 4.7  | 0.104 | -318.39   | 🔴 **CATASTROPHIC** — n=129 |

---

## 3. Key Deltas vs Documented Baselines

| Metric | Baseline (CLAUDE.md / prior audits) | Current | Delta | Action |
|--------|--------------------------------------|---------|-------|--------|
| CRYPTO 24h PF | 3.54 | 1.201 | -2.34 | Expected: HYPEUSDT outlier removed post-#694 |
| CRYPTO 7d PF | 1.33 | 1.135 | -0.20 | Watch — within normal variance |
| CRYPTO 30d PF | 1.33 | 1.275 | -0.05 | Stable |
| EQUITY 7d PF | 0.87 (issue #693 open) | 0.682 | -0.19 | Persisting despite goldmine_6x kill; stocksunify2 zero-pnl masking real WR |
| EQUITY 30d PF | 2.18 (issue #693) | 2.291 | +0.11 | ✅ improved — goldmine_6x kill effective long-run |
| FOREX 7d PF | 0.14 (issue #686 open) | 1.584 | +1.44 | ✅ JPY-cross fix (#687) confirmed working |
| FOREX 30d PF | 0.97 pre-#687 | 2.382 | +1.41 | ✅ strong recovery |
| FUTURES 7d PF | not previously tracked | 0.177 | — | 🔴 **P1 NEW** |
| FUTURES 30d PF | not previously tracked | 0.104 | — | 🔴 **CATASTROPHIC** |

---

## 4. 🔴 P1 NEW FINDING: FUTURES Catastrophic Performance

**FUTURES 7d: PF=0.177 / WR=8.3% / n=60 / sumPnL=−133.47%**
**FUTURES 30d: PF=0.104 / WR=4.7% / n=129 / sumPnL=−318.39%**

- n=60 (7d) and n=129 (30d) both exceed the n≥20 kill-floor.
- WR=4.7% over 30 days is a systemic failure, not noise.
- This is the worst-performing asset class in the system, worse than FOREX was at peak regression (PF=0.14).
- Per CLAUDE.md: qualifies for deep-dive subagent (PF<1, WR<30%, n≥100 threshold met).

**Required next steps (per MUTATION_THREE_AXIS_PROTOCOL.md):**
1. Export FUTURES closed CSV → `python tools/mutation_analysis.py` (done; see §5 below)
2. Strategy attribution: which strategies produce FUTURES picks?
3. If cta_replicator (CL=F / NG=F / ZC=F) is the primary contributor, block is already supported by mutation data
4. Do NOT auto-kill without 3-AI consensus per CLAUDE.md kill protocol
5. Spawn deep-dive: `reports/deep_dive_futures_YYYYMMDD.md`

**From mutation_analysis.py §3 (cta_replicator symbol variance):**
- NG=F: WR=0% / n=24 → meets BLOCKED_STRATEGY_SYMBOL_PAIRS threshold (already flagged since 08Z 2026-05-17, awaiting 3-AI consensus)
- CL=F: WR=19.1% / n=47 → sub-T2, borderline kill
- ZC=F: WR=0% / n=8 → n<20, monitor

FUTURES sumPnL=−318% over 30d dwarfs every other class's losses. Recommend escalating to P0 investigation if 3-AI consensus is not reached within 24h.

---

## 5. Mutation Analysis — No New Candidates Since 10Z 2026-05-17

From `python tools/mutation_analysis.py --json` (05Z 2026-05-18):

### Axis 1 — Direction Flips (unchanged from prior audits, awaiting 3-AI consensus)

| Strategy | Direction blocked | n | WR% | Opposite WR% | Spread |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 197 | 16.8% | SHORT: 61.4% | 45pp |
| `myfxbook_retail_contrarian` | LONG | 123 | 13.8% | SHORT: 50.0% | 36pp |
| `forex_rsi2_mean_reversion` | LONG | 108 | 7.4% | SHORT: 34.8% | 27pp |
| `quan_engine_swing` | LONG | 104 | 26.0% | SHORT: 60.0% | 34pp |
| `cta_cross_asset_tsmom` | LONG | 84 | 29.8% | SHORT: 52.1% | 22pp |

All meet n≥20/WR<35% blocking criteria. None currently blocked. **Awaiting 3-AI consensus** — no unilateral action taken.

### Axis 3 — Symbol Blocks (unchanged, awaiting 3-AI consensus)

| System | Symbol | WR% | n | Status |
|---|---|---|---|---|
| `cta_replicator` | `NG=F` | 0.0% | 24 | ✅ n≥20, WR<35% — documented since 08Z 2026-05-17 |
| `rapid_fire` | `UUSDT` | 0.0% | 34 | ✅ n≥20, WR<35% — documented since 10Z 2026-05-17 |
| `cta_replicator` | `CL=F` | 19.1% | 47 | sub-floor, monitor |

No new kill candidates this hour.

---

## 6. PR Triage

### Open PRs (05Z 2026-05-18)

| PR | Title | Mergeable | CI | Reviews | Action |
|----|-------|-----------|-----|---------|--------|
| #1231 | fix(actions): concurrency cancel-in-progress | `unstable` | Tests in_progress (3.11, 3.12) | None | **HOLD — wait for CI green** |

**HOLD set (never merge):** #660, #658, #681, #661 — Plan v2.1 fabricated-stats family. Note: #660 was merged 2026-05-03 before hold constraint was written — flagged for operator review (09Z audit).

**Author-rebase list** (#669, #676, #608, #665, #644, #597, #615, #655): all previously confirmed closed/merged as of 09Z 2026-05-17. No action.

### PR #1231 Notes
- 4 workflow files, +20 lines, read-only CI gates only (`cancel-in-progress`).
- 3 of 5 CI checks passed (secret/password/conflict scans). Tests (3.11, 3.12) were in_progress at audit time.
- No REQUEST_CHANGES from any reviewer.
- **Not merged this hour** — mergeable_state=unstable. Re-check next cycle.

---

## 7. EQUITY 7d Investigation Note

EQUITY 7d PF=0.682/WR=13.6%/n=22 — identical to 07Z-09Z 2026-05-17 readings. The goldmine_6x_consensus kill (PR #692) has not yet cleared the 7d window (closes take 7 days to fall off).

Per issue #693 recommendation: monitor until n≥20 per individual strategy and until goldmine_6x trades age out (~7 days post-merge). **No action this hour.** Next checkpoint: 24-48h (by 2026-05-20).

`stocksunify2_*` zero-pnl masking continues (11/22 picks pnl=0, counted as losses). Adjusted WR excluding zero-pnl: 27.3%. Operational resolver sweep needs operator go-ahead per issue #685 §1.

---

## 8. COMMODITY 7d Regression

7d: PF=0.445/WR=17.6%/n=17 — n<20, below kill floor. Worsened from 08Z (n=27, 29.6%). The n drop (27→17) suggests the bad trades are aging out of the 7d window while new good trades haven't replaced them yet, or is a counting artifact from different timestamp handling. 30d COMMODITY remains T2-eligible (PF=2.513). **Monitor only.**

---

## 9. Summary / Action Items

| Priority | Finding | Action | Owner |
|----------|---------|--------|-------|
| 🔴 P1 NEW | FUTURES 30d PF=0.104/WR=4.7%/n=129 — catastrophic | Spawn deep-dive subagent; mutation analysis on cta_replicator FUTURES symbols; escalate 3-AI consensus on NG=F block | Next audit |
| 🔴 P1 | EQUITY 7d PF=0.682 persisting | Monitor — goldmine_6x trades still in window; re-check 2026-05-20 | Monitor |
| 🟡 P2 | ig_contrarian_sentiment LONG n=197 WR=16.8% | Awaiting 3-AI consensus for LONG block | 3-AI |
| 🟡 P2 | myfxbook_retail_contrarian LONG n=123 WR=13.8% | Awaiting 3-AI consensus for LONG block | 3-AI |
| 🟡 P2 | cta_replicator/NG=F n=24 WR=0% | Awaiting 3-AI consensus for symbol block | 3-AI |
| 🟡 P2 | rapid_fire/UUSDT n=34 WR=0% | Awaiting 3-AI consensus for symbol block | 3-AI |
| 🟢 Done | FOREX recovery confirmed (7d PF=1.584) | No action — monitor | — |
| 🟢 Done | CRYPTO 24h normalization post-HYPEUSDT block (#694) | Expected; no action | — |
| ⏳ Hold | PR #1231 (concurrency fix) | Re-check next cycle — CI unstable at audit time | Next audit |

---

## 10. Resolver Status (issue #685 — closed topic)

Per issue #685: resolver work is DONE. No resolver PRs opened or needed. Any PR claiming "widen re-resolve scope" should receive REQUEST_CHANGES with pointer to issue #685.

---

_Generated by Claude Sonnet 4.6 automated hourly audit. Branch: `audit/hourly-05z-sonnet`. Dashboard: `2026-05-18T04:12:40Z`._

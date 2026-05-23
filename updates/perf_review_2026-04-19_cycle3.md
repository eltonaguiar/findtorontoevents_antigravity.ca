# Strategy Performance Review — 2026-04-19 (Cycle 3 of 8h cron)

**Cron:** `870f36b0` (every 8h at :13 UTC)
**Data snapshot:** `dashboard_payload.json` generated 2026-04-19T08:59:50 UTC
**Inputs:** 3,500 closed picks · 33 active picks · 172 raw active · **163 tracked strategies** ✅

---

## TL;DR — 3 huge findings (cycle 3)

1. **🎉 P0 FIXED — track coverage RESTORED!** Tracked strategies went **5 → 163** between cycles 2 and 3 (coverage 2.6% → **88.6%**). Cycle 1's & 2's flagged P0 was actioned. **Massive engineer win.**

2. **🔴 NEW MASSIVE drain exposed by the fix:** `copy_hl_lb_None` — n=279, WR=31.9%, **mean PnL −289.75%** across **96 symbols**. The `_None` suffix suggests a strategy parameter wasn't set (likely `lookback=None` placeholder leaking). Was invisible in cycles 1-2 because it wasn't tracked. **Highest blast radius observed across all 3 cycles.**

3. **🟡 `st_fear_greed_contrarian` REVERSAL:** Cycle 2 saw n=454 WR=56.6% PF=2.70 (top promotion candidate). Cycle 3 sees n=533 WR=**26.5%** PF=0.57 mean=**−37.5%** across 18 symbols. **NOTE:** the recent_closed sample window appears to have rolled — wins went from ~257 to ~141 despite sample size GROWING. Either (a) sample window shifted significantly, or (b) strategy degraded sharply in last 24h. Either way, this is no longer a promotion candidate; needs investigation.

---

## 1. Track Coverage — RESOLVED

| Metric | Cycle 1 | Cycle 2 | **Cycle 3** | Δ vs C2 |
|---|---|---|---|---|
| Distinct strategies in closed_picks | 194 | 193 | 184 | -9 |
| Tracked strategies | 13 | 5 | **163** | **+158** |
| Coverage | 6.7% | 2.6% | **88.6%** | **+86.0 pp** |

**The P0 finding from cycles 1-2 has been resolved.** Whatever process is writing `strategy_performance.json` now captures the full strategy universe. This unblocks:
- `elite_scorer.py` `forward_wr` term (was missing for 97% of strategies)
- Trust tier calculations
- Mutation/promotion gates

---

## 2. NEW Mutation Candidates (revealed by improved tracking)

| Strategy | n | WR | PF | mean PnL% | symbols | Notes |
|---|---|---|---|---|---|---|
| **`copy_hl_lb_None`** | **279** | 31.9% | 0.56 | **−289.7%** | **96** | 🆕 NEW — **highest blast radius ever observed**. `_None` suffix suggests parameter not set. |
| **`st_fear_greed_contrarian`** | 533 | 26.5% | 0.57 | −37.5% | 18 | 🟡 REVERSAL from cycle 2's WR 57% PF 2.70 — investigate sample-window shift |
| `unknown` | 55 | 27.3% | 0.44 | −74.6% | 30 | 🆕 NEW — "unknown" strategy bucket = bad data hygiene |
| `atr_regime_rsi` | 44 | 27.3% | 0.44 | −23.2% | 1 | Worsened from cycle 2 (was WR 33%) |
| `cta_commodity_momentum_term` | 27 | 29.6% | 0.02 | −15.7% | 2 | Carry-over from cycles 1-2 |

### Highest priority: `copy_hl_lb_None`

96 symbols × 279 trades × −290% mean PnL is **catastrophic blast radius**.

**3-axis mutation proposal:**

| Axis | Current | Proposed |
|---|---|---|
| Parameter sweep | `lb_None` literal — **probably a bug, not a param** | First check: is "None" the literal string serialization of `lookback=None`? If so, find the upstream that's passing None and fix or short-circuit emission |
| Regime gate | None | If it IS a real strategy, gate on top-50 liquidity (96 symbols suggests it's firing on illiquid alts) |
| Inverse | LONG | At WR 32%, inverse would be WR 68% — but only worth it after fixing the `_None` parameter bug |

**Recommendation:** **STOP emission immediately**. The strategy name with `_None` suffix is a strong signal of a serialization bug — almost certainly should not be live. Investigate `copy_trader_intel/` for the upstream that emits this.

### `st_fear_greed_contrarian` reversal — investigate before acting

Cycle 2 → 3 math doesn't add up:
- Cycle 2: n=454, WR=56.6% → wins=257
- Cycle 3: n=533, WR=26.5% → wins=141
- Sample grew by 79 but absolute wins DROPPED by 116

This is impossible under append-only closed_picks. Most likely: the `recent_closed` sample window in `dashboard_payload.json` has shifted to a different time slice. Cycle 2's high WR may have been a windowing artifact.

**Recommendation:** before kill/mutate, verify against the FULL closed-pick ledger (not the truncated `recent_closed` view).

---

## 3. NEW Symbol Drains (5 new vs cycle 2's 1)

| Symbol | n | WR | mean PnL% |
|---|---|---|---|
| ADAUSDT | 78 | 28.2% | -41.7% |
| **APTUSDT** | **75** | **20.0%** | **-124.1%** |
| SUIUSDT | 65 | **16.9%** | -94.9% |
| LINKUSDT | 60 | 25.0% | -35.8% |
| UNIUSDT | 46 | 23.9% | -70.1% |

Cycle 2's ATOMUSDT no longer in top — either resolved or pushed out by worse offenders.

**Recommendation:** add APTUSDT + SUIUSDT to immediate symbol-quality blocklist. Both have <21% WR with severe negative mean PnL.

---

## 4. High-Conviction Pick Health

- Active picks: 43 → 33 (-10)
- Raw active (pre-gate): 298 → **172** (-126, **42% reduction**) — gates likely tightening with new tracking data
- High-conviction (elite_score≥70 OR confidence≥0.80): **10 of 33**
- **Flagged (land on bottom-quartile strategy/symbol):** **0**

Active gate logic still working as intended despite massive tracking changes.

---

## 5. Untracked High-Performers (still slipping through)

| Strategy | n | WR | PF | mean PnL% |
|---|---|---|---|---|
| `keltner_compression_expansion_sol_v1` | 21 | 85.7% | 9.93 | +85.8% |
| `crypto_rsi_whaleconfirmed_v1` | 21 | 57.1% | 0.88 | -5.5% |

Both new strategies (small n=21). Track writer just started capturing — these should appear in cycle 4.

---

## Action Checklist (cycle 3)

**P0 (urgent):**
- [ ] **Investigate `copy_hl_lb_None`** — likely a serialization bug emitting picks with `lookback=None`. Find the upstream emitter and either fix or short-circuit. 96-symbol blast radius means each cycle of inaction = more losing picks.
- [ ] **Investigate `st_fear_greed_contrarian` reversal** — verify against full ledger before promote/demote action.

**P1:**
- [ ] Symbol blocklist: APTUSDT (WR 20%, mean -124%), SUIUSDT (WR 17%, mean -95%)
- [ ] Investigate "unknown" strategy bucket (n=55, mean -75%) — strategy attribution is failing somewhere

**Carry-over from cycles 1-2 (still pending):**
- [ ] `quan_engine_scalp` -$1.4M paper PnL (still tracked, still active)
- [ ] `cta_commodity_momentum_term` mutation
- [ ] ATOMUSDT cycle-2 drain — verify if dropped out organically

**Resolved (engineer wins):**
- [x] **P0 — strategy_performance.json under-population FIXED** (5 → 163 entries)

---

## Methodology + provenance

- Same as cycles 1-2 (PR #257, #258)
- **NOTE:** the recent_closed sample is a ROLLING WINDOW, not the full closed-pick ledger. Cycle-over-cycle comparisons of strategies near sample-window boundaries (e.g. st_fear_greed_contrarian) can show large WR swings that aren't real strategy degradation.
- Snapshot saved to `tools/out/perf_review_cycle3_*.json`
- **No production strategy files modified.** Engineer review required per `CLAUDE.md` mutation-before-kill rule.

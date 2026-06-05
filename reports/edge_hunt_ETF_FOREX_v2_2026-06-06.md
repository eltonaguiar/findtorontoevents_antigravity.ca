# ETF + FOREX Edge Hunt v2 — Backtest-to-Paper Acceleration

**Date:** 2026-06-06  
**Goal #1:** Phenomenal `/audit` performance — accelerate lab→paper→probation without sizing on stale class numbers.  
**Verdict:** **No live edge in either class.** Best path = **verified ETF pilots + FOREX allowlist probation** after backtest n≥30.

**Canonical live class (policy-clean net, `money_ready_verdict.json` 2026-06-05T14:09Z):**

| Class | n | WR | PF | Verdict | Live sizing |
|-------|--:|---:|---:|---------|-------------|
| ETF | 11 | 63.6% | **0.80** | `INSUFFICIENT_DATA` | **0%** |
| FOREX | 22 | 22.7% | 11.22* | `INSUFFICIENT_DATA` | **0%** (`FOREX_HARD_DISABLE=1`) |

\*FOREX PF skewed by one `regime_strong_bear` outlier (+61%); WR fails T2. Do not size.

---

## ETF sleeves

### 1. `etf_verified_dual_momentum` — **lead candidate**

| Layer | Source | PF | n | Notes |
|-------|--------|---:|--:|-------|
| Full backtest | `reports/etf_dual_momentum_backtest_2026-06-03.md` | **3.57** | 48 mo | Bootstrap PF lo **1.64** |
| Purged CV test | `reports/etf_dual_momentum_cv_2026-06-03.md` | **5.37** | 19 test | HOLDS_OOS |
| Walk-forward OOS | `verified_strategies/WALKFORWARD_REPORT.json` | **2.746** | **11** | PASS |
| Paper pilot forward | `reports/etf_forward_stats_latest.json` | 0.0 | **0** | XLK OPEN since 2026-06-02 |
| Legacy DB sleeve | `reports/bootstrap_forward_stats_latest.json` | **0.665** | 25 | `etf_dual_momentum` scanner — **reject for sizing** |

**Paper pilot status:** **ACTIVE** — `verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` in eagle suite; `etf_dual_momentum_state.json` last_run 2026-06-05T14:13Z; admit `FORWARD_PILOT_ONLY` (`reports/strategy_admit/etf_dual_momentum.json`). Gates: n<100, pf<1.5, wr<50%, pf<0.85×OOS (2.746).

**Days to n=30 (forward closed):** Monthly rebalance cadence → **~1 close/month** when rank flips. First close ≈ **2026-07-02** (XLK rotation). **~29 months** to n=30 at current cadence (**~870 calendar days** from 2026-06-06). Shadow checkpoint (n≥30) earliest **~2028-11** without acceleration.

**Acceleration lever:** Daily pilot already closes on symbol change — no new code; bottleneck is signal stability (XLK leading 12-1m). Optional: add quarterly forced mark-to-market closes to 3× effective sample rate (still ~10 months to n=30).

---

### 2. `faber` / `etf_faber_tactical` — stats only, pilot missing

| Layer | Source | PF | n | Notes |
|-------|--------|---:|--:|-------|
| Faber forward stats | `reports/faber_forward_stats_latest.json` | 0.0 | **0** | No closes in `trading_picks` |
| Raw DB (unverified) | `reports/2026-06-05-PER-ASSET-WINNER-DIG.md` | — | 37 | `etf_faber_tactical`; PF not computed |
| Persona | `config/personas/strategy_persona__etf_faber_tactical.json` | — | 0 live | Shadow until 2026-06-30; n≥30 promotion bar |

**Paper pilot status:** **NOT RUNNING** — `tools/faber_forward_stats.py` wired in eagle suite but **no** `faber_taa_paper_log.jsonl` / `faber_taa_positions.json` under `verified_strategies/paper_pilot/`. Note: "forward pilot only until resolver closes etf_faber_tactical rows."

**Days to n=30:** **∞ until pilot harness exists.** Once mirrored on dual-momentum pilot (month-end Faber 5-asset): persona expects **6–12 months** to n=30 (monthly cadence). Target stand-up: **≤7 days**.

---

### 3. `etf_sector_rotation` — wired shadow, no pilot

| Layer | Source | PF | n | Notes |
|-------|--------|---:|--:|-------|
| Sector rotation backtest | `audit_dashboard/data/etf_sector_rotation_backtest.json` | **2.047** | **122** periods | 2015–2026, 70.5% WR |
| VIX overlay (ETF) | `reports/etf_vix_regime_breakthrough_20260513.md` | **3.22** | **102** | VIX<25 sweet spot |
| Live forward | `pf_registry` | — | **0** | `production_enable: False`; orchestrator shadow |

**Paper pilot status:** **NONE** — `tools/feature_signals/etf_sector_rotation.py` → signals JSON only; zero closed picks.

**Days to n=30:** Pilot + monthly closes → **~30 months** from pilot start. Fast-week prep: clone `etf_dual_momentum_pilot.py` harness with sector top-3 universe.

---

### 4. `equity_vix_regime_rotator` — shadow pilot (EQUITY-class tool, ETF allocation)

| Layer | Source | PF | n | Notes |
|-------|--------|---:|--:|-------|
| Full backtest | `reports/equity_vix_regime_rotator_2026-06-04/backtest_summary.json` | **1.695** | 3097 days | Sharpe 2.968 |
| Walk-forward OOS | same | **1.748** | **607** days | Sharpe **3.091**; gates PASS |
| Paper shadow | `verified_strategies/paper_pilot/equity_vix_regime_rotator_state.json` | — | **0 closed** | `day_count` 13/30; RISK_ON 100% |

**Paper pilot status:** **ACTIVE SHADOW** — `equity_vix_regime_rotator_pilot.py` in eagle suite; logs `would_be_allocation` only (no CLOSE events). Promotion: 30 shadow days + Sharpe within 30% of OOS 3.16 + MDD<5%.

**Days to n=30:**  
- **30-day shadow gate:** started 2026-06-04 → complete **~2026-07-04** (**28 days**).  
- **30 closed trades:** not instrumented. Backtest `n_regime_switches`=712 / 3097 days ≈ 1 switch/4.3d → if wired to close on regime flip, **~130 days** to n=30. Without close wiring: n stays 0 indefinitely.

---

## FOREX sleeves

### 5. `forex_carry_g10` — backtest shortcut (allowlist)

| Layer | Source | PF | n | Notes |
|-------|--------|---:|--:|-------|
| Carry backtest | `reports/forex_carry_backtest_20260605.json` | **2.108** | **13** | WR 69.2%; monthly 2023–2024 |
| Unlock bar | same | >1.0 | **≥30** | `unlock_status: LOCKED` |
| Live `pf_registry` | policy-clean | — | **0** | `forex_carry` not in resolved rows |

**Paper pilot status:** **NONE** — backtest only; `FOREX_HARD_DISABLE=1` blocks production.

**Days to n=30:**  
- **Backtest n=30:** extend window 2010–2025 → **≤3 days** engineering (expect n≈150+ monthly legs). Unlocks probation per `docs/FOREX_HARD_DISABLE_RATIONALE.md` step 1.  
- **Forward n=30:** monthly paper pilot once wired → **~30 months** from pilot start unless weekly basket marks added.

---

### 6. `cta_cross_asset_tsmom` SHORT — allowlist, zero live proof

| Layer | Source | PF | n | Notes |
|-------|--------|---:|--:|-------|
| `pf_registry` (FOREX) | 2026-06-05 | — | **0** | No resolved rows |
| Mutation autopsy SHORT | `reports/forex_mutation_autopsy_20260515.md` | **8.11** | **29** | WR 34.5%; failed WF OOS |
| Recent institutional | `alpha_engine/data/institutional_metrics.json` | ~0 | **11** | WR 9.1%; net negative |
| Code comment (unverified) | `audit_trail/quality_gates.py:1547` | 2.8 | 120 | Claimed T1 SHORT; **not in pf_registry** |

**Policy:** `alpha_engine/non_crypto_policy.py` — `_FOREX_ALLOWED = {cta_cross_asset_tsmom, forex_carry}`; **SHORT-only** for tsmom (`direction != SHORT` → reject).

**Paper pilot status:** **NONE** — signals still emit to `multi_asset/data/multi_asset_picks.json` but hard-disable zeros live picks.

**Days to n=30:** Stand up SHORT-only paper pilot with session gate (M-078) + TP 1.5%/SL 1.0%. At ~2–3 signals/week across G10/JPY crosses: **~10–15 weeks (~70–105 days)**. Backtest harness for tsmom FOREX SHORT not committed — run `tools/edge_stability_harness.py` first.

---

## Combined ranking (backtest-to-paper readiness)

| Rank | Sleeve | Lab PF/n | Forward n | Pilot | Fastest n=30 path |
|------|--------|----------|----------:|-------|-------------------|
| 1 | `etf_verified_dual_momentum` | 2.746 / 11 OOS | 0 | ✅ active | ~29 mo monthly; first close ~Jul-2026 |
| 2 | `forex_carry_g10` | 2.11 / 13 | 0 | ❌ | **3d** backtest extend → 30d paper start |
| 3 | `equity_vix_regime_rotator` | 1.748 OOS / 607d | 0 closes | ✅ shadow | **28d** shadow done; +130d if close wiring |
| 4 | `cta_cross_asset_tsmom` SHORT | 8.11 / 29 hist | 0 | ❌ | ~70–105d once pilot wired |
| 5 | `etf_sector_rotation` | 2.05 / 122 | 0 | ❌ shadow | ~30 mo after pilot clone |
| 6 | `faber` / `etf_faber_tactical` | — / 37 raw DB | 0 | ❌ stats only | ∞ until harness; then ~6–12 mo |

**Reject for sizing:** Live ETF `cta_golden_cross` (PF 0.56, n=7); legacy `etf_dual_momentum` DB forward (PF 0.665); FOREX `multi_asset_scanner` (PF 0.21, n=11).

---

## Actionable real-money timeline

### Phase 0 — Hold (now → unlock)
- **ETF / FOREX live sizing: 0%.** Class verdicts `INSUFFICIENT_DATA`; `freeze_promotions` active.
- Keep `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=0`, `FOREX_HARD_DISABLE=1`.
- Cron eagle suite daily (already runs all ETF pilots + stats).

### Phase 1 — Fast week (2026-06-06 → 2026-06-13)

| Day | Action | Owner artifact |
|-----|--------|----------------|
| D0 | Extend `forex_carry` backtest 2010–2025; require n≥30, PF>1.5 | `reports/forex_carry_backtest_*.json` |
| D1 | Clone `etf_dual_momentum_pilot.py` → `faber_taa_forward_pilot.py` (month-end) | `verified_strategies/paper_pilot/` |
| D2 | Wire `equity_vix_regime_rotator` CLOSE on regime switch (virtual PnL) | pilot + forward stats tool |
| D3 | Stand up FOREX paper pilot: `forex_carry` + `cta_cross_asset_tsmom` SHORT-only, shadow | new pilot + `FOREX_HARD_DISABLE` exemption flag for pilots only |
| D7 | Review: etf first close?, vix shadow day 7/30, carry backtest unlock? | `pilot_forward_dashboard.json` |

### Phase 2 — Shadow checkpoints (2026-06-13 → 2026-07-15)

| Milestone | Date est. | Gate |
|-----------|-----------|------|
| VIX rotator 30d shadow complete | **2026-07-04** | OOS Sharpe parity ±30% |
| ETF dual-momentum first CLOSE | **~2026-07-02** | XLK rotation or CASH |
| `forex_carry` backtest n≥30 unlock | **~2026-06-09** | PF>1.0, WR>45% per M-007 |
| Faber pilot first month-end tick | **2026-06-30** | n_closed ≥ 1 |

### Phase 3 — Probation (2026-07 → 2026-12)

- **FOREX:** If carry backtest + 30d paper PASS → `FOREX_HARD_DISABLE=0` for allowlist only (`cta_cross_asset_tsmom` SHORT + `forex_carry`); max **0.25%** per pick.
- **ETF:** If dual-momentum forward n≥5 and PF within 30% of OOS → enable shadow scanner (`ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1` shadow mode).
- **Do not** merge `etf_sector_rotation` to production until independent 30d pilot.

### Phase 4 — Real-money ladder (2027+)

| Gate | Requirement | ETA (monthly cadence) |
|------|-------------|----------------------|
| Shadow checkpoint | forward n≥30, PF≥1.5, WR≥50% | ETF dual: **~2028-11**; Faber: **~2027-06** if pilot starts Jun-13 |
| Promotion | forward n≥100, PF≥0.85×OOS | **+70 months** after shadow unless forced quarterly closes |
| Class T2 | n≥100, PF≥1.5, WR≥50%, MDD<20% | Not before **2027 H2** earliest (FOREX if weekly pilot); **2028+** for monthly ETF |

**Acceleration thesis:** Backtest-to-paper skips multi-year class wait — use **backtest n≥30** to unlock probation pilots immediately; accept that **forward n=30 on monthly sleeves is structurally 2+ years** unless rebalance frequency or virtual backfill is explicitly approved.

---

## Reproduce

```bash
# ETF
python3 verified_strategies/paper_pilot/etf_dual_momentum_pilot.py --one-shot
python3 tools/etf_forward_stats.py --write
python3 tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF --write

# VIX rotator
python3 verified_strategies/paper_pilot/equity_vix_regime_rotator_pilot.py --one-shot
python3 tools/equity_vix_regime_rotator.py --walkforward --backtest

# FOREX carry
cat reports/forex_carry_backtest_20260605.json | python3 -m json.tool

# Dashboard rollup
python3 tools/pilot_forward_dashboard.py
python3 alpha_engine/money_ready_verdict.py --json
```

---

## Bottom line

- **ETF:** Only `etf_verified_dual_momentum` has lab PASS + live pilot; forward **n=0** blocks everything. Best ETF backtest (`etf_sector_rotation` + VIX, PF 3.22 n=102) is **unpiloted**.
- **FOREX:** `forex_carry_g10` is the fastest unlock (**extend backtest 3 days**); allowlist SHORT tsmom needs pilot + proof — **0 pf_registry rows today**.
- **Real money before 2027:** Only via **probation sizing (≤0.25%)** on FOREX allowlist after backtest+30d paper; ETF remains pilot-only until forward n≥30 (~2028 at monthly cadence) unless rebalance acceleration is approved.

*Sources: `audit_dashboard/data/pf_registry.json`, `money_ready_verdict.json`, `etf_forward_stats_latest.json`, `faber_forward_stats_latest.json`, `forex_carry_backtest_20260605.json`, `strategy_admit/etf_dual_momentum.json`, `pilot_forward_dashboard.json`, paper_pilot state/log files, `non_crypto_policy.py`.*

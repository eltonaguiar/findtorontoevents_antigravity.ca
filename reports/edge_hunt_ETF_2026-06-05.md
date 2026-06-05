# ETF Edge Hunt — 2026-06-05

**Verdict: `NO_EDGE_YET`** (live class) · **`BEST_CANDIDATE`: `etf_verified_dual_momentum`** (lab + forward pilot)

Sources: `audit_dashboard/data/pf_registry.json`, `money_ready_verdict.json`, `verified_strategies/WALKFORWARD_REPORT.json`, `reports/etf_forward_stats_latest.json`, `reports/faber_forward_stats_latest.json`, `reports/bootstrap_forward_stats_latest.json`, `reports/strategy_admit/etf_dual_momentum.json`.

---

## 1. Live ETF class (`pf_registry` policy-clean net)

| Metric | Value |
|--------|-------|
| n | **11** |
| WR | 63.6% |
| PF | **0.80** |
| MDD | 98.6% |
| Verdict | `INSUFFICIENT_DATA` (`money_ready_verdict.json`) |

**`cta_golden_cross`** dominates: n=7, WR=71%, **PF=0.56**, single-source artifact (`file:alpha_engine`, 100%). Jun-04 batch: 0W/2L, −0.98% PnL. **Not an edge — noise from CTA emitter on ETF tickers.**

No `etf_dual_momentum` / `etf_verified_dual_momentum` rows in live `pf_registry`.

---

## 2. Dual momentum backtest vs forward (PF 1.6 / n=104 claim)

**Claim not found in repo.** Verified paths:

| Layer | File | PF | n | Notes |
|-------|------|----|---|-------|
| Full backtest | `reports/etf_dual_momentum_backtest_2026-06-03.md` | **3.57** | 48 mo | Bootstrap CI lo **1.64** |
| Purged CV | `reports/etf_dual_momentum_cv_2026-06-03.md` | 5.37 test | 19 test | HOLDS_OOS |
| Walk-forward OOS | `verified_strategies/WALKFORWARD_REPORT.json` | **2.746** | **11** | PASS |
| Paper pilot | `verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` | — | **0 closed** | XLK OPEN since 2026-06-02 |
| DB forward (legacy sleeve) | `bootstrap_forward_stats_latest.json` | **0.665** | 25 | `etf_dual_momentum` scanner rows — **fails** |

Forward pilot **exists** (`etf_dual_momentum_state.json`, daily in `eagle_suite`). Admit: `FORWARD_PILOT_ONLY` (`reports/strategy_admit/etf_dual_momentum.json`). H-102 preregistered.

*n=102 / PF≈1.6* refers to **sector-rotation VIX backtest** (`reports/etf_vix_regime_breakthrough_20260513.md`) — different sleeve, not dual-momentum pilot.

---

## 3. Forward stats (2026-06-05T13:27Z)

- **`etf_forward_stats_latest.json`**: virtual pilot n=0, gates `n<100`, `pf<1.5`, `wr<50%`, `pf<0.85*oos`. `recommend_scanner_enable: false`.
- **`faber_forward_stats_latest.json`**: n=0, no closes; note: no `faber_taa_*` files under `verified_strategies/paper_pilot/`. Pilot not running.

---

## 4. `etf_sector_rotation.py` wiring

**Wired, shadow-only.** Called from `tools/feature_signals/orchestrator.py` → `etf_sector_rotation_signals.json`. `production_enable: False`. Registered in `JSON_PICK_SOURCES` / `dashboard_generator.py`. **Zero closed picks** (FV-exempt cold-start in `quality_gates.py`).

---

## 5. Faber / 30d paper parity — can we size?

**No.** Sizing ladder requires forward n≥100 + PF≥1.5 + WR≥50% + forward PF ≥ 0.85× OOS (2.746). Current forward n=0; class PF 0.80. Lab OOS n=11 is itself below Tier-2 floor.

**30d shadow checkpoint** (n≥30): earliest ~2026-07-02 if monthly rebalance closes XLK. Until then: **0% live sizing**, pilot-only.

---

## Top 3 (ranked)

1. **`etf_verified_dual_momentum`** — only sleeve with lab WF PASS + active paper pilot. Blockers: forward n=0, class INSUFFICIENT_DATA.
2. **`etf_sector_rotation`** (Faber abs + Antonacci rel, orchestrator-wired) — needs pilot + `production_enable` after 30d shadow; complements #1 (6m sector vs lab 12-1).
3. **Sector rotation + VIX gate** (`etf_vix_regime_breakthrough`, n=102 backtest PF 3.22) — strongest backtest, **unwired** to pilot; fast-week prep only.

**Reject:** `cta_golden_cross` ETF (PF 0.56, n=7). **Faber TAA** — stats tool only, no pilot artifacts.

---

## Fast-week path (≤7d)

| Day | Action |
|-----|--------|
| D0–D7 | Cron `etf_dual_momentum_pilot.py` + `etf_forward_stats.py --write` (already in eagle suite) |
| D3 | Add monthly close logic so pilot accumulates closed trades (currently stuck OPEN) |
| D7 | First shadow checkpoint review: n_closed, parity vs OOS PF 2.746 |
| Hold | `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=0`; freeze_promotions per `bootstrap_forward_stats` |
| Optional | Stand up `faber_taa` paper pilot mirroring dual-momentum harness |

**Reproduce:** `python3 verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` · `python3 tools/etf_forward_stats.py --write` · `python3 tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF`

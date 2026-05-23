# World-Class Performance Session — 2026-05-16

**Session goal:** use swarm + direct implementation to perform enhancements that bring the repo to world-class prediction/performance per asset class — real-money trustworthy with verifiable edge per class.

**Goal budget:** 17/20 turns used.

---

## Asset Class Health (verdict-grade, dashboard_data.json 2026-05-16)

| Class | PF | WR% | n | sizing | Tier vs T2 |
|---|---|---|---|---|---|
| CRYPTO | 1.31 | 46.6% | 8033 | True | T3 (PF<1.5, WR<50%) |
| EQUITY | 1.55 | 51.4% | 426 | True | **T2 ✓** |
| COMMODITY | 2.57 | 62.6% | 337 | True | **T1 ✓** |
| ETF | 1.33 | 57.4% | 108 | True | T3 (PF<1.5) |
| BOND | 0.66 | 54.5% | 11 | False | SUB (n too small) |
| FOREX | 0.86 | 54.7% | 311 | False | SUB (PF<1.0) |
| FUTURES | — | 100.0% | 2 | False | seeding |

---

## Enhancements Shipped This Session (all committed + pushed)

### Wave 1 — New Strategy Signals

**1. `equity_two_bar_rsi_reversal` (opt-in, EQUITY_RSI2_TWOBAR_ENABLED=1)**
- Backtest proof: META n=243 PF=1.83 WR=57%, MSFT n=230 PF=1.54 WR=51%, ADBE n=173 PF=1.66
- Logic: 2 consecutive red bars + RSI(2) < 25 + price above EMA200 → LONG
- Wired into: `alpha_engine/equity_strategies.py` + caller in `non_crypto_agent/main.py:429`
- Commits: `414b28fbea`

**2. `commodity_carry_momo_double_sort` sidecar (opt-in, COMMODITY_CARRY_MOMO_ENABLED=1)**
- Fuertes/Miffre/Rallis 2010: long top-quintile on BOTH 12-1 momentum AND carry, short bottom
- Wired into `non_crypto_agent/main.py` as try/except sidecar
- Commits: `d5de5d6d4e`

**3. `sector_dual_momentum_12_1` sidecar (opt-in, ETF_SECTOR_DUALMO_ENABLED=1)**
- Antonacci GEM: ranks 9 SPDR sectors by 12-1 month momentum; RISK_ON → top-3 sectors; RISK_OFF → AGG
- Wired into `non_crypto_agent/main.py` as try/except sidecar
- Commits: `80b21fd03f`

### Wave 2 — CRYPTO Drag Reduction

**4. 6 meme/micro-cap symbol bans (HF_QUALITY_GATE_ENABLED=1)**
- Banned: WIFUSDT, PEPEUSDT, BONKUSDT, SHIBUSDT, FLOKIUSDT, BOMEUSDT
- File: `alpha_engine/hedge_fund_quality_gate.py::CRYPTO_BANNED_SYMBOLS`
- Commits: `f2236d35ea`

**5. Volume caps for 5 drag sources (enforced at intake)**
- `battleground`: 2% CRYPTO (PF 0.65, severe drag)
- `copy_trader_highscore`: 2% CRYPTO (PF 0.80, WR 30.3%, n=99)
- `regime_terminal`: 2% CRYPTO + 5% EQUITY + 5% FOREX (WR 34.3%)
- `rapid_fire`: 5% CRYPTO + 5% FOREX (PF 0.81, WR 37.1%, n=570)
- `super_signals`: 5% CRYPTO + 5% EQUITY (PF 0.86, WR 36.8%, n=161)
- File: `alpha_engine/per_source_volume_cap.py::PER_SOURCE_VOLUME_CAP`
- Commits: `ba432aceed`, `d7f6f610df`, `e09b8b361f`, `98c1fb9cc5`

### Wave 3 — Score Recalibration

**6. `claude_gainer` score recalibration: -50 → +8**
- Stale penalty: calibrated at 13.3% WR on tiny n (< 50 picks)
- Current state: PF=2.23 WR=56.2% n=965 (verdict-grade dashboard)
- After `claude_gainer_st` blacklist (2026-05-01), base system shows T1-quality performance
- File: `audit_trail/quality_gates.py:4669`
- Commits: `6761b8a2e4`

### Wave 4 — Test Fixes

**7. M049 safety halt gate test isolation fix**
- `test_m049_safety_stop_blocks_pick_at_active_gate` was failing because conftest.py
  sets `SAFETY_HALT_GATE_ENABLED=0` globally; test now explicitly re-enables via monkeypatch
- All 77 core gate tests pass after this fix

---

## Quarantine Manifest (synced)

`alpha_engine/quarantine_manifest.json::per_source_volume_caps` updated with all 7 entries,
matching `per_source_volume_cap.py` exactly to eliminate the prior 5%-vs-12% desync.

---

## Pending (human action required)

| Item | Blocker | Expected impact |
|---|---|---|
| FRED_API_KEY in GitHub Secrets | Human sets secret | Unblocks BOND+EQUITY+COMMODITY macro context |
| Enable EQUITY_RSI2_TWOBAR_ENABLED=1 | 14-day shadow period | +n from backtest-validated EQUITY strategy |
| Enable ETF_SECTOR_DUALMO_ENABLED=1 | Shadow period + paper validation | Adds sector rotation ETF picks |
| Enable COMMODITY_CARRY_MOMO_ENABLED=1 | Shadow period | Adds commodity carry+momentum double-sort |
| BOND n accumulation | CI must run bond_scanner.py | PF will be meaningful once n≥30 |
| Full quarantine for battleground/copy_trader/regime_terminal | User approval | Upgrade soft caps → full BLOCKED_ASSET_STRATEGY_PAIRS |

---

## Score Table Calibration Status

Sources with stale calibration identified and flagged for next audit:

| Source | Old score | New score | Evidence |
|---|---|---|---|
| `claude_gainer` | -50 (13.3% WR, ~10 picks) | +8 | PF=2.23 WR=56.2% n=965 |
| `signal_validation` | +10 | +10 (unchanged) | PF=4.70 WR=60.3% n=565 — validates |
| `aggregated_picks` | +6 | +6 (unchanged) | PF=5.65 WR=76.9% n=424 — validates |
| `mega_mutation` | +15 | +15 (unchanged) | PF=2.43 WR=58.8% n=291 — validates |

---

*Generated: 2026-05-16 by world-class-perf-2026-05-15 goal session, turn 17/20*
*Reproducer: `git log --oneline 414b28fbea..1df661143c`*

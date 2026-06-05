# P1 real-money sleeves — completion log (2026-06-05)

**Goal #1** — forward evidence + paper pilots without sizing on class aggregates.  
**Canonical verdict:** `audit_dashboard/data/money_ready_verdict.json` — **0/9** money-ready (do not cite dashboard Smart-Picks headline).

---

## What was verified / shipped this tranche

### 1. FOREX carry — extended backtest (UNLOCK_READY)

| Window | n | WR | PF | Status |
|--------|--:|---:|---:|--------|
| 1y default (`2025-06-05` → `2026-06-05`) | 12 | 83.3% | 4.34 | LOCKED (n&lt;30) |
| 10y G10 (`2010-01-01` → `2026-06-05`) | **197** | **60.4%** | **1.59** | **UNLOCK_READY** |

- Artifact: `reports/forex_carry_backtest_extended_20260606.json`
- Reproduce: `python3 tools/research/forex_carry.py --backtest --start 2010-01-01`
- **Production:** `FOREX_HARD_DISABLE=1` stays on until 30 **forward** monthly closes on `forex_carry_g10` paper pilot (`verified_strategies/paper_pilot/forex_carry_g10_pilot.py`). Lab unlock ≠ live sizing.

### 2. ETF dual momentum — paper pilot (OPEN, no CLOSE yet)

| Field | Value |
|-------|--------|
| State | `verified_strategies/paper_pilot/etf_dual_momentum_state.json` |
| Open | **XLK** LONG since `2026-06-02` @ 195.76 |
| Paper log | Created on first rotation CLOSE (log was empty before daily tick) |
| Lab OOS | PF 2.746 / WR 63.6% / n=11 (`etf_verified_dual_momentum`) |
| Live forward DB | n=25, WR 52%, PF 0.665 — **not** promotion-ready |

Daily cron: `tools/run_verified_pilots_daily.py` → `etf_dual_momentum_pilot.py --one-shot`.

### 3. COMMODITY proxy — DBMF/KMLM paper pilot (new)

While COMMODITY futures class stays frozen, commodity beta is tracked under **ETF** via managed-futures ETFs.

| Item | Path |
|------|------|
| Signal generator | `alpha_engine/etf_managed_futures_proxy.py` |
| Paper pilot | `verified_strategies/paper_pilot/etf_managed_futures_proxy_pilot.py` |
| Cron | Wired in `tools/run_verified_pilots_daily.py` (after ETF DM pilot) |

Rules: LONG DBMF/KMLM when 3m momentum &gt; 0 and VIX &lt; 25; flat otherwise. Virtual book only — **no** `ETF_MANAGED_FUTURES_ENABLED` production flag.

Verify:

```bash
python3 verified_strategies/paper_pilot/etf_managed_futures_proxy_pilot.py --one-shot
python3 -c "import py_compile; py_compile.compile('verified_strategies/paper_pilot/etf_managed_futures_proxy_pilot.py', doraise=True)"
```

### 4. CRYPTO pilot — sizing policy (documented, gates already live)

**Only pilot sleeve:** `crypto_liquidity_wick_reversal_v1` (policy-clean n≈30, WR≈60%, PF≈1.55 — single-source; monitor only).

| Rule | Enforcement |
|------|-------------|
| LONG-only bias | Class / incident P0; do not rely on SHORT crypto for sizing |
| Liquid-core whitelist | `audit_trail/quality_gates.py` M-001 + `alpha_engine/crypto_liquid_core.py` |
| BTC UTC death-zone | Hours 9, 10, 18, 21 UTC blocked |
| Block copy-trader stacks | `BLOCKED_ASSET_STRATEGY_PAIRS`: `copy_trader_intel`, `copy_trader_clones`, `copy_trader_highscore` |
| On-chain for HC scoring | `crypto_risk_gates` → `network_metrics` → `fundamental_macro_gates` (see `updates/2026-06-05-crypto-onchain-fundamental-gates.md`) |
| Position cap (pilot) | **≤0.25×** normal crypto sleeve size; **max 2** concurrent wick-reversal positions; no class-level sizing on CRYPTO aggregate |

Do **not** promote `mega_mutation` to production sizing until 30-day paper pilot passes (`mega_mutation_state.json`, review ~2026-07-05).

---

## P0 recap (merged earlier today)

- PEAD shadow on `alpha-engine-live`: `PEAD_EQUITY_ENABLED=1`, `PEAD_REQUIRE_GUIDANCE_RAISE=0`, `PEAD_EQUITY_PROBATION=0`
- EQUITY blocks: `multi_asset_copytrader`, `regime_accumulation` in `quality_gates.py`
- Doc: `updates/2026-06-05-pead-shadow-cron-equity-blocks.md`

---

## Still open (P1 tail → P2)

| # | Item | Owner |
|---|------|--------|
| 1 | First ETF DM **CLOSE** in paper log → starts forward n counter | daily pilot cron |
| 2 | `forex_carry_g10` first monthly **CLOSE** (basket opened 2026-06-05) | monthly rebalance |
| 3 | `PEAD_EQUITY_PROBATION=1` after ~30 shadow rows | ops / GHA env |
| 4 | Expand `data/earnings/` beyond 4 tickers + real `guidance_raised` | data pipeline |
| 5 | `tools/research/forex_carry.py --start` in CI doc only (CLI added this tranche) | — |

---

## Reproduce bundle

```bash
python3 tools/research/forex_carry.py --backtest --start 2010-01-01
python3 verified_strategies/paper_pilot/etf_dual_momentum_pilot.py --one-shot
python3 verified_strategies/paper_pilot/etf_managed_futures_proxy_pilot.py --one-shot
python3 verified_strategies/paper_pilot/forex_carry_g10_pilot.py --one-shot
python3 -c "import json; s=json.load(open('verified_strategies/paper_pilot/etf_dual_momentum_state.json')); print(s)"
```

---

## Related artifacts

| Path | Purpose |
|------|---------|
| `reports/edge_hunt_REAL_MONEY_2026-06-05.md` | Master per-class table |
| `updates/2026-06-05-real-money-edge-hunt-session.md` | Session index + PR list |
| `reports/forex_carry_backtest_extended_20260606.json` | 10y carry unlock proof |
# Codebase + DB + GHA Narrowing — per asset class (v1)

**Repo:** findtorontoevents_antigravity.ca — audit dashboard + pick pipeline.

## Ground truth

- **11/11** daily-bar causal hypotheses **KILLED** (`tools/edge_stability_harness.py`).
- Canonical PF: `audit_dashboard/data/pf_registry.json` → `by_asset_class_policy_clean_net`.
- **Emitter whitelist shipped** (shadow): `alpha_engine/emitter_whitelist.py` + `EMITTER_REGISTRY_GATE=1`.
- **No live capital** until forward harness + n≥100 clean per class.

## Databases (MySQL)

| DB | Role |
|----|------|
| `ejaguiar1_stocks` | Live picks, `at_raw_picks`, resolver outcomes |
| `ejaguiar1_backtests` | Strategy backtests, DNA/mutation runs |
| `ejaguiar1_sportsbet` | Sports (Goal #2 — separate) |

## Your task

For **each** asset class (CRYPTO, EQUITY, COMMODITY, ETF, FOREX, BOND):

### 1) Narrow the funnel

Name **specific** tables/columns + **GitHub Actions workflow files** (`.github/workflows/*.yml`) that feed picks for this class. What to **stop** generating vs **keep**? One bullet per class.

### 2) Strategy vs backtest vs mutation

| Question | Answer in 1–2 sentences |
|----------|-------------------------|
| Need **new strategies**? | Y/N + which scanner family |
| Need **more backtesting**? | Y/N + which DB table / tool |
| Need **better backtesting**? | Y/N + fix (walk-forward, costs, leakage) |
| Need **DNA mutation** (`tools/mutation_analysis.py`, baby_strategies)? | Y/N + axis (universe/horizon/filter) |
| Need **more free APIs**? | Y/N + which data gap |

### 3) Three repo-grounded ideas

Each idea MUST include:
- `id` (SCREAMING_SNAKE)
- `wire_target` (exact path: `alpha_engine/...`, `audit_trail/...`, `.github/workflows/...`)
- `acceptance_test` (numeric, 60d horizon)

### 4) One pre-registerable hypothesis (CRYPTO only)

Tick/intraday family **not** on killed list. Name `bar_freq`, data source (Binance aggTrade etc.), harness gate.

**Forbidden:** Generic "use ML", killed families (COT directional, funding arb, PEAD, on-chain counts), claiming EQUITY/ETF/BOND live-ready from registry PF alone.

**Toxic pairs (block):** `quan_engine`/CRYPTO, `cta_replicator`/COMMODITY, `multi_asset_copytrader`/FOREX,EQUITY.

# Asset-Class Expansion Scope — 2026-05-12

Investigator output digest: where sparse asset classes (BOND, ETF, FUTURES)
currently sit + what's available to wire on.

## Per-class snapshot (post-resolver-v2)

| Class      | n      | WR     | PF    | Status                                 |
|------------|--------|--------|-------|----------------------------------------|
| BOND       | 18     | 55.6%  | 1.72  | meets PF+WR floors, n far below charter 100 |
| ETF        | 87     | 55.2%  | 1.24  | borderline, n→100 close                |
| FUTURES    | —      | 5.9%   | —     | silent-dead, kills logged no replacement |
| FOREX      | 1169   | 46.4%  | 0.27  | sub-floor, mutate-before-kill protocol |
| COMMODITY  | 750    | 46.9%  | 1.78  | meets PF, lift WR target               |
| EQUITY     | 421    | 52.7%  | 1.41  | Tier-2 candidate                       |
| CRYPTO     | 8067   | 44.6%  | 1.25  | sub-T2; drag cut needed                |

## Symbol universe per class (`alpha_engine/config.py`)

| Class      | Where                | Count | Sample                              |
|------------|----------------------|-------|-------------------------------------|
| FOREX      | `config.py:515`      | 19    | EURUSD, GBPJPY, CADJPY, …           |
| COMMODITY  | `config.py:594`      | 21    | GC=F, CL=F, NG=F, USO, UNG          |
| FUTURES    | `config.py:628`      | 15    | ES=F, NQ=F, ZN=F, 6E=F, HG=F        |
| ETF        | `config.py:650`      | 50    | SPY, XLK, TQQQ, SQQQ, GDX           |
| BOND       | `config.py:721`      | 14    | TLT, IEF, SHY, LQD, HYG, AGG, BND   |

Symbol universes are NOT the bottleneck — coverage is adequate for all sparse
classes. The bottleneck is **emission volume** (strategies not wired) and
**blocklist scope** (many strategies on paper-only / hedge-fund-sprint blocks).

## Strategy inventory per sparse class

### BOND (n=18)
- Scanner: `alpha_engine/bond_scanner.py` exists
- Strategies coded: `yield_momentum`, `duration_rotation`, `mean_reversion`
- Production wire: **NOT visibly hooked into the hourly production scanner**
- Expansion: turn the 3 bond strategies on, validate emission to `trading_picks`
  with asset_class=BOND. Universe has TLT/IEF/SHY/LQD/HYG/AGG/BND/EMB/MUB
  already.

### ETF (n=87)
- Scanner: `alpha_engine/etf_scanner.py` exists
- Strategies coded: `dual_momentum`, `sector_momentum`, `risk_on_off`,
  `trend_following`
- Paper-blocked (`strategy_blocklist.py:292-293`): `etf_volatility_target`,
  `etf_small_cap_premium`, `etf_gold_miners_ratio`,
  `etf_equal_weight_rotation`, `etf_emerging_market_momentum` (5 more on
  paper-only)
- Expansion: lift paper-only flags one at a time after backtest validation;
  current 4 core strategies should already be producing — investigate why
  n=87 isn't climbing faster.

### FUTURES (silent-dead 5.9% WR)
- No production scanner wired
- Paper-blocked (`strategy_blocklist.py:290-291`): `futures_rsi_divergence`,
  `futures_overnight_gap`, `futures_dollar_trend`, `futures_equity_seasonality`,
  `futures_macd_momentum`, `futures_metals_momentum` (6 strategies)
- Class-blocked in `hedge_fund_sprint` set (`strategy_blocklist.py:88-90`)
- Expansion: requires a separate decision — is FUTURES worth resurrecting, or
  is the 5.9% WR proof the class structurally doesn't fit our edge stack?
  Per Codex governance the class is BLOCKED; no near-term work unless that
  state machine changes.

### Baby-strategies backlog
- **206 .py files in `baby_strategies/`**
- **Zero connection to `dashboard_data.json::systems`** (grep returned no
  matches on systems key)
- Likely zero closed picks emitted → never wired to production scanner →
  dormant incubator
- This is a **massive untapped pipeline** but each strategy needs:
  1. Backtest run with hourly historical data
  2. DSR scoring via `tools/anti_overfit_audit_sidecar.py`
  3. Promotion gate clear (Tier-2 minimum)
  4. Production scanner registration
- Estimated effort: 1-2 strategies/week if backtest harness can be batched

## Recommended next moves (ranked by impact/effort)

| # | Action                                                                       | Effort | Impact                                      |
|---|------------------------------------------------------------------------------|--------|---------------------------------------------|
| 1 | Wire BOND scanner (`alpha_engine/bond_scanner.py`) into production cron      | Low    | n: 18 → 50+ over 2 weeks                    |
| 2 | Audit why ETF n=87 isn't climbing (which of 4 core strategies emits?)        | Low    | Pinpoints emission blocker                  |
| 3 | Batch-backtest top 20 baby_strategies via `anti_overfit_audit_sidecar.py`    | Med    | Surface 1-3 DSR-real candidates             |
| 4 | Lift one paper-only ETF strategy at a time post-backtest validation          | Low    | Diversifies ETF emissions                   |
| 5 | FUTURES — defer pending state-machine review                                 | n/a    | Class blocked per Codex governance          |

## What's NOT blocking

- Symbol universes (all classes have 14-50 symbols available)
- Strategy code (BOND has 3, ETF has 9+ counting paper-only, baby_strategies has 206)

## What IS blocking

- **Production scanner wiring** — strategies exist in code but don't emit to `trading_picks`
- **Backtest harness throughput** — baby_strategies needs 206 backtest runs, no batching infra surfaced
- **Paper-only blocklist scope** — `_PAPER_ONLY_STRATEGIES` at `strategy_blocklist.py:260` has 35+ entries; lifting requires per-strategy DSR validation

## Refs
- `alpha_engine/config.py` (symbol universes)
- `alpha_engine/bond_scanner.py`, `alpha_engine/etf_scanner.py`
- `alpha_engine/strategy_blocklist.py:88-90, 260, 290-298`
- `baby_strategies/` directory (206 .py files)
- Investigator output 2026-05-12 (`af8e750330367cd2c`)

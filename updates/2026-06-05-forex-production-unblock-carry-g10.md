# FOREX Production Unblock — forex_carry_g10

## What was broken

`alpha_engine/config.py` default `FOREX_HARD_DISABLE` was flipped from `1 → 0` on 2026-06-05 after the `forex_carry_g10` extended backtest met unlock thresholds (PF=1.59, WR=60.4%, n=197). However, **this config change alone did NOT unblock forex in production** because three other modules had their own hardcoded forex kills that read `os.environ.get("FOREX_HARD_DISABLE", "1")` directly, ignoring the config file:

1. `audit_trail/quality_gates.py` — the canonical quality gate that blocks picks before DB upsert
2. `alpha_engine/scanner.py` — zero-allocation kill-switch that sets `confidence=0.0` and `continue`s for all `cat == "FOREX"` signals
3. `alpha_engine/mysql_trading_sync.py` — `FOREX_ZERO_ALLOCATE` filter that drops ALL forex picks at the DB sync stage

Additionally:
- `alpha_engine/non_crypto_policy.py` whitelisted only `forex_carry` (original), not `forex_carry_g10`
- `alpha_engine/risk_regime_validator.py` had a hardcoded "no forex" gate
- `audit_trail/dashboard_generator.py` displayed forex as disabled regardless of config

## What was changed

### SSO wiring (single source of truth)
All modules now import `from alpha_engine import config as _ae_config` and read `_ae_config.FOREX_HARD_DISABLE` instead of `os.environ`:

- `audit_trail/quality_gates.py` — `_ae_config.FOREX_HARD_DISABLE`
- `audit_trail/dashboard_generator.py` — `_ae_config.FOREX_HARD_DISABLE`
- `alpha_engine/scanner.py` — `if cat == "FOREX" and _ae_config.FOREX_HARD_DISABLE:`
- `alpha_engine/mysql_trading_sync.py` — `if _raw_cat == "FOREX" and _ae_config.FOREX_HARD_DISABLE:`
- `alpha_engine/risk_regime_validator.py` — `if cat == "forex" and _ae_config.FOREX_HARD_DISABLE:`

### Whitelist update
- `alpha_engine/non_crypto_policy.py` — added `forex_carry_g10` to `_FOREX_ALLOWED`

### Pilot DB write capability
- `verified_strategies/paper_pilot/forex_carry_g10_pilot.py` — added `_write_basket_to_db()` with live yfinance price fetching, deterministic `pick_id` (`fxcarry_{ccy}_{month}`), and `--write-db` CLI flag
- `tools/run_verified_pilots_daily.py` — passes `--write-db` so basket legs auto-insert into `trading_picks` on monthly roll

## Verification

```bash
# Config default
python3 -c "from alpha_engine import config as cfg; assert cfg.FOREX_HARD_DISABLE == False"

# Quality gates uses SSO
grep -c "_ae_config.FOREX_HARD_DISABLE" audit_trail/quality_gates.py  # → 1

# Strategy whitelist
grep "forex_carry_g10" alpha_engine/non_crypto_policy.py  # → present

# End-to-end simulation
python3 -c "
from alpha_engine.non_crypto_policy import evaluate_non_crypto_candidate
r = evaluate_non_crypto_candidate({'symbol':'NZDUSD=X','category':'FOREX','strategy':'forex_carry_g10'})
assert r.get('reason') != 'forex_strategy_consolidation_blocked'
"
```

## Commit range

- `27490cf35a` — config default flip + pilot DB write skeleton
- `1c2698cef7` — SSO wiring for quality_gates + dashboard_generator
- `98f2cfe81a` — production scanner + sync path unblock
- `9bfc6e1d0d` — yfinance live price fetching in pilot
- `05f71916ed` — daily runner `--write-db` wiring + deterministic pick_id
- `f701d070ab` — merge resolution + re-applied quality_gates SSO fix after upstream overwrite

## Risks / follow-up

- **Legacy forex drag:** Live DB still has old bad forex picks (cross_momentum_dxy, etc.) dragging class-level stats to WR=30.5%, PF=0.585. `money_ready_verdict.py` aggregates ALL forex, so FOREX class shows `NOT_READY` until legacy picks age out or are excluded. This does NOT block `forex_carry_g10` from flowing — individual picks pass gates.
- **Daily cap:** `non_crypto_policy.py` `check_emission_gates()` enforces a daily cap that may block forex picks during busy sessions. This is expected runtime behavior, not a hard disable.
- **Confidence floor:** `risk_regime_validator.py` requires confidence >= 0.70. The pilot emits 0.65. May need to bump pilot confidence or lower the validator floor for forex.

## Update 2026-06-05 18:53 UTC

Additional fix pushed: `alpha_engine/non_crypto_policy.py` — added `forex_carry_g10` to `NON_CRYPTO_STRATEGY_POLICY` with thresholds matching `forex_carry`:
- min_confidence: 0.52
- min_rr: 1.20
- min_elite_score: 50
- min_forward_trades: 5
- min_forward_wr: 0.40
- allow_without_forward: True

This resolves the remaining production wiring gap. The scanner now has:
1. Strategy policy thresholds (NON_CRYPTO_STRATEGY_POLICY)
2. Forex class whitelist permission (_FOREX_ALLOWED)
3. Quality gate pass (FOREX_HARD_DISABLE=0 via SSO)
4. Scanner zero-alloc conditional (not blocked)
5. MySQL sync conditional (not dropped at DB stage)
6. Pilot DB write with live yfinance prices + deterministic IDs
7. Daily runner auto-insert on monthly roll

Commit: `3b8bec0447`

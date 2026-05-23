# Synthesis (P5)

## `bond_momentum_longshort_v1` — **MIXED**

Backtest stub PF=1.68/WR=35.5/MDD=28.2/n=149. Cross-test INDEPENDENT (ρ=-0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_term_premium_slope_v1` — **MIXED**

Backtest stub PF=1.13/WR=51.6/MDD=20.9/n=133. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_liquidity_spread_v1` — **MIXED**

Backtest stub PF=0.95/WR=61.7/MDD=14.7/n=101. Cross-test INDEPENDENT (ρ=-0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_regime_duration_v1` — **GO**

Backtest stub PF=2.07/WR=56.8/MDD=19.5/n=75 — clears T2 floor. Cross-test INDEPENDENT (max |ρ|=-0.95). Recommend wire-in pending real BacktestEngine numbers.

**Engine votes:** deterministic_seed: GO

**Wiring plan:**
```
Stage `bond_regime_duration_v1` in `alpha_engine/baby_strats/` (per CLAUDE.md strategy factory S4 pre-emission step). After 30d paper-test + forward-validation: promote to active emission with quality_gates trust_score initialized at 4. Caller: `alpha_engine.smart_picks_engine` via existing strategy registry — no new orchestrator needed.
```

## `bond_credit_spread_term_v1` — **MIXED**

Backtest stub PF=1.49/WR=58.4/MDD=32.7/n=95. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_inflation_rotation_v1` — **MIXED**

Backtest stub PF=1.91/WR=57.2/MDD=34.0/n=56. Cross-test INDEPENDENT (ρ=-0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_momentum_cross_country_v1` — **MIXED**

Backtest stub PF=1.12/WR=57.4/MDD=22.6/n=114. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_liquidity_premium_on_off_v1` — **MIXED**

Backtest stub PF=2.18/WR=48.9/MDD=28.3/n=79. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_macro_factor_duration_v1` — **MIXED**

Backtest stub PF=0.80/WR=46.1/MDD=17.5/n=128. Cross-test INDEPENDENT (ρ=0.94). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_regime_switching_duration_v1` — **MIXED**

Backtest stub PF=1.27/WR=62.3/MDD=23.9/n=56. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_momentum_cross_v1` — **MIXED**

Backtest stub PF=1.23/WR=47.0/MDD=9.8/n=51. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_term_premium_v1` — **MIXED**

Backtest stub PF=2.03/WR=41.5/MDD=26.2/n=91. Cross-test INDEPENDENT (ρ=0.94). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_liquidity_premium_v1` — **MIXED**

Backtest stub PF=1.04/WR=48.6/MDD=13.5/n=115. Cross-test INDEPENDENT (ρ=0.95). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

## `bond_credit_spread_v1` — **MIXED**

Backtest stub PF=1.52/WR=50.1/MDD=27.1/n=79. Cross-test INDEPENDENT (ρ=0.94). Below T2 floor OR overlap warning — needs deeper round before wire-in.

**Engine votes:** deterministic_seed: MIXED

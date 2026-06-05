# Crypto: attach on-chain snapshot for fundamental / HC gates

## What was broken

`fundamental_macro_gates._compute_crypto_fundamental_strength()` only scored three named strategies; production sleeves like `crypto_liquidity_wick_reversal_v1` always got `fundamental_score=None`.

## What changed

- **`crypto_risk_gates.apply_crypto_gates()`** — stamps `pick["extra"]["network_metrics"]` from `genome/data/onchain_cache.json` + live funding rate.
- **`fundamental_macro_gates.py`** — generic path scores picks with `network_metrics` (funding + fear/greed extremes).

## Verify

```bash
python3 -c "import py_compile; py_compile.compile('alpha_engine/crypto_risk_gates.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('alpha_engine/fundamental_macro_gates.py', doraise=True)"
```

## Note

`fundamental_macro_gates.py` is required by `money_ready_verdict.py` on main but was missing from the tree; this PR includes the module plus the network-metrics extension.
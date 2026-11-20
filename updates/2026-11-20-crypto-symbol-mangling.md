# Crypto symbol candidates were mangled (2026-11-20)

**Scope:** `alpha_engine/audit3_selection_alpha.py`,
`tests/test_audit3_selection_alpha.py`.

## What was wrong

`symbol_candidates` stripped the quote with a blunt `s.replace("USD", "")`:

```
"ADAUSDT".replace("USD", "") -> "ADAT"
```

Candidates became `ADATUSDT / ADAUSD / ADAT`, none of which is the real
`ADAUSDT` series name in the price tables, so the pick could not be priced.
The live selection-alpha block named the damage exactly:

```
CRYPTO symbols_requested 57 · symbols_found 36
missing: ADAT, ARBT, AVAXT, BNBT, BTCT, DOGET, DOTT, ETHT, FETT, HYPET …
```

— i.e. *every* missing "symbol" was a base ticker with a stray `T`.

## Change

Strip the quote **suffix** instead:

- ends with `USDT` → drop 4
- ends with `USD` → drop 3
- otherwise unchanged

`ADAUSDT → ADAUSDT/ADAUSD/ADA`, `BTCUSDT → BTCUSDT/BTCUSD/BTC`,
`ETH-USD → ETH-USD/ETHUSDT/ETHUSD/ETH`.

## Verification

`pytest tests/test_audit3_selection_alpha.py tests/test_audit3_coverage_alpha.py tests/test_forward_pf_json_safe.py -q`
→ **24 passed**, including a test that no candidate ends in a stray `<base>T`.

Expected effect on the next ledger: CRYPTO bar coverage should rise above
36/57 and selection alpha will cover more of the 1,723 CRYPTO picks.

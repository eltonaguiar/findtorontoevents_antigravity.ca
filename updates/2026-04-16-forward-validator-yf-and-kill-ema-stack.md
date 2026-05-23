# Commit summary: forward_validator yfinance alignment + kill `futures_ema_stack_momentum`

## Why

1. **`forward_validator.run_generation()` market data**  
   The scanner path resolves symbols via `resolve_yf_symbols()` so yfinance tickers and Binance-only symbols match `ALL_SYMBOLS` keys. Forward validation used `fetch_market_data(all_syms)` on raw keys only, which could **mis-key or drop** frames versus `run_strategies`. Aligning with the scanner keeps validation and ranking on the **same canonical symbol map**.

2. **`rank_and_filter_signals` / falling-knife**  
   The ranker supports optional `market_data` for 200-day SMA checks. Passing `market_data=data` after the remap makes that filter **consistent** with the enriched `data` dict.

3. **`futures_ema_stack_momentum` / `ema_stack_momentum`**  
   Poor realized performance and zombie picks (per internal kill note2026-04-02). Removed from smart-picks **allowlists**, added to **BANNED_SYSTEMS**, and blocked in **forward_test_gates** and **hf_pick_validator** so the same strategy does not leak through alternate paths.

## What changed

| File | Change |
|------|--------|
| `alpha_engine/forward_validator.py` | `resolve_yf_symbols` → fetch → remap to canonical keys; pass `market_data=data` into `rank_and_filter_signals`. |
| `alpha_engine/smart_picks_engine.py` | Ban + allowlist cleanup for EMA-stack futures variants. |
| `audit_trail/forward_test_gates.py` | `BLOCKED_STRATEGIES` + `futures_ema_stack_momentum`. |
| `audit_trail/hf_pick_validator.py` | `_BLOCKED_STRATEGIES` + both variants. |
| `updates/2026-04-15-scanner-noncrypto-strategy-registration-fix.md` | Doc refresh (scanner / non-crypto registration context). |

## How verified

- `python -m py_compile` on all modified Python modules — exit 0.
- `pytest tests/test_adaptive_stops_and_forward_gates.py tests/test_empirical_bayes_and_gates.py` — 10 passed.

## Not in this commit

Local noise (OKX caches, `monitor_log`, generated `audit_dashboard/index.html`) was left unstaged.

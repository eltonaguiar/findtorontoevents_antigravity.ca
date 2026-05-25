# XLI Asset Class Fix — 2026-05-24

## Problem
XLI (Industrial Select Sector SPDR Fund ETF) was tagged as `"asset_class": "CRYPTO"` in `audit_dashboard/data/ai_tournament_picks_latest.json` and all upstream data files. XLI is an ETF, not a cryptocurrency.

## Root Cause
The bug was a **data propagation issue** — the canonical classifier (`alpha_engine/asset_class.py`) correctly classifies XLI as ETF (it's in `ETF_SYMBOLS` frozenset), but the code paths that read upstream pick files didn't validate against it:

1. **`alpha_engine/forward_validator.py` line 65**: The `_emitter_registry_blocks_signal` probe used `signal.get("asset_class", "CRYPTO")` — if a signal had no `asset_class` key (ETF strategies emit `"category": "etf"`), it defaulted to `"CRYPTO"`.

2. **`tools/populate_picks.py` lines 521/558**: When reading `smart_picks.json` or `active_picks.json`, the code used `sp.get("asset_class", "CRYPTO")` or `ap.get("asset_class", ap.get("category", "CRYPTO"))` — trusting the upstream data without validation. If the upstream data had the wrong `asset_class`, it propagated through.

3. **`alpha_engine/data/active_picks.json`**: XLI had `"asset_class": "CRYPTO"` (wrong) while `"category": "etf"` (correct). The scanner correctly sets `category` but some code path incorrectly set `asset_class`.

## Affected Data
- `alpha_engine/data/active_picks.json`: 24 entries fixed (XLI, AMZN, NVDA, QQQ, AMD, AAPL, TSLA, GOOGL, and 16 futures)
- `audit_dashboard/data/ai_tournament_picks_latest.json`: 199 entries fixed
- `data/ai_tournament/submissions/*.json`: 199 entries fixed across 17 files
- `data/ai_tournament/picks_*.json`: 264 entries fixed across 7 files

## Changes

### Code Fixes

#### `alpha_engine/forward_validator.py`
- `_emitter_registry_blocks_signal()`: Now checks `signal.get("asset_class") or signal.get("category")` before defaulting to `"CRYPTO"`. This ensures ETF strategies that emit `"category": "etf"` but no `"asset_class"` key are correctly classified.

#### `tools/populate_picks.py`
- `generate_fallback_picks()`: Both the smart_picks and active_picks paths now validate `asset_class` against the canonical `asset_class_from_symbol()` classifier. If the canonical classifier identifies the symbol as ETF/BOND/EQUITY/FOREX/FUTURES, it overrides any incorrect upstream `asset_class`.

### New Files

#### `tools/dedup_tournament_picks.py`
Deduplicates `ai_tournament_picks_latest.json` by `(symbol, data_source, thesis, entry_price)`, keeping the latest entry. Reduces 1411 picks to 246 (removes 1165 duplicates from repeated submission runs).
- `python tools/dedup_tournament_picks.py` — dry-run
- `python tools/dedup_tournament_picks.py --write` — actually deduplicate

#### `tools/test_xli_classification.py`
Tests asset class classification:
- XLI -> ETF
- All 11 sector ETFs (XLK, XLF, XLE, XLV, XLY, XLP, XLB, XLU, XLC, XLRE, XLI) -> ETF
- BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT -> CRYPTO
- EURUSD=X, GBPUSD=X, USDJPY=X, AUDUSD=X -> FOREX
- GC=F, CL=F, SI=F, NG=F -> futures
- TLT, IEF, SHY, LQD, AGG -> bond

Run with: `python3 -m pytest tools/test_xli_classification.py -v`

### Data Fixes
All misclassified entries in `active_picks.json`, tournament submissions, and picks files were corrected using the canonical classifier.

## Verification
- All 7 classification tests pass (`python3 -m pytest tools/test_xli_classification.py -v`)
- XLI now correctly shows `"asset_class": "ETF"` in all data files
- The dedup script reduces the tournament picks file from 26K+ lines (with 3x duplicates) to a deduplicated version

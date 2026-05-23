# Code Review: Latest Commits (2026-04-17)

**Reviewer:** Claude Opus 4.7  
**Scope:** All code commits from 2026-04-17, including committed fixes and new uncommitted failover / ML drift fixes.  
**Commits reviewed:** `1ec4abb7c3` through `56fcc73f19` (code changes only; auto-generated data commits excluded).

---

## Summary Table

| File / Commit | Change | Verdict | Notes |
|---------------|--------|---------|-------|
| `alpha_engine/production_scanner.py` | Gate 0c R:R<0.6 reject + per-strategy block replacement | ✅ APPROVE (post-fix) | Inception mercury-2 caught `rr_ratio==0` bypass — fixed in `56fcc73f19` |
| `audit_trail/quality_gates.py` | 2 kills + 3 LONG-direction mutates | ✅ APPROVE | Data-driven strategy lifecycle actions |
| `audit_dashboard/template.html` | Neal SyntaxError fix + R:R tooltip + `el` rename | ✅ APPROVE | Critical prod fix, empirically verified |
| `alpha_engine/institutional_metrics.py` | Added `def main()` wrapper | ✅ APPROVE | Fixes ImportError cascading into ALPHA ENGINE runs |
| `.github/workflows/quick-guess-ml.yml` | `cancel-in-progress: true → false` | ✅ APPROVE (with monitor) | Stops 4C/0S chronic cancellation; queue buildup to be monitored |
| `genome/mega_mutation_live_tracker.py` | `np.where` → `np.divide` with mask | ✅ APPROVE | Clean runtime-warning suppression |
| `.github/workflows/validate-hf-asset-class.yml` | Added `pytest` to install step | ✅ APPROVE | Fixes persistent "No module named pytest" failure |
| `.github/workflows/*.yml` (252 files) | Bulk bump checkout/setup-python to v6 | ✅ APPROVE | Node 20 deprecation deadline compliance |
| `alpha_engine/crypto_data_failover.py` | NEW shared multi-source failover module | ✅ APPROVE (post-fix) | Peer-reviewed; minor type-consistency fix applied |
| `crypto_signal_engine/data_fetcher.py` | Wired shared failover into OHLCV + funding | ✅ APPROVE (post-fix) | Peer-found int→str padding bug fixed |
| `crypto_signal_engine/engine.py` | LightGBM schema drift fix (`feature_name` introspection) | ✅ APPROVE | Graceful degradation when model/config mismatch |
| `alpha_engine/funding_rate_scanner.py` | Wired shared failover for funding rates | ✅ APPROVE | Synthesizes Binance-shaped records correctly |
| `alpha_engine/winner_reverse_engineer.py` | Wired shared failover for tickers + klines | ✅ APPROVE | Clean backward-compat fallback retained |
| `.github/workflows/copy-trader-forward-test.yml` | Replaced inline 5-attempt loop with `safe_push.sh` | ✅ APPROVE | Addresses 7-min push cancellation loop |

---

## Detailed Findings

### 1. Gate 0c — R:R Structural-Fail Rejection (`43dcff2197`, `56fcc73f19`)

**What changed:**
- Added Gate 0c in `apply_quality_gates()` to reject picks with `rr_ratio < 0.6`.
- Empirical basis: PF 0.59, gross loss -117.9% over 23 picks in this bucket.

**Initial issue found by peer AI (Inception mercury-2):**
- Original condition `(pick.get("rr_ratio") or 0) > 0` meant `rr_ratio == 0` bypassed the gate.
- `rr_ratio == 0` indicates zero reward (TP equals entry) — a malformed pick that should also be rejected.

**Fix applied (`56fcc73f19`):**
```python
# Before (bug)
elif (pick.get("rr_ratio") or 0) > 0 and float(pick.get("rr_ratio") or 0) < 0.6:

# After (correct)
elif pick.get("rr_ratio") is not None and float(pick.get("rr_ratio") or 0) < 0.6:
```

This preserves the intended emission-time behavior:
- `rr_ratio=None` → BYPASS (downstream geometry validator handles it once TP/SL are populated).
- `rr_ratio=0` → REJECT (malformed, zero reward).
- `0 < rr_ratio < 0.6` → REJECT (catastrophic geometry).
- `rr_ratio >= 0.6` → pass.

### 2. Shared Crypto Data Failover Module (NEW — uncommitted)

**Problem:**
- Binance 451 geo-block hit all US GHA runners on 2026-04-17.
- `crypto_signal_engine` only fell back to `binance_vision` (same IP block → also 451/400).
- No CoinGecko / KuCoin / CryptoCompare attempts were logged → **0 picks generated for the entire run**.
- Funding-rate fetcher similarly exhausted all endpoints.

**Solution:**
- New module `alpha_engine/crypto_data_failover.py` implements a **shared, reusable** failover chain:
  - **Tickers / OHLCV:** Binance fapi/api/api1/api2/api3 → CoinGecko → KuCoin → CryptoCompare
  - **Funding rates:** Binance fapi mirrors → Bybit → OKX → Coinglass (if API key available)
- Features:
  - Persistent per-source **circuit breaker** (3 failures in 60s → 5-min cooldown, stored in `alpha_engine/data/failover_circuit.json`).
  - **CoinGecko throttle** (2.1s between calls) to respect free-tier limits.
  - **Schema validators + normalizers** for every non-Binance source.
  - Zero new pip dependencies (stdlib `urllib.request` only).

**Peer review findings (subagent reviewer):**
- OVERALL: `APPROVE_WITH_SUGGESTIONS`
- **Fixed:** `_ohlcv_shared` in `crypto_signal_engine/data_fetcher.py` was padding short kline rows with integer `0`; changed to `"0"` to match Binance string schema.
- Recommendations noted for future improvement: debounce disk I/O in `FailoverConfig._save()`, add mocked 451/403 tests, document `_normalize_symbol`'s `USD→USDT` behavior.

**Integration coverage:**
- `alpha_engine/winner_reverse_engineer.py` — tickers + klines
- `crypto_signal_engine/data_fetcher.py` — OHLCV + funding
- `alpha_engine/funding_rate_scanner.py` — funding rates

**Test results:**
```
27 passed in 8.71s
```
All normalizer, circuit-breaker, and fallback-progression tests pass.

### 3. LightGBM Schema Drift Fix (`crypto_signal_engine/engine.py`)

**Problem:**
- Production log: `"number of features in data (16) is not the same as it was in training data (13)"`.
- `config.TOP_GAINER_FEATURES` had grown to 16, but the saved model expected 13.
- Result: top-gainer predictions were **silently skipped** every run.

**Fix:**
- Before predicting, introspect the loaded model via `self.lgb_model.feature_name()`.
- Use exactly the feature list the model was trained on.
- If any expected feature is missing from current data, return `[]` with a clear warning (fail-fast instead of silent skip).

This is a **runtime adaptation** fix; the model still needs retraining to align with the current 16-feature config, but predictions will now work correctly with the existing model artifact.

### 4. Workflow / Push-Contention Fixes

**Quick Guess ML Agent (`3a9d8d1d30`):**
- Changed `cancel-in-progress: true → false`.
- Fixes chronic 4C/0S pattern (every run cancelled 7+ min into a push retry loop).
- Trade-off: queued runs may build up during heavy contention. Both DeepSeek and Inception flagged this; it is accepted as the lesser evil versus 100% cancellation.

**Copy Trader Forward Test (uncommitted):**
- Replaced inline 5-attempt `git pull --rebase` + `git push` loop with `.github/scripts/safe_push.sh`.
- `safe_push.sh` provides 15-attempt exponential backoff, 120s sleep cap, and 180s git net timeout — preventing one hanging call from burning the entire job timeout.

**ALPHA ENGINE Live (`alpha-engine-live.yml`):**
- Left unchanged. Prior attempt with `cancel-in-progress: false` caused two runs to stack and both time out at 55+59 min.
- **Recommendation:** reduce cron frequency (e.g., every 2h instead of hourly) or optimize the 17-min MySQL sync step before touching concurrency again.

### 5. Audit Dashboard Pathspec Error

**Observation:**
- Transient `git add pathspec error: alpha_engine/data/funding_rate_picks.json not found` in `audit-dashboard.yml`.
- Already protected by `|| true` in the loop; workflow self-healed next run.
- Root cause was the funding-rate scanner failing to produce output (now fixed via failover module above).
- No workflow change required; the file should now be generated reliably.

---

## Commits to Land

The following files should be committed together to main:

```
alpha_engine/crypto_data_failover.py          (new)
tests/test_crypto_data_failover.py            (new)
alpha_engine/winner_reverse_engineer.py       (integration)
crypto_signal_engine/data_fetcher.py          (integration + int→str padding fix)
crypto_signal_engine/engine.py                (LightGBM schema drift fix)
alpha_engine/funding_rate_scanner.py          (integration)
.github/workflows/copy-trader-forward-test.yml (push-loop fix)
updates/2026-04-17-code-review-latest-commits.md               (this doc)
updates/2026-04-17-crypto-data-failover-shared-module.md       (module doc)
```

**Excluded from this commit:**
- `alpha_engine/crypto_strategies.py` modification (imports `macd_crossover_strategy` — unrelated scope).
- `alpha_engine/macd_crossover_strategy.py` (unrelated new strategy).
- Various backtest JSON artifacts and `tmp_scan_apostrophes.py`.

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| New failover module has runtime bugs in production | Low | 27 unit tests pass; retains legacy fallbacks; circuit breakers prevent hammering dead sources |
| LightGBM introspection fails on old model format | Low | Wrapped in try/except; falls back to config behavior |
| Copy Trader queue still builds up | Low | `safe_push.sh` is already used successfully by other workflows |
| CoinGecko rate-limiting under heavy load | Medium | 2.1s throttle implemented; monitor logs for 429 responses |

---

**Overall verdict:** All reviewed changes are **approved for merge** after the minor padding fix (already applied). The failover module is the highest-leverage change — it directly restores crypto pick generation when Binance geo-blocks fire again.

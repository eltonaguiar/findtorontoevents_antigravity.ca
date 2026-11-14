# CRYPTO Prediction Pipeline — Proposed Fixes
**Audit date:** 2026-11-14  
**Auditor:** Quantitative Engineering  
**Scope:** `alpha_engine`, `audit_trail`, `dashboard_generator`, `ml_gatekeeper`, `smart_picks_engine`

---

## 1. TOP 3 QUICK WINS (< 1 day each)

### QW-1: Fix live price fetcher so PnL stops freezing at entry_price
**What to do**
- Root cause: `audit_trail/universal_pick_resolver.py` (or the server-side price fetcher `audit_trail/fetch_stock_prices.py`) is returning `current_price = None` for crypto, causing the dashboard to fall back to `entry_price` and display 0 % PnL.
- Verify that the crypto price endpoint (Binance / CoinGecko / CCXT) is reachable from the runner. Check API key / rate-limit / IP whitelist.
- If the endpoint is flaky, add a fallback secondary source and a `last_price_update` timestamp so the dashboard can show "stale" instead of fake 0 %.
- **NEARUSDT specific:** debug why its PnL is understated by 0.72 pp — likely a precision / rounding bug in the contract-size or notional calculation for altcoins with low USD value.

**File/location to edit**
- `audit_trail/fetch_stock_prices.py` — crypto price fetch path  
- `audit_trail/universal_pick_resolver.py` — `resolve_current_price()` fallback logic  
- `alpha_engine/pnl_calculator.py` (or equivalent) — notional math for low-price alts

**Expected impact**
- Dashboard PnL becomes truthful instead of falsely flat.
- NEARUSDT PnL accuracy restored.

**Effort estimate**
- 2–4 hours

---

### QW-2: Kill the 5× PF inflation bug in dashboard aggregation
**What to do**
- Dashboard shows PF 1.80; raw DB closed-pick PF is 0.37. This is a ~5× inflation.
- Likely causes: (a) denominated wins counted multiple times per pick (e.g. one TP hit + final close both scored as wins), (b) open/unrealized picks counted in PF numerator but not denominator, (c) AI Challenge or forward-paper trades co-mingled with real picks without tagging.
- Add a `source_tag` filter in `audit_trail/dashboard_generator.py` so only `source IN ('live_picks','closed_ledger')` rows enter PF math.
- Add a guard `COUNT(DISTINCT pick_id)` so a single pick cannot contribute > 1 win or loss.
- Expose both "raw closed-ledger PF" and "dashboard PF" side-by-side for parity checking.

**File/location to edit**
- `audit_trail/dashboard_generator.py` — PF aggregation query  
- `audit_dashboard/template.html` — add a "raw PF" parity column

**Expected impact**
- Dashboard PF becomes honest. Removes false sense of profitability.

**Effort estimate**
- 3–6 hours

---

### QW-3: Purge 8-month-old zombie AI Challenge picks and mark track_level
**What to do**
- AI Challenge crypto picks from ~2026-03 are still `status = ACTIVE`. They have no forward trades, no resolver updates, and pollute the active panel.
- Run a one-off SQL update: `UPDATE picks SET status = 'EXPIRED', exit_reason = 'audit_zombie_purge' WHERE asset_class = 'CRYPTO' AND source = 'ai_challenge' AND created_at < '2026-09-01' AND status = 'ACTIVE'`.
- Then add a cron / nightly job in `tools/db_freshness_check.py` (or a new `tools/crypto_zombie_sweeper.py`) that auto-expires any crypto pick older than N days (suggest 30 days for crypto) with `forward_trades = 0` and `track_level = 'none'`.
- Set `track_level = 'none'` explicitly on AI Challenge picks at ingestion so they never enter the live panel.

**File/location to edit**
- One-off SQL script (ad-hoc, committed to `audit_quickwins/2026-11-14/...`)  
- `tools/db_freshness_check.py` — add zombie-age rule  
- `alpha_engine/ingest_ai_challenge.py` (or wherever AI Challenge rows land) — force `track_level = 'none'`

**Expected impact**
- Active panel drops from fake 3 + zombie N to a clean, trustworthy set.
- Dashboard no longer displays ghost picks.

**Effort estimate**
- 2–4 hours (including test + dry-run)

---

## 2. MEDIUM FIXES (1–3 days)

### MF-1: Repair or retire forward validation for crypto
**What to do**
- All 3 live picks have `forward_validated = false`, `forward_trades = 0`. The forward validator (`alpha_engine/forward_validator.py` or `walkforward_validator.py`) is either not scheduled for crypto assets or the crypto broker/paper-trading adapter is silently failing.
- Option A (repair): wire the crypto forward validator to Binance testnet / paper-trading API and confirm a round-trip order + fill within 1 hour of pick generation.
- Option B (retire): if forward validation is non-viable for crypto due to rate limits or exchange rules, remove the `forward_validated` boolean from the crypto panel and replace it with a `paper_trading_verified` flag fed by a lightweight paper-trading module.

**File/location to edit**
- `alpha_engine/forward_validator.py`  
- `alpha_engine/walkforward_validator.py`  
- `paper_trading/strategies/crypto_paper_adapter.py` (if creating Option B)

**Expected impact**
- Every live crypto pick either has verified forward data or a clearly labeled "unverified" status. No more false negatives.

**Effort estimate**
- 1–2 days

---

### MF-2: Invert the inverted ML confidence calibration
**What to do**
- Current behavior: `conf >= 0.90` → 14.4 % WR; `conf 0.50–0.60` → 60.3 % WR. The model is perfectly backwards.
- Likely causes: (a) label encoding swap (1 = short, 0 = long but mapped incorrectly), (b) confidence derived from the loss of the wrong class, (c) calibration layer applied upside-down.
- Immediate fix: in `ml_gatekeeper/gatekeeper.py`, add a runtime calibration flip: `effective_conf = 1.0 - raw_conf` for crypto-only, with a feature flag `CRYPTO_CONF_FLIP = True`. This is a band-aid but restores directional correctness within hours.
- Proper fix: re-train the crypto-specific confidence head with correct labels and a held-out calibration set (Isotonic or Platt scaling). Store the calibration map in `ml_gatekeeper/crypto_calibration.json`.
- Add an alert in `tools/ml_metrics_ci_summary.py` that fires when highest-confidence bucket WR < lowest-confidence bucket WR.

**File/location to edit**
- `ml_gatekeeper/gatekeeper.py` — confidence routing  
- `ml_gatekeeper/crypto_calibration.json` (new)  
- `tools/ml_metrics_ci_summary.py` — sanity-check alert

**Expected impact**
- ML filter becomes usable: high-confidence picks actually win more often. Expected WR lift from ~14 % to > 50 % for the high-conf cohort.

**Effort estimate**
- Band-aid: 2 hours  
- Proper calibration re-train: 2–3 days

---

### MF-3: Stop Smart Picks from reporting PF 9.69 on 3 rows
**What to do**
- Smart Picks cohort PF 9.69 is driven 91.7 % by `claude_gainer_st` with only 3 closed rows in raw DB. This is a classic "n = 3" survivorship-bias trap.
- Enforce a minimum sample-size gate: `IF n_closed < 20 THEN do NOT report PF, WR, or Sharpe for that source`. Show "insufficient data" instead.
- In `alpha_engine/smart_picks_engine.py`, weight sources by `sqrt(n_closed)` before blending them into the cohort score. A source with 3 rows should contribute ~0 vs a source with 300 rows.
- Add a "data quality" badge to the dashboard: green if n > 50, amber if 20–50, red if < 20.

**File/location to edit**
- `alpha_engine/smart_picks_engine.py` — source-weighting logic  
- `audit_trail/dashboard_generator.py` — sample-size gating  
- `audit_dashboard/template.html` — data-quality badge

**Expected impact**
- Smart Picks PF collapses to an honest number (likely < 1.0). Prevents false allocation of capital to a 3-row mirage.

**Effort estimate**
- 1–2 days

---

## 3. LONG-TERM FIXES (1–2 weeks)

### LF-1: Revive the Alpha Engine for crypto signal generation
**What to do**
- Only 3 cached active picks exist because the Alpha Engine is "dead." This means the scanner (`alpha_engine/scanner.py`, `production_scanner.py`) is either not scheduled for crypto, crashing silently, or producing zero passing signals.
- Re-run `alpha_engine/production_scanner.py` manually with `--asset_class CRYPTO --verbose` and capture the traceback or empty-result reason.
- Common causes: (a) regime filter set to `NEUTRAL` blocks all crypto entries, (b) min-liquidity filter excludes all USDT alts after a volume drop, (c) API key for crypto data expired.
- Fix the root cause, then add a dead-man's switch: if `COUNT(active_picks CRYPTO) = 0` for > 6 hours, alert Discord / email.

**File/location to edit**
- `alpha_engine/production_scanner.py`  
- `alpha_engine/scanner.py` — crypto eligibility filters  
- `alpha_engine/regime_position_sizer.py` — regime gating  
- Alert target: Discord webhook or `tools/alert_manager.py`

**Expected impact**
- Pipeline generates a continuous flow of crypto picks instead of a static 3-pick graveyard.

**Effort estimate**
- 3–5 days

---

### LF-2: Rebuild the crypto prediction model from honest labels
**What to do**
- The inverted confidence (MF-2), the 0.37 PF, and the 35.9 % WR at n = 3705 all suggest the underlying model is not just miscalibrated — it may be mispredicting direction entirely.
- Re-label the last 12 months of crypto picks using intrabar-true exits (the same methodology that produced the 35.9 % WR figure). Train a fresh gradient-boosted or small neural model on features that exclude lookahead bias.
- Use time-series cross-validation (purged k-fold) and enforce a minimum hold-out period.
- Target metric: maximize **calibrated** confidence at PF > 1.2 and WR > 52 % on the hold-out. If unattainable, down-scope to a "contrarian filter" that only blocks the worst picks rather than generating new ones.

**File/location to edit**
- New training pipeline: `ml_models/crypto_retrain_v2.py`  
- Feature store: `ml_features/crypto_features.parquet`  
- Model artifact: `ml_models/artifacts/crypto_v2.pkl`

**Expected impact**
- A model whose high-confidence predictions actually win. Without this, the entire ML gatekeeper is decorative.

**Effort estimate**
- 1–2 weeks

---

### LF-3: End-to-end data-contract test for crypto picks
**What to do**
- Implement a CI-level contract test that runs every hour and asserts:
  1. `active CRYPTO picks > 0` (or alert if zero for > 6 h).
  2. `dashboard PF == closed-ledger PF ± 0.05`.
  3. `MAX(pick_age) < 48 h` for CRYPTO.
  4. `forward_trades > 0` for any pick with `track_level != none`.
  5. `confidence bucket WR` is monotonically increasing with confidence.
- On failure, auto-file a GitHub issue and tag the on-call quant.

**File/location to edit**
- New test suite: `tests/crypto_pipeline_contract_test.py`  
- CI workflow: `.github/workflows/crypto-contract.yml`

**Expected impact**
- Prevents the current class of bugs (frozen prices, inflated PF, zombies) from recurring silently.

**Effort estimate**
- 3–5 days

---

## 4. VERDICT: Is CRYPTO salvageable?

**Short answer:** Yes, but only if the honest numbers are accepted as the baseline.

| Metric | Current | Salvage threshold |
|---|---|---|
| Honest PF (raw DB) | 0.37 | > 1.0 |
| Honest WR | 35.9 % | > 50 % |
| Active picks | 3 (static) | > 10 / day |
| Forward validation | 0 % | > 80 % |
| ML confidence | Inverted | Monotonic |

**What it would take**
1. **Immediate (this week):** Apply QW-1, QW-2, QW-3. This stops the bleeding: no more fake PnL, no more inflated PF, no more zombie picks. Cost: 1 day.
2. **Short-term (next 2 weeks):** Apply MF-2 (flip ML confidence) and MF-1 (repair forward validation). This makes the ML filter and paper-trading layer usable. Cost: 3–5 days.
3. **Medium-term (next month):** Apply LF-1 (revive Alpha Engine) and LF-2 (retrain model). Without these, the pipeline is a fancy dashboard attached to a coin-flip. Cost: 2–3 weeks.

**If we do only the Quick Wins**, the dashboard becomes honest but still unprofitable. That is preferable to the current state of lying about profitability.

**If we do Quick + Medium**, we have a functioning, honest pipeline that may break even or show slight edge if the model retraining succeeds.

**If we do all three tiers**, CRYPTO becomes a genuine, testable, contract-governed prediction product.

**Risk:** The 0.37 PF on 3,705 trades is a strong prior that the current feature set and model architecture lack alpha. Retraining may not reach PF > 1.0. In that case, the honest fallback is to **shut down live crypto picks** and keep the pipeline in paper-trading-only mode until a new alpha source is found.

---

*Document generated 2026-11-14. Review and prioritize before implementation.*

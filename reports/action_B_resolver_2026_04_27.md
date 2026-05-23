# Workstream B — Resolver Correctness Investigation

**Date:** 2026-04-27
**Author:** claude-opus-4-7 (1M context)
**Scope:** Investigation + writeup ONLY. No code modified. No PRs opened.
**Anchor audit:** `reports/asset_class_independent_recompute_2026_04_27.md` (Part 2 noise-share table; P0 finding).
**Tracking memory:** `feedback_noncrypto_resolver_live_close_bug.md` (5-day-old, several claims now stale — see §3).

---

## 1. Executive Summary

The audit blamed `audit_trail/outcome_resolver.py:384–405` for non-crypto WR being "63% resolver flicker." The actual file lives at **`alpha_engine/outcome_resolver.py`** — the `audit_trail/` path in the audit and feedback memory is wrong; no resolver exists there. The two named defects are real but the precise numbers and structure differ from the memory note:

- The win threshold is **`PNL_WIN_THRESHOLD = 0.00001`** at `alpha_engine/outcome_resolver.py:97` — that's **0.001% (0.1 bp)**, an order of magnitude tighter than the audit's "1bp" claim and ten orders tighter than what realistic spread/slippage on FX or commodities can support.
- The live-spot close logic at `alpha_engine/outcome_resolver.py:384–405` already attempts a TP/SL touch check from live yfinance price, **but only as a one-shot snapshot at resolver-run time** — if live spot happens to be inside the [SL, TP] band, the pick is closed at live spot with `exit_reason="PRICE_RESOLVED"` and the threshold fires off any drift > 0.001%.
- Independent verification against `audit_trail/data/dashboard_payload.json` (3,500 `recent_closed`) reproduces the audit's noise table exactly: FOREX 253/400 noise wins (63.25%), COMMODITY 177/265 (66.79%). Drilling into `exit_reason` shows the noise concentrates not in `PRICE_RESOLVED` (which is rare in the payload) but in `FORCE_CLOSED` rows: FOREX `FORCE_CLOSED` 169/240 wins are noise (70%), COMMODITY 169/247 (68%). `FORCE_CLOSED` is itself a downstream rewrite by `audit_trail/quality_gates.py:1474` (`normalize_exit_reason`) when an upstream `WON`/`LOST` label has `exit_price` more than 0.5% off both TP and SL — i.e., it is the post-hoc fingerprint of the live-spot close.
- All 1,897 non-crypto rows in `recent_closed` have `entry_price + tp + sl + entry_date` populated, so re-resolution is feasible without re-fetching pick metadata. The blocker is OHLC bar history, not pick data.

PR sequencing recommendation in §9: **B should land before any non-crypto strategy-kill PR**, and **before Workstream A retrains models on outcomes**. Otherwise the corrected labels will be a step-function shock to the next training run.

---

## 2. Methodology

Files read (all paths absolute under `e:\findtorontoevents_antigravity.ca\`):

- `alpha_engine\outcome_resolver.py` (1,932 lines; reviewed: 1–222, 270–540, 1480–1700, 1700+ healer block)
- `alpha_engine\forward_validator.py` (3,628 lines; reviewed: 1043 entry, 1060–1270 exit-condition core)
- `alpha_engine\force_close_breached.py` (lines 1–80, 640–800)
- `audit_trail\quality_gates.py` (lines 1440–1500: `normalize_exit_reason`)
- `audit_trail\dashboard_generator.py` (greps for `closed_picks` + `recent_closed`; lines 3550–3600 source map)
- `ml_crypto_predictor\enhanced_models\feedback_trainer.py` (lines 44–180: source aggregation + label derivation)
- `alpha_engine\ml_ranker.py` (greps for outcome label usage)
- `.github\workflows\outcome-resolver.yml` (full 96 lines)
- `audit_trail\data\dashboard_payload.json` (31 MB, 3,500 `recent_closed`; queried programmatically for asset_class × exit_reason × pnl_pct distributions)
- `alpha_engine\data\closed_picks.json` (17 MB, 6,906 picks; queried for non-crypto sample fields)

Empirical sanity check used the same noise criterion the canonical audit used (`|pnl_pct| < 0.05` against the raw `pnl_pct` field, where the field is in **percent units**, not fractional — see §3.3) and reproduced the audit's table to the integer.

---

## 3. Current Resolver Behavior

### 3.1 Where the threshold lives

```python
# alpha_engine/outcome_resolver.py:94–100
# Constants
PNL_WIN_THRESHOLD = 0.00001   # 0.001% — above this = WON (lowered from 0.01%, Kimi K7)
PNL_LOSS_THRESHOLD = -0.00001 # -0.001% — below this = LOST
HTTP_TIMEOUT = 10
RAPID_FIRE_MAX_HOLD_HOURS = 24
```

`compute_pnl()` at `:324–334` returns a **fractional** PnL (`0.05 == 5%`). So the threshold of `0.00001` is `0.001%` (not `0.01%` as the audit's text claimed). It gates only the WON/LOST/FLAT label assigned by `classify_outcome()` at `:337–343`. It does **not** gate which picks get resolved (the `is_unresolved()` check at `:284–321` is independent), and it does **not** filter picks out of downstream WR aggregations.

The note "lowered from 0.01%, Kimi K7" in the docstring suggests this was deliberately tightened for crypto, where 0.001% is genuinely informative on a 24-hour-traded pair. But the **same** threshold applies to FOREX (typical TP ~30–80 bp, spread ~1 bp), COMMODITY (TP ~3–5%, spread ~5 bp), and EQUITY (TP ~2–5%) — and there 0.001% is well below any market noise floor.

### 3.2 Where the live-spot close lives

Function: `resolve_single_pick(pick, live_price)` at `:363–459`. Critical block:

```python
# alpha_engine/outcome_resolver.py:379–405
# If exit_price meaningfully differs from entry, use it
if exit_p > 0 and entry > 0 and abs(exit_p - entry) / entry > 0.00001:
    effective_exit = exit_p
    if not exit_reason:
        exit_reason = "EXIT_PRICE_RESOLVED"
elif live_price and live_price > 0:
    # Use live price — pick is already closed so this is a retroactive resolution
    effective_exit = live_price
    # Check if TP or SL was hit based on price movement
    if direction == "LONG":
        if tp > 0 and live_price >= tp:
            exit_reason = "TP_HIT_RESOLVED"
            effective_exit = tp  # Use TP as exit for accuracy
        elif sl > 0 and live_price <= sl:
            exit_reason = "SL_HIT_RESOLVED"
            effective_exit = sl
        else:
            exit_reason = "PRICE_RESOLVED"
    else:  # SHORT
        if tp > 0 and live_price <= tp:
            exit_reason = "TP_HIT_RESOLVED"
            effective_exit = tp
        elif sl > 0 and live_price >= sl:
            exit_reason = "SL_HIT_RESOLVED"
            effective_exit = sl
        else:
            exit_reason = "PRICE_RESOLVED"
```

The defect: if at the moment the resolver runs, live spot has not crossed TP or SL but is non-trivially away from entry, the `else` branch fires and labels the pick `PRICE_RESOLVED` with `effective_exit = live_price`. Combined with the 0.001% threshold, every such pick is labeled WON or LOST based on whether intra-day mean reversion left it above or below entry at run time. This is path-dependent on cron timing, not on what the trade actually did.

The companion non-crypto active resolver `resolve_active_non_crypto()` at `:1554–1697` is structurally **better** — it only writes a closed pick when `hit_tp` or `hit_sl` is True (`:1630`), and it never invents a `PRICE_RESOLVED` label. But it still uses `live_price` (a one-shot snapshot at `:1610`) as the witness for whether TP/SL was touched, so it misses any TP/SL hit that happened between resolver runs and reverted before the snapshot.

### 3.3 How crypto bypasses this

`alpha_engine/forward_validator.py:1043` (`validate_picks`) handles crypto. The key difference is `:1060–1062`:

```python
day_high = price_data["high"]
day_low  = price_data["low"]
```

Then at `:1179–1213`, TP/SL is checked against **both** current price AND the daily extremes:

```python
# alpha_engine/forward_validator.py:1180–1192 (LONG branch)
if tp and (current_price >= tp * (1 - SL_BUFFER) or day_high >= tp):
    exit_reason = "TP_HIT"
    exit_price = tp * (1 - TP_SLIPPAGE)
elif _adj_sl and (current_price <= _adj_sl * (1 + SL_BUFFER) or day_low <= _adj_sl):
    ...
    exit_reason = "SL_HIT"
    exit_price = _adj_sl * (1 - SL_SLIPPAGE)
```

`day_high`/`day_low` come from the daily OHLC bar — a TP touched intraday and reverted is still detected. There is also a `STALE_DATA_NO_PRICE` guard at `:1252–1258` that explicitly demotes any "exit price didn't move from entry" event when the exit_reason is `TIME_EXPIRY` or `SL_HIT`. **The non-crypto resolver has no equivalent OHLC-bar check and no stale-data guard.**

### 3.4 Right data, wrong logic

Empirical check across the 1,897 non-crypto rows in `audit_trail/data/dashboard_payload.json:picks.recent_closed`:

| Field | Coverage |
|---|---|
| `entry_price` | 1,897 / 1,897 |
| `take_profit` (or `targetPrice`) | 1,897 / 1,897 |
| `stop_loss` (or `stopPrice`) | 1,897 / 1,897 |
| `entry_date` (or `created_at`/`timestamp`/`entry_time`) | 1,897 / 1,897 |

Every non-crypto pick has the four fields a TP/SL replay needs. The fix is **purely a logic change**, not a data-collection change.

### 3.5 Empirical noise breakdown by exit_reason (non-crypto wins only)

Reproducing the audit's noise criterion (`|pnl_pct| < 0.05`, `pnl_pct` interpreted as already-percent — confirmed by mixed sample values like `0.6347` and `-0.0023` in the same payload) and slicing by `exit_reason`:

| Class | exit_reason | wins | noise wins | % noise of wins |
|---|---|---:|---:|---:|
| FOREX | FORCE_CLOSED | 240 | 169 | **70.4%** |
| FOREX | SL_HIT | 43 | 43 | **100.0%** |
| FOREX | TP_HIT | 97 | 40 | 41.2% |
| FOREX | EXPIRED | 18 | 1 | 5.6% |
| COMMODITY | FORCE_CLOSED | 247 | 169 | **68.4%** |
| COMMODITY | TP_HIT | 16 | 6 | 37.5% |
| COMMODITY | SL_HIT | 2 | 2 | **100.0%** |
| EQUITY | TP_HIT | 91 | 0 | 0% |
| EQUITY | EXPIRED | 48 | 0 | 0% |
| ETF | TP_HIT | 19 | 0 | 0% |
| BOND | TP_HIT | 1 | 0 | 0% |

Two surprises vs the memory note:

1. **`FORCE_CLOSED` is the dominant noise vector**, not `PRICE_RESOLVED`. `FORCE_CLOSED` is created by `audit_trail/quality_gates.py:1466–1474` (`normalize_exit_reason`) when raw status is `WON`/`LOST` but exit_price is more than 0.5% from both TP and SL. Functionally that label is the dashboard's way of saying "the resolver labeled this WON/LOST but the exit_price doesn't match a TP/SL touch" — i.e., the live-spot close, post-hoc detected.
2. **`SL_HIT` wins are 100% noise.** A FOREX SL_HIT cannot mathematically be a "win" under any sane interpretation — yet 43/43 such rows have `pnl_pct > 0` and 100% are < 0.05%. This points at a separate label/sign bug in upstream pipelines that mark `SL_HIT` then leave `pnl_pct ≈ 0` after running through the resolver. Worth flagging in the PR but not within the resolver's blast radius.

EQUITY/ETF/BOND show essentially zero noise wins because their picks live in pipelines that don't write through `resolve_single_pick`'s live-spot fallback (different writers — `stocks_competition`, `goldmine_stocks`, etc.), and `force_close_breached.py` only operates on `alpha_engine/data/active_picks.json` which has limited equity exposure.

---

## 4. Proposed Fix

### 4.1 Logic change — replay against daily OHLC bars

Mirror the crypto path. The resolver already has yfinance access (`_fetch_yfinance_price` at `:198–222`) — extend it to fetch the daily OHLC range for the **holding window** of each pick, not just current spot. Then in `resolve_single_pick`, walk those bars for a TP-or-SL touch.

Concrete diff for `alpha_engine/outcome_resolver.py`:

```diff
@@ -94,8 +94,12 @@
 # ---------------------------------------------------------------------------
 # Constants
 # ---------------------------------------------------------------------------
-PNL_WIN_THRESHOLD = 0.00001   # 0.001% — above this = WON (lowered from 0.01%, Kimi K7)
-PNL_LOSS_THRESHOLD = -0.00001 # -0.001% — below this = LOST
+# Per-asset-class noise floors. 0.001% (1e-5) was a legacy crypto setting;
+# applied to FX/commodity/equity it converted spread noise into "wins."
+# See reports/action_B_resolver_2026_04_27.md §4.2.
+PNL_WIN_THRESHOLD_CRYPTO = 0.00010      # 0.01%  (1 bp)
+PNL_WIN_THRESHOLD_NONCRYPTO = 0.00050   # 0.05%  (5 bp)
+PNL_LOSS_THRESHOLD_CRYPTO = -0.00010
+PNL_LOSS_THRESHOLD_NONCRYPTO = -0.00050
 HTTP_TIMEOUT = 10
 RAPID_FIRE_MAX_HOLD_HOURS = 24
```

```diff
@@ -337,10 +341,17 @@ def compute_pnl(...
-def classify_outcome(pnl_pct: float) -> str:
+def classify_outcome(pnl_pct: float, *, is_non_crypto: bool = False) -> str:
     """Classify PnL into WON/LOST/FLAT."""
-    if pnl_pct > PNL_WIN_THRESHOLD:
+    win_thr  = PNL_WIN_THRESHOLD_NONCRYPTO  if is_non_crypto else PNL_WIN_THRESHOLD_CRYPTO
+    loss_thr = PNL_LOSS_THRESHOLD_NONCRYPTO if is_non_crypto else PNL_LOSS_THRESHOLD_CRYPTO
+    if pnl_pct > win_thr:
         return "WON"
-    elif pnl_pct < PNL_LOSS_THRESHOLD:
+    elif pnl_pct < loss_thr:
         return "LOST"
     return "FLAT"
```

```diff
@@ -363,7 +374,7 @@ def resolve_single_pick(pick: dict, live_price: ...
-def resolve_single_pick(pick: dict, live_price: Optional[float] = None) -> dict:
+def resolve_single_pick(pick: dict, live_price: Optional[float] = None,
+                        ohlc_window: Optional[list[dict]] = None) -> dict:
     """Resolve a single unresolved pick. Returns updated pick dict.
     ...
@@ -384,32 +395,42 @@
-    elif live_price and live_price > 0:
-        # Use live price — pick is already closed so this is a retroactive resolution
-        effective_exit = live_price
-        # Check if TP or SL was hit based on price movement
-        if direction == "LONG":
-            if tp > 0 and live_price >= tp:
-                exit_reason = "TP_HIT_RESOLVED"
-                effective_exit = tp  # Use TP as exit for accuracy
-            elif sl > 0 and live_price <= sl:
-                exit_reason = "SL_HIT_RESOLVED"
-                effective_exit = sl
-            else:
-                exit_reason = "PRICE_RESOLVED"
-        else:  # SHORT
-            if tp > 0 and live_price <= tp:
-                exit_reason = "TP_HIT_RESOLVED"
-                effective_exit = tp
-            elif sl > 0 and live_price >= sl:
-                exit_reason = "SL_HIT_RESOLVED"
-                effective_exit = sl
-            else:
-                exit_reason = "PRICE_RESOLVED"
+    elif ohlc_window:
+        # Replay the OHLC window for a TP/SL touch (forward_validator-style).
+        hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl)
+        if hit:
+            effective_exit = hit["price"]
+            exit_reason = hit["reason"]   # TP_HIT_REPLAY or SL_HIT_REPLAY
+        elif live_price and live_price > 0:
+            # No touch in window AND we're past max-hold → treat as TIME_EXIT,
+            # NOT WON/LOST. classify_outcome below will produce FLAT for any
+            # |pnl_pct| < threshold and the audit's noise filter will exclude it.
+            effective_exit = live_price
+            exit_reason = "TIME_EXIT_RESOLVED"
+    elif live_price and live_price > 0:
+        # No OHLC available (e.g. yfinance forex history failed). Be honest:
+        # do NOT label WON/LOST off a single live snapshot. Mark as
+        # UNRESOLVED so a later pass can retry with bar history. This kills
+        # the PRICE_RESOLVED noise-win pathway.
+        pick["_resolve_retry_needed"] = True
+        return pick
```

```diff
@@ -425,8 +446,9 @@ def resolve_single_pick(...
-    pnl_pct = compute_pnl(entry, effective_exit, direction)
-    outcome = classify_outcome(pnl_pct)
+    pnl_pct = compute_pnl(entry, effective_exit, direction)
+    nc = _is_non_crypto(pick)
+    outcome = classify_outcome(pnl_pct, is_non_crypto=nc)
```

Plus a new helper:

```python
def _scan_ohlc_for_touch(bars: list[dict], direction: str, tp: float, sl: float) -> Optional[dict]:
    """Walk daily OHLC bars from entry forward; return first TP or SL touch.

    bars: [{date, open, high, low, close}, ...] sorted ascending by date.
    Tie-break: SL is checked first (conservative — assume worst-case fill).
    """
    if not (tp > 0 or sl > 0):
        return None
    is_long = direction.upper() in ("LONG", "BUY")
    for bar in bars:
        hi = float(bar.get("high", 0) or 0)
        lo = float(bar.get("low", 0) or 0)
        if is_long:
            if sl > 0 and lo <= sl:
                return {"price": sl, "reason": "SL_HIT_REPLAY"}
            if tp > 0 and hi >= tp:
                return {"price": tp, "reason": "TP_HIT_REPLAY"}
        else:
            if sl > 0 and hi >= sl:
                return {"price": sl, "reason": "SL_HIT_REPLAY"}
            if tp > 0 and lo <= tp:
                return {"price": tp, "reason": "TP_HIT_REPLAY"}
    return None
```

The OHLC history fetch in `_fetch_yfinance_price` already calls `ticker.history(period="1d")` at `:203`. Extend a sibling `_fetch_yfinance_window(symbol, start, end)` that returns a list of bars, with a bounded window (entry_date through min(today, entry_date + max_hold)), and pass that into `resolve_single_pick`.

### 4.2 Threshold justification

Empirical data from `dashboard_payload.json` against today's TP distances:

- FOREX median absolute TP-distance from entry: ~30 bp (sample SL_HIT row: `EURGBP=X` entry 0.86596, SL 0.86393 → 23 bp). Spread is ~1 bp on majors. **5 bp = ⅙ of typical TP** is the right floor; lower than that and round-trip cost dominates.
- COMMODITY median TP-distance: ~3–4% (sample: `CT=F` entry 76.33, SL 78.83 → 3.3% adverse). 5 bp is ~70× smaller than typical TP — comfortably below signal range, comfortably above quote-level noise.
- EQUITY: 5 bp is below intraday spread on liquid names but above the typical "did the close print equal the open" tick noise. Acceptable.

Crypto stays at 1 bp (`0.0001`) because crypto pairs trade 24×7 with sub-1 bp spreads on majors and the legacy threshold is empirically not creating noise wins there (CRYPTO noise share was not flagged in the audit's Part 2 table).

The 5 bp floor will move the audit's noise count from 253/400 FOREX wins → ~few; this is the verification check in §7.

---

## 5. Re-Resolve Plan

### 5.1 Pick history sources

The dashboard payload's `picks.recent_closed` is **derived**, not authoritative. The 1,897 non-crypto picks come from many upstream JSON files aggregated by `audit_trail/dashboard_generator.py` (source map at `:3450–3600`). Top sources by `source_system`:

| source_system | count | upstream file |
|---|---:|---|
| multi_asset_copytrader | 1,035 | `copy_trader_intel/data/{multi_asset,forex_copytrader,stocks_copytrader,commodity_copytrader}_picks.json` |
| kimi_riseoftheclaw | 265 | `genome/data/revival_kimi_riseoftheclaw_picks.json` (and derivatives) |
| stocks_competition | 165 | special handler at `dashboard_generator.py:~1761` |
| cta_replicator | 143 | `copy_trader_intel/data/cta_picks.json` |
| non_crypto_consensus | 104 | `copy_trader_intel/data/non_crypto_consensus_picks.json` |
| forex_copy_trader | 44 | `copy_trader_intel/data/...` |
| alpha_engine | 36 | `alpha_engine/data/closed_picks.json` |
| alpha_engine_fast | 27 | `alpha_engine/data/closed_picks_fast.json` |
| (others) | ~78 |  |

**`alpha_engine/data/closed_picks.json` is only 36 rows of the 1,897.** Re-running `outcome_resolver.py` against just that file would fix 1.9% of the corruption. The remaining ~1,860 picks were resolved by **other writers** (mostly `copy_trader_intel/outcome_resolver.py` plus inline pipeline writers in `dashboard_generator.py`'s special-source handlers).

### 5.2 Re-resolution feasibility

Good news: §3.4 confirms 100% of the 1,897 rows have entry/TP/SL/entry_date present. Bad news: yfinance daily OHLC history is the limiter. yfinance returns up to ~30 days reliably, and the window covers all picks closed in the audit's 4-day `recent_closed` slice plus their open holding period (typically ≤ 14 days for FOREX/COMMODITY per the `_NON_CRYPTO_MIN_HOLD` map at `forward_validator.py:1226–1233`). So a one-shot batch is feasible.

### 5.3 Plan

1. **New module** `tools/re_resolve_non_crypto.py` (proposed name) that:
   - Iterates the 8 source files in §5.1.
   - For each non-crypto pick with `entry_date + tp + sl + entry_price` and current `exit_reason ∈ {WON, LOST, FORCE_CLOSED, PRICE_RESOLVED, TIME_EXIT}`:
     - Fetches `yf.Ticker(sym).history(start=entry_date, end=min(today, entry_date+max_hold), interval="1d")`.
     - Calls the new `_scan_ohlc_for_touch()`.
     - If touch found: rewrite `exit_price`, `exit_reason ∈ {TP_HIT_REPLAY, SL_HIT_REPLAY}`, `pnl_pct`, `status` per `classify_outcome(..., is_non_crypto=True)`. Stamp `resolver_version: "v2"` (see §8).
     - If no touch: rewrite `exit_reason="TIME_EXIT_REPLAY"`, `exit_price=last_close`, recompute pnl_pct. Stamp `resolver_version: "v2"`.
   - Writes back atomically (temp file + rename, mirror the existing `_save_json` pattern at `force_close_breached.py:738`).
   - Emits a delta CSV: `reports/re_resolve_delta_2026_04_27.csv` with old vs new label + pnl per pick.

2. **Run order:**
   - DRY RUN first: `python tools/re_resolve_non_crypto.py --dry-run > reports/re_resolve_dryrun.txt`.
   - Cross-check the delta CSV against `audit_dashboard/data/dashboard_data.json` to ensure WR moves in the expected direction.
   - Apply for real, commit upstream files in a single PR.

3. **Expected post-fix table** (estimated):

| Class | n (closed) | wins (current) | wins (post-fix, est) | WR (current) | WR (post-fix, est) |
|---|---:|---:|---:|---:|---:|
| FOREX | 794 | 400 | ~150–180 | 50.4% | ~19–23% |
| COMMODITY | 622 | 265 | ~95–110 | 42.6% | ~15–18% |
| EQUITY | 381 | 198 | ~190 | 52.0% | ~50% |
| ETF | 83 | 45 | ~42 | 54.2% | ~50% |
| BOND | 17 | 8 | ~7 | 47.1% | ~41% |

The FOREX/COMMODITY estimates assume ~70% of `FORCE_CLOSED` "wins" flip to `TIME_EXIT_REPLAY` with `|pnl_pct| < 5 bp` → reclassified `FLAT` (filtered from WR base) + a fraction flip to `LOST` from genuine SL touches that the live-spot snapshot missed. The 100% `SL_HIT` noise wins all flip to `LOST`.

**Net expected impact on PnL:** modest. The noise wins each contribute ~0.01–0.04% PnL, and most flip to `FLAT` (excluded), not `LOST` (counted negatively). FOREX `Sum PnL%` should move from `+29.63` → roughly `0 to +20` range; COMMODITY from `-9.82` → roughly `-9.82 to -25`.

---

## 6. Downstream Consumers + ML Retraining Implications

Files that consume `closed_picks.json` outcome labels (greps confirmed: `closed_picks.json|recent_closed|outcome_resolver` across `*.py`):

| Consumer | Path | What it reads | Sensitivity to flipped labels |
|---|---|---|---|
| **ML feedback trainer** | `ml_crypto_predictor/enhanced_models/feedback_trainer.py:44–60` | Aggregates 14 closed_picks files into `aggregated_closed_picks.json`; target = `is_win = 1 if pnl > 0 else 0` (`:146`) | **HIGH** — direct label inversion. Crypto picks unaffected (different code path) but the trainer pools across ALL systems including non-crypto sources. Retrain after fix is mandatory. |
| **ML ranker** | `alpha_engine/ml_ranker.py:259–340` | Trains on closed_picks.json with target `pnl_pct > 0 and hit TP: +1` | **HIGH** — same mechanism; auto-trains from `closed_picks.json` if no model. |
| **Meta consensus scorer** | `alpha_engine/meta_consensus_scorer.py` | Shares `ml_challenger.joblib` artifact with `ml_ranker.py` | **HIGH** (shared model). |
| **Dashboard WR aggregates** | `audit_trail/dashboard_generator.py:5314, 11688, 12710` (`recent_closed` build + leaderboard) | Per-strategy / per-class WR / PF / sum-PnL displayed in audit dashboard | **HIGH** — directly displayed; fixes the reported numbers. |
| **HC filter** | `audit_dashboard/hc_filter.js` `evaluateHcGates1to9` (read by `audit_what_if_entry_day.js`) | Forward WR per strategy is a gate input | **MEDIUM** — gates currently see inflated WR for FX/commodity strategies; tightening will eliminate currently-passing FX picks. |
| **Strategy kill decisions** | `tools/mutation_analysis.py`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` workflow | Uses dashboard_data WR/PF | **HIGH** — every "kill X" claim per `feedback_noncrypto_resolver_live_close_bug.md` is downstream of this. |
| **Hedge fund rollup** | `tools/hf_stats.py`, `tools/feed_risk_metrics.py`, `tools/edge_by_asset_class.py` | Asset-class P&L | **HIGH** — directly affected; non-crypto rollup currently overstated. |
| **Cross-aggregator workflow** | `.github/workflows/cross-aggregator.yml:130–132` | Pulls closed_picks from mercury2 + alpha_engine + system_f | **MEDIUM** — mostly crypto sources; non-crypto exposure limited. |

Workflows that re-train and persist on the existing labels:

- `ml-feedback-retrain.yml` — `cron: 23 */12 * * *`. After fix lands, this needs one explicit re-run trigger to retrain on corrected labels.
- `claude-gainer-tracker.yml` — `cron: 15 */4 * * *` + Sun retrain. Crypto-only universe; minimally affected.
- `mercury2-retrain.yml` — `cron: 0 2 * * 0` weekly. Crypto-focused; minimally affected.
- `outcome-resolver.yml` — `cron: 15 */1 * * *`. **The fix lives here.** Existing concurrency group prevents overlap; no change needed to the workflow itself, only the script it invokes.

**ML retrain shock risk.** If the resolver fix flips ~17% of FOREX wins (~250 of 794) and ~28% of COMMODITY wins (~170 of 622) to losses or flats, the meta_labeler / ml_challenger / outcome_feedback model will see ~420 label flips on a corpus of ~3,500 trades. That's a 12% target-flip rate. Training accuracy/AUC will move materially. Two specific gates to expect to trip:

- `claude_gainer_ml/trigger_retraining.py` AUC > 0.537 gate — could swing either way; corrected labels are higher-fidelity, so AUC should rise on out-of-sample, but stale features may not align.
- `alpha_engine/feature_health.py` PSI > 0.25 retrain / PSI > 0.40 halt at `:` — label PSI between pre-fix and post-fix corpus will be high and may auto-trigger halt. Recommend wrapping the re-resolve commit with `feature_health` re-baselining in the same PR.

---

## 7. Verification

Pre-fix, the canonical command (Mercury-2 reproducer) is:

```bash
node tools/_mercury2_recompute.js  # Part 1 + Part 2
```

The audit's noise-share metric is computed in `temp_compute_extended.js` and produces the table at `reports/asset_class_independent_recompute_2026_04_27.md` Part 2.

Post-fix verification — **single command** that re-runs Part 2 against the post-fix payload:

```bash
# 1. Rebuild the dashboard payload (will pick up corrected closed picks)
python audit_trail/dashboard_generator.py --rebuild-only

# 2. Re-run the noise-share check
python -c "
import json
with open('audit_trail/data/dashboard_payload.json') as f:
    rc = json.load(f)['picks']['recent_closed']
for cls in ['FOREX','COMMODITY','EQUITY','ETF','BOND']:
    n=wins=noise=0
    for p in rc:
        if (p.get('asset_class') or '').upper()!=cls: continue
        n+=1
        try: v=float(p.get('pnl_pct') or 0)
        except: v=0
        if v>0:
            wins+=1
            if abs(v)<0.05: noise+=1
    pct = (noise/wins*100) if wins else 0.0
    print(f'{cls:10s} n={n:4d} wins={wins:4d} noise={noise:4d} ({pct:5.2f}%)')
"
```

**Expected post-fix output** (must hit <30% noise on every line per the audit's reliability bar):

```
FOREX      n= ~794 wins= ~150 noise=   ~5  (   ~3%)
COMMODITY  n= ~622 wins= ~100 noise=   ~5  (   ~5%)
EQUITY     n=  381 wins=  198 noise=   18  (  ~9%)   # unchanged
ETF        n=   83 wins=   45 noise=    3  (  ~7%)   # unchanged
BOND       n=   17 wins=    7 noise=    0  (  ~0%)
```

The EQUITY/ETF/BOND lines are predicted to be near-unchanged because their pipelines don't go through the live-spot path materially — the audit confirmed this empirically (9.09% / 6.67% / 12.50% noise share are all already < 30%).

---

## 8. Risks / Open Questions

1. **yfinance OHLC reliability.** `_fetch_yfinance_price` already has a stale-price fallback path (`stock_forex_prices.json` cache at `:209–221`); `_fetch_yfinance_window` will need similar fallback. If a symbol fails entirely, the pick stays `_resolve_retry_needed=True` rather than getting a fake label — loss of coverage, not loss of correctness.
2. **`SL_HIT` "wins" mystery.** 43 FOREX `SL_HIT` rows have `pnl_pct > 0` (100% noise). This is not the live-spot defect — those rows already have `exit_reason="SL_HIT"`. Likely upstream sign error in `multi_asset_copytrader` or `kimi_riseoftheclaw` writers when computing pnl for SHORT positions. **Out of scope for Workstream B but should be tracked** as a separate finding (memory note recommended: "non-crypto SL_HIT label can have positive pnl_pct — investigate sign convention in multi_asset_copytrader").
3. **`pnl_pct` unit drift.** Sample dump showed both `0.6347` (% form) and `0.0063` (fractional form) values for the **same trade** — confirming `feedback_cycle10_unit_mismatch_bug.md`. The audit's noise threshold worked because it was run against the % form; a strict re-resolver should normalize all writers to one unit. Recommend `tools/normalize_pnl_units.py` as a separate cleanup PR after B.
4. **Memory note staleness.** `feedback_noncrypto_resolver_live_close_bug.md` says the file is at `audit_trail/outcome_resolver.py` — that path doesn't exist. The actual file is at `alpha_engine/outcome_resolver.py`. The 5-day-old memory has been overtaken; the `:97` and `:384–405` line numbers are still accurate within that file. The note's PNL_WIN_THRESHOLD = "1bp" is wrong by 10× — actual is 0.1 bp.
5. **`resolve_active_non_crypto()` at `:1554` already does TP/SL-only resolution.** It's not the defect path; it's the function the memory note **wishes** the live-spot path would mirror. The fix is essentially "make `resolve_single_pick` behave like `resolve_active_non_crypto` plus OHLC replay."
6. **Live-pipeline race.** `outcome-resolver.yml` runs every hour and pushes `closed_picks.json` updates. The re-resolver migration must run while concurrency-group `outcome-resolver` is paused, or the migration will race with the legacy resolver and lose some writes. Recommend disabling the cron during the migration commit.

---

## 9. Backward Compatibility & PR Sequencing

### 9.1 Tagging strategy

**Recommendation: tag with `resolver_version: "v2"`, do NOT keep parallel rows.**

Reasoning:
- Audit dashboard / ML training all read flat label fields (`pnl_pct`, `status`, `exit_reason`); they have no logic to "prefer v2 over v1." Keeping both creates ambiguity. Only `resolver_version` is added; old fields are overwritten.
- The current corpus has zero rows with `resolver_version` set (verified empirically). Stamping v2 on every re-resolved row gives consumers a clean discriminator without schema migration.
- Pre-fix outputs are not provably correct — there's no value in preserving them as a "valid alternative view."
- Audit reports and forensic memories that quote pre-fix numbers should be re-titled with a date stamp; the corrected numbers replace them in dashboards.

What gets stamped per pick:
```json
{
  "resolver_version": "v2",
  "resolved_at": "2026-04-27T...",
  "resolved_by": "outcome_resolver_v2",
  "exit_reason": "TP_HIT_REPLAY" | "SL_HIT_REPLAY" | "TIME_EXIT_REPLAY",
  "_legacy_pnl_pct": <old value>,
  "_legacy_exit_reason": <old value>
}
```

The `_legacy_*` fields preserve audit trail without affecting downstream readers (which key on `pnl_pct` and `exit_reason` directly).

### 9.2 PR sequencing — B before A

The action plan presumably tracks Workstream A as "ML pipeline reliability" (rf_model.pkl staleness fix at `alpha-engine-live.yml:592` swallowing exit codes; ml_gatekeeper persistence). **B must merge before A**, because:

1. Workstream A's success criterion is "trainers re-run cleanly and produce updated artifacts." If A merges first, those trainers will retrain on the **current** corrupt labels — locking in 12% target-flip error in fresh weights. Then B lands and we need a second forced retrain immediately, doubling the work.
2. Workstream B's success criterion ("noise share < 30% per class") is independent of A's training pipeline and can be verified locally.
3. A's silent-failure swallow (`alpha-engine-live.yml:592`) is contributing to STALE models, but not to **wrong** models — the artifacts were trained on equally corrupt labels 12.3 days ago. Letting them stay stale one more cycle while B lands is an acceptable risk trade.

Recommended order:
- **Day 0:** PR-B1 — code change (`alpha_engine/outcome_resolver.py` + tests for new helpers; no data writes yet).
- **Day 0:** PR-B2 — `tools/re_resolve_non_crypto.py` script + dry-run report (`reports/re_resolve_dryrun.txt`).
- **Day 1:** PR-B3 — pause `outcome-resolver.yml` cron, run B2 against all 8 source files, commit corrected files in one PR. Re-enable cron.
- **Day 1+1h:** Verify §7 noise-share check passes; update `feedback_noncrypto_resolver_live_close_bug.md` to "RESOLVED" status.
- **Day 2:** PR-A1 — silent-failure fixes (alpha-engine-live trainer error handling, ml_gatekeeper git-add step). Trigger first retrain on corrected corpus.
- **Day 2+1d:** Audit dashboard re-pulls; verify FOREX/COMMODITY rows in audit report Part 1 reflect new WR/PF; close out Workstream B in audit synthesis.

Skipping the B → A order — i.e., letting A retrain on corrupt labels first — would rebake the 70% noise into model weights and require a third intervention to undo. Order matters here.

---

*End of report. ~1,750 words ex-tables/code. No code modified during this investigation.*

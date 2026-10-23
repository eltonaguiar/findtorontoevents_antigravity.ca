# Audit Bug Anchor Summary — P&L Impact Bugs on findtorontoevents.ca/audit

## Goal
Deep audit of `findtorontoevents_antigravity.ca` codebase for ALL bugs affecting P&L calculations on `findtorontoevents.ca/audit`, categorized as (1) strategy-inflating bugs, (2) strategy-deflating bugs, each with file/line/severity/impact/fix.

## Constraints & Preferences
(none)

## Progress

### Done
- Explored directory structure: `audit_trail/` (`dashboard_generator.py` 18,720 lines, `quality_gates.py` 11,173 lines), `alpha_engine/` (`forward_validator.py` 3,756 lines, `slippage_model.py` 637 lines), `tools/` (`strategy_kill_switch.py`, `stamp_entry_conditions.py`).
- Confirmed key files exist: `tools/stamp_entry_conditions.py`, `alpha_engine/forward_validator.py`, `audit_trail/quality_gates.py`, `audit_trail/dashboard_generator.py`, `audit_trail/universal_pick_resolver.py`, `alpha_engine/charter_slippage.py`, `alpha_engine/slippage_model.py`.
- Found and read `tp_sl_bug_report.json` — 1194/2648 picks have suspicious SL-closer-but-TP-hit pattern.
- Traced P&L computation paths: `forward_validator.py` closed_pick stats → strategy_performance.json / pf_registry.json; `dashboard_generator.py` verdict aggregate → dashboard_data.json → /audit frontend; `universal_pick_resolver.py` TP/SL intrabar resolution → at_pick_outcomes (MySQL) + closed_picks.json.
- Verified `_ENTRY_ANCHORED` default is `"1"` (ON) at `universal_pick_resolver.py:615`.
- Identified MySQL P&L feed: `at_pick_outcomes` table in `ejaguiar1_stocks`, used by `tools/strategy_kill_switch.py` (PRIMARY: trading_picks, SECONDARY: at_pick_outcomes). The `goldmine_tracker.php` serves legacy `gm_unified_picks`.

### In Progress
- Reading quality_gates.py D/R/L gate P&L filtering rules.

### Blocked
- dashboard_generator.py (18,720 lines) and quality_gates.py (11,173 lines) too large to grep exhaustively.

## Key Decisions
- Audit focuses on two P&L pipelines: (1) `alpha_engine/forward_validator.py` closed-pick stats fed to `strategy_performance.json` / `pf_registry.json`, (2) `audit_trail/universal_pick_resolver.py` + `dashboard_generator.py` feeding `at_pick_outcomes` (MySQL) + `dashboard_data.json` → /audit frontend.

## Bugs Found

### STRATEGY-INFLATING BUGS (overstate edge)

---

#### BUG A1 — TP/SL priority order: TP checked before SL
**File:** `alpha_engine/forward_validator.py:1281-1302`
**Severity:** P0
**Impact:** When both TP and SL are hit on the same bar (common in volatile crypto), TP_HIT wins because TP is checked first. Since TP outcomes are scored as WON and SL outcomes as LOST, this inflates win rate and profit factor. The `tp_sl_bug_report.json` (2026-06-05 investigation) found **1194/2648 picks** (45%) have SL closer to entry than TP yet were marked TP_HIT — the signature of TP-first priority.

**Evidence (L1281-1302):**
```python
if signal_type == "BUY":
    if tp and (current_price >= tp * (1 - SL_BUFFER) or day_high >= tp):
        exit_reason = "TP_HIT"      # ← TP checked first, wins on ambiguity
        exit_price = tp * (1 - TP_SLIPPAGE)
    elif _adj_sl and (current_price <= _adj_sl * (1 + SL_BUFFER) or day_low <= _adj_sl):
        exit_reason = "SL_HIT"
```

**Contrast:** `universal_pick_resolver.py` `_check_tp_sl_intrabar` (L670-689) does SL-first — the correct order. The inconsistency between these two resolution engines means picks validated by `forward_validator.py` get the lenient (TP-first) treatment while resolver-validated picks get the conservative (SL-first) treatment.

**Fix:** Reorder the BUY branch to check SL first (matching the SHORT branch and the intrabar helper). Or implement true first-touch detection via OHLC bar replay.

---

#### BUG A1b — TP-first priority also in `check_tp_sl` fallback function
**File:** `audit_trail/universal_pick_resolver.py:888-912`
**Severity:** P0
**Impact:** Same TP-first priority bug as BUG A1, but in the `close_approx` fallback path (called at L1465). When intrabar bars are unavailable, `check_tp_sl` checks TP before SL for BOTH LONG and SHORT. In the LONG branch (L898-904), if `current_price >= tp` AND `current_price <= sl` (both conditions met — price between SL and TP where TP was breached), TP_HIT wins → inflates win rate. In the SHORT branch (L905-911), same issue: `current_price <= tp` checked before `current_price >= sl`.

**Evidence (L898-911):**
```python
if direction == "LONG":
    if tp and current_price >= tp:     # TP checked first
        return ("TP_HIT", tp, pnl)
    if sl and current_price <= sl:     # SL checked second (loses on ambiguity)
        return ("SL_HIT", sl, pnl)
else:  # SHORT
    if tp and current_price <= tp:     # TP checked first
        return ("TP_HIT", tp, pnl)
    if sl and current_price >= sl:     # SL checked second
        return ("SL_HIT", sl, pnl)
```

**Fix:** Reorder both LONG and SHORT branches to check SL before TP (matching `_check_tp_sl_intrabar` at L670-689).

---

#### BUG A2 — Slippage model import path broken
**File:** `alpha_engine/production_scanner.py:5991`
**Severity:** P0
**Impact:** `from slippage_model import apply_slippage_and_vol_sizing` fails because the module is at `alpha_engine/slippage_model.py`. The ImportError is silently caught at L5997, logging "Module not available". The `apply_slippage_and_vol_sizing` function (L481-560 of `alpha_engine/slippage_model.py`) blocks negative-edge picks (picks where expected PnL < costs) by filtering them out. With the import broken, **negative-edge picks pass through unchecked**, inflating the active pick pool with losers.

**Evidence (L5991):**
```python
from slippage_model import apply_slippage_and_vol_sizing  # ← ImportError: should be alpha_engine.slippage_model
```
The actual function exists at `alpha_engine/slippage_model.py:481`.

**Fix:** `from alpha_engine.slippage_model import apply_slippage_and_vol_sizing`.

---

#### BUG A3 — Unit mismatch across pnl_pct consumers (reclassified as P1 data-integrity risk)
**File:** `alpha_engine/forward_validator.py:376` vs `:861-866` vs `:1384`
**Severity:** P1
**Impact (deflating):** `load_closed_picks()` (L863-866) normalizes `pnl_pct` to decimal format (e.g., 0.025) by dividing by 100 when `abs(pnl) > 1.0`. The `compute_strategy_stats` function (L326, containing L376) reads closed_picks.json directly (L359-360), bypassing `load_closed_picks()` normalization. It then divides by 100.0 at L376, assuming percentage format. If the file contains decimal-format `pnl_pct` (post-normalization by `save_closed_picks` → `load_closed_picks`), this double-divides → strategy returns are 100x too small → edge appears absent → **false rejection of profitable strategies**.

**Evidence:**
```python
# L376 — assumes percentage (divides by 100)
strat_returns[strat].append(float(pnl) / 100.0)

# L861-866 — normalizes to decimal
if pnl is not None and abs(pnl) > 1.0:
    p['pnl_pct'] = round(pnl / 100.0, 6)

# L1384 — writes as decimal
pick["pnl_pct"] = round(pnl_pct, 6)
```
So `save_closed_picks` writes decimals (L1384), and `load_closed_picks` also normalizes to decimal (L866). But `compute_strategy_stats` at L376 divides by 100 again → if data is already decimal, returns are 100x deflated.

**Fix:** Remove the `/100.0` at L376 if the file is always decimal, or route through `load_closed_picks()` for consistency.

---

#### BUG A4 — `_pick_pnl_pct` returns percentage, not decimal — unit mismatch
**File:** `audit_trail/dashboard_generator.py:481-499`
**Severity:** P1
**Impact (inflating for big-mover stats):** `_pick_pnl_pct` returns `((l - e) / e) * 100.0` (percentage like 2.5), but `pnl_pct` everywhere else in the ledger is decimal (e.g., 0.025). This percentage value feeds into `_summarize_big_movers` (L491-557) which rolls up `avg_pnl_pct` — so big-mover stats are 100x inflated relative to verdict aggregates that use decimal `pnl_pct`. Additionally, when `_pick_pnl_pct` is used as a fallback for missing `pnl_pct`, it can silently override with a percentage value where decimal is expected.

**Evidence (L499):**
```python
return ((l - e) / e) * 100.0  # percentage, but pnl_pct ledger convention is decimal
```

**Fix:** Return `((l - e) / e)` (decimal, no `* 100.0`) to match the ledger convention documented in `charter_slippage.py:71-74`.

---

#### BUG A5 — Frozen-exit resolution: TP/SL `close_approx` fallback uses shared snapshot
**File:** `audit_trail/universal_pick_resolver.py:1461-1466`
**Severity:** P1
**Impact:** When intrabar OHLC bars are unavailable, the resolver uses the `close_approx` fallback path which calls `_per_pick_price` (L693-722, added 2026-10-22). However, `_per_pick_price` falls back to `current_price` when no bars exist in the cache — and `current_price` is the single run-wide price snapshot. If `ohlc_bars_cache` is empty for a symbol, ALL picks of that symbol get the identical `current_price` → clustered wins/losses at the same price level → phantom correlated outcomes. The `tp_sl_bug_report.json` shows identical `resolved_at` timestamps (e.g., `2026-06-05 05:15:47` for multiple BTCUSDT picks across different strategies), suggesting they resolved against the same frozen tick.

**Evidence:**
- L1461-1466: `close_approx` fallback calls `_per_pick_price(pick, norm_sym, ohlc_bars_cache, current_price)`
- L710-722: `_per_pick_price` falls back to `current_price` when `ohlc_bars_cache` has no bars for the symbol
- L1149: `current_price` is fetched once per run via `_fetch_prices_failover()` and shared across all picks

**Fix:** Ensure `_ENTRY_ANCHORED=1` in production (verified: default is `"1"`), and ensure `current_price` fallback in `_per_pick_price` is not shared across picks of the same symbol — use per-pick timestamp pricing even in the close_approx path.

---

### STRATEGY-DEFLATING BUGS (understate edge)

---

#### BUG D1 — Zero-PnL trades counted as losses
**File:** `alpha_engine/forward_validator.py:1526-1527`
**Severity:** P1
**Impact:** `losses = sum(1 for p in pnls if p <= 0)` counts breakeven (pnl_pct == 0) trades as losses. Breakeven trades should be "flat" (neither win nor loss) — counting them as losses deflates win rate and profit factor. The `dashboard_generator.py` `_is_valid_resolved_pick` (L4903-4904) correctly rejects sentinel exits (exit_price <= 0) and flat-zero PnL rows, but `forward_validator._compute_stats_from_picks` has no such filter.

**Evidence (L1526-1527):**
```python
wins = sum(1 for p in pnls if p > 0)
losses = sum(1 for p in pnls if p <= 0)  # ← zero counted as loss
```

**Fix:** `losses = sum(1 for p in pnls if p < 0)` and add a separate `flat = sum(1 for p in pnls if p == 0)` counter, surfaced in the stats dict.

---

#### BUG D2 — Hold-days computed from date-only `entry_date` (phantom up-to-1-day offset)
**File:** `alpha_engine/forward_validator.py:1224-1231`
**Severity:** P1
**Impact:** `entry_date = pick.get("entry_date", _now_date())` reads a date-only string `YYYY-MM-DD`, then parses it with `datetime.strptime(entry_date, "%Y-%m-%d")` which defaults to **midnight UTC**. If a pick was entered at 20:00 EST (next day 01:00 UTC), the computed `days_held` starts from 00:00 of the entry date — adding up to ~1 full day of phantom hold time. This inflates `hold_days`, which can cause premature `TIME_EXPIRY` exits on short max-hold picks before they have a chance to hit TP, deflating win rate.

**Evidence (L1224-1231):**
```python
entry_date = pick.get("entry_date", _now_date())
try:
    _hold_delta = (datetime.now(timezone.utc) -
                   datetime.strptime(entry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc))
    days_held = _hold_delta.total_seconds() / 86400.0
```

**Fix:** Use `pick.get("created_at")` (full ISO timestamp) instead of `entry_date` (date-only), or parse `entry_date` with a time component fallback.

---

#### BUG D3 — Double-division of pnl_pct in Whites Reality Check (moved from A3)
**File:** `alpha_engine/forward_validator.py:376`
**Severity:** P1
**Impact:** Same as BUG A3 above. `forward_validator.compute_strategy_stats` reads `closed_picks.json` directly and divides by 100.0 at L376. After `load_closed_picks()` normalizes to decimal, this double-divides strategy returns by 100 → edge appears 100x weaker → profitable strategies may be incorrectly filtered or excluded from /audit display → **deflated performance metrics**.

See BUG A3 for full details. This is the same root cause — classified as deflating because it affects strategy significance testing.

---

#### BUG D4 — Leverage-token symbol normalization: DOTDOWN/DOTDOWNUSDT mismatch
**File:** `audit_trail/universal_pick_resolver.py:725-740` and `alpha_engine/forward_validator.py:1069-1080`
**Severity:** P1
**Impact (deflating):** The `_normalize_symbol` function at L725-740 appends "T" to any symbol ending in "USD" that isn't USDT/BUSD. A symbol like "DOTDOWN" (a leveraged inverse token that exists on Binance as `DOTDOWNUSDT`) would be normalized to "DOTDOWNT" — which is NOT a valid Binance symbol. The lookup would fail → no price → pick stays unresolved or gets stuck at TIME_EXIT with a stale price → **deflated win rate for leveraged-token picks**. Meanwhile, `forward_validator._normalize_to_yahoo` (L1069-1080) has different normalization rules, creating inconsistency between the two price-fetch paths.

**Evidence (L738-739):**
```python
if s.endswith("USD") and not s.endswith("USDT") and not s.endswith("BUSD"):
    s += "T"  # DOTDOWN -> DOTDOWNT (invalid Binance symbol)
```

**Fix:** Add explicit handling for leveraged token suffixes (DOWN, UP, BULL, BEAR) — they should map to their actual USDT trading pair (e.g., DOTDOWN → DOTDOWNUSDT, not DOTDOWNT).

---

#### BUG D5 — `at_pick_outcomes` has no `closed_at` column; `strategy_kill_switch` relies on alias
**File:** `tools/strategy_kill_switch.py:234-270` and `alpha_engine/mysql_trading_sync.py:1147-1168`
**Severity:** P2
**Impact (deflating for kill-switch accuracy):** The `strategy_kill_switch.py` docstring explicitly states `at_pick_outcomes has unreliable WR data due to near-flat TIME_EXIT resolutions`. The MySQL table `at_pick_outcomes` (defined at `mysql_trading_sync.py:1147-1168`) uses `resolved_at` aliased to `closed_at` in the query (L268). But the TIME_EXIT resolutions are computed from the frozen-exit fallback (BUG A5), meaning stale prices inflate flat/breakeven outcomes in MySQL. When `strategy_kill_switch` reads these unreliable outcomes, it may incorrectly KILL profitable strategies or FAIL TO KILL toxic ones.

**Fix:** See BUG A5 — ensure all MySQL outcomes use per-pick entry-anchored prices. Additionally, add a `closed_at` column to `at_pick_outcomes` schema for future-proofing (currently aliased from `resolved_at`).

---

## Relevant Files
- `alpha_engine/forward_validator.py` — closed-pick P&L stats (L376 double-division), hold_days (L1224 date-only), TP/SL exit priority (L1281-1302 TP-first), loss counting (L1527 zero-as-loss), pnl_pct normalization (L865)
- `alpha_engine/production_scanner.py` — slippage model import path bug (L5991: `slippage_model` vs `alpha_engine.slippage_model`)
- `alpha_engine/slippage_model.py` — `apply_slippage_and_vol_sizing` function (L481) that production_scanner fails to import
- `alpha_engine/charter_slippage.py` — `deduct_slippage` unit convention (L67-87, decimal format documented)
- `audit_trail/dashboard_generator.py` — `_is_valid_resolved_pick` (L4850), verdict aggregate with deduct_slippage (L15465), `_pick_pnl_pct` unit mismatch (L499), frozen-exit handling (L4291-4295)
- `audit_trail/universal_pick_resolver.py` — TP/SL intrabar check SL-first (L670-689), `_per_pick_price` frozen-exit fix (L693-722), `_normalize_symbol` DOT suffix bug (L725-740), close_approx fallback (L1461-1466), `_ENTRY_ANCHORED` default "1" (L615)
- `alpha_engine/money_ready_verdict.py` — net-of-slippage verdict (`_net_pnl` at L675-690 calls `deduct_slippage`)
- `tools/build_pf_registry.py` — PF registry generation, also calls `deduct_slippage` (L905-908)
- `tools/strategy_kill_switch.py` — reads trading_picks (PRIMARY) + at_pick_outcomes (SECONDARY), documents unreliable WR (L7, L236)
- `alpha_engine/mysql_trading_sync.py` — `at_pick_outcomes` MySQL schema (L1147-1168)
- `tp_sl_bug_report.json` — evidence of TP-first priority bug (1194/2648 suspicious)
- `paper_trading/forward_cohort_tracker.py` — independent forward-tracked P&L with per-pick price anchoring (L6-17 references the frozen-exit bug)

## Next Steps
1. Read quality_gates.py for D/R/L gate P&L filtering rules (L470-560, 700+) — check for additional filtering bugs.
2. Verify `pnl_pct` format in actual `closed_picks.json` file — decimal or percentage? (confirms if BUG A3/D3 double-division is active at runtime).
3. Search for leveraged token (UP/DOWN/BULL/BEAR) handling across all symbol normalization functions.
4. Verify slippage_model.py `apply_slippage_and_vol_sizing` — what fraction of picks it rejects, and confirm the import path fix would restore its filtering.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*

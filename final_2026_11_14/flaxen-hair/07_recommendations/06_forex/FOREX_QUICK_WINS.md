# Forex Quick Wins — MERGED

**Scope:** Forex (EURUSD=X, USDJPY=X, GBPUSD=X, AUDUSD=X, NZDUSD=X, USDCAD=X, USDCHF=X, AUDJPY=X, CADJPY=X, GBPJPY=X)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated findings

| # | Finding | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| FX-1 | Normalize PnL units to percent (multi_asset_closed.json stores ratio; institutional_closed.json stores percent — up to 100×) | HIGH | LOW | `multi_asset_closed.json`, `institutional_closed.json`, `quick_wins/shared/normalize_pnl_units.py` | My audit |
| FX-2 | Fix `recent_picks.txt` stale header — claims "Past 2 Hours" but data dated 2026-03-11 (~8 months stale) | MED | LOW | `recent_picks.txt`, `fetch_recent_picks.py:13` | My audit |
| FX-3 | Resolve/expire 23 forward_test_only forex picks (all null PnL, entry 2026-11-12) | MED | LOW | `multi_asset_picks.json` | My audit |
| FX-4 | Widen `PROVEN_STRATEGIES` whitelist to include forex (forex_carry portfolio at 0% deployed) | MED | LOW | `audit_dashboard/portfolio_manager.py:88`, `tools/edge_filter_engine_v3.py:57` | My audit |
| FX-5 | Make pick IDs unique — date-only IDs duplicate (e.g. `extreme_oversold_bounce::EURUSD=X::2026-03-12` ×5) | MED | LOW | `multi_asset_closed.json`, `quick_wins/shared/validate_pick_ids.py` | My audit |
| FX-6 | Decouple `ml_score` from `confidence` (identical on every pick) — ML code sound; inversion is data bug | LOW | LOW | `multi_asset_picks.json`, `institutional_picks.json` | My audit + peer childlike |
| FX-7 | Honor `BLACKLISTED_STRATEGIES` in `non_crypto_consensus.py` (stops `forex_rsi2_mean_reversion`, `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`) | P0/Critical | Small | `copy_trader_intel/non_crypto_consensus.py`, `alpha_engine/config.py` (~line 264) | Peer audits forex QW-1 |
| FX-8 | Respect `FOREX_HARD_DISABLE=1` in consensus + `combined_confidence_strategy.py` + `smart_picks_engine.py` | P0/Critical | Small | `alpha_engine/config.py`, `alpha_engine/combined_confidence_strategy.py`, `alpha_engine/smart_picks_engine.py` (~line 518) | Peer audits forex QW-2 |
| FX-9 | Dedupe consensus votes by `(symbol, direction, strategy)` | P1/Med | Small | `copy_trader_intel/non_crypto_consensus.py` | Peer audits forex QW-3 |
| FX-10 | Fix FX price resolver (96.6% null PnL) | P1/Med | Small | `audit_trail/fetch_stock_prices.py` (forex path), `audit_trail/universal_pick_resolver.py` | Peer audits forex MF-1 |
| FX-11 | Replace IG/myfxbook contrarian sources with regime-filtered momentum | P2/Low | Medium | `copy_trader_intel/` | Peer audits forex QW-4 |

## Key observations
- `multi_asset_closed.json` EURUSD=X `pnl_pct: -0.00567` (ratio) but recompute from entry/exit (identical prices) = 0.0%; pnl_pct was copied from `unrealized_pnl_pct` vs `current_price`, not from exit_price — data integrity bug.
- `recent_picks.txt` header "Picks Activity in the Past 2 Hours (since 6:24 PM EST)" — `fetch_recent_picks.py:13` hardcodes `now_est = 2026-03-11T20:24:32-04:00`; all entries dated 2026-03-11.
- `multi_asset_picks.json`: 23 forex picks, all `forward_test_only: true`, `pnl_pct: null`, `status: OPEN`, `forward_validated: false`, `forward_trades: 0`, entry 2026-11-12 — 2 days old, unresolved.
- `audit_dashboard/portfolio_manager.py:88` `PROVEN_STRATEGIES` has 11 strategies, all crypto/equity — zero forex. `REVIEW_ANSWERS.md:Q8` confirms this is the root cause of empty `forex_carry` portfolio (Cash $9,992 / Equity $9,992 = 0% deployed).
- `tools/edge_filter_engine_v3.py:57` `FOREX_PROVEN_STRATEGIES = {"forex-rsi-ema-scout"}` — strategy does NOT exist in `multi_asset/forex_strategies.py`.
- Duplicate IDs: `extreme_oversold_bounce::EURUSD=X::2026-03-12` ×5, `GBPUSD=X` ×4, `ema_stack_momentum::AUDUSD=X` ×3, `USDJPY=X` ×3, `NZDUSD=X` ×2.
- `confidence == ml_score` on every pick (e.g. EURUSD=X 0.75/0.75).
- Live cross-check (peer audits): USDCAD=X SHORT claimed -0.0% but live +0.061%; NZDUSD=X LONG claimed -0.0% but live +0.0385%.
- 4 active forex picks stale since 2026-05-25 (~172d), `current_price=None`, `pnl=0.0`, zombie rows (peer childlike).
- Closed coverage OK (1,097 FOREX + 120 lowercase `forex` case-dup) (peer childlike).
- Raw DB WR 83.3% but PF 0.108 (small wins masking catastrophic losses) (peer audits).
- Dashboard PF 2.02 vs raw 0.108 (-18.7x) (peer audits).
- PR #6 FOREX block bypassed via `non_crypto_consensus` cross-asset pipeline; blocked strategy `forex_rsi2_mean_reversion` still feeds consensus (peer audits).
- Money-ready: NOT_READY, policy_frozen=true, DSR ~0, expectancy -0.002 (peer audits).

## Verification (forex)
1. **PnL unit check:** compute `(exit_price - entry_price) / entry_price * 100` (LONG) or `(entry_price - exit_price) / entry_price * 100` (SHORT) vs stored `pnl_pct`/`realized_pnl_pct`. EURUSD=X macd_divergence should compute ~0.0% (exit==entry) but stored -0.00567 ratio.
2. **recent_picks.txt freshness:** every Entry/Close Time is `2026-03-11` while today is `2026-11-14`; `fetch_recent_picks.py:13` hardcodes 2026-03-11.
3. **Forward-test expiry:** each forex pick age (2026-11-12 → 2026-11-14) exceeds max hold; flag EXPIRED or resolve.
4. **PROVEN_STRATEGIES forex gap:** grep `portfolio_manager.py:88` — no strategy with `asset_classes` containing `"forex"`; cross-reference `portfolio_defs.py:STRATEGY_REGISTRY` which lists `carry_momentum` (forex, proven) and `mean_reversion_bollinger` (forex, proven) as proven but absent from whitelist.
5. **Duplicate ID detection:** `extreme_oversold_bounce::EURUSD=X::2026-03-12` count = 5 → must be 0 after fix.
6. **confidence==ml_score:** 100% match on all picks → must be decoupled.
7. **FOREX_HARD_DISABLE:** confirm `FOREX_HARD_DISABLE=1` is respected in consensus pipeline (not bypassed by `non_crypto_consensus.py`).

## Code snippets

**QW-1 PnL normalization (recompute as percent from entry/exit):**
```python
def normalize_pnl_pct(pick):
    entry = pick.get("entry_price"); exit_px = pick.get("exit_price") or pick.get("close_price")
    direction = pick.get("direction", "LONG")
    if not entry or not exit_px or entry <= 0: return 0.0
    raw = (exit_px - entry) / entry
    if direction == "SHORT": raw = -raw
    return round(raw * 100, 4)   # percent, e.g. -0.57
for p in closed_picks:
    p["pnl_pct"] = normalize_pnl_pct(p); p["pnl_pct_unit"] = "percent"
```
EURUSD=X recompute: entry 1.163602590560913, exit 1.163602590560913 → 0.0% (not -0.57%).

**QW-2 Fix recent_picks.txt (dynamic now):**
```python
from datetime import datetime, timedelta, timezone
now_est = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-4)))
two_hours_ago = now_est - timedelta(hours=2)
print(f"### Picks Activity in the Past 2 Hours (since {two_hours_ago.strftime('%I:%M %p %Z')})")
print(f"*Data generated {now_est.strftime('%Y-%m-%d %I:%M %p %Z')}*")
```

**QW-3 Expire stale forward-test forex picks:**
```python
from datetime import datetime, timezone
FOREX_MAX_HOLD_DAYS = 14; now = datetime.now(timezone.utc)
for p in multi_asset_picks:
    if p.get("asset_class")=="FOREX" and p.get("forward_test_only") and p.get("status")=="OPEN":
        entry = datetime.fromisoformat(p["entry_date"].replace("Z","+00:00"))
        age_days = (now - entry).days
        if age_days > FOREX_MAX_HOLD_DAYS:
            p["status"]="EXPIRED_FORWARD_TEST"; p["exit_reason"]=f"Forward test expired after {age_days} days (max {FOREX_MAX_HOLD_DAYS})"
            p["pnl_pct"]=0.0; p["closed_at"]=now.isoformat()
```

**QW-4 Add forex to PROVEN_STRATEGIES whitelist (`portfolio_manager.py`):**
```python
PROVEN_STRATEGIES = {
    # ... existing crypto/equity ...
    # FOREX — added 2026-11-14 (forex_carry portfolio was empty, 0% deployed)
    "carry_momentum",          # portfolio_defs.py STRATEGY_REGISTRY: forex, proven
    "mean_reversion_bollinger",# portfolio_defs.py STRATEGY_REGISTRY: forex, proven
    "forex_rsi2_mean_reversion", # pending forward evidence → RESEARCH_COHORT if unproven
}
```
Align `tools/edge_filter_engine_v3.py:57`:
```python
FOREX_PROVEN_STRATEGIES = {"carry_trade","session_overlap_momentum","keltner_compression_forex","dxy_trend_filter"}
```
(replace `"forex-rsi-ema-scout"` which has no implementation in `forex_strategies.py`.)

**QW-5 Unique pick IDs with timestamp:**
```python
def make_pick_id(strategy, symbol, dt):
    return f"{strategy}::{symbol}::{dt.strftime('%Y-%m-%d_%H%M%S')}"
# dedup validation on write:
ids = [p["id"] for p in closed_picks]
assert len(ids) == len(set(ids)), f"Duplicate pick IDs: {[i for i in ids if ids.count(i)>1]}"
```

**QW-6 Decouple confidence from ml_score:**
```python
ml_score = p["ml_score"]
regime_bonus = 0.05 if p.get("regime_match") else -0.05
tech_bonus = 0.03 if p.get("technical_alignment") else 0.0
p["confidence"] = round(min(0.95, max(0.10, ml_score + regime_bonus + tech_bonus)), 3)
p["confidence_source"] = "ml_score + regime + technical_alignment"  # not an alias
```

**QW-7 Honor BLACKLISTED_STRATEGIES in non_crypto_consensus.py:**
```python
# Before voting, skip blacklisted strategies
if strategy_name in BLACKLISTED_STRATEGIES:
    continue  # blocked strategies must not contribute to consensus
```

**QW-8 Respect FOREX_HARD_DISABLE:**
```python
if config.FOREX_HARD_DISABLE and pick.asset_class == "FOREX":
    continue  # hard-disable: no forex picks emitted
```

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.

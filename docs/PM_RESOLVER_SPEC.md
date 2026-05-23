# Prediction Market Closer Pipeline — Spec for `pm_resolver.py`

**Status:** Unbuilt. All PM systems have `closed_picks=0` because no event-settlement fetcher exists.
**Owner suggestion:** Kimi or Codex (they own `alpha_engine/kalshi_signals.py` + `alpha_engine/polymarket_signals.py`)
**Author of this spec:** `antigrav-dash-integrity` 2026-04-04

---

## Problem

PM picks enter the system from 5 sources:
- `pm_kalshi_signals` — 3 active, 0 closed, last signal 1h ago ✅
- `pm_whale_signals` — 1 active, 0 closed ✅
- `pm_high_conviction` — 1 active, 0 closed ✅
- `prediction_market_consensus` — 0 active, 0 closed (aggregator)
- `polymarket_signals` — 0 active, 0 closed (dormant)

But `closed_picks=0` everywhere. The **closer pipeline is broken** — picks enter and accumulate forever.

## Root Cause

`audit_trail/universal_pick_resolver.py:459-488` (`_snapshot_prediction_market_entry`) treats PM picks as **crypto TP/SL trades against BTC/ETH spot price**:

```python
# PRESENT LOGIC (wrong)
entry = last_price  # BTC spot
tp = entry * 1.025  # +2.5% TP
sl = entry * 0.985  # -1.5% SL
```

But Kalshi/Polymarket picks are **binary event-market** positions:
- Kalshi: YES/NO contracts that resolve on event settlement date (e.g., "Will Fed cut rates in April?")
- Polymarket: 0-100 probability shares that resolve when the event outcome is known

They don't close on crypto price movement. They close when the event **settles** (hours, days, or weeks later).

## Fix: Build `pm_resolver.py`

**Location:** `prediction_market_agents/pm_resolver.py`
**Ingested by:** `audit_trail/universal_pick_resolver.py` in an "is PM pick" branch that bypasses crypto TP/SL logic.

### Required API Calls (all unauthenticated)

**Kalshi settlement fetch:**
```
GET https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}
→ response.market.result  (values: "yes", "no", "" for still-open)
→ response.market.status  ("open" | "closed" | "settled")
→ response.market.close_time (ISO datetime)
→ response.market.settlement_value ($ payout per contract, cents)
```

**Polymarket settlement fetch (CLOB):**
```
GET https://clob.polymarket.com/markets/{condition_id}
→ response.closed  (bool)
→ response.accepting_orders  (bool)

GET https://gamma-api.polymarket.com/markets?closed=true&condition_ids={id}
→ outcome prices (final settlement)
```

**Polymarket settlement fetch (Gamma, alternative):**
```
GET https://gamma-api.polymarket.com/markets/{slug}
→ response.outcomes[]  (settlement percentages)
```

### Pipeline Shape

```python
def resolve_pm_picks(active_picks: list) -> list[dict]:
    """
    For each active PM pick, check if underlying event has settled.
    Returns list of closure records with:
      {pick_id, source_system, outcome ('WON'|'LOST'|'STILL_OPEN'),
       pnl_pct, exit_price, closed_at, exit_reason}
    """
    for pick in active_picks:
        if not _is_pm_pick(pick):
            continue
        market_ticker = _extract_market_ticker(pick)
        settlement = _fetch_settlement(market_ticker, pick['source_system'])
        if settlement['status'] != 'settled':
            continue
        # Compute PnL from entry probability vs settled outcome
        entry_prob = pick.get('entry_probability', 0.5)
        if settlement['outcome'] == pick['direction']:  # "YES" bet on YES outcome
            pnl_pct = ((1.0 - entry_prob) / entry_prob) * 100
            outcome = 'WON'
        else:
            pnl_pct = -100.0  # Total loss on losing side
            outcome = 'LOST'
        yield {
            'pick_id': pick['id'],
            'source_system': pick['source_system'],
            'outcome': outcome,
            'pnl_pct': round(pnl_pct, 2),
            'exit_price': settlement['settlement_value'],
            'closed_at': settlement['closed_at'],
            'exit_reason': f'MARKET_SETTLED_{settlement["outcome"].upper()}',
        }
```

### Wiring into `universal_pick_resolver.py`

Add a branch at L459 BEFORE `_snapshot_prediction_market_entry`:

```python
if _is_prediction_market_pick(pick):
    from prediction_market_agents.pm_resolver import resolve_single_pm_pick
    settlement = resolve_single_pm_pick(pick)
    if settlement and settlement['status'] == 'closed':
        _apply_pm_closure(pick, settlement)
        continue  # skip crypto TP/SL logic entirely
    # if still open, skip — don't treat as crypto
    continue
```

### Data Needed in Pick Payload

PM picks currently lack these fields — producers need to emit them:

| Field | Source | Used For |
|---|---|---|
| `pm_market_ticker` | `pm_kalshi_signals`, `polymarket_signals` | `_fetch_settlement()` lookup |
| `pm_condition_id` | Polymarket only | CLOB API |
| `entry_probability` | Signal generators | PnL calculation on settlement |
| `event_close_time` | Market metadata | Age / expiry gate |
| `pm_source` | Resolver | Know which API to hit |

### Scheduling

Run as a GitHub Actions job **every 15 min** (Kalshi settles hourly on weekdays, Polymarket continuously):
```yaml
# .github/workflows/pm-resolver.yml
on:
  schedule: [{cron: "*/15 * * * *"}]
jobs:
  resolve:
    runs-on: ubuntu-latest
    steps:
      - run: python -m prediction_market_agents.pm_resolver
```

### Expected Outcome After 14 Days

- `pm_kalshi_signals.closed_picks` grows to 50-100
- `pm_whale_signals.closed_picks` grows to 20-40
- Real WR / PF / PnL attribution populates `system_trust_registry.py`
- Systems can be re-tiered based on ACTUAL performance (not provisional WATCH)

## Acceptance Criteria

1. A Kalshi YES pick on `KXFED-24DEC-T5.00` resolves to WON/LOST when the market settles (visible in Kalshi API `result` field)
2. A Polymarket pick resolves when `closed=true` returned by CLOB
3. `closed_picks` count increments daily for each PM system
4. `attribution_tracker.py` produces a non-empty report with per-system WR for PM sources
5. No crypto TP/SL logic ever fires on a PM pick

## Related

- `alpha_engine/kalshi_signals.py` — signal generator (adds picks)
- `alpha_engine/polymarket_signals.py` — signal generator (adds picks)
- `alpha_engine/prediction_market_consensus.py` — consensus aggregator
- `prediction_market_agents/orchestrator.py` — currently orchestrates signal generation but NOT closure
- `audit_trail/universal_pick_resolver.py:459-488` — broken closer (to be bypassed)
- `cross_aggregation/system_trust_registry.py` — PM entries provisional WATCH tier (updated 2026-04-04)

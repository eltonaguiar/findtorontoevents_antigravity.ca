# Fix the red CI: isolate legacy hygiene tests from the audit3 denylist (2026-11-19)

**Scope:** five test modules + `tests/test_tier2_hero_cards.py`.

## The two failures on `main`

### 1. `test_feed_hygiene_*`, `test_polymarket_volume_filter`,
`test_prediction_market_shadow_pin`, `test_commodity_kill_switch`

`is_valid_active_pick` now runs the audit3 denylist before the anonymity rules.
Their fixtures are synthetic **BTCUSDT / CRYPTO** picks, and the committed
canonical ledger marks **BTC as a KILL symbol** and **CRYPTO as a KILL class**, so
the denylist vetoed the fixture before the rule under test was reached:

```
denied_reason -> "audit3 KILL: CRYPTO BTC LONG n=407 net=-0.8399%/trade"
```

The denylist is correct; the fixtures need isolation. Each of the five modules now
sets `AUDIT3_DENYLIST_DISABLED=1` in `setUpModule()` and clears it in
`tearDownModule()`. The denylist keeps its own coverage in
`tests/test_audit3_enforcement.py` (which passes).

### 2. `test_tier2_hero_cards`

The Tier-2 hero panel was **retired on 2026-11-19** (external review A6, "dead
tiles out"): the `#tier2-hero-section` markup was removed and
`getTier2ProvenStrategies()` returns `null` so a stale payload cannot re-promote
cards. The test still asserted the mount existed. It now asserts the retirement
itself: no mount, renderer present, null data guard intact.

## Verification

```
pytest tests/test_audit3_enforcement.py tests/test_audit3_*.py \
       tests/test_feed_hygiene_additional_fixes.py tests/test_feed_hygiene_schema.py \
       tests/test_polymarket_volume_filter.py tests/test_prediction_market_shadow_pin.py \
       tests/test_commodity_kill_switch.py tests/test_tier2_hero_cards.py -q
# 193 passed, 1 skipped
```

No production code changed; the gate behaviour is untouched.

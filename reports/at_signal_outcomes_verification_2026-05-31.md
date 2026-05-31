# at_signal_outcomes Verification (2026-05-31)

## Status: FRESH, not stale.

## Live DB query (zoocode peer, 2026-05-31): 107,777 rows; latest created_at 2026-05-30T23:44Z.

## Status distribution: CLOSED 50,465 / OPEN 45,726 / EXPIRED 31,146 / WON 14,546 / LOST 8,650.

## Source distribution (concentration risk): kimi_riseoftheclaw 68,628 (63.7%); alpha_engine 20,460 (19.0%); ml_battleground_system_f_clawsofdoom 10,602; battleground 7,380; ...

## Asset-class distribution: CRYPTO 53,480 / FOREX 35,978 / UNKNOWN 14,596 / MEMECOIN 3,554 / EQUITY 169.

## Implications:
- Incident "P0 #10 signal_outcomes 82d stale" is OBSOLETE — close it.
- EQUITY pipeline severely under-emitting (169 outcomes vs CRYPTO 53k) — separate Goal #1 blocker.
- 14,596 UNKNOWN asset_class outcomes require backfill via symbol pattern matching.
- 63.7% single-source concentration (kimi_riseoftheclaw) at the MySQL level confirms the class-level pattern.

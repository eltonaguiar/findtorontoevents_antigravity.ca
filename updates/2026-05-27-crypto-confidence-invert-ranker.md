# CRYPTO Confidence Invert for Smart Picks Ranker (Env-Gated)

**Date**: 2026-05-27  
**Model**: Cursor Composer  
**Incident**: INC-17 — smart_picks_engine weights confidence-derived signal; high conf → ~14% WR on CRYPTO

## What was broken

On CRYPTO, empirical win rate **inverts** with confidence: picks with conf≥0.9 show ~14% WR while conf 0.5–0.6 show ~60% WR. `_compute_ml_composite()` still used raw confidence (10% weight after 2026-05-25 IC fix), promoting worst picks to top of Smart Picks.

## What changed

- Added `_effective_confidence_for_ranking()` in `alpha_engine/smart_picks_engine.py`
- When `CONFIDENCE_INVERT_CRYPTO=1` and asset class is CRYPTO, ranking uses `1.0 - confidence`
- **Default OFF** (`CONFIDENCE_INVERT_CRYPTO=0`) — zero production behavior change at merge

## How to enable

```bash
export CONFIDENCE_INVERT_CRYPTO=1
# Or in crypto-smart-picks.yml env block
```

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('alpha_engine/smart_picks_engine.py', doraise=True)"
python3 -c "
from alpha_engine.smart_picks_engine import _effective_confidence_for_ranking
import os
os.environ['CONFIDENCE_INVERT_CRYPTO']='1'
p={'asset_class':'CRYPTO','confidence':0.9}
assert abs(_effective_confidence_for_ranking(p,0.9)-0.1)<1e-9
print('ok')
"
```

## Related

- `reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-quick-wins.md` (QW-01)
- Long-term: retrain ML classifier + enable `CONFIDENCE_CALIBRATION_ENABLED=1`

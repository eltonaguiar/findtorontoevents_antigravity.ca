# ETF strategy_admit forward-pilot gate fix

## What was broken

`tools/strategy_admit.py` claimed that live merge required the forward pilot to be ready, but it never actually loaded the ETF forward-pilot artifact. That meant the admit JSON could only see walk-forward and class money-ready status, while ignoring the real paper-pilot state for `etf_dual_momentum`.

## What changed

1. Added ETF forward-pilot loading to `tools/strategy_admit.py`.
2. Included a new `forward_pilot` section in the admit payload with:
   - `n_closed`
   - `pf`
   - `wr`
   - `promotion_ready`
   - `shadow_checkpoint_ready`
   - gate blockers and current open position
3. Tightened status logic so `PROMOTE_LIVE` now requires:
   - walk-forward PASS
   - class `MONEY_READY`
   - forward-pilot `promotion_ready=true`
4. Improved the recommendation string so it lists the actual blockers instead of implying the tool had already checked them.

## Why this matters

ETF is the cleanest current candidate edge, but it is still a forward-pilot story, not a live-sizing story. The admit artifact now says that honestly and exposes the exact missing gates instead of flattening everything into a generic recommendation.

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('tools/strategy_admit.py', doraise=True)"
python3 tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF --write
```

Expected result: the generated `reports/strategy_admit/etf_dual_momentum.json` includes `forward_pilot` and keeps the sleeve at `FORWARD_PILOT_ONLY` while the ETF class remains `INSUFFICIENT_DATA` and the paper pilot has `n_closed=0`.

# CRYPTO Audit Feedback - 2026-05-05T0121Z

Agent: GPT-5.5

## Verdict

CRYPTO is watch-only by charter. Current payload: `n=8166`, `WR=44.8%`, `PF=1.26`, `PnL=2198.61%`, `status=watch`, `sizing_allowed=true`.

## Legit Fix Path

- Split `sizing_allowed` semantics. The generator allows sizing for `stable` and `watch`, but Tier-2 sizing should require `PF > 1.5`, `WR > 50%`, `MDD < 20%`, and `n >= 100`.
- Prioritize `signal_validation` as the only confirmed Tier-2 style system-level edge, not the whole CRYPTO class.
- Add symbol-dependency checks for `alpha_engine`, `quan_engine`, `rapid_fire`, and `luxalgo_filters` before increasing CRYPTO volume share.

## Do Not Do

Do not promote CRYPTO class-level risk just because total PnL is positive. PF and WR both miss the charter floor.

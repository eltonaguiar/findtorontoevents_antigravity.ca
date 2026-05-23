# EQUITY Audit Feedback - 2026-05-05T0121Z

Agent: GPT-5.5

## Verdict

EQUITY is a candidate, not proven Tier 2. Current payload: `n=428`, `WR=52.8%`, `PF=1.42`, `PnL=276.23%`, `status=stable`, `sizing_allowed=true`.

## Legit Fix Path

- Focus on PF lift without sacrificing WR. The class clears sample and WR, but misses `PF > 1.5`.
- Audit system concentration before scaling: `alpha_engine` has `PF=1.23`, `MDD=194.03%`, and depends heavily on `INJUSDT`.
- Keep sizing conservative until class-level PF clears 1.5 and per-system MDD is under control.

## Do Not Do

Do not call EQUITY Tier 2 yet. It is close, but PF is below floor and large drawdown systems can contaminate the class.

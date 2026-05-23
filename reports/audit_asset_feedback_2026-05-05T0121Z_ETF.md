# ETF Audit Feedback - 2026-05-05T0121Z

Agent: GPT-5.5

## Verdict

ETF remains unproven. Current payload: `n=88`, `WR=53.4%`, `PF=1.20`, `PnL=19.79%`, `status=candidate`, `sizing_allowed=false`.

## Legit Fix Path

- Treat ETF as an observation lane until `n >= 100` and `PF > 1.5`.
- Add more forward samples before changing production gates.
- Run the same cost-aware checks as non-crypto consensus, because a decent WR with weak PF can vanish after costs.

## Do Not Do

Do not promote ETF based on WR alone. It fails both sample floor and PF floor.

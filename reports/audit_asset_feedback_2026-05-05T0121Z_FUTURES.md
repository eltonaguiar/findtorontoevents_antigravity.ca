# FUTURES Audit Feedback - 2026-05-05T0121Z

Agent: GPT-5.5

## Verdict

FUTURES is not analyzable. Current payload: `n=2`, `WR=100.0%`, `PF=n/a`, `PnL=0.00%`, `status=insufficient_data`, `sizing_allowed=false`.

## Legit Fix Path

- Do not report FUTURES performance as meaningful until `n >= 100`.
- If FUTURES is meant to be separate from COMMODITY, add explicit data sourcing and resolver coverage so it can accumulate a real sample.
- Otherwise, keep FUTURES merged into COMMODITY-style CTA analysis until there is enough standalone data.

## Do Not Do

Do not cite 100% WR. At `n=2`, it is noise.

# COMS note published 2026-11-23 — subject: notes/buffy-top-picks-and-landing-2026-11-23 (4,337 B, retained)

Sent to the fleet bus; this file is the local archive copy of the payload. Content covers:

1. **Landing** — `github.com/eltonaguiar/antigravity_review_Nov192026` branch `main`:
   `a3f6a6b` (2026-11-23/buffy-freebuff/PICKS.md + picks.json), `41a6e19`
   (34_FINAL_PICKS_2026-11-23/buffy-freebuff.md, ten-class schema), `3f1ab35` (appended Revision
   blocks). All three verified as ancestors of `origin/main` with `git merge-base --is-ancestor`;
   none required a cherry-pick because nothing sat on a side branch.
2. **Top five picks** — XLV, KO, MSFT longs (H-201 xsmom, 4/5 gates, fails only deflated Sharpe at
   0.9469/N=29); the R4b basket XLE/XLV/XLK/IWM/EFA (forward-only, zero records until 2026-11-30);
   T-bills at 4.32% as the reference line. Dead: BONDS, FOREX. Unknown: MUTUAL_FUND, COMMODITY,
   OPTIONS, PREDICTION_MARKET, PRIVATE_CREDIT. Crypto carry CANDIDATE at 0% allocation.
3. **How it was tested** — equity rests on the existing 3,744-day / 179-trade artifacts with a
   paired-bootstrap CI and a rebuilt DSR (skew -0.050, kurtosis 12.254); the ETF rule was
   deliberately NOT backtested (that would spend its trial), with 23 unit tests covering the clock
   and its append-only refresh; the power analysis used 10 arithmetic-only tests and read only the
   universe's volatility.
4. **A bug the tests caught** — the power tool compared an annual hurdle to a monthly SE and printed
   506 bp/month instead of 110; caught by two failing assertions, fixed in `monthly_hurdle()`, with
   a unit-boundary test added.
5. **Not tested** — no pick executed, no fill prices exist, equity cost disputed (12.0749 vs 1–5 bp).

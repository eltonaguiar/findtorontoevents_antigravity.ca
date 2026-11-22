# EQUITY edge consult

## Mechanisms under test
Post-earnings-announcement drift (PEAD), sector momentum, insider cluster buying.

## Measured evidence so far
PEAD, three separate attempts, all dead:
- EQ1 backtest: verdict FAIL, in-sample Sharpe -0.02, win rate 0.366
- H-010: kill #6
- H-034: anti-PEAD reversal also failed
`data/earnings/<TICKER>/latest.json` holds only 4 quarters and a SINGLE
eps_estimate snapshot fetched 2026-11-19. Applying it to quarters ending
2025-12-31 is look-ahead, so PEAD cannot be re-tested honestly from this file.

Class-level sweep: n 1224, net PF 0.939, CI lower bound -0.2068, halves
-0.2518 / +0.1396.

## Specific question
1. Given three failed PEAD attempts and non-vintage consensus data, is there
   any version of earnings drift that is worth a fourth attempt, and if so what
   exactly must be different (data, universe, holding period, benchmark)?
2. A "consistent up pattern" test (the user's framing): which equity signal has
   a documented positive median return with acceptable skew, not just a positive
   mean carried by a few winners?
3. Sector momentum built from current constituents is survivorship-biased.
   How much of a reported sector-momentum Sharpe is typically just that bias?
4. Name the single cheapest dataset acquisition that most improves an honest
   equity test here.

## Constraint
Every answer must name a falsifiable test. Do not recommend re-running a
killed strategy without stating what changed.

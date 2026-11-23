# Long-term memory — vanilla-handsaw / kilo

**Last updated:** 2026-11-23T00:31Z (this session)

## Current state
- Branch: feat/coms-final-notes-2026-11-20 (clean, 6 commits ahead of origin/main on the parity/fix work)
- Parity items 2–5 complete + P1-5 verifier + P1-6/P1-6b/P1-6c complete.
- End-goal chain (ranked picks per class + overall best real-money option + backtest + quant metrics) is the active todo list.
- N7 freeze gate (E11/E13/E14) still red — do not start new scanners.

## Key decisions recorded elsewhere
- POD-EQUITY-BREAKOUT retired (phantom strategies).
- EQUITY is the only class with positive net expectancy after measured Questrade costs (5.13 bps).
- CRYPTO/COMMODITY/FOREX = KILL (PF 0.84, negative expectancy).
- Highest profit potential (risk-controlled) is the ETF tactical drawdown sleeve (38% MaxDD cut).

## Next actions (wake on any of these)
- Background task finishes (P2-9 + asset_class_rankings.json)
- Fresh ledger lands from audit3-ledger cron
- Any COMS message on inbox/gx10-c9b9/vanilla-handsaw/kilo or mentions/all

## Constraints to respect
- Never read dbpasses.txt.
- Never push a branch that contains commits from other authors.
- Every code fix must have a matching .MD in updates/.
- Zero real money until forward gate (n>=100, PF CI-LB>1.0, 100% intrabar honesty, >=90% benchmark coverage).

## Personal notes
- The "prove an edge" request from the human is the true north star: produce a ranked list a human can actually put money into, then backtest it under the same entry criteria the live system would have used.
- Keep the COMS messages concise and actionable; the bus is for wake-ups, Git is the filing cabinet.

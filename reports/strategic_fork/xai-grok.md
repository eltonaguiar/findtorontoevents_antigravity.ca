# xai-grok - strategic fork

**1. ARE THESE MUTUALLY EXCLUSIVE?**

No, but concurrency is a resource trap for a three-to-five-person team. Option 2 (sandbox) is the only one that can run in parallel without immediate cash or headcount burn; it is literally “do nothing active.” Option 1 and 3 both require paid data feeds, co-location or direct-exchange access, and at least one full-time person writing production-grade ingestion and risk code. Running 1 and 3 together splits that scarce person into two half-efforts and guarantees neither reaches the walk-forward gate with clean data. The only defensible split is: sandbox stays permanently on, while the team picks exactly one of 1 or 3 for a time-boxed 90-day sprint. Anything else is scope creep.

**2. SEQUENCING**

Days 0-30: Lock the harness exactly as described (eff ≥ 0.30, same sign, ≥3/5 windows). No new data purchases. Run a single, narrow structural probe: 2s/10s futures basis net of borrow and margin. Use only public CME settlement files plus existing broker margin schedules. Kill criterion: if net carry after realistic execution and funding costs is < 8 bp per day on a $2 mm notional clip, terminate.

Days 31-60: If the basis probe survives, build a minimal live-paper engine (one VPS, one broker FIX connection, position limits hard-coded at 5 % NAV). If it fails, switch to Option 1 but only for one data set—options end-of-day skew from a single vendor (e.g., ORATS or similar <$800/mo). Ingest, align to existing universe, and push straight through the harness. Kill criterion identical: same-sign stability across the five walk-forward windows.

Days 61-90: Any surviving candidate must clear a second, stricter capital-realism gate: simulated round-trip cost (including exchange fees, clearing, and half a tick slippage) must leave at least 60 % of the gross edge. If it does not, return to sandbox and stay there. No further data purchases or strategy branches until that test is passed.

**3. BASE RATES**

- New input class (1): 8-12 % chance of producing a harness-passing edge in 6-12 months. Most purchased microstructure or alt-data sets still show the identical in-sample / OOS sign-flip pattern once latency and cost are modeled.
- Research-sandbox (2): 100 % chance of “producing” nothing, which is the correct outcome given the exhaustive prior search.
- Structural alpha (3): 15-20 % chance for a narrow carry or basis capture that clears the harness, but only if the team restricts itself to exchange-listed instruments with public settlement data. Broader market-making or gamma-trading variants drop below 5 % for a small team.

Rank order by expected positive-P&L probability: 3 > 1 >> 2 (where 2’s value is cost avoidance, not edge discovery).

**4. STRUCTURE ALPHA**

It is genuinely different only when the edge is compensation for providing balance-sheet or inventory services rather than forecasting direction. Most teams re-label directional bets as “structural” and fall into the same trap. One concrete, narrow example that can be tested inside the existing harness: CME Treasury futures calendar spreads held to delivery, capturing the net basis after cheapest-to-deliver optionality and margin drag. Data requirement: daily settlement files plus the CME’s published delivery history (public). Capital requirement: $1.5-2 mm margin at a clearing FCM that offers portfolio margining; risk limit: max 3 % NAV adverse move per spread leg. Execution: once per quarter, no intraday decisions. This passes the “paid to carry” test; anything requiring sub-second quoting or inventory skew prediction does not.

**5. THE SINGLE HIGHEST-EV MOVE**

Run the 30-day basis probe inside the frozen harness and accept the kill rule. If it dies (base-rate expectation), shut down all further signal or data spend for the rest of the year and treat the system as a permanent research ledger. The historical hit rate on new data or new structural variants for teams of this size and latency profile is low enough that continued spend is negative-EV.

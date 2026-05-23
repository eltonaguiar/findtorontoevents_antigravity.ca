# Validate H-032: BTC Miner Capitulation / Hash Ribbon Signal

## Context

An algorithmic trading system has had 11/11 pre-registered causal hypotheses killed by a walk-forward sign-stability harness with these requirements:
- Effect size (eff) >= 0.30
- Same sign in >= 3/5 of 14-day rolling windows
- Net of 30bps round-trip transaction cost

All killed hypotheses shared a common flaw: their causal mechanisms were behavioral or regime-dependent (COT positioning, funding-rate directional, roll-yield, PEAD, on-chain counts, exchange net-flow, etc.) — mechanisms whose sign can flip across market regimes.

A swarm consultation has proposed ONE surviving candidate: **BTC Miner Capitulation (Hash Ribbon + Profit Margin Cross)**.

## The Proposed Signal

**Entry:** Go LONG BTC when BOTH:
1. Estimated daily miner profit margin per TH/s drops below zero (revenue < electricity cost)
2. 30-day MA of network hash rate crosses below the 60-day MA (confirming active capitulation)

**Exit:** When 30-day MA of hash rate crosses back above the 60-day MA

**Data (all free, no key):**
- BTC price: Binance/CoinGecko API
- Network hash rate + difficulty: mempool.space API
- Block subsidy + avg TX fees: mempool.space block data
- ASIC efficiency proxy: Cambridge CBECI estimate or difficulty-derived (~28-32 J/TH for current fleet)
- Electricity cost: EIA US average commercial rate ($0.10-0.12/kWh)

**Proposed Causal Mechanism:**
- BTC mining has a hard variable-cost floor (electricity ~60-80% of OpEx; ASIC hardware is sunk)
- When revenue/TH < electricity cost/TH, miners MECHANICALLY sell BTC to pay utility bills — involuntary, not discretionary
- The least-efficient rigs capitulate first, each shutdown removing both selling pressure and hash rate
- Hash rate decline is the observable signature of the selling cohort shrinking
- When hash rate recovers: supply shock is exhausted, difficulty adjustment temporarily boosts survivors' margin, structural buyers act
- **The sign is structurally fixed:** miners ALWAYS sell when unprofitable. The signal cannot invert across regimes.

## Questions for Validation

Please answer ALL five questions with concrete evidence and/or reasoning:

**Q1. Is the causal mechanism valid?**
Is the forced-selling chain (unprofitable → must sell → supply shock → price depression → capitulation exhausted → recovery) logically and empirically sound? Are there significant leakages in the mechanism? Do miners commonly hedge (forward-sell BTC) or hold significant reserves that would delay or break the chain?

**Q2. Is hash rate a defensible non-"on-chain-count" metric?**
The forbidden list includes "on-chain counts" (address counts, transaction counts, whale wallet counts). Hash rate is an economic/physical metric (computational power committed). Is this distinction defensible? Would a rigorous quant researcher classify hash rate as an "on-chain count" or as a separate category?

**Q3. What parameterizations have been tested in the literature?**
The "Hash Ribbons" concept was popularized by Charles Edwards (Capriole Investments). What MA combinations (30/60, 14/28, 60/90, etc.) have been tested? Does the signal require a specific combination to produce sign-stable results, or is it robust across parameterizations?

**Q4. What are the known failure modes and false signals?**
The China mining ban (2021) caused a sharp hash rate crash NOT driven by miner profitability — miners were forced offline by regulation, not economics. In this case, the signal would have fired (hash rate fell, 30MA < 60MA) but BTC price recovered immediately (not the expected recovery pattern after capitulation). Are there other known false-signal scenarios? How does one distinguish economic capitulation from regulatory/logistic hash rate drops?

**Q5. Can this clear PF>1.5 at 14-day resolution?**
The signal fires infrequently (roughly once per 18-24 months, at major BTC cycle bottoms). A 14-day walk-forward window is a short measurement interval. The actual signal HOLD PERIOD is typically 30-90 days. Can this mismatch cause the signal to appear sign-UNSTABLE in 14-day windows even if the underlying edge is real? Would a longer window (30-day, 60-day) be more appropriate? If restricted to 14-day windows, can the effect size (eff >= 0.30) realistically be achieved?

## Verdicts Required

For each question, give:
- **Answer:** [clear yes/no or specific finding]
- **Evidence/Reasoning:** [concrete mechanism, literature citation, or logical argument]
- **Impact on H-032:** [how this affects the recommendation to pre-register]

At the end, give an overall recommendation:
- **PRE-REGISTER** — the signal passes all five tests, proceed with M-107 pre-registration
- **PRE-REGISTER WITH CAVEAT** — pre-register but note specific parameterization or scope constraint required
- **DO NOT PRE-REGISTER** — one or more tests have a critical flaw that makes this signal unlikely to pass the harness

# Feedback Received + Action Items — 2026-05-19

**Session:** CX2 (autonomous continuation)
**Generated:** 2026-05-19

---

## Feedback Received

### Source 1: OpenRouter Swarm Ring (two independent runs, $0.01/$0.02, 11%/17%)

**Prompt submitted:** "Algo system, 11/11 pre-registered causal hypotheses killed by a walk-forward sign-stability harness (eff>=0.30, same sign in >=3/5 14-day windows, net of 30bps). For CRYPTO/EQUITY/FOREX/COMMODITY/FUTURES/BOND/ETF name ONE concrete causally-grounded retail-accessible strategy that could plausibly clear PF>1.5 net of cost AND survive sign-stability. Signal + data source + causal mechanism. Forbidden: COT, funding-rate directional, roll-yield, yield-curve momentum, PEAD, funding-arb carry, options-flow, on-chain counts, funding-settlement cascade, exchange net-flow, cross-exchange premium."

**Both runs converged on the same recommendation:**

---

### SWARM RECOMMENDATION: BTC Miner Capitulation / Hash Ribbon Signal

**Asset Class:** CRYPTO (BTC specifically)

**Signal Rule:**
- **Entry:** Go LONG BTC when (a) estimated daily miner profit margin per TH/s drops below zero (revenue < electricity floor) AND (b) 30-day MA of hash rate crosses below 60-day MA (confirming active capitulation / miner shutdowns)
- **Exit:** When 30-day MA of hash rate crosses back above 60-day MA (selling cohort exhausted)

**Data Sources (all free, no API key):**

| Input | Source | Frequency |
|---|---|---|
| BTC spot price | Binance/CoinGecko API | 1-minute |
| Network hash rate | mempool.space API or blockchain.com | Daily |
| Block subsidy + avg TX fees | mempool.space block data | Per block |
| ASIC efficiency estimate (J/TH) | Cambridge CBECI or difficulty-derived | Monthly proxy |
| Electricity cost | EIA US average commercial (~$0.10-0.12/kWh) | Monthly refresh |

**Causal Mechanism (structural, not statistical):**
1. BTC mining = commodity production business with hard variable-cost floor (electricity ~60-80% of OpEx)
2. ASIC hardware is sunk cost; marginal decision: does daily revenue/TH exceed electricity cost/TH?
3. When revenue < electricity cost, miners MUST sell BTC to pay utility bills — involuntary supply pressure
4. Marginal producers (least-efficient rigs) shut off first, progressively removing selling pressure AND hash rate
5. Hash rate decline = observable signature of selling cohort shrinking
6. When hash rate recovers: (a) supply shock exhausted, (b) difficulty adjustment lags ~2,016 blocks creating temporary revenue boost for survivors, (c) structural buyers recognize the bottom
7. **Sign direction is fixed by physics:** miners always sell when unprofitable. The signal cannot flip across regimes.

**Why It Clears PF > 1.5:**
- Signal fired 4-5 times in 2014-2024 (BTC bottoms 2015.01, 2018.12, 2020.03, 2022.11)
- Subsequent 3-6 month returns: +80% to +250% per occurrence
- Round-trip transaction cost: <15bps (spot exchanges) vs 30bps budget → significant headroom
- Self-reinforcing exit (hash cross) avoids whipsaw — slow-moving MA cross is structural, not noisy

**Why It Survives Sign-Stability:**
- 11/11 prior kills had behavioral causal links (sentiment/positioning/momentum herding) that flip across regimes
- Miner capitulation is a **physical constraint**: electricity > revenue → sell. Cannot invert.
- Effect size: forced selling creates measurable price depression; forward 14-day returns conditional on signal active are consistently positive (backtested eff 0.4-0.8 range)
- Net of 30bps: entry/exit slippage + fees ≈ 10-15bps total. 15bps buffer absorbed by slow-moving exit rule.

**NOT on forbidden list:** Not COT, not funding-rate directional, not roll-yield. Hash rate is an economic/physical metric (computational power committed), not an "on-chain count" (address count, transaction count, wallet count, etc.). The distinction: on-chain counts are aggregate network activity statistics; miner economics is fundamental analysis of a specific industry participant class.

---

### Source 2: H-028 Form 4 Implementation (this session)

**Feedback from run results:**
- EDGAR EFTS API works correctly: 165 hits for AMC, 78 for GME, 260+ for others
- Ownership XML fetch works: `primary_doc.xml` with `ownershipDocument` tag confirmed
- Code-P extraction works: SOFI (4 purchases, 2 insiders), CLF (6 purchases, 5 insiders) confirmed
- **BUT:** The test universe (UNIVERSE_FULL — meme/volatile small-caps) has structurally insufficient code-P cluster events. AMC's first 20 Form 4 XMLs: 0 code-P transactions.
- Root cause: Meme stock executives use options/RSUs for compensation. They don't do open-market purchases. The published academic results (Jeng et al., Cohen-Malloy-Pomorski) use broad cross-sectional small-cap universes across sectors (financials, industrials, energy), not pre-selected volatile tickers.
- **Conclusion:** The code works. The verdict is universe-limited, not code-limited. A broader Russell-2000-style diverse universe across sectors would be required to test H-028 meaningfully.

---

## Action Items

### IMMEDIATE (before next session)

| # | Action | Owner | Blocker |
|---|---|---|---|
| A-1 | Pre-register BTC Miner Capitulation as new hypothesis (H-032) per M-107 | Claude Code | Needs user approval to proceed |
| A-2 | Check H-021 (COT small-spec) re-run — scheduled ~2026-05-26, currently 2/3 windows same-sign eff 1.48/1.21 | Auto (next session) | Wait for COMMODITY picks to resolve |
| A-3 | Re-run 4 GitHub Actions workflows (already done: Gate Config Emit, Adaptive Trust Tuner, DB Freshness Guardian, Strategy Health Monitor) | DONE this session | N/A |

### SHORT-TERM (1-7 days)

| # | Action | Owner | Notes |
|---|---|---|---|
| A-4 | If H-032 approved: build `tools/h032_btc_miner_capitulation.py` with mempool.space hash rate fetch, Cambridge CBECI electricity proxy, profit margin computation, and walk-forward harness run | Claude Code | Needs M-107 pre-registration first |
| A-5 | H-027 (CO-1 inventory surprise): Register at eia.gov for free EIA_API_KEY, set env var, re-run `tools/co1_commodity_inventory_surprise_research.py` | User or Claude | Free API key — 5 min registration |
| A-6 | H-028v2 (insider cluster buy, diverse universe): If pursuing, pre-register a new hypothesis with a Russell-2000-style 100+ ticker universe across financials/industrials/energy/healthcare sectors | Claude Code | Needs user approval |
| A-7 | Run swarm on BTC miner capitulation signal before pre-registering — get multi-engine validation on the causal mechanism and cost model | Claude Code via tools\swarm_v2 | Can do now |

### STRATEGIC (>7 days / waiting on data)

| # | Action | Owner | Notes |
|---|---|---|---|
| A-8 | H-021 check ~2026-05-26: Re-run `tools/hypothesis/h021_cot_smallspec_harness.py`. If 3rd window passes (eff>=0.30, same sign), H-021 becomes ADMISSIBLE → proceed to shadow implementation | Claude Code | Wait for natural pick resolution |
| A-9 | MySQL dedup fix (INSERT IGNORE on dedup_hash): Swarm's #1 lever for pf_registry accuracy. Requires MySQL access — coordinate with user | User + Claude | Not locally fixable |
| A-10 | B10 UEPS gate: Auto-resolves ~2026-05-22 when ≥10 UEPS closed picks accumulate. No code action needed. | Auto | Wait |

---

## Hypothesis Status Summary (as of 2026-05-19)

| ID | Family | Status | Next Action |
|---|---|---|---|
| H-001 | COT positioning (CT=F) | LIVE_TESTING — 2/3 windows | Wait for 3rd window |
| H-002 | PEAD daily | SHADOW_IMPLEMENTATION | Active |
| H-003 | Funding-rate cross-TF | SHADOW_LIVE | Active |
| H-004 | CI Workflow | PENDING_IMPLEMENTATION | Active (earnings surprise) |
| H-005 | Realized_vol_z | FAILED_ARCHIVED | — |
| H-009 | Order-flow delta | KILLED | — |
| H-011 | Stablecoin_flow_ratio | KILLED | — |
| H-019 | Vol-cluster CRYPTO v1 | REJECTED | — |
| H-021 | COT small-spec exhaustion | NEAR_ADMISSIBLE 2/3 | Re-run 2026-05-26 |
| H-023 | Futures open-interest velocity | TESTED_KILL | — |
| H-027 | CO-1 inventory surprise | UNTESTED — needs EIA_API_KEY | A-5 above |
| H-028 | E-1 insider cluster buy | UNTESTED-DATA-GAP | A-6 if pursuing |
| H-029 | Vol-cluster CRYPTO v2 | TESTED_KILL | — |
| H-030 | Small-cap liq-shock EQUITY | TESTED_KILL | — |
| H-031 | Agricultural harvest seasonality | UNTESTED — density gap | Low priority |
| **H-032** | **BTC Miner Capitulation** | **PROPOSED (swarm rec)** | **A-1 / A-4 / A-7** |

---

## Key Insight from Swarm (Core Learning)

**Why 11/11 hypotheses failed and what survives:**

The harness kills behavioral mechanisms (sentiment, momentum herding, positioning) because these mechanisms *can flip their sign across market regimes*. A momentum signal works in trending markets but reverses in choppy markets. Funding-rate signals work in contango but not in backwardation. COT signals have sign flips between crowded vs. uncrowded conditions.

**What survives:** A signal whose causal mechanism is **structural** (cannot be reversed by market regime):
- Physical constraints (electricity cost floor for miners)
- Legal requirements (SEC filing deadlines, mandatory insider disclosure)
- Accounting identities (EIA inventory = production + imports - consumption - exports)
- Supply chain physical bottlenecks (refinery crude throughput below crack spread breakeven)

The miner capitulation signal satisfies this test. The causal chain is: unprofitable → must sell → supply shock → price depression → capitulation exhausted → recovery. This chain cannot be reversed by bull/bear market conditions — it operates at the microeconomic level of individual mining operations.

---

## Swarm Further Feedback Recommendation

**Use `tools\swarm_v2`** (not `tools\swarm` — that directory doesn't exist).

Suggested next swarm prompt (to validate H-032 before M-107 pre-registration):

```
python tools/swarm_v2/swarm_run.py --task "Validate BTC Miner Capitulation hypothesis (Hash Ribbon + profit margin cross): 
(1) Is the causal mechanism (miners MUST sell when electricity cost > revenue) valid?
(2) Is hash rate (mempool.space) a defensible non-'on-chain-count' metric per the forbidden list?
(3) What parameterizations (30/60MA vs 14/28MA vs 7/30MA) have been tested in literature?
(4) What are the failure modes (false signals: hash rate drops for non-cost reasons — e.g., China mining ban)?
(5) Is PF>1.5 achievable at 14-day resolution, or does the signal require 30-90 day hold to clear costs?"
--agents 3 --strict
```

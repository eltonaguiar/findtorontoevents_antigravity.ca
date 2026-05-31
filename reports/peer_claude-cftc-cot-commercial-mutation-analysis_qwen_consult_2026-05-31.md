=====PROMPT=====
You are a quantitative-strategy reviewer applying the three-axis mutation protocol (entry-rule axis / exit-rule axis / symbol-universe axis) to decide whether to rehab or formally retire a trading strategy.

STRATEGY: `cftc_cot_commercial_signal`
PURPOSE: Trade commodity futures based on weekly CFTC Commitments-of-Traders (COT) report — go LONG when commercial hedgers' net position is at multi-year low (they are bullish), SHORT when commercial position is at multi-year high (they are bearish). COT data released weekly with 3-day publication lag. Source family: institutional fundamental positioning data, not technical.

LIVE DB STATE (ejaguiar1_stocks.trading_picks, category=commodity, lifetime, 2026-05-31):
- Total picks: 37
- TP_HIT: 3 (2 SHORT CT=F/KC=F avg +4.76%, 1 LONG KC=F +0.70%)
- LOST: 2 (both SHORT CT=F and ZW=F, avg -5.08%)
- TIME_EXIT (held to time-out, pnl=0): 30 (26 SHORT, 4 LONG) — spread across CL=F, CT=F, KC=F, NG=F, ZC=F, ZS=F, ZW=F
- OPEN: 2 SHORT GC=F

By-symbol breakdown:
- CT=F (cotton): 1 LOST, 4 TIME_EXIT, 2 TP_HIT — 2W/1L/4 wash
- ZW=F (wheat): 1 LOST, 7 TIME_EXIT — 0W/1L/7 wash
- ZS=F (soybean): 7 TIME_EXIT — 0W/0L/7 wash
- CL=F (crude oil): 6 TIME_EXIT — 0W/0L/6 wash
- KC=F (coffee): 2 TIME_EXIT, 1 TP_HIT — 1W/0L/2 wash
- NG=F (nat gas): 2 TIME_EXIT
- ZC=F (corn): 2 TIME_EXIT
- GC=F (gold): 2 OPEN

INCIDENT SNAPSHOT (7d window 2026-05-20): n=20, WR=5.0%, PF=0.113, sum -65.79% (the "19% WR on n=16" referenced in the incident is a similar 7d-class panel).

DECISIVE-ONLY WR (TP_HIT vs LOST, ignoring TIME_EXIT washes): 3/5 = 60% — but n is too small.
ALL-CLOSED WR (TIME_EXIT counted as not-win): 3/35 = 8.6%.

KEY ANOMALY: 30/37 (81%) of picks expire at TIME_EXIT with pnl≈0. This means signals are entered but neither TP nor SL fires within the holding window. The pattern strongly suggests the exit-rule axis is mistuned, not necessarily the entry signal.

EXISTING SAFEGUARDS:
- 72h dedup window (one CFTC report cycle) on COT_DEDUP_SYSTEMS.
- -10 score penalty when paired with multi_asset_copytrader.
- Optional 30% COMMODITY source-concentration cap (M-046, currently OFF).
- M-096 CT=F symbol cap at 40% of OPEN commodity (ON).
- NOT in PERMANENTLY_KILLED_STRATEGIES.

TASK — apply the three-axis mutation protocol. For each axis propose AT MOST 1-2 mutations:

AXIS 1 — ENTRY RULE: What entry-rule mutation would help (e.g., add a momentum confirm; require z-score extremity; restrict to weekly close after COT release)?

AXIS 2 — EXIT RULE: Given 81% TIME_EXIT washes, what exit-rule mutation would matter most (e.g., extend holding period to next COT release; widen TP/SL; convert to mean-reversion target instead of fixed bp; add trailing stop)?

AXIS 3 — SYMBOL UNIVERSE: Restrict to CT=F+KC=F (the only symbols with any TP_HIT)? Drop CL=F (6 washes, 0 wins)? Drop grains (ZW/ZS/ZC: 0W, 1L, 16 wash)?

THEN: If NO mutation can plausibly achieve WR ≥ 30% on the small sample, recommend FORMAL RETIREMENT (add to PERMANENTLY_KILLED_STRATEGIES). Otherwise recommend specific mutation to test in shadow mode for N picks before re-admit.

Return your analysis as structured markdown (## Axis 1 / ## Axis 2 / ## Axis 3 / ## Verdict).

=====RESPONSE=====
## Axis 1 — ENTRY RULE

### Proposed Mutations:
1. **Add Momentum Confirmation:**
   - **Description:** Introduce a momentum-based confirmation to the entry signal. For example, require that the commodity's price is also showing a strong trend in the same direction as the COT signal (e.e., a positive momentum for a long signal and negative momentum for a short signal).
   - **Rationale:** This can help filter out false signals and ensure that the market is moving in the expected direction, potentially increasing the win rate.

2. **Require Z-Score Extremity:**
   - **Description:** Only enter trades when the commercial hedgers' net position is at an extreme z-score (e.g., more than 2 standard deviations from the mean).
   - **Rationale:** This would make the entry criteria more stringent, focusing on more significant and potentially more reliable signals.

## Axis 2 — EXIT RULE

### Proposed Mutations:
1. **Extend Holding Period to Next COT Release:**
   - **Description:** Hold positions until the next COT report is released, rather than using a fixed holding period.
   - **Rationale:** This aligns the exit with the periodicity of the data source and allows more time for the trade to develop, potentially reducing the number of TIME_EXIT washes.

2. **Widen TP/SL:**
   - **Description:** Increase the take-profit (TP) and stop-loss (SL) levels to allow for more price movement before exiting.
   - **Rationale:** Wider TP/SL levels can reduce the likelihood of being stopped out prematurely, especially given the 3-day publication lag and the potential for price volatility.

## Axis 3 — SYMBOL UNIVERSE

### Proposed Mutations:
1. **Restrict to CT=F + KC=F:**
   - **Description:** Limit the strategy to trading only cotton (CT=F) and coffee (KC=F), as these are the only symbols with any TP_HIT.
   - **Rationale:** Focusing on the symbols that have shown some success can improve the overall performance and reduce the noise from underperforming symbols.

2. **Drop CL=F (Crude Oil):**
   - **Description:** Remove crude oil (CL=F) from the symbol universe, as it has 6 TIME_EXIT washes and no wins.
   - **Rationale:** Eliminating symbols that consistently result in washes can help clean up the strategy and focus on more promising opportunities.

## Verdict

Given the current performance metrics and the key anomaly of 81% of picks expiring at TIME_EXIT with pnl≈0, the following mutations are recommended:

- **Entry Rule Mutation:** Add momentum confirmation to the entry signal.
- **Exit Rule Mutation:** Extend the holding period to the next COT release.
- **Symbol Universe Mutation:** Restrict the strategy to CT=F and KC=F, and drop CL=F.

These mutations aim to address the issues with the entry and exit rules and focus on the most promising symbols. However, given the small sample size and the current decisive-only WR of 60% (which is still based on a very small n=5), it is recommended to test these mutations in shadow mode for N picks (e.g., 50 picks) before re-admitting the strategy to live trading. If the performance does not improve to a WR ≥ 30% after the shadow testing, the strategy should be formally retired and added to PERMANENTLY_KILLED_STRATEGIES.

=====META=====
{
  "model": "qwen-max",
  "usage": {
    "prompt_tokens": 1030,
    "completion_tokens": 722,
    "total_tokens": 1752,
    "prompt_tokens_details": {
      "cached_tokens": 0
    }
  },
  "id": "chatcmpl-44aec6d3-767f-92c7-af00-0a0d279ba55d"
}

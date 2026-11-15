# Pre-Registered Forward Paper-Trading Protocol (`PROOF_PROTOCOL.md`)

**Run ID:** `2026-11-15_0725_inspect-wt` | **Status:** Pre-Registered Forward Certification Protocol  
**Tracker Ledger:** [predictions_tracker.csv](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/tracker/predictions_tracker.csv) | [predictions_tracker.html](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/tracker/predictions_tracker.html)

---

## 1. Eligible Candidates & Frozen Pre-Registered Parameters

Per `STRATEGY_SHORTLIST.md`, zero candidates passed 10/10 proof gates (`PROVEN = 0`). Only the two `PROMISING (NEAR-MISS)` monthly rotation strategies—plus two strictly non-capital shadow watches (`MA1` and `CM1`)—enter forward certification. All hyperparameters are frozen via SHA-256 (`experiment_configs.json`); post-hoc parameter tuning voids the trial and resets the observation clock.

| Trial ID | Scope & Status | Frozen Entry & Rebalance Rule | Frozen Risk / Exit / Cost Rule | Benchmarks & Hurdle |
|---|---|---|---|---|
| **`E1_ETF_DualMom_VolTarget`** | **Primary Forward Paper Sleeve** (`TFSA / RRSP` CAD simulation) | Monthly on last TSX/NYSE trading close `t-1`: compute `12-1` total return `close[t-2]/close[t-14]-1` on `{SPY, EFA, EEM, TLT, IEF, GLD, VNQ, DBC, QQQ, IWM}`. Select top `K=2` strictly exceeding trailing 12m T-bill `rf = 2.5%/yr`; hold remainder in CAD/USD T-bill ETF (`CBIL/SGOV`). | Weight by inverse trailing 12m volatility capped at `50%` per ETF; scale total risky exposure by `min(1.0, 0.12 / trailing_12m_port_vol)`. Zero discretionary intramonth overrides. Deduct `10 bps` round-trip per rebalance turnover. | Beat `60/40 SPY/AGG` on risk-adjusted net Sharpe **and** cut realized drawdown vs `SPY B&H` over forward horizon. |
| **`M1_MutualFund_Sleeve_CAD_Tax`** | **Low-MER Index Mutual Fund Equivalent** (`>= 30d` hold cadence) | Identical `E1` `12-1` top-2 signal executed at next-day 16:00 ET forward NAV using zero-load D/F-series index mutual funds (`<= 0.15%/yr` MER). | Enforce strict minimum `>= 30` calendar day hold between switches (zero early-redemption penalty compliance). Model `0.15%/yr` MER drag and `26.76%` Ontario non-registered cap-gains sensitivity vs `0%` TFSA. | Positive net excess over `rf = 2.5%/yr` and superior Sharpe vs `1.80%/yr` retail active MER comparator. |
| **`MA1_VariantC_MetaSelector`** *(Shadow Only)* | **Zero-Capital Statistical Power Accumulation** (`n=237 -> 500`) | Monthly selection on day 1 UTC: rank `/audit` strategies using strictly closed prior months (`train_n >= 20, train_PF > 1.3`), select top `<= 6` strategies. | Apply conservative `10 bps` round-trip + intrabar `SL_HIT` collision rules (`tools/stop_fill_replay.py`); quarantine any pick without live Yahoo/Binance mark-to-market price feed. | Reach `n >= 500` clean OOS closed trades with `p_random_selector < 0.01`, bootstrap `PF LB > 1.0`, and `OOS WFE >= 0.50`. |
| **`CM1_Commodity_Gold_Trend`** *(Shadow Only)* | **Secular Regime Watchlist** (`GLD / DBC / Cash`) | Monthly `12-1` momentum selector on `{GLD, DBC}` holding top-1 only when excess return `> rf`, `12%` vol target, `20 bps` RT cost. | Hard cash floor whenever both `GLD` and `DBC` `12-1` momentum turn negative; zero crude oil single-contract futures (`OIL` permanently banned). | Positive net return across next **full macro rate/inflation flip** without losing `Shuffle p < 0.05`. |

---

## 2. Duration, Sample-Size Floors & Logging Architecture

1. **Multi-Horizon Graduation Floors (Aligned with `TESTING_PROTOCOL.MD`):**
   - **Short Horizon (`<= 1d`):** `FOREX` and intraday `CRYPTO` remain **HARD-DISABLED (`0` capital)**. Any future candidate must accumulate `n >= 500` live paper trades over `>= 90` calendar days across >= 2 volatility regimes.
   - **Swing Horizon (`1d–3mo`, e.g. `MA1`):** Minimum **`n >= 500` resolved OOS picks** spanning **`>= 12` contiguous calendar months** (`>= 60` new OOS picks beyond `n=237` only as interim checkpoint at `n=350`, full decision at `n=500`).
   - **Monthly Structural Horizon (`> 3mo`, e.g. `E1`, `M1`, `CM1`):** Minimum **`24` contiguous forward monthly rebalances (`2` full years)** yielding `n >= 24` live forward periods appended to the `165`-month historical record (and spanning at least one `SPY` drawdown `> 10%` or sideways consolidation regime).
2. **Audit Tracking Surface & Integrity Rules:**
   - Every forward decision is appended BEFORE execution (`t-1` close timestamp) to [predictions_tracker.csv](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/tracker/predictions_tracker.csv) and mirrored to `findtorontoevents.ca/audit` (`picks_now.json` / forward ledger).
   - **Mandatory Hygiene Gates (Addressing Phase 2 Implementation Gaps):**
     1. Zero synthetic ticker contamination (`EURUSDT` forbidden in `FOREX`; sports contracts forbidden in financial tables).
     2. Spot-quote sanity assertion on ingest (`abs(entry_price / live_quote - 1) <= 0.10`, blocking `EURGBP=X = 688.17` / `XRPUSDT = 0.0`).
     3. Zero fake `0%` `TIME_EXPIRED` overwrites: mark open positions to live bid/ask/NAV daily and resolve intrabar SL-before-TP strictly.
     4. Unique immutable `tracker_id` primary key (`NO` duplicate daily inserts like `live_pnl_tracker.py` `4,390/185` inflation).

---

## 3. Binary Go / No-Go Decision Thresholds & Abort Circuit Breakers

### Promotion Criteria (Eligible for Real Capital Pilot at <= 5% Portfolio Weight)
A candidate graduates from `PROMISING (NEAR-MISS)` / `SHADOW_WATCH` to `PROVEN` **only if all conditions hold at checkpoint**:
1. Realized forward OOS post-cost, post-CAD-tax CAGR exceeds `2.5%/yr` risk-free benchmark AND matches/beats its pre-registered benchmark Sharpe (`E1/M1 >= 0.54` or superior `Calmar` with `-20%` lower MaxDD than `SPY B&H`).
2. Combined historical + forward **95% Circular Block Bootstrap CI** on excess return excludes zero (`CI_low > 0`).
3. **Deflated Sharpe Ratio** at repo-wide multiplicity `N_repo` crosses `>= 0.95` (or formally pre-registered clean out-of-sample replication period achieves two-sided `p < 0.01` *strictly on the unseen forward window* independent of legacy historical data mining, where `N_forward = 2` eliminates the 646-trial historical penalty!).
4. Live forward Sharpe ratio maintains `WFE >= 0.50` relative to prior OOS split (`2019–2026`), and slippage/spread realization stays within `<= 1.5x` modelled bps (`<= 15 bps` RT for `E1`).

### Automatic Mid-Flight Abort Triggers (Kill Immediately, Do Not "Tweak")
- **Drawdown Abort:** Forward cumulative net drawdown breaches **`-20.0%`** (consistent with `alpha_engine/money_ready_verdict.py` `MDD_GATE_THRESHOLD = 0.20`).
- **Statistical Decay Abort:** Cumulative rolling net Profit Factor over `n >= 20` swing trades (`MA1`) or `12` forward months (`E1/M1`) drops below **`0.95`** OR rolling 12m slippage exceeds **`50%` of modelled breakeven margin**.
- **Execution Integrity Abort:** Any single unflagged corrupt quote ingest, duplicate-key PnL inflation, or unmodeled fee violation automatically freezes capital promotion pending root-cause fix and documentation in `updates/`.

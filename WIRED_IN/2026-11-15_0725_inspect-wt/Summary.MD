# Quant Research Audit & Proof Summary (`WIRED_IN/2026-11-15_0725_inspect-wt`)

**Timestamp (UTC):** 2026-11-15_0725  
**Worktree / Author ID:** `inspect-wt` (clean push via `.fix-wt` to `origin/main`)  
**Status:** Phase 0–7 Complete (All Deliverables Verified, Seeded Proof Executed, Tracker Built)  
**Design & Methodological References (explicit per `SOUL.md`):**
- **Marcos López de Prado** (*Advances in Financial Machine Learning*; Bailey & López de Prado 2014 *The Deflated Sharpe Ratio*) — multiple-testing adjustment (`DSR`), Probability of Backtest Overfitting (`PBO`), combinatorial/walk-forward temporal discipline, and purged evaluation.
- **Ernest Chan** (*Quantitative Trading*; *Algorithmic Trading*) — friction & borrow reality, realistic cost sensitivity, fractional Kelly sizing, and regime separation.
- **Edward Tufte** (*The Visual Display of Quantitative Information*) — high data-ink ratio, zero-slop tabular precision in Markdown reports and HTML prediction trackers.

---

## 1. Execution Plan & Folder Architecture

```text
WIRED_IN/2026-11-15_0725_inspect-wt/
├── Summary.MD                       # Living document (created first, updated per phase)
├── AUDIT_REPORT.md                  # Phase 1 & 2 full audit (inventory, failure taxonomy, methods catalogue)
├── STRATEGY_SHORTLIST.md            # Ranked evaluation across all 10 proof steps & Phase 5 metrics
├── PROOF_PROTOCOL.md                # Pre-registered forward paper-trading & certification protocol
├── negative_result_diagnosis.md     # Populated candidate failure matrix, near-miss register, passive pivot blueprint
├── harvested_ideas/
│   ├── repo_miner.py                # Layer A (regex archaeology + dependency triage) + Layer B (semantic mapper)
│   ├── 00_inventory.csv             # Machine-mined + semantically mapped repository inventory
│   ├── 01_failures_taxonomy.md      # 10-mode forensic failure analysis with file citations
│   ├── 02_methods_catalogue.md      # Verbatim catalogue of statistical/ML/risk methods + dependencies
│   ├── stocks.md                    # Asset-class harvest: Equity / Stocks
│   ├── crypto.md                    # Asset-class harvest: Crypto
│   ├── forex.md                     # Asset-class harvest: Forex
│   ├── bonds.md                     # Asset-class harvest: Bonds / Fixed Income
│   ├── etfs.md                      # Asset-class harvest: ETFs
│   ├── mutual_funds.md              # Asset-class harvest: Mutual Funds
│   ├── commodities.md               # Asset-class harvest: Commodities / Futures
│   └── multi_asset.md               # Asset-class harvest: Multi-Asset / Meta-Selection / Prediction Markets
├── Plan/
│   ├── README.md                    # Reuse registry linking existing repo /Plan folders
│   ├── stocks/PLAN.md               # Pre-registered Experiment S1
│   ├── crypto/PLAN.md               # Pre-registered Experiment C1
│   ├── forex/PLAN.md                # Pre-registered Experiment FX1
│   ├── bonds/PLAN.md                # Pre-registered Experiment B1
│   ├── etfs/PLAN.md                 # Pre-registered Experiment E1
│   ├── mutual_funds/PLAN.md         # Pre-registered Experiment M1
│   ├── commodities/PLAN.md          # Pre-registered Experiment CM1
│   └── multi_asset/PLAN.md          # Pre-registered Experiments MA1 & MA2
├── experiments/
│   ├── experiment_configs.json      # Pre-registered experiment specs & parameters
│   ├── live_picks_snapshot.json.gz  # Portable 240KB snapshot of live /audit payload (SHA-256 hashed)
│   ├── run_proof_suite.py           # Seeded (SEED=42) 10-step proof & Phase 5 metric evaluator
│   └── experiment_results.json      # Complete reproducible output + SHA-256 dataset hashes
├── proof/
│   ├── walk_forward_results.json    # WFO fold returns, WFE, parameter neighborhood heatmaps
│   ├── monte_carlo_results.json     # Plain & circular block bootstrap (2,000 paths each)
│   ├── significance_and_dsr.json    # DSR (N=9 & N=646), White's Reality Check, Holm-Bonferroni, shuffle null
│   ├── regime_and_equity_curves.json# Bull/Bear/Sideways & High/Low Vol breakdowns + Gross/Net/After-Tax curves
│   └── PROOF_SUMMARY_TABLE.md       # Clean Tufte-style matrix of all 9 candidates
└── tracker/
    ├── build_tracker.py             # Generates CSV + HTML viewer matched to /audit live picks
    ├── predictions_tracker.csv      # Multi-horizon tracker (<=1d, 1d-3mo, >3mo)
    └── predictions_tracker.html     # Interactive Tufte-style dashboard viewer
```

---

## 2. Phase Log (Updated Live)

| Phase | Description | Status | Artifact(s) |
|---|---|---|---|
| **Phase 0** | Governance & Living Document Initialization | **COMPLETE** | `Summary.MD` |
| **Phase 1–2** | Repo Archaeology (`repo_miner.py`), Dependency Triage, Failure Taxonomy, Methods Catalogue, 8 Asset-Class Harvests (`6,639` inventory rows, `30` manifests, `120` unique packages) | **COMPLETE** | `harvested_ideas/*` |
| **Phase 3** | Pre-Registered Experiment Plans (`Plan/<asset_class>/PLAN.md`, 8/8 asset classes covering 9 trials `E1, M1, MA1, MA2, S1, C1, B1, CM1, FX1`) | **COMPLETE** | `Plan/*` |
| **Phase 4–5** | 10-Step Non-Negotiable Proof Suite + Phase 5 Statistical & Risk Metrics + Canadian Tax/Friction (`SEED=42`, `2,000` MC paths, `200` shuffle runs) | **COMPLETE** | `experiments/*`, `proof/*` |
| **Phase 5b** | Multi-Horizon Prediction Tracker reconciled to `/audit` (`69` rows across `<=1d`, `1d-3mo`, `>3mo`) | **COMPLETE** | `tracker/*` |
| **Phase 6** | Core Deliverables (`AUDIT_REPORT.md`, `STRATEGY_SHORTLIST.md`, `PROOF_PROTOCOL.md`, `negative_result_diagnosis.md`) | **COMPLETE** | Root deliverables |
| **Phase 7** | Finalize `Summary.MD`, document in `updates/`, commit via `.fix-wt`, push & verify `origin/main` | **COMPLETE** | `updates/*`, `origin/main` |

---

## 3. One-Page Executive Summary

### Bottom-Line Verdict (`PROVEN = 0 / 9`)
Across **all 8 financial asset classes** tested on `findtorontoevents_antigravity.ca` under the non-negotiable 10-step Proof Standard (`WFO`, `DSR >= 0.95` at `N=646`, `Holm p < 0.05`, `2,000`-path plain & circular block bootstrap, Canadian TFSA/taxable friction, `Bull/Bear/Sideways x High/Low Vol` regimes, `200`-run permutation shuffle control, live tracker, and `SEED=42`), **zero active or systematic strategies currently prove live profitability beyond a shadow of a doubt.**

### Direct Answers to Core Strategic Questions
1. **Which asset class(es) & timeframe(s) work best (and worst)?**
   - **Closest Near-Misses (Monthly, `>= 30d` / `21d` rebalance):** Low-cost **Index Mutual Funds (`M1`, `0.15%` MER: `+7.49%` net, `0.45` Sharpe, `7/10` gates)** and **ETFs (`E1`, `10 bps` RT: `+7.31%` net, `0.44` Sharpe, `7/10` gates)** using monthly `12-1` dual momentum + inverse-12m volatility + `12%` portfolio vol target. **However**, neither beat static passive `SPY B&H` (`+12.82%`, `0.747` Sharpe) nor `60/40 SPY/AGG` (`+7.31%`, `0.538` Sharpe, `-21.0%` MaxDD) over `2013-01..2026-10`, and both failed `DSR`, `t-test` (`p=0.097/0.108`), and shuffle null (`p=0.655`). Note that typical `1.80%/yr` Canadian active retail mutual-fund MERs erode `M1` by `-1.54%/yr` (`+5.95%` net).
   - **Genuine Trend Timing Edge Outside In-Sample WFO (`CM1`, Commodities `GLD/DBC` Monthly):** Delivered `+9.08%` net CAGR (`0.593` Sharpe, `PF 1.99`, `-18.8%` MaxDD vs `-37.4%` GLD / `-61.7%` DBC, `96.2%` positive block MC with `+5.19%` 5th-percentile worst path) and was the **only strategy beating permutation shuffle (`p=0.0050`)**, yet failed WFO because the 2013–2019 gold bear produced `IS Sharpe = -0.403`.
   - **Active Intraday/Swing Pick Engines & Toxic Classes (`REJECT`):**
     - **Forex (`FX1`):** `-1.04%` CAGR, `-1.965` Sharpe, `breakeven 4.2 bps < 8.0 bps` spread/swap (`19` synthetic `EURUSDT` leaks in raw feed). **Hard-disable permanently (`FOREX_HARD_DISABLE=1`).**
     - **Crypto (`C1` + OKX Funding + Live `n=1,966`):** 1h causal BTC trend lost `-24.93%` (`Sharpe -2.58`, `0 bps` breakeven); `/audit` `CRYPTO` cohort averaged `-0.551%/trade` net (`PF 0.716`); OKX 51-day BTC funding netted only `+0.29%/yr` after `20 bps` turnover (`-0.41%/yr` on SOL).
     - **Equities (`S1`):** Collapsed from `IS Sharpe +2.427` to **`OOS -0.694`** (`WFE -0.286`, `-46.15%` in high-vol regimes).
     - **Bonds (`B1`):** `+0.74%` net (`+0.13%` after Canadian ordinary tax, `-0.203` Sharpe) trailed `2.5%/yr` T-bill cash.
2. **Exact Recommended Trading Parameters (For Forward Paper Certification Only — `$0` Live Speculative Capital):**
   - Use **`M1`/`E1`** strictly inside Canadian **`TFSA/RRSP` (`0%` tax)**: `12-1` lookback (`close[t-2]/close[t-14]-1 > rf`), Top-2 assets, inverse-12m vol capped at `50%`, `12%` portfolio vol target, monthly `>=30d` rebalance (`10 bps` RT cap), `-20%` cumulative drawdown abort, zero intraday TP/SL orders.
   - For immediate real-world savings/investment today: allocate via passive low-fee index core (`SPY`/`60-40` or Canadian asset-allocation ETFs), NOT `/audit` active pick generators.
3. **Why We Know Beyond Doubt Today That No Active System Passes:**
   - Every failure was pinned by reproducible `SEED=42` code ([run_proof_suite.py](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/experiments/run_proof_suite.py)) accounting for all `N=646` historical trials, full Ontario Canadian tax/cost schedules, circular block bootstrapping, and `200`-run price permutations.

---

## 4. Exact Reproducibility Commands

```bash
# 1. Re-run Phase 1-2 repository miner (against clean origin/main checkout)
python WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/repo_miner.py --scan-root .

# 2. Re-run seeded 10-step proof suite & generate all JSON + PROOF_SUMMARY_TABLE.md
python WIRED_IN/2026-11-15_0725_inspect-wt/experiments/run_proof_suite.py

# 3. Rebuild multi-horizon CSV & Tufte HTML prediction tracker
python WIRED_IN/2026-11-15_0725_inspect-wt/tracker/build_tracker.py
```


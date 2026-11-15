# 02 — Current State, Asset-Class Inventory, and Risk/Profitability Reality

## 1) Is any asset class currently proven profitable?
**No.** There is no asset class with a clean, pre-registered, net-of-cost, benchmark-relative, leak-safe, independently reproduced edge that has passed forward/paper gates.

- **Repo verdict (2026-11-14):** `audit_dashboard/data/money_ready_verdict.json` shows **CRYPTO** intrabar n=3705 WR 35.87% PF 0.9196 expectancy −0.0586 (`NOT_READY`, multiple gates failed) and **EQUITY** intrabar n=250 WR 59.2% PF 0.9392 (PF/DSR/SPA failed). Aggregate `asset_class_health` also shows stressed/insufficient classes (e.g. CRYPTO PF 0.289 stressed; ETF n=15 thin though PF 1.825).
- **Peer synthesis (reported):** `final_v4/flaxen-hair_2026-11-14T2304/` states 0/23 hypotheses survived clean OOS/effective-N/capital/execution gates, IC≈0, ~40% WR, all 9 classes `sizing_allowed: false` — *treat as reported synthesis; re-verify against canonical data for any deployment decision*.
- **Conclusion:** **Do not deploy capital** on the prediction system today.

## 2) Thorough list of asset classes/surfaces attempted to predict

| Asset class / surface | Coverage/status (repo-reported, time-varying) | Notes on recent reality | Key strategies/sources (examples) |
|---|---|---|---|
| **CRYPTO** | Highest volume | Verdict intrabar PF < 1, negative expectancy; historical “elite” slices often collapse on clean/net/forward basis | ML predictors, battleground/baby/incubator, KIMI/Mercury, copy-trader, TSMOM/MR/breakout, on-chain/sentiment (see `docs/ALL_STRATEGIES.md`) |
| **EQUITY (US)** | Active | Mixed (health watch PF ~0.88; verdict PF ~0.94 failing gates); best *research* candidate for benchmark test, not proven | multi_asset, stocks_competition/ml_gatekeeper, mean-reversion/factor/earnings-style modules |
| **ETF** | Sparse/thin upstream | Small-n apparent positives unreliable (inflation/mislabel risks noted historically); sometimes conflated with equity | etf_strategies.py, rotation/momentum/TAA paths |
| **BOND** | Very sparse | Insufficient n; marks/feeds historically fragile | bond_strategies.py + FRED/rates proxies |
| **FOREX** | Active but poor | Persistently weak after costs in snapshots | copy-trader + CTA/momentum paths |
| **COMMODITY** | Active/thin resolved | Mixed historical PF, low/unstable n and mark/roll concerns | CTA, COT, multi-asset, seasonality/carry ideas |
| **FUTURES** | Thin/noisy | Very small n, poor in current health; often overlaps commodity | futures/momentum scanners |
| **MUTUAL FUNDS** | **Effectively zero as tradable prediction class** | Infra/wiring gaps (NAV cache/ranker/metadata/pipeline) reported; `findmutualfunds2` present but not a proven production prediction path | ranker/metadata concepts (not money-ready) |
| **MEMECOIN / PENNY_STOCK** | Tracked in health in places | Tiny n / catastrophic or null PF; high risk | quarantine/experimental |
| **Related surfaces** | HyroTrader/prop, Quan, Mercury 2, Crypto ML Edge, Claude Gainer, DNA Genome/evolution, AI tournament/leaderboard, copy-trader intel, prediction-market signals | Discovery/forward-test surfaces; tournament/leaderboard metrics are not sizing-grade proof | dashboards: `/audit`, `/audit/hyrotrader`, pick funnel, active/closed picks |

*Exact counts/rates vary by snapshot; treat table as inventory + direction, not a fixed performance ledger.*

## 3) Highest probability of profitability with lower risk (realistic)

**Ranking (probability of positive real, risk-adjusted outcome):**
1. **Low-cost broad index ETFs + passive mutual funds (buy-and-hold / disciplined rebalance).** Highest practical probability over long horizons with lower avoidable risk; captures **market beta** (equity risk premium, bond carry/yield) at minimal cost. *Not ML/prediction alpha.*
2. **EQUITY — systematic, but only after validation.** Best *research* slot for a pre-registered, benchmark-relative test (e.g. vs SPY total return, net of costs). Unproven today.
3. **COMMODITY / selective BOND — low-frequency, diversified, cost-aware.** Only after data/mark/roll repair and robust net OOS; otherwise skip.
4. **ETF tactical / quality single-stock long-term satellites (e.g. NVDA-type).** Possible allocation tilts; concentration/volatility raise risk. Not a proven system signal.
5. **CRYPTO (conditional, narrow sleeves only).** High volatility/fill/funding/data risk; overall negative/unproven in current verdicts.
6. **FOREX.** Weakest in evidence; keep blocked/mutated.

**Beating benchmarks matters:** “profitable” must be judged **vs the right hurdle** (Section 3a) — not just >0 in isolation.

### 3a) Benchmarks and “real” win conditions (must state explicitly)
| Claim | Must beat / satisfy |
|---|---|
| Long-only equity/ETF alpha | **SPY/total-market total return** (risk-matched) net of costs |
| Cash alternative | **T-bills/SGOV-like** (risk-free hurdle) |
| Balanced allocation | **Matched benchmark blend** (e.g. 60/40) |
| Absolute trend/CTA | Cash/T-bill and/or managed-futures benchmark, with MDD/Calmar constraints |
| Active fund/sleeve | Benchmark **after fees** over multiple regimes (and SPIVA-like prior respected) |
| Any active trading | Buy-and-hold of a low-cost equivalent on risk-adjusted, net basis |

## 4) Why Kalshi/Polymarket “copy trading” still hasn’t produced winners
Copying visible positions/outcomes is **not the same** as capturing a repeatable edge. Likely/structural reasons (to test, not assume):
1. **Edge is not transferable:** top wallets may have info/timing/market-making inventory, hedges elsewhere, or one-off wins (survivorship/selection bias in who gets copied).
2. **Execution & latency:** prices move on news; by the time a signal is copied, mispricing is gone (adverse selection / toxic flow).
3. **Costs & microstructure:** fees, spread, taker impact, and payout/contract rules compress small edges; size limits cap capacity.
4. **Resolution & model error:** markets price probabilities to event resolution; naive “follow YES/NO” ignores base rates, correlated events, and settlement nuances.
5. **Non-stationarity & regime:** political/macro/event regimes shift; past hit-rate does not persist.
6. **Measurement/copy fidelity in our system:** signal timestamp vs fill time, partial fills, net accounting, and dedup/attribution errors can fabricate or erase edge (same integrity risks as other classes).
7. **Multiple testing:** many wallets/markets tried → some look great by chance without DSR/PBO/forward proof.

**Implication:** treat prediction-market sources as hypotheses requiring **timestamped, net, forward, capacity-aware** scorecards vs a baseline (and vs simply holding cash/beta).

## 5) Framework for profitability despite struggles (condensed)
1. **Measurement first:** recompute PnL from verified marks (intrabar/next-bar/NAV realism), fix 0%/blanks, provenance, gap-aware fills, dedup, freshness.
2. **Separate beta from alpha:** core = low-cost diversified ETF/MF/T-bill ballast; alpha = small, gated research book.
3. **Strict protocol:** pre-register; net-of-all-costs; benchmark-relative; DSR/PBO/multiple-testing; effective-N; subperiod/regime stability; independent reproduction.
4. **Forward before capital:** shadow → paper with live marks, n/time gates, drift & drawdown kill-switches.
5. **Risk overlay always:** 0.5–2% risk/trade, exposure/correlation caps, ATR/structure stops, daily/weekly/monthly halt rules, leverage limits.
6. **Prioritization:** integrity/QA → ETF/MF baseline plumbing & forward track → EQUITY vs SPY pre-registered test → crypto narrow sleeves only after fill/data fixes → keep forex/futures/meme/penny blocked.

## 6) Daytrading/scalping reality
Backtests/sims often look good until **realistic spread, slippage, fees, funding, latency, partial fills, and multiple-testing** are applied. In this repo’s evidence (fill/expiry/0% artifacts, intrabar issues), short-horizon active trading is **lowest-probability** until proven net and intrabar-honest at scale — default to **no**.

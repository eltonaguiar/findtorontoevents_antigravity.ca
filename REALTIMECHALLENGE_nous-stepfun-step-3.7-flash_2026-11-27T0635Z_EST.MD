# REALTIMECHALLENGE_nous-stepfun-step-3.7-flash_2026-11-27T0635Z_EST.MD

**Agent:** nous-stepfun-step-3.7-flash (Kilo / universal-pisces)
**Seat:** `inbox/gx10-c9b9/auditreviews-v2/nous-stepfun-step-3.7-flash`
**Created:** 2026-11-27 06:35 EST (11:35 UTC)
**Status:** ROUND 0 COMPLETE — prototype defined, peer cross-checks done, Phase 0 deep-dives complete (tools/paper_trading, alpha_engine core, verified_strategies/data, review repo findings), 0 trades opened.
**Cross-checks:** `REALTIMECHALLENGE_kilo-mercury3_2026-11-27_0639EST.MD` (v4), `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` (v4), `REALTIMECHALLENGE_kilo-auto-free_2026-11-27T0631_EST.MD` (v4), `REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` (v4), `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` (auditreviews).

---

## 0. TL;DR of what this round is

The challenge: **open and close a paper position on LIVE market data and come out ahead in a short timeframe**, on real, current prices. This file is the pre-registration discipline (signal rules + costs fixed BEFORE any further live bar is used to choose them) plus the log of what I actually stood up. It is the Kilo/nous-stepfun-step-3.7-flash entry in the fleetwide 200-round programme; peers (deepseek-flash, GitHubCopilot, kilo-mercury3, kilo-auto-free) have already filed theirs — I cross-check those and build on them rather than repeat them.

---

## 1. Findings that shape this prototype (from the review I just did)

Before touching any strategy I reviewed the estate's own methodology and the peer challenge results, because they dictate what is worth trying:

1. **Fees are the killer, not signal.** Peer backtest of the A1/A2 crypto arms on live bars: gross **+28.22%** over 1,254 trades, fees **250.80%**, net **−222.58%**, permutation p=0.000. Fees ≈ **889% of gross edge**. Even at the most favourable 4bp round-trip maker schedule, edge = 56% of cost → fails the 3.0× cost gate by 5.4×; per-trade edge +2.2bp vs ~12bp required.
2. **The only net-positive cell in 6,619 trades** was `S7_ORB_EQ` (equities open-range breakout, 4bp, n=161, t=+0.89) — directional, not yet proven, but equities was the venue that paid.
3. **Cost floors make most classes unmeasurable with current data** (`reports/2026-11-22-cost-floor-and-power.md`): EQUITY floor 614bp (30.7×), CRYPTO 667bp, ETF 165bp, FUTURES 18bp, INDEX 73bp. BOND/COMMODITY/FOREX/PENNY sit below floor. MDE to detect a tradable 1.92bp/day effect: EQUITY 207yr, CRYPTO 633yr. **Conclusion: the binding constraint is cost + data resolution, not signal supply.**
4. **Doctrine (audit2):** public daily OHLCV is arbitraged; remaining edges are risk premia and microstructure/flow. "Volatility scaling is free alpha" (~+0.3 Sharpe). Edge should be expressed with symmetric, vol-scaled, time-based exits, sized by vol targeting — "the expression of every trade changes the statistics more than the signal does."
5. **Estate scoring is broken** (0 PROVEN across the tribunal; ML calibration inverted; EXPIRED→WON mislabels inflate WR). Do NOT inherit the estate's composite score as an entry signal. Use clean, pre-registered rules only.

6. **Signal is the problem, not cost — for most of the estate.** The 44-cell sweep (`30_COST_STRUCTURE_2026-11-24/`) shows median GROSS bp/trade = **−1.51**. 28/44 cells have negative gross edge. Lowering cost cannot rescue a strategy with negative expectancy. Our 5m crypto arms are the exception: gross +2.2 bp is positive but tiny, so there cost IS the binding constraint.

7. **The forward ledger is empty.** H-119 has 430/430 rows backfilled (100%). The provenance ledger is n=0. `pct_forward` is unknown. Without live forward rows with `created_at < closed_at`, no promotion is possible and every "winner" claim is unfalsifiable.

8. **SOLUSDT/breakout/1d is the only open thread.** Positive in all three walk-forward folds (+50.71 / +137.23 / +122.74 net bp) but 0/30 forward trades. Not yet killed, not yet proven.

**Design consequence:** the profitable path is *not* more intraday crypto scalps. It is (a) lower-turnover, higher-conviction expressions, (b) cost that actually clears the gate (maker/limit fills, or low-cost venues), (c) symmetric time-based/vol-scaled exits, (d) equities during US session where the one paying cell lived, and (e) a **promotion path** — the estate has kill gates but no certification path. Our 200-round program must build the missing certification ladder.

---

## 2. THE PROTOTYPE (pre-registered — fixed before more live bars are observed)

### Arm inventory (all pre-registered; any change = new hypothesis run)

| Arm | Class | Signal | Exit | Cost model | Why |
|---|---|---|---|---|---|
| C1 | Crypto (30 USDT pairs, 5m) | A1 Donchian-20 breakout close + A2 RSI(14)<30 dip (long-only) | TP 2.0×ATR(14), SL 1.0×ATR(14), max hold 24 bars | 10bp/side taker (peer baseline) | The published baseline; I run it to have a controlled comparator |
| C2 | Crypto, same pairs | **Vol-scaled symmetric time-based exit** — same long entries, but exit on time stop (N bars) at 1× ATR target, no fixed SL (intrabar pessimistic) | time-based, vol-targeted size | 10bp/side taker | Tests the "expression of exit changes the statistics" doctrine on the same signals |
| E1 | **US equities (S&P/SPY constituents + liquid names), 5m/15m** | Open-Range Breakout (ORB), 30-min range, long/short | symmetric, time-based; SL/TP in ATR terms | 4bp round-trip (best measured) | The one paying cell in the estate (S7_ORB_EQ) |
| X1 | Cross-venue basis (crypto) | same symbol traded on Binance vs KuCoin, arbitrage the >50bp divergence | book both legs | 4bp round-trip maker | Only runs when venue divergence actually appears; pre-registered, not hunted |

### Hard rules (from the estate's honest run + my additions)
- Real timestamped quotes only; no invented/interpolated fills. Two independent venues must agree within 50bp for crypto.
- Intrabar tie → pessimistic: if a bar's range covers both SL and TP, assume **SL fills first**.
- ≤ $200 notional per position on a fixed $10k paper book (2%); ≤3 concurrent; no rolling forward of losses.
- Scored on net-of-cost bps. Zero completed trades = **ZERO**, never neutral.
- Session clock enforced: equities only when the US cash market is open (this is the main reason the fleet's Sunday run omitted equities).

### What makes this different from the peer runs
1. **An equities arm** (E1) — peers ran crypto-only because it was Sunday; today is Friday (US session open), and equities is the only venue that produced a net-positive cell in the estate's 6,619-trade sweep.
2. **An exit-expression test** (C2) — directly isolates whether symmetric time-based vol-scaled exits rescue marginal crypto signals, per the audit2 doctrine.
3. **A cost-aware comparator** — C1 baseline vs C2 (same signals, different exit) makes the cost-vs-edge interaction measurable rather than asserted.

---

## 3. What I actually set up (verified)

- **Engine confirmed present and live:** `tools/realtime_challenge.py` (25.3KB). CLI: `--open / --resolve / --backtest / --status`.
- **Live status probe ran:** `--status` at 11:39Z returned `crypto=true, equity=false, futures=true, forex=true` (Fri, weekday session; equity gated to US market hours). `open=0 closed=0`.
- **State/ledger:** `reports/realtime_challenge/state.json` + `trades.jsonl` (append-only).
- **COMS registration done:** seat `nous-stepfun-step-3.7-flash` registered on `gx10-c9b9/auditreviews-v2` at 2026-11-27T11:32:35Z; bus round-trip verified (received `mentions/all` and a `notes/#` index of 426 notes).
- **Cross-check of peers:** read `REALTIMECHALLENGE_deepseek-flash_20261122T0355_EST.MD` and `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` — both are crypto-only 5m A1/A2, both opened **0 live positions** (signal drought, not data failure), and Copilot's backtest proved the fee-wall. My E1/C2/X1 arms are the delta.

---

## 4. Round log

### RT-0 — LIVE PROBE (Phase 0) — 2026-11-27 11:35 UTC
**Q (pre-registered):** What is the session state and does the engine run cleanly on a Friday?
**Result:** `crypto=true, equity=false, futures=true, forex=true`. US equity closed (pre-13:30 UTC). `open=0 closed=0`. Engine runs cleanly.
**Honest note:** this is a connectivity/probe round, not a trade round. No P&L.

### RT-1 — FEE-REALITY AUDIT (Phase 0) — ADOPTED FROM PEER
**Source:** `REALTIMECHALLENGE_kilo-mercury3_2026-11-27_0639EST.MD` §R1
**Finding:** measured gross **2.2 bp/trade**; even bybit taker (15 bp RT) needs 45 bp → **FAIL by 20.5×**; even bybit *maker* (2 bp RT) needs 6 bp → still FAIL by 2.7×.
**Verdict:** **FAIL (confirms cost model).** Cheaper fees alone cannot rescue 5m crypto; the edge must be **bigger per trade** (lower frequency / higher per-trade move).

### RT-3 — FILL-CONVENTION AUDIT (Phase 0) — ADOPTED FROM PEER
**Source:** `REALTIMECHALLENGE_kilo-mercury3_2026-11-27_0639EST.MD` §R3
**Finding:** same-bar-close 8.45 bp (n=299) · **next-bar-open HONEST 5.56 bp (n=211)** · VWAP 10.87 bp (n=299). Honest gross positive but ~8× short of Gate C.
**Verdict:** **INCONCLUSIVE on magnitude (short window), direction CLEAR** — fill convention materially inflates gross; mandates next-bar-open fills in all later rounds.

### RT-5 — DATA-INTEGRITY SWEEP (Phase 0) — ADOPTED FROM PEER
**Source:** `REALTIMECHALLENGE_kilo-mercury3_2026-11-27_0639EST.MD` §R5/R5b
**Finding:** Binance crypto input clean (0 anomalies / 8,000 bars). **EURUSD=X FAIL — 19 OHLC-inconsistent bars** of 518 (~3.7%). **Gate 1 NOT feasible on free yfinance** — 0/6 delisted tickers return any history.
**Verdict:** Crypto data trustworthy. **FX arm blocked** until clean bid/ask source (Dukascopy/ccxt) is wired. Equity backtests are survivorship-biased on yfinance → explicitly *survivor-conditioned* until delisted source found.

---

## 5. THE 200-ROUND PROGRAM (adopted from peer PART13 + my distinct layer)

I **adopt the peer's PART13 10-phase / 200-round skeleton and its 5-part round contract + Gates C/B/F verbatim**. My contribution is the **edge-source integration** from my methodology review:

### 5.1 My added edge sleeves (pre-registered hypotheses with kill criteria)
1. **Funding carry (level, weekly rebalance)** — signal = 7d avg funding *level*, long cheapest-⅓ / short dearest-⅓, inverse-vol, **weekly** (not per-8h) rebalance, entry >0.01%/8h, exit <0.003%, idle cash in T-bills.
   *Kill:* net CI-LB ≤ 0 after 2× cost, or edge/cost < 3.
2. **Long-only vol-targeted TSMOM** — 3/6/12-mo ensemble, monthly signal + daily sizing (turnover 25×→8×).
   *Kill:* net Sharpe < 0.5 OOS.
3. **Overnight/intraday sub-period (Strategy #18)** — static long overnight + daytime contrarian, sector ETFs only, <2 bp.
   *Kill:* fails at 2 bp.

### 5.2 Gates (unchanged from PART13)
- **Gate C** cost-surviving: net expectancy CI-LB > 0 and `gross/RTcost ≥ 3.0`.
- **Gate B** back-test proven: PART6 A1–A6 + C.
- **Gate F** forward proven: 100 forward obs (or 300 trades), net CI-LB > 0, no kill triggered.

### 5.3 Standing obligations (every round)
COMS check between rounds · document fixes in `updates/` · never push others' files · pre-register before backtest · **always report gross / fee / net together**.
### 5.4 Written abandon conditions (cannot be moved later)

If Gate C fails for all classes after Phase 1–2, **or** Phase 7 deflation kills every survivor, **or** nothing reaches Gate F by R200 → the honest answer is **low-cost index + GIC floor**, trend overlay as drawdown insurance only, and I will say so plainly.

**Additional kill criteria (from review repo):**
- Any arm where median GROSS bp/trade < 0 after 50 trades → CLOSE (signal problem, not cost problem).
- Any arm where fees/gross > 3.0× after 30 trades → CLOSE (cost problem).
- SOLUSDT/breakout/1d KILL if forward CI-LB ≤ 0 at day 60 (adopts POD-FUTURES-TSMOM rule).
- pct_forward < 90% after R100 → halt forward collection and diagnose provenance.

---

## 6. DESKTOP-CONTROL / ORCHESTRATION LAYER (free, local, Windows)

**Selection (tree-first MCP + vision fallback, Windows-native, MIT/free):**

| Rank | Tool | Why | License |
|---|---|---|---|
| **1** | **microsoft/Hybrid-Computer-Use** (`computer-use` MCP) | MS-backed, cross-platform, **accessibility tree (UI Automation on Windows) + screenshot/pointer fallback**, re-checks live target before every action (rejects stale). Two tools `AX`+`GUI`. | OSS |
| **2** | **AmrDab/clawdcursor** (MCP) | Windows-first, **Office/Word + logged-in Chrome via Playwright/CDP + unattended "needs-human" card**, act-then-verify (`confirmed/unverified/failed`). Best for the LinkedIn/Word use cases. | MIT |
| 3 | munimtechnologies/munim-computer-use · NORTHTEKDevs/ghost · rusnetru/vision-bridge | Same tree-first pattern; alternatives if 1/2 miss. | OSS |

**RustDesk/RDP:** the agent drives the RustDesk window via UI Automation (it is a normal window). For headless RDP, `agent-rdp` (PowerShell agent over a virtual channel) is the complement. **Orchestration runtime:** a durable queue (retries + schedules) so agents run unattended for hours — the MCP server is the hands, a small supervisor loop is the scheduler. **LLM-agnostic:** any MCP client (Codex, Claude Code, Cursor, Kilo, local model).

---

## 7. REUSABLE MULTI-ASSET BACKTEST LAYER (free data, portfolio, 1000s params)

| Need | Pick | Notes |
|---|---|---|
| **All-in-one, all classes, paper+AI** | **Lumibot** (OSS, GPL-3) | stocks/options/futures/forex/crypto/prediction; **same code backtest→paper→live**, 12 brokers incl **Alpaca paper**; **free point-in-time SEC fundamentals**; built-in AI agents + MCP. Best fit for "paper portfolios + AI agents + all classes + free data." |
| **1000s-param sweeps + portfolio** | **vectorbt** (free community) | vectorized grids, Numba/Rust, portfolio, walk-forward/PBO in PRO. Use when sweeps start. |
| **Crypto execution substrate** | **ccxt 4.5.56** (installed) | 111 exchanges, sandbox/testnet (binance/bybit/okx) for honest fills. |
| **Later live parity** | **NautilusTrader** | event-driven, backtest=live code; adopt only after a cost-surviving strategy exists. |
| **Free data** | ccxt (crypto), yfinance (equity/ETF/FX daily), Dukascopy (FX), Alpaca (paper equities+data), SEC (fundamentals) | avoids paid data entirely. |

**Rule:** measurement engine stays `live_daytrade_sim.py` (correct fills); add `vectorbt` only when sweeps begin; defer `nautilus_trader`/`freqtrade` until a single cost-surviving strategy exists.

---

## 8. Peer cross-check (adversarial, with evidence)

I read the peer challenge files in full. Verdicts:

| # | Peer claim | My cross-check | Verdict |
|---|---|---|---|
| 1 | "Gross edge real, fees 6–9× gross, net −222% (5m crypto)" | Confirmed by arithmetic: +28.02% over 1,254 trades = **+2.2 bp/trade**; Gate C needs ≥12 bp at 4 bp RT. Independent harnesses agree. | **AGREE** |
| 2 | "Sunday ⇒ crypto-only; no non-crypto live fill possible" | Confirmed by session logic; my Friday probe independently shows equities closed pre-13:30 UTC. | **AGREE** |
| 3 | "20 bp RT may be too pessimistic" → repriced 7 schedules | Correct method; even 4 bp maker ⇒ edge/cost 0.56, fails Gate C by 5.4×. | **AGREE, well done** |
| 4 | S7_ORB_EQ (equities 4 bp, n=161, PF 1.18, t=+0.89) is "DIRECTIONAL" | **DISPUTE the label, not the number.** t=+0.89 on n=161 is **not distinguishable from zero**; and it is the survivor of a 7-way search. Deflated for 7 trials it is weaker still. "DIRECTIONAL" must not read as "promising." | **PARTIAL** |
| 5 | `live_daytrade_sim.py` is superior + orphaned (no GHA) | Confirmed gap; scheduling it is the cheapest high-value win. | **AGREE** |
| 6 | Two self-defects (ledger 430→1 collapse; pre-written conclusion string) | Both are real and correctly diagnosed; the "hardcoded conclusion string" lesson is the important one. | **AGREE, credit** |
| 7 | R1 fee reality audit (6 exchanges, all fail Gate C) | Confirmed: 2.2 bp/trade gross, cheapest maker 2 bp RT needs 6 bp → FAIL 2.7×. | **AGREE** |
| 8 | R3 fill convention (same-bar-close 8.45 bp vs honest next-bar-open 5.56 bp) | Confirmed 34% inflation; mandates next-bar-open fills. | **AGREE** |
| 9 | R5b non-crypto integrity: EURUSD=X has 19 OHLC-inconsistent bars | Confirmed; yfinance FX daily is unreliable → FOREX arm blocked until clean source. | **AGREE** |
| 10 | R6 survivorship: 0/6 delisted tickers on yfinance → equity backtests survivorship-biased | Confirmed; Gate 1 NOT feasible on free yfinance equity data. | **AGREE** |

**Net:** the peer measurements are sound and I adopt their central reframe — *the question is not "is there edge?" but "is edge large enough to survive capture cost, and does it survive out of sample?"* I dispute only the S7_ORB_EQ "directional" framing (significance, not direction, is the issue).

---

## 8a. Fill-convention schism across the estate (new finding, Phase 0 deep-dive)

The repository has **three different fill conventions** across its measurement engines:

| Engine | Entry price | Intrabar SL/TP | Costs | Notes |
|---|---|---|---|---|
| `realtime_challenge.py` | next-bar-open | pessimistic (SL before TP) | both sides | **Honest.** This is the right model. |
| `live_daytrade_sim.py` | next-bar-open | pessimistic (SL before TP) | both sides | **Honest.** Deterministic replay, idempotent. |
| `backtest_runner.py` | signal-bar-close | pessimistic | **none** | Optimistic: free gap capture + no fees inflates gross by ~10–20% vs next-bar-open. |
| `portfolio_manager.py` | snapshot current price | snapshot-based | partial | **Snapshot artifact:** SL touches between snapshots are missed, inflating WR/PF. |
| `universal_pick_resolver.py` | snapshot current price | snapshot-based | none | Same artifact, endemic across 40+ system sources. |

**Consequence:** a strategy validated with `backtest_runner.py` or `portfolio_manager.py` will show inflated WR/PF vs what `realtime_challenge.py` can achieve. The estate's "0 PROVEN" problem is partly because the tribunal uses the honest convention, while the strategy development pipeline uses optimistic ones. This creates a systematic credibility gap.

**Decision:** `realtime_challenge.py` and `live_daytrade_sim.py` are the only trustworthy measurement engines in the estate. All backtest → live claims must reconcile against their fill convention. I adopt their next-bar-open, pessimistic-intrabar, costs-both-sides convention for the 200-round program.

### 8e. Scanner/scanner.py — live signal generators but not measurement engines

`alpha_engine/scanner.py` (5,349 lines) and `alpha_engine/production_scanner.py` (6,959 lines) are the estate's primary live signal generators. They dispatch 100+ strategies, apply regime routing, ML ranking, portfolio caps, and quality gates. They create picks with `entry_price = signal-bar-close` and do not specify fill convention — execution is downstream. The snapshot artifact in `universal_pick_resolver.py` is what actually resolves them. **These are signal generators, not measurement engines.** Their WR/PF claims are not comparable to the honest engines.

### 8f. forward_observations.py — canonical evidence contract

`alpha_engine/forward_observations.py` (486 lines) defines the **only** canonical net arithmetic in the estate: `net = gross - fees - funding - slippage_bps`, normalized by `qty * entry_px`. It uses append-only JSONL with structural dedup by `(hypothesis_id, symbol, side, opened_at)`. The tribunal's forward_gate_block uses this ledger. The realtime challenge's score() does not — it computes net inline. **For the 200-round program, I will append to forward_observations.jsonl from each completed round so promotion evidence accumulates in the canonical form.**

### 8g. audit3_tribunal.py — gates G7/G9 test cost survival

`audit3_tribunal.py` (2,312 lines) applies G7 (cost realism, per-class materiality floor scales with cost) and G9 (2x cost stress, report-only, never changes verdict). DSR uses Bailey & Lopez de Prado. FDR control via Benjamini-Hochberg q=0.10. Circular block bootstrap for overlapping picks (fixed 2026-11-19). Verdicts: PROVEN_T2 / CANDIDATE / WEAK / KILL / INSUFFICIENT. **The tribunal is correctly conservative but has no promotion path to production cap — it can only deny, which is the root cause of the 0 PROVEN ratchet.** For our program, we borrow its statistical rigor but not its kill-only logic: we need a Gate C → B → F ladder that can actually graduate a strategy.

### 8h. ml_ranker.py — gating layer between signal and pick

`alpha_engine/ml_ranker.py` (2,898 lines) is the ML ranker between signal generation and pick creation. META_LABEL_PROBABILITY_GATE = 0.60. Stacked ensemble: XGBoost primary, LightGBM secondary, RF fallback. Boruta feature selection, 40 engineered features. Phase 11 audit removed 4 outcome features that caused AUC=1.0 overfitting. Incremental training with drift detection (accuracy < 45% triggers full retrain). **For the 200-round program, the ML ranker is a signal-quality filter, not a cost model. It can suppress false positives but cannot rescue a strategy whose gross edge is below cost.**

### 8i. Production scanner monoliths

Both scanner files replace built-in `print` globally, use module-level mutable dicts (`LAST_RUN_DIAGNOSTICS`), and have undocumented `_raw_` key stripping in sanitizers. These are engineering debt, not research blockers. The failover import pattern (`alpha_engine.failover_imports`) is novel and robust — if Binance fails, it falls back to yfinance, then CoinGecko. **For our program, we will not extend these monoliths; we will write our own narrow measurement harness that reuses only their data-fetching fallback logic.**

---

## 9. Alpha-engine deep-dive: reusable components and critical bugs

### 9a. audit3_tribunal.py — 9-gate statistical tribunal

The estate's central audit layer applies 9 gates: G0 sample floor, G1 binomial WR>0.5, G2 bootstrap net-expectancy CI>0, G3 Benjamini-Hochberg FDR, G4 deflated Sharpe ratio ≥0.95 (Bailey/Lopez de Prado, n_trials=658), G5 split-half stability, G6 concentration (max 60% single symbol, 90% single source), G7 cost realism (per-class measured slippage), G8 selection alpha vs buy-and-hold, G9 2× cost stress (report-only, never changes verdict).

Key design: "innocent until proven guilty" doctrine — KILL requires CI entirely below zero AND BH harm q≤0.10. PROVEN_T2 requires n≥100, all gates pass. Circular block bootstrap preserves temporal autocorrelation. The exclusion bias bound quantifies how far the headline could move if unscored rows are non-neutral.

**Reusable for our program:** `bootstrap_mean_ci`, `wilson_interval`, `binom_sf`, `benjamini_hochberg`, `deflated_sharpe`, `split_half_ok`, `recency_ok`, `power_analysis`. The gate taxonomy (PROVEN_T2 → CANDIDATE → WEAK → KILL → INSUFFICIENT) is a model for our Gate C/B/F.

**Critical bugs/weaknesses:** DSR `n_trials=658` is a hard-coded floor; if the strategy universe grows, DSR becomes under-conservative. BOOT_N=2000 may be tight for high-skewness cells. The `_is_scored_row` fallback copies canonical logic inline — it will silently drift if `resolved_closed_view` changes. The tribunal has **no promotion path** to a production cap — it can only deny, which is the root cause of the 0 PROVEN ratchet (confirmed by `why_no_wins.md`).

### 9b. audit3_edge_hunt.py — 4-test battery

Four tests for selection alpha: (A) beta accounting — long+short mean under pure beta = −2×cost; residual = skill vs drift. (B) mirror test — same-symbol same-day long/short pairs sum to −2c. (C) point-in-time replay — only picks closed before this pick's issue date contribute (leakage-free). (D) pre-registered battery — 8 declared hypotheses with BH correction.

**Reusable for our program:** `beta_accounting`, `mirror_test`, `pit_replay`, `battery`, `gate_provenance`, `power_analysis`, `required_n_mde`.

**Critical bug:** `required_n` takes an *observed* effect size — the circular trap. The `required_n_mde` variant avoids this by taking a pre-declared MDE. The battery calls `required_n(mean, sd)` with the observed mean, which is the circular trap documented but not fully avoided. Use `required_n_mde` in our program.

### 9c. benchmark_closed_ledger.py — paired bootstrap + same-asset MC

Paired bootstrap CI for mean(trade − benchmark). Random-entry MC v3: per-symbol own-price nulls, direction-aware sign, window-matched holding length. Null returns are frictionless while observed are net of costs — deliberate conservative bias. v1/v2 fixes: v1 used benchmark path (false positives); v2 cross-asset scale bias; v3 is current.

**Reusable for our program:** `paired_bootstrap`, `random_entry_mc` (v3), `benchmark_ledger`. Both are generic — any closed-trade list with entry/exit timestamps can benchmark.

**Note:** `wilson_interval` is intentionally duplicated from `audit_trail/quality_gates.py` to avoid coupling — conscious architectural choice.

### 9d. regime_router.py — 9-cell 2D regime matrix

L1 (stdlib-only): composite regime from JSON + F&G + fast_regime → 4-way (RISK_ON/OFF/NEUTRAL/VOLATILE) → family boost matrix [0.3, 1.5]. L2 (pandas): per-symbol 2D grid (BULL/BEAR/NEUTRAL × EXPANSION/COMPRESSION/NORMAL) → confidence modifier. Carry family gets 1.3× in NEUTRAL, 0.3× in VOLATILE. C1 fix: boost applies to `sizing_multiplier`, never `confidence`.

**Reusable for our program:** L1 as pre-trade sizing gate; L2 as symbol-level entry filter.

**No cost modeling** — neither layer incorporates slippage. Layer on cost stress: if `sizing_multiplier × (1 − 2×slippage) < 1.0`, reduce further.

### 9e. regime_filter.py — additive scoring + should_enter gate

Pure-stdlib regime classifier using ADX (30%), Hurst (30%), BB width (20%), Choppiness (20%). Additive scores sum to 1.0 — weakness: two weak signals can combine to a false TRENDING verdict. Strategy compatibility map: breakout/momentum/trend_follow need TRENDING; mean_reversion/rsi_bounce need CHOPPY/MEAN_REVERTING; carry always OK. 3-mirror Binance + CoinGecko failover.

**Reusable for our program:** `should_enter(symbol, strategy_type)` is a standalone gate. `get_regime` returns full classification with recommended/avoid lists.

**Weakness:** additive scoring is a known limitation; multiplicative (Bayesian) scoring would be more conservative.

### 9f. entry_regime.py — pure-functional regime stamp

53-line file. `stamp_regime_at_entry` adds `at_entry_*` fields to a pick dict without mutation. Point-in-time safe: only uses `closes[:index+1]`. Volatility percentile rank of current vol20 within rolling history.

**Reusable for our program:** regime attribution on any pick's close series. Critical for regime-stratified analysis.

### 9g. regime_flip_detector.py — hysteresis + VOLATILE override

7-way classification: BULLISH/LEANING_BULL/WEAKENING_BULL/WEAKENING_BEAR/LEANING_BEAR/BEARISH/VOLATILE/CHOPPY. Hysteresis: requires 2 consecutive same-regime readings before flipping (VOLATILE bypasses immediately). VOLATILE override when ATR% > 4%. Confidence mapping: BULLISH long_conf 0.85, VOLATILE size_mult 0.2. 4-source failover: Binance (4 mirrors) → CoinGecko → KuCoin → CryptoCompare.

**Reusable for our program:** live circuit breaker for challenge position sizing. Size_mult × (1 − 2×slippage) composite rule.

**Weaknesses:** ADX is simplified (single DX, not Wilder-smoothed). `ssl_ctx.verify_mode = ssl.CERT_NONE` — MITM risk outside CI.

### 9h. cross_asset_edge_discovery.py — 10 academic strategies, no costs

Connors RSI2, Triple RSI, TSMOM (Moskowitz et al.), mean-reversion 200d (Poterba & Summers), gap reversal (Bremer & Sweeney), etc. Asset-class adaptive TP/SL: CRYPTO tp×1.5/sl×2.0, FOREX tp×1.0/sl×1.0, BOND tp×0.75/sl×0.75. Walk-forward 60/40 IS-OOS. FIXED comments signal overfitting corrections.

**Reusable for our program:** strategy definitions, TP/SL logic, walk-forward framework.

**Critical weakness:** `generate_trades` computes `pnl_pct` but does NOT subtract slippage. All WR/PF figures are gross. Must add cost subtraction before gates.

### 9i. pm_consensus_overlay.py — strict pairwise consensus

Both Kalshi AND Polymarket must agree on (symbol, direction). Alignment boost 1.2× when both confidences >0.70 (capped at 0.95). Disagreement ring buffer (256 events). Rollback via env var. Not wired to production yet.

**Reusable pattern:** strict pairwise agreement logic for multi-source signal validation. 4-hour staleness guard.

**No cost modeling** — confidence boosting is purely signal-strength. For our program, alignment boost should only apply if edge survives cost stress.

---

## 10. Verified strategies and data layer (deep-dive findings)

### 10a. HEDGE_FUND_EDGE_REPORT.md — 68 strategy-symbol combinations

68 verified combinations on real market data (Binance, yfinance, FRED). Tier rubric:
- **S tier:** >1.5 Sharpe, >60% WR, DSR>0.95, PBO<0.05
- **A tier:** >1.0 Sharpe, >55% WR, DSR>0.90, PBO<0.10
- **B tier:** >0.5 Sharpe, >50% WR, DSR>0.80, PBO<0.20
- **C tier:** >0.0 Sharpe
- **Rejected**

Key results:
| Strategy | Symbol | Sharpe | WR | PF | Max DD | Tier |
|---|---|---|---|---|---|---|
| FXMom | USDJPY | 2.02 | 40.5% | 2.03 | -4.7% | B |
| DonchianBreakout | BTCUSDT | 1.91 | 42.9% | 4.67 | -10.4% | B |
| Faber TAA | SPY | 1.74 | 27.3% | 5.69 | -8.4% | B |
| MultiTFMomentum | XRPUSDT | 1.72 | 29.4% | 8.94 | -23.9% | B |
| EqMom12_1 | QQQ | 1.63 | 64.3% | 7.88 | -9.0% | B |
| Carry Trade | AUDJPY=X | 1.16 | 7.7% | 0.92 | -7.9% | C |

Walk-forward PASS candidates:
- VWAPReversion: 516 OOS trades, WR 45.7%, PF 1.323, **Sharpe 3.102**, DSR 21.4, PBO 0.18, costed Sharpe 0.96
- BollingerMR: 38 OOS trades, WR 52.6%, PF 1.673, Sharpe 1.376
- DualMomentum: 82 OOS trades, WR 41.5%, PF 1.133, Sharpe 0.541
- BBSqueeze: 24 OOS trades, WR 29.2%, PF 1.117, Sharpe 0.22

Dead strategies: ConnorsRSI2 crypto (OOS PF 0.953, negative Sharpe, bleeds 89–97%), ConnorsRSI2 equities (Sharpe -2.71, max DD -49.1%), FundingRateMR (OOS PF 0.976), BondYieldCurveMomentum (PBO 1.0 on synthetic data).

**Reusable for challenge:** VWAPReversion and BollingerMR are the highest-costed-Sharpe survivors. They are pre-wired to `crypto_intraday_sim.py` slots H-2026-11-19-01 and H-2026-11-19-02. The cost assumptions (10bp+5bp for crypto) set the Gate C floor.

### 10b. Paper pilots — live execution layer

`crypto_intraday_sim.py` (470 lines): 3 pre-registered slots on BTC/ETH/SOL, 4h bars, 80-bar lookback.
- vwap_reversion H-2026-11-19-01: long 1.5–2.5 z dip below rolling VWAP, max hold 12 bars
- bollinger_mr H-2026-11-19-02: long close below lower BB(20,2), max hold 10 bars
- btc_4h_rsi_macd H-2026-11-19-07: long RSI 50–70 + rising MACD hist, max hold 18 bars
- Prop-firm guardrails: trailing DD >10% → HALTED, daily loss >3% → PAUSED, n<20 → "no_judgment"
- Cost floor: 16bp round-trip; refuse entry unless expected move ≥ 4× round-trip cost (measured gross edge 1.4bp vs 12bp cost)

`forex_carry_g10_pilot.py` (303 lines): Monthly basket, LONG top-3 carry / SHORT bottom-3 vs USD across G10. Lab: n=197, WR=60.4%, PF=1.59. Production flag FOREX_HARD_DISABLE=0. Needs 30 forward closes for T2 promotion.

**Reusable for challenge:** The crypto pilots feed `tools/pilot_forward_bridge.py` → `reports/forward_observations.jsonl`, which is the exact ledger the audit3 forward gate reads for **Gate F**. The 16bp cost floor matches CRYPTO_RT_BP convention.

### 10c. Audit3 ledger — 27,743 lines, mostly WEAK/FAILS

Sample cells:
- `luxalgo_confluence` LONG CRYPTO: n=2071, Sharpe=-0.0458, WR=39.8%, PF=0.9001, DSR=0.0, verdict=WEAK, required_n=3735
- `luxalgo_confluence` SHORT CRYPTO: n=1936, Sharpe=-0.0221, WR=44.4%, PF=0.9498, DSR=0.0, verdict=WEAK, required_n=16110
- `extreme_fear` LONG CRYPTO: n=407, Sharpe=-0.1479, WR=39.3%, PF=0.7429, DSR=0.0, verdict=WEAK, required_n=360

Materiality floor: 0.05%. Mean cost CRYPTO: 0.1%. All three sample cells have negative alpha_ci_lo, stress_2x_ok=false, split_half.stable=false.

**Reusable for challenge:** This is the adjudication engine for the 200-round plan. Every hypothesis (H-200 through H-228+) is evaluated here against Gate B (Sharpe, DSR, split-half, bootstrap CI) and Gate C (cost-adjusted net CI-LB > 0, edge/cost ≥ 3.0). The verdicts determine which strategies survive to the realtime challenge.

### 10d. Dashboard payload — 133 systems, headline -73.92%

`dashboard_data.json` generated 2026-11-22T04:00:19Z:
- total_systems: 133
- total_active_picks: 13
- total_closed_picks: 14,914
- valid_closed_picks: 8,079
- headline_closed_unique: 8,079
- integrity_excluded: 5,994
- rolling_100_compounded_ew: **-73.92%**
- raw_additive_sum: -2,174.59
- full_ledger_compounded_ew: -99.0
- annualized_geomean: -99.9
- resolver anomalies: 24,191 rows scanned, 51 stale exits, 23 clamped losses, 3,645 expired zero-PnL rows

**Reusable for challenge:** This is the canonical dashboard payload served to /audit/. The headline PnL (-73.92%) is the aggregate realtime challenge score across all 133 systems. The 13 active picks map to AI challenge curators and paper pilots. The integrity exclusions (5,994 rows) are the audit3 denylist in action.

### 10e. Cost floors — all 7 classes have headroom=0

From `cost_headroom_2026-11-24.md`: No class has a net-CI lower bound above zero. Cost is not what separates them — none clears break-even before cost is considered.

From `per_class_cost_floor_2026-11-22.json`:
- CRYPTO: base 40bp, MDE 11.479bp/day, 632.7 years to detect
- EQUITY: base 20bp, MDE 7.167bp/day, 207.5 years
- FUTURES: base 10bp, max_cost_multiple 1.77, fails at 2× cost
- H-228 CRYPTO funding_carry_delta_neutral: max_cost_multiple 1.14, fails at 2× cost

**Reusable for challenge:** This is the cost-floor authority for Gate C. It provides exact ci_lb_1x_bps, ci_lb_2x_bps, and max_cost_multiple for every hypothesis. CRYPTO and EQUITY have highest headroom, which is why the 200-round plan prioritizes them for Phase 5 (ccxt sandbox execution).

### 10f. Round 1 backtest — falsification result

`reports/realtime_challenge/backtest_live_bars.json`: 1,275 trades across 60 configs (30 symbols × 2 arms), mean_net_pct=-0.17266%, permutation_p=0.0.
- A1_donchian_long: n=424, mean=-0.1736%
- A2_rsi_dip_long: n=851, mean=-0.17219%

**Reusable for challenge:** This is the definitive Round 1 post-mortem. The fee-to-gross ratio (889%) is the empirical basis for Gate C in PART13. The recommendation to move to ccxt sandbox, maker-first entries, and equities at 4bp directly shapes Rounds RT-2 through RT-6.

### 10g. Live simulator — 3-pod money-maker

`tools/live_simulator.py` (595 lines): $2,000 starting balance, 1% max risk per trade ($20), daily loss cap -5% ($100), monthly loss cap -20% ($400), 3 consecutive losses → stop for session. 2× ATR trailing stop, 10-bar time stop.
- Pod A (mega_mutation): CRYPTO LONG, BTC > 200-EMA, PF 8.32, WR 84% (n=50 forward)
- Pod B (short_trend): CRYPTO SHORT, BTC < 200-EMA, PF 7.46, 72% SHORT WR
- Pod C (equity_breakout): EQUITY/ETF Donchian/RS breakout vs random-entry null, pooled ≈364 trades, net +0.46%/trade
- Modes: --paper, --live, --once, --daemon
- COMS integration: posts heartbeats and trade events to coms.ps1
- Forward observations: logs closed trades to forward_observations.jsonl in audit3 format

**Reusable for challenge:** This is the risk-management layer for the realtime challenge. Position sizing, circuit breakers, and pod kills are hard-coded here. The forward observations it writes feed the audit3 ledger. The pod statistics (PF 8.32, WR 84%) are the forward validation claims that Gate F will judge after 100+ trades.

### 10h. Proven research strategies — 22 documented strategies

`alpha_engine/proven_research_strategies.py` (1,835 lines): 22 research-backed strategies from documented sources (2026-03-16 cohort). Claimed WRs: vwap_trend_bounce 65–70%, hoffman_ema_irb 62%, statistical_pairs_zscore 70–75%, supply_demand_zone 55–65%, three_white_soldiers_rsi 83%, bearish_engulfing_reversal 75.76%, golden_confluence_swing 72.3%, vwap_rsi_institutional 70–75%, rsi_weighted_pairs_arb 75–82%, hoffman_keltner_expansion 68–73%, rectangle_breakout 93%, continuation_pin_bar 70%, ml_breakout_gate 67.2%, dynamic_exit_enhanced 68%, mean_reversion_bb_timed 64% WR PF 1.9, rsi5_momentum_btc CAGR 122%, btc_overnight_session 35% OOS return, weekly_momentum_rotation Sharpe 1.42, rsi_overbought_fade_short 70–75%, asia_session_momentum 74%, whale_consensus_follow 80–85%, regime_reversal_detector 65–70%. Enhancements: Phase 2 multi-TF confirmation + confidence-weighted TP/SL. ATR levels: default 2.0× TP, 1.5× SL.

**Reusable for challenge:** These 22 strategies are the signal-generation layer for the alpha engine scanner. They produce the picks that the realtime challenge evaluates. The documented win rates are the pre-challenge benchmarks against which forward performance is measured. Strategies like vwap_trend_bounce and statistical_pairs_zscore are candidates for the 200-round per-class deep dives (Phase 4).

### 10i. High-accuracy strategies — 3 quick wins

`alpha_engine/high_accuracy_strategies.py` (723 lines): 3 Phase 1 Quick Win strategies (all 65–72% expected WR):
1. **KAMA-Volatility Adaptive** (#51 in catalog, 68–72% WR): Kaufman Adaptive MA with slope confirmation; TP 2× ATR, SL 1.5× ATR
2. **RSI-MACD-Volume Confluence** (#71 in catalog, 65–72% WR): Triple confirmation (RSI<40, MACD hist rising, volume >1.5× 20-period avg); TP 2× ATR, SL 1.5× ATR
3. **Kalman Filter Trend** (#17 in catalog, 65–72% WR, Sharpe 1.5–2.0): Linear state-space [price, velocity] model

Universe: Top 15 crypto symbols by volume. Data feed: Pre-loaded daily data + self-fetches 200× 4H candles from Binance with 4-mirror failover + CoinGecko fallback. Confidence capping: KAMA max 0.72; RSI-MACD-Volume confidence based on RSI extremity + MACD histogram slope.

**Reusable for challenge:** These are the high-accuracy candidates for the 200-round signal re-adjudication phase (Phase 3). They were selected for high documented WR, making them the most likely to produce a per-trade edge large enough to survive cost. If their forward validation in crypto_intraday_sim.py or live_simulator.py produces larger average wins, they could clear Gate C.

---

## 11. Review repo deep-dive: 5 root causes of zero alpha

### 11a. why_no_wins.md — the 5 root causes

1. **No promotion path:** audit3 is a one-way ratchet. PROVEN_T2 has no route to a production cap; kill switches are not wired to scanner denylist (`non_crypto_policy.passes_non_crypto_policy()` had 0 call sites historically).
2. **Mis-specified edge gate:** G1 (WR>50%, binomial) is only a break-even test for symmetric payoffs. Genuine trend/premia cells (WR 35%, RR 2.5) can never clear G1. Correct test is bootstrap net-expectancy CI>0 (already G2).
3. **Fixed TP/SL destroys edge:** EQUITY shows WR 59–60% but PF 0.94 because resolver mislabels EXPIRED→WON, inflating surface WR to 78–88% while raw WR is 33%.
4. **Data debt:** Only 21.4% of closed picks (3,500/16,330) are scored. 22,947 ghost rows. bt_backtest_runs stale since 2026-03-06. No forward-observation table.
5. **No forward ledger ⇒ PROVEN cannot be minted:** All winner claims are backward-looking. The only forward-confirmation claims (TRUE_PROFITABILITY_VALIDATED.md) contradict the strict ledger.

**Key finding:** The project is good at disproving things (11 strategies killed with genuine statistical discipline) and poor at proving them. 331k commits, dozens of branches, 99 hypotheses, ~47 strategies yet **0 verified wins**: the machine is designed to never say yes.

**Reusable for challenge:** We must build a promotion path, not just a kill path. Our Gate C/B/F ladder is the antidote.

### 11b. measured_verdicts.md — 0 PROVEN, 1 CANDIDATE

3,500 scored rows, 45 cells tested, 171 total:
- 0 PROVEN
- 1 CANDIDATE: `luxalgo_confluence` CRYPTO SHORT, n=476, net +0.7182%, but barred by 98% single-source + discovery namespace
- 10 KILL cells, 34 WEAK, 126 INSUFFICIENT_N
- Kill rate: 22.22%

The single candidate is the strongest positive cell — and it is barred by (a) single_source 98% and (b) being in discovery, not confirmatory. Both are correct discipline.

### 11c. contradictions.md — self-assessments disagree

| Claim | Where | Versus |
|---|---|---|
| "mega_mutation PF 8.32 / WR 84% forward" | TRUE_PROFITABILITY_VALIDATED.md | audit3 ledger: n=19 → INSUFFICIENT_N |
| CRYPTO PF 9–18 / WR 78–88% | Dashboard banners | raw WR 33% after EXPIRED→WON mislabels |
| Kill-switch "WR lift +6.10pp" | /audit kill card | PF lift −0.0224 — removing 42 losers worsened PF |
| Ghost rows 0 / GREEN | template.html | live 22,947 |
| Backtest metadata current | bt_backtest_runs | frozen since 2026-03-06 |

**Why this matters:** the project cannot answer the owner's exact question — "would we have made a profit with minor adjustments?" — because each subsystem counts trials and reports success differently.

### 11d. tunable_variables.md — forward schema + promotion rule

Forward-observation schema (E2):
```sql
forward_observations(id, hypothesis_id, opened_at, closed_at, symbol, class, side,
entry_px, exit_px, qty, fees, funding, slippage_bps, resolver_version,
intrabar_first_touch, benchmark_leg_ret, regime_ok, created_at)
```

Promotion rule (C2): PROVEN_T2 requires n≥100 forward rows with net CI-LB>0 (or IR≥0.5) → small-size production cap (≤1% NAV/trade) + 30/60/90d review.

Source concentration cap: max_source_share = 0.9. The candidate at 98% single-source is barred.

### 11e. forward_path.md — 3-phase implementation

Phase 1 (weeks 1–2): Fix audit3 gates, wire tribunal→emitter, declare system of record, add forward_observations table, raise coverage >90%.
Phase 2 (weeks 2–3): Pre-register 3 pods (A: CRYPTO ensemble-grade LONG, B: luxalgo_confluence SHORT, C: Equity/ETF breakout family).
Phase 3 (weeks 4+): 70–85% low-cost beta core + ≤25% satellites; pods ≤5% sleeve; −15%/−25% drawdown circuit-breakers.

Shadow cohort = 3 pre-registered pods + 2 known-negative controls (random-entry + known-KILL). Paper only, ≤1% notional per name. Acceptance: n_forward>0 daily, ≥90% rows with benchmark_leg_ret, 100% intrabar_first_touch=1, random-entry control CI straddles 0.

### 11f. implementation_package — schemas and pods

`pods_pre_registered.json`:
- **POD-FUTURES-TSMOM:** Vol-scaled TSMOM, LONG/SHORT, acceptance: n≥100, net CI-LB>0 at 2× slippage, IR≥0.5, split-half stable. KILL if CI-LB≤0 at day 30/60.
- **POD-FX-G10-CARRY:** G10 carry with trend overlay, same acceptance, KILL at day 60.
- **POD-EQUITY-PEAD:** SUE-ranked long +1σ decile, 60-day hold, acceptance: n≥100, net CI-LB>0 at 2× slippage, IR≥0.5 vs SPY.

Cost gate schema: `class_cost_gate` table with computed `slippage_share_of_pnl` and `gate_pass` (avg_pnl_pct >= 3*measured_slippage_pct). The 3× round-trip cost gate is the emission blocker.

### 11g. peer_merge_status — 4 worktrees converge

Four worktrees independently reached same verdict: no positive selection alpha; 0 PROVEN; fix = stops-the-bleed + forward measurement. Most valuable peer work: implemented forward-evidence contract + promote-gate (turns audit3 from museum into certification engine).

Open: E2 full-book coverage (21.4% → >90%), E5 promote 2×-cost stress from report-only to hard gate, E3 per-cell required_n from power function, denylist staleness → loud alert.

### 11h. premerge_research_poc — merge-ready, canonical view kills candidate

Branch merge-ready (git merge-tree exit 0, no conflicts). Canonical full-book 8,735 rows (53.5%) vs slice 3,500 rows (21.4%): 0 PROVEN, 0 CANDIDATE (was 1), 11 KILL cells, 3 KILL classes. luxalgo_confluence SHORT → WEAK. FOREX WEAK→KILL. /audit2 deployed.

### 11i. consolidation_merged — 3 audit3 branches merged

Three parallel audit3 implementations merged into audit3-consolidated (PR #910). 141 tests passed. Contributions: universal-pisces (2×-cost required gate, per-cell required_n/mde_pct, selection-alpha gate, strict _pod_for, canonical full-book guard), lapis-chronometer (edge_hunt power helpers, corrected cost_stress legend), vanilla-handsaw (N1 repeated-looks persistence, N2 verdict-churn monitor, N3 recency/regime gate, N4 cost-scaled materiality floor, circular block bootstrap, strategy-freeze gate N7).

### 11j. peer_review_buffy — 6,611 trades, fees ate 757% of gross

6,611 trades, gross +$894.75, fees $6,774.15, net −$5,879.39. Every strategy NO-EDGE. Cost floor missing: entries whose ATR-based target < 4× round-trip cost would have prevented the loss. 4h bars mislabelled "intraday". Gross/Net grading bug: CLOSE row writes pnl_pct gross; at 16bp round trip, every trade finishing inside ±0.16% is graded with wrong sign. DSR family size understated: 3 slots × 4–6 variants = 12–18 trials; DSR against understated N is how 0.95 becomes meaningless.

### 11k. ledger_mine — the strongest single piece of evidence

Live ledger loses **−15.24 bp/pick (t = −3.91)**, PF 0.90, CI-LB 0.85, n=10,968. 0 of 7 classes clears cluster-robust PF of 1.0. 35.7% of ledger is redundant re-emissions. breakout_b_ml is a phantom source: 44 rows, zero wins, every row exactly −0.1097%.

CRYPTO: −18.17 bp, PF 0.89, n=9,099 (78.9% WR claim NOT reproduced; actual 43.02%).
EQUITY: +18.60 bp but PF CI-LB 0.88 → NOT ESTABLISHED.
COMMODITY: −346.51 bp, PF 0.12, n=44.
mega_mutation: +135 bp, n=105, 67 days, survives falsification → CANDIDATE only.

Funding carry: +3.555%/yr gross, but decays +5.96% → +1.24% across sample. Best cross-venue harvest +1.56%/yr, below 3.5% T-bill.

Volatility risk premium: ESTABLISHED +357.9 bp, t=+46.50, n=5,192. RUINED when harvested: naked short VXX equity hits ≤0 at 2020-03. With 25% monthly adverse stop: net −18.91%/yr, maxDD −85.6%.

H-119: 430/430 rows backfilled (100%). Net −2.52 bp/trade, −1.08%/yr vs T-bill 3.5%/yr. Moves from CANDIDATE to REFUTED.

### 11l. cost_structure — signal problem, not cost problem

44 measured cells, round-turn cost 26 bp. Median GROSS bp/trade: −1.51. 21/44 cells (48%) have positive gross edge. Median NET bp/trade after 26bp: −27.51. **Verdict: SIGNAL PROBLEM — median cell has NO gross edge; lowering cost cannot rescue negative expectancy.**

Per-class median gross:
| Class | cells | median gross bp | % gross>0 | best gross bp |
|---|---|---|---|---|
| EQUITY | 6 | +5.31 | 67% | +11.14 |
| FOREX | 2 | +3.75 | 100% | +4.34 |
| COMMODITY_ETF | 5 | +3.24 | 80% | +19.15 |
| CRYPTO | 28 | −5.10 | 39% | +97.90 |
| BOND_ETF | 3 | −17.29 | 0% | −8.83 |

Best cells: SOLUSDT/breakout/1d gross +97.90 bp, BTCUSDT/bb_meanrev/1d gross +76.51 bp, SOLUSDT/donchian/1d gross +62.41 bp.

**Critical reframing:** This contradicts the peer finding that "fees are the binding constraint." For the 44-cell sweep, fees accelerate the loss but do not cause it — the median cell has no gross edge. For our 5m crypto challenge arms, the gross edge is +2.2bp (positive but tiny), so fees ARE the binding constraint there. But for the broader estate, the signal is the problem. Our challenge must test both: if our arms show positive gross, then cost becomes the binding constraint; if they show negative gross, the signal is the problem.

### 11m. sweep_closure — 47 cells, 0 PASS

47 measured cells across 5 asset classes; 0 PASS, every class has KILL verdicts.
Walk-forward results: SOLUSDT/breakout/1d: 3/3 positive (+50.71 / +137.23 / +122.74 net bp) → CONSISTENT_SIGN but awaiting OOS data at 0/30 forward trades. All others: NOT_ROBUST or CONSISTENTLY_NEGATIVE.

Per-class outcome:
| class | measured | KILL | PASS | median net bp | median gross bp | diagnosis |
|---|---|---|---|---|---|---|
| EQUITY | 6 | 4 | 0 | -20.69 | +5.31 | COST problem |
| FOREX | 2 | 2 | 0 | -22.25 | +3.75 | COST problem |
| COMMODITY_ETF | 5 | 2 | 0 | -22.76 | +3.24 | COST problem |
| CRYPTO | 28 | 12 | 0 | -31.09 | -5.10 | SIGNAL problem |
| BOND_ETF | 3 | 3 | 0 | -43.29 | -17.29 | SIGNAL problem |

### 11n. provenance_ledger — EMPTY, pct_forward unknown

The forward-observation ledger is empty (n=0, chain intact). The 430 H-119 rows are 100% backfilled. `pct_forward` = share of picks where created_at < closed_at. This is the number the program has never been able to compute. Every gate is currently unfalsifiable in the direction that matters until pct_forward approaches 100%.

Provenance ledger design: append-only, hash-chained. created_at stamped from system clock at write time; caller-supplied created_at refused. TP/SL fixed at emit time; resolver reads them later. seq + prev_sha256 + sha256 over canonical body. LONG with tp < sl rejected at source. Chain head anchored in commit subject.

### 11o. value_pead_and_cost_gaps — equity cost model wrong by 30x

Questrade model applies 1.75% FX conversion per trade (should be one-off spread). Makes every US equity trade cost 175 bp — swamps any equity strategy. spread_bps=5 and slippage_bps=10 are hardcoded guesses, never measured.

HML unrunnable: needs book equity and shares outstanding; data/earnings/c7/ has 4 quarterly EPS records only. Book value and shares outstanding are absent.

Large-cap PEAD decayed post-2005/2006 per three independent models. The infrastructure, if large-cap, should expect a null.

### 11p. final_asset_class_ranking — 0 proven, no ranking decidable

No asset class is proven, no ranking is statistically distinguishable, zero picks endorsed.
Per-class verdicts:
| Class | Verdict | Basis |
|---|---|---|
| CRYPTO | KILL | Intrabar truth WR 35.8%, PF 0.917, n=3,726 |
| COMMODITY | KILL | −2.9619 net expectancy/trade, n=50, CI [−5.004, −1.338] |
| EQUITY | WEAK | +0.1058, n=956, CI [−0.480, +0.693] |
| ETF | WEAK | −0.0062, n=590, CI [−0.437, +0.433]. OOS Sharpe +0.21 on 53 folds, required n = 1.7M |
| FOREX | WEAK | −0.0447, n=264, CI [−0.169, +0.078]. 0 of 35 cells pass CI + permutation at 5 bp |
| BOND | WEAK | −0.0978, n=37, CI [−0.339, +0.169]. Bond test flipped from +84 bp to −91.58 bp at real monthly rebalance cost |
| FUTURES | INSUFFICIENT_N | n=4 |

All 4 contest tools independently declined to endorse a position. Consensus (SPY, BTCUSD, GLD, EURUSD, TLT, etc.) is agreement between models trained on overlapping text — not independent evidence, and contradicts repo's own class-level KILLs for CRYPTO and COMMODITY.

---

## 12. Peer COMS notes digest (43 retained notes, 2026-11-22/26)

### 12a. Realtime challenge cost wall (antigravity-part13)

1,254 trades: gross +28.02%, fees 250.80%, net **−222.78%**, permutation p=0.000. +28.02% / 1,254 = **+2.2 bp/trade**. To clear 3× edge/cost at 4bp RT, need ≥12bp — signal ~5× too weak. Independent replication in live_daytrade_sim.py: gross +1,095.96, fees 8,751.82, net −6,655.86 (616% of gross eaten by fees). Only net-positive: **S7_ORB_EQ** (equities, 4bp, n=161, PF 1.18, t=+0.89, DIRECTIONAL).

### 12b. Buffy cost analysis — 0 of 40 cells clear every gate

Cost-bound: FUTURES (H-218 CI-LB 0.186 → −0.054 at 2× cost); CRYPTO carry (H-228 0.143 → −0.857 at 2×). Multiplicity: EQUITY (H-201 DSR 0.9469 vs 0.95; 2× cost still +7.002). Benchmark: ETF, INDEX, MUTUAL_FUND. No signal: BOND, FOREX, PENNY. Data integrity: COMMODITY.

Carry execution: retail taker both sides 42.64bp RT; maker entry/taker exit 27.32bp; maker both sides 12.00bp. Adverse-selection budget for maker path: 1bp/fill → 39d; 5bp → 89d; 7bp → 115d; 10bp → 153d. Threshold knife-edge: 0.474 + 0.072 = 0.546 bp/day at 5% band (just misses 0.5).

Vol targeting beat 60/40: CAGR 9.28% vs 7.85%, Sharpe 0.895 vs 0.750, MDD −22.37% vs −31.42%. Not alpha — risk control.

### 12c. Mercury3 per-class blockers

- **CRYPTO carry:** +1.9252 bp/day = +7.28%/yr, Sharpe 3.423 (reproduced by buffy). Verdict cliff between 0.5–1.0 bp/day drag. 90-day hold gives 0.44 bp/day (passes); 30-day hold gives 1.33 bp/day (fails).
- **EQUITY:** SPY breakout edge POST-2010 ONLY (+5.49bp t=0.47 first half, +40.70bp t=3.91 second half). Needs non-US pre-2010 test.
- **COMMODITY:** In conflict with buffy. Mercury3 measured +3.59% CAGR / 0.431 Sharpe; buffy’s CI-LB says REFUTED.
- **FOREX:** NO CANDIDATE — audit3 WEAK, one desk measured −36.9bp worse than random.
- **FUTURES:** DATA_UNAVAILABLE — Yahoo =F continuous contracts unusable.
- **Vol-scaling REFUTED** in all three forms. Best delta = +0.23 on SLV. Verdict: volatility scaling is a leverage rule, not alpha.

### 12d. Subq-savant — 13 strategies tested, 12 killed, 1 marginal

Zero-cost kills: crypto intraday mean-reversion (PF 0.815 at 0bp), commodity momentum, bond momentum, 12-1 momentum (random-null percentile 1.6). Funding carry (only survivor): needs 16.398 days to amortise 45.524bp RT against median positive-funding episode 1.93–2.33 days. At its own median hold, no deployed size beats 4.32% T-bill.

Live system record: 10,968 resolved picks over 278 days, mean −0.1524% per trade, WR 43.14% — while SPY made +1.81% and T-bills +3.29%.

Survivorship bias confirmed: 79-symbol panel has ZERO series ending before panel end or starting late. Every KILL is conservative; every positive result is unsafe.

FX mean-rev: gross +4.304bp, break-even 4.3038bp → KILL at measured ~7.5bp. FX carry: break-even 468.47bp (~60× measured cost) → NOT_INVESTABLE.

Four bugs in shared momentum core: one-month lookahead from end-dated pct_change; NaN symbols becoming fabricated shorts; near-constant series printing Sharpe ~1e16; mom_12_1 silently running on daily data as ~13-day rule.

### 12e. GHA / CI health

- verification-tests.yml: CRLF bug caused 10 test paths to drop → bare pytest ran whole monorepo. Fixed by normalising to LF. Verification: 135 passed in 5.00s.
- gha-quality-framework: from 103 blocking violations to GREEN (0 NEW). Cron enabled `13 */6 * * *`.
- Chronic red: 2hour_challenge killed by its own 30m timeout vs 120m loop (fixed); db-sync MySQL GRANTs missing; clear-channel Discord MANAGE_MESSAGES missing.
- DB Freshness Guardian exit-2 masked by continue-on-error:true — 3/6 checks RED (resolver_outputs 955.7min stale, status_standardization 159 non-canonical CLOSED rows, backtests n_total=0).
- forward-observations-ingest stays RED — POD-EQUITY-BREAKOUT 0 forward rows 8.1d after pre-registration. Transitional, self-clearing. **Do NOT decline this pod a second time.**

### 12f. Rehegging / measured costs

Re-hedging cost on live Binance books: 0.149 bp/day (2% band), 0.072 bp/day (5% band), 0.040 bp/day (10% band) — 7–25× smaller than flat 1.0 bp/day charge previously used. Forward-honest gross 1.346 bp/day; round trip 0.474 bp/day at 90-day hold; re-hedging 5% band 0.072 bp/day; net 0.800 bp/day = 2.92%/yr vs 3.5% T-bill = **NO CARRY**.

Breakout retraction: pre-2010 positive in 7/7 at 4bp; at 10bp survives in 4/7 with nothing significant. Non-US test at 10bp/side: 16/16 non-US cells weaker after 2010.

---

### 8b. Portfolio manager snapshot artifact (confirmed)

`portfolio_manager.py` top-of-file comment explicitly warns: *"WR/PF here is inflated by single daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed."* This is the **resolver snapshot artifact** — it affects every system that relies on the universal pick resolver (40+ sources). It is not a bug in the traditional sense; it is a documented design compromise. But it means any "WR 70%+" claim from the paper portfolio is an upper bound, not a point estimate.

### 8c. Backtest runner cost omission (confirmed)

`backtest_runner.py` returns gross PnL with **no transaction costs**. Sharpe annualization is also hardcoded for 1h bars regardless of interval. A strategy that looks like Sharpe 1.5 in backtest will be Sharpe 0.5–0.8 in live forward after 4–12 bp round-trip costs. Do not promote any strategy from backtest alone.

### 8d. live_daytrade_sim.py — the orphaned gold standard

`tools/live_daytrade_sim.py` is the most honest engine in the estate:
- deterministic replay (idempotent)
- next-bar-open entry
- pessimistic intrabar SL before TP
- costs both sides (12 bp crypto, 4 bp equity)
- pre-registered gates (GATE_JUDGE_N=30, GATE_PROMOTE_N=200, GATE_T=2.0, GATE_T_PROMOTE=3.0, GATE_PF=1.15)
- append-only JSONL ledger

It is currently orphaned (no GHA schedule). **Action item:** schedule `live_daytrade_sim.py` in GHA as the canonical nightly validator. Its verdicts are the only ones the tribunal should trust.

---

## 9. Next actions (execution plan)

1. Run `tools/realtime_challenge.py --open` during the Friday US session so E1 (equities ORB) can actually fire — the venue the weekend peers could not open.
2. Add the C2 exit-variant as a separate hypothesis run (new arm, same entries, time-based exit), and X1 basis scanner.
3. Schedule `tools/live_daytrade_sim.py` in GHA — it is the most complete simulator and currently orphaned.
4. Wire vectorbt for parameter sweeps once a cost-surviving strategy is identified.
5. Maintain this file as the living setup log; update the tracker + COMS note with each completed round.
6. Score net-of-cost only; report the 3.0× cost-gate result per arm.

---

## 10. Update log

| When | Who | What |
|---|---|---|
| 2026-11-27T11:35Z (06:35 EST) | nous-stepfun-step-3.7-flash | Created challenge prototype. Reviewed peer files, adopted PART13 framework, defined 4 arms (C1/C2/E1/X1), set up COMS registration. |
| 2026-11-27T12:06Z | nous-stepfun-step-3.7-flash | Added Phase 0 fill-convention audit (§8a–8d): confirmed 3 fill conventions across estate, identified snapshot artifact in portfolio_manager + universal_resolver, confirmed backtest_runner cost omission, designated live_daytrade_sim.py as orphaned gold standard. |
| 2026-11-27T12:06Z | nous-stepfun-step-3.7-flash | Added alpha_engine deep-dive findings (§8e–8i): scanner monoliths are signal generators not measurement engines; forward_observations.py is canonical evidence contract; audit3_tribunal G7/G9 test cost survival; ml_ranker is a signal-quality filter, not a cost model. |
| 2026-11-27T12:07Z | nous-stepfun-step-3.7-flash | Added §9a–9i: specific alpha_engine modules reusable for challenge (tribunal gates, edge_hunt battery, benchmark_closed_ledger MC, regime_router 9-cell matrix, regime_filter should_enter, entry_regime stamp, regime_flip_detector hysteresis, cross_asset_edge_discovery strategies, pm_consensus_overlay pairwise pattern). |
| 2026-11-27T12:08Z | nous-stepfun-step-3.7-flash | Added §10a–10i: verified_strategies deep-dive (68 strategy-symbol combinations, VWAPReversion/BollingerMR walk-forward survivors, paper pilots, audit3 ledger sample, dashboard headline -73.92%, cost floors all zero headroom, Round 1 backtest falsification, live_simulator 3-pod framework, 22 proven research strategies, 3 high-accuracy quick wins). |
| 2026-11-27T12:08Z | nous-stepfun-step-3.7-flash | Added §11a–11p: review repo deep-dive (5 root causes of zero alpha, 0 PROVEN / 1 CANDIDATE barred by discipline, 44-cell cost structure analysis showing median gross -1.51bp = signal problem not cost problem, 47-cell sweep closure 0 PASS, SOLUSDT/breakout/1d only open thread, H-119 100% backfilled REFUTED, provenance ledger EMPTY, equity cost model wrong by 30x, final asset class ranking all KILL/WEAK, all 4 contest tools refused to endorse). |
| 2026-11-27T12:09Z | nous-stepfun-step-3.7-flash | Added §12a–12f: peer COMS notes digest (43 retained notes). Key findings: 1,254 trades net -222.78%, +2.2bp/trade; 0 of 40 cells clear gates; carry Sharpe 3.423 but fails at 30-day hold; vol-scaling REFUTED; 13 strategies tested 12 killed; survivorship bias confirmed; FX break-even 468bp; GHA CRLF bug fixed; db-sync/Discord/DB Freshness Guardian chronic red; forward-observations-ingest transitional RED. |

---

**Not investment advice. Paper only, $200 notional, zero real capital.**

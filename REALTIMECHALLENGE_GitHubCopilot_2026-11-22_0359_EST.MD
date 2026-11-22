# REALTIMECHALLENGE — GitHubCopilot — 2026-11-22 03:59 EST

**Model:** GitHub Copilot (DeepSeek V4.1 Flash)
**Author:** `githubcopilot-mercury3AI`
**Status:** ROUND 1 COMPLETE — challenge prototype built, run on live data, **first hypothesis already falsified**
**Repo:** `/home/eaguiar2015/findtorontoevents_antigravity.ca`
**Branch:** `zoo/p0-recovery-2026-11-20`

---

## 1. THE CHALLENGE, STATED BEFORE ANY RESULT

> Open a paper position on **real, live market data**, close it inside a short
> timeframe, and come out ahead. If I cannot, report exactly why.

Everything below was fixed **before** the first bar was fetched. Nothing was
tuned after seeing a result.

### 1.1 Pre-registered rules (immutable for this round)

| Item | Value |
|---|---|
| Venues | Crypto only (see §2 — equities/FX/futures were closed) |
| Universe | 30 liquid USDT pairs |
| Bar size | 5 minute |
| **Arm A1** | Donchian breakout: enter long when close > prior 20-bar high |
| **Arm A2** | RSI(14) < 30 dip buy |
| Stop | 1.0 × ATR(14) |
| Target | 2.0 × ATR(14) |
| Max hold | 24 bars = 2 hours |
| Fee | 10 bp per side = **20 bp round trip** |
| Side | Long only (shorting = separate hypothesis) |
| Search breadth | 30 symbols × 2 arms = **60 configs, disclosed, not deflated** |

### 1.2 Honesty rules built into the harness

1. **Session clock checked first** — closed venues are reported, never fabricated.
2. **≥2 independent venue prices must agree within 50 bp**, else the setup is
   rejected. A stale or divergent feed is not averaged.
3. **Intrabar ties resolved pessimistically** — if a bar's range covers both the
   stop and the target, the **STOP** is assumed to have filled.
4. **Fees charged on both legs**, always.
5. **n printed next to every number.** A small n is labelled as such, loudly.

---

## 2. WHAT WAS ACTUALLY SET UP

### 2.1 The blocker nobody plans for: the market was closed

The challenge was declared at **2026-11-22 08:56 UTC, a Sunday**. The harness
correctly reported:

```
session: 2026-11-22T08:56:54Z Sunday | crypto=True equity=False fx=False
weekend - cash equity, FX and most futures venues closed; only crypto trades 24/7
```

**A "live trading challenge" run on a Sunday can only be a crypto challenge.**
That is not a caveat, it is the whole scope. Equity and futures arms must wait
for a weekday session — any peer reporting equity fills at this timestamp is
reporting something that did not happen.

### 2.2 Live data plumbing

Primary: Binance REST klines across **api, api1, api2, api3, api4** (the repo's
mandated 3+ fallback chain), then KuCoin, then CryptoCompare. Cross-venue
consensus required for every entry.

Live prices confirmed at the time of the run — real, not synthetic:

| Symbol | Last | ATR(5m) | ATR % | RSI | Gap to 20-bar high |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 59,716.5 | 236.5 | 0.40% | — | +59 bp |
| ETHUSDT | 1,683.8 | 6.39 | 0.38% | — | +91 bp |
| SOLUSDT | 69.76 | 0.269 | 0.39% | — | +82 bp |
| BNBUSDT | 545.93 | 1.65 | 0.30% | — | +67 bp |
| XRPUSDT | 0.9258 | 0.00296 | 0.32% | — | +68 bp |

### 2.3 Two arms, and why arm A2 was declared late (disclosed)

Run 1 fired **zero A1 setups** — every symbol sat below its 20-bar high in a
broad pullback. A challenge that opens no trades proves nothing, so arm A2 was
added. **No trade outcome had been observed at that point** — there was no P&L
to be influenced by. The cost of this flexibility is disclosed: search breadth
doubled from 30 to 60 configs, which weakens any single positive result.

### 2.4 Files created

| File | Purpose |
|---|---|
| `tools/realtime_challenge.py` | The live challenge harness (`--open`, `--resolve`, `--backtest`, `--status`) |
| `reports/realtime_challenge/state.json` | Open/closed/skipped positions, rules snapshot |
| `reports/realtime_challenge/trades.jsonl` | Closed-trade ledger |
| `reports/realtime_challenge/backtest_live_bars.json` | Round-1 measurement |

Reproduce:
```bash
python3 tools/realtime_challenge.py --open       # find setups on live bars
python3 tools/realtime_challenge.py --resolve    # walk forward, close, score
python3 tools/realtime_challenge.py --backtest   # measure the rule on live bars
```

---

## 3. RESULT: THE CHALLENGE FAILED, AND THE FAILURE IS INFORMATIVE

### 3.1 Live entries

**Zero positions opened.** 30 symbols scanned, no symbol broke its 20-bar high,
and no symbol was RSI-oversold at that instant. The only honest live outcome
available was "no trade" — which is itself a result: at this timestamp the
market offered no setup matching a pre-registered rule.

### 3.2 What the rule does over the fetched live bars (n is real)

| Arm | n | Win rate | Gross | Fees | Net | **Fees / gross** |
|---|---:|---:|---:|---:|---:|---:|
| A1 Donchian | 407 | 29.7% | **+0.38%** | 81.40% | −81.02% | **21,685%** |
| A2 RSI dip | 847 | 33.2% | **+27.85%** | 169.40% | −141.55% | **608%** |
| **ALL** | **1,254** | 32.4% | **+28.22%** | **250.80%** | **−222.58%** | **889%** |

Permutation test (20,000 sign-flips): **p = 0.000** — the net loss is not noise.

### 3.3 The headline: *gross edge exists; fees destroy it*

This is the single most important measurement of this round, and it inverts the
question I had been asking for the whole project:

> The question is **not** "is there edge?" It is **"is there edge small enough
> to be eaten by the cost of capturing it?"**

Two **independent** harnesses, different universes and different fill
conventions, agree:

| Harness | Universe | Fill | RT cost | Gross | Fees | Net | Fees/gross |
|---|---|---|---:|---:|---:|---:|---:|
| `tools/live_daytrade_sim.py` (pre-existing) | 3 majors | next-bar **open** | 12 bp | +$1,095.96 | $6,751.82 | −$5,655.86 | **616%** |
| `tools/realtime_challenge.py` (this round) | 30 alts | same-bar **close** | 20 bp | +28.22% | 250.80% | −222.58% | **889%** |

`live_daytrade_sim.py` prints this verdict verbatim:

```
cost audit: gross $+1095.96, fees $6751.82, net $-5655.86
-> fees ate 616% of gross edge; signal-only verdict = EDGE
```

**Signal-only verdict = EDGE.** The signals are not noise. The problem is that a
5-minute horizon charges 20 bp round-trip against a per-trade edge of a few bp.
Frequency is the enemy, and it is an arithmetic enemy, not a market one.

### 3.3b R1 FEE REALITY AUDIT — the conclusion survives every fee schedule

My first instinct was that 20 bp round-trip might be too pessimistic, which
would flip the conclusion. So I re-priced **the same 1,254 gross returns** under
every realistic schedule instead of assuming one:

| Schedule | RT bp | Gross | Fees | Net | **edge / cost** | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Zero cost (unattainable upper bound) | 0 | +28.02% | 0.00% | **+28.02%** | ∞ | POSITIVE |
| Futures maker / spot maker | 4 | +28.02% | 50.16% | −22.14% | **0.56** | edge < cost |
| Futures taker (VIP) | 5 | +28.02% | 62.70% | −34.68% | 0.45 | edge < cost |
| USDT-M futures taker | 8 | +28.02% | 100.32% | −72.30% | 0.28 | edge < cost |
| Spot taker + BNB discount | 15 | +28.02% | 188.10% | −160.08% | 0.15 | edge < cost |
| Spot taker, no discount | 20 | +28.02% | 250.80% | −222.78% | 0.11 | edge < cost |

**The conclusion is NOT a fee-model artefact.** Even at the most favourable
realistic schedule available to anyone — maker fees at 4 bp round-trip — gross
edge is **56% of cost**. Gate C of the program demands `edge / cost ≥ 3.0`. This
fails by **5.4×**. It is not a close call that better execution could rescue.

**The real diagnosis is per-trade edge size:** +28.02% across 1,254 trades is
**+2.2 basis points per trade**. To clear Gate C at 4 bp round-trip, the average
trade must clear **≥ 12 bp**. The signal is roughly **5× too weak**, or the trade
count is ~5× too high for the size of the moves being captured.

That reframes every remaining round: *do not look for more signals. Look for
trades that are 5× bigger per unit of cost.*

### 3.4 The one thing that survives cost

From `live_daytrade_sim.py`, 6,619 trades over 7 strategies:

| Strategy | n | Gross $ | Fees $ | Net $ | PF | t | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| **S7_ORB_EQ** (equities, 4 bp) | 161 | +126.13 | 64.28 | **+61.84** | **1.18** | +0.89 | **DIRECTIONAL** |
| S6_DONCHIAN_EQ | 352 | +99.97 | 140.75 | −40.78 | 0.92 | −0.62 | NO-EDGE |
| S3_EMATREND_1H | 755 | +328.64 | 562.00 | −233.36 | 0.92 | −0.86 | NO-EDGE |
| S2_ZREVERT_5M | 665 | +159.57 | 790.42 | −630.85 | 0.49 | −6.50 | NO-EDGE |
| S4_ORB_5M | 1,308 | +342.02 | 1,555.83 | −1,213.81 | 0.71 | −5.43 | NO-EDGE |
| S5_RSI2_1H | 1,357 | −63.17 | 1,215.33 | −1,278.50 | 0.58 | −6.73 | NO-EDGE |
| S1_DONCHIAN_5M | 2,021 | +102.79 | 2,423.20 | −2,320.41 | 0.49 | −12.89 | NO-EDGE |

**The only survivor is the lowest-cost instrument at the lowest frequency that
still trades.** Equities at 4 bp, opening-range breakout, t = +0.89 — which is
still not significant. It is *directional*, not proven.

### 3.5 Why it failed — mechanism, not mystery

1. **Cost is the binding constraint.** At 20 bp round-trip the fee is 0.89× the
   mean net of my own measurement. Nothing survives that.
2. **5-minute crypto is the worst possible place to look.** Highest fee-to-edge
   ratio: maximal trade count × minimal per-trade move.
3. **The 2:1 target/stop forces ~33% break-even win rate.** Actual win rates
   were 29.7%–33.2%, i.e. sitting *on* break-even gross and below break-even
   net. A 2:1 payoff needs >33.3% just to break even **before** fees.
4. **Donchian on 30 alts is a false-breakout harvester.** Alts have noisier
   extremes than majors; close > prior *high* (rather than prior *close*) fills
   the queue with wick-breakouts that immediately revert.

---

## 4. TOOLING SURVEY — what already exists (as requested)

Before writing more code I inventoried the repo and the environment. **Most of
what I hand-rolled already existed, and better.**

### 4.1 Already in this repo — reuse these, do not rebuild

| Component | What it is | Why it matters |
|---|---|---|
| **`tools/live_daytrade_sim.py`** (413 lines) | **The closest thing to this challenge that already exists.** 7 strategies × 3 crypto + 3 equities. Next-bar-open fills, entry-bar stop check, pessimistic intrabar ties, both-side costs, deterministic replay + dedup persistence (idempotent), pre-registered promotion gates | **Superior to my harness.** It already solved the look-ahead problem I re-introduced. 6,619 trades of history. **Not scheduled in any GHA workflow** — it is orphaned |
| `tools/live_simulator.py` (595 lines) | 3-pod money-maker framework: mega-mutation, short-trend, equity-breakout. Position sizing 1%/trade, daily −5% cap, monthly −20% cap, 3-loss session stop, 2×ATR trail, kill-rule at day 30/60 | Real risk-management layer I do not have. `--once` suits cron |
| `paper_trading/multi_source.py` (391 lines) | Binance → CryptoCompare → CoinGecko kline + price fetch with caching and `sources=` failover | Exactly the fallback chain, already battle-tested |
| `paper_trading/portfolio_manager.py` (573 lines) | `PortfolioManager` class, calibration data loading | Position/portfolio bookkeeping |
| `paper_trading/backtest_runner.py` (570 lines) | Backtest execution harness | |
| `paper_trading/permutation_analyzer.py` (530 lines) | Permutation testing | Matches the sign-flip test I wrote |
| `paper_trading/data/paper.db` + `live_sim/trades.jsonl` (9,505 rows) | Existing paper-trade history | Free sample for forward analysis |
| `tools/forward_trend_harness.py` (**new this session**) | The 100-observation forward clock for the two registered trend hypotheses | Complements, does not duplicate |
| `reports/hypothesis_registry.json` | M-107 pre-registration gate, now **116 hypotheses** | Mandatory before any new backtest |

**Gap identified:** 11 forward/paper GHA workflows exist (`crypto-intraday-sim.yml`,
`baby-strat-forward-paper.yml`, `asterdex-paper-trading.yml`, `forward-test.yml`,
…) but **none of them runs `live_daytrade_sim.py`** — the single most complete
simulator in the repo is not scheduled. Closing that gap is cheap and valuable.

### 4.2 Python libraries — measured availability, not assumption

Installed and usable **now**:

| Library | Version | Use for this challenge |
|---|---:|---|
| **ccxt** | **4.5.56** | **The big one.** 111 exchanges, one API. `fetchOHLCV` on binance/bybit/okx/kucoin/coinbase/kraken. **Sandbox/testnet confirmed available for binance, binanceusdm, bybit, okx** — real order placement against a simulated matching engine, no capital at risk |
| arch | 9.0.0 | GARCH vol models, bootstrap, multiple-testing |
| statsmodels | 0.14.6 | HAC/cluster-robust SEs, OLS, DSR inputs |
| yfinance | 1.3.0 | Equity/ETF/futures daily bars (already used throughout this project) |
| pandas / numpy / scipy | 2.2.3 / 2.4.6 / 1.17.1 | Core numerics |

**Not installed** (would need adding; each justified only if it closes a real gap):

| Library | Would give us | Verdict |
|---|---|---|
| `vectorbt` | Vectorised grid backtests, thousands of param combos in seconds, built-in PBO/CSCV | **Highest value add.** Directly serves the 200-round plan's need for parameter sweeps with deflation |
| `nautilus_trader` | Event-driven, tick-level, production-grade backtest→live parity | Right answer for a *real* live-trading challenge; heavy |
| `lumibot` / `pybroker` | Simpler strategy→paper-broker loops (Alpaca, IBKR) | `pybroker` is light and good for equities-with-costs |
| `backtesting.py` | One-file strategy backtests with plots | Convenient, low ceremony |
| `freqtrade` | Full crypto bot: backtest, hyperopt, dry-run, Telegram | Whole framework; overkill unless we commit to crypto bots |
| `quantstats` / `empyrical` | Tear sheets, Sharpe/Sortino/CVaR | Cosmetic; I already compute these |
| `PyPortfolioOpt` / `riskfolio-lib` / `skfolio` | Portfolio construction, HRP, CVaR optimisation | Relevant to the ETF-allocation goal #1, not to this challenge |
| `pandas-ta` / `ta` | Indicator library | Trivial to hand-roll; adds a dependency for little gain |
| `alpaca-py` | Commission-free paper equities with a real matching engine | **Best free way to run the equity arm live** — 4 bp-equivalent costs, honest fills, no capital |
| `python-binance` / `websocket-client` | Streaming instead of polling | Needed only if we move to tick-level |

### 4.3 The recommendation that follows from the measurement

The measurement says cost/frequency is the axis that matters. So the tooling
choice should follow cost realism, not feature count:

1. **Use `ccxt` sandbox (binance/bybit/okx testnet) as the live-execution
   venue.** It is installed, needs no new dependency, and provides honest order
   fills including fees. This is the correct substrate for a pretend-trading
   challenge — my REST-polling harness cannot see queue position or slippage.
2. **Use `live_daytrade_sim.py` as the measurement engine**, not my new file.
   It already has the correct fill convention and cost audit.
3. **Add `vectorbt` only when the parameter sweeps start**, because that is when
   PBO/CSCV deflation becomes mandatory rather than nice-to-have.
4. **Do not add `freqtrade`/`nautilus_trader` yet.** They are whole frameworks;
   adopting one before we have a single cost-surviving strategy is premature.

---

## 5. DEFECTS I FOUND IN MY OWN WORK THIS ROUND (2)

Recorded because this project's whole value is the audit trail.

| # | Defect | How caught | Fix |
|---|---|---|---|
| 1 | **Ledger data destruction.** My forward-harness `append()` keyed every row on `(hypothesis_id, observation_month)`. The 430 pre-existing `H-119` rows have no `observation_month`, so they all collapsed to one key — **430 rows → 1**. | Row-count check against `git show HEAD:` | Restored from git (byte-identical to HEAD verified), then rewrote `append()` to keep foreign lines as **raw strings, never re-keyed or re-serialised**; added an assertion `H-119 == 430` to every subsequent run |
| 2 | **A false claim embedded in my own code.** A `print()` in my cross-check script asserted *"gross was NEGATIVE before fees on my 30-symbol universe"* — written before the numbers existed. The actual result was gross **+28.22%**. | Reading my own output instead of trusting the statement | Corrected in this document. **This is the same failure mode as the 2026-11-20 retraction: claiming a number because it appeared in my output rather than because I verified it.** |

Defect 2 is worth dwelling on: I nearly shipped a conclusion that contradicted
my own data because I had pre-written the narrative. The lesson is that a
hardcoded *conclusion string* is as dangerous as a hardcoded number.

---

## 6. WHAT I NEED FROM PEERS (cross-check requests)

Be adversarial. These are the four places this round is weakest.

1. **Reproduce the 616% / 889% fee-to-gross ratios.** If gross edge is real and
   fees are 6–9× it, the entire project's search should move to *lower frequency
   × lower cost*, and every crypto 5m strategy should be abandoned. If those
   ratios are a cost-model artefact (e.g. 20 bp is unrealistically high for a
   maker order), the conclusion flips. **Check my fee assumption first.**
2. **Attack the fill convention.** `live_daytrade_sim.py` fills at the next bar's
   **open**; mine fills at the signalling bar's **close**. Which is defensible
   for a 5-minute breakout, and how much of the gross edge is a fill-convention
   artefact?
3. **Attack S7_ORB_EQ.** It is the only positive net result (n=161, PF 1.18,
   t=+0.89) and it is the basis for any equity claim. Is a *directional* verdict
   on 161 trades worth acting on, or is it the survivor of a 7-strategy search?
   What is the deflated Sharpe for a 7-way search?
4. **Confirm the Sunday scope limit.** Did any peer produce a *non-crypto* live
   fill at 2026-11-22 09:00 UTC? If so, from which venue, because cash equity,
   FX and most futures venues were closed.

---

## 7. NEXT ROUNDS FOR THIS CHALLENGE (mine)

| Round | Action |
|---|---|
| RT-2 | Re-run the challenge on a **weekday session** to unlock equity/ETF/FX arms. The Sunday constraint is a scope limit, not a result |
| RT-3 | Move execution to **ccxt sandbox** (binance/bybit/okx testnet) for honest fills, queue position and real fee schedules instead of assumed 20 bp |
| RT-4 | **Maker-first cost test:** does a limit-entry variant flip gross-positive into net-positive? This directly attacks the binding constraint. It is the highest-value single test available |
| RT-5 | Extend `live_daytrade_sim.py` to equities with `alpaca-py` paper (4 bp-equivalent) and test whether S7_ORB_EQ survives a deflation for the 7-way search |
| RT-6 | Schedule `live_daytrade_sim.py` in GHA (it currently runs nowhere) and start a forward clock on S7_ORB_EQ with written kill criteria |

---

## 8. BOTTOM LINE

**The challenge failed, and that failure is the useful part.**

- No live setup fired at the observed timestamp, so there was no "got rich in 2
  hours" story to tell.
- The rule at 5-minute frequency loses money with **p = 0.000**, but the loss is
  **not** because the signals are bad — gross is **positive** on both
  independent harnesses.
- **Fees are 6–9× gross edge.** Frequency is the arithmetic enemy.
- The only net-positive strategy in the repo's own 6,619-trade ledger is the
  **lowest-cost, lowest-frequency survivor** (equities, 4 bp) — and it is
  *directional*, not proven.
- Therefore the next question is not "find a better signal". It is **"find a
  cheaper way to capture this signal"** — maker orders, fewer trades, lower-cost
  instruments.

**Zero capital is sanctioned. No forward observation exists. Nothing here is
investment advice.**

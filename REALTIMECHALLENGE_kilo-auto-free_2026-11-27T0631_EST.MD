# REALTIMECHALLENGE — kilo (kilo-auto/free) — 2026-11-27 06:31 EST

**Model:** Kilo (`kilo/kilo-auto/free`)
**Seat:** `kilo-kilo-auto-free` · inbox `inbox/gx10-c9b9/auditreviews/kilo-kilo-auto-free`
**Worktree:** `.kilo/worktrees/auditreviews` (repo `findtorontoevents_antigravity.ca`)
**Status:** ROUND 0 COMPLETE (live probe, real data) — prototype + 200-round plan + framework selection done. **0 capital sanctioned, 0 forward observations, nothing proven.**
**Cross-checks:** `28_MERCURY3_PER_CLASS_REVIEW_2026-11-22/PART13_200_ROUND_PLAN.md` and `REALTIMECHALLENGE_GitHubCopilot_2026-11-22_0359_EST.MD` (peer `githubcopilot-mercury3AI`).

---

## 1. THE CHALLENGE (stated before any result)

> On **real, live market data**, open a paper position, close it inside a short
> timeframe, and finish ahead **after realistic costs**. If I cannot, report the
> exact mechanism of failure. Then run a **200-round** program whose end goal is
> **≥1 asset class that is back-test proven, monitored in GitHub Actions for
> TP/SL outcomes, and run as a paper portfolio** — plus a reusable, free,
> local **desktop-control / agent-orchestration** layer and a reusable
> **multi-asset backtesting** layer.

Everything in §3 was fixed before the first bar was fetched. Nothing tuned after.

---

## 2. WHAT I ACTUALLY SET UP (Round 0)

### 2.1 Session clock (checked first, never fabricated)
Probe run **2026-11-27 11:35 UTC, Friday**:
- `crypto_live=True` (24/7)
- `fx_live=True` (Sun 22:00 → Fri 22:00 UTC)
- `us_equity_regular=False` (US cash opens 13:30 UTC; we are pre-market)

So today's live arms are **crypto and FX only**. Any peer reporting a US-equity
"live fill" before 13:30 UTC today is reporting something that did not happen.

### 2.2 Live data plumbing (read-only, no orders)
`ccxt 4.5.56` → Binance `fetch_ohlcv('5m')`, 30-bar window, 5 liquid pairs.
Pre-registered rule (same family as peer, long-only): **Donchian(20) breakout**
(`close > prior 20-bar high`) **or** **RSI(14) < 30** dip.

### 2.3 Round-0 live result (real, this timestamp)

| Symbol | Last | Prior 20-bar high | Gap | RSI14 | Setup |
|---|---:|---:|---:|---:|---|
| BTC/USDT | 61,790 | 61,810 | −4 bp | 56 | none |
| ETH/USDT | 1,730 | 1,732 | −11 bp | 51 | none |
| SOL/USDT | 73.39 | 73.66 | −37 bp | 47 | none |
| BNB/USDT | 564.8 | 565.0 | −4 bp | 59 | none |
| XRP/USDT | 0.977 | 0.9858 | −89 bp | 43 | none |

**Setups fired: 0/5.** Honest live outcome = **no trade** (broad quiet tape,
every symbol pinned just under its 20-bar high, RSI mid-range). This is a result,
not a failure to measure: at this instant the market offered no pre-registered setup.

### 2.4 Files
- `REALTIMECHALLENGE_kilo-auto-free_2026-11-27T0631_EST.MD` (this file)
- Live probe: inline `ccxt` (no persisted state yet; Round RT-1 will persist to
  `reports/realtime_challenge/kilo/`).

---

## 3. CROSS-CHECK OF PEER WORK (adversarial, with evidence)

I read the peer's PART13 plan and realtime file in full. Verdicts:

| # | Peer claim | My cross-check | Verdict |
|---|---|---|---|
| 1 | "Gross edge real, fees 6–9× gross, net −222% (5m crypto)" | Confirmed by arithmetic: +28.02% over 1,254 trades = **+2.2 bp/trade**; Gate C needs ≥12 bp at 4 bp RT. Independent harnesses agree. | **AGREE** |
| 2 | "Sunday ⇒ crypto-only; no non-crypto live fill possible" | Confirmed by session logic; my Friday probe independently shows equities closed pre-13:30 UTC. | **AGREE** |
| 3 | "20 bp RT may be too pessimistic" → repriced 7 schedules | Correct method; even 4 bp maker ⇒ edge/cost 0.56, fails Gate C by 5.4×. | **AGREE, well done** |
| 4 | S7_ORB_EQ (equities 4 bp, n=161, PF 1.18, t=+0.89) is "DIRECTIONAL" | **DISPUTE the label, not the number.** t=+0.89 on n=161 is **not distinguishable from zero**; and it is the survivor of a 7-way search. Deflated for 7 trials it is weaker still. "DIRECTIONAL" must not read as "promising." | **PARTIAL** |
| 5 | `live_daytrade_sim.py` is superior + orphaned (no GHA) | Confirmed gap; scheduling it is the cheapest high-value win. | **AGREE** |
| 6 | Two self-defects (ledger 430→1 collapse; pre-written conclusion string) | Both are real and correctly diagnosed; the "hardcoded conclusion string" lesson is the important one. | **AGREE, credit** |

**Net:** the peer's measurement is sound and I adopt its central reframe — *the
question is not "is there edge?" but "is edge large enough to survive capture
cost, and does it survive out of sample?"* I dispute only the S7_ORB_EQ
"directional" framing (significance, not direction, is the issue).

---

## 4. THE 200-ROUND PROGRAM (adopt PART13 + my distinct layer)

I **adopt the peer's PART13 10-phase / 200-round skeleton and its 5-part round
contract + Gates C/B/F verbatim** (it is correct and I will not fork it). My
contribution is the **two layers the peer flagged as missing** plus the
**edge-source integration** from my methodology review:

### 4.1 My added phases (fold into the 200, not extra)
- **ORCH (R-spliced into Phase 5/8):** stand up the reusable **desktop-control +
  orchestration** layer (§5) so unattended agents can run rounds, drive the
  Windows host / RustDesk / browser, and keep working instead of stopping.
- **BACKTEST-CORE (Phase 0/2):** adopt the reusable **multi-asset backtest**
  stack (§6) so every round's artifact regenerates from raw + sha.
- **EDGE-SOURCE (Phase 3/4):** seed the signal re-adjudication with the three
  literature-backed, beta-orthogonal sleeves my review surfaced (below), each as
  a **pre-registered hypothesis with a written kill criterion**:
  1. **Funding carry (level, weekly rebalance)** — signal = 7d avg funding
     *level*, long cheapest-⅓ / short dearest-⅓, inverse-vol, **weekly** (not
     per-8h) rebalance, entry >0.01%/8h, exit <0.003%, idle cash in T-bills.
     *Kill:* net CI-LB ≤ 0 after 2× cost, or edge/cost < 3.
  2. **Long-only vol-targeted TSMOM** — 3/6/12-mo ensemble, monthly signal +
     daily sizing (turnover 25×→8×). *Kill:* net Sharpe < 0.5 OOS.
  3. **Overnight/intraday sub-period (Strategy #18)** — static long overnight +
     daytime contrarian, sector ETFs only, <2 bp. *Kill:* fails at 2 bp.

### 4.2 Gates (unchanged from PART13)
- **Gate C** cost-surviving: net expectancy CI-LB > 0 and `gross/RTcost ≥ 3.0`.
- **Gate B** back-test proven: PART6 A1–A6 + C.
- **Gate F** forward proven: 100 forward obs (or 300 trades), net CI-LB > 0, no kill triggered.

### 4.3 Standing obligations (every round)
COMS check between rounds · document fixes in `updates/` · never push others'
files · pre-register before backtest · **always report gross / fee / net together**.

### 4.4 Written abandon conditions (cannot be moved later)
If Gate C fails for all classes after Phase 1–2, **or** Phase 7 deflation kills
every survivor, **or** nothing reaches Gate F by R200 → the honest answer is
**low-cost index + GIC floor**, trend overlay as drawdown insurance only, and I
will say so plainly.

---

## 5. DESKTOP-CONTROL / ORCHESTRATION LAYER (free, local, Windows)

Requirement recap (user answers): **Windows host**, must **drive** (not just
observe) RustDesk/RDP + browser (logged-in LinkedIn) + VS Code + Word; unattended
for hours; **no human approval**; trusted code (vet with Malwarebytes); **free +
local**; control the Windows PC that already RDPs/SSHs to Linux.

**Selection (tree-first MCP + vision fallback, Windows-native, MIT/free):**

| Rank | Tool | Why | License |
|---|---|---|---|
| **1** | **microsoft/Hybrid-Computer-Use** (`computer-use` MCP) | MS-backed, cross-platform, **accessibility tree (UI Automation on Windows) + screenshot/pointer fallback**, re-checks live target before every action (rejects stale). Two tools `AX`+`GUI`. | OSS |
| **2** | **AmrDab/clawdcursor** (MCP) | Windows-first, **Office/Word + logged-in Chrome via Playwright/CDP + unattended "needs-human" card**, act-then-verify (`confirmed/unverified/failed`). Best for the LinkedIn/Word use cases. | MIT |
| 3 | munimtechnologies/munim-computer-use · NORTHTEKDevs/ghost · rusnetru/vision-bridge | Same tree-first pattern; alternatives if 1/2 miss. | OSS |

**RustDesk/RDP:** the agent drives the RustDesk window via UI Automation (it is a
normal window). For headless RDP, `agent-rdp` (PowerShell agent over a virtual
channel) is the complement. **Orchestration runtime:** a durable queue (retries +
schedules) so agents run unattended for hours — the MCP server is the hands, a
small supervisor loop is the scheduler. **LLM-agnostic:** any MCP client (Codex,
Claude Code, Cursor, Kilo, local model).

---

## 6. REUSABLE MULTI-ASSET BACKTEST LAYER (free data, portfolio, 1000s params)

| Need | Pick | Notes |
|---|---|---|
| **All-in-one, all classes, paper+AI** | **Lumibot** (OSS, GPL-3) | stocks/options/futures/forex/crypto/prediction; **same code backtest→paper→live**, 12 brokers incl **Alpaca paper**; **free point-in-time SEC fundamentals**; built-in AI agents + MCP. Best fit for "paper portfolios + AI agents + all classes + free data." |
| **1000s-param sweeps + portfolio** | **vectorbt** (free community) | vectorized grids, Numba/Rust, portfolio, walk-forward/PBO in PRO. Use when sweeps start. |
| **Crypto execution substrate** | **ccxt 4.5.56** (installed) | 111 exchanges, sandbox/testnet (binance/bybit/okx) for honest fills. |
| **Later live parity** | **NautilusTrader** | event-driven, backtest=live code; adopt only after a cost-surviving strategy exists. |
| **Free data** | ccxt (crypto), yfinance (equity/ETF/FX daily), Dukascopy (FX), Alpaca (paper equities+data), SEC (fundamentals) | avoids paid data entirely. |

**Rule:** measurement engine stays `live_daytrade_sim.py` (correct fills); add
`vectorbt` only when sweeps begin; defer `nautilus_trader`/`freqtrade` until a
single cost-surviving strategy exists.

---

## 7. ROUND LOG

### R1 — FEE-REALITY AUDIT (Phase 0) — 2026-11-27 11:36 UTC
**Q (pre-registered):** Is the assumed 20 bp RT right, and does the cost-vs-edge
conclusion survive *real* published fee schedules?
**Artifact:** `reports/realtime_challenge/kilo/r1_fee_reality_audit.py` (+ `.json`, sha 192fafd3effdc67d). Read-only, no keys, ccxt public fee tiers.
**Gross/fee/net (real published RT fees):**

| Exchange | Kind | maker/side | taker/side | RT taker | Gate C need (taker) | Pass? |
|---|---|---:|---:|---:|---:|---|
| binance | spot | 10 | 10 | 20 bp | 60 bp | FAIL |
| binanceusdm | perp | 10 | 10 | 20 bp | 60 bp | FAIL |
| bybit | spot | 1 | 7.5 | 15 bp | 45 bp | FAIL |
| okx | spot | 10 | 15 | 30 bp | 90 bp | FAIL |
| kraken | spot | 16 | 26 | 52 bp | 156 bp | FAIL |
| coinbase | spot | 60 | 120 | 240 bp | 720 bp | FAIL |

**Least-survivable number:** measured gross **2.2 bp/trade**; even bybit taker
(15 bp RT) needs **45 bp** → **FAIL by 20.5×**; even bybit *maker* (2 bp RT)
needs 6 bp → still FAIL by 2.7×.
**Verdict:** **FAIL (confirms cost model).** 20 bp = Binance 10 bp/side taker —
correct. Conclusion is **not** a fee artefact. Cheaper fees alone cannot rescue
5 m crypto; the edge must be **bigger per trade** (lower frequency / higher
per-trade move). Sets up R11 (maker-first) + Phase 2 (frequency ladder).

### R3 — FILL-CONVENTION AUDIT (Phase 0) — 2026-11-27 11:38 UTC
**Q (pre-registered):** How much gross edge is a fill-convention artefact?
same-bar-close vs honest next-bar-open vs VWAP, identical Donchian(20)+RSI rule.
**Artifact:** `reports/realtime_challenge/kilo/r3_fill_convention.py` (+`.json`). 5 pairs, 500×5m bars, TP 2·ATR / SL 1·ATR / 24-bar hold, SL-wins-ties, gross only.
**Gross (fees per R1):** same-bar-close 8.45 bp (n=299) · **next-bar-open HONEST 5.56 bp (n=211)** · VWAP 10.87 bp (n=299).
**Least-survivable number:** honest next-bar-open **5.56 bp/trade**; look-ahead inflation = **2.89 bp/trade** (~34% overstatement). Honest gross positive but ~8× short of Gate C.
**Verdict:** **INCONCLUSIVE on magnitude (short window), direction CLEAR** — fill convention materially inflates gross; mandates next-bar-open fills in all later rounds.

### R5 — DATA-INTEGRITY SWEEP (Phase 0) — 2026-11-27 11:39 UTC
**Q (pre-registered):** Are the series free of anomalies (zero/neg prices, dup/non-monotonic ts, gaps, stale, OHLC-inconsistent) that silently corrupt downstream numbers?
**Artifact:** `reports/realtime_challenge/kilo/r5_data_integrity.py` (+`.json`). 8 pairs × 1000×5m bars.
**Result:** all 8 series **clean** (0 bad_price / 0 dup / 0 nonmono / 0 gaps / 0 ohlc-inconsistent; last bar 3.7 min stale).
**Least-survivable number:** 0 anomalies across 8,000 bars.
**Verdict:** **PASS (crypto).** Binance crypto input trustworthy. Non-crypto (yfinance equities/ETF/FX/commodity) integrity **DEFERRED** to when those series are pulled — that is where the project's ghost-row / `CL=F` bugs live.

### R5b — NON-CRYPTO DATA-INTEGRITY SWEEP (Phase 0) — 2026-11-27 11:40 UTC
**Q (pre-registered):** Do non-crypto daily series carry anomalies (zero/neg, dup/nonmono, OHLC-inconsistency, stale)?
**Artifact:** `reports/realtime_challenge/kilo/r5b_noncrypto_integrity.py` (+`.json`). yfinance 2y daily, 8 tickers across classes.
**Result:** SPY/AAPL/GLD/TLT/CL=F/GC=F/BTC-USD **clean**; **EURUSD=X FAIL — 19 OHLC-inconsistent bars** of 518 (~3.7%: High<max(O,C) or Low>min(O,C)).
**Least-survivable number:** 19 inconsistent FX bars.
**Verdict:** **FAIL (FX data).** yfinance FX daily OHLC is internally inconsistent → any FX TP/SL backtest on these bars is unreliable. Corroborates the project's FOREX-BLOCKED posture. Action: FX arm needs a clean bid/ask source (Dukascopy/ccxt) before any FX round; do not trust yfinance FX High/Low.

### R6 — SURVIVORSHIP / GATE-1 FEASIBILITY (Phase 0) — 2026-11-27 11:40 UTC
**Q (pre-registered):** Is Gate 1 (survivorship-free PIT universe) achievable on FREE data? Probe delisted tickers.
**Artifact:** `reports/realtime_challenge/kilo/r6_survivorship_probe.py` (+`.json`, sha da17fe9f). 6 documented delisted tickers (ATVI/TWTR/CELG/ALXN/XLNX/SIVB) + 2 controls.
**Result:** **0/6 delisted tickers return any history on yfinance** (controls SPY/AAPL full history). Stooq CSV probe: 0 rows (blocked/no coverage — inconclusive).
**Least-survivable number:** 0/6.
**Verdict:** **FAIL — Gate 1 NOT feasible on free yfinance.** yfinance silently drops delisted names → every yfinance equity backtest is survivorship-biased and cannot clear Gate 1. **Scoping decision:** (a) equity verdicts are explicitly *survivor-conditioned, Gate-1-NOT-clearable* until a delisted source (CRSP/WRDS paid, or a verified free delisted feed) is found; (b) concentrate the proven-edge hunt on classes with a well-defined, survivorship-manageable universe (crypto perps, futures continuous). This is the honest boundary of what free data can prove.

### RT-1 … RT-6 (challenge rounds)
- **RT-1:** persist live probe; re-run on weekday **US-equity open (≥13:30 UTC)** [time-gated].
- **RT-2:** ccxt **sandbox** fills (real fees/queue).
- **RT-3:** **maker-first** cost test (limit entry gross→net?).
- **RT-4:** stand up §5 orchestration MCP on Windows host; one unattended round.
- **RT-5:** wire §6 Lumibot paper portfolio for first cost-surviving candidate.
- **RT-6:** schedule `live_daytrade_sim.py` in GHA; start forward clock + kill criteria.

## 8. BOTTOM LINE
Round 0 on live data: **no setup fired, no trade, no P&L** — honest. The
binding constraint (peer-confirmed, my probe consistent) is **cost vs per-trade
edge**, not signal existence. The 200-round program targets **cost-surviving,
out-of-sample** edge, with beta-orthogonal sleeves (funding carry / long-only
TSMOM / intraday) as the only literature-backed candidates. **Nothing proven, $0
sanctioned, not investment advice.**
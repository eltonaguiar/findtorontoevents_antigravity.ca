# 200-ROUND EDGE PROGRAM — Charter & Roadmap

**Owner:** `kilo-glm52-free-auditreviews` (seat) · host `gx10-c9b9` · worktree `auditreviews-v4`
**Started:** 2026-11-27T11:40Z · **Status:** Round 1 complete, Rounds 2–200 queued
**Bus:** `inbox/gx10-c9b9/auditreviews-v4/kilo-glm52-free-auditreviews`

---

## 0. The one-line mandate

Run **200 rounds** of development whose **end goal** is **one or more asset classes that are
at least back-test-proven and ideally forward-monitored (GitHub Actions) with paper
portfolios** — and, as a recurring reality check, a **live "pretend" trade on real live
markets** each round, reported honestly (win or lose).

## 1. What 200 rounds of evidence already told us (do not re-learn)

From `/audit`, `/audit2`, `/audit3`, `/audit/hyrotrader`, and both repos
(`antigravity_review_Nov192026`, `findtorontoevents_antigravity.ca`):

1. **No proven directional selection alpha.** audit3: 0 PROVEN / 1 CANDIDATE / 10 KILL / 126
   INSUFFICIENT. Rank persistence ρ≈0 (p=0.84). 166 strategy×class×direction cells, 0 pass.
2. **Gross edge ≈ round-turn cost in every class.** The binding constraint is **cost**, not
   signal. Per-trade edge is ~**5× too small** (Copilot R1: +2.2 bp/trade vs ≥12 bp needed at
   4 bp RT; even maker fees leave edge at 56% of cost vs the ≥3.0 gate).
3. **Fixed-TP/SL + daily resolution inflates PF 2–3×.** The only honest number is
   **intrabar first-touch, stop-biased**, with an optimistic/pessimistic **band**.
4. **Confidence is an anti-signal** (conf≥0.9 → 14% WR). The score booster already inverts it.
5. **The single most valuable missing piece = a forward ledger.** Nothing can graduate to
   PROVEN because live forward rows don't accrue. Fixing this is P0.
6. **Only crypto has free deep intraday data.** Everything else is daily-only free → allocation
   layer, not intrabar book.

**Design law for all 200 rounds:** *do not look for more signals; look for trades ≥5× bigger
per unit of cost, expressed with symmetric vol-scaled time exits, resolved intrabar-honestly,
and accrued on a forward ledger.*

## 2. The 6 phases (200 rounds)

| Phase | Rounds | Theme | Exit criterion |
|---|---|---|---|
| **P0 — Honest rails** | 1–20 | Forward ledger + intrabar-dual-run + cost gate wired; live paper harness (R1 done). | Every rule scored net-of-cost with PF band; ledger accrues. |
| **P1 — Cost-aware hunt** | 21–60 | Sweep horizon × cost × instrument; keep only gross expectancy > 3× cost. Promote **EDGE-1 funding-carry weekly** (first net-positive) to n≥100 forward. | ≥1 rule with net CI-LB>0 at 2× slip on ≥1 class. |
| **P2 — Conditional filters** | 61–100 | Regime/funding/vol/flow filters; 2nd-source for the luxalgo SHORT lead. | A conditional cell that survives DSR at honest N. |
| **P3 — Cross-asset** | 101–140 | Extend to equities ORB (only survivor), ETF/commodity trend, FX carry+trend (after backfill). | ≥1 non-crypto class with positive OOS. |
| **P4 — Forward paper** | 141–180 | GitHub Actions cron; paper portfolios; 90-day clock per pod. | Pods accrue ≥100 forward rows. |
| **P5 — Graduate / kill** | 181–200 | Promote survivors (PROVEN_T2), retire the rest with reason. | ≥1 PROVEN class OR a documented honest null. |

## 3. Round template (every round)

1. **Pre-register** the hypothesis + rule + cost model BEFORE looking at results.
2. **Live pretend trade** on real live data (crypto 24/7; equities only in US hours) →
   append to `REALTIMECHALLENGE_kilo-glm52-free_<ts>_EST.MD`.
3. **Backtest** the same rule on the Parquet lake, **intrabar dual-run**, report PF band + net
   CI at 2× slip + DSR at honest N.
4. **Cross-check peers** on the bus + git; reconcile which rules survive cost across models.
5. **Commit** code + a one-page `updates/round-NNN-<slug>.md` (what broke / changed / verified).

## 4. Reusable FREE framework decisions (from research)

- **Backtest stack:** `vectorbt` (10⁴-combo sweeps) + `NautilusTrader` (event-driven + paper,
  explicit intrabar path switch `bar_adaptive_high_low_ordering`) over a **Parquet data lake**
  you own; `bt` for daily allocation (mutual funds/bonds). Data lake is the durable asset.
- **Free data matrix:** crypto=Binance/CCXT (deep intraday); stocks/ETF=yfinance(30d 1m)/Stooq;
  FX=HistData tick (license strings); bonds=FRED/Treasury daily; mutual funds=NAV daily;
  futures=Stooq continuous (build the roll); options=DoltHub EOD chains. **No paid data.**
- **Intrabar honesty protocol:** tag every dataset `resolution`+`path_known`; require a detail
  series; where none, dual-run stop-first vs target-first and report PF as a **band**; ban
  daily-resolution from any headline; add a lookahead gate.

## 5. Desktop-control + orchestration (for unattended agent runs)

- **Stack:** Windows-MCP (tree-first local) + Playwright persistent context (logged-in browser)
  + **agent-rdp** (drives RDP/RustDesk via UIA over a Dynamic Virtual Channel) + **orca** or
  **agent-orchestra** (durable file-queue supervisor, 3-strike retry). $0 licence.
- **Rule:** tree-first → vision-fallback → abort (never blind-click). RDP kills the
  screenshot+click category. Host prep: `RemoteDesktop_SuppressWhenMinimized=2`, leave via
  `tscon`, disable idle-lock, enable NLA.
- **Starter:** `mcp.json` importing windows-mcp + orca; 5 automations in order: LinkedIn scrape
  → Word doc → VS Code → follow-up loop → RDP drive.

## 6. Peer cross-check (Round 1 reconciled — v3+v4 merged)

| Model | Universe | Result | Shared finding |
|---|---|---|---|
| deepseek-flash | 30-sym crypto 5m | 0 trades (signal drought) | zero=ZERO; record signal frequency |
| GitHubCopilot | 30-sym crypto 5m, 2 arms | gross +28%, **net −222%**; only equities ORB survives (t=0.89) | **cost eats edge; edge 5× too small** |
| kilo-mercury3 (v3, recovered) | crypto + **equities ORB** + exit-variant + basis | pre-registered E1/C2/X1; engine live | **equities is the only paying venue; test exit-expression** |
| kilo-glm52 (this, v4) | 5-sym crypto 1h, 3 rules | gross ~0, net negative; MR 21% win KILL | **same: cost-bound, MR loses, trend ~breakeven gross** |

**Consensus verdict R1:** no profitable short-window trade; the path is **bigger-per-cost
trades + lower frequency + honest forward ledger**, not more signals.

**MERGED FROM v3 (kilo-mercury3) — adopted into this program:**
1. **Cost-floor / power reality** (`reports/2026-11-22-cost-floor-and-power.md`, already in
   v4): cost is **six different problems**, not one — FUTURES dies at **1.8×** cost, EQUITY
   would need **614 bp** round-trip before cost binds (its problem is *multiplicity*, not cost).
   **MDE to detect a tradable 1.92 bp/day effect: EQUITY 207 yr, CRYPTO 633 yr** on daily data
   → **daily-return backtests cannot resolve the effect; the answer is event-driven per-trade
   sampling** (the basis H-201 already uses), not more years. This is now a P0 design law.
2. **Equities ORB arm (E1)** — the only net-positive cell in the estate's 6,619-trade sweep
   (`S7_ORB_EQ`, 4 bp, t=+0.89). Runs only in US cash hours (13:30–21:00 UTC weekdays).
3. **Exit-expression test (C2)** — same crypto entries, but **symmetric time-based vol-scaled
   exit** vs fixed SL/TP, to isolate the audit2 doctrine ("the exit expression changes the
   statistics more than the signal"). Cost-aware comparator C1 vs C2.
4. **Cross-venue basis (X1)** — pre-registered Binance-vs-KuCoin >50bp divergence arb, runs
   only when divergence appears (not hunted).

**Engine note:** `tools/realtime_challenge.py` (v4, 25KB) is the shared live harness
(`--open/--resolve/--backtest/--status`); `--status` at 11:52Z = crypto/futures/forex live,
equity gated to US hours; `--backtest` reconfirms the fee-wall (A1 n=459 WR 27.7% t=−11.15;
ALL permutation p=0.000; 20bp RT = 0.43× mean net).

**MERGED FROM v2 + base (2026-11-27 12:01Z) — executed probes, real artifacts in
`reports/realtime_challenge/kilo/`:**
1. **★ First net-positive signal in the fleet — FUNDING CARRY (level, WEEKLY rebalance)**
   (`edge1_funding_carry.py`, reproduced live 12:01Z): weekly **net +27.9 bp/trade, Sharpe
   0.494, n=24**; per-8h churn **−14.1 bp, Sharpe −3.32, n=599**. **Rebalance frequency IS
   the edge** — weekly collect-carry works, per-8h churn destroys it. **Marginal** (Sharpe
   0.494 just under the 0.5 kill bar) and **underpowered** (n=24). → new **EDGE-1 pod**,
   pre-registered kill = net CI-LB≤0 or Sharpe<0.5 OOS; needs n≥100 forward + 2× cost stress.
2. **Fill-convention audit (R3):** same-bar-close 8.45bp vs **honest next-bar-open 5.56bp**
   vs VWAP 10.87bp → look-ahead inflates gross ~34%. **Mandate next-bar-open fills** in all
   later rounds.
3. **Fee-reality audit (R1):** 20bp = Binance 10bp/side taker, correct; even bybit maker
   (2bp RT) needs 6bp vs 2.2bp edge → still FAIL 2.7×. Cheaper fees alone can't rescue 5m.
4. **Survivorship probe (R6):** 0/6 delisted tickers return history on yfinance → **Gate 1
   (PIT universe) NOT feasible on free equity data**; concentrate proven-edge hunt on
   survivorship-manageable universes (crypto perps, futures continuous).
5. **Non-crypto data integrity (R5b):** yfinance equities/ETF/commodity/futures **clean**;
   **EURUSD=X FAIL (19 OHLC-inconsistent bars)** → FX arm needs a clean bid/ask source
   (Dukascopy/ccxt); do not trust yfinance FX High/Low.
6. **nous-stepfun (v2) design:** TSMOM commodity (DBMF/KMLM proxy) + 10mo SMA SPY overlay,
   vectorbt sweep + GHA daily tick — adopted as the **Phase-3 cross-asset template**.
7. **kilo-auto-free (base):** adopts PART13 10-phase/200-round skeleton + Gates B/C/F;
   adds ORCH (desktop) + BACKTEST-CORE (Lumibot/vectorbt) + 3 beta-orthogonal sleeves
   (funding carry / long-only TSMOM / overnight-intraday). **Disputed S7_ORB_EQ "directional"
   label** (t=+0.89 on n=161 is not distinguishable from 0, survivor of 7-way search).

## 7. Definition of done for the 200-round program

≥1 asset class with: **intrabar-honest net PF CI-LB > 1.0 at 2× slip**, **DSR>0.95 at honest
N**, **≥100 forward rows** accrued via GitHub Actions, **paper portfolio** live — OR a
documented, reproducible **honest null** with the cost arithmetic that killed each candidate.
Either outcome is a win; a hidden daily-resolution PF is not.

## 8. EDGE registry (live status, updated each deep round)

| ID | Hypothesis | Deep-test result | Status | Kill / promote criterion |
|---|---|---|---|---|
| **EDGE-1** | Crypto funding-carry level, weekly | **FALSIFIED as carry**: 89% price / 11% carry; t=1.46, CI [−10.8,+137]; OOS unstable; 2/27 sweep cells sig=chance (`edge1_stress.py`) | **OBSERVE_ONLY** (price factor) | retire unless forward n≥100 & CI-LB>0 |
| **EDGE-2** | Funding EXTREME reversal (high→short) | **proven mechanism**: pure price reversal long-losers/short-winners +148bp t=1.47; momentum −166bp t=−1.64. EDGE-1 ≡ this factor; still not sig (n=24) | **OBSERVE_ONLY** | net CI-LB>0 @2× cost, n≥100 fwd |
| **EDGE-3** | Cross-venue funding dispersion (Binance/Bybit) | not yet run | QUEUED | net CI-LB>0 @2× cost |
| **EDGE-4** | TSMOM on DBMF/KMLM managed-futures | not yet run (nous template) | QUEUED | net Sharpe≥0.5 OOS |
| **EDGE-5** | SPY overnight (close→open) | **gross +3.34bp/d t=4.61 (real)**; net −0.66 @4bp, **+2.34 @1bp t=3.23** (`edge5_overnight_spy.py`) | **CANDIDATE (execution-dependent)** | promote only at ≤2bp fills; else retire |
| **EDGE-6** | Equities ORB (US hours) | engine `--backtest` only (S7_ORB_EQ t=0.89, not sig) | WATCH | n≥100 fwd & CI-LB>0 |

**Shipped this round:** forward ledger (`reports/realtime_challenge/kilo/forward_ledger.py`) +
GHA monitor (`.github/workflows/edge-forward-monitor.yml`) — accrues EDGE-1/EDGE-5 net-of-cost
observations daily/weekly, idempotent, `[skip ci]` commits. Deep-dive:
`updates/round-EDGE1-stress-funding-falsified-2026-11-27.md`.

**Method laws added:** (L1) decompose any "carry" claim into carry vs price before believing it;
(L2) sweep ≥20 parameter cells and report how many clear by chance before calling a cell an edge;
(L3) a rule is not "net-positive" if its 95% CI at zero cost straddles zero — that is underpowered,
not profitable.

*Paper only. Not investment advice.*
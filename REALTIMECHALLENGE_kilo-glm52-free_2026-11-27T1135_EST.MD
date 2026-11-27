# REALTIMECHALLENGE — kilo-glm52-free-auditreviews — 2026-11-27T11:35Z (EST)

**Model seat:** `kilo-glm52-free-auditreviews`
**Host / worktree:** `gx10-c9b9` / `auditreviews-v4`
**Session:** `ses_de339c4bbffeu0IPRl2Z1Bg`
**Bus inbox:** `inbox/gx10-c9b9/auditreviews-v4/kilo-glm52-free-auditreviews`
**Artefact:** `REALTIMECHALLENGE_live.py` (this worktree) + this file.

---

## 1. What the "Realtime Challenge" is

A recurring, honest, **paper-only** live-market trial: pull the most recent **closed**
candles from a **real, live, free** venue (Binance public REST, no key), evaluate a
**pre-registered** rule set, emit a paper trade with explicit **entry / stop / target /
time-horizon**, and resolve it **intrabar first-touch (stop-biased on ties)** against the
bars that actually printed afterwards. One observation per bar per symbol. No orders are
sent. No secrets. The output is a *measurement*, never an edge claim (n is small).

It exists because the audit corpus (audit3, antigravity_review_Nov192026) proved the old
pipeline's headline PF was a **daily-resolution artifact** (2–3× inflation) and that the
book has **no proven directional selection alpha**. So the challenge is deliberately built
to *not* repeat that mistake: symmetric vol-scaled exits, time exit primary, honest
intrabar resolution, optimistic-vs-pessimistic gap reported.

## 2. Round 1 setup (what I actually ran)

- **Venue / data:** Binance spot public API — `GET /api/v3/klines?interval=1h&limit=500`
  and `/ticker/24hr`. Free, keyless, 24/7. (Crypto is the only asset class with free,
  deep, intraday data — see §6.)
- **Universe (5):** BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT.
- **Rules (pre-registered, symmetric ATR brackets, 12h time exit):**
  - `trend_pullback_1h` LONG — EMA20>EMA50, RSI(14)<55, price ≥ 0.995·EMA20
  - `mean_reversion_1h` LONG — RSI(14)<32, price > 1.01·min(200h)
  - `trend_short_1h` SHORT — EMA20<EMA50, RSI(14)>60, price ≤ 1.005·EMA20
  - stop = ±1.5·ATR(14), target = ±2.5·ATR(14) (symmetric, vol-scaled)
- **Resolution:** walk bars after the signal bar; stop-first on same-bar tie; else time
  exit at 12h close.
- **Live snapshot (2026-11-27 11:35Z):** no rule fired on the *last* closed bar →
  I ran a **replay over the trailing ~280 closed 1h bars** to produce real observations.

## 3. Round 1 result (real data, paper)

```
total paper trades (replay 1h): 122
by status: STOP 64 | TARGET 42 | TIME 16
mean pnl -0.1170%  median -1.0987%  win 44.3%  n=122   (GROSS, before costs)

  mean_reversion_1h   n= 24  mean -1.1725%  win 21%
  trend_pullback_1h   n= 98  mean +0.1415%  win 50%
```

**Interpretation (honest):**
- **Mean-reversion is a clear loser** at 1h on majors (21% win, −1.17% avg). KILL.
- **Trend-pullback is ~breakeven GROSS** (+0.14% avg, 50% win). At the measured crypto
  round-turn cost (~20 bp major / ~52 bp alt) it is **net-negative**. NOT an edge.
- The **median (−1.10%) ≫ mean** gap = a few winners carry the mean; classic
  stop-first asymmetry. This is exactly the geometry the audit warned about.
- **Verdict R1: no profitable trade found in the short window.** Reported, not hidden.
- **Why not:** the rules are textbook trend/MR with symmetric brackets; on 1h majors the
  gross edge is inside the cost band. To win we must either (a) drop timeframe/cost
  (lower-fee venue, longer horizon so cost is a smaller fraction), or (b) find a
  *conditional* filter that lifts gross expectancy above ~3× cost (the audit's cost gate).

## 4. What I set up / wired

- `REALTIMECHALLENGE_live.py` — self-contained, stdlib-only (urllib), reproducible.
  `--json` for machine reading; default prints plan + resolution.
- Registered on COMS bus with goal/todo/done (see §1).
- This file is the durable drop; peers cross-check via the bus + git.

## 5. Next iterations queued (R2+)

1. **Cost-aware ranking:** add the canonical cost-of-record (crypto 20/52 bp) and only
   keep rules whose *gross* expectancy > 3× cost (audit cost gate).
2. **Horizon sweep:** 4h/12h/24h/72h time exits — cost becomes a smaller fraction.
3. **Conditional filter hunt:** regime (BTC trend), funding, vol regime — the audit's
   only live candidate (`luxalgo_confluence SHORT`, DSR 0.989) was blocked by
   single-source concentration, not stats → re-derive with a 2nd source.
4. **Honest dual-run:** stop-first vs target-first PF band on every rule.
5. **GitHub Actions monitor:** cron the script hourly, commit a JSONL ledger, so TP/SL
   resolution accrues forward (the audit's #1 missing piece: a forward ledger).

## 6. Cross-asset note (feeds the 200-round plan)

Only **crypto** has free deep intraday data. Stocks/ETFs = yfinance 30d 1m; FX = HistData
tick (license strings); futures/bonds/mutual-funds/options = **daily-only free** → they
belong in the vectorized/allocation layer, never the intrabar-sensitive book. The reusable
free backtest stack I recommend: **vectorbt (sweeps) + NautilusTrader (event-driven +
paper, has an explicit intrabar path switch) over a Parquet data lake**, with `bt` for the
daily allocation sleeve. Full matrix in the consolidated report.

## 7. Peer cross-check

Peers writing their own `REALTIMECHALLENGE_<model>_<datetime>_EST.MD` in this worktree.
I will diff rule sets + results on the bus (`mentions/all`, `inbox/.../all`) and in git,
and reconcile which rules survive cost across models before Round 2.

**v3 recovery (2026-11-27 11:52Z):** recovered `kilo-mercury3` (v3 worktree) — its file +
the shared `tools/realtime_challenge.py` engine + `reports/2026-11-22-cost-floor-and-power.md`.
Adopted into the charter: cost-floor/power law (event-driven sampling, not daily), equities ORB
arm (E1), exit-expression test (C2), cross-venue basis (X1). Engine `--backtest` reconfirms the
fee-wall (A1 WR 27.7% t=−11.15, permutation p=0.000). v3 had no other unique work (same HEAD,
only the one untracked file).

**v2 + base recovery (2026-11-27 12:01Z):** recovered `nous-stepfun` (v2, TSMOM commodity
design) and `kilo-auto-free` (base) with its **executed probe suite** now in
`reports/realtime_challenge/kilo/`. **Headline: the fleet's first net-positive signal —
funding carry level + WEEKLY rebalance, net +27.9 bp/trade, Sharpe 0.494, n=24** (reproduced
live); per-8h churn is −14 bp (rebalance frequency is the edge). Marginal + underpowered →
EDGE-1 pod. Also adopted: next-bar-open fills (R3, look-ahead was +34%), fee-reality (R1),
survivorship Gate-1 infeasible on free equity (R6), yfinance FX OHLC unreliable (R5b).

*Paper only. Not investment advice. No orders sent.*
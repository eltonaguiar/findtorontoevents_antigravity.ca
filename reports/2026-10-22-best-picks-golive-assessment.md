# Best Possible Picks — Go-Live / Go-Public Readiness Assessment (2026-10-22)

**Framing:** We are assessing what our *best possible* picks are across every agent's
work (Buffy, Grok, Zoo/Code, GHCOPILOT, OpenCode, INCEPTION/VLLM, Poolside/Kilo), for a
hypothetical go-live / public disclosure. **Nothing here is money-ready.** This is an
honest, ranked disclosure of evidence quality — not a buy list, not financial advice.

---

## The headline a public entity must state plainly

**0 of 9 asset classes are MONEY-READY.** Every pooled "winner" in the last 24h either
(1) decays forward, (2) collapses under one-position-at-a-time overlap removal, or
(3) is a resolver / look-ahead / batch-close artifact. That is the honest disclosure.

The single most important operational fact: **the scoreboard itself was corrupt** (the
frozen-exit resolver bug, fixed today 21:26 in commit `305f9a79`). It stamped one price
snapshot onto many open picks → fake win clusters → inflated every headline. The fix only
affects *future* resolutions; historical rows are NOT rewritten. So all pre-fix numbers are
suspect by default.

---

## Ranked best-possible picks (by evidence quality, net of costs)

### #1 — CRYPTO SHORT @ 1h RSI(14) ∈ 30–50  ·  label: CANDIDATE (strong)
*Owner: Buffy · the strongest evidence anywhere in this codebase.*
- **Why it's #1:** the only candidate that clears all ten institutional outputs on the
  honest cohort. Net PF **2.163**, day-block bootstrap 90% CI **[1.38, 3.31]** (low end
  stays above 1.0), Sharpe **3.34**, Sortino **8.59**, MaxDD **0.14%**, Calmar **11.1**,
  CVaR5 −0.03%/day, beta to BTC **≈0**, positive alpha **+1.56%/yr**. Survives 2× costs
  (PF 1.83).
- **Definitive coin-flip proof:** random-entry null — real PF beats **99.8%** of 1,000
  same-universe random books (95th-pct PF 1.74). The RSI *timing rule*, not just "shorts
  did well," produces the edge.
- **Diversified:** 31 symbols, top-3 = 60% of profit (acceptable), momentum-confirmed
  variant (F2 WITH) is stronger still (PF 2.475, CI low 1.57).
- **Why NOT proven:** the cohort is *retrospective*. Registry rule M-107 requires a fresh
  sealed forward sample (rules hashed, append-only, no re-tuning) to ~100 trades.
- **Direction:** SHORT only. This is a scalp/intraday edge (high time-in-market, thin
  per-trade edge, needs tight costs).

### #2 — ETF / equity monthly tactical rotation (TAA, MRBB+200d, IBS<0.15+200d) · CANDIDATE (research)
*Owner: Kilocode/Grok/Claude lane · the only *deployed, defensible* instrument.*
- **Why it's #2:** Sharpe **0.88 vs SPY 0.74**; bootstrap Sharpe positive across 2007–2026
  including 2008/2020/2022; MRBB+200d OOS n=487 PF 1.84; IBS+200d n=775 PF 1.63. Monthly
  rebalanced, diversified 3–5 ETFs. The combined book (edge_proof) scores ~70/100.
- **Why NOT proven:** monthly data only (no per-trade daily equity), costs assumed from
  daily bars, next-open entry untested, no sealed forward. MDD 20.5% breaches the 20% bar
  by 0.5pt on the combined book.
- **Direction:** LONG only. This is the *long-term* product, not a pick engine.

### #3 — stock `rs-breakout-scout` LONG · CANDIDATE (watch)
*Owner: Zoo/Code hidden-winner scan · surfaced today, NOT shown on /audit at all.*
- n=58, WR 55.2%, PF **2.00**, **1.88 at 2× costs**, 51 distinct close days, top-symbol
  XOM 21%, PF 2.35 excluding it. The cleanest *equity* lead found.
- **Why NOT proven:** n=58 < 100; CI-LB 0.99 (crosses 1.0). Needs a sealed forward test to
  n≥100. **This is the top stock candidate to seal next.**

### Watch / weak (do not headline)
- **high_trust_momentum (CRYPTO)** — CANDIDATE (weak): n=61, WR 60.7% gross, but PF ~1.29 net,
  bootstrap CI crosses 0, October decay WR 38.1%. DSR fails (many crypto trials).
- **luxalgo_confluence SHORT** — CANDIDATE (weak): largest n (572) but **fails the full-cohort
  ten-point battery** (net PF 0.971, CI [0.77,1.22] crosses 1.0). Only its last-30d slice was hot.
- **ML stack (ml_gatekeeper / ml_consensus)** — backtest-only "VALIDATED" (+8.4pp / +10.7pp WR
  holdout), but the **live A/B gate shows 0 emissions on both sleeves (PENDING)**. Cannot be
  headlined until it emits live and accrues n≥30/sleeve.

### REFUTED / FAIL (must be disclosed as such)
- **copper HG=F "PROVEN"** — REFUTED: 751/815 overlaps + SL-before-TP artifact.
- **mega_mutation** — REFUTED: 955 rows closed <2 min after entry (look-ahead) + created_at NULL.
- **BOND PF 1.79** — REFUTED: from a replay-artifact file, not real fills.
- **copy-trader** — FAIL: feed frozen since 06-21 (D2).
- **AI-tournament BOND/ETF** — coin-flip: 60% MISPRICED_ENTRY, no costs.

---

## Data-integrity bugs found this pass (must be fixed before any go-live claim)

1. **DSR > 1 is impossible** (DSR is a probability, caps at 1.0). `strategy_funnel_data.json`
   has **24 strategies with DSR > 1** (max 15.3). These are computation bugs that inflate
   confidence. Must be clamped/recomputed.
2. **Sentinel `-999999.9999`** present in `walk_forward_avg_os_sharpe` (strategy index 27).
   Must be excluded from all aggregates (Grok R7).
3. **Crypto-perp mislabeled as EQUITY**: `SPYUSDT` (n=18), `TSLAUSDT` (n=13) — genuine label
   bugs. (The `ZC=F`/`HG=F`-style "FUTURES vs COMMODITY" flags are *legitimate* futures
   contracts, not bugs — do not "fix" those.)
4. **0-price / placeholder exits**: 38 rows (Zoo already fixed the generator + renderers to
   drop exit_price ≤ 0). Verify the fix reaches production.
5. **DB "Access denied"** on the PHP fund/crypto/forex portfolio APIs — likely a stale MySQL
   password on the 50webs server config. **The error page leaks the DB username + server IP —
   a security fix, do it before going public.**

---

## Symbol-universe expansion (concrete)

Proven-winner symbols **missing from the active scan universe** (add these): `AUDJPY=X`,
`GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`.

Institutional-consensus large-caps derived from T1/T2 mutual-fund top holdings (fundamental
lane, feed to the equity conditional miner — *not* a buy list): **MU, NVDA, AAPL, MSFT,
GOOGL, AVGO, GOOG, META, TSLA, AMZN, SPG**. Rationale: these are the names 2–4 of our
highest-scoring funds actually own — the "safe" institutional edge — so run conditional
LONG entries on these only, rather than on a thin contaminated universe.

---

## What "best possible pick" means for a public entity (the honest answer)

If we had to name our single best product today it is **the ETF tactical-rotation sleeve**
(only deployed, diversified, benchmark-beating), and our single best *statistical edge* is
**CRYPTO SHORT RSI 30–50** (clearest beyond-coin-flip proof, but scalp-only and
retrospective). Neither is money-ready. The go-live path is: (1) fix the data-integrity
bugs above; (2) seal forward paper cohorts for the top-3 candidates to n≥100; (3) only label
PROVEN-FORWARD / MONEY-READY when a sealed forward sample re-confirms out-of-sample with
operator sign-off. Until then the correct public statement is **"0 money-ready strategies;
N candidates under sealed forward evaluation."**

*NFA. All figures net of round-trip costs (16bp crypto / 4bp equity / 2bp FX). Read-only
measurement; no production data modified by this assessment.*

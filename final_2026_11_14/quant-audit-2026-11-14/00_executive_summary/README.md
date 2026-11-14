# Executive Summary — Adjudication of All 2026-11-14 Peer Work

**Author:** Freebuff (quant auditor) · **Worktree:** `.worktrees/quant-audit-2026-11-14` · **Branch:** `audit/quant-remediation-plan`
**Date:** 2026-11-14 · **Scope:** every peer deliverable, every recently modified file, and the remote GitHub for 2026-11-14.

This folder does not re-state peers' work — it **tests** it. Each headline claim below was
either re-executed, recomputed, or marked unverifiable. Where a peer is right, I say so and
say what it still lacks. Where a peer is wrong, I name the specific number that breaks.

---

## Adjudication table

| Peer | Headline claim | My verdict | Evidence |
|---|---|---|---|
| **deepAI** (`audit/live-audit-2026-11-14`) | Walk-forward variant C: n=237, PF 1.26, +98.7pp, p<0.0013 | **REPRODUCED EXACTLY** — but sub-T2 and selection-based, not market edge | Ran their `walkforward_v6.py` verbatim on the live 34.5 MB payload → `n=237 WR=47.3% PF=1.26 sum=+98.7pp z=-0.84`, null `0/800` |
| **Kilo** (childlike-airport) | Regime-filtered VWAP: Sharpe 3.76, DSR 1.0000, "VALIDATED" | **REFUTED** — fatal annualization unit error; PBO gate inverted | Their own table: 12.7% total over ~22 months ⇒ implied ann. vol **1.84%** at Sharpe 3.76. Impossible at 40% size in 4h crypto |
| **ITERATION-005** (finpredict v1) | Vol-targeted trend: Sharpe 2.13, t=5.56, "PROVEN" | **PARTIALLY SUPPORTED, mislabelled** — internally consistent, but ≈ beta; significance tested against zero, not against buy-and-hold | Their own caveat: buy-and-hold of the same 10 had Sharpe ≈2.2. Mine: TSMOM365 OOS Sharpe 0.57, null p=0.200 |
| **finpredict v1/v2/v3/v4** | FAIL verdict; 10 numeric corrections; 0/9 money-ready | **CORROBORATED** (independent method, same direction) — one v2 statement is now stale | v2 crossref says the live-audit branch is "not on origin"; it **is** on origin now (verified) |
| **hilarious-seer** | FAIL; zombie/freshness defects | **CORROBORATED** | Matches my ledger counts within window differences |
| **flaxen-hair** | `pnl_pct` mixes ratio and percent units, up to 100× | **CORROBORATED — strongest single defect found by any peer** | Their recomputation is sound; it explains several "impossible" numbers elsewhere |
| **scratch-hippodraco** | Per-class quick wins | **ACCEPTED as advisory** (no statistical claims to test) | 12 files, 708 lines |
| **opencode** (sibling in this folder) | 0/166 money-ready cells | **CORROBORATED** | `06_evidence/screener_results_2026-11-14.json`, unmodified |
| **My own search** (v1–v4, 40 trials) | 0/40 pass null + DSR | **STANDS** | `02_my_findings/2026-11-14-edge-search-results.md` |

---

## The three things that actually matter

1. **The system is not profitable and every peer agrees.** Six independent FAIL verdicts, four
   methods. There is no dissent to reconcile — only different numbers for the same rot.

2. **Only one "profitable approach" claim survives contact: deepAI's variant C.** I re-ran it and
   it reproduces to the decimal, which is rare and creditable. But read what it proves: *selecting
   the top-6 strategies by prior-month profit factor beats selecting 6 at random.* That is
   selection skill over a pool containing thousands of clone re-emissions. It is **not** a market
   edge, its own win rate (47.3%) is below coin-flip with z = −0.84, and 4 of its 8 months lost
   money. It is a legitimate **paper pilot**, not a tradeable edge.

3. **The Kilo "VALIDATED" VWAP claim is arithmetically impossible as written.** 12.7% total return
   over 22 months with a reported Sharpe of 3.76 implies 1.84% annualized volatility on a
   40%-sized 4h crypto book. BTC alone runs 40%+. The 3.76 is a per-trade or per-bar ratio printed
   as if it were an annualized Sharpe. Compounding it: PBO 0.489 is reported as a **PASS** because
   the gate was written as `< 0.5` — a coin flip relabelled as success. The repo's own standard
   (`docs/BACKTEST_ADMISSIBILITY_STANDARD.md`) requires PBO ≤ 0.10.

---

## What I could not verify (stated, not guessed)

- **Kilo's harnesses** (`/tmp/kilo/regime_filtered_vwap_v1*.py`) are not in the repo and `/tmp` is
  ephemeral — the claim is unreproducible by construction. I refuted it from its own published
  table instead.
- **ITERATION-005's data pipeline** (2,490 bars claimed as 7.4 years = 336 bars/yr, not ~365) has
  an unexplained 8% bar deficit; I did not re-download 7.4 years of Binance data to settle it.
- **deepAI's branch** is based on `f54efb3b4ac` (2026-06-06 tree) and is **23,488 files** apart from
  `main`; it cannot be merged as-is. The payload it analyses is fetched live, so the *analysis* is
  current even though the *tree* is not.
- **`resolution_method` is `None` for all 3,500 `recent_closed` rows.** This is the single fact that
  blocks certifying any PF number in the system, including variant C: you cannot tell a take-profit
  from a timeout. Nobody — peer or mine — can currently prove *how* any trade closed.

---

## Bottom line

The research question "is there a proven profitable approach in this system today?" has one honest
answer: **no.** The closest candidate (deepAI variant C) reproduces and deserves a pre-registered
paper pilot; it does not deserve capital. The two "statistically valid" peer claims are one
accounting error and one beta masquerading as alpha. The deployed ledger remains 0/166 money-ready.

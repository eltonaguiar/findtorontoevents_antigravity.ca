# CRYPTO — how to get profitable (deepAI, evidence-first)

## My measured truth (live, 2026-11-14)
- Active: 125 picks, **76.4% EXPIRED zombies**, repriced open P/L **mean −2.57%** (worst class;
  Binance spot truth, 3,745 symbols available for repricing).
- Strategy sources in my V1 cell search: crypto cells PF **0.23–0.83** except one
  `etf_rsi_momentum_bollinger`-style outlier 1.14 — i.e. **the system's crypto zoo is anti-skill**.
- Variant C walk-forward: **1 crypto trade in 8 months** (n=1 of 237) — the pre-registered
  selection rule *auto-excludes* crypto because crypto strategies fail the training-PF gate.
- Ledger disagreement: **0 `mega_mutation` rows on `recent_closed`**, but 318 cells in
  `pf_registry` (top cells `is_single_source_artifact=True`, PF 49–53 at n=124).
- finpredict-v3's independent count: 4,907 closed crypto rows, WR 35.9% / PF 0.92 (anti-skill),
  86.7% of active_raw are zombies, `current_price==entry` frozen on 24/7 symbols.

## What peers propose (adjudicated in `01_peer_review`)
1. **Diversified vol-targeted TSMOM** (finpredict, now self-corrected): credible risk premium,
   bear-inclusive OOS Sharpe **0.57, null p=0.200** (quant-audit) — not proven alpha; bull-window
   2.13 was beta-vs-B&H. → keep as *external sleeve*, benchmark-relative.
2. **Funding/carry** (finpredict-v2): BTC-only 4.8% vs 4.5% cash at 1.5× capital, n=10 —
   clears cash by 0.3pp → **cash-alternative, not alpha**; capacity-limited.
3. **mega_mutation** (flaxen-hair): best system candidate (my V2: n=18 PF 3.20 p=0.048 both
   halves) but single-source, strict n=16, 21/50 rows synthetic → **disputed "PROVEN"**.

## My plan (concrete, ordered)
1. **Do not trade the system's crypto zoo. Ever.** Evidence: PF 0.23–0.92 everywhere, 76–87%
   zombies, frozen phantom prices. This is the *only* class where the honest answer is a
   permanent NO to the deployed strategies.
2. **mega_mutation verification test (cheap, decisive):** have flaxen-hair publish the 50
   forward rows (symbol, side, entry_ts, tp, sl, exit_ts, exit_px); I (or any peer) verify
   each against **Binance klines** — did price actually reach TP/SL intrabar? Pass → gated
   paper pilot (¼ Kelly); fail → the claim dies with it. This closes dispute #6 either way.
3. **External TSMOM sleeve (optional, non-system):** 50d+200d blend, 20% vol target, 20–40
   liquid pairs, 0.1% cost, **pre-registered on a bear-inclusive window**, measured as
   excess-of-B&H with paired bootstrap (finpredict's corrected protocol). Expect Sharpe
   0.5–1.0 honest, DD −17–27%. It is a diversifying sleeve, never a headline edge.
4. **Funding carry ≤10–15% of book** as cash substitute (finpredict-v3's cap) — only after
   the price-freshness pipeline is live.
5. **Data gates first** (see `_overall.md`): garbage-ingest guard (my fixspec — kills
   entry=0.0 and 100× unit rows), zombie purge, `current_price` live or `UNQUOTED`.

**Tradable today: NO.** Earliest honest date: after mega_mutation verification + data gates;
expected edge class = risk premium (0.5–1.0 Sharpe), not alpha.

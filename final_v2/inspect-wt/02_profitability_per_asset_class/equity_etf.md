# EQUITY / ETF — how to get profitable (deepAI: the only system-native path)

## My measured truth (live, 2026-11-14)
- Active: EQUITY 232 picks (71.6% zombie, real open P/L −0.22%), ETF 100 (76% zombie, −0.00%).
- **Variant C walk-forward decomposition (my best evidence anywhere):**
  - **ETF n=120 PF 1.21 (+26.5pp)** · **EQUITY n=112 PF 1.30 (+73.1pp)** → 232 of 237 forward
    trades, +99.6pp of the +98.7pp total (BOND n=4, CRYPTO n=1 = noise).
  - Contributors: `vwap-reversion-scout` n=15 **PF 3.74** (+46.9pp, ≈47% of all P/L),
    `rs-breakout-scout` n=110 PF 1.26 (+35.3), `donchian-stock-breakout` n=28 PF 1.39 (+26.5),
    `mtf-align-scout` n=19 PF 1.50 (+10.4), `gap-and-go-stocks` n=1 (+11.7).
  - Monthly PF: May 2.63 · Jun 1.02 · **Jul 0.50 (−45.9pp disaster)** · Aug 1.74 · Sep 1.28 ·
    Oct 1.49 · Nov 1.72 (4 improving months).
  - Robustness re-executed for final stage: **clone-dedup holds** (6/237 same-day clones;
    dedup PF 1.25–1.27, +94.7–99.2pp); reproduced exactly by quant-audit AND finpredict-v2.
  - Honest weaknesses (accepted): sub-T2 (PF 1.26<1.5, WR 47.3%<50%), selection-based null,
    `slippage_pct`=0 on closed rows (UNVERIFIED — breakeven buffer 0.416%/trade), Oct-23
    vintage objection open, `resolution_method=None`.

## What peers propose
- **finpredict final_v2:** replace single-name scouts with a diversified factor portfolio
  (momentum+value+quality+low-vol, 50+ names, monthly, risk-matched benchmark) — Sharpe ~0.4–0.8.
  Names my variant C as "a lead to reproduce" (it has since been reproduced twice).
- **finpredict-v3:** fundamental factor (Piotroski/quality), market-neutral long/short to
  remove beta, then PEAD sleeve with a real data source; ETF: multi-asset trend + SMA overlays,
  longer history (their current ETF n=15 fails CI).
- Both: benchmark-relative testing, capital adjustment.

## My plan (ordered — pilot first, research second)
1. **Variant C forward pilot (0–4 months) — the only edge the system itself can produce.**
   - Pre-registered rule (already locked, scheduler task `5992b142`, weekly): each month rank
     strategies by trailing PF (n≥20 train trades), take top-6 with PF>1.3, trade next month —
     **no re-tuning, equity/ETF focus** (crypto/forex already auto-excluded by the gate).
   - Sizing ¼ Kelly = 2.5%/trade; worst month ≈ −1.6% bankroll.
   - **Certification = T2 ∧ v3 gates on the forward record** (`_overall.md`); kill criteria:
     two consecutive PF<0.5 months or 3-month rolling PF<1.0.
   - Hardening before month 2 of the pilot: (a) populate `resolution_method`; (b) apply an
     explicit slippage estimate to closed P/L (0.1% equity round-trip) and re-report PF —
     my buffer is 0.416%/trade so PF should survive, but it must be *shown*; (c) cap
     `vwap-reversion-scout` weight (its n=15 PF 3.74 carries 47% of P/L — concentration is
     the pilot's #1 fragility).
2. **v2 research (after data-layer fixes, not before):** finpredict's factor portfolio and
   finpredict-v3's market-neutral construction are the right *second* generation — but as a
   separate research track with its own pre-registration, never mixed with the pilot's ledger.
3. **What NOT to do (my spent false-positive budget):** 46-cell source/strategy search —
   zero survivors; alive-filter refinement — failed (PF 0.80). Do not mine this class further.

**Tradable today: PILOT ONLY** (paper/¼-Kelly, forward record, explicit kill criteria).
This is the single class where I recommend spending live risk, because it is the single class
where a *reproduced, pre-registered* rule already exists on the system's own output.

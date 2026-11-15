# MUTUAL FUNDS — plan to profitability (user's conviction class)

**Verdict: highest-probability path, but as an ALLOCATION engine — not intraday picks.**
NAV priced once daily makes TP/SL picks structurally impossible (peer consensus, which we
adopt). "Winners given enough time" = capturing equity/bond risk premia at low cost, which
works *without* the prediction system. SubQ agrees on the split: active selection beats
index after costs P(yes)=**0.03**; simple rotation beats cash+fees P(yes)=**0.99**
(our caveat: optimistic; keep MDD discipline).

## Path A — deployment sleeve (probability of positive net return over 10y: 60-70%; SubQ skeptical view 55-70%)

1. **Build infrastructure (1-2 weeks):** daily NAV cache; fund metadata (ER, AUM,
   inception); share-class dedup (same portfolio → one entry); **point-in-time universe**
   (SubQ's #1 pick, conf 0.87 — survivorship is the research killer).
2. **Engine (the strategy):** monthly momentum rotation — 12-1 total return across broad
   share classes (US total / intl / EM / short-duration / TIP-class), **absolute-momentum
   filter** (hold only if > 3-month T-bill), top-2 inverse-vol weights, ER ≤ 0.20% screen,
   0.05%/one-way cost, 0.15%/yr fee drag modeled. Spec lives in
   `final_v4/inspect-wt/03_risk_management/backtest_rotation.py` (pre-registered docstring).
3. **Gate (benchmark-relative — the correction):** net Sharpe ≥ 0.7, MDD ≤ 20%, **Calmar ≥
   0.7 AND Calmar ≥ 60/40's Calmar**, within 0.5 Sharpe of SPY while cutting MDD ≥ 30%
   (drawdown reduction is the sleeve's honest selling point — full-cycle CAGR will NOT
   beat SPY: measured 8.2% vs 12.8%, that's the *point* of ballast).
4. **Forward:** paper-trade 3 monthly rebalances, then deploy in tranches (not all at once).
5. **Kill:** sleeve MDD > 20% intracycle, or 3 consecutive months of negative excess vs
   60/40 → fall back to plain 60/40 (the "boring default" still beats cash).

## Path B — active selection (research only; P(beat index after costs) 10-25%)

- Only after Path A exists. Pre-register the null: "active does not beat the index after
  fees" — burden of proof on rejecting it. Test style/sector rotation lag explicitly
  (managers' reported returns embed lag that live NAV trading does not get).
- Candidate edge worth ONE trial: **relative-strength rotation among style boxes
  (value/quality/small/growth) at monthly frequency** — slower than equity crowding,
  fits the NAV clock, and is the one active concept with historical literature support.
- Infrastructure: survivorship-corrected database (e.g., full survivor list incl. merged/
  liquidated funds — using today's list = instant fake alpha).

## Why this is "solid picks" on an honest clock
Monthly recommendations (overweight X, underweight Y, hold cash) with a stated rule set,
published before each rebalance, benchmarked vs 60/40 — a recommendation engine people can
verify. Never a TP/SL pick.

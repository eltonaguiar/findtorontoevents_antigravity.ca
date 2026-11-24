# US vs Canadian wrapper — decision (jurisdiction granted; decided here)

**Date:** 2026-11-24 · **Author:** Kilo · Paper only, not investment advice.
**Question:** for a Canadian retail investor (the audience of findtorontoevents.ca), should the recommended low-cost
index exposure be a **US-listed USD ETF** (SPY/VOO/VTI) or a **Canadian-listed CAD-traded** wrapper (VFV/XUS/ZSP or an
all-in-one like XEQT/VEQT / a Canadian index mutual fund)?

## Decision (the defensible default)
**Use a Canadian-listed, CAD-traded broad index ETF by default** — VFV or XUS for the S&P 500, or XEQT/VEQT for a
one-fund global portfolio — **in TFSA and taxable accounts.** Use a **US-listed ETF (VOO) only inside an RRSP**, and only
with cheap FX conversion (Norbert's gambit).

## Reasoning
1. **FX conversion cost.** A US-listed USD ETF requires converting CAD→USD on every purchase (~1–2% at retail FX, ~0.1%
   via Norbert's gambit). A CAD-traded wrapper needs none — you buy in CAD.
2. **US estate-tax exposure.** Non-residents holding **US-situs securities above ~$60k USD** (US-domiciled ETFs count)
   face potential **US estate tax up to 40%**. Canadian-listed ETFs are **not** US-situs → avoided entirely.
3. **Withholding by account:**
   - **TFSA:** US dividend withholding (15%) is **not recoverable** regardless; the Canadian wrapper doesn't fix that, but
     it avoids the FX cost and the estate-tax issue.
   - **RRSP:** the **US–Canada tax treaty exempts** US dividend withholding inside an RRSP → this is the one place a
     US-listed ETF (VOO, 0.03% fee) is genuinely better, *if* FX is converted cheaply.
4. **Fees are comparable:** VFV/XUS/ZSP ≈ 0.09–0.10% vs SPY 0.0945% (VOO 0.03% is the outlier-low). The fee gap between a
   CAD wrapper and SPY is negligible; the FX and estate-tax differences dominate.
5. **Simplicity:** CAD wrapper = no USD cash management, fractional CAD purchases, one currency to track.

## Consequences for the recommendation
- **Default answer for a Canadian:** a **Canadian-listed CAD-traded low-MER index ETF** (VFV/XUS, or XEQT/VEQT), held long;
  if a −25% drawdown is intolerable, a Canadian 60/40 or a conservative all-in-one (VCNS/VCIP).
- **RRSP optimization:** US-listed **VOO** + Norbert's gambit, keeping total US-situs under the estate-tax threshold.
- **Which mutual fund:** a Canadian-domiciled low-MER index mutual fund (e.g., a bank index fund) is acceptable only when
  minimums/automation make the ETF impractical — the same fee logic as before.

## Caveats (honest)
- This is a **structural/tax/FX** decision, **not measured** on our data (the local `market_prices.csv` holds only US funds;
  no Canadian ETF series). Fees cited are public product MERs.
- Tax rules are jurisdiction-specific and change; **tax is not modelled** here. Verify current CRA/IRS treatment and the
  US estate-tax threshold before acting.
- Not investment advice.

## Jurisdiction note (recorded, per operator grant)
- **Wrapper decision:** decided above — Canadian-listed CAD ETF by default; US-listed only in RRSP with cheap FX.
- **Branch placement:** this decision doc lives on a fresh branch cut from `origin/main`
  (`research/us-vs-cad-wrapper-2026-11-24`) so it is reviewable in isolation and does not carry my long-lived working
  branch's history or any foreign data churn.

# Decision: which jurisdiction does this fund report answer for?

**Date:** 2026-11-24 · **Status:** decided (operator delegated the decision)
**Supersedes:** the "E3–E6 blocked, needs operator" markers in the fund report.

## The question

Plan items E3–E6 asked whether the reader is a Canadian resident using a TFSA/RRSP, a US
taxpayer using a Roth/IRA, or someone in a taxable account. The answer changes the
recommendation, so it could not be left dangling without making the report's conclusion
conditional.

## Decision

**The report answers for a Canadian resident individual.** The US-taxpayer case is kept as a
short appendix rather than a co-equal branch.

## Reasoning

Four arguments, in order of weight.

1. **The report's own hardest constraints only exist for a Canadian.** PFIC treatment, US
   estate-tax exposure on US-situs assets, and TFSA-vs-RRSP dividend withholding are all
   Canadian-specific problems. If the reader were a US taxpayer, Step 0 would collapse to a
   single line — "use a tax-sheltered account and pick the lowest MER" — and roughly half of
   this report would be noise. A document whose most detailed section describes Canadian tax
   friction is answering a Canadian question.

2. **It is the conservative choice.** Deciding "Canadian" imposes more constraints (PFIC
   disqualifies the named funds outright; withholding bites; estate tax looms). Deciding "US
   taxpayer" would assume those away and let the report hand out the easy answer. When the
   persona is unknown, picking the branch that survives the harder constraint set is
   defensible; picking the one that avoids the constraints is not.

3. **The project context points the same way.** This repo and its operator work on
   Toronto-focused products. That is weak evidence about any individual reader, so it is
   ranked third — but it is not zero, and it agrees with the two arguments above rather than
   competing with them.

4. **The funds named in the report are US-domiciled.** A US taxpayer can buy FXAIX, FZROX and
   VTSAX directly; a Canadian cannot, on PFIC grounds. So the report as written is *usable* by
   an American and *inapplicable* to a Canadian — and it is more useful to make it applicable
   to the person most likely to read it than to leave it applicable only to the easier case.

## What this decides, concretely

- **Wrapper ranking for a Canadian resident:** TFSA and RRSP first (tax-free/deferred growth),
  taxable last. Within the two registered accounts the *domicile* decision flips: an RRSP is
  generally exempt from US dividend withholding under the treaty, a TFSA is not.
- **The named US-domiciled funds are ruled out** for a Canadian holder — PFIC, not preference.
  The transferable conclusion is the method (low cost, broad index, deliberate currency), not
  the ticker.
- **Currency is the first-order decision**, not the vehicle. Measured at ~2.9pp/yr in
  `reports/fund_cad_view.json` against a 0.0795pp fee edge.
- **Withholding is second-order but still larger than the fee question:** 0.150–0.369 pp/yr on
  the equity sleeve (`reports/fund_withholding.json`), i.e. 1.9x–4.6x the fee edge. Bond and
  T-bill distributions are mostly portfolio interest and generally not withheld, so a single
  blended withholding number for a 60/40 would be wrong.

## What this does *not* decide

- **Which registered account the reader actually has room in.** Not inferable. The report
  gives both.
- **Whether to hedge.** Becomes a stated choice with measured consequences, not a modelled
  recommendation — hedging cost is an assumed parameter, not a forward curve.
- **Any tax figure is verified.** The withholding rates used are the statutory 30% and the
  Canada–US treaty rate of 15%; the *applicability* to a given account is flagged unverified
  and the report says so twice.

## Consequences if wrong

If the reader is a US taxpayer, the practical answer degrades to: use a tax-sheltered account,
prefer FZROX/FXAIX on cost, ignore the withholding and PFIC sections. That is a *shorter*
answer, not a wrong one — the appendix states it. No conclusion in the report reverses; the
Canadian branch is strictly more constrained than the US one, so it does not fit a Canadian
answer onto an American reader.

The failure mode to avoid is the opposite: presenting the US-domiciled funds as a
recommendation to a Canadian reader who cannot legally hold them. That is why the decision is
written down rather than left to the reader.

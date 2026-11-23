# Plan for the next batch (todos #99)

**Date:** 2026-11-23T10:40Z · **Author:** Kilo.

## Where we are
Independent analysis is saturated and self-corrected: 0 investable; alpha gate sound but power-limited; F4 retracted;
fund/FAQ published with measured, CI-honest numbers. Remaining work is (a) peer-review round-trip, (b) data-gated research,
(c) hardening.

## Next batch (priority order)
1. **Peer-review round-trip (highest):** collect reviews of the F4 retraction + FAQ v2; fix anything they find; return my
   two findings on `f4_vehicle_noise.py` (excess Sharpe, add CIs).
2. **Data-gated research (needs inputs):** international diversification, factor tilts, TIPS/REITs, real returns, bond
   forward YTM, equity earnings yield. Each is blocked on a specific series; spec them and mark BLOCKED.
3. **Multi-AI panel check:** run the FAQ's key numbers through a multi-model panel (like the operator's ask4ais) to catch
   remaining errors before the human relies on them.
4. **Harden:** wire a "no-overclaim" lint + unit-consistency test into CI; add the new tools to `audit-surface-gates.yml`.
5. **Contest:** if Q1–Q3 answered / R02 opens, finalise entry; else keep it staged.
6. **Close-out:** refresh STATE_OF_PROGRAMME, artefact index, MEMORY.

## Definition of done for the batch
- Every FAQ number has either a CI or an explicit "point estimate, n=X" label.
- Every data-gated item is either run or marked BLOCKED with the missing input named.
- No residual overclaim (CI lint passes).
- Peer reviews received/adjudicated.

# 05 COMMODITY — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block, including the H-101 COT look-ahead incident, + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF net 0.1505 `[SRC: docs/audit_review_2026-11-22/05_COMMODITY.md:39]`

## cloudflare
Names **n 50**, same template.
**Assessment:** weak. The dossier's own point is that n 50 exceeds required_n 24, so n is not what makes the result fragile; the denominator of the PF is.

## deepinfra
Names **PF net 0.1505** and agrees with the dossier. "The COT publication-lag look-ahead incident (H-101) suggests that the number may be contaminated, making it fragile."
**Assessment:** the best use of the leakage context in either response set. It correctly notes that a COMMODITY PF may be contaminated by the H-101 look-ahead. The dossier should absorb this: it currently mentions denylisted picks but not H-101 by name.

## Curator verdict
deepinfra raised a real point (H-101 contamination on a COMMODITY PF). It does not change the KILL verdict, which is driven by a gross expectancy of −2.81 pct, but it belongs in the dossier's data-integrity section.

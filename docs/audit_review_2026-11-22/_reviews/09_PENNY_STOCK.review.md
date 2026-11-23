# 09 PENNY_STOCK — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF 0.1779 `[SRC: docs/audit_review_2026-11-22/09_PENNY_STOCK.md:34]`

## cloudflare
Names **n 4**, same template.
**Assessment:** at n 4 it is fair to say nothing survives, but the answer is not specific to this class.

## deepinfra
Names **PF 0.1779** and agrees with the dossier. Cites the small sample.
**Assessment:** correct conclusion, thin reasoning. It did not note the missing DSR baseline or `intrabar_truth: null`, both of which are in the dossier.

## Curator verdict
Agreement. The dossier's choice is right: on four trades the PF is the number that one trade flips.

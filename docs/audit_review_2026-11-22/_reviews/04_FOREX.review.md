# 04 FOREX — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF net 0.8496 `[SRC: docs/audit_review_2026-11-22/04_FOREX.md:40]`

## cloudflare
Names **n 264**, same template.
**Assessment:** here it is closer to right than in other classes, because the dossier itself says the ledger prices only 264 of 468 rows. But it names n without connecting it to the unjoined rows, which is the actual fragility.

## deepinfra
Names **PF net 0.8496** and agrees with the dossier. Cites the WEAK label as evidence of small sample.
**Assessment:** circular (the label is derived from the same numbers). It did not raise the 204 unpriceable rows, which is the class's central correctness gap.

## Curator verdict
Neither reviewer identified the real issue: the PF is computed on a subset and the excluded rows are unknown-quality. The dossier's choice is fine; the reviews add nothing to it.

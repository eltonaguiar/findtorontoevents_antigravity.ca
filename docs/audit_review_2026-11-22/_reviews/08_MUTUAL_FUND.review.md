# 08 MUTUAL_FUND — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
n 0 `[SRC: docs/audit_review_2026-11-22/08_MUTUAL_FUND.md:36]`

## cloudflare
Names **n 0**, same template.
**Assessment:** degenerate but correct: the only number in the class is zero.

## deepinfra
Names **n 0** and agrees with the dossier.
**Assessment:** same.

## Curator verdict
Both agree, and there is nothing else to say: a placeholder with zero rows has exactly one number, and the first ingested pick falsifies it.

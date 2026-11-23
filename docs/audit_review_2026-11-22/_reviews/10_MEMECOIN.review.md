# 10 MEMECOIN — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF 0.0234 `[SRC: docs/audit_review_2026-11-22/10_MEMECOIN.md:32]`

## cloudflare
Names **n 10**, same template.
**Assessment:** weak, and it misses the concentration cap (one symbol at 40 pct), which is what actually makes n 10 uninformative.

## deepinfra
Names **PF 0.0234** and agrees with the dossier. Notes the 40 pct single-symbol share.
**Assessment:** agrees with the dossier and cites the concentration, which is the right supporting fact.

## Curator verdict
Agreement. No new criticism; the class is unmeasured on the ghost-row question in both the dossier and the reviews.

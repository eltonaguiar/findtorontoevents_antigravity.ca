# 03 ETF — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF net 0.9947 `[SRC: docs/audit_review_2026-11-22/03_ETF.md:36]`

## cloudflare
Names **n 590**, same template as every other class.
**Assessment:** weak. n 590 is not the fragile part; the fragile part is that the net expectancy (−0.0062 pct) is the difference of two nearly equal numbers, gross 0.0449 pct and cost 0.0511 pct.

## deepinfra
Names **PF net 0.9947** and agrees with the dossier. "The cost of 0.0511 pct > gross 0.0449 pct suggests that the slippage is not measured, making the number fragile."
**Assessment:** this is the one genuinely useful observation in either response set: it ties the fragility to the unmeasured slippage constant rather than to n. It matches the dossier's own reasoning.

## Curator verdict
Agreement, no new criticism. Both the dossier and deepinfra rest on the same fact: the flat cost constant is 114 pct of gross, and it is not measured for ETFs.

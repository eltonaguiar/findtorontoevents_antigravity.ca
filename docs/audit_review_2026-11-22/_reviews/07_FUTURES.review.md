# 07 FUTURES — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF net 1.8719 `[SRC: docs/audit_review_2026-11-22/07_FUTURES.md:34]`

## cloudflare
Names **n 4**, same template.
**Assessment:** trivially correct in the sense that at n 4 nothing survives, but it is not a discriminating answer: it says the same thing about n 6926.

## deepinfra
Names **PF net 1.8719** and agrees with the dossier. "The DSR (null) suggests that the slippage is not measured."
**Assessment:** the conclusion is right but the stated reason is wrong: a null DSR follows from n 4 having no variance estimate, not from unmeasured slippage. Still, it lands on the right number.

## Curator verdict
Agreement. The honest summary for this class is that at n 4 no number survives; the dossier says the same. Neither review adds to it.

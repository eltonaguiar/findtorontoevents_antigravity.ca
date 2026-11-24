# 02 EQUITY — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF net 1.0499 `[SRC: docs/audit_review_2026-11-22/02_EQUITY.md:39]`

## cloudflare
Names **n 956** as least survivable, with the same template as every other class ("foundation of the PF net calculation").
**Assessment:** weak, and it misses the real issue: the split halves disagree in sign (first +0.7663, second −0.5546), which is a property of the PF, not of n.

## deepinfra
Names **PF net 1.0499** and agrees with the dossier. Adds that "the confidence interval (CI) straddling zero suggests that the sample size is small, making the number fragile."
**Assessment:** the reasoning is partially wrong (n 956 is not small; the CI is wide because the per-trade edge is tiny and high-variance), but the conclusion matches the dossier. It did not mention the sign-flipping split halves, which is the strongest argument.

## Curator verdict
No independent criticism was produced. The dossier's choice is defensible on its own stated ground (split-half sign flip), which neither reviewer cited.

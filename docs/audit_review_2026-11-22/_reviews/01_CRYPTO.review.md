# 01 CRYPTO — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block (H-101 COT look-ahead, negative selection alpha, 59.19 pct scored share, flat cost constant, `/tmp` provenance, sticky PROMOTED) + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
PF net 0.7886 `[SRC: docs/audit_review_2026-11-22/01_CRYPTO.md:43]`

## cloudflare
Names **n 6926** as least survivable: "the number of trades is the foundation of the PF net calculation, and if this number is wrong, the entire PF net calculation is invalid."
Second question: agrees with its own choice (does not speak to the dossier's).
**Assessment:** weak. n is a count of closed rows, not a statistic; it is the most directly checkable number in the dossier, not the most fragile. The templated answer repeated n for all 10 non-empty classes.

## deepinfra
Names **PF net 0.7886** and agrees with the dossier. "The PF net number is the least survivable because it's a key metric that determines the overall performance of the class."
**Assessment:** agrees but adds no reasoning beyond restating the dossier. It did not apply the leakage context to this class.

## Curator verdict
The two reviewers did not independently converge on a criticism: one defaulted to n, the other echoed the dossier. The dossier's own choice stands on its stated reason (mixed symbol cells, different cost models, verdict_churn flipping CRYPTO cells WEAK to KILL in one run). Treat this review as a weak signal only.

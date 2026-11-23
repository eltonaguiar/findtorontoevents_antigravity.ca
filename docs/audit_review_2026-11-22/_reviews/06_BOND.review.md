# 06 BOND — adversarial review

**Reviewers:** `cloudflare/@cf/meta/llama-3.1-8b-instruct`, `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct`
**Contract:** name the least-survivable number and why. Neither reviewer drafted the dossier (`model: none`).
**Prompt:** LEAKAGE CONTEXT block + the 12 class summaries. Raw responses: `/tmp/zoo_adv_2026-11-22/` (not committed).

## Dossier's named number
WR 43.24 pct at n 37 `[SRC: docs/audit_review_2026-11-22/06_BOND.md:36]`

## cloudflare
Names **n 37**, same template.
**Assessment:** weak. It does not mention the intrabar-versus-daily WR divergence, which is the one number in this class that actually matters.

## deepinfra
Names **WR 43.24 pct** and agrees with the dossier. Cites the 7.69 pct intrabar WR on n 26 against the 100 pct daily WR on n 2.
**Assessment:** this is the only response that engaged with the substance: two win rates on overlapping populations that disagree by 35 points means one of them will not survive. It agrees with the dossier for the dossier's reason.

## Curator verdict
Agreement with correct reasoning from deepinfra. The dossier's choice is the right one: the WR is the number that cannot survive, not n and not the PF (which is not even defined on the n 2 daily sample).

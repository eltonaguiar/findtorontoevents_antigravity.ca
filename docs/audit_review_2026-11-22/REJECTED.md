# Rejected drafts, 2026-11-22

Nothing is silently dropped. This records delegated drafts that failed the lint or the adversarial
pass and were not published, with the reason.

## R1. All twelve delegated drafts: not produced (fan-out blocked)

[SRC: manifest:entries] The `diverse5` fan-out needs five providers; `--doctor` showed only cloudflare
answering, so no peer could draft a dossier. See BLOCKERS.md B1 for the per-provider status.

Disposition: the curator wrote all twelve dossiers from frozen evidence instead. Each provenance
footer says `model: none`. None of them claims an AI drafter.

## R2. Adversarial reviews: not produced (fan-out blocked)

The mandatory two-model adversarial pass uses `reasoning4` (nvidia, gemini, together, fireworks),
of which zero answered. No dossier received an independent AI review.

Disposition: the "least survivable number" question is answered by the curator in each dossier,
but that is not the independent check the program requires. This is an open gap, not a pass.

## R3. Early dossier drafts that failed the lint

The first drafts put one marker at the top of a paragraph and several numbers after it. The lint
(per-section region rule) rejected them, and they were rewritten so each numeric line carries its
marker. They were not published in the failing form.

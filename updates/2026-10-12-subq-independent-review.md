# SubQ independent experiment and article

## What was missing

The exploratory SubQ runs lacked an explicit assistant baseline, a semantic
reference set, a direct local-model comparison and a public explanation of the
model's practical limitations. Numeric fixture success alone did not establish
semantic reliability or forecasting ability.

## Changes

- Recorded assistant candidate and asset-class research ratings before eight
  new comparative inference calls, with reference-file fingerprints in the
  ledger. The assistant had seen previous answers; this is not fully blind.
- Compared three rating variants, three semantic-classification variants,
  reason codes and directional forward-class ratings.
- Created [the HTML article](./2026-10-12-subq-independent-review.html) and
  [a public evidence bundle](./2026-10-12-subq-independent-review-evidence.json).
- Added a linked card immediately before the pinned incidents/enhancements
  marker in [the updates index](./index.html), preserving existing local edits.
- Kept private read-only DB diagnostics and credentials out of public files.

## Findings

The new comparison used eight successful SubQ inference calls, 35,420 input
tokens and 113 questions. The full investigation used 20 inference calls,
159,430 tokens and 328 questions. At published input pricing, estimated total
token cost is $0.0079715, not a verified billing debit.

SubQ matched 22/24, 23/24 and 23/24 authored semantic labels; local Qwen matched
19/24. These are small, repeated, authored cases, not independent forecasting
evidence. In two variants SubQ incorrectly supported the inference that missing
Commodity rows imply zero trades. Our own reasoning already identified that
contract limitation. No profitable strategy, sizing or execution gate was added.

## Verification and deployment

The validation checks the complete inference ledger, probability schemas,
unchanged reference fingerprints, public bundle totals, reference-case counts,
HTML structure and local links, preservation of all pre-existing index bytes
outside the new card, and absence of resolved credentials in public artifacts.
Browser checks cover readable tables, keyboard navigation, mobile overflow and
the evidence download.

Verified results:

- Eight new inference responses schema-validated; reference fingerprints and
  pre-registration file timestamps checked against first-call time.
- Complete totals: 20 inference calls, 159,430 input tokens, 328 answers.
- HTML parser: balanced tags, one H1, unique IDs, valid internal/local links.
- Live browser: skip link receives keyboard focus; five tables scroll inside
  wrappers with no document-level horizontal overflow at desktop/mobile sizes.
- Browser fetch of evidence JSON: HTTP 200 with exact expected totals.
- FTPS uploads retrieved and compared byte-for-byte.
- HTTPS article compared byte-for-byte with source; live index with our card
  removed exactly reproduces pre-publication production bytes.

Live and local indexes differed before this task. Publishing the entire dirty
local index would overwrite production-only content and deploy unrelated edits.
The deployment therefore uses the existing FTPS configuration but uploads a
staged copy of the current live index with only the same new card inserted,
alongside the article and evidence JSON. This deliberately avoids modifying or
running the already-dirty uploader script against the whole local index.
The live index is retrieved through FTPS immediately before insertion and checked
again before replacement. Pre-publication copies remain in the session workspace.
Post-upload verification requires HTTP 200, the article title and exact totals,
the new link before the auto marker, and the complete public JSON token count.

No unrelated changes are staged, committed, pushed or deployed. This article
and card should be merged as a targeted change rather than committing the whole
shared dirty working tree.

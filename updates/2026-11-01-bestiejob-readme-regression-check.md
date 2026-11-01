# bestiejob — README regression check (2026-11-01)

Verify that the restores after the two truncations were complete. Method: extract every `|`-table row
containing ServiceNow or Salesforce from **all 24 historical README blobs** on `main`, diff against
HEAD, then classify each apparent loss.

## Result

**One genuine loss found and restored.** Two apparent losses were artefacts of the extraction filter.

| Row | Verdict | Detail |
|---|---|---|
| Cognizant **Salesforce Business Analyst 00070950941**, Toronto hybrid, 3 office days, CAD 65–95k, **accepting until 2026-11-15** | **Genuinely lost** | Present at `bf3fdb4`, absent from every later commit including both restores. Added by `bf3fdb4` immediately before the truncating `8c25626`, so the first restore pass (which replayed the pre-truncation state) missed it. Restored in `f9fe1ff`-range commit. |
| CAAT Pension Plan **ITSM Analyst `JR100183`** | False positive | Present at HEAD. The row text never contains the string "ServiceNow", so the keyword filter skipped it at HEAD while catching it at `bf3fdb4` (where a duplicate row did name the platform). |
| The other 37 "orphan rows" | False positive | Every company is present at HEAD (GTT, Artech, Epsilon, Macpower, ICONMA, White Bay, Hire DigITalent, Diverse Lynx, IBM Canada, NewRocket, Optovia, Maarut, Panasonic, Jobgether, BULL-IT, Tamanna, S.I. Systems, Galent, Canadian Cancer Society, Orion, Q1, Chapman Tate, Alldus, National Bank). Commit `7721e89` added a `Posted` column, which shifted cell positions and made the crude title/company parser derive different keys for the same row. |

Table integrity at HEAD: `### Posted 2026-10-31` holds **28 postings**, `### Posted 2026-10-30` holds
**12** — both intact.

## Stale-copy issue (resolved)

`raw.githubusercontent.com/eltonaguiar/bestiejob/main/README.md` served a 618-line pre-push copy for
~15 minutes after the push, while the commit-SHA URL was already correct. Cause: CDN edge cache lag,
not a bad write — and the repo has since been **renamed to `eltonaguiar/BESTIEJOB`**, so the lowercase
path is a cached alias.

Verified 2026-11-01: all four combinations (old/new repo name × branch/SHA) now return the same
688-line file with the new sections. No action needed; do not "fix" it by re-pushing.

## Known limit of this check

The row extraction only collected rows mentioning ServiceNow or Salesforce. Every posting in this
repo is one of those two platforms, so coverage is complete in practice — but a row that named
neither (e.g. a generic "CRM Developer") would be invisible to the diff.

Branch-only content is covered separately in `2026-11-01-bestiejob-unmerged-branch-gap.md`.

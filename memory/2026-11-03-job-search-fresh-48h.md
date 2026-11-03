# Job search — fresh 48h scan (2026-11-03 ~18:30Z)

## What happened

Ran a today/yesterday sweep at Elton's request. 26 queries × 3 pages, `f_TPR=r172800`.

**731 raw → 172 net-new** (107 today, 61 yesterday). SN 11 / SF 38 / adjacent 123. GTA 105.
Buckets: apply 81 / consider 76 / skip 15.

## Findings worth remembering

- **GTA ServiceNow supply is genuinely thin.** One GTA ServiceNow role in 48h (Poly Tech
  Talent — ITSM Service Desk Manager, score 8). Volume is Montreal: Pomerleau (×5 variants),
  TCS (Specialist + CMDB), AceStack (CMDB/CSDM onsite).
- **Adjacent ITSM is the stronger channel than ServiceNow-titled roles.** Interac Incident
  Management Lead (8), UHN Incident Coordinator (7), TEKsystems Controls Transformation (8),
  Deloitte Manager Data Analysis (8). The ITIL v4 + ITSM depth carries these.
- **Salesforce GTA is healthy.** Co-operators bilingual Systems Developer (8), IKO (7),
  Canadian Cancer Society Senior SF Engineer (×4 regional variants, 6), Smart IT Frame SFMC ×2.
- **~20% of fresh roles are bilingual.** Co-operators, Cancer Society, Alithya, Desjardins,
  Pomerleau, Schneider, Bell. Resume is not bilingual → −2 each, but cert/module overlap still
  pulled several into apply tier.
- **Requisition duplication is heavy.** Pomerleau ×5, Cancer Society ×4, Salesforce ×3.
  Apply once per requisition. URL-dedupe does not catch regional variants.

## Mistake I made (documented so future-me doesn't repeat)

My aggregator used a bare `except Exception: continue` while loading prior corpora. The 684-job
files were on branch `job-search-2026-11-03-rounds21-27`, not the checked-out branch, so the
load silently failed and fell back to the 259-URL file — producing **197 net-new** instead of
the true **172**.

What caught it: I printed `Prior known URLs: 259` and knew 684 was expected. That one
diagnostic line was the entire detection mechanism.

**Rules adopted into the skill:**
1. No bare `except: continue` in data loaders — catch `FileNotFoundError` explicitly.
2. Always print the loaded prior count and compare against expectation.
3. Priors may live on another branch — use `git show <branch>:<path>`.
4. Never overwrite a good artifact with a suspect one; timestamp and set the bad one aside.

## Git

Push was rejected twice by repository rules (secret-scanning on a pre-existing commit
`faad94a9c0e` containing an OpenRouter key in `tools/ai_second_opinion.py:42,58` — **not my
commit**). Resolved by branching from the known-clean remote commit `7ed21345a97` and
committing only my four files. Pushed as `job-search-2026-11-03-fresh-48h` (`43e66e2f678`).

Also hit a self-inflicted one: `git checkout -b <new> 7ed21345a97` removed my untracked-but-
committed-in-43e6... files from the working tree mid-sequence. Recovered with
`git checkout 261c0231df4 -- <paths>`. Lesson: when re-branching mid-flight, `git show`-dump
or stash artifacts to `/tmp` first rather than trusting the working tree.

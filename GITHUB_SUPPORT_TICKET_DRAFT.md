# GitHub Support Ticket Draft — Large History Rewrite Push Failure (HTTP 500)

**Repository:** eltonaguiar / findtorontoevents_antigravity.ca  
**Date:** 2026-05-23  
**Priority:** High (production git history migration blocked)  
**Request Type:** Repository data migration / large force-push assistance

---

## Subject Line (recommended)

Force push of 16 GiB rewritten git history fails with HTTP 500 on receive-pack — request server-side import or bundle ingestion

---

## Ticket Body

### Summary

I successfully performed a targeted git history rewrite on `eltonaguiar/findtorontoevents_antigravity.ca` to remove two very large, repeatedly-committed JSON payload files that were causing ~18 GiB of bloat.

- `audit_dashboard/data/dashboard_data.json` (1,139 historical revisions removed)
- `audit_trail/data/dashboard_payload.json` (2,191 historical revisions removed)

The local rewrite using `git-filter-repo --invert-paths` completed successfully and passed all verification (`git fsck --full --strict` clean, zero remaining revisions for the removed paths across `--all`, recent commits intact).

I hold a complete `git clone --mirror` backup as the rollback source of truth.

**Problem:** Every attempt to push the rewritten history back to GitHub fails with HTTP 500 from `git-receive-pack` after ~60–90 seconds while sending a ~16 GiB pack. This occurs on both the original repository and even on a brand-new empty repository I created for staging.

I am the repository owner and am authenticated via the GitHub CLI.

### Evidence from Latest Failed Push (2026-05-23 06:00–06:02 UTC)

Fresh trace with `GIT_TRACE=1 GIT_CURL_VERBOSE=1`:

- Capability negotiation packet: HTTP 200 OK  
  Request ID: `9B0A:1C57C:3BA2D8:4A9CF9:6A114298`

- Large pack transmission: After ~78 seconds of sending, GitHub returns:  
  `HTTP/2 500`  
  Request ID: `9B0A:1C57C:3BA385:4A9DE0:6A114299`

Error: `error: RPC failed; HTTP 500 curl 22 The requested URL returned error: 500`

This is the same failure mode observed on multiple prior attempts (different Request IDs available on request).

### What I Have Locally (Ready to Provide)

1. Full mirror backup of the original (pre-rewrite) history:  
   `/home/eaguiar2015/fte-mirror-backup-2026-05-23.git` (17 GiB)

2. Fully rewritten clean clone with the large JSON files purged from the entire DAG:  
   `/home/eaguiar2015/repo-clean`

3. A `git bundle` of the cleaned history (I can generate and upload immediately upon request).

4. A freshly created empty staging repository:  
   `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca-clean`

### Requested Assistance

Please help me complete the migration of the cleaned history. Preferred options (in order):

1. **Server-side ingestion of the rewritten pack / bundle** into either:
   - The existing repository `eltonaguiar/findtorontoevents_antigravity.ca`, or
   - The staging repository `eltonaguiar/findtorontoevents_antigravity.ca-clean` (then I can rename/swap on GitHub).

2. Any internal GitHub tooling or support procedure for large history rewrites that bypass the public `git-receive-pack` timeout limits.

3. Guidance on the safest rename / transfer sequence once the clean history is on GitHub.

I am happy to:
- Upload the bundle file via any secure method you provide
- Grant temporary collaborator access or provide SSH access for an engineer
- Run any verification commands you need on the local side

### Rollback Plan (Already in Place)

The full original mirror backup exists and can be force-pushed to restore the pre-rewrite state at any time if needed.

---

## Attachments / Data I Can Provide Immediately

- Latest full `GIT_TRACE` log from the failed push (contains the two Request IDs above)
- Output of `git fsck --full --strict` and `git log --all --oneline -- <removed-path>` (showing 0 revisions)
- Size and pack listing from the clean clone
- The `git bundle` file itself (upon secure upload instructions)

---

## Contact

I am available for immediate follow-up. This is blocking further work on the repository.

Thank you for your assistance.

---

**End of draft**

Copy the subject + body above into https://support.github.com/ (or the internal enterprise support portal if applicable). Include the two latest Request IDs prominently.

After submitting, paste the ticket number here so we can reference it in future swarm updates or follow-ups.
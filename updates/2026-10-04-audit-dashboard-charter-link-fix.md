# /audit dashboard: dead `PERFORMANCE_CHARTER.md` link repointed to GitHub

**Date:** 2026-10-04
**Found in:** site + `/audit` health audit (`reports/SITE_AND_CI_HEALTH_2026-10-04.md`)

## What was broken

The `/audit` dashboard's **TIER-2 PROVEN** hero section rendered an anchor to the
Performance Charter:

```html
Tier badges per <a href="/docs/PERFORMANCE_CHARTER.md">CHARTER &sect;2</a>.
```

That link 404s on **every** mirror because the live host (50webs) never receives
the repo's `docs/` tree — `tools/deploy_audit_files.py` uploads audit artifacts
and the updates index, but no `docs/*` files. Verified live:

```
404  https://findtorontoevents.ca/docs/PERFORMANCE_CHARTER.md
404  https://findtorontoevents.ca/docs/SMARTPICKS.MD
404  https://findtorontoevents.ca/docs/ai_feedback_summary.html
```

The document itself exists in-repo (`docs/PERFORMANCE_CHARTER.md`).

## What changed

Repointed the link to the GitHub blob URL, matching the convention already used
throughout the repo (e.g. `tools/_insert_audit_review_index.py` and the doc links
in `audit_dashboard/incidents.html`):

- `audit_dashboard/template.html` (source for the generated `/audit/index.html`)
- `audit_dashboard/index.html` (the committed generated artifact)

```html
Tier badges per <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/docs/PERFORMANCE_CHARTER.md"
  target="_blank" rel="noopener">CHARTER &sect;2</a>.
```

The GitHub blob URL was verified reachable (`200`), as was the raw URL.

## Verification

- `grep -rn 'href="/docs/' audit_dashboard/*.html` → no remaining matches.
- `curl -sIL .../blob/main/docs/PERFORMANCE_CHARTER.md` → `200`.

## Known remaining (not fixed here)

`audit_dashboard/incidents.html` and `audit_dashboard/real_money.html` also embed
`[CHARTER §2](/docs/PERFORMANCE_CHARTER.md)` inside **rendered markdown** blobs
(the incidents enhancement-plan feeds). Those are the same class of dead link but
live inside large JSON/markdown payloads; they should be repointed when their
feed generator is next touched. The systemic root cause — `/docs/` never being
deployed — is documented above so a future deploy change can fix all of them at
once.

# Retire the orphaned v2 page (2026-11-19)

**Scope:** `audit_dashboard/v2/index.html`.

## Why

`audit_dashboard/v2/index.html` was a 46 KB page frozen in May 2026. It is not in
any deploy list (verified: no reference in `.github/workflows/*` or
`tools/deploy_audit_files.py`), so it is not live — but it is still committed and
its numbers **contradict** the live kill tribunal (the old page showed CRYPTO as
profitable; audit3 has CRYPTO as a KILL class). Anyone who opens it as a reference
gets the wrong answer.

## What

Replaced the file with a small redirect stub:

- `<meta http-equiv="refresh" content="2; url=/audit3/">`
- `<link rel="canonical" href="/audit3/">`
- links to `/audit3/` (kill tribunal) and `/audit2/` (candidate & methodology).

No deploy entry was added, so the stub does not publish itself; it only ensures
that if the path is ever served or opened, it forwards to the current surface
instead of showing stale numbers.

## Verification

- `audit_dashboard/v2/index.html` no longer contains market statistics.
- `grep -r "audit_dashboard/v2" .github/workflows tools/deploy_audit_files.py`
  returns nothing (unchanged: the page is still not deployed).
- Live surfaces unaffected: `/audit3/` and `/audit2/` are served from
  `audit_dashboard/audit3.html` and `audit_dashboard/audit2.html`.

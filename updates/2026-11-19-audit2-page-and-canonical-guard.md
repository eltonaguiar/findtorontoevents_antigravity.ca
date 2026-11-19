# audit2 page + canonical-view guard (2026-11-19)

**Author:** Kilo (worktree `universal-pisces`)
**Scope:** `audit_dashboard/audit2.html` (new), `audit_dashboard/audit2.js` (new),
`.github/workflows/audit3-ledger.yml`.

## 1. audit2 — candidate & methodology library

`/audit2` was a 404. This adds the surface the review's consolidated spec
(`11_AUDIT2_SPEC_CONSOLIDATED.md`) calls for: the **positive** side of the
kill tribunal.

Files:
- `audit_dashboard/audit2.html` — markup + styles (single file, no build step).
- `audit_dashboard/audit2.js` — data + rendering.

Sections: doctrine banner (collapsible quotes); live verdict table from
`audit3_ledger.json` (class, verdict, n, net expectancy, net CI, 2×-cost OK,
DSR, `required_n`) with the coverage denominator; candidate/observe pod
registry (static snapshot, clearly dated, because `reports/` is not
web-served); measures library; traps/graveyard; retired-with-reason;
provenance & freshness (warns if the source path is a `/tmp` build path).

Rules honoured: no hardcoded live win rates/PF; every live number comes from
the fetched ledger; a missing ledger renders an honest unavailable message,
never a fabricated table. The ledger is looked up in four candidate paths
(`/audit2/`, `/audit3/`, `/audit/data/`, `/audit2/data/`) so it works wherever
it is deployed.

Verification: `html.parser` parses the page; `node --check audit2.js` passes.

## 2. Canonical-view guard (E2 hardening)

The ledger was scoring the 3,500-row export slice (21.4%) whenever the
canonical sidecar fetch failed, silently. The live payload now carries a
`resolved_closed_picks_net` block, so a failed sidecar fetch is a real defect.

`audit3-ledger.yml` now fails the run when the payload declares a canonical
view (`rows_file` present) but the sidecar was not fetched — instead of
publishing a 21.4% ledger. A legacy payload with no block still scores the
slice with a warning.

Verified: the canonical path scores 8,735 rows (53.5%) and the slice's only
CANDIDATE is refuted on the full book — see
`updates/2026-11-19-audit3-canonical-fullbook-verification.md`.

## Not done

- Deploying `/audit2` (needs the FTP deploy list to include it).
- Wiring the page's pod registry to a live `reports/` feed (static by design).

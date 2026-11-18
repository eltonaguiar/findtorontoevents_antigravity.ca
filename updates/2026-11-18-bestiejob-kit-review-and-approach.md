# BESTIEJOB "kit" review — scan_boards.py · render_board.py · AGENT-RUNBOOK (2).md

**Reviewer:** kilo · seat `inbox/gx10-c9b9/bestiejobharvest-v2/kilo`
**Date:** 2026-11-18 · files on `eltonaguiar/BESTIEJOB@main`
**Verdict:** Useful and directly strengthens the job-hunt methodology. Adopt the discovery engine + governance layer; fix the missing data files; resolve the LinkedIn/Adzuna rights question before scaling redistribution.

---

## What these files are

A **read-only, ethics-first discovery + curated-snapshot kit** that is complementary to (and more conservative than) the automated BESTIEJOB pipeline I reviewed earlier.

- **`scan_boards.py`** — offline-by-default lead staging for four *documented* ATS APIs (Lever, Greenhouse, Ashby, SmartRecruiters). No network unless `--read`; endpoints built from an adapter allowlist (never scraped URLs); `NoRedirect` handler; 20 MB payload cap; bounded pages/details/delay; per-host stop on 401/403/429 with `Retry-After` respect. Emits `status='lead_only'` JSONL — explicitly **not** a verified board. Honest date semantics: Greenhouse `updated_at` labeled "NOT posted", Ashby `publishedAt` = "LAST published", SmartRecruiters `releasedDate`.
- **`render_board.py`** — offline `board.html` generator from a reviewed `job-snapshot.csv`. 3 tracks (ServiceNow / Salesforce / Other) × 3 geo buckets (Remote-from-Ontario / Toronto / Global-confirm-Ontario). Evidence-first cards (access level, date source, posting ID, apply vs corroborating links). Honesty guards: refuses mixed `checked_local_date`, refuses duplicate `(publisher,posting_id)`, "Form reached ≠ applied", "dated research snapshot, not a live feed", recheck-before-apply. Accessible (focus-visible, `aria-live` tally, print CSS, `lang=en-CA`, `rel=noopener`).
- **`AGENT-RUNBOOK (2).md`** — the methodology: employer-first sourcing, a per-source **rights/ethics policy**, an ATS-reading guide, title-expansion queries, verification discipline, a dedupe **identity order**, BestieJob integration steps, and a 7-day measurement pilot.

---

## What's useful (mapped to my 4-angle batched methodology)

| Kit asset | Value to the methodology |
|---|---|
| `scan_boards.py` + watchlist | A ready **Batch A (company portals)** engine with a documented ATS allowlist — the highest-signal angle, already coded. |
| Per-source rights labels (`manual_discovery` / `permitted_api_private` / `own_site_attributed` / `redistribution_approved` / `unknown→don't redistribute`) | A **governance layer** my design lacked. Directly governs what may be published to a public board. |
| "Two clocks" (still-listed vs newly-posted; fresh feed uses issuer date in an explicit window) | Reinforces the freshness gate; separates liveness from recency. |
| Liveness taxonomy (`form_reached` / `apply_shown` / `gated_route` / `listed` / `needs_review` / `closed`) | Richer than the pipeline's 404/410/451 gate — distinguishes "listed" from "form actually reachable". |
| Dedupe identity order: `(ATS, tenant, posting_id)` → employer req + country → normalized canonical URL → *review* similar title+company+area | A **stronger primary key** than `title\|company\|city`; prevents false merges (e.g. Versapay CA vs US reqs). |
| Verified, dated 2026 partner/conference URLs (ServiceNow World Forum Toronto 2026 + sponsor showcase; Salesforce World Tour Toronto May 2026 + sponsor catalog; Partner Finder; AppExchange Consulting) | **De-risks Batch D** and resolves several of my earlier `<uncertain>` source tags with concrete, citable links. |
| 7-day pilot (incremental yield, verification quality, freshness lag, cost; **exclusive vs shared** finds) | A method to **empirically rank** the four angles instead of by judgment — and to stop the first adapter taking all the credit. |

---

## Gaps / risks

1. **Kit is not runnable as committed.** `employer-watchlist.csv` and `job-snapshot.csv` return **HTTP 404** on both `main` and the pinned revision `7851e00` (the scripts read them from repo root via `HOME = script parent`). The runbook's "extracted kit directory" is evidently a local artifact. **Action: commit the data files (runbook cites 23 watchlist entries) and pin the kit to a revision.**
2. **Rights conflict with the live pipeline.** The current BESTIEJOB automation uses the **LinkedIn guest API** and **Adzuna**; the runbook explicitly flags LinkedIn (bars scraping/unauthorized automation) and Adzuna (attribution + linked label + licence for commercial/redistribution use). A public board is *redistribution*. **Highest-priority governance action: label every source's rights and gate publishing on them (`unknown → hold`).**
3. **Conservative kit vs aggressive pipeline.** The kit forbids auto-apply, credentials, and republication of restricted text; the pipeline auto-merges and publishes. Keep the kit's guardrails for **discovery + verification**; use the pipeline only to **distribute rights-cleared rows**.

---

## Suggested approach

1. **Commit `employer-watchlist.csv` + `job-snapshot.csv`**; pin the kit to a revision so it is reproducible.
2. **Adopt `scan_boards.py` as the Batch-A engine.** Seed the watchlist from the board's proven Workday/ATS tenants, ServiceNow Partner Finder (Elite→Premier→Select, incl. Toronto boutiques like Pentio), Salesforce AppExchange Consulting, and 12–24 mo of past hirers. Run per small employer batch → JSONL leads.
3. **Add a `rights` field to the inbox row schema** and gate the merger on it (`unknown`/restricted → hold, don't publish).
4. **Upgrade the dedupe primary key** to `(ATS, tenant, posting_id)`, then employer-req+country, then normalized URL; keep `title|company|city` as the *review* tier only.
5. **Adopt the liveness taxonomy + two-clocks labels** in the board's Note column (`listed` vs `form_reached`; `newly-posted ≤30d` vs `still-listed older`).
6. **Run the 7-day pilot** across the four angles; report incremental unique yield, verification quality, issuer→discovery freshness lag, and cost — then **rank the angles on evidence**, reporting exclusive vs shared finds.
7. **Route kit output into BestieJob via the existing inbox/merger** (one file per agent per day, `--dry-run` the validator/merge, additive path, single `bestiejob-main-write` writer). Keep the rich evidence in a **private sidecar** — the merger's 6th-cell Note is not reliably carried into output.
8. **De-risk Batch D** with the runbook's dated 2026 event/partner URLs rather than guessed finder paths.

---

## Bottom line

The kit is the disciplined, employer/ATS-first counterpart to the aggregator-heavy pipeline (which is ~55% LinkedIn+Adzuna today). Folding it in raises signal quality and untapped headroom on Batch A, adds the rights governance a public board needs, and gives a measured way to rank the angles. Immediate actions: **commit the missing data files**, **label source rights and gate publishing**, and **run the pilot** before scaling redistribution.

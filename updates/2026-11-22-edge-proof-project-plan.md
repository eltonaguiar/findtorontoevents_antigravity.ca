# Edge-proof project plan published

**Why:** the desk needed a written, checkable standard for what "proven edge"
means before any more strategy work, so that promotion cannot happen by
enthusiasm.

**What:** `reports/2026-11-22-edge-proof-project-plan.md` — the honest starting
line (no class survives cost; EQUITY is the only gross-positive class at net
0.990), the G0–G8 proof gates pinned to concrete repo artifacts, ranked tracks
(T1 equity → T6 measurement infra), a sample-size table (μ = 0.05 R needs 3,136
trades), the forward-sleeve design with promotion/kill rules, phases P0–P5 with
hard acceptance criteria, and a pre-committed concession clause.

**Findings recorded while writing it:** the hypothesis registry uses 29 distinct
status strings for what should be a closed vocabulary (P0 fixes this);
`forward_book.json` stores TP/SL at rule level only, so an entry cannot be
scored independently (P0 adds per-entry TP/SL); the forward book has 5 open and
0 closed entries, so no score exists yet.

**Verification:** figures quoted are from `audit_dashboard/data/dashboard_data.json`,
the 2026-11-22 full-population retraction, `reports/hypothesis_registry.json`
(counted: 108 hypotheses, 29 status strings), and
`audit_dashboard/data/forward_book.json` (5 OPEN / 0 resolved, generated
2026-11-22T08:16:15Z).

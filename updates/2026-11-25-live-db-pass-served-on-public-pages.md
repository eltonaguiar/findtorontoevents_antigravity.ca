# P0 — Live DB password was still being served publicly (2026-11-25)

**Status:** fixed in repo source, verified pre-deploy.
**Severity:** P0 — live production credential readable by anyone on the internet.
**Owner action still required:** **rotate the `ejaguiar1_*` DB passwords.** See §6.

---

## 1. What was broken

The peer audit `notes/buffy-deploy-scrub-2026-11-25` (v14) reported the phishing-kit
cleanup as verified and stated:

> VERIFIED: `/audit/incidents.html` 200 with 0 occurrences, `/updates/` 200 with 0 occurrences.

That was **true for `incidents.html` and false for the other two**. Measured live from
the internet (independent of the audit workstation, which 403s site-wide):

| URL | Status | Family-pattern occurrences |
|---|---|---|
| `/audit/incidents.html` | 200 | **0** — fix held |
| `/audit/data/incidents_enhancements_feed.json` | 200 | **3** |
| `/updates/` | 200 | **2** |

The leaking text was **INCIDENT #89** — *"Live DB password `<SECRET>` hardcoded repo-wide
(rotate + scrub)"*. The incident row that *narrates* the leak *was* the leak: its
`title`, `description` and `recommended_fix` fields all quoted the live
`ejaguiar1_stocks` password verbatim, and the feed is served with
`"asset_class": "OVERALL"` so it appeared on every consumer of that sidecar.

## 2. Root cause — the fix was applied to the wrong layer

The real source of truth for all three artefacts is the **MySQL database**, not the
committed files:

- `tools/audit_pick_funnel/render_incidents_page.py` reads 20 tables —
  `INCIDENT_<CLASS>` / `ENHANCEMENT_<CLASS>` for STOCKS, ETFS, CRYPTO, FOREX,
  COMMODITIES, BONDS, FUTURES, PENNY + `OVERALL` — and writes
  `audit_dashboard/incidents.html`, `audit_dashboard/data/incidents_enhancements_feed.json`
  and the auto-injected block inside `updates/index.html`.
- `.github/workflows/incidents-enhancements-nightly.yml` runs that renderer nightly,
  **commits** the three outputs (`[skip ci]`) and **FTP-deploys** them.

The DB itself had already been cleaned by the peer audit. Verified here directly:

```
target tables: 20
TOTAL cell hits in DB: 0     <-- the DB is clean
```

So the DB was right and the *committed outputs* were stale. Because the nightly job
FTP-uploads whatever is committed, **each nightly run re-published the un-redacted
copies** — the server-side fix was overwritten repeatedly. Edit the site and it comes
back; edit the repo and it stays fixed.

A secondary, self-concealing detail: `updates/index.html` is regenerated from DB text,
so a hand-edit there is also transient unless it lives outside the auto-injected block
(see §3).

## 3. What changed

Regenerated all three artefacts from the now-clean DB, then redacted the one remaining
hand-authored occurrence:

| File | Before | After regenerate-from-DB | After redaction |
|---|---|---|---|
| `audit_dashboard/data/incidents_enhancements_feed.json` | 3 | **0** | 0 |
| `audit_dashboard/incidents.html` | 3 | **0** | 0 |
| `updates/index.html` | 2 | 1 | **0** |

- The two `updates/index.html` hits: one was inside the
  `AUTO-INJECTED:INCIDENTS-ENHANCEMENTS` block (regeneration removed it); one was in a
  **hand-authored historical entry** outside the block (offset 221,895) and was redacted
  by direct replacement.
- The scanner/redactor used the family regex
  `(stocks|backtests|sportsbet|favcreators|events|memecoin|news|tvmoviestrailers|deals)1234560`
  — the literal was never printed into logs, commits or notes.

**Regeneration was otherwise a no-op**, which is the proof that the DB text was already
fixed and only the committed copies were stale:

```
3 files changed, 11 insertions(+), 11 deletions(-)
```

## 4. How it was verified

| Check | Result |
|---|---|
| DB scan, all 20 `INCIDENT_*`/`ENHANCEMENT_*` tables | 0 cell hits |
| Family-pattern count, `incidents_enhancements_feed.json` | 0 |
| Family-pattern count, `incidents.html` | 0 |
| Family-pattern count, `updates/index.html` | 0 |
| `json.load()` on the feed | OK — incidents=196, enhancements=208, findings=21 |
| `</html>` present in both HTML files | 1 each |
| Diff scope | exactly 3 files, 11+/11− |
| Secret literal in this document / commit message | 0 occurrences |

Post-deploy verification (must be run **from the internet**, not locally — the nightly
job is what republishes them):

```bash
PAT='(stocks|backtests|sportsbet|favcreators|events|memecoin|news|tvmoviestrailers|deals)1234560'
for u in https://findtorontoevents.ca/audit/data/incidents_enhancements_feed.json \
         https://findtorontoevents.ca/audit/incidents.html \
         https://findtorontoevents.ca/updates/ ; do
  printf '%s -> %s\n' "$u" "$(curl -s "$u" | grep -coE "$PAT")"
done
# all three must print 0
```

## 5. Why the local worktree agreed with the server

v14 also claimed *"the worktree is already redacted; an owner commit ships it."* It was
not: the working tree carried the same 2 and 3 hits, identical to `origin/main`. That is
the tell that the "fix" was applied at the DB/deployed-output layer while the repo layer
was never committed.

## 6. Owner action still required

1. **Rotate `ejaguiar1_*` database passwords.** This value has been public on a public
   GitHub repo since roughly June 2026 and was additionally served over HTTP. Redaction
   stops further disclosure; it does not un-disclose anything. Assume compromised.
   For reference: `DB_PASS_STOCKS` currently connects successfully, so the credential is
   live.
2. **Remaining 25 tracked files still contain class passwords** (this PR intentionally
   scoped to the 3 publicly-served artefacts). Highest counts:

   | File | Occurrences |
   |---|---|
   | `groksstuff.txt` | 77 |
   | `reports/transcript_scan_20260525_055154.md` | 10 |
   | `HANDOFF_CLAUDE_CLI_2026-06-03.md` | 9 |
   | `docs/DB_CREDENTIALS_MIGRATION_2026-06-02.md` | 6 |
   | `updates/2026-05-23-fc-db-restore-after-repo-migration.md` | 4 |
   | `updates/2026-06-02-eagle6-and-eagle4-5-guide-db-doc.md` | 3 |
   | `.github/workflows/db-password-leak-guard.yml` | 2 |
   | `reports/peer_blackbox_incidents-enhancements-pr_2026-05-31.md` | 2 |
   | plus 18 files with 1 each | 18 |

   None of these are served through the web docroots (they are repo-root/reports paths,
   not in the `findtorontoevents.ca/` or `tdotevent.ca/` deploy lists), so they do not
   have a live-URL exposure — but they are world-readable on GitHub. A follow-up sweep
   is recommended. Note the all-9-classes breadth: this is not a one-password problem.
3. **Consider the guard.** `.github/workflows/db-password-leak-guard.yml` itself still
   contains the literal, so the guard's own tree-scan can never be clean. It should
   reference the credentials by env var / secret name only.

## 7. Notes for the next agent

- **Fixing a deployed artefact is not fixing the defect.** Always ask "what regenerates
  this file, and what is *its* input?" Here the input was MySQL; the fix had to land in
  the DB (peer audit) *and* the repo (this PR). Verify with
  `git grep -lE '<pattern>' origin/main -- .`, never just by curling the live URL.
- **A generated file and a hand-authored file can share one path.** `updates/index.html`
  is both. Regenerating it silently reverted nothing here, but a hand-edit *inside* the
  auto-injected block would be destroyed on the next nightly run. Check block
  containment before hand-editing a page that has `AUTO-INJECTED:*` markers.
- **`grep -c` counts lines, `grep -o | wc -l` counts occurrences.** An early count read
  6 hits; the true occurrence count was 8.
- **Don't publish the secret while proving the secret is published.** Use the family
  regex, mask contexts, and verify 0 occurrences in your own output before committing.

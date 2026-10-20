# Freebuff session-log page published to /updates/ (2026-10-19)

## What was requested

Document the day's changes / plan / achievements / future research as an HTML
page with "freebuff" in the name, under findtorontoevents.ca/updates/.

## What was done

1. **Created** `updates/freebuff-2026-10-19-money-ready-methods.html` —
   self-contained (inline CSS, no external deps, `noindex`) session log:
   Task 10 module + verification ledger, method-review findings, the
   combined-book reproduction table (initially shipped with a since-**retracted**
   "two reference-parser bugs" claim — see Correction below; final version shows
   the exact 8/8 reproduction), the adopted 4-phase plan with failure protocol,
   and future-research
   list (Task 10 wiring, PEAD shadow→production, funding-carry regime gate,
   TSMOM→n≥100, GRS/conformal/sequential gates, French-data refresh).
2. **Inserted** its entry at the top of `updates/index.html` (per the file's
   own newest-first rule, right after the INSERT marker; re-anchored because a
   parallel combined-book entry had landed at the top meanwhile).
3. **Deployed** both files over FTPS. First attempt extracted only the
   import+assignment AST nodes from `tools/deploy_updates_v05.py` (whose
   top-level code connects on import) and uploaded via `ftplib.FTP_TLS` +
   `prot_p()`. **Superseded:** per later instruction, no further credential
   extraction from that script is performed — `FTP_*` was found already present
   in the process environment and is now the sole deploy path; hard-code
   removal is proposed (uncommitted) in
   `updates/2026-10-19-ftp-credential-handling-proposal.md`. No credential
   value is printed or copied into any file, memory, or page.

## Verification

- stdlib HTMLParser: freebuff page — no errors, no unclosed tags. The
  pre-existing `updates/index.html` body/div mismatch reproduces with the new
  block stripped out, so it is **not** caused by this change (not fixed here —
  3.9 MB file owned by the changelog pipeline).
- Live HTTP checks: `index.html` **200** (3,916,155 bytes, contains
  "Freebuff session log" ×2 — entry text + link), freebuff page **200**
  (13,025 bytes, correct `<title>`).

## Notes / limitations

- `updates/index.html` was deployed with a concurrent agent's Oct 19
  combined-book entry also present (unavoidable — single shared file; entries
  are independent blocks).
- The reference reproduction artifacts (pristine, **unmodified** `run.py`;
  an earlier TXT-flavor attempt needed local patches, all dropped after the
  CSV-zip re-run) live in `/tmp/grokbot-check/` — throwaway, by design; the
  findings are recorded in the freebuff page and memory, not as repo files.

## Correction (2026-10-19, after reference-author review)

- The page/entry originally claimed "two reference-parser bugs" (cp1252
  decode, whitespace-delimited Ken French table). **Retracted — not bugs.**
  The reference reads Ken French `*_CSV.zip` files (comma-separated, through
  2026-08); the first run used the older TXT flavor (ends 2022-08), which the
  parser was never meant to handle.
- Re-run with the CSV zips + unmodified `run.py`: **8/8 rows identical** to
  committed `results.csv`, max |Sharpe Δ| = **0.0000** (Combined 1.2666 /
  8.85% / −20.45%; QualVal 0.859 with data ending 2026-08).
- Page + index entry wording corrected and redeployed (env-var FTP path);
  nothing in `grokbot` needs to change.

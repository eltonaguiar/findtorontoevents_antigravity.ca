# audit3 — canonical full-book verification (2026-11-19)

**Author:** Kilo (worktree `universal-pisces`)
**Question:** the ledger scores the 3,500-row export slice (21.4%). What changes
when it scores the canonical resolved view (8,735 rows)?

## Method

Fetched the live payload and its canonical sidecar from the site:

- `https://findtorontoevents.ca/audit/data/dashboard_data.json` (26.1 MB,
  `generated_at` 2026-11-19T07:13Z) — carries a `resolved_closed_picks_net`
  block (`rows_count=8735`, `rows_sha256=aa7f7f89…`).
- `https://findtorontoevents.ca/audit/data/resolved_closed_picks_net.json`
  (3.36 MB, 8,735 rows).

Ran `python3 -m alpha_engine.audit3_tribunal` with the sidecar next to the
payload so `load_rows` used the canonical view (`coverage.denominator.mode =
canonical`).

## Result — the full book is harsher

| Metric | Slice (3,500) | Canonical (8,735) |
|---|---|---|
| Rows scored | 3,500 (21.4%) | **8,735 (53.5%)** |
| Cells tested | 45 | 67 |
| PROVEN | 0 | 0 |
| CANDIDATE | **1** | **0** |
| KILL cells | 10 | 11 |
| KILL classes | 2 | **3** (CRYPTO, FOREX, COMMODITY) |

**The slice's only CANDIDATE does not survive the full book.**
`luxalgo_confluence SHORT` was CANDIDATE on n=476 (net +0.688%/trade). On the
canonical view it is **WEAK, n=1,924, net −0.089%/trade, 2× CI [−0.343, −0.038]**
— negative expectancy. Its LONG side is KILL (n=2,062, −0.142%/trade). The
apparent short edge was a small-sample artefact of the export slice.

FOREX moves WEAK → **KILL** on the full book (n=270), consistent with the known
FX data problems.

## Why this matters

This is the direct, measured answer to the review's E2 recommendation: scoring
the export slice flatters the system. The canonical view is available and the
workflow already fetches it; the 04:04 snapshot simply predated the payload
carrying the block (`fallback_reason: no_canonical_block`). The next scheduled
`audit3-ledger.yml` run should pick up the canonical denominator automatically.

## Recommended follow-up (not done here)

1. Make the canonical-view fetch **required** (or fail the run) rather than
   `continue-on-error`, so a silent return to the 21.4% slice is impossible.
2. Publish both denominators on `/audit3` (slice vs canonical) so a reader can
   never mistake one for the other.
3. Treat the `luxalgo_confluence SHORT` candidate as **refuted**, not pending.

## Reproduction

```
curl -o dd.json https://findtorontoevents.ca/audit/data/dashboard_data.json
curl -o resolved_closed_picks_net.json \
     https://findtorontoevents.ca/audit/data/resolved_closed_picks_net.json
python3 -m alpha_engine.audit3_tribunal --picks dd.json --out audit3_canonical.json
```

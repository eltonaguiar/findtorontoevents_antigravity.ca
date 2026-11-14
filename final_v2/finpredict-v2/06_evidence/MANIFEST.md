# Evidence Manifest — final_2026_11_14/finpredict-v2

**Captured:** 2026-11-14T20:25Z

## Sources

| Source | What | Notes |
|---|---|---|
| `https://findtorontoevents.ca/audit/data/*.json` | live dashboard payloads | captured 16:03–16:05Z; `generated_at 2026-11-14T14:30:07Z` |
| GitHub API / `gh` | 365 workflows, 500 runs, job logs | `actions_deepdive/` |
| Binance Vision/API | spot klines, funding rates | `data/manifest.json` with SHA-256 |
| Nasdaq quote API | ETF daily closes | price-only, ~10y cap |
| Treasury.gov | 13-week bill yield | cash benchmark |
| `data/live_picks.db`, `audit_dashboard/data/*` | local DB snapshots | read-only |
| Peer worktrees/branches | claims and audits | reviewed, not copied wholesale |

## Included

- `01_audit/` — `MASTER_AUDIT.md`, `INDEX.md`, `PEER_CROSSREF.md`, `sub/A–G`, `recommendations/`
  (P0/P1, per-class, patch plan).
- `02_research/profitability/` — protocols v1/v3/v4, `SCORECARD.md`, `HYPOTHESES.md`, `README.md`,
  `NEXT_DATA_REQUIREMENTS.md`, code (`backtest.py`, `strategies.py`, `data/loader.py`,
  `run_v1..v4.py`, `validate_h10.py`), runs/v1–v4 (results, reports, verdicts, returns), validation
  (H10 + VWAP replication/review), `forward/`.
- `03_peer_reviews/` — PF1–PF5, RR1–RR3, FP1–FP4, `inspect-wt_integration.md`,
  `FOLDER_REVIEW_SYNTHESIS.md`, `rereview_1837/`.
- `04_actions/actions_deepdive/` — `ACTIONS_DEEP_DIVE.md`, GA1–GA4, matrix, trimmed raw logs.
- `05_final/` — `FINAL_SYNTHESIS.md`, `PEER_CLAIMS_MATRIX.md`.

## Excluded (reproducible)

- `data/cache/` (Binance/Nasdaq/Treasury downloads) — re-fetch via loaders.
- 25–34 MB `dashboard_data.json` / `dashboard_payload.json` — re-fetch from the live URLs.
- 795 MB workflow logs — `gh run view <id> --log`.
- Peer source trees — only findings/reviews are included.

## Reproduction

```bash
# audit payloads
for f in dashboard_data dashboard_payload money_ready_verdict pf_registry \
         anti_overfit_audit audit_surface_truth summary_picks db_health; do
  curl -sS "https://findtorontoevents.ca/audit/data/$f.json" -o "$f.json"
done

# research
cd 02_research/profitability
python3 run_v1.py && python3 run_v2.py && python3 run_v3.py && python3 run_v4.py
python3 validate_h10.py

# actions
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows --paginate
```

## Integrity

- Data manifests with SHA-256: `02_research/profitability/data/manifest.json`.
- Every numeric claim in `05_final/` traces to a review file in `03_peer_reviews/` or a run in
  `02_research/profitability/runs/`.
- `UNVERIFIED` items are listed in the individual reviews and in `FINAL_SYNTHESIS.md` §8.

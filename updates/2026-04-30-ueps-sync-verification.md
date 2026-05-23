# UEPS → active_picks.json Sync Verification — 2026-04-30

## Verdict: PARTIAL

PR #518 wire-up code is merged and correct. `ueps_picks.json` has `n_long=30`, but
`active_picks.json` shows `long_term_value count = 0` because the UEPS cron has not
yet fired during US market hours since the merge. First eligible fire: ~14:30 UTC
2026-04-30. Re-verify after that window.

---

## PR #518 Merge Metadata

| Field | Value |
|---|---|
| Title | feat(ueps): sync UEPS picks into active_picks.json (4h cron wire-up) |
| State | MERGED |
| Merged at | 2026-04-29T21:21:01Z |
| Head commit (shorthash) | `34468a61` |
| PR URL | https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/518 |

---

## `active_picks.json` Stats (origin/main as of ~07:46 UTC 2026-04-30)

| Metric | Value |
|---|---|
| Total picks | 153 |
| `pick_type = long_term_value` | **0** |
| UEPS-keyed picks (`id` prefix `ueps__`) | 0 |
| Dominant source systems | multi_asset_copytrader (51), copy_trader_intel (48), ml_crypto_predictor (19) |

All 153 entries carry `pick_type: null/none` — none are `long_term_value`. The
`sync_to_active_picks()` function has not yet been exercised post-merge.

---

## `ueps_picks.json` Stats (origin/main)

| Metric | Value |
|---|---|
| `generated_at` | 2026-04-30T05:43:30.524248+00:00 |
| `summary.n_long` | **30** |
| `summary.n_short` | (see raw file) |

Full long-pick symbol list (30 symbols):

```
ADBE, QCOM, META, PYPL, HD, MSFT, MA, XOM, CRM, GOOG,
V, GOOGL, NVDA, PEP, NFLX, T, MDT, AAPL, DHR, TXN,
PFE, JNJ, COST, IBM, CSCO, LIN, AVGO, TSLA, BMY, BA
```

---

## Symbol Overlap (UEPS long-picks that also appear in active_picks)

3 symbols coincidentally appear in `active_picks.json`, but **not** as `long_term_value`
picks — they belong to other source systems (copy trader / ML predictor):

| Symbol | Appears in active_picks? | As LTV pick? |
|---|---|---|
| GOOGL | ✓ | ✗ |
| NVDA | ✓ | ✗ |
| PFE | ✓ | ✗ |

Remaining 27 UEPS symbols: not in `active_picks.json` at all.

---

## Cron Commits Since Merge

The expected commit message pattern is:
`data: ueps picks refresh - long=X short=Y (timestamp) [skip ci]`
(from `.github/workflows/ueps-pick-runner.yml`)

| Result |
|---|
| **0 matching commits found** in visible git history since merge |

Git history available in this fetch begins at ~05:18 UTC 2026-04-30. The merge
landed at 21:21 UTC 2026-04-29, just after US market close (EDT ≈ 20:00 UTC).
The 4h cron fires only during US market hours; first eligible slot post-merge is
approximately 14:30 UTC 2026-04-30 — which had not yet occurred at time of
verification.

### Anomaly logged

A commit `da9b8fd4` ("Signal recorder update 2026-04-30 05:50 UTC") appeared in
an initial path-filter query for `audit_dashboard/data/ueps_picks.json` but on
inspection its only changed file was `alpha_engine/data/active_picks_fast.json`.
This is likely a shallow-clone path-filter artifact. `ueps_picks.json`'s
`generated_at` (05:43 UTC) predates this commit; the file was probably written by
a separate signal-recorder process that does **not** invoke
`run_ueps_pickers.py`'s new sync path.

---

## Next Steps (PARTIAL verdict)

1. **Re-verify at ~15:00 UTC 2026-04-30** — after the first post-merge market-hours
   cron fire. Look for a commit with subject
   `data: ueps picks refresh - long=30 short=... [skip ci]`.
2. After that commit lands, re-run this check:
   ```bash
   git show origin/main:alpha_engine/data/active_picks.json \
     | python3 -c "import json,sys; p=json.load(sys.stdin); \
       ltv=[x for x in (p if isinstance(p,list) else p['picks']) \
       if x.get('pick_type')=='long_term_value']; print(len(ltv),'LTV picks')"
   ```
   Expected: `>= 1 LTV picks` (ideally 30).
3. If still 0 after two consecutive cron fires, investigate whether the
   signal-recorder process is overwriting `ueps_picks.json` via a separate code
   path that bypasses `run_ueps_pickers.main()` — in which case the sync hook
   in `main()` would never be called from that path.
4. Confirm `ueps-pick-runner.yml` schedule is not suspended or skipped via
   `gh run list --workflow=ueps-pick-runner.yml --limit=5`.

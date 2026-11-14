# Archive — finpredict-v3 audit session (2026-11-14)

Agent subtree: `finpredict-v3`
Archive stamp: `2026-11-14T155500Z`
Source: findtorontoevents.ca/audit live dashboard (payload generated 2026-11-14T14:30Z), GitHub Actions API, Binance/Yahoo live quotes.

## Deliverables in this archive

- `tools/pi_data_hygiene.py` — data-hygiene guardian (additive, read-only). Flags:
  - `STALE_CRYPTO_PRICE` (24/7 crypto whose current_price == entry_price, pinned)
  - `FROZEN_CLOSED_PHANTOM` (closed picks resolved to 0% with exit UNKNOWN, exit==entry)
  - `DATE_ONLY_SEED` (signal_time/entry_time stored as bare YYYY-MM-DD → UI renders "no date")
  - `NULL_PRICE`, `PLACEHOLDER_ENTRY`
  - prints TRUE per-class recency (signal age vs whether a live quote exists).
  Run: `python tools/pi_data_hygiene.py --json audit_dashboard/data/dashboard_data.json --asof 2026-11-14T15:50:00+00:00 --show`
  Exit 1 when findings exist (CI-gateable).
- `tests/test_pi_data_hygiene.py` — 11 tests (11 passed, 0.2s).
- `updates/2026-11-14-prediction-data-hygiene.md` — full defect evidence + per-asset-class remediation plan with target code.

## Verified findings (evidence in the updates doc)

| # | Finding | Live evidence |
|---|---------|---------------|
| 1 | Crypto current_price pinned to entry (STALE) | XRPUSDT, BTCUSDT current==entry while market moved +0.9%/+1.3% (Binance). |
| 2 | "1.9h ago" banner = signal age, not price freshness | Newest crypto signal 13:53Z; prices never re-quoted at 14:30Z build. |
| 3 | 11 frozen closed FOREX phantoms | March 2026 rows, pnl 0.0, exit UNKNOWN, exit==entry (EURUSD, USDCHF, USDJPY, AUDUSD, GBPUSD, NZDUSD, SOFI). |
| 4 | Futures ES=F "no date" = date-only signal_time string | `"2026-11-14"` (no time), gated placeholder, 0 closed history. |
| 5 | Bond picks unmarked / dead | open seeds ~1d old, current_price null; only settled bond closed Nov 10; n=1 closed. |
| 6 | Survivorship in headline stats | 7,914/16,126 (49%) closed pass integrity; 8,888 auto-expired removed pre-resolution. |
| 7 | Metrics not alive | edge_ratio absent from main JSON; FWD populated 48% (111/255 zero-forward); strong_signals.json 404; kalshi snapshot ~7mo stale w/ null prices; several sections empty. |

## Investment verdict

Not money-ready. Aggregate closed book negative: WR 41.8%, PF 0.94, equal-weight compounded −99%. System's own `money_ready_verdict.json` list is empty (every class NOT_READY / INSUFFICIENT_DATA). Headline EQUITY 75% WR is n=8 (95% CI [0.41,0.93]); full n=461 sample shows ~43%/PF 0.70. Don't allocate capital on this surface.

## Reproducibility

- `python3 -m pytest tests/test_pi_data_hygiene.py -q` → 11 passed
- Guardian live run: 2 stale crypto prices, 11 frozen phantoms, 3 date-only seeds.

## Peer reconciliation status (2026-11-14 ~16:00Z)

Attempted to reconcile against peer-agent findings ("another agent's findings" / a
`chat_transcript_2026-11-14.md`). The cited file path is a Windows path
(`C:\Users\zerou\Desktop\chat_transcript_2026-11-14.md`) on a different machine
and is NOT readable from this Linux host. I searched for a local copy:

- Shared task board: no peer messages posted yet.
- `origin/main` under `2026-11-14/`: only this `finpredict-v3` archive (no peer archive merged).
- Worktrees: `wt-audit-prediction-system` (branch `audit-prediction-system-20261114-154529`) is a plain checkout of `main`; its `chat_transcript.MD` is an OLD 2026-05-15 file, not today's.
- Project root: only `bestiejob/` job-discovery files today (unrelated to prediction audit). No master-plan/review/findings doc found.

**Conclusion:** no peer findings were accessible to reconcile against. This archive stands
as the finpredict-v3 session deliverable, UNCHANGED pending peer input. The reviewer agent
should reconcile against the full audit report + this data-hygiene guardian. Items I could
NOT verify against peer work are marked accordingly; nothing here is fabricated.

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
  - prints TRUE per-class recency (signal age vs whether a live quote exists)
  - `ACTIVE_RAW ZOMBIE SCAN` — per-class count of rows older than 7d / with null price,
    so the raw feed's zombie population is visible (e.g. CRYPTO 3,577 rows: 3,085 older
    than 7d, 3,170 null-price).
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

## Peer reconciliation (2026-11-14, after peer transcript supplied)

Peer = the `audit/live-audit-2026-11-14` agent (June snapshot + Nov 14 live). I reconciled
its findings against my verified ones. Convergences and deltas below. Peer left external
market-quote verification UNVERIFIED (blocked); I completed it (Binance + Yahoo), so this
archive now carries the verified market cross-references.

### Convergences (peer corroborates my findings)
- Crypto "1.9h ago" = signal age on the main panel; raw `active_raw` feed is full of zombies
  (peer: CRYPTO median age 89d; mine: 3,085/3,577 older than 7d). Concur.
- Bonds "4 days ago": peer newest closed BOND = 98h (4.1d); mine = last settled TLT Nov 10. Concur.
- FUTURES dead: peer median raw age 2,344h; mine 10/13 raw older than 7d, ES=F placeholder. Concur.
- `hyro_pick_performance.json` stale ~157–158h (peer + mine agree, ~6.6d).
- Verdict: not money-ready; `money_ready_verdict` empty; aggregate negative. Concur.

### Deltas added from peer (now folded into my findings)
- **Honesty-layer root cause:** CRYPTO headline PF 9–18 / WR 78–88% surfaces are inflated by
  `claude_gainer_st` picks with **EXPIRED→WON resolver mislabels**; honest numbers are
  pf_registry policy-clean-net (PF 0.98 / WR 39.7%) and money_ready_verdict (PF 0.96 / WR 31.3%).
  This explains why official surfaces disagree (my "policy_clean 0.26 vs intrabar 0.92" vs peer's
  0.98/0.96).
- **Multiple-testing quantification:** your361 strategy families + 285 baby strategies + mutation lab
  ⇒ ~260 lucky PF>1.5 survivors expected at p=5%. June anti-overfit: 31/38 (82%) OVERFIT_LIKELY.
  z-scores: CRYPTO z=−7.1 (significantly worse than random), EQUITY z=1.39 (needs 1.96). This is
  the strongest direct answer to "profitable or artifact?" — mostly artifact.
- **Prediction-market-consensus garbage:** `XRPUSDT SHORT entry=0.0` emitted 2026-11-14T13:54 by
  `prediction_market_consensus`; BTCUSDT garbage entries 0.3322 / 1.334. Directly answers the
  "kalshi/mtf real?" question — the consensus feed emits zero-entry placeholder rows; on-disk
  kalshi snapshot ~7mo stale with null prices.
- **Mutual funds effectively unbuilt:** `alpha_engine/mutual_fund_ranker.py` and
  `/audit/mutual-funds.html` do not exist (institutional plan item F2). So "mutual funds" class
  is planned, not implemented.
- **Frozen scope depth:** 1,147/1,882 closed rows dropped as "spot-flicker" artifacts
  (|pnl|<0.02bps, exit==entry); 3,509 non-canonical FORCE_CLOSED_TOXIC statuses (tier red);
  exit reasons include 57 RESOLVE_FAILED_MAX_RETRIES; open incubator BTC picks stuck at
  current_price=None / pnl=0.
- **Actions health deltas:** Unified Audit Dashboard cancelled 3× with 0 jobs executed (queue
  discard); ALPHA ENGINE FAST had 2 failures in last 4 runs; Daily Prices yfinance failed Nov 12
  and 13. Root causes of runner failures remain UNVERIFIED (admin logs).

### Where I go beyond peer
- External price verification: Binance (crypto) + Yahoo (equity/ETF/futures/forex/commodity) —
  all matched to the cent / 0.25–1.3% crypto deltas. Peer left these UNVERIFIED.
- NEARUSDT: peer cites resolved trades +8.75% TP_HIT (entry 3.543) and −12.03% SL_HIT;
  the user's "3.16%" is not reproducible (my payload says 2.74%, live 2.98%) — magnitude plausible,
  exact figure an artifact.

**Validator:** this archive now reflects both agents' evidence. Tool upgraded with the
ACTIVE_RAW ZOMBIE scan. Nothing fabricated; peer items I could not independently confirm are
attributed to the peer.

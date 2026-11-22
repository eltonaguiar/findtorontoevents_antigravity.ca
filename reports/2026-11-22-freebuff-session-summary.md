# freebuff session summary — 2026-11-22 (for fleet review)

Branch: `fix/dsr-baselines-h146-key-scrub-2026-11-21`
Commits today: `72eda5af3ff`, `2d7af0f2c44`, `8ec96b7ef8a`, `40efacc378a`, `09efaa37fb3`
Earlier today: `a5809b45638` (H-151), `01d9159d6f5` (fleet map), `188551e1c5a`

## Achieved

1. **vLLM on :8000** — `nvidia/Qwen3.6-35B-A3B-NVFP4`, ~80 tok/s with thinking.
2. **Consult tooling** — `local_qwen` provider + automatic cloud→local fallback in
   `tools/consult_multi.py`; `vllm` target in `tools/fleet_consult.py`. Handles the
   HTTP-200-with-empty-content trap (budget < 1500 → thinking off).
3. **H-151 (net share issuance) REFUTED** — net spread −0.2054%/mo, FF4 alpha
   −0.357%/mo t=−0.63, harness REJECTED, 43 names/leg vs gate 100.
4. **Registry R5 cleared** — 6 prose-only entries given structured metrics;
   R5 6→0, R3 0, hypotheses 111 unchanged. H-126/H-133 → TESTED_WEAK,
   H-127/128/129 → blocked/untested (they were never run).
5. **Net-of-cost + OOS audit** (`tools/ledger_net_and_oos.py`) — CRYPTO net PF
   1.184 (gross 1.313), EQUITY 1.175 (1.229), ETF net 0.981 (edge is 7.8 bp wide).
   MomentumEMA has exactly two outcomes (−2.00/+3.00); mega_mutation trades 3 symbols.
6. **Full-population cost audit** (`tools/population_cost_audit.py`) — CRYPTO
   **PF 0.2656, −0.0464%/trade GROSS, n=22,864**. Every class is negative gross
   except ETF (n=32). The 1.31 was window selection.
7. **First-touch with real bars** (`tools/ohlc_bars.py` + `tools/first_touch_resolve.py`)
   — 1,717 crypto picks re-walked: 54% of exits have a different first-touch level,
   yet PF moves 1.367 → **1.479**. H-120's inflation does NOT reproduce on crypto.
8. **Data health** (`tools/ledger_data_health.py`) — 38 rows with exit_price=0.0
   marked CLOSED; 54 rows at exactly 0% P/L; 44 inverted SL/TP; **400 rows whose
   exit sits outside their own TP/SL envelope, where P/L == price move exactly
   (ratio 1.00), so the LEVELS are stale, not the P/L**; 1,112/4,877 "resolved"
   rows with no exit price.
9. **audit3 publish path** — `/audit/audit3.html` 404'd because the page only ever
   went to `/audit3/index.html`; fetches made absolute and upload added to
   `audit3-ledger.yml`'s credentialed `/audit` block (the `healthchecks` group in
   deploy_audit_files.py is never invoked — dead config removed).

## Correction to my own earlier claim

I called CRYPTO "PROVEN" on 2026-11-18 data. That was gross and window-selected.
On the full population it is **negative before costs**. Retracted.

## Real-money readiness — blockers

1. Per-pick net P/L does not exist (`after_cost_net_per_trade` on 0/3,500).
2. 38 unresolved rows counted as closed; 1,112 unresolved rows in a resolved file.
3. Level fields stale on 11.4% of rows.
4. DSR gate red: 74/80 strategies below 0.95 (peer report).
5. No forward, auto-tracked, pre-registered paper book with bar-resolved exits.
6. No position sizing / drawdown kill switch wired to these numbers.

## Candidate set for cross-check (NOT a recommendation)

Selection: recent-window per-symbol net expectancy, n ≥ 8, cost 20bp crypto /
10bp equity+ETF. Every class below is negative on the full population.

| class | #1 | #2 | #3 |
|---|---|---|---|
| CRYPTO | LINK-USD (n=20, PF 1.79, WR 65%) | AVAX (n=18, PF 1.93, WR 61%) | TIA-USD (n=16, PF 1.92, WR 63%) |
| EQUITY | AAPL (n=71, PF 1.78, WR 56%) | AMD (n=65, PF 1.83, WR 55%) | BAC (n=25, PF 1.67, WR 64%) |
| ETF | QQQ (n=72, PF 1.37, WR 50%) | XLK (n=60, PF 1.33, WR 48%) | SOXX (n=37, PF 1.19, WR 46%) |

Honourable mention, excluded for sample size: NEAR-USD (n=11, PF 4.54), RIOT
(n=10, PF 3.10).

**Ask of peers:** produce your own top-3-per-class with the same cost assumption
and say where you disagree. Also: if you have a bar source for EQUITY/ETF daily
OHLC that answers without a key (Stooq now serves a JS challenge), that unblocks
first-touch for 1,193 non-crypto picks.

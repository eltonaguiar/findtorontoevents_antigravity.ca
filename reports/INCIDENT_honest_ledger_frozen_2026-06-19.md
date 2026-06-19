> **✅ RESOLVED 2026-06-19 ~03:30Z** — `at_signal_outcomes` is flowing again (latest_created 03:39, intrabar 03:58; outcome-resolver GREEN). The CONVERGED root cause (FMP_API_KEY not wired into the active_picks_sync env; secret existed) is authoritative — the earlier DB_PASS_BACKUPS / yfinance-IP-block theories below are SUPERSEDED. Only the un-mask (P0-5) remains open.

# P0 INCIDENT — honest ledger (`at_signal_outcomes`) frozen ~6 days behind GREEN CI

**Found:** 2026-06-19 ~01:05Z (via the money-ready monitoring loop). **Severity:** P0 — the verdict-grade honest measurement layer (foundation of the entire money-ready program) stopped updating, while `audit-dashboard.yml` reported success every hour.

## Symptom
- DB `NOW()` = 2026-06-19 01:02 (clock current).
- `at_signal_outcomes`: **latest `created_at` = 2026-06-12 19:03**, **latest `intrabar_resolved_at` = 2026-06-13 17:55**, **0 resolved in last 12h**.
- Yet `at_raw_picks` is fresh (`recorded_at` 2026-06-19 00:15) — picks ARE flowing in; they are NOT being resolved into the honest ledger.
- `audit-dashboard.yml` last 3 hourly runs all "success".

## Impact
- The honest ledger has been frozen ~6 days. All MEASURE numbers (per-class 0/9, the `crypto_rsi5070_us` lead at n=108) are on a **frozen cohort**.
- The lead's **n≥150 Jun-25 gate is unreachable** while resolution is dead.
- Classic masked-failure: `|| echo non-fatal` + resolver swallowing its own DB error → green CI, dead ledger. (cf. `feedback-masked-failure-pattern-ci`.)

## Root causes (from run 27796353273 logs)
1. **`universal_pick_resolver` step had NO DB credentials** — env block was only `PICK_OUTCOMES_MYSQL_ENABLED: '1'`; the 5 sibling DB-writing steps carry `DB_PASS_STOCKS`/`MYSQL_PASSWORD`. Result: `[mysql] connection/upsert error: (1045, "Access denied for user '..._stocks' (using password: NO)")` → writes failed; the resolver logged it as a warning and exited 0 → step green. **← FIXED this session.**
2. **`No module named 'yfinance'`** in price-dependent steps → equity price fetch fails → `active_picks_sync` raises "0/1 EQUITY prices fetched — APPLY mode, refusing to proceed" (correct safety halt, but no resolution).
3. **Binance HTTP 451 (geo-blocked on GH runners) + CryptoCompare 401** → crypto prices fail; API-failover chain (CoinGecko/KuCoin per the CLAUDE.md rule) not rescuing.
4. **Intrabar reresolve (`reresolve_intrabar_signal_outcomes.py`) frozen since 06-13** despite having `DB_PASS_STOCKS` + `DB_PASS_BACKUPS` env — suspect the **`DB_PASS_BACKUPS` secret is unset/empty** (line 564 has no fallback, unlike `DB_PASS_STOCKS`); the resolver does a mandatory backup-before-mutation via `get_backups_creds()` and raises if backups creds fail (swallowed by `|| non-fatal`). This is the exact 2026-06-12 P0A failure mode recurring.

## Fix applied (this session)
- **`audit-dashboard.yml` (commit e45c434b7):** wired the existing DB secret onto the `universal_pick_resolver` step (`DB_PASS_STOCKS`/`MYSQL_PASSWORD`/host/user/db), matching the sibling "Sync paper trades" step. Restores the resolver's DB write. YAML validated.

## OPERATOR / deeper items (not unilaterally fixable)
- **Verify the `DB_PASS_BACKUPS` GitHub secret exists** (or give line 564 a `|| secrets.MYSQL_PASSWORD` fallback IF the backups DB shares the stocks password) — otherwise the intrabar reresolve stays frozen even after fix #1.
- **`yfinance` install gap:** ensure every price-dependent step `pip install yfinance` (or a shared deps step) — several steps import it without installing.
- **Binance 451:** the failover chain must actually engage on 451 (CoinGecko/KuCoin/CryptoCompare) for crypto price fetch on GH runners.
- **Un-mask:** the resolver swallows DB-auth errors + exits 0 — make DB-auth failures fail-hard (or assert rows-written > 0) so this can't recur silently. Assert `generated_at`/row-count, never trust green.

## Verify
After the next `audit-dashboard.yml` run: `SELECT MAX(created_at), MAX(intrabar_resolved_at) FROM at_signal_outcomes` should advance past 2026-06-12/13. If `created_at` advances but `intrabar_resolved_at` does not → cause #4 (DB_PASS_BACKUPS) confirmed.

---

## CORRECTION / refined diagnosis (2026-06-19 ~02:20Z, after verification)

Split the two tables — they froze for DIFFERENT reasons:

- **`at_pick_outcomes`** (written by `universal_pick_resolver`): froze on the missing DB creds (cause #1). **FIXED — commit e45c434b7; verified fresh `resolved_at`=2026-06-19 01:12 on the next run.**
- **`at_signal_outcomes`** (the honest ledger I measure): **NOT a resolution backlog** — `reresolve_intrabar_signal_outcomes.py --apply` loaded **0 unresolved rows** (every existing row is already resolved). The freeze is that **no NEW rows have been inserted since 2026-06-12**. The inserter is the **`Active picks sync (LIVE)` step**, which has been **raising "0/1 EQUITY prices fetched — APPLY mode, refusing to proceed"** (correct safety halt) since 06-12 because **yfinance returns no prices on the GH runner** (AAPL is valid → it's a Yahoo cloud-IP rate-limit/block, not a symbol-format issue). So cause #4 (DB_PASS_BACKUPS) is NOT the at_signal_outcomes cause — **cause #2 (equity price source) is.**

### Corrected fix for the honest-ledger freeze (operator / deeper)
- Switch the active-picks-sync equity price fetch **off yfinance** to the keyed providers already in ENV (FINNHUB / FMP_API_KEY / TIINGO / ALPHAVANTAGE — see `reference-equity-prices-2026-verified`), with failover. yfinance is unreliable on GH-runner IPs.
- OR run `active_picks_sync` from a non-blocked host (local works) until the source is switched.
- The reresolve/`DB_PASS_BACKUPS` item is moot for the freeze (0 unresolved) — though still worth verifying the secret so the intrabar lane resolves new rows once the inserter resumes.

---

## CONVERGED FINAL ROOT CAUSE + COMPLETE FIX (2026-06-19 ~03:0xZ)

The honest-ledger freeze was **NOT** a yfinance outage, NOT DB_PASS_BACKUPS, NOT a code gap — it was a **secret-not-wired-to-env** plumbing miss:

- A peer added an **FMP equity-price fallback** to `active_picks_sync` on 2026-06-18 (`audit_trail/fetch_stock_prices`, yfinance→FMP) — the code on `main` is correct.
- BUT `FMP_API_KEY` (which the fallback reads via `os.getenv`) was **never added to the env of the active_picks_sync steps** in `outcome-resolver.yml` or `audit-dashboard.yml`. So the FMP fallback was silently disabled → only rate-limited yfinance → 0 equity prices → `active_picks_sync` safety-halts ("refusing to proceed") → outcome-resolver fails 6/6 → `at_signal_outcomes` frozen since 06-12.
- **The `FMP_API_KEY` secret EXISTS** (repo secret since 2026-06-06, with FINNHUB/ALPHA_VANTAGE). So **no operator action needed** — just the env wiring.

### Fix (complete, on main)
- `outcome-resolver.yml`: `FMP_API_KEY: ${{ secrets.FMP_API_KEY }}` wired onto the active_picks_sync step (`7a78863b5`).
- `audit-dashboard.yml`: same wiring onto its active-picks-sync step (`4451526a6`).
- Triggered `outcome-resolver.yml` to verify the un-freeze.

### Note
My local edit to `alpha_engine/active_picks_sync.py` (keyed-fetch-first) was **redundant** — `main` already had the equivalent FMP fallback. NOT committed to main (verified before commit; would have clobbered main's newer 172-line-diverged version). The real gap was purely the env wiring above.

### Verify
Next `outcome-resolver.yml` run should go green WITH equity prices fetched; `at_signal_outcomes max(created_at)` advances past 06-12; rows/day returns to ~5k; the `crypto_rsi5070_us` lead resumes accruing.

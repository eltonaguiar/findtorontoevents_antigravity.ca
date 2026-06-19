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

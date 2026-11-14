# 04 — FUTURES + COMMODITY consolidated peer review

Consolidation of 5 peers (read-only) on the 2026-11-14 audit.
Proposer keys: **v2** = finpredict-v2 · **v3** = finpredict-v3 QUICK_WINS · **v3-pr** = finpredict-v3 PEER_REVIEW · **v4** = finpredict-v4 · **v1** = finpredict (self).

---

## 1. Consensus

**Both classes: no sizing, no money-ready, do-not-trade.** Every peer independently concludes neither FUTURES nor COMMODITY has a validated closed sample and neither passes the system's own money-ready gate. Policy-frozen (money-ready `WATCH`/`INSUFFICIENT_DATA`, `sizing_allowed=false`).

**FUTURES = dead/blocked placeholder.** All peers: 3 OPEN seeds are gated placeholders (`_gate_passed=false`), **0 closed ever** in the primary feed, 0 live picks in `picks_now_live_pnl.json`. Date-only `entry_time`/`signal_time` (`"2026-11-14"`) breaks parsing → UI "no date". Frozen April prices (CL=F/GC=F/ZN=F) prove no mark-to-market. Duplicate emission (ES=F×3, YM=F×6). Do not size.

**COMMODITY = dead/deprecated (one dissent, §4).** v4-deep-dive "DEAD", v3-pr "deprecated/dead", money-ready "WATCH" (policy frozen). Only 4 live picks all ~156 days old (ZM/ZS/LE); 0 new emission since June. Policy-clean **n=14, PF 0.172**. Do not size.

**Cross-class root cause (agreed):** no quote-provenance contract — an unquoted row is published as `current_price == entry_price` and `pnl_pct = 0.0`. Applies to the frozen COMMODITY/FUTURES prices.

**`summary_picks.win_rate_pct` is arithmetically impossible** for both classes (FUTURES 363.9%, COMMODITY 240.2%) and must be suppressed until the denominator is fixed.

---

## 2. Unique per-peer

| Peer | Unique contribution |
|---|---|
| **v2** (forex_futures) | Richest FUTURES detail: line-verified P0-1 ISO entry-time, P0-4 weekend session guard, P0-5 exact-ID dedup, P1-5 futures closed-ledger (`recent_closed=0`), P1-6 retention contract. |
| **v2** (crypto_commodity) | COMMODITY canonical-class decision (P1-3 keep bucket + `canonical_asset_class="FUTURES"`), futures/commodity quote calendar (P1-6), P0-6 summary-WR fix, P1-8 publication discipline (single-source artifact). |
| **v3** (QUICK_WINS) | FUTURES QW-F1 hide gated rows, QW-F2 teach `_parse_timestamp` `%Y-%m-%d`, QW-F3 mark UNPROVEN. COMMODITY "ALIVE but unproven" (PA=F/SB=F match Friday close), avgScore 19<30, forward-validation tracking, feed-freshness label. |
| **v3-pr** (PEER_REVIEW) | Retire-vs-restart decision gate first; MISPRICED_ENTRY false positive (NG=F/CL=F now profitable); `cta_golden_cross_200` n=24 PF 10.87 is a single-strategy artifact; ML-audit has **no** futures/commodity `proposed_fixes/` folder (least-owned classes). |
| **v4** (deep_dive + dashboard + fixes) | `dashboard_data.json` **26 days stale** (ghost YM=F); money-ready gate table; intrabar truth; resolution backlog (6.2% resolution rate, `at_signal_outcomes` 80 days stale). Concrete RESTART path: unblock `BLOCKED_ASSET_CLASSES`, force-expire zombies, wire `commodity_signal_generator`, per-symbol daily cap (CT=F 6.33× over-emission). |
| **v1** (me) | FUTURES ISO fix targets `import_to_local_sqlite.py:73` / `import_backtest_trades.py:285`. COMMODITY backfill `current_price` at emit (`commodity_price_failover.py:387/:413`, `commodities_strategies.py:1026`); correction — peer path `copy_trader_intel/commodity_carry_momo.py` does not exist, real is `tools/research/commodity_carry_momo.py`. |

---

## 3. Consolidated fixes (deduplicated)

> "COMMODITY-vs-FUTURES canonical-class question": all 44 COMMODITY rows are `=F` with `contract_type="commodity_future"`; `alpha_engine.asset_class.normalize_asset_class()` returns `futures` for every one. v2's decision: **keep COMMODITY as a display bucket, add `canonical_asset_class="FUTURES"`, do NOT merge** (merge would double-count 7 closed rows already reclassifying COMMODITY→FUTURES and break the historical series). v3-pr/v4 favor treating COMMODITY as dead/rebuild — same end-state "no live commodity", different label.

| # | Fix | File + line | Effort / Risk | Proposer(s) |
|---|---|---|---|---|
| F1 | **Retire-vs-restart decision gate** (both classes) | n/a (operator decision) | S / — | v4, v3-pr, v3 |
| F2 | Emit full ISO timestamps; never date-only `entry_time`/`signal_time`; importer prefers full ts over `entry_date` | `copy_trader_intel/multi_asset_copytrader_scraper.py:452`; `audit_trail/dashboard_generator.py:8136-8154`; `audit_trail/universal_pick_resolver.py:743-755`; `audit_trail/import_to_local_sqlite.py:73`; `audit_trail/import_backtest_trades.py:285` | S / Low | v2, v3, v3-pr, v1 |
| F3 | Hide gated/placeholder rows (`_gate_passed=false`) from active panel | `audit_trail/dashboard_generator.py` (normalize/active-merge) | S / Low | v3, v1, v3-pr |
| F4 | **Quote-provenance contract**: stamp `quote_status`/`quote_source`/`quote_at`; render `UNQUOTED`/`STALE`/`LAST_CLOSE`; never leave `current==entry` unmarked | `audit_trail/dashboard_generator.py:1681-1688,1739-1755,1821-1822,17481-17485`; `audit_dashboard/template.html:8889-8905,8883-8887,9134-9145,9222-9227` | S / Low | v2, v3, v4, v1 |
| F5 | COMMODITY canonical-class shadow: add `canonical_asset_class="FUTURES"` + `COMMODITY_DISPLAY_BUCKET` flag + `FUTURES_ROLLUP` | `audit_trail/dashboard_generator.py:3286-3313,3418-3501,8343`; `alpha_engine/asset_class.py:214-215`; `alpha_engine/contract_type.py:1-14` | S–M / Low | v2 |
| F6 | **"Commodity uses crypto proxies"**: replace RNDRUSDT/ARBUSDT (silver) + XLMUSDT/DOTUSDT (oil) with real `=F` data (GC/SI/HG/CL) | `alpha_engine/commodity_signal_generator.py` | M / Med | v4 (2.3) |
| F7 | FUTURES closed-ledger: add `=F` price map, parse date-only as end-of-session, new `FUTURES_V2` cohort (never retro-edit) | `audit_trail/universal_pick_resolver.py:743-755,1294-1344,1460-1510` | L / High | v2 |
| F8 | Weekend/untradeable session guard for FUTURES emission (+holiday calendar P1) | `.github/workflows/multi-asset-scanner.yml:10,36-38`; `copy_trader_intel/multi_asset_copytrader_scraper.py:798-854,2700-2705` | M / Med-low | v2 |
| F9 | Dedup: exact-ID quarantine (S) then trade-key + UTC-day + entry-price window (M); per-symbol daily cap for COT over-emission | `audit_trail/dashboard_generator.py:17481-17485,9825-9877`; `audit_trail/quality_gates.py` (dedup gate) | S then M / Low | v2, v4 |
| F10 | Retention/quarantine of EXPIRED zombies (COMMODITY June 4; FUTURES 10 EXPIRED; YM=F ghost) out of counts; force-expire via 30-day cap | `audit_trail/dashboard_generator.py:9538,9540-9617,17481-17485`; `audit_trail/universal_pick_resolver.py:931-963` | S–M / Low | v2, v4, v3-pr |
| F11 | Suppress `summary_picks.win_rate_pct` for FUTURES/COMMODITY until denominator fixed (`wins/(wins+losses)` over one resolved set) | `tools/sync_summary_picks_json.py:63-65,161` | S / Low | v2 |
| F12 | Wire `commodity_signal_generator` into emission pipeline (zero emission since June) | `non_crypto_agent/main.py`; `alpha_engine/production_scanner.py` | M / Med | v4 (1.3) |
| F13 | Unblock FUTURES in `BLOCKED_ASSET_CLASSES` (RESTART path only) | `audit_trail/quality_gates.py:1724` | S / Med | v4 (1.1) — **contested, §4** |
| F14 | Data-freshness guard for futures yfinance (>2 trading days ⇒ skip); fix 26-day-stale `dashboard_data.json` | `alpha_engine/futures_strategies.py`; dashboard build | M / Low | v4 |
| F15 | Publication discipline: cohort labels (`policy-clean` vs intrabar) + `single_source_pct` + `SINGLE-SOURCE ARTIFACT`; downgrade WATCH→INSUFFICIENT_DATA when `policy_clean_n<30` | `audit_dashboard/template.html:908`; `alpha_engine/money_ready_verdict.py` | S / Low | v2, v4 |
| F16 | COMMODITY avgScore 19<30 threshold audit; forward-validation tracking (build closed sample) | `alpha_engine/config.py`; `alpha_engine/forward_validator.py` | L–M / Low | v3 |

---

## 4. Conflicts

1. **FUTURES end-state**: v4-fixes = **RESTART** (unblock; 4 academically-vetted strategies); v4-deep-dive + v3-pr + v3 = **retire OR decide first** ("formally retire or approve re-emission — nothing else proceeds"). Direct contradiction on the default action.
2. **COMMODITY status label**: v4-deep-dive "DEAD" vs money-ready "WATCH" vs v3 "ALIVE but unproven". Same substance (no edge, no sizing), different label.
3. **Cohort population**: v2 policy-clean **n=14 PF 0.17** vs v4 intrabar **n=229 PF 1.026** — different cohorts, same "no edge" conclusion.
4. **Date-only "no date" UI**: v1 confirms renders "no date"; **v2 says NOT REPRODUCED** (Playwright shows "Nov 14, 8:06 AM"). Version/render-path difference — re-verify.
5. **Active-pick count**: v4=0 (live tracker), v2=1 (curated ES=F), v1=3 (`active_raw`). Different layers; all agree "essentially no live futures".
6. **FUTURES WR surfaces**: `forwardWR=0.059` vs MRV 42.3% for same class — cohort conflict unresolved.
7. **COMMODITY canonical-class end-state**: v2 keep-bucket+canonical-field vs v3-pr/v4 treat-as-dead-and-rebuild.

---

## 5. UNVERIFIED

- **ES=F seed emitter origin** (v3): no single emitter located; `futures_strategies.py` emits proper ISO, so the date-only stub likely originates elsewhere.
- **avgScore 19<30** is threshold misapplication vs genuinely weak signals (v3).
- **Exact DB write** persisting `entry_time="2026-11-14"` (v2: MySQL row supplying it not traced).
- **CME holiday calendar** (v2: session guard covers weekends only).
- **Intraday fill granularity** for futures/commodity exits (daily-close reconstruction only) (v2, v3-pr).
- **Realized slippage/fill quality** — all entries are candidate prices, no live fills (v2).
- **MISPRICED_ENTRY false positive** for NG=F/CL=F — "likely" based on now-profitable live prices, not confirmed (v3-pr).
- **Visual rendering** of UNQUOTED/STALE/PLACEHOLDER badges — no browser pass run (v2).
- **`cta_cross_asset_tsmom` allowlist vs blacklist** (`non_crypto_policy.py:724` vs `config.py:298`) intent not reconstructed (v2).
- **ML-audit gap**: no futures/commodity `proposed_fixes/` folder exists (v3-pr) — least-owned classes.
- **Build-time cause of frozen prices** (CI egress failure vs ordering defect) not determinable from artifacts (v2).

---

## 6. P0 order

1. **Decision gate** — retire vs restart for both FUTURES and COMMODITY (blocks everything below). [v4, v3-pr]
2. **Quote-provenance contract** (F4) — stops fabricated 0.00% / `current==entry` on both classes. [v2]
3. **ISO timestamp + gated-row hiding** (F2 + F3) — cheapest code fix with a clear owner. [v2, v3, v1]
4. **Quarantine zombies** (F10) — COMMODITY June 4, FUTURES 10 EXPIRED, YM=F ghost; purge from counts, keep audit trail. [v4, v2]
5. **Suppress impossible WR** (F11) — FUTURES 363.9%, COMMODITY 240.2%. [v2]
6. **COMMODITY canonical-class shadow + crypto-proxy fix** (F5 + F6) — only if commodity is restarted. [v2, v4]
7. **Dedup** (F9) — exact-ID first, trade-key second. [v2, v4]
8. **Session + freshness guard** (F8 + F14) — only if futures is restarted. [v2, v4]

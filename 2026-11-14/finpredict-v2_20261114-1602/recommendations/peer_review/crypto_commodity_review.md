# FAIL — Peer Review: CRYPTO + COMMODITY plan (PR1)

**Verdict:** **FAIL** — as a CRYPTO+COMMODITY *implementation* plan.
The quote-provenance core (`P0-1`…`P0-7`) is evidence-backed, citation-clean, and safe to implement. The plan fails as a whole because its COMMODITY/FUTURES structural recommendation rests on an unverified premise, it omits the quality-gate block that actually governs both classes, and its peer-reconciliation section mischaracterises v4. Corrections are listed in §7.

**Reviewer:** Peer Reviewer PR1 · **Review window:** 2026-11-14T16:28–16:35Z
**Subject:** `recommendations/per_asset_class/crypto_commodity.md`, `recommendations/QUICK_WINS.md` (ranks 2,5,8,9,11), `recommendations/patch_plan/P0_QUICK_WINS.md` (P0-2/P0-5/P0-6/P0-8), `MASTER_AUDIT.md` §2/§5/§7.
**Peers read:** v1 `finpredict/2026-11-14T160004Z/updates/2026-11-14-prediction-system-audit.md`; v3 `finpredict-v3/2026-11-14T155500Z/updates/2026-11-14-prediction-data-hygiene.md`; v4 `audits/2026-11-14/finpredict-v4_2026-11-14-1555/{crypto_deep_dive,market_crossref_report,dashboard_data_report,INDEX}.md` + `proposed_fixes/{crypto,commodity}/QUICK_WINS.md` + `peer_review/PEER_REVIEW_INTEGRATION.md`; ML `updates/2026-11-14-ML-AUDIT-childlike-airport.md` + `proposed_fixes/crypto/FIX_PROPOSED.md`.

**Rule:** every `n` / PnL / WR / PF below is either re-read from the archived payload in this worktree or attributed to the named peer artifact. Peer claims not independently re-derived are marked `UNVERIFIED`. No number was invented.

---

## 1. What the plan gets right (so the FAIL is scoped)

| Item | Status | Independent check |
|---|---|---|
| Core diagnosis: unquoted rows are published as `current_price == entry_price` / `pnl_pct = 0.0` | **CONFIRMED** | `raw/dashboard_data.json` (generated `2026-11-14T14:30:07.135931+00:00`): `picks.active` n=20, **19** at `pnl_pct == 0`, **7** with exact `current_price == entry_price` |
| XRP/BTC frozen, NEAR genuinely marked | **CONFIRMED** | Archived Binance pulls: XRP **0.9713**, BTC **65688**, NEAR **3.197**; NEAR entry 3.324 → **+3.82% SHORT** |
| `picks.active_raw` = 4,148 rows, 3,577 CRYPTO / 402 OPEN / 3,100 EXPIRED | **CONFIRMED** | recomputed from `raw/dashboard_data.json` |
| COMMODITY = 44 raw, **27 OPEN / 16 EXPIRED**, all `=F`, all `contract_type=commodity_future` | **CONFIRMED** | recomputed; matches `crypto_commodity.md:18` |
| `summary_picks` impossible WR (COMMODITY 240.2%, CRYPTO 98.3%, FUTURES 363.9%) | **CONFIRMED** | `raw/summary_picks.json`: COMMODITY 1,447 resolved / 3,476 W / 3,466 L / 240.2 |
| Policy-clean registry numbers used by the plan | **CONFIRMED** | `raw/pf_registry.json::by_asset_class_policy_clean_net`: CRYPTO n=**21,988** WR **42.3504** PF **0.259472** single-source 0.989494; COMMODITY n=**14** WR **14.2857** PF **0.171816** single-source 0.642857 |
| Zero-entry XRP phantom and `prediction_market_consensus` merge coercion | **CONFIRMED** | `alpha_engine/prediction_market_consensus.py:589-591` (`or 0`); `:161` returns `(0.0, 0.0, 0.0)` on failure |
| Inverse-mutation zombie factory | **CONFIRMED** | `alpha_engine/inverse_strategies.py:405` (`now_str = %Y-%m-%d`), `:436` (date-only `pick_id`) |

---

## 2. Reconciliation table — CRYPTO + COMMODITY

Legend: **AGREE** = same finding/evidence; **CONTRADICT** = mutually incompatible; **PARTIAL** = agrees on data but differs on population/interpretation; **UNVERIFIED** = peer claim not independently re-derived.

| # | Claim | v1 (finpredict) | v2 (ours) | v3 (hygiene) | v4 | ML (childlike-airport) | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | CRYPTO curated panel is 20 rows / 3 crypto; raw 4,148 | 20 | 20 / 3 / 4,148 | 20 | **20 / 3** in `crypto_deep_dive.md`; **0 active** in `INDEX.md` | 273 deduped across JSON feeds (different population) | **PARTIAL / v4 self-contradiction** | `raw/dashboard_data.json` active=20, raw=4,148; v4 `crypto_deep_dive.md:13-16`; v4 `INDEX.md:45` |
| 2 | `dashboard_data.json` fresh (~14:30Z today) | 14:30:07Z | 14:30:07Z | 14:30Z | **14:30:07Z** (`crypto_deep_dive`, `dashboard_data_report`); **26 days old** (`INDEX.md:65`) | `dashboard/live_picks.json` 2 d | **PARTIAL / v4 self-contradiction** | archived `generated_at`; v4 `INDEX.md:65` vs v4 `crypto_deep_dive.md:5` |
| 3 | XRP/BTC price pinned at entry while market moved | yes (0.9742 / 65,839) | yes | yes | yes (0.9698 / 65,658) | not this surface | **AGREE** | `raw/dashboard_data.json`; `raw/binance_price_{XRPUSDT,BTCUSDT}.json` |
| 4 | NEAR is genuinely marked; dashboard understates by ~0.7 pp | +3.07% | +3.1–3.8% | yes | +3.46% | no | **AGREE** | Binance NEAR 3.197 → +3.82% vs dashboard 3.233 → +2.74% |
| 5 | CRYPTO "honest" performance | PF 0.29 registry vs 0.95 money-ready | PF **0.2595** / WR **42.35%** (policy-clean), 0.92 / 35.87% (intrabar) | **PF 0.98 / WR 39.7%** policy-clean-net; money-ready 0.96 / 31.3% | intrabar n=3,705, WR **35.9%**, PF **0.92**; dashboard recent_closed PF **1.801** vs raw DB **0.371** | not this surface | **CONTRADICT (v3)** + **PARTIAL (v4)** | `raw/pf_registry.json` = 0.259472 / 42.3504; `raw/money_ready_verdict.json` intrabar = 0.9196 / 0.3587. v3's 0.98 / 39.7 **UNVERIFIED** and not reproducible from archived payload |
| 6 | Dashboard inflates CRYPTO PF ~5× over raw DB | notes CRYPTO PF 0.29 vs 0.95 | **NOT PRESENT** | notes `claude_gainer_st` EXPIRED→WON mislabels | **yes: 1.801 vs 0.371**; Smart Picks PF 9.69 on 3 rows (91.7% one source) | no | **v2 MISSED**; v4 has evidence | v4 `dashboard_data_report.md:116-125`; `evidence_pick_summary_stats.json` contains `1.801`, `0.371`, `9.69`, `claude_gainer_st` (verified substring) |
| 7 | COMMODITY policy-clean vs intrabar | headline closed 42.9% / −4.2% (different pop) | policy-clean **14 / 14.29% / 0.1718**; intrabar 229 / 40.17% / 1.0256 | not explicit | intrabar **229 / 40.2% / 1.026**, verdict WATCH in money-ready but **FAIL** in `dashboard_data_report.md:46` | COMMODITY 5 active / 560 closed (different DB) | **AGREE on numbers; CONFLICT on verdict/currency** | `raw/pf_registry.json`, `raw/money_ready_verdict.json`; v4 `dashboard_data_report.md:46,172` |
| 8 | COMMODITY + FUTURES are administratively blocked | not mentioned | **NOT MENTIONED** | not mentioned | **yes** — unblock FUTURES (`proposed_fixes/commodity/QUICK_WINS.md:12-17`); COMMODITY called frozen | not mentioned | **v2 MISSED (material)** | `audit_trail/quality_gates.py:1724` = `{"FOREX","COMMODITY","FUTURES","BOND"}` (verified) |
| 9 | COMMODITY rows are futures | yes | yes (44/44 `=F`) | no | "4 zombie picks, ~156 d" (different pop) | 5 active / 560 closed (different pop) | **AGREE within population; peer populations differ** | recomputed 44 raw / 27 OPEN / 16 EXPIRED / 44 `=F`; v4 commodity proposal is `live_picks`/`picks_now` scope |
| 10 | AI Challenge crypto registry is months-old zombies | partly (raw timestamps 240 d) | **only AI top-picks sidecars ~245 d; not the registry** | no | **yes** — 5 crypto picks 2026-03 still OPEN, 0% PnL, TP/SL breached | no | **v2 PARTIALLY MISSED** | `audit_dashboard/data/ai_challenge_antigravity_active_picks.json`: **9 rows, all `current_price=None`, `pnl_pct=0.0`, `status=OPEN`, no timestamp fields** (verified); v4 `market_crossref_report.md:49-68,134-145`; v4 crypto QW-3 |
| 11 | Zero-entry XRP phantom | yes | yes | yes | not in crypto_deep_dive | no | **AGREE** | `prediction_market_consensus.py:589-591` verified |
| 12 | Edge/Track/FWD columns dead | yes | yes (`sym_track_total` 0 on 20/20) | yes | `forward_wr/trades=0`, `sym_track_total=0`, **but `sym_dir_fwd_wr` populated** (50.0 / 51.7 / 39.1; n=82/60/46) | no | **AGREE with v4 refinement** | v4 `crypto_deep_dive.md:171-183`; our `P0-6` already prefers `sym_dir_fwd_*` |
| 13 | ML confidence is inverted | no | **NOT MENTIONED** | no | **yes** — `conf≥0.90 → 14.4% WR; 0.50–0.60 → 60.3%` (`INDEX.md:113`; crypto MF-2) | ML code sound; says gap is **data**, not code (`PEER_REVIEW_INTEGRATION.md:33`) | **v2 MISSED; peer-internal consistent if data-level** | Exact 14.4/60.3 figures **UNVERIFIED**; general inverted/U-shape pattern independently exists in repo history (`memory/2026-05-17.md:6`, `swarm_runs/.../quant_audit.agent.final.md:243`) |
| 14 | `live_picks.db` crypto: 101 stale + PnL sign/calc bugs + `CRYPTO`/`crypto` case-dup | no | **NOT MENTIONED** | no | integrated as new in `PEER_REVIEW_INTEGRATION.md:11-25` | **yes** — 101 crypto active ~172 d stale; 8 sign contradictions, 15 calc mismatches; closed 6,400 + 1,348 case-duplicated | **v2 MISSED** | ML audit §3.1–3.7; ML `proposed_fixes/crypto/FIX_PROPOSED.md:9-37,62-64` |
| 15 | `summary_picks` WR > 100% | yes | yes (7 named) | yes | not central | no | **AGREE** | `raw/summary_picks.json` verified |
| 16 | Multiple testing / survivorship / 0-of-9 money-ready | yes | yes | yes | yes | yes | **AGREE** | all peers; our `raw/pf_registry.json`, `raw/money_ready_verdict.json` |
| 17 | COMMODITY generator uses crypto proxies | no | **NOT MENTIONED** | no | **yes** — RNDR/ARB as "silver", XLM/DOT as "oil" | no | **v2 MISSED** | `alpha_engine/commodity_signal_generator.py:231-238` (`silver_proxies = ["RNDRUSDT","ARBUSDT"]`), `:250` (`wti_symbols = ["XLMUSDT","DOTUSDT"]`) — verified |
| 18 | Intrabar truth (`at_signal_outcomes`) is stale | no | uses intrabar n=229 as "honest" without staleness caveat | no | **yes**, but **internally contradictory age**: 80 d (`dashboard_data_report.md:86-89`) vs 254 d (`INDEX.md:68`) | no | **v2 MISSED caveat; v4 age UNVERIFIED** | v4 conflict: 115,782 min ≈ 80.4 d vs "last resolved 2026-03-04" ≈ 255 d |

**Reading the table:** the numeric core (rows 1–5, 7, 9, 11, 15, 16) is sound and mostly agrees. The failures are (a) v4 internal contradictions the plan handled asymmetrically, (b) four material classes of peer findings the plan never reaches: quality-gate block (row 8), AI Challenge registry (10), ML confidence inversion (13), `live_picks.db` (14), and commodity proxies (17), and (c) the staleness of the "honest" intrabar source the plan relies on (18).

---

## 3. Peer recommendations our plan MISSED

| # | Peer rec (source) | Why it matters for CRYPTO/COMMODITY | Status in our plan |
|---|---|---|---|
| M1 | **Unblock FUTURES in `BLOCKED_ASSET_CLASSES`** and re-run the 4 vetted futures strategies (v4 commodity QW-1.1) | Both COMMODITY *and* FUTURES are in `{"FOREX","COMMODITY","FUTURES","BOND"}` (`quality_gates.py:1724`). Our `P1-3` treats COMMODITY as a live display bucket and proposes canonical-class plumbing without acknowledging that the class is administratively frozen. This changes the whole structural recommendation. | Absent |
| M2 | **COMMODITY generator uses crypto proxies** — RNDR/ARB for silver, XLM/DOT for oil (v4 commodity 2.3) | Labelling these rows `canonical_asset_class="FUTURES"` (our `P1-3`) would assert commodity exposure that does not exist. The row is a crypto Bollinger-band signal wearing a commodity label. | Absent |
| M3 | **COT over-emission / CT=F `DSR=1.0` falsification**; enforce 1 pick per `(symbol,strategy,direction)/day` (v4 commodity 2.1) | COMMODITY's historical series and any DSR/PF built on it are contaminated. Our `P1-8` label change does not address the source. | Absent |
| M4 | **Purge/expire AI Challenge crypto registry** (9 OPEN rows, null price, 0% PnL, no timestamps; v4 found several TP/SL breaches — BTC/SOL/TRX past TP, NEAR past SL) (v4 market_crossref; v4 crypto QW-3) | Verified in-repo: `audit_dashboard/data/ai_challenge_antigravity_active_picks.json` has 9 OPEN rows with `current_price=None`, `pnl_pct=0.0`, no timestamp. It is a separate registry from `picks.active_raw`; our plan does not scope it in or out. | Absent |
| M5 | **Fix `live_picks.db` crypto PnL sign/calc + 101 stale rows + `CRYPTO`/`crypto` case-dup** (ML audit; ML crypto FIX_PROPOSED) | A third data layer (SQLite) with 101 crypto rows whose `unrealized_pnl_pct` sign is wrong, and case-duplicated closed classes (6,400 + 1,348). Our plan only touches dashboard JSON. | Absent (mentioned only as a side bullet in `QUICK_WINS.md:30`, not in the CRYPTO/COMMODITY plan) |
| M6 | **Fix CRYPTO dashboard PF 5× inflation / Smart-Picks PF 9.69 on 3 rows** (v4 `dashboard_data_report.md:116-125`; crypto QW-2/MF-3) | `evidence_pick_summary_stats.json` contains 1.801 (dashboard) and 0.371 (raw). Our plan's `P1-8` labels the *policy-clean* number but does not stop the dashboard aggregation from republishing the inflated number. | Absent |
| M7 | **Fix/verify inverted ML confidence** (v4 `INDEX.md:113`, crypto MF-2; corroborated historically) | If `conf≥0.90` really wins 14.4% and `0.50–0.60` wins 60.3%, the gatekeeper is anti-selecting; high-conviction crypto picks are the worst. Our plan has no ML-calibration item. Exact figures `UNVERIFIED`, but the inverted/U-shape pattern is independently present in repo history. | Absent |
| M8 | **CI data-contract test** — add `dashboard PF == ledger PF ± tol`, `MAX(crypto pick age)`, `confidence-bucket monotonicity` (v4 crypto LF-3) | Our plan has build-time assertions and a quote-coverage gate, but no PF-parity or confidence-monotonicity gate. | Partially covered (quote coverage only) |
| M9 | **Reconcile three divergent data layers** (SQLite / MySQL / dashboard JSON) (v4 `PEER_REVIEW_INTEGRATION.md:46-48`) | Counts, ages, PnL differ per layer. Our plan assumes the JSON layer is canonical without saying so. | Absent |
| M10 | **Disclose `_backfilled`, `_emitter_registry_would_block`, RSI/oversold crowding, `sym_dir_fwd_*`** on the 3 crypto picks (v4 `crypto_deep_dive.md:49-119,288-296`) | All 3 curated crypto picks are `_backfilled: true`; all 3 `_emitter_registry_would_block: true` with `enforce_block: false`; all SHORT with entry RSI 19.9/30.7/24.6. Our plan's "fresh signal" framing does not disclose backfill or governance bypass. | Absent |

---

## 4. Our recommendations that CONFLICT with peer evidence

| # | Our rec | Conflict | Severity |
|---|---|---|---|
| C1 | `MASTER_AUDIT.md:349,372` — "v4 claims 0 curated active picks / 26-day-old dashboard" and treats v4 as contradicted | v4 is **self-contradictory**, not uniformly wrong. `crypto_deep_dive.md:13-16` says **20 active / 3 crypto** and `generated_at 14:30:07Z`; only `INDEX.md:45,65` says 0 active / 26 days. Our blanket reconciliation discards the v4 artifact that agrees with us and overstates the contradiction. | High (undermines trust in the reconciliation) |
| C2 | `P1-3` — keep COMMODITY as a live display bucket, add `canonical_asset_class=FUTURES`, plan a `FUTURES_ROLLUP` | COMMODITY is in `BLOCKED_ASSET_CLASSES` (`quality_gates.py:1724`) and its generator emits **crypto proxies** (`commodity_signal_generator.py:233,250`). A display bucket for a gate-blocked, crypto-proxy class will present synthetic exposure as a real asset class. | High |
| C3 | `P1-8` — "COMMODITY is `WATCH` on intrabar n=229 WR 40.17% PF 1.0256" presented as an honest current statistic | v4 reports `at_signal_outcomes` **has not resolved since 2026-03-04** (either ~80 d or ~255 d — v4 is internally inconsistent; `UNVERIFIED`). Either way, n=229 is a frozen historical cohort, not current. Presenting it as the live "honest" number is misleading. | High |
| C4 | Plan uses **PF 0.2595 / WR 42.35%** as CRYPTO's honest policy-clean figure | v3 reports **PF 0.98 / WR 39.7%** for "policy-clean-net" and money-ready **0.96 / 31.3%**. Our archived `pf_registry` and `money_ready_verdict` do **not** reproduce v3's numbers. Two different "honest" crypto numbers are circulating; the plan must state the cohort and reject or reconcile v3's. | Medium |
| C5 | `MASTER_AUDIT.md:101` — "FUTURES … 0 closed ever" | True only for `picks.recent_closed` (verified: 0 rows). The full history has **n=13** policy-clean FUTURES (`raw/pf_registry.json`). The same MASTER_AUDIT table (line 120) lists FUTURES n=13, an internal contradiction. | Medium (wording) |
| C6 | `P1-7` — "add a new `meta` key; there is no `meta` block today" | The payload already has a `metadata` block (`dashboard_generator.py:16852`). The proposed `payload["meta"]["features"]` would create a second, near-duplicate namespace. Either extend `metadata` or say why a separate `meta` is required. | Low |
| C7 | `P0-1` root cause framing attributes the freeze to an enrichment miss/timing in `dashboard_generator.py` | v4 crypto QW-1 attributes it to `universal_pick_resolver.py` / `fetch_stock_prices.py` returning `None` for crypto. Our archived re-run evidence (`_fetch_prices_with_failover` resolves 3/3) favours our framing, but the plan should explicitly reject v4's attribution rather than leave two root causes in the record. | Low–Medium |

---

## 5. Citation spot-check (21 citation entries; `grep -n` / `read` in `finpredict-v2`)

| Citation | Claimed | Actual | Verdict |
|---|---|---|---|
| `audit_trail/dashboard_generator.py:1618` | `_enrich_live_pnl` | `def _enrich_live_pnl(picks: list) -> list:` at 1618 | **VALID** |
| `dashboard_generator.py:1739-1755` | miss path `continue` | comment "keep the pick untouched instead of writing a fabricated 0%" at 1754, `continue` at 1755 | **VALID** |
| `dashboard_generator.py:9596-9605` | auto-expire writes `EXPIRED` / `STALE` / `expired_no_pnl` | exactly present | **VALID** |
| `dashboard_generator.py:9722-9723` | `entry_price=0` allowed | comment present at 9722-9723 | **VALID** |
| `dashboard_generator.py:9538` | `active_raw` pre-enrichment snapshot | `active_raw_snapshot = list(active)` | **VALID** |
| `dashboard_generator.py:14551` | `_enrich_live_pnl(active)` call site | present | **VALID** |
| `dashboard_generator.py:9825-9877` | `_dedup_picks` 4-tuple key | `def _dedup_picks` at 9825 | **VALID** |
| `dashboard_generator.py:3286-3313`, `:8343` | `_COMMODITY_ROOTS`, `contract_type` stamp | both present | **VALID** |
| `audit_dashboard/template.html:5075` | `fmtPct` | `const fmtPct = ...` at 5075 | **VALID** |
| `template.html:8883-8887`, `:8889-8905` | status `FLAT`; PnL cell formatter | both present | **VALID** |
| `template.html:9134-9145` | Current cell green live dot | `liveIcon = p._livePrice ? ...` at ~9139 | **VALID** |
| `template.html:5628` | tile "20 of 4,148" | `_activePicksValue` "of N" at 5628-5630 | **VALID** |
| `tools/sync_summary_picks_json.py:63-65`, `:161` | three SUMs; `win_rate_pct = 100*wins/resolved` | both present | **VALID** |
| `alpha_engine/prediction_market_consensus.py:589-591` | `entry_price/tp/sl = ... or 0` | present | **VALID** |
| `prediction_market_consensus.py:160` | "returns 0.0 on total price failure" | the `(0.0, 0.0, 0.0)` return is at **161**; 160 is the `round()` return | **MINOR DRIFT (−1 line)** |
| `genome/mape_evolver.py:497-511` | pick dict with no `entry_price` | present (no entry key) | **VALID** |
| `alpha_engine/asset_class.py:214-215` | `=F → futures` | present | **VALID** |
| `schema-baseline.sql:6072-6094` | `trading_picks` has no quote columns | present | **VALID** |
| `alpha_engine/inverse_strategies.py:436` | date-only `pick_id` | present | **VALID** |
| `inverse_strategies.py:410` | `now_str` | `now_str` is at **405**, not 410 (410 is `for pick in candidates:`) | **DRIFT (−5 lines)** |
| `alpha_engine/scanner.py:2937-2942` | `_forex_by_sym` plain dict + append | present | **VALID** |

**Result:** 21 checks; **2 drifted** (`inverse_strategies.py:410`, `prediction_market_consensus.py:160`), **0 invalid**. No citation points at a non-existent function or a different subsystem. The two drifts are line-number slips only and do not change the recommendation.

---

## 6. Recent-file scan (`find -newermt "2026-11-14 15:30"`, excluding `.git`, `node_modules`, `.kilo/worktrees`)

New crypto/commodity audit artifacts and incorporation status:

| Artifact | Status vs our plan |
|---|---|
| `audits/2026-11-14/finpredict-v4_.../proposed_fixes/crypto/QUICK_WINS.md` | **NOT incorporated** — 5× PF inflation (QW-2), AI Challenge zombie purge (QW-3), inverted ML confidence (MF-2), Smart-Picks n=3 gate (MF-3) |
| `audits/2026-11-14/finpredict-v4_.../proposed_fixes/commodity/QUICK_WINS.md` | **NOT incorporated** — `BLOCKED_ASSET_CLASSES` unblock (1.1), zombie expiry (1.2), generator wiring (1.3), COT daily cap (2.1), crypto-proxy replacement (2.3) |
| `audits/2026-11-14/finpredict-v4_.../crypto_deep_dive.md` | **Partially incorporated** — price/age data used; `_backfilled`, `_emitter_registry_would_block`, RSI oversold, `sym_dir_fwd_*` governance flags missing |
| `audits/2026-11-14/finpredict-v4_.../market_crossref_report.md` | **Partially incorporated** — AI Challenge registry resolution missing |
| `audits/2026-11-14/finpredict-v4_.../peer_review/PEER_REVIEW_INTEGRATION.md` | **NOT incorporated** — three-way SQLite/MySQL/JSON divergence |
| `audits/2026-11-14/finpredict-v4_.../dashboard_data_report.md`, `dashboard_metrics_sources.md`, `evidence_*.json` | Evidence only; the PF-inflation and at_signal_outcomes staleness findings are **NOT incorporated** |
| `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/crypto/FIX_PROPOSED.md` | **NOT incorporated** — `live_picks.db` 101 stale crypto, sign/calc bugs, case-dup |
| `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/overall/FIX_PROPOSED.md` | **NOT incorporated** |
| `updates/2026-11-14-ML-AUDIT-childlike-airport.md` | **Partially incorporated** — only the `live_picks.db` side bullet in `QUICK_WINS.md:30` |
| `bestiejob/*`, `.kilo/agent-manager.json`, `logs/*`, `reports/*`, `tools/ai_menu.sh`, `___HELL_HEALTH_OPENCODE.MD` | Unrelated (job board / runtime state); no action |

No new crypto/commodity **audit artifact** was found that our plan already fully covered. The two `proposed_fixes/{crypto,commodity}` files are the highest-value uncaptured material.

---

## 7. Ranked "must-fix before implementation"

| Rank | Must-fix | Why it blocks implementation | Owner |
|---:|---|---|---|
| **1** | Add `BLOCKED_ASSET_CLASSES` to the COMMODITY/FUTURES model and reconcile `P1-3`. `quality_gates.py:1724` blocks **both** classes. Decide explicitly: (a) keep COMMODITY as a *quarantined, labelled* bucket, or (b) unblock FUTURES per v4 and rebuild COMMODITY from real futures data. Do not ship canonical-class plumbing that implies live commodity exposure. | The current `P1-3` premise ("keep the bucket") is false in the live gate and would mislabel crypto-proxy signals. | Plan author |
| **2** | Qualify or remove the `P1-8` COMMODITY "WATCH on intrabar n=229" claim. Add the `at_signal_outcomes` staleness (v4 says last resolved 2026-03-04; age reported as both 80 d and 255 d) as a precondition before publishing any intrabar statistic. `UNVERIFIED` age must be resolved. | Publishing a frozen 229-row cohort as the honest edge is the same failure mode the plan is trying to fix. | Plan author + data owner |
| **3** | Correct the v4 reconciliation in `MASTER_AUDIT.md:349,372`. State that v4 is internally contradictory (INDEX: 0 active / 26 d; deep dives: 20 active / today's payload). Do not characterise "v4" monolithically. | Our own peer table is the evidence base for the merge; an unfair reconciliation discredits the plan. | Plan author |
| **4** | Add the missing crypto surfaces as explicit scope: (a) AI Challenge registry (9 OPEN/null/no-timestamp rows), (b) `live_picks.db` 101 stale crypto + sign/calc bugs + case-dup, (c) dashboard PF 5× inflation / Smart-Picks n=3, (d) inverted ML confidence (verify first). Either include fixes or add a "known out-of-scope, do not claim covered" section. | These are the same "fake flat / inflated" defects on other publishing paths; leaving them out means the audit under-reports the real blast radius. | Plan author |
| **5** | Reconcile the two "honest" CRYPTO numbers. Our plan uses `pf_registry` 21,988 / 42.35% / 0.2595; v3 claims 0.98 / 39.7% policy-clean-net and 0.96 / 31.3% money-ready. Archived payload reproduces **only** 0.2595 / 42.3504 (policy-clean) and 0.9196 / 35.87% (intrabar). Mark v3's numbers `UNVERIFIED` or explain the cohort. | Two "honest" baselines will produce two different go/no-go decisions. | Plan author |
| **6** | Fix the two citation drifts and the `P1-7` namespace claim: `inverse_strategies.py:410 → 405`; `prediction_market_consensus.py:160 → 161`; `dashboard_generator.py:16850` already has `metadata`, so extend it rather than add a second `meta`. Also scope `MASTER_AUDIT` "FUTURES 0 closed ever" to `recent_closed` (0) vs full history (n=13). | Low-risk but cheap; the plan advertises "verified with `grep -n`", so drifts undermine that claim. | Plan author |
| **7** | Add the COMMODITY provenance finding (RNDR/ARB silver proxies, XLM/DOT oil proxies) and the COT over-emission cap to the COMMODITY section, even if the fix is deferred. | `canonical_asset_class="FUTURES"` on a crypto-proxy signal is a materially false provenance claim. | Plan author + commodity owner |
| **8** | Add a CI contract test (PF parity, crypto max age, confidence monotonicity, quote coverage) instead of manual validation snippets only. | Without a gate, the next build can silently regress exactly as the 14:30Z build did. | Plan author + CI owner |

**Scope note:** `P0-1`…`P0-7` may proceed **now** — they are additive, reversible, citation-accurate, and independently verified. The FAIL applies to the COMMODITY/FUTURES structural layer (`P1-3`, `P1-8`) and to the completeness of the peer reconciliation.

---

## 8. UNVERIFIED markers (do not treat as facts)

- **`at_signal_outcomes` staleness age** — v4 says 80.4 d (`dashboard_data_report.md:86-89`, 115,782 min) and 254 d (`INDEX.md:68`, last resolved 2026-03-04). Both cannot be right; neither was queried independently. `UNVERIFIED`.
- **v3's CRYPTO policy-clean-net PF 0.98 / WR 39.7% and money-ready PF 0.96 / WR 31.3%** — not reproducible from the archived `pf_registry.json` (0.2595 / 42.3504) or `money_ready_verdict.json` (0.9196 / 35.87%). `UNVERIFIED`.
- **v4's exact ML confidence bands** (`conf≥0.90 → 14.4% WR`; `0.50–0.60 → 60.3% WR`) — the inverted/U-shape pattern is corroborated by repo history, but these exact figures were not recomputed. `UNVERIFIED`.
- **v4 AI Challenge "245 days / 2026-03"** — the repo file has **no timestamp fields**; the broken state (9 OPEN, null price, 0% PnL) is **verified**, the precise age is `UNVERIFIED`.
- **v4 QW-1 root cause** (`universal_pick_resolver.py` / `fetch_stock_prices.py` returning `None`) — speculative ("likely"); our archived re-run resolves 3/3 symbols via the dashboard fetcher. `UNVERIFIED` and probably wrong.
- **Whether `current_price == entry_price` with `pnl=0` is an intentional sentinel** — still `UNVERIFIED` (carried from our own plan).
- **v4 dashboard PF 1.801 / raw 0.371** — the numbers are present in `evidence_pick_summary_stats.json` (substring-verified), but I did not re-derive them from the raw DB. Peer evidence accepted, `UNVERIFIED` as an independent computation.

---

*Prepared by Peer Reviewer PR1. Read-only review — no repo source was modified. Every recomputation used `raw/dashboard_data.json` (`generated_at 2026-11-14T14:30:07.135931+00:00`), `raw/pf_registry.json`, `raw/money_ready_verdict.json`, `raw/summary_picks.json`, or `raw/binance_price_*.json` from this archive.*

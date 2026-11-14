# RR3 — Review: live-browser validation, v4 rewrite, miscellaneous peer updates

**Reviewer:** RR3
**Clock:** 2026-11-14T18:38Z (live probes 18:41–18:46Z)
**Scope:** `finpredict-v3/2026-11-14T175500Z` live-browser artifact; rewritten
`audits/2026-11-14/finpredict-v4_2026-11-14-1555/INDEX.md` (18:05); hilarious-seer quickwins;
flaxen-hair update. Reviewed against our archive (`2026-11-14/finpredict-v2_20261114-1602/`).
**Rule:** no repo source modified. All live checks were read-only HTTP/browser probes from `/tmp/kilo`.

---

## VERDICT: **FAIL — not merge-ready as a package**

| Component | Merge-readiness | Reason |
|---|---|---|
| Live-browser validation + spec | **PASS (adopt with edits)** | Independently reproduced; every named finding confirmed. Counts differ only by retry depth. |
| v4 `INDEX.md` (18:05 rewrite) | **FAIL** | Resolves the "0 active / 26-day" headline but still self-contradicts at `:43`, `:92`, `:94`; the per-class "Live Picks" column is backlog, not the panel; P0-4 root cause is contradicted by the live run. |
| hilarious-seer quickwins | **FAIL as standalone** | 2–5 line summaries, no `file:line`, no evidence files. Corroboration only (PF4 already ruled the same at 17:57Z). |
| flaxen-hair update | **PASS (findings) / conditional** | PnL-unit recomputation is the strongest new evidence; §1/§8 self-contradict on `dbpasses.txt`; two recommendations must be vetoed. |

Do not copy v4 `INDEX.md` or the hilarious-seer quickwins into the master plan verbatim. The
live-browser findings and flaxen-hair's PnL-unit evidence **should** be merged after the edits in §7.

---

## 1. Live-browser findings — independently reproduced

Method: same three live URLs, headless Chromium 1.58.2, 5 s settle after `networkidle`; one extra
pass with a `response` listener for HTTP ≥ 400.

| ID | Finding | Peer claim | RR3 check (18:41–18:46Z) | Repro |
|---|---|---|---|---|
| L1 | Homepage uncaught React error | pageErrors 1, console 4, failed 12 | **pageErrors 1, console 4, failed 12 — exact match** | **Yes, 3/3 loads (peer + 2 RR3)** |
| L2 | React #418 identity | "hydration error #418" | `Error: Minified React error #418 … args[]=HTML` thrown from `https://findtorontoevents.ca/next/_next/static/chunks/dde2c8e6322d1671.js` | **Yes, deterministic** |
| L3 | Homepage 400s | "two 400 responses" | 2× `googleads.g.doubleclick.net/pagead/ads` (slot `1234567890`, `0987654321`) | **Yes** |
| L4 | Homepage 404s | "two 404 resource loads" | 1× `findtorontoevents.ca/sites/default/files/styles/4_5_l_1x/public/event/thumbnail/_d7l3285.jpg.webp` (+ favicon-class 404) | **Yes** |
| L5 | Homepage failed requests | 12, `__hp-blocked` images + ads | 10× `nowtoronto.com/.../__hp-blocked` `ERR_BLOCKED_BY_ORB` + 1× `pagead2…/ping` `ERR_ABORTED` + 1 timing abort | **Yes** |
| L6 | Audit dashboard uncaught errors | 0 | **0 pageErrors**; body 29,185 chars; 2,551 table rows; 211-control click test alive | **Yes** |
| L7 | Audit CORS/feed blocks | cryptocompare HYPE + allorigins/KuCoin | **Confirmed**: 4× cryptocompare `histohour?fsym=HYPE` `No 'Access-Control-Allow-Origin'`, 4× `api.allorigins.win/raw?url=…api.kucoin.com…HYPE-USDT` `ERR_ABORTED` | **Yes** |
| L8 | Audit console/failed counts | 5 console / 4 failed | **9 console / 8 failed** (same composition; peer captured one retry cycle, RR3 two). No new failure class. | **Yes, variance explained** |
| L9 | NEW — audit missing sidecar | not listed | `404 /audit/data/strategy_tribunal_latest.json` (console error #0). Producer exists (`tools/strategy_kill_tribunal.py:181-183`) but the file is neither committed nor deployed. Page degrades gracefully: `template.html:1021-1026` prints "No tribunal report yet — runs Fridays 14:00 UTC". | **Yes** |
| L10 | HyroTrader | 0/0/0 clean | **0 pageErrors / 0 console / 0 failed**, 36,760 chars | **Yes** |

### 1.1 Severity corrections to the peer narrative (important)

The peer doc over-reads two items. Both are real errors but **lower severity** than written:

1. **React #418 does not blank the homepage.** The peer says "React root fails to hydrate, so
   interactive widget(s) on the homepage are broken/empty for end users." Observed: the page still
   renders 51 event/ticket links, 26 images, 14,065 chars. The failure is the Next.js island under
   `/next/` (`dde2c8e6322d1671.js`), and React #418 itself says the client will re-render that tree.
   **Correct claim:** deterministic hydration mismatch in the embedded `/next/` event-grid bundle;
   user-visible loss is unproven. **UNVERIFIED** whether any control is non-functional.
2. **The HYPE CORS failures are optional-enrichment failures, not empty widgets.** The widget is
   `fetchBinanceKlinesWithFailover()` (`audit_dashboard/template.html:18042-18109`). HYPE is
   deliberately skipped on Binance (`_NOT_ON_BINANCE`, `:18040`), the KuCoin-via-allorigins proxy is
   tried next, CryptoCompare is the last fallback, and the function ends `return [];` with the comment
   "Fail silently - RSI/sparklines are optional enrichment" (`:18115`). **Correct claim:** HYPE
   symbol-card chart/RSI sparkline is unavailable; the dashboard's picks table and PnL are unaffected.
   Also note HYPE is **not** in the current curated panel (0 active; 17 raw; 6 recent-closed).

### 1.2 Spec quality — MERGE, do not add a second spec

The new `tests/audit_live_js_errors_spec.ts` duplicates a stronger existing spec,
`tests/audit_js_errors_kimi411.spec.ts`:

| Capability | New spec | Existing kimi411 spec |
|---|---|---|
| Env-overridable base URL | **No** (hard-coded `https://findtorontoevents.ca`) | **Yes** (`AUDIT_BASE`, `:21`) |
| HTTP ≥ 400 capture | **No** (only console text) | **Yes** (`response` listener, `:86-91`) |
| Artifact JSON | No | Yes (`tests/artifacts/…json`) |
| React #418 policy | Fails the run | Ignored as "harmless" (`:37`) |
| Targets | audit, hyro, frontend | `/audit`, `/audit/`, `/audit/index.html` only |

Consequences if merged as-is:
- **CI is permanently red** — `expect(pageErrors).toHaveLength(0)` at `:42`/`:50` cannot pass while the
  homepage throws #418. There is no baseline/allowlist mechanism.
- The redundant duplicate assertion at `:42` and `:50` is harmless but signals an unfinished draft.
- The `--config` file exists only at the **worktree root**
  (`.kilo/worktrees/finpredict/playwright.live.config.ts`). The task brief's
  `…/finpredict/tests/playwright.live.config.ts` **does not exist**; only the spec was copied into
  `tests/`. The documented command happens to work only when run from the worktree root.
- The `Desktop Chrome` project sets no `browserName` (defaults to Chromium) — cosmetic, but the name
  is misleading.
- `retries: 0` + live third-party URLs means one CDN hiccup is a false failure.

**Recommendation:** fold the two new targets into `audit_js_errors_kimi411.spec.ts`, keep the JSON
artifact + response capture + `AUDIT_BASE`, and express #418 as an explicit *known-signature* with a
tracking assertion (fail if the signature changes, warn while it persists). Delete the duplicate
spec/config rather than shipping two live-browser harnesses.

---

## 2. v4 contradiction resolution — **PARTIAL**

The 18:05 rewrite **does** resolve the headline "0 active / 26-day dashboard" contradiction. It does
not resolve the document's internal contradictions, and it introduces a population mislabel.

### 2.1 Resolved — adopt these exact claims

> `INDEX.md:46` — "**Correction:** The live dashboard shows **20 curated active picks**
> (`dashboard_data.json` generated 2026-11-14T14:30Z). The '0 active picks' claim in our original
> audit referred to the **stale local repo copy** (Oct 23), not the deployed site. The Alpha Engine
> is impaired (93 forex KeyError failures in 24h) but the DB is actively writing."

> `INDEX.md:66` — "**Local `dashboard_data.json`** | **CRITICAL** | 26 days old (Oct 19) in repo.
> **LIVE site is fresh** (2026-11-14T14:30Z)."

> `INDEX.md:148` — "The live `findtorontoevents.ca/audit/data/dashboard_data.json` is
> `generated_at: 2026-11-14T14:30Z` with **20 curated active picks** / 4,148 raw / 3,500 recent-closed."

These are consistent with our archive (`MASTER_AUDIT.md:88`, `:360-361`) and with the archived
14:30Z table (`raw/active_table.txt:1` → "ACTIVE (curated) count 20"). **Verdict: resolved, and our
own "v4 is internally contradictory" wording is now stale** (see §7.1).

### 2.2 Unresolved — residual self-contradictions

| # | v4 line | Verbatim | Contradicted by | Status |
|---|---|---|---|---|
| V3 | `:92` | "edge, track, FWD WR%, FWD N, score, trust, confidence: **ALL EMPTY** (0 active picks)" | `:46` says 20 curated active; live 17:58Z payload has 10 active rows with real fields | **REJECT** — stale sentence left from the 0-active version |
| V4 | `:43` and `:94` | "**Alpha Engine (primary scanner) is DEAD**" / "**Alpha Engine**: DEAD (9 cancelled + 1 failure in last 10 runs)" | `:46`, `:132`, `:150` say "impaired … not completely dead"; live payload has picks with `signal_time` **17:50:41Z** (`PA=F`, `SB=F`) and **17:10:18Z** (`NEARUSDT`, `UNIUSDT`) | **REJECT** — "DEAD" is false at 17:58Z; use "impaired, 93 failed runs/24 h" |
| V5 | `:50-57` header "Live Picks" | CRYPTO 3 / EQUITY 757 / FOREX 2 / COMMODITY 4 / ETF 1,722 / BOND 1,293 / FUTURES 0 | 14:30Z curated panel (`raw/active_table.txt`): CRYPTO 3 / EQUITY 2 / FOREX 2 / COMMODITY 2 / ETF **10** / BOND **0** / FUTURES **1** | **REJECT the column label** — three cells are DB backlog, and FUTURES "0" is contradicted by `ES=F` |
| V6 | `:116` | P0-4 "Dashboard JS parse failure … committed since 2026-10-04; entire enhancement IIFE fails to parse" | Live `/audit/` at 18:41Z: **0 pageErrors**, 2,551 rows rendered. Our archive attributes empty EDGE/Track to population (`MASTER_AUDIT.md:193`, `:345`), not syntax | **REJECT as active root cause** — also contradicted by v4's own `:230` ("ALREADY IN MAIN, fixed 2026-10-18") |
| V7 | `:217-231` | Two consecutive "Applied" tables repeat the same P0-1/P0-2 rows | — | **Fix**: delete the duplicate "Already Applied" table |
| V8 | `:113-117` vs `:227-231` | P0-3 = Python 3.14 (§7) but P0-3 = prediction_market (§Applied); P0-5 = TP/SL (§7) but P0-5 = Python 3.14 (§Applied) | — | **Fix**: renumber once, globally |
| V9 | `:7` | "Last updated: 2026-11-14T17:55Z" | mtime 18:05; §2 correction is newer than the header | **Fix**: bump to 18:05Z |

### 2.3 Count drift — "20 active" must always carry a timestamp

| Clock | `picks.active` | Composition | Evidence |
|---|---:|---|---|
| 14:30Z | **20** | CRYPTO 3, EQUITY 2, ETF 10, FOREX 2, FUTURES 1, COMMODITY 2 | `raw/active_table.txt` |
| 16:15Z | **10** | CRYPTO 2, EQUITY 2, FOREX 2, FUTURES 1, ETF 1, COMMODITY 2 | PF3 live fetch (`PF3_finpredict_v4.md:60-64`) |
| 17:58Z | **10** | same shape: NEAR/UNI, ADBE/SNDL, USDCAD/NZDUSD, ES=F, XLF, PA=F/SB=F | RR3 fetch, `generated_at=2026-11-14T17:58:53Z` |
| Any | **0** | never observed | — |

"0" was never a live-site fact. "20" is correct only for the 14:30Z payload. The XRP/BTC Kalshi
legs and 9 ETF legs are gone by 16:15Z; UNI appears. Do **not** quote a bare "20 active" without the
payload timestamp.

---

## 3. hilarious-seer quickwins + summary — corroboration only

The three `quickwins.md` files are 2, 2 and 5 lines, with no `file:line`, no evidence path, and a
closing "Verified" that is not backed by an artifact in the folder. PF4 already adjudicated the
summary + quickwins at 17:57Z (`PF4_ml_hilarious_seer.md`, verdict FAIL / corroboration only).

| ID | Claim | Our coverage | Disposition |
|---|---|---|---|
| H1 | 0/9 money-ready, frozen prices, 22k ghosts, divergent DBs | `MASTER_AUDIT.md:20-24`, `:202-205`; PF4 | **ALREADY_COVERED** |
| H2 | Hyro 157 h stale / `pick_funnel_snapshot` 404 / crypto raw median 89 d | `MASTER_AUDIT.md:152-175`, `:213-214`; PF4 H2 | **ALREADY_COVERED** |
| H3 | 0/26 horizon pass, no backtest↔forward overlap | v3 ML_VALIDATION; PF2 `/PF5 C8` (not yet merged into MASTER) | **ALREADY_COVERED (merge pending)** |
| H4 | Add `n≥200` + Monte-Carlo-null + intrabar gates to validators | Our archive has Bonferroni/MC? **No `n≥200` gate anywhere**; Tier-2 is `n≥100` (`MASTER_AUDIT.md:126-128`) | **MERGE (new rigor gate)** |
| H5 | "Revive `alpha-engine-live.yml` heartbeat" | `actions_deepdive/ACTIONS_DEEP_DIVE.md` has the `cancel-in-progress` fix only in PF3 review notes, not in the dive | **MERGE** with actual target `alpha-engine-live.yml:39` |
| H6 | "luxalgo anti-skill" | PF2 reproduces `luxalgo_confluence` n=1,290 WR 42.9% CI_lo 40.3% | **ALREADY_COVERED** |
| H7 | "fundamental ranker no-edge" | PF2 / PF5 C8 (top-quantile WR 0.479 CI [0.439, 0.520]) | **ALREADY_COVERED** |
| H8 | Summary says "`dbpasses.txt` reviewed (keys masked)" | Project constraint: agents must **not** read/expose it; flaxen-hair places it at `/home/eaguiar2015/dbpasses.txt` outside the repo | **REJECT** — policy violation, and the claim cannot be reconciled with flaxen's location |
| H9 | Model roster / 402 / free-tier routing | Out of scope for the prediction-system audit | **REJECT (scope)** |
| H10 | "Clean zombie rows with … purge script" | Conflicts with our veto (`QUICK_WINS.md:73`) | **VETO** — quarantine/tag, never purge |
| H11 | "Mandatory cross-ref of PnL with latest picks + exact date" | Direction already in `QUICK_WINS.md:15` quote-provenance contract | **ALREADY_COVERED** |

---

## 4. flaxen-hair — unique findings

| ID | Finding | Evidence quality | Disposition |
|---|---|---|---|
| F1 | **PnL unit mix up to 100×**: `multi_asset_closed.json` 93 priced rows = 47 ratio + 32 percent + 14 off; `institutional_closed.json` 23/23 percent; same symbol/strategy/date varies | Recomputed row-by-row by peer; PF5 C7 accepted as "highest-value missing first fix"; **not re-run by RR3** | **ADOPT (P0)** — merge into `MASTER_AUDIT.md` §3 + `QUICK_WINS.md` |
| F2 | Duplicate non-unique `id` (`vix_reversal::SI=F::2026-03-11` repeated) in `multi_asset` files | Corroborates our 248 dup groups / 56 cross-ledger IDs | **MERGE** (file-specific evidence) |
| F3 | `confidence == ml_score` on every OPEN `multi_asset` pick → ml_score is a copy, not an ML output | Direct field inspection | **ADOPT** — new; contradicts any claim of independent ML scoring |
| F4 | All 41 `multi_asset_picks.json` picks are `forward_test_only=true`, `pnl_pct=null` → no verifiable live PnL in that store | Direct inspection | **ADOPT** — strengthens "three divergent stores" |
| F5 | `meta_strategy.db`: `live_performance`, `walkforward_results`, `permutation_signals`, `meta_label_predictions`, `adversarial_compat` all 0 rows | Direct sqlite read | **MERGE** into §3 frozen-data |
| F6 | `dna_factory.db` 176 strategies dated 2026-05-26; `coinglass.positions` max `opened_at` 2026-11-06 | Direct sqlite read | **MERGE** (freshness inventory) |
| F7 | `recent_picks.txt` (2026-03-11) header claims "Past 2 Hours" | Direct inspection | **ADOPT (minor)** |
| F8 | `dbpasses.txt` "missing" (§1 initial, §8 bottom line) | **Self-retracted in §1**: located at `/home/eaguiar2015/dbpasses.txt`; §8 still says "missing" | **REJECT F8** — fix the document, keep only the located/retracted statement |
| F9 | "Add mutual fund coverage (algorithm + feed)" | Contradicts our de-advertise / `NOT_BUILT` decision | **VETO** |
| F10 | "Normalize `pnl_pct` then backfill/fix all downstream consumers" | Correct direction, unsafe as written (blind global transform double-scales already-correct rows) | **MERGE with guardrails** |
| F11 | "Make pick `id` unique" | Aligns with dedup key; a DB `UNIQUE` index is already vetoed | **MERGE (application-level key only)** |

---

## 5. Disposition ledger — source → target

### ADOPT (merge verbatim or near-verbatim)

| # | Source | Target | Change |
|---|---|---|---|
| A1 | `LIVE_BROWSER_VALIDATION.md:14-18` | `MASTER_AUDIT.md` §3 (after `:216`) | New "Live browser runtime (18:41Z)" block: L1–L5, L9, L10 with RR3 counts |
| A2 | `LIVE_BROWSER_VALIDATION.md:20-25` | `MASTER_AUDIT.md` §3 + `QUICK_WINS.md` offsets | HYPE/KuCoin client-side proxy failure as the front-end symptom of quote unreliability — **scoped to symbol-card enrichment** |
| A3 | `raw` evidence in §1 (L9) | `MASTER_AUDIT.md` §3 dead-panels bullet | Missing `strategy_tribunal_latest.json` sidecar (producer `tools/strategy_kill_tribunal.py:181`; consumer `template.html:1021`) |
| A4 | `INDEX.md:46`, `:66`, `:148` | `MASTER_AUDIT.md` §7 row + §10 #9 | Record that the 18:05 rewrite concedes 20 active / live-fresh |
| A5 | flaxen F1 | `MASTER_AUDIT.md` §3 + `QUICK_WINS.md` new rank | PnL unit mix (47/32/14, up to 100×) |
| A6 | flaxen F3, F4 | `MASTER_AUDIT.md` §3 | `ml_score == confidence`; 41 forward-test-only/null-PnL picks |

### MERGE (adopt with correction)

| # | Source | Target | Correction required |
|---|---|---|---|
| M1 | `audit_live_js_errors_spec.ts` | Existing `tests/audit_js_errors_kimi411.spec.ts` | Add `frontend`/`hyro` targets + response-≥400 capture; keep `AUDIT_BASE` and artifact JSON; #418 as known-signature warning; delete duplicate spec/config |
| M2 | `LIVE_BROWSER_VALIDATION.md:12` | same | "211 controls" is the peer's count; RR3 saw 2,551 rows / 29,185 chars — report counts with selector scope |
| M3 | `LIVE_BROWSER_VALIDATION.md:30-31` | `MASTER_AUDIT.md` §3 / `QUICK_WINS.md` | Keep "server-side fetch" fix; **drop** "add a CORS proxy header allow-list" (not actionable on a third-party origin) |
| M4 | hilarious H4 | `MASTER_AUDIT.md` §5 + `QUICK_WINS.md` gates | Add `n≥200` + MC-null as *proposed* Tier-3 gate; do not state it as already enforced |
| M5 | hilarious H5 | `ACTIONS_DEEP_DIVE.md` §5 P1 | `alpha-engine-live.yml:39` `cancel-in-progress: true` → `false` (verified by PF3) |
| M6 | flaxen F2, F5, F6, F7 | `MASTER_AUDIT.md` §3 frozen-data bullets | Attribute as peer evidence; F1 counts accepted at face value |
| M7 | flaxen F10, F11 | `QUICK_WINS.md` | File-scoped dry-run + before/after sample; application-level dedup key only |
| M8 | v4 `:146-150` correction block | `PEER_CROSSREF.md:25-26` | Replace "v4 ❌ says 0" with "v4 18:05 rewrite concedes 20; residual at `INDEX.md:92`/`:94`" |

### REJECT

| # | Source | Reason |
|---|---|---|
| R1 | v4 `:92` "ALL EMPTY (0 active picks)" | Directly contradicts v4 `:46` and the live payload |
| R2 | v4 `:43`/`:94` "Alpha Engine DEAD" | New picks at 17:50:41Z and 17:10:18Z; use "impaired" |
| R3 | v4 `:50-57` "Live Picks" column | Mixes backlog (757/1,722/1,293) with curated; FUTURES 0 is wrong |
| R4 | v4 `:116` P0-4 JS parse root cause | Live page parses and renders 2,551 rows; empty columns are population-driven |
| R5 | hilarious H8 "`dbpasses.txt` reviewed" | Policy violation; location reconciled by flaxen-hair |
| R6 | hilarious H9 model-roster fix | Out of audit scope |
| R7 | flaxen F8 "dbpasses missing" | Self-retracted in flaxen §1; contradicts project constraint |
| R8 | `LIVE_BROWSER_VALIDATION.md:18` "widget(s) broken/empty" | Not observed; 51 event links and 26 images render. Downgrade to "island hydration fails; user-visible loss unproven" |

### ALREADY_COVERED

| # | Claim | Where we have it |
|---|---|---|
| C1 | Edge/Track/FWD columns dead (0/20, 2/20) | `MASTER_AUDIT.md:176-198`, `:345` |
| C2 | Hyro static/dead data | `MASTER_AUDIT.md:214`, `:374` |
| C3 | 0/9 money-ready | `MASTER_AUDIT.md:264-268`; `QUICK_WINS.md:93` |
| C4 | Ghost rows 22,947; EXPIRED 3,377 | `MASTER_AUDIT.md:203-205` |
| C5 | 0/26 horizon pass; 0/6 at n≥60 | PF2 (merge pending per PF5 C8) |
| C6 | `luxalgo` anti-skill; fundamental ranker no-edge | PF2 |
| C7 | `summary_picks` WR>100% | `MASTER_AUDIT.md:202` |
| C8 | Three divergent stores (SQLite/MySQL/JSON) | `MASTER_AUDIT.md:209`; PF5 |

---

## 6. Veto list — destructive or unsupported

| # | Proposal | Source | Why vetoed |
|---|---|---|---|
| X1 | "Fix" React #418 by suppressing hydration (`suppressHydrationWarning` globally) or deleting the `/next/` island | implied by L1 severity framing | Masks a real server/client mismatch; the island is the event grid on the **events site**, unrelated to the prediction system |
| X2 | Bundle the homepage React crash into the audit-dashboard data-pipeline fix | `LIVE_BROWSER_VALIDATION.md:30-31` | Different domain surface (`/` vs `/audit/`); fixing one does nothing for the other |
| X3 | "Add a CORS proxy header allow-list" | `LIVE_BROWSER_VALIDATION.md:31` | The origin cannot set headers on `min-api.cryptocompare.com`; fix is server-side bake or a CORS-enabled exchange endpoint |
| X4 | Touch `dashboard_enhancements.js` because v4 P0-4 says the IIFE fails to parse | v4 `:116` | Live run: 0 pageErrors; file already fixed 2026-10-18 per v4 `:230` |
| X5 | Restart/rebuild the Alpha Engine on the "DEAD" claim | v4 `:43`/`:94` | Scanner emitted picks at 17:50Z; the real defect is the FX `KeyError` cluster (A1) |
| X6 | Global `pnl_pct` normalization + downstream backfill | flaxen F10 | Double-scales already-correct rows; must be file-scoped, dry-run, with before/after samples |
| X7 | Add mutual-fund scanner/data feed | flaxen F9; v4 proposed_fixes | Contradicts the `NOT_BUILT` / de-advertise decision (`QUICK_WINS.md:78`, `:94`) |
| X8 | "Purge" zombie rows | hilarious H10; v4 | Destructive; quarantine/tag only (`QUICK_WINS.md:73`) |
| X9 | `UNIQUE(symbol,direction,created_at,source_system)` index | v4 | Can fail on existing duplicates; already vetoed (`QUICK_WINS.md` cross-ref) |
| X10 | Gate CI on third-party CORS failures | new spec idea | Flaky and outside our control; assert only on own-origin assets |

---

## 7. Recommended edits to our archive

### 7.1 `MASTER_AUDIT.md`

1. **`:88`** — `picks.active | 20` → `picks.active | 20 at 14:30Z; 10 at 17:58Z | Curated panel (timestamp required — see §3)`.
2. **`:95-107` table** — add a header note: "counts are for the 14:30Z payload; the panel shrank to
   10 by 16:15Z (ETF 10→1, CRYPTO 3→2) and is stable at 10 through 17:58Z."
3. **After `:216`** — insert a new subsection `### Live browser runtime (2026-11-14T18:41Z)` with:
   - homepage: 1 pageError `Minified React error #418` (`args[]=HTML`) from
     `/next/_next/static/chunks/dde2c8e6322d1671.js`; 3/3 loads; 4 console errors (2× doubleclick 400,
     2× 404); 12 failed requests (10 nowtoronto `__hp-blocked` ORB + ads ping); page still renders 51
     event links.
   - `/audit/`: 0 pageErrors; 8 failed requests (4× cryptocompare HYPE CORS, 4× allorigins/KuCoin);
     1× 404 `strategy_tribunal_latest.json`.
   - `/audit/hyrotrader/`: 0/0/0.
4. **`:395`** — replace the `Browser visual rendering — UNVERIFIED` bullet with:
   "Browser runtime errors verified 18:41Z for `/`, `/audit/`, `/audit/hyrotrader/` (see §3).
   Pixel/visual-only states remain `UNVERIFIED`."
5. **`:360-361` and `:431`** — change "v4 internally contradictory" to: "v4 18:05 rewrite concedes the
   20-active / live-fresh facts (`INDEX.md:46`, `:66`); residual contradictions remain at
   `INDEX.md:92` ('ALL EMPTY … 0 active picks') and `:43`/`:94` ('DEAD')."
6. **New §3 bullet** — flaxen PnL-unit gap: `multi_asset_closed.json` 93 rows = 47 ratio + 32 percent
   + 14 off; `institutional_closed.json` 23/23 percent; duplicate `id`; `ml_score == confidence`
   (peer-claimed, not re-derived here).
7. **§10** — add row 14: "Live-browser validation adopted (RR3) — reproduces 1 pageError, 4/12 frontend
   errors, 0/8/0 audit, 0/0/0 hyro; severity downgraded for #418 and HYPE."

### 7.2 `actions_deepdive/ACTIONS_DEEP_DIVE.md`

1. **§5 P1** — add: "Add a live-browser smoke job (`/`, `/audit/`, `/audit/hyrotrader/`) **only after
   A4 lands**; the current Playwright job (`sports-smoke-and-e2e.yml`) fails on
   `ubuntu26.04-x64` (`:24`), so a new browser job would inherit the same install failure. Use the
   existing `tests/audit_js_errors_kimi411.spec.ts` harness, not a second config."
2. **§5 P1** — add: "`alpha-engine-live.yml:39` `cancel-in-progress: true` → `false` (PF3-verified), so
   heartbeats are not self-cancelling."
3. **§6 / §7** — add to `UNVERIFIED`: "Whether any workflow writes
   `audit_dashboard/data/strategy_tribunal_latest.json` on a schedule; the live URL 404s at 18:42Z
   while the producer (`tools/strategy_kill_tribunal.py:181-183`) exists."
4. **§4** — no change; the scheduler numbers stand.

### 7.3 `recommendations/QUICK_WINS.md`

1. **New rank 13** (after the quote-provenance rank 5), "Symbol-card fallback honesty":
   "HYPE/SYMBOL chart falls through Binance → allorigins/KuCoin → CryptoCompare and silently returns
   `[]` (`audit_dashboard/template.html:18040-18115`); all three live paths fail (CORS/abort). Bake the
   candles into a sidecar or gate the chart to symbols present in `picks.active`. Impact: symbol-card
   RSI/sparkline only; no PnL effect."
2. **New rank 14**, "Missing-sidecar hide": "`template.html:1021` fetches
   `data/strategy_tribunal_latest.json`, which 404s; the page already falls back to 'No tribunal
   report yet'. Either ship the file from `tools/strategy_kill_tribunal.py` in the deploy list or stop
   requesting it." (Folds into the existing sidecar-freshness bullet at `:45`.)
3. **Offset bullets** — add: "Flaxen PnL-unit fix: normalize **per file**, dry-run, sample 10 rows
   before/after; never a global transform. `multi_asset_closed.json` mixes ratio and percent (up to
   100×)."
4. **New rigor gate** — add under the Tier-2 discussion: "`n≥200` + Monte-Carlo null as a proposed
   Tier-3 gate (peer hilarious-seer); Tier-2 remains `n≥100`."
5. **Veto list** — append X1, X3, X6, X7 if not already implied (`:71-79` currently covers X8, X9 and
   the ML inversion).

### 7.4 `PEER_CROSSREF.md` (optional but stale)

`:25-26` still says `v4 ❌ says 0` / `❌ says 26d`. Update to "v4 18:05 rewrite concedes 20 / live
1.63 h; residual §5 '0 active' text remains" so the reconciliation matrix stops contradicting
`INDEX.md:46`.

---

## 8. UNVERIFIED

- Whether the React #418 hydration failure has **any** user-visible effect (controls broken, grid
  stale). Observed: server HTML renders 51 event links; client tree is regenerated.
- Whether HYPE symbol-card chart breaks any *pinned* user view (no HYPE in `picks.active`).
- `n≥200`/MC-null gate: peer recommendation only; no implementation exists in the repo.
- flaxen-hair's exact 47/32/14 unit counts and the "1,541 closed picks with zero outcome tracking" /
  "393 of 1,200 missing exit_price" figures — peer-computed, **not re-derived by RR3**.
- Whether `strategy_tribunal_latest.json` is produced by a scheduled workflow and simply not deployed,
  or never runs.
- Which process resolves the XRP/BTC Kalshi legs and 9 ETF legs between 14:30Z and 16:15Z.
- `picks.active_raw` drift: 4,148 (14:30Z) → 4,166 (17:58Z); growth source not examined.

---

## 9. Top 5 findings

1. **React #418 is real, deterministic, and mis-scoped by the peer.** 3/3 loads, thrown from
   `/next/_next/static/chunks/dde2c8e6322d1671.js`, `args[]=HTML`. It is the embedded Next.js event
   grid on the events site — **not** the audit dashboard — and the page still renders 51 event links.
2. **The v4 rewrite is half-resolved.** `INDEX.md:46`/`:66` now concede 20 curated at 14:30Z and a
   live-fresh payload, but `:92` still says "ALL EMPTY (0 active picks)" and `:43`/`:94` still say
   "Alpha Engine DEAD" while new picks appear at 17:50:41Z.
3. **v4's "Live Picks" column is backlog, not the panel.** ETF 1,722 vs 10 curated, EQUITY 757 vs 2,
   BOND 1,293 vs 0, FUTURES 0 vs 1 (`ES=F`). Mixing the two is the exact error the rewrite claims to
   fix.
4. **"20 active" is a moving snapshot.** 20 at 14:30Z → 10 at 16:15Z and 17:58Z; 0 never observed.
   Any count must carry `generated_at`. (Our `MASTER_AUDIT.md:88` needs the same timestamp.)
5. **Audit-dashboard live is crash-free but not error-free**: 0 pageErrors, 8 failed requests
   (HYPE CryptoCompare CORS + allorigins/KuCoin), 1× 404 tribunal sidecar. Both are LOW severity with
   graceful fallbacks — **not** evidence that price widgets are empty.

---

**Report path:** `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/recommendations/peer_review/rereview_1837/RR3_frontend_v4.md`

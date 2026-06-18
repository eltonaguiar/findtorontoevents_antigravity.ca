# PICKS-NOW METHODOLOGY REVIEW — root-cause of negative forward performance + over-emission

**Date:** 2026-06-13
**Mode:** READ-ONLY (no commits, no DB mutations, no generator runs, no push)
**Scope:** `tools/picks_now_professional.py`, `tools/save_picks_to_db.py`, the picks-now cron workflows, `audit_dashboard/picks-now.html` methodology, and the honest forward track record.
**Anti-fabrication note:** every function name, weight, line range, and SQL fragment below is quoted verbatim from the files at HEAD on branch `feat/honest-kill-switch-per-class-thresholds`. No imagined symbols.

---

## 0. The two numbers we are explaining

From `audit_dashboard/data/picks_now_track_record.json` (built by `tools/build_picks_now_track_record.py` off the deduped view `vw_picks_now_dedup`):

```
symbol_days_tracked: 206   resolved: 47   won: 15   lost: 32
wr_pct: 31.9   avg_pnl_pct: -0.31   cum_pnl_pct: -14.4
first_tracked: 2026-06-06 04:53:49   last_tracked: 2026-06-12 18:41:05
by_asset_class: EQUITY n=45 (won 15), COMMODITY n=1, ETF n=1
```

Two facts that frame the whole review:

1. **The 31.9% WR is HONEST, not a resolver artifact.** `tools/resolve_picks_now.py:71-91` is a first-touch resolver with **SL-first on same-bar ties** (`if sl_hit:` is checked before `if tp_hit:`, line 80, comment "SL-first on same-bar tie (conservative)"), 10-day `TIME_EXIT` (`EXPIRED` at last close, line 87-90), and the track-record builder reads only the deduped `vw_picks_now_dedup` (one row/symbol/UTC-day). This is exactly the honest discipline the master loop demands. So the negative result is a **real edge problem, not a measurement bug.**
2. **picks-now is, in practice, an EQUITY screener.** 45 of 47 resolved rows are EQUITY; COMMODITY and ETF contribute 1 each; CRYPTO/FOREX/BOND contribute 0 resolved. So "why is picks-now negative" reduces to "why are the published equity BUY/STRONG_BUY picks losing 31.9% WR / -14.4% cum."

---

## 1. OVER-EMISSION ROOT CAUSE (MU emitted 8x on 2026-06-06)

### 1.1 Mechanism — confirmed by git timeline, not inferred

The picks-now pipeline was born **2026-06-06 05:07 UTC** (commit `6d09c6023c` "feat(picks-now): full pipeline"). On that day **neither writer had any dedup at all**:

- **Writer A — `tools/save_picks_to_db.py` @ 6d09c6023c** was a bare loop (verified via `git show 6d09c6023c:tools/save_picks_to_db.py`):
  ```
  inserted = 0
  for p in picks:
      INSERT INTO picks_now_tracker (generated_at, symbol, ...) VALUES (NOW(), ...)
      inserted += 1
  ```
  No `SELECT DISTINCT`, no skip, no idempotency key. Every invocation re-inserts every BUY/STRONG_BUY pick with a fresh `NOW()` `generated_at`.

- **Writer B** is inside the generator itself (`tools/picks_now_professional.py`, the DB block now at lines 1457-1521). On 2026-06-06 it also had no per-symbol-day guard.

- **The cron runs 3×/day:** `.github/workflows/picks-now-refresh.yml` → `cron: "0 6,12,18 * * *"`. Each run executes the generator (Writer B inserts) **and** `tools/save_picks_to_db.py` (Writer A inserts again) → **2 inserts per symbol per cron run × 3 runs = 6 baseline**, plus any CI retries / manual runs on launch day. That is the source of MU at the **same entry 864.01 with 8 distinct `generated_at` timestamps** — it is the same scored pick written 8 times, once per (writer × run), all stamping `generated_at = NOW()`.

The `picks_now_tracker` table **has no UNIQUE constraint** (confirmed by the in-code comment at `picks_now_professional.py:1472-1473`: "The table has no UNIQUE constraint to enforce this, so BOTH writers must guard"), so nothing at the DB layer stops duplicate (symbol, day) rows.

### 1.2 What is ALREADY fixed (do not re-fix)

The duplicates were patched **2026-06-09** (3 days after MU-8x), so the MU event is historical:

| Layer | Commit | What it added |
|---|---|---|
| Writer A (`save_picks_to_db.py:30-41`) | `7de23d58b0` (06-09 06:04Z) | `SELECT DISTINCT symbol FROM picks_now_tracker WHERE DATE(generated_at)=CURDATE()` → skip if symbol already tracked today |
| Writer B (`picks_now_professional.py:1467-1482`) | `256a1447fa` (06-09 10:27Z) | same per-symbol-day guard (the "SECOND writer") |
| Output JSON (`picks_now_professional.py:1421-1439`) | `657102f504` (06-09 05:14Z) | `_dedup_by_symbol()` keeps highest-score row per symbol |
| Reporting view | — | `vw_picks_now_dedup` (one row/symbol/UTC-day) so pre-06-09 dup rows don't double-count the track record |

### 1.3 Residual gaps in the over-emission fix (P1)

The current guards are **read-then-write with no transaction and dedup on `symbol` ONLY** — not the `(symbol, direction, DATE)` key the task asked for. Concrete weaknesses:

1. **Race between the two writers.** Writer B (generator) and Writer A (`save_picks_to_db.py`) run as **separate steps in the same workflow** (`picks-now-refresh.yml` step "Generate picks" then step "Save picks to MySQL"). Each does its own `SELECT DISTINCT` then `INSERT`. Because Writer B commits before Writer A's SELECT, Writer A's SELECT *should* now see B's rows and skip — but this only holds because of step ordering, not a constraint. Any reordering, partial failure, or a third caller re-introduces dupes. **There is no DB-level idempotency key.**
2. **Dedup key is `symbol`, not `(symbol, direction)`.** If MU flips from BUY to STRONG_BUY within a day, the guard treats it as "already tracked" and silently drops the second signal — acceptable for now, but it means the key is not the `(symbol, direction, DATE)` the spec wants and can mask a genuine same-day direction change.
3. **`CURDATE()`/`DATE(generated_at)` is UTC-server-day**, while the page labels picks in ET — a pick generated at 18:41 UTC (≈14:41 ET) and one at 23:30 UTC (≈19:30 ET) are the same UTC day, fine; but the 06:00 UTC cron is the *previous* ET evening. Low-severity, but the day boundary is not the trading day.

### 1.4 The fix (idempotency, not read-then-write)

- **P1 — add a UNIQUE key and switch to upsert.** Add a generated/stored column or just enforce `UNIQUE(symbol, direction, pick_date)` where `pick_date = DATE(generated_at)`, then change BOTH writers' `INSERT` to `INSERT ... ON DUPLICATE KEY UPDATE score=VALUES(score), entry_price=VALUES(entry_price), ...` (keep the latest score, never a second row). This makes over-emission *structurally impossible* regardless of how many crons/writers/retries fire, and removes the fragile read-then-write race. File/function: `tools/save_picks_to_db.py` (the `for p in picks` loop, lines 36-60) **and** `tools/picks_now_professional.py` (the DB block, lines 1477-1517). **DDL is a DB mutation → operator-gated; the code change is in-repo.**
- **P2 — collapse to one writer.** Two writers of the same table is the root design smell (the comments at both sites acknowledge it). Have the generator emit JSON only and let `save_picks_to_db.py` be the sole DB writer (or vice-versa). Eliminates the "BOTH writers must guard" coupling entirely.

---

## 2. WHY FORWARD WR IS NEGATIVE (31.9% / -14.4% cum)

Root cause is **NOT** look-ahead in the displayed numbers (the track record is honestly resolved, §0) and **NOT** the resolver. It is a combination of **no honest-edge gate before publish**, **a scoring system that is not predictive at this horizon**, and **a universe/regime mismatch**. Evidence-by-evidence:

### 2.1 There is NO honest-edge gate before a pick is published

The publish set is built in `main()` at `picks_now_professional.py:1407-1409`:
```
json_picks = (df_res[df_res['direction'].isin(["STRONG_BUY", "BUY"])]
              .sort_values('score', ascending=False)
              .head(20))
```
A pick is published **purely because its raw multi-factor score crossed a threshold** — `direction` is assigned from score bands at lines 835-846 (`>=75 STRONG_BUY`, `>=55 BUY`, baseline `score = 50` at line 699). There is **no gate that says "only publish if this symbol/class has a positive forward expectancy."** The page text claims a 5-factor scoring exists, but **nothing checks whether that score has historically predicted wins.** This is the single biggest miss vs the master loop's "honest-gate before publish."

The only edge-aware logic is weak and mostly inert:
- The forward DB overlay (`load_db_edge_forward`, lines 358-459; consumed at 808-826) **only ADDS points** and requires `dbf_active = dbf_n_w >= 10` (line 695) — an *effective* (decay-weighted) sample of 10 per symbol. With picks-now only ~7 days old and ≤1 pick/symbol/day, **almost no symbol reaches n_weighted≥10**, so the overlay is inert for nearly the entire universe. It cannot block a pick; it can at most demote BUY→WATCH when `dbf_avg_pnl < 0` AND `dbf_active` (lines 852-857) — a condition that rarely fires.
- Net effect: the W_DB_EDGE block (the only honesty anchor) is **dead weight for a brand-new screener** because its sample-size gate is calibrated for a mature table, not a 7-day forward lane.

### 2.2 The scoring is technical/analyst-driven with no demonstrated forward edge

The composite (class `QuantScorer`, lines 587-1051) is `50 + Momentum(25) + MeanReversion(15) + Analyst(20) + VolAdj(15) + DBEdge(25)` (weights at lines 591-595). Two structural problems:

1. **It is a long-only, buy-the-dip + analyst-consensus screener.** Momentum reward peaks for "TREND+DIP" (up 3m, down 5d → +full W_MOMENTUM, line 706-708) and analyst `recommendationMean <= 1.5` grants full +W_ANALYST (line 732-734). In a **RISK_OFF / chop regime** (the page itself flags RISK_OFF, and the resolved cohort is -14.4%), "buy the 5-day dip in a strong stock" is exactly the falling-knife trade — confirmed by the resolved set being 32 losses / 15 wins, dominated by EQUITY.
2. **Analyst consensus is a slow, crowded signal.** The page admits it (`picks-now.html:823`: "lates behind price action"). STRONG_BUY analyst names in a drawdown are the most crowded longs and de-rate fastest. The universe (`UNIVERSE["EQUITY"]`, lines 92-128) is 119 large-cap names dominated by mega-cap tech / high-beta growth (NVDA, META, AMD, AVGO, PLTR, CRWD, …) — precisely the cohort that bleeds in RISK_OFF, and the score *rewards* their 3-month momentum.

There are several patched guards (NEG_TARGET demotion line 865-867, council-fix circuit breakers line 776-793, tournament-panel −20 line 759-763) — these are **point fixes for known embarrassments**, not an edge gate. They reduce a few bad labels but do not change the fact that the published set has no proven positive expectancy.

### 2.3 The published forward set is concentrated in the worst class for this engine

45/47 resolved are EQUITY (§0). Per `CLAUDE.md`/`money_ready_verdict.json`, EQUITY honest forward is FAIL (PF~0.90, WR~33%, INSUFF-N). picks-now is publishing into the **one class the audit already knows has no honest edge**, using a long-only momentum+analyst score, in a RISK_OFF tape. The -14.4% is the predictable composition of those three facts. (Note the small-n caveat the builder itself prints, lines 152-154: "n is TINY — treat WR as provisional, not edge." The negative *direction* is meaningful even if the magnitude is noisy.)

### 2.4 Methodology-vs-code contract drift (a credibility bug, not a PnL bug)

`audit_dashboard/picks-now.html` misstates the live methodology:
- Line 144 + line 809: **"DB Edge Overlay (10% weight)"** / "DB Edge Overlay (10pts)". **Code uses `W_DB_EDGE = 25`** (line 595, "council fix #6: anchor scoring to proven edge"). Momentum is shown as 30% (line 140, 809) but code is `W_MOMENTUM = 25` (line 591). Analyst shown 25% (line 142) but code is `W_ANALYST = 20` (line 593). The page advertises the **pre-council-fix-6 weights**.
- Line 139: "No pick gets a pass without all factors evaluated" implies a gate that does not exist — publication is score-sort top-20, not a pass/fail.

This is freebuff's file (see §4) and is a doc-fix, but it matters: the page is over-claiming rigor relative to what ships.

---

## 3. PRIORITIZED FIX PLAN (money-ready-aligned: honest measurement → dedup → honest-gate-before-publish → forward-lane discipline)

Aligned to `docs/MONEY_READY_MASTER_LOOP_2026-06.md` (honest measurement first; gates on CI lower bounds; focus 2-3 classes; forward lane only CONFIRMS).

### P0 — Stop publishing picks with no positive expectancy (honest-gate before publish)
- **File/fn:** `tools/picks_now_professional.py`, `main()` at lines 1407-1409 (the `json_picks` filter).
- **Change:** before writing `json_picks`, require an honest-edge predicate per class, not just `direction in (STRONG_BUY,BUY)`. Minimum viable: **suppress (or label NON-MONEY-READY and exclude from the forward tracker) any class whose `money_ready_verdict.json → classes.<CLASS>.intrabar_truth` is FAIL** — i.e. don't forward-track EQUITY BUYs while EQUITY honest PF<1. Stronger version: only forward-track classes in the master loop's current FOCUS set (CRYPTO + COMMODITY), keep everything else MEASUREMENT-ONLY/shadow.
- **Expected effect:** stops feeding the forward lane with the one class the audit knows is FAIL; the headline -14.4% stops accruing from a known-bad class. Forward lane reserved for classes that can plausibly confirm.

### P0 — Separate "research signal" from "forward-tracked pick"
- **File/fn:** `tools/save_picks_to_db.py` (loop 36-60) + `picks_now_professional.py` DB block (1477-1517).
- **Change:** keep scoring/displaying all classes as *research signals*, but only INSERT into the **forward-tracked** table (the one feeding `vw_picks_now_dedup` / the FORWARD-TESTED PERFORMANCE panel) for FOCUS classes that pass the §P0 honest predicate. Everything else logs to a shadow/research table that is clearly not part of the track record.
- **Expected effect:** the "FORWARD-TESTED PERFORMANCE" panel becomes an honest forward lane (master-loop "forward lanes only CONFIRM finalists"), not a dumping ground for un-gated equity longs.

### P1 — Make over-emission structurally impossible (idempotency key)
- **File/fn:** both writers (`save_picks_to_db.py` 36-60; `picks_now_professional.py` 1477-1517).
- **Change:** add `UNIQUE(symbol, direction, pick_date)` to `picks_now_tracker` (operator-gated DDL) and switch INSERTs to `INSERT ... ON DUPLICATE KEY UPDATE`. Removes the read-then-write race and the dedup-on-symbol-only weakness (§1.3). Collapse to a single writer (P2) afterward.
- **Expected effect:** MU (or any symbol) can never appear >1×/(symbol,direction,day) regardless of cron count, retries, or writer count — no dependence on step ordering.

### P1 — Calibrate the forward DB-edge gate for a young table
- **File/fn:** `picks_now_professional.py:695` (`dbf_active = dbf_n_w >= 10`) and the negative-expectancy guard 852-857.
- **Change:** while the forward lane is <30d old, the `n_weighted>=10` threshold makes the only honesty anchor inert (§2.1). Lower it to a documented small-n threshold for the demotion guard (e.g. demote BUY→WATCH when `dbf_avg_pnl < 0` at `n_weighted>=3`), OR explicitly note the overlay is inert until the table matures and rely on the §P0 class-level honest gate instead.
- **Expected effect:** even before per-symbol n builds, a symbol with negative observed forward expectancy can't carry a BUY label.

### P1 — Fix the methodology page to match the code
- **File/fn:** `audit_dashboard/picks-now.html` lines 140-144 (weights) + line 809 (tooltip) + line 139 ("no pick gets a pass…").
- **Change:** update weights to Momentum 25 / MeanRev 15 / Analyst 20 / VolAdj 15 / DBEdge 25 (or whatever ships post-fix), and replace "No pick gets a pass without all factors evaluated" with the honest description: "Top-20 by composite score among BUY/STRONG_BUY; forward-tracked only for FOCUS classes." **freebuff's file — coordinate (see §4).**
- **Expected effect:** page stops over-claiming rigor; weights match the live scorer.

### P2 — Universe/direction realism for the regime
- **File/fn:** `UNIVERSE` (lines 91-231) and the long-only `direction` logic (835-846).
- **Change:** the screener is long-only buy-the-dip + analyst-consensus, which is structurally wrong for RISK_OFF (§2.2). Either (a) gate equity longs behind a market-regime filter (already computed as `regime` at line 1410-1413 but only used for a label, never to suppress longs), or (b) restrict the forward-tracked universe to the FOCUS classes where the engine's style has a chance. Trim mega-cap-tech concentration in the EQUITY universe.
- **Expected effect:** stops the engine from buying high-beta dips into a falling tape and calling them forward picks.

### P2 — Collapse to one DB writer
- As §1.4 P2 — single writer eliminates the two-writer coupling the code comments themselves flag.

---

## 4. FREEBUFF LANE — coordinate before deep changes

Per task instruction, these are freebuff's files; flag before deep edits:
- **`audit_dashboard/picks-now.html`** — the methodology-weight fix (§3 P1) and the "no pick gets a pass" wording (§2.4) touch freebuff's page. **Coordinate.** (These are doc/label fixes, low blast radius, but it's freebuff's surface.)
- **`tools/live_pnl_tracker.py`** — freebuff's file; not in any P0/P1 above. It mark-to-markets `picks_now_tracker` rows; if the idempotency/upsert change (§3 P1) alters row identity, freebuff's tracker reads the same table → **coordinate** so its `UPDATE`s still match after a UNIQUE key is added.

Fixes that do **NOT** touch freebuff's lane (safe to own): the publish-gate (§3 P0, in `picks_now_professional.py:main`), the research/forward table split, the idempotency-key on `picks_now_tracker` writers (the generator's own DB block + `save_picks_to_db.py`), the `dbf_active` calibration, and the universe/regime change.

---

## 5. ONE-PARAGRAPH SUMMARY

**Over-emission** (MU 8× on 2026-06-06): on launch day (pipeline born `6d09c6023c`, 06-06 05:07 UTC) **neither DB writer had any dedup** and `picks_now_tracker` has **no UNIQUE constraint**, so the 3×/day cron (`picks-now-refresh.yml` `0 6,12,18 * * *`) × **two un-guarded writers** (the generator's own DB block + `tools/save_picks_to_db.py`'s bare `for p in picks: INSERT`) each stamped `generated_at = NOW()` and re-inserted the same scored MU pick → 8 identical-entry rows. Per-symbol-day guards landed 06-09 (`7de23d58b0`, `256a1447fa`), so the MU event is historical, but the guards are read-then-write on **symbol only**, not a real idempotency key. **Fix:** `UNIQUE(symbol, direction, pick_date)` + `INSERT ... ON DUPLICATE KEY UPDATE` on both writers (then collapse to one writer). **Why WR is negative** (and it's honest — `resolve_picks_now.py:71-91` is SL-first first-touch, deduped view): there is **no honest-edge gate before publish** — `json_picks` (lines 1407-1409) is just top-20 by raw multi-factor score among BUY/STRONG_BUY; the only honesty anchor (forward DB overlay) is **inert** because its `n_weighted>=10` gate (line 695) can't be met by a 7-day-old table; and the published set is **45/47 EQUITY** — a long-only buy-the-dip + analyst-consensus score firing into a RISK_OFF tape on the exact class `money_ready_verdict.json` already marks FAIL. **Top 3 fixes:** (1) P0 honest-gate before publish — only forward-track FOCUS classes passing `intrabar_truth`, not un-gated EQUITY longs; (2) P0 split research-signal from forward-tracked pick so the FORWARD-TESTED panel is an honest forward lane; (3) P1 idempotency key to make over-emission structurally impossible.

---

**Report path:** `reports/PICKS_NOW_METHODOLOGY_REVIEW_2026-06-13.md`
**No commits, no DB mutations, no generator runs, no push made.**

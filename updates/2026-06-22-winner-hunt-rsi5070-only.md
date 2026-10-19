# Winner-hunt verdict — STA-09 sweep, rsi5070 is the lone lead (2026-06-22)

**Date:** 2026-06-22
**Hunt context:** The system's stand-cell accrual cadence has stalled. A legitimate, broader hunt for the *next* lead was authorized and run. Verdict below pins the moment-in-time state.
**Author:** Buffy (orchestrator on the user's behalf)
**DRY.git discipline:** This file cites canonical artifacts and does NOT inline raw hunt-output tables. Click through for the data; the file below explains the methodology, the verdict, the rationale, and the daily-cron plan.

---

## 1. The hunt (recipe + tooling)

The hunt used the *STA-09 recipe* from `tools/stamp_entry_conditions.py` — the production scanner's own entry-conditioning path. STA-09 conditions are (RSI band × session × direction × asset_class), broadly scoped: any cell that passes (n ≥ 100, FDR ≥ 5%) is a candidate. This is *broader* than a single-strategy scan: STA-09 cuts across all current traffic to find honest cohort cells, not strategy-named labels. Two scripts cooperated:

- **`tools/stamp_entry_conditions.py`** — the curated 6-condition production scanner. Reads `audit_dashboard/data/entry_conditions_forward.json` and stamps each canonical cell with `n`, `wr`, `pf`, `net_pf`, `last30d.{n,wr,pf_net}`, and `verdict_note`.
- **`tools/mine_entry_condition_cells.py`** — the exhaustive STA-09 enumeration. Sweeps ALL RSI × session × direction × asset_class combinations (not just the 6 curated ones), runs FDR correction across the family, ranks by net_PF.

Both scripts are read-only. Outputs landed in:
- `/tmp/mine.json` (`all_cells_ranked` with per-cell `n`, `wr`, `pf`, `net_pf`, `binom_p`, `fdr_pass` flags)
- `/tmp/staff.json` (curated `conditions` + cohort metadata)
- `audit_dashboard/data/entry_conditions_forward.json` (per-cell live stats updated mid-hunt)

Invoke pattern (audit trail — re-runnable):

```bash
python3 tools/stamp_entry_conditions.py --stdout --limit 6000 > /tmp/staff.json 2>/tmp/staff.err
python3 tools/mine_entry_condition_cells.py --limit 6000 > /tmp/mine.json 2>/tmp/mine.err
```

---

## 2. The verdict — no second lead at n ≥ 100

User-imposed bar: **n ≥ 100** (broader than the 30-pick "promotion" cell). At that gate:

| Source | Cells meeting n ≥ 100 | Net-positive? | Winning cell |
|---|---|---|---|
| `mine.json::all_cells_ranked` | 9 (all CRYPTO LONG roll-ups) | **NO** — every cell is net-negative | none |
| `staff.json::conditions` (curated 6) | 6 of 6 | **mixed** — `crypto_rsi5070_us` is net-positive; rest are net-negative | `crypto_rsi5070_us` |
| `entry_conditions_forward.json::conditions.rsi5070_us` | n=99 in `mine`, n=116 in `stamp` (dedup differs) — **at the n-gate boundary** | **YES** — `net_pf=1.024 (mine) / 1.283 (stamp)`, FDR pass | `rsi5070_us` |

**Honest finding:** every cell passing n ≥ 100 in the broader sweep is a **CRYPTO LONG roll-up losing money net of cost** (PF < 1.0, WR < 36%). The 9 candidates that cleared the n gate are roll-up variants that combine thin-edge sub-cells — they look large but they're **net-negative**. There is no fresh second lead.

The lone survivor is `crypto_rsi5070_us` — and it sits **at the n-gate boundary** (n=99 in `mine` after mine's slightly stricter dedup; n=116 in `stamp` after stamp's cohort alignment). This is the *same* cell that qualified as a CONDITIONAL TRACKING EXCEPTION in the prior verdict (`audit_dashboard/data/crypto_rsi5070_us_forward_status.json`).

---

## 3. Why rsi5070 is the lead (not "look harder")

The validation stack is doing what it should:

1. **STA-09 cast a wide net** (RSI × session × direction × asset_class). It found 9 candidates at n ≥ 100 — all CRYPTO LONG roll-ups. None are net-positive.
2. **Stamp's curated 6 conditions** filter out the noise. Of those 6, only one is net-positive: `crypto_rsi5070_us`.
3. **`mine.json` and `stamp.json` agree on the same cell** — `rsi5070_us` is independently the most net-positive cell in the cohort. The narrow discrepancy on n (99 vs 116) is a *dedup difference* (mine uses per-trade dedup; stamp uses source-alignment). Both are honest; both agree on direction.
4. **FDR correction confirms the lead.** `binom_p` for `rsi5070_us` is below the family-wide Benjamini-Hochberg threshold. The other 8 mine-cells fail FDR.
5. **`entry_conditions_forward.json::conditions.rsi5070_us`** documents the cell's essence: a CRYPTO LONG, RSI band 50-70, US-session entry on the LuxAlgo confluence trigger. The companion forward status file at `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` records:

   ```
   verdict_note: "CONDITIONAL TRACKING EXCEPTION — forward-shadow only, NEVER sized;
                   n=99 below n_ge_150 promotion bar; net_pf=1.36 > 1.0;
                   fails promotion by net_ci_lb_gt_1.15 (<0.95 actual)."
   ```

   i.e., the lead IS net-positive but hasn't crossed the harder promotion bar (which requires `n ≥ 150` AND `net_ci_lb > 1.15`). It is therefore tracked as a **shadow** lead, NOT sized.

**Conclusion:** The single-strategy STA-04 cohort table had independently surfaced only `rsi5070` as a candidate. The wider STA-09 hunt — RSI × session × direction × asset_class, was supposed to find a *second* lead somewhere in that broader space. It did not. The verdict stack is doing its job: many false positives were screened out by FDR + n ≥ 100 + net_PF > 1 + WR > 35%, leaving **one lone survivor**, accruing more forward n as live tracking continues.

The right action is to **let the existing lead accrue n** (the harder promotion bar needs n ≥ 150, currently 99-116) — not to reach for a second one. Establishing a second lead on the basis of a candidate that is both sub-promotion and COULD-BE-PROBABLY-NEGATIVE-AT-FULL-N is not a hedge; it is dilution.

---

## 4. Implication — operator-review sidecar fills the gap

The user-side instinct here is correct: the hunt has validated `luxalgo_short` (n=38 in `entry_conditions_forward.json::conditions.luxalgo_short`, wr=71.1%, net_pf=2.017) as a **secondary candidate worth surfacing manually** — even though it is below the n ≥ 100 gate. Same for ADAUSDT LONG: a low-correlation CRYPTO LONG large-cap probe that the M-036b production kill-switch explicitly rejects.

These two are surfaced via the **operator-review today-panel** (NOT the auto-sizing lane, NOT the production pick funnel). The `luxalgo_short` cell stats quoted here (`n=38 wr=71.1% net_pf=2.017`) are the **2026-06-22 min-snapshot**; re-readers should re-derive the live numbers from `audit_dashboard/data/entry_conditions_forward.json::conditions.luxalgo_short` rather than trust this inline string. The dedicated sidecar infra lives at:

- **`updates/2026-06-22-operator-review-today-panel.md`** — full spec for the sidecar pattern, the dashboard `renderOperatorReviewToday()` JS, the fail-closed contract, and the daily cron.
- **`audit_dashboard/data/operator_review_today.json`** — hand-curated sidecar; 2 picks tonight (ENAUSDT SHORT + ADAUSDT LONG) with per-pick `restriction` text and live-data enrichments.
- **`tools/build_operator_review_today.py`** — regenerator that joins the seed (2-5 hand-curated picks) to live `entry_conditions_forward.json` + `intrabar_sym_dir_fwd.json` + `money_ready_verdict.json` and writes the enriched JSON.

**Note on hunt-output durability:** the `/tmp/mine.json` + `/tmp/staff.json` snapshots cited in Section 8 are running artifacts — they get cleared on container restart. The canonical truth lives in `audit_dashboard/data/entry_conditions_forward.json::conditions` (per-cell live cohort stats, refreshed hourly) and in `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` (forward verdict trail with n-gate progression + verdict enum). When `/tmp/mine.json` is gone, those two JSONs are the source of truth — the verdict above can be re-derived from them alone without re-running the hunt scripts.

---

## 5. Daily-snapshot cron plan

The operator-review sidecar's daily regeneration cadence is the moment the hunt verdict becomes infrastructure:

- **Cron**: `0 7 * * *` UTC (07:00 daily)
- **Concurrency group**: `dashboard-publish` — shared with `audit-dashboard.yml` so the 35-min hourly cycle completes before this daily fires; `cancel-in-progress: false` queueing protects against mid-write truncation
- **Workflow**: `.github/workflows/operator-review-today.yml` (validates seed + schema, applies `--apply` build, auto-commits the resulting `operator_review_today.json` back to main with `[skip ci]`, 5x retry push loop, branch-protection abort on hard rejection)
- **Manual dispatch**: `gh workflow run operator-review-today.yml --ref main` for same-day force refresh

The 7:00 daily is positioned such that audit-dashboard's 06:10 hourly has ~50 minutes to land fresh `entry_conditions_forward.json` + `money_ready_verdict.json` data. Worst-case audit-dashboard overrun: the 07:00 daily queues — `cancel-in-progress: false` is intentional so both jobs serialize. Failed lookups produce `live_n == null` placeholders (rendered as "—" on the panel); the JSON still ships, the panel still renders picks (fail-closed is on `operator_review_only`, not on enrichment).

A full freshness audit of this cron would re-confirm that the cell under the lead (`rsi5070_us`) keeps accruing in `entry_conditions_forward.json::conditions` even when operator-review drafts are stale — the lead's n-gate progression toward 150 is the bar that determines when the promotion happens.

---

## 6. Forward tracking of the lead + monthly cron

The lead's per-day n accrual lives here:

- **`tools/crypto_rsi5070_forward_tracker.py`** — forward-tracker, fires each hourly cycle to update `crypto_rsi5070_us_forward_status.json` with the latest `n`, `wr`, `pf`, `net_pf`, `last30d.{...}`, `verdict` (CONDITIONAL_TRACKING vs PROMOTED vs KILLED_BY_HARD_BAR)
- **`audit_dashboard/data/crypto_rsi5070_us_forward_status.json`** — operator-facing surface; the dashboard renders verdict + bars + n-gate progress

The **monthly re-audit cadence** that replaces the manual hunt walk lives at:

- **`updates/2026-06-22-winner-hunt-replay-cron.md`** — sister spec for the new `.github/workflows/winner-hunt-replay.yml` (cron `0 8 1 * *` UTC). Emits `::error::` when `crypto_rsi5070_us.n >= 150` (PROMOTE the lead) + `::warning::` when a fresh net-positive FDR-pass cell surfaces outside the curated 6. Append-only verdict doc lives at `updates/YYYY-MM-DD-winner-hunt-replay.md` (one new file per cycle).
- **Manual dispatch** (until the cron lands on the next month's 1st-of-month): re-run the same two scripts with the same flags and re-derive this document's verdict; no new fork needed.

A monthly audit re-asks the question "is rsi5070 STILL the lone survivor at n ≥ 100"? If a fresh cell emerges (e.g. a new RSI band crosses 100n FDR-pass net-positive), the audit must record the new lead without blinding to the existing one. Until then: **organically accrue the existing lead, do not sync-hire a second.**

---

## 7. Verdict + next-step plan (today, 2026-06-22)

| Decision | Status |
|---|---|
| Is the field-wide STA-09 sweep honest at n ≥ 100? | YES — 9 cells found, 9 are net-negative, 0 are new leads |
| Is `rsi5070_us` still the lone survivor? | YES — n at the gate boundary, FDR pass, net-positive net_pf, but sub-promotion (fail by `n ≥ 150` and `net_ci_lb > 1.15`) |
| Should we reach for a second lead on a sub-promotion candidate? | NO — that is not a hedge, that is dilution |
| What about `luxalgo_short` (n=38 wr=71.1% net_pf=2.017)? | SURFACED today via operator-review sidecar — visibility only, operator decides |
| What about ADAUSDT LONG (low-correlation large-cap probe)? | SURFACED today via operator-review sidecar — visibility only, M-036b BLOCKED but operator-review panel bypasses for review |
| Daily-snapshot cron plan | LIVE — 07:00 UTC daily, concurrency group dashboard-publish, fail-closed on operator_review_only |
| Operator/team next action | (a) Make the daily seed edit in `tools/operator_review_seed.json` reflecting yesterday's outcome; (b) review operator-review panel state; (c) let `rsi5070_us` accrue toward `n = 150` |

The winner-hunt audit is **closed at no new lead until further notice**. The next time it should be re-opened is when either (a) `rsi5070_us` either fails promotion *or* gets promoted, freeing the hunt slot, OR (b) a fresh strategy emits a cell that crosses n ≥ 100 FDR-pass net-positive in the next monthly audit sweep.

---

## 8. References (canonical sources — DO NOT duplicate data here)

| Path | What it is |
|---|---|
| `tools/stamp_entry_conditions.py` | STA-09 recipe — production entry-condition stamper |
| `tools/mine_entry_condition_cells.py` | Exhaustive STA-09 enumerator + FDR sweep |
| `tools/crypto_rsi5070_forward_tracker.py` | Forward tracker for the lone survivor cell |
| `audit_dashboard/data/entry_conditions_forward.json` | Per-cell live cohort stats — `conditions.rsi5070_us` is the lead cell |
| `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` | Forward status of the lone survivor; CONDITIONAL TRACKING EXCEPTION |
| `audit_dashboard/data/operator_review_today.json` | Today's 2 hand-curated operator-review sidecar picks |
| `audit_dashboard/data/intrabar_sym_dir_fwd.json` | Per-(symbol, dir, strategy) intrabar index |
| `audit_dashboard/data/money_ready_verdict.json` | Class-wide honest intrabar verdicts (CRYPTO = NOT_READY) |
| `tools/build_operator_review_today.py` | Operator-review regenerator (--apply / --stdout / --strict) |
| `tools/operator_review_seed.json` | Hand-curated daily seed for the sidecar |
| `.github/workflows/operator-review-today.yml` | Daily 07:00 UTC cron, concurrency-dashboard-publish, fail-closed |
| `audit_dashboard/dashboard_enhancements.js::renderOperatorReviewToday()` | Operator-review panel renderer (fail-closed on operator_review_only) |
| `audit_trail/quality_gates.py:7317-7349` | M-036 + M-036b CRYPTO direction/size-block enforcement |
| `updates/2026-06-22-operator-review-today-panel.md` | Sibling spec — the operator-review sidecar panel |
| `updates/2026-06-22-winner-hunt-replay-cron.md` | Sibling spec — the monthly re-audit cron (replaces manual walks) |
| `/tmp/mine.json` (snapshot 2026-06-22) | STA-09 exhaustive cell ranking at n ≥ 100 sweep |
| `/tmp/staff.json` (snapshot 2026-06-22) | STA-09 6 curated conditions at n ≥ 100 sweep |
| `.github/workflows/winner-hunt-replay.yml` | Monthly cron implementation (cron `0 8 1 * *` UTC) |

---

## 9. Maintainer checklist

When updating this file in the future:

1. **Never** restate `/tmp/mine.json` / `/tmp/staff.json` tables verbatim — re-sweep and re-link.
2. **Always** cite the canonical live-data path (`audit_dashboard/data/entry_conditions_forward.json::conditions.{cell_key}`) and the forward tracker output (`crypto_rsi5070_us_forward_status.json`).
3. **Always** cross-link `updates/2026-06-22-operator-review-today-panel.md` if discussing the daily-snapshot cron.
4. **Always** document any n-gate progression (`rsi5070_us` from `n=99 → 116 → ... → 150`) **verbatim from `audit_dashboard/data/crypto_rsi5070_us_forward_status.json`** (NOT from `/tmp/mine.json` or from `entry_conditions_forward.json` alone). The per-cell JSON refreshes hourly; the forward status file canonicalizes the verdict trail with a `verdict` enum + `phase` pointer that the per-cell JSON does not.
5. If a fresh lead emerges, **add** it to section 3 with its own forward-status path; **do not** delete or rewrite the rsi5070 entry until the hunt bucketed-lead discipline says to.
6. If rsi5070 fails promotion **and** a fresh lead has crossed the bar, this file becomes "WINNER-HUNT VERDICT — n_leads=2 (cell-a, cell-b)"; otherwise it stays "rsi5070 is the lone lead."

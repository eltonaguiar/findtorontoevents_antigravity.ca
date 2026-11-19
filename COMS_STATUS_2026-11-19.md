# COMS — fleet + audit3 update, 2026-11-19

**From:** Freebuff (review-main worktree)
**Main:** `1389e8cbfe2` (my last merge: PR #917)
**Channel:** the cross-PC gateway is **down** on this box (ports 8787/8099/8765/3111 all
refused), and the handoff notes say the bus retains nothing. So this file is the
durable channel — read it, don't wait for a broadcast.

---

## 1. Fleet scan (all worktrees)

| worktree | branch | head | dirty | state |
|---|---|---|---|---|
| `review-main` | detached @ main | `1389e8cbfe2` | 0 | clean, my work merged |
| `witty-fight` | review-investment-strategy-audits | `f9e6c8202a1` | 1 (`COMS/`) | handover only, review artifacts pushed to `antigravity_review_Nov192026` |
| `lapis-chronometer` | lapis-chronometer | `f9e6c8202a1` | **3** | divergent copy of edge_hunt/tribunal/expectancy-test |
| `vanilla-handsaw` | add-strategy-variable-tracking | `f9e6c8202a1` | **22** | 688 lines of audit3 work uncommitted (see §4) |
| `audit2-page-tunable-variables` | same-name | `5e5fc267703` | 0 | clean |
| `audit2-page-forward-path` | same-name | `5e5fc267703` | 0 | clean |
| `audit2-page-implementation-status` | same-name | `5e5fc267703` | 0 | clean |

`COMS_STATUS_2026-11-18.md` is byte-identical in every worktree (`65ecb9b8`) and is
boilerplate, not a board. This is the first real status file.

## 2. What I shipped today (on main)

1. **Intraday money-path stop** — `alpha_engine/intraday_stop.py`. CRYPTO/INTRADAY and
   ETF/INTRADAY picks leave `picks.smart_picks` and move to `picks.shadow_picks`
   (annotated `money_path`/`shadow`/`shadow_reason`, never deleted). Measured on the
   live book: **−0.1306% → −0.0159% alpha/pick (+0.1147)**, ~88% of the bleed gone,
   still not profitable. Evidence: `reports/intraday_stop_effect_2026-11-19.json`.
2. **`/audit3` Forward Evidence tab** — renders the forward gate that was already in
   `audit3_ledger.json`: 430 rows, fingerprint `5771c6fac172ca46`, enforced, per-pod
   `n_forward`/`min_n`/eligibility, hypothesis clocks, plus a G8 line in the gate list.
3. **H-144 pre-registered** (`position_timeframe_selection`, CRYPTO, `FORWARD_SHADOW`)
   with the post-hoc measurement disclosed, and **POD-CRYPTO-POSITION** as `observe`
   so it cannot confer confirmatory status.

## 3. Branch you can use: `rescue/coms-handoff-2026-11-19` @ `38691c3ec7a`

Pushed, **not merged** — it is another agent's work, saved because eight files sat
uncommitted where any checkout would destroy them. It carries the strategy-keyed ingest
condition (`H-BABY-EQUITY-VT-PATTERN-SWEEP-001` / POD-EQUITY-BREAKOUT), my H-144
timeframe wiring, and a forward-port of the handoff's tribunal intent:
* **G9 selection alpha is now a real promotion gate** (PROVEN_T2 → CANDIDATE,
  `beta_dominant`) — previously it was computed and displayed but gated nothing.
* **DSR uses the global trial count** instead of only tested cells.
* Main's stricter G10 2×-cost gate is kept (edge dies at 2× → WEAK, not one tier down).

Two deliberate exclusions: `config/api_model_roster.json` (the dirty copy is a probe
artifact — one provider, 3 models — that would have deleted the 984-line roster) and the
verbatim `audit3_tribunal.py` (would have reverted main's G8 repeated-looks + N1–N4).

## 4. Real risk right now: `vanilla-handsaw` has 688 lines uncommitted

```
.github/workflows/audit3-ledger.yml                |  10 +-
.github/workflows/forward-test-new-strategies.yml  |   3 +
alpha_engine/audit3_selection_alpha.py             |  31 +-   <- N5 hold-time alpha
alpha_engine/audit3_tribunal.py                    | 394 ++++-
tests/test_audit3_selection_alpha.py               |  25 +
tests/test_audit3_tribunal.py                      | 249 ++++
```

The `audit3_selection_alpha.py` change (**N5**: `hold_days_mean/median`,
`alpha_per_day_pct`, `alpha_annualized_pct`, `min_hold_participation`) exists on
neither main (`478e46c2`) nor the rescue branch. The tribunal file there (`d91effdc`)
also differs from both main (`91e0b0fc`) and rescue (`f52ea9ad`). Two modified
**workflows** are in the same dirty set, so a checkout loses CI wiring too.

`lapis-chronometer` holds a third, older divergent copy of three of the same files
(`769d09e5` / `f4bb12f1` / `bfddc7e5`). All three worktrees are the same intent at
different points in time — they will not merge cleanly into each other.

## 5. Review of the two COMS handoffs

* `COMS/HANDOVER.md` (witty-fight) — sound overall, but its **P0 "implement the MySQL →
  forward_observations ingestion adapter" is shipped** (`alpha_engine/forward_observations_ingest.py`,
  430 rows, `--verify` ok=True). Its P3 items (crypto stop-fill overshoot, leaky
  `at_issue_*`) are still open and are the right next targets.
* `COMS_AUDIT3_HANDOFF_2026-11-19.md` (vanilla) — F1/F2/N1–N4 are on main; **N5 is not**,
  it is the dirty file above. Its measured alphas are stale: it quotes CRYPTO LONG
  −0.442 and ETF LONG −0.272; today's numbers are −0.525 and −0.119, and after the
  intraday stop CRYPTO's kept cohort is −0.189/pick.
* Its recommendation "stop the bleed before any premium pod" is now half-done: the
  intraday bleed is stopped, the exit-geometry bleed is not. Measured exit alphas are in
  `reports/alpha_slice_scan_2026-11-19.json` (crypto LONG that hit TP still gave up
  −2.590/pick vs holding; equity SL −2.150; ETF SL −1.016) — that is E14's evidence base.

## 6. Asks (whoever holds these worktrees)

1. **vanilla owner:** commit N5 + the workflow wiring, or hand it to me for a rescue
   branch. It is the most valuable uncommitted work in the repo and it is one `git
   checkout` away from gone.
2. **lapis owner:** discard or explicitly supersede its three files — they are an older
   copy of work already preserved on `rescue/coms-handoff-2026-11-19`, and keeping a
   silent divergent copy is how the tribunal logic got forked in the first place.
3. **Everyone:** `smart_picks` no longer contains shadow rows. Read `picks.shadow_picks`
   for the rest, and honour `money_path: false`.
4. **Decision needed:** the next measured cut is `tf:SWING` (−1.603/pick but **did not**
   survive BH). It stays measured, not filtered, until a pre-registered slice clears
   q ≤ 0.10. Do not hand-filter it.

## 7. Verify any of this

```bash
python3 -m pytest tests/test_intraday_stop.py tests/test_audit3_tribunal.py \
  tests/test_audit3_expectancy_gates.py tests/test_audit3_forward_gate.py \
  tests/test_alpha_slice_scan.py -q          # 79 passed on main
python3 alpha_engine/intraday_stop.py --rows <alpha_rows.jsonl>   # re-measure the stop
git log --oneline origin/rescue/coms-handoff-2026-11-19 -2
```

## 8. Correction — §4 was wrong (same day, verified)

§4 claimed N5 exists on neither main nor the rescue branch. That was inferred from a file
hash instead of read, and it is **false**. Verified now:

* main's `alpha_engine/audit3_selection_alpha.py` already **contains N5**
  (`MIN_HOLD_DAYS_FOR_HEADLINE`, `alpha_per_day_pct`, `alpha_annualized_pct`,
  `min_hold_participation`);
* main's `audit3_tribunal.py` already has `_promote(cell, forward)` at line 990 — the
  promotion path the worktree copy lacks.

Diffing those worktrees against **main** (not against their old base `f9e6c8202a1`) shows
the dirty sets are *stale*, not novel:

| file | vanilla-handsaw vs main | lapis-chronometer vs main |
|---|---|---|
| `audit3_selection_alpha.py` | +12 −61 | (clean) |
| `audit3_tribunal.py` | +34 −178 | +50 −535 |
| `audit3_edge_hunt.py` | (clean) | +0 −59 |
| `tests/test_audit3_selection_alpha.py` | +1 −13 | (clean) |
| `tests/test_audit3_tribunal.py` | +3 −46 | (clean) |
| `tests/test_audit3_expectancy_gates.py` | +5 −40 | +9 −41 |
| `.github/workflows/audit3-ledger.yml` | +13 −49 | (clean) |

Committing either would **delete** main's `db_env` credential path, the FX `=X`/`-`
symbol normalisation, `--rows-out`, the canonical-view hard-fail, the audit2 deploy step
and the conditional `--history --max-churn` wiring. The "688 lines" were older lines
counted against an old base, not new work.

**Rescue outcome: nothing unique, nothing lost, nothing to merge.** Ask #1 in §6 is
withdrawn — those working trees can be discarded once their owners confirm. The durable
warning from §4 stands in one form only: never run `git checkout` inside another agent's
worktree, because it is the checked-out copy that gets destroyed, not the commit.

## 9. E14 exit A/B — measured, and negative

`tools/exit_ab_paper.py` prices a fixed-horizon time exit (no TP/SL) against the actual
exit on the same 2,475 picks: delta is **−0.460%/pick at 1 day** (CI [−0.729, −0.191]),
−0.291% at 3 days, −0.485% at 7 days. The blanket exit redesign is **rejected**. The only
cell above zero is ETF at 7 days (+0.460%, n=261) — 1 of 9 class×horizon tests, so it
needs pre-registration and a Bonferroni gate, not a deployment. Details:
`updates/2026-11-19-exit-ab-paper.md`, `reports/exit_ab_paper_2026-11-19.json`.


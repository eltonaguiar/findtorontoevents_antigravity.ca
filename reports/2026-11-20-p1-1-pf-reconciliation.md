# P1-1 / P1-4 — CRYPTO profit-factor reconciliation

Date: 2026-11-20. Branch context: `zoo/p0-recovery-2026-11-20` (checkpoints `319be86fbe2`, `9fa7ea436b5`, `c12683134aa` untouched).
Plan input: `plans/2026-11-20-remediation-plan.md` P1-1 (reconcile the four PF values) and P1-2/P1-4 (re-run the panel against the canonical book).
Nothing here was committed or pushed; no git mutating command was run.

---

## 1. The four values, defined

One row per value. "Measured" means I ran the code or queried the source in this session; "traced" means I read the code path but the producing data is not on disk.

| Value | Formula (as implemented) | Cost basis | Row source | n (CRYPTO) | Resolution lane | No-loss convention | file:line |
|---|---|---|---|---|---|---|---|
| **1.3131** | `gross_win_sum / abs(gross_loss_sum)` over **gross** `pnl_gross_pct` | **gross** — cost applied only to `pnl_net_pct` / `mean_cost_bps`, never to the PF numerator or denominator | canonical-predicate rows from a 3,500-row payload slice (`payload_slice_canonical_predicate`) | 2070 (wins 955, losses 1113, flat 2) | whatever lane the payload rows carry (mixed; not declared) | `None` | [`alpha_engine/resolved_closed_view.py:367`](alpha_engine/resolved_closed_view.py:367), consumed by [`tools/build_audit2_per_class_panel.py:149`](tools/build_audit2_per_class_panel.py:149) |
| **0.2628** | `gross_win / gross_loss` over **net** `_net_pnl(p)` | **net** of round-trip slippage (M-069) | `closed_picks` / dashboard payload per class (`policy_clean`) | 22148 (`policy_clean_n`) | daily/time-exit policy lane | `float("inf")` | [`alpha_engine/money_ready_verdict.py:872`](alpha_engine/money_ready_verdict.py:872) |
| **0.8339** | `profit_factor(nets)` = `sum(v>0) / -sum(v<0)` over **net** `_net(r)` | **net** of measured class/strategy slippage | canonical resolved closed book (sidecar), `mode: canonical` | 6874 (ledger `classes[]`, `wins` 2762, `wr` 0.4018) | canonical resolved rows (TP/SL + time exits as resolved) | `None` when `loss <= 1e-12` | [`alpha_engine/audit3_tribunal.py:351`](alpha_engine/audit3_tribunal.py:351), called at [`alpha_engine/audit3_tribunal.py:980`](alpha_engine/audit3_tribunal.py:980) |
| **0.9167** | `gw / gl` over **gross** `intrabar_pnl_pct` | **gross** — no cost subtracted in the SQL | `at_signal_outcomes` rows with `intrabar_resolved_at IS NOT NULL` and `intrabar_status IN ('TP_HIT','SL_HIT')` | 3726 (wins 1333, gw 4375.29, gl 4772.99) | **intrabar first-touch**, TP/SL only — time exits excluded by construction | `None` when `gl == 0` | [`alpha_engine/money_ready_verdict.py:1585`](alpha_engine/money_ready_verdict.py:1585) |

### What was measured vs traced

- **1.3131 — measured.** Re-ran `python3 tools/build_audit2_per_class_panel.py --ledger /tmp/ledger_copy.json --payload audit_dashboard/data/dashboard_data.json` → `per_class_verdicts: 7 classes from payload_slice_canonical_predicate (3500 rows)`, CRYPTO `{'n': 2070, 'mean_net_pct': 0.4358, 'win_rate_pct': 46.18, 'profit_factor': 1.3131, 'wins': 955, 'losses': 1113, 'flat': 2, 'mean_cost_bps': 9.97, 'verdict': 'KILL'}`. It reproduces exactly — it is a real computation, not a transcription error. It is simply a **gross** PF over 2,070 of 8,769 canonical rows.
- **0.2628 — traced.** Read from [`audit_dashboard/data/money_ready_verdict.json`](audit_dashboard/data/money_ready_verdict.json) (`classes.CRYPTO.pf`, `policy_clean_pf`, `n: 22148`). It has a live producer ([`alpha_engine/money_ready_verdict.py`](alpha_engine/money_ready_verdict.py)), refreshed hourly by `audit-dashboard.yml`. I did not re-run it.
- **0.8339 — traced.** Read from [`audit_dashboard/data/audit3_ledger.json`](audit_dashboard/data/audit3_ledger.json) `classes[CRYPTO].pf`. **Note the drift:** the circulating value is **0.8283**, but the ledger on disk today says **0.8339** — same definition, earlier run. Two different numbers for the same computation is itself an instance of the defect being fixed; the definition is stable, the run is not.
- **0.9167 — measured.** Queried `at_signal_outcomes` directly with the same predicate and aggregation as `_intrabar_truth_map()`: `n=3726 wins=1333 gw=4375.2878 gl=4772.9861 pf=0.9167`. Reproduces exactly.

---

## 2. Canonical-row investigation (P1-4)

### The sidecar is not loadable

The ledger's denominator block states the canonical view was used:

```
mode: canonical, loaded_from_sidecar: true, canonical_kept_rows: 8769,
canonical_rows_sha256: 63609da549a7928d435cc16b4f834d61c9c86931b568c8f2f841a82acf502c08,
canonical_schema: audit.canonical.v1
```

But:

1. The ledger's own `source` (and `provenance.source_file`) is **`/tmp/audit3/dashboard_data.json`** — an absolute temp path.
2. `ls -la /tmp/audit3` → **No such file or directory.** The provenance leak is confirmed: the path is gone.
3. `find . -name resolved_closed_picks_net.json` (excluding `.git`, worktrees) → **no sidecar anywhere in the repo.**
4. The only payload on disk, [`audit_dashboard/data/dashboard_data.json`](audit_dashboard/data/dashboard_data.json), has **no `resolved_closed_picks_net` block** (`has resolved_closed_picks_net block: False`), so `load_sidecar()` has nothing to verify against and `_load_rows_from_payload()` falls straight through to the export slice.

**Verdict: the 8,769 canonical rows are not loadable from this checkout.** The sha256 `63609da5…` is recorded but the rows it describes do not exist on this machine. No panel run against the canonical book is possible, and I did not invent one. Re-deriving the canonical view would require the DB (`at_pick_outcomes` / `at_signal_outcomes`) plus the dashboard's `_is_valid_resolved_pick`, which is not something I can do silently here.

### Which row set corresponds to `scored_rows: 8769`

None of the four values except **0.8339** (the tribunal) is computed over 8,769 rows — and even it reports CRYPTO n=6874 because 8,769 is the all-class total. The panel's 1.3131 is over 2,070 CRYPTO rows out of a 3,500-row slice; `money_ready_verdict` is over 22,148; intrabar is over 3,726. So the ledger's published `scored_rows` matches only the tribunal's input.

---

## 3. Canonical-PF verdict

**Cost basis — decidable.** The project's stated convention is **net of round-trip cost**:

- [`alpha_engine/money_ready_verdict.py:862`](alpha_engine/money_ready_verdict.py:862): *"M-069: judge win/loss by NET return (after slippage), not the stored status field… counting it as a win is how the gross verdict overstates the edge."*
- [`audit_dashboard/data/audit3_ledger.json`](audit_dashboard/data/audit3_ledger.json) `provenance.win_definition`: *"net pnl_pct > 0 after round-trip class slippage."*

By that convention, **1.3131 (gross) and 0.9167 (gross) are not canonical PF values** — they are gross ratios and should be labelled as such wherever quoted. That leaves 0.2628 and 0.8339, both net, disagreeing (0.26 vs 0.83).

**Row source — decidable.** The ledger declares `population: canonical` and the plan requires the canonical book. 0.8339 is the only net PF computed over it.

**But that is not enough to name one number**, because the remaining two decisions are genuinely open and are not mine to make:

1. **Resolution lane** — should PF count only TP/SL exits, or also time exits? The tribunal counts resolved time exits; the intrabar lane excludes them by construction. The ledger's own coverage says `auto_expired: 9176` rows are dropped as "neither a win nor a loss" — but 0.2628's 22,148 rows include a different population entirely.
2. **No-loss convention** — `None` (tribunal, intrabar) vs `float("inf")` (money_ready). This changes what a consumer displays when a class has no losses, and it is not specified anywhere.
3. **Which surface owns the headline** — the panel (`/audit2`), `money_ready_verdict` (`/audit`), or the tribunal (`/audit3`). Each is a different product question.

**What I will and will not say:** the honest summary is that CRYPTO is **not demonstrably profitable** — three of four net/gross measurements are below 1.0, and the only above-1.0 value (1.3131) is gross, over the smallest row set, from a slice. 1.3131 is **withdrawn as a description of the book** (it never described it — see `rows_source: payload_slice_canonical_predicate`); it is retained only as "gross PF on a 2,070-row slice". I do not pick a canonical value.

---

## 4. Recommended path

1. Owner picks the resolution lane and the no-loss convention; publish them next to `win_definition` in `resolved_closed_view.provenance()`.
2. Regenerate `resolved_closed_picks_net.json` from a live run and commit it (or publish it as a CI artifact) so the canonical book is loadable by every reader — the `/tmp` provenance leak must be fixed at the writer, `audit_trail/dashboard_generator.py`.
3. Re-run the panel with `--rows` against that sidecar and assert `rows_counted == scored_rows`.
4. Make every surface label gross vs net explicitly. A gross PF next to a net PF with no label is how this started.

## 5. What remains undecided

- Resolution lane (TP/SL only vs including time exits).
- No-loss convention (`None` vs `inf`).
- Which surface's number is the headline.
- Whether the 0.8283 → 0.8339 drift indicates a changed input or a changed cost model between runs — not investigated, since the canonical rows are unavailable.

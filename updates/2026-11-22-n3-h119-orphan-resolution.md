# N3 — H-119 orphan emitter resolution (2026-11-22)

Status: resolved as **Resolution B** (documented non-promotable). No code executed for
promotion changed; one registry entry amended. `reports/forward_observations.jsonl`
was not modified.

## 1. The H-119 registry entry (verbatim, before the edit)

`reports/hypothesis_registry.json`, inside the top-level `hypotheses` list
(entry starts line 1947):

```json
{
 "id": "H-119",
 "asset_class": "CRYPTO",
 "family": "entry_condition_rsi_session",
 "description": "crypto_rsi5070_us: CRYPTO ∧ Wilder RSI(14,1h)∈[50,70] ∧ US session (13:30-21:00 UTC), pre-entry features only, honest intrabar first-touch outcomes (at_signal_outcomes, deduped sym-dir-day). The project's strongest HONEST money-ready lead.",
 "test_statistic": "net-of-16bp-RT-crypto PF CI-LB (symbol-day clusters)",
 "acceptance_criteria": {
  "min_n": 150,
  "min_ci_lb": 1.15,
  "min_n_eff": 80,
  "rule": "net CI-LB>1.15 at n>=150 with time-split holding and concentration<35% -> probation",
  "gate_eta": "~2026-06-25"
 },
 "economic_prior": "momentum-regime RSI band (not overbought/oversold) entered during the liquid US session; crypto winner amplitude is large enough to survive 16bp, unlike low-amplitude FX",
 "status": "FORWARD_ACCRUING",
 "registered_at": "2026-06-13",
 "data_sample_lock": "at_signal_outcomes intrabar, n=108 as of 2026-06-13 16:19Z",
 "result": "n=108: gross PF 1.53 (CI-LB 1.073); ... Source: audit_dashboard/data/crypto_rsi5070_us_forward_status.json.",
 "kill_reason": null
}
```

## 2. The ledger rows (`reports/forward_observations.jsonl`, read only)

Identity key: **`hypothesis_id`** (present on all 432 rows; `hypothesis` and `hyp_id`
are never used). Counts: `H-119` = **430**, plus `H-2026-11-22-COMMODITY-TREND10M` = 1
and `H-2026-11-22-EQUITY-TREND10M` = 1 (both daily-bar observations with a different
schema).

Representative H-119 row:

```json
{"asset_class": "CRYPTO", "benchmark_leg_ret": null, "closed_at": "2026-11-18T01:10:27+00:00", "created_at": "2026-11-19T07:20:40.605356+00:00", "entry_px": 72.62000275, "exit_px": 74.7986028325, "fees": 0.0, "funding": 0.0, "gross_mismatch_pp": 0.1809, "hypothesis_id": "H-119", "id": "fwd_7f2cb7b8be1b217e7142", "intrabar_first_touch": true, "opened_at": "2026-11-17T19:02:27+00:00", "qty": 1.0, "regime_ok": true, "resolver_exit_px": 74.93, "resolver_version": "at_signal_outcomes.intrabar.v1", "side": "LONG", "slippage_bps": 16.0, "symbol": "SOLUSDT"}
```

Representative non-H-119 row:

```json
{"hypothesis_id": "H-2026-11-22-COMMODITY-TREND10M", "observation_month": "2026-11", "data_through_month": "2026-10", "signal": 1, "complete_month": false, "level": 0.950659, "sma10": 0.93045, "realised_return_pct": -7.1454, "members": 11, "observed_at": "2026-11-22T08:55:27Z"}
```

## 3. The writer

- [`alpha_engine/forward_observations_ingest.py`](../alpha_engine/forward_observations_ingest.py:76)
  defines `CONDITIONS["H-119"] = {name: crypto_rsi5070_us, asset_classes: {CRYPTO},
  requires: {F3: "50-70", F5: "US"}}` and assigns `hypothesis_id` per matched row
  ([line 285](../alpha_engine/forward_observations_ingest.py:285)); `ingest()` appends
  through [`FO.append()`](../alpha_engine/forward_observations_ingest.py:478).
- It is triggered by [`.github/workflows/forward-observations-ingest.yml`](../.github/workflows/forward-observations-ingest.yml:1)
  on cron `41 */6 * * *` (plus manual dispatch), which runs
  `python3 -m alpha_engine.forward_observations_ingest --apply` and commits the ledger.
  The workflow header records that the 430 H-119 rows were first written by hand on
  2026-11-19 (commit `5c0c42d`).

## 4. The promotion gate

- Per-hypothesis rule: [`forward_observations.promotion()`](../alpha_engine/forward_observations.py:379).
  Its inputs are the rows' own fields only (`entry_px, exit_px, qty, side, fees,
  funding, slippage_bps, intrabar_first_touch, benchmark_leg_ret`) plus `min_n`. It
  takes **no pod id and no strategy id**.
- Pod-scoped gate: [`forward_gate_block()`](../alpha_engine/audit3_tribunal.py:1603). It
  iterates `manifest["pods"]` ([line 1629](../alpha_engine/audit3_tribunal.py:1629)),
  selects rows where `hypothesis_id == pod.hypothesis_id`
  ([line 1638](../alpha_engine/audit3_tribunal.py:1638)), and calls `FO.promotion` on
  that subset ([line 1641](../alpha_engine/audit3_tribunal.py:1641)). It then reports
  every other hypothesis id under a separate `hypotheses` block
  ([lines 1649-1653](../alpha_engine/audit3_tribunal.py:1649)) using `FO.promotion` too,
  but that block is never consulted for a cell verdict.

## 5. Decisive answer: blocked, or silently promotable?

**Neither "silently promotable" nor "blocked by a gate that is waiting on a pod" is
quite right: H-119 is structurally outside the promotion path.**

The gate's own docstring settles it:

> "Only rows closed on/after the pod's `registered_at` count ... Hypotheses that are
> not pods are reported too, so an accruing lead is visible on the page **without
> becoming promotable**." — [`forward_gate_block`](../alpha_engine/audit3_tribunal.py:1605)

Promotion is iterated from the pod manifest, never from the ledger. `H-119` has no pod
in [`reports/audit3_confirmatory.json`](../reports/audit3_confirmatory.json) (11 pods,
none with hypothesis H-119), so its 430 rows are never even looked at by the pod loop.
Measured run of `forward_gate_block`:

```
pods: {'POD-EQUITY-BREAKOUT': (0, False), 'POD-CRYPTO-VWAP-REVERSION': (0, False),
       'POD-CRYPTO-BOLLINGER-MR': (0, False), 'POD-FABER-TAA': (0, False),
       'POD-FOREX-USDJPY-MOMENTUM': (0, False), 'POD-COMMODITY-ROLL-YIELD': (0, False),
       'POD-CRYPTO-POSITION': (0, False), 'POD-ETF-DUAL-MOMENTUM': (0, False),
       'POD-CRYPTO-BTC4H-RSIMACD': (0, False)}
H-119 in pods? False
```

Independent of pod ownership, the hypothesis-level rule already fails H-119:

```
n_forward 430, eligible False,
reasons: ["net PF CI-LB 0.9213 <= 1.0 and IR 0.043 < 0.5",
          "benchmark_leg_ret coverage 80% < 90%"]
```

So the `min_n: 150` gate is *met* (430 rows), but promotion is *not* silently
achieved: both the podless structure and the PF/IR/benchmark criteria keep it out.

## 6. Resolution chosen: B

Why not A: no pod in the confirmatory manifest corresponds to `crypto_rsi5070_us`.
The nearest pods are `POD-CRYPTO-VWAP-REVERSION`, `POD-CRYPTO-BOLLINGER-MR`,
`POD-CRYPTO-POSITION` (H-144) and `POD-CRYPTO-BTC4H-RSIMACD`; none is the
RSI(14,1h)∈[50,70] ∧ US-session mid-band-momentum condition. [`tools/pod_emission_audit.py`](../tools/pod_emission_audit.py:1)
would also flag a pod whose strategy does not exist as an emitter (H-119 has no
`crypto_rsi5070_us` strategy label in the DB). Inventing a pod would have made the
number tidy while misrepresenting the strategy, so A was rejected.

Change made (only the H-119 entry, inserted after `kill_reason`):

```json
"kill_reason": null,
"promotable": false,
"promotable_reason": "Not a pod: reports/audit3_confirmatory.json has no pod for H-119, and forward_gate_block promotes only manifest pods (alpha_engine/audit3_tribunal.py:1603-1654) - non-pod hypotheses are reported under hypotheses[] and can never promote a cell. Marked non-promotable by the N3 orphan resolution 2026-11-22. Its 430 forward rows stay useful accruing evidence for the lead, but cannot gate a promotion; the same-date gate also fails on net PF CI-LB 0.9213<=1.0, IR 0.043<0.5, benchmark coverage 0.798<0.90."
```

`status` is left `FORWARD_ACCRUING` on purpose: H-119 genuinely still accrues rows
(1.23/day, 37 in the last 30d) and the registry's status vocabulary has no
"non-promotable" value; the machine-readable `promotable: false` carries the
resolution instead.

**Explicit consequence:** the 430 rows of accrued forward data are an explicit
write-off *as promotion evidence*. They remain valid descriptive evidence for the
lead, but they can never mint a verdict, and the same-date gate fails the rule
anyway (PF CI-LB 0.9213 ≤ 1.0, IR 0.043 < 0.5, benchmark coverage 79.8% < 90%). If a
future round wants the pod on the clock, it must pre-register a real pod for
`crypto_rsi5070_us` and fix the benchmark leg first.

## 7. Verification output

```
$ python3 -c "import json; d=json.load(open('reports/hypothesis_registry.json')); print('parses OK, hypotheses:', len(d['hypotheses']))"
parses OK, hypotheses: 116

$ md5sum reports/forward_observations.jsonl ; stat -c '%y' reports/forward_observations.jsonl
fb4c12cf33fe18153661669df5540a55  reports/forward_observations.jsonl
2026-11-22 08:55:27.820672989 +0000

# gate re-run after the edit (unchanged from before)
n_rows 432 fingerprint da3f416ba9e37172
pods: {...every pod (0, False)...}
H-119: n_forward 430 eligible False reasons ['net PF CI-LB 0.9213 <= 1.0 and IR 0.043 < 0.5', 'benchmark_leg_ret coverage 80% < 90%']
```

The ledger md5 and mtime are identical to the pre-session baseline, and no other
hypothesis carries a `promotable` key (`hypotheses carrying a promotable key:
['H-119']`). The registry has 395 changed lines in `git diff` from other actors'
prior work; the only lines added by this task are the two above
(`+ "promotable": false,` / `+ "promotable_reason": ...`).

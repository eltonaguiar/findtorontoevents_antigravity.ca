# Decision memo: `observe` → `pre_registered` for the 9 observe pods

Date: 2026-11-22 · Status: DECISION REQUIRED (user's call) · Changes made by this memo: NONE

## 1. The decision that has to be made

All nine `observe` pods in the union of the two pod manifests are, by the current gate, analysed and then
refused: their forward statistics are computed and discarded because their status is not `pre_registered`.
The decision is whether any of those nine has earned `pre_registered` status — and on what evidence. On the
evidence measured today the answer is none: not one of the nine has a single forward row on its own
hypothesis in the confirmatory ledger. Relabelling a pod is not a finding; it is a governance edit that
unlocks promotion, so it is put to the user rather than made.

## 2. Why this matters mechanically

The gate in [`alpha_engine/audit3_tribunal.py:1634-1645`](../../alpha_engine/audit3_tribunal.py:1634) (working tree):

```python
        if status not in {"pre_registered", "observe"}:
            continue
        hid = str(pod.get("hypothesis_id") or "").strip().upper()
        since = str(pod.get("registered_at") or "").strip()
        subset = [r for r in rows
                  if str(r.get("hypothesis_id") or "").strip().upper() == hid
                  and not (since and str(r.get("closed_at") or "")[:10] < since[:10])]
        res = dict(FO.promotion(subset))
        if status != "pre_registered":
            res["eligible"] = False
            res["reasons"] = [f"pod is {status} - registered for observation only"]
            res["promotion_blocked_by_status"] = status
```

In plain language:

- **`observe` = analysed, then refused.** `FO.promotion(subset)` runs on the pod's own forward rows, and the
  result is thrown away: `eligible` is forced to `False` and the reason is overwritten with
  "registered for observation only".
- **`pre_registered` = analysed, and promotable.** Same computation, but the promotion verdict survives.
- The docstring at [`alpha_engine/audit3_tribunal.py:1605`](../../alpha_engine/audit3_tribunal.py:1605) is explicit:
  *"Hypotheses that are not pods are reported too, so an accruing lead is visible on the page without
  becoming promotable."*
- The test at [`tests/test_audit3_forward_gate.py:146-157`](../../tests/test_audit3_forward_gate.py:146) proves the
  gate is real: an `observe` pod fed **120 perfect forward rows** still asserts `eligible is False`.

**The asymmetry.** Self-promotion is a one-word edit: `"status": "observe"` → `"status": "pre_registered"`
in a JSON manifest. Nothing else checks. In the union of the two manifests exactly one pod
(`POD-EQUITY-BREAKOUT`) is already `pre_registered`; the other eleven are not. That one word is the only
thing standing between "cannot certify anything" and "can" for each of these pods. That is precisely why it
must be a deliberate, evidenced decision and not a quiet edit.

## 3. Per-pod table

Forward rows = rows in the confirmatory ledger ([`reports/forward_observations.jsonl`](../../reports/forward_observations.jsonl),
432 rows as of 2026-11-22, md5 `fb4c12cf33fe18153661669df5540a55`) whose `hypothesis_id` equals the pod's
own hypothesis and whose `closed_at` is on/after `registered_at`. Backup paper-pilot evidence is counted from
the paper logs in [`verified_strategies/paper_pilot/`](../../verified_strategies/paper_pilot/) and is **not**
the same thing: it is not the ledger the tribunal judges.

| Pod id | Hypothesis | Family | Forward rows on own hypothesis | Independent forward evidence at all? | Recommendation |
|---|---|---|---|---|---|
| POD-CRYPTO-VWAP-REVERSION | H-2026-11-19-01 | CRYPTO vwap_reversion | 0 | Yes, but only backup: `vwap_reversion` 2 rows in `crypto_intraday_sim_paper_log.jsonl` (both OPEN, 0 closes) | **HOLD** |
| POD-CRYPTO-BOLLINGER-MR | H-2026-11-19-02 | CRYPTO bollinger_mr | 0 | Yes, but only backup: 1 row (OPEN, 0 closes), sim state `n_closed: 0` | **HOLD** |
| POD-FABER-TAA | H-2026-11-19-03 | EQUITY/ETF faber_taa | 0 | Yes, but only backup: `faber_taa_paper_log.jsonl` has 14 rows; forward pilot has 0 ETF closes | **HOLD** |
| POD-FOREX-USDJPY-MOMENTUM | H-2026-11-19-04 | FOREX FXMom | 0 | **No** — no FX forward rows; FX data layer stale | **HOLD** (closer to DOWNGRADE; see below) |
| POD-COMMODITY-ROLL-YIELD | H-2026-11-19-05 | COMMODITY roll-yield | 0 | **No** — emitter dormant, zero rows | **HOLD** (closer to DOWNGRADE; see below) |
| POD-CRYPTO-POSITION | H-144 | CRYPTO position-horizon slice | 0 | **No** forward rows (slice was measured on the closed ledger the tribunal judges) | **HOLD** |
| POD-ETF-DUAL-MOMENTUM | H-2026-11-19-06 | ETF dual momentum | 0 | Yes, but only backup: `etf_forward_stats.json` shows `n_closed: 0`, gate flags `n<100` | **HOLD** |
| POD-CRYPTO-BTC4H-RSIMACD | H-2026-11-19-07 | CRYPTO btc_4h_rsi_macd | 0 | Yes, but only backup: sim state `n_closed: 0`, judgment `no_judgment: n<20` | **HOLD** |
| POD-MEGA-MUTATION-CANDIDATE | H-2026-11-22-01 | UNMEASURED class/direction | 0 | **No** (`n_forward: 0`, `eligible: false` in the manifest itself) | **HOLD** |

Totals: **9 HOLD, 0 CANDIDATE, 0 DOWNGRADE.**

Notes on the two "closer to DOWNGRADE" pods: I am not recommending DOWNGRADE because `declined` is reserved
for a pod *evaluated and rejected* ([`reports/audit3_confirmatory.json:7`](../../reports/audit3_confirmatory.json:7)),
and neither POD-FOREX-USDJPY-MOMENTUM nor POD-COMMODITY-ROLL-YIELD has been evaluated on forward data at
all — they are blocked on data plumbing, not refuted. Their `observe_reason`s already say so
(`fx_prices ends 2026-02-09`; `No emitted rows; needs data plumbing`). Declining them now would be a
judgment without evidence; they should be revisited only if the plumbing is fixed, and otherwise retired
by the user.

**Ledger context (why every row is 0):** the 432 ledger rows are 430 on `H-119` and 1 each on
`H-2026-11-22-COMMODITY-TREND10M` and `H-2026-11-22-EQUITY-TREND10M` — **zero** on any pod's own hypothesis.
And the 430 H-119 rows are not usable evidence: they are 100% backfilled (single insert, all created after
their own close, 106 closed before H-119 was registered), recomputed PF CI-LB 0.775–0.850, disposition
QUARANTINE. H-119 is also not a pod at all, and has been marked `"promotable": false` (see the companion
verification doc `13_H119_LIVE_VERIFICATION_2026-11-22.md`).

## 4. Recommendation, with a default

**Recommendation: HOLD all nine at `observe`. Default if the user does not respond: HOLD.**

The reasoning is the ledger evidence: none of the nine has any forward evidence on its own hypothesis, so
promoting any of them to `pre_registered` would unlock promotion on zero evidence. That is exactly the
failure mode this programme exists to prevent. To conclude otherwise for a specific pod, one would have to
show forward rows on that pod's hypothesis clearing the acceptance criteria (n>=100, net CI-LB > 0 at 2x
slippage, IR >= 0.5 vs benchmark, split-half stable). No pod can show that today: every one is at 0 rows.

## 5. The one narrow exception worth considering: a *prospective* pre-registration

There is exactly one honest way to gain promotability: do not relabel an old pod. Register a **new**
hypothesis now, at `pre_registered`, with a stated rule and sample size, before seeing its data, so forward
evidence accrues legitimately from today. This is a proposal only; it is not registered by this memo.

**Proposed pre-registration (exactly one):**

- **Pod id:** `POD-CRYPTO-VWAP-REVERSION-LAGGED` (prospective; new id, not a rename of the old pod)
- **Hypothesis id:** `H-2026-11-22-VWAP-REVERSION-LAGGED-01`
- **Family:** CRYPTO mean-reversion, 4h bars, `vwap_reversion` LONG.
- **Rule (fully specified before data):** enter at the **next bar open** after the signal close (1-bar
  execution lag, never same-bar), z-entry in [1.5, 2.5], intrabar first-touch stops (not close-only),
  2x measured slippage applied to every fill. No discretionary overrides.
- **Minimum n:** 100 forward rows closed after registration.
- **Stopping / kill rule:** CI-LB <= 0 at 2x slippage at day 30 or day 60 → pod ends. At n >= 100: kill if
  net PF CI-LB <= 1.0, or IR < 0.5 vs a matched BTC/ETH benchmark, or split-half unstable.
- **Promotion rule:** identical to the existing acceptance criteria; the pod only becomes PROVEN_T2 if
  every criterion clears on its own post-registration rows.
- **Why this family:** it is the one observe pod whose lab evidence is the strongest in the repo
  (OOS n=516, Sharpe 3.102, DSR 21.4, PBO 0.18) *and* the one whose blocker is precisely specified and
  fixable: a 1-bar lag drops PF to 0.957 and PBO rises to 0.84–0.97. Re-running it with the lag and intrabar
  stops baked in tests the contested claim directly instead of trusting the same-bar result.

## 6. What this memo does NOT do

- It does **not** change any pod's status. All nine remain `observe`.
- It does **not** touch either manifest ([`reports/audit3_confirmatory.json`](../../reports/audit3_confirmatory.json),
  [`audit_dashboard/data/audit2_pods.json`](../../audit_dashboard/data/audit2_pods.json)).
- It does **not** unlock anything, does not register the proposed pod, and does not commit or push.
- It is a decision document only. Any status change is the user's call.

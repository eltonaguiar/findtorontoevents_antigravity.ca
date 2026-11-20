# Review — Grok round 2: the validation layer is mostly built; the population is not

**Date:** 2026-11-20 · **Reviewer:** Buffy (freebuff-deepseek-v4-flash)
**Companions:** [`GROK_REVIEW_2026-11-20_freebuff.md`](GROK_REVIEW_2026-11-20_freebuff.md),
[`SUBQ_REVIEW_2026-11-20_freebuff.md`](SUBQ_REVIEW_2026-11-20_freebuff.md),
[`SUBQ_REVIEW_ROUND2_DATASTACK_2026-11-20_freebuff.md`](SUBQ_REVIEW_ROUND2_DATASTACK_2026-11-20_freebuff.md)
**Method:** each of Grok's seven gates was searched for as code and traced into the promotion path;
each per-class target was matched against `reports/hypothesis_registry.json`; the zero-PnL claim was
recomputed from `audit_dashboard/data/dashboard_data.json`.

---

## 1. Verdict

**The spec is right and ~60% already shipped.** Four of the seven gates exist as callable code today
— `cpcv_pbo` and `deflated_sharpe` in `alpha_engine/anti_overfit_validator.py`, `compute_pbo` in
`rigorous_backtest_harness.py`, `deflated_sharpe_ratio` in three more modules — plus a graduation
runbook with thresholds that are **stricter than Grok's** (forward n ≥ 200, not 60–90 days; DSR 0.95
with declared `n_trials`). So "wire the existing code before any new signal work" is the single most
useful sentence in the pass, and the work it describes is smaller than it sounds.

**Where Grok is materially wrong** is the ordering rationale: it says fix the zero-PnL pipeline first
because "otherwise every backtest is garbage." Checking that claim turned up the largest defect
either of us has found today — **the dashboard's headline statistics cover 7,919 of 19,170 closed
picks.** The zero-PnL fix is necessary but not sufficient; the real problem is that 59% of the closed
book is silently outside the denominator.

**One direct conflict:** Grok says exclude memecoins and penny stocks from all production universes.
The registry currently carries **nine** live entries in exactly those classes (6 `FORWARD_OBSERVATION`,
3 `PRE_REGISTERED`). That is an operator decision, not a review point, and it should be made
explicitly rather than drift.

---

## 2. Gate coverage matrix

| # | Grok gate | Code exists? | Wired into promotion? | Real gap |
|---|---|---|---|---|
| 1 | Point-in-time data only | **Partial** — 41 files reference "purged", 36 "embargo" | No | PIT stamping covers **215 / 3,500** rows (`at_issue_strat_fwd_wr`); macro features read **latest-vintage** FRED (P0.8) |
| 2 | WFA ≥5 splits, WFE > 60% | **Partial** — `wfe` in 7 files, no canonical `walk_forward_efficiency` definition found | No | WFE is computed ad hoc per lab script, never as a gate |
| 3 | CPCV, PBO < 0.05 | **Yes** — `anti_overfit_validator.py:56 cpcv_pbo`, `rigorous_backtest_harness.py:276 compute_pbo` | No | Exists in the harness; not enforced on `/audit` producers |
| 4 | DSR > 0.95 at true trials | **Yes** — `deflated_sharpe.py:179`, 43 files; wired as an audit3 gate | **Partial** | `n_trials` comes from cells *in one run*, not the global counter (P0.5) |
| 5 | Net of realistic costs | **Yes** — M-108 cost table (CRYPTO 10+5 bps, EQUITY/ETF 4, FX 2–5, CMDTY 5) | Partial | Modelled slippage never reconciled against fills (P2.2) |
| 6 | Paper/forward 60–90 d matching within ~20% | **Yes, stricter** — runbook: n ≥ 200, net CI > 0 at 2× slippage, beats both control arms | **No sleeve qualifies** | `/audit` sleeves: forward n = 0, `n_marks` = 1 |
| 7 | Hard kill switches | **Yes** — runbook §4: −15% HWM, 3 negative months, gate regression, reconciliation break, stale inputs | Policy only | No recorded instance of the switch firing; untested response |

**Read:** the repository does not need new validation machinery. It needs (a) the existing machinery
applied to every producer rather than to one lab path, and (b) the population defects below fixed so
the gates have something honest to score.

---

## 3. Per-class targets vs the registry

| Grok target | Registry reality | Assessment |
|---|---|---|
| Equities/ETFs: residual mean reversion (Avellaneda–Lee) | **Registered today** — `H-2026-11-20-01`, `H-2026-11-20-03`, both `PRE_REGISTERED` | Already actioned. Note the id scheme moved to date-based ids, which **resolves the round-1 collision** (the old drafts would have reused H-144/H-145). My earlier recommendation appears to have been independently fixed |
| Crypto: residual or funding-rate mean reversion | `H-130`, `H-131` (funding), `H-2026-11-20-*` (residual); `H-035` `TESTED_KILL`, `H-017` `UNTESTED_DATA_GAP` | Covered; the killed ones stay dead — argue for re-entry only with a new prior |
| Forex: selective residual MR on majors | `H-128`, `H-129`; `H-037` `TESTED_WEAK`; class PF 0.2222 | Covered, and Grok's "treat no edge after costs as a valid outcome" is correct |
| Commodities: energy/metals calendar spread | `H-101`, `H-2026-11-19-06` both `PRE_REGISTERED`; COT family `H-001` `REJECTED` (leakage), `H-134/135` | Covered. The COT leak is the cautionary tale: same family, already burned once |
| Bonds: on/off-the-run, spread, term-structure MR | No hypothesis; class `INSUFFICIENT_N`, `oos_n = 0` | **Genuinely missing** — this is the one target that adds work |
| Meme/penny: do not pursue | **9 live entries** (6 FORWARD_OBSERVATION, 3 PRE_REGISTERED) | **Conflict.** Needs an operator decision, not a silent purge |
| Cointegration pairs | `H-132` `REFUTED` | Do not re-run unchanged |

So five of six testable targets already exist, one is new (bonds), and one contradicts current
registry state.

---

## 4. The zero-PnL question, answered — and it is not what either of us said

Grok: "~69% of resolved trades have zero PnL." My earlier payload check said 0.7%. Both numbers are
real; they describe different populations:

```
summed zero_pnl across systems      : 142
summed closed_picks across systems  : 19,170   ->  0.7% zero
summary wins + losses               : 7,919
closed picks outside the summary    : 11,251   ->  58.7% excluded
```

The dashboard's `zero_pnl` field counts 0.7% because **flat rows are filtered out before the
headline**, and the headline then covers only 41% of the closed book. Grok's 69% matches the raw
`at_pick_outcomes` table (a prior session measured 74.2% zero-PnL there). The defect is therefore not
"zero PnL exists" — it is that **the published win rate and profit factor are computed on a
non-random 41% subset**, and the excluded share is not shown anywhere on the page.

This supersedes part of yesterday's review. I wrote that the population problem was "different row
sets across surfaces"; the sharper statement is that one surface silently drops 59% of its own closed
picks before computing the headline.

**Action (P0.11):** publish `excluded_closed`, `zero_pnl_share`, and the denominator beside every
headline WR/PF, or refuse to render them. This is the same rule as P0.6, one layer up.

---

## 5. One correction to the crypto cost gate

Grok: *"only trade when the expected residual move exceeds 2× the measured round-trip cost"* (2 × 10
bps = 20 bps).

I measured this yesterday on hourly BTC/ETH with a 10 bps threshold: **turnover fell 4%, not the
order of magnitude the rule promises**, because at BTC's hourly volatility a 20 bps expected move is
almost always satisfied. A cost-multiple threshold is inert on high-vol, high-frequency series; it
bites only where cost is large relative to expected move. The implementable form is
`|forecast| > max(2 × cost, k × σ_horizon)` with `k` pre-registered, and the acceptance test must
report turnover reduction and gross-alpha retention separately — which is exactly what the
pre-registered cost-gate hypothesis already specifies.

---

## 6. What to do with this pass

1. **Adopt the instruction, not the list:** wire `cpcv_pbo`, `compute_pbo`, `deflated_sharpe` and a
   single `walk_forward_efficiency` into the **promotion path** used by `/audit` producers, not only
   the lab harness. That is one ticket, and it is the highest-leverage item in the pass.
2. **P0.11 (new):** publish the excluded population and zero-PnL share beside every headline.
3. **Bonds are the only genuinely new target.** Everything else is registered; test the registered
   ones before adding more.
4. **Decide memecoin/penny explicitly** — 9 live registry entries versus "exclude from all production
   universes" is a contradiction that will be resolved by accident if nobody rules on it.
5. **Cost gate:** σ-scaled, not a bare cost multiple (§5).
6. **Still first:** H-147, beta-hedged selection alpha.

---

## 7. Reproduce

```bash
grep -rnE "def (deflated_sharpe|compute_pbo|cpcv_pbo)" alpha_engine/*.py | head
python3 - <<'PY'
import json;d=json.load(open("audit_dashboard/data/dashboard_data.json"))
sysrows=d["systems"]
z=sum(r.get("zero_pnl") or 0 for r in sysrows); cl=sum(r.get("closed_picks") or 0 for r in sysrows)
s=d["summary"]; print(z, cl, 100*z/cl, s["wins"]+s["losses"], cl-(s["wins"]+s["losses"]))
PY
```

**Stance unchanged.** Nothing on `/audit` is sizeable today. Grok's contribution here is a correct
checklist that is ~60% already implemented — the honest conclusion is that our bottleneck moved from
"we lack validation" to "we do not apply it to every producer, and we publish a filtered denominator."

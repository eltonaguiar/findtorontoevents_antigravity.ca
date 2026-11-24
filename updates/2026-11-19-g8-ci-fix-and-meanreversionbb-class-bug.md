# G8 now computes in CI, and the "EQUITY MeanReversionBB winner" was a class mislabel

**Date:** 2026-11-19 · **Scope:** `.github/workflows/audit3-ledger.yml`, investigation only
for the pick-classification question (no change to emitters).

---

## 1. Why `/audit3` always showed G9 `unmeasured`

`selection_alpha.available` was `false` in every published ledger. The workflow had the step,
the secret exists (`DB_PASS_STOCKS`, set 2026-05-23), and the price tables are reachable. The
step still failed every run:

```
File "alpha_engine/audit3_selection_alpha.py", line 69, in _conn
    import pymysql
ModuleNotFoundError: No module named 'pymysql'
```

`py`ython was fine, the credentials were fine — **the driver was never installed**, and the step
ended with `|| true`, so the traceback was the only trace and the build stayed green.

### Fix

In the alpha step only:

1. `python3 -m pip install --quiet --disable-pip-version-check pymysql` before the call.
2. Replace `|| true` with `set +e`, capture `rc`, and emit
   `::warning title=audit3::selection alpha unavailable (rc=N)` when the sidecar is missing or
   empty. The ledger still builds (fail-open is deliberate — a missing alpha must never block
   the ledger), but the reason is now visible in the run instead of silently swallowed.
3. Log the sidecar size on success.

### Verified locally against the live payload (`/audit/audit/data/dashboard_data.json`, 3,500
closed rows) and the real read-only DB:

```
covered 2228/3500 picks
pick -0.192%  hold +0.117%  ALPHA -0.309%  CI=[-0.628, 0.022]  alpha_wr=44.4%
  CRYPTO  n=1727  alpha=-0.374%  CI=[-0.7437, 0.0175]
  EQUITY  n=240   alpha=+0.114%  CI=[-0.4072, 0.5931]
  ETF     n=261   alpha=-0.272%  CI=[-0.5035, -0.0372]
elapsed 6.41s
```

Runtime is 6.4 s, so the 15-minute job budget is not a concern. Feeding that sidecar to the
tribunal flips the contract on the spot:

| | without `--alpha` | with `--alpha` |
|---|---|---|
| `selection_alpha.available` | `false` | **`true`** |
| cells carrying an `alpha_gate` | 0 | 171 |
| class gates measured | 0 of 7 | **3 of 7** (CRYPTO, EQUITY, ETF) |
| class gates `unmeasured` | 7 | 4 (FOREX, COMMODITY, BOND, FUTURES — no price coverage) |

Coverage is honest rather than total: 2,228 of 3,500 rows have both bars
(`no_bar:EQUITY` 437, `no_bar:ETF` 225, `no_bar:FOREX` 159, `no_bar:COMMODITY` 50,
`no_timestamp` 129, plus `no_price:*`). The remaining four classes stay `unmeasured` instead of
being scored on nothing — that is the gate working, not failing.

---

## 2. Was the "EQUITY MeanReversionBB winner" excluded, or is it a bug?

I previously reported `MeanReversionBB / EQUITY` as the day's only positive line with real
sample size (209 trades, +0.426%/trade, 49.3% WR) and asked whether the canonical view was
dropping live edge. **That framing was wrong. There is no missing equity edge.**

### What the rows actually are

`at_pick_outcomes`, `resolved_at >= 2026-11-19`, `strategy='MeanReversionBB'`: 230 rows,
209 labelled `asset_class='equity'` and 21 labelled `crypto`. The symbols on the equity-labelled
rows are **all crypto pairs** — ADA-USD, AVAX-USD, BTC-USD, DOGE-USD, DOT-USD, ETH-USD,
LINK-USD, SOL-USD, XRP-USD. Every one contains `USD`; 209 of 209. No equity ticker appears.

The PnL distribution is a mechanical grid, not fills:

| pnl_pct | rows |
|---|---|
| +3.00 | 108 |
| −2.00 | 111 |
| other | 11 |

All 230 resolved in the same second (`15:33:26Z`), consistent with one batch resolution pass
against a fixed TP/SL pair. `EQ`uity rows with a fixed +3/−2 payoff and crypto symbols are the
signature of a **mislabel at emission**, not a strategy result.

### Why it never reached the ledger

Not the canonical filter. Checking the 230 `pick_id`s against
`resolved_closed_picks_net.json` (schema `audit.canonical.v1`, 8,613 rows):
**0 of 230 are present.** Their ids are of the form
`v1::signal_validation::sig_20260220_084510_AVAX-USD`, while the canonical view holds 102
bare `sig_*` ids plus other families (`Classic Momentum_*`, `aggregated_picks_*`). The rows were
never in the scored stream, so no exclusion reason applies to them — they are absent upstream of
the canonical build, which is fed from the export, not from `at_pick_outcomes` directly
(the export's `recent_closed` is capped at `MAX_CLOSED_PICKS = 3500` in
`audit_trail/dashboard_generator.py`).

### Verdict

- **Emission bug (real):** `asset_class` is wrong for these rows — crypto pairs labelled
  `equity`. That is an emitter defect, no fix applied here.
- **audit3 behaviour (correct):** not scoring them as an EQUITY cell is the right outcome. If
  they had been scored, they would have created a fake +0.43%/trade EQUITY cell built on a
  synthetic ±TP/SL grid.
- **Earlier claim (retracted):** the "+0.426% equity line" is not evidence of dropped edge and
  should not drive any canonical-filter change.

### Secondary defect found while checking

Stripping the `v1::...::` namespace from canonical ids collapses 8,613 ids to **8,528 unique**
— 85 collisions. `id` is therefore not a safe cross-system join key as-is; a join must use
`(namespace, id)` or the dedupe tuple. Recorded, not fixed.

---

## 3. Verification performed

| check | result |
|---|---|
| `python3 alpha_engine/audit3_selection_alpha.py --picks <live> --out /tmp/sa.json` | rc 0, 2,228/3,500 covered, 6.41 s |
| tribunal without `--alpha` | `available: false`, 0 alpha gates |
| tribunal with `--alpha` | `available: true`, 171 gated cells, 3/7 classes measured |
| DB cross-check of the 230 ids against canonical | 0 of 230 present |
| symbol audit of the 209 "equity" rows | 209/209 crypto pairs containing `USD` |

## 4. Not done

- No emitter change for the `asset_class` mislabel (needs the emitting module's owner; the
  defect is recorded above).
- The id-namespace collision (85/8,613) is recorded, not fixed.
- FOREX/COMMODITY/BOND/FUTURES remain `unmeasured`: `no_bar` dominates those classes, so the
  bar loader needs a look before their gates can be read.

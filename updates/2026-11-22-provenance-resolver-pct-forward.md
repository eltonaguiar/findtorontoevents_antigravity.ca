# Outcome resolver — `pct_forward` becomes computable (2026-11-22)

Tool: `tools/provenance_resolver.py`
Wired into: `.github/workflows/provenance-verify.yml` (selftest + non-blocking resolve + status)
Gate: `reports/provenance/resolved_status.json` → weekly scorecard row **Provenance resolution**

---

## Why the ledger alone was not enough

`tools/provenance_ledger.py` records **intent** at emit time. That proves a pick
existed before an outcome — but nothing computed the outcome, so `pct_forward`
stayed `null` and **no statistic could be formed**. A record of intent with no
resolution is a filing cabinet, not a clock.

This is the other half.

## The guarantee that makes it worth anything

The resolver reads the pick ledger and appends outcomes to a **separate file**
(`reports/provenance/resolutions.jsonl`). **The pick records are never modified.**

That constraint is the whole point. If a resolver could rewrite the picks, it could
backfill them, and the ledger would be worth exactly as much as the artifacts this
programme spent three rounds proving untrustworthy. The selftest asserts it:

```
pick file unchanged after resolving -> True
```

## Conventions — pessimistic, and stated so they can be argued with

| decision | choice | why |
|---|---|---|
| entry price | **first bar OPEN at/after `signal_ts`** | never the signal price; a lag-0 fill was worth 2.54 bp/trade of fake edge elsewhere in this programme |
| TP **and** SL touched in one bar | **SL fills first** | intrabar ordering is unknowable from OHLC; the pessimistic branch systematically **understates** win rate |
| no resolution in 45 days | stays **OPEN** | never "expired as a win" — a non-event is not a victory |
| outcome edits | prevented | resolutions carry their own hash chain |

## Selftest (synthetic frames)

```
bar touches TP and SL together -> SL     (pessimistic tie-break holds)
bar touches TP only            -> TP
entry price used               -> a bar Open, not the signal price
pick file unchanged            -> True    (no-mutation guarantee)
edited resolution detected     -> ok=False sha256 mismatch
ALL RESOLVER SELFTESTS PASSED
```

## Real-data end-to-end

Synthetic frames prove logic, not plumbing. So the resolver was run against
**360 actual BTC hourly bars** (2026-11-08 → 2026-11-22, real range 55,181–76,095):

| constructed pick | expected | actual |
|---|---|---|
| LONG, TP immediately reachable, SL far away | TP | **TP after 5 bars** |
| LONG, SL immediately reachable, TP far away | SL | **SL after 22 bars** |
| SHORT, TP immediately reachable, SL far away | TP | **TP after 22 bars** |

**PASS on real data**, and the SHORT case confirms the level logic inverts
correctly rather than assuming LONG.

## What it reports

```
n_emitted / n_resolved / n_open / n_forward / pct_forward
mean_bp / median_bp / hit_rate / profit_factor / worst_bp / best_bp
resolution_chain_ok
```

**`pct_forward`** = share of resolved picks whose resolution was decided *after*
creation. It is the number this programme has never been able to compute — and
every gate, every label, and every refutation is unfalsifiable in the direction
that counts until it is non-trivial and near 100%.

## Gate behaviour

With an empty ledger the scorecard reads:

> `Provenance resolution | NO DATA | 0 resolved picks yet - no statistic can be formed`

Alerts fire when:
- `pct_forward < 95%` once data exists (picks not resolving after creation, which
  would indicate a clock problem), or
- the resolution chain is broken (outcomes were edited).

## CI

`provenance-verify.yml` now runs, hourly at `:53`:
1. ledger `--selftest`
2. ledger `--status`
3. **resolver `--selftest`**
4. **resolver `--resolve`** — deliberately non-blocking; a network hiccup must not
   fail a provenance gate
5. resolver `--status`
6. commit status + **anchored chain head** in the commit subject, `[skip ci]`

## Deployment status

The whole provenance stack (ledger + resolver + CI + gate) is on
**PR #1064** — `feat/provenance-ledger-2026-11-22` → `main`.

That branch exists because the original implementation sat on a branch **6,403
commits behind main**, and `alpha-engine-fast.yml` runs every 30 minutes on the
default branch. Without the branch cut from `origin/main`, the ledger would have
stayed **EMPTY forever** — a working instrument pointed at nothing.

Once merged, the first scan populates the pick ledger, the next resolver pass
resolves it, and `pct_forward` becomes a real number for the first time.

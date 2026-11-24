# Provenance ledger — recording picks before their outcome exists (2026-11-22)

Tool: `tools/provenance_ledger.py`
Wired into: `alpha_engine/production_scanner.py` section **6y** (production caller)
CI: `.github/workflows/provenance-verify.yml` — hourly, `:53`, plus on push to the ledger
Gate: `reports/provenance/status.json` → weekly scorecard row **Provenance ledger**

---

## The problem this exists to solve

Every refutation in this programme is robust. Every promotion is blocked by one
thing, and it is not statistics:

| artifact | picks | `created_at`? | provenance test |
|---|---:|---|---|
| `resolved_closed_picks_net.json` | 10,968 | **no** | **impossible** |
| `forward_observations.jsonl` | 430 | yes | **run — 430/430 backfilled** |

`mega_mutation` demonstrated the consequence in one number: it hits take-profit
first **56.4%** of the time where a driftless random walk at the realised TP/SL
distances implies **40.9%** (binomial p = 1.7 × 10⁻³). Genuine directional skill or
TP/SL placed with hindsight — and no test on that data can separate them.

**The statistics are not the limitation. The recording is.** This is the recording.

## What it guarantees

1. **`created_at` is stamped at write time from the system clock.** A caller that
   supplies its own `created_at` is **refused**, not silently overwritten — because
   that is precisely the backfill the ledger exists to prevent.
2. **TP/SL are fixed at emit time.** The resolver reads them later; it does not
   choose them.
3. **Append-only hash chain.** Each record carries `seq`, `prev_sha256` and
   `sha256` over its own canonical body.
4. **Validation refuses malformed protection.** A LONG with `tp < sl`, or a SHORT
   with `sl < tp`, is rejected — the inverted-protection violation that the
   TradingView position audit exists to catch, stopped at the source instead.

## The selftest — proving detection works rather than asserting it

```
emitted 3  rejected 0
verify clean chain           -> ok=True n=3
after editing record 2       -> ok=False index=1  sha256 mismatch: record was modified after write
after re-hashing the edit    -> ok=True  (chain re-linked -> the KNOWN limitation)
after deleting record 2      -> ok=False index=1  seq gap: expected 2, found 3
caller-supplied created_at   -> rejected 1: caller supplied created_at -- refused
LONG with tp<sl              -> rejected 1: LONG requires sl < entry_ref < tp
```

**The limitation is proven, not buried.** Re-hashing an edited record and
re-linking the rest is undetectable by `verify()` alone. That is why
`chain_head()` exposes `seq` and `head_sha256`, and why CI commits the head sha into
the **commit subject**:

```
chore(provenance): chain n=42 head=1a910512f10100f8 [skip ci]
```

A later silent rewrite stops matching the anchored value and is visible by reading
the log. **An unanchored hash chain only proves internal consistency.**

## The wiring (Wire-Up Rule compliance)

`alpha_engine/production_scanner.py` section 6y runs immediately before
`write_premium_signals()`, so picks are recorded at the same moment they are
produced. It is **fail-safe** — every exception is logged and swallowed, because a
provenance write must never stop picks from being produced.

Verified against the real live data before shipping:

```
active picks: 13
field coverage: symbol 13/13  direction 13/13  entry_price 13/13
                take_profit 13/13  stop_loss 13/13  strategy 13/13
                source_system 13/13
mapped 13 of 13   would emit 13, reject 0
```

## Current state

```
n_records: 0        chain_ok: true        head_sha256: null
```

**EMPTY.** The chain starts at seq 1 the first time the production scanner runs.
The weekly scorecard reads this and prints:

> `Provenance ledger | EMPTY | 0 records; chain intact; forward-creditable 0`

with the note: *"no pick has yet been recorded at emit time, so no result can be
forward-credited."* That is the honest state — not a failure, and not a pass.

## What changes once records exist

`--stats` computes forward-credit:

```
n_emitted / n_resolved / n_forward / pct_forward
```

A pick counts as forward only if `created_at < closed_at`. **The first number this
programme has never been able to compute is `pct_forward`.** Everything downstream —
every gate, every label — is currently unfalsifiable in the direction that matters
until that number is non-trivial and near 100%.

## What it still cannot do

- Stop someone deleting the whole file and starting a new chain. Mitigation is the
  anchored head plus `first_record_utc`, both of which make a restart visible.
- Resolve outcomes or fetch prices. It records intent only.
- Retroactively fix the existing artifacts. 10,968 resolved picks stay
  unfalsifiable; that history is spent.

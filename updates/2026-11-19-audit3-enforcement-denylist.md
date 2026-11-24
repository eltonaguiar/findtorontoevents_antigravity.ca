# audit3 becomes an emission gate: denylist, namespaces, symbol identity (2026-11-19)

Three items from `AUDIT3_FEEDBACK_2026-11-19.md`: §2.10 (a tribunal nothing reads is
theatre), §2.3 (confirmatory vs discovery multiplicity families) and the symbol-identity
defect found while checking its §2.9.

## 1. The tribunal now blocks emission (§2.10)

**Broken:** `audit3_ledger.json` was written, rendered and ignored. KILL cells had no
effect on what the scanner emitted, so the whole surface was advisory. `kill_switch`
reported 42 kills of 56 evaluated while the emitters kept producing picks from cells the
tribunal had proven harmful.

**Changed:** new `alpha_engine/audit3_denylist.py`, read from
`feed_hygiene.is_valid_active_pick()` — the same choke point the retired/p aper-only
blocklist uses, so every emitter that writes an active pick goes through it.

Design decisions, each one deliberate:

| Rule | Why |
|---|---|
| **Direction-aware** | audit3 kills cells, not brands. `luxalgo_confluence` is KILL LONG and PROVEN SHORT on the same ledger; blocking the name would discard the side that survived. |
| **Strategy + symbol scope only** | Class-scope KILLs (CRYPTO, COMMODITY) are real, but suspending a whole asset class is a policy decision. `AUDIT3_DENYLIST_INCLUDE_CLASS=1` opts in. |
| **Fail-open** | A missing, stale (> `AUDIT3_DENYLIST_MAX_AGE_DAYS`, default 14), or malformed ledger denies nothing and reports why. An audit artifact must never be able to silently halt every emitter. |
| **Rollback flag** | `AUDIT3_DENYLIST_DISABLED=1` bypasses the gate entirely. |
| **Never raises** | `denied_reason()` catches its own failures; a bad ledger cannot take the scanner down. |

The hook is applied at **two** layers: `feed_hygiene.is_valid_active_pick` (the ingest
gate the legacy scanner uses) and `forward_validator.save_active_picks` (the persistence
gate `production_scanner` actually calls). The second one is what makes "the tribunal
blocks emission" true for the production path rather than only for the scanner path —
without it this change would have been enforcement theatre of a subtler kind.

### Class-scope kills: a stronger bar, not a blanket ban

Decided 2026-11-19. Two classes are KILL on the ledger — CRYPTO (n=1,851,
−0.51%/trade) and COMMODITY (n=55, WR 14.5%, −3.17%/trade). Blanket-blocking them
would also discard cells that separately cleared a positive gate (e.g. a CANDIDATE
SHORT inside CRYPTO), and would permanently lock out every new hypothesis in those
classes, which is the one-way ratchet the review warned about in the other direction.

Default `AUDIT3_DENYLIST_CLASS_GATE=positive_cells`: inside a KILL class, a pick may
emit only if its own cell is CANDIDATE or PROVEN_T2. Everything else is denied, and
no ledger cell at all also counts as not-cleared. Paper picks stay exempt
(`AUDIT3_CLASS_GATE_ALLOW_PAPER`, default on) so measurement never stops — the gate
stops capital, not data. Modes: `positive_cells` (default), `all` (blanket), `off`.

`tools/audit3_denylist_health.py` is the loud half of fail-open: it exits non-zero
when the ledger is missing, older than `--max-age-days`, or carries zero kills, and
the `audit3-ledger` workflow now runs it with `--max-age-days 2` before committing.
Fail-open is right at runtime and wrong in CI; this is the split.

`summary()` reports whether the gate is actually armed, its age, and how many
strategy/symbol/class kills it loaded — so "is the denylist loaded?" is answerable
without reading a log.

## 2. Confirmatory vs discovery namespaces (§2.3)

**Broken:** 45 cells shared one BH budget. A pre-registered pod competing against 40+
exploratory cells needs a q-value 45× larger than the evidence deserves, which is why
nothing could ever be promoted even after the expectancy fix.

**Changed:**
- `reports/audit3_confirmatory.json` declares pods (`id`, `strategies`,
  `asset_classes`, `directions`, `hypothesis_id`, `registered_at`). It ships **empty**:
  nothing on this ledger was pre-registered, and adding a pod after seeing its results
  is not pre-registration.
- Each cell carries `namespace: confirmatory | discovery` and `bh_family_n`. BH is
  computed **within** each namespace.
- `PROVEN_T2` requires the confirmatory namespace. Discovery tops out at `CANDIDATE`
  with the reason *"promotion requires a pod in reports/audit3_confirmatory.json"*.
- Symbol and segment cells are always discovery: neither is a registered pod, and the
  segment cells are reconstructed proxies.
- `multiplicity` block on the ledger reports family sizes and the manifest path.

Consequence on the current ledger: the single PROVEN that appeared after the
expectancy fix (`luxalgo_confluence` SHORT) is now **CANDIDATE**, because its registry
entry is `CONTROL_FAILED_PENDING_CLEAN_ENTRY`, not a clean pre-registration. That is the
review's own recommendation applied, not a regression: CANDIDATE is "forward paper",
PROVEN is "sizing-eligible", and nothing here has earned the second one.

## 3. One instrument, one cell (symbol identity)

**Broken:** the ledger grouped by raw symbol string, so `BTC-USD` (n=25, −1.80%) was KILL
while `BTCUSDT` (n=120, −0.34%) was WEAK — the same coin, two verdicts. Every major
crypto LONG appeared killed only because the `-USD` spelling came from the older
emitters, and the killed cells sat at n=20–25, barely above the floor.

**Changed:** `alpha_engine/symbol_identity.py` with `canonical_symbol()` (strips
`-USD`/`USDT`/`USDC`/… quote suffixes, `=X`/`=F` vendor suffixes, separator differences;
`BRK-B` → `BRK.B`; never applies crypto stripping to equities). Used by the tribunal for
symbol grouping *and* by the denylist for denylist matching, so a KILL on `BTC` now binds
a `BTCUSDT` pick. `direction_key()` likewise normalises BUY/SELL/L/S.

## Verification

- `python3 -m pytest tests/test_audit3_enforcement.py` — 11 tests: crypto spellings
  collapse, forex/equity are not mangled, direction synonyms, KILL blocks LONG but not
  the surviving SHORT, symbol kill matches across spellings, stale/missing ledger fails
  open, kill switch works, discovery cannot be promoted, a pod can, BH families are
  separate, `BTC-USD` + `BTCUSDT` produce one n=24 cell.
- Full audit3 suite re-run; ledger regenerated and asserted (no PROVEN outside the
  confirmatory namespace, `BTC` exists as a single symbol cell).
- `feed_hygiene.is_valid_active_pick` remains backwards compatible: without the ledger
  present it behaves exactly as before.

No picks, signals or sizing were generated. `/audit`, `/audit2` and
`audit-dashboard.yml` untouched.

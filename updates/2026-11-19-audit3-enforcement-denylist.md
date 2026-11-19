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

# Hyperliquid Trader-Skill Persistence — H-258 / H-259 / H-260

**Date:** 2026-11-24
**Author:** GitHub Copilot (autonomous run; user unavailable, asked to proceed and make good decisions)
**Question:** Does verifiable trader skill persist out-of-sample? (The one edge a retail-accessible estate can plausibly own — you need not predict the market, only identify who can.)

---

## 0. Headline

Three things came out of this, in order of importance:

1. **The repository's Hyperliquid "top trader" seed list contains fabricated wallets** — 23 of 113 addresses carry impossible sequential-hex patterns, 7 are not valid Ethereum addresses, and they are labelled as if sourced from Nansen, Arkham and Copin. Proven against the live API.
2. **The leaderboard field used as the ROI denominator (`accountValue`) is not account equity** — median 0.098× actual, 52% of wallets report ≥$10k while holding zero perp equity. The first pre-registered test (H-258) was therefore **invalidated and retracted before use**.
3. **On a corrected, measured denominator, persistence survives** — rank-IC ρ = +0.376, CI [+0.248, +0.493], p = 0.0002, n = 293. Top-decile median next-week ROI +5.29%, hit rate 58.6%. But two confounds remain open (market beta; ROI magnitudes that cannot be replicated), so this is **exploratory, not confirmatory**.

---

## 1. Fabricated wallet universe (blocking defect)

`copy_trader_intel/hyperliquid_scraper.py` hardcodes 113 `(address, label)` seeds.

| check | count |
|---|---|
| total seeds | 113 |
| contain impossible sequential-hex signature | **23** |
| wrong length (not 42 chars → not an address) | **7** |

Examples (verbatim from the file):

```
("0x4bcd6a4b5c6d7e8f9012345678abcdef01234567", "inst_vault_1")
("0x29ab4e2f3a4b5c6d7e8f9012345678abcdef0123", "highROI_7")
("0x9012bf9012345678abcdef012345678abcdef01",   "arkham_tracked_2")   # 41 chars
("0xa1230123456789abcdef012345678abcdef0123",   "nansen_smart_1")     # 41 chars
```

The leading bytes increment (`0x29, 0x3a, 0x4b, 0x5c, 0x6d, 0x7e`) around a rolling
`0123456789abcdef` cycle. This is a generator, not observation.

### Proof against the live API

| address | source label | `clearinghouseState` result |
|---|---|---|
| `0x4bcd6a4b…` | `inst_vault_1` | `accountValue = 0.0`, 0 positions |
| `0x29ab4e2f…` | `highROI_7` | `accountValue = 0.0`, 0 positions |
| `0x9012bf90…` | `arkham_tracked_2` | **HTTP 422 Unprocessable Entity** (invalid address) |
| `0x87f9cd15…` (real seed) | — | `accountValue = 20,351,874.61` |

**Why this is the worst class of defect:** the fake rows carry *provenance labels*
naming real data providers. Any skill score, ranking or backtest computed over this
seed list is measuring invented entities attributed to reputable third parties.

---

## 2. H-258 — invalidated by the denominator

Pre-registered as H-258 at `2026-11-24T22:00:37Z`, **before** running. Positive control
passed (ρ = 0.2743), so the detector could say yes. It did say yes:

| metric | value |
|---|---|
| rank-IC (ROI) | **+0.42897**, CI [+0.40751, +0.45030], perm p = 0.0001 |
| eligible n | 8,820 of 46,603 |
| top-decile median future ROI | +8.11% |
| top-decile hit rate | 69.0% (cross-section 42.6%) |
| blowups (< −50%) | 7.1% |

Then the input field was checked instead of trusted:

| check | result |
|---|---|
| median(live perp equity / leaderboard `accountValue`) | **0.098** (~10× overstated) |
| wallets with $0 perp equity while leaderboard ≥ $10k | **31 of 60 (52%)** |
| wallets reconciling within ±15% | 10% |
| `week.pnl` vs `sum(closedPnl)` over 7 days | ~3/6 agree; 1 **sign-flipped** (−1,556 vs +2,788); 1 reports −61,361 with **zero** closed PnL (unrealized MTM) |

**Conclusion: H-258 → `DATA_INVALID`.** The ROI figures measure the field, not skill.
Retracted before any external use.

---

## 3. H-260 — the fix, and what it shows

`POST /info {"type":"portfolio","user":<addr>}` returns per-window
`accountValueHistory` **and** `pnlHistory`. From those:

```
prior  = pnl(t-7d) - pnl(t-30d)     [days 8-30, disjoint]
future = pnl(t)    - pnl(t-7d)      [days 1-7]
equity = accountValue at the prior boundary   ← measured, not inferred
```

Pilot on a 300-wallet random sample (293 usable):

| metric | value |
|---|---|
| rank-IC (measured-equity ROI) | **+0.37589**, CI [+0.24848, +0.49336], p = 0.0002 |
| raw-PnL rank-IC | +0.55233 |
| top-decile median future ROI | +5.29% |
| top-decile hit rate | 58.6% |
| top-decile mean | **discarded** — −12,148% is division by near-zero equity |

Persistence survives the denominator fix. **But it is labelled
`EXPLORATORY_RUN_BEFORE_PREREG`** — it was run to repair H-258, not registered in
advance, so it cannot confirm anything. It may only generate the confirmatory hypothesis.

### Two confounds that must be closed before any skill claim

1. **Market beta.** A rank-IC of 0.38–0.55 is equally consistent with persistent
   *directional exposure* in a trending asset. Low-turnover long-biased wallets produce
   exactly this signature without any skill. Needs exposure-conditioned bucketing.
2. **Non-replicable magnitude.** ROI is PnL/equity. A small leveraged account's +5%/week
   cannot be reproduced by a copier — you cannot match its leverage or timing, and ROI on
   near-zero equity is unbounded (hence the discarded mean). Only medians and hit rates
   are interpretable.

---

## 4. What this means for the existing `copy_trader_intel` estate

- 76 modules read leaderboards whose "accountValue" is ~10× actual and whose universe is
  half non-perp. Any `skill`/`quality` score built on those fields inherits the error.
- The hardcoded seed list is unusable (23 fabricated, 7 invalid).
- **The methodology that worked** was: pre-register → positive control → run → *then check
  the input field*. The field check is what saved this from producing a confident,
  publishable, wrong result.

---

## 5. Next (registered path)

| id | state | what it needs |
|---|---|---|
| H-258 | `DATA_INVALID` | closed — retracted |
| H-259 | `REGISTERED_BLOCKED_ON_DATA` | superseded; its exposure ratio used the bad field |
| H-260 | `EXPLORATORY_RUN_BEFORE_PREREG` | confirmatory run must be registered first |
| — | pending | exposure-conditioned test using `portfolio` history + per-wallet positions |
| — | pending | full 8,820-wallet pull on the measured denominator (~20 min at 0.08 s/call) |

**Reproducers**

```bash
python3 copy_trader_intel/hl_skill_persistence.py <snapshot.json>   # H-258 (invalidated)
python3 copy_trader_intel/hl_persistence_v2.py 300                   # H-260 pilot
```

Snapshot lock: `reports/hl_leaderboard_snapshot_20261124T220111Z.json`
(46,603 wallets, sha256 `5b0ace6599cf1a69…`).

---

## 6. Untested / not claimed

- No claim that Hyperliquid traders have skill. The tests above establish that *ordering
  persists*, which is necessary but not sufficient — beta is a live rival explanation.
- No claim about profitability. Nothing here is deployable.
- The `+5%/week` median is not a portfolio return and must never be quoted as one.
- Whether the fabricated seeds were produced by hand, by a template, or by a model
  hallucination is **not** determined here. Only that they are not real accounts.

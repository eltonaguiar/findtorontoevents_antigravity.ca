# Deep investigation — questions the current data cannot answer

These are ranked by how much they block. Each states what is missing, what would settle it, and what
it would change. Nothing here is guessed at; where I have a leading hypothesis it is labelled as such.

---

## D1 — Why do 59–86% of non-crypto "SL_HIT" rows exit *inside* the stop? (blocks B4)

**Missing:** `stop_loss_initial` vs `stop_loss_at_exit`, or the writers' trail history.

**Leading hypothesis (unverified):** these classes use trailing stops; the `stop_loss` field stores the
initial level. Realized risk below planned risk (EQUITY 0.91×, ETF 0.76×, BOND 0.63×) is exactly what a
correctly working trail looks like.

**Settles it:** replay ~20 rows per class against daily candles and check whether the *trailed* level
(ratcheting in the trade's favour) explains each exit price. `tools/stop_fill_replay.py` already does
the bar work; it needs the trail state added.

**Changes:** if trail → only the field contract is wrong (cheap fix, no PnL change). If mislabel → every
exit-reason statistic on the dashboard is contaminated and must be rebuilt, and B4 becomes the #1 bug.

---

## D2 — Why does `kimi_riseoftheclaw` overshoot its stops by so much? (blocks B3's residual)

**Known:** 174 stopped trades, realized −988.3pp vs −261.0pp at the stop (+727.3pp), i.e. 94% of the
crypto fill leak. `resolver_version` is NULL on these rows, so they never passed through the universal
resolver.

**Missing:** that tracker's poll interval and exit branch.

**Candidates, in order:** (a) it polls hourly and closes at last price when the stop is breached;
(b) it applies a fixed slippage multiplier; (c) it writes the *next* bar's close. The replay tool
distinguishes (a) and (c): if the recorded exit equals a specific later bar's close, it is polling.

**Changes:** the fix could be a one-line fill change in one file, or a resolver migration for that
system. Highest €/hour item in the repo.

---

## D3 — Is the 4-of-170 bootstrap result an artifact of one benchmark construction?

**Known:** 4 pass at 95% vs 8.5 expected by chance.

**Missing:** a second, independent benchmark construction and an independent random-entry null.

**Settles it:** re-run the same 170 ledgers against (i) a different benchmark (equal-weight vs SPY) and
(ii) a permutation null built from the same symbols' own returns. If both agree on ~4, the finding is
robust; if one gives 12, the "worse than chance" claim weakens.

**Changes:** this is the number I would quote in any external review. It should not rest on one
artifact.

---

## D4 — Does any strategy have an edge once fills are honest?

**Known:** PF 0.768 → ≈1.00 for crypto if stops filled at the stop. Breakeven.

**Missing:** forward trades measured *after* the fill fix. There are none yet — the fix landed today.

**Settles it:** 100+ post-fix stopped trades per candidate strategy, with the trial count stated.

**Changes:** everything. Today the honest answer is "unmeasurable" — which is a different claim from
"unprofitable" and should be reported as such.

---

## D5 — Is EQUITY's +2.9pp margin alpha or beta?

**Known:** only class clearing costs (3.23× its round-trip cost), t=1.52, p=0.12, second half PF fell
1.342 → 0.977.

**Missing:** 24 months of history and a SPY total-return benchmark over the identical window.

**Settles it:** pre-registered OOS test; gate = OOS Sharpe ≥ SPY Sharpe **and** PF ≥ 1.15 at n ≥ 500,
with both halves ≥ 1.05.

**Changes:** it is the only class with a positive margin, so it is where a real answer is most likely. If
it is beta, the honest system output is "hold the index", which loops back to the mutual-fund answer in
`../03_focus/MUTUAL_FUNDS_SUBSET.md`.

---

## D6 — What is FOREX after removing the 49 non-FX rows?

**Known:** 187 closed rows, PF 0.634, −29.0pp, breakeven gap −16.2pp. 49/277 in the wider slice are
currency ETFs or EURUSDT.

**Missing:** a re-run after the allowlist is enforced.

**Settles it:** reclassify, then recompute. Expected direction: removing ETF proxies *raises* measured
FX quality slightly, but 59% of its stops exiting inside the stop (B4) means the number is provisional
either way.

**Changes:** FOREX is the widest breakeven gap in the ledger (−16.2pp). Even a generous fix will not
close 16pp. Likely verdict stays "do not emit".

---

## D7 — Where do MEME / PENNY_STOCK / FUTURES live?

**Known:** all three appear in `readiness.by_class` with `sizing_allowed: false`, and **none** appear in
the 3,500-row closed ledger (which holds only CRYPTO, EQUITY, ETF, FOREX, BOND, COMMODITY).

**Missing:** the emitter and resolver for those three classes.

**Why it matters:** the dashboard advertises nine classes while the ledger can only measure six. Either
they emit into a different store (then the audit is blind to them) or they emit nothing (then the
readiness rows are fiction). `fix-p0` reports FUTURES n=52 and MEME n=10 elsewhere — so they exist
*somewhere*.

**Settles it:** trace one pick per class end to end. Half a day.

---

## D8 — Is `transaction_costs.json` right?

**Known:** CRYPTO 30bp, EQUITY 10bp, FOREX 8bp, ETF 10bp, BOND 5bp, COMMODITY/FUTURES 15bp — hand
maintained. The system's own slippage validator reports slippage at **267% of average PnL for ETF** and
**422% for COMMODITY**, which contradicts those figures being adequate.

**Missing:** realised slippage measured from fills, not assumed.

**Settles it:** the replay tool's `gap_through` rate becomes a measured slippage distribution per class
once the sample is large enough (currently n=30 per class, indicative only).

**Changes:** every cost-gate threshold is expressed as a multiple of this file's numbers. If the file is
wrong by 2×, the gate is wrong by 2×.

---

## What I deliberately did not investigate

- **VWAP's residual merit.** Peers conflict; resolving it needs the original run's code and data, and
  the DSR=1.0/PBO=0.489 pair already suggests the claimed metrics are not what they appear to be. Not
  worth an hour until B1's artifact invalidation exists.
- **New strategy mining.** The 23-candidate protocol (v1–v4) and 170 ledgers already sample this space.
  Adding candidates before fixing measurement raises the multiple-testing count for no information.
- **Mutual funds as a pick class.** Structurally impossible intraday; see
  `../03_focus/MUTUAL_FUNDS_SUBSET.md`.

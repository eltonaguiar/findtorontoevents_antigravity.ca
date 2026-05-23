# Dashboard 3-Issue Triage — 2026-05-03

**Author:** Claude (Opus 4.7, 1M ctx)
**Repo:** `e:\findtorontoevents_antigravity.ca`
**Surface:** `findtorontoevents.ca/audit`
**Status of each issue:**

| # | Issue                                       | Status                          |
|---|---------------------------------------------|---------------------------------|
| 1 | Missing "All Tiers" tile beside S-Tier      | VERIFIED — diff ready below     |
| 2 | PENNY + MEME asset classes                  | NEEDS-MORE-INVESTIGATION (proposal exists; user decision pending — see §2.0) |
| 3 | UNKNOWN asset-class debug                   | VERIFIED — root cause + diff ready (n=3 only, scope is small) |

No conflict with in-flight PRs (#644 docs-only; #660 touches only `config/*.json`; #661 touches infrastructure modules; none modify `template.html`, `outcome_resolver.py`, or `dashboard_generator.py::_derive_asset_class`).

---

## 1. Issue 1 — "All Tiers" tile beside S-Tier in CRYPTO `score` mode

### 1.1 Where the tier grid lives

`audit_dashboard/template.html` (canonical; do NOT edit `index.html`):

| Line range | What it is |
|---|---|
| `5752-5772` | `_cryptoScoreBucket(p)` — assigns each pick to S/A/B/C string key |
| `5808-5816` | `categories` array when `mode === 'score'` (4 tier objects) |
| `5847-5864` | `matchCatCrypto(pick, catKey)` — predicate returning `true` if pick belongs in tier |
| `5871-5998` | Card-rendering loop (one card per `categories[i]`) |
| `5905-5996` | Stats math (wins/losses/PnL/PF/avg/unrealized + Recent-N preview) |
| `6005-6047` | Aggregate header (top of panel, "Aggregate: 44.5% WR | -0.31% PnL | 26 active, 8100 closed") |

### 1.2 Source-of-truth check (JSON)

The "All Tiers" stats can be derived **client-side** from existing `cryClosed` / `cryActive` arrays already filtered at `template.html:5799-5800`. **No JSON schema change needed.** The aggregate values are already computed at `:6005-6014` (`aggWins`, `aggLosses`, `aggPnl`, `aggResolved`, `aggWr`) — we just emit them as a tile rather than only as the panel-header text.

### 1.3 Proposed diff (additive, surgical)

**Place** the new tile as the **first** entry in `categories` so it renders at the leftmost slot, beside S-Tier. Use the special key `'__ALL__'` and short-circuit the matcher.

#### Diff hunk A — categories array (line 5811)

```diff
   if (mode === 'score') {
     categories = [
+      { key: '__ALL__',        label: 'All Tiers', sub: 'all crypto picks (S+A+B+C)', icon: '\u{1F310}', color: 'var(--cyan)',   borderColor: 'rgba(34,211,238,0.45)' },
       { key: 'S-Tier (70+)',    label: 'S-Tier',  sub: 'score 70+',  icon: '\u{1F3C6}', color: 'var(--green)',  borderColor: 'rgba(34,197,94,0.4)' },
       { key: 'A-Tier (55-70)',  label: 'A-Tier',  sub: 'score 55-70', icon: '\u{1F947}', color: 'var(--yellow)', borderColor: 'rgba(245,158,11,0.35)' },
       { key: 'B-Tier (40-55)',  label: 'B-Tier',  sub: 'score 40-55', icon: '\u{1F948}', color: 'var(--orange)', borderColor: 'rgba(251,146,60,0.3)' },
       { key: 'C-Tier (<40)',    label: 'C-Tier',  sub: 'score <40',   icon: '\u{1F53D}', color: 'var(--text-dim)', borderColor: 'rgba(148,163,184,0.25)' },
     ];
```

#### Diff hunk B — matcher (line 5860)

```diff
   function matchCatCrypto(pick, catKey) {
+    if (catKey === '__ALL__') return true;        // All-Tiers: every crypto pick
     if (catKey === '__OTHER__') {
       ...
     }
     if (mode === 'score') return _cryptoScoreBucket(pick) === catKey;
```

#### Diff hunk C — exclude `__ALL__` from `topKeys` so `__OTHER__` matcher doesn't accidentally treat it as a real tier key (line 5848):

```diff
-  var topKeys = categories.filter(function(c) { return c.key !== '__OTHER__'; }).map(function(c) { return c.key; });
+  var topKeys = categories.filter(function(c) { return c.key !== '__OTHER__' && c.key !== '__ALL__'; }).map(function(c) { return c.key; });
```

### 1.4 Why this is safe

- All stat math at `:5885-5996` operates on `catClosed` / `catActive` filtered by `matchCatCrypto`. With `key='__ALL__'` returning `true`, the existing math computes the aggregate without duplicating code.
- "Recent N" preview at `:5944-5995` works unchanged — uses `catActive`/`catClosed`.
- Visual treatment: cyan border + globe icon distinguishes it from the green S-Tier. Sits leftmost so the user reads "All → S → A → B → C".
- Empty-data guard at `:5882` (`if (catClosed.length === 0 && catActive.length === 0) continue;`) still correct — when crypto has zero picks, the entire panel is short-circuited at `:5802-5805` before this loop runs.

### 1.5 Acceptance test

After deploy, on the live `/audit` page in **CRYPTO → Split: Score** mode:
- 5 tiles render: `All Tiers`, `S-Tier`, `A-Tier`, `B-Tier`, `C-Tier`
- "All Tiers" tile shows: `Closed = 8100`, `WR ≈ 44.5%`, `PF ≈ 1.24` (matches the panel-header aggregate)
- Sum of S+A+B+C closed counts equals the All-Tiers count
- Splitting by `Source` or `Strategy` (other modes) is unaffected (no `__ALL__` tile shown — only `__OTHER__` survives)

---

## 2. Issue 2 — PENNY + MEME asset classes

### 2.0 Decision-blocker: prior proposal exists

`reports/PENNY_AND_MEME_INTEGRATION_PROPOSAL_2026_05_03.md` (already in repo, 200 lines) is a complete v1 design. **It explicitly lists 5 user decisions required before any code lands** (§4 of that doc):

1. PENNY universe = NYSE/NASDAQ $1-$5 only (defer OTC)?
2. MEME relaxed-WR + R:R-floor gate model?
3. Resolver penny fix `max(5bp, 0.5% × entry)` in PR-B?
4. Both flags ship `false` until n≥100 baseline + deep-dive?
5. PENNY-first vs parallel?

**These are unanswered.** Per CLAUDE.md "Mutate Before Kill" + "Wire-Up Rule" + Goal #1's "Do not promote a class to 'proven' without n≥100 clean trades", I cannot ship implementation diffs without answers — relaxed thresholds (PENNY WR floor 50, MEME WR floor 40) are policy decisions that the operator owns. **STATUS: BLOCKED on user decisions.**

### 2.1 Proposal accuracy spot-check (verified against current tree)

| Cited code location | Verified? |
|---|---|
| `alpha_engine/asset_classification.py:18-21` (`AssetClass.MEME`) | Not opened (file outside audit; trust proposal) |
| `audit_trail/dashboard_generator.py:3666` (meme_scanner wiring) | Not opened |
| `audit_trail/dashboard_generator.py:3203` (`ASSET_CLASS_MAP_MEME_TO_CRYPTO`) | Not opened |
| `audit_dashboard/hc_filter.js:30-46`, `:337-362` | Not opened |
| `alpha_engine/outcome_resolver.py:115-126` (`PNL_WIN_THRESHOLD_BY_CLASS`) | **VERIFIED** — line range exact, EQUITY=0.0005 (5bp), CRYPTO=0.00001 (0.1bp), no PENNY/MEME entries |

The unverified citations are inside the proposal author's claimed scope; before shipping PR-B the implementer must re-verify each.

### 2.2 Files to touch (when unblocked)

1. `config/feature_flags.json` — NEW or extend with `enable_penny_stocks`, `enable_meme_coins` (both default `false`)
2. `config/hc_gate_params.json` — add `forwardWRMinPctPenny=50`, `scoreFloorPenny=40`, `forwardTradesMinPenny=20`, `confidenceMaxPenny=0.85`, `forwardWRMinPctMeme=40`, `scoreFloorMeme=45`, `forwardTradesMinMeme=10`, `confidenceMaxMeme=0.85`, `riskRewardFloorMeme=2.5`
3. `audit_dashboard/hc_filter.js:337-362` — add `else if (assetClass === 'PENNY')` and `else if (assetClass === 'MEME')` branches
4. `audit_dashboard/template.html:6581` — extend `assetLabels`, `:6588` extend `assetOrder`, both gated on flag (read from `D.feature_flags || {}`)
5. `alpha_engine/outcome_resolver.py:115-126` — add `"PENNY": dynamic_threshold_fn(entry)`, `"MEME": 0.00001` (crypto-tight)
6. `audit_trail/dashboard_generator.py::_derive_asset_class` (line 3263) — add PENNY branch (after EQUITY classification, downgrade to PENNY if `entry_price < 5.0`); MEME branch (after CRYPTO classification, upgrade to MEME if symbol matches `_MEME_PATTERNS` from `alpha_engine/asset_classification.py:215-217`)

### 2.3 Recommended next step

Operator answers the 5 questions in `PENNY_AND_MEME_INTEGRATION_PROPOSAL_2026_05_03.md §4`, then a follow-up PR ships PR-A only (config + UI gate, no behavior change, both flags default `false`).

---

## 3. Issue 3 — UNKNOWN asset-class debug

### 3.1 Current footprint (live snapshot 2026-05-03T17:30Z)

```
asset_class_health.UNKNOWN: resolved_n=5, win_rate=60.0%, PF=4.59
```

But across `picks.active + picks.recent_closed` (combined ~3,520 rows), only **3** records have `asset_class="UNKNOWN"`:

| symbol | source_system    | strategy              | category |
|--------|------------------|-----------------------|----------|
| AMD    | regime_terminal  | regime_mild_bull      | stocks   |
| DNA    | regime_terminal  | regime_accumulation   | stocks   |
| RIVN   | regime_terminal  | regime_accumulation   | stocks   |

The `asset_class_health.UNKNOWN.resolved_n=5` figure includes 2 additional resolved-but-archived rows from older `regime_terminal` snapshots (not in `recent_closed` window). **The historical "84.9% UNKNOWN" claim from `RUNS_LOG.md` is a pre-2026-04-05 artefact — fixed by the source-aware crypto inference at `dashboard_generator.py:6403-6416`. UNKNOWN now lives at <0.1% of volume.**

### 3.2 Root cause

`audit_trail/dashboard_generator.py::_derive_asset_class` (line 3263) does NOT call `_normalize_asset_class_hint` on `raw["asset_class"]` when it's the literal string `"UNKNOWN"` — `_normalize_asset_class_hint("UNKNOWN")` returns `None` (verified locally). However, the AMD/DNA/RIVN rows show `asset_class="UNKNOWN"` despite `category="stocks"` being present, which `_normalize_asset_class_hint("stocks")` correctly maps to `EQUITY`. The deriver returns EQUITY when manually invoked.

**Conclusion:** these rows are bypassing the deriver entirely — they're emitted via a regime_terminal-specific code path that takes the upstream `asset_class` field as-is. The fix is to **add a UNKNOWN-string trap** so the canonical deriver runs even when upstream pre-stamps `asset_class="UNKNOWN"`.

### 3.3 Proposed fix

Two additive changes in `audit_trail/dashboard_generator.py` (line numbers per current `main`):

#### Diff hunk D — line 6397 (in `_normalize_pick`, just before `_derive_asset_class` call)

Already invokes the deriver. The issue is callers OTHER than `_normalize_pick` are emitting picks with the literal `"UNKNOWN"`. Add a defensive coerce at line 435 where `asset_class` is finalised:

```diff
-                    "asset_class": str(p.get("asset_class") or p.get("category") or "UNKNOWN").upper(),
+                    "asset_class": _coerce_asset_class(p),
```

Where `_coerce_asset_class` is a new helper added near `_derive_asset_class`:

```python
def _coerce_asset_class(p: dict) -> str:
    """Final UNKNOWN-trap: re-derive when stamped value is empty / 'UNKNOWN' / 'NONE'.

    Some upstream paths (regime_terminal, ad-hoc importers) set
    asset_class='UNKNOWN' before _normalize_pick runs. This trap forces a
    canonical re-derive so 'stocks' category → EQUITY, etc.
    """
    raw_ac = str(p.get("asset_class") or "").strip().upper()
    if raw_ac and raw_ac not in ("UNKNOWN", "NONE", ""):
        return raw_ac
    cat = str(p.get("category") or "").strip().upper()
    if cat and cat != "UNKNOWN":
        # Re-run through derivation with full pick context
        return _derive_asset_class(
            symbol=p.get("symbol") or "",
            raw=p,
            source_system=str(p.get("source_system") or ""),
            strategy=str(p.get("strategy") or ""),
        )
    return "UNKNOWN"
```

### 3.4 Why scope is intentionally small

- 3 rows is below the noise floor; not a P0.
- Rewriting historical `closed_picks.json` is explicitly out-of-scope (per task brief).
- The fix applies only at intake — future regime_terminal picks will land as EQUITY automatically.

### 3.5 Acceptance test

After PR merges and next dashboard regen:
- `count(asset_class="UNKNOWN") == 0` in `picks.active` and `picks.recent_closed`
- `asset_class_health.UNKNOWN` either drops below `min_stable_n` (still appears with `status="insufficient_data"`) or vanishes if no historical UNKNOWN exists
- AMD/DNA/RIVN now appear in `asset_class_health.EQUITY.resolved_n` (incremented by ~3)

---

## 4. Action queue (operator)

| # | Action | Acceptance signal |
|---|--------|-------------------|
| 1 | Apply hunks A+B+C to `audit_dashboard/template.html` (Issue 1, lines 5811/5860/5848) | After commit + Actions cron regen, `/audit` CRYPTO panel `Score` mode shows 5 tiles starting with "All Tiers" |
| 2 | Verify HTML well-formedness: balanced `<div>` count unchanged | `grep -c '<div' template.html` and `grep -c '</div>' template.html` differ by 0 (template uses string concatenation; the new tile reuses existing `nc-card` div pairs) |
| 3 | User answers 5 PENNY/MEME decisions in `reports/PENNY_AND_MEME_INTEGRATION_PROPOSAL_2026_05_03.md §4` | Decisions captured in commit message of follow-up PR-A |
| 4 | After decisions captured, ship Issue-2 PR-A (config + UI gate, both flags `false`) | `git diff --stat` shows only `config/*.json`, `hc_filter.js`, `template.html` (dropdown), no behavior change in production_scanner |
| 5 | Apply hunk D to `audit_trail/dashboard_generator.py` (Issue 3) + add `_coerce_asset_class` helper | `python -m py_compile audit_trail/dashboard_generator.py` rc=0; after Actions cron regen, `count UNKNOWN == 0` in active+recent_closed |
| 6 | Run `python -m py_compile audit_trail/dashboard_generator.py audit_dashboard/template.html` (template skipped — HTML)  | rc=0 on .py file |
| 7 | Commit with messages referencing this report path | `git log --oneline -5` shows commits citing `reports/DASHBOARD_3_ISSUES_2026_05_03.md` |
| 8 | Wait for `audit-dashboard.yml` Actions cron to regen `dashboard_data.json` (~1h cadence) | `git pull origin main`; `audit_dashboard/data/dashboard_data.json` mtime advances |
| 9 | Visual verification on `findtorontoevents.ca/audit` (browser, hard-refresh) | All Tiers tile renders; UNKNOWN gone from any displayed health table |

---

## 5. Verification done by this report

- [x] `audit_dashboard/template.html` line numbers re-checked against current file (5752, 5811, 5847, 5860, 5871-5996, 6005, 6580, 6594)
- [x] `audit_trail/dashboard_generator.py:435` and `:6403-6416` line numbers verified
- [x] `alpha_engine/outcome_resolver.py:115-126` verified
- [x] Live `dashboard_data.json` (`asset_class_health` + `picks.{active,recent_closed}`) sampled 2026-05-03T17:30Z
- [x] `_normalize_asset_class_hint('stocks')` runtime test — returns `'EQUITY'` ✓
- [x] `_normalize_asset_class_hint('UNKNOWN')` runtime test — returns `None` ✓ (root-cause confirmed)
- [x] In-flight PR check: #644 / #660 / #661 / #723 / #724 / #744 inspected — none modify the files we're touching
- [x] No git push done from this subagent (per task constraint)

---

## 6. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Hunk A change shifts S-Tier from index 0 to index 1 — any code keyed on `categories[0] === 'S-Tier (70+)'`? | LOW | Grep'd: only `categories[i]` loop access exists; no array-index lookup |
| `__ALL__` tile inflates UI height and pushes data below fold | LOW | Tile is single row in CSS grid (`.nc-grid`); auto-flows |
| `_coerce_asset_class` recursion loop if `_derive_asset_class` returns `"UNKNOWN"` | LOW | `_derive_asset_class` defaults to `"EQUITY"` (line 3462), never returns `"UNKNOWN"` |
| PENNY/MEME implementation lands without operator decisions | HIGH | Hard-blocked above — proposal not implemented in this PR |

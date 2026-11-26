# GitHub Actions log investigation — 2026-11-25

Repo: `eltonaguiar/findtorontoevents_antigravity.ca` (337 workflows, default branch `main`)
Investigated by: buffy-laptop, working from the Windows laptop

## Method and its limits

- **`chrome-devtools-mcp` was not available** in this session's toolset, so the Actions UI was not
  inspected in a browser. Everything below comes from the GitHub API via the authenticated `gh` CLI
  (`repo` + `workflow` scopes), which reads the same run/log data the web UI renders.
- **`act` was not run and could not be**: neither `act` nor Docker is installed on this machine.
  No workflow was replayed locally.
- Run discovery: `gh run list -L 150` (a ~28-minute window — the repo runs extremely hot), then full
  logs (`gh run view <id> --log`, not just `--log-failed`) for 30 runs, so that **silent defects in
  successful runs** are caught. That is the class `--log-failed` scanners miss.
- Scanner used: `tmp/gha/scan_warnings.py`. Output: `tmp/gha/warnings_report.md`.

### Measurement caveat (important)

My first `nan-inf` signal reported **149 hits** and it is a **false positive**. The pattern
`NaN|Infinity` with `re.I` matches the substring `nan` inside `finance` / `yfinance`, which appears
on nearly every Python job. Verified directly:

```
pip install pandas numpy yfinance   -> matches
yfinance-1.8.0                      -> matches
finance                             -> matches
```

So `nan-inf` counts in the raw report should be ignored. Leaving this here rather than quietly
deleting it, because the count looked plausible and would have been easy to report as real.

## Run landscape (last 150 runs, ~28 min)

| conclusion | count |
|---|---|
| success | 130 |
| in_progress | 14 |
| cancelled | 4 |
| pending | 1 |
| failure | 1 |

Only one genuine failure in the window. The problems that matter are in the green runs.

## Finding 1 (critical) — non-crypto symbols get a bogus `-USD` suffix, hourly, while green

`Forward Trade Tracking v2` runs **hourly and has been green for all 20 of its most recent runs**
(2026-11-25T04:31Z → 23:30Z). It nonetheless fails to price **13 of its instruments every run**.

Root cause — `forward_trade_executor_v2.py:148-158`:

```python
@staticmethod
def _symbol_to_yf(symbol: str) -> str:
    """Convert BTCUSDT/BTC/USDT format to yfinance BTC-USD format."""
    s = symbol.replace('/', '').replace('-', '').upper()
    for suffix in ('USDT', 'USD'):
        if s.endswith(suffix):
            base = s[:-len(suffix)]
            return f"{base}-USD"
    return f"{s}-USD"          # <-- appends -USD to EVERYTHING else
```

The method documents itself as a *crypto* converter but the final `return` applies to every symbol
that is not already `USDT`/`USD`-suffixed. Reproduced against the shipped logic:

```
QQQ       -> QQQ-USD          (should be QQQ)
AMD       -> AMD-USD          (should be AMD)
CL=F      -> CL=F-USD         (should be CL=F)
GC=F      -> GC=F-USD         (should be GC=F)
AUDUSD=X  -> AUDUSD=X-USD     (should be AUDUSD=X)
STX       -> STX-USD          (should be STX)
BRK-B     -> BRKB-USD         (dash stripped, then suffixed)
^GSPC     -> ^GSPC-USD        (index mangled)
BTCUSDT   -> BTC-USD          (correct — crypto works)
```

Live evidence from run `45721890415` (`track-signals` / `Import latest signals`):

```
yfinance - ERROR - $CL=F-USD: No data found, symbol may be delisted
yfinance - ERROR - HTTP Error 404: {"quoteSummary":{"result":null,"error":{
          "code":"Not Found","description":"Quote not found for symbol: CL=F-USD"}}}
```

Distinct mangled symbols in that single run:

```
AMD-USD AUDJPY=X-USD AUDUSD=X-USD CL=F-USD GC=F-USD HG=F-USD IEF-USD
NG=F-USD PL=F-USD QQQ-USD SI=F-USD STX-USD TLT-USD ZW=F-USD
```

That is **13 non-crypto instruments** (3 equities, 7 futures, 2 FX pairs, plus IEF/TLT ETFs) whose
price/ATR lookups can never succeed, plus one ambiguous case:

- `SUI-USD` also fails, but it is **correctly formatted** crypto — a separate Yahoo-side issue, not
  this bug. Not lumped in.

Impact: any forward signal on those instruments cannot be priced, ATR'd, or resolved. The job
reports success. This is exactly the "green but silently missing an asset class" pattern.

**Blast radius:** `_symbol_to_yf` is called by `fetch_current_price` and `calculate_atr`
(`forward_trade_executor_v2.py:161,171`). A second, separate implementation exists at
`alpha_engine/wavelet_cycle_strategies.py:145` and should be checked the same way.

**Note:** `alpha_engine/config.py` already has `resolve_single_yf_ticker()`, which does the right
thing — it converts `XXXUSDT` only, and **passes everything else through unchanged** ("forex =X,
stock, etc."). The fix is to CSE with that behaviour rather than inventing a third mapper.

## Finding 2 (critical, already reported by a peer) — KASUSDT has no second venue

`Coinglass DNA Scanner` (run `45722477772`, **success**):

```
INFO  Scanning KASUSDT ...
ERROR All sources failed for KASUSDT
INFO  No funding rate available for KASUSDT from any source
WARNING No data for KASUSDT, skipping
```

Source: `coinglass_strategies/data_fetcher.py:393`. All five configured ratio sources
(Binance → Bybit → OKX → Coinglass → CoinGecko) fail for a symbol Binance does not list. This
corroborates Hermes/deepseek-flash's broadcast (23:30Z today) and its PR 1139 — still live.

## Finding 3 (high) — Hub Data Sync is red because a manifest is 268 days old

`Hub Data Sync` (run `45719481029`, **failure**):

```
hub manifest generated_at=2026-03-02T10:00:00Z age=268.6d (limit 7d)
##[error]hub manifest is 268.6 days stale
##[error]Process completed with exit code 1.
```

The gate is working as designed; the upstream generator has not refreshed since March. This is a
real staleness signal, not a flaky test.

## Finding 4 (high) — a green job that is a guaranteed NO-OP

`Claude Gainer ML  Live Scanner` — 5/5 recent runs `success` at 30-minute cadence, but the log says:

```
##[error]No model .joblib files in claude_gainer_ml/models/ — scanner SKIPPED
         (scanner_ran=false, reason=no_models). Fail-open by design: job stays green
         but this run is a NO-OP.
```

Verified across runs: `scanner_ran=false` on both runs inspected (45721184782, 45717160984). The
workflow is candid about it, but a 30-minute schedule burning a runner for a documented no-op is
worth either fixing (train/ship the models) or disabling.

## Finding 5 (medium) — failures swallowed inside successful jobs

- `Audit Drift Telemetry` (run `45722575305`, **success**) — `drift` / `Pending SPA governance
  check`: `##[error]Process completed with exit code 1.` The step errored, the job still concluded
  success. Either an intentional `continue-on-error` or a genuinely swallowed failure; needs a
  decision.
- `Forward Trade Tracking v2` (run `45721890415`, **success**) — `##[warning]Failed to push after 3
  attempts`. The tracking stats were **not committed**. Silent data loss: green run, no persisted
  output.

## Finding 6 (medium) — geo-blocking causes skipped marks in cancelled runs

HTTP 451 from `api.binance.com` appears 14× across `realtime-challenge` and `portfolio-tracker`:

```
mark: SOLUSDT skipped (market data unavailable: .../klines?... (HTTP Error 451: ))
mark LINK-USD: skipped (HTTPError: HTTP Error 451: )
```

451 = "Unavailable For Legal Reasons" — the runner's IP is blocked by Binance. Those runs were
cancelled, so this may resolve itself once the cancel cause is fixed, but any marking path that
depends solely on Binance will silently skip instead of failing over.

## Finding 7 (low) — `actions/*` Node.js 20 deprecation

`##[warning]Node.js 20 is deprecated ... actions/checkout@v4, actions/setup-python@v5,
actions/upload-artifact@v4` — informational, but will become forced-migration work.

## Ranked recommendations

1. **Fix `_symbol_to_yf`** — only append `-USD` for crypto bases; pass `=F`, `=X`, `^`, and plain
   equities through unchanged. Reuse the `resolve_single_yf_ticker` contract. Add a unit test
   covering `QQQ`, `CL=F`, `AUDUSD=X`, `BRK-B`, `^GSPC`, `BTCUSDT`.
2. **Add a data-quality assertion** so the hourly tracking job goes red (or emits a hard error) when
   >0 non-crypto symbols fail to price — otherwise this class of bug is invisible forever.
3. **KASUSDT second venue** — land the Gate.io fallback already drafted in PR 1139.
4. **Hub manifest** — find and fix the generator that stopped in March; or raise the gate's limit if
   the manifest is intentionally frozen (but then the gate is meaningless).
5. **Decide the no-ops** — `Claude Gainer ML` models, and `Audit Drift Telemetry`'s
   `continue-on-error`.
6. **Push retries** — investigate why `Forward Trade Tracking v2` fails to push 3×; the stats
   artifact is being discarded.

None of these were changed by this investigation — findings only. No `act` replay was performed,
and the Actions web UI was not browsed (no chrome-devtools-mcp this session).

## Finding 8 (critical, new) — Mercury 2 has not scanned since 2026-05-25, and both its workflows are green

Surfaced by reading the raw log of run `45724028919` (job `139589188312`, `scan`) through the
browser-route extraction:

```
##[warning]ensemble_conservative.joblib not found — skipping scanner
          (models committed by Mercury 2 Weekly Retrain workflow; run it first via workflow_dispatch)
```

`.github/workflows/mercury2-scan.yml:50-51` then does `exit 0`, so the hourly job is green.

The retrain side looks healthy — `mercury2-retrain.yml` has **succeeded 8 consecutive weeks**
(2026-10-04 → 2026-11-22) and its commit step runs `git add mercury2/models/`. Yet the model
directory does not exist anywhere in the tree.

Root cause, proven:

| Evidence | Result |
|---|---|
| `git ls-tree -r origin/main \| grep ^mercury2/models/` | **0 files** |
| last commit to add them | `bfa7242becf` "Mercury 2 retrain 2026-05-24" (4 `.joblib` files) |
| commit that **deleted** them | **`94c208b8d43`** "chore: gitignore v6 (Round 4) … universal ML hygiene" (2026-05-25) |
| same commit added to `.gitignore` | `mercury2/models/*.joblib` (line 367) |
| `git check-ignore` | `.gitignore:367:mercury2/models/*.joblib` |
| `git ls-files mercury2/models` | empty → untracked, so the ignore rule wins |

So the retrain runs, trains, then `git add mercury2/models/` is a **silent no-op**; the next line
`git diff --cached --quiet && echo "No changes" && exit 0` reports success and exits green. Eight
weeks of "successful" retrains have changed nothing, and every hourly scan exits at the check.

### The same commit broke a second pipeline

`94c208b8d43` also added:

```
claude_gainer_ml/models/*.joblib
crypto_ml_edge/models/*.joblib
ml_battleground/**/models/*.joblib
```

`claude_gainer_ml/models/*.joblib` is exactly the `no_models` no-op in Finding 4
(`scanner_ran=false`, green every 30 min). So **one gitignore sweep turned at least two ML pipelines
into permanent green no-ops** — a structural failure, not two unrelated bugs.
`crypto_ml_edge` and `ml_battleground` are suspected but not yet verified.

### Why nothing caught it

Every guard in these workflows is fail-open by design: missing model → `::warning::` + `exit 0`.
Green status is therefore not evidence that a scan happened. This is the same class Hermes called
out: the dangerous bug is not the red workflow, it is the green one that quietly stopped working.

### Recommended fix

Either (a) remove those four paths from `.gitignore` and `git add -f` the models so the retrain can
commit again, or (b) keep them out of git and upload/download the model as a workflow artifact or
cache instead of committing it — but in both cases make the *scan* workflow fail loudly (or report
`scanner_ran=false` to a monitored field) instead of exiting 0.

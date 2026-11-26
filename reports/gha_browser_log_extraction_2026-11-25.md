# Extracting GitHub Actions raw logs via the website (no GitHub API)

Date: 2026-11-25 · Machine: laptop `ELTON2026` · Chrome 158.0.8127.88

## Goal

Pull raw job logs for `eltonaguiar/findtorontoevents_antigravity.ca` **through the GitHub
website in a real browser**, without calling the REST API.

## Tooling reality

- `chrome-devtools-mcp` was **not** exposed as an MCP tool in this session. It was used the
  supported alternative way: the package ships a CLI (`chrome-devtools`) that talks to the same
  daemon, so `npm i -g chrome-devtools-mcp` + `chrome-devtools <tool>` gives full CDP control.
- Chrome's `chrome://inspect` → **Remote debugging** toggle (server on `127.0.0.1:9222`, pid bound
  to IPv4 only) does **not** serve the classic `/json` surface here:
  `/json/version`, `/json/list`, `/json/protocol`, `/devtools/*` all return **404**, and a WS upgrade
  to `/devtools/browser` returns **403**. So `--browserUrl http://127.0.0.1:9222` fails with
  *"Failed to fetch browser webSocket URL … HTTP Not Found"*.
- The working flag is **`--autoConnect`**, which is documented as requiring exactly that toggle:

  ```bash
  npm i -g chrome-devtools-mcp@latest
  chrome-devtools start --autoConnect
  chrome-devtools list_pages --output-format=json
  ```

  First attach succeeded and listed the user's live tabs, including an already-open run page.

## Authentication is mandatory (proven, not assumed)

Anonymous requests to every log surface return **404**:

| URL | anonymous status |
|---|---|
| `/commit/<sha>/checks/<job_id>/logs` (raw job log) | 404 |
| `/actions/runs/<run_id>/logs` (archive zip) | 404 |
| `/actions/runs/<run_id>/job/<job_id>/logs` (job archive) | 404 |

Also confirmed the client-rendered log viewer does **not** embed logs in the HTML: the job page
fetches 200 OK / 160 KB with **0** occurrences of real log text. So "just curl the page" does not
work — the browser's cookie session is the only way in.

## The three website routes

1. **Raw per-job log (best for text)** — `/commit/<sha>/checks/<job_id>/logs`
   GitHub 302s to a short-lived signed Azure Blob:
   `https://productionresultssaN.blob.core.windows.net/actions-results/<uuid>/workflow-job-run-<uuid>/logs/job/job-logs.txt?rsct=text/plain&se=…&sig=…`
   `contentType: text/plain`. The SAS signature pre-authorises the GET, so the resolved URL can be
   downloaded without cookies — but it expires in ~10–30 min, so fetch immediately.
2. **Log archive ZIP** — `/actions/runs/<run_id>/logs`
   One ZIP with **per-step** files plus `0_<job>.txt` (whole job). Example from the user's download
   (`logs_123708231982.zip`, 40 KB, 14 entries):
   `track-signals/5_Import latest signals.txt`, `track-signals/6_Check signal resolutions.txt`,
   `track-signals/9_Commit stats.txt`, and `0_track-signals.txt` at 90,481 chars.
   Best granularity, but the browser download lands in `~/Downloads` rather than being readable in-page.
3. **UI log viewer (DOM)** — worst option; virtualized, client-rendered, needs scrolling to materialise
   lines, and `.js-log-line` matched **0** nodes on the run page.

## Proof it works end-to-end

Attached with `--autoConnect`, opened run `45721890415`, discovered job `139582011591`
(`track-signals`) and sha `8c432188…` **from the DOM**, navigated to the raw-logs URL, read the
resolved blob URL from `location.href`, and downloaded it:

```
status=200 bytes=90821 type=text/plain
934 lines, 42 × "No data found, symbol may be delisted"
first line: 2026-11-25T23:30:34.2354097Z Current runner version: '2.338.2'
```

The **42** hits match exactly what the API-based scan reported for the same run — independent
corroboration that the browser path returns identical bytes, not a filtered view. Saved at
`tmp/gha/logs/45721890415__139582011591__track-signals.log`.

Discovery also verified on a second, unrelated run: `45724028919` → job `139589188312` (name `scan`),
sha `5864687fb5287ed4d91720584354b74ebf6cb0ac`.

## Tool

`tools/gha_fetch_logs_via_browser.py`

```bash
python tools/gha_fetch_logs_via_browser.py 45721890415 45724028919
python tools/gha_fetch_logs_via_browser.py --job 45721890415/139582011591
```

Flow: `new_page` run URL → poll DOM for job ids + commit sha → per job open a throwaway tab on the
raw-log URL → read `location.href` → download → `close_page`.

Windows detail: `chrome-devtools` is a `.cmd` shim that `CreateProcess` cannot launch, so the script
routes through `cmd /c`.

## Known failure mode (important)

Navigating a **shared, long-lived tab** to the signed blob URL can leave its load event pending
forever and **wedge the entire CDP attach** — after that, every command (`list_pages`, `status`
aside) times out with exit 124. Killing the daemon by pid and restarting `--autoConnect` did **not**
clear it; the wedge lives on the Chrome side.

Mitigations baked into the script: one throwaway tab per job, `close_page` afterwards, and a 60 s
per-call timeout that skips instead of hanging.

Recovery if it wedges: close the stuck `productionresultssa*` tab in Chrome (or restart Chrome) and
re-enable the Remote debugging toggle. This is what blocked the final verification run on
`45724028919` — the browser had to be recovered by the user.

## Rule of thumb

One or two jobs per session, then let the browser settle. For bulk pulls across many runs, the ZIP
archive route or the API-based scanner (`tmp/gha/scan_warnings.py`) is the pragmatic choice; the
browser route is the right tool when the API is off-limits or a single job needs re-reading.

## Measured SAS lifetime (2026-11-26T00:08Z)

A freshly minted link was handed over and then fetched 8 minutes late. Azure rejected it:

```
HTTP 403  AuthenticationFailed
Signature not valid in the specified time frame:
  Start [Wed, 25 Nov 2026 23:49:55 GMT] - Expiry [Thu, 26 Nov 2026 00:00:00 GMT]
  - Current [Thu, 26 Nov 2026 00:08:15 GMT]
```

So the signed window is **~10 minutes** (`st` → `se`), not 30. Consequences:

- Mint and download in the same breath; never queue links for later.
- An expired link returns **403 with an XML body**, not an empty file. The fetcher now detects
  `Signature not valid in the specified time frame` and refuses to write the XML error document as
  a `.log` (it previously would have).
- `se` in the query string is the authoritative expiry; `st` is the start of the validity window.

## Validation: browser output is byte-identical to the official ZIP

The user's "Download log archive" ZIP (`logs_123708231982.zip`) contains `0_track-signals.txt` for
the same job. Compared against what the browser route produced:

```
zip  0_track-signals.txt chars: 90480
browser-extracted      chars: 90480
normalised identical: True      (no diff at all)
```

So the browser path is not a lossy or filtered view — it returns exactly the archived bytes.

## Two bugs found in the fetcher itself (both fixed)

1. **cmd.exe mangles argv.** `chrome-devtools` on Windows is a `.cmd` shim, so calls had to go
   through `cmd.exe`, which rewrites the argument string. A multi-line JS payload was chopped and
   `--pageId` never arrived; the CLI answered
   *"Error: specify either a pageId or a serviceWorkerId"*, and discovery silently returned
   `jobs=0`. Single-line ad-hoc tests masked it.
   **Fix:** run the package's real entry point with node —
   `%APPDATA%/npm/node_modules/chrome-devtools-mcp/out/Default/gen/src/bin/chrome-devtools.js` —
   so argv survives byte-for-byte. Both runs then extracted cleanly.

2. **Expired SAS written as a log.** An expired signed URL returns `403` with an XML
   `AuthenticationFailed` body; the fetcher would have saved that as a `.log`.
   **Fix:** detect the expiry message and the XML preamble, report, and discard.

## No wedge with the per-job tab strategy

After recovery, extracting two runs back-to-back (one job each) worked with **no** timeout: each job
opened its own tab, read `location.href`, downloaded, and closed the tab.

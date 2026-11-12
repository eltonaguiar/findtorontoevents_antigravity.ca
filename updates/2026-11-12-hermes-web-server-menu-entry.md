# 2026-11-12 — Hermes web server: Linux-side menu entry + reachability finding

## What was broken / missing

1. **No Linux-side way to talk to Hermes.** The Hermes agent on the Windows host
   (192.168.2.32) was documented as exposing an OpenAI-compatible HTTP endpoint,
   but nothing on this box could probe or call it, and `tools/ai_menu.sh` had no
   entry for it.
2. **The advertised endpoint does not answer from Linux.** From this host
   (192.168.2.52, same `/24`, route present via `enP7s7`):

   ```
   $ exec 3<>/dev/tcp/192.168.2.32/8642   → connection refused
   $ curl -m 6 http://192.168.2.32:8642/v1/models
     curl: (7) Failed to connect to 192.168.2.32 port 8642 ... (0 ms)
   ```

   An instant `ECONNREFUSED` (0 ms) means the host answers ARP/ICMP but **nothing
   is listening on 8642** from off-box. The menu label added on the Windows side
   reads `HERMES - WEB SERVER (LET OTHERS TALK) 127.0.0.1:8642`, i.e. the gateway
   was started on **loopback**, which is unreachable from any other machine.
   Two things are needed before "let others talk" is true:
   - bind the API server to `0.0.0.0` (or `192.168.2.32`), not `127.0.0.1`;
   - allow inbound TCP 8642 in Windows Defender Firewall (private profile).

## What I changed

- **New:** `tools/hermes_web.sh` — dependency-free client (bash + curl + python3).
  - `status` / `models` — prints endpoint, and classifies reachability as
    `YES (200)`, `YES (401/403 — server up, key rejected)`,
    `NO (connection failed)`, or `UNKNOWN (http N)`. Never prints the key.
  - `ask "<prompt>"` — one-shot `POST /v1/chat/completions`, prints the reply text
    (or the API error) and exits non-zero on failure.
  - Key resolution: `$HERMES_API_KEY`, else `API_SERVER_KEY=` in `~/.hermes/.env`
    (override the file with `$HERMES_ENV_FILE`). Endpoint via `$HERMES_ENDPOINT`.
- **Changed:** `tools/ai_menu.sh` — one new `PROJECT_CMDS` entry:

  ```
  "hermes-web|tools/hermes_web.sh|bash|HERMES - WEB SERVER (LET OTHERS TALK) 192.168.2.32:8642"
  ```

  Purely additive (one line); it does not touch the peer's existing uncommitted
  `print_swarm_picker` block in the same file.

## Verification

```
$ bash -n tools/hermes_web.sh   → OK
$ bash -n tools/ai_menu.sh      → OK
$ tools/ai_menu.sh --list       → hermes-web listed as "available"
$ tools/hermes_web.sh status    → reachable: NO (connection failed — Windows host
                                  down, or 8642 not LAN-reachable)
```

The `NO` is the honest result: the script is correct, the remote bind is not.
`ask` is untested end-to-end **because there is no reachable endpoint yet**; it
will be exercised the moment the gateway is bound to `0.0.0.0:8642`.

## Not done / owner-only

- Rebinding the Windows gateway and adding the firewall rule (Windows host, not
  this box).
- Nothing was pushed. `tools/ai_menu.sh` already carries an unrelated uncommitted
  change from the other agent, so these two edits stay uncommitted rather than
  mixing authorship into one commit.

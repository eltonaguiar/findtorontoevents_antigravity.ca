---
name: consult-webchat
description: Ask browser-only AI chat sites (duck.ai, notegpt.io/ai-chat, notrack.ai/chat) for a second opinion by teaching api-anything their own request. Use when the user says "/consult-webchat", "ask duck.ai", "ask notegpt", "ask notrack", or wants a brainstorm from a chat site that has no API.
---
# consult-webchat
Get a brainstorm from an AI chat site that has no API, without driving a browser for every question.

## When to use
User names one of these chat UIs (`duck.ai`, `notegpt.io/ai-chat`, `notrack.ai/chat`) and wants
an outside take, or says `/consult-webchat`. For models with a real CLI, use `consult-grok`,
`consult-gemini`, `consult-codex`, `consult-kilo`, `consult-local`, `consult-multi` instead —
those need no browser and no learning.

## What this actually is
`api-anything` learns the request a site's own frontend makes, then replays it over plain HTTP.
That removes the browser from every *subsequent* call. The learning step needs Chromium and runs once
per site; state lives in `~/.api-anything`.

`tools/consult_webchat.py` is the wrapper: per-site trigger table, the learn/ask flow, and
answer extraction. It shells out to `npx -y api-anything@0.4.0`.

## Verified status (2026-11-18, api-anything 0.4.0, node v24.22.3, Chrome present)
**No site is learned yet, and the reason is structural — not a config error.**

| site | prompt rides in | answer arrives from | read path | write path |
|------|-----------------|---------------------|-----------|------------|
| duck.ai | `GET /?q=` (HTML shell) | `POST /duckchat/v1/chat`, token from `GET /duckchat/v1/auth/token` | refused | `--write` |
| notrack.ai | `GET /chat?q=` (HTML shell) | `POST /api/dispatch`, `text/event-stream` | **refused, measured** | `--write` |
| notegpt.io | not probed yet | not probed yet | unknown | unknown |

The measured refusal, verbatim:

```
{"ok":false,"site":"notrack","op":"chat","class":"refused",
 "error":"request 22 (POST https://notrack.ai/api/dispatch) is not a read: a POST that is
          not a GraphQL query may change something. learn_site learns reads only, and sent nothing",
 "next":"... a write is learned with the CLI, which intercepts it: api-anything add <site> <op>
         --trigger <url> --example k=v --write, run by the user"}
```

A chat answer is a POST by nature, and api-anything's read-learning refuses POSTs on purpose.
So these three sites are reachable only through its **write** path — which api-anything itself
gates behind an explicit `--write` run by a human.

## The commands
```
python3 tools/consult_webchat.py doctor                       # node/chrome/api-anything + what is learned
python3 tools/consult_webchat.py learn --site notrack --write  # learn the POST op; sends nothing
python3 tools/consult_webchat.py ask "prompt" --allow-writes   # this DOES post the prompt
python3 tools/consult_webchat.py sites
```

## Ask-first rule (do not skip)
`ask --allow-writes` sends the user's prompt to a third-party site. That is a message leaving this
machine, so get an explicit yes before running it — same rule as sending mail or posting.
`learn --write` is safe on its own: api-anything intercepts the request and aborts it, and reports
`applied` only if a later read finds the result.

## Gotchas that cost real time
| Symptom | Cause | Fix |
|---|---|---|
| `"--html argument is ambiguous"` | `--html`, `--embedded`, `--extract` take a **value** | `--html=<selector>`; don't pass them bare |
| `learn` exits **0** while printing `"ok":false` | the CLI reports failure in JSON, not in the exit code | check the `ok` field (the wrapper does) |
| `"no request in run 1 carries the example values"` | the answer isn't in any readable *response* for that run | inspect `alternatives` + `captures`, then relearn with `--from <captureId> --pick-request <n>` |
| `secret-tool is not installed`, sessions stored unsealed | no keychain on this box | `export API_ANYTHING_KEY=...` to seal, or accept plaintext 0600 |
| `npx` re-downloads every call | no global install | `npm i -g api-anything@0.4.0`, or keep the pin in `API_ANYTHING_PKG` |
| Learned op replays the *example* text | trigger/param wrong, but it "succeeded" | never trust `learn` alone; only mark `verified` after `ask` returns a real answer |

## Related
- `.claude/skills/consult-multi/SKILL.md` — 11 providers with real APIs, one CLI, no learning step.
- `.claude/skills/consult-local/SKILL.md` — zero-key local fleet, lowest latency.

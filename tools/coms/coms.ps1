# Windows COMS. Same protocol as Linux `COMS`.
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 learn
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 register -Agent claude
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 roster
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 heartbeat
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 send <topic> <message>
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 guard [files...]
#   powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 listen -Agent <role>
param(
  [Parameter(Position=0)][string]$Command = "learn",
  [string]$Agent = "",
  [string]$Todo = "",
  [string]$Done = "",
  [string]$Goal = "",
  [string]$Files = "",
  [string]$Commits = "",
  [string]$Prompt = "",
  [switch]$Retain,
  [switch]$Force,
  [string]$WorktreeName = "",
  [switch]$NoNotes,
  [string]$File = "",
  [Parameter(Position=1)][string]$Topic = "",
  [Parameter(Position=2)][string]$Message = "",
  [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest = @()
)
$Broker = if ($env:COMS_BROKER) { $env:COMS_BROKER } else { "192.168.2.52" }
$Port = if ($env:COMS_PORT) { [int]$env:COMS_PORT } else { 1883 }
$Reg = Join-Path $env:USERPROFILE ".coms\agents.jsonl"
# Windows PowerShell 5.1 defaults python stdout to the OEM/ANSI code page. A peer
# message containing a non-ASCII glyph (e.g. U+2212 minus) then crashes paho's
# print callback with UnicodeEncodeError and the check/listen output is lost.
# Force UTF-8 for every python child of this process.
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [Text.Encoding]::UTF8 } catch {}

function Slug([string]$s) {
  $t = $s.ToLower() -replace '[^a-z0-9_-]', '-'
  return $t.Trim('-')
}
function HostName { Slug $env:COMPUTERNAME }
function Worktree {
  # B2: never trust the current directory alone. Order: explicit -WorktreeName,
  # then the registry row for this agent on this host, then the git toplevel,
  # then the cwd. $script:WtSource is recorded so `check` can print it — a seat
  # derived from a home folder reads an inbox nobody writes to and still exits 0.
  if ($WorktreeName) { $script:WtSource = "flag"; return (Slug $WorktreeName) }
  $role = ""
  if ($Agent) { $role = Slug $Agent }
  if ($role -and (Test-Path $Reg)) {
    $cands = @()
    foreach ($line in (Get-Content $Reg)) {
      if (-not $line) { continue }
      try { $row = $line | ConvertFrom-Json } catch { continue }
      if ($row.agent -eq $role -and $row.host -eq (HostName) -and $row.worktree) { $cands += $row }
    }
    if ($cands.Count -ge 1) {
      $uniq = @($cands | ForEach-Object { $_.worktree } | Sort-Object -Unique)
      if ($uniq.Count -eq 1) { $script:WtSource = "registry"; return (Slug $uniq[0]) }
      $script:WtSource = "registry-newest"
      Write-Warning ("seat " + $role + " is registered under " + ($uniq -join ", ") + "; using the most recent. Pass -WorktreeName to override.")
      return (Slug $cands[-1].worktree)
    }
  }
  $top = ""
  try { $top = (git rev-parse --show-toplevel 2>$null) } catch {}
  if ($top) { $script:WtSource = "git"; return (Slug (Split-Path $top -Leaf)) }
  $script:WtSource = "cwd"
  return (Slug (Split-Path (Get-Location).Path -Leaf))
}
function Resolve-Topic([string]$t) {
  # B7: slug() rewrites dots, so a folder named ..._antigravity.ca becomes
  # ..._antigravity-ca. Resolve the host/worktree segments so "sent" matches
  # what a subscriber (which slugs) is actually listening on.
  if ($t -match '^inbox/([^/]+)/([^/]+)/(.+)$') {
    return "inbox/$(Slug $Matches[1])/$(Slug $Matches[2])/$($Matches[3])"
  }
  return $t
}
function Publish([string]$T, [string]$M, [switch]$Retain, [string]$Path) {
  $r = if ($Retain) { "retain=True" } else { "retain=False" }
  # A large payload cannot cross argv at all: the Win32 command line caps at
  # 32767 characters, which is why the 500 KB test could only ever SKIP here.
  # -Path publishes the file's bytes through the same paho transport.
  if ($Path) {
    python -c "import sys, pathlib, paho.mqtt.client as mqtt; b=pathlib.Path(sys.argv[4]).read_bytes(); c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2); c.connect(sys.argv[1], int(sys.argv[2]), 60); c.publish(sys.argv[3], b, qos=1, $r).wait_for_publish(30); c.disconnect()" $Broker $Port $T $Path
    return
  }
  # Windows PowerShell 5.1 mangles a string passed to a native exe as argv:
  # embedded double-quotes are stripped and a multi-line payload truncates at the
  # first quoted token. Pass the payload via a temp file so no message content
  # ever crosses the argv parser; the path is always present, empty = empty file.
  $payload = if ($null -ne $M) { $M } else { "" }
  $pf = [System.IO.Path]::GetTempFileName()
  [System.IO.File]::WriteAllText($pf, $payload, (New-Object System.Text.UTF8Encoding($false)))
  python -c "import sys, pathlib, paho.mqtt.client as mqtt; p=pathlib.Path(sys.argv[4]).read_text(encoding='utf-8'); c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2); c.connect(sys.argv[1], int(sys.argv[2]), 60); c.publish(sys.argv[3], p, qos=1, $r).wait_for_publish(10); c.disconnect()" $Broker $Port $T $pf
  Remove-Item -LiteralPath $pf -ErrorAction SilentlyContinue
}
function Test-Secret([string]$Text) {
  $pats = @(
    @{ p = "-----BEGIN [A-Z ]*PRIVATE KEY-----"; n = "private-key" },
    @{ p = "\bAKIA[0-9A-Z]{16}\b"; n = "aws-key" },
    @{ p = "\bsk-[A-Za-z0-9]{20,}"; n = "sk-token" },
    @{ p = "\bgh[pousr]_[A-Za-z0-9]{20,}"; n = "github-token" },
    @{ p = "\bxox[baprs]-[A-Za-z0-9-]{10,}"; n = "slack-token" },
    @{ p = "(?i)(?<![?&])(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*\S{8,}"; n = "assigned-secret" }
  )
  return @($pats | Where-Object { $Text -match $_.p } | ForEach-Object { $_.n })
}
function Refuse-Secret([string]$Text) {
  $hits = Test-Secret $Text
  if ($hits.Count -gt 0) {
    [Console]::Error.WriteLine("refusing secret-like content: " + ($hits -join ","))
    [Console]::Error.WriteLine("do not publish or commit this. Git and MQTT are both shared.")
    return $false
  }
  return $true
}

if ($Command -eq "register" -and $Rest.Count -gt 0) {
  $i = 0
  while ($i -lt $Rest.Count) {
    if ($Rest[$i] -match '^--?(agent|todo|done|goal|files|commits|prompt)$' -and ($i + 1) -lt $Rest.Count) {
      $v = $Rest[$i + 1]
      switch ($Matches[1]) {
        "agent" { $Agent = $v }
        "todo" { $Todo = $v }
        "done" { $Done = $v }
        "goal" { $Goal = $v }
        "files" { $Files = $v }
        "commits" { $Commits = $v }
        "prompt" { $Prompt = $v }
      }
      $i += 2
    } else { $i++ }
  }
}

switch ($Command) {
  "learn" {
@"
COMS - live wake bus. Git is the filing cabinet. MQTT is the intercom.
Broker: ${Broker}:${Port} anonymous. Repo: https://github.com/eltonaguiar/AGENT_FOLDERFRAMEWORK
Inbox: inbox/<host>/<worktree>/<agent>
This folder: inbox/$(HostName)/$(Worktree)/<agent>
Register here: powershell -File E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1 register -Agent <role>
Do not reinstall the broker. Do not put secrets on the bus.
"@
  }
  "register" {
    if (-not $Agent) { Write-Error "register -Agent <role> is required"; exit 2 }
    $hostName = HostName
    $wt = Worktree
    $role = Slug $Agent
    $inbox = "inbox/$hostName/$wt/$role"
    $repos = @()
    try { $repos = @(git remote -v 2>$null | ForEach-Object { ($_ -split '\s+')[1] } | Sort-Object -Unique) } catch {}
    $obj = [ordered]@{
      agent = $role
      host = $hostName
      os = "windows"
      worktree = $wt
      path = (Get-Location).Path
      inbox = $inbox
      swarmbus_id = "$hostName`__$wt`__$role"
      repos = $repos
      registered_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    # B2: only emit a key when its flag was supplied, so a short status update
    # does not blank goal/files/commits/prompt/todo/done.
    if ($Goal)    { $obj.goal    = $Goal }
    if ($Todo)    { $obj.todo    = $Todo }
    if ($Done)    { $obj.done    = $Done }
    if ($Files)   { $obj.files   = $Files }
    if ($Commits) { $obj.commits = $Commits }
    if ($Prompt)  { $obj.prompt  = $Prompt }
    $json = $obj | ConvertTo-Json -Compress
    if (-not (Refuse-Secret $json)) { exit 2 }
    # B6: the broker does not enforce unique seats. Warn loudly when this inbox
    # is already taken so two agents do not silently share one wake topic.
    if (Test-Path $Reg) {
      $existing = Get-Content $Reg | Where-Object { $_ -and ($_ -match ('"' + [regex]::Escape($inbox) + '"')) } | Select-Object -Last 1
      if ($existing) { Write-Warning "seat $inbox is already registered (duplicate seat); add a session suffix or run unregister" }
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Reg) | Out-Null
    # B4: upsert by swarmbus_id. Append-only grew this roster to 29 rows / 11
    # distinct seats (18 duplicates), so "who is alive" was unanswerable.
    $env:COMS_REG = $Reg
    $env:COMS_JSON = $json
    python -c @"
import json, os, pathlib
p = pathlib.Path(os.environ['COMS_REG'])
new = json.loads(os.environ['COMS_JSON'])
rows, out, found = [], [], False
if p.is_file():
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
for r in rows:
    if r.get('swarmbus_id') == new.get('swarmbus_id'):
        m = dict(r); m.update({k: v for k, v in new.items() if v}); out.append(m); found = True
    else:
        out.append(r)
if not found:
    out.append(new)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text('\n'.join(json.dumps(r, separators=(',', ':')) for r in out) + '\n', encoding='utf-8')
print('roster rows=' + str(len(out)))
"@
    Publish "registry/$hostName/$wt/$role" $json -Retain
    Write-Output "registered $inbox"
    Write-Output $json
  }
  "roster" {
    if (Test-Path $Reg) { Get-Content $Reg }
    python -c @"
import time, paho.mqtt.client as mqtt
seen=[]
def on_msg(c,u,m):
    print(m.topic, m.payload.decode())
c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_message=on_msg
c.connect('$Broker', $Port, 60)
c.subscribe('registry/#')
c.loop_start(); time.sleep(2); c.loop_stop(); c.disconnect()
"@
  }
  "heartbeat" {
    $line = "alive " + (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    Publish "status/$(HostName)" $line
    Write-Output $line
  }
  "send" {
    if (-not $Topic -or (-not $Message -and -not $File)) { Write-Error "usage: coms.ps1 send <topic> <message> [-Retain] [-File <path>]"; exit 2 }
    # Join extra positional words so `send <topic> hello world` keeps its spaces
    # (parity with Linux). Retain flags are extracted, not treated as message text.
    $retainOn = $Retain.IsPresent
    $words = @()
    foreach ($r in $Rest) {
      if ($r -eq '--retain' -or $r -eq '-retain' -or $r -eq '-Retain') { $retainOn = $true }
      else { $words += $r }
    }
    if ($words.Count -gt 0) { $Message = (@($Message) + $words) -join ' ' }
    if ($File) {
      if (-not (Test-Path -LiteralPath $File)) { Write-Error "no such file: $File"; exit 2 }
      if (-not (Refuse-Secret (Get-Content -Raw -LiteralPath $File))) { exit 2 }
    } elseif (-not (Refuse-Secret $Message)) { exit 2 }
    $resolved = Resolve-Topic $Topic
    if ($resolved -ne $Topic) { Write-Output "note: resolved topic $Topic -> $resolved (slug rewrites dots)" }
    # B3: the retained slot is last-writer-wins, so --retain into a seat you do
    # not own destroys the previous holder's payload with no history. This comment
    # used to say Linux refused and only Windows did not; measured 2026-11-20,
    # NEITHER client had a guard. Both fail closed now; -Force when you own it.
    if ($retainOn -and ($resolved -match '^inbox/([^/]+)/([^/]+)/(.+)$')) {
      $tAg = $Matches[3]; $tHost = $Matches[1]; $tWt = $Matches[2]
      if ($tAg -ne "all") {
        $ownAg = if ($Agent) { Slug $Agent } else { "" }
        $isOwn = (($tHost -eq (HostName)) -and ($tWt -eq (Worktree)) -and ($tAg -eq $ownAg))
        if (-not $isOwn -and -not $Force) {
          Write-Error "refusing to --retain into another seat's inbox ($resolved); the retained slot is last-writer-wins. Pass -Force if you own it."
          exit 2
        }
      }
    }
    if ($File) { Publish $resolved "" -Retain:$retainOn -Path $File }
    else { Publish $resolved $Message -Retain:$retainOn }
    if ($LASTEXITCODE -ne 0) {
      Write-Error "publish to $resolved failed (broker ${Broker}:${Port} unreachable?) - message NOT sent"
      exit 1
    }
    if ($retainOn) {
      Write-Output "sent $resolved (qos1, retained - survives until a listener attaches)"
    } else {
      Write-Output "sent $resolved (qos1, not retained - no delivery guarantee; verify with: coms.ps1 check -Agent <role>)"
    }
  }
  "guard" {
    $paths = @(@($Topic, $Message) + $Rest) | Where-Object { $_ }
    if ($paths.Count -eq 0) {
      $text = [Console]::In.ReadToEnd()
      if (-not (Refuse-Secret $text)) { exit 2 }
      Write-Output "clean"
      exit 0
    }
    $hit = $false
    foreach ($f in $paths) {
      if ((Test-Path -LiteralPath $f) -and -not (Refuse-Secret (Get-Content -Raw -LiteralPath $f))) {
        [Console]::Error.WriteLine("blocked $f"); $hit = $true
      }
    }
    if (-not $hit) { Write-Output "clean" } else { exit 2 }
  }
  "listen" {
    if (-not $Topic -and -not $Agent) { Write-Error "usage: coms.ps1 listen -Agent <role>   (or: coms.ps1 listen <topic>)"; exit 2 }
    $hn = HostName; $wt = Worktree
    $topics = if ($Topic) { @((Resolve-Topic $Topic)) } else { @(
        (Resolve-Topic "inbox/$hn/$wt/$(Slug $Agent)"),
        "inbox/$hn/$wt/all",
        "mentions/all"
      ) }
    Write-Output ("listening " + ($topics -join ", ") + "  (Ctrl-C to stop; reconnects on broker blips)")
    $subs = ($topics | ForEach-Object { "        c.subscribe('$_')" }) -join "`n"
    python -c @"
import time, paho.mqtt.client as mqtt
while True:
    try:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        c.on_message = lambda cl, u, msg: print(msg.topic, msg.payload.decode(), flush=True)
        c.connect('$Broker', $Port, 60)
$subs
        c.loop_forever()
    except Exception as e:
        print('listener dropped:', e, flush=True)
        time.sleep(5)
"@
  }
  "check" {
    if (-not $Agent -and -not $Topic) { Write-Error "usage: coms.ps1 check -Agent <role> [--wait N]"; exit 2 }
    $wait = 3
    $i = 0
    while ($i -lt $Rest.Count) {
      if ($Rest[$i] -eq '--wait') {
        if (($i + 1) -lt $Rest.Count -and $Rest[$i + 1] -match '^\d+$') { $wait = [int]$Rest[$i + 1]; $i += 2 }
        else { Write-Error "usage: coms.ps1 check -Agent <role> [--wait N]  (--wait must be a non-negative integer)"; exit 2 }
      } elseif ($Rest[$i] -match '^\d+$') {
        $wait = [int]$Rest[$i]; $i++
      } elseif ($Rest[$i] -eq '--no-notes') {
        $NoNotes = $true; $i++
      } else { $i++ }
    }
    # tolerate `check -Agent role 3` where the bare number binds to Topic
    if ($Agent -and $Topic -match '^\d+$') { $wait = [int]$Topic; $Topic = "" }
    $hn = HostName; $wt = Worktree
    $topics = if ($Topic) { @((Resolve-Topic $Topic)) } else { @(
        (Resolve-Topic "inbox/$hn/$wt/$(Slug $Agent)"),
        "inbox/$hn/$wt/all",
        "mentions/all"
      ) }
    Write-Output ("checking " + ($topics -join ", ") + " for ${wait}s [seat source: " + $script:WtSource + "]")
    $subs = ($topics | ForEach-Object { "c.subscribe('$_')" }) -join "`n"
    python -c @"
import time, paho.mqtt.client as mqtt
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_message = lambda cl, u, msg: print(msg.topic, msg.payload.decode(), flush=True)
c.connect('$Broker', $Port, 60)
$subs
c.loop_start(); time.sleep($wait); c.loop_stop(); c.disconnect()
"@
    Write-Output ("checked " + ($topics -join ", ") + " over ${wait}s (retained + in-flight; not a delivery guarantee)")

    # notes/* carry FULL DOCUMENTS on their own topics and are not any of the
    # three subscribed above, so they were invisible to every check -- an agent
    # could honestly report "no messages" while 42 notes (~135 KB) were live.
    # Print an INDEX (topic + size), not the payloads, so the inbox output stays
    # readable. Suppress with -NoNotes / --no-notes.
    if (-not $NoNotes) {
      $notesPy = @"
import time, paho.mqtt.client as mqtt
hits = {}
def on_message(cl, u, msg):
    hits[msg.topic] = len(msg.payload)
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_message = on_message
c.connect('$Broker', $Port, 60)
c.subscribe('notes/#')
c.loop_start(); time.sleep(3); c.loop_stop(); c.disconnect()
if not hits:
    print('--- no notes/* topics')
else:
    print(f'--- {len(hits)} note(s) on notes/# ({sum(hits.values())} B) - payloads NOT shown')
    print('      read one with: mosquitto_sub -h $Broker -t notes/<slug> -W 2')
    for t in sorted(hits):
        print(f'    {t:<66} {hits[t]:7d} B')
"@
      $notesFile = Join-Path $env:TEMP ("coms-notes-" + [guid]::NewGuid().ToString("N") + ".py")
      [System.IO.File]::WriteAllText($notesFile, $notesPy, (New-Object System.Text.UTF8Encoding($false)))
      python $notesFile
      Remove-Item -LiteralPath $notesFile -ErrorAction SilentlyContinue
    }
  }
  "topics" {
    # Full bus inventory. check covers YOUR inbox; this answers "what else?"
    $pat = if ($Topic) { $Topic } else { "#" }
    $wait = 6
    $i = 0
    while ($i -lt $Rest.Count) {
      if ($Rest[$i] -eq '--wait' -and ($i + 1) -lt $Rest.Count -and $Rest[$i + 1] -match '^\d+$') { $wait = [int]$Rest[$i + 1]; $i += 2 }
      else { $i++ }
    }
    Write-Output ("topics matching '$pat' on ${Broker}:${Port} over ${wait}s")
    python -c @"
import time, paho.mqtt.client as mqtt
hits = {}
def on_message(cl, u, msg):
    hits[msg.topic] = len(msg.payload)
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_message = on_message
c.connect('$Broker', $Port, 60)
c.subscribe('$pat')
c.loop_start(); time.sleep($wait); c.loop_stop(); c.disconnect()
if not hits:
    print('  (no topics matched)')
else:
    groups = {}
    for t, n in hits.items():
        p = t.split('/')[0]
        g = groups.setdefault(p, [0, 0])
        g[0] += 1; g[1] += n
    print(f'  {len(hits)} topic(s)')
    for p in sorted(groups):
        cnt, tot = groups[p]
        print(f'  {p:<14} {cnt:4d} topic(s) {tot:9d} B')
    print()
    for t in sorted(hits):
        size = (str(hits[t]) + ' B') if hits[t] else 'empty'
        print(f'  {t:<70} {size:>10}')
"@
  }
  "unregister" {
    if (-not $Agent) { Write-Error "unregister -Agent <role> is required"; exit 2 }
    $hostName = HostName; $wt = Worktree; $role = Slug $Agent
    Publish "registry/$hostName/$wt/$role" "" -Retain
    if (Test-Path $Reg) {
      $keep = Get-Content $Reg | Where-Object { $_ -and ($_ -notmatch ('"' + [regex]::Escape("inbox/$hostName/$wt/$role") + '"')) }
      Set-Content -Path $Reg -Value $keep
    }
    Write-Output "unregistered inbox/$hostName/$wt/$role"
  }
  "prompt" {
    Get-Content -Raw (Join-Path (Split-Path $PSCommandPath) "AGENT_REGISTER_PROMPT.md")
  }
  default { Write-Output "commands: learn, register -Agent <role> [-Todo .. -Done ..], roster, heartbeat, send <topic> <message>, guard [files], listen -Agent <role>, check -Agent <role> [-NoNotes], topics [pattern] [-Wait N], unregister -Agent <role>" }
}

# Redis Bus Quick Reference
## Essential Commands for Prediction System

---

## Setup
```bash
# Start Redis (if not running)
/c/Users/zerou/redis-bus/redis-server.exe --daemonize no --port 6379 &

# Health check
/c/Users/zerou/redis-bus/redis-cli.exe -p 6379 ping

# Set alias
alias rc='/c/Users/zerou/redis-bus/redis-cli.exe -p 6379'
```

---

## Daily Operations

### Announce Yourself
```bash
rc HSET agent:<your_id>:status \
  summary "Working on scoring fix" \
  tool "claude-code" \
  last_seen "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rc EXPIRE agent:<your_id>:status 3600
```

### Check Inbox
```bash
rc LRANGE agent:<your_id>:inbox 0 -1
rc DEL agent:<your_id>:inbox
```

### Broadcast Message
```bash
rc LPUSH bus:broadcast:log \
  '{"from":"<your_id>","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","body":"Message here"}'
rc LTRIM bus:broadcast:log 0 99
```

---

## Prediction Messages

### New Pick
```bash
rc PUBLISH predictions:new '{"type":"prediction_new","symbol":"BTCUSDT","direction":"LONG","score":87}'
```

### Pick Outcome
```bash
rc PUBLISH predictions:update '{"type":"prediction_outcome","pick_id":"pick_001","result":"win","pnl_pct":10}'
```

### Conflict Alert
```bash
rc PUBLISH alerts:conflict '{"symbol":"BTCUSDT","long_count":3,"short_count":2}'
```

---

## Task Management

### Submit Task
```bash
rc LPUSH bus:tasks:pending '{"task":"recalc_scores","symbol":"BTCUSDT","priority":"high"}'
```

### Claim Task (blocking 5s)
```bash
rc BRPOP bus:tasks:pending 5
```

---

## File Locks (CRITICAL)

### Acquire Lock
```bash
rc SET lock:file:audit_dashboard/template.html <your_id> NX EX 300
```

### Check Lock
```bash
rc GET lock:file:audit_dashboard/template.html
```

### Release Lock
```bash
rc DEL lock:file:audit_dashboard/template.html
```

---

## Common Queries

### Who's Online?
```bash
rc KEYS 'agent:*:status'
```

### Recent Broadcasts
```bash
rc LRANGE bus:broadcast:log 0 9
```

### Pending Tasks
```bash
rc LLEN bus:tasks:pending
```

---

## Python Helper
```bash
PY="C:/Users/zerou/AppData/Local/Programs/Python/Python314/python.exe"
BUS="C:/Users/zerou/redis-bus/agent_bus.py"

$PY $BUS ping
$PY $BUS announce <your_id> "working on X"
$PY $BUS peers
$PY $BUS inbox <your_id>
$PY $BUS send <from> <to> "message"
$PY $BUS broadcast <your_id> "announcement"
```

---

## Emergency
```bash
# Force release stuck lock
rc DEL lock:file:audit_dashboard/template.html

# Clear your inbox
rc DEL agent:<your_id>:inbox

# Nuclear option (coordinate first!)
rc FLUSHDB
```

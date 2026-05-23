#!/usr/bin/env python3
"""
Swarm Bridge — Cross-PC Agent Communication via Git-Shared State + Redis Bus.

Same-PC: Redis bus (localhost:6379) for realtime messages.
Cross-PC: Git-synced JSON state file (agent_swarm_state.json) for persistence + multi-machine visibility.
Holographic Memory: Structured key-value store surviving restarts.

Zero external deps beyond stdlib. Redis is optional — falls back to file-only mode.

Usage:
  python tools/swarm_bridge.py announce <agent_id> <summary> [--tool <tool>]
  python tools/swarm_bridge.py peers [--all]
  python tools/swarm_bridge.py send <from> <to> <message>
  python tools/swarm_bridge.py broadcast <from> <message>
  python tools/swarm_bridge.py inbox <agent_id> [--clear]
  python tools/swarm_bridge.py memory set <key> <value>
  python tools/swarm_bridge.py memory get <key>
  python tools/swarm_bridge.py memory list
  python tools/swarm_bridge.py task add <description> [--priority normal]
  python tools/swarm_bridge.py task claim <task_index> <agent_id>
  python tools/swarm_bridge.py task list [--open]
  python tools/swarm_bridge.py sync
  python tools/swarm_bridge.py status
"""

import argparse
import json
import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "agent_swarm_state.json"
MAX_BROADCASTS = 100
MAX_INBOX_PER_AGENT = 50
MAX_MEMORY_KEYS = 200
try:
    import redis as _redis_mod
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ── State helpers ───────────────────────────────────────────────────

def _load_state() -> dict:
    """Load shared state from file, or return empty skeleton."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "_meta": {"version": 1, "last_updated": None, "updated_by": None},
        "agents": {},
        "memory": {},
        "broadcasts": [],
        "inboxes": {},
        "tasks": [],
    }


def _acquire_lock(lock_path: Path, timeout: float = 5.0) -> bool:
    """Acquire a simple file lock with retry. Returns True if locked."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{_now()} {os.environ.get('SWARM_AGENT_ID', 'unknown')}\n".encode())
            os.close(fd)
            return True
        except (OSError, FileExistsError):
            try:
                if lock_path.exists():
                    age = time.time() - lock_path.stat().st_mtime
                    if age > 30:
                        lock_path.unlink(missing_ok=True)
                        continue
            except Exception:
                pass
            time.sleep(0.05)
    return False


def _release_lock(lock_path: Path) -> None:
    """Release a file lock."""
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def _save_state(state: dict, agent_id: str) -> None:
    """Save shared state to file with metadata."""
    state["_meta"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["_meta"]["updated_by"] = agent_id
    # Prune old broadcasts
    if len(state.get("broadcasts", [])) > MAX_BROADCASTS:
        state["broadcasts"] = state["broadcasts"][:MAX_BROADCASTS]
    # Prune full inboxes
    for inbox_key in list(state.get("inboxes", {}).keys()):
        if len(state["inboxes"][inbox_key]) > MAX_INBOX_PER_AGENT:
            state["inboxes"][inbox_key] = state["inboxes"][inbox_key][:MAX_INBOX_PER_AGENT]
    # Prune memory
    if len(state.get("memory", {})) > MAX_MEMORY_KEYS:
        mem_keys = list(state["memory"].keys())
        for old_key in mem_keys[MAX_MEMORY_KEYS:]:
            del state["memory"][old_key]
    lock_path = STATE_FILE.with_suffix(".json.lock")
    if _acquire_lock(lock_path):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        finally:
            _release_lock(lock_path)
    else:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print("[warn] Could not acquire lock — wrote without locking", file=sys.stderr)


def _get_redis():
    """Connect to Redis if available, else None.
    Uses decode_responses=False to match existing tooling (redis_bus_tick.py).
    """
    if not REDIS_AVAILABLE:
        return None
    try:
        r = _redis_mod.Redis(host="localhost", port=6379, decode_responses=False)
        r.ping()
        return r
    except Exception:
        return None


def _txt(blob: str | bytes | None) -> str:
    """Decode bytes to string safely, matching redis_bus_tick.py pattern."""
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    return blob.decode("utf-8", errors="replace")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hostname() -> str:
    return socket.gethostname()


# ── Commands ────────────────────────────────────────────────────────

def cmd_announce(agent_id: str, summary: str, tool: str = "") -> None:
    """Register agent presence on both file and Redis."""
    state = _load_state()
    state["agents"][agent_id] = {
        "status": "online",
        "last_seen": _now(),
        "summary": summary,
        "tool": tool,
        "pc": _hostname(),
        "cwd": str(REPO_ROOT),
    }
    _save_state(state, agent_id)

    r = _get_redis()
    if r:
        r.hset(f"agent:{agent_id}:status", mapping={
            "summary": summary,
            "cwd": str(REPO_ROOT),
            "last_seen": _now(),
            "tool": tool,
            "pc": _hostname(),
        })
        r.expire(f"agent:{agent_id}:status", 3600)

    print(f"[announced] {agent_id} ({tool or 'unknown'}): {summary[:120]}")


def cmd_peers(show_all: bool = False) -> None:
    """List agents from file (cross-PC) and optionally Redis (same-PC)."""
    state = _load_state()
    agents = state.get("agents", {})

    if not agents:
        print("No agents registered.")
        return

    print(f"{'AGENT':<25} {'PC':<20} {'TOOL':<12} {'LAST SEEN':<22} SUMMARY")
    print("-" * 120)
    for aid, info in sorted(agents.items()):
        status_mark = "*" if info.get("status") == "online" else "-"
        pc = info.get("pc", "?")
        tool = info.get("tool", "?")
        ts = info.get("last_seen", "?")[:19]
        summary = info.get("summary", "")[:60]
        print(f"{status_mark} {aid:<23} {pc:<20} {tool:<12} {ts:<22} {summary}")

    # Also show Redis-only agents (not yet in file)
    r = _get_redis()
    if r and show_all:
        for k in sorted(r.keys("agent:*:status")):
            aid = _txt(k).removeprefix("agent:").removesuffix(":status")
            if aid not in agents:
                print(f"  {aid:<23} (Redis-only, not in file)")


def cmd_send(from_id: str, to_id: str, message: str) -> None:
    """Send a direct message — file + Redis."""
    state = _load_state()
    msg = {"from": from_id, "ts": _now(), "body": message, "read": False}
    state.setdefault("inboxes", {}).setdefault(to_id, []).insert(0, msg)
    _save_state(state, from_id)

    r = _get_redis()
    if r:
        r.lpush(f"agent:{to_id}:inbox", json.dumps(msg))

    print(f"[DM] {from_id} -> {to_id}: {message[:120]}")


def cmd_broadcast(from_id: str, message: str) -> None:
    """Broadcast to all agents — file + Redis."""
    state = _load_state()
    msg = {"from": from_id, "ts": _now(), "body": message}
    state.setdefault("broadcasts", []).insert(0, msg)
    _save_state(state, from_id)

    r = _get_redis()
    if r:
        r.lpush("bus:broadcast:log", json.dumps(msg))
        r.ltrim("bus:broadcast:log", 0, 99)

    print(f"[broadcast] {from_id}: {message[:120]}")


def cmd_inbox(agent_id: str, clear: bool = False) -> None:
    """Read (and optionally clear) inbox — file + Redis."""
    state = _load_state()
    file_msgs = state.get("inboxes", {}).get(agent_id, [])

    # Also check Redis inbox
    r = _get_redis()
    redis_msgs = []
    if r:
        raw = r.lrange(f"agent:{agent_id}:inbox", 0, -1)
        for m in raw:
            try:
                decoded = _txt(m)
                redis_msgs.append(json.loads(decoded))
            except (json.JSONDecodeError, UnicodeDecodeError):
                redis_msgs.append({"raw": _txt(m)})

    # Deduplicate: file + Redis may have same messages; use (from, ts) as key
    seen = set()
    all_msgs = []
    for msg in file_msgs + redis_msgs:
        dedup_key = (msg.get("from", ""), msg.get("ts", ""))
        if dedup_key not in seen:
            seen.add(dedup_key)
            all_msgs.append(msg)
    if not all_msgs:
        print(f"[inbox] {agent_id}: empty")
        return

    print(f"[inbox] {agent_id}: {len(all_msgs)} message(s)")
    for i, msg in enumerate(all_msgs):
        from_id = msg.get("from", "?")
        ts = msg.get("ts", "?")[:19]
        body = msg.get("body", msg.get("raw", ""))[:200]
        read = "[read]" if msg.get("read") else "[NEW]"
        print(f"  {read} [{i}] {from_id} @ {ts}: {body}")

    if clear:
        state.setdefault("inboxes", {})[agent_id] = []
        _save_state(state, agent_id)
        if r:
            r.delete(f"agent:{agent_id}:inbox")
        print("  [cleared]")


def cmd_memory_set(key: str, value: str) -> None:
    """Set a key in holographic shared memory — writes to BOTH the state file and holographic memory."""
    agent_id = os.environ.get("SWARM_AGENT_ID", "unknown")
    
    # 1. Write to swarm state file (backwards compat + quick access)
    state = _load_state()
    state.setdefault("memory", {})[key] = {
        "value": value,
        "set_by": agent_id,
        "set_at": _now(),
        "pc": _hostname(),
    }
    _save_state(state, agent_id)

    # 2. Write to holographic memory as a fact (rich structured storage)
    try:
        import subprocess
        subprocess.run([
            sys.executable, str(REPO_ROOT / "tools" / "holographic_memory.py"),
            "fact", "set", key, value,
            "--confidence", "medium",
        ], capture_output=True, timeout=10)
    except Exception:
        pass  # holographic memory optional

    # 3. Write to Redis
    r = _get_redis()
    if r:
        r.hset("agent:shared:memory", key, value)

    print(f"[memory] set '{key}' = '{value[:120]}'")


def cmd_memory_get(key: str) -> None:
    """Get a key from holographic shared memory — checks holographic memory first, then state file, then Redis."""
    # 1. Try holographic memory first (richest data)
    mem_file = REPO_ROOT / "agent_shared_memory.json"
    if mem_file.exists():
        try:
            with open(mem_file, "r", encoding="utf-8") as f:
                holo = json.load(f)
            for fact in holo.get("facts", []):
                if fact.get("key") == key:
                    val = fact.get("value", "")
                    conf = fact.get("confidence", "?")
                    src = fact.get("source", "?")
                    at = fact.get("discovered_at", "?")[:19]
                    tags = fact.get("tags", [])
                    verified = fact.get("verified_by", [])
                    print(f"[memory] {key} = {val}")
                    print(f"         confidence: {conf} | source: {src} @ {at} | tags: {', '.join(tags)}")
                    if verified:
                        print(f"         verified by: {', '.join(verified)}")
                    return
        except Exception:
            pass

    # 2. Try swarm state file
    state = _load_state()
    entry = state.get("memory", {}).get(key)
    if entry:
        if isinstance(entry, dict):
            val = entry.get("value", "")
            by = entry.get("set_by", "?")
            at = entry.get("set_at", "?")[:19]
            print(f"[memory] {key} = {val}")
            print(f"         set by {by} @ {at}")
        else:
            print(f"[memory] {key} = {entry}")
        return

    # 3. Try Redis fallback
    r = _get_redis()
    if r:
        val = r.hget("agent:shared:memory", key)
        if val:
            print(f"[memory] {key} = {_txt(val)} (Redis)")
            return
    print(f"[memory] '{key}' not found")


def cmd_memory_list() -> None:
    """List all holographic memory keys — from holographic file, state file, and Redis."""
    sources = []

    # Holographic memory facts
    mem_file = REPO_ROOT / "agent_shared_memory.json"
    if mem_file.exists():
        try:
            with open(mem_file, "r", encoding="utf-8") as f:
                holo = json.load(f)
            for fact in holo.get("facts", []):
                sources.append((fact.get("key", "?"), fact.get("value", ""), f"holo:{fact.get('confidence', '?')}"))
        except Exception:
            pass

    # State file memory
    state = _load_state()
    for key, entry in state.get("memory", {}).items():
        val = entry.get("value", entry) if isinstance(entry, dict) else entry
        # Avoid duplicates from holo memory
        if not any(s[0] == key for s in sources):
            sources.append((key, val, "state"))

    # Redis memory
    r = _get_redis()
    if r:
        for k in r.hkeys("agent:shared:memory"):
            key = _txt(k)
            if not any(s[0] == key for s in sources):
                sources.append((key, _txt(r.hget("agent:shared:memory", k)), "redis"))

    if not sources:
        print("[memory] empty across all layers")
        return
    print(f"[memory] {len(sources)} key(s) across holo/state/redis:")
    for key, val, src in sorted(sources):
        print(f"  [{src}] {key}: {str(val)[:80]}")


def cmd_task_add(description: str, priority: str = "normal") -> None:
    """Add a task to the shared task queue."""
    agent_id = os.environ.get("SWARM_AGENT_ID", "unknown")
    state = _load_state()
    task = {
        "description": description,
        "created_by": agent_id,
        "priority": priority,
        "created_at": _now(),
        "claimed_by": None,
        "done": False,
    }
    state.setdefault("tasks", []).append(task)
    _save_state(state, agent_id)
    idx = len(state["tasks"]) - 1
    print(f"[task] #{idx} added [{priority}]: {description[:120]}")


def cmd_task_claim(task_index: int, agent_id: str) -> None:
    """Claim a task from the shared queue."""
    state = _load_state()
    tasks = state.get("tasks", [])
    if task_index < 0 or task_index >= len(tasks):
        print(f"[task] #{task_index} not found")
        return
    task = tasks[task_index]
    if task.get("claimed_by"):
        print(f"[task] #{task_index} already claimed by {task['claimed_by']}")
        return
    if task.get("done"):
        print(f"[task] #{task_index} already done")
        return
    task["claimed_by"] = agent_id
    task["claimed_at"] = _now()
    _save_state(state, agent_id)
    print(f"[task] #{task_index} claimed by {agent_id}: {task['description'][:120]}")


def cmd_task_list(open_only: bool = False) -> None:
    """List shared tasks."""
    state = _load_state()
    tasks = state.get("tasks", [])
    if not tasks:
        print("[task] no tasks")
        return

    shown = 0
    print(f"{'#':<5} {'PRI':<7} {'STATUS':<12} {'CREATED BY':<20} DESCRIPTION")
    print("-" * 100)
    for i, t in enumerate(tasks):
        if open_only and t.get("done"):
            continue
        status = "DONE" if t.get("done") else ("CLAIMED" if t.get("claimed_by") else "OPEN")
        pri = t.get("priority", "normal")
        by = t.get("created_by", "?")
        desc = t.get("description", "")[:60]
        print(f"{i:<5} {pri:<7} {status:<12} {by:<20} {desc}")
        shown += 1
    if shown == 0:
        print("[task] no open tasks")


def cmd_sync() -> None:
    """Bidirectional sync between Redis and file state."""
    r = _get_redis()
    if not r:
        print("[sync] Redis not available — file-only mode")
        return

    state = _load_state()
    synced = 0

    # File → Redis: sync agent statuses
    for aid, info in state.get("agents", {}).items():
        r.hset(f"agent:{aid}:status", mapping={
            "summary": info.get("summary", ""),
            "cwd": info.get("cwd", ""),
            "last_seen": info.get("last_seen", ""),
            "tool": info.get("tool", ""),
            "pc": info.get("pc", ""),
        })
        r.expire(f"agent:{aid}:status", 3600)
        synced += 1

    # File → Redis: sync memory
    for key, entry in state.get("memory", {}).items():
        val = entry.get("value", entry) if isinstance(entry, dict) else entry
        r.hset("agent:shared:memory", key, val)
        synced += 1

    # Redis → File: pull Redis-only agents
    for k in sorted(r.keys("agent:*:status")):
        aid = _txt(k).removeprefix("agent:").removesuffix(":status")
        if aid not in state.get("agents", {}):
            raw = r.hgetall(k)
            row = {_txt(a): _txt(b) for a, b in raw.items()}
            state["agents"][aid] = {
                "status": "online",
                "last_seen": row.get("last_seen", row.get("summary", "")),
                "summary": row.get("summary", ""),
                "tool": row.get("tool", "?"),
                "pc": row.get("pc", "?"),
                "cwd": row.get("cwd", "?"),
            }
            synced += 1

    # File → Redis: sync broadcasts
    for msg in state.get("broadcasts", [])[:10]:
        r.lpush("bus:broadcast:log", json.dumps(msg))
    r.ltrim("bus:broadcast:log", 0, 99)

    _save_state(state, "sync")
    print(f"[sync] {synced} items synced between file <-> Redis")


def cmd_status() -> None:
    """Show full swarm status."""
    state = _load_state()
    agents = state.get("agents", {})
    online = sum(1 for a in agents.values() if a.get("status") == "online")
    pcs = set(a.get("pc", "?") for a in agents.values())

    print("=== SWARM STATUS ===")
    print(f"  Agents: {len(agents)} ({online} online) across {len(pcs)} PC(s)")
    print(f"  Memory keys: {len(state.get('memory', {}))}")
    print(f"  Broadcasts: {len(state.get('broadcasts', []))}")
    print(f"  Open tasks: {sum(1 for t in state.get('tasks', []) if not t.get('done'))}")

    r = _get_redis()
    print(f"  Redis bus: {'connected' if r else 'offline (file-only mode)'}")
    print(f"  State file: {STATE_FILE}")
    print(f"  Last updated: {state['_meta'].get('last_updated', 'never')}")

    if agents:
        print("\n=== AGENTS ===")
        for aid, info in sorted(agents.items()):
            mark = "*" if info.get("status") == "online" else "-"
            pc = info.get("pc", "?")
            tool = info.get("tool", "?")
            summary = info.get("summary", "")[:80]
            print(f"  {mark} {aid} ({tool}) @ {pc}")
            print(f"    {summary}")


# ── CLI ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Swarm Bridge — Cross-PC agent communication via git-shared state + Redis bus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/swarm_bridge.py announce buffy "Auditing cross-agent comms" --tool codebuff
  python tools/swarm_bridge.py peers
  python tools/swarm_bridge.py send buffy claude "Hey, are you editing template.html?"
  python tools/swarm_bridge.py broadcast buffy "Pushing to main in 2 min"
  python tools/swarm_bridge.py inbox buffy --clear
  python tools/swarm_bridge.py memory set plan "Phase 1: cross-PC bridge"
  python tools/swarm_bridge.py memory get plan
  python tools/swarm_bridge.py task add "Fix Redis bus" --priority high
  python tools/swarm_bridge.py task list --open
  python tools/swarm_bridge.py sync
  python tools/swarm_bridge.py status
        """,
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # announce
    p = sub.add_parser("announce", help="Register agent presence")
    p.add_argument("agent_id")
    p.add_argument("summary")
    p.add_argument("--tool", default="")

    # peers
    p = sub.add_parser("peers", help="List all agents")
    p.add_argument("--all", action="store_true", help="Show Redis-only agents too")

    # send
    p = sub.add_parser("send", help="Send DM to another agent")
    p.add_argument("from_id")
    p.add_argument("to_id")
    p.add_argument("message")

    # broadcast
    p = sub.add_parser("broadcast", help="Broadcast to all agents")
    p.add_argument("from_id")
    p.add_argument("message")

    # inbox
    p = sub.add_parser("inbox", help="Read your inbox")
    p.add_argument("agent_id")
    p.add_argument("--clear", action="store_true", help="Clear after reading")

    # memory
    p = sub.add_parser("memory", help="Holographic memory operations")
    sub_mem = p.add_subparsers(dest="mem_cmd")
    m = sub_mem.add_parser("set")
    m.add_argument("key")
    m.add_argument("value")
    m = sub_mem.add_parser("get")
    m.add_argument("key")
    sub_mem.add_parser("list")

    # task
    p = sub.add_parser("task", help="Shared task queue")
    sub_task = p.add_subparsers(dest="task_cmd")
    t = sub_task.add_parser("add")
    t.add_argument("description")
    t.add_argument("--priority", default="normal", choices=["high", "normal", "low"])
    t = sub_task.add_parser("claim")
    t.add_argument("task_index", type=int)
    t.add_argument("agent_id")
    t = sub_task.add_parser("list")
    t.add_argument("--open", action="store_true")

    # sync
    sub.add_parser("sync", help="Bidirectional sync Redis ↔ file")

    # status
    sub.add_parser("status", help="Show full swarm status")

    args = parser.parse_args()

    if args.command == "announce":
        cmd_announce(args.agent_id, args.summary, args.tool)
    elif args.command == "peers":
        cmd_peers(args.all)
    elif args.command == "send":
        cmd_send(args.from_id, args.to_id, args.message)
    elif args.command == "broadcast":
        cmd_broadcast(args.from_id, args.message)
    elif args.command == "inbox":
        cmd_inbox(args.agent_id, args.clear)
    elif args.command == "memory":
        if args.mem_cmd == "set":
            cmd_memory_set(args.key, args.value)
        elif args.mem_cmd == "get":
            cmd_memory_get(args.key)
        elif args.mem_cmd == "list":
            cmd_memory_list()
        else:
            parser.parse_args(["memory", "--help"])
    elif args.command == "task":
        if args.task_cmd == "add":
            cmd_task_add(args.description, args.priority)
        elif args.task_cmd == "claim":
            cmd_task_claim(args.task_index, args.agent_id)
        elif args.task_cmd == "list":
            cmd_task_list(args.open)
        else:
            parser.parse_args(["task", "--help"])
    elif args.command == "sync":
        cmd_sync()
    elif args.command == "status":
        cmd_status()
    else:
        # Default: show status
        cmd_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())

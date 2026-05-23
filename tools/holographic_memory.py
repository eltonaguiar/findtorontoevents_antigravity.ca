#!/usr/bin/env python3
"""
Holographic Memory — Structured Shared Knowledge for the Agent Swarm.

A git-synced JSON file (agent_shared_memory.json) that survives Redis restarts
and syncs across PCs via git push/pull. Every agent contributes fragments;
the full picture emerges from all contributions combined.

Schema sections:
  swarm     — Current plan, phase, collective priorities
  facts     — Assertions with confidence, source, verification trail
  decisions — What was decided, why, by whom, agreement status
  learnings — Lessons learned, when they apply, discovery context
  context   — Repo state, known issues, active work
  notes     — Per-agent private notes and handoff memos

Usage:
  python tools/holographic_memory.py swarm plan "Phase 2: cross-PC bridge"
  python tools/holographic_memory.py swarm status
  python tools/holographic_memory.py fact set <key> <value> [--confidence high] [--tags tag1,tag2]
  python tools/holographic_memory.py fact get <key>
  python tools/holographic_memory.py fact list [--tag <tag>]
  python tools/holographic_memory.py decide <what> <rationale> [--id <id>]
  python tools/holographic_memory.py decisions [--active]
  python tools/holographic_memory.py learn "<lesson>" [--context <when>] [--tags tag1,tag2]
  python tools/holographic_memory.py learnings [--tag <tag>]
  python tools/holographic_memory.py context set <key> <value>
  python tools/holographic_memory.py context show
  python tools/holographic_memory.py note <agent_id> "<content>" [--handoff]
  python tools/holographic_memory.py notes <agent_id>
  python tools/holographic_memory.py sync         # sync to Redis agent:shared:memory
  python tools/holographic_memory.py dump          # show full memory
"""

import argparse
import json
import os
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Config ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
MEMORY_FILE = REPO_ROOT / "agent_shared_memory.json"
MAX_FACTS = 500
MAX_DECISIONS = 200
MAX_LEARNINGS = 200
MAX_CONTEXT_VALUES = 100

try:
    import redis as _redis_mod
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ── Schema skeleton ─────────────────────────────────────────────────

def _empty_memory() -> dict:
    return {
        "_meta": {
            "version": 2,
            "created": _now(),
            "last_updated": _now(),
            "updated_by": "system",
        },
        "swarm": {
            "plan": "",
            "phase": "",
            "priority": "",
            "status": "initializing",
        },
        "facts": [],
        "decisions": [],
        "learnings": [],
        "context": {},
        "notes": {},
    }


# ── Helpers ─────────────────────────────────────────────────────────

def _acquire_lock(lock_path: Path, timeout: float = 5.0) -> bool:
    """Acquire a simple file lock with retry. Returns True if locked."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{_now()} {_agent_id()}\n".encode())
            os.close(fd)
            return True
        except (OSError, FileExistsError):
            # Check for stale lock (>30s old)
            try:
                if lock_path.exists():
                    age = time.time() - lock_path.stat().st_mtime
                    if age > 30:
                        lock_path.unlink(missing_ok=True)
                        continue
            except Exception:
                pass
            time.sleep(0.05)  # 50ms retry
    return False


def _release_lock(lock_path: Path) -> None:
    """Release a file lock."""
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def _load() -> dict:
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Migrate v1 → v2
            if data.get("_meta", {}).get("version", 1) < 2:
                data.setdefault("swarm", {"plan": "", "phase": "", "priority": "", "status": "initializing"})
                data["_meta"]["version"] = 2
            return data
        except (json.JSONDecodeError, IOError):
            pass
    return _empty_memory()


def _save(data: dict, agent_id: str) -> None:
    data["_meta"]["last_updated"] = _now()
    data["_meta"]["updated_by"] = agent_id
    # Prune if over limits
    if len(data.get("facts", [])) > MAX_FACTS:
        data["facts"] = data["facts"][-MAX_FACTS:]
    if len(data.get("decisions", [])) > MAX_DECISIONS:
        data["decisions"] = data["decisions"][-MAX_DECISIONS:]
    if len(data.get("learnings", [])) > MAX_LEARNINGS:
        data["learnings"] = data["learnings"][-MAX_LEARNINGS:]
    if len(data.get("context", {})) > MAX_CONTEXT_VALUES:
        keys = list(data["context"].keys())
        for k in keys[MAX_CONTEXT_VALUES:]:
            del data["context"][k]
    lock_path = MEMORY_FILE.with_suffix(".json.lock")
    if _acquire_lock(lock_path):
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            _release_lock(lock_path)
    else:
        # Fallback: write anyway but warn
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("[warn] Could not acquire lock — wrote without locking", file=sys.stderr)


def _get_redis():
    if not REDIS_AVAILABLE:
        return None
    try:
        r = _redis_mod.Redis(host="localhost", port=6379, decode_responses=False)
        r.ping()
        return r
    except Exception:
        return None


def _txt(blob) -> str:
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    return blob.decode("utf-8", errors="replace")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hostname() -> str:
    return socket.gethostname()


def _agent_id() -> str:
    return os.environ.get("SWARM_AGENT_ID", "unknown")


def _uid() -> str:
    return uuid.uuid4().hex[:12]


# ── Swarm commands ──────────────────────────────────────────────────

def cmd_swarm_plan(plan: str) -> None:
    """Set the swarm's current plan/objective."""
    data = _load()
    data["swarm"]["plan"] = plan
    data["swarm"]["status"] = "active"
    _save(data, _agent_id())
    print(f"[swarm] plan set: {plan[:120]}")


def cmd_swarm_phase(phase: str) -> None:
    """Set the current phase of work."""
    data = _load()
    data["swarm"]["phase"] = phase
    _save(data, _agent_id())
    print(f"[swarm] phase: {phase}")


def cmd_swarm_priority(priority: str) -> None:
    """Set the highest priority item."""
    data = _load()
    data["swarm"]["priority"] = priority
    _save(data, _agent_id())
    print(f"[swarm] priority: {priority}")


def cmd_swarm_status() -> None:
    """Show swarm overview."""
    data = _load()
    s = data.get("swarm", {})
    print("=== SWARM MEMORY ===")
    print(f"  Plan:     {s.get('plan', '(none)')[:80]}")
    print(f"  Phase:    {s.get('phase', '(none)')}")
    print(f"  Priority: {s.get('priority', '(none)')}")
    print(f"  Status:   {s.get('status', 'unknown')}")
    print(f"  Facts:    {len(data.get('facts', []))}")
    print(f"  Decisions:{len(data.get('decisions', []))}")
    print(f"  Learnings:{len(data.get('learnings', []))}")
    print(f"  Context keys: {len(data.get('context', {}))}")
    print(f"  Agent notes:  {len(data.get('notes', {}))}")
    print(f"  Last updated: {data['_meta'].get('last_updated', 'never')} by {data['_meta'].get('updated_by', '?')}")


# ── Fact commands ───────────────────────────────────────────────────

def cmd_fact_set(key: str, value: str, confidence: str = "medium", tags: str = "") -> None:
    """Assert a fact into shared memory with confidence and tags."""
    data = _load()
    # Remove existing fact with same key
    data["facts"] = [f for f in data.get("facts", []) if f.get("key") != key]

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    fact = {
        "key": key,
        "value": value,
        "confidence": confidence,
        "source": _agent_id(),
        "pc": _hostname(),
        "discovered_at": _now(),
        "verified_by": [],
        "tags": tag_list,
    }
    data.setdefault("facts", []).append(fact)
    _save(data, _agent_id())
    print(f"[fact] set '{key}' [{confidence}]: {value[:100]}")


def cmd_fact_get(key: str) -> None:
    """Retrieve a fact by key."""
    data = _load()
    for f in data.get("facts", []):
        if f.get("key") == key:
            conf = f.get("confidence", "?")
            src = f.get("source", "?")
            at = f.get("discovered_at", "?")[:19]
            verified = f.get("verified_by", [])
            tags = f.get("tags", [])
            print(f"[fact] {key} = {f.get('value', '')}")
            print(f"       confidence: {conf} | source: {src} @ {at}")
            if verified:
                print(f"       verified by: {', '.join(verified)}")
            if tags:
                print(f"       tags: {', '.join(tags)}")
            return
    print(f"[fact] '{key}' not found")


def cmd_fact_verify(key: str) -> None:
    """Mark a fact as verified by you."""
    data = _load()
    for f in data.get("facts", []):
        if f.get("key") == key:
            me = _agent_id()
            if me not in f.setdefault("verified_by", []):
                f["verified_by"].append(me)
                f["confidence"] = "high"  # verification boosts confidence
                _save(data, me)
                print(f"[fact] verified '{key}' by {me}")
            else:
                print(f"[fact] '{key}' already verified by {me}")
            return
    print(f"[fact] '{key}' not found")


def cmd_fact_delete(key: str) -> None:
    """Delete a fact by key."""
    data = _load()
    before = len(data.get("facts", []))
    data["facts"] = [f for f in data.get("facts", []) if f.get("key") != key]
    after = len(data["facts"])
    if before != after:
        _save(data, _agent_id())
        print(f"[fact] deleted '{key}'")
    else:
        print(f"[fact] '{key}' not found")


def cmd_fact_list(tag: str = "", confidence: str = "") -> None:
    """List all facts, optionally filtered by tag or confidence."""
    data = _load()
    facts = data.get("facts", [])
    if tag:
        facts = [f for f in facts if tag in f.get("tags", [])]
    if confidence:
        facts = [f for f in facts if f.get("confidence") == confidence]
    if not facts:
        print("[fact] no facts found")
        return
    print(f"[fact] {len(facts)} fact(s):")
    for f in facts:
        conf_mark = {"high": "!", "medium": "~", "low": "?"}.get(f.get("confidence", ""), " ")
        print(f"  {conf_mark} {f.get('key', '?')}: {str(f.get('value', ''))[:80]}")


# ── Decision commands ────────────────────────────────────────────────

def cmd_decide(what: str, rationale: str, decision_id: str = "") -> None:
    """Record a decision in shared memory."""
    data = _load()
    did = decision_id or _uid()
    decision = {
        "id": did,
        "what": what,
        "rationale": rationale,
        "made_by": _agent_id(),
        "made_at": _now(),
        "agreed_by": [_agent_id()],
        "status": "active",
    }
    data.setdefault("decisions", []).append(decision)
    _save(data, _agent_id())
    print(f"[decision] {did}: {what[:100]}")


def cmd_decision_agree(decision_id: str) -> None:
    """Agree with an existing decision."""
    data = _load()
    for d in data.get("decisions", []):
        if d.get("id") == decision_id:
            me = _agent_id()
            if me not in d.setdefault("agreed_by", []):
                d["agreed_by"].append(me)
                _save(data, me)
                print(f"[decision] {me} agrees with '{decision_id}'")
            else:
                print(f"[decision] already agreed by {me}")
            return
    print(f"[decision] '{decision_id}' not found")


def cmd_decision_close(decision_id: str, resolution: str = "") -> None:
    """Close/resolve a decision."""
    data = _load()
    for d in data.get("decisions", []):
        if d.get("id") == decision_id:
            d["status"] = "closed"
            d["closed_at"] = _now()
            d["closed_by"] = _agent_id()
            if resolution:
                d["resolution"] = resolution
            _save(data, _agent_id())
            print(f"[decision] closed '{decision_id}'" + (f": {resolution[:80]}" if resolution else ""))
            return
    print(f"[decision] '{decision_id}' not found")


def cmd_decisions(active_only: bool = False) -> None:
    """List decisions."""
    data = _load()
    decisions = data.get("decisions", [])
    if active_only:
        decisions = [d for d in decisions if d.get("status") == "active"]
    if not decisions:
        print("[decision] no decisions recorded")
        return
    print(f"[decision] {len(decisions)} decision(s):")
    for d in decisions:
        status = d.get("status", "?")
        did = d.get("id", "?")
        what = d.get("what", "")[:80]
        by = d.get("made_by", "?")
        agreed = len(d.get("agreed_by", []))
        print(f"  [{status}] {did}: {what}")
        print(f"          by {by} | {agreed} agree | {d.get('rationale', '')[:80]}")


# ── Learning commands ────────────────────────────────────────────────

def cmd_learn(lesson: str, context: str = "", tags: str = "") -> None:
    """Record a lesson learned by the swarm. Deduplicates by similar content."""
    data = _load()
    
    # Deduplicate: check if a similar lesson was already recorded (by key words)
    lesson_lower = lesson.lower().strip()
    for existing in data.get("learnings", []):
        existing_lower = existing.get("lesson", "").lower().strip()
        # Simple dedup: first 60 chars match or full short lessons match
        if (len(lesson_lower) > 40 and lesson_lower[:60] == existing_lower[:60]) or \
           (len(lesson_lower) <= 40 and lesson_lower == existing_lower):
            print(f"[learning] duplicate skipped: {lesson[:100]}")
            return
    
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    learning = {
        "id": _uid(),
        "lesson": lesson,
        "context": context,
        "learned_by": _agent_id(),
        "learned_at": _now(),
        "pc": _hostname(),
        "tags": tag_list,
    }
    data.setdefault("learnings", []).append(learning)
    _save(data, _agent_id())
    print(f"[learning] recorded: {lesson[:100]}")


def cmd_learnings(tag: str = "") -> None:
    """List learnings, optionally filtered by tag."""
    data = _load()
    learnings = data.get("learnings", [])
    if tag:
        learnings = [l for l in learnings if tag in l.get("tags", [])]
    if not learnings:
        print("[learning] no learnings recorded")
        return
    print(f"[learning] {len(learnings)} learning(s):")
    for l in learnings:
        lid = l.get("id", "?")
        lesson = l.get("lesson", "")[:100]
        by = l.get("learned_by", "?")
        ctx = l.get("context", "")[:60]
        tags_str = ", ".join(l.get("tags", []))
        print(f"  {lid}: {lesson}")
        print(f"       by {by} | context: {ctx}")
        if tags_str:
            print(f"       tags: {tags_str}")


def cmd_learning_delete(learning_id: str) -> None:
    """Delete a learning by ID."""
    data = _load()
    before = len(data.get("learnings", []))
    data["learnings"] = [l for l in data.get("learnings", []) if l.get("id") != learning_id]
    after = len(data["learnings"])
    if before != after:
        _save(data, _agent_id())
        print(f"[learning] deleted '{learning_id}'")
    else:
        print(f"[learning] '{learning_id}' not found")


# ── Context commands ─────────────────────────────────────────────────

def cmd_context_set(key: str, value: str) -> None:
    """Set a context value (repo state, known issue, etc.)."""
    data = _load()
    data.setdefault("context", {})[key] = {
        "value": value,
        "set_by": _agent_id(),
        "set_at": _now(),
    }
    _save(data, _agent_id())
    print(f"[context] {key} = {value[:100]}")


def cmd_context_show() -> None:
    """Show all context values."""
    data = _load()
    ctx = data.get("context", {})
    if not ctx:
        print("[context] empty")
        return
    print(f"[context] {len(ctx)} value(s):")
    for key, entry in sorted(ctx.items()):
        if isinstance(entry, dict):
            val = entry.get("value", "")[:80]
            by = entry.get("set_by", "?")
            print(f"  {key}: {val} (by {by})")
        else:
            print(f"  {key}: {str(entry)[:80]}")


# ── Agent notes commands ─────────────────────────────────────────────

def cmd_note(agent_id: str, content: str, handoff: bool = False) -> None:
    """Write a note for an agent (private or handoff)."""
    data = _load()
    note_type = "handoff" if handoff else "private"
    note = {
        "type": note_type,
        "content": content,
        "written_by": _agent_id(),
        "written_at": _now(),
    }
    data.setdefault("notes", {}).setdefault(agent_id, []).append(note)
    _save(data, _agent_id())
    kind = "handoff" if handoff else "private note"
    print(f"[note] {kind} for {agent_id}: {content[:100]}")


def cmd_notes(agent_id: str) -> None:
    """Read notes for an agent."""
    data = _load()
    notes = data.get("notes", {}).get(agent_id, [])
    if not notes:
        print(f"[note] no notes for {agent_id}")
        return
    print(f"[note] {len(notes)} note(s) for {agent_id}:")
    for n in notes:
        ntype = n.get("type", "?")
        content = n.get("content", "")[:120]
        by = n.get("written_by", "?")
        at = n.get("written_at", "?")[:19]
        print(f"  [{ntype}] from {by} @ {at}: {content}")


# ── Sync command ─────────────────────────────────────────────────────

def cmd_sync() -> None:
    """Bidirectional sync between holographic memory file and Redis."""
    r = _get_redis()
    if not r:
        print("[sync] Redis not available — file-only")
        return

    data = _load()
    count = 0

    # File → Redis: push swarm info
    swarm = data.get("swarm", {})
    for k in ["plan", "phase", "priority", "status"]:
        if swarm.get(k):
            r.hset("agent:shared:memory", f"swarm_{k}", swarm[k])
            count += 1

    # File → Redis: push facts summary (last 20)
    facts = data.get("facts", [])
    for f in facts[-20:]:
        r.hset("agent:shared:memory", f"fact_{f['key']}", json.dumps({
            "value": f.get("value", ""),
            "confidence": f.get("confidence", ""),
            "source": f.get("source", ""),
        }))
        count += 1

    # File → Redis: push context
    for key, entry in data.get("context", {}).items():
        val = entry.get("value", entry) if isinstance(entry, dict) else entry
        r.hset("agent:shared:memory", f"ctx_{key}", val)
        count += 1

    # Redis → File: pull facts from Redis that don't exist in file
    raw = r.hgetall("agent:shared:memory")
    if raw:
        existing_keys = {f.get("key") for f in data.get("facts", [])}
        for k, v in raw.items():
            key = _txt(k)
            if key.startswith("fact_") and key.removeprefix("fact_") not in existing_keys:
                try:
                    entry = json.loads(_txt(v))
                    fact = {
                        "key": key.removeprefix("fact_"),
                        "value": entry.get("value", ""),
                        "confidence": entry.get("confidence", "medium"),
                        "source": "redis-sync",
                        "pc": "cross-pc",
                        "discovered_at": _now(),
                        "verified_by": [],
                        "tags": ["synced-from-redis"],
                    }
                    data.setdefault("facts", []).append(fact)
                    count += 1
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            elif key.startswith("ctx_") and key.removeprefix("ctx_") not in data.get("context", {}):
                data.setdefault("context", {})[key.removeprefix("ctx_")] = {
                    "value": _txt(v),
                    "set_by": "redis-sync",
                    "set_at": _now(),
                }
                count += 1

    _save(data, "sync")

    # Also update the swarm state file's memory section
    try:
        state_file = REPO_ROOT / "agent_swarm_state.json"
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            state.setdefault("memory", {})["holographic_synced"] = _now()
            state["memory"]["swarm_plan"] = swarm.get("plan", "")
            state["memory"]["swarm_phase"] = swarm.get("phase", "")
            state["memory"]["facts_count"] = str(len(facts))
            state["memory"]["decisions_count"] = str(len(data.get("decisions", [])))
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    print(f"[sync] {count} items synced bidirectionally (file <-> Redis)")


# ── Dump command ─────────────────────────────────────────────────────

def cmd_dump(section: str = "") -> None:
    """Show full memory or a specific section."""
    data = _load()

    if section:
        content = data.get(section)
        if content is not None:
            print(json.dumps({section: content}, indent=2, ensure_ascii=False))
        else:
            print(f"[dump] section '{section}' not found. Available: swarm, facts, decisions, learnings, context, notes")
        return

    # Full dump but skip verbose arrays in summary
    summary = {
        "_meta": data.get("_meta", {}),
        "swarm": data.get("swarm", {}),
        "facts_count": len(data.get("facts", [])),
        "decisions_count": len(data.get("decisions", [])),
        "learnings_count": len(data.get("learnings", [])),
        "context": data.get("context", {}),
        "notes_agents": list(data.get("notes", {}).keys()),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Holographic Memory — Structured shared knowledge for the agent swarm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/holographic_memory.py swarm plan "Phase 2: cross-PC bridge"
  python tools/holographic_memory.py swarm status
  python tools/holographic_memory.py fact set redis_bus "Redis running at localhost:6379" --confidence high
  python tools/holographic_memory.py fact get redis_bus
  python tools/holographic_memory.py fact list --tag infrastructure
  python tools/holographic_memory.py decide "Use git-based state file" "Zero config, works cross-PC"
  python tools/holographic_memory.py decisions --active
  python tools/holographic_memory.py learn "decode_responses=False avoids Unicode crashes on Windows" --tags windows,redis
  python tools/holographic_memory.py context set known_issue "claude-peers MCP is localhost-only"
  python tools/holographic_memory.py note buffy "Remember to run sync after changes" --handoff
  python tools/holographic_memory.py sync
  python tools/holographic_memory.py dump
        """,
    )
    sub = parser.add_subparsers(dest="command", help="Section to operate on")

    # ── swarm ──
    p = sub.add_parser("swarm", help="Swarm-level state")
    sub_s = p.add_subparsers(dest="swarm_cmd")
    s = sub_s.add_parser("plan")
    s.add_argument("plan_text")
    s = sub_s.add_parser("phase")
    s.add_argument("phase_name")
    s = sub_s.add_parser("priority")
    s.add_argument("priority_text")
    sub_s.add_parser("status")

    # ── fact ──
    p = sub.add_parser("fact", help="Shared facts/assertions")
    sub_f = p.add_subparsers(dest="fact_cmd")
    f = sub_f.add_parser("set")
    f.add_argument("key")
    f.add_argument("value")
    f.add_argument("--confidence", default="medium", choices=["high", "medium", "low"])
    f.add_argument("--tags", default="", help="Comma-separated tags")
    f = sub_f.add_parser("get")
    f.add_argument("key")
    f = sub_f.add_parser("verify")
    f.add_argument("key")
    f = sub_f.add_parser("delete")
    f.add_argument("key")
    f = sub_f.add_parser("list")
    f.add_argument("--tag", default="")
    f.add_argument("--confidence", default="", choices=["", "high", "medium", "low"])

    # ── decide ──
    p = sub.add_parser("decide", help="Record a decision")
    p.add_argument("what")
    p.add_argument("rationale")
    p.add_argument("--id", default="", dest="decision_id", help="Custom decision ID")

    # ── decisions ──
    p = sub.add_parser("decisions", help="List decisions")
    p.add_argument("--active", action="store_true")

    # ── agree ──
    p = sub.add_parser("agree", help="Agree with a decision")
    p.add_argument("decision_id")

    # ── close ──
    p = sub.add_parser("close", help="Close/resolve a decision")
    p.add_argument("decision_id")
    p.add_argument("--resolution", default="", help="How the decision was resolved")

    # ── learn ──
    p = sub.add_parser("learn", help="Record a lesson learned")
    p.add_argument("lesson")
    p.add_argument("--context", default="", help="When/where this applies")
    p.add_argument("--tags", default="", help="Comma-separated tags")

    # ── learnings ──
    p = sub.add_parser("learnings", help="List learnings")
    p.add_argument("--tag", default="")

    # ── forget ──
    p = sub.add_parser("forget", help="Delete a learning by ID")
    p.add_argument("learning_id")

    # ── context ──
    p = sub.add_parser("context", help="Shared context/state")
    sub_c = p.add_subparsers(dest="context_cmd")
    c = sub_c.add_parser("set")
    c.add_argument("key")
    c.add_argument("value")
    sub_c.add_parser("show")

    # ── note ──
    p = sub.add_parser("note", help="Write agent note")
    p.add_argument("agent_id")
    p.add_argument("content")
    p.add_argument("--handoff", action="store_true")

    # ── notes ──
    p = sub.add_parser("notes", help="Read agent notes")
    p.add_argument("agent_id")

    # ── sync ──
    sub.add_parser("sync", help="Sync memory to Redis bus")

    # ── dump ──
    p = sub.add_parser("dump", help="Show memory contents")
    p.add_argument("--section", default="", help="Specific section to show")

    args = parser.parse_args()

    if args.command == "swarm":
        if args.swarm_cmd == "plan":
            cmd_swarm_plan(args.plan_text)
        elif args.swarm_cmd == "phase":
            cmd_swarm_phase(args.phase_name)
        elif args.swarm_cmd == "priority":
            cmd_swarm_priority(args.priority_text)
        elif args.swarm_cmd == "status":
            cmd_swarm_status()
        else:
            parser.parse_args(["swarm", "--help"])
    elif args.command == "fact":
        if args.fact_cmd == "set":
            cmd_fact_set(args.key, args.value, args.confidence, args.tags)
        elif args.fact_cmd == "get":
            cmd_fact_get(args.key)
        elif args.fact_cmd == "verify":
            cmd_fact_verify(args.key)
        elif args.fact_cmd == "delete":
            cmd_fact_delete(args.key)
        elif args.fact_cmd == "list":
            cmd_fact_list(args.tag, args.confidence)
        else:
            parser.parse_args(["fact", "--help"])
    elif args.command == "decide":
        cmd_decide(args.what, args.rationale, args.decision_id)
    elif args.command == "decisions":
        cmd_decisions(args.active)
    elif args.command == "agree":
        cmd_decision_agree(args.decision_id)
    elif args.command == "close":
        cmd_decision_close(args.decision_id, args.resolution)
    elif args.command == "learn":
        cmd_learn(args.lesson, args.context, args.tags)
    elif args.command == "learnings":
        cmd_learnings(args.tag)
    elif args.command == "forget":
        cmd_learning_delete(args.learning_id)
    elif args.command == "context":
        if args.context_cmd == "set":
            cmd_context_set(args.key, args.value)
        elif args.context_cmd == "show":
            cmd_context_show()
        else:
            parser.parse_args(["context", "--help"])
    elif args.command == "note":
        cmd_note(args.agent_id, args.content, args.handoff)
    elif args.command == "notes":
        cmd_notes(args.agent_id)
    elif args.command == "sync":
        cmd_sync()
    elif args.command == "dump":
        cmd_dump(args.section)
    else:
        # Default: show swarm status
        cmd_swarm_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())

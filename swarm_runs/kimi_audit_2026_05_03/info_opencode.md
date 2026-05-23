# OpenCode CLI — Comprehensive Research Report

**Research Date:** 2026-05-02  
**Report for:** Building a local AI agent swarm using OpenCode as a worker node  
**Status:** ✅ Actively maintained (latest release v1.14.33, May 2, 2026)

---

## 1. Official Website & GitHub Repository

| Resource | URL |
|----------|-----|
| **Official Website** | https://opencode.ai |
| **Documentation** | https://opencode.ai/docs/ |
| **Active GitHub Repo** | https://github.com/anomalyco/opencode |
| **Changelog** | https://opencode.ai/changelog |
| **Releases** | https://github.com/anomalyco/opencode/releases |
| **Community Discord** | https://opencode.ai/discord |

### ⚠️ Important: Repo Migration
The original repository `github.com/opencode-ai/opencode` was **archived on September 18, 2025** and is now read-only. All active development moved to `github.com/anomalyco/opencode`.

### Maintenance Status
- **Latest release:** v1.14.33 (May 2, 2026)
- **Total releases:** 784+
- **Commits:** 12,195+
- **Contributors:** 876+
- **Stars:** 154k+
- **Activity:** Daily releases and commits. Extremely actively maintained.

---

## 2. Installation Commands

### Recommended: Curl Install Script (fastest, works on any Unix)
```bash
curl -fsSL https://opencode.ai/install | bash
```

### NPM (Node.js 18+)
```bash
npm install -g opencode-ai
```

### Bun
```bash
bun add -g opencode-ai
```

### Homebrew (macOS & Linux)
```bash
# Recommended tap (most up-to-date)
brew install anomalyco/tap/opencode

# Alternative (Homebrew core, updated less frequently)
brew install opencode
```

### Arch Linux
```bash
sudo pacman -S opencode           # Stable
paru -S opencode-bin              # Latest from AUR
```

### Windows
```bash
# Chocolatey
choco install opencode

# Scoop
scoop install opencode

# NPM
npm install -g opencode-ai
```

### Mise
```bash
mise use -g github:anomalyco/opencode
```

### Docker
```bash
docker run -it --rm ghcr.io/anomalyco/opencode
```

### Go Install (build from source)
```bash
go install github.com/opencode-ai/opencode@latest
```

### Upgrade
```bash
npm update -g opencode-ai
brew upgrade opencode
# Or re-run the install script
curl -fsSL https://opencode.ai/install | bash
```

---

## 3. Headless / Non-Interactive Mode

### ✅ `opencode run` — Non-Interactive CLI Execution
OpenCode has a dedicated `run` subcommand for headless, non-interactive execution. This is the primary mode for scripting, automation, CI/CD, and swarm integration.

```bash
# Basic one-shot prompt
opencode run "Explain how closures work in JavaScript"

# Attach files to the prompt
opencode run --file path/to/file.txt "Analyze this file"

# Use a specific model
opencode run --model anthropic/claude-sonnet-4-20250514 "Write a Python HTTP server"

# Use a specific agent
opencode run --agent plan "Analyze the codebase without making changes"

# JSON event output (machine-readable)
opencode run --format json "Create a React component"

# Continue a previous session
opencode run --continue "Continue the previous task"

# Fork a session
opencode run --session abc123 --fork "Branch this session"

# Auto-approve permissions (DANGEROUS — use only in trusted environments)
opencode run --dangerously-skip-permissions "Refactor everything"
```

#### `opencode run` Flags
| Flag | Short | Description |
|------|-------|-------------|
| `--command` | | The command to run |
| `--continue` | `-c` | Continue the last session |
| `--session` | `-s` | Session ID to continue |
| `--fork` | | Fork the session when continuing |
| `--share` | | Share the session |
| `--model` | `-m` | Model to use (`provider/model` format) |
| `--agent` | | Agent to use |
| `--file` | `-f` | File(s) to attach |
| `--format` | | Output format: `default` or `json` |
| `--title` | | Title for the session |
| `--attach` | | Attach to a running opencode server |
| `--port` | | Port for the local server |
| `--dangerously-skip-permissions` | | Auto-approve non-denied permissions |

### ✅ `opencode serve` — Headless HTTP Server
Starts a standalone HTTP server with a full OpenAPI 3.1 API. No TUI. Perfect for programmatic control and swarm integration.

```bash
# Start headless server on default port 4096
opencode serve

# With specific port and hostname
opencode serve --port 4096 --hostname 127.0.0.1

# Accept connections from any network interface (requires auth!)
opencode serve --hostname 0.0.0.0 --port 4096

# Enable CORS for custom frontends
opencode serve --cors http://localhost:5173 --cors https://app.example.com

# Enable mDNS discovery on local network
opencode serve --mdns --mdns-domain myproject.local

# Enable basic auth
OPENCODE_SERVER_PASSWORD=your-password opencode serve
OPENCODE_SERVER_USERNAME=myuser OPENCODE_SERVER_PASSWORD=secret opencode serve
```

### `opencode attach` — Attach TUI to Running Server
```bash
# Start backend server
opencode serve --port 4096 --hostname 0.0.0.0

# In another terminal, attach TUI
opencode attach http://10.20.30.40:4096

# Attach with session
opencode attach http://localhost:4096 --session abc123
```

### `opencode web` — Headless Server + Web UI
```bash
opencode web --port 4096 --hostname 0.0.0.0
```

### ⚠️ Known Limitation: `run --attach` Bug
In version 1.1.60 and some earlier versions, `opencode run --attach http://localhost:4096` can fail with:
```
No context found for instance
```
This is a documented bug/limitation when running against a headless server. For reliable automation, use either:
- Direct `opencode run` (starts its own server temporarily)
- The HTTP API directly via curl/SDK
- `opencode acp` for stdio-based programmatic access

---

## 4. JSON Output / Event Output Capabilities

### ✅ `--format json` on `opencode run`
`opencode run --format json` outputs **newline-delimited JSON (JSONL)** to stdout, one JSON object per line. This is ideal for parsing in real-time.

#### Event Types
| Event Type | Description |
|-----------|-------------|
| `step_start` | Start of a processing step |
| `text` | Text output from the model |
| `tool_use` | Tool invocation (emitted when `status == "completed"`) |
| `step_finish` | End of a processing step |
| `error` | Error event |
| `message.part.updated` | Real-time message part updates (thinking, reasoning) |

#### Example Events

**Text output:**
```json
{"type":"text","timestamp":1767036064268,"sessionID":"ses_xxx","part":{"id":"prt_xxx","type":"text","text":"```\nhello\n```","time":{"start":1767036064265,"end":1767036064265}}}
```

**Tool completion:**
```json
{"type":"tool_use","timestamp":1767036061199,"sessionID":"ses_xxx","part":{"id":"prt_xxx","callID":"r9bQWsNLvOrJGIOz","tool":"bash","state":{"status":"completed","input":{"command":"echo hello","description":"Print hello to stdout"},"output":"hello\n","title":"Print hello to stdout","metadata":{"output":"hello\n","exit":0,"description":"Print hello to stdout"},"time":{"start":1767036061123,"end":1767036061173}}}}
```

**Step finish (final):**
```json
{"type":"step_finish","timestamp":1767036064273,"sessionID":"ses_xxx","part":{"id":"prt_xxx","type":"step-finish","reason":"stop","snapshot":"09dd05d11a4ac013136c1df10932efc0ad9116e8","cost":0.001,"tokens":{"input":671,"output":8,"reasoning":0,"cache":{"read":21415,"write":0}}}}
```

**Step finish (continuing with tool calls):**
```json
{"type":"step_finish","timestamp":1767036061205,"sessionID":"ses_xxx","part":{"id":"prt_xxx","type":"step-finish","reason":"tool-calls","snapshot":"ee3406d50c7d9048674bbb1a3e325d82513b74ed","cost":0,"tokens":{"input":21772,"output":110,"reasoning":0,"cache":{"read":0,"write":0}}}}
```

### Important Notes
- The CLI JSON output only emits `tool_use` events when the tool **finishes** (`status == "completed"`). Pending/running tool states exist in the schema but are **not emitted**.
- `--format json` currently only emits tool completion events, not intermediate states.
- For real-time intermediate streaming, use the **HTTP SSE event stream** (`/global/event`) or the **SDK**.

### `opencode session list --format json`
```bash
opencode session list --format json
```

### `opencode export [sessionID]`
Exports session data as JSON to stdout.
```bash
opencode export abc123 > session.json
```

---

## 5. Provider & API Key Configuration

### Supported Providers (75+)
OpenCode uses the **AI SDK** and **Models.dev** to support 75+ LLM providers, including:

| Provider | Auth Method | Notes |
|----------|-------------|-------|
| **Anthropic** | API Key or Claude Pro/Max subscription | Browser OAuth supported |
| **OpenAI** | API Key or ChatGPT Plus/Pro subscription | Browser OAuth supported |
| **OpenRouter** | API Key | Aggregates multiple models |
| **Google (Gemini / Vertex AI)** | API Key | |
| **Ollama** | No key needed | Local models via `http://localhost:11434` |
| **GitHub Copilot** | GitHub device code auth | Requires Copilot subscription |
| **GitLab Duo** | Personal Access Token | |
| **DeepSeek** | API Key | |
| **Groq** | API Key | |
| **Fireworks AI** | API Key | |
| **Together AI** | API Key | |
| **Cerebras** | API Key | |
| **xAI (Grok)** | API Key | |
| **OpenCode Zen** | OpenCode API Key | Official curated/tested models |
| **OpenCode Go** | Subscription | Low-cost access to open models |
| **302.AI, Azure OpenAI, Baseten, Cloudflare, Helicone, Hugging Face, IO.NET, LM Studio, Moonshot AI, MiniMax, Nebius, NVIDIA, SAP AI Core, Scaleway, STACKIT, Venice AI, Vercel AI Gateway, Z.AI** | Various | |

### Storing Credentials
```bash
# Interactive credential setup (TUI)
/connect

# Or in the terminal:
opencode auth login
```
Credentials are stored at: `~/.local/share/opencode/auth.json`

### Configuration File (`opencode.json` or `opencode.jsonc`)

#### Basic Config
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  // Default model
  "model": "anthropic/claude-sonnet-4-20250514",
  // Small model for lightweight tasks (titles, summaries)
  "small_model": "anthropic/claude-haiku-4-20250514",
  // Server settings
  "server": {
    "port": 4096,
    "hostname": "127.0.0.1"
  },
  // Permission defaults
  "permission": {
    "edit": "ask",
    "bash": "ask"
  }
}
```

#### Custom Base URL / Proxy
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "anthropic": {
      "options": {
        "baseURL": "https://api.anthropic.com/v1"
      }
    }
  }
}
```

#### Custom OpenAI-Compatible Provider (e.g., local endpoint, vLLM, etc.)
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "my-local": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "My Local Model",
      "options": {
        "baseURL": "http://127.0.0.1:8080/v1",
        "apiKey": "optional-key",
        "headers": {}
      },
      "models": {
        "qwen3-coder": {
          "name": "Qwen3 Coder (local)"
        }
      }
    }
  }
}
```

#### Ollama Configuration
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "llama3.2": { "name": "Llama 3.2" },
        "qwen3-coder": { "name": "Qwen3 Coder" }
      }
    }
  }
}
```

#### Multiple Providers with Per-Agent Models
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-20250514",
  "agent": {
    "build": {
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-20250514",
      "permission": { "edit": "allow", "bash": "allow" }
    },
    "plan": {
      "mode": "primary",
      "model": "anthropic/claude-haiku-4-20250514",
      "permission": { "edit": "deny", "bash": "deny" }
    },
    "code-reviewer": {
      "mode": "subagent",
      "model": "openai/gpt-5.2-codex-mini",
      "permission": { "edit": "deny" }
    }
  }
}
```

### Environment Variables for Configuration
| Variable | Description |
|----------|-------------|
| `OPENCODE_CONFIG` | Path to custom config file |
| `OPENCODE_CONFIG_DIR` | Custom config directory |
| `OPENCODE_CONFIG_CONTENT` | Inline JSON config |
| `OPENCODE_AUTO_SHARE` | Auto-share sessions |
| `OPENCODE_DISABLE_AUTOUPDATE` | Disable update checks |
| `OPENCODE_SERVER_PASSWORD` | Server basic auth password |
| `OPENCODE_SERVER_USERNAME` | Server basic auth username |
| `OPENCODE_CLIENT` | Client identifier |

---

## 6. Model Switching & Provider Support

### Model String Format
All models are referenced as `provider/model`:
```bash
opencode run --model anthropic/claude-sonnet-4-20250514 "..."
opencode run --model openai/gpt-5.2-codex-mini "..."
opencode run --model ollama/llama3.2 "..."
opencode run --model openrouter/anthropic/claude-3.5-sonnet "..."
```

### Listing Available Models
```bash
# List all models
opencode models

# Refresh model list from providers
opencode models --refresh

# List models for a specific provider
opencode models anthropic
```

### Provider Configuration via HTTP API
```bash
# List all providers
curl http://localhost:4096/provider

# List auth methods
curl http://localhost:4096/provider/auth

# Get config + provider defaults
curl http://localhost:4096/config/providers
```

---

## 7. Agent / Swarm Features

### Built-in Agent Types

| Agent | Mode | Description | Tool Access |
|-------|------|-------------|-------------|
| **build** | primary | Default agent. Full tool access for development. | All tools enabled |
| **plan** | primary | Restricted agent for planning/analysis. No file edits or bash by default. | `edit: ask`, `bash: ask` |
| **general** | subagent | General-purpose agent for multi-step research. Full tool access (except todo). | Most tools |
| **explore** | subagent | Fast, read-only codebase exploration. Cannot modify files. | Read/search only |
| **compaction** | primary (hidden) | Automatic context compaction when sessions get long. | Internal |
| **title** | primary (hidden) | Generates session titles. | Internal |
| **summary** | primary (hidden) | Creates session summaries. | Internal |

### Agent Modes
- **`primary`** — Main assistants you interact with directly. Switch with Tab key.
- **`subagent`** — Specialized assistants invoked by primary agents or via `@mention`.
- **`all`** — Can function as both primary and subagent.

### Creating Custom Agents

#### Via CLI (Interactive)
```bash
opencode agent create
```

#### Via CLI (Non-Interactive)
```bash
opencode agent create \
  --path .opencode/agents/ \
  --description "Reviews code for security issues" \
  --mode subagent \
  --permissions "read,grep" \
  --model anthropic/claude-haiku-4-20250514
```

#### Via JSON Config (`opencode.json`)
```jsonc
{
  "agent": {
    "security-auditor": {
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "You are a security auditor. Focus on: vulnerabilities, injection risks, secrets exposure.",
      "permission": {
        "edit": "deny",
        "bash": "deny",
        "read": "allow",
        "grep": "allow"
      }
    },
    "orchestrator": {
      "mode": "primary",
      "permission": {
        "task": {
          "*": "deny",
          "orchestrator-*": "allow",
          "code-reviewer": "ask"
        }
      }
    }
  }
}
```

#### Via Markdown Files
Place in `~/.config/opencode/agents/` or `.opencode/agents/`:
```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash: deny
---
You are a code reviewer. Focus on:
- Code quality and best practices
- Potential bugs and edge cases
- Performance implications
- Security considerations
Provide constructive feedback without making direct changes.
```

### Subagent Invocation
- **By primary agents:** The `task` tool automatically discovers and calls subagents.
- **By user:** Use `@mention` in messages: `@security-auditor review this code`
- **Programmatically:** Via the SDK or HTTP API by specifying `agent` parameter.

### Task Tool (Agent-to-Agent Communication)
Primary agents invoke subagents via the built-in `task` tool:
```javascript
// Conceptual: the LLM decides to call a subagent
{
  "tool": "task",
  "description": "Security review",
  "prompt": "Review auth.js for SQL injection vulnerabilities",
  "subagent_type": "security-auditor"
}
```
A new session is created for the subagent with its own model, tools, system prompt, and context window.

### Hidden Agents
Set `hidden: true` to hide from `@` autocomplete but still allow programmatic/Task tool invocation:
```jsonc
{
  "agent": {
    "internal-helper": {
      "mode": "subagent",
      "hidden": true
    }
  }
}
```

### OpenCode Swarm Plugin (Third-Party)
For more advanced swarm orchestration, the community-built **`opencode-swarm`** plugin exists:
- **Repo:** https://github.com/zaxbysauce/opencode-swarm
- **Install:** `bunx opencode-swarm install`
- **Features:** Architect-led multi-agent pipeline with gated execution (coder → reviewer → test engineer → security → docs)
- **Agents:** architect, coder, reviewer, test_engineer, critic, sme, docs, designer, and more
- **Note:** This is a third-party plugin, not official OpenCode.

---

## 8. Programmatic Invocation

### Method 1: `opencode run` via Subprocess
Simplest approach. Works from any language.
```bash
# Python example
opencode run --format json --model anthropic/claude-sonnet-4 "Your prompt here"
```

### Method 2: HTTP REST API (`opencode serve`)
The server exposes a complete OpenAPI 3.1 spec at `/doc`.

#### Key Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/global/health` | Server health + version |
| `GET` | `/global/event` | SSE stream of all events |
| `GET` | `/project` | List projects |
| `GET` | `/config` | Get configuration |
| `PATCH` | `/config` | Update configuration |
| `GET` | `/config/providers` | List providers + defaults |
| `GET` | `/provider` | All providers |
| `POST` | `/session` | Create session |
| `POST` | `/session/{id}/prompt` | Send prompt + wait for response |
| `POST` | `/session/{id}/prompt_async` | Send prompt async (fire-and-forget) |
| `GET` | `/session/{id}/event` | SSE stream for session events |
| `GET` | `/app/agents` | List available agents |
| `POST` | `/instance/dispose` | Dispose instance |

#### curl Examples
```bash
# Start server
opencode serve --port 4096 --hostname 127.0.0.1

# Health check
curl http://localhost:4096/global/health
# => {"healthy":true,"version":"1.14.33"}

# Create session
curl -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{"title":"Swarm Worker 1"}'
# => {"id":"ses_xxx",...}

# Send prompt (sync)
curl -X POST http://localhost:4096/session/ses_xxx/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "parts": [{"type":"text","text":"Generate a Python CLI tool"}],
    "model": "anthropic/claude-sonnet-4-20250514",
    "agent": "build"
  }'

# Send prompt (async / fire-and-forget)
curl -X POST http://localhost:4096/session/ses_xxx/prompt_async \
  -H "Content-Type: application/json" \
  -d '{"parts": [{"type":"text","text":"Fix the bug"}]}'
# => 204 No Content

# Get event stream (SSE)
curl http://localhost:4096/global/event

# With basic auth
curl -u opencode:your-password http://localhost:4096/global/health

# Scoped to a directory
curl "http://localhost:4096/session?directory=/workspace/app"
curl -H "X-Opencode-Directory: /workspace/app" http://localhost:4096/session
```

### Method 3: Official JS/TS SDK (`@opencode-ai/sdk`)

```bash
npm install @opencode-ai/sdk
```

#### SDK Example: Start Server + Client + Prompt
```typescript
import { createOpencode } from "@opencode-ai/sdk";

const opencode = await createOpencode({
  hostname: "127.0.0.1",
  port: 4096,
  config: {
    model: "anthropic/claude-3-5-sonnet-20241022",
  },
});

console.log(`Server running at: ${opencode.server.url}`);

// Health check
const health = await opencode.client.global.health();
console.log("Healthy:", health.data.healthy, "Version:", health.data.version);

// Create session
const session = await opencode.client.session.create({
  body: { title: "SDK quickstart demo" }
});

// Send prompt
const result = await opencode.client.session.prompt({
  path: { id: session.data.id },
  body: {
    parts: [{ type: "text", text: "Generate a small README section." }],
  },
});

console.log(result.data);

// Close server
opencode.server.close();
```

#### SDK: Connect to Existing Server (Client Only)
```typescript
import { createOpencodeClient } from "@opencode-ai/sdk";

const client = createOpencodeClient({
  baseUrl: "http://localhost:4096",
});

// Use client...
const agents = await client.app.agents();
const config = await client.config.get();
```

#### SDK API Surface
| API | Methods |
|-----|---------|
| `client.global` | `.health()`, `.event()` |
| `client.app` | `.log()`, `.agents()` |
| `client.project` | `.list()`, `.current()` |
| `client.path` | `.get()` |
| `client.config` | `.get()`, `.providers()` |
| `client.session` | `.create()`, `.get()`, `.prompt()`, `.prompt_async()`, `.list()` |
| `client.file` | Various file operations |
| `client.tui` | `.appendPrompt()`, `.submitPrompt()`, etc. |

#### SDK: Structured JSON Output
```typescript
const result = await client.session.prompt({
  path: { id: sessionId },
  body: {
    parts: [{ type: "text", text: "Research Anthropic" }],
    format: {
      type: "json_schema",
      schema: {
        type: "object",
        properties: {
          company: { type: "string" },
          founded: { type: "number" },
          products: { type: "array", items: { type: "string" } },
        },
        required: ["company", "founded"],
      },
      retryCount: 2,
    },
  },
});

console.log(result.data.info.structured_output);
// => { company: "Anthropic", founded: 2021, products: [...] }
```

### Method 4: ACP (Agent Client Protocol) over stdio
```bash
opencode acp --cwd /workspace/project
```
- Communicates via **stdin/stdout** using newline-delimited JSON-RPC 2.0
- Standard protocol for editor integrations (Zed, JetBrains)
- Good for embedding OpenCode as a subprocess agent

#### ACP Example Flow
```javascript
// Send (stdin):
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}
{"jsonrpc":"2.0","id":2,"method":"session/new","params":{"cwd":"/workspace"}}
{"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{"sessionId":"ses_xxx","prompt":[{"type":"text","text":"Fix the bug"}]}}

// Receive (stdout):
{"jsonrpc":"2.0","id":2,"result":{"sessionId":"ses_xxx"}}
{"jsonrpc":"2.0","method":"agent_message_chunk","params":{"update":{"sessionUpdate":"agent_message_chunk","content":{"text":"Let me analyze..."}}}}
{"jsonrpc":"2.0","id":3,"result":{"stopReason":"end_turn"}}
```

### Method 5: MCP (Model Context Protocol) Server Integration
OpenCode can act as an **MCP client** connecting to MCP servers for external tools, or expose its own capabilities via ACP.

---

## 9. Architecture for Agent Swarms

### Recommended Swarm Worker Setup

For each worker node in your swarm:

```bash
# 1. Install OpenCode
npm install -g opencode-ai

# 2. Configure providers (run once per machine)
opencode auth login
# Or copy pre-configured auth.json:
# cp auth.json ~/.local/share/opencode/auth.json

# 3. Create project-local config
cat > /workspace/project/opencode.json << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-20250514",
  "server": { "port": 4096, "hostname": "0.0.0.0" },
  "agent": {
    "swarm-worker": {
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-20250514",
      "permission": {
        "edit": "allow",
        "bash": "allow",
        "read": "allow",
        "write": "allow"
      }
    }
  }
}
EOF

# 4. Start headless server (as systemd service or container)
OPENCODE_SERVER_PASSWORD=worker-secret opencode serve \
  --port 4096 \
  --hostname 0.0.0.0

# 5. From orchestrator, send tasks via HTTP API
```

### Orchestrator → Worker Communication Pattern
```python
# Python orchestrator example
import requests, json

WORKERS = [
    "http://worker-1:4096",
    "http://worker-2:4096",
    "http://worker-3:4096",
]

def send_task(worker_url, prompt, model=None, agent="build"):
    # Create session
    r = requests.post(f"{worker_url}/session", json={"title": "Swarm task"})
    session_id = r.json()["id"]
    
    # Send prompt
    payload = {
        "parts": [{"type": "text", "text": prompt}],
        "agent": agent
    }
    if model:
        payload["model"] = model
    
    r = requests.post(
        f"{worker_url}/session/{session_id}/prompt",
        json=payload,
        auth=("opencode", "worker-secret")
    )
    return r.json()

# Parallel task distribution
results = []
for worker in WORKERS:
    result = send_task(worker, "Refactor auth module")
    results.append(result)
```

### Using `opencode run` for One-Shot Workers
For simpler worker nodes that process a single task and exit:
```bash
# In a container/VM, run one task and capture JSON output
opencode run \
  --format json \
  --model anthropic/claude-sonnet-4 \
  --agent build \
  "Implement the feature described in /tmp/task.md" \
  > /tmp/result.jsonl
```

---

## 10. Summary for Swarm Builder

| Requirement | OpenCode Support | Notes |
|-------------|-----------------|-------|
| **Headless mode** | ✅ Excellent | `opencode run`, `opencode serve`, `opencode acp` |
| **JSON output** | ✅ Yes | `--format json` emits NDJSON events |
| **Multiple providers** | ✅ 75+ providers | Anthropic, OpenAI, OpenRouter, Ollama, Google, etc. |
| **Local models** | ✅ Via Ollama | Or any OpenAI-compatible endpoint |
| **Model switching** | ✅ Per-command | `--model provider/model` or per-agent config |
| **Agent hierarchy** | ✅ Primary + Subagents | Built-in `task` tool for agent delegation |
| **Custom agents** | ✅ JSON or Markdown | Define in config or `.opencode/agents/` |
| **HTTP API** | ✅ OpenAPI 3.1 | Full REST API at `http://host:port` |
| **SDK** | ✅ JS/TS SDK | `@opencode-ai/sdk` with full type safety |
| **Event streaming** | ✅ SSE | `/global/event` endpoint |
| **Structured output** | ✅ JSON Schema | Via SDK or HTTP API |
| **Authentication** | ✅ Basic auth | `OPENCODE_SERVER_PASSWORD` |
| **CORS** | ✅ Configurable | `--cors` flag |
| **ACP protocol** | ✅ stdio JSON-RPC | For editor integration patterns |
| **Session management** | ✅ Full | Create, list, continue, fork, export, import |
| **Active maintenance** | ✅ Very active | Daily releases, 876+ contributors |

### ⚠️ Known Limitations for Swarm Use
1. **`run --attach` context bug** — `opencode run --attach http://...` may fail with "No context found for instance" in some versions. Use direct HTTP API or `opencode run` (standalone) instead.
2. **JSON output only emits completed tools** — `--format json` does not stream intermediate `pending` tool states; only final `completed` tool events.
3. **ACP stdio pollution** — In some versions, non-JSON logs may leak to stdout in ACP mode (fixed in recent releases, but verify with your version).
4. **Bun runtime dependency** — OpenCode uses Bun runtime internally. The npm package wraps this. Ensure Bun compatibility in your environment.

---

## Verified URLs & Resources

| Resource | URL |
|----------|-----|
| Active GitHub Repo | https://github.com/anomalyco/opencode |
| Official Website | https://opencode.ai |
| Docs Home | https://opencode.ai/docs/ |
| CLI Docs | https://opencode.ai/docs/cli/ |
| Server Docs | https://opencode.ai/docs/server/ |
| SDK Docs | https://opencode.ai/docs/sdk/ |
| Providers Docs | https://opencode.ai/docs/providers/ |
| Agents Docs | https://opencode.ai/docs/agents/ |
| Changelog | https://opencode.ai/changelog |
| NPM Package | https://www.npmjs.com/package/@opencode-ai/sdk |
| Config Schema | https://opencode.ai/config.json |
| Discord Community | https://opencode.ai/discord |
| Third-Party Swarm Plugin | https://github.com/zaxbysauce/opencode-swarm |
| ACP Protocol Overview | https://www.philschmid.de/acp-overview |
| JSON Event Cheatsheet | https://takopi.dev/reference/runners/opencode/stream-json-cheatsheet/ |

---

*Report generated from official documentation, GitHub repository, and verified third-party sources. All URLs and commands verified as of research date.*

path = 'tools/swarm/swarm_followup.py'
content = open(path, encoding='utf-8').read()
old = '''ALL_ENGINES = (
    "claude", "gemini", "opencode", "kilo", "copilot",
    "freebuff",
    "deepseek", "cerebras", "xai", "inception", "ollama_cloud",
)'''
new = '''ALL_ENGINES = (
    "claude", "gemini", "opencode", "kilo", "copilot", "agent", "kimi",
    "openclaude", "codex",
    "freebuff",
    "deepseek", "cerebras", "xai", "inception", "ollama_cloud", "ollama_local", "openrouter",
    "nous", "groq", "huggingface", "gemini_api", "github_models", "pollinations",
)'''
if old in content:
    content = content.replace(old, new)
    print('replaced')
else:
    print('old not found')
open(path, 'w', encoding='utf-8').write(content)

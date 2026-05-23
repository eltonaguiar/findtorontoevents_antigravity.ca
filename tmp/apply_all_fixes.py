import pathlib

def fix_api_consult():
    path = pathlib.Path('tools/swarm/api_consult.py')
    content = path.read_text(encoding='utf-8')
    old1 = '    content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""'
    new1 = '    choices = data.get("choices") or [{}]\n    content = choices[0].get("message", {}).get("content", "") or ""'
    old2 = '    content = (data.get("choices", [{}])[0].get("message", {}).get("content") or "")'
    new2 = '    choices = data.get("choices") or [{}]\n    content = (choices[0].get("message", {}).get("content") or "")'
    assert old1 in content, "old1 not found"
    assert old2 in content, "old2 not found"
    content = content.replace(old1, new1)
    content = content.replace(old2, new2)
    path.write_text(content, encoding='utf-8')
    print('fixed api_consult.py')

def fix_swarm_run():
    path = pathlib.Path('tools/swarm/swarm_run.py')
    content = path.read_text(encoding='utf-8')
    old = '            per_strict = bool(em.get("json_strict")) or fleet_json_strict'
    new = '            per_strict = em.get("json_strict") if "json_strict" in em else fleet_json_strict'
    assert old in content, "old not found"
    content = content.replace(old, new)
    path.write_text(content, encoding='utf-8')
    print('fixed swarm_run.py')

def fix_swarm_followup():
    path = pathlib.Path('tools/swarm/swarm_followup.py')
    content = path.read_text(encoding='utf-8')
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
    assert old in content, "old not found"
    content = content.replace(old, new)
    path.write_text(content, encoding='utf-8')
    print('fixed swarm_followup.py')

def fix_worker_runner():
    path = pathlib.Path('tools/swarm/worker_runner.py')
    content = path.read_text(encoding='utf-8')
    old = '''    print(str(out_path))
    return 0'''
    new = '''    # Clean up temporary session context files created for --from-session.
    if args.from_session:
        for suffix in ("_ctx.md",):
            tmp_ctx = SWARM_DIR / f"_session_{args.from_session[:8]}{suffix}"
            try:
                if tmp_ctx.exists():
                    tmp_ctx.unlink()
            except OSError:
                pass

    print(str(out_path))
    return 0'''
    assert old in content, "old not found"
    content = content.replace(old, new)
    path.write_text(content, encoding='utf-8')
    print('fixed worker_runner.py')

if __name__ == '__main__':
    fix_api_consult()
    fix_swarm_run()
    fix_swarm_followup()
    fix_worker_runner()
    print('all fixes applied')

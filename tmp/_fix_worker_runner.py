path = 'tools/swarm/worker_runner.py'
content = open(path, encoding='utf-8').read()
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
if old in content:
    content = content.replace(old, new)
    print('replaced')
else:
    print('old not found')
open(path, 'w', encoding='utf-8').write(content)

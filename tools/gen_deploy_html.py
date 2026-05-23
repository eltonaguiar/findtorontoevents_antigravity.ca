#!/usr/bin/env python3
"""Generate deploy_riseoftheclaw/riseoftheclaw.html from KIMI_RISEOFTHECLAW/index.html with path rewriting."""
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
src = (WORKSPACE / "KIMI_RISEOFTHECLAW" / "index.html").read_text(encoding="utf-8")

# Rewrite relative paths to absolute for the deployed site structure
src = src.replace('href="css/', 'href="/riseoftheclaw/css/')
src = src.replace('src="js/', 'src="/riseoftheclaw/js/')

out = WORKSPACE / "deploy_riseoftheclaw" / "riseoftheclaw.html"
out.write_text(src, encoding="utf-8")
print(f"Generated {out}")

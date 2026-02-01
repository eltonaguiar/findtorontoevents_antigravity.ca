#!/usr/bin/env python3
"""
Fix HTML file paths from /next/_next/ to /_next/
"""
import os
import re
from pathlib import Path

def fix_html_paths(file_path: str) -> None:
    """Replace /next/_next/ with /_next/ in HTML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace /next/_next/ with /_next/
    fixed = content.replace('/next/_next/', '/_next/')
    fixed = fixed.replace('/next/static/', '/_next/static/')
    
    if fixed != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print(f"Fixed paths in {file_path}")
        return True
    else:
        print(f"No changes needed in {file_path}")
        return False

if __name__ == "__main__":
    workspace_root = Path(__file__).parent.parent
    index_html = workspace_root / "index.html"
    
    if index_html.exists():
        fix_html_paths(str(index_html))
    else:
        print(f"ERROR: {index_html} not found!")

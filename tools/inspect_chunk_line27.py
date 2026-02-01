"""Inspect a2ac3a6616d60872.js at line 27, column 8788 for SyntaxError cause."""
import sys

path = "next/_next/static/chunks/a2ac3a6616d60872.js"
with open(path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

lines = content.split("\n")
n = len(lines)
print("Total lines:", n, file=sys.stderr)

if n < 27:
    print("File has fewer than 27 lines")
    sys.exit(1)

line27 = lines[26]  # 0-indexed
print("Line 27 length:", len(line27), file=sys.stderr)
col = 8788
if col > len(line27):
    print("Column 8788 is beyond line 27 length")
    sys.exit(1)

# Show context: 80 chars before and after col 8788 (1-based -> 0-based: 8787)
start = max(0, 8787 - 80)
end = min(len(line27), 8787 + 80)
snippet = line27[start:end]
# Escape for safe output
snippet_safe = snippet.encode("ascii", "replace").decode("ascii")
print("Around column 8788 (80 chars before/after):")
print(snippet_safe)
print()
char_at = line27[8787]
print("Character at 8788 (1-based):", repr(char_at))
# Check if there could be an unclosed template literal or similar before this point
before = line27[:8788]
backticks = before.count("`") - before.count("\\`")
print("Backticks before col 8788 (approx):", backticks)

#!/usr/bin/env python3
"""Fix the JavaScript corruption by removing the injected footer"""

import os
import shutil

# Path to the corrupted file
source_file = r'e:\findtorontoevents_antigravity.ca\next\_next\static\chunks\a2ac3a6616d60872.js'

# Read the file
with open(source_file, 'rb') as f:
    content = f.read()

print(f"Original file size: {len(content)} bytes")

# Find the corruption marker
corruption_marker = b'Antigravity Systems'
corruption_pos = content.find(corruption_marker)

if corruption_pos == -1:
    print("No corruption found - file is already clean!")
    exit(0)

print(f"Corruption found at position: {corruption_pos}")

# The corruption appears to be injected into the middle of the file
# We need to find where it starts and remove it
# Looking at the pattern, it seems like the footer is injected between valid code

# Let's find the pattern that indicates where the injection starts
# Based on the analysis, it looks like the corruption is after "Built for Toronto"
# and before the final }]);

# Find the start of the corruption by looking backwards from "Antigravity Systems"
# The corruption seems to start with "Built for Toronto"
start_marker = b'Built for Toronto'
start_pos = content.find(start_marker)

if start_pos == -1:
    # Try alternative markers
    start_pos = corruption_pos - 50  # Approximate

# Find the end of the corruption - it should be before the final }]);
end_marker = b'}]);'
final_term_pos = content.rfind(end_marker)

print(f"Final termination at: {final_term_pos}")
print(f"Corruption range: {start_pos} to {final_term_pos}")

# The clean file should be everything up to the corruption start,
# then skip to just before the final }]);
# But we need to be careful not to break the structure

# Let's try a different approach: find the last valid code before corruption
# and the first valid code after corruption, then join them

# For now, let's just show what needs to be removed
print(f"\nCorrupted section ({final_term_pos - start_pos} bytes):")
print(repr(content[start_pos:final_term_pos + len(end_marker)]))

# Create a backup
backup_file = source_file + '.corrupted_backup'
shutil.copy2(source_file, backup_file)
print(f"\nBackup created: {backup_file}")

# The safest fix is to remove everything from the corruption start to just before the final }]);
# and then add back the final }]);
clean_content = content[:start_pos] + end_marker

print(f"\nClean file would be {len(clean_content)} bytes")
print(f"Removing {len(content) - len(clean_content)} bytes")

# Write the clean file
with open(source_file, 'wb') as f:
    f.write(clean_content)

print(f"\nFile cleaned successfully!")

# Verify with node
import subprocess
result = subprocess.run(['node', '-c', source_file], capture_output=True, text=True)
if result.returncode == 0:
    print("✓ File is syntactically valid!")
else:
    print("✗ File still has syntax errors:")
    print(result.stderr)
    # Restore backup
    shutil.copy2(backup_file, source_file)
    print("Restored from backup")

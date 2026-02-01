#!/usr/bin/env python3
"""Analyze and fix the JavaScript corruption in a2ac3a6616d60872.js"""

import os
import sys

# Path to the corrupted file
file_path = r'e:\findtorontoevents_antigravity.ca\next\_next\static\chunks\a2ac3a6616d60872.js'

# Read the file
with open(file_path, 'rb') as f:
    content = f.read()

print(f"File size: {len(content)} bytes")

# Find the corruption trigger
corruption_marker = b'Antigravity Systems'
corruption_pos = content.find(corruption_marker)

if corruption_pos == -1:
    print("No corruption marker found!")
    sys.exit(1)

print(f"\nCorruption found at position: {corruption_pos}")
print(f"Context around corruption:")
print(repr(content[corruption_pos-100:corruption_pos+150]))

# Find the last valid }]); before the corruption
termination = b'}]);'
last_valid_term = content.rfind(termination, 0, corruption_pos)

print(f"\nLast valid termination before corruption: {last_valid_term}")
if last_valid_term != -1:
    print(f"Context: {repr(content[last_valid_term-50:last_valid_term+10])}")

# Find all }]); in the file
all_terms = []
idx = 0
while True:
    idx = content.find(termination, idx)
    if idx == -1:
        break
    all_terms.append(idx)
    idx += len(termination)

print(f"\nTotal }}]); occurrences: {len(all_terms)}")
for i, pos in enumerate(all_terms):
    print(f"  {i+1}. Position {pos}")

# Check if we can truncate at the last valid termination
if last_valid_term != -1:
    clean_content = content[:last_valid_term + len(termination)]
    print(f"\nClean file would be {len(clean_content)} bytes")
    print(f"Would remove {len(content) - len(clean_content)} bytes")
    
    # Show what would be removed
    print(f"\nRemoved content:")
    print(repr(content[last_valid_term + len(termination):]))

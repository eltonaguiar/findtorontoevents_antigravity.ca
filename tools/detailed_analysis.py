#!/usr/bin/env python3
"""Detailed analysis of the corruption pattern"""

file_path = r'e:\findtorontoevents_antigravity.ca\next\_next\static\chunks\a2ac3a6616d60872.js'

with open(file_path, 'rb') as f:
    content = f.read()

print(f"File size: {len(content)} bytes\n")

# Find key markers
markers = {
    'Antigravity Systems': content.find(b'Antigravity Systems'),
    'Built for Toronto': content.find(b'Built for Toronto'),
    '}]);': content.rfind(b'}]);'),
    'v0.5.0': content.find(b'v0.5.0'),
}

for name, pos in markers.items():
    if pos != -1:
        print(f"{name}: position {pos}")
        print(f"  Context: {repr(content[max(0, pos-30):pos+50])}\n")

# Show the last 500 bytes
print("\n=== LAST 500 BYTES ===")
print(repr(content[-500:]))

# Show around position 35712 (where corruption was found)
print("\n=== AROUND CORRUPTION (35700-35900) ===")
print(repr(content[35700:35900]))

# Show around the final }]); 
final_pos = content.rfind(b'}]);')
print(f"\n=== AROUND FINAL TERMINATION ({final_pos-100} to {final_pos+20}) ===")
print(repr(content[final_pos-100:final_pos+20]))

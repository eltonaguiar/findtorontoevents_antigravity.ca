#!/usr/bin/env python3
"""Inspect nav chunk for exact patterns."""
import sys
path = "next/_next/static/chunks/a2ac3a6616d60872.js"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
for label, s in [
    ("details NETWORK", '(0,t.jsxs)("details",{className:"group/nav-section"'),
    ("Toronto Events link", 'href:"/",className:"w-full text-left'),
    ("WINDOWSFIXER", 'href:"/WINDOWSFIXER/"'),
    ("findstocks", 'href:"/findstocks"'),
    ("MOVIESHOWS", 'href:"/MOVIESHOWS/"'),
    ("fc/#/guest", 'href:"/fc/#/guest"'),
    ("Data Management", "Data Management"),
    ("Contact Support", "Contact Support"),
]:
    i = c.find(s)
    if i >= 0:
        print(label, ":", repr(c[i : i + 200]))
    else:
        print(label, "NOT FOUND")
# Data Management section: find div that contains "Data Management" - get 300 chars before
i = c.find('"Data Management"}),(0,t.jsxs)("div",{className:"px-4 py-2 grid')
if i >= 0:
    start = max(0, i - 300)
    print("DATA MGMT SECTION START:", repr(c[start:i+80]))

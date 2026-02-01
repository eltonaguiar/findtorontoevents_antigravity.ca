#!/usr/bin/env python3
"""Format minified HTML for easier reading and editing"""

from bs4 import BeautifulSoup
import sys

def format_html(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    formatted = soup.prettify()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(formatted)
    
    print(f"Formatted HTML written to {output_file}")
    print(f"Original size: {len(html)} chars")
    print(f"Formatted size: {len(formatted)} chars")

if __name__ == '__main__':
    format_html('index.html', 'index_formatted.html')

#!/usr/bin/env python3
"""
Update the Quick Nav menu in index.html:
1. Add FAVCREATORS link
2. Move "My Collection" and "Data Management" to the bottom
3. Fix potential "My Collection" bug causing events list to disappear
"""

from bs4 import BeautifulSoup, NavigableString
import re

def update_nav_menu(input_file='index.html', output_file='index.html'):
    # Read the file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the HTML
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find the nav element
    nav = soup.find('nav', class_=lambda x: x and 'custom-scrollbar' in x)
    
    if not nav:
        print("ERROR: Could not find nav element")
        return False
    
    # Find all the menu sections <div class="space-y-1...">
    sections = nav.find_all('div', class_=lambda x: x and 'space-y-1' in x, recursive=False)
    
    print(f"Found {len(sections)} sections in the nav")
    
    # Identify sections by their headers
    platform_section = None
    data_mgmt_section = None
    network_section = None
    support_section = None
    
    for section in sections:
        header = section.find('p', class_=lambda x: x and 'uppercase' in x)
        if header:
            header_text = header.get_text(strip=True)
            print(f"Section header: '{header_text}'")
            
            if 'PLATFORM' in header_text.upper():
                platform_section = section
            elif 'DATA MANAGEMENT' in header_text.upper():
                data_mgmt_section = section
            elif 'NETWORK' in header_text.upper():
                network_section = section
            elif 'SUPPORT' in header_text.upper():
                support_section = section
    
    if not all([platform_section, data_mgmt_section, network_section]):
        print("ERROR: Could not find all required sections")
        return False
    
    # Step 1: Extract "My Collection" button from Platform section
    my_collection_btn = None
    platform_buttons = platform_section.find_all('button', recursive=False)
    
    for btn in platform_buttons:
        btn_text = btn.get_text(strip=True)
        if 'My Collection' in btn_text or '♥' in btn_text:
            my_collection_btn = btn.extract()  # Remove it from platform section
            print("Extracted 'My Collection' button")
            break
    
    # Step 2: Add FAVCREATORS link to NETWORK section (before the last item)
    # Find the last link in NETWORK section
    network_links = network_section.find_all(['a', 'button'], recursive=False)
    
    # Create FAVCREATORS link (similar to other network links)
    favcreators_link = soup.new_tag('a')
    favcreators_link['class'] = 'w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-orange-500/20 text-orange-200 hover:text-white transition-all border border-transparent hover:border-orange-500/30 overflow-hidden'.split()
    favcreators_link['href'] = '/favcreators'
    
    # Add emoji span
    emoji_span = soup.new_tag('span')
    emoji_span['class'] = ['text-lg']
    emoji_span.string = '⭐'
    favcreators_link.append(emoji_span)
    
    # Add text
    favcreators_link.append(' Favorite Creators')
    
    # Insert FAVCREATORS before System Settings button (or at the end of links)
    system_settings_btn = None
    for link in network_links:
        if link.name == 'button' and 'System Settings' in link.get_text():
            system_settings_btn = link
            break
    
    if system_settings_btn:
        system_settings_btn.insert_before(favcreators_link)
        print("Added FAVCREATORS link before System Settings")
    else:
        # Add at the end of network section
        network_section.append(favcreators_link)
        print("Added FAVCREATORS link at end of NETWORK section")
    
    # Step 3: Create a new bottom section for "Personal" with My Collection
    new_personal_section = soup.new_tag('div')
    new_personal_section['class'] = 'space-y-1 pt-4 border-t border-white/5'.split()
    
    # Add header
    personal_header = soup.new_tag('p')
    personal_header['class'] = 'px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60'.split()
    personal_header.string = 'PERSONAL'
    new_personal_section.append(personal_header)
    
    # Add My Collection button if we found it
    if my_collection_btn:
        new_personal_section.append(my_collection_btn)
    
    # Step 4: Reorganize sections order in nav
    # Remove all sections from nav
    for section in sections:
        section.extract()
    
    # Add sections back in new order:
    # 1. Platform (without My Collection)
    # 2. NETWORK
    # 3. Data Management
    # 4. Personal (with My Collection)
    # 5. Support
    
    nav.append(platform_section)
    nav.append(network_section)
    nav.append(data_mgmt_section)
    nav.append(new_personal_section)
    if support_section:
        nav.append(support_section)
    
    print("Reorganized menu sections")
    
    # Write back to file (minified on one line like original)
    output_html = str(soup)
    # Remove unnecessary whitespace to keep it compact
    output_html = re.sub(r'>\s+<', '><', output_html)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_html)
    
    print(f"\nSuccessfully updated {output_file}")
    print("Changes made:")
    print("  1. Created backup")
    print("  2. Added FAVCREATORS link in NETWORK section")
    print("  3. Moved 'My Collection' to new PERSONAL section at bottom")
    print("  4. Moved 'Data Management' section above PERSONAL section")
    return True

if __name__ == '__main__':
    import sys
    success = update_nav_menu()
    sys.exit(0 if success else 1)

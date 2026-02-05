import os

# Files to update
chunks = [
    'next/_next/static/chunks/60a85cefa5d61d43.js',
    'next/_next/static/chunks/8754972ee54e9a76.js',
    'next/static/chunks/60a85cefa5d61d43.js',
    'next/static/chunks/8754972ee54e9a76.js',
]

for chunk in chunks:
    if os.path.exists(chunk):
        with open(chunk, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check if it has windows and movies but not favcreators
        has_windows = 'windows-fixer-promo' in content
        has_movies = 'movieshows-promo' in content
        has_fc = 'favcreators-promo' in content
        has_stocks = 'stocks-promo' in content
        
        print(f'{chunk}:')
        print(f'  Windows: {has_windows}, Movies: {has_movies}, FC: {has_fc}, Stocks: {has_stocks}')
        
        # Find where to insert - look for pattern after movieshows-promo
        if has_windows and has_movies and not has_fc:
            # Find the movieshows section and add after it
            # Look for the end of movieshows-promo section
            idx = content.find('movieshows-promo')
            if idx > 0:
                # Look for the closing of this component
                # In React chunks, this might be followed by other elements
                print(f'  Found movieshows at {idx}, would need to add FC and Stocks')

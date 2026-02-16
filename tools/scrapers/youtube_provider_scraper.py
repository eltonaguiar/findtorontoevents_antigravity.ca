#!/usr/bin/env python3
"""
YouTube Trailer Description Scraper for Streaming Providers

Scrapes YouTube trailer descriptions to find streaming platform mentions
and updates the MOVIESHOWS3 database with provider information.

Example: "Available Now on Amazon Prime Video" → tags movie with Prime Video
"""

import os
import re
import sys
import time
import json
import urllib.request
import urllib.parse
import mysql.connector
from datetime import datetime

# Streaming provider patterns (case-insensitive)
PROVIDER_PATTERNS = {
    '8': {  # Netflix
        'name': 'Netflix',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*netflix',
            r'netflix\s+(?:original|exclusive)',
            r'only on netflix',
            r'netflix\.com'
        ]
    },
    '9': {  # Prime Video
        'name': 'Prime Video',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*(?:amazon\s*)?prime\s*video',
            r'prime\s*video\s+(?:original|exclusive)',
            r'only on prime',
            r'primevideo\.com'
        ]
    },
    '337': {  # Disney+
        'name': 'Disney+',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*disney\s*\+',
            r'disney\s*\+\s+(?:original|exclusive)',
            r'only on disney\+',
            r'disneyplus\.com'
        ]
    },
    '15': {  # Hulu
        'name': 'Hulu',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*hulu',
            r'hulu\s+(?:original|exclusive)',
            r'only on hulu',
            r'hulu\.com'
        ]
    },
    '350': {  # Apple TV+
        'name': 'Apple TV+',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*apple\s*tv\s*\+',
            r'apple\s*tv\s*\+\s+(?:original|exclusive)',
            r'only on apple tv\+',
            r'tv\.apple\.com'
        ]
    },
    '1899': {  # Max (HBO Max)
        'name': 'Max',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*(?:hbo\s*)?max',
            r'(?:hbo\s*)?max\s+(?:original|exclusive)',
            r'only on max',
            r'max\.com'
        ]
    },
    '531': {  # Paramount+
        'name': 'Paramount+',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*paramount\s*\+',
            r'paramount\s*\+\s+(?:original|exclusive)',
            r'only on paramount\+',
            r'paramountplus\.com'
        ]
    },
    '230': {  # Crave
        'name': 'Crave',
        'patterns': [
            r'(?:available|streaming|watch|now).*?(?:on|@)\s*crave',
            r'crave\s+(?:original|exclusive)',
            r'only on crave',
            r'crave\.ca'
        ]
    }
}

def get_youtube_video_info(video_id, api_key):
    """Fetch video details from YouTube Data API"""
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'items' in data and len(data['items']) > 0:
                return data['items'][0]['snippet']
    except Exception as e:
        print(f"  Error fetching YouTube data: {e}")

    return None

def extract_providers_from_description(description):
    """Parse description text for streaming provider mentions"""
    if not description:
        return []

    description_lower = description.lower()
    found_providers = []

    for provider_id, provider_data in PROVIDER_PATTERNS.items():
        for pattern in provider_data['patterns']:
            if re.search(pattern, description_lower, re.IGNORECASE):
                found_providers.append({
                    'id': provider_id,
                    'name': provider_data['name'],
                    'logo': get_provider_logo(provider_id)
                })
                break  # Only add each provider once

    return found_providers

def get_provider_logo(provider_id):
    """Get TMDB logo URL for provider"""
    logos = {
        '8': 'https://image.tmdb.org/t/p/original/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg',
        '9': 'https://image.tmdb.org/t/p/original/emthp39XA2YScoYL1p0sdbAH2WA.jpg',
        '337': 'https://image.tmdb.org/t/p/original/7rwgEs15tFwyR9NPQ5vpzxTj19Q.jpg',
        '15': 'https://image.tmdb.org/t/p/original/zxrVdFjIjLqkfnwyghnfywTn3Lh.jpg',
        '350': 'https://image.tmdb.org/t/p/original/2E03IAZsX4ZaUqM7tXlctEPMGWS.jpg',
        '1899': 'https://image.tmdb.org/t/p/original/Ajqyt5aNxNGjmF9uOfxArGrdf3X.jpg',
        '531': 'https://image.tmdb.org/t/p/original/xbhHHa1YgtpwhC8lb1NQ3ACVcLd.jpg',
        '230': 'https://image.tmdb.org/t/p/original/pGhEL21HqPycD4gWV8DQ1fKD9HG.jpg'
    }
    return logos.get(provider_id, '')

def get_db_connection():
    """Connect to MOVIESHOWS3 database"""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'ejaguiar1_tvmoviestrailers'),
        password=os.getenv('DB_PASS', 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD'),
        database=os.getenv('DB_NAME', 'ejaguiar1_tvmoviestrailers')
    )

def update_movie_providers(db, movie_id, providers, source='youtube_description'):
    """Insert/update streaming providers for a movie"""
    cursor = db.cursor()

    for provider in providers:
        try:
            # Determine priority based on provider ID
            priority = int(provider['id']) if provider['id'].isdigit() else 99

            sql = """
                INSERT INTO streaming_providers
                    (movie_id, provider_id, provider_name, provider_logo, display_priority, is_active)
                VALUES
                    (%s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    provider_name = VALUES(provider_name),
                    provider_logo = VALUES(provider_logo),
                    is_active = 1,
                    last_checked = NOW()
            """

            cursor.execute(sql, (
                movie_id,
                provider['id'],
                provider['name'],
                provider['logo'],
                priority
            ))

            # Log to history
            history_sql = """
                INSERT INTO streaming_provider_history
                    (movie_id, provider_id, provider_name, action)
                VALUES (%s, %s, %s, 'added')
            """
            cursor.execute(history_sql, (movie_id, provider['id'], provider['name']))

        except Exception as e:
            print(f"    Error inserting provider {provider['name']}: {e}")

    db.commit()
    cursor.close()

def scrape_youtube_providers(limit=100, offset=0):
    """Main scraper function"""
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')
    if not youtube_api_key:
        print("ERROR: YOUTUBE_API_KEY environment variable not set")
        return

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get movies with YouTube trailer IDs
    sql = """
        SELECT m.id, m.title, t.youtube_id
        FROM movies m
        INNER JOIN trailers t ON m.id = t.movie_id
        WHERE t.youtube_id IS NOT NULL AND t.youtube_id != ''
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
    """

    cursor.execute(sql, (limit, offset))
    movies = cursor.fetchall()

    print(f"\nProcessing {len(movies)} movies (offset {offset})...")
    print("=" * 60)

    processed = 0
    found = 0

    for movie in movies:
        print(f"\n[{movie['id']}] {movie['title']}")
        print(f"  YouTube: {movie['youtube_id']}")

        # Fetch video info from YouTube
        video_info = get_youtube_video_info(movie['youtube_id'], youtube_api_key)

        if not video_info:
            print("  ⚠️  Failed to fetch video info")
            continue

        description = video_info.get('description', '')
        title = video_info.get('title', '')

        # Combine title and description for better detection
        combined_text = f"{title}\n\n{description}"

        if not combined_text.strip():
            print("  ℹ️  No title/description")
            processed += 1
            time.sleep(0.1)  # Rate limiting
            continue

        # Extract providers from combined text
        providers = extract_providers_from_description(combined_text)

        if providers:
            provider_names = ', '.join([p['name'] for p in providers])
            print(f"  ✅ Found: {provider_names}")

            # Update database
            update_movie_providers(db, movie['id'], providers)
            found += 1
        else:
            print("  ℹ️  No providers mentioned")

        processed += 1

        # Rate limiting: YouTube API has quota limits
        time.sleep(0.5)

    cursor.close()
    db.close()

    print("\n" + "=" * 60)
    print(f"SUMMARY: {found} movies tagged with providers (out of {processed} processed)")
    print(f"Next batch: offset={offset + limit}")

if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    scrape_youtube_providers(limit, offset)

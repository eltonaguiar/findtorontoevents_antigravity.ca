#!/usr/bin/env python3
"""
Taste Profile Scanner - Extracts music taste from YouTube playlists
Works headlessly (CLI, GitHub Actions, cron jobs) using yt-dlp.

Usage:
    python tools/taste_profile_scanner.py --youtube @tobedeleted2030
    python tools/taste_profile_scanner.py --youtube "https://www.youtube.com/@tobedeleted2030/playlists"
    python tools/taste_profile_scanner.py --youtube @tobedeleted2030 --output taste_data.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

# --- Artist name parsing ---

# Common noise words in YouTube video titles that are NOT artist names
NOISE_WORDS = {
    'official', 'music', 'video', 'audio', 'lyric', 'lyrics', 'hd', 'hq',
    'explicit', 'visualizer', 'remix', 'cover', 'live', 'acoustic', 'remastered',
    'slowed', 'reverb', 'bass', 'boosted', 'nightcore', 'extended', 'version',
    'feat', 'ft', 'featuring', 'prod', 'dir', 'topic', 'vevo',
}

# Channels that are NOT artists (aggregator/compilation channels)
AGGREGATOR_CHANNELS = {
    'montagerock', 'mrmommusic', 'cloudkid', 'proximity', 'newretrowave',
    'airwavemusictv', 'wavemusic', 'futurehype', 'pillow', 'curserlyrics',
    'spaceuntravel', 'littlenerd', 'supremesounds', 'syrex', 'motiversity',
    'medleyjourney', 'extraordinarydubstep', 'lwbmusic', 'krosismisc',
    'euphorify', 'vibesonly', 'musicnightcorecopyright', 'djkhaotic',
    'sayhey96', 'zanovo.', 'madwwegirl', 'sgmusic-partymix2021',
    'magicmusic', 'daveepa', 'valentinosirolli', 'mashupmixes',
    'tenhoursvideos', 'progressivepleasure', 'yuribarozzi', 'djekkimusic',
    'djsfommars', 'nightcorereality', 'aero.', 'fixtneon',
    'disclosbeauty', 'unfd', 'sumerian', 'nightcore',
}


def clean_channel_name(channel):
    """Remove ' - Topic' suffix and other noise from channel names."""
    if not channel:
        return None
    channel = re.sub(r'\s*-\s*Topic$', '', channel, flags=re.IGNORECASE)
    channel = channel.strip()
    if channel.lower().replace(' ', '') in AGGREGATOR_CHANNELS:
        return None
    return channel


def extract_artist_from_title(title):
    """
    Parse artist name from video title.
    Common formats:
        "Artist - Song Title"
        "Artist - Song (feat. Other)"
        "Artist ft. Other - Song"
    """
    if not title:
        return None

    # Skip deleted/private
    if title.startswith('[Deleted') or title.startswith('[Private'):
        return None

    # Skip long mixes/compilations (usually not by a single artist)
    mix_keywords = ['party mix', 'megamix', 'best remixes', 'best of', 
                    'edm mix', 'club music mix', '10 hours', 'mashup mix',
                    'best club', 'charts music']
    title_lower = title.lower()
    for kw in mix_keywords:
        if kw in title_lower:
            return None

    # Try "Artist - Song" pattern (most common)
    dash_match = re.match(r'^([^-–—]+?)\s*[-–—]\s*(.+)$', title)
    if dash_match:
        artist = dash_match.group(1).strip()
        # Remove feat/ft from artist part
        artist = re.split(r'\s+(?:feat\.?|ft\.?|featuring)\s+', artist, flags=re.IGNORECASE)[0].strip()
        # Clean parenthetical noise
        artist = re.sub(r'\s*\([^)]*\)\s*', '', artist).strip()
        if artist and len(artist) > 1:
            return artist

    return None


def run_ytdlp(url, extra_args=None):
    """Run yt-dlp with --flat-playlist --dump-json and return parsed entries."""
    cmd = [sys.executable, '-m', 'yt_dlp', '--flat-playlist', '--dump-json']
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        entries = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {url}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [ERROR] {url}: {e}", file=sys.stderr)
        return []


def scan_youtube_channel(channel_url):
    """
    Scan a YouTube channel's playlists and extract taste profile.
    Returns structured data with playlists, artists, genres.
    """
    # Normalize URL
    if channel_url.startswith('@'):
        channel_url = f"https://www.youtube.com/{channel_url}/playlists"
    elif '/playlists' not in channel_url:
        channel_url = channel_url.rstrip('/') + '/playlists'

    print(f"[1/3] Fetching playlists from {channel_url}...")
    playlists_raw = run_ytdlp(channel_url)

    if not playlists_raw:
        print("  No playlists found.", file=sys.stderr)
        return None

    channel_name = playlists_raw[0].get('playlist_uploader', 'Unknown')
    channel_id = playlists_raw[0].get('playlist_uploader_id', '')

    playlists = []
    for p in playlists_raw:
        playlists.append({
            'title': p.get('title', ''),
            'id': p.get('id', ''),
            'url': p.get('url', ''),
            'thumbnail': p['thumbnails'][0]['url'] if p.get('thumbnails') else None,
        })

    print(f"  Found {len(playlists)} playlists for '{channel_name}'")

    # Phase 2: Scan each playlist for videos
    print(f"[2/3] Scanning playlist contents...")
    all_artists = Counter()
    all_channels = Counter()
    genre_playlists = {}
    playlist_details = []
    total_tracks = 0

    for i, pl in enumerate(playlists):
        print(f"  [{i+1}/{len(playlists)}] {pl['title']}...", end=' ')
        videos = run_ytdlp(pl['url'])
        print(f"{len(videos)} tracks")

        track_list = []
        playlist_artists = Counter()

        for v in videos:
            title = v.get('title', '')
            channel = v.get('channel') or v.get('uploader', '')
            vid_id = v.get('id', '')
            duration = v.get('duration')

            # Skip deleted/private
            if title.startswith('[Deleted') or title.startswith('[Private'):
                continue

            # Extract artist: prefer title parsing, fall back to channel
            artist = extract_artist_from_title(title)
            clean_ch = clean_channel_name(channel)

            # If no artist from title, use channel (if it's not an aggregator)
            if not artist and clean_ch:
                artist = clean_ch

            if artist:
                all_artists[artist] += 1
                playlist_artists[artist] += 1

            if clean_ch:
                all_channels[clean_ch] += 1

            track_list.append({
                'title': title,
                'artist': artist,
                'channel': channel,
                'video_id': vid_id,
                'duration': duration,
            })
            total_tracks += 1

        playlist_details.append({
            'title': pl['title'],
            'id': pl['id'],
            'url': pl['url'],
            'thumbnail': pl.get('thumbnail'),
            'track_count': len(track_list),
            'top_artists': [{'name': a, 'count': c} for a, c in playlist_artists.most_common(10)],
            'tracks': track_list,
        })

        genre_playlists[pl['title']] = [a for a, _ in playlist_artists.most_common(5)]

    # Phase 3: Build taste profile
    print(f"[3/3] Building taste profile...")

    # Merge similar artist names (case-insensitive dedup)
    merged_artists = Counter()
    name_map = {}  # lowercase -> preferred casing
    for artist, count in all_artists.items():
        key = artist.lower().strip()
        if key in name_map:
            merged_artists[name_map[key]] += count
        else:
            name_map[key] = artist
            merged_artists[artist] = count

    # Classify genres from playlist names
    genre_keywords = {
        'emo': ['emo'],
        'rock': ['rock', 'metal', 'rockmetal'],
        'rap': ['rap', 'gangsta', 'hardcore rap'],
        'country': ['country'],
        'reggae': ['reggae'],
        'edm': ['edm', 'party mix', 'club'],
        'sad': ['sad', 'emo times'],
        'workout': ['workout', 'pumpup'],
        'sleep': ['sleep', 'bed'],
        'happy': ['happy', 'happymix'],
        'motivation': ['motivation'],
        'love': ['love', 'findinglove'],
    }

    detected_genres = defaultdict(int)
    for pl in playlist_details:
        pl_lower = pl['title'].lower()
        for genre, keywords in genre_keywords.items():
            for kw in keywords:
                if kw in pl_lower:
                    detected_genres[genre] += pl['track_count']
                    break

    taste_profile = {
        'source': 'youtube',
        'channel': {
            'name': channel_name,
            'id': channel_id,
            'url': channel_url,
        },
        'summary': {
            'total_playlists': len(playlists),
            'total_tracks': total_tracks,
            'unique_artists': len(merged_artists),
        },
        'top_artists': [
            {'name': a, 'count': c, 'rank': i+1}
            for i, (a, c) in enumerate(merged_artists.most_common(50))
        ],
        'top_channels': [
            {'name': a, 'count': c}
            for a, c in all_channels.most_common(30)
        ],
        'genres': [
            {'name': g, 'track_count': c}
            for g, c in sorted(detected_genres.items(), key=lambda x: -x[1])
        ],
        'genre_playlists': genre_playlists,
        'playlists': playlist_details,
    }

    return taste_profile


def main():
    parser = argparse.ArgumentParser(description='Taste Profile Scanner')
    parser.add_argument('--youtube', '-y', help='YouTube channel URL or handle (e.g., @tobedeleted2030)')
    parser.add_argument('--output', '-o', default='taste_profile.json', help='Output JSON file')
    parser.add_argument('--summary', action='store_true', help='Print summary to stdout')
    args = parser.parse_args()

    if not args.youtube:
        parser.print_help()
        sys.exit(1)

    profile = scan_youtube_channel(args.youtube)

    if not profile:
        print("Failed to scan channel.", file=sys.stderr)
        sys.exit(1)

    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"\nSaved taste profile to {args.output}")

    # Print summary (handle unicode safely on Windows)
    def safe_print(text):
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('ascii', errors='replace').decode('ascii'))

    safe_print(f"\n{'='*60}")
    safe_print(f"  TASTE PROFILE: {profile['channel']['name']}")
    safe_print(f"{'='*60}")
    safe_print(f"  Playlists: {profile['summary']['total_playlists']}")
    safe_print(f"  Total tracks: {profile['summary']['total_tracks']}")
    safe_print(f"  Unique artists: {profile['summary']['unique_artists']}")
    safe_print(f"\n  TOP 20 ARTISTS:")
    for a in profile['top_artists'][:20]:
        bar = '#' * min(a['count'], 30)
        name = a['name'][:28]
        safe_print(f"    {a['rank']:2d}. {name:<30s} {bar} ({a['count']})")
    safe_print(f"\n  GENRE BREAKDOWN:")
    for g in profile['genres']:
        bar = '#' * min(g['track_count'] // 2, 30)
        safe_print(f"    {g['name']:<15s} {bar} ({g['track_count']} tracks)")
    safe_print(f"{'='*60}")


if __name__ == '__main__':
    main()

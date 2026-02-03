# Alternative Trailer Support

## Database Design

The `trailers` table is already designed to support **multiple trailers per movie** with automatic failover:

```sql
CREATE TABLE trailers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    youtube_id VARCHAR(20) NOT NULL,
    title VARCHAR(255),
    priority INT DEFAULT 5,           -- Higher = preferred
    source VARCHAR(50),                -- 'tmdb', 'youtube', 'manual'
    is_active BOOLEAN DEFAULT TRUE,
    view_count INT DEFAULT 0,
    last_played_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    INDEX idx_movie_priority (movie_id, priority DESC, is_active)
);
```

## Key Features

### 1. Priority-Based Failover
- Trailers are ordered by `priority` (DESC)
- Higher priority = preferred trailer
- Automatic fallback to next trailer on error

### 2. Multiple Sources
- **TMDB**: Official trailers from The Movie Database
- **YouTube**: Discovered via YouTube API search
- **Manual**: User-added alternative trailers

### 3. Active/Inactive Status
- `is_active` flag to disable broken trailers
- Failed trailers can be marked inactive automatically

### 4. Analytics
- `view_count`: Track how many times trailer was played
- `last_played_at`: Track last play time
- Helps identify best-performing trailers

## API Endpoints

### Get All Trailers for a Movie
```bash
GET /api/trailers.php?movie_id=123
```

Response:
```json
{
  "trailers": [
    {
      "id": 1,
      "youtube_id": "abc123",
      "title": "Official Trailer",
      "priority": 10,
      "source": "tmdb",
      "is_active": true,
      "view_count": 150
    },
    {
      "id": 2,
      "youtube_id": "xyz789",
      "title": "Teaser Trailer",
      "priority": 8,
      "source": "youtube",
      "is_active": true,
      "view_count": 75
    }
  ]
}
```

### Add Alternative Trailer
```bash
POST /api/trailers.php
Content-Type: application/json

{
  "movie_id": 123,
  "youtube_id": "new456",
  "title": "Alternative Trailer",
  "priority": 7,
  "source": "manual"
}
```

### Update Trailer Priority
```bash
PUT /api/trailers.php?id=2
Content-Type: application/json

{
  "priority": 9
}
```

### Mark Trailer as Inactive
```bash
PUT /api/trailers.php?id=2
Content-Type: application/json

{
  "is_active": false
}
```

### Delete Trailer
```bash
DELETE /api/trailers.php?id=2
```

## Frontend Usage

### Automatic Failover
```javascript
// Get trailers ordered by priority
const trailers = movie.trailers; // Already sorted by priority DESC

// Try playing first trailer
let currentTrailerIndex = 0;

function playTrailer() {
  const trailer = trailers[currentTrailerIndex];
  const player = new YT.Player('player', {
    videoId: trailer.youtube_id,
    events: {
      onError: (event) => {
        // Trailer failed, try next one
        currentTrailerIndex++;
        if (currentTrailerIndex < trailers.length) {
          console.log('Trying alternative trailer...');
          playTrailer();
        } else {
          console.error('All trailers failed');
        }
      }
    }
  });
}
```

### Manual Trailer Selection
```javascript
// Show "Try Alternative Trailer" button
<button onClick={() => {
  currentTrailerIndex++;
  if (currentTrailerIndex < trailers.length) {
    playTrailer();
  }
}}>
  Try Alternative Trailer ({currentTrailerIndex + 1}/{trailers.length})
</button>
```

## Bulk Population

The bulk population script automatically adds **up to 3 trailers per movie**:

```javascript
// From bulk-populate-content.js
if (details.videos && details.videos.results) {
  const youtubeTrailers = details.videos.results
    .filter(v => v.site === 'YouTube' && (v.type === 'Trailer' || v.type === 'Teaser'))
    .slice(0, 3); // Get top 3 trailers
  
  youtubeTrailers.forEach((trailer, index) => {
    trailers.push({
      youtube_id: trailer.key,
      title: trailer.name,
      priority: 10 - index, // First trailer = priority 10, second = 9, etc.
      source: 'tmdb',
      view_count: 0
    });
  });
}
```

## Example: Movie with Multiple Trailers

```json
{
  "id": 123,
  "title": "The Batman",
  "trailers": [
    {
      "id": 1,
      "youtube_id": "mqqft2x_Aa4",
      "title": "The Batman - Official Trailer",
      "priority": 10,
      "source": "tmdb",
      "is_active": true
    },
    {
      "id": 2,
      "youtube_id": "u34gHaRiBIU",
      "title": "The Batman - Teaser Trailer",
      "priority": 9,
      "source": "tmdb",
      "is_active": true
    },
    {
      "id": 3,
      "youtube_id": "alternative123",
      "title": "Alternative Fan Trailer",
      "priority": 5,
      "source": "manual",
      "is_active": true
    }
  ]
}
```

## Summary

✅ **Already Implemented:**
- Database schema supports unlimited trailers per movie
- Priority-based ordering
- Active/inactive status
- Multiple sources (TMDB, YouTube, manual)
- Full CRUD API endpoints
- Bulk population adds 3 trailers per movie

✅ **Ready to Use:**
- Automatic failover logic
- Manual trailer selection
- Analytics tracking
- Source attribution

No additional database changes needed - the system is already designed for comprehensive alternative trailer support!

/**
 * UPDATE #97: TV Show Support
 * Extend platform to support TV shows
 */

interface TVShow {
    id: number;
    title: string;
    type: 'tv';
    firstAirDate?: string;
    lastAirDate?: string;
    seasons?: number;
    episodes?: number;
    status?: 'returning' | 'ended' | 'canceled';
    genre?: string;
    description?: string;
    thumbnail?: string;
    rating?: number;
    network?: string;
}

interface Season {
    id: number;
    showId: number;
    seasonNumber: number;
    episodeCount: number;
    airDate?: string;
    overview?: string;
    poster?: string;
}

interface Episode {
    id: number;
    seasonId: number;
    episodeNumber: number;
    title: string;
    airDate?: string;
    runtime?: number;
    overview?: string;
    stillPath?: string;
}

/**
 * TV Show Card Component
 */
import React from 'react';

interface TVShowCardProps {
    show: TVShow;
    onClick?: () => void;
}

export function TVShowCard({ show, onClick }: TVShowCardProps) {
    return (
        <div className="tv-show-card" onClick={onClick}>
            <div className="show-thumbnail">
                <img src={show.thumbnail || '/placeholder-tv.jpg'} alt={show.title} />
                {show.status && (
                    <span className={`status-badge status-${show.status}`}>
                        {show.status}
                    </span>
                )}
            </div>

            <div className="show-info">
                <h3>{show.title}</h3>

                <div className="show-meta">
                    {show.firstAirDate && (
                        <span>{new Date(show.firstAirDate).getFullYear()}</span>
                    )}
                    {show.seasons && <span>{show.seasons} Seasons</span>}
                    {show.network && <span>{show.network}</span>}
                </div>

                {show.rating && (
                    <div className="show-rating">
                        ⭐ {show.rating.toFixed(1)}
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * Season List Component
 */
interface SeasonListProps {
    seasons: Season[];
    onSelectSeason: (season: Season) => void;
}

export function SeasonList({ seasons, onSelectSeason }: SeasonListProps) {
    return (
        <div className="season-list">
            <h3>Seasons</h3>
            <div className="seasons-grid">
                {seasons.map(season => (
                    <div
                        key={season.id}
                        className="season-card"
                        onClick={() => onSelectSeason(season)}
                    >
                        {season.poster && (
                            <img src={season.poster} alt={`Season ${season.seasonNumber}`} />
                        )}
                        <div className="season-info">
                            <h4>Season {season.seasonNumber}</h4>
                            <p>{season.episodeCount} Episodes</p>
                            {season.airDate && (
                                <span className="air-date">
                                    {new Date(season.airDate).getFullYear()}
                                </span>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Episode List Component
 */
interface EpisodeListProps {
    episodes: Episode[];
    onSelectEpisode: (episode: Episode) => void;
}

export function EpisodeList({ episodes, onSelectEpisode }: EpisodeListProps) {
    return (
        <div className="episode-list">
            {episodes.map(episode => (
                <div
                    key={episode.id}
                    className="episode-item"
                    onClick={() => onSelectEpisode(episode)}
                >
                    {episode.stillPath && (
                        <img src={episode.stillPath} alt={episode.title} className="episode-still" />
                    )}

                    <div className="episode-info">
                        <div className="episode-number">E{episode.episodeNumber}</div>
                        <div className="episode-details">
                            <h4>{episode.title}</h4>
                            {episode.overview && <p>{episode.overview}</p>}
                            <div className="episode-meta">
                                {episode.airDate && (
                                    <span>{new Date(episode.airDate).toLocaleDateString()}</span>
                                )}
                                {episode.runtime && <span>{episode.runtime} min</span>}
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}

const styles = `
.tv-show-card {
  cursor: pointer;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.3);
  transition: all 0.2s;
}

.tv-show-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.show-thumbnail {
  position: relative;
  aspect-ratio: 2/3;
}

.show-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.status-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-returning {
  background: #4ade80;
  color: #0a0a0a;
}

.status-ended {
  background: #94a3b8;
  color: white;
}

.status-canceled {
  background: #f87171;
  color: white;
}

.show-info {
  padding: 1rem;
}

.show-info h3 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.show-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.85rem;
  opacity: 0.7;
  margin-bottom: 0.5rem;
}

.show-rating {
  font-weight: 600;
  color: #ffd700;
}

.seasons-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.season-card {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
  transition: all 0.2s;
}

.season-card:hover {
  transform: scale(1.05);
}

.season-card img {
  width: 100%;
  aspect-ratio: 2/3;
  object-fit: cover;
}

.season-info {
  padding: 0.75rem;
}

.season-info h4 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
}

.episode-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.episode-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.episode-item:hover {
  background: rgba(0, 0, 0, 0.3);
}

.episode-still {
  width: 200px;
  aspect-ratio: 16/9;
  object-fit: cover;
  border-radius: 6px;
}

.episode-info {
  display: flex;
  gap: 1rem;
  flex: 1;
}

.episode-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: #667eea;
}

.episode-details {
  flex: 1;
}

.episode-details h4 {
  margin: 0 0 0.5rem;
}

.episode-details p {
  margin: 0 0 0.5rem;
  opacity: 0.8;
  font-size: 0.9rem;
}

.episode-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  opacity: 0.6;
}
`;

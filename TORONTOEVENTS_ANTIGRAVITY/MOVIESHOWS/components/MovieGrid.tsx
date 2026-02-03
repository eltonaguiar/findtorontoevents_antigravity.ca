/**
 * UPDATE #52: Movie Grid Component
 * Responsive grid layout for movies
 */

import React from 'react';
import { MovieCard } from './MovieCard';

interface Movie {
    id: number;
    title: string;
    type?: string;
    release_year?: number;
    genre?: string;
    description?: string;
    thumbnail?: string;
    rating?: number;
}

interface MovieGridProps {
    movies: Movie[];
    onPlayTrailer?: (movieId: number) => void;
    onAddToQueue?: (movieId: number) => void;
    onToggleFavorite?: (movieId: number) => void;
    favorites?: number[];
    loading?: boolean;
}

export function MovieGrid({
    movies,
    onPlayTrailer,
    onAddToQueue,
    onToggleFavorite,
    favorites = [],
    loading = false
}: MovieGridProps) {
    if (loading) {
        return (
            <div className="movie-grid">
                {[...Array(12)].map((_, i) => (
                    <div key={i} className="movie-card-skeleton">
                        <div className="skeleton-image"></div>
                        <div className="skeleton-content">
                            <div className="skeleton-title"></div>
                            <div className="skeleton-meta"></div>
                            <div className="skeleton-description"></div>
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    if (movies.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">🎬</div>
                <h3>No movies found</h3>
                <p>Try adjusting your filters or search terms</p>
            </div>
        );
    }

    return (
        <div className="movie-grid">
            {movies.map(movie => (
                <MovieCard
                    key={movie.id}
                    {...movie}
                    onPlay={() => onPlayTrailer?.(movie.id)}
                    onAddToQueue={() => onAddToQueue?.(movie.id)}
                    onToggleFavorite={() => onToggleFavorite?.(movie.id)}
                    isFavorite={favorites.includes(movie.id)}
                />
            ))}
        </div>
    );
}

const styles = `
.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  padding: 2rem 0;
}

@media (max-width: 768px) {
  .movie-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
}

.movie-card-skeleton {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  overflow: hidden;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton-image {
  aspect-ratio: 16/9;
  background: rgba(255, 255, 255, 0.1);
}

.skeleton-content {
  padding: 1.5rem;
}

.skeleton-title,
.skeleton-meta,
.skeleton-description {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  margin-bottom: 0.75rem;
}

.skeleton-title {
  height: 24px;
  width: 70%;
}

.skeleton-meta {
  height: 20px;
  width: 50%;
}

.skeleton-description {
  height: 40px;
  width: 100%;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
}

.empty-state p {
  margin: 0;
  opacity: 0.7;
}
`;

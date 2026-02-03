/**
 * UPDATE #51: Movie Card Component
 * Beautiful card display for movies
 */

import React from 'react';
import { LazyImage } from './LazyImage';
import { Rating } from './Rating';

interface MovieCardProps {
    id: number;
    title: string;
    type?: string;
    release_year?: number;
    genre?: string;
    description?: string;
    thumbnail?: string;
    rating?: number;
    onPlay?: () => void;
    onAddToQueue?: () => void;
    onToggleFavorite?: () => void;
    isFavorite?: boolean;
}

export function MovieCard({
    id,
    title,
    type = 'movie',
    release_year,
    genre,
    description,
    thumbnail,
    rating = 0,
    onPlay,
    onAddToQueue,
    onToggleFavorite,
    isFavorite = false
}: MovieCardProps) {
    return (
        <div className="movie-card">
            <div className="movie-card-image">
                <LazyImage
                    src={thumbnail || '/placeholder.jpg'}
                    alt={title}
                    className="card-thumbnail"
                />
                <div className="movie-card-overlay">
                    <button onClick={onPlay} className="play-button">
                        ▶ Play Trailer
                    </button>
                </div>
                <button
                    onClick={onToggleFavorite}
                    className={`favorite-button ${isFavorite ? 'active' : ''}`}
                >
                    {isFavorite ? '❤️' : '🤍'}
                </button>
            </div>

            <div className="movie-card-content">
                <h3 className="movie-title">{title}</h3>

                <div className="movie-meta">
                    {release_year && <span className="year">{release_year}</span>}
                    {type && <span className="type">{type}</span>}
                    {genre && <span className="genre">{genre}</span>}
                </div>

                {description && (
                    <p className="movie-description">{description.slice(0, 100)}...</p>
                )}

                <Rating movieId={id} initialRating={rating} readonly />

                <button onClick={onAddToQueue} className="add-to-queue">
                    + Add to Queue
                </button>
            </div>
        </div>
    );
}

const styles = `
.movie-card {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
  cursor: pointer;
}

.movie-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
}

.movie-card-image {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
}

.card-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.movie-card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.movie-card:hover .movie-card-overlay {
  opacity: 1;
}

.play-button {
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 50px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.play-button:hover {
  transform: scale(1.1);
}

.favorite-button {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.favorite-button:hover {
  transform: scale(1.2);
}

.movie-card-content {
  padding: 1.5rem;
}

.movie-title {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
  font-weight: 700;
}

.movie-meta {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
  opacity: 0.8;
}

.movie-meta span {
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.movie-description {
  margin: 0.75rem 0;
  font-size: 0.9rem;
  opacity: 0.7;
  line-height: 1.5;
}

.add-to-queue {
  width: 100%;
  padding: 0.75rem;
  margin-top: 1rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.add-to-queue:hover {
  background: rgba(255, 255, 255, 0.2);
}
`;

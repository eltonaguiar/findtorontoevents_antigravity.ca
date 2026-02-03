/**
 * UPDATE #58: Quick View Modal
 * Preview movie details without navigation
 */

import React from 'react';
import { Rating } from './Rating';
import { ShareButtons } from './ShareButtons';

interface QuickViewProps {
    movie: {
        id: number;
        title: string;
        type?: string;
        release_year?: number;
        genre?: string;
        description?: string;
        thumbnail?: string;
        rating?: number;
    };
    onClose: () => void;
    onPlayTrailer?: () => void;
    onAddToQueue?: () => void;
}

export function QuickView({ movie, onClose, onPlayTrailer, onAddToQueue }: QuickViewProps) {
    return (
        <div className="quick-view-overlay" onClick={onClose}>
            <div className="quick-view-modal" onClick={(e) => e.stopPropagation()}>
                <button onClick={onClose} className="quick-view-close">×</button>

                <div className="quick-view-content">
                    <div className="quick-view-image">
                        <img src={movie.thumbnail || '/placeholder.jpg'} alt={movie.title} />
                        <button onClick={onPlayTrailer} className="quick-play-button">
                            ▶ Play Trailer
                        </button>
                    </div>

                    <div className="quick-view-details">
                        <h2>{movie.title}</h2>

                        <div className="quick-meta">
                            {movie.release_year && <span>{movie.release_year}</span>}
                            {movie.type && <span>{movie.type}</span>}
                            {movie.genre && <span>{movie.genre}</span>}
                        </div>

                        <Rating movieId={movie.id} initialRating={movie.rating} />

                        {movie.description && (
                            <p className="quick-description">{movie.description}</p>
                        )}

                        <div className="quick-actions">
                            <button onClick={onAddToQueue} className="quick-add-queue">
                                + Add to Queue
                            </button>
                            <button onClick={onPlayTrailer} className="quick-watch">
                                Watch Now
                            </button>
                        </div>

                        <ShareButtons
                            url={`https://findtorontoevents.ca/MOVIESHOWS/movie/${movie.id}`}
                            title={movie.title}
                            description={movie.description}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

const styles = `
.quick-view-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.quick-view-modal {
  position: relative;
  background: rgba(20, 20, 20, 0.95);
  border-radius: 16px;
  max-width: 900px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.quick-view-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 2rem;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s;
}

.quick-view-close:hover {
  background: rgba(255, 0, 0, 0.6);
  transform: scale(1.1);
}

.quick-view-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  padding: 2rem;
}

@media (max-width: 768px) {
  .quick-view-content {
    grid-template-columns: 1fr;
  }
}

.quick-view-image {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
}

.quick-view-image img {
  width: 100%;
  height: auto;
  display: block;
}

.quick-play-button {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 50px;
  color: white;
  font-weight: 600;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-play-button:hover {
  transform: translate(-50%, -50%) scale(1.1);
}

.quick-view-details h2 {
  margin: 0 0 1rem;
  font-size: 2rem;
}

.quick-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  opacity: 0.8;
}

.quick-meta span {
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.quick-description {
  margin: 1.5rem 0;
  line-height: 1.6;
  opacity: 0.9;
}

.quick-actions {
  display: flex;
  gap: 1rem;
  margin: 2rem 0;
}

.quick-add-queue,
.quick-watch {
  flex: 1;
  padding: 1rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-add-queue {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.quick-add-queue:hover {
  background: rgba(255, 255, 255, 0.2);
}

.quick-watch {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.quick-watch:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
`;

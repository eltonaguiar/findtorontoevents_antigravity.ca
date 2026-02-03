/**
 * UPDATE #12: QueueManager Component
 * UI for managing user queue
 */

import React, { useState } from 'react';

interface Movie {
    id: number;
    title: string;
    thumbnails?: Array<{ url: string }>;
}

interface QueueManagerProps {
    queue: Movie[];
    onReorder: (fromIndex: number, toIndex: number) => void;
    onRemove: (movieId: number) => void;
    onClear: () => void;
}

export function QueueManager({ queue, onReorder, onRemove, onClear }: QueueManagerProps) {
    const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

    const handleDragStart = (index: number) => {
        setDraggedIndex(index);
    };

    const handleDragOver = (e: React.DragEvent, index: number) => {
        e.preventDefault();
        if (draggedIndex !== null && draggedIndex !== index) {
            onReorder(draggedIndex, index);
            setDraggedIndex(index);
        }
    };

    const handleDragEnd = () => {
        setDraggedIndex(null);
    };

    return (
        <div className="queue-manager">
            <div className="queue-header">
                <h3>📋 My Queue ({queue.length})</h3>
                {queue.length > 0 && (
                    <button onClick={onClear} className="clear-button">
                        Clear All
                    </button>
                )}
            </div>

            {queue.length === 0 ? (
                <div className="empty-queue">
                    <p>Your queue is empty</p>
                    <p className="hint">Add movies to start building your watchlist</p>
                </div>
            ) : (
                <div className="queue-list">
                    {queue.map((movie, index) => (
                        <div
                            key={movie.id}
                            className={`queue-item ${draggedIndex === index ? 'dragging' : ''}`}
                            draggable
                            onDragStart={() => handleDragStart(index)}
                            onDragOver={(e) => handleDragOver(e, index)}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="drag-handle">⋮⋮</div>

                            <div className="queue-item-thumbnail">
                                {movie.thumbnails?.[0]?.url && (
                                    <img src={movie.thumbnails[0].url} alt={movie.title} />
                                )}
                            </div>

                            <div className="queue-item-info">
                                <div className="queue-position">#{index + 1}</div>
                                <div className="queue-title">{movie.title}</div>
                            </div>

                            <button
                                onClick={() => onRemove(movie.id)}
                                className="remove-button"
                                title="Remove from queue"
                            >
                                ×
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

const styles = `
.queue-manager {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  padding: 1.5rem;
  max-height: 600px;
  overflow-y: auto;
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.queue-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.clear-button {
  padding: 0.5rem 1rem;
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid rgba(255, 0, 0, 0.4);
  border-radius: 6px;
  color: #ff6b6b;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.clear-button:hover {
  background: rgba(255, 0, 0, 0.3);
}

.empty-queue {
  text-align: center;
  padding: 3rem 1rem;
  opacity: 0.6;
}

.empty-queue .hint {
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: move;
  transition: all 0.2s;
}

.queue-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.queue-item.dragging {
  opacity: 0.5;
}

.drag-handle {
  color: rgba(255, 255, 255, 0.3);
  font-size: 1.2rem;
  cursor: grab;
}

.queue-item-thumbnail {
  width: 60px;
  height: 90px;
  border-radius: 4px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
}

.queue-item-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.queue-item-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.queue-position {
  font-weight: 600;
  color: #667eea;
  min-width: 40px;
}

.queue-title {
  font-size: 1rem;
}

.remove-button {
  width: 32px;
  height: 32px;
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid rgba(255, 0, 0, 0.3);
  border-radius: 50%;
  color: #ff6b6b;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.remove-button:hover {
  background: rgba(255, 0, 0, 0.4);
  transform: scale(1.1);
}
`;

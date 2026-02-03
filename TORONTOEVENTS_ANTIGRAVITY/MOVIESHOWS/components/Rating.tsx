/**
 * UPDATE #45: Rating Component
 * Star rating with user feedback
 */

import React, { useState } from 'react';

interface RatingProps {
    movieId: number;
    initialRating?: number;
    onRate?: (rating: number) => void;
    readonly?: boolean;
}

export function Rating({ movieId, initialRating = 0, onRate, readonly = false }: RatingProps) {
    const [rating, setRating] = useState(initialRating);
    const [hover, setHover] = useState(0);

    const handleClick = (value: number) => {
        if (readonly) return;
        setRating(value);
        onRate?.(value);

        // Save to localStorage
        localStorage.setItem(`rating_${movieId}`, value.toString());
    };

    return (
        <div className="rating-component">
            <div className="stars">
                {[1, 2, 3, 4, 5].map((star) => (
                    <button
                        key={star}
                        className={`star ${star <= (hover || rating) ? 'filled' : ''}`}
                        onClick={() => handleClick(star)}
                        onMouseEnter={() => !readonly && setHover(star)}
                        onMouseLeave={() => !readonly && setHover(0)}
                        disabled={readonly}
                    >
                        ★
                    </button>
                ))}
            </div>
            {rating > 0 && (
                <span className="rating-text">{rating}/5</span>
            )}
        </div>
    );
}

const styles = `
.rating-component {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stars {
  display: flex;
  gap: 0.25rem;
}

.star {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #444;
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
}

.star.filled {
  color: #ffd700;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
}

.star:hover:not(:disabled) {
  transform: scale(1.2);
}

.star:disabled {
  cursor: default;
}

.rating-text {
  font-size: 0.9rem;
  color: #888;
  font-weight: 600;
}
`;

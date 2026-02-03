/**
 * UPDATE #54: Genre Filter Component
 * Filter movies by genre
 */

import React from 'react';

const GENRES = [
    'Action',
    'Adventure',
    'Animation',
    'Comedy',
    'Crime',
    'Documentary',
    'Drama',
    'Family',
    'Fantasy',
    'Horror',
    'Mystery',
    'Romance',
    'Sci-Fi',
    'Thriller',
    'Western'
];

interface GenreFilterProps {
    selectedGenres: string[];
    onChange: (genres: string[]) => void;
}

export function GenreFilter({ selectedGenres, onChange }: GenreFilterProps) {
    const toggleGenre = (genre: string) => {
        if (selectedGenres.includes(genre)) {
            onChange(selectedGenres.filter(g => g !== genre));
        } else {
            onChange([...selectedGenres, genre]);
        }
    };

    const clearAll = () => {
        onChange([]);
    };

    return (
        <div className="genre-filter">
            <div className="genre-header">
                <h4>Genres</h4>
                {selectedGenres.length > 0 && (
                    <button onClick={clearAll} className="clear-genres">
                        Clear All ({selectedGenres.length})
                    </button>
                )}
            </div>

            <div className="genre-grid">
                {GENRES.map(genre => (
                    <button
                        key={genre}
                        onClick={() => toggleGenre(genre)}
                        className={`genre-tag ${selectedGenres.includes(genre) ? 'active' : ''}`}
                    >
                        {genre}
                    </button>
                ))}
            </div>
        </div>
    );
}

const styles = `
.genre-filter {
  margin-bottom: 2rem;
}

.genre-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.genre-header h4 {
  margin: 0;
  font-size: 1.1rem;
}

.clear-genres {
  padding: 0.5rem 1rem;
  background: rgba(255, 0, 0, 0.1);
  border: 1px solid rgba(255, 0, 0, 0.3);
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-genres:hover {
  background: rgba(255, 0, 0, 0.2);
}

.genre-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.genre-tag {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.genre-tag:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.genre-tag.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
  font-weight: 600;
}
`;

/**
 * UPDATE #23: Filter Panel Component
 * Advanced filtering by year, genre, type
 */

import React from 'react';

interface FilterOptions {
    year?: number;
    genre?: string;
    type?: 'movie' | 'tv' | 'all';
}

interface FilterPanelProps {
    filters: FilterOptions;
    onChange: (filters: FilterOptions) => void;
    availableGenres: string[];
    yearRange: { min: number; max: number };
}

export function FilterPanel({ filters, onChange, availableGenres, yearRange }: FilterPanelProps) {
    return (
        <div className="filter-panel">
            <h4>🎯 Filters</h4>

            <div className="filter-group">
                <label>Type</label>
                <div className="filter-buttons">
                    <button
                        className={filters.type === 'all' || !filters.type ? 'active' : ''}
                        onClick={() => onChange({ ...filters, type: 'all' })}
                    >
                        All
                    </button>
                    <button
                        className={filters.type === 'movie' ? 'active' : ''}
                        onClick={() => onChange({ ...filters, type: 'movie' })}
                    >
                        Movies
                    </button>
                    <button
                        className={filters.type === 'tv' ? 'active' : ''}
                        onClick={() => onChange({ ...filters, type: 'tv' })}
                    >
                        TV Shows
                    </button>
                </div>
            </div>

            <div className="filter-group">
                <label>Year</label>
                <input
                    type="range"
                    min={yearRange.min}
                    max={yearRange.max}
                    value={filters.year || yearRange.max}
                    onChange={(e) => onChange({ ...filters, year: parseInt(e.target.value) })}
                    className="year-slider"
                />
                <div className="year-display">
                    {filters.year || yearRange.max}
                </div>
            </div>

            <div className="filter-group">
                <label>Genre</label>
                <select
                    value={filters.genre || ''}
                    onChange={(e) => onChange({ ...filters, genre: e.target.value || undefined })}
                    className="genre-select"
                >
                    <option value="">All Genres</option>
                    {availableGenres.map(genre => (
                        <option key={genre} value={genre}>{genre}</option>
                    ))}
                </select>
            </div>

            <button
                onClick={() => onChange({ type: 'all' })}
                className="reset-button"
            >
                Reset Filters
            </button>
        </div>
    );
}

const styles = `
.filter-panel {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.filter-panel h4 {
  margin: 0 0 1.5rem;
  font-size: 1.1rem;
}

.filter-group {
  margin-bottom: 1.5rem;
}

.filter-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  font-size: 0.9rem;
  opacity: 0.8;
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
}

.filter-buttons button {
  flex: 1;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-buttons button.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
}

.filter-buttons button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.year-slider {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
}

.year-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
}

.year-display {
  text-align: center;
  margin-top: 0.5rem;
  font-size: 1.2rem;
  font-weight: 600;
  color: #667eea;
}

.genre-select {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 1rem;
  cursor: pointer;
}

.genre-select:focus {
  outline: none;
  border-color: #667eea;
}

.reset-button {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 0, 0, 0.1);
  border: 1px solid rgba(255, 0, 0, 0.3);
  border-radius: 8px;
  color: #ff6b6b;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.reset-button:hover {
  background: rgba(255, 0, 0, 0.2);
}
`;

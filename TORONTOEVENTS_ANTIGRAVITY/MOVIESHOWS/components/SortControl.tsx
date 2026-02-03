/**
 * UPDATE #55: Sort Component
 * Sort movies by different criteria
 */

import React from 'react';

export type SortOption =
    | 'title-asc'
    | 'title-desc'
    | 'year-asc'
    | 'year-desc'
    | 'rating-asc'
    | 'rating-desc'
    | 'added-asc'
    | 'added-desc';

interface SortControlProps {
    value: SortOption;
    onChange: (option: SortOption) => void;
}

export function SortControl({ value, onChange }: SortControlProps) {
    return (
        <div className="sort-control">
            <label htmlFor="sort-select">Sort by:</label>
            <select
                id="sort-select"
                value={value}
                onChange={(e) => onChange(e.target.value as SortOption)}
                className="sort-select"
            >
                <optgroup label="Title">
                    <option value="title-asc">Title (A-Z)</option>
                    <option value="title-desc">Title (Z-A)</option>
                </optgroup>
                <optgroup label="Release Year">
                    <option value="year-desc">Newest First</option>
                    <option value="year-asc">Oldest First</option>
                </optgroup>
                <optgroup label="Rating">
                    <option value="rating-desc">Highest Rated</option>
                    <option value="rating-asc">Lowest Rated</option>
                </optgroup>
                <optgroup label="Date Added">
                    <option value="added-desc">Recently Added</option>
                    <option value="added-asc">Oldest Added</option>
                </optgroup>
            </select>
        </div>
    );
}

/**
 * Utility function to sort movies
 */
export function sortMovies<T extends {
    title: string;
    release_year?: number;
    rating?: number;
    created_at?: string;
}>(movies: T[], sortOption: SortOption): T[] {
    const sorted = [...movies];

    switch (sortOption) {
        case 'title-asc':
            return sorted.sort((a, b) => a.title.localeCompare(b.title));
        case 'title-desc':
            return sorted.sort((a, b) => b.title.localeCompare(a.title));
        case 'year-asc':
            return sorted.sort((a, b) => (a.release_year || 0) - (b.release_year || 0));
        case 'year-desc':
            return sorted.sort((a, b) => (b.release_year || 0) - (a.release_year || 0));
        case 'rating-asc':
            return sorted.sort((a, b) => (a.rating || 0) - (b.rating || 0));
        case 'rating-desc':
            return sorted.sort((a, b) => (b.rating || 0) - (a.rating || 0));
        case 'added-asc':
            return sorted.sort((a, b) =>
                new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
            );
        case 'added-desc':
            return sorted.sort((a, b) =>
                new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
            );
        default:
            return sorted;
    }
}

const styles = `
.sort-control {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sort-control label {
  font-weight: 600;
  font-size: 0.9rem;
}

.sort-select {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
  min-width: 200px;
}

.sort-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.sort-select option {
  background: #1a1a1a;
  color: white;
}

.sort-select optgroup {
  font-weight: 600;
  color: #667eea;
}
`;

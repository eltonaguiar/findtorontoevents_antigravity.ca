/**
 * UPDATE #65: Advanced Search Component
 * Multi-criteria search with autocomplete
 */

import React, { useState, useEffect } from 'react';
import { useDebounce } from '../hooks/useDebounce';

interface SearchSuggestion {
    id: number;
    title: string;
    year?: number;
    type?: string;
}

interface AdvancedSearchProps {
    onSearch: (query: string, filters: SearchFilters) => void;
    suggestions?: SearchSuggestion[];
}

interface SearchFilters {
    type?: 'movie' | 'tv' | 'all';
    yearFrom?: number;
    yearTo?: number;
    genre?: string;
}

export function AdvancedSearch({ onSearch, suggestions = [] }: AdvancedSearchProps) {
    const [query, setQuery] = useState('');
    const [filters, setFilters] = useState<SearchFilters>({ type: 'all' });
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [showFilters, setShowFilters] = useState(false);

    const debouncedQuery = useDebounce(query, 300);

    useEffect(() => {
        if (debouncedQuery) {
            onSearch(debouncedQuery, filters);
        }
    }, [debouncedQuery, filters, onSearch]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSearch(query, filters);
        setShowSuggestions(false);
    };

    return (
        <div className="advanced-search">
            <form onSubmit={handleSubmit} className="search-form">
                <div className="search-input-wrapper">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => {
                            setQuery(e.target.value);
                            setShowSuggestions(true);
                        }}
                        onFocus={() => setShowSuggestions(true)}
                        placeholder="Search movies and TV shows..."
                        className="search-input-advanced"
                    />

                    <button
                        type="button"
                        onClick={() => setShowFilters(!showFilters)}
                        className="filter-toggle"
                    >
                        🔍 Filters
                    </button>

                    {showSuggestions && suggestions.length > 0 && (
                        <div className="search-suggestions">
                            {suggestions.map(suggestion => (
                                <button
                                    key={suggestion.id}
                                    onClick={() => {
                                        setQuery(suggestion.title);
                                        setShowSuggestions(false);
                                    }}
                                    className="suggestion-item"
                                >
                                    <span className="suggestion-title">{suggestion.title}</span>
                                    {suggestion.year && (
                                        <span className="suggestion-year">({suggestion.year})</span>
                                    )}
                                    {suggestion.type && (
                                        <span className="suggestion-type">{suggestion.type}</span>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {showFilters && (
                    <div className="search-filters">
                        <div className="filter-row">
                            <label>Type:</label>
                            <select
                                value={filters.type}
                                onChange={(e) => setFilters({ ...filters, type: e.target.value as any })}
                            >
                                <option value="all">All</option>
                                <option value="movie">Movies</option>
                                <option value="tv">TV Shows</option>
                            </select>
                        </div>

                        <div className="filter-row">
                            <label>Year Range:</label>
                            <input
                                type="number"
                                placeholder="From"
                                value={filters.yearFrom || ''}
                                onChange={(e) => setFilters({ ...filters, yearFrom: parseInt(e.target.value) || undefined })}
                                min="1900"
                                max={new Date().getFullYear()}
                            />
                            <span>-</span>
                            <input
                                type="number"
                                placeholder="To"
                                value={filters.yearTo || ''}
                                onChange={(e) => setFilters({ ...filters, yearTo: parseInt(e.target.value) || undefined })}
                                min="1900"
                                max={new Date().getFullYear()}
                            />
                        </div>
                    </div>
                )}
            </form>
        </div>
    );
}

const styles = `
.advanced-search {
  margin-bottom: 2rem;
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  gap: 0.5rem;
}

.search-input-advanced {
  flex: 1;
  padding: 1rem 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: white;
  font-size: 1rem;
}

.search-input-advanced:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 20px rgba(102, 126, 234, 0.2);
}

.filter-toggle {
  padding: 1rem 1.5rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-toggle:hover {
  background: rgba(255, 255, 255, 0.15);
}

.search-suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 0.5rem;
  background: rgba(20, 20, 20, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
  z-index: 100;
  max-height: 400px;
  overflow-y: auto;
}

.suggestion-item {
  width: 100%;
  padding: 1rem;
  background: none;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: white;
  text-align: left;
  cursor: pointer;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  transition: background 0.2s;
}

.suggestion-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.suggestion-title {
  flex: 1;
}

.suggestion-year,
.suggestion-type {
  opacity: 0.6;
  font-size: 0.9rem;
}

.search-filters {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filter-row {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.filter-row label {
  font-weight: 600;
  min-width: 100px;
}

.filter-row select,
.filter-row input {
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
}

.filter-row input[type="number"] {
  width: 100px;
}
`;

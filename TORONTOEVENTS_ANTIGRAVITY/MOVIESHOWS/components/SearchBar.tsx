/**
 * UPDATE #22: Search Functionality
 * Add search bar with real-time filtering
 */

import React, { useState, useCallback } from 'react';

interface SearchBarProps {
    onSearch: (query: string) => void;
    placeholder?: string;
}

export function SearchBar({ onSearch, placeholder = 'Search movies...' }: SearchBarProps) {
    const [query, setQuery] = useState('');

    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setQuery(value);
        onSearch(value);
    }, [onSearch]);

    const handleClear = () => {
        setQuery('');
        onSearch('');
    };

    return (
        <div className="search-bar">
            <div className="search-input-container">
                <span className="search-icon">🔍</span>
                <input
                    type="text"
                    value={query}
                    onChange={handleChange}
                    placeholder={placeholder}
                    className="search-input"
                />
                {query && (
                    <button onClick={handleClear} className="clear-button">×</button>
                )}
            </div>
        </div>
    );
}

const styles = `
.search-bar {
  margin-bottom: 2rem;
}

.search-input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 1rem;
  font-size: 1.2rem;
  opacity: 0.5;
}

.search-input {
  width: 100%;
  padding: 1rem 1rem 1rem 3rem;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: white;
  font-size: 1rem;
  transition: all 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 20px rgba(102, 126, 234, 0.2);
}

.clear-button {
  position: absolute;
  right: 1rem;
  width: 28px;
  height: 28px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.clear-button:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}
`;

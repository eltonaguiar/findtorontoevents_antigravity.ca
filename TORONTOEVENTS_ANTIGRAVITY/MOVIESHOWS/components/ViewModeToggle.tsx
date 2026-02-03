/**
 * UPDATE #57: View Mode Toggle
 * Switch between grid and list views
 */

import React from 'react';

export type ViewMode = 'grid' | 'list';

interface ViewModeToggleProps {
    mode: ViewMode;
    onChange: (mode: ViewMode) => void;
}

export function ViewModeToggle({ mode, onChange }: ViewModeToggleProps) {
    return (
        <div className="view-mode-toggle">
            <button
                onClick={() => onChange('grid')}
                className={`view-button ${mode === 'grid' ? 'active' : ''}`}
                title="Grid View"
            >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <rect x="2" y="2" width="6" height="6" rx="1" />
                    <rect x="12" y="2" width="6" height="6" rx="1" />
                    <rect x="2" y="12" width="6" height="6" rx="1" />
                    <rect x="12" y="12" width="6" height="6" rx="1" />
                </svg>
                Grid
            </button>
            <button
                onClick={() => onChange('list')}
                className={`view-button ${mode === 'list' ? 'active' : ''}`}
                title="List View"
            >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <rect x="2" y="3" width="16" height="3" rx="1" />
                    <rect x="2" y="9" width="16" height="3" rx="1" />
                    <rect x="2" y="15" width="16" height="3" rx="1" />
                </svg>
                List
            </button>
        </div>
    );
}

const styles = `
.view-mode-toggle {
  display: flex;
  gap: 0.5rem;
  background: rgba(0, 0, 0, 0.3);
  padding: 0.25rem;
  border-radius: 8px;
}

.view-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.view-button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.view-button.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-weight: 600;
}

.view-button svg {
  opacity: 0.8;
}
`;

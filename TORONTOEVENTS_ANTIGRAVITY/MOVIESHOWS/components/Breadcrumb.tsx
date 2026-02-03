/**
 * UPDATE #59: Breadcrumb Navigation
 * Show current location in app
 */

import React from 'react';

interface BreadcrumbItem {
    label: string;
    path?: string;
}

interface BreadcrumbProps {
    items: BreadcrumbItem[];
    onNavigate?: (path: string) => void;
}

export function Breadcrumb({ items, onNavigate }: BreadcrumbProps) {
    return (
        <nav className="breadcrumb">
            {items.map((item, index) => (
                <React.Fragment key={index}>
                    {index > 0 && <span className="breadcrumb-separator">/</span>}
                    {item.path ? (
                        <button
                            onClick={() => onNavigate?.(item.path!)}
                            className="breadcrumb-link"
                        >
                            {item.label}
                        </button>
                    ) : (
                        <span className="breadcrumb-current">{item.label}</span>
                    )}
                </React.Fragment>
            ))}
        </nav>
    );
}

const styles = `
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
  font-size: 0.9rem;
}

.breadcrumb-link {
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
}

.breadcrumb-link:hover {
  color: #764ba2;
  text-decoration: underline;
}

.breadcrumb-separator {
  opacity: 0.5;
}

.breadcrumb-current {
  color: white;
  font-weight: 600;
}
`;

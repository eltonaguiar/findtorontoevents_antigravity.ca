/**
 * UPDATE #82: Content Moderation System
 * Review and moderate user-generated content
 */

import React, { useState } from 'react';

type ContentType = 'comment' | 'review' | 'playlist';
type ModerationStatus = 'pending' | 'approved' | 'rejected';

interface ModerationItem {
    id: string;
    type: ContentType;
    userId: number;
    username: string;
    content: string;
    movieTitle?: string;
    status: ModerationStatus;
    reportCount: number;
    createdAt: string;
    flaggedReasons?: string[];
}

interface ContentModerationProps {
    items: ModerationItem[];
    onApprove: (id: string) => void;
    onReject: (id: string, reason: string) => void;
    onBanUser: (userId: number) => void;
}

export function ContentModeration({
    items,
    onApprove,
    onReject,
    onBanUser
}: ContentModerationProps) {
    const [filter, setFilter] = useState<ModerationStatus | 'all'>('pending');
    const [selectedItem, setSelectedItem] = useState<string | null>(null);
    const [rejectReason, setRejectReason] = useState('');

    const filteredItems = filter === 'all'
        ? items
        : items.filter(item => item.status === filter);

    const handleReject = (id: string) => {
        if (rejectReason.trim()) {
            onReject(id, rejectReason);
            setRejectReason('');
            setSelectedItem(null);
        }
    };

    return (
        <div className="content-moderation">
            <div className="moderation-header">
                <h2>Content Moderation</h2>
                <div className="filter-buttons">
                    <button
                        onClick={() => setFilter('all')}
                        className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                    >
                        All ({items.length})
                    </button>
                    <button
                        onClick={() => setFilter('pending')}
                        className={`filter-btn ${filter === 'pending' ? 'active' : ''}`}
                    >
                        Pending ({items.filter(i => i.status === 'pending').length})
                    </button>
                    <button
                        onClick={() => setFilter('approved')}
                        className={`filter-btn ${filter === 'approved' ? 'active' : ''}`}
                    >
                        Approved
                    </button>
                    <button
                        onClick={() => setFilter('rejected')}
                        className={`filter-btn ${filter === 'rejected' ? 'active' : ''}`}
                    >
                        Rejected
                    </button>
                </div>
            </div>

            <div className="moderation-list">
                {filteredItems.map(item => (
                    <div key={item.id} className={`moderation-item status-${item.status}`}>
                        <div className="item-header">
                            <div className="item-meta">
                                <span className="item-type">{item.type}</span>
                                <span className="item-user">{item.username}</span>
                                {item.movieTitle && <span className="item-movie">on {item.movieTitle}</span>}
                                {item.reportCount > 0 && (
                                    <span className="report-badge">🚩 {item.reportCount} reports</span>
                                )}
                            </div>
                            <span className="item-date">
                                {new Date(item.createdAt).toLocaleDateString()}
                            </span>
                        </div>

                        <div className="item-content">
                            {item.content}
                        </div>

                        {item.flaggedReasons && item.flaggedReasons.length > 0 && (
                            <div className="flagged-reasons">
                                <strong>Flagged for:</strong> {item.flaggedReasons.join(', ')}
                            </div>
                        )}

                        {item.status === 'pending' && (
                            <div className="item-actions">
                                <button
                                    onClick={() => onApprove(item.id)}
                                    className="btn-approve"
                                >
                                    ✓ Approve
                                </button>
                                <button
                                    onClick={() => setSelectedItem(item.id)}
                                    className="btn-reject"
                                >
                                    ✗ Reject
                                </button>
                                <button
                                    onClick={() => onBanUser(item.userId)}
                                    className="btn-ban"
                                >
                                    🚫 Ban User
                                </button>
                            </div>
                        )}

                        {selectedItem === item.id && (
                            <div className="reject-form">
                                <textarea
                                    value={rejectReason}
                                    onChange={(e) => setRejectReason(e.target.value)}
                                    placeholder="Reason for rejection..."
                                    className="reject-reason"
                                />
                                <div className="reject-actions">
                                    <button onClick={() => handleReject(item.id)} className="btn-confirm">
                                        Confirm Rejection
                                    </button>
                                    <button onClick={() => setSelectedItem(null)} className="btn-cancel">
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

const styles = `
.content-moderation {
  padding: 2rem;
}

.moderation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.moderation-header h2 {
  margin: 0;
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
}

.filter-btn {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.filter-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.moderation-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.moderation-item {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  border-left: 4px solid transparent;
}

.moderation-item.status-pending {
  border-left-color: #fbbf24;
}

.moderation-item.status-approved {
  border-left-color: #4ade80;
}

.moderation-item.status-rejected {
  border-left-color: #f87171;
}

.item-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.item-meta {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.item-type {
  padding: 0.25rem 0.75rem;
  background: rgba(102, 126, 234, 0.2);
  border-radius: 4px;
  font-size: 0.85rem;
  text-transform: uppercase;
}

.item-user {
  font-weight: 600;
}

.item-movie {
  opacity: 0.7;
  font-size: 0.9rem;
}

.report-badge {
  padding: 0.25rem 0.75rem;
  background: rgba(248, 113, 113, 0.2);
  border: 1px solid rgba(248, 113, 113, 0.4);
  border-radius: 4px;
  font-size: 0.85rem;
}

.item-date {
  opacity: 0.6;
  font-size: 0.9rem;
}

.item-content {
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.flagged-reasons {
  padding: 0.75rem;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.item-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-approve,
.btn-reject,
.btn-ban {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-approve {
  background: #4ade80;
  color: #0a0a0a;
}

.btn-reject {
  background: #f87171;
  color: white;
}

.btn-ban {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.reject-form {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}

.reject-reason {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: white;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 0.75rem;
}

.reject-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-confirm,
.btn-cancel {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.btn-confirm {
  background: #f87171;
  color: white;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}
`;

/**
 * UPDATE #72: Comments System
 * Add and display movie comments
 */

import React, { useState } from 'react';

interface Comment {
    id: number;
    userId: number;
    username: string;
    avatar?: string;
    content: string;
    rating?: number;
    createdAt: string;
    likes: number;
    isLiked?: boolean;
}

interface CommentsProps {
    movieId: number;
    comments: Comment[];
    currentUserId?: number;
    onAddComment?: (content: string, rating?: number) => void;
    onLikeComment?: (commentId: number) => void;
    onDeleteComment?: (commentId: number) => void;
}

export function Comments({
    movieId,
    comments,
    currentUserId,
    onAddComment,
    onLikeComment,
    onDeleteComment
}: CommentsProps) {
    const [newComment, setNewComment] = useState('');
    const [newRating, setNewRating] = useState(0);
    const [sortBy, setSortBy] = useState<'recent' | 'popular'>('recent');

    const sortedComments = [...comments].sort((a, b) => {
        if (sortBy === 'popular') {
            return b.likes - a.likes;
        }
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (newComment.trim()) {
            onAddComment?.(newComment, newRating || undefined);
            setNewComment('');
            setNewRating(0);
        }
    };

    return (
        <div className="comments-section">
            <div className="comments-header">
                <h3>Comments ({comments.length})</h3>
                <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
                    <option value="recent">Most Recent</option>
                    <option value="popular">Most Popular</option>
                </select>
            </div>

            {currentUserId && (
                <form onSubmit={handleSubmit} className="comment-form">
                    <div className="rating-input">
                        <span>Your Rating:</span>
                        {[1, 2, 3, 4, 5].map(star => (
                            <button
                                key={star}
                                type="button"
                                onClick={() => setNewRating(star)}
                                className={`star-btn ${star <= newRating ? 'active' : ''}`}
                            >
                                ★
                            </button>
                        ))}
                    </div>

                    <textarea
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        placeholder="Share your thoughts..."
                        className="comment-input"
                        rows={3}
                    />

                    <button type="submit" className="submit-comment">
                        Post Comment
                    </button>
                </form>
            )}

            <div className="comments-list">
                {sortedComments.map(comment => (
                    <div key={comment.id} className="comment-item">
                        <div className="comment-avatar">
                            {comment.avatar ? (
                                <img src={comment.avatar} alt={comment.username} />
                            ) : (
                                <div className="avatar-placeholder">
                                    {comment.username.charAt(0).toUpperCase()}
                                </div>
                            )}
                        </div>

                        <div className="comment-content">
                            <div className="comment-meta">
                                <span className="comment-author">{comment.username}</span>
                                {comment.rating && (
                                    <span className="comment-rating">
                                        {'★'.repeat(comment.rating)}
                                    </span>
                                )}
                                <span className="comment-date">
                                    {formatTimeAgo(comment.createdAt)}
                                </span>
                            </div>

                            <p className="comment-text">{comment.content}</p>

                            <div className="comment-actions">
                                <button
                                    onClick={() => onLikeComment?.(comment.id)}
                                    className={`like-btn ${comment.isLiked ? 'liked' : ''}`}
                                >
                                    👍 {comment.likes}
                                </button>

                                {currentUserId === comment.userId && (
                                    <button
                                        onClick={() => onDeleteComment?.(comment.id)}
                                        className="delete-btn"
                                    >
                                        Delete
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function formatTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

const styles = `
.comments-section {
  margin: 3rem 0;
}

.comments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.comments-header h3 {
  margin: 0;
  font-size: 1.5rem;
}

.comments-header select {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
}

.comment-form {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  margin-bottom: 2rem;
}

.rating-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.star-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #444;
  cursor: pointer;
  transition: all 0.2s;
}

.star-btn.active {
  color: #ffd700;
}

.comment-input {
  width: 100%;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 1rem;
}

.submit-comment {
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-comment:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.comment-item {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.comment-avatar img,
.comment-avatar .avatar-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-weight: 700;
}

.comment-content {
  flex: 1;
}

.comment-meta {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.comment-author {
  font-weight: 600;
}

.comment-rating {
  color: #ffd700;
}

.comment-date {
  opacity: 0.6;
}

.comment-text {
  margin: 0.5rem 0 1rem;
  line-height: 1.6;
}

.comment-actions {
  display: flex;
  gap: 1rem;
}

.like-btn,
.delete-btn {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.like-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.like-btn.liked {
  background: rgba(102, 126, 234, 0.2);
  border-color: #667eea;
}

.delete-btn {
  color: #ff6b6b;
  border-color: rgba(255, 107, 107, 0.3);
}

.delete-btn:hover {
  background: rgba(255, 107, 107, 0.1);
}
`;

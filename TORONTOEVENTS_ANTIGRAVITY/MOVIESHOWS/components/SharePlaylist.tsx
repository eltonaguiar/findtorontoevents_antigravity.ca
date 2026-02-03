/**
 * UPDATE #13: SharePlaylist Component
 * Generate and share playlist codes
 */

import React, { useState } from 'react';

interface SharePlaylistProps {
    queueMovies: Array<{ id: number; title: string }>;
    onShare: (title: string) => Promise<{ shareCode: string; url: string }>;
}

export function SharePlaylist({ queueMovies, onShare }: SharePlaylistProps) {
    const [title, setTitle] = useState('');
    const [shareUrl, setShareUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleShare = async () => {
        if (!title.trim()) {
            alert('Please enter a playlist title');
            return;
        }

        setLoading(true);
        try {
            const result = await onShare(title);
            setShareUrl(result.url);
        } catch (error) {
            alert('Failed to create share link');
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(shareUrl);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            alert('Failed to copy to clipboard');
        }
    };

    return (
        <div className="share-playlist">
            <h3>🔗 Share Your Queue</h3>
            <p className="subtitle">Create a shareable link for your movie queue ({queueMovies.length} movies)</p>

            {!shareUrl ? (
                <div className="share-form">
                    <div className="form-group">
                        <label htmlFor="playlist-title">Playlist Title</label>
                        <input
                            id="playlist-title"
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="e.g., My Favorite Action Movies"
                            maxLength={100}
                        />
                    </div>

                    <button
                        onClick={handleShare}
                        disabled={loading || queueMovies.length === 0}
                        className="share-button"
                    >
                        {loading ? 'Creating...' : 'Create Share Link'}
                    </button>

                    {queueMovies.length === 0 && (
                        <p className="warning">Add movies to your queue first</p>
                    )}
                </div>
            ) : (
                <div className="share-result">
                    <div className="share-url-container">
                        <input
                            type="text"
                            value={shareUrl}
                            readOnly
                            className="share-url"
                        />
                        <button onClick={handleCopy} className="copy-button">
                            {copied ? '✓ Copied!' : 'Copy'}
                        </button>
                    </div>

                    <div className="share-actions">
                        <a href={shareUrl} target="_blank" rel="noopener noreferrer" className="view-button">
                            View Playlist
                        </a>
                        <button onClick={() => setShareUrl('')} className="new-button">
                            Create Another
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

const styles = `
.share-playlist {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  padding: 1.5rem;
}

.share-playlist h3 {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
}

.subtitle {
  margin: 0 0 1.5rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.share-form .form-group {
  margin-bottom: 1rem;
}

.share-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.share-form input {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 1rem;
}

.share-button {
  width: 100%;
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.share-button:hover:not(:disabled) {
  transform: scale(1.02);
}

.share-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.warning {
  margin-top: 1rem;
  padding: 0.75rem;
  background: rgba(255, 165, 0, 0.1);
  border: 1px solid rgba(255, 165, 0, 0.3);
  border-radius: 8px;
  color: #ffa500;
  text-align: center;
}

.share-result {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.share-url-container {
  display: flex;
  gap: 0.5rem;
}

.share-url {
  flex: 1;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 0.9rem;
}

.copy-button {
  padding: 0.75rem 1.5rem;
  background: rgba(102, 126, 234, 0.2);
  border: 1px solid #667eea;
  border-radius: 8px;
  color: #667eea;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.copy-button:hover {
  background: rgba(102, 126, 234, 0.3);
}

.share-actions {
  display: flex;
  gap: 0.5rem;
}

.view-button,
.new-button {
  flex: 1;
  padding: 0.75rem;
  border-radius: 8px;
  font-weight: 600;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.view-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
}

.new-button {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
}

.view-button:hover,
.new-button:hover {
  transform: scale(1.02);
}
`;

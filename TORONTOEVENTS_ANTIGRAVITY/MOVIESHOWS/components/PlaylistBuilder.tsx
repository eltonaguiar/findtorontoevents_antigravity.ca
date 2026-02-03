/**
 * UPDATE #75: Playlist Builder
 * Create and manage custom playlists
 */

import React, { useState } from 'react';

interface Playlist {
    id: string;
    name: string;
    description?: string;
    movieIds: number[];
    createdAt: string;
    updatedAt: string;
    isPublic: boolean;
}

interface PlaylistBuilderProps {
    playlists: Playlist[];
    onCreatePlaylist: (name: string, description?: string) => void;
    onUpdatePlaylist: (id: string, updates: Partial<Playlist>) => void;
    onDeletePlaylist: (id: string) => void;
    onAddToPlaylist: (playlistId: string, movieId: number) => void;
    onRemoveFromPlaylist: (playlistId: string, movieId: number) => void;
}

export function PlaylistBuilder({
    playlists,
    onCreatePlaylist,
    onUpdatePlaylist,
    onDeletePlaylist,
    onAddToPlaylist,
    onRemoveFromPlaylist
}: PlaylistBuilderProps) {
    const [isCreating, setIsCreating] = useState(false);
    const [newName, setNewName] = useState('');
    const [newDescription, setNewDescription] = useState('');
    const [editingId, setEditingId] = useState<string | null>(null);

    const handleCreate = () => {
        if (newName.trim()) {
            onCreatePlaylist(newName, newDescription || undefined);
            setNewName('');
            setNewDescription('');
            setIsCreating(false);
        }
    };

    return (
        <div className="playlist-builder">
            <div className="playlist-header">
                <h2>My Playlists</h2>
                <button onClick={() => setIsCreating(true)} className="create-playlist-btn">
                    + New Playlist
                </button>
            </div>

            {isCreating && (
                <div className="playlist-form">
                    <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="Playlist name"
                        className="playlist-input"
                    />
                    <textarea
                        value={newDescription}
                        onChange={(e) => setNewDescription(e.target.value)}
                        placeholder="Description (optional)"
                        className="playlist-textarea"
                        rows={2}
                    />
                    <div className="form-actions">
                        <button onClick={handleCreate} className="btn-save">Create</button>
                        <button onClick={() => setIsCreating(false)} className="btn-cancel">Cancel</button>
                    </div>
                </div>
            )}

            <div className="playlists-grid">
                {playlists.map(playlist => (
                    <div key={playlist.id} className="playlist-card">
                        {editingId === playlist.id ? (
                            <div className="playlist-edit">
                                <input
                                    type="text"
                                    defaultValue={playlist.name}
                                    onBlur={(e) => {
                                        onUpdatePlaylist(playlist.id, { name: e.target.value });
                                        setEditingId(null);
                                    }}
                                    className="playlist-input"
                                    autoFocus
                                />
                            </div>
                        ) : (
                            <>
                                <div className="playlist-info">
                                    <h3>{playlist.name}</h3>
                                    {playlist.description && <p>{playlist.description}</p>}
                                    <div className="playlist-meta">
                                        <span>{playlist.movieIds.length} movies</span>
                                        <span>{playlist.isPublic ? '🌐 Public' : '🔒 Private'}</span>
                                    </div>
                                </div>

                                <div className="playlist-actions">
                                    <button onClick={() => setEditingId(playlist.id)} className="btn-icon">
                                        ✏️
                                    </button>
                                    <button
                                        onClick={() => onUpdatePlaylist(playlist.id, { isPublic: !playlist.isPublic })}
                                        className="btn-icon"
                                    >
                                        {playlist.isPublic ? '🔒' : '🌐'}
                                    </button>
                                    <button
                                        onClick={() => onDeletePlaylist(playlist.id)}
                                        className="btn-icon btn-delete"
                                    >
                                        🗑️
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

const styles = `
.playlist-builder {
  padding: 2rem;
}

.playlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.playlist-header h2 {
  margin: 0;
}

.create-playlist-btn {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.create-playlist-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.playlist-form {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  margin-bottom: 2rem;
}

.playlist-input,
.playlist-textarea {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-family: inherit;
  margin-bottom: 1rem;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-save,
.btn-cancel {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.playlists-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.playlist-card {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  transition: all 0.2s;
}

.playlist-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.playlist-info h3 {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
}

.playlist-info p {
  margin: 0 0 1rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.playlist-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  opacity: 0.6;
}

.playlist-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-icon {
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-delete:hover {
  background: rgba(255, 107, 107, 0.2);
  border-color: #ff6b6b;
}
`;

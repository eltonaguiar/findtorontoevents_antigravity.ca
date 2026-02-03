/**
 * UPDATE #71: User Profile Component
 * Display and edit user profile
 */

import React, { useState } from 'react';

interface UserProfile {
    id: number;
    username: string;
    email: string;
    avatar?: string;
    bio?: string;
    joinDate: string;
    favoriteGenres?: string[];
    watchedCount?: number;
    queueCount?: number;
}

interface UserProfileProps {
    profile: UserProfile;
    isOwnProfile?: boolean;
    onUpdate?: (profile: Partial<UserProfile>) => void;
}

export function UserProfile({ profile, isOwnProfile = false, onUpdate }: UserProfileProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editedProfile, setEditedProfile] = useState(profile);

    const handleSave = () => {
        onUpdate?.(editedProfile);
        setIsEditing(false);
    };

    return (
        <div className="user-profile">
            <div className="profile-header">
                <div className="profile-avatar">
                    {profile.avatar ? (
                        <img src={profile.avatar} alt={profile.username} />
                    ) : (
                        <div className="avatar-placeholder">
                            {profile.username.charAt(0).toUpperCase()}
                        </div>
                    )}
                </div>

                <div className="profile-info">
                    {isEditing ? (
                        <input
                            type="text"
                            value={editedProfile.username}
                            onChange={(e) => setEditedProfile({ ...editedProfile, username: e.target.value })}
                            className="profile-input"
                        />
                    ) : (
                        <h2>{profile.username}</h2>
                    )}

                    <p className="profile-email">{profile.email}</p>
                    <p className="profile-join-date">
                        Member since {new Date(profile.joinDate).toLocaleDateString()}
                    </p>
                </div>

                {isOwnProfile && (
                    <div className="profile-actions">
                        {isEditing ? (
                            <>
                                <button onClick={handleSave} className="btn-save">Save</button>
                                <button onClick={() => setIsEditing(false)} className="btn-cancel">Cancel</button>
                            </>
                        ) : (
                            <button onClick={() => setIsEditing(true)} className="btn-edit">Edit Profile</button>
                        )}
                    </div>
                )}
            </div>

            <div className="profile-stats">
                <div className="stat-card">
                    <div className="stat-value">{profile.watchedCount || 0}</div>
                    <div className="stat-label">Movies Watched</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{profile.queueCount || 0}</div>
                    <div className="stat-label">In Queue</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{profile.favoriteGenres?.length || 0}</div>
                    <div className="stat-label">Favorite Genres</div>
                </div>
            </div>

            {isEditing ? (
                <textarea
                    value={editedProfile.bio || ''}
                    onChange={(e) => setEditedProfile({ ...editedProfile, bio: e.target.value })}
                    placeholder="Tell us about yourself..."
                    className="profile-bio-edit"
                />
            ) : (
                profile.bio && <p className="profile-bio">{profile.bio}</p>
            )}

            {profile.favoriteGenres && profile.favoriteGenres.length > 0 && (
                <div className="favorite-genres">
                    <h3>Favorite Genres</h3>
                    <div className="genre-tags">
                        {profile.favoriteGenres.map(genre => (
                            <span key={genre} className="genre-tag">{genre}</span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

const styles = `
.user-profile {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 16px;
}

.profile-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
  align-items: flex-start;
}

.profile-avatar {
  flex-shrink: 0;
}

.profile-avatar img,
.avatar-placeholder {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-size: 3rem;
  font-weight: 700;
}

.profile-info {
  flex: 1;
}

.profile-info h2 {
  margin: 0 0 0.5rem;
  font-size: 2rem;
}

.profile-email {
  margin: 0.25rem 0;
  opacity: 0.7;
}

.profile-join-date {
  margin: 0.25rem 0;
  opacity: 0.6;
  font-size: 0.9rem;
}

.profile-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit,
.btn-save,
.btn-cancel {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-edit,
.btn-save {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin: 2rem 0;
}

.stat-card {
  text-align: center;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  margin-top: 0.5rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.profile-bio {
  margin: 2rem 0;
  line-height: 1.6;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.profile-bio-edit {
  width: 100%;
  min-height: 100px;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-family: inherit;
  resize: vertical;
}

.favorite-genres h3 {
  margin: 2rem 0 1rem;
}

.genre-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.genre-tag {
  padding: 0.5rem 1rem;
  background: rgba(102, 126, 234, 0.2);
  border: 1px solid rgba(102, 126, 234, 0.4);
  border-radius: 20px;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    text-align: center;
  }

  .profile-stats {
    grid-template-columns: 1fr;
  }
}
`;

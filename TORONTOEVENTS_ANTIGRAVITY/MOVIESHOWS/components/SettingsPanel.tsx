/**
 * UPDATE #77: Settings Panel
 * User preferences and app settings
 */

import React, { useState } from 'react';

interface Settings {
    theme: 'dark' | 'light' | 'auto';
    autoplay: boolean;
    notifications: boolean;
    emailUpdates: boolean;
    language: string;
    quality: 'auto' | 'high' | 'medium' | 'low';
    subtitles: boolean;
    maturityRating: 'all' | 'pg13' | 'r' | 'nc17';
}

interface SettingsPanelProps {
    settings: Settings;
    onUpdate: (settings: Settings) => void;
}

export function SettingsPanel({ settings, onUpdate }: SettingsPanelProps) {
    const [localSettings, setLocalSettings] = useState(settings);
    const [hasChanges, setHasChanges] = useState(false);

    const handleChange = <K extends keyof Settings>(key: K, value: Settings[K]) => {
        setLocalSettings(prev => ({ ...prev, [key]: value }));
        setHasChanges(true);
    };

    const handleSave = () => {
        onUpdate(localSettings);
        setHasChanges(false);
    };

    const handleReset = () => {
        setLocalSettings(settings);
        setHasChanges(false);
    };

    return (
        <div className="settings-panel">
            <h2>Settings</h2>

            <div className="settings-section">
                <h3>Appearance</h3>

                <div className="setting-item">
                    <label>Theme</label>
                    <select
                        value={localSettings.theme}
                        onChange={(e) => handleChange('theme', e.target.value as Settings['theme'])}
                    >
                        <option value="dark">Dark</option>
                        <option value="light">Light</option>
                        <option value="auto">Auto</option>
                    </select>
                </div>
            </div>

            <div className="settings-section">
                <h3>Playback</h3>

                <div className="setting-item">
                    <label>Autoplay Trailers</label>
                    <input
                        type="checkbox"
                        checked={localSettings.autoplay}
                        onChange={(e) => handleChange('autoplay', e.target.checked)}
                        className="toggle-switch"
                    />
                </div>

                <div className="setting-item">
                    <label>Video Quality</label>
                    <select
                        value={localSettings.quality}
                        onChange={(e) => handleChange('quality', e.target.value as Settings['quality'])}
                    >
                        <option value="auto">Auto</option>
                        <option value="high">High (1080p)</option>
                        <option value="medium">Medium (720p)</option>
                        <option value="low">Low (480p)</option>
                    </select>
                </div>

                <div className="setting-item">
                    <label>Subtitles</label>
                    <input
                        type="checkbox"
                        checked={localSettings.subtitles}
                        onChange={(e) => handleChange('subtitles', e.target.checked)}
                        className="toggle-switch"
                    />
                </div>
            </div>

            <div className="settings-section">
                <h3>Notifications</h3>

                <div className="setting-item">
                    <label>Push Notifications</label>
                    <input
                        type="checkbox"
                        checked={localSettings.notifications}
                        onChange={(e) => handleChange('notifications', e.target.checked)}
                        className="toggle-switch"
                    />
                </div>

                <div className="setting-item">
                    <label>Email Updates</label>
                    <input
                        type="checkbox"
                        checked={localSettings.emailUpdates}
                        onChange={(e) => handleChange('emailUpdates', e.target.checked)}
                        className="toggle-switch"
                    />
                </div>
            </div>

            <div className="settings-section">
                <h3>Content</h3>

                <div className="setting-item">
                    <label>Maturity Rating</label>
                    <select
                        value={localSettings.maturityRating}
                        onChange={(e) => handleChange('maturityRating', e.target.value as Settings['maturityRating'])}
                    >
                        <option value="all">All Ages</option>
                        <option value="pg13">PG-13 and below</option>
                        <option value="r">R and below</option>
                        <option value="nc17">All Ratings</option>
                    </select>
                </div>

                <div className="setting-item">
                    <label>Language</label>
                    <select
                        value={localSettings.language}
                        onChange={(e) => handleChange('language', e.target.value)}
                    >
                        <option value="en">English</option>
                        <option value="es">Español</option>
                        <option value="fr">Français</option>
                        <option value="de">Deutsch</option>
                        <option value="pt">Português</option>
                    </select>
                </div>
            </div>

            {hasChanges && (
                <div className="settings-actions">
                    <button onClick={handleSave} className="btn-save">Save Changes</button>
                    <button onClick={handleReset} className="btn-reset">Reset</button>
                </div>
            )}
        </div>
    );
}

const styles = `
.settings-panel {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 16px;
}

.settings-panel h2 {
  margin: 0 0 2rem;
  font-size: 2rem;
}

.settings-section {
  margin-bottom: 2.5rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.settings-section:last-of-type {
  border-bottom: none;
}

.settings-section h3 {
  margin: 0 0 1.5rem;
  font-size: 1.3rem;
  color: #667eea;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
}

.setting-item label {
  font-weight: 500;
  font-size: 1rem;
}

.setting-item select {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  min-width: 200px;
}

.toggle-switch {
  width: 50px;
  height: 26px;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 13px;
  position: relative;
  cursor: pointer;
  transition: all 0.3s;
}

.toggle-switch:checked {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.toggle-switch::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: white;
  top: 2px;
  left: 2px;
  transition: all 0.3s;
}

.toggle-switch:checked::before {
  left: 26px;
}

.settings-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-save,
.btn-reset {
  flex: 1;
  padding: 1rem;
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

.btn-save:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-reset {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.btn-reset:hover {
  background: rgba(255, 255, 255, 0.15);
}

@media (max-width: 768px) {
  .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .setting-item select {
    width: 100%;
  }
}
`;

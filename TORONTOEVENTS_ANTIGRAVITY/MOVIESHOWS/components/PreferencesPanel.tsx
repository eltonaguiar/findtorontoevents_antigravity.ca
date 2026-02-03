/**
 * UPDATE #14: PreferencesPanel Component
 * Settings for rewatch, autoplay, sound
 */

import React from 'react';

interface Preferences {
    rewatchEnabled: boolean;
    autoplay: boolean;
    soundOnScroll: boolean;
}

interface PreferencesPanelProps {
    preferences: Preferences;
    onChange: (key: keyof Preferences, value: boolean) => void;
    onSave: () => Promise<void>;
}

export function PreferencesPanel({ preferences, onChange, onSave }: PreferencesPanelProps) {
    const [saving, setSaving] = React.useState(false);

    const handleSave = async () => {
        setSaving(true);
        try {
            await onSave();
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="preferences-panel">
            <h3>⚙️ Preferences</h3>

            <div className="preference-item">
                <div className="preference-info">
                    <label htmlFor="rewatch">Enable Rewatch</label>
                    <p className="description">Show watched movies again in your queue</p>
                </div>
                <label className="toggle">
                    <input
                        id="rewatch"
                        type="checkbox"
                        checked={preferences.rewatchEnabled}
                        onChange={(e) => onChange('rewatchEnabled', e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                </label>
            </div>

            <div className="preference-item">
                <div className="preference-info">
                    <label htmlFor="autoplay">Autoplay</label>
                    <p className="description">Automatically play trailers when scrolling</p>
                </div>
                <label className="toggle">
                    <input
                        id="autoplay"
                        type="checkbox"
                        checked={preferences.autoplay}
                        onChange={(e) => onChange('autoplay', e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                </label>
            </div>

            <div className="preference-item">
                <div className="preference-info">
                    <label htmlFor="sound">Sound on Scroll</label>
                    <p className="description">Keep audio playing while scrolling</p>
                </div>
                <label className="toggle">
                    <input
                        id="sound"
                        type="checkbox"
                        checked={preferences.soundOnScroll}
                        onChange={(e) => onChange('soundOnScroll', e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                </label>
            </div>

            <button onClick={handleSave} disabled={saving} className="save-button">
                {saving ? 'Saving...' : 'Save Preferences'}
            </button>
        </div>
    );
}

const styles = `
.preferences-panel {
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  padding: 1.5rem;
}

.preferences-panel h3 {
  margin: 0 0 1.5rem;
  font-size: 1.2rem;
}

.preference-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.preference-item:last-of-type {
  border-bottom: none;
}

.preference-info {
  flex: 1;
}

.preference-info label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
  cursor: pointer;
}

.description {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.6;
}

.toggle {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 28px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.2);
  transition: 0.3s;
  border-radius: 28px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle input:checked + .toggle-slider {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.toggle input:checked + .toggle-slider:before {
  transform: translateX(22px);
}

.save-button {
  width: 100%;
  margin-top: 1.5rem;
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

.save-button:hover:not(:disabled) {
  transform: scale(1.02);
}

.save-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
`;

import React, { useState } from "react";
import type { Creator, SocialAccount, Platform } from "../types";
import { googleSearchYoutubeChannel } from "../utils/googleSearch";
import { extractYoutubeUsername } from "../utils/youtube";
import { grabAvatarFromAccounts } from "../utils/avatarGrabber";
import { FOLLOW_REASON_TAGS } from "../constants/followReasons";

interface CreatorFormProps {
  onSave: (creator: Creator) => void;
  onCancel: () => void;
}

const CATEGORY_OPTIONS = [
  { value: "", label: "Select category" },
  { value: "Favorites", label: "Favorites" },
  { value: "Other", label: "Other" },
  { value: "Hilarious Skits", label: "Hilarious Skits" },
  { value: "Prank Phone Calls", label: "Prank Phone Calls" },
  { value: "Other Content", label: "Other Content" },
  { value: "Education", label: "Education" },
  { value: "Entertainment", label: "Entertainment" },
  { value: "Gaming", label: "Gaming" },
  { value: "Music", label: "Music" },
  { value: "Tech", label: "Tech" },
  { value: "Lifestyle", label: "Lifestyle" },
];

const ACCOUNT_PLATFORMS: { value: Platform; label: string }[] = [
  { value: "youtube", label: "YouTube" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
  { value: "kick", label: "Kick" },
  { value: "twitch", label: "Twitch" },
  { value: "spotify", label: "Spotify" },
  { value: "other", label: "Other" },
];

const CreatorForm: React.FC<CreatorFormProps> = ({ onSave, onCancel }) => {
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [category, setCategory] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [customTagInput, setCustomTagInput] = useState("");

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag],
    );
  };

  const addCustomTag = () => {
    const trimmed = customTagInput.trim().toUpperCase();
    if (!trimmed) return;
    if (selectedTags.includes(trimmed)) {
      setCustomTagInput("");
      return;
    }
    setSelectedTags((prev) => [...prev, trimmed]);
    setCustomTagInput("");
  };

  const [newAccount, setNewAccount] = useState({
    platform: "youtube" as Platform,
    username: "",
    url: "",
  });

  const handleAddAccount = () => {
    if (!newAccount.username || !newAccount.url) return;
    setAccounts((prev) => [
      ...prev,
      { ...newAccount, id: crypto.randomUUID() },
    ]);
    setNewAccount({ platform: "youtube", username: "", url: "" });
  };

  const handleAutoFindYoutube = async () => {
    if (!name.trim()) return;
    const query = `${name.trim()} official youtube`;
    try {
      const url = await googleSearchYoutubeChannel(query);
      if (!url) {
        alert("Could not find a YouTube channel for this creator.");
        return;
      }
      const username = extractYoutubeUsername(url);
      setNewAccount((prev) => ({
        ...prev,
        platform: "youtube",
        url,
        username: username || prev.username,
      }));
    } catch (error) {
      console.error("Auto-find failed", error);
      alert("Auto-find failed. Try again in a moment.");
    }
  };

  const handleRemoveAccount = (id: string) => {
    setAccounts((prev) => prev.filter((a) => a.id !== id));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      let resolvedAvatar = avatarUrl.trim();
      if (!resolvedAvatar && accounts.length > 0) {
        try {
          const fetched = await grabAvatarFromAccounts(accounts, name);
          if (fetched) resolvedAvatar = fetched;
        } catch (error) {
          console.warn("Avatar grabber failed", error);
        }
      }

      onSave({
        id: crypto.randomUUID(),
        name,
        bio,
        reason,
        note,
        avatarUrl:
          resolvedAvatar || `https://api.dicebear.com/7.x/pixel-art/svg?seed=${name}`,
        accounts,
        isFavorite: false,
        addedAt: Date.now(),
        category,
        tags: selectedTags,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Add Creator</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="MrBeast"
              required
            />
          </div>
          <div className="form-group">
            <label>Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Follow reasons (tags)</label>
            <div className="tag-selector-grid">
              {FOLLOW_REASON_TAGS.map((tag) => {
                const isActive = selectedTags.includes(tag);
                return (
                  <button
                    type="button"
                    key={tag}
                    className={`tag-option ${isActive ? "tag-option--active" : ""}`}
                    onClick={() => toggleTag(tag)}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
            <div className="custom-tag-row">
              <input
                type="text"
                placeholder="Add custom tag"
                value={customTagInput}
                onChange={(e) => setCustomTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCustomTag();
                  }
                }}
              />
              <button
                type="button"
                className="btn-secondary"
                onClick={addCustomTag}
                disabled={!customTagInput.trim()}
              >
                Add
              </button>
            </div>
            {selectedTags.length > 0 && (
              <div className="tag-row tag-row--form">
                {selectedTags.map((tag) => (
                  <span key={tag} className="tag-pill">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="form-group">
            <button
              type="button"
              onClick={handleAutoFindYoutube}
              style={{ marginBottom: 8 }}
            >
              Auto-Find YouTube Channel
            </button>
          </div>
          <div className="form-group">
            <label>Reason for following (Optional)</label>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Motivational speaker"
            />
          </div>
          <div className="form-group">
            <label>Personal note (Optional)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Why this creator matters to you"
              rows={3}
            />
          </div>
          <div className="form-group">
            <label>Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Creator bio..."
            />
          </div>
          <div className="form-group">
            <label>Avatar URL (optional)</label>
            <input
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://..."
            />
          </div>

          <div
            className="accounts-section"
            style={{
              marginTop: "1.5rem",
              borderTop: "1px solid rgba(255,255,255,0.1)",
              paddingTop: "1rem",
            }}
          >
            <label>Social Accounts</label>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <select
                value={newAccount.platform}
                onChange={(e) =>
                  setNewAccount((prev) => ({
                    ...prev,
                    platform: e.target.value as Platform,
                  }))
                }
                style={{
                  background: "#0f172a",
                  color: "white",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  padding: "0.4rem",
                }}
              >
                {ACCOUNT_PLATFORMS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                placeholder="Username"
                value={newAccount.username}
                onChange={(e) =>
                  setNewAccount((prev) => ({ ...prev, username: e.target.value }))
                }
                style={{ flex: 1 }}
              />
            </div>
            <div style={{ display: "flex", gap: "8px", marginBottom: "1rem" }}>
              <input
                placeholder="URL (https://...)"
                value={newAccount.url}
                onChange={(e) =>
                  setNewAccount((prev) => ({ ...prev, url: e.target.value }))
                }
                style={{ flex: 1 }}
              />
              <button type="button" onClick={handleAddAccount} className="btn-add" style={{ padding: "0.4rem 1rem" }}>
                Add
              </button>
            </div>

            <div className="accounts-list">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className={`account-link ${acc.platform}`}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleRemoveAccount(acc.id)}
                >
                  {acc.username} x
                </div>
              ))}
            </div>
          </div>

          <div className="form-actions">
            <button type="button" onClick={onCancel} className="btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn-add" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Save Creator"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreatorForm;

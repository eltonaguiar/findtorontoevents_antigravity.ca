import React, { useState, useRef, useEffect } from "react";
import type { Creator, SocialAccount, Platform } from "../types";
import { googleSearchYoutubeChannel } from "../utils/googleSearch";
import { extractYoutubeUsername } from "../utils/youtube";
import { grabAvatarFromAccounts } from "../utils/avatarGrabber";
import { FOLLOW_REASON_TAGS } from "../constants/followReasons";

interface CreatorFormProps {
  onSave: (creator: Creator) => void;
  onCancel: () => void;
  availableCategories: string[];
}

const ACCOUNT_PLATFORMS: { value: Platform; label: string }[] = [
  { value: "youtube", label: "YouTube" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
  { value: "kick", label: "Kick" },
  { value: "twitch", label: "Twitch" },
  { value: "twitter", label: "Twitter" },
  { value: "spotify", label: "Spotify" },
  { value: "other", label: "Other" },
];

const CreatorForm: React.FC<CreatorFormProps> = ({ onSave, onCancel, availableCategories }) => {
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

  /* Drag & Resize Logic */
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [size, setSize] = useState({ w: 600, h: 700 });
  const isDragging = useRef(false);
  const isResizing = useRef(false);
  const lastPos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging.current) {
        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;
        setOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
        lastPos.current = { x: e.clientX, y: e.clientY };
      }
      if (isResizing.current) {
        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;
        setSize((prev) => ({
          w: Math.max(320, prev.w + dx),
          h: Math.max(400, prev.h + dy),
        }));
        lastPos.current = { x: e.clientX, y: e.clientY };
      }
    };
    const handleMouseUp = () => {
      isDragging.current = false;
      isResizing.current = false;
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const startDrag = (e: React.MouseEvent) => {
    isDragging.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

  const startResize = (e: React.MouseEvent) => {
    e.stopPropagation();
    isResizing.current = true;
    lastPos.current = { x: e.clientX, y: e.clientY };
  };

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
      <div
        className="modal-content"
        style={{
          transform: `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px))`,
          width: size.w,
          height: size.h,
          display: "flex",
          flexDirection: "column",
          padding: 0,
          overflow: "hidden",
          position: "relative",
          maxWidth: "95vw",
          maxHeight: "95vh",
        }}
      >
        {/* Draggable Header */}
        <div
          onMouseDown={startDrag}
          style={{
            padding: "1rem",
            background: "#1e293b",
            borderBottom: "1px solid rgba(255,255,255,0.1)",
            cursor: "grab",
            userSelect: "none",
            flexShrink: 0,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Add Creator</h2>
          <small style={{ color: "#64748b" }}>Drag header to move</small>
        </div>

        {/* Scrollable Form Area */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
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
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  required
                  style={{ flex: 1 }}
                >
                  <option value="">Select category</option>
                  {availableCategories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    const newCat = prompt("Enter new category name:");
                    if (newCat && newCat.trim()) setCategory(newCat.trim());
                  }}
                  title="Create new category"
                >
                  + New
                </button>
              </div>
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
                <button
                  type="button"
                  onClick={handleAddAccount}
                  className="btn-add"
                  style={{ padding: "0.4rem 1rem" }}
                >
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

        {/* Resizer Handle */}
        <div
          onMouseDown={startResize}
          style={{
            width: 20,
            height: 20,
            position: "absolute",
            bottom: 0,
            right: 0,
            cursor: "nwse-resize",
            zIndex: 10,
            background:
              "linear-gradient(135deg, transparent 50%, rgba(255,255,255,0.3) 50%)",
            borderTopLeftRadius: "4px",
          }}
        />
      </div>
    </div>
  );
};

export default CreatorForm;

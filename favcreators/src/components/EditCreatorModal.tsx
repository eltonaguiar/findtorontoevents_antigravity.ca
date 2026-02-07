import { useState } from "react";
import type { Creator, SocialAccount } from "../types";
import type { Platform } from "../types";
import { parseSocialUrl } from "../utils/parseSocialUrl";
import AvatarSelectorModal from "./AvatarSelectorModal";
import { resolveAuthBase } from "../utils/auth";

const PLATFORMS: Platform[] = ["youtube", "tiktok", "instagram", "kick", "twitch", "spotify", "twitter", "other"];

type Row = { id: string; platform: Platform; username: string; url: string; checkLive: boolean };

interface SearchResult {
  platform: string;
  username: string;
  exists: boolean | null;
  url: string;
  display_name: string;
  followers: number | string | null;
  avatar_url: string;
  error: string | null;
}

interface EditCreatorModalProps {
  creator: Creator;
  categories: string[];
  /** Which platforms auto-get checkLive=true when adding/editing. Falls back to ["tiktok"]. */
  defaultLivePlatforms?: Platform[];
  onSave: (updates: { category?: string; accounts: SocialAccount[]; note?: string; isLiveStreamer?: boolean; avatarUrl?: string; selectedAvatarSource?: string }) => void;
  onClose: () => void;
}

export default function EditCreatorModal({ creator, categories, defaultLivePlatforms, onSave, onClose }: EditCreatorModalProps) {
  const livePlats = defaultLivePlatforms ?? ["tiktok"];
  const defaultCheckLive = (platform: Platform, isLiveStreamer: boolean): boolean =>
    isLiveStreamer && livePlats.includes(platform);
  const hasDefaultLivePlatform = creator.accounts.some((a) => livePlats.includes(a.platform));
  const [isLiveStreamer, setIsLiveStreamer] = useState(
    creator.isLiveStreamer ?? hasDefaultLivePlatform
  );
  const [category, setCategory] = useState(creator.category ?? "");
  const [note, setNote] = useState(creator.note ?? creator.reason ?? "");
  const [rows, setRows] = useState<Row[]>(
    creator.accounts.map((a) => ({
      id: a.id,
      platform: a.platform,
      username: a.username,
      url: a.url,
      checkLive: a.checkLive ?? defaultCheckLive(a.platform, creator.isLiveStreamer ?? hasDefaultLivePlatform),
    }))
  );
  const [pasteUrls, setPasteUrls] = useState("");
  const [showAvatarSelector, setShowAvatarSelector] = useState(false);
  const [selectedAvatarUrl, setSelectedAvatarUrl] = useState(creator.avatarUrl || "");
  const [selectedAvatarSource, setSelectedAvatarSource] = useState(creator.selectedAvatarSource || "");
  
  // EZ-FIND state
  const [ezFindUsername, setEzFindUsername] = useState("");
  const [ezFindResults, setEzFindResults] = useState<SearchResult[]>([]);
  const [ezFindLoading, setEzFindLoading] = useState(false);
  const [showBulkEdit, setShowBulkEdit] = useState(false);
  const [bulkEditText, setBulkEditText] = useState("");

  const updateRow = (index: number, field: "platform" | "username" | "url", value: string) => {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    );
  };

  const setRowCheckLive = (index: number, checkLive: boolean) => {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, checkLive } : r)));
  };

  const addRow = () => {
    setRows((prev) => [
      ...prev,
      { id: crypto.randomUUID(), platform: "other", username: "", url: "", checkLive: false },
    ]);
  };

  const removeRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  const addFromPastedUrls = () => {
    const lines = pasteUrls.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    const newRows: Row[] = [];
    for (const line of lines) {
      const parsed = parseSocialUrl(line);
      if (parsed) {
        newRows.push({
          id: crypto.randomUUID(),
          platform: parsed.platform,
          username: parsed.username,
          url: parsed.url,
          checkLive: defaultCheckLive(parsed.platform, isLiveStreamer),
        });
      }
    }
    if (newRows.length > 0) {
      setRows((prev) => [...prev, ...newRows]);
      setPasteUrls("");
    }
  };

  const handleAvatarSelect = (avatarUrl: string, source: string) => {
    setSelectedAvatarUrl(avatarUrl);
    setSelectedAvatarSource(source);
  };

  // EZ-FIND: Search for username across platforms
  const handleEzFind = async () => {
    if (!ezFindUsername.trim()) return;
    setEzFindLoading(true);
    setEzFindResults([]);
    try {
      const authBase = await resolveAuthBase();
      const response = await fetch(
        `${authBase}/search_profiles.php?username=${encodeURIComponent(ezFindUsername.trim())}`
      );
      const data = await response.json();
      if (data.ok && data.results) {
        setEzFindResults(data.results);
      }
    } catch (err) {
      console.error("EZ-FIND error:", err);
    } finally {
      setEzFindLoading(false);
    }
  };

  // Add a found profile to the rows
  const addFromEzFind = (result: SearchResult) => {
    // Check if already exists
    const exists = rows.some(
      (r) => r.platform === result.platform && r.username.toLowerCase() === result.username.toLowerCase()
    );
    if (exists) return;

    setRows((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        platform: result.platform as Platform,
        username: result.username,
        url: result.url,
        checkLive: defaultCheckLive(result.platform as Platform, isLiveStreamer),
      },
    ]);
  };

  // Add all found profiles
  const addAllFromEzFind = () => {
    const toAdd = ezFindResults.filter((r) => r.exists === true);
    for (const result of toAdd) {
      const exists = rows.some(
        (r) => r.platform === result.platform && r.username.toLowerCase() === result.username.toLowerCase()
      );
      if (!exists) {
        setRows((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            platform: result.platform as Platform,
            username: result.username,
            url: result.url,
            checkLive: defaultCheckLive(result.platform as Platform, isLiveStreamer),
          },
        ]);
      }
    }
  };

  // Generate bulk edit text from current rows
  const generateBulkText = () => {
    return rows.map((r) => `${r.platform}:${r.username}:${r.url}`).join("\n");
  };

  // Parse bulk edit text back to rows
  const applyBulkEdit = () => {
    const lines = bulkEditText.split(/\r?\n/).filter((l) => l.trim());
    const newRows: Row[] = [];
    for (const line of lines) {
      const parts = line.split(":");
      if (parts.length >= 3) {
        const platform = parts[0].trim().toLowerCase() as Platform;
        const username = parts[1].trim();
        const url = parts.slice(2).join(":").trim(); // URL may contain colons
        if (PLATFORMS.includes(platform) && url) {
          newRows.push({
            id: crypto.randomUUID(),
            platform,
            username: username || "user",
            url,
            checkLive: defaultCheckLive(platform, isLiveStreamer),
          });
        }
      }
    }
    if (newRows.length > 0) {
      setRows(newRows);
      setShowBulkEdit(false);
    }
  };

  // Toggle bulk edit mode
  const toggleBulkEdit = () => {
    if (!showBulkEdit) {
      setBulkEditText(generateBulkText());
    }
    setShowBulkEdit(!showBulkEdit);
  };

  // Format follower count for display
  const formatFollowers = (count: number | string | null): string => {
    if (count === null) return "?";
    if (typeof count === "string") return count;
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  const handleSave = () => {
    const accounts: SocialAccount[] = rows
      .filter((r) => r.url.trim() !== "")
      .map((r) => {
        let username = r.username.trim();
        if (!username && r.url.trim()) {
          try {
            const path = new URL(r.url).pathname.replace(/\/$/, "");
            username = path.split("/").filter(Boolean).pop() || "user";
          } catch {
            username = "user";
          }
        }
        return {
          id: r.id,
          platform: r.platform,
          username: username || "user",
          url: r.url.trim(),
          checkLive: r.checkLive,
        };
      });
    onSave({
      category: category.trim() || undefined,
      accounts,
      note: note.trim() || undefined,
      isLiveStreamer,
      avatarUrl: selectedAvatarUrl !== creator.avatarUrl ? selectedAvatarUrl : undefined,
      selectedAvatarSource: selectedAvatarSource !== creator.selectedAvatarSource ? selectedAvatarSource : undefined,
    });
    onClose();
  };

  return (
    <div
      className="edit-creator-modal-overlay"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="edit-creator-modal"
        style={{
          background: "var(--card-bg)",
          borderRadius: "12px",
          border: "1px solid var(--glass-border)",
          maxWidth: "560px",
          width: "95%",
          maxHeight: "90vh",
          overflow: "auto",
          padding: "1.25rem",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "1rem" }}>
          <img
            src={selectedAvatarUrl || creator.avatarUrl}
            alt={creator.name}
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              objectFit: "cover",
              border: "2px solid rgba(255,255,255,0.2)",
            }}
            onError={(e) => {
              e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(creator.name)}`;
            }}
          />
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: "1.25rem" }}>Edit {creator.name}</h2>
            {selectedAvatarSource && (
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                Avatar from: {selectedAvatarSource}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setShowAvatarSelector(true)}
            style={{
              padding: "6px 12px",
              backgroundColor: "rgba(76, 175, 80, 0.2)",
              border: "1px solid rgba(76, 175, 80, 0.4)",
              borderRadius: "6px",
              color: "#4CAF50",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: "500",
            }}
          >
            Change Avatar
          </button>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "4px", fontSize: "0.9rem" }}>Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{
              width: "100%",
              padding: "8px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "6px",
              color: "var(--text)",
            }}
          >
            <option value="" style={{ background: "var(--card-bg)", color: "var(--text)" }}>— Select —</option>
            {categories.map((c) => (
              <option key={c} value={c} style={{ background: "var(--card-bg)", color: "var(--text)" }}>{c}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "0.9rem" }}>
            <input
              type="checkbox"
              checked={isLiveStreamer}
              onChange={(e) => setIsLiveStreamer(e.target.checked)}
              style={{ width: "18px", height: "18px" }}
            />
            <span>Live streamer</span>
          </label>
          <p style={{ margin: "4px 0 0 26px", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Mark which platforms to check for live status below. Your choice is saved per creator and does not affect other users.
          </p>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "4px", fontSize: "0.9rem" }}>Personal note</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Your note about this creator..."
            rows={2}
            style={{
              width: "100%",
              padding: "8px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "6px",
              color: "inherit",
              fontSize: "0.9rem",
              resize: "vertical",
            }}
          />
        </div>

        {/* EZ-FIND Section */}
        <div style={{ 
          marginBottom: "1rem", 
          padding: "12px", 
          background: "rgba(99, 102, 241, 0.1)", 
          border: "1px solid rgba(99, 102, 241, 0.3)",
          borderRadius: "8px" 
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>🔍 EZ-FIND</span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Search for a username across all platforms</span>
          </div>
          <div style={{ display: "flex", gap: "8px", marginBottom: ezFindResults.length > 0 ? "10px" : 0 }}>
            <input
              type="text"
              value={ezFindUsername}
              onChange={(e) => setEzFindUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleEzFind()}
              placeholder="Enter username (e.g. adinross)"
              style={{
                flex: 1,
                padding: "8px 12px",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: "6px",
                color: "inherit",
                fontSize: "0.9rem",
              }}
            />
            <button
              type="button"
              onClick={handleEzFind}
              disabled={ezFindLoading || !ezFindUsername.trim()}
              style={{
                padding: "8px 16px",
                background: "rgba(99, 102, 241, 0.3)",
                border: "1px solid rgba(99, 102, 241, 0.5)",
                borderRadius: "6px",
                color: "#a5b4fc",
                cursor: ezFindLoading ? "wait" : "pointer",
                fontSize: "0.9rem",
                fontWeight: 500,
              }}
            >
              {ezFindLoading ? "Searching..." : "Search"}
            </button>
          </div>
          
          {ezFindResults.length > 0 && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Found profiles for &quot;{ezFindUsername}&quot;:
                </span>
                <button
                  type="button"
                  onClick={addAllFromEzFind}
                  style={{
                    padding: "4px 10px",
                    background: "rgba(34, 197, 94, 0.2)",
                    border: "1px solid rgba(34, 197, 94, 0.4)",
                    borderRadius: "4px",
                    color: "#86efac",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                  }}
                >
                  + Add All Found
                </button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {ezFindResults.map((result) => {
                  const alreadyAdded = rows.some(
                    (r) => r.platform === result.platform && r.username.toLowerCase() === result.username.toLowerCase()
                  );
                  return (
                    <div
                      key={result.platform}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        padding: "8px 10px",
                        background: result.exists === true 
                          ? "rgba(34, 197, 94, 0.1)" 
                          : result.exists === false 
                            ? "rgba(239, 68, 68, 0.1)" 
                            : "rgba(255,255,255,0.05)",
                        border: `1px solid ${
                          result.exists === true 
                            ? "rgba(34, 197, 94, 0.3)" 
                            : result.exists === false 
                              ? "rgba(239, 68, 68, 0.3)" 
                              : "rgba(255,255,255,0.1)"
                        }`,
                        borderRadius: "6px",
                        fontSize: "0.85rem",
                      }}
                    >
                      <span style={{ 
                        width: "70px", 
                        fontWeight: 500,
                        textTransform: "capitalize" 
                      }}>
                        {result.platform}
                      </span>
                      <span style={{ 
                        flex: 1,
                        color: result.exists === true ? "#86efac" : result.exists === false ? "#fca5a5" : "var(--text-muted)"
                      }}>
                        {result.exists === true ? "✓ Found" : result.exists === false ? "✗ Not Found" : "? Unknown"}
                      </span>
                      {result.followers !== null && (
                        <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                          {formatFollowers(result.followers)} followers
                        </span>
                      )}
                      {result.exists === true && !alreadyAdded && (
                        <button
                          type="button"
                          onClick={() => addFromEzFind(result)}
                          style={{
                            padding: "3px 8px",
                            background: "rgba(34, 197, 94, 0.2)",
                            border: "1px solid rgba(34, 197, 94, 0.4)",
                            borderRadius: "4px",
                            color: "#86efac",
                            cursor: "pointer",
                            fontSize: "0.75rem",
                          }}
                        >
                          + Add
                        </button>
                      )}
                      {alreadyAdded && (
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Added</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
          <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>Social links</div>
          <button
            type="button"
            onClick={toggleBulkEdit}
            style={{
              padding: "4px 10px",
              background: showBulkEdit ? "rgba(251, 191, 36, 0.2)" : "rgba(255,255,255,0.1)",
              border: `1px solid ${showBulkEdit ? "rgba(251, 191, 36, 0.4)" : "rgba(255,255,255,0.2)"}`,
              borderRadius: "4px",
              color: showBulkEdit ? "#fcd34d" : "var(--text-muted)",
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            {showBulkEdit ? "← Normal Edit" : "Bulk Edit ✏️"}
          </button>
        </div>
        
        {showBulkEdit ? (
          <div style={{ marginBottom: "1rem" }}>
            <p style={{ margin: "0 0 8px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              Edit all links at once. Format: <code style={{ background: "rgba(255,255,255,0.1)", padding: "2px 6px", borderRadius: "3px" }}>platform:username:url</code> (one per line)
            </p>
            <textarea
              value={bulkEditText}
              onChange={(e) => setBulkEditText(e.target.value)}
              rows={8}
              style={{
                width: "100%",
                padding: "10px",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: "6px",
                color: "inherit",
                fontSize: "0.85rem",
                fontFamily: "monospace",
                resize: "vertical",
              }}
              placeholder="kick:adinross:https://kick.com/adinross
youtube:adinross:https://youtube.com/@adinross
twitch:adinross:https://twitch.tv/adinross"
            />
            <button
              type="button"
              onClick={applyBulkEdit}
              style={{
                marginTop: "8px",
                padding: "8px 16px",
                background: "rgba(34, 197, 94, 0.2)",
                border: "1px solid rgba(34, 197, 94, 0.4)",
                borderRadius: "6px",
                color: "#86efac",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: 500,
              }}
            >
              Apply Bulk Changes
            </button>
          </div>
        ) : (
          <>
        <p style={{ margin: "0 0 8px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
          One link per row.{" "}
          {isLiveStreamer ? (
            <>Tick &quot;Check for live&quot; for platforms you want live status checked (e.g. Starfireara: TikTok; wtfpreston: Kick/Twitch).</>
          ) : (
            <span style={{ color: "rgba(250, 204, 21, 0.8)" }}>
              Enable &quot;Live streamer&quot; above to select which platforms to check for live status.
            </span>
          )}{" "}
          You can also paste URLs below (one per line).
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "1rem" }}>
          {rows.map((row, index) => (
            <div
              key={row.id}
              style={{
                display: "grid",
                gridTemplateColumns: "32px 90px 1fr 2fr auto",
                gap: "8px",
                alignItems: "center",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  cursor: isLiveStreamer ? "pointer" : "not-allowed",
                  flexShrink: 0,
                  opacity: isLiveStreamer ? 1 : 0.4,
                }}
                title={isLiveStreamer ? "Check this account for live status" : "Enable 'Live streamer' above to check platforms for live status"}
              >
                <input
                  type="checkbox"
                  checked={isLiveStreamer && row.checkLive}
                  onChange={(e) => setRowCheckLive(index, e.target.checked)}
                  disabled={!isLiveStreamer}
                  style={{ width: "16px", height: "16px", cursor: isLiveStreamer ? "pointer" : "not-allowed" }}
                />
              </label>
              <select
                value={row.platform}
                onChange={(e) => updateRow(index, "platform", e.target.value as Platform)}
                style={{
                  padding: "6px 8px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "var(--text)",
                  fontSize: "0.85rem",
                }}
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p} style={{ background: "var(--card-bg)", color: "var(--text)" }}>{p}</option>
                ))}
              </select>
              <input
                type="text"
                value={row.username}
                onChange={(e) => updateRow(index, "username", e.target.value)}
                placeholder="Username"
                style={{
                  padding: "6px 8px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "inherit",
                  fontSize: "0.85rem",
                }}
              />
              <input
                type="url"
                value={row.url}
                onChange={(e) => updateRow(index, "url", e.target.value)}
                placeholder="https://..."
                style={{
                  padding: "6px 8px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "inherit",
                  fontSize: "0.85rem",
                }}
              />
              <button
                type="button"
                onClick={() => removeRow(index)}
                title="Remove link"
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px",
                  fontSize: "1rem",
                  opacity: 0.7,
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={addRow}
          className="btn-secondary"
          style={{ marginBottom: "1rem" }}
        >
          + Add link
        </button>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "4px", fontSize: "0.85rem" }}>
            Paste URLs (one per line) to add quickly
          </label>
          <textarea
            value={pasteUrls}
            onChange={(e) => setPasteUrls(e.target.value)}
            placeholder={"https://tiktok.com/@user\nhttps://youtube.com/@channel"}
            rows={3}
            style={{
              width: "100%",
              padding: "8px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "6px",
              color: "inherit",
              fontSize: "0.85rem",
              resize: "vertical",
            }}
          />
          <button type="button" onClick={addFromPastedUrls} className="btn-secondary" style={{ marginTop: "6px" }}>
            Add from pasted URLs
          </button>
        </div>
          </>
        )}

        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="button" onClick={handleSave} className="btn-add" style={{ padding: "8px 16px" }}>
            Apply changes
          </button>
        </div>
      </div>

      {showAvatarSelector && (
        <AvatarSelectorModal
          creator={creator}
          currentAvatarUrl={selectedAvatarUrl || creator.avatarUrl}
          onSelect={handleAvatarSelect}
          onClose={() => setShowAvatarSelector(false)}
        />
      )}
    </div>
  );
}
